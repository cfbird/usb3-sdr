#!/usr/bin/env python3
"""
Bus timing and trace-length verification script for usb3-sdr (Round 6 + Round 9 R1 update).
Checks routed net lengths on the AD9649 (80 MHz) and FT601Q (100 MHz) buses against
propagation delay, setup/hold slack, and Signal Integrity (SI) routing constraints.

Usage:
  python3 notes/pinswap/agy_timing_check.py --self-test
  python3 notes/pinswap/agy_timing_check.py path/to/usb3-sdr.kicad_pcb
  python3 notes/pinswap/agy_timing_check.py path/to/lengths.json -v
"""

import argparse
import json
import math
import os
import re
import sys

# ==============================================================================
# 1. Physical & Timing Constants (JLC04161H-7628 Stack-up + Datasheets)
# ==============================================================================
# Propagation delay bounds (ps/mm) on JLC04161H-7628 (h=0.2104 mm, er=4.4, w=0.15 mm, Z0=64 ohm)
TAU_FCU_MIN = 5.80  # F.Cu microstrip fast bound (ps/mm)
TAU_FCU_NOM = 6.00  # F.Cu microstrip nominal (ps/mm)
TAU_FCU_MAX = 6.20  # F.Cu microstrip slow bound (ps/mm)

TAU_BCU_MIN = 6.50  # B.Cu coated microstrip fast bound (ps/mm)
TAU_BCU_NOM = 6.75  # B.Cu coated microstrip nominal (ps/mm)
TAU_BCU_MAX = 7.00  # B.Cu coated microstrip slow bound (ps/mm)

# Conservative board-wide bounds across F.Cu/B.Cu mix
TAU_FAST = TAU_FCU_MIN  # 5.80 ps/mm
TAU_SLOW = TAU_BCU_MAX  # 7.00 ps/mm

# AD9649-80 (80 MHz, T = 12500 ps) + 22R + ECP5-25F-6 Bank 7 (LVCMOS18)
ADC_T_CLK_PS = 12500.0
ADC_SKEW_MIN_PS = 300.0     # t_DCO - t_DATA min (AD9649 Rev. B Table 4, p. 6)
ADC_SKEW_MAX_PS = 1100.0    # t_DCO - t_DATA max (AD9649 Rev. B Table 4, p. 6)
ADC_RC_NOM_PS = 440.0       # 22R * (4.5 pF + trace) delta-t_50% nominal (ps)
ADC_RC_DIFF_PS = 120.0      # max differential RC delay spread across bus (ps)
ECP5_ADC_TSU_PS = 3200.0    # ECP5 -6 Bank 7 PIO Input Setup (PCLK -> fabric/PIO) (ps)
ECP5_ADC_THD_PS = 500.0     # ECP5 -6 Bank 7 PIO Input Hold (ps)

# Old Round-6 rules (kept visible as comments per BRIEF_route_r1.md):
# ADC_MAX_SKEW_MM = 20.0
# ADC_MAX_TOTAL_MM = 50.0
# ADC_MAX_STUB_MM = 6.0
# FT_MAX_SKEW_MM = 15.0
# FT_MAX_TOTAL_MM = 35.0

# Updated Round-9 R1 rules (timing + SI):
ADC_MAX_SKEW_MM = 25.0      # +/- 25.0 mm to ADC_DCO (RC edge-matching limit; timing window is [-340, +518] mm w/ 0x16=0x80)
ADC_MAX_TOTAL_MM = 55.0     # <= 55.0 mm (AD9649 C_LOAD < 10 pF hard SI limit: 4.8 pF + 55*0.094 pF/mm = 9.97 pF)
ADC_MAX_STUB_MM = 8.0       # <= 8.0 mm (tau*L_stub <= t_r,int/6 ~ 85 ps, C_stub < 0.75 pF hard SI limit; R2 plan <= 5.05 mm)
ADC_SPI_MAX_MM = 120.0      # ADC_CSB/SCLK/SDIO exempt from DCO skew (1.25 MHz boot-only SPI in boot_seq.v, T_half = 400 ns)

