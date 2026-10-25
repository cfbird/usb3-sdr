# Clock Polarity Swap (`LMK61E2` $\to$ `AD9649`) & Output Termination Verification

**Author:** AGY (Antigravity)  
**Sources:**  
- Analog Devices `AD9649` Data Sheet, Rev. B (`refs/datasheets/AD9649_RevB.pdf`)  
- Texas Instruments `LMK61E2` Data Sheet, `SNAS674C`, Sep. 2015 / Rev. May 2025 (`refs/datasheets/LMK61E2_SNAS674C.pdf`)  
**Circuit Under Review (`kicad/gen/design.py:145-153`):**  
- `U9` (`LMK61E2`) Pin 4 (`OUTP`) $\to$ $100\text{ nF}$ (`C61`) $\to$ `U8` (`AD9649-80`) Pin 2 (`CLK−`)  
- `U9` (`LMK61E2`) Pin 5 (`OUTN`) $\to$ $100\text{ nF}$ (`C62`) $\to$ `U8` (`AD9649-80`) Pin 1 (`CLK+`)  
- $100\text{ }\Omega$ differential resistor across `AD9649` Pin 1 (`CLK+`) and Pin 2 (`CLK−`).

---

## Executive Summary Table

| Item | Claim / Question | Verdict | Datasheet Citations & Key Quantitative Result |
| :--- | :--- | :---: | :--- |
| **P1** | AD9649 clock input is self-biased differential, accepts AC-coupled LVDS; inverting polarity shifts sampling by $\frac{1}{2}T_{\text{CLK}} = 6.25\text{ ns}$ at $80\text{ MHz}$; `DATA` and `DCO` follow the inverted clock so FPGA capture is unaffected; DCS works the same | **VERIFIED** *(with DCS note)* | **AD9649 Rev. B:** Page 6 Table 3, Page 7 Table 4 & Fig. 2, Page 16 Fig. 30, Page 20 Figs. 46 & 50, Page 21 Fig. 52, Page 22, Page 27 Table 16. <br>• Internal bias = $0.9\text{ V}$ typ; accepts AC-coupled LVDS ($0.2\text{–}3.6\text{ V}_{\text{p-p}}$ diff).<br>• Polarity swap shifts `CLK+ - CLK−` rising zero-crossing by $D \cdot T_{\text{CLK}} = 6.25\text{ ns}$ ($50\%$ duty at $80\text{ MHz}$); `DCO` and `DATA` both shift by $+6.25\text{ ns}$ ($t_{\text{SKEW}} = 0.1\text{ ns}$ typ unchanged).<br>• **Correction on DCS:** The AD9649 **has no Duty-Cycle Stabilizer (DCS)** (no DCS in Fig. 1 or Reg `0x09` in Table 16). Instead, Page 21 Fig. 52 requires $50\% \pm 5\%$ duty cycle. Because `LMK61E2` LVDS duty cycle is $45\%\text{–}55\%$ (`SNAS674C` Page 5 §5.7), the inverted duty cycle $100\% - D$ is also $45\%\text{–}55\%$, remaining in Fig. 52's flat plateau. |
| **P2** | Nothing in the AD9649 datasheet (clock input, timing diagrams, DCS, pipeline latency) makes `CLK+` vs. `CLK−` polarity matter for a free-running $80\text{ MHz}$ single-ADC design | **VERIFIED** | **AD9649 Rev. B:** Page 7 Table 4 & Fig. 2, Page 10 Fig. 3 & Table 8, Page 16 Fig. 30, Page 20 Figs. 46–51, Page 22, Page 27–28 Table 16. <br>• `CLK+` and `CLK−` equivalent circuits (Fig. 30, Fig. 46) are 100% symmetric ($5\text{ }\Omega$ series + $15\text{ k}\Omega$/$50\text{ k}\Omega$ to internal $0.9\text{ V}$).<br>• Pipeline latency (8 clock cycles) and output timing are referenced solely to the differential `CLK+ - CLK−` crossing. Only single-ended CMOS mode (Fig. 51) is asymmetric. |
| **P3** | `LMK61E2` output is differential and symmetric, so either leg (`OUTP` / `OUTN`) can drive either ADC input (`CLK−` / `CLK+`) | **VERIFIED** | **LMK61E2 SNAS674C:** Page 3 Fig. 4-1 & Table 4-1, Page 5 §5.6–5.7, Page 6 §5.8, Page 14–15 Figs. 6-1 to 6-8, Page 19 §7.3.14. <br>• `OUTP` (Pin 4) and `OUTN` (Pin 5) are a balanced differential pair with symmetric swing ($V_{\text{OD}} = 390\text{ mV}$ typ LVDS), internal $125\text{ }\Omega$ diff termination, matched $t_R/t_F = 150\text{ ps}$ typ, and $45\%\text{–}55\%$ duty cycle. |
| **Format** | Which `LMK61E2` output format (`LVDS` / `LVPECL` / `HCSL`) is the $100\text{ }\Omega$ across `CLK+`/`CLK−` (with two $100\text{ nF}$ series caps only) correct for? | **LVDS ONLY** (`R21 = 0x02`) | **AD9649 Rev. B:** Page 20 Fig. 50 vs. Fig. 49. **LMK61E2 SNAS674C:** Page 5 §5.5 Note 2, Page 14–15 Figs. 6-1 to 6-7, Page 19 §7.3.14, Page 31 §8.1.10 (`R21`). <br>• **LVDS (`R21[1:0] = 0x2`)** uses **no DC resistors** before the $100\text{ nF}$ caps and **$100\text{ }\Omega$ diff** at the ADC (exact match to AD9649 Fig. 50 & LMK61E2 Figs. 6-2/6-5/6-7).<br>• **LVPECL (`R21[1:0] = 0x1`)** is an open-emitter follower that **requires $150\text{ }\Omega$ (or $240\text{ }\Omega$) DC pull-downs to GND on `OUTP`/`OUTN` before the AC caps** (LMK61E2 Fig. 6-4/6-7, AD9649 Fig. 49).<br>• **HCSL (`R21[1:0] = 0x3`)** is open-drain and **requires $50\text{ }\Omega$ to GND on `OUTP`/`OUTN` before the AC caps** (LMK61E2 Fig. 6-6/6-7). |

