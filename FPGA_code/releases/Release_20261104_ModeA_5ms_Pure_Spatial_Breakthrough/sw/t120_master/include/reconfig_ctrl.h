#ifndef RECONFIG_CTRL_H
#define RECONFIG_CTRL_H

#include <stdint.h>
#include <stdbool.h>

/**
 * Efinix AN 010 Reconfiguration Interface Definitions:
 * Signals:
 * - <instance>_CBSEL[1:0]: Multi-image select lines
 *       2'b00 = Flash Image 0 (Golden Image @ 0x000000)
 *       2'b01 = Flash Image 1 (Application Image 1 @ e.g. 0x100000)
 *       2'b10 = Flash Image 2
 *       2'b11 = Flash Image 3
 * - <instance>_ENA: When high, latches the value of CBSEL on CLK edge.
 * - <instance>_CONFIG: Asynchronous pulse initiates internal reconfiguration.
 * - <instance>_ERROR: Status output. 0 = Success / normal. 1 = Reconfiguration failed (CRC error).
 */

typedef enum {
    RECONFIG_IMAGE_GOLDEN = 0,
    RECONFIG_IMAGE_APP1   = 1,
    RECONFIG_IMAGE_APP2   = 2,
    RECONFIG_IMAGE_APP3   = 3
} reconfig_image_select_t;

/**
 * @brief Initialize the hardware reconfiguration controller GPIO / MMIO registers.
 * @param ctrl_base Memory mapped base address of the reconfiguration register block.
 */
void reconfig_ctrl_init(uint32_t ctrl_base);

/**
 * @brief Check if configuration error occurred (<instance>_ERROR is high).
 * @return true if error flag is set, false otherwise.
 */
bool reconfig_ctrl_has_error(void);

/**
 * @brief Execute the hardware internal reconfiguration sequence per Efinix AN 010.
 *        1. Present target image index on <instance>_CBSEL[1:0].
 *        2. Assert <instance>_ENA high.
 *        3. Assert <instance>_CONFIG high to trigger reconfiguration.
 * @param image_idx Target image (e.g. RECONFIG_IMAGE_APP1).
 */
void reconfig_ctrl_trigger(reconfig_image_select_t image_idx);

/**
 * @brief Toggle T20 hardware CRESET_N pin to force fallback to Golden Image.
 *        Pulls low for >= 10 ms and releases high.
 * @param creset_gpio_base Base address of GPIO controlling CRESET_N line.
 * @param pin_index Bit index corresponding to CRESET_N.
 */
void reconfig_t20_hardware_reset(uint32_t creset_gpio_base, uint8_t pin_index);

#endif /* RECONFIG_CTRL_H */
