"""Shared paths, config loading, and small helpers. No secrets live in this repo:
every key is read from environment variables (GitHub Actions secrets)."""

import json
import os
import re
import shutil
import urllib.parse
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(ROOT, "config")
DATA_DIR = os.path.join(ROOT, "data")
VIDEOS_DATA_DIR = os.path.join(DATA_DIR, "videos")
STATE_PATH = os.path.join(DATA_DIR, "state.json")
MUSIC_DIR = os.path.join(ROOT, "assets", "music")
WORK_DIR = os.path.join(ROOT, "work")  # scratch output, git-ignored


def load_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def settings():
    return load_json(os.path.join(CONFIG_DIR, "settings.json"), {})


def channels():
    return load_json(os.path.join(CONFIG_DIR, "channels.json"), {"channels": []})["channels"]


def today_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def slugify(text, max_len=48):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:max_len].rstrip("-") or "video"


ASIN_RE = re.compile(r"^[A-Z0-9]{10}$")


def parse_asin(text):
    """ASIN from a bare ASIN or a full Amazon link (/dp/<ASIN>, /gp/product/<ASIN>).
    Short amzn.to links can't be read offline: use SiteStripe's "Full link"."""
    t = (text or "").strip()
    if ASIN_RE.match(t.upper()) and len(t) == 10:
        return t.upper()
    m = re.search(r"/(?:dp|gp/product|gp/aw/d)/([A-Za-z0-9]{10})(?:[/?#]|$)", t)
    return m.group(1).upper() if m else ""


def amazon_product_link(asin, tracking_id):
    """Affiliate link to one specific product page."""
    return "https://www.amazon.com/dp/{0}?tag={1}".format(asin, tracking_id)


def products(channel_id):
    """Real products for a channel. Owner-picked ones (config/products.json) come first,
    then the ones the product finder agent verified (data/products.json, younger than
    product_finder_max_age_days). Never guessed. Returns [{"asin","name"}]."""
    manual = load_json(os.path.join(CONFIG_DIR, "products.json"), {"products": []}).get("products", [])
    max_age = int(settings().get("product_finder_max_age_days", 30))
    cutoff = (datetime.now(timezone.utc) - __import__("datetime").timedelta(days=max_age)).strftime("%Y-%m-%d")
    auto = [p for p in (load_json(os.path.join(DATA_DIR, "products.json"), None) or {}).get("products", [])
            if p.get("found", "") >= cutoff]
    out, seen = [], set()
    for p in manual + auto:
        asin = parse_asin(p.get("asin") or p.get("link") or "")
        if not asin or asin in seen or not p.get("name"):
            continue
        if channel_id in (p.get("channels") or []):
            seen.add(asin)
            out.append({"asin": asin, "name": p["name"].strip()})
    return out


def amazon_search_link(query, tracking_id):
    """Affiliate link to an Amazon search results page (allowed by Associates;
    needs no product API and never shows a stale price)."""
    q = urllib.parse.quote_plus(query.strip())
    return "https://www.amazon.com/s?k={0}&tag={1}".format(q, tracking_id)


def secret(name):
    """Read a secret from env. The workflow passes each secret by name
    (daily.yml lists YT_REFRESH_CH01..CH20)."""
    return os.environ.get(name) or ""


def ffmpeg_bin():
    return os.environ.get("FFMPEG") or shutil.which("ffmpeg") or "ffmpeg"


def log(msg):
    print("[{0}] {1}".format(datetime.now(timezone.utc).strftime("%H:%M:%S"), msg), flush=True)