---

## 1. Detailed Verification of Claims P1, P2, and P3

### Claim P1 — **VERIFIED** *(with adversarial note that AD9649 has no internal DCS)*

1. **Self-Biased Differential Clock Input & AC-Coupled LVDS Compliance:**
   - **`AD9649_RevB.pdf`, Page 6, Table 3 ("Differential Clock Inputs (CLK+, CLK−)"):**
     - **Logic Compliance:** `CMOS/LVDS/LVPECL`
     - **Internal Common-Mode Bias:** **$0.9\text{ V}$ typical**
     - **Differential Input Voltage ($V_{\text{ID}}$):** **$0.2\text{ V}_{\text{p-p}}$ min to $3.6\text{ V}_{\text{p-p}}$ max**
     - **Input Voltage Range:** $\text{GND} - 0.3\text{ V}$ to $\text{AVDD} + 0.2\text{ V}$ ($-0.3\text{ V}$ to $+2.0\text{ V}$)
     - **Input Resistance / Capacitance:** **$8\text{ k}\Omega$ min, $10\text{ k}\Omega$ typ, $12\text{ k}\Omega$ max** (differential); **$4\text{ pF}$ max**.
   - **`AD9649_RevB.pdf`, Page 16, Figure 30 ("Equivalent Clock Input Circuit") & Page 20, "Clock Input Considerations" / Figure 46:**
     - Page 20 explicitly states: *"The signal is typically ac-coupled into the CLK+ and CLK− pins via a transformer or capacitors. These pins are biased internally (see Figure 46) and require no external bias."*
   - **`AD9649_RevB.pdf`, Page 20, Figure 50 ("Differential LVDS Sample Clock (Up to 4× Rated Sample Rate)"):**
     - Shows an LVDS clock driver connected through two **$0.1\text{ }\mu\text{F}$ ($100\text{ nF}$) series AC-coupling capacitors** to `CLK+` and `CLK−`, with a **$100\text{ }\Omega$ differential termination resistor** directly across the ADC's `CLK+` and `CLK−` inputs.

