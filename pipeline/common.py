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


def amazon_search_link(query, tracking_id):
    """Affiliate link to an Amazon search results page (allowed by Associates;
    needs no product API and never shows a stale price)."""
    q = urllib.parse.quote_plus(query.strip())
    return "https://www.amazon.com/s?k={0}&tag={1}".format(q, tracking_id)


def secret(name):
    """Read a secret from env. In Actions, all secrets arrive as one JSON blob
    (ALL_SECRETS) so per-channel names don't need to be listed in the workflow."""
    v = os.environ.get(name)
    if v:
        return v
    blob = os.environ.get("ALL_SECRETS")
    if blob:
        try:
            return json.loads(blob).get(name) or ""
        except ValueError:
            return ""
    return ""


def ffmpeg_bin():
    return os.environ.get("FFMPEG") or shutil.which("ffmpeg") or "ffmpeg"


def log(msg):
    print("[{0}] {1}".format(datetime.now(timezone.utc).strftime("%H:%M:%S"), msg), flush=True)
