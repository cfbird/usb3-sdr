# FT601 Output IO-Register & PLL Phase Implementation (`usb3-sdr`, 2026-10-24)

**Author:** AGY  
**Scope:** Implementation and verification of `notes/pinswap/BRIEF_ft601_ioreg.md` (Items 1–4)  
**Edited Files:** `gateware/rtl/ft601_245.v`, `gateware/rtl/top.v`, `notes/pinswap/agy_ft601_ioreg.md`

---

## 1. Gateware Implementation (`ft601_245.v` & `top.v`)

### 1.1 Packing All FT601 Outputs & Tristate Enables into ECP5 `IOLOGIC`
Under `` `ifdef ECP5_IOREG ``, every synchronous FT601 output and tristate enable is now instantiated as an explicit ECP5 `IOLOGIC` flip-flop in `gateware/rtl/ft601_245.v` and connected to `BB` (`TRELLIS_IO #(.DIR("BIDIR"))`) pads in `gateware/rtl/top.v`:
- **Control outputs (`ft_wr_n`, `ft_rd_n`, `ft_oe_n`)**: 3 $\times$ `OFS1P3BX` (`u_wr`, `u_rd`, `u_oe`, `REGSET="SET"` so active-low strobes initialize high on GSR).
- **Data outputs (`ft_data[31:0]`)**: 32 $\times$ `OFS1P3DX` (`g_dout[g].u_do`, `IOLOGIC` `OUTFF` driving `BB.I` via `.DATAMUX_OREG = IOLDO`).
- **Data tristate enables (`ft_data[31:0].T`)**: 32 $\times$ `OFS1P3BX` (`g_dout[g].u_dt`, `IOLOGIC` `TSFF` driving active-low `BB.T` via `.TRIMUX_TSREG = IOLTO`, `REGSET="SET"` so the bus initializes to high-Z).
- **Byte-enable outputs & tristates (`ft_be[3:0]`, `ft_be[3:0].T`)**: 4 $\times$ `OFS1P3BX` (`g_be[g].u_bo` for data `1'b1`) + 4 $\times$ `OFS1P3BX` (`g_be[g].u_bt` for active-low tristate `BB.T`).
- **Inputs (`ft_txe_n`, `ft_rxf_n`, `ft_data[31:0]`)**: 34 $\times$ `IFS1P3DX` (`u_txe`, `u_rxf`, `g_din[g].u_d`, unchanged).

### 1.2 Why `BB` + Active-Low `OFS1P3BX` Is Required for `TSREG` Packing (`VERIFIED`)
- In the original `top.v`, `assign ft_data = doe ? dout : 32'bz;` inferred Yosys `$_TBUF_` cells with active-high `.E`. Because `TRELLIS_IO.T` is active-low (`0` = drive, `1` = high-Z), `nextpnr-ecp5` inserted a fabric `LUT4` inverter (`ft_data[i]$tr_io$invert_T`) in front of `TRELLIS_IO.T`, preventing any flip-flop from packing into `IOLOGIC` `TSREG` and creating the $5.17\text{ ns}$ `<async>` path (`u_ft.doe -> ft_data[6].T`).
- By generating active-low `doe_t_n = ~doe_nxt` before the flip-flop, registering it in 36 per-pad `OFS1P3BX` instances (`dout_t[31:0]`, `be_t[3:0]`), and feeding `BB.T` directly in `top.v`, `nextpnr-ecp5` packs all 36 tristate flip-flops into `IOLOGIC` (`PIOC.TRIMUX_TSREG = IOLTO`) with **zero** fabric LUTs or routing between `IOLOGIC` and `PIO`.
- In `gateware/build/nextpnr.log` (lines 123–163, 206), `IOLOGIC` utilization increases from `48/128` to **`55/128`** (41 FT601 `IOLOGIC` sites packing **109 FT601 IO flip-flops** + 14 ADC `IOLOGIC` sites = 123 total IO flip-flops), and the `posedge clk_ft -> <async>` path on `ft_data`/`ft_be` is **completely eliminated**.

