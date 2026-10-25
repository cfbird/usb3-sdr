# Claude review: AGY U11 escape plan r1 + thermal check (2026-10-25)

Round 1 first reply was blocked by a Gemini content filter (false positive, no files written); the re-ask (r1b)
delivered `agy_u11_plan.json` / `agy_u11.md`.

## Plan
| Claim | Verdict | How |
|---|---|---|
| u11_trial: 0 new copper DRC errors, 19/19 FT nets closed, BROKEN none, 54 -> 35 | VERIFIED | re-ran `u11_trial.py` on kicad/work, identical output |
| All FT601 sync nets pass length / skew | VERIFIED | `agy_timing_check.py -v` on the trial board: 11.2-28.5 mm, skew -1.4..+15.8 mm vs FT_CLK 12.63; remaining FAILs are pre-existing (ADC_OR/D2/D4 open, FT_SIWU_N is a checker name mismatch for FT_SIWU) |
| "routed 100% on F.Cu with 0 vias" | DISPUTED (minor) | the plan has 50 vias; 29 FT nets use 1-2 (top-row bus and bottom row go B.Cu under U11). Lengths still pass; vias not counted by the checker (~1.6 mm each) leave margin |
| Compatible with Claude's USB2 plan and 7 EP vias | VERIFIED | combined trial: 0 new copper errors; only VBUS->R47 branch re-opened (usb2_patch re-route vs C65's new spot), re-routed with grid_route |

Geometry: 1178 segments, 584 shorter than 0.05 mm (0.025 mm grid staircase), 98 % at 45-degree multiples, no
acute turns. Cosmetic; left as is. 17 signal vias sit in the ring between U11's pins and the centre pad (tented
front/back, no solder-mask-bridge errors). B.Cu runs under the centre pad (datasheet allows: rule is chip layer only).

## Thermal (FT601 centre pad, ~0.61 W)
| Claim | Verdict | How |
|---|---|---|
| Via barrel R: 0.2 mm drill 337 K/W full length, 42 K/W to In1; 0.3 mm 231 / 29 | VERIFIED | R = L / (k A), A = pi (d+t) t, t 18 um, k 385: recomputed |
| FR-4 path pad->In1 18.2 K/W; net 4.5 K/W (7 x 0.2) vs 2.1 (12 x 0.3) | VERIFIED | 0.2e-3 / (0.30 x 36.66e-6); parallel combination recomputed |
| dT_J ~23 C (7 vias) vs ~18 C (12 vias) | UNVERIFIABLE (plausible) | rests on assumed theta_JC,bot 3 K/W and plane-to-ambient 25-30 K/W; FTDI gives no theta_JA. Pad-to-plane drop itself (0.61 x 4.5 = 2.7 C) is solid |
| 12 x 0.3 grid would block the B.Cu corridors under U11 | VERIFIED | render of the adopted board: top-row bus crosses under the pad on B.Cu at y 119.5-122 |

Decision: keep the 7 x 0.2 mm EP vias.

## Adopted
kicad/work = work + AGY plan + usb2_patch + usb2_plan_claude + VBUS re-route. Backup:
kicad/deeppcb/work_before_u11.kicad_pcb. DRC: 33 unconnected, parity 0, copper clean (10 known SMA edge items,
dangling stubs/vias only).
