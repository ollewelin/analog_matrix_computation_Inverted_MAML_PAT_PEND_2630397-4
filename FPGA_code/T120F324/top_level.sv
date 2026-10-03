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
  (* syn_peri_port = 0 *) input PLL_25MHZ,
  (* syn_peri_port = 0 *) input pll_clk_75Mhz,
  (* syn_peri_port = 0 *) input pll_clk_100Mhz,
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
    wire sys_clk   = pll_clk_50Mhz;
    wire rgmii_clk = PLL_25MHZ; // 25 MHz clock for MII/RGMII 100M/SDR, 125MHz from PHY for 1000M

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
        .io_asyncReset              (1'b0),

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

    // =========================================================================
    // UART Mini APB3 (0xF810_0000) - TEMPORARY DEBUG ON SCLR_DAC_W_34 (Pin F13)
    // =========================================================================
    wire [31:0] uart_prdata;
    wire        uart_pready;
    wire        uart_txd;

    uart_mini_apb3 u_uart_mini (
        .pclk       (sys_clk),
        .presetn    (sys_rst_n_inv),
        .psel       (apb_psel & uart_mini_selected),
        .penable    (apb_penable),
        .pwrite     (apb_pwrite),
        .paddr      (apb_paddr[7:0]),
        .pwdata     (apb_pwdata),
        .prdata     (uart_prdata),
        .pready     (uart_pready),
        .pslverr    (),
        .uart_txd   (uart_txd),
        .uart_rxd   (1'b1),
        .debug_tx_activity(),
        .debug_any_write(),
        .debug_bus_state(),
        .debug_psel_in(),
        .debug_penable_in(),
        .debug_pwrite_in(),
        .debug_act_write(),
        .debug_act_read(),
        .debug_slave_ready(),
        .debug_reg_addr()
    );

    // Assign temporary debug UART TX to SCLR_DAC_W_34
    assign SCLR_DAC_W_34 = uart_txd;

    // =========================================================================
    // MDIO Master (0xF810_1000)
    // =========================================================================
    wire [31:0] mdio_prdata;
    wire        mdio_pready;
    wire        mdio_o;
    wire        mdio_oe;

    assign F2_MDIO_OUT = mdio_o;
    assign F2_MDIO_OE  = mdio_oe;

    mdio_master #(
        .SYS_CLK_HZ(50_000_000),
        .MDC_HZ    (1_000_000)
    ) u_mdio_master (
        .clk        (sys_clk),
        .rst_n      (sys_rst_n_inv),
        .psel       (apb_psel & mdio_selected),
        .penable    (apb_penable),
        .pwrite     (apb_pwrite),
        .paddr      ({2'b00, apb_paddr[3:2]}),
        .pwdata     (apb_pwdata),
        .prdata     (mdio_prdata),
        .pready     (mdio_pready),
        .pslverr    (),

        .mdc        (F2_MDC),
        .mdio_i     (F2_MDIO_IN),
        .mdio_o     (mdio_o),
        .mdio_oe    (mdio_oe),
        .phy_rst_n  (F2_RSTB),
        .irq        ()
    );

    // =========================================================================
    // Ethernet MAC Core (0xF810_2000)
    // =========================================================================
    wire [31:0] eth_prdata;
    wire        eth_pready;
    wire [3:0]  eth_txd;
    wire        eth_activity;

    assign F2_TXD0 = eth_txd[0];
    assign F2_TXD1 = eth_txd[1];
    assign F2_TXD2 = eth_txd[2];
    assign F2_TXD3 = eth_txd[3];

    eth_mac_100m u_eth_mac (
        .sys_clk        (sys_clk),
        .sys_rst_n      (sys_rst_n_inv),
        .apb_paddr      (apb_paddr[11:0]),
        .apb_psel       (apb_psel & eth_selected),
        .apb_penable    (apb_penable),
        .apb_pwrite     (apb_pwrite),
        .apb_pwdata     (apb_pwdata),
        .apb_prdata         (eth_prdata),
        .apb_pready         (eth_pready),
        .apb_pslverr        (),

        .rgmii_tx_clk   (rgmii_clk),
        .rgmii_txc      (F2_TXC),
        .rgmii_txctl    (F2_TXCTL),
        .rgmii_txd      (eth_txd),

        .rgmii_rxc      (F2_RXC),
        .rgmii_rxctl    (F2_RXCTL),
        .rgmii_rxd      ({F2_RXD3, F2_RXD2, F2_RXD1, F2_RXD0}),

        .phy_link_up    (1'b1),
        .activity_led   (eth_activity)
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
        .t20_creset_n   () // Ready for patch wire to T20 CRESET_N
    );

    // =========================================================================
    // APB3 Read Multiplexing
    // =========================================================================
    always_comb begin
        if (uart_mini_selected) begin
            apb_prdata = uart_prdata;
            apb_pready = uart_pready;
        end else if (mdio_selected) begin
            apb_prdata = mdio_prdata;
            apb_pready = mdio_pready;
        end else if (eth_selected) begin
            apb_prdata = eth_prdata;
            apb_pready = eth_pready;
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
