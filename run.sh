#!/usr/bin/env bash
# Start TokenMax Hub in the background (idempotent).
cd "$(dirname "$0")"
PORT=${HUB_PORT:-4646}
if curl -fs "http://127.0.0.1:$PORT/api/health" >/dev/null 2>&1; then
  echo "TokenMax Hub already running: http://127.0.0.1:$PORT"; exit 0
fi
mkdir -p data
setsid nohup python3 server.py > data/server.log 2>&1 &
for i in $(seq 1 20); do curl -fs "http://127.0.0.1:$PORT/api/health" >/dev/null 2>&1 && break; sleep 0.3; done
echo "TokenMax Hub started (pid $!): http://127.0.0.1:$PORT"
