// FT601 bus model vs. ft601_245 + async_fifo. Checks ordering/loss, host->FPGA words, bus contention.
#include <cstdio>
#include <cstdlib>
#include <deque>
#include "ft_sim.cc"

int main(int argc, char **argv) {
    int min_full = argc > 1 ? atoi(argv[1]) : 2;   // minimum TXE_N-high pulse length (cycles)
    cxxrtl_design::p_ft__tb__top t;
    srand(7);
    // 1.25 ns ticks: ft_clk half period 4 ticks (100 MHz), wr_clk half period 5 ticks (80 MHz)
    bool ftc = 0, wrc = 0, txe_n = 1, rxf_n = 1;
    long accepted = 0, errors = 0, contention = 0, rx_got = 0, rx_sent = 0, burst = 0;
    uint32_t expect = 0;
    std::deque<uint32_t> host_q;
    uint32_t host_next = 0xC0000000;
    t.p_rst.set<bool>(true);
    for (long tick = 0; tick < 4000000; tick++) {
        if (tick == 200) t.p_rst.set<bool>(false);
        bool ft_edge = (tick % 4 == 0), wr_edge = (tick % 5 == 0);
        if (ft_edge && !ftc) {
            // ---- sample DUT outputs as the FT601 would at this rising edge
            bool wr_n = t.p_wr__n.get<bool>(), rd_n = t.p_rd__n.get<bool>(), oe_n = t.p_oe__n.get<bool>();
            if (!oe_n && t.p_doe.get<bool>()) contention++;
            if (!wr_n && !txe_n) {
                uint32_t w = t.p_dout.get<uint32_t>();
                if (w != expect) { if (errors < 5) printf("ERR word %u expected %u\n", w, expect); errors++; expect = w; }
                expect++; accepted++;
            }
            if (!rd_n && !rxf_n && !host_q.empty()) host_q.pop_front();
        }
        // ---- clocks
        if (tick % 4 == 0) ftc = !ftc;
        if (tick % 5 == 0) wrc = !wrc;
        t.p_ft__clk.set<bool>(ftc); t.p_wr__clk.set<bool>(wrc);
        t.step();
        if (ft_edge && ftc) {
            if (t.p_rx__valid.get<bool>()) {
                uint32_t w = t.p_rx__data.get<uint32_t>();
                if (w != (0xC0000000u | (uint32_t)rx_got)) { printf("ERR rx %08x\n", w); errors++; }
                rx_got++;
            }
            // ---- FT601 model updates its outputs after the edge
            if (burst-- <= 0) { txe_n = !txe_n; burst = txe_n ? min_full - 1 + rand() % 20 : rand() % 300; }   // random space/full
            if (host_q.empty() && rand() % 3000 == 0) {                                      // occasional command burst
                int n = 1 + rand() % 4;
                for (int i = 0; i < n; i++) host_q.push_back(0xC0000000u | (uint32_t)rx_sent++);
            }
            rxf_n = host_q.empty();
            t.p_txe__n.set<bool>(txe_n); t.p_rxf__n.set<bool>(rxf_n);
            t.p_din.set<uint32_t>(host_q.empty() ? 0xdeadbeef : host_q.front());
        }
    }
    double us = 4000000 * 1.25e-3;
    printf("FPGA->host words %ld (%.0f MB/s avg over %.0f us), order errors %ld, bus contention %ld\n",
           accepted, accepted * 4.0 / us, us, errors, contention);
    printf("host->FPGA words sent %ld, received %ld; DUT order_err flag %d (min TXE_N high %d cycles)\n", rx_sent - (long)host_q.size(), rx_got, t.p_order__err.get<bool>(), min_full);
    // pass: either no ordering errors at all, or (only with 1-cycle pulses) every error was flagged by the DUT
    bool flagged_ok = errors == 0 ? !t.p_order__err.get<bool>() : (min_full == 1 && t.p_order__err.get<bool>());
    bool ok = flagged_ok && contention == 0 && rx_got == rx_sent - (long)host_q.size() && accepted > 100000;
    printf(ok ? "PASS\n" : "FAIL\n");
    return ok ? 0 : 1;
}
