// POST /api/pipeline/drafts {"draft": {...}} or {"error": "..."}  (header X-Pipeline-Key)
// Stores Medium drafts for /admin (each one is already published on the shop blog).
import { json, pipelineAuthorized } from "../../../lib/dashboard.js";
import { getDrafts } from "../../../lib/drafts.js";

export async function onRequestPost(context) {
  if (!pipelineAuthorized(context)) return json({ error: "unauthorized" }, 401);
  const body = await context.request.json();
  const d = await getDrafts(context.env);
  if (body.error) {
    d.last_error = String(body.error).slice(0, 300);
  } else if (body.draft && body.draft.id) {
    const x = body.draft;
    d.items = [{
      id: String(x.id).slice(0, 20), created: String(x.created || "").slice(0, 30),
      title: String(x.title || "").slice(0, 200), subtitle: String(x.subtitle || "").slice(0, 300),
      tags: (x.tags || []).slice(0, 5).map((t) => String(t).slice(0, 40)),
      products: (x.products || []).slice(0, 10).map((t) => String(t).slice(0, 80)),
      html: String(x.html || "").slice(0, 60000), markdown: String(x.markdown || "").slice(0, 60000),
      blog_url: String(x.blog_url || "").slice(0, 300), status: "new",
    }].concat(d.items.filter((i) => i.id !== x.id)).slice(0, 20);
    d.last_error = "";
  }
  await context.env.CHANNELS_KV.put("drafts", JSON.stringify(d));
  return json({ ok: true });
}