2. **Half-Period Sampling Shift ($\Delta t = 6.25\text{ ns}$ at $80\text{ MHz}$) and `DCO` / `DATA` Tracking:**
   - **`AD9649_RevB.pdf`, Page 7, Table 4 ("Switching Specifications") & Figure 2 ("CMOS Output Data Timing"), and Page 22 ("Timing" & "Data Clock Output (DCO)"):**
     - As shown in **Figure 2 (Page 7)**, sample $N$ is acquired on the rising edge of `CLK+` ( simultaneous falling edge of `CLK−`, i.e., the positive-going zero-crossing of $V_{\text{CLK,diff}}(t) = V_{\text{CLK+}}(t) - V_{\text{CLK−}}(t)$) plus aperture delay $t_A = 1.0\text{ ns}$ typ.
     - Connecting `LMK_OUTP` $\to$ `CLK−` and `LMK_OUTN` $\to$ `CLK+` negates the differential clock voltage:
       $$V_{\text{CLK,diff}}^{\text{swapped}}(t) = V_{\text{CLK+}}(t) - V_{\text{CLK−}}(t) = -\left(V_{\text{OUTP}}(t) - V_{\text{OUTN}}(t)\right)$$
     - For a clock of period $T_{\text{CLK}} = \frac{1}{80\text{ MHz}} = \mathbf{12.50\text{ ns}}$ and positive duty cycle $D \in [0.45, 0.55]$, negating the differential waveform exchanges the rising and falling zero-crossings, shifting every sampling instant by:
       $$\Delta t = D \cdot T_{\text{CLK}} = 0.50 \times 12.50\text{ ns} = \mathbf{6.25\text{ ns}} \quad (\text{range } 5.625\text{ ns to } 6.875\text{ ns for } D = 45\%\text{ to }55\%)$$
     - Per **Page 22 ("Timing" & "Data Clock Output (DCO)")** and **Page 7, Table 4 & Figure 2**, the internal pipeline, output data buffers (`D13:D0`, `OR`), and data clock output (`DCO`) are all driven by the internal clock derived from `CLK+`/`CLK−`. Specifically:
       $$t_{\text{PD}} = 3.0\text{ ns typ}, \qquad t_{\text{DCO}} = 3.0\text{ ns typ}, \qquad t_{\text{SKEW}} = t_{\text{DCO}} - t_{\text{PD}} = \mathbf{0.1\text{ ns typ}}$$
       Both `DATA` and `DCO` shift together by the exact same $\Delta t = 6.25\text{ ns}$. At the FPGA (`adc_dco` capturing `adc_d[13:0]` and `adc_or` at $80\text{ MHz}$), the setup and hold margins relative to `DCO` are completely unchanged.

3. **Adversarial Datasheet Check on the Duty-Cycle Stabilizer (DCS):**
   - **Fact-check:** Unlike several other Analog Devices ADCs (such as the AD9265 or AD9643, which include a Duty-Cycle Stabilizer controlled by SPI Register `0x09` bit 0), **the AD9649 does NOT have a Duty-Cycle Stabilizer (DCS)**:
     - The words *"duty cycle stabilizer"* or *"DCS"* do not appear anywhere in `AD9649_RevB.pdf` (**Page 1 "Features" & "Figure 1. Functional Block Diagram"** have no DCS block).
     - In **Page 27, Table 16 ("Memory Map Register Table")**, Register `0x09` is absent, and the header states: *"All address and bit locations that are not included in Table 16 are not currently supported for this device."*
     - Instead, **Page 21 ("Clock Duty Cycle" and "Figure 52. SNR vs. Clock Duty Cycle")** states:
       > *"Typical high speed ADCs use both clock edges to generate a variety of internal timing signals and, as a result, may be sensitive to clock duty cycle. Commonly, a 50% duty cycle clock with ±5% tolerance is required to maintain optimum dynamic performance, as shown in Figure 52."*
   - **Why polarity inversion still has zero impact on duty-cycle performance:**
     - If the `LMK61E2` output has positive duty cycle $D$ on `OUTP - OUTN`, swapping `OUTP`/`OUTN` gives positive duty cycle $D' = 1 - D = 100\% - D$ on `CLK+ - CLK−`.
     - Per `LMK61E2_SNAS674C.pdf` **Page 5, Section 5.7 ("LVDS Output Characteristics")**, the LMK61E2 output duty cycle (`ODC`) in Divide-by-1 mode (`Divide-by-1` on AD9649) is guaranteed over temperature to be **$45\%$ min to $55\%$ max** ($50\% \pm 5\%$). (In fact, because the LMK61E2 output divider `OUT_DIV = 60` or `65` divides a $4.8\text{–}5.2\text{ GHz}$ VCO down to $80\text{ MHz}$, its duty cycle is tightly centered at $50\%$.)
     - Since $D \in [45\%, 55\%] \iff D' = 100\% - D \in [45\%, 55\%]$, the inverted clock automatically satisfies the AD9649's **$50\% \pm 5\%$** specification and stays in the flat $\sim 74\text{ dBFS}$ plateau of **Figure 52 (Page 21)**.

