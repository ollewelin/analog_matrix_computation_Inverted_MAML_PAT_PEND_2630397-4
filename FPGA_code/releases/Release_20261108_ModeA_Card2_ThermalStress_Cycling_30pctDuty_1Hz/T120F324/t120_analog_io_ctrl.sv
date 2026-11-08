// =============================================================================
// t120_analog_io_ctrl.sv : T120 Analog DAC, ADC & 10.000 ms Autonomous Frame Engine
// =============================================================================
// Mapped at APB3 Base 0xF810_4000 in T120F324/top_level.sv.
//
// Responsibilities:
//   1. Parallel 8-bit 74HC595 Shift-Register DAC Driver across all 4 banks:
//        - Bank 0: DAC_2 (6 ch, Input Row Drive x, differential around 128)
//        - Bank 1: W_15  (8 ch, Matrix 3 Weight Charging, differential around 128)
//        - Bank 2: W_12  (8 ch, Matrix 8 Weight Charging, differential around 128)
//        - Bank 3: W_34  (8 ch, Matrix 33 Weight Charging + trim-DAC 38)
//   2. Hardware 10 Hz 3-State (255 -> 128 -> 0) Oscilloscope Swing Pattern
//      generator + Single-DAC Static Override mode.
//   3. Dual-Bank 6-Channel XC2361A 12-bit Serial SAR ADC Controller (ADC_45 & ADC_49)
//      with hardware-interlocked 4-Phase Settle-Then-Sample sequencing.
//   4. Rock-Solid Crystal-Locked 10.000000 ms (500,000 cycles @ 50.000 MHz)
//      Pure Verilog Autonomous Refresh & Hadamard Frame Engine:
//        - Zero CPU/C-code involvement in Refresh or Hadamard timing (0.00 ns jitter).
//        - Phase 1 (t = 0.000 .. 1.020 ms): Autonomous 6-Column Differential 2T1C
//          Refresh (G_N then G_P) from Shadow Weight RAM (0x400..0x5FF) + S-bus
//          PULSE_COL_GATES to T20.
//        - Phase 2: Cycle-exact hardware countdown to r_hw_stratum_cycles.
//        - Phase 3: Hardware 16x-averaged quiet Forward-Pass ADC_45/ADC_49 read,
//          Sub-Window A (Matrix 8 0x3F00, 14x 2.00 us Sylvester H_8 Simplex burst
//          -> cap49_ram), 20 us Tri-State Hi-Z gap, Sub-Window B (Matrix 3 0x003F,
//          14x 2.00 us burst -> cap45_ram), return to Hi-Z (0x8000), and automatic
//          S-bus Heater/Watchdog/LED sync.
// =============================================================================
`timescale 1ns / 1ps
`default_nettype none

