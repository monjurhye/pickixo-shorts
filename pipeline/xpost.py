"""Cross-post the best Shorts to Facebook (a separate Page), Instagram Reels, Threads and Bluesky.

Once a day it ranks the Shorts uploaded in the last 3 days (at least ~1 day old) by YouTube views
and queues the top `xpost_per_day` (default 5). Every daily run then posts up to `xpost_per_run`
of them, so the posts are spread over the day instead of arriving all at once. The same video goes
to every connected platform, always with the affiliate + AI-voice disclosure.

Accounts are connected in /admin -> Cross-post (tokens stay in Cloudflare KV); the pipeline asks
the dashboard for them. Video files come from pipeline/clips.py (GitHub Release assets).

  python -m pipeline.xpost             # post what is due now
  python -m pipeline.xpost --dry-run   # show the queue and captions, post nothing
"""

import argparse
import glob
import json
import os
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from . import clips, common, dashboard, facebook

STATE = os.path.join(common.DATA_DIR, "xpost.json")
GRAPH = "https://graph.facebook.com/v21.0"
THREADS = "https://graph.threads.net/v1.0"
BSKY = "https://bsky.social"
VIDEO_SVC = "https://video.bsky.app"
PLATFORMS = ("facebook", "instagram", "threads", "bluesky")


class PostError(Exception):
    pass


def _http(method, url, data=None, headers=None, timeout=120):
    h = {"User-Agent": "pickixo-pipeline/1.0"}
    h.update(headers or {})
    if isinstance(data, dict):
        data = urllib.parse.urlencode(data).encode()
        h.setdefault("Content-Type", "application/x-www-form-urlencoded")
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode() or "{}"
            return json.loads(body)
    except urllib.error.HTTPError as e:
        raise PostError("{0} {1}: {2}".format(e.code, url.split("?")[0].split("/")[-1],
                                              e.read().decode("utf-8", "ignore")[:300]))


# ---------- captions ----------

def _short(text, n):
    text = " ".join(str(text or "").split())
    return text if len(text) <= n else text[:n - 1].rstrip() + "…"


def captions(rec, cfg):
    """Every caption carries the Amazon affiliate links (the channel's own tracking ID, same links as
    the YouTube description) plus the disclosure. Instagram captions can't hold clickable links, so
    the links are listed as text and the bio link (shop.pickixo.com) is the clickable path."""
    title, hook, url = rec.get("title", ""), rec.get("hook", ""), rec["page_url"]
    items = [it for it in rec.get("items", []) if it.get("link")]
    disclosure = cfg.get("disclosure", "As an Amazon Associate I earn from qualifying purchases. #ad")
    tags = " ".join(["#amazonfinds", "#" + common.slugify(rec.get("niche", "finds"), 30).replace("-", "")])
    lines = "\n".join("• {0}: {1}".format(_short(it.get("name", ""), 60), it["link"]) for it in items)

    def fit(head, links, tail, limit):
        """head + as many links as fit + tail, within `limit` characters."""
        body = ""
        for it in links:
            add = "\n🛒 {0}: {1}".format(_short(it.get("name", ""), 40), it["link"])
            if len(head) + len(body) + len(add) + len(tail) > limit:
                break
            body += add
        return head + (body or "\n🛒 " + url) + tail

    return {
        "facebook": "{0}\n\n{1}\n\n{2}\n\nAll finds: {3}\n\n{4}\nVoice: AI-generated\n{5}".format(
            title, hook, lines, url, disclosure, tags),
        "instagram": "{0}\n\n{1}\n\n🛒 Links in bio → shop.pickixo.com\n{2}\n\n{3}\nVoice: AI-generated\n{4}".format(
            title, hook, lines, disclosure, tags),
        "threads": fit(_short(title, 150) + "\n", items, "\n\n#ad Amazon affiliate links · AI voice", 495),
        "bluesky": fit(_short(title, 90) + "\n", items[:1], "\n#ad Amazon affiliate · AI voice", 295),
    }


# ---------- platforms ----------

def post_facebook(acc, path, caption):
    return facebook.upload_reel(acc["page_id"], acc["token"], path, caption)


def _wait(fetch, ok, bad, what, tries=40, every=10):
    for _ in range(tries):
        time.sleep(every)
        st = fetch()
        if st in ok:
            return
        if st in bad:
            raise PostError("{0} processing failed ({1})".format(what, st))
    raise PostError(what + " processing timed out")


def post_instagram(acc, clip_url, caption):
    c = _http("POST", "{0}/{1}/media".format(GRAPH, acc["ig_id"]), {
        "media_type": "REELS", "video_url": clip_url, "caption": caption[:2200], "share_to_feed": "true",
        "access_token": acc["token"]})
    cid = c["id"]
    _wait(lambda: _http("GET", "{0}/{1}?fields=status_code&access_token={2}".format(
        GRAPH, cid, urllib.parse.quote(acc["token"]))).get("status_code"), ("FINISHED",), ("ERROR", "EXPIRED"), "Instagram")
    return _http("POST", "{0}/{1}/media_publish".format(GRAPH, acc["ig_id"]),
                 {"creation_id": cid, "access_token": acc["token"]})["id"]


