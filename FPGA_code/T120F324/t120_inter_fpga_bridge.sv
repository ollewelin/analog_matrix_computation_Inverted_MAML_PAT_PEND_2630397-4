// =============================================================================
// t120_inter_fpga_bridge.sv : T120 <-> T20 inter-FPGA bridge (T120 master side)
// =============================================================================
// Two independent buses share the physical wires and the one bus clock T20_CLK9
// (everything is synchronous to CLK9, all engines live in the sys_clk domain):
//
//   H-bus  (Hadamard, HARDWARE-ONLY timing, no CRC, 1-bit ACK)
//     TX11_P = H_SYNC   TX11_N = H_DATA          (T120 -> T20)
//     RX00_P = H_ACK    RX00_N = spare/H_STATUS  (T20 -> T120)
//   S-bus  (service: SoC C-code, SPI flash update, trace; CRC8, req/resp)
//     TX12_P/N = S_TX[0]/[1]  2 bit per CLK9      (T120 -> T20)
//     RX02_P/N, RX03_P/N = S_RX[0..3] 4 bit per CLK9 (T20 -> T120)
//   RX01_P/N reserved.
//
// t20_tx[3:0] = {S_TX1, S_TX0, H_DATA, H_SYNC}   (TX12_N, TX12_P, TX11_N, TX11_P)
// t20_rx[7:0] = {RX03_N, RX03_P, RX02_N, RX02_P, RX01_N, RX01_P, RX00_N, RX00_P}
// T20 CRESET_N is driven on t20_creset_n (board patch wire on T120 pin T120_LED1).
//
// APB3 register map (offsets inside the 4 KB window):
//   0x000 ID            RO  32'h5432_0102
//   0x004 CTRL          RW  [0] clk_en  [1] manual  [10:8] rx_dly (sys cycles)
//   0x008 CLK_PERIOD    RW  [11:0] sys_clk cycles per CLK9 period (5 = 10 MHz @50 MHz), default 25
//   0x00C MANUAL        RW  [0] clk9  [4:1] t20_tx[3:0]   (manual pin bit-bang, needs CTRL.manual)
//   0x010 RX_PINS       RO  [7:0] synchronised t20_rx
//   0x014 CRESET_CTRL   RW  [0] level(1=release)  W1:[1] pulse (write with [1]=1 leaves level unchanged)   RO:[8] busy
//   0x018 CRESET_US     RW  [23:0] pulse width in us (default 12000)
//   0x01C IRQ_EN        RW  [0] rx_valid [1] timeout [2] xact_done [3] h_done [4] h_ack_miss
//   0x020 IRQ_STATUS    RO
//   --- S-bus ---
//   0x040 S_CTRL        W1:[0] tx_start [1] rx_release [2] clr_status (also aborts a pending transaction)   RW:[3] no_ack [4] auto_creset
//   0x044 S_STATUS      RO  [0] tx_busy [1] xact_busy [2] rx_valid [3] crc_err* [4] timeout* [5] rx_ovf*
//                           [6] xact_done* [7] resp_match   (* sticky, cleared by clr_status/tx_start)
//   0x048 S_TX_HDR      RW  [31:24] channel [23:16] seq/op [15:0] length
//   0x04C S_RX_HDR      RO  [31:24] resp [23:16] channel [15:8] seq
//   0x050 S_RX_LEN      RO
//   0x054 S_TIMEOUT_US  RW  default 100000
//   --- H-bus ---
//   0x080 H_CTRL        W1:[0] start [1] stop [2] clr counters   RW:[8] loop [9] ack_en
//   0x084 H_STATUS      RO  [0] running [1] done [2] ack_miss*
//   0x088 H_COUNT       RW  steps per run (<= table depth)
//   0x08C H_PERIOD      RW  CLK9 cycles per step (>= H_WIDTH+3)
//   0x090 H_ACK_WIN     RW  [7:0] min latency  [15:8] max latency (CLK9 cycles from SYNC)
//   0x094 H_STEP        RO  current step
//   0x098 H_ACK_OK      RO
//   0x09C H_ACK_MISS    RO
//   0x0A0 H_LAT_LAST    RO
//   0x0A4 H_LAT_MIN     RO
//   0x0A8 H_LAT_MAX     RO
//   0x0AC H_WIDTH       RO
//   --- memories (32-bit words, little endian) ---
//   0x400..0x7FF  S_TX buffer (write only, 256 words)
//   0x800..0xBFF  S_RX buffer (read only,  256 words)
//   0xC00..0xFFF  H table     (write only, 256 words; low H_WIDTH bits used, MSB sent first)
// =============================================================================
`timescale 1ns / 1ps
`default_nettype none

