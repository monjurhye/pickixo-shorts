// Play Store app/game/tool ideas made by the "Suggest an app idea" button (KV "app_ideas").
export async function getAppIdeas(env) {
  const raw = await env.CHANNELS_KV.get("app_ideas");
  const d = raw ? JSON.parse(raw) : {};
  d.items = d.items || [];
  return d;
}