### 1.3 Avoiding `IOLOGIC` Resource Conflicts (`CE`, `LSR`, and Fabric Feedback)
- **No fabric fanout from `OFS1P3DX`/`OFS1P3BX` `.Q`**: In ECP5 silicon, `IOLOGIC` outputs (`IOLDO`, `IOLTO`) have dedicated hardwired connections only to their co-located `PIO` pad and cannot route back into the fabric. Internal FSM state copies (`wr_n_r`, `rd_n_r`, `oe_n_r`, `doe_r`) are updated by the exact same next-state wires (`wr_n_nxt`, `rd_n_nxt`, `oe_n_nxt`, `doe_nxt`) that feed `.D` of the `OFS1P3BX` cells.
- **Unconditional `.SP(1'b1)` and `.CD(1'b0)` / `.PD(1'b0)`**: Inside each `ft_data[g]` `IOLOGIC` Bel, `INFF`, `OUTFF`, and `TSFF` share a single `CE` mux and a single `LSR` mux. Driving `dout_nxt = rb[send[2:0]]` unconditionally into `OFS1P3DX` with `.SP(1'b1)` avoids a `CE` conflict with `IFS1P3DX` (`.SP(1'b1)`), and also removes the `rewind` judge logic from the 32-bit `dout` fanout cone (improving `clk_ft` Fmax by $+5.4\text{ to }+19.5\text{ MHz}$!).

---

## 2. Clocking Choice (`+112.5 deg` Single-Clock `EHXPLLL`) & 1-Cycle Replay Verification

### 2.1 Why the Single-Clock $+112.5^\circ$ (`+3.125 ns`) Variant Was Chosen (`VERIFIED`)
We implemented the **single-clock $+112.5^\circ$ ($\Delta t_{\text{PLL}} = \mathbf{+3.125\text{ ns}}$) `EHXPLLL` configuration** in `gateware/rtl/top.v`:
- `CLKI` = `ft_clk` ($100\text{ MHz}$ on `J16`, `PCLKT2_1`; `CLKI_DIV = 1`, `CLKFB_DIV = 1`, `CLKOP_DIV = 6`, `CLKOS_DIV = 6` $\implies f_{\text{VCO}} = 600\text{ MHz}$).
- **`CLKOP` ($0^\circ$, `CPHASE = 2, FPHASE = 0`)**: Connected to `CLKFB` (`FEEDBK_PATH = "CLKOP"`) via global clock network to compensate the global clock tree insertion delay.
- **`CLKOS` ($+112.5^\circ = +3.125\text{ ns}$, `CPHASE = 3, FPHASE = 7`)**: Promoted to global clock `clk_ft` (`global 1`) and drives **all** FT601 `IOLOGIC` cells (`IFS1P3DX`, `OFS1P3DX`, `OFS1P3BX`), `ft601_245` fabric, and `async_fifo.rd_clk`.

**Two decisive reasons for choosing the single-clock $+112.5^\circ$ variant over a split $0^\circ / +135^\circ$ scheme:**
1. **Hard ECP5 `IOLOGIC` Silicon & `nextpnr-ecp5` Constraint (`VERIFIED`)**:
   Each bidirectional `ft_data[g]` pad maps to a single `IOLOGIC` Bel (`X72/Y*/IOLOGIC[A-D]`) that packs `IFS1P3DX` (`INFF`), `OFS1P3DX` (`OUTFF`), and `OFS1P3BX` (`TSFF`) together (`IOLOGICC.MODE = IREG_OREG`). That `IOLOGIC` Bel has **only one `CLK` input pin** shared by `INFF`, `OUTFF`, and `TSFF`. Attempting to clock `IFS1P3DX` from $0^\circ$ `CLKOP` and `OFS1P3DX`/`OFS1P3BX` from $+135^\circ$ `CLKOS` on `ft_data[31:0]` is physically illegal in ECP5 and causes `nextpnr-ecp5` to abort during IO packing:
   ```
   ERROR: IOLOGIC 'u_bb$IOL' has conflicting clocks 'clk_out' and 'clk_in'
   ```
