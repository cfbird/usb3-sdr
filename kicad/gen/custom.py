"""Project-specific symbols and footprints, built from datasheet pinouts (sources noted per part)."""
import json
from sexp import Q

PIN_LEN = 2.54


def _pin(num, name, x, y, ang, etype="passive", hidden=False):
    p = ["pin", etype, "line", ["at", x, y, ang], ["length", PIN_LEN]]
    if hidden:
        p.append("hide")
    p += [["name", Q(name), ["effects", ["font", ["size", 1.27, 1.27]]]],
          ["number", Q(str(num)), ["effects", ["font", ["size", 1.27, 1.27]]]]]
    return p


def _props(name, ref, value, fp, ds, desc):
    hid = lambda k, v, y: ["property", Q(k), Q(v), ["at", 0, y, 0], ["effects", ["font", ["size", 1.27, 1.27]], ["hide", "yes"]]]
    return [["property", Q("Reference"), Q(ref), ["at", 0, 2, 0], ["effects", ["font", ["size", 1.27, 1.27]]]],
            ["property", Q("Value"), Q(value), ["at", 0, -2, 0], ["effects", ["font", ["size", 1.27, 1.27]]]],
            hid("Footprint", fp, 0), hid("Datasheet", ds, 0), hid("Description", desc, 0)]


def box_symbol(name, ref, value, fp, ds, desc, left, right, top=(), bottom=(), units=None):
    """left/right/top/bottom: lists of (num, name, etype) or None for a gap. units: list of such dicts."""
    unit_defs = units or [dict(left=left, right=right, top=top, bottom=bottom)]
    sym = ["symbol", Q(name), ["exclude_from_sim", "no"], ["in_bom", "yes"], ["on_board", "yes"]]
    sym += _props(name, ref, value, fp, ds, desc)
    for ui, u in enumerate(unit_defs, start=1):
        L, R, T, B = u.get("left", []), u.get("right", []), u.get("top", []), u.get("bottom", [])
        rows = max(len(L), len(R), 1)
        cols = max(len(T), len(B), 0)
        w = max(15.24, (cols + 1) * 2.54, 2.54 * 2 * max([len(p[1]) for p in L + R if p] + [4]) * 0.32 + 5.08)
        w = round(w / 2.54) * 2.54
        h = (rows + 1) * 2.54
        x0, y0 = -w / 2, h / 2
        body = ["symbol", Q(f"{name}_{ui}_1"),
                ["rectangle", ["start", x0, y0], ["end", -x0, -y0], ["stroke", ["width", 0.254], ["type", "default"]],
                 ["fill", ["type", "background"]]]]
        for i, p in enumerate(L):
            if p: body.append(_pin(p[0], p[1], x0 - PIN_LEN, y0 - 2.54 * (i + 1), 0, p[2]))
        for i, p in enumerate(R):
            if p: body.append(_pin(p[0], p[1], -x0 + PIN_LEN, y0 - 2.54 * (i + 1), 180, p[2]))
        for i, p in enumerate(T):
            if p: body.append(_pin(p[0], p[1], x0 + 2.54 * (i + 1), y0 + PIN_LEN, 270, p[2]))
        for i, p in enumerate(B):
            if p: body.append(_pin(p[0], p[1], x0 + 2.54 * (i + 1), -y0 - PIN_LEN, 90, p[2]))
        sym.append(body)
    return sym


def pw(n, name): return (n, name, "power_in")
def io(n, name): return (n, name, "bidirectional")
def inp(n, name): return (n, name, "input")
def out(n, name): return (n, name, "output")
def pas(n, name): return (n, name, "passive")


def ad9649():
    # AD9649 Rev B Table 8 (pin 0 = EPAD, the only ground). Package CP-32-11, EP 3.50 sq.
    return box_symbol("AD9649BCPZ-80", "U", "AD9649BCPZ-80",
                      "Package_CSP:LFCSP-32-1EP_5x5mm_P0.5mm_EP3.5x3.5mm_ThermalVias",
                      "https://www.analog.com/media/en/technical-documentation/data-sheets/AD9649.pdf",
                      "14-bit 80 MSPS 1.8 V ADC, parallel CMOS outputs",
                      left=[inp(31, "VIN+"), inp(30, "VIN-"), None, pas(27, "VCM"), pas(25, "VREF"), inp(26, "SENSE"),
                            pas(28, "RBIAS"), None, inp(1, "CLK+"), inp(2, "CLK-"), None, inp(4, "~{CSB}"),
                            inp(5, "SCLK/DFS"), io(6, "SDIO/PDWN")],
                      right=[out(7, "D0"), out(8, "D1"), out(9, "D2"), out(10, "D3"), out(11, "D4"), out(12, "D5"),
                             out(14, "D6"), out(15, "D7"), out(16, "D8"), out(17, "D9"), out(18, "D10"), out(19, "D11"),
                             out(20, "D12"), out(21, "D13"), None, out(22, "DCO"), io(23, "MODE/OR")],
                      top=[pw(3, "AVDD"), pw(24, "AVDD"), pw(29, "AVDD"), pw(32, "AVDD"), None, pw(13, "DRVDD")],
                      bottom=[pw(33, "EPAD")])


