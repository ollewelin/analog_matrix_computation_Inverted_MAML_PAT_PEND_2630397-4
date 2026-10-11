// =============================================================================
// t20_hw_responder.sv : hardware S-bus responder (no processor), CLK9 domain
// =============================================================================
// Lets the T120 control and observe the T20 over S-bus:
//  - CH 0x01 (Flash/Boot):
//      op 0x2 CMD_JUMP         payload[0] = CBSEL target (0=Golden, 1=Custom App)
//  - CH 0x02 (Hadamard cfg):
//      op 0x1 SET_EN           payload[0..1] = en_mask (big endian)
//      op 0x2 SET_STATIC       payload[0] = static_on, [1..2] = static_vec (BE)
//      op 0x3 CLR_CNT          clear H/S-bus counters
//      op 0x4 GET_CFG          -> en_mask(2) static_on(1) static_vec(2)
//  - CH 0x04 (Trace/Status):
//      op 0x0 STATUS           -> 16 byte payload ('T','2','0','A', ver, counters)
//  - CH 0x05 (Analog Matrix, Heater 0.2Hz PWM, LEDs & Column Gates):
//      op 0x1 SET_HEATER       payload[0]=armed, payload[1..4]=duty_1..4 (0..255)
//      op 0x2 SET_LEDS         payload[0]= {mat33_led(bit1), comp_led(bit0)} or payload[1]=mat33_led
//      op 0x3 SET_GATES_STATIC payload[0]=g_mat3[5:0], [1]=g_mat8[5:0], [2]=g_mat33[5:0]
//      op 0x4 PULSE_COL_GATES  payload[0]=col_mask[5:0], [1]={en_m33,en_m8,en_m3}, [2..3]=cycles(LE)
//      op 0x5 GET_ANALOG_ST    -> 10 byte status payload
// =============================================================================
`timescale 1ns / 1ps
`default_nettype none

