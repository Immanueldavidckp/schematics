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


# ------------------------------------------------------------------ STORAGE

def build_storage():
    sh = Sheet("storage", paper="A4")
    sh.text("SPI NOR flash - telemetry ring buffer (>=6 days at 150 B/10 s).",
            (g(20), g(24)), 2.0)
    sh.text("U7 = GD25Q64ESIGR (tape & reel, C2831359) per F-3; W25Q64JVSSIQ "
            "(C179171/C2904572) is a verified pin- and command-compatible alternate.",
            (g(20), g(28)))

    u7 = sh.place("jlc:GD25Q64ESIG", "U7", "GD25Q64ESIGR",
                  (g(90), g(80)), "jlc:SOP-8_L5.3-W5.3-P1.27-LS8.0-BL",
                  "C2831359",
                  fields={"Alternate": "W25Q64JVSSIQ C179171/C2904572"})
    # SPI1 to the MCU
    sh.hier(u7, "1", "FLASH_CS", "input", length=g(6))
    sh.hier(u7, "6", "SPI1_SCK", "input", length=g(6))
    sh.hier(u7, "5", "SPI1_MOSI", "input", length=g(6))
    sh.hier(u7, "2", "SPI1_MISO", "output", length=g(6))
    # WP# and HOLD# tied high: write protect and hold both disabled
    sh.net(u7, "3", "3V3", length=g(6))
    sh.net(u7, "7", "3V3", length=g(6))
    sh.net(u7, "8", "3V3", length=g(6))
    sh.gnd(u7, "4", length=g(3))

    sh.series("Device:C", "C20", "100nF", (g(46), g(60)), "3V3", None,
              C0603, LCSC_C100N, gnd_b=True)
    bulk = sh.place("Device:C", "C21", "1uF", (g(56), g(60)), C0603, LCSC_C1U)
    sh.hier(bulk, "1", "3V3", "input", length=g(5))
    sh.gnd(bulk, "2", length=g(3))
    sh.text("WP#(3) and HOLD#(7) tied to 3V3 per handoff section 5.",
            (g(20), g(112)))
    return sh


# ----------------------------------------------------------------------- IO

# F-8 in-stock selections (2026-09-02 sweep; see design-log for rationale)
LCSC_NMOS_150V = "C51886143"   # AM2390N-TP 150V 4A SOT-23-3L (see F-10 gate drive)
LCSC_PESD1CAN = "C15771"       # Nexperia PESD1CAN,215
LCSC_ACT45B = "C76584"         # TDK ACT45B-510-2P-TL003 (alt clone C48928226)
LCSC_J1_MX3 = "C7588012"       # XUNPU WAFER-MX3.0-12PZZ (Micro-Fit 3.0 ref series)
LCSC_BAV99 = "C2500"           # Nexperia BAV99,215
LCSC_SS3200 = "C65001"         # MDD SS3200 200V 3A SMA (F-11 approved swap from SS310)
LCSC_R60R4 = "C228935"         # YAGEO AC0805FR-0760R4L 60.4R 1%
LCSC_R12K_1206 = "C17912"      # UNI-ROYAL 1206W4F1202T5E 12k 1% 250mW
LCSC_R47K = "C17713"           # UNI-ROYAL 0805W8F4702T5E 47k 1%
LCSC_R100K = "C17407"          # UNI-ROYAL 0805W8F1003T5E 100k 1%
LCSC_R9K1 = "C17855"           # UNI-ROYAL 0805W8F9101T5E 9.1k 1%
LCSC_R1M = "C17514"            # UNI-ROYAL 0805W8F1004T5E 1M 1%
LCSC_C4N7 = "C1621"            # Samsung CL10B472KB8NNNC 4.7nF 50V X7R 0603
LCSC_MMBT3904V = "C20526"      # MMBT3904 NPN 40V SOT-23 (API-verified, 21,350 stock)


