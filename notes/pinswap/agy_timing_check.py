#!/usr/bin/env python3
"""
Bus timing budget & routed trace-length verification script for usb3-sdr.

Checks routed (or estimated) net lengths against the timing and signal-integrity
constraints derived in notes/pinswap/agy_timing.md for:
  1. FT601 245 Synchronous FIFO bus (100 MHz, 3.3 V LVCMOS33, Bank 2/3)
  2. AD9649 CMOS sample bus (80 MSPS, 1.8 V LVCMOS18, Bank 7)

Usage:
  python3 notes/pinswap/agy_timing_check.py [lengths.json] [--tau-f 6.0] [--tau-b 6.75]

Input JSON format (when lengths.json is supplied):
  {"net_name": length_mm, ...}
  Accepts flat KiCad net names ("FT_D0", "ADC_D0", "ADC_D0_R"), hierarchical
  KiCad net names ("/ADC and clock/ADC_D0_R"), or gateware LPF signal names
  ("ft_data[0]", "adc_d[0]"). If pre-resistor stub nets ("ADC_*_R") are present,
  they are checked against the stub limit and added to "ADC_*" to form total
  U8-to-U12 lengths.
"""

import argparse
import json
import math
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Propagation velocity model (JLC04161H-7628 4-layer stackup)
# ---------------------------------------------------------------------------
TAU_FCU_PS_PER_MM = 6.00    # F.Cu microstrip over In1.Cu GND (eps_eff ~ 3.24)
TAU_BCU_PS_PER_MM = 6.75    # B.Cu microstrip + 2-via transition (6.5-7.0 ps/mm)
TAU_MIN_PS_PER_MM = 6.00    # Fast-corner trace propagation delay
TAU_MAX_PS_PER_MM = 7.00    # Slow-corner trace propagation delay

# ---------------------------------------------------------------------------
# Datasheet & ECP5 speed-grade -6 timing parameters (ps)
# ---------------------------------------------------------------------------
# FT601 @ 100 MHz (refs/DS_FT600Q-FT601Q-IC-Datasheet.pdf, p. 17, Table 4.2)
FT_TCLK_PS = 10000.0
FT_T1_SU_SLAVE_PS = 3000.0   # FT601 output valid before posedge CLK (tCO_max = 7.0 ns)
FT_T2_HD_SLAVE_PS = 3500.0   # FT601 output hold after posedge CLK (tCO_min = 3.5 ns)
FT_T3_SU_MASTER_PS = 1000.0  # FT601 input setup required before posedge CLK
FT_T4_HD_MASTER_PS = 4800.0  # FT601 input hold required after posedge CLK

# ECP5 LFE5U-25F-6BG256C speed -6 (prjtrellis speed_6/cells.json)
ECP5_LVCMOS33_IN_MIN_PS = 990.0
ECP5_LVCMOS33_IN_MAX_PS = 1140.0
ECP5_LVCMOS33_OUT_MIN_PS = 1988.0
ECP5_LVCMOS33_OUT_MAX_PS = 2674.0
ECP5_LVCMOS33_TS_MIN_PS = 2203.0
ECP5_LVCMOS33_TS_MAX_PS = 3023.0

ECP5_LVCMOS18_IN_MIN_PS = 1311.0
ECP5_LVCMOS18_IN_MAX_PS = 1469.0

ECP5_IREG_SU_PS = 439.0      # IFS1P3DX setup (DI to posedge CLK)
ECP5_IREG_HD_PS = 311.0      # IFS1P3DX hold (DI to posedge CLK)
ECP5_OREG_CO_PS = 1200.0     # OFS1P3DX clock-to-out (CLK to IOLDO)
ECP5_TSREG_CO_PS = 1031.0    # OFS1P3DX tristate clock-to-out (CLK to IOLTO)

# ECP5 global clock tree insertion delay (PADDI to IOLOGIC CLK, uncompensated)
ECP5_GCLK_MIN_PS = 1200.0
ECP5_GCLK_MAX_PS = 1800.0

# Implemented EHXPLLL single-clock phase shift (+112.5 deg = +3.125 ns at 100 MHz, 600 MHz VCO)
# with CLKOP (0 deg) feedback compensation and PVT fast-corner factor 0.70
FT_PLL_SHIFT_PS = 3125.0
PVT_FAST_FACTOR = 0.70

