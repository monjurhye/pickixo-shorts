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
CSS_VERSION = __import__("hashlib").md5(open(os.path.join(ROOT, "site", "static", "style.css"), "rb").read()).hexdigest()[:8]


def page(title, body, desc="", canonical="", head_extra="", foot=""):
    cfg = common.settings()
    return """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="p:domain_verify" content="87ee4dd376b44ff90c6f4add82b02f56"/>
{verify}<title>{title}</title>
<meta name="description" content="{desc}">
{canon}
<link rel="stylesheet" href="/style.css?v={cssv}">
{head_extra}
</head><body>
<header class="top"><a class="brand" href="/">{brand}</a>
<nav><a href="/">Latest</a><a href="/disclosure/">Disclosure</a><a href="/privacy/">Privacy</a></nav></header>
<main>{body}</main>
<footer><p>{disc}</p><p>&copy; {brand} · {foot}</p></footer>
</body></html>""".format(title=e(title), desc=e(desc), brand=e(cfg.get("brand", "Pickixo Picks")),
                         canon='<link rel="canonical" href="{0}">'.format(e(canonical)) if canonical else "",
                         body=body, head_extra=head_extra, cssv=CSS_VERSION, verify=verify_tags(cfg),
                         foot=e(foot or "Product links go to Amazon.com."),
                         disc=e(cfg.get("disclosure", "")))


def verify_tags(cfg):
    """Search Console / Bing Webmaster verification codes from config/settings.json."""
    out = ""
    for key, name in (("google_site_verification", "google-site-verification"),
                      ("bing_site_verification", "msvalidate.01")):
        if cfg.get(key):
            out += '<meta name="{0}" content="{1}">\n'.format(name, e(cfg[key]))
    return out


def site_url(path=""):
    return common.settings()["site_url"].rstrip("/") + path


def sitemap_entries(videos):
    """(path, lastmod) for every page search engines should index. Locker "full" pages
    and /admin are left out on purpose (noindex / private)."""
    newest = videos[0]["date"] if videos else common.today_utc()
    out = [("/", newest), ("/disclosure/", ""), ("/privacy/", ""), ("/terms/", "")]
    for sub in ("free/lifetime-deals", "free/ios-without-mac", "free/ai-prompts"):
        if os.path.exists(os.path.join(OUT, sub, "index.html")):
            out.append(("/" + sub + "/", ""))
    out += [("/v/{0}/".format(v["key"]), v["date"]) for v in videos]
    return out


def sitemap_xml(entries):
    rows = []
    for path, mod in entries:
        rows.append("<url><loc>{0}</loc>{1}</url>".format(
            e(site_url(path)), "<lastmod>{0}</lastmod>".format(e(mod)) if mod else ""))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "\n".join(rows) + "\n</urlset>\n")


def robots_txt():
    return ("User-agent: *\nAllow: /\nDisallow: /admin\nDisallow: /api/\nDisallow: /auth/\n"
            "Disallow: /free/ios-without-mac/full/\nDisallow: /free/ai-prompts/full/\n\n"
            "Sitemap: {0}\n").format(site_url("/sitemap.xml"))


def item_cards(items):
    out = []
    for i, it in enumerate(items, 1):
        out.append("""<li class="card"><span class="num">{n}</span>
<div class="txt"><h3>{name}</h3><p>{benefit}</p></div>
<a class="btn" href="{link}" target="_blank" rel="sponsored nofollow noopener">{label}</a></li>""".format(
            n=i, name=e(it["name"]), benefit=e(it["benefit"]), link=e(it["link"]),
            label="View on Amazon →" if it.get("asin") else "Find on Amazon →"))
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
    og = thumb(v)[0]
    head = ('<meta property="og:title" content="{0}"><meta property="og:image" content="{1}">'
            '<meta name="twitter:card" content="summary_large_image">').format(e(v["title"]), e(og)) if og else ""
    return page(v["title"] + " · Pickixo Picks", body, v.get("description", ""), v.get("page_url", ""),
                head_extra=head)


def thumb(v):
    """Card image: the Pexels still saved with the video (free license), else the
    thumbnail of our own YouTube Short. Never Amazon product images."""
    if v.get("image"):
        return v["image"], ""
    if v.get("youtube_id"):
        return "https://i.ytimg.com/vi/{0}/hqdefault.jpg".format(e(v["youtube_id"])), "yt"
    return "", ""


