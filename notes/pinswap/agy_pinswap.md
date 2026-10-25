# Round 5: FPGA Bus Ball Assignment & BGA Escape Capacity (`usb3-sdr`)

**Author:** AGY (Antigravity)  
**Target:** LFE5U-25F-6BG256C (`U12`, CABGA256, $16\times 16$, $0.8\text{ mm}$ pitch) $\leftrightarrow$ FT601Q (`U11`) & AD9649 (`U8`)  
**Deliverables:** `notes/pinswap/agy_assignment.json`, `notes/pinswap/agy_pinswap.md`, `notes/pinswap/agy_check.py`

---

## Executive Summary Table

| Item | Claim / Task | Verdict | Key Quantitative Result |
| :--- | :--- | :---: | :--- |
| **C1** | Current FT601 bus has **237** straight-line crossings | **VERIFIED** | Exact reproduction: **237** crossings across $\binom{46}{2}=1035$ pairs (226 non-CLK + 11 with `FT_CLK`). Current ADC bus has **70** crossings in `data.json` (**60** with `R41.2` for `ADC_OR`). |
| **C2** | Fan-out via channel arithmetic ($0.35\text{ mm}$ vs $0.404\text{ mm}$; $0.18\text{ mm}$ pad-to-via) | **VERIFIED** | $G_{\text{via-via}} = 0.800 - 0.450 = \mathbf{0.350\text{ mm}} < 0.404\text{ mm}$ ($54\text{ }\mu\text{m}$ deficit $\implies 0$ tracks). $G_{\text{pad-via}} = 0.4\sqrt{2} - 0.160 - 0.225 = \mathbf{0.1807\text{ mm}} < 0.404\text{ mm}$. On `F.Cu` (no via in quad), $G_{\text{pad-pad}} = 0.800 - 0.320 = \mathbf{0.480\text{ mm}} \ge 0.404\text{ mm}$ (**1 track/gap**). |
| **T3** | Two-layer BGA escape capacity (a) current rules, (b) smaller vias/tracks, (c) FT601 & ADC feasibility | **DERIVED** | **(a)** Rings 0+1 (`F.Cu`) + Ring 2 (`B.Cu`, no outer signal vias blocking it!) escape **46 signals** in Banks 2+3 ($16+15+15$) and **24 signals** in Bank 7 ($8+8+8$), plus **+3 tracks** through the $1.150\text{ mm}$ BGA-center midline highway and **+2 net signals** per omitted Ring-2 via (up to **56** in Banks 2+3). **(b)** $0.35/0.15\text{ mm}$ vias fit 1 track/gap (**56** in B2+3, **29** in B7); $0.30/0.15\text{ mm}$ vias with $0.10/0.10\text{ mm}$ rules fit 2 tracks/gap (**all 64** in B2+3, **all 32** in B7). **(c) YES** for both buses under both (a) and (b). |
| **T1** | FT601 46-signal bus assignment in Banks 2+3 (`ft_clk` on true PCLK) | **SOLVED** | `ft_clk` on **`J16` (`PCLKT2_1`)**. Primary (`agy_assignment.json`): **0 crossings among all 45 non-CLK nets**, **6 total straight-line crossings** (down from **237**, $-97.5\%$), **0 intra-layer crossings on `F.Cu` (30 nets) and 0 on `B.Cu` (16 nets incl. `ft_clk`)**. Also provided: **Pure R012** (0 Ring $\ge 3$ balls, 11 CLK crossings) and **3-Crossing Global Minimum**. |
| **T2** | ADC 19-signal bus assignment in Bank 7 (`adc_dco` on true PCLK) + Bank 6 evaluation | **SOLVED** | `adc_dco` on **`J1` (`PCLKT7_1`)**. Primary (`agy_assignment.json`): **0 straight-line crossings (`0` across all 19 nets, down from 70!)**, **0 on `F.Cu`**, **0 on `B.Cu`**, 100% escapable under T3(a)/(b). Also provided: **R41.2-endpoint 0-crossing map**, **Pure R012** (0 Ring $\ge 3$ balls), and **Bank 6 Proposal** (saves **$92.2\text{ mm}$ [$18.6\%$]** wirelength). |
| **C3** | Buck converter (`TPS62A02`) $0.2\text{ mm}\times 0.6\text{ mm}$ `SW` neck at $2\text{ A}$ peak / $1\text{ A}$ avg | **VERIFIED** | Acceptable. $R_{\text{SW}} = \mathbf{1.48\text{ m}\Omega}$ ($25^\circ\text{C}$) / $\mathbf{1.68\text{ m}\Omega}$ ($60^\circ\text{C}$); $\Delta V = \mathbf{1.48\text{ mV}}$ @ $1\text{ A}$, $\mathbf{3.36\text{ mV}}$ @ $2\text{ A}$ ($P = 6.72\text{ mW}$). Because $L = 0.6\text{ mm} \ll \ell_{\text{heal}} = 3.1\text{ mm}$ ($\tau_{\text{th}} = 0.33\text{ ms}$), axial conduction to the pad + $0.6\text{ mm}$ trace limits local excess $\Delta T_{\text{neck}}$ to **$0.19\text{–}0.75\text{ K}$** @ $2\text{ A}$. FR-4 DC fusing $\ge \mathbf{6.0\text{ A}}$ ($10\text{ ms}$ fault fusing $20.2\text{ A} \gg 2.4\text{–}3.2\text{ A}$ IC limit). |
| **C4** | USB 2.0 HS ($480\text{ Mb/s}$) uncoupled $0.2\text{ mm}$ D+/D- tracks ($10\text{–}14\text{ mm}$, 2 vias) | **VERIFIED** | Acceptable (with 2 return-path/skew caveats). $\varepsilon_{\text{eff}} = \mathbf{3.21}$, $Z_0 = \mathbf{65.8\text{–}67.3\text{ }\Omega}$, $\tau_{\text{pd}} = \mathbf{5.97\text{ ps/mm}} \implies t_{\text{pd}} = \mathbf{59.7\text{–}83.6\text{ ps}}$ ($2 t_{\text{pd}} = 119\text{–}167\text{ ps} \le t_r / 3$ for $t_r = 500\text{ ps}$). Step $\Gamma_\infty = +0.188$ ($-14.5\text{ dB}$); finite-rise peak reflection $\mathbf{4.5\%\text{–}6.3\%} < 10\%$. Full-barrel L1$\leftrightarrow$L4 transition has **$\mathbf{0.00\text{ mm}}$ via stub**. |
| **C5** | Do `B.Cu` nets cross `In2.Cu` split boundaries (`1V1` / `3V3_D` / `1V8_A`)? | **VERIFIED** | **Yes — inevitably.** Because `1V1` ($[155.5..170.5, 116.5..131.5]$) completely encloses `U12` ($[157.0..169.0, 118.0..130.0]$), **100% of `B.Cu` dog-bone escapes from `U12` cross the `1V1` boundary**. Furthermore, `U8` $(141, 141)$ lies South of `1V8_A` ($y \le 134$) over bare `In2.Cu` unless `in2_gnd_fill.py` is run. Shrink `1V1` on `In2.Cu` to the core ball ring $[160.2..165.0, 121.6..126.8]$. |

---

## 1. BGA Escape Capacity Analysis (Task T3 & Claim C2)

### 1.1 Verification of Claim C2: Channel Geometry Arithmetic (`VERIFIED`)

From `kicad/gen/pcb_build.py:219-245`, `U12` (`CABGA256`) has ball pitch $p = 0.800\text{ mm}$, SMD pad diameter $d_{\text{pad}} = 0.320\text{ mm}$ ($r_{\text{pad}} = 0.160\text{ mm}$), and interstitial dog-bone vias at $(x_{\text{ball}} \pm 0.400, y_{\text{ball}} \pm 0.400)\text{ mm}$ with via pad diameter $d_v = 0.450\text{ mm}$ ($r_v = 0.225\text{ mm}$) and drill $d_{\text{drill}} = 0.200\text{ mm}$. Default routing rules are track width $w = 0.150\text{ mm}$ and copper-to-copper clearance $c = 0.127\text{ mm}$.

