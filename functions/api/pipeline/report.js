// POST /api/pipeline/report {"ch":"ch01","error":"..."}  (header X-Pipeline-Key)
// Lets the pipeline flag a channel (e.g. repeated upload 403s) so it shows on the dashboard.
import { getState, json, pipelineAuthorized, putState } from "../../../lib/dashboard.js";

export async function onRequestPost(context) {
  if (!pipelineAuthorized(context)) return json({ error: "unauthorized" }, 401);
  const { ch, error, disable } = await context.request.json();
  const st = await getState(context.env);
  if (!st.channels[ch]) return json({ error: "not_connected" }, 404);
  st.channels[ch].error = String(error || "").slice(0, 300);
  if (disable) st.channels[ch].enabled = false;
  await putState(context.env, st);
  return json({ ok: true });
}
