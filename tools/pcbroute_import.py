#!/usr/bin/env python3
"""Import a FreeRouting .ses session back onto the board, refill and report.

Stage 4 of milestone 4. Run after FreeRouting has produced a session file:

    python3 tools/pcbroute_import.py <routed.ses>

The hand-routed RF is exported LOCKED (Specctra `(type fix)`), so FreeRouting
does not move it and the import brings it back unchanged. Everything the
autorouter added is left unlocked so it can still be reworked.

FreeRouting version and jar SHA-256 are pinned in docs/MIGRATION.md section 1.
"""
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pcbgen import PCB, canonicalise                       # noqa: E402


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: pcbroute_import.py <routed.ses>")
    ses = sys.argv[1]
    if not os.path.exists(ses):
        sys.exit(f"missing session file: {ses}")

    board = pcbnew.LoadBoard(PCB)
    before = len(list(board.GetTracks()))
    print(f"before import: {before} track/via items")

    ok = pcbnew.ImportSpecctraSES(board, ses)
    print(f"ImportSpecctraSES: {ok}")

    board.BuildListOfNets()
    after = len(list(board.GetTracks()))
    print(f"after import:  {after} track/via items  (+{after - before})")

    try:
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
        print("zones refilled")
    except Exception as e:
        print(f"zone refill failed: {e}")

    pcbnew.SaveBoard(PCB, board)
    canonicalise(PCB)
    print("saved and canonicalised")


if __name__ == "__main__":
    main()
