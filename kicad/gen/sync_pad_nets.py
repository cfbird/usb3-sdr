#!/usr/bin/env python3
"""Push pad-net changes from the netlist onto a placed/routed board without regenerating it (a scripted
"update PCB from schematic" for the case where only pin assignments changed, e.g. an FPGA ball swap).

For every pad whose net differs from the netlist: the unlocked copper on both the old and the new net is ripped up
(it was routed for the old pin map), then the pad is moved to the new net. Locked copper on those nets is reported
and left alone. Components must match the netlist exactly.
usage: sync_pad_nets.py board.kicad_pcb netlist.net   (board edited in place)
"""
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from repair_conflicts import dangling, delete_by_uuid, refill  # noqa: E402
from sexp import parse, find, find1                             # noqa: E402


def main(path, net_path):
    if not os.path.exists(os.path.splitext(path)[0] + ".kicad_pro"):
        sys.exit(f"{path}: no matching .kicad_pro next to it")
    nl = parse(open(net_path).read())
    want = {}
    for net in find(find1(nl, "nets"), "net"):
        for n in find(net, "node"):
            want[(find1(n, "ref")[1], find1(n, "pin")[1])] = find1(net, "name")[1]
    b = pcbnew.LoadBoard(path)
    changes = {}
    for p in b.GetPads():
        k = (p.GetParentFootprint().GetReference(), p.GetNumber())
        if k in want and p.GetNetname() != want[k]:
            changes[k] = (p.GetNetname(), want[k])
    touched = {n for pair in changes.values() for n in pair if n}
    rip = {t.m_Uuid.AsString() for t in b.GetTracks() if t.GetNetname() in touched and not t.IsLocked()}
    kept = sorted({t.GetNetname() for t in b.GetTracks() if t.GetNetname() in touched and t.IsLocked()})
    print(f"{len(changes)} pads change net; {len(touched)} nets touched; ripping {len(rip)} unlocked items")
    if kept:
        print("  locked copper left on:", kept)
    del b
    delete_by_uuid(path, rip)
    while True:
        dead = dangling(path)
        if not dead:
            break
        delete_by_uuid(path, dead)

    b = pcbnew.LoadBoard(path)
    for p in b.GetPads():
        k = (p.GetParentFootprint().GetReference(), p.GetNumber())
        if k in changes:
            name = changes[k][1]
            net = b.FindNet(name)
            if net is None:
                net = pcbnew.NETINFO_ITEM(b, name)
                b.Add(net)
            p.SetNet(net)
    b.Save(path)
    refill(path)


if __name__ == "__main__":
    main(*sys.argv[1:3])