def lmk61e2():
    # SNAS674C pin table: 1 OE, 2 ADD, 3 GND, 4 OUTP, 5 OUTN, 6 VDD, 7 SDA, 8 SCL. Package SIA0008B.
    return box_symbol("LMK61E2-SIA", "U", "LMK61E2-100M00SIAR", "usb3sdr:TI_SIA0008B_QFM-8_7x5mm",
                      "https://www.ti.com/lit/ds/symlink/lmk61e2.pdf",
                      "Programmable oscillator, I2C, 90 fs RMS jitter",
                      left=[inp(1, "OE"), inp(2, "ADD"), None, io(7, "SDA"), inp(8, "SCL")],
                      right=[out(4, "OUTP"), out(5, "OUTN")],
                      top=[pw(6, "VDD")], bottom=[pw(3, "GND")])


def adt4_6t():
    # Mini-Circuits ADT4-6T+ datasheet: primary dot 3, primary 1, secondary dot 4, secondary 6, CT 5, NC 2.
    return box_symbol("ADT4-6T", "T", "ADT4-6T+", "RF_Mini-Circuits:Mini-Circuits_CD637_H5.23mm",
                      "https://www.minicircuits.com/pdfs/ADT4-6T+.pdf",
                      "1:4 RF transformer with secondary centre tap, 0.06-300 MHz",
                      left=[pas(3, "PRI_DOT"), None, pas(1, "PRI"), None, pas(2, "NC")],
                      right=[pas(4, "SEC_DOT"), None, pas(5, "CT"), None, pas(6, "SEC")])


def tps7a20_dbv(value):
    # TPS7A20 datasheet pin functions, DBV: 1 IN, 2 GND, 3 EN, 4 NC, 5 OUT (same as TLV755P DBV)
    return box_symbol(f"{value}", "U", value, "Package_TO_SOT_SMD:SOT-23-5",
                      "https://www.ti.com/lit/ds/symlink/tps7a20.pdf", "300 mA low-noise LDO, SOT-23-5",
                      left=[(1, "IN", "power_in"), None, inp(3, "EN")], right=[(5, "OUT", "power_out"), None, ("4", "NC", "no_connect")],
                      bottom=[None, pw(2, "GND")])


# ---------------------------------------------------------------- ECP5 LFE5U-25F/45F-6BG256
def ecp5_units(csv_json):
    """LFE5U-25F/45F-6BG256 from Lattice FPGA-SC-02033 (ECP5U-25 pinout CSV, CABGA256 column), already
    cross-checked against prjtrellis-db (same 197 I/O balls, banks and clock functions).
    Units 1-4: I/O by bank (0+1, 2+3, 6+7, 8); unit 5: power, ground, configuration and JTAG."""
    d = json.load(open(csv_json))
    order = lambda b: ("ABCDEFGHJKLMNPRT".index(b[0]), int(b[1:]))
    banks = {}
    for ball, (name, bank, dual) in d["io"].items():
        banks.setdefault(int(bank), []).append((ball, name + ("/" + dual if dual not in ("-", "") else "")))
    units = []
    for group in ((0, 1), (2, 3), (6, 7), (8,)):
        pins = []
        for b in group:
            pins += [io(ball, f"B{b}:{nm}") for ball, nm in sorted(banks[b], key=lambda x: order(x[0]))]
        half = (len(pins) + 1) // 2
        units.append(dict(left=pins[:half], right=pins[half:]))
    etype = {"CCLK": "bidirectional", "PROGRAMN": "input", "INITN": "open_collector", "DONE": "open_collector",
             "CFG_0": "input", "CFG_1": "input", "CFG_2": "input", "TCK": "input", "TMS": "input", "TDI": "input",
             "TDO": "output"}
    cfg, pwr, gnd = [], [], []
    for ball, names in sorted(d["nonio"].items(), key=lambda x: (x[1][0], order(x[0]))):
        f = names[0]
        if f in etype:
            cfg.append((ball, f, etype[f]))
        elif f == "GND":
            gnd.append((ball, f, "power_in"))
        else:
            pwr.append((ball, f, "power_in"))
    units.append(dict(left=pwr + [None] + cfg, right=gnd))
    return box_symbol("LFE5U-25F-6BG256C", "U", "LFE5U-25F-6BG256C",
                      "Package_BGA:BGA-256_14.0x14.0mm_Layout16x16_P0.8mm_Ball0.45mm_Pad0.32mm_NSMD",
                      "https://www.latticesemi.com/Products/FPGAandCPLD/ECP5",
                      "ECP5 FPGA 24k LUT, caBGA-256 (LFE5U-45F is ball compatible)",
                      None, None, units=units)