# AD9649-80 @ 80 MSPS (refs/datasheets/AD9649_RevB.pdf, p. 7, Table 4 & Fig. 2)
ADC_TCLK_PS = 12500.0
ADC_TPD_TYP_PS = 3000.0
ADC_TDCO_TYP_PS = 3000.0
ADC_TSKEW_MIN_PS = -100.0    # tDCO - tPD min (typ +100 ps in Table 4)
ADC_TSKEW_TYP_PS = 100.0     # tDCO - tPD typ (0.1 ns, Table 4)
ADC_TSKEW_MAX_PS = 300.0     # tDCO - tPD max
ADC_RC_SLOPE_PS_PER_MM = 3.7 # Extra RC delay per mm from 22+35 ohm driving 0.094 pF/mm

# ---------------------------------------------------------------------------
# Routing constraint thresholds (mm)
# ---------------------------------------------------------------------------
FT_MAX_ABS_LEN_MM = 35.0     # SI unterminated limit (~38 mm) & well below 85 mm timing max
FT_MAX_SKEW_MM = 15.0        # |L(FT_sig) - L(FT_CLK)| <= 15.0 mm (+/- 105 ps)

ADC_MAX_ABS_LEN_MM = 50.0    # Keeps total load C_trace + C_pin < 10 pF (AD9649 p. 17)
ADC_MAX_SKEW_MM = 20.0       # |L(ADC_sig) - L(ADC_DCO)| <= 20.0 mm
ADC_MAX_STUB_LEN_MM = 6.0    # U8 pin to 22-ohm series resistor pad 1 stub limit


# ---------------------------------------------------------------------------
# Canonical net lists
# ---------------------------------------------------------------------------
FT_SYNC_INPUTS = [
    "FT_TXE_N",
    "FT_RXF_N",
]
FT_SYNC_BIDIR = (
    [f"FT_D{i}" for i in range(32)]
    + [f"FT_BE{i}" for i in range(4)]
)
FT_SYNC_OUTPUTS = [
    "FT_WR_N",
    "FT_RD_N",
    "FT_OE_N",
]
FT_SYNC_NETS = ["FT_CLK"] + FT_SYNC_INPUTS + FT_SYNC_BIDIR + FT_SYNC_OUTPUTS
FT_ASYNC_NETS = ["FT_RESET_N", "FT_WAKEUP_N", "FT_GPIO0", "FT_GPIO1"]

ADC_SYNC_SIGNALS = [f"ADC_D{i}" for i in range(14)] + ["ADC_OR"]
ADC_SYNC_NETS = ["ADC_DCO"] + ADC_SYNC_SIGNALS
ADC_SPI_NETS = ["ADC_CSB", "ADC_SCLK", "ADC_SDIO"]


def canonicalize_net_name(raw_name):
    """Normalize KiCad flat/hierarchical or gateware signal name to canonical net name."""
    name = raw_name.strip()
    if "/" in name:
        name = name.split("/")[-1]
    low = name.lower()
    if low.startswith("ft_data[") and low.endswith("]"):
        return f"FT_D{low[8:-1]}"
    if low.startswith("ft_data") and low[7:].isdigit():
        return f"FT_D{low[7:]}"
    if low.startswith("ft_be[") and low.endswith("]"):
        return f"FT_BE{low[6:-1]}"
    if low == "ft_siwu_n":
        return "FT_WAKEUP_N"
    if low.startswith("ft_"):
        return low.upper()
    if low.startswith("adc_d[") and low.endswith("]"):
        return f"ADC_D{low[6:-1]}"
    if low.startswith("adc_data[") and low.endswith("]"):
        return f"ADC_D{low[9:-1]}"
    if low.startswith("adc_"):
        return low.upper()
    return name


