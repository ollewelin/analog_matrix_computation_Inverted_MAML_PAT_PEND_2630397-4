// =============================================================================
// mdio_master.sv : Clause-22 MDIO Master with APB Interface (CORRECTED)
// =============================================================================
// For Efinix T120 FPGA with RTL8211F-CG Ethernet PHY
// Supports IEEE 802.3 Clause-22 MDIO protocol
// CRITICAL FIX: Data changes on MDC FALLING edge, sampled on RISING edge
// =============================================================================

`timescale 1ns / 1ps
`default_nettype none

module mdio_master #(
    parameter int SYS_CLK_HZ = 50_000_000,  // System clock frequency
    parameter int MDC_HZ     = 1_000_000    // MDC frequency (max 2.5 MHz per spec)
) (
    // System
    input  wire         clk,
    input  wire         rst_n,

    // APB Interface (from RISC-V)
    input  wire         psel,
    input  wire         penable,
    input  wire         pwrite,
    input  wire [3:0]   paddr,      // Word address (4 registers)
    input  wire [31:0]  pwdata,
    output logic [31:0] prdata,
    output logic        pready,
    output logic        pslverr,

    // MDIO pins (directly to PHY)
    output logic        mdc,        // Management Data Clock
    input  wire         mdio_i,     // MDIO input
    output logic        mdio_o,     // MDIO output  
    output logic        mdio_oe,    // MDIO output enable (active high)

    // PHY Reset
    output logic        phy_rst_n,  // Connected to RTL8211F PHYRSTB (active low)

    // Interrupt (active high)
    output logic        irq
);

// =============================================================================
// Register Map (APB word addresses)
// =============================================================================
// Offset 0x00: CTRL   - Control Register (RW)
//              [0]    - Start transaction (write 1 to start, auto-clears)
//              [1]    - R/W (1=read, 0=write)
//              [4:2]  - Reserved
//              [9:5]  - PHY Address
//              [14:10]- Register Address
//              [15]   - Reserved
//              [31:16]- Write Data
//
// Offset 0x04: STATUS - Status Register (RO)
//              [0]    - Busy
//              [1]    - Done (sticky, write 1 to clear)
//              [15:2] - Reserved
//              [31:16]- Read Data
//
// Offset 0x08: CONFIG - Configuration Register (RW)
//              [0]    - PHY Reset (0=reset, 1=normal operation)
//              [1]    - Interrupt Enable
//              [31:2] - Reserved
//
// Offset 0x0C: VERSION - Version Register (RO)
//              [7:0]  - Minor version
//              [15:8] - Major version
//              [31:16]- Reserved

localparam logic [3:0] ADDR_CTRL    = 4'h0;
localparam logic [3:0] ADDR_STATUS  = 4'h1;
localparam logic [3:0] ADDR_CONFIG  = 4'h2;
localparam logic [3:0] ADDR_VERSION = 4'h3;

localparam logic [15:0] VERSION = 16'h0100;  // v1.0

// =============================================================================
// MDC Clock Generation
// =============================================================================
localparam int DIV_MAX = (SYS_CLK_HZ / (2 * MDC_HZ)) - 1;
localparam int DIV_BITS = $clog2(DIV_MAX + 1);

logic [DIV_BITS-1:0] div_cnt;
logic                mdc_int;
logic                mdc_d;
logic                mdc_fall;
logic                mdc_rise;

always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        div_cnt <= '0;
        mdc_int <= 1'b0;
        mdc_d   <= 1'b0;
    end else begin
        if (div_cnt >= DIV_MAX[DIV_BITS-1:0]) begin
            div_cnt <= '0;
            mdc_int <= ~mdc_int;
        end else begin
            div_cnt <= div_cnt + 1'b1;
        end
        mdc_d <= mdc_int;
    end
end

assign mdc      = mdc_int;
assign mdc_rise = mdc_int & ~mdc_d;       // LOW->HIGH transition
assign mdc_fall = ~mdc_int & mdc_d;       // HIGH->LOW transition

// =============================================================================
// State Machine
// =============================================================================
typedef enum logic [3:0] {
    S_IDLE,
    S_PREAMBLE,
    S_START,
    S_OPCODE,
    S_PHYAD,
    S_REGAD,
    S_TA_WR,
    S_TA_RD,
    S_WRITE,
    S_READ,
    S_DONE
} state_t;

state_t state;

