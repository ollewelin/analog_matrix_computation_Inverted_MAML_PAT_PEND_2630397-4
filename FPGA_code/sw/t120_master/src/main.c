#include <stdint.h>
#include <string.h>
#include "bsp.h"
#include "gpio.h"
#include "uart_mini_driver.h"
#include "mdio_apb_master.h"
#include "t120_bridge_regs.h"

// =============================================================================
// 100-Mbit Ethernet MAC Peripheral Registers (APB3 Base: 0xf8102000)
// =============================================================================
#define ETH_BASE            0xf8102000
#define ETH_CTRL_REG        (*(volatile uint32_t *)(ETH_BASE + 0x00))
#define ETH_STATUS_REG      (*(volatile uint32_t *)(ETH_BASE + 0x04))
#define ETH_TX_LEN_REG      (*(volatile uint32_t *)(ETH_BASE + 0x08))
#define ETH_RX_LEN_REG      (*(volatile uint32_t *)(ETH_BASE + 0x0C))
#define ETH_MAC_LO_REG      (*(volatile uint32_t *)(ETH_BASE + 0x10))
#define ETH_MAC_HI_REG      (*(volatile uint32_t *)(ETH_BASE + 0x14))
#define ETH_TX_CNT_REG      (*(volatile uint32_t *)(ETH_BASE + 0x18))
#define ETH_RX_CNT_REG      (*(volatile uint32_t *)(ETH_BASE + 0x1C))
#define ETH_RX_CRC_ERR_REG  (*(volatile uint32_t *)(ETH_BASE + 0x2C))
#define ETH_CAP_CTRL_REG    (*(volatile uint32_t *)(ETH_BASE + 0x20))  // [0]=arm, read [1]=done
#define ETH_CAP_DATA_REG    (*(volatile uint32_t *)(ETH_BASE + 0x24))  // write index, read sample
#define ETH_RXC_CNT_REG     (*(volatile uint32_t *)(ETH_BASE + 0x28))  // [31:16]=RXC ticks, [15:0]=RXCTL rising edges
#define ETH_RXSFD_REG       (*(volatile uint32_t *)(ETH_BASE + 0x2C))  // [31:16]=SFD hits, [15:0]=frames ended
#define ETH_LAST_CRC_REG    (*(volatile uint32_t *)(ETH_BASE + 0x30))
#define ETH_LAST_LEN_REG    (*(volatile uint32_t *)(ETH_BASE + 0x34))

// =============================================================================
// Ethernet MAC Packet RAM
// =============================================================================
#define ETH_TX_BUF          ((volatile uint32_t *)(ETH_BASE + 0x080))
#define ETH_RX_BUF          ((volatile uint32_t *)(ETH_BASE + 0x800))
#define ETH_CTRL_TX_START   (1u << 0)
#define ETH_CTRL_RX_ACK     (1u << 1)
#define ETH_CTRL_PROMISC    (1u << 2)
#define ETH_STATUS_TX_BUSY  (1u << 0)
#define ETH_STATUS_RX_READY (1u << 1)
#define ETH_STATUS_LINK_UP  (1u << 2)
#define ETH_STATUS_RX_CRC_ERR (1u << 3)

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
    mdio_write(phy, 0x1F, 0x0A43);
    bsp_uDelay(1000);
    uint16_t status = mdio_read(phy, 0x1A);
    mdio_write(phy, 0x1F, 0x0000);
    return status;
}

static uint8_t active_phy = 0x05;

