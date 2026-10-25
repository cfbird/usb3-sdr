#!/usr/bin/env python3
"""Small two-layer A* grid router for the few connections the autorouter cannot reach.

Obstacles are rasterised from the board's real copper (pads, tracks, vias, board edge) and inflated by the
clearance plus half the track width, so a path through free cells is DRC-clean by construction (DRC still checks).
Routes are added locked.

usage: grid_route.py board.kicad_pcb "<net>" FROM TO --width W --clear C [--box x0,y0,x1,y1] [--save out]
  FROM / TO:  REF-PAD (e.g. U11-25), or "net" for TO = any existing copper / pad of the same net
"""
import argparse
import heapq
import math
import re
import os
import sys

import numpy as np
import pcbnew

T, MM = pcbnew.ToMM, pcbnew.FromMM
STEP = 0.025                      # grid pitch, mm
VIA_D, VIA_DRILL = 0.45, 0.2
LAYERS = (pcbnew.F_Cu, pcbnew.B_Cu)
VIA_COST, DIAG = 4.0, math.sqrt(2)
TURN = 0.3 / STEP                 # each change of direction costs as much as 0.3 mm of track
BODY_REFS = "JYKL"                # connectors, crystals, relays, inductors: no copper under the body. ICs are
                                  # left out: a BGA is routed under its body, and a QFN's pads block it anyway


class Grid:
    def __init__(self, box):
        self.x0, self.y0, x1, y1 = box
        self.nx, self.ny = int((x1 - self.x0) / STEP) + 1, int((y1 - self.y0) / STEP) + 1
        self.X, self.Y = np.meshgrid(self.x0 + np.arange(self.nx) * STEP, self.y0 + np.arange(self.ny) * STEP)

    def cell(self, x, y):
        return int(round((x - self.x0) / STEP)), int(round((y - self.y0) / STEP))

    def xy(self, i, j):
        return self.x0 + i * STEP, self.y0 + j * STEP

    def seg_dist(self, ax, ay, bx, by):
        """Distance from every grid point to segment a-b."""
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        t = np.zeros_like(self.X) if L2 == 0 else np.clip(((self.X - ax) * dx + (self.Y - ay) * dy) / L2, 0, 1)
        return np.hypot(self.X - (ax + t * dx), self.Y - (ay + t * dy))

    def poly_dist(self, pts):
        """Distance to a closed polygon outline, 0 inside."""
        d = np.full(self.X.shape, np.inf)
        inside = np.zeros(self.X.shape, bool)
        n = len(pts)
        for k in range(n):
            (ax, ay), (bx, by) = pts[k], pts[(k + 1) % n]
            d = np.minimum(d, self.seg_dist(ax, ay, bx, by))
            cross = ((ay > self.Y) != (by > self.Y)) & (self.X < (bx - ax) * (self.Y - ay) / (by - ay + 1e-12) + ax)
            inside ^= cross
        d[inside] = 0
        return d


def pad_poly(pad, layer):
    if isinstance(pad, _Point):
        x, y = T(pad.pos.x), T(pad.pos.y)
        return [(x - .03, y - .03), (x + .03, y - .03), (x + .03, y + .03), (x - .03, y + .03)]
    sp = pad.GetEffectivePolygon(layer, pcbnew.ERROR_INSIDE) if hasattr(pad, "GetEffectivePolygon") else None
    if sp is None or sp.OutlineCount() == 0:
        bb = pad.GetBoundingBox()
        return [(T(bb.GetX()), T(bb.GetY())), (T(bb.GetRight()), T(bb.GetY())),
                (T(bb.GetRight()), T(bb.GetBottom())), (T(bb.GetX()), T(bb.GetBottom()))]
    o = sp.Outline(0)
    return [(T(o.CPoint(k).x), T(o.CPoint(k).y)) for k in range(o.PointCount())]


