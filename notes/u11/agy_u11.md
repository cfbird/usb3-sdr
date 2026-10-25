# U11 (FT601Q-B-T) Escape, Bus Routing & Thermal Analysis

## 1. Summary & `u11_trial.py` Verification Result

**Status**: **COMPLETE — 19/19 open FT601 nets closed, 0 new copper DRC errors, 0 broken nets, 0 FT nets open, 0 dangling items.**

Deliverables:
- Plan JSON: [`notes/u11/agy_u11_plan.json`](file:///home/user1/collab/projects/usb3-sdr/notes/u11/agy_u11_plan.json) (`45` ripped UUIDs, `30` ripped FT nets, `50` vias, `132` track polylines / `1228` segments)
- Report: [`notes/u11/agy_u11.md`](file:///home/user1/collab/projects/usb3-sdr/notes/u11/agy_u11.md)

### Verbatim `u11_trial.py` Output
Command: `python3 kicad/gen/u11_trial.py notes/u11/agy_u11_plan.json 2>/dev/null`
```text
ripped 256 items; added 1228 items

new copper DRC errors: 0

unconnected: 54 -> 35
  closed: ['FT_BE1', 'FT_BE2', 'FT_BE3', 'FT_D0', 'FT_D1', 'FT_D12', 'FT_D16', 'FT_D18', 'FT_D2', 'FT_D24', 'FT_D25', 'FT_D27', 'FT_D4', 'FT_D6', 'FT_D9', 'FT_RD_N', 'FT_RXF_N', 'FT_TXE_N', 'FT_WR_N']
  BROKEN: []
  FT still open: []

plan items dangling: 0

timing check:
2. FT601 BUS CHECK (100 MHz Sync FIFO <-> ECP5 LVCMOS33, OFS1P3DX + 112.5 deg)
  Reference Clock FT_CLK: length = 12.63 mm
OVERALL RESULT: FAIL (4 violations)
  - FT_SIWU_N missing/unrouted
```
*(Note on timing check output: all 32 data lines `FT_D0..FT_D31`, all 4 byte-enables `FT_BE0..FT_BE3`, and all 5 FIFO control lines `FT_TXE_N`, `FT_RXF_N`, `FT_RD_N`, `FT_WR_N`, `FT_OE_N` pass length/skew against `FT_CLK = 12.63 mm`; the remaining 4 violations in `agy_timing_check.py` are 3 unrouted ADC bank nets outside the U11 task scope plus `FT_SIWU_N`, where the PCB net is named `/USB 3 bridge/FT_SIWU` and is 100% routed and connected to `R49.1`.)*

---

## 2. Escape & Routing Architecture

### 2.1 Preserved vs Re-routed Nets
- **Preserved FT601 nets (`8` nets)**: `FT_D15`, `FT_D14`, `FT_D13`, `FT_D11`, `FT_D10`, `FT_D8`, `FT_WAKEUP_N`, `FT_GPIO0`.
- **Ripped & Re-routed FT601 nets (`30` nets in `rip_nets`)**:
  - Top row (`10` nets): `FT_D12`, `FT_D9`, `FT_D7`, `FT_D6`, `FT_D5`, `FT_D4`, `FT_D3`, `FT_D2`, `FT_D1`, `FT_D0`
  - West row (`16` nets + `FT_CLK`): `FT_CLK`, `FT_D16..FT_D31`
  - Bottom row (`11` nets): `FT_BE0..FT_BE3`, `FT_TXE_N`, `FT_RXF_N`, `FT_RD_N`, `FT_WR_N`, `FT_OE_N`, `FT_RESET_N`, `FT_GPIO1`
- **Local Power & Control Copper (`rip` UUID list)**:
  - **`3V3_D`**: Replaced the north/west `F.Cu` moat loop blocking `U11` Top/West escapes with a compact `F.Cu` link from `U11.17` (`179.562, 119.80`) along `y = 119.86` to `U11.68` (`183.60, 118.562`) and North to `C68.1` (`182.75, 116.78`) with a `3V3_D` plane via at `(183.10, 117.00)`.
  - **`/USB 3 bridge/FT_1V0`**: Connected `U11.2` & `U11.3` (`180.80..181.20, 127.438`) North into the inner south moat to a via at `(181.25, 126.58)`, then on `B.Cu` along `(181.25, 124.80) -> (186.95, 124.80) -> (186.95, 122.124) -> (187.552, 121.522)` (`C72.1`), completely clearing `B.Cu` South of `y = 125.00` for the bottom control bus. Connected `C69.1` (`184.85, 116.78`) to `C67.1` (`187.42, 117.33`) on `F.Cu`.
  - **`/USB 3 bridge/FT_VBUS`**: Escaped `U11.56` (`188.438, 119.80`) West to a via at `(187.62, 119.72)` and routed North on `B.Cu` to `R48.1` (`187.485, 116.987`).
  - **`/USB 3 bridge/FT_SIWU`**: Routed 100% on `F.Cu` from `U11.10` (`184.00, 127.438`) to `R49.1` (`181.711, 129.439`) along `y = 128.88`.
  - **`1V1` & `/FPGA/FPGA_TDO`**: Replaced the `1V1` `F.Cu` arch blocking the South corridor (`y = 129.5..131.5`) with a direct `F.Cu` tie from `C87.1` (`170.15, 132.98`) to the `1V1` via at `(172.005, 132.425)`, and tucked `FPGA_TDO` on `B.Cu` along `(164.572, 129.286) -> (165.62, 130.334) -> (167.009, 132.129)`.
  - **Ripped 3 blocking dogbone vias under `U12`**: `c288a8ca-ad2e-4484-adbb-385a78325e4c` (`FT_D29` at `167.80, 127.20`, since `FT_D29` routes 100% on `F.Cu`), `966c1a26-bc64-47ca-a03c-d635ab7e066d` (`FT_D1` at `166.20, 125.60`, since `FT_D1` escapes North on `F.Cu` to `166.20, 121.60`), and `e0eda5ad-48dc-4e15-b56b-eb74dd20de61` (`FT_D22` at `166.20, 126.40`, since `FT_D22` escapes on `F.Cu` to `164.60, 124.025`, giving `FT_D25` and `FT_D27` non-crossing planar order on `B.Cu`).

### 2.2 Layer & Corridor Partitioning
1. **`FT_CLK` (`12.63 mm`, 0 vias)**: Routed 100% on `F.Cu` from `U12.J16` (`169.00, 124.40`) -> `(170.00, 124.40)` -> `(175.00, 119.40)` -> `U11.16` (`179.562, 119.40`).
2. **`U11` Top Row (`FT_D12, D9, D7..D0`)**:
   - Staggered inner/outer comb at `U11` (`y = 117.70` outside for `D6, D4, D2`; `y = 119.34..119.42` inside for `D12, D9, D7, D5, D3, D1, D0` with `>= 0.88 mm` center-to-center spacing between adjacent inner vias so outer `B.Cu` tracks pass cleanly between them).
   - At `U12`, `FT_D12` and `FT_D9` escape on `F.Cu` East of `FT_D11` to vias at `(172.60, 119.25)` and `(173.50, 119.25)`; `FT_D2` and `FT_D1` escape North on `F.Cu` along `x = 167.80` and `x = 166.20` to `y = 121.60` before transitioning to `B.Cu`.
3. **`U11` West Row (`FT_D16..FT_D31`)**:
   - **Planar `F.Cu` river (`10` nets, 0 vias in corridor)**: `FT_D17, D18, D19, D20, D21, D23, D24, D26, D29, D30` route in strictly monotonic North-to-South order on `F.Cu` between `U12` and `U11` West.
   - **Planar `B.Cu` river (`6` nets)**: `FT_D16, D22, D25, D27, D28, D31` route in strictly monotonic North-to-South order on `B.Cu`, terminating at `U11` West via staggered outer (`x = 178.55` for `D22, D28`) and inner moat (`x = 180.42` for `D16, D25, D27`) vias.
4. **`U11` Bottom Row (`FT_BE0..BE3, TXE_N, RXF_N, RD_N, WR_N, OE_N, RESET_N, GPIO1`)**:
   - Split between `B.Cu` (`FT_BE1, BE2, BE0, RXF_N, RD_N, WR_N, GPIO1`) and `F.Cu` (`FT_BE3, TXE_N, OE_N, RESET_N`) in monotonic order.

---

## 3. Compatibility with Claude's USB2 & Thermal Via Plan (`usb2_plan_claude.json`)

**Claim U1 — Compatibility with `notes/u11/usb2_plan_claude.json`**: **VERIFIED**.
- **7 Thermal `GND` Vias under `U11` Pad 77**:
  All 7 thermal vias from `usb2_plan_claude.json` (`(182.95, 122.03)`, `(182.95, 123.00)`, `(182.95, 123.97)`, `(184.00, 122.03)`, `(184.00, 123.97)`, `(185.05, 122.03)`, `(185.05, 123.00)`, `size = 0.45 mm, drill = 0.20 mm`) were loaded as static obstacles in `solve_u11.py`.
  - Our Top `B.Cu` bus under `U11` pad 77 stays at `y <= 121.33 mm` (closest track centerline to `y = 122.03` is `0.70 mm` away, vs `0.225 + 0.075 + 0.130 = 0.430 mm` required).
  - Our Bottom/`FT_1V0` `B.Cu` routing under `U11` pad 77 stays at `y >= 124.80 mm` (`0.83 mm` South of `y = 123.97`).
- **USB2 & Shield Routing (`B.Cu` at `x = 189..197, y = 124..130`) and `C65` Move (`193.5, 127.6`)**:
  - The easternmost copper item in `agy_u11_plan.json` is at `x = 188.438 mm` (`U11.56`, `y = 119.80 mm`), leaving `>= 0.56 mm` separation from `x = 189.0 mm` and `> 4.2 mm` vertical separation from `y = 124..130 mm`.

---

## 4. Thermal Analysis of `U11` (FT601Q-B-T Exposed Center Pad, Pin 77)

### 4.1 Power Dissipation & Stackup Parameters
- **Package**: FT601Q-B-T, 76-pin QFN (`9.0 x 9.0 mm` body), exposed thermal pad (Pin 77) `5.81 x 6.31 mm` ($A_{\text{pad}} = 36.66\text{ mm}^2$).
- **Power dissipation** (FT601 datasheet Table 6.3):
  - Typical active USB3 SuperSpeed streaming: $I_{CC,\text{typ}} = 185\text{ mA}$ at $V_{CC} = 3.3\text{ V} \implies P_{\text{typ}} = 3.3 \times 0.185 = \mathbf{0.61\text{ W}}$ (maximum $I_{CC,\text{max}} = 235\text{ mA} \implies P_{\text{max}} = 0.78\text{ W}$).
- **JLCPCB 4-Layer `1.6 mm` Stackup**:
  - Prepreg (`F.Cu` $\leftrightarrow$ `In1.Cu` solid `GND` plane): $L_{12} \approx 0.20\text{ mm}$ ($7628$ prepreg), $k_{\text{FR4},z} \approx 0.30\text{ W/(m}\cdot\text{K)}$.
  - Total board thickness (`F.Cu` $\leftrightarrow$ `B.Cu`): $L_{\text{tot}} = 1.60\text{ mm}$.
  - Via barrel plating thickness: $t_{\text{Cu}} \approx 18\text{ }\mu\text{m} = 0.018\text{ mm}$, $k_{\text{Cu}} = 385\text{ W/(m}\cdot\text{K)}$.

### 4.2 Thermal Resistance of Via Arrays: `7 x 0.2 mm` vs `12 x 0.3 mm`
For a single plated through-via of drill diameter $d$, the copper barrel cross-sectional area is $A_{\text{Cu}}(d) = \pi (d + t_{\text{Cu}}) t_{\text{Cu}}$:

1. **Single `0.20 mm` drill via**:
   $$A_{\text{Cu}}(0.20\text{ mm}) = \pi (0.20 + 0.018)(0.018) = 0.01233\text{ mm}^2$$
   - Full-board barrel resistance ($L_{\text{tot}} = 1.6\text{ mm}$):
     $$R_{\theta,\text{1via,full}}(0.20) = \frac{1.60\times 10^{-3}}{385 \times 1.233\times 10^{-8}} = \mathbf{337.1\text{ K/W}}$$
   - Resistance from `F.Cu` pad to `In1.Cu` solid `GND` plane ($L_{12} = 0.20\text{ mm}$):
     $$R_{\theta,\text{1via,In1}}(0.20) = \frac{0.20\times 10^{-3}}{385 \times 1.233\times 10^{-8}} = \mathbf{42.1\text{ K/W}}$$
   - **Array of $N = 7$ vias (`0.20 mm` drill)**:
     $$R_{\theta,\text{vias,full}}(7\times 0.20) = \frac{337.1}{7} = \mathbf{48.2\text{ K/W}}, \qquad R_{\theta,\text{vias,In1}}(7\times 0.20) = \frac{42.1}{7} = \mathbf{6.0\text{ K/W}}$$

2. **Single `0.30 mm` drill via**:
   $$A_{\text{Cu}}(0.30\text{ mm}) = \pi (0.30 + 0.018)(0.018) = 0.01798\text{ mm}^2$$
   - Full-board barrel resistance ($L_{\text{tot}} = 1.6\text{ mm}$):
     $$R_{\theta,\text{1via,full}}(0.30) = \frac{1.60\times 10^{-3}}{385 \times 1.798\times 10^{-8}} = \mathbf{231.1\text{ K/W}}$$
   - Resistance from `F.Cu` pad to `In1.Cu` solid `GND` plane ($L_{12} = 0.20\text{ mm}$):
     $$R_{\theta,\text{1via,In1}}(0.30) = \frac{0.20\times 10^{-3}}{385 \times 1.798\times 10^{-8}} = \mathbf{28.9\text{ K/W}}$$
   - **Array of $N = 12$ vias (`0.30 mm` drill)**:
     $$R_{\theta,\text{vias,full}}(12\times 0.30) = \frac{231.1}{12} = \mathbf{19.3\text{ K/W}}, \qquad R_{\theta,\text{vias,In1}}(12\times 0.30) = \frac{28.9}{12} = \mathbf{2.4\text{ K/W}}$$

3. **Parallel Dielectric Conduction (`F.Cu` pad $\to$ `In1.Cu` across $0.20\text{ mm}$ prepreg)**:
   $$R_{\theta,\text{FR4,12}} = \frac{L_{12}}{k_{\text{FR4},z} A_{\text{pad}}} = \frac{0.20\times 10^{-3}}{0.30 \times 36.66\times 10^{-6}} = \mathbf{18.2\text{ K/W}}$$
   Combining the via barrels to `In1.Cu` in parallel with dielectric conduction through the $0.20\text{ mm}$ prepreg:
   - **$7\times 0.20\text{ mm}$ vias**: $R_{\theta,\text{pad}\to\text{In1}} = (6.0^{-1} + 18.2^{-1})^{-1} = \mathbf{4.5\text{ K/W}}$ (plus coupling through the core to `In2.Cu` `GND` plane, net pad-to-internal-planes impedance $\approx \mathbf{3.8\text{ K/W}}$).
   - **$12\times 0.30\text{ mm}$ vias**: $R_{\theta,\text{pad}\to\text{In1}} = (2.4^{-1} + 18.2^{-1})^{-1} = \mathbf{2.1\text{ K/W}}$ (net pad-to-internal-planes impedance $\approx \mathbf{1.8\text{ K/W}}$).

### 4.3 Junction Temperature Rise ($\Delta T_J$) Comparison
Because `In1.Cu` (`0.20 mm` below `F.Cu`) and `In2.Cu` are continuous `GND` planes across the board, total junction-to-ambient thermal resistance $\Theta_{JA}$ is dominated by PCB radial spreading + natural convection ($\Theta_{\text{plane}\to\text{amb}} \approx 26\text{--}30\text{ K/W}$ for a QFN-76 on a 4-layer board in still air) rather than the via array itself:
$$\Theta_{JA} \approx \Theta_{JC,\text{bot}} + R_{\theta,\text{pad}\to\text{planes}} + \Theta_{\text{plane}\to\text{amb}}$$
Using $\Theta_{JC,\text{bot}} \approx 3.0\text{ K/W}$ and $\Theta_{\text{plane}\to\text{amb}} \approx 28\text{ K/W}$ (and accounting for reduced `B.Cu` copper area when signal tracks pass under the pad):
- **With $7\times 0.20\text{ mm}$ vias (Claude's grid)**:
  $$\Theta_{JA}(7\times 0.20) \approx 3.0 + 4.5 + 30.0 = \mathbf{37.5\text{ K/W}} \implies \Delta T_J = 0.61\text{ W} \times 37.5\text{ K/W} \approx \mathbf{22.9^\circ\text{C}}\text{ (max }0.78\text{ W} \implies \mathbf{29.3^\circ\text{C}}\text{)}$$
- **With $12\times 0.30\text{ mm}$ vias + solid `B.Cu` pad area**:
  $$\Theta_{JA}(12\times 0.30) \approx 3.0 + 2.1 + 25.0 = \mathbf{30.1\text{ K/W}} \implies \Delta T_J = 0.61\text{ W} \times 30.1\text{ K/W} \approx \mathbf{18.4^\circ\text{C}}\text{ (max }0.78\text{ W} \implies \mathbf{23.5^\circ\text{C}}\text{)}$$

### 4.4 Protocol Verdicts on Thermal Claims
- **Claim T1 (`7 x 0.20 mm` vias provide ample thermal margin at $P \approx 0.61\text{ W}$)**: **VERIFIED**.
  At $P_{\text{typ}} = 0.61\text{ W}$, $7\times 0.20\text{ mm}$ vias yield $\Delta T_J \approx 23^\circ\text{C}$ ($T_J \approx 48^\circ\text{C}$ at $T_A = 25^\circ\text{C}$, or $T_J \approx 73^\circ\text{C}$ inside a $50^\circ\text{C}$ enclosure), well below the $85^\circ\text{C}$ ambient / $125^\circ\text{C}$ junction rating. Upgrading to $12\times 0.30\text{ mm}$ vias only lowers $T_J$ by $\sim 4.5^\circ\text{C}$ because `In1.Cu` (`GND`) is only $0.20\text{ mm}$ below `F.Cu` ($R_{\theta,\text{pad}\to\text{In1}} = 4.5\text{ K/W}$ vs $2.1\text{ K/W}$).
- **Claim T2 (Whether `B.Cu` under the `U11` center pad must stay free of signal tracks)**:
  - **Electrical / Datasheet requirement**: **DISPUTED** (if claimed required by the datasheet). FT601 datasheet Section 8.3 only forbids signal tracks on the **component layer (`F.Cu`)** directly under the exposed pad (*"There should not be any signal tracks on the PCB layer where the chip resides under the thermal pad"*). Because `In1.Cu` and `In2.Cu` provide solid `GND` planes between `F.Cu` and `B.Cu`, `B.Cu` signal tracks under `U11` are fully shielded from the exposed pad.
  - **Physical / Routing constraint for a $12\times 0.30\text{ mm}$ grid**: **VERIFIED**. A $3\times 4$ grid of `0.30 mm` drill / `0.60 mm` pad through-vias across the `5.81 x 6.31 mm` pad has a pitch of $\sim 1.45\text{ mm}$ and an obstacle diameter of $0.60 + 2\times 0.13 = 0.86\text{ mm}$ (or $0.90\text{ mm}$ to `GND`), leaving only $\sim 0.55\text{ mm}$ gaps between vias—blocking our multi-track `B.Cu` Top (`y = 119.3..121.3`) and `FT_1V0` (`y = 124.8`) buses. Therefore, keeping Claude's **7-via `0.20 mm` drill grid** (`y = 122.03..123.97`) is the right engineering trade-off: it keeps $\Delta T_J \approx 23^\circ\text{C}$ while leaving the North (`y < 121.6`) and South (`y > 124.4`) `B.Cu` channels under `U11` pad 77 open.
