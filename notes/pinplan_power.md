# ECP5 bank/pin plan and power tree (Rev A draft, Claude, 2026-10-22)

Source of ball→bank/function mapping: Project Trellis database `prjtrellis-db/ECP5/LFE5U-45F/iodb.json`
(CABGA256, 197 user I/O). Ring 0 = outermost ball row/column, which is the easiest escape on 4 layers.

## Bank geometry (CABGA256, top view)
| Bank | Side of BGA | I/O | Rings 0/1/2/3/4 | Clock-capable balls |
|---|---|---|---|---|
| 0 | top-left | 24 | 7/5/4/5/3 | A7/A8 PCLK0_0, C7/B7 PCLK0_1 |
| 1 | top-right | 32 | 7/7/6/7/5 | C8/B8 PCLK1_0, E8/D8 PCLK1_1 |
| 2 | right-upper | 32 | 8/8/8/4/4 | K16/K15 PCLK2_0, J16/J15 PCLK2_1 |
| 3 | right-lower | 32 | 8/7/7/6/4 | M16/M15 PCLK3_0, L16/L15 PCLK3_1 |
| 6 | left-lower | 32 | 8/7/7/6/4 | M1/M2 PCLK6_0, L1/L2 PCLK6_1 |
| 7 | left-upper | 32 | 8/8/8/4/4 | K1/K2 PCLK7_0, J1/J2 PCLK7_1 |
| 8 | bottom (config) | 13 | — | SPI config pins |

The floorplan has RF/ADC on the **left** and USB on the **right**, which matches the banks: 7/6 face the ADC, 2/3 face the FT601.

## Assignment
| Bank | VCCIO | Function | Signals | Balls |
|---|---|---|---|---|
| **7** | **1.8 V** (from the `1V8_D` LDO, shared with ADC DRVDD) | AD9649 data | D0–D13, OR (15) | Rings 0–1: B1 C1 D1 E1 F1 G1 J1 B2 C2 E2 F2 G2 H2 J2 K2 (map in ADC pin order to avoid crossings) |
| 7 | 1.8 V | AD9649 DCO (80 MHz) | DCO → **K1 (PCLKT7_0)** | K1 |
| 7 | 1.8 V | AD9649 SPI | SCLK, SDIO, CSB | Ring 2: C3 D3 E3 |
| **2 + 3** | **3.3 V** | FT601 FIFO | DATA[31:0], BE[3:0], TXE_N, RXF_N, WR_N, RD_N, OE_N, SIWU_N, RESET_N, WAKEUP_N, GPIO0/1 (~46) | Rings 0–2 of banks 2 and 3 (46 balls), plus ring 3 for slow signals (RESET_N, WAKEUP_N, GPIO) |
| 2 | 3.3 V | FT601 CLK (100 MHz, driven by the FT601) | CLK → **K16 (PCLKT2_0)** | K16 |
| **6** | 3.3 V | RF control and clock | pad switch ×2, LNA bypass ×2, LNA_EN, LMK61E2 I²C (SCL/SDA), 10 MHz ref in → **M1 (PCLKT6_0)**, LEDs ×2 | Rings 0–1 |
| 0 + 1 | 3.3 V | Expansion: 2× PMOD (16) + spare GPIO | — | Top edge, rings 0–1 |
| 8 | 3.3 V | Config: W25Q128 QSPI | CSN (R8), MOSI/D0 (T8), MISO/D1 (T7), D2 (M7), D3 (N7); CCLK is a dedicated pin | — |
| — | — | JTAG (dedicated TCK/TMS/TDI/TDO) | Tag-Connect TC2050 | — |

