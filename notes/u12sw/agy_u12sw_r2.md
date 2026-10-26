# U12 South-West Route Plan — Round 2 (`agy_u12sw_plan_r2.json`)

**Author:** AGY  
**Date:** 2026-10-26  
**Deliverables:** `notes/u12sw/agy_u12sw_plan_r2.json`, `notes/u12sw/agy_u12sw_r2.md`

---

## 1. Summary & Verification Status

- **RF-to-digital spacing (`>= 0.65 mm` edge-to-edge on same layer)**: **VERIFIED** via `python3 kicad/gen/rf_spacing.py /tmp/u12k/usb3-sdr.kicad_pcb --base kicad/work/usb3-sdr.kicad_pcb 2>/dev/null` — **0 pairs total on the entire board** (exit code `0`), eliminating all 13 `NEW` pairs from Round 1 **and** all 5 pre-existing pairs on `kicad/work` (`ADC_D6 / LNA_BYP`, `ADC_D6 / LNA_IN`, `ADC_D6 / LPF2_IN`, `ADC_D8 / NOTCH_OUT`, `REF10M / LPF2_OUT`).
- **All 33 open connections (29 open nets) closed (`unconnected: 33 -> 0`, `all still open: []`)**: **VERIFIED** via `python3 kicad/gen/u11_trial.py notes/u12sw/agy_u12sw_plan_r2.json --keep /tmp/u12k 2>/dev/null`.
- **0 new copper DRC errors (`new copper DRC errors: 0`)**: **VERIFIED**.
- **0 broken nets (`BROKEN: []`) and 0 dangling items (`plan items dangling: 0`)**: **VERIFIED**.
- **All In2.Cu power island slivers healed without editing zone outlines**: **VERIFIED**.
- **All 15 ADC high-speed nets (`ADC_D0..ADC_D13`, `ADC_OR`) + `ADC_DCO` + 3 SPI nets (`ADC_CSB`, `ADC_SCLK`, `ADC_SDIO`) pass `agy_timing_check.py`**: **VERIFIED** (`ADC_DCO = 30.75 mm`, data bus span `[27.74, 42.58] mm` = `14.84 mm`, skew to `ADC_DCO` within `[-3.00, +11.83] mm` vs `±25 mm` limit, all `U8 -> R` stubs `1.17 .. 6.00 mm <= 8.00 mm`).
- **Fewer vias & cleaner geometry than Round 1**: **VERIFIED** — 175 track polylines comprising 703 segments + 100 vias = `803` items (11 fewer vias and 23 fewer items than Round 1), with only **5** segments `< 0.05 mm` and **`moves: {}` (0 part moves)**.

---

## 2. What Changed vs Round 1 (`agy_u12sw_plan.json`) and Why

All 163 RF-path copper items on the board live on **`F.Cu`** (`0` on `B.Cu`), with a continuous solid `GND` plane on **`In1.Cu`** (`0.21 mm` below `F.Cu`). Consequently, digital tracks on **`B.Cu`** are fully shielded from `F.Cu` RF traces by `In1.Cu` (`GND`), whereas any digital **`F.Cu` track** or **through-via** (`F.Cu` pad radius `0.225 mm`) within `0.65 mm` edge-to-edge of an `F.Cu` RF item couples across the surface microstrip dielectric.

Three targeted routing changes eliminate every RF-spacing violation without moving any components:

### A. `REF10M`, `LMK_SCL`, `ADC_DCO`, `ADC_OR`, `ADC_D13`, and `ADC_D9` Across the RF Corridor (`x = 137..146, y = 123..134`)
- **Why R1 failed (11 `NEW` pairs)**:
  1. In R1, `REF10M` and `LMK_SCL` popped up to `F.Cu` at `x = 138.6..145.6, y = 130.0..131.6` to bridge over the `B.Cu` `ADC` bus, placing their `F.Cu` bridges within `0.20..0.37 mm` of `LPF1_IN`, `LPF1_OUT`, `LNA_IN`, `LNA_BYP`, and `RF_A2`.
  2. In R1, `ADC_DCO`, `ADC_OR`, and `ADC_D13` were routed by A* and placed layer-change vias + short `F.Cu` hops at `(143.3..147.0, 125.7..130.6)` within `0.20..0.64 mm` of `LNA_BYP` and `NOTCH_OUT`.
