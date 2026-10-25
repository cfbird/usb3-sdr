# Claude's review of AGY's pin-swap work (2026-10-24)

Independent checker: `notes/pinswap/claude_verify.py` (netlist + work board + Lattice pinout + LPF; does not use AGY's
code or data.json).

| Item | Verdict | How checked |
|---|---|---|
| T1 FT601 assignment (agy_assignment.json) | VERIFIED | claude_verify.py: 46 signals, banks 2/3 only, no ball already used by another net, unique; crossings 237 -> 6, 0 without ft_clk; ft_clk on J16 = PCLKT2_1 (Lattice CSV-derived ecp5_bg256.json) |
| T2 ADC assignment, primary | DISPUTED (inputs) | Built from data.json, whose ADC_OR endpoint was wrong (Claude's extract.py stopped at R40). Superseded by Alt-A. |
| T2 ADC assignment, Alt-A (R41-corrected) | VERIFIED | claude_verify.py: 19 signals, bank 7 only; crossings 60 -> 0; adc_dco on J1 = PCLKT7_1; ADC_OR endpoint = R41 pad 2 |
| Bug 1: pcb_build.py fan-out on unconnected balls | VERIFIED, fixed | `if not pad.GetNetname()` never skips `unconnected-(...)`. Generator fixed; the routed board no longer has those vias (DeepPCB run 1 removed them). |
| Bug 2: extract.py omitted R41 | VERIFIED, fixed | netlist: ADC_OR = R41.2 <-> U12 K2. range now 26..41, data.json regenerated. |
| T3 escape capacity / C2 | VERIFIED (arithmetic) | 0.8-0.45 = 0.35 < 0.404; ball-via diagonal 0.1807 mm; reproduced. Capacity claims will be proven by actually routing. |
| C3 buck neck | VERIFIED (accepting AGY's thermal model) | R = rho*L/(w*t) = 1.72e-8*0.6e-3/(0.2e-3*35e-6) = 1.47 mOhm, matches. |
| C4 USB2 | VERIFIED with two follow-ups | Follow-ups to apply: D+/D- length difference <= 1.5 mm; a 3V3_D-GND cap near the layer-change vias. |
| C5 split crossing | VERIFIED | Claude's own sampling found the same class of problem; In2 GND fill applied (kicad/gen/in2_gnd_fill.py). AGY's extra fix (shrink the 1V1 island to the core) still to evaluate. |
| Timing with the new map | VERIFIED by Claude | nextpnr seeds 1-4, old -> new: ft_clk 112.7-118.7 -> 116.6-122.9 MHz (need 100); adc_dco 100.8-107.6 -> 107.5-110.7 MHz (need 80). All PASS. |

Decision taken for now: ADC bus stays in bank 7 (AGY Alt-A, 0 crossings). AGY's bank-6 option (VCCIO 6<->7 swap,
-92 mm of bus) is left for the user to decide: it changes a bank voltage and moves ref10m, LMK I2C, relay and LED
lines.

## Clock polarity (notes/pinswap/agy_clock_polarity.md), 2026-10-24
| Item | Verdict | How checked |
|---|---|---|
| P1-P3 (swap is harmless; AD9649 has no DCS, needs 45-55 % duty; LMK LVDS ODC 45-55 %) | VERIFIED | AD9649 Rev B Fig. 50 (AC-coupled LVDS, 0.1 uF + 100R at ADC) read directly; AGY's page citations consistent |
| LVDS is the only LMK output format that fits our network (no driver-side resistors) | VERIFIED | matches boot_seq.v (writes R21 = 0x02, LVDS) |
| "LMK61E2-100M00SIAR is not a valid TI part number" | DISPUTED in wording, but it exposed a real BOM error | It is a real TI part (separate LMK61E2-100M datasheet, now refs/datasheets/LMK61E2-100M_fixed_6pin.pdf): **6-pin QFM, fixed 100 MHz LVDS, pins OE/NC/GND/OUTP/OUTN/VDD, no I2C.** Our design needs the 8-pin I2C-programmable LMK61E2 (FPGA programs 80 MHz at boot). Correct parts: LMK61E2-SIAR, LMK61E2BAA-SIAR or LMK61E2BBA-SIAR (SNAS674C orderable table). BOM U9 (LCSC C2871770) is wrong and must be changed before ordering. |

## Bus timing (notes/pinswap/agy_timing.md), 2026-10-24
| Item | Verdict | How checked |
|---|---|---|
| Routing constraints: FT601 nets <= 35 mm, skew vs FT_CLK <= 15 mm, no serpentines; ADC DCO/data skew budget | ACCEPTED as constraints | arithmetic reproduced at 6-7 ps/mm; will run agy_timing_check.py on routed lengths |
| FT601 outputs are fabric FFs, not IO registers (so T4 = 4.8 ns hold is a real problem) | VERIFIED | rtl/ft601_245.v: only inputs use IFS1P3DX under ECP5_IOREG; nextpnr log new1.log shows doe TRELLIS_FF -> ft_data[6].T at 5.17 ns (4.41 ns routing) |
| Fix: outputs + tristate into OFS1P3DX, clocked from EHXPLLL at +135 deg (window +105..+160) | PLAUSIBLE, to verify in gateware | needs implementation + nextpnr + sim; open item for the gateware pass |
| AD9649 DCO edge-aligned by default; reg 0x16 bit 7 inverts DCO | VERIFIED | datasheet Table 4 (tPD = tDCO = 3 ns, tSKEW = 0.1 ns) and Table 16 (0x16 bit 7 = DCO output polarity); boot_seq.v does not write 0x16 today |

## FT601 IO-register fix (notes/pinswap/agy_ft601_ioreg.md), 2026-10-24
| Item | Verdict | How checked |
|---|---|---|
| Scope: only rtl/ft601_245.v and rtl/top.v changed; LPF untouched | VERIFIED | diff against Claude's pre-task snapshot |
| Outputs, BE and per-pad tristate enables in IOLOGIC (OFS1P3DX / OFS1P3BX) via explicit BB buffers | VERIFIED | nextpnr: 55 IOLOGIC packed; 0 async paths to ft_data/ft_be (was doe -> ft_data[6].T, 5.17 ns) |
| Single +112.5 deg PLL clock (split 0/+135 impossible: one CLK per bidirectional IOLOGIC) | VERIFIED (arithmetic) | CLKOS - CLKOP = 1 VCO cycle (1.667 ns) + 7/8 fine step (1.458 ns) = 3.125 ns at VCO 600 MHz |
| T1-T4 slack table (+0.72 ns T4 / +0.73 ns T2 at the fast corner) | PLAUSIBLE | input path delay ~1 ns delays the earliest FT601 data change past the shifted capture edge + hold; numbers consistent. nextpnr does not time board-level IO, so this rests on the model |
| Sims (ddc, ft incl. 1-cycle TXE reorder, boot) | VERIFIED | re-run by Claude: all PASS, DDC numbers unchanged |
| Fmax seeds 1-3 | VERIFIED | re-run by Claude: clk_ft 111.88 / 119.82 / 120.02 MHz, adc_dco 108.19 / 100.01 / 101.21 MHz, all identical to AGY's table |
