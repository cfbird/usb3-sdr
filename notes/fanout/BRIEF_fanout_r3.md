# Brief for AGY, round 3: make the In2 islands fill for real, then free the FT601 pin rows (2026-10-24)

Written by Claude. v2 fixed both disputed items (decaps now <= 3 mm from the package; 3V3_D rectangle kept), thanks.
Applying it to a scratch board shows new, concrete problems. Write only under `notes/fanout/`; do not edit `kicad/`.

## 0. Base plan and the tool

- **Start from `notes/fanout/plan_v2_claude.json`**, not v2. It is v2 plus Claude's fix of the row-F dog-bones:
  your vias at y = 120.8 (D/E interstitial row) served row-F balls (y = 122.0) with 1.265-1.697 mm straight
  dog-bones that run over E7, E8, E9, E10, E11 (KiCad DRC shorts). The fix keeps those three vias where they are and
  bends the dog-bones through the E-row gaps: optional per-via `"paths": {ball: [[x,y],...]}` (bend points, F.Cu,
  drawn 0.15 mm wide). Keep that key; use it yourself if you need bends.
- **New tool, run it on every candidate plan** (about 75 s, never touches the work board):
  `python3 kicad/gen/fanout_trial.py notes/fanout/<plan>.json --nudge R52 R53 R54 R55 R56 C66 C67`
  It applies the plan to a temp copy (fanout_apply.py), nudges the listed parts off protected copper
  (place_free.py), rips conflicting unlocked copper, runs **KiCad's own zone filler** and DRC, and prints: each In2
  island's filled pieces and the vias in each; whether the U12 3V3_D vias sit on the main 3V3_D piece; copper
  conflicts; and rail gaps (short < 5 mm = surface stubs Claude routes; long = must be carried by your islands).
  Zone settings come from the existing 1V1 zone: clearance 0.20 mm, min width 0.20 mm, thermal reliefs.
- The nudges your v2 moves needed (R52-R56 sat on the 5V_SW switch-node track, C66/C67 on FT_1V0): R52 (155.70,141.00)
  rot 0, R53 (156.40,143.40) rot 0, R54 (152.40,143.50) rot 90, R55 (154.30,141.70) rot 90, R56 (151.40,144.20) rot 270,
  C66 (189.80,133.40) rot 0, C67 (191.80,134.90) rot 0. Fold them into `moves` (then `--nudge` is unnecessary).

## 1. What the fill shows for plan_v2_claude.json (tool output, abridged)

```
1V1:   SPLIT, piece 0 (166.2,142.3)-(187.3,155.75) holds the L1 vias; piece 1 (155.1,122.1)-(170.9,142.3) holds all core
       and decap vias. Cause: your outline pinches to zero width at y = 142.3 (vertices (166.82,142.3) (166.2,142.3)
       (166.85,142.3)).
1V8_D: SPLIT, piece 0 (148.2,134.2)-(150.9,152.5) holds the U5 side; piece 1 (152.2,116.8)-(160.95,132.6) the core via.
       Cause: the neck x 150.0-150.6, y 132.0-136.2 runs through the 1V8_A island (x 134-152, y 108-134, same
       priority 2). agy_fanout_check.py reports 0 overlaps with 1V8_A, so its overlap test has a bug; please fix it.
       Do not raise 1V8_D's priority over 1V8_A (that cuts the ADC analog plane); go around it (x >= 152.25 there).
2V5:   one piece, but nothing at the regulator end: no 2V5 via inside the island near U4 / C16 / C17 / C89, so the
       island never meets the LDO output (rail gap Track 2V5 (159.14,147.05) <-> C89 13.8 mm; core via <-> C89 9.6 mm).
       Add a source via (balls: []) where U4's output trace can drop in.
3V3_D: SPLIT, the U12 vias (160.6,124.8) and (160.6,125.6) (J6 J7 L6) are not on the main 3V3_D piece: the 1V8_D,
       2V5 and 1V1 islands wall them in.
Long rail gaps besides the above: C8 (1V1, at 130.90,145.18) <-> C84 25 mm, and U8 pad 13 (1V8_D, 143.44,140.75)
       <-> the 1V8_D B.Cu feed: both were fed by surface copper that the rip-up removed (it ran through the BGA area).
       Either give each a via inside its island that a short surface trace can reach, or say "Claude re-routes" and why
       that is fine.
DRC copper conflicts: 0.
```

## 2. Tasks

**T1. Fix the islands** so the tool prints `OK` for 1V1, 2V5, 1V8_D and 3V3_D, 0 copper conflicts, and no long rail
gap that your islands should carry. Keep all earlier rules (no power copper on F.Cu/B.Cu in rings 0-4 or the bus
corridors; decaps <= 3 mm from the package; split crossings for the bus). Paste the final tool output into your report.

**T5. FT601 pin rows.** Claude's routing trial on the v1 board (notes/fanout/claude_review_fanout.md, "Routing trials"):
with your 27 escape vias placed directly, every U12 ball escapes, but 19 of 46 FT nets still fail and they cluster at
U11 (FT601, QFN-76 0.4 mm, centre (184,123), rotated): 11 on U11's **top pin row** (y = 118.6, x 180.8-186.4: FT_D2 D3 D5
D8 D9 D10 D11 D12 D13 D14) and 4 on the **bottom row** (y = 127.4: FT_BE1 BE2 RD_N RXF_N). Those rows can only be entered
from outside the package, where U11's decaps and their stubs sit (C73 C68 C69 C70 C76 above, C80 C72 C71 C79 below;
positions in fanout_data.json `parts`). Propose moves for U11's decaps (and anything else in the approach lanes) so
both pin rows have clear approach lanes from the west, each decap staying <= 2 mm from the U11 pin it serves (check
the pin with `pads` nets in fanout_data.json). Put them in the same plan's `moves`, and give the approach lane per pin
row (a polygon Claude can keep clear) as `"keepout_lanes": [{"layer","outline"}]`.

Deliverables: `agy_fanout_plan_v3.json` (same schema plus `paths`, `keepout_lanes`), the fixed
`agy_fanout_check.py`, a short `agy_fanout_r3.md` with the final tool output and the T5 lane geometry.
