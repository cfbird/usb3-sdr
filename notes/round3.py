#!/usr/bin/env python3
"""
Round 3 Parametric Math & Verification Script (notes/round3.py)
1. LNA Bias Network & Stacked Choke Impedance (0.1 - 32 MHz vs >=10 MHz)
2. Cascaded NF, IIP3, SFDR3 (2.4 kHz BW), Clip Level, and Min LNA OIP3 Budget
3. TPS62A01A/02A (2.4 MHz) Damped LC Post-Filter & Spur Suppression at AD9649
"""

import numpy as np


def section_1_lna_bias():
    print("=== 1. LNA BIAS TEE & STACKED CHOKE (0.1 - 32 MHz) ===")
    r0 = 50.0
    f_min = 100e3
    l_min = (10.0 * r0) / (2.0 * np.pi * f_min)
    c_3db = 1.0 / (2.0 * np.pi * f_min * r0)
    c_flat = 10.0 / (2.0 * np.pi * f_min * r0)
    print(f"  For X_L >= 10*R0 = 500 ohm at 100 kHz: L_choke >= {l_min*1e6:.1f} uH -> E12: 820 uH or 1.0 mH")
    print(f"  For 100 kHz coupling cap: C(-3dB vs 50 ohm) = {c_3db*1e9:.1f} nF | C(X_C <= 5 ohm, <0.04 dB droop) = {c_flat*1e9:.1f} nF -> use 470 nF or 1 uF")

    # Compare single 1 mH power/RF choke (C_p ~ 20 pF -> SRF = 1.125 MHz)
    # vs 3-stage stacked choke: 1.0 uH (0603, SRF=350 MHz) + 22 uH||1.5k (0805, SRF=40 MHz) + 1.0 mH||2.2k (SRF=1.125 MHz)
    freqs = np.array([0.1e6, 1.0e6, 3.0e6, 10.0e6, 30.0e6, 50.0e6])
    s = 1j * 2.0 * np.pi * freqs

    def z_ind_srf(l_val, r_dc, f_srf, r_par=None):
        cp = 1.0 / ((2.0 * np.pi * f_srf)**2 * l_val)
        y = 1.0 / (r_dc + s * l_val) + s * cp
        if r_par is not None:
            y = y + 1.0 / r_par
        return 1.0 / y

    z_single_1mh = z_ind_srf(1.0e-3, 3.5, 1.125e6)  # C_p = 20 pF typical for 1 mH >=100 mA inductor
    z_stacked = (z_ind_srf(1.0e-6, 0.35, 350e6) +
                 z_ind_srf(22e-6, 1.2, 40e6, r_par=1500.0) +
                 z_ind_srf(1.0e-3, 3.5, 1.125e6, r_par=2200.0))

    # Insertion loss & return loss of shunt Z_choke across a 50-ohm line:
    il_single = 20.0 * np.log10(np.abs(1.0 + 25.0 / z_single_1mh))
    il_stacked = 20.0 * np.log10(np.abs(1.0 + 25.0 / z_stacked))

    for i, f in enumerate(freqs):
        print(f"  f={f/1e6:5.1f} MHz: Single 1mH(Cp=20pF) |Z|={np.abs(z_single_1mh[i]):6.1f} ohm (IL={il_single[i]:.3f} dB) | "
              f"Stacked (1uH+22uH+1mH) |Z|={np.abs(z_stacked[i]):6.1f} ohm (IL={il_stacked[i]:.3f} dB)")
    print()


def section_2_ip3_budget():
    print("=== 2. DYNAMIC RANGE, NF & IIP3 CASCADE BUDGET ===")
    l_sw = 0.3
    l_lpf1 = 1.5
    l_lpf2 = 1.5
    l_bal = 1.0  # Prompt value (ADT4-6T+ typ datasheet is 0.3-0.4 dB)
    l_pre = l_sw + l_lpf1   # 1.8 dB
    l_post = l_lpf2 + l_bal # 2.5 dB
    l_tot = l_pre + l_post  # 4.3 dB

    p_fs_adc = 4.0
    nf_adc = 27.9
    kt0 = -173.975
    bw = 2400.0
    bw_db = 10.0 * np.log10(bw)

    # AD9649 two-tone SFDR = 90 dBc at -7 dBFS per tone (P_tone = +4 - 7 = -3 dBm at ADC input):
    # Conv A: 90 dBc relative to carrier tone (-3 dBm) -> IIP3_ADC = -3 + 90/2 = +42.0 dBm
    # Conv B: 90 dBFS (83 dBc relative to -3 dBm tone) -> IIP3_ADC = -3 + 83/2 = +38.5 dBm
    for conv_label, iip3_adc in [("Conv A: 90 dBc -> IIP3_ADC = +42.0 dBm", 42.0),
                                 ("Conv B: 90 dBFS (83 dBc) -> IIP3_ADC = +38.5 dBm", 38.5)]:
        print(f"  [{conv_label}]")
        oip3_lna_match = iip3_adc + l_post
        print(f"  -> LNA OIP3 required to match ADC IIP3 (3 dB IIP3 / 2 dB SFDR3 split): +{oip3_lna_match:.1f} dBm "
              f"(or +{oip3_lna_match + 6.0:.1f} dBm for <1 dB IIP3 penalty)")

        # LNA OFF (Bypassed):
        nf_off = l_tot + nf_adc
        mds_off = kt0 + nf_off + bw_db
        iip3_off = iip3_adc + l_tot
        clip_off = p_fs_adc + l_tot
        sfdr3_off = (2.0 / 3.0) * (iip3_off - mds_off)
        print(f"  Mode: LNA OFF (G_net = -{l_tot:.1f} dB) | NF = {nf_off:5.2f} dB | MDS(2.4k) = {mds_off:7.2f} dBm | "
              f"IIP3 = +{iip3_off:5.2f} dBm | Clip = +{clip_off:4.2f} dBm | SFDR3 = {sfdr3_off:6.2f} dB")

        for g_lna in [15.0, 20.0]:
            f_sys_15 = (10**(l_pre/10)) * (10**(1.5/10) + (10**((l_post + nf_adc)/10) - 1.0) / (10**(g_lna/10)))
            f_sys_30 = (10**(l_pre/10)) * (10**(3.0/10) + (10**((l_post + nf_adc)/10) - 1.0) / (10**(g_lna/10)))
            nf_sys = 10.0 * np.log10(f_sys_15)
            nf_sys_3 = 10.0 * np.log10(f_sys_30)
            mds_on = kt0 + nf_sys + bw_db
            clip_on = p_fs_adc - (g_lna - l_tot)
            iip3_adc_ant = iip3_adc - (g_lna - l_tot)

            for oip3_lna in [34.5, 38.5, oip3_lna_match, 50.0]:
                iip3_lna_ant = oip3_lna - g_lna + l_pre
                iip3_casc = -10.0 * np.log10(10.0**(-iip3_lna_ant / 10.0) + 10.0**(-iip3_adc_ant / 10.0))
                sfdr3_on = (2.0 / 3.0) * (iip3_casc - mds_on)
                print(f"  Mode: LNA G={g_lna:2.0f}dB, OIP3=+{oip3_lna:4.1f}dBm | NF={nf_sys:5.2f}dB ({nf_sys_3:5.2f}dB @NF3) | "
                      f"MDS={mds_on:7.2f}dBm | IIP3={iip3_casc:+6.2f}dBm | Clip={clip_on:+6.2f}dBm | SFDR3={sfdr3_on:6.2f}dB")
    print()


