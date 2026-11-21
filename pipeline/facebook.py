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


def _post(path, fields, token=None):
    fields = dict(fields, access_token=token or common.secret("FB_PAGE_TOKEN"))
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


def schedule_text_on(page_id, token, message, when):
    """Scheduled text post on any Page whose token we have (e.g. Modern Tech Life)."""
    return _post("/{0}/feed".format(page_id), {
        "message": message, "published": "false", "scheduled_publish_time": int(when.timestamp())}, token)


def upload_reel(page_id, token, video_path, description, when=None):
    """Facebook Reels API: start -> upload bytes -> finish (scheduled if `when`)."""
    import os
    def call(fields):
        req = urllib.request.Request("{0}/{1}/video_reels".format(GRAPH, page_id),
                                     data=urllib.parse.urlencode(dict(fields, access_token=token)).encode(),
                                     method="POST")
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            raise FBError("reels {0}: {1}".format(fields.get("upload_phase"), e.read().decode("utf-8", "ignore")[:300]))
    start = call({"upload_phase": "start"})
    vid = start["video_id"]
    size = os.path.getsize(video_path)
    with open(video_path, "rb") as f:
        data = f.read()
    req = urllib.request.Request(start.get("upload_url") or "https://rupload.facebook.com/video-upload/v21.0/" + vid,
                                 data=data, method="POST", headers={
                                     "Authorization": "OAuth " + token, "offset": "0", "file_size": str(size)})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            up = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise FBError("reels upload: " + e.read().decode("utf-8", "ignore")[:300])
    if not up.get("success"):
        raise FBError("reels upload not accepted: " + str(up)[:200])
    fin = {"upload_phase": "finish", "video_id": vid, "description": description[:2200]}
    if when is not None:
        fin.update(video_state="SCHEDULED", scheduled_publish_time=str(int(when.timestamp())))
    else:
        fin["video_state"] = "PUBLISHED"
    res = call(fin)
    if not res.get("success", True):
        raise FBError("reels finish: " + str(res)[:200])
    return vid
