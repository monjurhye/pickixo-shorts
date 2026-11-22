// GET /admin  -> channel dashboard (sign in with Google first)
import { channelList, esc, getState, html, session } from "../../lib/dashboard.js";
import { getPins } from "../../lib/pins.js";
import { getDrafts } from "../../lib/drafts.js";
import { getIdeas, getIdeasRequest } from "../../lib/ideas.js";
import { getEarnings, postbackToken } from "../../lib/earnings.js";
import { getXp, getXpReport } from "../../lib/xpost.js";
import { mtlPage } from "../../lib/mtl.js";
import { getAdminProducts } from "../../lib/products.js";

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
.hero{background:var(--grad);color:#fff;border-radius:0 0 20px 20px;padding:12px 20px 12px;margin:0 -18px 0;box-shadow:var(--shadow);position:relative;overflow:hidden}
.hero:after{content:"";position:absolute;right:-60px;top:-60px;width:240px;height:240px;border-radius:50%;background:rgba(255,255,255,.12)}
.hero h1{font-size:21px;margin:0 0 2px;letter-spacing:-.02em}.hero p{margin:0;opacity:.92}.hero a{color:#fff;font-weight:700}
.hero .bar{margin:8px 0 0}.hero .stat{padding:4px 12px;min-width:110px;box-shadow:none}.hero .stat b{font-size:17px}.hero .stat .muted{font-size:12px}.hero .stat{background:rgba(255,255,255,.16);border:1px solid rgba(255,255,255,.28);color:#fff;backdrop-filter:blur(6px)}
.hero .stat .muted{color:rgba(255,255,255,.85)}
.nav{position:sticky;top:0;z-index:10;display:flex;gap:6px;overflow-x:auto;padding:12px 0;margin-bottom:6px;background:color-mix(in srgb,var(--bg) 88%,transparent);backdrop-filter:blur(10px)}
.nav a{white-space:nowrap;text-decoration:none;font-weight:700;font-size:13px;color:var(--ink);background:var(--card);border:1px solid var(--line);border-radius:999px;padding:7px 14px;box-shadow:var(--shadow)}
.nav a:hover{border-color:var(--accent);color:var(--accent)}
.nav a.active{background:var(--grad);color:#fff;border-color:transparent}
.tab{display:none;animation:fade .18s ease}.tab.active{display:block}.tab h2{margin-top:8px}
@keyframes fade{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}
h1{font-size:26px;margin:0 0 4px;letter-spacing:-.02em}
h2{--c:var(--accent);font-size:20px;margin:44px 0 4px;letter-spacing:-.01em;display:flex;align-items:center;gap:10px}
h2:before{content:"";width:10px;height:28px;border-radius:6px;background:var(--c);box-shadow:0 0 0 4px color-mix(in srgb,var(--c) 18%,transparent)}
h2#channels{--c:#ef4444}h2#facebook{--c:#1877f2}h2#pins{--c:#e60023}h2#drafts{--c:#10b981}h2#ideas{--c:#8b5cf6}h2#magnific-tool{--c:#f59e0b}h2#play{--c:#01875f}h2#earnings{--c:#16a34a}
.money{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px;margin:10px 0}
.money .card h3{margin:2px 0 6px;font-size:13px;color:var(--muted);text-transform:uppercase;letter-spacing:.05em}
.money .big{font-size:26px;font-weight:800}.pos{color:var(--ok)}.neg{color:var(--bad)}
.money .sub{font-size:12px;color:var(--muted)}
.ef{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:6px 0}.ef input,.ef select{padding:6px 8px;font-size:13px}.ef input[type=number]{width:100px}h2#ios{--c:#0a84ff}
.apps{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:10px;margin:10px 0}
a.applink{text-decoration:none;color:var(--ink);display:block;transition:transform .08s,border-color .15s}a.applink:hover{transform:translateY(-2px);border-color:var(--accent)}
a.applink h3{color:var(--accent);margin:4px 0 2px;font-size:15px}a.applink p{margin:0;font-size:13px}
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
details.idea{border:1px solid var(--line);border-left:5px solid #01875f;border-radius:12px;padding:10px 14px;margin:10px 0;background:var(--soft)}
details.idea summary{cursor:pointer}
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
.tab > .card{display:inline-block;vertical-align:top;width:calc(50% - 6px);margin:6px 8px 6px 0}.tab > .card + .card{margin-right:0}
.tab > .card.clampable{max-height:200px}.tab > .card:only-of-type{display:block;width:auto;margin:8px 0}
.card.clampable{max-height:280px;overflow:hidden;cursor:pointer}.card.clampable:after{content:"▼ more";position:absolute;left:0;right:0;bottom:0;padding:18px 16px 8px;font-size:12px;font-weight:700;color:var(--accent);background:linear-gradient(transparent,var(--card) 55%)}
.card.clampable.open{max-height:none}.card.clampable.open:after{display:none}
.clamp.open{-webkit-line-clamp:unset}
.tab table:not(.keep){display:block;max-height:55vh;overflow:auto}
@media (max-width:800px){.tab > .card{display:block;width:auto;margin:8px 0}}
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
    // fold tall cards of the visible tab (heights are only known once it is shown)
    var t=tabs.filter(function(x){return x.dataset.tab===id})[0];
    if(t) [].slice.call(t.querySelectorAll('.grid > .card, .tab > .card')).forEach(function(c){
      if(c.dataset.fold||c.querySelector('form')||c.scrollHeight<=(c.parentNode.classList.contains('tab')?210:290)||c.querySelector('input[type=file]'))return; c.dataset.fold='1';
      c.classList.add('clampable');c.addEventListener('click',function(e){if(e.target.closest('a,button,input,select,textarea,label'))return;c.classList.toggle('open')});});
  }
  links.forEach(function(a){a.addEventListener('click',function(e){e.preventDefault();var id=a.getAttribute('href').slice(1);
    history.replaceState(null,'','#'+id);show(id);window.scrollTo(0,0);});});
  window.addEventListener('hashchange',function(){show(location.hash.slice(1))});
  show(location.hash.slice(1));
  // keep each tab short: long intros show 2 lines, tall cards fold, click to open
  document.querySelectorAll('.tab > p, .tab > .msg').forEach(function(p){ if(p.textContent.length>160 && !p.querySelector('form,input,button')){p.classList.add('clamp');p.title='Click to read more';p.addEventListener('click',function(){p.classList.toggle('open')});}});
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

  const [chans, st, pins, drafts, ideas, ideasReq, earn, xp, xpRep, mtlRaw, mtlP] = await Promise.all([channelList(context), getState(context.env), getPins(context.env), getDrafts(context.env), getIdeas(context.env), getIdeasRequest(context.env), getEarnings(context.env), getXp(context.env), getXpReport(context.env), context.env.CHANNELS_KV.get("mtl"), mtlPage(context.env)]);
  const appIdeas = await context.env.CHANNELS_KV.get("app_ideas");
  const adminProducts = await getAdminProducts(context.env);
  const vr = await context.env.ASSETS.fetch(new URL("/videos-index.json", context.request.url));
  const videoIndex = vr.ok ? await vr.json().catch(() => []) : [];
  const fbPagesRaw = await context.env.CHANNELS_KV.get("fbpages");
  const fbPages = fbPagesRaw ? JSON.parse(fbPagesRaw) : { pages: [] };
  const fbRaw = await context.env.CHANNELS_KV.get("fb");
  const fb = fbRaw ? JSON.parse(fbRaw) : { posts: [] };
  // drafts that lost their blog link (e.g. sent before the dashboard knew the field): match by title
  try {
    const br = await context.env.ASSETS.fetch(new URL("/blog/index.json", context.request.url));
    if (br.ok) {
      const posts = await br.json();
      for (const x of drafts.items || []) {
        if (!x.blog_url) { const m = posts.find((p) => p.title === x.title); if (m) x.blog_url = m.url; }
      }
    }
  } catch (e) { /* no blog yet */ }
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
<nav class="nav"><a href="#channels">▶ YouTube</a><a href="#facebook">f Facebook</a><a href="#xpost">🔁 Cross-post</a><a href="#mtl">🇧🇩 Modern Tech Life</a><a href="#pins">📌 Pinterest</a><a href="#drafts">✍ Medium</a><a href="#products">🛒 Products</a><a href="#ideas">✨ Image ideas</a><a href="#magnific-tool">🛠 Magnific tool</a><a href="#play">▶ Play Console</a><a href="#ios"> iOS</a><a href="#earnings">💰 Earnings</a></nav>
${note}<h2 id="channels">YouTube channels</h2>
<p>🤖 <a href="https://claude.ai/code/routines/trig_01671Hhho11hhREEtgihzqsA" target="_blank" rel="noopener">Claude daily review</a> <span class="muted">· checks the report every day at 9pm (Bangladesh) and opens a PR if something needs fixing</span></p>
<div class="chans">${rows}</div>
<p class="muted">Connect: pick the Google account, then the exact YouTube channel for that niche, and allow.
If Google shows “hasn't verified this app”, choose Advanced → Go to Pickixo Shorts Uploader.</p>
${fbSection(fb, fbPlan, fbPages)}${xpostSection(xp, xpRep)}${mtlSection(mtlRaw ? JSON.parse(mtlRaw) : null, mtlP)}${pinsSection(pins)}${draftsSection(drafts)}${productsSection(adminProducts, chans, videoIndex)}${ideasSection(ideas, ideasReq)}${magnificToolSection(ideas)}${appsSection(appIdeas ? JSON.parse(appIdeas) : [])}${earningsSection(earn, new URL(context.request.url).origin + "/api/postback/adbluemedia?k=" + (context.env.PIPELINE_KEY ? await postbackToken(context.env, "adbluemedia") : ""))}`));
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

// Older drafts carried "reviewed and edited by the author"; nobody reviews them now.
function fixNote(t) {
  return String(t || "").replace("This article was drafted with AI assistance and reviewed and edited by the author.",
    "This article was written with AI assistance from the deal information AppSumo publishes. Check each deal page for current terms before you buy.");
}

const INCOME_SOURCES = ["Amazon Associates", "AdBlueMedia", "Magnific", "Facebook", "YouTube",
  "Google Play", "App Store", "AliExpress", "AppSumo (Impact)", "Other"];
const COST_ITEMS = ["OpenAI API", "Domain / hosting", "Buffer", "Tools / software", "Ads", "Other"];
const REPORTS = [
  ["Amazon Associates", "https://affiliate-program.amazon.com/home/reports"],
  ["AliExpress", "https://portals.aliexpress.com/affiportals/web/report.htm"],
  ["AppSumo (Impact)", "https://app.impact.com/"],
  ["AdBlueMedia", "https://www.adbluemedia.com/"],
  ["Magnific", "https://contributor.magnific.com/dashboard"],
  ["Facebook", "https://www.facebook.com/professional_dashboard/monetization"],
  ["YouTube", "https://studio.youtube.com/"],
  ["Google Play", "https://play.google.com/console/developers/payments"],
  ["App Store", "https://appstoreconnect.apple.com/trends"],
  ["OpenAI cost", "https://platform.openai.com/usage"],
];

// Revenue (automatic + typed), costs (typed + monthly fixed spread over the days) and profit.
function earningsSection(e, abmUrl) {
  const bd = (d) => new Date(d.getTime() + 6 * 3600e3).toISOString().slice(0, 10);   // Bangladesh date
  const today = bd(new Date());
  const dayAdd = (s, n) => bd(new Date(Date.parse(s + "T00:00:00Z") - 6 * 3600e3 + n * 864e5));
  const inc = {}, cost = {};
  const add = (map, day, key, v) => { (map[day] = map[day] || {})[key] = ((map[day] || {})[key] || 0) + v; };
  for (const [day, srcs] of Object.entries(e.auto.days || {})) for (const [k, v] of Object.entries(srcs)) add(inc, day, k, v);
  for (const [day, srcs] of Object.entries(e.postback.days || {})) for (const [k, v] of Object.entries(srcs)) add(inc, day, k, v);
  for (const [day, items] of Object.entries(e.auto.costs || {})) for (const [k, v] of Object.entries(items)) add(cost, day, k, v);
  for (const x of e.manual.income) add(inc, x.date, x.source, x.amount);
  for (const x of e.manual.costs) add(cost, x.date, x.item, x.amount);
  const monthlyTotal = e.manual.monthly.reduce((a, x) => a + x.amount, 0);
  const dailyFixed = (day) => monthlyTotal / new Date(Date.UTC(+day.slice(0, 4), +day.slice(5, 7), 0)).getUTCDate();
  const sum = (o) => Object.values(o || {}).reduce((a, v) => a + v, 0);
  const period = (from, to) => {
    let i = 0, c = 0; const by = {};
    for (let d = from; d <= to; d = dayAdd(d, 1)) {
      i += sum(inc[d]); c += sum(cost[d]) + dailyFixed(d);
      for (const [k, v] of Object.entries(inc[d] || {})) by[k] = (by[k] || 0) + v;
    }
    return { i, c, p: i - c, by };
  };
  const $ = (v) => (v < 0 ? "-$" : "$") + Math.abs(v).toFixed(2);
  const monthStart = today.slice(0, 8) + "01";
  const P = [["Today", today, today], ["Yesterday", dayAdd(today, -1), dayAdd(today, -1)],
    ["Last 7 days", dayAdd(today, -6), today], ["This month", monthStart, today]].map(([n, a, b]) => [n, period(a, b)]);
  const tiles = P.map(([n, r]) => `<div class="card"><h3>${n}</h3><div class="big ${r.p >= 0 ? "pos" : "neg"}">${$(r.p)}</div>
<div class="sub">Income ${$(r.i)} · Cost ${$(r.c)}</div></div>`).join("");
  const month = P[3][1];
  const srcRows = Object.entries(month.by).sort((a, b) => b[1] - a[1])
    .map(([k, v]) => `<tr><td>${esc(k)}</td><td>${$(v)}</td></tr>`).join("") || `<tr><td colspan="2" class="muted">No income recorded this month yet.</td></tr>`;
  let days = "";
  for (let n = 0; n < 14; n++) {
    const d = dayAdd(today, -n), i = sum(inc[d]), c = sum(cost[d]) + dailyFixed(d);
    days += `<tr><td>${d}</td><td>${$(i)}</td><td>${$(c)}</td><td class="${i - c >= 0 ? "pos" : "neg"}"><b>${$(i - c)}</b></td></tr>`;
  }
  const opt = (list) => list.map((x) => `<option>${esc(x)}</option>`).join("");
  const del = (kind, x, label) => `<form method="post" action="/admin/action"><input type="hidden" name="kind" value="${kind}">
<input type="hidden" name="id" value="${esc(x.id)}"><button class="danger ico" name="do" value="earn_del" title="Remove">✕</button></form> ${label}`;
  const recent = e.manual.income.slice(0, 6).map((x) => `<div>${del("income", x, `${esc(x.date)} · ${esc(x.source)} · <b>${$(x.amount)}</b> ${esc(x.note || "")}`)}</div>`).join("")
    + e.manual.costs.slice(0, 6).map((x) => `<div>${del("costs", x, `${esc(x.date)} · cost: ${esc(x.item)} · <b>${$(x.amount)}</b> ${esc(x.note || "")}`)}</div>`).join("");
  const monthly = e.manual.monthly.map((x) => `<div>${del("monthly", x, `${esc(x.item)} · <b>${$(x.amount)}</b>/month`)}</div>`).join("");
  const links = REPORTS.map(([n, u]) => `<a class="btn ico" href="${u}" target="_blank" rel="noopener">${esc(n)} ↗</a>`).join(" ");
  return `<h2 id="earnings">Earnings · cost · profit</h2>
<p class="muted">Bangladesh dates, US dollars. Automatic: AppSumo (Impact), AliExpress, OpenAI/Anthropic cost${e.auto.updated ? " (last update " + bdTime(e.auto.updated) + ")" : ""}
and AdBlueMedia (instantly, by postback${e.postback.last.AdBlueMedia ? ", last lead " + bdTime(e.postback.last.AdBlueMedia) : ""}).
Amazon, Magnific and Facebook have no API, so type those below. Monthly fixed costs are spread over the days.</p>
<div class="money">${tiles}</div>
<div class="card"><h3>Add income</h3><form method="post" action="/admin/action" class="ef">
<input type="date" name="date" value="${today}"><select name="source">${opt(INCOME_SOURCES)}</select>
<input type="number" name="amount" step="0.01" min="0" placeholder="$ amount" required><input type="text" name="note" placeholder="note (optional)">
<button class="primary" name="do" value="earn_add">Add</button></form>
<h3>Add cost</h3><form method="post" action="/admin/action" class="ef">
<input type="date" name="date" value="${today}"><select name="item">${opt(COST_ITEMS)}</select>
<input type="number" name="amount" step="0.01" min="0" placeholder="$ amount" required><input type="text" name="note" placeholder="note (optional)">
<button name="do" value="cost_add">Add cost</button></form>
<h3>Monthly fixed cost</h3><form method="post" action="/admin/action" class="ef">
<select name="item">${opt(COST_ITEMS)}</select><input type="number" name="amount" step="0.01" min="0" placeholder="$ per month" required>
<button name="do" value="monthly_add">Add monthly</button></form>${monthly}${recent ? "<h3>Recent entries</h3>" + recent : ""}</div>
<div class="card"><h3>This month by source</h3><table class="keep"><tbody>${srcRows}</tbody></table>
<h3>Last 14 days</h3><table class="keep"><thead><tr><th>Date</th><th>Income</th><th>Cost</th><th>Profit</th></tr></thead><tbody>${days}</tbody></table></div>
<p class="muted">${(e.auto.notes || []).map(esc).join(" · ")}</p>
<div class="card"><h3>AdBlueMedia postback (one-time setup)</h3>
<p class="muted">AdBlueMedia → Tools / Postback → paste this URL. Keep it private (it contains a secret key).
If their payout or lead-id macro has a different name, change only the part in { }.</p>
<input type="text" readonly onclick="this.select()" style="width:100%" value="${esc(abmUrl + "&payout={payout}&id={lead_id}")}"></div>
<div class="row">${links}</div>`;
}

function draftsSection(d) {
  const items = (d.items || []).map((x) => {
    const pill = x.status === "published" ? `<span class="pill off">Published</span>` : `<span class="pill on">New</span>`;
    const toggle = x.status === "published"
      ? `<button name="do" value="draft_new">Mark as new</button>`
      : `<button class="primary" name="do" value="draft_done">Mark published</button>`;
    return `<details class="draft"><summary>${pill} ${esc(x.title)} <span class="muted">· ${bdTime(x.created)} · ${esc((x.products || []).join(", "))}</span></summary>
<div class="row">
${x.blog_url ? `<a class="btn" href="${esc(x.blog_url)}" target="_blank" rel="noopener">🌐 On the blog ↗</a>
<a class="btn primary" href="https://medium.com/p/import" target="_blank" rel="noopener" onclick="navigator.clipboard&&navigator.clipboard.writeText('${esc(x.blog_url)}')">⬇ Import to Medium (link copied)</a>` : ""}
<button type="button" onclick="copyDraft('${esc(x.id)}')">📋 Copy article</button>
<button type="button" onclick="copyText('${esc(x.id)}-tags')">🏷 Copy tags</button>
<a class="btn" href="https://medium.com/new-story" target="_blank" rel="noopener">✍ Open Medium editor</a>
<form method="post" action="/admin/action"><input type="hidden" name="id" value="${esc(x.id)}">${toggle}
<button class="danger" name="do" value="draft_delete" onclick="return confirm('Delete this draft?')">Delete</button></form></div>
<p class="muted">Tags: <span id="${esc(x.id)}-tags">${esc((x.tags || []).join(", "))}</span></p>
<div class="preview" id="${esc(x.id)}-html">${fixNote(x.html)}</div>
<textarea id="${esc(x.id)}-md" hidden>${esc(fixNote(x.markdown))}</textarea></details>`;
  }).join("") || `<p class="muted">No drafts yet. A new one is made every day at 3pm (Bangladesh).</p>`;
  const err = d.last_error ? `<div class="msg">${esc(d.last_error)}</div>` : "";
  return `<h2 id="drafts">Medium · AppSumo + AdBlueMedia</h2>
<p class="muted">Two articles a day: one from real AppSumo deal data (Impact, sub id <b>medium</b>), published automatically on
<a href="/blog/" target="_blank" rel="noopener">shop.pickixo.com/blog</a> and one how-to (AI stock images / iOS without a Mac) that offers the AdBlueMedia free pack or ebook at the end.
Both are sent to Google/Bing. For Medium (no API): press
<b>Import to Medium</b>, paste the copied link (Cmd+V), Import, add the tags, publish, then <b>Mark published</b>.</p>
<div class="card"><h3>🔓 AI prompt pack (AdBlueMedia locker)</h3>
<p><a href="/free/ai-prompts/" target="_blank" rel="noopener">shop.pickixo.com/free/ai-prompts/</a> · up to 100 stock-image prompts,
4 more each time you press <b>Make new prompts</b>. 5 are open; the full pack (/free/ai-prompts/full/) opens after the visitor completes one AdBlueMedia sponsor offer.</p>
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
async function copyText(id){ try{ await navigator.clipboard.writeText(document.getElementById(id).innerText); alert('Copied.'); }catch(e){ alert('Copy failed.'); } }
</script>`;
}

// 4 Amazon search ideas per channel niche (owner opens them, picks products, pastes the SiteStripe link).
const PRODUCT_KEYWORDS = {
  ch01: ["pot boil over stopper", "silicone stretch lids", "vegetable chopper", "oil sprayer for cooking"],
  ch02: ["sunset lamp", "mini waffle maker", "desk organizer gift", "cozy socks gift set"],
  ch03: ["under sink organizer", "stackable drawer organizer", "over door organizer", "clear storage bins with lids"],
  ch04: ["pet hair remover roller", "cat water fountain", "lick mat for dogs", "dog paw cleaner cup"],
  ch05: ["milk frother handheld", "cold brew maker", "electric gooseneck kettle", "loose leaf tea infuser"],
  ch06: ["drain hair catcher", "shower caddy adhesive", "toothbrush holder wall mount", "bath mat quick dry"],
  ch07: ["self watering planter", "plant grow light", "garden kneeler seat", "plant stand indoor"],
  ch08: ["electric spin scrubber", "lint remover", "collapsible laundry basket", "microfiber cleaning cloths"],
  ch09: ["heatless curling rod", "makeup organizer", "lighted makeup mirror", "makeup brush cleaner"],
  ch10: ["resistance bands set", "yoga mat thick", "ab roller wheel", "adjustable jump rope"],
  ch11: ["silicone bib", "toddler tower", "baby bath seat", "suction plates for toddlers"],
  ch12: ["car seat gap filler", "car trash can", "magnetic phone mount car", "car seat organizer"],
  ch13: ["rechargeable camping lantern", "camping hammock", "collapsible water container", "camping headlamp"],
  ch14: ["monitor stand riser", "laptop stand", "desk cable management", "desk pad large"],
  ch15: ["controller charging station", "headset stand", "gaming mouse pad xl", "led light strip gaming"],
  ch16: ["smart plug", "motion sensor light indoor", "smart led strip lights", "smart light bulb"],
  ch17: ["packing cubes", "travel adapter universal", "neck pillow memory foam", "toiletry bag hanging"],
  ch18: ["magnetic tiles", "kids drawing tablet", "building blocks set", "bubble machine"],
  ch19: ["silicone baking mat", "cookie scoop set", "cake decorating kit", "silicone spatula set"],
  ch20: ["bed sheet holder straps", "sunrise alarm clock", "silk pillowcase", "bedside caddy"],
};
const amzSearch = (k) => "https://www.amazon.com/s?k=" + encodeURIComponent(k).replace(/%20/g, "+") + "&low-price=10&high-price=40";

// Amazon products the owner pastes (SiteStripe "Full link" or ASIN) -> KV "admin_products" -> videos.
function productsSection(d, chans, videos) {
  const name = (id) => { const c = chans.find((x) => x.id === id); return c ? c.niche || c.title || id : id; };
  const count = {};
  d.products.forEach((p) => p.channels.forEach((c) => { count[c] = (count[c] || 0) + 1; }));
  const boxes = chans.map((c) => `<label style="display:inline-block;margin:3px 10px 3px 0;white-space:nowrap"><input type="checkbox" name="channels" value="${esc(c.id)}">
${esc(c.id)} · ${esc(c.niche || c.title || "")} <span class="muted">(${count[c.id] || 0})</span></label>`).join("");
  const rows = d.products.map((p) => `<tr><td><a href="https://www.amazon.com/dp/${esc(p.asin)}" target="_blank" rel="noopener">${esc(p.asin)}</a></td>
<td>${esc(p.name)}</td><td>${p.channels.map((c) => `<span class="pill off" title="${esc(name(c))}">${esc(c)}</span>`).join(" ")}</td><td class="muted">${esc(p.added || "")}</td>
<td><form method="post" action="/admin/action" onsubmit="return confirm('Remove this product?')"><input type="hidden" name="asin" value="${esc(p.asin)}">
<button class="danger ico" name="do" value="prod_del" title="Remove">✕</button></form></td></tr>`).join("");
  const ideas = chans.map((c) => `<tr><td><b>${esc(c.id)}</b> <span class="muted">${esc(c.niche || "")} (${count[c.id] || 0})</span></td><td>${(PRODUCT_KEYWORDS[c.id] || [])
    .map((k) => `<a href="${amzSearch(k)}" target="_blank" rel="noopener">${esc(k)} ↗</a>`).join(" · ")}</td></tr>`).join("");
  const vids = videos || [];
  const isProduct = (i) => !!i.asin;
  const vidCards = chans.map((c) => {
    const list = vids.filter((v) => v.channel_id === c.id);
    if (!list.length) return "";
    const withP = list.filter((v) => v.items.some(isProduct)).length;
    const rows = list.map((v) => `<tr><td class="muted">${esc(v.date)}</td>
<td>${v.youtube_id ? `<a href="https://youtube.com/shorts/${esc(v.youtube_id)}" target="_blank" rel="noopener">${esc(v.title)} ↗</a>` : esc(v.title)}</td>
<td>${v.items.map((i) => `<a href="${esc(i.link)}" target="_blank" rel="noopener" title="${isProduct(i) ? "Product page" : "Amazon search"}">${isProduct(i) ? "🛒" : "🔍"} ${esc(i.name)}</a>`).join("<br>")}</td></tr>`).join("");
    return `<details class="card"><summary><b>${esc(c.id)}</b> ${esc(c.niche || "")} · <b>${list.length}</b> videos · ${withP} with product links</summary>
<table class="keep"><thead><tr><th>Date</th><th>Video</th><th>Links in the description</th></tr></thead><tbody>${rows}</tbody></table></details>`;
  }).join("");
  const totalP = vids.filter((v) => v.items.some(isProduct)).length;
  const videoBlock = `<div class="card"><h3>🎬 Videos: ${vids.length} in all · ${totalP} with product links · ${vids.length - totalP} with search links only</h3>
<p class="muted">🛒 = link to one product page · 🔍 = link to an Amazon search. Click a channel to see its videos.</p></div>${vidCards}`;
  return `<h2 id="products">Amazon products for videos</h2>
<p class="muted">Products you pick yourself. Videos use them first, so a channel with 4 or more links straight to product pages;
otherwise its videos link to an Amazon search with your tag (you still earn on anything bought). The automatic product finder is off (it cost about $4 a day).</p>
<div class="msg"><b>How:</b> 1) open a search below (already $10-40) → tick <b>4 Stars &amp; Up</b> → open a product that is not "Sponsored", rated 4.3+, 1,000+ reviews, Prime if possible, no health/medical claims;
2) SiteStripe bar at the top → <b>Get link</b> → copy the affiliate link (Short or Full, both work);
3) paste it below, write a short name (e.g. "Collapsible silicone colander"), tick the channel(s), Save. Aim for 4 per channel: one per search.</div>
<div class="card"><h3>🔍 What to search (4 per channel)</h3><table class="keep"><tbody>${ideas}</tbody></table></div>
<form method="post" action="/admin/action" class="card">
<p><input name="link" required placeholder="Affiliate link from SiteStripe (https://amzn.to/... or https://www.amazon.com/...)" style="width:100%"></p>
<p><input name="name" required maxlength="80" placeholder="Short product name" style="width:100%"></p>
<p class="muted">Channels (number = products you added):</p><div>${boxes}</div>
<p><button class="primary" name="do" value="prod_add">Save product</button></p></form>
${rows ? `<div class="card"><h3>Your products (${d.products.length})</h3><table class="keep"><thead><tr><th>ASIN</th><th>Name</th><th>Channels</th><th>Added</th><th></th></tr></thead><tbody>${rows}</tbody></table></div>`
    : `<p class="muted">No products added yet.</p>`}
${videoBlock}`;
}

const FREE_TOOLS = [
  ["Adobe Firefly", "https://firefly.adobe.com/image-generate", "Free monthly credits, commercial use. Gives about 2048×2048 directly (≈4MP), so no upscaling: best approval chance. Download the largest size."],
];

// "Write prompts with Claude": opens claude.ai with a ready request (your Claude account, no API cost).
const CLAUDE_PROMPT_REQUEST = `Today is {DATE}. I sell AI stock photos on Magnific (Freepik) to US designers and marketers.
Write exactly 4 Adobe Firefly prompts for images that get APPROVED and DOWNLOADED.

Style that gets approved (keep it for all 4): a TOP-DOWN FLAT-LAY real photograph, aspect ratio 1:1.
3 to 5 simple objects on ONE plain surface (light linen, light oak, white marble, kraft paper, plain tile),
small in the frame (about one third of the picture), ALL fully inside the frame with wide empty margins,
nothing cut off at the edges, plenty of empty space for text.

Each prompt from a DIFFERENT group:
- 2 seasonal: US holidays/events 3 to 8 weeks after today (buyers prepare early).
- 1 evergreen best-seller: blank mockups (blank greeting card + envelope, business cards, tote bag,
  folded t-shirt, gift box: "blank, no print, no text"), business/office, healthy food, beauty/spa,
  education, travel, or an empty texture background with one small object in a corner.
- 1 trend: a current colour or style (pastel, earthy neutral, Japandi) on one of those groups.

Never: text, letters, numbers, logos, brands, people, hands, glass or shiny reflective things, glossy
plastic, 3D/CGI look, tiny fiddly things (spice grains, small flowers, string, ribbon, scissors, jewelry),
needle herbs (rosemary, pine, thyme, dill), fog, steam, dim light. Use broad leaves (eucalyptus, olive).

Each prompt: one paragraph, 45-75 words, in this structure:
"Top-down real photograph of [objects] on [surface], with [one small extra]. Natural [texture] with tiny
imperfections, matte not glossy. Bright even daylight with soft shadows, everything in sharp focus. All
objects small and fully inside the frame with wide empty margins on every side, nothing cut off at the
edges. Clean minimal composition with plenty of empty space for text. Muted natural colors."

Do NOT repeat these recent themes or their main objects: {AVOID}

Answer in Bangla, but keep each prompt in English inside its own code block so I can copy it.
For each: the theme, why buyers download it (one line), aspect ratio 1:1, the prompt, and what to check
at 100% zoom before uploading. Finally suggest a Magnific title (include "mockup" for mockups) and
10 keywords for each.`;

function claudePromptButton(d, id = "claudePrompt") {
  const avoid = (d && d.ideas || []).map((i) => i.theme).join("; ") || "(none)";
  // copy + open a blank claude.ai chat (no prefilled link, so no warning): paste with Cmd+V and send
  return `<a class="btn primary" href="https://claude.ai/new" target="_blank" rel="noopener" onclick="copyText('${id}')">🤖 Copy prompt request + open Claude</a>
<pre id="${id}" style="display:none"></pre>
<script>(function(){var p=${JSON.stringify(CLAUDE_PROMPT_REQUEST).replace(/</g, "\\u003c")},a=${JSON.stringify(avoid).replace(/</g, "\\u003c")};
var d=new Date(Date.now()+6*3600e3).toISOString().slice(0,10);document.getElementById('${id}').textContent=p.replace('{DATE}',d).replace('{AVOID}',a);})();</script>`;
}

function ideasSection(d, req) {
  const button = req
    ? `<div class="msg">⏳ Requested ${bdTime(req.at)}. New prompts arrive in about 10-15 minutes; refresh this page.
<form method="post" action="/admin/action" style="display:inline"><button name="do" value="ideas_cancel">Cancel</button></form></div>`
    : `<form method="post" action="/admin/action" onsubmit="return confirm('Make 4 new Firefly prompts now? Free (Google Gemini).')">
<button name="do" value="ideas_request">✨ Make new prompts (free)</button></form>`;
  const claude = `<div class="row">${claudePromptButton(d)}<span class="muted">Copies a ready request and opens claude.ai: press Cmd+V and send. Claude writes 4 flat-lay 1:1 prompts. Free with your Claude account; the prompts appear in Claude, not here.</span></div>`;
  const tools = FREE_TOOLS.map(([n, u, t]) =>
    `<div class="card"><h3><a href="${u}" target="_blank" rel="noopener">${esc(n)} ↗</a></h3><p class="muted">${esc(t)}</p></div>`).join("");
  const cards = (d.ideas || []).map((i, n) => `<div class="card">
<span class="pill ${i.kind === "seasonal" ? "on" : "off"}">${esc(i.kind)}</span> <span class="muted">${esc(i.aspect)} · ${esc(i.best_tool)}</span>
<h3>${esc(i.theme)}</h3><p class="muted">${esc(i.why)}</p>
<div class="prompt" id="idea-${n}">${esc(i.prompt)}</div>
<div class="row"><a class="btn primary" href="https://firefly.adobe.com/image-generate" target="_blank" rel="noopener" onclick="copyText('idea-${n}')">🎨 Copy + open Firefly</a>
<button type="button" onclick="copyText('idea-${n}')">📋 Copy prompt</button></div>
<p class="muted"><b>Check:</b> ${esc(i.avoid)}</p>
<p class="muted"><b>Keywords:</b> ${esc((i.keywords || []).join(", "))}</p></div>`).join("")
    || `<p class="muted">No ideas yet. Press the button to make some.</p>`;
  return `<h2 id="ideas">Magnific · Image ideas</h2>
<p class="muted">Made only when you press the button, by Google Gemini (free tier). Seasonal ideas are for events 3-8 weeks ahead, because buyers download early.
${d.date ? "Updated " + bdTime(d.created) + "." : ""} ${esc(d.season_note || "")}</p>
${button}
${claude}
<div class="msg"><b>Fastest free routine:</b> 1) press <b>🎨 Copy + open Firefly</b>, paste (Cmd+V), pick the aspect ratio shown on the card and the largest size, generate, download the good ones;
2) double-click <b>Magnific Batch</b> on your Mac Desktop: it takes the Firefly downloads, checks quality, writes titles, 45 keywords and the CSV, and opens the upload folder + Magnific;
3) drag the JPGs and the CSV into Magnific, mark AI, Submit. (After 500 published files Magnific opens SFTP; then upload can be automatic too.)</div>
<p><b>Free workflow:</b> copy a prompt → make 4-8 images in Adobe Firefly (big enough without upscaling) → keep only clean ones (hands, faces, no text) → run <code>tools/magnific/run.sh</code> for titles/keywords/CSV → upload on Magnific and mark as AI.</p>
<div class="msg"><b>Avoid "Low quality" rejections:</b> zoom to 100% before uploading. Reject images with plastic or waxy surfaces,
smeared small details, over-sharp edges, odd hands or fake text. Fewer objects in a scene = fewer AI mistakes.
The Mac tool now scores every image and leaves weak ones out of the CSV (see magnific_report.txt).</div>
<div class="grid">${tools}</div>
<div class="grid">${cards}</div>
<p><a class="btn" href="https://contributor.magnific.com/dashboard" target="_blank" rel="noopener">Magnific contributor ↗</a></p>
<p class="muted">Also check <b>Search Trends</b> in the Magnific contributor menu and favour ideas that match it.</p>`;
}

// Quick links to the app stores (no API: they open in a new tab, already signed in).
function appsSection(used) {
  const links = (items) => items.map(([n, u, t]) =>
    `<a class="card applink" href="${u}" target="_blank" rel="noopener"><h3>${esc(n)} ↗</h3><p class="muted">${esc(t)}</p></a>`).join("");
  return `<h2 id="play">Google Play Console</h2>
