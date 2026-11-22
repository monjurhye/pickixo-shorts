"""Daily stock-image ideas for Magnific: what to make so it gets approved AND downloaded.

Buyers download seasonal images 3-8 weeks ahead, so ideas mix upcoming US seasons/events
with evergreen high-demand themes. Each idea has a ready prompt for Adobe Firefly
(firefly.adobe.com), aspect ratio, starter keywords and approval tips.
Written by Google Gemini (free tier, GEMINI_API_KEY). Sent to the dashboard (/admin -> Magnific image ideas).

  python -m pipeline.image_ideas            # make today's ideas
  python -m pipeline.image_ideas --dry-run  # print the request only
"""

import argparse
import os
from datetime import datetime, timezone

from . import common, dashboard, gemini

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
                    "aspect": {"type": "string", "enum": ["1:1"]},
                    "best_tool": {"type": "string", "enum": ["Adobe Firefly"]},
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

Make exactly 4 image ideas for today's date, all for Adobe Firefly (firefly.adobe.com).
EVERY idea is a TOP-DOWN FLAT-LAY real photograph, aspect ratio 1:1 (this style gets approved;
others were rejected). Only the subject changes between ideas:
- 2 seasonal: US holidays, seasons and events 3 to 8 weeks AFTER today (buyers prepare early).
- 1 evergreen with steady demand: business/teamwork, home office, healthy food, wellness,
  technology and AI concepts, finance, education, abstract backgrounds with copy space,
  diverse everyday lifestyle.
- 1 trend: visual styles or topics rising now (be realistic, no made-up statistics).

Rules so images get APPROVED (Magnific rejects these):
- No visible text, letters, logos, brands, trademarks, famous places' signage, real people
  or celebrities, artists' names or "in the style of" living artists.
- Avoid close-ups of hands/fingers and crowds of faces (AI malformations). Prefer objects,
  scenes, flat lays, backgrounds, people at medium distance.
- Useful for designers: clean composition, copy space where it fits, good light.
- Each prompt must be clearly different from the others (no near-duplicates).
- NO objects that carry marks AI garbles: measuring tapes, rulers, clocks/watches, calendars,
  books/notebooks with pages showing, newspapers, labels, price tags, packaging print, keyboards,
  screens, maps, signs, receipts, game boards with numbers. Closed plain notebooks are fine.
- NO fiddly small objects AI tangles or melts: scissors, twine/string/ribbon/yarn piles,
  jewelry chains, cutlery bundles, cables, wire, lace, eyeglasses, hands holding small things.
- NO mood that hides detail: fog, mist, haze, steam clouds, rain on windows, dim candle-light,
  heavy glow/bloom, dreamy soft focus, very dark scenes. The main subject must be in SHARP focus
  with bright, even daylight; only a gentle background blur is allowed.
- Flat lay seen straight from above: 3 to 5 simple objects lying on ONE plain surface (light linen
  tablecloth, light oak table, white marble, kraft paper, plain ceramic tile), arranged loosely
  with plenty of empty space around them for text. The objects must be SMALL in the frame
  (together about one third of the picture), ALL fully inside the frame with wide margins:
  nothing touching or cut off at any edge (a cut-off lemon and mug handle got an image rejected).
  Simple shapes (whole fruit, ceramics, bowls, broad leaves, wooden spoons, plain mugs, closed
  plain notebooks, folded linen) work best. NO herbs or plants with many thin needles or tiny
  leaves (rosemary, pine, thyme, dill): use broad leaves (bay, eucalyptus, olive) instead.
- NO people, NO hands, NO glossy plastic products, NO single "hero product" on a blank backdrop,
  NO 3D-render or CGI look.

Quality (Magnific rejects "Low quality" a lot): ask for real, detailed textures (wood grain,
linen weave, knit wool, ceramic glaze, skin pores at medium distance), natural light with
soft shadows, realistic depth of field, muted true-to-life colours, simple uncluttered
composition with few objects (fewer objects = fewer AI errors). Avoid "8k, ultra HD,
hyperrealistic" fluff, glossy plastic looks, heavy bokeh orbs, neon overload.

