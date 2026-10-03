/**
 * UART_mini.sv - Simple standalone UART module with 32-byte FIFOs
 * 
 * Features:
 * - 32-byte input (TX) FIFO buffer
 * - 32-byte output (RX) FIFO buffer
 * - Simple flag-based interface: empty_tx, full_tx, empty_rx, full_rx
 * - 8-bit data ports: uart_tx_byte (to send), uart_rx_byte (received)
 * - Configurable baud rate via parameter
 * - Standard UART protocol: 1 start bit, 8 data bits, 1 stop bit, no parity
 * 
 * Integration with SoC:
 * - SoC polls empty_rx / full_rx flags
 * - SoC reads uart_rx_byte when data available
 * - SoC writes uart_tx_byte and sets tx_write strobe
 * - SoC polls empty_tx / full_tx to manage TX throughput
 */

module uart_mini #(
    parameter CLK_FREQ_HZ = 50_000_000,     // FPGA clock frequency (50 MHz default)
    parameter BAUD_RATE = 115200,            // UART baud rate
    parameter FIFO_DEPTH = 32                // 32-byte FIFO for both TX and RX
) (
    // Clock and reset
    input  logic clk,
    input  logic rst_n,
    
    // Physical UART pins
    output logic uart_txd,                   // UART TX (to external FTDI/serial device)
    input  logic uart_rxd,                   // UART RX (from external FTDI/serial device)
    
    // TX FIFO interface (SoC writes data to send)
    input  logic [7:0] tx_data,              // Data byte to transmit
    input  logic tx_write,                   // Write strobe (pulse high to add byte to TX FIFO)
    output logic tx_empty,                   // TX FIFO empty flag
    output logic tx_full,                    // TX FIFO full flag
    
    // RX FIFO interface (SoC reads received data)
    output logic [7:0] rx_data,              // Received data byte
    input  logic rx_read,                    // Read strobe (pulse high to remove byte from RX FIFO)
    output logic rx_empty,                   // RX FIFO empty flag
    output logic rx_full,                    // RX FIFO full flag
    
    // Debug/status (optional)
    output logic [4:0] tx_count,             // Number of bytes in TX FIFO
    output logic [4:0] rx_count              // Number of bytes in RX FIFO
);

    // ========== UART Clock Division for Baud Rate ==========
    // Calculate baud clock divisor to generate UART bit rate
    localparam BAUD_DIVISOR = CLK_FREQ_HZ / (BAUD_RATE * 16);  // 16x oversampling
    localparam BAUD_CNT_WIDTH = $clog2(BAUD_DIVISOR);
    
    logic [BAUD_CNT_WIDTH-1:0] baud_cnt;
    logic baud_tick;  // Single-cycle pulse at 16x baud rate
    
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            baud_cnt <= '0;
            baud_tick <= 1'b0;
        end else begin
            if (baud_cnt >= BAUD_DIVISOR - 1) begin
                baud_cnt <= '0;
                baud_tick <= 1'b1;
            end else begin
                baud_cnt <= baud_cnt + 1;
                baud_tick <= 1'b0;
            end
        end
    end
    
    // ========== TX FIFO (32 bytes) ==========
    logic [7:0] tx_fifo [0:FIFO_DEPTH-1];
    logic [4:0] tx_wr_ptr, tx_rd_ptr;
    logic [4:0] tx_count_next;
    
    assign tx_empty = (tx_wr_ptr == tx_rd_ptr);
    assign tx_full = ((tx_wr_ptr + 1) == tx_rd_ptr);  // Simplified - wraps at 32
    assign tx_count = tx_wr_ptr - tx_rd_ptr;
    
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            tx_wr_ptr <= '0;
        end else if (tx_write && !tx_full) begin
            tx_fifo[tx_wr_ptr[4:0]] <= tx_data;
            tx_wr_ptr <= tx_wr_ptr + 1;
        end
    end
    
    // ========== RX FIFO (32 bytes) ==========
    logic [7:0] rx_fifo [0:FIFO_DEPTH-1];
    logic [4:0] rx_wr_ptr, rx_rd_ptr;
    
    assign rx_empty = (rx_wr_ptr == rx_rd_ptr);
    assign rx_full = ((rx_wr_ptr + 1) == rx_rd_ptr);
    assign rx_count = rx_wr_ptr - rx_rd_ptr;
    assign rx_data = rx_fifo[rx_rd_ptr[4:0]];
    
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rx_rd_ptr <= '0;
        end else if (rx_read && !rx_empty) begin
            rx_rd_ptr <= rx_rd_ptr + 1;
        end
    end
    
    // ========== TX ENGINE (Serial transmission) ==========
    // State machine for transmitting bytes from TX FIFO
    
    typedef enum logic [2:0] {
        TX_IDLE,      // Waiting for data in TX FIFO
        TX_START,     // Send start bit (0)
        TX_DATA,      // Send 8 data bits
        TX_STOP       // Send stop bit (1)
    } tx_state_t;
    
    tx_state_t tx_state, tx_state_next;
    logic [3:0] tx_bit_cnt;      // Which bit (0-7) of the 8 data bits
    logic [3:0] tx_oversample;   // 16x oversampling counter
    logic [7:0] tx_shift_reg;
    
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            tx_state <= TX_IDLE;
            tx_bit_cnt <= '0;
            tx_oversample <= '0;
            tx_shift_reg <= 8'hFF;
            uart_txd <= 1'b1;  // UART idle = 1
        end else if (baud_tick) begin
            case (tx_state)
                TX_IDLE: begin
                    uart_txd <= 1'b1;  // Keep line idle
                    if (!tx_empty) begin
                        tx_state <= TX_START;
                        tx_shift_reg <= tx_fifo[tx_rd_ptr[4:0]];
                        tx_oversample <= 4'h0;
                    end
                end
                
                TX_START: begin
                    uart_txd <= 1'b0;  // Start bit
                    if (tx_oversample == 4'hF) begin
                        tx_state <= TX_DATA;
                        tx_bit_cnt <= 4'h0;
                        tx_oversample <= 4'h0;
                    end else begin
                        tx_oversample <= tx_oversample + 1;
                    end
                end
                
                TX_DATA: begin
                    uart_txd <= tx_shift_reg[0];  // Send LSB first
                    if (tx_oversample == 4'hF) begin
                        if (tx_bit_cnt == 4'h7) begin
                            tx_state <= TX_STOP;
                            tx_bit_cnt <= 4'h0;
                        end else begin
                            tx_bit_cnt <= tx_bit_cnt + 1;
                        end
                        tx_shift_reg <= {1'b0, tx_shift_reg[7:1]};  // Shift right
                        tx_oversample <= 4'h0;
                    end else begin
                        tx_oversample <= tx_oversample + 1;
                    end
                end
                
                TX_STOP: begin
                    uart_txd <= 1'b1;  // Stop bit (1)
                    if (tx_oversample == 4'hF) begin
                        tx_state <= TX_IDLE;
                        tx_rd_ptr <= tx_rd_ptr + 1;  // Advance read pointer
                        tx_oversample <= 4'h0;
                    end else begin
                        tx_oversample <= tx_oversample + 1;
                    end
                end
                
                default: tx_state <= TX_IDLE;
            endcase
        end
    end
    
    // ========== RX ENGINE (Serial reception) ==========
    // Receives UART bytes and stores in RX FIFO
    
    typedef enum logic [2:0] {
        RX_IDLE,      // Waiting for start bit
        RX_START,     // Receiving start bit
        RX_DATA,      // Receiving data bits
        RX_STOP       // Receiving stop bit
    } rx_state_t;
    
    rx_state_t rx_state, rx_state_next;
    logic [3:0] rx_bit_cnt;
    logic [3:0] rx_oversample;
    logic [7:0] rx_shift_reg;
    logic rx_sample;
    
    // Synchronize RX input with clock domain
    logic [2:0] uart_rxd_sync;
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            uart_rxd_sync <= 3'b111;
        else
            uart_rxd_sync <= {uart_rxd_sync[1:0], uart_rxd};
    end
    
    // Sample RX line at center of bit (oversample = 8)
    assign rx_sample = uart_rxd_sync[2];
    
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rx_state <= RX_IDLE;
            rx_bit_cnt <= '0;
            rx_oversample <= '0;
            rx_shift_reg <= '0;
            rx_wr_ptr <= '0;
        end else if (baud_tick) begin
            case (rx_state)
                RX_IDLE: begin
                    if (!rx_sample) begin  // Start bit detected (line went low)
                        rx_state <= RX_START;
                        rx_oversample <= 4'h0;
                    end
                end
                
                RX_START: begin
                    if (rx_oversample == 4'hF) begin
                        rx_state <= RX_DATA;
                        rx_bit_cnt <= 4'h0;
                        rx_oversample <= 4'h0;
                    end else begin
                        rx_oversample <= rx_oversample + 1;
                    end
                end
                
                RX_DATA: begin
                    if (rx_oversample == 4'h7) begin
                        rx_shift_reg <= {rx_sample, rx_shift_reg[7:1]};  // Shift in MSB
                    end
                    if (rx_oversample == 4'hF) begin
                        if (rx_bit_cnt == 4'h7) begin
                            rx_state <= RX_STOP;
                            rx_bit_cnt <= 4'h0;
                        end else begin
                            rx_bit_cnt <= rx_bit_cnt + 1;
                        end
                        rx_oversample <= 4'h0;
                    end else begin
                        rx_oversample <= rx_oversample + 1;
                    end
                end
                
                RX_STOP: begin
                    if (rx_oversample == 4'hF) begin
                        // Valid stop bit received, store byte in RX FIFO if not full
                        if (!rx_full) begin
                            rx_fifo[rx_wr_ptr[4:0]] <= rx_shift_reg;
                            rx_wr_ptr <= rx_wr_ptr + 1;
                        end
                        rx_state <= RX_IDLE;
                        rx_oversample <= 4'h0;
                    end else begin
                        rx_oversample <= rx_oversample + 1;
                    end
                end
                
                default: rx_state <= RX_IDLE;
            endcase
        end
    end

endmodule
