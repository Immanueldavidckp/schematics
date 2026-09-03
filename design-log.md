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
*Next entry: pin-map review release / modem_rf, or F-10/F-11 decisions.*
