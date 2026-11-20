// GET /admin  -> channel dashboard (sign in with Google first)
import { channelList, esc, getState, html, session } from "../../lib/dashboard.js";
import { getPins } from "../../lib/pins.js";
import { getDrafts } from "../../lib/drafts.js";
import { getIdeas, getIdeasRequest } from "../../lib/ideas.js";

const CSS = `
:root{--bg:#f4f5fb;--ink:#151827;--muted:#646b82;--line:#e3e6f0;--card:#fff;--soft:#f8f9fd;
--accent:#6d28d9;--accent2:#db2777;--ok:#059669;--bad:#dc2626;--warn:#d97706;
--grad:linear-gradient(135deg,#6d28d9 0%,#db2777 55%,#f59e0b 100%);--shadow:0 1px 2px rgba(20,24,40,.06),0 8px 24px rgba(20,24,40,.06)}
@media (prefers-color-scheme:dark){:root{--bg:#0e1018;--ink:#eceef6;--muted:#9aa1b8;--line:#262a3a;--card:#161926;--soft:#1b1f2e;
--accent:#a78bfa;--accent2:#f472b6;--ok:#34d399;--bad:#f87171;--warn:#fbbf24;--shadow:0 1px 2px rgba(0,0,0,.4),0 8px 24px rgba(0,0,0,.35)}}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:70px}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
a{color:var(--accent)}main{max-width:1100px;margin:0 auto;padding:0 18px 70px}
.muted{color:var(--muted)}
.hero{background:var(--grad);color:#fff;border-radius:0 0 22px 22px;padding:18px 22px 14px;margin:0 -18px 0;box-shadow:var(--shadow);position:relative;overflow:hidden}
.hero:after{content:"";position:absolute;right:-60px;top:-60px;width:240px;height:240px;border-radius:50%;background:rgba(255,255,255,.12)}
.hero h1{font-size:24px;margin:0 0 2px;letter-spacing:-.02em}.hero p{margin:0;opacity:.92}.hero a{color:#fff;font-weight:700}
.hero .bar{margin:10px 0 0}.hero .stat{padding:6px 14px}.hero .stat b{font-size:19px}.hero .stat{background:rgba(255,255,255,.16);border:1px solid rgba(255,255,255,.28);color:#fff;backdrop-filter:blur(6px)}
.hero .stat .muted{color:rgba(255,255,255,.85)}
.nav{position:sticky;top:0;z-index:10;display:flex;gap:6px;overflow-x:auto;padding:12px 0;margin-bottom:6px;background:color-mix(in srgb,var(--bg) 88%,transparent);backdrop-filter:blur(10px)}
.nav a{white-space:nowrap;text-decoration:none;font-weight:700;font-size:13px;color:var(--ink);background:var(--card);border:1px solid var(--line);border-radius:999px;padding:7px 14px;box-shadow:var(--shadow)}
.nav a:hover{border-color:var(--accent);color:var(--accent)}
.nav a.active{background:var(--grad);color:#fff;border-color:transparent}
.tab{display:none;animation:fade .18s ease}.tab.active{display:block}.tab h2{margin-top:8px}
@keyframes fade{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}
h1{font-size:26px;margin:0 0 4px;letter-spacing:-.02em}
h2{--c:var(--accent);font-size:22px;margin:44px 0 6px;letter-spacing:-.01em;display:flex;align-items:center;gap:10px}
h2:before{content:"";width:10px;height:28px;border-radius:6px;background:var(--c);box-shadow:0 0 0 4px color-mix(in srgb,var(--c) 18%,transparent)}
h2#channels{--c:#ef4444}h2#facebook{--c:#1877f2}h2#pins{--c:#e60023}h2#drafts{--c:#10b981}h2#ideas{--c:#8b5cf6}h2#magnific-tool{--c:#f59e0b}
.bar{display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:space-between;margin:16px 0}
.stats{display:flex;gap:10px;flex-wrap:wrap}
.stat{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:10px 16px;min-width:130px;box-shadow:var(--shadow)}
.stat b{display:block;font-size:24px;line-height:1.2}
.msg{background:color-mix(in srgb,var(--accent) 7%,var(--card));border:1px solid color-mix(in srgb,var(--accent) 25%,var(--line));border-left:5px solid var(--accent);border-radius:12px;padding:11px 15px;margin:12px 0}
table{width:100%;border-collapse:separate;border-spacing:0;background:var(--card);border:1px solid var(--line);border-radius:16px;overflow:hidden;box-shadow:var(--shadow)}
th,td{padding:11px 13px;border-top:1px solid var(--line);text-align:left;vertical-align:middle}
th{border-top:0;font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);background:var(--soft)}
tbody tr:hover{background:color-mix(in srgb,var(--accent) 5%,transparent)}
td b{background:color-mix(in srgb,#ef4444 12%,transparent);color:#ef4444;border-radius:7px;padding:2px 7px;font-size:12px}
.pill{display:inline-block;border-radius:999px;padding:3px 11px;font-size:12px;font-weight:800;letter-spacing:.01em}
.on{background:color-mix(in srgb,var(--ok) 16%,transparent);color:var(--ok)}
.off{background:color-mix(in srgb,var(--muted) 16%,transparent);color:var(--muted)}
.err{background:color-mix(in srgb,var(--bad) 16%,transparent);color:var(--bad)}
.hero .pill.on{background:#fff;color:var(--ok)}
button,.btn{font:inherit;font-weight:700;font-size:13px;border-radius:10px;padding:8px 13px;border:1px solid var(--line);background:var(--card);color:var(--ink);cursor:pointer;text-decoration:none;display:inline-block;margin:2px 0;transition:transform .08s,box-shadow .15s,border-color .15s}
button:hover,.btn:hover{border-color:var(--accent);box-shadow:0 4px 14px color-mix(in srgb,var(--accent) 22%,transparent);transform:translateY(-1px)}
.primary{background:var(--grad);color:#fff;border-color:transparent}
.hero .primary,.hero button{background:#fff;color:#6d28d9;border-color:#fff}
.danger{color:var(--bad);border-color:color-mix(in srgb,var(--bad) 35%,var(--line))}
.hero .danger{background:rgba(255,255,255,.95);color:#dc2626}
form{display:inline}
details.draft{background:var(--card);border:1px solid var(--line);border-left:5px solid #10b981;border-radius:14px;padding:12px 15px;margin:10px 0;box-shadow:var(--shadow)}
details.draft summary{cursor:pointer;font-weight:700}
.preview{border-top:1px solid var(--line);margin-top:10px;padding-top:6px}
.preview h1{font-size:22px}.preview h2{font-size:18px;margin:16px 0 4px}.preview h2:before{display:none}.preview h3{font-size:15px;color:var(--muted)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px;margin:14px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:14px 16px;box-shadow:var(--shadow);position:relative;overflow:hidden}
.card:before{content:"";position:absolute;left:0;top:0;right:0;height:4px;background:var(--grad)}
.card h3{margin:6px 0 6px;font-size:16px}
.prompt{font-size:13px;background:var(--soft);border:1px dashed var(--line);border-radius:10px;padding:9px;margin:8px 0;white-space:pre-wrap}
.row{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0;align-items:center}
input[type=text],input[type=file],select,textarea{font:inherit;border:1px solid var(--line);border-radius:10px;padding:7px 10px;background:var(--card);color:var(--ink)}
.signin{max-width:440px;margin:12vh auto;text-align:center;background:var(--card);border:1px solid var(--line);border-radius:22px;padding:34px 28px;box-shadow:var(--shadow)}
.signin .logo{width:64px;height:64px;border-radius:18px;background:var(--grad);margin:0 auto 14px;display:grid;place-items:center;color:#fff;font-size:30px;font-weight:900}
.chans{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:8px;margin:10px 0}
.chan{background:var(--card);border:1px solid var(--line);border-left:4px solid #ef4444;border-radius:12px;padding:7px 10px;box-shadow:var(--shadow);min-width:0}
.chan-top{display:flex;align-items:center;gap:6px}.chan-top .acts{margin-left:auto;white-space:nowrap}
.chan-name{font-weight:700;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:2px}.chan-name .muted{font-weight:400}
.chan-niche{font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.cid{background:color-mix(in srgb,#ef4444 12%,transparent);color:#ef4444;border-radius:7px;padding:1px 7px;font-size:12px}
.ico{padding:3px 8px;font-size:12px;border-radius:8px;margin:0}
.tab .grid{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(280px,320px);grid-template-columns:none;overflow-x:auto;scroll-snap-type:x mandatory;padding-bottom:8px}
.tab .grid>*{scroll-snap-align:start}
.clamp{display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;overflow:hidden;cursor:pointer}
.card.clampable{max-height:340px;overflow:hidden;cursor:pointer}.card.clampable:after{content:"▼ more";position:absolute;left:0;right:0;bottom:0;padding:18px 16px 8px;font-size:12px;font-weight:700;color:var(--accent);background:linear-gradient(transparent,var(--card) 55%)}
.card.clampable.open{max-height:none}.card.clampable.open:after{display:none}
.clamp.open{-webkit-line-clamp:unset}
.tab table:not(.keep){display:block;max-height:55vh;overflow:auto}
@media (max-width:700px){table.ch td:nth-child(2),table.ch th:nth-child(2){display:none}.hero h1{font-size:24px}.stat{min-width:0;flex:1 1 40%}}
`;

