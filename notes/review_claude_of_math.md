# Claude review of AGY math.md (2026-10-22)
| Item | Verdict | Notes |
|---|---|---|
| 1 USB throughput | VERIFIED | Arithmetic is correct. The FX3/FT601 sustained figures were inputs from Claude's prompt. FT601 has about 360 MB/s measured read (ft60x-rs). AD9649 raw mode is 160 MB/s. |
| 2 Jitter | VERIFIED | Same formula independently gives 532 fs at 30 MHz for AD9649 (74.1 dBFS), which scales consistently with AGY's 381 fs at 77 dBFS. The LMK61E2 is at about 0.1 ps. |
| 3 MDS/NF | VERIFIED (formulas); inputs superseded | The ITU-R P.372 coefficients (rural 67.2/27.7, quiet rural 53.6/28.6, galactic 52.0/23.0) are correct. Redone for AD9649-80: NF_ADC = 27.9 dB, so LNA gain needed at 30 MHz is ≥ 3 dB (rural), ≥ 11.5 dB (galactic) and ≥ 18.4 dB (quiet). AGY correctly flagged that FS = +4 dBm needs a 1:4 impedance transformer. Claude's draft had said "1:2", which was ambiguous, and has been corrected. |
| 4 DDC/CIC | VERIFIED | Ran verify_math.py and the bit growth matches N·log2(R). The warning against using the CIC alone to the final rate is correct. 80 MHz clock instead of 125 MHz still leaves about 41 cycles per output sample at R=64. |
| 5 AAF | VERIFIED (math); inputs superseded | Redone for fs = 80 MSPS: elliptic order 8 for 80 dB. Key new finding: FM aliases into 8–28 MHz. AGY's FM-notch plus two-section recommendation is adopted. |
| 6 Impedance | VERIFIED with a caveat | Claude's own Hammerstad-Jensen gives 0.373 mm for bare 50 Ω, matching AGY exactly (Claude's earlier IPC-2141 figure of 0.35 mm was the less accurate one). AGY's 2D solver reads about 2 Ω low compared with H-J at the same width. Final widths come from the JLC calculator; expect about 0.34–0.36 mm (50 Ω SE with mask) and about 0.26 mm with 0.15 mm gap (90 Ω differential). |

