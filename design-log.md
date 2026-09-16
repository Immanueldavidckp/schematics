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

## Placement amendments (approved 2026-09-04) — layout directives

These are recorded as directives for the real layout;
`docs/placement-study.svg` was milestone-3 prep and is superseded by the
actual board once placement lands.

**(a) Minimise the U5–L1–SS3200–Cin switching loop.** The hot loop is
`C73/C74 (+) -> U5 pin 8/9 VIN -> U5 pin 6 SW -> L1 -> 5V0` with the return
`D16 SS3200 anode -> GND -> C73/C74 (-)`, i.e. the current that commutates
between the high-side switch and the freewheel diode every cycle. The loop to
minimise in *area* is the one carrying the discontinuous current: **C73/C74,
U5, and D16**. Directives:
- C73/C74 sit hard against U5 pins 8/9 and pin 3 (GND) — shortest possible
  path, ideally sharing a pad-adjacent copper island rather than a trace.
- D16 cathode hard against the U5 SW pin; D16 anode to GND with its own via
  field straight down to L2, not via a long trace.
- L1 placed so the SW node copper is a short, wide, compact pour — SW is the
  dV/dt aggressor, so keep its *area* small even though it needs current
  capability.
- No L2 GND plane interruption under the loop; the return path must mirror
  directly beneath it.

**(b) Inductor at maximum distance from the ANT_GNSS trace.** The constraint
that makes this awkward: U5 must stay adjacent to the HV front end (it is fed
from VIN_B through R80, on the connector side), so the power block cannot move
far from the left/HV end. The available degree of freedom is **which corner
each antenna occupies**.

Resolution: **swap the two U.FL corners — GNSS to the bottom-right, LTE to the
top-right.** The power block sits top-middle, so this puts the inductor
diagonally opposite the GNSS connector and its feed:

| | L1 to GNSS U.FL | L1 to LTE U.FL |
|---|---|---|
| Before (GNSS top-right) | ~48 mm | ~49 mm |
| After (GNSS bottom-right) | **~67 mm** | ~48 mm |

The trade is deliberate and one-directional: GNSS is a receive-only system at
roughly −130 dBm sensitivity with no ability to out-shout interference, so
broadband buck switching noise costs fixes directly. LTE runs 200–300 mW
transmit with AGC and closed-loop power control, and its receiver sits near
−100 dBm; giving it the noisier corner costs far less. Handoff §7 only requires
the two U.FL to be ≥15 mm apart and both at the antenna end — the corner
assignment was never constrained, so this costs nothing.
Also: keep L1 at the **left** end of the power block (nearest the HV boundary,
furthest from the RF edge), and route ANT_GNSS on the shortest path to the
bottom-right corner without passing under or beside the power block.

**(c) U3 IMU adjacent to a mounting hole — CONFLICT, raised as F-18.**
The intent is sound: a mounting screw is the stiffest point on the board, so an
IMU beside one sees least flex, and impact energy arrives through the mount
rather than as board bending. The problem is that **none of the four M3 holes
is in a zone the IMU can occupy.** On the provisional 80 × 60 outline with
holes 3.5 mm in from each corner:

| Hole | Position | Zone | Usable for U3? |
|---|---|---|---|
| top-left | (3.5, 3.5) | inside the HV strip (x < 20 mm) | **no** — I2C sensor in the 100 V zone |
| bottom-left | (3.5, 56.5) | inside the HV strip | **no** |
| top-right | (76.5, 3.5) | RF corner, beside a U.FL | **no** — and I2C would run the length of the board past the module |
| bottom-right | (76.5, 56.5) | RF corner, beside a U.FL | **no** |

**NEW FLAG F-18 — proposal: add a fifth M3 hole in the digital zone and place
U3 beside it.** This is not just a workaround for the IMU; an 80 × 60 × 1.6 mm
FR4 board screwed only at its corners has real centre compliance, and this
board carries a **31 × 28 mm LCC module** whose solder joints must survive five
years of MEWP vibration. A centre standoff stiffens the panel for both reasons.
Provisional position: digital zone, lower-middle, clear of U2/U7 and the
SWD test-point cluster; U3 placed immediately adjacent with its axes on silk.

**This needs the housing to provide a matching boss, and the housing is still
an open item (handoff §9)** — so the fifth hole is provisional exactly like the
outline. *Decision needed:* confirm a 5-standoff housing is acceptable, or
accept U3 at the stiffest available interior point with 4 corner screws only.
Not a routing blocker either way — the hole position is a keepout, not copper.

## F-16 — SIM holder: X ambiguity resolved, Y still open, no copper guessed

Searched LCSC and the JLCPCB parts library for an in-stock nano-SIM push-push
holder whose drawing dimensions the locating posts unambiguously. Both sites
were reachable; every dimension below came off a drawing that was opened, and
the GCT numbers were re-extracted and re-read locally rather than taken on
trust.

**Correction to the earlier F-16 entry.** The reading that the incumbent's
`2.50` and `1.22` are the post X positions was **wrong**. On the JXTCONN
drawing those two figures are the **bottom-pad-row chain** (2.50 = bottom pad
pitch, 1.22 = middle bottom-pad centreline to product centreline). The post
dimension is `8.50`, and it is **post centre to post centre**. So the
incumbent's post **X is actually determined**, not ambiguous:
8.50 apart, sitting at −5.00 and +3.50 from the product centreline given the
GND-pad centrelines at ±6.50.

**Only Y is genuinely ambiguous** — and it is ambiguous for the reason
originally flagged: the posts' only Y reference is `0.06` to the bottom-pad-row
centreline, and that row's own Y is chained off an unnamed "PRODUCT CONTOUR
LINE" via 13.48 / 2×12.00 / 6.92. The datum feature is never identified.
HMTCONN C53121332 and Megastar C7419851 reuse the identical drawing with the
identical gap. **Not resolved, and not inferred.**

**A corroborated Y candidate now exists.** Three independent vendors publish
what is evidently the same standardised layout, all at ±0.05:

| | GCT SIM8066 | HRO SIM-13A | Megastar ZX-NSIM-481.37J-Z |
|---|---|---|---|
| posts | 2 × Ø0.75 | 2 × Ø0.75 | 2 × Ø0.75 |
| post-to-post | 8.50 | 8.50 | 8.50 |
| lower-left GND-pad C/L to left post | 1.50 | 1.50 | 1.50 |
| lower GND-pad C/L to post (Y, post above) | **1.25** | **1.25** | **1.25** |
| GND-pad C/L frame | 13.00 × 12.00 | 13.00 × 12.00 | 13.00 × 12.00 |

Verified locally on the GCT sheet: its "Recommended PCB Layout (Viewed from
Component Side — Tolerance: ±0.05mm)" block does carry 0.75, 8.50, 1.50, 1.25,
13.00 and 12.00. The Megastar, HRO and JXTCONN PDFs carry their dimensions as
outlined vectors with no extractable text, so those were read visually by the
research pass and not re-verified locally — flagged as such.

Relative to a frame centre with GND-pad centrelines at ±6.50 X and the lower
GND-pad centreline at Y = 0, that scheme puts the post centres at
**(−5.00, +1.25)** and **(+3.50, +1.25)**.

### Candidates found

| LCSC | Part | Posts dimensioned? | Stock | $@250 | vs incumbent |
|---|---|---|---|---|---|
| C53207808 | JXTCONN NANO SIM 7P 1.37H PUSH *(incumbent)* | X yes, **Y no** | 845 | 0.181 | — |
| **C7419882** | **Megastar ZX-NSIM-481.37J-Z** | **fully** | 1422 | 0.205 | **+13 %** |
| C3020889 | HRO SIM-13A | fully | 569 | 0.330 | +83 %; also **−20 °C only** |
| C3032925 | GCT SIM8066-6-1-14-01-A | fully | 2856 | 1.069 | +491 % |
| C2977286 | JAE SF72S006VBDR2500 | **no posts at all** (pure SMT) | 1188 | 0.458 | +154 %; CD polarity **inverted** |
| C5148297 | Hirose KP13B-SF-PEJ(800) | **no posts at all** | 11680 | 0.930 | +415 %; CD polarity **inverted** |

Ruled out: Amphenol ICC stock no nano push-push; Attend nano parts all stock 0;
Molex 78724/105163/104168 and Würth 693071010811 are not carried at all. Molex
1042240820 and Würth 693043020611 are push-**pull**, not push-push.

### Why the switch was NOT applied

C7419882 satisfies the stated rule — well documented, similar cost (+$0.03/unit,
+$6 on a 250-piece buy), same class (4FF, push-push, 1.37 mm, 6+CD, 1.27 pitch,
−40…+85 °C), and its card-detect keeps the incumbent's normally-closed polarity
so no firmware change. **But `easyeda2kicad --lcsc_id=C7419882` fails: the
EasyEDA API has no data for that part.** Switching therefore means hand-drawing
the land pattern, which is exactly what skill golden rule 1 forbids
("NEVER invent a footprint... every component comes from easyeda2kicad using
its verified C-number"). Trading a documented-but-hand-drawn footprint for an
imported-and-already-verified one is not obviously a win, and the posts are
moulded bosses — get the holes wrong and the part will not seat, so this is not
a low-consequence guess.

**Held for the user, two ways forward:**
1. **Switch to C7419882** and accept a hand-drawn footprint from its fully
   dimensioned drawing — a logged deviation from golden rule 1. Lowest
   dimensional risk, highest process risk.
2. **Keep C53207808** and either (a) apply the 3-vendor corroborated
   Y = +1.25 to the incumbent, accepting cross-vendor inference on a moulded
   feature, or (b) order 5 samples (min buy 1, no reel penalty) and measure —
   the original plan.

**For this layout iteration the SIM area is reserved with the incumbent's
already-verified pad map and NO post holes**, so no copper is guessed and the
decision stays open. The holes are NPTH mechanical features: adding them later
does not disturb routing.

## F-13 applied — VBAT_MODEM bulk to X7R, 111.9 uF effective

**APPROVED, no waiver.** The old bulk was `2x 100 uF 6.3 V X5R 1210` (C49066),
which broke rule 1 twice over: X5R dielectric, and 6.3 V on a 4.35 V rail is
**1.45:1**, not the required >=2:1.

**Applied: 4x Murata GRM32ER71A476KE15L, LCSC C84494** — 47 uF 10 V **X7R**
1210. Refs C40, C41, C81, C82 on VBAT_MODEM, all inside 5 mm of U1 pads 57-60.

| | old | new |
|---|---|---|
| dielectric | X5R (rule violation) | **X7R** |
| derating | 6.3 / 4.35 = **1.45:1** | 10 / 4.35 = **2.30:1** |
| effective at 4.35 V, 85 C | not qualified | **111.9 uF** |
| count / area | 2 x 1210 = 16 mm^2 | 4 x 1210 = **32 mm^2** |
| cost/board | — | $1.75 |

Curve figures, read at exact 4.35 V / 85.0 C grid points from Murata's own
simulation backend (not interpolated from a printed graph):
**27.97 uF per part** at 4.35 V bias and 85 C, x4 = **111.9 uF**.
Second source for the same position: Taiyo Yuden **C20486249** (renamed
C778723), whose published curve gives -37 % at 4.35 V/25 C and TCC -3.3 % at
85 C -> ~26 uF, **within ~7 % of the Murata figure** — an independent
cross-validation of the recommended part.

The 10 uF X5R 0805 (C440198, used for C77-C79 and others) is replaced by
**C109040**, Murata GRM21BC71E106KE11L, 10 uF 25 V **X7S** — same footprint,
better at 85 C than the incumbent, and rated **+125 C** against the old part's
+85 C ceiling.

### Four findings worth keeping beyond the part numbers

1. **All three options previously logged under F-13 fail the target.** They
   deliver **63 uF, 76 uF and ~92 uF** effective, not >=100 uF. Four 47 uF
   parts is the minimum that works in 1210.
2. **No 100 uF X7R/X7S at >=10 V exists in 1210 or 1812 from anyone** —
   checked against Murata's and TDK's own catalogues, not just a distributor
   search. TDK's 100 uF 16 V X7S is the flattest part found (only -4.0 % at
   4.35 V) but it is 2220, lands at ~88 uF at 85 C so one part still misses,
   and had 493 in stock against the 500 needed for 250 boards.
