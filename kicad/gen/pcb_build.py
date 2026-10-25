#!/usr/bin/env python3
"""Create usb3-sdr.kicad_pcb from the KiCad netlist: outline, stackup, net classes, floorplan placement,
BGA dog-bone fan-out and planes. Routing is left for the next step.

Floorplan (notes/spec.md section 6): RF chain on the left, ADC + clock left of centre, ECP5 centre (bank 7 faces
the ADC, banks 2/3 face the FT601, bank 8 faces down to flash/JTAG), FT601 + USB on the right, power along the
bottom with the switchers bottom-right, far from the ADC.
"""
import math
import os
import re
import sys
import pcbnew
from sexp import parse, find, find1

HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.abspath(os.path.join(HERE, ".."))
FPDIR = "/usr/share/kicad/footprints"
MM = pcbnew.FromMM
OX, OY = 100.0, 100.0          # board origin on the KiCad page
BW, BH = 100.0, 60.0           # board size, mm


def P(x, y):
    return pcbnew.VECTOR2I(MM(OX + x), MM(OY + y))


# ------------------------------------------------------------------ netlist
nl = parse(open(os.path.join(PRJ, "usb3-sdr.net")).read())
comps = {}
for c in find(find1(nl, "components"), "comp"):
    ref = find1(c, "ref")[1]
    sp = find1(c, "sheetpath")
    comps[ref] = dict(value=find1(c, "value")[1], fp=(find1(c, "footprint") or [0, ""])[1],
                      tstamps=find1(sp, "tstamps")[1], sym=find1(c, "tstamps")[1],
                      sheet=find1(sp, "names")[1].strip("/") or "root",
                      sheetfile=next((p[2] for p in find(c, "property") if p[1] == "Sheetfile"), ""))
pad_net = {}
net_pins = {}
for net in find(find1(nl, "nets"), "net"):
    name = find1(net, "name")[1]
    for n in find(net, "node"):
        r, p = find1(n, "ref")[1], find1(n, "pin")[1]
        pad_net[(r, p)] = name
        net_pins.setdefault(name, []).append((r, p))

board = pcbnew.BOARD()
ds = board.GetDesignSettings()
ds.SetCopperLayerCount(4)
board.SetEnabledLayers(board.GetEnabledLayers())
ds.SetBoardThickness(MM(1.6))

# ------------------------------------------------------------------ stackup: JLC04161H-7628
try:
    stk = ds.GetStackupDescriptor()
    stk.BuildDefaultStackupList(ds, 4)
    diel = [it for it in stk.GetList() if it.GetType() == pcbnew.BS_ITEM_TYPE_DIELECTRIC]
    copper = [it for it in stk.GetList() if it.GetType() == pcbnew.BS_ITEM_TYPE_COPPER]
    for it, t, er in zip(diel, (0.2104, 1.065, 0.2104), (4.4, 4.6, 4.4)):
        it.SetThickness(MM(t)); it.SetEpsilonR(er)
    for it, t in zip(copper, (0.035, 0.0152, 0.0152, 0.035)):
        it.SetThickness(MM(t))
    ds.m_HasStackup = True
    stack_ok = True
except Exception as e:  # stackup is informational; fab uses the JLC preset anyway
    stack_ok = f"not set ({e})"

# ------------------------------------------------------------------ rules and net classes (JLC 4-layer capabilities)
ds.m_TrackMinWidth = MM(0.09)
ds.m_MinClearance = MM(0.09)
ds.m_ViasMinSize = MM(0.4)
ds.m_MinThroughDrill = MM(0.2)
ns = ds.m_NetSettings
dflt = ns.GetDefaultNetclass()
dflt.SetTrackWidth(MM(0.15)); dflt.SetClearance(MM(0.127)); dflt.SetViaDiameter(MM(0.45)); dflt.SetViaDrill(MM(0.2))


def netclass(name, width, clearance=0.15, dp=None, pattern=()):
    nc = pcbnew.NETCLASS(name)
    nc.SetTrackWidth(MM(width)); nc.SetClearance(MM(clearance))
    nc.SetViaDiameter(MM(0.45)); nc.SetViaDrill(MM(0.2))
    if dp:
        nc.SetDiffPairWidth(MM(dp[0])); nc.SetDiffPairGap(MM(dp[1]))
    ns.SetNetclass(name, nc)
    for p in pattern:
        ns.SetNetclassPatternAssignment(p, name)


