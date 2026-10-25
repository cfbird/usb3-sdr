# Brief for AGY: FPGA bus ball assignment + BGA escape capacity (usb3-sdr, 2026-10-23)

Written by Claude. Read this file and `notes/pinswap/data.json` first. Write results only under `notes/pinswap/`
(do not edit `kicad/` or `gateware/`; Claude will apply and verify your result there).
Answer each claim in §4 with VERIFIED / DISPUTED / UNVERIFIABLE per ~/collab/PROTOCOL.md, with runnable checks.

## 1. Where the board is

4-layer board, 100 x 60 mm. Stack: F.Cu (signal) / In1.Cu (GND plane, whole board) / In2.Cu (split power planes:
1V1 under the FPGA core region x155.5-170.5 y116.5-131.5, 3V3_D x152-199.7 y100.3-142, 1V8_A x134-152 y108-134) / B.Cu (signal).
No signals may go on In1/In2.

Routing so far: hand-routed + locked RF chain, USB3 SS pairs, ADC analog input, buck converters; then two DeepPCB
autorouter runs (the second with existing copper protected). **80 connections remain unrouted**, and they are almost
all the two buses into the FPGA:
- FT601 (U11, QFN-76, 0.4 mm pitch, centre (184, 123), rotated 90 deg) <-> FPGA (U12, LFE5U-25F CABGA256, 0.8 mm pitch,
  centre (163, 124)): ~38 unrouted.
- AD9649 ADC (U8, LFCSP-32, centre (141, 141)) -> 15 series resistors R26..R40 -> FPGA bank 7: ~17 unrouted.

Claude's diagnosis (please check, §4): the ball assignment was a provisional "pool" (the LPF says so) and does not
follow the pin order of the FT601 / ADC, so the buses cross. Straight-line ratsnest of the 46 FT601<->FPGA nets has
**237 pairwise crossings**. Two signal layers cannot untangle that.

## 2. Data (`notes/pinswap/data.json`, produced by `notes/pinswap/extract.py` from the routed board)

- `fpga_balls[ball]`: `xy` (mm), `ring` (0 = outer ring), `bank`, `pio`, `special` (PCLK/GPLL/VREF/config), `net`
  (current KiCad net), `gateware_signal` (current LPF signal on that ball).
  Ball naming: letter = row along +y (A at y=118.0, T at y=130.0), number = column along +x (1 at x=157.0, 16 at x=169.0).
- `ft601_pins[pin]`: `xy`, `net`, `datasheet_name` (DATA_0..31, BE_0..3, CLK, ~TXE, ~RXF, ~WR, ~RD, ~OE, ~RESET,
  ~WAKEUP, GPIO0/1, ...).
- `adc_pins[pin]` (U8) and `adc_series_resistors[R26..R40]` with both pads: pad 1 = U8 side (`ADC_Dn_R` nets), pad 2 = FPGA
  side (`ADC_Dn` nets). Resistors are placed; the R-to-ball side is what gets re-planned.
- `bank_vccio`: 0,1,2,3,6,8 = 3.3 V, 7 = 1.8 V.

## 3. Task (AGY leads; this is the complex part)

### T1. FT601 bus assignment
Assign the 46 FT601-side nets (gateware `ft_data[0..31]`, `ft_be[0..3]`, `ft_clk`, `ft_txe_n`, `ft_rxf_n`, `ft_wr_n`,
`ft_rd_n`, `ft_oe_n`, `ft_reset_n`, `ft_wakeup_n`, plus FT_GPIO0/FT_GPIO1 currently on P13/P14) to FPGA balls.
Hard constraints:
1. Banks 2 or 3 only (VCCIO 3.3 V, the side facing U11). Usable = balls whose current net is empty/`unconnected-*` or
   is one of these 46 nets. Never use power/GND/config balls.
2. `ft_clk` on a **true** PCLK input: PCLKT2_0 (K16), PCLKT2_1 (J16), PCLKT3_0 (M16) or PCLKT3_1 (L16).
3. The gateware treats bits as names only, so any bit can go to any ball; the 245 FIFO runs at 100 MHz with the
   input/output registers in the IO cells, so skew between balls is not a constraint at this board size (say so if you
   disagree).

Objective: a ball order that makes the bus **planar** (zero crossings) between the U11 pins and the balls, **and is
escapable** from the BGA on two layers given the fan-out geometry in T3. Prefer outer rings. Minimise total length
second.

