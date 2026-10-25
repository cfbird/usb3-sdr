#!/usr/bin/env python3
"""Rip up unlocked copper that DRC says conflicts with locked copper, then strip the dangling stubs this leaves.

Run after merge_routed.py (and again after buck_patch.py). Repeats DRC until no conflict involves a locked item.
Conflicts between two unlocked items are left alone: those are the autorouter's own and get reported, not fixed.
usage: repair_conflicts.py board.kicad_pcb    (edited in place; the project + schematics must sit next to it)
"""
import json
import os
import subprocess
import sys
import tempfile

import pcbnew

CONFLICT = {"shorting_items", "tracks_crossing", "clearance", "hole_clearance", "holes_co_located", "hole_to_hole"}


def drc(path):
    out = tempfile.mktemp(suffix=".json")
    subprocess.run(["kicad-cli", "pcb", "drc", "--format", "json", "-o", out, path], capture_output=True)
    d = json.load(open(out))
    os.unlink(out)
    return d


def delete_by_uuid(path, uuids):
    """Delete top-level (segment ...), (arc ...) and (via ...) blocks whose uuid is listed, editing the file text.
    pcbnew's SWIG wrappers go stale after BOARD.Remove(), so edits are done on the S-expression instead."""
    txt = open(path).read()
    out, i, n = [], 0, 0
    while True:
        j = min([k for k in (txt.find("\n\t(segment", i), txt.find("\n\t(via", i), txt.find("\n\t(arc", i)) if k >= 0],
                default=-1)
        if j < 0:
            out.append(txt[i:]); break
        depth, k = 0, j + 2
        while True:                        # find the matching close paren (no parens inside quoted strings here)
            c = txt[k]
            depth += c == "("
            depth -= c == ")"
            k += 1
            if depth == 0:
                break
        block = txt[j:k]
        out.append(txt[i:j])
        if any(u in block for u in uuids):
            n += 1
        else:
            out.append(block)
        i = k
    open(path, "w").write("".join(out))
    return n


def dangling(path):
    """uuids of unlocked track segments with an end touching nothing of their net, and unlocked vias with no track."""
    b = pcbnew.LoadBoard(path)
    items, pads, dead = list(b.GetTracks()), list(b.GetPads()), set()
    for t in items:
        if t.IsLocked():
            continue
        net = t.GetNetCode()
        if t.Type() == pcbnew.PCB_VIA_T:
            p = t.GetPosition()
            if not any(o.GetNetCode() == net and o.Type() != pcbnew.PCB_VIA_T and o.HitTest(p, 1000) for o in items) \
                    and not any(pd.GetNetCode() == net and pd.HitTest(p) for pd in pads):
                dead.add(t.m_Uuid.AsString())
            continue
        for e in (t.GetStart(), t.GetEnd()):
            if not any(o is not t and o.GetNetCode() == net and o.HitTest(e, 1000) for o in items) and \
                    not any(pd.GetNetCode() == net and pd.HitTest(e) for pd in pads):
                dead.add(t.m_Uuid.AsString())
                break
    return dead


def refill(path):
    b = pcbnew.LoadBoard(path)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.Save(path)


def main(path):
    # pcbnew falls back to default design rules when no .kicad_pro sits beside the board, and Save() then
    # writes those defaults out: refuse rather than silently loosen or tighten the rules
    if not os.path.exists(os.path.splitext(path)[0] + ".kicad_pro"):
        sys.exit(f"{path}: no matching .kicad_pro next to it")
    total = 0
    for rnd in range(8):
        d = drc(path)
        b = pcbnew.LoadBoard(path)
        locked = {t.m_Uuid.AsString() for t in b.GetTracks() if t.IsLocked()}
        locked |= {p.m_Uuid.AsString() for p in b.GetPads()}
        locked |= {f.m_Uuid.AsString() for f in b.GetFootprints()}
        tracks = {t.m_Uuid.AsString() for t in b.GetTracks()}
        kill = set()
        for v in d["violations"]:
            if v["type"] in ("via_dangling", "copper_edge_clearance"):   # half-connected vias, copper at the edge
                kill |= {i["uuid"] for i in v["items"] if i["uuid"] not in locked and i["uuid"] in tracks}
            if v["type"] not in CONFLICT:
                continue
            ids = [i["uuid"] for i in v["items"]]
            if any(i in locked for i in ids):
                kill |= {i for i in ids if i not in locked and i in tracks}
        n = delete_by_uuid(path, kill) if kill else 0
        while True:                        # strip the stubs the rip-up left behind
            dead = dangling(path)
            if not dead:
                break
            n += delete_by_uuid(path, dead)
        if n == 0:
            break
        refill(path)
        total += n
        print(f"round {rnd}: removed {n} items")
    print(f"done: removed {total} items")


if __name__ == "__main__":
    main(sys.argv[1])