def normalize_lengths_dict(raw_dict):
    """
    Return (total_lengths, stub_lengths, post_res_lengths) keyed by canonical net name.
    If both 'ADC_X' and 'ADC_X_R' are present in raw_dict, total_lengths['ADC_X'] =
    raw['ADC_X'] + raw['ADC_X_R'].
    """
    norm = {}
    for k, v in raw_dict.items():
        if isinstance(v, (int, float)):
            ck = canonicalize_net_name(k)
            norm[ck] = float(v)

    stub_lengths = {}
    post_res_lengths = {}
    total_lengths = dict(norm)

    for net in ADC_SYNC_NETS:
        stub_key = f"{net}_R"
        if stub_key in norm:
            stub_lengths[net] = norm[stub_key]
            if net in norm:
                post_res_lengths[net] = norm[net]
                total_lengths[net] = norm[net] + norm[stub_key]

    return total_lengths, stub_lengths, post_res_lengths


def evaluate_ft601_timing(lengths):
    """
    Evaluate FT601 100 MHz 245-mode timing and length constraints.
    Returns (passed, results_list, summary_dict).
    """
    results = []
    all_pass = True

    if "FT_CLK" not in lengths:
        return False, [("FT_CLK_PRESENT", False, "FT_CLK missing from input JSON")], {}

    l_clk = lengths["FT_CLK"]
    t_clk_min = l_clk * TAU_MIN_PS_PER_MM
    t_clk_max = l_clk * TAU_MAX_PS_PER_MM

    min_read_su_slack_ps = float("inf")
    min_read_hd_slack_ps = float("inf")
    min_write_su_slack_ps = float("inf")
    min_write_hd_slack_ps = float("inf")
    max_abs_len = 0.0
    max_abs_net = ""
    max_skew_abs = 0.0
    max_skew_net = ""

    per_net = {}

    for net in FT_SYNC_NETS:
        if net not in lengths:
            all_pass = False
            results.append((f"{net}_PRESENT", False, f"Missing synchronous FT601 net {net}"))
            continue

        l_net = lengths[net]
        skew_mm = l_net - l_clk
        t_net_min = l_net * TAU_MIN_PS_PER_MM
        t_net_max = l_net * TAU_MAX_PS_PER_MM

        if l_net > max_abs_len:
            max_abs_len = l_net
            max_abs_net = net
        if abs(skew_mm) > abs(max_skew_abs):
            max_skew_abs = skew_mm
            max_skew_net = net

        is_input = net in FT_SYNC_INPUTS or net in FT_SYNC_BIDIR
        is_output = net in FT_SYNC_OUTPUTS or net in FT_SYNC_BIDIR

        # 1. Input (Read / status capture in IFS1P3DX, clocked by +112.5 deg = +3125 ps EHXPLLL CLKOS)
        #   t_clk_IOL = t_clk_pcb + FT_PLL_SHIFT_PS
        #   t_data_max = -T1 + t_net_max + t_IN_PIO_max
        #   t_data_min = +T2 + t_net_min + PVT_FAST_FACTOR * t_IN_PIO_min
        if is_input:
            rd_su_slack = (
                (t_clk_min + FT_PLL_SHIFT_PS)
                - (-FT_T1_SU_SLAVE_PS + t_net_max + ECP5_LVCMOS33_IN_MAX_PS)
                - ECP5_IREG_SU_PS
            )
            rd_hd_slack = (
                (FT_T2_HD_SLAVE_PS + t_net_min + PVT_FAST_FACTOR * ECP5_LVCMOS33_IN_MIN_PS)
                - (t_clk_max + FT_PLL_SHIFT_PS)
                - ECP5_IREG_HD_PS
            )
            min_read_su_slack_ps = min(min_read_su_slack_ps, rd_su_slack)
            min_read_hd_slack_ps = min(min_read_hd_slack_ps, rd_hd_slack)
        else:
            rd_su_slack = None
            rd_hd_slack = None

        # 2. Output (Write / control launch from OFS1P3DX/OFS1P3BX with +112.5 deg = +3125 ps EHXPLLL CLKOS)
        # Round-trip delay adds: t_arrive_U11 = t_clk + t_PLL + t_CO_FPGA + t_net
        if is_output:
            t_co_max = max(
                ECP5_OREG_CO_PS + ECP5_LVCMOS33_OUT_MAX_PS,
                ECP5_TSREG_CO_PS + ECP5_LVCMOS33_TS_MAX_PS,
            )
            t_co_min = PVT_FAST_FACTOR * (ECP5_OREG_CO_PS + ECP5_LVCMOS33_OUT_MIN_PS)
            wr_su_slack = (
                (FT_TCLK_PS - FT_T3_SU_MASTER_PS)
                - (t_clk_max + FT_PLL_SHIFT_PS + t_co_max + t_net_max)
            )
            wr_hd_slack = (
                (t_clk_min + FT_PLL_SHIFT_PS + t_co_min + t_net_min)
                - FT_T4_HD_MASTER_PS
            )
            min_write_su_slack_ps = min(min_write_su_slack_ps, wr_su_slack)
            min_write_hd_slack_ps = min(min_write_hd_slack_ps, wr_hd_slack)
        else:
            wr_su_slack = None
            wr_hd_slack = None

        len_ok = l_net <= FT_MAX_ABS_LEN_MM
        skew_ok = abs(skew_mm) <= FT_MAX_SKEW_MM
        rd_ok = True if not is_input else (rd_su_slack >= 0 and rd_hd_slack >= 0)
        wr_ok = True if not is_output else (wr_su_slack >= 0 and wr_hd_slack >= 0)
        net_ok = len_ok and skew_ok and rd_ok and wr_ok
        if not net_ok:
            all_pass = False

        per_net[net] = {
            "length_mm": l_net,
            "skew_mm": skew_mm,
            "len_ok": len_ok,
            "skew_ok": skew_ok,
            "rd_su_slack_ps": rd_su_slack,
            "rd_hd_slack_ps": rd_hd_slack,
            "wr_su_slack_ps": wr_su_slack,
            "wr_hd_slack_ps": wr_hd_slack,
            "pass": net_ok,
        }

    c_len = max_abs_len <= FT_MAX_ABS_LEN_MM
    c_skew = abs(max_skew_abs) <= FT_MAX_SKEW_MM
    c_rd_su = min_read_su_slack_ps >= 0
    c_rd_hd = min_read_hd_slack_ps >= 0
    c_wr_su = min_write_su_slack_ps >= 0
    c_wr_hd = min_write_hd_slack_ps >= 0

    results.extend([
        (
            "FT601_MAX_ABS_LEN",
            c_len,
            f"max={max_abs_len:.2f} mm ({max_abs_net}) <= {FT_MAX_ABS_LEN_MM:.1f} mm "
            f"(slack {FT_MAX_ABS_LEN_MM - max_abs_len:+.2f} mm)",
        ),
        (
            "FT601_CLK_SKEW",
            c_skew,
            f"max |L - L(FT_CLK)|={abs(max_skew_abs):.2f} mm ({max_skew_net}, {max_skew_abs:+.2f} mm) "
            f"<= {FT_MAX_SKEW_MM:.1f} mm (slack {FT_MAX_SKEW_MM - abs(max_skew_abs):+.2f} mm)",
        ),
        (
            "FT601_READ_SETUP",
            c_rd_su,
            f"worst read setup slack = {min_read_su_slack_ps:+.0f} ps (>= 0 ps)",
        ),
        (
            "FT601_READ_HOLD",
            c_rd_hd,
            f"worst read hold slack  = {min_read_hd_slack_ps:+.0f} ps (>= 0 ps)",
        ),
        (
            "FT601_WRITE_SETUP",
            c_wr_su,
            f"worst write setup slack = {min_write_su_slack_ps:+.0f} ps (>= 0 ps, IOREG + 112.5 deg PLL)",
        ),
        (
            "FT601_WRITE_HOLD",
            c_wr_hd,
            f"worst write hold slack  = {min_write_hd_slack_ps:+.0f} ps (>= 0 ps vs T4=4800 ps, IOREG + 112.5 deg PLL)",
        ),
    ])

    summary = {
        "ft_clk_mm": l_clk,
        "max_abs_len_mm": max_abs_len,
        "max_abs_net": max_abs_net,
        "max_skew_mm": max_skew_abs,
        "max_skew_net": max_skew_net,
        "min_read_su_slack_ps": min_read_su_slack_ps,
        "min_read_hd_slack_ps": min_read_hd_slack_ps,
        "min_write_su_slack_ps": min_write_su_slack_ps,
        "min_write_hd_slack_ps": min_write_hd_slack_ps,
        "per_net": per_net,
    }
    return all_pass, results, summary


