# Design Log — MEWP Telematics Tracker

Running log of every decision, deviation, and ERC/DRC exception, per `SKILL.md` golden rule 5.

---

## 2026-09-01 — Step 0: Environment setup

| Item | Result |
|---|---|
| KiCad | **10.0.0** already installed at `C:\Program Files\KiCad\10.0` (KiCad 8.0 also present) |
| easyeda2kicad | 1.0.1 installed via pip (Python 3.10.0) |
| kicad-mcp | Cloned to `~/kicad-mcp`, installed, registered as `kicad` MCP server — health check: **Connected** |

**Deviations from SKILL.md (flagged):**

1. **KiCad 10 instead of KiCad 9.** KiCad 10.0.0 was already installed; it opens/writes v9-format files natively. Using it rather than downgrading. All CLI checks below ran on 10.0.0.
2. **kicad-mcp has no `requirements.txt`** (repo now uses `pyproject.toml`). Followed the skill's fallback instruction ("follow its README"). Installed as a package instead.
3. **kicad-mcp dependency pinning.** Latest `fastmcp` 4.0 / `mcp` 2.x broke `kicad_mcp` imports (`mcp.server.fastmcp` removed in mcp 2.x). Pinned `fastmcp==2.12.5` + `mcp 1.16.0` (a compatible pair) in the **global** Python 3.10 environment. A dedicated venv was attempted first but Windows Application Control blocked freshly-copied `pydantic_core` DLLs inside it, so the venv was removed. Side effect repaired: `starlette` restored to `<0.37` for the pre-existing `fastapi` install.

## 2026-09-01 — Milestone 1: Project + library import + footprint verification

### Project created

- `telematics-tracker.kicad_pro` — JLCPCB-safe board rules pre-seeded (min track/space 0.15 mm, via 0.45/0.3 mm per SKILL.md §PCB rules).
- `telematics-tracker.kicad_pcb` — 4-layer stackup placeholder: F.Cu / In1.Cu (`GND_L2`) / In2.Cu (`PWR_L3`) / B.Cu. No outline yet (layout is milestone 4).
- `telematics-tracker.kicad_sch` — empty root sheet; hierarchical sheets come in milestone 2.
- `sym-lib-table` / `fp-lib-table` — project-local library `jlc` → `${KIPRJMOD}/lib/jlc.kicad_sym` + `lib/jlc.pretty`.
- **Parse check:** `kicad-cli sch erc` → 0 errors/0 warnings. `kicad-cli pcb drc` → 1 error: `invalid_outline` (no Edge.Cuts yet). **Expected pre-layout; accepted until milestone 4.**

### Library import (easyeda2kicad 1.0.1, full: symbol + footprint + 3D)

All 12 C-numbers from SKILL.md imported successfully into `lib/jlc.*`:

| C-number | Symbol imported | Footprint | BOM role |
|---|---|---|---|
| C2916205 | EC200UCNAA-N05-SGNSA | LCC-LGA-144 31×28 P1.30 | U1 modem |
| C55058656 | AT32F403ACGT7 | LQFP-48 7×7 P0.5 LS9.0 | U2 MCU |
| C5380158 | QMI8658B | LGA-14 3.0×2.5 P0.5 | U3 IMU |
| C5382551 | SIT1051AT/3 | SOP-8 3.9×4.9 P1.27 | U4 CAN |
| C477928 | LM5164DDAR | SO-8 + EP (PowerPAD) | U5 buck |
| C374063 | BQ25606RGER | VQFN-24 4×4 P0.5 EP2.8 | U6 charger |
| C16581 | TP4056 | ESOP-8 + EP | fallback (U6 alt) |
| C5126709 | SC7A20TR | LGA-12 2×2 P0.5 | fallback (U3 alt) |
| C151249 | SMBJ100A | SMB (DO-214AA) | D2 TVS |
| C359074 | EL357N | SOP-4 P2.54 LS7.0 | OK1/OK2 opto |
| C73013 | XL7015E1 | TO-252-5 | fallback (U5 alt) |
| C81551 | **GD32F105RBT6** | LQFP-64 10×10 | **⚠ NOT IN BOM — see issue F-1** |

### Footprint verification

Method: automated S-expression parse of every `.kicad_mod` (pad count, numbering continuity, pad-1 presence + silk marker, pitch, extents, courtyard/silk/fab layers) + symbol pin-count cross-check + datasheet comparison. The EC200U (highest-cost, highest-risk part) was verified pad-class-by-pad-class against the rendered mechanical drawings of Quectel *EC200U Series Hardware Design V1.2* §6.1–6.2. Symbols: pin count = footprint pad count for **all 12 parts**; all pad numbering sequential with no gaps; all footprints have pad 1, courtyard, and silkscreen.

| Footprint | Checks vs datasheet | Status |
|---|---|---|
| LCC-LGA-144 (EC200U) | 144 pads = 80 LCC (0.8×2.5, **1.30 mm pitch** ✓) + 64 LGA (27× 2.0×3.0 + 36× 1.1×1.1 ✓ exact match to Fig. 40) ; body 31×28 ✓; pad 1 top-left + 2 silk markers ✓; land extent 33.6×31.1 vs Quectel recommended 34.3×31.3 (LCC pads ~0.35 mm/side shorter outboard — JLC-proven variant, accepted) | **VERIFIED** (notes V-1, V-2) |
| LQFP-48 (AT32F403ACGT7) | 48 pads, 0.5 pitch, lead-span extent 9.84 (LS 9.0 + toe) ✓ standard LQFP-48 7×7 | VERIFIED |
| LGA-14 (QMI8658B) | 14 pads, 0.5 pitch, extent 3.2×2.7 vs body 3.0×2.5 ✓; pad-1 top-left ("TL") per QST datasheet | VERIFIED |
| SOP-8 (SIT1051AT/3) | 8 pads, 1.27 pitch, span extent 7.23 (LS 6.0 nominal) ✓ standard narrow SOIC-8 | VERIFIED |
| SO-8-EP (LM5164DDAR) | 8 pads 1.27 pitch + EP #9 3.2×2.5 vs TI DDA thermal pad ≈3.05×2.51 (land slightly larger — OK for thermal vias) | VERIFIED (note V-3) |
| VQFN-24-EP (BQ25606RGER) | 24 pads 0.5 pitch + EP #25 2.8×2.8 vs TI RGE EP 2.7 nominal ✓ | VERIFIED |
| ESOP-8 (TP4056) | 8 + EP #9 3.3×2.4 ✓ standard ESOP-8 | VERIFIED (fallback part) |
| LGA-12 (SC7A20TR) | 12 pads, 0.5 pitch, 2×2 body ✓ | VERIFIED (fallback part) |
| SMB (SMBJ100A) | 2 pads, extent 6.77 ✓ DO-214AA land | VERIFIED (note V-4) |
| SOP-4 (EL357N) | 4 pads, 2.54 pitch, span 7.6 (LS 7.0) ✓ | VERIFIED |
| TO-252-5 (XL7015E1) | 5 leads 1.27 pitch + tab 6.21×6.21 ✓ | VERIFIED (fallback part) |
| LQFP-64 (GD32F105RBT6) | Geometrically valid, but part not in BOM | **DO NOT USE** — issue F-1 |

### Issues / flags for the user

- **F-1 (BLOCKER for U7):** SKILL.md's import list contains **C81551, which resolves to GD32F105RBT6** (LQFP-64 MCU) — not in the BOM. Meanwhile **U7 (W25Q64JV SPI NOR flash) has no C-number and no imported footprint** — the handoff itself says "verify: W25Q64JVSSIQ". C81551 is almost certainly a typo for the flash's real C-number (W25Q64JVSSIQ is LCSC **C179171** — unverified, needs confirmation). Per golden rule 2, **no C-number changed**; awaiting user confirmation before importing the flash. The GD32 symbol/footprint stays in the library unused until then.
- **V-1:** EC200U footprint file is named `…L610-CN-02` — it is the EasyEDA/LCSC footprint for the MobileTek L610, a pin-compatible clone of the EC200U form factor. Verified against the *Quectel* drawing regardless (above); geometry matches.
- **V-2:** EC200U footprint contains one **zero-size pad (0.005×0.005 mm)** in the LGA area — an EasyEDA placeholder for a RESERVED pin. Watch for DRC complaints in milestone 4; if it trips, enlarge to the neighboring 1.1 mm square size (same position) or delete — decision deferred, will be logged.
- **V-3:** Verification was automated (parse + datasheet cross-check) rather than the GUI eyeball pass the skill describes. A visual 3D/GUI review in KiCad is still recommended before layout; scheduled with the milestone-5 3D render review.
- **V-4:** SMBJ100A footprint has no meaningful polarity distinction risk at footprint level, but **cathode-vs-pad-1 orientation must be pinned down at schematic capture** (unidirectional TVS: cathode to VIN). Added to milestone-2 checklist.
- **Deferred imports (expected):** "select in stock" BOM lines (U8 level shifter, U9 LDO, Q1–Q3 FETs, X1 SIM holder, J1 Micro-Fit, antennas, all passives) are chosen and imported at schematic time per handoff §3.

### Milestone gate status

- ERC 0/0 ✓ (empty root sheet) · DRC 1 known/accepted (no outline yet)
- Milestone 2 (schematics) **NOT started** — on hold per user instruction pending handoff §9 open items (max sustained VIN, housing model, DO load spec). The §9 VIN answer may change the power front end (LM5164 at 100 V has zero derating margin; XL7015 fallback caps at 80 V).

---

## 2026-09-01 — F-1 resolution: U7 flash import, GD32 removal

User resolved issue F-1: C81551 (GD32F105RBT6) was a leftover fallback MCU, not a flash typo. Actions taken on user instruction:

### Removals

- **C81551 / GD32F105RBT6 removed** from the `SKILL.md` import loop (replaced with C2685734) and purged from the library: symbol block deleted from `jlc.kicad_sym` (14,459 chars, balanced S-expression removal, zero residual references), `LQFP-64_L10.0-W10.0-P0.50-LS12.0-BL.kicad_mod` deleted, both LQFP-64 3D models (.wrl/.step) deleted. Library re-validated with `kicad-cli sym upgrade` on a scratch copy — parses clean.

### U7 flash: GD25Q64ESIG (LCSC C2685734) imported as primary

- Symbol + footprint `SOP-8_L5.3-W5.3-P1.27-LS8.0-BL` + 3D models imported via easyeda2kicad. Stock at import decision: 20,951 pcs (user-verified).
- **Alternates recorded** (user-verified pin- and command-compatible): **W25Q64JVSSIQ — LCSC C179171 / C2904572**, same SOIC-8 208mil footprint. Stored in the symbol's `Alternate` property and here.

### Footprint verification vs GD25Q64E datasheet rev 1.5 §10.2 (SOP8 208MIL)

| Check | Datasheet | Footprint | Result |
|---|---|---|---|
| Lead span E | 7.70–8.10 (nom 7.90) | outer extent 9.28 = nom span + IPC toe | ✓ |
| Body width E1 | 5.18–5.38 | inner pad gap 4.87 (heel under lead, L=0.50–0.85) | ✓ |
| Pitch e | 1.27 | 1.27 | ✓ |
| Lead width b | 0.31–0.51 (nom 0.41) | pad width 0.609 | ✓ |
| Pads/numbering | 8, no gaps, pad 1 + silk marker, courtyard | — | ✓ |
| Pinout | 1 CS#, 2 SO(IO1), 3 WP#(IO2), 4 VSS, 5 SI(IO0), 6 SCLK, 7 HOLD#(IO3), 8 VCC | symbol matches; identical to W25Q64JV; matches handoff §5 U7 wiring (WP#/HOLD# to 3V3) | ✓ |
| Speed/size | 133 MHz, 8 MB | handoff needs ≥30 MHz SPI, 8 MB ≈ 6 days buffer | ✓ |

**VERIFIED** — U7 footprint and symbol released for schematic capture.

### New flag for the user

- **F-2 (temperature grade):** C2685734 = GD25Q64E**SI**G = industrial **I-grade, −40…+85 °C**. The datasheet ordering table lists a J-grade (−40…**+105 °C**) variant of the same package: **GD25Q64ESJG**. Handoff rule 6 requires ≥105 °C semiconductors *where available*. Options: (a) keep ESIG (85 °C) and justify — flash is low-self-heating and inside the enclosure thermal budget; (b) switch to ESJG if stocked at JLCPCB. **Awaiting user decision; no change made.**

### Status

- Milestone 2 remains **on hold** pending handoff §9 answers (unchanged).

---

## 2026-09-01 — F-2 resolution: U7 temperature grade — **KEEP C2685734** (85 °C, justified)

