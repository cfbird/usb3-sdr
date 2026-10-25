# Claude's own checks while AGY works on BRIEF.md (2026-10-23)

## Fab limits (for BRIEF T3b): JLCPCB, checked on the web, not recalled
- Standard multilayer: min via hole 0.2 mm, min via pad 0.45 mm (0.4 mm "limit"); annular ring enlarged in production.
  So the current 0.45/0.2 fan-out via is already at the standard minimum.
- 0.15 mm hole / 0.25 mm pad vias exist only in JLC's ink-plugged BGA-via process (2- and 4-layer), with 4-layer
  trace/space down to ~0.09 mm. Using it is a cost/process option, not the default.
- Sources: jlcpcb.com/capabilities/PCB-capabilities, jlcpcb.com/help/article/bga-design-guidelines---pcb-layout-recommendations-for-bga-packages

## Buck part rating (self-check of C3 premise): VERIFIED
TI SLUSEG9E §4 Device Comparison Table: TPS62A02ADRLR = 2 A, SOT-563, FPWM, PG on pin 6. ("1A DRL" on page 1 is the
TPS62A01 DRL R_DSON line.) Pinout 1 GND, 2 SW, 3 VIN, 4 EN, 5 FB, 6 PG (Table 5-1), matches design.py.

## C5: B.Cu reference planes (run on kicad/deeppcb/r2_deeppcb_routed.kicad_pcb): PROBLEM FOUND
Method: sample every B.Cu track every 0.1 mm; a point is "referenced" if a filled In2.Cu zone lies under it.
In2 has copper only in three islands (1V1, 3V3_D, 1V8_A), so all 66 B.Cu nets have unreferenced length. Their only
reference there is In1 GND, ~1.1 mm away through the core. Worst signal nets:

| net | unreferenced / total B.Cu (mm) |
|---|---|
| ADC_DCO_R (ADC data clock out, 80 MHz) | 31.3 / 31.3 |
| ADC_CLKP (ADC **sample clock**, from LMK61E2) | 27.3 / 27.3 |
| 3V3_CLK | 20.6 / 20.6 |
| ADC_VCM, ADC_VREF | 18.4, 15.9 (all) |
| REF10M | 16.7 / 35.0 |
| K1_COIL, K2_COIL (relay coils) | 17.7, 12.2 |

Proposed fix: add a GND zone on In2.Cu at the lowest priority covering the whole board, so the power islands keep
their copper and everything else on In2 becomes GND. Separately, the ADC sample clock (ADC_CLKP/N) should not run
27 mm on B.Cu at all: it belongs in the hand-routed critical set (F.Cu over In1 GND, short, coupled), like the RF chain.
