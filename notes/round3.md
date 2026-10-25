# Round 3: LNA Bias/Selection, Cascaded Dynamic Range/IP3 Budget, and Buck Post-Filter

**Author**: AGY (Gemini 4 Argon)  
**Project**: `usb3-sdr` (`AD9649-80` @ $80\text{ MSPS}$, $R_0 = 50\,\Omega$)  
**Verification Script**: [`notes/round3.py`](file:///home/user1/collab/projects/usb3-sdr/notes/round3.py)

---

## 1. LNA Evaluation (`GVA-84+` vs. Alternatives) & Bias Network ($0.1\text{–}32\text{ MHz}$)

### 1.1 `GVA-84+` Datasheet Audit (`DISPUTED` as HF LNA choice)
Per the **Mini-Circuits `GVA-84+` datasheet** ($+25^\circ\text{C}$, $50\,\Omega$), the part is an InGaP HBT Darlington MMIC rated `"DC to 7 GHz"` with its **lowest characterized points at $50\text{ MHz}$ and $100\text{ MHz}$**:
- **Gain**: $24.0\text{ dB}$ @ $50\text{ MHz}$, $24.1\text{ dB}$ typ ($22.9\text{–}25.3\text{ dB}$) @ $100\text{ MHz}$.
- **Noise Figure ($\text{NF}$)**: **$5.4\text{ dB}$ typ @ $50\text{ MHz}$**, **$5.5\text{ dB}$ typ ($6.5\text{ dB}$ max) @ $100\text{ MHz}$**.
- **Output IP3 ($\text{OIP3}$)**: **$+34.5\text{ dBm}$ @ $50\text{ MHz}$**, $+35.8\text{ to }+36.7\text{ dBm}$ @ $100\text{ MHz}$ ($P_{1\text{dB}} = +19.8\text{ dBm}$).
- **Device Voltage & Current**: **$V_d = +5.0\text{ V}$ nominal ($4.8\text{ V}$ min, $5.2\text{ V}$ max)**, **$I_d = 108\text{ mA}$ typ ($85\text{–}130\text{ mA}$)** $\implies P_{\text{DC}} = 540\text{ mW}$.

**Why `GVA-84+` is Unsuitable for a USB-Powered HF Receiver**:
1. **Zero Bias Headroom from $5\text{ V}$ USB (and cannot run from $3.3\text{ V}$)**: Because $V_d = 5.0\text{ V}$ ($4.8\text{ V}$ min) is required directly at the MMIC output pin, a $5.0\text{ V}$ USB rail ($4.75\text{–}5.25\text{ V}$) leaves $R_{\text{bias}} = \frac{V_{CC} - V_d}{I_d} = \mathbf{0\,\Omega}$ (no current ballast stabilization!). Even a $3.5\,\Omega$ DC resistance in a $1\text{ mH}$ choke drops $108\text{ mA} \times 3.5\,\Omega = 0.38\text{ V}$, starving the device below its $4.8\text{ V}$ minimum. It cannot run from $3.3\text{ V}$ at all ($2 V_{BE}$ Darlington stack).
2. **High Noise Figure ($5.4\text{–}6.5\text{ dB}$ + HBT $1/f$ noise below $10\text{ MHz}$)**: Violates the $\text{NF} \le 3.0\text{ dB}$ spec.
3. **Excessive Gain ($24.0\text{ dB}$) Degrades Input IP3**: $\text{IIP3} = +34.5 - 24.0 = +10.5\text{ dBm}$ (worse than the ADC!).

### 1.2 Bias Tee & Stacked Choke Math for $0.1\text{–}32\text{ MHz}$ (vs. $\ge 10\text{ MHz}$)
- **Choke Inductance for $X_L \ge 10 R_0 = 500\,\Omega$ at $f_{\min} = 100\text{ kHz}$**:
  $$L_{\text{choke}} \ge \frac{500\,\Omega}{2\pi (100\text{ kHz})} = \mathbf{795.8\,\mu\text{H}} \longrightarrow \text{E12: } \mathbf{820\,\mu\text{H}\text{ or }1.0\text{ mH}}$$
- **Single-Inductor SRF Problem**: A single $1.0\text{ mH}$ inductor rated for $\ge 100\text{ mA}$ has $C_p \approx 15\text{–}25\text{ pF}$ ($\text{SRF} \approx 1.0\text{–}1.3\text{ MHz}$) plus multi-layer winding resonances at $10\text{–}30\text{ MHz}$. Above $1.3\text{ MHz}$ it looks capacitive ($|Z| = 265\,\Omega$ at $30\text{ MHz}$ for $C_p = 20\text{ pF}$), detuning LPF #2!
- **3-Stage Stacked Choke Solution ($0.1\text{–}50\text{ MHz}$, $|Z| \ge 620\,\Omega$ everywhere)**:
  1. **$L_{b1} = 1.0\,\mu\text{H}$** (closest to RF pin, 0603, $\text{SRF} \ge 350\text{ MHz}$, $R_{\text{DC}} = 0.35\,\Omega$) — isolates RF node above $10\text{ MHz}$.
  2. **$L_{b2} = 22\,\mu\text{H}$** (0805, $\text{SRF} \approx 40\text{ MHz}$, $R_{\text{DC}} = 1.2\,\Omega$) in parallel with **$1.5\text{ k}\Omega$ de-Q resistor**.
  3. **$L_{b3} = 1.0\text{ mH}$** (1210 shielded, $\text{SRF} \approx 1.1\text{ MHz}$, $R_{\text{DC}} = 3.5\,\Omega$) in parallel with **$2.2\text{ k}\Omega$ de-Q resistor**.
- **Coupling Capacitors for $100\text{ kHz}$ Corner**:
  - $-3\text{ dB}$ vs. $50\,\Omega$: $C = \frac{1}{2\pi(100\text{ kHz})(50\,\Omega)} = \mathbf{31.8\text{ nF}}$.
  - Flat passband ($X_C \le 5\,\Omega \implies <0.04\text{ dB}$ loss at $100\text{ kHz}$): $C \ge \mathbf{318.3\text{ nF}} \longrightarrow$ use **$470\text{ nF}\text{ or }1.0\,\mu\text{F}$ (0603 X7R) $\parallel 10\text{ nF}$ (0402 C0G)**.

### 1.3 Better LNA Alternatives & "No LNA Below 10 MHz" Simplification

| LNA Option | Freq Range | Gain | NF | OIP3 | Supply ($V_{CC} \to V_d, I_d$) | Verdict / Choke Impact |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Mini-Circuits `GVA-84+`** | DC–7 GHz (char $\ge 50\text{ MHz}$) | $24.0\text{ dB}$ | $5.4\text{ dB}$ | $+34.5\text{ dBm}$ | Needs $V_d=5.0\text{ V}$ @ $108\text{ mA}$ ($R_{\text{bias}}=0\,\Omega$ from 5V!) | **REJECT**: No bias headroom from 5V USB, high NF ($5.4\text{ dB}$), high gain hurts IIP3. |
| **Mini-Circuits `PHA-13LN+` / `LHA-13LN+` + $3\text{ dB}$ out pad** | **1–1000 MHz** (char @ 1, 10, 50 MHz) | $22.2\text{ dB}$ ($19.2\text{ dB}$ w/ pad) | **$1.0\text{–}1.2\text{ dB}$** | **$+38.5\text{ dBm}$** ($+35.5\text{ dBm}$ after pad) | Supports **$V_d=3.0\text{–}3.3\text{ V}$ @ $71\text{ mA}$** ($R_{\text{bias}} = 24\,\Omega$ from 5V!) or $5\text{ V}$ | **BEST MMIC ($1\text{–}32\text{ MHz}$)**: Characterized to $1\text{ MHz}$, runs from 5V w/ $24\,\Omega$ drop resistor. |
| **Mini-Circuits `GVA-62+` (used $\ge 10\text{ MHz}$ only)** | **10–6000 MHz** | **$15.2\text{ dB}$** | **$1.5\text{ dB}$** | **$+39.0\text{ dBm}$** | $V_d = 4.8\text{–}5.0\text{ V}$ @ $82\text{ mA}$ (or use **Norton BJT `BFU550A`** @ 5V/40mA) | **BEST IF BYPASSED $<10\text{ MHz}$**: Since ITU noise below $10\text{ MHz}$ is $>39.5\text{ dB}$, **bypass LNA $<10\text{ MHz}$** and use a single **$15\,\mu\text{H}$ 0805 choke + $100\text{ nF}$ caps**! |

---

## 2. Dynamic Range / IP3 Cascade Budget (`AD9649-80` @ $f_s = 80\text{ MSPS}$)

### 2.1 Chain & ADC Linearity Derivation
- **Chain**: $\text{Protection (0 dB)} \to \text{Switch (0.3 dB)} \to \text{LPF1+Notch (1.5 dB)} \to \text{LNA }(G, \text{NF}, \text{OIP3}) \to \text{LPF2 (1.5 dB)} \to \text{Balun ADT4-6T+ (1.0 dB assumed; 0.35 dB typ DS)} \to \text{AD9649}$.
  - Pre-LNA loss: $L_{\text{pre}} = 0.3 + 1.5 = \mathbf{1.8\text{ dB}}$.
  - Post-LNA loss: $L_{\text{post}} = 1.5 + 1.0 = \mathbf{2.5\text{ dB}}$ (Total passive loss $L_{\text{tot}} = \mathbf{4.3\text{ dB}}$).
- **AD9649 Parameters**: $P_{\text{FS}} = +4.0\text{ dBm}$, $\text{NF}_{\text{ADC}} = 27.9\text{ dB}$, two-tone $\text{SFDR} = 90\text{ dB}$ at $-7\text{ dBFS}$ per tone ($P_{\text{tone,ADC}} = +4.0 - 7.0 = -3.0\text{ dBm}$):
  - **Convention A (`90 dBc` relative to $-3\text{ dBm}$ tone)**: $\text{IIP3}_{\text{ADC}} = -3.0 + \frac{90}{2} = \mathbf{+42.0\text{ dBm}}$.
  - **Convention B (ADI `90 dBFS` $= 83\text{ dBc}$ relative to $-3\text{ dBm}$ tone)**: $\text{IIP3}_{\text{ADC}} = -3.0 + \frac{83}{2} = \mathbf{+38.5\text{ dBm}}$.
- **Required LNA OIP3 so LNA Does Not Dominate ADC IMD**:
  Referring $\text{IIP3}_{\text{ADC}}$ back across $L_{\text{post}} = 2.5\text{ dB}$ to the LNA output node gives a threshold **independent of $G_{\text{LNA}}$ and $L_{\text{pre}}$**:
  $$\text{OIP3}_{\text{LNA, match}} = \text{IIP3}_{\text{ADC}} + L_{\text{post}} = \begin{cases} \mathbf{+44.5\text{ dBm}} & (\text{Conv. A: } 90\text{ dBc}) \\ \mathbf{+41.0\text{ dBm}} & (\text{Conv. B: } 90\text{ dBFS}) \end{cases}$$
  At $\text{OIP3}_{\text{LNA}} = \text{OIP3}_{\text{LNA, match}}$, LNA and ADC contribute equally ($3\text{ dB}$ IIP3 penalty = $2.0\text{ dB}$ $\text{SFDR}_3$ penalty). With a practical **$+38.5\text{ dBm}$ OIP3 MMIC**, $\text{SFDR}_3(2.4\text{ kHz})$ is still **$97.2\text{–}98.1\text{ dB}$**!

### 2.2 Cascade Performance Table ($B = 2.4\text{ kHz}$, $\text{NF}_{\text{LNA}} = 1.5\text{ dB}$ [and $3.0\text{ dB}$ in parens])

| Mode | LNA $\text{OIP3}$ | Net Gain $G_{\text{net}}$ | Cascaded $\text{NF}_{\text{sys}}$ | $\text{MDS}_{0\text{dB}}$ ($2.4\text{ kHz}$) | Full-Scale Clip Level | Input $\text{IIP3}$ (Conv A / Conv B) | $\text{SFDR}_3$ in $2.4\text{ kHz}$ (Conv A / Conv B) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **LNA OFF (Bypass)** | N/A | $-4.3\text{ dB}$ | **$32.20\text{ dB}$** | $-107.97\text{ dBm}$ | **$+8.30\text{ dBm}$** | **$+46.30$ / $+42.80\text{ dBm}$** | **$102.85$ / $100.52\text{ dB}$** |
| **LNA ON ($G=15\text{ dB}$)** | $+34.5\text{ dBm}$ (`GVA-84+`) | $+10.7\text{ dB}$ | **$17.37\text{ dB}$** ($17.44$) | $-122.80\text{ dBm}$ | **$-6.70\text{ dBm}$** | $+20.89$ / $+20.42\text{ dBm}$ | $95.79$ / $95.48\text{ dB}$ |
| **LNA ON ($G=15\text{ dB}$)** | **$+38.5\text{ dBm}$** (`PHA-13LN+`) | $+10.7\text{ dB}$ | **$17.37\text{ dB}$** ($17.44$) | $-122.80\text{ dBm}$ | **$-6.70\text{ dBm}$** | **$+24.33$ / $+23.36\text{ dBm}$** | **$98.09$ / $97.44\text{ dB}$** |
| **LNA ON ($G=15\text{ dB}$)** | **$+44.5 / +41.0\text{ dBm}$** (Match) | $+10.7\text{ dB}$ | **$17.37\text{ dB}$** ($17.44$) | $-122.80\text{ dBm}$ | **$-6.70\text{ dBm}$** | **$+28.29$ / $+24.79\text{ dBm}$** | **$100.73$ / $98.40\text{ dB}$** |
| **LNA ON ($G=20\text{ dB}$)** | $+34.5\text{ dBm}$ (`GVA-84+`) | $+15.7\text{ dB}$ | **$12.72\text{ dB}$** ($12.92$) | $-127.45\text{ dBm}$ | **$-11.70\text{ dBm}$** | $+15.89$ / $+15.42\text{ dBm}$ | $95.56$ / $95.25\text{ dB}$ |
| **LNA ON ($G=20\text{ dB}$)** | **$+38.5\text{ dBm}$** (`PHA-13LN+`) | $+15.7\text{ dB}$ | **$12.72\text{ dB}$** ($12.92$) | $-127.45\text{ dBm}$ | **$-11.70\text{ dBm}$** | **$+19.33$ / $+18.36\text{ dBm}$** | **$97.85$ / $97.21\text{ dB}$** |
| **LNA ON ($G=20\text{ dB}$)** | **$+44.5 / +41.0\text{ dBm}$** (Match) | $+15.7\text{ dB}$ | **$12.72\text{ dB}$** ($12.92$) | $-127.45\text{ dBm}$ | **$-11.70\text{ dBm}$** | **$+23.29$ / $+19.79\text{ dBm}$** | **$100.49$ / $98.16\text{ dB}$** |

---

## 3. Buck Post-Filter Design (`TPS62A01A` / `02A` @ $2.4\text{ MHz}$)

### 3.1 Required Attenuation & `TPS7A20` PSRR Fact-Check
- **Input Ripple Level**: $20\text{ mV}_{\text{pp}}$ at $2.4\text{ MHz}$ is $20\log_{10}(20\text{ mV}_{\text{pp}} / 2000\text{ mV}_{\text{pp}}) = \mathbf{-40.0\text{ dBFS}}$.
- **Target ADC Spur Floor**: At $f_s = 80\text{ MSPS}$ ($\text{SNR}_0 = 74.1\text{ dBFS}$), the $2.4\text{ kHz}$ noise floor is $-74.1 - 10\log_{10}(40\text{e6}/2400) = \mathbf{-116.32\text{ dBFS}}$.
  - For **$-10\text{ dB}$ margin below $2.4\text{ kHz}$ noise floor ($-126.3\text{ dBFS}$)**: Required total path attenuation $A_{\text{tot}} \ge -40.0 - (-126.32) = \mathbf{86.3\text{ dB}}$.
  - For **$-20\text{ dB}$ margin ($-136.3\text{ dBFS}$, invisible on narrow FFT waterfall)**: $A_{\text{tot}} \ge \mathbf{96.3\text{ dB}}$.
- **`TPS7A20` PSRR Datasheet Fact-Check (`DISPUTED` on $55\text{–}60\text{ dB}$ @ $1\text{ MHz}$)**:
  - Per TI `TPS7A20` datasheet (SBVS338, Electrical Characteristics & Fig. 6-1 at $I_{\text{OUT}} = 300\text{ mA}, V_{\text{DO}} = 1.0\text{ V}$): PSRR is $60\text{ dB}$ at **$100\text{ kHz}$**, drops to **$45\text{ dB}$ at $1.0\text{ MHz}$**, and rolls off to **$\sim 38\text{ dB}$ @ $2.4\text{ MHz}$**, **$\sim 33\text{ dB}$ @ $4.8\text{ MHz}$**, and **$\sim 30\text{ dB}$ @ $7.2\text{ MHz}$**.
  - Below we compute required LC post-filter attenuation for **both** the conservative TI datasheet curve ($38 / 33 / 30\text{ dB}$) and the optimistic $55 / 49 / 45\text{ dB}$ assumption, with $\text{PSRR}_{\text{ADC}} = 40\text{ dB}$.

### 3.2 Critically Damped Series-$R$ + $1.0\,\mu\text{H}$ LC Post-Filter Design
- **Why a $1.0\,\mu\text{H}$ Inductor Beats a Ferrite Bead at $2.4\text{ MHz}$**: A $120\,\Omega\text{ @ }100\text{ MHz}$ ferrite bead has only $3\text{–}6\,\Omega$ impedance at $2.4\text{ MHz}$, whereas a **$1.0\,\mu\text{H}$ 0603/0805 inductor** ($R_{\text{DC}} = 0.10\,\Omega$) has $|Z_L| = 15.1\,\Omega$ @ $2.4\text{ MHz}$, $30.2\,\Omega$ @ $4.8\text{ MHz}$, and $45.2\,\Omega$ @ $7.2\text{ MHz}$.
- **Simple Series Damping (Zero Peaking, No Bulk Electrolytic Needed)**:
  - Shunt capacitor bank before the `TPS7A2018` LDOs: **$C_1 = 10\,\mu\text{F}$ (0603 X7R, $\text{ESL}=0.5\text{ nH}, \text{ESR}=5\text{ m}\Omega$, $f_{\text{SRF}}=2.25\text{ MHz}$) $\parallel C_2 = 1.0\,\mu\text{F}$ (0402 X7R, $\text{ESL}=0.4\text{ nH}, \text{ESR}=10\text{ m}\Omega$, $f_{\text{SRF}}=7.96\text{ MHz}$)**.
  - Characteristic impedance: $Z_0 = \sqrt{L_f / (C_1 + C_2)} = \sqrt{1.0\,\mu\text{H} / 11\,\mu\text{F}} = \mathbf{0.302\,\Omega}$ ($f_0 = 48.0\text{ kHz}$).
  - Adding a **$R_{\text{damp}} = 0.47\,\Omega$ (0402) resistor in series with $L_f = 1.0\,\mu\text{H}$** yields $\zeta = \frac{0.10 + 0.47}{2 \times 0.302} = \mathbf{0.94}$ (**zero resonant peaking: max gain $= -0.10\text{ dB}$ across $1\text{ kHz–}20\text{ MHz}$**), while dropping only $65\text{ mA} \times 0.57\,\Omega = \mathbf{37\text{ mV}}$ out of the $1.5\text{ V}$ LDO headroom ($3.3\text{ V} \to 1.8\text{ V}$)!

| Harmonic Frequency | $\text{PSRR}_{\text{LDO}}$ (TI DS / Opt.) | $\text{PSRR}_{\text{ADC}}$ (Assumed) | Req. Total Atten. ($-10\text{ dB} / -20\text{ dB}$ vs. $2.4\text{ kHz}$ floor) | Req. LC Filter Atten. (TI DS, $-10 / -20\text{ dB}$) | Req. LC Filter Atten. (Opt., $-10 / -20\text{ dB}$) | Actual Damped $1\,\mu\text{H}$ LC Atten. (Chip / w/ $+0.5\text{ nH}$ Via ESL) | Resulting ADC Spur Level |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **$2.4\text{ MHz}$ ($f_{\text{sw}}$)** | $38\text{ dB}$ / $55\text{ dB}$ | $40\text{ dB}$ | **$86.3$ / $96.3\text{ dB}$** | **$8.3$ / $18.3\text{ dB}$** | $0.0$ / $1.3\text{ dB}$ | **$69.5\text{ dB}$** ($62.6\text{ dB}$ w/ via) | **$-180.6\text{ dBFS}$** (PASS by $>54\text{ dB}$) |
| **$4.8\text{ MHz}$ ($2 f_{\text{sw}}$)** | $33\text{ dB}$ / $49\text{ dB}$ | $40\text{ dB}$ | **$86.3$ / $96.3\text{ dB}$*** | **$13.3$ / $23.3\text{ dB}$** | $0.0$ / $7.3\text{ dB}$ | **$65.0\text{ dB}$** ($65.6\text{ dB}$ w/ via) | **$-178.6\text{ dBFS}$** (PASS by $>52\text{ dB}$) |
| **$7.2\text{ MHz}$ ($3 f_{\text{sw}}$)** | $30\text{ dB}$ / $45\text{ dB}$ | $40\text{ dB}$ | **$86.3$ / $96.3\text{ dB}$*** | **$16.3$ / $26.3\text{ dB}$** | $1.3$ / $11.3\text{ dB}$ | **$73.0\text{ dB}$** ($71.1\text{ dB}$ w/ via) | **$-181.1\text{ dBFS}$** (PASS by $>54\text{ dB}$) |

*\*Conservatively assumes full $20\text{ mV}_{\text{pp}}$ at harmonics ($4.8/7.2\text{ MHz}$ are actually $12\text{–}19\text{ dB}$ lower).*