---

### Claim P2 — **VERIFIED**

Checking every section of `AD9649_RevB.pdf`:
1. **Pin Configuration & Equivalent Circuits (Page 10, Figure 3 & Table 8; Page 16, Figure 30; Page 20, Figure 46):**
   - `CLK+` (Pin 1) and `CLK−` (Pin 2) have identical internal equivalent circuits: a $5\text{ }\Omega$ series resistance, ESD diodes to `AVDD` and `GND`, and matched bias resistors ($15\text{ k}\Omega$ in Fig. 30 / $50\text{ k}\Omega$ in Fig. 46) to the internal $0.9\text{ V}$ reference.
2. **Clock Input Options (Page 20, Figures 47–51):**
   - Figures 47, 48, 49, and 50 (Transformer, Balun, PECL, LVDS) are all balanced differential interfaces. Only **Figure 51 ("Single-Ended 1.8 V CMOS Input Clock")** is asymmetric (driving `CLK+` directly from a 1.8 V CMOS gate while AC-grounding `CLK−` through $0.1\text{ }\mu\text{F}$).
3. **Switching Specifications, Timing Diagram & Pipeline Latency (Page 7, Table 4 & Figure 2; Page 22):**
   - Pipeline latency is **8 clock cycles** (`Table 4`, Page 7; `TIMING`, Page 22). There is no external `SYNC` or timestamp reset pin on the 32-lead AD9649 (`Figure 3`, Page 10).
4. **Clock Divider & Output Phase Registers (Page 20–21 "Input Clock Divider"; Page 27–28, Table 16 Registers `0x0B`, `0x16`, `0x17`):**
   - In Divide-by-1 mode (`Register 0x0B = 0x00`, default), every rising edge of `CLK+ - CLK−` triggers a sample and a `DCO` rising edge. In a single-ADC HF/VHF SDR receiver where the RF input is continuous and not phase-referenced to the 80 MHz sampling clock phase, shifting the sampling grid by $T_{\text{CLK}}/2 = 6.25\text{ ns}$ ($\pi\text{ radians}$ of carrier phase at $f_{\text{in}}$) is indistinguishable from a $6.25\text{ ns}$ change in coax cable length.

---

### Claim P3 — **VERIFIED**

In `LMK61E2_SNAS674C.pdf`:
- **Page 3, Figure 4-1 ("SIA Package 8-Pin QFM Top View") & Table 4-1 ("Pin Functions"):**
  - Pin 4 (`OUTP`) and Pin 5 (`OUTN`) are the complementary legs of a single universal differential output buffer (`LVPECL, LVDS or HCSL`).
- **Page 5, Section 5.7 ("LVDS Output Characteristics"), Page 15, Figure 6-8 ("Differential Output Voltage and Rise/Fall Time"), and Page 19, Section 7.3.14 ("High-Speed Clock Output"):**
  - In LVDS mode, the buffer has an integrated **$125\text{ }\Omega$ differential output impedance (`ROUT`)** between `OUTP` and `OUTN`, common-mode voltage $V_{\text{OS}} = 1.2\text{ V}$ typ, single-ended swing $V_{\text{OD}} = 300\text{ mV}$ min / $390\text{ mV}$ typ / $480\text{ mV}$ max ($V_{\text{OUT,DIFF,PP}} = 2|V_{\text{OD}}| = \mathbf{600\text{ to }960\text{ mV}_{\text{p-p}}}$, $780\text{ mV}_{\text{p-p}}$ typ), symmetric rise/fall times $t_R / t_F = 150\text{ ps}$ typ ($250\text{ ps}$ max, $20\%\text{–}80\%$), and $45\%\text{–}55\%$ duty cycle.
  - Because `OUTP` and `OUTN` are driven by a symmetric differential stage and AC-coupled through identical $100\text{ nF}$ capacitors (`C61`, `C62`), either output leg can drive either ADC clock input pin.

