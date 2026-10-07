#!/usr/bin/env bash
# Stop TokenMax Hub server(s) whose working dir is this folder (leaves other projects' servers alone).
cd "$(dirname "$0")"; HERE="$PWD"
for p in $(pgrep -x python3); do
  [ "$(readlink /proc/$p/cwd)" = "$HERE" ] && tr '\0' ' ' < /proc/$p/cmdline | grep -q "server.py" && kill "$p" && echo "stopped $p"
done; true
