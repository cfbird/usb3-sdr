// Decimate-by-2 FIR for an I/Q pair, one MAC per rail, time-multiplexed.
// Needs NTAPS <= clocks per output (2 input samples): HB 23 taps in 32 clocks, CFIR 59 taps in 64 clocks
// at 80 MHz. Pipeline latency (6 clocks) overlaps the next run.
// Coefficients: signed Q1.17 (DC gain 1.0 = 2^17), loaded from COEF_FILE.
module fir_decim #(
    parameter NTAPS     = 23,
    parameter COEF_FILE = "hb.hex",
    parameter DW        = 18,
    parameter AW        = 6      // sample buffer 2^AW >= NTAPS + 2
) (
    input  wire                 clk,
    input  wire                 rst,
    input  wire signed [DW-1:0] i_in,
    input  wire signed [DW-1:0] q_in,
    input  wire                 in_valid,
    output reg  signed [DW-1:0] i_out,
    output reg  signed [DW-1:0] q_out,
    output reg                  out_valid
);
    localparam AccW = DW + 18 + AW;

    reg [17:0]   coef [0:NTAPS-1];
    initial $readmemh(COEF_FILE, coef);

    reg [2*DW-1:0] buf_mem [0:(1<<AW)-1];   // {I,Q}
    reg [AW-1:0]   wptr;
    reg            phase;                     // decimation phase

    // MAC sequencer: addr -> BRAM read -> BRAM output reg -> multiply (registered) -> accumulate.
    // first/last flags travel with the data, so back-to-back runs need no idle cycles.
    reg            busy = 0;
    reg [AW-1:0]   base, k;
    reg [7:0]      tap;
    reg [7:0]      tk = 0;
    reg [2*DW-1:0] x_rd, x_rd2;
    reg signed [17:0] h_rd, h_rd2;
    reg signed [DW+17:0] p_i, p_q;
    reg [3:0]      v = 0, f = 0, l = 0;     // valid / first / last, one bit per pipeline stage
    reg signed [AccW-1:0] acc_i, acc_q, res_i, res_q;
    reg            res_v = 0;

    always @(posedge clk) begin
        if (rst) begin
            wptr <= 0; phase <= 0; busy <= 0; out_valid <= 0; v <= 0; f <= 0; l <= 0; res_v <= 0;
        end else begin
            out_valid <= 0;

            // write incoming samples; start a MAC run on every 2nd sample
            if (in_valid) begin
                buf_mem[wptr + 1'b1] <= {i_in, q_in};
                wptr  <= wptr + 1'b1;
                phase <= ~phase;
                if (phase) begin busy <= 1; base <= wptr + 1'b1; tap <= 0; end
            end

            // stage 0: addresses
            if (busy) begin
                k   <= base - tap[AW-1:0];
                tk  <= tap;
                tap <= tap + 1'b1;
                if (tap == NTAPS - 1) busy <= 0;
            end
            v[0] <= busy; f[0] <= busy && tap == 0; l[0] <= busy && tap == NTAPS - 1;
            // stage 1: RAM/ROM read; stage 2: output registers
            x_rd  <= buf_mem[k];  h_rd  <= coef[tk];
            x_rd2 <= x_rd;        h_rd2 <= h_rd;
            // stage 3: multiply
            p_i <= $signed(x_rd2[2*DW-1:DW]) * h_rd2;
            p_q <= $signed(x_rd2[DW-1:0])    * h_rd2;
            v[3:1] <= v[2:0]; f[3:1] <= f[2:0]; l[3:1] <= l[2:0];
            // stage 4: accumulate; capture the finished sum on the last tap
            if (v[3]) begin
                acc_i <= (f[3] ? 0 : acc_i) + p_i;
                acc_q <= (f[3] ? 0 : acc_q) + p_q;
            end
            res_v <= v[3] && l[3];
            if (v[3] && l[3]) begin
                res_i <= (f[3] ? 0 : acc_i) + p_i;
                res_q <= (f[3] ? 0 : acc_q) + p_q;
            end
            // stage 5: round, saturate, output
            if (res_v) begin
                i_out <= sat((res_i + (1 <<< 16)) >>> 17);
                q_out <= sat((res_q + (1 <<< 16)) >>> 17);
                out_valid <= 1;
            end
        end
    end

    function signed [DW-1:0] sat(input signed [AccW-1:0] x);
        if (x > $signed({1'b0, {(DW-1){1'b1}}}))      sat = {1'b0, {(DW-1){1'b1}}};
        else if (x < $signed({1'b1, {(DW-1){1'b0}}})) sat = {1'b1, {(DW-1){1'b0}}};
        else                                          sat = x[DW-1:0];
    endfunction
endmodule
