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
  const fbPagesRaw = await context.env.CHANNELS_KV.get("fbpages");
  const fbPages = fbPagesRaw ? JSON.parse(fbPagesRaw) : { pages: [] };
  const fbRaw = await context.env.CHANNELS_KV.get("fb");
  const fb = fbRaw ? JSON.parse(fbRaw) : { posts: [] };
  const planRes = await context.env.ASSETS.fetch(new URL("/facebook-plan.json", context.request.url));
  const fbPlan = planRes.ok ? await planRes.json() : null;
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
${fbSection(fb, fbPlan, fbPages)}${pinsSection(pins)}${draftsSection(drafts)}${ideasSection(ideas)}${magnificToolSection()}`));
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
Keep the disclosure line at the top.</p>
<div class="card"><h3>🔓 AI prompt pack (AdBlueMedia locker)</h3>
<p><a href="/free/ai-prompts/" target="_blank" rel="noopener">shop.pickixo.com/free/ai-prompts/</a> · up to 100 stock-image prompts,
10 new every morning. 5 are open; the full pack (/free/ai-prompts/full/) opens after the visitor completes one AdBlueMedia sponsor offer.</p>
<p class="muted"><b>Who wants it:</b> people making AI images for stock sites, Etsy, social media. <b>Where to share:</b> a Medium article
like "How I pick AI image ideas that sell on stock sites" with the pack linked at the end; LinkedIn/X posts; Quora answers about AI stock photos;
Pinterest pins of example images. <b>Rules:</b> say clearly that unlocking needs one sponsor offer; never promise money or prizes;
no fake countdowns; don't spam groups. <b>Results:</b> AdBlueMedia dashboard (clicks, unlocks, earnings).</p></div>
<div class="card"><h3>📘 Free ebook: Publish an iOS App Without a Mac (AdBlueMedia locker)</h3>
<p><a href="/free/ios-without-mac/" target="_blank" rel="noopener">shop.pickixo.com/free/ios-without-mac/</a> · English edition of your Pickixo ebook.
Chapter 1 and the contents are open; the full book (/free/ios-without-mac/full/) opens after one sponsor offer, and readers can save it as a PDF.</p>
<p class="muted"><b>Who wants it:</b> developers on Windows who want to publish iPhone apps (huge in South Asia, but for earnings target US/UK/CA readers too).
<b>Where to share:</b> a Medium article such as "How I published an iPhone app from Windows without a Mac" (a short version of Chapter 2 with the ebook linked at the end),
dev.to/Hashnode, Reddit answers where self-promotion is allowed, Quora ("Can I publish an iOS app without a Mac?"), LinkedIn.
<b>Rules:</b> say that unlocking needs one sponsor offer; no fake urgency.</p></div>
<div class="card"><h3>📋 AppSumo deals list (open, no locker)</h3>
<p><a href="/free/lifetime-deals/" target="_blank" rel="noopener">shop.pickixo.com/free/lifetime-deals/</a> · 25 newest AppSumo deals, sub id <b>freepage</b>.
Good as the "full updated list" link at the end of your AppSumo Medium articles.</p></div>
${err}${items}
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
<div class="msg"><b>Avoid "Low quality" rejections:</b> zoom to 100% before uploading. Reject images with plastic or waxy surfaces,
smeared small details, over-sharp edges, odd hands or fake text. Fewer objects in a scene = fewer AI mistakes.
The Mac tool now scores every image and leaves weak ones out of the CSV (see magnific_report.txt).</div>
<div class="grid">${tools}</div>
<div class="grid">${cards}</div>
<p><a class="btn" href="https://contributor.magnific.com/dashboard" target="_blank" rel="noopener">Magnific contributor ↗</a></p>
<p class="muted">Also check <b>Search Trends</b> in the Magnific contributor menu and favour ideas that match it.</p>`;
}

function magnificToolSection() {
  return `<h2 id="magnific-tool">Magnific · Upscale + metadata tool</h2>
<p class="muted">Choose your finished images. For each one it: makes sure the short side is 2000px+ (AI upscale 4× with ESRGAN, then down to 2048,
or a plain resize for small changes), checks quality at 100% like a reviewer, writes the title and keywords (45 incl. the AI tag), and builds
Magnific's CSV. Weak images (below 7/10 or with problems such as fake text) are left out; you can tick them back in. Images stay in your browser;
only small previews go to the AI.</p>
<div class="card"><div class="row">
<input type="file" id="mag-files" accept="image/jpeg,image/png,image/webp" multiple>
<label title="Slow on older laptops"><input type="checkbox" id="mag-ai"> AI upscale (slow, off by default)</label>
<input type="text" id="mag-model" placeholder="Model (as in Magnific's dropdown), optional" style="min-width:260px">
<button class="primary" id="mag-run" onclick="window.__mag.run()">Check & make metadata</button></div>
<div class="row" id="mag-out" style="display:none">
<button onclick="window.__mag.jpgs()">⬇ Download JPGs (ticked)</button>
<button onclick="window.__mag.csv()">⬇ Download CSV (ticked)</button>
<a class="btn" href="https://contributor.magnific.com/" target="_blank" rel="noopener">Open Magnific ↗</a></div>
<p class="muted">Then on Magnific: Uploads → drop the downloaded JPGs → Import metadata → choose the CSV → check AI label and model → Submit.
AI upscaling runs on your computer; the first image loads the model (~10&nbsp;MB) and can take a few minutes on an older Mac.</p></div>
<div class="grid" id="mag-results"></div>
<script src="/magnific-tool.js?v=3"></script>`;
}

