# Finishing the routing by hand — a guide for someone new to PCB design

You do not need to understand electronics for this. The job is mechanical:
KiCad shows every missing connection as a thin straight line (a "ratsnest"
line) between two pads, and you draw a copper track along a path between
them. The design rules are already in the project, so KiCad itself stops you
from drawing anything illegal. Work through `hand-routing-worksheet.md`, one
line at a time, until no ratsnest lines are left.

Budget: about 44 nets, 94 connections. Expect 3–6 hours the first time.
Save often (Ctrl+S). Everything is in git, so nothing you do is dangerous.

## 0. Before you start (5 minutes)

1. Open a terminal in `/home/david/pcb` and get the finished branch:
   `git merge worktree-route-finish`
2. Open the project: double-click `telematics-tracker.kicad_pro`, then open
   the **PCB Editor** (the green board icon).
3. Turn on the things you need to see. In the right-hand **Appearance**
   panel:
   - **Layers** tab: make sure `F.Cu` (red) and `B.Cu` (blue) are visible.
     Turn OFF `GND_L2` and `PWR_L3` (the inner layers) so they do not
     confuse the picture — you must not draw on them anyway.
   - **Objects** tab: make sure **Ratsnest** is ticked. The thin white/grey
     straight lines that appear are the missing connections. Your goal is to
     make all of them disappear.
4. Make the board fit the screen: press **Home**. Zoom with the mouse
   wheel; pan by holding the middle button (or the wheel) and dragging.

## 1. The five keys you will use

| key | what it does |
|---|---|
| **X** | start drawing a track (the "interactive router") |
| **left click** | put a corner down while drawing |
| **double-click** or **click on the target pad** | finish the track |
| **V** (while drawing) | put a via down and continue on the other copper layer |
| **Esc** | cancel what you are drawing |
| **Ctrl+Z** | undo |
| **Page Up / Page Down** | switch between top (F.Cu) and bottom (B.Cu) layer when not drawing |

Set the router to *shove* once: **Route → Interactive Router Settings →
Mode: Shove**, tick **Optimize pad connections**. Shove mode pushes other
tracks gently out of the way instead of stopping — it is the mode that makes
this doable in a full area.

## 2. Routing one connection (repeat ~94 times)

1. Pick the next line in the worksheet, e.g. `U2.37 at (25.25, 19.33) F  <->
   TP2.1 at (49.35, 26.14) B`.
2. Find the first pad. Fastest way: press **Ctrl+F**, type the reference
   (`U2`), Enter — the part is highlighted; the worksheet coordinates tell you
   which pin (the status bar at the bottom shows your cursor's X and Y).
   Hovering a pad also shows its net name in the status bar — check it
   matches the worksheet.
3. Make sure the active layer (the layer dropdown in the top toolbar) is the
   pad's layer (F or B from the worksheet). Press **X**, click the pad.
4. Move the mouse toward the other pad. A track follows you. Click to place
   corners where you need to turn. The router will not let you cross
   another track or pad — it draws around them or stops.
5. If it stops and cannot pass: press **V** to drop a via and continue on the
   other layer, where there is usually room. Vias are fine anywhere except
   inside a part's outline, and never inside the two areas marked below.
6. Click on the destination pad. The ratsnest line disappears. Done —
   tick it in the worksheet.
7. Every 10 connections: **Ctrl+S**, then run DRC (section 4).

Tips that matter on this board:
- The hard area is around **U2** (the big square chip in the middle-left,
  around X 25–34, Y 18–26). Its pins are 0.5 mm apart. Zoom in a lot. Start
  a track by clicking exactly on the pin, drag straight out away from the
  chip for 1–2 mm, then turn.
- If a track refuses to go anywhere from a pin, drop a via **right next to
  the pin** (press V immediately after leaving the pad) and route on the
  other side of the board — the other side is usually emptier.
- Long nets (MODEM_RX/TX/RI/DTR from U2 to U8, SWDIO/SWCLK to TP1/TP2) have
  the most room on the **bottom** layer, running east.
- The GND connections in the worksheet are pads that need a short track to
  a **via** (any via on GND connects to the internal ground plane): press X
  on the pad, move 1 mm away, press V, then Esc. Done.
- 3V3 / 5V0 / SYS pads: same trick — a short stub to a via — works only
  where the inner power layer under that spot carries that rail. If DRC
  later says the via is unconnected, delete it and route a track on top or
  bottom to the nearest pad of the same net instead.

## 3. Things you must NOT do

- Do not draw on **GND_L2** or **PWR_L3** (the inner layers). They are
  solid ground and power pours by design. Keep them hidden.
- Do not move or delete any existing track that KiCad shows as **locked**
  (it will ask "unlock?" — answer No). Those are the high-voltage and
  antenna tracks; they were placed to keep 100 V away from everything else.
- Do not route anything in the strip **left of X = 19 mm** (the 100 V
  input area) or **right of X = 76.8 mm** (the antenna area). Nothing in the
  worksheet needs to go there.
- Do not change any part's position. (If you accidentally drag one,
  Ctrl+Z.)
- Do not change any design rule or netclass setting, even if KiCad offers.

## 4. Checking your work

**Inspect → Design Rules Checker**, tick *Report all errors for each track*,
click **Run DRC**. Two numbers matter, at the bottom:

- **Violations** must be **0**. If you see any, click each one — it jumps to
  the spot — and fix it (usually: move the track a little, Ctrl+Z, or drop
  the via elsewhere). Do not "exclude" violations.
- **Unconnected items** is your remaining to-do count. It starts at 94 and
  must reach **0**.

Warnings are fine; only the two numbers above block the order.

## 5. When both numbers are 0

In the terminal, from `/home/david/pcb`:

```
git add telematics-tracker.kicad_pcb && git commit -m "Hand-routed the remaining nets"
PYTHONPATH=tools python3 tools/release.py
```

If it prints `GATE PASSED`, upload `out/gerbers.zip`, `out/bom.csv` and
`out/positions.csv` to JLCPCB (4 layers, 1.6 mm, ENIG or HASL as per the
spec, **conformal coating on**, assembly: both sides). If it prints
`RELEASE BLOCKED`, it tells you why; nothing was exported.

## 6. If you get stuck

- A pad you cannot reach at all: note the net name and pin and ask — a
  small placement change may be needed, and that is a two-minute fix in the
  generator, not a redo.
- Something turned red / a part moved / you are unsure what happened:
  `git checkout -- telematics-tracker.kicad_pcb` in the terminal restores
  the last committed board (you lose only the uncommitted routing, so commit
  after every good DRC).
- Alternative to doing it yourself: this is a 3–4 hour task for a freelance
  KiCad layout engineer. Give them this file, the worksheet, and the branch;
  the DRC gate tells both of you when it is done.
