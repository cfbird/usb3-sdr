#!/usr/bin/env python3
"""
Anti-Alias Filter Chain Synthesis & ABCD Parasitic Simulation (notes/aaf_sim.py)
Target:
  - Z0 = 50 ohm, fs = 80 MSPS, Passband = 0.1 - 32 MHz (ripple <= 0.5 dB), First Alias = 48 MHz
  - LPF#1 & LPF#2: 7th-order Elliptic (Cauer) Low-Pass Filter, E12 Inductors (0805HP/LQW18) & E24 C0G Capacitors
  - FM Band-Stop Notch: 3-branch self-matched Pi Band-Stop Filter (88 - 108 MHz >= 40 dB, minimal effect < 32 MHz)
  - Cascade Simulation: LPF#1 + FM Notch + LPF#2 via 2x2 ABCD Matrices with:
      * Inductor skin-effect Q(f) = Q_100MHz * sqrt(f / 100 MHz), Q_100MHz in {40, 50, 60}
      * Inductor parallel parasitic capacitance C_p from datasheet SRF (Coilcraft 0805HP / Murata LQW18AN)
      * Capacitor series ESL = 0.5 nH (0603 C0G) and Q_C = 1000
"""

import numpy as np
from scipy import signal

E12 = np.array([1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2])
E24 = np.array([1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0,
                3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1])


def snap_value(val, series):
    exp = np.floor(np.log10(val))
    candidates = np.concatenate([series * 0.1, series, series * 10.0]) * (10.0**exp)
    return candidates[np.argmin(np.abs(candidates - val))]


def synthesize_cauer_7_ladder(rp_db, as_db, fc_hz, r0=50.0, perm=(0, 1, 2)):
    """
    Exact Darlington / Fujisawa zero-shifting LC ladder synthesis for a 7th-order
    minimum-inductance (shunt-C first) Elliptic/Cauer Low-Pass Filter.
    Topology: Shunt C1 -> Series (L2||C2) -> Shunt C3 -> Series (L4||C4) -> Shunt C5 -> Series (L6||C6) -> Shunt C7
    """
    z, p, k = signal.ellip(7, rp_db, as_db, 1.0, btype="low", analog=True, output="zpk")
    wz = np.sort(np.abs(z[np.imag(z) > 0]))
    E = np.poly(p)
    P = k * np.poly(z)
    EE = np.polymul(E, E * ((-1.0)**np.arange(7, -1, -1)))
    PP = np.polymul(P, P * ((-1.0)**np.arange(6, -1, -1)))
    PP_pad = np.zeros_like(EE)
    PP_pad[len(EE) - len(PP):] = PP
    roots_u = np.sort(np.real(np.roots((-(EE - PP_pad))[::2][:-1])))
    u_unique = 0.5 * (roots_u[0::2] + roots_u[1::2])
    F = np.zeros(8)
    F[0::2] = -np.poly(u_unique)
    num_Y, den_Y = E - F, (E + F)[1:]

    C_sh_norm, L_s_norm, C_s_norm = [], [], []
    for w_z in [wz[perm[0]], wz[perm[1]], wz[perm[2]]]:
        s_z = 1j * w_z
        c_i = np.real((np.polyval(num_Y, s_z) / np.polyval(den_Y, s_z)) / s_z)
        C_sh_norm.append(c_i)
        num_Y = num_Y - np.polymul([c_i, 0.0], den_Y)
        q_num, _ = np.polydiv(num_Y, [1.0, 0.0, w_z**2])
        inv_ck = np.real(np.polyval(den_Y, s_z) / (s_z * np.polyval(q_num, s_z)))
        c_k = 1.0 / inv_ck
        l_k = 1.0 / (c_k * (w_z**2))
        L_s_norm.append(l_k)
        C_s_norm.append(c_k)
        q_den, _ = np.polydiv(den_Y - np.polymul([inv_ck, 0.0], q_num), [1.0, 0.0, w_z**2])
        num_Y, den_Y = q_num, q_den
    C_sh_norm.append(np.real(num_Y[0] / den_Y[0]))

    wc = 2.0 * np.pi * fc_hz
    C_sh_exact = np.array(C_sh_norm) / (wc * r0)
    L_s_exact = np.array(L_s_norm) * r0 / wc
    C_s_exact = np.array(C_s_norm) / (wc * r0)

    C_sh_snap = np.array([snap_value(c, E24) for c in C_sh_exact])
    L_s_snap = np.array([snap_value(l, E12) for l in L_s_exact])
    # Snap C_s to E24 while preserving each tank's resonant zero frequency 1/sqrt(L_k * C_k)
    C_s_snap = np.array([snap_value((L_s_exact[k] * C_s_exact[k]) / L_s_snap[k], E24) for k in range(3)])
    return (C_sh_exact, L_s_exact, C_s_exact), (C_sh_snap, L_s_snap, C_s_snap)


