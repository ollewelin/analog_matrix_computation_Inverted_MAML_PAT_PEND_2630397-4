`timescale 1ns / 1ps
`default_nettype none

module tb_settle_then_sample;
    reg pclk = 1'b0;
    always #10 pclk = ~pclk; // 50 MHz system clock

    reg presetn = 1'b0;
    integer errors = 0;

    // Bridge APB signals
    reg  [11:0] b_paddr = 12'd0;
    reg         b_psel = 1'b0, b_penable = 1'b0, b_pwrite = 1'b0;
    reg  [31:0] b_pwdata = 32'd0;
    wire [31:0] b_prdata;
    wire        b_pready, b_pslverr;

    // AIO APB signals
    reg  [11:0] a_paddr = 12'd0;
    reg         a_psel = 1'b0, a_penable = 1'b0, a_pwrite = 1'b0;
    reg  [31:0] a_pwdata = 32'd0;
    wire [31:0] a_prdata;
    wire        a_pready, a_pslverr;

    // Interlock wires between Bridge and Analog IO Ctrl
    wire        h_step_strobe, h_latch_strobe, h_active;
    wire [3:0]  h_step_idx;
    wire        h_hold_busy, quiet_bus_freeze;

    // T120 -> T20 wires
    wire        t20_clk9;
    wire [3:0]  t20_tx;
    wire [7:0]  t20_rx;
    wire        t20_creset_n;

    // DAC & ADC wires
    wire [5:0]  sck_dac_2;
    wire [7:0]  sck_dac_w15, sck_dac_w12, sck_dac_w34;
    wire        adc_45_conv, adc_45_sck_1_2, adc_45_sck_3_4, adc_45_sck_5_6;
    wire        adc_49_conv, adc_49_sck_1_2, adc_49_sck_3_4, adc_49_sck_5_6;
    reg  [5:0]  out_adc_45 = 6'd0;
    reg  [5:0]  out_adc_49 = 6'd0;

    wire h_ack;
    assign t20_rx = {7'd0, h_ack};

    t120_inter_fpga_bridge u_bridge (
        .pclk              (pclk),
        .presetn           (presetn),
        .psel              (b_psel),
        .penable           (b_penable),
        .pwrite            (b_pwrite),
        .paddr             (b_paddr),
        .pwdata            (b_pwdata),
        .prdata            (b_prdata),
        .pready            (b_pready),
        .pslverr           (b_pslverr),
        .t20_clk9          (t20_clk9),
        .t20_tx            (t20_tx),
        .t20_rx            (t20_rx),
        .t20_creset_n      (t20_creset_n),
        .irq               (),
        .h_step_strobe     (h_step_strobe),
        .h_latch_strobe    (h_latch_strobe),
        .h_step_idx        (h_step_idx),
        .h_active          (h_active),
        .h_hold_busy       (h_hold_busy),
        .quiet_bus_freeze  (quiet_bus_freeze)
    );

    t120_analog_io_ctrl u_aio (
        .pclk              (pclk),
        .presetn           (presetn),
        .psel              (a_psel),
        .penable           (a_penable),
        .pwrite            (a_pwrite),
        .paddr             (a_paddr),
        .pwdata            (a_pwdata),
        .prdata            (a_prdata),
        .pready            (a_pready),
        .pslverr           (a_pslverr),
        .h_latch_strobe    (h_latch_strobe),
        .h_step_idx        (h_step_idx),
        .h_active          (h_active),
        .h_hold_busy       (h_hold_busy),
        .quiet_bus_freeze  (quiet_bus_freeze),
        .si_dac_2          (),
        .sck_dac_2         (sck_dac_2),
        .rck_dac_2         (),
        .sclr_dac_2        (),
        .si_dac_w15        (),
        .sck_dac_w15       (sck_dac_w15),
        .rck_dac_w15       (),
        .sclr_dac_w15      (),
        .si_dac_w12        (),
        .sck_dac_w12       (sck_dac_w12),
        .rck_dac_w12       (),
        .sclr_dac_w12      (),
        .si_dac_w34        (),
        .sck_dac_w34       (sck_dac_w34),
        .rck_dac_w34       (),
        .sclr_dac_w34      (),
        .out_adc_45        (out_adc_45),
        .adc_45_conv       (adc_45_conv),
        .adc_45_sck_1_2    (adc_45_sck_1_2),
        .adc_45_sck_3_4    (adc_45_sck_3_4),
        .adc_45_sck_5_6    (adc_45_sck_5_6),
        .out_adc_49        (out_adc_49),
        .adc_49_conv       (adc_49_conv),
        .adc_49_sck_1_2    (adc_49_sck_1_2),
        .adc_49_sck_3_4    (adc_49_sck_3_4),
        .adc_49_sck_5_6    (adc_49_sck_5_6)
    );

    // T20 H-bus receiver (testing 3-state OE + differential P/N)
    wire [15:0] pad_p, pad_n, pad_oe;

    t20_hbus_rx #(.W(16)) u_t20_rx (
        .clk9         (t20_clk9),
        .rstn         (presetn),
        .h_sync       (t20_tx[0]),
        .h_data       (t20_tx[1]),
        .en_mask      (16'h7FFF),
        .static_on    (1'b0),
        .static_vec   (16'd0),
        .pad_p        (pad_p),
        .pad_n        (pad_n),
        .pad_oe       (pad_oe),
        .ack          (h_ack),
        .word_cnt     (),
        .sync_err_cnt ()
    );

    // Simple XC2361A 12-bit SAR ADC behavioral responder:
    // Shifts out a 16-bit word (2 leading zeros + 12-bit code [13:2] + 2 trailing zeros)
    reg [15:0] adc45_shift = 16'd0;
    reg [15:0] adc49_shift = 16'd0;
    reg [11:0] sim_adc45_code = 12'd2300; // +252 above 2048 center (0x00FC)
    reg [11:0] sim_adc49_code = 12'd1800; // -248 below 2048 center (0xFF08)

    always @(posedge adc_45_conv) begin
        adc45_shift <= {2'b00, sim_adc45_code, 2'b00};
        adc49_shift <= {2'b00, sim_adc49_code, 2'b00};
        out_adc_45  <= {6{1'b0}};
        out_adc_49  <= {6{1'b0}};
    end
    always @(negedge adc_45_sck_1_2) begin
        out_adc_45  <= {6{adc45_shift[14]}};
        adc45_shift <= {adc45_shift[14:0], 1'b0};
        out_adc_49  <= {6{adc49_shift[14]}};
        adc49_shift <= {adc49_shift[14:0], 1'b0};
    end

    // APB helpers
    task b_write(input [11:0] addr, input [31:0] data);
        begin
            @(posedge pclk);
            b_paddr <= addr; b_pwdata <= data; b_pwrite <= 1'b1; b_psel <= 1'b1; b_penable <= 1'b0;
            @(posedge pclk);
            b_penable <= 1'b1;
            @(posedge pclk);
            b_psel <= 1'b0; b_penable <= 1'b0; b_pwrite <= 1'b0;
        end
    endtask

    task b_read(input [11:0] addr, output [31:0] data);
        begin
            @(posedge pclk);
            b_paddr <= addr; b_pwrite <= 1'b0; b_psel <= 1'b1; b_penable <= 1'b0;
            @(posedge pclk);
            b_penable <= 1'b1;
            @(posedge pclk);
            data = b_prdata;
            b_psel <= 1'b0; b_penable <= 1'b0;
        end
    endtask

    task a_write(input [11:0] addr, input [31:0] data);
        begin
            @(posedge pclk);
            a_paddr <= addr; a_pwdata <= data; a_pwrite <= 1'b1; a_psel <= 1'b1; a_penable <= 1'b0;
            @(posedge pclk);
            a_penable <= 1'b1;
            @(posedge pclk);
            a_psel <= 1'b0; a_penable <= 1'b0; a_pwrite <= 1'b0;
        end
    endtask

    task a_read(input [11:0] addr, output [31:0] data);
        begin
            @(posedge pclk);
            a_paddr <= addr; a_pwrite <= 1'b0; a_psel <= 1'b1; a_penable <= 1'b0;
            @(posedge pclk);
            a_penable <= 1'b1;
            @(posedge pclk);
            data = a_prdata;
            a_psel <= 1'b0; a_penable <= 1'b0;
        end
    endtask

    reg [3:0] pclk_after_freeze = 4'd0;
    // Monitor: Once T20_CLK9 completes its falling edge (within 3 pclk cycles of quiet_bus_freeze),
    // T20_CLK9, DAC_SCK, and ADC_SCK MUST remain 100% static LOW for the entire Quiet Settling + S/H Lock window!
    always @(posedge pclk) begin
        if (h_latch_strobe) $display("LATCH_STROBE at t=%0t step=%0d c=%0d", $time, h_step_idx, u_bridge.u_hbus.c);
        if (!quiet_bus_freeze) begin
            pclk_after_freeze <= 4'd0;
        end else begin
            if (pclk_after_freeze < 4'd15) pclk_after_freeze <= pclk_after_freeze + 4'd1;
            if (pclk_after_freeze >= 4'd4) begin
                if (t20_clk9 !== 1'b0 || sck_dac_2 !== 6'd0 || adc_45_sck_1_2 !== 1'b0) begin
                    $display("FAIL: digital clock active during quiet_bus_freeze at t=%0t (clk9=%b dac=%b adc=%b)",
                             $time, t20_clk9, sck_dac_2, adc_45_sck_1_2);
                    errors = errors + 1;
                end
            end
        end
    end

    reg [31:0] rval, rval49;

    initial begin
        presetn = 1'b1;
        #1 presetn = 1'b0;
        repeat (10) @(posedge pclk);
        presetn = 1'b1;
        repeat (300) @(posedge pclk); // Let initial DAC center load finish

        // 1. Verify T20 Hadamard outputs are 3-stated (OE == 0) at reset
        if (pad_oe[14:0] !== 15'h0000) begin
            $display("FAIL: T20 Hadamard OE not 0 at reset!");
            errors = errors + 1;
        end else begin
            $display("PASS: T20 Hadamard outputs 3-stated (OE=0, Hi-Z centered) at reset.");
        end

        // 2. Configure AIO settle cycles = 100 (2.0 us @ 50 MHz), conv = 25, and pi_inv[0]=3, pi_inv[1]=0
        a_write(12'h010, (32'd25 << 16) | 32'd100);
        a_write(12'h040, 32'h7654_3203); // step 0 -> row 3, step 1 -> row 0

        // 3. Configure Bridge CLK9 = 10 MHz (period=5) and load 2 active Hadamard words + 1 quiet trailing word (0x8000)
        b_write(12'h008, 32'd5);   // 10 MHz CLK9
        b_write(12'h004, 32'd1);   // clk_en = 1
        b_write(12'hC00, 32'h0000_2AAA); // Step 0: active Hadamard word (bit 15 = 0)
        b_write(12'hC04, 32'h0000_5555); // Step 1: active Hadamard word (bit 15 = 0)
        b_write(12'hC08, 32'h0000_8000); // Step 2 (trailing word): bit 15 = 1 -> 3-state Hi-Z!

        b_write(12'h088, 32'd3);   // H_COUNT = 3 (2 active + 1 trailing Hi-Z)
        b_write(12'h08C, 32'd20);  // H_PERIOD = 20
        b_write(12'h080, 32'h0000_0201); // Start H-bus sequencer + ack_en

        // Wait for first active word to latch on T20 and verify OE=1 and differential complementarity
        @(posedge h_latch_strobe);
        repeat (5) @(posedge pclk);
        if (pad_oe[14:0] !== 15'h7FFF || (pad_p[14:0] ^ pad_n[14:0]) !== 15'h7FFF) begin
            $display("FAIL: T20 Hadamard OE or differential P/N mismatch during active state! OE=%h P=%h N=%h",
                     pad_oe[14:0], pad_p[14:0], pad_n[14:0]);
            errors = errors + 1;
        end else begin
            $display("PASS: T20 Hadamard active state drives OE=1 with complementary P/N (%h / %h).", pad_p[14:0], pad_n[14:0]);
        end

        // Verify quiet_bus_freeze is active during the 2us settle window
        if (quiet_bus_freeze !== 1'b1 || h_hold_busy !== 1'b1) begin
            $display("FAIL: quiet_bus_freeze/h_hold_busy not asserted during 2us settle window!");
            errors = errors + 1;
        end else begin
            $display("PASS: 2us Quiet Analog DC Settling Window active (quiet_bus_freeze=1, h_hold_busy=1).");
        end

        // Wait for entire 3-word sweep to finish
        wait (h_active == 1'b0);
        repeat (100) @(posedge pclk);

        // 4. Verify trailing word (0x8000, bit 15 = 1) returned T20 Hadamard outputs to 3-state Hi-Z (OE == 0)
        if (pad_oe[14:0] !== 15'h0000) begin
            $display("FAIL: T20 Hadamard OE did not return to 0 (Hi-Z) after trailing word 0x8000! OE=%h", pad_oe[14:0]);
            errors = errors + 1;
        end else begin
            $display("PASS: Trailing word 0x8000 returned all T20 Hadamard outputs to 3-state Hi-Z (OE=0, 100%% centered).");
        end

        // 5. Verify Capture RAM scatter-write via pi_inv[0]=3 and differential subtraction (raw - 2048)
        // Row 3 = index {3, 2'd0} = word 12 -> byte offset 12*4 = 0x30
        $display("DBG: sample_cnt=%0d cap_step=%0d dst_step=%0d sig45_0=%h ram12=%h ram0=%h", u_aio.sample_cnt, u_aio.adc_cap_step, u_aio.dst_step, u_aio.adc45_sig_lat[0], u_aio.cap45_ram[12], u_aio.cap45_ram[0]);
        a_read(12'h130, rval);   // cap45_ram[{3, 0}] = {adc45_sig[1], adc45_sig[0]} = 0x00FC_00FC
        a_read(12'h230, rval49); // cap49_ram[{3, 0}] = {adc49_sig[1], adc49_sig[0]} = 0xFF08_FF08
        if (rval !== 32'h00FC_00FC || rval49 !== 32'hFF08_FF08) begin
            $display("FAIL: Capture RAM[pi_inv[0]=3] got ADC45=0x%08x (exp 0x00FC00FC), ADC49=0x%08x (exp 0xFF08FF08)", rval, rval49);
            errors = errors + 1;
        end else begin
            $display("PASS: Differential ADC S/H & Scatter-Write verified: ADC45[row=3]=+252 (0x00FC), ADC49[row=3]=-248 (0xFF08).");
        end

        if (errors == 0) begin
            $display("ALL SETTLE-THEN-SAMPLE & 3-STATE DIFFERENTIAL TESTS PASSED");
        end else begin
            $display("%0d ERRORS", errors);
            $finish(1);
        end
        $finish;
    end
endmodule
`default_nettype wire
