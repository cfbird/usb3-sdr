"""usb3-sdr Rev A netlist, one dict per sheet. Pin maps use symbol pin numbers (verified against datasheets).
Component tuple: (ref, lib_id, value, footprint, {pin: net}, unit)  -- footprint None = symbol default.
"""
R0402, C0402, C0603, C0805 = ("Resistor_SMD:R_0402_1005Metric", "Capacitor_SMD:C_0402_1005Metric",
                              "Capacitor_SMD:C_0603_1608Metric", "Capacitor_SMD:C_0805_2012Metric")
L0805, L0603, LPWR = ("Inductor_SMD:L_0805_2012Metric", "Inductor_SMD:L_0603_1608Metric",
                      "Inductor_SMD:L_Taiyo-Yuden_NR-30xx")
SOT23 = "Package_TO_SOT_SMD:SOT-23"

_auto = {}


def _ref(prefix):
    _auto[prefix] = _auto.get(prefix, 0) + 1
    return f"{prefix}{_auto[prefix]}"


def R(a, b, val, fp=R0402): return (_ref("R"), "Device:R", val, fp, {"1": a, "2": b}, 1)
def C(a, b, val, fp=C0402): return (_ref("C"), "Device:C", val, fp, {"1": a, "2": b}, 1)
def L(a, b, val, fp=L0805): return (_ref("L"), "Device:L", val, fp, {"1": a, "2": b}, 1)
def FB(a, b, val="600R@100MHz"): return (_ref("FB"), "Device:FerriteBead", val, "Inductor_SMD:L_0603_1608Metric", {"1": a, "2": b}, 1)
def PWR(net): return (_ref("#FLG"), "power:PWR_FLAG", "PWR_FLAG", "", {"1": net}, 1)


def decouple(net, vals):
    return [C(net, "GND", v, C0603 if v in ("10u", "4.7u") else C0805 if v == "22u" else C0402) for v in vals]


def lc_lpf(prefix, n_in, n_out):
    """AGY Design A 7th-order elliptic LPF (notes/aaf.md): C1 | L2||C2 | C3 | L4||C4 | C5 | L6||C6 | C7.
    Tank caps are 0805 so their pads sit directly above the 0805 inductor pads in the layout."""
    n2, n4 = f"{prefix}_N2", f"{prefix}_N4"
    fpL = "Inductor_SMD:L_0805_2012Metric"
    return [C(n_in, "GND", "62p C0G 2%"), L(n_in, n2, "180n 0805HP 2%", fpL), C(n_in, n2, "62p C0G 2%", C0805),
            C(n2, "GND", "130p C0G 2%"), L(n2, n4, "270n 0805HP 2%", fpL), C(n2, n4, "30p C0G 2%", C0805),
            C(n4, "GND", "160p C0G 2%"), L(n4, n_out, "270n 0805HP 2%", fpL), C(n4, n_out, "11p C0G 2%", C0805),
            C(n_out, "GND", "91p C0G 2%")]


def relay(ref, com_a, nc_a, no_a, com_b, nc_b, no_b, drive_net):
    """HFD4/5-SR (G6K-2 symbol; wiring verified: coil 1+/8-, COM 3/6, NC 2/7, NO 4/5) + low-side driver."""
    coil = f"{ref}_COIL"
    q = _ref("Q")
    return [(ref, "Relay:G6K-2", "HFD4/5-SR", "usb3sdr:Relay_DPDT_Hongfa_HFD4-SR",
             {"1": "5V_SW", "8": coil, "3": com_a, "2": nc_a, "4": no_a, "6": com_b, "7": nc_b, "5": no_b}, 1),
            (_ref("D"), "Diode:1N4148W", "1N4148W", "Diode_SMD:D_SOD-123", {"1": "5V_SW", "2": coil}, 1),
            (q, "Transistor_FET:2N7002", "2N7002", SOT23, {"1": f"{q}_G", "2": "GND", "3": coil}, 1),
            R(drive_net, f"{q}_G", "100"), R(f"{q}_G", "GND", "100k")]