def build_io():
    sh = Sheet("io", paper="A3")
    sh.text("MACHINE I/O - CAN, isolated digital inputs, low-side outputs, "
            "supply sensing.  HV zone: J1 / dividers / DI series R / DO drains.",
            (g(20), g(16)), 2.0)
    sh.text("Valid DI input range 9-100 V.  DO loads: relay coils / buzzers "
            "<= 0.5 A at 12/24 V.", (g(20), g(20)))

    # ---------------- J1 machine harness, 12-pin Micro-Fit 3.0 class --------
    j1 = sh.place("Connector_Generic:Conn_01x12", "J1", "WAFER-MX3.0-12PZZ",
                  (g(46), g(80)),
                  "Connector_Molex:Molex_Micro-Fit_3.0_43045-1212_2x06_P3.00mm_Vertical",
                  LCSC_J1_MX3)
    J1MAP = {
        "1": ("VIN", "hier", "input"), "2": ("GND", "gnd", None),
        "3": ("IGN", "net", None), "4": ("CANH", "net", None),
        "5": ("CANL", "net", None), "6": ("GND", "gnd", None),
        "7": ("DI1_IN", "net", None), "8": ("DI2_IN", "net", None),
        "9": ("DO1_OUT", "net", None), "10": ("DO2_OUT", "net", None),
        "11": ("J1_SPARE1", "net", None), "12": ("J1_SPARE2", "net", None),
    }
    for pin, (net, kind, shape) in J1MAP.items():
        if kind == "gnd":
            sh.gnd(j1, pin, length=g(3))
        elif kind == "hier":
            sh.hier(j1, pin, net, shape, length=g(6))
        else:
            sh.net(j1, pin, net, length=g(6))
    sh.text("J1 pinout: 1 VIN, 2 GND, 3 IGN, 4 CANH, 5 CANL, 6 GND, 7 DI1, "
            "8 DI2, 9 DO1, 10 DO2, 11/12 spare.", (g(20), g(104)))
    for i, net in (("8", "J1_SPARE1"), ("9", "J1_SPARE2")):
        tp = sh.place("Connector:TestPoint", f"TP{i}", net,
                      (g(20 + (0 if net.endswith('1') else 8)), g(96)), TP)
        sh.net(tp, "1", net, length=g(3))

    # ---------------- CAN: choke + TVS at connector, transceiver, split term
    # TDK ACT45B circuit diagram: winding A = pins 1->4, winding B = pins 2->3
    ch = sh.place("jlc:ACT45B-510-2P-TL003", "L2", "ACT45B-510-2P",
                  (g(84), g(52)), "jlc:IND-SMD_4P-L4.5-W3.2-TL", LCSC_ACT45B,
                  fields={"Alternate": "MetalLions ACT45B-510-2P-TF C48928226"})
    sh.net(ch, "1", "CANH", length=g(4))
    sh.net(ch, "4", "CANH_T", length=g(4))
    sh.net(ch, "2", "CANL", length=g(4))
    sh.net(ch, "3", "CANL_T", length=g(4))
    d3 = sh.place("jlc:PESD1CAN,215", "D3", "PESD1CAN",
                  (g(64), g(34)),
                  "jlc:SOT-23_L2.9-W1.3-P1.90-LS2.4-BR", LCSC_PESD1CAN)
    sh.net(d3, "1", "CANH", length=g(4))
    sh.net(d3, "2", "CANL", length=g(4))
    sh.gnd(d3, "3", length=g(3))
    sh.text("D3 Nexperia PESD1CAN: dual-line bidirectional CAN TVS at the "
            "connector (24 V standoff).", (g(56), g(28)))

    u4 = sh.place("jlc:SIT1051AT_3", "U4", "SIT1051AT/3",
                  (g(140), g(48)), "jlc:SOP-8_L4.9-W3.9-P1.27-LS6.0-BL",
                  "C5382551")
    sh.hier(u4, "1", "CAN1_TX", "input", length=g(6))
    sh.hier(u4, "4", "CAN1_RX", "output", length=g(6))
    sh.hier(u4, "3", "5V0", "input", length=g(6))
    sh.hier(u4, "5", "3V3", "input", length=g(6))
    sh.hier(u4, "8", "CAN_STB", "input", length=g(6))
    sh.gnd(u4, "2", length=g(3))
    sh.net(u4, "7", "CANH_T", length=g(6))
    sh.net(u4, "6", "CANL_T", length=g(6))
    sh.series("Device:C", "C23", "100nF", (g(118), g(28)), "5V0", None,
              C0603, LCSC_C100N, gnd_b=True)
    sh.series("Device:C", "C24", "100nF", (g(128), g(28)), "3V3", None,
              C0603, LCSC_C100N, gnd_b=True)

    # split termination, jumper-selectable, DEFAULT OPEN (machine bus is
    # already terminated at both physical ends)
    sh.series("Device:R", "R11", "60.4R", (g(108), g(64)), "CANH_T", "CAN_MID",
              R0805, LCSC_R60R4)
    sh.series("Device:R", "R12", "60.4R", (g(118), g(64)), "CANL_T", "CAN_MID",
              R0805, LCSC_R60R4)
    jp2 = sh.place("Jumper:SolderJumper_2_Open", "JP2", "CAN_TERM",
                   (g(130), g(72)), SJ_OPEN)
    sh.net(jp2, "1", "CAN_MID", length=g(4))
    sh.net(jp2, "2", "CAN_SPLIT", length=g(4))
    sh.series("Device:C", "C22", "4.7nF", (g(140), g(78)), "CAN_SPLIT", None,
              C0603, LCSC_C4N7, gnd_b=True)
    sh.text("Split termination 2x60R + 4.7nF behind JP2, DEFAULT OPEN.",
            (g(104), g(58)))

    # ---------------- isolated digital inputs DI1/DI2 -----------------------
    for n, ybase in ((1, 130), (2, 168)):
        # 3 x 12k in series (36k total) per F-7: two 1206 parts ran ~1.6x their
        # 105 C derated rating at 100 V input; three share the dissipation.
        base = 14 + (n - 1) * 3
        chain = [f"DI{n}_IN", f"DI{n}_M1", f"DI{n}_M2", f"DI{n}_LED"]
        for k in range(3):
            sh.series("Device:R", f"R{base + k}", "12k",
                      (g(58 + k * 12), g(ybase)), chain[k], chain[k + 1],
                      R1206, LCSC_R12K_1206)
        ok = sh.place("jlc:EL357N", f"OK{n}", "EL357N(D)",
                      (g(112), g(ybase + 8)),
                      "jlc:OPTO-SMD-4_L4.4-W4.1-P2.54-LS7.0-BL", "C359074")
        sh.net(ok, "1", f"DI{n}_LED", length=g(5))
        sh.gnd(ok, "2", length=g(3))
        sh.gnd(ok, "3", length=g(3))
        sh.hier(ok, "4", f"DI{n}", "output", length=g(6))
        # BAV99 as the antiparallel (reverse) diode across the opto LED.
        # Series pair: D2 conducts GND->LED anode on reverse input; pin 1 is
        # tied to pin 3 so the unused half carries no current.
        bav = sh.place("Diode:BAV99", f"D{4 + n}", "BAV99",
                       (g(96), g(ybase + 20)), SOT23, LCSC_BAV99)
        sh.net(bav, "3", f"DI{n}_LED", length=g(4))
        sh.net(bav, "1", f"DI{n}_LED", length=g(4))
        sh.gnd(bav, "2", length=g(3))
        sh.series("Device:R", f"R{20 + n}", "47k", (g(134), g(ybase)),
                  "3V3", f"DI{n}", R0805, LCSC_R47K)
        sh.series("Device:C", f"C{24 + n}", "100nF", (g(146), g(ybase + 6)),
                  f"DI{n}", None, C0603, LCSC_C100N, gnd_b=True)
    sh.text("DI1/DI2: 36k series (3x12k 1206, F-7) -> EL357N(D) opto, 47k pull-up "
            "+ 100nF at the MCU side.  Valid input 10.5-100 V.", (g(64), g(124)))

    # ---------------- low-side digital outputs DO1/DO2 ----------------------
    # F-10: two-stage NON-INVERTING NPN driver per channel, gate swing 0/~4.1 V
    # from 5V0. Provably OFF with the MCU pin open: base pulldown holds QnA
    # off -> R_c1 pulls QnB base high -> QnB clamps the gate low; with the
    # whole board unpowered the retained 10k gate pulldown holds the gate at
    # GND. Consequence (accepted): DO1/DO2, like CAN, are inactive during
    # battery-backup operation because 5V0 is absent.
    for n, ybase in ((1, 210), (2, 246)):
        qa, qb = f"Q{3 + 2 * n}", f"Q{4 + 2 * n}"          # Q5/Q6, Q7/Q8
        rb, rbpd, rc1, rpu = (f"R{38 + 4 * n}", f"R{39 + 4 * n}",
                              f"R{40 + 4 * n}", f"R{41 + 4 * n}")
        # stage A: MCU -> 4.7k -> QnA base, 10k base pulldown on the MCU side
        r1 = sh.place("Device:R", rb, "4.7k", (g(56), g(ybase)),
                      R0805, LCSC_R4K7)
        sh.hier(r1, "1", f"DO{n}_GATE", "input", length=g(6))
        sh.net(r1, "2", f"DO{n}_B", length=g(4))
        sh.series("Device:R", rbpd, "10k", (g(46), g(ybase + 6)),
                  f"DO{n}_GATE", None, R0805, LCSC_R10K, gnd_b=True)
        qA = sh.place("Transistor_BJT:Q_NPN_BEC", qa, "MMBT3904",
                      (g(68), g(ybase + 6)), SOT23, LCSC_MMBT3904V)
        sh.net(qA, "1", f"DO{n}_B", length=g(3))
        sh.gnd(qA, "2", length=g(3))
        sh.net(qA, "3", f"DO{n}_X", length=g(3))
        sh.series("Device:R", rc1, "10k", (g(76), g(ybase - 6)),
                  "5V0", f"DO{n}_X", R0805, LCSC_R10K)
        # stage B: inverts again -> non-inverting overall
        qB = sh.place("Transistor_BJT:Q_NPN_BEC", qb, "MMBT3904",
                      (g(88), g(ybase + 6)), SOT23, LCSC_MMBT3904V)
        sh.net(qB, "1", f"DO{n}_X", length=g(3))
        sh.gnd(qB, "2", length=g(3))
        sh.net(qB, "3", f"DO{n}_DRV", length=g(3))
        sh.series("Device:R", rpu, "2.2k", (g(96), g(ybase - 6)),
                  "5V0", f"DO{n}_DRV", R0805, LCSC_R2K2)
        # retained: 100R gate series and 10k gate pulldown
        rg = sh.place("Device:R", f"R{22 + n}", "100R", (g(70 + 36), g(ybase)),
                      R0805, LCSC_R100)
        sh.net(rg, "1", f"DO{n}_DRV", length=g(4))
        sh.net(rg, "2", f"Q{n}_G", length=g(4))
        sh.series("Device:R", f"R{24 + n}", "10k", (g(82 + 36), g(ybase + 6)),
                  f"Q{n}_G", None, R0805, LCSC_R10K, gnd_b=True)
        q = sh.place("Transistor_FET:Q_NMOS_GSD", f"Q{n}", "AM2390N-TP",
                     (g(104 + 36), g(ybase)),
                     "jlc:SOT-23-3_L2.9-W1.3-P1.90-LS2.4-BR", LCSC_NMOS_150V)
        sh.net(q, "1", f"Q{n}_G", length=g(4))
        sh.gnd(q, "2", length=g(3))
        sh.net(q, "3", f"DO{n}_OUT", length=g(4))
        # flyback: anode on the drain, cathode to VIN (SS3200 200V per F-11)
        d = sh.place("Device:D_Schottky", f"D{6 + n}", "SS3200",
                     (g(164), g(ybase - 8)), "Diode_SMD:D_SMA", LCSC_SS3200)
        sh.net(d, "2", f"DO{n}_OUT", length=g(4))
        sh.net(d, "1", "VIN", length=g(4))
    sh.text("DO1/DO2 (F-10): two-stage NPN driver from 5V0, non-inverting, "
            "default OFF (base pulldown + QnB clamps gate; 10k gate pulldown "
            "retained).  SS3200 200V flyback to VIN (F-11).  DO1/DO2 inactive "
            "on battery backup (5V0 absent).", (g(44), g(204)))

    # ---------------- supply / ignition / battery sensing -------------------
    for tag, src, ysense in (("VIN", "VIN", 40), ("IGN", "IGN", 74)):
        prev = src
        for k in range(3):
            nxt = f"{tag}_D{k}" if k < 2 else f"{tag}_SENSE"
            sh.series("Device:R", f"R{30 + (0 if tag == 'VIN' else 3) + k}",
                      "100k", (g(230 + k * 12), g(ysense)), prev, nxt,
                      R0805, LCSC_R100K)
            prev = nxt
        sh.series("Device:R", f"R{36 + (0 if tag == 'VIN' else 1)}", "9.1k",
                  (g(268), g(ysense)), f"{tag}_SENSE", None, R0805, LCSC_R9K1,
                  gnd_b=True)
        sh.series("Device:C", f"C{27 + (0 if tag == 'VIN' else 1)}", "100nF",
                  (g(278), g(ysense)), f"{tag}_SENSE", None, C0603,
                  LCSC_C100N, gnd_b=True)
        # BAV99 rail clamp: signal on pin 3, pin 1 to 3V3, pin 2 to GND
        bav = sh.place("Diode:BAV99", f"D{10 if tag == 'VIN' else 11}", "BAV99",
                       (g(292), g(ysense + 10)), SOT23, LCSC_BAV99)
        sh.net(bav, "3", f"{tag}_SENSE", length=g(4))
        sh.net(bav, "1", "3V3", length=g(4))
        sh.gnd(bav, "2", length=g(3))
        shape = "output"
        sh.hier(sh.place("Connector:TestPoint", f"TP{10 if tag == 'VIN' else 11}",
                         f"{tag}_SENSE", (g(304), g(ysense)), TP),
                "1", f"{tag}_SENSE", shape, length=g(4))
    sh.text("VIN and IGN sensing: 300k (3x100k 0805) : 9.1k, 100nF, BAV99 "
            "clamp to 3V3/GND.  IGN also serves as the EXTI wake input.",
            (g(224), g(30)))

    # battery sense from the SYS power-path node
    sh.series("Device:R", "R38", "1M", (g(230), g(108)), "SYS", "VBAT_SENSE",
              R0805, LCSC_R1M)
    sh.series("Device:R", "R39", "1M", (g(242), g(108)), "VBAT_SENSE", None,
              R0805, LCSC_R1M, gnd_b=True)
    sh.series("Device:C", "C29", "100nF", (g(254), g(108)), "VBAT_SENSE", None,
              C0603, LCSC_C100N, gnd_b=True)
    bs = sh.place("Connector:TestPoint", "TP12", "VBAT_SENSE",
                  (g(266), g(108)), TP)
    sh.hier(bs, "1", "VBAT_SENSE", "output", length=g(4))
    sh.hier(sh.place("Connector:TestPoint", "TP13", "SYS", (g(218), g(116)), TP),
            "1", "SYS", "input", length=g(4))
    sh.text("Battery sense 1M:1M from SYS (~2 uA standing drain).",
            (g(224), g(102)))

    # spare ADC divider footprint, fitted DNP
    sh.series("Device:R", "R40", "100k", (g(230), g(140)), "VIN", "ADC_SPARE",
              R0805, LCSC_R100K, dnp=True)
    sh.series("Device:R", "R41", "9.1k", (g(242), g(140)), "ADC_SPARE", None,
              R0805, LCSC_R9K1, dnp=True, gnd_b=True)
    sp = sh.place("Device:C", "C30", "100nF", (g(254), g(140)), C0603,
                  LCSC_C100N, dnp=True)
    sh.hier(sp, "1", "ADC_SPARE", "output", length=g(5))
    sh.gnd(sp, "2", length=g(3))
    sh.text("Spare ADC divider footprint - fitted DNP (handoff section 5, PB1).",
            (g(224), g(134)))

    return sh


BUILDERS = {"mcu": build_mcu, "storage": build_storage, "io": build_io}

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
