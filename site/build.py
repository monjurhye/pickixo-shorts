"""Static site generator for shop.pickixo.com.
Cloudflare Pages build command:  python3 site/build.py   (output directory: public)

Reads data/videos/*.json written by the daily pipeline and makes:
  /                 latest picks, grouped by niche
  /v/<key>/         one page per video: the items with Amazon links (+ the Short)
  /disclosure/      affiliate disclosure
No prices and no Amazon images are shown (not allowed without the product API)."""

import glob
import html
import json
import os
import shutil
import sys
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from pipeline import common  # noqa: E402

OUT = os.path.join(ROOT, "public")
STATIC = os.path.join(ROOT, "site", "static")
e = html.escape


def page(title, body, desc="", canonical="", head_extra="", foot=""):
    cfg = common.settings()
    return """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="p:domain_verify" content="87ee4dd376b44ff90c6f4add82b02f56"/>
<title>{title}</title>
<meta name="description" content="{desc}">
{canon}
<link rel="stylesheet" href="/style.css">
{head_extra}
</head><body>
<header class="top"><a class="brand" href="/">{brand}</a>
<nav><a href="/">Latest</a><a href="/disclosure/">Disclosure</a><a href="/privacy/">Privacy</a></nav></header>
<main>{body}</main>
<footer><p>{disc}</p><p>&copy; {brand} · {foot}</p></footer>
</body></html>""".format(title=e(title), desc=e(desc), brand=e(cfg.get("brand", "Pickixo Picks")),
                         canon='<link rel="canonical" href="{0}">'.format(e(canonical)) if canonical else "",
                         body=body, head_extra=head_extra,
                         foot=e(foot or "Product links go to Amazon.com search results."),
                         disc=e(cfg.get("disclosure", "")))


def item_cards(items):
    out = []
    for i, it in enumerate(items, 1):
        out.append("""<li class="card"><span class="num">{n}</span>
<div class="txt"><h3>{name}</h3><p>{benefit}</p></div>
<a class="btn" href="{link}" target="_blank" rel="sponsored nofollow noopener">Find on Amazon →</a></li>""".format(
            n=i, name=e(it["name"]), benefit=e(it["benefit"]), link=e(it["link"])))
    return '<ol class="cards">' + "".join(out) + "</ol>"


def video_page(v):
    embed = ""
    if v.get("youtube_id"):
        embed = ('<div class="short"><iframe src="https://www.youtube-nocookie.com/embed/{0}" '
                 'title="{1}" loading="lazy" allowfullscreen></iframe></div>').format(
                     e(v["youtube_id"]), e(v["title"]))
    body = """<p class="kicker">{niche}</p><h1>{title}</h1><p class="lead">{desc}</p>
{embed}{cards}<p class="note">Tap an item to see current options and prices on Amazon.</p>""".format(
        niche=e(v["niche"]), title=e(v["title"]), desc=e(v.get("description", "")),
        embed=embed, cards=item_cards(v["items"]))
    return page(v["title"] + " · Pickixo Picks", body, v.get("description", ""), v.get("page_url", ""))


def index_page(videos):
    groups = OrderedDict()
    for v in videos:
        groups.setdefault(v["niche"], []).append(v)
    sections = []
    for niche, vs in groups.items():
        links = "".join('<li><a href="/v/{0}/">{1}</a><span>{2}</span></li>'.format(
            e(v["key"]), e(v["title"]), e(v["date"])) for v in vs[:8])
        sections.append('<section class="niche"><h2>{0}</h2><ul>{1}</ul></section>'.format(e(niche), links))
    if not sections:
        sections = ['<p class="lead">New picks are on the way. Check back tomorrow.</p>']
    body = """<section class="hero"><h1>Useful finds, fewer regrets.</h1>
<p class="lead">Short lists of handy things for home, kitchen, pets and more, picked to make everyday life a bit easier.</p></section>
<div class="grid">{0}</div>""".format("".join(sections))
    return page("Pickixo Picks · Useful finds for everyday life", body,
                "Short lists of handy Amazon finds for home, kitchen, pets and more.")


def disclosure_page():
    cfg = common.settings()
    body = """<h1>Affiliate disclosure</h1>
<p class="lead">{0}</p>
<p>Pickixo Picks is a participant in the Amazon Services LLC Associates Program, an affiliate advertising
program designed to provide a means for sites to earn advertising fees by advertising and linking to Amazon.com.
When you buy through our links we may earn a commission, at no extra cost to you.</p>
<p>Prices and availability change often, so we don't list prices here. You'll see the current price on Amazon.</p>""".format(
        e(cfg.get("disclosure", "")))
    return page("Disclosure · Pickixo Picks", body)


def privacy_page():
    body = """<h1>Privacy policy</h1>
<p class="lead">Pickixo Picks is a simple website of product recommendations. We keep this short and honest.</p>
<h2>What we collect</h2>
<p>This site has no accounts, forms, or tracking cookies of its own. Our hosting provider (Cloudflare) may
keep standard server logs (such as IP address and browser type) for security and reliability.</p>
<h2>Amazon links</h2>
<p>When you click a product link you go to Amazon.com, which may set its own cookies to track the referral
for the Amazon Associates program. Amazon's privacy notice applies there.</p>
<h2>Embedded videos</h2>
<p>Video pages may embed our YouTube Shorts using YouTube's privacy-enhanced mode (youtube-nocookie.com).</p>
<h2>Our YouTube upload tool</h2>
<p>We use Google's YouTube Data API only to upload videos to our own YouTube channels. We don't access,
store, or share anyone else's Google or YouTube data. Our use of information received from Google APIs
adheres to the Google API Services User Data Policy, including the Limited Use requirements.</p>
<h2>Contact</h2>
<p>Questions? Open an issue at <a href="https://github.com/monjurhye/pickixo-shorts/issues">github.com/monjurhye/pickixo-shorts</a>.</p>"""
    return page("Privacy · Pickixo Picks", body)


