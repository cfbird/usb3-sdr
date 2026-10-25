# usb3-sdr gateware (Rev A skeleton)

Target: Lattice ECP5 LFE5U-25F-6BG256C (the 45F is a drop-in, `make DEVICE=45k`). Open toolchain only.

```
AD9649 14b @ 80 MSPS ─► IO regs ─► DDC (NCO/mixer ─► CIC5 /16 ─► HB23 /2 ─► CFIR59 /2) ─► 1.25 MSPS IQ ─┐
                              └──────────────── raw mode: 2 samples/word, 160 MB/s ────────────────────┤
                                                                       async FIFO 4K×32 (80 → 100 MHz) ─► FT601 245 master ─► USB 3
internal OSCG ~2.4 MHz ─► boot_seq: ADC standby → LMK61E2 → 80 MHz (I²C) → ADC 1.8 V CMOS/2's comp → run
```

## Build / test
Tools come from a project-local venv (`../.venv`, pip: `yowasp-yosys yowasp-nextpnr-ecp5`); g++ for CXXRTL.

```
make            # gen coefficients, synth, place & route, bitstream -> build/usb3sdr.bit
make sim        # all three CXXRTL testbenches
```

| File | Purpose |
|---|---|
| rtl/top.v | Pins, clock domains, control registers and CDC, raw/DDC mux, host protocol (documented in its header) |
| rtl/boot_seq.v | Op-table sequencer: AD9649 SPI + LMK61E2 I²C power-up programming |
| rtl/nco.v, cic_decim.v, fir_decim.v, ddc.v | DDC chain |
| rtl/async_fifo.v | Gray-pointer dual-clock FIFO, FWFT, BRAM output register |
| rtl/ft601_245.v | FT601 245-sync master with IO-register inputs and replay buffer |
| constraints/usb3sdr.lpf | Ball map (from notes/pinplan_power.md) and IO standards |
| tools/gen_coeffs.py | NCO ROM, halfband and CIC-compensating FIR (quantized responses printed) |
| sim/ | CXXRTL testbenches + analysis |
| ../host/sdr_ctl.py | Minimal D3XX host control/capture (**untested, no hardware**) |

## Verified so far (simulation + P&R only, no hardware)
| Check | Result |
|---|---|
| DDC two-tone (7.1 MHz NCO, tones at +100 kHz / +900 kHz, 0.45 FS each) | Tone at +100.02 kHz, −13.22 dBFS (−12.96 expected; see AGY review). +900 kHz alias rejected **94.9 dB**. DC spur −105 dBFS (SFDR 92.2 dBc). Output 1.2499 MSPS |
| Filter design (quantized 18-bit) | Passband ripple 0.001 dB to 0.5 MHz, HB stopband −99 dB, CFIR stopband −87 dB |
| FT601 bus model, random TXE_N (≥ 2-cycle full pulses), host commands | 400k words at 320 MB/s (source-limited), **0 order errors, 0 bus contention**, all host words received |
| Same with 1-cycle TXE_N pulses | Adjacent-word swaps occur and are **flagged** by `order_err` (see open items) |
| Boot sequence decode | All 11 SPI/I²C transactions bit-exact, I²C ACKed, done in 35.7 ms |
| Place & route, LFE5U-25F, 10 runs | Every run passes. ADC domain 100.6–108.5 MHz (needs 80), FT domain **100.1–119.0 MHz** (needs 100), so the FT margin can be as thin as 0.1 %. Results vary run to run even with a fixed seed. 11 % LUT, 13/56 BRAM, 6/28 MULT. Internal paths only: board-level IO timing is open item 1 |

Bugs found and fixed by the sims and timing reports: an out-of-bounds coefficient read; a DC spur from floor
truncation (round-to-nearest at all four truncation points); an unsigned-concatenation sign bug in CIC rounding;
BRAM clock-to-out on three paths (FIFO, FIR, NCO); and the FT601 input timing (below).

## Open items
1. **FT601 output hold, T4 = 4.8 ns (DS Table 4.2).** Outputs are fabric registers today. Hold depends on
   clock insertion + clock-to-out and is not modelled by nextpnr. Fix: move WR_N/RD_N/OE_N/DATA into IO output
   registers, and run them from an EHXPLLL copy of FT CLK with a tunable phase. Verify on the bench.
2. **FT601 TXE_N 1-cycle pulses.** With IO-registered inputs (required by the T1 = 3.0 ns setup window)
   the master learns of a rejected word one cycle late. A 1-cycle full pulse can reorder two words. It is
   detected (`order_err`, reported in the status word) but not prevented. Check on hardware whether the FT601
   ever produces such pulses.
3. **LMK61E2 program** uses the reset-default loop filter (integer mode, doubler on), changing only N (48)
   and OUTDIV (60). Values were computed from SNAS674C. Confirm with TICS Pro, and optionally write the EEPROM once.
4. **No framing** in the sample stream (status only while streaming is off). Add a header or sequence word
   before multi-DDC.
5. Multi-DDC: 6 multipliers per DDC means the 25F fits 4 DDCs. Parameterise ddc.v and interleave the outputs.
6. Raw mode at 160 MB/s has ~100 µs of FIFO buffering (AW = 12). Raise AW to 14 (16K words, 32 BRAM) if
   host stalls drop samples.
7. 10 MHz reference discipline (ref10m pin): not implemented.
8. FT-domain margin is thin on some placements (worst seen 100.1 MHz). The next step is pipelining the replay-buffer judge, or a PLL-generated FT clock with IO output registers (item 1).
