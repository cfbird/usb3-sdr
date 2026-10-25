# Datasheets

The design was checked against these vendor documents. They are copyrighted by their vendors, so they are not in this
repository; download them to the local path shown (scripts and notes refer to these names). Links checked
2026-10-24: "ok" = HTTP 200; "blocked" = the vendor refuses scripted requests but the URL is the vendor's own.

| Local path | Part | Source | Link |
|---|---|---|---|
| refs/datasheets/AD9649_RevB.pdf | AD9649 14-bit 80 MSPS ADC (rev B) | https://www.analog.com/media/en/technical-documentation/data-sheets/AD9649.pdf | blocked |
| refs/DS_FT600Q-FT601Q-IC-Datasheet.pdf | FTDI FT601 USB 3.0 FIFO bridge | https://ftdichip.com/wp-content/uploads/2023/09/DS_FT600Q-FT601Q-IC-Datasheet.pdf | blocked |
| refs/datasheets/LMK61E2_SNAS674C.pdf | TI LMK61E2 programmable oscillator (8-pin, I2C) | https://www.ti.com/lit/ds/symlink/lmk61e2.pdf | ok |
| refs/datasheets/LMK61E2-100M_fixed_6pin.pdf | TI LMK61E2-100M fixed 100 MHz (6-pin, **not** the BOM part) | https://www.ti.com/lit/ds/symlink/lmk61e2-100m.pdf | ok |
| refs/tps62a0x/tps62a02.pdf | TI TPS62A02 2 A buck | https://www.ti.com/lit/ds/symlink/tps62a02.pdf | ok |
| refs/datasheets/TPS7A20.pdf | TI TPS7A20 LDO | https://www.ti.com/lit/ds/symlink/tps7a20.pdf | ok |
| refs/datasheets/TPS22918.pdf | TI TPS22918 load switch | https://www.ti.com/lit/ds/symlink/tps22918.pdf | ok |
| refs/datasheets/Lattice_ECP5_Versa_FPGA-EB-02021.pdf | Lattice ECP5 Versa board user guide (FPGA-EB-02021) | https://ftp.libre-soc.org/FPGA-EB-02021-2-3-ECP5-Versa-Development-Board.pdf (mirror; original on latticesemi.com) | ok |
| refs/datasheets/GVA-62+.pdf | Mini-Circuits GVA-62+ amplifier | https://www.minicircuits.com/pdfs/GVA-62+.pdf | ok |
| refs/datasheets/GVA-84+.pdf | Mini-Circuits GVA-84+ amplifier | https://www.minicircuits.com/pdfs/GVA-84+.pdf | ok |
| refs/datasheets/LHA-13LN+.pdf | Mini-Circuits LHA-13LN+ LNA | https://www.minicircuits.com/pdfs/LHA-13LN+.pdf | ok |
| refs/datasheets/PHA-13LN+.pdf | Mini-Circuits PHA-13LN+ amplifier | https://www.minicircuits.com/pdfs/PHA-13LN+.pdf | ok |
| refs/datasheets/ADT4-6T+.pdf | Mini-Circuits ADT4-6T+ transformer | https://www.minicircuits.com/pdfs/ADT4-6T+.pdf | ok |
| refs/datasheets/Omron_G6K.pdf | Omron G6K signal relay | https://omronfs.omron.com/en_US/ecb/products/pdf/en-g6k.pdf | ok |
| refs/datasheets/Hongfa_HFD4.pdf | Hongfa HFD4 signal relay | hongfa.com product page for HFD4 (the old direct PDF link now returns 404) | — |

The ECP5 pinout CSV and the Project Trellis IO databases in `refs/data/` are kept: the CSV is Lattice's published
pinout, the Trellis files are ISC-licensed.