def img_tag(v):
    """YouTube's hqdefault for a Short is 4:3 with black side bars, so it is zoomed to the
    centre (class yt); Pexels stills are shown as they are."""
    src, kind = thumb(v)
    if not src:
        return ""
    return '<span class="thumbw"><img class="thumb {0}" src="{1}" alt="{2}" loading="lazy"></span>'.format(
        kind, e(src), e(v["title"]))


def index_page(videos):
    groups = OrderedDict()
    for v in videos:
        groups.setdefault(v["niche"], []).append(v)
    sections = []
    for niche, vs in groups.items():
        links = "".join('<li><a href="/v/{0}/">{1}</a><span>{2}</span></li>'.format(
            e(v["key"]), e(v["title"]), e(v["date"])) for v in vs[:8])
        cover = '<a href="/v/{0}/">{1}</a>'.format(e(vs[0]["key"]), img_tag(vs[0])) if thumb(vs[0])[0] else ""
        sections.append('<section class="niche">{2}<h2>{0}</h2><ul>{1}</ul></section>'.format(e(niche), links, cover))
    if not sections:
        sections = ['<p class="lead">New picks are on the way. Check back tomorrow.</p>']
    body = """<section class="hero"><h1>Useful finds, fewer regrets.</h1>
<p class="lead">Short lists of handy things for home, kitchen, pets and more, picked to make everyday life a bit easier.</p></section>
<div class="grid">{0}</div>""".format("".join(sections))
    return page("Pickixo Picks · Useful finds for everyday life", body,
                "Short lists of handy Amazon finds for home, kitchen, pets and more.", site_url("/"))


def disclosure_page():
    cfg = common.settings()
    body = """<h1>Affiliate disclosure</h1>
<p class="lead">{0}</p>
<p>Pickixo Picks is a participant in the Amazon Services LLC Associates Program, an affiliate advertising
program designed to provide a means for sites to earn advertising fees by advertising and linking to Amazon.com.
When you buy through our links we may earn a commission, at no extra cost to you.</p>
<p>Prices and availability change often, so we don't list prices here. You'll see the current price on Amazon.</p>""".format(
        e(cfg.get("disclosure", "")))
    return page("Disclosure · Pickixo Picks", body, "Affiliate disclosure for Pickixo Picks.",
                site_url("/disclosure/"))


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


def free_deals_page():
    """Open list of the newest AppSumo deals (no locker). Sub id 'freepage'."""
    data = common.load_json(os.path.join(common.DATA_DIR, "free_deals.json"), {"deals": []})
    deals = data.get("deals", [])
    cards = "".join("""<li class="card"><span class="num">{n}</span>
<div class="txt"><h3>{name}</h3><p>{desc}</p></div>
<a class="btn" href="{link}" target="_blank" rel="sponsored nofollow noopener">See the deal on AppSumo →</a></li>""".format(
        n=i, name=e(d["name"]), desc=e(d["desc"] or "Software deal on AppSumo."), link=e(d["link"]))
        for i, d in enumerate(deals, 1))
    body = """<section class="hero"><h1>{n} Lifetime Software Deals That Replace Monthly Subscriptions</h1>
<p>A free, regularly updated list of one-time-payment software deals on AppSumo for solopreneurs,
freelancers and small teams. Updated {up}.</p></section>
<ol class="cards">{cards}</ol>
<p class="note">Before buying any lifetime deal, read the plan limits and refund window on the deal page.
Lifetime deals depend on the company staying in business.</p>""".format(
        n=len(deals), up=e(data.get("updated", "")), cards=cards)
    return page("Lifetime software deals list (AppSumo)", body,
                "Free updated list of AppSumo lifetime software deals that replace monthly subscriptions.",
                foot="Links on this page are affiliate links (AppSumo via Impact); we may earn a commission.")


