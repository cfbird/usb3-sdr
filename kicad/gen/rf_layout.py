"""Scripted placement and locked routes for the critical paths: the RF chain (SMA -> ADC inputs) and the USB 3
SuperSpeed pairs. Coordinates are board-relative mm (origin top-left), derived from the footprint pad geometry
(see notes in each block). Everything else is left for the autorouter (DeepPCB).

RF serpentine: row A (y=13, L->R) SMA, GDT, clamp, K1 + 20 dB pad, LPF1, FM notch; row B (y=30, R->L) K2 + LNA loop,
LPF2; row C (y=41, L->R) ADT4-6T+, 200R termination, 33R, ADC. Series parts sit in line, shunt parts drop to a via.
"""
import pcbnew

ROW_A, ROW_B, ROW_C = 13.0, 30.0, 41.0
DX = 1.0                     # shift of the chain after the GDT (clamp courtyard clearance)
X_UTURN_AB, X_UTURN_BC = 49.5 + DX, 19.5

# keep-out rectangles for the generic placer (x0, y0, x1, y1)
CORRIDORS = [(0.0, 6.0, 51.5, 21.0), (18.0, 17.0, 51.5, 37.0), (17.5, 34.0, 36.0, 43.8)]


def short(n):
    return n.split("/")[-1]


