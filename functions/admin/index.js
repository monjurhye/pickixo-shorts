// GET /admin  -> channel dashboard (sign in with Google first)
import { channelList, esc, getState, html, session } from "../../lib/dashboard.js";
import { getPins } from "../../lib/pins.js";

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

  const [chans, st, pins] = await Promise.all([channelList(context), getState(context.env), getPins(context.env)]);
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
${pinsSection(pins)}`));
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
