#!/usr/bin/env python3
"""Dump the U12 (CABGA256) fan-out state of the work board for the fan-out re-plan.
usage: python3 notes/fanout/extract_fanout.py [board]  -> notes/fanout/fanout_data.json"""
import json, os, re, sys
import pcbnew

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
board = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "kicad/work/usb3-sdr.kicad_pcb")
T = pcbnew.ToMM
b = pcbnew.LoadBoard(board)
u12 = b.FindFootprintByReference("U12")
bus = set(json.load(open("/tmp/claude-1000/-home-user1/d098a269-bdde-482f-8b73-8a52833e662c/scratchpad/bus_nets.json")))
lpf = {}
for line in open(os.path.join(ROOT, "gateware/constraints/usb3sdr.lpf")):
    m = re.match(r'\s*LOCATE\s+COMP\s+"([^"]+)"\s+SITE\s+"([A-T]\d+)"', line)
    if m:
        lpf[m.group(2)] = m.group(1)
PWR = {"GND", "1V1", "3V3_D", "2V5", "1V8_A", "1V8_D"}
balls = {}
for p in u12.Pads():
    n = p.GetNetname()
    q = p.GetPosition()
    if n.startswith("unconnected-") or not n:
        role = "unused"
    elif n in bus:
        role = "bus_ft" if n.startswith(("FT_", "/FT")) or "FT_" in n else "bus_adc"
    elif n == "GND":
        role = "gnd"
    elif any(n.endswith(k) for k in PWR) or n in PWR:
        role = "power"
    else:
        role = "signal"
    balls[p.GetNumber()] = dict(xy=[round(T(q.x), 3), round(T(q.y), 3)], net=n, role=role,
                                lpf_signal=lpf.get(p.GetNumber()))
x0, y0, x1, y1 = 155.5, 116.5, 170.5, 131.5
vias, tracks = [], []
for t in b.GetTracks():
    if t.Type() == pcbnew.PCB_VIA_T:
        q = t.GetPosition()
        if x0 <= T(q.x) <= x1 and y0 <= T(q.y) <= y1:
            vias.append(dict(xy=[round(T(q.x), 3), round(T(q.y), 3)], net=t.GetNetname(), locked=t.IsLocked(),
                             pad=round(T(t.GetWidth(pcbnew.F_Cu)), 3), drill=round(T(t.GetDrillValue()), 3),
                             uuid=t.m_Uuid.AsString()))
    else:
        s, e = t.GetStart(), t.GetEnd()
        if any(x0 <= T(p.x) <= x1 and y0 <= T(p.y) <= y1 for p in (s, e)):
            tracks.append(dict(a=[round(T(s.x), 3), round(T(s.y), 3)], b=[round(T(e.x), 3), round(T(e.y), 3)],
                               w=round(T(t.GetWidth()), 3), layer=b.GetLayerName(t.GetLayer()),
                               net=t.GetNetname(), locked=t.IsLocked()))
zones = []
for z in b.Zones():
    if z.GetLayerName() in ("In1.Cu", "In2.Cu") or z.IsOnLayer(pcbnew.In2_Cu):
        bb = z.GetBoundingBox()
        zones.append(dict(net=z.GetNetname(), layer="+".join(b.GetLayerName(l) for l in z.GetLayerSet().Seq()), priority=z.GetAssignedPriority(),
                          bbox=[round(T(bb.GetX()), 2), round(T(bb.GetY()), 2), round(T(bb.GetRight()), 2),
                                round(T(bb.GetBottom()), 2)],
                          outline=[[round(T(c.x), 2), round(T(c.y), 2)] for c in
                                   [z.Outline().CVertex(i) for i in range(z.Outline().TotalVertices())]]))
ds = b.GetDesignSettings()
out = dict(board=os.path.relpath(board, ROOT), balls=balls, vias=vias, tracks=tracks, inner_zones=zones,
           ball_pad_mm=0.32, pitch_mm=0.8,
           rules=dict(track=0.15, clearance=round(T(ds.m_MinClearance), 3)))
json.dump(out, open(os.path.join(ROOT, "notes/fanout/fanout_data.json"), "w"), indent=1)
from collections import Counter
print(Counter(v["role"] for v in balls.values()))
print("vias", len(vias), Counter(v["net"] for v in vias).most_common(8), "locked", sum(v["locked"] for v in vias))
print("tracks", len(tracks), Counter((t["layer"]) for t in tracks))
print([(z["net"], z["layer"], z["priority"], z["bbox"]) for z in zones])

# parts and pads in the U12 <-> U11 / ADC region (for decap relocation and corridor planning)
X0, Y0, X1, Y1 = 128.0, 105.0, 200.0, 160.0
parts = {}
for f in b.GetFootprints():
    q = f.GetPosition()
    if not (X0 < T(q.x) < X1 and Y0 < T(q.y) < Y1):
        continue
    cy = f.GetCourtyard(pcbnew.F_CrtYd).BBox() if f.GetCourtyard(pcbnew.F_CrtYd).OutlineCount() else f.GetBoundingBox(False)
    parts[f.GetReference()] = dict(value=f.GetValue(), xy=[round(T(q.x), 3), round(T(q.y), 3)],
                                   rot=f.GetOrientationDegrees(), locked=f.IsLocked(),
                                   courtyard=[round(T(cy.GetX()), 2), round(T(cy.GetY()), 2),
                                              round(T(cy.GetRight()), 2), round(T(cy.GetBottom()), 2)],
                                   pads={p.GetNumber(): dict(xy=[round(T(p.GetPosition().x), 3),
                                                                 round(T(p.GetPosition().y), 3)],
                                                             net=p.GetNetname()) for p in f.Pads()}
                                   if f.GetReference() != "U12" else "see balls")
out["parts"] = parts
json.dump(out, open(os.path.join(ROOT, "notes/fanout/fanout_data.json"), "w"), indent=1)
print("parts", len(parts))
