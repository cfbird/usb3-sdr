#!/usr/bin/env python3
"""Nudge parts to the nearest spot where their pads clear protected copper and their courtyards clear other parts.

Protected copper = locked items plus every track/via/pad of the nets in PROTECT (power, switch nodes) on the part's
layer; other unlocked signal copper is ignored (it gets ripped by repair_conflicts.py and re-routed).
Searches outward from the current position in 0.1 mm steps up to RADIUS, rotations 0/90/180/270.
usage: place_free.py board.kicad_pcb REF [REF ...]   (board edited in place)
"""
import os
import sys

import pcbnew

T, MM = pcbnew.ToMM, pcbnew.FromMM
PROTECT = {"GND", "1V1", "3V3_D", "1V8_D", "1V8_A", "2V5", "5V_SW", "VBUS", "/USB 3 bridge/FT_1V0",
           "/USB 3 bridge/FT_VDDA"}
CLR = 0.15          # mm, pad to protected copper
RADIUS, STEP = 3.0, 0.1


def blockers(b, f):
    out = []
    for t in b.GetTracks():
        if not t.IsOnLayer(f.GetLayer()):
            continue
        if t.IsLocked() or t.GetNetname() in PROTECT:
            out.append(t)
    for g in b.GetFootprints():
        if g.GetReference() != f.GetReference():
            out += [p for p in g.Pads() if p.IsOnLayer(f.GetLayer())]
    return out


def courtyards(b, f):
    lay = pcbnew.F_CrtYd if f.GetLayer() == pcbnew.F_Cu else pcbnew.B_CrtYd
    return [g.GetCourtyard(lay) for g in b.GetFootprints() if g.GetReference() != f.GetReference()
            and g.GetCourtyard(lay).OutlineCount()], lay


def ok(f, obs, cys, lay):
    for p in f.Pads():
        s = p.GetEffectiveShape(f.GetLayer())
        for o in obs:
            if o.GetNetCode() == p.GetNetCode() and p.GetNetCode() > 0:
                continue
            if s.Collide(o.GetEffectiveShape(f.GetLayer()), MM(CLR)):
                return False
    mine = f.GetCourtyard(lay)
    return not any(mine.Collide(c.Outline(0)) for c in cys) if mine.OutlineCount() else True


def main(path, refs):
    if not os.path.exists(os.path.splitext(path)[0] + ".kicad_pro"):
        sys.exit(f"{path}: no matching .kicad_pro next to it")
    b = pcbnew.LoadBoard(path)
    for ref in refs:
        f = b.FindFootprintByReference(ref)
        obs = blockers(b, f)
        cys, lay = courtyards(b, f)
        x0, y0, r0 = T(f.GetPosition().x), T(f.GetPosition().y), f.GetOrientationDegrees()
        cands = sorted(((dx * STEP, dy * STEP) for dx in range(-30, 31) for dy in range(-30, 31)
                        if (dx * dx + dy * dy) * STEP * STEP <= RADIUS ** 2), key=lambda d: d[0] ** 2 + d[1] ** 2)
        for dx, dy in cands:
            hit = None
            for rot in (r0, r0 + 90, r0 + 180, r0 + 270):
                f.SetOrientationDegrees(rot % 360)
                f.SetPosition(pcbnew.VECTOR2I(MM(x0 + dx), MM(y0 + dy)))
                if ok(f, obs, cys, lay):
                    hit = rot % 360
                    break
            if hit is not None:
                print(f"{ref}: ({x0:.2f},{y0:.2f}) -> ({x0 + dx:.2f},{y0 + dy:.2f}) rot {hit:.0f}")
                break
        else:
            f.SetOrientationDegrees(r0); f.SetPosition(pcbnew.VECTOR2I(MM(x0), MM(y0)))
            print(f"{ref}: no free spot within {RADIUS} mm, left in place")
        f.SetLocked(True)
    b.Save(path)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