# ================================================================ sheets
def power():
    s = [
        (_ref("F"), "Device:Polyfuse", "1.1A", "Fuse:Fuse_1206_3216Metric", {"1": "VBUS", "2": "VBUS_F"}, 1),
        (_ref("D"), "Device:D_TVS", "SMF5.0A", "Diode_SMD:D_SOD-123F", {"1": "VBUS_F", "2": "GND"}, 1),
        *decouple("VBUS_F", ["22u", "100n"]),
        ("U1", "Power_Management:TPS22917DBV", "TPS22918DBVR", None,
         {"1": "VBUS_F", "2": "GND", "3": "LS_ON", "4": "LS_CT", "5": "", "6": "5V_SW"}, 1),
        R("VBUS_F", "LS_ON", "100k"), R("LS_ON", "GND", "100k"), C("LS_CT", "GND", "1n"),
        *decouple("5V_SW", ["22u", "100n"]),
        # 1V1 core buck: Vout = 0.6 (1 + 100k/120k) = 1.100 V
        ("U2", "Regulator_Switching:TPS62A02ADRL", "TPS62A02ADRLR", None,
         {"1": "GND", "2": "SW_1V1", "3": "5V_SW", "4": "5V_SW", "5": "FB_1V1", "6": "PG_1V1"}, 1),
        L("SW_1V1", "1V1", "1u 2A shielded", LPWR), R("1V1", "FB_1V1", "100k 1%"), R("FB_1V1", "GND", "120k 1%"),
        R("PG_1V1", "1V1", "100k"), *decouple("1V1", ["22u", "22u", "100n"]), *decouple("5V_SW", ["10u"]),
        # 3V3_D buck: Vout = 0.6 (1 + 226k/49.9k) = 3.317 V
        ("U3", "Regulator_Switching:TPS62A02ADRL", "TPS62A02ADRLR (forced PWM)", None,
         {"1": "GND", "2": "SW_3V3", "3": "5V_SW", "4": "5V_SW", "5": "FB_3V3", "6": "PG_3V3"}, 1),
        L("SW_3V3", "3V3_D", "1u 2A shielded", LPWR), R("3V3_D", "FB_3V3", "226k 1%"), R("FB_3V3", "GND", "49.9k 1%"),
        R("PG_3V3", "3V3_D", "100k"), *decouple("3V3_D", ["22u", "22u", "100n"]), *decouple("5V_SW", ["10u"]),
        # AGY round-3 pi post-filter before the LDOs: 1 uH + 0.47 R damping, 10 u + 1 u
        L("3V3_D", "3V3_PF", "1u"), R("3V3_PF", "3V3_D_F", "0.47"), *decouple("3V3_D_F", ["10u", "1u"]),
        ("U4", "Regulator_Linear:TLV75525PDBV", "TLV75525PDBVR", None,
         {"1": "3V3_D_F", "3": "3V3_D_F", "2": "GND", "5": "2V5"}, 1),
        *decouple("2V5", ["1u", "100n"]),
        ("U5", "usb3sdr:TPS7A2018PDBVR", "TPS7A2018PDBVR", None,
         {"1": "3V3_D_F", "3": "3V3_D_F", "2": "GND", "5": "1V8_D"}, 1),
        *decouple("1V8_D", ["1u", "100n"]),
        # analog chain from 5V
        FB("5V_SW", "5V_A"), *decouple("5V_A", ["10u", "100n"]),
        ("U6", "usb3sdr:TPS7A2033PDBVR", "TPS7A2033PDBVR", None,
         {"1": "5V_A", "3": "5V_A", "2": "GND", "5": "3V3_A"}, 1),
        *decouple("3V3_A", ["1u", "100n"]),
        ("U7", "usb3sdr:TPS7A2018PDBVR", "TPS7A2018PDBVR", None,
         {"1": "3V3_A", "3": "3V3_A", "2": "GND", "5": "1V8_A"}, 1),
        *decouple("1V8_A", ["1u", "100n"]),
        # LNA supply switch: P-FET high side, driven by LNA_EN
        ("Q10", "Transistor_FET:AO3401A", "AO3401A", SOT23, {"1": "Q10_G", "2": "5V_SW", "3": "5V_LNA"}, 1),
        R("5V_SW", "Q10_G", "100k"),
        ("Q11", "Transistor_FET:2N7002", "2N7002", SOT23, {"1": "Q11_G", "2": "GND", "3": "Q10_G"}, 1),
        R("LNA_EN", "Q11_G", "100"), R("Q11_G", "GND", "100k"), *decouple("5V_LNA", ["10u", "100n"]),
    ]
    # PWR_FLAG only where no power-output pin drives the net (J1 drives VBUS/GND, U1 drives 5V_SW)
    s += [PWR(n) for n in ("VBUS_F", "5V_A", "1V1", "3V3_D", "3V3_D_F")]
    return s


