// 32-bit phase accumulator NCO, quarter-wave ROM (4096 x 18), 14-bit effective phase.
// Latency: 3 clocks from the phase accumulator to sin/cos (4 from phase_inc).
module nco #(
    parameter ROM_FILE = "nco_quarter.hex"
) (
    input  wire               clk,
    input  wire [31:0]        phase_inc,
    output reg  signed [17:0] cos_o,
    output reg  signed [17:0] sin_o
);
    reg [17:0] rom [0:4095];
    initial $readmemh(ROM_FILE, rom);

    reg [31:0] acc = 0;
    always @(posedge clk) acc <= acc + phase_inc;

    // sin uses phase p, cos uses p + quarter turn
    wire [13:0] ps = acc[31:18];
    wire [13:0] pc = acc[31:18] + 14'd4096;

    // quadrant mirror: odd quadrants read the table backwards (exact thanks to the half-sample offset)
    wire [11:0] as = ps[12] ? ~ps[11:0] : ps[11:0];
    wire [11:0] ac = pc[12] ? ~pc[11:0] : pc[11:0];

    // ROM read + BRAM output register (keeps the slow BRAM clock-to-out off the negate path)
    reg [17:0] rs, rc, rs2, rc2;
    reg        ns, nc, ns2, nc2;
    always @(posedge clk) begin
        rs  <= rom[as];  ns  <= ps[13];
        rc  <= rom[ac];  nc  <= pc[13];
        rs2 <= rs;       ns2 <= ns;
        rc2 <= rc;       nc2 <= nc;
        sin_o <= ns2 ? -$signed(rs2) : $signed(rs2);
        cos_o <= nc2 ? -$signed(rc2) : $signed(rc2);
    end
endmodule
