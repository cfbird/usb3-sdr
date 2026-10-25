# Brief for AGY: bus timing budgets for routing (usb3-sdr, 2026-10-24)

Claude is about to route the two FPGA buses (assignment = notes/pinswap/agy_assignment.json for FT601, Alt-A for ADC,
already applied). We need routing constraints derived from datasheet timing, and a check to run on the result.

1. FT601 245 synchronous FIFO, 100 MHz, FT601 drives CLK (U11 pin 58 -> FPGA J16, PCLKT2_1, global clock).
   Gateware: rtl/ft601_245.v (inputs captured in IO registers, outputs from IO registers; write side judged one cycle late).
   Datasheet: refs/DS_FT600Q-FT601Q-IC-Datasheet.pdf (245 mode timing table: T1..T9, setup/hold/clock-to-out).
   ECP5 IO register timing: use nextpnr's numbers if you can't find a Lattice figure; say which.
   Derive: (a) max allowed trace length difference between FT_CLK and any data/control line, (b) max absolute length,
   (c) whether the existing open item "FT601 output hold, T4 = 4.8 ns, PLL phase" (STATUS.md) is a real problem and what
   PLL phase / IO delay would fix it. Assume ~6 ps/mm on F.Cu microstrip and ~6.5-7 ps/mm on B.Cu (state your numbers).
2. AD9649 CMOS outputs, 80 MSPS, DCO (U8 pin 22 -> R40 22 ohm -> FPGA J1, PCLKT7_1), data through R26..R39 (22 ohm),
   1.8 V LVCMOS18 in bank 7. Datasheet refs/datasheets/AD9649_RevB.pdf (tPD, tDCO, tSKEW, output rise/fall, load).
   Derive: max DCO-to-data length skew, and whether the 22 ohm series resistors + ~30-50 mm traces need anything else.
3. Give a runnable `notes/pinswap/agy_timing_check.py` that, given per-net routed lengths in a JSON file
   ({"net": length_mm, ...}, which Claude will generate from the board), reports pass/fail per constraint.

Write results to notes/pinswap/agy_timing.md. VERIFIED / DISPUTED / UNVERIFIABLE on any datasheet number you use, with page
and table. Do not edit kicad/ or gateware/.
