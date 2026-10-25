#!/usr/bin/env python3
"""Move parts per a plan's "moves" and rip the copper that the moves invalidate.

Rips unlocked copper with an end on a moved part's pad, plus all unlocked copper of the nets matching --rip (a
regex; e.g. the whole ADC bus, so it is re-routed from the new positions instead of patched), strips what that
leaves dangling, then rips unlocked copper that conflicts with the moved parts (repair_conflicts.py).
usage: apply_moves.py plan.json board.kicad_pcb [--rip REGEX]   (board edited in place)
"""
import json
import os
import re
import subprocess
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from repair_conflicts import dangling, delete_by_uuid  # noqa: E402

MM = pcbnew.FromMM


def main(plan_path, path, rip=None):
    if not os.path.exists(os.path.splitext(path)[0] + ".kicad_pro"):
        sys.exit(f"{path}: no matching .kicad_pro next to it")
    moves = json.load(open(plan_path))["moves"]
    b = pcbnew.LoadBoard(path)
    pads = [q for r in moves for q in b.FindFootprintByReference(r).Pads()]
    dead = set()
    for t in b.GetTracks():
        if t.IsLocked():
            continue
        ends = [t.GetPosition()] if t.Type() == pcbnew.PCB_VIA_T else [t.GetStart(), t.GetEnd()]
        if (rip and re.search(rip, t.GetNetname())) or any(q.HitTest(e) for q in pads for e in ends):
            dead.add(t.m_Uuid.AsString())
    del b
    n = delete_by_uuid(path, dead)
    while True:
        d = dangling(path)
        if not d:
            break
        n += delete_by_uuid(path, d)
    b = pcbnew.LoadBoard(path)
    for ref, m in moves.items():
        f = b.FindFootprintByReference(ref)
        f.SetOrientationDegrees(m["rot"]); f.SetPosition(pcbnew.VECTOR2I(MM(m["xy"][0]), MM(m["xy"][1])))
        f.SetLocked(True)
    b.Save(path)
    print(f"ripped {n} items, moved {len(moves)} parts")
    subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "repair_conflicts.py"),
                    path], check=True, capture_output=True)


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[1], a[a.index("--rip") + 1] if "--rip" in a else None)
