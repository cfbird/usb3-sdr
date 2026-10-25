# usb3-sdr KiCad 9 project (Rev A0, generated)

Open `usb3-sdr.kicad_pro` in KiCad 9. Sheets: Power, RF front end, ADC and clock, USB 3 bridge, FPGA.

**Generated, not hand-drawn:** `gen/build.py` builds every sheet from `gen/design.py` (pin maps checked against
datasheets) and places a net label exactly on each pin end. Connectivity is exact; the visual layout is a packed
netlist style, not tidied. If you edit in KiCad, stop regenerating (or move the edits into design.py).

```
cd gen && python3 build.py && python3 verify.py && python3 check_lpf.py   # regenerate + check
kicad-cli sch erc --severity-all ../usb3-sdr.kicad_sch
```

## Verification status
| Check | Result |
|---|---|
| `gen/verify.py`: KiCad-exported netlist vs design.py | **203/203 nets identical** (no missing, merged or extra nets), 226 components |
| `gen/check_lpf.py`: gateware LPF → KiCad net → far-end **datasheet pin name** (through series resistors) | **71/71 signals land on the right pin**. Independent of design.py |
| ECP5 ball data: Lattice FPGA-SC-02033 CSV vs prjtrellis-db | Same 197 I/O balls, 0 bank mismatches, 0 clock-function mismatches. Pin names in the symbol are the official Lattice names |
| ERC | **2 violations, both expected**: J1 SSRX± "input not driven" (the host drives them through the cable) |
| Symbols vs datasheets | FT601Q (all 76 pins + EP), USB3 Micro-B, TPS62A02A, TLV75525, TPS7A20 DBV, TPS22918 (= TPS22917DBV pinout), W25Q128JVS, PHA-13LN, 74LVC1G17, G6K-2 vs HFD4/5-SR wiring |
| Footprints vs datasheets | FT601 QFN-76 EP 5.81×6.31 (DS Fig 8.3), AD9649 CP-32-11 EP 3.50 sq, BGA-256 14×14 0.8 mm, ADT4-6T+ CD637 |

## Open items
1. ~~ECP5 power/config unit~~ **Done** from Lattice FPGA-SC-02033 (`gen/ecp5_bg256.json`, extracted from the CSV).
   Configuration follows the Lattice ECP5 Versa board (FPGA-EB-02021 Fig. 12): CFG[2:0] = 010 (Master SPI) via 1k,
   10k pull-ups on PROGRAMN/INITN/DONE, 50 Ω series CCLK at the FPGA, JTAG powered from VCCIO8 (3.3 V).
   The 4.7k TCK pull-down is common Lattice practice, **not** taken from the Versa sheet.
2. J1 footprint is the stock Connfly DS1104-01, but the BOM lists Amphenol GSB343133HR. Pick one and match them.
3. GDT footprint is a 1812 placeholder until a GDT part is chosen.
4. FT601 data/control ball assignment follows the gateware LPF pool and is provisional; reorder at layout.

# PCB (stage 1: setup, placement, fan-out; not routed)
`gen/pcb_build.py` writes `usb3-sdr.kicad_pcb` from the exported netlist (footprints keep their symbol links, so
KiCad's *Update PCB from Schematic* works). It regenerates the placement from scratch, so after hand edits start, stop running it.

| Item | Setting |
|---|---|
| Board | 100 × 60 mm, 4 × M2.5 holes, 1.6 mm |
| Stackup | JLC04161H-7628: 35 µm / 0.2104 mm 7628 (εr 4.4) / 15 µm / 1.065 mm core / 15 µm / 0.2104 mm / 35 µm |
| Planes | In1 = solid GND. In2 = 1V1 under the BGA, 1V8_A under the ADC, 3V3_D across the digital half |
| Net classes | RF50 0.35 mm (confirm in the JLC calculator), USB90 diff 0.26 / 0.15, LVDS100 diff 0.20 / 0.15, PWR 0.4 mm, default 0.15 / 0.127 |
| Vias | 0.2 mm drill / 0.45 mm pad (JLC multilayer minimum, no surcharge) |
| BGA fan-out | 156 dog-bone vias: every power/GND ball, and signal balls in rings ≥ 2. Rings 0-1 escape on F.Cu between balls (needs ~0.1 mm neck-down) |

Checks (`kicad-cli pcb drc --schematic-parity`): **0 parity issues** (227 footprints = netlist, + 4 board-only holes).
Errors: only the 10 SMA edge-launch pads meeting Edge.Cuts (inherent to edge launch). Expected while unrouted: 499
unconnected, 112 dangling fan-out vias, 1V8_A plane isolated. Silkscreen overlap warnings are cosmetic (packed reference designators).

## PCB open items
1. **RF chain needs hand placement** in a straight line (SMA → GDT/clamp → K1/pad → LPF1 → notch → K2/LNA → LPF2 → T1 → ADC)
   with 50 Ω lines and the shield-can outlines. The generator only clusters it.
2. SMA edge position: set at the F.Fab flange line (+2.54 mm). **Check against the Amphenol 132289 drawing.**
3. FPGA 100 nF decoupling is on top around the BGA; moving it under the BGA (B.Cu, between vias) is better.
4. FT601 data balls: reorder to match the FT601 pin order at routing, then update the LPF + design.py and rerun verify/check_lpf.
5. 2V5 and 1V8_D BGA vias (VCCAUX, VCCIO7) need B.Cu feeds; the In2 split only covers 1V1 / 3V3_D / 1V8_A.

# PCB stage 2: scripted critical layout (gen/rf_layout.py), ready for DeepPCB
`gen/make_all.sh` runs everything: schematic → verify → check_lpf → ERC → netlist → PCB → DRC.

**RF chain**, a serpentine in the left third of the board (rows at y = 13 / 30 / 41 mm):
- Row A (→): SMA → GDT (Bourns 2038) → BAV99 clamp → K1 (bypass on NC above, 20 dB π-pad on NO below) → LPF1 → FM notch.
- Row B (←): K2 (bypass on NC below, LNA loop on NO above: DC block → PHA-13LN+ → choke/DC block → 3 dB pad) → LPF2.
- Row C (→): ADT4-6T+ → 200 Ω termination → 33 Ω → 10 pF kickback caps → AD9649 VIN±.
- Series parts sit in line, tank caps directly above their inductors, every shunt part has its own GND via to In1.
  Relays are rotated so COM3/COM6 sit in line with the row. All of it is locked.
**USB3 SuperSpeed**: FT601 → J1, one vertical jog per line (topmost line first, so nothing crosses), TX AC caps
on the lines, 0.2 mm width beside the 0.4 mm-pitch QFN. Locked.

Status: DRC errors only the inherent SMA edge items; schematic parity 0; every scripted net complete; 479 airwires left.
In1/In2 are marked as power layers, so signals stay on F.Cu/B.Cu. USB 2 pair renamed USB_D_P/N so diff-pair detection works.

**DeepPCB**: upload `deeppcb/usb3-sdr_for_deeppcb.zip` (or the two files) at app.deeppcb.ai (the KiCad plugin needs KiCad 10).
Check on return: (1) locked RF/USB tracks unchanged, (2) nothing routed on In1/In2, (3) USB90/LVDS100 pairs coupled,
(4) rerun `kicad-cli pcb drc --schematic-parity`. Their docs don't say whether locked tracks are honoured, so
diff the returned board against this one before accepting.
