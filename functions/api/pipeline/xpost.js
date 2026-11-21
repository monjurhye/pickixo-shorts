// GET  /api/pipeline/xpost -> accounts for cross-posting (tokens; header X-Pipeline-Key)
// POST /api/pipeline/xpost {updated, queue, recent} -> results shown in /admin -> Cross-post
import { json, pipelineAuthorized } from "../../../lib/dashboard.js";
import { getXp, putXp } from "../../../lib/xpost.js";

export async function onRequestGet(context) {
  if (!pipelineAuthorized(context)) return json({ error: "unauthorized" }, 401);
  const { env } = context;
  const xp = await getXp(env);
  // Threads long-lived tokens last 60 days: refresh when fewer than 20 days are left
  if (xp.threads && Date.parse(xp.threads.expires_at) - Date.now() < 20 * 864e5) {
    const r = await fetch("https://graph.threads.net/refresh_access_token?" + new URLSearchParams({
      grant_type: "th_refresh_token", access_token: xp.threads.token }));
    const d = await r.json();
    if (d.access_token) {
      xp.threads.token = d.access_token;
      xp.threads.expires_at = new Date(Date.now() + (d.expires_in || 5184000) * 1000).toISOString();
      await putXp(env, xp);
    }
  }
  const page = xp.meta.pages.find((p) => p.id === xp.meta.active);
  const on = (k) => !xp.off[k];
  return json({
    paused: !!xp.paused,
    facebook: page && on("facebook") ? { page_id: page.id, name: page.name, token: page.token } : null,
    instagram: page && page.ig_id && on("instagram") ? { ig_id: page.ig_id, username: page.ig_username, token: page.token } : null,
    threads: xp.threads && on("threads") ? { user_id: xp.threads.user_id, token: xp.threads.token } : null,
    bluesky: xp.bluesky && on("bluesky") ? { handle: xp.bluesky.handle, app_password: xp.bluesky.app_password } : null,
  });
}

export async function onRequestPost(context) {
  if (!pipelineAuthorized(context)) return json({ error: "unauthorized" }, 401);
  const b = await context.request.json();
  const s = (v, n) => String(v ?? "").slice(0, n);
  const recent = (b.recent || []).slice(0, 20).map((r) => {
    const o = { key: s(r.key, 120), title: s(r.title, 160), at: s(r.at, 30), views: Number(r.views) || 0, error: s(r.error, 200) };
    for (const p of ["facebook", "instagram", "threads", "bluesky"]) if (r[p]) o[p] = s(r[p], 220);
    return o;
  });
  const queue = { date: s((b.queue || {}).date, 12), keys: ((b.queue || {}).keys || []).slice(0, 10).map((k) => s(k, 120)) };
  await context.env.CHANNELS_KV.put("xpost_report", JSON.stringify({ updated: s(b.updated, 30), queue, recent }));
  return json({ ok: true });
}
