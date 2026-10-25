#!/usr/bin/env python3
"""Lay out the ADC sample clock: LMK61E2 (U9) -> AC caps C61/C62 -> 100R termination R43 -> AD9649 CLK+/CLK- (U8-1/2),
all on F.Cu over the In1 GND plane, no vias.

Polarity is swapped in the schematic (OUTN -> C62 -> CLK+, OUTP -> C61 -> CLK-), which makes the route planar:
the pair leaves the ADC clock pins southward, R43 sits right under the pins, the pair turns east just above the LMK's
top pads, then runs south down the LMK's east side, where C62 and C61 sit in-line before the OUTN / OUTP pads.
To make room: R28 (ADC D2 series R, which sat under the clock pins) moves to the ADC resistor column, and the
autorouter's local 1V8_A, 3V3_A and LMK_SDA copper in the LMK east channel is ripped and re-routed afterwards.
Run after sync_pad_nets.py has applied the polarity swap.
usage: adc_clock_patch.py board.kicad_pcb   (edited in place)
"""
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from grid_route import connect_net                             # noqa: E402
from repair_conflicts import dangling, delete_by_uuid, refill  # noqa: E402

T, MM = pcbnew.ToMM, pcbnew.FromMM
P = lambda x, y: pcbnew.VECTOR2I(MM(x), MM(y))
CLKP, CLKN = "/ADC and clock/ADC_CLKP", "/ADC and clock/ADC_CLKN"
OUTP, OUTN = "/ADC and clock/LMK_OUTP", "/ADC and clock/LMK_OUTN"
# (net, box) of unlocked copper to clear: the clock nets anywhere, plus the local pieces in the LMK east channel
CLEAR = [(CLKP, None), (CLKN, None), (OUTP, None), (OUTN, None),
         ("1V8_A", (140.0, 143.3, 147.6, 149.1)),          # U8-3 escape, its via chain and the trunk stub across
         ("3V3_A", (144.2, 149.8, 145.4, 151.0)),    # FB2-1 escape via
         ("LMK_SDA", (140.5, 146.5, 144.8, 151.8)),
         ("ADC_VCM", (144.3, 147.6, 145.2, 148.4)),               # via sitting on the outer (N) track line
         ("LMK_SDA", (144.3, 150.9, 145.2, 152.3)), ("3V3_D", (145.2, 150.9, 146.4, 152.3)),   # R44 pad copper
         ("/ADC and clock/3V3_CLK", (146.0, 149.2, 147.7, 151.0)),
         ("GND", (146.1, 147.1, 146.75, 147.8))]                    # C49's GND via, in the way of the moved R36               # FB2-2 escape (FB2 moves 0.5 mm east)
MOVED = ("R28", "R36", "R44", "FB2", "R43", "C61", "C62")
W, CLR = 0.15, 0.15                                         # clock track width; the LVDS100 class clearance