def post_threads(acc, clip_url, text):
    c = _http("POST", "{0}/{1}/threads".format(THREADS, acc["user_id"]), {
        "media_type": "VIDEO", "video_url": clip_url, "text": text, "access_token": acc["token"]})
    cid = c["id"]
    _wait(lambda: _http("GET", "{0}/{1}?fields=status,error_message&access_token={2}".format(
        THREADS, cid, urllib.parse.quote(acc["token"]))).get("status"), ("FINISHED",), ("ERROR", "EXPIRED"), "Threads")
    return _http("POST", "{0}/{1}/threads_publish".format(THREADS, acc["user_id"]),
                 {"creation_id": cid, "access_token": acc["token"]})["id"]


def _bsky_facets(text):
    """Clickable link facets for every http(s) URL in the text (byte offsets, as Bluesky wants)."""
    import re
    out, b = [], text.encode("utf-8")
    for m in re.finditer(rb"https?://[^\s]+", b):
        out.append({"index": {"byteStart": m.start(), "byteEnd": m.end()},
                    "features": [{"$type": "app.bsky.richtext.facet#link", "uri": m.group().decode()}]})
    return out


def post_bluesky(acc, path, text, name):
    s = _http("POST", BSKY + "/xrpc/com.atproto.server.createSession",
              json.dumps({"identifier": acc["handle"], "password": acc["app_password"]}).encode(),
              {"Content-Type": "application/json"})
    jwt, did = s["accessJwt"], s["did"]
    pds = BSKY
    for svc in (s.get("didDoc") or {}).get("service", []):
        if svc.get("id", "").endswith("#atproto_pds"):
            pds = svc.get("serviceEndpoint", BSKY).rstrip("/")
    with open(path, "rb") as f:
        data = f.read()
    blob = None
    try:  # recommended path: Bluesky's video service (transcodes for every player)
        aud = "did:web:" + urllib.parse.urlparse(pds).hostname
        tok = _http("GET", "{0}/xrpc/com.atproto.server.getServiceAuth?{1}".format(pds, urllib.parse.urlencode({
            "aud": aud, "lxm": "com.atproto.repo.uploadBlob", "exp": int(time.time()) + 1800})),
            headers={"Authorization": "Bearer " + jwt})["token"]
        try:
            up = _http("POST", "{0}/xrpc/app.bsky.video.uploadVideo?{1}".format(VIDEO_SVC, urllib.parse.urlencode(
                {"did": did, "name": name})), data, {"Authorization": "Bearer " + tok, "Content-Type": "video/mp4"}, timeout=300)
        except PostError as e:
            if "already_exists" not in str(e):
                raise
            up = json.loads(str(e).split(": ", 1)[1])
        job = (up.get("jobStatus") or up).get("jobId")
        for _ in range(40):
            time.sleep(5)
            st = _http("GET", "{0}/xrpc/app.bsky.video.getJobStatus?jobId={1}".format(VIDEO_SVC, job),
                       headers={"Authorization": "Bearer " + jwt}).get("jobStatus", {})
            if st.get("blob"):
                blob = st["blob"]
                break
            if st.get("state") == "JOB_STATE_FAILED":
                raise PostError("Bluesky video failed: " + str(st.get("error") or st.get("message")))
    except PostError as e:
        common.log("bluesky video service: {0}; uploading the blob directly".format(e))
    if blob is None:  # fallback: plain blob upload to the PDS
        blob = _http("POST", pds + "/xrpc/com.atproto.repo.uploadBlob", data,
                     {"Authorization": "Bearer " + jwt, "Content-Type": "video/mp4"}, timeout=300)["blob"]
    record = {"$type": "app.bsky.feed.post", "text": text, "facets": _bsky_facets(text), "langs": ["en"],
              "createdAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
              "embed": {"$type": "app.bsky.embed.video", "video": blob, "aspectRatio": {"width": 1080, "height": 1920}}}
    r = _http("POST", pds + "/xrpc/com.atproto.repo.createRecord",
              json.dumps({"repo": did, "collection": "app.bsky.feed.post", "record": record}).encode(),
              {"Authorization": "Bearer " + jwt, "Content-Type": "application/json"})
    return r.get("uri", "")


# ---------- choosing videos ----------

def youtube_views(recs):
    """{youtube_id: views} using any connected channel's token (public statistics)."""
    out = {}
    ids = [r["youtube_id"] for r in recs if r.get("youtube_id")]
    if not ids or not dashboard.enabled():
        return out
    token = ""
    for r in recs:
        token, _ = dashboard.access_token(r["channel_id"])
        if token:
            break
    if not token:
        return out
    for i in range(0, len(ids), 50):
        d = _http("GET", "https://www.googleapis.com/youtube/v3/videos?part=statistics&id=" + ",".join(ids[i:i + 50]),
                  headers={"Authorization": "Bearer " + token})
        for it in d.get("items", []):
            out[it["id"]] = int(it.get("statistics", {}).get("viewCount", 0))
    return out


