// Earnings for the dashboard.
//   KV "earnings_auto":     {updated, days:{date:{source:amount}}, costs:{date:{item:amount}}, notes}
//                           (written by the GitHub pipeline: Impact, AliExpress, OpenAI/Anthropic costs)
//   KV "earnings_postback": {days:{date:{source:amount}}, ids:[...], last:{source:iso}}
//                           (written by networks that call /api/postback/<source>, e.g. AdBlueMedia)
//   KV "earnings_manual":   {income:[{id,date,source,amount,note}], costs:[{id,date,item,amount,note}],
//                           monthly:[{id,item,amount}]} (typed in /admin)
export const POSTBACK_SOURCES = { adbluemedia: "AdBlueMedia" };

export async function getEarnings(env) {
  const [a, m, p] = await Promise.all([env.CHANNELS_KV.get("earnings_auto"), env.CHANNELS_KV.get("earnings_manual"),
    env.CHANNELS_KV.get("earnings_postback")]);
  const auto = a ? JSON.parse(a) : { updated: "", days: {}, notes: [] };
  auto.days = auto.days || {}; auto.costs = auto.costs || {};
  const manual = m ? JSON.parse(m) : {};
  manual.income = manual.income || []; manual.costs = manual.costs || []; manual.monthly = manual.monthly || [];
  const postback = p ? JSON.parse(p) : {};
  postback.days = postback.days || {}; postback.ids = postback.ids || []; postback.last = postback.last || {};
  return { auto, manual, postback };
}
export async function putManual(env, m) {
  await env.CHANNELS_KV.put("earnings_manual", JSON.stringify(m));
}
export async function putPostback(env, p) {
  await env.CHANNELS_KV.put("earnings_postback", JSON.stringify(p));
}

// Secret token for a postback URL, derived from PIPELINE_KEY (no extra secret to set up).
export async function postbackToken(env, source) {
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode("postback:" + env.PIPELINE_KEY),
    { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const sig = new Uint8Array(await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(source)));
  return Array.from(sig.slice(0, 12), (b) => b.toString(16).padStart(2, "0")).join("");
}
