#!/usr/bin/env python3
"""Generate the usb3-sdr KiCad 9 project: hierarchical schematic, project symbol/footprint libraries.

Every pin gets a net label exactly on its connection point (no wires), so connectivity is fully determined
by the netlist in design.py. Nets used on more than one sheet become global labels. Unused pins get a
no-connect flag. Verification is done afterwards with kicad-cli (ERC + netlist comparison, see verify.py).
"""
import os
import sys
import uuid
import design
import custom
from sexp import Q, SymLib, dump, find, find1

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(HERE, ".."))
PROJECT = "usb3-sdr"
ECP5_JSON = os.path.join(HERE, "ecp5_bg256.json")   # from Lattice FPGA-SC-02033 CSV (see README)
LPF = os.path.abspath(os.path.join(HERE, "../../gateware/constraints/usb3sdr.lpf"))
GRID = 1.27
NOBOM = {"J3"}   # Tag-Connect TC2050 is a pad pattern, not a purchased part
uid = lambda: Q(str(uuid.uuid4()))
snap = lambda v: round(v / GRID) * GRID

# ------------------------------------------------------------------ libraries
lib = SymLib()
CUSTOM = {s[1]: s for s in [custom.ad9649(), custom.lmk61e2(), custom.adt4_6t(),
                            custom.tps7a20_dbv("TPS7A2018PDBVR"), custom.tps7a20_dbv("TPS7A2033PDBVR"),
                            custom.ecp5_units(ECP5_JSON)]}


def get_symbol(lib_id):
    ln, name = lib_id.split(":", 1)
    if ln == "usb3sdr":
        return CUSTOM[name]
    return lib.get(ln, name)


def ecp5_unit_balls():
    sym = CUSTOM["LFE5U-25F-6BG256C"]
    units = {}
    for n, nm, x, y, a, u, t in SymLib.pins(sym):
        units.setdefault(u, []).append(n)
    return [units[u] for u in sorted(units)]


# ------------------------------------------------------------------ sheet content
SHEETS = [("power", "Power", design.power()), ("rf", "RF front end", design.rf()),
          ("adc_clk", "ADC and clock", design.adc_clk()), ("usb", "USB 3 bridge", design.usb()),
          ("fpga", "FPGA", design.fpga(LPF, ecp5_unit_balls()))]

net_sheets = {}
for fname, _, comps in SHEETS:
    for ref, lid, val, fp, pins, unit in comps:
        for n in pins.values():
            if n:
                net_sheets.setdefault(n, set()).add(fname)
GLOBAL = {n for n, s in net_sheets.items() if len(s) > 1}


def text_w(s):
    return len(s) * 1.0 + 3.0


def place_sheet(comps, max_w):
    """Shelf packing: returns [(comp, X, Y)] and (width, height)."""
    placed, x, y, row_h, W = [], 20.0, 30.0, 0.0, 0.0
    for c in comps:
        ref, lid, val, fp, pins, unit = c
        sym = get_symbol(lid)
        ps = [p for p in SymLib.pins(sym) if p[5] in (0, unit)]
        if not ps:
            ps = [("1", "", 0, 0, 0, unit, "passive")]
        xs = [p[2] for p in ps]; ys = [-p[3] for p in ps]
        lab = lambda ang: max([text_w(pins.get(p[0], "") or "x") for p in ps if p[4] == ang] + [0])
        left, right = min(xs) - lab(0) - 2, max(xs) + lab(180) + 2
        top, bot = min(ys) - lab(270) - 4, max(ys) + lab(90) + 4
        w, h = right - left, bot - top
        if x + w > max_w and x > 20:
            x, y, row_h = 20.0, y + row_h + 6, 0.0
        X, Y = snap(x - left), snap(y - top)
        placed.append((c, X, Y, sym))
        x += w + 4; row_h = max(row_h, h); W = max(W, x)
    return placed, (W + 20, y + row_h + 30)


def label_for(net, x, y, pin_ang, fname):
    ang = {0: 180, 180: 0, 90: 270, 270: 90}[pin_ang]
    just = {0: "left", 180: "right", 90: "left", 270: "right"}[ang]
    eff = ["effects", ["font", ["size", 1.27, 1.27]], ["justify", just]]
    if net in GLOBAL:
        return ["global_label", Q(net), ["shape", "passive"], ["at", x, y, ang], ["fields_autoplaced", "yes"], eff, ["uuid", uid()],
                ["property", Q("Intersheetrefs"), Q("${INTERSHEET_REFS}"), ["at", x, y, ang],
                 ["effects", ["font", ["size", 1.27, 1.27]], ["hide", "yes"]]]]
    return ["label", Q(net), ["at", x, y, ang], ["fields_autoplaced", "yes"], eff, ["uuid", uid()]]