Prompt style: one paragraph, 45-75 words, written like this example (keep its structure,
change the subject):
"Top-down real photograph of three whole oranges and one halved orange on a light beige linen
tablecloth, with a small ceramic bowl of cloves. Natural textured orange peel with pores and tiny
imperfections, matte not glossy. Bright even daylight with soft shadows, everything in sharp
focus. All objects small and fully inside the frame with wide empty margins on every side,
nothing cut off at the edges. Clean minimal composition with plenty of empty space for text. Muted
natural colors."
Always say: "Top-down real photograph", the surface, natural texture with small imperfections,
"matte not glossy" for shiny things, bright even daylight with soft shadows, everything in sharp
focus, "all objects small and fully inside the frame with wide empty margins on every side,
nothing cut off at the edges", plenty of empty space for text, muted natural colors. English only.

why: one short sentence on who buys it and when. avoid: what to check/reject before upload.
Write every prompt for Adobe Firefly Image (it understands plain descriptive English;
no weights, no negative-prompt syntax, no "--ar" flags). best_tool: always "Adobe Firefly". keywords: 10 lowercase buyer search terms.
season_note: one sentence on what buyers are preparing for right now."""


# Words that got (or usually get) AI stock images rejected: garbled marks, tangled small
# objects, hazy/dim moods. Flagged on the idea card if the model still uses them.
RISKY = ("rosemary", "pine", "thyme", "dill", "hand ", "hands", "person", "woman", "man ", "3d", "render", "glossy", "measuring tape", "tape measure", "ruler", "clock", "watch", "calendar", "newspaper",
         "open book", "label", "price tag", "scissors", "twine", "string", "ribbon", "yarn",
         "lace", "chain", "fog", "mist", "haze", "steam", "rain on", "candlelight", "candle light",
         "dim light", "dreamy", "glow")


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
            "Write today's 4 ideas.").format(today.strftime("%Y-%m-%d"), today.strftime("%A"),
                                            a.strftime("%B %d"), b.strftime("%B %d"))
    if args.dry_run:
        print(user)
        return
    if not gemini.enabled():
        raise SystemExit("GEMINI_API_KEY is not set (free key: https://aistudio.google.com/apikey)")
    res = gemini.call_json(SYSTEM, user, SCHEMA, common.settings(), 6000)
    ideas = res.get("ideas", [])[:4]
    for i in ideas:
        i["best_tool"] = "Adobe Firefly"
        i["aspect"] = "1:1"   # flat lays only (approved style)
        if "cut off" not in i["prompt"].lower():   # the model sometimes drops this; it decides approval
            i["prompt"] = i["prompt"].rstrip(". ") + (". All objects small and fully inside the frame with wide "
                                                      "empty margins on every side, nothing cut off at the edges.")
    bad = ("logo", "brand", "celebrity", "in the style of")
    for i in ideas:
        if any(b in i["prompt"].lower() for b in bad):
            i["avoid"] = ("Prompt mentions a brand/style word; edit before using. " + i["avoid"]).strip()
        risky = [w for w in RISKY if w in i["prompt"].lower()]
        if risky:
            i["avoid"] = ("Risky for approval ({0}): remove before using. ".format(", ".join(risky)) + i["avoid"]).strip()
    payload = {"date": today.strftime("%Y-%m-%d"), "created": today.strftime("%Y-%m-%dT%H:%M:%SZ"),
               "season_note": res.get("season_note", ""), "ideas": ideas}
    if dashboard.enabled():
        dashboard.ideas_report(payload)
    common.log("ideas ready: {0}".format(len(ideas)))
    extra = []
    for _ in range(args.pack):
        more = gemini.call_json(SYSTEM, user + " Make them different from these themes: " +
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
