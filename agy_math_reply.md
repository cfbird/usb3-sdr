Full derivations, parametric equations, and verification scripts have been written to [math.md](file:///home/user1/collab/projects/usb3-sdr/notes/math.md) and verified with [verify_math.py](file:///home/user1/collab/projects/usb3-sdr/notes/verify_math.py). Below is the complete summary with derivations and runnable Python checks.

---

### 1. USB3 Throughput Budget (`VERIFIED` via bus-rate derivation)

Both **FX3 (`CYUSB3014`)** and **FT601Q** have a $32\text{-bit} \times 100\text{ MHz} = 400\text{ MB/s}$ ($10^6\text{ B/s}$) synchronous parallel bus ceiling:
- **FX3**: $350\text{–}380\text{ MB/s}$ ($333.8\text{–}362.4\text{ MiB/s}$) sustained bulk-IN (512 KB internal SRAM absorbs host xHCI latency).
- **FT601**: $300\text{–}340\text{ MB/s}$ ($286.1\text{–}324.2\text{ MiB/s}$) claimed, often $240\text{–}300\text{ MB/s}$ without deep FPGA FIFO buffering (only 16 KB internal FIFO).
- **Byte rate**: $R_{\text{byte}} = f_s \cdot (B_{\text{wire}} / 8)$ for real samples; $R_{\text{byte,IQ}} = 4 \, f_{s,\text{IQ}}$ for complex $16\text{I}+16\text{Q}$ ($4\text{ B/sample}$).

| ADC Rate $f_s$ | 16-bit Unpacked ($2\text{ B/s}$) | 14-bit Packed ($1.75\text{ B/s}$) | 12-bit Packed ($1.5\text{ B/s}$) | FX3 ($350\text{–}380\text{ MB/s}$) | FT601 ($300\text{–}340\text{ MB/s}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **65 MSPS** | $130.0\text{ MB/s}$ ($124.0\text{ MiB/s}$) | $113.75\text{ MB/s}$ | $97.50\text{ MB/s}$ | **PASS** (34–37%) | **PASS** (38–43%) |
| **105 MSPS** | $210.0\text{ MB/s}$ ($200.3\text{ MiB/s}$) | $183.75\text{ MB/s}$ | $157.50\text{ MB/s}$ | **PASS** (55–60%) | **PASS** (62–70%) |
| **125 MSPS** | $250.0\text{ MB/s}$ ($238.4\text{ MiB/s}$) | $218.75\text{ MB/s}$ | $187.50\text{ MB/s}$ | **PASS** (66–71%) | **PASS / Tight** (74–83%*) |
| **130 MSPS** | $260.0\text{ MB/s}$ ($248.0\text{ MiB/s}$) | $227.50\text{ MB/s}$ | $195.00\text{ MB/s}$ | **PASS** (68–74%) | **MARGINAL** (76–87%*) |
| **160 MSPS** | $320.0\text{ MB/s}$ ($305.2\text{ MiB/s}$) | $280.00\text{ MB/s}$ | $240.00\text{ MB/s}$ | **PASS** (84–91%) | **FAIL (16b)** / **PASS (14b/12b)** |
| **Max Rate** | **FX3: 175–190 MSPS**<br>**FT601: 150–170 MSPS** | **FX3: 200–217 MSPS**<br>**FT601: 171–194 MSPS** | **FX3: 233–253 MSPS**<br>**FT601: 200–226 MSPS** | Hard GPIF ceiling:<br>$200\text{ MSPS}$ @ 16b | *Needs FPGA FIFO/SDRAM on FT601 |

- **Complex $16\text{I}+16\text{Q}$ DDC Output Bandwidths ($4\text{ B/sample}$, $B_{80\%} = 0.8 \, f_{s,\text{IQ}}$)**:
  - **FX3**: $f_{s,\text{IQ},\max} = \mathbf{87.5\text{–}95.0\text{ MSPS}} \implies B_{80\%} = \mathbf{70.0\text{–}76.0\text{ MHz}}$.
  - **FT601**: $f_{s,\text{IQ},\max} = \mathbf{75.0\text{–}85.0\text{ MSPS}} \implies B_{80\%} = \mathbf{60.0\text{–}68.0\text{ MHz}}$.
  - *Note*: At $125\text{ MSPS}$, the full $62.5\text{ MHz}$ Nyquist zone takes $250\text{ MB/s}$ whether sent as 16-bit real @ $125\text{ MSPS}$ or 16I+16Q complex @ $62.5\text{ MSPS}$. Decimating in the FPGA ($R=64 \Rightarrow 1.953125\text{ MSPS} = \mathbf{7.8125\text{ MB/s}}$ per slice, $B_{80\%} = \mathbf{1.5625\text{ MHz}}$) offloads the host CPU, allows streaming **24I+24Q** ($11.72\text{ MB/s}$) to preserve decimated dynamic range, or supports **multi-slice receivers**.

---

### 2. Clock Jitter Budget (`VERIFIED` via noise-power sum derivation)

**Derivation**: Combining uncorrelated ADC thermal/quantization noise ($10^{-\text{SNR}_0/10}$) and full-scale aperture/clock jitter noise ($(2\pi f_{\text{in}} t_{j,\text{total}})^2$):
$$10^{-\text{SNR}_{\text{total}}/10} = 10^{-\text{SNR}_0/10} + (2\pi f_{\text{in}} t_{j,\text{total}})^2 \le 10^{-(\text{SNR}_0 - \Delta\text{SNR})/10}$$
$$t_{j,\text{total}} \le \frac{10^{-\text{SNR}_0/20}\sqrt{10^{\Delta\text{SNR}/10} - 1}}{2\pi f_{\text{in}}}, \qquad t_{j,\text{clk}} \le \sqrt{t_{j,\text{total}}^2 - t_{j,\text{ADC}}^2}$$
For $\text{SNR}_0 = 77\text{ dBFS}$ and $\Delta\text{SNR} \le 1.0\text{ dB}$, required $\text{SNR}_{\text{jitter}} \ge \mathbf{82.87\text{ dBFS}}$:

| Input Freq $f_{\text{in}}$ | Max Total Jitter $t_{j,\text{total}}$ | Max Clock Jitter ($t_{j,\text{ADC}} = 70\text{ fs}$, e.g. LTC2208) | Max Clock Jitter ($t_{j,\text{ADC}} = 100\text{ fs}$, e.g. AD9265/LTC2165) | Max Clock Jitter ($t_{j,\text{ADC}} = 150\text{ fs}$) |
| :--- | :--- | :--- | :--- | :--- |
| **30 MHz** | **381.3 fs** | **374.8 fs** | **368.0 fs** | **350.6 fs** |
| **60 MHz** | **190.7 fs** | **177.3 fs** | **162.3 fs** | **117.7 fs** |
| **150 MHz** (undersampled) | **76.3 fs** | **30.3 fs** | **0 fs (Impossible @ 0 dBFS: $\Delta\text{SNR}=1.60\text{ dB}$ w/ ideal clock)** | **0 fs ($\Delta\text{SNR}=2.99\text{ dB}$ w/ ideal clock)** |

- *Undersampling note*: The $76.3\text{ fs}$ limit at $150\text{ MHz}$ assumes a **full-scale $0\text{ dBFS}$ blocker** at $150\text{ MHz}$. If front-end bandpass filtering keeps the strongest $150\text{ MHz}$ blocker $\le -6\text{ dBFS}$ (or $-10\text{ dBFS}$), allowable $t_{j,\text{total}}$ relaxes to **$152.5\text{ fs}$** (or **$241.2\text{ fs}$**). Never route the sample clock through the FPGA.

---

### 3. Dynamic Range, MDS, Implied NF & LNA Cascade (`VERIFIED` via Friis & ITU-R P.372-16)

**Derivation**: At $f_s = 125\text{ MSPS}$ ($f_s/2 = 62.5\text{ MHz} \implies 10\log_{10}(f_s/2) = 77.96\text{ dB}\cdot\text{Hz}$), $\text{SNR}_0 = 77.0\text{ dBFS}$, and $P_{\text{FS}} = +4.0\text{ dBm}$ *(note: $2\text{ V}_{\text{pp}}$ into $200\,\Omega$ diff via a 1:4 transformer from $50\,\Omega$ is $2.5\text{ mW} = +3.98\text{ dBm}$; $2\text{ V}_{\text{pp}}$ directly into $50\,\Omega$ is $+10.0\text{ dBm}$)*:
- **Noise Spectral Density**:
  $$\text{NSD}_{\text{dBFS/Hz}} = -77.0 - 77.96 = \mathbf{-154.96\text{ dBFS/Hz}}, \qquad \text{NSD}_{\text{dBm/Hz}} = +4.0 - 154.96 = \mathbf{-150.96\text{ dBm/Hz}}$$
- **Implied Bare ADC Noise Figure** (vs. $k_B T_0 = -173.98\text{ dBm/Hz}$ at $290\text{ K}$):
  $$\text{NF}_{\text{ADC}} = -150.96 - (-173.98) = \mathbf{23.02\text{ dB}} \quad (\mathbf{24.5\text{–}25.0\text{ dB}}\text{ with }1.5\text{–}2.0\text{ dB passive filter/balun loss})$$

| Bandwidth $B$ | Processing Gain $G_p = 10\log_{10}(\frac{f_s/2}{B})$ | Dynamic Range $\text{DR}(B)$ | Noise Floor (dBFS) | $\text{MDS}_{0\text{dB}}$ (Noise Floor, dBm) | $\text{MDS}_{3\text{dB}}$ ($\text{SNR}=3\text{ dB}$, dBm) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **2.4 kHz** | **44.16 dB** | **121.16 dB** | $-121.16\text{ dBFS}$ | **$-117.16\text{ dBm}$** | $-114.16\text{ dBm}$ |
| **10 kHz** | **37.96 dB** | **114.96 dB** | $-114.96\text{ dBFS}$ | **$-110.96\text{ dBm}$** | $-107.96\text{ dBm}$ |
| **200 kHz** | **24.95 dB** | **101.95 dB** | $-101.95\text{ dBFS}$ | **$-97.95\text{ dBm}$** | $-94.95\text{ dBm}$ |
| **2.0 MHz** | **14.95 dB** | **91.95 dB** | $-91.95\text{ dBFS}$ | **$-87.95\text{ dBm}$** | $-84.95\text{ dBm}$ |

**LNA Requirement at $30\text{ MHz}$ (ITU-R P.372-16 External Noise $F_{am} = c - d\log_{10} f_{\text{MHz}}$)**:
Total system noise factor is $f_{\text{tot}} = f_a + f_{\text{sys}} - 1$.
- **Criterion A (System MDS degrades $\le 3\text{ dB}$ vs. antenna noise alone)**: $f_{\text{sys}} \le 1 + (10^{3/10}-1)f_a \approx f_a$ ($\text{NF}_{\text{sys}} \le F_a$).
- **Criterion B (Stricter: Receiver internal noise floor is $3\text{ dB}$ *below* antenna noise, i.e., $1.76\text{ dB}$ MDS degradation)**: $\text{NF}_{\text{sys}} \le F_a - 3\text{ dB}$.
- Using Friis $G_{\text{LNA,min}} = 10\log_{10}\!\left(\frac{f_2 - 1}{f_{\text{sys,target}} - f_{\text{LNA}}}\right)$ with $\text{NF}_{\text{LNA}} = 3.0\text{ dB}$ and $f_2 = 10^{(\text{NF}_{\text{ADC}} + L_{\text{post}})/10}$:

| ITU-R P.372 Model @ 30 MHz | Formula ($f$ in MHz) | $F_a$ @ 30 MHz | Min $G_{\text{LNA}}$ (Crit. A: $\text{NF}_{\text{sys}} \le F_a$, bare / $+1.5\text{ dB}$ loss) | Min $G_{\text{LNA}}$ (Crit. B: $\text{NF}_{\text{sys}} \le F_a - 3\text{ dB}$, bare / $+1.5\text{ dB}$ loss) |
| :--- | :--- | :--- | :--- | :--- |
| **ITU Rural Man-Made** | $67.2 - 27.7\log_{10} f$ | **26.28 dB** | **0 dB (No LNA needed!)** / **0 dB** | **0 dB** / **1.3 dB** |
| **ITU Galactic (Sky floor)** | $52.0 - 23.0\log_{10} f$ | **18.03 dB** | **5.1 dB** / **6.6 dB** | **8.2 dB** / **9.8 dB** |
| **ITU Quiet Rural** | $53.6 - 28.6\log_{10} f$ | **11.35 dB** | **12.0 dB** / **13.5 dB** | **16.1 dB** / **17.6 dB** |

*Recommendation*: Use a **switchable $12\text{–}16\text{ dB}$ LNA ($\text{NF} \approx 2\text{–}3\text{ dB}$)** with a **0 dB bypass** (since literal ITU Rural man-made noise at $\le 30\text{ MHz}$ already exceeds the bare ADC NF, where LNA gain only hurts overload margin).

---

### 4. DDC Design & ECP5 Multiplier Fit (`VERIFIED` via exact Hogenauer transfer function)

**Derivation**: For an $N$-stage CIC ($M=1$) with decimation $R_{\text{CIC}}$ and $B_{\text{in}} = 16\text{ bits}$:
$$|H(f)| = \left|\frac{\sin(\pi R_{\text{CIC}} f / f_s)}{R_{\text{CIC}} \sin(\pi f / f_s)}\right|^N, \qquad B_{\text{growth}} = \lceil N\log_2 R_{\text{CIC}} \rceil, \qquad B_{\max} = 16 + B_{\text{growth}}$$
For $R_{\text{total}} = 64$ ($f_{\text{out}} = 1.953125\text{ MSPS}$, 80% usable passband $B_{80\%} = \mathbf{1.5625\text{ MHz}} \implies f_p = \mathbf{781.25\text{ kHz}}$):
- **Never decimate by $R_{\text{CIC}}=64$ directly to the final rate** for an 80% passband: at $f_p = 0.40 f_{\text{CIC}}$ and first alias $f_{\text{alias}} = 0.60 f_{\text{CIC}}$, alias rejection is only $(0.6/0.4)^N = 3.52\text{ dB/stage}$ relative to the passband edge!
- Instead, decimate by **$R_{\text{CIC}} = 32$** followed by a **$2:1$ Compensating FIR** (or **$R_{\text{CIC}} = 16 \to 2:1\text{ HB} \to 2:1\text{ CFIR}$**):

| Architecture ($R_{\text{total}}=64, f_{\text{out}}=1.953\text{ MSPS}$) | Order $N$ | $R_{\text{CIC}}$ | Bit Growth | $B_{\max}$ | Droop @ $781.25\text{ kHz}$ | Alias Rej. @ $f_{\text{CIC}}-f_p$ (vs. DC) | Alias Rej. (vs. Edge) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Direct CIC** ($R_{\text{CIC}}=64 \to 1:1\text{ CFIR}$) | $N=5$ | 64 | $30\text{ b}$ | $46\text{ b}$ | $-12.10\text{ dB}$ | $29.70\text{ dB}$ | $17.61\text{ dB}$ (Fails) |
| **CIC + 2:1 CFIR** ($R_{\text{CIC}}=32 \to 2:1\text{ CFIR}$) | **$N=5$** | **32** | **25 b** | **41 b** | **$-2.89\text{ dB}$** | **63.06 dB** | **60.16 dB** (Good) |
| **CIC + 2:1 CFIR** ($R_{\text{CIC}}=32 \to 2:1\text{ CFIR}$) | **$N=6$** | **32** | **30 b** | **46 b** | **$-3.47\text{ dB}$** | **75.67 dB** | **72.20 dB** (Recommended) |
| **CIC + HB + CFIR** ($R_{\text{CIC}}=16 \to \text{HB} \to \text{CFIR}$) | **$N=5$** | **16** | **20 b** | **36 b** | **$-0.71\text{ dB}$** | **95.91 dB** | **95.20 dB** (Best DR) |

**ECP5 Multiplier Fit Check (1 DDC @ $f_{\text{clk}} = 125\text{ MHz}$)**:
- **NCO**: **0 mults** (CORDIC) or **1 mult** (Taylor-interpolated BRAM LUT).
- **Real-to-Complex Mixer**: **2 mults** ($x[n]\cos\omega_0 n$, $-x[n]\sin\omega_0 n$).
- **CIC**: **0 mults**.
- **63-tap $2:1$ CFIR (+ optional 19-tap HB)**: At $f_{\text{out}} = 1.953125\text{ MSPS}$, there are **$64\text{ clock cycles/sample}$** at $125\text{ MHz}$.
  - **Time-Multiplexed Polyphase MAC**: **2–4 mults** (1–2 per I/Q rail). **Total = 4–7 mults/DDC** $\implies$ **Fits LFE5U-25F (28 mults, up to 4–7 DDCs)** and **LFE5U-45F (72 mults, up to 10–18 DDCs)**.
  - **Naive Unfolded Parallel FIR**: 32 symmetric taps $\times 2 = 64\text{ mults}$ (**66–67 mults total**) $\implies$ **Fails LFE5U-25F**, barely fits 1 DDC in LFE5U-45F.

---

### 5. Anti-Alias Filter (`VERIFIED` via exact `scipy.signal` order synthesis)

At $f_s = 125\text{ MSPS}$, passband $f_p = 55\text{ MHz}$ aliases with $f_{\text{stop}} = f_s - f_p = \mathbf{70\text{ MHz}}$ (steep transition ratio $\Omega_s = 70/55 = 1.2727$). From Item 3, the $10\text{ kHz}$ noise floor is **$-114.96\text{ dBFS}$ ($-110.96\text{ dBm}$)**:

| Blocker Scenario @ $\ge 70\text{ MHz}$ | Required $A_{\text{stop}}$ | Passband Ripple $R_p$ | Butterworth $N$ | Chebyshev $N$ | Elliptic (Cauer) $N$ |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **$0\text{ dBFS}$ ($+4\text{ dBm}$) $\to$ $10\text{ kHz}$ Floor** | **115.0 dB** | $0.5\text{ dB}$ / $1.0\text{ dB}$ | **60** / **58** | **21** / **21** | **12** / **11** |
| **$-20\text{ dBm}$ FM Blocker $\to$ $10\text{ kHz}$ Floor** | **91.0 dB** | $0.5\text{ dB}$ / $1.0\text{ dB}$ | **48** / **47** | **17** / **17** | **10** / **9** |
| **$0\text{ dBFS}$ $\to$ Full-Nyquist Floor ($-77\text{ dBFS}$)** | **77.0 dB** | $0.5\text{ dB}$ / $1.0\text{ dB}$ | **42** / **40** | **15** / **15** | **9** / **8** |

- *Hardware note*: A single lumped LC filter cannot achieve $115\text{ dB}$ isolation at $70\text{ MHz}$ due to PCB ground/parasitic coupling ($\sim 80\text{ dB}$ practical limit per stage). Split into **two cascaded 7th-order Elliptic LPFs** ($2 \times 64\text{ dB} > 120\text{ dB}$, 3 inductors + 7 caps each) placed before and after the LNA/switch, or a **9th-order Elliptic LPF + 88–108 MHz FM notch**.

---

### 6. PCB Stackup Impedance (`JLC04161H-7628`, $h=0.2104\text{ mm}$, $t=0.035\text{ mm}$) (`VERIFIED` via 2D Laplace & K-J/IPC models)

Because textbook Hammerstad-Jensen / Kirschning-Jansen models assume **uncoated air** ($\varepsilon_r = 1.0$ in the gap) while JLCPCB's calculator (Polar Si9000) models **coated solder mask** ($\varepsilon_{r,\text{SM}} \approx 3.8$ filling the gap and lowering $Z_{\text{diff}}$ by $4\text{–}6\,\Omega$) and uses $\varepsilon_r = 4.6$ for 7628 resin content, both bare and coated/JLC-equivalent widths are tabulated below:

| Target Line | Assumed Spacing $s$ | Bare Analytical ($\varepsilon_r=4.4$, H-J / K-J) | 2D Laplace Field Solver w/ Solder Mask ($\varepsilon_r=4.4$) | Coated / JLC Calculator Equiv. ($\varepsilon_r=4.6$) | Recommended Layout Width $w$ |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **$50\,\Omega$ SE** | N/A | **$0.373\text{ mm}$** ($14.7\text{ mil}$) | **$0.330\text{ mm}$** ($13.0\text{ mil}$) | **$0.315\text{–}0.335\text{ mm}$** ($12.4\text{–}13.2\text{ mil}$) | **$0.34\text{ mm}$** ($13.4\text{ mil}$) |
| **$90\,\Omega$ Diff (USB3)** | **$0.127\text{ mm}$ ($5.0\text{ mil}$)** | $0.299\text{ mm}$ ($11.8\text{ mil}$) | $0.232\text{ mm}$ ($9.1\text{ mil}$) | **$0.235\text{–}0.249\text{ mm}$** ($9.3\text{–}9.8\text{ mil}$) | **$0.24\text{ mm}$** ($9.5\text{ mil}$) |
| **$90\,\Omega$ Diff (USB3)** | **$0.150\text{ mm}$ ($5.9\text{ mil}$)** | $0.318\text{ mm}$ ($12.5\text{ mil}$) | $0.248\text{ mm}$ ($9.8\text{ mil}$) | **$0.255\text{–}0.268\text{ mm}$** ($10.0\text{–}10.6\text{ mil}$) | **$0.26\text{ mm}$** ($10.2\text{ mil}$) |
| **$90\,\Omega$ Diff (USB3)** | **$0.200\text{ mm}$ ($7.9\text{ mil}$)** | $0.347\text{ mm}$ ($13.7\text{ mil}$) | $0.275\text{ mm}$ ($10.8\text{ mil}$) | **$0.285\text{–}0.300\text{ mm}$** ($11.2\text{–}11.8\text{ mil}$) | **$0.29\text{ mm}$** ($11.4\text{ mil}$) |
| **$100\,\Omega$ Diff (LVDS)** | **$0.127\text{ mm}$ ($5.0\text{ mil}$)** | $0.234\text{ mm}$ ($9.2\text{ mil}$) | $0.175\text{ mm}$ ($6.9\text{ mil}$) | **$0.180\text{–}0.195\text{ mm}$** ($7.1\text{–}7.7\text{ mil}$) | **$0.185\text{ mm}$** ($7.3\text{ mil}$) |
| **$100\,\Omega$ Diff (LVDS)** | **$0.150\text{ mm}$ ($5.9\text{ mil}$)** | $0.251\text{ mm}$ ($9.9\text{ mil}$) | $0.189\text{ mm}$ ($7.4\text{ mil}$) | **$0.195\text{–}0.214\text{ mm}$** ($7.7\text{–}8.4\text{ mil}$) | **$0.20\text{ mm}$** ($7.9\text{ mil}$) |
| **$100\,\Omega$ Diff (LVDS)** | **$0.200\text{ mm}$ ($7.9\text{ mil}$)** | $0.279\text{ mm}$ ($11.0\text{ mil}$) | $0.214\text{ mm}$ ($8.4\text{ mil}$) | **$0.225\text{–}0.240\text{ mm}$** ($8.9\text{–}9.4\text{ mil}$) | **$0.23\text{ mm}$** ($9.1\text{ mil}$) |

---

### Runnable Python Check (All 6 Items)
Saved at [verify_math.py](file:///home/user1/collab/projects/usb3-sdr/notes/verify_math.py):
```python
python3 /home/user1/collab/projects/usb3-sdr/notes/verify_math.py
```
