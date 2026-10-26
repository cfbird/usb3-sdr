#!/usr/bin/env python3
"""Report digital copper that runs close to the RF signal path on the same outer layer.

RF path: every /RF front end/ net except the relay coils and FET gates, plus ADC_VINP/VINN.
Aggressors: every other net except GND, power rails and DC / slow nets (QUIET). Tracks are sampled every 0.1 mm; digital vias count as
a point with their pad radius. A pair is listed when some edge-to-edge gap is below --gap (default 0.65 mm, about
3 x the 0.21 mm F.Cu/B.Cu-to-plane dielectric), with the run length inside that band and the smallest gap.
usage: python3 kicad/gen/rf_spacing.py board.kicad_pcb [--gap 0.65] [--base other.kicad_pcb]
  --base: also list which pairs are new / gone compared with another board.
Exit code 1 if any pair is listed (with --base: only if a new or worse pair is listed).
"""
import collections
import math
import re
import sys

import pcbnew

T = pcbnew.ToMM
NOT_RF = ("K1_COIL", "K2_COIL", "Q1_G", "Q2_G")
POWER = re.compile(r"^(GND|\d+V\d*(_\w+)?|VBUS|5V_\w+|unconnected.*)$")
# DC / slow nets, not aggressors: ADC references, relay coils and drives, FET gates, LNA enable
QUIET = re.compile(r"^(ADC_VCM|ADC_VREF|ADC_RBIAS|K\d_COIL|Q\d_G|RLY_\w+|LNA_EN)$")


def is_rf(n):
    return ("/RF front end/" in n and not n.endswith(NOT_RF)) or n in ("ADC_VINP", "ADC_VINN")


def is_dig(n):
    return n and not is_rf(n) and not POWER.match(n.split("/")[-1]) and not QUIET.match(n.split("/")[-1])


def dps(p, a, b):
    ax, ay = b[0] - a[0], b[1] - a[1]
    L = ax * ax + ay * ay
    u = 0 if L == 0 else max(0, min(1, ((p[0] - a[0]) * ax + (p[1] - a[1]) * ay) / L))
    return math.hypot(p[0] - a[0] - u * ax, p[1] - a[1] - u * ay)


def items(b):
    out = []
    for x in b.GetTracks():
        n = x.GetNetname()
        if x.Type() == pcbnew.PCB_VIA_T:
            p = x.GetPosition()
            q = (T(p.x), T(p.y))
            for L in ("F.Cu", "B.Cu"):
                out.append((n, L, q, q, T(x.GetWidth(pcbnew.F_Cu)) / 2))
        else:
            a, c = x.GetStart(), x.GetEnd()
            out.append((n, b.GetLayerName(x.GetLayer()), (T(a.x), T(a.y)), (T(c.x), T(c.y)), T(x.GetWidth()) / 2))
    for f in b.GetFootprints():
        for p in f.Pads():
            if not is_rf(p.GetNetname()):
                continue
            bb = p.GetBoundingBox()
            q = (T(p.GetPosition().x), T(p.GetPosition().y))
            r = min(T(bb.GetWidth()), T(bb.GetHeight())) / 2
            for L in ("F.Cu", "B.Cu"):
                if p.IsOnLayer(pcbnew.F_Cu if L == "F.Cu" else pcbnew.B_Cu):
                    out.append((p.GetNetname(), L, q, q, r))
    return out


def scan(path, gap):
    s = items(pcbnew.LoadBoard(path))
    rf = [x for x in s if is_rf(x[0])]
    res = collections.defaultdict(lambda: [0.0, 99.0, None])
    for n, L, a, b, r in s:
        if not is_dig(n):
            continue
        near = [x for x in rf if x[1] == L and min(x[2][0], x[3][0]) - 3 < max(a[0], b[0])
                and min(a[0], b[0]) - 3 < max(x[2][0], x[3][0]) and min(x[2][1], x[3][1]) - 3 < max(a[1], b[1])
                and min(a[1], b[1]) - 3 < max(x[2][1], x[3][1])]
        if not near:
            continue
        ln = math.dist(a, b)
        k = max(1, int(ln / 0.1))
        for i in range(k + 1):
            q = (a[0] + (b[0] - a[0]) * i / k, a[1] + (b[1] - a[1]) * i / k)
            for m, _, c, d, r2 in near:
                g = dps(q, c, d) - r - r2
                if g < gap:
                    e = res[(n.split("/")[-1], m.split("/")[-1], L)]
                    e[0] += ln / (k + 1)
                    if g < e[1]:
                        e[1], e[2] = g, q
    return res


def main(a):
    gap = float(a[a.index("--gap") + 1]) if "--gap" in a else 0.65
    base = scan(a[a.index("--base") + 1], gap) if "--base" in a else None
    res = scan(a[0], gap)
    print(f"digital copper within {gap} mm of RF-path copper, same layer: {len(res)} pairs")
    bad = 0
    for k, (ln, g, q) in sorted(res.items(), key=lambda kv: kv[1][1]):
        tag = ""
        if base is not None:
            tag = "NEW " if k not in base else ("WORSE " if g < base[k][1] - 0.01 or ln > base[k][0] + 0.5 else "")
            bad += bool(tag)
        else:
            bad += 1
        print(f"  {tag:6s}{k[0]:14s} {k[1]:13s} {k[2]}  run {ln:5.2f} mm  min gap {g:.2f} @({q[0]:.2f},{q[1]:.2f})")
    if base is not None:
        for k in sorted(set(base) - set(res)):
            print(f"  gone  {k[0]:14s} {k[1]:13s} {k[2]}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main(sys.argv[1:])