To route $k$ parallel tracks of width $w$ with clearance $c$ between two obstacles separated by edge-to-edge gap $G$, the required gap is:
$$G_{\text{req}}(k) = k\,w + (k + 1)\,c \implies G_{\text{req}}(1) = 0.150 + 2(0.127) = \mathbf{0.404\text{ mm}}$$

Checking the three elementary channels on `U12`:
1. **Via-to-via orthogonal channel (`B.Cu` and `F.Cu`):**
   $$G_{\text{via-via}} = p - d_v = 0.800 - 0.450 = \mathbf{0.350\text{ mm}} < 0.404\text{ mm} \quad (\text{deficit } = 54\text{ }\mu\text{m} \implies \mathbf{0\text{ tracks}})$$
2. **Ball-pad-to-interstitial-via diagonal channel (`F.Cu`):**
   $$G_{\text{pad-via}} = \sqrt{0.400^2 + 0.400^2} - r_{\text{pad}} - r_v = 0.5657 - 0.160 - 0.225 = \mathbf{0.1807\text{ mm}} \approx 0.18\text{ mm} < 0.404\text{ mm}$$
   Even if the via pad is shrunk to $d_v = 0.300\text{ mm}$, $G_{\text{pad-via}} = 0.5657 - 0.160 - 0.150 = 0.2557\text{ mm} < 0.300\text{ mm}$. Thus **any interstitial via inside a $2\times 2$ ball quad completely blocks `F.Cu` routing through that quad**.
3. **Ball-pad-to-ball-pad orthogonal channel (`F.Cu`, no interstitial via in quad):**
   Because `RINGS_DIRECT = 2` (`pcb_build.py:220`) places **no vias** on Ring 0 or Ring 1 signal balls, the orthogonal gap between adjacent Ring 0 pads on `F.Cu` is:
   $$G_{\text{pad-pad}} = p - d_{\text{pad}} = 0.800 - 0.320 = \mathbf{0.480\text{ mm}} \ge 0.404\text{ mm} \quad (\text{surplus } = 76\text{ }\mu\text{m} \implies \mathbf{1\text{ track/gap}})$$
   *(Note: for 2 tracks at $w=0.10\text{ mm}, c=0.10\text{ mm}$, $G_{\text{req}}(2) = 2(0.10) + 3(0.10) = 0.500\text{ mm} > 0.480\text{ mm}$, so $G_{\text{pad-pad}}$ always carries at most **1 track** across all candidates in T3).*

> [!WARNING]
> **Bug Found in `kicad/gen/pcb_build.py:228`:**  
> Line 228 checks `if not pad.GetNetname(): continue` to skip unused balls when placing dog-bone vias. However, KiCad assigns unconnected pads the non-empty netname `"unconnected-(U12...)"` (`bool("unconnected-...") == True`)! As a result, `pcb_build.py` placed **83 locked dog-bone vias on unconnected balls** in Rings 2–4, unnecessarily walling off `B.Cu` escape channels. Fix line 228 to:
> ```python
> net = pad.GetNetname()
> if not net or net.startswith("unconnected-"):
>     continue
> ```

---

### 1.2 Task T3(a): Two-Layer Escape Capacity with Current Vias ($0.45/0.20\text{ mm}$, $w=0.15\text{ mm}, c=0.127\text{ mm}$)

On a 2-signal-layer board (`F.Cu` + `B.Cu`), total escape capacity is the sum of independent capacities on `F.Cu` and `B.Cu`:

1. **`F.Cu` Capacity (Rings 0 and 1, `RINGS_DIRECT = 2`):**
   - **Ring 0:** Escapes directly outward from the package perimeter ($N_{\text{R0}}$ signals).
   - **Ring 1:** Escapes outward through the $0.480\text{ mm}$ inter-pad channels between adjacent Ring 0 balls (1 track per open Ring-0 gap, minus any gap blocked by a Ring 0 or Ring 1 power/GND dog-bone via).
   - **Idealized 16-ball side:** $16\text{ (Ring 0)} + 14\text{ (Ring 1)} = \mathbf{30\text{ signals/side on F.Cu}}$.
   - **Actual `U12` Banks 2+3 (East + South-East perimeter):** Has **16 Ring 0 IO balls** (`B16..G16, J16..R16, T13..T15`) and **15 Ring 1 IO balls** (`B15, C15, E15..M15, P15, R12..R15`). Out of the 19 perimeter gaps spanning `A16..T16..T12`, only 3 interior gaps are blocked by GND vias (`D15`, `H16`, `N15`), leaving **16 open `F.Cu` channels** for the **15 Ring 1 IO balls**. Thus **all $16 + 15 = \mathbf{31}$ Ring 0 & Ring 1 balls in Banks 2+3 escape on `F.Cu`**.
   - **Actual `U12` Bank 7 (West upper perimeter, `B1..K3`):** Has **8 Ring 0 IO balls** (`B1..G1, J1, K1`) and **8 Ring 1 IO balls** (`B2, C2, E2..K2`). With `D2 (GND)` and `H1 (GND)` blocking 2 gaps, there are 8 open `F.Cu` channels (including the top gap above `B1` next to `A1`), so **all $8 + 8 = \mathbf{16}$ Ring 0 & Ring 1 balls in Bank 7 escape on `F.Cu`**.

2. **`B.Cu` Capacity (Rings $\ge 2$, via dog-bones):**
   - **Crucial observation:** On `B.Cu`, the SMD BGA ball pads do not exist; **only vias are obstacles**. Because Rings 0 and 1 have **no signal vias**, the **outermost ring of signal vias (Ring 2)** has *no signal vias outside it* and escapes directly outward on `B.Cu` without passing between adjacent signal vias! (Where Ring 1 GND vias `D15`, `N15`, `D2` sit $0.8\text{ mm}$ outside `D14`, `N14`, `D3`, the diagonal distance to the adjacent Ring 2 via is $0.8\sqrt{2} = 1.131\text{ mm}$, giving an edge-to-edge gap of $1.131 - 0.450 = \mathbf{0.681\text{ mm}} \ge 0.404\text{ mm}$, which easily passes 1 track; and in the SE corner, `P11..P13` exit via the unobstructed $1.150\text{ mm}$ horizontal highway along Row R between `P11..P14`'s vias at $y=128.8\text{ mm}$ and `T12, T16`'s GND vias at $y=130.4\text{ mm}$.)
   - Therefore, with **all Ring 2 balls used ($m = 0$ omitted Ring 2 balls)**, **100% of Ring 2 balls escape on `B.Cu`**:
     - **Idealized 16-ball side:** $12$ Ring 2 balls $\implies 30 + 12 = \mathbf{42\text{ signals/side}}$.
     - **Actual `U12` Banks 2+3:** **15 Ring 2 IO balls** (`C14..N14, P11..P14`) $\implies 31 + 15 = \mathbf{46\text{ signals}}$ in Rings 0–2 alone!
     - **Actual `U12` Bank 7:** **8 Ring 2 IO balls** (`C3..K3`) $\implies 16 + 8 = \mathbf{24\text{ signals}}$ in Rings 0–2 alone!
   - **Natural BGA-Center Midline Highway ($y = 124.0\text{ mm}$ and $x = 163.0\text{ mm}$):**
     Because `pcb_build.py:236-237` flips the dog-bone offset direction (`sx, sy = +0.4 if p >= c else -0.4`) across the package center $(163.0, 124.0)$, Row H ($y = 123.6$) places vias at $y = 123.2\text{ mm}$ while Row J ($y = 124.4$) places vias at $y = 124.8\text{ mm}$. Their center-to-center spacing is $2p = 1.600\text{ mm}$, creating a natural **$1.600 - 0.450 = \mathbf{1.150\text{ mm}}$ edge-to-edge corridor** between `H14` and `J14` (and between `H3` and `J3` in Bank 7) that fits:
     $$n_{\text{midline}} = \left\lfloor \frac{1.150 - 0.127}{0.150 + 0.127} \right\rfloor = \left\lfloor \frac{1.023}{0.277} \right\rfloor = \mathbf{3\text{ tracks on B.Cu}}$$
     even when every Ring 2 ball is populated!
   - **Capacity as a Function of Omitted Ring 2 Balls ($m$):**
     If $m$ isolated Ring 2 balls are left unused (no via placed), each omitted Ring 2 via removes $-1$ Ring 2 signal and opens a $2p - d_v = 1.150\text{ mm}$ window on `B.Cu` that carries **3 tracks** from Rings 3–4, yielding a **net gain of $+2\text{ signals}$ per omitted Ring 2 ball** (or if $m$ *consecutive* Ring 2 balls are omitted, a gap of $(m+1)p - d_v$ carrying $\lfloor((m+1)p - d_v - c)/(w+c)\rfloor$ tracks):
     $$C_{\text{B2+3}}(m) = 31_{\text{F.Cu}} + (15 - m)_{\text{R2}} + \min\!\left(18_{\text{R3+R4}},\; 3_{\text{midline}} + 3m\right) = \min\!\left(64 - m,\; 49 + 2m\right)$$
     For $m = 0$: **46 signals** (Rings 0–2 only) or **49 signals** (with midline highway). For $m = 5$ omitted Ring 2 vias: **56 signals** (all 46 signals easily escaped with 0 Ring 4 balls!).

