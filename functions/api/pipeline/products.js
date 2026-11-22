// GET /api/pipeline/products -> {"products":[{"asin","name","channels":[...]}]}  (header X-Pipeline-Key)
// Products the owner pasted in /admin -> Products (KV "admin_products").
import { json, pipelineAuthorized } from "../../../lib/dashboard.js";
import { getAdminProducts } from "../../../lib/products.js";

export async function onRequestGet(context) {
  if (!pipelineAuthorized(context)) return json({ error: "unauthorized" }, 401);
  const d = await getAdminProducts(context.env);
  return json({ products: d.products.map(({ asin, name, channels }) => ({ asin, name, channels })) });
}
