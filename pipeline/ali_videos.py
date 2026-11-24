"""YouTube Shorts for the watch channel (config/ali_videos.json, default ch21) from AliExpress.

AliExpress best sellers that come with a seller video (product_video_url from the official
Affiliates API) -> the video's own sound and music are dropped -> our own free AI voiceover
(Kokoro) + on-screen feature cards are added (render.build) -> uploaded with the affiliate link.
Products that name a real watch brand (or look like replicas) are skipped.

  python -m pipeline.ali_videos              # make + upload (videos_per_run)
  python -m pipeline.ali_videos --no-upload  # make only (test), nothing recorded
"""

import os
import re
import shutil
import subprocess
import sys
import urllib.request

from . import aliexpress, common, content, dashboard, render, tts, youtube

CONFIG = os.path.join(common.CONFIG_DIR, "ali_videos.json")
STATE = os.path.join(common.DATA_DIR, "ali_videos.json")

# real brands (incl. the ones replicas copy) and replica words: never promoted
BRANDS_RE = re.compile(
    r"\b(rolex|omega|cartier|patek|audemars|hublot|breitling|tag ?heuer|tudor|longines|tissot|"
    r"seiko|citizen|casio|g-?shock|orient|bulova|fossil|michael kors|armani|hugo boss|"
    r"tommy|guess|daniel wellington|swatch|invicta|movado|rado|panerai|iwc|zenith|chopard|"
    r"richard mille|vacheron|jaeger|apple|iwatch|samsung|galaxy|huawei|xiaomi|garmin|amazfit|"
    r"fitbit|disney|marvel|replica|aaa|1:1|homage|copy)\b", re.I)
BANNED = ("today only", "limited time", "selling out", "flash sale", "guaranteed", "lowest price",
          "free shipping", "% off", "best watch ever")
PRICE_RE = re.compile(r"[$€£]\s?\d|\d+\s?(usd|dollars)", re.I)

SCHEMA = {
    "type": "object",
    "properties": {
        "ok": {"type": "boolean"},
        "title": {"type": "string"},
        "hook": {"type": "string"},
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"name": {"type": "string"}, "benefit": {"type": "string"}},
                "required": ["name", "benefit"],
                "additionalProperties": False,
            },
        },
        "cta": {"type": "string"},
        "description": {"type": "string"},
        "hashtags": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["ok", "title", "hook", "items", "cta", "description", "hashtags"],
    "additionalProperties": False,
}

SYSTEM = """You write a 20-30 second YouTube Short voiceover for a budget watch channel
("Affordable Watch Reviews", US viewers). The video shows the seller's own product footage
with its sound removed; your text is spoken by an AI voice and shown on screen.
Given one AliExpress product's raw title and category, write:
- ok: false if the product names or imitates a real brand (Rolex, Casio, Apple...), looks like
  a replica/knock-off, is not a watch or watch accessory, or the title is too unclear to
  describe honestly; otherwise true.
- title: YouTube title <= 70 characters, natural, says what the watch is (no brand names,
  no ALL CAPS, at most one emoji).
- hook: one spoken sentence <= 12 words that makes a viewer keep watching.
- items: exactly 3 features. name <= 4 words, benefit <= 10 words. ONLY features that the
  title itself states (e.g. "waterproof", "luminous", "chronograph", "stainless steel");
  never invent specs, water-resistance depth, battery life or materials.
- cta: short spoken line, e.g. "Check the link in the description".
- description: 1-2 plain sentences about the watch for the YouTube description.
- hashtags: 3-5 lowercase, no '#'.
Rules: never say a price, discount or shipping time; no fake urgency; never claim you
personally tested, owned or reviewed it; no superlatives you cannot know ("best", "#1")."""


def load_cfg():
    return common.load_json(CONFIG, {})


def checks(s, raw_title):
    issues = []
    blob = " ".join([s["title"], s["hook"], s["cta"], s["description"]] +
                    [i["name"] + " " + i["benefit"] for i in s["items"]]).lower()
    issues += ["banned phrase " + b for b in BANNED if b in blob]
    m = BRANDS_RE.search(blob + " " + raw_title.lower())
    if m:
        issues.append("brand or replica: " + m.group(0))
    if PRICE_RE.search(blob):
        issues.append("price mentioned")
    if not s.get("ok"):
        issues.append("writer flagged product")
    if len(s["items"]) < 2:
        issues.append("too few features")
    return issues


def pick_products(cfg, st, want):
    """Best sellers with a seller video, not posted before, no brand in the title."""
    done = set(st.get("posted", {}))
    kws = cfg.get("keywords") or ["men watch"]
    start = int(st.get("keyword_index", 0))
    min_rate = float(cfg.get("min_rating_percent", 90))
    out = []
    for n in range(len(kws)):
        kw = kws[(start + n) % len(kws)]
        st["keyword_index"] = (start + n + 1) % len(kws)
        try:
            prods = aliexpress.hot_products(kw, cfg.get("tracking_id", "Pinterest"), page_size=40)
        except aliexpress.AliError as e:
            common.log("aliexpress {0}: {1}".format(kw, e))
            continue
        for p in prods:
            rate = float(str(p.get("rating") or "0").rstrip("%") or 0)
            if (p["video"] and p["id"] not in done and not BRANDS_RE.search(p["title"])
                    and (rate == 0 or rate >= min_rate)):
                out.append(dict(p, keyword=kw))
                done.add(p["id"])
                break  # one per keyword: variety
        if len(out) >= want:
            break
    return out


