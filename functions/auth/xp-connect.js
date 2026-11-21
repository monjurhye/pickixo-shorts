// GET /auth/xp-connect?kind=meta|threads -> login for the cross-post accounts (admin only).
// meta: a SEPARATE Facebook Page (+ its Instagram professional account). Uses FB_APP_ID/FB_APP_SECRET
//       (or FB_XP_CONFIG_ID for a Facebook Login for Business configuration that includes Instagram).
// threads: Threads login. Uses THREADS_APP_ID/THREADS_APP_SECRET (Meta app -> Threads API use case).
import { cookie, randomId, redirect, session, sign } from "../../lib/dashboard.js";
import { THREADS_SCOPES, XP_META_SCOPES } from "../../lib/xpost.js";

const back = (m) => redirect("/admin?msg=" + encodeURIComponent(m) + "#xpost");

export async function onRequestGet(context) {
  const { env, request } = context;
  if (!(await session(context))) return redirect("/admin");
  const kind = new URL(request.url).searchParams.get("kind") === "threads" ? "threads" : "meta";
  const nonce = randomId();
  const st = await sign(env, { nonce, mode: "xp-" + kind, exp: Date.now() + 10 * 60e3 });
  const redirect_uri = new URL("/auth/xp-callback", request.url).toString();
  let url;
  if (kind === "threads") {
    if (!env.THREADS_APP_ID || !env.THREADS_APP_SECRET) return back("Add THREADS_APP_ID and THREADS_APP_SECRET in Cloudflare Pages settings first.");
    url = "https://threads.net/oauth/authorize?" + new URLSearchParams({ client_id: env.THREADS_APP_ID, redirect_uri,
      scope: THREADS_SCOPES, response_type: "code", state: nonce });
  } else {
    if (!env.FB_APP_ID || !env.FB_APP_SECRET) return back("Add FB_APP_ID and FB_APP_SECRET in Cloudflare Pages settings first.");
    const p = { client_id: env.FB_APP_ID, redirect_uri, response_type: "code", state: nonce, auth_type: "rerequest" };
    if (env.FB_XP_CONFIG_ID) p.config_id = env.FB_XP_CONFIG_ID; else p.scope = XP_META_SCOPES;
    url = "https://www.facebook.com/v21.0/dialog/oauth?" + new URLSearchParams(p);
  }
  return redirect(url, { "Set-Cookie": cookie("pk_xpoauth", st, 600) });
}
