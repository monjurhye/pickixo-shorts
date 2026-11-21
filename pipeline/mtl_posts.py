"""Daily Bangla posts for the Facebook page "Modern Tech Life": 3 honest posts about earning
online with AI from Bangladesh.

Step 1 (web search): find ONE real, currently working way to earn with AI that a Bangladeshi
beginner can actually use (signup + payout possible from Bangladesh), with sources.
Step 2: write 3 Bangla posts from that research + the owner's REAL experience
(config/mtl_facts.json). Hard rules: no income promises, no made-up numbers, no scams.

Posts go to the dashboard (/admin -> Modern Tech Life) with copy buttons; the owner posts them.

  python -m pipeline.mtl_posts            # research + write + send to dashboard
  python -m pipeline.mtl_posts --dry-run  # print the prompts only (no API call)
"""

import argparse
import json
import os
from datetime import datetime, timedelta, timezone

from . import common, content, dashboard, facebook

STATE = os.path.join(common.DATA_DIR, "mtl_posts.json")
FACTS = os.path.join(common.CONFIG_DIR, "mtl_facts.json")

BANNED = ("betting, casino, gambling, lottery, crypto/forex trading signals, 'earn by watching ads/videos', "
          "'earn by clicking', MLM/referral pyramids, paid 'investment' apps, selling followers/likes, "
          "fake reviews, copying other people's content, cheating on AI-detection, bypassing platform rules")

RESEARCH_SYSTEM = """You research REAL ways to earn money online with AI tools for a beginner living
in Bangladesh. Use web search. Pick ONE method that:
- is legal, legitimate and currently working (check recent sources from 2025-2026),
- a person in Bangladesh can sign up for AND get paid from (say how: Payoneer, bank transfer,
  bKash via a partner, etc. Only state what a source supports; if unclear, say "unclear"),
- does not need upfront payment beyond a phone/computer and internet (say if any cost exists),
- is NOT any of: """ + BANNED + """.
Avoid the topics listed by the user (already covered).
Report plainly in English: method name, what exactly you do, free tools used, platform rules
(especially rules about AI content), how payment reaches Bangladesh, realistic time before the
first income, realistic earning range ONLY if a source states one (with the source), main risks
and common reasons people fail. Include the source URLs you used."""