# FT601Q (100 MHz, T = 10000 ps) + ECP5-25F-6 Bank 6/2/3 (LVCMOS33)
FT_T_CLK_PS = 10000.0
FT_TCO_MAX_PS = 7000.0      # FT601Q T_OD max (Table 6.3, p. 25)
FT_TCO_MIN_PS = 1000.0      # FT601Q T_OH min (Table 6.3, p. 25)
FT_TSU_MIN_PS = 3500.0      # FT601Q T_IS min (Table 6.3, p. 25)
FT_THD_MIN_PS = 0.0         # FT601Q T_IH min (Table 6.3, p. 25)

# Round-7 OFS1P3DX + PLL +112.5 deg (+3125 ps) parameters (active gateware in top.v):
ECP5_FT_PLL_SHIFT_PS = 3125.0
ECP5_FT_RD_TSU_IOREG_PS = 1800.0   # IFS1P3DX effective setup with +3125 ps PLL shift (ps)
ECP5_FT_RD_THD_IOREG_PS = -182.0   # IFS1P3DX effective hold with +3125 ps PLL shift (ps)
ECP5_FT_WR_TCO_MAX_IOREG_PS = 4800.0  # OFS1P3DX + +3125 ps PLL shift max clock-to-out (ps)
ECP5_FT_WR_TCO_MIN_IOREG_PS = 824.0   # OFS1P3DX + +3125 ps PLL shift min clock-to-out (ps)

# Legacy fabric-output parameters (informational only; superseded by Round-7 OFS1P3DX):
ECP5_FT_RD_TSU_FAB_PS = 2100.0
ECP5_FT_RD_THD_FAB_PS = 200.0
ECP5_FT_WR_TCO_MAX_FAB_PS = 5800.0
ECP5_FT_WR_TCO_MIN_FAB_PS = 2000.0

FT_MIN_SKEW_MM = -10.0      # L_sig - L_CLK >= -10.0 mm (read/write hold slack >= +680 ps)
FT_MAX_SKEW_MM = 30.0       # L_sig - L_CLK <= +30.0 mm (longer data traces increase hold slack; setup slack > +1400 ps)
FT_MAX_TOTAL_MM = 45.0      # <= 45.0 mm (LVCMOS33 tau*L <= t_r/3 SI limit; L_crit = t_r/(2*tau) = 69.2 mm)
FT_ASYNC_MAX_MM = 60.0      # FT_RESET_N/WAKEUP_N/GPIO0/GPIO1 asynchronous per FT601Q Table 3.2 (exempt from FT_CLK skew)

# Net lists
ADC_DATA_NETS = [f"ADC_D{i}" for i in range(14)] + ["ADC_OR"]
ADC_ALL_SYNC_NETS = ["ADC_DCO"] + ADC_DATA_NETS
ADC_STUB_NETS = [f"{n}_R" for n in ADC_ALL_SYNC_NETS]
ADC_SPI_NETS = ["ADC_CSB", "ADC_SCLK", "ADC_SDIO"]

FT_SYNC_NETS = (
    [f"FT_D{i}" for i in range(32)]
    + [f"FT_BE{i}" for i in range(4)]
    + ["FT_TXE_N", "FT_RXF_N", "FT_WR_N", "FT_RD_N", "FT_OE_N", "FT_SIWU_N"]
)
FT_ALL_SYNC_NETS = ["FT_CLK"] + FT_SYNC_NETS
FT_ASYNC_NETS = ["FT_RESET_N", "FT_WAKEUP_N", "FT_GPIO0", "FT_GPIO1"]


