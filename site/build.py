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


def page(title, body, desc="", canonical=""):
    cfg = common.settings()
    return """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
{canon}
<link rel="stylesheet" href="/style.css">
</head><body>
<header class="top"><a class="brand" href="/">{brand}</a>
<nav><a href="/">Latest</a><a href="/disclosure/">Disclosure</a></nav></header>
<main>{body}</main>
<footer><p>{disc}</p><p>&copy; {brand} · Product links go to Amazon.com search results.</p></footer>
</body></html>""".format(title=e(title), desc=e(desc), brand=e(cfg.get("brand", "Pickixo Picks")),
                         canon='<link rel="canonical" href="{0}">'.format(e(canonical)) if canonical else "",
                         body=body, disc=e(cfg.get("disclosure", "")))


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
    for name in os.listdir(STATIC):
        shutil.copy(os.path.join(STATIC, name), os.path.join(OUT, name))
    print("built {0} video pages into {1}".format(len(videos), OUT))


if __name__ == "__main__":
    main()
