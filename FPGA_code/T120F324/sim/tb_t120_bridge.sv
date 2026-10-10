// =============================================================================
// tb_t120_bridge.sv : bench test of the T120 bridge against a behavioural T20
// Run:  FPGA_code/T120F324/sim/run_sim.sh
// =============================================================================
`timescale 1ns / 1ps

module tb_t120_bridge;
    localparam integer W = 16;

    reg clk = 0;
    always #10 clk = ~clk;          // 50 MHz
    reg rstn = 0;

    reg         psel = 0, penable = 0, pwrite = 0;
    reg  [11:0] paddr = 0;
    reg  [31:0] pwdata = 0;
    wire [31:0] prdata;

    wire        t20_clk9;
    wire [3:0]  t20_tx;
    wire [7:0]  t20_rx;
    wire        t20_creset_n, irq, h_step_strobe, h_active;

    t120_inter_fpga_bridge #(.H_WIDTH(W)) dut (
        .pclk(clk), .presetn(rstn), .psel(psel), .penable(penable), .pwrite(pwrite),
        .paddr(paddr), .pwdata(pwdata), .prdata(prdata), .pready(), .pslverr(),
        .t20_clk9(t20_clk9), .t20_tx(t20_tx), .t20_rx(t20_rx), .t20_creset_n(t20_creset_n),
        .irq(irq), .h_step_strobe(h_step_strobe), .h_active(h_active));

    // ---------------- APB tasks ----------------
    task apb_write(input [11:0] a, input [31:0] d);
        begin
            @(posedge clk); #1; psel = 1; pwrite = 1; paddr = a; pwdata = d; penable = 0;
            @(posedge clk); #1; penable = 1;
            @(posedge clk); #1; psel = 0; penable = 0; pwrite = 0;
        end
    endtask
    task apb_read(input [11:0] a, output [31:0] d);
        begin
            @(posedge clk); #1; psel = 1; pwrite = 0; paddr = a; penable = 0;
            @(posedge clk); #1; penable = 1;
            #5; d = prdata;
            @(posedge clk); #1; psel = 0; penable = 0;
        end
    endtask

    // ---------------- Behavioural T20 ----------------
    wire #3 clk9_t20 = t20_clk9;
    wire [3:0] #3 tx_t20_d = t20_tx; wire [3:0] tx_t20 = tx_t20_d;
    wire h_sync_in = tx_t20[0];
    wire h_data_in = tx_t20[1];
    wire [1:0] s_sym_in = {tx_t20[3], tx_t20[2]};

    // CRC8 poly 0x07
    function [7:0] crc8(input [7:0] crc, input [7:0] d);
        reg [7:0] x; integer i;
        begin
            x = crc ^ d;
            for (i = 0; i < 8; i = i + 1) x = x[7] ? ((x << 1) ^ 8'h07) : (x << 1);
            crc8 = x;
        end
    endfunction

    // --- H-bus receiver (shift register on CLK9 only, exactly the intended T20 logic) ---
    reg [W-1:0] h_sh;
    integer     h_cnt = 0;
    reg [W-1:0] h_vec;
    reg         h_done_q = 0, h_ack_pipe = 0, h_ack_q = 0;
    time        apply_t [0:1023];
    reg [W-1:0] apply_v [0:1023];
    integer     apply_n = 0;
    always @(posedge clk9_t20) begin
        h_done_q   <= 1'b0;
        if (h_sync_in) begin
            h_sh  <= {{(W-1){1'b0}}, h_data_in};
            h_cnt <= 1;
        end else if (h_cnt != 0) begin
            h_sh <= {h_sh[W-2:0], h_data_in};
            if (h_cnt == W - 1) begin
                h_vec <= {h_sh[W-2:0], h_data_in};
                apply_t[apply_n] = $time;
                apply_v[apply_n] = {h_sh[W-2:0], h_data_in};
                apply_n = apply_n + 1;
                h_done_q <= 1'b1;
                h_cnt <= 0;
            end else begin
                h_cnt <= h_cnt + 1;
            end
        end
        h_ack_pipe <= h_done_q;
        h_ack_q    <= h_ack_pipe;
    end

    // --- S-bus receiver / responder ---
    reg        t20_silent = 0, t20_bad_crc = 0;
    reg [7:0]  sr = 0;
    integer    s_state = 0;       // 0 hunt, 1 bytes
    integer    s_sym_cnt = 0, s_fld = 0, s_pidx = 0;
    reg [7:0]  s_byte, s_crc, s_ch, s_seq, s_lenh;
    integer    s_len;
    reg [7:0]  s_pay [0:1023];
    integer    s_frames_good = 0, s_frames_bad = 0;
    reg [7:0]  nibq [0:4095];
    integer    nq_wr = 0, nq_rd = 0;
    reg [3:0]  s_rx_q = 0;

    task push_byte(input [7:0] b);
        begin nibq[nq_wr] = {4'd0, b[7:4]}; nq_wr = nq_wr + 1; nibq[nq_wr] = {4'd0, b[3:0]}; nq_wr = nq_wr + 1; end
    endtask

    integer k;
    reg [7:0] rc;
    task build_response;
        begin
            rc = 8'h00;
            push_byte(8'hA5);
            push_byte(8'h06);                 rc = crc8(rc, 8'h06);
            push_byte(s_ch);                  rc = crc8(rc, s_ch);
            push_byte(s_seq);                 rc = crc8(rc, s_seq);
            push_byte(8'h00);                 rc = crc8(rc, 8'h00);
            push_byte((s_len > 8) ? 8'd8 : s_len[7:0]);
            rc = crc8(rc, (s_len > 8) ? 8'd8 : s_len[7:0]);
            for (k = 0; k < ((s_len > 8) ? 8 : s_len); k = k + 1) begin
                push_byte(s_pay[k]); rc = crc8(rc, s_pay[k]);
            end
            push_byte(t20_bad_crc ? ~rc : rc);
        end
    endtask

    always @(posedge clk9_t20) begin
        // RX lanes toward T120: nibble queue launched on CLK9 rising edge
        if (nq_rd != nq_wr) begin s_rx_q <= nibq[nq_rd][3:0]; nq_rd = nq_rd + 1; end
        else s_rx_q <= 4'h0;

        sr <= {sr[5:0], s_sym_in};
        if (s_state == 0) begin
            if ({sr[5:0], s_sym_in} == 8'hA5) begin
                s_state = 1; s_sym_cnt = 0; s_fld = 0; s_crc = 8'h00;
            end
        end else begin
            s_byte = {s_byte[5:0], s_sym_in};
            s_sym_cnt = s_sym_cnt + 1;
            if (s_sym_cnt == 4) begin
                s_sym_cnt = 0;
                case (s_fld)
                    0: begin s_ch  = s_byte; s_crc = crc8(s_crc, s_byte); s_fld = 1; end
                    1: begin s_seq = s_byte; s_crc = crc8(s_crc, s_byte); s_fld = 2; end
                    2: begin s_lenh = s_byte; s_crc = crc8(s_crc, s_byte); s_fld = 3; end
                    3: begin
                        s_len = {s_lenh, s_byte}; s_crc = crc8(s_crc, s_byte); s_pidx = 0;
                        s_fld = (s_len == 0) ? 5 : 4;
                    end
                    4: begin
                        s_pay[s_pidx] = s_byte; s_pidx = s_pidx + 1; s_crc = crc8(s_crc, s_byte);
                        if (s_pidx == s_len) s_fld = 5;
                    end
                    default: begin
                        if (s_byte == s_crc) begin
                            s_frames_good = s_frames_good + 1;
                            if (!t20_silent) build_response;
                        end else s_frames_bad = s_frames_bad + 1;
                        s_state = 0;
                    end
                endcase
            end
        end
    end

    assign #8 t20_rx = {s_rx_q, 2'b00, 1'b0, h_ack_q};

    // ---------------- Test sequence ----------------
    integer errors = 0;
    reg [31:0] r;
    integer i;
    time dt, dt0;
    integer lat_min_i;

    task check(input cond, input [255:0] msg);
        begin
            if (!cond) begin errors = errors + 1; $display("FAIL: %0s (t=%0t)", msg, $time); end
        end
    endtask

    task run_hadamard(input integer steps, input integer period);
        begin
            apply_n = 0;
            apb_write(12'h088, steps);
            apb_write(12'h08C, period);
            apb_write(12'h080, 32'h0000_0201);          // ack_en, start
            r = 0;
            while (!r[1]) apb_read(12'h084, r);          // wait for done
            repeat (50) @(posedge clk);
        end
    endtask

    task check_hadamard(input integer steps, input integer period, input integer clk_ns);
        begin
            check(apply_n == steps, "hadamard word count");
            for (i = 0; i < steps; i = i + 1) check(apply_v[i] == (16'hA000 + i * 16'h0111), "hadamard word value");
            dt0 = apply_t[1] - apply_t[0];
            for (i = 1; i < steps; i = i + 1) begin
                dt = apply_t[i] - apply_t[i-1];
                check(dt == period * clk_ns, "hadamard exact word spacing");
            end
            apb_read(12'h098, r); check(r == steps, "ack_ok count");
            apb_read(12'h09C, r); check(r == 0, "ack_miss zero");
            apb_read(12'h0A4, r); lat_min_i = r; apb_read(12'h0A8, r);
            $display("   H latency min=%0d max=%0d (expect W+3=%0d), spacing=%0t ps", lat_min_i, r, W + 3, dt0);
            check(lat_min_i == r, "ack latency jitter-free (min==max)");
            check(r == W + 3, "ack latency == W+3");
        end
    endtask

    initial begin
        $dumpfile("tb_t120_bridge.vcd"); $dumpvars(0, tb_t120_bridge);
        repeat (5) @(posedge clk); rstn = 1; repeat (3) @(posedge clk);

        apb_read(12'h000, r); check(r == 32'h5432_0102, "ID");
        check(t20_creset_n === 1'b1, "creset released after reset");

        // ---- manual pin test ----
        apb_write(12'h004, 32'h0000_0002);
        apb_write(12'h00C, {27'd0, 4'b1010, 1'b1});
        #50; check(t20_clk9 === 1'b1 && t20_tx === 4'b1010, "manual pins");
        apb_write(12'h004, 32'h0000_0000);

        // ---- table load ----
        for (i = 0; i < 16; i = i + 1) apb_write(12'hC00 + 4 * i, 32'hA000 + i * 32'h0111);

        // ---- Hadamard at 10 MHz (period 5 sys cycles) ----
        $display("== H-bus @10 MHz");
        apb_write(12'h008, 5); apb_write(12'h004, 32'h1);
        run_hadamard(8, 24); check_hadamard(8, 24, 100);
        apb_write(12'h080, 32'h0000_0204);              // clr counters (keep ack_en)

        // ---- Hadamard at 2 MHz ----
        $display("== H-bus @2 MHz");
        apb_write(12'h004, 32'h0); apb_write(12'h008, 25); apb_write(12'h004, 32'h1);
        run_hadamard(8, 20); check_hadamard(8, 20, 500);
        apb_write(12'h080, 32'h0000_0204);

        // ---- S-bus request/response ----
        $display("== S-bus");
        for (i = 0; i < 3; i = i + 1) apb_write(12'h400 + 4 * i, 32'h0403_0201 + i * 32'h04040404);
        apb_write(12'h048, {8'h01, 8'h42, 16'd10});
        apb_write(12'h040, 32'h1);
        r = 0; i = 0;
        while (!r[6] && !r[4] && i < 4000) begin apb_read(12'h044, r); i = i + 1; end
        check(r[2], "rx_valid"); check(r[7], "resp_match"); check(!r[3] && !r[4], "no crc/timeout");
        apb_read(12'h04C, r); check(r[31:24] == 8'h06 && r[23:16] == 8'h01 && r[15:8] == 8'h42, "rx header");
        apb_read(12'h050, r); check(r == 8, "rx len");
        apb_read(12'h800, r); check(r == 32'h0403_0201, "rx payload w0");
        apb_read(12'h804, r); check(r == 32'h0807_0605, "rx payload w1");
        check(s_frames_good == 1, "T20 got 1 good frame");
        for (i = 0; i < 10; i = i + 1) check(s_pay[i] == (i + 1), "T20 payload bytes");
        apb_write(12'h040, 32'h2);

        // ---- CRC error from T20 ----
        $display("== S-bus bad CRC response");
        t20_bad_crc = 1;
        apb_write(12'h048, {8'h04, 8'h01, 16'd0});
        apb_write(12'h040, 32'h5);                       // start + clr
        i = 0; r = 0;
        while (!r[3] && i < 600) begin apb_read(12'h044, r); i = i + 1; end
        check(r[3], "crc_err sticky"); check(!r[2], "no rx_valid on bad crc");
        t20_bad_crc = 0;

        // ---- timeout + auto CRESET ----
        $display("== S-bus timeout and CRESET");
        t20_silent = 1;
        apb_write(12'h054, 200);                         // 200 us
        apb_write(12'h018, 100);                         // 100 us reset pulse
        apb_write(12'h040, 32'h0000_0010 | 32'h5);       // auto_creset, start, clr
        i = 0; r = 0;
        while (!r[4] && i < 20000) begin apb_read(12'h044, r); i = i + 1; end
        check(r[4], "timeout sticky");
        #1000; check(t20_creset_n === 1'b0, "creset asserted");
        #150000; check(t20_creset_n === 1'b1, "creset released");
        t20_silent = 0;
        apb_write(12'h040, 32'h0000_0000);

        // ---- H-bus loop while S-bus traffic runs: spacing must stay exact ----
        $display("== H-bus loop + concurrent S-bus traffic");
        apb_write(12'h040, 32'h4);
        apb_write(12'h080, 32'h0000_0204);
        apb_write(12'h088, 8); apb_write(12'h08C, 20);
        apply_n = 0;
        apb_write(12'h080, 32'h0000_0301);               // loop, ack_en, start
        apb_write(12'h048, {8'h04, 8'h07, 16'd4});
        for (i = 0; i < 5; i = i + 1) begin
            apb_write(12'h040, 32'h1);
            repeat (3000) @(posedge clk);
            apb_write(12'h040, 32'h2);
        end
        apb_write(12'h080, 32'h0000_0102);               // stop (keep loop)
        repeat (100) @(posedge clk);
        for (i = 1; i < apply_n; i = i + 1) begin
            dt = apply_t[i] - apply_t[i-1];
            check(dt == 20 * 500, "loop spacing exact under S-bus load");
        end
        apb_read(12'h09C, r); check(r == 0, "no ack miss under load");
        apb_read(12'h0A4, r); lat_min_i = r; apb_read(12'h0A8, r); check(lat_min_i == r, "latency jitter-free under load");
        $display("   words=%0d, S-bus frames good=%0d", apply_n, s_frames_good);

        if (errors == 0) $display("ALL TESTS PASSED"); else $display("%0d ERRORS", errors);
        $finish;
    end

    initial begin #200000000; $display("TIMEOUT"); $finish; end
endmodule
