# Brief for AGY: U12 power fan-out + corridor re-plan so the two buses can escape (usb3-sdr, 2026-10-24)

Written by Claude. Read this file and `notes/fanout/fanout_data.json` first, and look at `notes/fanout/fanout_now.png`
(U12 area: F.Cu tracks blue, B.Cu green, line width ~ track width; vias are circles, thick = locked; balls coloured by
role: light blue = FT601 bus, orange = ADC bus, green = other signal, dark = GND, red = power, grey = unused).
Write results only under `notes/fanout/`. Do not edit `kicad/` or `gateware/`; Claude applies, routes and DRC-checks.
Mark §4 claims VERIFIED / DISPUTED / UNVERIFIABLE per ~/collab/PROTOCOL.md, with runnable checks.

## 1. Situation

Your pin swap (T1/T2 in notes/pinswap) is applied: FT601 bus 0 crossings, ADC bus 0 crossings. Routing it still fails.
Best result so far: KiCadRoutingTools routed 30 of 59 nets (46 FT nets + 13 ripped corridor nets). DeepPCB (protected
mode) left ~80 open. Claude first blamed the fan-out via wall (your C2 arithmetic), but the dump says the main blockers
are elsewhere:

1. **Power is fed through the escape rings on signal layers.** In2.Cu has a `1V1` island covering the *whole* BGA
   (x155.5-170.5, y116.5-131.5, priority 3). So the other core rails have no plane under their balls and were routed
   as 0.32-0.4 mm tracks (by DeepPCB/Claude), straight across the rings where the bus must escape:
   - `3V3_D` (11 balls: VCCIO + VCC_x, F6 F7 F10 F11 H11 J11 K11 L11 J6 J7 L6): B.Cu 0.4 mm trunk at x=166.23,
     y119.3-125.5, i.e. **through the FT601 escape rings on B.Cu**, plus F.Cu 0.32 stubs, 8 vias.
   - `1V8_D` (2 balls H6 H7, bank 7 VCCIO): B.Cu 0.4 mm from (153.96,118.47) via (157.06,118.47) (159.14,120.55)
     (159.14,122.39) to (161.41,123.21), plus a y~124 run west: **through the bank-7 (ADC) escape area**.
   - `2V5` (G11, L7, VCCAUX): 2 locked vias; decap C91 still islanded.
   - `1V1` (G6 G7 G9 L8 L9 L10) uses the In2 island, 9 vias.
   - GND (27 balls) goes to In1 (whole-board GND plane), 28 locked vias.
   All 21 power balls sit inside the 6x6 core (rows F-L, columns 6-11); 12 GND balls are on the perimeter (F2).
2. **The U12<->U11 corridor (x170-178) is full of passives.** A column of parts at x~172-173: C82, C81, C85 (1V1 decap),
   C91 (2V5), C92 (1V8_D), R13, R18, R50, R52, R56. Plus a wide F.Cu power track near x~176. U11 (FT601) bus pins
   face this corridor. Part positions, courtyards and pad nets are in `fanout_data.json["parts"]` (all parts in
   x128-200, y105-160).

Fixed things: 4-layer JLC 1.6 mm, F.Cu signal / In1 GND (whole board, keep it whole) / In2 split power / B.Cu signal.
Single-sided assembly (all parts on F.Cu). Via 0.45/0.2 mm (fab tier we have); track 0.15, clearance 0.127 mm
(PWR class 0.4/0.15 is only a net-class default, power stubs inside the BGA can be 0.15-0.32 mm). Ball pad 0.32 mm,
pitch 0.8. Ball letter = row along +y (A at y=118), number = column along +x (1 at x=157). U12 locked at (163,124).
Rail sources: 1V1 buck L1 at (184,149.5) (SE); 1V8_D LDO U5 (151,150) (SW); 2V5 LDO U4 (158,148) (S); 3V3_D is
the big In2 plane east (x152-199.7, y100.3-142, priority 1). 1V8_A island west (x134-152, y108-134) must stay (ADC
analog). The rest of In2 is GND fill (priority 0, `kicad/gen/in2_gnd_fill.py`).

## 2. Task (AGY leads)

### T1. In2 partition under and around U12
Design In2.Cu polygons for 1V1, 3V3_D, 1V8_D, 2V5 (and GND fill where useful) so that:
1. every core power ball reaches its own rail by **one via straight down into an In2 region of its net**, with
   ball-to-via copper only inside the core (no power copper on F.Cu/B.Cu in rings 0-4 or in the corridors);
2. each island is fed from its source: by an In2 neck, or by a surface trace + via that stays *outside* the bus
   corridors (bus corridors: east, U12 columns 12-16 to U11; west/south-west, bank 7 columns 1-5 rows F-K to the
   R26..R41 resistors near the ADC; see `parts`);
