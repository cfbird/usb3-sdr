# Rev A schematic netlist spec (Claude, 2026-10-22)

Pin numbers marked ✔ were taken from the datasheet in this project:
AD9649 Rev B Table 8; FT600Q/FT601Q DS v1.05 §3.2 (QFN-76 column, in refs/); ECP5 balls from prjtrellis-db
CABGA256. Everything else is by function name. **Check against the symbol/footprint before layout.**

---
## Sheet 1: Power
| Ref | Part | In → Out | Notes |
|---|---|---|---|
| J1 | USB 3.0 Micro-B (FTDI reference designs use Std-B/Micro-B, DS §6.1) | VBUS | Shell → chassis GND via 1 MΩ ∥ 4.7 nF |
| F1, D1 | 1.1 A PTC + 5 V TVS (SMF5.0A) | VBUS → 5V_IN | — |
| U1 | TPS22918 load switch (soft start) | 5V_IN → 5V_SW | EN from VBUS divider |
| U2 | **TPS62A02A** (forced PWM, 2 A) | 5V_SW → **1V1** | ECP5 VCC. 1 µH shielded + π post-filter |
| U3 | **TPS62A01A** (forced PWM, 1 A) | 5V_SW → **3V3_D** | — |
| U4 | TLV75525 | 3V3_D → **2V5** | ECP5 VCCAUX |
| U5 | TPS7A2018 | 3V3_D → **1V8_D** | ADC DRVDD + ECP5 VCCIO7 |
| FB1 + U6 | ferrite + TPS7A2033 | 5V_SW → **3V3_A** | LMK61E2, LNA bias, U7 input |
| U7 | TPS7A2018 | 3V3_A → **1V8_A** | ADC AVDD (pins 3, 24, 29, 32) |
| — | FB + 4.7 µF | 3V3_D → FT601 VDDA | DS: VDDA = 3.3 V PHY supply ✔ |

Power-up order: 1V1 → 2V5 → 3V3 (ECP5 tolerates any order, but chain the PG/EN pins anyway). Each IC gets local 100 nF + 1 µF (0402) per supply pin. ECP5: 10 µF bulk per rail plus 0402 caps under the BGA (L4).

---
## Sheet 2: RF front end (left edge, in shield cans)
```
J2 SMA ─ GDT (90 V) ─ 2× BAV99 limiter clamp (low-C) ─ K1 relay: [20 dB π-pad: shunt 61.9 Ω / series 249 Ω / shunt 61.9 Ω (E96; ideal 61.1/247.5) | thru]
 ─ LPF#1 (AGY Design A, notes/aaf.md) ─ FM band-stop (aaf.md §3) ─ K2 relay: [LNA | thru]
 ─ LPF#2 (Design A) ─ T1 ADT4-6T+ (1:4) ─ ADC VIN+/VIN−
```
- K1, K2: Omron G6K-2F-RF or similar **DPDT signal relays** (one relay switches both ends of the bypass). Driven from bank 6
  through 2N7002 FETs with flyback diodes. Latching variants (G6KU) save about 100 mW.
- LNA: LHA-13LN+ at 5 V (filtered 5V_SW via a 15 µH 0805 choke plus 100 nF, valid since the LNA is only used ≥ 10 MHz), followed by a 3 dB π-pad. LNA_EN gates the supply so it draws 0 W when bypassed.
- T1 secondary: center tap → ADC **VCM (pin 27 ✔)** with 0.1 µF. Each leg 33 Ω series + 2×10 pF to GND at the
  ADC pins (charge-kickback filter, standard for unbuffered pipeline ADC inputs).
  **Re-check FS with 200 Ω differential termination.**

