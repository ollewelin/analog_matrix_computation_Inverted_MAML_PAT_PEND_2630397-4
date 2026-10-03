#include <stdint.h>

#define GPIO_BASE          0xF800D000UL
#define GPIO_OUTPUT_REG    (*(volatile uint32_t*)(GPIO_BASE + 0x04))
#define GPIO_OE_REG        (*(volatile uint32_t*)(GPIO_BASE + 0x08))

static inline void delay_loop(uint32_t count) {
    __asm__ volatile (
        "1: addi %0, %0, -1\n"
        "   bnez %0, 1b\n"
        : "+r" (count)
    );
}

int main(void) {
    /* Set GPIO pins [3:0] as outputs */
    GPIO_OE_REG = 0x0F;

    while (1) {
        /* LED ON (Pin 0 = 1) - ~0.5 second at measured 1 MHz loop rate */
        GPIO_OUTPUT_REG = 0x01;
        delay_loop(500000);

        /* LED OFF (Pin 0 = 0) - ~0.5 second */
        GPIO_OUTPUT_REG = 0x00;
        delay_loop(500000);
    }

    return 0;
}