// Each section (from one <h2 id="..."> to the next) becomes a tab, so the page fits
// on one screen: the nav buttons switch sections instead of scrolling down.
function tabify(body) {
  if (!body.includes('class="nav"')) return body;
  const parts = body.split('<h2 id="');
  return parts[0] + parts.slice(1).map((p) => {
    const id = p.slice(0, p.indexOf('"'));
    return `<section class="tab" data-tab="${id}"><h2 id="${p}</section>`;
  }).join("");
}

const TABS_JS = `<script>
(function(){
  var tabs=[].slice.call(document.querySelectorAll('.tab')), links=[].slice.call(document.querySelectorAll('.nav a'));
  function show(id){
    if(!tabs.some(function(t){return t.dataset.tab===id})) id=tabs.length?tabs[0].dataset.tab:'';
    tabs.forEach(function(t){t.classList.toggle('active',t.dataset.tab===id)});
    links.forEach(function(a){a.classList.toggle('active',a.getAttribute('href')==='#'+id)});
  }
  links.forEach(function(a){a.addEventListener('click',function(e){e.preventDefault();var id=a.getAttribute('href').slice(1);
    history.replaceState(null,'','#'+id);show(id);window.scrollTo(0,0);});});
  window.addEventListener('hashchange',function(){show(location.hash.slice(1))});
  show(location.hash.slice(1));
  // keep each tab short: long intros show 2 lines, tall cards fold, click to open
  document.querySelectorAll('.tab > p.muted').forEach(function(p){ if(p.textContent.length>140){p.classList.add('clamp');p.title='Click to read more';p.addEventListener('click',function(){p.classList.toggle('open')});}});
  document.querySelectorAll('.tab .grid > .card').forEach(function(c){ if(c.scrollHeight>360){c.classList.add('clampable');c.addEventListener('click',function(e){if(e.target.closest('a,button,input,select,textarea,label'))return;c.classList.toggle('open')});}});
})();
</script>`;

