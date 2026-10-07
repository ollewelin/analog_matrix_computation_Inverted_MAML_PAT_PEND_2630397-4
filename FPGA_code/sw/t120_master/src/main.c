#include <stdint.h>
#include <string.h>
#include "bsp.h"
#include "gpio.h"
#include "uart_mini_driver.h"
#include "mdio_driver.h"

// =============================================================================
// Ethernet MAC Peripheral Registers (APB3 Base: 0xf8100000)
// =============================================================================
#define TSE_BASE            0xf8100000
#define TSE_VERSION_REG     (*(volatile uint32_t *)(TSE_BASE + 0x00))
#define TSE_CMD_CONFIG_REG  (*(volatile uint32_t *)(TSE_BASE + 0x08))
#define TSE_MAC_ADDR0_REG   (*(volatile uint32_t *)(TSE_BASE + 0x0C))
#define TSE_MAC_ADDR1_REG   (*(volatile uint32_t *)(TSE_BASE + 0x10))
#define TSE_FRM_LENGTH_REG  (*(volatile uint32_t *)(TSE_BASE + 0x14))

// =============================================================================
// Ethernet Packet FIFO Peripheral Registers (APB3 Base: 0xf8102000)
// =============================================================================
#define PKT_FIFO_BASE       0xf8102000
#define PKT_CTRL_REG        (*(volatile uint32_t *)(PKT_FIFO_BASE + 0x00))
#define PKT_STATUS_REG      (*(volatile uint32_t *)(PKT_FIFO_BASE + 0x04))
#define PKT_TX_LEN_REG      (*(volatile uint32_t *)(PKT_FIFO_BASE + 0x08))
#define PKT_RX_LEN_REG      (*(volatile uint32_t *)(PKT_FIFO_BASE + 0x0C))

#define PKT_TX_RAM          ((volatile uint32_t *)(PKT_FIFO_BASE + 0x080))
#define PKT_RX_RAM          ((volatile uint32_t *)(PKT_FIFO_BASE + 0x800))

#define PKT_CTRL_TX_START   (1 << 0)
#define PKT_CTRL_RX_ACK     (1 << 1)

#define PKT_STATUS_TX_BUSY  (1 << 0)
#define PKT_STATUS_RX_READY (1 << 1)
#define PKT_STATUS_RX_ERR   (1 << 2)

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
    return mdio_read(phy, 0x11);
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
    // RGMII internal delay: page 0xd08, register 0x11
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

    // =========================================================================
    // TVINGA FAST 100M FULL DUPLEX
    // =========================================================================
    println_s("=FORCING FAST 100M FULL DUPLEX=");
    mdio_write(phy, PHY_REG_BMCR, 0x2100);

    print_s("Waiting for link..");
    uart_drain();

    int linked = 0;
    uint16_t bmsr = 0;
    for (int i = 0; i < 10; i++) {
        bsp_uDelay(500000);
        bmsr = bmsr_read(phy);
        if (bmsr & 0x0004) {
            linked = 1;
            break;
        }
        print_s(".");
        uart_drain();
    }
    println_s("");

    bmsr            = bmsr_read(phy);
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
// Packet FIFO Send / Receive Routines
// =============================================================================
static void pkt_fifo_send(const uint8_t *frame, uint16_t len) {
    if (len == 0 || len > 1514) return;

    // Pad to minimum Ethernet frame size (60 bytes without FCS)
    uint16_t send_len = (len < 60) ? 60 : len;

    // Wait if transmitter is busy
    uint32_t timeout = 100000;
    while ((PKT_STATUS_REG & PKT_STATUS_TX_BUSY) && --timeout);

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
        PKT_TX_RAM[i] = word;
    }

    // Set TX length and trigger start
    PKT_TX_LEN_REG = send_len;
    PKT_CTRL_REG   = PKT_CTRL_TX_START;
}

