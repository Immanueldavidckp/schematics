"""Build out/bom-local-purchase.xlsx: the schematic BOM grouped for local
(Indian market) price comparison, with BOM flags and a per-ref list.

Usage: python tools/bom_local.py   (run from the repo root; needs openpyxl)
Part metadata (specs, MPNs, substitution rules, notes) is hand-maintained in
the M / P tables below, sourced from design-log.md and the handoff spec.
"""
import json, re, sys, collections, os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
def parse(s):
    toks = re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()"]+', s)
    stack=[[]]
    for t in toks:
        if t=='(':
            stack.append([])
        elif t==')':
            x=stack.pop(); stack[-1].append(x)
        else:
            stack[-1].append(t[1:-1].replace('\\"','"') if t.startswith('"') else t)
    return stack[0]
parts=[]
for sh in ["power","mcu","io","modem_rf","storage"]:
    tree=parse(open(f"{sh}.kicad_sch").read())[0]
    for n in tree:
        if isinstance(n,list) and n and n[0]=="symbol" and any(isinstance(c,list) and c[0]=="lib_id" for c in n):
            lib=[c[1] for c in n if isinstance(c,list) and c[0]=="lib_id"][0]
            props={c[1]:c[2] for c in n if isinstance(c,list) and c[0]=="property"}
            flags={c[0]:c[1] for c in n if isinstance(c,list) and c[0] in("in_bom","dnp","on_board")}
            ref=props.get("Reference","")
            if ref.startswith("#"): continue
            parts.append(dict(sheet=sh,lib=lib,ref=ref,val=props.get("Value",""),fp=props.get("Footprint","").split(":")[-1],
              lcsc=props.get("LCSC") or props.get("LCSC Part",""),mpn=props.get("MPN",""),mfr=props.get("Manufacturer",""),
              desc=props.get("Description",""),dnp=flags.get("dnp","no"),inbom=flags.get("in_bom","yes")))
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.comments import Comment
from openpyxl.worksheet.datavalidation import DataValidation


def pkg(fp):
    m=re.match(r'[RCL]_(\d{4})_',fp)
    if m: return m.group(1)
    return {"LED_0603_1608Metric":"0603","SOT-23":"SOT-23","D_SMA":"SMA (DO-214AC)","D_SMC":"SMC (DO-214AB)",
            "Crystal_SMD_3225-4Pin_3.2x2.5mm":"SMD 3225 4-pin","Crystal_SMD_3215-2Pin_3.2x1.5mm":"SMD 3215 2-pin",
            "JST_XH_B3B-XH-A_1x03_P2.50mm_Vertical":"JST-XH 3-pin vertical TH"}.get(fp, fp.split("_")[0])

def norm(v):
    v=re.sub(r'\s*\(F-\d+\)','',v)
    v=re.sub(r'\s+(25V)$','',v)
    return v.strip()

# ---------- group ----------
groups=collections.OrderedDict(); pcb_only=[]; dnp=[]
for p in parts:
    r=p["ref"]
    if r.startswith("TP") or r.startswith("JP"): pcb_only.append(p); continue
    if p["dnp"]=="yes": dnp.append(p); continue
    v=norm(p["val"]); k=(v,pkg(p["fp"]))
    if r=="C72": k=("100nF","0603","VIN")
    if r in("D20","D21","D13"): k=("LED","0603")
    if r in("R56","R58"): k=("47k","0805")
    groups.setdefault(k,[]).append(p)

def refsort(rs):
    return sorted(rs,key=lambda x:(re.match(r'[A-Z]+',x).group(),int(re.search(r'\d+',x).group())))