function page(body) {
  body = tabify(body);
  return `<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex">
<title>Pickixo · Dashboard</title><style>${CSS}</style></head><body><main>${body}</main>${body.includes('class="tab"') ? TABS_JS : ""}</body></html>`;
}

export async function onRequestGet(context) {
  const msg = new URL(context.request.url).searchParams.get("msg");
  const note = msg ? `<div class="msg">${esc(msg)}</div>` : "";
  const s = await session(context);
  if (!s) {
    return html(page(`<div class="signin"><div class="logo">P</div><h1>Pickixo dashboard</h1>
<p class="muted">Sign in with the owner Google account to manage channels, posts and tools.</p>
${note}<p><a class="btn primary" href="/auth/login">Sign in with Google</a></p></div>`));
  }

  const [chans, st, pins, drafts, ideas, ideasReq] = await Promise.all([channelList(context), getState(context.env), getPins(context.env), getDrafts(context.env), getIdeas(context.env), getIdeasRequest(context.env)]);
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
      actions = `<a class="btn primary ico" href="/auth/connect?ch=${esc(c.id)}">Connect</a>`;
    } else {
      connected++;
      if (info.error) errors++;
      if (info.enabled && !info.error) active++;
      status = info.error
        ? `<span class="pill err" title="${esc(info.error)}">Needs reconnect</span>`
        : info.enabled ? `<span class="pill on">Active</span>` : `<span class="pill off">Paused</span>`;
      const toggle = info.enabled ? "disable" : "enable";
      actions = `<form method="post" action="/admin/action"><input type="hidden" name="ch" value="${esc(c.id)}">
<button class="ico" title="${info.enabled ? "Pause" : "Resume"}" name="do" value="${toggle}">${info.enabled ? "⏸" : "▶"}</button></form>
<a class="btn ico" title="Reconnect" href="/auth/connect?ch=${esc(c.id)}">↻</a>
<form method="post" action="/admin/action" onsubmit="return confirm('Disconnect ${esc(c.id)}?')">
<input type="hidden" name="ch" value="${esc(c.id)}"><button class="danger ico" title="Disconnect" name="do" value="disconnect">✕</button></form>`;
    }
    const yt = info ? `<a href="https://www.youtube.com/channel/${esc(info.youtube_id)}" target="_blank" rel="noopener">${esc(info.title)}</a> <span class="muted">${esc(info.handle)}</span>` : `<span class="muted">—</span>`;
    return `<div class="chan"><div class="chan-top"><b class="cid">${esc(c.id)}</b>${status}<span class="acts">${actions}</span></div>
<div class="chan-name">${yt}</div><div class="muted chan-niche">${esc(c.niche)}</div></div>`;
  }).join("");

  const pauseBtn = st.paused
    ? `<button class="primary" name="do" value="resume_all">▶ Resume all</button>`
    : `<button class="danger" name="do" value="pause_all">■ Pause all uploads</button>`;

  return html(page(`<header class="hero"><h1>Pickixo dashboard</h1>
<p>Signed in as ${esc(s.email)} · <a href="/auth/logout">Sign out</a></p>
<div class="bar"><div class="stats">
<div class="stat"><span class="muted">Connected</span><b>${connected} / ${chans.length}</b></div>
<div class="stat"><span class="muted">Uploading</span><b>${st.paused ? 0 : active}</b></div>
<div class="stat"><span class="muted">Need attention</span><b>${errors}</b></div>
<div class="stat"><span class="muted">All uploads</span><b>${st.paused ? "Paused" : "On"}</b></div></div>
<form method="post" action="/admin/action">${pauseBtn}</form></div></header>
<nav class="nav"><a href="#channels">▶ YouTube</a><a href="#facebook">f Facebook</a><a href="#pins">📌 Pinterest</a><a href="#drafts">✍ Medium</a><a href="#ideas">✨ Image ideas</a><a href="#magnific-tool">🛠 Magnific tool</a></nav>
${note}<h2 id="channels">YouTube channels</h2>
<p>🤖 <a href="https://claude.ai/code/routines/trig_01671Hhho11hhREEtgihzqsA" target="_blank" rel="noopener">Claude daily review</a> <span class="muted">· checks the report every day at 9pm (Bangladesh) and opens a PR if something needs fixing</span></p>
<div class="chans">${rows}</div>
<p class="muted">Connect: pick the Google account, then the exact YouTube channel for that niche, and allow.
If Google shows “hasn't verified this app”, choose Advanced → Go to Pickixo Shorts Uploader.</p>
${fbSection(fb, fbPlan, fbPages)}${pinsSection(pins)}${draftsSection(drafts)}${ideasSection(ideas, ideasReq)}${magnificToolSection()}`));
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
  return `<h2 id="pins">Pinterest · AliExpress</h2>
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

function ideasSection(d, req) {
  const button = req
    ? `<div class="msg">⏳ Requested ${bdTime(req.at)}. New prompts arrive in about 10-15 minutes; refresh this page.
