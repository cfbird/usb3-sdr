#!/usr/bin/env python3
"""Claude's independent check of AGY's bus ball assignment (does not import AGY's code or data.json).

Sources: kicad/usb3-sdr.net (connectivity), kicad/work/usb3-sdr.kicad_pcb (pad positions), refs/data/ecp5_bg256.json
(Lattice bank / special functions), gateware/constraints/usb3sdr.lpf (current signal -> ball).
usage (repo root): python3 notes/pinswap/claude_verify.py FT.json ADC.json
"""
import itertools
import json
import re
import sys

sys.path.insert(0, "kicad/gen")
import pcbnew                      # noqa: E402
from sexp import parse, find, find1  # noqa: E402

T = pcbnew.ToMM
nl = parse(open("kicad/usb3-sdr.net").read())
nodes, net_of = {}, {}
for net in find(find1(nl, "nets"), "net"):
    name = find1(net, "name")[1]
    nodes[name] = [(find1(n, "ref")[1], find1(n, "pin")[1]) for n in find(net, "node")]
    for r, p in nodes[name]:
        net_of[(r, p)] = name
b = pcbnew.LoadBoard("kicad/work/usb3-sdr.kicad_pcb")
pos = {(p.GetParentFootprint().GetReference(), p.GetNumber()): (T(p.GetPosition().x), T(p.GetPosition().y)) for p in b.GetPads()}
io = json.load(open("refs/data/ecp5_bg256.json"))["io"]
lpf = {}
for line in open("gateware/constraints/usb3sdr.lpf"):
    m = re.match(r'LOCATE COMP "([^"]+)" SITE "([^"]+)"', line)
    if m:
        lpf[m.group(1)] = m.group(2)
lpf["FT_GPIO0"], lpf["FT_GPIO1"] = "P13", "P14"          # wired on the board, not used by the gateware


def endpoint(sig):
    """The non-FPGA pad that the signal's ball connects to today (U11 pin, U8 pin or series-resistor pad)."""
    ball = lpf[sig]
    others = [(r, p) for r, p in nodes[net_of[("U12", ball)]] if r != "U12"]
    assert len(others) == 1, (sig, ball, others)
    return others[0], net_of[("U12", ball)]


def cross(s, t):
    o = lambda a, c, d: (c[0] - a[0]) * (d[1] - a[1]) - (c[1] - a[1]) * (d[0] - a[0])
    (a, c), (d, e) = s, t
    return o(a, c, d) * o(a, c, e) < 0 and o(d, e, a) * o(d, e, c) < 0


def check(name, assign, banks, clk_sig, clk_sites):
    ok = True
    sigs = sorted(assign)
    if len(set(assign.values())) != len(assign):
        print(f"  FAIL {name}: duplicate balls"); ok = False
    bus_nets = {endpoint(s)[1] for s in sigs}
    for s, ball in assign.items():
        if ball not in io or io[ball][1] not in banks:
            print(f"  FAIL {s} -> {ball}: bank {io.get(ball, ['', '?'])[1]} not in {banks}"); ok = False
        cur = net_of.get(("U12", ball), "")
        if cur and not cur.startswith("unconnected-") and cur not in bus_nets:
            print(f"  FAIL {s} -> {ball}: ball already carries {cur}"); ok = False
    if assign[clk_sig] not in clk_sites:
        print(f"  FAIL {clk_sig} on {assign[clk_sig]} ({io[assign[clk_sig]][2]}), need one of {clk_sites}"); ok = False
    seg = lambda A: {s: (pos[endpoint(s)[0]], pos[("U12", A[s])]) for s in sigs}
    before = seg({s: lpf[s] for s in sigs})
    after = seg(assign)
    n0 = sum(cross(before[a], before[c]) for a, c in itertools.combinations(sigs, 2))
    n1 = sum(cross(after[a], after[c]) for a, c in itertools.combinations(sigs, 2))
    n1_noclk = sum(cross(after[a], after[c]) for a, c in itertools.combinations([s for s in sigs if s != clk_sig], 2))
    L = lambda S: sum(((x0 - x1) ** 2 + (y0 - y1) ** 2) ** .5 for (x0, y0), (x1, y1) in S.values())
    print(f"  {name}: {len(sigs)} signals, constraints {'PASS' if ok else 'FAIL'}; crossings {n0} -> {n1} "
          f"({n1_noclk} without {clk_sig}); straight-line length {L(before):.1f} -> {L(after):.1f} mm")
    return ok


ft = {k: v for k, v in json.load(open(sys.argv[1])).items() if k.startswith(("ft_", "FT_"))}
adc = {k: v for k, v in json.load(open(sys.argv[2])).items() if k.startswith("adc_")}
check("FT601 bus", ft, {"2", "3"}, "ft_clk", {"J16", "K16", "L16", "M16"})
check("ADC bus", adc, {"7"}, "adc_dco", {"J1", "K1"})
for s in ("ft_clk", "adc_dco"):
    print(f"  {s}: {(ft | adc)[s]} = {io[(ft | adc)[s]][2]}")
print("  ADC_OR endpoint used:", endpoint("adc_or")[0])
