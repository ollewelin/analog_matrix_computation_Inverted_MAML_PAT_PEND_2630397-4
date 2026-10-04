#include "eth_mac_100m.h"
#include <string.h>

#define REG32(addr) (*(volatile uint32_t *)(uintptr_t)(addr))

void eth_mac_init(const uint8_t mac_addr[6]) {
    if (mac_addr) {
        uint32_t mac_lo = ((uint32_t)mac_addr[0]) |
                          (((uint32_t)mac_addr[1]) << 8) |
                          (((uint32_t)mac_addr[2]) << 16) |
                          (((uint32_t)mac_addr[3]) << 24);
        uint32_t mac_hi = ((uint32_t)mac_addr[4]) |
                          (((uint32_t)mac_addr[5]) << 8);
        REG32(ETH_MAC_BASE + ETH_REG_MAC_LO) = mac_lo;
        REG32(ETH_MAC_BASE + ETH_REG_MAC_HI) = mac_hi;
    }
    /* Clear control register (promisc=0, loopback=0) */
    REG32(ETH_MAC_BASE + ETH_REG_CTRL) = 0;
}

bool eth_mac_is_link_up(void) {
    return (REG32(ETH_MAC_BASE + ETH_REG_STATUS) & ETH_STATUS_LINK_UP) != 0;
}

bool eth_mac_tx_busy(void) {
    return (REG32(ETH_MAC_BASE + ETH_REG_STATUS) & ETH_STATUS_TX_BUSY) != 0;
}

void eth_mac_send(const uint8_t *frame, uint16_t length) {
    if (length == 0 || length > 1514) return;

    /* Wait if previous transmission is still busy */
    uint32_t timeout = 100000;
    while (eth_mac_tx_busy() && --timeout);

    /* Copy frame into TX RAM as 32-bit words */
    volatile uint32_t *tx_ram = (volatile uint32_t *)(ETH_MAC_BASE + ETH_TX_RAM_OFFSET);
    uint32_t words = (length + 3) / 4;
    
    /* Ensure no out-of-bounds byte reading by packing into uint32_t */
    for (uint32_t i = 0; i < words; i++) {
        uint32_t word = 0;
        uint32_t b_offset = i * 4;
        for (int b = 0; b < 4; b++) {
            if (b_offset + b < length) {
                word |= ((uint32_t)frame[b_offset + b]) << (b * 8);
            }
        }
        tx_ram[i] = word;
    }

    /* Set TX length */
    REG32(ETH_MAC_BASE + ETH_REG_TX_LEN) = length;

    /* Trigger TX */
    REG32(ETH_MAC_BASE + ETH_REG_CTRL) |= ETH_CTRL_TX_START;
}

bool eth_mac_has_rx(void) {
    return (REG32(ETH_MAC_BASE + ETH_REG_STATUS) & ETH_STATUS_RX_READY) != 0;
}

uint16_t eth_mac_rx_len(void) {
    uint32_t status = REG32(ETH_MAC_BASE + ETH_REG_STATUS);
    return (uint16_t)((status >> 16) & 0xFFFF);
}

void eth_mac_rx_ack(void) {
    REG32(ETH_MAC_BASE + ETH_REG_CTRL) |= ETH_CTRL_RX_ACK;
}

uint16_t eth_mac_recv(uint8_t *buffer, uint16_t max_len) {
    if (!eth_mac_has_rx()) return 0;

    uint16_t len = eth_mac_rx_len();
    if (len == 0) {
        eth_mac_rx_ack();
        return 0;
    }

    uint16_t copy_len = (len < max_len) ? len : max_len;
    volatile uint32_t *rx_ram = (volatile uint32_t *)(ETH_MAC_BASE + ETH_RX_RAM_OFFSET);
    uint32_t words = (copy_len + 3) / 4;

    for (uint32_t i = 0; i < words; i++) {
        uint32_t word = rx_ram[i];
        uint32_t b_offset = i * 4;
        for (int b = 0; b < 4; b++) {
            if (b_offset + b < copy_len) {
                buffer[b_offset + b] = (uint8_t)((word >> (b * 8)) & 0xFF);
            }
        }
    }

    /* Acknowledge packet reception to unlock RX buffer */
    eth_mac_rx_ack();

    return copy_len;
}
