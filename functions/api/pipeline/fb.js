// POST /api/pipeline/fb {"date","created","posts":[...]}  (header X-Pipeline-Key)
import { json, pipelineAuthorized } from "../../../lib/dashboard.js";

export async function onRequestPost(context) {
  if (!pipelineAuthorized(context)) return json({ error: "unauthorized" }, 401);
  const b = await context.request.json();
  const s = (v, n) => String(v ?? "").slice(0, n);
  const posts = (b.posts || []).slice(0, 6).map((p) => ({
    type: s(p.type, 20), time_et: s(p.time_et, 20), pillar: s(p.pillar, 120), title: s(p.title, 160),
    hook: s(p.hook, 300), script: s(p.script, 2500), visuals: s(p.visuals, 800), caption: s(p.caption, 800),
    hashtags: (p.hashtags || []).slice(0, 6).map((h) => s(h, 40)), status: s(p.status, 200),
  }));
  await context.env.CHANNELS_KV.put("fb", JSON.stringify({ date: s(b.date, 20), created: s(b.created, 30), autopost: !!b.autopost, posts }));
  return json({ ok: true });
}
