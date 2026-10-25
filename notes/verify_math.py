#!/usr/bin/env python3
"""
Parametric Math Verification for USB3 Direct-Sampling SDR (usb3-sdr)
Reproduces all tables in notes/math.md:
  1. USB3 Throughput Budget (FX3 vs FT601, raw real & complex IQ)
  2. Clock Jitter Budget (30, 60, 150 MHz for <=1 dB degradation from 77 dBFS)
  3. Dynamic Range, NSD, Processing Gain, MDS, NF, and ITU-R P.372 LNA Cascade
  4. FPGA DDC (CIC bit growth, droop, alias rejection, ECP5 multiplier fit)
  5. Anti-Alias Filter Orders (Butterworth, Chebyshev, Elliptic for 55->70 MHz)
  6. PCB Microstrip & Differential Impedance (JLC04161H-7628 stackup)
"""

import numpy as np
from scipy import signal
from scipy.optimize import brentq


def section_1_usb3():
    print("=== 1. USB3 THROUGHPUT BUDGET ===")
    rates_msps = [65, 105, 125, 130, 160]
    fx3_min, fx3_max = 350.0, 380.0
    ft601_min, ft601_max = 300.0, 340.0
    for fs in rates_msps:
        mb_16 = fs * 2.0
        mb_14 = fs * 1.75
        mb_12 = fs * 1.50
        fx3_ok = "PASS" if mb_16 <= fx3_min else ("MARGINAL" if mb_16 <= fx3_max else "FAIL")
        ft_ok = "PASS" if mb_16 <= ft601_min else ("MARGINAL" if mb_16 <= ft601_max else "FAIL")
        print(f"  Fs={fs:3d} MSPS: 16b={mb_16:6.2f} MB/s ({mb_16/1.048576:6.2f} MiB/s) | "
              f"14b={mb_14:6.2f} MB/s | 12b={mb_12:6.2f} MB/s | FX3:{fx3_ok} | FT601:{ft_ok}")
    print(f"  Complex 16I+16Q (4 B/sample) max IQ rate: "
          f"FX3 = {fx3_min/4:.1f}-{fx3_max/4:.1f} MSPS (80% BW = {0.8*fx3_min/4:.1f}-{0.8*fx3_max/4:.1f} MHz), "
          f"FT601 = {ft601_min/4:.1f}-{ft601_max/4:.1f} MSPS (80% BW = {0.8*ft601_min/4:.1f}-{0.8*ft601_max/4:.1f} MHz)\n")


def section_2_jitter(snr0_dbfs=77.0, max_deg_db=1.0):
    print("=== 2. CLOCK JITTER BUDGET ===")
    snr_j_min = snr0_dbfs - 10.0 * np.log10(10.0**(max_deg_db / 10.0) - 1.0)
    print(f"  Base SNR0 = {snr0_dbfs:.1f} dBFS, max degradation = {max_deg_db:.1f} dB -> min SNR_jitter = {snr_j_min:.2f} dBFS")
    for fin_mhz in [30.0, 60.0, 150.0]:
        fin = fin_mhz * 1e6
        tj_tot = (10.0**(-snr0_dbfs / 20.0) * np.sqrt(10.0**(max_deg_db / 10.0) - 1.0)) / (2.0 * np.pi * fin)
        tj_clk_70 = np.sqrt(max(0.0, tj_tot**2 - (70e-15)**2))
        tj_clk_100 = np.sqrt(max(0.0, tj_tot**2 - (100e-15)**2))
        print(f"  f_in = {fin_mhz:5.1f} MHz: t_j,total <= {tj_tot*1e15:6.1f} fs | "
              f"t_j,clk(ADC=70fs) <= {tj_clk_70*1e15:6.1f} fs | t_j,clk(ADC=100fs) <= {tj_clk_100*1e15:6.1f} fs")
    print()


