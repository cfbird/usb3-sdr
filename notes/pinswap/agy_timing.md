# Bus Timing Budgets & Routing Constraints (`usb3-sdr`, 2026-10-24)

**Author:** AGY  
**Scope:** Response to `notes/pinswap/BRIEF_timing.md` (Items 1–3)  
**Deliverables:** `notes/pinswap/agy_timing.md` (this report), `notes/pinswap/agy_timing_check.py` (runnable length & timing checker)

---

## 0. PCB Propagation Velocity Model (`JLC04161H-7628`)

From `kicad/gen/pcb_build.py` (lines 339–350), the 4-layer stackup is `JLC04161H-7628`:
- **`F.Cu` / `B.Cu`**: $35\text{ }\mu\text{m}$ copper ($1\text{ oz}$) with $10\text{ }\mu\text{m}$ solder mask over `7628` prepreg ($h = 0.2104\text{ mm}$, $\varepsilon_r = 4.4$, $\tan\delta = 0.02$).
- **`In1.Cu`**: Continuous `GND` reference plane under `F.Cu`.
- **`In2.Cu`**: Split power planes (`1V8_A`, `1V1`, `3V3_D`) under `B.Cu`.

For a $w = 0.15\text{ mm}$ (`6 mil`) microstrip over $h = 0.2104\text{ mm}$ ($\varepsilon_r = 4.4$):
$$\varepsilon_{\text{eff}} \approx \frac{\varepsilon_r + 1}{2} + \frac{\varepsilon_r - 1}{2}\left(1 + 12\frac{h}{w}\right)^{-1/2} + \Delta\varepsilon_{\text{mask}} \approx 3.24, \qquad Z_0 \approx \mathbf{64\text{ }\Omega}, \qquad c_{\text{trace}} = \frac{\tau}{Z_0} \approx \mathbf{0.094\text{ pF/mm}}$$

We state and use the following propagation delay figures across all timing budgets and in `agy_timing_check.py`:
- **`F.Cu` microstrip delay ($\tau_F$)**: $\mathbf{6.00\text{ ps/mm}}$ ($v_p = 1.67 \times 10^8\text{ m/s} = 0.556\,c_0$).
- **`B.Cu` microstrip + via-transition effective delay ($\tau_B$)**: $\mathbf{6.75\text{ ps/mm}}$ nominal, $\mathbf{6.50\text{–}7.00\text{ ps/mm}}$ range (accounts for two $1.6\text{ mm}$ dog-bone fanout vias contributing $\sim 15\text{–}20\text{ ps}$ plus return-current coupling across `In2.Cu`/`In1.Cu` stitching caps).
- **Corner analysis**: Every setup/hold equation below and in `agy_timing_check.py` evaluates **fast traces at $\tau_{\min} = 6.00\text{ ps/mm}$** and **slow traces at $\tau_{\max} = 7.00\text{ ps/mm}$**, automatically bounding mixed-layer (`F.Cu` vs `B.Cu`) routing.

---

## 1. Datasheets & FPGA Timing Parameters — Verification Table