---

### 1.3 Task T3(b) & T3(c): Capacity Table Across Via/Track/Clearance Candidates

For orthogonal inter-via pitch $p = 0.800\text{ mm}$, the edge-to-edge gap is $G_{\text{vv}} = 0.800 - d_v$, and the number of tracks per inter-via gap is:
$$n_{\text{vv}}(d_v, w, c) = \max\!\left(0,\; \left\lfloor \frac{0.800 - d_v - c}{w + c} \right\rfloor\right)$$

| Via Pad / Drill ($d_v / d_{\text{drill}}$) | Track / Clearance ($w / c$) | $G_{\text{vv}}$ ($\text{mm}$) | $G_{\text{req}}(1)$ ($\text{mm}$) | $G_{\text{req}}(2)$ ($\text{mm}$) | Tracks / Via Gap ($n_{\text{vv}}$) | Ideal 16-Ball Side Capacity | Actual `U12` Banks 2+3 (max 64 IO) | Actual `U12` Bank 7 (max 32 IO) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **$0.45 / 0.20\text{ mm}$** *(current)* | $0.15 / 0.127\text{ mm}$ | $0.350$ | $0.404$ | $0.681$ | **0** | **42** *(46 w/ skip)* | **46** (R0–2) / **56\*** | **24** (R0–2) / **28\*** |
| **$0.45 / 0.20\text{ mm}$** | $0.10 / 0.100\text{ mm}$ | $0.350$ | $0.300$ | $0.500$ | **1** | **52** (R0–R3) | **56** (all R0–R3) | **29** (R0–R3 + 1) |
| **$0.40 / 0.20\text{ mm}$** | $0.15 / 0.127\text{ mm}$ | $0.400$ | $0.404$ | $0.681$ | **0** *(by $4\text{ }\mu\text{m}$)* | **42** *(46 w/ skip)* | **46** (R0–2) / **56\*** | **24** (R0–2) / **28\*** |
| **$0.40 / 0.20\text{ mm}$** | $0.10 / 0.100\text{ mm}$ | $0.400$ | $0.300$ | $0.500$ | **1** | **52** (R0–R3) | **56** (all R0–R3) | **29** (R0–R3 + 1) |
| **$0.35 / 0.15\text{ mm}$** | $0.15 / 0.127\text{ mm}$ | $0.450$ | $0.404$ | $0.681$ | **1** | **52** (R0–R3) | **56** (all R0–R3) | **29** (R0–R3 + 1) |
| **$0.35 / 0.15\text{ mm}$** | $0.10 / 0.100\text{ mm}$ | $0.450$ | $0.300$ | $0.500$ | **1** | **52** (R0–R3) | **56** (all R0–R3) | **29** (R0–R3 + 1) |
| **$0.30 / 0.15\text{ mm}$** | $0.15 / 0.127\text{ mm}$ | $0.500$ | $0.404$ | $0.681$ | **1** | **52** (R0–R3) | **56** (all R0–R3) | **29** (R0–R3 + 1) |
| **$0.30 / 0.15\text{ mm}$** | $0.10 / 0.100\text{ mm}$ | $0.500$ | $0.300$ | $0.500$ | **2** | **60** (R0–R4) | **64** (**100% R0–R4**) | **32** (**100% R0–R4**) |

*\*With the $1.150\text{ mm}$ BGA-center midline highway (3 tracks) and/or omitting $m$ Ring 2 vias once bug `pcb_build.py:228` is fixed.*

**Answer to Task T3(c):**
- **46-signal FT601 bus (Banks 2+3):** **YES, escapable on two layers under BOTH (a) and (b).** Under (a), Banks 2+3 contain $16\text{ (R0)} + 15\text{ (R1)} + 15\text{ (R2)} = \mathbf{46}$ balls in Rings 0–2 alone (plus the 3-track midline highway at $y=124.0\text{ mm}$ and open Ring 2 windows when any Ring 2 balls are traded for Ring 3 balls). Under (b), capacity rises to **56 signals** ($n_{\text{vv}}=1$) or **all 64 signals** ($n_{\text{vv}}=2$).
- **19-signal ADC bus (Bank 7):** **YES, escapable on two layers under BOTH (a) and (b).** Under (a), Bank 7 contains $8\text{ (R0)} + 8\text{ (R1)} + 8\text{ (R2)} = \mathbf{24} > 19$ balls in Rings 0–2 alone, and when only 4 of the 8 Ring 2 balls are used, the 4 unused Ring 2 slots (`C3..F3`) plus the $1.150\text{ mm}$ `H3`–`J3` midline highway and empty Bank 6 interior (`K4, L3, M3`) allow up to **28 signals** to escape under (a) (and **29 to 32 signals** under (b)).

---

## 2. Task T1: FT601 Bus Assignment (46 Signals in Banks 2 & 3)

### 2.1 Diagnosis of the 237 Crossings & Geometric Lower Bound

1. **Why the current LPF has 237 crossings (Claim C1 — `VERIFIED`):**
   Evaluating all $\binom{46}{2} = 1035$ pairs of straight-line segments from `U11` pad centers to `U12` ball centers in `data.json` yields **exactly 237 proper intersections** (226 among the 45 non-CLK nets + 11 with `FT_CLK`).  
   **Root cause:** The current assignment actually picked the exact 46 balls of Rings 0, 1, and 2 (`R012`), but swept **down Ring 0 (`B16..J16`), then jumped back up to the top of Ring 1 (`B15..K15`), then jumped back up to the top of Ring 2 (`C14..K14`)** instead of sweeping monotonically by angle across all three rings together! Furthermore, `FT_D0..15` on `U11`'s North edge (pins 40..57, $y = 118.562\text{ mm}$) run **East-to-West** ($x = 187.2 \to 180.4\text{ mm}$), whereas `B16..C14` are at the North-West, inverting the entire 16-bit upper fan.