def main(path):
    if not os.path.exists(os.path.splitext(path)[0] + ".kicad_pro"):
        sys.exit(f"{path}: no matching .kicad_pro next to it")
    b = pcbnew.LoadBoard(path)
    dead = set()
    moved_pads = [q for r in MOVED for q in b.FindFootprintByReference(r).Pads()]
    for t in b.GetTracks():
        if t.IsLocked():
            continue
        ends = [t.GetPosition()] if t.Type() == pcbnew.PCB_VIA_T else [t.GetStart(), t.GetEnd()]
        if any(q.HitTest(e) for q in moved_pads for e in ends):
            dead.add(t.m_Uuid.AsString())     # copper ending on a part that is about to move
        pts = [t.GetPosition()] if t.Type() == pcbnew.PCB_VIA_T else [t.GetStart(), t.GetEnd()]
        for net, box in CLEAR:
            if t.GetNetname() == net and (box is None or
                                          all(box[0] < T(p.x) < box[2] and box[1] < T(p.y) < box[3] for p in pts)):
                dead.add(t.m_Uuid.AsString())
    del b
    n = delete_by_uuid(path, dead)
    while True:
        d = dangling(path)
        if not d:
            break
        n += delete_by_uuid(path, d)
    print(f"cleared {n} items")

    b = pcbnew.LoadBoard(path)
    fp = b.FindFootprintByReference

    def place(ref, x, y, rot):
        f = fp(ref); f.SetOrientationDegrees(rot); f.SetPosition(P(x, y)); f.SetLocked(True)
        return {p.GetNumber(): (T(p.GetPosition().x), T(p.GetPosition().y)) for p in f.Pads()}

    place("R28", 145.5, 140.0, 0)                 # free spot in the ADC series-R column, next to U8-9 (D2_R)
    for ref, dx in (("R36", 0.7), ("R44", 0.8), ("FB2", 0.5)):   # widen the LMK east channel
        f = fp(ref); q = f.GetPosition(); place(ref, T(q.x) + dx, T(q.y), f.GetOrientationDegrees())
    r43 = place("R43", 139.26, 145.0, 0)          # pad 1 = CLKP (west), pad 2 = CLKN (east)
    c62 = place("C62", 144.3, 148.35, 90)         # P leg: pad 2 (CLKP) up, pad 1 (LMK_OUTN) down
    c61 = place("C61", 144.3, 151.35, 90)         # N leg: pad 2 (CLKN) up, pad 1 (LMK_OUTP) down
    assert c62["2"][1] < c62["1"][1] and c61["2"][1] < c61["1"][1], "cap orientation"
    u8 = {p.GetNumber(): (T(p.GetPosition().x), T(p.GetPosition().y)) for p in fp("U8").Pads()}
    u9 = {p.GetNumber(): (T(p.GetPosition().x), T(p.GetPosition().y)) for p in fp("U9").Pads()}

    def track(pts, net):
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(b); t.SetStart(P(x0, y0)); t.SetEnd(P(x1, y1)); t.SetWidth(MM(W))
            t.SetLayer(pcbnew.F_Cu); t.SetNet(b.FindNet(net)); t.SetLocked(True); b.Add(t)

    # Geometry (checked against pad boxes and Fab outlines): the east run passes under R27 (pad bottom 145.79)
    # and over the LMK top pads (146.74). Caps sit at x = 144.3: courtyards just clear the LMK's, 0.45 mm body gap.
    # P (inside) leaves x = 143.85 below U9-6 and steps onto C62; N (outside) runs at 144.835, clear of the moved
    # R36 (moved), C62 and the moved FB2 (pad from x = 145.275) all the way down, then steps in onto C61.
    yN, yP = 146.15, 146.45                       # east run: N inside (north), P outside (south)
    # ADC pins -> R43 (P jogs 0.5 mm west so a 0402 fits across the pair)
    track([u8["1"], (u8["1"][0], 144.2), (r43["1"][0], 144.7), r43["1"]], CLKP)
    track([u8["2"], (u8["2"][0], 144.2), (r43["2"][0], 144.45), r43["2"]], CLKN)
    # R43 -> east run -> south run -> caps
    track([r43["1"], (r43["1"][0], yP), (143.55, yP), (143.85, yP + 0.3), (143.85, 147.0), (144.3, 147.45),
           c62["2"]], CLKP)
    track([r43["2"], (r43["2"][0], yN), (144.235, yN), (144.835, yN + 0.6), (144.835, 150.3), (144.45, 150.685),
           c61["2"]], CLKN)
    track([c62["1"], (143.85, c62["1"][1] + 0.45), (143.13, u9["5"][1]), u9["5"]], OUTN)   # leaves westward: N is 0.15 away
    track([c61["1"], (c61["1"][0], u9["4"][1] - 0.35), (u9["4"][0] + 0.35, u9["4"][1]), u9["4"]], OUTP)

    b.Save(path)
    # re-route what was cleared, around the now-locked clock, until DRC shows each net whole again
    for net, w, box in (("1V8_A", 0.2, (134.0, 136.0, 152.0, 158.0)),
                        ("3V3_A", 0.2, (128.0, 140.0, 152.0, 158.0)),
                        ("/ADC and clock/3V3_CLK", 0.2, (134.0, 144.0, 152.0, 158.0)),
                        ("3V3_D", 0.2, (140.0, 144.0, 152.0, 156.0)),
                        ("LMK_SDA", 0.15, (136.0, 140.0, 168.0, 156.0)),
                        ("ADC_VCM", 0.15, (130.0, 136.0, 152.0, 152.0)),
                        ("GND", 0.2, (142.0, 144.0, 150.0, 151.0))):
        print(f"{net}:", "connected" if connect_net(path, net, box, w, 0.16) else "STILL OPEN", flush=True)
    # strip what the rip-up and re-routes left hanging (half-connected vias, stubs)
    while True:
        d = dangling(path)
        if not d:
            break
        delete_by_uuid(path, d)
    refill(path)


if __name__ == "__main__":
    main(sys.argv[1])
