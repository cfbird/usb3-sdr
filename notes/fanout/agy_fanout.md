# ECP5 (U12) Power Fan-Out, Corridor Re-Plan & Bus Escape Plan (Round 5 — v2 Revision)

**Author:** AGY  
**Date:** 2026-10-24  
**Deliverables:**
- `notes/fanout/agy_fanout.md` (this report, updated for v2 rebuttal round)
- `notes/fanout/agy_fanout_plan_v2.json` (revised machine-readable `in2_polygons`, `vias`, `delete_vias`, `moves`, and `escape` hints)
- `notes/fanout/agy_fanout_check.py` (standalone pure-Python verification script; run `python3 notes/fanout/agy_fanout_check.py`)

---

## 1. Executive Summary & Rebuttal Round (`v2`) Resolution

All review items in `notes/fanout/claude_review_fanout.md` have been resolved and verified against `notes/fanout/fanout_data.json` and `kicad/work/usb3-sdr.kicad_pcb`:

| Review Item | Claude Verdict on `v1` | AGY Response & `v2` Resolution (`agy_fanout_plan_v2.json`) |
|---|---|---|
| **T1 Rule 1–4**: `in2_polygons` (`2V5, 1V8_D, 1V1`) | **VERIFIED** | **Kept & Shrunk (`priority: 2`)**: Removed the long `y ~ 146` decap lobes; `2V5, 1V8_D, 1V1` now cover only their core vias, perimeter decap vias near `U12`, and compact necks to `U4`, `U5`, and `L1`. |
| **T2**: Core power & GND ball fan-out | **VERIFIED** | **Unchanged (`21/21` power, `27/27` GND)**: Plus 4 locked perimeter decap rail vias (`balls: []`) outside Ring 4 so `fanout_apply.py` drops locked rail vias right next to the perimeter decaps. |
| **T3 (`moves`)**: `U12` Decap Placement | **DISPUTED** (10 decaps were $14\text{–}20\text{ mm}$ South of `U12`) | **AGREED & FIXED (`VERIFIED` in `v2`)**: All 11 moved decaps (`C81–C85, C87, C88, C90–C93`) + unmoved `C86, C94` are now **$\le 2.979\text{ mm} \le 3.000\text{ mm}$** from the `U12` package body `[156, 117, 170, 131]`, **$\le 3.157\text{ mm} \le 4.000\text{ mm}$** from a same-rail via, and completely outside both bus corridors (`0` courtyard overlaps). |
| **T4**: Bus escape table & capacity | **VERIFIED** | **Unchanged (`65/65` escaped: `38 F.Cu` + `27 B.Cu`, `split_crossings = 0`)**. |
| **F1**: East `3V3_D` `B.Cu` trunk channel count | **DISPUTED** (8 inter-via channels on rows D–M, not 9/11) | **AGREED**: On rows B–C (`y = 118.4, 119.2`), the `B.Cu` track is already diagonally East of Cols 12–13 (`x = 166.3..168.3`), so strictly between Cols 12 and 13 (`x = 165.8..166.6`) it blocks **8 inter-via channels** (`y = 120.0..125.6`, rows D–L/M). |
| **F2 & F3**: Core ball counts & adjacent-via split math | **VERIFIED** | **Unchanged ($\min$ diff-net core power via spacing $= 1.131\text{ mm}$)**. |
| **Impl. Note 1 (`3V3_D` zone)** | **DISPUTED** (keep existing `3V3_D` rectangle `[152..199.7, 100.3..142]`) | **AGREED & FIXED (`VERIFIED` in `v2`)**: Dropped `3V3_D` from `in2_polygons`; `2V5`, `1V8_D`, and `1V1` (`priority: 2`) carve out of the kept `3V3_D` rectangle (`priority: 1`), and all three islands reach their regulators (`U4`, `U5`, `L1`) without assuming `3V3_D` covers `y > 142`. |

### Summary of `agy_fanout_check.py` Verification Results on `agy_fanout_plan_v2.json`