<p class="muted">Android apps: releases, reviews, statistics and earnings.</p>
${appIdeaCard(used)}
<div class="apps">${links([
    ["All apps", "https://play.google.com/console/developers", "Every app, its status and quick actions"],
    ["Releases & testing", "https://play.google.com/console/developers/app-list", "Pick an app → Test and release → Production"],
    ["Ratings & reviews", "https://play.google.com/console/developers/app-list", "Pick an app → Ratings and reviews (reply to users)"],
    ["Statistics", "https://play.google.com/console/developers/app-list", "Installs, uninstalls, active users"],
    ["Earnings & payouts", "https://play.google.com/console/developers/payments", "Revenue, payments profile, payouts"],
    ["Policy status", "https://play.google.com/console/developers/policy-status", "Warnings and rejected updates"],
  ])}</div>
<h2 id="ios">iOS · App Store Connect</h2>
<p class="muted">iPhone apps: builds, TestFlight, App Store listing, sales.</p>
<div class="apps">${links([
    ["My apps", "https://appstoreconnect.apple.com/apps", "All iOS apps and their review status"],
    ["TestFlight", "https://appstoreconnect.apple.com/apps", "Pick an app → TestFlight (testers and builds)"],
    ["Sales & trends", "https://appstoreconnect.apple.com/trends", "Downloads, proceeds, countries"],
    ["Payments & financial", "https://appstoreconnect.apple.com/itc/payments_and_financial_reports", "Bank, tax and payouts"],
    ["Ratings & reviews", "https://appstoreconnect.apple.com/apps", "Pick an app → Ratings and Reviews"],
    ["Developer account", "https://developer.apple.com/account", "Certificates, identifiers, membership"],
  ])}</div>`;
}

// "What should I build next?" — opens claude.ai with a ready prompt (no API key, no API cost).
// One Kotlin Multiplatform (KMP) project -> Android + iOS + web app. Names saved under the button
// (KV "app_ideas") go into the prompt as "do not suggest again", so an idea never comes twice.
const APP_IDEA_PROMPT = `Today is {DATE}. I am a solo developer in Bangladesh. I build with Kotlin Multiplatform (KMP)
and Compose Multiplatform: ONE shared Kotlin codebase that I ship as 3 products:
  1. Android app on Google Play
  2. iOS app on the Apple App Store
  3. Web app (Compose for Web / Kotlin Wasm), found through Google search
