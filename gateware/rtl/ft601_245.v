// FT601 "245 synchronous FIFO" bus master, 32-bit, clocked by the FT601's 100 MHz CLK.
//
// Timing (FT600Q/FT601Q DS v1.05 Table 4.2): FT601 outputs are valid only 3.0 ns before CLK, so TXE_N,
// RXF_N and DATA are captured in I/O registers and the master learns one cycle late whether a word
// was taken. A word moves on an edge where WR_N and TXE_N are both low (or RD_N and RXF_N).
//
// Write side: words are staged in an 8-entry replay buffer. Every presented word is judged one cycle
// later against the registered TXE_N; a rejected word rewinds the send pointer so it is presented again.
// Unavoidable corner: if TXE_N is high for exactly one edge, the word after the rejected one may be
// taken first. That is detected and flagged in order_err (sticky), never silently passed.
//
// Read side (host -> FPGA): RD_N is deasserted one cycle after RXF_N rises; the FT601 ignores RD_N
// while RXF_N is high, so the late stop is harmless.
// Tri-state buffers live in the top level; this module exposes dout/doe/din.
module ft601_245 (
    input  wire        clk,
    input  wire        rst,
    // FT601 pins
    input  wire        txe_n,
    input  wire        rxf_n,
    output reg         wr_n,
    output reg         rd_n,
    output reg         oe_n,
    output reg  [31:0] dout,
    output reg  [3:0]  be_out,
    output reg         doe,          // 1: FPGA drives DATA/BE
    input  wire [31:0] din,
    // FPGA -> host stream (FWFT source)
    input  wire [31:0] tx_data,
    input  wire        tx_empty,
    output wire        tx_pop,
    // host -> FPGA words
    output reg  [31:0] rx_data,
    output reg         rx_valid,
    output reg         order_err
);
    // ---------------- input capture (ECP5 I/O registers when ECP5_IOREG is defined, behavioral otherwise)
    wire        txe_q, rxf_q;
    wire [31:0] din_q;
`ifdef ECP5_IOREG
    IFS1P3DX u_txe (.D(txe_n), .SP(1'b1), .SCLK(clk), .CD(1'b0), .Q(txe_q));
    IFS1P3DX u_rxf (.D(rxf_n), .SP(1'b1), .SCLK(clk), .CD(1'b0), .Q(rxf_q));
    genvar g;
    generate for (g = 0; g < 32; g = g + 1) begin : g_din
        IFS1P3DX u_d (.D(din[g]), .SP(1'b1), .SCLK(clk), .CD(1'b0), .Q(din_q[g]));
    end endgenerate
`else
    reg txe_r = 1, rxf_r = 1;
    reg [31:0] din_r;
    always @(posedge clk) begin txe_r <= txe_n; rxf_r <= rxf_n; din_r <= din; end
    assign txe_q = txe_r; assign rxf_q = rxf_r; assign din_q = din_r;
`endif

    // ---------------- replay buffer: [conf, send) presented-unconfirmed, [send, fill) not yet sent
    reg [31:0] rb [0:7];
    reg [3:0]  conf = 0, send = 0, fill = 0;   // 4-bit pointers over 8 entries (wrap bit included)
    reg [3:0]  cur_idx, prev_idx;               // word on the bus last cycle / the cycle before
    reg        prev_v = 0;                       // a word was on the bus the cycle before last

    wire [3:0] fill_lvl = fill - conf;
    assign tx_pop = !tx_empty && (fill_lvl < 4'd8) && !rst;

    localparam S_WR = 3'd0, S_TURN_R = 3'd1, S_RD_OE = 3'd2, S_RD = 3'd3, S_TURN_W = 3'd4;
    reg [2:0] st = S_WR;
    reg       rd_prev = 1;                        // rd_n during the previous cycle

    always @(posedge clk) begin
        rx_valid <= 0;
        if (rst) begin
            st <= S_WR; wr_n <= 1; rd_n <= 1; oe_n <= 1; doe <= 0; be_out <= 4'hf;
            conf <= 0; send <= 0; fill <= 0; prev_v <= 0; rd_prev <= 1; order_err <= 0;
        end else begin
            // refill from the stream FIFO
            if (tx_pop) begin rb[fill[2:0]] <= tx_data; fill <= fill + 1'b1; end

            // judge the word that was on the bus two edges ago, using TXE_N sampled at the last edge
            begin : judge
                reg [3:0] send_n;
                reg       rewind;
                send_n = send; rewind = 0;
                if (prev_v) begin
                    if (!txe_q) begin
                        if (prev_idx == conf) conf <= conf + 1'b1;
                        else order_err <= 1;                         // taken out of order (1-cycle TXE_N pulse)
                    end else if ((prev_idx - conf) < (send - conf)) begin
                        send_n = prev_idx; rewind = 1;               // rejected: present it again
                    end
                end
                prev_v   <= !wr_n;
                prev_idx <= cur_idx;

                // drive the next word: needs last-seen space, no rewind this edge, and a word to send
                // (no rewind => send_n == send, so the data mux never waits on the judge logic)
                if (st == S_WR && rxf_q && !rewind && !txe_q && send != fill) begin
                    dout <= rb[send[2:0]]; cur_idx <= send; wr_n <= 0; send <= send + 1'b1;
                end else begin
                    wr_n <= 1; send <= send_n;
                end
            end

            // bus ownership / read path
            rd_prev <= rd_n;
            case (st)
            S_WR: begin
                doe <= 1;
                if (!rxf_q) begin st <= S_TURN_R; end                // host has data: finish this cycle, release
            end
            S_TURN_R: begin
                if (prev_v || !wr_n) ;                               // wait until no write is in flight
                else begin doe <= 0; st <= S_RD_OE; end
            end
            S_RD_OE: begin oe_n <= 0; st <= S_RD; end
            S_RD: begin
                rd_n <= rxf_q;                                       // read while the FT601 reports data
                if (!rd_prev && !rxf_q) begin rx_data <= din_q; rx_valid <= 1; end
                if (rxf_q && rd_n) begin oe_n <= 1; st <= S_TURN_W; end
            end
            S_TURN_W: st <= S_WR;
            default:  st <= S_WR;
            endcase
        end
    end
endmodule
