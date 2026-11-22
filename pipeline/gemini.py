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


def call_json(system, user, schema, cfg, max_tokens=4000):
    model = cfg.get("gemini_model", DEFAULT_MODEL)
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {"responseMimeType": "application/json", "responseSchema": _schema(schema),
                             "maxOutputTokens": max_tokens * 2},
    }
    url = "https://generativelanguage.googleapis.com/v1beta/models/{0}:generateContent".format(model)
    for attempt in range(4):
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={
            "x-goog-api-key": common.secret("GEMINI_API_KEY"), "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                data = json.loads(r.read().decode())
            break
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "ignore")[:300]
            if e.code in (429, 500, 503) and attempt < 3:
                common.log("gemini {0}, retrying".format(e.code))
                time.sleep(30 * (attempt + 1))
                continue
            raise RuntimeError("Gemini HTTP {0}: {1}".format(e.code, msg))
    cand = (data.get("candidates") or [{}])[0]
    text = "".join(p.get("text", "") for p in (cand.get("content") or {}).get("parts") or [])
    if not text.strip():
        raise RuntimeError("Gemini returned no text ({0})".format(cand.get("finishReason") or data.get("promptFeedback")))
    return json.loads(text)
