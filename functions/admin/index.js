// GET /admin  -> channel dashboard (sign in with Google first)
import { channelList, esc, getState, html, session } from "../../lib/dashboard.js";
import { getPins } from "../../lib/pins.js";
import { getDrafts } from "../../lib/drafts.js";
import { getIdeas } from "../../lib/ideas.js";

const CSS = `
:root{--bg:#faf8f5;--ink:#1c1917;--muted:#6b6560;--line:#e7e2db;--accent:#c2410c;--ok:#15803d;--bad:#b91c1c;--card:#fff}
@media (prefers-color-scheme:dark){:root{--bg:#14171c;--ink:#ece8e3;--muted:#a39d96;--line:#2a2f37;--accent:#fb923c;--ok:#4ade80;--bad:#f87171;--card:#1b1f26}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
main{max-width:980px;margin:0 auto;padding:24px 16px 60px}
h2{font-size:21px;margin:36px 0 4px;letter-spacing:-.01em}h1{font-size:26px;margin:0 0 4px;letter-spacing:-.02em}.muted{color:var(--muted)}
.bar{display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:space-between;margin:16px 0}
.stats{display:flex;gap:10px;flex-wrap:wrap}.stat{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:10px 14px}
.stat b{display:block;font-size:22px}
.msg{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--accent);border-radius:10px;padding:10px 14px;margin:12px 0}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:14px;overflow:hidden}
th,td{padding:10px 12px;border-top:1px solid var(--line);text-align:left;vertical-align:middle}
th{border-top:0;font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)}
.pill{display:inline-block;border-radius:999px;padding:2px 10px;font-size:12px;font-weight:700}
.on{background:color-mix(in srgb,var(--ok) 15%,transparent);color:var(--ok)}
.off{background:color-mix(in srgb,var(--muted) 15%,transparent);color:var(--muted)}
.err{background:color-mix(in srgb,var(--bad) 15%,transparent);color:var(--bad)}
button,.btn{font:inherit;font-weight:700;font-size:13px;border-radius:9px;padding:7px 12px;border:1px solid var(--line);background:var(--card);color:var(--ink);cursor:pointer;text-decoration:none;display:inline-block}
.primary{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.danger{color:var(--bad)}
form{display:inline}
details.draft{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px;margin:10px 0}
details.draft summary{cursor:pointer;font-weight:700}
.preview{border-top:1px solid var(--line);margin-top:10px;padding-top:6px}
.preview h1{font-size:22px}.preview h2{font-size:18px}.preview h3{font-size:15px;color:var(--muted)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:12px;margin:12px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px}
.card h3{margin:4px 0 6px;font-size:16px}.prompt{font-size:13px;background:color-mix(in srgb,var(--muted) 10%,transparent);border-radius:8px;padding:8px;margin:8px 0;white-space:pre-wrap}
.row{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0}
@media (max-width:700px){table.ch td:nth-child(2),table.ch th:nth-child(2){display:none}}
`;

function page(body) {
  return `<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex">
<title>Pickixo · Dashboard</title><style>${CSS}</style></head><body><main>${body}</main></body></html>`;
}