---
## Sheet 3: ADC and sample clock
| U8 AD9649BCPZ-80 pin ✔ | Net |
|---|---|
| EPAD (0) | AGND (only ground! ≥ 9 vias) |
| 1, 2 CLK+/CLK− | 100 nF AC-coupled from U9 LVDS out, 100 Ω differential termination at the ADC |
| 3, 24, 29, 32 AVDD | 1V8_A |
| 13 DRVDD | 1V8_D |
| 4 CSB | FPGA ADC_CSB (bank 7, E3) |
| 5 SCLK/DFS | FPGA ADC_SCLK (C3) |
| 6 SDIO/PDWN | FPGA ADC_SDIO (D3), bidirectional 3-wire SPI |
| 7–12, 14–21 D0–D13 | 22 Ω series at the ADC, then bank 7 (see Sheet 4) |
| 22 DCO | 22 Ω, then **K1 (PCLKT7_0)** |
| 23 MODE/OR | → K2 (OR flag, default function) |
| 25 VREF | 1 µF + 0.1 µF to GND |
| 26 SENSE | AGND → fixed internal 1.0 V reference, 2.0 Vpp FS (Table 10 ✔) |
| 27 VCM | T1 center tap, 0.1 µF |
| 28 RBIAS | 10 kΩ 1 % to GND |
| 30, 31 VIN−/VIN+ | T1 secondary through the kickback filter |

