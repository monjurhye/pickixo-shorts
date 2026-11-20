// Facebook Page connection for the dashboard. Env: FB_APP_ID (plain), FB_APP_SECRET (secret),
// optional FB_CONFIG_ID (Facebook Login for Business configuration). Page tokens live only in KV.
export const GRAPH = "https://graph.facebook.com/v21.0";
export const FB_SCOPES = "pages_show_list,pages_read_engagement,pages_manage_posts";

export async function getFb(env) {
  const raw = await env.CHANNELS_KV.get("fbpages");
  return raw ? JSON.parse(raw) : { pages: [], active: "" };
}
export async function putFb(env, d) {
  await env.CHANNELS_KV.put("fbpages", JSON.stringify(d));
}
export function fbCallbackUrl(request) {
  return new URL("/auth/fb-callback", request.url).toString();
}
