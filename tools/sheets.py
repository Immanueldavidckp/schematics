"""
sheets.py - builds the telematics tracker's hierarchical schematic sheets.

Usage:  python tools/sheets.py mcu [storage io modem_rf]
Writes the named sheets plus the root schematic into the project directory.

Every net name follows telematics-handoff.md section 5 exactly. Cross-sheet
nets use hierarchical labels; sheet-internal nets use plain labels.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schgen import Sheet, write_root  # noqa: E402

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# footprints
R0805 = "Resistor_SMD:R_0805_2012Metric"
R1206 = "Resistor_SMD:R_1206_3216Metric"
C0603 = "Capacitor_SMD:C_0603_1608Metric"
C0805 = "Capacitor_SMD:C_0805_2012Metric"
C1210 = "Capacitor_SMD:C_1210_3225Metric"
LED0603 = "LED_SMD:LED_0603_1608Metric"
FB0805 = "Inductor_SMD:L_0805_2012Metric"
SOT23 = "Package_TO_SOT_SMD:SOT-23"
TP = "TestPoint:TestPoint_Pad_D1.5mm"
SJ_OPEN = "Jumper:SolderJumper-2_P1.3mm_Open_Pad1.0x1.5mm"

# JLCPCB Basic-part C-numbers for generic passives (assembly BOM)
LCSC_R10K = "C17414"
LCSC_R4K7 = "C17673"
LCSC_R2K2 = "C4356"
LCSC_R1K = "C17513"
LCSC_R100 = "C17408"
LCSC_R0 = "C17477"
LCSC_C100N = "C14663"
LCSC_C1U = "C15849"
LCSC_C4U7 = "C23733"
LCSC_C18P = "C1653"
LCSC_C6P8 = "C1555"
LCSC_LED_G = "C2286"
LCSC_MMBT3904 = "C20526"
LCSC_FB = "C1017"

G = 1.27


def g(n):
    """grid helper: n * 1.27 mm"""
    return round(n * G, 4)


# ---------------------------------------------------------------------- MCU

def build_mcu():
    sh = Sheet("mcu", paper="A3")
    U2FP = "jlc:LQFP-48_L7.0-W7.0-P0.50-LS9.0-BL_1"
    u2 = sh.place("jlc:AT32F403ACGT7_C55058656", "U2", "AT32F403ACGT7",
                  (g(150), g(118)), U2FP, "C55058656")

    sh.text("MCU - AT32F403ACGT7 LQFP-48.  Pin map per telematics-handoff.md section 5.",
            (g(60), g(48)), 2.0)
    sh.text("JTAG must be disabled in firmware (SWD retained) before PA15/PB3/PB4 "
            "are used as GPIO.  CAN1 uses the PB8/PB9 remap.", (g(60), g(52)))

    # --- cross-sheet signals: pin -> (net, shape) -----------------------
    HIER = {
        "10": ("IGN_SENSE", "input"),
        "11": ("VIN_SENSE", "input"),
        "18": ("VBAT_SENSE", "input"),
        "19": ("ADC_SPARE", "passive"),
        "14": ("FLASH_CS", "output"),
        "15": ("SPI1_SCK", "output"),
        "16": ("SPI1_MISO", "input"),
        "17": ("SPI1_MOSI", "output"),
        "21": ("MODEM_PWR_EN", "output"),
        "25": ("DI1", "input"),
        "26": ("DI2", "input"),
        "27": ("DO1_GATE", "output"),
        "28": ("DO2_GATE", "output"),
        "29": ("MODEM_PWRKEY", "output"),
        "30": ("MODEM_TX", "output"),
        "31": ("MODEM_RX", "input"),
        "32": ("MODEM_RI", "input"),
        "33": ("MODEM_DTR", "output"),
        "38": ("CAN_STB", "output"),
        "39": ("MODEM_RESET", "output"),
        "40": ("MODEM_STATUS", "input"),
        "45": ("CAN1_RX", "input"),
        "46": ("CAN1_TX", "output"),
    }
    for pin, (net, shape) in HIER.items():
        sh.hier(u2, pin, net, shape, length=g(8))

    # --- local signals --------------------------------------------------
    LOCAL = {
        "1": "VBAT_MCU", "2": "SYS_LED",
        "3": "OSC32_IN", "4": "OSC32_OUT",
        "5": "OSC_IN", "6": "OSC_OUT",
        "7": "NRST", "9": "3V3A",
        "12": "DBG_TX", "13": "DBG_RX",
        "20": "BOOT1", "22": "NET_STATUS_LED",
        "24": "3V3", "36": "3V3", "48": "3V3",
        "34": "SWDIO", "37": "SWCLK",
        "41": "IMU_INT1", "42": "I2C1_SCL", "43": "I2C1_SDA",
        "44": "BOOT0",
    }
    for pin, net in LOCAL.items():
        sh.net(u2, pin, net, length=g(4))

    for pin in ("8", "23", "35", "47"):          # VSSA, VSS_1..3
        sh.gnd(u2, pin, length=g(3))

    # --- 8 MHz HSE crystal (Crystal_GND24: pins 1/3 = terminals, 2/4 = case)
    y1 = sh.place("Device:Crystal_GND24", "Y1", "8MHz",
                  (g(88), g(104)), "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
                  "C115962")
    sh.net(y1, "1", "OSC_IN", length=g(3))
    sh.net(y1, "3", "OSC_OUT", length=g(3))
    sh.gnd(y1, "2", length=g(3))                 # pin 4 shares pin 2's coordinate
    sh.series("Device:C", "C1", "18pF", (g(84), g(114)), "OSC_IN", None,
              C0603, LCSC_C18P, gnd_b=True)
    sh.series("Device:C", "C2", "18pF", (g(94), g(114)), "OSC_OUT", None,
              C0603, LCSC_C18P, gnd_b=True)

    # --- 32.768 kHz LSE crystal
    y2 = sh.place("Device:Crystal", "Y2", "32.768kHz",
                  (g(88), g(84)), "Crystal:Crystal_SMD_3215-2Pin_3.2x1.5mm",
                  "C32346")
    sh.net(y2, "1", "OSC32_IN", length=g(3))
    sh.net(y2, "2", "OSC32_OUT", length=g(3))
    sh.series("Device:C", "C3", "6.8pF", (g(84), g(92)), "OSC32_IN", None,
              C0603, LCSC_C6P8, gnd_b=True)
    sh.series("Device:C", "C4", "6.8pF", (g(94), g(92)), "OSC32_OUT", None,
              C0603, LCSC_C6P8, gnd_b=True)

    # --- reset
    sh.series("Device:C", "C5", "100nF", (g(88), g(126)), "NRST", None,
              C0603, LCSC_C100N, gnd_b=True)

    # --- BOOT0: 10k pulldown + solder jumper to 3V3 for bootloader entry
    sh.series("Device:R", "R1", "10k", (g(240), g(126)), "BOOT0", None,
              R0805, LCSC_R10K, gnd_b=True)
    sj = sh.place("Jumper:SolderJumper_2_Open", "JP1", "BOOT0_SEL",
                  (g(240), g(114)), SJ_OPEN)
    sh.net(sj, "1", "3V3", length=g(3))
    sh.net(sj, "2", "BOOT0", length=g(3))

    # --- BOOT1 (PB2) pulldown: required for deterministic boot mode
    sh.series("Device:R", "R2", "10k", (g(240), g(138)), "BOOT1", None,
              R0805, LCSC_R10K, gnd_b=True)

    # --- VBAT (RTC) fed from 3V3 through 0 ohm, per section 5
    sh.series("Device:R", "R3", "0R", (g(56), g(64)), "3V3", "VBAT_MCU",
              R0805, LCSC_R0)
    sh.series("Device:C", "C6", "100nF", (g(66), g(64)), "VBAT_MCU", None,
              C0603, LCSC_C100N, gnd_b=True)

    # --- VDDA filter: ferrite + 1uF + 100nF
    fb = sh.place("Device:FerriteBead", "FB1", "600R@100MHz",
                  (g(56), g(84)), FB0805, LCSC_FB)
    sh.net(fb, "1", "3V3", length=g(3))
    sh.net(fb, "2", "3V3A", length=g(3))
    sh.series("Device:C", "C7", "1uF", (g(66), g(84)), "3V3A", None,
              C0603, LCSC_C1U, gnd_b=True)
    sh.series("Device:C", "C8", "100nF", (g(76), g(84)), "3V3A", None,
              C0603, LCSC_C100N, gnd_b=True)

    # --- VDD decoupling: 100nF per VDD pin + bulk
    for i, x in enumerate((252, 260, 268)):
        sh.series("Device:C", f"C{9 + i}", "100nF", (g(x), g(64)), "3V3", None,
                  C0603, LCSC_C100N, gnd_b=True)
    bulk = sh.place("Device:C", "C12", "4.7uF", (g(276), g(64)), C0805, LCSC_C4U7)
    sh.hier(bulk, "1", "3V3", "input", length=g(5))
    sh.gnd(bulk, "2", length=g(3))

    # --- heartbeat LED on PC13 (sinks current: 3V3 -> R -> LED -> PC13)
    sh.series("Device:R", "R4", "1k", (g(252), g(150)), "3V3", "SYS_LED_A",
              R0805, LCSC_R1K)
    d1 = sh.place("Device:LED", "D1", "GRN", (g(252), g(158)), LED0603, LCSC_LED_G)
    sh.net(d1, "2", "SYS_LED_A", length=g(3))
    sh.net(d1, "1", "SYS_LED", length=g(3))

    # --- network-status LED on PB11 via NPN, per section 5
    sh.series("Device:R", "R5", "4.7k", (g(268), g(150)), "NET_STATUS_LED",
              "NSL_BASE", R0805, LCSC_R4K7)
    q1 = sh.place("Transistor_BJT:Q_NPN_BEC", "Q4", "MMBT3904",
                  (g(280), g(158)), SOT23, LCSC_MMBT3904)
    sh.net(q1, "1", "NSL_BASE", length=g(3))
    sh.gnd(q1, "2", length=g(3))
    sh.net(q1, "3", "NSL_K", length=g(3))
    d2 = sh.place("Device:LED", "D2", "BLU", (g(280), g(142)), LED0603, LCSC_LED_G)
    sh.net(d2, "1", "NSL_K", length=g(3))
    sh.net(d2, "2", "NSL_A", length=g(3))
    sh.series("Device:R", "R6", "1k", (g(280), g(130)), "3V3", "NSL_A",
              R0805, LCSC_R1K)

    # --- IMU U3 (QMI8658B).  Wiring per QST QMI8658B datasheet Rev D sec 1.4:
    #     CS high selects I2C; SDO/SA0 high -> slave address 0x6A;
    #     RESV (pin 10) must NOT be low; RESV-NC (pin 11) must float.
    u3 = sh.place("jlc:QMI8658B_C5380158", "U3", "QMI8658B",
                  (g(230), g(80)), "jlc:LGA-14_L3.0-W2.5-P0.50-TL", "C5380158")
    sh.net(u3, "13", "I2C1_SCL", length=g(4))
    sh.net(u3, "14", "I2C1_SDA", length=g(4))
    sh.net(u3, "4", "IMU_INT1", length=g(4))
    for p in ("1", "2", "3", "5", "8", "10", "12"):
        sh.net(u3, p, "3V3", length=g(4))
    for p in ("6", "7"):
        sh.gnd(u3, p, length=g(3))
    sh.nc(u3, "9")      # INT2 unused
    sh.nc(u3, "11")     # RESV-NC must float
    sh.series("Device:C", "C13", "100nF", (g(196), g(60)), "3V3", None,
              C0603, LCSC_C100N, gnd_b=True)
    sh.series("Device:C", "C14", "1uF", (g(204), g(60)), "3V3", None,
              C0603, LCSC_C1U, gnd_b=True)
    sh.text("U3 IMU: CS=high -> I2C mode; SA0=high -> addr 0x6A;",
            (g(178), g(46)))
    sh.text("RESV(10) tied high per datasheet (must NOT be GND); RESV-NC(11) floats.",
            (g(178), g(50)))

    # --- I2C pull-ups (2.2k per section 5; the IMU's internal 200k is too weak)
    sh.series("Device:R", "R7", "2.2k", (g(212), g(66)), "3V3", "I2C1_SCL",
              R0805, LCSC_R2K2)
    sh.series("Device:R", "R8", "2.2k", (g(220), g(66)), "3V3", "I2C1_SDA",
              R0805, LCSC_R2K2)

    # --- test points: SWD, both debug UART lines, reset, rails
    for i, (net, x) in enumerate((("SWDIO", 300), ("SWCLK", 308), ("NRST", 316),
                                  ("DBG_TX", 324), ("DBG_RX", 332),
                                  ("3V3", 340))):
        tp = sh.place("Connector:TestPoint", f"TP{i + 1}", net,
                      (g(x), g(96)), TP)
        sh.net(tp, "1", net, length=g(3))
    tpg = sh.place("Connector:TestPoint", "TP7", "GND", (g(348), g(96)), TP)
    sh.gnd(tpg, "1", length=g(3))
    sh.text("Test points: SWD + debug UART + reset + rails (production test jig).",
            (g(296), g(90)))

    # Declares the global GND net driven for ERC. Placed here once for the
    # whole project; the real ground return comes from power.kicad_sch.
    sh.gnd_driver((g(30), g(170)))
    sh.text("GND driver flag for ERC (one per project).", (g(24), g(166)))

    return sh


BUILDERS = {"mcu": build_mcu}

RAILS = ["VIN", "SYS", "5V0", "3V3", "VBAT_MODEM", "VDD_EXT_1V8"]
NOTES = [
    "TEMPORARY: the PWR_FLAG symbols below mark rails that will be driven by",
    "power.kicad_sch (not yet drawn - pending the buck selection decision).",
    "Remove them when the power sheet is added.",
]


def main(names):
    built = []
    for n in names:
        if n not in BUILDERS:
            raise SystemExit(f"unknown sheet '{n}'; known: {sorted(BUILDERS)}")
        sh = BUILDERS[n]()
        path = sh.write(PROJ)
        print(f"wrote {os.path.basename(path)}  "
              f"({len(sh.parts)} symbols, {len(sh.hier_pins)} sheet pins)")
        built.append(sh)
    write_root(PROJ, built, rails=RAILS, notes=NOTES)
    print("wrote root schematic with sheets:", ", ".join(s.name for s in built))
    for s in built:
        print(f"  {s.name}: sheet pins = {sorted(s.hier_pins)}")


if __name__ == "__main__":
    main(sys.argv[1:] or ["mcu"])