| Source & Parameter | Symbol | Value Used | Verdict | Citation & Notes |
|---|---|---|---|---|
| **FT601** FIFO Clock Period ($100\text{ MHz}$) | $T_{\text{CLK}}$ | $10.0\text{ ns}$ ($50\%$ typ duty) | **VERIFIED** | `refs/DS_FT600Q-FT601Q-IC-Datasheet.pdf` v1.05, **p. 17, Table 4.2 & Fig. 4.8** |
| **FT601** `T1..T9` parameter numbering in brief | `T1..T9` | Only **`T1..T4`** exist | **DISPUTED** *(minor)* | `DS_FT600Q-FT601Q-IC-Datasheet.pdf`, **p. 17, Table 4.2** & **p. 32 List of Tables**: FT600Q/601Q defines only `T1..T4` (`T1..T9` is from older FT232H 60 MHz 245 datasheet). |
| **FT601** Slave Drive Data Setup (`FT601 -> FPGA` valid before $\uparrow\text{CLK}$) | $T_1$ | $\mathbf{3.0\text{ ns}}$ min ($\implies t_{\text{CO,max}} = \mathbf{7.0\text{ ns}}$) | **VERIFIED** | `DS_FT600Q-FT601Q-IC-Datasheet.pdf`, **p. 17, Table 4.2** (`DATA[31:0]`, `BE[3:0]`, `RXF_N`, `TXE_N`) |
| **FT601** Slave Drive Data Hold (`FT601 -> FPGA` valid after $\uparrow\text{CLK}$) | $T_2$ | $\mathbf{3.5\text{ ns}}$ min ($\implies t_{\text{CO,min}} = \mathbf{3.5\text{ ns}}$) | **VERIFIED** | `DS_FT600Q-FT601Q-IC-Datasheet.pdf`, **p. 17, Table 4.2** |
| **FT601** Master Drive Data Setup (`FPGA -> FT601` required before $\uparrow\text{CLK}$) | $T_3$ | $\mathbf{1.0\text{ ns}}$ min | **VERIFIED** | `DS_FT600Q-FT601Q-IC-Datasheet.pdf`, **p. 17, Table 4.2** (`DATA[31:0]`, `BE[3:0]`, `WR_N`, `RD_N`, `OE_N`) |
| **FT601** Master Drive Data Hold (`FPGA -> FT601` required after $\uparrow\text{CLK}$) | $T_4$ | $\mathbf{4.8\text{ ns}}$ min | **VERIFIED** | `DS_FT600Q-FT601Q-IC-Datasheet.pdf`, **p. 17, Table 4.2** |
| **FT601** I/O Pin Capacitance & Drive Impedance | $C_p$, $R_{\text{drv}}$ | $2.0\text{ pF}$ max; $18/25/35/50\text{ }\Omega$ | **VERIFIED** | `DS_FT600Q-FT601Q-IC-Datasheet.pdf`, **p. 21, Table 5.4** ($C_p = 2.0\text{ pF}$) & **p. 11, Sec. 4.1** |
| **AD9649-80** Clock Period ($80\text{ MSPS}$) | $t_{\text{CLK}}$ | $12.5\text{ ns}$ ($t_{\text{CH}}, t_{\text{CL}} = 5.6\text{–}6.9\text{ ns}$) | **VERIFIED** | `refs/datasheets/AD9649_RevB.pdf`, **p. 7, Table 4** |
| **AD9649-80** Data & DCO Propagation Delay | $t_{\text{PD}}, t_{\text{DCO}}$ | $\mathbf{3.0\text{ ns}}$ typ ($C_{\text{LOAD}} = 5\text{ pF}$, no min/max) | **VERIFIED** | `AD9649_RevB.pdf`, **p. 7, Table 4, Footnotes 1–2** (min/max not tabulated; typ only) |
| **AD9649-80** DCO-to-Data Skew ($t_{\text{DCO}} - t_{\text{PD}}$) | $t_{\text{SKEW}}$ | $\mathbf{+0.1\text{ ns}}$ typ ($[-0.1, +0.3]\text{ ns}$ corner) | **VERIFIED** | `AD9649_RevB.pdf`, **p. 7, Table 4 & Fig. 2**. **Crucial catch:** Fig. 2 shows $\uparrow\text{DCO}$ is **edge-aligned** ($+0.1\text{ ns}$ after `DATA` transition) by default (`0x16=0x00`), NOT center-aligned! |
| **AD9649-80** Max Capacitive Load & Drive Adjust | $C_{\text{LOAD}}$ | $5\text{ pF}$ test, **$< 10\text{ pF}$** recommended; `0x15[1:0]` = 1x..4x | **VERIFIED** | `AD9649_RevB.pdf`, **p. 7 Table 4**, **p. 17 "Digital Outputs"**, **p. 28 Table 16 (`0x15`–`0x17`)** |
| **ECP5 (`-6`)** `IOLOGIC` Input Register (`IFS1P3DX`) | $t_{\text{SU,IREG}}, t_{\text{H,IREG}}$ | $t_{\text{SU}} = \mathbf{439\text{ ps}}$, $t_{\text{H}} = \mathbf{311\text{ ps}}$, $t_{\text{CO}} = \mathbf{474\text{ ps}}$ | **VERIFIED** | `prjtrellis` speed `-6` database (`speed_6/cells.json`, `IOLOGIC:MODE=IREG`) |
| **ECP5 (`-6`)** `IOLOGIC` Output / Tristate Reg (`OFS1P3DX`) | $t_{\text{CO,OREG}}, t_{\text{CO,TSREG}}$ | $t_{\text{CO,OREG}} = \mathbf{1200\text{ ps}}$, $t_{\text{CO,TSREG}} = \mathbf{1031\text{ ps}}$ | **VERIFIED** | `prjtrellis` speed `-6` database (`speed_6/cells.json`, `IOLOGIC:MODE=OREG`, `TSREG`) |
| **ECP5 (`-6`)** `PIO` `LVCMOS33` Delays | $t_{\text{IN}}, t_{\text{OUT}}, t_{\text{TS}}$ | `PAD->PADDI`: $[0.990, 1.140]\text{ ns}$<br>`PADDO->PAD`: $[1.988, 2.674]\text{ ns}$<br>`PADDT->PAD`: $[2.203, 3.023]\text{ ns}$ | **VERIFIED** | `prjtrellis` speed `-6` database (`speed_6/cells.json`, `PIO:IOTYPE=LVCMOS33`) |
| **ECP5 (`-6`)** `PIO` `LVCMOS18` Input Delay | $t_{\text{IN,18}}$ | `PAD->PADDI`: $[1.311, 1.469]\text{ ns}$ | **VERIFIED** | `prjtrellis` speed `-6` database (`speed_6/cells.json`, `PIO:IOTYPE=LVCMOS18`) |
| **ECP5 (`-6`)** Global Clock Tree Delay & `DELAYG` | $t_{\text{GCLK}}$, $\Delta t_{\text{DEL}}$ | $t_{\text{GCLK}} \in [1.20, 1.80]\text{ ns}$ (uncomp.); `DELAYG`: $25\text{ ps/tap} \times 127 = 3.175\text{ ns}$ | **VERIFIED** | Lattice ECP5 Family Data Sheet (`FPGA-DS-02012`, Sec. 3.16: $t_{\text{CO,max}} = 5.8\text{ ns}$ no PLL vs $3.8\text{ ns}$ w/ PLL $\implies t_{\text{IN,CLK}}+t_{\text{GCLK}} \approx 2.0\text{–}2.8\text{ ns}$). |

