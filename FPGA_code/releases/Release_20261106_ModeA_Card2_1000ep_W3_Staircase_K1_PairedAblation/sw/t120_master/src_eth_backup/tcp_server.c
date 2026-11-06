#include "tcp_server.h"
#include <string.h>

#ifdef LWIP_ALTCP
#include "lwip/altcp.h"
#include "lwip/altcp_tcp.h"
#else
#include "lwip/tcp.h"
#endif

static struct tcp_pcb *server_pcb = NULL;
static struct tcp_pcb *active_client_pcb = NULL;
static tcp_cmd_handler_t global_cmd_handler = NULL;

static uint8_t rx_stream_buffer[TCP_SERVER_RX_BUF_SIZE];
static uint32_t rx_stream_len = 0;

static err_t tcp_server_recv_callback(void *arg, struct tcp_pcb *tpcb, struct pbuf *p, err_t err) {
    if (p == NULL) {
        /* Connection closed by client */
        tcp_close(tpcb);
        if (active_client_pcb == tpcb) {
            active_client_pcb = NULL;
        }
        return ERR_OK;
    }

    if (err != ERR_OK) {
        pbuf_free(p);
        return err;
    }

    /* Copy pbuf chain into local parsing buffer */
    struct pbuf *q;
    for (q = p; q != NULL; q = q->next) {
        if (rx_stream_len + q->len <= TCP_SERVER_RX_BUF_SIZE) {
            memcpy(&rx_stream_buffer[rx_stream_len], q->payload, q->len);
            rx_stream_len += q->len;
        }
    }

    /* Announce received data back to TCP window */
    tcp_recved(tpcb, p->tot_len);
    pbuf_free(p);

    /* Frame Parsing:
     * Header: [0xAA, 0x55] (2B)
     * Opcode: [1B]
     * Address: [4B] (Big Endian)
     * Length: [4B] (Big Endian)
     * Payload: [Length bytes]
     */
    while (rx_stream_len >= 11) {
        /* Check preamble */
        if (rx_stream_buffer[0] != 0xAA || rx_stream_buffer[1] != 0x55) {
            /* Shift buffer by 1 to re-align */
            memmove(&rx_stream_buffer[0], &rx_stream_buffer[1], rx_stream_len - 1);
            rx_stream_len--;
            continue;
        }

        uint8_t opcode = rx_stream_buffer[2];
        uint32_t addr = ((uint32_t)rx_stream_buffer[3] << 24) |
                        ((uint32_t)rx_stream_buffer[4] << 16) |
                        ((uint32_t)rx_stream_buffer[5] << 8)  |
                        ((uint32_t)rx_stream_buffer[6]);
        uint32_t data_len = ((uint32_t)rx_stream_buffer[7] << 24) |
                            ((uint32_t)rx_stream_buffer[8] << 16) |
                            ((uint32_t)rx_stream_buffer[9] << 8)  |
                            ((uint32_t)rx_stream_buffer[10]);

        uint32_t full_frame_size = 11 + data_len;
        if (rx_stream_len < full_frame_size) {
            /* Incomplete frame, wait for more data */
            break;
        }

        /* Complete frame found */
        if (global_cmd_handler) {
            tcp_command_t cmd;
            cmd.opcode = opcode;
            cmd.target_addr = addr;
            cmd.data_len = data_len;
            cmd.payload = &rx_stream_buffer[11];
            global_cmd_handler(&cmd);
        }

        /* Consume processed frame */
        if (rx_stream_len > full_frame_size) {
            memmove(&rx_stream_buffer[0], &rx_stream_buffer[full_frame_size], rx_stream_len - full_frame_size);
        }
        rx_stream_len -= full_frame_size;
    }

    return ERR_OK;
}

static err_t tcp_server_accept_callback(void *arg, struct tcp_pcb *newpcb, err_t err) {
    if (err != ERR_OK || newpcb == NULL) {
        return ERR_VAL;
    }

    active_client_pcb = newpcb;
    rx_stream_len = 0;

    tcp_recv(newpcb, tcp_server_recv_callback);
    return ERR_OK;
}

int tcp_server_init(tcp_cmd_handler_t handler) {
    global_cmd_handler = handler;

    server_pcb = tcp_new();
    if (!server_pcb) {
        return -1;
    }

    err_t err = tcp_bind(server_pcb, IP_ADDR_ANY, TCP_SERVER_PORT);
    if (err != ERR_OK) {
        tcp_close(server_pcb);
        server_pcb = NULL;
        return -2;
    }

    server_pcb = tcp_listen(server_pcb);
    if (!server_pcb) {
        return -3;
    }

    tcp_accept(server_pcb, tcp_server_accept_callback);
    return 0;
}

#include "bsp.h"
#include "lwip/timeouts.h"
#include "ethernetif.h"

extern struct netif g_netif;

u32_t sys_now(void) {
    /* CLINT timer runs at 50 MHz (50,000 cycles per millisecond) */
    uint32_t lo = clint_getTimeLow(BSP_CLINT);
    return lo / 50000;
}

void tcp_server_poll(void) {
    /* Poll Ethernet MAC for incoming frames and pass to lwIP */
    ethernetif_input(&g_netif);

    /* Process periodic lwIP timers (TCP retransmissions, ACK delays, 2MSL) */
    sys_check_timeouts();
}

int tcp_server_send_response(const uint8_t *data, uint16_t len) {
    if (!active_client_pcb || !data || len == 0) {
        return -1;
    }

    err_t err = tcp_write(active_client_pcb, data, len, TCP_WRITE_FLAG_COPY);
    if (err != ERR_OK) {
        return -2;
    }

    tcp_output(active_client_pcb);
    return (int)len;
}