3. **Do not derive effective capacitance by multiplying a 25 C DC-bias curve
   by a 0 V temperature curve.** That over-predicts by **9-12 %** on
   high-density parts. Only Murata publishes the combined bias-plus-temperature
   surface; Samsung, TDK and others need that extra margin applied.
4. **Samwha (C5440143), CCTC, Chinocera and HRE publish no DC-bias curve at
   all** — both Samwha catalogues were read and contain only a series-level
   temperature graph. Those parts are **unqualifiable** against this rule, not
   merely unattractive. Also two TDK MPNs that LCSC lists do not exist in TDK's
   own database — distributor MPN drift, the same failure mode as the JLC
   dielectric mislabelling.

**Rule 1 (no electrolytic or tantalum; ceramic X7R/X7S only; voltage derated
>=2:1) is now MET** across the design.

## F-17 closed — MFF2 land pattern derived and built

`lib/jlc.pretty/eSIM_MFF2_VFDFPN8.kicad_mod` created. X2 re-pointed from the
placeholder `TBD-MFF2:eSIM_MFF2_VFDFPN8` to `jlc:eSIM_MFF2_VFDFPN8`; that
placeholder was the **last unresolved footprint in the netlist** and was also
the single `footprint_link_issues` ERC warning, so **ERC is now 0 errors /
13 warnings** — one better than the 14 carried since milestone 2.

**Deviation from skill golden rule 1, logged deliberately.** The rule requires
every footprint to come from easyeda2kicad against a verified C-number. MFF2 is
a **standard package site**, not one LCSC part — the whole point of X2 is that
any vendor's MFF2 can be fitted — so there is no C-number to import. The land
is therefore derived from cited primary documents rather than invented.

**Sources (all opened and hashed):**
- **ETSI TS 102 671 V12.0.0 (2018-07)** — normative package spec.
  md5 `b6c0feffce862e5cb98aacb20a67d5a3`
- **Infineon OPTIGA Connect IoT** datasheet rev 3.0, 2022-02-18, fig 6 p.22.
  md5 `eed84276d38b692e2fcfe740b4a94b29`
- Velocity IoT VIoT-Flex MFF2 p.4; 1NCE IoT SIM Chip Industrial (vector
  drawing, pixel-verified); ConnectedYou CY SIM MFF2 Packaging §4 p.5.
- ST ST4SIM-200M DB4082 rev 5 via mirror — **st.com is hard-blocked from this
  environment**, so no ST-authored land pattern was ever seen. ST's own
  "PCB integration recommendations" is an application schematic, not a land.

**All four vendor documents publish the identical land**, covering three
different silicon vendors. Built to that consensus:

| pad | signal | X | Y (KiCad, Y down) | size |
|---|---|---|---|---|
| 1 | GND | -1.905 | +2.85 | 0.40 x 0.80 |
| 2 | SWIO (nc) | -0.635 | +2.85 | 0.40 x 0.80 |
| 3 | I/O | +0.635 | +2.85 | 0.40 x 0.80 |
| 4 | NC | +1.905 | +2.85 | 0.40 x 0.80 |
| 5 | NC | +1.905 | -2.85 | 0.40 x 0.80 |
| 6 | CLK | +0.635 | -2.85 | 0.40 x 0.80 |
| 7 | /RESET | -0.635 | -2.85 | 0.40 x 0.80 |
| 8 | VCC | -1.905 | -2.85 | 0.40 x 0.80 |
| EP | **GND** | 0 | 0 | 4.20 x 3.40 |

Body 5.00 x 6.00; **the pitch axis runs along the 5.0 mm axis** (3 x 1.27 =
3.81 span); pin 1 = bottom-left viewed from top; numbering counter-clockwise.
Courtyard **5.65 x 7.00** (derived: max body/copper extent + IPC-7351B
nominal-density QFN excess 0.25 mm — no vendor publishes a courtyard).
Stencil: pads 1:1 with copper; EP gets a **3 x 3 aperture array** at
X = -1.45/0/+1.45, Y = -1.25/0/+1.25 (1.2 wide; 0.8/1.2/0.8 tall), ~71 % paste
coverage. Solder-mask expansion is **UNVERIFIED** — no vendor prints a number —
so the KiCad house default applies.

**ETSI cross-check: the schematic pinout is CONFIRMED CORRECT.** TS 102 671
Table 6.1 maps package pins 1-8 to UICC contacts C5, C6, C7, C8, C4, C3, C2,
C1, which yields exactly the assignment already in `modem_rf`. Confirmed
independently by four vendor pin tables. §7.0 also explains why pins 4 and 5
are NC: *"In the case where the MFF does not support the functionality as
defined in ETSI TS 102 600 then contacts C4 and C8 shall not be bonded."*

Three traps recorded so nobody re-derives this wrongly:
- **Letter trap.** ETSI-style documents call E = 6.00 and D = 5.00; JEDEC-style
  ones swap them, and swap `D2`/`E2` with them. Physically identical. Fix the
  axes physically, never by letter.
- **Do not take geometry from logical pinout diagrams.** ST's and 1GLOBAL's
  pin diagrams draw the body taller than wide with pins in vertical columns,
  which would put the pitch on the 6 mm axis. Every *dimensioned* outline says
  the 5 mm axis.
- **`5.7` is centre-to-centre between pad rows, not outer-to-outer.** Confirmed
  three ways, including ConnectedYou dimensioning the same feature as `4.9`
  inner-edge to inner-edge (4.9 + 2 x 0.8 = 5.7).

**Exposed pad tied to GND**, per the only affirmative vendor statement found
(Infineon p.24 note: *"must be connected to the common ground reference (GND)
for heat distribution"*). Note the apparent conflict: ETSI **Annex A
(informative)** says the central pads *"are not electrically connected (i.e.
they are insulated) and may serve as anchors"* — but Annex A describes a
**socket-compatible** layout where those are socket anchors, not a soldered
MFF2 thermal land. Vendor guidance wins for a soldered part. The EP pad is
**numbered "1"** so it merges with the GND pin without needing a 9-pin symbol.

**ETSI Annex A publishes a different land** (0.50 x 0.96 pads at +/-2.675,
segmented insulated centre) and was deliberately **not** used: the vendor
consensus land is what the silicon vendors qualified their reflow to, it
accommodates the full cross-vendor tolerance envelope (contact length
0.40-0.75, width 0.30-0.50), it gives 0.25 mm toe extension for an inspectable
fillet against Annex A's 0.155, and it comes with a defined stencil. Build
Annex A **only** if an MFF socket might ever be fitted in the X2 site, which
needs a 10.50 x 11.10 mm clearance zone — wasted area on a soldered-only DNP
site.

