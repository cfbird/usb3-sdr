#!/usr/bin/env python3
"""Analyze ddc_out.csv from tb_ddc: tone frequency/level, out-of-band rejection, spurs."""
import sys
import numpy as np
from scipy.signal import windows

FS_OUT = 80e6 / 64
d = np.loadtxt(sys.argv[1] if len(sys.argv) > 1 else "build/ddc_out.csv", delimiter=",")[2000:]
x = (d[:, 0] + 1j * d[:, 1]) / 32768.0
N = len(x)
w = windows.blackmanharris(N)
X = np.fft.fftshift(np.fft.fft(x * w)) / w.sum()
f = np.fft.fftshift(np.fft.fftfreq(N, 1 / FS_OUT))
P = 20 * np.log10(np.abs(X) + 1e-20)

def peak(fc, bw=5e3):
    m = np.abs(f - fc) < bw
    i = np.argmax(np.where(m, P, -400))
    return f[i], P[i]

f1, p1 = peak(100e3)
fa, pa = peak(-350e3)                      # +900 kHz tone aliases to 900k - 1.25M = -350 kHz
expect = 20 * np.log10(0.45 * 8191 / 8192 / 2)  # real->complex halves amplitude
excl = np.abs(f - f1) < 10e3
spur_f, spur_p = f[~excl][np.argmax(P[~excl])], P[~excl].max()
pb = np.abs(f) < 0.5e6
noise = np.median(P[pb & ~excl])
print(f"in-band tone : {f1/1e3:8.2f} kHz  {p1:7.2f} dBFS (expected {expect:.2f})")
print(f"+900k alias  : {fa/1e3:8.2f} kHz  {pa:7.2f} dBFS -> rejection {p1 - pa:.1f} dB")
print(f"worst spur   : {spur_f/1e3:8.2f} kHz  {spur_p:7.2f} dBFS -> SFDR {p1 - spur_p:.1f} dBc")
print(f"median bin floor in passband: {noise:.1f} dBFS (N={N}, BH window)")
