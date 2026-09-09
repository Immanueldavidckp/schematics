#!/bin/bash
# Safe manual enforcement of the LV cap for chain cycle 2 (outer timeout
# failed to fire). Sequence: freeze the parent so it cannot spawn or reap,
# let the in-flight child finish its net and save (single-writer preserved),
# then kill parent+timeout by explicit PID. The chain's bash then proceeds
# to the cycle-end DRC/commit and cycle 3.
set -u
TP=2273756   # timeout 25000
PP=2273758   # python3 -u tools/pcbroute_lv.py (orchestrator)
kill -STOP "$PP" "$TP" 2>/dev/null
for i in $(seq 1 240); do
  pgrep -f 'pcbroute_lv.py --' >/dev/null || break
  sleep 5
done
kill -TERM "$PP" "$TP" 2>/dev/null
sleep 3
kill -CONT "$PP" "$TP" 2>/dev/null
sleep 2
kill -KILL "$PP" "$TP" 2>/dev/null
echo "LV_KILLED $(date +%H:%M:%S)"
