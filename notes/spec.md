# USB3 Direct-Sampling SDR: Rev A spec (DRAFT)

Status: draft by Claude, 2026-10-22. Math cross-check: AGY (see math.md / THREAD.md).
Prices are distributor snapshots from web search on 2026-10-22. **Re-quote before ordering.**

## 1. Goal and scope
- Receive-only, direct-sampling HF receiver: **0.06–~30 MHz** in the 1st Nyquist zone (droop corrected in DSP up to 32 MHz).
  6 m and FM through undersampling would need a **switched bandpass filter per Nyquist zone** (Rev B option). An AAF bypass alone folds the zones together.
- FPGA DDC, so the host can take either a raw stream or several narrowband IQ channels.
- USB 3.0 bus-powered, 2-layer-friendly analog section, **4-layer JLCPCB** board with JLC assembly.
- Target: **< $150 BOM at qty 1** (excluding the PCB), under $100 at qty 50.
- Open toolchain (Yosys/nextpnr) and no vendor licenses.

## 2. Architecture

```
SMA ─► protection ─► [20 dB pad | thru] ─► 7th-order elliptic LPF #1 + FM band-stop ─► LNA (bypassable) ─► 7th-order elliptic LPF #2 (32 MHz)
     ─► 1:2 balun ─► AD9649-80 (14b, 80 MSPS, CMOS out) ═14b+DCO═► ECP5 LFE5U-45F
                         ▲ CLK                                     │  NCO/mixer/CIC/FIR DDC ×N
                LMK61E2 (80.000 MHz, ~0.1 ps) ─────────────────────┤  FT601 FIFO master
                (opt. 10 MHz ext ref via ECP5 PLL discipline)       ▼
                                              FT601Q ═ 32b @100 MHz ═► USB 3.0 (USB-C)
```

## 3. Part selection

| Block | Choice | Why | Price (1 pc) | Availability | Runner-up |
|---|---|---|---|---|---|
| ADC | **ADI AD9649BCPZ-80**: 14-bit, 80 MSPS, SNR 74.1 dBFS / SFDR 93 dBc @ 30.5 MHz, 1.8–3.3 V parallel CMOS out, 82–95 mW, LFCSP-32 | Cheapest genuine 14-bit high-speed part found. CMOS output needs no LVDS deserializer. | ~$50 (DigiKey/Mouser, ~269 in stock); $18.25 @1ku (ADI list) | In stock | TI ADC3664 (dual 14b 125 MSPS, SLVDS): TI shows it out of stock, no price. ADC3544 (1ch 14b 125 MSPS) ~$90. LTC2208 (16b 130 MSPS, as in the RX888) is **obsolete** and costs $92–135 from authorized distributors; $12 AliExpress parts are almost certainly pulls or fakes. |
| FPGA | **Lattice LFE5U-25F-6BG256C** (default, LCSC C1521614 in stock; 28 mults, ~4 DDCs). 45F is a ball-compatible drop-in when in stock (verified via prjtrellis-db). Originally: LFE5U-45F-6BG256C: 44k LUT, 72 18×18 multipliers, 1.9 Mb EBR, CABGA-256 at 0.8 mm | Open toolchain. At LCSC the 45F costs about the same as the 25F, so the extra headroom is free. Enough for 4–8 DDCs. | ~$17 (LCSC) | LCSC/JLC stock | LFE5U-25F (~$15 Arrow). Artix-7 35T costs ~$40 and has 16–52 week lead times. |
| USB 3 bridge | **FTDI FT601Q**: 32-bit FIFO at 100 MHz, QFN-76 | No firmware, QFN (not BGA), cheap. ~360 MB/s sustained read reported (ft60x-rs). | ~$8–9 (RS) | RS has partial stock | Infineon FX3 CYUSB3014: $14 LCSC, $31 Mouser, BGA-121, needs firmware, 13–16 week lead time at some distributors. Proven in the RX888. |
| ADC clock | **TI LMK61E2** programmable oscillator, 1 differential output (LVPECL/LVDS/HCSL), 90 fs RMS typ (TI, fOUT > 100 MHz; *verify jitter at 80 MHz*) | A clean clock is the biggest SNR factor at high input frequency. Programmable, so 76.8/80 MHz can be swapped. | ~$8 (est., *verify*) | — | Fixed low-jitter XO (Crystek CCHD-575, ~$30). **Not** Si5351: tens of ps of jitter. |
| Config flash | W25Q128JVSIQ (QSPI) | Standard for ECP5 | $1 | JLC basic | — |
| FT601 clock | 30 MHz ±20 ppm, 18 pF, 50 Ω ESR crystal. **An oscillator cannot be substituted** (DS v1.05 §4.5, VERIFIED) | — | $0.3 | — | — |
| Balun | **1:4 impedance** transformer **Mini-Circuits ADT4-6T+ (0.06–300 MHz, verified)**. ADT4-1WT/TC4-1W were rejected because they only go down to 2–3 MHz. | 50 Ω → 200 Ω differential gives full scale (2 Vpp) = **+4 dBm** and 6 dB of free voltage gain. NF without LNA ≈ 27.9 dB. | ~$3–5 | — | 1:1 transformer: FS +10 dBm, NF ≈ 34 dB |
| LNA | **Mini-Circuits LHA-13LN+** (or PHA-13LN+), 1 MHz–1 GHz, **5 V / ~140 mA**: G 24 dB, NF 1.1–1.2 dB, OIP3 +38.9/+40.2 dBm @20 MHz (datasheets ✔). Use it **only ≥ 10 MHz** (bypass relay below that, where band noise ≫ the 32 dB LNA-off NF). Follow with a 3–6 dB pad to trade NF against clip level (see review_claude_of_math.md table). LHA is preferred because its abs-max input is +10 dBm vs +6 dBm for PHA. GVA-84+ (no 5 V headroom, NF 5+) and GVA-62+ (NF 4.7) were rejected. | Per the AGY/Claude noise math: not needed ≤ 10 MHz. Rural site at 30 MHz needs ≥ 3 dB of gain, quiet site ≥ 18 dB, 6 m ≥ 26 dB. Bypass on low bands to keep IMD headroom. | ~$3–6 | — | — |
| Step attenuator / bypass | 2× SPDT RF switch rated down to **< 50 kHz** (**not PE4259**, which has a 10 MHz minimum). Candidates: PE4283 (*range unverified*) or a small signal relay (G6K-2F-RF), plus a π-pad | Strong-signal handling on low HF | ~$2 | — | — |
| Power | 5 V USB → **TPS62A02A** 2 A buck (1.1 V core), **TPS62A01A** 1 A buck (3.3 V). The A suffix means forced PWM at a fixed 2.4 MHz (in the 120 m broadcast band, so spurs are deterministic), with π LC post-filters, LDO 2.5 V (VCCAUX), **2× TPS7A2018 LDO** (ADC AVDD and DRVDD at 1.8 V, from 3.3 V), ferrite-isolated | Low noise where it matters, efficient elsewhere | ~$4 total | JLC basic/extended | — |
| Connectors | **USB 3.0 Micro-B** for Rev A (one SS lane, so no mux or CC logic needed). USB-C would need an HD3SS3212 SS mux plus 5.1 kΩ Rd on CC1/CC2. SMA edge ×2 (RF, 10 MHz ref) | — | ~$3 | — | — |

