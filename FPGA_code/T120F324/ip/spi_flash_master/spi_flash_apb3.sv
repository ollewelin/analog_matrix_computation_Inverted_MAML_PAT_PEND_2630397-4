// =============================================================================
// spi_flash_apb3.sv : Memory-Mapped SPI Flash Master with APB3 Interface
// =============================================================================
// Connects to W25Q128JVSIQ (U99) external configuration SPI flash on T120 FPGA:
//   - spi_cs_n   : Chip select (active low)
//   - spi_sclk   : SPI clock (Mode 0: CPOL=0, CPHA=0)
//   - spi_mosi   : Master Out Slave In
//   - spi_miso   : Master In Slave Out
//   - spi_wp_n   : Write protect (drive 1)
//   - spi_hold_n : Hold (drive 1)
//
// Includes Remote Update / Reconfiguration triggers:
//   - cfg_CONFIG : Pulse high to trigger FPGA reload from flash!
//   - cfg_CBSEL  : Image selector [1:0]
//   - cfg_ENA    : Image select latch enable
//
// Register Map (offset from base, e.g. 0xf8103000):
//   0x00 [RW] DATA_XFER:
//             Write [7:0]: Transmit byte over SPI, starts transfer
//             Read  [7:0]: Received byte from last SPI transfer
//   0x04 [RW] STATUS_CTRL:
//             Bit 0 [RO]: BUSY (1 = SPI transfer in progress)
//             Bit 1 [RW]: CS_N (0 = Assert /CS low, 1 = Deassert /CS high)
//             Bit 2 [RW]: WP_N (default 1)
//             Bit 3 [RW]: HOLD_N (default 1)
//             Bits [15:8] [RW]: CLK_DIV (SPI SCLK divider: F_sclk = F_clk / (2 * (DIV+1)), default 2 = 8.33MHz @ 50MHz)
//   0x08 [RW] RECONFIG_CTRL:
//             Bit 0 [WO]: TRIGGER (Write 1 to trigger FPGA reconfiguration from Flash)
//             Bits [2:1] [RW]: CBSEL (Target bitstream image index: 0=default, 1, 2, 3)
//             Bit 3 [RO]: ERROR (Status of previous remote update, from cfg_ERROR)
//             Bit 4 [RO]: USR_STATUS (User mode status)
// =============================================================================

