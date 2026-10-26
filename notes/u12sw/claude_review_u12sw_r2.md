# Claude review: AGY U12 south-west plan r2 (2026-10-26)

AGY ran ~45 min (BRIEF_u12sw_r2.md sent 13:19 -> reply 14:03; log `agy_u12sw_r2_reply.log`). Plan
`agy_u12sw_plan_r2.json`, notes `agy_u12sw_r2.md`. Trial board kept at scratchpad/u12k2.

## Claims
| Claim | Verdict | How |
|---|---|---|
| u11_trial: 0 new copper DRC errors, 33 -> 0, BROKEN none, 0 dangling plan items | VERIFIED | re-ran `u11_trial.py --keep`, identical output |
| rf_spacing --base: 0 pairs; ADC_D6 x3, ADC_D8 / NOTCH_OUT, REF10M / LPF2_OUT (pre-existing) gone | VERIFIED | re-ran `rf_spacing.py ... --base kicad/work`, identical, exit 0 |
| ADC timing: DCO 30.75 mm; data 27.74-42.58 mm, skew -3.00..+11.83 mm, stubs <= 6.00 mm; SPI 36-40 mm | VERIFIED | `agy_timing_check.py -v` on the kept board, all PASS |
| FT601 unchanged and passing | VERIFIED | 11.22-28.45 mm; only FAIL FT_SIWU_N (checker name mismatch) |
| 0 moves, 175 polylines / 703 segments (5 < 0.05 mm), 100 plan vias | VERIFIED | counted from the plan |
| Ripped "pre-existing dangling 1V8_A stub + via at (138.755,132.852)" | DISPUTED | not dangling: it was the only feed of the In2 1V8_A zone (rect x 134-152, y 108-134, pcb_build.py:321). With it gone, DRC reports `isolated_copper: Zone [1V8_A] on In2.Cu`, new vs kicad/work |

## Narrow tracks (accepted, noted)
Seven nets run at w 0.10 mm, not only necked at pins: ADC_D2 18.7 mm, D8 16.6, D6 16.4, CSB 15.7, D4 15.5, SDIO 13.2,
D4_R 4.0 (F.Cu, 0.23 mm pitch, 0.13 mm gaps). Board minimum is 0.09 mm (`min_track_width` in the .kicad_pro), so
DRC passes; the r1 brief allowed 0.127 for necking only. Effects: higher trace impedance than 0.15 mm at 0.21 mm
height and a tighter fab tolerance; at 30-40 mm LVCMOS18 lengths behind 22R series resistors this is not a
timing or SI problem (timing re-checked above). Fab capability for 0.10 / 0.13 to be confirmed with the chosen fab.

## Floating 1V8_A plane: fix tested
The zone carries no load: every 1V8_A pad sits south of y 134 and all are connected by tracks (trial: 0 unconnected
with the zone isolated). It is left from an earlier ADC position and sits under the RF section. Tested on a copy of
the r2 trial board: zone net 1V8_A -> GND, refill, DRC: 0 unconnected, isolated_copper gone, no other change; the
region fills as one 460 mm^2 GND piece tied by 11 GND vias. Restoring a 1V8_A feed via instead was tried on paper:
the corner (x 136-139, y 132-136) is now full (LMK_SCL and REF10M on B.Cu, Q1_G and ADC_D13/OR on F.Cu).

## Status
ADOPTED 2026-10-26 (user approved r2 + zone -> GND): kicad/work = r2 trial board with the In2 1V8_A rect retargeted to
GND. Backup kicad/deeppcb/work_before_u12sw.kicad_pcb. In-place DRC: 0 unconnected, parity 0, 10 SMA edge items,
8 dangling vias + 1 stub; rf_spacing 0 pairs; timing all pass (FT_SIWU_N checker mismatch only).
