// CXXRTL testbench for ddc.v: two tones in, captures complex output to ddc_out.csv
#include <cmath>
#include <cstdio>
#include <cstdint>
#include <cstdlib>
#include "ddc_sim.cc"

int main(int argc, char **argv) {
    const double FS = 80e6, F_NCO = 7.1e6;
    const double F1 = F_NCO + 100e3, F2 = F_NCO + 900e3;   // in-band tone, out-of-band tone
    const double A = 0.45 * 8191;
    const int N_OUT = 2000 + 16384;
    cxxrtl_design::p_ddc top;
    uint32_t pinc = (uint32_t)llround(F_NCO / FS * 4294967296.0);
    top.p_phase__inc.set<uint32_t>(pinc);
    top.p_rst.set<bool>(true);
    for (int i = 0; i < 8; i++) { top.p_clk.set<bool>(false); top.step(); top.p_clk.set<bool>(true); top.step(); }
    top.p_rst.set<bool>(false);
    FILE *f = fopen("ddc_out.csv", "w");
    srand(1);
    long n = 0; int got = 0;
    while (got < N_OUT) {
        double t = n / FS;
        double dither = ((rand() / (double)RAND_MAX) - 0.5) * 2.0;   // ~1 LSB pk-pk
        int x = (int)lround(A * sin(2 * M_PI * F1 * t) + A * sin(2 * M_PI * F2 * t) + dither);
        top.p_adc.set<uint16_t>((uint16_t)(x & 0x3fff));
        top.p_clk.set<bool>(false); top.step();
        top.p_clk.set<bool>(true);  top.step();
        n++;
        if (top.p_out__valid.get<bool>()) {
            int16_t i = (int16_t)top.p_i__out.get<uint16_t>();
            int16_t q = (int16_t)top.p_q__out.get<uint16_t>();
            fprintf(f, "%d,%d\n", i, q);
            got++;
        }
    }
    fclose(f);
    printf("cycles %ld, outputs %d, output rate %.4f MSPS\n", n, got, got / (n / FS) / 1e6);
    return 0;
}