class Layout:
    def __init__(self, board, fps, nets, P, ox, oy):
        self.b, self.fps, self.nets, self.P, self.ox, self.oy = board, fps, nets, P, ox, oy
        self.placed = {}
        self.by_nets = {}
        for ref, fp in fps.items():
            key = (ref[0] if ref[:1] in "RCLDQ" else ref[:2], frozenset(short(p.GetNetname()) for p in fp.Pads() if p.GetNetname()))
            self.by_nets.setdefault(key, []).append(ref)

    def find(self, kind, *nets):
        refs = self.by_nets.get((kind, frozenset(nets)), [])
        if len(refs) != 1:
            raise KeyError(f"{kind} with nets {nets}: {refs}")
        return refs[0]

    def put(self, ref, x, y, rot):
        fp = self.fps[ref]
        fp.SetOrientationDegrees(rot)
        fp.SetPosition(self.P(x, y))
        fp.SetLocked(True)
        self.placed[ref] = (x, y, rot)
        return ref

    def pad(self, ref, num):
        for p in self.fps[ref].Pads():
            if p.GetNumber() == str(num):
                v = p.GetPosition()
                return (pcbnew.ToMM(v.x) - self.ox, pcbnew.ToMM(v.y) - self.oy)
        raise KeyError(f"{ref}.{num}")

    def pad_of_net(self, ref, net):
        for p in self.fps[ref].Pads():
            if short(p.GetNetname()) == net:
                v = p.GetPosition()
                return (pcbnew.ToMM(v.x) - self.ox, pcbnew.ToMM(v.y) - self.oy)
        raise KeyError(f"{ref} has no pad on {net}")

    def netobj(self, net):
        for full, ni in self.nets.items():
            if short(full) == net:
                return ni
        raise KeyError(net)

    def track(self, net, pts, width=0.35, layer=pcbnew.F_Cu):
        ni = self.netobj(net)
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            if abs(x1 - x2) < 1e-6 and abs(y1 - y2) < 1e-6:
                continue
            t = pcbnew.PCB_TRACK(self.b)
            t.SetStart(self.P(x1, y1)); t.SetEnd(self.P(x2, y2))
            t.SetWidth(pcbnew.FromMM(width)); t.SetLayer(layer); t.SetNet(ni); t.SetLocked(True)
            self.b.Add(t)

    def via(self, net, x, y):
        v = pcbnew.PCB_VIA(self.b)
        v.SetPosition(self.P(x, y)); v.SetWidth(pcbnew.FromMM(0.45)); v.SetDrill(pcbnew.FromMM(0.2))
        v.SetNet(self.netobj(net)); v.SetLocked(True)
        self.b.Add(v)

    def gnd_drop(self, ref, dx=0.0, dy=1.0):
        """GND pad -> via, offset away from the line."""
        x, y = self.pad_of_net(ref, "GND")
        self.via("GND", x + dx, y + dy)
        self.track("GND", [(x, y), (x + dx, y + dy)], 0.4)

    # ------------------------------------------------------------------ RF chain
    def rf(self):
        f, put, pad, pon, T = self.find, self.put, self.pad, self.pad_of_net, self.track
        # ---- row A: input protection + pad relay
        put("J2", 2.54, ROW_A, 180)
        put("GDT1", 9.5, ROW_A + 3.3, 270)          # pad 1 (line) on the row, pads 2/3 (GND) below
        d10 = put(f("D", "RF_IN", "GND"), 14.2 + DX, ROW_A + 0.938, 90)   # BAV99: common pin 3 on the line
        k1 = put("K1", 20.0 + DX, ROW_A - 1.6, 90)        # COM3/COM6 on the row, NC (bypass) above, NO (pad) below
        rser = put(f("R", "PAD_IN", "PAD_OUT"), 20.0 + DX, ROW_A + 4.4, 0)
        rs1 = put(f("R", "PAD_IN", "GND"), 17.9 + DX, ROW_A + 6.0, 270)
        rs2 = put(f("R", "PAD_OUT", "GND"), 22.1 + DX, ROW_A + 6.0, 270)
        T("RF_IN", [pad("J2", 1), pad("GDT1", 1), pad(d10, 3), pad(k1, 3)])
        for p in ("2", "3"):
            x, y = pad("GDT1", p); self.via("GND", x - 2.0, y); self.via("GND", x + 2.0, y)
        for p in ("1", "2"):
            x, y = pad(d10, p); self.via("GND", x, y + 1.2); T("GND", [(x, y), (x, y + 1.2)], 0.4)
        T("PAD_BYP", [pad(k1, 2), pad(k1, 7)])
        no4, no5 = pad(k1, 4), pad(k1, 5)
        T("PAD_IN", [no4, (no4[0], ROW_A + 4.4), pon(rser, "PAD_IN")]); T("PAD_IN", [(no4[0], ROW_A + 4.4), pon(rs1, "PAD_IN")])
        T("PAD_OUT", [no5, (no5[0], ROW_A + 4.4), pon(rser, "PAD_OUT")]); T("PAD_OUT", [(no5[0], ROW_A + 4.4), pon(rs2, "PAD_OUT")])
        self.gnd_drop(rs1); self.gnd_drop(rs2)
        # ---- row A: LPF1 (L->R) and FM notch
        node = self.lpf("LPF1", "RF_A", "LPF1_OUT", start_x=24.0 + DX, y=ROW_A, d=+1, start_pad=pad(k1, 6))
        lt1 = put(f("L", "LPF1_OUT", "TRAP1"), 41.6 + DX, ROW_A + 1.062, 270)
        ct1 = put(f("C", "TRAP1", "GND"), 41.6 + DX, ROW_A + 4.0, 270)   # below the L courtyard
        ltk = put(f("L", "LPF1_OUT", "NOTCH_OUT"), 44.4 + DX, ROW_A, 0)
        ctk = put(f("C", "LPF1_OUT", "NOTCH_OUT"), 44.4 + DX, ROW_A - 2.1, 0)
        lt3 = put(f("L", "NOTCH_OUT", "TRAP3"), 47.2 + DX, ROW_A + 1.062, 270)
        ct3 = put(f("C", "TRAP3", "GND"), 47.2 + DX, ROW_A + 4.0, 270)
        T("LPF1_OUT", [node, pon(lt1, "LPF1_OUT"), pon(ltk, "LPF1_OUT")])
        T("TRAP1", [pon(lt1, "TRAP1"), pon(ct1, "TRAP1")]); self.gnd_drop(ct1)
        T("TRAP3", [pon(lt3, "TRAP3"), pon(ct3, "TRAP3")]); self.gnd_drop(ct3)
        for net in ("LPF1_OUT", "NOTCH_OUT"):
            cx, cy = pon(ctk, net); T(net, [(cx, cy), (cx, ROW_A)])
        # NOTCH_OUT -> U-turn -> K2 COM3
        k2 = put("K2", 44.5 + DX, ROW_B + 1.6, 270)       # COM3 right, COM6 left on row B; NO (LNA) above, NC (bypass) below
        T("NOTCH_OUT", [pon(ltk, "NOTCH_OUT"), pon(lt3, "NOTCH_OUT"), (X_UTURN_AB, ROW_A), (X_UTURN_AB, ROW_B), pad(k2, 3)])
        T("LNA_BYP", [pad(k2, 2), pad(k2, 7)])
        # ---- LNA loop above K2 (input from NO4 on the right, output to NO5 on the left)
        u13 = put("U13", 44.5 + DX, 22.5, 270)
        cin = put(f("C", "LNA_IN", "LNA_RFIN"), 47.6 + DX, 23.5, 90)
        cout = put(f("C", "LNA_RFOUT", "LNA_O"), 41.5 + DX, 21.5, 270)
        lch = put(f("L", "5V_LNA", "LNA_RFOUT"), 38.5 + DX, 20.55, 0)
        rsa = put(f("R", "LNA_O", "GND"), 40.0 + DX, 22.9, 180)
        rse = put(f("R", "LNA_O", "LNA_PAD_OUT"), 41.5 + DX, 24.2, 270)
        rsb = put(f("R", "LNA_PAD_OUT", "GND"), 40.0 + DX, 25.3, 180)
        no4, no5 = pad(k2, 4), pad(k2, 5)
        ci = pon(cin, "LNA_IN")
        T("LNA_IN", [no4, (no4[0], 25.2), (ci[0], 25.2), ci])
        ri = pon(cin, "LNA_RFIN"); p1 = pad(u13, 1)
        T("LNA_RFIN", [ri, (ri[0], p1[1]), p1])
        p3 = pad(u13, 3); co = pon(cout, "LNA_RFOUT")
        T("LNA_RFOUT", [p3, (co[0], p3[1]), co]); T("LNA_RFOUT", [pon(lch, "LNA_RFOUT"), (co[0], p3[1])])
        lo = pon(cout, "LNA_O")
        T("LNA_O", [lo, (lo[0], 22.9), pon(rsa, "LNA_O")]); T("LNA_O", [(lo[0], 22.9), pon(rse, "LNA_O")])
        po = pon(rse, "LNA_PAD_OUT")
        T("LNA_PAD_OUT", [po, (po[0], 26.2), (no5[0], 26.2), no5]); T("LNA_PAD_OUT", [(po[0], 25.3), pon(rsb, "LNA_PAD_OUT")])
        self.gnd_drop(rsa, dx=-1.0, dy=0.0); self.gnd_drop(rsb, dx=-1.0, dy=0.0)
        gx, gy = pad(u13, 2); self.via("GND", gx, gy - 1.6); T("GND", [(gx, gy), (gx, gy - 1.6)], 0.4)
        # ---- row B: LPF2 (R->L)
        node = self.lpf("LPF2", "LPF2_IN", "LPF2_OUT", start_x=39.6 + DX, y=ROW_B, d=-1, start_pad=pad(k2, 6))
        # ---- U-turn to row C: transformer, termination, series R, ADC
        t1 = put("T1", 26.0, ROW_C - 2.54, 0)
        T("LPF2_OUT", [node, (X_UTURN_BC, ROW_B), (X_UTURN_BC, ROW_C), pad(t1, 3)])
        x1, y1 = pad(t1, 1); self.via("GND", x1 - 2.15, y1); T("GND", [(x1, y1), (x1 - 2.15, y1)], 0.4)
        rt = put(f("R", "AIN_P_T", "AIN_N_T"), 32.0, ROW_C - 2.54, 90)
        r33p = put(f("R", "AIN_P_T", "ADC_VINP"), 33.8, ROW_C, 0)
        r33n = put(f("R", "AIN_N_T", "ADC_VINN"), 33.8, ROW_C - 5.08, 0)
        p4, p6, p5 = pad(t1, 4), pad(t1, 6), pad(t1, 5)
        T("AIN_P_T", [p4, (32.0, p4[1]), pon(rt, "AIN_P_T")], 0.3); T("AIN_P_T", [(32.0, p4[1]), pon(r33p, "AIN_P_T")], 0.3)
        T("AIN_N_T", [p6, (32.0, p6[1]), pon(rt, "AIN_N_T")], 0.3); T("AIN_N_T", [(32.0, p6[1]), pon(r33n, "AIN_N_T")], 0.3)
        self.via("ADC_VCM", p5[0] + 2.3, p5[1]); T("ADC_VCM", [p5, (p5[0] + 2.3, p5[1])], 0.3)
        # ADC inputs: pins 31 (VIN+) / 30 (VIN-), whichever ends up on top gets the top resistor's net
        u8 = "U8"
        vp, vn = pad(u8, 31), pad(u8, 30)
        rp, rn = pon(r33p, "ADC_VINP"), pon(r33n, "ADC_VINN")
        if not (vp[1] > vn[1]):   # P must be the lower pin, like its resistor, or the two routes cross
            raise RuntimeError(f"ADC VIN pin order crosses: VIN+ {vp} VIN- {vn}")
        # both pins sit below the P resistor row, so P must take the LEFT vertical (its horizontal at the resistor
        # row then stops short of N's vertical, and N's vertical ends above P's final horizontal)
        xj = vp[0] - 1.2
        T("ADC_VINP", [rp, (xj - 1.1, rp[1]), (xj - 1.1, vp[1]), vp], 0.25)
        T("ADC_VINN", [rn, (xj - 0.5, rn[1]), (xj - 0.5, vn[1]), vn], 0.25)
        # 10 pF charge-kickback caps right on the VIN traces, GND via away from the pair
        kp = put(f("C", "ADC_VINP", "GND"), rp[0] + 1.0, ROW_C + 0.48, 270)
        kn = put(f("C", "ADC_VINN", "GND"), rn[0] + 1.0, ROW_C - 5.08 - 0.48, 90)
        self.gnd_drop(kp, dy=1.0); self.gnd_drop(kn, dy=-1.0)
        return k1, k2

    def lpf(self, prefix, n_in, n_out, start_x, y, d, start_pad):
        """C1 | L2||C2 | C3 | L4||C4 | C5 | L6||C6 | C7, series in line, tank caps on the far side from the shunts."""
        f, put, pon, T = self.find, self.put, self.pad_of_net, self.track
        n2, n4 = f"{prefix}_N2", f"{prefix}_N4"
        nodes = [n_in, n2, n4, n_out]
        step = 2.6
        shunt_rot = 270              # pad 1 (signal) at the top -> on the line, GND below
        tank_dy = -2.1               # tank caps above the line
        x = start_x
        prev_pad = start_pad
        last = None
        for i, net in enumerate(nodes):
            c = put(f("C", net, "GND"), x, y + 0.48, shunt_rot)
            T(net, [prev_pad, pon(c, net)] if prev_pad else [pon(c, net)])
            self.gnd_drop(c)
            last = pon(c, net)
            if i == 3:
                break
            nxt = nodes[i + 1]
            lx = x + d * step
            rot = 0 if d > 0 else 180    # pad 1 (input-side net) faces the incoming direction
            l = put(f("L", net, nxt), lx, y, rot)
            cc = put(f("C", net, nxt), lx, y + tank_dy, rot)
            T(net, [last, pon(l, net)])
            for nn in (net, nxt):
                cx, cy = pon(cc, nn); T(nn, [(cx, cy), (cx, y)])
            prev_pad = pon(l, nxt)
            x = lx + d * step
        return last

    # ------------------------------------------------------------------ USB 3 SuperSpeed
    def usb3(self):
        """FT601 TOD/RID pairs to J1 SSTX/SSRX. All four lines move up between the QFN and the connector, so each
        makes one vertical jog: the topmost line jogs first (nearest the QFN), the next one 0.45 mm further right,
        etc., so no horizontal run ever crosses a later jog. AC caps on TX, staggered so a P line passes beside the
        N cap. 0.2 mm wide (0.4 mm QFN pitch), short enough that the impedance step is negligible."""
        f, put, pad, pon, T = self.find, self.put, self.pad, self.pad_of_net, self.track
        cn = f("C", "FT_TXN", "USB_SSTXN"); cp = f("C", "FT_TXP", "USB_SSTXP")
        lines = [  # (net at FT, FT pad, J1 pad, AC cap or None, net at J1)
            ("FT_TXN", pad("U11", 31), pad("J1", 6), cn, "USB_SSTXN"),
            ("FT_TXP", pad("U11", 32), pad("J1", 7), cp, "USB_SSTXP"),
            ("USB_SSRXN", pad("U11", 34), pad("J1", 9), None, "USB_SSRXN"),
            ("USB_SSRXP", pad("U11", 35), pad("J1", 10), None, "USB_SSRXP")]
        by_ft = sorted(lines, key=lambda l: l[1][1]); by_j = sorted(lines, key=lambda l: l[2][1])
        if [l[0] for l in by_ft] != [l[0] for l in by_j]:
            raise RuntimeError("USB3 lines would cross: FT601 and J1 orders differ")
        a = max(l[1][0] for l in lines) + 1.0
        cap_x = {cn: None, cp: None}
        for k, (net, ftp, jp, cap, jnet) in enumerate(by_ft):
            xv = a + 0.45 * k
            if cap == cn:
                # lowest line: AC cap on its own row before the jog, jog pushed right of the cap
                cx = a + 2.2; xv = a + 3.4
                put(cap, cx, ftp[1], 0)
                T(net, [ftp, pon(cap, net)], 0.2)
                T(jnet, [pon(cap, jnet), (xv, ftp[1]), (xv, jp[1]), jp], 0.2)
            elif cap == cp:
                put(cap, xv + 1.4, jp[1], 0)
                T(net, [ftp, (xv, ftp[1]), (xv, jp[1]), pon(cap, net)], 0.2)
                T(jnet, [pon(cap, jnet), jp], 0.2)
            else:
                T(net, [ftp, (xv, ftp[1]), (xv, jp[1]), jp], 0.2)
        return [cn, cp]
