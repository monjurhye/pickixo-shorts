// POST /api/pipeline/earnings {"updated","days":{date:{source:amount}},"notes":[...]}  (header X-Pipeline-Key)
import { json, pipelineAuthorized } from "../../../lib/dashboard.js";

export async function onRequestPost(context) {
  if (!pipelineAuthorized(context)) return json({ error: "unauthorized" }, 401);
  const b = await context.request.json();
  const clean = (obj) => {
    const out = {};
    for (const [d, srcs] of Object.entries(obj || {}).slice(0, 400)) {
      if (!/^\d{4}-\d{2}-\d{2}$/.test(d)) continue;
      out[d] = {};
      for (const [k, v] of Object.entries(srcs || {}).slice(0, 20)) out[d][String(k).slice(0, 40)] = Number(v) || 0;
    }
    return out;
  };
  await context.env.CHANNELS_KV.put("earnings_auto", JSON.stringify({
    updated: String(b.updated || "").slice(0, 30), days: clean(b.days), costs: clean(b.costs),
    notes: (b.notes || []).slice(0, 10).map((n) => String(n).slice(0, 200)) }));
  return json({ ok: true });
}
