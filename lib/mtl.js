// Modern Tech Life page for auto-posting. KV "mtl_cfg": {page_id, off}.
// Page tokens come from the Facebook connections already in KV ("xpost" Meta login, "fbpages").
import { getXp } from "./xpost.js";
import { getFb } from "./fb.js";

export async function mtlPages(env) {
  const [xp, fb] = await Promise.all([getXp(env), getFb(env)]);
  const all = [...(xp.meta.pages || []), ...(fb.pages || [])].filter((p) => p.id && p.token);
  return all.filter((p, i) => all.findIndex((q) => q.id === p.id) === i);
}
export async function getMtlCfg(env) {
  const raw = await env.CHANNELS_KV.get("mtl_cfg");
  return raw ? JSON.parse(raw) : {};
}
export async function putMtlCfg(env, d) {
  await env.CHANNELS_KV.put("mtl_cfg", JSON.stringify(d));
}
// picked page, else the one whose name says "Modern Tech Life"
export async function mtlPage(env) {
  const [cfg, pages] = await Promise.all([getMtlCfg(env), mtlPages(env)]);
  const page = pages.find((p) => p.id === cfg.page_id) || pages.find((p) => /modern\s*tech\s*life/i.test(p.name || ""));
  return { cfg, pages, page };
}
