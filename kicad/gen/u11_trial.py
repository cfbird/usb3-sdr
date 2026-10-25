#!/usr/bin/env python3
"""Try a routing plan (moves, rips, explicit tracks and vias) on a throw-away copy of the work board and report what
KiCad's real zone fill and DRC say. Written for the U11 (FT601) escape plan; works for any plan of this shape:

  {"moves": {REF: {"xy": [x, y], "rot": deg}},          parts to move (apply_moves.py: their old copper is ripped)
   "rip":   [uuid, ...],                                  existing tracks / vias to delete (uuids from u11_data.json)
   "rip_nets": [regex, ...],                              delete all unlocked copper of matching nets
   "tracks": [{"net", "layer", "w", "pts": [[x, y], ...]}],   polyline per entry, F.Cu or B.Cu
   "vias":  [{"net", "xy": [x, y], "size": 0.45, "drill": 0.2}]}

Order: rip, moves (+ rip of copper the moves invalidate), add tracks/vias, fill, DRC. Prints:
  - copper DRC errors (shorts, clearance, hole clearance, crossing, courtyards, edge) not present on the work board;
  - unconnected count, nets the plan closed, nets it broke (open now, complete before), FT nets still open;
  - plan items DRC calls dangling;
  - agy_timing_check.py result for FT601 / ADC.
The work board is never touched.
usage: python3 kicad/gen/u11_trial.py plan.json [--keep DIR] [--base DIR]   (base: board dir to start from, default kicad/work)
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import pcbnew

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GEN = os.path.join(ROOT, "kicad/gen")
WORK = os.path.join(ROOT, "kicad/work")
sys.path.insert(0, GEN)
from repair_conflicts import delete_by_uuid, drc, refill  # noqa: E402

MM = pcbnew.FromMM
COPPER = {"shorting_items", "clearance", "hole_clearance", "hole_to_hole", "tracks_crossing", "courtyards_overlap",
          "copper_edge_clearance", "solder_mask_bridge", "via_diameter", "track_width", "annular_width",
          "drill_out_of_range", "items_not_allowed", "npth_inside_courtyard", "pth_inside_courtyard"}


def key(v):
    return (v["type"], tuple(sorted(round(i["pos"]["x"], 2) for i in v["items"])),
            tuple(sorted(round(i["pos"]["y"], 2) for i in v["items"])))


def opens(d):
    out = {}
    for u in d["unconnected_items"]:
        m = re.search(r"\[([^\]]+)\]", u["items"][0]["description"])
        out[m.group(1) if m else "?"] = out.get(m.group(1) if m else "?", 0) + 1
    return out


def main(plan_path, keep=None, work=WORK):
    plan = json.load(open(plan_path))
    tmp = keep or tempfile.mkdtemp(prefix="u11trial_")
    os.makedirs(tmp, exist_ok=True)
    for f in os.listdir(work):
        s = os.path.join(work, f)
        if f.endswith((".kicad_pcb", ".kicad_pro")) or f.endswith(".kicad_sch") or f == "fp-lib-table" \
                or f == "sym-lib-table":
            d = os.path.join(tmp, f)
            if os.path.lexists(d):
                os.unlink(d)
            (shutil.copy if f.endswith((".kicad_pcb", ".kicad_pro")) else
             (lambda a, b: os.symlink(os.path.realpath(a), b)))(s, d)
    pcb = os.path.join(tmp, "usb3-sdr.kicad_pcb")
    base = drc(os.path.join(work, "usb3-sdr.kicad_pcb"))

    rip = set(plan.get("rip", []))
    if plan.get("rip_nets"):
        b = pcbnew.LoadBoard(pcb)
        for t in b.GetTracks():
            if not t.IsLocked() and any(re.search(p, t.GetNetname()) for p in plan["rip_nets"]):
                rip.add(t.m_Uuid.AsString())
        del b
    n_rip = delete_by_uuid(pcb, rip) if rip else 0
    if plan.get("moves"):
        mp = os.path.join(tmp, "_moves.json")
        json.dump({"moves": plan["moves"]}, open(mp, "w"))
        r = subprocess.run([sys.executable, os.path.join(GEN, "apply_moves.py"), mp, pcb], capture_output=True,
                           text=True)
        print(r.stdout.strip() or r.stderr.strip()[-400:])

    b = pcbnew.LoadBoard(pcb)
    nets = b.GetNetsByName()
    added, bad = [], []
    for t in plan.get("tracks", []):
        if t["net"] not in nets:
            bad.append(t["net"]); continue
        layer = b.GetLayerID(t["layer"])
        for p, q in zip(t["pts"], t["pts"][1:]):
            s = pcbnew.PCB_TRACK(b)
            s.SetStart(pcbnew.VECTOR2I(MM(p[0]), MM(p[1]))); s.SetEnd(pcbnew.VECTOR2I(MM(q[0]), MM(q[1])))
            s.SetWidth(MM(t.get("w", 0.15))); s.SetLayer(layer); s.SetNet(nets[t["net"]])
            b.Add(s); added.append(s.m_Uuid.AsString())
    for v in plan.get("vias", []):
        if v["net"] not in nets:
            bad.append(v["net"]); continue
        s = pcbnew.PCB_VIA(b)
        s.SetPosition(pcbnew.VECTOR2I(MM(v["xy"][0]), MM(v["xy"][1])))
        s.SetWidth(MM(v.get("size", 0.45))); s.SetDrill(MM(v.get("drill", 0.2)))
        s.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); s.SetNet(nets[v["net"]])
        b.Add(s); added.append(s.m_Uuid.AsString())
    b.Save(pcb)
    del b
    refill(pcb)
    d = drc(pcb)

    print(f"ripped {n_rip} items; added {len(added)} items" + (f"; UNKNOWN NETS {sorted(set(bad))}" if bad else ""))
    old = {key(v) for v in base["violations"]}
    new = [v for v in d["violations"] if v["type"] in COPPER and key(v) not in old]
    print(f"\nnew copper DRC errors: {len(new)}")
    for v in new:
        print(f"  {v['type']}: " + " | ".join(f"{i['description']} @({i['pos']['x']:.2f},{i['pos']['y']:.2f})"
                                               for i in v["items"]))
    ob, oa = opens(base), opens(d)
    print(f"\nunconnected: {sum(ob.values())} -> {sum(oa.values())}")
    print("  closed:", sorted(n.split("/")[-1] for n in ob if n not in oa))
    print("  BROKEN:", sorted(n.split("/")[-1] for n in oa if n not in ob))
    print("  FT still open:", sorted(n.split("/")[-1] for n in oa if "FT_" in n))
    ids = set(added)
    dang = [i["description"] + f" @({i['pos']['x']:.2f},{i['pos']['y']:.2f})" for v in d["violations"]
            if v["type"] in ("via_dangling", "track_dangling") for i in v["items"] if i["uuid"] in ids]
    print(f"\nplan items dangling: {len(dang)}")
    for s in dang:
        print("  " + s)
    r = subprocess.run([sys.executable, os.path.join(ROOT, "notes/pinswap/agy_timing_check.py"), pcb],
                       capture_output=True, text=True)
    print("\ntiming check:")
    print("\n".join(l for l in r.stdout.splitlines() if re.search(r"FAIL|PASS|FT|SUMMARY", l))[:4000])
    print(f"\nboard: {pcb}" if keep else "")
    if not keep:
        shutil.rmtree(tmp)


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[a.index("--keep") + 1] if "--keep" in a else None,
         os.path.abspath(a[a.index("--base") + 1]) if "--base" in a else WORK)