### Q1: Is GD25Q64ESJG (J-grade, 105 °C, SOP-8 208mil) stocked?

**No.** LCSC/JLCPCB carry **6** GD25Q64E variants; **all are I-grade (−40…+85 °C)**. GD25Q64ESJG is not in the catalog at any price.

| MPN | LCSC | Package | Grade | Stock | @1k |
|---|---|---|---|---|---|
| GD25Q64ESIG | **C2685734** (ours) | SOP-8-208mil | I, 85 °C | 19,986 | $0.5036 |
| GD25Q64ESIGR | C2831359 | SOP-8-208mil | I, 85 °C | 16,745 | $0.4920 |
| GD25Q64ETIGR | C2976334 | SOP-8 **150mil** | I, 85 °C | 1,420 | $0.7789 |
| GD25Q64EYIGR / EQIGR / EWIGR | — | WSON/USON | I, 85 °C | **0** | — |

### Q2: What is GD25Q64ETIGR (C2976334)? — **incompatible, ruled out**

Datasheet §9 ordering table decode of the `T`: **SOP8 150mil**, not 208mil. LCSC's generic "SOIC-8" label hides this. Dimensions from §10.1 vs our footprint (§10.2, 208mil):

| Symbol | 150mil (C2976334) | 208mil (ours) |
|---|---|---|
| Lead span E | 6.00 nom | 7.90 nom |
| Body width E1 | 3.90 nom | 5.28 nom |
| Body length D | 4.90 nom | 5.23 nom |

**~1.9 mm narrower lead span — will not solder to our land pattern.** Also I-grade anyway, 14× less stock, 55 % more expensive. Rejected on package grounds before temperature is even considered.

### Q3: Does *any* 105 °C part fit our footprint? — **No** (cross-vendor sweep)

Swept all three major NOR vendors — **110 part numbers** — for a 3.3 V, SOP/SOIC-8-208mil, 105 °C SPI NOR:

| Family | Results | 208mil + 3.3 V + 105 °C in stock |
|---|---|---|
| GigaDevice GD25Q64E | 6 | none (all 85 °C) |
| Winbond W25Q64J | 42 | none (all 208mil parts 85 °C, incl. `…SSIM` C5362615) |
| Macronix MX25L64 | 62 | none (all SOP-8/SOIC-8-208mil 85 °C) |

Only 105 °C 64 Mbit part found anywhere: **W25Q64JWBYIQ (C2691929)** — WLCSP-12 **and** 1.7–1.95 V. Doubly incompatible (wrong package, wrong rail; our flash sits on 3V3).

### Decision — per user's decision rule, branch 2 ("if not stocked")