def build(board, net, box, width, clear):
    g = Grid(box)
    x0, y0, x1, y1 = box
    trk_r, via_r = clear + width / 2, clear + VIA_D / 2
    near = lambda x, y, m: x0 - m < x < x1 + m and y0 - m < y < y1 + m
    dist = {L: np.full(g.X.shape, np.inf) for L in LAYERS}      # distance to foreign copper per layer
    own = {L: np.zeros(g.X.shape, bool) for L in LAYERS}         # cells on own-net copper (targets)
    hole = np.full(g.X.shape, np.inf)                            # distance to any drilled hole
    code = board.FindNet(net).GetNetCode()
    for fp in board.GetFootprints():
        for pd in fp.Pads():
            q = pd.GetPosition()
            if not near(T(q.x), T(q.y), 3):
                continue
            for L in LAYERS:
                if not pd.IsOnLayer(L):
                    continue
                d = g.poly_dist(pad_poly(pd, L))
                if pd.GetNetCode() == code:
                    own[L] |= d == 0
                else:
                    dist[L] = np.minimum(dist[L], d)
            if pd.GetDrillSize().x > 0:
                hole = np.minimum(hole, np.hypot(g.X - T(q.x), g.Y - T(q.y)) - T(pd.GetDrillSize().x) / 2)
    for t in board.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            q = t.GetPosition()
            if not near(T(q.x), T(q.y), 2):
                continue
            d = np.hypot(g.X - T(q.x), g.Y - T(q.y)) - T(t.GetWidth(pcbnew.F_Cu)) / 2
            hole = np.minimum(hole, d + T(t.GetWidth(pcbnew.F_Cu)) / 2 - T(t.GetDrill()) / 2)
            for L in LAYERS:
                if t.GetNetCode() == code:
                    own[L] |= d <= 0
                else:
                    dist[L] = np.minimum(dist[L], d)
            continue
        s, e = t.GetStart(), t.GetEnd()
        if t.GetLayer() not in LAYERS or not (near(T(s.x), T(s.y), 15) or near(T(e.x), T(e.y), 15)):
            continue
        d = g.seg_dist(T(s.x), T(s.y), T(e.x), T(e.y)) - T(t.GetWidth()) / 2
        if t.GetNetCode() == code:
            own[t.GetLayer()] |= d <= 0
        else:
            dist[t.GetLayer()] = np.minimum(dist[t.GetLayer()], d)
    edge = board.GetBoardEdgesBoundingBox()
    ex = np.minimum.reduce([g.X - T(edge.GetX()), T(edge.GetRight()) - g.X, g.Y - T(edge.GetY()), T(edge.GetBottom()) - g.Y])
    own_pad_gap = np.full(g.X.shape, np.inf)       # vias stay 0.1 mm clear of this net's pads (no via-in-pad)
    for fp in board.GetFootprints():
        for pd in fp.Pads():
            q = pd.GetPosition()
            if near(T(q.x), T(q.y), 3) and pd.GetNetCode() == code:
                for L in LAYERS:
                    if pd.IsOnLayer(L):
                        own_pad_gap = np.minimum(own_pad_gap, g.poly_dist(pad_poly(pd, L)))
    # no copper under a part's body: block its Fab outline except right at this net's own pads, so a route can
    # only reach a pad from outside the body (keeps tracks out from under the USB-C shell, crystals, etc.)
    near_own = {L: np.zeros(g.X.shape, bool) for L in LAYERS}
    any_body = np.zeros(g.X.shape, bool)
    for fp in board.GetFootprints():
        q = fp.GetPosition()
        if not near(T(q.x), T(q.y), 8) or fp.GetReference()[0] not in BODY_REFS:
            continue
        L = pcbnew.B_Cu if fp.IsFlipped() else pcbnew.F_Cu
        fab = pcbnew.B_Fab if fp.IsFlipped() else pcbnew.F_Fab
        boxes = [it.GetBoundingBox() for it in fp.GraphicalItems() if it.GetLayer() == fab]
        if boxes:
            bx0, by0 = min(T(bb.GetX()) for bb in boxes), min(T(bb.GetY()) for bb in boxes)
            bx1, by1 = max(T(bb.GetRight()) for bb in boxes), max(T(bb.GetBottom()) for bb in boxes)
            body = (g.X >= bx0) & (g.X <= bx1) & (g.Y >= by0) & (g.Y <= by1)      # the part's Fab outline
            for pd in fp.Pads():
                if pd.GetNetCode() == code and pd.IsOnLayer(L):
                    near_own[L] |= g.poly_dist(pad_poly(pd, L)) <= 0.2
            dist[L][body & ~near_own[L]] = 0
            any_body |= body
    free = {L: (dist[L] >= trk_r) & (ex >= 0.5 + width / 2) for L in LAYERS}
    via_ok = (dist[LAYERS[0]] >= via_r) & (dist[LAYERS[1]] >= via_r) & (hole >= 0.25 + VIA_DRILL / 2) & \
        (ex >= 0.5 + VIA_D / 2) & ~any_body & (own_pad_gap >= VIA_D / 2 + 0.1)
    return g, free, via_ok, own


