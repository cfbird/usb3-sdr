#!/usr/bin/env python3
"""Apply a U12 power fan-out plan (notes/fanout/agy_fanout_plan.json): new In2 islands, core vias, corridor part moves.

Rips the core-rail copper (1V1, 3V3_D, 1V8_D, 2V5) under the BGA (even locked) and the unlocked rail copper around
it, the vias the plan deletes (with their dog-bones, even when locked) and unlocked copper ending on parts the plan moves. Then replaces the In2 zones of
every net the plan gives polygons for (3V3_D and GND fills are kept and extended, not replaced), places the plan's
vias with straight ball-to-via tracks, moves the parts, and refills. Routing what the rip-up opened is left to
grid_route / the router.
usage: fanout_apply.py plan.json board.kicad_pcb   (board edited in place)
"""
import json
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from repair_conflicts import dangling, delete_by_uuid, refill  # noqa: E402

T, MM = pcbnew.ToMM, pcbnew.FromMM
P = lambda x, y: pcbnew.VECTOR2I(MM(x), MM(y))
RAILS = ("1V1", "3V3_D", "1V8_D", "2V5")
RIP_BOX = (154.0, 115.0, 179.0, 133.0)          # U12 plus the U12 <-> U11 corridor
U12_BOX = (155.5, 116.5, 170.5, 131.5)          # here rail copper goes even when locked (e.g. vccaux_patch's 2V5)
KEEP_ZONES = ("3V3_D", "GND")                   # nets whose existing In2 zones stay (plan polygons are added)
DOGBONE_W = 0.25
NEAR = 0.05                                     # mm, position match for delete_vias


def seg_dist(p, a, c):
    (px, py), (ax, ay), (cx, cy) = p, a, c
    dx, dy = cx - ax, cy - ay
    u = 0.0 if dx == dy == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return ((ax + u * dx - px) ** 2 + (ay + u * dy - py) ** 2) ** 0.5


def inside(p, box):
    return box[0] < T(p.x) < box[2] and box[1] < T(p.y) < box[3]


