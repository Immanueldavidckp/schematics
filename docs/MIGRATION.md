# Machine migration — environment snapshot and restart instructions

Written before moving this project to another machine. Everything below was
captured from the working machine on 2026-09-04, at commit `main`.

Design state at freeze: **milestone 2 complete, milestone 3 deliverables
presented, awaiting sign-off.** Schematics are ERC-clean; layout has not
started and is intentionally blocked.

---

## 1. Toolchain versions

| Tool | Version | Notes |
|---|---|---|
| **KiCad** | **10.0.5** (Linux; was 10.0.0 on Windows pre-migration) | `C:\Program Files\KiCad\10.0`. The skill file asks for KiCad 9; 10 was already installed and reads/writes these files natively (logged deviation, milestone 1). |
| Python | 3.10.0 | `%LOCALAPPDATA%\Programs\Python\Python310` |
| easyeda2kicad | 1.0.1 | LCSC part import |
| Git Credential Manager | `credential.helper=manager` | how the GitHub push authenticated |

### Pinned Python packages (do not "upgrade" these)

```
fastmcp==2.12.5
mcp==1.16.0
```

These two must move together. Newer `fastmcp` 4.x / `mcp` 2.x **break
`kicad_mcp`** — in mcp 2.x `FastMCP` was renamed `MCPServer` and
`mcp.server.fastmcp` no longer exists. A leftover `fastmcp` 4.0 directory also
shadows a downgrade, so if imports still fail after pinning, delete
`site-packages/fastmcp/` and reinstall. Full incident in design-log, step 0.

```bash
pip install "fastmcp==2.12.5"            # pulls the matching mcp 1.16.0
python -c "import kicad_mcp; print('ok')"
```

### FreeRouting — pending tool dependency (milestone 4 routing)

**Not installed yet.** Recorded here now because the routing plan depends on
it: the critical nets (RF CPWG + fence vias, HV front end, VBAT_MODEM, the U5
switching loop) are hand-routed, and FreeRouting handles only the remaining
low-speed nets, after which its output is reviewed to DRC-clean.

| | |
|---|---|
| Upstream | https://github.com/freerouting/freerouting |
| Artefact | `freerouting-<version>.jar` from the GitHub Releases page |
| Version | **TO BE RECORDED** — pin the exact release tag, jar filename and SHA-256 here before it is run against the board |
| Runtime | `java` (present: /usr/bin/java) |
| Interface | KiCad exports Specctra `.dsn`; FreeRouting returns `.ses` which KiCad imports |

Rules for using it, so an autorouted result never silently becomes the design:
- it runs **only after** the critical nets are hand-routed and locked;
- its `.ses` import is reviewed and DRC-checked before commit;
- the exact jar version goes in this table, because routing output is not
  reproducible across FreeRouting versions.

### kicad-mcp

| | |
|---|---|
| Repo | https://github.com/lamaalrajih/kicad-mcp.git |
| Commit | `98c9ea41cb393393a8bafd157a93e84431e00afb` |
| Date/subject | 2025-10-17 · "Merge pull request #33 from paul356/workaround_null_ctx" |
| Installed at | `~/kicad-mcp`, registered as MCP server `kicad` |

The repo has no `requirements.txt` (it uses `pyproject.toml`); install the
package itself, then apply the pins above. A dedicated venv was attempted and
abandoned — Windows Application Control blocked the freshly-copied
`pydantic_core` DLL inside it, so the packages live in the global Python 3.10.

---

## 2. File-format versions (as written in the headers)

| File | Header `(version ...)` |
|---|---|
| `telematics-tracker.kicad_sch` and all five sheets | **20250610** |
| `telematics-tracker.kicad_pcb` | **20241229** |
| `lib/jlc.kicad_sym` | **20251024** |

`SCH_VERSION = "20250610"` is set in `tools/schgen.py`. If a future KiCad
rejects the generated sheets, that constant is the single place to change.
The symbol library was upgraded from easyeda2kicad's original 20211014 format
so its symbols embed cleanly into schematics (milestone 1).

---

## 3. Path portability — verified before the move

- `sym-lib-table` and `fp-lib-table` both use `${KIPRJMOD}/lib/...`. No
  absolute paths.
- **All 26 footprint `(model ...)` 3D-model references were rewritten from
  absolute `C:/home/PCB/...` to `${KIPRJMOD}/lib/jlc.3dshapes/...`** as part of
  this migration prep. easyeda2kicad had written machine-specific absolute
  paths; those would have broken every 3D model on a new machine. All 26
  referenced `.wrl` files were confirmed to resolve after the rewrite.
- `tools/schgen.py` no longer hardcodes the KiCad install. It searches, in
  order: `$KICAD_SYMBOL_DIR`, the Windows 10.0 and 9.0 paths, the Linux path,
  and the macOS bundle path. **On a machine where KiCad lives elsewhere, set
  `KICAD_SYMBOL_DIR`** and everything else follows.

Remaining `C:\...` strings in tracked files are prose in `design-log.md`
(historical narrative) and the Windows default inside the `schgen.py`
candidate list — neither is a functional dependency.

---

## 4. Restoring on the new machine

```bash
git clone https://github.com/Immanueldavidckp/schematics.git
cd schematics
# install KiCad 10.x, then:
pip install easyeda2kicad "fastmcp==2.12.5"
# only if the KiCad install path differs from the defaults in schgen.py:
export KICAD_SYMBOL_DIR="/your/kicad/share/kicad/symbols"
```

**Verify the move did not change the design** — regenerate and diff against the
committed snapshot:

