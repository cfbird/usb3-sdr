// N-stage CIC decimator, M = 1. Gain R^N must be a power of two (R=16, N=5 -> 2^20).
// Integrators run every clock; combs run on the decimated strobe.
module cic_decim #(
    parameter IW = 18,          // input width
    parameter N  = 5,
    parameter LOG2R = 4,        // R = 16
    parameter OW = 18
) (
    input  wire                 clk,
    input  wire                 rst,
    input  wire signed [IW-1:0] din,
    output reg  signed [OW-1:0] dout,
    output reg                  dout_valid
);
    localparam W = IW + N * LOG2R;   // 38 bits for 18/5/4

    reg signed [W-1:0] integ [0:N-1];
    reg signed [W-1:0] comb  [0:N-1];
    reg signed [W-1:0] dly   [0:N-1];
    reg [LOG2R-1:0]    cnt;
    reg                strobe;
    integer i;

    always @(posedge clk) begin
        if (rst) begin
            cnt <= 0; strobe <= 0; dout_valid <= 0;
            for (i = 0; i < N; i = i + 1) begin integ[i] <= 0; comb[i] <= 0; dly[i] <= 0; end
        end else begin
            integ[0] <= integ[0] + {{(W-IW){din[IW-1]}}, din};
            for (i = 1; i < N; i = i + 1) integ[i] <= integ[i] + integ[i-1];

            cnt    <= cnt + 1'b1;
            strobe <= (cnt == {LOG2R{1'b1}});
            dout_valid <= 0;
            if (strobe) begin
                // pipelined combs: stage i differences stage i-1's previous outputs (1 output of latency per stage)
                comb[0] <= integ[N-1] - dly[0];  dly[0] <= integ[N-1];
                for (i = 1; i < N; i = i + 1) begin
                    comb[i] <= comb[i-1] - dly[i];
                    dly[i]  <= comb[i-1];
                end
            end
            if (strobe) begin
                dout <= sat_round(comb[N-1]);
                dout_valid <= 1;
            end
        end
    end
    // round to nearest at the output width (gain R^N = 2^(W-IW)), saturating the +0.5 LSB edge case
    function signed [OW-1:0] sat_round(input signed [W-1:0] v);
        reg [W:0] t, half;
        begin
            // explicit sign extension: a concatenation is unsigned and would zero-extend v
            half = 0; half[W-OW-1] = 1'b1;
            t = {v[W-1], v} + half;
            sat_round = (t[W:W-1] == 2'b01) ? {1'b0, {(OW-1){1'b1}}} : t[W-1 -: OW];
        end
    endfunction
endmodule
