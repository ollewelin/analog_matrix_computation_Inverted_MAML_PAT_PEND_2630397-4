// =============================================================================
// mdio_master_top.sv : Top-level wrapper for RTL8211F-CG PHY interface
// =============================================================================
// Instantiates mdio_master with tri-state I/O handling for Efinix T120
// Directly connects to F2_MDC, F2_MDIO, F2_RSTB GPIO pins
// =============================================================================

`timescale 1ns / 1ps
`default_nettype none

module mdio_master_top #(
    parameter int SYS_CLK_HZ = 50_000_000,
    parameter int MDC_HZ     = 1_000_000
) (
    // System
    input  wire         clk,
    input  wire         rst_n,

    // APB Interface (from RISC-V / Sapphire SoC)
    input  wire         psel,
    input  wire         penable,
    input  wire         pwrite,
    input  wire [3:0]   paddr,
    input  wire [31:0]  pwdata,
    output wire [31:0]  prdata,
    output wire         pready,
    output wire         pslverr,

    // PHY Interface - Direct to Efinix GPIO
    // Match names from T120F324_A.peri.xml / pinout.csv
    output wire         F2_MDC,         // T18 - GPIOB_TXN01
    input  wire         F2_MDIO_IN,     // R15 - GPIOB_TXN05 input
    output wire         F2_MDIO_OUT,    // R15 - GPIOB_TXN05 output
    output wire         F2_MDIO_OE,     // R15 - GPIOB_TXN05 output enable
    output wire         F2_RSTB,        // T17 - GPIOB_TXP00

    // Interrupt
    output wire         irq
);

// =============================================================================
// Internal signals
// =============================================================================
wire        mdc_int;
wire        mdio_i;
wire        mdio_o;
wire        mdio_oe;
wire        phy_rst_n;

// =============================================================================
// MDIO Master Core
// =============================================================================
mdio_master #(
    .SYS_CLK_HZ (SYS_CLK_HZ),
    .MDC_HZ     (MDC_HZ)
) u_mdio_master (
    .clk        (clk),
    .rst_n      (rst_n),

    // APB
    .psel       (psel),
    .penable    (penable),
    .pwrite     (pwrite),
    .paddr      (paddr),
    .pwdata     (pwdata),
    .prdata     (prdata),
    .pready     (pready),
    .pslverr    (pslverr),

    // MDIO
    .mdc        (mdc_int),
    .mdio_i     (mdio_i),
    .mdio_o     (mdio_o),
    .mdio_oe    (mdio_oe),

    // PHY Reset
    .phy_rst_n  (phy_rst_n),

    // Interrupt
    .irq        (irq)
);

// =============================================================================
// GPIO Connections
// =============================================================================
// MDC is output only
assign F2_MDC = mdc_int;

// MDIO is bidirectional (directly wire to Efinix tri-state GPIO)
assign mdio_i      = F2_MDIO_IN;
assign F2_MDIO_OUT = mdio_o;
assign F2_MDIO_OE  = mdio_oe;

// PHY Reset (active low)
assign F2_RSTB = phy_rst_n;

endmodule

`default_nettype wire