US/UK/CA audience preferred.

Suggest exactly ONE new app, game or tool that works well on all three and has a realistic chance to RANK
(Google Play search, App Store search and Google web search), not just because it is a nice idea.

Please use web search first to check:
- what people are searching for right now (rising topics, seasonal needs for the coming weeks, new rules or devices),
- how crowded it is: search play.google.com and apps.apple.com for the main keyword (how many strong apps, ratings,
  installs/reviews, last-update dates) and Google for web tools doing the same. Prefer keywords where the top results
  are old, low-rated or few.
It must be buildable by one person in about 1-3 weeks with KMP libraries that support Android, iOS AND web
(Compose Multiplatform, Ktor, kotlinx.serialization, kotlinx-datetime, multiplatform-settings, SQLDelight or Room KMP).
Avoid features that only work on one platform (widgets, background services, NFC, health data, heavy camera/AR) unless
they are optional. Do not suggest anything that needs medical, financial or legal claims, gambling,
copyrighted characters/brands, or a big backend.

ALREADY SUGGESTED (do NOT suggest any of these again, and nothing that is basically the same idea under another name):
{AVOID}

Answer in Bangla (keep the app name, keywords and code names in English).
The very first line must be exactly: APP: <app name>
1. App name (max 30 characters, includes the main keyword), type (app/game/tool), Google Play category and App Store category
2. Why it can rank now (what you found), and how strong the current top results are on Play, App Store and web
3. 3-6 keywords to target (store keywords + web search keywords)
4. Minimum features for version 1, marking what is shared KMP code and what (if anything) is platform-specific
5. KMP setup: modules (shared / androidApp / iosApp / webApp), the libraries above you would use, and anything that
   does not work on web or iOS and how to handle it
