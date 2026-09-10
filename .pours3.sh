#!/bin/bash
cd /home/david/pcb
exec >> .pours.log 2>&1
for R in 1 2 3; do
  echo "=== pour ROUND $R $(date +%H:%M:%S)"
  bash .pours.sh </dev/null >/dev/null 2>&1
  U=$(grep -cE '^\[unconnected' .pours.rpt)
  echo "ROUND $R END unconnected=$U"
  git add -A >/dev/null 2>&1; git commit -q -m "pour round $R: unconnected=$U" >/dev/null 2>&1
done
echo POUR_ROUNDS_DONE
