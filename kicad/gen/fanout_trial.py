#!/usr/bin/env python3
"""Try a U12 fan-out plan on a throw-away copy of the work board and report what KiCad's real zone fill and DRC say.

Copies kicad/work (board, project, schematic links) into a temp dir, runs fanout_apply.py with the plan, nudges the
listed parts off protected copper (place_free.py), rips unlocked copper that conflicts (repair_conflicts.py), fills,
then prints:
  - per In2 island net: the filled pieces, and which rail vias / source vias each contains (a rail is OK when one piece
    holds every via of that net that lies inside its outline);
  - DRC shorts / clearance / hole clearance (copper only);
  - rail (1V1 2V5 1V8_D 3V3_D) unconnected pairs, split into "decap stub" (a decap pad to anything: Claude routes
    these short F.Cu stubs) and "other" (the ones the plan must fix).
The work board is never touched.
usage: python3 kicad/gen/fanout_trial.py plan.json [--nudge REF ...] [--keep DIR]
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GEN = os.path.join(ROOT, "kicad/gen")
RAILS = ("1V1", "2V5", "1V8_D", "3V3_D")
ISLANDS = ("1V1", "2V5", "1V8_D")
STUB = 5.0         # mm; a rail gap shorter than this is a surface stub, not a plane problem


def run(args, cwd):
    r = subprocess.run([sys.executable] + args, cwd=cwd, capture_output=True, text=True)
    out = "\n".join(l for l in (r.stdout + r.stderr).splitlines() if "Debug:" not in l)
    if r.returncode:
        sys.exit(f"{args[0]} failed:\n{out}")
    return out


def main():
    a = sys.argv[1:]
    plan = os.path.abspath(a[0])
    nudge = a[a.index("--nudge") + 1:] if "--nudge" in a else []
    nudge = [r for r in nudge if not r.startswith("--")]
    keep = a[a.index("--keep") + 1] if "--keep" in a else None
    d = keep or tempfile.mkdtemp(prefix="fanout_trial_")
    os.makedirs(d, exist_ok=True)
    w = os.path.join(ROOT, "kicad/work")
    for f in os.listdir(w):
        src = os.path.join(w, f)
        if f.endswith((".kicad_pcb", ".kicad_pro")):
            shutil.copy(src, d)
        elif not f.endswith(".kicad_prl") and not os.path.exists(os.path.join(d, f)):
            os.symlink(os.path.realpath(src), os.path.join(d, f))
    pcb = os.path.join(d, "usb3-sdr.kicad_pcb")
    print(run([os.path.join(GEN, "fanout_apply.py"), plan, pcb], d).splitlines()[-1])
    if nudge:
        print(run([os.path.join(GEN, "place_free.py"), pcb] + nudge, d))
    run([os.path.join(GEN, "repair_conflicts.py"), pcb], d)

    import pcbnew
    b = pcbnew.LoadBoard(pcb)
    T = pcbnew.ToMM
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    print("\n== In2 islands (KiCad fill)")
    for z in b.Zones():
        n = z.GetNetname()
        if z.GetLayer() != pcbnew.In2_Cu or n not in ISLANDS + ("3V3_D",):
            continue
        fp = z.GetFilledPolysList(pcbnew.In2_Cu)
        vias = [t for t in b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T and t.GetNetname() == n
                and z.Outline().Contains(t.GetPosition())]
        if n == "3V3_D":      # the big plane: only ask whether the U12 core vias reach its main piece
            main = max(range(fp.OutlineCount()), key=lambda i: fp.Outline(i).Area())
            core = [v for v in vias if 155.5 < T(v.GetPosition().x) < 170.5 and 116.5 < T(v.GetPosition().y) < 131.5]
            off = [(round(T(v.GetPosition().x), 2), round(T(v.GetPosition().y), 2)) for v in core
                   if not fp.Outline(main).PointInside(v.GetPosition(), pcbnew.FromMM(0.3))]
            print(f"3V3_D: {'OK' if not off else 'SPLIT'}, {len(core)} U12 vias, not on the main plane piece: {off}")
            continue
        pieces = {i: [] for i in range(fp.OutlineCount())}
        lost = []
        for v in vias:
            hit = [i for i in pieces if fp.Outline(i).PointInside(v.GetPosition(), pcbnew.FromMM(0.3))]
            (pieces[hit[0]] if hit else lost).append((round(T(v.GetPosition().x), 2), round(T(v.GetPosition().y), 2)))
        status = "OK" if sum(1 for p in pieces.values() if p) <= 1 and not lost else "SPLIT"
        print(f"{n}: {status}, {fp.OutlineCount()} filled piece(s)")
        for i, p in pieces.items():
            bb = fp.Outline(i).BBox()
            print(f"   piece {i} bbox ({T(bb.GetX()):.2f},{T(bb.GetY()):.2f})-({T(bb.GetRight()):.2f},"
                  f"{T(bb.GetBottom()):.2f}) vias {p}")
        if lost:
            print(f"   vias inside the outline but in no filled piece: {lost}")
    b.Save(pcb)

    rep = pcb + ".drc.json"
    subprocess.run(["kicad-cli", "pcb", "drc", "--schematic-parity", "--format", "json", "-o", rep, pcb],
                   capture_output=True)
    r = json.load(open(rep))
    fmt = lambda i: f'{i["description"][:60]} @({i["pos"]["x"]:.2f},{i["pos"]["y"]:.2f})'
    bad = [v for v in r["violations"] if v["type"] in ("shorting_items", "clearance", "hole_clearance")]
    print(f"\n== DRC copper conflicts: {len(bad)}")
    for v in bad:
        print(f'   {v["type"]}: ' + " || ".join(fmt(i) for i in v["items"]))
    stubs, other = [], []
    for u in r["unconnected_items"]:
        s = " <-> ".join(fmt(i) for i in u["items"])
        if not any(f"[{n}]" in s for n in RAILS):
            continue
        (p, q) = [(i["pos"]["x"], i["pos"]["y"]) for i in u["items"][:2]]
        gap = ((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2) ** 0.5
        (stubs if gap < STUB else other).append(f"{s}  [{gap:.1f} mm]")
    print(f"\n== rail unconnected: {len(stubs)} short pairs < {STUB} mm (stubs Claude routes on F.Cu), "
          f"{len(other)} longer (the plan's islands/necks must carry these)")
    for s in other:
        print("   " + s)
    print(f"\nboard: {pcb}" if keep else "")
    if not keep:
        shutil.rmtree(d)


if __name__ == "__main__":
    main()