# ---------- metadata ----------
# subst: E = exact part only, Q = equivalent with same key specs, G = generic OK
X,Q,G="Exact part only","Equivalent OK (match key specs)","Generic OK"
J="JLC/LCSC ~Aug-2026, "
M={
("EC200UCNAA-N05-SGNSA","LCC"):("1 Modules & ICs","LTE Cat-1bis + GNSS modem","Quectel EC200UCNAA-N05-SGNSA",9.91,J+"@250+ (handoff §3)",X,"Buy from Quectel distributor only. Grey-market modules often have wrong firmware/region. Variant must be -N05-SGNSA (GNSS)."),
("AT32F403ACGT7","LQFP-48"):("1 Modules & ICs","MCU Cortex-M4 240 MHz, LQFP-48","Artery AT32F403ACGT7",1.69,J+"@250+ (handoff §3)",X,"Firmware is written for this exact chip. Do not swap to STM32F103 even if pin-compatible."),
("QMI8658B","LGA-14"):("1 Modules & ICs","6-axis IMU, I2C, LGA-14 3.0x2.5","QST QMI8658B",0.80,J+"@250+ (handoff §3)",X,"LGA part. Needs reflow/hot-air, not hand iron."),
("SIT1051AT/3","SOP-8"):("1 Modules & ICs","CAN-FD transceiver, 3.3 V VIO, SOP-8","SIT SIT1051AT/3",0.30,J+"@250+ (handoff §3)",Q,"Pin-compatible equivalents: TJA1051T/3, TCAN1051HV. Must be the /3 (VIO pin) version."),
("EG11752","SOIC-8"):("1 Modules & ICs","200 V buck regulator to 5V0, SOIC-8 EP","EG Micro EG11752",None,"price not recorded in repo",X,"Only 200 V-rated part that passed the design rule (design log 2026-09-02). Not a common local part. Plan to buy from LCSC."),
("BQ25606RGER","VQFN-24"):("1 Modules & ICs","1S Li-ion charger + power path, VQFN-24 4x4","TI BQ25606RGER",1.62,J+"@250+ (handoff §3)",X,"Genuine TI only. Counterfeits are common in local markets."),
("GD25Q64ESIGR","SOP-8"):("1 Modules & ICs","64 Mbit (8 MB) SPI NOR flash, SOP-8 208mil","GigaDevice GD25Q64ESIGR",0.492,"LCSC (design log F-3)",Q,"W25Q64JVSSIQ (Winbond) is an approved equivalent. Must be 208-mil SOP-8 body, not 150-mil SOIC."),
("TXB0104PWR","TSSOP-14"):("1 Modules & ICs","4-ch auto-direction level shifter, TSSOP-14","TI TXB0104PWR",0.30,"estimate (handoff §3)",X,"TSSOP-14 package specifically. Not the SOIC or QFN version."),
("ME6211C33M5G","SOT-23-5"):("1 Modules & ICs","3.3 V LDO 500 mA, SOT-23-5","MICRONE ME6211C33M5G",0.15,"estimate (handoff §3)",Q,"Pin-compatible: XC6220/ME6217 class. Check pinout: 1=VIN 2=GND 3=EN 4=NC 5=VOUT."),
("EL357N(D)","OPTO-SMD-4"):("2 Discretes","Optocoupler, CTR (D) bin 300-600%, SOP-4","Everlight EL357N(D)",0.06,"estimate (handoff §3)",Q,"Must be the (D) high-CTR bin. A plain EL357N may not switch at low input voltage."),
("AM2390N-TP","SOT-23-3"):("2 Discretes","N-MOSFET 150 V 4 A, logic-level, SOT-23","AM2390N-TP",0.084,J+"@500 (design log)",Q,"Needs VDS≥100 V, ID≥1 A, Vgs(th)≤2.5 V, RDS spec'd at 4.5 V. AO3400 is NOT OK (30 V only)."),
("AO3401A","SOT-23-3"):("2 Discretes","P-MOSFET -30 V 4 A, SOT-23","AOS AO3401A",0.05,"estimate (handoff §3)",G,"Very common locally."),
("MMBT3904","SOT-23"):("2 Discretes","NPN small-signal, SOT-23","MMBT3904 (marking 1AM)",None,"",G,"Very common locally."),
("MMBT3906","SOT-23"):("2 Discretes","PNP small-signal, SOT-23","Nexperia MMBT3906,215 (marking 2A)",None,"",G,"Very common locally."),
("BAV99","SOT-23"):("2 Discretes","Dual series switching diode, SOT-23","Nexperia BAV99,215 (marking A7)",0.01,"LCSC (design log)",G,""),
("S3M","SMB"):("2 Discretes","Rectifier 1000 V 3 A, SMB","TWGMC S3M (SMB body)",0.05,"estimate (handoff §3)",Q,"Footprint is SMB. Most local S3M stock is SMC (DO-214AB), which will not fit. Ask for SMB / DO-214AA."),
("SS3200","SMA (DO-214AC)"):("2 Discretes","Schottky 200 V 3 A, SMA","MDD SS3200",None,"",Q,"200 V rating is required. SS34 / SS310 are NOT OK."),
("LED","0603"):("2 Discretes","LED 0603 (status)","LCSC C2286 on all three",None,"",G,"D20 is labelled GRN, D21 BLU, D13 NET, but all carry the same LCSC number. Decide colours before buying."),
("SMDJ100A","SMC (DO-214AB)"):("3 Protection","TVS 3 kW, VRWM 100 V, SMC","Littelfuse SMDJ100A",0.32,J+"@1k (design log)",Q,"Must be the 3 kW SMDJ series in SMC. SMBJ100A (600 W) is NOT OK."),
("SMF5.0A","SOD-123FL"):("3 Protection","TVS 5 V unidirectional, SOD-123FL","MDD SMF5.0A",None,"",G,""),
("PESD1CAN","SOT-23"):("3 Protection","CAN bus dual TVS 24 V, SOT-23","Nexperia PESD1CAN,215",0.056,"LCSC @100 (design log)",Q,"Equivalent: any dual-line 24 V CAN TVS in SOT-23 with the same pinout."),
("SMF05C","SOT-363"):("3 Protection","5-line ESD array (SIM), SOT-363","onsemi SMF05CT1G",None,"",Q,""),
("USBLC6-2SC6","SOT-23-6"):("3 Protection","USB ESD array, SOT-23-6","ST USBLC6-2SC6",None,"",Q,""),
("1A 250V","FUSE-SMD"):("3 Protection","Fuse 1 A, 250 V AC/DC, 50 A interrupt, SMD 10x3 mm","Littelfuse 0443001.DR",None,"",X,"Voltage rating must be ≥125 V DC (input reaches 100 V). Common 32/63 V SMD fuses are NOT OK."),
("150uH 2.7A","IND-SMD"):("4 Inductors & ferrites","Power inductor 150 µH, Isat ≥2.7 A, shielded, 12x12 mm","SMDRI127-151MT",None,"",Q,"Must be shielded, 12.3x12.3 mm footprint, saturation current ≥2.7 A."),
("2.2uH","L1008"):("4 Inductors & ferrites","Power inductor 2.2 µH, 2520 (1008)","Murata DFE252012P-2R2M",None,"",Q,"Rated ≥2 A for the charger."),
("ACT45B-510-2P","IND-SMD"):("4 Inductors & ferrites","CAN common-mode choke 51 µH","TDK ACT45B-510-2P-TL003",0.28,J+"@1k (design log)",Q,"Alternate in repo: MetalLions ACT45B-510-2P-TF."),
("600R@100MHz","0805"):("4 Inductors & ferrites","Ferrite bead 600 Ω @100 MHz, 0805","LCSC C1017",None,"",G,""),
("68nH","0402"):("4 Inductors & ferrites","RF inductor 68 nH, WIREWOUND, 0402","Murata LQW15AN68NG80D",None,"",X,"Must be wirewound (SRF 2.5 GHz). Multilayer 0402 68 nH does NOT work at GPS frequency."),
("8MHz","SMD 3225 4-pin"):("5 Crystals","Crystal 8 MHz, 3225 4-pin","LCSC C115962",None,"",Q,"Load capacitance ~10-12 pF to suit the 18 pF caps."),
("32.768kHz","SMD 3215 2-pin"):("5 Crystals","Crystal 32.768 kHz, 3215","LCSC C32346",None,"",Q,"Load capacitance ~6-7 pF to suit the 6.8 pF caps."),
("WAFER-MX3.0-12PZZ","XUNPU"):("6 Connectors","Micro-Fit 3.0 style 2x6, 3.0 mm, vertical TH header","XUNPU WAFER-MX3.0-12PZZ",0.21,J+"@500 (design log)",Q,"Molex 43045-1212 is the original. Mating housing + crimps for the harness are NOT included here."),
("B3B-XH-A","JST-XH 3-pin vertical TH"):("6 Connectors","JST-XH 3-pin vertical header (battery)","JST B3B-XH-A(LF)(SN)",None,"",G,"Generic XH 2.5 mm OK."),
("NANO-SIM","SIM-SMD"):("6 Connectors","Nano-SIM push-push holder, 7-pin","JXTCONN NANO SIM 7P 1.37H PUSH",0.181,"LCSC (design log)",X,"Footprint is drawn for this exact holder. Other holders have different pad layouts."),
("U.FL","CONN-SMD"):("6 Connectors","U.FL / IPEX-1 RF connector, SMD","XYECONN XY-IPEX1",None,"",G,"Any IPEX gen-1 / U.FL."),
}
# passives: (cat, spec, mpn, subst, notes)
P={
("2.2uF 100V","1210"):("7 Capacitors","2.2 µF 100 V X7R 1210","CCTC TCC1210X7R225K101MT",Q,"Must be 100 V and X7R. Lower voltage parts will fail."),
("47uF X7R","1210"):("7 Capacitors","47 µF 10 V X7R 1210","Murata GRM32ER71A476KE15L",Q,"X7R and ≥10 V. X5R loses too much capacitance at temperature."),
("10uF","0805"):("7 Capacitors","10 µF 25 V X7S/X7R 0805","Murata GRM21BC71E106KE11L",Q,"≥25 V, X7R/X7S."),
("4.7uF","0805"):("7 Capacitors","4.7 µF ≥25 V X5R/X7R 0805","LCSC C23733",G,""),
("1uF","0603"):("7 Capacitors","1 µF ≥25 V X7R 0603","LCSC C15849",G,"C75 is labelled 25 V. Buy all at ≥25 V."),
("100nF","0603"):("7 Capacitors","100 nF ≥25 V X7R 0603","LCSC C14663",G,"C76 is labelled 25 V. Buy all at ≥25 V."),
("100nF","0603","VIN"):("7 Capacitors","100 nF ≥100 V X7R (on 10.5-100 V input)","schematic: C14663 (general 0603 part)",X,"CHECK: C72 sits on the input rail that reaches 100 V. Buy a ≥100 V rated part, and fix the schematic part number."),
("100nF","0402"):("7 Capacitors","100 nF X7R 0402","schematic says C14663, which is 0603",G,"MISMATCH: footprint is 0402 but the LCSC number is the 0603 part. Buy 0402. Repo suggests YAGEO C60474."),
("47nF","0603"):("7 Capacitors","47 nF X7R 0603","TBD (F-5)",G,"Value provisional (design log F-5). Confirm before buying."),
("10nF","0402"):("7 Capacitors","10 nF X7R 0402","TBD (F-22)",G,"Part number not yet chosen (F-22)."),
("4.7nF","0603"):("7 Capacitors","4.7 nF 50 V X7R 0603","Samsung CL10B472KB8NNNC",G,""),
("18pF","0603"):("7 Capacitors","18 pF C0G/NP0 0603","LCSC C1653",G,"C0G/NP0 only."),
("6.8pF","0603"):("7 Capacitors","6.8 pF C0G/NP0 0603","LCSC C1555",G,"C0G/NP0 only."),
("100pF C0G","0402"):("7 Capacitors","100 pF C0G 50 V 0402 (RF series block)","FH 0402CG101J500NT",G,"Always fitted: removing it opens the GNSS antenna path."),
("1R 2512 anti-surge","2512"):("8 Resistors","1 Ω 2512 ANTI-SURGE / pulse rated","FOJAN FRS2512F1R00TS",X,"Must be an anti-surge (pulse withstanding) resistor. A plain 2512 can fuse on input surges."),
("12k","1206"):("8 Resistors","12 kΩ 1% 1206 250 mW","UNI-ROYAL 1206W4F1202T5E",Q,"1206 size is needed for voltage/power (up to 100 V input). Do not use 0805."),
("60.4R","0805"):("8 Resistors","60.4 Ω 1% 0805","YAGEO AC0805FR-0760R4L",Q,"Exact 60.4 Ω for split CAN termination. 62 Ω is acceptable if 60.4 is not stocked."),
("68R","1210"):("8 Resistors","68 Ω 1210 (GNSS feed current limit)","TBD (F-22)",Q,"1210 size is set by the fault calculation (design log F-22). Part number not yet chosen."),
("0R","0402"):("8 Resistors","0 Ω jumper 0402","schematic says C17477, which is 0805",G,"MISMATCH: footprint is 0402 but the LCSC number is the 0805 part. Buy 0402."),
("33R","0805"):("8 Resistors","33 Ω 1% 0805","schematic says C17408, which is 100 Ω",G,"MISMATCH: value is 33 Ω but the LCSC number is 100 Ω (known F-5 placeholder). Buy 33 Ω."),
("47k","0805"):("8 Resistors","47 kΩ 1% 0805","UNI-ROYAL 0805W8F4702T5E (C17713)",G,"R56 and R58 carry C17414 (10 kΩ) by mistake. Buy 47 kΩ for them too."),
}
TBDR={"4.3k","1.5k","976R","536R","5.23k","30.1k"}

