#!/usr/bin/env bash
# Refresh hub screenshots and rebuild the zip so it includes whatever exists right now.
cd "$(dirname "$0")"
./run.sh >/dev/null
./screenshot.sh >/dev/null 2>&1
python3 bundle.py
./screenshot.sh >/dev/null 2>&1   # 04-offline-bundle reflects the fresh bundle
python3 bundle.py >/dev/null      # ...and the zip carries that fresh 04 screenshot
