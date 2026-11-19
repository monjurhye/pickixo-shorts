"""Free stock footage from Pexels (free license, no attribution required; we credit
Pexels in the description anyway). Needs PEXELS_API_KEY."""

import json
import os
import random
import urllib.parse
import urllib.request

from . import common

API = "https://api.pexels.com/videos/search"


def _get(url, key):
    req = urllib.request.Request(url, headers={"Authorization": key,
                                               "User-Agent": "pickixo-shorts/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def _best_file(video):
    """Portrait mp4 closest to 1080 wide, never above 1440 (keeps downloads small)."""
    files = [f for f in video.get("video_files", [])
             if f.get("file_type") == "video/mp4" and f.get("width") and f.get("height")
             and f["height"] > f["width"] and f["width"] <= 1440]
    if not files:
        return None
    return min(files, key=lambda f: abs(f["width"] - 1080))


def find_clips(queries, count, used_ids, key):
    """Return up to `count` clip dicts {id, url, duration} not used before."""
    picked, seen = [], set(str(u) for u in used_ids)
    for q in queries:
        if len(picked) >= count:
            break
        url = API + "?" + urllib.parse.urlencode(
            {"query": q, "orientation": "portrait", "size": "medium", "per_page": 15})
        try:
            data = _get(url, key)
        except Exception as e:  # network / quota: fall back to plain backgrounds
            common.log("pexels search failed for {0!r}: {1}".format(q, e))
            continue
        vids = data.get("videos", [])
        random.shuffle(vids)
        for v in vids:
            if len(picked) >= count:
                break
            if str(v["id"]) in seen or (v.get("duration") or 0) < 4:
                continue
            f = _best_file(v)
            if f:
                picked.append({"id": v["id"], "url": f["link"], "duration": v["duration"]})
                seen.add(str(v["id"]))
    return picked


def download(clip, dest_dir):
    os.makedirs(dest_dir, exist_ok=True)
    path = os.path.join(dest_dir, "clip_{0}.mp4".format(clip["id"]))
    req = urllib.request.Request(clip["url"], headers={"User-Agent": "pickixo-shorts/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r, open(path, "wb") as f:
        while True:
            chunk = r.read(1 << 16)
            if not chunk:
                break
            f.write(chunk)
    return path
