"""AI voiceover with OpenAI text-to-speech (needs OPENAI_API_KEY).
Disclosed in every video description as "Voice: AI-generated"."""

import os
import re
import subprocess

from . import common

VOICES = ["coral", "nova", "sage", "shimmer", "alloy", "ash", "echo", "verse"]
STYLE = ("Warm, upbeat and friendly, like recommending finds to a friend. "
         "Natural pace, clear American English, no exaggerated hype.")


def voice_for(channel_index, cfg):
    voices = cfg.get("tts_voices") or VOICES
    return voices[channel_index % len(voices)]


def synth(text, voice, out_path, cfg):
    import openai
    client = openai.OpenAI()
    with client.audio.speech.with_streaming_response.create(
            model=cfg.get("tts_model", "gpt-4o-mini-tts"),
            voice=voice,
            input=text,
            instructions=STYLE,
            response_format="mp3") as resp:
        resp.stream_to_file(out_path)
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