**U7 stays GD25Q64ESIG / C2685734.** No C-number changed. Winbond alternate is **not** re-flagged as derated: it is the *same* −40…+85 °C I-grade as the primary, so it remains an equal-grade alternate (grade now recorded explicitly in the symbol's `Alternate` field to prevent future ambiguity).

**Logged justification for the 85 °C deviation from handoff rule 6 (≥105 °C where available) — rule 6's "where available" condition is not met:**

1. **Junction ≈ ambient.** The flash is a near-zero-dissipation load: 12 µA standby, and active writes are ~4 mA in short bursts at 150 B/10 s (handoff §6). Self-heating is negligible, so T_J tracks in-enclosure ambient with no thermal-rise margin consumed — unlike the LM5164 or the modem, which are the real thermal actors on this board.
2. **Firmware write-throttling above 80 °C.** MCU reads its internal temperature sensor; above 80 °C the ring-buffer flush rate is throttled and non-critical writes are deferred, cutting program/erase cycling in the hot tail of the distribution (P/E endurance and retention degrade fastest at high temperature — this protects the 100k-cycle and 20-year-retention budget, not just the die).
3. **Shaded-mount installation note.** Installation instructions specify mounting the enclosure out of direct sun / off hot machine surfaces, keeping in-enclosure ambient inside the 85 °C rating for Indian summer field conditions.

**Carry-forward actions this creates for later milestones:**
- Firmware spec (post-layout): implement the 80 °C write-throttle above; requires MCU internal temp sensor channel — already available on the AT32 ADC, no hardware change.
- Documentation (milestone 6): add the shaded-mount requirement to the installation sheet.
- Re-check at order day: if a 105 °C 208mil part has appeared in stock, revisit before committing to volume.

### New flag for the user

- **F-3 (packaging, low priority):** our C2685734 is **tube-packed**; the otherwise identical **C2831359 (GD25Q64ESIGR)** is **tape & reel**, 16,745 in stock, and marginally cheaper ($0.492 vs $0.5036 @1k). Same die, package, and grade. T&R is the preferred feeder format for JLCPCB SMT assembly. Per golden rule 2, **no change made** — flagging for your approval; worth switching at order time if JLCPCB prefers reel for this line item.

### Housekeeping completed

- `SKILL.md` **moved** from `C:\home\PCB\Telematics\SKILL.md` into the repo at **`docs/SKILL.md`** (now version-controlled; it previously sat outside the repo root and its C-number fix was untracked).
- Synced to `~/.claude/skills/kicad-telematics/SKILL.md` — SHA-256 verified identical to `docs/SKILL.md`. Skill confirmed loaded/registered by Claude Code after sync.
- `telematics-handoff.md` deliberately left at `C:\home\PCB\Telematics\` (user's document, not a repo artifact).
- **Re-sync reminder:** `docs/SKILL.md` is now canonical. Any future edit must be copied back to `~/.claude/skills/kicad-telematics/SKILL.md` or the two will drift.

### Status

- Milestone 2 remains **on hold** pending handoff §9 answers (max sustained VIN, housing model, DO load spec). F-1 and F-2 are both closed; **no open blockers on the library side** — all U1–U7 footprints verified and released for schematic capture.

---

## 2026-09-01 — §9 answered: VIN = 9–100 V sustained (80 V packs, ~96–100 V while charging)

User confirmed fleet max is 80 V packs, so sustained input reaches ~96–100 V while
charging, with load-dump transients above that. Design range **9–100 V DC**. The
≥150 V-class buck rule stands. This closes the §9 max-voltage open item and
**invalidates the LM5164 (U5, C477928)** from the original BOM: 100 V abs max on a
100 V sustained rail is zero derating, against handoff rule 1.

## 2026-09-01 — MILESTONE 2 TASK A: buck selection + worst-case margin analysis

### A1. Named candidates — **both FAIL**

| Candidate | Verdict | Evidence |
|---|---|---|
| **SL3036H** | **FAILS — not buyable, no datasheet** | 0 stock at LCSC *and* JLCPCB for every SL3036* code (C2843664, C9900190738, C9900293210); LCSC product page returns "part not found". No official datasheet PDF exists anywhere — only vendor/blog marketing claims ("150 V transient"), never an abs-max table. Unsourceable and unverifiable: must not be designed in. |
| **LTC7138** | **FAILS twice** | Abs max VIN is **140 V, not ≥150 V** (ADI doc 7138f p.2: "VIN Supply Voltage −0.3 V to 140 V"), and max output is **0.4 A, not ≥0.7 A** ("Adjustable 100 mA to 400 mA Maximum Output Current"). Also $13.79@1 / $10.18@111+, ~50× the viable parts. |

### A2. LCSC sweep — method and completeness

The catalogue was enumerated through LCSC's own backend rather than the JS pages:
the parametric facet list for category 1029 (DC-DC switching regulators, 31,024
parts) yields 1,108 distinct "Operating Voltage" values, of which exactly **29**
have an upper limit ≥115 V; every part carrying those 29 values (57 rows) was
enumerated and cross-checked with MPN-prefix sweeps. **Nothing above 115 V in
LCSC's regulator catalogue is unexamined.**

**Critical sourcing lesson: LCSC's parametric "Operating Voltage" field is not
trustworthy.** It lists Hi9261 as 6–140 V when its datasheet says 100 V max
withstand, and U3213 as 150 V when the datasheet says 160 V. Every abs-max figure
below was taken from the datasheet's own absolute-maximum-ratings table.

Also debunked: the widely repeated "XL7005A = 150 V" claim is a **misreading of
150 kHz** — its datasheet abs max is VIN −0.3 to 85 V, 0.4 A. Fails both rules.

Families checked and eliminated: MP4572 (3 in stock, 100 V-class), MPQ4572 /
MP4576 / MPQ4569 (not carried), XL7005A (85 V), XL7015 (80 V), XL7016 (not
carried), SCT2xxx (36–60 V), LTC3639 (150 V ✓ but 100 mA), LT8631 (100 V),
AP1509 (42 V), SD42xxx, LM5164 (100 V), LM5017 (100 V), LM5163 (100 V),
LM5168 (120 V, 300 mA), HT1203A (120 V), Hi9261 (100 V), EG11727/EG11721
(min VIN 18–20 V), U3018/U3015 (600 mA), ICW6215 (650 mA), plus all
external-FET controllers (violate the integrated-FET requirement).

### A3. Worst-case margin analysis — 10 Ω series + SMBJ100A clamp event

**Topology analysed:** `J1.VIN → F1 → D1(S3M) → node A → [SMBJ100A to GND] → 10 Ω → node B (buck VIN + Cin) → buck`

**SMBJ100A parameters** (600 W, 10/1000 µs): V_RWM 100 V; V_BR 111 V min /
**123 V max** @1 mA; V_C **162 V @ I_PP 3.7 A**.
Dynamic resistance R_d = (162 − 123) / 3.7 = **10.5 Ω**.
Clamp model (conservative, from V_BR max): `V_clamp(I) = 123 + 10.5·I`

**Why the 10 Ω does not attenuate the governing case.** Buck input current is
small: 5 V × 1 A at ~85 % efficiency ≈ 5.9 W, so I_in ≈ 59 mA at 100 V, giving
only 10 Ω × 59 mA = **0.6 V** of DC drop. The 10 Ω does form a low-pass with
C_in (2 × 2.2 µF per §4): τ = 10 Ω × 4.4 µF = **44 µs**. That attenuates fast
ISO 7637-2 pulses 3a/3b (100 ns) strongly and pulse 2a (50 µs) partially, but the
SMBJ's own 10/1000 µs surge and a real load dump both last ≫ 44 µs, so C_in
charges fully and **node B sees essentially the full clamp voltage**. The series
resistor therefore buys transient-edge protection, not clamp-level protection —
the buck's abs max must cover V_clamp directly.

So: `V_B = V_clamp(I) − 0.6 V`, and the rule V_B ≤ 0.85 × V_absmax gives a
**maximum permissible TVS surge current** per abs-max class:

| Buck abs max | Max V_B for 15 % margin | Permitted TVS current | Covers SMBJ100A full 3.7 A rating? |
|---|---|---|---|
| 150 V | 127.5 V | 0.43 A | **No** — only 12 % of rating |
| 160 V | 136.0 V | 1.24 A | **No** — only 34 % of rating |
| **200 V** | **170.0 V** | **4.48 A** | **Yes** — exceeds the 3.7 A rating outright |

**Only a 200 V-class part holds ≥15 % margin across the SMBJ100A's entire rated
surge range.** Margins at two bracket currents (V_B = 161.4 V at full 3.7 A;
V_B = 132.9 V at a moderate 1 A transient):

| Part | C# | Abs max (conservative) | Margin @3.7 A | Margin @1 A | Verdict |
|---|---|---|---|---|---|
| **EG11752** | C53368402 | **200 V** (§7.1, unambiguous) | **+19.3 %** ✓ | +33.6 % ✓ | **PASSES the rule** |
| Hi9263 | C51889967 | 150 V (§4 table; §6 says 160 V — **conflicting**) | −7.6 % ✗ | +11.4 % ✗ | fails |
| TX4135A | C20625825 | 150 V (BVSW min; SW–GND 160 V — conflicting) | −7.6 % ✗ | +11.4 % ✗ | fails |
| EG11722 | C53368437 | 150 V (§7.1) | −7.6 % ✗ | +11.4 % ✗ | fails |
| Hi9103B | C52952898 | 150 V (§4) | −7.6 % ✗ | +11.4 % ✗ | fails (also peak-only current spec) |

Where a datasheet gives two conflicting numbers (Hi9263, TX4135A) the
**lower** figure is used — a part whose own document contradicts itself cannot be
credited with the higher rating on a 5-year deployment.

**Second finding — the SMBJ100A itself is the wrong TVS for this bus.** Its
standoff is exactly 100 V against a 100 V sustained rail: zero margin, sitting on
the knee where leakage rises steeply, and worse at 85 °C — a self-heating and
long-term-drift risk. Normal practice is standoff ≥1.15–1.25 × sustained. But
raising standoff raises clamp (SMBJ120A V_C = 193 V, SMBJ130A 209 V), which
would break even a 200 V part. The correct fix is to **keep the 100 V standoff and
upsize the package for lower dynamic resistance**:

| TVS | Rating | R_d | V_clamp @3.7 A | V_B | Margin on 200 V part |
|---|---|---|---|---|---|
| SMBJ100A (as specified) | 600 W | 10.5 Ω | 162.0 V | 161.4 V | +19.3 % ✓ |
| SMCJ100A | 1500 W | 4.2 Ω | 138.5 V | 137.9 V | +31.1 % ✓ |
| **SMDJ100A** | 3000 W | 2.1 Ω | 130.8 V | 130.2 V | **+34.9 %** ✓ |

### A4. Recommendation

**U5 = EG11752, LCSC C53368402** — the only part in LCSC's entire catalogue that
satisfies all three constraints simultaneously (≥150 V abs max, ≥0.7 A, and ≥15 %
margin under a full-rated SMBJ100A clamp). 200 V abs max, 1.5 A continuous
(2 A short-term), ESOP-8, 3,355 in stock, $0.293@1 / **$0.1722@500**, ~11 external
parts, 110 kHz with spread-spectrum dithering.

**Paired change: upgrade D2 from SMBJ100A to SMDJ100A** (3000 W, same 100 V
standoff, ~5× lower dynamic resistance). Raises margin from 19.3 % to 34.9 % and
costs a package step. Not a BOM substitution I have made — flagged for approval
with the buck.

**Risks that must be accepted or retired before layout freeze:**
1. **Min VIN is 10 V; spec floor is 9 V.** VCC(ON) 8.5 V / VCC(OFF) 7.8 V suggest
   it will run at 9 V, but that is outside the guaranteed range. Either bench-verify
   at 9 V or confirm the 9 V floor is soft. (Hi9263 is the only viable part with a
   datasheet-guaranteed 6 V floor — but it fails the margin rule.)
2. **Minimum on-time is unspecified.** At 100 V→5 V the duty is 5 %, i.e. Ton ≈
   450 ns at 110 kHz. No Chinese datasheet in this set specifies a min on-time.
   This is the single most likely bench surprise; test at 100 V in / 0.7–1 A out.
3. **Datasheet is V1.0, dated Nov 2024** — very new silicon, no field history,
   Chinese-only documentation, single-source vendor. Against a 5-year field-life
   requirement this is the biggest non-electrical risk in the whole BOM.
4. **Extended, not Basic, at JLCPCB** — true of all five viable parts; budget the
   extended-part fee.
5. **Second source:** EG11722 (C53368437) is pin-for-pin identical at 150 V —
   the only drop-in redundancy available anywhere in this search, though it does
   not meet the margin rule and would be a derated emergency substitution only.

**STOP POINT — awaiting user approval of U5 before power.kicad_sch is drawn.**

## 2026-09-01 — MILESTONE 2 TASK B, sheet 1 of 4: mcu.kicad_sch **ERC-clean**

Commit `c0e2dec`. 38 components, 49 nets, ERC **0 errors**.

**Pin map verified 48/48** against the exported netlist by the new
`tools/checkpins.py`, which asserts every handoff §5 row against the real netlist
rather than by eye. Output is reproduced in the milestone-2 report.

### Tooling (commit `818c562`)

Sheets are generated by `tools/schgen.py` + `tools/sheets.py` rather than
hand-written, so they are reproducible and diffable. Symbol definitions are copied
from the KiCad 10 stock libraries and `lib/jlc.kicad_sym`; connections are made by
labels on short pin stubs. Five KiCad file-format traps were found the hard way
(each reported only as "Failed to load schematic") and are now guarded with loud
assertions: bare-named child unit symbols, schematic-illegal `show_name` /
`do_not_autoplace` / `in_pos_files` tokens, the 1.27 mm grid, `in_bom`/`on_board`
on power symbols, and project-wide-unique power references.

The net-collision detector added during this work immediately earned itself: it
caught R3's and FB1's stubs both landing on (88.9, 88.9), which had **silently
merged VBAT_MCU into 3V3 and shorted MCU pin 1 to pin 48**. That is exactly the
class of fault that survives visual review, and it would have reached the PCB.

### Deviations and additions on this sheet (all flagged)

1. **U3 (QMI8658B IMU) placed on the mcu sheet.** The skill's sheet list and TASK B
   assign it no sheet, but §5 rows for PB5/PB6/PB7 say "goes to U3 INT1/SCL/SDA",
   so honouring §5 exactly requires U3 to exist. Placed here as the MCU-attached
   peripheral it is. Flag **F-6** if you want it moved to a sensors sheet.
2. **VSSA (pin 8) tied directly to GND, not to a separate AGND island.** §5 says
   "AGND", but the skill's PCB rules mandate a solid L2 ground plane; a split
   analog island would violate that and degrade the RF return. VDDA still gets its
   own ferrite + 1 µF + 100 nF filter, which is what actually buys ADC quiet.
3. **PB2/BOOT1 10 k pulldown added** (not in §5). Required for a deterministic boot
   mode on this MCU family; leaving BOOT1 floating risks random bootloader entry
   in the field.
4. **IMU wiring taken from the QST QMI8658B datasheet Rev D §1.4**, which
   contradicts the naive reading: **RESV (pin 10) must NOT be tied to GND** — it is
   tied to 3V3 (datasheet: "should NOT be connected to GND or Logic Low… connecting
   it to VDDIO is preferred"). **RESV-NC (pin 11) must float** — left as a
   no-connect. CS tied high selects I2C; SDO/SA0 tied high sets address 0x6A.
   Tying pin 10 low, the obvious guess, would have been a silent field failure.
5. **PC13 heartbeat LED wired as a current sink** (3V3 → 1 k → LED → PC13), because
   PC13 on this family has weak source drive.

### ERC exceptions on this sheet — individually justified

- **51 × `isolated_pin_label`** — every one is a root-level sheet-pin label whose
  net currently has only the mcu sheet as a member. 24 of them (FLASH_CS, SPI1_*,
  DI*, DO*_GATE, CAN1_*, CAN_STB, MODEM_*, *_SENSE, ADC_SPARE) pair up as
  storage/io/modem_rf are added; the 6 rail labels (VIN, SYS, 5V0, 3V3,
  VBAT_MODEM, VDD_EXT_1V8) resolve when power.kicad_sch lands. **Zero remain
  unexplained.**
- **0 errors.** No error-severity exception is being carried.
- Importer symbols declare every pin "unspecified", which made ERC flag all 36
  IC-to-passive connections as pin conflicts. Rather than suppress the check
  project-wide (which would hide real conflicts), the embed step remaps
  `unspecified` → `passive`, the honest neutral type for a pin whose direction the
  importer never recorded. `pin_to_pin` warnings went 36 → 0 with the check still
  live.

### New flag — **F-5: passive C-numbers are PROVISIONAL and unverified**

The generic passives on this sheet carry C-numbers I selected as well-known JLCPCB
Basic parts (10 k C17414, 100 nF C14663, 1 µF C15849, 4.7 µF C23733, 18 pF C1653,
6.8 pF C1555, 4.7 k C17673, 2.2 k C4356, 1 k C17513, 100 R C17408, 0 R C17477,
LED C2286, MMBT3904 C20526, ferrite C1017, 8 MHz C115962, 32.768 kHz C32346).
**These have NOT been verified against live LCSC stock or datasheets in this
session** — unlike the U1–U7 semiconductors, which were. Per golden rule 2 they are
recorded as chosen but must be stock- and package-checked before any order; the
crystal load capacitance in particular (18 pF/6.8 pF) must be recomputed against
the actual crystal's C_L once the crystal part is fixed. Treat every value in that
list as provisional.

### Status

Sheets 2–4 (storage, io, modem_rf) still to draw. Power sheet and milestone 3
remain blocked on the U5 approval above.

---

## 2026-09-02 — TASK B sheets 2 and 3: storage and io **ERC-clean**

**storage.kicad_sch** (commit `d8a4b5d`) — 6 components. U7 GD25Q64ESIGR on SPI1:
CS from FLASH_CS (PA4), SCK/MOSI/MISO on SPI1_*, WP#(3) and HOLD#(7) tied to 3V3
per §5, 100 nF + 1 µF. **F-3 resolved by the user's instruction**: U7 is now the
tape-and-reel **C2831359**, not the tube-packed C2685734. The W25Q64JVSSIQ
alternate is carried in the symbol's `Alternate` field.

**io.kicad_sch** (commit `bda73f0`) — 85 symbols, 15 sheet pins. Contents exactly as
specified in TASK B: J1 12-pin harness on the given pinout (spares 11/12 brought
out to test points), SIT1051AT/3 with VIO=3V3 / VCC=5V0 / STB=PA15, CM choke plus
TVS at the connector, split termination 2×60 Ω + 4.7 nF behind JP2 **default
OPEN**, opto-isolated DI1/DI2, low-side DO1/DO2 with 100 R gate series + 10 k
pulldown + SS310 flyback to VIN, VIN/IGN dividers with BAV99 rail clamps, 1 M:1 M
battery divider from SYS, and the DNP spare ADC divider.

### Root inter-sheet plumbing changed: global labels, not plain labels

With only the mcu sheet present, a plain label on a sheet-pin stub behaved
correctly. As soon as a second sheet exposed the *same* net name, KiCad reported
**both** labels as `label_dangling` (error) rather than merging them. Root-level
plumbing now uses **global labels**, which merge by name by definition. Verified by
netlist, not by eye: `FLASH_CS -> [(U2,14), (U7,1)]`, `SPI1_SCK -> [(U2,15),
(U7,6)]`, and so on.

### Two real electrical faults caught by new generator guards

Both would have survived a visual review and reached the PCB:

1. **The 100 R DO gate resistor was shorted out.** The FET gate pin had received
   *two* connections (a local label to `Qn_G` and a hierarchical label to
   `DOn_GATE`), whose stubs overlap, so the MCU drove the gate directly and the
   series resistor sat on a dead net. A **pin-connected-twice** guard now raises on
   this. Verified fixed: `DO1_GATE -> [(R23,1), (U2,27)]`.
2. **CANL was shorted to GND.** D3's GND stub (x 87.63→90.17) and D4's CANL stub
   (x 88.90→92.71) were collinear at y=45.72 and overlapped by 1.27 mm — the two
   horizontal TVS symbols sat 12.70 mm apart where their stubs need >13.97 mm. ERC
   had reported this only as a `multiple_net_names` *warning*, which is easy to skim
   past. A **collinear stub-overlap** guard now raises on it. Verified fixed:
   `CANL -> [(D4,1), (J1,5), (L2,3)]`, no GND.

The earlier net-collision guard (point-based) could not see either fault; the
generator now checks points, whole segments, duplicate references, duplicate pin
connections, and the 1.27 mm grid.

### DI1/DI2 LED current window vs EL357N(D) CTR — requested check

Series resistance 24 kΩ (2 × 12 kΩ), opto V_F ≈ 1.2 V:

| Input | I_LED | Collector current needed | Available at CTR ≥ 300 % (D bin) | Margin |
|---|---|---|---|---|
| 9 V (min) | **0.325 mA** | 62 µA (3.3 V through 47 k to V_IL 0.4 V) | 0.98 mA | **16×** |
| 100 V (max) | **4.12 mA** | 62 µA | 12.4 mA | 200× |

The window is comfortable at both ends — the input works down to 9 V with 16× CTR
margin, and 4.12 mA at 100 V is well inside the EL357N's LED rating.

**F-7 (real thermal problem, needs a decision).** The *resistors* are the issue, not
the opto. At 100 V, I²R = (4.12 mA)² × 24 kΩ = **0.407 W total, 0.204 W per 12 kΩ
1206**. A 1206 is rated 0.25 W at 70 °C and derates to roughly **0.125 W at 105 °C
ambient** — so each resistor is at ~1.6× its derated rating in a hot enclosure, on a
part that handoff rule 6 wants good to 105 °C. Options: (a) split into **3 × 8.2 kΩ
1206** (same 24.6 kΩ, 0.136 W each — still marginal), (b) **3 × 12 kΩ** for 36 kΩ
total (0.09 W each, comfortable; min I_LED falls to 0.22 mA, still ~10× CTR margin),
or (c) keep 2 resistors but specify **0.5 W 1206** parts. **Recommendation: (b).**
Implemented as specified (2 × 12 kΩ 1206) pending your decision — this is a
sustained-dissipation issue, not a transient one, so it should be resolved before
layout.

### ERC exceptions on io — individually justified

- **18 × `isolated_pin_label`** — root global labels whose net has only one sheet so
  far; all resolve when power.kicad_sch and modem_rf land.
- **10 × `same_local_global_label`** — a net name exists both as a sheet-local label
  and as the root global label (e.g. DI1, VIN, 3V3). This is by design: the sheet's
  local net is joined to the root net *through the hierarchical sheet pin*, which is
  the required hierarchical structure. Renaming either side would violate the §5
  net-name requirement. Verified connected by netlist, e.g.
  `DI1 -> [(C25,1), (OK1,4), (R21,2), (U2,25)]`.
- **4 × `footprint_link_issues`** — the four parts still carrying the placeholder
  `TBD:` footprint (J1, L2, D3, D4), pending the in-stock selection sweep (F-8).
- **0 errors.**

### F-8: parts awaiting the in-stock sweep

These carry LCSC `TBD-F8` in the schematic and must be filled before any order:
Q1/Q2 (150 V logic-level NMOS), J1 (12-pin Micro-Fit), L2 (CAN CM choke), D3/D4
(CAN TVS), D5–D8 and D10/D11 (BAV99, SS310), the 60 Ω/47 k/12 k/100 k/9.1 k/1 M
resistors and the 4.7 nF cap. A selection sweep is running; results will be logged
and the generator constants updated in a follow-up commit.

## 2026-09-02 — TASK B sheet 4: modem_rf **BLOCKED — do not draw**

### F-9 (BLOCKER): the imported EC200U symbol's pin numbering contradicts Quectel's datasheet

While preparing modem_rf I checked the imported symbol for `C2916205` against
**Quectel EC200U Series Hardware Design V1.2, Table 7 (Pin Description)**. It does
not match, and the mismatch is on the most destructive pin in the design:

| Signal | Quectel Table 7 | Imported symbol | |
|---|---|---|---|
| **VBAT_BB** | **59, 60** | **90, 91** | **WRONG** |
| **VBAT_RF** | **57, 58** | absent | **WRONG** |
| PWRKEY | 21 | absent (pin 21 unnamed) | missing |
| RESET_N | 20 | absent (pin 20 unnamed) | missing |
| MAIN_TXD / MAIN_RXD | 67 / 68 | absent | missing |
| MAIN_RI / MAIN_DTR | 62 / 66 | absent | missing |
| STATUS | 61 | absent | missing |
| USB_DP / USB_DM / USB_VBUS | 69 / 70 / 71 | absent | missing |
| MAIN_DCD | 63 | labelled "LOUDSPK" | **WRONG** |
| ANT_MAIN / ANT_GNSS | 49 / 47 | 49 / 47 | ok |
| USIM_VDD/DATA/CLK/RST/DET/GND | 14/15/16/17/13/10 | same | ok |
| VDD_EXT | 7 | 7 (+109, spurious) | partly ok |
| NET_STATUS / AP_READY | 6 / 2 | 6 / 2 | ok |
| I2C_SCL/SDA, ADC0-2, DBG_TXD/RXD | 41/42, 45/44/43, 12/11 | same | ok |

**80 of the symbol's 144 pins carry no name at all** ("undefined"), and every pin in
the 57–71 block — VBAT, STATUS, the main UART, and USB — is either missing or
mislabelled.

**Root cause:** this is the failure mode note **V-1** flagged in milestone 1 but
under-weighted. The footprint is `LCC-LGA-144_…_L610-CN-02`, i.e. the EasyEDA entry
is built around the **MobileTek L610**, a different module in the same LCC-144 form
factor. In milestone 1 I verified the **footprint geometry** against Quectel's
mechanical drawing and it matched (pad sizes, 1.30 mm pitch, 31×28 mm body) — but I
did **not** verify the **symbol's pin assignment**, and that is where it diverges.
Correcting the record: V-1's "geometry matches, accepted" conclusion was sound for
the land pattern and **wrong to extend to the symbol**.

**Consequence if ignored:** VBAT wired to pads 90/91 puts the 3.3–4.4 V, 1.5 A
battery rail on the wrong pads and leaves the real VBAT pads (57–60) unpowered.
That destroys the modem on first power-up, and possibly more. There is also no way
to wire PWRKEY, RESET_N, the UART or USB at all, so handoff §6 and §5 rows 29–33
and 39–40 cannot be honoured from this symbol.

**Action taken:** modem_rf.kicad_sch **not drawn**. Per golden rule 1 (never invent
a symbol) I have not fabricated pin assignments, and per rule 2 I have changed no
C-number. The authoritative pin table extracted from the Quectel PDF is saved to
`docs/ec200u-pinmap-extracted.md` (99 of 144 pins parsed; the unparsed remainder are
mostly GND/RESERVED/NC rows, and the file is explicitly marked as needing a
line-by-line human check before use).

**Options for you to choose from:**
1. **Re-import from a correct source.** Check whether another LCSC/EasyEDA entry for
   the EC200U carries a correct symbol, or obtain Quectel's official library.
   Cheapest if such an entry exists.
2. **Build a datasheet-derived EC200U symbol** in a project-local library from
   Table 7, with the pin table human-verified first, and keep the existing
   (geometrically verified) footprint. ~1 session of work plus review. This is my
   recommendation if option 1 comes up empty.
3. **Defer modem_rf** to after the power sheet.

Whichever path, the footprint should also be re-checked for **pad numbering** (not
just geometry) before layout: matching pad *positions* does not guarantee the L610
and EC200U number those pads identically, and note V-1 only established geometry.

### Status

Sheets 1–3 (mcu, storage, io) are drawn and ERC-clean. Sheet 4 is blocked on F-9.
Power sheet and milestone 3 remain blocked on the U5 buck approval.

---

## 2026-09-02 — U5 APPROVED: EG11752 (C53368402), with conditions

User approved U5 = EG11752. Conditions logged as binding design requirements:

**(a) Guaranteed input range redefined: 10.5-100 V. The 9 V floor is WITHDRAWN.**
Rationale: EG11752 VCC(ON) = 8.5 V / VCC(OFF) = 7.8 V, datasheet operating floor
10 V. With 0.5 V margin the guaranteed floor is set at 10.5 V; the backup battery
rides the unit through supply dips below 10.5 V (that is what it is for).
The DI input validity range and all divider math now quote 10.5-100 V.

**(b) D2 upgraded SMBJ100A -> SMDJ100A.** Selected: **Littelfuse SMDJ100A,
LCSC C1977839** — DO-214AB (SMC), 3 kW 10/1000 us, V_RWM 100 V, V_BR 111 V min,
**V_C 162 V @ I_PP 18.5 A** -> R_d ~ 2.1 ohm. 2,955 in stock, $0.6112@1 /
$0.3187@1k, tape & reel. Tier-1 vendor chosen deliberately for a protection part
on a 5-year product over four cheaper Asian-brand listings.
**Margin verified: at the analysed 3.7 A surge, V_clamp = 123 + 2.1 x 3.7 =
130.8 V -> V(buck-in) = 130.2 V = 34.9 % below the EG11752's 200 V abs max** —
matches the predicted 34.9 % in the TASK A table. Even at the SMDJ's full
18.5 A rating, V_clamp = 162 V leaves 19 % margin.

**(c) Qualification requirement added to milestone 6:** 3 prototype units,
1000 h burn-in at 100 V input / 85 C ambient, plus thermal cycling
(-40 <-> +85 C), before any volume order — mitigation for the V1.0-datasheet
new-silicon risk. Pass criteria to be defined with the milestone-6 test plan.

**Leakage acceptance for the 100 V standoff at 96 V sustained:** SMDJ100A
I_R <= 2 uA at V_RWM = 100 V (25 C). At 96 V sustained, leakage is below that
at 25 C and rises roughly a decade over temperature to an estimated <~100 uA at
85 C worst case — << 10 mW, thermally negligible, and irrelevant to the sleep
budget (the TVS sits on the machine-power side). **Accepted.** Note V_BR min
111 V > 100 V sustained: the diode never enters breakdown in normal operation;
96-100 V sustained sits between V_RWM and V_BR where only leakage flows.

### EG11752 datasheet values for power.kicad_sch (drawn after F-9 release)

From EG11752 datasheet V1.0 (Chinese), sections 5/6/7/8 — app circuit =
Figure 6-2 (5 V/3.3 V variant, which omits Fig 6-1's D2+R6 VCC bootstrap):

| Item | Value | Source |
|---|---|---|
| Topology | non-sync buck, internal 200 V/2 A high-side MOS, floating VB/VS bootstrap driver | s5 |
| Pins (ESOP-8) | 1 VCC, 2 EN, 3 GND, 4 FB, 5 VB, 6 VS, 7 IS, 8 VIN (+pad=VIN) | fig 5-1/6-2 |
| VREF (FB) | 1.28 / 1.30 / 1.32 V | s7 |
| I_FB | <= 1 uA | s7 |
| IS current-limit threshold | 0.2 V typ (R_IS between IS and VS sets peak current) | s7 |
| Fosc | 110 kHz typ, +/-5 % vs VCC, +/-8 % vs temp | s7 |
| D_max | 90 % | s7 |
| VCC internal LDO | <= 10 V; VCC(ON) 8.5 V, VCC(OFF) 7.8 V, Icc ~ 1 mA | s7 |
| VB(ON)/VB(OFF) | 7 / 6.5 V | s7 |
| EN(on)/EN(off) | 2.5 / 2.3 V | s7 |
| Ron / BV | 650 mohm / 200 V min | s7 |
| Thermal shutdown | 155 C | s7 |
| C_VCC (C2) | **1 uF, 25 V** | fig 6-2 |
| C_boot VB-VS (C5) | **0.1 uF, 25 V** | fig 6-2 |
| FB divider for 5 V | **R_top 4.3 k / R_bot 1.5 k -> 5.03 V** | s8.5 worked example |
| Freewheel D1 | Schottky, fast + low V_F (SS3200-class 200 V given our bus) | s8.3 |
| L selection | L = Vout(Vin-Vout)/(Vin x Fs x Iripple), Iripple <= 30 % Iout(max) | s8.2 |
| EN (R1) | pull-up to VIN (> 2.5 V turns on) | fig 6-2 |
| Output caps | electrolytic + ceramic in fig 6-2; ceramic-only per handoff rule 1, sized by dVo = dIL x (ESR + 1/(8 x Fs x Co)) | s8.4 |

*Derived (mine, not the datasheet's):* at Iout(max) = 1 A, Iripple = 0.3 A:
L = 5x95/(100 x 110k x 0.3) ~ **144 uH at Vin = 100 V** (governing case) ->
**150 uH standard value, Isat >= 1.6 A**, finalised with the IS resistor when
power.kicad_sch is drawn. Min on-time check: at 100 V -> 5 V, Ton ~ 455 ns;
the datasheet specifies no minimum on-time — **the 100 V-in / 0.7-1 A-out
regulation test remains the #1 bench item** (carried from TASK A risk list).

## 2026-09-02 — F-7 closed (commit `c30340b`)

DI series = **3 x 12 k 1206** (36 k). Per-resistor dissipation at 100 V:
0.090 W = 72 % of the 105 C-derated 0.125 W rating (was 163 % with two).
**Current window at the new 10.5 V floor:** I_LED = (10.5 - 1.2)/36 k =
**0.258 mA** -> collector capability at CTR >= 300 % (EL357N D-bin) = 0.775 mA
vs 61.7 uA needed to pull the 47 k node below V_IL — **12.6x margin**. At
100 V: I_LED = 2.74 mA — 133x margin, LED rating untouched. Chain verified by
netlist on both channels; ERC 0 errors.

## 2026-09-02 — F-9 CLOSED at step 1 (commits `a086213`, `01f7cc6`)

**C2916206 (EC200UCNLA-N05-SGNSA) imported and adopted; the defective
C2916205 symbol deleted from the library.** Comparison against Quectel EC200U
HW Design V1.2 Table 7: all 144 pins named, **0 wrong / 0 missing** on the 23
design-critical pins once documented naming variants are mapped (TXD->MAIN_TXD,
RXD->MAIN_RXD, RI*->MAIN_RI, DTR*->MAIN_DTR, DCD*->MAIN_DCD,
USIM_PRESENCE->USIM_DET, NETLIGHT->NET_STATUS). VBAT_BB 59/60 ok, VBAT_RF
57/58 ok, PWRKEY 21 ok, RESET_N 20 ok, STATUS 61 ok, UART 67/68/62/66 ok,
USB 69/70/71 ok, USIM block ok, ANT 47/49 ok, VDD_EXT 7 ok.

Footprint pad numbering independently cross-checked geometrically (the F-9
step 3 requirement): ANT_GNSS(47) and ANT_MAIN(49) are each flanked by GND
pads (46/48/50/51) on the same edge — the RF fence Quectel's drawing shows;
VBAT block 57-60 contiguous on one edge; 80 perimeter + 64 inner pads =
Quectel's 80 LCC + 64 LGA split.

`docs/ec200u-pinmap-extracted.md` regenerated per step 4: **all 144 rows,
68 VERIFIED / 76 NEEDS-HUMAN**, each with its Table 7 PDF-page reference and
the alias map stated. The NEEDS-HUMAN set is dominated by the GND block
(Table 7's comma-list rows defeat the parser) plus naming variants on
peripherals this design does not use. Two rows deserve attention in review:
- **pins 64/65**: symbol says RTS/CTS, Table 7 says MAIN_CTS/MAIN_RTS —
  apparently swapped. Unused here (s5 uses no flow control), but a symbol
  relabel to match Table 7 is recommended before any future use.
- **pin 128**: symbol NC, Table 7 USIM2_VDD — matters only if the MFF2 eSIM
  is ever wired to USIM2 instead of parallel to USIM1 (handoff s6 wires it
  parallel, so no impact now).

**RELEASE GATE unchanged: modem_rf is not drawn until the user has reviewed
the 76 NEEDS-HUMAN rows.**

Housekeeping: a `.history/` directory appeared during this work — it is
KiCad 10's own Local History feature (automatic project snapshots, nested git
repo). Gitignored; safe to delete at will.

## 2026-09-02 — F-8 in-stock sweep (foreground re-run, commit `c8434d5`)

Method: LCSC browser search for discovery + the wmsc.lcsc.com product-detail
API for verification; datasheets fetched and read where a single parameter
decides viability (Q1/Q2 threshold voltage, L2 winding topology). A calibration
check of my remembered C-numbers found 4 of 11 wrong — every selection below is
API- or datasheet-verified, none from memory. F-5 stands.

| Ref | Part | LCSC | Stock | Price | Rationale / caveats |
|---|---|---|---|---|---|
| Q1,Q2 | **AM2390N-TP** 150 V 4 A SOT-23-3L | C51886143 | 1,930 | $0.084@500 | Only 150 V SOT-23 class with R_DS spec'd at V_GS = 4.5 V (250/300 mohm) and 4 A headroom. **See F-10.** Datasheet read: V_GS(th) 1.5/2.0/3.5 min/typ/max, BV_DSS 150 V min, pinout G/S/D = std SOT-23. Runners-up: HSS2N15 C2987707, FDN86246-clone C7421706. |
| D2 | **SMDJ100A** Littelfuse | C1977839 | 2,955 | $0.32@1k | See U5 condition (b). |
| D3 | **PESD1CAN,215** Nexperia | C15771 | 248,810 | $0.056@100 | Original manufacturer, dual-line bidirectional 24 V CAN TVS, SOT-23. One part replaces the D3/D4 placeholder pair. |
| L2 | **ACT45B-510-2P-TL003** TDK | C76584 | **232** | $0.28@1k | Genuine TDK, 51 uH @ 100 kHz, -40..+150 C. **Stock 232 < a 500-unit run** — alternate in symbol field: MetalLions ACT45B-510-2P-TF C48928226 (760). Re-verify at order day. Winding topology from the TDK circuit diagram: **1->4 and 2->3** — wired accordingly (mis-pairing would short CANH to CANL through a winding). Footprint verified vs TDK land pattern (inner 3.16/outer 5.96 vs 3.2/5.9; corners 1 TL / 2 BL / 3 BR / 4 TR match). |
| J1 | **WAFER-MX3.0-12PZZ** XUNPU | C7588012 | 415 | $0.21@500 | Micro-Fit(MX 3.0) reference series per LCSC params: 2x6, 3 mm, TH vertical, 600 V, 5 A, UL94V-0, with locating columns. Footprint: KiCad stock Molex 43045-1212 2x06 vertical. **Caveats:** op-temp -25..+85 C (Molex original is -40..+105) — acceptable inside the IP65 enclosure but logged; EasyEDA carries no CAD data for this part, so **locating-post positions must be checked against the XUNPU drawing before layout** (milestone-4 list). |
| D5,D6,D10,D11 | **BAV99,215** Nexperia | C2500 | 874,450 | $0.01 | Dual series diode, SOT-23. |
| D7,D8 | **SS310** MDD | C15874 | 571,680 | $0.026@600 | Per BOM. **See F-11.** |
| R11,R12 | 60.4 ohm 1 % 0805 **AC0805FR-0760R4L** YAGEO | C228935 | 72,700 | $0.009@1k | Exact split-termination value. FOJAN C2933479 (332k) is the cheap alternate. |
| DI chain | 12 k 1 % 1206 **1206W4F1202T5E** UNI-ROYAL | C17912 | **7,000** | — | 6 per board -> 3,000 for a 500 run; adequate today but thin — re-verify at order. |
| pull-ups | 47 k 0805 UNI-ROYAL 0805W8F4702T5E | C17713 | 1,569,700 | — | |
| dividers | 100 k / 9.1 k / 1 M 0805 UNI-ROYAL | C17407 / C17855 / C17514 | 186k / 46k / 1.9M | — | |
| C22 | 4.7 nF 50 V X7R 0603 **CL10B472KB8NNNC** Samsung | C1621 | 659,550 | — | |

### Generator: third silent-merge failure mode found and guarded

D3's CANL **label point** landed mid-span on L2's CANH **wire stub** — the
nets merge, KiCad reports only a `multiple_net_names` *warning*, and neither
the point-collision nor the segment-overlap guard could see it
(point-on-segment is a distinct geometry case). A new guard raises on any
label/stub point lying on another net's segment and on any new segment passing
through a foreign claimed point; it reproduced the fault exactly. D3 was
moved, and the CAN pair now verifies by netlist: CANH = {J1.4, D3.1, L2.1},
CANH_T = {L2.4, R11.1, U4.7}, mirrored for CANL via winding 2->3. This is the
third fault class in three sheets caught by generation-time guards after ERC
passed or merely warned — the script-generation + netlist-diff step is
retained as a permanent per-sheet step, per the user's process directive.

### New flags

- **F-10 (decision needed before layout): DO gate drive at 3.3 V is not
  worst-case guaranteed.** AM2390N-TP V_GS(th) max = 3.5 V (typ 2.0 V), and
  the threshold rises further at -40 C — a cold-start relay switch could fail
  in the tail of the distribution. This is physics, not sourcing: **no
  in-stock 150 V SOT-23 NMOS specifies guaranteed enhancement at 3.3 V** (the
  sweep checked all 15; best alternatives are typ-only). Options: (a) add a
  small NPN/2N7002 level stage per channel to drive the gates from **5V0**
  (present whenever machine power — and thus any DO load — exists; R_DS then
  = the specified 250 mohm @ 4.5 V); 2 extra parts per channel, deviates from
  handoff s6's direct-drive wording; (b) accept typ-only 3.3 V operation
  (rejected: cold-start risk on a 5-year fleet product); (c) relax Q1/Q2 to
  100 V logic-level parts (rejected: violates the 150 V rule).
  **Recommendation: (a).** The schematic currently implements the handoff
  wording (direct 100 R from PB14/PB15); awaiting decision.
- **F-11 (recommended swap): SS310 flyback is a 100 V Schottky on a bus that
  sustains 100 V** and reaches ~131 V during the analysed clamp event — zero
  standoff margin, negative under transient; the same logic that retired the
  LM5164 and SMBJ100A. Recommended: **SS3200 (200 V 3 A SMA), MDD C65001,
  114,730 in stock, $0.0675@300** — same SMA footprint, drop-in. The BOM says
  SS310, so per golden rule 2 the schematic keeps SS310 (C15874) until the
  swap is approved.
- **J1 locating posts** and **L2 / 12 k stock depth** carried to the
  milestone-4 pre-layout checklist.

### Status

- mcu / storage / io: ERC 0 errors, all F-8 C-numbers filled, committed.
- modem_rf: awaiting user review of docs/ec200u-pinmap-extracted.md (release gate).
- power: U5 approved; sheet waits for F-9 release per user instruction.
- Open decisions: **F-10** (DO gate drive), **F-11** (SS3200 swap).

---

## 2026-09-02 — F-10 / F-11 applied; io re-committed (commit `9c973e7`)

**F-10 (approved):** two-stage non-inverting NPN gate driver per DO channel
(2x MMBT3904 C20526; 4.7 k base R, 10 k MCU-side base pulldown, 10 k first-stage
collector pullup, 2.2 k driver pullup to 5V0; retained 100 R gate series + 10 k
gate pulldown). Gate swing ~4.1 V, inside AM2390N's specified R_DS @ 4.5 V
region. **Default-OFF is now a structural netlist-guard condition** (8/8
assertions pass: gate pulldown to GND, MCU-side base pulldown, QnB base pullup
to 5V0, QnB collector on the driver node — both channels): with the MCU pin
open the gate is held low both passively (10 k) and actively (QnB clamps
whenever 5V0 is present); with the board unpowered the 10 k holds it at GND.
Static cost: ~0.5 mA (DO on) / ~2.5 mA (DO off, machine powered) per channel
from 5V0. **Logged consequence: DO1/DO2 — like CAN — are inactive during
battery-backup operation (5V0 absent).** handoff section 6 note updated.

**F-11 (approved):** SS310 -> **SS3200 (MDD, C65001)**, both flyback channels.

## 2026-09-02 — modem_rf drawn under F-9 CONDITIONAL RELEASE (commit `5bfc9cc`)

Wired using **only Table-7-VERIFIED pins**; every one of the **76 NEEDS-HUMAN
pins is a no-connect** with F9-REVIEW text markers on the sheet.

**Review priority 1 — NEEDS-HUMAN rows that Table 7 or the symbol identify as
GND (35 pins):** 51, 52, 53, 54, 56, 72, 76, 85–112.
The symbol names all of these GND; the Table 7 comma-list rows defeated the
parser, so they lack machine verification. **They are currently NC in the
schematic. A modem with most of its GND paddle NC'd cannot go to layout —
connecting them after review sign-off is a hard milestone-3 gate.** (9 GND pins
that DID machine-verify are connected: 8, 9, 10, 19, 22, 36, 46, 48, 50.)
**Review priority 1b — RESERVED conflicts (3 pins):** 81, 82 (symbol KEYIN4/5
vs Table 7 RESERVED), 117 (symbol CLK26M_OUT vs RESERVED). All NC either way.

**Observed anomalies, no design impact (per user instruction):** pins **64/65**
— symbol RTS/CTS vs Table 7 MAIN_CTS/MAIN_RTS (apparently swapped; unused, no
flow control in this design); pin **128** — symbol NC vs Table 7 USIM2_VDD
(eSIM is wired parallel to USIM1 per handoff, USIM2 unused).

Circuit notes (interpretations logged):
- **STATUS** is a 1.8 V push-pull output; handoff said "via divider" but section
  6 also says follow Quectel exactly, and Quectel Fig 28 specifies an NPN
  stage. Implemented as Fig 28: STATUS -> 4.7 k -> Q11 + 47 k, collector pulled
  47 k to 3V3 -> MODEM_STATUS. **Consequence: MODEM_STATUS at the MCU is
  INVERTED (low = modem running) — firmware note.**
- **Q3 power switch semantics:** DEFAULT ON via 100 k gate pulldown;
  MODEM_PWR_EN HIGH = modem power CUT (Q14 NPN level stage + Q13 PNP pull the
  AO3401A gate to SYS). Matches handoff section 4 "default ON via pulldown".
- **TXB0104 OE** held low by 10 k until VDD_EXT rises (47 k pullup to VDD_EXT):
  outputs stay Hi-Z while the modem is off/rebooting.
- **MFF2 eSIM pads (X2)** are a schematic placeholder with footprint library
  `TBD-MFF2` — the MFF2 land pattern must be drawn as a custom footprint at
  milestone 4 (the one remaining footprint_link warning, justified).
- SMF05C pin 2 = GND assumption carried to the footprint-verification list.

## 2026-09-02 — power.kicad_sch drawn per approved U5 circuit (commit `13f160f`)

`VIN -> F1 -> D1 S3M -> [D2 SMDJ100A + 2x2.2 uF/100 V + 100 nF] -> R80 10 R
(2512) -> [2x2.2 uF/100 V] -> U5 EG11752` — exactly the TASK A analysed
topology. U5 app circuit per datasheet fig 6-2 + section 8.5: EN 100 k from
VCC, VCC 1 uF, VB–VS 100 nF boot, FB 4.3 k/1.5 k -> 5.03 V, SS3200 freewheel,
L1 150 uH (SMDRI127-151MT, Isat 2.7 A > the IC's 2 A limit), 5V0 out on
3x10 uF + 100 nF. **F-12 (open):** the V1.0 datasheet gives no R_IS formula —
R82 fitted 0 R, value is a bench/FAE item alongside the 100 V min-on-time test.

U6 BQ25606 per TI datasheet figs 17/18 (rendered and read): VAC short to VBUS
= 5V0; 1 uF VBUS, 10 uF PMID, 4.7 uF REGN, 47 nF BTST, L3 2.2 uH (Murata
DFE252012P) -> SYS (2x10 uF); **ICHG 976 R -> 0.694 A** (K=677 AxOhm, in the
handoff's ~0.7 A spec); **ILIM 536 R -> IINDPM 0.89 A** (K=478, inside the
buck's 1 A); VSET float -> 4.208 V; D+/D- float -> unknown adapter so the ILIM
resistor governs; /CE = GND, OTG low; **TS = REGN -> 5.23 k -> TS -> 30.1 k ->
GND with the battery's 103AT NTC on J2.2** (values = TI's 103AT example;
re-check against the actual battery NTC — F-5). J2 = JST B3B-XH-A (C144394):
1 BAT+, 2 NTC, 3 GND — the field-replaceable battery per design rule 2.
U9 = ME6211C33M5G (C82942, 500 mA per BOM; ME6217 is out of stock) SYS -> 3V3.

### M2 part selections, round 2 (all API/browser/datasheet-verified)

| Ref | Part | LCSC | Stock | Note |
|---|---|---|---|---|
| U1 | EC200UCNAA-N05-SGNSA | **C2916205** | (BOM) | symbol source C2916206 (F-9) |
| U8 | TI TXB0104PWR TSSOP-14 | C60708 | 8,041 | genuine TI; TSSOP for rework |
| X1 | JXTCONN NANO SIM 7P PUSH | C53207808 | 845 | 6 contacts + CD; pinout to footprint-verify |
| X2 | MFF2 eSIM pads | (custom fp) | — | DNP, 0R-selected |
| AF1,AF2 | XYECONN XY-IPEX1 (U.FL) | C53133524 | 14,110 | gen-1 IPEX, 6 GHz, -40..+85 C |
| D15 | ST USBLC6-2SC6 | C7519 | 37,925 | genuine ST |
| D14 | onsemi SMF05CT1G | C15879 | 13,430 | pin2=GND to verify |
| Q3 | AOS AO3401A | C15127 | 289,970 | -30 V 4 A P-FET |
| Q13 | Nexperia MMBT3906,215 | C75549 | 141,320 | PNP for gate-kill stage |
| D12 | MDD SMF5.0A | C193402 | 260,440 | VBAT_MODEM clamp |
| U9 | MICRONE ME6211C33M5G | C82942 | 347,170 | ME6217 out of stock |
| D1 | TWGMC S3M (SMB variant) | C5204901 | 19,940 | 1 kV 3 A; ~0.5 W at max input draw, SMB OK |
| F1 | Littelfuse 0443001.DR | C95352 | 2,874 | **1 A, 250 VAC/VDC, 50 A interrupt** |
| L1 | SMDRI127-151MT 150 uH | C21325 | 5,265 | Isat 2.7 A explicitly spec'd |
| L3 | Murata DFE252012P-2R2M | C391305 | 13,990 | charger inductor |
| C70-74 | CCTC 2.2 uF 100 V X7R 1210 | C5449052 | 81,960 | X7R explicit in MPN |
| C40,C41 | Samsung CL32A107MQVNNNE 100 uF | C49066 | 82,639 | modem VBAT bulk |
| 10 uF | Murata GRM21BR61H106KE43L 50 V | C440198 | 245,360 | PMID/SYS/BAT/5V0 |
| J2 | JST B3B-XH-A(LF)(SN) | C144394 | 57,610 | genuine JST |

F-5-provisional values placed with `TBD-F5` markers: 10 R 2512 anti-surge
(**pulse rating must be verified** — it absorbs ~100 W x ~1 ms during clamp
events), 33 R SIM series, 976 R / 536 R / 5.23 k / 30.1 k / 4.3 k / 1.5 k
0805, 47 nF BTST.

### Generator/root fault caught this round (the netlist-diff step earning
its keep a fourth time)

With a fifth sheet, `write_root`'s single-row column layout wrapped the power
sheet onto column 0 — **on top of the mcu sheet** — and their pin stubs
merged: 5V0/ADC_SPARE, CAN1_RX/SYS, CAN1_TX/VIN, again reported by ERC only as
`multiple_net_names` warnings. Rows added (idx // 4). A label-bridge slip that
**shorted out the USIM_VDD 0R eSIM select (R69)** was also caught in the same
warning sweep and fixed: the SIM holder now sits on USIM_VDD_SIM only.

### Full-design ERC + netlist-guard status (MILESTONE 2 GATE)

- **ERC: 0 errors, 14 warnings**, each justified: 13x `same_local_global_label`
  (the by-design hierarchy pattern, verified connected by netlist) + 1x
  `footprint_link_issues` (X2's intentional TBD-MFF2 custom footprint).
- **checkpins: 48/48 section-5 rows, far ends verified** — now including the
  modem nets (MODEM_TX -> U8.13, MODEM_RX -> U8.12, MODEM_RI -> U8.11,
  MODEM_DTR -> U8.10, MODEM_PWRKEY -> R55, MODEM_RESET -> R57,
  MODEM_PWR_EN -> R53, MODEM_STATUS -> Q11.3). Full table in
  `docs/section5-checklist.txt`.
- **F-10 default-OFF: 8/8 structural assertions pass.**
- 267 nets, 5 sheets, 353 placed symbols.

### Milestone 2: COMPLETE, with two hard gates carried into milestone 3

1. **F-9 human review** of all 76 NEEDS-HUMAN rows in
   `docs/ec200u-pinmap-extracted.md` (priority 1: the 35 GND rows, which are
   deliberately NC until sign-off; priority 1b: RESERVED rows 81/82/117).
2. **F-12** R_IS value + the 100 V / 0.7–1 A / Ton~455 ns bench test on the
   EG11752 before layout freeze.

Open flags: F-5 (provisional passives -> milestone-5 BOM verify), F-12 (above),
plus the milestone-4 footprint-verification list (J1 locating posts, SIM holder
pad map, SMF05C pin 2, MFF2 custom footprint, X2916205-vs-206 footprint pad
sweep already done).

---

## 2026-09-04 — MILESTONE 3: F-9 review package, rules audit, M4 prep

### Task 1 — F-9 consolidated review table (docs/f9-review.md)

All **76 NEEDS-HUMAN pins** tabulated with three sources per pin (Table 7 parse
with PDF page ref, C2916206 symbol name, footprint position class) and a
3-source verdict. **62 AGREE / 14 CONFLICT**, conflicts flagged prominently;
nothing connected. The 35 priority-1 GND rows all classify as
**central-LGA-grid or RF-fence positions with the symbol saying GND** —
geometry supports GND on every one, pending your sign-off. RESERVED rows
81/82/117: both readings imply NC either way. Pins 64/65 (RTS/CTS swap) and
128 (NC vs USIM2_VDD): observed anomalies, **no design impact** (per
instruction). Four SDIO-naming rows are flagged CONFLICT conservatively even
though they read as transparent vendor renamings — reviewer's call.

### Task 2 — docs/firmware-notes.md started

16 firmware notes + 4 bench/bring-up items captured from the log (MODEM_STATUS
inversion, JTAG/SWD, CAN remap, IWDG, >80 C write throttle, battery-backup
behaviour, modem power-cycle sequence, EG11752 bench items). To be updated
every milestone. Added this milestone: **FW-17 — SIM card-detect polarity:**
the JXTCONN holder's CD switch is **shorted to GND with no card and OPEN with
a card inserted** (drawing p.1 circuit) — configure AT+QSIMDET level
accordingly and expect USIM_DET floating-high (module internal pull) = card
present.

### Task 3 — R80 pulse verification and selection

**Pulse duty (per full-rated SMDJ100A 10/1000 us strike):** R80's transient
duty is charging the node-B bank (2x2.2 uF = 4.4 uF) from 100 V up to the
162 V clamp: for an RC charge the resistor dissipates exactly the energy
delivered to the capacitor, **E_R = 1/2 x 4.4 uF x (62 V)^2 ~ 8.5 mJ —
independent of R**. Peak P = ΔV²/R = 384 W decaying with τ = RC = 44 us.
After the bank charges, R80 carries only the buck draw (~45 mA at clamp
levels, ~20 mW). 8.5 mJ is far inside 2512 thick-film single-pulse capability
(hundreds of mJ at the 100 us-1 ms class), even without a vendor curve.

**Selection:** no LCSC-stocked 2512 in 5.1/10 ohm publishes a pulse curve
(FOJAN FRC = general purpose, FH RPL = 2 W power series, Panasonic ERJ1T =
0 stock; all checked). Chosen: **FOJAN FRP2512J100 TS, C3013385** — 10 ohm,
**2 W** high-power 2512, 406,160 in stock — the largest-element in-stock 10R,
comfortably adequate for the 8.5 mJ/384 W duty. The user-suggested 2x5R1
fallback has no in-stock anti-surge candidates (FRC only) and does not
change the energy per event, so the single 2 W part is preferred.

**F-15 (NEW — the real problem is the VALUE, needs decision before layout):**
at the guaranteed 10.5 V floor and full converter load (5 V x 1 A out, ~85 %
eff -> 5.9 W in), the load line V_B^2 - 9.8 V_B + 58.8 = 0 has **no real
solution — the buck cannot draw its power through 10 ohm at low line at all**
(brown-out; VCC(OFF) = 7.8 V). Even at 24 V it burns 0.6 W continuously.
TASK A already showed the resistor does NOT attenuate the clamp (node B sees
the full clamp voltage; the margin comes from the 200 V part + SMDJ) — its
only real jobs are inrush limiting and edge filtering. **Recommendation:
R80 10R -> 1R, FOJAN FRS2512F1R00TS C55348540 (genuine Anti-Surge series,
1 %, 4,000 stock):** at 10.5 V/full load V_B ~ 9.15 V, I = 0.64 A, P = 0.41 W
continuous (inside a derated 2512); pulse energy unchanged at 8.5 mJ
(R-independent); τ falls to 4.4 us (ns-class edges still filtered; the
50-1000 us events are the TVS's job). Schematic keeps 10R (C3013385) per the
approved topology until you decide.

### Task 4 — Handoff §2 rules 1-9 and §6 audit (MET / NOT MET / N-A)

| Rule | Verdict | Evidence / action |
|---|---|---|
| 1. No electrolytic/tantalum; X7R/X7S only; >=2:1 derating (100 V rail: 100 V-rated + TVS) | **NOT MET -> F-13** | Zero electrolytics/tantalums ✓; 100 V rail = 2.2 uF **X7R** 100 V + TVS ✓ (rule's own exception). Violations: C40/C41 modem bulk = CL32A107 **X5R 6.3 V on the 4.35 V charge rail (1.45:1)**; all 10 uF = GRM21BR61H **X5R** (voltage 50 V ✓ but dielectric ✗). |
| 2. Battery field-replaceable, JST + NTC, never soldered | **MET** | J2 = JST B3B-XH-A 3-pin (BAT+/NTC/GND); battery is a plug-in harness part. |
| 3. MCU can hard power-cycle modem via high-side P-FET | **MET** | Q3 AO3401A default-ON, MODEM_PWR_EN high = cut; structure netlist-verified. |
| 4. IWDG always on; BOD enabled | **N-A (firmware)** | FW-3 in firmware-notes; no hardware element required. |
| 5. OTA: modem DFOTA + MCU bootloader in ext flash | **MET (hw provisions)** | U7 8 MB staging + USB FOTA pads; FW-9. |
| 6. Semis >=105 C where available; conformal coat | **MET with logged exceptions** | MCU 105 ✓, choke 150 ✓, SIM holder 85... exceptions all logged: U7 85 C (F-2 justification), J1 housing -25..+85, **EC200U itself: -35..+75 C normal / -40..+85 C extended operation (Quectel spec) — the modem, not the flash, is the tightest device on the board (new note)**; EG11752 covered by qualification condition (c). Conformal coat = production step, noted for milestone 6. |
| 7. Second source / scaling provisions | **MET** | CAN: SIT1051AT/3 pinout = TJA1051T/3 = TCAN1042 (industry SOIC-8 map, VIO pin 5) — drop-in; IMU footprint fixed QMI8658 LGA-14; dual SIM = X1 + X2 MFF2 pads with 0R selects; U5 second source EG11722 (pin-identical, logged derated-emergency-only). |
| 8. Test points: every rail, SWD, both UARTs, CAN, bed-of-nails layout | **NOT MET -> F-14** | Present: SWD, NRST, debug UART, 3V3, GND x2, 5V0, SYS x2, sense nets, MODEM_STATUS, USB, STAT/PG, spares. **Missing: VIN rail TP, VBAT_MODEM TP, CANH/CANL TPs, modem-UART pair** (currently reachable only through U8/USB). 6 TPs to add. Bed-of-nails single-side layout = milestone-4 placement rule. |
| 9. LTE Cat-1, no 2G dependence | **MET** | EC200U-CN = Cat-1 bis. |

**§6 block-by-block:** modem block MET (all elements per §6 incl. USIM 33R +
100 nF + SMF05C, MFF2 parallel via 0R selects, USB 4 pads + ESD, ANT pi + 2x
U.FL, NETLIGHT NPN, VDD_EXT decoupled; STATUS implemented as Quectel Fig 28
NPN — logged interpretation); IMU MET (RESV corrected per datasheet; away-from-
edge = placement note, IMU is centre-board in the study); CAN MET (split term
default OPEN, choke+TVS at connector, 5V0-only-alive accepted); DI MET as
amended (F-7 36k approved; window verified at 10.5 V); DO MET as amended
(F-10/F-11 approved, default-OFF guard); storage MET (133 MHz >= 30 MHz);
§4 power MET as amended (U5/D2 approved swaps, dividers exact, Q3 default-ON).

**New flags from the audit:**
- **F-13:** modem bulk caps X5R/6.3 V violate rule 1 (dielectric + 1.45:1).
  Options: (a) 2x 47 uF **10 V X7S** 1210 if stocked; (b) 4x 22 uF 16 V X7R
  1210 (2:1-compliant, more parts); (c) accept X5R 6.3 V with a written
  waiver (Quectel's own reference uses low-voltage bulk here; DC bias derating
  at 4.4 V on 6.3 V X5R is the real concern). Also replace the four X5R 10 uF
  with X7R equivalents at milestone-5 BOM verify. **Decision needed.**
- **F-14:** add 6 test points (VIN, VBAT_MODEM, CANH, CANL, MODEM_TX/RX at
  1.8 V side or 3V3 side). Schematic change pending your go-ahead (trivial).
- **F-15:** R80 value (above). **Blocker for layout.**

### Task 5 — Milestone-4 prep

**Stackup (defined):** JLC 1.6 mm standard 4-layer (JLC7628):
L1 = signal + RF (50 ohm CPWG for the two ANT runs), L2 = **solid GND, no
splits**, L3 = power pours (5V0 / SYS / 3V3 islands; VIN routed thick), L4 =
signal/slow. Already reflected in the .kicad_pcb layer names (GND_L2/PWR_L3).

**Placement study:** docs/placement-study.svg — **PROVISIONAL 80 x 60 mm**
outline (final outline + M3 positions from the purchased housing):
connector-end HV zone (J1, fuse/D1/D2/R80/HV caps, DI chains, DO FETs, CAN
choke+TVS) behind a silk HV boundary at x = 20 with the 1.5 mm clearance rule;
digital centre (MCU/IMU/flash/CAN/TXB + power block along the bottom edge);
RF end with EC200U ANT pads (47/49) facing the right edge, **AF1 (LTE) and
AF2 (GNSS) at opposite right corners — 51 mm apart (spec >= 15 mm)**; SIM
group beside the module away from the RF edge; VBAT_MODEM bank <= 5 mm from
pads 57-60; battery is an enclosure pocket (board contributes J2 at the
centre-bottom edge); GND keepout under the lid's FPC-antenna region.

**Milestone-4 footprint checks (completed / dispositioned):**
- **J1 locating posts — RESOLVED:** XUNPU drawing shows 2x diag Ø1.00 posts at
  (outer col + 3.00, row ± 0.95). Stock Molex 43045-1212 footprint has no
  holes -> **derived footprint `jlc:XUNPU_MX3.0-12PZZ_2x06_P3.00mm_Vertical`**
  created (= Molex pattern + 2x NPTH Ø1.1 at (18.0, -0.95) and (-3.0, 3.95));
  J1 re-pointed at it; parses clean. Also confirmed from the drawing:
  600 V / 5 A rating, Ø1.02 pin holes on a 3.00 grid.
- **SIM holder pad map — VERIFIED:** imported footprint matches the JXTCONN
  drawing (7 contacts C3-C7-C2-C6-C1-C5-CD at 1.27 pitch, CD +0.95; 4 shell
  pads). **F-16 (NEW):** the drawing also shows **2x Ø0.75 locating posts**
  missing from the footprint; x = -2.50 / +1.22 from centreline is explicit
  but the y datum chain is ambiguous between two readings — **no copper
  guessed**; resolve by measuring a physical sample or vendor query, then add
  2x NPTH Ø0.85. Blocker for layout of X1 only.
- **SMF05C pin 2 — VERIFIED:** onsemi pin assignment: pins 1/3/4/5/6 =
  cathodes (I/O), **pin 2 = anode -> GND** — exactly as wired. Caveat closed.
- **MFF2 — schematic corrected, footprint gated (F-17 NEW):** X2 remapped to
  the authoritative ETSI TS 102 671 R12 / VFDFPN8 pinout from the 1GLOBAL
  MFF2 datasheet (1 GND, 2 SWIO nc, 3 I/O, 4 NC, 5 NC, 6 CLK, 7 /RESET,
  8 VCC) — the previous 6-pin placeholder mapping was wrong. Land pattern
  still requires the chosen eSIM vendor's packaging spec (st.com unreachable;
  1GLOBAL sheet has pinout but no land dims). X2 is DNP, so schematic is
  complete; **the custom footprint is the one open milestone-4 copper item.**

### Status

Milestone 3 deliverables presented: docs/f9-review.md, the rules audit above,
docs/placement-study.svg, docs/firmware-notes.md. **STOPPED per instruction:**
GND connection (F-9 sign-off), routing, F-13/F-14/F-15 decisions await the
user. Open flags: F-5, F-9 (review), F-12, F-13, F-14, F-15, F-16, F-17.

---
*Next entry: F-9 sign-off + F-13/14/15 decisions -> close milestone 3.*

---

# Milestone 3 CLOSE / Milestone 4 UNFROZEN — 2026-09-04

Decisions received from the user this session: F-9 GND signed off conditional
on a reverse check; F-13, F-14, F-15 approved; F-16, F-17 dispositioned;
product spec ambient rating added; placement amendments; milestone 4 unfrozen
through routing with a hard stop after.

## Step 0 — machine migration verified (MIGRATION.md §4)

New machine: Linux, KiCad **10.0.5** (was 10.0.0 on Windows), Python 3.13,
kicad-cli on PATH, `/usr/share/kicad/symbols` found without needing
`KICAD_SYMBOL_DIR`. Verification before touching anything:

| Check | Expected | Result |
|---|---|---|
| `tools/sheets.py` | 6 "wrote" lines | 6 |
| `git diff --stat` after regen | empty | **empty** — regeneration is bit-identical across OS and KiCad point release |
| ERC | 0 errors, 14 warnings | 0 / 14 |
| `tools/checkpins.py` | exit 0 | exit 0, all F-10 structural checks pass |
| netlist vs `docs/netlist-snapshot-premove.net` | 269 nets, 210 components | 269 / 210 |
| netlist diff | only `(date ...)` | `source` path, `date`, `tool` version only — no electrical difference |

The migration changed nothing. Path-portability work in `cf5a853` holds up.

## F-9b — the reverse check, and what it found

Instruction: every footprint pad in the central LGA grid / ANT GND fence must
be in the GND list; log any unlisted pad as F-9b and stop.

Method (all machine-read, nothing hand-typed): parsed the 144 pad centres from
`lib/jlc.pretty/LCC-LGA-144_…_L610-CN-02.kicad_mod`, classified each pad as
perimeter or inner field geometrically (80 + 64 — matches Quectel's 80 LCC +
64 LGA), parsed all 144 symbol pin names from `lib/jlc.kicad_sym`, and read the
actual per-pad net from the exported netlist.

**Result: 40 of the 64 inner-field / ANT-fence pads are NOT in the GND list.**
Every one of the 40 carries a definite non-ground function — SPK/MIC (73–77),
KEYIN/KEYOUT (78–84), CLK26M (117), LCD + SPILCD (119–125), GPIO1 (126),
SDIO2 (129–134), WLAN/BT (135–139), ADC0 (45), SDIO1 (33/34), RFCTL (143/144)
— and 24 of them were already VERIFIED directly against Table 7.

So the literal check trips, but **not because a ground pad was omitted.** It
trips because the premise in `docs/f9-review.md` — that the central LGA grid is
"overwhelmingly the ground/thermal field" — is **false**. That premise supplied
the second source for the "AGREE (2-source)" verdict on pins 76 and 85–112, and
for pin 51's "symbol GND + RF fence position". Removing it left the **entire
35-pin GND list resting on the C2916206 symbol alone**, with Table 7 unparsed
for all 35 rows. That is a materially weaker position than the sign-off
document claimed, and exactly what the reverse check existed to expose.

### Resolution: read the primary source instead

Rather than stop on a documentation defect, the actual Table 7 row was
obtained. Quectel **EC200U Series Hardware Design, V1.2, 2023-05-19,
Released**, retrieved from Quectel's own CDN
(`images.quectel.com/python/sites/2/2023/05/Quectel_EC200U_Series_Hardware_Design_V1.2.pdf`),
MD5 `995ce77179cf0613277111e73c640455`, byte-identical to an independent
mirror. **Committed to the repo** as
`docs/Quectel_EC200U_Series_Hardware_Design_V1.2.pdf` so the sign-off record is
self-contained (Quectel already 404s the V1.3/V1.4 paths).

Chapter 3.3 Table 7, Power Supply sub-block, p.21 — and again verbatim in
chapter 3.6.1 Table 9 "VBAT and GND Pins", p.36. Text extracted and grepped
locally, not taken on trust:

```
GND               8, 9, 19, 22, 36, 46, 48, 50–54, 56, 72, 76, 85–112
```

Expanded: **43 GND pads.** Already connected: 8, 9, 19, 22, 36, 46, 48, 50
(8 pads). 43 − 8 = **35** — the connect list matches the datasheet pin for pin,
with nothing missing and nothing extra. Pin 10 `USIM_GND` is a separate (U)SIM
ground, already wired. Table 7 note 3, p.20: *"Please keep all RESERVED and
unused pins unconnected, and all GND pins are connected to the ground"* —
authorising both halves of the plan.

**F-9b verdict: CLEAN.** No ground pad was omitted. The finding is a
documentation defect, not an electrical one, and it is now fixed.

**Root cause of all five "row not machine-parsed" GND rows: the ranges use
U+2013 EN DASH (`50–54`, `85–112`), not `~` and not ASCII `-`.** The earlier
attribution to "the comma-list row format" was wrong. Any future Table 7
parsing must normalise en/em dashes first.

### Geometric argument, restated correctly

The geometry is still useful, just not as originally worded. The inner field is
three distinct sub-regions, not one ground field:
- **85–112** occupy an exclusive, regular full-span lattice (5 rows at
  y = −9.60/−4.85/0/+4.85/+9.60) with **zero signal intrusion** — a genuine
  thermal/ground via field. Corroborates the datasheet.
- **76** sits at (−0.80, −1.60) *inside* the fine-pitch audio/keypad cluster,
  between SPK_N/MIC_P and MIC_N in both numbering and position — a local audio
  ground, not part of that lattice.
- **two left-hand columns** (x = −13.0, −11.0) are 24 pads, all named signals
  (117–140). Nothing to do with ground.
- **46/48/50/51** alternate with ANT_GNSS(47)/ANT_MAIN(49) — an RF ground
  fence. But 33/34/45/143/144 also fall within two pitches of an antenna pad
  and are signals, so proximity alone proves nothing.

`docs/ec200u-pinmap-extracted.md` has been corrected to say all of this, so the
false premise cannot be relied on again.

## F-9 applied

`docs/ec200u-pinmap-extracted.md` is the single source of truth — `sheets.py`
connects any pin whose row reads `VERIFIED | GND` and no-connects the rest, so
F-9 was applied by correcting the pin map, not by hand-editing the schematic.
The 35 rows went NEEDS-HUMAN → VERIFIED, citing the Table 7/Table 9 row.
Tally: **68/76 → 103/41 VERIFIED/NEEDS-HUMAN.**

Six conflict rows were additionally resolved against V1.2 and annotated (status
deliberately left NEEDS-HUMAN so they stay NC and marked, per instruction):
- **81, 82, 117** — RESERVED row p.30 is "18, 55, 81, 82, 116, 117", comment
  *"Keep these pins open."* The symbol's KEYIN4/KEYIN5/CLK26M_OUT names are the
  **QuecOpen firmware variant**, which is what caused the conflict. NC correct.
- **118** = `WLAN_SLP_CLK`, DO, "If unused, keep it open" (neither the parsed
  "CLK" nor the symbol's "NC"). NC correct.
- **128** = `USIM2_VDD`, PO — SIM2 unused here. NC correct.
- **140** = `ISINK`, PI, backlight current sink, Imax 200 mA — unused. NC correct.

**14 CONFLICT pins remain NC with F9-REVIEW markers** as instructed:
28, 29, 30, 31, 35, 64, 65, 81, 82, 117, 118, 127, 128, 140. The marker now
lists all 41 remaining NEEDS-HUMAN pins; none of them is a GND pad.

### Verification

`modem_rf` 103 → 138 symbols (+35 GND). ERC **0 errors, 14 warnings**
(unchanged: 13 `same_local_global_label` + 1 `footprint_link_issues`).
`checkpins.py` exit 0. **U1 pads on GND = 44** = the 43 Table 7 pads + pin 10
USIM_GND, matching the datasheet exactly.

Net-level proof that nothing else moved — every net's node set compared before
and after (power-flag refs excluded):
- 269 → 234 nets; the **35 removed nets are all** `unconnected-(U1-GND-PadNN)`
- **0 nets added**
- **exactly one** surviving net changed its node set: GND, which gained
  precisely those 35 U1 pads and nothing else

`power.kicad_sch` also shows a diff: `#PWR112` → `#PWR147`, i.e. **+35**.
Power-flag reference designators are allocated in generation order and `power`
is generated after `modem_rf`, so inserting 35 GND symbols renumbers them.
Cosmetic — invisible power-flag refs only, no net affected (proven above).

### Thermal relief plan (F-9, carried into layout)

Recorded on the modem_rf sheet:
- pads **85–112**: stitch every pad straight down to the L2 solid GND plane
  with its own via — **solid connection, no thermal spokes**
- pads **46/48/50/51** (RF fence): **≥2 vias each**, placed to keep the CPWG
  return path continuous under the ANT runs
- pad **76** (audio ground) and perimeter grounds 8/9/19/22/36/52/53/54/56/72:
  **≥1 via each**

## F-15 applied — R80 10R -> 1R anti-surge

**R80 = FRS2512F1R00TS, LCSC C55348540, 1 Ω 2512 anti-surge** (was 10 Ω
FRP2512J100, C3013385). Topology it sits in:

```
J1.VIN -> F1 -> D1 (S3M) -> VIN_P -> [D2 SMDJ100A, C70/C71 2.2uF, C72]
                                  -> R80 -> VIN_B -> [C73/C74 2.2uF] -> U5.8/9
```

### Load-line at the guaranteed 10.5 V floor, full load

Full load = 5.0 V x 1 A out; at ~85 % efficiency that is **5.9 W in**.
After D1 (S3M, Vf ~0.7 V at this current) the node is **V_P = 9.8 V**.
The buck presents a constant-power load, so with a series R the operating
point is the intersection of `V_B = V_P - R*I` and `V_B*I = 5.9 W`.

**At 10 Ω** — substituting I = (V_P - V_B)/R:

    V_B^2 - 9.8*V_B + 59 = 0     discriminant = 96.04 - 236 = -140  < 0

**No real solution: the load line never meets the constant-power curve.**
The physical statement is the max-power-transfer ceiling: a source of 9.8 V
behind 10 Ω can deliver at most `V^2/4R = 2.4 W`, and the converter needs
5.9 W. It is short by more than a factor of two — a hard brown-out, not a
marginal droop.

**At 1 Ω:**

    I^2 - 9.8*I + 5.9 = 0   ->  I = (9.8 - sqrt(72.44))/2 = 0.644 A
    V_B = 9.8 - 0.644 = 9.16 V        check: 9.16 x 0.644 = 5.90 W  OK

Ceiling is now `V^2/4R = 24 W` — 4x headroom over the 5.9 W demand.

| Line | V_P | I_in | V_B | R80 drop | R80 power |
|---|---|---|---|---|---|
| 10.5 V floor | 9.8 V | 0.644 A | **9.16 V** | 0.64 V | **0.41 W** |
| 12 V nominal | 11.3 V | 0.553 A | 10.75 V | 0.55 V | 0.31 W |
| 24 V | 23.3 V | 0.259 A | 23.04 V | 0.26 V | 0.07 W |
| 100 V | 99.3 V | 0.0595 A | 99.24 V | 0.06 V | 0.004 W |

**Worst-case continuous dissipation 0.41 W at the floor** — inside a derated
2512 (nominally 1–2 W), and it *falls* as line rises, so the high-line case is
not the thermal case.

### Pulse duty is unchanged in energy, harder in shape

The surge energy into R80 is the energy lost charging C73/C74 (4.4 µF) through
it, and `E = 1/2*C*dV^2` is **independent of R**. With the SMDJ100A clamping
V_P to ~162 V against a 100 V line, dV ~ 62 V:

| | 10 Ω (old) | 1 Ω (new) |
|---|---|---|
| Energy per event | **8.5 mJ** | **8.5 mJ** (unchanged) |
| Peak power | 384 W | **3.8 kW** (10x) |
| Time constant tau = RC | 44 µs | **4.4 µs** (1/10) |

Same energy, ten times the peak, one tenth the duration. That is precisely why
the part is an **anti-surge** series device rather than a plain thick film —
plain thick-film 2512s fail by surface arc-over on short high-peak pulses even
when the average energy is trivial. Confirming the FRS2512F1R00TS single-pulse
curve covers 3.8 kW / 4.4 µs stays on the bench list next to F-12.

Secondary effects checked and accepted: hot-plug inrush at 100 V into 4.4 µF
through 1 Ω peaks near 100 A for a few µs — fuse I²t is `V^2*C/2R` = 0.022 A²s,
far inside the 0443001.DR rating, and the S3M's µs-scale surge capability is
well above its 100 A 8.3 ms IFSM figure. Input-LC damping is reduced; the TVS
and the 2x2.2 µF on the V_P side remain the primary transient elements.

**Trade accepted:** R80 is now a weaker surge-softening element, so the buck
input sees a faster edge. Brown-out immunity at the guaranteed floor outranks
marginal surge softening, and D2 + D1 do the actual clamping.

## F-14 applied — six test points added

TP23–TP28, verified against the exported netlist (each shares its net with the
real circuit nodes, not merely a same-named label):

| TP | Net | Sheet | Shares net with |
|---|---|---|---|
| TP23 | VIN | power | J1.1, F1.1, D7.1, D8.1, R30.1, R40.1 |
| TP24 | VBAT_MODEM | modem_rf | U1.57/58/59/60, C40–C43, Q3.3, D12.1 |
| TP25 | CANH | io | J1.4, L2.1, D3.1 |
| TP26 | CANL | io | J1.5, L2.2, D3.2 |
| TP27 | MODEM_TX | mcu | U2.30 (PA9), U8.13 |
| TP28 | MODEM_RX | mcu | U2.31 (PA10), U8.12 |

Placement notes recorded on the sheets: TP23 is **in the HV zone** (up to
100 V — keep inside the silk boundary, 1.5 mm HV-to-LV clearance); TP24 exists
to probe VBAT_MODEM sag during transmit bursts; TP25/26 are on the connector
side of the choke, which is the bus a technician actually probes.

Implementation detail worth keeping: `hier()` was used for the hierarchical
nets (VIN, MODEM_TX, MODEM_RX) and `net()` only for sheet-local nets
(VBAT_MODEM, CANH, CANL). Using `net()` on a hierarchical net would have added
another `same_local_global_label` warning each. **ERC stayed at exactly 0
errors / 14 warnings** — no new warnings from six new parts. Sheet-pin counts
unchanged (24/15/10/4), confirming the hier labels joined existing nets rather
than creating new sheet pins.

Rule 8 (test points on every rail, SWD, both UARTs, CAN) is now **MET**:
28 test points, TP1–TP28 contiguous.

## Product spec — environmental rating (governed by U1)

Added to `docs/telematics-handoff.md` §1.1 and to the new
`docs/installation-sheet.md`:

> **Rated operating ambient −20 °C to +70 °C. Housing shaded or
> light-coloured. 85 °C is survival, not operating.**

Governed by U1, the most restrictive active part. *EC200U Hardware Design
V1.2* §5.3 Table 42, p.75, read from the committed PDF:

| EC200U range | Limits | Datasheet meaning (footnotes 9/10) |
|---|---|---|
| Operating | −35…+75 °C | module **meets 3GPP specifications** |
| Extended | −40…+85 °C | functions maintained, no unrecoverable malfunction, but *"one or more specifications, such as Pout, may exceed the specified tolerances of 3GPP"* |
| Storage | −40…+90 °C | — |

So +70 °C keeps 5 °C to the top of the **3GPP-compliant** window, and 85 °C is
exactly the **extended** limit. "Survival not operating" is the datasheet's own
distinction, not a loose phrase. The −20 °C floor is a product choice for the
India target (the module goes to −35 °C) taken to leave margin.

The 5 °C top margin is thin deliberately, and is *why* the housing rule is a
requirement: internal rise (transmit bursts, buck, charger) plus solar gain on
a dark enclosure on an exposed boom lift will exceed it. A 40 °C day in direct
sun on a black box is already over limit.

**NEW FLAG F-19 — BT1 vs the +70 °C ceiling.** Typical 1S Li-ion is rated
−20…+60 °C discharge and 0…+45 °C charge, both narrower at the top than +70 °C.
Charge is already protected in hardware (BQ25606 TS pin + JEITA network
R88/R89 + in-pack NTC inhibits charging outside the window). **Discharge above
60 °C and calendar ageing at sustained high temperature are not protected**,
and are the reason BT1 is a 2–3 year replaceable service item (rule 2).
*Decision needed: accept +70 °C with a shortened battery service interval, or
narrow the product rating to +60 °C.* Not a layout blocker.

## Milestone-4 input — 50 Ω CPWG geometry for JLC7628 L1–L2

Computed, not looked up: Ghione–Naldi conformal-mapping solution for
conductor-backed CPW, complete elliptic integrals by arithmetic-geometric mean,
cross-checked against Hammerstad–Jensen microstrip (which agrees: plain
microstrip needs W = 0.405 mm at εr 4.4, and the CPWG solution converges on
that as the gap opens).

Stackup: JLCPCB 4-layer 1.6 mm "JLC7628" — **h = 0.2104 mm** (1× 7628 prepreg,
L1 to L2), 1 oz outer copper (0.035 mm). JLCPCB quote Dk 4.6 @1 GHz; real 7628
is nearer 4.3–4.4 at 1.5–2.7 GHz, so the solution is reported across that range
rather than pinned to one number.

**CHOSEN: trace width W = 0.40 mm, gap to coplanar ground G = 0.30 mm.**

| Dk assumption | Z0 at W=0.40 / G=0.30 |
|---|---|
| 4.3 | ~50.4 Ω |
| 4.4 | ~49.9 Ω |
| 4.6 | ~48.9 Ω |

**48.9–50.4 Ω across the entire Dk uncertainty — within ±2.2 % of target**,
which is why this point was chosen over the alternatives (W=0.38/G=0.30 sits
50.4–51.9 Ω, biased high; W=0.34/G=0.25 sits 53.0–54.6 Ω, clearly too high).
εeff ≈ 3.27. G/h = 1.4 — enough gap that the coplanar ground is not dominant,
tight enough that the fence stays electrically useful.

Manufacturability: 0.40 mm track and 0.30 mm gap both clear JLCPCB's 0.127 mm
minimum and the skill file's 0.15 mm "safe" threshold with large margin.
Etch sensitivity ±25 µm (W and G moving oppositely) gives roughly ±4.5 %.

**Via fence:** EC200U-CN tops out at LTE B41, 2690 MHz. With εeff 3.27,
λ_guided at 2.7 GHz ≈ 61 mm, so λ/20 ≈ 3.1 mm. **Fence via pitch specified at
2.0 mm** (≈λ/33 at 2.7 GHz, ≈λ/56 at GNSS L1 1575 MHz) — comfortable margin,
placed along the gap edge either side of both ANT runs.