def terms_page():
    body = """<h1>Terms of use</h1>
<p class="lead">Pickixo Picks shares product ideas for information only.</p>
<p>We don't sell products. Purchases happen on Amazon.com under Amazon's terms. Prices and availability
change, so check Amazon before you buy. We may earn a commission from qualifying purchases at no extra
cost to you. Content is provided "as is" without warranties.</p>"""
    return page("Terms · Pickixo Picks", body)


# AdBlueMedia content locker (public snippet from the AdBlueMedia dashboard; no secret in it).
LOCKER_HEAD = """<script type="text/javascript">var gJXKc_sbq_gLMDqc={"it":4383972,"key":"ae49a"};</script>
<script src="https://d1chbu4sfo2xhu.cloudfront.net/71fd049.js"></script>"""


def free_deals_page(full=False):
    """Teaser page (3 deals + unlock button) or, with full=True, the unlocked full list.
    Unlock goes through the AdBlueMedia URL locker (settings: adbluemedia_locker_url), whose
    destination should be /free/lifetime-deals/full/."""
    data = common.load_json(os.path.join(common.DATA_DIR, "free_deals.json"), {"deals": []})
    locker_url = common.settings().get("adbluemedia_locker_url", "")
    deals = data.get("deals", [])
    def card(i, d):
        return """<li class="card"><span class="num">{n}</span>
<div class="txt"><h3>{name}</h3><p>{desc}</p></div>
<a class="btn" href="{link}" target="_blank" rel="sponsored nofollow noopener">See the deal on AppSumo →</a></li>""".format(
            n=i, name=e(d["name"]), desc=e(d["desc"] or "Software deal on AppSumo."), link=e(d["link"]))
    teaser = "".join(card(i, d) for i, d in enumerate(deals[:3], 1))
    rest = "".join(card(i, d) for i, d in enumerate(deals[3:], 4)) if full else ""
    if full:
        button = '<p><b>Unlocked, thanks!</b> Here is the full list.</p>'
    elif locker_url:
        button = '<p><a class="btn" href="{0}" rel="nofollow">Unlock the full list</a></p>'.format(e(locker_url))
    else:
        button = '<p><button class="btn" onclick="if(typeof _ET===\'function\'){{_ET();}}">Unlock the full list</button></p>'
    button = button.replace("{{", "{").replace("}}", "}")
    body = """<section class="hero"><h1>{n} Lifetime Software Deals That Replace Monthly Subscriptions</h1>
<p>A free, regularly updated list of one-time-payment software deals on AppSumo for solopreneurs,
freelancers and small teams. Updated {up}.</p></section>
<ol class="cards">{teaser}</ol>
<div class="unlock"><h2>See the full list ({more} more deals)</h2>
<p>The full list is free. To unlock it, complete <b>one short offer from our sponsor</b>
(for example a quick survey or a free app). This keeps the list free. You don't have to buy anything.</p>
{button}</div>
<ol class="cards" start="4">{rest}</ol>
<p class="note">Before buying any lifetime deal, read the plan limits and refund window on the deal page.
Lifetime deals depend on the company staying in business.</p>""".format(
        n=len(deals), up=e(data.get("updated", "")), teaser=teaser, more=max(0, len(deals) - 3), rest=rest,
        button=button)
    foot = ("Some links on this page are affiliate links (AppSumo via Impact); we may earn a commission. "
            "The unlock offers come from our sponsor AdBlueMedia; we may earn when you complete one.")
    head = LOCKER_HEAD if not (full or locker_url) else ""
    if full:
        head += '<meta name="robots" content="noindex">'
    return page("Free list: lifetime software deals (AppSumo)", body,
                "Free updated list of AppSumo lifetime software deals that replace monthly subscriptions.",
                head_extra=head, foot=foot)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    videos = []
    for p in glob.glob(os.path.join(common.VIDEOS_DATA_DIR, "*.json")):
        with open(p, encoding="utf-8") as f:
            videos.append(json.load(f))
    videos.sort(key=lambda v: (v["date"], v["key"]), reverse=True)
    for v in videos:
        write(os.path.join(OUT, "v", v["key"], "index.html"), video_page(v))
    write(os.path.join(OUT, "index.html"), index_page(videos))
    write(os.path.join(OUT, "disclosure", "index.html"), disclosure_page())
    write(os.path.join(OUT, "privacy", "index.html"), privacy_page())
    write(os.path.join(OUT, "terms", "index.html"), terms_page())
    if os.path.exists(os.path.join(common.DATA_DIR, "free_deals.json")):
        write(os.path.join(OUT, "free", "lifetime-deals", "index.html"), free_deals_page())
        write(os.path.join(OUT, "free", "lifetime-deals", "full", "index.html"), free_deals_page(full=True))
    with open(os.path.join(OUT, "channels.json"), "w", encoding="utf-8") as f:
        json.dump({"channels": [{"id": c["id"], "niche": c["niche"]} for c in common.channels()]}, f)
    for name in os.listdir(STATIC):
        shutil.copy(os.path.join(STATIC, name), os.path.join(OUT, name))
    print("built {0} video pages into {1}".format(len(videos), OUT))


if __name__ == "__main__":
    main()