# ==============================================================================
# 2. Timing Slack Calculators
# ==============================================================================
def calc_adc_slack_ps(l_dco_mm: float, l_data_mm: float, inv_dco: bool = False):
    """
    Returns (setup_slack_ps, hold_slack_ps) for an ADC data net with total length
    l_data_mm (U8 -> R -> U12) relative to ADC_DCO length l_dco_mm (U8 -> R40 -> U12).
    """
    t_pcb_skew_setup = TAU_FCU_MIN * l_dco_mm - TAU_BCU_MAX * l_data_mm
    t_pcb_skew_hold = TAU_FCU_MAX * l_dco_mm - TAU_BCU_MIN * l_data_mm

    if not inv_dco:
        setup_slack = (
            ADC_SKEW_MIN_PS
            + t_pcb_skew_setup
            - ADC_RC_DIFF_PS
            - ECP5_ADC_TSU_PS
        )
        hold_slack = (
            ADC_T_CLK_PS
            - ADC_SKEW_MAX_PS
            - t_pcb_skew_hold
            - ADC_RC_DIFF_PS
            - ECP5_ADC_THD_PS
        )
    else:
        half_t = 0.5 * ADC_T_CLK_PS  # 6250 ps
        setup_slack = (
            half_t
            + ADC_SKEW_MIN_PS
            + t_pcb_skew_setup
            - ADC_RC_DIFF_PS
            - ECP5_ADC_TSU_PS
        )
        hold_slack = (
            half_t
            - ADC_SKEW_MAX_PS
            - t_pcb_skew_hold
            - ADC_RC_DIFF_PS
            - ECP5_ADC_THD_PS
        )
    return setup_slack, hold_slack


def calc_ft601_slack_ps(l_clk_mm: float, l_sig_mm: float):
    """
    Returns dict of setup/hold slacks (ps) for FT601 read and write cycles
    under the active Round-7 OFS1P3DX + PLL +112.5 deg gateware (plus legacy fabric fallback).
    """
    rd_setup = (
        FT_T_CLK_PS
        - FT_TCO_MAX_PS
        - TAU_BCU_MAX * l_sig_mm
        + TAU_FCU_MIN * l_clk_mm
        - ECP5_FT_RD_TSU_IOREG_PS
    )
    rd_hold = (
        FT_TCO_MIN_PS
        + TAU_FCU_MIN * l_sig_mm
        - TAU_FCU_MAX * l_clk_mm
        - ECP5_FT_RD_THD_IOREG_PS
    )
    wr_setup = (
        FT_T_CLK_PS
        - TAU_FCU_MAX * l_clk_mm
        - ECP5_FT_WR_TCO_MAX_IOREG_PS
        - TAU_BCU_MAX * l_sig_mm
        - FT_TSU_MIN_PS
    )
    wr_hold = (
        TAU_FCU_MIN * l_clk_mm
        + ECP5_FT_WR_TCO_MIN_IOREG_PS
        + TAU_FCU_MIN * l_sig_mm
        - FT_THD_MIN_PS
    )
    wr_setup_fab = (
        FT_T_CLK_PS
        - TAU_FCU_MAX * l_clk_mm
        - ECP5_FT_WR_TCO_MAX_FAB_PS
        - TAU_BCU_MAX * l_sig_mm
        - FT_TSU_MIN_PS
    )
    return {
        "rd_setup_ps": rd_setup,
        "rd_hold_ps": rd_hold,
        "wr_setup_ps": wr_setup,
        "wr_hold_ps": wr_hold,
        "wr_setup_fab_ps": wr_setup_fab,
    }


# ==============================================================================
# 3. KiCad PCB / JSON Length Parser
# ==============================================================================
def load_lengths_from_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if "lengths" in data and isinstance(data["lengths"], dict):
        return {k: float(v) for k, v in data["lengths"].items()}
    return {k: float(v) for k, v in data.items() if isinstance(v, (int, float))}


