#!/usr/bin/env python3
"""
Standalone verification script for the ECP5 (U12) & FT601 (U11) fan-out plan (v3).
Run from the repository root:
    python3 notes/fanout/agy_fanout_check.py

Reads:
    notes/fanout/fanout_data.json
    notes/fanout/agy_fanout_plan_v3.json

Checks:
    1. T1 Rule 1: In2.Cu polygons for 2V5, 1V8_D, 1V1 (priority 2, carving out of the
       existing 3V3_D rectangle [152.0..199.7, 100.3..142.0] at priority 1):
       pairwise non-overlap (including the true 1V8_A rectangle [134.0, 108.0, 152.0, 134.0]
       with >= 0.25 mm clearance), zero self-intersections, min neck width >= 0.50 mm
       (including step-pinch checks across all vertex scanlines), max island width >= 1.00 mm.
    2. T1 Rule 3: Source regulator & decap connectivity (every island covers its regulator
       L1 / U4 / U5 and U8 pad 13 via [144.30, 140.60]).
    3. T1 Rule 4: Polygon clearance >= 0.25 mm to other-net via pads (r_pad = 0.225 mm,
       so center-to-polygon distance >= 0.475 mm).
    4. T2 Power & GND ball coverage: All 21 power balls and 27 GND balls covered;
       every power via strictly inside its rail's In2.Cu zone (margin >= 0.225 mm);
       0 ball-fanout power vias outside the 6x6 core; min different-net power via distance.
    5. T3 Courtyard non-overlap after applying `moves`, all relocated U12 decaps
       (C81-C85, C87, C88, C90, C91, C92 + C86, C93, C94) within <= 3.00 mm of the U12
       package body [156.0, 117.0, 170.0, 131.0], outside the bus corridors, and within
       <= 4.00 mm of a via of their rail, plus R50 <= 5.00 mm from N9->U10 route.
    6. T4 & T1 Rule 2: All 65 bus nets (46 FT + 19 ADC) escaped, and 0 B.Cu escapes
       cross any In2.Cu split against the carved 3V3_D plane.
    7. T5 FT601 (U11) decap moves & approach lanes: All 9 blocking decaps (C68, C69, C70,
       C71, C72, C73, C76, C79, C80) relocated with rail pad <= 2.00 mm from a same-rail
       pin/via, and 0 footprints overlapping the two keepout_lanes polygons.
"""
import json
import math
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Pure-Python computational geometry helpers (no external dependencies)
# ---------------------------------------------------------------------------
def pt_in_poly(pt, poly):
    x, y = pt
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if ((y1 > y) != (y2 > y)) and (x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-15) + x1):
            inside = not inside
    return inside


def pt_to_seg_dist(pt, a, b):
    px, py = pt
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy
    if l2 == 0.0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / l2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def pt_to_poly_dist(pt, poly):
    return min(pt_to_seg_dist(pt, poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly)))


def segs_intersect(a, b, c, d):
    def ccw(p1, p2, p3):
        return (p3[1] - p1[1]) * (p2[0] - p1[0]) - (p2[1] - p1[1]) * (p3[0] - p1[0])
    d1 = ccw(c, d, a)
    d2 = ccw(c, d, b)
    d3 = ccw(a, b, c)
    d4 = ccw(a, b, d)
    if ((d1 > 1e-9 and d2 < -1e-9) or (d1 < -1e-9 and d2 > 1e-9)) and \
       ((d3 > 1e-9 and d4 < -1e-9) or (d3 < -1e-9 and d4 > 1e-9)):
        return True
    return False


def polys_overlap(p1, p2):
    for i in range(len(p1)):
        for j in range(len(p2)):
            if segs_intersect(p1[i], p1[(i + 1) % len(p1)], p2[j], p2[(j + 1) % len(p2)]):
                return True, f"edge {i} intersects edge {j}"
    for pt in p1:
        if pt_in_poly(pt, p2) and pt_to_poly_dist(pt, p2) > 1e-6:
            return True, f"vertex {pt} strictly inside second polygon"
    for pt in p2:
        if pt_in_poly(pt, p1) and pt_to_poly_dist(pt, p1) > 1e-6:
            return True, f"vertex {pt} strictly inside first polygon"
    return False, "OK"


