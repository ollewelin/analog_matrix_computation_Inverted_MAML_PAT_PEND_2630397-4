#ifndef FLASH_WRITER_H
#define FLASH_WRITER_H

#include <stdint.h>
#include <stdbool.h>

#define FLASH_SECTOR_SIZE       4096    /* 4 KB sector erase requirement */
#define FLASH_PAGE_SIZE         256     /* Standard SPI Flash page write */

/* Standard SPI Flash Command Opcodes */
#define SPI_FLASH_CMD_WREN      0x06    /* Write Enable */
#define SPI_FLASH_CMD_WRDI      0x04    /* Write Disable */
#define SPI_FLASH_CMD_RDSR      0x05    /* Read Status Register */
#define SPI_FLASH_CMD_READ      0x03    /* Read Data (24-bit address) */
#define SPI_FLASH_CMD_PP        0x02    /* Page Program (24-bit address) */
#define SPI_FLASH_CMD_SE        0x20    /* Sector Erase (4 KB, 24-bit address) */
#define SPI_FLASH_CMD_RDID      0x9F    /* Read JEDEC ID */

#define FLASH_STATUS_WIP_BIT    0x01    /* Write In Progress mask */

/**
 * @brief Initialize SPI peripheral for flash communication.
 * @param spi_base Base address of the SPI master peripheral.
 * @param cs_index Chip select line index (typically 0).
 */
void flash_writer_init(uint32_t spi_base, uint32_t cs_index);

/**
 * @brief Read JEDEC manufacturer and memory ID.
 * @return 24-bit JEDEC identifier.
 */
uint32_t flash_writer_read_id(void);

/**
 * @brief Erase a 4 KB sector enforcing 4 KB boundary alignment and 24-bit addressing.
 * @param addr 24-bit start address within the target sector (must be 4096-aligned).
 * @return 0 on success, negative error code on misaligned address or timeout.
 */
int flash_writer_erase_sector_4k(uint32_t addr);

/**
 * @brief Program a 256-byte page into SPI Flash.
 * @param addr 24-bit page start address.
 * @param data Buffer containing up to 256 bytes.
 * @param len Length in bytes (max 256).
 * @return Number of bytes written or negative error.
 */
int flash_writer_program_page(uint32_t addr, const uint8_t *data, uint16_t len);

/**
 * @brief Erase and write multi-sector payload enforcing 4 KB alignment and 24-bit addressing.
 * @param target_addr 24-bit destination address in SPI flash.
 * @param data Pointer to bitstream payload buffer.
 * @param len Total length in bytes.
 * @return 0 on success, negative error code on failure.
 */
int flash_writer_write_image(uint32_t target_addr, const uint8_t *data, uint32_t len);

/**
 * @brief Read back and verify bytes from flash.
 * @param addr 24-bit address in SPI flash.
 * @param expected Data buffer to compare against.
 * @param len Length in bytes.
 * @return 0 if matched, -1 if mismatch.
 */
int flash_writer_verify(uint32_t addr, const uint8_t *expected, uint32_t len);

#endif /* FLASH_WRITER_H */