lines=[]
for k,ps in groups.items():
    refs=refsort([p["ref"] for p in ps]); qty=len(ps)
    lc=sorted({p["lcsc"] for p in ps})
    lcs=", ".join(lc)
    base=k[:2] if len(k)==2 else k
    meta=None
    for mk,mv in M.items():
        if k[0]==mk[0] and (k[1].startswith(mk[1]) or mk[1] in k[1]): meta=mv; break
    if meta:
        cat,spec,mpn,price,pnote,sub,note=meta
    elif k in P:
        cat,spec,mpn,sub,note=P[k]; price=None; pnote=""
    elif k[1] in("0805","0603","0402") and re.match(r'^[\d.]+[RkM]?$|^\d+(\.\d+)?[kM]$',k[0]):
        v=k[0]; ohm=v.replace("R"," Ω").replace("k"," kΩ").replace("M"," MΩ")
        if not ohm.endswith("Ω"): ohm+=" Ω"
        cat="8 Resistors"; spec=f"{ohm} 1% {k[1]}"
        mpn=lcs if not lcs.startswith("TBD") else "TBD (F-5)"
        sub=G; price=None; pnote=""
        note="Value provisional (design log F-5). Confirm before buying." if v in TBDR else ""
        if v in("976R","536R","5.23k","30.1k"): note+=" E96 value: 1% tolerance needed." 
    else:
        raise SystemExit(f"no meta for {k}")
    if lcs.startswith("TBD"): lcs="not chosen yet"
    if k==("100nF","0402"): lcs="C14663 (wrong size)"
    if k==("100nF","0603","VIN"): lcs="C14663 (rating too low)"
    if k==("0R","0402"): lcs="C17477 (wrong size)"
    if k==("33R","0805"): lcs="C17408 (wrong value)"
    if k==("47k","0805"): lcs="C17713 (R56/R58 show C17414)"
    lines.append(dict(cat=cat,part=k[0] if k[0]!="LED" else "LED",pkg=k[1],spec=spec,mpn=mpn,lcsc=lcs,refs=", ".join(refs),qty=qty,price=price,pnote=pnote,sub=sub,note=note))

