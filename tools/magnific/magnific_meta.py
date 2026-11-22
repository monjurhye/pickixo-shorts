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

Uses Google's free Gemini API (no OpenAI). The key is read from the GEMINI_API_KEY
environment variable or the macOS Keychain item "pickixo-gemini" (never printed).
Free tier: a few hundred images a day, about 10 a minute (the tool paces itself).
"""

import argparse
import base64
import csv
import io
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

from PIL import Image

EXTS = (".jpg", ".jpeg", ".png")
MIN_QUALITY = 7                 # AI quality score needed to go into the CSV
MIN_SHARPNESS = 2.5             # edge energy below this looks soft at 100% (rough guide; tune after a few batches)
MIN_SHORT = 2000                # Magnific rejects "Min dimensions not reached" below this
MIN_PIXELS = 4_000_000          # ~2000x2000; smaller files are usually rejected
DUP_DISTANCE = 6                # dHash bits; lower = more similar
MODEL = os.environ.get("MAGNIFIC_MODEL", "gemini-flash-lite-latest")
GAP = 6.5                       # seconds between AI calls: stays under the free tier's ~10 a minute
AI_TAG = "_ai_generated"
# Column names: compare with the CSV template on Magnific's Upload page and edit if different.
HEADER = ["filename", "title", "keywords", "prompt", "model"]   # names the Magnific panel checks for

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
        "quality": {"type": "integer"},
        "quality_notes": {"type": "string"},
    },
    "required": ["title", "keywords", "category", "problems", "quality", "quality_notes"],
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
  heavy artifacts, flat low-detail texture. Empty list if none.
- quality: 1-10, judged like a strict stock reviewer. The SECOND image is a 100% crop
  from the centre of the full-size file: judge real detail there. Score 7+ only if
  textures look natural (no plastic/waxy surfaces, no smeared or melted details, no
  over-sharpened halos, no upscaling artifacts), light and composition are professional,
  and nothing looks AI-broken. 5-6 = likely "Low quality" rejection. 1-4 = clearly reject.
- quality_notes: one short sentence on the main weakness (or "clean")."""


