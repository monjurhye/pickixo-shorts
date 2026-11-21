// GET/POST /api/postback/<source>?k=<token>&payout=<amount>&id=<lead id>
// Called by an ad network on every lead (server-to-server). The amount is added to that day's
// income (Bangladesh date). Duplicate lead ids are ignored. The token comes from /admin -> Earnings.
import { json } from "../../../lib/dashboard.js";
import { POSTBACK_SOURCES, getEarnings, postbackToken, putPostback } from "../../../lib/earnings.js";

const AMOUNT_KEYS = ["payout", "amount", "commission", "revenue", "payout_usd", "earnings"];
const ID_KEYS = ["id", "lead_id", "leadid", "transaction_id", "tid", "conversion_id", "clickid", "click_id"];

async function handle(context) {
  const { env, request, params } = context;
  const source = String(params.source || "").toLowerCase();
  const name = POSTBACK_SOURCES[source];
  if (!name) return json({ error: "unknown source" }, 404);
  const q = new URL(request.url).searchParams;
  if (request.method === "POST") {
    try { for (const [k, v] of (await request.formData()).entries()) if (!q.has(k)) q.set(k, String(v)); } catch (e) { /* not a form */ }
  }
  if (!env.PIPELINE_KEY || q.get("k") !== (await postbackToken(env, source))) return json({ error: "unauthorized" }, 401);
  const raw = AMOUNT_KEYS.map((k) => q.get(k)).find((v) => v !== null && v !== "");
  const amount = Math.round(parseFloat(String(raw || "").replace(/[^0-9.\-]/g, "")) * 100) / 100;
  if (!Number.isFinite(amount) || Math.abs(amount) > 1000) return json({ error: "bad amount" }, 400);
  const lead = ID_KEYS.map((k) => q.get(k)).find((v) => v);
  const { postback } = await getEarnings(env);
  const key = lead ? source + ":" + String(lead).slice(0, 80) : "";
  if (key && postback.ids.includes(key)) return json({ ok: true, duplicate: true });
  const day = new Date(Date.now() + 6 * 3600e3).toISOString().slice(0, 10);
  const d = (postback.days[day] = postback.days[day] || {});
  d[name] = Math.round(((d[name] || 0) + amount) * 100) / 100;
  if (key) postback.ids = [key, ...postback.ids].slice(0, 3000);
  postback.last[name] = new Date().toISOString();
  const keep = Object.keys(postback.days).sort().slice(-400);
  postback.days = Object.fromEntries(keep.map((k) => [k, postback.days[k]]));
  await putPostback(env, postback);
  return json({ ok: true });
}
export const onRequestGet = handle;
export const onRequestPost = handle;
