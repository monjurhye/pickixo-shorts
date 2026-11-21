// POST /admin/action  -> pause/resume/disconnect a channel, or pause/resume everything
import { getState, putState, redirect, session } from "../../lib/dashboard.js";
import { getPins, putPins } from "../../lib/pins.js";
import { setIdeasRequest } from "../../lib/ideas.js";
import { getEarnings, putManual } from "../../lib/earnings.js";
import { getXp, putXp } from "../../lib/xpost.js";
import { getMtlCfg, putMtlCfg } from "../../lib/mtl.js";

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
  if (action === "fb_select" || action === "fb_disconnect") {
    const raw = await env.CHANNELS_KV.get("fbpages");
    const d = raw ? JSON.parse(raw) : { pages: [] };
    if (action === "fb_disconnect") await env.CHANNELS_KV.delete("fbpages");
    else { d.active = String(form.get("page") || ""); await env.CHANNELS_KV.put("fbpages", JSON.stringify(d)); }
    return redirect("/admin?msg=" + encodeURIComponent(action === "fb_disconnect" ? "Facebook disconnected." : "Active Page changed.") + "#facebook");
  }
  if (action === "earn_add" || action === "cost_add" || action === "monthly_add" || action === "earn_del") {
    const { manual } = await getEarnings(env);
    const f = (k, n) => String(form.get(k) || "").trim().slice(0, n);
    const amount = Math.round(parseFloat(f("amount", 20)) * 100) / 100;
    const id = Date.now().toString(36);
    const date = /^\d{4}-\d{2}-\d{2}$/.test(f("date", 10)) ? f("date", 10) : new Date().toISOString().slice(0, 10);
    let m = "Saved.";
    if (action === "earn_del") {
      const kind = f("kind", 10), del = f("id", 20);
      if (manual[kind]) manual[kind] = manual[kind].filter((x) => x.id !== del);
      m = "Removed.";
    } else if (!(amount > 0)) {
      return redirect("/admin?msg=" + encodeURIComponent("Amount must be a number above 0.") + "#earnings");
    } else if (action === "earn_add") {
      manual.income.unshift({ id, date, source: f("source", 40) || "Other", amount, note: f("note", 120) });
    } else if (action === "cost_add") {
      manual.costs.unshift({ id, date, item: f("item", 40) || "Other", amount, note: f("note", 120) });
    } else {
      manual.monthly.push({ id, item: f("item", 40) || "Other", amount });
    }
    manual.income = manual.income.slice(0, 1000); manual.costs = manual.costs.slice(0, 1000); manual.monthly = manual.monthly.slice(0, 30);
    await putManual(env, manual);
    return redirect("/admin?msg=" + encodeURIComponent(m) + "#earnings");
  }
  if (action === "mtl_auto" || action === "mtl_disconnect") {
    const c = await getMtlCfg(env);
    if (action === "mtl_disconnect") delete c.page; else c.off = !c.off;
    await putMtlCfg(env, c);
    return redirect("/admin?msg=" + encodeURIComponent(action === "mtl_disconnect" ? "Modern Tech Life disconnected." : (c.off ? "Auto-post off." : "Auto-post on.")) + "#mtl");
  }
  if (action.startsWith("xp_")) {
    const xp = await getXp(env);
    const f = (k, n) => String(form.get(k) || "").trim().slice(0, n);
    let m = "Saved.";
    if (action === "xp_page") xp.meta.active = f("page", 40);
    else if (action === "xp_toggle") { const k = f("platform", 20); xp.off[k] = !xp.off[k]; m = k + (xp.off[k] ? " off." : " on."); }
    else if (action === "xp_pause") { xp.paused = !xp.paused; m = xp.paused ? "Cross-posting paused." : "Cross-posting resumed."; }
    else if (action === "xp_bsky") {
      const handle = f("handle", 100).replace(/^@/, ""), pw = f("app_password", 40);
      if (!/^[a-z0-9.-]+\.[a-z]{2,}$/i.test(handle) || !/^[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}$/i.test(pw))
        return redirect("/admin?msg=" + encodeURIComponent("Use your handle (name.bsky.social) and an App Password like xxxx-xxxx-xxxx-xxxx (Bluesky → Settings → App passwords), not your login password.") + "#xpost");
      xp.bluesky = { handle, app_password: pw }; m = "Bluesky saved: @" + handle;
    } else if (action === "xp_disconnect") {
      const k = f("kind", 10);
      if (k === "meta") xp.meta = { pages: [], active: "" }; else if (k === "threads") delete xp.threads; else if (k === "bluesky") delete xp.bluesky;
      m = "Disconnected.";
    }
    await putXp(env, xp);
    return redirect("/admin?msg=" + encodeURIComponent(m) + "#xpost");
  }
  if (action === "ideas_request" || action === "ideas_cancel") {
    await setIdeasRequest(env, action === "ideas_request" ? { at: new Date().toISOString() } : null);
    return redirect("/admin?msg=" + encodeURIComponent(action === "ideas_request"
      ? "Requested. New prompts arrive in about 10-15 minutes (refresh this page)."
      : "Request cancelled.") + "#ideas");
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
