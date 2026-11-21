// GET /auth/xp-callback -> stores the cross-post Page/Instagram or Threads token in KV (never shown).
import { cookie, getCookie, redirect, session, verify } from "../../lib/dashboard.js";
import { GRAPH } from "../../lib/fb.js";
import { getXp, putXp } from "../../lib/xpost.js";

const back = (m, h) => redirect("/admin?msg=" + encodeURIComponent(m) + "#xpost", h);
const q = (o) => new URLSearchParams(o).toString();

export async function onRequestGet(context) {
  const { env, request } = context;
  const clear = { "Set-Cookie": cookie("pk_xpoauth", "", 0) };
  if (!(await session(context))) return redirect("/admin");
  const u = new URL(request.url);
  if (u.searchParams.get("error")) return back("Login cancelled: " + (u.searchParams.get("error_description") || u.searchParams.get("error")), clear);
  const st = await verify(env, getCookie(request, "pk_xpoauth"));
  if (!st || !String(st.mode).startsWith("xp-") || st.nonce !== u.searchParams.get("state")) return back("Login expired, try again.", clear);
  const code = (u.searchParams.get("code") || "").replace(/#_$/, "");
  const redirect_uri = new URL("/auth/xp-callback", request.url).toString();
  const xp = await getXp(env);

  if (st.mode === "xp-threads") {
    let r = await fetch("https://graph.threads.net/oauth/access_token", { method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: q({ client_id: env.THREADS_APP_ID, client_secret: env.THREADS_APP_SECRET, grant_type: "authorization_code", redirect_uri, code }) });
    let d = await r.json();
    if (!d.access_token) return back("Threads token error: " + ((d.error && d.error.message) || d.error_message || r.status), clear);
    r = await fetch("https://graph.threads.net/access_token?" + q({ grant_type: "th_exchange_token",
      client_secret: env.THREADS_APP_SECRET, access_token: d.access_token }));
    const ll = await r.json();
    const token = ll.access_token || d.access_token;
    r = await fetch("https://graph.threads.net/v1.0/me?" + q({ fields: "id,username", access_token: token }));
    const me = await r.json();
    xp.threads = { user_id: String(me.id || d.user_id), username: me.username || "", token,
      expires_at: new Date(Date.now() + (ll.expires_in || 3600) * 1000).toISOString() };
    await putXp(env, xp);
    return back("Threads connected: @" + (me.username || me.id), clear);
  }

  let r = await fetch(GRAPH + "/oauth/access_token?" + q({ client_id: env.FB_APP_ID, client_secret: env.FB_APP_SECRET, redirect_uri, code }));
  let d = await r.json();
  if (!d.access_token) return back("Facebook token error: " + ((d.error && d.error.message) || r.status), clear);
  r = await fetch(GRAPH + "/oauth/access_token?" + q({ grant_type: "fb_exchange_token", client_id: env.FB_APP_ID,
    client_secret: env.FB_APP_SECRET, fb_exchange_token: d.access_token }));
  const ll = await r.json();
  r = await fetch(GRAPH + "/me/accounts?" + q({ fields: "id,name,access_token,instagram_business_account{id,username}", limit: "100",
    access_token: ll.access_token || d.access_token }));
  d = await r.json();
  const pages = (d.data || []).filter((p) => p.access_token).map((p) => ({ id: p.id, name: p.name, token: p.access_token,
    ig_id: (p.instagram_business_account || {}).id || "", ig_username: (p.instagram_business_account || {}).username || "" }));
  if (!pages.length) return back("No Pages came back. Tick the new Page (and its Instagram) in the Facebook dialog.", clear);
  const withIg = pages.find((p) => p.ig_id);
  xp.meta = { pages, active: pages.some((p) => p.id === xp.meta.active) ? xp.meta.active : (withIg || pages[0]).id,
    connected_at: new Date().toISOString() };
  await putXp(env, xp);
  const a = pages.find((p) => p.id === xp.meta.active);
  return back("Connected: " + a.name + (a.ig_username ? " + Instagram @" + a.ig_username : " (no Instagram linked to this Page)"), clear);
}
