#!/usr/bin/env bash
# Capture 1440x900 screenshots of each hub tab (live server on :4646, plus the offline bundle index if present).
set -euo pipefail
cd "$(dirname "$0")"
PORT="${HUB_PORT:-4646}"
CHROME="$(command -v google-chrome || command -v chromium || command -v chromium-browser)"
mkdir -p screenshots
shot() { # url out
  local prof; prof="$(mktemp -d /tmp/hubshot.XXXX)"
  "$CHROME" --headless=new --no-sandbox --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
    --window-size=1440,900 --virtual-time-budget=5000 --user-data-dir="$prof" --screenshot="$2" "$1" >/dev/null 2>&1
  rm -rf "$prof"; echo "  $2"
}
shot "http://127.0.0.1:$PORT/?tab=projects" screenshots/01-projects.png
shot "http://127.0.0.1:$PORT/?tab=story"    screenshots/02-tonights-build.png
shot "http://127.0.0.1:$PORT/?tab=bots"     screenshots/03-bot-launcher.png
if [ -f dist/bundle-preview/TokenMax-Oct7-build/index.html ]; then
  shot "file://$PWD/dist/bundle-preview/TokenMax-Oct7-build/index.html?tab=projects" screenshots/04-offline-bundle.png
fi
