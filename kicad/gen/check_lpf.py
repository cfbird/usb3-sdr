#!/usr/bin/env python3
"""End-to-end check, independent of design.py: for every LOCATE in the gateware LPF, follow the KiCad net from
that FPGA ball (through at most one series resistor) and confirm it lands on the pin whose *datasheet name*
matches the gateware signal."""
import os, re, sys
from sexp import parse, find, find1

HERE = os.path.dirname(os.path.abspath(__file__))
nl = parse(open(os.path.join(HERE, "..", "usb3-sdr.net")).read())
net_of, nodes = {}, {}
for net in find(find1(nl, "nets"), "net"):
    name = find1(net, "name")[1]
    nodes[name] = [(find1(n, "ref")[1], find1(n, "pin")[1], (find1(n, "pinfunction") or [0, ""])[1]) for n in find(net, "node")]
    for r, p, f in nodes[name]:
        net_of[(r, p)] = name

def far_ends(ball):
    """(ref, pinfunction) reachable from FPGA ball directly or through one 2-pin resistor."""
    out = []
    for r, p, f in nodes[net_of[("U12", ball)]]:
        if r == "U12":
            continue
        out.append((r, f))
        if r.startswith("R"):
            other = net_of.get((r, "2" if p == "1" else "1"))
            out += [(r2, f2) for r2, p2, f2 in nodes.get(other, []) if r2 != r]
    return out

want = {  # gateware signal -> (ref, datasheet pin name)
    "adc_dco": ("U8", "DCO"), "adc_or": ("U8", "MODE/OR"), "adc_sclk": ("U8", "SCLK/DFS"), "adc_sdio": ("U8", "SDIO/PDWN"),
    "adc_csb": ("U8", "~{CSB}"), "ft_clk": ("U11", "CLK"), "ft_txe_n": ("U11", "~{TXE}"), "ft_rxf_n": ("U11", "~{RXF}"),
    "ft_wr_n": ("U11", "~{WR}"), "ft_rd_n": ("U11", "~{RD}"), "ft_oe_n": ("U11", "~{OE}"), "ft_reset_n": ("U11", "~{RESET}"),
    "ft_wakeup_n": ("U11", "~{WAKEUP}"), "lmk_scl": ("U9", "SCL"), "lmk_sda": ("U9", "SDA"), 
    "rly_pad": ("Q1", "G"), "rly_lna": ("Q2", "G"), "lna_en": ("Q11", "G")}
ok = bad = 0
for line in open(os.path.join(HERE, "../../gateware/constraints/usb3sdr.lpf")):
    m = re.match(r'LOCATE COMP "([^"]+)" SITE "([^"]+)"', line)
    if not m:
        continue
    sig, ball = m.group(1).replace("[", "").replace("]", ""), m.group(2)
    mm = re.match(r"(adc_d|ft_data|ft_be)(\d+)$", sig)
    if mm:
        w = {"adc_d": ("U8", f"D{mm.group(2)}"), "ft_data": ("U11", f"DATA_{mm.group(2)}"), "ft_be": ("U11", f"BE_{mm.group(2)}")}[mm.group(1)]
    elif sig.startswith("led"):
        w = None
    elif sig == "ref10m":   # 74LVC1G17 output pins are unnamed in the KiCad symbol: check pin 4 (Y) by number
        n = net_of[("U12", ball)]
        ok, bad = (ok + 1, bad) if ("U14", "4") in [(r, p) for r, p, f in nodes[n]] else (ok, bad + 1)
        continue
    else:
        w = want[sig]
    ends = far_ends(ball)
    if w is None or w in ends:
        ok += 1
    else:
        bad += 1
        print(f"  MISMATCH {sig} @ {ball}: expected {w}, reaches {ends}")
print(f"LPF signals checked end-to-end: {ok} ok, {bad} mismatched")
sys.exit(1 if bad else 0)