def load_lengths_from_kicad_pcb(path: str):
    """
    Parses a .kicad_pcb file (via pcbnew if available, else regex S-expression parser)
    and sums segment lengths per net name ( stripping hierarchical prefix '/ADC and clock/').
    """
    try:
        import pcbnew  # type: ignore
        board = pcbnew.LoadBoard(path)
        net_lengths = {}
        for track in board.GetTracks():
            if track.GetClass() == "PCB_VIA":
                continue
            net_name = track.GetNetname()
            short_name = net_name.split("/")[-1]
            length_mm = pcbnew.ToMM(track.GetLength())
            net_lengths[short_name] = net_lengths.get(short_name, 0.0) + length_mm
            if short_name != net_name:
                net_lengths[net_name] = net_lengths.get(net_name, 0.0) + length_mm
        return net_lengths
    except Exception:
        pass

    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    net_id_to_name = {}
    for m in re.finditer(r'\(\s*net\s+(\d+)\s+"([^"]*)"\s*\)', text):
        net_id = int(m.group(1))
        name = m.group(2)
        net_id_to_name[net_id] = name

    net_lengths = {}
    seg_pattern = re.compile(
        r'\(\s*segment\s+'
        r'\(\s*start\s+([-\d.]+)\s+([-\d.]+)\s*\)\s*'
        r'\(\s*end\s+([-\d.]+)\s+([-\d.]+)\s*\).*?'
        r'\(\s*net\s+(\d+)\s*\)',
        re.DOTALL,
    )
    for m in seg_pattern.finditer(text):
        x1, y1 = float(m.group(1)), float(m.group(2))
        x2, y2 = float(m.group(3)), float(m.group(4))
        net_id = int(m.group(5))
        seg_len = math.hypot(x2 - x1, y2 - y1)
        net_name = net_id_to_name.get(net_id, f"NET_{net_id}")
        short_name = net_name.split("/")[-1]
        net_lengths[short_name] = net_lengths.get(short_name, 0.0) + seg_len
        if short_name != net_name:
            net_lengths[net_name] = net_lengths.get(net_name, 0.0) + seg_len

    return net_lengths


