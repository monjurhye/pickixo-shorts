// GET  /api/pipeline/fb-post -> {"connected", "page"}           (header X-Pipeline-Key)
// POST /api/pipeline/fb-post {"message","image_url","when"(unix)} -> schedules on the active Page
import { json, pipelineAuthorized } from "../../../lib/dashboard.js";
import { GRAPH, getFb } from "../../../lib/fb.js";

async function active(env) {
  const d = await getFb(env);
  return d.pages.find((p) => p.id === d.active) || null;
}

export async function onRequestGet(context) {
  if (!pipelineAuthorized(context)) return json({ error: "unauthorized" }, 401);
  const p = await active(context.env);
  return json({ connected: !!p, page: p ? p.name : "" });
}

export async function onRequestPost(context) {
  if (!pipelineAuthorized(context)) return json({ error: "unauthorized" }, 401);
  const p = await active(context.env);
  if (!p) return json({ error: "not_connected" }, 404);
  const b = await context.request.json();
  const form = { message: String(b.message || "").slice(0, 5000), access_token: p.token };
  if (b.when) { form.published = "false"; form.scheduled_publish_time = String(parseInt(b.when, 10)); }
  let path = "/" + p.id + "/feed";
  if (b.image_url) { path = "/" + p.id + "/photos"; form.url = String(b.image_url); form.caption = form.message; delete form.message; }
  const r = await fetch(GRAPH + path, { method: "POST", body: new URLSearchParams(form) });
  const d = await r.json();
  if (!r.ok || d.error) return json({ error: (d.error && d.error.message) || ("HTTP " + r.status) }, 502);
  return json({ ok: true, id: d.id || d.post_id || "" });
}