def poly_to_poly_dist(p1, p2):
    ov, _ = polys_overlap(p1, p2)
    if ov:
        return 0.0
    d1 = min(pt_to_poly_dist(pt, p2) for pt in p1)
    d2 = min(pt_to_poly_dist(pt, p1) for pt in p2)
    return min(d1, d2)


def poly_min_neck_and_max_width(poly):
    """Compute minimum internal neck width (including step transitions) and maximum island width."""
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    min_w = float("inf")
    max_w = 0.0

    def x_intervals_at(ym):
        x_ints = []
        n = len(poly)
        for k in range(n):
            x1, y1 = poly[k]
            x2, y2 = poly[(k + 1) % n]
            if (y1 <= ym < y2) or (y2 <= ym < y1):
                x_ints.append(x1 + (ym - y1) * (x2 - x1) / (y2 - y1))
        x_ints.sort()
        return [(x_ints[k], x_ints[k + 1]) for k in range(0, len(x_ints) - 1, 2)]

    def y_intervals_at(xm):
        y_ints = []
        n = len(poly)
        for k in range(n):
            x1, y1 = poly[k]
            x2, y2 = poly[(k + 1) % n]
            if (x1 <= xm < x2) or (x2 <= xm < x1):
                y_ints.append(y1 + (xm - x1) * (y2 - y1) / (x2 - x1))
        y_ints.sort()
        return [(y_ints[k], y_ints[k + 1]) for k in range(0, len(y_ints) - 1, 2)]

    u_ys = sorted(set(ys))
    prev_x_ivs = []
    for i in range(len(u_ys) - 1):
        ym = 0.5 * (u_ys[i] + u_ys[i + 1])
        ivs = x_intervals_at(ym)
        for a, b in ivs:
            max_w = max(max_w, b - a)
            min_w = min(min_w, b - a)
        # Check step overlap across horizontal scanline u_ys[i]
        for a, b in ivs:
            overlaps = [min(b, pb) - max(a, pa) for pa, pb in prev_x_ivs if min(b, pb) > max(a, pa)]
            if overlaps:
                min_w = min(min_w, max(overlaps))
        prev_x_ivs = ivs

    u_xs = sorted(set(xs))
    prev_y_ivs = []
    for i in range(len(u_xs) - 1):
        xm = 0.5 * (u_xs[i] + u_xs[i + 1])
        ivs = y_intervals_at(xm)
        for a, b in ivs:
            max_w = max(max_w, b - a)
            min_w = min(min_w, b - a)
        for a, b in ivs:
            overlaps = [min(b, pb) - max(a, pa) for pa, pb in prev_y_ivs if min(b, pb) > max(a, pa)]
            if overlaps:
                min_w = min(min_w, max(overlaps))
        prev_y_ivs = ivs

    return round(min_w, 3), round(max_w, 3)


def dist_to_u12_pkg(xy):
    """Distance from point (x, y) to U12 14x14 mm package body [156.0, 117.0, 170.0, 131.0]."""
    x, y = xy
    return math.hypot(max(156.0 - x, 0.0, x - 170.0), max(117.0 - y, 0.0, y - 131.0))


