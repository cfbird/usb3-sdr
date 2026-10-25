#!/usr/bin/env python3
"""Add rule-area keep-outs (no tracks, no vias; zones and pads allowed) in a strip along the board edge.

DeepPCB run 3 ran tracks 0.34 mm from the edge although the board's copper-to-edge rule is 0.5 mm. A keep-out it
must respect closes that off. Idempotent: strips named EDGE_KEEPOUT are replaced.
usage: edge_keepout.py board.kicad_pcb [width_mm]   (edited in place; default 0.6 mm)
"""
import os
import sys

import pcbnew

MM = pcbnew.FromMM
NAME = "EDGE_KEEPOUT"


def main(path, w=0.6):
    if not os.path.exists(os.path.splitext(path)[0] + ".kicad_pro"):
        sys.exit(f"{path}: no matching .kicad_pro next to it")
    b = pcbnew.LoadBoard(path)
    for z in [z for z in b.Zones() if z.GetIsRuleArea() and z.GetZoneName() == NAME]:
        b.Remove(z)
    bb = b.GetBoardEdgesBoundingBox()
    x0, y0, x1, y1 = bb.GetX(), bb.GetY(), bb.GetRight(), bb.GetBottom()
    d = MM(w)
    strips = [(x0, y0, x1, y0 + d), (x0, y1 - d, x1, y1), (x0, y0, x0 + d, y1), (x1 - d, y0, x1, y1)]
    ls = pcbnew.LSET(); ls.AddLayer(pcbnew.F_Cu); ls.AddLayer(pcbnew.B_Cu)
    for a, c, e, f in strips:
        z = pcbnew.ZONE(b)
        z.SetIsRuleArea(True); z.SetZoneName(NAME); z.SetLayerSet(ls)
        z.SetDoNotAllowTracks(True); z.SetDoNotAllowVias(True)
        z.SetDoNotAllowPads(False); z.SetDoNotAllowFootprints(False); z.SetDoNotAllowCopperPour(False)
        o = z.Outline(); o.NewOutline()
        for x, y in ((a, c), (e, c), (e, f), (a, f)):
            o.Append(x, y)
        b.Add(z)
    b.Save(path)
    print(f"{len(strips)} edge keep-out strips, {w} mm")


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 0.6)
