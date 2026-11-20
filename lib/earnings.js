// Earnings for the dashboard. KV "earnings_auto": {updated, days:{date:{source:amount}}, notes}
// (written by the GitHub pipeline). KV "earnings_manual": {income:[{id,date,source,amount,note}],
// costs:[{id,date,item,amount,note}], monthly:[{id,item,amount}]} (typed in /admin).
export async function getEarnings(env) {
  const [a, m] = await Promise.all([env.CHANNELS_KV.get("earnings_auto"), env.CHANNELS_KV.get("earnings_manual")]);
  const auto = a ? JSON.parse(a) : { updated: "", days: {}, notes: [] };
  const manual = m ? JSON.parse(m) : {};
  manual.income = manual.income || []; manual.costs = manual.costs || []; manual.monthly = manual.monthly || [];
  return { auto, manual };
}
export async function putManual(env, m) {
  await env.CHANNELS_KV.put("earnings_manual", JSON.stringify(m));
}
