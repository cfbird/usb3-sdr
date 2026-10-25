#!/usr/bin/env python3
"""Dump the U11 (FT601) escape region of the work board for the U11 escape plan.
usage: python3 notes/u11/extract_u11.py [board]  -> notes/u11/u11_data.json
Box: x 164-202, y 106-142 (U11, the U12 east side, the corridor between them)."""
import json, os, subprocess, sys, tempfile
import pcbnew

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
board = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "kicad/work/usb3-sdr.kicad_pcb")
X0, Y0, X1, Y1 = 164, 106, 202, 142
T = pcbnew.ToMM
r = lambda v: round(v, 3)
xy = lambda p: [r(T(p.x)), r(T(p.y))]
inbox = lambda p: X0 <= T(p.x) <= X1 and Y0 <= T(p.y) <= Y1

out = tempfile.mktemp(suffix=".json")
subprocess.run(["kicad-cli", "pcb", "drc", "--format", "json", "-o", out, board], capture_output=True)
drc = json.load(open(out)); os.unlink(out)
opens = {}
for u in drc["unconnected_items"]:
    net = u["items"][0]["description"].split("[")[1].split("]")[0]
    opens.setdefault(net, []).append([[i["description"], [i["pos"]["x"], i["pos"]["y"]]] for i in u["items"]])

b = pcbnew.LoadBoard(board)
LN = lambda l: b.GetLayerName(l)
def pad(p):
    bb = p.GetBoundingBox()
    return {"num": p.GetNumber(), "xy": xy(p.GetPosition()), "size": [r(T(p.GetSize().x)), r(T(p.GetSize().y))],
            "rot": r(p.GetOrientationDegrees()), "net": p.GetNetname(),
            "layers": [LN(l) for l in p.GetLayerSet().CuStack()],
            "bbox": [r(T(bb.GetX())), r(T(bb.GetY())), r(T(bb.GetRight())), r(T(bb.GetBottom()))]}
parts = {}
for f in b.GetFootprints():
    ps = [p for p in f.Pads() if inbox(p.GetPosition())]
    if not ps:
        continue
    cy = f.GetCourtyard(f.GetSide() if hasattr(f, "GetSide") else pcbnew.F_CrtYd)
    cb = f.GetBoundingBox(False)
    parts[f.GetReference()] = {"xy": xy(f.GetPosition()), "rot": r(f.GetOrientationDegrees()),
        "side": "B" if f.IsFlipped() else "F", "locked": f.IsLocked(), "value": f.GetValue(),
        "bbox_no_text": [r(T(cb.GetX())), r(T(cb.GetY())), r(T(cb.GetRight())), r(T(cb.GetBottom()))],
        "pads": [pad(p) for p in (f.Pads() if f.GetReference() != "U12" else ps)]}
tracks, vias = [], []
for t in b.GetTracks():
    if t.Type() == pcbnew.PCB_VIA_T:
        if inbox(t.GetPosition()):
            vias.append({"uuid": t.m_Uuid.AsString(), "net": t.GetNetname(), "xy": xy(t.GetPosition()),
                         "size": r(T(t.GetWidth(pcbnew.F_Cu))), "drill": r(T(t.GetDrill())), "locked": t.IsLocked()})
    elif inbox(t.GetStart()) or inbox(t.GetEnd()):
        tracks.append({"uuid": t.m_Uuid.AsString(), "net": t.GetNetname(), "layer": LN(t.GetLayer()),
                       "a": xy(t.GetStart()), "b": xy(t.GetEnd()), "w": r(T(t.GetWidth())), "locked": t.IsLocked()})
zones = []
for z in b.Zones():
    bb = z.GetBoundingBox()
    if T(bb.GetRight()) < X0 or T(bb.GetX()) > X1 or T(bb.GetBottom()) < Y0 or T(bb.GetY()) > Y1:
        continue
    o = z.Outline()
    zones.append({"name": z.GetZoneName(), "net": z.GetNetname(), "rule_area": z.GetIsRuleArea(),
                  "layers": [LN(l) for l in z.GetLayerSet().CuStack()],
                  "outline": [xy(o.CVertex(i)) for i in range(o.TotalVertices())]})
ft_open = {n: v for n, v in opens.items() if "FT_" in n}
d = {"box": [X0, Y0, X1, Y1],
     "rules": {"clearance_default": 0.127, "track_default": 0.15, "via": [0.45, 0.2], "min_via": [0.4, 0.2],
               "hole_clearance": 0.25, "hole_to_hole": 0.25, "PWR_class": "clearance 0.15, width 0.4",
               "layers": "F.Cu signal, In1.Cu GND plane, In2.Cu power islands, B.Cu signal"},
     "open_nets": opens, "ft_open_nets": sorted(ft_open), "parts": parts, "tracks": tracks, "vias": vias, "zones": zones}
json.dump(d, open(os.path.join(ROOT, "notes/u11/u11_data.json"), "w"), indent=0)
print(len(opens), "open nets,", len(ft_open), "FT;", len(parts), "parts,", len(tracks), "tracks,", len(vias), "vias,", len(zones), "zones")