| U9 LMK61E2 | Net |
|---|---|
| VDD | 3V3_A (own ferrite, 10 µF + 0.1 µF) |
| OUTP/OUTN (LVDS) | → U8 CLK± |
| SCL/SDA | bank 6, 4.7 kΩ pull-ups to 3V3_D |
- **Boot hazard:** the LMK61E2 comes up at its EEPROM default frequency, which is 156.25 MHz for the base SIAR and 100 MHz for the -100M00 variant.
  Both exceed the AD9649-80 limit (tCLK ≥ 12.5 ns ✔). Gateware sequence: hold the ADC in **standby (SPI reg 0x08 bits[1:0] = 10, i.e. 0x08 = 0x02, then 0xFF = 0x01 transfer ✔ Table 16)**
  → program the LMK61E2 to 80.000 MHz (and **write its EEPROM once**, so the next power-up is already correct) → set **0x14 = 0x81** (1.8 V CMOS outputs, since the default is 3.3 V CMOS; two's complement) → 0x08 = 0x00 (run) → 0xFF = 0x01.
  Overclocking for the few ms before the FPGA takes over is assumed harmless but is *UNVERIFIED*.

---
## Sheet 4: ECP5 LFE5U-45F-6BG256C (ball map ✔ from prjtrellis-db)
| Bank | VCCIO | Balls → nets |
|---|---|---|
| 7 | 1V8_D | B1 D0, B2 D1, C1 D2, C2 D3, D1 D4, E2 D5, E1 D6, F2 D7, F1 D8, G2 D9, G1 D10, H2 D11, J1 D12, J2 D13, **K1 DCO (PCLKT7_0)**, K2 OR, C3 SCLK, D3 SDIO, E3 CSB |
| 2 + 3 | 3V3_D | FT601 bus. **K16 = FT_CLK (PCLKT2_0)**. Other 45 signals go on rings 0–2 of banks 2/3, assigned at layout to follow the FT601 pin order (DATA0–7 = FT pins 40–47, DATA8–15 = 50–57, CLK = 58, DATA16–23 = 60–67, DATA24–31 = 69–76, BE0–3 = 4–7, TXE_N 8, RXF_N 9, WR_N 11, RD_N 12, OE_N 13, RESET_N 15, WAKEUP_N 16, GPIO0/1 17/18 ✔) |
| 6 | 3V3_D | M1 REF10M_IN (PCLKT6_0), LMK_SCL, LMK_SDA, RLY_PAD, RLY_LNA, LNA_EN, LED×2 |
| 0, 1 | 3V3_D | 2× PMOD (8 signals each) |
| 8 | 3V3_D | U10 W25Q128JV: R8 CSN, T8 MOSI/D0, T7 MISO/D1, M7 D2, N7 D3; CCLK dedicated |
| JTAG | 3V3_D | J3 Tag-Connect TC2050: TCK/TMS/TDI/TDO + 3V3/GND |
- CFG pins: CFG[2:0] for SPI master boot (*check DS-02012 config table*). PROGRAMN pull-up plus button. DONE → LED.
- 10 MHz ref: J4 SMA → 50 Ω → 74LVC1G17 Schmitt buffer (3V3) → M1. Gateware measures LMK frequency against it and trims it over I²C (AGY: LMK61E2 fine margining, *unverified*).

---
## Sheet 5: USB 3 bridge
| U11 FT601Q pin ✔ | Net |
|---|---|
| 21 XI / 22 XO | Y1 30 MHz ±20 ppm, 18 pF load crystal (two ~27 pF caps, calculate from the crystal's CL). Oscillator **not allowed** ✔ |
| 23 DP / 25 DM | J1 D+/D−, 90 Ω differential |
| 31/32 TODN/TODP | 100 nF 0402 AC caps → J1 SSRX−/SSRX+ (check the connector naming direction) |
| 34/35 RIDN/RIDP | J1 SSTX−/SSTX+ (the host side has the AC caps) |
| 27 RREF | **1.6 kΩ 1 %** to GND ✔ |
| 37 VBUS | J1 VBUS through a divider/series R per DS Fig 6.1 |
| 38 VCC33 | 3V3_D |
| 39 DV10 | 4.7 µF; feeds VD10 (3, 48) and AVDD (2) ✔ |
| 28 VDDA | 3V3_D through a ferrite ✔ |
| 59, 68 VCCIO | 3V3_D (100 MHz requires 2.5 or 3.3 V ✔) |
| 10 SIWU_N | 10 kΩ pull-up (reserved) ✔ |
| 29, 36 GND + EPAD | GND |
- FIFO mode (245 sync, 100 MHz) is set once with FTDI's FT60x configuration utility (stored on the chip).
- **On-chip FIFO is only 4 KB × 2 per direction in 245 mode ✔.** Host stalls must be absorbed in FPGA EBR (~240 KB total in the 45F, about 1.5 ms at the raw-mode 160 MB/s). DDC modes have lots of margin. If raw mode drops samples in testing, the Rev B fix is a HyperRAM.

---
## Corrections from KiCad capture (2026-10-22). These supersede the tables above.
Found while checking every KiCad symbol and footprint against its datasheet:
1. **FT601 power pins were incomplete above.** Full list (DS v1.05 Table 3.1, matches the KiCad FT601Q symbol):
   VCC33 = 20, 24, 38; VD10 = 3, 30, 33, 48; VCCIO = 14, 49, 59, 68; GND = 1, 26, 29, 36 + EP (77); pin 19 Reserved (NC).
2. **USB3 direction:** Micro-B receptacle pin names are from the device's side. FT601 TODP/N goes through 100 nF to **SSTX±**;
   SSRX± goes directly to RIDP/N. The "TODN/TODP → SSRX" line above was wrong.
3. **LMK61E2 ADD (pin 2) must be tied to GND** to get I²C address 0x58, which the gateware uses (SNAS674C Table 7-1;
   open = 0x59, VDD = 0x5A). OE (pin 1) is tied high.
4. **Relays HFD4/5-SR:** wiring is the same as the Omron G6K-2 symbol (coil 1+/8−, COM 3/6, NC 2/7, NO 4/5; checked against
   the Hongfa datasheet wiring diagram). **The footprint is NOT the G6K-2F-Y one**: HFD4 rows are at ±2.1 mm vs ±3.5 mm.
   Custom footprint: kicad/usb3sdr.pretty/Relay_DPDT_Hongfa_HFD4-SR.
5. **ADT4-6T+:** primary 3 (dot)/1, secondary 4 (dot)/6, centre tap 5, pin 2 NC (Mini-Circuits datasheet). KiCad's
   stock ADT4-6 symbol is the non-centre-tap part, so a custom symbol is used. A 200 Ω differential termination across the
   secondary was added (needed for the +4 dBm full-scale assumption).
6. **LMK61E2 footprint:** custom from the TI SIA0008B land pattern (no stock KiCad footprint).
7. TPS22918 QOD is left unconnected (quick discharge disabled) rather than tied to VOUT.