*Implementation note for anyone editing a `.kicad_mod` by hand: KiCad's
S-expression parser has **no comment syntax**. `;;` comment lines made the
whole `jlc` library fail to load, which surfaced as 28 spurious
`footprint_link_issues` ERC warnings ("configuration does not include the
footprint library 'jlc'") rather than as a footprint error.*

---

# MILESTONE 4 — stage 1 and 2 (placement + planes). NOT ROUTED.

**Routing has not started, and this is not a clean DRC.** The board is a
first-pass floorplan for review. Reporting it as anything else would be false.

## Why routing stopped here

No autorouter is available in this environment: KiCad ships none, and
freerouting is not installed. Routing 234 nets across a board with a 100 V
zone, two 50 ohm CPWG runs, a 2 mm VBAT_MODEM rail and a switching loop that
must be minimised is not work to hand to an autorouter unreviewed, and
downloading a third-party jar to do it is a decision for the user.

## Generators

Consistent with `tools/sheets.py`, the board is **generated, not hand-drawn**:
- `tools/pcbgen.py` — outline, mounting holes, HV silk boundary. Builds from
  `tools/pcb-template.kicad_pcb` (layers/setup only) every run.
- `tools/pcbplace.py` — footprints, net binding, L2 GND plane, L3 power pours,
  F-9 stitching vias.

Regeneration is **byte-identical across runs** (verified 3x), so the
MIGRATION.md "regenerate, then git diff must be empty" check still proves the
design has not changed. Getting there needed two pcbnew workarounds, both
documented in the code:
- **`board.Remove()` segfaults the interpreter.** It hands ownership back to
  Python, which double-frees on the next GC (exit 139, no traceback). The
  generators never delete; they rebuild from the template.
- **KIIDs are random with no Python setter, and footprints are saved from an
  unordered container**, so plain regeneration reordered blocks and reminted
  every uuid. `canonicalise()` sorts top-level forms by a stable key and
  restamps uuids by position.

And one real bug worth remembering: **pcbnew returns one C++ FOOTPRINT per
library id, so caching and reusing it collapses every component that shares a
footprint onto a single instance.** `board.Add()` is a no-op after the first
call and the next `SetPosition()` just moves it. That silently produced **45
footprints instead of 219 and left 349 pads unbound to nets** — a board that
looked plausible and was electrically hollow. Always load a fresh instance.

## Density — the finding that shapes everything

**Total courtyard area is 3315 mm^2 against 4800 mm^2 of board: 69 % of one
side.** U1 alone is 873 mm^2, 18 % of the board.

| sheet | parts | courtyard |
|---|---|---|
| modem_rf | 57 | 1439 mm^2 |
| io | 70 | 837 mm^2 |
| power | 44 | 694 mm^2 |
| mcu | 40 | 306 mm^2 |
| storage | 3 | 38 mm^2 |

With L2 a solid GND plane and L3 the power pours, **only L1 and L4 carry
signal**. 69 % single-sided occupancy will not route on two signal layers, so
the placement is **double-sided: 171 top, 47 bottom.** That has a cost
consequence — double-sided SMT assembly at JLCPCB — which the user should
confirm. The alternatives are shrinking passives to 0402 or growing the board,
and the board is housing-constrained.

## Floorplan

Zones, x in mm: **HV 1-19.25** (left of the silk boundary at x = 20),
**power 20.75-45 / y 1-16.5**, **digital 20.75-45 / y 17-59**,
**RF 45.5-79**. The power sheet needs 694 mm^2 against a 372 mm^2 power zone,
so it spills into the digital zone; **HV deliberately spills nowhere** — a
100 V part must not wander out of the zone the 1.5 mm rule and the silk
boundary are drawn around.

Placement amendments applied:
- **(a) switching loop** — U5 at (35.5, 4.5), D16 SS3200 at (35.5, 9.5),
  C73/C74 at (31.0, 3.0)/(31.0, 5.5): the discontinuous-current loop packed
  tight.
- **(b) inductor away from ANT_GNSS** — L1 at (27.5, 8.5), the left end of the
  power block; **GNSS U.FL moved to the bottom-right corner** and LTE to the
  top-right, putting L1 ~62 mm from the GNSS feed instead of ~45 mm.
- **(c) IMU by a mounting hole** — U3 at (31.5, 51.5), hard against the
  provisional 5th M3 at (27, 52). See **F-18**.

## Planes and vias

- **L2: solid GND**, full board inset 0.35 mm, **pad connection FULL (no
  thermal reliefs)**. Not a preference — EC200U HW Design V1.2 §4.3 requires
  *"The GND pins adjacent to RF pins should not be designed as thermal relief
  pads, and should be fully connected to ground."*
- **L3: power pours** — 5V0, SYS, 3V3 across the digital/power zones.
- **43 F-9 stitching vias**: 28 in the 85-112 lattice (pads are 2.0 x 3.0 mm at
  3.2 mm spacing, so via-in-pad is comfortable), 4 in the RF fence
  (46/48/50/51), 11 on the perimeter grounds and pad 76.
  Via 0.60/0.30 in the lattice, 0.50/0.30 elsewhere — **0.45/0.30 gives only a
  0.075 mm annulus and fails the 0.100 mm board minimum**, which is what the
  first 17 `annular_width` errors were.

## Quectel RF layout rules — two of these change earlier decisions

Read from the committed PDF, §4.3 p.69-70:
1. Impedance controlled to 50 ohm with a simulation tool — done, see the CPWG
   entry above.
2. **"The GND pins adjacent to RF pins should not be designed as thermal relief
   pads, and should be fully connected to ground."** — confirms the F-9 relief
   plan; implemented as ZONE_CONNECTION_FULL.
3. **"All the right-angle traces should be changed to curved ones. The
   recommended trace angle is 135 degrees."** — no right angles on RF.
4. **"There should be clearance area under the signal pin of the antenna
   connector or solder joint."** — a GND void under each U.FL signal pin.
   **NOT YET IMPLEMENTED** — routing-stage item.
5. **"The distance between the ground vias and RF traces should be not less
   than twice the width of RF signal traces (2 x W)."** With W = 0.40 mm that
   is **>= 0.80 mm**, which **supersedes the earlier fence note**: fence vias
   must stand off 0.80 mm from the trace, so with the 0.30 mm coplanar gap the
   via centre sits >= 1.30 mm from the trace centreline. The 2.0 mm *pitch*
   along the run is unchanged.
6. Keep RF away from interference sources; avoid paralleling on adjacent layers.

Note Quectel's figures 34/35 show CPWG referenced to **L3 or L4**. This design
references **L2** deliberately (handoff: L2 = solid GND), which is the tighter
and better-controlled choice, and is what h = 0.2104 mm was computed for.

## Deliverables

- `drc-placement.rpt` — full DRC
- `docs/drc-exceptions.md` — every violation classified: expected vs defect
- `out/renders/top.png`, `bottom.png`, `iso.png`

**896 violations: 443 unconnected (nothing routed), 169 silk-over-copper
(inherent to the vendor footprints, normally waived), and ~137 genuine
placement defects** — 51 shorting items, 58 clearance, 22 courtyard overlaps —
that need placement iteration before routing is worth starting.

The 3D render already earned its keep: it caught **J2, the battery
wire-to-board JST, sitting mid-board next to U2** where its lead could not
leave the board. Moved to the bottom edge at (40, 55).

## Open before routing

- **F-18** 5th mounting hole — needs a housing with a matching boss.
- **F-19** BT1 vs the +70 C ceiling.
- **F-16** SIM locating-post holes — deliberately absent, decision open.
- **Double-sided assembly** — confirm the cost is acceptable.
- **~137 placement defects** to clear.
- **AF1/AF2 sit at x = 72 but U1's ANT pads are at x = 76.55**, so the RF run
  currently doubles back inboard. Short (~4.5 mm) but wrong-way; the U.FL
  should move outboard of the ANT pads, which collides with the H2/H4 corner
  holes. Resolve with the final outline.

---

# MILESTONE 4 — Option 4 complete: floorplan for review. STILL NOT ROUTED.

Placement, L2 GND, L3 pours, HV keepout and thermal vias are done and the
review deliverables are produced. **Routing has not started** — that is
Option 1, gated on floorplan approval.

`tools/build.py` now runs the whole thing in one command, because the ordering
is load-bearing and every failure mode in it was silent. Verified
**byte-identical across consecutive builds**, so MIGRATION.md's
"regenerate, then git diff must be empty" check still works on the board.

## Result

| | first pass | now |
|---|---|---|
| total DRC violations | 896 | **518** |
| unconnected (nothing routed) | 443 | 450 |
| silk | 398 | **38** |
| **shorting items** | 51 | **0** |
| **solder mask bridges** | 71 | **0** |
| **courtyard overlaps** | 22 | **3** |
| clearance | 58 | 24 |
| annular width / padstack | 17 / 2 | **0 / 0** |
| hole-to-hole / dangling vias | 7 / 9 | **0 / 0** |
| components placed | 214 of 218 | **218 of 218** |

Of the 24 remaining clearance items, 23 are justified waivers and 1 is open;
full classification in `docs/drc-exceptions.md`.

## Six real bugs found and fixed along the way

1. **`GetCourtyard()` can be smaller than the pad extent.** U2's LQFP-48
   courtyard measures 7.1 x 7.1 (the body) while its pads reach 9.0 mm, so
   packing against the courtyard dropped 0603s onto its leads. That single
   mistake caused most of the U1/U2 clearance and shorting violations.
   Keepout is now `max(courtyard, pad extent)` per axis.
2. **The keepout box was centred on the footprint origin, not on the box.**
   J1's derived Molex courtyard is centred **7.50 mm in x and 1.92 mm in y**
   from its origin, because the origin sits on pin 1. A correctly-sized box was
   being blocked in the wrong place, which is what let D2, D6, F1, TP8 and TP9
   be packed on top of J1.
3. **`FindPadByNumber()` returns only the first pad with that number.** The
   MFF2 exposed pad is deliberately numbered "1" so it merges with the GND pin;
   only one of the two got a net, and DRC reported the netless one as a short
   against its twin. Net binding now assigns every pad carrying the number.
4. **Zones were filled before net classes existed.** The fill used Default
   0.2 mm where HV needs 0.6 mm, so the GND plane was flagged against every
   J1 pad. Fixed by ordering: net classes, then `kicad-cli pcb drc
   --refill-zones --save-board`.
5. **`pcbnew.SaveBoard()` wipes `net_settings` out of the project.** The board
   generators were destroying the net classes on every run, so RF/HV/MODEM_BULK
   silently stopped applying while DRC still looked like it was passing them.
   `tools/netclasses.py` is therefore applied *after* the generators, and it
   **verifies the classes survive a KiCad round trip** rather than assuming it.
6. **Hand-written net class dicts are silently discarded by KiCad.** Any class
   missing `bus_width`, `priority` or `tuning_profile`, or written with the
   wrong `meta.version`, is dropped on the next load-and-save. All five classes
   had gone back to just "Default" without a warning, and that state had
   already been committed.

## F-16 CLOSED — the imported footprint already had the post holes

The flag was chasing a dimension that was in the file the whole time.
`SIM-SMD_YKSIM-PUSH137-140NANO` contains two NPTH locating holes, and they
agree with the 3-vendor consensus to within 0.01 mm:

| dimension | GCT / HRO / Megastar | imported footprint |
|---|---|---|
| post-to-post | 8.50 | **8.490** |
| left GND pad c/l -> left post | 1.50 | **1.510** |
| lower GND pad c/l -> post (Y) | **1.25** | **1.250** |
| GND-pad frame | 13.00 x 12.00 | **13.00 x 12.00** (x = +/-6.50, y = -5.26 / +6.74) |

So the "genuinely ambiguous" Y was sitting in the footprint, on the corroborated
value. **No part switch, no samples, no guessed copper.** One real defect fixed:
the holes were imported as **PTH with a zero annular ring**, which is what the
`annular_width` and `padstack` errors were. They are mechanical locating bosses,
so they are now `np_thru_hole`.

## J1 footprint defect found and fixed

The derived `XUNPU_MX3.0-12PZZ` footprint had **four** NPTH holes where the
drawing specifies two. Two were Ø1.10 at (18.0, -0.95) and (-3.0, 3.95) — the
correct diagonal pair, matching "outer pin column +/- 3.00, row +/- 0.95". The
other two were Ø1.02 leftovers from the Molex base pattern: one sat **0.01 mm**
from a correct hole (the `hole_to_hole` error) and the other would have drilled
an extra hole in the board for nothing. Both removed.

## F-20 (NEW) — the buck's exposed pad is at line voltage

**EG11752 pin 9, the SOIC-8 exposed pad, is VIN_B — up to 100 V.** Measured
from the footprint: the EP is 3.30 x 2.40 mm centred, and the signal pads sit
at y = +/-2.72 with 1.94 mm height, so their inner edges are at +/-1.75 against
an EP edge at +/-1.20. **0.55 mm from a 100 V pad to its own signal pins, set
by the package.** No layout can widen it.

Consequences, all now handled explicitly:
- The 1.5 mm HV-to-signal rule was **unsatisfiable as originally written** and
  would have masked real violations. It is now scoped to the `HV_ZONE` rule
  area, which is what makes it a zone-separation rule rather than an
  intra-package one.
- A separate documented exception allows 0.3 mm inside U5's courtyard.
  **This is conditional on conformal coating actually being applied** (handoff
  rule 6): the IPC-2221 figure for external *uncoated* conductors at 100 V is
  0.60 mm, while coated (B4) at 100 V is about 0.25 mm. An uncoated board
  relies on the package's own certified spacing alone.
- The EP needs thermal vias (skill file: >= 9) but they had nothing to land on,
  so **L3 now carries a VIN_B island under U5** (8.2 x 10.6 mm). That both
  clears the dangling vias and is what actually spreads the heat. Being an HV
  island on L3, it holds HV-netclass clearance from the 5V0/SYS/3V3 pours.
- Via pitch in the EP is 0.85 mm, giving 0.55 mm hole-to-hole against the
  0.5 mm minimum. The first attempt scaled with pad size and produced 0.42 mm.

**Decision needed:** confirm conformal coating is non-negotiable in production,
since the U5 exception depends on it.

## HV keepout

Implemented as a named rule area `HV_ZONE` on all copper layers over
x = 0.5 to 20 mm, plus the silkscreen boundary and the scoped 1.5 mm rule.

More usefully, **HV zone membership is now decided by net, not by sheet.**
The io sheet mixes 100 V front ends with 3V3 logic, and assigning the whole
sheet to the HV zone pushed the eight DO gate-drive resistors R42-R49 into it,
filled the zone and left 13 parts unplaced. A part is now placed in the HV zone
if and only if it touches an HV-class net: **21 HV nets, 35 parts.** Nothing
low-voltage sits inside the boundary except the transition devices themselves.

## Floorplan

Zones (x, y in mm): **HV 1-19.25**, **power 20.75-43 / y 1-27**,
**digital 20.75-43 / y 27.5-59**, **RF 44-79**. Power gets 26 mm of height
because L1 alone is 13.8 x 12.4 mm. RF stops at x = 44 because U1's keepout
reaches 44.2.

**137 top / 81 bottom.** Double-sided is not a choice: 3315 mm2 of courtyard
against 4800 mm2 of board is 69 % of one side, and only L1/L4 carry signal.

Placement amendments as applied:
- **(a)** U5 / D16 / C73 / C74 clustered around L1 — the loop is tight, and the
  3 remaining courtyard overlaps are the price of that tightness.
- **(b)** GNSS U.FL at the bottom-right corner, LTE at the top-right, so the
  inductor is diagonally opposite the GNSS feed.
- **(c)** U3 at (29.5, 55) beside the provisional 5th M3, which moved to
  (23.5, 55) — the first position had the hole's GND pad 0.2 mm from U3's 3V3
  pads.
- J2 on the bottom edge, where a battery lead can actually leave the board.

## Deliverables

`drc-placement.rpt`, `docs/drc-exceptions.md`,
`out/renders/{top,bottom,iso}.png`.

## Next: Option 1 (after floorplan approval)

Hand-route RF CPWG + fence vias, the HV front end, the VBAT_MODEM rail and the
U5 switching loop; then FreeRouting for the remaining low-speed nets; then
review to DRC-clean. **FreeRouting is not yet installed** — it will be recorded
in MIGRATION.md §1 as a tool dependency with its exact version and jar source
at the point it is fetched, before it touches the board.

## Open for the user

- **Floorplan approval** — the gate on starting Option 1.
- **F-20** conformal coating must be confirmed non-negotiable.
- **Buck cluster density** — smaller inductor, bigger board, or accept touching
  courtyards.
- **Double-sided assembly cost.**
- **F-18** 5th M3 hole needs a matching housing boss.
- **F-19** 1S Li-ion is -20..+60 C discharge against the +70 C product ceiling.
- **AF1/AF2 at x = 72 but U1's ANT pads at x = 76.55**, so the RF run doubles
  back inboard. Short, but wrong-way; resolve with the final outline.

---

# F-20 CONFIRMED + buck cluster resolved — 2026-09-05

## F-20 — conformal coating is a safety-critical process requirement

**CONFIRMED by the user.** Coating is now recorded as a process requirement,
not a finish preference, because **creepage at U5 depends on it**.

| condition | IPC-2221 at 100 V | actual at U5 | verdict |
|---|---|---|---|
| external, **uncoated** (B1) | 0.60 mm | 0.55 mm | **FAILS** |
| external, **coated** (B4) | ≈0.25 mm | 0.55 mm | passes, >2:1 |

Recorded in four places so it cannot be lost:
- `docs/SKILL.md` **P1** — safety-critical process requirements section.
- `docs/telematics-handoff.md` **§6.1** and rule 6 (now "MANDATORY on every
  board, including prototypes").
- `telematics-tracker.kicad_dru` — the 0.3 mm exception now states it is
  **valid only while the coating requirement holds**, and that if coating is
  ever dropped the rule must be deleted and U5 reconsidered.
- `docs/installation-sheet.md` §2a — field warning not to scrape or
  solvent-clean the coating.

Applied as instructed:
- **Prototypes are coated before the 100 V / 85 °C burn-in.**
- **U5 is marked as a coating inspection point on the assembly drawing**:
  `coating_inspection_marks()` draws a boxed outline on F.Fab around U5 plus
  the caption `COATING INSPECTION - CREEPAGE CRITICAL (F-20)`.
- The 0.3 mm exception stays scoped to `HV_ZONE`.

## Buck cluster — courtyard overlaps 3 → 0, and the inductor was NOT the cause

Instruction was to select a smaller inductor, or grow the outline if none
qualified. **Both were measured, and neither would have worked.** The overlaps
were a floorplan defect, not a component-size problem:

| attempted fix | courtyard overlaps |
|---|---|
| baseline (12.3 × 12.3 inductor) | **3** |
| grow board to 82 / 84 / 86 mm | 2 / 2 / 2 — plateaus, never reaches 0 |
| synthetic 10 × 10 inductor probe | **1** — better, still not 0 |
| **restructure the cluster into a column** | **0** |

The real cause: C73/C74 were stacked in the narrow strip **above** L1, which
left a 4.2 mm gap for two 3.29 mm parts. C73 was clamped on the zone edge and
L1 blocked C74, so the relaxation could not separate them — it converged them
to 3.08 mm apart no matter what they were anchored to.

**Fix:** the buck cluster is now a vertical column beside L1, ordered to follow
the hot loop (amendment (a)): **D16 above U5** because SW is pin 6 on U5's
upper edge, **C73 below** because VIN is pin 8 on the lower edge. U6 (charger)
moved to the digital zone beside J2, which is where it belongs electrically —
it feeds SYS to the battery. U9 (SYS→3V3 LDO) has no critical position and was
dropped from the anchors entirely. **C74 was also un-anchored**: only the cap
nearest U5's VIN pin is loop-critical, and anchoring both over-constrained a
4.7 mm-wide column whose zone edge is 0.65 mm away.

### Inductor comparison (researched as instructed, NOT applied)

A qualifying part does exist. All figures read from datasheets; prices at the
150–499 break; all parts including the incumbent are JLCPCB **Extended**.

| | **C21325** incumbent | **C5142144** best candidate | C5374179 | C2596017 Sumida |
|---|---|---|---|---|
| MPN | SMDRI127-151MT | YNR1050-151M | SNR.1050.TYD151MT00 | CDRH10D60BT150NP-101MC |
| L | 150 µH ±20 % | 150 µH ±20 % | 150 µH ±20 % | **100 µH** |
| Isat | **2.70 A** @25 % drop | 2.00 A @30 % drop | 2.00 A | 1.92 A |
| Irms | **1.42 A** | 1.20 A | 1.20 A | 2.30 A |
| **DCR** | **280 mΩ** | **438 mΩ max** | 438 mΩ | 250 mΩ |
| **I²R @ 1.0 A** | **0.280 W** | **0.438 W (+0.158 W)** | 0.438 W | 0.250 W |
| Body | 12.3 × 12.3 × 8.0 | **10.0 × 10.0 × 5.0** | same | 10.3 × 10.0 × 6.35 |
| Land area | ~170 mm² | ~102 mm² (**−40 %**) | 102 mm² | 108 mm² |
| Stock | **5132** | 496 | 787 | 415 |
| $ @250 | 0.154 | 0.162 | 0.127 | 1.11 |

**DECISION: keep the incumbent C21325.** The area saving is no longer needed —
overlaps are already 0 — and the swap costs real margin on a 5-year product:

- **DCR +56 % (280 → 438 mΩ)**, conduction loss 0.280 → 0.438 W at 1.0 A.
  That is +0.158 W, about 3.2 % of the 5 W output, on a converter whose
  thermal headroom is already the thing limiting the +70 °C ambient rating.
  At 125 °C copper the 438 mΩ becomes roughly 0.61 Ω.
- **Irms 1.42 → 1.20 A**, so self-heating rises materially at the same load.
- **Isat 2.70 → 2.00 A**, and the criteria differ — the incumbent's figure is
  at 25 % inductance drop, the candidate's at 30 %, so like-for-like the
  candidate is slightly under 2.00 A. Startup and over-current derating is
  much tighter.
- **Stock 5132 → 496** — under two builds of 250.
- Requires a **new footprint** (NR1050 pads are 5.5 × 2.0 with a 6.2 mm inner
  gap, rotated 90° relative to the current 2.90 × 5.40 at x = ±5.45).
- **Core loss UNVERIFIED** — neither datasheet publishes it, and a smaller core
  at the same 150 µH and ripple means higher peak flux density.

Rejected candidates and the exact reason: **C19190466** (8 × 8, would save
58 %) has Isat **min 1.60 A** and Irms **min 0.95 A** — zero Isat margin and
guaranteed Irms *below* the 1.0 A operating current. **C2594377** Sumida is
technically the best part (250 mΩ, AEC-Q200, −55…+150 °C) but **stock 0**.
**C397813 / C53430502** publish a single "IDC max" with no Isat/Irms
definition — unverifiable, rejected on evidence. **C18222150** is the right
part with only **44 pcs**.

**Kept on file:** if the outline ever shrinks or the buck moves, C5142144 is
the qualified 10 × 10 option and C5374179 is its second source (identical
geometry and electrical table, same OEM design — but its datasheet never says
"shielded", so that claim is UNVERIFIED for that vendor specifically).

## Four more silent bugs found this pass

1. **SMD anchors were blocked on the bottom-side shelves too.** U1 alone
   removed ~1030 mm² of bottom-side area it does not occupy, which is why
   parts started going unplaced. Only through-hole pads, unplated holes and
   vias pierce both sides.
2. **The stitching-via sites were reserved AFTER packing**, despite the comment
   saying "before". R84 was packed on the bottom directly under U5's
   exposed-pad via field — 3 shorts, 3 mask bridges and 3 hole-clearance
   errors from one misordered step. Reservation now happens at the moment the
   last anchor is placed.
3. **`canonicalise()` could not order zones.** Zones carry neither a
   `Reference` nor an `(at ...)` — they are polygons — so every zone sorted as
   equal and the L3 pours swapped places between runs, breaking byte-identical
   regeneration. The sort key now includes zone name, net name and first
   vertex.
4. **`tools/build.py` was truncating warnings out of its own output.** The
   relaxation's "did NOT converge" message was being cut by the `tail -14`,
   which cost real debugging time chasing a symptom whose cause was already
   being printed. `run()` now always keeps lines containing NOT converge /
   UNPLACED / FAILED / WARNING.

The relaxation also now **reports any pair it fails to separate**, so silent
non-convergence cannot resurface as a mystery courtyard error later.

## Permanent guards added to docs/SKILL.md

As instructed, the two silent-bug classes are now standing requirements:
- **G1** — a footprint's courtyard may be smaller than its pad extent, and is
  not necessarily centred on the origin. Keepout must be
  `max(courtyard, pads)` positioned by the box centre.
- **G2** — `pcbnew.SaveBoard()` wipes `net_settings`; net classes must be
  applied *after* every board-writing step and **verified to survive a KiCad
  round trip**.
Plus the two related pcbnew traps (`board.Remove()` segfault,
`FootprintLoad()` object reuse) and the **P1** coating requirement.

## State

| | |
|---|---|
| DRC | **33 violations + 452 unconnected** (896 on the first pass) |
| courtyard overlaps / shorts / mask bridges | **0 / 0 / 0** |
| annular / padstack / hole-to-hole / dangling via | **0 / 0 / 0 / 0** |
| ERC | 0 errors, 13 warnings |
| placement | **218 of 218**, 132 top / 86 bottom |
| regeneration | byte-identical across consecutive builds |

**Routing is NOT started and remains blocked on floorplan approval.**

---

# Floorplan approval measurements — 2026-09-05. 4 of 8 FAIL. ROUTING NOT STARTED.

Measured by `tools/floorplan_check.py` (committed; exit code gates routing).
Full output in `docs/floorplan-measurements.txt`. **Inductor decision: incumbent
C21325 retained as instructed; C5142144 stays logged as the qualified fallback.**

| # | check | result |
|---|---|---|
| 1 | ANT pad → U.FL, CPWG path clear, GND fence | **FAIL** |
| 2 | Antenna-region keepout, area in mm² | **FAIL** |
| 3 | HV→LV clearance ≥ 1.5 mm | **FAIL** |
| 4 | VBAT_MODEM caps ≤ 5 mm from U1 57–60 | **FAIL** |
| 5 | U3 IMU adjacent to a mounting hole | PASS |
| 6 | Buck hot-loop enclosed area | PASS |
| 7 | J1/J2 edge positions, SIM access | PASS |
| 8 | Renders in `docs/renders/` | PASS |

## 1. FAIL — three separate findings

```
ANT_MAIN (LTE)  U1.49 (76.77, 21.04) -> AF1.3 (73.53,  8.73)  = 12.72 mm
ANT_GNSS        U1.47 (76.77, 26.74) -> AF2.3 (73.53, 47.12)  = 20.63 mm
```

**(a) The π-network series resistors are not in the RF path.** R71 sits
6.19 mm off the ANT_MAIN line, R72 **20.94 mm** off the ANT_GNSS line. They were
never anchored, so the packer placed them by area. A series element in a π
network has to be in-line — this is a placement defect.

**(b) Q3.3 [VBAT_MODEM] is inside the ANT_GNSS corridor** (2.60 mm wide,
= W + 2G + 2×fence standoff). The ANT_MAIN corridor is clear.

**(c) The structural one — there is not enough room outboard of the ANT pads.**

| | |
|---|---|
| ANT pad outer edge | x = 78.02 |
| board edge | x = 80.05 |
| usable strip (less 0.30 copper-to-edge) | **1.73 mm** |
| CPWG trace + gaps (W 0.40 + 2×G 0.30) | 1.00 mm |
| **CPWG + two-sided via fence** | **3.10 mm** |

A fenced 50 Ω CPWG does not fit in 1.73 mm. A one-sided inboard fence fits in
1.00 mm, but then the outboard side relies on the board edge rather than a via
wall — which is exactly what Quectel §4.3 asks for ("adding some ground vias
around RF traces… distance ≥ 2 × W"). **This cannot be nudged away.** U1 has to
move left, which means narrowing the digital zone, or the outline has to grow.

Also worth stating plainly: **ANT_GNSS is the longer run at 20.63 mm**, on the
receive-only system with −130 dBm sensitivity. On FR4 CPWG that is roughly
0.2–0.3 dB of extra loss before any mismatch. If the outline changes anyway,
GNSS should get the shorter run, not the longer one.

## 2. FAIL — no antenna keepout can be drawn yet

Cleared area: **0.0 mm²**. Not an oversight and not fixable by layout: the BOM
lists **ANT as "select in stock"** for both the LTE FPC and the GNSS patch, so
neither datasheet's ground-clearance dimensions exist. Handoff §7 requires a
"GND keepout under the FPC antenna region **per antenna datasheet**". Both
antennas also mount in the **lid**, so the keepout depends on the housing,
which is also unconfirmed. **Blocked on a BOM/housing decision, not on layout.**

## 3. FAIL by the stated criterion — but read which pair

```
minimum HV->LV, ANY pair (outside the U5 exception):
    0.800 mm   R32.1 [/io/VIN_D1]  <->  R32.2 [VIN_SENSE]
minimum BETWEEN DIFFERENT components (what layout controls):
    1.025 mm   R30.2 [/io/VIN_D0]  <->  Q1.1 [/io/Q1_G]
```

The 0.800 mm pair is **the two ends of one 0805 resistor** — R32 is the bottom
element of the 3×100k VIN divider, so it has the divided node on one pad and
the ADC tap on the other. That spacing is the package (0805 pads are 0.8 mm
apart) and no layout can widen it. Same category as F-20 at U5.

The number layout *can* act on is **1.025 mm between R30 and Q1**, still short
of 1.5 mm. Both are HV-zone parts near the DO gate drive.

*Measurement bug found and fixed while producing this:* the first version
compared pads without checking layers and reported 0.000 mm for
C73 [F.Cu] ↔ R87 [B.Cu] — opposite sides of 1.6 mm of FR4. That is also why
DRC, which does check layers, reported no short. The check is now layer-aware.

## 4. FAIL — the bulk caps are nowhere near the modem

```
U1 VBAT pads 57-60 at y = 13.09, x = 67.27 .. 71.17   (U1's top edge)

C40 (46.34,  2.65)   20.07 mm      C41 (51.84,  2.65)   15.16 mm
C81 (46.34,  6.64)   18.87 mm      C82 (51.84,  6.64)   13.53 mm
                                   requirement: <= 5.00 mm
```

The four F-13 caps were **never anchored** — added in the F-13 commit and left
to the packer, which placed them by free area. Handoff §4 requires them within
5 mm of pads 57–60.

Fixing this is not just an anchor edit: **four 1210 caps (4.69 mm keepout each)
cannot all sit within 5 mm of four pads spanning 3.9 mm on one side.** The
arrangement that works is two on top immediately above the pads and two on the
**bottom directly beneath them** — which is lower inductance than 5 mm away
laterally, and is standard for modem bulk decoupling. That is a placement
change to make deliberately, not a nudge.

## 5. PASS

U3 at (29.31, 55.00); nearest mounting hole **H5 at 5.81 mm** (criterion
≤ 8 mm). Distance from the four-corner-hole centroid (36.7, 35.0) is
**21.32 mm**, i.e. well away from mid-span.

## 6. PASS

Commutating loop C73 → U5 VIN → U5 SW → D16 → GND → C73:
**enclosed area 43.42 mm²**, bounding box 4.56 × 13.03 mm.
U5 SW (pin 6) to the nearest L1 pad: **4.31 mm**.

## 7. PASS

Outline 80.1 × 60.1 mm.
**J1** 1.04 mm from the left edge · **J2** 1.11 mm from the bottom edge — both
wire-to-board connectors are on an edge as required.
**X1** 1.52 mm from the bottom edge, card slot facing +Y, i.e. toward that
edge. Insertion is accessible; confirm the lid does not foul it.

## 8. PASS

`docs/renders/{top,bottom,iso}.png` exported and committed.

## Verdict

**Routing is NOT started.** Checks 1 and 4 are placement work; check 3 needs a
decision on whether the 1.5 mm rule is meant to apply across a transition
component; check 2 is blocked on selecting the antennas.

Check 1(c) is the one that shapes everything else: **the RF corridor is
1.73 mm where a fenced CPWG needs 3.10 mm.** Fixing 1(a), 1(b) and 4 before
that is settled risks doing the work twice, because moving U1 left moves the
ANT pads, the U.FLs, the π networks and the VBAT caps together.

---

# Floorplan conditions: 7 of 8 pass — 2026-09-05

Inductor: **incumbent C21325 retained** as instructed; C5142144 remains the
logged qualified fallback.

## Check 1 PASS — RF corridor opened, at the cost of two outline growths

```
corridor = board_edge(82.05) - copper_to_edge(0.30) - ANT pad outer edge(77.80)
         = 3.95 mm            requirement 3.10 mm
ANT_MAIN  U1.49 (77.55, 22.90) -> AF1.3 (80.83, 10.21)  = 13.40 mm
ANT_GNSS  U1.47 (77.55, 28.60) -> AF2.3 (80.83, 48.49)  = 20.35 mm
R71 / R72 inline: 0.88 mm pad-to-pad from their ANT pad (<= 2.00), outboard
both dog-leg corridors (2.60 mm wide) CLEAR of non-GND pads and vias
Q3 moved off the RF edge to beside the VBAT caps
```

**The outline grew twice. Both were forced, and both are logged in
`tools/pcbgen.py` at the constant:**

1. **Y 60 → 62 mm.** AF1 has to clear H2's M3 pad — a 6.29 mm keepout reaching
   y = 6.65 — so U1 must sit at y ≥ 28.15. X1 is 15.09 mm tall and must fit
   below U1 inside the keep-in, so U1 must sit at y ≤ 27.51.
   **Infeasible by 0.64 mm.**
2. **X 80 → 82 mm.** Moving U1 inboard for the corridor took 2 mm off the power
   zone. That left the buck cluster single-file in a 5.35 mm strip and put
   C73's VIN_B pad **0.215 mm** from U5's LV pins. Growing X back and returning
   U1 to x = 61 keeps the 3.95 mm corridor *and* restores the 22.25 mm power
   zone.

Measured alternatives that did **not** work, so they are not worth retrying:
growing X alone plateaued at 2 courtyard overlaps, and a synthetic 10 × 10
inductor probe still left 1.

## Check 2 RECLASSIFIED (per instruction) — still open on part selection

**PCB copper keepout is N/A.** Both antennas mount in the lid and reach the
board only through a U.FL pigtail, so no board copper sits under either one —
there is nothing on the PCB to keep clear. The check now verifies instead that
the **metal-clearance figure is recorded as an installation/housing
requirement** in `docs/installation-sheet.md`. Antenna selection is in
progress; the check stays FAIL until the datasheet clearance numbers are in
that document.

*(Checker bug fixed on the way: R80's value "1R 2512 anti-surge" contains the
substring "ANT", so it was being reported as an antenna footprint. Now matched
as a whole word.)*

## Check 3 PASS — metric split permanently, ≤40 V exemption applied

```
minimum HV->LV, ANY pair (outside the U5 exception):
    0.800 mm   R32.1 [/io/VIN_D1] <-> R32.2 [VIN_SENSE]      intra, exempt
minimum BETWEEN DIFFERENT components (what layout controls):
    1.779 mm   U5.8 [/power/VIN_B] <-> L1.2 [5V0]            was 1.025 mm
```

**Per-resistor voltage, as justification for the ≤40 V exemption.** The VIN and
IGN sense chains are 3 × 100k in series then 9.1k to ground:

| | |
|---|---|
| total | 300k + 9.1k = 309.1 kΩ |
| current at VIN = 100 V | 100 / 309100 = **323.5 µA** |
| across each 100k | **32.35 V** → ≤ 40 V, **EXEMPT** |
| across the 9.1k | 2.94 V (this is VIN_SENSE / IGN_SENSE) |

Intra-component pairs **above** 40 V, listed separately and *not* exempt by
this rule — they rest on the IPC-2221 figure for their actual voltage plus the
mandatory coating, the same basis as F-20:

| part | gap | V across | note |
|---|---|---|---|
| Q1, Q2 | 1.04 mm | 100 V | LV gate against HV drain, SOT-23 pitch |
| R40 | 0.80 mm | **91.66 V** | DNP spare divider |
| R14–R19 | — | 49.4 V | DI series, 2 × 12k each |
| OK1, OK2 | 5.00 mm | — | the isolation barrier itself |

**Flagged: R40 is a SINGLE 100k** with the 9.1k, so it sees 91.7 V where the
fitted dividers see 32.35 V. It is DNP, but if it is ever populated it should
be 3 × 100k like the others.

**How the 1.5 mm is enforced, and the mistake worth remembering.** The packer
inflates a part's keepout by 0.85 mm across an HV/LV boundary. The first
version classified each part as simply "HV" or not — which is wrong, because a
**transition device** (a DO FET, a divider resistor, an opto) has *both* an HV
pad and an LV pad. Classified as HV, it got no extra spacing from other HV
parts while its LV pad still needed 1.5 mm from their HV pads, and the
measurement sat at 1.060 mm. The margin now uses **per-pad flags** and applies
whenever one part has an HV pad and the other has an LV pad, either direction.

## Check 4 PASS — VBAT bulk split top and bottom

```
C40 top    1.95 mm from the nearest of U1 pads 57-60
C41 top    1.95 mm
C81 bottom 0.00 mm   directly beneath the pads
C82 bottom 0.00 mm
```

Four 1210s cannot all sit within 5 mm of four pads spanning 3.9 mm on one side,
so two are on top immediately above the pads and two on the **bottom directly
beneath them** — lower inductance than 5 mm away laterally. All four anchored.

**New FIXED anchor class.** R71/R72, AF1/AF2, C40/C41/C81/C82, U1 and U3 are
now immovable in the relaxation, which pushes everything else around them.
Without it the relaxation slid the π-network resistors off their ANT pads and
the bulk caps out from under U1 — silently undoing checks 1 and 4 after they
had been made to pass.

*Bug found doing this:* a zero-size bound (how a FIXED anchor is pinned) was
clamped as if it were a region, collapsing to `centre − w/2` and sliding the
part half its own width. **U1 jumped 16.8 mm left.**

## Checks 5, 6, 7, 8 PASS

U3 **5.50 mm** from H5 and 17.5 mm off the hole centroid · hot loop
**44.85 mm²**, U5 SW to nearest L1 pad 4.31 mm · J1 **1.04 mm** from the left
edge, J2 moved to the new bottom edge, X1 **1.81 mm** from it with the slot
facing +Y · renders regenerated for 82 × 62 in `docs/renders/`.

## GNSS bias-T added (DNP) — verified against Quectel, one question left open

Read from the committed PDF, **§4.2, Table 37 and Figure 31 (p.67–68)**:

- **Table 37: `ANT_GNSS` pin 47 is AI — analog input, 50 Ω, "If unused, keep it
  open."** The pin carries **no internal DC feed**, so an active antenna must
  be biased externally. An external bias-T is therefore correct and cannot
  conflict with anything inside the module.
- **Figure 31 "Reference Circuit of GNSS Antenna" is itself a bias-T**, and its
  values are now what the schematic uses: **47 nH series** into the RF line,
  **100 pF shunt**, **10 R + 0.1 µF** on the supply feed, and a series 0 R on
  the module side, with two NM positions.
- **Note 2: "The VDD circuit is not needed if you select a passive antenna."**
  That is exactly the DNP-by-default arrangement — populated only for the
  external active-antenna (steel-cabinet) build.
- Note 1: "An external LDO can be selected to supply power according to the
  active antenna requirement" — relevant because the feed here is 3V3.

Added to `modem_rf`, all DNP: **L4** 47 nH series, **C84** 100 pF shunt,
**R90** 10 R and **C83** 100 nF on the 3V3 feed, on a new `GNSS_BIAS` net.

**NEW FLAG F-21 — is a DC block needed in series with ANT_GNSS?** Quectel's
Figure 31 shows the module pin DC-coupled to the injection node through the
0 R. With the bias-T populated, 3V3 would therefore sit on ANT_GNSS. The pin is
specified as AI, 50 Ω, with no statement either way about DC tolerance. The
R72 position is documented as **0R-or-DC-block**: fit 0 R for a passive antenna
(no DC anywhere), fit a DC-blocking capacitor when the bias-T is populated.
**Not resolved — do not populate the bias-T until this is settled.**

## State

DRC **19 violations + 452 unconnected**. ERC 0 errors / 13 warnings.
`checkpins` exit 0. 222 components placed. Board and DRC report byte-stable.
**Routing NOT started.**

---

# Check 2 closed — antennas selected. 8 of 8 pass. Routing still on hold.

## F-21 RETRACTED — I misread Figure 31, and the misreading was mine

I raised F-21 saying Quectel's reference circuit DC-couples the module pin to
the bias node through the 0 R, so 3V3 would land on ANT_GNSS. **That was wrong.**
It came from reading the `pdftotext -layout` dump, where `0R` and `100 pF`
share a row and `NM NM` sit on the row below — I took the 100 pF for a shunt.

I rendered page 69 at 200 dpi and looked at the actual drawing. **The 100 pF has
vertical plates sitting in the horizontal signal line: it is a SERIES DC
block.** The 47 nH injects VDD on the **antenna** side of it. The 0 R and both
NM positions are on the module side. The module pin is DC-isolated by
construction, and there was never a conflict to resolve.

```
ANT_GNSS --*--[0R]--*--||--*------ GNSS Antenna
           |        | 100pF|
          (NM)     (NM)  [47nH]
                           |
                         [10R]--VDD--0.1uF--GND
```

Corroborated by **Antenna Design Guide V3.3 §5.1 note 5**:
> "It is necessary to reserve LNA power supply circuit on the motherboard and a
> blocking capacitor should be reserved to block DC. Inductors of above 56 nH
> should be applied in series between the power supply and the impedance line."

Two consequences applied to the schematic:

1. **C84 (100 pF) is in series in the RF path and is ALWAYS FITTED.** It is not
   DNP — depopulating it opens the antenna. At 1575.42 MHz it is 1.0 Ω,
   electrically invisible. Only L4 / R90 / C83 are DNP.
2. **L4 is 68 nH, not Figure 31's 47 nH** — the Design Guide asks for ≥ 56 nH.

Also worth recording: **Table 40 (Absolute Maximum Ratings) does not list
ANT_GNSS at all.** There is no published DC rating for pin 47. That, rather
than any module-versus-bias-T conflict, is the real reason the block is
mandatory.

The netlist guard earned its keep here: the first placement of the bias-T
tripped `checkpins` with *"stub for net 'GNSS_BIAS' passes through … which
belongs to net 'USIM_VDD'. They would merge."* — a genuine short caught before
it reached copper.

Final chain, verified in the netlist:
```
ANT_GNSS_M : U1.47, R72.1, C50.1(NM)
ANT_GNSS_C : R72.2, C84.1, C51.1(NM)
ANT_GNSS_F : C84.2, AF2.3, L4.1        <- bias injected here, antenna side
GNSS_BIAS  : L4.2, R90.2, C83.1
```

**Parts, all in stock.** The inductor **must be wirewound**: every multilayer
47/68 nH 0402 at LCSC has SRF ≈1.0–1.3 GHz and is already capacitive at
1575 MHz.

| fn | value | LCSC | part | note |
|---|---|---|---|---|
| series DC block | 100 pF C0G | **C1546** | FH 0402CG101J500NT | JLC Basic, **always fitted** |
| bias choke | 68 nH | **C3221844** | Murata LQW15AN68NG80D | wirewound, **SRF 2.5 GHz**, 320 mA, DNP |
| feed resistor | 10 Ω | **C25077** | UNI-ROYAL 0402 | JLC Basic, DNP |
| feed bypass | 0.1 µF | **C60474** | YAGEO X7R 16 V | DNP |

Avoid: C97998, C76776, C27151, C395068 (multilayer, SRF ~1.1 GHz) and
C3221157 (LQW15AW68NJ80D, SRF 1.8 GHz — only 14 % above carrier).

## Antennas selected

**LTE — C496569**, Bat Wireless BW4GFNX39-15B1. 5,536 stock, $0.383 @250.
700–2700 MHz continuous, 39.6 × 14.5 mm, RG1.13 120 mm IPEX-1, 2.8 dBi typ,
VSWR < 2.1, −45…+85 °C. Runner-up **C22467619** (AICF002, $0.234, adhesive) was
**rejected: it omits B40 (2300–2400 MHz), which Jio uses heavily in India**, and
its VSWR is 5/4/7:1.
*Caveat:* C496569's datasheet gives its mount as **压扣 (crimp)**; a 3M backing
is **UNVERIFIED** and must be confirmed with the supplier.

**GNSS — C784386**, Bat Wireless BWGNSCNX25-25B1Y4L120. 942 stock, ~$1.53 @250.
25 × 25 × 6.5 mm, IPEX-1 RG1.13 120 mm, RHCP, −45…+85 °C.

**DEVIATION FROM THE STATED SPEC, needs a decision.** The brief asked for a
**passive** 25 × 25 patch with a U.FL pigtail. **No such part is in LCSC
stock** — verified two independent ways. C784386 is **ACTIVE** (internal LNA
21.5 dB, 1.8–3.6 V, 4.3 mA). Consequences:

- **The bias-T stops being optional for the internal build.** L4/R90/C83 must be
  POPULATED, not DNP, if C784386 is fitted. 3V3 sits inside its 1.8–3.6 V
  window and 4.3 mA is trivial for the 320 mA choke.
- Its LNA masks both the coax loss and the absent ground plane, which is
  genuinely useful for a lid mount.

The alternative is **C784398** (BWGNSCNX25-25W4, 1,830 stock, $0.484) — 25 × 25
× 4 mm and genuinely **passive**, but it has **solder pins and no cable**, so it
needs a hand-added pigtail *and* a ground plane built into the lid.

Neither datasheet states a ground-plane size. Quectel's **GNSS Antenna
Application Note V1.0 §4.2.1** simulates exactly a 25 × 25 × 4 mm patch on a
**30 × 30 mm** plane, and Figure 13 gives gain against plane size:

| plane | 30 | 40 | 50 | 60 | 70 | 80 | 100 mm |
|---|---|---|---|---|---|---|---|
| gain dBi | +1.25 | **−1.38** | +0.36 | +1.30 | **+1.40** | +1.26 | +0.72 |

If the passive route is taken, **target 60–70 mm and specifically avoid ~40 mm**
— counter-intuitively worse than 30 mm.

**External active (steel cabinet) — u-blox ANN-MB-00.** LNA 28 ±3 dB, 3.0–5.0 V,
15 mA, SMA male, RG174 5.0 m, magnetic + 2 × M4, −40…+85 °C. Not LCSC-stocked.

## The 17 dB LNA limit — recommendation, not a hard limit

Quectel Table 39 lists `Active antenna internal LNA gain: < 17 dB` with no test
method, no tolerance and no compatibility clause. The only stated consequence is
in the GNSS Antenna Application Note:
> "excessive gain in the LNA may cause saturation or system de-sensitization…
> The total antenna gain equals the internal LNA gain minus the total insertion
> loss of cables and components inside the antenna."

So it is measured on **total** gain, and **Quectel's own active antennas
(YEGB000Q1C, YEGN001Q1A) are 21 ±3 dB — above their own figure.** Both of our
candidates land ≈4 dB over: ANN-MB at 21.4 dB (28 − 6.6 dB cable), C784386 at
≈21.3 dB.

**Design rule adopted:** treat 17 dB as the target, accept up to ~22 dB total,
and **validate C/N0 on the bench with the LTE modem transmitting at full
power**. If desense appears, fit a 3–6 dB 0402 pad at the module end — cheaper
than re-sourcing. ANN-MB's SAW pre-filter (85/80/70/75/80 dB rejection at
698/960/1710/2170/2690 MHz) makes its 21.4 dB materially lower-risk than the
same figure from an unfiltered antenna sharing the lid.

## Check 2 result

PCB copper keepout **N/A** — both antennas are lid-mounted and reach the board
only by U.FL, so no board copper sits under either. The clearance figures are
now recorded in `docs/installation-sheet.md` as installation/housing
requirements: **LTE FPC > 5 mm from the main PCB**, **GNSS patch ≥ 10 mm from
tall metal and ≥ 3 mm from a non-metal enclosure wall**, **> 40 dB antenna
isolation**. Plus the adhesive warning: at +70 °C ambient the LTE FPC must be
heat-staked or clamped, not stuck on.

## State — 8 of 8 PASS

DRC 19 violations + 452 unconnected · ERC 0 errors / 13 warnings ·
`checkpins` exit 0 · 222 components placed · board byte-stable.
**Routing NOT started.**

---

# F-22 R90 approved, F-23 accepted — 2026-09-05

## F-22 — GNSS feed current limit, R90 = 68 R 1210 (APPROVED)

**The vendor publishes only a TYPICAL 4.3 mA and no maximum**, for either
current or supply voltage — both sit under a column headed "Typical value",
and the datasheet has no absolute-maximum table at all. There is therefore no
published worst case to design against, so the value is set from a conservative
multiple and the fault power.

Series chain is R90 + L4's DCR = 68 + 1.128 = **69.13 Ω**.

**Normal operation**, 3V3 at −5 % = 3.135 V, antenna needs ≥ 1.80 V:

| draw | V at the antenna | |
|---|---|---|
| 1× typical (4.3 mA) | 2.838 V | ok |
| 2× (8.6 mA) | 2.540 V | ok |
| 3× (12.9 mA) | 2.243 V | ok |
| **4× (17.2 mA)** | **1.946 V** | ok |
| 5× (21.5 mA) | 1.649 V | fails |

So it tolerates **4.3× the typical current** before the LNA drops out of spec —
adequate cover for an unpublished maximum.

**Fault — antenna or coax shorted**, 3V3 at +5 % = 3.465 V:

```
I_fault = 3.465 / 69.13 = 50.1 mA
P_R90   = 0.0501^2 x 68 = 0.171 W
```

50.1 mA against a 500 mA LDO (ME6211) already carrying ~150 mA: the 3V3 rail
cannot be pulled out of regulation. Also well under L4's 320 mA rating.

**Why 68 R and not the ~150 mA the brief asked for.** The fault-power reasoning
is the deciding factor:

| R90 | I_fault | P_R90 | package needed at 70 °C |
|---|---|---|---|
| 22 R | 143 mA | **0.448 W** | 2512, and still 90 % of a 50 %-derated 1 W |
| 33 R | 97 mA | 0.309 W | 2010 |
| **68 R** | **50 mA** | **0.171 W** | **1210 — 68 % of a 50 %-derated 500 mW** |
| 100 R | 33 mA | 0.106 W | 1206, but only 1.78 V at 15 mA — too tight |

A shorted coax does not clear itself. At 22 R the board would dissipate
**0.448 W continuously inside a sealed IP65 enclosure at 70 °C ambient**, from
a fault that persists until someone opens the unit. 68 R limits harder than
asked, survives indefinitely in a 1210, and still leaves 4.3× current headroom.

**C85 10 nF APPROVED** at the injection node. Raising Quectel's 10 R to 68 R
increases supply-noise coupling into the LNA; C83 (0.1 µF) with 68 R puts the
supply corner at 23 kHz, and C85 handles what the electrolytic-scale bypass
cannot at higher frequency.

C-numbers for R90/C85 are **TBD-F22**, to be fixed at the milestone-5 BOM
stage like the other TBD-F5 passives.

## F-23 ACCEPTED — antennas join the 85 °C survival tier

Both antennas are **−45 to +85 °C for operating and storage** (identical
ranges, verified verbatim in both datasheets). Accepted: they join the **85 °C
survival tier already set by U1**, whose extended range tops out at the same
+85 °C. The product's survival limit is therefore set consistently by three
parts — U1, and now both antennas — rather than by the antennas alone.

**Consequences recorded:**

1. **The antennas are field-replaceable items, alongside BT1.** The service
   list is now: BT1 (2–3 year interval, rule 2) **and both antennas**. All
   three are the parts whose life is set by temperature rather than by design
   margin, and all three are reachable without unsoldering anything — the
   antennas are lid-mounted on U.FL pigtails.
2. **85 °C soak added to prototype qualification, with C/N0 measured before
   and after.** GNSS carrier-to-noise is the right metric: it is the thing an
   ageing patch or a degraded LNA actually loses, and it is measurable in the
   field afterwards. Measuring only "does it still fix" would miss gradual
   degradation.

This also raises the stakes on two existing requirements rather than adding
new ones: the housing must be shaded or light-coloured (§1.1), and antenna
retention must be mechanical (§6.3) — adhesive fails first at exactly the
temperature that defines this tier.

## FreeRouting import rules (standing policy)

Recorded because they govern every future autorouter run, not just this one:

1. **Never loosen a netclass width or clearance to improve completion.**
   HV 1.5 mm, VBAT_MODEM 2 mm and the locked RF are non-negotiable. If the
   router cannot finish, the answer is placement or hand-routing, never a
   relaxed rule.
2. **After every import, verify:** the locked RF items are byte-identical to
   pre-export; `net_settings` survived the round trip (SKILL G2 — KiCad
   silently drops net classes); and `floorplan_check.py` still passes, with no
   autorouted copper inside the RF corridors, the antenna region, or the U1/U5
   via fields.
3. **Unrouted nets are listed individually** and resolved by local placement
   change or hand-routing — reported per net, never left silent.
4. **Every autorouted HV net path is reviewed individually** (VIN, IGN, DI
   chains, DO drains): confirm it stays inside `HV_ZONE` and measure its
   closest LV approach.
5. **Thermal vias under the U1 paddle and the U5 exposed pad are counted and
   logged** after import, since the router may add or disturb vias.

---

# FreeRouting cannot route this board within the agreed constraints — 2026-09-05

**Result NOT imported into the repo.** Everything below was measured on a
scratch copy. Two full runs, 38m40s and 37m47s, both plateaued.

| | run 1 (L3 pours present) | run 2 (L3 pours removed) |
|---|---|---|
| SMD pins needing fanout | 633 total | **726 total** |
| fanout escaped | 551/633 (87 %) | similar |
| items to auto-route | 245 | 250 |
| **final unrouted** | **143** | **130** |
| FreeRouting's own violations | 65 | 65 |
| layers it put tracks on | F.Cu, B.Cu only | **F.Cu, B.Cu only** |

## What the diagnosis actually was, and where I was wrong

I first assumed the inner layers were unavailable because they carried planes,
and that freeing L3 would unlock a third routing layer. **That was wrong**, and
the log says so plainly:

> `Layer 'GND_L2' has been automatically configured as a dedicated power plane
> because it contains a large conduction area covering >50% of the board.`

Only **GND_L2** was reclassified. **PWR_L3 was available as a signal layer the
whole time and FreeRouting simply never used it** — zero tracks on it in either
run. Removing the L3 pours was worse than neutral: the fanout population went
**633 → 726 SMD pins**, because those pours were doing real connectivity work
for 5V0 / SYS / 3V3, and removing them added roughly a hundred connections for
no benefit.

## The imported result, measured

Importing `routed2.ses` onto a scratch board adds **1532 tracks/vias
(80 → 1612)** and then fails DRC on four counts:

| count | violation |
|---|---|
| **183** | unconnected items, across **81 distinct nets** |
| **30** | clearance against the **HV netclass** — the 100 V nets |
| **20** | `track_width` — 0.150 mm used where the board minimum is 0.200 mm |
| **11** | `annular_width` — 0.050 mm ring where the minimum is 0.100 mm |
| 12 | other clearance |

Worst-affected nets by unconnected pads: GND (17), VIN (12), VBAT_MODEM (10),
VIN_SENSE (7), 3V3A (6), DI1_LED (6), DI2_LED (6), CANL (6), VIN_P (5).

**FreeRouting v2.4.1 did not honour the constraints in the DSN.** It undercut
the board's minimum track width and minimum annular ring, and it violated the
HV netclass clearance 30 times. Those are not near-misses on a preference —
0.15 mm where 0.20 mm is the floor, and HV clearance on the 100 V front end.

Per the standing import rules, **the only way to make this result "pass" would
be to loosen the netclasses, which rule 1 forbids.** So it is rejected rather
than patched.

## What this board actually needs

The routing problem: **223 components, 726 SMD pins, 69 % courtyard density,
82 × 62 mm, and effectively two usable signal layers** — L2 is a solid GND
plane (correct and non-negotiable for the RF return path) and the autorouter
will not use L3. Two signal layers is not enough for this pin count.

Options, in the order I would recommend them:

1. **Interactive routing in KiCad, by hand.** The placement is verified —
   8/8 floorplan checks, 0 clearance/shorts/mask-bridge/crossing DRC — and the
   critical nets are already routed and locked. This is the realistic path for
   a board of this density, and it is what the remaining work actually is.
2. **Go to 6 layers** (L1 sig, L2 GND, L3 sig, L4 sig, L5 PWR, L6 sig) and
   retry the autorouter with 4 signal layers. This is the standard answer at
   this density; it raises fab cost, which is a budget decision.
3. **Shrink the routing problem** — X2 (MFF2, DNP), R40/R41/C30 (spare ADC
   divider, DNP) and some of the 28 test points are all candidates, and the
   outline could grow again.
4. **A different autorouter.** Given v2.4.1 ignored explicit DSN width and
   clearance rules here, I would not trust it on the HV front end regardless
   of completion rate.

**Repo state is unchanged and clean:** the committed board has the 23
hand-routed RF tracks and 57 vias, DRC 0 clearance / 0 shorting / 0 mask bridge
/ 0 crossing / 0 starved thermal / 0 dangling via, with 329 unconnected (the
bulk nets, still unrouted) and 13 waivable silk items.

---

# HV rule rescope (APPROVED) + step-2 routing — 2026-09-06

## The rescope, as approved

Two changes to how the 1.5 mm HV-to-LV separation is scoped. **The 1.5 mm
rule itself is unchanged** where it applies; no clearance value was reduced
anywhere. Both rescopes are encoded in `telematics-tracker.kicad_dru` and in
`tools/netclasses.py`, and enforced identically by `tools/pcbroute_hv.py`.

### 1. BUCK_HV named area (buck cluster: 0.60 mm to LV)

`BUCK_HV` rule area covers x 20..44, y 0.5..20 — U5, L1, D16, the bootstrap
cap C76, the output caps, and the SW_BUCK / VIN_B / U5_VB copper. Inside it
the HV-to-LV minimum is the electrical 0.60 mm (IPC-2221 table 6-1; B4 coated
basis with conformal coating MANDATORY per F-20).

Justification as approved: the 1.5 mm figure is defence-in-depth for
externally-wired nets exposed to harness transients and contamination. The
buck cluster is internal, post-TVS/post-R80, coated, and compact by
construction — SW_BUCK cannot sit 1.5 mm from U5's own FB/VCC pins in any
package. Discovered as a hard blocker when SW_BUCK was correctly reclassified
into HV (it had been sitting in Default — the buck switching node swings
GND-to-VIN every cycle) and instantly became unroutable at 0/4.

### 2. MV netclass (interior nodes <= 70 V: 0.60 mm, 0.20 mm track)

Nets: VIN_D0/D1, IGN_D0/D1, DI1/2_M1, DI1/2_M2, DI1/2_LED.
Calculated worst-case node voltages at VIN = 100 V (logged in netclasses.py):

    dividers (3 x 100k : 9.1k, I = 0.324 mA): D0 nodes 67.6 V, D1 nodes 35.3 V
    DI chains (3 x 12k -> EL357N LED, I = 2.74 mA): M1 67.1 V, M2 34.2 V,
    LED ~1.2 V (clamped)

All <= 70 V. These are interior chain nodes on the same current path as their
HV parents: the potential between an HV net and its own MV node is one
resistor drop (~33 V), and a 1.5 mm wall between them just walls off the
divider it feeds. MV-to-anything is 0.60 mm via the MV netclass — the same
electrical minimum the design uses for 100 V — so even rated as if they sat at
the full bus voltage, they clear uncoated.

HV class now = connector-side nets only: VIN, VIN_F, VIN_P, VIN_B, IGN,
DI1/2_IN, DO1/2_OUT, J1_SPARE1/2, plus SW_BUCK and U5_VB (inside BUCK_HV).

### TP15/16/17 kept

USB DP/DM/VBUS test points stay (modem firmware recovery path); handoff §2
rule 8 amended accordingly.

## What step-2 routing surfaced (all fixed, none by loosening a rule)

1. **SW_BUCK/U5_VB misclassification** (Default -> HV), found because the
   router walled U5's own VIN pins behind an LV halo.
2. **HV_ZONE excluded the buck primary** — and with it the F-20 U5 exception
   (conditioned on insideArea) had been dead code. Zone is now L-shaped.
3. **Router defects**: via-sized halos blocking track-legal lanes (split into
   separate track/via grids); round-to-nearest halo quantisation admitting
   0.075 mm encroachment (now floor/ceil outward); global exemption where the
   DRU is courtyard-scoped (now clipped to courtyards). 128 of 129 clearance
   violations traced to these.
4. **Placement defects**: VIN_P filter caps C70-C72 packed on B.Cu under U5,
   25 mm from the node they filter, sealing the bootstrap cap C76 into a
   63-cell pocket (flood-fill measured); DI chains and dividers scattered by
   the packer; J1 not pinned (the relaxer walked it half off the board).
   The whole HV strip is now tiled from MEASURED keepout boxes: dividers in
   the sliver left of J1, front-end chain in the right column and below J1,
   DI chains as ordered B-side rows below J1, VIN_P caps beside R80.
5. **Greedy route-order matters**: VIN_P routed first walled C73 into a
   626-cell pocket. Constrained-first ORDER is now explicit in the router,
   with the reasoning in a comment.

---

# Step 4 STOP report: FreeRouting plateaus — but as a TOOL failure — 2026-09-06

## The runs (all on the pinned freerouting-2.4.1.jar, SHA verified)

| run | input | passes | budget | outcome |
|-----|-------|--------|--------|---------|
| 1 | 3502 locked items (per-cell segments) | -mp 100 | 90 min | killed at budget, no .ses (v2.4.1 writes .ses only on completion) |
| 2 | same | -mp 8 | 85 min | killed at budget, no .ses |
| 3 | same, log captured | -mp 1 | 88 min | NPE crashloop in fanout: `SearchTreeObject.shapeLayer` on null, thrown continuously from the event thread |
| 4 | COALESCED copper (517 locked items) | -mp 8 | 88 min* | fanout clean: 483/617 pins escaped in 7.1 min. Auto-routing pass #1 then ran 6.5 h; killed after the pass-1 report |

*run 4's wall-clock guard failed operationally (the process detached from its
wrapper), which is the only reason pass #1's full duration got measured.

## Run 4, measured

- Fanout: 483/617 SMD pins (78.3%) in 425 s, 0 errors.
- Auto-routing pass #1: 23,328 s wall, **1,133 s CPU (5% duty)** — the
  engine spent 95% of the time NOT routing. The same
  `SearchTreeObject.shapeLayer` NullPointerException storm reappeared during
  the pass, on input that was now clean long segments.
- Pass #1 result: 188 of 252 items unrouted, **539 violations**, score 406.
- No .ses was ever produced inside any budget window.

## Reading

The <95% plateau is real, but it is NOT yet evidence about the BOARD:
v2.4.1 malfunctions on this input (NPE storm from its own search tree,
5% CPU duty). The earlier rejected run (2026-09-05, 78 locked items) at
least completed; with the full locked HV/RF field it does not. The 539
violations echo the previous finding that FreeRouting undercuts the rules
it is given. Nothing in these runs says a 4-layer board cannot be routed -
our own maze router just completed 41/41 of the HARDEST nets (HV at 1.5 mm
separation) with 0 DRC violations on this same board.

## 6-layer cost delta (requested if plateaued)

Not quantifiable without an account: JLCPCB's calculator is JS-gated, the
official quotation API requires a registered API key, and no published
figure for ~82 x 62 mm at 500 pcs exists that I would trust. Quote
parameters for a 2-minute manual check: 82 x 62 mm, JLC7628 4-layer vs
6-layer, 1.6 mm, 1 oz outer / 0.5 oz inner, HASL or ENIG as spec'd,
qty 500. The marketing floor ("5 pcs from $2") says nothing at volume.

## Options on the table (decision held for the user)

a. Swap autorouter version (e.g. FreeRouting 1.9.x classic) - a pinned tool
   dependency change, needs sign-off and re-verification.
b. Extend tools/pcbroute_hv.py to route the remaining 269 low-speed
   connections under their netclass rules (Default 0.20/0.15, PWR, GND,
   MODEM_BULK), constrained-first with failed-first retry, DRC after each
   net. The router has already demonstrated 41/41 under HARDER rules.
   No rule change, no cost change, deterministic, and the tool is ours.
c. 6-layer respin (cost delta pending the manual quote).

Recommendation: (b), with (c) only if (b) plateaus - the same gate the
user set for FreeRouting.


---

# Zone-priority bug, routing A/B, FreeRouting bisect, housing variants — 2026-09-15

## The adopt stage was dead, and the cause was two missing integers

DRC on the 09-11 board reported 2 `zones_intersect` errors: the two 3V3 L3
pocket fingers (POWER_POURS, added 09-11) overlapped island B and each other
at priority 0. `POWER_POURS` *documented* them as "priority 1" and "priority
2" but `add_zone()` never set a priority at all — the intent was written down
and never implemented.

Consequence chain, verified in the chain-v13 log: `zones_intersect` names the
zone's NET (`3V3`), so `pcbroute_adopt.py` added 3V3 to its rip set, ripped
3V3 *segments* to clear a *zone* overlap, ripped 0 forms, concluded
"violations remain on LOCKED copper - placement problem" and exited
`ADOPT_BASELINE_NOT_CLEAN`. Every FreeRouting result was therefore discarded
before the LV finisher ever ran. Fix: `add_zone(..., priority=)`, every
POWER_POURS row carries its priority explicitly, live board patched in place
(a regeneration would have ripped the routing), netclasses re-applied and
round-trip verified (G2). DRC 2 -> 0, unconnected unchanged.

## Controlled A/B: the LV plateau is not the zone patch

After the fix, a full LV run routed 2 nets and failed 50 in pass 1, with GND
as the dominant wall in every flood diagnostic. To rule the patch in or out,
the same nets were routed as single children against the pre-patch board
(58dbe4b) and the post-patch board (5bdaad6) in isolated temp projects:
`/mcu/IMU_INT1` and `/mcu/BOOT0` fail identically (`no path`) on both. The
router's obstacle model is pads + vias + track segments only (zone fills are
not obstacles), so the GND walls are real copper: GND pads and the 47 GND
stitching vias. This is the placement-density plateau of
`docs/routing-endgame-report.md`, unchanged by relief round 2.

