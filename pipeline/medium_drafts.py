"""Daily Medium article DRAFTS about AppSumo deals (from the Impact API, read-only).

Each article is published automatically on the shop blog (shop.pickixo.com/blog/<slug>/,
data/blog/*.json -> site/build.py) and sent to the dashboard, where one click imports it into
Medium (Medium's own "Import a story" keeps the blog as the canonical source).

Honesty rules baked in: no invented first-person use ("I tested"), only facts from the
deal data, affiliate disclosure at the top, AI-assisted note at the end, links labelled
as AppSumo, tracking sub id "medium".

  python -m pipeline.medium_drafts            # make today's draft and send it to the dashboard
  python -m pipeline.medium_drafts --dry-run  # sample deals, no API calls, prints the draft
"""

import argparse
import html
import os
import random
import re
import urllib.parse
from datetime import datetime, timezone

from . import common, content, dashboard, impact

STATE = os.path.join(common.DATA_DIR, "medium.json")
FREE_DEALS = os.path.join(common.DATA_DIR, "free_deals.json")   # used by site/build.py -> /free/lifetime-deals/
APPSUMO_CAMPAIGN = 7443
SUB_ID = "medium"

DISCLOSURE = ("Disclosure: this post contains affiliate links. If you buy through them, "
              "I may earn a commission at no extra cost to you.")
AI_NOTE = ("This article was written with AI assistance from the deal information AppSumo publishes. "
           "Check each deal page for current terms before you buy.")
BLOG_DIR = os.path.join(common.DATA_DIR, "blog")

ARTICLE_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "subtitle": {"type": "string"},
        "intro": {"type": "array", "items": {"type": "string"}},
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "product": {"type": "string"},
                    "heading": {"type": "string"},
                    "paragraphs": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["product", "heading", "paragraphs"],
                "additionalProperties": False,
            },
        },
        "closing": {"type": "array", "items": {"type": "string"}},
        "tags": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["title", "subtitle", "intro", "sections", "closing", "tags"],
    "additionalProperties": False,
}

WRITER = """You draft Medium articles for US solopreneurs, freelancers and small business owners
about software deals on AppSumo. The author will edit the draft before publishing.

Hard rules:
- Use ONLY the facts given for each product (name, description, deal page). Do not invent
  features, prices, discounts, plan limits, ratings, user counts or deadlines.
- Never claim personal use. No "I tested", "I've been using", "in my experience". Write as a
  helpful researcher: what it does, who it suits, what to check before buying.
- For each product include one honest caveat (for example: lifetime deals depend on the
  company staying in business; check the plan limits and refund window on the deal page).
- No hype words (game-changer, revolutionary, must-have, unleash, elevate, seamless).
  No fake urgency (today only, selling out, last chance).
- Plain US English, short paragraphs, friendly and direct.
- Do not put any URLs in the text; links are added separately.

Shape:
- title: under 80 characters, specific and searchable (what a US reader would google).
- subtitle: one sentence.
- intro: 2 short paragraphs about the problem (too many monthly subscriptions, etc.).
- sections: one per product, in the given order; "product" = the exact product name given;
  heading = product name + a short benefit; 2 paragraphs each.
- closing: 2 short paragraphs: how to choose, and a reminder to read the deal terms.
- tags: exactly 5 lowercase Medium topics (e.g. productivity, small business, saas)."""

BANNED = ("i tested", "i've been using", "ive been using", "in my experience", "game-changer",
          "game changer", "today only", "selling out", "last chance", "revolutionary")
PRICE_RE = re.compile(r"[$€£]\s?\d")

THEMES = [
    ("Lifetime Deals for Solopreneurs", "solopreneurs who want fewer monthly subscriptions"),
    ("AppSumo Deals for Freelancers", "freelancers who need simple tools for clients and projects"),
    ("AI Tools on AppSumo Worth a Look", "small teams curious about AI tools without monthly bills"),
    ("Marketing Tools on AppSumo", "small business owners doing their own marketing"),
    ("New on AppSumo This Week", "readers who like to check new software deals"),
]