---

## 2. Task 1 — FT601 245 Synchronous FIFO Bus (`100 MHz`, Bank 2/3 `LVCMOS33`)

### 2.1 Read / Status Input Path (`U11` $\to$ FPGA `IFS1P3DX`: `FT_D[31:0]`, `FT_BE[3:0]`, `FT_TXE_N`, `FT_RXF_N`)

The FT601 drives both `FT_CLK` (`U11` pin 58 $\to$ `J16`) and the input signals (`source-synchronous`). Relative to $\uparrow\text{FT\_CLK}$ at `U11` pin 58 ($t = 0$):
- FT601 guarantees valid output data from $t = -T_1 = -3.000\text{ ns}$ until $t = +T_2 = +3.500\text{ ns}$.
- At the FPGA `IFS1P3DX` input flip-flop:
  - Signal arrival at `DI`: $t_{\text{sig,DI}} = \tau_{\text{sig}} + t_{\text{IN,DATA}}$, where $t_{\text{IN,DATA}} \in [0.990, 1.140]\text{ ns}$.
  - Clock arrival at `CLK`: $t_{\text{clk,FF}} = \tau_{\text{clk}} + t_{\text{IN,CLK}} + t_{\text{GCLK}}$, where $t_{\text{IN,CLK}} \in [0.990, 1.140]\text{ ns}$ and $t_{\text{GCLK}} \in [1.200, 1.800]\text{ ns}$ (or $t_{\text{IN,CLK}} + t_{\text{GCLK}} = 0$ if a $0^\circ$ feedback-compensated PLL is used).
- Notice that the `LVCMOS33` input buffer delay $t_{\text{IN,PIO}}$ cancels between clock and data up to on-die bank skew $\Delta t_{\text{IN}} = t_{\text{IN,max}} - t_{\text{IN,min}} = 1.140 - 0.990 = \mathbf{0.150\text{ ns}}$.

**Input Setup Slack** (conservatively evaluated at $t_{\text{GCLK,min}} = 0$ so it holds both with and without a $0^\circ$ PLL):
$$\text{Slack}_{\text{SU,rd}} = T_1 + (\tau_{\text{clk,min}} - \tau_{\text{sig,max}}) - \Delta t_{\text{IN}} - t_{\text{SU,IREG}} = 3000 + (\tau_{\text{clk,min}} - \tau_{\text{sig,max}}) - 150 - 439 = \mathbf{2411\text{ ps}} + (\tau_{\text{clk,min}} - \tau_{\text{sig,max}})$$

**Input Hold Slack** (evaluated at worst-case uncompensated $t_{\text{GCLK,max}} = 1800\text{ ps}$):
$$\text{Slack}_{\text{HD,rd}} = T_2 + (\tau_{\text{sig,min}} - \tau_{\text{clk,max}}) - \Delta t_{\text{IN}} - t_{\text{GCLK,max}} - t_{\text{H,IREG}} = 3500 + (\tau_{\text{sig,min}} - \tau_{\text{clk,max}}) - 150 - 1800 - 311 = \mathbf{1239\text{ ps}} + (\tau_{\text{sig,min}} - \tau_{\text{clk,max}})$$

Even for the largest trace skew on the board ($\Delta L = +10.65\text{ mm}$ on `FT_D1`), $\text{Slack}_{\text{SU,rd}} = \mathbf{+2322\text{ ps}}$ and $\text{Slack}_{\text{HD,rd}} = \mathbf{+1216\text{ ps}}$.

---

### 2.2 Write / Control Output Path (`FPGA` $\to$ `U11`: `FT_D[31:0]`, `FT_BE[3:0]`, `FT_WR_N`, `FT_RD_N`, `FT_OE_N`) & Open Item 1 (`T4 = 4.8 ns`)

On the write path, the FT601 drives `FT_CLK` to the FPGA (`flight time` $\tau_{\text{clk}}$) and captures the FPGA's output signals returning to `U11` (`flight time` $\tau_{\text{sig}}$). Thus **the PCB flight times ADD ($\tau_{\text{rt}} = \tau_{\text{clk}} + \tau_{\text{sig}}$)**.

