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

## 5. RESUME HERE — state as of 2026-09-05 (after F-20 + buck fix)

Milestone 3 is closed. Milestone 4 placement is complete and **awaiting the
user's floorplan approval**. **Routing has not started and must not start until
that approval is given.**

### Verify before touching anything

Do these three checks first. Each guards a failure that is otherwise silent:

```bash
python3 tools/build.py        # runs the whole build in the only order that works
```
Then confirm all three:

| check | expected | why it matters |
|---|---|---|
| `VERIFIED: net classes and patterns survive a KiCad round trip` appears twice | yes | `pcbnew.SaveBoard()` wipes `net_settings`; if this fails, RF/HV/VBAT_MODEM rules are silently not applying (SKILL G2) |
| DRC total | **33 violations + 452 unconnected** — i.e. 20 clearance, 8 silk-over-copper, 3 isolated-copper, 2 silk-overlap. **Courtyard overlaps, shorting items and solder-mask bridges must all be 0.** | a different number means something moved; reconcile before proceeding |
| ERC | **0 errors, 13 warnings** (all `same_local_global_label`) | — |

`git status` must be clean after a build: the board is generated
deterministically and re-running must produce a byte-identical file.

### What is done

- **F-9 / F-9b** signed off; all 43 EC200U GND pads connected, verified against
  Table 7 of the datasheet committed at `docs/Quectel_EC200U_..._V1.2.pdf`.
- **F-13** 4× 47 µF X7R (C84494) = 111.9 µF effective at 4.35 V/85 °C. Rule 1 MET.
- **F-14** six test points. **F-15** R80 = 1 Ω (C55348540).
- **F-16 CLOSED** — the imported SIM footprint already had the locating-post
  holes, matching three vendors to 0.01 mm. Now NPTH.
- **F-17 CLOSED** — MFF2 land derived from four vendor documents + ETSI.
- **F-20 CONFIRMED** — conformal coating is a **safety-critical process
  requirement**; the 0.3 mm DRC exception at U5 is valid only while it holds.
- Placement, L2 GND, L3 pours, HV keepout (`HV_ZONE` rule area), 46 stitching
  vias. All 218 components placed, 137 top / 81 bottom.

### Next actions, in order

1. **Wait for floorplan approval.** Renders are in `out/renders/`.
   The buck-cluster overlaps are resolved (3 → 0) by restructuring the cluster
   into a column, **not** by changing the inductor — measured: growing the
   board plateaued at 2 overlaps and a 10×10 inductor still left 1. The
   incumbent L1 (C21325) is retained; C5142144 is the qualified 10×10 fallback
   if the outline ever shrinks. See design-log for the DCR/loss comparison.
2. **Then Option 1 routing** — hand-route RF CPWG (W = 0.40, G = 0.30) with
   fence vias at ≥ 0.80 mm standoff and 2.0 mm pitch, the HV front end, the
   VBAT_MODEM 2 mm rail and the U5 switching loop; then FreeRouting for the
   remaining low-speed nets (**pin its version and jar SHA-256 in §1 first**);
   then review to DRC-clean.

### Still open for the user

**F-20 is CONFIRMED and closed** — conformal coating is mandatory; the 0.3 mm
DRC exception at U5 is valid only while that holds (SKILL.md P1).
**F-18** 5th M3 hole needs a matching housing boss · **F-19** 1S Li-ion is
−20…+60 °C discharge against the +70 °C product ceiling · double-sided assembly
cost · AF1/AF2 sit at x = 72 while U1's ANT pads are at x = 76.55, so the RF run
doubles back inboard · final outline and hole positions from the purchased
housing.

**The narrative for every decision above is in `design-log.md`, newest last.**

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
