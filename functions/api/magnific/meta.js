// POST /api/magnific/meta  (admin session)
//   {"mode":"meta",  "preview": "<b64 jpeg>"}                          -> title, keywords, category
//   {"mode":"check", "preview": "<b64>", "crop": "<b64>", "extra":[..]} -> strict quality check
// Google Gemini (free) when the Pages secret GEMINI_API_KEY is set, otherwise OpenAI (OPENAI_API_KEY).
import { json, session } from "../../../lib/dashboard.js";

const CATEGORIES = ["Backgrounds", "Business", "Food and drink", "Animals", "Nature", "Holidays",
  "Technology", "People", "Lifestyle", "Interiors", "Education", "Health", "Travel", "Sports",
  "Objects", "Abstract", "Industry", "Beauty and fashion"];

const META_INSTRUCTIONS = `You write stock-image metadata for Magnific (Freepik) buyers, mostly in the US.
Look at the image and return:
- title: 5 to 12 plain English words describing exactly what is shown. No brand names, no "AI",
  no "stock photo", no keyword stuffing.
- keywords: 40 to 44 single words or short phrases buyers would search, most important first:
  subject, objects, setting, colors, mood, concepts, possible uses ("background", "banner",
  "copy space" only if true). Lowercase, no brands, no people's names, no duplicates.
  Only describe what is really visible.
- category: the best one from the list.`;

const CHECK_INSTRUCTIONS = `You are a strict stock-image reviewer for Magnific (Freepik). Judge only quality.
- problems: anything that would get the image rejected: malformed hands/fingers/faces, garbled
  or fake text (look closely at calendars, books, signs, maps, labels: AI letters and numbers are
  usually gibberish), logos or brands, watermarks, a recognizable real person, blur, heavy
  artifacts, flat low-detail texture, a CGI/3D-render look. Empty list if none.
- quality: 1-10. The SECOND image is a 100% crop from the centre of the full-size file: judge real
  detail there. 7+ only if textures look natural (no plastic/waxy surfaces, no smeared details, no
  over-sharpened halos, no upscaling artifacts), light and composition are professional and
  nothing looks AI-broken. Any fake text = 5 or less.
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
    look tangled, melted, merged or physically impossible.
  - plastic_or_cgi: true if surfaces look waxy, glossy-plastic or like a 3D render instead of a photo.`;

const META_SCHEMA = {
  type: "object",
  properties: {
    title: { type: "string" },
    keywords: { type: "array", items: { type: "string" } },
    category: { type: "string", enum: CATEGORIES },
  },
  required: ["title", "keywords", "category"],
  additionalProperties: false,
};

const CHECK_SCHEMA = {
  type: "object",
  properties: {
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
        plastic_or_cgi: { type: "boolean" },
      },
      required: ["text_or_numbers", "subject_sharp", "hazy_or_noisy", "fiddly_objects_broken", "plastic_or_cgi"],
      additionalProperties: false,
    },
  },
  required: ["problems", "quality", "quality_notes", "checks"],
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
  if (c.plastic_or_cgi) flag("plastic/waxy or 3D-render look", 6);
  d.problems = problems;
  d.quality = Math.min(Number(d.quality) || 0, cap);
  return d;
}

const noAdditional = (x) => Array.isArray(x) ? x.map(noAdditional)
  : x && typeof x === "object" ? Object.fromEntries(Object.entries(x).filter(([k]) => k !== "additionalProperties").map(([k, v]) => [k, noAdditional(v)]))
  : x;

async function askGemini(env, instructions, schema, text, images) {
  const body = {
    systemInstruction: { parts: [{ text: instructions }] },
    contents: [{ role: "user", parts: [{ text }, ...images.map((b) => ({ inline_data: { mime_type: "image/jpeg", data: b } }))] }],
    generationConfig: { responseMimeType: "application/json", responseSchema: noAdditional(schema), maxOutputTokens: 4000 },
  };
  const model = env.GEMINI_MODEL || "gemini-flash-lite-latest";
  const r = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`, {
    method: "POST", headers: { "x-goog-api-key": env.GEMINI_API_KEY, "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  const d = await r.json().catch(() => ({}));
  if (r.status === 429) throw new Error("Gemini free limit reached for this minute: wait a minute and try again.");
  if (!r.ok) throw new Error("Gemini " + r.status + ": " + ((d.error && d.error.message) || "").slice(0, 200));
  const parts = (((d.candidates || [])[0] || {}).content || {}).parts || [];
  return parts.map((p) => p.text || "").join("");
}

async function askOpenAI(env, instructions, schema, text, images, effort) {
  const r = await fetch("https://api.openai.com/v1/responses", {
    method: "POST",
    headers: { "Authorization": "Bearer " + env.OPENAI_API_KEY, "Content-Type": "application/json" },
    body: JSON.stringify({
      model: "gpt-5-nano", instructions, reasoning: { effort }, max_output_tokens: 8000,
      text: { format: { type: "json_schema", name: "meta", strict: true, schema } },
      input: [{ role: "user", content: [{ type: "input_text", text },
        ...images.map((b) => ({ type: "input_image", image_url: "data:image/jpeg;base64," + b }))] }],
    }),
  });
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error("OpenAI " + r.status + ": " + ((d.error && d.error.message) || "").slice(0, 200));
  let out = d.output_text || "";
  if (!out) for (const o of d.output || []) for (const c of o.content || []) if (c.type === "output_text") out += c.text;
  return out;
}

export async function onRequestPost(context) {
  const { env, request } = context;
  if (!(await session(context))) return json({ error: "Sign in to the dashboard first." }, 401);
  if (!env.GEMINI_API_KEY && !env.OPENAI_API_KEY) return json({ error: "Set GEMINI_API_KEY (free) in Cloudflare Pages → Settings → Variables and secrets." }, 500);
  const b = await request.json();
  const ok = (s) => typeof s === "string" && s.length > 100 && s.length < 3_000_000;
  const check = b.mode === "check";
  if (!ok(b.preview) || (check && !ok(b.crop))) return json({ error: "bad image data" }, 400);
  const images = check ? [b.preview, b.crop, ...(Array.isArray(b.extra) ? b.extra : []).filter(ok).slice(0, 2)] : [b.preview];
  const text = check
    ? "Check this image. First image: whole picture (reduced). Second: 100% centre crop. Any further images: 100% crops of the most detailed areas."
    : "Write the metadata for this image.";
  const [instr, schema] = check ? [CHECK_INSTRUCTIONS, CHECK_SCHEMA] : [META_INSTRUCTIONS, META_SCHEMA];
  for (let attempt = 0; attempt < 2; attempt++) {
    let out;
    try {
      out = env.GEMINI_API_KEY ? await askGemini(env, instr, schema, text, images)
        : await askOpenAI(env, instr, schema, text, images, check ? "high" : "low");
    } catch (e) {
      return json({ error: String(e.message || e) }, 502);
    }
    if (!out.trim()) continue;
    let d;
    try { d = JSON.parse(out); } catch (e) { continue; }
    return json(check ? applyChecks(d) : d);
  }
  return json({ error: "AI gave no answer, try again" }, 502);
}
