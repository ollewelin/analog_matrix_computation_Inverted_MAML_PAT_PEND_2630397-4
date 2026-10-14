#include "t120_t20_bus.h"
#include <string.h>

#if __has_include("bsp.h")
#include "bsp.h"
#include "io.h"
#define BUS_WRITE_REG(addr, val) write_u32(val, addr)
#define BUS_READ_REG(addr)       read_u32(addr)
#define BUS_DELAY_US(us)         bsp_uDelay(us)
#else
#define BUS_WRITE_REG(addr, val) (*(volatile uint32_t*)(uintptr_t)(addr) = (val))
#define BUS_READ_REG(addr)       (*(volatile uint32_t*)(uintptr_t)(addr))
static inline void BUS_DELAY_US(uint32_t us) {
    volatile uint32_t count = us * 50;
    while (count--);
}
#endif

/* Register offsets in custom bus IP or GPIO bank:
 * 0x00: TX Data & Clock [bit 0: CLK, bits 4..1: TX[3:0]]
 * 0x04: RX Data [bits 7..0: RX[7:0]]
 */
#define BUS_REG_TX_CTRL     0x00
#define BUS_REG_RX_DATA     0x04

static uint32_t g_bus_base = 0;

void t120_t20_bus_init(uint32_t gpio_base) {
    g_bus_base = gpio_base;
    if (g_bus_base) {
        /* Set Clock low, TX low */
        BUS_WRITE_REG(g_bus_base + BUS_REG_TX_CTRL, 0x00);
    }
}

/* Transmit 4 bits over TX lines and generate 1 clock pulse on T20_CLK9 */
static void bus_tx_nibble(uint8_t nibble) {
    uint32_t val = ((uint32_t)(nibble & 0x0F) << 1);
    /* Clock LOW with data valid */
    BUS_WRITE_REG(g_bus_base + BUS_REG_TX_CTRL, val);
    BUS_DELAY_US(1);
    /* Clock HIGH (rising edge latches into T20) */
    BUS_WRITE_REG(g_bus_base + BUS_REG_TX_CTRL, val | 0x01);
    BUS_DELAY_US(1);
    /* Clock LOW */
    BUS_WRITE_REG(g_bus_base + BUS_REG_TX_CTRL, val);
}

/* Transmit 1 byte as high nibble then low nibble */
static void bus_tx_byte(uint8_t byte) {
    bus_tx_nibble((byte >> 4) & 0x0F);
    bus_tx_nibble(byte & 0x0F);
}

/* Sample 1 byte from 8-bit RX lines */
static uint8_t bus_rx_byte(void) {
    /* Pulse clock to let T20 advance */
    BUS_WRITE_REG(g_bus_base + BUS_REG_TX_CTRL, 0x01);
    BUS_DELAY_US(1);
    uint32_t raw = BUS_READ_REG(g_bus_base + BUS_REG_RX_DATA);
    BUS_WRITE_REG(g_bus_base + BUS_REG_TX_CTRL, 0x00);
    BUS_DELAY_US(1);
    return (uint8_t)(raw & 0xFF);
}

static uint16_t compute_crc16(const uint8_t *data, uint16_t len) {
    uint16_t crc = 0xFFFF;
    for (uint16_t i = 0; i < len; i++) {
        crc ^= (uint16_t)data[i] << 8;
        for (uint8_t b = 0; b < 8; b++) {
            if (crc & 0x8000) {
                crc = (crc << 1) ^ 0x1021;
            } else {
                crc = crc << 1;
            }
        }
    }
    return crc;
}

