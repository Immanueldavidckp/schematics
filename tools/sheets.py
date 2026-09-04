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
    d1 = sh.place("Device:LED", "D20", "GRN", (g(252), g(158)), LED0603, LCSC_LED_G)
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
    d2 = sh.place("Device:LED", "D21", "BLU", (g(280), g(142)), LED0603, LCSC_LED_G)
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
                  "jlc:XUNPU_MX3.0-12PZZ_2x06_P3.00mm_Vertical",
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


# ------------------------------------------------------------------ MODEM_RF

# F-8/M2 sweep selections for modem_rf (2026-09-02, all API/browser-verified)
LCSC_EC200U = "C2916205"       # BOM part EC200UCNAA-N05-SGNSA; symbol source C2916206
LCSC_TXB0104 = "C60708"        # TI TXB0104PWR TSSOP-14
LCSC_SIM = "C53207808"         # JXTCONN NANO SIM 7P 1.37H PUSH (6 contacts + CD)
LCSC_UFL = "C53133524"         # XYECONN XY-IPEX1 (IPEX gen-1 / U.FL, 6 GHz 50R)
LCSC_USBLC6 = "C7519"          # ST USBLC6-2SC6 (genuine)
LCSC_SMF05C = "C15879"         # onsemi SMF05CT1G SOT-363
LCSC_AO3401A = "C15127"        # AOS AO3401A -30V 4A SOT-23
LCSC_MMBT3906 = "C75549"       # Nexperia MMBT3906,215
LCSC_SMF50A = "C193402"        # MDD SMF5.0A (modem VBAT clamp)
LCSC_C100U = "C49066"          # Samsung CL32A107MQVNNNE 100uF 6.3V X5R 1210
LCSC_C10U = "C440198"          # Murata GRM21BR61H106KE43L 10uF 50V X5R 0805
C1210 = "Capacitor_SMD:C_1210_3225Metric"


def _ec200u_verified_pins():
    """Parse docs/ec200u-pinmap-extracted.md -> (verified: {pin: name},
    needs_human: {pin: name}). Single source of truth for the F-9 gate."""
    import re as _re
    path = os.path.join(PROJ, "docs", "ec200u-pinmap-extracted.md")
    ver, human = {}, {}
    for ln in open(path, encoding="utf-8"):
        m = _re.match(r"\| (\d+) \| ([^|]+) \| (VERIFIED|NEEDS-HUMAN) \|", ln)
        if m:
            pin, name, status = m.group(1), m.group(2).strip(), m.group(3)
            (ver if status == "VERIFIED" else human)[pin] = name
    assert len(ver) + len(human) == 144, "pin map doc incomplete"
    return ver, human


