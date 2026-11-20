// Medium drafts for the dashboard, in KV key "drafts".
export async function getDrafts(env) {
  const raw = await env.CHANNELS_KV.get("drafts");
  return raw ? JSON.parse(raw) : { items: [], last_error: "" };
}
