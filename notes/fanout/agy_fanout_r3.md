# Round 3 Fan-Out Plan Revision (`agy_fanout_plan_v3.json`)

**Status:** All `In2.Cu` island fills (`1V1`, `2V5`, `1V8_D`, `3V3_D`) **VERIFIED (`OK`)** in real KiCad zone fill (`fanout_trial.py`), **0 DRC copper conflicts**, **0 rail gaps >= 5.0 mm**, and **T5 FT601 (`U11`) approach lanes** cleared with all 9 blocking decaps relocated within `<= 1.97 mm` of their rail pins/vias.

---

## 1. Summary of `In2.Cu` Island & Rail-Gap Fixes (Section 1)

| Rail / Issue in `plan_v2_claude.json` | Root Cause | Fix in `agy_fanout_plan_v3.json` | KiCad Trial Verdict |
|---|---|---|---|
| **1a. `1V1` split at `y = 142.3` (`18.1 mm` neck gap)** | East edge stepped left `[167.42, 142.3] -> [166.82, 142.3]` at the same `y = 142.3` where West edge stepped right `[166.20, 142.3] -> [166.85, 142.3]` (`-0.03 mm` width). Also `C8` (`100 nF` `1V1` buck output cap) was stranded at old buck location `(131.4, 145.2)` (`25 mm` gap). | Keep East edge at `x = 167.42` down to `y = 143.00` (`0.55 mm` from `GND` via `[167.318, 143.550]`) and keep West edge straight at `x = 166.26` from `y = 147.50` to `y = 137.25` (`0.478 mm` from `FPGA_TCK` via `[165.782, 141.715]`), giving a `0.56-1.16 mm` wide neck. Move `C8` beside `U2/L1/C6` to `[185.40, 146.15] rot 0` with `1V1` via `[184.92, 147.10]` (`0.95 mm`) and `GND` via `[186.60, 146.15]`. | **`1V1: OK, 1 filled piece`** (`9 vias`, `0` gaps `>= 5 mm`) |
| **1b. `1V8_D` split at `y = 132..134` (`18.6 mm` gap) + `U8` pad 13 (`7.2 mm` gap)** | `1V8_D` stepped West to `x = 150.0..150.6` at `y = 132.0..132.6`, overlapping the true priority-2 `1V8_A` rectangle `[134.0, 108.0, 152.0, 134.0]` on `In2.Cu`. Also `U8` pad 13 (`143.44, 140.75`) lost its `1V8_D` trace, and `C92/C93/C94` lost their unlocked NW `1V8_D` via. | Keep `1V8_D` neck at `x = 152.25..152.85` (`>= 0.25 mm` East of `1V8_A` `x = 152.0`) down to `y = 134.30..134.90` (`>= 0.30 mm` South of `1V8_A` `y = 134.0`) before stepping West to `x = 150.00..150.60`. Extend a `0.70 mm` West arm at `y = 140.25..140.95` to `x = 143.95` with a locked `1V8_D` via at `[144.30, 140.60]` (`0.88 mm` from `U8.13`), and add a locked NW `1V8_D` via at `[152.75, 118.00]` (`1.37 mm` from `C93.1`). | **`1V8_D: OK, 1 filled piece`** (`6 vias`, `0` gaps `>= 5 mm`) |
| **1c. `2V5` missing source via at `U4/C16` (`15.6 mm` gap)** | `U4` (`2V5` LDO) and `C16/C17` connected on `F.Cu` only with no `2V5` via inside `poly_2v5`'s regulator lobe. | Add locked `2V5` source via (`"balls": []`) at `[160.95, 147.05]` inside `poly_2v5` (`0.86 mm` from `C16.1`, `1.81 mm` from `U4.5`) and locked `C89` `2V5` via at `[165.35, 135.75]` (`0.92 mm` from `C89.1`). | **`2V5: OK, 1 filled piece`** (`5 vias`, `0` gaps `>= 5 mm`) |
| **1d. `3V3_D` split at `(160.6, 124.8)` & `(160.6, 125.6)` (`J6, J7, L6`)** | `poly_1v8` and `poly_2v5` pinched off the `69.3 mm^2` Bank-7 `3V3_D` region at `(160.95, 121.12) <-> (161.08, 121.28)` (`0.13 mm` gap), and `poly_2v5`'s `C89` branch touched `poly_1v1` at `x = 166.85`, isolating the South `3V3_D` pocket (`U10.8` / `J3.1`). | Merge core `1V1` via `[162.2, 122.4]` into `[163.0, 122.4]` (`G6, G7, G9`) and `GND` vias `[162.2, 123.2]` / `[162.2, 124.8]` into `[163.8, 123.2]` (`G8, H8, G10, H9, H10`) and `[162.2, 125.6]` (`J8, K6, K7, K8`), shifting `poly_2v5`'s upper West leg East to `x = 161.85..162.45` (`0.57 mm` `3V3_D` copper bridge). Pull `poly_2v5`'s `C89` branch West to `x = 165.70` (`1.15 mm` gap to `poly_1v1`) and add `3V3_D` via `[168.40, 139.63]` (`0.94 mm` from `J3.1`). | **`3V3_D: OK, 6 U12 vias, not on the main plane piece: []`** |

