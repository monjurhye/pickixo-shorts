"""Generates soft, royalty-free background pads (our own synthesis, so no copyright
issues) into assets/music/. Run once:  python3 tools/make_music.py
Needs ffmpeg (or FFMPEG env var pointing at one)."""

import math
import os
import shutil
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "music")
SECONDS = 48

# note name -> frequency (octave 3/4)
N = {"C": 130.81, "D": 146.83, "E": 164.81, "F": 174.61, "G": 196.00, "A": 220.00, "B": 246.94}

TRACKS = {  # name: (chords as note lists, seconds per chord)
    "soft_pad_cmaj": ([["C", "E", "G"], ["A", "C", "E"], ["F", "A", "C"], ["G", "B", "D"]], 3.0),
    "warm_pad_fmaj": ([["F", "A", "C"], ["C", "E", "G"], ["D", "F", "A"], ["A", "C", "E"]], 3.0),
    "light_pad_gmaj": ([["G", "B", "D"], ["E", "G", "B"], ["C", "E", "G"], ["D", "F", "A"]], 2.5),
    "calm_pad_amin": ([["A", "C", "E"], ["F", "A", "C"], ["C", "E", "G"], ["G", "B", "D"]], 3.5),
}


def chord_expr(notes):
    parts = []
    for name in notes:
        f = N[name]
        # two slightly detuned sines per note = soft chorus; plus one octave up, quieter
        parts.append("sin(2*PI*{0:.2f}*t)+sin(2*PI*{1:.2f}*t)+0.35*sin(2*PI*{2:.2f}*t)".format(
            f, f * 1.003, f * 2))
    return "(" + "+".join(parts) + ")"


def track_expr(chords, d):
    cycle = d * len(chords)
    sel = "0"
    for i in reversed(range(len(chords))):
        sel = "if(lt(mod(t,{c}),{edge}),{ch},{rest})".format(
            c=cycle, edge=d * (i + 1), ch=chord_expr(chords[i]), rest=sel)
    env = "(0.55-0.45*cos(2*PI*mod(t,{d})/{d}))".format(d=d)  # gentle swell per chord
    bass = "0.6*sin(2*PI*{f:.2f}*t)".format(f=N[chords[0][0]] / 2)
    return "0.035*{env}*({sel})+0.02*{bass}".format(env=env, sel=sel, bass=bass)


def main():
    ff = os.environ.get("FFMPEG") or shutil.which("ffmpeg")
    if not ff:
        raise SystemExit("ffmpeg not found")
    os.makedirs(OUT, exist_ok=True)
    for name, (chords, d) in TRACKS.items():
        out = os.path.join(OUT, name + ".m4a")
        expr = track_expr(chords, d)
        subprocess.run([ff, "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                        "aevalsrc='{0}':s=44100:d={1}".format(expr, SECONDS),
                        "-af", "lowpass=f=2200,aecho=0.8:0.6:120|240:0.25|0.15,"
                               "afade=t=in:d=1.5,afade=t=out:st={0}:d=2,loudnorm=I=-24".format(SECONDS - 2),
                        "-ac", "2", "-c:a", "aac", "-b:a", "96k", out], check=True)
        print("wrote", out)


if __name__ == "__main__":
    main()
