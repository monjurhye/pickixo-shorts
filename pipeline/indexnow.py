"""Tell Bing, Yandex, Seznam, Naver and other IndexNow engines about shop.pickixo.com pages.

  python -m pipeline.indexnow            # submit every URL in the built sitemap
  python -m pipeline.indexnow --new 2    # only pages from the last 2 days (+ home page)

Google does not use IndexNow: it reads /sitemap.xml once the site is added in
Google Search Console. The key file /<indexnow_key>.txt is written by site/build.py."""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

from . import common

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sitemap_urls(days=0):
    sys.path.insert(0, os.path.join(ROOT, "site"))
    import build  # noqa: E402  (site/build.py)
    build.main()  # builds public/ so the list matches what is deployed
    xml = open(os.path.join(build.OUT, "sitemap.xml"), encoding="utf-8").read()
    rows = re.findall(r"<loc>([^<]+)</loc>(?:<lastmod>([^<]+)</lastmod>)?", xml)
    if not days:
        return [u for u, _ in rows]
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    home = common.settings()["site_url"].rstrip("/") + "/"
    return [u for u, mod in rows if u == home or (mod and mod >= cutoff)]


def submit(urls):
    cfg = common.settings()
    key = cfg.get("indexnow_key", "")
    if not key or not urls:
        common.log("indexnow: nothing to send")
        return
    host = cfg["site_url"].split("//", 1)[1].rstrip("/")
    body = json.dumps({"host": host, "key": key,
                       "keyLocation": cfg["site_url"].rstrip("/") + "/" + key + ".txt",
                       "urlList": urls[:10000]}).encode()
    req = urllib.request.Request("https://api.indexnow.org/indexnow", data=body, method="POST",
                                 headers={"Content-Type": "application/json; charset=utf-8",
                                          "User-Agent": "pickixo-pipeline/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            common.log("indexnow: sent {0} urls -> HTTP {1}".format(len(urls), r.status))
    except urllib.error.HTTPError as e:
        # 403 = key file not live yet (first deploy), 422 = url/host mismatch, 429 = too often
        common.log("indexnow: HTTP {0} {1}".format(e.code, e.read().decode(errors="ignore")[:200]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--new", type=int, default=0, help="only pages from the last N days")
    args = ap.parse_args()
    submit(sitemap_urls(args.new))


if __name__ == "__main__":
    main()