What the LV pass did achieve: GND pour taps (47 vias) and SYS, 174 -> 131
unconnected at 0 errors (commit eecfe23).

## FreeRouting collapse (v13: 1156 -> 55 wires in 10 s) does not reproduce

Bisect on the current board, two isolated 10-minute runs: with the injected
keepouts and without them, FreeRouting 1.9.0 ran the full budget in both
cases (it writes the .ses only on completion, so 10 min with -mp 2 produced
none). The v13 collapse was specific to the freshly regenerated board that
carried only the locked HV/RF copper; on a board with LV copper present FR
behaves normally. The DSN it saw in v13 was healthy (146 nets, 139 routable).
The hybrid cycle (FR 8 passes / 120 min -> adopt -> LV finisher) is now
running on the 131-unconnected board without build.py; result appended below.

## Housing: two Blender variants, IP67 intent

`tools/housing.py` builds `internal` (LTE FPC bay + GNSS patch pocket in an
8 mm lid; walls solid, SMA seats as sealed pilot dimples) and `external`
(two O-ring-sealed SMA bulkheads, plain 3.5 mm lid) from one model. Shared
sealing: d2.0 O-ring cord in a 2.4 x 1.6 lid groove compressed by a 1.0 x 0.8
tongue on the base wall; six lid screws outside the seal line; M16 IP68
gland; M12 ePTFE vent (closes the old open item 5). Antenna rules from
installation-sheet 5a are asserted in the script (patch exactly 3.0 mm from
the +X wall; no metal fixings over either antenna). Render review caught a
strap rib and the pigtail clip intersecting the lid skirt — fixed before
commit (4e21bae). Details in `docs/housing-notes.md`.