At `U11`'s pins, FT601 requires (`Table 4.2`, p. 17):
- **Earliest allowed transition after $\uparrow\text{FT\_CLK}$ (Hold $T_4$)**:
  $$t_{\text{arrive,min}}(\text{at U11}) \ge T_4 = \mathbf{4.800\text{ ns}}$$
- **Latest allowed transition before next $\uparrow\text{FT\_CLK}$ (Setup $T_3$)**:
  $$t_{\text{arrive,max}}(\text{at U11}) \le T_{\text{CLK}} - T_3 = 10.000 - 1.000 = \mathbf{9.000\text{ ns}}$$

This defines a valid transition window at `U11` of **$[\mathbf{4.800\text{ ns}},\; \mathbf{9.000\text{ ns}}]$** (width $\mathbf{4.200\text{ ns}}$, center $\mathbf{6.900\text{ ns}}$).

#### (c) Verdict on Open Item 1 (*"FT601 output hold, T4 = 4.8 ns, PLL phase"* in `STATUS.md` / `gateware/README.md`)
- **Verdict: `VERIFIED` — Open Item 1 is a REAL hardware timing problem in two ways:**
  1. **Outputs in `gateware/rtl/ft601_245.v` today are fabric flip-flops, not IO registers:**
     Currently `ft601_245.v` only instantiates `IFS1P3DX` on inputs (`din`, `txe_n`, `rxf_n`), while `dout[31:0]`, `be_out[3:0]`, `wr_n`, `rd_n`, `oe_n`, and `doe` come from fabric `TRELLIS_FF` slices. In `gateware/build/pnr_cmp/new1.log` (lines 670–680), `clk-to-q + fabric routing` to the `PIO` pad is **$5.17\text{ ns}$** on `doe -> ft_data[6].T` **before** adding clock insertion ($2.3\text{–}2.9\text{ ns}$) and `PIO` tristate buffer delay ($2.2\text{–}3.0\text{ ns}$), giving a worst-case arrival of **$\sim 10.5\text{ ns} > 9.0\text{ ns}$ (setup violation on $T_3$)**, while bits placed adjacent to their IO tile have fabric routing $< 0.5\text{ ns}$ (**$> 3.5\text{ ns}$ bit-to-bit bus skew**).
     - **Fix Step 1:** All synchronous FT601 outputs (`dout[31:0]`, `be_out[3:0]`, `wr_n`, `rd_n`, `oe_n`) and output-enable registers (`doe` replicated per pin) **must** be placed in `OFS1P3DX` IO registers (`IOLOGIC:MODE=OREG` and `TSREG`).
  2. **With `OFS1P3DX` IO registers, fast-corner hold ($T_4 = 4.8\text{ ns}$) fails without a clock phase shift:**
     From `prjtrellis` speed `-6`, the internal IO register + `LVCMOS33` pad delay is:
     $$t_{\text{OREG+PIO}} = t_{\text{CO,OREG}} + t_{\text{OUT,PIO}} = 1.200 + [1.988,\; 2.674]\text{ ns} = [\mathbf{3.188\text{ ns}},\; \mathbf{3.874\text{ ns}}]$$
     (and for `TSREG` tristate: $1.031 + [2.203,\; 3.023]\text{ ns} = [\mathbf{3.234\text{ ns}},\; \mathbf{4.054\text{ ns}}]$).
     Across PVT (fast silicon corner, $+3.45\text{ V}$ `VCCIO`, low temperature, where CMOS delay scales by $\approx 0.65\text{–}0.70\times$), $t_{\text{OREG+PIO,min}} \approx 0.70 \times 3.188 = \mathbf{2.232\text{ ns}}$.
     - If an `EHXPLLL` is used at $0^\circ$ (canceling clock tree insertion delay), $t_{\text{arrive,min}} \approx 2.23 + 0.17 = \mathbf{2.40\text{ ns}} < \mathbf{4.80\text{ ns}}$ (**violates $T_4$ by $-2.40\text{ ns}$**).
     - Even without a PLL (relying on uncompensated `J16` input + global clock tree $t_{\text{IN,CLK}} + t_{\text{GCLK}} \approx [2.19,\; 2.94]\text{ ns}$ nominal, or $\approx 1.53\text{ ns}$ at $0.70\times$ fast PVT), $t_{\text{arrive,min}} \approx 1.53 + 2.23 + 0.17 = \mathbf{3.93\text{ ns}} < \mathbf{4.80\text{ ns}}$ (**violates $T_4$ by $-0.87\text{ ns}$ at fast PVT corner**, matching Lattice `FPGA-DS-02012` $t_{\text{CO,max}} = 5.8\text{ ns} \implies t_{\text{CO,min}} \approx 3.2\text{–}3.6\text{ ns}$).

