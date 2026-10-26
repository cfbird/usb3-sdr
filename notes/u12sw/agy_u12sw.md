# U12 South-West Route Plan (`agy_u12sw_plan.json`)

**Author:** AGY  
**Date:** 2026-10-26  
**Deliverables:** `notes/u12sw/agy_u12sw_plan.json`, `notes/u12sw/agy_u12sw.md`

---

## 1. Summary & Verification Status

- **All 33 open connections (29 open nets) closed (`unconnected: 33 -> 0`, `all still open: []`)**: **VERIFIED** via `python3 kicad/gen/u11_trial.py notes/u12sw/agy_u12sw_plan.json 2>/dev/null`.
- **0 new copper DRC errors (`new copper DRC errors: 0`)**: **VERIFIED**.
- **0 broken nets (`BROKEN: []`) and 0 dangling items (`plan items dangling: 0`)**: **VERIFIED**.
- **All In2.Cu power island slivers (`1V1` at `(162.7, 122.1)` and `2V5` at `(164.9, 123.5)`) healed without editing zone outlines**: **VERIFIED** (by relocating the pinching vias out of the narrow `In2.Cu` necks under `U12`).
- **All 15 ADC high-speed nets (`ADC_D0..ADC_D13`, `ADC_OR`) + `ADC_DCO` + 3 SPI nets (`ADC_CSB`, `ADC_SCLK`, `ADC_SDIO`) pass `agy_timing_check.py`**: **VERIFIED** (`ADC_DCO = 34.90 mm`, data bus span `[27.74, 42.58] mm` = `14.84 mm`, skew to `ADC_DCO` within `[-7.16, +7.67] mm` vs `±25 mm` limit, all `U8 -> R` stubs `1.17 .. 6.00 mm <= 8.00 mm`).
- **Clean octilinear geometry**: **VERIFIED** — 189 track polylines comprising 715 segments (`826` KiCad items = `715` segments + `111` vias), with only **6** segments `< 0.05 mm` (down from 584 in the U11 round).

---

## 2. Part Moves

- **`moves`: `{}` (0 part moves)**. Every open net, power stub, and `In2.Cu` sliver is resolved purely in copper without moving any components.

---

## 3. Honest Via & Segment Count

- **Plan vias added**: **111 vias** (`0.45 mm` pad / `0.20 mm` drill) across all routed and re-routed nets.
- **Existing vias ripped**: **47 vias** (from ripped nets/UUIDs to clear `In2.Cu` island necks and uncross the `ADC` / `FPGA config` / `Flash` corridors).
- **Net change in board via count**: **`+64` vias** (`715` track segments + `111` vias = `826` added items; `309` track segments + `47` vias = `356` ripped items).

---

## 4. Method: Lane per Net, Layer Assignment & Via Positions

### A. Healing the `In2.Cu` Power Island Slivers & Rail Stubs
1. **`1V1` In2.Cu sliver at `(162.7, 122.1)`**:
   - **Root cause**: `FT_D1` via at `(162.6, 121.2)` (`uuid: 8560c370...`) pinched the narrow `In2.Cu` `1V1` neck against `U12.E9` (`GND` via at `(163.0, 122.0)`).
   - **Fix**: Ripped the `FT_D1` via at `(162.6, 121.2)` and shifted it `0.60 mm` North-East to **`(162.95, 120.70)`**, opening the `In2.Cu` `1V1` channel so KiCad's zone fill connects the northern `1V1` lobe continuously.
2. **`2V5` In2.Cu sliver at `(164.9, 123.5)` and `2V5` Southern island**:
   - **Root cause**: Vias for `FT_D6` at `(165.27, 122.86)` (`uuid: ac86f834...`), `FT_D4` at `(165.24, 123.62)` (`uuid: 17bc1975...`), `FT_WR_N` at `(166.20, 129.60)`, `FT_WAKEUP_N` at `(166.20, 130.40)`, and `FT_GPIO0` at `(167.00, 130.40)` severed the `In2.Cu` `2V5` ring along the East/South-East edge of `U12`.
   - **Fix**:
     - Routed `FT_D6` and `FT_D4` out of `U12` on `F.Cu` to vias East of the `2V5` ring at **`(169.37, 122.58)`** (`FT_D6`) and **`(169.85, 123.62)`** (`FT_D4`).
     - Routed `FT_WR_N` (`U12.R13`), `FT_WAKEUP_N` (`U12.T13`), and `FT_GPIO0` (`U12.T14`) on `F.Cu` to vias outside the `2V5` neck at **`(167.64, 130.85)`** (`FT_WR_N`) and **`(168.23, 130.85)`** (`FT_GPIO0`), with `FT_WAKEUP_N` staying purely on `F.Cu`.
