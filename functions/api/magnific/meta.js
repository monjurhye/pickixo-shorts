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
- quality_notes: one short sentence on the main weakness (or "clean").
- Images 3 and 4 (when present) are 100% crops of the most detailed areas: inspect every small
  object there (ribbons, tape, string, scissors, labels, leaves) at full size before answering.
  If markings MIGHT be text or numbers (e.g. a measuring-tape pattern), treat them as text.
- checks (answer each honestly, these decide acceptance):
  - text_or_numbers: true if ANY letters, digits, tick marks or scale markings are visible anywhere
    (measuring tapes, rulers, clocks, books, labels, packaging, screens, signs, receipts).
  - subject_sharp: true only if the main subject is crisp at 100% (the crop), not soft or smeared.
  - hazy_or_noisy: true if the image is foggy/dreamy, mostly out of focus, dark with grain/noise,
    or heavy glow/bloom hides detail.
  - fiddly_objects_broken: true if scissors, cutlery, string/twine/ribbon, jewelry, plants or hands
    look tangled, melted, merged or physically impossible.`;

const SCHEMA = {
  type: "object",
  properties: {
    title: { type: "string" },
    keywords: { type: "array", items: { type: "string" } },
    category: { type: "string", enum: CATEGORIES },
    problems: { type: "array", items: { type: "string" } },
    quality: { type: "integer" },
    quality_notes: { type: "string" },
    checks: {
      type: "object",
      properties: {
        text_or_numbers: { type: "boolean" },
        subject_sharp: { type: "boolean" },
        hazy_or_noisy: { type: "boolean" },
        fiddly_objects_broken: { type: "boolean" },
      },
      required: ["text_or_numbers", "subject_sharp", "hazy_or_noisy", "fiddly_objects_broken"],
      additionalProperties: false,
    },
  },
  required: ["title", "keywords", "category", "problems", "quality", "quality_notes", "checks"],
  additionalProperties: false,
};

// Turn the yes/no checks into hard rules (Magnific rejected images for exactly these reasons).
function applyChecks(d) {
  const c = d.checks || {};
  const problems = d.problems || [];
  let cap = 10;
  const flag = (msg, max) => { if (!problems.some((p) => p.toLowerCase().includes(msg.split(" ")[0]))) problems.push(msg); cap = Math.min(cap, max); };
  if (c.text_or_numbers) flag("text or numbers visible (AI usually garbles them)", 5);
  if (c.fiddly_objects_broken) flag("small objects look tangled or broken", 5);
  if (c.subject_sharp === false) flag("main subject is not sharp at 100%", 6);
  if (c.hazy_or_noisy) flag("hazy, out of focus or noisy", 6);
  d.problems = problems;
  d.quality = Math.min(Number(d.quality) || 0, cap);
  return d;
}

export async function onRequestPost(context) {
  const { env, request } = context;
  if (!(await session(context))) return json({ error: "Sign in to the dashboard first." }, 401);
  if (!env.OPENAI_API_KEY) return json({ error: "OPENAI_API_KEY is not set in Cloudflare Pages (Settings → Variables and secrets)." }, 500);
  const b = await request.json();
  const ok = (s) => typeof s === "string" && s.length > 100 && s.length < 3_000_000;
  if (!ok(b.preview) || !ok(b.crop)) return json({ error: "bad image data" }, 400);
  const extra = (Array.isArray(b.extra) ? b.extra : []).filter(ok).slice(0, 2);
  const body = {
    model: "gpt-5-nano",
    instructions: INSTRUCTIONS,
    reasoning: { effort: "high" },
    max_output_tokens: 8000,
    text: { format: { type: "json_schema", name: "meta", strict: true, schema: SCHEMA } },
    input: [{ role: "user", content: [
      { type: "input_text", text: "Write the metadata. First image: whole picture (reduced). Second: 100% centre crop. Any further images: 100% crops of the most detailed areas." },
      { type: "input_image", image_url: "data:image/jpeg;base64," + b.preview },
      { type: "input_image", image_url: "data:image/jpeg;base64," + b.crop },
      ...extra.map((e) => ({ type: "input_image", image_url: "data:image/jpeg;base64," + e })),
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
      let d2;
      try { d2 = JSON.parse(text); } catch (e) { continue; }
      return json(applyChecks(d2));
    }
  }
  return json({ error: "AI gave no answer, try again" }, 502);
}
