/**
 * uart_mini_apb3.sv - APB3 slave wrapper for uart_mini
 * 
 * Based on Efinix apb3_cam reference implementation
 * Implements proper APB3 state machine (IDLE → SETUP → ACCESS)
 * 
 * Register Map (at base address IO_APB_SLAVE_0_INPUT = 0xf8100000):
 * 0x00: UART_CTRL (read/write)
 *       [0] = tx_write (write strobe)
 *       [7:1] = unused
 * 
 * 0x04: UART_STATUS (read-only)
 *       [0] = tx_empty
 *       [1] = tx_full
 *       [2] = rx_empty
 *       [3] = rx_full
 *       [7:4] = unused
 * 
 * 0x08: UART_TX_DATA (write-only)
 *       [7:0] = tx_data byte to transmit
 * 
 * 0x0C: UART_RX_DATA (read-only)
 *       [7:0] = rx_data byte received
 * 
 * 0x10: UART_RX_CTRL (write-only)
 *       [0] = rx_read (strobe to pop from RX FIFO)
 */

module uart_mini_apb3 #(
    parameter CLK_FREQ_HZ = 50_000_000,
    parameter BAUD_RATE = 9600
) (
    // APB3 slave interface
    input  logic pclk,
    input  logic presetn,
    input  logic psel,
    input  logic penable,
    input  logic pwrite,
    input  logic [31:0] paddr,
    input  logic [31:0] pwdata,
    output logic [31:0] prdata,
    output logic pready,
    output logic pslverr,
    
    // UART physical pins
    output logic uart_txd,
    input  logic uart_rxd,
    
    // DEBUG: TX activity indicator (pulses when TX write occurs)
    output logic debug_tx_activity,
    output logic debug_any_write,    // DEBUG: ANY APB3 write detected
    
    // DEBUG: APB3 Protocol Analyzer Probes
    output logic [1:0]  debug_bus_state,    // Current state: 00=IDLE, 01=SETUP, 10=ACCESS
    output logic        debug_psel_in,      // APB3 PSEL input
    output logic        debug_penable_in,   // APB3 PENABLE input
    output logic        debug_pwrite_in,    // APB3 PWRITE input
    output logic        debug_act_write,    // Write strobe (fires in ACCESS only)
    output logic        debug_act_read,     // Read strobe (fires in ACCESS only)
    output logic        debug_slave_ready,  // Captured strobe for PREADY
    output logic        debug_pready_out,   // PREADY output
    output logic [7:0]  debug_reg_addr      // Register address being accessed
);

    // APB3 register addresses (offset from base)
    localparam REG_CTRL        = 32'h00;
    localparam REG_STATUS      = 32'h04;
    localparam REG_TX_DATA     = 32'h08;
    localparam REG_RX_DATA     = 32'h0C;
    localparam REG_RX_CTRL     = 32'h10;
    
    // Control signals for uart_mini
    logic [7:0] tx_data_val, rx_data_val;
    logic tx_write_strobe, rx_read_strobe;
    logic tx_empty, tx_full, rx_empty, rx_full;
    logic [4:0] tx_count, rx_count;
    
    // Instantiate uart_mini core
    uart_mini #(
        .CLK_FREQ_HZ(CLK_FREQ_HZ),
        .BAUD_RATE(BAUD_RATE),
        .FIFO_DEPTH(32)
    ) uart_inst (
        .clk(pclk),
        .rst_n(presetn),
        .uart_txd(uart_txd),
        .uart_rxd(uart_rxd),
        .tx_data(tx_data_val),
        .tx_write(tx_write_strobe),
        .tx_empty(tx_empty),
        .tx_full(tx_full),
        .rx_data(rx_data_val),
        .rx_read(rx_read_strobe),
        .rx_empty(rx_empty),
        .rx_full(rx_full),
        .tx_count(tx_count),
        .rx_count(rx_count)
    );
    
    // APB3 State Machine (from Efinix reference: apb3_cam.v)
    localparam [1:0] IDLE   = 2'b00,
                     SETUP  = 2'b01,
                     ACCESS = 2'b10;
    
    reg [1:0]  bus_state, bus_next;
    
    // APB3 control signals
    wire act_write;     // Write strobe - triggered when in ACCESS state
    wire act_read;      // Read strobe - triggered when in ACCESS state
    reg slave_ready;    // Latches transaction strobe for PREADY (sequential, 1-cycle delay)
    
    // State machine: IDLE → SETUP (PSEL=1, PENABLE=0) → ACCESS (PSEL=1, PENABLE=1) → IDLE
    always @(posedge pclk or negedge presetn) begin
        if (!presetn)
            bus_state <= IDLE;
        else
            bus_state <= bus_next;
    end
    
    always @(*) begin
        bus_next = bus_state;
        case (bus_state)
            IDLE:
                // Enter SETUP when PSEL asserted (uart_mini is the ONLY slave on this port)
                if (psel)
                    bus_next = SETUP;
                else
                    bus_next = IDLE;
            SETUP:
                // Enter ACCESS when PENABLE asserted (PSEL must stay high)
                if (psel && penable)
                    bus_next = ACCESS;
                else if (!psel)
                    bus_next = IDLE;
                else
                    bus_next = SETUP;
            ACCESS:
                bus_next = IDLE;  // Zero wait states - always 1 cycle
            default:
                bus_next = IDLE;
        endcase
    end
    
    // Write and read strobes only valid during ACCESS state
    assign act_write  = pwrite & (bus_state == ACCESS);
    assign act_read   = !pwrite & (bus_state == ACCESS);
    
    // PREADY: Sequential strobe detection with combinational gating (per Efinix reference)
    always @(posedge pclk or negedge presetn) begin
        if (!presetn)
            slave_ready <= 1'b0;
        else
            slave_ready <= act_write | act_read;
    end
    
    // APB3 control signals
    assign pslverr = 1'b0;  // No slave error
    assign pready = (bus_state == ACCESS);  // Zero wait states - immediate PREADY
    
    // Address decoder - extract register offset from lower bits
    logic [7:0] reg_addr;
    assign reg_addr = paddr[7:0];
    
    // Write path - strobe generation for one-cycle pulses
    // CRITICAL: Only execute writes during ACCESS state (when PSEL & PENABLE both high)
    always_ff @(posedge pclk or negedge presetn) begin
        if (!presetn) begin
            tx_write_strobe <= 1'b0;
            rx_read_strobe <= 1'b0;
            tx_data_val <= 8'h00;
        end else begin
            // Default: clear strobes (one-cycle pulse)
            tx_write_strobe <= 1'b0;
            rx_read_strobe <= 1'b0;
            
            // APB3 write - only execute during ACCESS state
            if (act_write) begin
                case (reg_addr)
                    REG_TX_DATA: begin
                        tx_data_val <= pwdata[7:0];
                        tx_write_strobe <= 1'b1;  // Strobe to write to TX FIFO
                    end
                    
                    REG_RX_CTRL: begin
                        rx_read_strobe <= pwdata[0];  // Strobe to read from RX FIFO
                    end
                    
                    default: begin
                        // No action for other registers
                    end
                endcase
            end
        end
    end
    
    // DEBUG: TX activity detector - TOGGLE on each TX write (for visible LED blink)
    logic debug_tx_toggle;
    logic debug_any_write_strobe;  // DEBUG: ANY APB3 write strobe (one-cycle pulse)
    
    always_ff @(posedge pclk or negedge presetn) begin
        if (!presetn) begin
            debug_tx_toggle <= 1'b0;
            debug_any_write_strobe <= 1'b0;
        end else begin
            debug_any_write_strobe <= 1'b0;  // One-cycle pulse default
            
            if (act_write) begin
                debug_any_write_strobe <= 1'b1;  // ANY write detected
                
                // TX register write specifically
                if (reg_addr == REG_TX_DATA) begin
                    debug_tx_toggle <= ~debug_tx_toggle;  // Toggle on TX write
                end
            end
        end
    end
    assign debug_tx_activity = debug_tx_toggle;      // Toggle (0→1→0→1) on each TX write
    assign debug_any_write = debug_any_write_strobe; // One-cycle pulse on ANY write
    
    // Read path - COMBINATIONAL for zero-wait-state reads
    // PRDATA must be valid in same cycle as PREADY
    always_comb begin
        prdata = 32'h00000000;
        if (act_read) begin
            case (reg_addr)
                REG_STATUS:  prdata = {24'h0, 4'h0, rx_full, rx_empty, tx_full, tx_empty};
                REG_RX_DATA: prdata = {24'h0, rx_data_val};
                default:     prdata = 32'h00000000;
            endcase
        end
    end
    
    // DEBUG: Route internal signals to analyzer probes
    assign debug_bus_state = bus_state;
    assign debug_psel_in = psel;
    assign debug_penable_in = penable;
    assign debug_pwrite_in = pwrite;
    assign debug_act_write = act_write;
    assign debug_act_read = act_read;
    assign debug_slave_ready = slave_ready;
    assign debug_pready_out = pready;
    assign debug_reg_addr = reg_addr;

endmodule