- **R2 Fix**:
  1. **Removed the `F.Cu` bridge on `REF10M` and `LMK_SCL`**: Both nets now stay **100% on `B.Cu`** across the entire RF section from `x = 153.15` (`U12` West) all the way to `x = 126.48 / 117.80` (`y = 133.32` and `y = 133.60` between `x = 138.3` and `x = 144.5`). Instead of `REF10M / LMK_SCL` bridging over the `ADC` nets on `F.Cu`, the 5 western `ADC` nets (`ADC_OR`, `ADC_D13`, `ADC_DCO`, `ADC_D12`, `ADC_D11`) cross over `REF10M / LMK_SCL` on **`F.Cu`** South of `y = 131.20` (where they are already on `F.Cu` escaping `R24, R25, R27, R28, R40`) and drop to `B.Cu` at `(139.10, 132.22)`, `(138.50, 132.88)`, `(139.70, 132.02)`, `(141.45, 131.20)`, and `(142.10, 131.20)` (`> 1.0 mm` South of `C40.1 [LPF1_IN]`). We also ripped the pre-existing dangling `1V8_A` stub + via at `(138.755, 132.852)` (`uuids: 88e44668..., f1479567..., dd5e1b0c...`) to clear that corridor.
  2. **Replaced A* routes for `ADC_DCO`, `ADC_OR`, `ADC_D13` with 100% manual concentric `B.Cu` trunks**: They now run alongside `ADC_D12`, `ADC_D11`, and `ADC_D9` at `x = 143.50, 143.80, 144.10, 144.40, 144.70, 145.00` on `B.Cu` with **zero vias** inside the RF region (`x < 153.15`). This also shortens `ADC_DCO` from `34.90 mm` to `30.75 mm` (`R40 -> U12 = 27.31 mm`, closer to the `24..37 mm` data bus median) and reduces total plan vias by 11.

### B. `U12` West `F.Cu` Doorway (`ADC_D2`, `ADC_D6`, `ADC_D8`, `ADC_CSB`, `ADC_D4`, `ADC_SDIO`) vs `NOTCH_OUT` (`x = 150.50, y = 113..130`)
- **Why R1 failed (2 `NEW` pairs)**:
  In R1, the 6 vertical `F.Cu` tracks between `NOTCH_OUT` (`x = 150.50, w = 0.35`, right copper edge `150.675 mm`) and the `2V5 / 1V1` decap pads `C90.1 / C91.1 / C84.1` (left copper edge `152.740 mm`) ran at `x = 150.96..152.46` (`w = 0.15 mm`), placing `ADC_D2` (`0.14 mm` gap) and `ADC_D6` (`0.44 mm` gap) within `0.65 mm` of `NOTCH_OUT`.
- **R2 Fix**:
  Necked those 6 doorway tracks to `w = 0.10 mm` (matching the existing `0.10 mm` board design rule used on `ADC_D4_R`) at `0.230 mm` center-to-center pitch (`0.130 mm > 0.127 mm` edge-to-edge track gap) across `x = 151.385, 151.615, 151.845, 152.075, 152.305, 152.535`:
  - Westmost track (`ADC_D2` at `x = 151.385, w = 0.10`): left copper edge `151.335 mm` $\rightarrow$ **`0.660 mm >= 0.650 mm`** edge-to-edge gap from `NOTCH_OUT` (`150.675 mm`).
  - Eastmost track (`ADC_SDIO` at `x = 152.535, w = 0.10`): right copper edge `152.585 mm` $\rightarrow$ **`0.155 mm >= 0.150 mm`** power-net clearance from `C90.1 / C91.1 / C84.1` (`152.740 mm`).
  - Shifted `VIA ADC_D2` to `(151.20, 130.80)` (`0.663 mm >= 0.650 mm` edge gap from `NOTCH_OUT @(150.50, 130.00)`) and `VIA ADC_D6` by `+0.04 mm` South to `(149.62, 131.08)` (`0.680 mm >= 0.650 mm` edge gap from `NOTCH_OUT`).

### C. Pre-existing `REF10M / LPF2_OUT` Parallel Run (`x = 118.90, y = 133.23..145.20`)
- **Why `kicad/work` had a pre-existing violation (`run 9.67 mm, min gap 0.20 mm`)**:
  On `kicad/work`, `REF10M` rose to `F.Cu` at `VIA (118.899, 133.231)` and ran vertically on `F.Cu` at `x = 118.899` (`y = 133.231..145.195`), parallel to `LPF2_OUT` at `x = 119.500` (`w = 0.35, y = 130.0..141.0`) with only a `0.351 mm` (`0.20 mm` at the via) edge gap.
- **R2 Fix**:
  Ripped the 4 unlocked `REF10M` items at `x = 118.899` (`uuids: 1c6378fa..., 2491e8fc..., 8bdcd05e..., 0e5fec71...`), moved `VIA REF10M` `1.10 mm` West to **`(117.80, 133.231)`** (`1.30 mm` edge gap from `LPF2_OUT`), and routed `REF10M` on `F.Cu` along **`[[117.80, 133.231], [116.60, 134.431], [116.60, 147.494], [111.109, 152.985]]`** (`0.603 mm` center-to-center West of `LMK_SCL` at `x = 117.203`, and `2.65 mm` edge-to-edge away from `LPF2_OUT`).

---

## 3. Honest Via & Segment Count

- **Plan vias added**: **100 vias** (`0.45 mm` pad / `0.20 mm` drill) — **11 fewer vias than Round 1 (`111`)**.
- **Existing vias ripped**: **49 vias** (`47` from R1 + `1` dangling `1V8_A` via at `(138.755, 132.852)` + `1` `REF10M` via at `(118.899, 133.231)`).
- **Net change in board via count**: **`+51` vias** (down from `+64` in Round 1).
- **Total plan items**: `703` track segments (across `175` polylines, with only `5` segments `< 0.05 mm`) + `100` vias = `803` added items; `314` track segments + `49` vias = `363` ripped items.

