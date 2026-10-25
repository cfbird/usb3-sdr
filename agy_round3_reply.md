Both [round3.md](file:///home/user1/collab/projects/usb3-sdr/notes/round3.md) and [round3.py](file:///home/user1/collab/projects/usb3-sdr/notes/round3.py) have been written and verified. Below is the complete summary.

---

### 1. LNA Analysis (`GVA-84+` vs. Alternatives) & Bias Network (`0.1–32 MHz` vs. `≥10 MHz`)

#### 1.1 `GVA-84+` Datasheet Audit (`DISPUTED` as HF LNA choice)
Per the **Mini-Circuits `GVA-84+` datasheet** ($+25^\circ\text{C}$, $50\,\Omega$), the device is an InGaP HBT Darlington MMIC rated `"DC to 7 GHz"`, with its **lowest characterized points at $50\text{ MHz}$ and $100\text{ MHz}$** (nothing is characterized below $50\text{ MHz}$, where low-frequency cutoff is external-bias-limited and HBT $1/f$ noise rises):
- **Gain ($S_{21}$)**: $24.0\text{ dB}$ @ $50\text{ MHz}$; $24.1\text{ dB}$ typ ($22.9\text{–}25.3\text{ dB}$) @ $100\text{ MHz}$.
- **Noise Figure ($\text{NF}$)**: **$5.4\text{ dB}$ typ @ $50\text{ MHz}$**; **$5.5\text{ dB}$ typ ($6.5\text{ dB}$ max) @ $100\text{ MHz}$**.
- **Linearity**: **$\text{OIP3} = +34.5\text{ dBm}$ @ $50\text{ MHz}$** ($+35.8\text{ to }+36.7\text{ dBm}$ @ $100\text{ MHz}$); $P_{1\text{dB}} = +19.8\text{ dBm}$ @ $50\text{ MHz}$.
- **Bias ($V_d, I_d$)**: **$V_d = +5.0\text{ V}$ nominal ($4.8\text{ V}$ min, $5.2\text{ V}$ max)**, **$I_d = 108\text{ mA}$ typ ($85\text{–}130\text{ mA}$)** ($540\text{ mW}$).

**Why `GVA-84+` Fails for This Receiver**:
1. **Zero Bias Headroom from $5\text{ V}$ USB (and cannot run from $3.3\text{ V}$)**: Because $V_d \ge 4.8\text{ V}$ ($5.0\text{ V}$ nom) is required directly at the MMIC output pin, biasing from $5.0\text{ V}$ USB ($4.75\text{–}5.25\text{ V}$) requires $R_{\text{bias}} = \frac{5.0 - 5.0}{0.108} = \mathbf{0\,\Omega}$ (no DC current ballast!). Even a $3.5\,\Omega$ DC resistance in a $1\text{ mH}$ choke drops $108\text{ mA} \times 3.5\,\Omega = 0.38\text{ V}$, starving $V_d$ to $4.62\text{ V} < 4.8\text{ V}$. It cannot operate from $3.3\text{ V}$ ($2V_{BE}$ Darlington stack).
2. **Poor NF ($5.4\text{–}6.5\text{ dB}$)**: Violates the $\text{NF} \le 3\text{ dB}$ requirement.
3. **Excessive Gain ($24.0\text{ dB}$) Hurts Input IP3**: $\text{IIP3} = +34.5 - 24.0 = +10.5\text{ dBm}$.

#### 1.2 Bias Tee Math ($X_L \ge 10 R_0 = 500\,\Omega$ at $100\text{ kHz}$) & Stacked Choke
- **Choke Inductance**: $L_{\text{choke}} \ge \frac{500}{2\pi(100\text{ kHz})} = \mathbf{795.8\,\mu\text{H}} \implies$ E12 **$820\,\mu\text{H}$ or $1.0\text{ mH}$**.
- **SRF / Size Problem**: A single $1.0\text{ mH}$, $\ge 100\text{ mA}$ inductor (1210/3015 size) has $C_p \approx 15\text{–}25\text{ pF}$ ($\text{SRF} \approx \mathbf{1.0\text{–}1.3\text{ MHz}}$). Above $1.3\text{ MHz}$ it is capacitive ($|Z| = 265\,\Omega$ at $30\text{ MHz}$ for $C_p = 20\text{ pF}$), detuning LPF #2.
- **3-Stage Stacked Choke ($0.1\text{–}50\text{ MHz}$, $|Z| \ge 620\,\Omega$, IL $\le 0.21\text{ dB}$)**:
  $$\text{RF Pin} \to \underbrace{1.0\,\mu\text{H}}_{\text{0603, SRF } 350\text{MHz}} \to \underbrace{(22\,\mu\text{H} \parallel 1.5\text{ k}\Omega)}_{\text{0805, SRF } 40\text{MHz}} \to \underbrace{(1.0\text{ mH} \parallel 2.2\text{ k}\Omega)}_{\text{1210, SRF } 1.1\text{MHz}} \to R_{\text{bias}} \to V_{CC}$$
- **Coupling Caps ($100\text{ kHz}$)**: $C_{-3\text{dB}} = \frac{1}{2\pi(100\text{ kHz})(50\,\Omega)} = \mathbf{31.8\text{ nF}}$; for $<0.04\text{ dB}$ droop ($X_C \le 5\,\Omega$), $C \ge \mathbf{318\text{ nF}} \implies$ use **$470\text{ nF}$ or $1.0\,\mu\text{F}$ (0603 X7R) $\parallel 10\text{ nF}$ (0402 C0G)**.

#### 1.3 Recommended LNA Alternatives & "No LNA Below 10 MHz" Simplification

| LNA Candidate | Characterized Range | Gain | NF | OIP3 | Bias ($V_d, I_d$, $R_{\text{bias}}$ from 5V) | Verdict / Choke Simplification |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`GVA-84+`** | DC–7 GHz (char $\ge 50\text{ MHz}$) | $24.0\text{ dB}$ | $5.4\text{ dB}$ | $+34.5\text{ dBm}$ | $5.0\text{ V}, 108\text{ mA}$ ($R_{\text{bias}} = 0\,\Omega$!) | **REJECT**: No bias headroom on 5V, NF $= 5.4\text{ dB}$. |
| **`PHA-13LN+` / `LHA-13LN+` + $3\text{ dB}$ out pad** | **1–1000 MHz** (char @ 1, 10, 50 MHz) | $22.2\text{ dB}$ ($19.2\text{ dB}$ net) | **$1.0\text{–}1.2\text{ dB}$** | **$+38.5\text{ dBm}$** ($+35.5\text{ dBm}$ net) | Supports **$3.0\text{–}3.3\text{ V}$ @ $71\text{ mA}$** ($R_{\text{bias}} = \mathbf{24\,\Omega}$ from 5V!) | **BEST $1\text{–}32\text{ MHz}$ MMIC**: Characterized to $1\text{ MHz}$; $3\text{ dB}$ output pad stabilizes LPF#2 stopband reflections. |
| **`GVA-62+` (used $\ge 10\text{ MHz}$ only)** | **10–6000 MHz** | **$15.2\text{ dB}$** | **$1.5\text{ dB}$** | **$+39.0\text{ dBm}$** | $4.8\text{–}5.0\text{ V}$ @ $82\text{ mA}$ (or **Norton BJT `BFU550A`** @ $3.3\text{V}/35\text{mA}$) | **BEST SYSTEM CHOICE ("No LNA $<10\text{ MHz}$")**: ITU rural noise $<10\text{ MHz}$ is $\ge 39.5\text{ dB} \gg \text{NF}_{\text{off}}$ ($32.2\text{ dB}$). Bypassing LNA $<10\text{ MHz}$ shrinks the choke to a **single $15\,\mu\text{H}$ 0805 inductor + $100\text{ nF}$ caps**! |

---

### 2. Dynamic Range / IP3 Cascade Budget (`VERIFIED` via Friis & Cascaded IIP3)

- **Losses**: $L_{\text{pre}} = 0.3\text{ (sw)} + 1.5\text{ (LPF1+notch)} = \mathbf{1.8\text{ dB}}$; $L_{\text{post}} = 1.5\text{ (LPF2)} + 1.0\text{ (balun)} = \mathbf{2.5\text{ dB}}$ ($L_{\text{tot}} = \mathbf{4.3\text{ dB}}$; note `ADT4-6T+` datasheet midband loss is $0.3\text{–}0.4\text{ dB}$, so $1.0\text{ dB}$ includes $0.6\text{ dB}$ margin).
- **AD9649-80 $\text{IIP3}_{\text{ADC}}$**: With $P_{\text{FS}} = +4.0\text{ dBm}$, each $-7\text{ dBFS}$ tone is $P_{\text{tone}} = -3.0\text{ dBm}$:
  - **Conv. A (`90 dBc` below tone)**: $\text{IIP3}_{\text{ADC}} = -3.0 + 90/2 = \mathbf{+42.0\text{ dBm}}$.
  - **Conv. B (ADI `90 dBFS` $= 83\text{ dBc}$ below tone)**: $\text{IIP3}_{\text{ADC}} = -3.0 + 83/2 = \mathbf{+38.5\text{ dBm}}$.
- **Required LNA OIP3 so LNA IMD Doesn't Dominate ADC**:
  Referred to the LNA output node, the ADC's intercept is $\text{OIP3}_{\text{ADC, at LNA out}} = \text{IIP3}_{\text{ADC}} + L_{\text{post}}$ (**independent of $G_{\text{LNA}}$ and $L_{\text{pre}}$!**):
  $$\text{OIP3}_{\text{LNA}} \ge \text{IIP3}_{\text{ADC}} + L_{\text{post}} = \begin{cases} \mathbf{+44.5\text{ dBm}} & (\text{Conv. A: } 90\text{ dBc}) \\ \mathbf{+41.0\text{ dBm}} & (\text{Conv. B: } 90\text{ dBFS}) \end{cases}$$
  At this point, LNA and ADC contribute equally ($3\text{ dB}$ IIP3 / $2\text{ dB}$ $\text{SFDR}_3$ split). Even with a **$+38.5\text{ dBm}$ OIP3 MMIC**, $\text{SFDR}_3(2.4\text{ kHz})$ stays within $2.0\text{–}2.6\text{ dB}$ of the match point:

| Mode ($\text{NF}_{\text{LNA}} = 1.5\text{ dB}$ [$3.0\text{ dB}$ in parens]) | LNA $\text{OIP3}$ | Net Gain | Cascaded $\text{NF}_{\text{sys}}$ | $\text{MDS}_{0\text{dB}}$ ($2.4\text{ kHz}$) | Blocking / Clip Level | Input $\text{IIP3}$ (Conv A / B) | $\text{SFDR}_3$ in $2.4\text{ kHz}$ (Conv A / B) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **LNA OFF (Bypass)** | N/A | $-4.3\text{ dB}$ | **$32.20\text{ dB}$** | $-107.97\text{ dBm}$ | **$+8.30\text{ dBm}$** | **$+46.30$ / $+42.80\text{ dBm}$** | **$102.85$ / $100.52\text{ dB}$** |
| **LNA ON ($G=15\text{ dB}$)** | $+34.5\text{ dBm}$ (`GVA-84+`) | $+10.7\text{ dB}$ | **$17.37\text{ dB}$** ($17.44$) | $-122.80\text{ dBm}$ | **$-6.70\text{ dBm}$** | $+20.89$ / $+20.42\text{ dBm}$ | $95.79$ / $95.48\text{ dB}$ |
| **LNA ON ($G=15\text{ dB}$)** | **$+38.5\text{ dBm}$** (`PHA-13LN+`) | $+10.7\text{ dB}$ | **$17.37\text{ dB}$** ($17.44$) | $-122.80\text{ dBm}$ | **$-6.70\text{ dBm}$** | **$+24.33$ / $+23.36\text{ dBm}$** | **$98.09$ / $97.44\text{ dB}$** |
| **LNA ON ($G=15\text{ dB}$)** | **$+44.5 / +41.0\text{ dBm}$** (Match) | $+10.7\text{ dB}$ | **$17.37\text{ dB}$** ($17.44$) | $-122.80\text{ dBm}$ | **$-6.70\text{ dBm}$** | **$+28.29$ / $+24.79\text{ dBm}$** | **$100.73$ / $98.40\text{ dB}$** |
| **LNA ON ($G=20\text{ dB}$)** | $+34.5\text{ dBm}$ (`GVA-84+`) | $+15.7\text{ dB}$ | **$12.72\text{ dB}$** ($12.92$) | $-127.45\text{ dBm}$ | **$-11.70\text{ dBm}$** | $+15.89$ / $+15.42\text{ dBm}$ | $95.56$ / $95.25\text{ dB}$ |
| **LNA ON ($G=20\text{ dB}$)** | **$+38.5\text{ dBm}$** (`PHA-13LN+`) | $+15.7\text{ dB}$ | **$12.72\text{ dB}$** ($12.92$) | $-127.45\text{ dBm}$ | **$-11.70\text{ dBm}$** | **$+19.33$ / $+18.36\text{ dBm}$** | **$97.85$ / $97.21\text{ dB}$** |
| **LNA ON ($G=20\text{ dB}$)** | **$+44.5 / +41.0\text{ dBm}$** (Match) | $+15.7\text{ dB}$ | **$12.72\text{ dB}$** ($12.92$) | $-127.45\text{ dBm}$ | **$-11.70\text{ dBm}$** | **$+23.29$ / $+19.79\text{ dBm}$** | **$100.49$ / $98.16\text{ dB}$** |

---

### 3. Buck Post-Filter (`TPS62A01A/02A` @ $2.4\text{ MHz}$) (`DISPUTED` on TPS7A20 1 MHz PSRR; `VERIFIED` filter)

- **Required Total Attenuation**:
  - $20\text{ mV}_{\text{pp}}$ ripple vs. $2.0\text{ V}_{\text{pp}}$ FS $= \mathbf{-40.0\text{ dBFS}}$.
  - `AD9649-80` noise floor in $2.4\text{ kHz}$: $-74.1 - 10\log_{10}(40\text{e6}/2400) = \mathbf{-116.32\text{ dBFS}}$.
  - For **$-10\text{ dB}$ margin below $2.4\text{ kHz}$ floor ($-126.3\text{ dBFS}$)**: $A_{\text{tot}} \ge \mathbf{86.3\text{ dB}}$ (or **$96.3\text{ dB}$** for $-20\text{ dB}$ waterfall margin).
- **`TPS7A20` PSRR Fact-Check (`DISPUTED`)**: Per TI `TPS7A20` datasheet (SBVS338, Fig. 6-1, $I_{\text{OUT}}=300\text{ mA}, V_{\text{DO}}=1\text{ V}$), PSRR is $60\text{ dB}$ at **$100\text{ kHz}$**, drops to **$45\text{ dB}$ at $1\text{ MHz}$** (not $55\text{–}60\text{ dB}$), and rolls off to **$\sim 38\text{ dB}$ @ $2.4\text{ MHz}$**, **$\sim 33\text{ dB}$ @ $4.8\text{ MHz}$**, and **$\sim 30\text{ dB}$ @ $7.2\text{ MHz}$**.
- **Filter Sizing & Damping**:
  - Use **$L_f = 1.0\,\mu\text{H}$** (0603/0805 shielded inductor, $R_{\text{DC}} = 0.10\,\Omega$, $|Z_L| = 15.1\,\Omega$ @ $2.4\text{ MHz}$, vs. only $3\text{–}6\,\Omega$ for a ferrite bead) feeding **$C_1 = 10\,\mu\text{F}$ (0603 X7R, $\text{ESL}=0.5\text{ nH}, f_{\text{SRF}}=2.25\text{ MHz}$) $\parallel C_2 = 1.0\,\mu\text{F}$ (0402 X7R, $\text{ESL}=0.4\text{ nH}, f_{\text{SRF}}=7.96\text{ MHz}$)**.
  - **Critical Damping**: With $Z_0 = \sqrt{1\,\mu\text{H} / 11\,\mu\text{F}} = \mathbf{0.302\,\Omega}$ ($f_0 = 48.0\text{ kHz}$), placing a single **$R_{\text{damp}} = 0.47\,\Omega$ (0402) resistor in series with $L_f$** achieves $\zeta = \frac{0.10 + 0.47}{2 \times 0.302} = \mathbf{0.94}$ (**zero peaking: max gain $= -0.10\text{ dB}$ across $1\text{ kHz–}20\text{ MHz}$**) while dropping only $65\text{ mA} \times 0.57\,\Omega = \mathbf{37\text{ mV}}$ out of the $1.5\text{ V}$ LDO headroom!

| Frequency | $\text{PSRR}_{\text{LDO}}$ (TI DS / Opt.) | $\text{PSRR}_{\text{ADC}}$ | Req. LC Atten. (TI DS, $-10/-20\text{ dB}$ margin) | Req. LC Atten. (Opt., $-10/-20\text{ dB}$ margin) | Actual Damped $1\,\mu\text{H}$ LC Atten. (Chip / w/ $+0.5\text{ nH}$ Via ESL) | Resulting ADC Spur Level |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **$2.4\text{ MHz}$** | $38\text{ dB}$ / $55\text{ dB}$ | $40\text{ dB}$ | **$8.3$ / $18.3\text{ dB}$** | $0.0$ / $1.3\text{ dB}$ | **$69.5\text{ dB}$** ($62.6\text{ dB}$ w/ via) | **$-180.6\text{ dBFS}$** (PASS by $>54\text{ dB}$) |
| **$4.8\text{ MHz}$** | $33\text{ dB}$ / $49\text{ dB}$ | $40\text{ dB}$ | **$13.3$ / $23.3\text{ dB}$** | $0.0$ / $7.3\text{ dB}$ | **$65.0\text{ dB}$** ($65.6\text{ dB}$ w/ via) | **$-178.6\text{ dBFS}$** (PASS by $>52\text{ dB}$) |
| **$7.2\text{ MHz}$** | $30\text{ dB}$ / $45\text{ dB}$ | $40\text{ dB}$ | **$16.3$ / $26.3\text{ dB}$** | $1.3$ / $11.3\text{ dB}$ | **$73.0\text{ dB}$** ($71.1\text{ dB}$ w/ via) | **$-181.1\text{ dBFS}$** (PASS by $>54\text{ dB}$) |

### Runnable Python Verification
```bash
python3 /home/user1/collab/projects/usb3-sdr/notes/round3.py
```