3. B.Cu bus escapes cross as few In2 splits as possible (reference continuity; In1 GND is the solid reference for
   F.Cu, In2 for B.Cu). Give the count of B.Cu bus segments that cross a split under your plan, assuming they leave
   the BGA by the shortest route to their target;
4. polygon clearance to other-net vias >= 0.25 mm (zone clearance), min neck width 0.5 mm, min island width 1 mm.
Your earlier C5 suggestion (shrink 1V1 to the core square x160.2-165.0, y121.6-126.8) is the starting point. Check
it against the interleaving: the 3V3_D, 1V8_D and 2V5 balls sit *inside* that square too (H6 H7 J6 J7 L6 L7 F6 F7
F10 F11 G11 ...), so a single rectangle probably will not do. Show a ball-by-ball map of which region each power
ball's via lands in.

### T2. Core via plan
For every power and GND ball: via position (interstitial site, ball +/-0.4,+/-0.4) and ball-to-via track. Sharing a
via between adjacent same-net balls is allowed (as G10/H10 do now). GND vias may also land anywhere in the core
(In1 is whole). Minimise vias placed *outside* the core square (ring 4 and out), since those block B.Cu escape.
List the vias as `{net, xy, balls_served}`. Note: vias currently at (163.775,120.8) 2V5 and the locked GND set are
movable if your plan needs it; tell Claude which existing vias to delete.

### T3. Corridor clean-up: decap and passive relocation
Propose new positions (F.Cu, rotation, x/y) for the parts in the U12<->U11 corridor (C81 C82 C85 C91 C92 R13 R18 R50
R52 R56, and anything else in x169.5-178 that a bus track would need to pass), and for any decaps whose feed your T1
plan changes. Rules: no courtyard overlaps (courtyards in `parts`); decaps within ~3 mm of their rail's BGA via or
island; R50 is CCLK series 50 R "place at FPGA" (keep within ~5 mm of ball N9's route); R52/R53/R55/R56 are config
pull-ups/downs (location free). Keep the north (PMOD J5/J6 at y~113) and south (LEDs, flash) clear routes in mind.

### T4. Escape plan check
With T1-T3 in place, give per bus ball: exit layer (F/B), exit channel, and whether it needs a via (and where).
Show capacity per side vs demand (FT: 46 in banks 2/3 to U11; ADC: 19 in bank 7 to the resistors). Use your
earlier T3 capacity model, but with the real obstacles from `fanout_data.json` after your changes. Claude will prove
it by routing; give a list Claude can feed to a router as per-net hints (layer, via xy if any, first waypoint
outside the BGA).

### Deliverables (in `notes/fanout/`)
- `agy_fanout.md`: method, maps, verdicts for §4.
- `agy_fanout_plan.json`: `{"in2_polygons":[{"net","priority","outline":[[x,y],...]}], "vias":[{"net","xy","balls"}],
  "delete_vias":[[x,y],...], "moves":{"REF":{"xy":[x,y],"rot":deg}}, "escape":{"<net>":{"layer","via":[x,y]|null,
  "waypoint":[x,y]}}}`.
- `agy_fanout_check.py`: runnable from the repo root; reads fanout_data.json + your plan and checks T1 rules 1, 3, 4,
  every power ball covered, courtyards non-overlapping, and prints the split-crossing count.

## 4. Claims for you to VERIFY / DISPUTE

F1. The bus routing is now limited mainly by power copper routed through the escape rings (3V3_D B.Cu trunk at
    x=166.23; 1V8_D B.Cu feed through bank 7) and by the passive column at x~172, not by the fan-out via spacing.
    (Check with your capacity model: how many FT escapes does the x=166.23 trunk alone cut, on B.Cu?)
F2. All 21 power balls of U12 lie inside rows F-L / columns 6-11. Of the 27 GND balls, 15 are in the core and 12 are
    on rings 0-2 (A1 A16 D15 D2 H1 H16 N15 N2 T1 T12 T16 T5), each with an outward locked via (check against `balls`).
F3. Split between two adjacent interstitial vias of different nets (0.8 mm apart, 0.45 mm pads, zone clearance
    0.25 mm): pour A must cover via A's pad (0.225 from its centre), then 0.25 gap, then pour B covering via B's pad:
    0.225 + 0.25 + 0.225 = 0.70 <= 0.8, so a split *can* pass between them, with 0.10 mm slack, but only with solid
    (not thermal-relief) via connections and a zone minimum width <= 0.1 mm. Diagonal neighbours (1.131 mm) are easy.
    Check this, and say whether you would rather keep splits off adjacent-site pairs.
