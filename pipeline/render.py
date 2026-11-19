"""Builds a 1080x1920 Short: stock clip (or a soft gradient) per scene with a bold
text card on top, then joins scenes and adds quiet music (or silence)."""

import glob
import os
import random
import subprocess

from PIL import Image, ImageDraw, ImageFont

from . import common

W, H = 1080, 1920
FPS = 30

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",          # Ubuntu (Actions)
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",             # macOS
    "/Library/Fonts/Arial Bold.ttf",
]

PALETTES = [  # (card background RGBA, accent, text) - one per channel, chosen by index
    ((15, 23, 42, 222), (250, 204, 21), (255, 255, 255)),
    ((24, 24, 27, 222), (52, 211, 153), (255, 255, 255)),
    ((30, 27, 75, 222), (244, 114, 182), (255, 255, 255)),
    ((12, 74, 110, 222), (253, 186, 116), (255, 255, 255)),
]


def _font(size):
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def _wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def text_card(path, kind, palette, title, subtitle="", badge=""):
    """Transparent full-frame PNG: rounded card in the lower-middle of the frame."""
    bg, accent, fg = palette
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    big = _font(116 if kind != "item" else 104)
    small = _font(64)
    pad, max_w = 70, W - 2 * 100
    t_lines = _wrap(d, title, big, max_w)
    s_lines = _wrap(d, subtitle, small, max_w) if subtitle else []
    line_h_big, line_h_small = 132, 80
    card_h = pad * 2 + len(t_lines) * line_h_big + (24 + len(s_lines) * line_h_small if s_lines else 0)
    if badge:
        card_h += 90
    top = int(H * 0.56) - card_h // 2
    d.rounded_rectangle([60, top, W - 60, top + card_h], radius=48, fill=bg)
    y = top + pad
    if badge:
        bf = _font(52)
        bw = d.textlength(badge, font=bf) + 60
        d.rounded_rectangle([110, y - 6, 110 + bw, y + 70], radius=35, fill=accent)
        d.text((140, y + 2), badge, font=bf, fill=(17, 17, 17))
        y += 90
    for ln in t_lines:
        d.text((110, y), ln, font=big, fill=fg)
        y += line_h_big
    if s_lines:
        y += 24
        for ln in s_lines:
            d.text((110, y), ln, font=small, fill=accent)
            y += line_h_small
    img.save(path)
    return path


def _run(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        raise RuntimeError("ffmpeg failed: " + p.stderr.decode("utf-8", "ignore")[-800:])


def _scene(ffmpeg, bg_clip, overlay_png, dur, out_path, gradient_seed=0):
    vf_fit = ("scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
              "fps={F},format=yuv420p").format(W=W, H=H, F=FPS)
    if bg_clip:
        src = ["-stream_loop", "-1", "-i", bg_clip]  # loop short clips to fill the scene
    else:
        colors = ["0x1e293b", "0x3f3f46", "0x312e81", "0x0c4a6e"]
        c = colors[gradient_seed % len(colors)]
        src = ["-f", "lavfi", "-t", "{0:.2f}".format(dur), "-i",
               "color=c={0}:s={1}x{2}:r={3}".format(c, W, H, FPS)]
    fc = ("[0:v]{fit}[bg];[bg][1:v]overlay=0:0:format=auto,"
          "fade=t=in:st=0:d=0.25,format=yuv420p[v]").format(fit=vf_fit)
    _run([ffmpeg, "-y", "-loglevel", "error"] + src +
         ["-i", overlay_png, "-filter_complex", fc, "-map", "[v]", "-an",
          "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-r", str(FPS),
          "-t", "{0:.2f}".format(dur), out_path])


def build(script, channel_index, clips, out_path, cfg, brand="Pickixo Picks"):
    """script: approved script dict. clips: list of local mp4 paths (may be empty)."""
    ffmpeg = common.ffmpeg_bin()
    work = os.path.dirname(out_path)
    palette = PALETTES[channel_index % len(PALETTES)]

    scenes = [("hook", script["hook"], "", "", float(cfg.get("seconds_hook", 3)))]
    for i, it in enumerate(script["items"], 1):
        scenes.append(("item", it["name"], it["benefit"], "#{0}".format(i),
                       float(cfg.get("seconds_per_item", 4))))
    scenes.append(("cta", script["cta"], "Link in description  ·  " + brand, "",
                   float(cfg.get("seconds_cta", 3))))

    parts = []
    for n, (kind, title, sub, badge, dur) in enumerate(scenes):
        png = text_card(os.path.join(work, "card_%02d.png" % n), kind, palette, title, sub, badge)
        clip = clips[n % len(clips)] if clips else None
        part = os.path.join(work, "scene_%02d.mp4" % n)
        _scene(ffmpeg, clip, png, dur, part, gradient_seed=channel_index + n)
        parts.append(part)

    listfile = os.path.join(work, "parts.txt")
    with open(listfile, "w") as f:
        for p in parts:
            f.write("file '{0}'\n".format(os.path.abspath(p)))
    silent = os.path.join(work, "joined.mp4")
    _run([ffmpeg, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", listfile,
          "-c", "copy", silent])

    total = sum(s[4] for s in scenes)
    tracks = glob.glob(os.path.join(common.MUSIC_DIR, "*.mp3")) + \
        glob.glob(os.path.join(common.MUSIC_DIR, "*.m4a"))
    if tracks:
        audio_in = ["-stream_loop", "-1", "-i", random.choice(tracks)]
        af = ["-af", "volume={0},afade=t=out:st={1:.2f}:d=1".format(
            cfg.get("music_volume", 0.15), max(0, total - 1))]
    else:
        audio_in = ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
        af = []
    _run([ffmpeg, "-y", "-loglevel", "error", "-i", silent] + audio_in + af +
         ["-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
          "-t", "{0:.2f}".format(total), "-movflags", "+faststart", out_path])
    return out_path, total