MAX_EXPANSIONS = 1_500_000        # give up (return None) rather than exhaust memory on a hopeless search


def astar(g, free, via_ok, starts, goal, target=None):
    """starts: list of (layer index, i, j); goal(l, i, j) -> bool. States carry the last step direction so that
    turns can be charged; the returned path is a list of (layer, i, j). With a target cell (ti, tj) the search is
    A* with the octile distance as heuristic (admissible: every step costs at least its length)."""
    if target:
        ti, tj = target
        h = lambda i, j: (lambda dx, dy: max(dx, dy) + (DIAG - 1) * min(dx, dy))(abs(i - ti), abs(j - tj))
    else:
        h = lambda i, j: 0.0
    moves = [(1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 1), (1, 1, DIAG), (1, -1, DIAG), (-1, 1, DIAG), (-1, -1, DIAG)]
    openq, came, cost = [], {}, {}
    for s in starts:
        st = (*s, 0, 0)
        cost[st] = 0.0
        heapq.heappush(openq, (h(s[1], s[2]), st))
    expanded = 0
    while openq:
        f, cur = heapq.heappop(openq)
        c = cost.get(cur, math.inf)
        if f - h(cur[1], cur[2]) > c + 1e-9:
            continue
        expanded += 1
        if expanded > MAX_EXPANSIONS:
            return None
        l, i, j, di0, dj0 = cur
        if goal(l, i, j):
            path = [cur]
            while path[-1] in came:
                path.append(came[path[-1]])
            return [p[:3] for p in path[::-1]]
        nbrs = [((l, i + di, j + dj, di, dj), w + (TURN if (di0, dj0) not in ((0, 0), (di, dj)) else 0))
                for di, dj, w in moves]
        if via_ok[j, i]:
            nbrs.append(((1 - l, i, j, 0, 0), VIA_COST / STEP))
        for (nl, ni, nj, a, bb), w in nbrs:
            if not (0 <= ni < g.nx and 0 <= nj < g.ny) or not free[LAYERS[nl]][nj, ni]:
                continue
            # a 45-degree step must not cut the corner of a blocked cell
            if nl == l and ni != i and nj != j and not (free[LAYERS[l]][j, ni] and free[LAYERS[l]][nj, i]):
                continue
            nxt, nc = (nl, ni, nj, a, bb), c + w
            if nc < cost.get(nxt, math.inf):
                cost[nxt] = nc
                came[nxt] = cur
                heapq.heappush(openq, (nc + h(ni, nj), nxt))
    return None


def emit(board, g, net, path, width):
    """Turn a cell path into locked tracks (collinear runs merged) and vias."""
    netobj = board.FindNet(net)
    P = lambda i, j: pcbnew.VECTOR2I(MM(g.xy(i, j)[0]), MM(g.xy(i, j)[1]))
    items, run = [], [path[0]]
    for prev, cur in zip(path, path[1:]):
        if cur[0] != prev[0]:
            items.append(("trk", run)); items.append(("via", cur)); run = [cur]
        else:
            run.append(cur)
    items.append(("trk", run))
    n_trk = n_via = 0
    for kind, data in items:
        if kind == "via":
            v = pcbnew.PCB_VIA(board); v.SetPosition(P(data[1], data[2])); v.SetWidth(MM(VIA_D)); v.SetDrill(MM(VIA_DRILL))
            v.SetNet(netobj); v.SetLocked(True); board.Add(v); n_via += 1
            continue
        pts = [data[0]]
        for k in range(1, len(data) - 1):
            d1 = (data[k][1] - data[k - 1][1], data[k][2] - data[k - 1][2])
            d2 = (data[k + 1][1] - data[k][1], data[k + 1][2] - data[k][2])
            if d1 != d2:
                pts.append(data[k])
        pts.append(data[-1])
        for a, b in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(board); t.SetStart(P(a[1], a[2])); t.SetEnd(P(b[1], b[2])); t.SetWidth(MM(width))
            t.SetLayer(LAYERS[a[0]]); t.SetNet(netobj); t.SetLocked(True); board.Add(t); n_trk += 1
    return n_trk, n_via


class _Point:
    """Stand-in for a start pad when a route starts from a point on existing copper ("pt:<layer>:<x>,<y>")."""
    def __init__(self, layer, x, y):
        self.layer, self.pos = layer, pcbnew.VECTOR2I(MM(x), MM(y))
        self.m_Uuid = pcbnew.KIID()

    def GetPosition(self):
        return self.pos

    def IsOnLayer(self, L):
        return L == self.layer

    def HitTest(self, p, acc=0):
        return (p - self.pos).EuclideanNorm() <= max(acc, MM(0.05))

    def Type(self):
        return pcbnew.PCB_PAD_T


