// =============================================================================
// t20_sbus_tx.sv : S-bus transmitter (T20 -> T120), 4 bits per CLK9 cycle, CLK9 domain
// =============================================================================
// Frame: 0xA5 | RESP | CH | SEQ/OP | LEN_H | LEN_L | PAYLOAD[LEN] | CRC8
// High nibble of every byte first, idle nibble 4'h0, CRC8 poly 0x07 init 0 over
// every byte after the preamble. nib is a registered output launched on the
// CLK9 RISING edge (T120 samples it one CLK9 period later through its RX sync).
// The payload byte for index pay_idx is supplied by the caller (pay_byte); it
// may have one CLK9 cycle of latency (synchronous RAM): the byte for index n is
// needed 2 cycles after pay_idx moves to n.
// =============================================================================
`timescale 1ns / 1ps
`default_nettype none

module t20_sbus_tx (
    input  wire         clk9,
    input  wire         rstn,

    input  wire         start,
    input  wire [7:0]   resp,
    input  wire [7:0]   ch,
    input  wire [7:0]   seqop,
    input  wire [10:0]  len,

    output wire [9:0]   pay_idx,
    input  wire [7:0]   pay_byte,

    output logic        busy,
    output logic        done,
    output logic [3:0]  nib
);
    localparam [3:0] PH_PRE = 4'd0, PH_RESP = 4'd1, PH_CH = 4'd2, PH_SEQ = 4'd3, PH_LENH = 4'd4,
                     PH_LENL = 4'd5, PH_PAY = 4'd6, PH_CRC = 4'd7;

    function automatic [7:0] crc8_byte(input [7:0] crc, input [7:0] d);
        reg [7:0] x;
        integer i;
        begin
            x = crc ^ d;
            for (i = 0; i < 8; i = i + 1)
                x = x[7] ? ((x << 1) ^ 8'h07) : (x << 1);
            crc8_byte = x;
        end
    endfunction

    logic [3:0]  phase;
    logic [7:0]  cur_byte;
    logic        half;           // 0: sending high nibble, 1: low nibble
    logic [7:0]  crc;
    logic [10:0] nidx;
    logic [10:0] len_q;
    logic [7:0]  resp_q, ch_q, seq_q;

    assign pay_idx = nidx[9:0];

    wire [10:0] len_c = (len > 11'd1024) ? 11'd1024 : len;

    always_ff @(posedge clk9 or negedge rstn) begin
        if (!rstn) begin
            busy <= 1'b0; done <= 1'b0; nib <= 4'h0; phase <= PH_PRE; cur_byte <= 8'h00;
            half <= 1'b0; crc <= 8'h00; nidx <= 11'd0; len_q <= 11'd0;
            resp_q <= 8'h00; ch_q <= 8'h00; seq_q <= 8'h00;
        end else begin
            done <= 1'b0;

            if (start && !busy) begin
                busy <= 1'b1; resp_q <= resp; ch_q <= ch; seq_q <= seqop; len_q <= len_c;
                phase <= PH_PRE; cur_byte <= 8'hA5; half <= 1'b0; crc <= 8'h00; nidx <= 11'd0;
            end else if (busy) begin
                nib <= half ? cur_byte[3:0] : cur_byte[7:4];
                half <= ~half;
                if (half) begin
                    case (phase)
                        PH_PRE:  begin phase <= PH_RESP; cur_byte <= resp_q; crc <= crc8_byte(crc, resp_q); end
                        PH_RESP: begin phase <= PH_CH;   cur_byte <= ch_q;   crc <= crc8_byte(crc, ch_q); end
                        PH_CH:   begin phase <= PH_SEQ;  cur_byte <= seq_q;  crc <= crc8_byte(crc, seq_q); end
                        PH_SEQ:  begin phase <= PH_LENH; cur_byte <= {5'd0, len_q[10:8]}; crc <= crc8_byte(crc, {5'd0, len_q[10:8]}); end
                        PH_LENH: begin phase <= PH_LENL; cur_byte <= len_q[7:0]; crc <= crc8_byte(crc, len_q[7:0]); end
                        PH_LENL, PH_PAY: begin
                            if (nidx == len_q) begin
                                phase <= PH_CRC; cur_byte <= crc;
                            end else begin
                                phase <= PH_PAY; cur_byte <= pay_byte; crc <= crc8_byte(crc, pay_byte);
                                nidx <= nidx + 11'd1;
                            end
                        end
                        default: begin busy <= 1'b0; done <= 1'b1; end
                    endcase
                end
            end else begin
                nib <= 4'h0;
            end
        end
    end
endmodule
`default_nettype wire
