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
  (* syn_peri_port = 0 *) output F2_TXC_HI,
  (* syn_peri_port = 0 *) output F2_TXC_LO,
  (* syn_peri_port = 0 *) output F2_TXCTL,
  (* syn_peri_port = 0 *) output F2_TXD0_HI,
  (* syn_peri_port = 0 *) output F2_TXD0_LO,
  (* syn_peri_port = 0 *) output F2_TXD1_HI,
  (* syn_peri_port = 0 *) output F2_TXD1_LO,
  (* syn_peri_port = 0 *) output F2_TXD2_HI,
  (* syn_peri_port = 0 *) output F2_TXD2_LO,
  (* syn_peri_port = 0 *) output F2_TXD3_HI,
  (* syn_peri_port = 0 *) output F2_TXD3_LO,
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
    // SoC-klocka direkt från extern 50 MHz-oscillator (som i fungerande referens).
    // pll_clk_50Mhz saknar SDC-constraint -> SoC:ens timing var helt okontrollerad.
    wire sys_clk   = T120_GCLK;

    // Hardware Heartbeat for LED1 (2 Hz toggle from 50 MHz clock)
    logic [24:0] led1_counter = '0;
    logic        led1_hw_toggle = 1'b0;
    always_ff @(posedge sys_clk) begin
        if (led1_counter == 25'd12_500_000 - 1) begin
            led1_counter   <= '0;
            led1_hw_toggle <= ~led1_hw_toggle;
        end else begin
            led1_counter <= led1_counter + 1'b1;
        end
    end

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

    // Slave Selects:
    // 0x0000 - 0x0FFF : UART Mini (Base 0xF810_0000)
    // 0x1000 - 0x1FFF : MDIO Master (Base 0xF810_1000)
    // 0x2000 - 0x2FFF : Ethernet MAC (Base 0xF810_2000)
    // 0x3000 - 0x3FFF : T120 <-> T20 Bus Peripheral (Base 0xF810_3000)
    wire uart_mini_selected = (apb_paddr[15:12] == 4'h0);
    wire mdio_selected      = (apb_paddr[15:12] == 4'h1);
    wire eth_selected       = (apb_paddr[15:12] == 4'h2);
    wire t20_bus_selected   = (apb_paddr[15:12] == 4'h3);

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

    // Hardware UART on dedicated board pin SCLR_DAC_W_34
    assign SCLR_DAC_W_34 = sapphire_uart_txd;

    // =========================================================================
    // APB3 Address Decoder
    // Base 0xF810_0000..0xF810_0FFF -> TSE MAC Configuration & MDIO Registers
    // Base 0xF810_2000..0xF810_2FFF -> TSE MAC Packet Buffer FIFO (TX/RX RAM)
    // Base 0xF810_3000..0xF810_3FFF -> T120 <-> T20 Custom Bus
    // =========================================================================
    wire mac_selected     = (apb_paddr[15:12] == 4'h0);
    wire pkt_fifo_selected= (apb_paddr[15:12] == 4'h2);
    wire t20_bus_selected = (apb_paddr[15:12] == 4'h3);

    // =========================================================================
    // APB3 to AXI4-Lite Bridge (for standard Efinix TSE MAC core)
    // =========================================================================
    wire [9:0]  axi_awaddr;
    wire        axi_awvalid, axi_awready;
    wire [31:0] axi_wdata;
    wire        axi_wvalid,  axi_wready;
    wire [1:0]  axi_bresp;
    wire        axi_bvalid,  axi_bready;
    wire [9:0]  axi_araddr;
    wire        axi_arvalid, axi_arready;
    wire [1:0]  axi_rresp;
    wire [31:0] axi_rdata;
    wire        axi_rvalid,  axi_rready;

    wire [31:0] mac_apb_prdata;
    wire        mac_apb_pready;
    wire        mac_apb_pslverr;

    apb3_2_axi4_lite #(
        .ADDR_WTH (10)
    ) u_apb3_2_axi4_lite (
        .clk              (sys_clk),
        .rstn             (sys_rst_n_inv),
        .s_apb3_paddr     (apb_paddr[9:0]),
        .s_apb3_psel      (apb_psel & mac_selected),
        .s_apb3_penable   (apb_penable),
        .s_apb3_pready    (mac_apb_pready),
        .s_apb3_pwrite    (apb_pwrite),
        .s_apb3_pwdata    (apb_pwdata),
        .s_apb3_prdata    (mac_apb_prdata),
        .s_apb3_pslverror (mac_apb_pslverr),

        .m_axi_awaddr     (axi_awaddr),
        .m_axi_awvalid    (axi_awvalid),
        .m_axi_awready    (axi_awready),
        .m_axi_wdata      (axi_wdata),
        .m_axi_wvalid     (axi_wvalid),
        .m_axi_wready     (axi_wready),
        .m_axi_bresp      (axi_bresp),
        .m_axi_bvalid     (axi_bvalid),
        .m_axi_bready     (axi_bready),
        .m_axi_araddr     (axi_araddr),
        .m_axi_arvalid    (axi_arvalid),
        .m_axi_arready    (axi_arready),
        .m_axi_rresp      (axi_rresp),
        .m_axi_rdata      (axi_rdata),
        .m_axi_rvalid     (axi_rvalid),
        .m_axi_rready     (axi_rready)
    );

    // =========================================================================
    // Standard Efinix Triple-Speed Ethernet MAC (RGMII + Hardware MDIO)
    // =========================================================================
    wire [3:0] rgmii_txd_HI, rgmii_txd_LO;
    wire       rgmii_tx_ctl_HI, rgmii_tx_ctl_LO;
    wire       rgmii_txc_HI, rgmii_txc_LO;
    wire [3:0] rgmii_rxd_HI, rgmii_rxd_LO;
    wire       rgmii_rx_ctl_HI, rgmii_rx_ctl_LO;

    // Trion T120 Board RGMII Control Workaround (Efinix User Guide page 26 & temac_ex.v)
    assign F2_TXCTL       = rgmii_tx_ctl_HI | rgmii_tx_ctl_LO;
    assign rgmii_rx_ctl_HI = F2_RXCTL;
    assign rgmii_rx_ctl_LO = F2_RXCTL;

    // RGMII Clock forward to PHY: generated by the MAC (25 MHz in 100M mode, divided from the
    // 125 MHz tx_mac_aclk) and driven through a DDIO pad clocked by the 90-degree shifted 125 MHz clock
    // so that TXC is centre-aligned to TXD/TXCTL (UG "RGMII Transmit Clock Delay").
    assign F2_TXC_HI      = rgmii_txc_HI;
    assign F2_TXC_LO      = rgmii_txc_LO;

    // RGMII Data bus to physical DDIO pins (HI/LO are identical in 100M mode)
    assign F2_TXD0_HI     = rgmii_txd_HI[0];
    assign F2_TXD1_HI     = rgmii_txd_HI[1];
    assign F2_TXD2_HI     = rgmii_txd_HI[2];
    assign F2_TXD3_HI     = rgmii_txd_HI[3];
    assign F2_TXD0_LO     = rgmii_txd_LO[0];
    assign F2_TXD1_LO     = rgmii_txd_LO[1];
    assign F2_TXD2_LO     = rgmii_txd_LO[2];
    assign F2_TXD3_LO     = rgmii_txd_LO[3];

    assign rgmii_rxd_HI   = {F2_RXD3, F2_RXD2, F2_RXD1, F2_RXD0};
    assign rgmii_rxd_LO   = {F2_RXD3, F2_RXD2, F2_RXD1, F2_RXD0};

    // Hardware MDIO Pins
    wire phy_mdo, phy_mdo_en;
    assign F2_MDIO_OUT = phy_mdo;
    assign F2_MDIO_OE  = phy_mdo_en;

    // Dedicated Hardware Power-On-Reset for RTL8211F PHY (100 ms active-low pulse after config)
    // PLUS software controllable reset via SoC GPIO bit 1 (0 = reset asserted, 1 = normal operation).
    logic [23:0] phy_por_cnt = '0;
    always_ff @(posedge sys_clk) begin
        if (!phy_por_cnt[23]) phy_por_cnt <= phy_por_cnt + 1'b1;
    end
    wire phy_hw_rstn = phy_por_cnt[23] & gpio_out[1];
    assign F2_RSTB   = phy_hw_rstn;

    // AXI-Stream Packet Interface
    wire [7:0] rx_axis_mac_tdata, tx_axis_mac_tdata;
    wire       rx_axis_mac_tvalid, tx_axis_mac_tvalid;
    wire       rx_axis_mac_tlast,  tx_axis_mac_tlast;
    wire       rx_axis_mac_tuser,  tx_axis_mac_tuser;
    wire       rx_axis_mac_tready, tx_axis_mac_tready;

    rgmii_eth_efx_tsemac u_tsemac (
        .mac_reset          (~sys_rst_n_inv),
        .proto_reset        (1'b0),
        .tx_mac_aclk        (PLL_125MHZ),     // 125 MHz reference clock (required in all speeds, 100M TXC = /5)
        .rx_mac_aclk        (),
        .eth_speed          (),

        // AXI4-Stream RX Interface
        .rx_axis_clk        (sys_clk),
        .rx_axis_mac_tdata  (rx_axis_mac_tdata),
        .rx_axis_mac_tvalid (rx_axis_mac_tvalid),
        .rx_axis_mac_tlast  (rx_axis_mac_tlast),
        .rx_axis_mac_tstrb  (),
        .rx_axis_mac_tuser  (rx_axis_mac_tuser),
        .rx_axis_mac_tready (rx_axis_mac_tready),

        // AXI4-Stream TX Interface
        .tx_axis_clk        (sys_clk),
        .tx_axis_mac_tdata  (tx_axis_mac_tdata),
        .tx_axis_mac_tvalid (tx_axis_mac_tvalid),
        .tx_axis_mac_tlast  (tx_axis_mac_tlast),
        .tx_axis_mac_tstrb  (1'b1),
        .tx_axis_mac_tuser  (tx_axis_mac_tuser),
        .tx_axis_mac_tready (tx_axis_mac_tready),

        // RGMII PHY Interface
        .rgmii_txd_HI       (rgmii_txd_HI),
        .rgmii_txd_LO       (rgmii_txd_LO),
        .rgmii_tx_ctl_HI    (rgmii_tx_ctl_HI),
        .rgmii_tx_ctl_LO    (rgmii_tx_ctl_LO),
        .rgmii_txc_HI       (rgmii_txc_HI),
        .rgmii_txc_LO       (rgmii_txc_LO),
        .rgmii_rxd_HI       (rgmii_rxd_HI),
        .rgmii_rxd_LO       (rgmii_rxd_LO),
        .rgmii_rx_ctl_HI    (rgmii_rx_ctl_HI),
        .rgmii_rx_ctl_LO    (rgmii_rx_ctl_LO),
        .rgmii_rxc          (F2_RXC),

        // AXI4-Lite Register Interface
        .s_axi_aclk         (sys_clk),
        .s_axi_awaddr       (axi_awaddr),
        .s_axi_awvalid      (axi_awvalid),
        .s_axi_awready      (axi_awready),
        .s_axi_wdata        (axi_wdata),
        .s_axi_wvalid       (axi_wvalid),
        .s_axi_wready       (axi_wready),
        .s_axi_bresp        (axi_bresp),
        .s_axi_bvalid       (axi_bvalid),
        .s_axi_bready       (axi_bready),
        .s_axi_araddr       (axi_araddr),
        .s_axi_arvalid      (axi_arvalid),
        .s_axi_arready      (axi_arready),
        .s_axi_rresp        (axi_rresp),
        .s_axi_rdata        (axi_rdata),
        .s_axi_rvalid       (axi_rvalid),
        .s_axi_rready       (axi_rready),

        // Integrated Hardware MDIO Interface
        .Mdo                (phy_mdo),
        .MdoEn              (phy_mdo_en),
        .Mdi                (F2_MDIO_IN),
        .Mdc                (F2_MDC)
    );

    // =========================================================================
    // TSE MAC Packet Buffer FIFO (APB3 Base 0xF810_2000)
    // Connects TSE MAC AXI4-Stream to Sapphire SoC APB3 bus
    // =========================================================================
    wire [31:0] pkt_fifo_prdata;
    wire        pkt_fifo_pready;

    tsemac_axis_packet_fifo u_pkt_fifo (
        .clk           (sys_clk),
        .rstn          (sys_rst_n_inv),

        // APB3 Slave Interface
        .apb_paddr     (apb_paddr[11:0]),
        .apb_psel      (apb_psel & pkt_fifo_selected),
        .apb_penable   (apb_penable),
        .apb_pwrite    (apb_pwrite),
        .apb_pwdata    (apb_pwdata),
        .apb_prdata    (pkt_fifo_prdata),
        .apb_pready    (pkt_fifo_pready),
        .apb_pslverr   (),

        // RX from TSE MAC
        .rx_axis_tdata (rx_axis_mac_tdata),
        .rx_axis_tvalid(rx_axis_mac_tvalid),
        .rx_axis_tlast (rx_axis_mac_tlast),
        .rx_axis_tuser (rx_axis_mac_tuser),
        .rx_axis_tready(rx_axis_mac_tready),

        // TX to TSE MAC
        .tx_axis_tdata (tx_axis_mac_tdata),
        .tx_axis_tvalid(tx_axis_mac_tvalid),
        .tx_axis_tlast (tx_axis_mac_tlast),
        .tx_axis_tuser (tx_axis_mac_tuser),
        .tx_axis_tready(tx_axis_mac_tready)
    );

    // =========================================================================
    // T120 <-> T20 Custom Inter-FPGA Bus APB3 Slave (0xF810_3000)
    // =========================================================================
    wire [31:0] t20_bus_prdata;
    wire        t20_bus_pready;
    wire [3:0]  t20_tx_wires;
    wire [7:0]  t20_rx_wires = {RX03_T20_N1, RX03_T20_P1, RX02_T20_N1, RX02_T20_P1,
                                RX01_T20_N1, RX01_T20_P1, RX00_T20_N1, RX00_T20_P1};

    assign TX11_T20_P1 = t20_tx_wires[0];
    assign TX11_T20_N1 = t20_tx_wires[1];
    assign TX12_T20_P1 = t20_tx_wires[2];
    assign TX12_T20_N1 = t20_tx_wires[3];

    t120_t20_bus_apb3 u_t20_bus (
        .pclk           (sys_clk),
        .presetn        (sys_rst_n_inv),
        .psel           (apb_psel & t20_bus_selected),
        .penable        (apb_penable),
        .pwrite         (apb_pwrite),
        .paddr          (apb_paddr[7:0]),
        .pwdata         (apb_pwdata),
        .prdata         (t20_bus_prdata),
        .pready         (t20_bus_pready),
        .pslverr        (),

        .t20_clk9       (T20_CLK9),
        .t20_tx         (t20_tx_wires),
        .t20_rx         (t20_rx_wires),
        .t20_creset_n   ()
    );

    // =========================================================================
    // APB3 Read Multiplexing
    // =========================================================================
    always_comb begin
        if (mac_selected) begin
            apb_prdata = mac_apb_prdata;
            apb_pready = mac_apb_pready;
        end else if (pkt_fifo_selected) begin
            apb_prdata = pkt_fifo_prdata;
            apb_pready = pkt_fifo_pready;
        end else if (t20_bus_selected) begin
            apb_prdata = t20_bus_prdata;
            apb_pready = t20_bus_pready;
        end else begin
            apb_prdata = 32'h0;
            apb_pready = 1'b1;
        end
    end

    // =========================================================================
    // Status LEDs
    // =========================================================================
    assign T120_LED1 = led1_hw_toggle;
    assign T120_LED2 = gpio_out[0];

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