3. **Power rail stubs (`1V1`, `1V8_D`, `2V5`, `3V3_D`)**:
   - `1V1`: `C88.1 (156.86, 132.56) -> C82.1 (155.525, 133.90) -> VIA 1V1 (156.30, 135.05)` on `F.Cu` (`w = 0.20..0.30 mm`).
   - `2V5`: `C90.1 (153.02, 130.56) -> VIA 2V5 (155.15, 131.78)` on `F.Cu` (`w = 0.25 mm`).
   - `1V8_D`: `U8.10 (143.438, 140.75) -> VIA 1V8_D (144.30, 140.60)` on `F.Cu` (`w = 0.25 mm`), plus `In2.Cu` neck unpinched by shifting `U12` West doorway vias to `x = 149.17..151.42` / `153.15`.
   - `3V3_D`: `R56.2 (152.40, 143.69) -> R54.2 (153.40, 144.01) -> R55.2 (154.30, 141.19) -> R52.2 (156.21, 141.00) -> R53.2 (156.91, 143.40) -> R57.2 (158.95, 144.01) -> R59.2 (159.507, 141.82) -> VIA 3V3_D (159.507, 141.108)` on `F.Cu` (`w = 0.25..0.40 mm`).

### B. ADC Bus (`ADC_D0..ADC_D13`, `ADC_OR`, `ADC_DCO`) & `ADC_CSB / SCLK / SDIO`
To eliminate topological crossings between the 19 ADC signals travelling from `R26..R41` / `U8` (`x = 139..148, y = 134..145`) to `U12` Bank 7 (`x = 157.0..159.8, y = 121.6..126.0`), the bus is partitioned into two non-crossing layer groups across a **2-layer Manhattan crossbar** West of `U12` (`x = 144.3..155.4, y = 120.7..134.0`):

