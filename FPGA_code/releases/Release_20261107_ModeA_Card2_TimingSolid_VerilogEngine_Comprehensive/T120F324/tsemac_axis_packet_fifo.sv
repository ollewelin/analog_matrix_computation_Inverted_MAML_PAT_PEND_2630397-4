// =============================================================================
// tsemac_axis_packet_fifo.sv
// Dual BRAM Packet FIFO connecting TSE MAC AXI4-Stream to Sapphire SoC APB3
// =============================================================================
// Both AXI4-Stream and APB3 run synchronously on sys_clk (50 MHz).
// BRAM blocks are inferred cleanly with simple register-based indexing.
//
// Memory Map (within 4KB APB3 space, e.g. Base 0xF810_2000):
//   0x000: CTRL Register
//          bit 0: TX_START (pulse 1 to transmit packet in TX RAM)
//          bit 1: RX_ACK   (pulse 1 to release RX RAM for next incoming packet)
//   0x004: STATUS Register
//          bit 0: TX_BUSY  (1 when packet is currently transmitting to TSE MAC)
//          bit 1: RX_READY (1 when valid packet has been captured in RX RAM)
//          bit 2: RX_ERROR (1 if packet had bad CRC/tuser from MAC)
//   0x008: TX_LEN Register (Number of bytes in TX buffer to transmit)
//   0x00C: RX_LEN Register (Number of bytes captured in RX buffer)
//   0x080 - 0x7FF: TX RAM (up to 1920 bytes, 32-bit word accessible)
//   0x800 - 0xFFF: RX RAM (up to 2048 bytes, 32-bit word accessible)
// =============================================================================

`timescale 1ns / 1ps
`default_nettype none