# off-board items
lines+= [
 dict(cat="9 Off-board items",part="LTE antenna",pkg="FPC + 120 mm IPEX cable",spec="LTE FPC antenna 700-2700 MHz, IPEX-1, 120 mm RG1.13",mpn="Bat Wireless BW4GFNX39-15B1",lcsc="C496569",refs="ANT (LTE)",qty=1,price=0.383,pnote="LCSC @250 (installation sheet)",sub=Q,note="Cable length and IPEX-1 plug matter for the lid mounting."),
 dict(cat="9 Off-board items",part="GNSS antenna",pkg="25x25 mm patch + 120 mm IPEX cable",spec="ACTIVE GNSS patch, 1.8-3.6 V LNA, IPEX-1, 120 mm",mpn="Bat Wireless BWGNSCNX25-25B1Y4L120",lcsc="C784386",refs="ANT (GNSS)",qty=1,price=1.53,pnote="LCSC @250 (installation sheet)",sub=Q,note="Must be an ACTIVE antenna that runs on 3.3 V. Passive patch needs R90/L4 changes."),
 dict(cat="9 Off-board items",part="Battery",pkg="103450 1S pack + JST-XH 3-pin lead",spec="1S Li-ion 103450 ~1800 mAh with 10k NTC and JST-XH 3-pin lead",mpn="Indian sourcing (handoff §3)",lcsc="-",refs="BT1",qty=1,price=1.70,pnote="estimate (handoff §3)",sub=Q,note="Needs a built-in NTC (TS pin, JEITA) and protection PCB. Confirm NTC value against R88/R89."),
]
for l in dnp: pass
order={c:i for i,c in enumerate(sorted({l["cat"] for l in lines}))}
def vkey(l):
    m=re.match(r'([\d.]+)\s*([pnuµRkM]?)',l["part"])
    mul={"p":1e-12,"n":1e-9,"u":1e-6,"R":1,"k":1e3,"M":1e6,"":1}
    return float(m.group(1))*mul.get(m.group(2),1) if m else 0
lines.sort(key=lambda l:(order[l["cat"]],vkey(l) if l["cat"][0] in "78" else 0,l["refs"]))

# ---------- workbook ----------
wb=Workbook(); ws=wb.active; ws.title="Local Price Compare"
F="Arial"
f=lambda **kw: Font(name=F,**kw)
YEL=PatternFill("solid",fgColor="FFF2CC"); HDR=PatternFill("solid",fgColor="1F3864"); CAT=PatternFill("solid",fgColor="D9E1F2")
RED=PatternFill("solid",fgColor="F8CBAD"); GRY=PatternFill("solid",fgColor="EDEDED")
thin=Side(style="thin",color="BFBFBF"); BOX=Border(left=thin,right=thin,top=thin,bottom=thin)
wrap=Alignment(wrap_text=True,vertical="top")

ws["A1"]="MEWP Telematics Tracker — BOM for local purchase price comparison"; ws["A1"].font=f(bold=True,size=14)
ws["A2"]="Source: schematic sheets (power, mcu, io, modem_rf, storage) as committed. Test points, solder jumpers and DNP parts are not purchased (see other tabs)."; ws["A2"].font=f(italic=True,size=9)
inputs=[("Boards to build",10,"Number of boards you are buying parts for."),
        ("USD → INR rate",96,"~₹95.9 interbank on 1-Oct-2026. Edit to today's rate. Used only to convert the JLC/LCSC reference price."),
        ("Default spares per line (pcs)",0,"Extra pieces added to every line. Small passives are often sold in strips of 10-100 anyway.")]
for i,(lab,val,cm) in enumerate(inputs):
    r=3+i; ws.cell(r,1,lab).font=f(bold=True); c=ws.cell(r,3,val); c.font=f(color="0000FF",bold=True); c.fill=YEL; c.border=BOX
    ws.cell(r,4,cm).font=f(size=9,italic=True)