def abcd_cap(freqs, c_val, esl=0.0, q_c=None):
    w = 2.0 * np.pi * freqs
    s = 1j * w
    zc = 1.0 / (s * c_val)
    if esl > 0.0:
        zc = zc + s * esl
    if q_c is not None:
        zc = zc + 1.0 / (w * c_val * q_c)
    return zc


def abcd_ind(freqs, l_val, q_100mhz=None, srf_hz=None):
    w = 2.0 * np.pi * freqs
    s = 1j * w
    zl = s * l_val
    if q_100mhz is not None:
        r_100 = (2.0 * np.pi * 100e6 * l_val) / q_100mhz
        zl = zl + r_100 * np.sqrt(freqs / 100e6)
    if srf_hz is not None:
        cp = 1.0 / ((2.0 * np.pi * srf_hz)**2 * l_val)
        zl = 1.0 / (1.0 / zl + s * cp)
    return zl


def build_lpf_abcd(freqs, C_sh, L_s, C_s, q_l=None, srf_l=None, esl_c=0.0, q_c=None):
    n = len(freqs)
    A = np.ones(n, dtype=complex)
    B = np.zeros(n, dtype=complex)
    C = np.zeros(n, dtype=complex)
    D = np.ones(n, dtype=complex)
    for k in range(3):
        y_sh = 1.0 / abcd_cap(freqs, C_sh[k], esl_c, q_c)
        A, C = A + B * y_sh, C + D * y_sh
        z_l = abcd_ind(freqs, L_s[k], q_l, srf_l[k] if srf_l is not None else None)
        z_c = abcd_cap(freqs, C_s[k], esl_c, q_c)
        z_tank = 1.0 / (1.0 / z_l + 1.0 / z_c)
        B, D = A * z_tank + B, C * z_tank + D
    y_sh = 1.0 / abcd_cap(freqs, C_sh[3], esl_c, q_c)
    A, C = A + B * y_sh, C + D * y_sh
    return A, B, C, D


def build_bsf_abcd(freqs, L_n, C_n, q_l=None, srf_l=None, esl_c=0.0, q_c=None):
    """
    3-Branch Self-Matched Pi FM Band-Stop Filter (88-108 MHz):
      Branch 1 (Shunt series-LC):   L_n[0] + C_n[0] to GND (f_z1 ~ 88.9 MHz)
      Branch 2 (Series parallel-LC): L_n[1] || C_n[1] in series (f_z2 ~ 96.9 MHz)
      Branch 3 (Shunt series-LC):   L_n[2] + C_n[2] to GND (f_z3 ~ 107.1 MHz)
    """
    n = len(freqs)
    A = np.ones(n, dtype=complex)
    B = np.zeros(n, dtype=complex)
    C = np.zeros(n, dtype=complex)
    D = np.ones(n, dtype=complex)

    y1 = 1.0 / (abcd_ind(freqs, L_n[0], q_l, srf_l[0] if srf_l is not None else None) +
                abcd_cap(freqs, C_n[0], esl_c, q_c))
    A, C = A + B * y1, C + D * y1

    z2 = 1.0 / (1.0 / abcd_ind(freqs, L_n[1], q_l, srf_l[1] if srf_l is not None else None) +
                1.0 / abcd_cap(freqs, C_n[1], esl_c, q_c))
    B, D = A * z2 + B, C * z2 + D

    y3 = 1.0 / (abcd_ind(freqs, L_n[2], q_l, srf_l[2] if srf_l is not None else None) +
                abcd_cap(freqs, C_n[2], esl_c, q_c))
    A, C = A + B * y3, C + D * y3
    return A, B, C, D


