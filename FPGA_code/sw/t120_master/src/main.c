#include <stdint.h>
#include <string.h>
#include "bsp.h"
#include "gpio.h"
#include "uart_mini_driver.h"
#include "mdio_driver.h"

// =============================================================================
// Ethernet MAC Peripheral Registers (APB3 Base: 0xf8102000)
// =============================================================================
#define TSE_BASE            0xf8100000
#define TSE_VERSION_REG     (*(volatile uint32_t *)(TSE_BASE + 0x00))
#define TSE_CMD_CONFIG_REG  (*(volatile uint32_t *)(TSE_BASE + 0x08))
#define TSE_MAC_ADDR0_REG   (*(volatile uint32_t *)(TSE_BASE + 0x0C))
#define TSE_MAC_ADDR1_REG   (*(volatile uint32_t *)(TSE_BASE + 0x10))
#define TSE_FRM_LENGTH_REG  (*(volatile uint32_t *)(TSE_BASE + 0x14))

// Network Configuration
static const uint8_t MY_MAC[6] = {0x00, 0x12, 0x34, 0x56, 0x78, 0x9A};
static const uint8_t MY_IP[4]  = {192, 168, 1, 50};

// Working packet buffers
static uint8_t tx_frame[1536];
static uint8_t rx_frame[1536];

// =============================================================================
// Standard Sapphire SoC UART (Pin SCLR_DAC_W_34 @ 115200 baud)
// =============================================================================
static void uart_drain(void) {
    bsp_uDelay(500);
}

static void print_s(const char *s) {
    uart_writeStr(BSP_UART_TERMINAL, s);
}

static void println_s(const char *s) {
    print_s(s);
    uart_writeStr(BSP_UART_TERMINAL, "\r\n");
}

static void print_hex8_s(uint8_t v) {
    const char h[] = "0123456789ABCDEF";
    uart_write(BSP_UART_TERMINAL, h[(v >> 4) & 0xF]);
    uart_write(BSP_UART_TERMINAL, h[ v       & 0xF]);
}

static void print_hex16_s(uint16_t v) {
    print_hex8_s((uint8_t)(v >> 8));
    print_hex8_s((uint8_t)(v & 0xFF));
}

static void print_dump(const char *tag, const uint8_t *buf, uint16_t len) {
    print_s(tag); print_s("["); print_hex16_s(len); print_s("]: ");
    uint16_t show_len = (len > 32) ? 32 : len;
    for (int i = 0; i < show_len; i++) {
        print_hex8_s(buf[i]);
        if ((i % 4) == 3) {
            uart_write(BSP_UART_TERMINAL, ' ');
        }
    }
    println_s("");
}

// GPIO Controls:
// bit 0 = T120_LED2
// bit 1 = F2_RSTB (RTL8211F PHY hardware reset, active-low)
static uint32_t current_gpio = 0x2; // default: F2_RSTB high (normal run)

static void led_on(void)  { current_gpio |= 0x1;  gpio_setOutput(SYSTEM_GPIO_0_IO_CTRL, current_gpio); }
static void led_off(void) { current_gpio &= ~0x1; gpio_setOutput(SYSTEM_GPIO_0_IO_CTRL, current_gpio); }

static void phy_hw_reset_assert(void) {
    current_gpio &= ~0x2; // Drive F2_RSTB LOW (in reset)
    gpio_setOutput(SYSTEM_GPIO_0_IO_CTRL, current_gpio);
}

static void phy_hw_reset_release(void) {
    current_gpio |= 0x2;  // Drive F2_RSTB HIGH (normal run)
    gpio_setOutput(SYSTEM_GPIO_0_IO_CTRL, current_gpio);
}

static void led_pulse(int ms) {
    led_on();
    bsp_uDelay(ms * 1000);
    led_off();
    bsp_uDelay(ms * 1000);
}

static uint16_t bmsr_read(uint8_t phy) {
    mdio_read(phy, PHY_REG_BMSR);
    uint16_t v = mdio_read(phy, PHY_REG_BMSR);
    if (v == 0xFFFF) return 0;
    return v;
}

static uint16_t rtl_physr(uint8_t phy) {
    return mdio_read(phy, 0x11);
}

static uint8_t active_phy = 0x05;