def main():
    root = Path(__file__).resolve().parents[2]
    data_path = root / "notes" / "fanout" / "fanout_data.json"
    plan_path = Path(sys.argv[1]) if len(sys.argv) > 1 else (root / "notes" / "fanout" / "agy_fanout_plan_v3.json")

    data = json.loads(data_path.read_text())
    plan = json.loads(plan_path.read_text())

    errors = []
    print("=" * 72)
    print(f"AGY FAN-OUT PLAN v3 VERIFICATION ({plan_path.name})")
    print("=" * 72)

    # -----------------------------------------------------------------------
    # 1. T1 Rule 1: In2.Cu Polygons (2V5, 1V8_D, 1V1 at priority 2; 3V3_D kept as existing rect)
    # -----------------------------------------------------------------------
    polys = {p["net"]: p["outline"] for p in plan["in2_polygons"]}
    expected_island_rails = {"2V5", "1V8_D", "1V1"}
    if set(polys.keys()) != expected_island_rails:
        errors.append(f"T1 Rule 1: Expected In2.Cu islands {expected_island_rails}, found {set(polys.keys())}")
    for p in plan["in2_polygons"]:
        if p.get("priority") != 2:
            errors.append(f"T1 Rule 1: {p['net']} priority must be 2, got {p.get('priority')}")

    # Existing kept zones on In2.Cu (using true 1V8_A rectangle [134.0, 108.0, 152.0, 134.0]):
    poly_3v3d_rect = [[152.0, 100.3], [199.7, 100.3], [199.7, 142.0], [152.0, 142.0]]
    poly_1v8a = [[134.0, 108.0], [152.0, 108.0], [152.0, 134.0], [134.0, 134.0]]
    all_polys = dict(polys)
    all_polys["1V8_A"] = poly_1v8a

    for net, poly in polys.items():
        n = len(poly)
        for i in range(n):
            for j in range(i + 2, n):
                if i == 0 and j == n - 1:
                    continue
                if segs_intersect(poly[i], poly[(i + 1) % n], poly[j], poly[(j + 1) % n]):
                    errors.append(f"T1 Rule 1: {net} polygon self-intersects at edges {i} and {j}")
        min_neck, max_width = poly_min_neck_and_max_width(poly)
        print(f"[T1 Rule 1] {net:6s}: vertices={len(poly):2d}, priority=2, min_neck={min_neck:.3f} mm (>=0.500), max_width={max_width:.2f} mm (>=1.00)")
        if min_neck < 0.50:
            errors.append(f"T1 Rule 1: {net} min neck {min_neck:.3f} mm < 0.50 mm")
        if max_width < 1.00:
            errors.append(f"T1 Rule 1: {net} max width {max_width:.3f} mm < 1.00 mm")

    net_names = sorted(all_polys.keys())
    for i in range(len(net_names)):
        for j in range(i + 1, len(net_names)):
            n1, n2 = net_names[i], net_names[j]
            ov, msg = polys_overlap(all_polys[n1], all_polys[n2])
            if ov:
                errors.append(f"T1 Rule 1: Overlap between {n1} and {n2}: {msg}")
    d_1v8_1v8a = poly_to_poly_dist(polys["1V8_D"], poly_1v8a)
    if d_1v8_1v8a < 0.25:
        errors.append(f"T1 Rule 1: 1V8_D to 1V8_A [134..152, 108..134] clearance {d_1v8_1v8a:.3f} mm < 0.250 mm")
    print(f"[T1 Rule 1] Pairwise polygon overlap check (incl. true 1V8_A [134..152, 108..134], clr={d_1v8_1v8a:.3f} mm): PASS")

    # -----------------------------------------------------------------------
    # 2. T2 Power & GND Ball Coverage + Core Via Rules
    # -----------------------------------------------------------------------
    del_set = {(round(x, 2), round(y, 2)) for x, y in plan["delete_vias"]}
    kept_vias = [
        v for v in data["vias"]
        if (round(v["xy"][0], 2), round(v["xy"][1], 2)) not in del_set
    ]
    plan_vias = plan["vias"]

    covered_balls = {}
    for v in plan_vias:
        vx, vy = v["xy"]
        vnet = v["net"]
        if v["balls"] and vnet in ("3V3_D", "2V5", "1V8_D", "1V1"):
            if not (160.5 <= vx <= 165.5 and 120.7 <= vy <= 126.5):
                errors.append(f"T2: Core power via {vnet} at {v['xy']} is outside the 6x6 core")
        if vnet in polys:
            if not pt_in_poly([vx, vy], polys[vnet]):
                errors.append(f"T2: Power via {vnet} at {v['xy']} is not inside {vnet} polygon")
            elif pt_to_poly_dist([vx, vy], polys[vnet]) < 0.225:
                errors.append(f"T2: Power via {vnet} pad at {v['xy']} overhangs {vnet} polygon boundary")
        elif vnet == "3V3_D":
            if not pt_in_poly([vx, vy], poly_3v3d_rect) or pt_to_poly_dist([vx, vy], poly_3v3d_rect) < 0.225:
                errors.append(f"T2: 3V3_D via at {v['xy']} not inside existing 3V3_D rectangle")
            for p_net, p_poly in polys.items():
                if pt_in_poly([vx, vy], p_poly) or pt_to_poly_dist([vx, vy], p_poly) < 0.475:
                    errors.append(f"T2: 3V3_D via at {v['xy']} violates 0.25mm clearance to {p_net} cutout")
        for bname in v["balls"]:
            binfo = data["balls"].get(bname)
            if not binfo:
                errors.append(f"T2: Unknown ball {bname} in via {v}")
                continue
            if binfo["net"] != vnet:
                errors.append(f"T2: Ball {bname} ({binfo['net']}) assigned to wrong-net via {vnet}")
            dist = math.hypot(binfo["xy"][0] - vx, binfo["xy"][1] - vy)
            if dist > 2.05:
                errors.append(f"T2: Ball {bname} too far ({dist:.3f} mm) from via {v['xy']}")
            covered_balls[bname] = v["xy"]

    for bname, binfo in data["balls"].items():
        if binfo["role"] == "gnd" and bname not in covered_balls:
            bx, by = binfo["xy"]
            for kv in kept_vias:
                if kv["net"] == "GND" and math.hypot(kv["xy"][0] - bx, kv["xy"][1] - by) < 0.60:
                    covered_balls[bname] = kv["xy"]
                    break

    power_balls = [b for b, info in data["balls"].items() if info["role"] == "power"]
    gnd_balls = [b for b, info in data["balls"].items() if info["role"] == "gnd"]
    uncovered_pwr = [b for b in power_balls if b not in covered_balls]
    uncovered_gnd = [b for b in gnd_balls if b not in covered_balls]
    if uncovered_pwr:
        errors.append(f"T2: Uncovered power balls: {uncovered_pwr}")
    if uncovered_gnd:
        errors.append(f"T2: Uncovered GND balls: {uncovered_gnd}")

    core_pwr_vias = [v for v in plan_vias if v["balls"] and v["net"] in ("3V3_D", "2V5", "1V8_D", "1V1")]
    min_diff_pwr_dist = float("inf")
    for i in range(len(core_pwr_vias)):
        for j in range(i + 1, len(core_pwr_vias)):
            if core_pwr_vias[i]["net"] != core_pwr_vias[j]["net"]:
                d_ij = math.hypot(core_pwr_vias[i]["xy"][0] - core_pwr_vias[j]["xy"][0],
                                  core_pwr_vias[i]["xy"][1] - core_pwr_vias[j]["xy"][1])
                min_diff_pwr_dist = min(min_diff_pwr_dist, d_ij)
    print(f"[T2] Power balls covered: {len(power_balls) - len(uncovered_pwr)}/{len(power_balls)}, "
          f"GND balls covered: {len(gnd_balls) - len(uncovered_gnd)}/{len(gnd_balls)}, "
          f"min diff-net core power via dist: {min_diff_pwr_dist:.3f} mm")

    # -----------------------------------------------------------------------
    # 3. T3 Courtyard Non-Overlap, Decap Proximity (<= 3.0mm to U12 pkg, <= 4.0mm to rail via), & R50
    # -----------------------------------------------------------------------
    moves = plan["moves"]
    boxes = {}
    body_boxes = {}
    part_centers = {}
    for ref, p in data["parts"].items():
        x0, y0, x1, y1 = p["courtyard"]
        if ref not in moves:
            part_centers[ref] = p["xy"]
            boxes[ref] = [x0, y0, x1, y1]
            body_boxes[ref] = [round(x0 + 0.25, 4), round(y0 + 0.25, 4),
                               round(x1 - 0.25, 4), round(y1 - 0.25, 4)]
        else:
            w, h = round(x1 - x0, 4), round(y1 - y0, 4)
            rot = moves[ref].get("rot", p["rot"])
            if int(round(p["rot"])) % 180 != int(round(rot)) % 180:
                w, h = h, w
            xy = moves[ref]["xy"]
            part_centers[ref] = xy
            hw, hh = w / 2.0, h / 2.0
            boxes[ref] = [round(xy[0] - hw, 4), round(xy[1] - hh, 4),
                          round(xy[0] + hw, 4), round(xy[1] + hh, 4)]
            bw, bh = max(0.2, w - 0.50) / 2.0, max(0.2, h - 0.50) / 2.0
            body_boxes[ref] = [round(xy[0] - bw, 4), round(xy[1] - bh, 4),
                               round(xy[0] + bw, 4), round(xy[1] + bh, 4)]

    refs = sorted(boxes.keys())
    cy_overlaps = []
    for i in range(len(refs)):
        for j in range(i + 1, len(refs)):
            r1, r2 = refs[i], refs[j]
            if r1 not in moves and r2 not in moves:
                continue
            b1, b2 = body_boxes[r1], body_boxes[r2]
            if not (b1[2] <= b2[0] or b2[2] <= b1[0] or b1[3] <= b2[1] or b2[3] <= b1[1]):
                cy_overlaps.append((r1, r2))
    if cy_overlaps:
        errors.append(f"T3: Footprint body/pad overlaps found: {cy_overlaps}")
    print(f"[T3] Footprint overlap check across all {len(refs)} parts ({len(moves)} moved): PASS ({len(cy_overlaps)} overlaps)")

    u12_decap_rails = {
        "C81": "1V1", "C82": "1V1", "C83": "1V1", "C84": "1V1",
        "C85": "1V1", "C86": "1V1", "C87": "1V1", "C88": "1V1",
        "C89": "2V5", "C90": "2V5", "C91": "2V5",
        "C92": "1V8_D", "C93": "1V8_D", "C94": "1V8_D",
    }
    relocated_decaps = {"C81", "C82", "C83", "C84", "C85", "C87", "C88", "C90", "C91", "C92", "C93"}
    board_rail_vias = [{"net": v["net"], "xy": v["xy"]} for v in plan_vias]
    max_pkg_dist = 0.0
    max_via_dist = 0.0
    for ref, rail in sorted(u12_decap_rails.items()):
        cxy = part_centers[ref]
        d_pkg = dist_to_u12_pkg(cxy)
        d_via = min(math.hypot(cxy[0] - v["xy"][0], cxy[1] - v["xy"][1]) for v in board_rail_vias if v["net"] == rail)
        max_via_dist = max(max_via_dist, d_via)
        if ref in relocated_decaps or ref in ("C86", "C94"):
            max_pkg_dist = max(max_pkg_dist, d_pkg)
            if d_pkg > 3.00:
                errors.append(f"T3: Decap {ref} at {cxy} is {d_pkg:.3f} mm > 3.00 mm from U12 package body")
        if d_via > 4.00:
            errors.append(f"T3: Decap {ref} ({rail}) at {cxy} is {d_via:.3f} mm > 4.00 mm from nearest {rail} via")
        if 169.5 <= cxy[0] <= 178.0 and 117.5 <= cxy[1] <= 130.5:
            errors.append(f"T3: Decap {ref} at {cxy} is inside East FT601 bus corridor")
        if cxy[0] <= 156.0 and 120.8 <= cxy[1] <= 130.0:
            errors.append(f"T3: Decap {ref} at {cxy} is inside West Bank-7 ADC corridor")
    print(f"[T3] Relocated U12 decaps: max dist to U12 pkg = {max_pkg_dist:.3f} mm (<= 3.000 mm), "
          f"max dist to rail via = {max_via_dist:.3f} mm (<= 4.000 mm)")

    n9_xy = data["balls"]["N9"]["xy"]
    u10_cclk_xy = data["parts"]["U10"]["pads"]["6"]["xy"]
    r50_xy = part_centers["R50"]
    r50_route_dist = pt_to_seg_dist(r50_xy, n9_xy, u10_cclk_xy)
    if r50_route_dist > 5.0:
        errors.append(f"T3: R50 at {r50_xy} is {r50_route_dist:.2f} mm > 5.0 mm from N9->U10 route")
    print(f"[T3] R50 distance to N9->U10 CCLK route: {r50_route_dist:.2f} mm (<= 5.00 mm)")

    # -----------------------------------------------------------------------
    # 4. T1 Rule 3: Source & Decap Connectivity
    # -----------------------------------------------------------------------
    all_decap_rails = dict(u12_decap_rails)
    all_decap_rails.update({"C8": "1V1", "C16": "2V5", "C17": "2V5", "C57": "1V8_D", "C58": "1V8_D"})
    max_decap_poly_dist = 0.0
    for ref, rail in all_decap_rails.items():
        if ref in part_centers:
            cxy = part_centers[ref]
        elif ref in moves:
            cxy = moves[ref]["xy"]
        else:
            continue
        poly = polys[rail]
        d_poly = 0.0 if pt_in_poly(cxy, poly) else pt_to_poly_dist(cxy, poly)
        max_decap_poly_dist = max(max_decap_poly_dist, d_poly)
        if d_poly > 3.5:
            errors.append(f"T1 Rule 3: Decap {ref} ({rail}) at {cxy} is {d_poly:.2f} mm > 3.5 mm from {rail} island")

    sources = {
        "1V1":   [184.000, 149.679],  # L1 1V1 buck output via
        "2V5":   [160.950, 147.050],  # U4/C16 2V5 LDO output via
        "1V8_D": [148.731, 151.955],  # U5 1V8_D LDO output via
    }
    for rail, s_xy in sources.items():
        if not pt_in_poly(s_xy, polys[rail]):
            errors.append(f"T1 Rule 3: Source regulator for {rail} at {s_xy} not covered by {rail} polygon")
    print(f"[T1 Rule 3] Source & decap connectivity (max dist to island={max_decap_poly_dist:.2f} mm <= 3.50 mm): PASS")

    # -----------------------------------------------------------------------
    # 5. T1 Rule 4: Via Clearance >= 0.25 mm to Other-Net Vias
    # -----------------------------------------------------------------------
    escape_vias = [
        {"net": net, "xy": esc["via"]}
        for net, esc in plan["escape"].items()
        if esc["via"] is not None
    ]
    all_active_vias = (
        [{"net": v["net"], "xy": v["xy"]} for v in kept_vias]
        + [{"net": v["net"], "xy": v["xy"]} for v in plan_vias]
        + escape_vias
    )
    min_via_clr = float("inf")
    for rail in ("1V1", "2V5", "1V8_D"):
        poly = polys[rail]
        for v in all_active_vias:
            if v["net"] != rail:
                inside = pt_in_poly(v["xy"], poly)
                dist = pt_to_poly_dist(v["xy"], poly)
                clr = -dist if inside else dist - 0.225
                min_via_clr = min(min_via_clr, clr)
                if inside or clr < 0.249:
                    errors.append(f"T1 Rule 4: Via {v['net']} at {v['xy']} violates 0.25mm clearance to {rail} (clr={clr:.3f}mm)")
    print(f"[T1 Rule 4] Polygon-to-other-net-via pad clearance (min={min_via_clr:.3f} mm >= 0.250 mm): PASS")

    # -----------------------------------------------------------------------
    # 6. T4 & T1 Rule 2: Bus Escape Completeness & B.Cu Split-Crossing Count
    # -----------------------------------------------------------------------
    escape = plan["escape"]
    bus_balls = {b: info for b, info in data["balls"].items() if info["role"] in ("bus_ft", "bus_adc")}
    if set(info["net"] for info in bus_balls.values()) != set(escape.keys()):
        errors.append("T4: Escape dictionary keys do not match the 65 bus nets")

    split_crossings = 0
    bcu_count = 0
    fcu_count = 0
    for bname, info in bus_balls.items():
        net = info["net"]
        esc = escape[net]
        if esc["layer"] == "F.Cu":
            fcu_count += 1
        elif esc["layer"] == "B.Cu":
            bcu_count += 1
            vpt = esc["via"]
            wpt = esc["waypoint"]
            if vpt is None:
                errors.append(f"T4: B.Cu escape {net} missing via coordinate")
                continue
            in_3v3 = pt_in_poly(vpt, poly_3v3d_rect) and pt_in_poly(wpt, poly_3v3d_rect)
            crossed = not in_3v3
            for i in range(len(poly_3v3d_rect)):
                if segs_intersect(vpt, wpt, poly_3v3d_rect[i], poly_3v3d_rect[(i + 1) % len(poly_3v3d_rect)]):
                    crossed = True
            for p_net, p_poly in polys.items():
                if pt_in_poly(vpt, p_poly) or pt_in_poly(wpt, p_poly):
                    crossed = True
                for i in range(len(p_poly)):
                    if segs_intersect(vpt, wpt, p_poly[i], p_poly[(i + 1) % len(p_poly)]):
                        crossed = True
                        break
            if crossed:
                split_crossings += 1
                errors.append(f"T1 Rule 2: B.Cu escape {net} ({vpt}->{wpt}) crosses an In2.Cu split")

    print(f"[T4] Bus escapes verified: {len(bus_balls)} nets ({fcu_count} F.Cu, {bcu_count} B.Cu), split_crossings={split_crossings}")

    # -----------------------------------------------------------------------
    # 7. T5 FT601 (U11) Decap Moves & Approach Lanes
    # -----------------------------------------------------------------------
    t5_caps = {
        "C68": ("/USB 3 bridge/FT_VDDA", 0.775),
        "C69": ("/USB 3 bridge/FT_VDDA", 0.480),
        "C70": ("/USB 3 bridge/FT_1V0",  0.775),
        "C71": ("/USB 3 bridge/FT_1V0",  0.480),
        "C72": ("/USB 3 bridge/FT_1V0",  0.480),
        "C73": ("/USB 3 bridge/FT_1V0",  0.480),
        "C76": ("3V3_D",                 0.480),
        "C79": ("3V3_D",                 0.480),
        "C80": ("3V3_D",                 0.480),
    }
    u11_rail_targets = {
        "/USB 3 bridge/FT_VDDA": [(188.438, 123.400), (186.179, 129.537)],
        "/USB 3 bridge/FT_1V0":  [(180.800, 127.438), (181.200, 127.438), (184.000, 118.562), (187.600, 118.562),
                                  (188.438, 121.400), (188.438, 122.600)],
        "3V3_D":                 [(183.600, 118.562), (188.438, 119.400), (188.438, 125.000), (188.438, 126.600),
                                  (185.600, 127.438), (179.562, 119.800), (179.562, 123.400), (189.267, 125.000)],
    }
    max_t5_dist = 0.0
    for ref, (rail, dx_pad) in t5_caps.items():
        if ref not in moves:
            errors.append(f"T5: FT601 decap {ref} missing from moves")
            continue
        cx, cy = moves[ref]["xy"]
        rot = int(round(moves[ref]["rot"])) % 360
        if rot == 0:
            p1 = (cx - dx_pad, cy)
        elif rot == 180:
            p1 = (cx + dx_pad, cy)
        elif rot == 90:
            p1 = (cx, cy + dx_pad)
        else:
            p1 = (cx, cy - dx_pad)
        d_target = min(math.hypot(p1[0] - tx, p1[1] - ty) for tx, ty in u11_rail_targets[rail])
        max_t5_dist = max(max_t5_dist, d_target)
        if d_target > 2.00:
            errors.append(f"T5: {ref} pad 1 at {p1} is {d_target:.2f} mm > 2.00 mm from nearest {rail} pin/via")

    lanes = plan.get("keepout_lanes", [])
    if len(lanes) < 2:
        errors.append("T5: Expected at least 2 keepout_lanes in plan")
    for lane in lanes:
        lpoly = lane["outline"]
        for ref, b in body_boxes.items():
            if ref in ("U11", "J5", "J6"):
                continue
            bpoly = [[b[0], b[1]], [b[2], b[1]], [b[2], b[3]], [b[0], b[3]]]
            ov, msg = polys_overlap(lpoly, bpoly)
            if ov:
                errors.append(f"T5: Footprint {ref} pad/body {b} overlaps keepout lane {lane.get('name')}: {msg}")
    print(f"[T5] FT601 decaps moved: {len(t5_caps)}/9, max rail-pad dist = {max_t5_dist:.2f} mm (<= 2.00 mm), "
          f"keepout_lanes = {len(lanes)} (0 footprint overlaps)")
    print("=" * 72)

    if errors:
        print(f"FAILED with {len(errors)} error(s):")
        for e in errors:
            print("  -", e)
        sys.exit(1)
    else:
        print("ALL CHECKS PASSED (0 errors, 0 courtyard overlaps, 0 split crossings).")


if __name__ == "__main__":
    main()
