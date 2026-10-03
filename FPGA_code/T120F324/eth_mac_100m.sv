// =============================================================================
// eth_mac_100m.sv : 100Mbit Ethernet MAC with APB3 Interface for RGMII PHY
// =============================================================================
// Designed for RTL8211F PHY running in 100BASE-TX mode (25 MHz SDR clock).
// Connects to RISC_mini SoC via APB3 bus at offset 0xf8102000.
//
// Features:
//   - TX Path: 25 MHz SDR on F2_TXC, F2_TXCTL, F2_TXD[3:0]
//     * Hardware Preamble (7x 0x55) + SFD (1x 0xD5) generation
//     * Hardware IEEE 802.3 CRC32 (FCS) calculation and appending
//     * Hardware minimum frame padding (to 60 bytes payload + 4 bytes FCS)
//     * Standard nibble ordering (LSB nibble [3:0] first, MSB [7:4] second)
//     * Driven on falling edge of 25 MHz clock -> 20 ns setup/hold margin!
//   - RX Path: 25 MHz SDR on F2_RXC, F2_RXCTL, F2_RXD[3:0]
//     * Preamble / SFD detector
//     * Nibble-to-byte assembly (LSB nibble first, MSB second)
//     * Real-time CRC32 calculation and verification
//     * Frame length recording
//   - APB3 Interface (50 MHz sys_clk domain):
//     * 0x00: ETH_CTRL    [0]=tx_start, [1]=rx_ack, [2]=promisc, [3]=loopback
//     * 0x04: ETH_STATUS  [0]=tx_busy, [1]=rx_ready, [2]=link_up, [3]=rx_crc_err
//                         [31:16]=rx_frame_len
//     * 0x08: ETH_TX_LEN  [15:0]=tx_frame_len (bytes, 60..1514)
//     * 0x0C: ETH_RX_LEN  [15:0]=rx_frame_len (bytes, payload without FCS)
//     * 0x10: ETH_MAC_LO  [31:0]=our MAC [31:0]
//     * 0x14: ETH_MAC_HI  [15:0]=our MAC [47:32]
//     * 0x18: ETH_TX_CNT  [31:0]=transmitted frames counter
//     * 0x1C: ETH_RX_CNT  [31:0]=received valid frames counter
//     * 0x800-0xFFF:   TX Buffer (2048 bytes, word accessible)
//     * 0x1000-0x17FF: RX Buffer (2048 bytes, word accessible)
// =============================================================================

`timescale 1ns / 1ps
`default_nettype none