### Rough BOM (qty 1): superseded by bom.md (parts $132 at qty 1)
ADC $50 + FPGA $17 + FT601 $9 + LMK61E2 $8 + front end $12 + power $5 + flash/crystals/passives $10
+ connectors $4 ≈ **$115**. PCB (4-layer, 100×60 mm) with JLC assembly adds ~$40–70 for 5 boards,
dominated by BGA/extended-part setup fees.
At qty 50 the ADC falls toward ~$25–45 and the total toward ~$80.

## 4. Gateware (ECP5)
- ADC capture: 14 bits + DCO on **1.8 V CMOS** (DRVDD = VCCIO7 = 1.8 V).
  The AD9649 output is **SDR**: capture in IFS1P3DX input flops on DCO (PCLK ball K1). The whole DDC runs in the DCO domain; there is no separate 80 MHz clock.
- DDC ×4 (initially): 32-bit NCO (CORDIC or LUT), complex mixer, 5-stage CIC (R = 10–80), then
  a compensating FIR + half-band. Outputs at 48 kHz–2 MHz IQ.
- Raw mode: 14→16-bit samples at 80 MSPS = **160 MB/s**, inside FT601 headroom.
- FT601 245-FIFO master at 100 MHz, 32-bit, from a separate PLL clock domain via async FIFO (EBR).
- Control over FT601 channel or a simple command packet in the OUT pipe. SPI master to the ADC and LMK61E2 (I²C).
- Toolchain: Yosys + nextpnr-ecp5 + ecppack, Amaranth or Verilog.

## 5. Host software
- `libftd3xx` (FTDI, closed source) or the open **ft60x-rs**/libusb path.
- SoapySDR module → GNU Radio, SDR++, CubicSDR. Optional ExtIO wrapper for HDSDR/SDR Console.

## 6. PCB

### Stackup (JLC04161H-7628, 1.6 mm)
| Layer | Use |
|---|---|
| L1 | Signals, RF, components |
| L2 | **Solid GND**, no splits |
| L3 | Power islands (1.1 V under FPGA, 3.3 V, 2.5 V, 1.8 V-A under ADC) plus slow signals |
| L4 | Signals (BGA inner-ring escape), a few components |