Notes:
- The AD9649 DRVDD and ECP5 VCCIO7 share 1.8 V. Lowest output swing means the least digital kickback into the ADC (AD9649 supports DRVDD 1.7–3.6 V; datasheet Table 1).
- Clocks: `clk_adc` = DCO (80 MHz) on a PCLK ball, directly to the capture flops. `clk_usb` = FT601 CLK (100 MHz). Async FIFO in EBR between them. No PLL in the ADC sample path; the sample clock goes LMK61E2 → ADC only.
- FT601 signals **VERIFIED against DS_FT600Q-FT601Q v1.05** (refs/): DATA[31:0], BE_0–3, CLK, TXE_N, RXF_N, WR_N, RD_N, OE_N, RESET_N, WAKEUP_N, GPIO0/1 = 46 FPGA pins.
  SIWU_N is reserved and only needs an external pull-up (no FPGA pin). **CLK = 100 MHz is only allowed at VCCIO 2.5 V or 3.3 V** (we use 3.3 V).
  The FT601 has an internal 1.0 V LDO: VCC33 → DV10 output (4.7 µF) → VD10 + AVDD. VDDA is 3.3 V for the PHYs and should get a ferrite from 3V3_D.
- Ball-level FT601 mapping is done at layout time to follow the FT601 QFN pin order.

## Power tree
```
USB VBUS 5 V (USB 3: 900 mA max = 4.5 W)
 │  ferrite + 22 µF + TVS, load switch (soft start)
 ├─► BUCK1 TPS62A02 (2 A) ─► 1V1   ECP5 VCC core
 ├─► BUCK2 TPS62A01 (1 A) ─► 3V3_D ─┬─► ECP5 VCCIO0/1/2/3/6/8, FT601 VCC/VCCIO, flash, LEDs
 │                                   ├─► LDO TLV75525 ─► 2V5 ECP5 VCCAUX (+ VCCIO if needed)
 │                                   └─► LDO TPS7A2018 ─► 1V8_D  ADC DRVDD + ECP5 VCCIO7
 ├─► LDO TPS7A2033 (from 5 V, ferrite) ─► 3V3_A ─┬─► LMK61E2 (own ferrite + local caps)
 │                                                ├─► LDO TPS7A2018 ─► 1V8_A  ADC AVDD
 │                                                └─► LNA supply (if a 3.3 V LNA is chosen)
```
- Bucks: ≥ 2 MHz switching, shielded inductors, on the right/bottom edge (≥ 25 mm from the ADC and balun).
  2 MHz harmonics land in-band. Sync the bucks to an FPGA-generated clock or pick spread-spectrum off and
  fixed frequency, so spurs are deterministic and can be notched in software.
- Analog rails come from separate LDO chains with ferrite isolation and a star return into the solid L2 GND (no split ground).

## Power budget (estimate; confirm with the Lattice Power Calculator)
| Load | Rail | Estimate | Basis |
|---|---|---|---|
| ECP5-45F, ~4 DDC + FIFO @ 80/100 MHz | 1V1 | 0.3–0.6 A → 0.35–0.65 W | Estimate. *Verify with Lattice calculator.* |
| ECP5 VCCAUX + VCCIO | 2V5/3V3/1V8 | ~0.15 W | Estimate |
| AD9649-80 | 1V8_A/D | 0.088 W (1.8 V, sine input) | Datasheet Table 1 (82.3–87.5 mW at 80 MSPS) |
| FT601 | 3V3_D | **0.62 W** (185 mA typ, SuperSpeed active) + VCCIO 9.5 mA | DS v1.05 Table 5.3 (VERIFIED) |
| LMK61E2 (LVDS) | 3V3_A | ~0.3–0.4 W | Estimate. *Verify with datasheet.* |
| LNA (LHA-13LN+, only when ≥ 10 MHz) | 5 V filtered | **0.7 W** (143 mA) | Datasheet ✔ |
| Losses (bucks ~85 %, LDO drops) | — | ~0.4 W | — |
| **Total** | | **~2.4–3.3 W** (LNA on) | Inside the 4.5 W USB 3 budget with about 27 % margin at the high end |
