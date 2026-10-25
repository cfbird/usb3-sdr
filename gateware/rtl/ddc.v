// Digital down-converter: real 14-bit @ 80 MSPS -> complex 16+16 bit @ 1.25 MSPS (+/-0.5 MHz usable).
// NCO/mixer -> CIC5 /16 -> halfband /2 -> CIC-compensating FIR /2.
// Multipliers: mixer 2 + HB 2 + CFIR 2 = 6 (ECP5-25F has 28).
module ddc #(
    parameter NCO_ROM  = "nco_quarter.hex",
    parameter HB_FILE  = "hb.hex",
    parameter CFIR_FILE = "cfir.hex"
) (
    input  wire               clk,        // ADC DCO, 80 MHz
    input  wire               rst,
    input  wire signed [13:0] adc,        // two's complement
    input  wire [31:0]        phase_inc,  // f_nco = phase_inc * 80 MHz / 2^32
    output wire signed [15:0] i_out,
    output wire signed [15:0] q_out,
    output wire               out_valid
);
    wire signed [17:0] cos_w, sin_w;
    nco #(.ROM_FILE(NCO_ROM)) u_nco (.clk(clk), .phase_inc(phase_inc), .cos_o(cos_w), .sin_o(sin_w));

    // NCO has 4 clocks of latency from phase_inc; data delay doesn't matter for a free-running mixer.
    reg signed [13:0] x;
    reg signed [31:0] pi, pq;
    reg signed [17:0] mi, mq;
    always @(posedge clk) begin
        x  <= adc;
        pi <= x * cos_w;
        pq <= -(x * sin_w);
        // full-scale ADC -> full-scale 18 bit (real->complex costs 6 dB); round to nearest, not floor,
        // or the truncation bias shows up as a DC spur
        mi <= (pi + 32'sd4096) >>> 13;
        mq <= (pq + 32'sd4096) >>> 13;
    end

    wire signed [17:0] ci, cq;
    wire               cv, cvq;
    cic_decim #(.IW(18), .N(5), .LOG2R(4), .OW(18)) u_cic_i (.clk(clk), .rst(rst), .din(mi), .dout(ci), .dout_valid(cv));
    cic_decim #(.IW(18), .N(5), .LOG2R(4), .OW(18)) u_cic_q (.clk(clk), .rst(rst), .din(mq), .dout(cq), .dout_valid(cvq));

    wire signed [17:0] hi, hq;
    wire               hv;
    fir_decim #(.NTAPS(23), .COEF_FILE(HB_FILE), .AW(5)) u_hb (
        .clk(clk), .rst(rst), .i_in(ci), .q_in(cq), .in_valid(cv),
        .i_out(hi), .q_out(hq), .out_valid(hv));

    wire signed [17:0] fi, fq;
    fir_decim #(.NTAPS(59), .COEF_FILE(CFIR_FILE), .AW(6)) u_cfir (
        .clk(clk), .rst(rst), .i_in(hi), .q_in(hq), .in_valid(hv),
        .i_out(fi), .q_out(fq), .out_valid(out_valid));

    // round 18 -> 16 bits with saturation
    function signed [15:0] rnd16(input signed [17:0] v);
        reg signed [18:0] t;
        begin
            t = v + 19'sd2;
            rnd16 = (t[18:17] == 2'b01) ? 16'sh7fff : t[17:2];
        end
    endfunction
    assign i_out = rnd16(fi);
    assign q_out = rnd16(fq);
endmodule
