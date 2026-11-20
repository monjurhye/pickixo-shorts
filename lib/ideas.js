// Magnific image ideas for the dashboard, in KV key "ideas".
export async function getIdeas(env) {
  const raw = await env.CHANNELS_KV.get("ideas");
  return raw ? JSON.parse(raw) : { date: "", ideas: [] };
}

// Ideas are made only when the owner presses the button (KV key "ideas_request"),
// so no OpenAI cost on days nobody asks.
export async function getIdeasRequest(env) {
  const raw = await env.CHANNELS_KV.get("ideas_request");
  return raw ? JSON.parse(raw) : null;
}
export async function setIdeasRequest(env, req) {
  if (req) await env.CHANNELS_KV.put("ideas_request", JSON.stringify(req));
  else await env.CHANNELS_KV.delete("ideas_request");
}