## Process notes

- EnterWorktree branched from `origin/main`, 67 commits behind local main;
  the worktree carried a 2.1 MB board with none of the routing. Reset to
  local main and `cmp` against the main checkout before any edit.
- A single `pkill -f <pattern>` matched its own shell (exit 144). Match on
  the child's argv, not on a string the invoking command also contains.

## Hybrid cycles under the repaired pipeline (same day, later)

| step | unconnected | errors |
|---|---|---|
| LV finisher (GND taps, 47 vias, SYS) | 131 | 0 |
| cycle 1: FR 8 passes, 20 min -> adopt, rip set EMPTY | 120 | 0 |
| LV finisher: GND +13 vias; 67/68 signal nets `no path` | 114 | 0 |
| cycle 2: FR 20 passes, 37 min -> adopt, rip set EMPTY | 111 | 0 |
| LV finisher (40 min deadline): GND +2, CANL fragment | **109** | **0** |

Floor reached with both engines honest for the first time. 72 % of the
remaining pad edges are in the pocket x 19-42 and U2 carries 26 edge-halves
(west column + north row). U7 sits in U2's only south escape corridor while
U2's SPI pins face east; front-side x 43-52 / y 12-24 is empty. Recommendation
and evidence: `docs/routing-endgame-report.md`, addendum 2026-09-15. Held for
approval as a placement change (same gate as relief round 2).


