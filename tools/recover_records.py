"""Rebuild lost website records (data/videos/<key>.json) for Shorts that are on YouTube
but whose record never reached the repo (e.g. the 2026-11-22 17:00 run whose push failed).

For each channel it reads the channel's own uploads (dashboard token, youtube.readonly),
keeps videos whose description points at https://shop.pickixo.com/v/<date>-..., and writes
a record from the title + description ("• name: link" lines) when the file is missing.

    PIPELINE_KEY=... python -m tools.recover_records 2026-11-22
"""

import json
import os
import re
import sys
import urllib.parse
import urllib.request

from pipeline import common, dashboard, state

API = "https://www.googleapis.com/youtube/v3/"


def get(path, token):
    req = urllib.request.Request(API + path, headers={"Authorization": "Bearer " + token})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def seconds(iso):
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return 0
    h, mi, s = (int(x or 0) for x in m.groups())
    return h * 3600 + mi * 60 + s


def parse_items(desc):
    items = []
    for line in desc.splitlines():
        m = re.match(r"^•\s*(.+?):\s*(https?://\S+)\s*$", line.strip())
        if not m:
            continue
        name, link = m.group(1).strip(), m.group(2)
        q = urllib.parse.parse_qs(urllib.parse.urlparse(link).query)
        asin = common.parse_asin(link) if "/dp/" in link else ""
        items.append({"name": name, "benefit": "", "amazon_search": (q.get("k") or [name])[0],
                      "asin": asin or "", "link": link})
    return items


def main(date):
    if not dashboard.enabled():
        sys.exit("PIPELINE_KEY missing")
    site = common.settings()["site_url"].rstrip("/")
    page_re = re.compile(re.escape(site) + r"/v/(" + re.escape(date) + r"-ch\d+-[a-z0-9-]+)/")
    st = state.load()
    made = 0
    for ch in common.channels():
        token, err = dashboard.access_token(ch["id"])
        if not token:
            print("{0}: no token ({1})".format(ch["id"], err))
            continue
        chans = get("channels?part=contentDetails&mine=true", token).get("items", [])
        if not chans:
            continue
        uploads = chans[0]["contentDetails"]["relatedPlaylists"]["uploads"]
        ids = [it["contentDetails"]["videoId"] for it in
               get("playlistItems?part=contentDetails&maxResults=50&playlistId=" + uploads, token).get("items", [])]
        if not ids:
            continue
        for v in get("videos?part=snippet,contentDetails&id=" + ",".join(ids), token).get("items", []):
            desc = v["snippet"].get("description", "")
            m = page_re.search(desc)
            if not m or not m.group(1).split("-")[3] == ch["id"]:
                continue
            key = m.group(1)
            path = os.path.join(common.VIDEOS_DATA_DIR, key + ".json")
            if os.path.exists(path):
                continue
            items = parse_items(desc)
            if not items:
                print("{0}: {1} has no product lines, skipped".format(ch["id"], key))
                continue
            first = desc.split("\n\n")[0].strip()
            title = v["snippet"]["title"]
            common.save_json(path, {
                "key": key, "date": date, "channel_id": ch["id"],
                "channel_name": ch.get("name", ""), "niche": ch["niche"],
                "title": title, "hook": title, "description": first, "items": items,
                "youtube_id": v["id"], "page_url": site + "/v/" + key + "/", "clip": "",
                "seconds": seconds(v["contentDetails"].get("duration")),
                "recovered": True,
            })
            c = state.ch(st, ch["id"])
            state.remember_topic(c, title)
            state.remember_asins(c, [it["asin"] for it in items])
            made += 1
            print("{0}: recovered {1} ({2})".format(ch["id"], key, v["id"]))
    state.save(st)
    print("recovered", made)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else common.today_utc())