# ---------------------------------------------------------------- footprints
def _fp_pad(num, x, y, w, h, shape="roundrect"):
    return f'\t(pad "{num}" smd {shape} (at {x:.4f} {y:.4f}) (size {w} {h}) (layers "F.Cu" "F.Paste" "F.Mask")' \
           + (' (roundrect_rratio 0.1)' if shape == "roundrect" else "") + ")\n"


def _fp(name, desc, pads, body_w, body_h, ref_y):
    s = f'(footprint "{name}"\n\t(version 20241229)\n\t(generator "usb3sdr-gen")\n\t(layer "F.Cu")\n\t(descr "{desc}")\n\t(attr smd)\n'
    s += f'\t(property "Reference" "REF**" (at 0 {ref_y}) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))\n'
    s += f'\t(property "Value" "{name}" (at 0 {-ref_y}) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))\n'
    hx, hy = body_w / 2, body_h / 2
    for (x1, y1, x2, y2) in ((-hx, -hy, hx, -hy), (hx, -hy, hx, hy), (hx, hy, -hx, hy), (-hx, hy, -hx, -hy)):
        s += f'\t(fp_line (start {x1} {y1}) (end {x2} {y2}) (stroke (width 0.1) (type solid)) (layer "F.Fab"))\n'
    cx, cy = hx + 0.25, hy + 0.25
    s += f'\t(fp_rect (start {-cx} {-cy}) (end {cx} {cy}) (stroke (width 0.05) (type solid)) (fill no) (layer "F.CrtYd"))\n'
    s += "".join(pads) + ")\n"
    return s


def fp_hfd4_sr():
    # Hongfa HFD4 SMT (J-legs) land pattern, datasheet p.5 bottom view: pads 0.8 x 1.8, pin pitch 3.2/2.2/2.2,
    # rows 2.4 mm apart (inner) / 6.0 mm (outer) -> row centres +/-2.1. Top view = mirror of the bottom view.
    xs = {1: 3.8, 2: 0.6, 3: -1.6, 4: -3.8}
    pads = [_fp_pad(n, xs[n], -2.1, 0.8, 1.8) for n in (1, 2, 3, 4)]
    pads += [_fp_pad(9 - n, xs[n], 2.1, 0.8, 1.8) for n in (1, 2, 3, 4)]
    return _fp("Relay_DPDT_Hongfa_HFD4-SR", "Hongfa HFD4 SMT signal relay (pin-compatible with Omron G6K-2F-Y wiring; "
               "rows at +/-2.1 mm, NOT the G6K-2F-Y +/-3.5 mm)", pads, 10.0, 6.5, -4.3)


def fp_ti_sia0008b():
    # TI SIA0008B example board layout (LMK61E2 datasheet p.55): 6x 1.0 x 1.4 pads at x +/-1.85, y -2.54/0/+2.54;
    # pins 7/8 0.8 x 0.8 on the centreline at y -/+2.865.
    pads = [_fp_pad(1, -1.85, -2.54, 1.0, 1.4), _fp_pad(2, -1.85, 0, 1.0, 1.4), _fp_pad(3, -1.85, 2.54, 1.0, 1.4),
            _fp_pad(4, 1.85, 2.54, 1.0, 1.4), _fp_pad(5, 1.85, 0, 1.0, 1.4), _fp_pad(6, 1.85, -2.54, 1.0, 1.4),
            _fp_pad(7, 0, -2.865, 0.8, 0.8), _fp_pad(8, 0, 2.865, 0.8, 0.8)]
    return _fp("TI_SIA0008B_QFM-8_7x5mm", "TI SIA0008B QFM-8 7.0x5.0 mm (LMK61E2)", pads, 5.0, 7.0, -4.6)
