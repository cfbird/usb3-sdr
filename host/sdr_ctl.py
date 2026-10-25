#!/usr/bin/env python3
"""Minimal host-side control/capture for the usb3-sdr gateware (UNTESTED: no hardware yet).

Uses FTDI's D3XX Python wrapper (pip package 'ftd3xx', needs libftd3xx installed).
245 mode: OUT pipe 0x02 (host -> FPGA), IN pipe 0x82 (FPGA -> host).
Register protocol is documented at the top of gateware/rtl/top.v.
"""
import argparse
import struct
import numpy as np

FS = 80e6
REG_CTRL, REG_NCO_LO, REG_NCO_HI, REG_COMMIT, REG_RF, REG_STATUS_REQ = range(6)


class Sdr:
    def __init__(self):
        import ftd3xx  # imported lazily so --help works without the driver
        self.dev = ftd3xx.create(0, ftd3xx.defines.FT_OPEN_BY_INDEX)
        if self.dev is None:
            raise SystemExit("no FT60x device found")

    def wr(self, addr, data):
        word = (0xC0 << 24) | ((addr & 0xFF) << 16) | (data & 0xFFFF)
        self.dev.writePipe(0x02, struct.pack("<I", word), 4)

    def configure(self, freq_hz, raw=False, stream=True):
        inc = int(round(freq_hz / FS * 2**32)) & 0xFFFFFFFF
        self.wr(REG_NCO_LO, inc & 0xFFFF)
        self.wr(REG_NCO_HI, inc >> 16)
        self.wr(REG_CTRL, (1 if stream else 0) | (2 if raw else 0))
        self.wr(REG_COMMIT, 0)

    def status(self):
        self.wr(REG_CTRL, 0); self.wr(REG_COMMIT, 0)       # streaming off, then ask
        self.wr(REG_STATUS_REQ, 0)
        w, = struct.unpack("<I", self.dev.readPipeEx(0x82, 4)["bytes"][:4])
        if w >> 24 != 0x5A:
            raise RuntimeError(f"bad status word {w:08x}")
        return dict(streaming=w & 1, overflow=(w >> 1) & 1, boot_done=(w >> 2) & 1, i2c_nack=(w >> 3) & 1, ft_order_err=(w >> 4) & 1)

    def read_iq(self, n):
        raw = self.dev.readPipeEx(0x82, 4 * n)["bytes"]
        a = np.frombuffer(raw, dtype="<i2").reshape(-1, 2)
        return (a[:, 0] + 1j * a[:, 1]) / 32768.0      # word = {Q, I}: I in the low half


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--freq", type=float, default=7.1e6, help="DDC centre frequency, Hz")
    ap.add_argument("--n", type=int, default=1 << 16, help="IQ samples to capture (1.25 MSPS)")
    ap.add_argument("--out", default="capture.npy")
    a = ap.parse_args()
    sdr = Sdr()
    print("status:", sdr.status())
    sdr.configure(a.freq)
    np.save(a.out, sdr.read_iq(a.n))
    print(f"saved {a.n} IQ samples @ 1.25 MSPS centred on {a.freq/1e6:.4f} MHz to {a.out}")
