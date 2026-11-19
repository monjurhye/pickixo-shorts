"""Persistent run state committed back to the repo (data/state.json):
recent topics per channel (to avoid repeats), used stock clip ids, and
per-channel health (consecutive upload errors -> auto-disable)."""

from . import common

RECENT_TOPICS_KEEP = 60
USED_CLIPS_KEEP = 300


def load():
    st = common.load_json(common.STATE_PATH, None) or {}
    st.setdefault("channels", {})
    return st


def save(st):
    common.save_json(common.STATE_PATH, st)


def ch(st, channel_id):
    c = st["channels"].setdefault(channel_id, {})
    c.setdefault("recent_topics", [])
    c.setdefault("used_clips", [])
    c.setdefault("upload_errors", 0)
    c.setdefault("auto_disabled", False)
    c.setdefault("last_error", "")
    return c


def remember_topic(c, topic):
    c["recent_topics"] = (c["recent_topics"] + [topic])[-RECENT_TOPICS_KEEP:]


def remember_clip(c, clip_id):
    c["used_clips"] = (c["used_clips"] + [str(clip_id)])[-USED_CLIPS_KEEP:]