def section_3_dynamic_range(snr0_dbfs=77.0, fs=125e6, p_fs_dbm=4.0):
    print("=== 3. DYNAMIC RANGE, MDS, NF & LNA CASCADE ===")
    b_nyq = fs / 2.0
    nsd_dbfs = -snr0_dbfs - 10.0 * np.log10(b_nyq)
    nsd_dbm = p_fs_dbm + nsd_dbfs
    kt0_dbm = 10.0 * np.log10(1.380649e-23 * 290.0 * 1e3)  # -173.975 dBm/Hz
    nf_adc = nsd_dbm - kt0_dbm
    print(f"  NSD = {nsd_dbfs:.2f} dBFS/Hz = {nsd_dbm:.2f} dBm/Hz (at P_FS = +{p_fs_dbm:.1f} dBm)")
    print(f"  Implied bare ADC NF = {nf_adc:.2f} dB (kT0 = {kt0_dbm:.2f} dBm/Hz)")
    for bw_hz in [2400.0, 10e3, 200e3, 2e6]:
        gp = 10.0 * np.log10(b_nyq / bw_hz)
        dr = snr0_dbfs + gp
        mds_0db = nsd_dbm + 10.0 * np.log10(bw_hz)
        print(f"  BW = {bw_hz/1e3:7.1f} kHz: G_p = {gp:5.2f} dB | DR = {dr:6.2f} dB | "
              f"MDS(0dB SNR) = {mds_0db:7.2f} dBm | MDS(3dB SNR) = {mds_0db+3.0:7.2f} dBm")

    f_mhz = 30.0
    models = [
        ("ITU-R P.372 Rural Man-Made", 67.2 - 27.7 * np.log10(f_mhz)),
        ("ITU-R P.372 Galactic (30 MHz)", 52.0 - 23.0 * np.log10(f_mhz)),
        ("ITU-R P.372 Quiet Rural", 53.6 - 28.6 * np.log10(f_mhz)),
    ]
    f_lna = 10.0**(3.0 / 10.0)  # NF_LNA = 3.0 dB
    for label, fa_db in models:
        fa = 10.0**(fa_db / 10.0)
        f_sys_critA = 1.0 + (10.0**(3.0 / 10.0) - 1.0) * fa
        f_sys_critB = 10.0**((fa_db - 3.0) / 10.0)
        f2_bare = 10.0**(nf_adc / 10.0)
        f2_loss = 10.0**((nf_adc + 1.5) / 10.0)
        g_A_bare = 0.0 if f_sys_critA >= f2_bare else 10.0 * np.log10((f2_bare - 1.0) / (f_sys_critA - f_lna))
        g_A_loss = 0.0 if f_sys_critA >= f2_loss else 10.0 * np.log10((f2_loss - 1.0) / (f_sys_critA - f_lna))
        g_B_bare = 0.0 if f_sys_critB >= f2_bare else 10.0 * np.log10((f2_bare - 1.0) / (f_sys_critB - f_lna))
        g_B_loss = 0.0 if f_sys_critB >= f2_loss else 10.0 * np.log10((f2_loss - 1.0) / (f_sys_critB - f_lna))
        print(f"  {label:30s} (Fa={fa_db:5.2f} dB): "
              f"CritA G_min={g_A_bare:4.1f}/{g_A_loss:4.1f} dB | CritB G_min={g_B_bare:4.1f}/{g_B_loss:4.1f} dB")
    print()


def section_4_ddc():
    print("=== 4. DDC CIC DECIMATOR & ECP5 FIT ===")
    for desc, R, bw_ratio in [
        ("Direct CIC R=64 (80% of f_cic)", 64, 0.8),
        ("CIC R=32 + 2:1 CFIR (80% of f_out = 40% of f_cic)", 32, 0.4),
        ("CIC R=16 + HB + CFIR (80% of f_out = 20% of f_cic)", 16, 0.2),
    ]:
        print(f"  [{desc}]")
        for N in [4, 5, 6]:
            fp = bw_ratio / (2.0 * R)
            fa = (1.0 - bw_ratio / 2.0) / R
            hp = (np.sin(np.pi * R * fp) / (R * np.sin(np.pi * fp)))**N
            ha = np.abs(np.sin(np.pi * R * fa) / (R * np.sin(np.pi * fa)))**N
            droop = 20.0 * np.log10(hp)
            arej = -20.0 * np.log10(ha)
            bg = int(np.ceil(N * np.log2(R)))
            print(f"    N={N}: BitGrowth={bg:2d}b (Bmax={16+bg:2d}b) | Droop={droop:6.2f} dB | "
                  f"AliasRej(DC)={arej:6.2f} dB | AliasRej(edge)={arej+droop:6.2f} dB")
    print()


def section_5_aaf(fp=55e6, fstop=70e6):
    print("=== 5. ANTI-ALIAS FILTER (0-55 MHz Passband, >=70 MHz Stopband) ===")
    for rp in [0.5, 1.0]:
        for a_stop in [77.0, 91.0, 115.0]:
            nb, _ = signal.buttord(fp, fstop, rp, a_stop, analog=True)
            nc, _ = signal.cheb1ord(fp, fstop, rp, a_stop, analog=True)
            ne, _ = signal.ellipord(fp, fstop, rp, a_stop, analog=True)
            print(f"  Rp={rp:.1f} dB, A_stop={a_stop:5.1f} dB -> Butterworth N={nb:2d} | Chebyshev N={nc:2d} | Elliptic N={ne:2d}")
    print()


