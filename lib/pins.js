// Pinterest (AliExpress via Buffer) state for the dashboard, in KV key "pins".
export async function getPins(env) {
  const raw = await env.CHANNELS_KV.get("pins");
  return raw ? JSON.parse(raw) : { paused: false, total_scheduled: 0, recent: [], last_rows: [] };
}
export async function putPins(env, p) {
  await env.CHANNELS_KV.put("pins", JSON.stringify(p));
}