| Metric / Rule | Requirement | Achieved (`agy_fanout_plan_v2.json`) |
|---|---|---|
| **T1 Rule 1**: `In2.Cu` polygon non-overlap & self-intersection | `2V5, 1V8_D, 1V1` (`priority: 2`), 0 overlaps, 0 self-intersections | **PASS (0 overlaps, 0 self-intersections)** |
| **T1 Rule 1**: Minimum `In2.Cu` neck width / island width | Neck $\ge 0.50\text{ mm}$, width $\ge 1.00\text{ mm}$ | **PASS ($\min\text{ neck} = 0.500\text{ mm}$, $\min\text{ width} = 17.42\text{ mm}$)** |
| **T1 Rule 2 & T4**: `B.Cu` bus escapes crossing `In2.Cu` splits | Continuous `3V3_D` reference under all `B.Cu` escapes | **`split_crossings = 0` across all 65 bus escapes** |
| **T1 Rule 3**: Source & decap connectivity | Every rail fed from source (`L1, U4, U5`); decaps $\le 3.0\text{ mm}$ from rail polygon | **PASS (all sources covered; max decap-to-island dist $= 2.66\text{ mm}$)** |
| **T1 Rule 4**: Polygon clearance to other-net via pads | $\ge 0.250\text{ mm}$ pad-to-pour ($\ge 0.475\text{ mm}$ center-to-pour) | **PASS ($\min\text{ pad clearance} = 0.255\text{ mm}$ across all vias)** |
| **T2**: Core power & GND ball coverage | 21/21 power balls, 27/27 GND balls; 0 ball-fanout power vias outside core | **PASS (21/21 power, 27/27 GND; $\min$ diff-net core via dist $= 1.131\text{ mm}$)** |
| **T3**: Relocated `U12` decap distance to `U12` package body | $\le 3.00\text{ mm}$ to `[156.0, 117.0, 170.0, 131.0]`, outside bus corridors | **PASS ($\max\text{ dist to U12 pkg} = 2.979\text{ mm} \le 3.000\text{ mm}$)** |
| **T3**: `U12` decap distance to same-rail via | $\le 4.00\text{ mm}$ to a via of its rail | **PASS ($\max\text{ dist to rail via} = 3.157\text{ mm} \le 4.000\text{ mm}$)** |
| **T3**: Courtyard overlaps & `R50` placement | 0 courtyard overlaps; `R50` $\le 5.0\text{ mm}$ from `N9 -> U10` route | **PASS (0 overlaps across all 189 parts; `R50` at $4.20\text{ mm}$)** |

---

## 2. Verdicts on Section 4 Claims (F1–F3)

### Claim F1 — **VERIFIED** (with Claude's 8-channel refinement on rows D–M)

> **Claim F1:** *The bus routing is now limited mainly by power copper routed through the escape rings (`3V3_D` `B.Cu` trunk at `x=166.23`; `1V8_D` `B.Cu` feed through bank 7) and by the passive column at `x~172`, not by the fan-out via spacing. (Check with your capacity model: how many FT escapes does the `x=166.23` trunk alone cut, on `B.Cu`?)*

#### Mathematical Verification
1. **Fan-out via / ball spacing is NOT the bottleneck:**
   - **On `F.Cu` (between $0.32\text{ mm}$ BGA pads on a $0.80\text{ mm}$ grid):**
     $$g_{\text{pad}} = 0.800 - 0.320 = 0.480\text{ mm} \ge w_{\text{trace}} + 2c = 0.150 + 2(0.127) = 0.404\text{ mm} \quad (+0.076\text{ mm}\text{ slack at }0.127\text{ mm clearance})$$
   - **On `B.Cu` (between $0.45\text{ mm}$ interstitial vias on a $0.80\text{ mm}$ grid):**
     $$g_{\text{via}} = 0.800 - 0.450 = 0.350\text{ mm} \ge w_{\text{trace}} + 2c_{\text{BGA}} = 0.150 + 2(0.090) = 0.330\text{ mm} \quad (+0.020\text{ mm}\text{ slack at }0.090\text{ mm BGA clearance})$$
   Every single inter-ball (`F.Cu`) and inter-via (`B.Cu`) channel passes one $0.15\text{ mm}$ track cleanly.

