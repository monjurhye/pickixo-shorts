// GET /auth/fb-connect -> Facebook login for the Page (admin only)
// GET /auth/fb-connect?for=mtl -> login only for the "Modern Tech Life" page (direct daily posts)
import { cookie, randomId, redirect, session, sign } from "../../lib/dashboard.js";
import { FB_SCOPES, fbCallbackUrl } from "../../lib/fb.js";

export async function onRequestGet(context) {
  const { env, request } = context;
  if (!(await session(context))) return redirect("/admin");
  if (!env.FB_APP_ID || !env.FB_APP_SECRET)
    return redirect("/admin?msg=" + encodeURIComponent("Add FB_APP_ID and FB_APP_SECRET in Cloudflare Pages settings first.") + "#facebook");
  const mtl = new URL(request.url).searchParams.get("for") === "mtl";
  const nonce = randomId();
  const st = await sign(env, { nonce, mode: mtl ? "mtl" : "fb", exp: Date.now() + 10 * 60e3 });
  const p = { client_id: env.FB_APP_ID, redirect_uri: fbCallbackUrl(request), response_type: "code", state: nonce };
  if (mtl) p.auth_type = "rerequest";
  if (env.FB_CONFIG_ID) p.config_id = env.FB_CONFIG_ID; else p.scope = FB_SCOPES;
  const url = "https://www.facebook.com/v21.0/dialog/oauth?" + new URLSearchParams(p).toString();
  return redirect(url, { "Set-Cookie": cookie("pk_fboauth", st, 600) });
}