| Net | `U8 -> R` (`F.Cu`) | R-side Via(s) | Main Trunk Layer & Corridor | U12-side Via(s) | U12 Entry Layer |
|---|---|---|---|---|---|
| `ADC_D12` | Existing (`3.42 mm`) | `(141.45, 131.20)` | `B.Cu` outer NW (`x=144.35, y=122.25 -> y=121.00`) | Existing `(159.80, 124.00)` | `B.Cu -> F.Cu` |
| `ADC_D11` | Existing (`1.38 mm`) | `(142.05, 136.35)`, `(142.05, 135.20)`, `(142.10, 131.20)` | `B.Cu` NW (`x=144.65, y=122.60 -> y=121.55`) | Existing `(159.80, 121.60)` | `B.Cu -> F.Cu` |
| `ADC_D9` | Re-routed (`6.00 mm`) | `(140.54, 132.85)` | `B.Cu` NW (`x=144.95, y=122.95 -> y=121.92`) | Existing `(159.80, 122.40)` | `B.Cu -> F.Cu` |
| `ADC_DCO` | Existing (`3.44 mm`) | `(140.15, 131.70)`, `(143.95, 130.65)`, `(143.95, 129.05)` | `B.Cu` (`x=145.45, y=124.00`) | `(153.15, 124.00)` | `F.Cu` (`y=124.00 -> H1`) |
| `ADC_OR` | Existing (`1.62 mm`) | `(138.85, 133.47)`, `(143.30, 130.40)`, `(143.30, 128.80)`, `(147.00, 125.70)` | `B.Cu` (`x=145.75, y=125.60`) | `(153.15, 125.60)` | `F.Cu` (`y=125.60 -> K2`) |
| `ADC_D13` | Existing (`1.40 mm`) | `(140.40, 136.29)`, `(139.10, 135.40)`, `(139.40, 132.75)`, `(143.65, 130.55)`, `(143.65, 128.90)` | `B.Cu` (`x=146.10, y=126.25`) | `(153.15, 126.25)`, `(156.15, 126.50)`, `(159.80, 124.80)` | `F.Cu -> B.Cu -> F.Cu` |
| `ADC_SCLK` | Direct SPI | `(144.77, 145.20)` | `B.Cu` (`x=146.92 -> y=127.95 -> x=153.60 -> y=122.35`) | Existing `(158.20, 122.40)` | `B.Cu -> F.Cu` |
| `ADC_D0` | Re-routed (`5.34 mm`) | `(148.05, 143.95)` | `B.Cu` (`x=147.22 -> y=128.25 -> x=153.90 -> y=122.70`) | Existing `(159.00, 122.40)` | `B.Cu -> F.Cu` |
| `ADC_D5` | Existing (`1.17 mm`) | `(145.52, 141.30)` | `B.Cu` (`x=147.52 -> y=128.55 -> x=154.20 -> y=124.05`) | Existing `(159.00, 124.00)` | `B.Cu -> F.Cu` |
| `ADC_D1` | Existing (`1.99 mm`) | `(145.97, 143.45)` | `B.Cu` (`x=147.82 -> y=128.85 -> x=154.50 -> y=124.40`) | Existing `(158.20, 124.00)` | `B.Cu -> F.Cu` |
| `ADC_D3` | Existing (`1.62 mm`) | `(146.42, 142.30)` | `B.Cu` (`x=148.12 -> y=129.15 -> x=154.80 -> y=124.80`) | Existing `(158.20, 124.80)` | `B.Cu -> F.Cu` |
| `ADC_D7` | Existing (`1.96 mm`) | `(147.45, 139.50)` | `B.Cu` (`x=148.42 -> y=129.45 -> x=155.10 -> y=125.60`) | Existing `(158.20, 125.60)` | `B.Cu -> F.Cu` |
| `ADC_D10` | Existing (`5.08 mm`) | `(148.12, 137.35)` | `B.Cu` (`x=148.72 -> y=129.75 -> x=155.40 -> y=126.05`) | Existing `(159.00, 124.80)` | `B.Cu -> F.Cu` |
| `ADC_D8` | Existing (`4.04 mm`) | `(148.57, 138.80)` | `B.Cu` (`x=149.02 -> 149.17`) -> `F.Cu` (`x=151.56, y=122.70`) | `(149.17, 131.47)` | `F.Cu` (`U12.E1`) |
| `ADC_D6` | Existing (`4.06 mm`) | `(148.57, 140.00)` | `B.Cu` (`x=149.32 -> 149.62`) -> `F.Cu` (`x=151.26, y=122.30`) | `(149.62, 131.04)` | `F.Cu` (`U12.D1`) |
| `ADC_D4` | Re-routed (`4.04 mm`) | `(148.57, 141.65)` | `B.Cu` (`x=149.62 -> 150.07`) -> `F.Cu` (`x=152.16, y=124.75`) | `(150.07, 132.33)` | `F.Cu` (`U12.H2`) |
| `ADC_D2` | Existing (`4.04 mm`) | `(148.57, 142.80)` | `B.Cu` (`x=149.92 -> 150.52`) -> `F.Cu` (`x=150.96, y=120.70`) | `(150.52, 130.61)` | `F.Cu` (`U12.D4`) |
| `ADC_CSB` | Direct SPI | `(145.95, 145.65)` | `B.Cu` (`x=150.22 -> 150.97`) -> `F.Cu` (`x=151.86, y=123.40`) | `(150.97, 131.90)` | `F.Cu` (`U12.G2`) |
| `ADC_SDIO` | Direct SPI | `(144.32, 144.75)` | `B.Cu` (`x=150.52 -> 151.42`) -> `F.Cu` (`x=152.46, y=125.10`) | `(151.42, 132.76)` | `F.Cu` (`U12.K1`) |

### C. `ADC_RBIAS`, `ADC_VCM`, and `1V8_A` Under `U8` South-West
- **`ADC_RBIAS` (`/ADC and clock/ADC_RBIAS`)**: `U8.28 (138.5625, 140.75) -> VIA (138.75, 140.75) -> B.Cu` inner SW lane `([139.00, 141.00] -> [139.00, 143.00] -> [141.40, 143.00] -> [145.00, 146.60] -> [146.975, 146.60]) -> VIA (146.975, 146.60) -> F.Cu -> R42.1 (147.056, 145.758)`.
- **`ADC_VCM`**: Takes the middle `B.Cu` lane `([137.782, 140.25] -> [138.15, 140.618] -> [138.15, 143.35] -> [141.05, 143.35] -> [145.175, 147.475] -> [145.70, 147.475])`.
- **`1V8_A`**: Takes the outer `B.Cu` lane `([137.491, 143.016] -> [137.491, 143.75] -> [139.528, 145.787] -> [140.547, 145.787])` plus vertical branch `[140.225, 144.175] -> [140.225, 145.787]`.