### T2. ADC bus assignment (bank 7, VCCIO 1.8 V)
Assign `adc_d[0..13]`, `adc_or`, `adc_sclk`, `adc_sdio`, `adc_csb` and `adc_dco` to bank-7 balls. `adc_dco` must stay on a
true PCLK: PCLKT7_0 (K1) or PCLKT7_1 (J1). The data lines go through R26..R40 (fixed positions; which resistor carries
which bit is fixed by the U8 side, see the `ADC_Dn_R` / `ADC_Dn` nets). Same objective: planar from the resistor pads to
the balls, escapable. Note: bank 7 is the FPGA's upper-left; the ADC is lower-left at (141,141). If moving the ADC bus to
bank 6 (lower-left, currently 3.3 V with ref10m, LMK I2C, relay/LED lines) would be clearly better, quantify it, but
treat it as a proposal: it changes a bank voltage.

### T3. BGA escape capacity (math)
Current fan-out (kicad/gen/pcb_build.py ~line 230): every ball in ring >= RINGS_DIRECT (signals) and every power ball gets
a dog-bone: 0.15 mm F.Cu track from the 0.32 mm ball pad to a via (0.45 mm pad, 0.2 mm drill) on the interstitial site
(ball +/- 0.4, +/- 0.4) pointing away from the package centre. Design rules: default track 0.15 mm, clearance 0.127 mm
(PWR class 0.4/0.15).
Claude's back-of-envelope (check it): adjacent interstitial vias are 0.8 mm apart, so the gap is 0.8 - 0.45 = 0.35 mm,
but a 0.15 mm track needs 0.15 + 2 x 0.127 = 0.404 mm. **So no B.Cu track fits between two fan-out vias**, and a
ball-to-via channel on F.Cu is also too narrow (ball (0,0) to via (0.4,0.4): 0.566 - 0.16 - 0.225 = 0.18 mm).
Questions:
a. How many signals can escape per side on F.Cu + B.Cu with the current via size, as a function of which balls are
   used? (Unused balls need no via.)
b. Same with smaller vias. Candidates: 0.40/0.20, 0.35/0.15, 0.30/0.15 mm (pad/drill), and track 0.1 mm / clearance
   0.1 mm. Claude will check which ones the fab (JLCPCB 4-layer) actually supports; do not rely on recalled fab limits,
   just give capacity as a function of via pad, track and clearance.
c. Is the 46-signal FT bus escapable from banks 2/3 on two layers under (a), and under the best option in (b)? Same for
   the 19-signal ADC bus in bank 7.

### Deliverables (in `notes/pinswap/`)
- `agy_assignment.json`: `{"<gateware signal or net>": "<ball>"}` for T1 and T2.
- `agy_pinswap.md`: method, escape analysis, verdicts for §4.
- `agy_check.py`: runnable with `python3 notes/pinswap/agy_check.py` from the repo root. Reads data.json + your
  assignment, checks constraints 1-2 for both buses, counts straight-line crossings (reproduce Claude's 237 for the
  current assignment as a sanity test), and checks escape feasibility under your model.

## 4. Claims for you to VERIFY / DISPUTE (Claude is checking its own work here)

C1. The current FT601 <-> FPGA assignment has 237 straight-line crossings (method: segment U11 pad centre to U12 ball
    centre per net, count properly intersecting pairs).
C2. Fan-out via channel arithmetic in T3 (0.35 mm gap vs 0.404 mm needed; 0.18 mm ball-to-via channel).
C3. Buck converter patch (kicad/gen/buck_patch.py), TPS62A02 at up to 2 A: SW leaves the 0.35 mm-wide SOT-563 pin on a
    0.2 mm x ~0.6 mm neck, then 0.6 mm to the inductor; VIN/GND necks 0.2 mm x ~0.45 mm then 0.4 mm. Is a 0.2 mm-wide,
    ~0.6 mm-long 1 oz (35 um) outer-layer neck acceptable at 2 A peak / ~1 A average (temperature rise, IR drop,
    fusing margin)? Show the numbers.
C4. USB 2.0 (480 Mb/s) D+/D- from U11 to the USB3 Micro-B J1 are routed as two single 0.2 mm tracks, not coupled, each
    ~10-14 mm long with 2 vias, partly on B.Cu (referenced to In2 = 3V3_D plane, which is continuous under that area),
    partly on F.Cu (referenced to In1 = GND). Is that acceptable for USB 2.0 HS? Quantify: electrical length vs
    rise time (USB 2.0 HS tr >= 500 ps), reflection from a ~60-70 ohm single-ended section, via stubs on a 1.6 mm board.
    Stack-up numbers you need: assume JLC 4-layer 1.6 mm, prepreg 0.2104 mm (7628), Er ~ 4.4, 35 um outer copper;
    state any other assumption.
C5. With In2 split into 1V1 / 3V3_D / 1V8_A islands, are there B.Cu nets that cross a split (no continuous reference)?
    You cannot see copper geometry from data.json; instead tell Claude exactly what check to run, and Claude will run it.