# 50 R microstrip on L1 over L2 GND: 0.373 mm bare (Hammerstad-Jensen, AGY+Claude), ~0.35 with mask -> confirm in JLC calc
netclass("RF50", 0.35, 0.2, pattern=["*/RF_IN", "*/RF_A", "*/PAD_*", "*LPF*", "*/TRAP*", "*/NOTCH_OUT", "*/LNA_*",
                                     "*/REF_IN"])   # transformer secondary / ADC inputs are short 200 R diff, not RF50
# 90 R differential: 0.26 / 0.15 gap (round-2 review), USB 2 and USB 3
netclass("USB90", 0.26, 0.15, dp=(0.26, 0.15), pattern=["*USB_SS*", "*/FT_TX*", "*USB_D*"])
# 100 R LVDS clock to the ADC
netclass("LVDS100", 0.2, 0.15, dp=(0.2, 0.15), pattern=["*LMK_OUT*", "*ADC_CLK*"])
netclass("PWR", 0.4, 0.15, pattern=["VBUS", "*VBUS_F", "5V_*", "*5V_A", "1V1", "3V3_*", "2V5", "1V8_*", "*/SW_*",
                                    "*FT_1V0", "*FT_VDDA", "*3V3_CLK", "*3V3_PF", "*3V3_D_F"])

# ------------------------------------------------------------------ nets
nets = {}
for name in net_pins:
    ni = pcbnew.NETINFO_ITEM(board, name)
    board.Add(ni)
    nets[name] = ni


def load_fp(fpid):
    lib, name = fpid.split(":", 1)
    path = os.path.join(PRJ, "usb3sdr.pretty") if lib == "usb3sdr" else os.path.join(FPDIR, lib + ".pretty")
    return pcbnew.FootprintLoad(path, name)


fps = {}
for ref, c in comps.items():
    if not c["fp"]:
        print("no footprint:", ref); continue
    fp = load_fp(c["fp"])
    fp.SetReference(ref); fp.SetValue(c["value"])
    fp.SetFPIDAsString(c["fp"]) if hasattr(fp, "SetFPIDAsString") else None
    fp.SetPath(pcbnew.KIID_PATH(c["tstamps"] + c["sym"]))
    fp.SetSheetname(c["sheet"]); fp.SetSheetfile(c["sheetfile"])
    for pad in fp.Pads():
        n = pad_net.get((ref, pad.GetNumber()))
        if n:
            pad.SetNet(nets[n])
    board.Add(fp)
    fps[ref] = fp

# ------------------------------------------------------------------ outline + mounting holes
for (x1, y1, x2, y2) in ((0, 0, BW, 0), (BW, 0, BW, BH), (BW, BH, 0, BH), (0, BH, 0, 0)):
    s = pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(P(x1, y1)); s.SetEnd(P(x2, y2)); s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(MM(0.1))
    board.Add(s)
holes = [(3.5, 3.5), (BW - 3.5, 3.5), (3.5, BH - 3.5), (BW - 3.5, BH - 3.5)]
for i, (x, y) in enumerate(holes, 1):
    h = load_fp("MountingHole:MountingHole_2.7mm_M2.5")
    h.SetReference(f"H{i}"); h.SetPosition(P(x, y)); h.SetBoardOnly(True)
    board.Add(h)

