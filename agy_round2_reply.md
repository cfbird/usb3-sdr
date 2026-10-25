Both [aaf_sim.py](file:///home/user1/collab/projects/usb3-sdr/notes/aaf_sim.py) and [aaf.md](file:///home/user1/collab/projects/usb3-sdr/notes/aaf.md) have been written and verified. Below are **(A)** the adversarial fact-check of [spec.md](file:///home/user1/collab/projects/usb3-sdr/notes/spec.md) and **(B)** the E12/E24 anti-alias + FM band-stop design and ABCD parasitic simulation.

---

## A. Adversarial Fact-Check of `notes/spec.md`

### 1. Section 3 Part Selection & Architecture Claims

| Claim in `spec.md` | Verdict | Source / Math / Adversarial Finding |
| :--- | :--- | :--- |
| **Sec 1 (L7–8)**: *"0.01–32 MHz in 1st Nyquist, plus 6 m and FM-band through undersampling if AAF is bypassed."* | **DISPUTED** | At $f_s = 80\text{ MSPS}$, 6m ($50\text{–}54\text{ MHz}$, Zone 2 $\to 26\text{–}30\text{ MHz}$) and FM ($88\text{–}108\text{ MHz}$, Zone 3 $\to 8\text{–}28\text{ MHz}$) only work if a **bandpass filter (BPF)** isolates that single Nyquist zone. An unfiltered AAF "bypass" folds Zones 1, 2, and 3 ($0\text{–}40$, $40\text{–}80$, $80\text{–}120\text{ MHz}$) on top of each other. |
| **AD9649BCPZ-80** (L29): 14-bit, 80 MSPS, SNR $74.1\text{ dBFS}$ / SFDR $93\text{ dBc}$ @ $30.5\text{ MHz}$, $1.8\text{–}3.3\text{ V}$ CMOS, $82\text{–}95\text{ mW}$, LFCSP-32 | **VERIFIED** | Matches ADI AD9649 datasheet (Rev. B, Table 1 & Table 2: SNR $= 74.1\text{ dBFS}$ typ @ $30.5\text{ MHz}$, SFDR $= 93\text{ dBc}$, total power $82\text{ mW}$ @ $20\text{ MSPS}$ to $95\text{ mW}$ @ $80\text{ MSPS}$, 32-lead $5\times 5\text{ mm}$ LFCSP). |
| **LFE5U-45F-6BG256C** (L30): 44k LUT, 72 $18\times 18$ mults, $1.9\text{ Mb}$ EBR, CABGA-256 @ $0.8\text{ mm}$, *"LCSC/JLC stock ~$17"* | **VERIFIED (specs)** / **DISPUTED (stock)** | Lattice ECP5 Family Data Sheet (FPGA-DS-02012): 44k LUT4, 72 $18\times 18$ mults, 108 EBR blocks $\times 18\text{ kb} = 1.944\text{ Mb}$. However, LCSC (`C267360`) is frequently **0 in stock** for `-6BG256C` (while `-6BG381C` or `LFE5U-25F-6BG256C` has better stock); verify LCSC inventory before locking footprint. |
| **FT601Q + 30 MHz crystal** (L31, L34): 32-bit FIFO @ 100 MHz, QFN-76, 30 MHz crystal | **VERIFIED** | FT600Q/FT601Q Datasheet (Sec. 5.2): requires a **30.000 MHz** parallel-resonant crystal ($\pm 20\text{ ppm}$, $C_L = 18\text{ pF}$, $\text{ESR} \le 50\,\Omega$) directly across `XI`/`XO` (external oscillator drive on `XI` is explicitly unsupported by FTDI). |
| **TI LMK61E2** (L20–21, L32): 1 diff output (LVPECL/LVDS/HCSL), $90\text{ fs}$ RMS typ, *"80 MHz, opt. 10 MHz ext ref via ECP5 PLL discipline"* | **VERIFIED (jitter/I²C)** / **UNVERIFIABLE (stock)** | TI LMK61E2 datasheet: supports $80\text{ MHz}$ LVDS/LVPECL ($90\text{ fs}$ typ $12\text{ kHz–}20\text{ MHz}$) and supports **glitchless fine frequency margining over $\text{I}^2\text{C}$** (acting as a DCXO that the ECP5 can steer against a 10 MHz reference counter). Stock/price at TI/DigiKey is sporadic; have a footprint fallback for a fixed $80\text{ MHz}$ $5\times 7\text{ mm}$ XO (e.g. Crystek CCHD-950X / Abracon). |
| **Balun: Mini-Circuits `ADT4-1WT+` / `TC4-1W+`** (L35) for $0.01\text{–}32\text{ MHz}$, $\text{FS} = +4\text{ dBm}$, $\text{NF} \approx 27.9\text{ dB}$ | **VERIFIED (NF math)** / **DISPUTED (parts!)** | **Math**: $\text{NSD} = +3.98 - 74.1 - 10\log_{10}(40\text{e6}) = -146.14\text{ dBm/Hz} \implies \text{NF}_{\text{ADC}} = \mathbf{27.84\text{ dB}}$ ($33.86\text{ dB}$ for 1:1).<br>**Part Catch**: **`ADT4-1WT+` is rated $2\text{–}775\text{ MHz}$** and **`TC4-1W+` is rated $3\text{–}800\text{ MHz}$**! Both fail below $2\text{–}3\text{ MHz}$ (losing LF/MF/160m). Replace with **`ADT4-6T+` ($0.06\text{–}160\text{ MHz}$)** or **`T4-6T+` ($0.02\text{–}200\text{ MHz}$)**. |
| **LNA: `PGA-103+`** (L36): $15\text{–}20\text{ dB}$ gain, *"Rural 30 MHz needs $\ge 3\text{ dB}$, quiet $\ge 18\text{ dB}$, 6 m $\ge 26\text{ dB}$"* | **DISPUTED (part & 6m gain)** | 1. **`PGA-103+` is specified for $50\text{–}4000\text{ MHz}$** (Mini-Circuits datasheet). Below $50\text{ MHz}$ its return loss, bias tee reactance, and stability degrade unless heavily modified; use an HF-capable MMIC (`GVA-84+` DC–7 GHz, `PSA4-5043+` w/ low-freq bias choke, or Norton/feedback BJT).<br>2. **Math**: At 30 MHz with $\text{NF}_{\text{ADC}} = 27.84\text{ dB}$, Crit. A ($\text{NF}_{\text{sys}} \le F_a$) needs **$2.3\text{ dB}$** (ITU Rural $26.3\text{ dB}$), **$10.1\text{ dB}$** (Galactic $18.0\text{ dB}$), **$17.4\text{ dB}$** (Quiet Rural $11.4\text{ dB}$). At 6m ($50\text{ MHz}$), external noise is limited by **Galactic sky noise ($F_a = 12.9\text{ dB}$)**, needing **$15.6\text{ dB}$** (Crit A) or **$19.3\text{ dB}$** (Crit B)—not $26\text{ dB}$ (and $26\text{ dB}$ gain clips the $+4\text{ dBm}$ ADC at $-22\text{ dBm}$!). |
| **RF Switch: pSemi `PE4259`** (L37) for $0.01\text{–}32\text{ MHz}$ | **DISPUTED** | pSemi `PE4259` datasheet specifies **$f_{\min} = 10\text{ MHz}$**! Below $10\text{ MHz}$, FET gate time constants cause severe IMD3/harmonics (degrading the AD9649's $93\text{ dBc}$ SFDR on 160m/80m/40m). Use **`PE4283` ($5\text{ kHz–}4000\text{ MHz}$)**, **`ADG918` (DC–4 GHz)**, or a signal relay (`G6K-2F-RF`). |
| **Power: `TPS62A01` / `TPS62A02` + `2x TPS7A2018`** (L38 vs. L48) | **DISPUTED (2 bugs)** | 1. **Voltage contradiction**: L38 specifies `2× TPS7A2018` (**fixed 1.8 V** LDO) for `AVDD` and `DRVDD`, but Sec 4 (L48) says *"Use DRVDD = 2.5 V to match a 2.5 V ECP5 bank"*. Fix: **ECP5 `sysIO` banks natively support `LVCMOS18` (`VCCIO = 1.8 V`)**. Keep `DRVDD = 1.8 V` (`TPS7A2018`) and power the dedicated ADC bank on the ECP5 at $1.8\text{ V}$ (cuts digital switching ground bounce by $48\%$ vs $2.5\text{ V}$!).<br>2. **Buck switching noise in HF**: `TPS62A01`/`02` switch at **$2.4\text{ MHz}$ (inside the 160m/80m HF band!)** and enter variable-frequency PFM at light load. Specify **`TPS62A01A`/`TPS62A02A` (Forced-PWM)** + 2-stage LC $\pi$-filtering. |

---

### 2. Section 4 & Section 6 (Gateware & PCB Layout) Fact-Check

| Claim in `spec.md` | Verdict | Source / Adversarial Finding |
| :--- | :--- | :--- |
| **Sec 4 (L48–49)**: *"Capture with an IDDR/SDR register clocked by DCO, then cross into the 80 MHz system clock (same source)."* | **DISPUTED** | AD9649 outputs **single-data-rate (SDR)** 14-bit parallel CMOS (not DDR), so use a standard SDR input flip-flop (`IFS1P3DX`), not `IDDR`. Furthermore, per L91, the LMK61E2 has only **one** output going to the ADC, so there is no separate "80 MHz system clock" on the FPGA—route `DCO` to an ECP5 **`PCLK` (Primary Clock)** pin and run the entire 80 MHz DDC domain directly on `DCO`! |
| **Sec 6 (L93)**: *"BGA-256 at 0.8 mm on 4 layers: dog-bone fanout with 0.2 mm drill and 0.4 mm pad vias."* | **DISPUTED** | On JLCPCB 4-layer boards, a $0.20\text{ mm}$ drill incurs an extra **small-hole surcharge** ($<0.30\text{ mm}$) and a $0.40\text{ mm}$ pad leaves a minimum borderline $0.10\text{ mm}$ annular ring (`0.45 mm` pad is JLCPCB's recommended minimum for $0.2\text{ mm}$ drill). More importantly, a **$0.8\text{ mm}$ pitch BGA (`CABGA-256`) has $1.13\text{ mm}$ diagonal ball pitch** and easily accepts JLCPCB's free standard **$0.25\text{ mm}$ drill / $0.45\text{ mm}$ pad** (or $0.30\text{ mm} / 0.50\text{ mm}$) dog-bone vias! |
| **Sec 6 (L39, L97–98)**: *"USB-C (GCT USB4105 or JLC 24-pin)... SS TX/RX pairs 90 Ω diff, AC caps (100 nF 0201/0402) on TX"* | **DISPUTED (missing Mux & CC)** | 1. **Missing SuperSpeed 2:1 Mux**: FT601Q has only **one** SS lane (`TXP/N`, `RXP/N`), whereas a 24-pin USB-C receptacle has two orientations (`A` and `B`). Without a **USB3 2:1 mux** (`HD3SS3212` / `VL160`) + **$2\times 5.1\text{ k}\Omega$ `Rd` resistors on `CC1`/`CC2`** (to detect cable orientation and enable 5V VBUS on USB-C hosts!), the USB-C cable will only work in one flip orientation (or won't get VBUS from a native USB-C port). Either add `HD3SS3212` + `CC1/CC2` logic or use a **USB 3.0 Type-B / Micro-B** connector.<br>2. **Avoid 0201**: Use **0402** $100\text{ nF}$ AC caps; 0201 triggers JLCPCB precision SMT fees. |
| **Sec 6 (L99)**: *"USB2 D+/D− also 90 Ω differential."* | **VERIFIED** | Matches USB 2.0 Specification (Sec. 7.1.1.3): $90\,\Omega \pm 15\%$ differential impedance. |

---

## B. Anti-Alias Chain Design & Parasitic ABCD Simulation (`fs = 80 MSPS`)

Full synthesis code and ABCD solver are in [aaf_sim.py](file:///home/user1/collab/projects/usb3-sdr/notes/aaf_sim.py) and detailed documentation in [aaf.md](file:///home/user1/collab/projects/usb3-sdr/notes/aaf.md).

### 1. 7th-Order Elliptic (Cauer) LPF Section (`LPF #1` & `LPF #2`, $R_0 = 50\,\Omega$)
- **Topology**: Minimum-inductance $\pi$-ladder: **4 shunt capacitors** ($C_1, C_3, C_5, C_7$) separated by **3 series parallel-resonant tanks** ($L_2\parallel C_2$, $L_4\parallel C_4$, $L_6\parallel C_6$).
- **Corner Pre-Distortion**: Placing the lossless prototype edge at **$f_c = 35.5\text{ MHz}$ (Design A)** instead of $32.6\text{ MHz}$ (Design B) shifts the high-$Q$ pole cluster just above $32\text{ MHz}$, cutting finite-$Q$ resistive droop at $32\text{ MHz}$ from $2.40\text{ dB}$ down to **$1.47\text{ dB}$ per LPF** ($0.03\text{ dB}$ lossless) while still delivering **$62.2\text{ dB}$ rejection per stage at $48\text{ MHz}$**.

| Component | Role / Tank Zero | Exact Value ($f_c=35.5\text{ MHz}$) | **Snapped E12 ($L$) / E24 ($C$)** | Design B ($f_c=32.6\text{ MHz}$) Snapped | 0805 / 0603 Part & Datasheet Parasitics |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **$C_1$** | Shunt C (In) | $59.50\text{ pF}$ | **$62\text{ pF}$** (E24) | $75\text{ pF}$ | 0603 C0G/NP0 50V $\pm 2\%$ ($\text{ESL}=0.5\text{ nH}, Q_C\ge 1000$) |
| **$L_2$** | Series Tank 1 | $183.7\text{ nH}$ | **$180\text{ nH}$** (E12) | $270\text{ nH}$ | Coilcraft `0805HP-181` / Murata `LQW18ANR18G00` ($\text{SRF}=850\text{ MHz}$) |
| **$C_2$** | Series Tank 1 ($f_{z1}=47.6\text{ MHz}$) | $59.31\text{ pF}$ | **$62\text{ pF}$** (E24) | $33\text{ pF}$ | 0603 C0G/NP0 50V $\pm 2\%$ |
| **$C_3$** | Shunt C | $132.87\text{ pF}$ | **$130\text{ pF}$** (E24) | $130\text{ pF}$ | 0603 C0G/NP0 50V $\pm 2\%$ |
| **$L_4$** | Series Tank 2 | $273.9\text{ nH}$ | **$270\text{ nH}$** (E12) | $270\text{ nH}$ | Coilcraft `0805HP-271` / Murata `LQW18ANR27G00` ($\text{SRF}=650\text{ MHz}$) |
| **$C_4$** | Series Tank 2 ($f_{z2}=55.9\text{ MHz}$) | $28.97\text{ pF}$ | **$30\text{ pF}$** (E24) | $47\text{ pF}$ | 0603 C0G/NP0 50V $\pm 2\%$ |
| **$C_5$** | Shunt C | $155.50\text{ pF}$ | **$160\text{ pF}$** (E24) | $150\text{ pF}$ | 0603 C0G/NP0 50V $\pm 2\%$ |
| **$L_6$** | Series Tank 3 | $293.0\text{ nH}$ | **$270\text{ nH}$** (E12) | $330\text{ nH}$ | Coilcraft `0805HP-271` ($\text{SRF}=650\text{ MHz}$) |
| **$C_6$** | Series Tank 3 ($f_{z3}=92.3\text{ MHz}$) | $9.87\text{ pF}$ | **$11\text{ pF}$** (E24) | $10\text{ pF}$ | 0603 C0G/NP0 50V $\pm 2\%$ |
| **$C_7$** | Shunt C (Out) | $93.23\text{ pF}$ | **$91\text{ pF}$** (E24) | $100\text{ pF}$ | 0603 C0G/NP0 50V $\pm 2\%$ |

---

### 2. Self-Matched 3-Branch $\pi$ FM Band-Stop Filter ($88\text{–}108\text{ MHz}$)
Below $32\text{ MHz}$, the two shunt series-LC traps ($L_{n1}+C_{n1}$, $L_{n3}+C_{n3}$) act as effective shunt capacitors ($\sim 44\text{ pF}, 51\text{ pF}$) and the middle series parallel-LC tank ($L_{n2}\parallel C_{n2}$) acts as an effective series inductor ($\sim 202\text{ nH}$), forming a **self-matched $50\,\Omega$ low-pass $\pi$-section below $32\text{ MHz}$** (return loss **$>31\text{ dB}$**, lossless ripple **$0.00\text{ dB}$**, loss **$\le 0.20\text{ dB}$** at $Q=50$) while providing **$\ge 54.8\text{ dB}$ standalone rejection across the entire $88\text{–}108\text{ MHz}$ band**:

| Branch | Topology | E12 Inductor $L$ (0805HP/LQW18) | E24 Capacitor $C$ (0603 C0G) | Trap Zero (w/ $\text{ESL}=0.5\text{ nH}$ & SRF) | Standalone $88\text{–}108\text{ MHz}$ Rejection ($Q=50$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Branch 1** | Shunt series $L_{n1}+C_{n1}$ to GND | **$82\text{ nH}$** ($\text{SRF}=1.3\text{ GHz}$) | **$39\text{ pF}$** | **$88.7\text{ MHz}$** | **$61.05\text{ dB}$** @ $88\text{ MHz}$ |
| **Branch 2** | Series parallel $L_{n2}\parallel C_{n2}$ | **$180\text{ nH}$** ($\text{SRF}=850\text{ MHz}$) | **$15\text{ pF}$** | **$96.1\text{ MHz}$** | **$62.20\text{ dB}$** @ $98\text{ MHz}$ |
| **Branch 3** | Shunt series $L_{n3}+C_{n3}$ to GND | **$47\text{ nH}$** ($\text{SRF}=1.7\text{ GHz}$) | **$47\text{ pF}$** | **$106.5\text{ MHz}$** | **$54.80\text{ dB}$** @ $108\text{ MHz}$ (**$\ge 54.8\text{ dB}$ min**) |

---

### 3. ABCD Cascade Simulation Results (`LPF #1 + FM Notch + LPF #2`)

Inductor skin-effect loss is modeled as $R_s(f) = \frac{2\pi (100\text{ MHz}) L}{Q_{100}} \sqrt{\frac{f}{100\text{ MHz}}}$ in parallel with datasheet $C_p = \frac{1}{(2\pi f_{\text{SRF}})^2 L}$, and capacitor impedance includes series $\text{ESL} = 0.5\text{ nH}$ and $Q_C = 1000$:

| Model / Stage | $32\text{ MHz}$ ($S_{21}$) | $48\text{ MHz}$ ($S_{21}$) | $88\text{ MHz}$ ($S_{21}$) | $98\text{ MHz}$ ($S_{21}$) | $108\text{ MHz}$ ($S_{21}$) | $150\text{ MHz}$ ($S_{21}$) | Passband ($0.1\text{–}32\text{ MHz}$) Ripple / Droop | Passband Min Return Loss |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Single LPF (Snapped Lossless)** | $-0.03\text{ dB}$ | $-69.12\text{ dB}$ | $-74.43\text{ dB}$ | $-73.37\text{ dB}$ | $-65.88\text{ dB}$ | $-60.06\text{ dB}$ | **$0.12\text{ dB}$** | **$15.55\text{ dB}$** |
| **Single LPF ($Q_{100}=50$, $\text{ESL}=0.5\text{ nH}$, SRF)** | $-1.47\text{ dB}$ | $-62.20\text{ dB}$ | $-76.50\text{ dB}$ | $-72.11\text{ dB}$ | $-65.69\text{ dB}$ | $-60.83\text{ dB}$ | **$1.44\text{ dB}$** (resistive droop) | **$15.91\text{ dB}$** |
| **FM Notch Only ($Q_{100}=50$, $\text{ESL}=0.5\text{ nH}$, SRF)** | $-0.20\text{ dB}$ | $-1.11\text{ dB}$ | $-61.05\text{ dB}$ | $-62.20\text{ dB}$ | $-54.80\text{ dB}$ | $-9.19\text{ dB}$ | **$0.20\text{ dB}$** | **$31.42\text{ dB}$** |
| **Full Cascade (Snapped Lossless)** | **$-0.10\text{ dB}$** | **$-137.96\text{ dB}$** | **$-208.87\text{ dB}$** | **$-203.05\text{ dB}$** | **$-169.17\text{ dB}$** | **$-127.86\text{ dB}$** | **$0.31\text{ dB}$** ($\le 0.5\text{ dB}$ PASS) | **$11.61\text{ dB}$** |
| **Full Cascade ($Q_{100}=60$, $\text{ESL}=0.5\text{ nH}$, SRF)** | **$-2.68\text{ dB}$** | **$-126.44\text{ dB}$** | **$-213.72\text{ dB}$** | **$-194.03\text{ dB}$** | **$-164.06\text{ dB}$** | **$-129.73\text{ dB}$** | $2.63\text{ dB}$ ($0.85\text{ dB}$ @ $\le 25\text{ MHz}$) | **$12.69\text{ dB}$** |
| **Full Cascade ($Q_{100}=50$, $\text{ESL}=0.5\text{ nH}$, SRF)** | **$-3.17\text{ dB}$** | **$-124.64\text{ dB}$** | **$-212.39\text{ dB}$** | **$-193.65\text{ dB}$** | **$-163.77\text{ dB}$** | **$-129.74\text{ dB}$** | $3.12\text{ dB}$ ($1.02\text{ dB}$ @ $\le 25\text{ MHz}$) | **$12.86\text{ dB}$** |
| **Full Cascade ($Q_{100}=40$, $\text{ESL}=0.5\text{ nH}$, SRF)** | **$-3.92\text{ dB}$** | **$-122.18\text{ dB}$** | **$-210.51\text{ dB}$** | **$-193.02\text{ dB}$** | **$-163.30\text{ dB}$** | **$-129.74\text{ dB}$** | $3.85\text{ dB}$ ($1.27\text{ dB}$ @ $\le 25\text{ MHz}$) | **$13.10\text{ dB}$** |

### Runnable Python Verification
```bash
python3 /home/user1/collab/projects/usb3-sdr/notes/aaf_sim.py
```