def build_queue(st, today, per_day):
    start = (datetime.strptime(today, "%Y-%m-%d") - timedelta(days=3)).strftime("%Y-%m-%d")
    recs = []
    for f in glob.glob(os.path.join(common.VIDEOS_DATA_DIR, "*.json")):
        r = common.load_json(f, {})
        if r.get("clip") and r.get("youtube_id") and start <= r.get("date", "") < today and r["key"] not in st["posted"]:
            recs.append(r)
    try:
        views = youtube_views(recs)
    except Exception as e:
        common.log("xpost: views not available ({0}); newest first".format(e))
        views = {}
    recs.sort(key=lambda r: (views.get(r["youtube_id"], -1), r["date"]), reverse=True)
    pick = []
    for r in recs:  # at most 2 from one channel, so the day is not one niche
        if sum(1 for p in pick if p["channel_id"] == r["channel_id"]) < 2:
            pick.append(r)
        if len(pick) >= per_day:
            break
    return {"date": today, "keys": [r["key"] for r in pick], "views": {r["key"]: views.get(r["youtube_id"], -1) for r in pick}}


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    cfg = common.settings()
    per_day, per_run = int(cfg.get("xpost_per_day", 5)), int(cfg.get("xpost_per_run", 2))
    st = common.load_json(STATE, {}) or {}
    st.setdefault("posted", {})
    st.setdefault("queue", {})
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    accounts = {}
    if dashboard.enabled():
        try:
            accounts = dashboard.xpost_config()
        except Exception as e:
            common.log("xpost: dashboard config failed: {0}".format(e))
            return
    if accounts.get("paused"):
        common.log("xpost: paused in the dashboard")
        return
    live = [p for p in PLATFORMS if accounts.get(p)]
    if not live and not args.dry_run:
        common.log("xpost: no account connected yet (/admin -> Cross-post)")
        return

    if st["queue"].get("date") != today:
        st["queue"] = build_queue(st, today, per_day)
        common.log("xpost: queue for {0}: {1}".format(today, st["queue"]["keys"]))
        if not args.dry_run:
            try:
                common.log("xpost: removed {0} old clip releases".format(clips.cleanup()))
            except Exception as e:
                common.log("xpost: cleanup failed: {0}".format(e))
    done_today = sum(1 for v in st["posted"].values() if v.get("at", "").startswith(today))
    due = [k for k in st["queue"]["keys"] if k not in st["posted"]][:max(0, min(per_run, per_day - done_today))]
    results = []
    for key in due:
        rec = common.load_json(os.path.join(common.VIDEOS_DATA_DIR, key + ".json"), {})
        if not rec:
            continue
        caps = captions(rec, cfg)
        if args.dry_run:
            print(json.dumps({"key": key, "clip": rec.get("clip"), "captions": caps}, ensure_ascii=False, indent=1))
            continue
        work = os.path.join(common.WORK_DIR, "xpost-" + key)
        os.makedirs(work, exist_ok=True)
        path = os.path.join(work, key + ".mp4")
        row = {"key": key, "title": rec.get("title", ""), "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "views": st["queue"].get("views", {}).get(key, -1)}
        try:
            urllib.request.urlretrieve(clips.github_url(rec["clip"]), path)
            for p in live:
                try:
                    acc = accounts[p]
                    if p == "facebook":
                        row[p] = "ok " + str(post_facebook(acc, path, caps[p]))
                    elif p == "instagram":
                        row[p] = "ok " + str(post_instagram(acc, rec["clip"], caps[p]))
                    elif p == "threads":
                        row[p] = "ok " + str(post_threads(acc, rec["clip"], caps[p]))
                    elif p == "bluesky":
                        row[p] = "ok " + str(post_bluesky(acc, path, caps[p], key + ".mp4"))
                except Exception as e:
                    row[p] = "error: " + str(e)[:200]
                common.log("xpost [{0}] {1}: {2}".format(key, p, row[p]))
        except Exception as e:
            row["error"] = "clip download failed: " + str(e)[:200]
            common.log("xpost [{0}] {1}".format(key, row["error"]))
        finally:
            shutil.rmtree(work, ignore_errors=True)
        st["posted"][key] = row
        results.append(row)

    if args.dry_run:
        return
    # keep 30 days of history
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
    st["posted"] = {k: v for k, v in st["posted"].items() if v.get("at", "")[:10] >= cutoff}
    common.save_json(STATE, st)
    if dashboard.enabled():
        recent = sorted(st["posted"].values(), key=lambda v: v.get("at", ""), reverse=True)[:20]
        dashboard.xpost_report({"updated": today, "queue": st["queue"], "recent": recent})


if __name__ == "__main__":
    main()