# ------------------------------------------------------------------ key placements (x, y, rotation, side)
KEY = {
    "J4": (2.54, 47.0, 180),                                  # SMA edge launch: board edge at the F.Fab flange line (+2.54)
    "J1": (BW - 2.65, 24.0, 90),                              # USB3 Micro-B, "PCB Edge" line at local y=+2.65
    "U12": (63.0, 24.0, 0),                                   # ECP5: A1 top-left, bank 7 left, banks 2/3 right
    "U8": (41.0, 41.0, 90),                                   # AD9649 at the end of RF row C; outputs face up/right
    "U9": (41.0, 50.0, 0),                                    # LMK61E2 under the ADC clock pins
    "U11": (84.0, 23.0, 90),                                  # FT601: USB (pins 20-38) to the right, data to the left
    "Y1": (91.0, 31.0, 0),
    "U10": (60.0, 38.0, 0), "J3": (70.0, 39.0, 0), "U14": (9.0, 53.0, 0),
    "U1": (92.0, 46.0, 0), "U2": (84.0, 52.0, 0), "U3": (74.0, 52.0, 0),
    "U4": (58.0, 48.0, 0), "U5": (51.0, 50.0, 0), "U6": (22.0, 52.0, 0), "U7": (30.0, 52.0, 0),
    "F1": (95.0, 36.0, 0), "D1": (95.0, 40.0, 0),
    "Q10": (30.0, 3.2, 0), "Q11": (34.5, 3.2, 0),             # LNA supply switch, above RF row A
}
REGION = {   # sheet -> (x0, y0, x1, y1) for parts without an anchor
    "RF front end": (4.0, 2.0, 33.0, 36.0), "ADC and clock": (33.0, 6.0, 54.0, 38.0),
    "FPGA": (52.0, 33.0, 76.0, 44.0), "USB 3 bridge": (74.0, 3.0, 98.0, 40.0), "Power": (30.0, 41.0, 98.0, 58.0),
}
occupied = [(x - 3.3, y - 3.3, x + 3.3, y + 3.3) for x, y in holes]


def bbox_mm(fp):
    bb = fp.GetBoundingBox(False)
    return (pcbnew.ToMM(bb.GetLeft()) - OX, pcbnew.ToMM(bb.GetTop()) - OY,
            pcbnew.ToMM(bb.GetRight()) - OX, pcbnew.ToMM(bb.GetBottom()) - OY)


def overlaps(r, margin=0.25):
    return any(r[0] < o[2] + margin and r[2] > o[0] - margin and r[1] < o[3] + margin and r[3] > o[1] - margin
               for o in occupied)


def place(fp, x, y, rot=0):
    fp.SetOrientationDegrees(rot)
    fp.SetPosition(P(x, y))
    occupied.append(bbox_mm(fp))


for ref, (x, y, rot) in KEY.items():
    place(fps[ref], x, y, rot)
    fps[ref].SetLocked(True)

# ------------------------------------------------------------------ scripted critical layout (rf_layout.py)
import rf_layout
lay = rf_layout.Layout(board, fps, nets, P, OX, OY)
lay.rf()
lay.usb3()
for ref in lay.placed:
    occupied.append(bbox_mm(fps[ref]))
    KEY.setdefault(ref, lay.placed[ref])
occupied.extend(rf_layout.CORRIDORS)
# scripted copper is a keep-out for the generic placer too (0.4 mm margin around every locked segment)
for t in board.GetTracks():
    if t.IsLocked():
        xs = [pcbnew.ToMM(t.GetStart().x) - OX, pcbnew.ToMM(t.GetEnd().x) - OX]
        ys = [pcbnew.ToMM(t.GetStart().y) - OY, pcbnew.ToMM(t.GetEnd().y) - OY]
        m = 0.4 + pcbnew.ToMM(t.GetWidth()) / 2
        occupied.append((min(xs) - m, min(ys) - m, max(xs) + m, max(ys) + m))


def place_top_edge(fp, x):
    """Right-angle header: choose the rotation whose body (bbox beyond the pads) points up, then sit it at the edge."""
    best = None
    for rot in (0, 90, 180, 270):
        fp.SetOrientationDegrees(rot); fp.SetPosition(P(x, 10))
        b = bbox_mm(fp)
        pads_y = [pcbnew.ToMM(pd.GetPosition().y) - OY for pd in fp.Pads()]
        up = (min(pads_y) - b[1]) - (b[3] - max(pads_y))      # body extent above the pads minus below
        wide = (b[2] - b[0]) > (b[3] - b[1])
        if wide and (best is None or up > best[0]):
            best = (up, rot)
    fp.SetOrientationDegrees(best[1]); fp.SetPosition(P(x, 10))
    b = bbox_mm(fp)
    fp.SetPosition(P(x, 10 - b[1] + 0.3))
    occupied.append(bbox_mm(fp))


