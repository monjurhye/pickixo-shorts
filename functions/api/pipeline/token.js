// POST /api/pipeline/token {"ch":"ch01"}  (header X-Pipeline-Key)
// Returns a short-lived YouTube access token; the refresh token never leaves Cloudflare.
import { GOOGLE_TOKEN, getRefresh, getState, json, pipelineAuthorized, putState } from "../../../lib/dashboard.js";

export async function onRequestPost(context) {
  const { env } = context;
  if (!pipelineAuthorized(context)) return json({ error: "unauthorized" }, 401);
  const { ch } = await context.request.json();
  const st = await getState(env);
  const info = st.channels[ch];
  if (!info) return json({ error: "not_connected" }, 404);
  if (st.paused || !info.enabled) return json({ error: "paused" }, 409);
  const refresh = await getRefresh(env, ch);
  if (!refresh) return json({ error: "not_connected" }, 404);

  const r = await fetch(GOOGLE_TOKEN, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      client_id: env.GOOGLE_CLIENT_ID, client_secret: env.GOOGLE_CLIENT_SECRET,
      refresh_token: refresh, grant_type: "refresh_token",
    }),
  });
  const tok = await r.json();
  if (!r.ok) {
    if (tok.error === "invalid_grant") {  // revoked or expired: show "Needs reconnect" on the dashboard
      info.error = "Authorization revoked or expired. Reconnect this channel.";
      await putState(env, st);
    }
    return json({ error: tok.error || "token_error", detail: tok.error_description || "" }, 502);
  }
  return json({ access_token: tok.access_token, expires_in: tok.expires_in });
}