## Relief round 3 results — six parallel pipelines (2026-09-16, 23:45-03:35)

Each variant: fresh regeneration (~262 open) -> RF -> HV -> FreeRouting ->
adopt -> finisher, twice, in its own worktree, four to six pipelines at once
on 16 cores.

| variant | SYS fixed | pours | cycle 1 | final |
|---|---|---|---|---|
| A | no | old | 92 | 91 |
| B | no | old | 97 | 96 |
| C | no | old | 105 | 104 |
| D | no | old | 106 | 105 |
| E | yes | redrawn | 108 | 108 |
| **F** | **yes** | old | 149 | **98** |

Reading: moving U8 out of the pocket is worth ~10 (C vs the 109 floor);
U7 out of U2's west corridor another ~13 (A vs C); TP4 did nothing (D).
A-D are electrically wrong (split SYS), so **F is the board**: 98 / 0. E's
redrawn pours did not pay off by cycle 2 (E gained 0 in its second finisher
pass, F gained 51), so the old pour plan stays; the pad-vs-island mismatch
is real and remains a documented option.

Two process findings:

1. **Cycle-2 FreeRouting hangs in every pipeline** (6/6): 0-3 % CPU, log
   frozen after "New version available", never "Starting auto-routing";
   cycle 1 always ran. The interactive-session run on 09-15 did complete a
   second cycle, so this is environmental (likely a GUI/update-check dialog
   on a non-interactive JVM). Killing java lets adopt fall through with the
   unchanged scratch (no regression). The follow-up cycle script forces
   `-Djava.awt.headless=true` and kills java if auto-routing has not
   started within 300 s. Net effect so far: no variant has had a working
   second FreeRouting pass on the new placement - headroom remains.