6. How it makes money on each platform (Android, iOS, web), and roughly how many days of work
7. The sources you checked
Be honest: if the evidence is thin, say so.`;

function appIdeaCard(used) {
  const list = (used || []).map((x) => x.name);
  const chips = (used || []).map((x) => `<form method="post" action="/admin/action" style="display:inline"><input type="hidden" name="name" value="${esc(x.name)}">
<span class="pill off">${esc(x.name)} <button class="ico" name="do" value="appidea_del" title="Remove">✕</button></span></form>`).join(" ");
  return `<div class="card"><h3>💡 What should I build next? (KMP: Android + iOS + web)</h3>
<p class="muted">Opens claude.ai in a new tab with a ready question: Claude checks the web, Google Play and the App Store and suggests ONE idea
you build once in Kotlin Multiplatform and ship as an Android app, an iOS app and a web app. Free (your Claude account, no API key).
Turn on web search in Claude if it asks.</p>
<a class="btn primary" id="appIdeaBtn" href="https://claude.ai/new" target="_blank" rel="noopener">✨ Suggest today's app idea</a>
<p class="muted"><b>So it never comes twice:</b> copy the name from Claude's first line (<code>APP: …</code>) and save it here.
Every saved name is sent with the next question as "do not suggest again".</p>
<form method="post" action="/admin/action" class="ef"><input name="name" maxlength="60" placeholder="App name from Claude" required>
<button name="do" value="appidea_save">Save as suggested</button></form>
${chips ? `<p class="muted">Already suggested (${list.length}):</p><p>${chips}</p>` : ""}</div>
<script>(function(){var b=document.getElementById('appIdeaBtn'),p=${JSON.stringify(APP_IDEA_PROMPT).replace(/</g, "\\u003c")},
a=${JSON.stringify(list.length ? list.map((n) => "- " + n).join("\n") : "(none yet)").replace(/</g, "\\u003c")};
function u(){var d=new Date(Date.now()+6*3600e3).toISOString().slice(0,10);b.href='https://claude.ai/new?q='+encodeURIComponent(p.replace('{DATE}',d).replace('{AVOID}',a));}
u();b.addEventListener('click',u);})();</script>`;
}

// Cross-posting the best Shorts to a separate Facebook Page + Instagram, Threads and Bluesky.
function xpostSection(xp, rep) {
  const page = xp.meta.pages.find((p) => p.id === xp.meta.active);
  const pill = (k, ok, label) => `<form method="post" action="/admin/action" style="display:inline"><input type="hidden" name="platform" value="${k}">