static t20_bus_status_t bus_send_packet(uint8_t opcode, const uint8_t *payload, uint16_t len) {
    if (g_bus_base == 0) return BUS_RESP_UNKNOWN_CMD;

    /* Preamble */
    bus_tx_byte(BUS_FRAME_PREAMBLE_H);
    bus_tx_byte(BUS_FRAME_PREAMBLE_L);

    /* Opcode */
    bus_tx_byte(opcode);

    /* Length (Big Endian) */
    bus_tx_byte((uint8_t)((len >> 8) & 0xFF));
    bus_tx_byte((uint8_t)(len & 0xFF));

    /* Payload */
    for (uint16_t i = 0; i < len; i++) {
        bus_tx_byte(payload[i]);
    }

    /* CRC16 */
    uint16_t crc = compute_crc16(payload, len);
    bus_tx_byte((uint8_t)((crc >> 8) & 0xFF));
    bus_tx_byte((uint8_t)(crc & 0xFF));

    /* Postamble */
    bus_tx_byte(BUS_FRAME_POSTAMBLE);

    return BUS_RESP_OK;
}

static t20_bus_status_t bus_await_ack(t20_bus_response_t *out_resp, uint32_t timeout_loops) {
    if (g_bus_base == 0) return BUS_RESP_TIMEOUT;

    uint8_t h0 = 0, h1 = 0;
    while (timeout_loops--) {
        h0 = bus_rx_byte();
        if (h0 == BUS_RESP_PREAMBLE_H) {
            h1 = bus_rx_byte();
            if (h1 == BUS_RESP_PREAMBLE_L) {
                break;
            }
        }
        BUS_DELAY_US(10);
    }

    if (timeout_loops == 0) {
        return BUS_RESP_TIMEOUT;
    }

    /* Read status */
    uint8_t status = bus_rx_byte();

    /* Read length */
    uint16_t resp_len = ((uint16_t)bus_rx_byte() << 8) | bus_rx_byte();

    if (out_resp) {
        out_resp->status = status;
        out_resp->length = resp_len;
        for (uint16_t i = 0; i < resp_len && i < sizeof(out_resp->payload); i++) {
            out_resp->payload[i] = bus_rx_byte();
        }
    } else {
        for (uint16_t i = 0; i < resp_len; i++) {
            (void)bus_rx_byte();
        }
    }

    /* Skip CRC & Postamble */
    (void)bus_rx_byte();
    (void)bus_rx_byte();
    (void)bus_rx_byte();

    return (t20_bus_status_t)status;
}

/* Task 1 Implementation: Reflash chunk */
t20_bus_status_t t120_t20_bus_reflash_chunk(uint32_t target_flash_addr, const uint8_t *data, uint16_t len) {
    uint8_t pkt_payload[260];
    pkt_payload[0] = (uint8_t)((target_flash_addr >> 16) & 0xFF);
    pkt_payload[1] = (uint8_t)((target_flash_addr >> 8) & 0xFF);
    pkt_payload[2] = (uint8_t)(target_flash_addr & 0xFF);

    uint16_t copy_len = (len > 256) ? 256 : len;
    memcpy(&pkt_payload[3], data, copy_len);

    t20_bus_status_t st = bus_send_packet(BUS_CMD_REFLASH_STREAM, pkt_payload, copy_len + 3);
    if (st != BUS_RESP_OK) return st;

    /* Await T20 flash programming Ack */
    return bus_await_ack(NULL, 10000);
}

/* Task 1 Implementation: Jump command */
t20_bus_status_t t120_t20_bus_reflash_jump(uint8_t app_slot) {
    uint8_t slot = app_slot;
    t20_bus_status_t st = bus_send_packet(BUS_CMD_REFLASH_FINISH, &slot, 1);
    if (st != BUS_RESP_OK) return st;

    return bus_await_ack(NULL, 5000);
}

/* Task 2 Implementation: Hadamard Table Run command and acknowledgment */
t20_bus_status_t t120_t20_bus_run_hadamard_table(uint8_t table_index, uint16_t num_steps, t20_bus_response_t *resp) {
    uint8_t cmd_buf[3];
    cmd_buf[0] = table_index;
    cmd_buf[1] = (uint8_t)((num_steps >> 8) & 0xFF);
    cmd_buf[2] = (uint8_t)(num_steps & 0xFF);

    t20_bus_status_t st = bus_send_packet(BUS_CMD_HADAMARD_RUN, cmd_buf, sizeof(cmd_buf));
    if (st != BUS_RESP_OK) return st;

    /* Await completion and acknowledgment from T20 */
    return bus_await_ack(resp, 20000);
}