def section_6_pcb(h=0.2104, t=0.035, er=4.4):
    print("=== 6. PCB IMPEDANCE (JLC04161H-7628: h=0.2104 mm, t=0.035 mm) ===")

    def microstrip_se(w, er_val):
        dw1 = (t / np.pi) * np.log(1.0 + (4.0 * np.e) / ((t / h) * (1.0 / np.tanh(np.sqrt(6.517 * w / h)))**2))
        we = w + 0.5 * dw1 * (1.0 + 1.0 / np.cosh(np.sqrt(er_val - 1.0)))
        u = we / h
        a = 1.0 + (1.0 / 49.0) * np.log((u**4 + (u / 52.0)**2) / (u**4 + 0.432)) + (1.0 / 18.7) * np.log(1.0 + (u / 18.1)**3)
        b = 0.564 * ((er_val - 0.9) / (er_val + 3.0))**0.053
        eeff = (er_val + 1.0) / 2.0 + ((er_val - 1.0) / 2.0) * (1.0 + 10.0 / u)**(-a * b)
        fu = 6.0 + (2.0 * np.pi - 6.0) * np.exp(-(30.666 / u)**0.7528)
        z0 = (60.0 / np.sqrt(eeff)) * np.log(fu / u + np.sqrt(1.0 + (2.0 / u)**2))
        return z0, eeff

    def kj_diff(w, s, er_val):
        u = w / h
        g = s / h
        t_h = t / h
        du_t = (t_h / np.pi) * np.log(1.0 + (4.0 * np.e) / (t_h * (1.0 / np.tanh(np.sqrt(6.517 * u)))**2))
        du_to = du_t * (1.0 - 0.5 * np.exp(-0.69 * du_t / t_h))
        u_o = u + du_to * 0.5 * (1.0 + 1.0 / np.cosh(np.sqrt(er_val - 1.0)))
        z0_s, eeff_s = microstrip_se(w, er_val)
        z0_air_o = z0_s * np.sqrt(eeff_s)
        a_o = 0.7287 * (eeff_s - (er_val + 1.0) / 2.0) * (1.0 - np.exp(-0.179 * (u_o**0.9236)))
        b_o = (0.747 * er_val) / (0.15 + er_val)
        c_o = b_o - (b_o - 0.207) * np.exp(-0.414 * u_o)
        d_o = 0.593 + 0.694 * np.exp(-0.562 * u_o)
        eeff_o = ((er_val + 1.0) / 2.0 + a_o - eeff_s) * np.exp(-c_o * (g**d_o)) + eeff_s
        q1 = 0.8695 * (u_o**0.194)
        q2 = 1.0 + 0.7519 * g + 0.189 * (g**2.31)
        q3 = 0.1975 + (16.6 + (8.4 / g)**6)**(-0.387) + (1.0 / 241.0) * np.log((g**10) / (1.0 + (g / 3.4)**10))
        q4 = (2.0 * q1 / q2) / (np.exp(-g) * (u_o**q3) + (2.0 - np.exp(-g)) * (u_o**(-q3)))
        q5 = 1.794 + 1.14 * np.log(1.0 + 0.638 / (g + 0.517 * (g**2.43)))
        q6 = 0.2305 + (1.0 / 281.3) * np.log((g**10) / (1.0 + (g / 5.8)**10)) + (1.0 / 5.1) * np.log(1.0 + 0.598 * (g**1.154))
        q7 = (10.0 + 190.0 * (g**2)) / (1.0 + 82.3 * (g**3))
        q8 = np.exp(-6.5 - 0.95 * np.log(g) - (g / 0.15)**5)
        q9 = np.log(q7) * (q8 + 1.0 / 16.5)
        q10 = (q2 * q4 - q5 * np.exp(np.log(u_o) * q6 * (u_o**(-q9)))) / q2
        z0o = (z0_air_o / np.sqrt(eeff_o)) / (1.0 - (z0_air_o / 376.730313) * q10)
        zdiff_ipc = 2.0 * z0_s * (1.0 - 0.48 * np.exp(-0.96 * g))
        return 2.0 * z0o, zdiff_ipc

    w50_44 = brentq(lambda w: microstrip_se(w, 4.4)[0] - 50.0, 0.05, 1.0)
    w50_46 = brentq(lambda w: microstrip_se(w, 4.6)[0] - 50.0, 0.05, 1.0)
    print(f"  50 ohm SE: w(er=4.4, bare H-J) = {w50_44:.3f} mm ({w50_44/0.0254:.2f} mil) | "
          f"w(er=4.6) = {w50_46:.3f} mm ({w50_46/0.0254:.2f} mil)")
    for zd_target, label in [(90.0, "90 ohm Diff (USB3)"), (100.0, "100 ohm Diff (LVDS)")]:
        for s in [0.127, 0.150, 0.200]:
            w_kj = brentq(lambda w: kj_diff(w, s, 4.4)[0] - zd_target, 0.05, 1.0)
            w_ipc = brentq(lambda w: kj_diff(w, s, 4.6)[1] - zd_target, 0.05, 1.0)
            print(f"  {label:20s} @ s={s:.3f} mm ({s/0.0254:4.1f} mil): "
                  f"w(K-J bare, er=4.4) = {w_kj:.3f} mm ({w_kj/0.0254:5.2f} mil) | "
                  f"w(Coated/IPC, er=4.6) = {w_ipc:.3f} mm ({w_ipc/0.0254:5.2f} mil)")


if __name__ == "__main__":
    section_1_usb3()
    section_2_jitter()
    section_3_dynamic_range()
    section_4_ddc()
    section_5_aaf()
    section_6_pcb()