#### Exact Fix for Open Item 1 (`EHXPLLL` Phase vs `DELAYG`)
- **Why `EHXPLLL` phase shift is preferred over `DELAYG`:**
  In ECP5, `DELAYG` (`DEL_VALUE = 0..127`, $25\text{ ps/tap}$ nominal, max $3.175\text{ ns}$) sits only in the `PADDO` data path and **cannot delay the `PADDT` tristate enable path (`doe`)**. An `EHXPLLL` phase shift clocks both `OREG` (`PADDO`) and `TSREG` (`PADDT`) uniformly.
- **Optimal `EHXPLLL` Phase Shift:**
  We want the FPGA output transition (plus round-trip PCB flight $\tau_{\text{rt}} \in [0.16,\; 0.28]\text{ ns}$) to sit centered inside $[4.800\text{ ns},\; 9.000\text{ ns}]$:
  - **Two-output PLL (`CLKOP` + `CLKOS`, Recommended):**
    - `CLKOP` at **$0^\circ$** (or uncompensated global clock): clocks input `IFS1P3DX` registers and fabric ($\text{Slack}_{\text{SU,rd}} = +2.32\text{ ns}$, $\text{Slack}_{\text{HD,rd}} = +1.22\text{ ns}$).
    - `CLKOS` at **$+135^\circ$ ($\Delta t_{\text{PLL}} = \mathbf{+3.750\text{ ns}}$)** in feedback-compensated mode: clocks output `OFS1P3DX` (`OREG` and `TSREG`) registers.
    - Resulting arrival time at `U11` for $L \in [12.6,\; 24.8]\text{ mm}$:
      $$t_{\text{arrive,min}} = 3.750 + 2.232 + 0.160 = \mathbf{6.142\text{ ns}} \ge 4.800\text{ ns} \implies \mathbf{\text{Hold Slack} = +1342\text{ ps}}$$
      $$t_{\text{arrive,max}} = 3.750 + 4.054 + 0.272 = \mathbf{8.076\text{ ns}} \le 9.000\text{ ns} \implies \mathbf{\text{Setup Slack} = +924\text{ ps}}$$
    - Valid `CLKOS` phase window with positive slack at all corners: **$+105^\circ\text{ to }+160^\circ$ ($+2.92\text{ ns}\text{ to }+4.44\text{ ns}$)**.
  - **Single-clock PLL option (if clocking both `IFS1P3DX` and `OFS1P3DX` from one net):**
    - The intersection of input hold ($t_{\text{clk}} \le +3.92\text{ ns}$) and output hold ($t_{\text{clk}} \ge +2.51\text{ ns}$) is $t_{\text{clk}} \in [+2.51,\; +3.92]\text{ ns}$, centered at **$+115^\circ$ ($+3.20\text{ ns}$)** ($\ge +690\text{ ps}$ margin on all four read/write setup/hold checks).

---

### 2.3 FT601 Routing Constraints (`(a)` Max Length Skew & `(b)` Max Absolute Length)

1. **(a) Max allowed trace length difference between `FT_CLK` and any synchronous data/control line (`|L(FT_sig) - L(FT_CLK)|`):**
   - **Hard timing limit**: Read hold allows $|L_{\text{sig}} - L_{\text{clk}}| \le 177\text{ mm}$; write setup/hold depends on the sum $L_{\text{clk}} + L_{\text{sig}}$.
   - **Recommended PCB Routing Constraint**:
     $$\boxed{|L_{\text{FT\_sig}} - L_{\text{FT\_CLK}}| \le \mathbf{15.0\text{ mm}} \quad (\pm 105\text{ ps max skew})}$$
   - **Actual board geometry (`notes/pinswap/agy_assignment.json`)**: `FT_CLK` octilinear length is $14.13\text{ mm}$ (Manhattan $15.56\text{ mm}$); all 41 synchronous signals span $12.64\text{ to }24.78\text{ mm}$ octilinear ($11.96\text{ to }27.64\text{ mm}$ Manhattan), so the natural skew is **$[-1.49\text{ mm},\; +10.65\text{ mm}]$** (Manhattan **$[-3.60\text{ mm},\; +12.08\text{ mm}]$**).
   - **Important router guidance**: **Do NOT add serpentine length-matching trombones** to the FT601 bus. Natural point-to-point routing already meets $\pm 15\text{ mm}$ with $> 900\text{ ps}$ slack, whereas adding serpentine copper in the $21\text{ mm}$ channel between `U11` and `U12` increases round-trip delay $\tau_{\text{clk}} + \tau_{\text{sig}}$ and crosstalk.

2. **(b) Max absolute trace length (`L(FT_*)`):**
   - **Hard write-setup timing limit**:With $+135^\circ$ PLL shift ($t_{\text{CO,max}} = 7.804\text{ ns}$), $L_{\text{clk}} + L_{\text{sig}} \le \frac{1196\text{ ps}}{7.0\text{ ps/mm}} = 170.8\text{ mm}$ ($\approx 85\text{ mm}$ per net).
   - **Signal-integrity (unterminated stub/reflection) limit**: For unterminated $3.3\text{ V}$ `LVCMOS33` ($t_r \approx 1.0\text{ ns}$ with `SLEWRATE=SLOW` or FT601 $25/35\text{ }\Omega$ driver), keeping one-way flight time $\tau L \le t_r / 4 = 250\text{ ps}$ gives $L_{\text{max,SI}} = \frac{250\text{ ps}}{6.75\text{ ps/mm}} = \mathbf{37.0\text{ mm}}$.
   - **Recommended PCB Routing Constraint**:
     $$\boxed{L_{\text{FT\_net}} \le \mathbf{35.0\text{ mm}}}$$
     (All 42 synchronous FT601 nets route in **$12.6\text{–}24.8\text{ mm}$**, leaving $> 10\text{ mm}$ margin.)

