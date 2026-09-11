#!/bin/bash
# v13: FULL regeneration with relief-round-2 placement, then hybrid cycles.
cd /home/david/pcb
exec 9>/home/david/pcb/.chain9.lock
flock -n 9 || { echo "another chain instance holds the lock - exiting"; exit 7; }
exec >> /home/david/pcb/.chain9.log 2>&1
echo "=== chain v13 start $(date)"
timeout 300 python3 tools/build.py 2>&1 | grep -E 'NOT converge|UNPLACED'
PYTHONPATH=tools timeout 200 python3 tools/pcbroute.py >/dev/null 2>&1
PYTHONPATH=tools timeout 2400 python3 tools/pcbroute_hv.py 2>/dev/null | grep -E 'routed:|UNROUTED'
kicad-cli pcb drc --severity-error -o /dev/null telematics-tracker.kicad_pcb 2>&1 | grep 'Found.*violations' | head -1
echo PRE_AUTO_MARK
git add -A >/dev/null 2>&1; git commit -q -m "v13 regen: relief placement + RF + HV" >/dev/null 2>&1
export _JAVA_OPTIONS="-Xmx1500m"
for CY in 1 2 3 4; do
  echo "=== V13 CYCLE $CY $(date +%H:%M)"
  FR_PASSES=8 PYTHONPATH=tools timeout 6600 python3 -u tools/pcbroute_auto.py $HOME/.cache/pcb-tools/freerouting-1.9.0.jar 90 2>/dev/null | grep -E 'injected|session|no .ses|budget'
  PYTHONPATH=tools timeout 1800 python3 -u tools/pcbroute_adopt.py 2>/dev/null | grep -E 'ADOPT|ripping'
  LV_DEADLINE_S=10800 LV_DEBUG=1 PYTHONUNBUFFERED=1 PYTHONPATH=tools timeout 14400 python3 -u tools/pcbroute_lv.py 2>/dev/null | grep -E '^ROUTED|BATCH FAIL|LV_DEADLINE'
  kicad-cli pcb drc --severity-error -o /home/david/pcb/.v13cy$CY.rpt telematics-tracker.kicad_pcb >/dev/null 2>&1
  U=$(grep -cE '^\[unconnected' /home/david/pcb/.v13cy$CY.rpt)
  E=$(grep -E '^\[' /home/david/pcb/.v13cy$CY.rpt | grep -vc unconnected)
  echo "V13 CYCLE $CY END: unconnected=$U errors=$E"
  git add -A >/dev/null 2>&1; git commit -q -m "hybrid v13 cycle $CY: unconnected=$U errors=$E" >/dev/null 2>&1
  if [ "$U" -eq 0 ]; then echo ALL_CONNECTED
    PYTHONPATH=tools timeout 3600 python3 -u tools/deliverables.py 2>/dev/null
    git add -A >/dev/null 2>&1; git commit -q -m "Milestone 4 deliverables" >/dev/null 2>&1
    break
  fi
done
echo CHAIN13_DONE
