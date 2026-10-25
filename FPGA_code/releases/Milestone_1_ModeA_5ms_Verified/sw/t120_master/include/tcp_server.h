#ifndef TCP_SERVER_H
#define TCP_SERVER_H

#include <stdint.h>
#include <stdbool.h>

#define TCP_SERVER_PORT         8080
#define TCP_SERVER_RX_BUF_SIZE  4096

typedef enum {
    CMD_OP_UPDATE = 0x01,
    CMD_OP_JUMP   = 0x02,
    CMD_OP_STATUS = 0x03
} tcp_cmd_opcode_t;

typedef struct {
    uint8_t opcode;
    uint32_t target_addr;
    uint32_t data_len;
    const uint8_t *payload;
} tcp_command_t;

typedef void (*tcp_cmd_handler_t)(const tcp_command_t *cmd);

/**
 * @brief Initialize lwIP TCP server listening on TCP_SERVER_PORT (8080).
 * @param handler Callback invoked when a validated command frame arrives.
 * @return 0 on success, negative error code on failure.
 */
int tcp_server_init(tcp_cmd_handler_t handler);

/**
 * @brief Poll the TCP server and lwIP stack for incoming packets (if not using RTOS).
 */
void tcp_server_poll(void);

/**
 * @brief Send response buffer back to currently connected client.
 * @param data Pointer to response byte buffer.
 * @param len Length in bytes.
 * @return Number of bytes queued or negative on error.
 */
int tcp_server_send_response(const uint8_t *data, uint16_t len);

#endif /* TCP_SERVER_H */
