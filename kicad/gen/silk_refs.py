#!/usr/bin/env python3
"""Re-place footprint reference labels on F.Silkscreen so they clear pads, silk outlines, other labels and the board
edge; hide the label (it stays on F.Fab) where no free spot exists near the part.

Candidates per part: the label inside the part's outline (centre, +/-0.5 mm), and centred on each side and corner of the part's outline box (pads + silk + courtyard),
pushed out in 0.25 mm steps up to 1.9 mm and slid along the side, at 0 or 90 deg, height 1.0 then 0.8 mm (stroke
0.15). A candidate is rejected if its centre is nearer another part's pads than its own (readable assignment).
The best candidate is the one nearest the part, preferring 1.0 mm. Parts with the fewest free candidates are
placed first; each placed label becomes an obstacle for the next.
usage: python3 kicad/gen/silk_refs.py in.kicad_pcb out.kicad_pcb [--report out.json]
"""
import json
import math
import sys

import pcbnew

MM, T = pcbnew.FromMM, pcbnew.ToMM
PAD_CLR, SILK_CLR, EDGE_CLR = 0.12, 0.05, 0.5
SIZES = (1.0, 0.8)
STROKE = 0.15


def rect_of(bb, grow=0.0):
    return (T(bb.GetX()) - grow, T(bb.GetY()) - grow, T(bb.GetRight()) + grow, T(bb.GetBottom()) + grow)


def glyph_rect(t):
    """Box of the stroked glyphs (what DRC tests), not the looser text box."""
    return rect_of(t.GetEffectiveTextShape().BBox())


def overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def seg_rect_dist(p, q, r):
    """Distance between segment p-q and axis-aligned rectangle r (0 if they touch)."""
    def inside(x, y):
        return r[0] <= x <= r[2] and r[1] <= y <= r[3]
    if inside(*p) or inside(*q):
        return 0.0
    corners = [(r[0], r[1]), (r[2], r[1]), (r[2], r[3]), (r[0], r[3])]
    edges = list(zip(corners, corners[1:] + corners[:1]))

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    for a, b in edges:
        if cross(p, q, a) * cross(p, q, b) < 0 and cross(a, b, p) * cross(a, b, q) < 0:
            return 0.0

    def dps(x, a, b):
        ax, ay = b[0] - a[0], b[1] - a[1]
        L = ax * ax + ay * ay
        u = 0 if L == 0 else max(0, min(1, ((x[0] - a[0]) * ax + (x[1] - a[1]) * ay) / L))
        return math.hypot(x[0] - a[0] - u * ax, x[1] - a[1] - u * ay)
    return min([dps(c, p, q) for c in corners] + [dps(p, a, b) for a, b in edges] + [dps(q, a, b) for a, b in edges])


def shapes(items, layer):
    """(kind, geometry, half-width) for graphic items on a layer: segments as lines, everything else as boxes."""
    out = []
    for g in items:
        if g.GetLayer() != layer or not isinstance(g, pcbnew.PCB_SHAPE):
            continue
        hw = T(g.GetWidth()) / 2
        if g.GetShape() == pcbnew.SHAPE_T_SEGMENT:
            s, e = g.GetStart(), g.GetEnd()
            out.append(("seg", ((T(s.x), T(s.y)), (T(e.x), T(e.y))), hw))
        elif g.GetShape() == pcbnew.SHAPE_T_RECT and not g.IsFilled():
            s, e = g.GetStart(), g.GetEnd()
            c = [(T(s.x), T(s.y)), (T(e.x), T(s.y)), (T(e.x), T(e.y)), (T(s.x), T(e.y))]
            out += [("seg", (a, b), hw) for a, b in zip(c, c[1:] + c[:1])]
        else:
            out.append(("box", rect_of(g.GetBoundingBox()), 0.0))
    return out


def clear(r, obs, clr):
    for kind, g, hw in obs:
        if kind == "seg":
            if min(g[0][0], g[1][0]) - hw - clr > r[2] or max(g[0][0], g[1][0]) + hw + clr < r[0] \
                    or min(g[0][1], g[1][1]) - hw - clr > r[3] or max(g[0][1], g[1][1]) + hw + clr < r[1]:
                continue
            if seg_rect_dist(g[0], g[1], r) < hw + clr:
                return False
        elif overlap(r, (g[0] - clr, g[1] - clr, g[2] + clr, g[3] + clr)):
            return False
    return True


