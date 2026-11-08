// =============================================================================
// t120_sbus_tx.sv : S-bus transmitter (T120 -> T20), 2 bits per CLK9 cycle
// =============================================================================
// Service bus (software / C-code driven: SoC, SPI-flash, trace). NOT used for
// Hadamard timing. Frame (bytes, MS 2-bit symbol first, 4 symbols per byte):
//   0xA5 | CH | SEQ/OP | LEN_H | LEN_L | PAYLOAD[LEN] | CRC8
// CRC8: poly 0x07, init 0, over every byte after the 0xA5 preamble.
// Idle symbol = 2'b00. LEN <= 1024 (larger values are clamped).
// Payload is read byte-wise (little endian: byte0 = word[7:0]) from an
// external synchronous RAM via ram_addr/ram_rdata.
// =============================================================================
`timescale 1ns / 1ps
`default_nettype none

module t120_sbus_tx (
    input  wire        clk,
    input  wire        rstn,
    input  wire        fall_ev,

    input  wire        start,
    input  wire [7:0]  hdr_ch,
    input  wire [7:0]  hdr_seq,
    input  wire [15:0] hdr_len,

    output wire [7:0]  ram_addr,
    input  wire [31:0] ram_rdata,

    output logic       busy,
    output logic       done,
    output logic [1:0] sym
);
    localparam [2:0] PH_PRE = 3'd0, PH_CH = 3'd1, PH_SEQ = 3'd2, PH_LENH = 3'd3,
                     PH_LENL = 3'd4, PH_PAY = 3'd5, PH_CRC = 3'd6;

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

    logic [2:0]  phase;
    logic [7:0]  cur_byte;
    logic [1:0]  sym_cnt;
    logic [7:0]  crc;
    logic [10:0] nidx;      // index of the next payload byte to load
    logic [10:0] len_q;
    logic [7:0]  ch_q, seq_q;

    assign ram_addr = nidx[9:2];

    wire [15:0] len_clamped = (hdr_len > 16'd1024) ? 16'd1024 : hdr_len;

    reg [7:0] pay_byte;
    always @(*) begin
        case (nidx[1:0])
            2'd0:    pay_byte = ram_rdata[7:0];
            2'd1:    pay_byte = ram_rdata[15:8];
            2'd2:    pay_byte = ram_rdata[23:16];
            default: pay_byte = ram_rdata[31:24];
        endcase
    end

    always_ff @(posedge clk or negedge rstn) begin
        if (!rstn) begin
            busy     <= 1'b0;
            done     <= 1'b0;
            sym      <= 2'b00;
            phase    <= PH_PRE;
            cur_byte <= 8'h00;
            sym_cnt  <= 2'd0;
            crc      <= 8'h00;
            nidx     <= 11'd0;
            len_q    <= 11'd0;
            ch_q     <= 8'h00;
            seq_q    <= 8'h00;
        end else begin
            done <= 1'b0;

            if (start && !busy) begin
                busy     <= 1'b1;
                ch_q     <= hdr_ch;
                seq_q    <= hdr_seq;
                len_q    <= len_clamped[10:0];
                phase    <= PH_PRE;
                cur_byte <= 8'hA5;
                sym_cnt  <= 2'd0;
                crc      <= 8'h00;
                nidx     <= 11'd0;
            end

            if (fall_ev) begin
                if (busy) begin
                    sym      <= cur_byte[7:6];
                    cur_byte <= {cur_byte[5:0], 2'b00};
                    sym_cnt  <= sym_cnt + 2'd1;

                    if (sym_cnt == 2'd3) begin
                        case (phase)
                            PH_PRE: begin
                                phase <= PH_CH;  cur_byte <= ch_q;
                                crc <= crc8_byte(crc, ch_q);
                            end
                            PH_CH: begin
                                phase <= PH_SEQ; cur_byte <= seq_q;
                                crc <= crc8_byte(crc, seq_q);
                            end
                            PH_SEQ: begin
                                phase <= PH_LENH; cur_byte <= {5'd0, len_q[10:8]};
                                crc <= crc8_byte(crc, {5'd0, len_q[10:8]});
                            end
                            PH_LENH: begin
                                phase <= PH_LENL; cur_byte <= len_q[7:0];
                                crc <= crc8_byte(crc, len_q[7:0]);
                            end
                            PH_LENL, PH_PAY: begin
                                if (nidx == len_q) begin
                                    phase    <= PH_CRC;
                                    cur_byte <= crc;
                                end else begin
                                    phase    <= PH_PAY;
                                    cur_byte <= pay_byte;
                                    crc      <= crc8_byte(crc, pay_byte);
                                    nidx     <= nidx + 11'd1;
                                end
                            end
                            default: begin // PH_CRC sent
                                busy <= 1'b0;
                                done <= 1'b1;
                            end
                        endcase
                    end
                end else begin
                    sym <= 2'b00;
                end
            end
        end
    end
endmodule
`default_nettype wire
