# SMA edge position check: J2 (RF in), J4 (10 MHz ref), Amphenol 132289 (2026-10-26)

## Board vs footprint: CONSISTENT
| | J2 | J4 |
|---|---|---|
| footprint origin / rotation | (102.54, 113.0) / 180 | (102.54, 147.0) / 180 |
| flange face (footprint local x +2.54) | x 100.000 = board edge | x 100.000 = board edge |
| leg ends (model local x -2.21) | x 104.75 (on board) | x 104.75 |
| barrel tip (local x +13.97) | x 88.57 (off board) | x 88.57 |
| pads (centre F.Cu; ground F.Cu + B.Cu) | x 100.000-105.080, end flush with the edge | same |

Edge.Cuts: rectangle x 100-200, y 100-160. Board thickness 1.600 mm (stackup sums to ~1.585 mm); the part is for
0.062" (1.575 mm) boards.

## Footprint vs 3D model: CONSISTENT (not independent)
KiCad library `Connector_Coaxial:SMA_Amphenol_132289_EdgeMount`: F.Fab edge arrow at local x +2.54; legs -1.91..+2.54;
flange +2.54..+4.445 (10.16 wide); barrel to +13.97. STEP model (KiCad StepUp, made by the KiCad library team):
flange rear face at x +2.54, legs back to x -2.21, flange 9.52 (y) x 7.92 (z), bottom legs at z -1.6..-1.83 (1.6 mm
board). One third-party listing (FindIC) gives 9.52 x 7.92 x 12.7 mm, matching the flange.

## Against the Amphenol drawing: UNVERIFIABLE so far
The customer drawing (footprint descr link
https://www.amphenolrf.com/library/download/link/link_id/595984/parent/132289/, also LCSC C3172723) could not be
fetched: amphenolrf.com, alldatasheet, datasheets.com and octopart return 403 to scripted downloads; the Farnell
catalog PDF (2580768) has no dimensions. Needed from the drawing: leg length from the flange face, flange thickness,
centre-pin width and position vs the board top, and whether the flange face is meant to sit on the board edge.
Download it by browser into refs/datasheets/ (gitignored) and re-check.
