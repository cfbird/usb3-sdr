#!/usr/bin/env python3
"""Dump everything needed to re-plan the FT601 and ADC bus ball assignment into data.json (run from repo root)."""
import json, re, sys
sys.path.insert(0, "kicad/gen")
import pcbnew
from sexp import parse, find, find1

T = pcbnew.ToMM
b = pcbnew.LoadBoard("kicad/deeppcb/r2_deeppcb_routed.kicad_pcb")
nl = parse(open("kicad/usb3-sdr.net").read())
pinfn = {}
for net in find(find1(nl, "nets"), "net"):
    for n in find(net, "node"):
        pinfn[(find1(n, "ref")[1], find1(n, "pin")[1])] = (find1(n, "pinfunction") or [0, ""])[1]
io = json.load(open("refs/data/ecp5_bg256.json"))["io"]
lpf = {}
for line in open("gateware/constraints/usb3sdr.lpf"):
    m = re.match(r'LOCATE COMP "([^"]+)" SITE "([^"]+)"', line)
    if m:
        lpf[m.group(2)] = m.group(1)
pads = {(p.GetParentFootprint().GetReference(), p.GetNumber()): p for p in b.GetPads()}
xy = lambda p: [round(T(p.GetPosition().x), 3), round(T(p.GetPosition().y), 3)]
ROWS = "ABCDEFGHJKLMNPRT"
balls = {}
for (ref, num), p in pads.items():
    if ref != "U12":
        continue
    r, c = ROWS.index(num[0]), int(num[1:]) - 1
    balls[num] = {"xy": xy(p), "ring": min(r, 15 - r, c, 15 - c), "net": p.GetNetname(),
                  "bank": io[num][1] if num in io else None, "pio": io[num][0] if num in io else None,
                  "special": io[num][2] if num in io and io[num][2] != "-" else "",
                  "gateware_signal": lpf.get(num, "")}
ft = {}
for (ref, num), p in pads.items():
    if ref == "U11":
        ft[num] = {"xy": xy(p), "net": p.GetNetname(), "datasheet_name": pinfn.get(("U11", num), "")}
adc = {}
for (ref, num), p in pads.items():
    if ref == "U8":
        adc[num] = {"xy": xy(p), "net": p.GetNetname(), "datasheet_name": pinfn.get(("U8", num), "")}
series = {}
for ref in [f"R{i}" for i in range(26, 42)]:      # R26..R41 (R41 = ADC_OR)
    series[ref] = {n: {"xy": xy(pads[(ref, n)]), "net": pads[(ref, n)].GetNetname()} for n in ("1", "2")}
fp = lambda r: (lambda f: {"center": [T(f.GetPosition().x), T(f.GetPosition().y)], "rot": f.GetOrientationDegrees()})(b.FindFootprintByReference(r))
json.dump({"units": "mm, KiCad board coordinates (y grows downward)",
           "parts": {"U12_FPGA_LFE5U25_CABGA256_0p8mm": fp("U12"), "U11_FT601Q_QFN76": fp("U11"), "U8_AD9649_LFCSP32": fp("U8")},
           "fpga_balls": balls, "ft601_pins": ft, "adc_pins": adc, "adc_series_resistors": series,
           "bank_vccio": {"0": 3.3, "1": 3.3, "2": 3.3, "3": 3.3, "6": 3.3, "7": 1.8, "8": 3.3}},
          open("notes/pinswap/data.json", "w"), indent=1)
print("balls", len(balls), "ft601 pins", len(ft), "adc pins", len(adc))
