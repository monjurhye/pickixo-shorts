"""YouTube upload with one OAuth client (YT_CLIENT_ID / YT_CLIENT_SECRET) and one
refresh token per channel (secret YT_REFRESH_<CHANNEL_ID>, e.g. YT_REFRESH_CH01).
Tokens are created once with tools/youtube_authorize.py."""

import json
import os
import urllib.error
import urllib.parse
import urllib.request

from . import common

TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = ("https://www.googleapis.com/upload/youtube/v3/videos"
              "?uploadType=resumable&part=snippet,status")


class UploadError(Exception):
    def __init__(self, msg, permanent=False):
        Exception.__init__(self, msg)
        self.permanent = permanent  # True -> count toward auto-disable


def refresh_secret_name(channel_id):
    return "YT_REFRESH_" + channel_id.upper()


def has_credentials(channel_id):
    return bool(common.secret("YT_CLIENT_ID") and common.secret("YT_CLIENT_SECRET")
                and common.secret(refresh_secret_name(channel_id)))


def _access_token(channel_id):
    body = urllib.parse.urlencode({
        "client_id": common.secret("YT_CLIENT_ID"),
        "client_secret": common.secret("YT_CLIENT_SECRET"),
        "refresh_token": common.secret(refresh_secret_name(channel_id)),
        "grant_type": "refresh_token",
    }).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(TOKEN_URL, data=body), timeout=30) as r:
            return json.loads(r.read().decode())["access_token"]
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")[:300]
        # invalid_grant = token revoked/expired -> needs re-authorization
        raise UploadError("token refresh failed ({0}): {1}".format(e.code, detail),
                          permanent="invalid_grant" in detail)


def upload(channel_id, video_path, title, description, tags, cfg):
    token = _access_token(channel_id)
    meta = {
        "snippet": {
            "title": title[:100],
            "description": description[:4900],
            "tags": [t.lstrip("#") for t in tags][:15],
            "categoryId": str(cfg.get("youtube_category_id", "26")),
        },
        "status": {
            "privacyStatus": cfg.get("youtube_privacy", "public"),
            "selfDeclaredMadeForKids": False,
        },
    }
    size = os.path.getsize(video_path)
    init = urllib.request.Request(UPLOAD_URL, data=json.dumps(meta).encode(), method="POST",
                                  headers={"Authorization": "Bearer " + token,
                                           "Content-Type": "application/json; charset=UTF-8",
                                           "X-Upload-Content-Type": "video/mp4",
                                           "X-Upload-Content-Length": str(size)})
    try:
        with urllib.request.urlopen(init, timeout=60) as r:
            session_url = r.headers["Location"]
        with open(video_path, "rb") as f:
            put = urllib.request.Request(session_url, data=f.read(), method="PUT",
                                         headers={"Content-Type": "video/mp4",
                                                  "Content-Length": str(size)})
        with urllib.request.urlopen(put, timeout=600) as r:
            return json.loads(r.read().decode())["id"]
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")[:400]
        # 403 covers quota, upload limits, suspended/unverified channels;
        # quotaExceeded is temporary, the rest point at the channel itself
        permanent = e.code in (401, 403) and "quotaExceeded" not in detail
        raise UploadError("upload failed ({0}): {1}".format(e.code, detail), permanent=permanent)
