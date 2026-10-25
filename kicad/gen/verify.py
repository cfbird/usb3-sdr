#!/usr/bin/env python3
"""Compare KiCad's exported netlist with the intended netlist from design.py (expected_nets.json).
Nets are compared as sets of REF.PIN, so naming differences (sheet paths) don't matter."""
import json, os, subprocess, sys
from sexp import parse, find, find1

HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.join(HERE, "..")
net_file = os.path.join(PRJ, "usb3-sdr.net")
subprocess.run(["kicad-cli", "sch", "export", "netlist", "--format", "kicadsexpr", "-o", net_file,
                os.path.join(PRJ, "usb3-sdr.kicad_sch")], check=True, capture_output=True)
nl = parse(open(net_file).read())
got = {}
for net in find(find1(nl, "nets"), "net"):
    pins = frozenset(f"{find1(n, 'ref')[1]}.{find1(n, 'pin')[1]}" for n in find(net, "node")
                     if not find1(n, "ref")[1].startswith("#"))
    if pins:
        got[pins] = find1(net, "name")[1]
exp = {frozenset(v): k for k, v in json.load(open(os.path.join(HERE, "expected_nets.json"))).items()}

# every expected net must appear exactly as one KiCad net
missing = [(name, sorted(p)) for p, name in exp.items() if p not in got]
# KiCad nets that are not expected (excluding single unconnected pins KiCad lists as their own nets)
extra = [(name, sorted(p)) for p, name in got.items() if p not in exp and len(p) > 1]
comps = {find1(c, "ref")[1] for c in find(find1(nl, "components"), "comp")}
print(f"KiCad netlist: {len(comps)} components, {len(got)} nets with pins; expected nets: {len(exp)}")
print(f"matched: {sum(1 for p in exp if p in got)}  missing/merged: {len(missing)}  unexpected: {len(extra)}")
for name, p in missing[:15]:
    print("  MISSING", name, p[:8])
for name, p in extra[:15]:
    print("  EXTRA  ", name, p[:8])
sys.exit(1 if missing or extra else 0)