---

## 4. ADC Lengths & Skew Table (`notes/pinswap/agy_timing_check.py -v`)

Reference Clock `ADC_DCO`: **total = `30.75 mm`** (`U8 -> R40` stub = `3.44 mm`, `R40 -> U12` = `27.31 mm`).

| Net | `U8 -> R` Stub (mm) | `R -> U12` (mm) | Total Length (mm) | Skew vs `ADC_DCO` (mm) | InvDCO Setup / Hold (ps) | Status |
|---|---:|---:|---:|---:|---:|---|
| `ADC_D0` | 5.34 | 37.23 | 42.58 | +11.83 | +3110 / +4616 | **PASS** |
| `ADC_D1` | 1.99 | 31.14 | 33.13 | +2.39 | +3176 / +4555 | **PASS** |
| `ADC_D2` | 4.04 | 31.98 | 36.02 | +5.28 | +3156 / +4574 | **PASS** |
| `ADC_D3` | 1.62 | 29.21 | 30.83 | +0.09 | +3193 / +4540 | **PASS** |
| `ADC_D4` | 4.04 | 25.51 | 29.55 | -1.20 | +3202 / +4531 | **PASS** |
| `ADC_D5` | 1.17 | 30.61 | 31.78 | +1.03 | +3186 / +4546 | **PASS** |
| `ADC_D6` | 4.06 | 25.99 | 30.06 | -0.69 | +3198 / +4535 | **PASS** |
| `ADC_D7` | 1.96 | 25.79 | 27.74 | -3.00 | +3214 / +4520 | **PASS** |
| `ADC_D8` | 4.04 | 24.39 | 28.43 | -2.32 | +3209 / +4524 | **PASS** |
| `ADC_D9` | 6.00 | 31.40 | 37.40 | +6.65 | +3147 / +4582 | **PASS** |
| `ADC_D10` | 5.08 | 24.99 | 30.07 | -0.68 | +3198 / +4535 | **PASS** |
| `ADC_D11` | 1.38 | 32.20 | 33.58 | +2.83 | +3173 / +4558 | **PASS** |
| `ADC_D12` | 3.42 | 36.14 | 39.56 | +8.81 | +3131 / +4596 | **PASS** |
| `ADC_D13` | 1.40 | 33.68 | 35.08 | +4.33 | +3163 / +4567 | **PASS** |
| `ADC_OR` | 1.62 | 29.14 | 30.76 | +0.01 | +3193 / +4539 | **PASS** |
| `ADC_CSB` | (exempt) | 39.02 | 39.02 | EXEMPT | 1.25 MHz SPI | **PASS** |
| `ADC_SCLK` | (exempt) | 39.86 | 39.86 | EXEMPT | 1.25 MHz SPI | **PASS** |
| `ADC_SDIO` | (exempt) | 36.13 | 36.13 | EXEMPT | 1.25 MHz SPI | **PASS** |

---

## 5. Verbatim `u11_trial.py` Output

```text
ripped 363 items; added 803 items

new copper DRC errors: 0

unconnected: 33 -> 0
  closed: ['1V1', '1V8_D', '2V5', '3V3_D', 'ADC_CSB', 'ADC_D0', 'ADC_D1', 'ADC_D11', 'ADC_D12', 'ADC_D13', 'ADC_D2', 'ADC_D3', 'ADC_D4', 'ADC_D4_R', 'ADC_D5', 'ADC_OR', 'ADC_RBIAS', 'ADC_SCLK', 'ADC_SDIO', 'FLASH_IO1', 'FLASH_IO2', 'FPGA_CFG0', 'FPGA_CFG1', 'FPGA_CFG2', 'FPGA_DONE', 'FPGA_INIT_N', 'FPGA_PROGRAM_N', 'LED1', 'LMK_SDA']
  BROKEN: []
  FT still open: []
  all still open: []

plan items dangling: 0

timing check:
  Reference Clock ADC_DCO: total = 30.75 mm (U8->R40 stub = 3.44 mm, R40->U12 = 27.31 mm)
  Reference Clock FT_CLK: length = 12.63 mm
OVERALL RESULT: FAIL (1 violations)

board: /tmp/u12k/usb3-sdr.kicad_pcb
```
*(Note: As in Round 1, the single violation in `agy_timing_check.py` is the known `FT_SIWU_N` 1-pin net on `U11`.)*

---

## 6. Verbatim `rf_spacing.py --base` Output

```text
digital copper within 0.65 mm of RF-path copper, same layer: 0 pairs
  gone  ADC_D6         LNA_BYP       F.Cu
  gone  ADC_D6         LNA_IN        F.Cu
  gone  ADC_D6         LPF2_IN       F.Cu
  gone  ADC_D8         NOTCH_OUT     F.Cu
  gone  REF10M         LPF2_OUT      F.Cu
```
