#include <stdint.h>
#include "bsp.h"
#include "gpio.h"
#include "uart_mini_driver.h"

void main(void) {
    gpio_setOutputEnable(SYSTEM_GPIO_0_IO_CTRL, 0x3);

    while (1) {
        // Tänd LED2 och skicka telemetry via UART Mini (Pin F13)
        gpio_setOutput(SYSTEM_GPIO_0_IO_CTRL, 0x1);
        uart_mini_tx_string("U");
        bsp_uDelay(300000);

        // Släck LED2
        gpio_setOutput(SYSTEM_GPIO_0_IO_CTRL, 0x0);
        bsp_uDelay(300000);
    }
}