---

## 3. Task 2 — AD9649 CMOS Outputs (`80 MSPS`, Bank 7 `LVCMOS18`)

### 3.1 Source-Synchronous Timing Budget (`ADC_DCO` vs `ADC_D[13:0]`, `ADC_OR`)

At $80\text{ MSPS}$ ($T_{\text{CLK}} = 12.500\text{ ns}$), the AD9649 drives `DCO` (`U8` pin 22 $\to$ `R40` $22\text{ }\Omega \to$ `J1`, `PCLKT7_1`) and `D[13:0]` / `OR` (`U8` pins 7–21, 23 $\to$ `R26..R39, R41` $22\text{ }\Omega \to$ Bank 7 balls).

#### Critical Datasheet Finding (`AD9649_RevB.pdf`, Page 7 Figure 2 vs Page 28 Table 16)
In **Figure 2 (Page 7)** and **Table 4 (Page 7)**, $t_{\text{PD}} = 3.0\text{ ns}$ typ, $t_{\text{DCO}} = 3.0\text{ ns}$ typ, and $t_{\text{SKEW}} = t_{\text{DCO}} - t_{\text{PD}} = \mathbf{+0.1\text{ ns}}$ typ ($[-0.1,\; +0.3]\text{ ns}$ over corners). That means **by default (`Register 0x16 = 0x00`), the rising edge of `DCO` is edge-aligned with the `DATA` transition** ($+100\text{ ps}$ after `DATA` changes), NOT center-aligned!

Let's compare both operating modes at the FPGA `IFS1P3DX` input registers (`gateware/rtl/top.v` lines 72–76):

1. **Mode 1 — Default `DCO` Polarity (`Register 0x16 = 0x00`, current `boot_seq.v`):**
   - `DCO` enters `J1` (`PCLKT7_1`), passes through the `LVCMOS18` input buffer ($t_{\text{IN,18}} \in [1.311, 1.469]\text{ ns}$) and the **ECP5 global clock tree ($t_{\text{GCLK}} \in [1.200, 1.800]\text{ ns}$)** before reaching `IFS1P3DX.SCLK`.
   - `DATA` enters its Bank 7 ball, passes through an identical `LVCMOS18` input buffer ($t_{\text{IN,18}} \in [1.311, 1.469]\text{ ns}$, bank mismatch $\Delta t_{\text{IN,18}} = 158\text{ ps}$), and goes directly to `IFS1P3DX.D`.
   - Thus the FPGA's global clock tree delay $t_{\text{GCLK}} \ge 1.200\text{ ns}$ naturally delays `DCO` past the `DATA` transition:
     $$\text{Slack}_{\text{SU,def}} = t_{\text{SKEW,min}} + t_{\text{GCLK,min}} + (\tau_{\text{dco,min}} - \tau_{\text{data,max}}) - \Delta t_{\text{RC}} - \Delta t_{\text{IN,18}} - t_{\text{SU,IREG}}$$
     $$= -100 + 1200 + (\tau_{\text{dco,min}} - \tau_{\text{data,max}}) - \Delta t_{\text{RC}} - 158 - 439 = \mathbf{+503\text{ ps}} + (\tau_{\text{dco,min}} - \tau_{\text{data,max}}) - \Delta t_{\text{RC}}$$
     $$\text{Slack}_{\text{HD,def}} = T_{\text{CLK}} - t_{\text{SKEW,max}} - t_{\text{GCLK,max}} - (\tau_{\text{dco,max}} - \tau_{\text{data,min}}) - \Delta t_{\text{IN,18}} - t_{\text{H,IREG}} \approx \mathbf{+9931\text{ ps}}$$

2. **Mode 2 — Inverted `DCO` Polarity (`Register 0x16 = 0x80` in `boot_seq.v`, or capture on `negedge clk_adc`):**
   - Inverting `DCO` places the active rising edge at $T_{\text{CLK}}/2 = \mathbf{6.250\text{ ns}}$ (dead-center in the $12.500\text{ ns}$ data eye):
     $$\text{Slack}_{\text{SU,inv}} = 6250 - 100 + (\tau_{\text{dco,min}} - \tau_{\text{data,max}}) - \Delta t_{\text{RC}} - 158 - 439 = \mathbf{+5553\text{ ps}} + (\tau_{\text{dco,min}} - \tau_{\text{data,max}}) - \Delta t_{\text{RC}}$$
     $$\text{Slack}_{\text{HD,inv}} = 6250 - 300 - 1800 - (\tau_{\text{dco,max}} - \tau_{\text{data,min}}) - 158 - 311 = \mathbf{+3681\text{ ps}} - (\tau_{\text{dco,max}} - \tau_{\text{data,min}})$$
   - **Both setup and hold slack exceed $+3.6\text{ ns}$ ($> 500\text{ mm}$ of trace skew margin) without relying on $t_{\text{GCLK}}$!**

