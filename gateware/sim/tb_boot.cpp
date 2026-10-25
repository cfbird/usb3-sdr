// Decodes boot_seq's SPI and I2C pin activity (with an ACKing I2C target model) and checks the sequence.
#include <cstdio>
#include <string>
#include <vector>
#include "boot_sim.cc"

int main() {
    cxxrtl_design::p_boot__seq t;
    std::vector<std::string> got;
    // SPI decode
    bool csb_prev = 1, sclk_prev = 0; uint32_t spi_sh = 0; int spi_n = 0;
    // I2C target model
    bool scl_prev = 1, sda_prev = 1, in_frame = 0, ack_drive = 0; int bits = 0; uint32_t byte = 0;
    std::vector<int> frame;
    t.p_rst.set<bool>(true);
    long cyc;
    for (cyc = 0; cyc < 400000 && !t.p_done.get<bool>(); cyc++) {
        if (cyc == 4) t.p_rst.set<bool>(false);
        bool scl = !t.p_scl__oe.get<bool>();
        bool sda = !t.p_sda__oe.get<bool>() && !ack_drive;
        t.p_sda__in.set<bool>(sda);
        t.p_clk.set<bool>(false); t.step(); t.p_clk.set<bool>(true); t.step();

        // ---- SPI (sample on SCLK rising edge while CSB low)
        bool csb = t.p_adc__csb.get<bool>(), sclk = t.p_adc__sclk.get<bool>();
        if (!csb && sclk && !sclk_prev) { spi_sh = (spi_sh << 1) | t.p_adc__sdio.get<bool>(); spi_n++; }
        if (csb && !csb_prev) {
            char b[64]; snprintf(b, sizeof b, "SPI %s addr 0x%03x = 0x%02x (%d bits)", (spi_sh >> 23) & 1 ? "RD" : "WR",
                                 (spi_sh >> 8) & 0x1fff, spi_sh & 0xff, spi_n);
            got.push_back(b); spi_sh = 0; spi_n = 0;
        }
        csb_prev = csb; sclk_prev = sclk;

        // ---- I2C target
        scl = !t.p_scl__oe.get<bool>();
        sda = !t.p_sda__oe.get<bool>() && !ack_drive;
        if (scl && scl_prev && sda_prev && !sda) { in_frame = 1; bits = 0; byte = 0; frame.clear(); }   // START
        else if (scl && scl_prev && !sda_prev && sda && in_frame) {                                      // STOP
            in_frame = 0;
            char b[64]; snprintf(b, sizeof b, "I2C dev 0x%02x R%d = 0x%02x", frame.size() > 0 ? frame[0] >> 1 : -1,
                                 frame.size() > 1 ? frame[1] : -1, frame.size() > 2 ? frame[2] : -1);
            got.push_back(b);
        } else if (in_frame && scl && !scl_prev) {                                                     // SCL rising
            if (bits < 8) { byte = (byte << 1) | sda; bits++; }
            else { bits = 0; byte = 0; }                                                               // ACK clock
        } else if (in_frame && !scl && scl_prev) {                                                     // SCL falling
            if (bits == 8 && !ack_drive) { frame.push_back(byte); ack_drive = 1; }                    // ACK next bit
            else if (bits == 0 && ack_drive) ack_drive = 0;
        }
        scl_prev = scl; sda_prev = !t.p_sda__oe.get<bool>() && !ack_drive;
    }
    const char *expect[] = {
        "SPI WR addr 0x008 = 0x02 (24 bits)", "SPI WR addr 0x0ff = 0x01 (24 bits)",
        "I2C dev 0x58 R21 = 0x02", "I2C dev 0x58 R22 = 0x00", "I2C dev 0x58 R23 = 0x3c",
        "I2C dev 0x58 R25 = 0x00", "I2C dev 0x58 R26 = 0x30", "I2C dev 0x58 R72 = 0x02",
        "SPI WR addr 0x014 = 0x81 (24 bits)", "SPI WR addr 0x008 = 0x00 (24 bits)", "SPI WR addr 0x0ff = 0x01 (24 bits)"};
    int n = sizeof expect / sizeof *expect, bad = 0;
    for (size_t i = 0; i < got.size(); i++) {
        bool ok = (int)i < n && got[i] == expect[i];
        printf("%s %s\n", ok ? "  ok " : " BAD ", got[i].c_str()); bad += !ok;
    }
    if ((int)got.size() != n) bad++;
    printf("done=%d after %ld boot clocks (%.1f ms @ 2.42 MHz), nack=%d\n", t.p_done.get<bool>(), cyc,
           cyc / 2.42e3, t.p_i2c__nack.get<bool>());
    bool pass = !bad && t.p_done.get<bool>() && !t.p_i2c__nack.get<bool>();
    printf(pass ? "PASS\n" : "FAIL\n");
    return pass ? 0 : 1;
}
