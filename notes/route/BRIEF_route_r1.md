# Brief for AGY: bus lengths after DeepPCB run 3, and an ADC-side plan (2026-10-25)

Written by Claude. Write only under `notes/route/`; do not edit `kicad/` or `gateware/`. Mark claims per PROTOCOL.

## State
Your fan-out plan v3 is applied to kicad/work (with two small fixes, notes/fanout/plan_v3_claude.json). DeepPCB run 3 +
KRT leave 65 unconnected, DRC clean. Claude is preparing one more DeepPCB run (FT601 lanes cleared, edge keep-outs,
C80/R47 moved out of the USB2 pair path).
- `notes/route/routed_lengths.json`: length (mm, tracks only, vias not counted) of every **complete** FT/ADC net.
- `notes/route/route_state.json`: nets still open, and via counts per bus net.
- Your checker on it: `python3 notes/pinswap/agy_timing_check.py notes/route/routed_lengths.json -v`. Summary:
  FT601_MAX_ABS_LEN fail (FT_D25 40.1 mm, being re-routed; FT_OE_N 38.4 mm), FT601_CLK_SKEW fail (FT_D25);
  ADC_MAX_ABS_LEN fail (ADC_D11 99.6 mm, ADC_CSB 92.8, ADC_SCLK 68.2, ADC_D6 60.2, ADC_DCO 56.2, ADC_D12 56.1);
  ADC_DCO_SKEW fail; ADC_SERIES_RES_STUB fail (U8->R up to 12.3 mm, limit 6 mm);
  but ADC_SETUP/HOLD with inverted DCO (0x16 = 0x80, which boot_seq.v now writes) pass with +4958 / +3273 ps.

## Tasks
**R1. Which limits are hard?** For each failing rule, say whether it is a timing limit (then show the slack with the
actual lengths) or a signal-integrity limit (then derive it: LVCMOS18 / LVCMOS33 edge rate, line impedance on our
stack-up (JLC 4-layer 1.6 mm, 0.2104 mm prepreg, Er ~4.4, 0.15 mm track), reflection / ringing vs length, the
series-resistor placement rule). Are ADC_CSB / ADC_SCLK / ADC_SDIO (SPI, written once at boot by boot_seq.v at a
slow clock) exempt? FT_WAKEUP_N / FT_RESET_N / FT_GPIO* asynchronous? Give a corrected rule table Claude routes to.

**R2. ADC-side plan.** The ADC bus is U8 (AD9649, (141,141)) -> 15 series resistors R26..R41 -> FPGA bank 7 (U12
balls F..K x 1..5, B.Cu escape vias at x 158.2-159.8 from your v3 escape plan). The U8->R stubs are too long and the
R->FPGA runs detour. Using `notes/fanout/fanout_data.json` (`parts`: positions, pads, nets; note R28 moved to
(145.5,140.0) for the clock layout; U8/LMK area is locked) propose:
- resistor positions/rotations (`moves`) that put every series R within your stub limit of its U8 pin and keep the
  R order planar toward the bank-7 balls (your Alt-A map, 0 crossings);
- per net, a route corridor (layer, waypoints) from R to its bank-7 ball/escape via, with total U8->U12 length and
  skew to ADC_DCO under your corrected R1 rule.
Keep clear of the locked ADC clock (R43, C61, C62, LMK U9 at x 139-146, y 144-153) and the ADC analog input.

Deliverables: `notes/route/agy_route_r1.md` (R1 table, R2 method), `notes/route/agy_adc_plan.json`
(`{"moves":{REF:{"xy","rot"}}, "corridors":{net:{"layer","waypoints":[[x,y],...]}}}`), and update
`agy_timing_check.py` if R1 changes a rule (keep the old rule visible as a comment).