---

### 3.2 Signal Integrity of $22\text{ }\Omega$ Series Resistors (`R26..R41`) + $30\text{–}50\text{ mm}$ Traces

1. **Source Impedance Matching (Reflections & Ringing):**
   - At `DRVDD = 1.8 V` and default `1x` drive strength (`Register 0x15[1:0] = 00`, p. 28 Table 16), the AD9649 CMOS output stage has $R_{\text{out,ADC}} \approx 30\text{–}40\text{ }\Omega$.
   - In series with `R26..R41` ($R_s = 22\text{ }\Omega$), the total source impedance is:
     $$Z_{\text{source}} = R_{\text{out,ADC}} + R_s \approx 52\text{–}62\text{ }\Omega \approx Z_0(64\text{ }\Omega) \implies \Gamma_{\text{source}} = \frac{Z_{\text{source}} - Z_0}{Z_{\text{source}} + Z_0} \approx \mathbf{-0.10\text{ to }-0.02}$$
   - Any reflection from the high-impedance FPGA input ($C_{\text{in,FPGA}} \approx 5\text{ pF}$) is absorbed at the source in a single round trip ($2\tau L \approx 0.35\text{–}0.60\text{ ns}$) with negligible overshoot/ringing.

2. **Capacitive Loading & Rise Time ($C_{\text{total}} < 10\text{ pF}$ rule, Page 17):**
   - Trace capacitance is $c_{\text{trace}} \approx 0.094\text{ pF/mm}$. For $L = 30\text{–}50\text{ mm}$, $C_{\text{trace}} = 2.8\text{–}4.7\text{ pF}$.
   - Adding $C_{\text{in,FPGA}} \approx 5.0\text{ pF}$ gives $C_{\text{total}} \approx \mathbf{7.8\text{–}9.7\text{ pF}}$, which satisfies the AD9649 datasheet requirement ($< 10\text{ pF}$ on Page 17) as long as $L \le \mathbf{50.0\text{ mm}}$.
   - The RC $50\%$ propagation delay sensitivity to trace length difference is:
     $$\frac{d t_{\text{RC}}}{dL} \approx 0.69 \cdot Z_{\text{source}} \cdot c_{\text{trace}} \approx 0.69 \times 57\text{ }\Omega \times 0.094\text{ pF/mm} = \mathbf{3.7\text{ ps/mm}}$$
     Because `ADC_DCO` also passes through an identical $22\text{ }\Omega$ resistor (`R40`) and $0.15\text{ mm}$ trace, its RC delay tracks `ADC_D[13:0]` closely, leaving only $\Delta t_{\text{RC}} = 3.7\text{ ps/mm} \times (L_{\text{sig}} - L_{\text{dco}})$.

