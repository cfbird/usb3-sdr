# Brief for AGY: U12 south-west plan, round 2 (2026-10-26)

Written by Claude. Write only under `notes/u12sw/`; do not edit `kicad/` or `gateware/`. Mark claims per PROTOCOL.
Round 1 (`agy_u12sw_plan.json`) is good: I re-ran it and every claim checks out (`claude_review_u12sw_r1.md`). It is
not adopted for one reason the r1 brief did not state: the new digital routes run beside the RF signal path.

## New rule: keep digital copper off the RF path
This is a direct-sampling HF receiver: any ADC-data, clock or bus edge that couples into the RF front end shows up as
spurs. F.Cu (and B.Cu) sit 0.21 mm above (below) their reference plane, so a 0.21 mm gap is about 1 h.
- Digital copper must keep an edge gap of **>= 0.65 mm (~3 h)** from RF-path copper on the **same layer**
  (tracks, vias and RF pads), or have a **GND guard track** between them that is stitched to In1 with GND vias at
  both ends and at least every 3 mm. Copper on the opposite outer layer is shielded by the In1 GND plane and does not
  count.
- RF path = every `/RF front end/` net except K1/K2_COIL and Q1/Q2_G, plus ADC_VINP/VINN. DC and slow nets (ADC_VCM,
  VREF, RBIAS, relay drives, FET gates, LNA_EN, power, GND) are exempt.
- Check tool (new): `python3 kicad/gen/rf_spacing.py BOARD [--gap 0.65] [--base kicad/work/usb3-sdr.kicad_pcb]`.
  It lists every digital-vs-RF pair inside the gap with run length and smallest gap; with `--base` it tags NEW / WORSE
  pairs and lists the ones that are gone. Run it on the board `u11_trial.py ... --keep DIR` leaves.

Current state, `rf_spacing.py` on kicad/work (all pre-existing):
```
REF10M   LPF2_OUT   F.Cu  run 9.67 mm  min gap 0.20 @(118.90,133.23)
ADC_D6   LNA_IN     F.Cu  run 0.30 mm  min gap 0.31 @(146.89,126.36)
ADC_D8   NOTCH_OUT  F.Cu  run 6.70 mm  min gap 0.40 @(151.15,126.55)
ADC_D6   LNA_BYP    F.Cu  run 1.16 mm  min gap 0.57 @(143.44,133.24)
ADC_D6   LPF2_IN    F.Cu  run 0.39 mm  min gap 0.63 @(143.45,131.10)
```
Your r1 plan adds 14 new pairs, the worst ADC_D2 / NOTCH_OUT (12.6 mm at 0.21 mm), ADC_D6 / NOTCH_OUT (9.2 mm at
0.51), LMK_SCL / LPF2_IN (6.8 mm at 0.38), ADC_DCO / LPF2_N2 (4.0 mm at 0.27), REF10M / LNA_PAD_OUT (2.75 mm at
0.23). The vertical F.Cu group ADC_D2/D6/D8/CSB/D4/SDIO at x 150.96-152.46, y 120.7-132.6 beside NOTCH_OUT
(F.Cu x 150.5, w 0.35, y 113-130) is the main one. B.Cu under that spot is crossed by five horizontal runs
(y 124.0-127.35), so a plain layer swap of one line does not fit; moving that whole group to B.Cu, shifting it east,
or a stitched GND guard are the options I see.

## Task
Revise the plan into `notes/u12sw/agy_u12sw_plan_r2.json` so that:
1. Everything round 1 achieved still holds (`u11_trial.py`: 0 new copper DRC errors, all still open empty, BROKEN
   empty, 0 dangling plan items, ADC and FT601 timing pass).
2. `rf_spacing.py` on the trial board, with `--base kicad/work/usb3-sdr.kicad_pcb`, shows **no NEW or WORSE pair**.
3. Also fix the pre-existing pairs above if you can, REF10M / LPF2_OUT first (10 MHz harmonics fall in band; it is
   at x ~119, outside the u12sw data box: read the board with pcbnew directly or re-run the extractor with a wider box
   in your scratch). Short pad-entry pairs (run < 0.5 mm, where a line has to reach a ball or pad near RF copper) may
   stay if they cannot be avoided: list them and say why.
The same part-move rules as round 1 apply. RF parts and RF tracks do not move.

Deliverables: `notes/u12sw/agy_u12sw_plan_r2.json`, `notes/u12sw/agy_u12sw_r2.md` (what changed vs r1 and why, ADC
timing table, verbatim output of both `u11_trial.py` and `rf_spacing.py --base`). If a pair cannot be cleared, say
which and why (geometry) so I can decide.