<button class="ico" name="do" value="xp_toggle" title="Switch on/off"><span class="pill ${ok && !xp.off[k] ? "on" : "off"}">${label}${ok ? (xp.off[k] ? " · off" : " · on") : " · not connected"}</span></button></form>`;
  const disc = (k) => `<form method="post" action="/admin/action" style="display:inline"><input type="hidden" name="kind" value="${k}">
<button class="danger ico" name="do" value="xp_disconnect" title="Disconnect">✕</button></form>`;
  const pageSel = xp.meta.pages.length > 1 ? `<form method="post" action="/admin/action" class="ef"><select name="page">${xp.meta.pages.map((p) =>
    `<option value="${esc(p.id)}"${p.id === xp.meta.active ? " selected" : ""}>${esc(p.name)}${p.ig_username ? " + @" + esc(p.ig_username) : ""}</option>`).join("")}</select>
<button name="do" value="xp_page">Use this Page</button></form>` : "";
  const res = (v) => !v ? "" : v.startsWith("ok") ? "✅" : `<span title="${esc(v)}">⚠️</span>`;
  const rows = (rep.recent || []).map((r) => `<tr><td>${bdTime(r.at)}</td><td>${esc(r.title)}${r.error ? ` <span class="muted">${esc(r.error)}</span>` : ""}</td>