def rf():
    s = [
        ("J2", "Connector:Conn_Coaxial", "SMA RF IN", "Connector_Coaxial:SMA_Amphenol_132289_EdgeMount",
         {"1": "RF_IN", "2": "GND"}, 1),
        # Bourns 2038-09-SM is 3-electrode: line 1, centre ground 2, line 3 also grounded -> single line-to-GND arrester
        ("GDT1", "Device:GDT_3Pin", "2038-09-SM (90V)", "Fuse:GDT_Bourns_2038", {"1": "RF_IN", "2": "GND", "3": "GND"}, 1),
        # antiparallel clamp: common node (pin 3) to the line, outer pins to GND
        ("D10", "Diode:BAV99", "BAV99", SOT23, {"3": "RF_IN", "1": "GND", "2": "GND"}, 1),
        # 20 dB pad relay: de-energised = through (NC)
        *relay("K1", "RF_IN", "PAD_BYP", "PAD_IN", "RF_A", "PAD_BYP", "PAD_OUT", "RLY_PAD"),
        R("PAD_IN", "GND", "61.9 1%"), R("PAD_IN", "PAD_OUT", "249 1%"), R("PAD_OUT", "GND", "61.9 1%"),
        *lc_lpf("LPF1", "RF_A", "LPF1_OUT"),
        # FM band-stop (notes/aaf.md section 3): trap1 82n+39p shunt, tank 180n||15p series, trap3 47n+47p shunt
        L("LPF1_OUT", "TRAP1", "82n 0805HP 2%"), C("TRAP1", "GND", "39p C0G 2%"),
        L("LPF1_OUT", "NOTCH_OUT", "180n 0805HP 2%"), C("LPF1_OUT", "NOTCH_OUT", "15p C0G 2%", C0805),
        L("NOTCH_OUT", "TRAP3", "47n 0805HP 2%"), C("TRAP3", "GND", "47p C0G 2%"),
        # LNA bypass relay
        *relay("K2", "NOTCH_OUT", "LNA_BYP", "LNA_IN", "LPF2_IN", "LNA_BYP", "LNA_PAD_OUT", "RLY_LNA"),
        C("LNA_IN", "LNA_RFIN", "100n"),
        ("U13", "RF_Amplifier:PHA-13LN", "PHA-13LN+", None, {"1": "LNA_RFIN", "2": "GND", "3": "LNA_RFOUT"}, 1),
        L("5V_LNA", "LNA_RFOUT", "15u bias choke", "Inductor_SMD:L_1206_3216Metric"),
        C("LNA_RFOUT", "LNA_O", "100n"),
        # 3 dB pi pad after the LNA (E96: 294 / 17.8 / 294)
        R("LNA_O", "GND", "294 1%"), R("LNA_O", "LNA_PAD_OUT", "17.8 1%"), R("LNA_PAD_OUT", "GND", "294 1%"),
        *lc_lpf("LPF2", "LPF2_IN", "LPF2_OUT"),
        # 1:4 transformer to the ADC, 200 R differential termination, kickback filter (33 R + 10 pF at the ADC)
        ("T1", "usb3sdr:ADT4-6T", "ADT4-6T+", None,
         {"3": "LPF2_OUT", "1": "GND", "2": "", "4": "AIN_P_T", "6": "AIN_N_T", "5": "ADC_VCM"}, 1),
        R("AIN_P_T", "AIN_N_T", "200 1%"),
        R("AIN_P_T", "ADC_VINP", "33"), R("AIN_N_T", "ADC_VINN", "33"),
    ]
    return s


