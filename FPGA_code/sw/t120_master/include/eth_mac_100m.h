#ifndef ETH_MAC_100M_H
#define ETH_MAC_100M_H

#include <stdint.h>
#include <stdbool.h>

#define ETH_MAC_BASE        0xF8102000UL

/* Register offsets */
#define ETH_REG_CTRL        0x00
#define ETH_REG_STATUS      0x04
#define ETH_REG_TX_LEN      0x08
#define ETH_REG_RX_LEN      0x0C
#define ETH_REG_MAC_LO      0x10
#define ETH_REG_MAC_HI      0x14
#define ETH_REG_TX_CNT      0x18
#define ETH_REG_RX_CNT      0x1C

/* Buffer offsets */
#define ETH_TX_RAM_OFFSET   0x080
#define ETH_RX_RAM_OFFSET   0x800

/* Control bits */
#define ETH_CTRL_TX_START   (1 << 0)
#define ETH_CTRL_RX_ACK     (1 << 1)
#define ETH_CTRL_PROMISC    (1 << 2)
#define ETH_CTRL_LOOPBACK   (1 << 3)

/* Status bits */
#define ETH_STATUS_TX_BUSY  (1 << 0)
#define ETH_STATUS_RX_READY (1 << 1)
#define ETH_STATUS_LINK_UP  (1 << 2)
#define ETH_STATUS_CRC_ERR  (1 << 3)

void eth_mac_init(const uint8_t mac_addr[6]);
bool eth_mac_is_link_up(void);
bool eth_mac_tx_busy(void);
void eth_mac_send(const uint8_t *frame, uint16_t length);
bool eth_mac_has_rx(void);
uint16_t eth_mac_rx_len(void);
uint16_t eth_mac_recv(uint8_t *buffer, uint16_t max_len);
void eth_mac_rx_ack(void);

#endif /* ETH_MAC_100M_H */