<td>${r.views >= 0 ? r.views : "—"}</td><td>${res(r.facebook)}</td><td>${res(r.instagram)}</td><td>${res(r.threads)}</td><td>${res(r.bluesky)}</td></tr>`).join("")
    || `<tr><td colspan="7" class="muted">Nothing cross-posted yet.</td></tr>`;
  return `<h2 id="xpost">Cross-post · best Shorts</h2>
<p class="muted">Every day the 5 Shorts with the most YouTube views (from the last 3 days, max 2 per channel) are posted to the accounts below,
spread over the 3 daily runs. Each post carries the Amazon affiliate links and the #ad + AI-voice disclosure (Instagram can't make caption links
clickable, so put shop.pickixo.com in its bio). Click a platform to switch it on/off.</p>
<div class="card"><h3>Accounts ${xp.paused ? '<span class="pill off">paused</span>' : ""}</h3>
<p>${pill("facebook", !!page, "Facebook" + (page ? ": " + esc(page.name) : ""))} ${pill("instagram", !!(page && page.ig_id), "Instagram" + (page && page.ig_username ? ": @" + esc(page.ig_username) : ""))}
${pill("threads", !!xp.threads, "Threads" + (xp.threads && xp.threads.username ? ": @" + esc(xp.threads.username) : ""))} ${pill("bluesky", !!xp.bluesky, "Bluesky" + (xp.bluesky ? ": @" + esc(xp.bluesky.handle) : ""))}</p>
<p><a class="btn primary" href="/auth/xp-connect?kind=meta">Connect new Facebook Page + Instagram</a> ${page ? disc("meta") : ""}
<a class="btn" href="/auth/xp-connect?kind=threads">Connect Threads</a> ${xp.threads ? disc("threads") : ""}</p>${pageSel}
<form method="post" action="/admin/action" class="ef"><input type="text" name="handle" placeholder="Bluesky handle (name.bsky.social)" value="${esc((xp.bluesky || {}).handle || "")}">
<input type="password" name="app_password" placeholder="App password xxxx-xxxx-xxxx-xxxx" autocomplete="off"><button name="do" value="xp_bsky">Save Bluesky</button>${xp.bluesky ? disc("bluesky") : ""}</form>
<form method="post" action="/admin/action"><button name="do" value="xp_pause">${xp.paused ? "▶ Resume cross-posting" : "■ Pause cross-posting"}</button></form>
<p class="muted">The Facebook login opens for the account that owns the NEW Page (log out of the old one in that dialog if needed).
In development mode that Facebook account and the Threads account must be added as testers of the Meta app.</p></div>
<div class="card"><h3>Recent${rep.queue && rep.queue.date ? " · today's queue: " + rep.queue.keys.length : ""}</h3>
<table class="keep"><thead><tr><th>When</th><th>Video</th><th>YT views</th><th>FB</th><th>IG</th><th>Threads</th><th>Bluesky</th></tr></thead><tbody>${rows}</tbody></table></div>`;
}

// Today's 3 honest Bangla posts for the "Modern Tech Life" page (pipeline/mtl_posts.py).
function mtlSection(d, mp) {
  const label = { morning: "সকাল · শেখানো", afternoon: "দুপুর · আমার আসল ফল", evening: "রাত · সতর্কতা / প্রশ্ন" };
  const cards = d ? d.posts.map((p, n) => `<div class="card"><span class="pill on">${esc(label[p.slot] || p.slot)}</span>