ws["C4"].number_format='0.00'
ws["H3"]="How to use"; ws["H3"].font=f(bold=True)
legend=["Yellow cells are inputs. Type each shop's price per piece in ₹ under Shop 1/2/3 (incl. GST), e.g. 0.45 or 1250.",
        "Rename the Shop 1/2/3 headers to the shop names. 'Best shop' picks the cheapest filled-in price.",
        "'Substitute?' says how strict to be. Red rows have a BOM problem: read the Notes and the 'BOM flags' tab before buying."]
for i,t in enumerate(legend): ws.cell(4+i,8,t).font=f(size=9)

H=["#","Part / value","Package","Spec to ask for","Manufacturer part (from repo)","LCSC #","Ref designators","Qty / board",
   "Spares","Buy qty","JLC ref $/pc","JLC ref ₹/pc","Shop 1","Shop 2","Shop 3","Best ₹/pc","Best shop","Line total ₹","Local vs JLC","Substitute?","Notes"]
HR=8
for j,h in enumerate(H,1):
    c=ws.cell(HR,j,h); c.font=f(bold=True,color="FFFFFF"); c.fill=HDR; c.alignment=Alignment(wrap_text=True,vertical="center",horizontal="center"); c.border=BOX
widths=[4,16,14,34,28,16,26,7,7,7,9,9,10,10,10,9,12,11,9,16,52]
for j,w in enumerate(widths,1): ws.column_dimensions[get_column_letter(j)].width=w
for j in (13,14,15): ws.cell(HR,j).fill=PatternFill("solid",fgColor="7F6000")

r=HR+1; n=0; cur=None; first=r
for l in lines:
    if l["cat"]!=cur:
        cur=l["cat"]; ws.cell(r,1,cur[2:]).font=f(bold=True)
        for j in range(1,len(H)+1): ws.cell(r,j).fill=CAT
        r+=1
    n+=1
    vals=[n,l["part"],l["pkg"],l["spec"],l["mpn"],l["lcsc"],l["refs"],l["qty"]]
    for j,v in enumerate(vals,1): ws.cell(r,j,v)
    ws.cell(r,9,"=$C$5")
    ws.cell(r,10,f"=H{r}*$C$3+I{r}")
    if l["price"] is not None:
        c=ws.cell(r,11,l["price"]); c.font=f(color="0000FF"); c.comment=Comment(f"Source: {l['pnote']}. Indicative only, re-check on order day.","BOM")
    ws.cell(r,12,f'=IF(K{r}="","",K{r}*$C$4)')
    for j in (13,14,15): ws.cell(r,j).fill=YEL; ws.cell(r,j).font=f(color="0000FF")
    ws.cell(r,16,f'=IF(COUNT(M{r}:O{r})=0,"",MIN(M{r}:O{r}))')
    ws.cell(r,17,f'=IF(P{r}="","",INDEX($M${HR}:$O${HR},MATCH(P{r},M{r}:O{r},0)))')
    ws.cell(r,18,f'=IF(P{r}="","",P{r}*J{r})')
    ws.cell(r,19,f'=IF(OR(P{r}="",L{r}=""),"",P{r}/L{r}-1)')
    ws.cell(r,20,l["sub"]); ws.cell(r,21,l["note"])
    for j in range(1,len(H)+1):
        c=ws.cell(r,j); c.border=BOX; c.alignment=wrap
        if c.font.color is None or c.font.name!=F: c.font=f(color=c.font.color.rgb if c.font.color and c.font.color.type=="rgb" else None)
    if any(w in l["note"] for w in ("MISMATCH","CHECK:","by mistake","Decide colours")):
        for j in (2,21): ws.cell(r,j).fill=RED
    if l["sub"]==X: ws.cell(r,20).font=f(bold=True,color="C00000")
    for j,fmt in ((11,'$0.000'),(12,'₹#,##0.00'),(13,'₹#,##0.00'),(14,'₹#,##0.00'),(15,'₹#,##0.00'),(16,'₹#,##0.00'),(18,'₹#,##0.00'),(19,'+0%;-0%;0%')):
        ws.cell(r,j).number_format=fmt
    r+=1
last=r-1
r+=1
ws.cell(r,1,"TOTALS").font=f(bold=True)
ws.cell(r,7,"Lines priced locally:").font=f(bold=True)
ws.cell(r,8,f'=COUNT(P{first}:P{last})&" of "&COUNT(A{first}:A{last})').font=f(bold=True)
ws.cell(r,10,"Total ₹").font=f(bold=True)
ws.cell(r,18,f"=SUM(R{first}:R{last})"); ws.cell(r,18).number_format='₹#,##0.00'; ws.cell(r,18).font=f(bold=True)
ws.cell(r+1,10,"Per board ₹").font=f(bold=True)
ws.cell(r+1,18,f"=IF($C$3=0,\"\",R{r}/$C$3)"); ws.cell(r+1,18).number_format='₹#,##0.00'; ws.cell(r+1,18).font=f(bold=True)
ws.cell(r+2,10,"Parts per board (incl. antennas, battery)").font=f(bold=True); ws.cell(r+2,18,f"=SUM(H{first}:H{last})").font=f(bold=True)
ws.cell(r+3,1,"Price columns: 'JLC ref' is indicative USD from the repo docs (Aug-2026, mostly 250-1000 pc breaks). Blank means the repo has no recorded price. Local vs JLC = best local ÷ JLC ref − 1.").font=f(size=9,italic=True)
dv=DataValidation(type="decimal",operator="greaterThanOrEqual",formula1="0",allow_blank=True); ws.add_data_validation(dv); dv.add(f"M{first}:O{last}")
ws.freeze_panes=ws.cell(HR+1,3)
ws.auto_filter.ref=f"A{HR}:{get_column_letter(len(H))}{last}"
ws.row_dimensions[HR].height=32
for row in ws.iter_rows(min_row=1,max_row=7):
    for c in row:
        if c.font.name!=F: c.font=Font(name=F,bold=c.font.bold,italic=c.font.italic,size=c.font.sz,color=c.font.color)

