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

/* S-bus response codes */
#define T20_RESP_ACK         0x06
#define T20_RESP_NAK         0x15
#define T20_RESP_BUSY        0x55
#define T20_RESP_ERR         0xEE

#endif /* T120_BRIDGE_REGS_H */