${p.warning ? `<span class="pill err">${esc(p.warning)}</span>` : ""}${p.fb ? `<span class="pill ${p.fb.startsWith("scheduled") ? "on" : "err"}">Facebook: ${esc(p.fb)}</span>` : ""}
<div class="prompt" id="mtl-${n}" style="white-space:pre-wrap">${esc(p.text)}\n\n${esc(p.hashtags.map((h) => "#" + h).join(" "))}</div>
<div class="row"><button type="button" onclick="copyText('mtl-${n}')">📋 Copy post</button></div></div>`).join("") : "";
  const src = d && d.sources.length ? `<p class="muted">Sources checked: ${d.sources.map((u) => `<a href="${esc(u)}" target="_blank" rel="noopener">${esc(u.replace(/^https?:\/\//, "").slice(0, 40))}</a>`).join(" · ")}</p>` : "";
  const auto = mp.page
    ? `<div class="card"><h3>🤖 Direct posting: ${mp.cfg.off ? "OFF" : "ON"} → ${esc(mp.page.name)}</h3>
<p class="muted">Each day's 3 posts go straight to this page at 9am, 2pm and 8pm (Bangladesh). A post with a warning is not posted: it waits here.</p>
<div class="row"><form method="post" action="/admin/action"><input type="hidden" name="do" value="mtl_auto"><button>${mp.cfg.off ? "Turn posting on" : "Turn posting off"}</button></form>
<a class="btn" href="/auth/fb-connect?for=mtl">Reconnect</a>
<form method="post" action="/admin/action"><input type="hidden" name="do" value="mtl_disconnect"><button>Disconnect</button></form></div></div>`
    : `<div class="card"><h3>🤖 Direct posting: not connected</h3>
