#ifndef T120_T20_BUS_H
#define T120_T20_BUS_H

#include <stdint.h>
#include <stdbool.h>

/**
 * T120 <-> T20 Bus Pinout Reference (pinout_T120_T20.md):
 * - Clock: T20_CLK9 (T120 drives bus clock)
 * - TX: 4 bits (TX11_P1, TX11_N1, TX12_P1, TX12_N1) - T120 -> T20
 * - RX: 8 bits (RX00_P1/N1 .. RX03_P1/N1) - T20 -> T120
 */

/* Bus Framing Constants */
#define BUS_FRAME_PREAMBLE_H    0xAA
#define BUS_FRAME_PREAMBLE_L    0x55
#define BUS_FRAME_POSTAMBLE     0x7E

#define BUS_RESP_PREAMBLE_H     0x55
#define BUS_RESP_PREAMBLE_L     0xAA

/* Opcodes for the 2 primary tasks */
typedef enum {
    BUS_CMD_REFLASH_STREAM  = 0x01,  /* Task 1: Stream bitstream payload chunk to T20 for reflashing */
    BUS_CMD_REFLASH_FINISH  = 0x02,  /* Task 1: Signal flashing complete & trigger jump to App image */
    BUS_CMD_HADAMARD_RUN    = 0x10,  /* Task 2: Trigger Hadamard table run on analog matrix */
    BUS_CMD_PING            = 0x00   /* Bus connectivity check */
} t20_bus_cmd_t;

/* Response status codes from T20 */
typedef enum {
    BUS_RESP_OK             = 0x00,
    BUS_RESP_BUSY           = 0x01,
    BUS_RESP_CRC_ERR        = 0x02,
    BUS_RESP_FLASH_ERR      = 0x03,
    BUS_RESP_TIMEOUT        = 0xFE,
    BUS_RESP_UNKNOWN_CMD    = 0xFF
} t20_bus_status_t;

typedef struct {
    uint8_t  status;
    uint16_t length;
    uint8_t  payload[64];
} t20_bus_response_t;

/**
 * @brief Initialize T120 hardware bus controller registers.
 * @param gpio_base Base address of GPIO / Custom APB peripheral for bus pins.
 */
void t120_t20_bus_init(uint32_t gpio_base);

/**
 * @brief Task 1: Send a reflash payload chunk across the bus to T20.
 * @param target_flash_addr 24-bit flash address where T20 should program chunk.
 * @param data Pointer to bitstream payload buffer.
 * @param len Chunk length (up to 256 bytes).
 * @return BUS_RESP_OK on success, or error status.
 */
t20_bus_status_t t120_t20_bus_reflash_chunk(uint32_t target_flash_addr, const uint8_t *data, uint16_t len);

/**
 * @brief Task 1: Finish reflashing and command T20 to trigger internal reconfiguration (jump).
 * @param app_slot 1 for Application Image 1.
 * @return BUS_RESP_OK on success, or error status.
 */
t20_bus_status_t t120_t20_bus_reflash_jump(uint8_t app_slot);

/**
 * @brief Task 2: Transmit Hadamard table run command to T20 and await acknowledgment.
 * @param table_index Index of the Hadamard / Walsh pattern sequence to apply.
 * @param num_steps Number of perturbation steps / rows to modulate.
 * @param resp Output buffer to receive acknowledgment and any raw data telemetry.
 * @return BUS_RESP_OK when acknowledged by T20, or error status.
 */
t20_bus_status_t t120_t20_bus_run_hadamard_table(uint8_t table_index, uint16_t num_steps, t20_bus_response_t *resp);

#endif /* T120_T20_BUS_H */