module t120_analog_io_ctrl (
    input  wire         pclk,
    input  wire         presetn,

    // APB3 Slave Interface (0xF810_4000..0xF810_4FFF)
    input  wire         psel,
    input  wire         penable,
    input  wire         pwrite,
    input  wire [11:0]  paddr,
    input  wire [31:0]  pwdata,
    output logic [31:0] prdata,
    output wire         pready,
    output wire         pslverr,

    // Hardware Handshake with t120_inter_fpga_bridge (H-bus Sequencer)
    input  wire         h_latch_strobe,
    input  wire [3:0]   h_step_idx,
    input  wire         h_active,
    output logic        h_hold_busy,
    output logic        quiet_bus_freeze,

    // Master Control Port to t120_inter_fpga_bridge for Autonomous 10.0 ms Engine
    output wire         hw_auto_active,
    output logic        hw_clk9_sync,
    output logic        hw_clk9_10mhz,
    output logic        hw_sbus_start,
    output logic [31:0] hw_sbus_hdr,
    output logic [31:0] hw_sbus_pay0,
    output logic [31:0] hw_sbus_pay1,
    output logic        hw_hbus_start,
    input  wire         hw_hbus_done,

    // Bank 0: DAC_2 (6 channels)
    output logic [5:0]  si_dac_2,
    output logic [5:0]  sck_dac_2,
    output logic        rck_dac_2,
    output wire         sclr_dac_2,

    // Bank 1: W_15 (8 channels, Matrix 3)
    output logic [7:0]  si_dac_w15,
    output logic [7:0]  sck_dac_w15,
    output logic        rck_dac_w15,
    output wire         sclr_dac_w15,

    // Bank 2: W_12 (8 channels, Matrix 8)
    output logic [7:0]  si_dac_w12,
    output logic [7:0]  sck_dac_w12,
    output logic        rck_dac_w12,
    output wire         sclr_dac_w12,

    // Bank 3: W_34 (8 channels, Matrix 33 + trim-DAC 38)
    output logic [7:0]  si_dac_w34,
    output logic [7:0]  sck_dac_w34,
    output logic        rck_dac_w34,
    output wire         sclr_dac_w34,

    // ADC_45 (6 channels, Intermediate Layer 1 Output)
    input  wire  [5:0]  out_adc_45,
    output logic        adc_45_conv,
    output logic        adc_45_sck_1_2,
    output logic        adc_45_sck_3_4,
    output logic        adc_45_sck_5_6,

    // ADC_49 (6 channels, Final Summed Output)
    input  wire  [5:0]  out_adc_49,
    output logic        adc_49_conv,
    output logic        adc_49_sck_1_2,
    output logic        adc_49_sck_3_4,
    output logic        adc_49_sck_5_6
);
    assign pready  = 1'b1;
    assign pslverr = 1'b0;

    // =========================================================================
    // Configuration & Shadow Registers
    // =========================================================================
    logic        r_dac_sclr_n;
    logic        r_osc_10hz_en;
    logic        r_ovr_en;
    logic        r_auto_h_adc_en;
    logic        r_adc_conv_mode; // 0: pulse CONV high then read; 1: CS# low frame
    logic        r_pi_inv_en;
    logic [1:0]  r_adc_bit_align; // 0: [13:2], 1: [14:3], 2: [11:0], 3: [15:4]
    logic [3:0]  r_sck_div;

    logic [15:0] r_settle_cycles; // Default 100 (2.00 us @ 50 MHz)
    logic [7:0]  r_conv_cycles;   // Default 25  (500 ns @ 50 MHz)

    logic [7:0]  r_ovr_val;
    logic [2:0]  r_ovr_ch;
    logic [1:0]  r_ovr_bank;

    // 32-bit packed DAC shadow registers (initialized to 0x01 = bitrev8(128) center)
    logic [31:0] r_dac2_lo, r_dac2_hi;
    logic [31:0] r_w15_lo,  r_w15_hi;
    logic [31:0] r_w12_lo,  r_w12_hi;
    logic [31:0] r_w34_lo,  r_w34_hi;

    // Inverse permutation table pi_inv[0..15] packed into two 32-bit registers
    logic [31:0] r_pi_inv_lo; // {pi_inv[7], ..., pi_inv[0]}
    logic [31:0] r_pi_inv_hi; // {pi_inv[15], ..., pi_inv[8]}

    // Autonomous Hardware 10.000000 ms Frame Engine Registers
    logic        r_hw_auto_en;
    logic        r_hw_had_en;
    logic [7:0]  r_hw_gate_clk9;
    logic [23:0] r_hw_stratum_cycles;
    logic [31:0] r_hw_heater_cfg; // [0]=armed, [15:8]=d0, [23:16]=d1, [31:24]=d2
    logic [31:0] r_hw_heater_led; // [7:0]=d3, [8]=comp_led, [9]=mat33_led

    assign hw_auto_active = r_hw_auto_en && !r_osc_10hz_en && !r_ovr_en;

    assign sclr_dac_2   = r_dac_sclr_n;
    assign sclr_dac_w15 = r_dac_sclr_n;
    assign sclr_dac_w12 = r_dac_sclr_n;
    assign sclr_dac_w34 = r_dac_sclr_n;

    wire apb_wr = psel && penable && pwrite;
    wire is_reg = (paddr[11:8] == 4'h0);
    wire [5:0] ra = paddr[7:2];

    logic [3:0] cmd_dac_load;
    logic       cmd_adc_trig;
    logic       init_dac_kick;
    logic       dac2_pend_auto;

    // =========================================================================
    // Shadow Weight Block RAM (128 x 32-bit at APB 0x400..0x5FF)
    //   Address = {half_col_step[3:0], word_idx[2:0]}
    //   where half_col_step = {col[2:0], is_pos} (0..11)
    //   and word_idx: 0=w15_lo, 1=w15_hi, 2=w12_lo, 3=w12_hi, 4=w34_lo, 5=w34_hi
    // =========================================================================
    (* ram_style = "block" *) reg [31:0] shadow_w_ram [0:127];
    integer sw_i;
    initial begin
        for (sw_i = 0; sw_i < 128; sw_i = sw_i + 1) begin
            shadow_w_ram[sw_i] = 32'h0101_0101; // bitrev8(128) = 0x01 (1.65V center)
        end
    end

    logic [6:0]  sh_w_raddr;
    logic [31:0] sh_w_rd_q;
    always_ff @(posedge pclk) begin
        if (apb_wr && (paddr[11:9] == 3'b010)) begin
            shadow_w_ram[paddr[8:2]] <= pwdata;
        end
        sh_w_rd_q <= shadow_w_ram[sh_w_raddr];
    end

    // =========================================================================
    // 10 Hz 3-State (255 -> 128 -> 0) Oscilloscope Pattern Generator
    // =========================================================================
    localparam [22:0] OSC_10HZ_PERIOD = 23'd5_000_000; // 100 ms @ 50 MHz
    logic [22:0] osc_cnt;
    logic [1:0]  osc_state; // 0: 255, 1: 128, 2: 0
    logic        osc_trig;

    always_ff @(posedge pclk or negedge presetn) begin
        if (!presetn) begin
            osc_cnt   <= 23'd0;
            osc_state <= 2'd0;
            osc_trig  <= 1'b0;
        end else begin
            osc_trig <= 1'b0;
            if (!r_osc_10hz_en) begin
                osc_cnt   <= 23'd0;
                osc_state <= 2'd0;
            end else if (osc_cnt >= OSC_10HZ_PERIOD - 23'd1) begin
                osc_cnt   <= 23'd0;
                osc_state <= (osc_state == 2'd2) ? 2'd0 : (osc_state + 2'd1);
                osc_trig  <= 1'b1;
            end else begin
                osc_cnt <= osc_cnt + 23'd1;
            end
        end
    end

    wire [7:0] osc_code = (osc_state == 2'd0) ? 8'd255 :
                          (osc_state == 2'd1) ? 8'd128 : 8'd0;

    // =========================================================================
    // Pure Verilog 10.000000 ms (500,000 cycles @ 50.000 MHz) Frame Engine
    // =========================================================================
    localparam [18:0] HW_FRAME_PERIOD_CYC = 19'd500_000; // Exact 10.000000 ms

    localparam [3:0]
        HWF_IDLE         = 4'd0,
        HWF_REF_STEP     = 4'd1,
        HWF_STRATUM_WAIT = 4'd2,
        HWF_FWD_ADC      = 4'd3,
        HWF_M8_CFG       = 4'd4,
        HWF_M8_BURST     = 4'd5,
        HWF_GAP_20US     = 4'd6,
        HWF_M3_CFG       = 4'd7,
        HWF_M3_BURST     = 4'd8,
        HWF_EXIT_SYNC    = 4'd9;

    logic [3:0]  hw_fsm_state;
    logic [18:0] frame_timer;
    logic [3:0]  hw_col_step;
    logic [15:0] hw_sub_cnt;
    logic [23:0] hw_stratum_cnt;
    logic [4:0]  hw_avg_cnt;
    logic        hw_adc_armed;
    logic        hw_adc_trig;
    logic [3:0]  hw_dac_load;
    logic        hw_dac2_clr_pend;
    logic [31:0] hw_frame_seq;
    logic [31:0] hw_refresh_cnt;

    logic signed [19:0] fwd_acc45 [0:5];
    logic signed [19:0] fwd_acc49 [0:5];
    logic [15:0]        hw_fwd_adc45 [0:5];
    logic [15:0]        hw_fwd_adc49 [0:5];

    wire hw_pipe_2us_en = hw_auto_active && (hw_fsm_state == HWF_M8_BURST || hw_fsm_state == HWF_M3_BURST);
    wire hw_cap_m8_only = hw_auto_active && (hw_fsm_state == HWF_M8_BURST);
    wire hw_cap_m3_only = hw_auto_active && (hw_fsm_state == HWF_M3_BURST);

    assign sh_w_raddr = {hw_col_step, hw_sub_cnt[2:0]};

    // =========================================================================
    // Register Write Logic & Autonomous Weight Latching
    // =========================================================================
    always_ff @(posedge pclk or negedge presetn) begin
        if (!presetn) begin
            r_dac_sclr_n        <= 1'b1;
            r_osc_10hz_en       <= 1'b0;
            r_ovr_en            <= 1'b0;
            r_auto_h_adc_en     <= 1'b1;
            r_adc_conv_mode     <= 1'b0;
            r_pi_inv_en         <= 1'b1;
            r_adc_bit_align     <= 2'd2;
            r_sck_div           <= 4'd2;
            r_settle_cycles     <= 16'd100; // 2.00 us quiet DC settle @ 50 MHz
            r_conv_cycles       <= 8'd25;   // 500 ns S/H conversion pulse
            r_ovr_val           <= 8'd128;
            r_ovr_ch            <= 3'd0;
            r_ovr_bank          <= 2'd0;
            r_dac2_lo           <= 32'h0101_0101;
            r_dac2_hi           <= 32'h0000_0101;
            r_w15_lo            <= 32'h0101_0101;
            r_w15_hi            <= 32'h0101_0101;
            r_w12_lo            <= 32'h0101_0101;
            r_w12_hi            <= 32'h0101_0101;
            r_w34_lo            <= 32'h0101_0101;
            r_w34_hi            <= 32'h0101_0101;
            r_pi_inv_lo         <= 32'h7654_3210;
            r_pi_inv_hi         <= 32'hFEDC_BA98;
            r_hw_auto_en        <= 1'b0;
            r_hw_had_en         <= 1'b1;
            r_hw_gate_clk9      <= 8'd100;      // 50.00 us @ 2 MHz CLK9
            r_hw_stratum_cycles <= 24'd250_000; // 5000.00 us @ 50 MHz
            r_hw_heater_cfg     <= 32'd0;
            r_hw_heater_led     <= 32'd0;
            cmd_dac_load        <= 4'b0000;
            cmd_adc_trig        <= 1'b0;
            init_dac_kick       <= 1'b1;
            dac2_pend_auto      <= 1'b0;
        end else begin
            cmd_dac_load  <= 4'b0000;
            cmd_adc_trig  <= 1'b0;
            init_dac_kick <= 1'b0;

            if (hw_dac2_clr_pend) begin
                dac2_pend_auto <= 1'b0;
            end

            if (init_dac_kick || osc_trig) begin
                cmd_dac_load <= 4'b1111;
            end

            // Hardware Autonomous Refresh loads W_15, W_12, W_34 from shadow_w_ram
            if (hw_auto_active && (hw_fsm_state == HWF_REF_STEP)) begin
                case (hw_sub_cnt)
                    16'd1: r_w15_lo <= sh_w_rd_q;
                    16'd2: r_w15_hi <= sh_w_rd_q;
                    16'd3: r_w12_lo <= sh_w_rd_q;
                    16'd4: r_w12_hi <= sh_w_rd_q;
                    16'd5: r_w34_lo <= sh_w_rd_q;
                    16'd6: r_w34_hi <= sh_w_rd_q;
                    default: ;
                endcase
            end

            if (apb_wr && is_reg) begin
                case (ra)
                    6'h01: begin // 0x004 CTRL
                        r_dac_sclr_n    <= pwdata[0];
                        r_osc_10hz_en   <= pwdata[1];
                        r_ovr_en        <= pwdata[2];
                        r_auto_h_adc_en <= pwdata[3];
                        r_adc_conv_mode <= pwdata[4];
                        r_pi_inv_en     <= pwdata[5];
                        r_adc_bit_align <= pwdata[7:6];
                        r_sck_div       <= (pwdata[11:8] == 4'd0) ? 4'd1 : pwdata[11:8];
                        if (pwdata[1] != r_osc_10hz_en || pwdata[2] != r_ovr_en)
                            cmd_dac_load <= 4'b1111;
                    end
                    6'h03: begin // 0x00C CMD
                        if (!hw_auto_active) begin
                            cmd_dac_load <= pwdata[3:0];
                            cmd_adc_trig <= pwdata[4];
                        end
                        if (pwdata[5]) begin // dac_center_all
                            r_dac2_lo    <= 32'h0101_0101;
                            r_dac2_hi    <= 32'h0000_0101;
                            r_w15_lo     <= 32'h0101_0101;
                            r_w15_hi     <= 32'h0101_0101;
                            r_w12_lo     <= 32'h0101_0101;
                            r_w12_hi     <= 32'h0101_0101;
                            r_w34_lo     <= 32'h0101_0101;
                            r_w34_hi     <= 32'h0101_0101;
                            if (!hw_auto_active) cmd_dac_load <= 4'b1111;
                        end
                    end
                    6'h04: begin // 0x010 SETTLE_CYCLES
                        r_settle_cycles <= (pwdata[15:0] < 16'd10) ? 16'd10 : pwdata[15:0];
                        r_conv_cycles   <= (pwdata[23:16] < 8'd4)  ? 8'd4   : pwdata[23:16];
                    end
                    6'h05: begin // 0x014 DAC_OVR_CFG
                        r_ovr_val    <= pwdata[7:0];
                        r_ovr_ch     <= pwdata[10:8];
                        r_ovr_bank   <= pwdata[13:12];
                        cmd_dac_load <= 4'b1111;
                    end
                    6'h08: r_dac2_lo <= pwdata;
                    6'h09: begin
                        r_dac2_hi <= pwdata;
                        if (!hw_auto_active) begin
                            cmd_dac_load[0] <= 1'b1;
                        end else if (hw_fsm_state == HWF_STRATUM_WAIT || hw_fsm_state == HWF_IDLE) begin
                            cmd_dac_load[0] <= 1'b1;
                        end else begin
                            dac2_pend_auto <= 1'b1;
                        end
                    end
                    6'h0A: if (!hw_auto_active) r_w15_lo <= pwdata;
                    6'h0B: if (!hw_auto_active) begin r_w15_hi <= pwdata; cmd_dac_load[1] <= 1'b1; end
                    6'h0C: if (!hw_auto_active) r_w12_lo <= pwdata;
                    6'h0D: if (!hw_auto_active) begin r_w12_hi <= pwdata; cmd_dac_load[2] <= 1'b1; end
                    6'h0E: if (!hw_auto_active) r_w34_lo <= pwdata;
                    6'h0F: if (!hw_auto_active) begin r_w34_hi <= pwdata; cmd_dac_load[3] <= 1'b1; end
                    6'h10: r_pi_inv_lo <= pwdata;
                    6'h11: r_pi_inv_hi <= pwdata;
                    6'h20: begin // 0x080 AIO_HW_FRAME_CTRL
                        r_hw_auto_en   <= pwdata[0];
                        r_hw_had_en    <= pwdata[1];
                        r_hw_gate_clk9 <= (pwdata[15:8] < 8'd20) ? 8'd100 : pwdata[15:8];
                    end
                    6'h21: begin // 0x084 AIO_HW_STRATUM_CYC
                        if (pwdata[23:0] < 24'd5_000)
                            r_hw_stratum_cycles <= 24'd5_000;
                        else if (pwdata[23:0] > 24'd380_000)
                            r_hw_stratum_cycles <= 24'd380_000;
                        else
                            r_hw_stratum_cycles <= pwdata[23:0];
                    end
                    6'h22: r_hw_heater_cfg <= pwdata; // 0x088 AIO_HW_HEATER_CFG
                    6'h23: r_hw_heater_led <= pwdata; // 0x08C AIO_HW_HEATER_LED
                    default: ;
                endcase
            end
        end
    end

    // Helper function to select effective 8-bit DAC code for (bank, ch)
    function automatic [7:0] eff_dac_byte(
        input [1:0] bank,
        input [2:0] ch,
        input [7:0] base_val
    );
        begin
            if (r_osc_10hz_en)
                eff_dac_byte = osc_code;
            else if (r_ovr_en && (r_ovr_bank == bank) && (r_ovr_ch == ch))
                eff_dac_byte = r_ovr_val;
            else
                eff_dac_byte = base_val;
        end
    endfunction

    // =========================================================================
    // Parallel 74HC595 Shift-Register DAC Engine (8 bits MSB-first + RCK latch)
    // =========================================================================
    logic       dac_busy;
    logic [3:0] dac_pend_mask;
    logic [3:0] dac_act_mask;
    logic [2:0] dac_state; // 0:IDLE, 1:SETUP, 2:SCK_HI, 3:RCK_HI
    logic [2:0] dac_bit_idx;
    logic [3:0] dac_div_cnt;

    logic [7:0] sh_d2  [0:5];
    logic [7:0] sh_w15 [0:7];
    logic [7:0] sh_w12 [0:7];
    logic [7:0] sh_w34 [0:7];

    wire [3:0] dac_sck_div = hw_auto_active ? 4'd15 : r_sck_div;
    wire [3:0] eff_dac_load = cmd_dac_load | hw_dac_load;

    integer di;
    always_ff @(posedge pclk or negedge presetn) begin
        if (!presetn) begin
            dac_busy      <= 1'b0;
            dac_pend_mask <= 4'b0000;
            dac_act_mask  <= 4'b0000;
            dac_state     <= 3'd0;
            dac_bit_idx   <= 3'd7;
            dac_div_cnt   <= 4'd0;
            si_dac_2      <= 6'd0; sck_dac_2   <= 6'd0; rck_dac_2   <= 1'b0;
            si_dac_w15    <= 8'd0; sck_dac_w15 <= 8'd0; rck_dac_w15 <= 1'b0;
            si_dac_w12    <= 8'd0; sck_dac_w12 <= 8'd0; rck_dac_w12 <= 1'b0;
            si_dac_w34    <= 8'd0; sck_dac_w34 <= 8'd0; rck_dac_w34 <= 1'b0;
            for (di = 0; di < 6; di = di + 1) sh_d2[di]  <= 8'h01;
            for (di = 0; di < 8; di = di + 1) begin
                sh_w15[di] <= 8'h01;
                sh_w12[di] <= 8'h01;
                sh_w34[di] <= 8'h01;
            end
        end else begin
            if (eff_dac_load != 4'b0000)
                dac_pend_mask <= dac_pend_mask | eff_dac_load;

            case (dac_state)
                3'd0: begin // IDLE
                    rck_dac_2   <= 1'b0;
                    rck_dac_w15 <= 1'b0;
                    rck_dac_w12 <= 1'b0;
                    rck_dac_w34 <= 1'b0;
                    // Never shift DACs while quiet_bus_freeze is active!
                    if (dac_pend_mask != 4'b0000 && !quiet_bus_freeze) begin
                        dac_busy      <= 1'b1;
                        dac_act_mask  <= dac_pend_mask;
                        dac_pend_mask <= 4'b0000;
                        dac_bit_idx   <= 3'd7;
                        dac_div_cnt   <= 4'd0;

                        sh_d2[0] <= eff_dac_byte(2'd0, 3'd0, r_dac2_lo[7:0]);
                        sh_d2[1] <= eff_dac_byte(2'd0, 3'd1, r_dac2_lo[15:8]);
                        sh_d2[2] <= eff_dac_byte(2'd0, 3'd2, r_dac2_lo[23:16]);
                        sh_d2[3] <= eff_dac_byte(2'd0, 3'd3, r_dac2_lo[31:24]);
                        sh_d2[4] <= eff_dac_byte(2'd0, 3'd4, r_dac2_hi[7:0]);
                        sh_d2[5] <= eff_dac_byte(2'd0, 3'd5, r_dac2_hi[15:8]);

                        sh_w15[0] <= eff_dac_byte(2'd1, 3'd0, r_w15_lo[7:0]);
                        sh_w15[1] <= eff_dac_byte(2'd1, 3'd1, r_w15_lo[15:8]);
                        sh_w15[2] <= eff_dac_byte(2'd1, 3'd2, r_w15_lo[23:16]);
                        sh_w15[3] <= eff_dac_byte(2'd1, 3'd3, r_w15_lo[31:24]);
                        sh_w15[4] <= eff_dac_byte(2'd1, 3'd4, r_w15_hi[7:0]);
                        sh_w15[5] <= eff_dac_byte(2'd1, 3'd5, r_w15_hi[15:8]);
                        sh_w15[6] <= eff_dac_byte(2'd1, 3'd6, r_w15_hi[23:16]);
                        sh_w15[7] <= eff_dac_byte(2'd1, 3'd7, r_w15_hi[31:24]);

                        sh_w12[0] <= eff_dac_byte(2'd2, 3'd0, r_w12_lo[7:0]);
                        sh_w12[1] <= eff_dac_byte(2'd2, 3'd1, r_w12_lo[15:8]);
                        sh_w12[2] <= eff_dac_byte(2'd2, 3'd2, r_w12_lo[23:16]);
                        sh_w12[3] <= eff_dac_byte(2'd2, 3'd3, r_w12_lo[31:24]);
                        sh_w12[4] <= eff_dac_byte(2'd2, 3'd4, r_w12_hi[7:0]);
                        sh_w12[5] <= eff_dac_byte(2'd2, 3'd5, r_w12_hi[15:8]);
                        sh_w12[6] <= eff_dac_byte(2'd2, 3'd6, r_w12_hi[23:16]);
                        sh_w12[7] <= eff_dac_byte(2'd2, 3'd7, r_w12_hi[31:24]);

                        sh_w34[0] <= eff_dac_byte(2'd3, 3'd0, r_w34_lo[7:0]);
                        sh_w34[1] <= eff_dac_byte(2'd3, 3'd1, r_w34_lo[15:8]);
                        sh_w34[2] <= eff_dac_byte(2'd3, 3'd2, r_w34_lo[23:16]);
                        sh_w34[3] <= eff_dac_byte(2'd3, 3'd3, r_w34_lo[31:24]);
                        sh_w34[4] <= eff_dac_byte(2'd3, 3'd4, r_w34_hi[7:0]);
                        sh_w34[5] <= eff_dac_byte(2'd3, 3'd5, r_w34_hi[15:8]);
                        sh_w34[6] <= eff_dac_byte(2'd3, 3'd6, r_w34_hi[23:16]);
                        sh_w34[7] <= eff_dac_byte(2'd3, 3'd7, r_w34_hi[31:24]);

                        dac_state <= 3'd1;
                    end else begin
                        dac_busy <= 1'b0;
                    end
                end

                3'd1: begin // SETUP SI (SCK LOW)
                    sck_dac_2   <= 6'd0;
                    sck_dac_w15 <= 8'd0;
                    sck_dac_w12 <= 8'd0;
                    sck_dac_w34 <= 8'd0;
                    for (di = 0; di < 6; di = di + 1) si_dac_2[di]   <= sh_d2[di][dac_bit_idx];
                    for (di = 0; di < 8; di = di + 1) begin
                        si_dac_w15[di] <= sh_w15[di][dac_bit_idx];
                        si_dac_w12[di] <= sh_w12[di][dac_bit_idx];
                        si_dac_w34[di] <= sh_w34[di][dac_bit_idx];
                    end
                    if (dac_div_cnt >= dac_sck_div - 4'd1) begin
                        dac_div_cnt <= 4'd0;
                        dac_state   <= 3'd2;
                    end else begin
                        dac_div_cnt <= dac_div_cnt + 4'd1;
                    end
                end

                3'd2: begin // SCK HIGH
                    if (dac_act_mask[0]) sck_dac_2   <= 6'h3F;
                    if (dac_act_mask[1]) sck_dac_w15 <= 8'hFF;
                    if (dac_act_mask[2]) sck_dac_w12 <= 8'hFF;
                    if (dac_act_mask[3]) sck_dac_w34 <= 8'hFF;
                    if (dac_div_cnt >= dac_sck_div - 4'd1) begin
                        dac_div_cnt <= 4'd0;
                        sck_dac_2   <= 6'd0;
                        sck_dac_w15 <= 8'd0;
                        sck_dac_w12 <= 8'd0;
                        sck_dac_w34 <= 8'd0;
                        if (dac_bit_idx == 3'd0) begin
                            dac_state <= 3'd3;
                        end else begin
                            dac_bit_idx <= dac_bit_idx - 3'd1;
                            dac_state   <= 3'd1;
                        end
                    end else begin
                        dac_div_cnt <= dac_div_cnt + 4'd1;
                    end
                end

                3'd3: begin // RCK HIGH LATCH PULSE
                    rck_dac_2   <= dac_act_mask[0];
                    rck_dac_w15 <= dac_act_mask[1];
                    rck_dac_w12 <= dac_act_mask[2];
                    rck_dac_w34 <= dac_act_mask[3];
                    if (dac_div_cnt >= dac_sck_div - 4'd1) begin
                        dac_div_cnt <= 4'd0;
                        rck_dac_2   <= 1'b0;
                        rck_dac_w15 <= 1'b0;
                        rck_dac_w12 <= 1'b0;
                        rck_dac_w34 <= 1'b0;
                        dac_busy    <= 1'b0;
                        dac_state   <= 3'd0;
                    end else begin
                        dac_div_cnt <= dac_div_cnt + 4'd1;
                    end
                end

                default: dac_state <= 3'd0;
            endcase
        end
    end

    // =========================================================================
    // 4-Phase Settle-Then-Sample XC2361A SAR ADC Sequencer (ADC_45 & ADC_49)
    // =========================================================================
    localparam [2:0]
        ADC_IDLE         = 3'd0,
        ADC_QUIET_SETTLE = 3'd1,
        ADC_SH_CONV      = 3'd2,
        ADC_SHIFT_LO     = 3'd3,
        ADC_SHIFT_HI     = 3'd4,
        ADC_STORE        = 3'd5;

    logic [2:0]  adc_state;
    logic        adc_busy;
    logic        adc_is_h_trig;
    logic [3:0]  adc_cap_step;
    logic [15:0] adc_timer;
    logic [4:0]  adc_bit_cnt;
    logic [3:0]  adc_div_cnt;
    logic [15:0] sample_cnt;

    logic [15:0] adc45_sh [0:5];
    logic [15:0] adc49_sh [0:5];

    // Latest raw 12-bit (0..4095) and signed differential Q1.11 (raw - 2048)
    logic [11:0] adc45_raw_lat [0:5];
    logic [11:0] adc49_raw_lat [0:5];
    logic [15:0] adc45_sig_lat [0:5];
    logic [15:0] adc49_sig_lat [0:5];

    // 16-step Hadamard Capture RAM (packed 2 signed 16-bit channels per 32-bit word: 16 steps * 4 words = 64 words)
    (* ram_style = "block" *) reg [31:0] cap45_ram [0:63];
    (* ram_style = "block" *) reg [31:0] cap49_ram [0:63];
    logic [1:0]  store_sub;

    // Synchronize serial SDO inputs
    logic [5:0] sdo45_s1, sdo45_s2;
    logic [5:0] sdo49_s1, sdo49_s2;
    always_ff @(posedge pclk) begin
        sdo45_s1 <= out_adc_45; sdo45_s2 <= sdo45_s1;
        sdo49_s1 <= out_adc_49; sdo49_s2 <= sdo49_s1;
    end

    // Lookup pi_inv[adc_cap_step]
    wire [63:0] pi_inv_vec = {r_pi_inv_hi, r_pi_inv_lo};
    wire [3:0]  pi_inv_lut = pi_inv_vec[{adc_cap_step, 2'b00} +: 4];

    function automatic [11:0] extract_12b(input [15:0] w, input [1:0] align);
        case (align)
            2'd0: extract_12b = w[13:2];
            2'd1: extract_12b = w[14:3];
            2'd2: extract_12b = w[11:0];
            2'd3: extract_12b = w[15:4];
        endcase
    endfunction

    wire [15:0] eff_settle_cycles = hw_pipe_2us_en ? 16'd1  : (hw_auto_active ? 16'd100 : r_settle_cycles);
    wire [7:0]  eff_conv_cycles   = hw_pipe_2us_en ? 8'd21  : (hw_auto_active ? 8'd25   : r_conv_cycles);
    wire [3:0]  adc_sck_div       = hw_pipe_2us_en ? 4'd2   : (hw_auto_active ? 4'd4    : r_sck_div);
    wire        eff_pi_inv_en     = hw_auto_active ? 1'b0   : r_pi_inv_en;

    wire [3:0] dst_step      = eff_pi_inv_en ? pi_inv_lut : adc_cap_step;
    logic      quiet_freeze_q;
    wire       hold_trig     = (h_latch_strobe && (r_auto_h_adc_en || hw_auto_active)) ||
                               (hw_auto_active ? hw_adc_trig : cmd_adc_trig);
    wire       pipe_2us_mode = (eff_settle_cycles <= 16'd4);

    always_comb begin
        h_hold_busy      = pipe_2us_mode ? 1'b0 : (adc_busy || hold_trig);
        quiet_bus_freeze = pipe_2us_mode ? 1'b0 : (quiet_freeze_q || hold_trig);
    end

    integer ai;
    always_ff @(posedge pclk or negedge presetn) begin
        if (!presetn) begin
            adc_state        <= ADC_IDLE;
            adc_busy         <= 1'b0;
            quiet_freeze_q   <= 1'b0;
            adc_is_h_trig    <= 1'b0;
            adc_cap_step     <= 4'd0;
            adc_timer        <= 16'd0;
            adc_bit_cnt      <= 5'd0;
            adc_div_cnt      <= 4'd0;
            sample_cnt       <= 16'd0;
            store_sub        <= 2'd0;
            adc_45_conv      <= 1'b0;
            adc_49_conv      <= 1'b0;
            adc_45_sck_1_2   <= 1'b0; adc_45_sck_3_4 <= 1'b0; adc_45_sck_5_6 <= 1'b0;
            adc_49_sck_1_2   <= 1'b0; adc_49_sck_3_4 <= 1'b0; adc_49_sck_5_6 <= 1'b0;
            for (ai = 0; ai < 6; ai = ai + 1) begin
                adc45_sh[ai]      <= 16'd0;
                adc49_sh[ai]      <= 16'd0;
                adc45_raw_lat[ai] <= 12'd2048;
                adc49_raw_lat[ai] <= 12'd2048;
                adc45_sig_lat[ai] <= 16'd0;
                adc49_sig_lat[ai] <= 16'd0;
            end
        end else begin
            case (adc_state)
                ADC_IDLE: begin
                    adc_45_conv    <= r_adc_conv_mode ? 1'b1 : 1'b0;
                    adc_49_conv    <= r_adc_conv_mode ? 1'b1 : 1'b0;
                    adc_45_sck_1_2 <= 1'b0; adc_45_sck_3_4 <= 1'b0; adc_45_sck_5_6 <= 1'b0;
                    adc_49_sck_1_2 <= 1'b0; adc_49_sck_3_4 <= 1'b0; adc_49_sck_5_6 <= 1'b0;

                    if (hold_trig) begin
                        adc_busy         <= 1'b1;
                        quiet_freeze_q   <= 1'b1;
                        adc_is_h_trig    <= (h_latch_strobe && (r_auto_h_adc_en || hw_auto_active));
                        adc_cap_step     <= h_step_idx;
                        adc_timer        <= 16'd0;
                        adc_state        <= ADC_QUIET_SETTLE;
                    end else begin
                        adc_busy         <= 1'b0;
                        quiet_freeze_q   <= 1'b0;
                    end
                end

                // Phase 2: Quiet Analog DC Settling Window
                ADC_QUIET_SETTLE: begin
                    if (adc_timer >= eff_settle_cycles - 16'd1) begin
                        adc_timer   <= 16'd0;
                        adc_45_conv <= r_adc_conv_mode ? 1'b0 : 1'b1;
                        adc_49_conv <= r_adc_conv_mode ? 1'b0 : 1'b1;
                        adc_state   <= ADC_SH_CONV;
                    end else begin
                        adc_timer <= adc_timer + 16'd1;
                    end
                end

                // Phase 3a: S/H Conversion Aperture
                ADC_SH_CONV: begin
                    if (r_adc_conv_mode || (adc_timer >= {8'd0, eff_conv_cycles} - 16'd1)) begin
                        adc_timer        <= 16'd0;
                        adc_45_conv      <= 1'b0;
                        adc_49_conv      <= 1'b0;
                        quiet_freeze_q   <= 1'b0;
                        adc_bit_cnt      <= 5'd0;
                        adc_div_cnt      <= 4'd0;
                        for (ai = 0; ai < 6; ai = ai + 1) begin
                            adc45_sh[ai] <= 16'd0;
                            adc49_sh[ai] <= 16'd0;
                        end
                        adc_state <= ADC_SHIFT_LO;
                    end else begin
                        adc_timer <= adc_timer + 16'd1;
                    end
                end

                // Phase 3b: Serial Clock Low phase
                ADC_SHIFT_LO: begin
                    adc_45_sck_1_2 <= 1'b0; adc_45_sck_3_4 <= 1'b0; adc_45_sck_5_6 <= 1'b0;
                    adc_49_sck_1_2 <= 1'b0; adc_49_sck_3_4 <= 1'b0; adc_49_sck_5_6 <= 1'b0;
                    if (adc_div_cnt >= adc_sck_div - 4'd1) begin
                        adc_div_cnt    <= 4'd0;
                        adc_45_sck_1_2 <= 1'b1; adc_45_sck_3_4 <= 1'b1; adc_45_sck_5_6 <= 1'b1;
                        adc_49_sck_1_2 <= 1'b1; adc_49_sck_3_4 <= 1'b1; adc_49_sck_5_6 <= 1'b1;
                        adc_state      <= ADC_SHIFT_HI;
                    end else begin
                        adc_div_cnt <= adc_div_cnt + 4'd1;
                    end
                end

                // Phase 3b: Serial Clock High phase & Sample SDO
                ADC_SHIFT_HI: begin
                    if (adc_div_cnt >= adc_sck_div - 4'd1) begin
                        adc_div_cnt    <= 4'd0;
                        adc_45_sck_1_2 <= 1'b0; adc_45_sck_3_4 <= 1'b0; adc_45_sck_5_6 <= 1'b0;
                        adc_49_sck_1_2 <= 1'b0; adc_49_sck_3_4 <= 1'b0; adc_49_sck_5_6 <= 1'b0;
                        for (ai = 0; ai < 6; ai = ai + 1) begin
                            adc45_sh[ai] <= {adc45_sh[ai][14:0], sdo45_s2[ai]};
                            adc49_sh[ai] <= {adc49_sh[ai][14:0], sdo49_s2[ai]};
                        end
                        if (adc_bit_cnt == 5'd15) begin
                            adc_45_conv <= r_adc_conv_mode ? 1'b1 : 1'b0;
                            adc_49_conv <= r_adc_conv_mode ? 1'b1 : 1'b0;
                            store_sub   <= 2'd0;
                            adc_state   <= ADC_STORE;
                        end else begin
                            adc_bit_cnt <= adc_bit_cnt + 5'd1;
                            adc_state   <= ADC_SHIFT_LO;
                        end
                    end else begin
                        adc_div_cnt <= adc_div_cnt + 4'd1;
                    end
                end

                // Phase 3c & Phase 4: Differential (-2048) conversion & Capture RAM store
                ADC_STORE: begin
                    if (store_sub == 2'd0) begin
                        for (ai = 0; ai < 6; ai = ai + 1) begin
                            adc45_raw_lat[ai] <= extract_12b(adc45_sh[ai], r_adc_bit_align);
                            adc49_raw_lat[ai] <= extract_12b(adc49_sh[ai], r_adc_bit_align);
                            adc45_sig_lat[ai] <= {4'd0, extract_12b(adc45_sh[ai], r_adc_bit_align)} - 16'd2048;
                            adc49_sig_lat[ai] <= {4'd0, extract_12b(adc49_sh[ai], r_adc_bit_align)} - 16'd2048;
                        end
                        store_sub <= 2'd1;
                    end else if (store_sub == 2'd1) begin
                        store_sub <= 2'd2;
                    end else if (store_sub == 2'd2) begin
                        store_sub <= 2'd3;
                    end else begin
                        sample_cnt       <= sample_cnt + 16'd1;
                        quiet_freeze_q   <= 1'b0;
                        adc_busy         <= 1'b0;
                        adc_state        <= ADC_IDLE;
                    end
                end

                default: adc_state <= ADC_IDLE;
            endcase
        end
    end

    // =========================================================================
    // Pure Verilog 10.000000 ms Master Frame State Machine
    // =========================================================================
    wire [2:0] cur_ref_col    = hw_col_step[3:1];
    wire       cur_ref_is_pos = hw_col_step[0];

    integer fi;
    always_ff @(posedge pclk or negedge presetn) begin
        if (!presetn) begin
            frame_timer      <= 19'd0;
            hw_fsm_state     <= HWF_IDLE;
            hw_col_step      <= 4'd0;
            hw_sub_cnt       <= 16'd0;
            hw_stratum_cnt   <= 24'd0;
            hw_avg_cnt       <= 5'd0;
            hw_adc_armed     <= 1'b0;
            hw_adc_trig      <= 1'b0;
            hw_dac_load      <= 4'b0000;
            hw_dac2_clr_pend <= 1'b0;
            hw_clk9_sync     <= 1'b0;
            hw_clk9_10mhz    <= 1'b0;
            hw_sbus_start    <= 1'b0;
            hw_sbus_hdr      <= 32'd0;
            hw_sbus_pay0     <= 32'd0;
            hw_sbus_pay1     <= 32'd0;
            hw_hbus_start    <= 1'b0;
            hw_frame_seq     <= 32'd0;
            hw_refresh_cnt   <= 32'd0;
            for (fi = 0; fi < 6; fi = fi + 1) begin
                fwd_acc45[fi]    <= 20'sd0;
                fwd_acc49[fi]    <= 20'sd0;
                hw_fwd_adc45[fi] <= 16'd0;
                hw_fwd_adc49[fi] <= 16'd0;
            end
        end else begin
            hw_adc_trig      <= 1'b0;
            hw_dac_load      <= 4'b0000;
            hw_dac2_clr_pend <= 1'b0;
            hw_clk9_sync     <= 1'b0;
            hw_sbus_start    <= 1'b0;
            hw_hbus_start    <= 1'b0;

            if (!hw_auto_active) begin
                frame_timer   <= 19'd0;
                hw_fsm_state  <= HWF_IDLE;
                hw_clk9_10mhz <= 1'b0;
            end else begin
                // Modulo-500,000 Crystal-Locked 10.000000 ms Counter (0.00 ns jitter!)
                if (frame_timer == HW_FRAME_PERIOD_CYC - 19'd1) begin
                    frame_timer <= 19'd0;
                end else begin
                    frame_timer <= frame_timer + 19'd1;
                end

                // Trigger exact 10.000000 ms frame start at frame_timer == 0
                if (frame_timer == 19'd0) begin
                    hw_clk9_10mhz    <= 1'b0;
                    hw_clk9_sync     <= 1'b1; // Phase-lock 2.0 MHz CLK9 to t = 0.000000 ms!
                    hw_col_step      <= 4'd0;
                    hw_sub_cnt       <= 16'd0;
                    hw_dac2_clr_pend <= 1'b1;
                    hw_fsm_state     <= HWF_REF_STEP;
                end else begin
                    case (hw_fsm_state)
                        // ---------------------------------------------------------
                        // Phase 1: 6-Column Differential 2T1C Refresh (12 x 85.00 us = 1.020 ms)
                        // ---------------------------------------------------------
                        HWF_REF_STEP: begin
                            if (hw_sub_cnt == 16'd6) begin
                                hw_dac_load <= (hw_col_step == 4'd0) ? 4'b1111 : 4'b1110;
                            end else if (hw_sub_cnt == 16'd550) begin
                                // After 5.4 us DAC shift + 5.6 us op-amp settle: pulse T20 column gates!
                                hw_sbus_hdr   <= 32'h05_04_0004;
                                hw_sbus_pay0  <= {8'd0, r_hw_gate_clk9,
                                                  (cur_ref_is_pos ? 8'h07 : 8'h70),
                                                  (8'h01 << cur_ref_col)};
                                hw_sbus_start <= 1'b1;
                            end

                            if (hw_sub_cnt >= 16'd4499) begin
                                hw_sub_cnt <= 16'd0;
                                if (hw_col_step == 4'd11) begin
                                    hw_refresh_cnt <= hw_refresh_cnt + 32'd1;
                                    hw_stratum_cnt <= 24'd0;
                                    if (dac2_pend_auto) begin
                                        hw_dac_load      <= 4'b0001;
                                        hw_dac2_clr_pend <= 1'b1;
                                    end
                                    hw_fsm_state <= HWF_STRATUM_WAIT;
                                end else begin
                                    hw_col_step <= hw_col_step + 4'd1;
                                end
                            end else begin
                                hw_sub_cnt <= hw_sub_cnt + 16'd1;
                            end
                        end

                        // ---------------------------------------------------------
                        // Phase 2: Exact Hardware Stratum Settling Countdown
                        // ---------------------------------------------------------
                        HWF_STRATUM_WAIT: begin
                            if (hw_stratum_cnt >= r_hw_stratum_cycles - 24'd1) begin
                                hw_stratum_cnt <= 24'd0;
                                for (fi = 0; fi < 6; fi = fi + 1) begin
                                    fwd_acc45[fi] <= 20'sd0;
                                    fwd_acc49[fi] <= 20'sd0;
                                end
                                hw_avg_cnt   <= 5'd0;
                                hw_adc_armed <= 1'b1;
                                hw_fsm_state <= HWF_FWD_ADC;
                            end else begin
                                hw_stratum_cnt <= hw_stratum_cnt + 24'd1;
                            end
                        end

                        // ---------------------------------------------------------
                        // Phase 3a: 16x Hardware-Averaged Quiet Forward-Pass ADC Read
                        // ---------------------------------------------------------
                        HWF_FWD_ADC: begin
                            if (hw_adc_armed && adc_state == ADC_IDLE && !adc_busy && !hw_adc_trig) begin
                                hw_adc_trig  <= 1'b1;
                                hw_adc_armed <= 1'b0;
                            end else if (adc_state == ADC_STORE) begin
                                if (store_sub == 2'd1) begin
                                    for (fi = 0; fi < 6; fi = fi + 1) begin
                                        fwd_acc45[fi] <= fwd_acc45[fi] + {{4{adc45_sig_lat[fi][15]}}, adc45_sig_lat[fi]};
                                        fwd_acc49[fi] <= fwd_acc49[fi] + {{4{adc49_sig_lat[fi][15]}}, adc49_sig_lat[fi]};
                                    end
                                end else if (store_sub == 2'd3) begin
                                    if (hw_avg_cnt == 5'd15) begin
                                        for (fi = 0; fi < 6; fi = fi + 1) begin
                                            hw_fwd_adc45[fi] <= (fwd_acc45[fi] + 20'sd8) >>> 4;
                                            hw_fwd_adc49[fi] <= (fwd_acc49[fi] + 20'sd8) >>> 4;
                                        end
                                        hw_sub_cnt   <= 16'd0;
                                        hw_fsm_state <= r_hw_had_en ? HWF_M8_CFG : HWF_EXIT_SYNC;
                                    end else begin
                                        hw_avg_cnt   <= hw_avg_cnt + 5'd1;
                                        hw_adc_armed <= 1'b1;
                                    end
                                end
                            end
                        end

                        // ---------------------------------------------------------
                        // Phase 3b: Configure T20 for Sub-Window A (Matrix 8 = 0x3F00)
                        // ---------------------------------------------------------
                        HWF_M8_CFG: begin
                            if (hw_sub_cnt == 16'd0) begin
                                // CH 0x02 OP 0x1 SET_EN = 0x3F00 (big endian: pay[0]=0x3F, pay[1]=0x00)
                                hw_sbus_hdr   <= 32'h02_01_0002;
                                hw_sbus_pay0  <= 32'h0000_003F;
                                hw_sbus_start <= 1'b1;
                            end else if (hw_sub_cnt == 16'd1250) begin
                                // CH 0x02 OP 0x2 SET_STATIC (static_on=0, vec=0x8000)
                                hw_sbus_hdr   <= 32'h02_02_0003;
                                hw_sbus_pay0  <= 32'h0000_8000;
                                hw_sbus_start <= 1'b1;
                            end

                            if (hw_sub_cnt >= 16'd2499) begin
                                hw_sub_cnt    <= 16'd0;
                                hw_clk9_10mhz <= 1'b1;
                                hw_clk9_sync  <= 1'b1;
                                hw_fsm_state  <= HWF_M8_BURST;
                            end else begin
                                hw_sub_cnt <= hw_sub_cnt + 16'd1;
                            end
                        end

                        // ---------------------------------------------------------
                        // Phase 3c: Sub-Window A Hadamard Burst (14 x 2.00 us on M8 -> cap49_ram)
                        // ---------------------------------------------------------
                        HWF_M8_BURST: begin
                            if (hw_sub_cnt == 16'd2) begin
                                hw_hbus_start <= 1'b1;
                            end

                            if (hw_sub_cnt >= 16'd1799 && !h_active && !adc_busy) begin
                                hw_sub_cnt    <= 16'd0;
                                hw_clk9_10mhz <= 1'b0;
                                hw_clk9_sync  <= 1'b1;
                                hw_fsm_state  <= HWF_GAP_20US;
                            end else begin
                                hw_sub_cnt <= hw_sub_cnt + 16'd1;
                            end
                        end

                        // ---------------------------------------------------------
                        // Phase 3d: 20.00 us Tri-State Hi-Z Separation Gap
                        // ---------------------------------------------------------
                        HWF_GAP_20US: begin
                            if (hw_sub_cnt == 16'd0) begin
                                // CH 0x02 OP 0x2 SET_STATIC (static_on=1, vec=0x8000 -> Hi-Z)
                                hw_sbus_hdr   <= 32'h02_02_0003;
                                hw_sbus_pay0  <= 32'h0000_8001;
                                hw_sbus_start <= 1'b1;
                            end

                            if (hw_sub_cnt >= 16'd2249) begin
                                hw_sub_cnt   <= 16'd0;
                                hw_fsm_state <= HWF_M3_CFG;
                            end else begin
                                hw_sub_cnt <= hw_sub_cnt + 16'd1;
                            end
                        end

                        // ---------------------------------------------------------
                        // Phase 3e: Configure T20 for Sub-Window B (Matrix 3 = 0x003F)
                        // ---------------------------------------------------------
                        HWF_M3_CFG: begin
                            if (hw_sub_cnt == 16'd0) begin
                                // CH 0x02 OP 0x1 SET_EN = 0x003F (big endian: pay[0]=0x00, pay[1]=0x3F)
                                hw_sbus_hdr   <= 32'h02_01_0002;
                                hw_sbus_pay0  <= 32'h0000_3F00;
                                hw_sbus_start <= 1'b1;
                            end else if (hw_sub_cnt == 16'd1250) begin
                                // CH 0x02 OP 0x2 SET_STATIC (static_on=0, vec=0x8000)
                                hw_sbus_hdr   <= 32'h02_02_0003;
                                hw_sbus_pay0  <= 32'h0000_8000;
                                hw_sbus_start <= 1'b1;
                            end

                            if (hw_sub_cnt >= 16'd2499) begin
                                hw_sub_cnt    <= 16'd0;
                                hw_clk9_10mhz <= 1'b1;
                                hw_clk9_sync  <= 1'b1;
                                hw_fsm_state  <= HWF_M3_BURST;
                            end else begin
                                hw_sub_cnt <= hw_sub_cnt + 16'd1;
                            end
                        end

                        // ---------------------------------------------------------
                        // Phase 3f: Sub-Window B Hadamard Burst (14 x 2.00 us on M3 -> cap45_ram)
                        // ---------------------------------------------------------
                        HWF_M3_BURST: begin
                            if (hw_sub_cnt == 16'd2) begin
                                hw_hbus_start <= 1'b1;
                            end

                            if (hw_sub_cnt >= 16'd1799 && !h_active && !adc_busy) begin
                                hw_sub_cnt    <= 16'd0;
                                hw_clk9_10mhz <= 1'b0;
                                hw_clk9_sync  <= 1'b1;
                                hw_fsm_state  <= HWF_EXIT_SYNC;
                            end else begin
                                hw_sub_cnt <= hw_sub_cnt + 16'd1;
                            end
                        end

                        // ---------------------------------------------------------
                        // Phase 3g: Return to 3-State Hi-Z + Sync Heater/Watchdog & LEDs
                        // ---------------------------------------------------------
                        HWF_EXIT_SYNC: begin
                            if (hw_sub_cnt == 16'd0) begin
                                // CH 0x02 OP 0x2 SET_STATIC (static_on=1, vec=0x8000 -> Hi-Z)
                                hw_sbus_hdr   <= 32'h02_02_0003;
                                hw_sbus_pay0  <= 32'h0000_8001;
                                hw_sbus_start <= 1'b1;
                            end else if (hw_sub_cnt == 16'd1250) begin
                                // CH 0x05 OP 0x1 SET_HEATER (refreshes T20 PWM & Watchdog!)
                                hw_sbus_hdr   <= 32'h05_01_0005;
                                hw_sbus_pay0  <= {r_hw_heater_cfg[31:8], 7'd0, r_hw_heater_cfg[0]};
                                hw_sbus_pay1  <= {24'd0, r_hw_heater_led[7:0]};
                                hw_sbus_start <= 1'b1;
                            end else if (hw_sub_cnt == 16'd2500) begin
                                // CH 0x05 OP 0x2 SET_LEDS
                                hw_sbus_hdr   <= 32'h05_02_0002;
                                hw_sbus_pay0  <= {16'd0, 7'd0, r_hw_heater_led[9], 7'd0, r_hw_heater_led[8]};
                                hw_sbus_start <= 1'b1;
                            end

                            if (hw_sub_cnt >= 16'd3749) begin
                                hw_sub_cnt   <= 16'd0;
                                hw_frame_seq <= hw_frame_seq + 32'd1;
                                hw_fsm_state <= HWF_IDLE;
                            end else begin
                                hw_sub_cnt <= hw_sub_cnt + 16'd1;
                            end
                        end

                        default: begin // HWF_IDLE: wait for frame_timer == 0
                            hw_sub_cnt <= 16'd0;
                        end
                    endcase
                end
            end
        end
    end

    // Dedicated Dual-Port Block RAM Write & Read Ports (selective M8/M3 capture in Auto Mode)
    logic        cap_ram_we;
    logic [5:0]  cap_ram_waddr;
    logic [31:0] cap45_ram_wdata, cap49_ram_wdata;

    always_comb begin
        cap_ram_we      = 1'b0;
        cap_ram_waddr   = 6'd0;
        cap45_ram_wdata = 32'd0;
        cap49_ram_wdata = 32'd0;
        if (adc_state == ADC_STORE && adc_is_h_trig) begin
            case (store_sub)
                2'd1: begin
                    cap_ram_we      = 1'b1;
                    cap_ram_waddr   = {dst_step, 2'd0};
                    cap45_ram_wdata = {adc45_sig_lat[1], adc45_sig_lat[0]};
                    cap49_ram_wdata = {adc49_sig_lat[1], adc49_sig_lat[0]};
                end
                2'd2: begin
                    cap_ram_we      = 1'b1;
                    cap_ram_waddr   = {dst_step, 2'd1};
                    cap45_ram_wdata = {adc45_sig_lat[3], adc45_sig_lat[2]};
                    cap49_ram_wdata = {adc49_sig_lat[3], adc49_sig_lat[2]};
                end
                2'd3: begin
                    cap_ram_we      = 1'b1;
                    cap_ram_waddr   = {dst_step, 2'd2};
                    cap45_ram_wdata = {adc45_sig_lat[5], adc45_sig_lat[4]};
                    cap49_ram_wdata = {adc49_sig_lat[5], adc49_sig_lat[4]};
                end
                default: ;
            endcase
        end
    end

    wire cap45_we = cap_ram_we && (!hw_auto_active || hw_cap_m3_only);
    wire cap49_we = cap_ram_we && (!hw_auto_active || hw_cap_m8_only);

    // Synchronous read and write port for Capture RAMs
    logic [31:0] cap45_rd_q, cap49_rd_q;
    always_ff @(posedge pclk) begin
        if (cap45_we) cap45_ram[cap_ram_waddr] <= cap45_ram_wdata;
        if (cap49_we) cap49_ram[cap_ram_waddr] <= cap49_ram_wdata;
        cap45_rd_q <= cap45_ram[paddr[7:2]];
        cap49_rd_q <= cap49_ram[paddr[7:2]];
    end

    // =========================================================================
    // APB3 Read Multiplexer
    // =========================================================================
    always_comb begin
        prdata = 32'd0;
        if (paddr[11:8] == 4'h1) begin
            prdata = cap45_rd_q;
        end else if (paddr[11:8] == 4'h2) begin
            prdata = cap49_rd_q;
        end else if (is_reg) begin
            case (ra)
                6'h00: prdata = 32'h4149_4F31; // "AIO1"
                6'h01: prdata = {20'd0, r_sck_div, r_adc_bit_align, r_pi_inv_en,
                                 r_adc_conv_mode, r_auto_h_adc_en, r_ovr_en, r_osc_10hz_en, r_dac_sclr_n};
                6'h02: prdata = {sample_cnt, 4'd0, adc_cap_step, 2'd0, osc_state,
                                 quiet_bus_freeze, h_hold_busy, adc_busy, dac_busy};
                6'h04: prdata = {8'd0, r_conv_cycles, r_settle_cycles};
                6'h05: prdata = {18'd0, r_ovr_bank, 1'b0, r_ovr_ch, r_ovr_val};
                6'h06: prdata = 32'h2026_1030; // HW Logic Version Date: 2026-10-30 (BCD)
                6'h07: prdata = 32'h4D41_4D31; // HW Logic Subsystem: "MAM1" (Mode A Logic v1)
                6'h08: prdata = r_dac2_lo;
                6'h09: prdata = r_dac2_hi;
                6'h0A: prdata = r_w15_lo;
                6'h0B: prdata = r_w15_hi;
                6'h0C: prdata = r_w12_lo;
                6'h0D: prdata = r_w12_hi;
                6'h0E: prdata = r_w34_lo;
                6'h0F: prdata = r_w34_hi;
                6'h10: prdata = r_pi_inv_lo;
                6'h11: prdata = r_pi_inv_hi;
                // 0x050..0x064: Signed Q1.11 differential ADC readings (raw_12b - 2048)
                6'h14: prdata = {adc45_sig_lat[1], adc45_sig_lat[0]};
                6'h15: prdata = {adc45_sig_lat[3], adc45_sig_lat[2]};
                6'h16: prdata = {adc45_sig_lat[5], adc45_sig_lat[4]};
                6'h17: prdata = {adc49_sig_lat[1], adc49_sig_lat[0]};
                6'h18: prdata = {adc49_sig_lat[3], adc49_sig_lat[2]};
                6'h19: prdata = {adc49_sig_lat[5], adc49_sig_lat[4]};
                // 0x068..0x07C: Raw unsigned 12-bit ADC readings (0..4095)
                6'h1A: prdata = {4'd0, adc45_raw_lat[1], 4'd0, adc45_raw_lat[0]};
                6'h1B: prdata = {4'd0, adc45_raw_lat[3], 4'd0, adc45_raw_lat[2]};
                6'h1C: prdata = {4'd0, adc45_raw_lat[5], 4'd0, adc45_raw_lat[4]};
                6'h1D: prdata = {4'd0, adc49_raw_lat[1], 4'd0, adc49_raw_lat[0]};
                6'h1E: prdata = {4'd0, adc49_raw_lat[3], 4'd0, adc49_raw_lat[2]};
                6'h1F: prdata = {4'd0, adc49_raw_lat[5], 4'd0, adc49_raw_lat[4]};
                // 0x080..0x0B0: Autonomous Hardware 10.000 ms Frame Engine Registers
                6'h20: prdata = {16'd0, r_hw_gate_clk9, 6'd0, r_hw_had_en, r_hw_auto_en};
                6'h21: prdata = {8'd0, r_hw_stratum_cycles};
                6'h22: prdata = r_hw_heater_cfg;
                6'h23: prdata = r_hw_heater_led;
                6'h24: prdata = hw_frame_seq;
                6'h25: prdata = {4'd0, hw_fsm_state, 5'd0, frame_timer};
                6'h26: prdata = {hw_fwd_adc45[1], hw_fwd_adc45[0]};
                6'h27: prdata = {hw_fwd_adc45[3], hw_fwd_adc45[2]};
                6'h28: prdata = {hw_fwd_adc45[5], hw_fwd_adc45[4]};
                6'h29: prdata = {hw_fwd_adc49[1], hw_fwd_adc49[0]};
                6'h2A: prdata = {hw_fwd_adc49[3], hw_fwd_adc49[2]};
                6'h2B: prdata = {hw_fwd_adc49[5], hw_fwd_adc49[4]};
                6'h2C: prdata = hw_refresh_cnt;
                default: prdata = 32'd0;
            endcase
        end
    end

endmodule
`default_nettype wire
