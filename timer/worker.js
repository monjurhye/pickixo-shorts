// Pickixo timer: a Cloudflare Worker with ONE cron trigger ("*/10 * * * *").
// GitHub's own schedule runs late or not at all, so this worker starts the GitHub
// workflows on time through the GitHub API (workflow_dispatch).
//
// Worker settings (Cloudflare dashboard > Workers > pickixo-timer > Settings):
//   Secret  GH_TOKEN     fine-grained GitHub token, repo monjurhye/pickixo-shorts only,
//                        permission "Actions: Read and write" (nothing else)
//   KV      CHANNELS_KV  the same namespace the shop dashboard uses (for the prompt button)
//   Trigger cron         */10 * * * *
//
// Open https://pickixo-timer.<account>.workers.dev/ to see the plan and the last runs.

const REPO = "monjurhye/pickixo-shorts";

// UTC "HH:MM" -> workflows to start (the cron fires every 10 minutes, so minutes are 00/10/20/...)
const PLAN = {
  "02:00": [["ideas.yml", { mode: "fb" }]],        // 8am Bangladesh: Facebook posts + Modern Tech Life posts
  "09:00": [["medium.yml", {}]],                    // AppSumo draft
  "11:30": [["pins.yml", {}]],                      // Pinterest pins for the day
  "12:00": [["products.yml", {}]],                  // product finder (only channels that need it)
  "13:00": [["daily.yml", {}]],                     // Shorts run 1 (8-9am US Eastern)
  "17:00": [["daily.yml", {}]],                     // Shorts run 2 (12-1pm US Eastern)
  "22:00": [["daily.yml", {}]],                     // Shorts run 3 (5-6pm US Eastern)
};

async function dispatch(env, workflow, inputs) {
  const r = await fetch(`https://api.github.com/repos/${REPO}/actions/workflows/${workflow}/dispatches`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.GH_TOKEN}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "pickixo-timer",
    },
    body: JSON.stringify({ ref: "main", inputs }),
  });
  return r.status === 204 ? "ok" : `HTTP ${r.status} ${(await r.text()).slice(0, 200)}`;
}

async function log(env, line) {
  if (!env.CHANNELS_KV) return;
  const raw = await env.CHANNELS_KV.get("timer_log");
  const items = raw ? JSON.parse(raw) : [];
  items.unshift(new Date().toISOString().slice(0, 16) + "Z " + line);
  await env.CHANNELS_KV.put("timer_log", JSON.stringify(items.slice(0, 60)));
}

async function tick(env, when) {
  const d = new Date(when);
  // round down to the 10-minute slot, so a trigger that fires a little late still matches
  const slot = String(d.getUTCHours()).padStart(2, "0") + ":" + String(Math.floor(d.getUTCMinutes() / 10) * 10).padStart(2, "0");
  for (const [wf, inputs] of PLAN[slot] || []) {
    await log(env, `${slot} ${wf} ${JSON.stringify(inputs)} -> ${await dispatch(env, wf, inputs)}`);
  }
  // "Make new prompts" button in /admin: start the ideas workflow only when it was pressed
  if (env.CHANNELS_KV && (await env.CHANNELS_KV.get("ideas_request"))) {
    const last = await env.CHANNELS_KV.get("timer_ideas_sent");
    if (!last || Date.now() - Number(last) > 20 * 60 * 1000) {   // at most one start per 20 min
      await env.CHANNELS_KV.put("timer_ideas_sent", String(Date.now()));
      await log(env, `${slot} ideas.yml {"mode":"ideas"} -> ${await dispatch(env, "ideas.yml", { mode: "ideas" })}`);
    }
  }
}

export default {
  async scheduled(event, env, ctx) {
    ctx.waitUntil(tick(env, event.scheduledTime));
  },
  async fetch(request, env) {
    const raw = env.CHANNELS_KV ? await env.CHANNELS_KV.get("timer_log") : null;
    const plan = Object.entries(PLAN).map(([t, w]) => `${t} UTC  ${w.map((x) => x[0]).join(", ")}`).join("\n");
    return new Response(
      `Pickixo timer\n\nToken set: ${env.GH_TOKEN ? "yes" : "NO"}\nKV bound: ${env.CHANNELS_KV ? "yes" : "NO"}\n\n` +
      `Plan (every day):\n${plan}\n+ every 10 min: ideas.yml if the prompt button was pressed\n\n` +
      `Last runs:\n${raw ? JSON.parse(raw).join("\n") : "(none yet)"}\n`,
      { headers: { "content-type": "text/plain; charset=utf-8" } });
  },
};
