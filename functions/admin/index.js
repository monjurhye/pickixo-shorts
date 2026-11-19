// GET /admin  -> channel dashboard (sign in with Google first)
import { channelList, esc, getState, html, session } from "../../lib/dashboard.js";

const CSS = `
:root{--bg:#faf8f5;--ink:#1c1917;--muted:#6b6560;--line:#e7e2db;--accent:#c2410c;--ok:#15803d;--bad:#b91c1c;--card:#fff}
@media (prefers-color-scheme:dark){:root{--bg:#14171c;--ink:#ece8e3;--muted:#a39d96;--line:#2a2f37;--accent:#fb923c;--ok:#4ade80;--bad:#f87171;--card:#1b1f26}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
main{max-width:980px;margin:0 auto;padding:24px 16px 60px}
h1{font-size:26px;margin:0 0 4px;letter-spacing:-.02em}.muted{color:var(--muted)}
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
@media (max-width:700px){td:nth-child(2),th:nth-child(2){display:none}}
`;

function page(body) {
  return `<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex">
<title>Pickixo · Channels</title><style>${CSS}</style></head><body><main>${body}</main></body></html>`;
}

export async function onRequestGet(context) {
  const msg = new URL(context.request.url).searchParams.get("msg");
  const note = msg ? `<div class="msg">${esc(msg)}</div>` : "";
  const s = await session(context);
  if (!s) {
    return html(page(`<h1>Pickixo channels</h1><p class="muted">Sign in with the owner Google account to manage YouTube channels.</p>
${note}<p><a class="btn primary" href="/auth/login">Sign in with Google</a></p>`));
  }

  const [chans, st] = await Promise.all([channelList(context), getState(context.env)]);
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
<table><thead><tr><th>ID</th><th>Niche</th><th>YouTube channel</th><th>Status</th><th></th></tr></thead><tbody>${rows}</tbody></table>
<p class="muted">Connect: pick the Google account, then the exact YouTube channel for that niche, and allow.
If Google shows “hasn't verified this app”, choose Advanced → Go to Pickixo Shorts Uploader.</p>`));
}
