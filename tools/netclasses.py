#!/usr/bin/env python3
"""Apply the project's net classes and their net patterns, then PROVE they
survive a kicad-cli round trip.

Why this is a tool and not a one-off edit: hand-written class dicts were
silently discarded by KiCad. Any class missing a field KiCad 10 expects
(`bus_width`, `priority`, `tuning_profile`) or written with the wrong
`meta.version` is dropped on the next load-and-save, and kicad-cli re-saves the
project on every erc/drc/render run. The whole set went back to just "Default"
without any warning, and the RF/HV/MODEM_BULK rules stopped applying while the
DRC still looked like it was passing them. The verify step at the end exists so
that failure mode can never be silent again.

Run:  python3 tools/netclasses.py
"""
import json
import os
import subprocess
import sys

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRO = os.path.join(PROJ, "telematics-tracker.kicad_pro")
PCB = os.path.join(PROJ, "telematics-tracker.kicad_pcb")

# Nets at up to 100 V. VIN_SENSE / IGN_SENSE are deliberately NOT here: they
# are the divider OUTPUTS into the ADC and sit at a few volts.
HV = ["VIN", "/power/VIN_F", "/power/VIN_P", "/power/VIN_B",
      "/io/VIN_D0", "/io/VIN_D1", "/io/DO1_OUT", "/io/DO2_OUT",
      "/io/IGN", "/io/IGN_D0", "/io/IGN_D1",
      "/io/DI1_IN", "/io/DI1_M1", "/io/DI1_M2", "/io/DI1_LED",
      "/io/DI2_IN", "/io/DI2_M1", "/io/DI2_M2", "/io/DI2_LED",
      "/io/J1_SPARE1", "/io/J1_SPARE2"]
RF = ["/modem_rf/ANT_GNSS_M", "/modem_rf/ANT_GNSS_C",
      "/modem_rf/ANT_MAIN_M", "/modem_rf/ANT_MAIN_C"]
PWR = ["5V0", "SYS", "3V3", "/mcu/3V3A", "/modem_rf/VDD_EXT_1V8"]
BULK = ["/modem_rf/VBAT_MODEM"]

# (name, priority, clearance, track, via_dia, via_drill)
# Lower priority number wins; Default keeps KiCad's sentinel 2147483647.
CLASSES = [
    # 50 ohm CPWG on JLC7628 L1-L2: W = 0.40, G = 0.30 (see design-log).
    ("RF",         0, 0.30, 0.40, 0.60, 0.30),
    # 0.60 mm is IPC-2221 table 6-1, external uncoated, at 100 V. The 1.5 mm
    # HV-to-signal separation is a custom rule in telematics-tracker.kicad_dru
    # because it must except GND.
    ("HV",         1, 0.60, 0.50, 0.80, 0.40),
    # handoff section 4: VBAT_MODEM carries the 2 A transmit burst, >= 2 mm.
    ("MODEM_BULK", 2, 0.20, 2.00, 0.80, 0.40),
    ("PWR",        3, 0.20, 0.50, 0.80, 0.40),
    # GND gets its own class purely so the HV rule can name it as an exception.
    ("GND",        4, 0.15, 0.50, 0.60, 0.30),
]


def cls(name, priority, clearance, track, vd, vdr):
    return {
        "bus_width": 12,
        "clearance": clearance,
        "diff_pair_gap": 0.25,
        "diff_pair_via_gap": 0.25,
        "diff_pair_width": 0.2,
        "line_style": 0,
        "microvia_diameter": 0.3,
        "microvia_drill": 0.1,
        "name": name,
        "pcb_color": "rgba(0, 0, 0, 0.000)",
        "priority": priority,
        "schematic_color": "rgba(0, 0, 0, 0.000)",
        "track_width": track,
        "tuning_profile": "",
        "via_diameter": vd,
        "via_drill": vdr,
        "wire_width": 6,
    }


def apply():
    d = json.load(open(PRO))
    ns = d["net_settings"]
    default = [c for c in ns["classes"] if c["name"] == "Default"]
    ns["classes"] = default + [cls(*c) for c in CLASSES]
    ns["netclass_patterns"] = (
        [{"netclass": "RF", "pattern": p} for p in RF] +
        [{"netclass": "HV", "pattern": p} for p in HV] +
        [{"netclass": "MODEM_BULK", "pattern": p} for p in BULK] +
        [{"netclass": "PWR", "pattern": p} for p in PWR] +
        [{"netclass": "GND", "pattern": "GND"}]
    )
    ns["meta"] = {"version": 5}
    json.dump(d, open(PRO, "w"), indent=2)
    print(f"wrote {len(ns['classes'])} classes, "
          f"{len(ns['netclass_patterns'])} patterns")


def verify():
    """Force KiCad to load and re-save the project, then re-read it."""
    subprocess.run(["kicad-cli", "pcb", "drc", "--output", os.devnull, PCB],
                   capture_output=True)
    d = json.load(open(PRO))
    ns = d["net_settings"]
    names = [c["name"] for c in ns["classes"]]
    pats = ns.get("netclass_patterns") or []
    want = {"Default"} | {c[0] for c in CLASSES}
    ok = set(names) == want and len(pats) == len(RF) + len(HV) + len(BULK) + len(PWR) + 1
    print(f"after kicad round trip: classes={names}")
    print(f"                        patterns={len(pats)}")
    if not ok:
        print("FAILED: KiCad discarded net class data - schema mismatch")
        return 1
    print("VERIFIED: net classes and patterns survive a KiCad round trip")
    return 0


if __name__ == "__main__":
    apply()
    sys.exit(verify())
