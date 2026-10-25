# Brief for AGY: U11 (FT601) escape plan, round 1 (2026-10-25)

Written by Claude. Write only under `notes/u11/`; do not edit `kicad/` or `gateware/`. Mark claims per PROTOCOL.

## State
kicad/work after DeepPCB run 4 (commit 3cfb659): 54 unconnected, DRC copper-clean. 19 FT601 nets stayed open through
every router (DeepPCB x2, KRT, grid_route):
- U11 bottom row (y=127.44): FT_BE1, BE2, BE3, TXE_N, RXF_N, WR_N, RD_N (pins 5-12, x 182.0-184.8)
- U11 top row, east half (y=118.56): FT_D12, D9, D6, D4, D2, D1, D0 (pins 54..40, x 181.6-187.2)
- U11 west column (x=179.56): FT_D16, D18, D24, D25, D27 (pins 60, 62, 69, 70, 72)
The other ends are U12 balls or their existing escape stubs/vias at x 165-169.4 (see `open_nets`).
Render: `notes/u11/ftopen_r4.png`. Diagnosis: the U12-U11 corridor is full of the bus nets that did route, wrapped
around U11's corners; the east top-row pins can only be entered from the north, where your T5 decaps C76, C71, C72
(y=116.3) and C73 (187.42,116.85) sit. QFN pitch 0.4 mm: no track between pins, every pin is entered straight on.

Data: `notes/u11/u11_data.json` (box x 164-202, y 106-142; regenerate: `python3 notes/u11/extract_u11.py`):
`parts` (pos, rot, locked, pads with bbox and net), `tracks` / `vias` (uuid, net, layer, locked), `zones`
(In1 GND plane; In2 GND/3V3_D/2V5/1V1 islands; EDGE_KEEPOUT), `open_nets` (DRC endpoints per open net), `rules`.
Signal layers are F.Cu and B.Cu only. No parts on B.Cu.

## Rules
- Track 0.15 mm (min 0.09 abs; 0.127 ok for necking at pins), clearance 0.127 (PWR class nets 0.15, width 0.4),
  via 0.45/0.2 (min 0.4/0.2), hole clearance 0.25, hole-to-hole 0.25, copper-edge 0.5.
- FT601 length <= 45 mm, skew to FT_CLK (12.53 mm) within -10..+30 mm (your route r1 table).
- Do not move U11, U12, or anything else locked except decaps. Decaps may move but stay <= 2 mm from their rail pin
  and keep their connection (include the stubs / vias in the plan).
- Any copper you rip (including routed FT nets and locked fan-out copper) must be re-created by the plan, or the
  trial lists the net as BROKEN.

## Task
Make an explicit escape + route plan that closes all 19 nets (re-routing already-routed FT nets if that frees the
corridor), as `notes/u11/agy_u11_plan.json`:
```
{"moves": {REF: {"xy": [x, y], "rot": deg}},
 "rip": [uuid, ...], "rip_nets": [regex, ...],
 "tracks": [{"net": "FT_D0", "layer": "B.Cu", "w": 0.15, "pts": [[x, y], ...]}],
 "vias": [{"net": "FT_D0", "xy": [x, y], "size": 0.45, "drill": 0.2}]}
```
Track `pts` must start/end exactly on a pad centre, existing track end or via; vias you add must sit on a point of a
track of that net. Net names as in u11_data.json (FT nets are bare, e.g. `FT_D0`).

**Check it yourself before replying**, with the real KiCad fill + DRC on a throw-away copy:
`python3 kicad/gen/u11_trial.py notes/u11/agy_u11_plan.json 2>/dev/null`
(add `--keep /tmp/u11k` to keep the board). Iterate until it prints 0 new copper DRC errors, BROKEN empty, no plan
items dangling, and FT still open empty, with the timing check passing for every FT net. If you cannot close all 19,
deliver the best plan and say which nets remain and why (geometry), so Claude can decide on decap/pin-swap options.

Deliverables: `notes/u11/agy_u11_plan.json`, `notes/u11/agy_u11.md` (method: lane assignment per net with layer,
entry side, via positions; decap moves; the final trial output pasted verbatim).