---

## 2. Section 0 Nudged Parts Folded into `moves`

All 7 `place_free.py` nudges from Section 0 of `BRIEF_fanout_r3.md` are folded directly into `agy_fanout_plan_v3.json["moves"]`:
- `R52`: `[155.70, 141.00]`, `rot = 0`
- `R53`: `[156.40, 143.40]`, `rot = 0`
- `R54`: `[152.40, 143.50]`, `rot = 90`
- `R55`: `[154.30, 141.70]`, `rot = 90`
- `R56`: `[151.40, 144.20]`, `rot = 270`
- `C66`: `[189.80, 133.40]`, `rot = 0`
- `C67`: `[191.80, 134.90]`, `rot = 0`

---

## 3. T5: FT601 (`U11`) Decap Moves & Approach Lanes (Section 2)

### 3.1 Relocated FT601 Decaps (`<= 1.97 mm` from Rail Pin/Via)

| Ref | Size | Rail | Old `xy` | New `xy` | New `rot` | Rail Pad (`pad 1`) `xy` | Nearest Rail Pin / Via | Distance |
|---|---|---|---|---|---|---|---|---|
| `C68` | `0603` | `FT_VDDA` | `(183.00, 116.76)` | `[185.40, 131.10]` | `180` | `(186.175, 131.100)` | `FB3.2 (186.179, 129.537)` | **`1.56 mm`** |
| `C69` | `0402` | `FT_VDDA` | `(186.16, 117.06)` | `[189.85, 123.00]` | `0` | `(189.370, 123.000)` | `U11.28 (188.438, 123.400)` | **`1.01 mm`** |
| `C70` | `0603` | `FT_1V0` | `(176.89, 120.79)` | `[180.46, 130.15]` | `270` | `(180.460, 129.375)` | `U11.2 (180.800, 127.438)` | **`1.97 mm`** |
| `C71` | `0402` | `FT_1V0` | `(179.79, 129.40)` | `[183.80, 116.30]` | `90` | `(183.800, 116.780)` | `U11.48 (184.000, 118.562)` | **`1.79 mm`** |
| `C72` | `0402` | `FT_1V0` | `(177.57, 127.05)` | `[184.85, 116.30]` | `90` | `(184.850, 116.780)` | `U11.48 (184.000, 118.562)` | **`1.97 mm`** |
| `C73` | `0402` | `FT_1V0` | `(179.79, 116.98)` | `[187.42, 116.85]` | `90` | `(187.420, 117.330)` | `U11.39 (187.600, 118.562)` | **`1.25 mm`** |
| `C76` | `0402` | `3V3_D` | `(177.43, 118.62)` | `[182.75, 116.30]` | `90` | `(182.750, 116.780)` | `U11.49 (183.600, 118.562)` | **`1.97 mm`** |
| `C79` | `0402` | `3V3_D` | `(180.47, 130.92)` | `[190.16, 117.90]` | `0` | `(189.680, 117.900)` | `U11.38 (188.438, 119.400)` | **`1.95 mm`** |
| `C80` | `0402` | `3V3_D` | `(177.32, 128.44)` | `[191.20, 125.10]` | `0` | `(190.720, 125.100)` | `3V3_D via (189.267, 125.000)` | **`1.46 mm`** |

*(Note: `C74` (`0603`, `3V3_D`) is also shifted `1.7 mm` South to `[186.00, 133.15] rot 0` (`0.83 mm` from its `3V3_D` via `[185.23, 132.32]`) so `C68` (`0603`, `FT_VDDA`) sits directly below `FB3` with zero courtyard or pad overlap. Obsolete vias `[181.095, 116.319]` (`FT_1V0`) and `[185.15, 117.588]` (`FT_VDDA`) inside the top approach lane are added to `delete_vias` so their `F.Cu`/`B.Cu` stubs are ripped cleanly.)*

### 3.2 Approach Lane Polygons (`keepout_lanes`)