def section_3_buck_filter():
    print("=== 3. BUCK 2.4 MHz POST-FILTER & SPUR BUDGET ===")
    v_rip_pp = 20e-3
    v_fs_pp = 2.0
    rip_dbfs = 20.0 * np.log10(v_rip_pp / v_fs_pp)  # -40.0 dBFS
    snr0 = 74.1
    fs = 80e6
    bw = 2400.0
    gp = 10.0 * np.log10((fs / 2.0) / bw)
    noise_2k4_dbfs = -snr0 - gp  # -116.32 dBFS
    target_spur_dbfs = noise_2k4_dbfs - 10.0  # -126.32 dBFS (10 dB below 2.4 kHz floor)
    req_tot_att = rip_dbfs - target_spur_dbfs # 86.32 dB

    print(f"  20 mVpp ripple = {rip_dbfs:.1f} dBFS (vs 2 Vpp FS)")
    print(f"  AD9649-80 noise floor in 2.4 kHz = {noise_2k4_dbfs:.2f} dBFS")
    print(f"  Required total attenuation for spur <= -126.3 dBFS (-10 dB below floor): {req_tot_att:.2f} dB "
          f"(or {req_tot_att+10:.2f} dB for -20 dB margin)")

    psrr_adc = 40.0
    f_harm = np.array([2.4e6, 4.8e6, 7.2e6])
    psrr_ldo_ds = np.array([38.0, 33.0, 30.0])
    psrr_ldo_opt = np.array([55.0, 49.0, 45.0])

    def lc_response(freqs, esl_scale=1.0):
        s = 1j * 2.0 * np.pi * freqs
        z_ser = (0.10 + 0.47) + s * 1.0e-6
        z_c1 = 0.005 + 1.0 / (s * 10e-6) + s * (0.5e-9 * esl_scale)
        z_c2 = 0.010 + 1.0 / (s * 1e-6) + s * (0.4e-9 * esl_scale)
        z_sh = 1.0 / (1.0 / z_c1 + 1.0 / z_c2 + 1.0 / 50.0)
        return 20.0 * np.log10(np.abs(z_sh / (z_ser + z_sh)))

    f_sweep = np.logspace(3, 7.3, 1000)
    g_sweep = lc_response(f_sweep)
    att_lc_nom = -lc_response(f_harm, esl_scale=1.0)
    att_lc_mnt = -lc_response(f_harm, esl_scale=2.0)

    print(f"  Damped LC Filter (L=1.0 uH + R_damp=0.47 ohm -> 10 uF || 1 uF): "
          f"f0=48.0 kHz, zeta=0.95, Max Peaking={np.max(g_sweep):+.2f} dB")
    for i, f in enumerate(f_harm):
        req_lc_ds = req_tot_att - (psrr_ldo_ds[i] + psrr_adc)
        req_lc_opt = max(0.0, req_tot_att - (psrr_ldo_opt[i] + psrr_adc))
        spur_out = rip_dbfs - (att_lc_mnt[i] + psrr_ldo_ds[i] + psrr_adc)
        print(f"  f={f/1e6:3.1f} MHz: LDO_PSRR={psrr_ldo_ds[i]:.0f}dB (opt {psrr_ldo_opt[i]:.0f}dB) + ADC_PSRR=40dB "
              f"-> Req LC Att (-10dB/-20dB margin) = {req_lc_ds:4.1f}/{req_lc_ds+10:4.1f} dB (opt {req_lc_opt:4.1f}/{req_lc_opt+10:4.1f} dB) | "
              f"Actual LC Att = {att_lc_nom[i]:4.1f} dB ({att_lc_mnt[i]:4.1f} dB w/ via ESL) -> Spur = {spur_out:6.1f} dBFS")


if __name__ == "__main__":
    section_1_lna_bias()
    section_2_ip3_budget()
    section_3_buck_filter()
