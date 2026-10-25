#!/usr/bin/env python3
"""Connect the FPGA's two VCCAUX (2V5) balls, G11 and L7, which the autorouter left without fan-out.

G11 sits inside a ring of other nets' fan-out vias, with no free via site. Its neighbours G10 and H10 are both GND
and each has its own dog-bone via; G10 is tied straight across to H10 (same net, 0.8 mm) so they share H10's via, and
G10's old via site goes to G11. Both balls are then routed to the 2V5 net with grid_route.py. The bank-2 area east of
column 11 is kept free for the FT601 bus re-plan.
usage: vccaux_patch.py board.kicad_pcb   (edited in place)
"""
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from grid_route import route                                   # noqa: E402
from repair_conflicts import delete_by_uuid, refill            # noqa: E402

T, MM = pcbnew.ToMM, pcbnew.FromMM
BOX = (152.0, 114.0, 176.0, 140.0)
KEEP = [(165.4, 117.0, 171.5, 126.6)]          # bank-2 escape area east of column 11 (FT601 bus)


def main(path):
    if not os.path.exists(os.path.splitext(path)[0] + ".kicad_pro"):
        sys.exit(f"{path}: no matching .kicad_pro next to it")
    b = pcbnew.LoadBoard(path)
    balls = {p.GetNumber(): p for p in b.FindFootprintByReference("U12").Pads()}
    g10, h10 = balls["G10"], balls["H10"]
    assert g10.GetNetname() == h10.GetNetname() == "GND"
    # G10's dog-bone (ball -> two short F.Cu segments -> via at the up-left interstitial site): every unlocked GND
    # item lying wholly inside the small box between G10 and that site; H10's dog-bone sits 0.8 mm lower, outside it
    gx, gy = T(g10.GetPosition().x), T(g10.GetPosition().y)
    box = (gx - 0.1, gy - 0.65, gx + 0.65, gy + 0.15)
    inside = lambda p: box[0] < T(p.x) < box[2] and box[1] < T(p.y) < box[3]
    dead = {t.m_Uuid.AsString() for t in b.GetTracks() if t.GetNetname() == "GND" and not t.IsLocked() and
            all(inside(p) for p in ([t.GetPosition()] if t.Type() == pcbnew.PCB_VIA_T else [t.GetStart(), t.GetEnd()]))}
    del b
    print(f"removed G10 dog-bone: {delete_by_uuid(path, dead)} items")

    b = pcbnew.LoadBoard(path)
    balls = {p.GetNumber(): p for p in b.FindFootprintByReference("U12").Pads()}
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(balls["G10"].GetPosition()); t.SetEnd(balls["H10"].GetPosition()); t.SetWidth(MM(0.2))
    t.SetLayer(pcbnew.F_Cu); t.SetNet(b.FindNet("GND")); t.SetLocked(True); b.Add(t)   # G10 shares H10's via
    for pad in ("U12-G11", "U12-L7"):
        r = route(b, "2V5", pad, "net", 0.15, 0.16, BOX, keepout=KEEP)
        if r is None:
            sys.exit(f"no path for {pad}")
        print(f"{pad}: {r[0]} tracks, {r[1]} vias")
    b.Save(path)
    refill(path)


if __name__ == "__main__":
    main(sys.argv[1])