module t20_hw_responder #(
    parameter integer HAS_SOC = 0
)(
    input  wire         clk9,
    input  wire         rstn,

    input  wire         frame_ok,
    input  wire         frame_err,
    input  wire [7:0]   rx_ch,
    input  wire [7:0]   rx_seqop,
    input  wire [63:0]  pay8,

    input  wire [15:0]  h_word_cnt,
    input  wire [15:0]  h_sync_err,
    input  wire         tx_busy,

    output logic        tx_start,
    output logic [7:0]  tx_resp,
    output logic [7:0]  tx_ch,
    output logic [7:0]  tx_seqop,
    output logic [10:0] tx_len,
    input  wire [9:0]   tx_pay_idx,
    output wire  [7:0]  tx_pay_byte,

    output logic        fwd_to_soc,

    output logic [15:0] en_mask,
    output logic        static_on,
    output logic [15:0] static_vec,

    output logic [15:0] good_cnt,
    output logic [15:0] crc_err_cnt,
    output logic        nak_sticky,

    // Internal Reconfiguration (CONFIG_CTRL0)
    output logic [1:0]  cfg_cbsel,
    output logic        cfg_config,
    output logic        cfg_ena,

    // Heater 0.2 Hz PWM & Safety Interlock
    output logic        heater_armed,
    output logic [7:0]  heat_duty_0,
    output logic [7:0]  heat_duty_1,
    output logic [7:0]  heat_duty_2,
    output logic [7:0]  heat_duty_3,
    input  wire         wdog_ok_sync,
    input  wire [7:0]   pwm_step_sync,

    // Analog Column Output LED Array Switches
    output logic        comp_led_on,
    output logic        mat33_led_on,

    // Differential Column Refresh Gate Outputs (active high, P = G+, N = G-)
    output wire  [5:0]  g_mat3_p_out,
    output wire  [5:0]  g_mat3_n_out,
    output wire  [5:0]  g_mat8_p_out,
    output wire  [5:0]  g_mat8_n_out,
    output wire  [5:0]  g_mat33_p_out,
    output wire  [5:0]  g_mat33_n_out
);
    logic [7:0] rsp [0:15];

    assign tx_pay_byte = rsp[tx_pay_idx[3:0]];

    wire [3:0] op = rx_seqop[3:0];

    // Differential column gate static + hardware pulse timer registers
    logic [5:0]  g_mat3_p_static,  g_mat8_p_static,  g_mat33_p_static;
    logic [5:0]  g_mat3_n_static,  g_mat8_n_static,  g_mat33_n_static;
    logic [5:0]  g_mat3_p_pulse,   g_mat8_p_pulse,   g_mat33_p_pulse;
    logic [5:0]  g_mat3_n_pulse,   g_mat8_n_pulse,   g_mat33_n_pulse;
    logic [15:0] gate_pulse_cnt;

    assign g_mat3_p_out  = (gate_pulse_cnt != 16'd0) ? g_mat3_p_pulse  : g_mat3_p_static;
    assign g_mat3_n_out  = (gate_pulse_cnt != 16'd0) ? g_mat3_n_pulse  : g_mat3_n_static;
    assign g_mat8_p_out  = (gate_pulse_cnt != 16'd0) ? g_mat8_p_pulse  : g_mat8_p_static;
    assign g_mat8_n_out  = (gate_pulse_cnt != 16'd0) ? g_mat8_n_pulse  : g_mat8_n_static;
    assign g_mat33_p_out = (gate_pulse_cnt != 16'd0) ? g_mat33_p_pulse : g_mat33_p_static;
    assign g_mat33_n_out = (gate_pulse_cnt != 16'd0) ? g_mat33_n_pulse : g_mat33_n_static;

    integer i;
    always_ff @(posedge clk9 or negedge rstn) begin
        if (!rstn) begin
            tx_start <= 1'b0; tx_resp <= 8'h06; tx_ch <= 8'd0; tx_seqop <= 8'd0; tx_len <= 11'd0;
            fwd_to_soc <= 1'b0; en_mask <= 16'h7FFF; static_on <= 1'b0; static_vec <= 16'd0;
            good_cnt <= 16'd0; crc_err_cnt <= 16'd0; nak_sticky <= 1'b0;
            cfg_cbsel <= 2'b00; cfg_config <= 1'b0; cfg_ena <= 1'b0;
            heater_armed <= 1'b0;
            heat_duty_0  <= 8'd0;
            heat_duty_1  <= 8'd0;
            heat_duty_2  <= 8'd0;
            heat_duty_3  <= 8'd0;
            comp_led_on  <= 1'b0;
            mat33_led_on <= 1'b0;
            g_mat3_p_static  <= 6'd0; g_mat3_n_static  <= 6'd0;
            g_mat8_p_static  <= 6'd0; g_mat8_n_static  <= 6'd0;
            g_mat33_p_static <= 6'd0; g_mat33_n_static <= 6'd0;
            g_mat3_p_pulse   <= 6'd0; g_mat3_n_pulse   <= 6'd0;
            g_mat8_p_pulse   <= 6'd0; g_mat8_n_pulse   <= 6'd0;
            g_mat33_p_pulse  <= 6'd0; g_mat33_n_pulse  <= 6'd0;
            gate_pulse_cnt   <= 16'd0;
            for (i = 0; i < 16; i = i + 1) rsp[i] <= 8'd0;
        end else begin
            tx_start   <= 1'b0;
            fwd_to_soc <= 1'b0;

            // Decrement column gate pulse timer if active
            if (gate_pulse_cnt != 16'd0) begin
                gate_pulse_cnt <= gate_pulse_cnt - 16'd1;
                if (gate_pulse_cnt == 16'd1) begin
                    g_mat3_p_pulse  <= 6'd0; g_mat3_n_pulse  <= 6'd0;
                    g_mat8_p_pulse  <= 6'd0; g_mat8_n_pulse  <= 6'd0;
                    g_mat33_p_pulse <= 6'd0; g_mat33_n_pulse <= 6'd0;
                end
            end

            // Auto-disarm heater if watchdog expires
            if (!wdog_ok_sync) begin
                heater_armed <= 1'b0;
            end

            if (frame_err) crc_err_cnt <= crc_err_cnt + 16'd1;

            if (frame_ok) begin
                good_cnt <= good_cnt + 16'd1;
                tx_ch    <= rx_ch;
                tx_seqop <= rx_seqop;
                tx_resp  <= 8'h06;
                tx_len   <= 11'd0;

                if (rx_ch == 8'h04 && op == 4'h0) begin
                    rsp[0]  <= "T"; rsp[1] <= "2"; rsp[2] <= "0"; rsp[3] <= "A";
                    rsp[4]  <= 8'h02;
                    rsp[5]  <= {3'd0, heater_armed, comp_led_on, mat33_led_on, static_on, HAS_SOC[0]};
                    rsp[6]  <= h_word_cnt[15:8];  rsp[7]  <= h_word_cnt[7:0];
                    rsp[8]  <= h_sync_err[15:8];  rsp[9]  <= h_sync_err[7:0];
                    rsp[10] <= good_cnt[15:8];    rsp[11] <= good_cnt[7:0];
                    rsp[12] <= crc_err_cnt[15:8]; rsp[13] <= crc_err_cnt[7:0];
                    rsp[14] <= en_mask[15:8];     rsp[15] <= en_mask[7:0];
                    tx_len  <= 11'd16; tx_start <= 1'b1;
                end else if (rx_ch == 8'h02 && op == 4'h1) begin
                    en_mask <= {pay8[7:0], pay8[15:8]};
                    rsp[0]  <= pay8[7:0]; rsp[1] <= pay8[15:8];
                    tx_len  <= 11'd2; tx_start <= 1'b1;
                end else if (rx_ch == 8'h02 && op == 4'h2) begin
                    static_on  <= pay8[0];
                    static_vec <= {pay8[15:8], pay8[23:16]};
                    tx_len <= 11'd0; tx_start <= 1'b1;
                end else if (rx_ch == 8'h02 && op == 4'h3) begin
                    good_cnt <= 16'd0; crc_err_cnt <= 16'd0; nak_sticky <= 1'b0;
                    tx_len <= 11'd0; tx_start <= 1'b1;
                end else if (rx_ch == 8'h02 && op == 4'h4) begin
                    rsp[0] <= en_mask[15:8]; rsp[1] <= en_mask[7:0]; rsp[2] <= {7'd0, static_on};
                    rsp[3] <= static_vec[15:8]; rsp[4] <= static_vec[7:0];
                    tx_len <= 11'd5; tx_start <= 1'b1;
                end else if (rx_ch == 8'h01 && op == 4'h2) begin
                    // CMD_JUMP: Channel 0x01 (FLASH), Opcode 0x02 (JUMP)
                    cfg_cbsel  <= pay8[1:0];
                    cfg_ena    <= 1'b1;
                    cfg_config <= 1'b1;
                    rsp[0]     <= pay8[7:0];
                    tx_len     <= 11'd1;
                    tx_start   <= 1'b1;
                end else if (rx_ch == 8'h05 && op == 4'h1) begin
                    // CH 0x05 OP 0x1: SET_HEATER (0.2 Hz PWM + Master Arm Interlock)
                    heater_armed <= pay8[0];
                    heat_duty_0  <= pay8[15:8];
                    heat_duty_1  <= pay8[23:16];
                    heat_duty_2  <= pay8[31:24];
                    heat_duty_3  <= pay8[39:32];
                    rsp[0]       <= {7'd0, pay8[0]};
                    rsp[1]       <= pay8[15:8];
                    rsp[2]       <= pay8[23:16];
                    rsp[3]       <= pay8[31:24];
                    rsp[4]       <= pay8[39:32];
                    tx_len       <= 11'd5;
                    tx_start     <= 1'b1;
                end else if (rx_ch == 8'h05 && op == 4'h2) begin
                    // CH 0x05 OP 0x2: SET_LEDS (COMP_LED_ON, MAT33_LED_ON)
                    comp_led_on  <= pay8[0];
                    mat33_led_on <= pay8[1] | pay8[8];
                    rsp[0]       <= {7'd0, pay8[0]};
                    rsp[1]       <= {7'd0, (pay8[1] | pay8[8])};
                    tx_len       <= 11'd2;
                    tx_start     <= 1'b1;
                end else if (rx_ch == 8'h05 && op == 4'h3) begin
                    // CH 0x05 OP 0x3: SET_GATES_STATIC
                    // pay8[0..2] = P gates (mat3, mat8, mat33), pay8[3..5] = N gates (mat3, mat8, mat33)
                    g_mat3_p_static  <= pay8[5:0];
                    g_mat8_p_static  <= pay8[13:8];
                    g_mat33_p_static <= pay8[21:16];
                    g_mat3_n_static  <= pay8[29:24];
                    g_mat8_n_static  <= pay8[37:32];
                    g_mat33_n_static <= pay8[45:40];
                    gate_pulse_cnt   <= 16'd0;
                    rsp[0]           <= {2'd0, pay8[5:0]};
                    rsp[1]           <= {2'd0, pay8[13:8]};
                    rsp[2]           <= {2'd0, pay8[21:16]};
                    rsp[3]           <= {2'd0, pay8[29:24]};
                    rsp[4]           <= {2'd0, pay8[37:32]};
                    rsp[5]           <= {2'd0, pay8[45:40]};
                    tx_len           <= 11'd6;
                    tx_start         <= 1'b1;
                end else if (rx_ch == 8'h05 && op == 4'h4) begin
                    // CH 0x05 OP 0x4: PULSE_COL_GATES (Differential P / N control)
                    // pay8[5:0]   = column bitmask [5:0] (cols 1..6)
                    // pay8[10:8]  = P-gate matrix mask {mat33_p, mat8_p, mat3_p}
                    // pay8[14:12] = N-gate matrix mask {mat33_n, mat8_n, mat3_n}
                    // pay8[31:16] = duration in clk9 cycles (default 40 = 4.0 us @ 10MHz)
                    g_mat3_p_pulse  <= pay8[8]  ? pay8[5:0] : 6'd0;
                    g_mat8_p_pulse  <= pay8[9]  ? pay8[5:0] : 6'd0;
                    g_mat33_p_pulse <= pay8[10] ? pay8[5:0] : 6'd0;
                    g_mat3_n_pulse  <= pay8[12] ? pay8[5:0] : 6'd0;
                    g_mat8_n_pulse  <= pay8[13] ? pay8[5:0] : 6'd0;
                    g_mat33_n_pulse <= pay8[14] ? pay8[5:0] : 6'd0;
                    gate_pulse_cnt  <= (pay8[31:16] == 16'd0) ? 16'd40 : pay8[31:16];
                    rsp[0]          <= {2'd0, pay8[5:0]};
                    rsp[1]          <= pay8[15:8];
                    rsp[2]          <= pay8[23:16];
                    rsp[3]          <= pay8[31:24];
                    tx_len          <= 11'd4;
                    tx_start        <= 1'b1;
                end else if (rx_ch == 8'h05 && op == 4'h5) begin
                    // CH 0x05 OP 0x5: GET_ANALOG_STATUS (13 bytes)
                    rsp[0]  <= {5'd0, wdog_ok_sync, mat33_led_on, comp_led_on};
                    rsp[1]  <= {7'd0, heater_armed};
                    rsp[2]  <= heat_duty_0;
                    rsp[3]  <= heat_duty_1;
                    rsp[4]  <= heat_duty_2;
                    rsp[5]  <= heat_duty_3;
                    rsp[6]  <= {2'd0, g_mat3_p_out};
                    rsp[7]  <= {2'd0, g_mat8_p_out};
                    rsp[8]  <= {2'd0, g_mat33_p_out};
                    rsp[9]  <= {2'd0, g_mat3_n_out};
                    rsp[10] <= {2'd0, g_mat8_n_out};
                    rsp[11] <= {2'd0, g_mat33_n_out};
                    rsp[12] <= pwm_step_sync;
                    tx_len  <= 11'd13;
                    tx_start <= 1'b1;
                end else if (HAS_SOC != 0) begin
                    fwd_to_soc <= 1'b1;
                end else begin
                    tx_resp <= 8'h15; nak_sticky <= 1'b1;
                    tx_len <= 11'd0; tx_start <= 1'b1;
                end
            end
        end
    end
endmodule
`default_nettype wire
