#!/usr/bin/env python3
"""Re-place and hand-route the two TPS62A02 buck power stages (U2 -> 1V1, U3 -> 3V3_D).

Follows the TI layout example (SLUSEG9E Fig. 8-24): IC rotated so VIN|SW|GND face the inductor, Cin beside VIN,
Cout beside the inductor output, FB divider and PG pull-up under the IC. Everything inside a cluster is routed
and locked here; the links from the cluster to the rest of the board (5V_SW feed, 1V1 / 3V3_D out) are left as
airwires for the autorouter.

On a routed board, follow with repair_conflicts.py: it rips the unlocked copper that now collides with the
clusters and strips the stubs left pointing at the parts' old positions.
usage: buck_patch.py in.kicad_pcb out.kicad_pcb
"""
import os
import sys
import pcbnew

MM, T = pcbnew.FromMM, pcbnew.ToMM
P = lambda x, y: pcbnew.VECTOR2I(MM(x), MM(y))

# ref -> (dx, dy, {net suffix: wanted side as unit vector}) ; the side picks the rotation
CLUSTERS = {
    "U2": dict(at=(184.0, 152.6), out="1V1", L="L1", cin="C9", cout=("C6", "C7"), rtop="R3", rbot="R4", rpg="R5"),
    "U3": dict(at=(173.5, 152.6), out="3V3_D", L="L2", cin="C13", cout=("C10", "C11"), rtop="R6", rbot="R7", rpg="R8"),
}
VIA_D, VIA_DRILL = 0.45, 0.2


def short(n):
    return n.split("/")[-1]


def pad_by_net(fp, net):
    return next(p for p in fp.Pads() if short(p.GetNetname()) == net)


def xy(p):
    q = p.GetPosition()
    return T(q.x), T(q.y)


def place(fp, x, y, net=None, toward=None):
    """Place fp at (x, y); when net/toward are given, pick the rotation that puts that net's pad on that side."""
    best = None
    for rot in (0, 90, 180, 270):
        fp.SetOrientationDegrees(rot)
        fp.SetPosition(P(x, y))
        if net is None:
            return
        px, py = xy(pad_by_net(fp, net))
        score = (px - x) * toward[0] + (py - y) * toward[1]
        if best is None or score > best[0]:
            best = (score, rot)
    fp.SetOrientationDegrees(best[1])
    fp.SetPosition(P(x, y))


