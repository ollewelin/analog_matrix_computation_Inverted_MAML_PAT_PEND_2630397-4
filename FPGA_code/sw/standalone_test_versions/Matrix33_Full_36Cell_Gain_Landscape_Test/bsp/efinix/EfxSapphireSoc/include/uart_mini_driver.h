/**
 * uart_mini_driver.h - C driver interface for uart_mini APB3 peripheral
 * 
 * Register Base Address: IO_APB_SLAVE_0_INPUT + 0x0000 (from soc.h)
 * This peripheral is at the first offset of the APB3 slave bus
 */

#ifndef UART_MINI_DRIVER_H
#define UART_MINI_DRIVER_H

#include <stdint.h>
#include <stdio.h>

// Base address for uart_mini APB3 slave - at start of APB3 slave 0 space
#define UART_MINI_BASE_ADDR  0xf8100000

// Register offsets
#define UART_CTRL_REG        0x00
#define UART_STATUS_REG      0x04
#define UART_TX_DATA_REG     0x08
#define UART_RX_DATA_REG     0x0C
#define UART_RX_CTRL_REG     0x10

// Status register bit definitions
#define UART_STATUS_TX_EMPTY (1 << 0)
#define UART_STATUS_TX_FULL  (1 << 1)
#define UART_STATUS_RX_EMPTY (1 << 2)
#define UART_STATUS_RX_FULL  (1 << 3)

/**
 * uart_mini_init() - Initialize UART mini peripheral
 * (Currently no-op as uart_mini initializes automatically)
 */
static inline void uart_mini_init(void)
{
    // uart_mini auto-initializes, nothing needed here
}

/**
 * uart_mini_get_status() - Read UART status register
 * 
 * Returns: 8-bit status with flags:
 *   [0] tx_empty - TX FIFO is empty
 *   [1] tx_full  - TX FIFO is full
 *   [2] rx_empty - RX FIFO is empty
 *   [3] rx_full  - RX FIFO is full
 */
static inline uint8_t uart_mini_get_status(void)
{
    volatile uint32_t *status_reg = (volatile uint32_t *)(UART_MINI_BASE_ADDR + UART_STATUS_REG);
    return (uint8_t)(*status_reg & 0xFF);
}

/**
 * uart_mini_tx_ready() - Check if TX FIFO has space
 * 
 * Returns: 1 if TX FIFO is not full, 0 otherwise
 */
static inline int uart_mini_tx_ready(void)
{
    return !(uart_mini_get_status() & UART_STATUS_TX_FULL);
}

/**
 * uart_mini_rx_available() - Check if RX FIFO has data
 * 
 * Returns: 1 if RX FIFO is not empty, 0 otherwise
 */
static inline int uart_mini_rx_available(void)
{
    return !(uart_mini_get_status() & UART_STATUS_RX_EMPTY);
}

/**
 * uart_mini_tx_byte() - Write one byte to TX FIFO (non-blocking)
 * 
 * @data: Byte to transmit
 * Returns: 1 if written successfully, 0 if TX FIFO full
 */
static inline int uart_mini_tx_byte(uint8_t data)
{
    if (!uart_mini_tx_ready())
        return 0;  // TX FIFO full
    
    volatile uint32_t *tx_data_reg = (volatile uint32_t *)(UART_MINI_BASE_ADDR + UART_TX_DATA_REG);
    *tx_data_reg = (uint32_t)data;  // Write triggers tx_write strobe
    
    return 1;
}

/**
 * uart_mini_rx_byte() - Read one byte from RX FIFO (non-blocking)
 * 
 * @data: Pointer to store received byte
 * Returns: 1 if byte read successfully, 0 if RX FIFO empty
 */
static inline int uart_mini_rx_byte(uint8_t *data)
{
    if (!uart_mini_rx_available())
        return 0;  // RX FIFO empty
    
    volatile uint32_t *rx_data_reg = (volatile uint32_t *)(UART_MINI_BASE_ADDR + UART_RX_DATA_REG);
    *data = (uint8_t)(*rx_data_reg & 0xFF);
    
    // Strobe rx_read to pop from FIFO
    volatile uint32_t *rx_ctrl_reg = (volatile uint32_t *)(UART_MINI_BASE_ADDR + UART_RX_CTRL_REG);
    *rx_ctrl_reg = 0x01;  // rx_read = 1
    
    return 1;
}

/**
 * uart_mini_tx_byte_blocking() - Write one byte, blocking until TX FIFO has space
 * 
 * @data: Byte to transmit
 */
static inline void uart_mini_tx_byte_blocking(uint8_t data)
{
    while (!uart_mini_tx_byte(data)) {
        // Spin until TX FIFO has space
    }
}

/**
 * uart_mini_rx_byte_blocking() - Read one byte, blocking until data available
 * 
 * Returns: Received byte
 */
static inline uint8_t uart_mini_rx_byte_blocking(void)
{
    uint8_t data;
    while (!uart_mini_rx_byte(&data)) {
        // Spin until RX FIFO has data
    }
    return data;
}

/**
 * uart_mini_tx_string() - Transmit a null-terminated string (blocking)
 * 
 * @str: Pointer to string to transmit
 */
static inline void uart_mini_tx_string(const char *str)
{
    while (*str) {
        uart_mini_tx_byte_blocking((uint8_t)*str);
        str++;
    }
}

/**
 * uart_mini_print_hex8() - Print 8-bit value as 2-digit hex
 */
static inline void uart_mini_print_hex8(uint8_t val)
{
    const char hex[] = "0123456789ABCDEF";
    uart_mini_tx_byte_blocking(hex[(val >> 4) & 0xF]);
    uart_mini_tx_byte_blocking(hex[val & 0xF]);
}

/**
 * uart_mini_print_hex16() - Print 16-bit value as 4-digit hex
 */
static inline void uart_mini_print_hex16(uint16_t val)
{
    uart_mini_print_hex8((val >> 8) & 0xFF);
    uart_mini_print_hex8(val & 0xFF);
}

/**
 * uart_mini_print_hex32() - Print 32-bit value as 8-digit hex
 */
static inline void uart_mini_print_hex32(uint32_t val)
{
    uart_mini_print_hex16((val >> 16) & 0xFFFF);
    uart_mini_print_hex16(val & 0xFFFF);
}

/**
 * uart_mini_newline() - Print CR+LF
 */
static inline void uart_mini_newline(void)
{
    uart_mini_tx_byte_blocking('\r');
    uart_mini_tx_byte_blocking('\n');
}

#endif // UART_MINI_DRIVER_H
