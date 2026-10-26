# Brief for AGY: U12 south-west plan (ADC bus, FPGA config, flash), round 1 (2026-10-25)

Written by Claude. Write only under `notes/u12sw/`; do not edit `kicad/` or `gateware/`. Mark claims per PROTOCOL.

## State
kicad/work at commit 6f4461e (your U11 plan + USB2 route adopted): 33 unconnected, DRC copper-clean (the 10 SMA edge
items and dangling stubs are known). DeepPCB run 5 on this board stopped after 4 min with no revision: the remaining
opens are one congested region, the same situation U11 was in. All 33 are listed below with DRC endpoints
(`open_nets` in the data file).

| Group | Nets | From -> to |
|---|---|---|
| ADC data | ADC_D0-D5, D11-D13, ADC_OR | series R (R26-R41, x 139-148, y 134-145; R->U12 half open) -> U12 bank-7 balls / escapes x 157.8-160.2, y 122-125.2 |
| ADC stubs | ADC_D4_R (U8 143.4,141.8 -> R30 147.4,141.7), ADC_RBIAS (U8 138.6,140.8 -> R42 147.1,145.8) | short |
| ADC SPI | ADC_CSB, SCLK, SDIO | U8 (140.8-141.8, 143.4) -> U12 (157-158.6, 122.8-125.2) |
| FPGA config | FPGA_CFG0/1/2, DONE, INIT_N | R54/R55/R56/R53/R52 (151-156, 141-144) -> U12 (163.4-164.2, 127.6-130.0) |
| | FPGA_PROGRAM_N | U12 (163.4,129.2) -> (166.9,137.8) |
| Flash | FLASH_IO1, FLASH_IO2 | U10 (156.4,137.4) / (160.1,135.7) -> U12 (161.8,130.0) / (161.8,126.8) |
| Misc | LED1 U12 (157.8,126) -> D5 (162.6,133.4); LMK_SDA U12 (157,128.4) -> (141.8,146.9) | |
| Rails | 1V1 (156.3,135.1)-(155.5,133.9) and an In2 island sliver at (162.7,122.1); 1V8_D U8 (143.4,140.8)-(144.3,140.6) and (153.4,121.2)-(149.9,139.3); 2V5 (153,131.6)-(155.2,131.8), (161.4,126.4)-(165,134.9), In2 sliver (164.9,123.5); 3V3_D R52 (156.2,141)-(155.9,138.9) | PWR class, w 0.4 where it fits (necking to 0.2 at pads is fine) |

Render: `notes/u12sw/u12sw_open.png` (open-net pads orange). Data: `notes/u12sw/u12sw_data.json` (box x 134-172,
y 112-150; same layout as u11_data.json: parts with pads / bbox / net / locked, tracks and vias with uuid, zones,
open_nets, rules; regenerate with `python3 notes/u12sw/extract_u12sw.py`). The U12 pad list is limited to balls in
the box. Signal layers F.Cu and B.Cu only. No parts on B.Cu.

The In2 "slivers" (1V1 at 162.7,122.1; 2V5 at 164.9,123.5) are isolated pieces of the In2 power islands under U12
that the fill cut off from the rest: they need a via/track link or a clear path in In2 (moving or removing the via that
cuts them off), not a zone edit (zones are not part of the plan format; tell me if you think a zone outline must
change and I will do it).

## Rules
- Track 0.15 (0.127 ok for necking at pins), clearance 0.127 (PWR 0.15 / w 0.4), via 0.45/0.2 (min 0.4/0.2), hole
  clearance 0.25, hole-to-hole 0.25, edge 0.5. BGA pitch 0.8 mm: one 0.15 track between ball pads.
- ADC timing (notes/pinswap/agy_timing_check.py, your numbers): data total U8->R->U12 <= 55 mm, skew to ADC_DCO
  (25.99 mm) within +/-25 mm, so each data net 1..51 mm in total; U8->R stub <= 8 mm. ADC_CSB/SCLK/SDIO <= 120 mm.
  Note the checker measures connected copper only, so a half-open net (D0, D1, D3, ...) shows PASS with a few mm:
  the DRC unconnected list is the closure test, the checker the length test.
- Do not move U8, U10, U12, U11, K2, the RF/filter parts (L6-L11, C32-C42, U13, J3), or the series resistors
  R26-R41 (their stubs set the ADC stub lengths). Unlocked parts (D5, R42, R57-R60, R64, R65, Q2, decaps
  C49-C58, C86-C105, C14-C17) and the config pull-ups R52-R56 may move if it frees a lane; decaps stay <= 2 mm from
  their rail pin and keep their connection. Keep every moved part's courtyard clear.
- Any copper you rip (routed nets, locked fan-out copper) must be re-created by the plan or the trial lists the net
  as BROKEN. Re-routing already-routed nets is fine if it frees the corridor (ADC_D6-D10 / DCO timing must still
  pass).

## Task
Make an explicit route plan that closes all 33, as `notes/u12sw/agy_u12sw_plan.json`, same format as round U11:
```
{"moves": {REF: {"xy": [x, y], "rot": deg}},
 "rip": [uuid, ...], "rip_nets": [regex, ...],
 "tracks": [{"net": "ADC_D0", "layer": "B.Cu", "w": 0.15, "pts": [[x, y], ...]}],
 "vias": [{"net": "ADC_D0", "xy": [x, y], "size": 0.45, "drill": 0.2}]}
```
Track `pts` start/end exactly on a pad centre, existing track end or via; vias sit on a point of a track of that net.
Net names as in the data file (hierarchical names are full, e.g. as printed in `open_nets`).

**Check it yourself before replying**, with real KiCad fill + DRC on a throw-away copy:
`python3 kicad/gen/u11_trial.py notes/u12sw/agy_u12sw_plan.json 2>/dev/null` (`--keep /tmp/u12k` keeps the board).
It now also prints "all still open" and the ADC timing FAIL lines. Iterate to 0 new copper DRC errors, BROKEN empty,
no plan items dangling, all still open empty (FT_SIWU_N in the timing output is a known checker name mismatch). If
you cannot close everything, deliver the best plan and name what remains and why (geometry), so I can decide.
Prefer fewer, cleaner segments over a 0.025 mm staircase where you can (last round had 584 segments < 0.05 mm;
cosmetic, but harder to review). Count vias honestly in the summary.

Deliverables: `notes/u12sw/agy_u12sw_plan.json`, `notes/u12sw/agy_u12sw.md` (method: lane per net with layer and
via positions; part moves; ADC lengths/skew table; final trial output pasted verbatim).