def evaluate_adc_timing(lengths, stub_lengths):
    """
    Evaluate AD9649 80 MSPS CMOS bus timing and length constraints.
    Reports both default DCO polarity (0x16=0x00, edge-aligned + GCLK insertion)
    and inverted DCO polarity (0x16=0x80, center-aligned).
    """
    results = []
    all_pass = True

    if "ADC_DCO" not in lengths:
        return False, [("ADC_DCO_PRESENT", False, "ADC_DCO missing from input JSON")], {}

    l_dco = lengths["ADC_DCO"]
    t_dco_min = l_dco * TAU_MIN_PS_PER_MM
    t_dco_max = l_dco * TAU_MAX_PS_PER_MM

    max_abs_len = 0.0
    max_abs_net = ""
    max_skew_abs = 0.0
    max_skew_net = ""
    max_stub_len = 0.0
    max_stub_net = ""

    min_su_default_ps = float("inf")
    min_hd_default_ps = float("inf")
    min_su_inv_ps = float("inf")
    min_hd_inv_ps = float("inf")

    per_net = {}

    for net in ADC_SYNC_NETS:
        if net not in lengths:
            all_pass = False
            results.append((f"{net}_PRESENT", False, f"Missing synchronous ADC net {net}"))
            continue

        l_net = lengths[net]
        skew_mm = l_net - l_dco
        t_net_min = l_net * TAU_MIN_PS_PER_MM
        t_net_max = l_net * TAU_MAX_PS_PER_MM
        rc_diff_ps = skew_mm * ADC_RC_SLOPE_PS_PER_MM

        if l_net > max_abs_len:
            max_abs_len = l_net
            max_abs_net = net
        if net != "ADC_DCO" and abs(skew_mm) > abs(max_skew_abs):
            max_skew_abs = skew_mm
            max_skew_net = net

        stub_mm = stub_lengths.get(net)
        if stub_mm is not None and stub_mm > max_stub_len:
            max_stub_len = stub_mm
            max_stub_net = f"{net}_R"

        # Default DCO polarity (0x16 = 0x00): DCO edge-aligned at ADC (tSKEW = -100..+300 ps),
        # delayed inside ECP5 by global clock tree t_GCLK (1200..1800 ps).
        su_def = (
            ADC_TSKEW_MIN_PS
            + ECP5_GCLK_MIN_PS
            + (t_dco_min - t_net_max)
            - max(0.0, rc_diff_ps)
            - (ECP5_LVCMOS18_IN_MAX_PS - ECP5_LVCMOS18_IN_MIN_PS)
            - ECP5_IREG_SU_PS
        )
        hd_def = (
            ADC_TCLK_PS
            - ADC_TSKEW_MAX_PS
            - ECP5_GCLK_MAX_PS
            - (t_dco_max - t_net_min)
            - max(0.0, -rc_diff_ps)
            - (ECP5_LVCMOS18_IN_MAX_PS - ECP5_LVCMOS18_IN_MIN_PS)
            - ECP5_IREG_HD_PS
        )

        # Inverted DCO polarity (0x16 = 0x80) or negedge capture: centers DCO at T_CLK/2 = 6250 ps
        su_inv = (
            0.5 * ADC_TCLK_PS
            + ADC_TSKEW_MIN_PS
            + (t_dco_min - t_net_max)
            - max(0.0, rc_diff_ps)
            - (ECP5_LVCMOS18_IN_MAX_PS - ECP5_LVCMOS18_IN_MIN_PS)
            - ECP5_IREG_SU_PS
        )
        hd_inv = (
            0.5 * ADC_TCLK_PS
            - ADC_TSKEW_MAX_PS
            - ECP5_GCLK_MAX_PS
            - (t_dco_max - t_net_min)
            - max(0.0, -rc_diff_ps)
            - (ECP5_LVCMOS18_IN_MAX_PS - ECP5_LVCMOS18_IN_MIN_PS)
            - ECP5_IREG_HD_PS
        )

        if net != "ADC_DCO":
            min_su_default_ps = min(min_su_default_ps, su_def)
            min_hd_default_ps = min(min_hd_default_ps, hd_def)
            min_su_inv_ps = min(min_su_inv_ps, su_inv)
            min_hd_inv_ps = min(min_hd_inv_ps, hd_inv)

        len_ok = l_net <= ADC_MAX_ABS_LEN_MM
        skew_ok = abs(skew_mm) <= ADC_MAX_SKEW_MM
        stub_ok = True if stub_mm is None else (stub_mm <= ADC_MAX_STUB_LEN_MM)
        timing_ok = su_def >= 0 and hd_def >= 0
        net_ok = len_ok and skew_ok and stub_ok and timing_ok
        if not net_ok:
            all_pass = False

        per_net[net] = {
            "length_mm": l_net,
            "stub_mm": stub_mm,
            "skew_mm": skew_mm,
            "len_ok": len_ok,
            "skew_ok": skew_ok,
            "stub_ok": stub_ok,
            "su_default_ps": su_def,
            "hd_default_ps": hd_def,
            "su_inv_ps": su_inv,
            "hd_inv_ps": hd_inv,
            "pass": net_ok,
        }

    c_len = max_abs_len <= ADC_MAX_ABS_LEN_MM
    c_skew = abs(max_skew_abs) <= ADC_MAX_SKEW_MM
    c_su_def = min_su_default_ps >= 0
    c_hd_def = min_hd_default_ps >= 0
    c_su_inv = min_su_inv_ps >= 0
    c_hd_inv = min_hd_inv_ps >= 0

    results.extend([
        (
            "ADC_MAX_ABS_LEN",
            c_len,
            f"max={max_abs_len:.2f} mm ({max_abs_net}) <= {ADC_MAX_ABS_LEN_MM:.1f} mm "
            f"(slack {ADC_MAX_ABS_LEN_MM - max_abs_len:+.2f} mm)",
        ),
        (
            "ADC_DCO_SKEW",
            c_skew,
            f"max |L - L(ADC_DCO)|={abs(max_skew_abs):.2f} mm ({max_skew_net}, {max_skew_abs:+.2f} mm) "
            f"<= {ADC_MAX_SKEW_MM:.1f} mm (slack {ADC_MAX_SKEW_MM - abs(max_skew_abs):+.2f} mm)",
        ),
        (
            "ADC_SETUP_DEFAULT_0x16_00",
            c_su_def,
            f"worst setup slack (default DCO 0x16=0x00) = {min_su_default_ps:+.0f} ps (>= 0 ps)",
        ),
        (
            "ADC_HOLD_DEFAULT_0x16_00",
            c_hd_def,
            f"worst hold slack  (default DCO 0x16=0x00) = {min_hd_default_ps:+.0f} ps (>= 0 ps)",
        ),
        (
            "ADC_SETUP_INVDCO_0x16_80",
            c_su_inv,
            f"worst setup slack (inverted DCO 0x16=0x80) = {min_su_inv_ps:+.0f} ps (>= 0 ps)",
        ),
        (
            "ADC_HOLD_INVDCO_0x16_80",
            c_hd_inv,
            f"worst hold slack  (inverted DCO 0x16=0x80) = {min_hd_inv_ps:+.0f} ps (>= 0 ps)",
        ),
    ])

    if stub_lengths:
        c_stub = max_stub_len <= ADC_MAX_STUB_LEN_MM
        if not c_stub:
            all_pass = False
        results.append((
            "ADC_SERIES_RES_STUB",
            c_stub,
            f"max U8->R stub={max_stub_len:.2f} mm ({max_stub_net}) <= {ADC_MAX_STUB_LEN_MM:.1f} mm "
            f"(slack {ADC_MAX_STUB_LEN_MM - max_stub_len:+.2f} mm)",
        ))

    summary = {
        "adc_dco_mm": l_dco,
        "max_abs_len_mm": max_abs_len,
        "max_abs_net": max_abs_net,
        "max_skew_mm": max_skew_abs,
        "max_skew_net": max_skew_net,
        "max_stub_len_mm": max_stub_len if stub_lengths else None,
        "max_stub_net": max_stub_net if stub_lengths else None,
        "min_su_default_ps": min_su_default_ps,
        "min_hd_default_ps": min_hd_default_ps,
        "min_su_inv_ps": min_su_inv_ps,
        "min_hd_inv_ps": min_hd_inv_ps,
        "per_net": per_net,
    }
    return all_pass, results, summary