def main(src, dst, report=None):
    b = pcbnew.LoadBoard(src)
    fps = [f for f in b.GetFootprints() if not f.IsFlipped()]
    edge = shapes(b.GetDrawings(), pcbnew.Edge_Cuts)
    for f in b.GetFootprints():
        edge += shapes(f.GraphicalItems(), pcbnew.Edge_Cuts)
    ob = rect_of(b.GetBoardEdgesBoundingBox())
    inner = (ob[0] + EDGE_CLR, ob[1] + EDGE_CLR, ob[2] - EDGE_CLR, ob[3] - EDGE_CLR)
    pads = [("box", rect_of(p.GetBoundingBox()), 0.0) for f in b.GetFootprints() for p in f.Pads()
            if p.IsOnLayer(pcbnew.F_Mask) or p.IsOnLayer(pcbnew.F_Cu)]
    silk = shapes(b.GetDrawings(), pcbnew.F_SilkS)
    for f in fps:
        silk += shapes(f.GraphicalItems(), pcbnew.F_SilkS)
        for t in f.GraphicalItems():
            if isinstance(t, pcbnew.PCB_TEXT) and t.GetLayer() == pcbnew.F_SilkS and t.IsVisible():
                silk.append(("box", glyph_rect(t), 0.0))
        v = f.Value()
        if v.IsVisible() and v.GetLayer() == pcbnew.F_SilkS:
            silk.append(("box", glyph_rect(v), 0.0))

    def body(f):
        r = None
        for bb in [p.GetBoundingBox() for p in f.Pads()] + [g.GetBoundingBox() for g in f.GraphicalItems()
                                                             if g.GetLayer() in (pcbnew.F_SilkS, pcbnew.F_CrtYd)]:
            x = rect_of(bb)
            r = x if r is None else (min(r[0], x[0]), min(r[1], x[1]), max(r[2], x[2]), max(r[3], x[3]))
        return r or rect_of(f.GetBoundingBox(False, False))

    def text_rect(ref, size, ang):
        ref.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size)))
        ref.SetTextThickness(MM(STROKE))
        ref.SetTextAngle(pcbnew.EDA_ANGLE(ang, pcbnew.DEGREES_T))
        ref.SetPosition(pcbnew.VECTOR2I(0, 0))
        r = glyph_rect(ref)
        return r[2] - r[0], r[3] - r[1], ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)

    def pad_box(f):
        xs = [rect_of(p.GetBoundingBox()) for p in f.Pads()]
        return (min(x[0] for x in xs), min(x[1] for x in xs), max(x[2] for x in xs), max(x[3] for x in xs)) if xs else None

    def dist(p, r):
        return math.hypot(max(r[0] - p[0], 0, p[0] - r[2]), max(r[1] - p[1], 0, p[1] - r[3]))
    boxes = {f.GetReference(): pad_box(f) for f in b.GetFootprints()}
    boxes = {k: v for k, v in boxes.items() if v}

    def unambiguous(name, p):
        own = dist(p, boxes[name]) if name in boxes else 0
        return all(dist(p, v) > own for k, v in boxes.items() if k != name
                   and v[0] - 4 < p[0] < v[2] + 4 and v[1] - 4 < p[1] < v[3] + 4)

    cands = {}
    for f in fps:
        ref = f.Reference()
        bx = body(f)
        cx, cy = (bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2
        lst = []
        for si, size in enumerate(SIZES):
            for ang in (0, 90):
                w, h, off = text_rect(ref, size, ang)
                pos = [(cx + dx, cy + dy, 0.1 + abs(dx) + abs(dy)) for dx in (0, -0.5, 0.5) for dy in (0, -0.5, 0.5)]
                for push in (0.15, 0.4, 0.65, 0.9, 1.15, 1.4, 1.65, 1.9):
                    for side in ("N", "S", "W", "E"):
                        span = (bx[2] - bx[0]) if side in "NS" else (bx[3] - bx[1])
                        for slide in sorted({0.0, -0.5, 0.5, -1.0, 1.0, -1.5, 1.5, -span / 2, span / 2}, key=abs):
                            if side == "N":
                                x, y = cx + slide, bx[1] - push - h / 2
                            elif side == "S":
                                x, y = cx + slide, bx[3] + push + h / 2
                            elif side == "W":
                                x, y = bx[0] - push - w / 2, cy + slide
                            else:
                                x, y = bx[2] + push + w / 2, cy + slide
                            pos.append((x, y, push + abs(slide) * 0.5))
                for x, y, base in pos:
                    r = (x - w / 2, y - h / 2, x + w / 2, y + h / 2)
                    if not (inner[0] <= r[0] and r[2] <= inner[2] and inner[1] <= r[1] and r[3] <= inner[3]):
                        continue
                    if not unambiguous(f.GetReference(), (x, y)):
                        continue
                    if not clear(r, edge, EDGE_CLR) or not clear(r, pads, PAD_CLR) or not clear(r, silk, SILK_CLR):
                        continue
                    lst.append((base + si * 1.0 + (0.05 if ang else 0), size, ang, (x - off[0], y - off[1]), r))
        cands[f.GetReference()] = sorted(lst)

    placed, hidden, moved = [], [], {}
    byref = {f.GetReference(): f for f in fps}
    for name in sorted(cands, key=lambda n: (len(cands[n]), n)):
        f = byref[name]
        ref = f.Reference()
        for score, size, ang, pos, r in cands[name]:
            if all(not overlap(r, (p[0] - SILK_CLR, p[1] - SILK_CLR, p[2] + SILK_CLR, p[3] + SILK_CLR))
                   for p in placed):
                text_rect(ref, size, ang)
                ref.SetPosition(pcbnew.VECTOR2I(MM(pos[0]), MM(pos[1])))
                ref.SetVisible(True)
                placed.append(glyph_rect(ref))
                moved[name] = {"size": size, "angle": ang, "xy": [round(pos[0], 3), round(pos[1], 3)]}
                break
        else:
            text_rect(ref, SIZES[0], 0)
            ref.SetPosition(f.GetPosition())
            ref.SetVisible(False)
            hidden.append(name)
    b.Save(dst)
    n08 = sum(m["size"] == 0.8 for m in moved.values())
    print(f"{len(fps)} parts: {len(moved)} labels placed ({n08} at 0.8 mm), {len(hidden)} hidden")
    print("hidden:", " ".join(sorted(hidden, key=lambda s: (s.rstrip('0123456789'), int('0' + s[len(s.rstrip('0123456789')):])))))
    if report:
        json.dump({"placed": moved, "hidden": hidden}, open(report, "w"), indent=1)


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[1], a[a.index("--report") + 1] if "--report" in a else None)
