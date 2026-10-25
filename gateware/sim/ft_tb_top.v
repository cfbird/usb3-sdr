// Test harness: counter source (80 MHz domain) -> async_fifo -> ft601_245 (100 MHz domain)
module ft_tb_top (
    input  wire        wr_clk,
    input  wire        ft_clk,
    input  wire        rst,
    input  wire        txe_n,
    input  wire        rxf_n,
    input  wire [31:0] din,
    output wire        wr_n, rd_n, oe_n, doe,
    output wire [31:0] dout,
    output wire [31:0] rx_data,
    output wire        rx_valid,
    output wire        ovf,
    output wire        order_err
);
    reg [31:0] cnt = 0;
    wire full;
    always @(posedge wr_clk) if (!rst && !full) cnt <= cnt + 1;
    wire [31:0] q; wire empty, pop; wire [3:0] be;
    async_fifo #(.DW(32), .AW(6)) u_fifo (
        .wr_clk(wr_clk), .wr_rst(rst), .wr_data(cnt), .wr_en(!rst), .wr_full(full), .wr_overflow(ovf),
        .rd_clk(ft_clk), .rd_rst(rst), .rd_data(q), .rd_en(pop), .rd_empty(empty));
    ft601_245 u_ft (.clk(ft_clk), .rst(rst), .txe_n(txe_n), .rxf_n(rxf_n), .wr_n(wr_n), .rd_n(rd_n), .oe_n(oe_n),
        .dout(dout), .be_out(be), .doe(doe), .din(din), .tx_data(q), .tx_empty(empty), .tx_pop(pop),
        .rx_data(rx_data), .rx_valid(rx_valid), .order_err(order_err));
endmodule