# ---------- BOM flags ----------
fl=wb.create_sheet("BOM flags")
fl["A1"]="Fix or confirm these before buying"; fl["A1"].font=f(bold=True,size=13)
FH=["Severity","Refs","Problem","What to buy for now"]
for j,h in enumerate(FH,1):
    c=fl.cell(3,j,h); c.font=f(bold=True,color="FFFFFF"); c.fill=HDR
flags=[
("High","C72","100 nF on the 10.5-100 V input rail uses the same general-purpose 0603 part (C14663) as the logic decoupling caps. A 50 V-class cap on a 100 V rail can crack or short.","100 nF X7R rated ≥100 V. Then update the schematic part number."),
("High","R56, R58","Value says 47 kΩ but the LCSC field is C17414 (10 kΩ). An order placed by LCSC number gets the wrong resistor.","47 kΩ 0805. Fix the LCSC field in tools/sheets.py."),
("High","R66, R67, R68","Value says 33 Ω (USIM series) but the LCSC field is C17408 (100 Ω). Known F-5 placeholder.","33 Ω 0805."),
("Medium","C12, C63","LCSC C23733 is a 4.7 µF 10 V part in 0402, but the footprint is 0805 (found in price check).","4.7 µF ≥10 V 0805 X5R/X7R, e.g. LCSC C1779."),
("Medium","C1, C2","LCSC C1653 is 22 pF, but the value is 18 pF (8 MHz crystal load caps).","18 pF C0G 0603, e.g. LCSC C1647."),
("Medium","Y1","LCSC C115962 is an 8 MHz crystal in a 5.0x3.2 mm package with 20 pF load, but the footprint is 3.2x2.5 mm.","8 MHz 3225 4-pin crystal; recheck load caps against its CL."),
("Medium","R71, R72","Footprint is 0402 but the LCSC field is C17477 (0805 0 Ω).","0 Ω 0402."),
("Medium","C83","Footprint is 0402 but the LCSC field is C14663 (0603 100 nF).","100 nF X7R 0402."),
("Medium","D13, D20, D21","Labelled NET, GRN and BLU, but all three use LCSC C2286. Colours are undecided.","Pick colours, then buy 0603 LEDs."),
("Medium","R83, R84, R85, R86, R88, R89, C64","Values are provisional (design log F-5) and have no part number. R83/R84 set the 5 V output, R85/R86 set charge/input current, R88/R89 set the battery NTC thresholds.","Confirm values first. They are cheap 1% 0805 parts, so buy a few nearby E96 values as backup."),
("Medium","R90, C85","GNSS feed parts have no part number yet (F-22).","68 Ω 1210 and 10 nF 0402."),
("Medium","U5 EG11752, L2 ACT45B","Stock is thin at LCSC and these are unlikely to be found in local markets.","Order from LCSC/JLC early."),
("Info","J1 harness","Only the PCB header is in the BOM. The harness side (housing, crimps, wire) is not.","Add Micro-Fit 3.0 2x6 receptacle + crimps if you build the cable."),
("Info","Enclosure","No enclosure, gasket, cable gland or antenna mounting hardware is in the BOM.","Source separately."),
]
for i,fr in enumerate(flags):
    for j,v in enumerate(fr,1):
        c=fl.cell(4+i,j,v); c.font=f(bold=(j==1),color=("C00000" if fr[0]=="High" and j==1 else None)); c.alignment=wrap; c.border=BOX
for j,w in enumerate([10,26,80,50],1): fl.column_dimensions[get_column_letter(j)].width=w

# ---------- Not purchased ----------
npur=wb.create_sheet("Not purchased")
npur["A1"]="On the schematic but not bought"; npur["A1"].font=f(bold=True,size=13)
for j,h in enumerate(["Ref","Value","Footprint","Why not bought"],1):
    c=npur.cell(3,j,h); c.font=f(bold=True,color="FFFFFF"); c.fill=HDR
rr=4
for p in sorted(dnp,key=lambda p:p["ref"])+sorted(pcb_only,key=lambda p:p["ref"]):
    why="DNP (do not populate)" if p["dnp"]=="yes" else ("Copper test pad on PCB" if p["ref"].startswith("TP") else "Solder jumper on PCB")
    if p["ref"]=="X2": why="DNP: footprint for future soldered eSIM (MFF2)"
    if p["ref"]=="R70": why="DNP: 0 Ω selector for the eSIM path"
    for j,v in enumerate([p["ref"],p["val"],p["fp"],why],1): npur.cell(rr,j,v).font=f()
    rr+=1
for j,w in enumerate([8,20,40,48],1): npur.column_dimensions[get_column_letter(j)].width=w

# ---------- every ref ----------
al=wb.create_sheet("All refs")
cols=["Sheet","Ref","Value","Footprint","LCSC","DNP"]
for j,h in enumerate(cols,1):
    c=al.cell(1,j,h); c.font=f(bold=True,color="FFFFFF"); c.fill=HDR
for i,p in enumerate(sorted(parts,key=lambda p:(re.match(r'[A-Z]+',p["ref"]).group(),int(re.search(r'\d+',p["ref"]).group()))),2):
    for j,v in enumerate([p["sheet"],p["ref"],p["val"],p["fp"],p["lcsc"],p["dnp"]],1): al.cell(i,j,v).font=f()
for j,w in enumerate([10,8,22,44,14,6],1): al.column_dimensions[get_column_letter(j)].width=w
al.freeze_panes="A2"; al.auto_filter.ref=f"A1:F{len(parts)+1}"