1. **`U11_top_row_FIFO_D0_D15`** (`F.Cu`, feeds `FT_D0..FT_D15` at `x = 180.4..187.2, y = 118.562`):
   - Outline: `[[174.50, 115.40], [182.20, 115.40], [182.20, 117.05], [185.40, 117.05], [185.40, 115.40], [186.85, 115.40], [186.85, 117.60], [187.25, 117.60], [187.25, 118.10], [174.50, 118.10]]`
   - Provides a `2.70 mm` high (`y = 115.40..118.10`) NW entrance across `x = 174.50..182.20` (`8+` tracks at `0.30 mm` pitch), a `1.05 mm` clear channel (`y = 117.05..118.10`) below `C76/C71/C72`, and a `2.70 mm` pocket (`y = 115.40..118.10`) at `x = 185.40..186.85` feeding `FT_D0..FT_D5`.
2. **`U11_bottom_row_FIFO_ctrl`** (`F.Cu`, feeds `FT_BE0..FT_OE_N` at `x = 181.6..185.2, y = 127.438`):
   - Outline: `[[174.50, 127.90], [185.30, 127.90], [185.30, 128.50], [179.65, 128.50], [179.65, 130.80], [174.50, 130.80]]`
   - Provides a `2.90 mm` high (`y = 127.90..130.80`) SW entrance across `x = 174.50..179.65` (`9+` tracks at `0.30 mm` pitch) feeding into the clear horizontal channel (`y = 127.88..128.90`) directly below `U11` pins `4..13` (`FT_BE0..FT_OE_N`).

---

## 4. Final `fanout_trial.py` Output

```text
3 In2 zones, 30 vias, 32 moves

== In2 islands (KiCad fill)
1V1: OK, 1 filled piece(s)
   piece 0 bbox (155.95,122.13)-(187.30,155.75) vias [(184.92, 147.1), (163.0, 122.4), (156.3, 135.05), (163.8, 126.4), (167.75, 132.11), (170.55, 131.95), (186.87, 155.32), (184.0, 149.68), (163.0, 126.4)]
2V5: OK, 1 filled piece(s)
   piece 0 bbox (153.75,121.28)-(165.70,148.90) vias [(165.35, 135.75), (155.15, 131.78), (164.6, 123.2), (160.95, 147.05), (161.4, 126.4)]
1V8_D: OK, 1 filled piece(s)
   piece 0 bbox (143.95,116.80)-(160.90,152.50) vias [(150.09, 140.24), (144.3, 140.6), (150.39, 142.1), (160.6, 123.2), (148.73, 151.96), (152.75, 118.0)]
3V3_D: OK, 6 U12 vias, not on the main plane piece: []

== DRC copper conflicts: 0

== rail unconnected: 26 short pairs < 5.0 mm (stubs Claude routes on F.Cu), 0 longer (the plan's islands/necks must carry these)
```

## 5. Final `agy_fanout_check.py` Output

```text
========================================================================
AGY FAN-OUT PLAN v3 VERIFICATION (agy_fanout_plan_v3.json)
========================================================================
[T1 Rule 1] 2V5   : vertices=32, priority=2, min_neck=0.600 mm (>=0.500), max_width=17.42 mm (>=1.00)
[T1 Rule 1] 1V8_D : vertices=32, priority=2, min_neck=0.580 mm (>=0.500), max_width=18.10 mm (>=1.00)
[T1 Rule 1] 1V1   : vertices=46, priority=2, min_neck=0.500 mm (>=0.500), max_width=21.04 mm (>=1.00)
[T1 Rule 1] Pairwise polygon overlap check (incl. true 1V8_A [134..152, 108..134], clr=0.250 mm): PASS
[T2] Power balls covered: 21/21, GND balls covered: 27/27, min diff-net core power via dist: 1.131 mm
[T3] Footprint overlap check across all 189 parts (32 moved): PASS (0 overlaps)
[T3] Relocated U12 decaps: max dist to U12 pkg = 2.979 mm (<= 3.000 mm), max dist to rail via = 3.707 mm (<= 4.000 mm)
[T3] R50 distance to N9->U10 CCLK route: 4.20 mm (<= 5.00 mm)
[T1 Rule 3] Source & decap connectivity (max dist to island=3.25 mm <= 3.50 mm): PASS
[T1 Rule 4] Polygon-to-other-net-via pad clearance (min=0.255 mm >= 0.250 mm): PASS
[T4] Bus escapes verified: 65 nets (38 F.Cu, 27 B.Cu), split_crossings=0
[T5] FT601 decaps moved: 9/9, max rail-pad dist = 1.97 mm (<= 2.00 mm), keepout_lanes = 2 (0 footprint overlaps)
========================================================================
ALL CHECKS PASSED (0 errors, 0 courtyard overlaps, 0 split crossings).
```