def main(src, dst):
    # pcbnew falls back to default design rules when no .kicad_pro sits beside the board, and Save() then
    # writes those defaults out: refuse rather than silently loosen or tighten the rules
    if not os.path.exists(os.path.splitext(src)[0] + ".kicad_pro"):
        sys.exit(f"{src}: no matching .kicad_pro next to it")
    b = pcbnew.LoadBoard(src)
    fps = {f.GetReference(): f for f in b.GetFootprints()}
    nets = b.GetNetsByName()

    def net(name):
        for k in (name, "/Power/" + name):
            if k in nets:
                return nets[k]
        raise KeyError(name)

    def track(pts, name, w, layer=pcbnew.F_Cu):
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(P(x0, y0)); t.SetEnd(P(x1, y1)); t.SetWidth(MM(w)); t.SetLayer(layer)
            t.SetNet(net(name)); t.SetLocked(True); b.Add(t)

    def via(x, y, name):
        v = pcbnew.PCB_VIA(b)
        v.SetPosition(P(x, y)); v.SetWidth(MM(VIA_D)); v.SetDrill(MM(VIA_DRILL))
        v.SetNet(net(name)); v.SetLocked(True); b.Add(v)

    moved = [r for c, d in CLUSTERS.items() for r in (c, d["L"], d["cin"], *d["cout"], d["rtop"], d["rbot"], d["rpg"])]

    # place and route each cluster (coordinates relative to the IC centre)
    for ic, d in CLUSTERS.items():
        cx, cy = d["at"]
        out, sw, fb, pg = d["out"], "SW_" + ("1V1" if ic == "U2" else "3V3"), "FB_" + ("1V1" if ic == "U2" else "3V3"), \
            "PG_" + ("1V1" if ic == "U2" else "3V3")
        A = lambda dx, dy: (cx + dx, cy + dy)
        u = fps[ic]
        place(u, cx, cy, sw, (0, -1))                      # SW pin up, toward the inductor
        place(fps[d["L"]], *A(0, -3.1), sw, (0, 1))         # inductor above, SW pad facing the IC
        place(fps[d["cin"]], *A(-2.55, -0.45), "5V_SW", (1, 0))
        for k, c in enumerate(d["cout"]):
            place(fps[c], *A(2.9 + 2.1 * k, -3.1), out, (0, -1))
        place(fps[d["rbot"]], *A(0, 2.25), fb, (0, -1))
        place(fps[d["rtop"]], *A(1.1, 2.25), fb, (0, -1))
        place(fps[d["rpg"]], *A(2.2, 2.25), pg, (0, -1))

        pin = {short(p.GetNetname()) if short(p.GetNetname()) != "5V_SW" else ("VIN" if p.GetNumber() == "3" else "EN"):
               xy(p) for p in u.Pads()}
        lsw, lout = xy(pad_by_net(fps[d["L"]], sw)), xy(pad_by_net(fps[d["L"]], out))
        cin_v, cin_g = xy(pad_by_net(fps[d["cin"]], "5V_SW")), xy(pad_by_net(fps[d["cin"]], "GND"))
        co = [(xy(pad_by_net(fps[c], out)), xy(pad_by_net(fps[c], "GND"))) for c in d["cout"]]
        rb_fb, rb_g = xy(pad_by_net(fps[d["rbot"]], fb)), xy(pad_by_net(fps[d["rbot"]], "GND"))
        rt_fb = xy(pad_by_net(fps[d["rtop"]], fb))
        rp_pg = xy(pad_by_net(fps[d["rpg"]], pg))
        # pins are on a 0.5 mm pitch with 0.15 mm gaps: leave each pin at 0.2 mm, widen once clear of the row
        s0, v0, e0, g = pin[sw], pin["VIN"], pin["EN"], pin["GND"]
        track([s0, (s0[0], cy - 1.6)], sw, 0.2)
        track([(s0[0], cy - 1.6), (s0[0], lsw[1])], sw, 0.6)                              # SW -> L
        track([v0, (cx - 0.95, v0[1])], "5V_SW", 0.2)
        track([(cx - 0.95, v0[1]), (cin_v[0], v0[1])], "5V_SW", 0.4)                     # VIN -> Cin
        track([e0, (cx - 0.95, e0[1])], "5V_SW", 0.2)
        track([(cx - 0.95, e0[1]), (cin_v[0], e0[1]), cin_v], "5V_SW", 0.3)              # EN tied to VIN at Cin
        track([g, (cx + 0.95, g[1])], "GND", 0.2)
        track([(cx + 0.95, g[1]), (cx + 1.4, g[1]), co[0][1]], "GND", 0.4)               # GND pin -> Cout GND
        track([co[0][1], co[1][1]], "GND", 0.5)
        track([(lout[0], co[0][0][1]), co[0][0], co[1][0]], out, 0.6)                    # L out -> Cout
        track([pin[fb], (pin[fb][0], rb_fb[1]), rt_fb], fb, 0.15)                         # FB divider
        track([pin[pg], (pin[pg][0], cy + 1.15), (rp_pg[0], cy + 1.15), rp_pg], pg, 0.15)  # PG pull-up
        for vx, vy in [(cin_g[0] - 0.3, cin_g[1] + 1.0), (cin_g[0] + 0.35, cin_g[1] + 1.0)]:
            via(vx, vy, "GND"); track([cin_g, (vx, vy)], "GND", 0.3)
        for vx in (cx + 1.4, cx + 2.05):
            via(vx, cy - 0.1, "GND"); track([(cx + 1.4, g[1]), (vx, cy - 0.1)], "GND", 0.3)
        via(co[1][1][0] - 0.6, co[1][1][1] + 1.05, "GND")
        track([co[1][1], (co[1][1][0] - 0.6, co[1][1][1] + 1.05)], "GND", 0.3)
        via(rb_g[0], rb_g[1] + 0.65, "GND"); track([rb_g, (rb_g[0], rb_g[1] + 0.65)], "GND", 0.2)

    for r in moved:
        fps[r].SetLocked(True)
    b.Save(dst)
    print(f"moved {len(moved)} parts -> {dst}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