---

## 2. Which `LMK61E2` Output Format (`LVDS` / `LVPECL` / `HCSL`) Matches the $100\text{ }\Omega$ Termination?

**Answer:** The schematic's termination—two series $100\text{ nF}$ AC-coupling capacitors (`C61`, `C62`) with **no DC pull-down resistors on the `LMK61E2` side** and a single **$100\text{ }\Omega$ differential resistor across `CLK+`/`CLK−` at the `AD9649`**—is **correct ONLY for `LVDS` (`OUT_SEL[1:0] = 2 [0x2]` in Register `R21`, Page 31)**.

### Comparison of the Three `LMK61E2` Output Formats (`SNAS674C` & `AD9649 Rev. B`)

| `LMK61E2` Format (`R21[1:0]`) | Internal Driver Topology (`SNAS674C` Page 19 §7.3.14) | Required Driver-Side Termination *Before* AC Caps (`SNAS674C` Page 14–15) | Required Receiver-Side Termination *After* AC Caps (`AD9649` Page 20) | Diff. Swing into $100\text{ }\Omega$ ($V_{\text{OUT,DIFF,PP}}$) | Compatible with Current Schematic (`2×100 nF + 100 Ω diff only`)? |
| :--- | :--- | :--- | :--- | :---: | :---: |
| **`LVDS`** (`OUT_SEL = 2`, `R21 = 0x02`) | Current-steering bridge with internal **$125\text{ }\Omega$** diff resistor (`Page 5 §5.7`, `Page 19 §7.3.14`) | **None (`Open`)** (`Fig. 6-2`, `Fig. 6-5`, `Fig. 6-7` Page 14–15) | **$100\text{ }\Omega$ differential** across `CLK+`/`CLK−` (`AD9649 Fig. 50` Page 20) | **$0.60\text{–}0.96\text{ V}_{\text{p-p}}$** ($0.78\text{ V}_{\text{p-p}}$ typ) | **YES — EXACT MATCH** (`AD9649 Fig. 50` & `LMK61E2 Fig. 6-5/6-7`) |
| **`LVPECL`** (`OUT_SEL = 1`, `R21 = 0x01`) | Open-emitter follower (`Page 19 §7.3.14`: *"requires external termination"*) | **$150\text{ }\Omega$ to GND on `OUTP` and $150\text{ }\Omega$ to GND on `OUTN`** (`Fig. 6-4`, `Fig. 6-7` Page 14–15; `Page 5 §5.5 Note 2`; or $240\text{ }\Omega$ in `AD9649 Fig. 49`) | $100\text{ }\Omega$ differential across `CLK+`/`CLK−` (`AD9649 Fig. 49` Page 20) | $1.40\text{–}2.40\text{ V}_{\text{p-p}}$ ($1.60\text{ V}_{\text{p-p}}$ typ *when DC pull-downs present*) | **NO** — Without DC emitter pull-downs to GND before `C61`/`C62`, the open emitters have no DC current path! |
| **`HCSL`** (`OUT_SEL = 3`, `R21 = 0x03`) | Open-drain switched current source (`Page 19 §7.3.14`) | **$50\text{ }\Omega$ to GND on `OUTP` and $50\text{ }\Omega$ to GND on `OUTN`** (`Fig. 6-3`, `Fig. 6-6`, `Fig. 6-7` Page 14–15) | $100\text{ }\Omega$ diff or $50\text{ }\Omega$ to GND | $1.20\text{–}1.70\text{ V}_{\text{p-p}}$ (*when $50\text{ }\Omega$ pull-downs present*) | **NO** — Without $50\text{ }\Omega$ DC pull-downs to GND before `C61`/`C62`, the open drains have no DC return! |