# ==============================================================================
# 4. Verification & Reporting Engine
# ==============================================================================
def check_lengths(raw_lengths: dict, verbose: bool = False):
    """
    Evaluates all ADC and FT601 nets against the Round-9 R1 updated length, skew,
    stub, and setup/hold slack limits. Returns (all_passed: bool, report_lines: list[str]).
    """
    lines = []
    all_passed = True
    violations = []

    def get_len(net):
        if net in raw_lengths:
            return raw_lengths[net]
        alt = f"/ADC and clock/{net}"
        if alt in raw_lengths:
            return raw_lengths[alt]
        return None

    # --------------------------------------------------------------------------
    # A. ADC Bus Check (U8 -> R26..R41 -> U12 Bank 7)
    # --------------------------------------------------------------------------
    lines.append("=" * 78)
    lines.append("1. ADC BUS CHECK (AD9649 80 MHz -> 22R -> ECP5 Bank 7 LVCMOS18)")
    lines.append("=" * 78)

    dco_post = get_len("ADC_DCO")
    dco_stub = get_len("ADC_DCO_R")
    if dco_post is None:
        lines.append("  [WARN] ADC_DCO not found in routed lengths (unrouted board?).")
        all_passed = False
    else:
        dco_total = dco_post + (dco_stub if dco_stub is not None else 0.0)
        lines.append(
            f"  Reference Clock ADC_DCO: total = {dco_total:.2f} mm "
            f"(U8->R40 stub = {dco_stub if dco_stub is not None else 0.0:.2f} mm, "
            f"R40->U12 = {dco_post:.2f} mm)"
        )
        if dco_stub is not None and dco_stub > ADC_MAX_STUB_MM:
            violations.append(
                f"ADC_DCO_R stub = {dco_stub:.2f} mm > {ADC_MAX_STUB_MM:.1f} mm [SI]"
            )
            all_passed = False
        if dco_total > ADC_MAX_TOTAL_MM:
            violations.append(
                f"ADC_DCO total = {dco_total:.2f} mm > {ADC_MAX_TOTAL_MM:.1f} mm [SI: C_LOAD < 10 pF]"
            )
            all_passed = False

        lines.append(
            f"  {'Net':<10} {'Stub(mm)':>9} {'R->U12':>9} {'Total(mm)':>10} "
            f"{'SkewDCO':>9} {'Su/Hd(Def)':>14} {'Su/Hd(InvDCO)':>15} {'Status':>8}"
        )
        lines.append("  " + "-" * 74)

        for net in ADC_DATA_NETS:
            post = get_len(net)
            stub = get_len(f"{net}_R")
            stub_val = stub if stub is not None else 0.0
            stub_ok = (stub is None) or (stub_val <= ADC_MAX_STUB_MM)
            if not stub_ok:
                violations.append(
                    f"{net}_R stub {stub_val:.2f} mm > {ADC_MAX_STUB_MM:.1f} mm [SI]"
                )
                all_passed = False
            if post is None:
                violations.append(f"{net} missing/unrouted")
                all_passed = False
                if verbose or not stub_ok:
                    lines.append(
                        f"  {net:<10} {stub_val:>9.2f} {'MISSING':>9} {'-':>10} "
                        f"{'-':>9} {'-':>14} {'-':>15} {'FAIL':>8}"
                    )
                continue
            total = post + stub_val
            skew = total - dco_total

            su_def, hd_def = calc_adc_slack_ps(dco_total, total, inv_dco=False)
            su_inv, hd_inv = calc_adc_slack_ps(dco_total, total, inv_dco=True)

            tot_ok = total <= ADC_MAX_TOTAL_MM
            skew_ok = abs(skew) <= ADC_MAX_SKEW_MM
            # boot_seq.v configures AD9649 Reg 0x16 = 0x80 (invert DCO) at boot
            timing_ok = (su_inv >= 0.0) and (hd_inv >= 0.0)

            net_ok = stub_ok and tot_ok and skew_ok and timing_ok
            status = "PASS" if net_ok else "FAIL"
            if not net_ok:
                all_passed = False
                if not tot_ok:
                    violations.append(
                        f"{net} total {total:.2f} mm > {ADC_MAX_TOTAL_MM:.1f} mm [SI: C_LOAD]"
                    )
                if not skew_ok:
                    violations.append(
                        f"{net} skew {skew:+.2f} mm outside +/-{ADC_MAX_SKEW_MM:.1f} mm [SI/RC]"
                    )
                if not timing_ok:
                    violations.append(
                        f"{net} InvDCO (0x16=0x80) timing slack {su_inv:+.0f}/{hd_inv:+.0f} ps < 0 [TIMING]"
                    )

            if verbose or not net_ok:
                lines.append(
                    f"  {net:<10} {stub_val:>9.2f} {post:>9.2f} {total:>10.2f} "
                    f"{skew:>+9.2f} {su_def:>+6.0f}/{hd_def:>+6.0f} "
                    f"{su_inv:>+7.0f}/{hd_inv:>+6.0f} {status:>8}"
                )

        # Check boot-only SPI nets (exempt from DCO skew; sanity length cap <= 120 mm)
        for net in ADC_SPI_NETS:
            val = get_len(net)
            if val is not None:
                spi_ok = val <= ADC_SPI_MAX_MM
                if not spi_ok:
                    all_passed = False
                    violations.append(
                        f"{net} (SPI) length {val:.2f} mm > {ADC_SPI_MAX_MM:.1f} mm"
                    )
                if verbose or not spi_ok:
                    lines.append(
                        f"  {net:<10} {'(exempt)':>9} {val:>9.2f} {val:>10.2f} "
                        f"{'EXEMPT':>9} {'1.25MHz SPI':>14} {'T_half=400ns':>15} "
                        f"{'PASS' if spi_ok else 'FAIL':>8}"
                    )

    # --------------------------------------------------------------------------
    # B. FT601 Bus Check (U11 <-> U12 Bank 6/2/3)
    # --------------------------------------------------------------------------
    lines.append("")
    lines.append("=" * 78)
    lines.append("2. FT601 BUS CHECK (100 MHz Sync FIFO <-> ECP5 LVCMOS33, OFS1P3DX + 112.5 deg)")
    lines.append("=" * 78)

    ft_clk = get_len("FT_CLK")
    if ft_clk is None:
        lines.append("  [WARN] FT_CLK not found in routed lengths (unrouted board?).")
        all_passed = False
    else:
        lines.append(f"  Reference Clock FT_CLK: length = {ft_clk:.2f} mm")
        if ft_clk > FT_MAX_TOTAL_MM:
            violations.append(
                f"FT_CLK length = {ft_clk:.2f} mm > {FT_MAX_TOTAL_MM:.1f} mm [SI]"
            )
            all_passed = False

        sync_lengths = [
            get_len(n) for n in FT_ALL_SYNC_NETS if get_len(n) is not None
        ]
        min_len = min(sync_lengths) if sync_lengths else 0.0
        max_len = max(sync_lengths) if sync_lengths else 0.0
        span_mm = max_len - min_len
        lines.append(
            f"  Bus length range: [{min_len:.2f}, {max_len:.2f}] mm (span = {span_mm:.2f} mm)"
        )

        lines.append(
            f"  {'Net':<12} {'Length(mm)':>10} {'SkewCLK':>9} "
            f"{'Rd Su/Hd(ps)':>14} {'Wr Su/Hd(IOReg)':>16} {'WrSu(Fab)':>10} {'Status':>8}"
        )
        lines.append("  " + "-" * 74)

        for net in FT_SYNC_NETS:
            l_mm = get_len(net)
            if l_mm is None:
                violations.append(f"{net} missing/unrouted")
                all_passed = False
                continue

            skew_clk = l_mm - ft_clk
            slacks = calc_ft601_slack_ps(ft_clk, l_mm)

            tot_ok = l_mm <= FT_MAX_TOTAL_MM
            skew_ok = FT_MIN_SKEW_MM <= skew_clk <= FT_MAX_SKEW_MM
            rd_ok = (slacks["rd_setup_ps"] >= 0.0) and (slacks["rd_hold_ps"] >= 0.0)
            wr_ok = (slacks["wr_setup_ps"] >= 0.0) and (slacks["wr_hold_ps"] >= 0.0)

            net_ok = tot_ok and skew_ok and rd_ok and wr_ok
            status = "PASS" if net_ok else "FAIL"
            if not net_ok:
                all_passed = False
                if not tot_ok:
                    violations.append(
                        f"{net} length {l_mm:.2f} mm > {FT_MAX_TOTAL_MM:.1f} mm [SI]"
                    )
                if not skew_ok:
                    violations.append(
                        f"{net} skew to FT_CLK {skew_clk:+.2f} mm outside [{FT_MIN_SKEW_MM:+.1f}, {FT_MAX_SKEW_MM:+.1f}] mm"
                    )
                if not rd_ok:
                    violations.append(
                        f"{net} read slack {slacks['rd_setup_ps']:+.0f}/{slacks['rd_hold_ps']:+.0f} ps < 0 [TIMING]"
                    )
                if not wr_ok:
                    violations.append(
                        f"{net} write slack {slacks['wr_setup_ps']:+.0f}/{slacks['wr_hold_ps']:+.0f} ps < 0 [TIMING]"
                    )

            if verbose or not net_ok:
                lines.append(
                    f"  {net:<12} {l_mm:>10.2f} {skew_clk:>+9.2f} "
                    f"{slacks['rd_setup_ps']:>+6.0f}/{slacks['rd_hold_ps']:>+6.0f} "
                    f"{slacks['wr_setup_ps']:>+7.0f}/{slacks['wr_hold_ps']:>+6.0f} "
                    f"{slacks['wr_setup_fab_ps']:>+10.0f} {status:>8}"
                )

        # Check asynchronous FT601 control/GPIO nets (exempt from FT_CLK skew per Table 3.2)
        for net in FT_ASYNC_NETS:
            val = get_len(net)
            if val is not None:
                async_ok = val <= FT_ASYNC_MAX_MM
                if not async_ok:
                    all_passed = False
                    violations.append(
                        f"{net} (async) length {val:.2f} mm > {FT_ASYNC_MAX_MM:.1f} mm"
                    )
                if verbose or not async_ok:
                    lines.append(
                        f"  {net:<12} {val:>10.2f} {'EXEMPT':>9} "
                        f"{'Async Table3.2':>14} {'Static/Slow':>16} {'-':>10} "
                        f"{'PASS' if async_ok else 'FAIL':>8}"
                    )

    lines.append("")
    lines.append("=" * 78)
    if all_passed:
        lines.append("OVERALL RESULT: PASS (0 violations)")
    else:
        lines.append(f"OVERALL RESULT: FAIL ({len(violations)} violations)")
        for v in violations:
            lines.append(f"  - {v}")
    lines.append("=" * 78)

    return all_passed, lines


