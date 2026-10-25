// Power-up sequencer on the ECP5 internal oscillator (~2.4 MHz): puts the AD9649 in standby, programs the
// LMK61E2 to 80 MHz over I2C, then enables the ADC (1.8 V CMOS, two's complement). Runs from a small
// op table, so the sequence is data, not logic.
//
// Op word: [23:22] op (0 SPI write, 1 I2C write, 2 wait, 3 end) | [21:8] address | [7:0] data
//   SPI : AD9649 3-wire write, 16-bit instruction {R/W=0, W1:W0=00, A12:A0} + data (DS Rev B, SPI section)
//   I2C : LMK61E2 @ 0x58, {reg, data} (SNAS674C 7.5)
//   wait: data * 1024 boot clocks (~0.42 ms per unit at 2.4 MHz)
module boot_seq (
    input  wire clk,
    input  wire rst,
    // AD9649 SPI (3-wire, write-only here)
    output reg  adc_csb,
    output reg  adc_sclk,
    output reg  adc_sdio,
    // LMK61E2 I2C, open drain: *_oe = 1 pulls the line low
    output reg  scl_oe,
    output reg  sda_oe,
    input  wire sda_in,
    output reg  done,
    output reg  i2c_nack           // sticky: a byte was not acknowledged
);
    localparam OP_SPI = 2'd0, OP_I2C = 2'd1, OP_WAIT = 2'd2, OP_END = 2'd3;
    localparam LMK_ADDR = 7'h58;

    reg [23:0] rom [0:15];
    initial begin
        rom[0]  = {OP_WAIT, 14'h0000, 8'd25};   // ~10 ms after configuration
        rom[1]  = {OP_SPI,  14'h0008, 8'h02};   // AD9649 0x08 = standby
        rom[2]  = {OP_SPI,  14'h00FF, 8'h01};   // transfer shadow registers
        rom[3]  = {OP_I2C,  14'd21,   8'h02};   // LMK R21 OUT_SEL = LVDS (reset default is LVPECL)
        rom[4]  = {OP_I2C,  14'd22,   8'h00};   // R22 OUT_DIV[8] = 0
        rom[5]  = {OP_I2C,  14'd23,   8'd60};   // R23 OUT_DIV = 60  -> 4800 MHz / 60 = 80 MHz
        rom[6]  = {OP_I2C,  14'd25,   8'h00};   // R25 NDIV[11:8] = 0
        rom[7]  = {OP_I2C,  14'd26,   8'd48};   // R26 NDIV = 48 x 100 MHz PFD (doubler on, reset default) = 4800 MHz
        rom[8]  = {OP_I2C,  14'd72,   8'h02};   // R72 SWR2PLL: recalibrate VCO and reset dividers
        rom[9]  = {OP_WAIT, 14'h0000, 8'd50};   // ~20 ms for VCO cal + lock
        rom[10] = {OP_SPI,  14'h0014, 8'h81};   // AD9649 0x14: 1.8 V CMOS, two's complement
        rom[11] = {OP_SPI,  14'h0008, 8'h00};   // chip run
        rom[12] = {OP_SPI,  14'h00FF, 8'h01};   // transfer
        rom[13] = {OP_WAIT, 14'h0000, 8'd5};
        rom[14] = {OP_END,  22'h0};
        rom[15] = {OP_END,  22'h0};
    end

    reg [3:0]  pc;
    reg [23:0] op;
    reg [3:0]  st;
    reg [17:0] cnt;
    reg [5:0]  bitn;
    reg [23:0] sh;         // SPI: 24 bits out; I2C: 3 bytes {addr+W, reg, data}
    reg [1:0]  byten;
    reg [1:0]  q;          // I2C quarter-bit phase
    reg [2:0]  qdiv;

    localparam S_FETCH = 0, S_DISPATCH = 1, S_WAIT = 2, S_SPI = 3, S_SPI_END = 4,
               S_I2C_START = 5, S_I2C_BIT = 6, S_I2C_ACK = 7, S_I2C_STOP = 8, S_DONE = 9;

    always @(posedge clk) begin
        if (rst) begin
            pc <= 0; st <= S_FETCH; done <= 0; i2c_nack <= 0;
            adc_csb <= 1; adc_sclk <= 0; adc_sdio <= 0; scl_oe <= 0; sda_oe <= 0;
        end else case (st)
        S_FETCH:    begin op <= rom[pc]; pc <= pc + 1'b1; st <= S_DISPATCH; end
        S_DISPATCH: case (op[23:22])
            OP_WAIT: begin cnt <= {op[7:0], 10'd0}; st <= S_WAIT; end
            OP_SPI:  begin sh <= {3'b000, op[20:8], op[7:0]}; adc_sdio <= 1'b0; bitn <= 24; adc_csb <= 0; adc_sclk <= 0; st <= S_SPI; end  // first bit (R/W=0) preset
            OP_I2C:  begin sh <= {LMK_ADDR, 1'b0, op[15:8], op[7:0]}; byten <= 0; qdiv <= 0; q <= 0; st <= S_I2C_START; end
            default: begin done <= 1; st <= S_DONE; end
        endcase
        S_WAIT: if (cnt == 0) st <= S_FETCH; else cnt <= cnt - 1'b1;

        // SPI mode 0: SDIO changes on the falling edge, the ADC samples on the rising edge
        S_SPI: begin
            if (!adc_sclk) adc_sclk <= 1;
            else begin
                adc_sclk <= 0;
                if (bitn == 1) st <= S_SPI_END;
                else begin adc_sdio <= sh[22]; sh <= {sh[22:0], 1'b0}; end
                bitn <= bitn - 1'b1;
            end
        end
        S_SPI_END: begin adc_csb <= 1; adc_sdio <= 0; st <= S_FETCH; end

        // I2C at ~100 kHz: 4 quarter phases of 6 boot clocks each
        S_I2C_START, S_I2C_BIT, S_I2C_ACK, S_I2C_STOP: begin
            qdiv <= qdiv + 1'b1;
            if (qdiv == 3'd5) begin
                qdiv <= 0;
                q <= q + 1'b1;
                case (st)
                S_I2C_START: case (q)          // SDA falls while SCL high
                    2'd0: begin sda_oe <= 0; scl_oe <= 0; end
                    2'd1: sda_oe <= 1;
                    2'd2: scl_oe <= 1;
                    2'd3: begin bitn <= 8; st <= S_I2C_BIT; end
                endcase
                S_I2C_BIT: case (q)
                    2'd0: begin sda_oe <= ~sh[23]; sh <= {sh[22:0], 1'b0}; end
                    2'd1: scl_oe <= 0;
                    2'd2: ;
                    2'd3: begin scl_oe <= 1; bitn <= bitn - 1'b1; if (bitn == 1) st <= S_I2C_ACK; end
                endcase
                S_I2C_ACK: case (q)
                    2'd0: sda_oe <= 0;             // release SDA for ACK
                    2'd1: scl_oe <= 0;
                    2'd2: if (sda_in) i2c_nack <= 1;
                    2'd3: begin
                        scl_oe <= 1;
                        byten <= byten + 1'b1;
                        if (byten == 2) st <= S_I2C_STOP; else begin bitn <= 8; st <= S_I2C_BIT; end
                    end
                endcase
                S_I2C_STOP: case (q)           // SDA rises while SCL high
                    2'd0: sda_oe <= 1;
                    2'd1: scl_oe <= 0;
                    2'd2: sda_oe <= 0;
                    2'd3: st <= S_FETCH;
                endcase
                default: ;
                endcase
            end
        end
        S_DONE: ;
        default: st <= S_FETCH;
        endcase
    end
endmodule