def build_estimated_lengths_from_repo(repo_root, relocate_adc_resistors=True):
    """
    Build estimated routed lengths (Manhattan with 45-deg / 1.12x Euclidean blend)
    from notes/pinswap/data.json and notes/pinswap/agy_assignment.json for self-test.
    """
    with open(repo_root / "notes" / "pinswap" / "data.json") as f:
        data = json.load(f)
    with open(repo_root / "notes" / "pinswap" / "agy_assignment.json") as f:
        asgn = json.load(f)

    fpga_xy = {b: tuple(v["xy"]) for b, v in data["fpga_balls"].items()}
    ft_xy = {
        info["net"]: tuple(info["xy"])
        for info in data["ft601_pins"].values()
        if info["net"].startswith("FT_")
    }
    adc_pin_xy = {
        info["net"].split("/")[-1]: tuple(info["xy"])
        for info in data["adc_pins"].values()
        if info["net"]
    }
    res_info = {
        rinfo["2"]["net"]: (tuple(rinfo["1"]["xy"]), tuple(rinfo["2"]["xy"]))
        for rinfo in data["adc_series_resistors"].values()
    }

    est = {}
    for sig, ball in asgn.items():
        net = canonicalize_net_name(sig)
        p_fpga = fpga_xy[ball]
        if net in ft_xy:
            p_ft = ft_xy[net]
            dx = abs(p_fpga[0] - p_ft[0])
            dy = abs(p_fpga[1] - p_ft[1])
            # Octilinear (45-degree) routed distance + 1.5 mm escape overhead
            oct_len = max(dx, dy) + (math.sqrt(2) - 1.0) * min(dx, dy) + 1.5
            est[net] = round(oct_len, 2)
        elif net in ADC_SYNC_NETS and f"{net}_R" in adc_pin_xy:
            p_u8 = adc_pin_xy[f"{net}_R"]
            if relocate_adc_resistors:
                # Resistor placed 2.2 mm from U8 pin toward FPGA
                stub = 2.20
                dx = abs(p_fpga[0] - p_u8[0])
                dy = abs(p_fpga[1] - p_u8[1])
                oct_total = max(dx, dy) + (math.sqrt(2) - 1.0) * min(dx, dy) + 2.0
                est[f"{net}_R"] = round(stub, 2)
                est[net] = round(oct_total - stub, 2)
            else:
                p1, p2 = res_info[net]
                dx1, dy1 = abs(p1[0] - p_u8[0]), abs(p1[1] - p_u8[1])
                dx2, dy2 = abs(p_fpga[0] - p2[0]), abs(p_fpga[1] - p2[1])
                stub = max(dx1, dy1) + (math.sqrt(2) - 1.0) * min(dx1, dy1)
                main = max(dx2, dy2) + (math.sqrt(2) - 1.0) * min(dx2, dy2)
                est[f"{net}_R"] = round(stub, 2)
                est[net] = round(main, 2)
    return est