# Claude review of AGY round 2 (spec fact-check + AAF), 2026-10-22
| AGY claim | Claude verdict | Evidence |
|---|---|---|
| Undersampling 6 m/FM needs a bandpass filter, not an AAF bypass | VERIFIED (Claude's spec was wrong) | Basic Nyquist folding |
| LFE5U-45F-6BG256C often 0 stock at LCSC "C267360" | **DISPUTED** | Claude found that part at LCSC as **C1550834** ($17.21). AGY's part code does not match. Stock still needs checking at order time. |
| ADT4-1WT+ is 2–775 MHz, so it fails at LF/MF; use ADT4-6T+ | VERIFIED | Mini-Circuits: ADT4-6T+ is 0.06–300 MHz, 1:4. T4-6T+ range not confirmed. |
| PGA-103+ is 50–4000 MHz, so it is unsuitable for HF | VERIFIED | Mini-Circuits datasheet. GVA-84+ is DC–7 GHz with low-frequency cutoff set by the external choke/caps. |
| PE4259 minimum 10 MHz | VERIFIED | pSemi datasheet: 10–3000 MHz. PE4283 at "0 Hz–4 GHz" is from a distributor only and **unverified**. |
| TPS62A0x is 2.4 MHz with PFM at light load; use TPS62A0xA forced-PWM | VERIFIED (part) / DISPUTED (detail) | The A variants exist and run forced PWM at 2.4 MHz. But 2.4 MHz is **not** in 160 m (1.8–2.0) or 80 m (3.5–4.0). It sits in the **120 m SW broadcast band (2.3–2.495 MHz)**, and harmonics land at 4.8 / 7.2 MHz. The conclusion (fixed frequency, filter hard) stands. |
| JLC 0.2 mm drill carries a surcharge; use 0.25/0.45 | PARTLY DISPUTED | JLC capabilities: multilayer minimum hole 0.2 mm, via diameter 0.45 mm (0.4 limit). The surcharge applies at **0.15 mm**. So 0.2–0.25 mm drill with a **0.45 mm pad** is correct, and Claude's 0.4 mm pad was at the limit. |
| USB-C needs a SuperSpeed 2:1 mux plus 5.1 kΩ Rd on CC1/CC2 because the FT601 has one SS lane | VERIFIED | Standard USB Type-C requirement. Major catch. |
| AD9649 is SDR, so no IDDR; clock the DDC from DCO | VERIFIED | Datasheet: CMOS SDR output with DCO |
| AAF Design A values and response | VERIFIED | Claude's independent ABCD model gives 32 MHz −1.42 dB / 48 MHz −62.5 dB per section at Q50 (AGY: −1.47/−62.2). Ideal case: 48 MHz −67.9 (AGY −69.1). |
| AAF "passband ripple ≤ 0.5 dB PASS" | DISPUTED (scope) | Passes only for ideal parts. With real inductors the cascade droops 2.6–3.9 dB at 32 MHz (AGY's own table), or 2.5 dB per section in the pessimistic case where Q ∝ f. Spec it as **usable to about 30 MHz**, correct the droop in DSP, and re-simulate with Coilcraft S-parameter models. |
| FM notch values | Not independently simulated | — |

# Claude review of AGY round 3, 2026-10-22 (datasheets in scratch: Mini-Circuits GVA-84+, GVA-62+, PHA-13LN+, LHA-13LN+)
| AGY claim | Verdict | Datasheet |
|---|---|---|
| GVA-84+ Vd 4.8–5.2 V, Id 85–130 mA, so there is no bias headroom from USB 5 V. Reject. | VERIFIED | Vd 4.8/5.0/5.2, Id 85/108/130 mA |
| PHA-13LN+ "22.2 dB, NF 1.0–1.2, OIP3 +38.5 dBm at 3.0–3.3 V / 71 mA" | **DISPUTED: columns mixed** | **5 V**: G 24.0, NF 1.2, OIP3 **+40.2** @20 MHz, **Id 138.9 mA**. **3 V**: G 23.3, NF 1.1, OIP3 only **+33.3** @20 MHz, Id 71.2 mA. NF at 1 MHz is 3.1 dB. |
| GVA-62+ "10–6000 MHz, 15.2 dB, **NF 1.5 dB**, OIP3 +39" | **DISPUTED** | NF **4.7 dB** @50 MHz (6.2 max). G 16.5, OIP3 +37.8 @50 MHz. 0.01–6 GHz is correct. |
| Bias-tee choke math (≥ 796 µH for 100 kHz), SRF problem, stacked choke | VERIFIED (reasoning) | Moot once the LNA is bypassed below 10 MHz |
| Cascade NF / IIP3 / SFDR equations and the "OIP3_LNA ≥ IIP3_ADC + L_post" rule | VERIFIED | Claude's independent cascade reproduces the LNA-off row exactly (32.2 dB, +8.3 dBm, 102.85/100.52 dB) |
| Buck π filter (1 µH + 11 µF, 0.47 Ω series damping, ζ ≈ 0.94, ~62–73 dB at 2.4/4.8/7.2 MHz) | VERIFIED | f0 = 48 kHz and (2.4 MHz / 48 kHz)² ≈ 68 dB check out. Caveats: X7R DC-bias derating raises f0, and real coupling will be via ground/magnetic paths, not the rail. TPS7A20 PSRR figures not checked (margin > 50 dB either way). |

## Corrected LNA budget (Claude, real datasheet values @ 20 MHz, PHA-13LN+ at 5 V)
| Config | NF_sys | Net gain | MDS 2.4 kHz | Clip at input | IIP3 | SFDR3 2.4 kHz |
|---|---|---|---|---|---|---|
| LNA off | 32.2 dB | −4.3 | −108.0 dBm | +8.3 dBm | +46.3/+42.8 | 102.9/100.5 dB |
| PHA-13LN+ 5 V, no pad | 9.3 dB | 19.7 | −130.9 dBm | −15.7 dBm | +16.6/+15.4 | 98.3/97.5 dB |
| PHA-13LN+ 5 V, 6 dB pad | 14.5 dB | 13.7 | −125.7 dBm | −9.7 dBm | +17.6/+17.2 | 95.5/95.2 dB |
| PHA-13LN+ 3 V, 6 dB pad | 15.2 dB | 13.0 | −125.0 dBm | −9.0 dBm | +11.7/+11.6 | 91.2/91.1 dB |
| GVA-62+ @50 MHz | 16.2 dB | 12.2 | −124.0 dBm | −8.2 dBm | +22.3/+21.4 | 97.5/96.9 dB |

# Claude review of AGY round 4 (gateware review), 2026-10-22
| AGY claim | Verdict | Check |
|---|---|---|
| NCO mirror exact; truncation spur −84.3 dBc | VERIFIED | Agrees with design intent (half-sample offset) and the gen_coeffs comment |
| NCO latency comment inconsistent (nco.v vs ddc.v) | VERIFIED: fixed | acc → rs → rs2 → sin_o = 3 clocks, 4 from phase_inc. Claude's comment was wrong |
| Mixer worst case −8192 × −131071 → +131071, no overflow | VERIFIED | Recomputed: (1073733632 + 4096) >> 13 = 131071 |
| Pipelined comb = z^-96 (1 − z^-16)^5, exact CIC + delay | VERIFIED | Same reasoning Claude used when writing it |
| FIR buffer overwrite margins (oldest tap at w0+10 / w0+6) | VERIFIED | Recomputed (−(NTAPS−1) mod 2^AW) |
| −0.26 dB tone level = Blackman-Harris scalloping (−0.258 dB) + net chain −0.00004 dB, predicted −13.2156 vs sim −13.22 | VERIFIED | Matches the simulated value |
| FT601 replay: only 1-cycle TXE_N pulses reorder, always flagged; exhaustive 2^16 sequences | VERIFIED (consistent with Claude's CXXRTL run) | AGY's first pass showed 1906 "unflagged" cases. AGY traced them to end-of-sequence truncation (word not yet judged) and got 0 with a 2-cycle drain |
| Read path: rd_prev aligns with the IO-register delay; turnaround ≥ 1 dead cycle | VERIFIED | Matches the tb_ft results (all host words received) |
