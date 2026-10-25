// =============================================================================
// t20_sbus_rx.sv : S-bus receiver (T120 -> T20), 2 bits per CLK9 cycle, CLK9 domain
// =============================================================================
// Frame: 0xA5 | CH | SEQ/OP | LEN_H | LEN_L | PAYLOAD[LEN] | CRC8   (MS 2-bit symbol first)
// CRC8: poly 0x07, init 0, over every byte after the preamble. LEN <= 1024.
// Idle symbol is 2'b00; the preamble is found with a sliding 8-bit window.
// SEQ/OP byte: [7:4] sequence, [3:0] opcode.
// The first 8 payload bytes are also captured in pay8 (used by the hardware
// responder); the full payload goes to a RAM through the ram_* write port
// (little endian word packing) when buf_busy == 0.
// =============================================================================
`timescale 1ns / 1ps
`default_nettype none

module t20_sbus_rx (
    input  wire         clk9,
    input  wire         rstn,
    input  wire [1:0]   sym,
    input  wire         buf_busy,

    output logic        ram_we,
    output logic [7:0]  ram_waddr,
    output logic [31:0] ram_wdata,

    output logic [7:0]  rx_ch,
    output logic [7:0]  rx_seqop,
    output logic [10:0] rx_len,
    output logic [63:0] pay8,         // payload byte0 in [7:0]

    output logic        frame_ok,
    output logic        frame_err,
    output logic        frame_ovf
);
    localparam [2:0] F_CH = 3'd0, F_SEQ = 3'd1, F_LENH = 3'd2, F_LENL = 3'd3, F_PAY = 3'd4, F_CSUM = 3'd5;

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

    logic [7:0]  win;
    logic        in_frame;
    logic [1:0]  sc;
    logic [7:0]  sbyte;
    logic [2:0]  fld;
    logic [7:0]  crc;
    logic        ignore;
    logic [7:0]  t_ch, t_seq;
    logic [2:0]  t_lenh;
    logic [10:0] t_len;
    logic [10:0] bidx;
    logic [31:0] wacc;
    logic [63:0] t_pay8;

    wire [7:0]  b       = {sbyte[5:0], sym};
    wire        byte_rdy = in_frame && (sc == 2'd3);
    wire [31:0] new_w   = wacc | ({24'd0, b} << {bidx[1:0], 3'b000});
    wire        last_b  = (bidx + 11'd1 == t_len);
    wire [10:0] len_now = {t_lenh, b};

    always_ff @(posedge clk9 or negedge rstn) begin
        if (!rstn) begin
            win <= 8'd0; in_frame <= 1'b0; sc <= 2'd0; sbyte <= 8'd0; fld <= F_CH; crc <= 8'd0;
            ignore <= 1'b0; t_ch <= 8'd0; t_seq <= 8'd0; t_lenh <= 3'd0; t_len <= 11'd0;
            bidx <= 11'd0; wacc <= 32'd0; t_pay8 <= 64'd0; pay8 <= 64'd0;
            ram_we <= 1'b0; ram_waddr <= 8'd0; ram_wdata <= 32'd0;
            rx_ch <= 8'd0; rx_seqop <= 8'd0; rx_len <= 11'd0;
            frame_ok <= 1'b0; frame_err <= 1'b0; frame_ovf <= 1'b0;
        end else begin
            ram_we <= 1'b0; frame_ok <= 1'b0; frame_err <= 1'b0; frame_ovf <= 1'b0;
            win <= {win[5:0], sym};

            if (!in_frame) begin
                if ({win[5:0], sym} == 8'hA5) begin
                    in_frame <= 1'b1; sc <= 2'd0; fld <= F_CH; crc <= 8'd0; ignore <= buf_busy;
                end
            end else begin
                sbyte <= {sbyte[5:0], sym};
                sc    <= sc + 2'd1;
                if (byte_rdy) begin
                    case (fld)
                        F_CH:   begin t_ch  <= b; crc <= crc8_byte(crc, b); fld <= F_SEQ; end
                        F_SEQ:  begin t_seq <= b; crc <= crc8_byte(crc, b); fld <= F_LENH; end
                        F_LENH: begin
                            crc <= crc8_byte(crc, b);
                            if (b[7:3] != 5'd0) begin in_frame <= 1'b0; frame_ovf <= 1'b1; end
                            else begin t_lenh <= b[2:0]; fld <= F_LENL; end
                        end
                        F_LENL: begin
                            crc <= crc8_byte(crc, b); t_len <= len_now; bidx <= 11'd0; wacc <= 32'd0;
                            t_pay8 <= 64'd0;
                            if (len_now > 11'd1024) begin in_frame <= 1'b0; frame_ovf <= 1'b1; end
                            else fld <= (len_now == 11'd0) ? F_CSUM : F_PAY;
                        end
                        F_PAY: begin
                            crc <= crc8_byte(crc, b);
                            if (bidx < 11'd8) t_pay8[8*bidx[2:0] +: 8] <= b;
                            if (bidx[1:0] == 2'd3 || last_b) begin
                                if (!ignore) begin ram_we <= 1'b1; ram_waddr <= bidx[9:2]; ram_wdata <= new_w; end
                                wacc <= 32'd0;
                            end else wacc <= new_w;
                            bidx <= bidx + 11'd1;
                            if (last_b) fld <= F_CSUM;
                        end
                        default: begin // F_CSUM
                            in_frame <= 1'b0;
                            if (b != crc)      frame_err <= 1'b1;
                            else if (ignore)   frame_ovf <= 1'b1;
                            else begin
                                frame_ok <= 1'b1; rx_ch <= t_ch; rx_seqop <= t_seq;
                                rx_len <= t_len; pay8 <= t_pay8;
                            end
                        end
                    endcase
                end
            end
        end
    end
endmodule
`default_nettype wire