Controlled impedance on L1 referenced to L2 (trace widths from AGY, cross-checked with the JLC calculator):
50 Ω single-ended RF, 90 Ω differential USB SS, 100 Ω differential for ADC clock (if LVDS/LVPECL).

### Floorplan (≈100 × 60 mm)
```
 ┌──────────────────────────────────────────────────────────────────────┐
 │ SMA RF   prot ─ pad ─ LNA ─ LPF ─ balun ─ ADC          ┆   FT601     │
 │ (edge)   ◄──────── analog zone, ~35 mm ────────►  ║    ┆   30MHz Y  ═╪═ USB-C
 │                              LMK61E2 ─► (short)   ║ ECP5 BG256    │  (edge)
 │ SMA 10M                      AVDD LDOs            ║  + flash      │
 │                                                   ║  1.1V buck    │
 │ ◄──── quiet ──── 5 V input filter → bucks ─────────────────────────│
 └──────────────────────────────────────────────────────────────────────┘
```
- **Analog zone**: no digital traces on L1/L4 under or near it. AVDD LDO is local. ADC exposed pad
  is stitched to L2 with 9+ vias. Keep switching regulators at least 25 mm from the ADC input and clock, with shielded inductors.
  Optional solder-on shield can (e.g. 30×25 mm) over the LNA, LPF, balun and ADC.
- **DRVDD = VCCIO7 = 1.8 V**.
- **ADC→FPGA**: 15 CMOS lines (D0–D13, DCO) on L1, ≤ 25 mm, length-matched ±2 mm, 22–33 Ω series
  resistors at the ADC to slow edges and cut digital feedback into the input. Run DRVDD at the lowest voltage the
  FPGA bank accepts.
- **ADC clock**: LMK61E2 next to the ADC, < 10 mm, differential, away from the data bus. The LMK61E2 has a **single** output, so it
  goes to the ADC only. The FPGA captures with the ADC's DCO (same frequency), and the FT601 domain runs off its own 100 MHz CLKOUT.
- **BGA-256 at 0.8 mm on 4 layers**: dog-bone fanout with 0.2–0.25 mm drill and **0.45 mm pad** vias (JLC multilayer minimum, no surcharge; 0.15 mm drill carries a fee). Outer 2 rings escape on L1,
  the next 2 rings on L4. Only ~70 of the 197 I/O are used, so bank assignment can favor the outer rings.
  (Precedent: the ULX3S routes an ECP5 BGA-381 on 4 layers.) VCC/GND balls via to L3/L2. Decoupling
  0402 on L4 under the BGA.
- **USB 3**: SS TX/RX pairs 90 Ω differential, < 30 mm from FT601 to the connector, AC caps (100 nF **0402**) on
  TX at the FT601 side, no stubs, GND vias beside each layer change, intra-pair skew < 0.1 mm.
  USB2 D+/D− also 90 Ω differential.
- **FT601 FIFO bus**: 32 data + ~8 control at 100 MHz, ≤ 40 mm, matched ±5 mm, over unbroken L2.
- **Power**: USB 5 V → ferrite + bulk → bucks. 1.1 V core rated ≥ 1.5 A (use the Lattice power calculator).
  Estimated total draw ≈ 1.6–2.2 W, inside the 4.5 W USB 3 budget.

## 6b. Anti-alias filter (from the AGY/Claude cross-check)
- At 80 MSPS, **FM broadcast at 88–108 MHz aliases to 8–28 MHz**, right in the middle of HF. Local FM is the critical blocker.
- Edges are 32 MHz passband and 48 MHz first-alias stopband. Elliptic order for 60/80/100 dB of rejection is 6/8/9; Chebyshev needs 9/12/14 and Butterworth 20/26/31.
- One lumped LC section is practically limited to about 80 dB by layout coupling (AGY rule of thumb, unverified). So use **two 7th-order elliptic sections** split around the LNA plus an 88–108 MHz notch, each in its own shielded compartment.

## 7. Open items / risks
1. LMK61E2 price and stock: unverified (TI page lists none). FT601 crystal: verified (DS v1.05).
2. ADC3664 dual 125 MSPS is a nicer Rev B upgrade (two antennas / diversity, 0–55 MHz) but is out of stock and SLVDS.
3. FT601 sustained throughput depends on the host. Raw 80 MSPS mode needs ~160 MB/s, which is fine. DDC modes need far less.
4. ESD/overload protection vs IMD: the protection diodes must not degrade SFDR at the 93 dBc level. Use low-capacitance parts and put the pad and LNA after them.
5. JTAG/programming path: Tag-Connect JTAG header + ecpprog with an FT232H adapter (Rev A).
   Rev B: reflash over the FT601.