<form method="post" action="/admin/action" style="display:inline"><button name="do" value="ideas_cancel">Cancel</button></form></div>`
    : `<form method="post" action="/admin/action" onsubmit="return confirm('Make 10 new prompts now? This uses the OpenAI API (small cost).')">
<button name="do" value="ideas_request">✨ Make new prompts (uses API)</button></form>`;
  const tools = FREE_TOOLS.map(([n, u, t]) =>
    `<div class="card"><h3><a href="${u}" target="_blank" rel="noopener">${esc(n)} ↗</a></h3><p class="muted">${esc(t)}</p></div>`).join("");
  const cards = (d.ideas || []).map((i, n) => `<div class="card">
<span class="pill ${i.kind === "seasonal" ? "on" : "off"}">${esc(i.kind)}</span> <span class="muted">${esc(i.aspect)} · ${esc(i.best_tool)}</span>
<h3>${esc(i.theme)}</h3><p class="muted">${esc(i.why)}</p>
<div class="prompt" id="idea-${n}">${esc(i.prompt)}</div>
<div class="row"><button type="button" onclick="copyText('idea-${n}')">📋 Copy prompt</button></div>
<p class="muted"><b>Check:</b> ${esc(i.avoid)}</p>
<p class="muted"><b>Keywords:</b> ${esc((i.keywords || []).join(", "))}</p></div>`).join("")
    || `<p class="muted">No ideas yet. Press the button to make some.</p>`;
  return `<h2 id="ideas">Magnific · Image ideas</h2>
<p class="muted">Made only when you press the button: no button, no API cost. Seasonal ideas are for events 3-8 weeks ahead, because buyers download early.
${d.date ? "Updated " + bdTime(d.created) + "." : ""} ${esc(d.season_note || "")}</p>
${button}
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