def adc_clk():
    d = {str(p): f"ADC_D{i}_R" for i, p in enumerate([7, 8, 9, 10, 11, 12, 14, 15, 16, 17, 18, 19, 20, 21])}
    pins = {"31": "ADC_VINP", "30": "ADC_VINN", "27": "ADC_VCM", "25": "ADC_VREF", "26": "GND", "28": "ADC_RBIAS",
            "1": "ADC_CLKP", "2": "ADC_CLKN", "4": "ADC_CSB", "5": "ADC_SCLK", "6": "ADC_SDIO",
            "22": "ADC_DCO_R", "23": "ADC_OR_R", "3": "1V8_A", "24": "1V8_A", "29": "1V8_A", "32": "1V8_A",
            "13": "1V8_D", "33": "GND", **d}
    s = [("U8", "usb3sdr:AD9649BCPZ-80", "AD9649BCPZ-80", None, pins, 1)]
    s += [R(f"ADC_D{i}_R", f"ADC_D{i}", "22") for i in range(14)]
    s += [R("ADC_DCO_R", "ADC_DCO", "22"), R("ADC_OR_R", "ADC_OR", "22")]
    s += [C("ADC_VINP", "GND", "10p C0G"), C("ADC_VINN", "GND", "10p C0G"), C("ADC_VCM", "GND", "100n"),
          C("ADC_VREF", "GND", "1u"), C("ADC_VREF", "GND", "100n"), R("ADC_RBIAS", "GND", "10k 1%")]
    s += decouple("1V8_A", ["10u", "100n", "100n", "100n", "100n"]) + decouple("1V8_D", ["1u", "100n"])
    # LMK61E2: ADD = GND -> I2C address 0x58 (SNAS674C Table 7-1); OE tied high
    # 8-pin I2C-programmable LMK61E2 (SNAS674C). Not LMK61E2-100M00SIAR: that is a 6-pin fixed-100 MHz part, no I2C.
    s += [("U9", "usb3sdr:LMK61E2-SIA", "LMK61E2-SIAR", None,
           {"1": "3V3_CLK", "2": "GND", "3": "GND", "4": "LMK_OUTP", "5": "LMK_OUTN", "6": "3V3_CLK",
            "7": "LMK_SDA", "8": "LMK_SCL"}, 1),
          FB("3V3_A", "3V3_CLK"), *decouple("3V3_CLK", ["10u", "100n"]),
          # Polarity deliberately swapped (OUTP -> CLK-, OUTN -> CLK+): both parts number their pins counter-clockwise,
          # so facing P->P / N->N would have to cross. Inverting the AC-coupled clock only moves the sampling edge
          # by half a period; DCO follows it (AD9649 Fig. 50 circuit).
          C("LMK_OUTP", "ADC_CLKN", "100n"), C("LMK_OUTN", "ADC_CLKP", "100n"), R("ADC_CLKP", "ADC_CLKN", "100"),
          R("LMK_SDA", "3V3_D", "4.7k"), R("LMK_SCL", "3V3_D", "4.7k"), PWR("3V3_CLK")]
    return s


