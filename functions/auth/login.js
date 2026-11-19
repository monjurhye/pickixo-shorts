// GET /auth/login  -> sign in with Google (email only) to manage the dashboard
import { GOOGLE_AUTH, callbackUrl, cookie, randomId, redirect, sign } from "../../lib/dashboard.js";

export async function onRequestGet(context) {
  const nonce = randomId();
  const st = await sign(context.env, { nonce, mode: "login", exp: Date.now() + 10 * 60e3 });
  const url = new URL(GOOGLE_AUTH);
  url.search = new URLSearchParams({
    client_id: context.env.GOOGLE_CLIENT_ID,
    redirect_uri: callbackUrl(context.request),
    response_type: "code",
    scope: "openid email",
    prompt: "select_account",
    state: nonce,
  }).toString();
  return redirect(url.toString(), { "Set-Cookie": cookie("pk_oauth", st, 600) });
}
