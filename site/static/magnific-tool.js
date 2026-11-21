// Magnific metadata tool for /admin. Runs in the browser: checks size, makes a JPG that
// meets Magnific's minimum (short side 2000+), asks /api/magnific/meta (OpenAI, server side)
// for title, keywords and a strict quality score, then builds Magnific's CSV.
(function () {
  const MIN_SHORT = 2000, TARGET_SHORT = 2048, MIN_PIXELS = 4000000, MIN_QUALITY = 7, AI_TAG = "_ai_generated";
  const $ = (id) => document.getElementById(id);
  const results = [];

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  // AI upscaler (UpscalerJS + ESRGAN medium 4x, MIT licence), loaded only when needed.
  const LIBS = ["https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@4.22.0/dist/tf.min.js",
                "https://cdn.jsdelivr.net/npm/@upscalerjs/default-model@1.0.0/dist/umd/index.min.js",
                "https://cdn.jsdelivr.net/npm/upscaler@1.0.0/dist/browser/umd/upscaler.min.js",
                "https://cdn.jsdelivr.net/npm/@upscalerjs/esrgan-medium@1.0.0/dist/umd/models/esrgan-medium/src/x4/index.min.js"];
  let upscaler = null;
  function loadScript(src) {
    return new Promise((res, rej) => { const t = document.createElement("script"); t.src = src; t.onload = res; t.onerror = () => rej(new Error("could not load " + src)); document.head.appendChild(t); });
  }
  async function getUpscaler() {
    if (upscaler) return upscaler;
    for (const src of LIBS) await loadScript(src);
    upscaler = new window.Upscaler({ model: window.ESRGANMedium4x });
    return upscaler;
  }
  async function aiUpscale(bmp, onProgress) {
    // ESRGAN 4x on a source no bigger than 1280px, then the caller shrinks to 2048 (supersampling).
    const k = Math.min(1, 1280 / Math.max(bmp.width, bmp.height));
    const src = canvasOf(Math.round(bmp.width * k), Math.round(bmp.height * k));
    src.getContext("2d").drawImage(bmp, 0, 0, src.width, src.height);
    const up = await getUpscaler();
    const dataUrl = await up.upscale(src, { patchSize: 64, padding: 4, progress: (p) => onProgress && onProgress(p) });
    const img = new Image();
    await new Promise((res, rej) => { img.onload = res; img.onerror = rej; img.src = dataUrl; });
    return img;
  }

  function canvasOf(w, h) {
    const c = document.createElement("canvas");
    c.width = w; c.height = h;
    return c;
  }

  function toBlob(c, q) {
    return new Promise((res) => c.toBlob(res, "image/jpeg", q));
  }

  async function b64(c, q) {
    const blob = await toBlob(c, q);
    const buf = new Uint8Array(await blob.arrayBuffer());
    let s = "";
    for (let i = 0; i < buf.length; i += 0x8000) s += String.fromCharCode.apply(null, buf.subarray(i, i + 0x8000));
    return btoa(s);
  }

  function cleanKeywords(list) {
    const seen = new Set(), out = [];
    for (let k of list || []) {
      k = String(k).toLowerCase().replace(/[;,]/g, " ").replace(/\s+/g, " ").trim();
      if (k && k !== AI_TAG && !seen.has(k)) { seen.add(k); out.push(k); }
    }
    return out.slice(0, 44).concat([AI_TAG]);
  }

  async function processFile(file, row) {
    const bmp = await createImageBitmap(file);
    let w = bmp.width, h = bmp.height, note = "";
    const short = Math.min(w, h);
    let scale = 1;
    let source = bmp;
    if (short < MIN_SHORT || w * h < MIN_PIXELS) {
      scale = TARGET_SHORT / short;
      if (scale > 1.3 && !$("mag-ai").checked) {
        row.innerHTML = cardHtml({ name: file.name, err: `Too small (${w}×${h}): needs ${scale.toFixed(1)}× enlargement. Make it bigger at the source (Firefly ~2048px), or tick "AI upscale" (slow).` });
        return null;
      }
      if (scale > 4) {
        row.innerHTML = cardHtml({ name: file.name, err: `Too small (${w}×${h}): more than 4× enlargement is needed. Make it bigger at the source.` });
        return null;
      }
      note = `${w}×${h} → `;
      if (scale > 1.3 && $("mag-ai").checked) {
        row.innerHTML = cardHtml({ name: file.name, size: note + "AI upscaling (first time loads the model, can take a few minutes)…", busy: true });
        try {
          source = await aiUpscale(bmp, (p) => {
            row.innerHTML = cardHtml({ name: file.name, size: note + "AI upscaling " + Math.round(p * 100) + "%…", busy: true });
          });
          note = "AI 4× then " + note;
        } catch (e) {
          note = "(AI upscale failed, plain resize) " + note;
        }
      }
    }
    const W = Math.round(w * scale), H = Math.round(h * scale);
    note += `${W}×${H}`;
    const full = canvasOf(W, H), fx = full.getContext("2d");
    fx.imageSmoothingEnabled = true; fx.imageSmoothingQuality = "high";
    fx.drawImage(source, 0, 0, W, H);
    const jpg = await toBlob(full, 0.95);

    const k = Math.min(1, 1024 / Math.max(W, H));
    const prev = canvasOf(Math.round(W * k), Math.round(H * k));
    prev.getContext("2d").drawImage(full, 0, 0, prev.width, prev.height);
    const s = Math.min(1024, W, H);
    const crop = canvasOf(s, s);
    crop.getContext("2d").drawImage(full, (W - s) / 2, (H - s) / 2, s, s, 0, 0, s, s);

    row.innerHTML = cardHtml({ name: file.name, size: note, busy: true, thumb: prev.toDataURL("image/jpeg", 0.7) });
    const r = await fetch("/api/magnific/meta", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ preview: await b64(prev, 0.85), crop: await b64(crop, 0.9) }),
    });
    const d = await r.json().catch(() => ({ error: "bad reply" }));
    if (!r.ok || d.error) {
      row.innerHTML = cardHtml({ name: file.name, size: note, thumb: prev.toDataURL("image/jpeg", 0.7), err: d.error || ("HTTP " + r.status) });
      return null;
    }
    const base = file.name.replace(/\.[^.]+$/, "");
    const item = {
      file: file.name, out: base + (scale > 1 ? "_2048" : "") + ".jpg", jpg, size: note,
      thumb: prev.toDataURL("image/jpeg", 0.7), title: String(d.title || "").replace(/\.$/, ""),
      keywords: cleanKeywords(d.keywords), category: d.category, quality: d.quality,
      notes: d.quality_notes, problems: d.problems || [],
    };
    item.include = item.quality >= MIN_QUALITY && item.problems.length === 0;
    results.push(item);
    row.innerHTML = cardHtml(item, results.length - 1);
    return item;
  }

  function cardHtml(x, idx) {
    const thumb = x.thumb ? `<img src="${x.thumb}" style="width:100%;border-radius:8px;margin-bottom:6px">` : "";
    if (x.err) return `<div class="card">${thumb}<b>${esc(x.name)}</b><p class="muted">${esc(x.size || "")}</p><div class="msg">${esc(x.err)}</div></div>`;
    if (x.busy) return `<div class="card">${thumb}<b>${esc(x.name)}</b><p class="muted">${esc(x.size)} · checking with AI…</p></div>`;
    const good = x.include;
    const probs = x.problems.length ? `<p style="color:var(--bad)"><b>Check:</b> ${esc(x.problems.join("; "))}</p>` : "";
    return `<div class="card">${thumb}
<span class="pill ${good ? "on" : "err"}">quality ${esc(x.quality)}/10</span> <span class="muted">${esc(x.size)} · ${esc(x.category)}</span>
<h3 style="margin:6px 0">${esc(x.title)}</h3><p class="muted">${esc(x.notes)}</p>${probs}
<p class="muted" style="font-size:12px">${esc(x.keywords.join(", "))}</p>
<label><input type="checkbox" ${good ? "checked" : ""} onchange="window.__mag.toggle(${idx}, this.checked)"> include in CSV</label>
<p class="muted" style="font-size:12px">Upload file: <b>${esc(x.out)}</b></p></div>`;
  }

  function download(blob, name) {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = name;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  }

  window.__mag = {
    toggle(i, on) { results[i].include = on; },
    async run(given) {
      const files = [...(given || $("mag-files").files)].filter((f) => /^image\/(jpeg|png|webp)$/.test(f.type));
      if (!files.length) { alert("Choose JPG/PNG images first."); return; }
      const grid = $("mag-results");
      results.length = 0; grid.innerHTML = "";
      $("mag-run").disabled = true;
      for (const f of files) {
        const row = document.createElement("div");
        grid.appendChild(row);
        row.innerHTML = cardHtml({ name: f.name, size: "", busy: true });
        try { await processFile(f, row); } catch (e) { row.innerHTML = cardHtml({ name: f.name, err: String(e) }); }
      }
      $("mag-run").disabled = false;
      $("mag-out").style.display = results.length ? "" : "none";
    },
    csv() {
      const model = ($("mag-model").value || "").trim();
      const rows = [["filename", "title", "keywords", "prompt", "model"]];
      for (const x of results) if (x.include) rows.push([x.out, x.title, x.keywords.join(","), "", model]);
      if (rows.length < 2) { alert("No image is ticked for the CSV."); return; }
      const text = rows.map((r) => r.map((c) => String(c).replace(/[;\r\n]/g, " ")).join(";")).join("\r\n");
      download(new Blob([text], { type: "text/csv" }), "magnific_metadata.csv");
    },
    // Plain PNG/WEBP -> JPG converter (no AI, no resize). Transparent areas become white.
    async convert() {
      const files = [...$("mag-files").files].filter((f) => /^image\/(jpeg|png|webp)$/.test(f.type));
      if (!files.length) { alert("Choose PNG/WEBP/JPG images first."); return; }
      const btn = $("mag-convert"), msg = $("mag-convert-msg");
      btn.disabled = true;
      let n = 0;
      for (const f of files) {
        msg.textContent = `Converting ${n + 1} of ${files.length}…`;
        const bmp = await createImageBitmap(f);
        const c = canvasOf(bmp.width, bmp.height), ctx = c.getContext("2d");
        ctx.fillStyle = "#ffffff"; ctx.fillRect(0, 0, c.width, c.height);
        ctx.drawImage(bmp, 0, 0);
        const blob = await toBlob(c, 0.95);
        download(blob, f.name.replace(/\.[^.]+$/, "") + ".jpg");
        n++;
        await new Promise((r) => setTimeout(r, 400));
      }
      msg.textContent = `Done: ${n} JPG file(s) downloaded (same size, quality 95%).`;
      btn.disabled = false;
    },
    async jpgs() {
      const list = results.filter((x) => x.include);
      if (!list.length) { alert("No image is ticked."); return; }
      for (const x of list) { download(x.jpg, x.out); await new Promise((r) => setTimeout(r, 400)); }
    },
  };
})();
