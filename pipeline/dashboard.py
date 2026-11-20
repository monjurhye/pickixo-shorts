"""Client for the channel dashboard at shop.pickixo.com/admin (Cloudflare Pages Functions).
Channels are connected there with a button; the pipeline asks it which channels are
active and for short-lived YouTube access tokens. Needs secret PIPELINE_KEY."""

import json
import urllib.error
import urllib.request

from . import common


def enabled():
    return bool(common.secret("PIPELINE_KEY"))


def _url(path):
    return common.settings()["site_url"].rstrip("/") + path


def _call(path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(_url(path), data=data, method="POST" if data else "GET", headers={
        "X-Pipeline-Key": common.secret("PIPELINE_KEY"),
        "Content-Type": "application/json",
        "User-Agent": "pickixo-pipeline/1.0",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode() or "{}")
        except ValueError:
            return e.code, {"error": "http_" + str(e.code)}


def state():
    """{"paused": bool, "channels": {"ch01": {"enabled": bool, "title": ..}}} or raises."""
    code, data = _call("/api/pipeline/state")
    if code != 200:
        raise RuntimeError("dashboard state failed ({0}): {1}".format(code, data))
    return data


def access_token(channel_id):
    """Returns (token, error_code)."""
    code, data = _call("/api/pipeline/token", {"ch": channel_id})
    if code == 200:
        return data["access_token"], ""
    return "", data.get("error", "http_" + str(code))


def report(channel_id, error, disable=False):
    try:
        _call("/api/pipeline/report", {"ch": channel_id, "error": error, "disable": disable})
    except Exception as e:
        common.log("dashboard report failed: {0}".format(e))


def pins_paused():
    """True if pins are paused on the dashboard (False if unreachable, so the GitHub
    variable PINS_PAUSED stays the main switch)."""
    try:
        code, data = _call("/api/pipeline/pins")
        return code == 200 and bool(data.get("paused"))
    except Exception as e:
        common.log("dashboard pins state failed: {0}".format(e))
        return False


def pins_report(run):
    try:
        code, data = _call("/api/pipeline/pins", run)
        if code != 200:
            common.log("dashboard pins report failed ({0}): {1}".format(code, data))
    except Exception as e:
        common.log("dashboard pins report failed: {0}".format(e))


def draft_report(payload):
    """Send a Medium draft (or an error note) to the dashboard."""
    try:
        code, data = _call("/api/pipeline/drafts", payload)
        if code != 200:
            common.log("dashboard draft report failed ({0}): {1}".format(code, data))
    except Exception as e:
        common.log("dashboard draft report failed: {0}".format(e))


def ideas_report(payload):
    """Send today's Magnific image ideas to the dashboard."""
    try:
        code, data = _call("/api/pipeline/ideas", payload)
        if code != 200:
            common.log("dashboard ideas report failed ({0}): {1}".format(code, data))
    except Exception as e:
        common.log("dashboard ideas report failed: {0}".format(e))


def fb_report(payload):
    """Send today's Facebook post ideas to the dashboard."""
    try:
        code, data = _call("/api/pipeline/fb", payload)
        if code != 200:
            common.log("dashboard fb report failed ({0}): {1}".format(code, data))
    except Exception as e:
        common.log("dashboard fb report failed: {0}".format(e))


def fb_state():
    try:
        code, data = _call("/api/pipeline/fb-post")
        return data if code == 200 else {"connected": False}
    except Exception:
        return {"connected": False}


def fb_post(message, image_url, when_unix):
    code, data = _call("/api/pipeline/fb-post", {"message": message, "image_url": image_url, "when": when_unix})
    if code != 200:
        raise RuntimeError(data.get("error", "http_" + str(code)))
    return data
