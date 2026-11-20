// GET  /api/pipeline/pins  -> {"paused": bool}           (header X-Pipeline-Key)
// POST /api/pipeline/pins  {"date","want","rows":[...]}  -> stores the run for /admin
import { json, pipelineAuthorized } from "../../../lib/dashboard.js";
import { getPins, putPins } from "../../../lib/pins.js";

export async function onRequestGet(context) {
  if (!pipelineAuthorized(context)) return json({ error: "unauthorized" }, 401);
  const p = await getPins(context.env);
  return json({ paused: !!p.paused });
}

export async function onRequestPost(context) {
  if (!pipelineAuthorized(context)) return json({ error: "unauthorized" }, 401);
  const run = await context.request.json();
  const p = await getPins(context.env);
  const rows = (run.rows || []).slice(0, 20).map((r) => ({
    keyword: String(r.keyword || "").slice(0, 60), product: String(r.product || "").slice(0, 120),
    title: String(r.title || "").slice(0, 120), board: String(r.board || "").slice(0, 80),
    status: String(r.status || "").slice(0, 20), note: String(r.note || "").slice(0, 200),
    due: String(r.due || "").slice(0, 40), link: String(r.link || "").slice(0, 600),
  }));
  const ok = rows.filter((r) => r.status === "scheduled").length;
  p.last_run = { at: new Date().toISOString(), date: String(run.date || ""), want: Number(run.want) || 0,
    scheduled: ok, message: String(run.message || "").slice(0, 300) };
  p.total_scheduled = (p.total_scheduled || 0) + ok;
  p.recent = rows.filter((r) => r.status === "scheduled").concat(p.recent || []).slice(0, 30);
  p.last_rows = rows;
  await putPins(context.env, p);
  return json({ ok: true });
}
