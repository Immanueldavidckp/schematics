#!/usr/bin/env python3
"""Apply the 3V3 pocket fingers (POWER_POURS additions) to the LIVE board.

Regeneration would rip all routing, so the two new L3 zones are added to the
routed board directly with the same add_zone() the generator uses; pcbplace's
POWER_POURS carries the same rectangles so a future regeneration reproduces
this board. Run only while nothing else writes the board file.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbgen                                                  # noqa: E402
import pcbnew                                                  # noqa: E402
from pcbgen import PCB, canonicalise                           # noqa: E402
from pcbplace import add_zone                                  # noqa: E402

FINGERS = [(20.8, 15.0, 44.5, 26.9), (21.0, 5.0, 33.5, 15.2)]

board = pcbnew.LoadBoard(PCB)
l3 = board.GetLayerID("PWR_L3")
net = board.FindNet("3V3")
for rect in FINGERS:
    add_zone(board, l3, net, rect, name="")
    print(f"added 3V3 L3 finger {rect}")
board.BuildListOfNets()
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(PCB, board)
canonicalise(PCB)
print("FINGERS_APPLIED")
