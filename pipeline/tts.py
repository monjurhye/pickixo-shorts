"""AI voiceover with Kokoro (free, open-source text-to-speech; runs on the GitHub runner's CPU).
Model: Kokoro-82M (Apache 2.0) through kokoro-onnx (MIT). No API key, no per-video cost.
Disclosed in every video description as "Voice: AI-generated"."""

import os
import re
import subprocess
import urllib.request
import wave

from . import common

# American English Kokoro voices, one per channel in turn (af_ = female, am_ = male).
VOICES = ["af_heart", "am_michael", "af_bella", "am_fenrir", "af_nicole", "am_puck", "af_sarah", "af_kore"]
MODEL_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
MODEL_FILES = ("kokoro-v1.0.onnx", "voices-v1.0.bin")
_KOKORO = None


def voice_for(channel_index, cfg):
    voices = cfg.get("tts_voices") or VOICES
    return voices[channel_index % len(voices)]


def _model_dir():
    d = os.environ.get("KOKORO_DIR") or os.path.join(os.path.expanduser("~"), ".cache", "kokoro")
    os.makedirs(d, exist_ok=True)
    for name in MODEL_FILES:   # downloaded once (cached by the workflow), ~350 MB
        path = os.path.join(d, name)
        if not os.path.exists(path):
            common.log("downloading Kokoro " + name)
            urllib.request.urlretrieve(MODEL_URL + name, path + ".part")
            os.replace(path + ".part", path)
    return d


def _engine():
    global _KOKORO
    if _KOKORO is None:
        from kokoro_onnx import Kokoro  # lazy: only runs that speak need it
        d = _model_dir()
        _KOKORO = Kokoro(os.path.join(d, MODEL_FILES[0]), os.path.join(d, MODEL_FILES[1]))
    return _KOKORO


def synth(text, voice, out_path, cfg):
    import numpy as np
    samples, rate = _engine().create(text, voice=voice, speed=float(cfg.get("tts_speed", 1.05)), lang="en-us")
    wav = out_path + ".wav"
    with wave.open(wav, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes((np.clip(samples, -1, 1) * 32767).astype("<i2").tobytes())
    subprocess.run([common.ffmpeg_bin(), "-y", "-loglevel", "error", "-i", wav, "-b:a", "128k", out_path], check=True)
    os.remove(wav)
    return out_path


def duration(path):
    """Seconds, read from ffmpeg's banner (works without ffprobe)."""
    p = subprocess.run([common.ffmpeg_bin(), "-hide_banner", "-i", path],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", p.stderr.decode("utf-8", "ignore"))
    if not m:
        return 0.0
    h, mi, s = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(s)


def scene_lines(script):
    """What is spoken over each scene (same order as render scenes)."""
    lines = [script["hook"]]
    words = ["one", "two", "three", "four", "five", "six"]
    for i, it in enumerate(script["items"]):
        if script.get("steps_voice"):  # Facebook reels: "Step one: ..." style
            lines.append("{0}. {1}.".format(it["name"].rstrip("."), it["benefit"].rstrip(".")))
        else:
            lines.append("Number {0}: {1}. {2}.".format(words[i] if i < len(words) else i + 1,
                                                         it["name"], it["benefit"].rstrip(".")))
    lines.append(script["cta"].rstrip(".") + "." + script.get("cta_voice_extra", " Product links are in the description."))
    return lines


def voice_scenes(script, voice, work_dir, cfg):
    """Returns list of (mp3_path or None) per scene. Failures leave None (silent scene)."""
    out = []
    for n, line in enumerate(scene_lines(script)):
        path = os.path.join(work_dir, "voice_%02d.mp3" % n)
        try:
            synth(line, voice, path, cfg)
            out.append(path)
        except Exception as e:
            common.log("tts failed for scene {0}: {1}".format(n, str(e)[:150]))
            out.append(None)
    return out
