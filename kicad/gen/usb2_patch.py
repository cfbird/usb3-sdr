#!/usr/bin/env python3
"""Open a path for the FT601 USB 2 pair (U11-23 D+, U11-25 D-) and route it to the USB-C connector J1.

FT601 pin 24 (3V3_D) sits between D+ and D-. The autorouter put its via right at the pins, which closes off D+.
This moves that via ~1.2 mm out: pin 24's trace runs between the pair lines (0.2 mm gap each side) to a via placed
where D+ has already turned away. D+ and D- are then routed with grid_route.py (they swap order between U11 and J1,
so one of them changes layer).
usage: usb2_patch.py board.kicad_pcb   (edited in place)
"""
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from grid_route import route                                   # noqa: E402
from repair_conflicts import dangling, delete_by_uuid, refill  # noqa: E402

T, MM = pcbnew.ToMM, pcbnew.FromMM
P = lambda x, y: pcbnew.VECTOR2I(MM(x), MM(y))
BOX = (186.0, 120.0, 198.0, 131.0)
DP, DN = "/USB 3 bridge/USB_D_P", "/USB 3 bridge/USB_D_N"
# (net, box): the autorouter's copper to clear first. Pin 24's escape, and the VBUS branch to R47 (VBUS detect
# through 1k, signal current only) whose via sits exactly where the pair has to change layer in front of J1.
PAIR_CORRIDOR = (188.9, 124.3, 195.3, 127.8)     # in front of U11-23..25 out to J1-2/3, kept for the pair
CLEAR = [("3V3_D", (188.3, 124.85, 189.6, 125.15)), ("VBUS", (192.5, 123.5, 195.0, 128.1))]


def main(path):
    if not os.path.exists(os.path.splitext(path)[0] + ".kicad_pro"):
        sys.exit(f"{path}: no matching .kicad_pro next to it")
    b = pcbnew.LoadBoard(path)
    old = []
    for t in b.GetTracks():
        pts = [t.GetPosition()] if t.Type() == pcbnew.PCB_VIA_T else [t.GetStart(), t.GetEnd()]
        for net, (x0, y0, x1, y1) in CLEAR:
            if t.GetNetname() == net and not t.IsLocked() and all(x0 < T(p.x) < x1 and y0 < T(p.y) < y1 for p in pts):
                old.append(t.m_Uuid.AsString())
    del b
    n = delete_by_uuid(path, set(old))
    while True:
        dead = dangling(path)
        if not dead:
            break
        n += delete_by_uuid(path, dead)
    print(f"cleared {n} items (pin-24 escape, VBUS sense branch)")

    b = pcbnew.LoadBoard(path)
    pin24 = next(p for p in b.FindFootprintByReference("U11").Pads() if p.GetNumber() == "24")
    px, py = T(pin24.GetPosition().x), T(pin24.GetPosition().y)
    net = b.FindNet("3V3_D")
    for (x0, y0), (x1, y1) in [((px, py), (px + 1.96, py)), ((px + 1.96, py), (px + 2.06, py + 0.1))]:
        t = pcbnew.PCB_TRACK(b); t.SetStart(P(x0, y0)); t.SetEnd(P(x1, y1)); t.SetWidth(MM(0.2))
        t.SetLayer(pcbnew.F_Cu); t.SetNet(net); t.SetLocked(True); b.Add(t)
    v = pcbnew.PCB_VIA(b); v.SetPosition(P(px + 2.06, py + 0.1)); v.SetWidth(MM(0.45)); v.SetDrill(MM(0.2))
    v.SetNet(net); v.SetLocked(True); b.Add(v)      # drops straight into the In2 3V3_D plane
    # VBUS sense first: R47 sits right above the pair's exit, and once D- runs past it R47 has no way out
    r = route(b, "VBUS", "R47-1", "net", 0.2, 0.17, (186.0, 118.0, 198.0, 134.0), keepout=[PAIR_CORRIDOR])
    if r is None:
        sys.exit("no path for the VBUS sense line")
    print(f"VBUS -> R47: {r[0]} tracks, {r[1]} vias")
    for net_name, frm, to in ((DN, "U11-25", "J1-2"), (DP, "U11-23", "J1-3")):   # D- has the tighter entry
        r = route(b, net_name, frm, to, 0.2, 0.17, BOX)
        if r is None:
            sys.exit(f"no path for {net_name}")
        print(f"{net_name}: {r[0]} tracks, {r[1]} vias")
    b.Save(path)
    refill(path)


if __name__ == "__main__":
    main(sys.argv[1])