// =============================================================================
// RTL8211F-CG PHY Initialization via MDIO (100M Full Duplex Mode)
// =============================================================================
static void phy_init_100m(void) {
    println_s("=PHY INIT (100M)=");

    // Hardware reset: assert for 50 ms, release, wait 300 ms for PHY ready
    print_s("PHY HW RST...");
    phy_hw_reset_assert();
    bsp_uDelay(50000);
    phy_hw_reset_release();
    bsp_uDelay(300000);
    println_s("OK");

    uint8_t phy = 0x00;
    print_s("SCAN PHY: ");
    for (int a = 0; a < 32; a++) {
        uint16_t id = mdio_read(a, PHY_REG_PHYID1);
        if (id == 0x001C) {
            print_s("[0x"); print_hex8_s(a); print_s("] ");
            if (a != 0) phy = a; // Prefer unicast address
        }
    }
    println_s("");
    active_phy = phy;

    uint16_t id1 = mdio_read(phy, PHY_REG_PHYID1);
    uint16_t id2 = mdio_read(phy, PHY_REG_PHYID2);
    print_s("ACTIVE PHYAD=0x"); print_hex8_s(phy);
    print_s(" ID="); print_hex16_s(id1); print_s("/"); print_hex16_s(id2); println_s("");

    // -----------------------------------------------------------------
    // RGMII internal delay: page 0xd08, register 0x11
    //   bit 8 = TXDLY (2 ns TX delay in PHY)
    //   bit 3 = RXDLY (2 ns RX delay in PHY)
    // -----------------------------------------------------------------
    print_s("RGMII DLY...");
    mdio_write(phy, 0x1F, 0x0d08);
    bsp_uDelay(1000);
    uint16_t reg11 = mdio_read(phy, 0x11);
    reg11 |= (1 << 8) | (1 << 3);
    mdio_write(phy, 0x11, reg11);
    bsp_uDelay(1000);
    mdio_write(phy, 0x1F, 0x0000);
    println_s("OK");

    // -----------------------------------------------------------------
    // Disable Green Ethernet / EEE (datasheet 7.10.2: page 0, Reg 27/28)
    // -----------------------------------------------------------------
    print_s("Dis GreenEth...");
    mdio_write(phy, 0x1F, 0x0000);
    mdio_write(phy, 0x1B, 0x8011);
    mdio_write(phy, 0x1C, 0x573F);
    println_s("OK");

    // =========================================================================
    // LOOPBACK TESTS (Exact sequence from Test v5)
    // =========================================================================
    println_s("=LOOPBACK TEST=");
    // 10M LB
    mdio_write(phy, PHY_REG_BMCR, 0x4100);
    bsp_uDelay(500000);
    uint16_t bmsr = bmsr_read(phy);
    print_s("10M  LB: BMSR=0x"); print_hex16_s(bmsr);
    println_s((bmsr & 0x0004) ? " UP" : " DN");

    // SW reset
    mdio_write(phy, PHY_REG_BMCR, 0x8000);
    bsp_uDelay(200000);

    // 100M LB
    mdio_write(phy, PHY_REG_BMCR, 0x6100);
    bsp_uDelay(500000);
    bmsr = bmsr_read(phy);
    print_s("100M LB: BMSR=0x"); print_hex16_s(bmsr);
    println_s((bmsr & 0x0004) ? " UP" : " DN");

    // SW reset
    mdio_write(phy, PHY_REG_BMCR, 0x8000);
    bsp_uDelay(200000);

    // 1G LB
    mdio_write(phy, PHY_REG_BMCR, 0x4140);
    bsp_uDelay(500000);
    bmsr = bmsr_read(phy);
    print_s("1G   LB: BMSR=0x"); print_hex16_s(bmsr);
    println_s((bmsr & 0x0004) ? " UP" : " DN");

    // Exit LB via SW reset
    mdio_write(phy, PHY_REG_BMCR, 0x8000);
    bsp_uDelay(200000);

    // Re-apply Green Ethernet disable
    mdio_write(phy, 0x1F, 0x0000);
    mdio_write(phy, 0x1B, 0x8011);
    mdio_write(phy, 0x1C, 0x573F);

    // =========================================================================
    // AUTO-NEGOTIATION (Exact sequence from Test v5)
    // =========================================================================
    println_s("=AUTO-NEG=");
    mdio_write(phy, PHY_REG_GBCR, 0x0200); // 1000M FD
    mdio_write(phy, PHY_REG_ANAR, 0x01E1); // 100M/10M
    mdio_write(phy, PHY_REG_BMCR, 0x1200); // AN enable + restart
    print_s("Wait");
    uart_drain();

    int linked = 0;
    for (int i = 0; i < 15; i++) {
        bsp_uDelay(1000000); // 1 second
        bmsr = bmsr_read(phy);
        if ((bmsr & 0x0004) && (bmsr & 0x0020)) {
            linked = 1;
            break;
        }
        print_s(".");
        uart_drain();
    }
    println_s("");

    // Report final status
    bmsr   = bmsr_read(phy);
    uint16_t gbsr   = mdio_read(phy, PHY_REG_GBSR);
    uint16_t anlpar = mdio_read(phy, PHY_REG_ANLPAR);
    uint16_t physr  = rtl_physr(phy);

    print_s("FINAL BMSR="); print_hex16_s(bmsr);
    println_s((bmsr & 0x0004) ? " [LINK UP]" : " [LINK DOWN]");
    print_s("GBSR=");   print_hex16_s(gbsr);   println_s("");
    print_s("ANLPAR="); print_hex16_s(anlpar); println_s("");

    uint16_t spd = (physr >> 4) & 0x3;
    print_s("PHYSR=0x"); print_hex16_s(physr);
    if      (spd == 2) print_s(" 1000M");
    else if (spd == 1) print_s(" 100M");
    else               print_s(" 10M");
    print_s((physr & 0x08) ? " FD" : " HD");
    println_s("");

    if (linked && spd == 1) {
        println_s("** 100M FULL DUPLEX LINK UP! **");
    } else if (linked) {
        println_s("** LINK UP (OTHER SPEED) **");
    } else {
        println_s("NOTE: Physical link down on cable.");
    }
}

