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
    "18": "VBAT_SENSE", "19": "ADC_SPARE", "21": "MODEM_PWR_EN",
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


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(PROJ, "nl.net")
    nets = load_nets(path)
    pin_of = {}
    for net, nodes in nets.items():
        for ref, pin in nodes:
            pin_of.setdefault((ref, pin), []).append(net)

    ok, bad = [], []
    for pin, want in sorted(SEC5.items(), key=lambda kv: int(kv[0])):
        got = pin_of.get(("U2", pin))
        if not got:
            bad.append(f"pin {pin:>2}: expected '{want}' but pin is UNCONNECTED")
        elif want not in got:
            bad.append(f"pin {pin:>2}: expected '{want}', netlist says {got}")
        else:
            ok.append((pin, want, got[0]))

    print(f"U2 AT32F403ACGT7 - section 5 pin map: {len(ok)}/{len(SEC5)} verified")
    for pin, want, got in ok:
        print(f"  [x] pin {pin:>2}  {want}")
    if bad:
        print("\nMISMATCHES:")
        for b in bad:
            print("  [!] " + b)
    stray = [k for k in pin_of if k[0] == "U2" and k[1] not in SEC5]
    if stray:
        print("\nU2 pins not covered by the checklist:", sorted(stray))
    print(f"\nnets in design: {len(nets)}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
