#!/usr/bin/env python3
"""Purchase BOM for buying the parts yourself (India): one line per part with
the words to ask for at a component shop, the exact manufacturer part number,
what substitutes are acceptable, where the part is realistically available,
and how many to buy for N boards with spares.

Reads out/bom-mpn.csv (written by tools/bom_audit.py). Writes
docs/bom-india-purchase.csv, .html and .pdf.

  PYTHONPATH=tools python3 tools/bom_india.py [--boards 5]
"""
import argparse
import csv
import html
import math
import os
import re
import subprocess

TOOLS = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(TOOLS)
SRC = os.path.join(PROJ, "out", "bom-mpn.csv")
DOCS = os.path.join(PROJ, "docs")

# Where a part is realistically bought in India
SOURCES = {
    "L": "Local SMD shop / Robu / Evelta",
    "D": "Distributor: Mouser India / DigiKey India / element14 India",
    "C": "LCSC direct (lcsc.com, ships to India) - China-brand part",
    "Q": "Quectel India distributor (or Mouser India)",
}

# Per-part guidance keyed by LCSC number: (ask-for wording, substitute rule,
# source code). Resistors and capacitors not listed here get generic wording.
G = {
    "C53133524": ("U.FL / IPEX MHF1 SMD RF receptacle (2 mm)", "Any brand U.FL (IPEX1 / MHF1) receptacle", "L"),
    "C84494": ("SMD ceramic capacitor 1210, 47 uF, 10 V, X7R", "Murata/Samsung/TDK, must be X7R and 1210; X5R not accepted", "D"),
    "C109040": ("SMD ceramic capacitor 0805, 10 uF, 25 V, X7R or X7S", "Any brand, X7R/X7S; X5R not accepted", "D"),
    "C5449052": ("SMD ceramic capacitor 1210, 2.2 uF, 100 V, X7R", "Any brand, MUST be rated 100 V, X7R, 1210", "D"),
    "C5204901": ("Rectifier diode S3M, 3 A 1000 V, SMB (DO-214AA)", "Any brand S3M", "L"),
    "C1977839": ("TVS diode SMDJ100A, 100 V standoff, 3000 W, SMC (DO-214AB), UNIDIRECTIONAL", "Littelfuse / Bourns / Vishay SMDJ100A. NOT the bidirectional SMDJ100CA", "D"),
    "C15771": ("CAN bus ESD/TVS diode PESD1CAN, SOT-23", "Nexperia PESD1CAN or NUP2105L (onsemi)", "D"),
    "C2501": ("Dual diode BAV70 (common cathode), SOT-23", "Any brand BAV70", "L"),
    "C65001": ("Schottky diode SS3200, 3 A 200 V, SMA (DO-214AC)", "Any brand SS3200 or SS3200-class 200 V 3 A schottky in SMA. SS34 (40 V) is NOT acceptable", "L"),
    "C2500": ("Dual diode BAV99 (series pair), SOT-23", "Any brand BAV99", "L"),
    "C193402": ("TVS diode SMF5.0A, 5 V unidirectional, SOD-123FL", "Any brand SMF5.0A", "L"),
    "C2286": ("SMD LED 0603 red", "Any brand 0603 red LED", "L"),
    "C12624": ("SMD LED 0603 green", "Any brand 0603 green LED", "L"),
    "C2288": ("SMD LED 0603 blue", "Any brand 0603 blue LED", "L"),
    "C179747": ("ESD diode array PESD5V0L5UY, 5-line, SOT-363 (SC-70-6)", "Nexperia PESD5V0L5UY; else a 5-line 5 V SOT-363 array with pin 2 = GND and <= 15 pF/line", "D"),
    "C7519": ("USB ESD protection USBLC6-2SC6, SOT-23-6", "ST USBLC6-2SC6 or any brand with the same name/pinout", "D"),
    "C95352": ("SMD fuse 1 A 250 V, Littelfuse 0443 series (Nano2, 10.1 x 3.1 mm)", "Littelfuse 0443001.DR only (footprint-specific)", "D"),
    "C1017": ("Ferrite bead 0805, 600 ohm @ 100 MHz, >= 500 mA", "Any brand 0805 600R ferrite bead", "L"),
    "C7588012": ("Micro-Fit 3.0 compatible header, 2 x 6 = 12 pins, 3.0 mm pitch, VERTICAL through-hole (the harness connector)", "Molex 43045 series 12-circuit vertical header, or XUNPU WAFER-MX3.0-12PZZ from LCSC", "D"),
    "C144394": ("JST XH 3-pin vertical through-hole header, 2.5 mm (B3B-XH-A) - battery connector", "JST B3B-XH-A or any XH-compatible 3-pin vertical header", "L"),
    "C21325": ("Shielded power inductor 150 uH, 12.3 x 12.3 mm, Isat >= 2.7 A, DCR <= 0.3 ohm", "Any 12 x 12 mm shielded 150 uH inductor with Isat >= 2.7 A (check the datasheet)", "D"),
    "C76584": ("Common-mode choke TDK ACT45B-510-2P (51 uH, CAN bus)", "TDK ACT45B-510-2P-TL003 only (footprint-specific)", "D"),
    "C391305": ("Power inductor 2.2 uH, 2.5 x 2.0 mm (1008 / 2520), >= 2.2 A", "Murata DFE252012P-2R2M or same-size metal-alloy 2.2 uH >= 2 A", "D"),
    "C3221844": ("Chip inductor 68 nH 0402 (GNSS antenna bias)", "Any brand 0402 68 nH wire-wound, +/-2 or 5 %", "D"),
    "C359074": ("Optocoupler EL357N, 4-pin SMD (SOP-4), high-CTR bin", "Everlight EL357N - see note on the CTR bin in the report", "D"),
    "C51886143": ("N-channel MOSFET AM2390N, 150 V, SOT-23", "Exact from LCSC preferred. Substitute only if: SOT-23, VDS >= 100 V, ID >= 1 A, RDS(on) specified at VGS 4.5 V", "C"),
    "C15127": ("P-channel MOSFET AO3401A, 30 V 4 A, SOT-23", "Any brand AO3401A", "L"),
    "C20526": ("NPN transistor MMBT3904, SOT-23", "Any brand MMBT3904", "L"),
    "C75549": ("PNP transistor MMBT3906, SOT-23", "Any brand MMBT3906", "L"),
    "C55348540": ("SMD resistor 2512, 1 ohm, 1 %, ANTI-SURGE / pulse-withstanding type, >= 1 W", "Any brand 2512 1R 1 % anti-surge (not a plain thick film)", "D"),
    "C327057": ("SMD current-sense resistor 0805, 0.1 ohm, 1 %, >= 0.25 W", "Any brand 0805 0R1 1 %", "D"),
    "C137091": ("SMD resistor 1210, 68 ohm, 1 %, 0.5 W", "Any brand 1210 68R 1 %", "D"),
    "C2916205": ("LTE Cat 1 + GNSS module Quectel EC200U-CN (EC200UCNAA-N05-SGNSA), LCC-144", "Exact part. Buy from a Quectel India distributor or Mouser India", "Q"),
    "C55058656": ("MCU Artery AT32F403ACGT7, LQFP-48", "Exact part (LCSC or Artery's India distributor)", "C"),
    "C5380158": ("IMU QST QMI8658B, LGA-14", "Exact part (LCSC)", "C"),
    "C5382551": ("CAN transceiver SIT1051AT/3, SOP-8, 3.3 V I/O", "NXP TJA1051T/3 (pin-compatible, Mouser/DigiKey) is the substitute", "C"),
    "C53368402": ("Buck converter EG Micro EG11752, SOIC-8 with exposed pad, 100 V", "Exact part, LCSC only - no substitute", "C"),
    "C374063": ("Battery charger TI BQ25606RGER, VQFN-24", "Exact part", "D"),
    "C2831359": ("SPI NOR flash GD25Q64ESIGR 64 Mbit, SOIC-8 208 mil (5.3 mm wide), industrial grade", "GigaDevice GD25Q64E or Winbond W25Q64JVSSIQ (same package)", "D"),
    "C60708": ("Level shifter TI TXB0104PWR, TSSOP-14", "Exact part (TI TXB0104PWR)", "D"),
    "C82942": ("LDO 3.3 V 500 mA ME6211C33M5G, SOT-23-5", "Diodes AP2112K-3.3 (same SOT-23-5 pinout VIN-GND-EN-NC-VOUT) is the substitute", "C"),
    "C53207808": ("Nano-SIM card holder, push-push, 7 pins, 1.37 mm height, SMD", "Exact from LCSC, or another nano-SIM push-push holder ONLY if its footprint matches the drawing", "C"),
    "C2682775": ("Crystal 8 MHz, SMD 3225 (3.2 x 2.5 mm) 4-pin, load capacitance 12 pF", "Any brand 8 MHz 3225 with CL = 12 pF", "L"),
    "C48615": ("Crystal 32.768 kHz, SMD 3215 (3.2 x 1.5 mm) 2-pin, load capacitance 7 pF", "Epson FC-135 / Q13FC13500002 or any 3215 32.768 kHz with CL = 7 pF", "D"),
}