def sheet_file(fname, title, comps, root_uuid, sheet_uuid, page):
    placed, (W, H) = place_sheet(comps, 340)
    used = {}
    body = []
    for (ref, lid, val, fp, pins, unit), X, Y, sym in placed:
        used[lid] = sym
        fpv = fp if fp is not None else (find1(sym, "property") and next(
            (p[2] for p in find(sym, "property") if p[1] == "Footprint"), ""))
        allpins = [p for p in SymLib.pins(sym) if p[5] in (0, unit)]
        inst = ["symbol", ["lib_id", Q(lid)], ["at", X, Y, 0], ["unit", unit], ["exclude_from_sim", "no"],
                ["in_bom", "no" if ref.startswith("#") or ref in NOBOM else "yes"], ["on_board", "no" if ref.startswith("#") else "yes"],
                ["dnp", "no"], ["uuid", uid()]]
        ys = [-p[3] for p in allpins] or [0]
        inst.append(["property", Q("Reference"), Q(ref), ["at", X, snap(Y + min(ys) - 3.81), 0],
                     ["effects", ["font", ["size", 1.27, 1.27]]] + ([["hide", "yes"]] if ref.startswith("#") else [])])
        inst.append(["property", Q("Value"), Q(val), ["at", X, snap(Y + max(ys) + 3.81), 0],
                     ["effects", ["font", ["size", 1.27, 1.27]]] + ([["hide", "yes"]] if ref.startswith("#") else [])])
        inst.append(["property", Q("Footprint"), Q(fpv or ""), ["at", X, Y, 0], ["effects", ["font", ["size", 1.27, 1.27]], ["hide", "yes"]]])
        inst.append(["property", Q("Datasheet"), Q(""), ["at", X, Y, 0], ["effects", ["font", ["size", 1.27, 1.27]], ["hide", "yes"]]])
        for p in allpins:
            inst.append(["pin", Q(p[0]), ["uuid", uid()]])
        inst.append(["instances", ["project", Q(PROJECT), ["path", Q(f"/{root_uuid}/{sheet_uuid}"),
                                                           ["reference", Q(ref)], ["unit", unit]]]])
        body.append(inst)
        for num, nm, px, py, pang, u, et in allpins:
            x, y = round(X + px, 4), round(Y - py, 4)
            net = pins.get(num)
            if net:
                if not ref.startswith("#FLG") or True:
                    body.append(label_for(net, x, y, pang, fname))
            elif et != "no_connect":
                body.append(["no_connect", ["at", x, y], ["uuid", uid()]])
    lib_syms = []
    for lid, sym in used.items():
        s = [e for e in sym]
        s[1] = Q(lid)
        lib_syms.append(s)
    paper = ["paper", Q("User"), round(max(W, 420), 1), round(max(H, 297), 1)]
    doc = ["kicad_sch", ["version", 20250114], ["generator", Q("eeschema")], ["generator_version", Q("9.0")],
           ["uuid", Q(sheet_uuid if fname != "root" else root_uuid)], paper,
           ["title_block", ["title", Q(f"usb3-sdr Rev A: {title}")], ["date", Q("2026-10-22")], ["rev", Q("A0")],
            ["comment", 1, Q("Generated by kicad/gen/build.py from design.py (datasheet-verified pin maps)")],
            ["comment", 2, Q("Labels sit on pin endpoints: connectivity is exact, layout is not tidied")]],
           ["lib_symbols"] + lib_syms] + body
    return doc