<p>Click the button. If Facebook asks "continue with your previous settings?", choose <b>Edit settings</b>, then tick <b>Modern Tech Life</b> and keep the pages that are already ticked (unticking them stops their posts).</p>
<p><a class="btn primary" href="/auth/fb-connect?for=mtl">f Connect Modern Tech Life page</a></p></div>`;
  return `<h2 id="mtl">Modern Tech Life · daily Bangla posts</h2>
<div class="msg">⏸ <b>Stopped (to save OpenAI cost):</b> no new posts are written or posted. To turn it back on: GitHub repo → Settings → Secrets and variables → Actions → Variables → add <code>MTL_ON</code> = <code>true</code>.</div>
<p class="muted">Every morning AI researches ONE real, current way to earn with AI from Bangladesh (web search, sources below) and writes 3 honest
posts: a how-to, your real result (only from config/mtl_facts.json) and a warning or question. No income promises. They are posted directly on
<a href="https://www.facebook.com/ModernTechLife" target="_blank" rel="noopener">the page ↗</a>; copy buttons are here too.${d ? " Today's topic: <b>" + esc(d.topic) + "</b> (" + esc(d.date) + ")." : ""}</p>
${auto}${cards ? `<div class="grid">${cards}</div>` : '<p class="muted">No posts yet. They arrive with the 8am (Bangladesh) run.</p>'}${src}`;
}

function magnificToolSection(magIdeas) {
  return `<h2 id="magnific-tool">Magnific · Upscale + metadata tool</h2>
<p class="muted">Choose your finished images. For each one it makes sure the short side is 2000px+ (AI upscale 4× with ESRGAN, then down to 2048,
or a plain resize for small changes) and writes the title and keywords. The strict AI quality check is a separate, optional button: press it only
when you want a second opinion (it unticks weak images: below 7/10 or with problems such as fake text). Images stay in your browser; only small
previews go to the AI.</p>
<div class="card"><div class="row">
<input type="file" id="mag-files" accept="image/jpeg,image/png,image/webp" multiple>
<label title="Only for images that need more than 1.5x; can freeze the page for minutes"><input type="checkbox" id="mag-ai"> AI upscale (only very small images; very slow)</label>
<input type="text" id="mag-model" placeholder="Model (as in Magnific's dropdown), optional" style="min-width:260px">
<button class="primary" id="mag-run" onclick="window.__mag.run()">Make title + keywords</button>
<button id="mag-convert" type="button" onclick="window.__mag.convert()" title="No AI needed">🔄 PNG → JPG only</button>
<span id="mag-convert-msg" class="muted"></span></div>
<div class="row" id="mag-out" style="display:none">
<button class="primary" onclick="window.__mag.jpgs()">⬇ Download JPGs with title + keywords inside (ticked)</button>
<button onclick="window.__mag.csv()">⬇ CSV (optional)</button>
<button id="mag-check" type="button" onclick="window.__mag.check()">🔍 AI quality check (optional)</button>
<a class="btn" href="https://contributor.magnific.com/" target="_blank" rel="noopener">Open Magnific ↗</a></div>
<p class="muted">Then on Magnific: Uploads → drop the downloaded JPGs (title and keywords are written inside each file, no CSV needed) → set "Created with AI: Yes" and the model → Submit.
AI upscaling runs on your computer; the first image loads the model (~10&nbsp;MB) and can take a few minutes on an older Mac.</p></div>
<div class="card"><h3>🤖 Image prompts with Claude (claude.ai, free)</h3>
<p class="muted">Press the button: the request is copied and claude.ai opens. Press <b>Cmd+V</b> and send. Claude writes 4 Firefly prompts
(top-down flat lay, 1:1, best-selling subjects). Copy a prompt into Firefly, make the images, then come back here for title + keywords.</p>
${claudePromptButton(magIdeas, "claudePromptTool")}</div>
<div class="grid" id="mag-results"></div>
<script src="/magnific-tool.js?v=10"></script>`;
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
  const auto = d.autopost ? `<span class="pill on">Auto-posting ON</span> reels, photo and question posts are scheduled on your Page automatically.`
    : `<span class="pill off">Auto-posting OFF</span> press "Connect Facebook Page" below to switch it on.`;
  return `<h2 id="facebook">Facebook page · USA</h2>
<p class="muted">Daily posts for your monetized Page, written for US viewers and timed for US Eastern. ${auto}
Reels are made automatically too (stock clips + AI voice + on-screen steps) and scheduled with the posts. ${d.date ? "Updated " + bdTime(d.created) + "." : ""}</p>
${fbConnectHtml(fp || {})}${planHtml}<div class="grid">${posts}</div>
<p><a class="btn" href="https://business.facebook.com/latest/content_calendar" target="_blank" rel="noopener">Meta Business Suite planner ↗</a>
<a class="btn" href="https://www.facebook.com/professional_dashboard/monetization" target="_blank" rel="noopener">Monetization ↗</a></p>`;
}