module t120_inter_fpga_bridge #(
    parameter integer H_WIDTH   = 16,
    parameter integer US_CYCLES = 50     // sys_clk cycles per microsecond
)(
    input  wire         pclk,
    input  wire         presetn,
    input  wire         psel,
    input  wire         penable,
    input  wire         pwrite,
    input  wire [11:0]  paddr,
    input  wire [31:0]  pwdata,
    output logic [31:0] prdata,
    output wire         pready,
    output wire         pslverr,

    output wire         t20_clk9,
    output wire [3:0]   t20_tx,
    input  wire [7:0]   t20_rx,
    output wire         t20_creset_n,

    output wire         irq,
    output wire         h_step_strobe,
    output wire         h_active
);
    assign pready  = 1'b1;
    assign pslverr = 1'b0;

    // ------------------------------------------------------------------
    // Time base
    // ------------------------------------------------------------------
    logic [7:0] us_cnt;
    logic       us_tick;
    always_ff @(posedge pclk or negedge presetn) begin
        if (!presetn) begin us_cnt <= 8'd0; us_tick <= 1'b0; end
        else if (us_cnt == US_CYCLES - 1) begin us_cnt <= 8'd0; us_tick <= 1'b1; end
        else begin us_cnt <= us_cnt + 8'd1; us_tick <= 1'b0; end
    end

    // ------------------------------------------------------------------
    // Registers
    // ------------------------------------------------------------------
    logic        r_clk_en, r_manual;
    logic [2:0]  r_rx_dly;
    logic [11:0] r_period;
    logic        r_man_clk;
    logic [3:0]  r_man_tx;
    logic [23:0] r_creset_us;
    logic [4:0]  r_irq_en;
    logic        r_no_ack, r_auto_creset;
    logic [31:0] r_s_tx_hdr;
    logic [31:0] r_s_timeout;
    logic        r_h_loop, r_h_ack_en;
    logic [15:0] r_h_count, r_h_period;
    logic [15:0] r_h_ack_win;

    wire apb_wr = psel && penable && pwrite;
    wire reg_sel = (paddr[11:10] == 2'b00);
    wire [5:0] ra = paddr[7:2];

    wire w_ctrl     = apb_wr && reg_sel && (ra == 6'h01);
    wire w_creset   = apb_wr && reg_sel && (ra == 6'h05);
    wire w_s_ctrl   = apb_wr && reg_sel && (ra == 6'h10);
    wire w_h_ctrl   = apb_wr && reg_sel && (ra == 6'h20);

    wire p_s_tx_start   = w_s_ctrl && pwdata[0];
    wire p_s_rx_release = w_s_ctrl && pwdata[1];
    wire p_s_clr        = w_s_ctrl && pwdata[2];
    wire p_creset_pulse = w_creset && pwdata[1];
    wire p_h_start      = w_h_ctrl && pwdata[0];
    wire p_h_stop       = w_h_ctrl && pwdata[1];
    wire p_h_clr        = w_h_ctrl && pwdata[2];

    always_ff @(posedge pclk or negedge presetn) begin
        if (!presetn) begin
            r_clk_en <= 1'b0; r_manual <= 1'b0; r_rx_dly <= 3'd0;
            r_period <= 12'd25; r_man_clk <= 1'b0; r_man_tx <= 4'd0;
            r_creset_us <= 24'd12000; r_irq_en <= 5'd0;
            r_no_ack <= 1'b0; r_auto_creset <= 1'b0;
            r_s_tx_hdr <= 32'd0; r_s_timeout <= 32'd100000;
            r_h_loop <= 1'b0; r_h_ack_en <= 1'b1;
            r_h_count <= 16'd0; r_h_period <= 16'd32; r_h_ack_win <= 16'h3F01;
        end else if (apb_wr && reg_sel) begin
            case (ra)
                6'h01: begin r_clk_en <= pwdata[0]; r_manual <= pwdata[1]; r_rx_dly <= pwdata[10:8]; end
                6'h02: r_period    <= pwdata[11:0];
                6'h03: begin r_man_clk <= pwdata[0]; r_man_tx <= pwdata[4:1]; end
                6'h06: r_creset_us <= pwdata[23:0];
                6'h07: r_irq_en    <= pwdata[4:0];
                6'h10: begin r_no_ack <= pwdata[3]; r_auto_creset <= pwdata[4]; end
                6'h12: r_s_tx_hdr  <= pwdata;
                6'h15: r_s_timeout <= pwdata;
                6'h20: begin r_h_loop <= pwdata[8]; r_h_ack_en <= pwdata[9]; end
                6'h22: r_h_count   <= pwdata[15:0];
                6'h23: r_h_period  <= pwdata[15:0];
                6'h24: r_h_ack_win <= pwdata[15:0];
                default: ;
            endcase
        end
    end

    // ------------------------------------------------------------------
    // RX input synchroniser (2 FF, inputs are asynchronous to sys_clk)
    // ------------------------------------------------------------------
    logic [7:0] rx_s1, rx_s2;
    always_ff @(posedge pclk) begin
        rx_s1 <= t20_rx;
        rx_s2 <= rx_s1;
    end

    // ------------------------------------------------------------------
    // CLK9 generator
    // ------------------------------------------------------------------
    wire clk9, rise_ev, fall_ev;
    t120_bridge_clkgen u_clkgen (
        .clk(pclk), .rstn(presetn), .enable(r_clk_en && !r_manual),
        .period(r_period), .clk9(clk9), .rise_ev(rise_ev), .fall_ev(fall_ev)
    );

    // RX sampling strobe = rise_ev delayed by rx_dly sys cycles
    logic [6:0] rise_dly;
    always_ff @(posedge pclk) rise_dly <= {rise_dly[5:0], rise_ev};
    wire smp_ev = (r_rx_dly == 3'd0) ? rise_ev : rise_dly[r_rx_dly - 3'd1];

    // ------------------------------------------------------------------
    // S-bus: buffers, TX, RX, transaction FSM
    // ------------------------------------------------------------------
    (* ram_style = "block" *) reg [31:0] tx_ram [0:255];
    (* ram_style = "block" *) reg [31:0] rx_ram [0:255];
    (* ram_style = "block" *) reg [31:0] h_tab  [0:255];

    logic [31:0] tx_rd_q, rx_rd_q, h_rd_q;
    wire  [7:0]  sb_tx_addr;
    wire  [7:0]  h_rd_addr;
    wire         rx_we;
    wire  [7:0]  rx_waddr;
    wire  [31:0] rx_wdata;

    always_ff @(posedge pclk) begin
        if (apb_wr && paddr[11:10] == 2'b01) tx_ram[paddr[9:2]] <= pwdata;
        if (apb_wr && paddr[11:10] == 2'b11) h_tab[paddr[9:2]]  <= pwdata;
        if (rx_we) rx_ram[rx_waddr] <= rx_wdata;
        tx_rd_q <= tx_ram[sb_tx_addr];
        h_rd_q  <= h_tab[h_rd_addr];
        rx_rd_q <= rx_ram[paddr[9:2]];
    end

    wire        sb_tx_busy, sb_tx_done, sb_tx_start;
    wire [1:0]  sb_sym;
    wire        xact_busy, xact_done, xact_timeout;
    wire [7:0]  rx_resp, rx_ch, rx_seq;
    wire [10:0] rx_len;
    wire        fr_ok, fr_err, fr_ovf;
    logic       rx_valid;

    t120_sbus_tx u_sbus_tx (
        .clk(pclk), .rstn(presetn), .fall_ev(fall_ev),
        .start(sb_tx_start),
        .hdr_ch(r_s_tx_hdr[31:24]), .hdr_seq(r_s_tx_hdr[23:16]), .hdr_len(r_s_tx_hdr[15:0]),
        .ram_addr(sb_tx_addr), .ram_rdata(tx_rd_q),
        .busy(sb_tx_busy), .done(sb_tx_done), .sym(sb_sym)
    );

    t120_sbus_rx u_sbus_rx (
        .clk(pclk), .rstn(presetn), .smp_ev(smp_ev), .nib(rx_s2[7:4]),
        .buf_busy(rx_valid),
        .ram_we(rx_we), .ram_waddr(rx_waddr), .ram_wdata(rx_wdata),
        .rx_resp(rx_resp), .rx_ch(rx_ch), .rx_seq(rx_seq), .rx_len(rx_len),
        .frame_ok(fr_ok), .frame_err(fr_err), .frame_ovf(fr_ovf)
    );

    t120_sbus_xact u_sbus_xact (
        .clk(pclk), .rstn(presetn), .us_tick(us_tick),
        .start(p_s_tx_start), .no_ack(r_no_ack), .timeout_us(r_s_timeout),
        .tx_start(sb_tx_start), .tx_done(sb_tx_done), .rx_ok(fr_ok), .rx_err(fr_err), .abort(p_s_clr && !p_s_tx_start),
        .busy(xact_busy), .done_p(xact_done), .timeout_p(xact_timeout)
    );

    logic st_crc_err, st_timeout, st_ovf, st_done, st_match;
    always_ff @(posedge pclk or negedge presetn) begin
        if (!presetn) begin
            rx_valid <= 1'b0; st_crc_err <= 1'b0; st_timeout <= 1'b0;
            st_ovf <= 1'b0; st_done <= 1'b0; st_match <= 1'b0;
        end else begin
            if (p_s_rx_release) rx_valid <= 1'b0;
            if (p_s_clr) begin
                st_crc_err <= 1'b0; st_timeout <= 1'b0; st_ovf <= 1'b0; st_done <= 1'b0;
            end
            if (p_s_tx_start) begin st_done <= 1'b0; st_timeout <= 1'b0; end
            if (fr_ok) begin
                rx_valid <= 1'b1;
                st_match <= (rx_ch == r_s_tx_hdr[31:24]) && (rx_seq == r_s_tx_hdr[23:16]);
            end
            if (fr_err)       st_crc_err <= 1'b1;
            if (fr_ovf)       st_ovf     <= 1'b1;
            if (xact_timeout) st_timeout <= 1'b1;
            if (xact_done)    st_done    <= 1'b1;
        end
    end

    // ------------------------------------------------------------------
    // H-bus sequencer
    // ------------------------------------------------------------------
    wire        h_sync, h_data, h_running, h_done, h_miss_sticky;
    wire [15:0] h_step, h_lat_last, h_lat_min, h_lat_max;
    wire [31:0] h_ack_ok, h_ack_miss;

    t120_hbus_seq #(.W(H_WIDTH), .DL(8)) u_hbus (
        .clk(pclk), .rstn(presetn), .fall_ev(fall_ev), .rise_ev(rise_ev),
        .rd_addr(h_rd_addr), .rd_data(h_rd_q),
        .start(p_h_start), .stop(p_h_stop), .clr(p_h_clr),
        .loop_en(r_h_loop), .ack_en(r_h_ack_en),
        .count(r_h_count), .period(r_h_period),
        .ack_min(r_h_ack_win[7:0]), .ack_max(r_h_ack_win[15:8]),
        .h_sync(h_sync), .h_data(h_data), .ack_in(rx_s2[0]),
        .running(h_running), .done(h_done), .ack_miss_sticky(h_miss_sticky),
        .step(h_step), .ack_ok(h_ack_ok), .ack_miss(h_ack_miss),
        .lat_last(h_lat_last), .lat_min(h_lat_min), .lat_max(h_lat_max),
        .step_strobe(h_step_strobe)
    );
    assign h_active = h_running;

    // ------------------------------------------------------------------
    // T20 CRESET_N
    // ------------------------------------------------------------------
    wire creset_busy;
    wire auto_pulse = r_auto_creset && xact_timeout;
    t120_creset_controller u_creset (
        .clk(pclk), .rstn(presetn), .us_tick(us_tick),
        .level_we(w_creset && !pwdata[1]), .level_val(pwdata[0]),
        .pulse_start(p_creset_pulse || auto_pulse), .pulse_us(r_creset_us),
        .creset_n(t20_creset_n), .busy(creset_busy)
    );

    // ------------------------------------------------------------------
    // Pins
    // ------------------------------------------------------------------
    assign t20_clk9 = r_manual ? r_man_clk : clk9;
    assign t20_tx   = r_manual ? r_man_tx  : {sb_sym[1], sb_sym[0], h_data, h_sync};

    // ------------------------------------------------------------------
    // Interrupt and APB read
    // ------------------------------------------------------------------
    wire [4:0] irq_status = {h_miss_sticky, h_done, st_done, st_timeout, rx_valid};
    assign irq = |(r_irq_en & irq_status);

    always_comb begin
        prdata = 32'd0;
        if (paddr[11:10] == 2'b10) begin
            prdata = rx_rd_q;
        end else if (reg_sel) begin
            case (ra)
                6'h00: prdata = 32'h5432_0102;
                6'h01: prdata = {21'd0, r_rx_dly, 6'd0, r_manual, r_clk_en};
                6'h02: prdata = {20'd0, r_period};
                6'h03: prdata = {27'd0, r_man_tx, r_man_clk};
                6'h04: prdata = {24'd0, rx_s2};
                6'h05: prdata = {23'd0, creset_busy, 7'd0, t20_creset_n};
                6'h06: prdata = {8'd0, r_creset_us};
                6'h07: prdata = {27'd0, r_irq_en};
                6'h08: prdata = {27'd0, irq_status};
                6'h10: prdata = {27'd0, r_auto_creset, r_no_ack, 3'd0};
                6'h11: prdata = {24'd0, st_match, st_done, st_ovf, st_timeout, st_crc_err,
                                 rx_valid, xact_busy, sb_tx_busy};
                6'h12: prdata = r_s_tx_hdr;
                6'h13: prdata = {rx_resp, rx_ch, rx_seq, 8'd0};
                6'h14: prdata = {21'd0, rx_len};
                6'h15: prdata = r_s_timeout;
                6'h20: prdata = {22'd0, r_h_ack_en, r_h_loop, 8'd0};
                6'h21: prdata = {29'd0, h_miss_sticky, h_done, h_running};
                6'h22: prdata = {16'd0, r_h_count};
                6'h23: prdata = {16'd0, r_h_period};
                6'h24: prdata = {16'd0, r_h_ack_win};
                6'h25: prdata = {16'd0, h_step};
                6'h26: prdata = h_ack_ok;
                6'h27: prdata = h_ack_miss;
                6'h28: prdata = {16'd0, h_lat_last};
                6'h29: prdata = {16'd0, h_lat_min};
                6'h2A: prdata = {16'd0, h_lat_max};
                6'h2B: prdata = H_WIDTH;
                default: prdata = 32'd0;
            endcase
        end
    end
endmodule
`default_nettype wire