def root_file(root_uuid, sheet_uuids):
    doc = ["kicad_sch", ["version", 20250114], ["generator", Q("eeschema")], ["generator_version", Q("9.0")],
           ["uuid", Q(root_uuid)], ["paper", Q("A3")],
           ["title_block", ["title", Q("usb3-sdr Rev A")], ["date", Q("2026-10-22")], ["rev", Q("A0")],
            ["comment", 1, Q("Direct-sampling HF SDR: AD9649 + ECP5 + FT601 (see ~/collab/projects/usb3-sdr/notes)")]],
           ["lib_symbols"]]
    for i, ((fname, title, _), su) in enumerate(zip(SHEETS, sheet_uuids)):
        x, y = 30 + (i % 3) * 120, 40 + (i // 3) * 70
        doc.append(["sheet", ["at", x, y], ["size", 90, 40], ["exclude_from_sim", "no"], ["in_bom", "yes"],
                    ["on_board", "yes"], ["dnp", "no"], ["fields_autoplaced", "yes"],
                    ["stroke", ["width", 0.1524], ["type", "solid"]], ["fill", ["color", 0, 0, 0, 0.0]],
                    ["uuid", Q(su)],
                    ["property", Q("Sheetname"), Q(title), ["at", x, y - 0.7, 0],
                     ["effects", ["font", ["size", 1.27, 1.27]], ["justify", "left", "bottom"]]],
                    ["property", Q("Sheetfile"), Q(f"{fname}.kicad_sch"), ["at", x, y + 40.6, 0],
                     ["effects", ["font", ["size", 1.27, 1.27]], ["justify", "left", "top"]]],
                    ["instances", ["project", Q(PROJECT), ["path", Q(f"/{root_uuid}"), ["page", Q(str(i + 2))]]]]])
    doc.append(["sheet_instances", ["path", Q("/"), ["page", Q("1")]]])
    return doc


def main():
    os.makedirs(OUT, exist_ok=True)
    root_uuid = str(uuid.uuid4())
    sheet_uuids = [str(uuid.uuid4()) for _ in SHEETS]
    for (fname, title, comps), su, pg in zip(SHEETS, sheet_uuids, range(2, 10)):
        open(f"{OUT}/{fname}.kicad_sch", "w").write(dump(sheet_file(fname, title, comps, root_uuid, su, pg)) + "\n")
    open(f"{OUT}/{PROJECT}.kicad_sch", "w").write(dump(root_file(root_uuid, sheet_uuids)) + "\n")
    # project libraries
    symlib = ["kicad_symbol_lib", ["version", 20241209], ["generator", Q("usb3sdr-gen")], ["generator_version", Q("9.0")]]
    symlib += list(CUSTOM.values())
    open(f"{OUT}/usb3sdr.kicad_sym", "w").write(dump(symlib) + "\n")
    os.makedirs(f"{OUT}/usb3sdr.pretty", exist_ok=True)
    open(f"{OUT}/usb3sdr.pretty/Relay_DPDT_Hongfa_HFD4-SR.kicad_mod", "w").write(custom.fp_hfd4_sr())
    open(f"{OUT}/usb3sdr.pretty/TI_SIA0008B_QFM-8_7x5mm.kicad_mod", "w").write(custom.fp_ti_sia0008b())
    open(f"{OUT}/sym-lib-table", "w").write(
        '(sym_lib_table\n\t(version 7)\n\t(lib (name "usb3sdr") (type "KiCad") (uri "${KIPRJMOD}/usb3sdr.kicad_sym") (options "") (descr "project symbols"))\n)\n')
    open(f"{OUT}/fp-lib-table", "w").write(
        '(fp_lib_table\n\t(version 7)\n\t(lib (name "usb3sdr") (type "KiCad") (uri "${KIPRJMOD}/usb3sdr.pretty") (options "") (descr "project footprints"))\n)\n')
    if not os.path.exists(f"{OUT}/{PROJECT}.kicad_pro"):
        open(f"{OUT}/{PROJECT}.kicad_pro", "w").write('{\n  "meta": {"filename": "%s.kicad_pro", "version": 3}\n}\n' % PROJECT)
    # expected connectivity for verify.py
    import json
    exp = {}
    for fname, _, comps in SHEETS:
        for ref, lid, val, fp, pins, unit in comps:
            if ref.startswith("#"):
                continue
            for n, net in pins.items():
                if net:
                    exp.setdefault(net if net in GLOBAL else f"/{fname}/{net}", []).append(f"{ref}.{n}")
    json.dump(exp, open(f"{HERE}/expected_nets.json", "w"), indent=1, sort_keys=True)
    n_comp = sum(1 for _, _, c in SHEETS for x in c if not x[0].startswith("#"))
    print(f"wrote {len(SHEETS)} sheets, {n_comp} symbol instances, {len(exp)} nets ({len(GLOBAL)} global)")


if __name__ == "__main__":
    main()
