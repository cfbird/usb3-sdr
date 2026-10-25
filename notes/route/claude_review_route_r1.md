# Claude's review of AGY routing round 1 (agy_route_r1.md, agy_adc_plan.json), 2026-10-25

| Claim | Verdict | How checked |
|---|---|---|
| ADC series resistors are 22 ohm | VERIFIED | work board values: R26-R41 all "22" |
| ADC setup/hold pass with DCO inverted (0x16 = 0x80) even at 106 mm | VERIFIED | agy_timing_check.py output; boot_seq.v rom[11] writes 0x16 = 0x80 |
| "AD9649 Rev B p.17 specifies C_LOAD < 10 pF", so ADC <= 55 mm is a hard limit | DISPUTED (citation) | pdftotext of refs/datasheets/AD9649_RevB.pdf: no C_LOAD limit. The datasheet says performance is measured with "approximately 5 pF loading on each output bit" and the digital-outputs section advises minimising output trace length and loads, plus buffers for large capacitive loads. So 55 mm is a reasonable design target, not a datasheet limit. The plan's 22-36 mm meets it either way. |
| FT601 length / skew rules relaxed (<= 45 mm; -10..+30 mm skew) with slack numbers | PLAUSIBLE | consistent with the IO-register timing model Claude verified earlier; not independently re-derived |
| SPI and async nets exempt from skew | VERIFIED | boot_seq.v SPI divider; FT601 datasheet signal table (WAKEUP/RESET/GPIO async) |
| R2 resistor moves: "0 courtyard / pad conflicts" | DISPUTED | applied on scratchpad/r4 (kicad/gen/apply_moves.py), KiCad DRC: R35 pad 1 on K2 pad 8 (short, K2_COIL vs ADC_D9_R); R31 overlaps U8's courtyard and is 0 mm from your own 1V8_D via (144.30,140.60); R36 and R37 overlap K2's courtyard. place_free.py nudged them: R35 -> (141.05,133.40) rot 180, R31 -> (145.10,141.30), R36 -> (146.15,137.35), R37 -> (141.45,136.80). After that DRC is clean. Your checks use rectangles from fanout_data.json; run kicad/gen/fanout_trial.py (or DRC) on placements next time. |
| R2 corridors | not used | DeepPCB run 4 routes the ADC bus from the new resistor positions; lengths will be checked with your updated agy_timing_check.py |
