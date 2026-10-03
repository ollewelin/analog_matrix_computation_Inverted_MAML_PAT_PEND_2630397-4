// =============================================================================
// t120_t20_bus_apb3.sv : APB3 Slave Peripheral for T120 <-> T20 Custom Bus
// =============================================================================
// Memory Map (Offset from APB Base, e.g. 0x0001_0000):
// 0x00: TX_CTRL (RW)
//       [0]   : T20_CLK9 manual state
//       [4:1] : TX[3:0] (TX11_P1, TX11_N1, TX12_P1, TX12_N1)
// 0x04: RX_DATA (RO)
//       [7:0] : RX[7:0] (RX00_P1..RX03_N1)
// 0x08: CRESET_CTRL (RW)
//       [0]   : T20_CRESET_N output control (1=release, 0=assert reset)
// =============================================================================

`timescale 1ns / 1ps
`default_nettype none

module t120_t20_bus_apb3 (
    input  wire         pclk,
    input  wire         presetn,
    input  wire         psel,
    input  wire         penable,
    input  wire         pwrite,
    input  wire [7:0]   paddr,
    input  wire [31:0]  pwdata,
    output logic [31:0] prdata,
    output logic        pready,
    output logic        pslverr,

    // Physical bus lines to T20
    output logic        t20_clk9,
    output logic [3:0]  t20_tx,
    input  wire  [7:0]  t20_rx,
    output logic        t20_creset_n
);

    assign pready  = 1'b1;
    assign pslverr = 1'b0;

    logic [4:0] tx_ctrl_reg;
    logic       creset_reg;

    assign t20_clk9     = tx_ctrl_reg[0];
    assign t20_tx       = tx_ctrl_reg[4:1];
    assign t20_creset_n = creset_reg;

    always_ff @(posedge pclk or negedge presetn) begin
        if (!presetn) begin
            tx_ctrl_reg <= 5'b00000;
            creset_reg  <= 1'b1; // Default: out of reset
        end else if (psel && penable && pwrite) begin
            case (paddr[3:0])
                4'h0: tx_ctrl_reg <= pwdata[4:0];
                4'h8: creset_reg  <= pwdata[0];
                default: ;
            endcase
        end
    end

    always_comb begin
        case (paddr[3:0])
            4'h0: prdata = {27'd0, tx_ctrl_reg};
            4'h4: prdata = {24'd0, t20_rx};
            4'h8: prdata = {31'd0, creset_reg};
            default: prdata = 32'd0;
        endcase
    end

endmodule
