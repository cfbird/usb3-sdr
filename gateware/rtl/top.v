// usb3-sdr Rev A top level (LFE5U-25F/45F-6BG256C).
// Clock domains:
//   clk_adc  80 MHz  AD9649 DCO (ball K1, PCLKT7_0): capture, DDC, raw packer, FIFO write
//   clk_ft  100 MHz  FT601 CLK  (ball K16, PCLKT2_0): FT601 bus, command registers, FIFO read
//   clk_boot ~2.4 MHz internal OSCG: power-up sequencing (exists before the ADC clock is valid)
//
// Host protocol (32-bit words, host -> FPGA): 0xC0 | addr[7:0] | data[15:0] in bits [31:24]/[23:16]/[15:0]
//   0x00 CTRL   [0] stream enable  [1] raw mode (0 = DDC IQ)  [2] clear overflow
//   0x01 NCO_LO, 0x02 NCO_HI       phase_inc = f * 2^32 / 80 MHz
//   0x03 COMMIT                    any write: CTRL/NCO take effect in the ADC domain
//   0x04 RF     [0] 20 dB pad relay [1] LNA relay [2] LNA power
//   0x05 STATUS_REQ                any write: one status word is sent (only while streaming is off)
// FPGA -> host: raw mode = two 16-bit samples per word (older sample in [15:0]);
//   DDC mode = {Q[15:0], I[15:0]} at 1.25 MSPS; status = 0x5A000000 | {order_err, i2c_nack, boot_done, overflow, streaming}.
module top (
    // AD9649
    input  wire        adc_dco,
    input  wire [13:0] adc_d,
    input  wire        adc_or,
    output wire        adc_csb,
    output wire        adc_sclk,
    output wire        adc_sdio,
    // LMK61E2
    inout  wire        lmk_scl,
    inout  wire        lmk_sda,
    // FT601
    input  wire        ft_clk,
    inout  wire [31:0] ft_data,
    inout  wire [3:0]  ft_be,
    input  wire        ft_txe_n,
    input  wire        ft_rxf_n,
    output wire        ft_wr_n,
    output wire        ft_rd_n,
    output wire        ft_oe_n,
    output wire        ft_reset_n,
    output wire        ft_wakeup_n,
    // RF control
    output wire        rly_pad,
    output wire        rly_lna,
    output wire        lna_en,
    input  wire        ref10m,
    output wire [1:0]  led
);
    // ------------------------------------------------------------------ boot domain
    wire clk_boot;
    OSCG #(.DIV(128)) u_osc (.OSC(clk_boot));       // ~310 MHz / 128

    reg [7:0] por_boot = 0;
    always @(posedge clk_boot) if (!por_boot[7]) por_boot <= por_boot + 1'b1;
    wire rst_boot = !por_boot[7];

    wire scl_oe, sda_oe, boot_done, i2c_nack;
    boot_seq u_boot (
        .clk(clk_boot), .rst(rst_boot),
        .adc_csb(adc_csb), .adc_sclk(adc_sclk), .adc_sdio(adc_sdio),
        .scl_oe(scl_oe), .sda_oe(sda_oe), .sda_in(lmk_sda),
        .done(boot_done), .i2c_nack(i2c_nack));
    assign lmk_scl = scl_oe ? 1'b0 : 1'bz;
    assign lmk_sda = sda_oe ? 1'b0 : 1'bz;

    // ------------------------------------------------------------------ FT601 domain reset
    reg [7:0] por_ft = 0;
    always @(posedge ft_clk) if (!por_ft[7]) por_ft <= por_ft + 1'b1;
    wire rst_ft = !por_ft[7];

    wire status_sent, tx_pop, ft_order_err;

    // ------------------------------------------------------------------ ADC domain
    wire clk_adc = adc_dco;

    // capture in the I/O cell registers (ECP5 IFS1P3DX)
    wire [14:0] cap_in = {adc_or, adc_d};
    wire [14:0] cap;
    genvar g;
    generate for (g = 0; g < 15; g = g + 1) begin : g_cap
        IFS1P3DX u_ff (.D(cap_in[g]), .SP(1'b1), .SCLK(clk_adc), .CD(1'b0), .Q(cap[g]));
    end endgenerate

    reg [2:0] boot_sync_adc = 0;
    always @(posedge clk_adc) boot_sync_adc <= {boot_sync_adc[1:0], boot_done};
    wire rst_adc = !boot_sync_adc[2];

    // control registers from the FT domain: quasi-static values latched on a synchronized commit toggle
    wire [15:0] ctrl_ft;
    wire [31:0] nco_ft;
    wire        commit_tgl_ft;
    reg  [2:0]  commit_sync = 0;
    reg  [15:0] ctrl_adc = 0;
    reg  [31:0] nco_adc = 0;
    always @(posedge clk_adc) begin
        commit_sync <= {commit_sync[1:0], commit_tgl_ft};
        if (commit_sync[2] ^ commit_sync[1]) begin ctrl_adc <= ctrl_ft; nco_adc <= nco_ft; end
    end
    wire stream_en = ctrl_adc[0] & !rst_adc;
    wire raw_mode  = ctrl_adc[1];
    wire clr_ovf   = ctrl_adc[2];

    wire signed [15:0] di, dq;
    wire               dv;
    ddc u_ddc (.clk(clk_adc), .rst(rst_adc), .adc(cap[13:0]), .phase_inc(nco_adc),
               .i_out(di), .q_out(dq), .out_valid(dv));

    // raw packer: two sign-extended samples per word -> 40 Mwords/s = 160 MB/s
    reg [15:0] raw_lo;
    reg        raw_half = 0;
    reg [31:0] wdata;
    reg        wen = 0;
    always @(posedge clk_adc) begin
        wen <= 0;
        if (raw_mode) begin
            raw_half <= ~raw_half;
            if (!raw_half) raw_lo <= {{2{cap[13]}}, cap[13:0]};
            else begin wdata <= {{2{cap[13]}}, cap[13:0], raw_lo}; wen <= stream_en; end
        end else if (dv) begin
            wdata <= {dq, di}; wen <= stream_en;
        end
    end

    wire fifo_full, fifo_ovf;
    wire [31:0] fifo_q;
    wire fifo_empty, fifo_pop;
    async_fifo #(.DW(32), .AW(12)) u_fifo (
        .wr_clk(clk_adc), .wr_rst(rst_adc | clr_ovf), .wr_data(wdata), .wr_en(wen),
        .wr_full(fifo_full), .wr_overflow(fifo_ovf),
        .rd_clk(ft_clk), .rd_rst(rst_ft), .rd_data(fifo_q), .rd_en(fifo_pop), .rd_empty(fifo_empty));

    // ------------------------------------------------------------------ FT601 domain
    reg [2:0] ovf_sync = 0, boot_sync_ft = 0;
    always @(posedge ft_clk) begin
        ovf_sync     <= {ovf_sync[1:0], fifo_ovf};
        boot_sync_ft <= {boot_sync_ft[1:0], boot_done};
    end

    // command registers
    reg [15:0] r_ctrl = 0, r_nco_lo = 0, r_nco_hi = 0, r_rf = 0;
    reg        r_commit = 0, status_req = 0;
    wire [31:0] rx_data;
    wire        rx_valid;
    always @(posedge ft_clk) begin
        if (rx_valid && rx_data[31:24] == 8'hC0) case (rx_data[23:16])
            8'h00: r_ctrl   <= rx_data[15:0];
            8'h01: r_nco_lo <= rx_data[15:0];
            8'h02: r_nco_hi <= rx_data[15:0];
            8'h03: r_commit <= ~r_commit;
            8'h04: r_rf     <= rx_data[15:0];
            8'h05: status_req <= 1;
            default: ;
        endcase
        if (status_sent) status_req <= 0;
    end
    assign ctrl_ft = r_ctrl;
    assign nco_ft = {r_nco_hi, r_nco_lo};
    assign commit_tgl_ft = r_commit;

    // TX source: the sample FIFO, or one status word when streaming is off
    wire        streaming = r_ctrl[0];
    wire [31:0] status_word = {8'h5A, 19'd0, ft_order_err, i2c_nack, boot_sync_ft[2], ovf_sync[2], streaming};
    wire        use_status = status_req && !streaming;
    wire [31:0] tx_data  = use_status ? status_word : fifo_q;
    wire        tx_empty = use_status ? 1'b0 : fifo_empty;
    assign      status_sent = tx_pop && use_status;
    assign fifo_pop = tx_pop && !use_status;

    wire [31:0] dout;
    wire [3:0]  be_out;
    wire        doe;
    ft601_245 u_ft (
        .clk(ft_clk), .rst(rst_ft),
        .txe_n(ft_txe_n), .rxf_n(ft_rxf_n), .wr_n(ft_wr_n), .rd_n(ft_rd_n), .oe_n(ft_oe_n),
        .dout(dout), .be_out(be_out), .doe(doe), .din(ft_data),
        .tx_data(tx_data), .tx_empty(tx_empty), .tx_pop(tx_pop),
        .rx_data(rx_data), .rx_valid(rx_valid), .order_err(ft_order_err));
    assign ft_data = doe ? dout   : 32'bz;
    assign ft_be   = doe ? be_out : 4'bz;
    assign ft_reset_n  = !rst_boot;          // from the internal oscillator: FT601 CLK may not run while in reset
    assign ft_wakeup_n = 1'b1;

    assign rly_pad = r_rf[0];
    assign rly_lna = r_rf[1];
    assign lna_en  = r_rf[2];
    assign led = {ovf_sync[2], boot_sync_ft[2]};
endmodule
