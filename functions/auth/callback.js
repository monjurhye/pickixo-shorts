// GET /auth/callback  -> Google returns here for both sign-in and channel connect
import { GOOGLE_TOKEN, callbackUrl, cookie, getCookie, getState, idTokenEmail, owners, putRefresh,
  putState, redirect, session, sign, verify } from "../../lib/dashboard.js";

function back(msg, extraHeaders = {}) {
  return redirect("/admin?msg=" + encodeURIComponent(msg), extraHeaders);
}

export async function onRequestGet(context) {
  const { env, request } = context;
  const url = new URL(request.url);
  const clearState = { "Set-Cookie": cookie("pk_oauth", "", 0) };

  const st = await verify(env, getCookie(request, "pk_oauth"));
  if (!st || st.nonce !== url.searchParams.get("state")) return back("Sign-in expired, try again.", clearState);
  if (url.searchParams.get("error")) return back("Google: " + url.searchParams.get("error"), clearState);

  const r = await fetch(GOOGLE_TOKEN, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      code: url.searchParams.get("code") || "",
      client_id: env.GOOGLE_CLIENT_ID,
      client_secret: env.GOOGLE_CLIENT_SECRET,
      redirect_uri: callbackUrl(request),
      grant_type: "authorization_code",
    }),
  });
  const tok = await r.json();
  if (!r.ok) return back("Token exchange failed: " + (tok.error_description || tok.error), clearState);
  const email = idTokenEmail(tok.id_token || "");

  if (st.mode === "login") {
    if (!email || !owners(env).includes(email)) return back("This Google account is not allowed: " + email, clearState);
    const s = await sign(env, { email, exp: Date.now() + 12 * 3600e3 });
    return new Response(null, { status: 302, headers: new Headers([
      ["Location", "/admin"],
      ["Set-Cookie", cookie("pk_oauth", "", 0)],
      ["Set-Cookie", cookie("pk_session", s, 12 * 3600)],
    ]) });
  }

  // connect mode: must still be signed in as an owner
  if (!(await session(context))) return back("Please sign in first.", clearState);
  if (!tok.refresh_token) return back("Google gave no refresh token. Remove the app at myaccount.google.com/permissions and connect again.", clearState);

  const yr = await fetch("https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true",
    { headers: { Authorization: "Bearer " + tok.access_token } });
  const yj = await yr.json();
  const item = (yj.items || [])[0];
  if (!item) return back("That account has no YouTube channel selected. Try again and pick a channel.", clearState);

  const state = await getState(env);
  // the same YouTube channel must not be linked to two niches
  for (const [other, info] of Object.entries(state.channels)) {
    if (other !== st.ch && info.youtube_id === item.id) {
      return back(`"${item.snippet.title}" is already connected as ${other}. Pick a different channel.`, clearState);
    }
  }
  await putRefresh(env, st.ch, tok.refresh_token);
  state.channels[st.ch] = {
    enabled: true,
    youtube_id: item.id,
    title: item.snippet.title,
    handle: item.snippet.customUrl || "",
    google_email: email,
    connected_at: new Date().toISOString(),
    error: "",
  };
  await putState(env, state);
  return back(`Connected ${st.ch}: ${item.snippet.title}`, clearState);
}
