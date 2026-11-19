// GET /auth/connect?ch=ch01  -> Google consent for one YouTube channel (admin only)
import { GOOGLE_AUTH, YT_SCOPES, callbackUrl, channelList, cookie, randomId, redirect, session, sign }
  from "../../lib/dashboard.js";

export async function onRequestGet(context) {
  if (!(await session(context))) return redirect("/admin");
  const ch = new URL(context.request.url).searchParams.get("ch") || "";
  const known = (await channelList(context)).some((c) => c.id === ch);
  if (!known) return redirect("/admin?msg=" + encodeURIComponent("Unknown channel " + ch));

  const nonce = randomId();
  const st = await sign(context.env, { nonce, mode: "connect", ch, exp: Date.now() + 10 * 60e3 });
  const url = new URL(GOOGLE_AUTH);
  url.search = new URLSearchParams({
    client_id: context.env.GOOGLE_CLIENT_ID,
    redirect_uri: callbackUrl(context.request),
    response_type: "code",
    scope: YT_SCOPES,
    access_type: "offline",
    prompt: "consent select_account",   // always returns a refresh token; lets you pick the channel
    include_granted_scopes: "true",
    state: nonce,
  }).toString();
  return redirect(url.toString(), { "Set-Cookie": cookie("pk_oauth", st, 600) });
}
