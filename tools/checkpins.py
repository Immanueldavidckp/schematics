"""
checkpins.py - verify the exported netlist against the handoff section 5 pin map.

Usage: python tools/checkpins.py [netlist.net]
Exits non-zero if any expected pin/net pair is missing or any pin is unconnected.
"""
import os
import re
import sys

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# telematics-handoff.md section 5, verbatim: pin -> net
SEC5 = {
    "10": "IGN_SENSE", "11": "VIN_SENSE", "12": "DBG_TX", "13": "DBG_RX",
    "14": "FLASH_CS", "15": "SPI1_SCK", "16": "SPI1_MISO", "17": "SPI1_MOSI",
    "18": "VBAT_SENSE", "21": "MODEM_PWR_EN",
    "22": "NET_STATUS_LED", "25": "DI1", "26": "DI2", "27": "DO1_GATE",
    "28": "DO2_GATE", "29": "MODEM_PWRKEY", "30": "MODEM_TX", "31": "MODEM_RX",
    "32": "MODEM_RI", "33": "MODEM_DTR", "34": "SWDIO", "37": "SWCLK",
    "38": "CAN_STB", "39": "MODEM_RESET", "40": "MODEM_STATUS",
    "41": "IMU_INT1", "42": "I2C1_SCL", "43": "I2C1_SDA",
    "45": "CAN1_RX", "46": "CAN1_TX",
    "2": "SYS_LED", "3": "OSC32_IN", "4": "OSC32_OUT",
    "5": "OSC_IN", "6": "OSC_OUT", "7": "NRST",
    "44": "BOOT0", "1": "VBAT_MCU",
    "8": "GND", "9": "3V3A",
    # power/ground pins and PB2 (BOOT1) are not signal rows in section 5
    "20": "BOOT1", "23": "GND", "24": "3V3", "35": "GND", "36": "3V3",
    "47": "GND", "48": "3V3",
}


def _balanced(txt, start):
    """Return the balanced S-expression beginning at txt[start] == '('."""
    depth, i = 0, start
    while True:
        c = txt[i]
        if c == '"':
            i += 1
            while txt[i] != '"' or txt[i - 1] == '\\':
                i += 1
        elif c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                return txt[start:i + 1]
        i += 1


def load_nets(path):
    """Return {net_name: {(ref, pin), ...}} from a kicadsexpr netlist."""
    txt = open(path, encoding="utf-8").read()
    nets = {}
    for m in re.finditer(r'\(net\b', txt):
        block = _balanced(txt, m.start())
        nm = re.search(r'\(name "([^"]*)"\)', block)
        if not nm:
            continue
        nodes = set(re.findall(
            r'\(node\s*\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)', block))
        # net names carry the sheet path, e.g. "/mcu/SPI1_SCK"
        nets.setdefault(nm.group(1).split("/")[-1], set()).update(nodes)
    return nets


# handoff section 5 "Goes to" column: pin -> (ref, pin) that must share the net
FAR_END = {
    "14": ("U7", "1"), "15": ("U7", "6"), "16": ("U7", "2"), "17": ("U7", "5"),
    "25": ("OK1", "4"), "26": ("OK2", "4"),
    "27": ("R42", "1"), "28": ("R46", "1"),
    "38": ("U4", "8"), "45": ("U4", "4"), "46": ("U4", "1"),
    "41": ("U3", "4"), "42": ("U3", "13"), "43": ("U3", "14"),
    "10": ("R35", "2"), "11": ("R32", "2"), "18": ("R38", "2"),
    "21": ("R53", "1"), "29": ("R55", "1"), "30": ("U8", "13"),
    "31": ("U8", "12"), "32": ("U8", "11"), "33": ("U8", "10"),
    "39": ("R57", "1"), "40": ("Q11", "3"),
    "3": ("Y2", "1"), "4": ("Y2", "2"), "5": ("Y1", "1"), "6": ("Y1", "3"),
}
# nets whose far end lives on a sheet that is not drawn yet
PENDING = {
    "22": "on-sheet LED via Q4", "19": "spare divider, fitted DNP",
}


