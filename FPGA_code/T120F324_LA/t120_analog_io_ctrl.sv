// =============================================================================
// t120_analog_io_ctrl.sv : T120 Analog DAC & ADC Hardware Engine (APB3 Slave)
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
//      with hardware-interlocked 4-Phase Settle-Then-Sample sequencing:
//        Phase 1: Shift 16-bit Hadamard word over H-bus & latch on T20 (OE=1, +/-)
//        Phase 2: Quiet Analog DC Settling Window (~2.0 us default at 500 kHz,
//                 scaling up to 20.0 us at 50 kHz). T20_CLK9, H-bus, DAC_SCK,
//                 and ADC_SCK are held 100% static low while analog matrix settles.
//        Phase 3: At the END of the quiet DC settling window, assert ADC_CONV to
//                 lock Sample-and-Hold capacitors, shift 12-bit words into T120,
//                 convert to signed differential Q1.11 (raw_12b - 2048), and
//                 scatter-write via pi_inv[step] into Capture RAM.
//        Phase 4: Release h_hold_busy so t120_hbus_seq advances to the next
//                 Hadamard state (ending with 17th word 16'h8000 -> T20 OE=0 Hi-Z).
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
    output logic        adc_49_sck_5_6,

    // Logic Analyzer hardware debug taps
    output wire         dbg_adc_done_1shot,
    output wire  [11:0] dbg_adc45_ch0_raw,
    output wire  [11:0] dbg_adc45_ch1_raw,
    output wire  [11:0] dbg_adc45_ch2_raw,
    output wire  [11:0] dbg_adc45_ch1_sig,
    output wire  [11:0] dbg_adc49_ch2_raw
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
    logic [7:0]  r_conv_cycles;   // Default 30  (600 ns @ 50 MHz)

    logic [7:0]  r_ovr_val;
    logic [2:0]  r_ovr_ch;
    logic [1:0]  r_ovr_bank;

    // 32-bit packed DAC shadow registers (initialized to 0x80 = 128 center)
    logic [31:0] r_dac2_lo, r_dac2_hi;
    logic [31:0] r_w15_lo,  r_w15_hi;
    logic [31:0] r_w12_lo,  r_w12_hi;
    logic [31:0] r_w34_lo,  r_w34_hi;

    // Inverse permutation table pi_inv[0..15] packed into two 32-bit registers
    logic [31:0] r_pi_inv_lo; // {pi_inv[7], ..., pi_inv[0]}
    logic [31:0] r_pi_inv_hi; // {pi_inv[15], ..., pi_inv[8]}

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
    // Register Write Logic
    // =========================================================================
    always_ff @(posedge pclk or negedge presetn) begin
        if (!presetn) begin
            r_dac_sclr_n    <= 1'b1;
            r_osc_10hz_en   <= 1'b0;
            r_ovr_en        <= 1'b0;
            r_auto_h_adc_en <= 1'b1;
            r_adc_conv_mode <= 1'b0;
            r_pi_inv_en     <= 1'b1;
            r_adc_bit_align <= 2'd0;
            r_sck_div       <= 4'd2;
            r_settle_cycles <= 16'd100; // 2.00 us quiet DC settle @ 50 MHz
            r_conv_cycles   <= 8'd25;   // 500 ns S/H conversion pulse
            r_ovr_val       <= 8'd128;
            r_ovr_ch        <= 3'd0;
            r_ovr_bank      <= 2'd0;
            r_dac2_lo       <= 32'h8080_8080;
            r_dac2_hi       <= 32'h0000_8080;
            r_w15_lo        <= 32'h8080_8080;
            r_w15_hi        <= 32'h8080_8080;
            r_w12_lo        <= 32'h8080_8080;
            r_w12_hi        <= 32'h8080_8080;
            r_w34_lo        <= 32'h8080_8080;
            r_w34_hi        <= 32'h8080_8080;
            r_pi_inv_lo     <= 32'h7654_3210;
            r_pi_inv_hi     <= 32'hFEDC_BA98;
            cmd_dac_load    <= 4'b0000;
            cmd_adc_trig    <= 1'b0;
            init_dac_kick   <= 1'b1;
        end else begin
            cmd_dac_load  <= 4'b0000;
            cmd_adc_trig  <= 1'b0;
            init_dac_kick <= 1'b0;

            if (init_dac_kick || osc_trig) begin
                cmd_dac_load <= 4'b1111;
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
                        cmd_dac_load <= pwdata[3:0];
                        cmd_adc_trig <= pwdata[4];
                        if (pwdata[5]) begin // dac_center_all (set all to 128)
                            r_dac2_lo    <= 32'h8080_8080;
                            r_dac2_hi    <= 32'h0000_8080;
                            r_w15_lo     <= 32'h8080_8080;
                            r_w15_hi     <= 32'h8080_8080;
                            r_w12_lo     <= 32'h8080_8080;
                            r_w12_hi     <= 32'h8080_8080;
                            r_w34_lo     <= 32'h8080_8080;
                            r_w34_hi     <= 32'h8080_8080;
                            cmd_dac_load <= 4'b1111;
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
                    6'h08: r_dac2_lo   <= pwdata;
                    6'h09: begin r_dac2_hi <= pwdata; cmd_dac_load[0] <= 1'b1; end
                    6'h0A: r_w15_lo    <= pwdata;
                    6'h0B: begin r_w15_hi  <= pwdata; cmd_dac_load[1] <= 1'b1; end
                    6'h0C: r_w12_lo    <= pwdata;
                    6'h0D: begin r_w12_hi  <= pwdata; cmd_dac_load[2] <= 1'b1; end
                    6'h0E: r_w34_lo    <= pwdata;
                    6'h0F: begin r_w34_hi  <= pwdata; cmd_dac_load[3] <= 1'b1; end
                    6'h10: r_pi_inv_lo <= pwdata;
                    6'h11: r_pi_inv_hi <= pwdata;
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
            for (di = 0; di < 6; di = di + 1) sh_d2[di]  <= 8'd128;
            for (di = 0; di < 8; di = di + 1) begin
                sh_w15[di] <= 8'd128;
                sh_w12[di] <= 8'd128;
                sh_w34[di] <= 8'd128;
            end
        end else begin
            if (cmd_dac_load != 4'b0000)
                dac_pend_mask <= dac_pend_mask | cmd_dac_load;

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
                    if (dac_div_cnt >= r_sck_div - 4'd1) begin
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
                    if (dac_div_cnt >= r_sck_div - 4'd1) begin
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
                    if (dac_div_cnt >= r_sck_div - 4'd1) begin
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

    wire [3:0] dst_step      = r_pi_inv_en ? pi_inv_lut : adc_cap_step;
    logic      quiet_freeze_q;
    wire       hold_trig     = (h_latch_strobe && r_auto_h_adc_en) || cmd_adc_trig;
    wire       pipe_2us_mode = (r_settle_cycles <= 16'd4);

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
                        quiet_freeze_q   <= 1'b1; // Freeze T20_CLK9 & DAC shifting during quiet DC settle!
                        adc_is_h_trig    <= (h_latch_strobe && r_auto_h_adc_en);
                        adc_cap_step     <= h_step_idx;
                        adc_timer        <= 16'd0;
                        adc_state        <= ADC_QUIET_SETTLE;
                    end else begin
                        adc_busy         <= 1'b0;
                        quiet_freeze_q   <= 1'b0;
                    end
                end

                // Phase 2: Quiet Analog DC Settling Window (~2.0 us at 500 kHz, up to 20.0 us at 50 kHz)
                ADC_QUIET_SETTLE: begin
                    if (adc_timer >= r_settle_cycles - 16'd1) begin
                        adc_timer <= 16'd0;
                        // Phase 3a: Lock Sample-and-Hold Capacitors at the END of the quiet DC settling window!
                        adc_45_conv <= r_adc_conv_mode ? 1'b0 : 1'b1;
                        adc_49_conv <= r_adc_conv_mode ? 1'b0 : 1'b1;
                        adc_state   <= ADC_SH_CONV;
                    end else begin
                        adc_timer <= adc_timer + 16'd1;
                    end
                end

                // Phase 3a: S/H Conversion Aperture (while digital clocks remain 100% static)
                ADC_SH_CONV: begin
                    if (r_adc_conv_mode || (adc_timer >= {8'd0, r_conv_cycles} - 16'd1)) begin
                        adc_timer        <= 16'd0;
                        adc_45_conv      <= 1'b0;
                        adc_49_conv      <= 1'b0;
                        quiet_freeze_q   <= 1'b0; // S/H capacitor is now locked; allow ADC_SCK shifting while h_hold_busy keeps T20_CLK9 frozen!
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
                    if (adc_div_cnt >= r_sck_div - 4'd1) begin
                        adc_div_cnt <= 4'd0;
                        adc_45_sck_1_2 <= 1'b1; adc_45_sck_3_4 <= 1'b1; adc_45_sck_5_6 <= 1'b1;
                        adc_49_sck_1_2 <= 1'b1; adc_49_sck_3_4 <= 1'b1; adc_49_sck_5_6 <= 1'b1;
                        adc_state   <= ADC_SHIFT_HI;
                    end else begin
                        adc_div_cnt <= adc_div_cnt + 4'd1;
                    end
                end

                // Phase 3b: Serial Clock High phase & Sample SDO
                ADC_SHIFT_HI: begin
                    if (adc_div_cnt >= r_sck_div - 4'd1) begin
                        adc_div_cnt <= 4'd0;
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

                // Phase 3c & Phase 4: Differential (-2048) conversion, Capture RAM store & Release Next Hadamard State
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
                        if (adc_is_h_trig) begin
                            cap45_ram[{dst_step, 2'd0}] <= {adc45_sig_lat[1], adc45_sig_lat[0]};
                            cap49_ram[{dst_step, 2'd0}] <= {adc49_sig_lat[1], adc49_sig_lat[0]};
                        end
                        store_sub <= 2'd2;
                    end else if (store_sub == 2'd2) begin
                        if (adc_is_h_trig) begin
                            cap45_ram[{dst_step, 2'd1}] <= {adc45_sig_lat[3], adc45_sig_lat[2]};
                            cap49_ram[{dst_step, 2'd1}] <= {adc49_sig_lat[3], adc49_sig_lat[2]};
                        end
                        store_sub <= 2'd3;
                    end else begin
                        if (adc_is_h_trig) begin
                            cap45_ram[{dst_step, 2'd2}] <= {adc45_sig_lat[5], adc45_sig_lat[4]};
                            cap49_ram[{dst_step, 2'd2}] <= {adc49_sig_lat[5], adc49_sig_lat[4]};
                        end
                        sample_cnt       <= sample_cnt + 16'd1;
                        quiet_freeze_q   <= 1'b0;
                        adc_busy         <= 1'b0; // Releases h_hold_busy so H-bus sequencer shifts next Hadamard state!
                        adc_state        <= ADC_IDLE;
                    end
                end

                default: adc_state <= ADC_IDLE;
            endcase
        end
    end

    // Synchronous read port for Capture RAMs
    logic [31:0] cap45_rd_q, cap49_rd_q;
    always_ff @(posedge pclk) begin
        cap45_rd_q <= cap45_ram[paddr[7:2]];
        cap49_rd_q <= cap49_ram[paddr[7:2]];
    end

    // Logic Analyzer debug taps (registered 1-cycle pulse on ADC_STORE completion)
    assign dbg_adc_done_1shot = (adc_state == ADC_STORE) && (store_sub == 2'd1);
    assign dbg_adc45_ch0_raw  = adc45_raw_lat[0];
    assign dbg_adc45_ch1_raw  = adc45_raw_lat[1];
    assign dbg_adc45_ch2_raw  = adc45_raw_lat[2];
    assign dbg_adc45_ch1_sig  = adc45_sig_lat[1][11:0];
    assign dbg_adc49_ch2_raw  = adc49_raw_lat[2];

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
                default: prdata = 32'd0;
            endcase
        end
    end

endmodule
`default_nettype wire