2. **Full $10.0\text{ ns}$ Period for All Fabric-to-IO Paths (`VERIFIED`)**:
   If the fabric ran on $0^\circ$ and output registers ran on $+135^\circ$, every fabric-to-`OFS1P3DX` path (`wr_n_nxt`, `dout_nxt`, `doe_t_n`) would cross between two phases separated by only $3.75\text{ ns}$. Running `IFS1P3DX`, the `ft601_245` FSM, and `OFS1P3DX`/`OFS1P3BX` on the single `clk_ft` (`+112.5 deg`) gives every register-to-register path inside the FPGA a full $10.000\text{ ns}$ clock period.

### 2.2 Verification of 1-Cycle Write-Side Replay Buffer Relationships (`VERIFIED`)
Because `OFS1P3DX`/`OFS1P3BX` **replaces** the original fabric flip-flop stage on `wr_n` and `dout` (driven by combinational `wr_n_nxt` and `dout_nxt`), there is **zero change in pipeline depth** (still 1 register stage from `rb[send[2:0]]` to `ft_data`). Tracing the physical edges with $\Delta t_{\text{PLL}} = +3.125\text{ ns}$:
1. **Launch at FPGA edge $C_k$ ($t = 10k + 3.125\text{ ns}$)**: `OFS1P3DX` launches word $W_0$ (`wr_n = 0, dout = W_0`). Including PCB flight and `PIO` delay, $W_0$ arrives at `U11` at $t \in [10k + 5.52,\; 10k + 7.27]\text{ ns} \subset [10k + 4.80,\; 10k + 9.00]\text{ ns}$.
2. **Sample at FT601 edge $E_{k+1}$ ($t = 10(k+1)\text{ ns}$)**: FT601 samples $W_0$ and evaluates its internal `TXE_N(E_{k+1})`. FT601 holds `TXE_N(E_{k+1})` valid on the pin until at least $t = 10(k+1) + T_2 = 10(k+1) + 3.50\text{ ns}$ (which remains at `IFS1P3DX.D` until $\ge 10(k+1) + 4.27\text{ ns}$).
3. **Capture at FPGA edge $C_{k+1}$ ($t = 10(k+1) + 3.125\text{ ns}$)**: `IFS1P3DX` (`u_txe`) captures `TXE_N(E_{k+1})` into `txe_q` while `prev_v <= !wr_n_r` and `prev_idx <= cur_idx` record that $W_0$ was on the bus at $E_{k+1}$, and `OFS1P3DX` speculatively launches $W_1$ for $E_{k+2}$.
4. **Judge at FPGA edge $C_{k+2}$ ($t = 10(k+2) + 3.125\text{ ns}$)**: The `judge` logic inspects `prev_v` (for $W_0$) and `txe_q` (`TXE_N(E_{k+1})`), either advancing `conf <= conf + 1` (if `txe_q == 0` and `prev_idx == conf`), flagging `order_err <= 1` (if taken out of order after a 1-cycle `TXE_N` pulse), or rewinding `send_n = prev_idx` (if `txe_q == 1`).

Thus the 1-cycle replay loop and 1-cycle `TXE_N` reorder detection are **100% preserved**.

---

## 3. Verification: Simulation & `nextpnr-ecp5` Multi-Seed Fmax (`Seeds 1–4`)

