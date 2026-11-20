// Magnific image ideas for the dashboard, in KV key "ideas".
export async function getIdeas(env) {
  const raw = await env.CHANNELS_KV.get("ideas");
  return raw ? JSON.parse(raw) : { date: "", ideas: [] };
}
