#!/usr/bin/env python3
"""Place the U12 bus escape vias from a fan-out plan's "escape" hints: for each net with a via, a 0.45/0.2 via at the
hint and a straight F.Cu dog-bone from its ball. Nets that escape on F.Cu get nothing (the router starts at the ball).
usage: escape_apply.py plan.json board.kicad_pcb   (board edited in place)
"""
import json
import os
import sys

import pcbnew

T, MM = pcbnew.ToMM, pcbnew.FromMM
P = lambda x, y: pcbnew.VECTOR2I(MM(x), MM(y))


def main(plan_path, path):
    if not os.path.exists(os.path.splitext(path)[0] + ".kicad_pro"):
        sys.exit(f"{path}: no matching .kicad_pro next to it")
    esc = json.load(open(plan_path))["escape"]
    b = pcbnew.LoadBoard(path)
    balls = {q.GetNetname(): q for q in b.FindFootprintByReference("U12").Pads()}
    n = 0
    for net, e in esc.items():
        if not e.get("via"):
            continue
        q, ni = balls[net], b.FindNet(net)
        v = pcbnew.PCB_VIA(b); v.SetPosition(P(*e["via"])); v.SetWidth(MM(0.45)); v.SetDrill(MM(0.2))
        v.SetNet(ni); v.SetLocked(True); b.Add(v)
        t = pcbnew.PCB_TRACK(b); t.SetStart(q.GetPosition()); t.SetEnd(P(*e["via"])); t.SetWidth(MM(0.15))
        t.SetLayer(pcbnew.F_Cu); t.SetNet(ni); t.SetLocked(True); b.Add(t)
        n += 1
    b.Save(path)
    print(f"{n} escape vias")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