E24 = {"1", "1.1", "1.2", "1.3", "1.5", "1.6", "1.8", "2", "2.2", "2.4", "2.7", "3", "3.3", "3.6", "3.9",
       "4.3", "4.7", "5.1", "5.6", "6.2", "6.8", "7.5", "8.2", "9.1"}


def r_generic(comment, desc):
    """'RES 10kΩ ±1% 125mW 0805' -> ask-for text, substitute rule, source."""
    m = re.search(r"RES ([\d.]+)([kM]?)Ω.*?(\d{4})$", desc)
    if not m:
        return None
    val, mult, size = m.groups()
    num = float(val)
    mant = ("%g" % (num / 10 ** math.floor(math.log10(num)))) if num > 0 else "0"
    common = num == 0 or mant in E24
    ask = f"SMD resistor {size}, {val} {mult}ohm, 1 %".replace(" ohm", "ohm").replace("0 ohm", "0 ohm (jumper)")
    ask = f"SMD resistor {size}, {val}{mult} ohm, 1 %" if num else f"SMD resistor {size}, 0 ohm (jumper link)"
    return (ask, "Any brand, 1 %" + ("" if common else " - E96 value, may need a distributor"), "L" if common else "D")


def c_generic(comment, desc):
    m = re.search(r"CAP CER ([\d.]+[pnu]F) (\d+)V (\w+) (\d{4})$", desc)
    if not m:
        return None
    val, volt, diel, size = m.groups()
    ask = f"SMD ceramic capacitor {size}, {val}, {volt} V, {diel}"
    rule = "Any brand, same dielectric (C0G/NP0 required)" if diel == "C0G" else f"Any brand, must be {diel} (X5R/Y5V not accepted), >= {volt} V"
    return (ask, rule, "L")


