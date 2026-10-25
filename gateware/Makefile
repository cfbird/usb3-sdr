# usb3-sdr gateware. Tools: yowasp-yosys / yowasp-nextpnr-ecp5 / yowasp-ecppack from ../.venv
VENV    ?= ../.venv/bin
YOSYS   ?= $(VENV)/yowasp-yosys
NEXTPNR ?= $(VENV)/yowasp-nextpnr-ecp5
ECPPACK ?= $(VENV)/yowasp-ecppack
DEVICE  ?= 25k            # 45k once LFE5U-45F is in stock (ball-compatible)
SEED    ?= 4             # fixed seed; nextpnr results still vary run to run (see README)
RTL = $(addprefix rtl/,top.v boot_seq.v nco.v cic_decim.v fir_decim.v ddc.v async_fifo.v ft601_245.v)
B = build
CXXRTL_INC = $(shell find ../.venv -type d -path "*cxxrtl/runtime" | head -1)

all: $(B)/usb3sdr.bit

$(B)/nco_quarter.hex $(B)/hb.hex $(B)/cfir.hex: tools/gen_coeffs.py
	python3 tools/gen_coeffs.py

# $readmemh paths resolve relative to the build dir
$(B)/usb3sdr.json: $(RTL) $(B)/nco_quarter.hex $(B)/hb.hex $(B)/cfir.hex
	cd $(B) && ../$(YOSYS) -q -l yosys.log -p "read_verilog -DECP5_IOREG $(addprefix ../,$(RTL)); synth_ecp5 -top top -json usb3sdr.json"

$(B)/usb3sdr.config: $(B)/usb3sdr.json constraints/usb3sdr.lpf
	$(NEXTPNR) -q -l $(B)/nextpnr.log --$(strip $(DEVICE)) --package CABGA256 --speed 6 --seed $(SEED) \
	  --json $< --lpf constraints/usb3sdr.lpf --textcfg $@ --timing-allow-fail
	@grep -E "Max frequency|Device utilisation" -A 12 $(B)/nextpnr.log | grep -E "MHz|TRELLIS_SLICE|DP16KD|MULT18X18D|TRELLIS_IO" | head -12

$(B)/usb3sdr.bit: $(B)/usb3sdr.config
	$(ECPPACK) --compress $< $@

# ---- simulation (CXXRTL)
sim-ddc: $(B)/nco_quarter.hex
	cd $(B) && ../$(YOSYS) -q -p "read_verilog ../rtl/nco.v ../rtl/cic_decim.v ../rtl/fir_decim.v ../rtl/ddc.v; hierarchy -top ddc; proc; flatten; opt_clean; write_cxxrtl -O5 ddc_sim.cc"
	cd $(B) && g++ -O2 -std=c++17 -I$(abspath $(CXXRTL_INC)) -I. -o tb_ddc ../sim/tb_ddc.cpp && ./tb_ddc
	python3 sim/analyze_ddc.py $(B)/ddc_out.csv

sim-ft:
	cd $(B) && ../$(YOSYS) -q -p "read_verilog ../rtl/async_fifo.v ../rtl/ft601_245.v ../sim/ft_tb_top.v; hierarchy -top ft_tb_top; proc; flatten; opt_clean; write_cxxrtl -O5 ft_sim.cc"
	cd $(B) && g++ -O2 -std=c++17 -I$(abspath $(CXXRTL_INC)) -I. -o tb_ft ../sim/tb_ft.cpp && ./tb_ft 2 && ./tb_ft 1

sim-boot:
	cd $(B) && ../$(YOSYS) -q -p "read_verilog ../rtl/boot_seq.v; hierarchy -top boot_seq; proc; flatten; opt_clean; write_cxxrtl -O5 boot_sim.cc"
	cd $(B) && g++ -O2 -std=c++17 -I$(abspath $(CXXRTL_INC)) -I. -o tb_boot ../sim/tb_boot.cpp && ./tb_boot

sim: sim-ddc sim-ft sim-boot

clean:
	rm -f $(B)/*.json $(B)/*.config $(B)/*.bit $(B)/*.log $(B)/*_sim.cc $(B)/tb_* $(B)/*.csv

.PHONY: all sim sim-ddc sim-ft sim-boot clean
