// Modern Tech Life page: direct daily posts (its own Facebook connection, not cross-post).
// KV "mtl_cfg": {page:{id,name,token,connected_at}, off}. Connected via /auth/fb-connect?for=mtl.
export async function getMtlCfg(env) {
  const raw = await env.CHANNELS_KV.get("mtl_cfg");
  return raw ? JSON.parse(raw) : {};
}
export async function putMtlCfg(env, d) {
  await env.CHANNELS_KV.put("mtl_cfg", JSON.stringify(d));
}
export async function mtlPage(env) {
  const cfg = await getMtlCfg(env);
  return { cfg, page: cfg.page && cfg.page.token ? cfg.page : null };
}