# ==============================================================================
# 5. Built-in Self-Test (Target Post-Route Euclidean / Manhattan Estimates)
# ==============================================================================
def build_synthetic_target_lengths():
    """
    Constructs realistic target routed lengths (mm) from our Round-9 R2 ADC plan
    and Round-5 FT601 placement to verify that planned routes pass all constraints.
    """
    synth = {}
    # R2 planned ADC lengths (U8 -> R26..R41 -> U12 Bank 7)
    r2_adc = {
        "ADC_DCO":  (3.35, 24.35),
        "ADC_OR":   (1.50, 27.92),
        "ADC_D0":   (5.05, 30.57),
        "ADC_D1":   (2.00, 25.82),
        "ADC_D2":   (4.00, 26.16),
        "ADC_D3":   (1.65, 23.77),
        "ADC_D4":   (4.05, 20.70),
        "ADC_D5":   (1.10, 25.10),
        "ADC_D6":   (4.00, 20.97),
        "ADC_D7":   (2.10, 20.10),
        "ADC_D8":   (4.30, 19.15),
        "ADC_D9":   (1.95, 25.42),
        "ADC_D10":  (4.90, 18.62),
        "ADC_D11":  (1.60, 25.27),
        "ADC_D12":  (3.45, 27.66),
        "ADC_D13":  (1.30, 32.59),
    }
    for net, (st, mn) in r2_adc.items():
        synth[f"{net}_R"] = st
        synth[net] = mn
    synth["ADC_CSB"] = 33.37
    synth["ADC_SCLK"] = 32.24
    synth["ADC_SDIO"] = 30.03

    # FT601 lengths
    synth["FT_CLK"] = 12.53
    for i in range(32):
        synth[f"FT_D{i}"] = 12.0 + (i % 16) * 0.9
    for i in range(4):
        synth[f"FT_BE{i}"] = 17.5 + i * 0.8
    for idx, ctrl in enumerate(
        ["FT_TXE_N", "FT_RXF_N", "FT_WR_N", "FT_RD_N", "FT_OE_N", "FT_SIWU_N"]
    ):
        synth[ctrl] = 16.0 + idx * 1.2
    synth["FT_RESET_N"] = 28.09
    synth["FT_WAKEUP_N"] = 16.65
    synth["FT_GPIO0"] = 22.87
    synth["FT_GPIO1"] = 26.86

    return synth


def main():
    parser = argparse.ArgumentParser(
        description="Verify ADC (80 MHz) and FT601 (100 MHz) trace lengths and timing slack."
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Path to .kicad_pcb file or routed lengths .json file",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run self-test using synthetic target lengths from R2 ADC plan",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Print all nets (even passing)"
    )
    args = parser.parse_args()

    if args.self_test or not args.input:
        print("Running built-in self-test on target post-route lengths (R2 ADC plan)...")
        lengths = build_synthetic_target_lengths()
        passed, report = check_lengths(lengths, verbose=True)
        print("\n".join(report))
        sys.exit(0 if passed else 1)

    if not os.path.exists(args.input):
        print(f"Error: file not found: {args.input}", file=sys.stderr)
        sys.exit(2)

    if args.input.endswith(".json"):
        lengths = load_lengths_from_json(args.input)
    else:
        lengths = load_lengths_from_kicad_pcb(args.input)

    passed, report = check_lengths(lengths, verbose=args.verbose)
    print("\n".join(report))
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