def pad_center(board, spec):
    if spec.startswith("pt:"):
        _, layer, xy = spec.split(":")
        x, y = map(float, xy.split(","))
        q = _Point(LAYERS[int(layer)], x, y)
        return x, y, q
    ref, num = spec.rsplit("-", 1)
    p = next(p for p in board.FindFootprintByReference(ref).Pads() if p.GetNumber() == num)
    return T(p.GetPosition().x), T(p.GetPosition().y), p


def route(board, net, frm, to, width, clear, box, keepout=(), layers=("F", "B"), aim=None):
    """keepout: rectangles (x0, y0, x1, y1) this route may not use, e.g. a corridor reserved for another net.
    layers: ("F",) keeps the route on F.Cu (no vias).
    aim: (x, y) of the own-net copper a "net" route is expected to reach; steers the search (heuristic only)."""
    g, free, via_ok, own = build(board, net, box, width, clear)
    if "B" not in layers:
        via_ok[:] = False
        free[pcbnew.B_Cu][:] = False
    for kx0, ky0, kx1, ky1 in keepout:
        k = (g.X >= kx0) & (g.X <= kx1) & (g.Y >= ky0) & (g.Y <= ky1)
        via_ok &= ~k
        for L in LAYERS:
            free[L] &= ~k
    x, y, p = pad_center(board, frm)
    si, sj = g.cell(x, y)
    starts = [(k, si, sj) for k, L in enumerate(LAYERS) if p.IsOnLayer(L)]
    for s in starts:
        free[LAYERS[s[0]]][sj, si] = True
    if to == "net":
        sx = {(s[1], s[2]) for s in starts}
        # any own-net copper that is not already connected to the start pad (walk touching copper from the pad)
        code_ = board.FindNet(net).GetNetCode()
        items = [t for t in board.GetTracks() if t.GetNetCode() == code_]
        pads_ = [q for q in board.GetPads() if q.GetNetCode() == code_]
        ends = lambda t: [t.GetPosition()] if t.Type() == pcbnew.PCB_VIA_T else [t.GetStart(), t.GetEnd()]
        isl_t, isl_p, todo = set(), {p.m_Uuid.AsString()}, [p]
        if isinstance(p, _Point):          # a point start belongs to the track it sits on
            todo = [t for t in items if t.HitTest(p.GetPosition(), 1000)] or [p]
            isl_t = {t.m_Uuid.AsString() for t in todo if t is not p}
        while todo:
            it = todo.pop()
            for t in items:
                u = t.m_Uuid.AsString()
                if u in isl_t:
                    continue
                touch = any(it.HitTest(e, 1000) for e in ends(t)) if it.Type() == pcbnew.PCB_PAD_T or \
                    it.Type() == pcbnew.PCB_VIA_T else any(t.HitTest(e, 1000) for e in ends(it)) or \
                    any(it.HitTest(e, 1000) for e in ends(t))
                if touch:
                    isl_t.add(u); todo.append(t)
            if it.Type() != pcbnew.PCB_PAD_T:
                for q in pads_:
                    if q.m_Uuid.AsString() not in isl_p and any(q.HitTest(e) for e in ends(it)):
                        isl_p.add(q.m_Uuid.AsString()); todo.append(q)
        island = {k: np.zeros(g.X.shape, bool) for k in range(len(LAYERS))}
        for k, L in enumerate(LAYERS):
            for q in pads_:
                if q.m_Uuid.AsString() in isl_p and q.IsOnLayer(L):
                    island[k] |= g.poly_dist(pad_poly(q, L)) <= 0
            for t in items:
                if t.m_Uuid.AsString() not in isl_t:
                    continue
                if t.Type() == pcbnew.PCB_VIA_T:
                    island[k] |= np.hypot(g.X - T(t.GetPosition().x), g.Y - T(t.GetPosition().y)) <= T(t.GetWidth(pcbnew.F_Cu)) / 2
                elif t.GetLayer() == L:
                    island[k] |= g.seg_dist(T(t.GetStart().x), T(t.GetStart().y), T(t.GetEnd().x), T(t.GetEnd().y)) <= T(t.GetWidth()) / 2
        goal = lambda l, i, j: own[LAYERS[l]][j, i] and not island[l][j, i]
    else:
        tx, ty, tp = pad_center(board, to)
        tpoly = {k: g.poly_dist(pad_poly(tp, L)) <= 0 for k, L in enumerate(LAYERS) if tp.IsOnLayer(L)}
        ti, tj = g.cell(tx, ty)
        for k in tpoly:
            free[LAYERS[k]][tj, ti] = True
        goal = lambda l, i, j: l in tpoly and i == ti and j == tj
    # own-net copper never blocks
    for L in LAYERS:
        free[L] |= own[L]
    if to == "net" and aim is None:
        # aim at the nearest own-net copper that is not the start pad's own island: endpoints of tracks / vias / pads
        sx, sy = T(p.GetPosition().x), T(p.GetPosition().y)
        code = board.FindNet(net).GetNetCode()
        pts = []
        for t in board.GetTracks():
            if t.GetNetCode() != code:
                continue
            for q in ([t.GetPosition()] if t.Type() == pcbnew.PCB_VIA_T else [t.GetStart(), t.GetEnd()]):
                if not p.HitTest(q):
                    pts.append((T(q.x), T(q.y)))
        pts += [(T(q.GetPosition().x), T(q.GetPosition().y)) for q in board.GetPads()
                if q.GetNetCode() == code and q.m_Uuid.AsString() != p.m_Uuid.AsString()]
        x0, y0, x1, y1 = box
        pts = [q for q in pts if x0 <= q[0] <= x1 and y0 <= q[1] <= y1]
        if pts:
            aim = min(pts, key=lambda q: (q[0] - sx) ** 2 + (q[1] - sy) ** 2)
    target = (ti, tj) if to != "net" else (g.cell(*aim) if aim else None)
    path = astar(g, free, via_ok, starts, goal, target)
    if path is None:
        return None
    return emit(board, g, net, path, width)