### 3.1 CXXRTL Simulation Results (`make sim` / `make sim-ft`)
All three simulation testbenches pass:
- **`make sim-ft` (`./tb_ft 2` — normal $\ge 2$-cycle `TXE_N` pulses)**:
  `FPGA->host words 399974 (320 MB/s avg over 5000 us), order errors 0, bus contention 0`
  `host->FPGA words sent 390, received 390; DUT order_err flag 0 (min TXE_N high 2 cycles) -> PASS`
- **`make sim-ft` (`./tb_ft 1` — 1-cycle `TXE_N` pulse reorder detection)**:
  `FPGA->host words 400068 (320 MB/s avg over 5000 us), order errors 198, bus contention 0`
  `host->FPGA words sent 385, received 385; DUT order_err flag 1 (min TXE_N high 1 cycles) -> PASS`
- **`make sim-ddc`**: `1.2499 MSPS`, alias rejection `94.9 dB`, SFDR `92.2 dBc` -> `PASS`
- **`make sim-boot`**: `done=1 after 86429 boot clocks (35.7 ms @ 2.42 MHz), nack=0` -> `PASS`

### 3.2 `nextpnr-ecp5` Fmax & Resource Summary Across Seeds 1–4 (`LFE5U-25F-6BG256C`)

| Metric / Clock Domain | Target | Baseline (Before Fix, Seed 4) | Seed 1 | Seed 2 | Seed 3 | Seed 4 (Default) | Verdict |
|---|---|---|---|---|---|---|---|
| **`$glbnet$clk_ft` Fmax** | $\ge 100.00\text{ MHz}$ | $100.56\text{ MHz}$ | **$111.88\text{ MHz}$** | **$119.82\text{ MHz}$** | **$120.02\text{ MHz}$** | **$106.00\text{ MHz}$** | **PASS (4/4 seeds)** |
| **`$glbnet$adc_dco` Fmax** | $\ge 80.00\text{ MHz}$ | $109.77\text{ MHz}$ | **$108.19\text{ MHz}$** | **$100.01\text{ MHz}$** | **$101.21\text{ MHz}$** | **$101.48\text{ MHz}$** | **PASS (4/4 seeds)** |
| **`$glbnet$clk_boot` Fmax** | $\ge 2.42\text{ MHz}$ | $153.42\text{ MHz}$ | **$132.28\text{ MHz}$** | **$134.72\text{ MHz}$** | **$139.78\text{ MHz}$** | **$136.48\text{ MHz}$** | **PASS (4/4 seeds)** |
| **`IOLOGIC` Utilization** | — | `48 / 128 (37%)` | `55 / 128 (42%)` | `55 / 128 (42%)` | `55 / 128 (42%)` | `55 / 128 (42%)` | **VERIFIED** |
| **`EHXPLLL` Utilization** | — | `0 / 2 (0%)` | `1 / 2 (50%)` | `1 / 2 (50%)` | `1 / 2 (50%)` | `1 / 2 (50%)` | **VERIFIED (`X70/Y49`)** |
| **`TRELLIS_FF` Utilization** | — | `2650 / 24288` | `2618 / 24288` | `2618 / 24288` | `2618 / 24288` | `2618 / 24288` | **$-32$ fabric FFs** |
| **`TRELLIS_COMB` Utilization** | — | `2835 / 24288` | `2797 / 24288` | `2797 / 24288` | `2797 / 24288` | `2797 / 24288` | **$-38$ fabric LUTs** |

---

## 4. Re-Derived FT601 `T1..T4` Bus Timing Budget (Final Implementation)

