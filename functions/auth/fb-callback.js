// GET /auth/fb-callback -> code -> long-lived user token -> Page tokens (stored in KV, never shown)
import { cookie, getCookie, redirect, session, verify } from "../../lib/dashboard.js";
import { GRAPH, fbCallbackUrl, getFb, putFb } from "../../lib/fb.js";

const back = (msg, h) => redirect("/admin?msg=" + encodeURIComponent(msg) + "#facebook", h);

export async function onRequestGet(context) {
  const { env, request } = context;
  const clear = { "Set-Cookie": cookie("pk_fboauth", "", 0) };
  if (!(await session(context))) return redirect("/admin");
  const u = new URL(request.url);
  if (u.searchParams.get("error")) return back("Facebook: " + (u.searchParams.get("error_description") || "cancelled"), clear);
  const st = await verify(env, getCookie(request, "pk_fboauth"));
  if (!st || st.mode !== "fb" || st.nonce !== u.searchParams.get("state")) return back("Login expired, try again.", clear);
  const q = (o) => new URLSearchParams(o).toString();
  let r = await fetch(GRAPH + "/oauth/access_token?" + q({ client_id: env.FB_APP_ID, client_secret: env.FB_APP_SECRET,
    redirect_uri: fbCallbackUrl(request), code: u.searchParams.get("code") || "" }));
  let d = await r.json();
  if (!d.access_token) return back("Facebook token error: " + ((d.error && d.error.message) || r.status), clear);
  r = await fetch(GRAPH + "/oauth/access_token?" + q({ grant_type: "fb_exchange_token", client_id: env.FB_APP_ID,
    client_secret: env.FB_APP_SECRET, fb_exchange_token: d.access_token }));
  const ll = await r.json();
  const userToken = ll.access_token || d.access_token;
  r = await fetch(GRAPH + "/me/accounts?" + q({ fields: "id,name,access_token,tasks", limit: "100", access_token: userToken }));
  d = await r.json();
  const pages = (d.data || []).filter((p) => p.access_token).map((p) => ({ id: p.id, name: p.name, token: p.access_token,
    can_post: (p.tasks || []).includes("CREATE_CONTENT") || (p.tasks || []).includes("MANAGE") }));
  if (!pages.length) return back("No Pages came back. Make sure you ticked your Page in the Facebook dialog.", clear);
  const cur = await getFb(env);
  const active = pages.some((p) => p.id === cur.active) ? cur.active : pages[0].id;
  await putFb(env, { pages, active, connected_at: new Date().toISOString() });
  return back("Facebook connected: " + pages.map((p) => p.name).join(", "), clear);
}