```bash
python tools/sheets.py                       # must print 6 "wrote" lines
git diff --stat                              # must be EMPTY (regeneration is deterministic)

kicad-cli sch erc --output erc-full.rpt telematics-tracker.kicad_sch
#   expect: 0 errors, 14 warnings

kicad-cli sch export netlist --format kicadsexpr --output nl.net telematics-tracker.kicad_sch
python tools/checkpins.py nl.net             # expect exit 0
diff nl.net docs/netlist-snapshot-premove.net
```

`docs/netlist-snapshot-premove.net` is the frozen pre-move netlist:
**269 nets, 210 components**. A clean `diff` proves the migration changed
nothing electrical. (The `(date ...)` line inside the file will differ — that
is the only acceptable difference.)

---

## 5. Exact next step after migrating

Resume at **milestone 3, tasks 1–5** — the deliverables are prepared and
presented; what remains is the user's sign-off and the decisions it unblocks.
Nothing may be connected or routed before that.

1. **Task 1 — F-9 sign-off (hard gate).** Review `docs/f9-review.md`
   line by line: all 76 NEEDS-HUMAN EC200U pins, three sources each, 62 AGREE /
   14 CONFLICT. Priority 1 is the **35 GND rows** (51–54, 56, 72, 76, 85–112),
   then RESERVED rows 81/82/117. These pins are currently **no-connect** in
   `modem_rf.kicad_sch`; a modem with its ground field NC cannot go to layout,
   so connecting them after sign-off is the gate that unblocks milestone 4.
   Pins 64/65 (RTS/CTS swap) and 128 are logged anomalies with no design impact.
2. **Task 2 — keep `docs/firmware-notes.md` current** (FW-1…FW-17, BV-1…BV-4);
   update it every milestone.
3. **Task 3 — F-15 decision (layout blocker).** R80 is 10 Ω
   (FRP2512J100, C3013385). The pulse duty is fine — 8.5 mJ/event, 384 W peak,
   τ = 44 µs, energy independent of R — but 10 Ω has **no load-line solution at
   the 10.5 V floor at full load** (brown-out). Recommended: **1 Ω anti-surge,
   FRS2512F1R00TS, C55348540** (0.41 W continuous, same pulse energy).
4. **Task 4 — close the rules audit findings.** **F-13**: modem bulk caps are
   X5R 6.3 V on a 4.35 V rail (violates the no-X5R / 2:1 derating rule) —
   choose 10 V X7S, 4×22 µF/16 V X7R, or a written waiver. **F-14**: add the six
   missing test points (VIN, VBAT_MODEM, CANH, CANL, modem UART pair).
5. **Task 5 — milestone-4 prep is done except two footprint items.**
   Stackup defined (JLC7628 1.6 mm: L1 sig/RF, L2 solid GND, L3 power, L4 sig);
   placement study in `docs/placement-study.svg` on a **provisional 80×60 mm**
   outline — final outline and M3 hole positions come from the purchased
   housing. Open: **F-16** (SIM holder locating posts — drawing's y-datum is
   ambiguous, needs a physical sample or vendor answer; no copper was guessed)
   and **F-17** (MFF2 land pattern — needs the chosen eSIM vendor's packaging
   spec; st.com was unreachable).

Also still open: **F-12** (EG11752 R_IS value and the 100 V / 455 ns
min-on-time bench test — the #1 bench item) and **F-5** (provisional passive
C-numbers, to be verified at the milestone-5 BOM stage).

**Do not start routing until F-9 is signed off and F-15 is decided.**

---

## 6a. Build order (milestone 4 onwards)

The board is generated, like the sheets. **Use `python3 tools/build.py`** — do
not run the stages by hand. The order is load-bearing and every failure mode in
it is silent:

| step | why the order matters |
|---|---|
| `tools/sheets.py` | — |
| `kicad-cli sch export netlist` | `pcbplace.py` reads `nl.net`, not the schematic |
| `tools/pcbgen.py` | outline, mounting holes, HV silk boundary |
| `tools/pcbplace.py` | footprints, nets, HV keepout, planes, stitching vias |
| `tools/netclasses.py` | **after** the two above: `pcbnew.SaveBoard()` rewrites the project and wipes `net_settings`, so net classes applied earlier are gone |
| `kicad-cli pcb drc --refill-zones --save-board` | **after** net classes: the zones were filled while only Default existed, so the fill used 0.2 mm where HV needs 0.6 mm |
| canonicalise | the refill rewrote the board; re-stabilise it |

`tools/netclasses.py` verifies the classes survive a KiCad round trip and exits
non-zero if they do not. That check exists because all five classes had
silently reverted to just "Default" — any class missing `bus_width`,
`priority` or `tuning_profile`, or written with the wrong `meta.version`, is
discarded on the next load-and-save.

Two pcbnew traps worth knowing before editing the generators:
- **`board.Remove()` segfaults the interpreter** (exit 139, no traceback) — it
  hands ownership back to Python, which double-frees on the next GC. The
  generators never delete; they rebuild from `tools/pcb-template.kicad_pcb`.
- **`pcbnew.FootprintLoad()` returns one C++ object per library id.** Caching
  and reusing it collapses every component sharing a footprint onto a single
  instance, because `board.Add()` is a no-op after the first call. That
  produced 45 footprints instead of 219 and left 349 pads unbound to nets.

## 6. Working practice to carry over

Sheets are generated, not hand-drawn. Edit `tools/sheets.py`, run it, then run
ERC **and** `tools/checkpins.py`. The netlist guard is not optional: it has
caught four real faults that ERC reported only as warnings or missed entirely
(shorted-out gate resistor, CANL tied to GND, VBAT merged into 3V3, and a
root-sheet wrap-around shorting three rails).