### Verification of LVDS Voltage Swing & High-Pass Corner at the `AD9649` Inputs
1. **Differential amplitude margin:**  
   In `LVDS` mode (`R21 = 0x02`), the LMK61E2 specifies $V_{\text{OD}} = 300\text{ mV}$ min, $390\text{ mV}$ typ, $480\text{ mV}$ max into an external $100\text{ }\Omega$ differential load (`SNAS674C` Page 5 Section 5.7 & Page 14 Figure 6-2), producing a peak-to-peak differential voltage of:
   $$V_{\text{OUT,DIFF,PP}} = 2\,|V_{\text{OD}}| = \mathbf{0.60\text{ V}_{\text{p-p}}\text{ min}}, \quad \mathbf{0.78\text{ V}_{\text{p-p}}\text{ typ}}, \quad \mathbf{0.96\text{ V}_{\text{p-p}}\text{ max}}$$
   This satisfies the `AD9649` differential clock input specification of **$0.20\text{ V}_{\text{p-p}}$ min to $3.6\text{ V}_{\text{p-p}}$ max** (`AD9649_RevB.pdf` Page 6 Table 3) with $3\times$ margin above the minimum threshold and matches the $\sim 0.8\text{ V}_{\text{p-p}}$ swing recommended on Page 20.
2. **Common-mode & single-ended excursion check:**  
   With the AD9649 self-biasing `CLK+` and `CLK−` to $V_{\text{CM}} = 0.90\text{ V}$ (`AD9649` Page 6 Table 3 & Page 20 Figure 46), each pin swings between $0.90\text{ V} \pm \frac{1}{2}V_{\text{OD}} = \mathbf{0.705\text{ V}}$ and $\mathbf{1.095\text{ V}}$ (typ), well inside the allowed $\text{GND} - 0.3\text{ V}$ to $\text{AVDD} + 0.2\text{ V}$ ($[-0.3\text{ V}, +2.0\text{ V}]$) range.
3. **AC-coupling high-pass corner:**  
   Two series $C = 100\text{ nF}$ capacitors (`C61`, `C62`) in series with the $R_{\text{diff}} = 100\text{ }\Omega \parallel 10\text{ k}\Omega \approx 99\text{ }\Omega$ load form a differential high-pass filter with effective capacitance $C_{\text{eff}} = C/2 = 50\text{ nF}$ and cutoff frequency:
   $$f_c = \frac{1}{2\pi\,R_{\text{diff}}\,(C/2)} = \frac{1}{2\pi \times 99\text{ }\Omega \times 50\text{ nF}} = \mathbf{32.2\text{ kHz}} \ll 80\text{ MHz}$$

---

## 3. LMK61E2 Orderable Part Number & Exact 80 MHz Register Configuration

1. **Orderable Part Number & Factory Default Warning (`SNAS674C` Page 1 & Page 50):**
   - In `kicad/gen/design.py:145`, `U9`'s value string is currently `"LMK61E2-100M00SIAR"`. Per `SNAS674C` **Page 1 ("Package Information")** and **Page 50 ("Packaging Information")**, the programmable `LMK61E2` is sold under three factory-EEPROM variants:
     - **`LMK61E2-SIAR` / `LMK61E2-SIAT`:** Boots at **$156.25\text{ MHz}$ LVPECL** (`R21 = 0x01`).
     - **`LMK61E2BAA-SIAR` / `LMK61E2BAA-SIAT`:** Boots at **$156.25\text{ MHz}$ LVDS** (`R21 = 0x02`).
     - **`LMK61E2BBA-SIAR` / `LMK61E2BBA-SIAT`:** Boots at **$125.00\text{ MHz}$ LVDS** (`R21 = 0x02`).
   - Regardless of which variant is populated, once the FPGA programs the `LMK61E2` over I2C (`ADD = GND` $\implies$ 7-bit I2C target address **`0x58` [`0b1011000`]**, `SNAS674C` Page 3 Table 4-1 & Page 21 Section 7.5.1), you can optionally commit the $80\text{ MHz}$ LVDS settings to on-chip EEPROM (`R56 = 0xBE`, `R48 = 0x01`, Page 23 Section 7.5.3 & Page 38 Section 8.1.36) so the oscillator powers up directly in **$80\text{ MHz}$ LVDS** on every subsequent boot.