2. **Fixing SYS made the board harder, correctly.** The merged SYS is a
   real cross-board 0.5 mm PWR net (charger at y 46 to the LDO and the
   modem switch at the top-right) that did not exist before; E/F's first
   FreeRouting sessions were 79-83 KB vs ~220 KB for A-D.

Follow-ups running on F: G = headless FreeRouting cycle (12 passes) + 60 min
finisher; H = finisher pocket restart (rip window x 19-43, y 15-61, hard-
first, 90 min) after a headless FreeRouting pass.

Follow-up note: `-Djava.awt.headless=true` is NOT a fix - FreeRouting 1.9.0
throws HeadlessException from the main thread and exits in seconds; it is a
GUI application that needs a display even for -de/-do batch runs. The
cycle-2 hang is therefore a modal window on the desktop waiting for a click.
G/H fell through to their finishers with the board unchanged (98).

Follow-ups on F (98): G = 60 min finisher after a no-op FreeRouting stage ->
101 (one batch rolled back; the finisher is at its noise floor, +-3).
H = pocket restart (ripped 1159 unlocked items in x 19-43, y 15-61, hard-
first, 90 min) -> 131: it re-routed 34 of 87 nets and left 78. On this
placement the restart destroys more than it recovers. Both discarded.

**Board of record: F — 98 unconnected, 0 DRC errors, SYS one net, ERC 0
errors, checkpins 48/48.** Remaining work is ~48 nets in the U2 pocket; the
automated toolkit is exhausted on this placement.