def print_report(title, raw_dict, verbose=False):
    total_lengths, stub_lengths, _ = normalize_lengths_dict(raw_dict)

    has_ft = any(k in total_lengths for k in FT_SYNC_NETS)
    has_adc = any(k in total_lengths for k in ADC_SYNC_NETS)

    print("=" * 78)
    print(f"USB3-SDR BUS TIMING & LENGTH CHECK: {title}")
    print("=" * 78)

    overall_pass = True

    if has_ft:
        ft_ok, ft_res, ft_sum = evaluate_ft601_timing(total_lengths)
        overall_pass = overall_pass and ft_ok
        print("\n[1] FT601 245 Synchronous FIFO Bus (100 MHz, 3.3 V LVCMOS33)")
        print("-" * 78)
        for cname, ok, msg in ft_res:
            status = "PASS" if ok else "FAIL"
            print(f"  [{status}] {cname:26s}: {msg}")
        if verbose and "per_net" in ft_sum:
            print("\n  Per-net FT601 summary (sorted by length):")
            for net, info in sorted(ft_sum["per_net"].items(), key=lambda x: x[1]["length_mm"]):
                st = "PASS" if info["pass"] else "FAIL"
                w_su = f"{info['wr_su_slack_ps']:+6.0f}ps" if info["wr_su_slack_ps"] is not None else "   n/a"
                w_hd = f"{info['wr_hd_slack_ps']:+6.0f}ps" if info["wr_hd_slack_ps"] is not None else "   n/a"
                r_su = f"{info['rd_su_slack_ps']:+6.0f}ps" if info["rd_su_slack_ps"] is not None else "   n/a"
                r_hd = f"{info['rd_hd_slack_ps']:+6.0f}ps" if info["rd_hd_slack_ps"] is not None else "   n/a"
                print(
                    f"    {st} {net:12s}: L={info['length_mm']:5.2f} mm, "
                    f"dL={info['skew_mm']:+6.2f} mm | Rd(SU/HD)={r_su}/{r_hd} | Wr(SU/HD)={w_su}/{w_hd}"
                )

    if has_adc:
        adc_ok, adc_res, adc_sum = evaluate_adc_timing(total_lengths, stub_lengths)
        overall_pass = overall_pass and adc_ok
        print("\n[2] AD9649 CMOS Sample Bus (80 MSPS, 1.8 V LVCMOS18)")
        print("-" * 78)
        for cname, ok, msg in adc_res:
            status = "PASS" if ok else "FAIL"
            print(f"  [{status}] {cname:26s}: {msg}")
        if verbose and "per_net" in adc_sum:
            print("\n  Per-net AD9649 summary (sorted by length):")
            for net, info in sorted(adc_sum["per_net"].items(), key=lambda x: x[1]["length_mm"]):
                st = "PASS" if info["pass"] else "FAIL"
                stub_str = f", stub={info['stub_mm']:4.2f}mm" if info["stub_mm"] is not None else ""
                print(
                    f"    {st} {net:10s}: L={info['length_mm']:5.2f} mm{stub_str}, "
                    f"dL={info['skew_mm']:+6.2f} mm | "
                    f"Def(SU/HD)={info['su_default_ps']:+5.0f}/{info['hd_default_ps']:+6.0f}ps | "
                    f"Inv(SU/HD)={info['su_inv_ps']:+5.0f}/{info['hd_inv_ps']:+5.0f}ps"
                )

    if not has_ft and not has_adc:
        print("  [FAIL] Input JSON contains neither FT601 nor AD9649 synchronous bus nets.")
        overall_pass = False

    print("\n" + "=" * 78)
    print(f"OVERALL RESULT: {'PASS' if overall_pass else 'FAIL'}")
    print("=" * 78)
    return overall_pass