def build_modem_rf():
    sh = Sheet("modem_rf", paper="A2")
    sh.text("MODEM + RF - Quectel EC200U-CN (BOM part C2916205; schematic symbol "
            "imported from C2916206 after F-9). Wiring per Quectel EC200U HW "
            "Design V1.2 and handoff section 6.", (g(20), g(14)), 2.0)
    sh.text("F-9 SIGNED OFF 2026-09-04. All 43 GND pads are connected per "
            "Quectel EC200U HW Design V1.2 Table 7 p.21 / Table 9 p.36: "
            "\"8, 9, 19, 22, 36, 46, 48, 50-54, 56, 72, 76, 85-112\". "
            "F-9b reverse check clean - no GND pad omitted. Remaining "
            "NEEDS-HUMAN pins stay no-connect (Table 7 note 3).",
            (g(20), g(18)))

    ver, human = _ec200u_verified_pins()

    u1 = sh.place("jlc:EC200UCNLA-N05-SGNSA", "U1", "EC200UCNAA-N05-SGNSA",
                  (g(160), g(140)),
                  "jlc:LCC-LGA-144_L31.0-W28.0-P1.30_L610-CN-02", LCSC_EC200U,
                  fields={"SymbolSource": "C2916206 (F-9)"})

    WIRE = {
        "57": ("VBAT_MODEM", "net"), "58": ("VBAT_MODEM", "net"),
        "59": ("VBAT_MODEM", "net"), "60": ("VBAT_MODEM", "net"),
        "20": ("RESETN_MOD", "net"), "21": ("PWRKEY_MOD", "net"),
        "61": ("STATUS_MOD", "net"),
        "67": ("MTXD_1V8", "net"), "68": ("MRXD_1V8", "net"),
        "62": ("MRI_1V8", "net"), "66": ("MDTR_1V8", "net"),
        "69": ("USB_DP_M", "net"), "70": ("USB_DM_M", "net"),
        "71": ("USB_VBUS", "net"),
        "14": ("USIM_VDD", "net"), "15": ("USIM_DATA_M", "net"),
        "16": ("USIM_CLK_M", "net"), "17": ("USIM_RST_M", "net"),
        "13": ("USIM_DET", "net"), "10": ("GND", "net"),
        "47": ("ANT_GNSS_M", "net"), "49": ("ANT_MAIN_M", "net"),
        "7": ("VDD_EXT_1V8", "net"), "6": ("NETLIGHT_MOD", "net"),
    }
    review = []
    for pin in sorted(u1.pins, key=int):
        if pin in WIRE:
            assert pin in ver, f"pin {pin} is wired but NOT VERIFIED -- F-9 gate"
            sh.net(u1, pin, WIRE[pin][0], length=g(4))
        elif pin in ver and ver[pin] == "GND":
            sh.gnd(u1, pin, length=g(3))
        else:
            sh.nc(u1, pin)
            if pin in human:
                review.append(pin)
    sh.text(f"F9-REVIEW: {len(review)} unused/RESERVED pins remain no-connect "
            f"pending human review before any future use "
            f"(Table 7 note 3: keep RESERVED and unused pins unconnected):",
            (g(20), g(230)))
    sh.text("  " + ", ".join(review), (g(20), g(234)))
    sh.text("THERMAL RELIEF PLAN (F-9, for layout): pads 85-112 are the "
            "central thermal/ground lattice - stitch every one straight down "
            "to the L2 solid GND plane with its own via (no thermal spokes, "
            "solid connection). Pad 76 is the local audio ground and pads "
            "46/48/50/51 are the RF ground fence flanking ANT_GNSS(47)/"
            "ANT_MAIN(49) - fence pads get >=2 vias each, placed to keep the "
            "CPWG return path continuous. Perimeter grounds 8/9/19/22/36/"
            "52/53/54/56/72 get >=1 via each.", (g(20), g(238)))

    # ---- VBAT_MODEM decoupling + clamp, <=5mm from U1 at layout -----------
    sh.series("Device:C", "C40", "100uF", (g(60), g(40)), "VBAT_MODEM", None,
              C1210, LCSC_C100U, gnd_b=True)
    sh.series("Device:C", "C41", "100uF", (g(70), g(40)), "VBAT_MODEM", None,
              C1210, LCSC_C100U, gnd_b=True)
    sh.series("Device:C", "C42", "1uF", (g(80), g(40)), "VBAT_MODEM", None,
              C0603, LCSC_C1U, gnd_b=True)
    sh.series("Device:C", "C43", "100nF", (g(90), g(40)), "VBAT_MODEM", None,
              C0603, LCSC_C100N, gnd_b=True)
    dv = sh.place("jlc:SMF5.0A_C193402", "D12", "SMF5.0A",
                  (g(100), g(46)), "jlc:SOD-123FL_L2.7-W1.8-LS3.8-RD",
                  LCSC_SMF50A)
    sh.net(dv, "1", "VBAT_MODEM", length=g(3))     # cathode to rail
    sh.gnd(dv, "2", length=g(3))
    sh.text("VBAT_MODEM: 2x100uF + 1uF + 100nF + SMF5.0A, place <=5mm from "
            "U1 VBAT pads (57-60).", (g(50), g(32)))

    # ---- Q3 modem power switch: default ON, MODEM_PWR_EN high = power cut --
    q3 = sh.place("jlc:AO3401A", "Q3", "AO3401A", (g(36), g(60)),
                  "jlc:SOT-23-3_L2.9-W1.3-P1.90-LS2.4-BR", LCSC_AO3401A)
    sh.hier(q3, "2", "SYS", "input", length=g(6))          # source
    sh.net(q3, "3", "VBAT_MODEM", length=g(4))             # drain
    sh.net(q3, "1", "Q3_G", length=g(4))
    sh.series("Device:R", "R50", "100k", (g(24), g(70)), "Q3_G", None,
              R0805, LCSC_R100K, gnd_b=True)               # default ON
    q13 = sh.place("Transistor_BJT:Q_PNP_BEC", "Q13", "MMBT3906",
                   (g(48), g(76)), SOT23, LCSC_MMBT3906)
    sh.net(q13, "2", "SYS", length=g(3))                   # emitter
    sh.net(q13, "3", "Q3_G", length=g(3))                  # collector
    sh.net(q13, "1", "Q13_B", length=g(3))
    sh.series("Device:R", "R51", "10k", (g(60), g(82)), "Q13_B", "Q14_C",
              R0805, LCSC_R10K)
    sh.series("Device:R", "R52", "47k", (g(48), g(90)), "SYS", "Q13_B",
              R0805, LCSC_R47K)
    q14 = sh.place("Transistor_BJT:Q_NPN_BEC", "Q14", "MMBT3904",
                   (g(72), g(90)), SOT23, LCSC_MMBT3904V)
    sh.net(q14, "3", "Q14_C", length=g(3))
    sh.gnd(q14, "2", length=g(3))
    sh.net(q14, "1", "Q14_B", length=g(3))
    r53 = sh.place("Device:R", "R53", "4.7k", (g(84), g(84)), R0805, LCSC_R4K7)
    sh.hier(r53, "1", "MODEM_PWR_EN", "input", length=g(6))
    sh.net(r53, "2", "Q14_B", length=g(3))
    sh.series("Device:R", "R54", "47k", (g(94), g(96)), "Q14_B", None,
              R0805, LCSC_R47K, gnd_b=True)
    sh.text("Q3 high-side switch: DEFAULT ON (R50 pulls gate low). "
            "MODEM_PWR_EN HIGH = modem power CUT (power-cycle). Q14 NPN "
            "level stage + Q13 PNP pull gate to SYS.", (g(20), g(102)))

    # ---- PWRKEY / RESET_N open-collector NPN stages ------------------------
    for ref, rref, sig, mod in (("Q9", 55, "MODEM_PWRKEY", "PWRKEY_MOD"),
                                ("Q10", 57, "MODEM_RESET", "RESETN_MOD")):
        qq = sh.place("Transistor_BJT:Q_NPN_BEC", ref, "MMBT3904",
                      (g(36 + (0 if ref == "Q9" else 28)), g(120)),
                      SOT23, LCSC_MMBT3904V)
        rr = sh.place("Device:R", f"R{rref}", "4.7k",
                      (g(24 + (0 if ref == "Q9" else 28)), g(112)),
                      R0805, LCSC_R4K7)
        sh.hier(rr, "1", sig, "input", length=g(6))
        sh.net(rr, "2", f"{ref}_B", length=g(3))
        sh.net(qq, "1", f"{ref}_B", length=g(3))
        sh.gnd(qq, "2", length=g(3))
        sh.net(qq, "3", mod, length=g(3))
        sh.series("Device:R", f"R{rref + 1}", "47k",
                  (g(30 + (0 if ref == "Q9" else 28)), g(130)),
                  f"{ref}_B", None, R0805, LCSC_R10K, gnd_b=True)

    # ---- STATUS: Quectel Fig 28 NPN stage (MODEM_STATUS is INVERTED) -------
    sh.series("Device:R", "R59", "4.7k", (g(96), g(112)), "STATUS_MOD",
              "Q11_B", R0805, LCSC_R4K7)
    q11 = sh.place("Transistor_BJT:Q_NPN_BEC", "Q11", "MMBT3904",
                   (g(108), g(120)), SOT23, LCSC_MMBT3904V)
    sh.net(q11, "1", "Q11_B", length=g(3))
    sh.gnd(q11, "2", length=g(3))
    sh.hier(q11, "3", "MODEM_STATUS", "output", length=g(5))
    sh.series("Device:R", "R60", "47k", (g(102), g(130)), "Q11_B", None,
              R0805, LCSC_R47K, gnd_b=True)
    r61 = sh.place("Device:R", "R61", "47k", (g(118), g(112)), R0805, LCSC_R47K)
    sh.hier(r61, "1", "3V3", "input", length=g(5))   # brings 3V3 onto this sheet
    sh.net(r61, "2", "MODEM_STATUS", length=g(3))
    tp = sh.place("Connector:TestPoint", "TP14", "MODEM_STATUS",
                  (g(130), g(120)), TP)
    sh.net(tp, "1", "MODEM_STATUS", length=g(4))
    sh.text("STATUS per Quectel Fig 28 NPN stage. NOTE: MODEM_STATUS at the "
            "MCU is INVERTED (low = modem running) - firmware note logged.",
            (g(92), g(136)))

    # ---- UART level shifter U8: VCCA=VDD_EXT 1.8V, VCCB=3V3 ---------------
    u8 = sh.place("jlc:TXB0104PWR", "U8", "TXB0104PWR", (g(200), g(60)),
                  "jlc:TSSOP-14_L5.0-W4.4-P0.65-LS6.4-BL", LCSC_TXB0104)
    sh.net(u8, "1", "VDD_EXT_1V8", length=g(4))
    sh.net(u8, "14", "3V3", length=g(4))
    sh.gnd(u8, "7", length=g(3))
    sh.nc(u8, "6"); sh.nc(u8, "9")
    # OE pulldown: outputs Hi-Z until modem's 1.8 V rail is up
    sh.net(u8, "8", "U8_OE", length=g(4))
    sh.series("Device:R", "R62", "10k", (g(178), g(76)), "U8_OE", None,
              R0805, LCSC_R10K, gnd_b=True)
    sh.series("Device:R", "R63", "47k", (g(168), g(52)), "VDD_EXT_1V8",
              "U8_OE", R0805, LCSC_R47K)
    # A side 1.8V, named directly for the modem pins they reach:
    # A1 (from B1 = MODEM_TX) drives modem MAIN_RXD(68); A2 <- MAIN_TXD(67)
    sh.net(u8, "2", "MRXD_1V8", length=g(4))
    sh.net(u8, "3", "MTXD_1V8", length=g(4))
    sh.net(u8, "4", "MRI_1V8", length=g(4))
    sh.net(u8, "5", "MDTR_1V8", length=g(4))
    # B side 3.3V to MCU (hier)
    hb = {"13": ("MODEM_TX", "input"), "12": ("MODEM_RX", "output"),
          "11": ("MODEM_RI", "output"), "10": ("MODEM_DTR", "input")}
    for pin, (net, shape) in hb.items():
        sh.hier(u8, pin, net, shape, length=g(6))
    sh.series("Device:C", "C44", "1uF", (g(168), g(40)), "VDD_EXT_1V8", None,
              C0603, LCSC_C1U, gnd_b=True)
    sh.series("Device:C", "C45", "100nF", (g(178), g(40)), "VDD_EXT_1V8", None,
              C0603, LCSC_C100N, gnd_b=True)
    sh.series("Device:C", "C46", "100nF", (g(188), g(40)), "3V3", None,
              C0603, LCSC_C100N, gnd_b=True)
    sh.text("U8 TXB0104: A=1.8V (VDD_EXT), B=3V3. A1<->B1 carries MCU TX -> "
            "modem MAIN_RXD(68); A2<->B2 modem MAIN_TXD(67) -> MCU RX; "
            "A3 RI(62); A4 DTR(66). OE held low until VDD_EXT rises.",
            (g(160), g(30)))

    # ---- NETLIGHT LED ------------------------------------------------------
    sh.series("Device:R", "R64", "4.7k", (g(148), g(112)), "NETLIGHT_MOD",
              "Q12_B", R0805, LCSC_R4K7)
    q12 = sh.place("Transistor_BJT:Q_NPN_BEC", "Q12", "MMBT3904",
                   (g(160), g(120)), SOT23, LCSC_MMBT3904V)
    sh.net(q12, "1", "Q12_B", length=g(3))
    sh.gnd(q12, "2", length=g(3))
    sh.net(q12, "3", "NETLED_K", length=g(3))
    d13 = sh.place("Device:LED", "D13", "NET", (g(160), g(104)), LED0603,
                   LCSC_LED_G)
    sh.net(d13, "1", "NETLED_K", length=g(3))
    sh.net(d13, "2", "NETLED_A", length=g(3))
    sh.series("Device:R", "R65", "1k", (g(170), g(98)), "3V3", "NETLED_A",
              R0805, LCSC_R1K)

    # ---- USIM: holder + MFF2 eSIM pads in parallel -------------------------
    for sig, xoff in (("DATA", 0), ("CLK", 10), ("RST", 20)):
        sh.series("Device:R", f"R{66 + xoff // 10}", "33R",
                  (g(232 + xoff), g(60)), f"USIM_{sig}_M", f"SIM_{sig}",
                  R0805, LCSC_R100)   # F-5 provisional: 33R 0805 to verify
    sh.series("Device:C", "C47", "100nF", (g(262), g(60)), "USIM_VDD", None,
              C0603, LCSC_C100N, gnd_b=True)
    x1 = sh.place("jlc:NANOSIM7P1.37HPUSH", "X1", "NANO-SIM",
                  (g(250), g(100)), "jlc:SIM-SMD_YKSIM-PUSH137-140NANO",
                  LCSC_SIM)
    sh.net(x1, "C1", "USIM_VDD_SIM", length=g(4))
    sh.net(x1, "C2", "SIM_RST", length=g(4))
    sh.net(x1, "C3", "SIM_CLK", length=g(4))
    sh.net(x1, "C7", "SIM_DATA", length=g(4))
    sh.net(x1, "CD", "USIM_DET", length=g(4))
    sh.gnd(x1, "C5", length=g(3))
    sh.nc(x1, "C6")
    for pnum in ("8", "9", "10", "11"):
        sh.gnd(x1, pnum, length=g(3))              # shield/mount pads
    # MFF2 eSIM pads in parallel, VDD via 0R selects (eSIM path DNP)
    # X2 pin map per ETSI TS 102 671 R12 / ST VFDFPN8 (1GLOBAL MFF2 datasheet
    # fig.1): 1 GND, 2 SWIO(nc), 3 I/O, 4 NC, 5 NC, 6 CLK, 7 /RESET, 8 VCC
    es = sh.place("Connector_Generic:Conn_01x08", "X2", "MFF2-eSIM-pads",
                  (g(282), g(100)), "TBD-MFF2:eSIM_MFF2_VFDFPN8", "DNP-MFF2",
                  dnp=True)
    sh.gnd(es, "1", length=g(3))
    sh.nc(es, "2")
    sh.net(es, "3", "SIM_DATA", length=g(4))
    sh.nc(es, "4")
    sh.nc(es, "5")
    sh.net(es, "6", "SIM_CLK", length=g(4))
    sh.net(es, "7", "SIM_RST", length=g(4))
    sh.net(es, "8", "USIM_VDD_ESIM", length=g(4))
    sh.series("Device:R", "R69", "0R", (g(272), g(76)), "USIM_VDD",
              "USIM_VDD_SIM", R0805, LCSC_R0)
    sh.series("Device:R", "R70", "0R", (g(282), g(76)), "USIM_VDD",
              "USIM_VDD_ESIM", R0805, LCSC_R0, dnp=True)
    # ESD array at the holder
    e1 = sh.place("jlc:SMF05CT1G", "D14", "SMF05C", (g(232), g(130)),
                  "jlc:SOT-363_L2.0-W1.3-P0.65-LS2.1-BR", LCSC_SMF05C)
    sh.net(e1, "1", "SIM_DATA", length=g(4))
    sh.net(e1, "3", "SIM_CLK", length=g(4))
    sh.net(e1, "4", "SIM_RST", length=g(4))
    sh.net(e1, "5", "USIM_VDD", length=g(4))
    sh.gnd(e1, "2", length=g(3))
    sh.nc(e1, "6")
    sh.text("USIM: 33R series on DATA/CLK/RST, 100nF on VDD, SMF05C at the "
            "holder. MFF2 eSIM pads (X2, DNP) parallel; VDD via 0R selects "
            "R69 (fitted, holder) / R70 (DNP, eSIM). SMF05C pin2=GND to be "
            "confirmed at footprint verification.", (g(226), g(146)))

    # ---- USB to test pads with ESD -----------------------------------------
    ud = sh.place("jlc:USBLC6-2SC6", "D15", "USBLC6-2SC6", (g(60), g(160)),
                  "jlc:SOT-23-6_L2.9-W1.6-P0.95-LS2.8-BL", LCSC_USBLC6)
    sh.net(ud, "1", "USB_DP_M", length=g(4))
    sh.net(ud, "3", "USB_DM_M", length=g(4))
    sh.net(ud, "6", "USB_DP_TP", length=g(4))
    sh.net(ud, "4", "USB_DM_TP", length=g(4))
    sh.net(ud, "5", "USB_VBUS", length=g(4))
    sh.gnd(ud, "2", length=g(3))
    for i, (net, x) in enumerate((("USB_DP_TP", 90), ("USB_DM_TP", 98),
                                  ("USB_VBUS", 106))):
        tp = sh.place("Connector:TestPoint", f"TP{15 + i}", net,
                      (g(x), g(158)), TP)
        sh.net(tp, "1", net, length=g(3))
    tpg = sh.place("Connector:TestPoint", "TP18", "GND", (g(114), g(158)), TP)
    sh.gnd(tpg, "1", length=g(3))
    sh.text("USB (FOTA/Quectel tools): DP/DM/VBUS + GND on 4 test pads via "
            "USBLC6-2SC6 flow-through ESD.", (g(52), g(172)))

    # ---- RF: pi networks + U.FL --------------------------------------------
    for tag, base, ref in (("MAIN", 190, 0), ("GNSS", 190 + 40, 1)):
        yb = 160
        rs = sh.place("Device:R", f"R{71 + ref}", "0R",
                      (g(base), g(yb)), "Resistor_SMD:R_0402_1005Metric",
                      LCSC_R0)
        sh.net(rs, "1", f"ANT_{tag}_M", length=g(4))
        sh.net(rs, "2", f"ANT_{tag}_C", length=g(4))
        c1 = sh.place("Device:C", f"C{48 + 2 * ref}", "DNP",
                      (g(base - 6), g(yb + 8)),
                      "Capacitor_SMD:C_0402_1005Metric", "", dnp=True)
        sh.net(c1, "1", f"ANT_{tag}_M", length=g(3))
        sh.gnd(c1, "2", length=g(3))
        c2 = sh.place("Device:C", f"C{49 + 2 * ref}", "DNP",
                      (g(base + 6), g(yb + 8)),
                      "Capacitor_SMD:C_0402_1005Metric", "", dnp=True)
        sh.net(c2, "1", f"ANT_{tag}_C", length=g(3))
        sh.gnd(c2, "2", length=g(3))
        af = sh.place("jlc:XY-IPEX1", f"AF{1 + ref}", "U.FL",
                      (g(base + 16), g(yb - 8)), "jlc:CONN-SMD_XY-IPEX1",
                      LCSC_UFL)
        sh.net(af, "3", f"ANT_{tag}_C", length=g(4))
        sh.nc(af, "4")
        sh.gnd(af, "1", length=g(3))
        sh.gnd(af, "2", length=g(3))
    sh.text("ANT_MAIN(49) / ANT_GNSS(47): 50R CPWG at layout, pi network "
            "(series 0R fitted, shunts DNP) to U.FL. SMA drill template is a "
            "housing option, not a board part.", (g(182), g(178)))

    return sh