`timescale 1ns / 1ps

module spi_flash_apb3 #(
    parameter int DEFAULT_DIVIDER = 2 // 50 MHz / (2 * (2 + 1)) = 8.33 MHz
)(
    input  logic        pclk,
    input  logic        presetn,
    input  logic        psel,
    input  logic        penable,
    input  logic        pwrite,
    input  logic [11:0] paddr,
    input  logic [31:0] pwdata,
    output logic [31:0] prdata,
    output logic        pready,
    output logic        pslverr,

    // SPI Flash Interface (to U99 W25Q128)
    output logic        spi_cs_n,
    output logic        spi_sclk,
    output logic        spi_mosi,
    input  logic        spi_miso,
    output logic        spi_wp_n,
    output logic        spi_hold_n,

    // Efinix CONFIG_CTRL0 Interface
    output logic        cfg_CONFIG,
    output logic [1:0]  cfg_CBSEL,
    output logic        cfg_ENA,
    input  logic        cfg_ERROR,
    input  logic        cfg_USR_STATUS
);

    assign pslverr = 1'b0;
    assign pready  = 1'b1; // Zero-wait-state APB register access

    // Registers
    logic [7:0]  rx_data;
    logic        cs_n_reg;
    logic        wp_n_reg;
    logic        hold_n_reg;
    logic [7:0]  clk_div_reg;
    logic [1:0]  cbsel_reg;
    logic        reconfig_trigger;
    logic [7:0]  reconfig_timer;

    assign spi_cs_n   = cs_n_reg;
    assign spi_wp_n   = wp_n_reg;
    assign spi_hold_n = hold_n_reg;
    assign cfg_CBSEL  = cbsel_reg;
    assign cfg_ENA    = 1'b1;

    // SPI Master State Machine
    typedef enum logic [1:0] {
        SPI_IDLE  = 2'b00,
        SPI_PHASE = 2'b01,
        SPI_DONE  = 2'b10
    } spi_state_t;

    spi_state_t  state;
    logic [7:0]  tx_shift;
    logic [7:0]  rx_shift;
    logic [2:0]  bit_cnt;
    logic [7:0]  clk_cnt;
    logic        sclk_int;

    assign spi_sclk = sclk_int;
    assign spi_mosi = tx_shift[7];
    logic  spi_busy;
    assign spi_busy = (state != SPI_IDLE);

    // APB3 Write & Reconfig Trigger
    wire reg_wr = psel & penable & pwrite;
    wire reg_rd = psel & !pwrite;

    always_ff @(posedge pclk or negedge presetn) begin
        if (!presetn) begin
            cs_n_reg         <= 1'b1; // De-asserted by default
            wp_n_reg         <= 1'b1; // High (not write protected)
            hold_n_reg       <= 1'b1; // High (not holding)
            clk_div_reg      <= DEFAULT_DIVIDER[7:0];
            cbsel_reg        <= 2'b00;
            reconfig_trigger <= 1'b0;
            reconfig_timer   <= 8'd0;
            cfg_CONFIG       <= 1'b0;
        end else begin
            // Reconfiguration pulse generator
            if (reconfig_trigger) begin
                cfg_CONFIG     <= 1'b1;
                reconfig_timer <= reconfig_timer + 1'b1;
                if (reconfig_timer == 8'd255) begin
                    reconfig_trigger <= 1'b0;
                    cfg_CONFIG       <= 1'b0;
                end
            end else begin
                cfg_CONFIG <= 1'b0;
            end

            if (reg_wr) begin
                case (paddr[7:0])
                    8'h04: begin // STATUS_CTRL
                        cs_n_reg    <= pwdata[1];
                        wp_n_reg    <= pwdata[2];
                        hold_n_reg  <= pwdata[3];
                        if (pwdata[15:8] != 8'd0)
                            clk_div_reg <= pwdata[15:8];
                    end
                    8'h08: begin // RECONFIG_CTRL
                        cbsel_reg <= pwdata[2:1];
                        if (pwdata[0]) begin
                            reconfig_trigger <= 1'b1;
                            reconfig_timer   <= 8'd0;
                        end
                    end
                    default: ;
                endcase
            end
        end
    end

    // APB3 Read Mux
    always_comb begin
        prdata = 32'd0;
        if (reg_rd) begin
            case (paddr[7:0])
                8'h00: prdata = {24'd0, rx_data};
                8'h04: prdata = {16'd0, clk_div_reg, 4'd0, hold_n_reg, wp_n_reg, cs_n_reg, spi_busy};
                8'h08: prdata = {27'd0, cfg_USR_STATUS, cfg_ERROR, cbsel_reg, reconfig_trigger};
                default: prdata = 32'd0;
            endcase
        end
    end

    // SPI Clock and Shift Logic (Mode 0: CPOL=0, CPHA=0)
    always_ff @(posedge pclk or negedge presetn) begin
        if (!presetn) begin
            state    <= SPI_IDLE;
            tx_shift <= 8'h00;
            rx_shift <= 8'h00;
            rx_data  <= 8'h00;
            bit_cnt  <= 3'd0;
            clk_cnt  <= 8'd0;
            sclk_int <= 1'b0;
        end else begin
            case (state)
                SPI_IDLE: begin
                    sclk_int <= 1'b0;
                    clk_cnt  <= 8'd0;
                    bit_cnt  <= 3'd7;
                    if (reg_wr && (paddr[7:0] == 8'h00)) begin
                        tx_shift <= pwdata[7:0];
                        state    <= SPI_PHASE;
                    end
                end

                SPI_PHASE: begin
                    if (clk_cnt == clk_div_reg) begin
                        clk_cnt <= 8'd0;
                        if (!sclk_int) begin
                            // Rising edge of sclk -> sample MISO
                            sclk_int <= 1'b1;
                            rx_shift <= {rx_shift[6:0], spi_miso};
                        end else begin
                            // Falling edge of sclk -> shift MOSI
                            sclk_int <= 1'b0;
                            if (bit_cnt == 3'd0) begin
                                state   <= SPI_DONE;
                            end else begin
                                bit_cnt  <= bit_cnt - 1'b1;
                                tx_shift <= {tx_shift[6:0], 1'b0};
                            end
                        end
                    end else begin
                        clk_cnt <= clk_cnt + 1'b1;
                    end
                end

                SPI_DONE: begin
                    rx_data  <= rx_shift;
                    sclk_int <= 1'b0;
                    state    <= SPI_IDLE;
                end
            endcase
        end
    end

endmodule