With the final implementation (`EHXPLLL` `CLKOS` at $\Delta\phi = +112.5^\circ \implies \Delta t_{\text{PLL}} = \mathbf{+3.125\text{ ns}}$, `CLKOP` at $0^\circ$ feeding `CLKFB`, and all FT601 inputs/outputs/tristates in `IOLOGIC`), and using the board trace lengths from `notes/pinswap/agy_assignment.json`:
- `FT_CLK` octilinear length: $L_{\text{clk}} = 14.13\text{ mm}$ ($\tau_{\text{clk}} \in [85,\; 99]\text{ ps}$ for $\tau \in [6.0,\; 7.0]\text{ ps/mm}$).
- Synchronous signal octilinear lengths: $L_{\text{sig}} \in [12.64,\; 24.78]\text{ mm}$ ($\tau_{\text{sig}} \in [76,\; 173]\text{ ps}$).
- Effective `IOLOGIC.SCLK` arrival time relative to $\uparrow\text{FT\_CLK}$ at `U11` pin 58:
  $$t_{\text{clk,IOL}} = \tau_{\text{clk}} + \Delta t_{\text{PLL}} \in [85 + 3125,\; 99 + 3125] = [\mathbf{3210\text{ ps}},\; \mathbf{3224\text{ ps}}]$$

### 4.1 Read / Status Input Path (`FT601` $\to$ `FPGA IFS1P3DX`: `T1 = 3000 ps`, `T2 = 3500 ps`)
- **Latest data arrival at `IFS1P3DX.D` (`T1` Setup)**:
  $$t_{\text{data,max}} = -T_1 + \tau_{\text{sig,max}} + t_{\text{IN,PIO,max}} = -3000 + 173 + 1140 = \mathbf{-1687\text{ ps}}$$
  $$\text{Slack}_{\text{SU,rd}} = t_{\text{clk,IOL,min}} - t_{\text{data,max}} - t_{\text{SU,IREG}} = 3210 - (-1687) - 439 = \mathbf{+4458\text{ ps}}$$
- **Earliest data transition at `IFS1P3DX.D` (`T2` Hold)**:
  - At `prjtrellis` speed `-6` min corner ($t_{\text{IN,PIO,min}} = 990\text{ ps}$):
    $$t_{\text{data,min}} = T_2 + \tau_{\text{sig,min}} + t_{\text{IN,PIO,min}} = 3500 + 76 + 990 = \mathbf{+4566\text{ ps}}$$
    $$\text{Slack}_{\text{HD,rd}}(\text{speed }-6) = t_{\text{data,min}} - t_{\text{clk,IOL,max}} - t_{\text{H,IREG}} = 4566 - 3224 - 311 = \mathbf{+1031\text{ ps}}$$
  - At $0.70\times$ fast-PVT derated corner ($t_{\text{IN,PIO,fast}} = 0.70 \times 990 = 693\text{ ps}$):
    $$t_{\text{data,min}}(\text{fast PVT}) = 3500 + 76 + 693 = \mathbf{+4269\text{ ps}} \implies \text{Slack}_{\text{HD,rd}}(\text{fast PVT}) = 4269 - 3224 - 311 = \mathbf{+734\text{ ps}}$$

### 4.2 Write / Control Output Path (`FPGA OFS1P3DX/OFS1P3BX` $\to$ `FT601`: `T3 = 1000 ps`, `T4 = 4800 ps`)
- **Latest arrival at `U11` before next $\uparrow\text{FT\_CLK}$ (`T3` Setup, required $\le T_{\text{CLK}} - T_3 = 9000\text{ ps}$)**:
  - Data/control (`OREG`: $t_{\text{CO,OREG}} + t_{\text{OUT,PIO,max}} = 1200 + 2674 = 3874\text{ ps}$):
    $$t_{\text{arrive,max}}(\text{OREG}) = t_{\text{clk,IOL,max}} + 3874 + \tau_{\text{sig,max}} = 3224 + 3874 + 173 = \mathbf{7271\text{ ps}} \implies \text{Slack}_{\text{SU,wr}}(\text{OREG}) = 9000 - 7271 = \mathbf{+1729\text{ ps}}$$
  - Tristate enable (`TSREG`: $t_{\text{CO,TSREG}} + t_{\text{TS,PIO,max}} = 1031 + 3023 = 4054\text{ ps}$):
    $$t_{\text{arrive,max}}(\text{TSREG}) = t_{\text{clk,IOL,max}} + 4054 + \tau_{\text{sig,max}} = 3224 + 4054 + 173 = \mathbf{7451\text{ ps}} \implies \text{Slack}_{\text{SU,wr}}(\text{TSREG}) = 9000 - 7451 = \mathbf{+1549\text{ ps}}$$