def usb():
    ft = {"1": "GND", "26": "GND", "29": "GND", "36": "GND", "77": "GND",
          "2": "FT_1V0", "3": "FT_1V0", "30": "FT_1V0", "33": "FT_1V0", "48": "FT_1V0", "39": "FT_1V0",
          "20": "3V3_D", "24": "3V3_D", "38": "3V3_D", "14": "3V3_D", "49": "3V3_D", "59": "3V3_D", "68": "3V3_D",
          "28": "FT_VDDA", "37": "FT_VBUS", "21": "FT_XI", "22": "FT_XO", "23": "USB_D_P", "25": "USB_D_N",
          "27": "FT_RREF", "31": "FT_TXN", "32": "FT_TXP", "34": "USB_SSRXN", "35": "USB_SSRXP",
          "10": "FT_SIWU", "19": "", "17": "FT_GPIO0", "18": "FT_GPIO1",
          "15": "FT_RESET_N", "16": "FT_WAKEUP_N", "8": "FT_TXE_N", "9": "FT_RXF_N", "11": "FT_WR_N",
          "12": "FT_RD_N", "13": "FT_OE_N", "58": "FT_CLK",
          "4": "FT_BE0", "5": "FT_BE1", "6": "FT_BE2", "7": "FT_BE3"}
    data_pins = list(range(40, 48)) + list(range(50, 58)) + list(range(60, 68)) + list(range(69, 77))
    ft.update({str(p): f"FT_D{i}" for i, p in enumerate(data_pins)})
    s = [("U11", "Interface_USB:FT601Q", "FT601Q-B-T", None, ft, 1),
         # USB3 Micro-B: pin names are from the device's side, so FT601 TX -> SSTX (AC caps on the transmitter)
         ("J1", "Connector:USB3_B_Micro", "USB3 Micro-B", "Connector_USB:USB3_Micro-B_Connfly_DS1104-01",
          {"1": "VBUS", "2": "USB_D_N", "3": "USB_D_P", "4": "", "5": "GND", "6": "USB_SSTXN", "7": "USB_SSTXP",
           "8": "GND", "9": "USB_SSRXN", "10": "USB_SSRXP", "11": "USB_SHIELD"}, 1),
         C("FT_TXN", "USB_SSTXN", "100n"), C("FT_TXP", "USB_SSTXP", "100n"),
         R("USB_SHIELD", "GND", "1M"), C("USB_SHIELD", "GND", "4.7n 250V", C0603),
         R("VBUS", "FT_VBUS", "1k"),
         R("FT_RREF", "GND", "1.6k 1%"), R("FT_SIWU", "3V3_D", "10k"),
         ("Y1", "Device:Crystal_GND24", "30MHz 20pF X322530MSB4SI", "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
          {"1": "FT_XI", "3": "FT_XO", "2": "GND", "4": "GND"}, 1),
         C("FT_XI", "GND", "33p C0G"), C("FT_XO", "GND", "33p C0G"),
         FB("3V3_D", "FT_VDDA"), *decouple("FT_VDDA", ["4.7u", "100n"]),
         *decouple("FT_1V0", ["4.7u", "100n", "100n", "100n"]),
         *decouple("3V3_D", ["10u", "100n", "100n", "100n", "100n", "100n", "100n"]),
         PWR("FT_VDDA"), PWR("FT_VBUS")]   # FT_1V0 is driven by the FT601 DV10 LDO output
    return s


