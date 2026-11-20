"""Daily Facebook post ideas for the US 'Frugal Home Hacks' page (config/facebook.json).
Sent to the dashboard (/admin -> Facebook page). Nothing is posted automatically."""

from datetime import datetime, timedelta, timezone

from . import buffer, common, content, dashboard, facebook

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
                },
                "required": ["type", "time_et", "pillar", "title", "hook", "script", "visuals", "caption", "hashtags"],
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
Rules: practical, true, no medical/legal/financial guarantees, no exact prices or savings
promises ("can help you save" is fine), no fake stories, plain friendly US English."""


def main():
    cfg = common.load_json(common.os.path.join(common.CONFIG_DIR, "facebook.json"), {})
    now = datetime.now(timezone.utc)
    sysmsg = SYSTEM.format(niche=cfg.get("niche"), audience=cfg.get("audience"),
                           pillars="; ".join(cfg.get("pillars", [])),
                           reels=cfg["per_day"]["reels"], photos=cfg["per_day"]["photo_or_carousel"],
                           eng=cfg["per_day"]["engagement"], times=", ".join(cfg.get("schedule_us_et", [])),
                           date=now.strftime("%B %d, %Y"))
    res = content._call_json(sysmsg, "Write today's posts.", SCHEMA, common.settings(), 7000)
    posts = res.get("posts", [])[:6]
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
    for p in posts:
        p["status"] = "idea"
        if not auto or p["type"] == "reel":
            if p["type"] == "reel":
                p["status"] = "reel: make the video and post it yourself"
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
        main()
