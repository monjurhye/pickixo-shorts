"""Magnific (ex-Freepik) contributor helper: check images and write the metadata CSV.

Put your finished AI images in a folder, then:

    tools/magnific/run.sh ~/Desktop/magnific_batch

For every image it:
  1. checks size and finds near-duplicates (Magnific rejects "too similar" files),
  2. asks an AI vision model for a title, 40-50 keywords and a category,
  3. writes magnific_metadata.csv (semicolon separated, keywords comma separated,
     AI tag added) into the same folder, plus a report of skipped files.

Then upload the images on contributor.magnific.com -> Upload, upload the CSV there,
check a few titles, and click Submit yourself. Nothing is uploaded by this tool.

The OpenAI key is read from the OPENAI_API_KEY environment variable or the macOS
Keychain item "pickixo-openai" (never printed). Cost is about $0.001 per image.
"""

import argparse
import base64
import csv
import io
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

from PIL import Image

EXTS = (".jpg", ".jpeg", ".png")
MIN_PIXELS = 4_000_000          # ~2000x2000; smaller files are usually rejected
DUP_DISTANCE = 6                # dHash bits; lower = more similar
MODEL = os.environ.get("MAGNIFIC_MODEL", "gpt-5-nano")
AI_TAG = "_ai_generated"
# Column names: compare with the CSV template on Magnific's Upload page and edit if different.
HEADER = ["Filename", "Title", "Keywords", "Prompt", "Model"]

CATEGORIES = ["Backgrounds", "Business", "Food and drink", "Animals", "Nature", "Holidays",
              "Technology", "People", "Lifestyle", "Interiors", "Education", "Health",
              "Travel", "Sports", "Objects", "Abstract", "Industry", "Beauty and fashion"]

SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "keywords": {"type": "array", "items": {"type": "string"}},
        "category": {"type": "string", "enum": CATEGORIES},
        "problems": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["title", "keywords", "category", "problems"],
    "additionalProperties": False,
}

INSTRUCTIONS = """You write stock-image metadata for Magnific (Freepik) buyers, mostly in the US.
Look at the image and return:
- title: 5 to 12 plain English words describing exactly what is shown. No brand names,
  no "AI", no "stock photo", no keyword stuffing.
- keywords: 40 to 50 single words or short phrases buyers would search, most important
  first: subject, objects, setting, colors, mood, concepts, possible uses (e.g. "background",
  "banner", "copy space" only if true). Lowercase, no brands, no people's names, no duplicates.
- category: the best one from the list.
- problems: anything that would get the image rejected: malformed hands/fingers/faces,
  garbled or fake text, logos or brands, watermarks, a recognizable real person, blur,
  heavy artifacts, flat low-detail texture. Empty list if none."""


def api_key():
    k = os.environ.get("OPENAI_API_KEY", "").strip()
    if k:
        return k
    try:
        return subprocess.run(["security", "find-generic-password", "-s", "pickixo-openai", "-w"],
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return ""


def dhash(img, size=8):
    g = img.convert("L").resize((size + 1, size), Image.LANCZOS)
    px = list(g.getdata())
    bits = 0
    for r in range(size):
        for c in range(size):
            bits = (bits << 1) | (px[r * (size + 1) + c] > px[r * (size + 1) + c + 1])
    return bits


def preview_jpeg(img):
    im = img.convert("RGB")
    im.thumbnail((1024, 1024))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode()


def describe(key, b64):
    body = {
        "model": MODEL,
        "instructions": INSTRUCTIONS,
        "input": [{"role": "user", "content": [
            {"type": "input_text", "text": "Write the metadata for this image."},
            {"type": "input_image", "image_url": "data:image/jpeg;base64," + b64}]}],
        "text": {"format": {"type": "json_schema", "name": "meta", "strict": True, "schema": SCHEMA}},
        "max_output_tokens": 3000,
    }
    req = urllib.request.Request("https://api.openai.com/v1/responses", data=json.dumps(body).encode(),
                                 headers={"Authorization": "Bearer " + key,
                                          "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError("OpenAI HTTP {0}: {1}".format(e.code, e.read().decode("utf-8", "ignore")[:200]))
    text = data.get("output_text") or "".join(
        c.get("text", "") for o in data.get("output", []) for c in o.get("content", []) if c.get("type") == "output_text")
    return json.loads(text)


def clean_keywords(words):
    out, seen = [], set()
    for w in words:
        w = " ".join(str(w).lower().replace(";", " ").replace(",", " ").split())
        if w and w not in seen:
            seen.add(w)
            out.append(w)
    out = [w for w in out if w != AI_TAG][:49]
    return out + [AI_TAG]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--model-name", default="", help="generator you used, e.g. Midjourney (for the Model column)")
    ap.add_argument("--check-only", action="store_true", help="only size/duplicate checks, no AI calls")
    args = ap.parse_args()

    folder = os.path.expanduser(args.folder)
    if not os.path.isdir(folder):
        os.makedirs(folder)
        subprocess.run(["open", folder])
        sys.exit("Created the folder " + folder + " (opened in Finder).\n"
                 "Put your images (.jpg/.png) in it, then run the same command again.")
    files = sorted(f for f in os.listdir(folder) if f.lower().endswith(EXTS))
    if not files:
        subprocess.run(["open", folder])
        sys.exit("No .jpg/.png files in " + folder + " (opened in Finder). Add images and run again.")
    key = "" if args.check_only else api_key()
    if not args.check_only and not key:
        sys.exit("No OpenAI key. Save it once with:\n  security add-generic-password -s pickixo-openai -a openai -w\n"
                 "(it asks for the key; paste it there, not in chat)")

    rows, report, hashes = [], [], []
    for i, name in enumerate(files, 1):
        path = os.path.join(folder, name)
        try:
            img = Image.open(path)
            img.load()
        except Exception as e:
            report.append((name, "cannot open: {0}".format(e)))
            continue
        w, h = img.size
        if w * h < MIN_PIXELS:
            report.append((name, "too small ({0}x{1}); make it bigger at the source (Firefly ~2048px) "
                                 "or upscale 2x only and check at 100% zoom".format(w, h)))
            continue
        hsh = dhash(img)
        twin = next((n for n, x in hashes if bin(x ^ hsh).count("1") <= DUP_DISTANCE), None)
        if twin:
            report.append((name, "very similar to " + twin + "; keep only the better one"))
            continue
        hashes.append((name, hsh))
        if args.check_only:
            print("[{0}/{1}] ok {2}".format(i, len(files), name))
            continue
        try:
            meta = describe(key, preview_jpeg(img))
        except Exception as e:
            report.append((name, "AI error: {0}".format(e)))
            continue
        if meta.get("problems"):
            report.append((name, "check before uploading: " + "; ".join(meta["problems"])))
        rows.append([name, meta["title"].strip().rstrip("."), ",".join(clean_keywords(meta["keywords"])),
                     "", args.model_name])
        print("[{0}/{1}] {2} -> {3} ({4})".format(i, len(files), name, meta["title"], meta["category"]))

    if rows:
        out = os.path.join(folder, "magnific_metadata.csv")
        with open(out, "w", newline="", encoding="utf-8") as f:
            wr = csv.writer(f, delimiter=";")
            wr.writerow(HEADER)
            wr.writerows(rows)
        print("\nCSV: " + out)
    rep = os.path.join(folder, "magnific_report.txt")
    with open(rep, "w", encoding="utf-8") as f:
        for n, why in report:
            f.write("{0}: {1}\n".format(n, why))
    print("{0} ready, {1} need a look -> {2}".format(len(rows), len(report), rep))


if __name__ == "__main__":
    main()
