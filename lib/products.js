// Amazon products the owner adds in /admin -> Products (KV "admin_products").
// {products:[{asin, name, channels:["ch01",..], added:"YYYY-MM-DD"}]}. The pipeline reads them through
// /api/pipeline/products and puts them first (before config/products.json and data/products.json).
export async function getAdminProducts(env) {
  const raw = await env.CHANNELS_KV.get("admin_products");
  return raw ? JSON.parse(raw) : { products: [] };
}

export async function putAdminProducts(env, d) {
  await env.CHANNELS_KV.put("admin_products", JSON.stringify(d));
}

// ASIN from a 10-character ASIN or an amazon.* product URL (/dp/, /gp/product/, /gp/aw/d/). "" if none.
export function parseAsin(text) {
  const t = String(text || "").trim();
  if (/^[A-Z0-9]{10}$/i.test(t)) return t.toUpperCase();
  if (!/^https?:\/\/([a-z0-9-]+\.)*amazon\.[a-z.]+\//i.test(t)) return "";
  const m = t.match(/\/(?:dp|gp\/product|gp\/aw\/d)\/([A-Z0-9]{10})(?:[/?#]|$)/i);
  return m ? m[1].toUpperCase() : "";
}