def mult_abcd(m1, m2):
    A1, B1, C1, D1 = m1
    A2, B2, C2, D2 = m2
    return (A1 * A2 + B1 * C2, A1 * B2 + B1 * D2, C1 * A2 + D1 * C2, C1 * B2 + D1 * D2)


def abcd_to_sparams(m, r0=50.0):
    A, B, C, D = m
    denom = A + B / r0 + C * r0 + D
    s21 = 2.0 / denom
    s11 = (A + B / r0 - C * r0 - D) / denom
    return 20.0 * np.log10(np.abs(s21)), 20.0 * np.log10(np.abs(s11))


def main():
    # 1. Synthesize 7th-Order Elliptic LPF (Pre-distorted fc=35.5 MHz to keep finite-Q loss low at 32 MHz)
    exact_35, snap_35 = synthesize_cauer_7_ladder(rp_db=0.08, as_db=61.0, fc_hz=35.5e6, perm=(0, 1, 2))
    C_sh, L_s, C_s = snap_35
    # Datasheet SRFs for Coilcraft 0805HP / Murata LQW18AN:
    # 180 nH -> 850 MHz, 270 nH -> 650 MHz
    srf_lpf = [850e6, 650e6, 650e6]

    # Also compute un-predistorted fc=32.6 MHz design for comparison:
    exact_32, snap_32 = synthesize_cauer_7_ladder(rp_db=0.06, as_db=61.0, fc_hz=32.6e6, perm=(1, 0, 2))

    # 2. FM Band-Stop Filter (88-108 MHz) E12(L)/E24(C) values:
    L_bsf = np.array([82.0, 180.0, 47.0]) * 1e-9
    C_bsf = np.array([39.0, 15.0, 47.0]) * 1e-12
    # Datasheet SRFs for 82 nH (1300 MHz), 180 nH (850 MHz), 47 nH (1700 MHz):
    srf_bsf = [1300e6, 850e6, 1700e6]

    print("=== 7TH-ORDER ELLIPTIC LPF ELEMENT VALUES (E12 L / E24 C) ===")
    print("Design A (Corner pre-distorted fc=35.5 MHz for low finite-Q droop at 32 MHz):")
    print(f"  Exact C_shunt (pF): {np.round(exact_35[0]*1e12, 2)} -> E24: {np.round(C_sh*1e12, 1)}")
    print(f"  Exact L_ser   (nH): {np.round(exact_35[1]*1e9, 1)} -> E12: {np.round(L_s*1e9, 0)}")
    print(f"  Exact C_ser   (pF): {np.round(exact_35[2]*1e12, 2)} -> E24: {np.round(C_s*1e12, 1)}")
    print("Design B (Nominal fc=32.6 MHz):")
    print(f"  Exact C_shunt (pF): {np.round(exact_32[0]*1e12, 2)} -> E24: {np.round(snap_32[0]*1e12, 1)}")
    print(f"  Exact L_ser   (nH): {np.round(exact_32[1]*1e9, 1)} -> E12: {np.round(snap_32[1]*1e9, 0)}")
    print(f"  Exact C_ser   (pF): {np.round(exact_32[2]*1e12, 2)} -> E24: {np.round(snap_32[2]*1e12, 1)}")

    print("\n=== FM BAND-STOP NOTCH (88-108 MHz) ELEMENT VALUES ===")
    print("  Shunt Trap 1 (88.9 MHz): L1 = 82 nH (E12), C1 = 39 pF (E24)")
    print("  Series Tank 2 (96.9 MHz): L2 = 180 nH (E12) || C2 = 15 pF (E24)")
    print("  Shunt Trap 3 (107.1 MHz): L3 = 47 nH (E12), C3 = 47 pF (E24)")

    f_pb = np.linspace(0.1e6, 32.0e6, 320)
    f_fm = np.linspace(88.0e6, 108.0e6, 201)
    f_spot = np.array([32.0e6, 48.0e6, 88.0e6, 98.0e6, 108.0e6, 150.0e6])

    for q_val, esl_val, use_srf, tag in [
        (None, 0.0, False, "Ideal Lossless (Snapped E12/E24)"),
        (50.0, 0.5e-9, True, "Realistic Parasitics (Q=50 @ 100MHz, ESL=0.5nH, SRF)"),
        (40.0, 0.5e-9, True, "Worst-Case Q=40 @ 100MHz, ESL=0.5nH, SRF"),
        (60.0, 0.5e-9, True, "High-Q=60 @ 100MHz, ESL=0.5nH, SRF"),
    ]:
        qc = 1000.0 if q_val is not None else None
        sl_lpf = srf_lpf if use_srf else None
        sl_bsf = srf_bsf if use_srf else None

        m_lpf_pb = build_lpf_abcd(f_pb, C_sh, L_s, C_s, q_l=q_val, srf_l=sl_lpf, esl_c=esl_val, q_c=qc)
        m_bsf_pb = build_bsf_abcd(f_pb, L_bsf, C_bsf, q_l=q_val, srf_l=sl_bsf, esl_c=esl_val, q_c=qc)
        m_cas_pb = mult_abcd(mult_abcd(m_lpf_pb, m_bsf_pb), m_lpf_pb)

        s21_lpf_pb, s11_lpf_pb = abcd_to_sparams(m_lpf_pb)
        s21_bsf_pb, s11_bsf_pb = abcd_to_sparams(m_bsf_pb)
        s21_cas_pb, s11_cas_pb = abcd_to_sparams(m_cas_pb)

        m_bsf_fm = build_bsf_abcd(f_fm, L_bsf, C_bsf, q_l=q_val, srf_l=sl_bsf, esl_c=esl_val, q_c=qc)
        s21_bsf_fm, _ = abcd_to_sparams(m_bsf_fm)

        m_lpf_sp = build_lpf_abcd(f_spot, C_sh, L_s, C_s, q_l=q_val, srf_l=sl_lpf, esl_c=esl_val, q_c=qc)
        m_bsf_sp = build_bsf_abcd(f_spot, L_bsf, C_bsf, q_l=q_val, srf_l=sl_bsf, esl_c=esl_val, q_c=qc)
        m_cas_sp = mult_abcd(mult_abcd(m_lpf_sp, m_bsf_sp), m_lpf_sp)

        s21_lpf_sp, _ = abcd_to_sparams(m_lpf_sp)
        s21_bsf_sp, _ = abcd_to_sparams(m_bsf_sp)
        s21_cas_sp, _ = abcd_to_sparams(m_cas_sp)

        print(f"\n=== {tag} ===")
        print(f"  Single LPF Passband (0.1-32 MHz):  Ripple/Droop = {np.max(s21_lpf_pb)-np.min(s21_lpf_pb):.2f} dB, "
              f"Min RL = {-np.max(s11_lpf_pb):.2f} dB")
        print(f"  Standalone FM Notch (0.1-32 MHz):  Max IL = {-np.min(s21_bsf_pb):.2f} dB, "
              f"Min RL = {-np.max(s11_bsf_pb):.2f} dB, Min 88-108 MHz Rej = {np.min(-s21_bsf_fm):.2f} dB")
        print(f"  Full Cascade (LPF1+Notch+LPF2):    Ripple/Droop = {np.max(s21_cas_pb)-np.min(s21_cas_pb):.2f} dB, "
              f"Min RL = {-np.max(s11_cas_pb):.2f} dB")
        print("  Spot Frequencies [32, 48, 88, 98, 108, 150] MHz S21 (dB):")
        for idx, f_hz in enumerate(f_spot):
            print(f"    {f_hz/1e6:5.0f} MHz: LPF1 = {s21_lpf_sp[idx]:7.2f} dB | "
                  f"Notch = {s21_bsf_sp[idx]:7.2f} dB | Cascade = {s21_cas_sp[idx]:8.2f} dB")


if __name__ == "__main__":
    main()