def fpga(lpf_path, iodb_units):
    """ECP5 IO units: nets from the gateware LPF (single source of truth for ball -> signal)."""
    import re
    ball_net = {}
    for line in open(lpf_path):
        m = re.match(r'LOCATE COMP "([^"]+)" SITE "([^"]+)"', line)
        if m:
            sig, ball = m.groups()
            sig = sig.replace("[", "").replace("]", "")
            net = {"adc_dco": "ADC_DCO", "adc_or": "ADC_OR", "adc_sclk": "ADC_SCLK", "adc_sdio": "ADC_SDIO",
                   "adc_csb": "ADC_CSB", "ft_clk": "FT_CLK", "ft_txe_n": "FT_TXE_N", "ft_rxf_n": "FT_RXF_N",
                   "ft_wr_n": "FT_WR_N", "ft_rd_n": "FT_RD_N", "ft_oe_n": "FT_OE_N", "ft_reset_n": "FT_RESET_N",
                   "ft_wakeup_n": "FT_WAKEUP_N", "ref10m": "REF10M", "lmk_scl": "LMK_SCL", "lmk_sda": "LMK_SDA",
                   "rly_pad": "RLY_PAD", "rly_lna": "RLY_LNA", "lna_en": "LNA_EN", "led0": "LED0", "led1": "LED1"}.get(sig)
            if net is None:
                mm = re.match(r"(adc_d|ft_data|ft_be)(\d+)", sig)
                net = {"adc_d": "ADC_D", "ft_data": "FT_D", "ft_be": "FT_BE"}[mm.group(1)] + mm.group(2)
            ball_net[ball] = net
    # FT601 GPIO0/1 are wired but unused by the gateware; balls placed in FT601 pin order (notes/pinswap/)
    ball_net.update({"T14": "FT_GPIO0", "T15": "FT_GPIO1"})
    # config flash on bank 8 (balls from prjtrellis function names): CSN R8, MOSI/D0 T8, MISO/D1 T7, D2 M7, D3 N7
    ball_net.update({"R8": "FLASH_CS_N", "T8": "FLASH_IO0", "T7": "FLASH_IO1", "M7": "FLASH_IO2", "N7": "FLASH_IO3"})
    # two PMODs on banks 0/1, outer rings
    pmod = "A2 A3 A4 A5 B3 B4 B5 B6 A10 A11 A12 A13 B10 B11 B12 B13".split()
    for i, b in enumerate(pmod):
        ball_net[b] = f"PMOD{i // 8}_{i % 8}"
    # unit 5: supplies (bank VCCIO per notes/pinplan_power.md) and configuration (Lattice ECP5 Versa board,
    # FPGA-EB-02021 Fig. 12: 10k pull-ups on INITN/DONE, 50R series on CCLK at the FPGA, CFG straps via 1k;
    # CFG[2:0] = 010 = Master SPI; JTAG pins are powered from VCCIO8)
    import json, os
    nonio = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ecp5_bg256.json")))["nonio"]
    rail = {"VCC": "1V1", "VCCAUX": "2V5", "GND": "GND", "VCCIO0": "3V3_D", "VCCIO1": "3V3_D", "VCCIO2": "3V3_D",
            "VCCIO3": "3V3_D", "VCCIO6": "3V3_D", "VCCIO7": "1V8_D", "VCCIO8": "3V3_D",
            "CCLK": "CCLK_FPGA", "PROGRAMN": "FPGA_PROGRAM_N", "INITN": "FPGA_INIT_N", "DONE": "FPGA_DONE",
            "CFG_0": "FPGA_CFG0", "CFG_1": "FPGA_CFG1", "CFG_2": "FPGA_CFG2",
            "TCK": "FPGA_TCK", "TMS": "FPGA_TMS", "TDI": "FPGA_TDI", "TDO": "FPGA_TDO"}
    for ball, names in nonio.items():
        ball_net[ball] = rail[names[0]]
    s = []
    for unit, balls in enumerate(iodb_units, start=1):
        s.append(("U12", "usb3sdr:LFE5U-25F-6BG256C", "LFE5U-25F-6BG256C", None,
                  {b: ball_net.get(b, "") for b in balls}, unit))
    s += [("U10", "Memory_Flash:W25Q128JVS", "W25Q128JVSIQ", None,
           {"1": "FLASH_CS_N", "2": "FLASH_IO1", "3": "FLASH_IO2", "4": "GND", "5": "FLASH_IO0",
            "6": "FPGA_CCLK", "7": "FLASH_IO3", "8": "3V3_D"}, 1),
          R("CCLK_FPGA", "FPGA_CCLK", "50 (place at FPGA)"),
          R("FPGA_PROGRAM_N", "3V3_D", "10k"), R("FPGA_INIT_N", "3V3_D", "10k"), R("FPGA_DONE", "3V3_D", "10k"),
          R("FPGA_CFG0", "GND", "1k"), R("FPGA_CFG1", "3V3_D", "1k"), R("FPGA_CFG2", "GND", "1k"),
          R("FPGA_TCK", "GND", "4.7k"),
          *decouple("1V1", ["10u", "10u", "100n", "100n", "100n", "100n", "100n", "100n"]),
          *decouple("2V5", ["10u", "100n", "100n"]),
          *decouple("1V8_D", ["10u", "100n", "100n"]),
          *decouple("3V3_D", ["10u", "10u"] + ["100n"] * 11),
          R("FLASH_CS_N", "3V3_D", "4.7k"), R("FLASH_IO2", "3V3_D", "10k"), R("FLASH_IO3", "3V3_D", "10k"),
          C("3V3_D", "GND", "100n"),
          # JTAG on Tag-Connect TC2050 (project-defined mapping)
          ("J3", "Connector:TC2050", "TC2050 JTAG", None,
           {"1": "3V3_D", "2": "FPGA_TMS", "3": "GND", "4": "FPGA_TCK", "5": "GND", "6": "FPGA_TDO", "7": "",
            "8": "FPGA_TDI", "9": "GND", "10": "FPGA_PROGRAM_N"}, 1),
          # 10 MHz reference input: 50 R termination, AC coupled, biased to mid-rail, Schmitt buffer
          ("J4", "Connector:Conn_Coaxial", "SMA 10MHz REF", "Connector_Coaxial:SMA_Amphenol_132289_EdgeMount",
           {"1": "REF_IN", "2": "GND"}, 1),
          R("REF_IN", "GND", "49.9"), C("REF_IN", "REF_AC", "100n"), R("3V3_D", "REF_AC", "10k"), R("REF_AC", "GND", "10k"),
          ("U14", "74xGxx:74LVC1G17", "74LVC1G17", "Package_TO_SOT_SMD:SOT-23-5",
           {"1": "", "2": "REF_AC", "3": "GND", "4": "REF10M", "5": "3V3_D"}, 1),
          C("3V3_D", "GND", "100n"),
          ("J5", "Connector_Generic:Conn_02x06_Top_Bottom", "PMOD0", "Connector_PinHeader_2.54mm:PinHeader_2x06_P2.54mm_Horizontal",
           {"1": "PMOD0_0", "2": "PMOD0_1", "3": "PMOD0_2", "4": "PMOD0_3", "5": "GND", "6": "3V3_D",
            "7": "PMOD0_4", "8": "PMOD0_5", "9": "PMOD0_6", "10": "PMOD0_7", "11": "GND", "12": "3V3_D"}, 1),
          ("J6", "Connector_Generic:Conn_02x06_Top_Bottom", "PMOD1", "Connector_PinHeader_2.54mm:PinHeader_2x06_P2.54mm_Horizontal",
           {"1": "PMOD1_0", "2": "PMOD1_1", "3": "PMOD1_2", "4": "PMOD1_3", "5": "GND", "6": "3V3_D",
            "7": "PMOD1_4", "8": "PMOD1_5", "9": "PMOD1_6", "10": "PMOD1_7", "11": "GND", "12": "3V3_D"}, 1)]
    for i in (0, 1):
        led = _ref("D")
        s += [(led, "Device:LED", "LED green", "LED_SMD:LED_0603_1608Metric", {"2": f"LED{i}", "1": f"{led}_K"}, 1),
              R(f"{led}_K", "GND", "330")]
    return s
