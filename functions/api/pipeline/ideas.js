// GET  /api/pipeline/ideas -> {"requested": bool}  (is a button press waiting?)
// POST /api/pipeline/ideas {"take":true} -> {"requested"} and clears the request
// POST /api/pipeline/ideas {"date","created","season_note","ideas":[...]}  (header X-Pipeline-Key)
import { json, pipelineAuthorized } from "../../../lib/dashboard.js";
import { getIdeasRequest, setIdeasRequest } from "../../../lib/ideas.js";

export async function onRequestGet(context) {
  if (!pipelineAuthorized(context)) return json({ error: "unauthorized" }, 401);
  const req = await getIdeasRequest(context.env);
  return json({ requested: !!req, requested_at: req ? req.at : "" });
}

export async function onRequestPost(context) {
  if (!pipelineAuthorized(context)) return json({ error: "unauthorized" }, 401);
  const b = await context.request.json();
  if (b.take) {  // the workflow claims a waiting request (so a failed run never repeats the API cost)
    const req = await getIdeasRequest(context.env);
    if (req) await setIdeasRequest(context.env, null);
    return json({ requested: !!req });
  }
  const s = (v, n) => String(v ?? "").slice(0, n);
  const ideas = (b.ideas || []).slice(0, 12).map((i) => ({
    theme: s(i.theme, 120), why: s(i.why, 300), kind: s(i.kind, 20), prompt: s(i.prompt, 1200),
    avoid: s(i.avoid, 400), aspect: s(i.aspect, 10), best_tool: s(i.best_tool, 40),
    keywords: (i.keywords || []).slice(0, 15).map((k) => s(k, 40)),
  }));
  await context.env.CHANNELS_KV.put("ideas", JSON.stringify({
    date: s(b.date, 20), created: s(b.created, 30), season_note: s(b.season_note, 400), ideas }));
  return json({ ok: true });
}