2. **Exact Hall's Marriage Theorem / Cut-Line Proof for `FT_CLK`:**
   - The 45 non-CLK pins on `U11` march clockwise around `U11`'s North, West, and South perimeter:
     - **North edge ($y = 118.562\text{ mm}$, West to East):** `FT_D15` ($x=180.4$) $\to$ `FT_D0` ($x=187.2$) [16 nets]
     - **West edge ($x = 179.562\text{ mm}$, North to South):** `FT_D16` ($y=120.2$) $\to$ `FT_D31` ($y=126.6$) [16 nets]
     - **South edge ($y = 127.438\text{ mm}$, West to East):** `FT_BE0` ($x=181.6$) $\to$ `FT_GPIO1` ($x=187.2$) [13 nets]
   - Matching any 45 Bank 2/3 balls in monotonic angular order to this 45-net perimeter sequence gives **0 crossings among all 45 non-CLK nets** (which immediately implies **0 intra-layer crossings on `F.Cu`** and **0 intra-layer crossings on `B.Cu`**!).
   - For `ft_clk` (Hard Constraint 2: must be on a true PCLK in `{K16, J16, M16, L16}`), the highest true PCLK is **`J16` (`PCLKT2_1`)** at $(169.0, 124.4)\text{ mm}$, while `U11` pin 58 (`FT_CLK`) is at $(179.562, 119.4)\text{ mm}$ (top of `U11`'s West edge).
   - Across all 63 remaining Bank 2/3 IO balls, **at most 33 balls** lie below the line through `J16` and `FT_CLK` (25 in Rings 0–2, 5 in Ring 3, 3 in Ring 4), so at least $45 - 33 = 12$ balls must lie above `J16`$\to$`FT_CLK`. Meanwhile, on `U11`'s North edge ($y = 118.562$), rays from the top of Bank 2 (`B16..E16`) pass above `FT_CLK` $(179.562, 119.4)$ for the first **9** North-edge pins (`FT_D15..FT_D7`). Thus by Hall's Marriage Theorem, the **exact mathematical minimum** straight-line crossing count over all $\binom{63}{45}\times 45!$ assignments in Banks 2+3 is:
     - **$12 - 9 = \mathbf{3\text{ crossings}}$** across all 64 Bank 2/3 balls (`T1 Alt-C`, using 4 Ring 4 balls),
     - **$15 - 9 = \mathbf{6\text{ crossings}}$** with 0 Ring 4 balls (`T1 Primary` in `agy_assignment.json`, where **all 6 crossings with `FT_CLK` are Ring 0/1 balls on `F.Cu`**, so routing `FT_CLK` on `B.Cu` gives **0 crossings on `F.Cu` and 0 crossings on `B.Cu`**!),
     - **$20 - 9 = \mathbf{11\text{ crossings}}$** when restricted strictly to the 46 balls of Rings 0, 1, 2 (`T1 Alt-B Pure R012`, 0 Ring 3/4 balls).

3. **Bus Skew Verification (Hard Constraint 3):**
   In `T1 Primary`, segment lengths span $\ell \in [11.0\text{ mm}, 22.8\text{ mm}]$ ($\Delta \ell_{\max} = 11.8\text{ mm}$). At $\tau_{\text{pd}} \approx 6.0\text{ ps/mm}$, the maximum flight-time skew across the entire 46-bit bus is $\Delta t_{\text{skew}} \approx \mathbf{71\text{ ps}}$ ($0.71\%$ of the $10.0\text{ ns}$ period at $100\text{ MHz}$), confirming that bit-to-ball permutation has zero timing impact when using ECP5 IO cell registers.

---

### 2.2 Complete T1 Assignment Table (`agy_assignment.json` Primary + Alternatives)

- **`T1 Primary` (`agy_assignment.json`):** Uses 16 Ring 0 + 15 Ring 1 (`F.Cu`) + 10 Ring 2 + 5 Ring 3 (`B.Cu`) = 46 balls (**0 Ring 4 balls**). Omits 5 consecutive Ring 2 balls (`E14..J14`) to open a **$5.150\text{ mm}$ (18-track) `B.Cu` window** above `K14`. **Crossings:** **0 non-CLK**, **6 with `ft_clk`** (`F15, F16, G15, G16, H15, J15` — all in Rings 0–1 on `F.Cu`, so **0 crossings on `F.Cu` and 0 on `B.Cu`**!).
- **`T1 Alt-B (Pure R012)`:** Uses the **exact 46 Ring 0/1/2 balls** currently wired on the PCB (**0 Ring 3 or Ring 4 balls**). **Crossings:** **0 non-CLK**, **11 with `ft_clk`**.
- **`T1 Alt-C (Min-3)`:** Global minimum **3 crossings** (`0` non-CLK, `3` with `ft_clk`).

| Gateware Signal | Net Name | `U11` Pin | `U11` $(x, y)$ ($\text{mm}$) | **T1 Primary (`agy_assignment.json`)** | Primary Ring / Bank | **T1 Alt-B (`Pure R012`, 0 R3/4)** | **T1 Alt-C (`Min-3` Global)** |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `ft_clk` | `FT_CLK` | 58 | $(179.562, 119.400)$ | **`J16`** (`PCLKT2_1`) | R0 / B2 | `J16` (`PCLKT2_1`) | `J16` (`PCLKT2_1`) |
| `ft_data[15]` | `FT_D15` | 57 | $(180.400, 118.562)$ | **`B15`** | R1 / B2 | `B15` | `B15` |
| `ft_data[14]` | `FT_D14` | 56 | $(180.800, 118.562)$ | **`B16`** | R0 / B2 | `B16` | `B16` |
| `ft_data[13]` | `FT_D13` | 55 | $(181.200, 118.562)$ | **`C14`** | R2 / B2 | `C14` | `C14` |
| `ft_data[12]` | `FT_D12` | 54 | $(181.600, 118.562)$ | **`C15`** | R1 / B2 | `C15` | `C15` |
| `ft_data[11]` | `FT_D11` | 53 | $(182.000, 118.562)$ | **`C16`** | R0 / B2 | `C16` | `C16` |
| `ft_data[10]` | `FT_D10` | 52 | $(182.400, 118.562)$ | **`D14`** | R2 / B2 | `D14` | `D14` |
| `ft_data[9]` | `FT_D9` | 51 | $(182.800, 118.562)$ | **`D16`** | R0 / B2 | `D16` | `D16` |
| `ft_data[8]` | `FT_D8` | 50 | $(183.200, 118.562)$ | **`E15`** | R1 / B2 | `E14` | `E14` |
| `ft_data[7]` | `FT_D7` | 47 | $(184.400, 118.562)$ | **`E16`** | R0 / B2 | `E15` | `E15` |
| `ft_data[6]` | `FT_D6` | 46 | $(184.800, 118.562)$ | **`F15`** | R1 / B2 | `E16` | `E16` |
| `ft_data[5]` | `FT_D5` | 45 | $(185.200, 118.562)$ | **`F16`** | R0 / B2 | `F14` | `F12` |
| `ft_data[4]` | `FT_D4` | 44 | $(185.600, 118.562)$ | **`G15`** | R1 / B2 | `F15` | `F13` |
| `ft_data[3]` | `FT_D3` | 43 | $(186.000, 118.562)$ | **`G16`** | R0 / B2 | `F16` | `K15` |
| `ft_data[2]` | `FT_D2` | 42 | $(186.400, 118.562)$ | **`K15`** | R1 / B2 | `G14` | `L13` |
| `ft_data[1]` | `FT_D1` | 41 | $(186.800, 118.562)$ | **`L13`** | R3 / B3 | `G16` | `L12` |
| `ft_data[0]` | `FT_D0` | 40 | $(187.200, 118.562)$ | **`K16`** | R0 / B2 | `H14` | `K16` |
| `ft_data[16]` | `FT_D16` | 60 | $(179.562, 120.200)$ | **`H15`** | R1 / B2 | `G15` | `K14` |
| `ft_data[17]` | `FT_D17` | 61 | $(179.562, 120.600)$ | **`J15`** | R1 / B2 | `H15` | `M11` |
| `ft_data[18]` | `FT_D18` | 62 | $(179.562, 121.000)$ | **`K14`** | R2 / B2 | `J14` | `M12` |
| `ft_data[19]` | `FT_D19` | 63 | $(179.562, 121.400)$ | **`L14`** | R2 / B3 | `J15` | `L14` |
| `ft_data[20]` | `FT_D20` | 64 | $(179.562, 121.800)$ | **`L15`** | R1 / B3 | `K14` | `L15` |
| `ft_data[21]` | `FT_D21` | 65 | $(179.562, 122.200)$ | **`L16`** | R0 / B3 | `K15` | `L16` |
| `ft_data[22]` | `FT_D22` | 66 | $(179.562, 122.600)$ | **`M13`** | R3 / B3 | `K16` | `M13` |
| `ft_data[23]` | `FT_D23` | 67 | $(179.562, 123.000)$ | **`M14`** | R2 / B3 | `L14` | `M14` |
| `ft_data[24]` | `FT_D24` | 69 | $(179.562, 123.800)$ | **`M15`** | R1 / B3 | `L15` | `M15` |
| `ft_data[25]` | `FT_D25` | 70 | $(179.562, 124.200)$ | **`N11`** | R3 / B3 | `L16` | `N11` |
| `ft_data[26]` | `FT_D26` | 71 | $(179.562, 124.600)$ | **`M16`** | R0 / B3 | `M14` | `M16` |
| `ft_data[27]` | `FT_D27` | 72 | $(179.562, 125.000)$ | **`N12`** | R3 / B3 | `M15` | `N12` |
| `ft_data[28]` | `FT_D28` | 73 | $(179.562, 125.400)$ | **`N13`** | R3 / B3 | `M16` | `N13` |
| `ft_data[29]` | `FT_D29` | 74 | $(179.562, 125.800)$ | **`N14`** | R2 / B3 | `N14` | `N14` |
| `ft_data[30]` | `FT_D30` | 75 | $(179.562, 126.200)$ | **`N16`** | R0 / B3 | `N16` | `N16` |
| `ft_data[31]` | `FT_D31` | 76 | $(179.562, 126.600)$ | **`P11`** | R2 / B3 | `P11` | `P11` |
| `ft_be[0]` | `FT_BE0` | 4 | $(181.600, 127.438)$ | **`P12`** | R2 / B3 | `P12` | `P12` |
| `ft_be[1]` | `FT_BE1` | 5 | $(182.000, 127.438)$ | **`P13`** | R2 / B3 | `P13` | `P13` |
| `ft_be[2]` | `FT_BE2` | 6 | $(182.400, 127.438)$ | **`P14`** | R2 / B3 | `P14` | `P14` |
| `ft_be[3]` | `FT_BE3` | 7 | $(182.800, 127.438)$ | **`P15`** | R1 / B3 | `P15` | `P15` |
| `ft_txe_n` | `FT_TXE_N` | 8 | $(183.200, 127.438)$ | **`P16`** | R0 / B3 | `P16` | `P16` |
| `ft_rxf_n` | `FT_RXF_N` | 9 | $(183.600, 127.438)$ | **`R12`** | R1 / B3 | `R12` | `R12` |
| `ft_wr_n` | `FT_WR_N` | 11 | $(184.400, 127.438)$ | **`R13`** | R1 / B3 | `R13` | `R13` |
| `ft_rd_n` | `FT_RD_N` | 12 | $(184.800, 127.438)$ | **`R14`** | R1 / B3 | `R14` | `R14` |
| `ft_oe_n` | `FT_OE_N` | 13 | $(185.200, 127.438)$ | **`R15`** | R1 / B3 | `R15` | `R15` |
| `ft_reset_n` | `FT_RESET_N` | 15 | $(186.000, 127.438)$ | **`R16`** | R0 / B3 | `R16` | `R16` |
| `ft_wakeup_n` | `FT_WAKEUP_N` | 16 | $(186.400, 127.438)$ | **`T13`** | R0 / B3 | `T13` | `T13` |
| `FT_GPIO0` | `FT_GPIO0` | 17 | $(186.800, 127.438)$ | **`T14`** | R0 / B3 | `T14` | `T14` |
| `FT_GPIO1` | `FT_GPIO1` | 18 | $(187.200, 127.438)$ | **`T15`** | R0 / B3 | `T15` | `T15` |

> [!TIP]
> **Routing Note on `FT_D[0..15]` (Under-QFN `B.Cu` vs. Exterior NW-Corner Arch):**  
> In `r2_deeppcb_routed.kicad_pcb`, `U11`'s central thermal pad (`pin 77`) is on `F.Cu` only (`['F.Cu', 'F.Mask']`, with no thermal vias), so `B.Cu` is open under `U11` and straight-line/southern entry into pins 40..57 (`FT_D15` topmost $\to$ `FT_D0` lower) is directly routable. If you later add thermal vias to `U11` pad 77 so `FT_D[0..15]` must exit **North** ($y < 118.562\text{ mm}$) and arch around `U11`'s North-West corner, simply reverse the 16-element slice `ft_data[15..0]` onto the same 16 balls (`ft_data[0] -> B15`, `ft_data[1] -> B16`, ..., `ft_data[15] -> K16`), which gives **0 perimeter crossings** for exterior NW-corner routing.

---

## 3. Task T2: ADC Bus Assignment (19 Signals in Bank 7) & Bank 6 Proposal

### 3.1 Diagnosis & Zero-Crossing Bank 7 Assignment

1. **Why the current Bank 7 assignment has 70 crossings (60 on PCB):**
   Besides non-monotonic ball ordering in `usb3sdr.lpf`, `spiral_place` in `pcb_build.py` placed `R40` (`ADC_DCO`) at **`(137.301, 147.395)`** (South-West of `U8`), even though `U8` pin 22 (`ADC_DCO_R`) is on the **North edge** of `U8` at `(140.25, 138.562)`!
2. **Note on `extract.py:42` (`R41` Omission):**
   In `notes/pinswap/extract.py:42`, `for i in range(26, 41)` stopped at `R40` and omitted **`R41`** (which carries `ADC_OR` at pad 2 `xy = [148.317, 138.038]`), so `data.json` fell back to `U8` pin 23 `[139.75, 138.562]` ($42.06^\circ$) instead of `R41` pad 2 `[148.317, 138.038]` ($60.00^\circ$).
3. **Exact Zero-Crossing Solutions in Bank 7 (`adc_dco` on `J1 = PCLKT7_1`):**
   Moving `adc_dco` from `K1` to **`J1` (`PCLKT7_1`)** splits Bank 7 across the line `J1 (157.0, 124.4) -> R40.2 (137.301, 147.395)` so that the number of Bank 7 balls on each side of `J1`$\to$`R40.2` matches the exact number of ADC nets on each side!
   - **`T2 Primary` (`agy_assignment.json`, using `data.json` endpoints):** Achieves **0 straight-line crossings (`0` across all 19 nets, `0` on `F.Cu`, `0` on `B.Cu`)**! On `B.Cu`, because 4 consecutive Ring 2 balls (`C3..F3`) and Bank 6's `K4, L3, M3` are unused (0 vias) and `H3`–`J3` has the $1.150\text{ mm}$ midline highway, all Ring 2–4 balls escape under **both T3(a) and T3(b)**: `F4, G4, G5` exit via the open `C3..F3` North window, `H4, H5` exit via the $1.150\text{ mm}$ `H3`–`J3` midline highway, and `J4, J5` exit via the open `K4, L3, M3` South window.
   - **`T2 Alt-A` (`R41.2` endpoint `[148.317, 138.038]` for `ADC_OR`):** Also achieves **0 straight-line crossings (`0` across all 19 nets)** on the actual PCB resistor coordinates!
   - **`T2 Alt-B` (`Pure R012`, 0 Ring $\ge 3$ balls):** Uses 7 Ring 0 + 8 Ring 1 + 4 Ring 2 = 19 balls (**0 balls in Rings 3–4**), achieving **0 non-DCO crossings** (`0` on `F.Cu`, `0` on `B.Cu`) and 7 crossings with `adc_dco`.

| Gateware Signal | Net Name | Source Endpoint in `data.json` ($\text{mm}$) | **T2 Primary (`agy_assignment.json`, 0 Crossings on `data.json`)** | Primary Ring / Bank | **T2 Alt-A (0 Crossings w/ `R41.2` for `ADC_OR`)** | **T2 Alt-B (`Pure R012`, 0 R3/4)** | **T2 Bank 6 Proposal (`L1` PCLK)** |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `adc_dco` | `ADC_DCO` | $(137.301, 147.395)$ (`R40.2`) | **`J1`** (`PCLKT7_1`) | R0 / B7 | `J1` (`PCLKT7_1`) | `J1` (`PCLKT7_1`) | `L1` (`PCLKT6_1`) |
| `adc_or` | `ADC_OR` | $(139.750, 138.562)$ (`U8.23`)\* | **`E1`** | R0 / B7 | `J3` *(for `R41.2`)* | `C1` | `L2` |
| `adc_d[6]` | `ADC_D6` | $(137.157, 144.549)$ (`R32.2`) | **`F1`** | R0 / B7 | `F1` | `B2` | `M1` |
| `adc_d[8]` | `ADC_D8` | $(136.985, 145.854)$ (`R34.2`) | **`G1`** | R0 / B7 | `G1` | `C2` | `M2` |
| `adc_csb` | `ADC_CSB` | $(140.750, 143.438)$ (`U8.20`) | **`H2`** | R1 / B7 | `H2` | `D1` | `L3` |
| `adc_sclk` | `ADC_SCLK` | $(141.250, 143.438)$ (`U8.19`) | **`G3`** | R2 / B7 | `G3` | `E2` | `M3` |
| `adc_d[2]` | `ADC_D2` | $(139.741, 145.325)$ (`R28.2`) | **`F4`** | R3 / B7 | `F4` | `E1` | `N1` |
| `adc_sdio` | `ADC_SDIO` | $(141.750, 143.438)$ (`U8.18`) | **`K1`** | R0 / B7 | `F5` | `F2` | `N3` |
| `adc_d[4]` | `ADC_D4` | $(145.937, 138.864)$ (`R30.2`) | **`J2`** | R1 / B7 | `K1` | `F1` | `P1` |
| `adc_d[1]` | `ADC_D1` | $(142.901, 145.467)$ (`R27.2`) | **`H3`** | R2 / B7 | `J2` | `G1` | `P2` |
| `adc_d[0]` | `ADC_D0` | $(146.010, 141.188)$ (`R26.2`) | **`G4`** | R3 / B7 | `H3` | `G2` | `P3` |
| `adc_d[3]` | `ADC_D3` | $(146.253, 142.771)$ (`R29.2`) | **`J3`** | R2 / B7 | `G4` | `G3` | `R1` |
| `adc_d[11]` | `ADC_D11` | $(148.321, 139.573)$ (`R37.2`) | **`K2`** | R1 / B7 | `K2` | `H2` | `R2` |
| `adc_d[5]` | `ADC_D5` | $(146.097, 144.222)$ (`R31.2`) | **`H4`** | R3 / B7 | `H4` | `H3` | `R3` |
| `adc_d[7]` | `ADC_D7` | $(145.681, 145.500)$ (`R33.2`) | **`K3`** | R2 / B7 | `K3` | `J2` | `T2` |
| `adc_d[10]` | `ADC_D10` | $(145.690, 146.802)$ (`R36.2`) | **`J4`** | R3 / B7 | `J4` | `J3` | `T3` |
| `adc_d[9]` | `ADC_D9` | $(148.510, 141.188)$ (`R35.2`) | **`G5`** | R4 / B7 | `G5` | `K1` | `R4` |
| `adc_d[12]` | `ADC_D12` | $(148.835, 142.800)$ (`R38.2`) | **`H5`** | R4 / B7 | `H5` | `K2` | `T4` |
| `adc_d[13]` | `ADC_D13` | $(148.317, 144.337)$ (`R39.2`) | **`J5`** | R4 / B7 | `J5` | `K3` | `P4` |

*\*On the PCB, `ADC_OR` is routed via `R41` pad 2 at $(148.317, 138.038)\text{ mm}$; use **T2 Alt-A** once `extract.py` includes `R41`.*

### 3.2 Quantified Evaluation of Moving the ADC Bus to Bank 6 (Proposal)

Currently, Bank 7 (`VCCIO7 = 1.8 V`) is on the **upper-left** of `U12` ($y \in [118.8, 125.2]\text{ mm}$), whereas `U8` (`AD9649`) and `R26..R41` are on the **lower-left** ($y \in [138.0, 147.4]\text{ mm}$). Meanwhile, Bank 6 (`VCCIO6 = 3.3 V`) sits on the **lower-left** of `U12` ($y \in [126.0, 130.0]\text{ mm}$) and carries only 8 slow/static signals (`ref10m` on `M1`, `lmk_scl/sda`, `rly_pad/lna`, `lna_en`, `led[0..1]`).

Swapping `VCCIO6` ($3.3\text{ V} \to 1.8\text{ V}$) and `VCCIO7` ($1.8\text{ V} \to 3.3\text{ V}$) and moving the 19 ADC nets to Bank 6 (`L1 = PCLKT6_1` or `M1 = PCLKT6_0` for `adc_dco`):
1. **Wirelength reduction:** Total Euclidean bus length drops from **$494.5\text{ mm}$** (current Bank 7) / **$472.6\text{ mm}$** (optimized Bank 7) to **$402.3\text{ mm}$** in Bank 6 R0–R2 (or **$395.5\text{ mm}$** across Bank 6) — saving **$92.2\text{ mm}$ ($18.6\%$)** of total trace length (mean trace length drops from $26.0\text{ mm}$ to $21.2\text{ mm}$).
2. **Ring depth & PCLK geometry:** Because `L1` (`PCLKT6_1`, $y=126.0$) and `M1` (`PCLKT6_0`, $y=126.8$) sit at the **North end** of Bank 6 (matching `R40.2`'s position at the North-West of the ADC fan), **all 19 ADC signals fit strictly inside Rings 0, 1, and 2 of Bank 6** with **0 non-DCO crossings** (and **0 total crossings** if `R40` is placed near `U8` pin 22).
3. **Clock input note:** `ref10m` moves from `M1` (`PCLKT6_0`) to `K1` (`PCLKT7_0`) in Bank 7, which is also a dedicated left-side `PCLK` input (so `ref10m` still drives the global clock network).

---

## 4. Adversarial Verification of Claims C1–C5

### Claim C1: Current FT601 Assignment Has 237 Straight-Line Crossings — **VERIFIED**
- **Method:** Construct the 46 line segments $S_i = (\mathbf{p}_{U11, i}, \mathbf{p}_{U12, i})$ from `ft601_pins` and `fpga_balls` in `notes/pinswap/data.json` and test all $\binom{46}{2} = 1035$ pairs for proper intersection using exact 2D orientation predicates.
- **Result:** **237 proper intersections** (reproduced in `python3 notes/pinswap/agy_check.py`).

### Claim C2: Fan-Out Via Channel Arithmetic in T3 — **VERIFIED**
- **Result:** $G_{\text{via-via}} = 0.800 - 0.450 = \mathbf{0.350\text{ mm}} < 0.404\text{ mm}$ ($0.150 + 2\times 0.127\text{ mm}$); $G_{\text{pad-via}} = 0.4\sqrt{2} - 0.160 - 0.225 = \mathbf{0.1807\text{ mm}} \approx 0.18\text{ mm} < 0.404\text{ mm}$. Full derivation in §1.1 above.

---

### Claim C3: Buck Converter (`TPS62A02`) $0.2\text{ mm} \times 0.6\text{ mm}$ `SW` Neck — **VERIFIED (Acceptable)**

From `kicad/gen/buck_patch.py:42-73`, `U2` and `U3` (`TPS62A02`, SOT-563 at $0.50\text{ mm}$ pin pitch, pad width $0.35\text{ mm}$) exit `SW` (pin 2) on a $w = 0.20\text{ mm}$ neck for $L \approx 0.60\text{ mm}$ ($0.8875\text{ mm}$ center-to-center, $0.550\text{ mm}$ exposed past the pad edge) before widening to $0.60\text{ mm}$ into `L1`/`L2`, while `VIN` and `GND` use $0.20\text{ mm} \times 0.45\text{ mm}$ necks ($0.275\text{ mm}$ exposed past the pad edge) before widening to $0.40\text{ mm}$.

1. **Cross-Section & DC Resistance ($1\text{ oz} = 35\text{ }\mu\text{m}$ copper):**
   $$A = w\,t = 0.20\text{ mm} \times 0.035\text{ mm} = 7.00 \times 10^{-3}\text{ mm}^2 = 13.815\text{ cmil}, \qquad N_\square = \frac{L}{w} = \frac{0.60}{0.20} = 3.0\text{ }\square$$
   With $\rho_{\text{Cu}}(25^\circ\text{C}) = 1.724\times 10^{-8}\text{ }\Omega\cdot\text{m}$ ($R_\square = 0.493\text{ m}\Omega/\square$) and $\rho_{\text{Cu}}(60^\circ\text{C}) = 1.960\times 10^{-8}\text{ }\Omega\cdot\text{m}$ ($R_\square = 0.560\text{ m}\Omega/\square$):
   $$R_{\text{SW}}(25^\circ\text{C}) = \mathbf{1.48\text{ m}\Omega}, \qquad R_{\text{SW}}(60^\circ\text{C}) = \mathbf{1.68\text{ m}\Omega}, \qquad R_{\text{VIN/GND}}(0.45\text{ mm}) = \mathbf{1.11\text{ m}\Omega}\text{ (25}^\circ\text{C)}$$
   *(This is $< 1.5\%$ of the TPS62A02 internal MOSFET $R_{\text{DS(on)}} \approx 110\text{ m}\Omega$ HS / $70\text{ m}\Omega$ LS.)*

2. **IR Drop & Power Dissipation:**
   - **At $I_{\text{avg}} = 1.0\text{ A}$:** $\Delta V_{\text{SW}} = \mathbf{1.48\text{ mV}}$ ($1.68\text{ mV}$ at $60^\circ\text{C}$; $\Delta V_{\text{SW+VIN}} = 2.59\text{ mV}$), $P_{\text{SW}} = \mathbf{1.48\text{ mW}}$.
   - **At $I_{\text{pk}} = 2.0\text{ A}$:** $\Delta V_{\text{SW}} = \mathbf{2.96\text{ mV}}$ ($\mathbf{3.36\text{ mV}}$ at $60^\circ\text{C}$; $\Delta V_{\text{SW+VIN}} = 5.18\text{ mV}$), $P_{\text{SW}} = \mathbf{6.72\text{ mW}}$.

3. **Temperature Rise (Infinite-Trace IPC-2152 vs. Actual $0.60\text{ mm}$ Short-Neck Axial Conduction):**
   - For an *infinitely long* $0.20\text{ mm}$ external trace ($1\text{ oz}$), IPC-2152 gives $\Delta T_\infty \approx \mathbf{12^\circ\text{C}}$ at $1.0\text{ A}$ and $\mathbf{45^\circ\text{C}}$ at $2.0\text{ A}$.
   - However, the thermal healing length of a $35\text{ }\mu\text{m}$ trace over $h = 0.2104\text{ mm}$ FR-4 prepreg ($k_{\text{FR4}} \approx 0.30\text{ W/(m}\cdot\text{K)}$, $k_{\text{Cu}} = 385\text{ W/(m}\cdot\text{K)}$) to the `In1.Cu` GND plane is:
     $$\ell_{\text{heal}} = \sqrt{\frac{k_{\text{Cu}}\,t_{\text{Cu}}}{k_{\text{FR4}} / h_{\text{prepreg}}}} = \sqrt{\frac{385 \times 35\times 10^{-6}}{0.30 / 0.2104\times 10^{-3}}} = \mathbf{3.07\text{ mm}} \gg L_{\text{neck}} = 0.60\text{ mm}$$
     With axial thermal time constant $\tau_{\text{th}} = \frac{L^2}{\pi^2 \alpha_{\text{Cu}}} = \mathbf{0.33\text{ ms}}$, heat generated in the $0.60\text{ mm}$ neck conducts axially into the SOT-563 pad and $0.60\text{ mm}$ inductor trace. The local excess temperature rise at the center of the neck (2-sided conduction $\Delta T = \frac{P L}{8 k_{\text{Cu}} A}$, 1-sided $\frac{P L}{2 k_{\text{Cu}} A}$) is only:
     $$\Delta T_{\text{neck}}(1\text{ A}) = \mathbf{0.04\text{–}0.16\text{ K}}, \qquad \Delta T_{\text{neck}}(2\text{ A}) = \mathbf{0.19\text{–}0.75\text{ K}}$$

4. **Fusing Margin:**
   - **Steady-state DC fusing on FR-4 ($h = 0.21\text{ mm}$ to `In1.Cu` GND):** $I_{\text{fuse, DC}} = A \sqrt{\frac{(k_{\text{FR4}}/h)(T_m - T_a)}{\bar{\rho}_{\text{Cu}} t_{\text{Cu}}}} \approx \mathbf{6.0\text{ A}}$ (and higher with axial heat sinking into the pads).
   - **Adiabatic fault pulse (Onderdonk):** During a hard short before the TPS62A02 cycle-by-cycle high-side current limit ($I_{\text{LIM}} = 2.4\text{–}3.2\text{ A}$, response time $< 420\text{ ns}$) acts, the $10\text{ ms}$ adiabatic fusing current is **$I_{\text{fuse}}(10\text{ ms}) = \mathbf{20.2\text{ A}}$** (and $1\text{ s}$ vacuum adiabatic Onderdonk is $2.02\text{ A}$).
   - *(Optional layout improvement: `VIN` [pin 1] and `GND` [pin 3] exit outward away from `SW` [pin 2], so their necks can be widened from $0.20\text{ mm}$ to $0.35\text{ mm}$ with zero clearance penalty to `SW`.)*

---

### Claim C4: USB 2.0 HS ($480\text{ Mb/s}$) Uncoupled $0.2\text{ mm}$ D+/D- Routing — **VERIFIED (Acceptable)**

Given stack-up parameters: outer copper $t = 35\text{ }\mu\text{m}$, 7628 prepreg $h = 0.2104\text{ mm}$, $\varepsilon_r = 4.4$, trace width $w = 0.200\text{ mm}$, trace length $\ell = 10\text{–}14\text{ mm}$, 2 vias per line, USB 2.0 High-Speed rise time $t_r \ge 500\text{ ps}$:

1. **Single-Ended Microstrip Impedance & Propagation Velocity:**
   Using Hammerstad–Jensen (with thickness correction $w_{\text{eff}} = 0.2286\text{ mm}$, $u = w_{\text{eff}}/h = 1.086$) and IPC-2141A:
   $$\varepsilon_{\text{eff}} = \frac{\varepsilon_r + 1}{2} + \frac{\varepsilon_r - 1}{2\sqrt{1 + 12/u}} = \mathbf{3.21}, \qquad Z_0 = \mathbf{65.8\text{ }\Omega}\text{ (Hammerstad–Jensen)} \;\text{to}\; \mathbf{67.3\text{ }\Omega}\text{ (IPC-2141A)}$$
   Phase velocity and propagation delay per unit length:
   $$v_p = \frac{c_0}{\sqrt{\varepsilon_{\text{eff}}}} = \frac{299.79\text{ mm/ns}}{\sqrt{3.21}} = \mathbf{167.4\text{ mm/ns}}, \qquad \tau_{\text{pd}} = \frac{1}{v_p} = \mathbf{5.97\text{ ps/mm}}$$

2. **Electrical Length vs. Rise Time ($t_r \ge 500\text{ ps}$):**
   For $\ell = 10\text{–}14\text{ mm}$:
   $$t_{\text{pd}} = \ell\,\tau_{\text{pd}} = \mathbf{59.7\text{–}83.6\text{ ps}} \quad (11.9\%\text{–}16.7\%\text{ of }t_r), \qquad 2\,t_{\text{pd}} = \mathbf{119\text{–}167\text{ ps}} \le \frac{t_r}{3}$$
   Because the round-trip delay $2 t_{\text{pd}}$ is less than one-third of the $500\text{ ps}$ transition time, the source reflection returns while the edge is still slewing (**electrically short / lumped-element regime**).

3. **Reflection Amplitude from the $Z_0 \approx 66\text{ }\Omega$ Uncoupled Section:**
   Each USB 2.0 HS line is terminated in $R_T = 45\text{ }\Omega \pm 10\%$ to GND ($90\text{ }\Omega$ differential).
   - **Asymptotic step reflection ($t_r \to 0$):**
     $$\Gamma_\infty = \frac{Z_0 - Z_S}{Z_0 + Z_S} = \frac{65.8 - 45.0}{65.8 + 45.0} = \mathbf{+0.188} \quad (-14.5\text{ dB}; \;\text{for }Z_0 \in [60, 70]\text{ }\Omega,\; \Gamma_\infty \in [+0.143, +0.217])$$
   - **Actual peak reflection for finite rise time $t_r = 500\text{ ps}$:**
     Treating the electrically short high-$Z_0$ segment as excess series inductance $\Delta L = t_{\text{pd}}(Z_0 - Z_S) = 1.24\text{–}1.74\text{ nH}$ (or piecewise-linear ramp superposition $\Gamma_{\text{eff}} \approx \Gamma_\infty \frac{2 t_{\text{pd}}}{t_r}$):
     $$\Gamma_{\text{eff, L}} \approx \frac{\Delta L}{2 Z_S t_r} = \mathbf{2.8\%\text{–}3.9\%}, \qquad \Gamma_{\text{eff, ramp}} \approx \Gamma_\infty \frac{2 t_{\text{pd}}}{t_r} = \mathbf{4.5\%\text{–}6.3\%}$$
     Both are well below the $\pm 10\%$ USB 2.0 HS eye-diagram reflection budget.

4. **Via Stubs on the $1.6\text{ mm}$ Board:**
   Because the signal transitions between **`F.Cu` (Layer 1, top)** and **`B.Cu` (Layer 4, bottom)**, current flows through the **entire $1.6\text{ mm}$ via barrel**:
   $$L_{\text{stub}} = \mathbf{0.00\text{ mm}} \quad (\text{zero dangling stub!})$$
   The through-via itself has $L_{\text{via}} \approx 0.7\text{ nH}$ and $C_{\text{via}} \approx 0.3\text{ pF}$, giving a matched characteristic impedance $Z_{\text{via}} = \sqrt{L_{\text{via}}/C_{\text{via}}} \approx \mathbf{48\text{ }\Omega} \approx 45\text{ }\Omega$ and adding only $\sim 15\text{ ps}$ of delay per via.
   - **Two layout caveats to verify on the board:** (1) When a trace transitions from `F.Cu` (referenced to `In1.Cu = GND`) to `B.Cu` (referenced to `In2.Cu = 3V3_D`), return current must transfer between `GND` and `3V3_D` through nearby decoupling capacitors; keep the `B.Cu` segment short or place a $100\text{ nF}$ `3V3_D`–`GND` capacitor within $2\text{–}3\text{ mm}$ of the signal vias. (2) Keep intra-pair length mismatch $|\ell_{D+} - \ell_{D-}| \le 1.5\text{ mm}$ ($\le 9\text{ ps}$ skew).

---

### Claim C5: Do `B.Cu` Nets Cross `In2.Cu` Splits? — **VERIFIED (Yes, Inevitably)**

1. **Analytical Proof Directly from the Zone Coordinates in `BRIEF.md` §1:**
   From `BRIEF.md` §1, the `In2.Cu` power islands are:
   - `1V1`: $x \in [155.5, 170.5]\text{ mm},\; y \in [116.5, 131.5]\text{ mm}$
   - `3V3_D`: $x \in [152.0, 199.7]\text{ mm},\; y \in [100.3, 142.0]\text{ mm}$
   - `1V8_A`: $x \in [134.0, 152.0]\text{ mm},\; y \in [108.0, 134.0]\text{ mm}$
   Compare these against the component coordinates in `data.json`:
   - **`U12` (FPGA) balls** span $x \in [157.0, 169.0]\text{ mm},\; y \in [118.0, 130.0]\text{ mm}$ — **completely inside the `1V1` island**! Meanwhile, `U11` (`FT601`) is at $x \approx 184\text{ mm}$ (inside `3V3_D`), and `U8` (`AD9649`) is at $(141, 141)$. Therefore, **100% of `B.Cu` dog-bone escape traces leaving `U12` MUST cross the `1V1` split boundary** at $x = 170.5\text{ mm}$ (East) or $x = 155.5\text{ mm}$ (West)!
   - **`U8` (`AD9649` ADC) and `R26..R41`** span $x \in [137.0, 148.8]\text{ mm},\; y \in [138.0, 147.4]\text{ mm}$. Because `1V8_A` stops at **$y = 134.0\text{ mm}$** and `3V3_D` starts at **$x = 152.0\text{ mm}$**, the entire region $x \in [134, 152],\; y \in [134, 148]$ under `U8` and `R26..R41` has **no `In2.Cu` copper at all** unless `kicad/gen/in2_gnd_fill.py` is applied!

2. **Exact Command for Claude to Run on the Routed Board:**
   Run the following one-liner from the repo root to list every `B.Cu` track segment on `kicad/deeppcb/r2_deeppcb_routed.kicad_pcb` that crosses an `In2.Cu` split or bare region (using actual filled zone polygons `ZONE.HitTest`):
   ```bash
   python3 -c '
   import pcbnew
   b = pcbnew.LoadBoard("kicad/deeppcb/r2_deeppcb_routed.kicad_pcb")
   in2, bcu = b.GetLayerID("In2.Cu"), b.GetLayerID("B.Cu")
   zs = [(z.GetNetname(), z) for z in b.Zones() if z.IsOnLayer(in2)]
   def z_at(x, y):
       pt = pcbnew.VECTOR2I(int(x), int(y))
       return next((n for n, z in zs if z.HitTestFilledArea(in2, pt, 0)), "NONE")
   bad = {}
   for t in b.GetTracks():
       if t.GetClass() == "PCB_TRACK" and t.GetLayer() == bcu:
           s, e = t.GetStart(), t.GetEnd()
           mods = {z_at(s.x + (e.x - s.x)*k/10, s.y + (e.y - s.y)*k/10) for k in range(11)}
           if len(mods) > 1 or "NONE" in mods:
               bad.setdefault(t.GetNetname(), set()).update(mods)
   print(f"B.Cu nets crossing In2.Cu splits/voids: {len(bad)}")
   for n, m in sorted(bad.items()): print(f"  {n:28s}: {sorted(m)}")
   '
   ```
   *(On `r2_deeppcb_routed.kicad_pcb`, this reports **51 nets** crossing `In2.Cu` splits/voids, including `FT_D15, FT_D17, FT_D19, FT_D22, FT_D25, FT_D26`, `ADC_D13`, `ADC_CLKP`, `ADC_DCO_R`, `REF10M`, and `LMK_OUTN`.)*

3. **Recommended Fix for `In2.Cu` (`pcb_build.py` + `in2_gnd_fill.py`):**
   - **Shrink the `1V1` zone on `In2.Cu` from `[155.5..170.5, 116.5..131.5]` to `[160.2..165.0, 121.6..126.8]`!** All six `1V1` balls on `U12` (`G6, G7, G9, L8, L9, L10`) and their fan-out vias lie inside $x \in [160.6, 164.6]\text{ mm},\; y \in [122.4, 126.4]\text{ mm}$. Shrinking `1V1` to that $4.8\text{ mm}\times 5.2\text{ mm}$ core square allows `3V3_D` (East) and `GND` (West, via `in2_gnd_fill.py`) to extend continuously underneath **all Ring 2–4 signal vias of `U12`**, eliminating the `1V1` split crossing for every FT601 and ADC `B.Cu` escape trace!