def tracked(link, sub=SUB_ID):
    """Impact tracking link with a sub id so each place's sales show separately."""
    p = urllib.parse.urlparse(link)
    q = dict(urllib.parse.parse_qsl(p.query))
    q["subId1"] = sub
    return urllib.parse.urlunparse(p._replace(query=urllib.parse.urlencode(q)))


def appsumo_deals():
    """Unique AppSumo products from the Impact Ads feed, newest first."""
    seen, out = set(), []
    for page in range(1, 6):
        rows = impact.get("/Ads", CampaignId=APPSUMO_CAMPAIGN, PageSize=200, Page=page).get("Ads", [])
        if not rows:
            break
        for a in rows:
            land = (a.get("LandingPageUrl") or "").split("?")[0].rstrip("/")
            link = a.get("TrackingLink") or ""
            name = re.sub(r"\s*-\s*logo$", "", str(a.get("Name") or "")).strip()
            if not (land and link and name) or "/products/" not in land or land in seen:
                continue
            seen.add(land)
            out.append({"name": name, "desc": str(a.get("Description") or "")[:500],
                        "page": land, "link": tracked(link),
                        "created": a.get("DealDateCreated") or a.get("DateCreated") or ""})
        if len(rows) < 200:
            break
    out.sort(key=lambda d: str(d["created"]), reverse=True)
    return out


def save_free_deals(deals):
    """Newest 25 deals for the site's free list page (sub id 'freepage')."""
    rows = [{"name": d["name"], "desc": d["desc"], "page": d["page"],
             "link": tracked(d["link"], "freepage")} for d in deals[:25]]
    if rows:
        common.save_json(FREE_DEALS, {"updated": common.today_utc(), "deals": rows})
        common.log("free deals list: {0}".format(len(rows)))


def sample_deals():
    return [{"name": n, "desc": d, "page": "https://appsumo.com/products/" + n.lower(),
             "link": "https://appsumo.8odi.net/c/0/0/7443?subId1=medium", "created": ""}
            for n, d in (("Voxpopme", "Uses video surveys to capture real customer feedback."),
                         ("Tevent", "Lets you host virtual events that encourage networking."),
                         ("ReachOut.AI", "Auto-generates personalized one-to-one sales videos."))]


def checks(art, names):
    blob = " ".join([art["title"], art["subtitle"]] + art["intro"] + art["closing"] +
                    [p for s in art["sections"] for p in s["paragraphs"]]).lower()
    issues = ["banned phrase: " + b for b in BANNED if b in blob]
    if PRICE_RE.search(blob):
        issues.append("mentions a price")
    if "http" in blob:
        issues.append("url in text")
    missing = [n for n in names if n.lower() not in " ".join(s["product"] for s in art["sections"]).lower()]
    if missing:
        issues.append("missing sections: " + ", ".join(missing))
    return issues


