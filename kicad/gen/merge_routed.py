#!/usr/bin/env python3
"""Merge an autorouted board back onto the pre-route board.

DeepPCB's output rewrites locked copper (it re-tidies corners and changes widths). For every net whose locked
copper lies outside the FPGA BGA (the hand-routed RF chain, USB and clock nets) this restores the original copper
and drops the autorouter's copper on that net. The BGA fan-out and every other net keep the autorouter's version.
Placement and zones come from the original board.
usage: merge_routed.py original.kicad_pcb routed.kicad_pcb out.kicad_pcb
"""
import os
import sys
import pcbnew

T = pcbnew.ToMM
PARTIAL = ("GND", "ADC_VCM")


def main(orig_f, routed_f, out_f):
    # pcbnew falls back to default design rules when no .kicad_pro sits beside the board, and Save() then
    # writes those defaults out: refuse rather than silently loosen or tighten the rules
    if not os.path.exists(os.path.splitext(orig_f)[0] + ".kicad_pro"):
        sys.exit(f"{orig_f}: no matching .kicad_pro next to it")
    # read the routed copper into plain tuples first: SWIG wrappers of one board go stale once another is edited
    r = pcbnew.LoadBoard(routed_f)
    routed = []
    for t in r.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            routed.append(("via", t.GetNetname(), t.GetPosition(), t.GetWidth(pcbnew.F_Cu), t.GetDrill(),
                           t.GetLayerSet().Seq()[0], t.GetLayerSet().Seq()[-1]))
        else:
            routed.append(("trk", t.GetNetname(), t.GetStart(), t.GetEnd(), t.GetWidth(), t.GetLayer()))
    routed = [(k, n, *[pcbnew.VECTOR2I(v.x, v.y) if hasattr(v, "x") else v for v in rest]) for k, n, *rest in routed]

    a = pcbnew.LoadBoard(orig_f)
    bga = a.FindFootprintByReference("U12").GetBoundingBox(False)
    bga.Inflate(pcbnew.FromMM(0.5))

    def in_bga(t):
        pts = (t.GetPosition(),) if t.Type() == pcbnew.PCB_VIA_T else (t.GetStart(), t.GetEnd())
        return all(bga.Contains(p) for p in pts)

    # nets the hand routing finished (RF chain, USB, ADC input) come only from the original; nets it left
    # incomplete (GND, ADC_VCM) get the original locked copper plus the autorouter's copper
    critical = {t.GetNetname() for t in a.GetTracks() if t.IsLocked() and not in_bga(t)} - set(PARTIAL)
    for t in [t for t in a.GetTracks() if t.GetNetname() not in critical | set(PARTIAL)]:
        a.Remove(t)
    added = 0
    for item in routed:                    # take everything else from the routed board
        if item[1] in critical:
            continue
        if item[0] == "via":
            _, n, pos, w, drill, top, bot = item
            v = pcbnew.PCB_VIA(a); v.SetPosition(pos); v.SetWidth(w); v.SetDrill(drill); v.SetLayerPair(top, bot)
        else:
            _, n, s, e, w, layer = item
            v = pcbnew.PCB_TRACK(a); v.SetStart(s); v.SetEnd(e); v.SetWidth(w); v.SetLayer(layer)
        v.SetNet(a.FindNet(n)); a.Add(v); added += 1
    # drop exact duplicates (the routed board repeats some original GND / ADC_VCM copper), then refill zones
    seen, dup = set(), 0
    for t in sorted(a.GetTracks(), key=lambda t: not t.IsLocked()):
        k = (t.Type(), t.GetNetname(), t.GetLayer(), t.GetPosition().x, t.GetPosition().y) if t.Type() == pcbnew.PCB_VIA_T \
            else (t.Type(), t.GetNetname(), t.GetLayer(), t.GetWidth(),
                  tuple(sorted([(t.GetStart().x, t.GetStart().y), (t.GetEnd().x, t.GetEnd().y)])))
        if k in seen and not t.IsLocked():
            a.Remove(t); dup += 1
        seen.add(k)
    pcbnew.ZONE_FILLER(a).Fill(a.Zones())
    a.Save(out_f)
    print(f"removed {dup} duplicate items, refilled {len(a.Zones())} zones")
    print(f"critical nets restored: {len(critical)}; routed items taken: {added} -> {out_f}")
    for n in sorted(critical):
        print("  ", n)


if __name__ == "__main__":
    main(*sys.argv[1:4])
