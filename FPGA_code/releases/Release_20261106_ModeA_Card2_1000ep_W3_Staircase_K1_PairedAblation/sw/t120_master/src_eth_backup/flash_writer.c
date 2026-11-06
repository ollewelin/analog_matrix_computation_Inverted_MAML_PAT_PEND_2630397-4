#include "flash_writer.h"
#include <string.h>

/* Low-level SPI abstraction hooks (compatible with Sapphire SoC spi.h or standalone HAL) */
#if __has_include("spi.h")
#include "spi.h"
#include "bsp.h"
#define HAL_SPI_SELECT(base, cs)    spi_select(base, cs)
#define HAL_SPI_DESELECT(base, cs)  spi_diselect(base, cs)
#define HAL_SPI_WRITE(base, byte)   spi_write(base, byte)
#define HAL_SPI_READ(base)          spi_read(base)
#define HAL_DELAY_US(us)            bsp_uDelay(us)
#else
/* Fallback register-level or simulator stub */
static inline void HAL_SPI_SELECT(uint32_t b, uint32_t c) { (void)b; (void)c; }
static inline void HAL_SPI_DESELECT(uint32_t b, uint32_t c) { (void)b; (void)c; }
static inline void HAL_SPI_WRITE(uint32_t b, uint8_t v) { (void)b; (void)v; }
static inline uint8_t HAL_SPI_READ(uint32_t b) { (void)b; return 0x00; }
static inline void HAL_DELAY_US(uint32_t us) { volatile uint32_t count = us * 50; while(count--); }
#endif

static uint32_t g_spi_base = 0;
static uint32_t g_cs_index = 0;

void flash_writer_init(uint32_t spi_base, uint32_t cs_index) {
    g_spi_base = spi_base;
    g_cs_index = cs_index;
}

static void flash_write_enable(void) {
    HAL_SPI_SELECT(g_spi_base, g_cs_index);
    HAL_SPI_WRITE(g_spi_base, SPI_FLASH_CMD_WREN);
    HAL_SPI_DESELECT(g_spi_base, g_cs_index);
}

static uint8_t flash_read_status(void) {
    HAL_SPI_SELECT(g_spi_base, g_cs_index);
    HAL_SPI_WRITE(g_spi_base, SPI_FLASH_CMD_RDSR);
    uint8_t status = HAL_SPI_READ(g_spi_base);
    HAL_SPI_DESELECT(g_spi_base, g_cs_index);
    return status;
}

static int flash_wait_ready(uint32_t timeout_loops) {
    while (timeout_loops--) {
        uint8_t status = flash_read_status();
        if ((status & FLASH_STATUS_WIP_BIT) == 0) {
            return 0;
        }
        HAL_DELAY_US(100);
    }
    return -1; /* Timeout */
}

uint32_t flash_writer_read_id(void) {
    HAL_SPI_SELECT(g_spi_base, g_cs_index);
    HAL_SPI_WRITE(g_spi_base, SPI_FLASH_CMD_RDID);
    uint32_t id = 0;
    id |= ((uint32_t)HAL_SPI_READ(g_spi_base)) << 16;
    id |= ((uint32_t)HAL_SPI_READ(g_spi_base)) << 8;
    id |= ((uint32_t)HAL_SPI_READ(g_spi_base));
    HAL_SPI_DESELECT(g_spi_base, g_cs_index);
    return id;
}

int flash_writer_erase_sector_4k(uint32_t addr) {
    /* Enforce 4KB sector boundary alignment */
    if (addr & (FLASH_SECTOR_SIZE - 1)) {
        return -1; /* Misaligned address */
    }

    flash_write_enable();

    HAL_SPI_SELECT(g_spi_base, g_cs_index);
    HAL_SPI_WRITE(g_spi_base, SPI_FLASH_CMD_SE);
    /* 24-bit address serialization */
    HAL_SPI_WRITE(g_spi_base, (uint8_t)((addr >> 16) & 0xFF));
    HAL_SPI_WRITE(g_spi_base, (uint8_t)((addr >> 8) & 0xFF));
    HAL_SPI_WRITE(g_spi_base, (uint8_t)(addr & 0xFF));
    HAL_SPI_DESELECT(g_spi_base, g_cs_index);

    /* Sector erase typically takes 30-100 ms */
    return flash_wait_ready(5000);
}

int flash_writer_program_page(uint32_t addr, const uint8_t *data, uint16_t len) {
    if (len > FLASH_PAGE_SIZE) {
        len = FLASH_PAGE_SIZE;
    }

    flash_write_enable();

    HAL_SPI_SELECT(g_spi_base, g_cs_index);
    HAL_SPI_WRITE(g_spi_base, SPI_FLASH_CMD_PP);
    /* 24-bit address serialization */
    HAL_SPI_WRITE(g_spi_base, (uint8_t)((addr >> 16) & 0xFF));
    HAL_SPI_WRITE(g_spi_base, (uint8_t)((addr >> 8) & 0xFF));
    HAL_SPI_WRITE(g_spi_base, (uint8_t)(addr & 0xFF));

    for (uint16_t i = 0; i < len; i++) {
        HAL_SPI_WRITE(g_spi_base, data[i]);
    }
    HAL_SPI_DESELECT(g_spi_base, g_cs_index);

    return flash_wait_ready(1000);
}

int flash_writer_write_image(uint32_t target_addr, const uint8_t *data, uint32_t len) {
    /* Validate 4 KB sector alignment */
    if (target_addr & (FLASH_SECTOR_SIZE - 1)) {
        return -1;
    }

    uint32_t num_sectors = (len + FLASH_SECTOR_SIZE - 1) / FLASH_SECTOR_SIZE;

    /* 1. Sector erase loop */
    for (uint32_t s = 0; s < num_sectors; s++) {
        uint32_t sector_addr = target_addr + (s * FLASH_SECTOR_SIZE);
        if (flash_writer_erase_sector_4k(sector_addr) != 0) {
            return -2; /* Erase failure */
        }
    }

    /* 2. Page programming loop */
    uint32_t bytes_written = 0;
    while (bytes_written < len) {
        uint32_t page_addr = target_addr + bytes_written;
        uint16_t chunk = (len - bytes_written > FLASH_PAGE_SIZE) ? 
                          FLASH_PAGE_SIZE : (uint16_t)(len - bytes_written);

        if (flash_writer_program_page(page_addr, &data[bytes_written], chunk) != 0) {
            return -3; /* Programming failure */
        }
        bytes_written += chunk;
    }

    return 0;
}

int flash_writer_verify(uint32_t addr, const uint8_t *expected, uint32_t len) {
    HAL_SPI_SELECT(g_spi_base, g_cs_index);
    HAL_SPI_WRITE(g_spi_base, SPI_FLASH_CMD_READ);
    /* 24-bit address */
    HAL_SPI_WRITE(g_spi_base, (uint8_t)((addr >> 16) & 0xFF));
    HAL_SPI_WRITE(g_spi_base, (uint8_t)((addr >> 8) & 0xFF));
    HAL_SPI_WRITE(g_spi_base, (uint8_t)(addr & 0xFF));

    for (uint32_t i = 0; i < len; i++) {
        uint8_t val = HAL_SPI_READ(g_spi_base);
        if (val != expected[i]) {
            HAL_SPI_DESELECT(g_spi_base, g_cs_index);
            return -1; /* Data mismatch */
        }
    }

    HAL_SPI_DESELECT(g_spi_base, g_cs_index);
    return 0; /* Verified matched */
}