def main():
    parser = argparse.ArgumentParser(description="Check FT601 and AD9649 routed net lengths against timing budgets.")
    parser.add_argument("json_file", nargs="?", help="Path to JSON file mapping net -> routed length in mm")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print per-net timing table")
    parser.add_argument("--tau-f", type=float, default=6.00, help="Fast / F.Cu delay in ps/mm (default: 6.0)")
    parser.add_argument("--tau-b", type=float, default=7.00, help="Slow / B.Cu delay in ps/mm (default: 7.0)")
    args = parser.parse_args()

    global TAU_MIN_PS_PER_MM, TAU_MAX_PS_PER_MM
    TAU_MIN_PS_PER_MM = min(args.tau_f, args.tau_b)
    TAU_MAX_PS_PER_MM = max(args.tau_f, args.tau_b)

    if args.json_file:
        with open(args.json_file) as f:
            raw_dict = json.load(f)
        ok = print_report(args.json_file, raw_dict, verbose=args.verbose)
        sys.exit(0 if ok else 1)

    # Self-test mode using repo geometry when invoked without a JSON file
    repo_root = Path(__file__).resolve().parents[2]
    est_relocated = build_estimated_lengths_from_repo(repo_root, relocate_adc_resistors=True)
    ok = print_report(
        "Self-test (octilinear lengths from agy_assignment.json + relocated R26..R41)",
        est_relocated,
        verbose=True,
    )
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