static uint16_t pkt_fifo_recv(uint8_t *buf, uint16_t max_len) {
    uint32_t status = PKT_STATUS_REG;
    if (!(status & PKT_STATUS_RX_READY)) {
        return 0;
    }

    uint16_t len = (uint16_t)(PKT_RX_LEN_REG & 0xFFFF);
    if (len == 0 || len > 1514) {
        PKT_CTRL_REG = PKT_CTRL_RX_ACK;
        return 0;
    }

    uint16_t copy_len = (len < max_len) ? len : max_len;
    uint32_t words = (copy_len + 3) / 4;

    for (uint32_t i = 0; i < words; i++) {
        uint32_t word = PKT_RX_RAM[i];
        uint32_t b_offset = i * 4;
        for (int b = 0; b < 4; b++) {
            if (b_offset + b < copy_len) {
                buf[b_offset + b] = (uint8_t)((word >> (b * 8)) & 0xFF);
            }
        }
    }

    // Release RX buffer
    PKT_CTRL_REG = PKT_CTRL_RX_ACK;
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
                uint32_t pst = PKT_STATUS_REG;
                uint16_t tok = (uint16_t)(*(volatile uint32_t *)(TSE_BASE + 0x68) & 0xFFFF);
                print_s("[ICMP] Ping Reply triggered! ST="); print_hex16_s((uint16_t)pst);
                print_s(" MAC_TX="); print_hex16_s(tok); println_s("");
            }
        }
    }
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
    println_s("= T120 Standard Efinix TSE MAC =");
    println_s("= IP:  192.168.1.50            =");
    println_s("= MAC: 00:12:34:56:78:9A       =");
    println_s("================================");
    println_s("Test 4: Sapphire SoC Packet Handling (ARP + Ping Responder)");

    // Initiera TSE MAC
    TSE_MAC_ADDR0_REG = 0x3456789A;
    TSE_MAC_ADDR1_REG = 0x00000012;
    TSE_FRM_LENGTH_REG = 1518;
    *(volatile uint32_t *)(TSE_BASE + 0x5C) = 0x0C; // TX_IPG_LEN = 12

    // eth_speed = 3'b010 (100 Mbps), promiscuous = 1, pad_en = 1, rx_ena = 1, tx_ena = 1
    // bit 0 = tx_en, bit 1 = rx_en, bit 4 = promisc, bit 5 = pad_en, bit [18:16] = speed (2)
    TSE_CMD_CONFIG_REG = (2 << 16) | (1 << 5) | (1 << 4) | (1 << 1) | (1 << 0);

    print_s("TSE Version: 0x");
    print_hex16_s((uint16_t)TSE_VERSION_REG);
    println_s("");

    // Initiera RTL8211F PHY via MDIO
    mdio_init();
    phy_init_100m();

    println_s("TSE MAC + Sapphire Packet FIFO Active. Listening for ARP / Ping...");

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

            uint16_t tx_ok = (uint16_t)(*(volatile uint32_t *)(TSE_BASE + 0x68) & 0xFFFF);
            uint16_t rx_ok = (uint16_t)(*(volatile uint32_t *)(TSE_BASE + 0x6C) & 0xFFFF);
            uint16_t rx_crc = (uint16_t)(*(volatile uint32_t *)(TSE_BASE + 0x70) & 0xFFFF);
            uint16_t if_out_err = (uint16_t)(*(volatile uint32_t *)(TSE_BASE + 0x8C) & 0xFFFF);
            uint32_t pkt_st = PKT_STATUS_REG;

            if ((bmsr & 0x0004) && !(last_bmsr & 0x0004)) {
                println_s(">>> ETHERNET LINK UP! (Cable connected) <<<");
            } else if (!(bmsr & 0x0004) && (last_bmsr & 0x0004)) {
                println_s(">>> ETHERNET LINK DOWN! (Cable disconnected) <<<");
            }
            last_bmsr = bmsr;

            print_s("[TSE] BMSR=");
            print_hex16_s(bmsr);
            print_s(" RX=");
            print_hex16_s(rx_ok);
            print_s(" TX=");
            print_hex16_s(tx_ok);
            print_s(" OUT_ERR=");
            print_hex16_s(if_out_err);
            print_s(" FIFO_ST=");
            print_hex16_s((uint16_t)pkt_st);
            println_s("");
        } else if ((loop_cnt % 500000) == 250000) {
            led_off();
        }
    }
}