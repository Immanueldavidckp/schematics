#!/usr/bin/env python3
"""Audit the BOM against LCSC's own part data, line by line.

For every line of out/bom.csv this fetches the LCSC part (cached in
docs/lcsc-cache.json) and checks:

  value     the schematic value (Comment) against the part's capacitance /
            resistance / inductance / frequency / current rating / LED
            colour, or its part number
  voltage   a rating in the Comment ("25V") must not exceed the part's
  package   the footprint's package (0603, SOT-23, ...) against the part's
  crystal   each crystal's load capacitance against its two load caps
            (CL = C/2 + ~4 pF stray, within 2.5 pF)
  stock     JLCPCB stock (what JLCPCB assembly uses) or LCSC stock (what a
            local assembler buys from) covers the quantity for BOARDS boards
  number    a placeholder instead of an LCSC number is a failure

and writes docs/bom-audit.md (every line, OK or why not) and out/bom-mpn.csv
(the BOM plus manufacturer and manufacturer part number, which a local
assembler needs - they buy by MPN, not by LCSC code).

Run:  python3 tools/bom_audit.py [--boards N] [--offline]
Exit 1 if any line fails.
"""
import csv
import json
import os
import re
import sys
import time
import urllib.request

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOM = os.path.join(PROJ, "out", "bom.csv")
CACHE = os.path.join(PROJ, "docs", "lcsc-cache.json")
REPORT = os.path.join(PROJ, "docs", "bom-audit.md")
MPN_BOM = os.path.join(PROJ, "out", "bom-mpn.csv")
API = "https://wmsc.lcsc.com/ftps/wm/product/detail?productCode="
JLC_API = ("https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/"
           "selectSmtComponentList")
# crystal -> its two load capacitors (design knowledge: tools/sheets.py)
CRYSTAL_LOAD = {"Y1": ("C1", "C2"), "Y2": ("C3", "C4")}
C_STRAY = 4e-12
COLOURS = {"GRN": "Green", "GREEN": "Green", "BLU": "Blue", "BLUE": "Blue", "RED": "Red",
           "YEL": "Yellow", "WHT": "White", "AMB": "Amber", "ORG": "Orange"}

SI = {"p": 1e-12, "n": 1e-9, "u": 1e-6, "µ": 1e-6, "m": 1e-3, "": 1.0,
      "k": 1e3, "K": 1e3, "M": 1e6, "G": 1e9}