def prompt_pack_page(full=False):
    """AI image prompt pack. Teaser (/free/ai-prompts/) shows 5 prompts and links to /full/.
    /full/ (noindex) loads the AdBlueMedia JS locker and opens it on page load, so the full
    list stays covered until the visitor completes one sponsor offer."""
    data = common.load_json(os.path.join(common.DATA_DIR, "prompt_pack.json"), {"prompts": []})
    prompts = data.get("prompts", [])
    def card(i, p):
        return """<li class="card"><span class="num">{n}</span><div class="txt"><h3>{t}</h3>
<p class="muted">{tool} · {aspect}</p><p>{prompt}</p></div></li>""".format(
            n=i, t=e(p["theme"]), tool=e(p.get("tool", "")), aspect=e(p.get("aspect", "")), prompt=e(p["prompt"]))
    shown = prompts if full else prompts[:5]
    cards = "".join(card(i, p) for i, p in enumerate(shown, 1))
    if full:
        unlock = '<div class="unlock"><b>Unlocked, thanks!</b> Here is the full pack. Bookmark this page; it updates every day.</div>'
    else:
        btn = '<a class="btn" href="/free/ai-prompts/full/" rel="nofollow">Unlock all {0} prompts</a>'.format(len(prompts))
        unlock = """<div class="unlock"><h2>Get all {n} prompts</h2>
<p>The full pack is free. To unlock it, complete <b>one short offer from our sponsor</b>
(for example a quick survey or a free app). You don't have to buy anything.</p><p>{btn}</p></div>""".format(
            n=len(prompts), btn=btn)
    body = """<section class="hero"><h1>{n} AI Image Prompts for Stock Photos (Updated Daily)</h1>
<p>Ready-to-use prompts for Adobe Firefly, Ideogram and FLUX: seasonal and evergreen themes that buyers search for,
written to avoid common AI mistakes (no text, no logos, no hand close-ups). Updated {up}.</p></section>
<ol class="cards">{cards}</ol>{unlock}
<p class="note">Tips: make 4-8 images per prompt, keep only clean ones, check at 100% zoom, and label AI images
when you upload them to stock sites.</p>""".format(n=len(prompts), up=e(data.get("updated", "")), cards=cards, unlock=unlock)
    head = ('<meta name="robots" content="noindex">' + LOCKER_HEAD +
            '<script>window.addEventListener("load",function(){if(typeof _ET==="function"){_ET();}});</script>'
            ) if full else ""
    return page("AI image prompt pack for stock photos", body,
                "Free daily-updated pack of AI image prompts for stock photos: seasonal and evergreen themes.",
                head_extra=head,
                foot="The unlock offers come from our sponsor AdBlueMedia; we may earn when you complete one.")


def md_inline(t):
    t = e(t)
    t = __import__("re").sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = __import__("re").sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
    t = __import__("re").sub(r"(?<![*\w])\*([^*\n]+)\*(?!\w)", r"<i>\1</i>", t)
    return t


def md_to_html(md):
    """Small Markdown subset: #/##/### headings, paragraphs, - and 1. lists, tables,
    ``` code, > quotes, --- rules, **bold**, *italic*, `code`."""
    import re
    out, lines, i = [], md.splitlines(), 0
    def slug(t):
        return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")[:60]
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("```"):
            buf = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                buf.append(lines[i]); i += 1
            out.append("<pre><code>" + e("\n".join(buf)) + "</code></pre>"); i += 1; continue
        if ln.strip() == "---":
            out.append("<hr>"); i += 1; continue
        m = re.match(r"(#{1,3}) (.*)", ln)
        if m:
            lv = len(m.group(1))
            out.append('<h{0} id="{1}">{2}</h{0}>'.format(lv, slug(m.group(2)), md_inline(m.group(2)))); i += 1; continue
        if ln.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")]); i += 1
            head, body = rows[0], [r for r in rows[1:] if not all(re.fullmatch(r":?-+:?", c or "-") for c in r)]
            out.append('<div class="tw"><table><thead><tr>' + "".join("<th>%s</th>" % md_inline(c) for c in head) +
                       "</tr></thead><tbody>" + "".join("<tr>" + "".join("<td>%s</td>" % md_inline(c) for c in r) + "</tr>"
                                                        for r in body) + "</tbody></table></div>")
            continue
        if ln.startswith("> "):
            buf = []
            while i < len(lines) and lines[i].startswith(">"):
                buf.append(lines[i][1:].strip()); i += 1
            out.append("<blockquote><p>" + md_inline(" ".join(buf)) + "</p></blockquote>"); continue
        if re.match(r"\s*(- |\d+\. )", ln):
            ordered = bool(re.match(r"\s*\d+\. ", ln))
            items = []
            while i < len(lines) and (re.match(r"\s*(- |\d+\. )", lines[i]) or (lines[i].startswith("   ") and lines[i].strip())):
                if re.match(r"(- |\d+\. )", lines[i]):
                    items.append(re.sub(r"^(- |\d+\. )", "", lines[i]))
                else:
                    items[-1] += "<br>" + lines[i].strip().lstrip("- ") if items else ""
                i += 1
            tag = "ol" if ordered else "ul"
            out.append("<%s>" % tag + "".join("<li>%s</li>" % (md_inline(x).replace("&lt;br&gt;", "<br>")) for x in items) + "</%s>" % tag)
            continue
        if not ln.strip():
            i += 1; continue
        buf = []
        while i < len(lines) and lines[i].strip() and not re.match(r"(#{1,3} |```|\||> |- |\d+\. |---$)", lines[i]):
            buf.append(lines[i].strip()); i += 1
        out.append("<p>" + md_inline(" ".join(buf)) + "</p>")
    return "\n".join(out)