# ======================= Price estimate tab =======================
# Prices gathered 2026-10-02 from LCSC / JLCPCB price ladders (via web search;
# the shop sites were not directly reachable). status: live = LCSC/JLC ladder,
# alt = other distributor or a sibling LCSC number, est = no price found, estimate.
# (p1, p10, moq, status, source)
PR={
"C2916205":(13.65,11.54,1,"live","JLCPCB C2916205"),
"C55058656":(2.1686,1.938,1,"alt","LCSC C528437 (same MPN)"),
"C5380158":(1.4209,1.18,1,"live","LCSC C5380158"),
"C5382551":(0.4356,0.3513,1,"live","LCSC C5382551"),
"C53368402":(0.50,0.50,1,"est","NO PRICE FOUND. Placeholder $0.50"),
"C374063":(1.6253,1.4132,1,"live","LCSC C374063"),
"C2831359":(1.137,0.79,1,"live","LCSC 1+, JLC-China 10+"),
"C60708":(0.5835,0.5681,1,"live","LCSC C60708"),
"C82942":(0.0604,0.0604,10,"live","LCSC 10+"),
"C359074":(0.0739,0.0739,1,"alt","LCSC C142283 EL357N(D)"),
"C51886143":(0.61,0.406,1,"alt","DigiKey AM2390N"),
"C1977839":(1.02,0.638,1,"alt","DigiKey SMDJ100A"),
"C15127":(0.0589,0.0589,10,"live","LCSC 10+"),
"C20526":(0.0127,0.0127,50,"live","JLC/LCSC 50+"),
"C75549":(0.0577,0.0577,10,"live","LCSC 10+"),
"C2500":(0.0211,0.0211,20,"live","LCSC 20+"),
"C5204901":(0.0276,0.0276,20,"live","LCSC 20+"),
"C65001":(0.0469,0.0469,20,"alt","LCSC MDD SS3200 SMA 100+ tier"),
"C2286":(0.0073,0.0073,1,"live","JLC 1+"),
"C193402":(0.0276,0.0276,20,"live","LCSC 20+"),
"C15771":(0.0721,0.0721,10,"live","LCSC 10+"),
"C15879":(0.1747,0.1747,5,"live","LCSC 5+"),
"C7519":(0.164,0.164,5,"live","LCSC 5+"),
"C95352":(2.37,1.966,1,"alt","DigiKey 0443001.DR"),
"C21325":(0.2231,0.2212,5,"live","JLC 1+ / LCSC 5+"),
"C391305":(0.1631,0.1091,5,"live","JLC 1+ / LCSC 5+"),
"C76584":(0.3571,0.3571,2,"live","LCSC 2+"),
"C1017":(0.0127,0.0127,1,"live","JLC 1+"),
"C3221844":(0.10,0.10,1,"est","no LCSC price; Arrow ~$0.065"),
"C115962":(0.1959,0.1959,1,"live","JLC 1+"),
"C32346":(0.1734,0.1734,5,"live","LCSC 5+"),
"C7588012":(0.21,0.21,1,"est","design log $0.21@500"),
"C144394":(0.0546,0.0546,10,"live","LCSC 10+"),
"C53207808":(0.181,0.181,1,"est","design log $0.181"),
"C53133524":(0.05,0.05,1,"est","similar IPEX1 parts from $0.04"),
"C496569":(0.6006,0.4959,1,"live","JLC 1+"),
"C784386":(2.06,2.06,1,"est","unverified JLC ~$2.06"),
"C5449052":(0.08,0.08,10,"est","no price found"),
"C84494":(0.4878,0.3811,1,"live","LCSC C84494"),
"C109040":(0.1052,0.1052,5,"live","LCSC 5+"),
"C55348540":(0.15,0.15,5,"est","FRS2512 family $0.105-0.20"),
"C17912":(0.0046,0.0046,100,"est","unverified $0.0046"),
"C228935":(0.0109,0.0109,100,"est","unverified $0.0109"),
"C23733":(0.0348,0.0348,20,"alt","0805 4.7uF C1779 20+ (C23733 is 0402)"),
"C15849":(0.0275,0.0275,50,"live","LCSC 50+"),
"C14663":(0.0031,0.0031,100,"live","LCSC 100+"),
"C17414":(0.0025,0.0025,100,"live","LCSC 100+"),
"C1653":(0.0041,0.0041,100,"alt","LCSC C1653 100+ (it is 22pF)"),
"BATTERY":(339/96,339/96,1,"live","probots.co.in Rs 339 incl GST, no NTC/JST"),
}
R0805=(0.0025,0.0025,100,"est","as 0805 1% resistor C17414")
C0603=(0.0041,0.0041,100,"est","as small 0603/0402 MLCC")
SPECIAL={("100nF","0603","VIN"):(0.03,0.03,20,"est","100V X7R 0805/1206 estimate"),
         ("68R","1210"):(0.01,0.01,100,"est","1210 resistor estimate"),
         ("1R 2512 anti-surge","2512"):PR["C55348540"]}
def price_for(l):
    key=(l["part"],l["pkg"])
    if l["mpn"].startswith("100 nF") or l["spec"].startswith("100 nF ≥100 V"): return SPECIAL[("100nF","0603","VIN")]
    if key in SPECIAL: return SPECIAL[key]
    if l["refs"]=="BT1": return PR["BATTERY"]
    m=re.match(r'(C\d+)',l["lcsc"])
    if m and m.group(1) in PR and not l["lcsc"].endswith("(wrong value)") and not l["lcsc"].endswith("(wrong size)"):
        return PR[m.group(1)]
    if l["cat"].startswith("8"): return R0805
    if l["cat"].startswith("7"): return C0603
    raise SystemExit("no price for "+str(key))

pe=wb.create_sheet("Price estimate",1)
pe["A1"]="Estimated cost for 1 and 5 boards (LCSC / JLCPCB small-quantity prices)"; pe["A1"].font=f(bold=True,size=14)
pe["A2"]="Prices collected 2026-10-02. 'Parts value' = qty used × unit price. 'Order cost' includes LCSC minimum order quantities (MOQ), which is what you actually pay. Shipping, customs duty and GST are NOT included."; pe["A2"].font=f(italic=True,size=9)
pe["A3"]="USD → INR"; pe["A3"].font=f(bold=True); pe["C3"]=96; pe["C3"].font=f(color="0000FF",bold=True); pe["C3"].fill=YEL
pe["D3"]="Interbank rate ~₹95.9 on 1-Oct-2026 (apacnewsnetwork.com). Edit if needed."; pe["D3"].font=f(size=9,italic=True)
PH=["#","Part","Refs","Qty / board","Unit $ @1","Unit $ @10","MOQ","Price status","Source",
    "1 board: buy qty","1 board: unit $","1 board parts value ₹","1 board order cost ₹",
    "5 boards: need","5 boards: buy qty","5 boards: unit $","5 boards parts value ₹","5 boards order cost ₹"]
