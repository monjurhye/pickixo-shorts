"""Daily Facebook posts for the US 'Frugal Home Hacks' page (config/facebook.json), fully
automatic: photo and question posts are scheduled on the connected Page, and reels are
rendered (Pexels clips + AI voice + on-screen steps, same engine as the Shorts) and
scheduled through the Reels API. Everything is also shown in the dashboard."""

import os
import shutil

from datetime import datetime, timedelta, timezone

from . import buffer, common, content, dashboard, facebook, pexels, render, tts

SCHEMA = {
    "type": "object",
    "properties": {
        "posts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["reel", "photo_or_carousel", "engagement"]},
                    "time_et": {"type": "string"},
                    "pillar": {"type": "string"},
                    "title": {"type": "string"},
                    "hook": {"type": "string"},
                    "script": {"type": "string"},
                    "visuals": {"type": "string"},
                    "caption": {"type": "string"},
                    "hashtags": {"type": "array", "items": {"type": "string"}},
                    "steps": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"title": {"type": "string"}, "detail": {"type": "string"}},
                            "required": ["title", "detail"],
                            "additionalProperties": False,
                        },
                    },
                    "stock_queries": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["type", "time_et", "pillar", "title", "hook", "script", "visuals", "caption",
                             "hashtags", "steps", "stock_queries"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["posts"],
    "additionalProperties": False,
}

SYSTEM = """You plan original Facebook content for a US page. Niche: {niche}.
Audience: {audience}. Content pillars: {pillars}.
Make today's posts: {reels} reels, {photos} photo or carousel post, {eng} engagement post,
spread over these US Eastern times: {times}. Use a different pillar for each post.
Seasonal: it is {date}; use what US households deal with in the next 1-3 weeks (holidays,
weather, school, bills), but don't force it.

For each post:
- title: internal name. hook: the first line/first 2 seconds (curiosity, no clickbait lies).
- script: for reels a 20-40 second voiceover, step by step, practical and specific; for photo/
  carousel the slide texts (Slide 1: ..., Slide 2: ...); for engagement a short question post.
- visuals: what to film or which AI/stock visuals to use (no people's faces needed, no brands).
- caption: 1-3 short lines + a question to get comments. If a product is useful, say
  "link in comments (#ad)" instead of putting a link.
- hashtags: 3-5, lowercase, no '#'.
- steps: for reels 3-5 steps shown on screen and spoken (title <= 5 words, detail <= 10 words,
  plain and specific); for other posts an empty list.
- stock_queries: for reels 3-4 short phrases for calm stock footage that fits (scenes, not
  brands or faces), e.g. "kitchen pantry shelves"; for other posts an empty list.
Rules: practical, true, no medical/legal/financial guarantees, no exact prices or savings
promises ("can help you save" is fine), no fake stories, plain friendly US English."""