place_top_edge(fps["J5"], 57.0)
place_top_edge(fps["J6"], 75.5)
KEY["J5"] = KEY["J6"] = None

# ------------------------------------------------------------------ BGA fan-out (dog-bone)
RINGS_DIRECT = 2   # rings 0-1 escape on F.Cu between pads; rings >= 2 (and every power/GND ball) get a via
bga = fps["U12"]
cx, cy = 63.0, 24.0
fan_vias = 0
for pad in bga.Pads():
    if not pad.GetNetname() or pad.GetNetname().startswith("unconnected-"):   # KiCad names unused pads "unconnected-(...)"
        continue
    row = "ABCDEFGHJKLMNPRT".index(pad.GetNumber()[0]); col = int(pad.GetNumber()[1:]) - 1
    ring = min(row, 15 - row, col, 15 - col)
    power = re.search(r"GND|1V1|2V5|3V3_D|1V8_D", pad.GetNetname()) is not None
    if ring < RINGS_DIRECT and not power:
        continue
    px, py = pcbnew.ToMM(pad.GetPosition().x) - OX, pcbnew.ToMM(pad.GetPosition().y) - OY
    sx = 0.4 if px >= cx else -0.4          # via on the interstitial site away from the package centre
    sy = 0.4 if py >= cy else -0.4
    v = pcbnew.PCB_VIA(board); v.SetPosition(P(px + sx, py + sy)); v.SetWidth(MM(0.45)); v.SetDrill(MM(0.2))
    v.SetNet(pad.GetNet()); v.SetLocked(True); board.Add(v)
    t = pcbnew.PCB_TRACK(board); t.SetStart(pad.GetPosition()); t.SetEnd(P(px + sx, py + sy))
    t.SetWidth(MM(0.15)); t.SetLayer(pcbnew.F_Cu); t.SetNet(pad.GetNet()); t.SetLocked(True); board.Add(t)
    fan_vias += 1

# ------------------------------------------------------------------ passives: cluster around the IC they serve
anchors = set(KEY) | {r for r in fps if r[0] in "UJKT"}
BIG = {"GND", "3V3_D", "1V1", "2V5", "1V8_D", "5V_SW"}


def anchor_of(ref):
    best, score = None, 0
    for pad in fps[ref].Pads():
        n = pad.GetNetname()
        if not n or n.split("/")[-1] in BIG:
            continue
        for r, p in net_pins.get(n, []):
            if r in KEY and r != ref:
                s = 2 if comps[r]["sheet"] == comps[ref]["sheet"] else 1
                if s > score:
                    best, score = r, s
    if best is None:   # decoupling caps etc: fall back to the sheet's main IC that shares a rail
        for pad in fps[ref].Pads():
            n = pad.GetNetname()
            for r, p in net_pins.get(n, []):
                if r in KEY and r != ref and comps[r]["sheet"] == comps[ref]["sheet"] and n.split("/")[-1] != "GND":
                    return r
    return best


def spiral_place(fp, ax, ay, region):
    w = (lambda b: (b[2] - b[0], b[3] - b[1]))(bbox_mm(fp))
    for rad in [i * 0.5 for i in range(1, 80)]:
        n = max(8, int(2 * math.pi * rad / 0.8))
        for k in range(n):
            a = 2 * math.pi * k / n
            x, y = ax + rad * math.cos(a), ay + rad * math.sin(a)
            fp.SetPosition(P(x, y))
            r = bbox_mm(fp)
            if r[0] < 0.5 or r[1] < 0.5 or r[2] > BW - 0.5 or r[3] > BH - 0.5:
                continue
            if region and not (r[0] >= region[0] and r[1] >= region[1] and r[2] <= region[2] and r[3] <= region[3]):
                continue
            if not overlaps(r):
                occupied.append(r)
                return True
    return False


failed = []
rest = [r for r in fps if r not in KEY]
rest.sort(key=lambda r: (comps[r]["sheet"], int(re.sub(r"\D", "", r) or 0)))
for ref in rest:
    fp = fps[ref]
    a = anchor_of(ref)
    region = REGION.get(comps[ref]["sheet"])
    if a:
        b = bbox_mm(fps[a]); ax, ay = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        ok = spiral_place(fp, ax, ay, None)
    else:   # RF chain: keep netlist (= signal) order, packed left to right, top to bottom in the RF region
        ok = spiral_place(fp, region[0] + 3, region[1] + 3, region)
    if not ok:
        failed.append(ref)