EBOOK = os.path.join(ROOT, "site", "ebooks", "ios-without-mac.md")


def ebook_page(full=False):
    """Free English ebook. Teaser = intro + contents + Chapter 1; /full/ = whole book,
    covered by the AdBlueMedia locker until one sponsor offer is completed."""
    md = open(EBOOK, encoding="utf-8").read()
    if full:
        content = md
        unlock = ('<div class="unlock"><b>Unlocked, thanks!</b> Bookmark this page. '
                  '<button class="btn" onclick="window.print()">Save as PDF</button></div>')
    else:
        end = md.index("## Chapter 2")
        content = md[:end]
        unlock = """<div class="unlock"><h2>Read the whole book free (16 chapters + checklist)</h2>
<p>To unlock the full book, complete <b>one short offer from our sponsor</b> (for example a quick survey or a free app).
You don't have to buy anything. After unlocking you can read it here or save it as a PDF.</p>
<p><a class="btn" href="/free/ios-without-mac/full/" rel="nofollow">Unlock the full book</a></p></div>"""
    body = '<article class="ebook">' + md_to_html(content) + "</article>" + unlock
    head = ('<meta name="robots" content="noindex">' + LOCKER_HEAD +
            '<script>window.addEventListener("load",function(){if(typeof _ET==="function"){_ET();}});</script>'
            ) if full else ""
    return page("Publish an iOS App Without a Mac (free ebook)", body,
                "Free ebook: publish an iPhone app on the App Store from Windows with no Mac or iPhone, using Codemagic, TestFlight and AdMob.",
                head_extra=head,
                foot="The unlock offers come from our sponsor AdBlueMedia; we may earn when you complete one.")


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
    if os.path.exists(EBOOK):
        write(os.path.join(OUT, "free", "ios-without-mac", "index.html"), ebook_page())
        write(os.path.join(OUT, "free", "ios-without-mac", "full", "index.html"), ebook_page(full=True))
    if os.path.exists(os.path.join(common.DATA_DIR, "prompt_pack.json")):
        write(os.path.join(OUT, "free", "ai-prompts", "index.html"), prompt_pack_page())
        write(os.path.join(OUT, "free", "ai-prompts", "full", "index.html"), prompt_pack_page(full=True))
    with open(os.path.join(OUT, "channels.json"), "w", encoding="utf-8") as f:
        json.dump({"channels": [{"id": c["id"], "niche": c["niche"]} for c in common.channels()]}, f)
    fb = common.load_json(os.path.join(common.CONFIG_DIR, "facebook.json"), None)
    if fb:   # plan only, no secrets; read by /admin
        with open(os.path.join(OUT, "facebook-plan.json"), "w", encoding="utf-8") as f:
            json.dump(fb, f)
    for name in os.listdir(STATIC):
        shutil.copy(os.path.join(STATIC, name), os.path.join(OUT, name))
    # search engines: sitemap, robots, IndexNow key file (the key is public by design)
    entries = sitemap_entries(videos)
    write(os.path.join(OUT, "sitemap.xml"), sitemap_xml(entries))
    write(os.path.join(OUT, "robots.txt"), robots_txt())
    key = common.settings().get("indexnow_key", "")
    if key:
        write(os.path.join(OUT, key + ".txt"), key)
    print("sitemap: {0} urls".format(len(entries)))
    print("built {0} video pages into {1}".format(len(videos), OUT))


if __name__ == "__main__":
    main()
