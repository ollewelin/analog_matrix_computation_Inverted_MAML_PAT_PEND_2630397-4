#include "ethernetif.h"
#include "eth_mac_100m.h"
#include "lwip/opt.h"
#include "lwip/def.h"
#include "lwip/mem.h"
#include "lwip/pbuf.h"
#include "lwip/stats.h"
#include "lwip/etharp.h"
#include "netif/ethernet.h"
#include <string.h>

#define IFNAME0 'e'
#define IFNAME1 't'

static err_t low_level_output(struct netif *netif, struct pbuf *p) {
    (void)netif;
    if (p->tot_len > 1514) {
        return ERR_BUF;
    }

    /* Wait if previous transmission is still in progress */
    uint32_t timeout = 50000;
    while (eth_mac_tx_busy() && --timeout);

    /* Direct copy into MAC TX buffer */
    volatile uint32_t *tx_ram = (volatile uint32_t *)(ETH_MAC_BASE + ETH_TX_RAM_OFFSET);
    uint16_t tot_len = p->tot_len;
    uint32_t word_idx = 0;
    uint32_t cur_word = 0;
    int byte_in_word = 0;

    for (struct pbuf *q = p; q != NULL; q = q->next) {
        const uint8_t *payload = (const uint8_t *)q->payload;
        for (uint16_t i = 0; i < q->len; i++) {
            cur_word |= ((uint32_t)payload[i]) << (byte_in_word * 8);
            byte_in_word++;
            if (byte_in_word == 4) {
                tx_ram[word_idx++] = cur_word;
                cur_word = 0;
                byte_in_word = 0;
            }
        }
    }
    if (byte_in_word > 0) {
        tx_ram[word_idx] = cur_word;
    }

    /* Set length and trigger start */
    *(volatile uint32_t *)(ETH_MAC_BASE + ETH_REG_TX_LEN) = tot_len;
    *(volatile uint32_t *)(ETH_MAC_BASE + ETH_REG_CTRL) |= ETH_CTRL_TX_START;

    return ERR_OK;
}

static struct pbuf *low_level_input(struct netif *netif) {
    (void)netif;
    if (!eth_mac_has_rx()) {
        return NULL;
    }

    uint16_t len = eth_mac_rx_len();
    if (len == 0 || len > 1514) {
        eth_mac_rx_ack();
        return NULL;
    }

    /* Allocate pbuf */
    struct pbuf *p = pbuf_alloc(PBUF_RAW, len, PBUF_POOL);
    if (p != NULL) {
        volatile uint32_t *rx_ram = (volatile uint32_t *)(ETH_MAC_BASE + ETH_RX_RAM_OFFSET);
        uint32_t word_idx = 0;
        uint32_t cur_word = 0;
        int byte_in_word = 4; // trigger initial load

        for (struct pbuf *q = p; q != NULL; q = q->next) {
            uint8_t *payload = (uint8_t *)q->payload;
            for (uint16_t i = 0; i < q->len; i++) {
                if (byte_in_word == 4) {
                    cur_word = rx_ram[word_idx++];
                    byte_in_word = 0;
                }
                payload[i] = (uint8_t)((cur_word >> (byte_in_word * 8)) & 0xFF);
                byte_in_word++;
            }
        }
    }

    /* Acknowledge reception to let hardware capture next packet */
    eth_mac_rx_ack();

    return p;
}

void ethernetif_input(struct netif *netif) {
    struct pbuf *p = low_level_input(netif);
    if (p != NULL) {
        if (netif->input(p, netif) != ERR_OK) {
            pbuf_free(p);
        }
    }
}

err_t ethernetif_init(struct netif *netif) {
    netif->name[0] = IFNAME0;
    netif->name[1] = IFNAME1;
    netif->output = etharp_output;
    netif->linkoutput = low_level_output;

    netif->mtu = 1500;
    netif->flags = NETIF_FLAG_BROADCAST | NETIF_FLAG_ETHARP | NETIF_FLAG_LINK_UP;

    eth_mac_init(netif->hwaddr);

    return ERR_OK;
}