// =============================================================================
// Control/Status Registers
// =============================================================================
logic        start_req;
logic        rw_reg;           // 1=read, 0=write
logic [4:0]  phy_addr_reg;
logic [4:0]  reg_addr_reg;
logic [15:0] wdata_reg;
logic [15:0] rdata_reg;
logic        phy_rst_reg;
logic        irq_en;
logic        done_flag;
logic        busy;

// Bit shifting
logic [5:0]  bit_cnt;
logic [15:0] shift_reg;
logic        mdio_out_bit;
logic        mdio_out_en;

// =============================================================================
// APB Interface
// =============================================================================
logic apb_write;
logic apb_read;

assign apb_write = psel & penable & pwrite;
assign apb_read  = psel & penable & ~pwrite;
assign pready    = 1'b1;  // No wait states
assign pslverr   = 1'b0;  // No errors

// APB Read
always_comb begin
    prdata = 32'h0;
    case (paddr)
        ADDR_CTRL:    prdata = {wdata_reg, 1'b0, reg_addr_reg, phy_addr_reg, 3'b0, rw_reg, 1'b0};
        ADDR_STATUS:  prdata = {rdata_reg, 14'b0, done_flag, busy};
        ADDR_CONFIG:  prdata = {30'b0, irq_en, phy_rst_reg};
        ADDR_VERSION: prdata = {16'b0, VERSION};
        default:      prdata = 32'h0;
    endcase
end

// APB Write
always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        start_req    <= 1'b0;
        rw_reg       <= 1'b0;
        phy_addr_reg <= 5'b0;
        reg_addr_reg <= 5'b0;
        wdata_reg    <= 16'b0;
        phy_rst_reg  <= 1'b1;  // AUTO-RELEASE: PHY comes out of reset when system reset ends
        irq_en       <= 1'b0;
        done_flag    <= 1'b0;
    end else begin
        // Auto-clear start request
        if (state != S_IDLE)
            start_req <= 1'b0;

        // Set done flag when transaction completes
        if (state == S_DONE && mdc_rise)
            done_flag <= 1'b1;

        if (apb_write) begin
            case (paddr)
                ADDR_CTRL: begin
                    start_req    <= pwdata[0];
                    rw_reg       <= pwdata[1];
                    phy_addr_reg <= pwdata[9:5];
                    reg_addr_reg <= pwdata[14:10];
                    wdata_reg    <= pwdata[31:16];
                end
                ADDR_STATUS: begin
                    // Write 1 to clear done flag
                    if (pwdata[1])
                        done_flag <= 1'b0;
                end
                ADDR_CONFIG: begin
                    phy_rst_reg <= pwdata[0];
                    irq_en      <= pwdata[1];
                end
                default: ;
            endcase
        end
    end
end

// PHY Reset output
assign phy_rst_n = phy_rst_reg;

// =============================================================================
// State Machine - Main Logic
// CRITICAL: Data bits change on MDC FALLING edge
//           Bits are sampled/stable on MDC RISING edge
// =============================================================================
always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        state        <= S_IDLE;
        bit_cnt      <= 6'd0;
        shift_reg    <= 16'd0;
        mdio_out_bit <= 1'b1;
        mdio_out_en  <= 1'b0;
        rdata_reg    <= 16'd0;
        busy         <= 1'b0;
    end else if (mdc_fall) begin  // CHANGED: Update on MDC FALLING edge
        case (state)
            S_IDLE: begin
                mdio_out_en  <= 1'b0;
                mdio_out_bit <= 1'b1;
                busy         <= 1'b0;
                if (start_req) begin
                    state        <= S_PREAMBLE;
                    bit_cnt      <= 6'd31;  // 32 bits of preamble
                    mdio_out_en  <= 1'b1;
                    mdio_out_bit <= 1'b1;
                    busy         <= 1'b1;
                end
            end

            S_PREAMBLE: begin
                // 32 bits of '1'
                if (bit_cnt == 0) begin
                    state        <= S_START;
                    bit_cnt      <= 6'd1;
                    mdio_out_bit <= 1'b0;  // First bit of ST = '01'
                end else begin
                    bit_cnt <= bit_cnt - 1'b1;
                end
            end

            S_START: begin
                // ST field = '01'
                if (bit_cnt == 1) begin
                    mdio_out_bit <= 1'b1;  // Second bit of ST
                    state        <= S_OPCODE;
                    bit_cnt      <= 6'd1;
                end
            end

            S_OPCODE: begin
                // OP field: Read='10', Write='01'
                if (bit_cnt == 1) begin
                    mdio_out_bit <= rw_reg ? 1'b1 : 1'b0;  // Read: '1', Write: '0'
                    bit_cnt      <= 6'd0;
                end else begin
                    mdio_out_bit <= rw_reg ? 1'b0 : 1'b1;  // Read: '0', Write: '1'
                    state        <= S_PHYAD;
                    bit_cnt      <= 6'd4;  // 5 bits, MSB first
                end
            end

            S_PHYAD: begin
                // 5-bit PHY address, MSB first
                mdio_out_bit <= phy_addr_reg[bit_cnt];
                if (bit_cnt == 0) begin
                    state   <= S_REGAD;
                    bit_cnt <= 6'd4;
                end else begin
                    bit_cnt <= bit_cnt - 1'b1;
                end
            end

            S_REGAD: begin
                // 5-bit Register address, MSB first
                mdio_out_bit <= reg_addr_reg[bit_cnt];
                if (bit_cnt == 0) begin
                    if (rw_reg) begin
                        // Read: TA = 2 bit times (PHY responds with '10')
                        state       <= S_TA_RD;
                        bit_cnt     <= 6'd2;  // 2 bit times
                        mdio_out_en <= 1'b0;  // Release bus for PHY
                        mdio_out_bit <= 1'b1; // Idle state
                    end else begin
                        // Write: TA = '10'
                        state        <= S_TA_WR;
                        bit_cnt      <= 6'd1;
                        mdio_out_bit <= 1'b1;  // First TA bit = '1'
                    end
                end else begin
                    bit_cnt <= bit_cnt - 1'b1;
                end
            end

            S_TA_WR: begin
                // Write TA = '10'
                if (bit_cnt == 1) begin
                    mdio_out_bit <= 1'b0;   // Second TA bit = '0'
                    bit_cnt      <= 6'd0;
                end else begin
                    state        <= S_WRITE;
                    bit_cnt      <= 6'd15;  // 16 bits of write data, MSB first
                    mdio_out_bit <= wdata_reg[15];
                end
            end

            S_TA_RD: begin
                // Read TA: bus released, wait for PHY response
                mdio_out_bit <= 1'b1;  // Keep idle
                if (bit_cnt == 0) begin
                    state   <= S_READ;
                    bit_cnt <= 6'd15;  // 16 bits to read
                end else begin
                    bit_cnt <= bit_cnt - 1'b1;
                end
            end

            S_WRITE: begin
                // 16-bit write data, MSB first
                mdio_out_bit <= wdata_reg[bit_cnt];
                if (bit_cnt == 0) begin
                    state       <= S_DONE;
                    mdio_out_en <= 1'b0;
                end else begin
                    bit_cnt <= bit_cnt - 1'b1;
                end
            end

            S_READ: begin
                // During read, we don't drive (mdio_out_en = 0 from TA phase)
                // Data is sampled on mdc_rise below
                if (bit_cnt == 0) begin
                    state <= S_DONE;
                end else begin
                    bit_cnt <= bit_cnt - 1'b1;
                end
            end

            S_DONE: begin
                // Transaction complete
                mdio_out_en  <= 1'b0;
                mdio_out_bit <= 1'b1;
                busy         <= 1'b0;
                // Waits for start_req to go low before returning to IDLE
                if (!start_req) begin
                    state <= S_IDLE;
                end
            end

            default: state <= S_IDLE;
        endcase
    end
end

// =============================================================================
// Data Sampling on MDC RISING edge (for READ operations)
// =============================================================================
always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        shift_reg <= 16'd0;
        rdata_reg <= 16'd0;
    end else if (mdc_rise && state == S_READ) begin
        // Sample MDIO input on MDC rising edge
        shift_reg[bit_cnt] <= mdio_i;
        
        // When last bit is sampled, latch into rdata_reg
        if (bit_cnt == 0) begin
            rdata_reg <= {shift_reg[15:1], mdio_i};
        end
    end
end

// =============================================================================
// MDIO Output (Open-Drain: driven LOW or tristated HIGH)
// =============================================================================
assign mdio_o  = ~mdio_out_bit;  // Output logic (inverted for open-drain)
assign mdio_oe = mdio_out_en;    // Output enable

// =============================================================================
// Interrupt
// =============================================================================
assign irq = done_flag & irq_en;

endmodule
