// POST /admin/app-idea -> asks Claude (with web search) for ONE app / game / tool idea that a solo
// developer can publish on Google Play and has a real chance to rank. Runs only when the button in
// /admin -> Play Console is pressed (each press costs a little API money).
// Needs ANTHROPIC_API_KEY in Cloudflare Pages -> Settings -> Variables and Secrets (encrypted).
// KV "app_ideas": {items:[{at, name, type, category, keywords, why, competition, features, monetize, build_days, sources}]}
import { json, session } from "../../lib/dashboard.js";
import { getAppIdeas } from "../../lib/app_ideas.js";

const MODEL = "claude-opus-5-5";

function prompt(today, previous) {
  return `Today is ${today}. I am a solo developer in Bangladesh who publishes on Google Play (US/UK/CA audience preferred).
Suggest exactly ONE new app, game or tool that I could build and publish, chosen because it has a realistic chance to RANK
in Google Play search, not just because it is a nice idea.

Use web search to check, before you decide:
- what people are searching for right now (rising topics, seasonal needs for the coming weeks, new rules or devices),
- how crowded that search is on Google Play (search play.google.com for the main keyword: how many strong apps,
  their ratings, installs and last-update dates). Prefer keywords where the top results are old, low-rated or few.
Do not suggest anything that needs medical, financial or legal claims, gambling, copyrighted characters/brands,
or a big backend. It must be buildable by one person in about 1-3 weeks.
${previous.length ? "Do not repeat or closely copy these earlier suggestions: " + previous.join("; ") + "." : ""}

Reply with ONLY one JSON object, no other text, with these keys:
"name": a short Play Store app name (English, include the main keyword, max 30 characters),
"type": "app" or "game" or "tool",
"category": the Google Play category,
"keywords": array of 3-6 English search keywords to target,
"why": 2-3 sentences in Bangla: why this can rank now (what you found),
"competition": 1-2 sentences in Bangla about the current top results for the main keyword,
"features": array of 3-5 short Bangla strings (the minimum features for version 1),
"monetize": 1 sentence in Bangla (ads / one-time purchase / subscription),
"build_days": a number (estimated days of work).
Be honest: if the evidence is thin, say so in "why".`;
}

async function callClaude(env, text) {
  const messages = [{ role: "user", content: text }];
  let r;
  for (let i = 0; i < 4; i++) {
    const res = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "x-api-key": env.ANTHROPIC_API_KEY,
        "anthropic-version": "2026-10-21",
        "anthropic-beta": "server-side-fallback-2026-07-01",
      },
      body: JSON.stringify({
        model: MODEL,
        max_tokens: 16000,
        output_config: { effort: "medium" },
        fallbacks: "default",
        tools: [{ type: "web_search_20260209", name: "web_search", max_uses: 6 }],
        messages,
      }),
    });
    r = await res.json();
    if (!res.ok) throw new Error("Claude API " + res.status + ": " + ((r.error && r.error.message) || "error").slice(0, 200));
    if (r.stop_reason !== "pause_turn") break;
    messages.splice(1, messages.length - 1, { role: "assistant", content: r.content });  // resume the paused turn
  }
  if (r.stop_reason === "refusal") throw new Error("Claude declined this request; try again.");
  const out = (r.content || []).filter((b) => b.type === "text").map((b) => b.text).join("");
  const m = out.match(/\{[\s\S]*\}/);
  if (!m) throw new Error("Claude did not return an idea; try again.");
  const idea = JSON.parse(m[0]);
  const sources = [];
  for (const b of r.content || []) {
    if (b.type === "web_search_tool_result" && Array.isArray(b.content)) {
      for (const s of b.content) if (s.url && sources.length < 5 && !sources.some((x) => x.url === s.url)) sources.push({ url: s.url, title: s.title || s.url });
    }
  }
  return { idea, sources };
}

export async function onRequestPost(context) {
  const { env, request } = context;
  if (!(await session(context))) return json({ error: "Please sign in again." }, 401);
  const origin = request.headers.get("Origin");
  if (origin && origin !== new URL(request.url).origin) return json({ error: "Bad origin" }, 403);
  if (!env.ANTHROPIC_API_KEY) return json({ error: "ANTHROPIC_API_KEY is not set in Cloudflare Pages (Settings → Variables and Secrets)." }, 400);
  const d = await getAppIdeas(env);
  const today = new Date(Date.now() + 6 * 3600e3).toISOString().slice(0, 10);
  try {
    const { idea, sources } = await callClaude(env, prompt(today, d.items.slice(0, 15).map((x) => x.name)));
    const s = (v, n) => String(v || "").slice(0, n);
    const arr = (v, n) => (Array.isArray(v) ? v : []).slice(0, n).map((x) => s(x, 120));
    const item = { at: new Date().toISOString(), name: s(idea.name, 60), type: s(idea.type, 10), category: s(idea.category, 40),
      keywords: arr(idea.keywords, 6), why: s(idea.why, 700), competition: s(idea.competition, 500), features: arr(idea.features, 5),
      monetize: s(idea.monetize, 300), build_days: Number(idea.build_days) || 0, sources };
    d.items = [item, ...d.items].slice(0, 20);
    await env.CHANNELS_KV.put("app_ideas", JSON.stringify(d));
    return json({ ok: true, item });
  } catch (e) {
    return json({ error: String(e.message || e).slice(0, 300) }, 502);
  }
}
