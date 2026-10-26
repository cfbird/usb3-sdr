# Claude review: AGY U12 south-west plan r1 (2026-10-26)

AGY ran ~13.5 h (19:09 -> 08:50). Reply log `agy_u12sw_r1_reply.log`; plan `agy_u12sw_plan.json`, notes `agy_u12sw.md`.

## Claims
| Claim | Verdict | How |
|---|---|---|
| u11_trial: 0 new copper DRC errors, 33 -> 0 unconnected, BROKEN none, 0 dangling plan items | VERIFIED | re-ran `u11_trial.py --keep`, identical output |
| ADC timing: DCO 34.90 mm; data 27.74-42.58 mm, skew -7.16..+7.67 mm, stubs 1.17-6.00 mm; SPI 36-40 mm | VERIFIED | `agy_timing_check.py -v` on the kept board, numbers match row by row |
| FT601 still passes after the FT_D1/D4/D6/WR_N/GPIO0/WAKEUP_N via moves | VERIFIED | same run: 11.22-28.45 mm, skew -1.41..+15.82 mm; only FAIL is FT_SIWU_N (checker name mismatch) |
| In2 1V1 / 2V5 slivers healed without zone edits | VERIFIED | DRC unconnected 0 includes both rails |
| 0 moves, 189 polylines / 715 segments, 6 < 0.05 mm, 111 vias added, 47 ripped | VERIFIED | counted from the plan JSON; no turns of 90 deg or sharper |

Full DRC of the trial board vs kicad/work: same 10 SMA edge items and silk counts; dangling 20 -> 9; 3
`lib_footprint_issues` are an artefact of the temp directory (fp-lib-table path), not of the plan.

## Finding: ADC bus runs along the RF path (not covered by the brief)
Same-layer digital copper within 0.5 mm (edge to edge) of RF-path nets (NOTCH, LNA_IN/RF/PAD/O, LPF, TRAP, ADC_VIN):

| Net | RF net | before | after |
|---|---|---|---|
| ADC_D2 | NOTCH_OUT | - | 12.2 mm at 0.21 mm |
| ADC_D8 | NOTCH_OUT | 5.7 mm at 0.40 mm | (moved out of the 0.5 mm band) |
| REF10M | LPF2_OUT | 9.1 mm at 0.35 mm | unchanged (pre-existing) |
| ADC_DCO | LPF2_N2 | - | 1.3 mm at 0.42 mm |
| ADC_D13 | LNA_PAD_OUT / LNA_IN | - | 0.6 mm at 0.36 mm |

The plan routes six lines (ADC_D2, D6, D8, CSB, D4, SDIO) as a vertical F.Cu bus at x 150.96-152.46 (0.3 mm pitch),
y 120.7-132.6, right beside NOTCH_OUT (F.Cu x 150.5, w 0.35, y 113-130). F.Cu-In1 dielectric is 0.21 mm, so the
nearest line sits at about 1 h from the RF track. B.Cu at x ~151 is crossed by five horizontal B.Cu runs (y
124.0-127.35), so a simple layer swap of ADC_D2 does not fit. Coupling magnitude not computed (UNVERIFIABLE here;
heavy-math item for AGY if wanted). Proposed constraint for a round 2: digital copper >= 3 h (~0.65 mm) edge gap from
RF-path nets on the same layer, or a GND guard stitched to In1 between them; REF10M / LPF2_OUT (10 MHz harmonics in
band) in the same pass.

## Status
Not adopted. kicad/work unchanged (33 open). Trial board kept at scratchpad/u12k.
