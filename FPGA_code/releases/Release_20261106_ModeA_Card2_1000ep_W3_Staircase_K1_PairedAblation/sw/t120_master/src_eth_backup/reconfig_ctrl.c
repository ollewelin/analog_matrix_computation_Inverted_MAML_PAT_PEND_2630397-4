#include "reconfig_ctrl.h"

#if __has_include("bsp.h")
#include "bsp.h"
#include "io.h"
#define RECONFIG_WRITE_REG(addr, val) write_u32(val, addr)
#define RECONFIG_READ_REG(addr)       read_u32(addr)
#define RECONFIG_DELAY_US(us)         bsp_uDelay(us)
#else
#define RECONFIG_WRITE_REG(addr, val) (*(volatile uint32_t*)(uintptr_t)(addr) = (val))
#define RECONFIG_READ_REG(addr)       (*(volatile uint32_t*)(uintptr_t)(addr))
static inline void RECONFIG_DELAY_US(uint32_t us) {
    volatile uint32_t count = us * 50;
    while (count--);
}
#endif

/* Register offsets within reconfiguration IP wrapper */
#define REG_RECONFIG_CTRL       0x00
#define REG_RECONFIG_STATUS     0x04

#define BIT_CFG_CBSEL_OFFSET    0
#define BIT_CFG_CBSEL_MASK      (0x3 << BIT_CFG_CBSEL_OFFSET)
#define BIT_CFG_ENA             (1 << 2)
#define BIT_CFG_CONFIG          (1 << 3)
#define BIT_CFG_ERROR           (1 << 0)

static uint32_t g_reconfig_base = 0;

void reconfig_ctrl_init(uint32_t ctrl_base) {
    g_reconfig_base = ctrl_base;
    /* Initialize control signals to low */
    RECONFIG_WRITE_REG(g_reconfig_base + REG_RECONFIG_CTRL, 0);
}

bool reconfig_ctrl_has_error(void) {
    if (g_reconfig_base == 0) return false;
    uint32_t status = RECONFIG_READ_REG(g_reconfig_base + REG_RECONFIG_STATUS);
    return (status & BIT_CFG_ERROR) != 0;
}

void reconfig_ctrl_trigger(reconfig_image_select_t image_idx) {
    if (g_reconfig_base == 0) return;

    /* Step 1: Present CBSEL value */
    uint32_t reg_val = ((uint32_t)image_idx & 0x03) << BIT_CFG_CBSEL_OFFSET;
    RECONFIG_WRITE_REG(g_reconfig_base + REG_RECONFIG_CTRL, reg_val);
    RECONFIG_DELAY_US(10);

    /* Step 2: Hold <instance>_ENA high to latch CBSEL on clock edge */
    reg_val |= BIT_CFG_ENA;
    RECONFIG_WRITE_REG(g_reconfig_base + REG_RECONFIG_CTRL, reg_val);
    RECONFIG_DELAY_US(20);

    /* Step 3: Assert <instance>_CONFIG high to initiate reconfiguration */
    reg_val |= BIT_CFG_CONFIG;
    RECONFIG_WRITE_REG(g_reconfig_base + REG_RECONFIG_CTRL, reg_val);
    RECONFIG_DELAY_US(50);

    /* Return to idle */
    RECONFIG_WRITE_REG(g_reconfig_base + REG_RECONFIG_CTRL, 0);
}

void reconfig_t20_hardware_reset(uint32_t creset_gpio_base, uint8_t pin_index) {
    if (creset_gpio_base == 0) return;

    /* Pull CRESET_N LOW */
    uint32_t current = RECONFIG_READ_REG(creset_gpio_base);
    current &= ~(1 << pin_index);
    RECONFIG_WRITE_REG(creset_gpio_base, current);

    /* Hold low for at least 10 ms (Efinix AN 006 spec: >= 10 ms) */
    RECONFIG_DELAY_US(15000);

    /* Release CRESET_N HIGH */
    current |= (1 << pin_index);
    RECONFIG_WRITE_REG(creset_gpio_base, current);

    /* Allow T20 internal configuration sequence to complete */
    RECONFIG_DELAY_US(50000);
}