POSTS_SCHEMA = {
    "type": "object",
    "properties": {
        "topic": {"type": "string"},
        "posts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "slot": {"type": "string", "enum": ["morning", "afternoon", "evening"]},
                    "kind": {"type": "string"},
                    "text": {"type": "string"},
                    "hashtags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["slot", "kind", "text", "hashtags"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["topic", "posts"],
    "additionalProperties": False,
}

WRITE_SYSTEM = """You write Facebook posts in natural, simple Bangla (Bangla script; English only for
tool and site names) for the page "Modern Tech Life", whose owner shares honestly what he builds,
how he plans income and what he really earns. Audience: Bangladeshi beginners.

Write exactly 3 posts for today:
1. morning, kind "how-to": the researched method, step by step (5 to 8 short steps), which free
   tools, platform rules, how money reaches Bangladesh, realistic time to first income.
2. afternoon, kind "my real result": ONLY from the owner's facts given below. Real numbers,
   including failures and small amounts. Never invent results, followers, sales or income.
3. evening, kind "warning or question": a common scam/mistake around this topic and how to spot
   it, OR one honest question to the audience. No fear-mongering.

Honesty rules (most important):
- NEVER promise or imply guaranteed income, "easy money", "passive income in X days" or big
  numbers. If you mention money, use only figures from the research sources (say they vary) or
  from the owner's facts.
- Say clearly that results take time, many people earn nothing at first, and effort is needed.
- If the research says something is unclear (e.g. payout to Bangladesh), say it is unclear.
- Nothing from this list: """ + BANNED + """.
- If a link is affiliate, say so. No clickbait, no ALL CAPS, at most 3 emojis per post.
- 80 to 200 words per post. End the how-to with one line: "উৎস:" plus 1-2 source site names.
hashtags: 3 to 5, Bangla or English, no spaces inside a tag, without the # sign."""


def load_state():
    return common.load_json(STATE, {}) or {"recent_topics": []}


def research(topics_done, cfg):
    import openai
    client = openai.OpenAI()
    user = "Already covered (do not repeat): " + ("; ".join(topics_done[-20:]) or "nothing yet")
    params = dict(model=cfg.get("mtl_model", "gpt-5-nano"), instructions=RESEARCH_SYSTEM, input=user,
                  tools=[{"type": "web_search"}], tool_choice="required",
                  include=["web_search_call.action.sources"], max_output_tokens=12000)
    try:
        resp = client.responses.create(reasoning={"effort": cfg.get("mtl_effort", "medium")}, **params)
    except openai.BadRequestError as e:
        if "reasoning" in str(e).lower() or "tool_choice" in str(e).lower():
            params.pop("tool_choice", None)
            resp = client.responses.create(**params)
        else:
            raise
    from .product_finder import _tool_urls
    urls = list(dict.fromkeys(_tool_urls(resp)))[:8]
    return (getattr(resp, "output_text", "") or "").strip(), urls


# Bangladesh time (UTC+6) each slot goes live on the page
SLOT_BD = {"morning": (9, 0), "afternoon": (14, 0), "evening": (20, 0)}


def auto_post(posts, today):
    """Schedule today's posts on the Modern Tech Life page (if picked + auto on in /admin).
    A post with a warning is NOT posted: it waits in /admin for a human."""
    try:
        code, cfg = dashboard._call("/api/pipeline/mtl")
    except Exception as e:
        common.log("mtl: page config failed: {0}".format(e))
        return
    page = (cfg or {}).get("page") if code == 200 else None
    if not (cfg or {}).get("auto") or not page:
        common.log("mtl: auto-post off or no page picked (/admin -> Modern Tech Life)")
        return
    now = datetime.now(timezone.utc)
    for n, p in enumerate(posts):
        if p.get("warning"):
            p["fb"] = "not posted: " + p["warning"]
            continue
        h, m = SLOT_BD.get(p.get("slot"), (20, 0))
        when = datetime.strptime(today, "%Y-%m-%d").replace(hour=h, minute=m, tzinfo=timezone.utc) - timedelta(hours=6)
        if when < now + timedelta(minutes=15):          # late run: post soon instead, 30 min apart
            when = now + timedelta(minutes=20 + 30 * n)
        msg = p["text"].strip() + "\n\n" + " ".join("#" + t.lstrip("#") for t in p.get("hashtags", []))
        try:
            r = facebook.schedule_text_on(page["id"], page["token"], msg, when)
            p["fb"] = "scheduled {0} BD".format((when + timedelta(hours=6)).strftime("%H:%M")) if r.get("id") else "error: no id"
        except Exception as e:
            p["fb"] = "error: {0}".format(str(e)[:150])
        common.log("mtl: {0} -> {1}".format(p.get("slot"), p["fb"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    cfg = common.settings()
    st = load_state()
    facts = common.load_json(FACTS, {}).get("facts", [])
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if args.dry_run:
        print(RESEARCH_SYSTEM[:400], "...\n\nfacts:", facts)
        return
    notes, urls = research(st["recent_topics"], cfg)
    if not notes:
        raise SystemExit("research returned nothing")
    user = ("Today is {0}.\n\nRESEARCH (use only this for the how-to and warning):\n{1}\n\nSOURCES:\n{2}\n\n"
            "OWNER'S REAL FACTS (the only allowed 'my result' material):\n- {3}").format(
        today, notes[:9000], "\n".join(urls), "\n- ".join(facts))
    res = content._call_json(WRITE_SYSTEM, user, POSTS_SCHEMA, cfg, 6000)
    posts = res.get("posts", [])[:3]
    # last guard: flag hype words a human must fix before posting
    hype = ("গ্যারান্টি", "নিশ্চিত আয়", "নিশ্চিতভাবে আয়", "guaranteed", "সহজে লাখ", "রাতারাতি", "100%")
    for p in posts:
        p["warning"] = "Check: contains hype word" if any(h.lower() in p["text"].lower() for h in hype) else ""
    st["recent_topics"] = (st["recent_topics"] + [res.get("topic", "")])[-40:]
    st["last"] = today
    common.save_json(STATE, st)
    if dashboard.enabled():
        auto_post(posts, today)
    payload = {"date": today, "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "topic": res.get("topic", ""), "sources": urls, "posts": posts}
    common.log("mtl: {0} ({1} posts, {2} sources)".format(payload["topic"], len(posts), len(urls)))
    if dashboard.enabled():
        code, data = dashboard._call("/api/pipeline/mtl", payload)
        common.log("dashboard mtl: {0} {1}".format(code, data))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