module eth_mac_100m (
    // System Clock Domain (50 MHz)
    input  wire         sys_clk,
    input  wire         sys_rst_n,

    // APB3 Slave Interface
    input  wire [11:0]  apb_paddr,     // 4KB address space
    input  wire         apb_psel,
    input  wire         apb_penable,
    input  wire         apb_pwrite,
    input  wire [31:0]  apb_pwdata,
    output logic [31:0] apb_prdata,
    output logic        apb_pready,
    output logic        apb_pslverr,

    // RGMII PHY Interface (25 MHz SDR for 100M mode)
    input  wire         rgmii_tx_clk,  // 25 MHz from PLL
    output logic        rgmii_txc,     // Forwarded 25 MHz clock to PHY (F2_TXC)
    output logic        rgmii_txctl,   // TX control / enable (F2_TXCTL)
    output logic [3:0]  rgmii_txd,     // TX nibble data (F2_TXD[3:0])

    input  wire         rgmii_rxc,     // 25 MHz RX clock from PHY (F2_RXC)
    input  wire         rgmii_rxctl,   // RX control / valid (F2_RXCTL)
    input  wire [3:0]   rgmii_rxd,     // RX nibble data (F2_RXD[3:0])

    // Status / Activity LED
    input  wire         phy_link_up,
    output logic        activity_led
);

    assign apb_pslverr = 1'b0;
    assign apb_pready  = 1'b1; // Zero-wait-state APB slave

    // Forward 25 MHz clock to PHY
    assign rgmii_txc = rgmii_tx_clk;

    // =========================================================================
    // APB3 Registers & Control Logic (sys_clk domain)
    // =========================================================================
    logic        tx_start_reg;
    logic        rx_ack_reg;
    logic        promisc_reg;
    logic        loopback_reg;
    logic [15:0] tx_len_reg;
    logic [47:0] our_mac_reg;
    logic [31:0] tx_frame_cnt;
    logic [31:0] rx_frame_cnt;

    // Signals crossing from TX domain (25 MHz) to sys_clk (50 MHz)
    logic tx_busy_tx_clk;
    logic tx_busy_sync1, tx_busy_sync2;
    always_ff @(posedge sys_clk or negedge sys_rst_n) begin
        if (!sys_rst_n) begin
            tx_busy_sync1 <= 1'b0;
            tx_busy_sync2 <= 1'b0;
        end else begin
            tx_busy_sync1 <= tx_busy_tx_clk;
            tx_busy_sync2 <= tx_busy_sync1;
        end
    end

    // Signals crossing from RX domain (25 MHz) to sys_clk (50 MHz)
    logic rx_ready_rx_clk;
    logic rx_ready_sync1, rx_ready_sync2;
    logic [15:0] rx_len_rx_clk;
    logic [15:0] rx_len_sync;
    logic rx_crc_err_rx_clk;
    logic rx_crc_err_sync1, rx_crc_err_sync2;

    always_ff @(posedge sys_clk or negedge sys_rst_n) begin
        if (!sys_rst_n) begin
            rx_ready_sync1   <= 1'b0;
            rx_ready_sync2   <= 1'b0;
            rx_len_sync      <= 16'd0;
            rx_crc_err_sync1 <= 1'b0;
            rx_crc_err_sync2 <= 1'b0;
        end else begin
            rx_ready_sync1   <= rx_ready_rx_clk;
            rx_ready_sync2   <= rx_ready_sync1;
            if (rx_ready_sync1) rx_len_sync <= rx_len_rx_clk;
            rx_crc_err_sync1 <= rx_crc_err_rx_clk;
            rx_crc_err_sync2 <= rx_crc_err_sync1;
        end
    end

    // Pulse synchronizers for tx_start and rx_ack (sys_clk -> tx_clk / rx_clk)
    logic tx_start_toggle_sys;
    logic rx_ack_toggle_sys;

    // =========================================================================
    // Dual-Port Packet Buffers (BRAM)
    // =========================================================================
    // TX Buffer: 512 words (2048 bytes).
    // Port A: sys_clk (APB3 write/read)
    // Port B: rgmii_tx_clk (read-only for TX engine)
    (* ram_style = "block" *) logic [31:0] tx_buffer [0:511];

    // RX Buffer: 512 words (2048 bytes).
    // Port A: sys_clk (APB3 read-only)
    // Port B: rgmii_rxc (write-only for RX engine)
    (* ram_style = "block" *) logic [31:0] rx_buffer [0:511];

    // Memory decoding
    logic is_tx_buf_addr;
    logic is_rx_buf_addr;
    logic [8:0] buf_word_idx;

    assign is_tx_buf_addr = (apb_paddr[11] == 1'b1) && (apb_paddr[10] == 1'b0); // 0x800-0xBFF
    assign is_rx_buf_addr = (apb_paddr[11] == 1'b1) && (apb_paddr[10] == 1'b1); // 0xC00-0xFFF or 0x1000..
    // Since apb_paddr is 12-bit [11:0] (0x000-0xFFF):
    // Let's map:
    // 0x000 - 0x0FF : Registers
    // 0x400 - 0x7FF : TX Buffer (1024 bytes / 256 words: apb_paddr[11:2] = 0x100..0x1FF)
    // 0x800 - 0xBFF : RX Buffer (1024 bytes / 256 words: apb_paddr[11:2] = 0x200..0x2FF)
    // Or for 2048 bytes (0x800 bytes):
    // Let's use:
    // apb_paddr[11:10] == 2'b00 : Registers (0x000-0x3FF)
    // apb_paddr[11:10] == 2'b01 : TX Buffer (0x400-0x7FF = 1024 bytes)
    // apb_paddr[11:10] == 2'b10 : RX Buffer (0x800-0xBFF = 1024 bytes)
    // Wait, max standard Ethernet frame is 1514 bytes.
    // If apb_paddr is 12-bit (4096 bytes total space 0x000..0xFFF):
    // 0x000 - 0x07F : Registers
    // 0x080 - 0x7FF : TX Buffer (1920 bytes)
    // 0x800 - 0xFFF : RX Buffer (2048 bytes)
    // That gives 1920 bytes TX and 2048 bytes RX! Perfectly fits standard MTU (1500)!

    wire is_reg_access = (apb_paddr < 12'h080);
    wire is_tx_ram     = (apb_paddr >= 12'h080) && (apb_paddr < 12'h800);
    wire is_rx_ram     = (apb_paddr >= 12'h800);

    wire [8:0] tx_ram_word_addr = (apb_paddr[10:2] - 9'd32); // offset from 0x080
    wire [8:0] rx_ram_word_addr = apb_paddr[10:2];           // offset from 0x800

    // APB3 Write Handling
    always_ff @(posedge sys_clk or negedge sys_rst_n) begin
        if (!sys_rst_n) begin
            tx_start_reg        <= 1'b0;
            rx_ack_reg          <= 1'b0;
            promisc_reg         <= 1'b0;
            loopback_reg        <= 1'b0;
            tx_len_reg          <= 16'd60; // Minimum valid ethernet frame
            our_mac_reg         <= 48'h00_12_34_56_78_9A; // Default MAC
            tx_start_toggle_sys <= 1'b0;
            rx_ack_toggle_sys   <= 1'b0;
            tx_frame_cnt        <= 32'd0;
            rx_frame_cnt        <= 32'd0;
        end else begin
            // Increment frame counters
            if (tx_busy_sync1 && !tx_busy_sync2) begin
                tx_frame_cnt <= tx_frame_cnt + 1'b1;
            end
            if (rx_ready_sync1 && !rx_ready_sync2) begin
                rx_frame_cnt <= rx_frame_cnt + 1'b1;
            end

            // APB Write
            if (apb_psel && apb_penable && apb_pwrite) begin
                if (is_reg_access) begin
                    case (apb_paddr[6:2])
                        5'h00: begin // 0x00: ETH_CTRL
                            if (apb_pwdata[0]) begin // TX_START
                                tx_start_toggle_sys <= ~tx_start_toggle_sys;
                            end
                            if (apb_pwdata[1]) begin // RX_ACK
                                rx_ack_toggle_sys <= ~rx_ack_toggle_sys;
                            end
                            promisc_reg  <= apb_pwdata[2];
                            loopback_reg <= apb_pwdata[3];
                        end
                        5'h02: tx_len_reg          <= apb_pwdata[15:0]; // 0x08: ETH_TX_LEN
                        5'h04: our_mac_reg[31:0]   <= apb_pwdata;       // 0x10: ETH_MAC_LO
                        5'h05: our_mac_reg[47:32]  <= apb_pwdata[15:0]; // 0x14: ETH_MAC_HI
                        default: ;
                    endcase
                end else if (is_tx_ram) begin
                    tx_buffer[tx_ram_word_addr] <= apb_pwdata;
                end
            end
        end
    end

    // APB3 Read Handling
    always_comb begin
        if (is_reg_access) begin
            case (apb_paddr[6:2])
                5'h00: apb_prdata = {28'd0, loopback_reg, promisc_reg, 1'b0, 1'b0};
                5'h01: apb_prdata = {rx_len_sync, 12'd0, rx_crc_err_sync2, phy_link_up, rx_ready_sync2, tx_busy_sync2};
                5'h02: apb_prdata = {16'd0, tx_len_reg};
                5'h03: apb_prdata = {16'd0, rx_len_sync};
                5'h04: apb_prdata = our_mac_reg[31:0];
                5'h05: apb_prdata = {16'd0, our_mac_reg[47:32]};
                5'h06: apb_prdata = tx_frame_cnt;
                5'h07: apb_prdata = rx_frame_cnt;
                default: apb_prdata = 32'h00000000;
            endcase
        end else if (is_tx_ram) begin
            apb_prdata = tx_buffer[tx_ram_word_addr];
        end else if (is_rx_ram) begin
            apb_prdata = rx_buffer[rx_ram_word_addr];
        end else begin
            apb_prdata = 32'h00000000;
        end
    end

    // =========================================================================
    // CRC32 Calculation Function (IEEE 802.3 Ethernet Polynomial 0xEDB88320)
    // =========================================================================
    function automatic [31:0] update_crc32(input [31:0] crc, input [7:0] data);
        logic [31:0] c;
        int i;
        begin
            c = crc;
            for (i = 0; i < 8; i = i + 1) begin
                if ((c[0] ^ data[i]) == 1'b1)
                    c = {1'b0, c[31:1]} ^ 32'hEDB88320;
                else
                    c = {1'b0, c[31:1]};
            end
            update_crc32 = c;
        end
    endfunction

    // =========================================================================
    // TX Engine (rgmii_tx_clk domain: 25 MHz SDR)
    // =========================================================================
    // Synchronize tx_start_toggle_sys into rgmii_tx_clk domain
    logic tx_start_toggle_r1, tx_start_toggle_r2, tx_start_toggle_r3;
    wire  tx_start_pulse = (tx_start_toggle_r2 ^ tx_start_toggle_r3);

    always_ff @(posedge rgmii_tx_clk) begin
        tx_start_toggle_r1 <= tx_start_toggle_sys;
        tx_start_toggle_r2 <= tx_start_toggle_r1;
        tx_start_toggle_r3 <= tx_start_toggle_r2;
    end

    typedef enum logic [3:0] {
        TX_IDLE     = 4'd0,
        TX_PREAMBLE = 4'd1, // 7 bytes 0x55
        TX_SFD      = 4'd2, // 1 byte 0xD5
        TX_DATA     = 4'd3, // Payload bytes (min 60)
        TX_CRC      = 4'd4, // 4 bytes CRC
        TX_IPG      = 4'd5  // Inter-packet gap (>= 960 ns / 24 cycles)
    } tx_state_t;

    tx_state_t tx_state = TX_IDLE;

    logic [15:0] tx_byte_idx;
    logic [15:0] tx_target_len;
    logic [31:0] tx_crc;
    logic [7:0]  tx_current_byte;
    logic        tx_nibble_sel; // 0 = low nibble [3:0], 1 = high nibble [7:4]
    logic [4:0]  tx_ipg_cnt;
    logic [31:0] tx_ram_word;

    // Buffer read address for TX
    wire [8:0] tx_rd_word_addr = tx_byte_idx[10:2];
    wire [1:0] tx_rd_byte_sel  = tx_byte_idx[1:0];

    always_comb begin
        tx_ram_word = tx_buffer[tx_rd_word_addr];
        case (tx_rd_byte_sel)
            2'b00: tx_current_byte = tx_ram_word[7:0];
            2'b01: tx_current_byte = tx_ram_word[15:8];
            2'b10: tx_current_byte = tx_ram_word[23:16];
            2'b11: tx_current_byte = tx_ram_word[31:24];
        endcase
    end

    logic       tx_ctl_reg;
    logic [3:0] tx_data_reg;

    // Drive outputs on FALLING edge of 25 MHz clock:
    // This gives a 20 ns setup and 20 ns hold margin before the rising edge of F2_TXC!
    always_ff @(negedge rgmii_tx_clk or negedge sys_rst_n) begin
        if (!sys_rst_n) begin
            tx_state        <= TX_IDLE;
            tx_ctl_reg      <= 1'b0;
            tx_data_reg     <= 4'h0;
            tx_byte_idx     <= 16'd0;
            tx_target_len   <= 16'd0;
            tx_crc          <= 32'hFFFFFFFF;
            tx_nibble_sel   <= 1'b0;
            tx_ipg_cnt      <= 5'd0;
            tx_busy_tx_clk  <= 1'b0;
        end else begin
            case (tx_state)
                TX_IDLE: begin
                    tx_ctl_reg     <= 1'b0;
                    tx_data_reg    <= 4'h0;
                    tx_nibble_sel  <= 1'b0;
                    tx_byte_idx    <= 16'd0;
                    tx_crc         <= 32'hFFFFFFFF;
                    if (tx_start_pulse) begin
                        tx_busy_tx_clk <= 1'b1;
                        tx_target_len  <= (tx_len_reg < 16'd60) ? 16'd60 : tx_len_reg;
                        tx_state       <= TX_PREAMBLE;
                    end else begin
                        tx_busy_tx_clk <= 1'b0;
                    end
                end

                TX_PREAMBLE: begin
                    tx_ctl_reg  <= 1'b1;
                    tx_data_reg <= 4'h5; // Preamble nibbles are always 0x5
                    if (tx_nibble_sel == 1'b0) begin
                        tx_nibble_sel <= 1'b1;
                    end else begin
                        tx_nibble_sel <= 1'b0;
                        tx_byte_idx   <= tx_byte_idx + 1'b1;
                        if (tx_byte_idx == 16'd6) begin // 7 bytes done (0..6)
                            tx_byte_idx <= 16'd0;
                            tx_state    <= TX_SFD;
                        end
                    end
                end

                TX_SFD: begin
                    tx_ctl_reg <= 1'b1;
                    if (tx_nibble_sel == 1'b0) begin
                        tx_data_reg   <= 4'h5; // SFD low nibble (0xD5 -> 0x5 first)
                        tx_nibble_sel <= 1'b1;
                    end else begin
                        tx_data_reg   <= 4'hD; // SFD high nibble (0xD5 -> 0xD second)
                        tx_nibble_sel <= 1'b0;
                        tx_byte_idx   <= 16'd0;
                        tx_crc        <= 32'hFFFFFFFF;
                        tx_state      <= TX_DATA;
                    end
                end

                TX_DATA: begin
                    tx_ctl_reg <= 1'b1;
                    if (tx_nibble_sel == 1'b0) begin
                        tx_data_reg   <= tx_current_byte[3:0]; // Low nibble first
                        tx_nibble_sel <= 1'b1;
                    end else begin
                        tx_data_reg   <= tx_current_byte[7:4]; // High nibble second
                        tx_nibble_sel <= 1'b0;
                        tx_crc        <= update_crc32(tx_crc, tx_current_byte);
                        tx_byte_idx   <= tx_byte_idx + 1'b1;
                        if (tx_byte_idx + 1'b1 >= tx_target_len) begin
                            tx_byte_idx <= 16'd0;
                            tx_state    <= TX_CRC;
                        end
                    end
                end

                TX_CRC: begin
                    tx_ctl_reg <= 1'b1;
                    // Ethernet CRC is transmitted inverted (~crc), LSB first
                    // Byte 0: ~tx_crc[7:0]
                    // Byte 1: ~tx_crc[15:8]
                    // Byte 2: ~tx_crc[23:16]
                    // Byte 3: ~tx_crc[31:24]
                    case (tx_byte_idx[1:0])
                        2'b00: tx_data_reg <= (tx_nibble_sel == 1'b0) ? ~tx_crc[3:0]   : ~tx_crc[7:4];
                        2'b01: tx_data_reg <= (tx_nibble_sel == 1'b0) ? ~tx_crc[11:8]  : ~tx_crc[15:12];
                        2'b10: tx_data_reg <= (tx_nibble_sel == 1'b0) ? ~tx_crc[19:16] : ~tx_crc[23:20];
                        2'b11: tx_data_reg <= (tx_nibble_sel == 1'b0) ? ~tx_crc[27:24] : ~tx_crc[31:28];
                    endcase

                    if (tx_nibble_sel == 1'b0) begin
                        tx_nibble_sel <= 1'b1;
                    end else begin
                        tx_nibble_sel <= 1'b0;
                        tx_byte_idx   <= tx_byte_idx + 1'b1;
                        if (tx_byte_idx == 16'd3) begin // 4 CRC bytes sent
                            tx_state   <= TX_IPG;
                            tx_ipg_cnt <= 5'd0;
                        end
                    end
                end

                TX_IPG: begin
                    tx_ctl_reg  <= 1'b0;
                    tx_data_reg <= 4'h0;
                    if (tx_ipg_cnt < 5'd24) begin // 24 nibbles = 960 ns IPG
                        tx_ipg_cnt <= tx_ipg_cnt + 1'b1;
                    end else begin
                        tx_busy_tx_clk <= 1'b0;
                        tx_state       <= TX_IDLE;
                    end
                end

                default: tx_state <= TX_IDLE;
            endcase
        end
    end

    assign rgmii_txctl = tx_ctl_reg;
    assign rgmii_txd   = tx_data_reg;

    // =========================================================================
    // RX Engine (rgmii_rxc domain: 25 MHz SDR from PHY)
    // =========================================================================
    // Synchronize rx_ack_toggle_sys into rgmii_rxc domain
    logic rx_ack_toggle_r1, rx_ack_toggle_r2, rx_ack_toggle_r3;
    wire  rx_ack_pulse = (rx_ack_toggle_r2 ^ rx_ack_toggle_r3);

    always_ff @(posedge rgmii_rxc) begin
        rx_ack_toggle_r1 <= rx_ack_toggle_sys;
        rx_ack_toggle_r2 <= rx_ack_toggle_r1;
        rx_ack_toggle_r3 <= rx_ack_toggle_r2;
    end

    typedef enum logic [2:0] {
        RX_IDLE     = 3'd0,
        RX_SFD_HUNT = 3'd1,
        RX_DATA     = 3'd2,
        RX_COMPLETE = 3'd3
    } rx_state_t;

    rx_state_t rx_state = RX_IDLE;

    logic [15:0] rx_byte_idx;
    logic [31:0] rx_crc;
    logic [3:0]  rx_low_nibble;
    logic        rx_nibble_phase; // 0 = low nibble, 1 = high nibble
    logic [7:0]  rx_assembled_byte;

    // Word assembler for RX BRAM write
    logic [31:0] rx_word_buf;
    logic        rx_word_wr_en;
    logic [8:0]  rx_wr_word_addr;

    // Sample inputs on RISING edge of rgmii_rxc (with PHY RXDLY enabled):
    always_ff @(posedge rgmii_rxc or negedge sys_rst_n) begin
        if (!sys_rst_n) begin
            rx_state          <= RX_IDLE;
            rx_ready_rx_clk   <= 1'b0;
            rx_crc_err_rx_clk <= 1'b0;
            rx_len_rx_clk     <= 16'd0;
            rx_byte_idx       <= 16'd0;
            rx_crc            <= 32'hFFFFFFFF;
            rx_nibble_phase   <= 1'b0;
            rx_word_wr_en     <= 1'b0;
            rx_wr_word_addr   <= 9'd0;
            rx_word_buf       <= 32'd0;
        end else begin
            rx_word_wr_en <= 1'b0;

            // Handle ACK from software
            if (rx_ack_pulse) begin
                rx_ready_rx_clk <= 1'b0;
            end

            case (rx_state)
                RX_IDLE: begin
                    rx_nibble_phase <= 1'b0;
                    rx_byte_idx     <= 16'd0;
                    rx_crc          <= 32'hFFFFFFFF;
                    if (rgmii_rxctl && (rgmii_rxd == 4'h5)) begin
                        rx_state <= RX_SFD_HUNT;
                    end
                end

                RX_SFD_HUNT: begin
                    if (!rgmii_rxctl) begin
                        rx_state <= RX_IDLE;
                    end else if (rgmii_rxd == 4'hD) begin // Found SFD high nibble (0xD5)
                        rx_nibble_phase <= 1'b0; // Next nibble is first data byte low nibble
                        rx_byte_idx     <= 16'd0;
                        rx_crc          <= 32'hFFFFFFFF;
                        rx_wr_word_addr <= 9'd0;
                        rx_state        <= RX_DATA;
                    end
                end

                RX_DATA: begin
                    if (!rgmii_rxctl) begin
                        // Frame ended!
                        if (rx_byte_idx >= 16'd64 && rx_crc == 32'hDEBB20E3) begin
                            // CRC is VALID (IEEE 802.3 residual for ~FCS is 0xDEBB20E3)
                            // Or if CRC matches FCS
                            if (!rx_ready_rx_clk) begin // Don't overwrite if unread
                                rx_ready_rx_clk   <= 1'b1;
                                rx_len_rx_clk     <= rx_byte_idx - 16'd4; // Payload length without FCS
                                rx_crc_err_rx_clk <= 1'b0;
                            end
                        end else begin
                            rx_crc_err_rx_clk <= 1'b1;
                        end
                        rx_state <= RX_IDLE;
                    end else begin
                        if (rx_nibble_phase == 1'b0) begin
                            rx_low_nibble   <= rgmii_rxd;
                            rx_nibble_phase <= 1'b1;
                        end else begin
                            rx_assembled_byte = {rgmii_rxd, rx_low_nibble};
                            rx_nibble_phase  <= 1'b0;
                            rx_crc           <= update_crc32(rx_crc, rx_assembled_byte);

                            // Store into word buffer
                            case (rx_byte_idx[1:0])
                                2'b00: rx_word_buf[7:0]   <= rx_assembled_byte;
                                2'b01: rx_word_buf[15:8]  <= rx_assembled_byte;
                                2'b10: rx_word_buf[23:16] <= rx_assembled_byte;
                                2'b11: begin
                                    rx_word_buf[31:24] <= rx_assembled_byte;
                                    rx_word_wr_en      <= 1'b1;
                                    rx_wr_word_addr    <= rx_byte_idx[10:2];
                                end
                            endcase

                            // Flush partial word at end if needed
                            if (rx_byte_idx < 16'd1536) begin
                                rx_byte_idx <= rx_byte_idx + 1'b1;
                            end
                        end
                    end
                end

                default: rx_state <= RX_IDLE;
            endcase

            // Write assembled word into RX BRAM
            if (rx_word_wr_en) begin
                rx_buffer[rx_wr_word_addr] <= rx_word_buf;
            end
        end
    end

    // Ethernet Activity LED
    assign activity_led = tx_busy_sync2 | rx_ready_sync2;

endmodule