def render(art, deals):
    """HTML (for rich paste into Medium) and Markdown (backup)."""
    by_name = {d["name"].lower(): d for d in deals}
    e = html.escape
    h = ["<h1>{0}</h1>".format(e(art["title"])), "<h3>{0}</h3>".format(e(art["subtitle"])),
         "<p><em>{0}</em></p>".format(e(DISCLOSURE))]
    md = ["# " + art["title"], "### " + art["subtitle"], "", "*" + DISCLOSURE + "*", ""]
    for p in art["intro"]:
        h.append("<p>{0}</p>".format(e(p)))
        md += [p, ""]
    for s in art["sections"]:
        d = by_name.get(s["product"].lower()) or next(
            (v for k, v in by_name.items() if k in s["product"].lower()), None)
        h.append("<h2>{0}</h2>".format(e(s["heading"])))
        md += ["## " + s["heading"], ""]
        for p in s["paragraphs"]:
            h.append("<p>{0}</p>".format(e(p)))
            md += [p, ""]
        if d:
            label = "See the {0} deal on AppSumo".format(d["name"])
            h.append('<p><a href="{0}">{1}</a></p>'.format(e(d["link"]), e(label)))
            md += ["[{0}]({1})".format(label, d["link"]), ""]
    h.append("<h2>How to choose</h2>")
    md += ["## How to choose", ""]
    for p in art["closing"]:
        h.append("<p>{0}</p>".format(e(p)))
        md += [p, ""]
    h.append("<p><em>{0}</em></p>".format(e(AI_NOTE)))
    md += ["*" + AI_NOTE + "*"]
    return "\n".join(h), "\n".join(md)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--deals-only", action="store_true", help="only refresh data/free_deals.json")
    args = ap.parse_args()
    cfg = common.settings()
    st = common.load_json(STATE, {"used": {}, "theme_index": 0})

    if args.dry_run:
        deals = sample_deals()
    else:
        if not impact.enabled():
            common.log("Impact keys missing; nothing to do")
            return
        all_deals = appsumo_deals()
        save_free_deals(all_deals)
        if args.deals_only:
            return
        deals = [d for d in all_deals if d["page"] not in st["used"]]
    if len(deals) < 3:
        common.log("not enough new AppSumo deals ({0})".format(len(deals)))
        return

    theme, audience = THEMES[st["theme_index"] % len(THEMES)]
    st["theme_index"] += 1
    pick = deals[:12]
    random.shuffle(pick)
    pick = pick[:5] if len(pick) >= 5 else pick
    names = [d["name"] for d in pick]
    facts = "\n".join("- {0}: {1}".format(d["name"], d["desc"] or "(no description given)") for d in pick)
    user = ("Article theme: {0}\nAudience: {1}\nProducts, in this order:\n{2}".format(theme, audience, facts))

    if args.dry_run:
        art = {"title": "5 AppSumo Lifetime Deals for Solopreneurs", "subtitle": "A short, honest look.",
               "intro": ["Monthly subscriptions add up.", "Here are a few one-time deals to look at."],
               "sections": [{"product": n, "heading": n + ": what it does",
                             "paragraphs": ["What it does.", "What to check before buying."]} for n in names],
               "closing": ["Pick the one that solves a real problem.", "Read the deal terms first."],
               "tags": ["productivity", "small business", "saas", "software", "entrepreneurship"]}
    else:
        art, issues = None, []
        for _ in range(2):
            art = content._call_json(WRITER, user, ARTICLE_SCHEMA, cfg, 3500)
            issues = checks(art, names)
            if not issues:
                break
        if issues:
            common.log("draft rejected by checks: " + "; ".join(issues))
            if dashboard.enabled():
                dashboard.draft_report({"error": "Draft skipped: " + "; ".join(issues)[:250]})
            return

    page_html, page_md = render(art, pick)
    draft = {"id": datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"),
             "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
             "title": art["title"], "subtitle": art["subtitle"],
             "tags": [t.strip().lower() for t in art["tags"]][:5],
             "products": names, "html": page_html, "markdown": page_md}
    if args.dry_run:
        print(page_md)
        return
    for d in pick:
        st["used"][d["page"]] = draft["id"]
    common.save_json(STATE, st)
    # publish on the shop blog (the site rebuilds on push)
    slug = "{0}-{1}".format(datetime.now(timezone.utc).strftime("%Y-%m-%d"), common.slugify(art["title"], 60))
    body = re.sub(r"^<h1>.*?</h1>\s*", "", page_html, count=1)
    blog_url = cfg["site_url"].rstrip("/") + "/blog/" + slug + "/"
    common.save_json(os.path.join(BLOG_DIR, slug + ".json"), {
        "slug": slug, "date": draft["created"][:10], "title": art["title"], "subtitle": art["subtitle"],
        "tags": draft["tags"], "products": names, "html": body})
    draft["blog_url"] = blog_url
    if dashboard.enabled():
        dashboard.draft_report({"draft": draft})
    common.log("draft ready: " + art["title"])


if __name__ == "__main__":
    main()
