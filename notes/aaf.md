# Anti-Alias Filter (AAF) + FM Band-Stop Design & Parasitic Simulation

**Author**: AGY (Gemini 4 Argon)  
**Project**: `usb3-sdr` ($f_s = 80\text{ MSPS}$, $R_0 = 50\,\Omega$, Passband $0.1\text{–}32\text{ MHz}$, First Alias Stopband $\ge 48\text{ MHz}$)  
**Simulation Script**: [`notes/aaf_sim.py`](file:///home/user1/collab/projects/usb3-sdr/notes/aaf_sim.py) (2×2 ABCD matrix cascade with frequency-dependent skin-effect $Q(f)$, inductor SRF parallel capacitance $C_p$, and capacitor $\text{ESL} = 0.5\text{ nH}$).

---

## 1. Architecture & Why Corner Pre-Distortion Matters

```
50 Ω In ─► [LPF #1: 7th-Order Cauer] ─► [FM Band-Stop: 88–108 MHz Pi-Notch] ─► (LNA / Bypass) ─► [LPF #2: 7th-Order Cauer] ─► 50 Ω Out
```

- **Key Finite-$Q$ Design Insight**: In a 7th-order elliptic LPF, the highest pole pair has a high loaded $Q_p \approx 10\text{–}12$ right near the cutoff edge. If the lossless prototype cutoff is placed right at $f_c = 32.6\text{ MHz}$ (**Design B**), realistic 0805 inductors ($Q \approx 50$ @ 100 MHz $\implies Q \approx 28.3$ @ 32 MHz due to $\sqrt{f}$ skin effect) produce **$-2.40\text{ dB}$** of resistive corner rounding at $32\text{ MHz}$ per stage ($-5.02\text{ dB}$ for two stages).
- By **pre-distorting the prototype passband edge to $f_c = 35.5\text{ MHz}$ (Design A, Recommended)** while keeping the transmission zeros anchored at $46.8, 55.6, 85.4\text{ MHz}$, the resistive loss at $32\text{ MHz}$ drops to **$-1.47\text{ dB}$ per LPF** ($-0.03\text{ dB}$ lossless!) while still achieving **$62.2\text{ dB}$ per section ($124.6\text{ dB}$ cascaded)** at $48.0\text{ MHz}$!

---

## 2. 7th-Order Elliptic (Cauer) Low-Pass Filter Section (`LPF #1` & `LPF #2`)

### 2.1 Topology (Minimum-Inductance $\pi$-Ladder: 3 Inductors, 7 Capacitors)
- **Shunt Branches to GND**: $C_1$ (input), $C_3$, $C_5$, $C_7$ (output).
- **Series Parallel-Resonant Tanks**: Tank 1 ($L_2 \parallel C_2$), Tank 2 ($L_4 \parallel C_4$), Tank 3 ($L_6 \parallel C_6$).

### 2.2 Exact vs. E12 ($L$) / E24 ($C$) Snapped Component Table

| Element | Role / Resonant Zero | Design A ($f_c = 35.5\text{ MHz}$, Recommended) Exact $\to$ **Snapped** | Design B ($f_c = 32.6\text{ MHz}$, Nominal) Exact $\to$ **Snapped** | Recommended 0805/0603 Part ($Q_{100\text{MHz}}, \text{SRF}$) |
| :--- | :--- | :--- | :--- | :--- |
| **$C_1$** | Shunt C (Input) | $59.50\text{ pF} \to \mathbf{62\text{ pF}}$ (E24) | $75.76\text{ pF} \to \mathbf{75\text{ pF}}$ (E24) | 0603 C0G/NP0 50V $\pm 2\%$ ($\text{ESL}\approx 0.5\text{ nH}$) |
| **$L_2$** | Series Tank 1 Ind | $183.7\text{ nH} \to \mathbf{180\text{ nH}}$ (E12) | $251.7\text{ nH} \to \mathbf{270\text{ nH}}$ (E12) | Coilcraft `0805HP-181XJLB` / Murata `LQW18ANR18G00` ($Q\approx 55, \text{SRF}=850\text{ MHz}$) |
| **$C_2$** | Series Tank 1 Cap | $59.31\text{ pF} \to \mathbf{62\text{ pF}}$ ($f_{z1}=47.6\text{ MHz}$) | $36.20\text{ pF} \to \mathbf{33\text{ pF}}$ ($f_{z1}=53.3\text{ MHz}$) | 0603 C0G/NP0 50V $\pm 2\%$ |
| **$C_3$** | Shunt C (Internal) | $132.87\text{ pF} \to \mathbf{130\text{ pF}}$ (E24) | $139.70\text{ pF} \to \mathbf{130\text{ pF}}$ (E24) | 0603 C0G/NP0 50V $\pm 2\%$ |
| **$L_4$** | Series Tank 2 Ind | $273.9\text{ nH} \to \mathbf{270\text{ nH}}$ (E12) | $255.6\text{ nH} \to \mathbf{270\text{ nH}}$ (E12) | Coilcraft `0805HP-271XJLB` / Murata `LQW18ANR27G00` ($Q\approx 55, \text{SRF}=650\text{ MHz}$) |
| **$C_4$** | Series Tank 2 Cap | $28.97\text{ pF} \to \mathbf{30\text{ pF}}$ ($f_{z2}=55.9\text{ MHz}$) | $49.18\text{ pF} \to \mathbf{47\text{ pF}}$ ($f_{z2}=44.7\text{ MHz}$) | 0603 C0G/NP0 50V $\pm 2\%$ |
| **$C_5$** | Shunt C (Internal) | $155.50\text{ pF} \to \mathbf{160\text{ pF}}$ (E24) | $153.51\text{ pF} \to \mathbf{150\text{ pF}}$ (E24) | 0603 C0G/NP0 50V $\pm 2\%$ |
| **$L_6$** | Series Tank 3 Ind | $293.0\text{ nH} \to \mathbf{270\text{ nH}}$ (E12) | $321.2\text{ nH} \to \mathbf{330\text{ nH}}$ (E12) | Coilcraft `0805HP-271XJLB` ($Q\approx 55, \text{SRF}=650\text{ MHz}$) |
| **$C_6$** | Series Tank 3 Cap | $9.87\text{ pF} \to \mathbf{11\text{ pF}}$ ($f_{z3}=92.3\text{ MHz}$) | $10.27\text{ pF} \to \mathbf{10\text{ pF}}$ ($f_{z3}=87.6\text{ MHz}$) | 0603 C0G/NP0 50V $\pm 1\text{–}2\%$ |
| **$C_7$** | Shunt C (Output) | $93.23\text{ pF} \to \mathbf{91\text{ pF}}$ (E24) | $96.08\text{ pF} \to \mathbf{100\text{ pF}}$ (E24) | 0603 C0G/NP0 50V $\pm 2\%$ |

---

## 3. FM Broadcast Band-Stop Filter ($88\text{–}108\text{ MHz}$)

### 3.1 Self-Matched 3-Branch $\pi$ Band-Stop Topology
Why does this 3-branch band-stop filter have **$<0.01\text{ dB}$ ideal ripple ($0.20\text{ dB}$ loss with $Q=50$) and $>31\text{ dB}$ return loss below $32\text{ MHz}$**?
- **Branch 1 (Shunt series-LC trap to GND @ $88.9\text{ MHz}$)**: Below $32\text{ MHz}$, $L_{n1} + C_{n1}$ is capacitive with effective capacitance $C_{1,\text{eff}} = C_{n1} / (1 - (f/f_{n1})^2) \approx 44\text{ pF}$.
- **Branch 2 (Series parallel-LC tank @ $96.9\text{ MHz}$)**: Below $32\text{ MHz}$, $L_{n2} \parallel C_{n2}$ is inductive with effective inductance $L_{2,\text{eff}} = L_{n2} / (1 - (f/f_{n2})^2) \approx 202\text{ nH}$.
- **Branch 3 (Shunt series-LC trap to GND @ $107.1\text{ MHz}$)**: Below $32\text{ MHz}$, $L_{n3} + C_{n3}$ is capacitive with $C_{3,\text{eff}} \approx 51\text{ pF}$.
- Together, $\sqrt{L_{2,\text{eff}} / (C_{1,\text{eff}} + C_{3,\text{eff}})} \approx \mathbf{46.1\,\Omega} \approx 50\,\Omega$, so the three FM traps form a **matched $50\,\Omega$ low-pass $\pi$-network across the entire $0.1\text{–}32\text{ MHz}$ HF band** while placing three staggered transmission zeros across $88\text{–}108\text{ MHz}$!

| Branch | Topology | E12 Inductor $L$ | E24 Capacitor $C$ | Unloaded Trap Zero $f_0$ | Zero w/ $\text{ESL}=0.5\text{ nH}$ & SRF | Standalone $88\text{–}108\text{ MHz}$ Rejection ($Q=50$) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Trap 1** | Shunt series $L_{n1} + C_{n1}$ | **$82\text{ nH}$** (`0805HP-820`, $\text{SRF}=1.3\text{ GHz}$) | **$39\text{ pF}$** | $89.0\text{ MHz}$ | $88.7\text{ MHz}$ | **$\ge 54.8\text{ dB}$ across entire $88\text{–}108\text{ MHz}$** |
| **Tank 2** | Series parallel $L_{n2} \parallel C_{n2}$ | **$180\text{ nH}$** (`0805HP-181`, $\text{SRF}=850\text{ MHz}$) | **$15\text{ pF}$** | $96.9\text{ MHz}$ | $96.1\text{ MHz}$ | ($61.1\text{ dB}$ @ $88\text{ MHz}$, $62.2\text{ dB}$ @ $98\text{ MHz}$, |
| **Trap 3** | Shunt series $L_{n3} + C_{n3}$ | **$47\text{ nH}$** (`0805HP-470`, $\text{SRF}=1.7\text{ GHz}$) | **$47\text{ pF}$** | $107.1\text{ MHz}$ | $106.5\text{ MHz}$ | $54.8\text{ dB}$ @ $108\text{ MHz}$) |

---

## 4. ABCD Simulation Results (`LPF #1 + FM Notch + LPF #2`, Design A)

### 4.1 Spot-Frequency Attenuation Table ($S_{21}$ in dB)

| Condition / Model | $32\text{ MHz}$ (Passband Edge) | $48\text{ MHz}$ (1st Alias Edge) | $88\text{ MHz}$ (FM Low) | $98\text{ MHz}$ (FM Mid) | $108\text{ MHz}$ (FM High) | $150\text{ MHz}$ (2m VHF) | Passband ($0.1\text{–}32\text{ MHz}$) Ripple / Droop | Passband Min Return Loss ($-S_{11}$) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Single LPF #1 (Ideal Snapped)** | $-0.03\text{ dB}$ | $-69.12\text{ dB}$ | $-74.43\text{ dB}$ | $-73.37\text{ dB}$ | $-65.88\text{ dB}$ | $-60.06\text{ dB}$ | **$0.12\text{ dB}$** | **$15.55\text{ dB}$** |
| **Single LPF #1 ($Q=50$, $\text{ESL}=0.5\text{ nH}$, SRF)** | $-1.47\text{ dB}$ | $-62.20\text{ dB}$ | $-76.50\text{ dB}$ | $-72.11\text{ dB}$ | $-65.69\text{ dB}$ | $-60.83\text{ dB}$ | **$1.44\text{ dB}$** (resistive droop) | **$15.91\text{ dB}$** |
| **Standalone FM Notch ($Q=50$, $\text{ESL}=0.5\text{ nH}$)** | $-0.20\text{ dB}$ | $-1.11\text{ dB}$ | $-61.05\text{ dB}$ | $-62.20\text{ dB}$ | $-54.80\text{ dB}$ | $-9.19\text{ dB}$ | **$0.20\text{ dB}$** | **$31.42\text{ dB}$** |
| **Full Cascade (Ideal Snapped)** | **$-0.10\text{ dB}$** | **$-137.96\text{ dB}$** | **$-208.87\text{ dB}$** | **$-203.05\text{ dB}$** | **$-169.17\text{ dB}$** | **$-127.86\text{ dB}$** | **$0.31\text{ dB}$** ($\le 0.5\text{ dB}$ PASS) | **$11.61\text{ dB}$** |
| **Full Cascade ($Q=60$ @ 100M, $\text{ESL}=0.5\text{ nH}$)** | **$-2.68\text{ dB}$** | **$-126.44\text{ dB}$** | **$-213.72\text{ dB}$** | **$-194.03\text{ dB}$** | **$-164.06\text{ dB}$** | **$-129.73\text{ dB}$** | $2.63\text{ dB}$ ($0.85\text{ dB}$ @ $\le 25\text{ MHz}$) | **$12.69\text{ dB}$** |
| **Full Cascade ($Q=50$ @ 100M, $\text{ESL}=0.5\text{ nH}$)** | **$-3.17\text{ dB}$** | **$-124.64\text{ dB}$** | **$-212.39\text{ dB}$** | **$-193.65\text{ dB}$** | **$-163.77\text{ dB}$** | **$-129.74\text{ dB}$** | $3.12\text{ dB}$ ($1.02\text{ dB}$ @ $\le 25\text{ MHz}$) | **$12.86\text{ dB}$** |
| **Full Cascade ($Q=40$ @ 100M, $\text{ESL}=0.5\text{ nH}$)** | **$-3.92\text{ dB}$** | **$-122.18\text{ dB}$** | **$-210.51\text{ dB}$** | **$-193.02\text{ dB}$** | **$-163.30\text{ dB}$** | **$-129.74\text{ dB}$** | $3.85\text{ dB}$ ($1.27\text{ dB}$ @ $\le 25\text{ MHz}$) | **$13.10\text{ dB}$** |

*(Note: Theoretical ABCD stopband values above $120\text{ dB}$ represent ideal mathematical cascade isolation; in physical hardware with LPF #1 + Notch in shield compartment #1 ahead of the LNA and LPF #2 in shield compartment #2 after the LNA, actual board-level isolation is governed by the compartment-to-compartment shielding floor of $\sim 110\text{–}130\text{ dB}$.)*
