// POST /api/pipeline/mtl {date, created, topic, sources, posts:[{slot,kind,text,hashtags,warning}]}  (X-Pipeline-Key)
// Today's 3 Bangla posts for the "Modern Tech Life" Facebook page, shown in /admin.
// GET /api/pipeline/mtl -> {auto, page:{id,name,token}|null}: where to auto-post (picked in /admin)
import { json, pipelineAuthorized } from "../../../lib/dashboard.js";
import { mtlPage } from "../../../lib/mtl.js";

export async function onRequestGet(context) {
  if (!pipelineAuthorized(context)) return json({ error: "unauthorized" }, 401);
  const { cfg, page } = await mtlPage(context.env);
  return json({ auto: !cfg.off, page: page ? { id: page.id, name: page.name, token: page.token } : null });
}

export async function onRequestPost(context) {
  if (!pipelineAuthorized(context)) return json({ error: "unauthorized" }, 401);
  const b = await context.request.json();
  const s = (v, n) => String(v ?? "").slice(0, n);
  const posts = (b.posts || []).slice(0, 3).map((p) => ({
    slot: s(p.slot, 12), kind: s(p.kind, 40), text: s(p.text, 3000), warning: s(p.warning, 120), fb: s(p.fb, 160),
    hashtags: (p.hashtags || []).slice(0, 6).map((h) => s(h, 40).replace(/^#/, "")),
  }));
  const sources = (b.sources || []).slice(0, 8).map((u) => s(u, 300)).filter((u) => /^https?:\/\//.test(u));
  await context.env.CHANNELS_KV.put("mtl", JSON.stringify({ date: s(b.date, 12), created: s(b.created, 30), topic: s(b.topic, 200), sources, posts }));
  return json({ ok: true });
}