// =============================================================================
// Wire-speed line-rate packet loopback is handled directly in hardware via TSE MAC.

// =============================================================================
// Main
// =============================================================================
void main(void) {
    bsp_init();

    // GPIO output enable for LED2 (bit 0) and F2_RSTB (bit 1)
    gpio_setOutputEnable(SYSTEM_GPIO_0_IO_CTRL, 0x3);
    current_gpio = 0x2; // F2_RSTB high
    gpio_setOutput(SYSTEM_GPIO_0_IO_CTRL, current_gpio);

    for (int i = 0; i < 3; i++) led_pulse(150);

    println_s("================================");
    println_s("= T120 Standard Efinix TSE MAC =");
    println_s("= IP:  192.168.1.50            =");
    println_s("= MAC: 00:12:34:56:78:9A       =");
    println_s("================================");

    // Initialize TSE MAC internal registers via AXI-Lite
    // Set MAC source address: 00:12:34:56:78:9A
    // 0x0C = lower 32 bits (0x3456789A), 0x10 = upper 16 bits (0x00000012)
    TSE_MAC_ADDR0_REG = 0x3456789A;
    TSE_MAC_ADDR1_REG = 0x00000012;
    TSE_FRM_LENGTH_REG = 1518;

    // Command_Config:
    // bit 0: tx_ena = 1
    // bit 1: rx_ena = 1
    // bit 4: promis_en = 1 (promiscuous mode)
    // bit 16..18: eth_speed = 3'b010 (100 Mbps) -> (2 << 16) = 0x00020000
    // Total = 0x00020013
    TSE_CMD_CONFIG_REG = (2 << 16) | (1 << 4) | (1 << 1) | (1 << 0);

    print_s("TSE Version: 0x");
    print_hex16_s((uint16_t)TSE_VERSION_REG);
    println_s("");

    // Initialize RTL8211F PHY via TSE integrated MDIO
    mdio_init();
    phy_init_100m();

    println_s("Standard TSE MAC Active. Direct Wire-Speed Loopback Running.");

    uint32_t loop_cnt = 0;
    while (1) {
        // Slow heartbeat on LED2 and periodic link check
        loop_cnt++;
        if ((loop_cnt % 5000000) == 0) {
            led_on();
            uint16_t bmsr = bmsr_read(active_phy);
            uint16_t physr = rtl_physr(active_phy);

            uint16_t tx_ok = (uint16_t)(*(volatile uint32_t *)(TSE_BASE + 0x68) & 0xFFFF);
            uint16_t rx_ok = (uint16_t)(*(volatile uint32_t *)(TSE_BASE + 0x6C) & 0xFFFF);
            uint16_t rx_crc = (uint16_t)(*(volatile uint32_t *)(TSE_BASE + 0x70) & 0xFFFF);
            uint16_t bmcr = mdio_read(active_phy, PHY_REG_BMCR);
            uint16_t anar = mdio_read(active_phy, PHY_REG_ANAR);
            uint16_t gbcr = mdio_read(active_phy, PHY_REG_GBCR);

            print_s("[TSE] BMSR=");
            print_hex16_s(bmsr);
            print_s(" BMCR=");
            print_hex16_s(bmcr);
            print_s(" ANAR=");
            print_hex16_s(anar);
            print_s(" GBCR=");
            print_hex16_s(gbcr);
            print_s(" RX=");
            print_hex16_s(rx_ok);
            print_s(" TX=");
            print_hex16_s(tx_ok);
            println_s("");
        } else if ((loop_cnt % 5000000) == 2500000) {
            led_off();
        }
    }
}