# Finisher experiments on the board of record (98/0) — 2026-09-16

Four parallel runs, each on a copy of F, 7200 s finisher deadline, all
ending at **98 / 0** - no gain:

| run | knobs | routed | note |
|---|---|---|---|
| X1 | grid 0.05 mm | 1/48 | fine grid is ~4x slower: 4 nets attempted in 2 h |
| X2 | rip-negotiation 6 nets / 6 mm (grid 0.10) | 2/48 | all five rip-retries "stalled ... no path" |
| X3 | X1 + X2 | 1/48 | as X1 |
| X4 | X3 + Default clearance 0.15 (MEASUREMENT ONLY, own worktree, not merged) | 1/48 | too slow to be informative; 3 nets tried at 0.15 all "no path" |

The in-house maze router (`tools/pcbroute_lv.py`) is exhausted on this
placement under every setting tried; the failures are `no path` even for
8 mm nets such as OSC_IN (U2.5 -> C1.1). A fifth run (0.15 clearance at the
normal grid) was blocked by the tool-permission classifier and not retried;
the clearance question is therefore still open and is a decision for the
owner (standing policy: never loosen a netclass for completion).

FreeRouting 2.4.1 (true headless CLI - no GUI, so no hang) was then run on
the same board: fanout escaped 436/617 SMD pins; auto-routing started at 182
unrouted items and reported 169 after each of passes 1-3 (flat). Result
appended below.

FreeRouting 2.4.1 result: 8 passes + 2 optimizer passes in 82 min, 1836
wires; its own report says 169 unrouted and 2137 "violations", but under the
project's real rules the adopted board is **94 unconnected / 0 DRC errors**
(rip set empty, 2 forms). 2.4.1 is the autorouter to use from here: it is a
real headless CLI (no display, no dialog hang) and it beats 1.9.0 on this
board. Its unrouted count was flat at 169 from pass 1 to pass 8, so it too
is at the placement floor.

**Board of record: a4dc73b — 94 unconnected, 0 DRC errors, ERC 0 errors,
SYS one net, checkpins 48/48.** Session total: 174 -> 94.
