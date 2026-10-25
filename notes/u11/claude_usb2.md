# USB2 pair + U11 exposed pad (Claude, 2026-10-25)

Plan: `notes/u11/usb2_plan_claude.json`, on top of `usb2_patch.py` (its VBUS->R47 re-route and pin-24 clear-out;
its grid_route of the pair fails: "no path for USB_D_N"). Trial on that base: 0 new copper DRC errors, BROKEN none,
USB_D_N / USB_D_P / U11 pin 24 (3V3_D) closed, 56 -> 53.

- The pair swaps order between U11 (D- above D+) and J1 (D+ above D-). D+ stays on F.Cu; D- drops to B.Cu at
  (189.3,124.5) right off pin 25, runs under D+ and comes back up at (194.95,127.33) beside J1 pad 2.
  Width 0.26 (USB90). Lengths ~8.0 mm (D+) / ~9.2 mm (D-).
- U11 pin 24 (3V3_D, between the pair) now goes east between the lines to a via at (189.9,124.85), possible once D-
  has left F.Cu.
- C65 (shield cap, 0603) sat across the pair's path with its links to R46; moved to (193.5,127.6) rot 270. Shield
  pad 1 goes by B.Cu (y 126.6) to J1 shield pad; GND pad 2 has its own via; R46 pad 2 got its own GND via.
- **Found: U11's exposed pad (pin 77, GND) had no thermal vias.** Its only path to the GND plane was one via on pin
  26's east escape, which this plan removes. Added 7 GND vias in the gaps between the paste windows (x 182.95 /
  184.0 / 185.05, y 122.03 / 123.0 / 123.97; (185.05,123.97) dropped, an FT_1V0 B.Cu track runs there). FT601
  datasheet thermal-via guidance not yet checked; more vias possible if B.Cu under the pad stays free.
- Not yet applied to kicad/work: AGY's U11 plan round 1 is running against the current work board; both plans get
  merged and trialled together.
