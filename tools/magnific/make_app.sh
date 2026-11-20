#!/bin/bash
# Makes "Magnific Batch.app" on the Desktop: double-click it after downloading images from
# Firefly. It runs autobatch.sh in a Terminal window so you can watch the progress.
DIR="$(cd "$(dirname "$0")" && pwd)"
APP="$HOME/Desktop/Magnific Batch.app"
chmod +x "$DIR/autobatch.sh" "$DIR/run.sh"
/usr/bin/osacompile -o "$APP" -e "tell application \"Terminal\"
  activate
  do script quoted form of \"$DIR/autobatch.sh\"
end tell"
echo "Made: $APP"
