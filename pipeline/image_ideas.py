"""Daily stock-image ideas for Magnific: what to make so it gets approved AND downloaded.

Buyers download seasonal images 3-8 weeks ahead, so ideas mix upcoming US seasons/events
with evergreen high-demand themes. Each idea has a ready prompt for free generators
(FLUX.1 schnell, Ideogram, Adobe Firefly), aspect ratio, starter keywords and approval tips.
Sent to the dashboard (/admin -> Magnific image ideas).

  python -m pipeline.image_ideas            # make today's ideas
  python -m pipeline.image_ideas --dry-run  # print the request only
"""

import argparse
import os
from datetime import datetime, timezone

from . import common, content, dashboard

SCHEMA = {
    "type": "object",
    "properties": {
        "season_note": {"type": "string"},
        "ideas": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "theme": {"type": "string"},
                    "why": {"type": "string"},
                    "kind": {"type": "string", "enum": ["seasonal", "evergreen", "trend"]},
                    "prompt": {"type": "string"},
                    "avoid": {"type": "string"},
                    "aspect": {"type": "string", "enum": ["16:9", "3:2", "1:1", "2:3", "9:16"]},
                    "best_tool": {"type": "string", "enum": ["FLUX.1 schnell", "Ideogram", "Adobe Firefly"]},
                    "keywords": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["theme", "why", "kind", "prompt", "avoid", "aspect", "best_tool", "keywords"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["season_note", "ideas"],
    "additionalProperties": False,
}

SYSTEM = """You are a stock-content strategist for a contributor on Magnific (formerly Freepik),
selling AI-generated photos/illustrations to mostly US buyers (designers, marketers, bloggers).

Make 10 image ideas for today's date:
- 4 seasonal: US holidays, seasons and events 3 to 8 weeks AFTER today (buyers prepare early).
- 4 evergreen with steady demand: business/teamwork, home office, healthy food, wellness,
  technology and AI concepts, finance, education, abstract backgrounds with copy space,
  diverse everyday lifestyle.
- 2 trend: visual styles or topics rising now (be realistic, no made-up statistics).

Rules so images get APPROVED (Magnific rejects these):
- No visible text, letters, logos, brands, trademarks, famous places' signage, real people
  or celebrities, artists' names or "in the style of" living artists.
- Avoid close-ups of hands/fingers and crowds of faces (AI malformations). Prefer objects,
  scenes, flat lays, backgrounds, people at medium distance.
- Useful for designers: clean composition, copy space where it fits, good light.
- Each prompt must be clearly different from the others (no near-duplicates).

Quality (Magnific rejects "Low quality" a lot): ask for real, detailed textures (wood grain,
linen weave, knit wool, ceramic glaze, skin pores at medium distance), natural light with
soft shadows, realistic depth of field, muted true-to-life colours, simple uncluttered
composition with few objects (fewer objects = fewer AI errors). Avoid "8k, ultra HD,
hyperrealistic" fluff, glossy plastic looks, heavy bokeh orbs, neon overload.

Prompt style: one paragraph, 40-80 words, photographic or illustration details (subject,
setting, light, camera/lens or art style, colors, mood, composition, "copy space on the
left" when useful). English only.

why: one short sentence on who buys it and when. avoid: what to check/reject before upload.
best_tool: prefer Adobe Firefly (large output, no upscaling needed) for photos and
lifestyle; Ideogram for graphic/illustration/poster looks; FLUX.1 schnell only for simple
photoreal objects or backgrounds. keywords: 10 lowercase buyer search terms.
season_note: one sentence on what buyers are preparing for right now."""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--pack", type=int, default=0, help="also make N extra batches for the prompt pack")
    args = ap.parse_args()
    today = datetime.now(timezone.utc)
    from datetime import timedelta
    a, b = today + timedelta(weeks=3), today + timedelta(weeks=8)
    user = ("Today is {0} ({1}). Seasonal ideas must be for events/seasons between {2} and {3}; "
            "do NOT suggest anything that happens before {2} (too late for buyers). "
            "Write today's 10 ideas.").format(today.strftime("%Y-%m-%d"), today.strftime("%A"),
                                            a.strftime("%B %d"), b.strftime("%B %d"))
    if args.dry_run:
        print(user)
        return
    res = content._call_json(SYSTEM, user, SCHEMA, common.settings(), 6000)
    ideas = res.get("ideas", [])[:12]
    bad = ("logo", "brand", "celebrity", "in the style of")
    for i in ideas:
        if any(b in i["prompt"].lower() for b in bad):
            i["avoid"] = ("Prompt mentions a brand/style word; edit before using. " + i["avoid"]).strip()
    payload = {"date": today.strftime("%Y-%m-%d"), "created": today.strftime("%Y-%m-%dT%H:%M:%SZ"),
               "season_note": res.get("season_note", ""), "ideas": ideas}
    if dashboard.enabled():
        dashboard.ideas_report(payload)
    common.log("ideas ready: {0}".format(len(ideas)))
    extra = []
    for _ in range(args.pack):
        more = content._call_json(SYSTEM, user + " Make them different from these themes: " +
                                  "; ".join(i["theme"] for i in ideas + extra), SCHEMA, common.settings(), 6000)
        extra += more.get("ideas", [])
    add_to_pack(ideas + extra, today.strftime("%Y-%m-%d"))


PACK = os.path.join(common.DATA_DIR, "prompt_pack.json")


def add_to_pack(ideas, date):
    """Newest prompts first, unique by theme, max 100 (used by /free/ai-prompts/)."""
    pack = common.load_json(PACK, {"prompts": []})
    seen, out = set(), []
    for i in [dict(theme=x["theme"], prompt=x["prompt"], tool=x["best_tool"], aspect=x["aspect"], date=date)
              for x in ideas] + pack["prompts"]:
        k = i["theme"].strip().lower()
        if k not in seen and not any(b in i["prompt"].lower() for b in ("logo", "brand", "celebrity", "in the style of")):
            seen.add(k)
            out.append(i)
    common.save_json(PACK, {"updated": date, "prompts": out[:100]})
    common.log("prompt pack: {0}".format(len(out[:100])))


if __name__ == "__main__":
    main()
