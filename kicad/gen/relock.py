#!/usr/bin/env python3
"""Re-apply lock flags from a reference board: every track/via locked in the reference is locked again on the target
where an item with the same net, type, layer, width and coordinates (within 2 um) exists. External routers
(DeepPCB) return boards with all locks cleared; this restores them without touching geometry.
usage: relock.py reference.kicad_pcb target.kicad_pcb   (target edited in place)
"""
import os
import sys

import pcbnew

T = pcbnew.ToMM


def key(t):
    r = lambda v: round(T(v) / 0.002)
    if t.Type() == pcbnew.PCB_VIA_T:
        return ("v", t.GetNetname(), r(t.GetPosition().x), r(t.GetPosition().y))
    a, b = sorted([(r(t.GetStart().x), r(t.GetStart().y)), (r(t.GetEnd().x), r(t.GetEnd().y))])
    return ("t", t.GetNetname(), t.GetLayer(), r(t.GetWidth()), a, b)


def main(ref, tgt):
    if not os.path.exists(os.path.splitext(tgt)[0] + ".kicad_pro"):
        sys.exit(f"{tgt}: no matching .kicad_pro next to it")
    want = {key(t) for t in pcbnew.LoadBoard(ref).GetTracks() if t.IsLocked()}
    b = pcbnew.LoadBoard(tgt)
    hit = 0
    for t in b.GetTracks():
        if key(t) in want and not t.IsLocked():
            t.SetLocked(True); hit += 1
    found = {key(t) for t in b.GetTracks()}
    print(f"re-locked {hit}; reference locked items not found on target: {len(want - found)}")
    b.Save(tgt)


if __name__ == "__main__":
    main(*sys.argv[1:3])
