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
*Next entry: storage.kicad_sch.*
