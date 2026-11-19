// POST /admin/action  -> pause/resume/disconnect a channel, or pause/resume everything
import { getState, putState, redirect, session } from "../../lib/dashboard.js";

export async function onRequestPost(context) {
  const { env, request } = context;
  if (!(await session(context))) return redirect("/admin");
  // same-origin check (SameSite=Lax cookie already blocks cross-site POSTs; belt and braces)
  const origin = request.headers.get("Origin");
  if (origin && origin !== new URL(request.url).origin) return new Response("Bad origin", { status: 403 });

  const form = await request.formData();
  const ch = String(form.get("ch") || "");
  const action = String(form.get("do") || "");
  const st = await getState(env);
  let msg = "";

  if (action === "pause_all") { st.paused = true; msg = "All uploads paused."; }
  else if (action === "resume_all") { st.paused = false; msg = "Uploads resumed."; }
  else if (st.channels[ch]) {
    if (action === "enable") { st.channels[ch].enabled = true; msg = ch + " resumed."; }
    else if (action === "disable") { st.channels[ch].enabled = false; msg = ch + " paused."; }
    else if (action === "disconnect") {
      delete st.channels[ch];
      await env.CHANNELS_KV.delete("refresh:" + ch);
      msg = ch + " disconnected.";
    }
  }
  await putState(env, st);
  return redirect("/admin?msg=" + encodeURIComponent(msg || "Nothing changed."));
}
