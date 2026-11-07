// =============================================================================
// t120_sbus_rx.sv : S-bus receiver (T20 -> T120), 4 bits per CLK9 cycle
// =============================================================================
// Frame (nibbles, high nibble of every byte first, idle nibble = 4'h0):
//   0xA5 | RESP | CH | SEQ | LEN_H | LEN_L | PAYLOAD[LEN] | CRC8
// RESP: 0x06 ACK, 0x15 NAK, 0x55 BUSY, 0xEE ERROR.
// CRC8: poly 0x07, init 0, over every byte after the 0xA5 preamble.
// Payload is written into an external RAM (little endian word packing).
// A frame that arrives while the buffer is still occupied (buf_busy) is parsed
// but dropped (frame_ovf). Bad CRC -> frame_err. No retry logic here: the
// S-bus is strictly request/response, T120 polls.
// smp_ev is the RX sampling strobe (CLK9 rise, optionally delayed).
// =============================================================================
`timescale 1ns / 1ps
`default_nettype none

module t120_sbus_rx (
    input  wire        clk,
    input  wire        rstn,
    input  wire        smp_ev,
    input  wire [3:0]  nib,
    input  wire        buf_busy,

    output logic       ram_we,
    output logic [7:0] ram_waddr,
    output logic [31:0] ram_wdata,

    output logic [7:0]  rx_resp,
    output logic [7:0]  rx_ch,
    output logic [7:0]  rx_seq,
    output logic [10:0] rx_len,

    output logic       frame_ok,
    output logic       frame_err,
    output logic       frame_ovf
);
    localparam [1:0] ST_A = 2'd0, ST_5 = 2'd1, ST_BYTE = 2'd2;
    localparam [2:0] F_RESP = 3'd0, F_CH = 3'd1, F_SEQ = 3'd2, F_LENH = 3'd3,
                     F_LENL = 3'd4, F_PAY = 3'd5, F_CSUM = 3'd6;

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

    logic [1:0]  st;
    logic [2:0]  fld;
    logic        half;
    logic [3:0]  hi;
    logic [7:0]  crc;
    logic        ignore;
    logic [7:0]  t_resp, t_ch, t_seq;
    logic [2:0]  t_lenh;
    logic [10:0] t_len;
    logic [10:0] bidx;
    logic [31:0] wacc;

    wire [7:0]  b = {hi, nib};
    wire [10:0] len_now = {t_lenh, b};
    wire [31:0] new_w = wacc | ({24'd0, b} << {bidx[1:0], 3'b000});
    wire        last_b = (bidx + 11'd1 == t_len);

    always_ff @(posedge clk or negedge rstn) begin
        if (!rstn) begin
            st <= ST_A; fld <= F_RESP; half <= 1'b0; hi <= 4'd0; crc <= 8'd0;
            ignore <= 1'b0; t_resp <= 8'd0; t_ch <= 8'd0; t_seq <= 8'd0;
            t_lenh <= 3'd0; t_len <= 11'd0; bidx <= 11'd0; wacc <= 32'd0;
            ram_we <= 1'b0; ram_waddr <= 8'd0; ram_wdata <= 32'd0;
            rx_resp <= 8'd0; rx_ch <= 8'd0; rx_seq <= 8'd0; rx_len <= 11'd0;
            frame_ok <= 1'b0; frame_err <= 1'b0; frame_ovf <= 1'b0;
        end else begin
            ram_we    <= 1'b0;
            frame_ok  <= 1'b0;
            frame_err <= 1'b0;
            frame_ovf <= 1'b0;

            if (smp_ev) begin
                case (st)
                    ST_A: if (nib == 4'hA) st <= ST_5;

                    ST_5: begin
                        if (nib == 4'h5) begin
                            st     <= ST_BYTE;
                            fld    <= F_RESP;
                            half   <= 1'b0;
                            crc    <= 8'h00;
                            ignore <= buf_busy;
                        end else if (nib != 4'hA) begin
                            st <= ST_A;
                        end
                    end

                    default: begin // ST_BYTE
                        if (!half) begin
                            hi   <= nib;
                            half <= 1'b1;
                        end else begin
                            half <= 1'b0;
                            case (fld)
                                F_RESP: begin t_resp <= b; crc <= crc8_byte(crc, b); fld <= F_CH;  end
                                F_CH:   begin t_ch   <= b; crc <= crc8_byte(crc, b); fld <= F_SEQ; end
                                F_SEQ:  begin t_seq  <= b; crc <= crc8_byte(crc, b); fld <= F_LENH; end
                                F_LENH: begin
                                    crc <= crc8_byte(crc, b);
                                    if (b[7:3] != 5'd0) begin
                                        st <= ST_A; frame_ovf <= 1'b1;   // length > 2047
                                    end else begin
                                        t_lenh <= b[2:0]; fld <= F_LENL;
                                    end
                                end
                                F_LENL: begin
                                    crc   <= crc8_byte(crc, b);
                                    t_len <= len_now;
                                    bidx  <= 11'd0;
                                    wacc  <= 32'd0;
                                    if (len_now > 11'd1024) begin
                                        st <= ST_A; frame_ovf <= 1'b1;
                                    end else if (len_now == 11'd0) begin
                                        fld <= F_CSUM;
                                    end else begin
                                        fld <= F_PAY;
                                    end
                                end
                                F_PAY: begin
                                    crc <= crc8_byte(crc, b);
                                    if (bidx[1:0] == 2'd3 || last_b) begin
                                        if (!ignore) begin
                                            ram_we    <= 1'b1;
                                            ram_waddr <= bidx[9:2];
                                            ram_wdata <= new_w;
                                        end
                                        wacc <= 32'd0;
                                    end else begin
                                        wacc <= new_w;
                                    end
                                    bidx <= bidx + 11'd1;
                                    if (last_b) fld <= F_CSUM;
                                end
                                default: begin // F_CSUM
                                    st <= ST_A;
                                    if (b != crc)      frame_err <= 1'b1;
                                    else if (ignore)   frame_ovf <= 1'b1;
                                    else begin
                                        frame_ok <= 1'b1;
                                        rx_resp  <= t_resp;
                                        rx_ch    <= t_ch;
                                        rx_seq   <= t_seq;
                                        rx_len   <= t_len;
                                    end
                                end
                            endcase
                        end
                    end
                endcase
            end
        end
    end
endmodule
`default_nettype wire