### D. FPGA Config (`FPGA_CFG0/1/2`, `DONE`, `INIT_N`, `PROGRAM_N`) & Flash (`U10`) & Misc
Five parallel non-crossing `B.Cu` lanes run down `x = 162.20..164.80` East of `U10` (`WSON-8`) and turn West along `y = 138.80..140.08` South of `U10` to reach `R52..R56`:
- **`/FPGA/FPGA_DONE` (Lane 1)**: `U12.N9 (163.40, 128.40) -> VIA (163.00, 128.00) -> B.Cu (x=162.55..162.58 -> x=162.20 -> y=138.80 -> x=152.35 -> y=143.40) -> VIA (155.15, 143.40) -> F.Cu -> R53.1 (155.89, 143.40)`.
- **`/FPGA/FPGA_CFG2` (Lane 2)**: `U12.P10 (164.20, 129.20) -> VIA (163.00, 129.60) -> B.Cu (x=162.95..162.98 -> x=162.55 -> y=139.12 -> x=152.95) -> VIA (152.95, 140.97) -> F.Cu -> R56.1 (151.40, 143.69)`.
- **`/FPGA/FPGA_INIT_N` (Lane 3)**: `U12.T9 (163.40, 130.00) -> F.Cu -> VIA (163.95, 134.10) -> B.Cu (x=162.90 -> y=139.44 -> x=155.00) -> VIA (155.00, 140.55) -> F.Cu -> R52.1 (155.19, 141.00)`.
- **`/FPGA/FPGA_CFG0` (Lane 4)**: `U12.M10 (164.20, 127.60) -> VIA (164.572, 127.172) -> B.Cu (x=163.80 -> x=164.48 -> x=163.25 -> y=139.76 -> y=144.20) -> VIA (152.10, 144.20) -> F.Cu -> R54.1 (152.40, 144.01)`.
- **`/FPGA/FPGA_CFG1` (Lane 5)**: `U12.N10 (164.20, 128.40) -> VIA (164.60, 128.00) -> B.Cu (x=164.12 -> x=164.80 -> x=163.60 -> y=140.08 -> x=156.90) -> VIA (156.90, 142.21) -> F.Cu -> R55.1 (154.30, 142.21)`.
- **`/FPGA/FPGA_PROGRAM_N`**: `U12.P9 (163.40, 129.20) -> VIA (163.00, 128.80) -> B.Cu -> VIA (163.45, 130.90) -> F.Cu (x=164.28 -> x=166.554) -> VIA (165.95, 137.90) -> F.Cu/B.Cu -> R58.2 (167.46, 138.365) & JTAG (170.30, 138.20)`.
- **`/FPGA/FLASH_IO2`**: `U12.N7 (161.80, 126.80) -> VIA (158.20, 127.20) -> B.Cu (x=158.00) -> VIA (158.00, 137.80) -> F.Cu -> U10.3 (156.4125, 138.635) & R59.1 (158.487, 141.82)`.
- **`/FPGA/FLASH_IO3`**: `U12.P7 (161.80, 127.60) -> VIA (159.00, 128.00) -> B.Cu (x=158.80..158.487) -> VIA (158.487, 133.387) -> R60.1 (158.487, 134.075) -> VIA (160.68, 135.08) -> B.Cu -> VIA (160.85, 137.50) -> F.Cu -> U10.7 (163.588, 137.365)`.
- **`/FPGA/FLASH_IO1`**: `U12.T7 (161.80, 130.00) -> VIA (160.00, 131.10) -> B.Cu (x=159.96) -> VIA (159.96, 137.50) -> F.Cu -> U10.2 (156.4125, 137.365)`.
- **`/FPGA/LED1`**: `U12.L2 (157.80, 126.00) -> F.Cu -> VIA (160.60, 126.40) -> B.Cu (x=159.80 -> 161.80) -> VIA (162.14, 132.85) -> F.Cu -> D5.2 (162.58, 133.423)`.
- **`LMK_SDA`**: `U12.P1 (157.00, 128.40) -> VIA (156.20, 128.20) -> B.Cu/F.Cu` East of `K2` (`x=156.20 -> x=150.70, y=139.00..146.90`) `-> B.Cu ([147.95, 147.50] -> [146.225, 149.225] -> [144.475, 149.225] -> [144.20, 149.50])`.

