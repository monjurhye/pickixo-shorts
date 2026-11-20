// POST /admin/action  -> pause/resume/disconnect a channel, or pause/resume everything
import { getState, putState, redirect, session } from "../../lib/dashboard.js";
import { getPins, putPins } from "../../lib/pins.js";

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

  if (action === "draft_done" || action === "draft_delete" || action === "draft_new") {
    const raw = await env.CHANNELS_KV.get("drafts");
    const d = raw ? JSON.parse(raw) : { items: [] };
    const id = String(form.get("id") || "");
    if (action === "draft_delete") d.items = d.items.filter((i) => i.id !== id);
    else d.items.forEach((i) => { if (i.id === id) i.status = action === "draft_done" ? "published" : "new"; });
    await env.CHANNELS_KV.put("drafts", JSON.stringify(d));
    return redirect("/admin?msg=" + encodeURIComponent(action === "draft_delete" ? "Draft deleted." : "Draft updated.") + "#drafts");
  }
  if (action === "pins_pause" || action === "pins_resume") {
    const p = await getPins(env);
    p.paused = action === "pins_pause";
    await putPins(env, p);
    return redirect("/admin?msg=" + encodeURIComponent(p.paused ? "Pinterest pins paused." : "Pinterest pins resumed."));
  }
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
