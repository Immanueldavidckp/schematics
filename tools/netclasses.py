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

# HV: the CONNECTOR-SIDE nets - the ones exposed to harness transients and
# contamination, which is what the 1.5 mm defence-in-depth separation is for.
# VIN_SENSE / IGN_SENSE are deliberately NOT here: they are the divider
# OUTPUTS into the ADC and sit at a few volts.
HV = ["VIN", "/power/VIN_F", "/power/VIN_P", "/power/VIN_B",
      "/io/DO1_OUT", "/io/DO2_OUT", "/io/IGN",
      "/io/DI1_IN", "/io/DI2_IN",
      "/io/J1_SPARE1", "/io/J1_SPARE2",
      # The buck switching node swings between GND and VIN on every cycle, so
      # it is a 100 V net with fast edges - it was sitting in Default (0.20 mm
      # track, 0.15 mm clearance). Found because the HV maze router treated it
      # as LV and walled U5's own VIN pins off behind a 1.50 mm halo, making
      # /power/VIN_B unroutable (0/4). U5_VB is the bootstrap, referenced to
      # SW_BUCK, so it rides to VIN + VCC and is HV for the same reason. Both
      # live inside the BUCK_HV rescope area (0.60 mm to LV, see .kicad_dru).
      "/power/SW_BUCK", "/power/U5_VB"]

# MV: interior chain/divider nodes at <= 70 V. They carry the same current
# path as their HV parents but sit behind series resistance, are not exposed
# to the harness, and the board is conformally coated (F-20, mandatory).
# 0.60 mm clearance = IPC-2221 table 6-1 at 100 V external uncoated - i.e.
# even rated as if they were at the full bus voltage uncoated, they clear.
# Calculated worst-case node voltages at VIN = 100 V:
#   VIN/IGN dividers, 3 x 100k : 9.1k, I = 100/309.1k = 0.324 mA:
#     VIN_D0 = IGN_D0 = 100 - 0.324m x 100k = 67.6 V   (<= 70)
#     VIN_D1 = IGN_D1 = 35.3 V
#   DI chains, 3 x 12k into the EL357N LED (Vf ~ 1.2 V), I = 2.74 mA:
#     DI*_M1  = 100 - 2.74m x 12k = 67.1 V             (<= 70)
#     DI*_M2  = 34.2 V
#     DI*_LED = 1.2 V (clamped by the opto LED + BAV99)
MV = ["/io/VIN_D0", "/io/VIN_D1", "/io/IGN_D0", "/io/IGN_D1",
      "/io/DI1_M1", "/io/DI1_M2", "/io/DI1_LED",
      "/io/DI2_M1", "/io/DI2_M2", "/io/DI2_LED"]
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
    # Interior <= 70 V nodes: electrical clearance only, no 1.5 mm layout rule.
    ("MV",         2, 0.60, 0.20, 0.50, 0.30),
    # handoff section 4: VBAT_MODEM carries the 2 A transmit burst, >= 2 mm.
    ("MODEM_BULK", 3, 0.20, 2.00, 0.80, 0.40),
    ("PWR",        4, 0.20, 0.50, 0.80, 0.40),
    # GND gets its own class purely so the HV rule can name it as an exception.
    ("GND",        5, 0.15, 0.50, 0.60, 0.30),
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


# Board-level minima. KiCad reset min_clearance from 0.15 to 0.0 during one of
# its project round-trips - the same silent-regression class as G2 wiping
# net_settings. A zero minimum clearance means the board-wide floor stops
# existing, so it is asserted here and verified after the round trip.
BOARD_RULES = {
    "min_clearance": 0.15,              # JLCPCB 4-layer floor
    "min_track_width": 0.20,
    "min_via_diameter": 0.50,
    "min_via_annular_width": 0.10,
    "min_through_hole_diameter": 0.30,
    "min_hole_to_hole": 0.50,           # matches the .kicad_dru rule
    "min_copper_edge_clearance": 0.50,
}


def _assert_floors():
    """Every class must meet the board floor: track >= 0.20, annulus >= 0.10."""
    for name, _prio, _clr, track, vd, vdr in CLASSES:
        assert track >= 0.20, f"{name}: track {track} < 0.20 board floor"
        ann = (vd - vdr) / 2
        assert ann >= 0.10 - 1e-9, f"{name}: via annulus {ann:.3f} < 0.10"
    print("all net classes meet the board floors (track >= 0.20, annulus >= 0.10)")


def apply():
    _assert_floors()
    d = json.load(open(PRO))
    rules = d.setdefault("board", {}).setdefault("design_settings", {}) \
             .setdefault("rules", {})
    rules.update(BOARD_RULES)
    ns = d["net_settings"]
    default = [c for c in ns["classes"] if c["name"] == "Default"]
    ns["classes"] = default + [cls(*c) for c in CLASSES]
    ns["netclass_patterns"] = (
        [{"netclass": "RF", "pattern": p} for p in RF] +
        [{"netclass": "HV", "pattern": p} for p in HV] +
        [{"netclass": "MV", "pattern": p} for p in MV] +
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
    ok = set(names) == want and \
        len(pats) == len(RF) + len(HV) + len(MV) + len(BULK) + len(PWR) + 1
    print(f"after kicad round trip: classes={names}")
    print(f"                        patterns={len(pats)}")
    # board minima must survive too
    got = d.get("board", {}).get("design_settings", {}).get("rules", {})
    bad = {k: (v, got.get(k)) for k, v in BOARD_RULES.items()
           if abs(float(got.get(k, -1)) - v) > 1e-9}
    if bad:
        print("FAILED: board minima did not survive:")
        for k, (want_v, got_v) in sorted(bad.items()):
            print(f"    {k}: want {want_v}, got {got_v}")
        return 1
    print(f"                        board minima: {len(BOARD_RULES)} verified "
          f"(min_clearance={got.get('min_clearance')})")
    if not ok:
        print("FAILED: KiCad discarded net class data - schema mismatch")
        return 1
    print("VERIFIED: net classes and patterns survive a KiCad round trip")
    return 0


if __name__ == "__main__":
    apply()
    sys.exit(verify())
