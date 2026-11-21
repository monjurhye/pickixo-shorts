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

  // Same edge-energy measure as the Mac tool (PIL FIND_EDGES mean on the 100% crop); very low = soft.
  const MIN_SHARPNESS = 2.5;
  function sharpness(canvas) {
    const { width: w, height: h } = canvas;
    const px = canvas.getContext("2d").getImageData(0, 0, w, h).data;
    const g = new Float32Array(w * h);
    for (let i = 0; i < w * h; i++) g[i] = 0.299 * px[i * 4] + 0.587 * px[i * 4 + 1] + 0.114 * px[i * 4 + 2];
    let sum = 0, n = 0;
    for (let y = 1; y < h - 1; y++) for (let x = 1; x < w - 1; x++) {
      const i = y * w + x;
      let v = 8 * g[i] - g[i - 1] - g[i + 1] - g[i - w] - g[i + w] - g[i - w - 1] - g[i - w + 1] - g[i + w - 1] - g[i + w + 1];
      sum += v < 0 ? 0 : v > 255 ? 255 : v; n++;
    }
    return n ? sum / n : 0;
  }

  // 100% crops of the two most detailed areas outside the centre (small objects, text, ribbons
  // often sit at the sides, where a single centre crop never looks).
  function busiestCrops(full, prev, W, H, cx, cy, cs) {
    const t = Math.min(768, W, H), step = Math.round(t / 2), k = prev.width / W;
    const cand = [];
    const pos = (L) => { const a = []; for (let v = 0; v + t <= L; v += step) a.push(v); if (a[a.length - 1] !== L - t) a.push(L - t); return a; };
    for (const y of pos(H)) for (const x of pos(W)) {
      const ox = Math.max(0, Math.min(x + t, cx + cs) - Math.max(x, cx)), oy = Math.max(0, Math.min(y + t, cy + cs) - Math.max(y, cy));
      if (ox * oy > 0.5 * t * t) continue;                       // mostly the centre crop already
      const sw = Math.max(8, Math.round(t * k));
      const small = canvasOf(sw, sw);
      small.getContext("2d").drawImage(prev, x * k, y * k, t * k, t * k, 0, 0, sw, sw);
      cand.push({ x, y, e: sharpness(small) });
    }
    cand.sort((a, b) => b.e - a.e);
    const pick = [];
    for (const c of cand) {
      if (c.e < 1) break;                                         // flat area: nothing to inspect
      if (pick.some((p) => Math.abs(p.x - c.x) < t * 0.7 && Math.abs(p.y - c.y) < t * 0.7)) continue;
      pick.push(c);
      if (pick.length === 2) break;
    }
    return pick.map((p) => { const c = canvasOf(t, t); c.getContext("2d").drawImage(full, p.x, p.y, t, t, 0, 0, t, t); return c; });
  }

  function cleanKeywords(list) {
    const seen = new Set(), out = [];
    for (let k of list || []) {
      k = String(k).toLowerCase().replace(/[;,]/g, " ").replace(/\s+/g, " ").trim();
      k = k.replace(/[^\p{L}\p{N} '\-]/gu, "").trim();   // Magnific rejects odd characters such as "_"
      if (k && k !== AI_TAG.replace(/_/g, "") && !seen.has(k)) { seen.add(k); out.push(k); }
    }
    // AI is marked with Magnific's own "Created with AI" switch, not with a keyword.
    return out.slice(0, 45);
  }

  // ---- write title + keywords INTO the JPG (IPTC IIM + XMP), so Magnific fills them on upload ----
  const enc = new TextEncoder();
  function u16(n) { return [(n >> 8) & 255, n & 255]; }
  function u32(n) { return [(n >>> 24) & 255, (n >> 16) & 255, (n >> 8) & 255, n & 255]; }
  function cut(s, maxBytes) {
    let b = enc.encode(s);
    while (b.length > maxBytes) { s = s.slice(0, -1); b = enc.encode(s); }
    return b;
  }
  function iptcSegment(title, keywords) {
    const ds = [];
    const add = (rec, id, bytes) => ds.push(0x1C, rec, id, ...u16(bytes.length), ...bytes);
    add(1, 90, [0x1B, 0x25, 0x47]);                      // coded character set = UTF-8
    add(2, 0, [0, 4]);                                    // record version
    add(2, 5, cut(title, 64));                            // Object Name (title)
    add(2, 105, cut(title, 256));                         // Headline
    add(2, 120, cut(title, 2000));                        // Caption / description
    for (const k of keywords) add(2, 25, cut(k, 64));     // Keywords (one per dataset)
    const res = [...enc.encode("8BIM"), 0x04, 0x04, 0, 0, ...u32(ds.length), ...ds];
    if (ds.length % 2) res.push(0);                       // resource data is padded to an even length
    const payload = [...enc.encode("Photoshop 3.0"), 0, ...res];
    return [0xFF, 0xED, ...u16(payload.length + 2), ...payload];
  }
  function xmlEsc(s) { return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }
  function xmpSegment(title, keywords) {
    const li = keywords.map((k) => `<rdf:li>${xmlEsc(k)}</rdf:li>`).join("");
    const xml = `<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?><x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">` +
      `<rdf:Description rdf:about="" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:photoshop="http://ns.adobe.com/photoshop/1.0/">` +
      `<dc:title><rdf:Alt><rdf:li xml:lang="x-default">${xmlEsc(title)}</rdf:li></rdf:Alt></dc:title>` +
      `<dc:description><rdf:Alt><rdf:li xml:lang="x-default">${xmlEsc(title)}</rdf:li></rdf:Alt></dc:description>` +
      `<photoshop:Headline>${xmlEsc(title)}</photoshop:Headline>` +
      `<dc:subject><rdf:Bag>${li}</rdf:Bag></dc:subject></rdf:Description></rdf:RDF></x:xmpmeta><?xpacket end="w"?>`;
    const payload = [...enc.encode("http://ns.adobe.com/xap/1.0/"), 0, ...enc.encode(xml)];
    return [0xFF, 0xE1, ...u16(payload.length + 2), ...payload];
  }
  async function withMeta(jpg, title, keywords) {
    const b = new Uint8Array(await jpg.arrayBuffer());
    let at = 2;                                           // after SOI
    if (b[2] === 0xFF && b[3] === 0xE0) at = 4 + ((b[4] << 8) | b[5]);   // keep JFIF (APP0) first
    const meta = new Uint8Array([...xmpSegment(title, keywords), ...iptcSegment(title, keywords)]);
    return new Blob([b.slice(0, at), meta, b.slice(at)], { type: "image/jpeg" });
  }
  window.__magMeta = { withMeta };

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
    const extra = busiestCrops(full, prev, W, H, (W - s) / 2, (H - s) / 2, s);

    row.innerHTML = cardHtml({ name: file.name, size: note, busy: true, thumb: prev.toDataURL("image/jpeg", 0.7) });
    const r = await fetch("/api/magnific/meta", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ preview: await b64(prev, 0.85), crop: await b64(crop, 0.9),
        extra: await Promise.all(extra.map((c) => b64(c, 0.88))) }),
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
    item.sharpness = Math.round(sharpness(crop) * 10) / 10;
    if (item.sharpness < MIN_SHARPNESS) {
      item.problems.push(`soft at 100% (sharpness ${item.sharpness}, needs ${MIN_SHARPNESS}+)`);
      item.quality = Math.min(item.quality, 6);
    }
    item.notes = (item.notes || "") + ` · sharpness ${item.sharpness}`;
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
      for (const x of list) {
        download(await withMeta(x.jpg, x.title, x.keywords), x.out);   // title + keywords inside the file
        await new Promise((r) => setTimeout(r, 400));
      }
    },
  };
})();
