Full adversarial review and mathematical proofs have been written to [round4_gateware_review.md](file:///home/user1/collab/projects/usb3-sdr/notes/round4_gateware_review.md). Below is the concise summary of verdicts, line-by-line checks, and derivations.

---

### Summary Verdicts

| Item | Target | Verdict | Key Finding |
| :--- | :--- | :---: | :--- |
| **1a** | [nco.v](file:///home/user1/collab/projects/usb3-sdr/gateware/rtl/nco.v#L18-L35) | **VERIFIED** | Quarter-wave mirror `~ps[11:0]` is **exact** due to the $+0.5\text{ LSB}$ phase offset ($4095 - m \equiv \text{\texttt{\~}}m$). Worst-case $P=14\text{-bit}$ phase-truncation spur is **$-84.29\text{ dBc}$**. *(Minor doc note: [nco.v:2](file:///home/user1/collab/projects/usb3-sdr/gateware/rtl/nco.v#L2) says 4-clock latency from `acc`, whereas [ddc.v:20](file:///home/user1/collab/projects/usb3-sdr/gateware/rtl/ddc.v#L20) correctly notes 3 clocks from `acc` $\to$ `sin_o`.)* |
| **1b** | [ddc.v](file:///home/user1/collab/projects/usb3-sdr/gateware/rtl/ddc.v#L25-L57) | **VERIFIED** | `(pi + 32'sd4096) >>> 13` maps worst-case $(-8192)\times(-131071) = +1{,}073{,}733{,}632 \to \mathbf{+131{,}071 = 2^{17}-1}$, so 18-bit signed `mi, mq` **never overflow** even at `adc = -8192`. [`rnd16`](file:///home/user1/collab/projects/usb3-sdr/gateware/rtl/ddc.v#L51-L57) properly saturates $v \ge +131070$ (`t[18:17] == 2'b01`) to `16'sh7fff`. |
| **1c** | [cic_decim.v](file:///home/user1/collab/projects/usb3-sdr/gateware/rtl/cic_decim.v#L15-L58) | **VERIFIED** | $W = 18 + 5\times 4 = 38\text{b}$ is exact. Each pipelined comb stage ([lines 37–41](file:///home/user1/collab/projects/usb3-sdr/gateware/rtl/cic_decim.v#L37-L41)) implements $H_{\text{comb},i}(z_d) = z_d^{-1}(1 - z_d^{-1})$, so all 5 stages + output reg yield $z_d^{-6}(1 - z_d^{-1})^5 = z^{-96}(1 - z^{-16})^5$: **an exact $N=5, R=16, M=1$ CIC filter** plus a pure 6-sample ($96\text{-clock}$) pipeline delay. [`sat_round`](file:///home/user1/collab/projects/usb3-sdr/gateware/rtl/cic_decim.v#L50-L58) sign-extends and saturates cleanly. |
| **1d** | [fir_decim.v](file:///home/user1/collab/projects/usb3-sdr/gateware/rtl/fir_decim.v#L20-L94) | **VERIFIED** | `AccW = DW + 18 + AW` ($41\text{b}$ HB, $42\text{b}$ CFIR) has $>5\text{ bits}$ headroom above worst-case $\sum|h_k|$. Rounding `(res + (1<<<16)) >>> 17` and [`sat()`](file:///home/user1/collab/projects/usb3-sdr/gateware/rtl/fir_decim.v#L90-L94) are exact. Traveling flags `v, f, l` allow 0-idle-cycle back-to-back runs. Circular buffer overwrite safety margins are **9 slots ($136\text{ clks}$)** for HB (`AW=5, NTAPS=23`) and **5 slots ($132\text{ clks}$)** for CFIR (`AW=6, NTAPS=59`). |
| **2** | [gen_coeffs.py](file:///home/user1/collab/projects/usb3-sdr/gateware/tools/gen_coeffs.py#L14-L54) & [analyze_ddc.py](file:///home/user1/collab/projects/usb3-sdr/gateware/sim/analyze_ddc.py#L11-L26) | **VERIFIED** | The $-13.22\text{ dBFS}$ vs. $-12.96\text{ dBFS}$ ($0.26\text{ dB}$) offset is **100% explained by Blackman-Harris window scalloping loss** ($-0.2582\text{ dB}$ at $100.000\text{ kHz}$, which lands at bin $1310.72$, $\delta = 0.28\text{ bins}$ below bin $1311$ at $100.021\text{ kHz}$). True cascaded filter gain at $100\text{ kHz}$ is **$-0.00004\text{ dB}$** ($-0.0285\text{ dB CIC} - 0.0002\text{ dB HB} + 0.0286\text{ dB CFIR}$). |
| **3** | [ft601_245.v](file:///home/user1/collab/projects/usb3-sdr/gateware/rtl/ft601_245.v#L54-L121) | **VERIFIED** | 4-bit pointers (`conf, send, fill`) with `fill_lvl < 8` prevent overwrite. The rewind guard `(prev_idx - conf) < (send - conf)` ([line 85](file:///home/user1/collab/projects/usb3-sdr/gateware/rtl/ft601_245.v#L85)) is essential to prevent a second in-flight rejected word from un-rewinding `send`. Exhaustively verified across all $2^{16}$ `TXE_N` sequences: **only a 1-cycle `TXE_N`-high pulse** can reorder words, and `prev_idx != conf` ([line 83](file:///home/user1/collab/projects/usb3-sdr/gateware/rtl/ft601_245.v#L83)) deterministically sets `order_err`. |

---

### 1. DSP Arithmetic Details

1. **NCO Quarter-Wave Symmetry & Spurs ([nco.v:18-35](file:///home/user1/collab/projects/usb3-sdr/gateware/rtl/nco.v#L18-L35), [gen_coeffs.py:45-47](file:///home/user1/collab/projects/usb3-sdr/gateware/tools/gen_coeffs.py#L45-L47))**:
   - The $4096 \times 18\text{-bit}$ ROM stores $\text{round}\big((2^{17}-1)\sin(2\pi(k+0.5)/16384)\big)$ for $k \in [0, 4095]$.
   - For 14-bit phase $p = \text{\texttt{acc[31:18]}} = 8192 q_1 + 4096 q_0 + m$ ($m = p[11:0] \in [0, 4095]$), in odd quadrants ($q_0 = 1$) the target angle modulo $\pi$ is:
     $$\frac{2\pi(4096 + m + 0.5)}{16384} = \pi - \frac{2\pi\big((4095 - m) + 0.5\big)}{16384}$$
     Since 12-bit bitwise NOT is $\text{\texttt{\~}}m \equiv 4095 - m$, indexing `rom[~ps[11:0]]` ([nco.v:22](file:///home/user1/collab/projects/usb3-sdr/gateware/rtl/nco.v#L22)) is **mathematically exact** with zero phase discontinuity at quadrant boundaries.
   - With $P = 14$ truncated phase bits and zero-mean phase error (via the $+0.5\text{ LSB}_{14}$ offset), the worst-case phase-truncation spur is $20\log_{10}(2^{-14}) = \mathbf{-84.29\text{ dBc}}$.

2. **Mixer Scaling ([ddc.v:25-31](file:///home/user1/collab/projects/usb3-sdr/gateware/rtl/ddc.v#L25-L31))**:
   - With `x` $\in [-8192, +8191]$ and `cos_w, -sin_w` $\in [-131071, +131071]$, the maximum positive product is $(-8192)\times(-131071) = +1{,}073{,}733{,}632$.
   - `(pi + 32'sd4096) >>> 13` gives $\lfloor 1{,}073{,}737{,}728 / 8192 \rfloor = \mathbf{+131{,}071 = 2^{17}-1}$, fitting inside signed 18-bit `mi, mq` without overflow.

3. **Pipelined CIC Transfer Function ([cic_decim.v:35-46](file:///home/user1/collab/projects/usb3-sdr/gateware/rtl/cic_decim.v#L35-L46))**:
   - On each decimated `strobe` ($z_d = z^{16}$), stage $i$ computes `comb[i] <= comb[i-1] - dly[i]; dly[i] <= comb[i-1]`, which has transfer function $H_{\text{comb},i}(z_d) = z_d^{-1}(1 - z_d^{-1})$.
   - Cascading $N=5$ stages plus the `dout` register yields $H_{\text{comb}}(z_d) = z_d^{-6}(1 - z_d^{-1})^5 = z^{-96}(1 - z^{-16})^5$, preserving the exact CIC magnitude/aliasing response with a pure $96$-clock delay.

4. **FIR Circular-Buffer Overwrite Safety ([fir_decim.v:49-65](file:///home/user1/collab/projects/usb3-sdr/gateware/rtl/fir_decim.v#L49-L65))**:
   - When a run starts at clock $t = 0$ with `base = w_0`, the oldest tap ($\tau = \text{NTAPS}-1$) is at address $k_{\text{oldest}} = w_0 - (\text{NTAPS}-1) \equiv w_0 + (2^{\text{AW}} - \text{NTAPS} + 1) \pmod{2^{\text{AW}}}$ and is read by `x_rd <= buf_mem[k]` ([line 65](file:///home/user1/collab/projects/usb3-sdr/gateware/rtl/fir_decim.v#L65)) at clock $t_{\text{read}} = \text{NTAPS} + 1$:

| Instance | `NTAPS` | `AW` ($2^{\text{AW}}$) | $k_{\text{oldest}}$ | $t_{\text{read}}$ | New Writes in $[1, t_{\text{read}}]$ | Overwrite Clock $t_{\text{ovw}}$ | Safety Margin |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`u_hb`** | 23 | 5 (32) | $w_0 + 10 \pmod{32}$ | $t = 24$ | 1 write (at $t=16 \to w_0+1$) | $t = 160$ | **9 slots ($136\text{ clks}$)** |
| **`u_cfir`** | 59 | 6 (64) | $w_0 + 6 \pmod{64}$ | $t = 60$ | 1 write (at $t=32 \to w_0+1$) | $t = 192$ | **5 slots ($132\text{ clks}$)** |

---

### 2. Filter Gain & The `-13.22 dBFS` vs. `-12.96 dBFS` Tone Level

At $f_{s,\text{out}} = 1.25\text{ MSPS}$ and $N = 16384$ ([analyze_ddc.py:11-24](file:///home/user1/collab/projects/usb3-sdr/gateware/sim/analyze_ddc.py#L11-L24)), $\Delta f = \frac{1.25\text{e6}}{16384} = 76.293945\text{ Hz}$. The $100.000\text{ kHz}$ tone falls at fractional bin **$1310.7200$**, which is **$\delta = 0.2800\text{ bins}$** away from integer bin $1311$ ($100.021\text{ kHz}$).

| Term | Exact Gain / Level | Notes |
| :--- | :---: | :--- |
| Ideal tone level | **$-12.9574\text{ dBFS}$** | $20\log_{10}(0.45 \times \frac{8191}{8192} \times \frac{1}{2})$ ([analyze_ddc.py:23](file:///home/user1/collab/projects/usb3-sdr/gateware/sim/analyze_ddc.py#L23)) |
| NCO ROM scaling | **$-0.0001\text{ dB}$** | $(2^{17}-1)/2^{17}$ |
| $\text{CIC}_5(R=16)$ @ $100\text{ kHz}$ | **$-0.0285\text{ dB}$** | $\|\sin(16\pi f/f_s)/(16\sin(\pi f/f_s))\|^5 = 0.996726$ |
| $\text{HB}_{23}$ (`hb.hex`) @ $100\text{ kHz}$ | **$-0.0002\text{ dB}$** | Quantized Q1.17 @ $5\text{ MSPS}$ ($0.999977$; DC $= 131069/2^{17}$) |
| $\text{CFIR}_{59}$ (`cfir.hex`) @ $100\text{ kHz}$ | **$+0.0286\text{ dB}$** | Quantized Q1.17 @ $2.5\text{ MSPS}$ ($1.003303$; pre-compensates CIC droop) |
| **Net Filter Chain ($\text{CIC}\cdot\text{HB}\cdot\text{CFIR}$)** | **$-0.00004\text{ dB}$** | **$0.999996$** ($4\text{ ppm}$ error at $100\text{ kHz}$; $\le 0.017\text{ dB}$ ripple across $0\text{–}500\text{ kHz}$) |
| Blackman-Harris scalloping ($\delta = 0.28$) | **$-0.2582\text{ dB}$** | 4-term BH window evaluated at $\delta = |1311 - 1310.72| = 0.28\text{ bins}$ |
| **Predicted vs. Simulated Bin 1311** | **$-13.2156\text{ dBFS}$ vs. $-13.22\text{ dBFS}$** | **Exact match to simulation** |

---

### 3. `rtl/ft601_245.v` Replay Buffer & Pointer Arithmetic

1. **4-Bit Pointers (`conf, send, fill`, [lines 55–61](file:///home/user1/collab/projects/usb3-sdr/gateware/rtl/ft601_245.v#L55-L61))**:
   - `rb[0:7]` is addressed by `[2:0]` while bit 3 tracks wrap-around so `fill_lvl = fill - conf` spans $0..8$. Stopping `tx_pop` at `fill_lvl == 8` guarantees `fill[2:0]` never overwrites an unconfirmed entry at `conf[2:0]`.
2. **Why `(prev_idx - conf) < (send - conf)` ([line 85](file:///home/user1/collab/projects/usb3-sdr/gateware/rtl/ft601_245.v#L85)) Is Required**:
   - When `TXE_N` goes high for $\ge 2$ cycles (rejecting $W_k$ at edge $t$ and $W_{k+1}$ at edge $t+1$), $W_k$'s rejection is judged at edge $t+1$, rewinding `send <= k` (so `send - conf == 0`).
   - One clock later (edge $t+2$), $W_{k+1}$ (`prev_idx = k+1`) is judged as rejected while `send == conf == k`. Because `(prev_idx - conf) < (send - conf)` evaluates `1 < 0` (**FALSE**), $W_{k+1}$ is prevented from overwriting `send <= k+1` and dropping $W_k$.
3. **1-Cycle `TXE_N` Pulse & `order_err` ([lines 81–88](file:///home/user1/collab/projects/usb3-sdr/gateware/rtl/ft601_245.v#L81-L88))**:
   - Because `wr_n` is deasserted at edge $t+2$ immediately after $W_k$ is judged rejected at edge $t+1$, only edge $t+1$ (where $W_{k+1}$ is already on the pins) can be accepted out of order, and *only* if `txe_n(t) = 1` and `txe_n(t+1) = 0` (a 1-cycle high pulse). At edge $t+2$, `prev_v && !txe_q` sees `prev_idx = k+1 != conf = k` and deterministically latches `order_err <= 1`.
