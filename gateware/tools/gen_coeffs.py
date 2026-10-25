#!/usr/bin/env python3
"""Generate ROM/coefficient hex files for the DDC.

Chain: 80 MSPS -> NCO/mixer -> CIC5 /16 -> 5 MSPS -> HB /2 -> 2.5 MSPS -> CFIR /2 -> 1.25 MSPS
Usable output passband: +/-0.5 MHz (80 % of the 0.625 MHz output Nyquist).

Writes to ../build/: nco_quarter.hex, hb.hex, cfir.hex, and prints the quantized responses.
"""
import os
import numpy as np
from scipy import signal

OUT = os.path.join(os.path.dirname(__file__), "..", "build")
os.makedirs(OUT, exist_ok=True)

FS = 80e6
CIC_N, CIC_R = 5, 16
F_CIC = FS / CIC_R          # 5 MSPS
F_HB = F_CIC / 2            # 2.5 MSPS
F_OUT = F_HB / 2            # 1.25 MSPS
F_PASS = 0.5e6
COEF_BITS = 18              # signed, Q1.17: DC gain 1.0 == 2**17
HB_TAPS = 23
CFIR_TAPS = 59              # 64 clocks per CFIR output at 80 MHz; MAC needs NTAPS + 3


def write_hex(name, vals, bits):
    mask = (1 << bits) - 1
    with open(os.path.join(OUT, name), "w") as f:
        for v in vals:
            f.write(f"{int(v) & mask:0{(bits + 3) // 4}x}\n")


def quant(h, bits=COEF_BITS):
    return np.round(h * 2 ** (bits - 1)).astype(int)


def resp_db(h, f, fs):
    _, H = signal.freqz(h, worN=f, fs=fs)
    return 20 * np.log10(np.maximum(np.abs(H), 1e-12))


# --- NCO: quarter-wave sine, 4096 entries x 18 bit, half-sample offset so the mirror is exact.
# 14-bit effective phase -> phase-truncation spurs near -84 dBc.
k = np.arange(4096)
quarter = np.round(np.sin(2 * np.pi * (k + 0.5) / 16384) * (2 ** 17 - 1)).astype(int)
write_hex("nco_quarter.hex", quarter, 18)

# --- Halfband 5 -> 2.5 MSPS. Aliases into the final passband come from >= 2.5 - 0.5 = 2.0 MHz.
hb = signal.remez(HB_TAPS, [0, F_PASS, F_HB - F_PASS, F_CIC / 2], [1, 0], fs=F_CIC)
hb = hb / hb.sum()
hb_q = quant(hb)

# --- CFIR 2.5 -> 1.25 MSPS: flat passband after compensating CIC droop + HB, stopband >= 0.75 MHz.
def cic_mag(f):
    x = np.pi * f / FS
    with np.errstate(invalid="ignore", divide="ignore"):
        m = np.abs(np.sin(CIC_R * x) / (CIC_R * np.sin(x))) ** CIC_N
    return np.where(f == 0, 1.0, m)

fpb = np.linspace(0, F_PASS, 64)
comp = 1 / (cic_mag(fpb) * np.abs(signal.freqz(hb_q / 2 ** 17, worN=fpb, fs=F_CIC)[1]))
bands, desired, weight = [], [], []
for a, b, ca, cb in zip(fpb[:-1], fpb[1:], comp[:-1], comp[1:]):
    bands += [a, b]; desired += [ca, cb]; weight.append(1.0)
bands += [F_OUT - F_PASS, F_HB / 2]; desired += [0, 0]; weight.append(30.0)
cfir = signal.firls(CFIR_TAPS, bands, desired, weight=np.repeat(weight, 1), fs=F_HB)
cfir = cfir / cfir.sum()
cfir_q = quant(cfir)

write_hex("hb.hex", hb_q, COEF_BITS)
write_hex("cfir.hex", cfir_q, COEF_BITS)

# --- Report quantized end-to-end response (CIC * HB * CFIR) in the output passband and alias bands.
f_chk = np.array([0, 0.1e6, 0.25e6, 0.4e6, 0.5e6])
tot_pb = 20 * np.log10(cic_mag(f_chk)) + resp_db(hb_q / 2**17, f_chk, F_CIC) + resp_db(cfir_q / 2**17, f_chk, F_HB)
print("passband dB  :", dict(zip((f_chk / 1e6).round(2), tot_pb.round(3))))
print("passband ripple (0-0.5 MHz): %.3f dB" % (tot_pb.max() - tot_pb.min()))
fs_hb = np.linspace(F_HB - F_PASS, F_CIC / 2, 400)
print("HB stopband worst (2.0-2.5 MHz): %.1f dB" % resp_db(hb_q / 2**17, fs_hb, F_CIC).max())
fs_cf = np.linspace(F_OUT - F_PASS, F_HB / 2, 400)
print("CFIR stopband worst (0.75-1.25 MHz): %.1f dB" % resp_db(cfir_q / 2**17, fs_cf, F_HB).max())
print("taps: HB %d, CFIR %d; coef max |%d| (limit %d)" % (HB_TAPS, CFIR_TAPS, max(abs(hb_q).max(), abs(cfir_q).max()), 2**17 - 1))