2. **Exact $80\text{ MHz}$ Integer-N PLL Configuration (`SNAS674C` Page 17 Eq. 1–2 & Pages 31–38):**
   Using the internal $F_{\text{REF}} = 50\text{ MHz}$ crystal (`Page 17 Section 7.3.4`) with the Reference Doubler enabled (`PLL_D = 1` $\implies f_{\text{PFD}} = 100\text{ MHz}$, `Page 18 Section 7.3.6` & `Page 33 R34.5`), **$80\text{ MHz}$ is an exact Integer-N PLL frequency** ($\text{NUM} = 0$), achieving the LMK61E2's lowest jitter mode (**$100\text{ fs}$ typ / $200\text{ fs}$ max RMS jitter**, `Page 8 Section 5.16`):
   $$F_{\text{VCO}} = F_{\text{REF}} \times D \times \text{INT} = 50\text{ MHz} \times 2 \times \text{INT} = 100\text{ MHz} \times \text{INT} \in [4600, 5600]\text{ MHz}, \qquad F_{\text{OUT}} = \frac{F_{\text{VCO}}}{\text{OUT\_DIV}} = 80\text{ MHz}$$
   Two exact Integer-N solutions exist inside $[4.6, 5.6]\text{ GHz}$ (plus $5600\text{ MHz}$ at the upper boundary):
   - **Solution 1 ($F_{\text{VCO}} = 4800\text{ MHz}$):** $\text{INT} = \mathbf{48}$ (`0x030`), $\text{OUT\_DIV} = \mathbf{60}$ (`0x03C`), $\text{NUM} = \mathbf{0}$.
   - **Solution 2 ($F_{\text{VCO}} = 5200\text{ MHz}$, closest to the $5000\text{ MHz}$ factory loop-filter center):** $\text{INT} = \mathbf{52}$ (`0x034`), $\text{OUT\_DIV} = \mathbf{65}$ (`0x041`), $\text{NUM} = \mathbf{0}$.

| Register | Name (`SNAS674C` Pages 31–38) | Value ($F_{\text{VCO}}=5.2\text{ GHz}$) | Value ($F_{\text{VCO}}=4.8\text{ GHz}$) | Field Description |
| :---: | :--- | :---: | :---: | :--- |
| **`R21`** (`0x15`) | `DIFFCTL` | **`0x02`** | **`0x02`** | `DIFF_OUT_PD = 0`, **`OUT_SEL[1:0] = 2` (LVDS)** |
| **`R22`** (`0x16`) | `OUTDIV_BY1` | **`0x00`** | **`0x00`** | `OUT_DIV[8] = 0` |
| **`R23`** (`0x17`) | `OUTDIV_BY0` | **`0x41`** ($65$) | **`0x3C`** ($60$) | `OUT_DIV[7:0] = 65` ($5200/65 = 80\text{ MHz}$) or `60` ($4800/60 = 80\text{ MHz}$) |
| **`R25`** (`0x19`) | `PLL_NDIV_BY1` | **`0x00`** | **`0x00`** | `PLL_NDIV[11:8] = 0` |
| **`R26`** (`0x1A`) | `PLL_NDIV_BY0` | **`0x34`** ($52$) | **`0x30`** ($48$) | `PLL_NDIV[7:0] = 52` ($100\times 52 = 5200\text{ MHz}$) or `48` ($4800\text{ MHz}$) |
| **`R27..R29`** | `PLL_FRACNUM` | **`0x00`** | **`0x00`** | `PLL_NUM[21:0] = 0` (pure Integer-N) |
| **`R33`** (`0x21`) | `PLL_MASHCTRL` | **`0x0C`** | **`0x0C`** | `PLL_DTHRMODE = 3` (dither disabled), **`PLL_ORDER = 0` (Integer Mode)** |
| **`R34`** (`0x22`) | `PLL_CTRL0` | **`0x28`** | **`0x28`** | `PLL_D = 1` (Ref Doubler enabled, $f_{\text{PFD}}=100\text{ MHz}$), `PLL_CP = 0x8` ($6.4\text{ mA}$) |
| **`R72`** (`0x48`) | `SWRST` | **`0x02`** | **`0x02`** | `SWR2PLL = 1` (triggers mandatory VCO recalibration; self-clearing, Page 19 §7.3.12) |
