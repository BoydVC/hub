#!/usr/bin/env bash
# One-shot schedule for tonight only: refresh the zip at 5:30, 6:15 and 6:50 PM ET, then exit.
cd /workspace/tokenmax/hub
for t in 17:30 18:15 18:50; do
  target=$(date -d "today $t" +%s); now=$(date +%s)
  [ "$target" -le "$now" ] && continue
  sleep $((target - now))
  echo "=== rebundle $(date '+%-I:%M %p %Z')" >> data/rebundle.log
  ./rebundle.sh >> data/rebundle.log 2>&1
done
echo "=== schedule done $(date '+%-I:%M %p %Z')" >> data/rebundle.log
