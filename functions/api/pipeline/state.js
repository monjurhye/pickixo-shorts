// GET /api/pipeline/state  (header X-Pipeline-Key) -> which channels may upload now
import { getState, json, pipelineAuthorized } from "../../../lib/dashboard.js";

export async function onRequestGet(context) {
  if (!pipelineAuthorized(context)) return json({ error: "unauthorized" }, 401);
  const st = await getState(context.env);
  const channels = {};
  for (const [id, info] of Object.entries(st.channels)) {
    channels[id] = { enabled: !!info.enabled && !info.error, title: info.title, handle: info.handle };
  }
  return json({ paused: !!st.paused, channels });
}
