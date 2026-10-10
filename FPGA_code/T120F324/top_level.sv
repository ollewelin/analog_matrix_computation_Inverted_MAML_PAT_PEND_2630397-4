module top_level
(
  (* syn_peri_port = 0 *) input F2_RXCTL,
  (* syn_peri_port = 0 *) input F2_RXD0,
  (* syn_peri_port = 0 *) input F2_RXD1,
  (* syn_peri_port = 0 *) input F2_RXD2,
  (* syn_peri_port = 0 *) input F2_RXD3,
  (* syn_peri_port = 0 *) input OUT1_ADC_45,
  (* syn_peri_port = 0 *) input OUT2_ADC_45,
  (* syn_peri_port = 0 *) input OUT3_ADC_45,
  (* syn_peri_port = 0 *) input OUT4_ADC_45,
  (* syn_peri_port = 0 *) input pll_inst1_LOCKED,
  (* syn_peri_port = 0 *) input RCK_DAC_W_34,
  (* syn_peri_port = 0 *) input SCK_DAC7_W_34,
  (* syn_peri_port = 0 *) input SCK_DAC8_W_34,
  (* syn_peri_port = 0 *) input SI_DAC2_DAC_2,
  (* syn_peri_port = 0 *) input SI_DAC5_DAC_2,
  (* syn_peri_port = 0 *) input SI_DAC8_W_34,
  (* syn_peri_port = 0 *) input F2_INTB,
  (* syn_peri_port = 0 *) input F2_MDIO_IN,
  (* syn_peri_port = 0 *) input OUT1_ADC_49,
  (* syn_peri_port = 0 *) input OUT2_ADC_49,
  (* syn_peri_port = 0 *) input OUT3_ADC_49,
  (* syn_peri_port = 0 *) input OUT4_ADC_49,
  (* syn_peri_port = 0 *) input OUT5_ADC_45,
  (* syn_peri_port = 0 *) input OUT5_ADC_49,
  (* syn_peri_port = 0 *) input OUT6_ADC_45,
  (* syn_peri_port = 0 *) input OUT6_ADC_49,
  (* syn_peri_port = 0 *) input RX00_T20_N1,
  (* syn_peri_port = 0 *) input RX00_T20_P1,
  (* syn_peri_port = 0 *) input RX01_T20_N1,
  (* syn_peri_port = 0 *) input RX01_T20_P1,
  (* syn_peri_port = 0 *) input RX02_T20_N1,
  (* syn_peri_port = 0 *) input RX02_T20_P1,
  (* syn_peri_port = 0 *) input RX03_T20_N1,
  (* syn_peri_port = 0 *) input RX03_T20_P1,
  (* syn_peri_port = 0 *) input T120_GCLK,
  (* syn_peri_port = 0 *) input F2_RXC,
  (* syn_peri_port = 0 *) input PLL_125MHZ,
  (* syn_peri_port = 0 *) input pll_clk_25Mhz_ext,
  (* syn_peri_port = 0 *) input PLL_125MHZ_90DEG,
  (* syn_peri_port = 0 *) input pll_clk_80Mhz,
  (* syn_peri_port = 0 *) input pll_clk_50Mhz,
  (* syn_peri_port = 0 *) input jtag_inst1_CAPTURE,
  (* syn_peri_port = 0 *) input jtag_inst1_DRCK,
  (* syn_peri_port = 0 *) input jtag_inst1_RESET,
  (* syn_peri_port = 0 *) input jtag_inst1_RUNTEST,
  (* syn_peri_port = 0 *) input jtag_inst1_SEL,
  (* syn_peri_port = 0 *) input jtag_inst1_SHIFT,
  (* syn_peri_port = 0 *) input jtag_inst1_TCK,
  (* syn_peri_port = 0 *) input jtag_inst1_TDI,
  (* syn_peri_port = 0 *) input jtag_inst1_TMS,
  (* syn_peri_port = 0 *) input jtag_inst1_UPDATE,
  (* syn_peri_port = 0 *) output F2_TXC,
  (* syn_peri_port = 0 *) output F2_TXCTL,
  (* syn_peri_port = 0 *) output F2_TXD0,
  (* syn_peri_port = 0 *) output F2_TXD1,
  (* syn_peri_port = 0 *) output F2_TXD2,
  (* syn_peri_port = 0 *) output F2_TXD3,
  (* syn_peri_port = 0 *) output RCK_DAC_W_12,
  (* syn_peri_port = 0 *) output SCK_DAC2_W_34,
  (* syn_peri_port = 0 *) output SCLR_DAC_W_12,
  (* syn_peri_port = 0 *) output SI_DAC1_W_15,
  (* syn_peri_port = 0 *) output SI_DAC2_W_15,
  (* syn_peri_port = 0 *) output SI_DAC2_W_34,
  (* syn_peri_port = 0 *) output SI_DAC4_W_15,
  (* syn_peri_port = 0 *) output SI_DAC6_W_15,
  (* syn_peri_port = 0 *) output SI_DAC7_W_15,
  (* syn_peri_port = 0 *) output T120_LED1,
  (* syn_peri_port = 0 *) output T20_CLK9,
  (* syn_peri_port = 0 *) output RCK_DAC_2,
  (* syn_peri_port = 0 *) output RCK_DAC_W_15,
  (* syn_peri_port = 0 *) output SCK_DAC1_DAC_2,
  (* syn_peri_port = 0 *) output SCK_DAC1_W_12,
  (* syn_peri_port = 0 *) output SCK_DAC1_W_34,
  (* syn_peri_port = 0 *) output SCK_DAC2_DAC_2,
  (* syn_peri_port = 0 *) output SCK_DAC2_W_12,
  (* syn_peri_port = 0 *) output SCK_DAC2_W_15,
  (* syn_peri_port = 0 *) output SCK_DAC3_DAC_2,
  (* syn_peri_port = 0 *) output SCK_DAC3_W_12,
  (* syn_peri_port = 0 *) output SCK_DAC3_W_15,
  (* syn_peri_port = 0 *) output SCK_DAC3_W_34,
  (* syn_peri_port = 0 *) output SCK_DAC4_DAC_2,
  (* syn_peri_port = 0 *) output SCK_DAC4_W_12,
  (* syn_peri_port = 0 *) output SCK_DAC4_W_15,
  (* syn_peri_port = 0 *) output SCK_DAC4_W_34,
  (* syn_peri_port = 0 *) output SCK_DAC5_DAC_2,
  (* syn_peri_port = 0 *) output SCK_DAC5_W_12,
  (* syn_peri_port = 0 *) output SCK_DAC5_W_15,
  (* syn_peri_port = 0 *) output SCK_DAC5_W_34,
  (* syn_peri_port = 0 *) output SCK_DAC6_DAC_2,
  (* syn_peri_port = 0 *) output SCK_DAC6_W_12,
  (* syn_peri_port = 0 *) output SCK_DAC6_W_15,
  (* syn_peri_port = 0 *) output SCK_DAC6_W_34,
  (* syn_peri_port = 0 *) output SCK_DAC7_W_15,
  (* syn_peri_port = 0 *) output SCK_DAC8_W_15,
  (* syn_peri_port = 0 *) output SCLR_DAC_2,
  (* syn_peri_port = 0 *) output SCLR_DAC_W_15,
  (* syn_peri_port = 0 *) output SI_DAC1_DAC_2,
  (* syn_peri_port = 0 *) output SI_DAC1_W_34,
  (* syn_peri_port = 0 *) output SI_DAC3_DAC_2,
  (* syn_peri_port = 0 *) output SI_DAC3_W_15,
  (* syn_peri_port = 0 *) output SI_DAC3_W_34,
  (* syn_peri_port = 0 *) output SI_DAC4_DAC_2,
  (* syn_peri_port = 0 *) output SI_DAC4_W_34,
  (* syn_peri_port = 0 *) output SI_DAC5_W_15,
  (* syn_peri_port = 0 *) output SI_DAC5_W_34,
  (* syn_peri_port = 0 *) output SI_DAC6_DAC_2,
  (* syn_peri_port = 0 *) output SI_DAC6_W_34,
  (* syn_peri_port = 0 *) output SI_DAC7_W_34,
  (* syn_peri_port = 0 *) output T120_LED2,
  (* syn_peri_port = 0 *) output TX11_T20_N1,
  (* syn_peri_port = 0 *) output TX11_T20_P1,
  (* syn_peri_port = 0 *) output TX12_T20_N1,
  (* syn_peri_port = 0 *) output TX12_T20_P1,
  (* syn_peri_port = 0 *) output ADC_45_CONV,
  (* syn_peri_port = 0 *) output ADC_45_SCK_1_2,
  (* syn_peri_port = 0 *) output ADC_45_SCK_3_4,
  (* syn_peri_port = 0 *) output ADC_45_SCK_5_6,
  (* syn_peri_port = 0 *) output ADC_49_CONV,
  (* syn_peri_port = 0 *) output ADC_49_SCK_1_2,
  (* syn_peri_port = 0 *) output ADC_49_SCK_3_4,
  (* syn_peri_port = 0 *) output ADC_49_SCK_5_6,
  (* syn_peri_port = 0 *) output F2_MDC,
  (* syn_peri_port = 0 *) output F2_RSTB,
  (* syn_peri_port = 0 *) output SCK_DAC1_W_15,
  (* syn_peri_port = 0 *) output SCK_DAC7_W_12,
  (* syn_peri_port = 0 *) output SCK_DAC8_W_12,
  (* syn_peri_port = 0 *) output SI_DAC1_W_12,
  (* syn_peri_port = 0 *) output SI_DAC2_W_12,
  (* syn_peri_port = 0 *) output SI_DAC3_W_12,
  (* syn_peri_port = 0 *) output SI_DAC4_W_12,
  (* syn_peri_port = 0 *) output SI_DAC5_W_12,
  (* syn_peri_port = 0 *) output SI_DAC6_W_12,
  (* syn_peri_port = 0 *) output SI_DAC7_W_12,
  (* syn_peri_port = 0 *) output SI_DAC8_W_12,
  (* syn_peri_port = 0 *) output SI_DAC8_W_15,
  (* syn_peri_port = 0 *) output jtag_inst1_TDO,
  (* syn_peri_port = 0 *) output F2_MDIO_OUT,
  (* syn_peri_port = 0 *) output F2_MDIO_OE,
  (* syn_peri_port = 0 *) output SCLR_DAC_W_34
);


    // =========================================================================
    // System Clocks and Resets
    // =========================================================================
    // The CPU/APB domain uses the board's constrained 50 MHz oscillator.
    wire sys_clk   = T120_GCLK;

    wire sys_rst_n;
    wire sys_rst_n_inv = ~sys_rst_n;

    // Power-on reset till SoC (som i referensen): håll io_asyncReset aktiv ~84 ms efter konfiguration.
    logic [22:0] por_cnt = '0;
    always_ff @(posedge T120_GCLK) begin
        if (!por_cnt[22]) por_cnt <= por_cnt + 1'b1;
    end
    wire soc_async_reset = ~por_cnt[22];

    // =========================================================================
    // APB3 Interconnect Signals from Sapphire SoC
    // =========================================================================
    wire [15:0] apb_paddr;
    wire        apb_psel;
    wire        apb_penable;
    wire        apb_pwrite;
    wire [31:0] apb_pwdata;
    logic [31:0] apb_prdata;
    logic       apb_pready;
    wire        apb_pslverr;

    // =========================================================================
    // Sapphire RISC-V SoC (RISC_mini)
    // =========================================================================
    wire sapphire_uart_txd;
    wire sapphire_uart_rxd = 1'b1;

    wire [3:0] gpio_out;
    wire [3:0] gpio_oe;

    RISC_mini u_sapphire_soc (
        .io_systemClk               (sys_clk),
        .io_systemReset             (sys_rst_n),
        .io_asyncReset              (soc_async_reset),

        .io_apbSlave_0_PADDR        (apb_paddr),
        .io_apbSlave_0_PSEL         (apb_psel),
        .io_apbSlave_0_PENABLE      (apb_penable),
        .io_apbSlave_0_PWRITE       (apb_pwrite),
        .io_apbSlave_0_PWDATA       (apb_pwdata),
        .io_apbSlave_0_PRDATA       (apb_prdata),
        .io_apbSlave_0_PREADY       (apb_pready),
        .io_apbSlave_0_PSLVERROR    (apb_pslverr),

        .system_uart_0_io_txd       (sapphire_uart_txd),
        .system_uart_0_io_rxd       (sapphire_uart_rxd),

        .system_i2c_0_io_scl_read   (1'b1),
        .system_i2c_0_io_scl_write  (),
        .system_i2c_0_io_sda_read   (1'b1),
        .system_i2c_0_io_sda_write  (),

        .system_gpio_0_io_writeEnable (gpio_oe),
        .system_gpio_0_io_write     (gpio_out),
        .system_gpio_0_io_read      (4'b0000),

        .system_spi_0_io_data_0_read(1'b0),
        .system_spi_0_io_data_0_write(),
        .system_spi_0_io_data_0_writeEnable(),
        .system_spi_0_io_data_1_read(1'b0),
        .system_spi_0_io_data_1_write(),
        .system_spi_0_io_data_1_writeEnable(),
        .system_spi_0_io_data_2_read(1'b0),
        .system_spi_0_io_data_2_write(),
        .system_spi_0_io_data_2_writeEnable(),
        .system_spi_0_io_data_3_read(1'b0),
        .system_spi_0_io_data_3_write(),
        .system_spi_0_io_data_3_writeEnable(),
        .system_spi_0_io_sclk_write (),
        .system_spi_0_io_ss         (),

        .system_spi_1_io_data_0_read(1'b0),
        .system_spi_1_io_data_0_write(),
        .system_spi_1_io_data_0_writeEnable(),
        .system_spi_1_io_data_1_read(1'b0),
        .system_spi_1_io_data_1_write(),
        .system_spi_1_io_data_1_writeEnable(),
        .system_spi_1_io_data_2_read(1'b0),
        .system_spi_1_io_data_2_write(),
        .system_spi_1_io_data_2_writeEnable(),
        .system_spi_1_io_data_3_read(1'b0),
        .system_spi_1_io_data_3_write(),
        .system_spi_1_io_data_3_writeEnable(),
        .system_spi_1_io_sclk_write (),
        .system_spi_1_io_ss         (),

        .userInterruptA             (1'b0),

        .jtagCtrl_enable            (jtag_inst1_SEL),
        .jtagCtrl_tdi               (jtag_inst1_TDI),
        .jtagCtrl_capture           (jtag_inst1_CAPTURE),
        .jtagCtrl_shift             (jtag_inst1_SHIFT),
        .jtagCtrl_update            (jtag_inst1_UPDATE),
        .jtagCtrl_reset             (jtag_inst1_RESET),
        .jtagCtrl_tck               (jtag_inst1_TCK),
        .jtagCtrl_tdo               (jtag_inst1_TDO)
    );

    // SCLR_DAC_W_34 tied to 1'b0 (DAC pin restored/disconnected from UART)
    assign SCLR_DAC_W_34 = 1'b0;

    // =========================================================================
    // APB3 Address Decoder
    // Base 0xF810_1000..0xF810_1FFF -> MDIO master
    // Base 0xF810_2000..0xF810_2FFF -> 100-Mbit Ethernet MAC and packet RAM
    // Base 0xF810_3000..0xF810_3FFF -> T120 <-> T20 Custom Bus
    // =========================================================================
    wire mdio_selected    = (apb_paddr[15:12] == 4'h1);
    wire eth_selected     = (apb_paddr[15:12] == 4'h2);
    wire t20_bus_selected = (apb_paddr[15:12] == 4'h3);

    // =========================================================================
    // Reference design's APB MDIO master and 100-Mbit MAC
    // =========================================================================
    wire [31:0] mdio_apb_prdata;
    wire        mdio_apb_pready;
    mdio_master #(
        .SYS_CLK_HZ(50_000_000),
        .MDC_HZ(1_000_000)
    ) u_mdio_master (
        .clk      (sys_clk),
        .rst_n    (sys_rst_n_inv),
        .psel     (apb_psel & mdio_selected),
        .penable  (apb_penable),
        .pwrite   (apb_pwrite),
        .paddr    ({2'b00, apb_paddr[3:2]}),
        .pwdata   (apb_pwdata),
        .prdata   (mdio_apb_prdata),
        .pready   (mdio_apb_pready),
        .pslverr  (),
        .mdc      (F2_MDC),
        .mdio_i   (F2_MDIO_IN),
        .mdio_o   (F2_MDIO_OUT),
        .mdio_oe  (F2_MDIO_OE),
        .phy_rst_n(),
        .irq      ()
    );

    wire [31:0] eth_apb_prdata;
    wire        eth_apb_pready;
    wire [3:0]  eth_txd;
    wire        eth_txctl;
    wire        eth_txc;

    // Dedicated Hardware Power-On-Reset for RTL8211F PHY (100 ms active-low pulse after config)
    // PLUS software controllable reset via SoC GPIO bit 1 (0 = reset asserted, 1 = normal operation).
    logic [23:0] phy_por_cnt = '0;
    always_ff @(posedge sys_clk) begin
        if (!phy_por_cnt[23]) phy_por_cnt <= phy_por_cnt + 1'b1;
    end
    wire phy_hw_rstn = phy_por_cnt[23] & gpio_out[1];
    assign F2_RSTB   = phy_hw_rstn;

    eth_mac_100m u_eth_mac_100m (
        .sys_clk       (sys_clk),
        .sys_rst_n     (sys_rst_n_inv),
        .apb_paddr     (apb_paddr[11:0]),
        .apb_psel      (apb_psel & eth_selected),
        .apb_penable   (apb_penable),
        .apb_pwrite    (apb_pwrite),
        .apb_pwdata    (apb_pwdata),
        .apb_prdata    (eth_apb_prdata),
        .apb_pready    (eth_apb_pready),
        .apb_pslverr   (),
        .rgmii_tx_clk  (pll_clk_25Mhz_ext),
        .rgmii_txc     (eth_txc),
        .rgmii_txctl   (eth_txctl),
        .rgmii_txd     (eth_txd),
        .rgmii_rxc     (F2_RXC),
        .rgmii_rxctl   (F2_RXCTL),
        .rgmii_rxd     ({F2_RXD3, F2_RXD2, F2_RXD1, F2_RXD0}),
        .phy_link_up   (1'b1),
        .activity_led  ()
    );
    assign F2_TXC   = eth_txc;
    assign F2_TXCTL = eth_txctl;
    assign F2_TXD0  = eth_txd[0];
    assign F2_TXD1  = eth_txd[1];
    assign F2_TXD2  = eth_txd[2];
    assign F2_TXD3  = eth_txd[3];

    // =========================================================================
    // T120 <-> T20 Custom Inter-FPGA Bus APB3 Slave (0xF810_3000)
    // =========================================================================
    wire [31:0] t20_bus_prdata;
    wire        t20_bus_pready;
    wire [3:0]  t20_tx_wires;
    wire [7:0]  t20_rx_wires = {RX03_T20_N1, RX03_T20_P1, RX02_T20_N1, RX02_T20_P1,
                                RX01_T20_N1, RX01_T20_P1, RX00_T20_N1, RX00_T20_P1};
    wire        t20_creset_n;

    // H-bus: TX11_P = H_SYNC, TX11_N = H_DATA (hardware-synchronous Hadamard)
    // S-bus: TX12_P/N = 2-bit service TX (C-code driven)
    assign TX11_T20_P1 = t20_tx_wires[0];
    assign TX11_T20_N1 = t20_tx_wires[1];
    assign TX12_T20_P1 = t20_tx_wires[2];
    assign TX12_T20_N1 = t20_tx_wires[3];

    t120_inter_fpga_bridge #(.H_WIDTH(16)) u_t20_bridge (
        .pclk           (sys_clk),
        .presetn        (sys_rst_n_inv),
        .psel           (apb_psel & t20_bus_selected),
        .penable        (apb_penable),
        .pwrite         (apb_pwrite),
        .paddr          (apb_paddr[11:0]),
        .pwdata         (apb_pwdata),
        .prdata         (t20_bus_prdata),
        .pready         (t20_bus_pready),
        .pslverr        (),

        .t20_clk9       (T20_CLK9),
        .t20_tx         (t20_tx_wires),
        .t20_rx         (t20_rx_wires),
        .t20_creset_n   (t20_creset_n),

        .irq            (),
        .h_step_strobe  (),
        .h_active       ()
    );

    // =========================================================================
    // APB3 Read Multiplexing
    // =========================================================================
    always_comb begin
        if (mdio_selected) begin
            apb_prdata = mdio_apb_prdata;
            apb_pready = mdio_apb_pready;
        end else if (eth_selected) begin
            apb_prdata = eth_apb_prdata;
            apb_pready = eth_apb_pready;
        end else if (t20_bus_selected) begin
            apb_prdata = t20_bus_prdata;
            apb_pready = t20_bus_pready;
        end else begin
            apb_prdata = 32'h0;
            apb_pready = 1'b1;
        end
    end

    // =========================================================================
    // Status LEDs:
    // LED1 pin is the patch wire to T20 CRESET_N (heartbeat removed)
    assign T120_LED1 = t20_creset_n;
    // LED2 pin is now UART TX (moved from DAC pin F13 to LED2)
    assign T120_LED2 = sapphire_uart_txd;

    // Tied off unused analog pins safely to ground/default
    assign ADC_45_CONV    = 1'b0;
    assign ADC_45_SCK_1_2 = 1'b0;
    assign ADC_45_SCK_3_4 = 1'b0;
    assign ADC_45_SCK_5_6 = 1'b0;
    assign ADC_49_CONV    = 1'b0;
    assign ADC_49_SCK_1_2 = 1'b0;
    assign ADC_49_SCK_3_4 = 1'b0;
    assign ADC_49_SCK_5_6 = 1'b0;

    assign RCK_DAC_W_12   = 1'b0;
    assign SCK_DAC2_W_34  = 1'b0;
    assign SCLR_DAC_W_12  = 1'b1;
    assign SI_DAC1_W_15   = 1'b0;
    assign SI_DAC2_W_15   = 1'b0;
    assign SI_DAC2_W_34   = 1'b0;
    assign SI_DAC4_W_15   = 1'b0;
    assign SI_DAC6_W_15   = 1'b0;
    assign SI_DAC7_W_15   = 1'b0;

    assign RCK_DAC_2      = 1'b0;
    assign RCK_DAC_W_15   = 1'b0;
    assign SCK_DAC1_DAC_2 = 1'b0;
    assign SCK_DAC1_W_12  = 1'b0;
    assign SCK_DAC1_W_34  = 1'b0;
    assign SCK_DAC2_DAC_2 = 1'b0;
    assign SCK_DAC2_W_12  = 1'b0;
    assign SCK_DAC2_W_15  = 1'b0;
    assign SCK_DAC3_DAC_2 = 1'b0;
    assign SCK_DAC3_W_12  = 1'b0;
    assign SCK_DAC3_W_15  = 1'b0;
    assign SCK_DAC3_W_34  = 1'b0;
    assign SCK_DAC4_DAC_2 = 1'b0;
    assign SCK_DAC4_W_12  = 1'b0;
    assign SCK_DAC4_W_15  = 1'b0;
    assign SCK_DAC4_W_34  = 1'b0;
    assign SCK_DAC5_DAC_2 = 1'b0;
    assign SCK_DAC5_W_12  = 1'b0;
    assign SCK_DAC5_W_15  = 1'b0;
    assign SCK_DAC5_W_34  = 1'b0;
    assign SCK_DAC6_DAC_2 = 1'b0;
    assign SCK_DAC6_W_12  = 1'b0;
    assign SCK_DAC6_W_15  = 1'b0;
    assign SCK_DAC6_W_34  = 1'b0;
    assign SCK_DAC7_W_15  = 1'b0;
    assign SCK_DAC8_W_15  = 1'b0;
    assign SCLR_DAC_2     = 1'b1;
    assign SCLR_DAC_W_15  = 1'b1;
    assign SI_DAC1_DAC_2  = 1'b0;
    assign SI_DAC1_W_34   = 1'b0;
    assign SI_DAC3_DAC_2  = 1'b0;
    assign SI_DAC3_W_15   = 1'b0;
    assign SI_DAC3_W_34   = 1'b0;
    assign SI_DAC4_DAC_2  = 1'b0;
    assign SI_DAC4_W_34   = 1'b0;
    assign SI_DAC5_W_15   = 1'b0;
    assign SI_DAC5_W_34   = 1'b0;
    assign SI_DAC6_DAC_2  = 1'b0;
    assign SI_DAC6_W_34   = 1'b0;
    assign SI_DAC7_W_34   = 1'b0;

    assign SCK_DAC1_W_15  = 1'b0;
    assign SCK_DAC7_W_12  = 1'b0;
    assign SCK_DAC8_W_12  = 1'b0;
    assign SI_DAC1_W_12   = 1'b0;
    assign SI_DAC2_W_12   = 1'b0;
    assign SI_DAC3_W_12   = 1'b0;
    assign SI_DAC4_W_12   = 1'b0;
    assign SI_DAC5_W_12   = 1'b0;
    assign SI_DAC6_W_12   = 1'b0;
    assign SI_DAC7_W_12   = 1'b0;
    assign SI_DAC8_W_12   = 1'b0;
    assign SI_DAC8_W_15   = 1'b0;

endmodule
