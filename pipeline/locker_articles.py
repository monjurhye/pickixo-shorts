"""Daily helpful article that promotes one of the free AdBlueMedia-locked resources
(the AI prompt pack, the iOS-without-a-Mac ebook). Published automatically on the shop blog
and sent to the dashboard, where one click imports it into Medium.

The article must be useful on its own; the resource is offered once at the end, with a clear
note that the full version opens after one short sponsor offer. No money/prize promises.

  python -m pipeline.locker_articles            # write, publish on the blog, send to dashboard
  python -m pipeline.locker_articles --dry-run  # print the article, no API calls
"""

import argparse
import html
import os
import re
from datetime import datetime, timezone

from . import common, content, dashboard

STATE = os.path.join(common.DATA_DIR, "locker_articles.json")
BLOG_DIR = os.path.join(common.DATA_DIR, "blog")

RESOURCES = [
    {"key": "ai-prompts", "path": "/free/ai-prompts/", "name": "AI image prompt pack for stock sites",
     "offer": "a pack of AI image prompts for stock sites (seasonal ideas, keywords included)",
     "topics": [
         "How to pick AI image ideas that actually sell on stock sites",
         "Seasonal AI stock images: what buyers search for 4-8 weeks ahead",
         "Writing better AI image prompts for stock photos: a simple checklist",
         "Why AI stock images get rejected (and how to fix the common problems)",
         "Keywords and titles for AI stock images: a practical guide",
         "Five stock image niches that are easy to start with AI tools",
     ]},
    {"key": "ios-without-mac", "path": "/free/ios-without-mac/", "name": "free ebook: Publish an iOS App Without a Mac",
     "offer": "a free step-by-step ebook on publishing an iOS app without owning a Mac",
     "topics": [
         "Can you publish an iPhone app without a Mac? The options explained",
         "Cloud Macs, CI services and cross-platform tools for Windows developers",
         "App Store review checklist for first-time iOS developers",
         "From Flutter or React Native to the App Store without a Mac",
     ]},
]

SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "subtitle": {"type": "string"},
        "intro": {"type": "array", "items": {"type": "string"}},
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"heading": {"type": "string"},
                               "paragraphs": {"type": "array", "items": {"type": "string"}}},
                "required": ["heading", "paragraphs"],
                "additionalProperties": False,
            },
        },
        "closing": {"type": "array", "items": {"type": "string"}},
        "tags": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["title", "subtitle", "intro", "sections", "closing", "tags"],
    "additionalProperties": False,
}

WRITER = """You write practical Medium-style articles in plain US English.
The article must be genuinely useful on its own: concrete steps, examples and common mistakes.

Hard rules:
- No invented statistics, earnings, sales numbers, studies or quotes. No income promises
  ("make $X", "passive income guaranteed"). No personal stories ("I made", "I tested").
- No hype words (game-changer, revolutionary, must-have, unleash, secret) and no urgency.
- Do not mention any free resource, download, pack, ebook or link: that is added separately.
- No URLs in the text.

Shape:
- title: under 80 characters, specific and searchable. subtitle: one sentence.
- intro: 2 short paragraphs. sections: 4-5, each a heading + 2 short paragraphs.
- closing: 1-2 short paragraphs with a next step the reader can take today.
- tags: exactly 5 lowercase Medium topics."""

BANNED = ("i made", "i tested", "i earned", "passive income", "guaranteed", "game-changer",
          "game changer", "secret", "get rich", "today only", "http")
MONEY_RE = re.compile(r"[$€£]\s?\d")


def checks(art):
    blob = " ".join([art["title"], art["subtitle"]] + art["intro"] + art["closing"] +
                    [p for s in art["sections"] for p in s["paragraphs"]]).lower()
    issues = ["banned phrase: " + b for b in BANNED if b in blob]
    if MONEY_RE.search(blob):
        issues.append("mentions money")
    if len(art["sections"]) < 3:
        issues.append("too few sections")
    return issues


def render(art, res, url):
    e = html.escape
    h = []
    for p in art["intro"]:
        h.append("<p>{0}</p>".format(e(p)))
    for s in art["sections"]:
        h.append("<h2>{0}</h2>".format(e(s["heading"])))
        h += ["<p>{0}</p>".format(e(p)) for p in s["paragraphs"]]
    for p in art["closing"]:
        h.append("<p>{0}</p>".format(e(p)))
    h.append("<h2>Free resource</h2>")
    h.append('<p>If this helped, I put together {0}. A few samples are open to everyone; the full '
             'version unlocks after you complete one short sponsor offer (that is how it stays free). '
             '<a href="{1}">Get the {2}</a>.</p>'.format(e(res["offer"]), e(url), e(res["name"])))
    h.append("<p><em>This article was written with AI assistance. The sponsor offer is optional; "
             "nothing here promises earnings.</em></p>")
    return "\n".join(h)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    cfg = common.settings()
    st = common.load_json(STATE, {"index": 0, "done": []})
    i = st["index"]
    res = RESOURCES[i % len(RESOURCES)]
    topic = res["topics"][(i // len(RESOURCES)) % len(res["topics"])]
    url = cfg["site_url"].rstrip("/") + res["path"]

    if args.dry_run:
        art = {"title": topic, "subtitle": "A short practical guide.", "intro": ["Intro 1.", "Intro 2."],
               "sections": [{"heading": "Step %d" % n, "paragraphs": ["Do this.", "Avoid that."]} for n in range(1, 5)],
               "closing": ["Start with one small test today."], "tags": ["ai", "stock photography", "creators", "how to", "tips"]}
    else:
        art, issues = None, []
        for _ in range(2):
            art = content._call_json(WRITER, "Write the article: " + topic, SCHEMA, cfg, 3500)
            issues = checks(art)
            if not issues:
                break
        if issues:
            common.log("locker article rejected: " + "; ".join(issues))
            if dashboard.enabled():
                dashboard.draft_report({"error": "Locker article skipped: " + "; ".join(issues)[:250]})
            return

    body = render(art, res, url)
    now = datetime.now(timezone.utc)
    slug = "{0}-{1}".format(now.strftime("%Y-%m-%d"), common.slugify(art["title"], 60))
    tags = [t.strip().lower() for t in art["tags"]][:5]
    if args.dry_run:
        print(art["title"], "\n", body)
        return
    common.save_json(os.path.join(BLOG_DIR, slug + ".json"), {
        "slug": slug, "date": now.strftime("%Y-%m-%d"), "title": art["title"], "subtitle": art["subtitle"],
        "tags": tags, "products": [res["name"]], "html": body})
    blog_url = cfg["site_url"].rstrip("/") + "/blog/" + slug + "/"
    full = "<h1>{0}</h1>\n<h3>{1}</h3>\n{2}".format(html.escape(art["title"]), html.escape(art["subtitle"]), body)
    draft = {"id": "L" + now.strftime("%Y%m%d%H%M%S"), "created": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
             "title": art["title"], "subtitle": art["subtitle"], "tags": tags,
             "products": ["AdBlueMedia: " + res["name"]], "html": full,
             "markdown": re.sub(r"<[^>]+>", "", full), "blog_url": blog_url}
    st["index"] = i + 1
    st["done"] = (st["done"] + [slug])[-200:]
    common.save_json(STATE, st)
    if dashboard.enabled():
        dashboard.draft_report({"draft": draft})
    common.log("locker article published: " + blog_url)


if __name__ == "__main__":
    main()
