# Brief for AGY: FT601 output IO-register fix (usb3-sdr, 2026-10-24)

From your notes/pinswap/agy_timing.md (Claude VERIFIED the problem: only the inputs use IFS1P3DX; outputs and the data
tristate enable `doe` are fabric TRELLIS_FFs, nextpnr shows doe -> ft_data[6].T at 5.17 ns, and the current build closes
ft_clk at only 100.56 MHz on seed 4).

Implement your fix in the gateware:
1. In gateware/rtl/ft601_245.v (and gateware/rtl/top.v if the clocking lives there): put ft_data/ft_be outputs, wr_n, rd_n,
   oe_n and the data/BE tristate enable into ECP5 IO registers (OFS1P3DX for data, the tristate register for the enables),
   under the same `ifdef ECP5_IOREG` scheme the inputs use, keeping a behavioral path for the CXXRTL sims.
2. Clock the output registers from an EHXPLLL output phase-shifted per your analysis (+135 deg, window +105..+160 deg,
   or the single-clock +115 deg variant if you judge it cleaner); inputs stay on the 0 deg clock. State which and why.
   Watch: the write side is judged one cycle late with the replay buffer (round-4 review), so check the one-cycle
   relationships still hold with the shifted output clock.
3. Verify: `cd gateware && make && make sim-ft` (sim must still PASS, including the 1-cycle TXE_N reorder detection), and
   report nextpnr Fmax for ft_clk / adc_dco over seeds 1-4 (`--seed N`, see the Makefile; run nextpnr with the build
   dir as scratch: the yowasp tools only see files under the current directory).
4. Also re-derive the FT601 T1-T4 budget with the final implementation (numbers in a table).

Allowed edits: gateware/rtl/*.v, gateware/sim/*, gateware/Makefile if needed, notes/pinswap/agy_ft601_ioreg.md (write-up).
Do NOT edit gateware/constraints/usb3sdr.lpf (just re-mapped and verified), anything under kicad/, or boot_seq.v's ROM.
Claude will review the diff, rerun the build/sims and nextpnr seeds, and check the timing write-up.
