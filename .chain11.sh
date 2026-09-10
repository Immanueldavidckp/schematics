#!/bin/bash
# hybrid v11: cycles-only continuation on the current board state.
# Changes vs v9: DSN keepout injection (edge strips + HV/MV halos), stale-ses
# guard in pcbroute_auto, LV wall-clock deadline (outer timeout unreliable).
cd /home/david/pcb
exec 9>/home/david/pcb/.chain9.lock
flock -n 9 || { echo "another chain instance holds the lock - exiting"; exit 7; }
exec >> /home/david/pcb/.chain9.log 2>&1
echo "=== chain v12 start $(date)"
export _JAVA_OPTIONS="-Xmx1500m"
for CY in 1 2 3 4; do
  echo "=== V12 CYCLE $CY $(date +%H:%M)"
  FR_PASSES=8 PYTHONPATH=tools timeout 6600 python3 -u tools/pcbroute_auto.py $HOME/.cache/pcb-tools/freerouting-1.9.0.jar 90 2>/dev/null | grep -E 'injected|session|no .ses|budget'
  PYTHONPATH=tools timeout 1800 python3 -u tools/pcbroute_adopt.py 2>/dev/null | grep -E 'ADOPT|ripping'
  LV_DEADLINE_S=10800 LV_DEBUG=1 PYTHONUNBUFFERED=1 PYTHONPATH=tools timeout 14400 python3 -u tools/pcbroute_lv.py 2>/dev/null | grep -E '^ROUTED|BATCH FAIL|LV_DEADLINE'
  kicad-cli pcb drc --severity-error -o /home/david/pcb/.v12cy$CY.rpt telematics-tracker.kicad_pcb >/dev/null 2>&1
  U=$(grep -cE '^\[unconnected' /home/david/pcb/.v12cy$CY.rpt)
  E=$(grep -E '^\[' /home/david/pcb/.v12cy$CY.rpt | grep -vc unconnected)
  echo "V12 CYCLE $CY END: unconnected=$U errors=$E"
  git add -A >/dev/null 2>&1; git commit -q -m "hybrid v12 cycle $CY: unconnected=$U errors=$E" >/dev/null 2>&1
  if [ "$U" -eq 0 ]; then echo ALL_CONNECTED
    PYTHONPATH=tools timeout 3600 python3 -u tools/deliverables.py 2>/dev/null
    git add -A >/dev/null 2>&1; git commit -q -m "Milestone 4 deliverables" >/dev/null 2>&1
    break
  fi
done
echo CHAIN12_DONE