def fetch(code, cache, offline):
    if code in cache:
        return cache[code]
    if offline:
        return None
    req = urllib.request.Request(API + code, headers={"User-Agent": "Mozilla/5.0"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.load(r)
            res = d.get("result")
            cache[code] = res
            time.sleep(0.3)
            return res
        except Exception as e:            # noqa: BLE001 - retry any network error
            err = e
            time.sleep(2 * (attempt + 1))
    print(f"  fetch {code} failed: {err}", file=sys.stderr)
    return None


def jlc(code, cache, offline):
    """JLCPCB library entry for an exact C-number: (stock, basic) or None."""
    rec = jlc_record(code, cache, offline)
    return None if rec is None else [rec["stock"], rec["basic"]]


def jlc_record(code, cache, offline):
    """The JLCPCB library record for an exact C-number (dict) or None. Also
    stands in for the LCSC detail when LCSC refuses a lookup (it does for a
    few parts, e.g. the EC200U module)."""
    key = "JLC2:" + code
    if key in cache:
        return cache[key]
    if offline:
        return None
    req = urllib.request.Request(
        JLC_API, data=json.dumps({"keyword": code, "currentPage": 1, "pageSize": 25}).encode(),
        headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                lst = json.load(r)["data"]["componentPageInfo"]["list"] or []
            hit = next((c for c in lst if c.get("componentCode") == code), None)
            cache[key] = ({"stock": hit.get("stockCount") or 0,
                           "basic": hit.get("componentLibraryType") == "base",
                           "mpn": hit.get("componentModelEn") or "",
                           "brand": hit.get("componentBrandEn") or "",
                           "pkg": hit.get("componentSpecificationEn") or "",
                           "desc": hit.get("describe") or ""}
                          if hit else {"stock": 0, "basic": False, "mpn": "", "brand": "",
                                       "pkg": "", "desc": ""})
            time.sleep(0.3)
            return cache[key]
        except Exception:                 # noqa: BLE001 - retry any network error
            time.sleep(2 * (attempt + 1))
    return None


def num(s, unit):
    """'4.7uF' -> 4.7e-6 ; '4k7' -> 4700 ; '60.4R' / '60.4Ω' -> 60.4 ; '0R' -> 0."""
    s = s.strip().replace("Ω", "R").replace("ohm", "R").replace(" ", "")
    m = re.fullmatch(r"(\d+(?:\.\d+)?)([pnuµmkKMG]?)" + unit + r"?", s, re.I if unit != "R" else 0)
    if m:
        return float(m.group(1)) * SI[m.group(2)]
    m = re.fullmatch(r"(\d+)([kKMR])(\d+)", s)          # 4k7, 2R2
    if m:
        return float(f"{m.group(1)}.{m.group(3)}") * (1.0 if m.group(2) == "R" else SI[m.group(2)])
    return None


def params(res):
    return {p.get("paramNameEn", ""): p.get("paramValueEn", "") for p in (res.get("paramVOList") or [])}


def pkg_of_footprint(fp):
    name = fp.split(":")[-1]
    m = re.search(r"_(0201|0402|0603|0805|1008|1206|1210|1812|2010|2512)_", name + "_")
    if m:
        return m.group(1)
    m = re.search(r"(?:^|_)L?(0201|0402|0603|0805|1008|1206|1210|1812|2010|2512)(?:$|_)", name)
    if m:
        return m.group(1)
    for k in ("SOT-23-6", "SOT-23-5", "SOT-363", "SOT-23", "SOD-123FL", "SOD-123", "LQFP-48",
              "VQFN-24", "TSSOP-14", "SOIC-8", "SOP-8", "LGA-14", "D_SMA", "D_SMB", "D_SMC",
              "SMB", "SMA", "SMC", "3225", "3215"):
        # whole token only: LGA-14 must not match the module's LGA-144
        if re.search(rf"(?<![A-Za-z0-9]){re.escape(k)}(?![0-9])", name, re.I):
            return {"D_SMA": "SMA", "D_SMB": "SMB", "D_SMC": "SMC"}.get(k, k)
    return None


def norm(s):
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def pkg_ok(fp_pkg, lcsc_pkg):
    if fp_pkg is None or not lcsc_pkg or norm(lcsc_pkg) in ("SMD", "SMT", "PLUGIN"):
        return None          # nothing specific to compare against
    a, b = norm(fp_pkg), norm(lcsc_pkg)
    alias = {"SMA": ["SMA", "DO214AC"], "SMB": ["SMB", "DO214AA"], "SMC": ["SMC", "DO214AB"],
             "SOT23": ["SOT23", "SOT233", "TO236"], "SOIC8": ["SOIC8", "SOP8"],
             "SOT363": ["SOT363", "SC88", "SC706"],
             "SOP8": ["SOP8", "SOIC8"], "SOD123FL": ["SOD123FL", "SOD123F"],
             "3225": ["3225", "SMD3225", "SMD32254P", "SMD322504P"],
             "3215": ["3215", "SMD3215", "FC135", "SMD32152P"]}
    return any(x in b for x in alias.get(a, [a]))


def check_value(comment, res):
    """(ok, note) - ok None when there is nothing comparable."""
    p = params(res)
    first = comment.split()[0] if comment.split() else ""
    if "Illumination Color" in p:
        want = COLOURS.get(first.upper())
        have = p["Illumination Color"]
        if want is None:
            return None, f"LED {have}"
        return want.lower() in have.lower(), f"LED {have}"
    m = re.fullmatch(r"(\d+(?:\.\d+)?)(m?)A", first)
    if m and "Current Rating" in p:
        want = float(m.group(1)) * (1e-3 if m.group(2) else 1.0)
        have = num(p["Current Rating"], "A")
        return (have is not None and abs(have - want) < 1e-9), f"rated {p['Current Rating']}"
    for name, unit in (("Capacitance", "F"), ("Resistance", "R"), ("Inductance", "H"),
                       ("Frequency", "Hz")):
        if name in p:
            want = num(first, unit) if unit != "Hz" else num(first.replace("Hz", ""), "")
            have = num(p[name].split("@")[0].strip(), unit) if unit != "Hz" else \
                num(p[name].replace("Hz", "").strip(), "")
            if want is None or have is None:
                return None, f"{name} {p[name]} (could not compare '{first}')"
            ok = abs(want - have) <= 1e-9 * max(abs(want), 1e-15) or (want == 0 and have == 0) or \
                (want and abs(want - have) / want < 0.005)
            return ok, f"{name} {p[name]}"
    # a record with no parameters (JLCPCB-only): the value must appear in the
    # description, e.g. 600R@100MHz -> "600Ω@100MHz"
    if not p and res.get("_jlc_only") and re.match(r"\d", first):
        want = first.replace("R@", "Ω@").replace("R", "Ω") if "@" in first else first
        if want.lower() in (res.get("productNameEn") or "").lower():
            return True, f"{want} in JLCPCB description"
    # not a passive: the comment should name the part
    mpn = res.get("productModel", "")
    c, m = norm(comment), norm(mpn)
    if c and m and (c in m or m in c or c[:6] == m[:6]):
        return True, f"part {mpn}"
    return False, f"part {mpn} vs '{comment}'"


def check_voltage(comment, res):
    m = re.search(r"(\d+(?:\.\d+)?)\s*V\b", comment)
    if not m:
        return None, ""
    want = float(m.group(1))
    v = (params(res).get("Voltage Rating") or params(res).get("Voltage - Rated")
         or params(res).get("Voltage Rating (DC)") or "")
    mv = re.search(r"(\d+(?:\.\d+)?)\s*V", v)
    if not mv:
        return None, "no voltage rating listed"
    return float(mv.group(1)) >= want, f"rated {v}"


def main():
    boards = 10
    if "--boards" in sys.argv:
        boards = int(sys.argv[sys.argv.index("--boards") + 1])
    offline = "--offline" in sys.argv
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    rows = list(csv.DictReader(open(BOM, newline="", encoding="utf-8")))
    out, bad = [], 0
    for r in rows:
        code = r["LCSC"].strip()
        refs = r["Designator"]
        qty = len([x for x in re.split(r",\s*", refs) if x]) if refs else 0
        # expand ranges like C8-C11
        qty = 0
        for part in re.split(r",\s*", refs):
            m = re.fullmatch(r"([A-Z]+)(\d+)-[A-Z]*(\d+)", part.strip())
            qty += (int(m.group(3)) - int(m.group(2)) + 1) if m else (1 if part.strip() else 0)
        notes, ok = [], True
        res = None
        if not re.fullmatch(r"C\d+", code):
            ok, notes = False, [f"no LCSC number ('{code}')"]
        else:
            res = fetch(code, cache, offline)
            if not res:
                rec = jlc_record(code, cache, offline)
                if rec and rec["mpn"]:
                    # LCSC refused the lookup; judge the part on JLCPCB's record
                    res = {"productModel": rec["mpn"], "brandNameEn": rec["brand"],
                           "encapStandard": rec["pkg"], "productNameEn": rec["desc"][:90],
                           "stockNumber": 0, "paramVOList": [], "_jlc_only": True}
                    notes.append("LCSC lookup refused; JLCPCB record used")
                else:
                    ok, notes = False, ["LCSC lookup failed"]
        if res:
            v_ok, v_note = check_value(r["Comment"], res)
            if v_ok is False:
                ok = False
                notes.append(f"VALUE: {v_note}")
            elif v_note:
                notes.append(v_note)
            vo, vn = check_voltage(r["Comment"], res)
            if vo is False:
                ok = False
                notes.append(f"VOLTAGE: {vn}")
            fp_pkg = pkg_of_footprint(r["Footprint"])
            po = pkg_ok(fp_pkg, res.get("encapStandard", ""))
            if po is False:
                ok = False
                notes.append(f"PACKAGE: footprint {fp_pkg} vs part {res.get('encapStandard')}")
            stock = res.get("stockNumber") or 0
            j = jlc(code, cache, offline)
            jstock, basic = (j or [0, False])
            r["_jlc"] = f"{'basic' if basic else 'extended'} {jstock}" if j else "?"
            if max(stock, jstock) < qty * boards:
                ok = False
                notes.append(f"STOCK: LCSC {stock}, JLCPCB {jstock} < {qty * boards}")
            elif stock < qty * boards:
                notes.append(f"LCSC retail {stock} (JLCPCB {jstock} ok)")
        if not ok:
            bad += 1
        out.append(dict(r, Qty=qty, Status="OK" if ok else "FIX", JLC=r.get("_jlc", ""),
                        _res=res,
                        Manufacturer=(res or {}).get("brandNameEn", ""),
                        MPN=(res or {}).get("productModel", ""),
                        Package=(res or {}).get("encapStandard", ""),
                        Description=(res or {}).get("productNameEn", ""),
                        Stock=(res or {}).get("stockNumber", ""),
                        Notes="; ".join(notes)))
    # crystal load: CL_eff = series of the two caps + stray, against the crystal's CL
    by_ref = {}
    for o in out:
        for part in re.split(r",\s*", o["Designator"]):
            m = re.fullmatch(r"([A-Z]+)(\d+)-[A-Z]*(\d+)", part.strip())
            refs = [f"{m.group(1)}{i}" for i in range(int(m.group(2)), int(m.group(3)) + 1)] if m \
                else [part.strip()]
            for rr in refs:
                by_ref[rr] = o
    for y, (ca, cb) in CRYSTAL_LOAD.items():
        oy, oa, ob = by_ref.get(y), by_ref.get(ca), by_ref.get(cb)
        if not (oy and oa and ob and oy["_res"]):
            continue
        cl = num(params(oy["_res"]).get("Load Capacitance", ""), "F")
        c1, c2 = num(oa["Comment"].split()[0], "F"), num(ob["Comment"].split()[0], "F")
        if cl is None or not c1 or not c2:
            continue
        eff = c1 * c2 / (c1 + c2) + C_STRAY
        note = f"load: crystal CL {cl * 1e12:.1f} pF, {ca}/{cb} give {eff * 1e12:.1f} pF"
        oy["Notes"] = "; ".join(x for x in (oy["Notes"], note) if x)
        if abs(eff - cl) > 2.5e-12:
            if oy["Status"] != "FIX":
                bad += 1
            oy["Status"] = "FIX"
            oy["Notes"] = oy["Notes"].replace("load:", "LOAD:")
    json.dump(cache, open(CACHE, "w"), indent=0, sort_keys=True)
    with open(MPN_BOM, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL)
        w.writerow(["Comment", "Designator", "Qty", "Footprint", "Manufacturer", "MPN", "LCSC",
                    "Description"])
        for o in out:
            w.writerow([o["Comment"], o["Designator"], o["Qty"], o["Footprint"], o["Manufacturer"],
                        o["MPN"], o["LCSC"], o["Description"]])
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("# BOM audit against LCSC part data\n\n")
        f.write(f"Generated by `tools/bom_audit.py` from `out/bom.csv`; stock checked for "
                f"{boards} boards. {len(out)} lines, {sum(o['Qty'] for o in out)} parts, "
                f"**{bad} line(s) to fix**.\n\n")
        f.write("| status | designators | value | footprint | LCSC | JLCPCB | manufacturer / MPN | LCSC says | notes |\n")
        f.write("|---|---|---|---|---|---|---|---|---|\n")
        for o in sorted(out, key=lambda o: o["Status"] != "FIX"):
            f.write(f"| {'**FIX**' if o['Status'] == 'FIX' else 'ok'} | {o['Designator']} | {o['Comment']} | "
                    f"{o['Footprint'].split(':')[-1]} | {o['LCSC']} | {o['JLC']} | {o['Manufacturer']} {o['MPN']} | "
                    f"{o['Description']} | {o['Notes']} |\n")
    for o in out:
        if o["Status"] == "FIX":
            print(f"FIX  {o['Designator'][:28]:28s} {o['Comment'][:18]:18s} {o['LCSC']:10s} {o['Notes']}")
    print(f"BOM_AUDIT lines={len(out)} fix={bad} -> {REPORT}, {MPN_BOM}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