def main(plan_path, path):
    if not os.path.exists(os.path.splitext(path)[0] + ".kicad_pro"):
        sys.exit(f"{path}: no matching .kicad_pro next to it")
    plan = json.load(open(plan_path))
    gone = [tuple(v) for v in plan.get("delete_vias", [])]
    b = pcbnew.LoadBoard(path)
    moved_pads = [q for r in plan.get("moves", {}) for q in b.FindFootprintByReference(r).Pads()]
    dead, frontier = set(), []
    tracks = list(b.GetTracks())
    for t in tracks:
        if t.Type() == pcbnew.PCB_VIA_T:
            q = t.GetPosition()
            if any(abs(T(q.x) - x) < NEAR and abs(T(q.y) - y) < NEAR for x, y in gone):
                dead.add(t.m_Uuid.AsString()); frontier.append((q, t.GetNetCode()))
    # walk each deleted via's dog-bone back to its ball, locked or not (some are two segments)
    pads = [q for q in b.GetPads()]
    while frontier:
        q, net = frontier.pop()
        for t in tracks:
            if t.Type() == pcbnew.PCB_VIA_T or t.GetNetCode() != net or t.m_Uuid.AsString() in dead:
                continue
            s_, e_ = t.GetStart(), t.GetEnd()
            if (s_ - q).EuclideanNorm() < MM(0.01) or (e_ - q).EuclideanNorm() < MM(0.01):
                dead.add(t.m_Uuid.AsString())
                far = e_ if (s_ - q).EuclideanNorm() < MM(0.01) else s_
                if not any(p.GetNetCode() == net and p.HitTest(far) for p in pads):
                    frontier.append((far, net))
    u12_pads = list(b.FindFootprintByReference("U12").Pads())
    for t in tracks:
        ends = [t.GetPosition()] if t.Type() == pcbnew.PCB_VIA_T else [t.GetStart(), t.GetEnd()]
        if t.Type() != pcbnew.PCB_VIA_T and t.GetNetname() == "GND" and \
                all(any(q.HitTest(e) for q in u12_pads) for e in ends):
            dead.add(t.m_Uuid.AsString())     # old ball-to-ball GND link (vccaux_patch G10-H10); plan vias replace it
        if t.GetNetname() in RAILS and any(inside(e, U12_BOX) for e in ends):
            dead.add(t.m_Uuid.AsString())
        if t.IsLocked():
            continue
        if t.GetNetname() in RAILS and any(inside(e, RIP_BOX) for e in ends):
            dead.add(t.m_Uuid.AsString())
        if any(q.HitTest(e) for q in moved_pads for e in ends):
            dead.add(t.m_Uuid.AsString())
        if t.Type() != pcbnew.PCB_VIA_T:      # unlocked foreign track under a new plan via (else it takes its net)
            s_, e_ = (T(t.GetStart().x), T(t.GetStart().y)), (T(t.GetEnd().x), T(t.GetEnd().y))
            keep = 0.225 + 0.127 + T(t.GetWidth()) / 2
            if any(v["net"] != t.GetNetname() and seg_dist(v["xy"], s_, e_) < keep for v in plan.get("vias", [])):
                dead.add(t.m_Uuid.AsString())
    del b
    n = delete_by_uuid(path, dead)
    while True:
        d = dangling(path)
        if not d:
            break
        n += delete_by_uuid(path, d)
    print(f"ripped {n} items")

    b = pcbnew.LoadBoard(path)
    polys = plan.get("in2_polygons", [])
    nets = {p["net"] for p in polys}
    in2 = [z for z in b.Zones() if z.GetLayer() == pcbnew.In2_Cu]
    proto = {z.GetNetname(): z for z in in2}
    template = proto.get("1V1") or in2[0]
    new = []
    for p in polys:
        z = (proto.get(p["net"]) or template).Duplicate()
        z.SetNet(b.FindNet(p["net"]))
        z.SetAssignedPriority(p["priority"])
        z.Outline().RemoveAllContours()
        z.Outline().NewOutline()
        for x, y in p["outline"]:
            z.Outline().Append(MM(x), MM(y))
        new.append(z)
    for z in in2:
        if z.GetNetname() in nets and z.GetNetname() not in KEEP_ZONES:
            b.Remove(z)
    for z in new:
        b.Add(z)

    balls = {q.GetNumber(): q for q in b.FindFootprintByReference("U12").Pads()}
    for v in plan.get("vias", []):
        net = b.FindNet(v["net"])
        via = pcbnew.PCB_VIA(b); via.SetPosition(P(*v["xy"])); via.SetWidth(MM(0.45)); via.SetDrill(MM(0.2))
        via.SetNet(net); via.SetLocked(True); b.Add(via)
        for ball in v["balls"]:
            q = balls[ball]
            assert q.GetNetname() == v["net"], f"{ball} is {q.GetNetname()}, plan says {v['net']}"
            # optional "paths": {ball: [[x,y],...]} bends a dog-bone between neighbouring balls (0.15 mm wide there)
            bend = v.get("paths", {}).get(ball, [])
            pts = [q.GetPosition()] + [P(*xy) for xy in bend] + [P(*v["xy"])]
            for a, c in zip(pts, pts[1:]):
                t = pcbnew.PCB_TRACK(b); t.SetStart(a); t.SetEnd(c)
                t.SetWidth(MM(0.15 if bend else DOGBONE_W))
                t.SetLayer(pcbnew.F_Cu); t.SetNet(net); t.SetLocked(True); b.Add(t)
    for ref, m in plan.get("moves", {}).items():
        f = b.FindFootprintByReference(ref)
        f.SetOrientationDegrees(m["rot"]); f.SetPosition(P(*m["xy"])); f.SetLocked(True)
    b.Save(path)
    refill(path)
    print(f"{len(new)} In2 zones, {len(plan.get('vias', []))} vias, {len(plan.get('moves', {}))} moves")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