PHR=6
for j,h in enumerate(PH,1):
    c=pe.cell(PHR,j,h); c.font=f(bold=True,color="FFFFFF"); c.fill=HDR; c.alignment=Alignment(wrap_text=True,vertical="center",horizontal="center"); c.border=BOX
for j,w in enumerate([4,26,22,7,9,9,6,9,30,8,9,11,11,8,8,9,11,11],1): pe.column_dimensions[get_column_letter(j)].width=w
pe.row_dimensions[PHR].height=44
EST=PatternFill("solid",fgColor="FCE4D6")
rr=PHR+1; pstart=rr; prow={}
for i,l in enumerate(lines,1):
    p1,p10,moq,st,src=price_for(l)
    nm=l["part"] if l["cat"][0] not in "78" else f'{l["part"]} {l["pkg"]}'
    vals=[i,nm,l["refs"],l["qty"],round(p1,4),round(p10,4),moq,st,src]
    for j,v in enumerate(vals,1): pe.cell(rr,j,v)
    pe.cell(rr,10,f"=MAX(D{rr},G{rr})")
    pe.cell(rr,11,f"=E{rr}")
    pe.cell(rr,12,f"=D{rr}*K{rr}*$C$3")
    pe.cell(rr,13,f"=J{rr}*K{rr}*$C$3")
    pe.cell(rr,14,f"=D{rr}*5")
    pe.cell(rr,15,f"=MAX(N{rr},G{rr})")
    pe.cell(rr,16,f"=IF(O{rr}>=10,F{rr},E{rr})")
    pe.cell(rr,17,f"=N{rr}*P{rr}*$C$3")
    pe.cell(rr,18,f"=O{rr}*P{rr}*$C$3")
    for j in range(1,19):
        c=pe.cell(rr,j); c.border=BOX; c.font=f(color=("0000FF" if j in(5,6,7) else None)); c.alignment=Alignment(vertical="top",wrap_text=(j in(2,3,9)))
    for j,fmt in ((5,'$0.0000'),(6,'$0.0000'),(11,'$0.0000'),(16,'$0.0000'),(12,'₹#,##0.00'),(13,'₹#,##0.00'),(17,'₹#,##0.00'),(18,'₹#,##0.00')):
        pe.cell(rr,j).number_format=fmt
    if st!="live":
        pe.cell(rr,8).fill=EST
    prow[i]=rr; rr+=1
pend=rr-1
rr+=1
tot=rr
pe.cell(tot,2,"TOTAL").font=f(bold=True,size=12)
for col in "LMQR":
    c=pe[f"{col}{tot}"]; c.value=f"=SUM({col}{pstart}:{col}{pend})"; c.number_format='₹#,##0'; c.font=f(bold=True,size=12)
pe.cell(tot+1,2,"Per board").font=f(bold=True)
for col,div in (("L",1),("M",1),("Q",5),("R",5)):
    c=pe[f"{col}{tot+1}"]; c.value=f"={col}{tot}/{div}"; c.number_format='₹#,##0'; c.font=f(bold=True)
pe.cell(tot+2,2,"Lines that are estimates or from another source").font=f(size=9)
pe.cell(tot+2,4,f'=COUNTIF(H{pstart}:H{pend},"<>live")').font=f(size=9)
pe.cell(tot+3,2,"Value of estimated lines, 1 board ₹").font=f(size=9)
c=pe.cell(tot+3,12,f'=SUMIF(H{pstart}:H{pend},"est",L{pstart}:L{pend})'); c.number_format='₹#,##0'; c.font=f(size=9)
pe.cell(tot+4,1,"Price status: live = LCSC/JLCPCB ladder found · alt = other distributor (DigiKey) or a sibling LCSC number · est = no price found, estimate (orange). Not included: PCB, assembly, enclosure, harness, shipping, customs duty, GST on LCSC imports.").font=f(size=9,italic=True)

# Top expensive (per board), ranked in Python, values pulled by formula
top=sorted(lines,key=lambda l:-(price_for(l)[0]*l["qty"]))[:15]
t0=tot+6
pe.cell(t0,1,"Most expensive parts (per board, 1-board price)").font=f(bold=True,size=12)
for j,h in enumerate(["Rank","Part","Refs","Qty","Unit $","Cost / board ₹","% of board"],1):
    c=pe.cell(t0+1,j,h); c.font=f(bold=True,color="FFFFFF"); c.fill=HDR
for k,l in enumerate(top,1):
    src=prow[lines.index(l)+1]; r=t0+1+k
    pe.cell(r,1,k); pe.cell(r,2,f"=B{src}"); pe.cell(r,3,f"=C{src}"); pe.cell(r,4,f"=D{src}")
    pe.cell(r,5,f"=E{src}").number_format='$0.000'
    pe.cell(r,6,f"=L{src}").number_format='₹#,##0.00'
    pe.cell(r,7,f"=L{src}/$L${tot}").number_format='0.0%'
    for j in range(1,8): pe.cell(r,j).font=f(); pe.cell(r,j).border=BOX
pe.freeze_panes=pe.cell(PHR+1,3)

from openpyxl.workbook.properties import CalcProperties
wb.calculation=CalcProperties(fullCalcOnLoad=True)
out="out/bom-local-purchase.xlsx"
wb.save(out)
print("lines",n,"placed qty",sum(l["qty"] for l in lines if not l["cat"].startswith("9")),"dnp",len(dnp),"pcbonly",len(pcb_only))
