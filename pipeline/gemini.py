"""Google Gemini API (free tier) for small JSON jobs: no OpenAI cost.
Needs GEMINI_API_KEY (free key from https://aistudio.google.com/apikey).
Free tier limits are per minute and per day; this waits and retries on 429."""

import json
import os
import time
import urllib.error
import urllib.request

from . import common

DEFAULT_MODEL = "gemini-flash-lite-latest"


def enabled():
    return bool(common.secret("GEMINI_API_KEY"))


def _schema(x):
    """JSON Schema -> the form Gemini's responseSchema accepts (no additionalProperties)."""
    if isinstance(x, dict):
        return {k: _schema(v) for k, v in x.items() if k != "additionalProperties"}
    if isinstance(x, list):
        return [_schema(v) for v in x]
    return x


_LAST = [0.0]


def call_json(system, user, schema, cfg, max_tokens=4000):
    model = cfg.get("gemini_model", DEFAULT_MODEL)
    gap = float(cfg.get("gemini_min_gap_seconds", 4.5))   # free tier: 15 requests a minute
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {"responseMimeType": "application/json", "responseSchema": _schema(schema),
                             "maxOutputTokens": max_tokens * 2},
    }
    # Busy (503/500/timeout) on one model -> the other free models have their own capacity.
    models = [model] + [m for m in cfg.get("gemini_fallback_models", ["gemini-flash-latest"])
                        if m != model]
    data, last = None, ""
    for mi, m in enumerate(models):
        url = "https://generativelanguage.googleapis.com/v1beta/models/{0}:generateContent".format(m)
        tries = 4 if mi == 0 else 2
        for attempt in range(tries):
            wait = gap - (time.time() - _LAST[0])
            if wait > 0:
                time.sleep(wait)
            _LAST[0] = time.time()
            req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={
                "x-goog-api-key": common.secret("GEMINI_API_KEY"), "Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=180) as r:
                    data = json.loads(r.read().decode())
                break
            except urllib.error.HTTPError as e:
                msg = e.read().decode("utf-8", "ignore")[:600]
                last = "Gemini HTTP {0}: {1}".format(e.code, msg)
                if e.code == 429 and "PerDay" in msg:
                    if mi + 1 < len(models):
                        common.log("gemini {0}: daily limit, trying {1}".format(m, models[mi + 1]))
                        break
                    raise RuntimeError("Gemini free daily limit reached (500 a day); the rest waits for tomorrow")
                if e.code == 404 and mi:  # a fallback model name that no longer exists: skip it
                    common.log("gemini {0}: not found, skipped".format(m))
                    break
                if e.code not in (429, 500, 503):
                    raise RuntimeError(last)
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                last = "Gemini network: {0}".format(e)
            if attempt + 1 < tries:
                common.log("gemini {0} busy, retrying ({1})".format(m, last[:60]))
                time.sleep(20 * (attempt + 1))
        if data is not None:
            if mi:
                common.log("gemini: answered by fallback model " + m)
            break
    if data is None:
        raise RuntimeError(last or "Gemini: no answer")
    cand = (data.get("candidates") or [{}])[0]
    text = "".join(p.get("text", "") for p in (cand.get("content") or {}).get("parts") or [])
    if not text.strip():
        raise RuntimeError("Gemini returned no text ({0})".format(cand.get("finishReason") or data.get("promptFeedback")))
    return json.loads(text)