- **Earliest transition at `U11` after $\uparrow\text{FT\_CLK}$ (`T4` Hold, required $\ge T_4 = 4800\text{ ps}$)**:
  - At `prjtrellis` speed `-6` min corner ($t_{\text{CO,OREG}} + t_{\text{OUT,PIO,min}} = 1200 + 1988 = 3188\text{ ps}$):
    $$t_{\text{arrive,min}}(\text{speed }-6) = t_{\text{clk,IOL,min}} + 3188 + \tau_{\text{sig,min}} = 3210 + 3188 + 76 = \mathbf{6474\text{ ps}} \implies \text{Slack}_{\text{HD,wr}}(\text{speed }-6) = 6474 - 4800 = \mathbf{+1674\text{ ps}}$$
  - At $0.70\times$ fast-PVT derated corner ($0.70 \times 3188 = 2232\text{ ps}$):
    $$t_{\text{arrive,min}}(\text{fast PVT}) = 3210 + 2232 + 76 = \mathbf{5518\text{ ps}} \implies \text{Slack}_{\text{HD,wr}}(\text{fast PVT}) = 5518 - 4800 = \mathbf{+718\text{ ps}}$$

### 4.3 Final FT601 `T1..T4` Timing Budget Summary Table

| FT601 Timing Parameter (`Table 4.2`, p. 17) | Direction & Path | Requirement at Endpoint | Actual Arrival / Window (`+112.5 deg` PLL + `IOLOGIC`) | Slack (Speed `-6` Corner) | Slack ($0.70\times$ Fast-PVT Corner) | Status |
|---|---|---|---|---|---|---|
| **`T1` — Slave Drive Setup** ($3.0\text{ ns}$ min) | `FT601 -> IFS1P3DX.D` | Data valid $\le t_{\text{clk,IOL}} - 439\text{ ps}$ ($\le +2771\text{ ps}$) | Valid from **$-1687\text{ ps}$** | **$+4458\text{ ps}$** | **$+4527\text{ ps}$** | **PASS** |
| **`T2` — Slave Drive Hold** ($3.5\text{ ns}$ min) | `FT601 -> IFS1P3DX.D` | Data held $\ge t_{\text{clk,IOL}} + 311\text{ ps}$ ($\ge +3535\text{ ps}$) | Held until **$+4566\text{ ps}$** (`-6`) / **$+4269\text{ ps}$** (PVT) | **$+1031\text{ ps}$** | **$+734\text{ ps}$** | **PASS** |
| **`T3` — Master Drive Setup** ($1.0\text{ ns}$ min) | `OFS1P3DX (OREG) -> FT601` | Arrival at `U11` $\le 10000 - 1000 = \mathbf{9000\text{ ps}}$ | Arrives at **$+7271\text{ ps}$** max | **$+1729\text{ ps}$** | — | **PASS** |
| **`T3` — Master Drive Setup (Tristate)** | `OFS1P3BX (TSREG) -> FT601` | Arrival at `U11` $\le \mathbf{9000\text{ ps}}$ | Arrives at **$+7451\text{ ps}$** max | **$+1549\text{ ps}$** | — | **PASS** |
| **`T4` — Master Drive Hold** ($4.8\text{ ns}$ min) | `OFS1P3DX (OREG) -> FT601` | Held at `U11` $\ge \mathbf{4800\text{ ps}}$ | Transitions at **$+6474\text{ ps}$** (`-6`) / **$+5518\text{ ps}$** (PVT) | **$+1674\text{ ps}$** | **$+718\text{ ps}$** | **PASS** |