// =============================================================================
// RTL8211F-CG PHY Initialization via MDIO (100M Full Duplex Mode)
// =============================================================================
static void phy_init_100m(void) {
    println_s("=PHY INIT (100M CABLE MODE)=");

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
    // RGMII internal delay: page 0xd08, register 0x11 (TX) and 0x15 (RX)
    // -----------------------------------------------------------------
    print_s("RGMII DLY...");
    mdio_write(phy, 0x1F, 0x0d08);
    bsp_uDelay(1000);
    uint16_t reg11 = mdio_read(phy, 0x11);
    reg11 |= (1 << 8) | (1 << 3);
    mdio_write(phy, 0x11, reg11);
    bsp_uDelay(1000);
    uint16_t reg15 = mdio_read(phy, 0x15);
    reg15 |= (1 << 3); // Enable RTL8211F RX delay (2 ns)
    mdio_write(phy, 0x15, reg15);
    bsp_uDelay(1000);
    mdio_write(phy, 0x1F, 0x0000);
    println_s("OK");

    // Disable Green Ethernet, matching the known-good reference PHY setup.
    mdio_write(phy, 0x1F, 0x0A43);
    mdio_write(phy, 0x1B, 0x8011);
    mdio_write(phy, 0x1C, 0x573F);
    mdio_write(phy, 0x1F, 0x0000);

    // Negotiate 10/100 only; do not advertise 1000BASE-T to the PHY partner.
    println_s("Configuring 100M Auto-Negotiation...");
    mdio_write(phy, PHY_REG_GBCR, 0x0000);
    mdio_write(phy, PHY_REG_ANAR, 0x01E1);
    mdio_write(phy, PHY_REG_BMCR, 0x1200);

    print_s("Waiting for link and autonegotiation...");
    uart_drain();

    int linked = 0;
    uint16_t bmsr = 0;
    for (int i = 0; i < 60; i++) {
        bsp_uDelay(100000);
        bmsr = bmsr_read(phy);
        if ((bmsr & 0x0004) && (bmsr & 0x0020)) {
            linked = 1;
            break;
        }
        print_s(".");
        uart_drain();
    }
    println_s("");

    bmsr = bmsr_read(phy);
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
// Ethernet Packet Buffer Send / Receive Routines
// =============================================================================
static void pkt_fifo_send(const uint8_t *frame, uint16_t len) {
    if (len == 0 || len > 1514) return;

    // Pad to minimum Ethernet frame size (60 bytes without FCS)
    uint16_t send_len = (len < 60) ? 60 : len;

    // Wait if transmitter is busy
    uint32_t timeout = 100000;
    while ((ETH_STATUS_REG & ETH_STATUS_TX_BUSY) && --timeout);

    // Copy to TX RAM (32-bit words, little endian)
    uint32_t words = (send_len + 3) / 4;
    for (uint32_t i = 0; i < words; i++) {
        uint32_t word = 0;
        uint32_t b_offset = i * 4;
        for (int b = 0; b < 4; b++) {
            if (b_offset + b < len) {
                word |= ((uint32_t)frame[b_offset + b]) << (b * 8);
            }
        }
        ETH_TX_BUF[i] = word;
    }

    // Set TX length and trigger start
    ETH_TX_LEN_REG = send_len;
    ETH_CTRL_REG   = ETH_CTRL_TX_START | ETH_CTRL_PROMISC;
}

static uint16_t pkt_fifo_recv(uint8_t *buf, uint16_t max_len) {
    uint32_t status = ETH_STATUS_REG;
    if (!(status & ETH_STATUS_RX_READY)) {
        return 0;
    }

    uint16_t len = (uint16_t)(ETH_RX_LEN_REG & 0xFFFF);
    if (len == 0 || len > 1514) {
        ETH_CTRL_REG = ETH_CTRL_RX_ACK | ETH_CTRL_PROMISC;
        return 0;
    }

    uint16_t copy_len = (len < max_len) ? len : max_len;
    uint32_t words = (copy_len + 3) / 4;

    for (uint32_t i = 0; i < words; i++) {
        uint32_t word = ETH_RX_BUF[i];
        uint32_t b_offset = i * 4;
        for (int b = 0; b < 4; b++) {
            if (b_offset + b < copy_len) {
                buf[b_offset + b] = (uint8_t)((word >> (b * 8)) & 0xFF);
            }
        }
    }

    // Release RX buffer
    ETH_CTRL_REG = ETH_CTRL_RX_ACK | ETH_CTRL_PROMISC;
    return copy_len;
}

// =============================================================================
// ARP and ICMP Echo (Ping) Protocol Handler
// =============================================================================
static void handle_ethernet_packet(uint8_t *frame, uint16_t len) {
    if (len < 14) return;

    uint16_t ether_type = ((uint16_t)frame[12] << 8) | frame[13];

    // -------------------------------------------------------------------------
    // ARP (EtherType 0x0806)
    // -------------------------------------------------------------------------
    if (ether_type == 0x0806 && len >= 42) {
        uint16_t hw_type = ((uint16_t)frame[14] << 8) | frame[15];
        uint16_t proto_type = ((uint16_t)frame[16] << 8) | frame[17];
        uint16_t opcode = ((uint16_t)frame[20] << 8) | frame[21];

        // Check if ARP Request for 192.168.1.50
        if (hw_type == 0x0001 && proto_type == 0x0800 && opcode == 0x0001) {
            if (memcmp(&frame[38], MY_IP, 4) == 0) {
                // Construct ARP Reply
                memcpy(tx_frame, &frame[6], 6);       // Dest MAC = sender MAC
                memcpy(&tx_frame[6], MY_MAC, 6);       // Src MAC  = MY_MAC
                tx_frame[12] = 0x08; tx_frame[13] = 0x06; // ARP

                tx_frame[14] = 0x00; tx_frame[15] = 0x01; // Ethernet
                tx_frame[16] = 0x08; tx_frame[17] = 0x00; // IPv4
                tx_frame[18] = 0x06; tx_frame[19] = 0x04; // HW len 6, Proto len 4
                tx_frame[20] = 0x00; tx_frame[21] = 0x02; // Opcode: Reply (2)

                memcpy(&tx_frame[22], MY_MAC, 6);      // Sender HW = MY_MAC
                memcpy(&tx_frame[28], MY_IP, 4);       // Sender IP = MY_IP
                memcpy(&tx_frame[32], &frame[22], 6);  // Target HW = sender MAC
                memcpy(&tx_frame[38], &frame[28], 4);  // Target IP = sender IP

                pkt_fifo_send(tx_frame, 42);
                println_s("[ARP] Replied to ARP Request!");
            }
        }
        return;
    }

    // -------------------------------------------------------------------------
    // IPv4 (EtherType 0x0800)
    // -------------------------------------------------------------------------
    if (ether_type == 0x0800 && len >= 34) {
        uint8_t ip_ver_ihl = frame[14];
        if ((ip_ver_ihl >> 4) != 4) return;
        uint8_t ihl = (ip_ver_ihl & 0x0F) * 4;
        uint8_t proto = frame[23];

        // Debug print for any incoming IPv4 packet
        print_s("[IP] Proto="); print_hex8_s(proto);
        print_s(" Dst="); 
        for (int i=0; i<4; i++) { print_hex8_s(frame[30+i]); if(i<3) print_s("."); }
        println_s("");

        // Check if packet destination is MY_IP
        if (memcmp(&frame[30], MY_IP, 4) != 0) return;

        // ICMP (Protocol 1)
        if (proto == 0x01 && len >= (14 + ihl + 8)) {
            uint32_t icmp_offset = 14 + ihl;
            uint8_t icmp_type = frame[icmp_offset];
            uint8_t icmp_code = frame[icmp_offset + 1];

            // ICMP Echo Request (Type 8)
            if (icmp_type == 8 && icmp_code == 0) {
                // Copy entire packet to TX buffer
                memcpy(tx_frame, frame, len);

                // Swap Ethernet MACs
                memcpy(tx_frame, &frame[6], 6);
                memcpy(&tx_frame[6], MY_MAC, 6);

                // Swap IPv4 Addresses
                memcpy(&tx_frame[26], &frame[30], 4); // Src IP = MY_IP
                memcpy(&tx_frame[30], &frame[26], 4); // Dst IP = sender IP

                // Set ICMP Type to 0 (Echo Reply)
                tx_frame[icmp_offset] = 0;

                // Adjust ICMP Checksum (+0x0800 because type went 8 -> 0)
                uint32_t csum = ((uint32_t)frame[icmp_offset + 2] << 8) | frame[icmp_offset + 3];
                csum += 0x0800;
                while (csum >> 16) csum = (csum & 0xFFFF) + (csum >> 16);
                tx_frame[icmp_offset + 2] = (uint8_t)(csum >> 8);
                tx_frame[icmp_offset + 3] = (uint8_t)(csum & 0xFF);

                pkt_fifo_send(tx_frame, len);
                uint32_t pst = ETH_STATUS_REG;
                uint16_t tok = (uint16_t)ETH_TX_CNT_REG;
                print_s("[ICMP] Ping Reply triggered! ST="); print_hex16_s((uint16_t)pst);
                print_s(" MAC_TX="); print_hex16_s(tok); println_s("");
            }
        }
    }
}


// =============================================================================
// T120 <-> T20 bridge self-test (no T20 needed): checks ID, Hadamard hardware
// sequencer (ACK check off) and T20 CRESET_N pulse (T120_LED1 pin).
// =============================================================================
static void bridge_selftest(void) {
    println_s("=BRIDGE SELFTEST=");
    print_s("ID=0x"); print_hex16_s((uint16_t)(T20_REG(T20_ID) >> 16)); print_hex16_s((uint16_t)T20_REG(T20_ID)); println_s("");

    T20_REG(T20_CLK_PERIOD) = 25;              // 2 MHz CLK9
    T20_REG(T20_CTRL)       = 1;               // clk_en
    for (uint32_t i = 0; i < 4; i++) {
        *(volatile uint32_t *)(T20_BRIDGE_BASE + T20_H_TABLE + 4 * i) = 0xA000 + i * 0x111;
    }
    T20_REG(T20_H_COUNT)  = 4;
    T20_REG(T20_H_PERIOD) = 20;
    T20_REG(T20_H_CTRL)   = (1 << 0);          // start, ack_en = 0 (no T20 yet)
    bsp_uDelay(2000);                          // 4 x 20 cycles @ 2 MHz = 40 us
    uint32_t hst = T20_REG(T20_H_STATUS);
    print_s("H_STATUS="); print_hex8_s((uint8_t)hst);
    println_s((hst & 2) ? " [H DONE OK]" : " [H DONE MISSING]");
    T20_REG(T20_CTRL) = 0;                     // CLK9 off again (idle bus = quiet pins)

    T20_REG(T20_CRESET_US)   = 12000;
    T20_REG(T20_CRESET_CTRL) = (1 << 1);       // 12 ms T20 reset pulse
    bsp_uDelay(1000);
    uint32_t c1 = T20_REG(T20_CRESET_CTRL);
    bsp_uDelay(20000);
    uint32_t c2 = T20_REG(T20_CRESET_CTRL);
    println_s(((c1 & 0x101) == 0x100 && (c2 & 0x101) == 0x001) ? "CRESET pulse [OK]" : "CRESET pulse [FAIL]");
}

// =============================================================================
// RGMII delay sweep: the RTL8211F TX delay is page 0xd08 reg 0x11 bit 8 and the
// RX delay is page 0xd08 reg 0x15 bit 3. Both are tried with a PHY loopback test
// (MAC -> PHY -> MAC) and with live LAN traffic; the best setting is kept.
// =============================================================================
static void rgmii_delay_set(uint8_t phy, int tx_dly, int rx_dly) {
    mdio_write(phy, 0x1F, 0x0d08);
    bsp_uDelay(1000);
    uint16_t txcr = mdio_read(phy, 0x11);
    uint16_t rxcr = mdio_read(phy, 0x15);
    txcr = tx_dly ? (txcr | (1 << 8)) : (txcr & ~(1 << 8));
    rxcr = rx_dly ? (rxcr | (1 << 3)) : (rxcr & ~(1 << 3));
    mdio_write(phy, 0x11, txcr);
    mdio_write(phy, 0x15, rxcr);
    bsp_uDelay(1000);
    mdio_write(phy, 0x1F, 0x0000);
}

// Drain the RX buffer (answering ARP/ping) for ms milliseconds.
static void eth_listen_ms(uint32_t ms, uint32_t *crc_seen) {
    for (uint32_t t = 0; t < ms * 10; t++) {
        if (crc_seen && (ETH_STATUS_REG & ETH_STATUS_RX_CRC_ERR)) *crc_seen = 1;
        uint16_t n = pkt_fifo_recv(rx_frame, sizeof(rx_frame));
        if (n) handle_ethernet_packet(rx_frame, n);
        bsp_uDelay(100);
    }
}

static uint32_t eth_loopback_test(uint8_t phy) {
    mdio_write(phy, PHY_REG_BMCR, 0x6100);   // loopback, 100M, full duplex, no autoneg
    bsp_uDelay(300000);
    uint8_t f[60];
    memset(f, 0xFF, 6);
    memcpy(&f[6], MY_MAC, 6);
    f[12] = 0x88; f[13] = 0xB5;              // IEEE local experimental ethertype
    for (int i = 14; i < 60; i++) f[i] = (uint8_t)i;
    uint32_t before = ETH_RX_CNT_REG;
    for (int k = 0; k < 8; k++) {
        pkt_fifo_send(f, sizeof(f));
        eth_listen_ms(5, 0);
    }
    eth_listen_ms(20, 0);
    return ETH_RX_CNT_REG - before;
}

static void eth_wait_link(uint8_t phy) {
    mdio_write(phy, PHY_REG_BMCR, 0x1200);   // restart autonegotiation
    for (int i = 0; i < 80; i++) {
        bsp_uDelay(100000);
        uint16_t b = bmsr_read(phy);
        if ((b & 0x0004) && (b & 0x0020)) break;
    }
}

static void rgmii_delay_sweep(uint8_t phy) {
    static const uint8_t combos[4][2] = {{1, 1}, {1, 0}, {0, 1}, {0, 0}};
    println_s("=RGMII DELAY SWEEP=");
    mdio_write(phy, 0x1F, 0x0d08);
    print_s("TXCR(0x11)="); print_hex16_s(mdio_read(phy, 0x11));
    print_s(" RXCR(0x15)="); print_hex16_s(mdio_read(phy, 0x15)); println_s("");
    mdio_write(phy, 0x1F, 0x0000);

    uint32_t best = 0;
    int best_tx = 1, best_rx = 1;
    for (int c = 0; c < 4; c++) {
        int tx = combos[c][0], rx = combos[c][1];
        rgmii_delay_set(phy, tx, rx);
        uint32_t lb = eth_loopback_test(phy);
        eth_wait_link(phy);
        uint32_t crc = 0;
        uint32_t before = ETH_RX_CNT_REG;
        eth_listen_ms(2000, &crc);
        uint32_t live = ETH_RX_CNT_REG - before;

        print_s("TXDLY="); print_hex8_s((uint8_t)tx);
        print_s(" RXDLY="); print_hex8_s((uint8_t)rx);
        print_s(" LOOPBACK_RX="); print_hex16_s((uint16_t)lb);
        print_s(" LIVE_RX="); print_hex16_s((uint16_t)live);
        print_s(" CRCFLAG="); print_hex8_s((uint8_t)crc);
        println_s("");
        uart_drain();
        if (lb + live > best) {
            best = lb + live;
            best_tx = tx;
            best_rx = rx;
        }
    }
    rgmii_delay_set(phy, best_tx, best_rx);
    print_s("SWEEP BEST: TXDLY="); print_hex8_s((uint8_t)best_tx);
    print_s(" RXDLY="); print_hex8_s((uint8_t)best_rx);
    print_s(" SCORE="); print_hex16_s((uint16_t)best); println_s("");
}

// =============================================================================
// RX diagnostics: counters and raw RGMII sample capture (needs the diagnostic MAC)
// Each sample prints as NN:PP = {ctl,d[3:0]} at the falling edge : rising edge.
// =============================================================================
static void eth_rx_diag(void) {
    uint32_t a = ETH_RXC_CNT_REG;
    bsp_uDelay(100);
    uint32_t b = ETH_RXC_CNT_REG;
    uint32_t s = ETH_RXSFD_REG;
    uint32_t crc = ETH_LAST_CRC_REG;
    print_s("RXC/100us="); print_hex16_s((uint16_t)((b >> 16) - (a >> 16)));
    print_s(" CTLEDGES="); print_hex16_s((uint16_t)b);
    print_s(" SFD="); print_hex16_s((uint16_t)(s >> 16));
    print_s(" ENDED="); print_hex16_s((uint16_t)s);
    print_s(" LASTLEN="); print_hex16_s((uint16_t)ETH_LAST_LEN_REG);
    print_s(" LASTCRC="); print_hex16_s((uint16_t)(crc >> 16)); print_hex16_s((uint16_t)crc);
    println_s("");

    for (int n = 0; n < 3; n++) {
        ETH_CAP_CTRL_REG = 0;
        bsp_uDelay(10);
        ETH_CAP_CTRL_REG = 1;
        int waited = 0;
        while (!(ETH_CAP_CTRL_REG & 2) && waited < 3000) {
            bsp_uDelay(1000);
            waited++;
        }
        if (!(ETH_CAP_CTRL_REG & 2)) {
            println_s("CAP: timeout, RXCTL never went high");
            break;
        }
        println_s("CAP:");
        for (int i = 0; i < 128; i++) {
            ETH_CAP_DATA_REG = (uint32_t)i;
            bsp_uDelay(2);
            uint32_t w = ETH_CAP_DATA_REG;
            print_hex8_s((uint8_t)((w >> 5) & 0x1F)); print_s(":");
            print_hex8_s((uint8_t)(w & 0x1F));        print_s(" ");
            if ((i & 15) == 15) {
                println_s("");
                uart_drain();
            }
        }
    }
    ETH_CAP_CTRL_REG = 0;
}

// =============================================================================
// Main
// =============================================================================
void main(void) {
    bsp_init();

    // GPIO output enable för LED2 (bit 0) och F2_RSTB (bit 1)
    gpio_setOutputEnable(SYSTEM_GPIO_0_IO_CTRL, 0x3);
    current_gpio = 0x2; // F2_RSTB high
    gpio_setOutput(SYSTEM_GPIO_0_IO_CTRL, current_gpio);

    for (int i = 0; i < 3; i++) led_pulse(150);

    println_s("================================");
    println_s("= T120 100M APB MAC =");
    println_s("= IP:  192.168.1.50            =");
    println_s("= MAC: 00:12:34:56:78:9A       =");
    println_s("================================");
    println_s("Test 4: Sapphire SoC Packet Handling (ARP + Ping Responder)");

    ETH_MAC_LO_REG = 0x56789A;
    ETH_MAC_HI_REG = 0x001234;
    ETH_CTRL_REG   = ETH_CTRL_PROMISC;

    // Initialize the RTL8211F through the separate APB MDIO master.
    mdio_init();
    phy_init_100m();
    eth_rx_diag();
    // Do NOT run rgmii_delay_sweep: phy_init_100m already sets reg 0x11 = 0x018b / bit 8+3.

    bridge_selftest();

    println_s("100M MAC + Sapphire SoC Active. Listening for ARP / Ping...");

    uint32_t loop_cnt = 0;
    uint16_t last_bmsr = 0;

    while (1) {
        loop_cnt++;

        // Poll incoming Ethernet frames
        uint16_t rx_len = pkt_fifo_recv(rx_frame, sizeof(rx_frame));
        if (rx_len > 0) {
            handle_ethernet_packet(rx_frame, rx_len);
        }

        // Periodic Status Telemetry (~every 1 second)
        if ((loop_cnt % 500000) == 0) {
            led_on();
            uint16_t bmsr = bmsr_read(active_phy);

            uint16_t tx_ok = (uint16_t)ETH_TX_CNT_REG;
            uint16_t rx_ok = (uint16_t)ETH_RX_CNT_REG;
            uint16_t rx_crc = (uint16_t)ETH_RX_CRC_ERR_REG;
            uint32_t pkt_st = ETH_STATUS_REG;

            if ((bmsr & 0x0004) && !(last_bmsr & 0x0004)) {
                println_s(">>> ETHERNET LINK UP! (Cable connected) <<<");
            } else if (!(bmsr & 0x0004) && (last_bmsr & 0x0004)) {
                println_s(">>> ETHERNET LINK DOWN! (Cable disconnected) <<<");
            }
            last_bmsr = bmsr;

            print_s("[ETH] BMSR=");
            print_hex16_s(bmsr);
            print_s(" RX=");
            print_hex16_s(rx_ok);
            print_s(" TX=");
            print_hex16_s(tx_ok);
            print_s(" FCS="); print_hex16_s(rx_crc);
            print_s(" FIFO_ST=");
            print_hex16_s((uint16_t)pkt_st);
            println_s("");
        } else if ((loop_cnt % 500000) == 250000) {
            led_off();
        }
    }
}