---

## 5. ADC Lengths & Skew Table (`notes/pinswap/agy_timing_check.py --verbose`)

Reference Clock `ADC_DCO`: **total = `34.90 mm`** (`U8 -> R40` stub = `3.44 mm`, `R40 -> U12` = `31.47 mm`).

| Net | `U8 -> R` Stub (mm) | `R -> U12` (mm) | Total Length (mm) | Skew vs `ADC_DCO` (mm) | InvDCO Setup / Hold (ps) | Status |
|---|---:|---:|---:|---:|---:|---|
| `ADC_D0` | 5.34 | 37.23 | 42.58 | +7.67 | +3134 / +4590 | **PASS** |
| `ADC_D1` | 1.99 | 31.14 | 33.13 | -1.77 | +3201 / +4529 | **PASS** |
| `ADC_D2` | 4.04 | 32.40 | 36.44 | +1.54 | +3177 / +4550 | **PASS** |
| `ADC_D3` | 1.62 | 29.21 | 30.83 | -4.07 | +3217 / +4514 | **PASS** |
| `ADC_D4` | 4.04 | 25.51 | 29.55 | -5.36 | +3226 / +4506 | **PASS** |
| `ADC_D5` | 1.17 | 30.61 | 31.78 | -3.12 | +3210 / +4520 | **PASS** |
| `ADC_D6` | 4.06 | 25.81 | 29.87 | -5.03 | +3223 / +4508 | **PASS** |
| `ADC_D7` | 1.96 | 25.79 | 27.74 | -7.16 | +3238 / +4494 | **PASS** |
| `ADC_D8` | 4.04 | 24.39 | 28.43 | -6.47 | +3233 / +4498 | **PASS** |
| `ADC_D9` | 6.00 | 29.82 | 35.82 | +0.91 | +3182 / +4546 | **PASS** |
| `ADC_D10` | 5.08 | 24.99 | 30.07 | -4.84 | +3222 / +4509 | **PASS** |
| `ADC_D11` | 1.38 | 31.71 | 33.08 | -1.82 | +3201 / +4529 | **PASS** |
| `ADC_D12` | 3.42 | 35.64 | 39.06 | +4.16 | +3159 / +4567 | **PASS** |
| `ADC_D13` | 1.40 | 31.35 | 32.74 | -2.16 | +3203 / +4526 | **PASS** |
| `ADC_OR` | 1.62 | 29.10 | 30.72 | -4.18 | +3217 / +4513 | **PASS** |
| `ADC_CSB` | (exempt) | 39.02 | 39.02 | EXEMPT | 1.25 MHz SPI | **PASS** |
| `ADC_SCLK` | (exempt) | 39.86 | 39.86 | EXEMPT | 1.25 MHz SPI | **PASS** |
| `ADC_SDIO` | (exempt) | 36.13 | 36.13 | EXEMPT | 1.25 MHz SPI | **PASS** |

---

## 6. Final `u11_trial.py` Output (Verbatim)

```text
ripped 356 items; added 826 items

new copper DRC errors: 0

unconnected: 33 -> 0
  closed: ['1V1', '1V8_D', '2V5', '3V3_D', 'ADC_CSB', 'ADC_D0', 'ADC_D1', 'ADC_D11', 'ADC_D12', 'ADC_D13', 'ADC_D2', 'ADC_D3', 'ADC_D4', 'ADC_D4_R', 'ADC_D5', 'ADC_OR', 'ADC_RBIAS', 'ADC_SCLK', 'ADC_SDIO', 'FLASH_IO1', 'FLASH_IO2', 'FPGA_CFG0', 'FPGA_CFG1', 'FPGA_CFG2', 'FPGA_DONE', 'FPGA_INIT_N', 'FPGA_PROGRAM_N', 'LED1', 'LMK_SDA']
  BROKEN: []
  FT still open: []
  all still open: []

plan items dangling: 0

timing check:
  Reference Clock ADC_DCO: total = 34.90 mm (U8->R40 stub = 3.44 mm, R40->U12 = 31.47 mm)
  Reference Clock FT_CLK: length = 12.63 mm
OVERALL RESULT: FAIL (1 violations)
```
*(Note: As noted in the brief, the single violation in `agy_timing_check.py` is the known `FT_SIWU_N` checker name mismatch.)*