def check_do_default_off(nets):
    """F-10 requirement: prove each DO gate is pulled to GND with the MCU pin
    open. Structural conditions asserted on the netlist:
      1. FET gate net Qn_G has a resistor to GND (10k gate pulldown);
      2. MCU-side net DOn_GATE has a resistor to GND (base pulldown, holds
         QnA off when the pin floats);
      3. QnB's base node DOn_X has a resistor to 5V0 (so QnB defaults ON and
         actively clamps the gate low whenever 5V0 is present);
      4. QnB's collector actually sits on the gate-driver node.
    """
    def has_r_between(net_a, net_b):
        ra = {ref for ref, pin in nets.get(net_a, set()) if ref.startswith("R")}
        rb = {ref for ref, pin in nets.get(net_b, set()) if ref.startswith("R")}
        return sorted(ra & rb)

    ok = True
    for n in (1, 2):
        checks = [
            (f"Q{n}_G", "GND", "gate pulldown"),
            (f"DO{n}_GATE", "GND", "MCU-side base pulldown"),
            (f"DO{n}_X", "5V0", "QnB base pullup (defaults driver to clamp)"),
        ]
        for a, b, what in checks:
            r = has_r_between(a, b)
            if r:
                print(f"  [x] DO{n}: {what}: {r[0]} between {a} and {b}")
            else:
                print(f"  [!] DO{n} default-OFF FAILED: no resistor between {a} and {b} ({what})")
                ok = False
        qb = f"Q{4 + 2 * n}"
        if (qb, "3") in nets.get(f"DO{n}_DRV", set()):
            print(f"  [x] DO{n}: {qb} collector clamps DO{n}_DRV")
        else:
            print(f"  [!] DO{n} default-OFF FAILED: {qb} collector not on DO{n}_DRV")
            ok = False
    return ok


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(PROJ, "nl.net")
    nets = load_nets(path)
    pin_of = {}
    for net, nodes in nets.items():
        for ref, pin in nodes:
            pin_of.setdefault((ref, pin), []).append(net)

    rows, bad = [], []
    for pin, want in sorted(SEC5.items(), key=lambda kv: int(kv[0])):
        got = pin_of.get(("U2", pin))
        if not got:
            bad.append(f"pin {pin:>2}: expected '{want}' but pin is UNCONNECTED")
            continue
        if want not in got:
            bad.append(f"pin {pin:>2}: expected '{want}', netlist says {got}")
            continue
        members = sorted(nets[want] - {("U2", pin)})
        note = ""
        if pin in FAR_END:
            fe = FAR_END[pin]
            if fe in nets[want]:
                note = f"-> {fe[0]}.{fe[1]} OK"
            else:
                bad.append(f"pin {pin:>2} ({want}): far end {fe[0]}.{fe[1]} "
                           f"NOT on this net; net has {members}")
                continue
        elif pin in PENDING:
            note = f"(pending: {PENDING[pin]})"
        rows.append((pin, want, note, members))

    print(f"U2 AT32F403ACGT7 - handoff section 5, {len(rows)}/{len(SEC5)} rows verified\n")
    print(f"{'pin':>4}  {'net':<16} {'far end':<22} other nodes on net")
    print("-" * 100)
    for pin, want, note, members in rows:
        mem = ", ".join(f"{r}.{p}" for r, p in members[:6])
        if len(members) > 6:
            mem += f", +{len(members) - 6} more"
        print(f"{pin:>4}  {want:<16} {note:<22} {mem}")
    if bad:
        print("\nMISMATCHES:")
        for b in bad:
            print("  [!] " + b)
    stray = [k for k in pin_of if k[0] == "U2" and k[1] not in SEC5]
    if stray:
        print("\nU2 pins not covered by the checklist:", sorted(stray))
    print(f"\nnets in design: {len(nets)}")
    print("\nF-10 default-OFF structural check:")
    do_ok = check_do_default_off(nets)
    return 1 if (bad or not do_ok) else 0


if __name__ == "__main__":
    sys.exit(main())
