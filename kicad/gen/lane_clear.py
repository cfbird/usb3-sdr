#!/usr/bin/env python3
"""Clear the FT601 approach lanes of a fan-out plan ("keepout_lanes") before a routing pass.

Rips unlocked copper inside each lane that does not belong to the FT601 bus (decap stubs and rails an autorouter
threaded through), plus every unlocked segment of the bus nets listed in REROUTE (detours worth redoing), strips what
that leaves dangling, then re-routes the ripped non-bus nets with grid_route under keepouts: the lanes' west
entrances and the top pocket are closed to them (the strip right under the U11 top-row decaps stays open, the decap
stubs have to cross it). Re-routed copper is locked, so the next autorouter pass leaves it alone.
usage: lane_clear.py plan.json board.kicad_pcb   (board edited in place)
"""
import json
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from grid_route import connect_net                             # noqa: E402
from repair_conflicts import dangling, delete_by_uuid, refill  # noqa: E402

MM = pcbnew.FromMM
REROUTE = ("FT_D25",)
# keepout rectangles for the re-routed non-bus nets (from the v3 lane outlines, minus the decap-stub strip)
KEEP = [(174.5, 115.4, 182.2, 118.1), (185.4, 115.4, 186.85, 118.1),       # top lane: west entrance, pocket
        (174.5, 127.9, 185.3, 128.5), (174.5, 128.5, 179.65, 130.8)]       # bottom lane
BOX = (168.0, 110.0, 195.0, 138.0)
WIDTH = {"GND": 0.2, "3V3_D": 0.2, "1V1": 0.25, "/USB 3 bridge/FT_1V0": 0.2}


def main(plan_path, path):
    if not os.path.exists(os.path.splitext(path)[0] + ".kicad_pro"):
        sys.exit(f"{path}: no matching .kicad_pro next to it")
    lanes = json.load(open(plan_path)).get("keepout_lanes", [])
    b = pcbnew.LoadBoard(path)
    polys = []
    for lane in lanes:
        s = pcbnew.SHAPE_POLY_SET(); s.NewOutline()
        for x, y in lane["outline"]:
            s.Append(MM(x), MM(y))
        polys.append(s)
    dead, nets = set(), set()
    for t in b.GetTracks():
        if t.IsLocked():
            continue
        n = t.GetNetname()
        if n in REROUTE:
            dead.add(t.m_Uuid.AsString()); continue
        if n.startswith("FT_"):
            continue
        pts = [t.GetPosition()] if t.Type() == pcbnew.PCB_VIA_T else [t.GetStart(), t.GetEnd(), (t.GetStart() + t.GetEnd()) / 2]
        if any(s.Contains(q) for s in polys for q in pts):
            dead.add(t.m_Uuid.AsString()); nets.add(n)
    del b
    k = delete_by_uuid(path, dead)
    while True:
        d = dangling(path)
        if not d:
            break
        k += delete_by_uuid(path, d)
    print(f"ripped {k} items; re-routing {sorted(nets)}")
    for n in sorted(nets):
        ok = connect_net(path, n, BOX, WIDTH.get(n, 0.15), 0.15, keepout=KEEP)
        print(f"  {n}: {'connected' if ok else 'STILL OPEN'}", flush=True)
    refill(path)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
