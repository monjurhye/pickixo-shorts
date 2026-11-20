// POST /api/magnific/meta  {"preview": "<base64 jpeg>", "crop": "<base64 jpeg>"}  (admin session)
// Asks OpenAI for stock metadata + a strict quality score. Needs Pages secret OPENAI_API_KEY.
import { json, session } from "../../../lib/dashboard.js";

const CATEGORIES = ["Backgrounds", "Business", "Food and drink", "Animals", "Nature", "Holidays",
  "Technology", "People", "Lifestyle", "Interiors", "Education", "Health", "Travel", "Sports",
  "Objects", "Abstract", "Industry", "Beauty and fashion"];

const INSTRUCTIONS = `You write stock-image metadata for Magnific (Freepik) buyers, mostly in the US.
Look at the image and return:
- title: 5 to 12 plain English words describing exactly what is shown. No brand names, no "AI",
  no "stock photo", no keyword stuffing.
- keywords: 40 to 44 single words or short phrases buyers would search, most important first:
  subject, objects, setting, colors, mood, concepts, possible uses ("background", "banner",
  "copy space" only if true). Lowercase, no brands, no people's names, no duplicates.
  Only describe what is really visible.
- category: the best one from the list.
- problems: anything that would get the image rejected: malformed hands/fingers/faces, garbled
  or fake text (look closely at calendars, books, signs, maps, labels: AI letters and numbers are
  usually gibberish), logos or brands, watermarks, a recognizable real person, blur, heavy
  artifacts, flat low-detail texture. Empty list if none.
- quality: 1-10, judged like a strict stock reviewer. The SECOND image is a 100% crop from the
  centre of the full-size file: judge real detail there. 7+ only if textures look natural (no
  plastic/waxy surfaces, no smeared details, no over-sharpened halos, no upscaling artifacts),
  light and composition are professional and nothing looks AI-broken. Any fake text = 5 or less.
- quality_notes: one short sentence on the main weakness (or "clean").`;

const SCHEMA = {
  type: "object",
  properties: {
    title: { type: "string" },
    keywords: { type: "array", items: { type: "string" } },
    category: { type: "string", enum: CATEGORIES },
    problems: { type: "array", items: { type: "string" } },
    quality: { type: "integer" },
    quality_notes: { type: "string" },
  },
  required: ["title", "keywords", "category", "problems", "quality", "quality_notes"],
  additionalProperties: false,
};

export async function onRequestPost(context) {
  const { env, request } = context;
  if (!(await session(context))) return json({ error: "Sign in to the dashboard first." }, 401);
  if (!env.OPENAI_API_KEY) return json({ error: "OPENAI_API_KEY is not set in Cloudflare Pages (Settings → Variables and secrets)." }, 500);
  const b = await request.json();
  const ok = (s) => typeof s === "string" && s.length > 100 && s.length < 3_000_000;
  if (!ok(b.preview) || !ok(b.crop)) return json({ error: "bad image data" }, 400);
  const body = {
    model: "gpt-5-nano",
    instructions: INSTRUCTIONS,
    reasoning: { effort: "low" },
    max_output_tokens: 8000,
    text: { format: { type: "json_schema", name: "meta", strict: true, schema: SCHEMA } },
    input: [{ role: "user", content: [
      { type: "input_text", text: "Write the metadata. First image: whole picture (reduced). Second: 100% centre crop." },
      { type: "input_image", image_url: "data:image/jpeg;base64," + b.preview },
      { type: "input_image", image_url: "data:image/jpeg;base64," + b.crop },
    ] }],
  };
  for (let attempt = 0; attempt < 2; attempt++) {
    const r = await fetch("https://api.openai.com/v1/responses", {
      method: "POST",
      headers: { "Authorization": "Bearer " + env.OPENAI_API_KEY, "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) return json({ error: "OpenAI " + r.status + ": " + ((d.error && d.error.message) || "").slice(0, 200) }, 502);
    let text = d.output_text || "";
    if (!text) for (const o of d.output || []) for (const c of o.content || []) if (c.type === "output_text") text += c.text;
    if (text.trim()) {
      try { return json(JSON.parse(text)); } catch (e) { /* retry */ }
    }
  }
  return json({ error: "AI gave no answer, try again" }, 502);
}
