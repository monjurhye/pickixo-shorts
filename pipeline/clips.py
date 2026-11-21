"""Keeps each uploaded Short as a GitHub Release asset (free hosting) so it can be cross-posted
later. Instagram and Threads need a public video URL; the site serves these files at
https://shop.pickixo.com/clip/<tag>/<file>.mp4 (functions/clip/[tag]/[file].js). One release per day
("clips-YYYY-MM-DD"); releases older than KEEP_DAYS are deleted.

Needs GITHUB_TOKEN (contents: write) and GITHUB_REPOSITORY (both set inside GitHub Actions)."""

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from . import common

API = "https://api.github.com"
KEEP_DAYS = 10


def enabled():
    return bool(common.secret("GITHUB_TOKEN") and os.environ.get("GITHUB_REPOSITORY"))


def _req(method, url, data=None, headers=None):
    h = {"Authorization": "Bearer " + common.secret("GITHUB_TOKEN"), "Accept": "application/vnd.github+json",
         "User-Agent": "pickixo-pipeline"}
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            body = r.read().decode() or "{}"
            return r.status, json.loads(body) if body.strip().startswith(("{", "[")) else {}
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read().decode("utf-8", "ignore")[:300]}


def _repo():
    return os.environ["GITHUB_REPOSITORY"]


def _release(tag):
    code, d = _req("GET", "{0}/repos/{1}/releases/tags/{2}".format(API, _repo(), tag))
    if code == 200:
        return d
    code, d = _req("POST", "{0}/repos/{1}/releases".format(API, _repo()), json.dumps({
        "tag_name": tag, "name": tag, "body": "Shorts kept for cross-posting (deleted after {0} days).".format(KEEP_DAYS),
        "prerelease": True}).encode(), {"Content-Type": "application/json"})
    if code not in (200, 201):
        raise RuntimeError("create release {0}: {1}".format(code, d))
    return d


def save(mp4_path, date, key):
    """Upload the file; returns the public URL on our site, or "" if it could not be kept."""
    if not enabled():
        return ""
    tag = "clips-" + date
    name = common.slugify(key, 90) + ".mp4"
    rel = _release(tag)
    for a in rel.get("assets", []):
        if a.get("name") == name:
            break
    else:
        upload = rel["upload_url"].split("{")[0] + "?" + urllib.parse.urlencode({"name": name})
        with open(mp4_path, "rb") as f:
            data = f.read()
        code, d = _req("POST", upload, data, {"Content-Type": "video/mp4"})
        if code not in (200, 201):
            raise RuntimeError("upload asset {0}: {1}".format(code, d))
    return "{0}/clip/{1}/{2}".format(common.settings()["site_url"].rstrip("/"), tag, name)


def github_url(clip_url):
    """Direct GitHub download URL for a clip URL on our site (for downloading the bytes)."""
    tag, name = clip_url.rstrip("/").split("/")[-2:]
    return "https://github.com/{0}/releases/download/{1}/{2}".format(_repo(), tag, name)


def cleanup():
    """Delete clip releases (and their tags) older than KEEP_DAYS."""
    if not enabled():
        return 0
    cutoff = (datetime.now(timezone.utc) - timedelta(days=KEEP_DAYS)).strftime("%Y-%m-%d")
    code, rels = _req("GET", "{0}/repos/{1}/releases?per_page=100".format(API, _repo()))
    n = 0
    for r in rels if code == 200 and isinstance(rels, list) else []:
        tag = r.get("tag_name", "")
        if tag.startswith("clips-") and tag[6:] < cutoff:
            _req("DELETE", "{0}/repos/{1}/releases/{2}".format(API, _repo(), r["id"]))
            _req("DELETE", "{0}/repos/{1}/git/refs/tags/{2}".format(API, _repo(), tag))
            n += 1
    return n