def buy_qty(kind, per_board, boards):
    n = per_board * boards
    if kind in ("R", "C", "FB", "L4"):          # sold in strips; spares are free insurance
        return max(20, int(math.ceil(n * 1.5 / 10.0) * 10))
    if kind == "Y":
        return n + 2
    return n + max(1, int(math.ceil(n * 0.2)))


def kind_of(ref):
    return re.match(r"[A-Z]+", ref).group(0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--boards", type=int, default=5)
    a = ap.parse_args()
    rows = list(csv.DictReader(open(SRC, newline="", encoding="utf-8")))
    out = []
    for r in rows:
        refs = [d.strip() for d in r["Designator"].split(",")]
        k = kind_of(refs[0])
        lcsc = r["LCSC"]
        g = G.get(lcsc)
        if g is None and k == "R":
            g = r_generic(r["Comment"], r["Description"])
        if g is None and k == "C":
            g = c_generic(r["Comment"], r["Description"])
        if g is None:
            g = (f'{r["Description"] or r["Comment"]} ({r["Footprint"].split(":")[-1]})', "Exact part", "D")
        ask, rule, src = g
        per = int(r["Qty"])
        out.append({
            "Source": src,
            "Ask for (what to say at the shop)": ask,
            "Manufacturer": r["Manufacturer"],
            "Part number": r["MPN"],
            "LCSC": lcsc,
            "Substitute allowed?": rule,
            "Designators": r["Designator"],
            "Per board": per,
            f"For {a.boards} boards": per * a.boards,
            "Buy (with spares)": buy_qty("L4" if lcsc == "C3221844" else k, per, a.boards),
            "Package": r["Footprint"].split(":")[-1],
        })
    order = {"L": 0, "D": 1, "C": 2, "Q": 3}
    out.sort(key=lambda x: (order[x["Source"]], x["Designators"]))

    os.makedirs(DOCS, exist_ok=True)
    csv_path = os.path.join(DOCS, "bom-india-purchase.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()), quoting=csv.QUOTE_ALL)
        w.writeheader()
        for row in out:
            row = dict(row, Source=SOURCES[row["Source"]])
            w.writerow(row)

    # printable list, one table per source
    parts = [f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Parts purchase list</title>
<style>@page{{size:A4 landscape;margin:10mm}}body{{font:9pt/1.3 "DejaVu Sans",Arial,sans-serif;color:#111}}
h1{{font-size:15pt;margin:0 0 2mm}}h2{{font-size:11.5pt;margin:6mm 0 2mm;border-bottom:1.5px solid #333;page-break-after:avoid}}
table{{border-collapse:collapse;width:100%;font-size:8.3pt}}th,td{{border:1px solid #999;padding:1mm 1.5mm;vertical-align:top;text-align:left}}
th{{background:#eee}}tr{{page-break-inside:avoid}}td.n{{text-align:right;white-space:nowrap}}.small{{color:#444;font-size:8pt}}</style></head><body>
<h1>Telematics tracker - parts purchase list ({a.boards} boards + spares)</h1>
<p class="small">From the verified BOM (tag v1.0.4-mfg-2026-09-30, {len(out)} lines). "Ask for" is the plain description to give a shop; the part number is the exact part
the design was checked with; the substitute column says when another brand or part is acceptable. Buy quantities include spares. Passives are usually sold in strips of 10/50/100.</p>"""]
    for code in ("L", "D", "C", "Q"):
        grp = [x for x in out if x["Source"] == code]
        if not grp:
            continue
        parts.append(f"<h2>{html.escape(SOURCES[code])} - {len(grp)} lines</h2><table><tr><th>Buy</th><th>Ask for</th><th>Part number (manufacturer)</th><th>LCSC</th><th>Substitute allowed?</th><th>Designators</th><th>Per board</th></tr>")
        for x in grp:
            parts.append(f'<tr><td class="n"><b>{x["Buy (with spares)"]}</b></td><td>{html.escape(x["Ask for (what to say at the shop)"])}</td>'
                         f'<td>{html.escape(x["Part number"])}<br><span class="small">{html.escape(x["Manufacturer"])}</span></td><td>{x["LCSC"]}</td>'
                         f'<td>{html.escape(x["Substitute allowed?"])}</td><td class="small">{html.escape(x["Designators"])}</td><td class="n">{x["Per board"]}</td></tr>')
        parts.append("</table>")
    parts.append("""<h2>Notes</h2><ul>
<li><b>Never substitute</b> without checking: U5 (EG11752), U1 (modem), U2 (MCU), U3 (IMU), U6 (charger), U8 (TXB0104), L2 (CAN choke), F1 (fuse footprint), D2 (must be the unidirectional SMDJ100A), crystals (load capacitance), the SIM holder (footprint).</li>
<li>Capacitor dielectric matters: buy X7R where it says X7R (many shops offer X5R/Y5V by default - refuse them); C0G/NP0 for the crystal and RF capacitors.</li>
<li>E96 resistor values (60.4R, 536R, 976R, 5.23k, 30.1k) are rarely in local shops - order those from a distributor with the rest of the "D" list.</li>
<li>LCSC ships the exact C-numbers to India (courier + customs duty); it is the only source for the China-brand parts in the "C" list, and usually the cheapest for everything else.</li>
<li>Assembly: the modem (LCC-144), charger (QFN-24, thermal pad) and IMU (LGA-14) need a stencil and reflow. Order the stencil with the bare boards (JLCPCB, ~$7) and use a local SMT shop, or a hot plate/oven at home for the first boards.</li>
</ul></body></html>""")
    html_path = os.path.join(DOCS, "bom-india-purchase.html")
    open(html_path, "w", encoding="utf-8").write("\n".join(parts))
    pdf_path = os.path.join(DOCS, "bom-india-purchase.pdf")
    subprocess.run(["google-chrome-stable", "--headless", "--disable-gpu", "--no-sandbox", "--no-pdf-header-footer",
                    f"--print-to-pdf={pdf_path}", html_path], capture_output=True, timeout=120)
    counts = {c: sum(1 for x in out if x["Source"] == c) for c in SOURCES}
    print(f"purchase BOM: {len(out)} lines -> {csv_path}, {pdf_path}  (local {counts['L']}, distributor {counts['D']}, LCSC-only {counts['C']}, Quectel {counts['Q']})")


if __name__ == "__main__":
    main()
