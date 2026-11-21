// Cross-post accounts (a separate Facebook Page + its Instagram, Threads, Bluesky). Tokens live only in KV.
//   KV "xpost": {meta:{pages:[{id,name,token,ig_id,ig_username}], active}, threads:{user_id,username,token,expires_at},
//                bluesky:{handle, app_password}, off:{facebook,instagram,threads,bluesky}, paused}
//   KV "xpost_report": {updated, queue, recent:[...]} (written by the pipeline)
export const XP_META_SCOPES = "pages_show_list,pages_read_engagement,pages_manage_posts,business_management,instagram_basic,instagram_content_publish";
export const THREADS_SCOPES = "threads_basic,threads_content_publish";

export async function getXp(env) {
  const raw = await env.CHANNELS_KV.get("xpost");
  const d = raw ? JSON.parse(raw) : {};
  d.meta = d.meta || { pages: [], active: "" }; d.off = d.off || {};
  return d;
}
export async function putXp(env, d) {
  await env.CHANNELS_KV.put("xpost", JSON.stringify(d));
}
export async function getXpReport(env) {
  const raw = await env.CHANNELS_KV.get("xpost_report");
  return raw ? JSON.parse(raw) : { recent: [], queue: { keys: [] } };
}
