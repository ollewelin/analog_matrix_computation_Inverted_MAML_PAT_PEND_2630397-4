#ifndef T120_BRIDGE_REGS_H
#define T120_BRIDGE_REGS_H

/* T120 <-> T20 bridge registers (APB3). Spec: FPGA_code/docs/t120_t20_bridge_spec.md
 * Hadamard (H-bus) runs entirely in hardware: C code only loads the table, sets
 * count/period and writes H_CTRL.start. Never put Hadamard timing into C code. */

#define T20_BRIDGE_BASE      0xF8103000u
#define T20_REG(off)         (*(volatile uint32_t *)(T20_BRIDGE_BASE + (off)))

#define T20_ID               0x000
#define T20_CTRL             0x004   /* [0] clk_en [1] manual [10:8] rx_dly */
#define T20_CLK_PERIOD       0x008   /* sys_clk cycles per CLK9 period (5=10 MHz) */
#define T20_MANUAL           0x00C   /* [0] clk9 [4:1] tx[3:0] */
#define T20_RX_PINS          0x010
#define T20_CRESET_CTRL      0x014   /* [0] level (1=release) W1:[1] pulse RO:[8] busy */
#define T20_CRESET_US        0x018
#define T20_IRQ_EN           0x01C
#define T20_IRQ_STATUS       0x020

#define T20_S_CTRL           0x040   /* W1: [0] tx_start [1] rx_release [2] clr_status; RW: [3] no_ack [4] auto_creset */
#define T20_S_STATUS         0x044
#define T20_S_TX_HDR         0x048   /* {channel, seq/op, length[15:0]} */
#define T20_S_RX_HDR         0x04C   /* {resp, channel, seq, 0} */
#define T20_S_RX_LEN         0x050
#define T20_S_TIMEOUT_US     0x054

#define T20_H_CTRL           0x080   /* W1: [0] start [1] stop [2] clr; RW: [8] loop [9] ack_en */
#define T20_H_STATUS         0x084   /* [0] running [1] done [2] ack_miss */
#define T20_H_COUNT          0x088
#define T20_H_PERIOD         0x08C   /* CLK9 cycles per word, >= H_WIDTH+3 */
#define T20_H_ACK_WIN        0x090   /* [7:0] min [15:8] max latency */
#define T20_H_STEP           0x094
#define T20_H_ACK_OK         0x098
#define T20_H_ACK_MISS       0x09C
#define T20_H_LAT_LAST       0x0A0
#define T20_H_LAT_MIN        0x0A4
#define T20_H_LAT_MAX        0x0A8
#define T20_H_WIDTH          0x0AC

#define T20_S_TX_BUF         0x400   /* write only, 256 words */
#define T20_S_RX_BUF         0x800   /* read only, 256 words */
#define T20_H_TABLE          0xC00   /* write only, 256 words */

/* S_STATUS bits */
#define T20_S_ST_TX_BUSY     (1u << 0)
#define T20_S_ST_XACT_BUSY   (1u << 1)
#define T20_S_ST_RX_VALID    (1u << 2)
#define T20_S_ST_CRC_ERR     (1u << 3)
#define T20_S_ST_TIMEOUT     (1u << 4)
#define T20_S_ST_RX_OVF      (1u << 5)
#define T20_S_ST_XACT_DONE   (1u << 6)
#define T20_S_ST_RESP_MATCH  (1u << 7)

/* S-bus channels */
#define T20_CH_FLASH         0x01
#define T20_CH_HADAMARD_CFG  0x02   /* configuration/status only, never Hadamard timing */
#define T20_CH_TABLE         0x03
#define T20_CH_TRACE         0x04
#define T20_CH_ANALOG_CTRL   0x05   /* Heater PWM, Analog LEDs, Differential G_P/G_N Gates */

/* Channel 0x05 (T20_CH_ANALOG_CTRL) opcodes */
#define T20_OP_SET_HEATER        0x01
#define T20_OP_SET_LEDS          0x02
#define T20_OP_SET_GATES_STATIC  0x03
#define T20_OP_PULSE_COL_GATES   0x04
#define T20_OP_GET_ANALOG_STATUS 0x05

/* S-bus response codes */
#define T20_RESP_ACK         0x06
#define T20_RESP_NAK         0x15
#define T20_RESP_BUSY        0x55
#define T20_RESP_ERR         0xEE

/* =========================================================================
 * T120 Analog DAC & ADC Controller (t120_analog_io_ctrl, APB3 Base 0xF8104000)
 * ========================================================================= */
