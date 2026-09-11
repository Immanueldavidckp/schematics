#!/bin/bash
# Land the four power pours ONE AT A TIME with an individual DRC gate each -
# batched together they share one gate and a single violation kept discarding
# all four (measured 3x). Same rules, same gate, batch size 1.
cd /home/david/pcb
exec >> .pours.log 2>&1
echo "=== pours start $(date +%H:%M:%S)"
cp telematics-tracker.kicad_pcb .pours.base
for N in 3V3 5V0 /power/SYS GND; do
  echo "--- $N $(date +%H:%M:%S)"
  LV_DEBUG=1 PYTHONUNBUFFERED=1 PYTHONPATH=tools timeout 5400 \
    python3 -u tools/pcbroute_lv.py --net "$N" 2>/dev/null | \
    grep -E 'CHILD_|island taps'
  kicad-cli pcb drc --severity-error -o .pours.rpt telematics-tracker.kicad_pcb >/dev/null 2>&1
  E=$(grep -E '^\[' .pours.rpt | grep -vc unconnected)
  U=$(grep -cE '^\[unconnected' .pours.rpt)
  echo "POUR $N: unconnected=$U errors=$E"
  if [ "$E" -gt 0 ]; then
    echo "POUR $N fouled - scrubbing the violating fragments"
    PYTHONPATH=tools python3 tools/scrub_fouls.py 2>/dev/null | grep SCRUB
    kicad-cli pcb drc --severity-error -o .pours.rpt telematics-tracker.kicad_pcb >/dev/null 2>&1
    E2=$(grep -E '^\[' .pours.rpt | grep -vc unconnected)
    U2=$(grep -cE '^\[unconnected' .pours.rpt)
    echo "POUR $N after scrub: unconnected=$U2 errors=$E2"
    if [ "$E2" -gt 0 ]; then
      echo "POUR $N still fouled - reverting"
      cp .pours.base telematics-tracker.kicad_pcb
    else
      cp telematics-tracker.kicad_pcb .pours.base
    fi
  else
    cp telematics-tracker.kicad_pcb .pours.base
  fi
done
echo POURS_DONE
