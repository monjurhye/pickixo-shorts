// GET /api/pipeline/fb-token (header X-Pipeline-Key) -> {"page_id","token"} of the active Page.
// Used only by the GitHub pipeline to upload Reels (video bytes go straight to Facebook).
import { json, pipelineAuthorized } from "../../../lib/dashboard.js";
import { getFb } from "../../../lib/fb.js";

export async function onRequestGet(context) {
  if (!pipelineAuthorized(context)) return json({ error: "unauthorized" }, 401);
  const d = await getFb(context.env);
  const p = d.pages.find((x) => x.id === d.active);
  if (!p) return json({ error: "not_connected" }, 404);
  return json({ page_id: p.id, name: p.name, token: p.token });
}