module tsemac_axis_packet_fifo (
    input  wire        clk,       // sys_clk (50 MHz)
    input  wire        rstn,      // sys_rst_n_inv (active high reset or active low reset)

    // APB3 Slave Interface
    input  wire [11:0] apb_paddr,
    input  wire        apb_psel,
    input  wire        apb_penable,
    input  wire        apb_pwrite,
    input  wire [31:0] apb_pwdata,
    output reg  [31:0] apb_prdata,
    output wire        apb_pready,
    output wire        apb_pslverr,

    // AXI4-Stream RX from TSE MAC (clk synchronous)
    input  wire [7:0]  rx_axis_tdata,
    input  wire        rx_axis_tvalid,
    input  wire        rx_axis_tlast,
    input  wire        rx_axis_tuser,
    output wire        rx_axis_tready,

    // AXI4-Stream TX to TSE MAC (clk synchronous)
    output reg  [7:0]  tx_axis_tdata,
    output reg         tx_axis_tvalid,
    output reg         tx_axis_tlast,
    output reg         tx_axis_tuser,
    input  wire        tx_axis_tready
);

    assign apb_pslverr = 1'b0;
    assign apb_pready  = 1'b1;

    // -------------------------------------------------------------------------
    // Packet Memory: Inferred Dual-Port Block RAMs
    // -------------------------------------------------------------------------
    // TX RAM: 512 words (2048 bytes)
    // Port A: APB read/write
    // Port B: TX streaming engine read
    (* ram_style = "block" *) reg [31:0] tx_ram [0:511];

    // RX RAM: 512 words (2048 bytes)
    // Port A: APB read-only
    // Port B: RX streaming engine write
    (* ram_style = "block" *) reg [31:0] rx_ram [0:511];

    // Address decoding
    wire is_reg    = (apb_paddr < 12'h080);
    wire is_tx_ram = (apb_paddr >= 12'h080) && (apb_paddr < 12'h800);
    wire is_rx_ram = (apb_paddr >= 12'h800);

    wire [8:0] tx_ram_apb_addr = (apb_paddr[10:2] - 9'd32); // offset from 0x080
    wire [8:0] rx_ram_apb_addr = apb_paddr[10:2];           // offset from 0x800

    // Registers
    reg [15:0] reg_tx_len;
    reg [15:0] reg_rx_len;
    reg        reg_tx_busy;
    reg        reg_rx_ready;
    reg        reg_rx_err;

    // APB Write
    reg tx_trigger;
    reg rx_ack_trigger;

    always @(posedge clk or negedge rstn) begin
        if (!rstn) begin
            reg_tx_len     <= 16'd0;
            tx_trigger     <= 1'b0;
            rx_ack_trigger <= 1'b0;
        end else begin
            tx_trigger     <= 1'b0;
            rx_ack_trigger <= 1'b0;

            if (apb_psel && apb_penable && apb_pwrite) begin
                if (is_reg) begin
                    case (apb_paddr[5:2])
                        4'h0: begin // 0x00: CTRL
                            if (apb_pwdata[0]) tx_trigger     <= 1'b1;
                            if (apb_pwdata[1]) rx_ack_trigger <= 1'b1;
                        end
                        4'h2: begin // 0x08: TX_LEN
                            reg_tx_len <= apb_pwdata[15:0];
                        end
                        default: ;
                    endcase
                end else if (is_tx_ram) begin
                    tx_ram[tx_ram_apb_addr] <= apb_pwdata;
                end
            end
        end
    end

    // APB Read
    reg [31:0] tx_ram_read_q;
    reg [31:0] rx_ram_read_q;
    always @(posedge clk) begin
        tx_ram_read_q <= tx_ram[tx_ram_apb_addr];
        rx_ram_read_q <= rx_ram[rx_ram_apb_addr];
    end

    always @(*) begin
        if (is_reg) begin
            case (apb_paddr[5:2])
                4'h0: apb_prdata = 32'd0;
                4'h1: apb_prdata = {13'd0, reg_rx_len, reg_rx_err, reg_rx_ready, reg_tx_busy}; // STATUS
                4'h2: apb_prdata = {16'd0, reg_tx_len};
                4'h3: apb_prdata = {16'd0, reg_rx_len};
                default: apb_prdata = 32'd0;
            endcase
        end else if (is_tx_ram) begin
            apb_prdata = tx_ram_read_q;
        end else if (is_rx_ram) begin
            apb_prdata = rx_ram_read_q;
        end else begin
            apb_prdata = 32'd0;
        end
    end

    // -------------------------------------------------------------------------
    // RX Engine: Streams bytes from TSE MAC into rx_ram
    // -------------------------------------------------------------------------
    // Ready when rx_ram is empty (!reg_rx_ready)
    assign rx_axis_tready = !reg_rx_ready;

    reg [8:0]  rx_word_idx;
    reg [1:0]  rx_byte_idx;
    reg [31:0] rx_word_accum;
    reg [15:0] rx_byte_count;

    always @(posedge clk or negedge rstn) begin
        if (!rstn) begin
            reg_rx_ready  <= 1'b0;
            reg_rx_err    <= 1'b0;
            reg_rx_len    <= 16'd0;
            rx_word_idx   <= 9'd0;
            rx_byte_idx   <= 2'd0;
            rx_word_accum <= 32'd0;
            rx_byte_count <= 16'd0;
        end else begin
            // Clear on CPU ACK
            if (rx_ack_trigger) begin
                reg_rx_ready  <= 1'b0;
                reg_rx_err    <= 1'b0;
                reg_rx_len    <= 16'd0;
                rx_word_idx   <= 9'd0;
                rx_byte_idx   <= 2'd0;
                rx_byte_count <= 16'd0;
            end

            // Capture incoming bytes
            if (rx_axis_tvalid && rx_axis_tready) begin
                rx_byte_count <= rx_byte_count + 1'b1;

                case (rx_byte_idx)
                    2'd0: rx_word_accum[7:0]   <= rx_axis_tdata;
                    2'd1: rx_word_accum[15:8]  <= rx_axis_tdata;
                    2'd2: rx_word_accum[23:16] <= rx_axis_tdata;
                    2'd3: begin
                        rx_word_accum[31:24]   <= rx_axis_tdata;
                        rx_ram[rx_word_idx]    <= {rx_axis_tdata, rx_word_accum[23:0]};
                        rx_word_idx            <= rx_word_idx + 1'b1;
                    end
                endcase
                rx_byte_idx <= rx_byte_idx + 1'b1;

                if (rx_axis_tlast) begin
                    // Flush remaining partial word
                    if (rx_byte_idx != 2'd3) begin
                        case (rx_byte_idx)
                            2'd0: rx_ram[rx_word_idx] <= {24'd0, rx_axis_tdata};
                            2'd1: rx_ram[rx_word_idx] <= {16'd0, rx_axis_tdata, rx_word_accum[7:0]};
                            2'd2: rx_ram[rx_word_idx] <= {8'd0, rx_axis_tdata, rx_word_accum[15:0]};
                            default: ;
                        endcase
                    end
                    reg_rx_len   <= rx_byte_count + 1'b1;
                    reg_rx_ready <= 1'b1;
                    reg_rx_err   <= rx_axis_tuser;
                end
            end
        end
    end

    // -------------------------------------------------------------------------
    // TX Engine: Streams bytes from tx_ram to TSE MAC
    // -------------------------------------------------------------------------
    typedef enum logic [1:0] {
        TX_IDLE,
        TX_FETCH,
        TX_STREAM
    } tx_fsm_t;

    tx_fsm_t tx_fsm;
    reg [8:0]  tx_word_idx;
    reg [1:0]  tx_byte_idx;
    reg [15:0] tx_bytes_sent;
    reg [31:0] tx_word_buf;

    always @(posedge clk or negedge rstn) begin
        if (!rstn) begin
            tx_fsm         <= TX_IDLE;
            reg_tx_busy    <= 1'b0;
            tx_axis_tvalid <= 1'b0;
            tx_axis_tlast  <= 1'b0;
            tx_axis_tuser  <= 1'b0;
            tx_axis_tdata  <= 8'd0;
            tx_word_idx    <= 9'd0;
            tx_byte_idx    <= 2'd0;
            tx_bytes_sent  <= 16'd0;
            tx_word_buf    <= 32'd0;
        end else begin
            case (tx_fsm)
                TX_IDLE: begin
                    tx_axis_tvalid <= 1'b0;
                    tx_axis_tlast  <= 1'b0;
                    tx_axis_tuser  <= 1'b0;
                    if (tx_trigger && reg_tx_len > 0) begin
                        reg_tx_busy   <= 1'b1;
                        tx_word_idx   <= 9'd0;
                        tx_byte_idx   <= 2'd0;
                        tx_bytes_sent <= 16'd0;
                        // Fetch first word from RAM
                        tx_word_buf   <= tx_ram[9'd0];
                        tx_fsm        <= TX_STREAM;
                    end else begin
                        reg_tx_busy   <= 1'b0;
                    end
                end

                TX_STREAM: begin
                    if (tx_axis_tvalid && tx_axis_tready && tx_axis_tlast) begin
                        // Last byte accepted by the MAC
                        tx_axis_tvalid <= 1'b0;
                        tx_axis_tlast  <= 1'b0;
                        tx_fsm         <= TX_IDLE;
                        reg_tx_busy    <= 1'b0;
                    end else if (!tx_axis_tvalid || tx_axis_tready) begin
                        // Output register is empty or being consumed: load the next byte
                        tx_axis_tvalid <= 1'b1;
                        case (tx_byte_idx)
                            2'd0: tx_axis_tdata <= tx_word_buf[7:0];
                            2'd1: tx_axis_tdata <= tx_word_buf[15:8];
                            2'd2: tx_axis_tdata <= tx_word_buf[23:16];
                            2'd3: tx_axis_tdata <= tx_word_buf[31:24];
                        endcase
                        tx_axis_tlast <= (tx_bytes_sent + 1'b1 >= reg_tx_len);
                        tx_bytes_sent <= tx_bytes_sent + 1'b1;
                        tx_byte_idx   <= tx_byte_idx + 1'b1;
                        if (tx_byte_idx == 2'd3) begin
                            tx_word_idx <= tx_word_idx + 1'b1;
                            tx_word_buf <= tx_ram[tx_word_idx + 1'b1];
                        end
                    end
                end

                default: tx_fsm <= TX_IDLE;
            endcase
        end
    end

endmodule
`default_nettype wire

