"""Facebook Page posting through the official Graph API (no browser automation).
Secrets: FB_PAGE_ID, FB_PAGE_TOKEN (long-lived Page access token with pages_manage_posts).
Photo posts use free Pexels photos (PEXELS_API_KEY). Posts are scheduled for US Eastern times."""

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from . import common

GRAPH = "https://graph.facebook.com/v21.0"


class FBError(Exception):
    pass


def enabled():
    return bool(common.secret("FB_PAGE_ID") and common.secret("FB_PAGE_TOKEN"))


def _post(path, fields):
    fields = dict(fields, access_token=common.secret("FB_PAGE_TOKEN"))
    req = urllib.request.Request(GRAPH + path, data=urllib.parse.urlencode(fields).encode(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read().decode()).get("error", {})
            raise FBError("{0}: {1}".format(err.get("code"), err.get("message", "")[:200]))
        except ValueError:
            raise FBError("HTTP {0}".format(e.code))


def check():
    """Page name, to confirm the token works (GET)."""
    url = "{0}/{1}?fields=name,followers_count&access_token={2}".format(
        GRAPH, common.secret("FB_PAGE_ID"), urllib.parse.quote(common.secret("FB_PAGE_TOKEN")))
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise FBError("HTTP {0}: {1}".format(e.code, e.read().decode("utf-8", "ignore")[:200]))


def et_to_utc(date, time_et):
    """'7:30 PM' US Eastern on date -> aware UTC datetime (EST/EDT by US DST rule)."""
    t = datetime.strptime(time_et.strip().upper(), "%I:%M %p")
    d = datetime.strptime(date, "%Y-%m-%d")
    y = d.year
    # DST: second Sunday of March 2:00 to first Sunday of November 2:00
    march = datetime(y, 3, 8 + (6 - datetime(y, 3, 8).weekday()) % 7)
    nov = datetime(y, 11, 1 + (6 - datetime(y, 11, 1).weekday()) % 7)
    local = d.replace(hour=t.hour, minute=t.minute)
    offset = 4 if march <= local < nov else 5
    return (local + timedelta(hours=offset)).replace(tzinfo=timezone.utc)


def pexels_photo(query):
    """A free Pexels photo URL (landscape, large) for the query, or ''."""
    key = common.secret("PEXELS_API_KEY")
    if not key:
        return ""
    url = "https://api.pexels.com/v1/search?" + urllib.parse.urlencode(
        {"query": query, "per_page": 10, "orientation": "landscape"})
    req = urllib.request.Request(url, headers={"Authorization": key, "User-Agent": "pickixo-fb/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            photos = json.loads(r.read().decode()).get("photos", [])
    except Exception:
        return ""
    import random
    random.shuffle(photos)
    return photos[0]["src"]["large2x"] if photos else ""


def schedule_photo(message, image_url, when):
    return _post("/{0}/photos".format(common.secret("FB_PAGE_ID")), {
        "url": image_url, "caption": message, "published": "false",
        "scheduled_publish_time": int(when.timestamp())})


def schedule_text(message, when):
    return _post("/{0}/feed".format(common.secret("FB_PAGE_ID")), {
        "message": message, "published": "false", "scheduled_publish_time": int(when.timestamp())})
