# Claude's review of AGY's fan-out plan (agy_fanout_plan.json, 2026-10-24 18:55)

Independent checks: `notes/fanout/claude_check_fanout.py` style one-offs (net of every ball each via serves, ball-via
distances, kept vias, polygon coverage of existing rail vias, parts under the new polygons), plus a render
(`notes/fanout/agy_plan.png`). AGY's own checker passes; these are things it does not test.

| Item | Verdict | How checked |
|---|---|---|
| F1 (power copper in the rings + passive column are the blockers) | VERIFIED | AGY's channel count agrees with the render; its extra finds (locked 2V5 F.Cu track at x=159.8, 3V3_D B.Cu trunk in bank 7, the x~177 FT601 passive column, three router detours) are real: all visible in fanout_now.png / wide render. |
| F1 sub-claim "B.Cu inter-via gap 0.350 >= 0.150 + 2(0.090) = 0.330" | DISPUTED | Our clearance is 0.127 mm, not 0.09: 0.150 + 2(0.127) = 0.404 > 0.350, so no B.Cu track between adjacent fan-out vias (your own C2 result). Does not change the plan, which keeps signal vias out of those gaps. |
| F2 | VERIFIED | same ball lists as Claude's script |
| F3 (0.70 <= 0.80, 0.10 slack; keep splits off adjacent pairs) | VERIFIED | arithmetic; plan's min different-net power via distance 1.131 mm reproduced |
| T2 core vias: 20 vias, every ball's net matches its via, 21/21 power + 15 core GND served, 12 perimeter GND vias kept | VERIFIED (bookkeeping) | script: no net mismatch |
| T2 geometry: the 1.265 mm 'two-step' dog-bones | DISPUTED | Applied to a scratch board, KiCad DRC shows shorts: F6/F7 -> (162.2,120.8) and F10/F11 -> (164.6,120.8) (3V3_D) run over E7, E10, E11; F8/F9 -> (163.0,120.8) (GND) over E8, E9. Row F is y = 122.0, row E y = 121.2, so y = 120.8 is the D/E interstitial row, not E/F (looks like an off-by-one row). G6 -> (162.2,122.4) and K6 -> (162.2,125.6) also span two columns. Every dog-bone has to be ball +/-0.4,+/-0.4 (0.566 mm). |
| T1 islands 1V1 / 1V8_D / 2V5 inside the core + necks | PLAUSIBLE | to be proven by refill + DRC; the necks are long only because the decaps were moved far away (next row) |
| T1 new 3V3_D polygon replacing the old rectangle | DISPUTED | New bbox 150.65-195 x 115-157.5 vs old 152-199.7 x 100.3-142. It puts 3V3_D (instead of the In2 GND fill) under U1 U2 U3 U4 U5, L2, Q2 and the regulator area, and drops it north of y=115 and east of x=195. Not needed: the islands at priority 2 already carve themselves out of the old priority-1 rectangle. Claude keeps the old 3V3_D zone (KEEP_ZONES unchanged). |
| T3 decap moves | DISPUTED | C81 C82 C83 C84 C85 C87 C88 (1V1), C90 C91 (2V5), C92 (1V8_D) move 19-32 mm from the BGA to y 146-150 / x 153. "Within 0.5 mm of the rail polygon" meets the letter of the brief but not its intent ("within ~3 mm of their rail's BGA via"): a 100 nF cap at the end of a 20-30 mm, 0.53 mm In2 neck has ~10+ nH of loop and is no longer a local decoupler. The brief's 3 mm is the requirement. |
| T3 other moves (R13 R18 R52-R56, C66/C67 next to Y1 (191,131), C70 C72 C76 C80 1-4.5 mm) | ACCEPTED | C66/C67 end up closer to the crystal Y1 than before; config resistors location-free; FT601 decaps still within 4.5 mm of U11 |
| R50 at (159.26,132.6) | ACCEPTED | |
| Notes on fanout_apply.py | 2 of 3 taken | (2) ripping the locked 2V5 trunk: yes, done by listing its uuids. (3) 2-segment GND dog-bones: yes, fanout_apply.py now walks the dog-bone chain from a deleted via to the ball (locked or not). (1) KEEP_ZONES: no, see 3V3_D row. Line numbers you quoted do not match the file (it was not edited). |

## Found when applying v1 to a scratch board (scratchpad/fo1)
- Moved parts land on existing routed copper: C92 on REF10M and ADC_OR, R13/R18 on D4_K and FLASH_IO1, R50 on FLASH_IO1,
  R52-R56 on the 5V_SW track, C81 on 3V3_D, C66/C67 on FT_1V0, C87 near 5V_SW. agy_fanout_check.py checks courtyards
  only; it should also check pads against existing tracks/vias of other nets (or list which nets Claude must re-route).
- The old locked GND track G10-H10 (vccaux_patch) is not a dog-bone of a listed via, so it stays and clashes with the new
  2V5 via at (164.6,123.2) (0.4 mm away).

## Routing trials on the v1 board (scratch only; nothing applied to kicad/work)
| Trial | Setup | FT601 bus | ADC (U8->R->bank 7, 35 nets) |
|---|---|---|---|
| krt5 | v1 applied (3V3_D polygon dropped), conflicts ripped; KRT bga_fanout + qfn_fanout + route, strict rules | BGA fan-out 36/46 (its own outer F.Cu escapes block inner via sites); 26/46 routed | 22/35 |
| krt6 | same, but AGY's 27 escape vias placed directly (`kicad/gen/escape_apply.py`), KRT routes only | U12 side all escape; 27/46 routed | 17/35 |