def download(url, path, max_mb):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 pickixo-videos/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r, open(path, "wb") as f:
        total = 0
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            total += len(chunk)
            if total > max_mb * (1 << 20):
                raise RuntimeError("video larger than {0} MB".format(max_mb))
            f.write(chunk)
    if os.path.getsize(path) < 50_000:
        raise RuntimeError("video too small / not a video")
    return path


def segments(src, n, work):
    """Cut the seller video (sound dropped) into n consecutive pieces, one per scene,
    so every scene shows a different part of the product."""
    ff = common.ffmpeg_bin()
    total = tts.duration(src)
    if total < 2:
        raise RuntimeError("seller video too short ({0:.1f}s)".format(total))
    step = total / n
    out = []
    for i in range(n):
        p = os.path.join(work, "seg_%02d.mp4" % i)
        subprocess.run([ff, "-y", "-loglevel", "error", "-ss", "{0:.2f}".format(i * step), "-i", src,
                        "-t", "{0:.2f}".format(max(step, 1.0)), "-an", "-c:v", "libx264",
                        "-preset", "veryfast", "-crf", "21", p], check=True)
        out.append(p)
    return out


def make_one(p, cfg, settings, upload, idx):
    raw = p["title"]
    s = content._call_json(SYSTEM, "Product title: {0}\nCategory: {1}".format(raw, p.get("category", "")),
                           SCHEMA, settings, 2000)
    s["items"] = s["items"][:3]
    issues = checks(s, raw)
    if issues:
        return {"id": p["id"], "status": "skipped", "note": "; ".join(issues)[:200]}
    work = os.path.join(common.WORK_DIR, "ali-" + p["id"])
    os.makedirs(work, exist_ok=True)
    try:
        src = download(p["video"], os.path.join(work, "seller.mp4"), int(cfg.get("max_video_mb", 60)))
        script = {"hook": s["hook"], "items": s["items"], "cta": s["cta"],
                  "cta_badge": "Link in Description", "cta_voice_extra": ""}
        clips = segments(src, len(script["items"]) + 2, work)
        rcfg = dict(settings, music_off=True)  # the seller's sound is already gone; voice only
        voices = tts.voice_scenes(script, tts.voice_for(idx + 5, rcfg), work, rcfg) \
            if rcfg.get("tts_enabled", True) else None
        out = os.path.join(work, "short.mp4")
        render.build(script, 20 + idx, clips, out, rcfg, "Affordable Watch Reviews", voice_files=voices)
        desc = ("{0}\n\n🛒 See it on AliExpress (affiliate link): {1}\n\n"
                "#ad As an affiliate I may earn a commission if you buy through this link.\n"
                "Footage: the seller's product video (sound removed). Voice: AI-generated.\n\n{2}").format(
            s["description"].strip(), p["link"],
            " ".join("#" + h.strip("#") for h in s["hashtags"][:5] + ["shorts"]))
        if not upload:
            keep = os.path.join(common.WORK_DIR, "ali-test-{0}.mp4".format(p["id"]))
            shutil.copy(out, keep)
            return {"id": p["id"], "status": "built", "note": s["title"], "file": keep}
        vid = youtube.upload(cfg.get("channel", "ch21"), out, s["title"], desc,
                             s["hashtags"] + ["watch", "shorts"], dict(settings, youtube_category_id="26"))
        return {"id": p["id"], "status": "uploaded", "note": s["title"], "youtube_id": vid}
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main():
    upload = "--no-upload" not in sys.argv
    cfg, settings = load_cfg(), common.settings()
    if not cfg.get("enabled", True):
        common.log("ali videos: off in config/ali_videos.json")
        return
    if not aliexpress.enabled():
        common.log("ali videos: no ALIEXPRESS_APP_KEY / SECRET")
        return
    ch = cfg.get("channel", "ch21")
    if upload and dashboard.enabled():
        info = (dashboard.state().get("channels") or {}).get(ch)
        if not info or not info.get("enabled"):
            common.log("ali videos: {0} not connected or paused in /admin, nothing made".format(ch))
            return
    st = common.load_json(STATE, {"posted": {}, "keyword_index": 0})
    want = max(1, int(cfg.get("videos_per_run", 1)))
    made = 0
    for idx, p in enumerate(pick_products(cfg, st, want * 4)):  # spares for skipped ones
        if made >= want:
            break
        try:
            r = make_one(p, cfg, settings, upload, idx)
        except youtube.UploadError as e:
            common.log("ali videos: upload error: " + str(e)[:200])
            break
        except Exception as e:
            r = {"id": p["id"], "status": "error", "note": str(e)[:200]}
        common.log("ali video [{0}] {1}: {2}".format(p["id"], r["status"], r.get("note", "")))
        if r["status"] in ("uploaded", "built"):
            made += 1
        if upload and r["status"] in ("uploaded", "skipped"):
            st["posted"][p["id"]] = {"date": common.today_utc(), "status": r["status"],
                                     "title": r.get("note", "")[:100], "youtube_id": r.get("youtube_id", ""),
                                     "keyword": p["keyword"]}
    if upload:
        common.save_json(STATE, st)
    common.log("ali videos: {0} made".format(made))


if __name__ == "__main__":
    main()
