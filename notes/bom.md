# Rev A costed BOM (qty 1 pricing, snapshot 2026-10-22)

Prices come from the LCSC product API (live at time of writing) unless the source column says otherwise. 'est.' means not looked up. **Re-quote before ordering.**

| Ref | Qty | MPN | Description | Source | LCSC # | Unit $ | Ext $ | Stock / note |
|---|---|---|---|---|---|---|---|---|
| U8 | 1 | AD9649BCPZ-80 | ADC 14b 80 MSPS | DigiKey (consign) | — | 49.56 | 49.56 | 269 @DigiKey snapshot; LCSC C514292 $67.49, 9 stk |
| U12 | 1 | LFE5U-25F-6BG256C | ECP5 FPGA 24k LUT (45F = drop-in) | LCSC | C1521614 | 15.37 | 15.37 | 160 stk; 45F C1550834 $15.94, 0 stk |
| U11 | 1 | FT601Q-B-T | USB3-FIFO bridge | LCSC | C1550513 | 13.35 | 13.35 | 79 stk |
| U9 | 1 | **LMK61E2-SIAR** (or LMK61E2BAA-SIAR / LMK61E2BBA-SIAR) | Programmable osc, 8-pin QFM with I2C | TI / DigiKey / Mouser (LCSC # to find) | — | ~10.7 | ~10.7 | **TO SOURCE.** Not C2871770: see note 1 |
| U13 | 1 | PHA-13LN+ | LNA 1 MHz–1 GHz (LHA-13LN+ alt, DigiKey) | LCSC | C3008204 | 11.71 | 11.71 | 193 stk |
| T1 | 1 | ADT4-6T+ | 1:4 transformer 0.06–300 MHz | LCSC | C3304892 | 7.04 | 7.04 | 7 stk |
| U10 | 1 | W25Q128JVSIQ | Config flash 128 Mb | LCSC | C97521 | 2.88 | 2.88 | 0 stk: any W25Q128JV pkg |
| U2,U3 | 2 | TPS62A02ADRLR | Buck 2 A forced PWM (used for both rails) | LCSC | C5820994 | 0.16 | 0.32 | 1175 stk; TPS62A01A C5181455 0 stk |
| U6 | 1 | TPS7A2033PDBVR | LDO 3.3 V low noise | LCSC | C2862740 | 0.21 | 0.21 | 155k stk |
| U5,U7 | 2 | TPS7A2018PDBVR | LDO 1.8 V low noise | DigiKey | — | 0.32 | 0.64 | no LCSC listing found |
| U4 | 1 | TLV75525PDBVR | LDO 2.5 V | LCSC | C2867155 | 0.23 | 0.23 | 0 stk: substitute |
| U1 | 1 | TPS22918DBVR | Load switch | LCSC | C131941 | 0.35 | 0.35 | 58k stk |
| U14 | 1 | 74LVC1G17 | Schmitt buffer (10 MHz ref) | LCSC | est. | 0.10 | 0.10 | basic |
| K1,K2 | 2 | HFD4/5-SR | DPDT signal relay 5 V SMD | LCSC | C64399 | 1.46 | 2.92 | 21.7k stk; HF isolation unverified |
| Y1 | 1 | X322530MSB4SI | 30 MHz ±10 ppm 20 pF xtal (FT601 asks 18 pF: adjust caps) | LCSC | C29538 | 0.10 | 0.10 | 12k stk |
| J1 | 1 | GSB343133HR | USB 3.0 Micro-B SMD | DigiKey | — | 1.09 | 1.09 | LCSC C464578 0 stk $3.08 |
| Q1-3 | 3 | 2N7002 | Relay/LNA drivers | LCSC | C8545 | 0.02 | 0.06 | basic |
| D2,D3 | 2 | BAV99,215 | RF limiter clamp | LCSC | C2500 | 0.01 | 0.02 | basic |
| L (AAF/notch) | 9 | Coilcraft 0805HP-xxxXGRB | AAF/notch inductors 47–270 nH 2 % | DigiKey/Coilcraft | — | 0.90 | 8.10 | Murata LQW18A rejected: 3.4 Ω DCR at 270 nH |
| C (AAF/notch) | 17 | C0G 0603 2 % | Filter caps 10–160 pF | LCSC | basic | 0.02 | 0.34 |  |
| L (power/LNA) | 6 | 1 µH / 15 µH shielded | Buck + π-filter + LNA choke | LCSC | est. | 0.20 | 1.20 |  |
| J2,J4 | 2 | SMA edge | RF in, 10 MHz ref | LCSC | est. | 0.80 | 1.60 |  |
| GDT1 | 1 | 90 V GDT | Input surge | LCSC | est. | 0.50 | 0.50 |  |
| F1,D1 | 2 | PTC 1.1 A + SMF5.0A | VBUS protection | LCSC | est. | 0.06 | 0.12 |  |
| Shield | 2 | Shield can ~30×25 mm | RF section | LCSC | est. | 1.00 | 2.00 |  |
| misc | 150 | R/C/ferrites 0402 | Decoupling, pull-ups, terminations | LCSC | basic | 0.01 | 1.50 |  |
| | | | | | | **Total parts** | **$132.04** | |

## Board fabrication and assembly (estimates: get a JLC quote)
| Item | Estimate | Notes |
|---|---|---|
| 4-layer PCB JLC04161H-7628, ~100×60 mm, 5 pcs | ~$15–30 | Impedance-controlled stackup, 0.2–0.25 mm drill / 0.45 mm via pad (no small-hole fee) |
| JLC Standard PCBA (BGA requires Standard, not Economic), 2 boards assembled | ~$30–60 setup/stencil/BGA X-ray | — |
| Extended-part loading fees | ~$3 per unique extended part, ~20–25 unique ≈ $60–75 per order | Fee is per order, not per board, so it amortizes over the batch |
| Consigned/global-sourced parts (AD9649, Coilcraft L, TPS7A2018, USB3 Micro-B) | Shipping + handling ~$10–25 | Or hand-solder the L's and the connector |

**First build (2 assembled boards):** parts ~$264 + fab/assembly ~$120–190 ≈ **$190–230 per board**.
**At 10+ boards:** per-board parts ≈ $115–120 (volume breaks on the ADC, FPGA, FT601, LMK, LNA) + about $15–25 of amortized assembly ≈ **$130–145**.
For comparison, RX888 MkII retail is $150–230.

## Sourcing risks (as of 2026-10-22)
1. **U9 must be the 8-pin, I2C-programmable LMK61E2** (LMK61E2-SIAR, -BAA-SIAR or -BBA-SIAR, SNAS674C orderable table). The previously listed LMK61E2-100M00SIAR (LCSC C2871770) is a *different* part: 6-pin, fixed 100 MHz LVDS, no I2C (TI LMK61E2-100M datasheet, refs/datasheets/LMK61E2-100M_fixed_6pin.pdf). It would clock the 80 MSPS ADC at 100 MHz and the FPGA's I2C program (boot_seq.v: LVDS, 80 MHz) would fail. Found 2026-10-24 (AGY flag, Claude check).
2. **ADT4-6T+: only 7 at LCSC.** Mini-Circuits sells direct.
3. **ECP5-45F is 0 at LCSC.** The 25F (160 in stock) is ball- and bank-compatible on CABGA-256 (verified against the prjtrellis-db; only PLL-input labels differ). It has 28 multipliers, enough for ~4 DDCs.
4. **AD9649**: LCSC $67.49 with 9 in stock, DigiKey ~$49.56 with 269 in stock (snapshot). Consign from DigiKey.
5. **W25Q128JVSIQ, TLV75525, TPS62A01A: 0 at LCSC.** All have trivial substitutes (another W25Q128JV package; any 2.5 V LDO; TPS62A02A on both rails).
6. **HFD4/5-SR relay:** cheap ($1.46 vs Omron RF $12), but its isolation at 30 MHz is unverified. Plan a bench check.