def connect_net(path, net, box, width, clear, max_rounds=6, **kw):
    """Route until DRC reports no unconnected pair on this net inside the box (zones count, so plane nets work).
    Each round loads the board, routes from one end of each reported pair (a pad, or a point on the track end
    nearest the other item) towards the other item, saves, and re-runs DRC."""
    import json, subprocess, tempfile
    for _ in range(max_rounds):
        out = tempfile.mktemp(suffix=".json")
        subprocess.run(["kicad-cli", "pcb", "drc", "--format", "json", "-o", out, path], capture_output=True)
        d = json.load(open(out)); os.unlink(out)
        pairs = []
        for u in d["unconnected_items"]:
            it = u["items"]
            if not all(f"[{net}]" in i["description"] for i in it):
                continue
            if all(box[0] <= i["pos"]["x"] <= box[2] and box[1] <= i["pos"]["y"] <= box[3] for i in it):
                pairs.append(it)
        if not pairs:
            return True
        b = pcbnew.LoadBoard(path)
        ok = False
        for a, c in pairs:
            for s_, e_ in ((a, c), (c, a)):
                m = re.match(r"Pad (\S+) \[.*\] of (\S+) on", s_["description"])
                if m:
                    frm = f"{m.group(2)}-{m.group(1)}"
                else:
                    lay = 1 if "on B.Cu" in s_["description"] else 0
                    frm = f"pt:{lay}:{s_['pos']['x']},{s_['pos']['y']}"
                r = route(b, net, frm, "net", width, clear, box, aim=(e_["pos"]["x"], e_["pos"]["y"]), **kw)
                if r:
                    ok = True
                    break
        b.Save(path)
        if not ok:
            return False
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("board"); ap.add_argument("net"); ap.add_argument("frm"); ap.add_argument("to")
    ap.add_argument("--width", type=float, required=True); ap.add_argument("--clear", type=float, required=True)
    ap.add_argument("--box", required=True); ap.add_argument("--save")
    a = ap.parse_args()
    if not os.path.exists(os.path.splitext(a.board)[0] + ".kicad_pro"):
        sys.exit(f"{a.board}: no matching .kicad_pro next to it")
    b = pcbnew.LoadBoard(a.board)
    r = route(b, a.net, a.frm, a.to, a.width, a.clear, tuple(map(float, a.box.split(","))))
    if r is None:
        sys.exit(f"no path for {a.net} {a.frm} -> {a.to}")
    print(f"{a.net}: {r[0]} tracks, {r[1]} vias")
    b.Save(a.save or a.board)


if __name__ == "__main__":
    main()
