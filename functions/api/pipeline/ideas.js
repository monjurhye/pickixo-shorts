// POST /api/pipeline/ideas {"date","created","season_note","ideas":[...]}  (header X-Pipeline-Key)
import { json, pipelineAuthorized } from "../../../lib/dashboard.js";

export async function onRequestPost(context) {
  if (!pipelineAuthorized(context)) return json({ error: "unauthorized" }, 401);
  const b = await context.request.json();
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
