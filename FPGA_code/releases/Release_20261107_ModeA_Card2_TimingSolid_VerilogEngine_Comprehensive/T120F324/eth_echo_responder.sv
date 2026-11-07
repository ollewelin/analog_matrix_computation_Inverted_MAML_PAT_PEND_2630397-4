// =============================================================================
// eth_echo_responder.sv
// Hardware ARP & ICMP Echo (Ping) Responder for AXI4-Stream Ethernet MAC
// =============================================================================
// Connects to TSE MAC AXI-Stream RX & TX interface at 50 MHz sys_clk.
// 1. Detects ARP Request for TARGET_IP (192.168.1.50) -> Generates ARP Reply
// 2. Detects ICMP Echo Request for TARGET_IP -> Swaps MAC/IP, sets Echo Reply,
//    recalculates ICMP checksum (+0x0800) and sends reply.
// 3. Other broadcast/multicast packets can be safely dropped or bypassed.
// =============================================================================

`timescale 1ns / 1ps

module eth_echo_responder #(
    parameter [47:0] MY_MAC    = 48'h00_12_34_56_78_9A,
    parameter [31:0] TARGET_IP = 32'hC0_A8_01_32       // 192.168.1.50
)(
    input  wire        clk,
    input  wire        rstn,

    // AXI4-Stream RX from MAC
    input  wire [7:0]  s_axis_tdata,
    input  wire        s_axis_tvalid,
    input  wire        s_axis_tlast,
    input  wire        s_axis_tuser,
    output wire        s_axis_tready,

    // AXI4-Stream TX to MAC
    output reg  [7:0]  m_axis_tdata,
    output reg         m_axis_tvalid,
    output reg         m_axis_tlast,
    output reg         m_axis_tuser,
    input  wire        m_axis_tready
);

    // Buffer to hold incoming packet (up to 1536 bytes)
    reg [7:0]  pkt_buf [0:2047];
    reg [10:0] rx_len;
    reg [10:0] tx_ptr;
    reg [10:0] tx_len;
    reg [19:0] new_csum;

    typedef enum logic [2:0] {
        IDLE,
        RX_PKT,
        PROCESS,
        TX_PKT
    } state_t;

    state_t state;

    assign s_axis_tready = (state == IDLE || state == RX_PKT);

    always_ff @(posedge clk or negedge rstn) begin
        if (!rstn) begin
            state         <= IDLE;
            rx_len        <= '0;
            tx_ptr        <= '0;
            tx_len        <= '0;
            m_axis_tvalid <= 1'b0;
            m_axis_tlast  <= 1'b0;
            m_axis_tuser  <= 1'b0;
            m_axis_tdata  <= 8'h00;
        end else begin
            case (state)
                IDLE: begin
                    m_axis_tvalid <= 1'b0;
                    m_axis_tlast  <= 1'b0;
                    tx_ptr        <= '0;
                    if (s_axis_tvalid && s_axis_tready) begin
                        pkt_buf[0] <= s_axis_tdata;
                        rx_len     <= 11'd1;
                        state      <= s_axis_tlast ? PROCESS : RX_PKT;
                    end
                end

                RX_PKT: begin
                    if (s_axis_tvalid && s_axis_tready) begin
                        pkt_buf[rx_len] <= s_axis_tdata;
                        rx_len          <= rx_len + 11'd1;
                        if (s_axis_tlast) begin
                            state <= PROCESS;
                        end
                    end
                end

                PROCESS: begin
                    // Packet parsing
                    // Ethernet Header:
                    // 0..5: Dest MAC, 6..11: Src MAC, 12..13: EtherType
                    if (rx_len >= 11'd42 && pkt_buf[12] == 8'h08 && pkt_buf[13] == 8'h06) begin
                        // -------------------------------------------------------------
                        // ARP Packet (EtherType 0x0806)
                        // 14..15: HTYPE, 16..17: PTYPE, 18: HLEN(6), 19: PLEN(4)
                        // 20..21: Operation (1 = Request, 2 = Reply)
                        // 22..27: Sender MAC, 28..31: Sender IP
                        // 32..37: Target MAC, 38..41: Target IP
                        // -------------------------------------------------------------
                        if (pkt_buf[20] == 8'h00 && pkt_buf[21] == 8'h01 &&
                            {pkt_buf[38], pkt_buf[39], pkt_buf[40], pkt_buf[41]} == TARGET_IP) begin
                            
                            // Build ARP Reply:
                            // Ethernet Dest MAC = Sender MAC
                            pkt_buf[0]  <= pkt_buf[22];
                            pkt_buf[1]  <= pkt_buf[23];
                            pkt_buf[2]  <= pkt_buf[24];
                            pkt_buf[3]  <= pkt_buf[25];
                            pkt_buf[4]  <= pkt_buf[26];
                            pkt_buf[5]  <= pkt_buf[27];
                            // Ethernet Src MAC = MY_MAC
                            pkt_buf[6]  <= MY_MAC[47:40];
                            pkt_buf[7]  <= MY_MAC[39:32];
                            pkt_buf[8]  <= MY_MAC[31:24];
                            pkt_buf[9]  <= MY_MAC[23:16];
                            pkt_buf[10] <= MY_MAC[15:8];
                            pkt_buf[11] <= MY_MAC[7:0];

                            // ARP Opcode = 2 (Reply)
                            pkt_buf[21] <= 8'h02;

                            // Target MAC = Sender MAC
                            pkt_buf[32] <= pkt_buf[22];
                            pkt_buf[33] <= pkt_buf[23];
                            pkt_buf[34] <= pkt_buf[24];
                            pkt_buf[35] <= pkt_buf[25];
                            pkt_buf[36] <= pkt_buf[26];
                            pkt_buf[37] <= pkt_buf[27];

                            // Target IP = Sender IP
                            pkt_buf[38] <= pkt_buf[28];
                            pkt_buf[39] <= pkt_buf[29];
                            pkt_buf[40] <= pkt_buf[30];
                            pkt_buf[41] <= pkt_buf[31];

                            // Sender MAC = MY_MAC
                            pkt_buf[22] <= MY_MAC[47:40];
                            pkt_buf[23] <= MY_MAC[39:32];
                            pkt_buf[24] <= MY_MAC[31:24];
                            pkt_buf[25] <= MY_MAC[23:16];
                            pkt_buf[26] <= MY_MAC[15:8];
                            pkt_buf[27] <= MY_MAC[7:0];

                            // Sender IP = TARGET_IP
                            pkt_buf[28] <= TARGET_IP[31:24];
                            pkt_buf[29] <= TARGET_IP[23:16];
                            pkt_buf[30] <= TARGET_IP[15:8];
                            pkt_buf[31] <= TARGET_IP[7:0];

                            tx_len <= (rx_len < 11'd60) ? 11'd60 : rx_len; // Pad to min Ethernet frame 60 bytes
                            tx_ptr <= '0;
                            state  <= TX_PKT;
                        end else begin
                            state <= IDLE; // Drop other ARP
                        end

                    end else if (rx_len >= 11'd42 && pkt_buf[12] == 8'h08 && pkt_buf[13] == 8'h00) begin
                        // -------------------------------------------------------------
                        // IPv4 Packet (EtherType 0x0800)
                        // IP Header start at 14:
                        // 23: Protocol (1 = ICMP)
                        // 26..29: Src IP, 30..33: Dest IP
                        // -------------------------------------------------------------
                        if (pkt_buf[23] == 8'd1 && // ICMP
                            {pkt_buf[30], pkt_buf[31], pkt_buf[32], pkt_buf[33]} == TARGET_IP) begin
                            
                            // ICMP Header start at 34 (assuming standard 20-byte IP header without options):
                            // 34: Type (8 = Echo Request, 0 = Echo Reply)
                            // 35: Code
                            // 36..37: ICMP Checksum
                            if (pkt_buf[34] == 8'h08) begin
                                // 1. Swap Ethernet MACs
                                pkt_buf[0]  <= pkt_buf[6];
                                pkt_buf[1]  <= pkt_buf[7];
                                pkt_buf[2]  <= pkt_buf[8];
                                pkt_buf[3]  <= pkt_buf[9];
                                pkt_buf[4]  <= pkt_buf[10];
                                pkt_buf[5]  <= pkt_buf[11];
                                pkt_buf[6]  <= MY_MAC[47:40];
                                pkt_buf[7]  <= MY_MAC[39:32];
                                pkt_buf[8]  <= MY_MAC[31:24];
                                pkt_buf[9]  <= MY_MAC[23:16];
                                pkt_buf[10] <= MY_MAC[15:8];
                                pkt_buf[11] <= MY_MAC[7:0];

                                // 2. Swap IP addresses
                                pkt_buf[30] <= pkt_buf[26];
                                pkt_buf[31] <= pkt_buf[27];
                                pkt_buf[32] <= pkt_buf[28];
                                pkt_buf[33] <= pkt_buf[29];
                                pkt_buf[26] <= TARGET_IP[31:24];
                                pkt_buf[27] <= TARGET_IP[23:16];
                                pkt_buf[28] <= TARGET_IP[15:8];
                                pkt_buf[29] <= TARGET_IP[7:0];

                                // 3. Change ICMP Type to 0 (Echo Reply)
                                pkt_buf[34] <= 8'h00;

                                // 4. Update ICMP Checksum:
                                // RFC 1624: diff = ~old_type + new_type = ~0x0800 + 0x0000 = -0x0800
                                // checksum = checksum + 0x0800
                                new_csum = {pkt_buf[36], pkt_buf[37]} + 16'h0800;
                                if (new_csum[16]) new_csum = new_csum[15:0] + 16'd1;
                                pkt_buf[36] <= new_csum[15:8];
                                pkt_buf[37] <= new_csum[7:0];

                                tx_len <= rx_len;
                                tx_ptr <= '0;
                                state  <= TX_PKT;
                            end else begin
                                state <= IDLE;
                            end
                        end else begin
                            state <= IDLE;
                        end
                    end else begin
                        state <= IDLE;
                    end
                end

                TX_PKT: begin
                    if (tx_ptr < tx_len) begin
                        m_axis_tvalid <= 1'b1;
                        m_axis_tdata  <= (tx_ptr < rx_len) ? pkt_buf[tx_ptr] : 8'h00; // Zero pad if needed
                        m_axis_tlast  <= (tx_ptr == tx_len - 11'd1);
                        m_axis_tuser  <= 1'b0;
                        if (m_axis_tready) begin
                            tx_ptr <= tx_ptr + 11'd1;
                        end
                    end else begin
                        m_axis_tvalid <= 1'b0;
                        m_axis_tlast  <= 1'b0;
                        state         <= IDLE;
                    end
                end

                default: state <= IDLE;
            endcase
        end
    end

endmodule