def api_key():
    k = os.environ.get("GEMINI_API_KEY", "").strip()
    if k:
        return k
    try:
        return subprocess.run(["security", "find-generic-password", "-s", "pickixo-gemini", "-w"],
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return ""


UPSCAYL_DIRS = ["/Applications/Upscayl.app/Contents/Resources",
                os.path.expanduser("~/Applications/Upscayl.app/Contents/Resources")]
# realistic models first; "digital art" style models make photos look plastic
UPSCAYL_MODELS = ["high-fidelity-4x", "upscayl-standard-4x", "realesrgan-x4plus", "remacri-4x"]
TARGET_SHORT = 2048             # final short side after supersampling


def upscayl():
    """(binary, models_dir, model) from an installed Upscayl app, or None."""
    for base in UPSCAYL_DIRS:
        b, m = os.path.join(base, "bin", "upscayl-bin"), os.path.join(base, "models")
        if os.path.isfile(b) and os.path.isdir(m):
            have = {f[:-6] for f in os.listdir(m) if f.endswith(".param")}
            model = next((x for x in UPSCAYL_MODELS if x in have), None) or (sorted(have)[0] if have else None)
            if model:
                return b, m, model
    return None


def supersample(path, ups):
    """Upscale 4x with Upscayl, then shrink so the short side is 2048 px (cleaner than a
    straight 2x). Writes <name>_up.jpg next to the original; returns that path."""
    import tempfile
    stem = os.path.splitext(path)[0]
    out = stem + "_up.jpg"
    if os.path.exists(out):
        return out
    b, models, model = ups
    with tempfile.TemporaryDirectory() as td:
        tmp = os.path.join(td, "x4.png")
        r = subprocess.run([b, "-i", path, "-o", tmp, "-s", "4", "-m", models, "-n", model, "-f", "png"],
                           capture_output=True, text=True)
        if r.returncode != 0 or not os.path.exists(tmp):
            raise RuntimeError("Upscayl failed: " + (r.stderr or r.stdout)[-300:])
        big = Image.open(tmp).convert("RGB")
        w, h = big.size
        k = TARGET_SHORT / float(min(w, h))
        if k < 1:
            big = big.resize((round(w * k), round(h * k)), Image.LANCZOS)
        big.save(out, "JPEG", quality=95, subsampling=0)
    return out


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


def crop_jpeg(img):
    """1024x1024 crop at full resolution from the centre (what a reviewer sees at 100%)."""
    im = img.convert("RGB")
    w, h = im.size
    s = min(1024, w, h)
    box = ((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s)
    buf = io.BytesIO()
    im.crop(box).save(buf, "JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode()


def sharpness(img):
    """Edge energy of a full-resolution centre crop; very low = soft/blurry."""
    from PIL import ImageFilter, ImageStat
    g = img.convert("L")
    w, h = g.size
    s = min(1024, w, h)
    c = g.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s))
    return ImageStat.Stat(c.filter(ImageFilter.FIND_EDGES)).mean[0]


def _gemini_schema(x):
    """JSON Schema -> the schema form Gemini accepts (no additionalProperties)."""
    if isinstance(x, dict):
        return {k: _gemini_schema(v) for k, v in x.items() if k != "additionalProperties"}
    if isinstance(x, list):
        return [_gemini_schema(v) for v in x]
    return x


_LAST = [0.0]


def describe(key, b64, crop_b64):
    body = {
        "systemInstruction": {"parts": [{"text": INSTRUCTIONS}]},
        "contents": [{"role": "user", "parts": [
            {"text": "Write the metadata for this image. First image: whole picture (reduced). "
                     "Second image: 100% centre crop."},
            {"inline_data": {"mime_type": "image/jpeg", "data": b64}},
            {"inline_data": {"mime_type": "image/jpeg", "data": crop_b64}}]}],
        "generationConfig": {"responseMimeType": "application/json",
                             "responseSchema": _gemini_schema(SCHEMA), "maxOutputTokens": 4000},
    }
    url = "https://generativelanguage.googleapis.com/v1beta/models/{0}:generateContent".format(MODEL)
    for attempt in range(4):
        wait = GAP - (time.time() - _LAST[0])
        if wait > 0:
            time.sleep(wait)
        _LAST[0] = time.time()
        req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                     headers={"x-goog-api-key": key, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                data = json.loads(r.read().decode())
            break
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "ignore")[:200]
            if e.code in (429, 503) and attempt < 3:   # free-tier minute limit / busy: wait and retry
                time.sleep(30 * (attempt + 1))
                continue
            raise RuntimeError("Gemini HTTP {0}: {1}".format(e.code, msg))
    text = "".join(p.get("text", "") for c in (data.get("candidates") or [])[:1]
                   for p in (c.get("content") or {}).get("parts") or [])
    if not text.strip():
        raise RuntimeError("empty AI reply ({0})".format(
            ((data.get("candidates") or [{}])[0]).get("finishReason") or data.get("promptFeedback") or "no text"))
    return json.loads(text)


def clean_keywords(words):
    out, seen = [], set()
    for w in words:
        w = " ".join(str(w).lower().replace(";", " ").replace(",", " ").split())
        if w and w not in seen:
            seen.add(w)
            out.append(w)
    out = [w for w in out if w != AI_TAG][:44]   # 45 with the AI tag (50 exactly was not imported)
    return out + [AI_TAG]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--model-name", default="", help="generator you used, e.g. Midjourney (for the Model column)")
    ap.add_argument("--check-only", action="store_true", help="only size/duplicate checks, no AI calls")
    ap.add_argument("--no-upscale", action="store_true", help=argparse.SUPPRESS)  # old flag, now the default
    ap.add_argument("--upscale", action="store_true", help="AI-upscale small images with Upscayl (slow on this Mac)")
    args = ap.parse_args()

    folder = os.path.expanduser(args.folder)
    if not os.path.isdir(folder):
        os.makedirs(folder)
        subprocess.run(["open", folder])
        sys.exit("Created the folder " + folder + " (opened in Finder).\n"
                 "Put your images (.jpg/.png) in it, then run the same command again.")
    files = sorted(f for f in os.listdir(folder)
                   if f.lower().endswith(EXTS) and not f.lower().endswith(("_up.jpg", "_2048.jpg")))
    if not files:
        subprocess.run(["open", folder])
        sys.exit("No .jpg/.png files in " + folder + " (opened in Finder). Add images and run again.")
    key = "" if args.check_only else api_key()
    if not args.check_only and not key:
        sys.exit("No Gemini key. Get a free one at https://aistudio.google.com/apikey, then save it once with:\n"
                 "  security add-generic-password -s pickixo-gemini -a gemini -w\n"
                 "(it asks for the key; paste it there, not in chat)")

    ups = upscayl() if args.upscale else None
    if args.upscale and not ups:
        print("Upscayl not found in Applications: small images will be skipped, not upscaled.\n"
              "Install it from https://upscayl.org to upscale automatically.\n")
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
        small = w * h < MIN_PIXELS or min(w, h) < MIN_SHORT
        if small and not ups and TARGET_SHORT / float(min(w, h)) <= 1.3:
            # small gap (e.g. 1792 -> 2048): a quick high-quality resize, no AI upscaler
            k = TARGET_SHORT / float(min(w, h))
            out_path = os.path.splitext(path)[0] + "_2048.jpg"
            img.convert("RGB").resize((round(w * k), round(h * k)), Image.LANCZOS).save(
                out_path, "JPEG", quality=95, subsampling=0)
            path, name = out_path, os.path.basename(out_path)
            img = Image.open(path)
            img.load()
            w, h = img.size
            report.append((name, "resized from the original; upload THIS file"))
        elif small and ups and min(w, h) >= 512:
            try:
                print("[{0}/{1}] {2} is {3}x{4}, upscaling (4x then down to 2048)...".format(i, len(files), name, w, h))
                path = supersample(path, ups)
                name = os.path.basename(path)
                img = Image.open(path)
                img.load()
                w, h = img.size
                report.append((name, "made by upscaling the original; upload THIS file, not the original"))
            except Exception as e:
                report.append((name, "upscale failed: {0}".format(e)))
                continue
        if w * h < MIN_PIXELS or min(w, h) < MIN_SHORT:
            report.append((name, "too small ({0}x{1}, short side must be 2000+); make it bigger at the source (Firefly ~2048px) "
                                 "or install Upscayl so the tool can upscale it".format(w, h)))
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
        sharp = sharpness(img)
        try:
            try:
                meta = describe(key, preview_jpeg(img), crop_jpeg(img))
            except RuntimeError:
                meta = describe(key, preview_jpeg(img), crop_jpeg(img))   # one retry
        except Exception as e:
            report.append((name, "AI error: {0}".format(e)))
            continue
        q = int(meta.get("quality", 0))
        if q < MIN_QUALITY or sharp < MIN_SHARPNESS:
            report.append((name, "NOT in CSV, likely 'Low quality' (score {0}/10, sharpness {1:.1f}): {2}{3}".format(
                q, sharp, meta.get("quality_notes", ""),
                "; problems: " + "; ".join(meta["problems"]) if meta.get("problems") else "")))
            print("[{0}/{1}] {2} -> low quality {3}/10, skipped".format(i, len(files), name, q))
            continue
        if meta.get("problems"):
            report.append((name, "in CSV but check: " + "; ".join(meta["problems"])))
        rows.append([name, meta["title"].strip().rstrip("."), ",".join(clean_keywords(meta["keywords"])),
                     "", args.model_name])
        print("[{0}/{1}] {2} -> {3} ({4}, quality {5}/10)".format(i, len(files), name, meta["title"],
                                                               meta["category"], q))

    # Magnific's photo upload takes JPG only: write JPG copies + a CSV that names them.
    if rows:
        jdir = os.path.join(folder, "upload_jpg")
        os.makedirs(jdir, exist_ok=True)
        for r in rows:
            src = os.path.join(folder, r[0])
            jname = os.path.splitext(r[0])[0] + ".jpg"
            if src.lower().endswith((".jpg", ".jpeg")):
                import shutil
                shutil.copy2(src, os.path.join(jdir, jname))
            else:
                Image.open(src).convert("RGB").save(os.path.join(jdir, jname), "JPEG", quality=95, subsampling=0)
            r[0] = jname
        out = os.path.join(jdir, "magnific_metadata.csv")
        with open(out, "w", newline="", encoding="utf-8") as f:
            wr = csv.writer(f, delimiter=";")
            wr.writerow(HEADER)
            wr.writerows(rows)
        print("\nUpload these JPGs + this CSV: " + jdir)
    rep = os.path.join(folder, "magnific_report.txt")
    with open(rep, "w", encoding="utf-8") as f:
        for n, why in report:
            f.write("{0}: {1}\n".format(n, why))
    print("{0} ready, {1} need a look -> {2}".format(len(rows), len(report), rep))


if __name__ == "__main__":
    main()
