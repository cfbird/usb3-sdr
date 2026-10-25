#!/usr/bin/env python3
"""Fill the unused parts of In2.Cu with GND so every B.Cu track has an adjacent reference plane.

In2 carries the 1V1, 3V3_D and 1V8_A power islands; elsewhere it was bare, which left B.Cu signals (the ADC clocks
among them) referenced only to In1 GND through the core. This adds a whole-board GND zone on In2 (same outline and
settings as the In1 GND plane) at the lowest priority, after moving each power island up one priority step so they
keep their copper. Idempotent: does nothing if an In2 GND zone already exists.
usage: in2_gnd_fill.py board.kicad_pcb   (edited in place; zones refilled)
"""
import os
import sys

import pcbnew


def main(path):
    if not os.path.exists(os.path.splitext(path)[0] + ".kicad_pro"):
        sys.exit(f"{path}: no matching .kicad_pro next to it")
    b = pcbnew.LoadBoard(path)
    zones = list(b.Zones())
    if any(z.GetLayer() == pcbnew.In2_Cu and z.GetNetname() == "GND" for z in zones):
        print("In2 GND zone already present")
        return
    src = next(z for z in zones if z.GetLayer() == pcbnew.In1_Cu and z.GetNetname() == "GND")
    for z in zones:
        if z.GetLayer() == pcbnew.In2_Cu:
            z.SetAssignedPriority(z.GetAssignedPriority() + 1)
    g = src.Duplicate()
    g.SetLayer(pcbnew.In2_Cu)
    g.SetAssignedPriority(0)
    b.Add(g)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.Save(path)
    for z in b.Zones():
        print(f"  {z.GetNetname():6s} {b.GetLayerName(z.GetLayer())} priority {z.GetAssignedPriority()}")


if __name__ == "__main__":
    main(sys.argv[1])