# ------------------------------------------------------------------ planes
def zone(net, layer, pts, prio=0):
    z = pcbnew.ZONE(board); z.SetLayer(layer); z.SetNet(nets[net]); z.SetAssignedPriority(prio)
    ol = z.Outline(); ol.NewOutline()
    for x, y in pts:
        ol.Append(MM(OX + x), MM(OY + y))
    z.SetMinThickness(MM(0.2)); z.SetLocalClearance(MM(0.2))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    board.Add(z)
    return z


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


zones = [zone("GND", pcbnew.In1_Cu, rect(0.3, 0.3, BW - 0.3, BH - 0.3)),
         zone("1V1", pcbnew.In2_Cu, rect(55.5, 16.5, 70.5, 31.5), 2),
         zone("1V8_A", pcbnew.In2_Cu, rect(34.0, 8.0, 52.0, 34.0), 1),
         zone("3V3_D", pcbnew.In2_Cu, rect(52.0, 0.3, BW - 0.3, 42.0), 0)]
for name in ("1V1", "1V8_A", "3V3_D"):
    if name not in nets:
        print("WARNING zone net missing:", name)
board.BuildConnectivity()   # zones are filled by kicad-cli (ZONE_FILLER segfaults in standalone pcbnew scripts)

# inner layers are planes: mark them as power layers so autorouters keep signals on F.Cu/B.Cu
board.SetLayerType(pcbnew.In1_Cu, pcbnew.LT_POWER)
board.SetLayerType(pcbnew.In2_Cu, pcbnew.LT_POWER)

out = os.path.join(PRJ, "usb3-sdr.kicad_pcb")
board.Save(out)

# JLC04161H-7628 stackup, written into (setup) directly (the SWIG binding does not expose the stackup builder)
from sexp import Q, dump as sdump
tree = parse(open(out).read())
setup = find1(tree, "setup")
L = lambda name, typ, *extra: ["layer", Q(name), ["type", Q(typ)], *extra]
stack = ["stackup",
         L("F.SilkS", "Top Silk Screen"), L("F.Paste", "Top Solder Paste"), L("F.Mask", "Top Solder Mask", ["thickness", 0.01]),
         L("F.Cu", "copper", ["thickness", 0.035]),
         L("dielectric 1", "prepreg", ["thickness", 0.2104], ["material", Q("7628")], ["epsilon_r", 4.4], ["loss_tangent", 0.02]),
         L("In1.Cu", "copper", ["thickness", 0.0152]),
         L("dielectric 2", "core", ["thickness", 1.065], ["material", Q("FR4")], ["epsilon_r", 4.6], ["loss_tangent", 0.02]),
         L("In2.Cu", "copper", ["thickness", 0.0152]),
         L("dielectric 3", "prepreg", ["thickness", 0.2104], ["material", Q("7628")], ["epsilon_r", 4.4], ["loss_tangent", 0.02]),
         L("B.Cu", "copper", ["thickness", 0.035]),
         L("B.Mask", "Bottom Solder Mask", ["thickness", 0.01]), L("B.Paste", "Bottom Solder Paste"), L("B.SilkS", "Bottom Silk Screen"),
         ["copper_finish", Q("HAL lead-free")], ["dielectric_constraints", "no"]]
setup[:] = [e for e in setup if not (isinstance(e, list) and e and e[0] == "stackup")]
setup.insert(1, stack)
open(out, "w").write(sdump(tree) + "\n")
stack_ok = "JLC04161H-7628 (1.6 mm)"

# zone fill must run on a board loaded from disk (ZONE_FILLER segfaults on a freshly built in-memory board)
b2 = pcbnew.LoadBoard(out)
b2.BuildConnectivity()
filled = pcbnew.ZONE_FILLER(b2).Fill(b2.Zones())
pcbnew.SaveBoard(out, b2)
print(f"footprints {len(fps)} (+4 holes), fan-out vias {fan_vias}, stackup {stack_ok}, zones filled {filled}, unplaced {failed}")