# -------------------------------------------------------------------- POWER

LCSC_EG11752 = "C53368402"     # EG11752 200V 2A buck (U5, approved)
LCSC_SMDJ100A = "C1977839"     # Littelfuse SMDJ100A 3kW (D2, approved)
LCSC_S3M = "C5204901"          # TWGMC S3M 1kV 3A (SMB variant)
LCSC_FUSE = "C95352"           # Littelfuse 0443001.DR 1A 250VAC/VDC
LCSC_L150U = "C21325"          # SMDRI127-151MT 150uH Isat 2.7A
LCSC_L2R2 = "C391305"          # Murata DFE252012P-2R2M 2.2uH
LCSC_C2U2_100V = "C5449052"    # CCTC TCC1210X7R225K101MT 2.2uF 100V X7R 1210
LCSC_BQ25606 = "C374063"
LCSC_ME6211 = "C82942"
LCSC_JST_XH3 = "C144394"       # JST B3B-XH-A(LF)(SN)


def build_power():
    sh = Sheet("power", paper="A3")
    sh.text("POWER - 10.5-100 V front end, EG11752 buck (U5, approved with "
            "conditions a-c), BQ25606 charger, ME6211 3V3 LDO.",
            (g(20), g(14)), 2.0)

    # ---- HV front end -------------------------------------------------------
    f1 = sh.place("jlc:0443001.DR", "F1", "1A 250V", (g(40), g(40)),
                  "jlc:FUSE-SMD_L10.1-W3.1", LCSC_FUSE)
    sh.hier(f1, "1", "VIN", "input", length=g(6))
    sh.net(f1, "2", "VIN_F", length=g(4))
    d1 = sh.place("jlc:S3M_C5204901", "D1", "S3M", (g(60), g(40)),
                  "jlc:SMB_L4.3-W3.6-LS5.3-RD", LCSC_S3M)
    sh.net(d1, "2", "VIN_F", length=g(4))       # anode
    sh.net(d1, "1", "VIN_P", length=g(4))       # cathode -> protected node
    d2 = sh.place("Device:D_TVS", "D2", "SMDJ100A", (g(74), g(50)),
                  "Diode_SMD:D_SMC", LCSC_SMDJ100A)
    sh.net(d2, "2", "VIN_P", length=g(3))
    sh.gnd(d2, "1", length=g(3))
    sh.series("Device:C", "C70", "2.2uF 100V", (g(86), g(50)), "VIN_P", None,
              C1210, LCSC_C2U2_100V, gnd_b=True)
    sh.series("Device:C", "C71", "2.2uF 100V", (g(96), g(50)), "VIN_P", None,
              C1210, LCSC_C2U2_100V, gnd_b=True)
    sh.series("Device:C", "C72", "100nF", (g(106), g(50)), "VIN_P", None,
              C0603, LCSC_C100N, gnd_b=True)
    # 10R series to the buck input (TASK A analysed topology)
    # R80: FOJAN FRP2512 2W high-power series (C3013385). Pulse duty per event
    # is ~8.5 mJ (see design-log F-15 math) - well inside 2512 capability -
    # but the 10R VALUE starves the buck at low line: see flag F-15.
    sh.series("Device:R", "R80", "10R 2512", (g(118), g(40)), "VIN_P", "VIN_B",
              "Resistor_SMD:R_2512_6332Metric", "C3013385")
    sh.series("Device:C", "C73", "2.2uF 100V", (g(130), g(50)), "VIN_B", None,
              C1210, LCSC_C2U2_100V, gnd_b=True)
    sh.series("Device:C", "C74", "2.2uF 100V", (g(140), g(50)), "VIN_B", None,
              C1210, LCSC_C2U2_100V, gnd_b=True)
    sh.text("Front end: F1 (250 VDC interrupt) -> D1 S3M reverse block -> "
            "D2 SMDJ100A 3kW -> 10R (2512 anti-surge, F-5: pulse rating to "
            "verify) -> buck. Margin at 3.7A clamp: 34.9% (design-log).",
            (g(30), g(28)))

    # ---- U5 EG11752 buck ----------------------------------------------------
    u5 = sh.place("jlc:EG11752_C53368402", "U5", "EG11752",
                  (g(180), g(48)), "jlc:SOIC-8_L4.9-W3.9-P1.27-LS6.0-BL-EP3.3-1",
                  LCSC_EG11752,
                  fields={"Alternate": "EG11722 C53368437 (150V, derated emergency only)"})
    sh.net(u5, "8", "VIN_B", length=g(4))
    sh.net(u5, "9", "VIN_B", length=g(4))       # EP = VIN per datasheet
    sh.gnd(u5, "3", length=g(3))
    sh.net(u5, "1", "U5_VCC", length=g(4))
    sh.series("Device:C", "C75", "1uF 25V", (g(200), g(28)), "U5_VCC", None,
              C0603, LCSC_C1U, gnd_b=True)
    sh.series("Device:R", "R81", "100k", (g(190), g(28)), "U5_VCC", "U5_EN",
              R0805, LCSC_R100K)
    sh.net(u5, "2", "U5_EN", length=g(4))
    sh.net(u5, "5", "U5_VB", length=g(4))
    sh.net(u5, "6", "SW_BUCK", length=g(4))
    cb = sh.place("Device:C", "C76", "100nF 25V", (g(158), g(34)),
                  C0603, LCSC_C100N)
    sh.net(cb, "1", "U5_VB", length=g(3))
    sh.net(cb, "2", "SW_BUCK", length=g(3))
    # IS sense: F-12 - datasheet gives no R_IS formula; 0R fitted, tune at bench
    sh.series("Device:R", "R82", "0R (F-12)", (g(158), g(60)), "U5_IS",
              "SW_BUCK", R0805, LCSC_R0)
    sh.net(u5, "7", "U5_IS", length=g(4))
    sh.net(u5, "4", "U5_FB", length=g(4))
    # freewheel + inductor + output
    df = sh.place("Device:D_Schottky", "D16", "SS3200", (g(158), g(74)),
                  "Diode_SMD:D_SMA", LCSC_SS3200)
    sh.net(df, "1", "SW_BUCK", length=g(3))     # cathode to switch node
    sh.gnd(df, "2", length=g(3))
    l1 = sh.place("jlc:SMDRI127-151MT", "L1", "150uH 2.7A",
                  (g(214), g(64)), "jlc:IND-SMD_L12.3-W12.3", LCSC_L150U)
    sh.net(l1, "1", "SW_BUCK", length=g(4))
    sh.net(l1, "2", "5V0", length=g(4))
    # FB divider: 4.3k / 1.5k -> 5.03 V (datasheet 8.5 worked example)
    sh.series("Device:R", "R83", "4.3k", (g(196), g(76)), "5V0", "U5_FB",
              R0805, "TBD-F5")
    sh.series("Device:R", "R84", "1.5k", (g(206), g(84)), "U5_FB", None,
              R0805, "TBD-F5", gnd_b=True)
    for i, x in enumerate((226, 236, 246)):
        sh.series("Device:C", f"C{77 + i}", "10uF", (g(x), g(74)), "5V0", None,
                  C0805, LCSC_C10U, gnd_b=True)
    sh.series("Device:C", "C80", "100nF", (g(256), g(74)), "5V0", None,
              C0603, LCSC_C100N, gnd_b=True)
    tp5 = sh.place("Connector:TestPoint", "TP19", "5V0", (g(238), g(60)), TP)
    sh.hier(tp5, "1", "5V0", "output", length=g(5))
    sh.text("U5 EG11752: EN 100k from VCC (per fig 6-2); VB-VS 100nF boot; "
            "IS via R82 0R - F-12: no R_IS formula in the V1.0 datasheet, "
            "bench/FAE item; FB 4.3k/1.5k -> 5.03V; L 150uH (Isat 2.7A); "
            "SS3200 freewheel. #1 bench test: 100V in, 0.7-1A out, Ton~455ns.",
            (g(150), g(96)))

    # ---- U6 BQ25606 charger -------------------------------------------------
    u6 = sh.place("jlc:BQ25606RGER", "U6", "BQ25606RGER", (g(90), g(150)),
                  "jlc:VQFN-24_L4.0-W4.0-P0.50-TL-EP2.8", LCSC_BQ25606)
    sh.net(u6, "24", "5V0", length=g(4))
    sh.net(u6, "1", "5V0", length=g(4))          # VAC shorted to VBUS (Table 7)
    sh.series("Device:C", "C61", "1uF", (g(56), g(128)), "5V0", None,
              C0603, LCSC_C1U, gnd_b=True)
    sh.net(u6, "23", "PMID", length=g(4))
    sh.series("Device:C", "C62", "10uF", (g(66), g(128)), "PMID", None,
              C0805, LCSC_C10U, gnd_b=True)
    sh.net(u6, "22", "REGN", length=g(4))
    sh.series("Device:C", "C63", "4.7uF", (g(76), g(128)), "REGN", None,
              C0805, LCSC_C4U7, gnd_b=True)
    sh.net(u6, "21", "U6_BTST", length=g(4))
    cbt = sh.place("Device:C", "C64", "47nF", (g(120), g(128)), C0603,
                   "TBD-F5")
    sh.net(cbt, "1", "U6_BTST", length=g(3))
    sh.net(cbt, "2", "SW_CHG", length=g(3))
    sh.net(u6, "19", "SW_CHG", length=g(4))
    sh.net(u6, "20", "SW_CHG", length=g(4))
    l3 = sh.place("jlc:DFE252012P-2R2M=P2", "L3", "2.2uH",
                  (g(134), g(140)), "jlc:L1008", LCSC_L2R2)
    sh.net(l3, "1", "SW_CHG", length=g(4))
    sh.net(l3, "2", "SYS", length=g(4))
    sh.net(u6, "15", "SYS", length=g(4))
    sh.net(u6, "16", "SYS", length=g(4))
    for i, x in enumerate((148, 158)):
        sh.series("Device:C", f"C{65 + i}", "10uF", (g(x), g(148)), "SYS",
                  None, C0805, LCSC_C10U, gnd_b=True)
    tps = sh.place("Connector:TestPoint", "TP20", "SYS", (g(168), g(140)), TP)
    sh.hier(tps, "1", "SYS", "output", length=g(5))
    sh.net(u6, "13", "VBAT_BT", length=g(4))
    sh.net(u6, "14", "VBAT_BT", length=g(4))
    sh.series("Device:C", "C67", "10uF", (g(120), g(178)), "VBAT_BT", None,
              C0805, LCSC_C10U, gnd_b=True)
    for pin in ("17", "18", "25"):
        sh.gnd(u6, pin, length=g(3))
    # programming pins
    sh.series("Device:R", "R85", "976R", (g(44), g(160)), "U6_ICHG", None,
              R0805, "TBD-F5", gnd_b=True)
    sh.net(u6, "10", "U6_ICHG", length=g(4))
    sh.series("Device:R", "R86", "536R", (g(54), g(168)), "U6_ILIM", None,
              R0805, "TBD-F5", gnd_b=True)
    sh.net(u6, "8", "U6_ILIM", length=g(4))
    sh.gnd(u6, "9", length=g(3))                 # /CE low = charge enabled
    sh.series("Device:R", "R87", "10k", (g(64), g(176)), "U6_OTG", None,
              R0805, LCSC_R10K, gnd_b=True)      # OTG low = no boost
    sh.net(u6, "6", "U6_OTG", length=g(4))
    sh.nc(u6, "3"); sh.nc(u6, "4")               # D+/D- float -> unknown adapter
    sh.nc(u6, "12")                              # VSET float -> 4.208 V
    sh.nc(u6, "2")
    for i, (pin, net) in enumerate((("5", "U6_STAT"), ("7", "U6_PG"))):
        sh.net(u6, pin, net, length=g(4))
        tpx = sh.place("Connector:TestPoint", f"TP{21 + i}", net,
                       (g(36 + 8 * i), g(186)), TP)
        sh.net(tpx, "1", net, length=g(3))
    # TS network: REGN -> 5.23k -> TS -> 30.1k -> GND, NTC (in battery) on TS
    sh.series("Device:R", "R88", "5.23k", (g(90), g(186)), "REGN", "U6_TS",
              R0805, "TBD-F5")
    sh.series("Device:R", "R89", "30.1k", (g(100), g(194)), "U6_TS", None,
              R0805, "TBD-F5", gnd_b=True)
    sh.net(u6, "11", "U6_TS", length=g(4))
    # battery connector
    j2 = sh.place("Connector_Generic:Conn_01x03", "J2", "B3B-XH-A",
                  (g(140), g(186)), "Connector_JST:JST_XH_B3B-XH-A_1x03_P2.50mm_Vertical",
                  LCSC_JST_XH3)
    sh.net(j2, "1", "VBAT_BT", length=g(4))
    sh.net(j2, "2", "U6_TS", length=g(4))
    sh.gnd(j2, "3", length=g(3))
    sh.text("U6 BQ25606: ICHG 976R -> 0.69A; ILIM 536R -> IINDPM 0.89A; "
            "VSET float -> 4.208V; D+/D- float -> unknown adapter (ILIM "
            "governs); TS 5.23k/30.1k + battery 103AT NTC (JEITA; finalize "
            "vs the actual battery NTC - F-5); /CE=GND, OTG low.",
            (g(30), g(204)))

    # ---- U9 3V3 LDO ---------------------------------------------------------
    u9 = sh.place("jlc:ME6211C33M5G-N", "U9", "ME6211C33M5G",
                  (g(220), g(150)), "jlc:SOT-23-5_L3.0-W1.7-P0.95-LS2.8-BL",
                  LCSC_ME6211)
    sh.net(u9, "1", "SYS", length=g(4))
    sh.net(u9, "3", "SYS", length=g(4))          # CE tied high
    sh.gnd(u9, "2", length=g(3))
    sh.nc(u9, "4")
    sh.hier(u9, "5", "3V3", "output", length=g(6))
    sh.series("Device:C", "C68", "1uF", (g(206), g(162)), "SYS", None,
              C0603, LCSC_C1U, gnd_b=True)
    c69 = sh.place("Device:C", "C69", "1uF", (g(236), g(162)), C0603, LCSC_C1U)
    sh.net(c69, "1", "3V3", length=g(3))
    sh.gnd(c69, "2", length=g(3))
    sh.text("U9 ME6211C33M5G: 500mA LDO, SYS -> 3V3 (load ~100mA worst; "
            "dropout margin OK at SYS >= 3.5V).", (g(200), g(172)))

    return sh


BUILDERS = {"mcu": build_mcu, "storage": build_storage, "io": build_io,
            "modem_rf": build_modem_rf, "power": build_power}

RAILS = []
NOTES = []


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
    main(sys.argv[1:] or ["mcu", "storage", "io", "modem_rf", "power"])