function fbConnectHtml(fp) {
  if (!fp.pages || !fp.pages.length)
    return `<div class="card"><h3>Connect your Facebook Page</h3><p class="muted">Uses your own Meta app (Pickixo Poster). The Page token is stored only in Cloudflare; nobody copies it.</p>
<p><a class="btn primary" href="/auth/fb-connect">Connect Facebook Page</a></p></div>`;
  const opts = fp.pages.map((p) => `<label style="display:block"><input type="radio" name="page" value="${esc(p.id)}" ${p.id === fp.active ? "checked" : ""}> ${esc(p.name)}${p.can_post ? "" : " <span class=\"muted\">(no posting rights)</span>"}</label>`).join("");
  return `<div class="card"><h3>✅ Facebook connected</h3><form method="post" action="/admin/action">${opts}
<div class="row"><button name="do" value="fb_select">Use this Page</button>
<a class="btn" href="/auth/fb-connect">Reconnect</a>
<button class="danger" name="do" value="fb_disconnect" onclick="return confirm('Disconnect Facebook?')">Disconnect</button></div></form></div>`;
}

function fbSection(d, plan, fp) {
  const planHtml = plan ? `<div class="card"><h3>Niche: ${esc(plan.niche)}</h3>
<p class="muted"><b>Audience:</b> ${esc(plan.audience)}</p><p class="muted"><b>Why:</b> ${esc(plan.why)}</p>
<p class="muted"><b>Pillars:</b> ${esc((plan.pillars || []).join(" · "))}</p>
<p class="muted"><b>Post times (US Eastern):</b> ${esc((plan.schedule_us_et || []).join(", "))} · <b>Name ideas:</b> ${esc((plan.page_name_ideas || []).join(", "))}</p>
<p class="muted"><b>Rules:</b> ${esc((plan.rules || []).join(" "))}</p></div>` : "";
  const posts = (d.posts || []).map((p, n) => `<div class="card">
<span class="pill ${String(p.status).startsWith("scheduled") ? "on" : String(p.status).startsWith("error") ? "err" : "off"}">${esc(p.status || p.type)}</span>
<span class="muted">${esc(p.type)} · ${esc(p.time_et)} ET</span>
<h3>${esc(p.title)}</h3><p class="muted">${esc(p.pillar)}</p>
<p><b>Hook:</b> ${esc(p.hook)}</p>
<div class="prompt" id="fbs-${n}">${esc(p.script)}</div>
<div class="row"><button type="button" onclick="copyText('fbs-${n}')">📋 Copy script</button>
<button type="button" onclick="copyText('fbc-${n}')">📋 Copy caption</button></div>
<p class="muted"><b>Visuals:</b> ${esc(p.visuals)}</p>
<p id="fbc-${n}">${esc(p.caption)} ${esc((p.hashtags || []).map((h) => "#" + h).join(" "))}</p></div>`).join("")
    || `<p class="muted">No posts yet. New ideas arrive every morning at 8am (Bangladesh).</p>`;
  const auto = d.autopost ? `<span class="pill on">Auto-posting ON</span> photo and question posts are scheduled on your Page automatically.`
    : `<span class="pill off">Auto-posting OFF</span> press "Connect Facebook Page" below to switch it on.`;
  return `<h2 id="facebook">Facebook page · USA</h2>
<p class="muted">Daily posts for your monetized Page, written for US viewers and timed for US Eastern. ${auto}
Reels are not auto-posted: make the video from the script and post it yourself (original video earns most). ${d.date ? "Updated " + bdTime(d.created) + "." : ""}</p>
${fbConnectHtml(fp || {})}${planHtml}<div class="grid">${posts}</div>
<p><a class="btn" href="https://business.facebook.com/latest/content_calendar" target="_blank" rel="noopener">Meta Business Suite planner ↗</a>
<a class="btn" href="https://www.facebook.com/professional_dashboard/monetization" target="_blank" rel="noopener">Monetization ↗</a></p>`;
}