def make_and_schedule_reel(p, idx, when, target):
    """Render a vertical reel for post p and schedule it on the Page."""
    cfg = dict(common.settings(), seconds_hook=3.0, seconds_per_item=4.0, seconds_cta=3.0)
    steps = [s for s in p.get("steps", []) if s.get("title")][:5]
    if len(steps) < 2:
        raise RuntimeError("reel has too few steps")
    script = {"hook": p["hook"][:80], "cta": "Follow for more money-saving home tips",
              "cta_badge": "Follow for daily tips", "cta_voice_extra": "", "steps_voice": True,
              "items": [{"name": s["title"][:40], "benefit": s["detail"][:80]} for s in steps]}
    work = os.path.join(common.WORK_DIR, "fb-reel-{0}".format(idx))
    os.makedirs(work, exist_ok=True)
    try:
        clips, key = [], common.secret("PEXELS_API_KEY")
        if key:
            queries = list(p.get("stock_queries", [])) + [p.get("pillar", "")[:40], "home kitchen"]
            for c in pexels.find_clips(queries, 3, [], key):
                try:
                    clips.append(pexels.download(c, work))
                except Exception as e:
                    common.log("reel clip download failed: " + str(e)[:100])
        voices = None
        if common.secret("OPENAI_API_KEY") and cfg.get("tts_enabled", True):
            voices = tts.voice_scenes(script, tts.voice_for(idx, cfg), work, cfg)
        out = os.path.join(work, "reel.mp4")
        render.build(script, idx + 3, clips, out, cfg, "Frugal Home Hacks", voice_files=voices)
        desc = "{0}\n\n{1}\n\n{2}\nVoice: AI-generated · Stock footage: Pexels".format(
            p["hook"].strip(), p["caption"].strip(), " ".join("#" + h.strip("#") for h in p["hashtags"][:5]))
        vid = facebook.upload_reel(target["page_id"], target["token"], out, desc, when)
        common.log("reel scheduled: {0} at {1}".format(vid, when.isoformat()))
        return vid
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main(test_reel=False):
    cfg = common.load_json(common.os.path.join(common.CONFIG_DIR, "facebook.json"), {})
    now = datetime.now(timezone.utc)
    sysmsg = SYSTEM.format(niche=cfg.get("niche"), audience=cfg.get("audience"),
                           pillars="; ".join(cfg.get("pillars", [])),
                           reels=cfg["per_day"]["reels"], photos=cfg["per_day"]["photo_or_carousel"],
                           eng=cfg["per_day"]["engagement"], times=", ".join(cfg.get("schedule_us_et", [])),
                           date=now.strftime("%B %d, %Y"))
    res = content._call_json(sysmsg, "Write today's posts.", SCHEMA, common.settings(), 7000)
    posts = res.get("posts", [])[:6]
    if test_reel:  # one real reel only, at the evening slot, no other posts, no dashboard update
        reels = [p for p in posts if p["type"] == "reel"]
        if not reels:
            raise SystemExit("no reel in the plan")
        p = reels[0]
        when = facebook.et_to_utc(now.strftime("%Y-%m-%d"), cfg.get("schedule_us_et", ["7:30 PM"])[-1])
        if when < now + timedelta(minutes=20):
            when += timedelta(days=1)
        target = dashboard.fb_token() if dashboard.enabled() else {
            "page_id": common.secret("FB_PAGE_ID"), "token": common.secret("FB_PAGE_TOKEN")}
        print("test reel:", p["title"], "|", when.isoformat(), "| page", target.get("name", target["page_id"]))
        make_and_schedule_reel(p, 0, when, target)
        return
    date = now.strftime("%Y-%m-%d")
    # Post route: the Graph API if FB secrets exist, otherwise the Facebook Page connected in Buffer.
    via, bch = "", None
    if cfg.get("autopost", True):
        if dashboard.enabled() and dashboard.fb_state().get("connected"):
            via = "dashboard"
        elif facebook.enabled():
            via = "graph"
        elif buffer.enabled():
            try:
                bch = buffer.find_channel("facebook")
                via = "buffer" if bch else ""
            except buffer.BufferError as e:
                common.log("buffer: " + str(e))
    auto = bool(via)
    reel_target = None
    if auto and cfg.get("auto_reels", True):
        try:
            reel_target = dashboard.fb_token() if via == "dashboard" else (
                {"page_id": common.secret("FB_PAGE_ID"), "token": common.secret("FB_PAGE_TOKEN")} if via == "graph" else None)
        except Exception as e:
            common.log("reels: no page token: " + str(e)[:150])
    for idx, p in enumerate(posts):
        p["status"] = "idea"
        if not auto:
            continue
        if p["type"] == "reel":
            if not reel_target:
                p["status"] = "reel: not posted (needs the Page connected in the dashboard)"
                continue
            try:
                when = facebook.et_to_utc(date, p["time_et"])
                if when < now + timedelta(minutes=20):
                    when += timedelta(days=1)
                make_and_schedule_reel(p, idx, when, reel_target)
                p["status"] = "scheduled " + p["time_et"] + " ET (reel)"
            except Exception as e:
                p["status"] = "error: reel " + str(e)[:150]
            continue
        try:
            when = facebook.et_to_utc(date, p["time_et"])
            if when < now + timedelta(minutes=20):
                when += timedelta(days=1)
            msg = p["caption"].strip() + "\n\n" + " ".join("#" + h.strip("#") for h in p["hashtags"][:5])
            img = ""
            if p["type"] == "photo_or_carousel":
                img = facebook.pexels_photo(p["visuals"][:80]) or facebook.pexels_photo(p["pillar"][:60])
                if not img:
                    raise facebook.FBError("no photo found")
            msg = p["hook"].strip() + "\n\n" + msg
            if via == "dashboard":
                dashboard.fb_post(msg, img, int(when.timestamp()))
            elif via == "graph":
                facebook.schedule_photo(msg, img, when) if img else facebook.schedule_text(msg, when)
            else:
                buffer.create_post(bch[1], msg, img, when.strftime("%Y-%m-%dT%H:%M:%S.000Z"))
            p["status"] = "scheduled " + p["time_et"] + " ET (" + via + ")"
        except Exception as e:
            p["status"] = "error: " + str(e)[:150]
    payload = {"date": date, "created": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "posts": posts,
               "autopost": bool(auto)}
    if dashboard.enabled():
        dashboard.fb_report(payload)
    common.log("facebook ideas: {0}".format(len(payload["posts"])))


if __name__ == "__main__":
    import sys
    if "--check" in sys.argv:
        if facebook.enabled():
            print(facebook.check())
        print("dashboard facebook:", dashboard.fb_state() if dashboard.enabled() else "no PIPELINE_KEY")
        print("buffer facebook channel:", buffer.find_channel("facebook") if buffer.enabled() else "no BUFFER_API_KEY")
    else:
        main(test_reel="--test-reel" in sys.argv)