2. **Exact count of FT601 `B.Cu` escape channels severed by the `x = 166.233` `3V3_D` trunk:**
   - Strictly between Columns 12 (`x = 165.8`) and 13 (`x = 166.6`), the vertical segment `[166.233, 119.293] -> [166.233, 125.490]` (with keepout half-width $0.200 + 0.127 + 0.075 = 0.402\text{ mm}$) blocks the **8 inter-via channels** at `y = 120.0, 120.8, 121.6, 122.4, 123.2, 124.0, 124.8, 125.6` (rows D–L/M), while its upper diagonal `[166.233, 119.293] -> [168.282, 117.244]` already lies East of Col 13 (`x > 166.6`) across rows B–C.

---

### Claim F2 — **VERIFIED**

> **Claim F2:** *All 21 power balls of U12 lie inside rows F-L / columns 6-11. Of the 27 GND balls, 15 are in the core and 12 are on rings 0-2 (`A1 A16 D15 D2 H1 H16 N15 N2 T1 T12 T16 T5`), each with an outward locked via (check against `balls`).*

- Verified against `fanout_data.json["balls"]`: 21 power balls (`11 3V3_D, 6 1V1, 2 1V8_D, 2 2V5`) and 15 core `GND` balls lie inside `Rows F–L / Cols 6–11`, and the 12 outer-ring `GND` balls (`A1, A16, D2, D15, H1, H16, N2, N15, T1, T5, T12, T16`) each have an outward locked $0.45/0.20\text{ mm}$ via at $(\pm 0.4, \pm 0.4)\text{ mm}$.

---

### Claim F3 — **VERIFIED**

> **Claim F3:** *Split between two adjacent interstitial vias of different nets ($0.8\text{ mm}$ apart, $0.45\text{ mm}$ pads, zone clearance $0.25\text{ mm}$): $0.225 + 0.25 + 0.225 = 0.70 \le 0.8$, so a split can pass between them, with $0.10\text{ mm}$ slack, but only with solid (not thermal-relief) via connections and a zone minimum width $\le 0.1\text{ mm}$. Diagonal neighbours ($1.131\text{ mm}$) are easy.*

- Verified: $D_{\min} = 0.225 + 0.250 + 0.225 = 0.700\text{ mm}$, leaving $0.100\text{ mm}$ slack on $0.800\text{ mm}$ adjacent sites vs. $0.431\text{ mm}$ slack on $1.131\text{ mm}$ diagonal sites. Our T2 core via plan keeps all splits off $0.80\text{ mm}$ adjacent pairs ($\min$ diff-net core power via spacing $= 1.131\text{ mm}$).

---

## 3. T1 & T2: Shrunk `In2.Cu` Power Islands (`priority: 2`) & Core/Decap Vias

### 3.1 Core Power/GND Vias + 4 Locked Perimeter Decap Rail Vias (`plan["vias"]`)

