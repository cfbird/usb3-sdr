#!/bin/bash
# Full regenerate + verify pipeline: schematic -> netlist checks -> ERC -> PCB -> DRC (with schematic parity)
set -e
cd "$(dirname "$0")"
python3 build.py
python3 verify.py | tail -1
python3 check_lpf.py
( cd .. && kicad-cli sch erc -o erc.rpt --severity-all usb3-sdr.kicad_sch | grep -i violations )
( cd .. && kicad-cli sch export netlist --format kicadsexpr -o usb3-sdr.net usb3-sdr.kicad_sch >/dev/null )
python3 -X faulthandler pcb_build.py | tail -1
( cd .. && kicad-cli pcb drc --schematic-parity --severity-all --format json -o drc.json usb3-sdr.kicad_pcb >/dev/null )
python3 - <<'PY'
import json, collections
d = json.load(open("../drc.json"))
print("DRC errors:", dict(collections.Counter(v["type"] for v in d["violations"] if v["severity"] == "error")))
print("DRC warnings:", dict(collections.Counter(v["type"] for v in d["violations"] if v["severity"] == "warning")))
print("unconnected:", len(d["unconnected_items"]), " parity issues:", len(d["schematic_parity"]))
PY
