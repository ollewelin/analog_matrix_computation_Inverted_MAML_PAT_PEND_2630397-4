// =============================================================================
// tb_mdio_master.sv : Testbench for MDIO Master
// =============================================================================
// Simple testbench to verify Clause-22 MDIO protocol
// =============================================================================

`timescale 1ns / 1ps

module tb_mdio_master;

// =============================================================================
// Parameters
// =============================================================================
parameter int SYS_CLK_HZ = 50_000_000;
parameter int MDC_HZ     = 2_500_000;  // Fast for simulation
parameter real CLK_PERIOD = 1_000_000_000.0 / SYS_CLK_HZ;  // 20ns for 50MHz

// =============================================================================
// Signals
// =============================================================================
logic        clk;
logic        rst_n;

// APB
logic        psel;
logic        penable;
logic        pwrite;
logic [3:0]  paddr;
logic [31:0] pwdata;
wire  [31:0] prdata;
wire         pready;
wire         pslverr;

// MDIO
wire         mdc;
wire         mdio_i;
wire         mdio_o;
wire         mdio_oe;
wire         phy_rst_n;
wire         irq;

// MDIO bus (bidirectional)
wire         mdio_bus;
logic        phy_mdio_out;
logic        phy_mdio_oe;

// =============================================================================
// Clock Generation
// =============================================================================
initial begin
    clk = 0;
    forever #(CLK_PERIOD/2) clk = ~clk;
end

// =============================================================================
// DUT
// =============================================================================
mdio_master #(
    .SYS_CLK_HZ (SYS_CLK_HZ),
    .MDC_HZ     (MDC_HZ)
) dut (
    .clk        (clk),
    .rst_n      (rst_n),
    .psel       (psel),
    .penable    (penable),
    .pwrite     (pwrite),
    .paddr      (paddr),
    .pwdata     (pwdata),
    .prdata     (prdata),
    .pready     (pready),
    .pslverr    (pslverr),
    .mdc        (mdc),
    .mdio_i     (mdio_bus),
    .mdio_o     (mdio_o),
    .mdio_oe    (mdio_oe),
    .phy_rst_n  (phy_rst_n),
    .irq        (irq)
);

// =============================================================================
// MDIO Bus Model
// =============================================================================
// Bidirectional bus with pull-up
assign mdio_bus = mdio_oe ? mdio_o : (phy_mdio_oe ? phy_mdio_out : 1'b1);
assign mdio_i = mdio_bus;

// =============================================================================
// Simple PHY Model for Read Responses
// =============================================================================
logic [63:0] mdio_shift;
int          mdio_bit_cnt;
logic [15:0] phy_read_data;
logic        phy_responding;

// Track MDIO frame
always @(posedge mdc or negedge rst_n) begin
    if (!rst_n) begin
        mdio_shift    <= '1;
        mdio_bit_cnt  <= 0;
        phy_mdio_out  <= 1'b1;
        phy_mdio_oe   <= 1'b0;
        phy_read_data <= 16'hABCD;  // Test read data
        phy_responding <= 1'b0;
    end else begin
        mdio_shift <= {mdio_shift[62:0], mdio_bus};
        
        // Detect read operation start (after preamble + ST + OP + PHYAD + REGAD)
        // OP for read = '10'
        if (mdio_shift[15:14] == 2'b01 &&  // Start of frame
            mdio_shift[13:12] == 2'b10 &&  // Read opcode
            mdio_bit_cnt >= 32 + 2 + 2 + 5 + 5 - 1) begin  // After REGAD
            
            if (!phy_responding) begin
                phy_responding <= 1'b1;
                mdio_bit_cnt   <= 0;
            end
        end
        
        // PHY turnaround and data response
        if (phy_responding) begin
            mdio_bit_cnt <= mdio_bit_cnt + 1;
            
            if (mdio_bit_cnt == 0) begin
                // TA bit 1: Hi-Z (release)
                phy_mdio_oe <= 1'b0;
            end else if (mdio_bit_cnt == 1) begin
                // TA bit 2: drive '0'
                phy_mdio_oe  <= 1'b1;
                phy_mdio_out <= 1'b0;
            end else if (mdio_bit_cnt >= 2 && mdio_bit_cnt <= 17) begin
                // Data bits, MSB first
                phy_mdio_oe  <= 1'b1;
                phy_mdio_out <= phy_read_data[17 - mdio_bit_cnt];
            end else begin
                phy_mdio_oe    <= 1'b0;
                phy_mdio_out   <= 1'b1;
                phy_responding <= 1'b0;
                mdio_bit_cnt   <= 0;
            end
        end else begin
            // Count bits in frame
            if (mdio_bus == 1'b0 && mdio_shift[0] == 1'b1) begin
                // Detected start bit (1->0 transition in preamble area)
                mdio_bit_cnt <= 1;
            end else if (mdio_bit_cnt > 0) begin
                mdio_bit_cnt <= mdio_bit_cnt + 1;
            end
        end
    end
end

// =============================================================================
// APB Tasks
// =============================================================================
task automatic apb_write(input [3:0] addr, input [31:0] data);
    @(posedge clk);
    psel    <= 1'b1;
    pwrite  <= 1'b1;
    paddr   <= addr;
    pwdata  <= data;
    @(posedge clk);
    penable <= 1'b1;
    @(posedge clk);
    psel    <= 1'b0;
    penable <= 1'b0;
    pwrite  <= 1'b0;
endtask

task automatic apb_read(input [3:0] addr, output [31:0] data);
    @(posedge clk);
    psel    <= 1'b1;
    pwrite  <= 1'b0;
    paddr   <= addr;
    @(posedge clk);
    penable <= 1'b1;
    @(posedge clk);
    data    = prdata;
    psel    <= 1'b0;
    penable <= 1'b0;
endtask

task automatic wait_done();
    logic [31:0] status;
    do begin
        apb_read(4'h1, status);  // Read STATUS
    end while (status[0]);  // While busy
endtask

// =============================================================================
// Test Sequence
// =============================================================================
initial begin
    $display("=== MDIO Master Testbench ===");
    $display("SYS_CLK_HZ = %0d, MDC_HZ = %0d", SYS_CLK_HZ, MDC_HZ);
    
    // Initialize
    rst_n   = 0;
    psel    = 0;
    penable = 0;
    pwrite  = 0;
    paddr   = 0;
    pwdata  = 0;
    
    // Reset
    repeat (10) @(posedge clk);
    rst_n = 1;
    repeat (10) @(posedge clk);
    
    // Read version register
    begin
        logic [31:0] version;
        apb_read(4'h3, version);
        $display("[%0t] Version = 0x%08X (v%0d.%0d)", $time, version, 
                 version[15:8], version[7:0]);
    end
    
    // Release PHY from reset
    $display("[%0t] Releasing PHY reset...", $time);
    apb_write(4'h2, 32'h0000_0001);  // CONFIG: phy_rst=1
    repeat (100) @(posedge clk);
    
    // === Test 1: Write to PHY register ===
    $display("[%0t] Test 1: Write PHY_ADDR=0x01, REG_ADDR=0x00, DATA=0x1234", $time);
    // CTRL: start=1, rw=0(write), phy_addr=1, reg_addr=0, wdata=0x1234
    apb_write(4'h0, {16'h1234, 1'b0, 5'd0, 5'd1, 3'b0, 1'b0, 1'b1});
    wait_done();
    $display("[%0t] Write complete", $time);
    
    repeat (50) @(posedge clk);
    
    // Clear done flag
    apb_write(4'h1, 32'h0000_0002);
    
    // === Test 2: Read from PHY register ===
    $display("[%0t] Test 2: Read PHY_ADDR=0x01, REG_ADDR=0x02", $time);
    // CTRL: start=1, rw=1(read), phy_addr=1, reg_addr=2, wdata=0
    apb_write(4'h0, {16'h0000, 1'b0, 5'd2, 5'd1, 3'b0, 1'b1, 1'b1});
    wait_done();
    
    begin
        logic [31:0] status;
        apb_read(4'h1, status);
        $display("[%0t] Read complete, DATA=0x%04X", $time, status[31:16]);
    end
    
    repeat (100) @(posedge clk);
    
    $display("=== Test Complete ===");
    $finish;
end

// =============================================================================
// Timeout
// =============================================================================
initial begin
    #1_000_000;  // 1ms timeout
    $display("ERROR: Timeout!");
    $finish;
end

// =============================================================================
// Waveform Dump
// =============================================================================
initial begin
    $dumpfile("tb_mdio_master.vcd");
    $dumpvars(0, tb_mdio_master);
end

endmodule
