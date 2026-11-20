#!/bin/bash
# Usage: tools/magnific/run.sh <image-folder> [--model-name Midjourney] [--check-only]
DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$DIR/.venv"
if [ ! -x "$VENV/bin/python" ]; then
  echo "First run: setting up (Pillow)..."
  python3 -m venv "$VENV" && "$VENV/bin/pip" -q install Pillow || exit 1
fi
exec "$VENV/bin/python" -I "$DIR/magnific_meta.py" "$@"