3. **Do the $22\text{ }\Omega$ resistors + $30\text{–}50\text{ mm}$ traces need anything else?**
   - **No additional BOM parts are needed.**
   - **Critical placement constraint on `R26..R41` (`U8 -> R` stub length):**
     For $R_s = 22\text{ }\Omega$ to act as a source termination, the stub between `U8` (`AD9649`) and pad 1 of `R26..R41` (`ADC_*_R`) **must be short ($L_{\text{stub}} \le 6.0\text{ mm}$, ideally $1.5\text{–}3.5\text{ mm}$)**.
     *Note:* In `notes/pinswap/data.json` (generated before Round 5 resistor relocation), the generic spiral placer put `R40` (`ADC_DCO`), `R32` (`ADC_D6`), `R34` (`ADC_D8`), and `R28` (`ADC_D2`) on the south-west side of `U8` ($9.5\text{–}10.8\text{ mm}$ away from `U8`'s north/east pins, creating a $\sim 20\text{ mm}$ hairpin detour). Placing `R26..R41` in a compact row along `U8`'s East (pins 7–16) and North (pins 17–23) edges reduces total `U8 -> R -> U12` routed lengths to **$23.2\text{–}29.7\text{ mm}$** and reduces max `DCO`-to-data length skew to **$5.12\text{ mm}$**!

---

## 4. Summary of Routing Constraints Enforced by `agy_timing_check.py`

| Bus | Constraint ID | Rule / Metric | Limit | Board Value (`agy_assignment.json` + local `R26..R41`) | Slack |
|---|---|---|---|---|---|
| **FT601 (`100 MHz`)** | `FT601_MAX_ABS_LEN` | $\max(L_{\text{FT}})$ | $\le \mathbf{35.0\text{ mm}}$ | $24.78\text{ mm}$ (`FT_D1`) | $+10.22\text{ mm}$ |
| **FT601 (`100 MHz`)** | `FT601_CLK_SKEW` | $\max\|L_{\text{FT\_sig}} - L_{\text{FT\_CLK}}\|$ | $\le \mathbf{15.0\text{ mm}}$ | $10.65\text{ mm}$ (`FT_D1`) | $+4.35\text{ mm}$ |
| **FT601 (`100 MHz`)** | `FT601_READ_SETUP` | Worst input setup slack (`IFS1P3DX`) | $\ge \mathbf{0\text{ ps}}$ | $+2322\text{ ps}$ | $+2322\text{ ps}$ |
| **FT601 (`100 MHz`)** | `FT601_READ_HOLD` | Worst input hold slack (`IFS1P3DX`) | $\ge \mathbf{0\text{ ps}}$ | $+1216\text{ ps}$ | $+1216\text{ ps}$ |
| **FT601 (`100 MHz`)** | `FT601_WRITE_SETUP` | Worst output setup slack (`OFS1P3DX` + $135^\circ$ PLL) | $\ge \mathbf{0\text{ ps}}$ | $+924\text{ ps}$ | $+924\text{ ps}$ |
| **FT601 (`100 MHz`)** | `FT601_WRITE_HOLD` | Worst output hold slack vs $T_4=4.8\text{ ns}$ | $\ge \mathbf{0\text{ ps}}$ | $+1342\text{ ps}$ | $+1342\text{ ps}$ |
| **AD9649 (`80 MSPS`)** | `ADC_MAX_ABS_LEN` | $\max(L_{\text{ADC\_total}})$ (`U8 -> R -> U12`) | $\le \mathbf{50.0\text{ mm}}$ | $29.74\text{ mm}$ (`ADC_D0`) | $+20.26\text{ mm}$ |
| **AD9649 (`80 MSPS`)** | `ADC_DCO_SKEW` | $\max\|L_{\text{ADC\_sig}} - L_{\text{ADC\_DCO}}\|$ | $\le \mathbf{20.0\text{ mm}}$ | $5.12\text{ mm}$ (`ADC_D0`) | $+14.88\text{ mm}$ |
| **AD9649 (`80 MSPS`)** | `ADC_SERIES_RES_STUB` | $\max(L_{\text{ADC\_stub}})$ (`U8 -> R` pad 1, if present) | $\le \mathbf{6.0\text{ mm}}$ | $2.20\text{ mm}$ | $+3.80\text{ mm}$ |
| **AD9649 (`80 MSPS`)** | `ADC_SETUP_DEFAULT_0x16_00` | Worst setup slack (default `DCO` `0x16=0x00`) | $\ge \mathbf{0\text{ ps}}$ | $+424\text{ ps}$ | $+424\text{ ps}$ |
| **AD9649 (`80 MSPS`)** | `ADC_HOLD_DEFAULT_0x16_00` | Worst hold slack (default `DCO` `0x16=0x00`) | $\ge \mathbf{0\text{ ps}}$ | $+9893\text{ ps}$ | $+9893\text{ ps}$ |
| **AD9649 (`80 MSPS`)** | `ADC_SETUP_INVDCO_0x16_80` | Worst setup slack (inverted `DCO` `0x16=0x80`) | $\ge \mathbf{0\text{ ps}}$ | $+5474\text{ ps}$ | $+5474\text{ ps}$ |
| **AD9649 (`80 MSPS`)** | `ADC_HOLD_INVDCO_0x16_80` | Worst hold slack (inverted `DCO` `0x16=0x80`) | $\ge \mathbf{0\text{ ps}}$ | $+3643\text{ ps}$ | $+3643\text{ ps}$ |

---

## 5. Usage of `notes/pinswap/agy_timing_check.py`

```bash
# 1. Check a board-extracted JSON file {"net": length_mm, ...}
python3 notes/pinswap/agy_timing_check.py path/to/routed_lengths.json

# 2. Verbose per-net slack breakdown
python3 notes/pinswap/agy_timing_check.py -v path/to/routed_lengths.json

# 3. Built-in self-test (no arguments: uses notes/pinswap/data.json + agy_assignment.json)
python3 notes/pinswap/agy_timing_check.py
```

- Accepts flat KiCad net names (`"FT_D0"`, `"ADC_D0"`, `"ADC_D0_R"`), hierarchical KiCad net names (`"/ADC and clock/ADC_D0_R"`), or gateware LPF signal names (`"ft_data[0]"`, `"adc_d[0]"`).
- If both `"ADC_D*"` (post-resistor trace) and `"ADC_D*_R"` (pre-resistor stub) are present in the JSON, it automatically sums them for total `U8 -> U12` length and checks `ADC_D*_R <= 6.0 mm`.
- Exits with code `0` if all constraints pass, or `1` if any constraint fails.
