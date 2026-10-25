// Dual-clock FIFO, Gray-coded pointers, block-RAM storage.
// Read side is first-word-fall-through: rd_data is valid whenever !rd_empty; rd_en pops it.
// Sustains one pop per clock.
module async_fifo #(
    parameter DW = 32,
    parameter AW = 12          // 4096 words (8 EBR); 2^14 = 16 KB*4 fits in the 25F too
) (
    input  wire          wr_clk,
    input  wire          wr_rst,
    input  wire [DW-1:0] wr_data,
    input  wire          wr_en,
    output wire          wr_full,
    output reg           wr_overflow,    // sticky: a write was attempted while full

    input  wire          rd_clk,
    input  wire          rd_rst,
    output wire [DW-1:0] rd_data,
    input  wire          rd_en,
    output wire          rd_empty
);
    reg [DW-1:0] mem [0:(1<<AW)-1];

    // ---------------- write domain ----------------
    reg  [AW:0] wbin = 0, wgray = 0;
    reg  [AW:0] rgray_w1 = 0, rgray_w2 = 0;
    wire [AW:0] wbin_n  = wbin + (wr_en & ~wr_full);
    wire [AW:0] wgray_n = (wbin_n >> 1) ^ wbin_n;
    assign wr_full = (wgray == {~rgray_w2[AW:AW-1], rgray_w2[AW-2:0]});

    always @(posedge wr_clk) begin
        if (wr_en & ~wr_full) mem[wbin[AW-1:0]] <= wr_data;
        if (wr_rst) begin
            wbin <= 0; wgray <= 0; wr_overflow <= 0;
        end else begin
            wbin <= wbin_n; wgray <= wgray_n;
            if (wr_en & wr_full) wr_overflow <= 1;
        end
        {rgray_w2, rgray_w1} <= {rgray_w1, rgray};
    end

    // ---------------- read domain ----------------
    reg  [AW:0] rbin = 0, rgray = 0;
    reg  [AW:0] wgray_r1 = 0, wgray_r2 = 0;
    always @(posedge rd_clk) {wgray_r2, wgray_r1} <= {wgray_r1, wgray};

    wire ram_empty = (rgray == wgray_r2);

    // FWFT: RAM read with the BRAM output register enabled (2 cycles of latency, keeps the slow
    // BRAM clock-to-out off the logic path), then a 4-entry register queue so pops can run every clock.
    reg [DW-1:0] ram_q, ram_q2;
    reg          rv1 = 0, rv2 = 0;          // read issued 1 / 2 cycles ago
    reg [DW-1:0] oq [0:3];
    reg [1:0]    oq_rd = 0, oq_wr = 0;
    reg [2:0]    oq_cnt = 0;

    wire pop   = rd_en & (oq_cnt != 0);
    wire [2:0] committed = oq_cnt + rv1 + rv2 - pop;
    wire issue = ~ram_empty & (committed < 3'd4);
    wire [AW:0] rbin_n = rbin + issue;

    always @(posedge rd_clk) begin
        ram_q  <= mem[rbin[AW-1:0]];
        ram_q2 <= ram_q;
        if (rd_rst) begin
            rbin <= 0; rgray <= 0; rv1 <= 0; rv2 <= 0; oq_rd <= 0; oq_wr <= 0; oq_cnt <= 0;
        end else begin
            rbin  <= rbin_n;
            rgray <= (rbin_n >> 1) ^ rbin_n;
            rv1 <= issue;
            rv2 <= rv1;
            if (rv2) begin oq[oq_wr] <= ram_q2; oq_wr <= oq_wr + 1'b1; end
            if (pop) oq_rd <= oq_rd + 1'b1;
            oq_cnt <= oq_cnt + rv2 - pop;
        end
    end

    assign rd_data  = oq[oq_rd];
    assign rd_empty = (oq_cnt == 0);
endmodule