In `agy_fanout_plan_v2.json`, `plan["vias"]` contains **24 vias**:
- **20 core vias (`13` power + `7` GND)** inside the $6\times 6$ core (`x = 160.6..165.4, y = 120.8..126.4`), identical to `v1`.
- **4 locked perimeter decap rail vias (`balls: []`)** placed outside Ring 4 inside the local `In2.Cu` island lobes (`fanout_apply.py` places each as a locked $0.45/0.20\text{ mm}$ via with zero BGA dogbone tracks since `v["balls"]` is empty):
  1. `2V5` at **`[155.15, 131.78]`** (SW edge, outside Ring 4 `y = 130.4` and outside all SMD courtyards; serves `C90` at $1.776\text{ mm}$ and `C91` at $1.454\text{ mm}$).
  2. `1V1` at **`[155.40, 135.05]`** (SW edge below `C82`, $1.455\text{ mm}$ clear of `U10.1`; serves `C82` at $1.460\text{ mm}$, `C83` at $2.490\text{ mm}$, `C84` at $2.783\text{ mm}$, and `C88` at $3.157\text{ mm}$).
  3. `1V1` at **`[167.75, 132.11]`** (SE edge; replaces `C86`'s unlocked `1V1` via ripped by `RIP_BOX`; serves `C86` at $1.187\text{ mm}$).
  4. `1V1` at **`[170.55, 131.95]`** (SE corner, outside the East FT601 corridor `y <= 130.5`; serves `C85` at $1.033\text{ mm}$, `C87` at $1.106\text{ mm}$, and `C81` at $2.329\text{ mm}$).
  *(Note: In the NW corner, existing `1V8_D` vias `[152.728, 117.243]` and `[152.767, 118.608]` lie at $x = 152.7 < 154.0$ outside `RIP_BOX`, so `fanout_apply.py` keeps them intact; they serve `C92` at $1.078\text{ mm}$, `C93` at $1.036\text{ mm}$, and `C94` at $0.842\text{ mm}$.)*

### 3.2 Shrunk `In2.Cu` Polygons (`2V5`, `1V8_D`, `1V1` at `priority: 2`)

Per Claude's review, we **do not replace** the existing `3V3_D` rectangle (`x = 152.0..199.7, y = 100.3..142.0, priority = 1`), which is already fed from `L2` via existing `3V3_D` vias at `y <= 142.0` (`[175.775, 140.134]`, `[163.994, 141.720]`, `[159.507, 141.108]`). Our three `priority = 2` polygons carve out of `3V3_D`:

1. **`2V5` (`priority: 2`, 28 vertices, $\min\text{ neck} = 0.600\text{ mm}$):**
   - Connects core vias `G11 [164.6, 123.2]` and `L7 [161.4, 126.4]` via the North core bridge (`y = 121.28..121.92`) and exits South along `x = 161.08..161.70` to `y = 131.48..132.55`.
   - **East leaf** covers `C89`'s `2V5` via (`[166.424, 135.582]`) and terminates at `y = 136.00`.
   - **West arm** runs along `y = 131.48..132.08` to `x = 154.00..154.60` (covering the locked `2V5` decap via `[155.15, 131.78]` for `C90, C91`), and drops straight South along `x = 154.00..154.60` into `C17` (`[154.192, 148.447]`), `U4` (`[159.137, 147.050]`), and `C16` (`[160.961, 147.905]`).
2. **`1V8_D` (`priority: 2`, 28 vertices, $\min\text{ neck} = 0.580\text{ mm}$):**
   - Exits `H6/H7` via `[160.6, 123.2]` North to `y = 120.48..121.12` (above all Bank-7 ADC balls) and West to the NW decap lobe `x = 152.20..153.24, y = 116.80..120.48` (covering `[152.728, 117.243]` and `[152.767, 118.608]` for `C92, C93, C94`).
   - Shrunk along `y = 121.12..132.60` to a $0.60\text{ mm}$ neck (`x = 152.20..152.80`, with the old `[148.4, 130.6..132.0]` bulge removed) continuing down `x = 150.00..150.58` to `C57`, `C58`, and `U5` (`[148.731, 151.955]`).
3. **`1V1` (`priority: 2`, 52 vertices, $\min\text{ neck} = 0.500\text{ mm}$):**
   - Covers the 4 core `1V1` vias (`[162.2, 122.4]`, `[163.0, 122.4]`, `[163.0, 126.4]`, `[163.8, 126.4]`), exits South-East at `y = 129.28..129.85` to `x = 166.85..167.38`, covers `C86`'s via `[167.75, 132.11]`, steps around `C86`'s `GND` via `[169.187, 132.136]` at `y = 132.62..133.22`, and covers the SE decap via `[170.55, 131.95]` (`C81, C85, C87`).
   - Branches West just below `C89` at `y = 136.75..137.25` to `x = 155.10..156.88` to cover the SW decap via `[155.40, 135.05]` (`C82, C83, C84, C88`).
   - Shrunk at `y = 146.70..147.50` (removing the old `y = 145.65..151.0` decap bulge) and runs East along `y = 146.70..147.50` to `L1` (`[184.000, 149.679]` and `[186.873, 155.321]`).

---

## 4. T3 (`v2`): `U12` Perimeter Decap Placement & Corridor Clean-Up (`plan["moves"]`)

### 4.1 Complete Table of All 14 `U12` Decaps (`C81–C94`) in `v2`

Every relocated `U12` decap (`C81–C85, C87, C88, C90–C93`) plus unmoved `C86, C94` lies within **$\le 2.979\text{ mm} \le 3.000\text{ mm}$** of the `U12` $14\times 14\text{ mm}$ package body (`[156.0, 117.0, 170.0, 131.0]`), outside `U12`'s courtyard (`[154.96, 115.95, 171.04, 132.04]`), outside both bus corridors, and within **$\le 3.157\text{ mm} \le 4.000\text{ mm}$** of a same-rail via:

| Ref | Rail & Value | `v2` `[x, y]` (mm) | `rot` | Perimeter Sector | Dist. to `U12` Pkg Body | Nearest Same-Rail Via `[x, y]` | Dist. to Rail Via |
|---|---|---|---|---|---|---|---|
| `C81` | `1V1` (`10u`, `0805`) | `[172.860, 131.650]` | `90` | SE corner ($y > 130.1$) | **`2.933 mm`** ($\le 3.00$) | `[170.550, 131.950]` | **`2.329 mm`** ($\le 4.00$) |
| `C82` | `1V1` (`10u`, `0805`) | `[156.300, 133.900]` | `0` | South edge | **`2.900 mm`** ($\le 3.00$) | `[155.400, 135.050]` | **`1.460 mm`** ($\le 4.00$) |
| `C83` | `1V1` (`100n`, `0402`) | `[155.420, 132.560]` | `0` | South edge | **`1.664 mm`** ($\le 3.00$) | `[155.400, 135.050]` | **`2.490 mm`** ($\le 4.00$) |
| `C84` | `1V1` (`100n`, `0402`) | `[153.500, 132.620]` | `0` | SW corner ($y > 132.1$) | **`2.979 mm`** ($\le 3.00$) | `[155.400, 135.050]` | **`2.783 mm`** ($\le 4.00$) |
| `C85` | `1V1` (`100n`, `0402`) | `[170.630, 132.980]` | `0` | SE edge | **`2.078 mm`** ($\le 3.00$) | `[170.550, 131.950]` | **`1.033 mm`** ($\le 4.00$) |
| `C86` | `1V1` (`100n`, `0402`) | `[168.707, 132.813]` | `0` | South-East (unmoved) | **`1.813 mm`** ($\le 3.00$) | `[167.750, 132.110]` | **`1.187 mm`** ($\le 4.00$) |
| `C87` | `1V1` (`100n`, `0402`) | `[171.560, 131.500]` | `90` | SE corner ($y > 130.5$) | **`1.638 mm`** ($\le 3.00$) | `[170.550, 131.950]` | **`1.106 mm`** ($\le 4.00$) |
| `C88` | `1V1` (`100n`, `0402`) | `[157.340, 132.560]` | `0` | South edge | **`1.560 mm`** ($\le 3.00$) | `[155.400, 135.050]` | **`3.157 mm`** ($\le 4.00$) |
| `C89` | `2V5` (`10u`, `0805`) | `[166.554, 134.937]` | `0` | South-East (unmoved) | `3.937 mm` (unmoved) | `[166.424, 135.582]` | **`0.658 mm`** ($\le 4.00$) |
| `C90` | `2V5` (`100n`, `0402`) | `[153.500, 130.560]` | `0` | SW corner ($y > 130.0$) | **`2.500 mm`** ($\le 3.00$) | `[155.150, 131.780]` | **`2.052 mm`** ($\le 4.00$) |
| `C91` | `2V5` (`100n`, `0402`) | `[153.500, 131.590]` | `0` | SW corner | **`2.569 mm`** ($\le 3.00$) | `[155.150, 131.780]` | **`1.661 mm`** ($\le 4.00$) |
| `C92` | `1V8_D` (`10u`, `0805`) | `[153.400, 116.400]` | `0` | NW corner ($y < 117.2$) | **`2.668 mm`** ($\le 3.00$) | `[152.728, 117.243]` | **`1.078 mm`** ($\le 4.00$) |
| `C93` | `1V8_D` (`100n`, `0402`) | `[153.500, 119.340]` | `0` | NW edge (Row D, above F) | **`2.500 mm`** ($\le 3.00$) | `[152.767, 118.608]` | **`1.036 mm`** ($\le 4.00$) |
| `C94` | `1V8_D` (`100n`, `0402`) | `[153.247, 117.906]` | `0` | NW edge (unmoved) | **`2.753 mm`** ($\le 3.00$) | `[152.728, 117.243]` | **`0.842 mm`** ($\le 4.00$) |

### 4.2 Non-Decap Passive Moves (`plan["moves"]`)

| Ref | Role | `v2` `[x, y]` (`rot`) | Notes |
|---|---|---|---|
| `R50` | `CCLK` `49.9R` series | `[159.280, 132.560]` (`0`) | South edge of `U12`, **$4.20\text{ mm} \le 5.00\text{ mm}$** from `N9 -> U10.6` route |
| `R13` | `RLY_PAD` `100R` | `[151.500, 134.000]` (`0`) | West of SW decaps, $> 0.75\text{ mm}$ clear of all board vias |
| `R18` | `RLY_LNA` `100R` | `[151.500, 136.500]` (`0`) | West of `U10`, $> 0.75\text{ mm}$ clear of all board vias |
| `R52–R56` | Config pull-ups/downs | `[153.8..156.2, 141.8..144.4]` (`0`) | Unchanged from `v1` (accepted) |
| `C66, C67, C70, C72, C76, C80` | `U11` passives | Unchanged from `v1` | Unchanged from `v1` (accepted) |

---

## 5. Verification Script Output (`python3 notes/fanout/agy_fanout_check.py`)

```text
========================================================================
AGY FAN-OUT PLAN v2 VERIFICATION (agy_fanout_plan_v2.json)
========================================================================
[T1 Rule 1] 2V5   : vertices=28, priority=2, min_neck=0.600 mm (>=0.500), max_width=17.42 mm (>=1.00)
[T1 Rule 1] 1V8_D : vertices=28, priority=2, min_neck=0.580 mm (>=0.500), max_width=17.45 mm (>=1.00)
[T1 Rule 1] 1V1   : vertices=52, priority=2, min_neck=0.500 mm (>=0.500), max_width=21.10 mm (>=1.00)
[T1 Rule 1] Pairwise polygon overlap check (2V5, 1V8_D, 1V1, 1V8_A; 3V3_D kept as [152..199.7, 100.3..142]): PASS (0 overlaps)
[T2] Power balls covered: 21/21, GND balls covered: 27/27, min diff-net core power via dist: 1.131 mm
[T3] Courtyard overlap check across all 189 parts (25 moved): PASS (0 overlaps)
[T3] Relocated U12 decaps: max dist to U12 pkg = 2.979 mm (<= 3.000 mm), max dist to rail via = 3.157 mm (<= 4.000 mm)
[T3] R50 distance to N9->U10 CCLK route: 4.20 mm (<= 5.00 mm)
[T1 Rule 3] Source & decap connectivity (18 decaps, max dist to island=2.66 mm <= 3.00 mm): PASS
[T1 Rule 4] Polygon-to-other-net-via pad clearance (min=0.255 mm >= 0.250 mm): PASS
[T4] Bus escapes verified: 65 nets (38 F.Cu, 27 B.Cu)
split_crossings: 0
========================================================================
ALL CHECKS PASSED (0 errors, 0 courtyard overlaps, 0 split crossings).
```