#define AIO_BASE             0xF8104000u
#define AIO_REG(off)         (*(volatile uint32_t *)(AIO_BASE + (off)))

#define AIO_ID               0x000   /* RO: 0x41494F31 ("AIO1") */
#define AIO_CTRL             0x004   /* [0] sclr_n [1] osc_10hz_en [2] ovr_en [3] auto_h_adc_en [4] adc_conv_mode [5] pi_inv_en [7:6] align [11:8] sck_div */
#define AIO_STATUS           0x008   /* [0] dac_busy [1] adc_busy [2] h_hold_busy [3] quiet_freeze [5:4] osc_st [11:8] step [31:16] sample_cnt */
#define AIO_CMD              0x00C   /* W1: [0] d2 [1] w15 [2] w12 [3] w34 [4] adc_trig [5] dac_center_all */
#define AIO_SETTLE_CYCLES    0x010   /* [15:0] settle_cycles (default 100 = 2.0 us @ 50 MHz) [23:16] conv_cycles */
#define AIO_DAC_OVR_CFG      0x014   /* [7:0] ovr_val [10:8] ovr_ch [13:12] ovr_bank */
#define AIO_HW_VERSION       0x018   /* RO: HW logic synthesis version e.g. 0x20261030 */
#define AIO_HW_ID            0x01C   /* RO: HW logic subsystem ID e.g. 0x4D414D31 ("MAM1") */

#define AIO_DAC2_LO          0x020   /* {d2[3], d2[2], d2[1], d2[0]} */
#define AIO_DAC2_HI          0x024   /* {16'd0, d2[5], d2[4]} */
#define AIO_W15_LO           0x028   /* {w15[3], w15[2], w15[1], w15[0]} */
#define AIO_W15_HI           0x02C   /* {w15[7], w15[6], w15[5], w15[4]} */
#define AIO_W12_LO           0x030   /* {w12[3], w12[2], w12[1], w12[0]} */
#define AIO_W12_HI           0x034   /* {w12[7], w12[6], w12[5], w12[4]} */
#define AIO_W34_LO           0x038   /* {w34[3], w34[2], w34[1], w34[0]} */
#define AIO_W34_HI           0x03C   /* {w34[7], w34[6], w34[5], w34[4]} */
#define AIO_PI_INV_LO        0x040   /* {pi_inv[7]..pi_inv[0]} (4 bits each) */
#define AIO_PI_INV_HI        0x044   /* {pi_inv[15]..pi_inv[8]} (4 bits each) */

#define AIO_ADC45_SIG_01     0x050   /* Signed Q1.11 (raw - 2048): {ch1, ch0} */
#define AIO_ADC45_SIG_23     0x054   /* Signed Q1.11 (raw - 2048): {ch3, ch2} */
#define AIO_ADC45_SIG_45     0x058   /* Signed Q1.11 (raw - 2048): {ch5, ch4} */
#define AIO_ADC49_SIG_01     0x05C   /* Signed Q1.11 (raw - 2048): {ch1, ch0} */
#define AIO_ADC49_SIG_23     0x060   /* Signed Q1.11 (raw - 2048): {ch3, ch2} */
#define AIO_ADC49_SIG_45     0x064   /* Signed Q1.11 (raw - 2048): {ch5, ch4} */

#define AIO_ADC45_RAW_01     0x068   /* Unsigned 12-bit (0..4095): {ch1, ch0} */
#define AIO_ADC45_RAW_23     0x06C   /* Unsigned 12-bit (0..4095): {ch3, ch2} */
#define AIO_ADC45_RAW_45     0x070   /* Unsigned 12-bit (0..4095): {ch5, ch4} */
#define AIO_ADC49_RAW_01     0x074   /* Unsigned 12-bit (0..4095): {ch1, ch0} */
#define AIO_ADC49_RAW_23     0x078   /* Unsigned 12-bit (0..4095): {ch3, ch2} */
#define AIO_ADC49_RAW_45     0x07C   /* Unsigned 12-bit (0..4095): {ch5, ch4} */

#define AIO_CAP_ADC45_BASE   0x100   /* 16 steps * 16 bytes (4 words/step), already un-permuted via pi_inv! */
#define AIO_CAP_ADC49_BASE   0x200   /* 16 steps * 16 bytes (4 words/step), already un-permuted via pi_inv! */

#endif /* T120_BRIDGE_REGS_H */

