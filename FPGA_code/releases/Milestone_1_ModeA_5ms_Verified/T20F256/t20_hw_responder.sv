// =============================================================================
// t20_hw_responder.sv : hardware S-bus responder (no processor), CLK9 domain
// =============================================================================
// Lets the T120 (and the AI agent through T120) bring up and observe the T20
// without any T20 CPU: link test, Hadamard configuration and monitoring.
// SEQ/OP byte: [7:4] sequence, [3:0] opcode. The response echoes CH and SEQ/OP.
//
//  CH 0x04 (trace/debug)  op 0x0 STATUS  -> 16 byte payload:
//        [0..3]  'T','2','0','G'      [4] version (0x01)   [5] flags {.. static_on, has_soc}
//        [6..7]  H words applied      [8..9]  H sync errors
//        [10..11] S-bus good frames   [12..13] S-bus CRC errors   [14..15] H en_mask
//  CH 0x02 (Hadamard cfg) op 0x1 SET_EN     payload[0..1] = en_mask (big endian)
//                         op 0x2 SET_STATIC payload[0] = static_on, [1..2] = static_vec (BE)
//                         op 0x3 CLR_CNT    clear H/S-bus counters
//                         op 0x4 GET_CFG    -> en_mask(2) static_on(1) static_vec(2)
// Any other (CH, op): forwarded to the SoC when HAS_SOC=1 (fwd_to_soc pulse,
// no response generated here), otherwise NAK (0x15) with empty payload.
// Responses: 0x06 ACK / 0x15 NAK.
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
    output logic        nak_sticky
);
    logic [7:0] rsp [0:15];
    logic       clr_h;

    assign tx_pay_byte = rsp[tx_pay_idx[3:0]];

    wire [3:0] op = rx_seqop[3:0];

    integer i;
    always_ff @(posedge clk9 or negedge rstn) begin
        if (!rstn) begin
            tx_start <= 1'b0; tx_resp <= 8'h06; tx_ch <= 8'd0; tx_seqop <= 8'd0; tx_len <= 11'd0;
            fwd_to_soc <= 1'b0; en_mask <= 16'd0; static_on <= 1'b0; static_vec <= 16'd0;
            good_cnt <= 16'd0; crc_err_cnt <= 16'd0; nak_sticky <= 1'b0;
            for (i = 0; i < 16; i = i + 1) rsp[i] <= 8'd0;
        end else begin
            tx_start   <= 1'b0;
            fwd_to_soc <= 1'b0;

            if (frame_err) crc_err_cnt <= crc_err_cnt + 16'd1;

            if (frame_ok) begin
                good_cnt <= good_cnt + 16'd1;
                tx_ch    <= rx_ch;
                tx_seqop <= rx_seqop;
                tx_resp  <= 8'h06;
                tx_len   <= 11'd0;

                if (rx_ch == 8'h04 && op == 4'h0) begin
                    rsp[0] <= "T"; rsp[1] <= "2"; rsp[2] <= "0"; rsp[3] <= "G";
                    rsp[4] <= 8'h01; rsp[5] <= {6'd0, static_on, HAS_SOC[0]};
                    rsp[6] <= h_word_cnt[15:8]; rsp[7] <= h_word_cnt[7:0];
                    rsp[8] <= h_sync_err[15:8]; rsp[9] <= h_sync_err[7:0];
                    rsp[10] <= good_cnt[15:8]; rsp[11] <= good_cnt[7:0];
                    rsp[12] <= crc_err_cnt[15:8]; rsp[13] <= crc_err_cnt[7:0];
                    rsp[14] <= en_mask[15:8]; rsp[15] <= en_mask[7:0];
                    tx_len <= 11'd16; tx_start <= 1'b1;
                end else if (rx_ch == 8'h02 && op == 4'h1) begin
                    en_mask <= {pay8[7:0], pay8[15:8]};
                    rsp[0] <= pay8[7:0]; rsp[1] <= pay8[15:8];
                    tx_len <= 11'd2; tx_start <= 1'b1;
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
