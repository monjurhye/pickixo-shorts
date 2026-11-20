#!/bin/bash
# One-click Magnific batch (free): collects the AI images you downloaded, checks them,
# writes titles/keywords/CSV, and opens the upload folder + Magnific's upload page.
#
#   tools/magnific/autobatch.sh            # takes Firefly*.jpg/png from ~/Downloads
#   tools/magnific/autobatch.sh ~/Pictures # another source folder
#
# Started by the "Magnific Batch" app on the Desktop (tools/magnific/make_app.sh).
# Files still downloading (changed in the last 20 seconds) are left for the next run.

SRC="${1:-$HOME/Downloads}"
ROOT="$HOME/Desktop/Magnific"
DIR="$(cd "$(dirname "$0")" && pwd)"
STAMP="$(date +%Y-%m-%d_%H%M)"
BATCH="$ROOT/$STAMP"

notify() { /usr/bin/osascript -e "display notification \"$1\" with title \"Magnific Batch\"" >/dev/null 2>&1; }

mkdir -p "$ROOT"
# Firefly names its downloads "Firefly ...". Add more patterns here if you use other free tools.
FILES=()
while IFS= read -r -d '' f; do FILES+=("$f"); done < <(
  find "$SRC" -maxdepth 1 -type f \( -iname 'firefly*.jpg' -o -iname 'firefly*.jpeg' -o -iname 'firefly*.png' \
       -o -iname 'adobe firefly*.jpg' -o -iname 'adobe firefly*.png' \) -mtime -14d -mtime +20s -print0)

if [ ${#FILES[@]} -eq 0 ]; then
  notify "No Firefly images found in $(basename "$SRC"). Download your images first."
  echo "No Firefly images in $SRC"
  exit 0
fi

mkdir -p "$BATCH"
for f in "${FILES[@]}"; do mv -n "$f" "$BATCH/"; done
notify "${#FILES[@]} images found. Checking quality and writing titles + keywords..."
echo "Batch: $BATCH (${#FILES[@]} images)"

"$DIR/run.sh" "$BATCH" --model-name "Adobe Firefly" $MAGNIFIC_EXTRA 2>&1 | tee "$BATCH/run_log.txt"

UP="$BATCH/upload_jpg"
N=$(ls "$UP" 2>/dev/null | grep -ci '\.jpg$')
if [ "${N:-0}" -gt 0 ]; then
  notify "$N images ready to upload. Folder and Magnific upload page are opening."
  open "$UP"
  open "https://contributor.magnific.com/dashboard"
else
  notify "No image passed the checks. See magnific_report.txt in the batch folder."
  open "$BATCH"
fi