krt6 failures are not at the FPGA any more: 11 of the 19 failed FT nets (D2 D3 D5 D8-D14) land on U11's **top pin row**
(y = 118.6, x 180.8-186.4) and 4 (BE1 BE2 RD_N RXF_N) on its **bottom row** (y = 127.4). Those pins can only be
approached from outside the package, where the FT601's own decaps sit (C73 C68 C69 C70 C76 above, C80 C72 C71 C79
below). Next bottleneck: FT601 decap/crystal placement (move them to U11's east side or between the pin rows' far ends).

## Round 3 (agy_fanout_plan_v3.json, 21:38)
| Item | Verdict | How checked |
|---|---|---|
| All four rails fill as one piece; 0 copper conflicts; 0 long rail gaps | VERIFIED | Claude re-ran `kicad/gen/fanout_trial.py` on v3 (scratchpad/fo3): identical output to AGY's |
| Long / merged core dog-bones (G6 -> (163.0,122.4) 2.04 mm etc.) | VERIFIED | full DRC on the trial board: no shorting/clearance items |
| T5 FT601 decap moves, 0 courtyard overlaps | DISPUTED (minor) | DRC: C69 at (189.85,123.0) overlaps the U11 and C63 courtyards. place_free.py moves it to (191.85,123.6) rot 270 (about 3.3 mm from U11.28, over the 2 mm target) |
| 3V3_D via (168.40,139.63) for J3.1 | DISPUTED (minor) | lands inside a keep-out area (DRC items_not_allowed) and on an FPGA_TMS track, so KiCad gives it the TMS net. Dropped; J3.1 gets a surface stub |

Routing trial krt7 (v3 + the two fixes + AGY's 27 escape vias; KRT strict rules): FT601 31/46 routed (was 27/46 on v1);
U11 top-row failures 11 -> 4. Remaining FT failures: 7 on U11's west side (FT_D16 D22 D25 D27-D29 D31, from the deeper
SE balls M13 N11-N14 P11 that escape on B.Cu), 4 bottom row, 4 top row. ADC 15/35 (U8 -> resistor side is local
congestion near the ADC, which the fan-out plan does not touch). KRT also broke FPGA_TDI.

## Applied to kicad/work + DeepPCB run 3 (2026-10-24 22:30-23:15)
- Applied `plan_v3_claude.json` (v3 + C69 move, minus the keep-out via) with fanout_apply, repair_conflicts and
  escape_apply. DRC: 0 copper conflicts, 181 unconnected, parity 0. Backup: kicad/deeppcb/work_before_fanout.kicad_pcb.
- DeepPCB run 3 (CurrentProtectedWiring, 17 min, ~$8.50): 181 -> 69 open (its count). All existing copper kept (a
  locked 1V8_A stub was only re-segmented), no parts moved, nothing on inner layers. Lock flags restored (relock.py,
  454). Raw: kicad/deeppcb/r3_deeppcb_routed.kicad_pcb.
- DeepPCB broke the rules in two places: Q1_G and Q2_G ran 20-30 mm along the top edge at 0.34 mm (rule 0.5), and
  FPGA_TCK sat too close to J3's NPTH. Claude ripped those (50 items with stubs): 80 open. Saved as
  kicad/deeppcb/work_after_r3.kicad_pcb.
- KRT on top (strict rules, existing copper kept or rerouted unlocked only): fixed 16 nets, broke 1 (ADC_D4_R). Work
  board now: **65 unconnected**, DRC only the 10 inherent SMA edge items + dangling stubs/vias, parity 0.

## DeepPCB run 4 (2026-10-25 00:23-00:53, 30 min) on the prepared board
Prep (scratchpad/r4, kept as kicad/deeppcb/r4_input.kicad_pcb): FT601 lanes cleared of non-bus copper
(kicad/gen/lane_clear.py), FT_D25 detour ripped, AGY's ADC resistor moves (4 nudged off K2/U8 by place_free), whole
ADC bus ripped for a fresh route, C80 -> (190.40,127.50), R47 -> (193.46,122.40) rot 90 out of the USB2 path,
0.6 mm edge keep-outs (kicad/gen/edge_keepout.py). Result 93 -> 49 (DeepPCB count); after relock/refill: DRC clean
(10 inherent SMA items only), **54 unconnected**, parity 0. All routed FT/ADC nets pass AGY's corrected length/skew
rules. Adopted into kicad/work (previous: kicad/deeppcb/work_before_r4.kicad_pcb).

The same 19 FT601 nets stay open through every router: BE1-3, RD_N, WR_N, RXF_N, TXE_N (U11 bottom row), D0 D1 D2
D4 D6 D9 D12 (east half of U11's top row), D16 D18 D24 D25 D27 (U11 west side). Render: the corridor is full of the
nets that did route, wrapping round U11's corners; the east half of the top row can only be entered from the north,
where C71 C72 C73 C76 now sit at y ~116.3 (T5 moves). Needs an explicit escape plan for U11, not more router time.