export async function onRequestGet(context) {
  const msg = new URL(context.request.url).searchParams.get("msg");
  const note = msg ? `<div class="msg">${esc(msg)}</div>` : "";
  const s = await session(context);
  if (!s) {
    return html(page(`<h1>Pickixo channels</h1><p class="muted">Sign in with the owner Google account to manage YouTube channels.</p>
${note}<p><a class="btn primary" href="/auth/login">Sign in with Google</a></p>`));
  }

  const [chans, st, pins, drafts, ideas] = await Promise.all([channelList(context), getState(context.env), getPins(context.env), getDrafts(context.env), getIdeas(context.env)]);
  let connected = 0, active = 0, errors = 0;
  const rows = chans.map((c) => {
    const info = st.channels[c.id];
    let status, actions;
    if (!info) {
      status = `<span class="pill off">Not connected</span>`;
      actions = `<a class="btn primary" href="/auth/connect?ch=${esc(c.id)}">Connect</a>`;
    } else {
      connected++;
      if (info.error) errors++;
      if (info.enabled && !info.error) active++;
      status = info.error
        ? `<span class="pill err" title="${esc(info.error)}">Needs reconnect</span>`
        : info.enabled ? `<span class="pill on">Active</span>` : `<span class="pill off">Paused</span>`;
      const toggle = info.enabled ? "disable" : "enable";
      actions = `<form method="post" action="/admin/action"><input type="hidden" name="ch" value="${esc(c.id)}">
<button name="do" value="${toggle}">${info.enabled ? "Pause" : "Resume"}</button></form>
<a class="btn" href="/auth/connect?ch=${esc(c.id)}">Reconnect</a>
<form method="post" action="/admin/action" onsubmit="return confirm('Disconnect ${esc(c.id)}?')">
<input type="hidden" name="ch" value="${esc(c.id)}"><button class="danger" name="do" value="disconnect">Disconnect</button></form>`;
    }
    const yt = info ? `<a href="https://www.youtube.com/channel/${esc(info.youtube_id)}" target="_blank" rel="noopener">${esc(info.title)}</a> <span class="muted">${esc(info.handle)}</span>` : `<span class="muted">—</span>`;
    return `<tr><td><b>${esc(c.id)}</b></td><td>${esc(c.niche)}</td><td>${yt}</td><td>${status}</td><td>${actions}</td></tr>`;
  }).join("");

  const pauseBtn = st.paused
    ? `<button class="primary" name="do" value="resume_all">▶ Resume all</button>`
    : `<button class="danger" name="do" value="pause_all">■ Pause all uploads</button>`;

  return html(page(`<h1>Pickixo channels</h1>
<p class="muted">Signed in as ${esc(s.email)} · <a href="/auth/logout">Sign out</a></p>${note}
<div class="bar"><div class="stats">
<div class="stat"><span class="muted">Connected</span><b>${connected} / ${chans.length}</b></div>
<div class="stat"><span class="muted">Uploading</span><b>${st.paused ? 0 : active}</b></div>
<div class="stat"><span class="muted">Need attention</span><b>${errors}</b></div>
<div class="stat"><span class="muted">All uploads</span><b>${st.paused ? "Paused" : "On"}</b></div></div>
<form method="post" action="/admin/action">${pauseBtn}</form></div>
<p>🤖 <a href="https://claude.ai/code/routines/trig_01671Hhho11hhREEtgihzqsA" target="_blank" rel="noopener">Claude daily review</a> <span class="muted">· checks the report every day at 9pm (Bangladesh) and opens a PR if something needs fixing</span></p>
<table class="ch"><thead><tr><th>ID</th><th>Niche</th><th>YouTube channel</th><th>Status</th><th></th></tr></thead><tbody>${rows}</tbody></table>
<p class="muted">Connect: pick the Google account, then the exact YouTube channel for that niche, and allow.
If Google shows “hasn't verified this app”, choose Advanced → Go to Pickixo Shorts Uploader.</p>
${pinsSection(pins)}${draftsSection(drafts)}${ideasSection(ideas)}`));
}

function bdTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d)) return esc(iso);
  return d.toLocaleString("en-GB", { timeZone: "Asia/Dhaka", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

function pinsSection(p) {
  const lr = p.last_run || null;
  const pauseBtn = p.paused
    ? `<button class="primary" name="do" value="pins_resume">▶ Resume pins</button>`
    : `<button class="danger" name="do" value="pins_pause">■ Pause pins</button>`;
  const statusPill = p.paused ? `<span class="pill off">Paused</span>` : `<span class="pill on">On</span>`;
  const rows = (p.recent || []).map((r) => `<tr><td>${bdTime(r.due)}</td><td>${esc(r.title || r.product)}
<div class="muted">${esc(r.keyword)}</div></td><td>${esc(r.board)}</td>
<td>${r.link ? `<a href="${esc(r.link)}" target="_blank" rel="noopener nofollow">AliExpress ↗</a>` : ""}</td></tr>`).join("")
    || `<tr><td colspan="4" class="muted">No pins yet.</td></tr>`;
  const problems = (p.last_rows || []).filter((r) => r.status !== "scheduled");
  const probHtml = problems.length ? `<div class="msg"><b>Last run, skipped or failed:</b><br>${problems.map((r) =>
    `${esc(r.keyword)} · ${esc(r.status)} · <span class="muted">${esc(r.note)}</span>`).join("<br>")}</div>` : "";
  const msg = lr && lr.message ? `<div class="msg">${esc(lr.message)}</div>` : "";
  return `<h2>Pinterest · AliExpress</h2>
<p class="muted">AliExpress best sellers → pin text → Buffer → Pinterest board. Runs every day at 5:30pm (Bangladesh), 6 pins, 2 hours apart. Tracking ID <b>Pinterest</b>.</p>
<div class="bar"><div class="stats">
<div class="stat"><span class="muted">Pins</span><b>${statusPill}</b></div>
<div class="stat"><span class="muted">Last run</span><b>${lr ? `${lr.scheduled} / ${lr.want}` : "—"}</b><span class="muted">${lr ? bdTime(lr.at) : "not run yet"}</span></div>
<div class="stat"><span class="muted">Total scheduled</span><b>${p.total_scheduled || 0}</b></div></div>
<form method="post" action="/admin/action">${pauseBtn}</form></div>
<p><a class="btn" href="https://www.pinterest.com/pickixofinds/" target="_blank" rel="noopener">Pinterest profile</a>
<a class="btn" href="https://publish.buffer.com/channels/6affb1b7ece6dfde5f2a654c/schedule?tab=queue" target="_blank" rel="noopener">Buffer queue</a>
<a class="btn" href="https://portals.aliexpress.com/affiportals/web/report.htm" target="_blank" rel="noopener">AliExpress reports</a>
<a class="btn" href="https://github.com/monjurhye/pickixo-shorts/actions/workflows/pins.yml" target="_blank" rel="noopener">Pins workflow</a></p>
${msg}${probHtml}
<table><thead><tr><th>Time (BD)</th><th>Pin</th><th>Board</th><th>Link</th></tr></thead><tbody>${rows}</tbody></table>`;
}

function draftsSection(d) {
  const items = (d.items || []).map((x) => {
    const pill = x.status === "published" ? `<span class="pill off">Published</span>` : `<span class="pill on">New</span>`;
    const toggle = x.status === "published"
      ? `<button name="do" value="draft_new">Mark as new</button>`
      : `<button class="primary" name="do" value="draft_done">Mark published</button>`;
    return `<details class="draft"><summary>${pill} ${esc(x.title)} <span class="muted">· ${bdTime(x.created)} · ${esc((x.products || []).join(", "))}</span></summary>
<div class="row">
<button type="button" onclick="copyDraft('${esc(x.id)}')">📋 Copy article</button>
<button type="button" onclick="copyText('${esc(x.id)}-tags')">🏷 Copy tags</button>
<a class="btn" href="https://medium.com/new-story" target="_blank" rel="noopener">✍ Open Medium editor</a>
<form method="post" action="/admin/action"><input type="hidden" name="id" value="${esc(x.id)}">${toggle}
<button class="danger" name="do" value="draft_delete" onclick="return confirm('Delete this draft?')">Delete</button></form></div>
<p class="muted">Tags: <span id="${esc(x.id)}-tags">${esc((x.tags || []).join(", "))}</span></p>
<div class="preview" id="${esc(x.id)}-html">${x.html}</div>
<textarea id="${esc(x.id)}-md" hidden>${esc(x.markdown)}</textarea></details>`;
  }).join("") || `<p class="muted">No drafts yet. A new one is made every day at 3pm (Bangladesh).</p>`;
  const err = d.last_error ? `<div class="msg">${esc(d.last_error)}</div>` : "";
  return `<h2 id="drafts">Medium drafts · AppSumo</h2>
<p class="muted">One draft a day from real AppSumo deal data (Impact, sub id <b>medium</b>). Nothing is posted for you:
open a draft, add your own experience, click <b>Copy article</b>, paste into the Medium editor, add the tags, publish, then <b>Mark published</b>.
Keep the disclosure line at the top.</p>${err}${items}
<script>
async function copyDraft(id){
  const h=document.getElementById(id+'-html').innerHTML, t=document.getElementById(id+'-md').value;
  try{ await navigator.clipboard.write([new ClipboardItem({'text/html':new Blob([h],{type:'text/html'}),'text/plain':new Blob([t],{type:'text/plain'})})]); alert('Article copied. Paste it into the Medium editor.'); }
  catch(e){ try{ await navigator.clipboard.writeText(t); alert('Copied as plain text.'); }catch(e2){ alert('Copy failed: select the preview and press Cmd+C.'); } }
}
async function copyText(id){ try{ await navigator.clipboard.writeText(document.getElementById(id).innerText); alert('Tags copied.'); }catch(e){ alert('Copy failed.'); } }
</script>`;
}

const FREE_TOOLS = [
  ["Adobe Firefly ★ first choice", "https://firefly.adobe.com", "Free monthly credits, commercial use. Gives about 2048×2048 directly (≈4MP), so no upscaling: best approval chance. Download the largest size."],
  ["Ideogram", "https://ideogram.ai", "Free daily credits. Illustrations and posters (turn text off). Output is smaller, needs 2x upscale. Check their terms before selling."],
  ["FLUX.1 schnell", "https://huggingface.co/spaces/black-forest-labs/FLUX.1-schnell", "Apache 2.0, free commercial use, realistic. Only ~1024px: needs 2x upscale, so use it less."],
  ["Upscayl (only if needed)", "https://upscayl.org", "Free Mac app. Use 2x only (never 4x) with a realistic/high-fidelity model, then check at 100% zoom. Plastic or over-sharp images get rejected."],
];

function ideasSection(d) {
  const tools = FREE_TOOLS.map(([n, u, t]) =>
    `<div class="card"><h3><a href="${u}" target="_blank" rel="noopener">${esc(n)} ↗</a></h3><p class="muted">${esc(t)}</p></div>`).join("");
  const cards = (d.ideas || []).map((i, n) => `<div class="card">
<span class="pill ${i.kind === "seasonal" ? "on" : "off"}">${esc(i.kind)}</span> <span class="muted">${esc(i.aspect)} · ${esc(i.best_tool)}</span>
<h3>${esc(i.theme)}</h3><p class="muted">${esc(i.why)}</p>
<div class="prompt" id="idea-${n}">${esc(i.prompt)}</div>
<div class="row"><button type="button" onclick="copyText('idea-${n}')">📋 Copy prompt</button></div>
<p class="muted"><b>Check:</b> ${esc(i.avoid)}</p>
<p class="muted"><b>Keywords:</b> ${esc((i.keywords || []).join(", "))}</p></div>`).join("")
    || `<p class="muted">No ideas yet. New ideas arrive every morning at 8am (Bangladesh).</p>`;
  return `<h2 id="ideas">Magnific · Image ideas</h2>
<p class="muted">Fresh every morning. Seasonal ideas are for events 3-8 weeks ahead, because buyers download early.
${d.date ? "Updated " + bdTime(d.created) + "." : ""} ${esc(d.season_note || "")}</p>
<p><b>Free workflow:</b> copy a prompt → make 4-8 images (Adobe Firefly first: big enough without upscaling) → keep only clean ones (hands, faces, no text) →
if smaller than ~2000px, upscale 2x only and check at 100% zoom → run <code>tools/magnific/run.sh</code> for titles/keywords/CSV → upload on Magnific and mark as AI.</p>
<div class="grid">${tools}</div>
<div class="grid">${cards}</div>
<p><a class="btn" href="https://contributor.magnific.com/dashboard" target="_blank" rel="noopener">Magnific contributor ↗</a></p>
<p class="muted">Also check <b>Search Trends</b> in the Magnific contributor menu and favour ideas that match it.</p>`;
}
