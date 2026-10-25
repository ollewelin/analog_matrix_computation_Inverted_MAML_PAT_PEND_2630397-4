#include "maml_platform.h"
#include "t120_bridge_regs.h"
#include "bsp.h"
#include <string.h>

/* ============================================================================
 * Fixed-Point & PRNG Utilities (Strictly following inverted_maml_math.md §2)
 * ============================================================================ */
static uint32_t g_prng_state = 0xA53C9E4Du;

static uint32_t prng_next(void) {
    uint32_t x = g_prng_state;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    g_prng_state = x ? x : 0xA53C9E4Du;
    return g_prng_state;
}

/* Convergent rounding (round-to-nearest-even) on right-shift by s bits */
static inline int32_t rshift_rne(int32_t val, int s) {
    if (s <= 0) return val;
    int32_t half = 1 << (s - 1);
    int32_t mask = (1 << s) - 1;
    int32_t frac = val & mask;
    int32_t q    = val >> s;
    if (frac > half || (frac == half && (q & 1))) {
        q += 1;
    }
    return q;
}

/* Symmetric saturation to signed 16-bit Q1.14 [-32767, +32767] */
static inline int16_t sat_q14(int32_t v) {
    if (v >  32767) return  32767;
    if (v < -32767) return -32767;
    return (int16_t)v;
}

/* Linear-regime saturation for Dual-2T1C compensation weights [-80, +80] DAC LSBs */
static inline int16_t sat_w80_q14(int32_t v) {
    const int32_t lim = (80 << 7);
    if (v >  lim) return (int16_t)lim;
    if (v < -lim) return (int16_t)(-lim);
    return (int16_t)v;
}

/* Symmetric saturation to signed 8-bit DAC offset [-127, +127] around 128 */
static inline int8_t sat_dac_off(int32_t v) {
    if (v >  127) return  127;
    if (v < -127) return -127;
    return (int8_t)v;
}

static inline uint8_t off_to_dac_u8(int32_t off) {
    int32_t code = 128 + off;
    if (code > 255) code = 255;
    if (code < 0)   code = 0;
    return (uint8_t)code;
}

/* ============================================================================
 * Natural 16x16 Sylvester Walsh-Hadamard Matrix Rows (bits 0..14 used, bit 15=0)
 *   Bit b (0..14) of HADAMARD_16[k] is 1 (+1) iff popcount(k & (b + 1)) is even:
 *     - Basis m = 0       : DC (unperturbed average across all 16 steps)
 *     - Basis m = 1..8    : bits 0..7  -> Matrix 3 rows 0..7 (H_M3_P/N[1..8])
 *     - Basis m = 9..15   : bits 8..14 -> Matrix 8 rows 0..6 (H_M8_P/N[1..7])
 * ============================================================================ */
static const uint16_t HADAMARD_16[16] = {
    0x7FFFu, /* k=0:  all +1 (DC) */
    0x2AAAu, /* k=1:  m odd  = -1, m even = +1 */
    0x1999u, /* k=2 */
    0x4CCCu, /* k=3 */
    0x0787u, /* k=4 */
    0x52D2u, /* k=5 */
    0x61E1u, /* k=6 */
    0x34B4u, /* k=7 */
    0x007Fu, /* k=8:  bits 0..6 (m=1..7) = +1, bits 7..14 (m=8..15) = -1 */
    0x552Au, /* k=9 */
    0x6619u, /* k=10 */
    0x334Cu, /* k=11 */
    0x7807u, /* k=12 */
    0x2D52u, /* k=13 */
    0x1E61u, /* k=14 */
    0x4B34u  /* k=15 */
};

/* ============================================================================
 * Global Platform State
 * ============================================================================ */
static maml_telemetry_pkt_t g_tel;

/* High-precision Q1.14 weight shadow registers (w_dac_off = w_q14 >> 7) */
static int16_t g_w0_m3_q14[8][6];   /* Ref 40 Base Model W_0 for M3 */
static int16_t g_w0_m8_q14[7][6];   /* Ref 40 Base Model W_0 for M8 */
static int16_t g_w_m3_q14[8][6];    /* Current adapted weights for M3 */
static int16_t g_w_m8_q14[7][6];    /* Current adapted weights for M8 */
static int16_t g_w_m33_q14[6][6];   /* Primary Payload Matrix M33 (fixed target) */

/* Momentum velocity buffers (Q1.14) */
static int16_t g_vel_m3_q14[8][6];
static int16_t g_vel_m8_q14[7][6];

/* Stratified time-slice gradient accumulators across the M=10 strata */
static int32_t g_acc_grad_m3[8][6];
static int32_t g_acc_grad_m8[7][6];

/* Ref 40 / Ref 41 MAML initial & final task gradients for Dot-Product 2nd Derivative */
static int16_t g_grad_init_m3[8][6];
static int16_t g_grad_init_m8[7][6];
static int16_t g_grad_final_m3[8][6];
static int16_t g_grad_final_m8[7][6];

/* Hardware Hidden Offset Emulator state (active in Ref 40/41, zeroed in Ref 42) */
static int8_t  g_hid_w_m3[NUM_BASINS][8][6];
static int8_t  g_hid_w_m8[NUM_BASINS][7][6];
static int8_t  g_hid_trim[NUM_BASINS];
static uint8_t g_cur_basin_idx = 0;

/* Outer Randomizer shuffled slot permutation P[0..M-1] */
static uint8_t g_slot_perm[16];
static uint8_t g_slot_cursor = 0;

/* Learning rates & hyperparameters */
static uint16_t g_lr_inner_q16   = 1024;  /* ~0.0156 in Q0.16 */
static uint16_t g_lr_outer_q16   = 512;   /* ~0.0078 in Q0.16 */
static uint16_t g_momentum_q16   = 58982; /* 0.90 in Q0.16 */
static uint8_t  g_hid_amp_dac    = 14;    /* Hidden offset amplitude in DAC LSBs */

static uint32_t g_wdog_refresh_cnt = 0;

/* Calibrated quiescent DC zero baselines (measured at all 30 DACs = 128, Hi-Z Hadamard) */
static int16_t  g_adc45_zero_cal[6] = {0, 0, 0, 0, 0, 0};
static int16_t  g_adc49_zero_cal[6] = {0, 0, 0, 0, 0, 0};
static uint8_t  g_comp_is_centered  = 0;

/* ============================================================================
 * S-Bus Transaction Helper to T20
 * ============================================================================ */
static int t20_sbus_xact(uint8_t ch, uint8_t op, const uint8_t *pay, uint16_t len,
                         uint32_t *rx_w0, uint32_t *rx_w1) {
    T20_REG(T20_CTRL)        = 1;     /* Ensure CLK9 enabled */
    T20_REG(T20_CRESET_CTRL) = 1;     /* Ensure CRESET_N released */
    T20_REG(T20_S_CTRL)      = (1u << 2); /* Clear sticky status */

    uint16_t words = (len + 3u) >> 2;
    for (uint16_t i = 0; i < words; i++) {
        uint32_t w = 0;
        for (int b = 0; b < 4; b++) {
            uint16_t idx = (i << 2) + b;
            if (idx < len) w |= ((uint32_t)pay[idx]) << (b * 8);
        }
        *(volatile uint32_t *)(T20_BRIDGE_BASE + T20_S_TX_BUF + (i << 2)) = w;
    }

    T20_REG(T20_S_TX_HDR) = ((uint32_t)ch << 24) | ((uint32_t)op << 16) | len;
    T20_REG(T20_S_CTRL)   = (1u << 0); /* Start S-bus TX */

    uint32_t timeout = 20000;
    while ((T20_REG(T20_S_STATUS) & T20_S_ST_XACT_BUSY) && --timeout) {
        bsp_uDelay(1);
    }

    uint32_t st  = T20_REG(T20_S_STATUS);
    uint32_t hdr = T20_REG(T20_S_RX_HDR);
    int ok = ((st & T20_S_ST_RX_VALID) && ((hdr >> 24) == T20_RESP_ACK));
    if (ok) {
        if (rx_w0) *rx_w0 = *(volatile uint32_t *)(T20_BRIDGE_BASE + T20_S_RX_BUF + 0);
        if (rx_w1) *rx_w1 = *(volatile uint32_t *)(T20_BRIDGE_BASE + T20_S_RX_BUF + 4);
    }
    T20_REG(T20_S_CTRL) = (1u << 1); /* Release RX buffer */
    return ok;
}

static void t20_sync_heater_and_wdog(void) {
    uint8_t pay[5];
    pay[0] = g_tel.heater_armed ? 1u : 0u;
    pay[1] = g_tel.heater_duty[0];
    pay[2] = g_tel.heater_duty[1];
    pay[3] = g_tel.heater_duty[2];
    pay[4] = g_tel.heater_duty[3];
    t20_sbus_xact(T20_CH_ANALOG_CTRL, T20_OP_SET_HEATER, pay, 5, NULL, NULL);

    uint32_t w0 = 0, w1 = 0;
    if (t20_sbus_xact(T20_CH_ANALOG_CTRL, T20_OP_GET_ANALOG_STATUS, NULL, 0, &w0, &w1)) {
        g_tel.heater_wdog_ok = (w0 & 0x04u) ? 1u : 0u;
    }
}

static void t20_sync_leds(void) {
    uint8_t pay[1];
    pay[0] = (g_tel.comp_led_on ? 1u : 0u) | (g_tel.mat33_led_on ? 2u : 0u);
    t20_sbus_xact(T20_CH_ANALOG_CTRL, T20_OP_SET_LEDS, pay, 1, NULL, NULL);
}

static void t20_set_hadamard_mask(uint16_t en_mask) {
    /* Support both 2-byte big-endian (T20_Golden/initial T20_Custom) and 6-byte payload */
    uint8_t pay2[2];
    pay2[0] = (uint8_t)((en_mask >> 8) & 0xFFu);
    pay2[1] = (uint8_t)(en_mask & 0xFFu);
    t20_sbus_xact(T20_CH_HADAMARD_CFG, 0x01, pay2, 2, NULL, NULL);
}

/* Force T20 Hadamard pins into 3-State Hi-Z (OE = 0, floating in analog middle 1.65V) */
static void t20_hadamard_tristate_center(void) {
    *(volatile uint32_t *)(T20_BRIDGE_BASE + T20_H_TABLE + 0) = 0x00008000u; /* vec[15] = 1 -> OE = 0 */
    T20_REG(T20_H_COUNT)  = 1;
    T20_REG(T20_H_PERIOD) = 24;
    T20_REG(T20_H_CTRL)   = (1u << 0) | (1u << 9);
    uint32_t timeout = 2000;
    while ((((T20_REG(T20_H_STATUS) & 2u) == 0u) || (T20_REG(T20_H_STATUS) & 1u)) && --timeout) {
        bsp_uDelay(1);
    }
    bsp_uDelay(2);
}

/* ============================================================================
 * DAC Bank Loading Helpers (AIO APB3 Slave at 0xF8104000)
 *   Per Schematic Page 12 (DAC_8BIT / 74HC595):
 *     - QA (pin 15, last bit shifted in)  = MSB of R-2R ladder (DAC_LAD_OUT)
 *     - QH (pin 7,  first bit shifted in) = LSB of R-2R ladder (GND end)
 *   Since hardware shifts bit 7 first and bit 0 last, bit-reversing each byte
 *   ensures bit 0 (LSB) lands in QH and bit 7 (MSB) lands in QA!
 * ============================================================================ */
static inline uint8_t bitrev8(uint8_t x) {
    x = (uint8_t)(((x & 0xF0u) >> 4) | ((x & 0x0Fu) << 4));
    x = (uint8_t)(((x & 0xCCu) >> 2) | ((x & 0x33u) << 2));
    x = (uint8_t)(((x & 0xAAu) >> 1) | ((x & 0x55u) << 1));
    return x;
}

static void aio_wait_dac_ready(void) {
    bsp_uDelay(15);
    uint32_t timeout = 10000;
    while ((AIO_REG(AIO_STATUS) & 0x01u) && --timeout);
}

static void aio_load_dac2(const uint8_t d2[6]) {
    uint32_t lo = ((uint32_t)bitrev8(d2[0])) |
                  ((uint32_t)bitrev8(d2[1]) << 8) |
                  ((uint32_t)bitrev8(d2[2]) << 16) |
                  ((uint32_t)bitrev8(d2[3]) << 24);
    uint32_t hi = ((uint32_t)bitrev8(d2[4])) |
                  ((uint32_t)bitrev8(d2[5]) << 8);
    AIO_REG(AIO_DAC2_LO) = lo;
    AIO_REG(AIO_DAC2_HI) = hi; /* Writing HI auto-triggers Bank 0 shift & RCK latch */
    aio_wait_dac_ready();
}

static void aio_load_weight_banks(const uint8_t w15[8], const uint8_t w12[8], const uint8_t w34[8]) {
    AIO_REG(AIO_W15_LO) = ((uint32_t)bitrev8(w15[0])) | ((uint32_t)bitrev8(w15[1]) << 8) |
                          ((uint32_t)bitrev8(w15[2]) << 16) | ((uint32_t)bitrev8(w15[3]) << 24);
    AIO_REG(AIO_W15_HI) = ((uint32_t)bitrev8(w15[4])) | ((uint32_t)bitrev8(w15[5]) << 8) |
                          ((uint32_t)bitrev8(w15[6]) << 16) | ((uint32_t)bitrev8(w15[7]) << 24);
    aio_wait_dac_ready();

    AIO_REG(AIO_W12_LO) = ((uint32_t)bitrev8(w12[0])) | ((uint32_t)bitrev8(w12[1]) << 8) |
                          ((uint32_t)bitrev8(w12[2]) << 16) | ((uint32_t)bitrev8(w12[3]) << 24);
    AIO_REG(AIO_W12_HI) = ((uint32_t)bitrev8(w12[4])) | ((uint32_t)bitrev8(w12[5]) << 8) |
                          ((uint32_t)bitrev8(w12[6]) << 16) | ((uint32_t)bitrev8(w12[7]) << 24);
    aio_wait_dac_ready();

    AIO_REG(AIO_W34_LO) = ((uint32_t)bitrev8(w34[0])) | ((uint32_t)bitrev8(w34[1]) << 8) |
                          ((uint32_t)bitrev8(w34[2]) << 16) | ((uint32_t)bitrev8(w34[3]) << 24);
    AIO_REG(AIO_W34_HI) = ((uint32_t)bitrev8(w34[4])) | ((uint32_t)bitrev8(w34[5]) << 8) |
                          ((uint32_t)bitrev8(w34[6]) << 16) | ((uint32_t)bitrev8(w34[7]) << 24);
    aio_wait_dac_ready();
}

/* ============================================================================
 * Differential Dual-2T1C (2X_2T1C) Column Refresh Sequence (Ref 18)
 *   For each column j = 0..5:
 *     1. Charge Positive Half-Cell (G_Pj_MAT_*): W+ = 128 + w_eff
 *     2. Charge Negative Half-Cell (G_Nj_MAT_*): W- = 128 - w_eff
 * ============================================================================ */
static void maml_sync_shadow_bytes(void) {
    for (int r = 0; r < 8; r++)
        for (int c = 0; c < 6; c++)
            g_tel.w_m3[r][c] = sat_dac_off(rshift_rne(g_w_m3_q14[r][c], 7));

    for (int r = 0; r < 7; r++)
        for (int c = 0; c < 6; c++)
            g_tel.w_m8[r][c] = sat_dac_off(rshift_rne(g_w_m8_q14[r][c], 7));

    for (int r = 0; r < 6; r++)
        for (int c = 0; c < 6; c++)
            g_tel.w_m33[r][c] = sat_dac_off(rshift_rne(g_w_m33_q14[r][c], 7));
}

/* Matrix P/N gate mask bits for pay[1] of T20_OP_PULSE_COL_GATES (CH 0x05 OP 0x4):
 *   pay[0] = col_mask_6b [5:0] (cols 1..6)
 *   pay[1] = {0, mat33_n, mat8_n, mat3_n, 0, mat33_p, mat8_p, mat3_p}
 *   pay[2..3] = duration in CLK9 cycles (LE)
 */
#define T20_GATE_M3_P    0x01u
#define T20_GATE_M8_P    0x02u
#define T20_GATE_M33_P   0x04u
#define T20_GATE_ALL_P   0x07u

#define T20_GATE_M3_N    0x10u
#define T20_GATE_M8_N    0x20u
#define T20_GATE_M33_N   0x40u
#define T20_GATE_ALL_N   0x70u

static void maml_pulse_t20_col_gates(uint8_t col_mask_6b, uint8_t mat_pn_mask, uint16_t clk9_cycles) {
    uint8_t pay[4];
    pay[0] = col_mask_6b & 0x3Fu;
    pay[1] = mat_pn_mask & 0x77u;
    pay[2] = (uint8_t)(clk9_cycles & 0xFFu);
    pay[3] = (uint8_t)((clk9_cycles >> 8) & 0xFFu);
    t20_sbus_xact(T20_CH_ANALOG_CTRL, T20_OP_PULSE_COL_GATES, pay, 4, NULL, NULL);
}

/* ============================================================================
 * Autonomous Synchronous 2T1C Refresh Timing Parameters (Tunable in future GUI)
 *   - g_col_settle_us     : Setting time per column (G_N + G_P).
 *                           Default = 100 us (50 us = 5*tau_charge for G_N +
 *                           50 us = 5*tau_charge for G_P, >99.3% settled).
 *                           Total Refresh Duty Time = 6 * g_col_settle_us = 600 us.
 *   - g_refresh_period_us : Full-matrix autonomous refresh period.
 *                           Default = 10000 us (10.0 ms, 100 Hz).
 * ============================================================================ */
static uint16_t g_col_settle_us     = 100u;   /* 100 us per column (50 us G_N + 50 us G_P) */
static uint32_t g_refresh_period_us = 10000u; /* 10.0 ms (100 Hz) autonomous refresh cycle */
static uint32_t g_hadamard_delay_us = 5000u;  /* Default 5.0 ms (5000 us) nominal plateau */
static uint32_t g_last_refresh_ticks = 0u;
static uint8_t  g_focus_col          = 0u;
static uint8_t  g_dac_row7_code      = 128u;  /* DAC2_D_ROW7 (w34[6], TRIM_B1) */
static uint8_t  g_dac_row8_code      = 128u;  /* DAC2_D_ROW8 (w34[7], TRIM_REF) */
static uint8_t  g_auto_random_data   = 0u;    /* Autonomous 100 Hz white-noise In-Data generator */

/* Primary Payload Matrix M33 (full-rank 6x6 target matrix with positive column
 * pedestal so single-supply COLTIA amplifiers U1/U2$CBB15 stay in the center
 * of their linear operating window around 1.65V / 0 LSB at t = 5.0 ms) */
static const int8_t k_default_m33[6][6] = {
    { +76, -20, +28,  -4, +44, -36 },
    { -20, +84, -12, +44,  -4, +36 },
    { +36,  -4, +80, -16, +32,  -4 },
    {  -4, +40,  -8, +72, -12, +44 },
    { +44, -12, +28, -12, +76,  -8 },
    { -28, +32,  -4, +40,  -8, +82 }
};

static void maml_refresh_all_columns(void) {
    maml_sync_shadow_bytes();

    /* Step 1: Ensure Hadamard outputs are 3-Stated (Hi-Z, OE=0) before recharging 2T1C gates */
    t20_hadamard_tristate_center();

    int use_hid = (g_tel.run_mode == MAML_MODE_BASE_TRAIN) && (g_hid_amp_dac > 0u);
    int8_t hid_trim = use_hid ? g_hid_trim[g_cur_basin_idx] : 0;
    g_tel.hid_trim_offset = hid_trim;
    uint8_t trim_code = off_to_dac_u8((int32_t)g_tel.trim_dac_38 + (int32_t)hid_trim);

    /* Split column setting time equally between G_N and G_P half-cells:
     * Default g_col_settle_us = 100 us -> half_settle_us = 50 us (5 * tau_charge).
     * At 2 MHz CLK9, 1 us = 2 CLK9 cycles -> pulse_clk9 = 100 cycles. */
    uint16_t half_settle_us = (g_col_settle_us >= 20u) ? (g_col_settle_us >> 1) : 10u;
    uint16_t pulse_clk9     = (uint16_t)(half_settle_us * 2u);

    uint8_t w15[8], w12[8], w34[8];

    for (int step = 0; step < 6; step++) {
        int col = (int)((g_focus_col + 1u + (uint8_t)step) % 6u);
        uint8_t col_bit = (uint8_t)(1u << col);

        /* --- A. Negative Half-Cells (G_N[col+1]_MAT_*) : W- = 128 - w_eff --- */
        for (int r = 0; r < 8; r++) {
            int32_t w = g_tel.w_m3[r][col] + (use_hid ? g_hid_w_m3[g_cur_basin_idx][r][col] : 0);
            w15[r] = off_to_dac_u8(-w);
        }
        for (int r = 0; r < 7; r++) {
            int32_t w = g_tel.w_m8[r][col] + (use_hid ? g_hid_w_m8[g_cur_basin_idx][r][col] : 0);
            w12[r] = off_to_dac_u8(-w);
        }
        w12[7] = trim_code; /* Ref 38 TRIM_DAC on W_12 channel 8 */
        for (int r = 0; r < 6; r++) {
            w34[r] = off_to_dac_u8(-g_tel.w_m33[r][col]);
        }
        w34[6] = g_dac_row7_code; /* DAC2_D_ROW7 (TRIM_B1) */
        w34[7] = g_dac_row8_code; /* DAC2_D_ROW8 (TRIM_REF) */

        aio_load_weight_banks(w15, w12, w34);
        bsp_uDelay(5); /* Let MCP6024T DAC buffers settle before opening G_N switch */

        maml_pulse_t20_col_gates(col_bit, T20_GATE_ALL_N, pulse_clk9);
        /* Wait full half_settle_us + 5 us guard so G_N switch closes BEFORE W DACs change */
        bsp_uDelay(half_settle_us + 5u);

        /* --- B. Positive Half-Cells (G_P[col+1]_MAT_*) : W+ = 128 + w_eff --- */
        for (int r = 0; r < 8; r++) {
            int32_t w = g_tel.w_m3[r][col] + (use_hid ? g_hid_w_m3[g_cur_basin_idx][r][col] : 0);
            w15[r] = off_to_dac_u8(+w);
        }
        for (int r = 0; r < 7; r++) {
            int32_t w = g_tel.w_m8[r][col] + (use_hid ? g_hid_w_m8[g_cur_basin_idx][r][col] : 0);
            w12[r] = off_to_dac_u8(+w);
        }
        w12[7] = trim_code; /* Ref 38 TRIM_DAC on W_12 channel 8 */
        for (int r = 0; r < 6; r++) {
            w34[r] = off_to_dac_u8(+g_tel.w_m33[r][col]);
        }
        w34[6] = g_dac_row7_code; /* DAC2_D_ROW7 (TRIM_B1) */
        w34[7] = g_dac_row8_code; /* DAC2_D_ROW8 (TRIM_REF) */

        aio_load_weight_banks(w15, w12, w34);
        bsp_uDelay(5); /* Let MCP6024T DAC buffers settle before opening G_P switch */

        maml_pulse_t20_col_gates(col_bit, T20_GATE_ALL_P, pulse_clk9);
        /* Wait full half_settle_us + 5 us guard so G_P switch closes BEFORE next column */
        bsp_uDelay(half_settle_us + 5u);
    }

    g_tel.total_refresh_cycles++;
}

/* ============================================================================
 * White-Noise Reference Pattern Generator (Ref 1, DAC_2) & Ideal Target (Ref 39)
 *   MANDATORY RULE: Held 100% constant across the entire refresh cycle and
 *   across all M shuffled strata slots before advancing!
 * ============================================================================ */
static void maml_recompute_z_target(void) {
    /* Compute ideal digital target output Z_target = g_adc49_zero_cal + M33_ideal * x_ref */
    for (int j = 0; j < 6; j++) {
        int32_t acc = 0;
        for (int i = 0; i < 6; i++) {
            acc += (int32_t)g_tel.w_m33[i][j] * (int32_t)g_tel.x_ref[i];
        }
        int32_t z_scaled = (int32_t)g_adc49_zero_cal[j] + rshift_rne(acc * 8, 8);
        if (z_scaled > 2047)  z_scaled = 2047;
        if (z_scaled < -2048) z_scaled = -2048;
        g_tel.z_target[j] = (int16_t)z_scaled;
    }
}

static void maml_generate_new_white_noise_ref(void) {
    uint8_t d2_codes[6];
    for (int i = 0; i < 6; i++) {
        /* Uniform white noise in [-45, +45] (DAC2 codes 83..173, keeping MOSFETs in linear triode region) */
        int32_t rnd = (int32_t)(prng_next() % 91u) - 45;
        g_tel.x_ref[i] = (int16_t)rnd;
        d2_codes[i]    = off_to_dac_u8(rnd);
    }
    aio_load_dac2(d2_codes);
    maml_recompute_z_target();
}

/* Fisher-Yates shuffle of time-slot permutation P[0..M-1] */
static void maml_shuffle_outer_slots(void) {
    uint8_t m = g_tel.num_strata_m;
    if (m < 1 || m > 16) m = NUM_STRATA_DEFAULT;
    for (uint8_t i = 0; i < m; i++) g_slot_perm[i] = i;
    for (int i = (int)m - 1; i > 0; i--) {
        uint32_t j = prng_next() % (uint32_t)(i + 1);
        uint8_t tmp = g_slot_perm[i];
        g_slot_perm[i] = g_slot_perm[j];
        g_slot_perm[j] = tmp;
    }
    g_slot_cursor = 0;
}

/* ============================================================================
 * Contiguous Interleaved 2x7 = 14-Pulse Sylvester H_8 Simplex Hadamard Table
 * (2.00 us per pulse = 28.00 us total + step 14 = 0x8000 Tri-State Hi-Z exit)
 *   - Uses all 7 non-DC rows of Sylvester H_8 (HADAMARD_16[1..7]):
 *     For any two distinct basis indices b != b' in 0..6, the dot product across
 *     the 7 non-DC rows is identically -1 (Simplex code).
 *   - Because active rows 0..5 are enabled (0x003Fu for M3, 0x3F00u for M8) while
 *     the 7th basis (b=6 for M3, b=14 for M8) is held in 3-State Hi-Z (y_6 == 0),
 *     subtracting c[6] from c[b] (c[b] - c[6] = 16 * y[b]) cancels 100% of
 *     off-diagonal inter-row cross-talk!
 *   - Interleaving (+) at 2*p and (-) at 2*p+1 separates each complementary pair
 *     by only 2.00 us, canceling 100% of capacitor discharge DC drift!
 * ============================================================================ */
static const uint16_t HADAMARD_2X7_POS[7] = {
    0x2AAAu, /* p=0: H_8 row 1 */
    0x1999u, /* p=1: H_8 row 2 */
    0x4CCCu, /* p=2: H_8 row 3 */
    0x0787u, /* p=3: H_8 row 4 */
    0x52D2u, /* p=4: H_8 row 5 */
    0x61E1u, /* p=5: H_8 row 6 */
    0x34B4u  /* p=6: H_8 row 7 (completes exact 7-row Sylvester H_8 simplex!) */
};

static void maml_run_2x6_hadamard_burst(uint16_t en_mask, int tristate_off, uint8_t sck_div) {
    /* Configure T20 active matrix mask over S-bus at standard 2 MHz CLK9 */
    T20_REG(T20_CLK_PERIOD) = 25u;
    t20_set_hadamard_mask(en_mask);
    t20_hadamard_tristate_center();

    /* Identity scatter map: pulse t (0..13) writes directly to cap_ram[t] */
    AIO_REG(AIO_PI_INV_LO) = 0x76543210u;
    AIO_REG(AIO_PI_INV_HI) = 0xFEDCBA98u;

    /* Load 2x7 = 14 contiguous interleaved 2.00 us pulses:
     *   - Step 2*p     : (+) pulse p
     *   - Step 2*p + 1 : (-) pulse p (exact complement, only 2.00 us after (+)!)
     *   - Step 14      : 0x8000 Tri-State exit at 28.00 us */
    for (int p = 0; p < 7; p++) {
        uint16_t w_pos = tristate_off ? 0x8000u : (HADAMARD_2X7_POS[p] & 0x7FFFu);
        uint16_t w_neg = tristate_off ? 0x8000u : ((~HADAMARD_2X7_POS[p]) & 0x7FFFu);
        *(volatile uint32_t *)(T20_BRIDGE_BASE + T20_H_TABLE + 4 * (2 * p))     = (uint32_t)w_pos;
        *(volatile uint32_t *)(T20_BRIDGE_BASE + T20_H_TABLE + 4 * (2 * p + 1)) = (uint32_t)w_neg;
    }
    *(volatile uint32_t *)(T20_BRIDGE_BASE + T20_H_TABLE + 4 * 14) = 0x00008000u; /* Exit to Hi-Z at 28.00 us */
    *(volatile uint32_t *)(T20_BRIDGE_BASE + T20_H_TABLE + 4 * 15) = 0x00008000u;

    /* Switch to Pipelined 2.00 us Contiguous Mode:
     *   - T20_CLK_PERIOD = 5 (10.0 MHz CLK9, 100 ns cycle)
     *   - T20_H_PERIOD   = 20 (20 CLK9 cycles = 2.000 us exact per pulse!)
     *   - T20_H_COUNT    = 15 (14 active pulses = 28.000 us + step 14 = 0x8000 Hi-Z)
     *   - r_settle_cycles = 1 (enables pipe_2us_mode, no CLK9 freeze), r_conv_cycles = 21 (locks S/H at 1.96 us) */
    g_tel.settle_cycles = 100u; /* 100 sys_clk cycles = 2.00 us per pulse */
    AIO_REG(AIO_SETTLE_CYCLES) = (21u << 16) | 1u;
    if (sck_div < 1u) sck_div = 2u;
    AIO_REG(AIO_CTRL) = (((uint32_t)(sck_div & 0x0Fu)) << 8) | 0xA9u;

    T20_REG(T20_CLK_PERIOD) = 5u;
    T20_REG(T20_H_COUNT)    = 15u;
    T20_REG(T20_H_PERIOD)   = 20u;
    T20_REG(T20_H_CTRL)     = (1u << 2) | (1u << 9); /* Clear counters */
    T20_REG(T20_H_CTRL)     = (1u << 0) | (1u << 9); /* Fire single 28.00 us hardware burst! */

    uint32_t timeout = 10000;
    while ((((T20_REG(T20_H_STATUS) & 2u) == 0u) ||
            (T20_REG(T20_H_STATUS) & 1u) ||
            (AIO_REG(AIO_STATUS) & 0x06u)) && --timeout) {
        bsp_uDelay(1);
    }

    g_tel.t20_h_ack_ok   = T20_REG(T20_H_ACK_OK);
    g_tel.t20_h_ack_miss = T20_REG(T20_H_ACK_MISS);
    g_tel.t20_h_lat_last = (uint16_t)T20_REG(T20_H_LAT_LAST);

    /* Restore standard 2 MHz S-bus clock and 74HC595 DAC shift divider (sck_div=15) */
    T20_REG(T20_CLK_PERIOD)    = 25u;
    AIO_REG(AIO_SETTLE_CYCLES) = (25u << 16) | 100u;
    AIO_REG(AIO_CTRL)          = 0x00000FA9u;
}

static void maml_run_permuted_hadamard_sweep(uint16_t en_mask) {
    maml_run_2x6_hadamard_burst(en_mask, 0, 2u);
}

/* Read latest 6-channel signed Q1.11 ADC_45 & ADC_49 readings */
static void maml_read_latest_adcs(int16_t adc45_out[6], int16_t adc49_out[6]) {
    uint32_t w45_01 = AIO_REG(AIO_ADC45_SIG_01);
    uint32_t w45_23 = AIO_REG(AIO_ADC45_SIG_23);
    uint32_t w45_45 = AIO_REG(AIO_ADC45_SIG_45);
    adc45_out[0] = (int16_t)(w45_01 & 0xFFFFu);
    adc45_out[1] = (int16_t)(w45_01 >> 16);
    adc45_out[2] = (int16_t)(w45_23 & 0xFFFFu);
    adc45_out[3] = (int16_t)(w45_23 >> 16);
    adc45_out[4] = (int16_t)(w45_45 & 0xFFFFu);
    adc45_out[5] = (int16_t)(w45_45 >> 16);

    uint32_t w49_01 = AIO_REG(AIO_ADC49_SIG_01);
    uint32_t w49_23 = AIO_REG(AIO_ADC49_SIG_23);
    uint32_t w49_45 = AIO_REG(AIO_ADC49_SIG_45);
    adc49_out[0] = (int16_t)(w49_01 & 0xFFFFu);
    adc49_out[1] = (int16_t)(w49_01 >> 16);
    adc49_out[2] = (int16_t)(w49_23 & 0xFFFFu);
    adc49_out[3] = (int16_t)(w49_23 >> 16);
    adc49_out[4] = (int16_t)(w49_45 & 0xFFFFu);
    adc49_out[5] = (int16_t)(w49_45 >> 16);
}

static void aio_trigger_settled_adc_read(int16_t adc45_out[6], int16_t adc49_out[6]) {
    int32_t acc45[6] = {0, 0, 0, 0, 0, 0};
    int32_t acc49[6] = {0, 0, 0, 0, 0, 0};
    int16_t tmp45[6], tmp49[6];
    for (int s = 0; s < 16; s++) {
        AIO_REG(AIO_CMD) = (1u << 4); /* Manual settled ADC_45 & ADC_49 conversion */
        uint32_t timeout = 10000;
        while ((AIO_REG(AIO_STATUS) & 0x06u) && --timeout);
        bsp_uDelay(2);
        maml_read_latest_adcs(tmp45, tmp49);
        for (int c = 0; c < 6; c++) {
            acc45[c] += tmp45[c];
            acc49[c] += tmp49[c];
        }
    }
    for (int c = 0; c < 6; c++) {
        adc45_out[c] = (int16_t)rshift_rne(acc45[c], 4);
        adc49_out[c] = (int16_t)rshift_rne(acc49[c], 4);
    }
}

/* ============================================================================
 * 14-Pulse (2x7 Interleaved (+) and (-)) Exact Orthogonal Sylvester H_8 Demodulator
 *   - Pulse 2*p     : (+) Table response Y_pos[p][c]
 *   - Pulse 2*p + 1 : (-) Table response Y_neg[p][c] (2.00 us later)
 *   - Differential pair dY[p][c] = Y_pos[p][c] - Y_neg[p][c] cancels DC offset
 *     and linear capacitor discharge slope!
 *   - Exact Simplex Orthogonalization:
 *       raw_c[b] = sum_{p=0..6} sign(HADAMARD_2X7_POS[p], bit b) * dY[p][c]
 *       Since bit 6 (for M3) and bit 14 (for M8) are held in 3-State Hi-Z (y == 0),
 *       raw_c[6] = -2 * sum_{r=0..5} y_r.
 *       Therefore: raw_c[b] - raw_c[6] = 16 * y_b (100% zero cross-talk!).
 * ============================================================================ */
static void maml_fwht16_demodulate(uint32_t cap_base_off, int16_t sens_out[16][6]) {
    int32_t buf[14][6];

    for (int k = 0; k < 14; k++) {
        uint32_t addr = cap_base_off + (uint32_t)(k * 16);
        uint32_t w01  = AIO_REG(addr + 0x0);
        uint32_t w23  = AIO_REG(addr + 0x4);
        uint32_t w45  = AIO_REG(addr + 0x8);
        buf[k][0] = (int16_t)(w01 & 0xFFFFu);
        buf[k][1] = (int16_t)(w01 >> 16);
        buf[k][2] = (int16_t)(w23 & 0xFFFFu);
        buf[k][3] = (int16_t)(w23 >> 16);
        buf[k][4] = (int16_t)(w45 & 0xFFFFu);
        buf[k][5] = (int16_t)(w45 >> 16);
    }

    /* k = 0: DC average across the 14 samples */
    for (int c = 0; c < 6; c++) {
        int32_t dc_sum = 0;
        for (int k = 0; k < 14; k++) dc_sum += buf[k][c];
        sens_out[0][c] = sat_q14(dc_sum / 14);
    }

    /* Raw 7-pulse Simplex correlation for bits b = 0..14 */
    int32_t raw_corr[15][6];
    for (int b = 0; b < 15; b++) {
        for (int c = 0; c < 6; c++) {
            int32_t corr = 0;
            for (int p = 0; p < 7; p++) {
                int32_t dy = buf[2 * p][c] - buf[2 * p + 1][c];
                if ((HADAMARD_2X7_POS[p] >> b) & 1u) {
                    corr += dy;
                } else {
                    corr -= dy;
                }
            }
            raw_corr[b][c] = corr;
        }
    }

    /* Subtract silent reference basis (b=6 for M3 rows 0..5, b=14 for M8 rows 0..5)
     * so cross-talk from the other 5 active rows cancels identically! */
    for (int c = 0; c < 6; c++) {
        int32_t ref_m3 = raw_corr[6][c];
        for (int r = 0; r < 6; r++) {
            sens_out[r + 1][c] = sat_q14((raw_corr[r][c] - ref_m3) >> 1);
        }
        sens_out[7][c] = 0;
        sens_out[8][c] = 0;

        int32_t ref_m8 = raw_corr[14][c];
        for (int r = 0; r < 6; r++) {
            sens_out[r + 9][c] = sat_q14((raw_corr[r + 8][c] - ref_m8) >> 1);
        }
        sens_out[15][c] = 0;
    }
}

/* ============================================================================
 * Pure Hardware Analog Readout & Non-Backprop Hadamard Gradient Engine
 *   Implements Equations 1–7 from NON_BACKPROP_HADAMARD_GRADIENT_RULES.md
 *   strictly from raw physical ADC_45 / ADC_49 and FWHT-16 measurements:
 *     - Eq. 1: Er_j^(49) = Z_out,j^(49) - Z_target,j
 *     - Eq. 2: dL / dW_{i,j}^(8) = <dz_j^(49)/dV_i^PTU>_H * Er_j^(49)  [NO * x_i!]
 *     - Eq. 5: Carrier Wave Search k = argmax_i |x_i^(8)|
 *     - Eq. 6: Regularized Inverse Scaling for sigma_2'(y_j^(8))
 *     - Eq. 4: Row Sensitivity Receipt dx_i^(8)
 *     - Eq. 7: dL / dW_{i,j}^(3) = <dz_j^(45)/dV_i^PTU>_H * dx_j^(8)   [NO * x_i!]
 * ============================================================================ */

static int16_t g_basin_w_m3_q14[NUM_BASINS][8][6];
static int16_t g_basin_w_m8_q14[NUM_BASINS][7][6];

static void maml_measure_and_extract_gradients(uint8_t stratum_idx,
                                               int16_t grad_m3_out[8][6],
                                               int16_t grad_m8_out[7][6]) {
    (void)stratum_idx;
    int16_t sens_m8_raw[16][6];
    int16_t sens_m3_raw[16][6];

    /* 1. Ensure Hadamard carrier is in 3-State (0x8000 Hi-Z) on the settled plateau
     *    and read the quiet forward-pass analog output on ADC_45 & ADC_49 FIRST! */
    t20_hadamard_tristate_center();
    bsp_uDelay(10);
    aio_trigger_settled_adc_read(g_tel.adc45_sig, g_tel.adc49_sig);

    /* 2. Sub-Window A: Perturb Matrix 8 FIRST (active rows 0..5 = 0x3F00, M3 3-stated Hi-Z)
     *    Per NON_BACKPROP_HADAMARD_GRADIENT_RULES.md §2: M8 is perturbed first while M3 is quiet! */
    maml_run_permuted_hadamard_sweep(0x3F00u);
    maml_fwht16_demodulate(AIO_CAP_ADC49_BASE, sens_m8_raw);

    /* 20 us quiet Tri-State separation between M8 table and M3 table */
    t20_hadamard_tristate_center();
    bsp_uDelay(20);

    /* 3. Sub-Window B: Perturb Matrix 3 SECOND (active rows 0..5 = 0x003F, M8 3-stated Hi-Z) */
    maml_run_permuted_hadamard_sweep(0x003Fu);
    maml_fwht16_demodulate(AIO_CAP_ADC45_BASE, sens_m3_raw);

    /* 4. Return Hadamard carrier to 3-State (0x8000 Hi-Z) immediately after burst */
    t20_hadamard_tristate_center();

    int16_t sens_m8[7][6];
    int16_t sens_m3[8][6];
    int16_t eval_adc45[6];
    int16_t eval_adc49[6];

    /* Direct physical signed 12-bit differential ADC readings (0 LSB = 1.65V hardware center) */
    for (int c = 0; c < 6; c++) {
        eval_adc45[c] = g_tel.adc45_sig[c];
        eval_adc49[c] = g_tel.adc49_sig[c];
        for (int r = 0; r < 8; r++) {
            sens_m3[r][c] = sens_m3_raw[r + 1][c];
        }
        for (int r = 0; r < 7; r++) {
            sens_m8[r][c] = sens_m8_raw[r + 9][c];
        }
    }

    int uncomp_mode = (g_tel.jumper_mode == JUMPER_OFF_NO_COMP) || (g_comp_is_centered != 0u);

    /* ========================================================================
     * Equation 1: Output Error Er_j^(49) and Total Loss L_total (Pure Hardware)
     * ======================================================================== */
    int32_t err49[6];
    uint32_t loss_sq_sum = 0;
    for (int j = 0; j < 6; j++) {
        err49[j] = (int32_t)g_tel.z_target[j] - (int32_t)eval_adc49[j];
        loss_sq_sum += (uint32_t)(err49[j] * err49[j]);
    }
    g_tel.loss_total_milli = loss_sq_sum;

    /* Effective Bit Precision (ENOB * 100) directly from measured hardware RMSE:
     *   ENOB = log2(2048 / RMSE) = 11.00 - 0.5 * log2(rmse_sq) */
    uint32_t rmse_sq = loss_sq_sum / 6u;
    uint16_t enob_centi = 1100;
    if (rmse_sq > 0) {
        uint32_t v = rmse_sq;
        int msb = 0;
        while (v > 1) { v >>= 1; msb++; }
        uint32_t base = 1u << msb;
        uint32_t frac = ((rmse_sq - base) << 8) >> msb; /* 0..255 fractional octave */
        int32_t log2_rmse_x100 = (msb * 50) + (int32_t)((frac * 50u) >> 8);
        int32_t eb = 1100 - log2_rmse_x100;
        if (eb < 0)    eb = 0;
        if (eb > 1200) eb = 1200;
        enob_centi = (uint16_t)eb;
    }
    if (uncomp_mode) {
        g_tel.bit_prec_uncomp_centi = enob_centi;
    } else {
        g_tel.bit_prec_comp_centi = enob_centi;
    }

    /* ========================================================================
     * Equation 2: Layer 2 (M8) Weight Gradient (Direct Hadamard Error Product)
     *   dL / dW_{i,j}^(8) = <dz_j^(49) / dV_i^PTU>_Hadamard * Er_j^(49)
     *   CRITICAL: NO digital multiplication by x_i^(8)!
     * ======================================================================== */
    for (int i = 0; i < 7; i++) {
        for (int j = 0; j < 6; j++) {
            int32_t prod = (int32_t)sens_m8[i][j] * (-err49[j]);
            grad_m8_out[i][j] = sat_q14(rshift_rne(prod, 1));
        }
    }

    /* ========================================================================
     * Equation 5: Carrier Wave Search (Find strongest intermediate row k)
     *   k = argmax_{i in 0..5} |x_i^(8)|
     *   where x_i^(8) is the zero-referenced Layer 1 activation on ADC_45[i]
     * ======================================================================== */
    int16_t x8_sig[6];
    uint8_t best_k = 0;
    int32_t max_abs_x8 = -1;
    for (uint8_t i = 0; i < 6; i++) {
        x8_sig[i] = (int16_t)((int32_t)eval_adc45[i] - (int32_t)g_adc45_zero_cal[i]);
        int32_t ax = x8_sig[i];
        if (ax < 0) ax = -ax;
        if (ax > max_abs_x8) {
            max_abs_x8 = ax;
            best_k     = i;
        }
    }
    g_tel.carrier_row_k = best_k;

    /* ========================================================================
     * Equation 6: Regularized Inverse Scaling for Column Slope sigma_2'(y_j^(8))
     *   sigma_2'(y_j^(8)) approx (x_k^(8) / ((x_k^(8))^2 + alpha)) * <dz_j^(49)/dW_{k,j}^(8)>_H
     *   Evaluated using the strongest carrier row best_k from Equation 5, with
     *   Tikhonov regularization alpha = 256 LSB^2 and non-negative clamp for the
     *   monotonically increasing BJT differential pair Sigmoid 10 (SIG2).
     * ======================================================================== */
    int32_t xk = x8_sig[best_k];
    int32_t denom = (xk * xk) + 256;
    for (int j = 0; j < 6; j++) {
        if (g_tel.jumper_mode == JUMPER_OFF_NO_COMP) {
            g_tel.sigma2_slope[j] = 0;
        } else if (g_tel.jumper_mode == JUMPER_BYPASS_SIG2) {
            g_tel.sigma2_slope[j] = 16384; /* 1.0 in Q1.14 */
        } else {
            int32_t s_kj = sens_m8[best_k][j];
            int32_t num  = xk * s_kj;
            if (num < 0) num = -num;
            int32_t slope_q14 = 2048 + ((num << 13) / denom);
            if (slope_q14 > 16384) slope_q14 = 16384;
            g_tel.sigma2_slope[j] = (int16_t)slope_q14;
        }
    }

    /* ========================================================================
     * Equation 4: Row Sensitivity Receipt dx_i^(8) back to Layer 1
     *   dx_i^(8) = sum_{j=0..5} W_{i,j}^(8)digital * sigma_2'(y_j^(8)) * Er_j^(49)
     *   Normalized for Q1.14 sigma_2_slope (>> 14) and 6x6 cascade fan-in (>> 6)
     * ======================================================================== */
    int32_t dx8[6];
    for (int i = 0; i < 6; i++) {
        int32_t sum = 0;
        for (int j = 0; j < 6; j++) {
            int32_t col_term = rshift_rne((int32_t)g_tel.sigma2_slope[j] * err49[j], 14);
            sum += (int32_t)g_tel.w_m8[i][j] * col_term;
        }
        dx8[i] = rshift_rne(sum, 6);
    }

    /* ========================================================================
     * Equation 7: Layer 1 (M3) Weight Gradient (Direct Hadamard Product)
     *   dL / dW_{i,j}^(3) = <dz_j^(45) / dV_i^PTU>_Hadamard * dx_j^(8)
     *   CRITICAL: NO digital multiplication by primary input x_i^(3)!
     * ======================================================================== */
    for (int i = 0; i < 8; i++) {
        for (int j = 0; j < 6; j++) {
            int32_t prod = (int32_t)sens_m3[i][j] * dx8[j];
            grad_m3_out[i][j] = sat_q14(rshift_rne(prod, 3));
        }
    }
}

/* ============================================================================
 * Update 3D Loss Landscape / Basin Projection Telemetry (Direct Weight Projection)
 * ============================================================================ */
static void maml_project_weights_2d(const int16_t m3[8][6], const int16_t m8[7][6],
                                    const int8_t hid3[8][6], const int8_t hid8[7][6],
                                    int16_t *out_x, int16_t *out_y) {
    int32_t sx = 0, sy = 0;
    for (int r = 0; r < 8; r++) {
        for (int c = 0; c < 6; c++) {
            int32_t w = (int32_t)m3[r][c] + (hid3 ? ((int32_t)hid3[r][c] << 7) : 0);
            sx += ((r + c) & 1) ? w : -w;
        }
    }
    for (int r = 0; r < 7; r++) {
        for (int c = 0; c < 6; c++) {
            int32_t w = (int32_t)m8[r][c] + (hid8 ? ((int32_t)hid8[r][c] << 7) : 0);
            sy += ((r + c) & 1) ? w : -w;
        }
    }
    *out_x = (int16_t)(sx / (48 * 16));
    *out_y = (int16_t)(sy / (42 * 16));
}

static void maml_update_3d_landscape_coords(void) {
    maml_project_weights_2d(g_w0_m3_q14, g_w0_m8_q14, NULL, NULL,
                            &g_tel.w0_coord_x, &g_tel.w0_coord_y);

    uint32_t dist_sum = 0;
    for (int k = 0; k < NUM_BASINS; k++) {
        maml_project_weights_2d(g_basin_w_m3_q14[k], g_basin_w_m8_q14[k],
                                g_hid_w_m3[k], g_hid_w_m8[k],
                                &g_tel.basin_coord_x[k], &g_tel.basin_coord_y[k]);
        int32_t dx = (int32_t)g_tel.basin_coord_x[k] - (int32_t)g_tel.w0_coord_x;
        int32_t dy = (int32_t)g_tel.basin_coord_y[k] - (int32_t)g_tel.w0_coord_y;
        int32_t adx = (dx < 0) ? -dx : dx;
        int32_t ady = (dy < 0) ? -dy : dy;
        dist_sum += (uint32_t)(adx + ady);
    }
    g_tel.basin_spread_milli = (uint16_t)(dist_sum >> 2);
}

/* ============================================================================
 * Seed Randomization & Center Compensation Weights (128)
 * ============================================================================ */
static void maml_load_default_m33(void) {
    for (int r = 0; r < 6; r++) {
        for (int c = 0; c < 6; c++) {
            g_w_m33_q14[r][c] = (int16_t)((int32_t)k_default_m33[r][c] << 7);
        }
    }
    maml_sync_shadow_bytes();
}

static void maml_calibrate_zero_baseline(void);
static void maml_wait_10ms_refresh_tick(void);

static void maml_center_compensation_weights(void) {
    g_auto_random_data = 0u;
    memset(g_w0_m3_q14,  0, sizeof(g_w0_m3_q14));
    memset(g_w0_m8_q14,  0, sizeof(g_w0_m8_q14));
    memset(g_w_m3_q14,   0, sizeof(g_w_m3_q14));
    memset(g_w_m8_q14,   0, sizeof(g_w_m8_q14));
    memset(g_vel_m3_q14, 0, sizeof(g_vel_m3_q14));
    memset(g_vel_m8_q14, 0, sizeof(g_vel_m8_q14));
    for (int k = 0; k < NUM_BASINS; k++) {
        memset(g_basin_w_m3_q14[k], 0, sizeof(g_basin_w_m3_q14[k]));
        memset(g_basin_w_m8_q14[k], 0, sizeof(g_basin_w_m8_q14[k]));
    }
    /* Keep Layer 1 diagonal pass-through + row 6 bias active on M3 and +24 linear pedestal
     * on M8 so both single-supply COLTIA_3 and COLTIA_8 operate in their 1.65V linear center! */
    for (int c = 0; c < 6; c++) {
        g_w0_m3_q14[c][c] = (int16_t)(64 << 7);
        g_w_m3_q14[c][c]  = (int16_t)(64 << 7);
        g_w0_m3_q14[6][c] = (int16_t)(48 << 7);
        g_w_m3_q14[6][c]  = (int16_t)(48 << 7);
        for (int r = 0; r < 6; r++) {
            g_w0_m8_q14[r][c] = (int16_t)(24 << 7);
            g_w_m8_q14[r][c]  = (int16_t)(24 << 7);
        }
    }
    /* Preserve Primary Payload Matrix M33 (k_default_m33) so COLTIA stays centered! */
    maml_load_default_m33();

    /* Calibrate quiescent zero-input baseline at DAC_2 = 128 and 100 Hz (10.0 ms) cadence */
    maml_calibrate_zero_baseline();

    /* Restore M3 and M8 linear center weights after calibration */
    for (int c = 0; c < 6; c++) {
        g_w0_m3_q14[c][c] = (int16_t)(64 << 7);
        g_w_m3_q14[c][c]  = (int16_t)(64 << 7);
        g_w0_m3_q14[6][c] = (int16_t)(48 << 7);
        g_w_m3_q14[6][c]  = (int16_t)(48 << 7);
        for (int r = 0; r < 6; r++) {
            g_w0_m8_q14[r][c] = (int16_t)(24 << 7);
            g_w_m8_q14[r][c]  = (int16_t)(24 << 7);
        }
    }

    /* Apply active reference input vector x_ref and compute zero-referenced z_target */
    maml_generate_new_white_noise_ref();

    g_comp_is_centered = 1;
    uint32_t settle_dly_us = (g_hadamard_delay_us > 0 && g_hadamard_delay_us <= 9500u) ?
                             g_hadamard_delay_us : 5000u;
    /* Let the 100 nF gate capacitors settle at the exact 10.0 ms (100 Hz) cadence */
    for (int rep = 0; rep < 3; rep++) {
        maml_wait_10ms_refresh_tick();
        bsp_uDelay(settle_dly_us);
    }

    /* Measure uncompensated bit precision at centered compensation weights */
    uint8_t saved_jm = g_tel.jumper_mode;
    g_tel.jumper_mode = JUMPER_OFF_NO_COMP;
    int16_t gm3[8][6], gm8[7][6];
    maml_measure_and_extract_gradients(0, gm3, gm8);
    g_tel.jumper_mode = saved_jm;
    g_tel.bit_prec_comp_centi = g_tel.bit_prec_uncomp_centi;
    for (int k = 0; k < NUM_BASINS; k++) {
        g_tel.basin_loss_milli[k] = g_tel.loss_total_milli;
    }
    maml_update_3d_landscape_coords();
}

static void maml_seed_weights(uint8_t mode, uint8_t swing_pct) {
    if (swing_pct > 100) swing_pct = 100;
    g_tel.seed_mode      = mode;
    g_tel.seed_swing_pct = swing_pct;
    g_comp_is_centered   = 0;

    /* Convert swing_pct (0..100%) to Q1.14 amplitude (127 DAC LSBs = 127 << 7 = 16256) */
    int32_t max_q14 = (16256 * (int32_t)swing_pct) / 100;
    if (mode == SEED_MODE_AUTO_GAIN) {
        /* Standard Xavier/Kaiming gain (~28% of full swing for 6-input fan-in) */
        max_q14 = (16256 * 28) / 100;
        g_tel.seed_swing_pct = 28;
    }

    for (int r = 0; r < 8; r++) {
        for (int c = 0; c < 6; c++) {
            int32_t v = 0;
            if (max_q14 > 0) {
                if (mode == SEED_MODE_ORTHOGONAL) {
                    int bit = (HADAMARD_16[r + 1] >> c) & 1;
                    v = bit ? max_q14 : -max_q14;
                } else if (mode == SEED_MODE_CHECKERBOARD) {
                    v = ((r + c) & 1) ? max_q14 : -max_q14;
                } else {
                    v = (int32_t)(prng_next() % (uint32_t)(2 * max_q14 + 1)) - max_q14;
                }
            }
            /* Add diagonal pass-through on Layer 1 (M3) so ACT(4)_D_ROW[0..5] drives M8 cleanly */
            if (r == c && r < 6 && g_tel.jumper_mode != JUMPER_OFF_NO_COMP) {
                v += (64 << 7);
            }
            g_w0_m3_q14[r][c]  = sat_q14(v);
            g_w_m3_q14[r][c]   = sat_q14(v);
            g_vel_m3_q14[r][c] = 0;
            for (int k = 0; k < NUM_BASINS; k++) {
                g_basin_w_m3_q14[k][r][c] = sat_q14(v);
            }
        }
    }

    for (int r = 0; r < 7; r++) {
        for (int c = 0; c < 6; c++) {
            int32_t v = 0;
            if (max_q14 > 0) {
                if (mode == SEED_MODE_ORTHOGONAL) {
                    int bit = (HADAMARD_16[r + 8] >> c) & 1;
                    v = bit ? max_q14 : -max_q14;
                } else if (mode == SEED_MODE_CHECKERBOARD) {
                    v = ((r + c) & 1) ? -max_q14 : max_q14;
                } else {
                    v = (int32_t)(prng_next() % (uint32_t)(2 * max_q14 + 1)) - max_q14;
                }
            }
            g_w0_m8_q14[r][c]  = sat_q14(v);
            g_w_m8_q14[r][c]   = sat_q14(v);
            g_vel_m8_q14[r][c] = 0;
            for (int k = 0; k < NUM_BASINS; k++) {
                g_basin_w_m8_q14[k][r][c] = sat_q14(v);
            }
        }
    }

    if (g_tel.jumper_mode == JUMPER_OFF_NO_COMP) {
        /* Randomize Matrix 33 in Mode B with +16 pedestal so weights actively refresh */
        for (int r = 0; r < 6; r++) {
            for (int c = 0; c < 6; c++) {
                int32_t v = (16 << 7);
                if (max_q14 > 0) {
                    if (mode == SEED_MODE_CHECKERBOARD) {
                        v += ((r + c) & 1) ? max_q14 : -max_q14;
                    } else {
                        v += (int32_t)(prng_next() % (uint32_t)(2 * max_q14 + 1)) - max_q14;
                    }
                }
                g_w_m33_q14[r][c] = sat_q14(v);
            }
        }
    } else {
        maml_load_default_m33();
    }
    maml_sync_shadow_bytes();
    maml_recompute_z_target();

    g_tel.outer_loop_epoch = 0;
    g_tel.cur_inner_step   = 0;
    maml_refresh_all_columns();
    bsp_uDelay((g_hadamard_delay_us > 0 && g_hadamard_delay_us <= 9500u) ? g_hadamard_delay_us : 5000u);

    /* Measure initial compensated bit precision from live hardware */
    int16_t gm3[8][6], gm8[7][6];
    maml_measure_and_extract_gradients(0, gm3, gm8);
    for (int k = 0; k < NUM_BASINS; k++) {
        g_tel.basin_loss_milli[k] = g_tel.loss_total_milli;
        g_tel.basin_hess_dot[k]   = 0;
    }
    maml_update_3d_landscape_coords();
}

/* Sample a new Hardware Hidden Offset state for Basin k (Ref 40/41 Emulator) */
static void maml_sample_hidden_offset(uint8_t basin_k) {
    int32_t amp = (int32_t)g_hid_amp_dac;
    if (amp < 2) amp = 2;
    const int8_t signs_x[4] = {-1, +1, -1, +1};
    const int8_t signs_y[4] = {-1, -1, +1, +1};
    for (int r = 0; r < 8; r++) {
        for (int c = 0; c < 6; c++) {
            int32_t jitter = (int32_t)(prng_next() % 5u) - 2;
            g_hid_w_m3[basin_k][r][c] = sat_dac_off(signs_x[basin_k] * (amp / 2) + jitter);
        }
    }
    for (int r = 0; r < 7; r++) {
        for (int c = 0; c < 6; c++) {
            int32_t jitter = (int32_t)(prng_next() % 5u) - 2;
            g_hid_w_m8[basin_k][r][c] = sat_dac_off(signs_y[basin_k] * (amp / 2) + jitter);
        }
    }
    g_hid_trim[basin_k] = sat_dac_off(signs_x[basin_k] * (amp / 3));
}

static void aio_load_all_30_dacs(uint8_t code);
static void maml_apply_fixed_even_dac2(void);
static void maml_seed_fixed_test_weights_once(uint32_t seed_val);

/* Calibrate quiescent DC zero baseline at x_ref = 0 (DAC_2 = 128) with M33 payload charged
 * and M3/M8 in their linear center (M3 diag = +64, row6 = +48, M8 = +24) at 100 Hz (10.0 ms) cadence */
static void maml_calibrate_zero_baseline(void) {
    t20_hadamard_tristate_center();
    uint8_t d2_mid[6] = {128, 128, 128, 128, 128, 128};
    g_dac_row7_code = 128u;
    g_dac_row8_code = 128u;
    aio_load_dac2(d2_mid);
    memset(g_w_m3_q14, 0, sizeof(g_w_m3_q14));
    memset(g_w_m8_q14, 0, sizeof(g_w_m8_q14));
    for (int c = 0; c < 6; c++) {
        g_w_m3_q14[c][c] = (int16_t)(64 << 7);
        g_w_m3_q14[6][c] = (int16_t)(48 << 7);
        for (int r = 0; r < 6; r++) {
            g_w_m8_q14[r][c] = (int16_t)(24 << 7);
        }
    }

    uint32_t settle_dly_us = (g_hadamard_delay_us > 0 && g_hadamard_delay_us <= 9500u) ?
                             g_hadamard_delay_us : 5000u;

    g_last_refresh_ticks = clint_getTimeLow(BSP_CLINT);
    for (int rep = 0; rep < 3; rep++) {
        maml_wait_10ms_refresh_tick();
    }

    int32_t acc45[6] = {0, 0, 0, 0, 0, 0};
    int32_t acc49[6] = {0, 0, 0, 0, 0, 0};
    for (int i = 0; i < 4; i++) {
        maml_wait_10ms_refresh_tick();
        bsp_uDelay(settle_dly_us);
        t20_hadamard_tristate_center();
        bsp_uDelay(10);
        int16_t a45[6], a49[6];
        aio_trigger_settled_adc_read(a45, a49);
        for (int c = 0; c < 6; c++) {
            acc45[c] += a45[c];
            acc49[c] += a49[c];
        }
    }
    for (int c = 0; c < 6; c++) {
        g_adc45_zero_cal[c] = (int16_t)rshift_rne(acc45[c], 2);
        g_adc49_zero_cal[c] = (int16_t)rshift_rne(acc49[c], 2);
    }
}

/* ============================================================================
 * Platform Initialization
 * ============================================================================ */
void maml_platform_init(void) {
    memset(&g_tel, 0, sizeof(g_tel));
    g_tel.magic              = MAML_MAGIC;
    g_tel.msg_type           = 0x90;
    g_tel.run_mode           = MAML_MODE_IDLE;
    g_tel.jumper_mode        = JUMPER_USE_SIG2;
    g_tel.heater_armed       = 0;
    g_tel.hadamard_freq_khz  = 500; /* Default 500 kHz -> 2.0 us quiet DC settle */
    g_tel.max_meas_duty_pct  = 25;
    g_tel.seed_mode          = SEED_MODE_AUTO_GAIN;
    g_tel.seed_swing_pct     = 28;
    g_tel.inner_loop_n       = 100; /* Default N = 100 inner loop iterations */
    g_tel.num_strata_m       = NUM_STRATA_DEFAULT;
    g_tel.settle_cycles      = 100;
    g_tel.bit_prec_uncomp_centi = 0; /* Strictly measured from live hardware */
    g_tel.bit_prec_comp_centi   = 0; /* Strictly measured from live hardware */

    /* Initialize Primary Payload Matrix M33 with pedestaled full-rank target matrix */
    maml_load_default_m33();

    for (uint8_t k = 0; k < NUM_BASINS; k++) {
        maml_sample_hidden_offset(k);
    }

    /* Configure T120 Analog IO Controller:
     * sclr_n=1, auto_h_adc=1, pi_inv=1, r_adc_bit_align=2 (w[11:0] 12-bit), sck_div=15 (280ns SCK/RCK HIGH) */
    AIO_REG(AIO_CTRL)          = 0x00000FA9u;
    AIO_REG(AIO_SETTLE_CYCLES) = (25u << 16) | 100u;

    maml_shuffle_outer_slots();
    maml_center_compensation_weights();
    g_tel.run_mode = MAML_MODE_IDLE;
    g_last_refresh_ticks = clint_getTimeLow(BSP_CLINT);
    t20_sync_heater_and_wdog();
    t20_sync_leds();
}

/* ============================================================================
 * Execute One Full MAML Training / Compensation Step
 *   - Enforces white-noise reference lock across the inner trajectory
 *   - Enforces Equations 1-7 (no digital multiplication by x_i)
 *   - Enforces Inner Loop (Ref 41) & Dot-Product Second-Derivative Outer Loop (Ref 40)
 * ============================================================================ */
static void maml_execute_step(void) {
    int16_t gm3[8][6], gm8[7][6];

    if (g_tel.run_mode == MAML_MODE_BASE_TRAIN) {
        /* --------------------------------------------------------------------
         * Base Model Training Mode (Ref 40 Outer Loop + Ref 41 Inner Loop)
         * 1 clean settled measurement + Hadamard extraction per 10 ms refresh!
         * -------------------------------------------------------------------- */
        if (g_tel.cur_inner_step == 0 && g_cur_basin_idx < NUM_BASINS) {
            /* If g_hid_amp_dac > 0: MAML meta-learning with basin hopping.
             * If g_hid_amp_dac == 0: Pure inner loop neural network training (no outer reset,
             * and reference input x_ref remains locked for monotonic convergence!) */
            if (g_hid_amp_dac > 0) {
                memcpy(g_w_m3_q14, g_w0_m3_q14, sizeof(g_w_m3_q14));
                memcpy(g_w_m8_q14, g_w0_m8_q14, sizeof(g_w_m8_q14));
                maml_sample_hidden_offset(g_cur_basin_idx);
                maml_generate_new_white_noise_ref();
            }
        }

        maml_shuffle_outer_slots();
        maml_refresh_all_columns();

        /* Wait until the programmable plateau delay (default 5000 us = 5.0 ms) after refresh
         * so 2T1C gate capacitors and column amplifiers are 100% settled! */
        uint32_t settle_dly_us = (g_hadamard_delay_us > 0 && g_hadamard_delay_us <= 9500u) ?
                                 g_hadamard_delay_us : 5000u;
        bsp_uDelay(settle_dly_us);

        memset(g_acc_grad_m3, 0, sizeof(g_acc_grad_m3));
        memset(g_acc_grad_m8, 0, sizeof(g_acc_grad_m8));

        uint8_t m = 1u;
        g_tel.cur_stratum_slot = g_slot_perm[0];
        maml_measure_and_extract_gradients(g_tel.cur_stratum_slot, gm3, gm8);
        for (int r = 0; r < 8; r++)
            for (int c = 0; c < 6; c++)
                g_acc_grad_m3[r][c] = gm3[r][c];
        for (int r = 0; r < 7; r++)
            for (int c = 0; c < 6; c++)
                g_acc_grad_m8[r][c] = gm8[r][c];

        /* Average gradient across the M strata and update Inner Loop weights (Ref 41) */
        for (int r = 0; r < 8; r++) {
            for (int c = 0; c < 6; c++) {
                int16_t g_avg = sat_q14(g_acc_grad_m3[r][c] / (int32_t)m);
                if (g_tel.cur_inner_step == 0) g_grad_init_m3[r][c] = g_avg;
                g_grad_final_m3[r][c] = g_avg;
                int32_t step_w = rshift_rne((int32_t)g_avg * (int32_t)g_lr_inner_q16, 12);
                g_w_m3_q14[r][c] = sat_w80_q14((int32_t)g_w_m3_q14[r][c] - step_w);
                if (g_hid_amp_dac == 0) {
                    g_w0_m3_q14[r][c] = g_w_m3_q14[r][c];
                }
                if (g_cur_basin_idx < NUM_BASINS) {
                    g_basin_w_m3_q14[g_cur_basin_idx][r][c] = g_w_m3_q14[r][c];
                }
            }
        }
        for (int r = 0; r < 7; r++) {
            for (int c = 0; c < 6; c++) {
                int16_t g_avg = sat_q14(g_acc_grad_m8[r][c] / (int32_t)m);
                if (g_tel.cur_inner_step == 0) g_grad_init_m8[r][c] = g_avg;
                g_grad_final_m8[r][c] = g_avg;
                int32_t step_w = rshift_rne((int32_t)g_avg * (int32_t)g_lr_inner_q16, 12);
                g_w_m8_q14[r][c] = sat_w80_q14((int32_t)g_w_m8_q14[r][c] - step_w);
                if (g_hid_amp_dac == 0) {
                    g_w0_m8_q14[r][c] = g_w_m8_q14[r][c];
                }
                if (g_cur_basin_idx < NUM_BASINS) {
                    g_basin_w_m8_q14[g_cur_basin_idx][r][c] = g_w_m8_q14[r][c];
                }
            }
        }

        if (g_cur_basin_idx < NUM_BASINS) {
            g_tel.basin_loss_milli[g_cur_basin_idx] = g_tel.loss_total_milli;
        }
        if (g_tel.cur_inner_step == 0 && g_cur_basin_idx == 0) {
            g_tel.w0_loss_milli = g_tel.loss_total_milli;
        }

        g_tel.cur_inner_step += (m == 1) ? 1u : 5u;
        if (g_tel.cur_inner_step >= g_tel.inner_loop_n) {
            if (g_hid_amp_dac > 0) {
                /* Outer Loop (Ref 40): Memory-Safe Dot-Product Second Derivative!
                 * Applied only when outer MAML meta-learning is active (w_hid_mag > 0) */
                int64_t dot_prod = 0;
                int64_t norm_sq  = 1024;
                for (int r = 0; r < 8; r++) {
                    for (int c = 0; c < 6; c++) {
                        dot_prod += (int64_t)g_grad_init_m3[r][c] * (int64_t)g_grad_final_m3[r][c];
                        norm_sq  += (int64_t)g_grad_init_m3[r][c] * (int64_t)g_grad_init_m3[r][c];
                    }
                }
                for (int r = 0; r < 7; r++) {
                    for (int c = 0; c < 6; c++) {
                        dot_prod += (int64_t)g_grad_init_m8[r][c] * (int64_t)g_grad_final_m8[r][c];
                        norm_sq  += (int64_t)g_grad_init_m8[r][c] * (int64_t)g_grad_init_m8[r][c];
                    }
                }
                int16_t d_align_q14 = sat_q14((int32_t)((dot_prod << 14) / norm_sq));
                g_tel.basin_hess_dot[g_cur_basin_idx] = d_align_q14;

                /* Apply second-derivative curvature correction to Base Model W_0 */
                for (int r = 0; r < 8; r++) {
                    for (int c = 0; c < 6; c++) {
                        int32_t dg = (int32_t)g_grad_final_m3[r][c] - (int32_t)g_grad_init_m3[r][c];
                        int32_t h_corr = rshift_rne((int32_t)d_align_q14 * dg, 15);
                        int32_t g_meta = (int32_t)g_grad_final_m3[r][c] - h_corr;
                        int32_t pull   = ((int32_t)g_w0_m3_q14[r][c] - (int32_t)g_w_m3_q14[r][c]) >> 3;
                        int32_t delta  = rshift_rne(g_meta * (int32_t)g_lr_outer_q16, 12) + pull;
                        g_w0_m3_q14[r][c] = sat_q14((int32_t)g_w0_m3_q14[r][c] - delta);
                    }
                }
                for (int r = 0; r < 7; r++) {
                    for (int c = 0; c < 6; c++) {
                        int32_t dg = (int32_t)g_grad_final_m8[r][c] - (int32_t)g_grad_init_m8[r][c];
                        int32_t h_corr = rshift_rne((int32_t)d_align_q14 * dg, 15);
                        int32_t g_meta = (int32_t)g_grad_final_m8[r][c] - h_corr;
                        int32_t pull   = ((int32_t)g_w0_m8_q14[r][c] - (int32_t)g_w_m8_q14[r][c]) >> 3;
                        int32_t delta  = rshift_rne(g_meta * (int32_t)g_lr_outer_q16, 12) + pull;
                        g_w0_m8_q14[r][c] = sat_q14((int32_t)g_w0_m8_q14[r][c] - delta);
                    }
                }
                g_cur_basin_idx = (g_cur_basin_idx + 1u) % NUM_BASINS;
            }

            g_tel.cur_inner_step = 0;
            g_tel.outer_loop_epoch++;
            maml_update_3d_landscape_coords();
        } else {
            maml_update_3d_landscape_coords();
        }
    } else if (g_tel.run_mode == MAML_MODE_OPERATIONAL) {
        /* --------------------------------------------------------------------
         * Operational Mode (Ref 42):
         *   - Hidden Offset Emulator is ZEROED.
         *   - 1 measurement window per refresh cycle at shuffled slot P[cursor],
         *     holding the EXACT SAME white-noise reference x_ref locked across
         *     all M refresh cycles until 100% of time slots are covered!
         * -------------------------------------------------------------------- */
        if (g_slot_cursor == 0) {
            maml_generate_new_white_noise_ref();
            maml_shuffle_outer_slots();
            memset(g_acc_grad_m3, 0, sizeof(g_acc_grad_m3));
            memset(g_acc_grad_m8, 0, sizeof(g_acc_grad_m8));
        }

        maml_refresh_all_columns();

        uint8_t slot = g_slot_perm[g_slot_cursor];
        g_tel.cur_stratum_slot = slot;

        /* Single-point deterministic time delay (e.g. 2500 us or 3000 us) when num_strata_m == 1 */
        uint32_t slot_delay_us = (g_tel.num_strata_m == 1 && g_hadamard_delay_us > 0) ?
                                 g_hadamard_delay_us :
                                 ((uint32_t)slot * (uint32_t)g_tel.settle_cycles);
        if (slot_delay_us > 0 && slot_delay_us <= 9500) {
            bsp_uDelay(slot_delay_us);
        }

        maml_measure_and_extract_gradients(slot, gm3, gm8);
        for (int r = 0; r < 8; r++)
            for (int c = 0; c < 6; c++)
                g_acc_grad_m3[r][c] += gm3[r][c];
        for (int r = 0; r < 7; r++)
            for (int c = 0; c < 6; c++)
                g_acc_grad_m8[r][c] += gm8[r][c];

        g_slot_cursor++;
        if (g_slot_cursor >= g_tel.num_strata_m) {
            /* All M time slots across the refresh period have been sampled with locked x_ref!
             * Apply the full-cycle temporal delta with momentum to M3 & M8. */
            uint8_t m = g_tel.num_strata_m;
            for (int r = 0; r < 8; r++) {
                for (int c = 0; c < 6; c++) {
                    int32_t g_avg = g_acc_grad_m3[r][c] / (int32_t)m;
                    int32_t v_new = rshift_rne((int32_t)g_vel_m3_q14[r][c] * (int32_t)g_momentum_q16, 16) +
                                    rshift_rne(g_avg * (int32_t)g_lr_inner_q16, 12);
                    g_vel_m3_q14[r][c] = sat_q14(v_new);
                    g_w_m3_q14[r][c]   = sat_q14((int32_t)g_w_m3_q14[r][c] - (int32_t)g_vel_m3_q14[r][c]);
                    g_w0_m3_q14[r][c]  = g_w_m3_q14[r][c];
                }
            }
            for (int r = 0; r < 7; r++) {
                for (int c = 0; c < 6; c++) {
                    int32_t g_avg = g_acc_grad_m8[r][c] / (int32_t)m;
                    int32_t v_new = rshift_rne((int32_t)g_vel_m8_q14[r][c] * (int32_t)g_momentum_q16, 16) +
                                    rshift_rne(g_avg * (int32_t)g_lr_inner_q16, 12);
                    g_vel_m8_q14[r][c] = sat_q14(v_new);
                    g_w_m8_q14[r][c]   = sat_q14((int32_t)g_w_m8_q14[r][c] - (int32_t)g_vel_m8_q14[r][c]);
                    g_w0_m8_q14[r][c]  = g_w_m8_q14[r][c];
                }
            }
            g_slot_cursor = 0;
            g_tel.outer_loop_epoch++;
            maml_update_3d_landscape_coords();
        }
    }
}

static void aio_load_all_30_dacs(uint8_t code) {
    uint32_t b   = (uint32_t)bitrev8(code);
    uint32_t w32 = b | (b << 8) | (b << 16) | (b << 24);
    AIO_REG(AIO_DAC2_LO) = w32;
    AIO_REG(AIO_DAC2_HI) = w32 & 0x0000FFFFu;
    aio_wait_dac_ready();
    AIO_REG(AIO_W15_LO)  = w32;
    AIO_REG(AIO_W15_HI)  = w32;
    aio_wait_dac_ready();
    AIO_REG(AIO_W12_LO)  = w32;
    AIO_REG(AIO_W12_HI)  = w32;
    aio_wait_dac_ready();
    AIO_REG(AIO_W34_LO)  = w32;
    AIO_REG(AIO_W34_HI)  = w32;
    aio_wait_dac_ready();
    AIO_REG(AIO_CMD)     = 0x0Fu;
    aio_wait_dac_ready();
}

/* ============================================================================
 * Periodic Background Tick (Synchronous Autonomous 10.0 ms Refresh Engine)
 * ============================================================================ */
static uint8_t g_osc_phase = 0;
static uint8_t g_alt_hadamard_on = 0;

static void maml_apply_fixed_even_dac2(void) {
    const uint8_t d2_even[6] = { 0u, 51u, 102u, 153u, 204u, 255u };
    for (int i = 0; i < 6; i++) {
        g_tel.x_ref[i] = (int16_t)((int32_t)d2_even[i] - 128);
    }
    aio_load_dac2(d2_even);
}

static void maml_seed_fixed_test_weights_once(uint32_t seed_val) {
    g_prng_state = seed_val ? seed_val : 0x5A3C9E4Du;
    g_comp_is_centered = 0;
    for (int r = 0; r < 8; r++) {
        for (int c = 0; c < 6; c++) {
            int32_t off = (int32_t)(prng_next() % 161u) - 80; /* [-80, +80] DAC LSBs */
            g_w0_m3_q14[r][c] = (int16_t)(off << 7);
            g_w_m3_q14[r][c]  = (int16_t)(off << 7);
        }
    }
    for (int r = 0; r < 7; r++) {
        for (int c = 0; c < 6; c++) {
            int32_t off = (int32_t)(prng_next() % 161u) - 80; /* [-80, +80] DAC LSBs */
            g_w0_m8_q14[r][c] = (int16_t)(off << 7);
            g_w_m8_q14[r][c]  = (int16_t)(off << 7);
        }
    }
    for (int r = 0; r < 6; r++) {
        for (int c = 0; c < 6; c++) {
            int32_t off = (int32_t)(prng_next() % 161u) - 80; /* [-80, +80] DAC LSBs */
            g_w_m33_q14[r][c] = (int16_t)(off << 7);
        }
    }
    maml_sync_shadow_bytes();
}

static void maml_flip_all_weights_sign(void) {
    for (int r = 0; r < 8; r++) {
        for (int c = 0; c < 6; c++) {
            g_w0_m3_q14[r][c] = (int16_t)(-g_w0_m3_q14[r][c]);
            g_w_m3_q14[r][c]  = (int16_t)(-g_w_m3_q14[r][c]);
        }
    }
    for (int r = 0; r < 7; r++) {
        for (int c = 0; c < 6; c++) {
            g_w0_m8_q14[r][c] = (int16_t)(-g_w0_m8_q14[r][c]);
            g_w_m8_q14[r][c]  = (int16_t)(-g_w_m8_q14[r][c]);
        }
    }
    for (int r = 0; r < 6; r++) {
        for (int c = 0; c < 6; c++) {
            g_w_m33_q14[r][c] = (int16_t)(-g_w_m33_q14[r][c]);
        }
    }
    maml_sync_shadow_bytes();
}

void maml_platform_tick(void) {
    g_wdog_refresh_cnt++;
    if ((g_wdog_refresh_cnt % 2000u) == 0) {
        t20_sync_heater_and_wdog();
    }

    /* 3-state DAC Swing: 255 (MAX) -> 128 (CENTER) -> 0 (MIN)
     * Driven with bitrev8() so 74HC595 QA (pin 15, R-2R MSB) outputs true 1.65V at 128! */
    if (g_tel.osc_10hz_en) {
        if ((g_wdog_refresh_cnt % 6000u) == 0) {
            g_osc_phase = (uint8_t)((g_osc_phase + 1u) % 3u);
            uint8_t code = (g_osc_phase == 0u) ? 255u : ((g_osc_phase == 1u) ? 128u : 0u);
            aio_load_all_30_dacs(code);
        } else if ((g_wdog_refresh_cnt % 200u) == 0) {
            AIO_REG(AIO_CMD) = 0x0Fu;
        }
        return;
    }

    if (g_tel.ovr_en) {
        /* Continuously re-shift the static DAC override so an oscilloscope on SCK/RCK triggers cleanly */
        if ((g_wdog_refresh_cnt % 200u) == 0) {
            AIO_REG(AIO_CMD) = 0x0Fu;
        }
        return;
    }

    /* Hardware-Synchronous Autonomous Refresh Timer (50 MHz CLINT -> 50 ticks/us):
     * Default g_refresh_period_us = 10000 us (10.0 ms = 500,000 CLINT ticks).
     * Runs continuously in ALL modes (IDLE, HOLD, BASE_TRAIN, OPERATIONAL) so the
     * 100 nF 2T1C gate capacitors across all 126 cells are refreshed every 10.0 ms! */
    uint32_t now_ticks    = clint_getTimeLow(BSP_CLINT);
    uint32_t period_ticks = g_refresh_period_us * 50u;
    if ((uint32_t)(now_ticks - g_last_refresh_ticks) >= period_ticks) {
        g_last_refresh_ticks = now_ticks;

        /* Always run the 100 Hz (10.0 ms) column refresh + Hadamard carrier burst at the programmable delay */
        if (g_tel.run_mode != MAML_MODE_BASE_TRAIN && g_tel.run_mode != MAML_MODE_OPERATIONAL) {
            if (g_auto_random_data) {
                maml_generate_new_white_noise_ref();
            }
            maml_refresh_all_columns();
            uint32_t delay_us = g_hadamard_delay_us;
            if (delay_us > 9500u) delay_us = 9500u;
            if (delay_us > 0) {
                bsp_uDelay(delay_us);
            }
            /* Read settled quiet forward-pass ADC_45 & ADC_49, run Hadamard bursts, and update live loss/ENOB */
            int16_t gm3_idle[8][6], gm8_idle[7][6];
            maml_measure_and_extract_gradients(0, gm3_idle, gm8_idle);
        } else {
            maml_execute_step();
        }
    }
}

/* ============================================================================
 * Cell-by-Cell Self-Diagnosis Probe (100% Pure Hardware ADC Measurements)
 * ============================================================================ */
static void maml_probe_charge_column(uint8_t matrix_id, uint8_t row, uint8_t col, int32_t w_signed) {
    memset(g_w_m3_q14,  0, sizeof(g_w_m3_q14));
    memset(g_w_m8_q14,  0, sizeof(g_w_m8_q14));
    memset(g_w_m33_q14, 0, sizeof(g_w_m33_q14));

    int16_t w_q14 = (int16_t)(w_signed << 7);
    if (col < 6u) {
        g_focus_col = col;
        if (matrix_id == 0u && row < 8u) {
            g_w_m3_q14[row][col] = w_q14;
        }
        if (matrix_id == 1u && row < 7u) {
            /* Matrix 8 rows 0..5 are driven by ACT(4)_D_ROW[0..5] (Layer 1 Matrix 3 outputs).
             * Enable Layer 1 pass-through on M3[row][row] so DAC_2[row] drives ACT(4)_D_ROW[row]. */
            if (row < 6u) {
                g_w_m3_q14[row][row] = (int16_t)(96 << 7);
            }
            /* Bias an unused row of Matrix 33 ((row+3)%6, held at constant DAC_2=128) at +48
             * so the shared single-supply COLTIA diff-amp (U1/U2$CBB15 -> ADC_49) stays above 0.0V
             * in its linear region for both W < 0 and W > 0 on Matrix 8. */
            uint8_t ped_row = (uint8_t)((row + 3u) % 6u);
            g_w_m33_q14[ped_row][col] = (int16_t)(48 << 7);
            g_w_m8_q14[row][col]      = w_q14;
        }
        if (matrix_id == 2u && row < 6u) {
            /* Bias an unused row ((row+3)%6, held at constant DAC_2=128) at +48 so the
             * single-supply COLTIA diff-amp (U1/U2$CBB15, R_ref->GND) stays above 0.0V
             * for both W < 0 and W > 0. Cancels out identically in base49 and raw49. */
            uint8_t ped_row = (uint8_t)((row + 3u) % 6u);
            g_w_m33_q14[ped_row][col] = (int16_t)(48 << 7);
            g_w_m33_q14[row][col]     = w_q14;
        }
    }

    /* Physical charging time constant: R2 = 1 kOhm, C = 100 nF -> tau_charge = 100 us.
     * Refresh across all columns so (matrix_id, row, col) charges cleanly to target weight. */
    maml_refresh_all_columns();
}

static void maml_wait_10ms_refresh_tick(void) {
    uint32_t period_ticks = g_refresh_period_us * 50u;
    while ((uint32_t)(clint_getTimeLow(BSP_CLINT) - g_last_refresh_ticks) < period_ticks) {
        /* Wait cleanly for the 100 Hz timer boundary */
    }
    g_last_refresh_ticks = clint_getTimeLow(BSP_CLINT);
    maml_refresh_all_columns();
}

static uint16_t maml_probe_single_cell(uint8_t matrix_id, uint8_t row, uint8_t col,
                                       int8_t x_amp, int8_t w_fixed, uint8_t mode_flag,
                                       uint16_t snap_dly_us,
                                       uint8_t *resp_buf, uint16_t resp_max) {
    if (resp_max < sizeof(maml_cell_probe_resp_t)) return 0;
    maml_cell_probe_resp_t resp;
    memset(&resp, 0, sizeof(resp));
    resp.magic     = MAML_MAGIC;
    resp.msg_type  = 0x97;
    resp.matrix_id = matrix_id;
    resp.row       = row;
    resp.col       = col;

    /* Probing a single cell pauses/disables autonomous random data generator */
    g_auto_random_data = 0u;

    /* Save active Q2.14 weight matrices so non-hold probes restore them cleanly */
    int16_t saved_m3[8][6];
    int16_t saved_m8[7][6];
    int16_t saved_m33[6][6];
    memcpy(saved_m3,  g_w_m3_q14,  sizeof(saved_m3));
    memcpy(saved_m8,  g_w_m8_q14,  sizeof(saved_m8));
    memcpy(saved_m33, g_w_m33_q14, sizeof(saved_m33));

    AIO_REG(AIO_CTRL) = 0x00000FA9u;

    /* Ensure Hadamard is 3-stated (Hi-Z centered) during static cell characterization */
    t20_hadamard_tristate_center();

    /* Multiplier snapshot delay (0..9500 us) chosen freely by the user.
     * Decoupled from Hadamard! If snap_dly_us is explicitly passed (> 0), honor user value directly.
     * If snap_dly_us == 0, default to 2500 us. */
    uint32_t settle_dly_us = (snap_dly_us > 0u && snap_dly_us <= 9500u) ? (uint32_t)snap_dly_us : 2500u;

    /* Measure quiescent column baseline at d2 = 128 (X = 0), w = 0 right after refresh */
    uint8_t d2_mid[6] = {128, 128, 128, 128, 128, 128};
    g_dac_row7_code = 128u;
    g_dac_row8_code = 128u;
    aio_load_dac2(d2_mid);
    maml_probe_charge_column(matrix_id, row, col, 0);
    bsp_uDelay(settle_dly_us);
    int16_t base45[6], base49[6];
    aio_trigger_settled_adc_read(base45, base49);

    int16_t raw45_zero[6], raw49_zero[6];
    int16_t raw45_pos[6],  raw49_pos[6];
    int16_t raw45_neg[6],  raw49_neg[6];

    if (mode_flag & 0x01u) {
        /* --------------------------------------------------------------------
         * Fixed-Weight Input-Up/Down Multiplier Mode (mode_flag bit 0 = 1):
         *   Each measurement (X = 0, X = +x_amp, X = -x_amp) is preceded by a
         *   fresh synchronous column refresh, settling cleanly on the plateau!
         * -------------------------------------------------------------------- */
        /* 1. X = 0 (all DAC_2 = 128) at fixed weight W = w_fixed */
        g_dac_row7_code = 128u;
        g_dac_row8_code = 128u;
        aio_load_dac2(d2_mid);
        maml_probe_charge_column(matrix_id, row, col, (int32_t)w_fixed);
        bsp_uDelay(settle_dly_us);
        aio_trigger_settled_adc_read(raw45_zero, raw49_zero);

        /* 2. X = +x_amp on probed row (move input UP) at fixed weight W = w_fixed */
        uint8_t d2_pos[6] = {128, 128, 128, 128, 128, 128};
        g_dac_row7_code = 128u;
        g_dac_row8_code = 128u;
        if (row < 6u) {
            d2_pos[row] = off_to_dac_u8(+(int32_t)x_amp);
        } else if (row == 6u) {
            g_dac_row7_code = off_to_dac_u8(+(int32_t)x_amp);
        } else if (row == 7u) {
            g_dac_row8_code = off_to_dac_u8(+(int32_t)x_amp);
        }
        aio_load_dac2(d2_pos);
        maml_refresh_all_columns();
        bsp_uDelay(settle_dly_us);
        aio_trigger_settled_adc_read(raw45_pos, raw49_pos);

        /* 3. X = -x_amp on probed row (move input DOWN) at fixed weight W = w_fixed */
        uint8_t d2_neg[6] = {128, 128, 128, 128, 128, 128};
        g_dac_row7_code = 128u;
        g_dac_row8_code = 128u;
        if (row < 6u) {
            d2_neg[row] = off_to_dac_u8(-(int32_t)x_amp);
        } else if (row == 6u) {
            g_dac_row7_code = off_to_dac_u8(-(int32_t)x_amp);
        } else if (row == 7u) {
            g_dac_row8_code = off_to_dac_u8(-(int32_t)x_amp);
        }
        aio_load_dac2(d2_neg);
        maml_refresh_all_columns();
        bsp_uDelay(settle_dly_us);
        aio_trigger_settled_adc_read(raw45_neg, raw49_neg);

        if (mode_flag & 0x02u) {
            /* Hold static (X = +x_amp, W = w_fixed) active on the board */
            g_dac_row7_code = (row == 6u) ? off_to_dac_u8(+(int32_t)x_amp) : 128u;
            g_dac_row8_code = (row == 7u) ? off_to_dac_u8(+(int32_t)x_amp) : 128u;
            aio_load_dac2(d2_pos);
            maml_refresh_all_columns();
            g_last_refresh_ticks = clint_getTimeLow(BSP_CLINT);
            bsp_uDelay(settle_dly_us);
            aio_trigger_settled_adc_read(g_tel.adc45_sig, g_tel.adc49_sig);
        } else {
            g_dac_row7_code = 128u;
            g_dac_row8_code = 128u;
            aio_load_dac2(d2_mid);
            memcpy(g_w_m3_q14,  saved_m3,  sizeof(saved_m3));
            memcpy(g_w_m8_q14,  saved_m8,  sizeof(saved_m8));
            memcpy(g_w_m33_q14, saved_m33, sizeof(saved_m33));
            maml_refresh_all_columns();
            g_last_refresh_ticks = clint_getTimeLow(BSP_CLINT);
        }
    } else {
        /* --------------------------------------------------------------------
         * Standard Cell Self-Diagnosis Mode (mode_flag = 0):
         *   Hold Input DAC_2[row] = +x_amp and step Weight W = 0, +w_fixed, -w_fixed
         * -------------------------------------------------------------------- */
        uint8_t d2[6] = {128, 128, 128, 128, 128, 128};
        g_dac_row7_code = 128u;
        g_dac_row8_code = 128u;
        if (row < 6u) {
            d2[row] = off_to_dac_u8(+(int32_t)x_amp);
        } else if (row == 6u) {
            g_dac_row7_code = off_to_dac_u8(+(int32_t)x_amp);
        } else if (row == 7u) {
            g_dac_row8_code = off_to_dac_u8(+(int32_t)x_amp);
        }
        aio_load_dac2(d2);
        maml_probe_charge_column(matrix_id, row, col, 0);
        bsp_uDelay(settle_dly_us);

        /* 1. Probe Zero Weight (W+ = 128, W- = 128) */
        aio_trigger_settled_adc_read(raw45_zero, raw49_zero);

        /* 2. Probe Positive Weight (w = +w_fixed) */
        maml_probe_charge_column(matrix_id, row, col, +(int32_t)w_fixed);
        bsp_uDelay(settle_dly_us);
        aio_trigger_settled_adc_read(raw45_pos, raw49_pos);

        /* 3. Probe Negative Weight (w = -w_fixed) */
        maml_probe_charge_column(matrix_id, row, col, -(int32_t)w_fixed);
        bsp_uDelay(settle_dly_us);
        aio_trigger_settled_adc_read(raw45_neg, raw49_neg);

        /* Restore weights after probing */
        g_dac_row7_code = 128u;
        g_dac_row8_code = 128u;
        aio_load_dac2(d2_mid);
        memcpy(g_w_m3_q14,  saved_m3,  sizeof(saved_m3));
        memcpy(g_w_m8_q14,  saved_m8,  sizeof(saved_m8));
        memcpy(g_w_m33_q14, saved_m33, sizeof(saved_m33));
        maml_refresh_all_columns();
        g_last_refresh_ticks = clint_getTimeLow(BSP_CLINT);
    }

    /* Return 100% raw hardware ADC deltas relative to the quiescent baseline */
    for (int c = 0; c < 6; c++) {
        resp.adc45_zero[c] = (int16_t)(raw45_zero[c] - base45[c]);
        resp.adc45_pos[c]  = (int16_t)(raw45_pos[c]  - base45[c]);
        resp.adc45_neg[c]  = (int16_t)(raw45_neg[c]  - base45[c]);

        resp.adc49_zero[c] = (int16_t)(raw49_zero[c] - base49[c]);
        resp.adc49_pos[c]  = (int16_t)(raw49_pos[c]  - base49[c]);
        resp.adc49_neg[c]  = (int16_t)(raw49_neg[c]  - base49[c]);
    }

    memcpy(resp_buf, &resp, sizeof(resp));
    return (uint16_t)sizeof(resp);
}

static void maml_read_cap_ram(uint32_t base_addr, int16_t dst[16][6]) {
    for (int k = 0; k < 16; k++) {
        uint32_t addr = base_addr + (uint32_t)(k * 16);
        uint32_t u01  = AIO_REG(addr + 0x0);
        uint32_t u23  = AIO_REG(addr + 0x4);
        uint32_t u45  = AIO_REG(addr + 0x8);
        dst[k][0] = (int16_t)(u01 & 0xFFFFu);
        dst[k][1] = (int16_t)(u01 >> 16);
        dst[k][2] = (int16_t)(u23 & 0xFFFFu);
        dst[k][3] = (int16_t)(u23 >> 16);
        dst[k][4] = (int16_t)(u45 & 0xFFFFu);
        dst[k][5] = (int16_t)(u45 >> 16);
    }
}

/* ============================================================================
 * 2x6 Contiguous 24.00 us (12 x 2.00 us) Hadamard & Time-Separated Diagnostics
 *   - mode 4 : Seed Weight Pattern A (+W) once across M3/M8/M33 + set DAC_2 = {0,51,102,153,204,255}
 *   - mode 5 : Refresh -> wait 2.0 ms -> 24.00 us Hadamard OFF (Tri-State 0x8000, 12 x 2.00 us samples)
 *   - mode 6 : Refresh -> wait 2.0 ms -> 24.00 us Hadamard ON  (2x6 active table, sck_div=2 = 12.5 MHz)
 *   - mode 7 : Refresh -> wait 2.0 ms -> 24.00 us Hadamard ON  (2x6 active table, sck_div=1 = 25.0 MHz)
 *   - mode 8 : Flip sign of ALL weights (M3, M8, M33: W <- -W) in-place, then run mode 6
 *   - mode 9 : Time-Separated M3 (0x00FF) then M8 (0x7F00) Hadamard ON in one refresh cycle:
 *                Sub-Window 1 (t = 2.000 ms, 24.00 us, mask 0x00FF): M3 active, M8 Tri-State -> cap45 & fwht45
 *                20 us Tri-State gap (0x8000 Hi-Z)
 *                Sub-Window 2 (t = 2.044 ms, 24.00 us, mask 0x7F00): M8 active, M3 Tri-State -> cap49 & fwht49
 *   - mode 10: Time-Separated M3 then M8 Hadamard OFF (Tri-State 0x8000 in both sub-windows)
 * ============================================================================ */
static uint16_t maml_diag_hadamard(uint8_t mode, uint16_t en_mask,
                                   uint8_t *resp_buf, uint16_t resp_max) {
    if (resp_max < sizeof(maml_hadamard_diag_resp_t)) return 0;
    maml_hadamard_diag_resp_t resp;
    memset(&resp, 0, sizeof(resp));
    resp.magic    = MAML_MAGIC;
    resp.msg_type = 0x99;
    resp.mode     = mode;
    resp.en_mask  = en_mask;

    for (int i = 0; i < 16; i++) resp.perm[i] = (uint8_t)i;
    for (int p = 0; p < 7; p++) {
        resp.h_words[2 * p]     = HADAMARD_2X7_POS[p] & 0x7FFFu;
        resp.h_words[2 * p + 1] = (~HADAMARD_2X7_POS[p]) & 0x7FFFu;
    }
    for (int k = 14; k < 16; k++) {
        resp.h_words[k] = 0x8000u;
    }

    if (mode == 4u) {
        maml_seed_fixed_test_weights_once(0x5A3C9E4Du);
    } else if (mode == 8u) {
        maml_flip_all_weights_sign();
    }

    /* Hold DAC_2 fixed at evenly distributed values {0, 51, 102, 153, 204, 255} for modes >= 4 */
    if (mode >= 4u) {
        maml_apply_fixed_even_dac2();
    }

    /* Refresh all 2T1C columns with the current fixed weights (+W or -W) */
    maml_refresh_all_columns();
    g_last_refresh_ticks = clint_getTimeLow(BSP_CLINT);

    /* Wait 2.0 ms (2000 us) after refresh so we sample on the flat/stable plateau */
    if (mode >= 4u) {
        t20_hadamard_tristate_center();
        bsp_uDelay(2000);
    }

    if (mode == 9u || mode == 10u) {
        int off_flag = (mode == 10u) ? 1 : 0;

        /* Sub-Window 1 (t = 2.000..2.024 ms): Perturb Matrix 3 ONLY (0x00FF, M8 in Tri-State Hi-Z) */
        maml_run_2x6_hadamard_burst(0x00FFu, off_flag, 2u);
        maml_read_cap_ram(AIO_CAP_ADC45_BASE, resp.cap45);
        maml_fwht16_demodulate(AIO_CAP_ADC45_BASE, resp.fwht45);

        /* 20 us quiet Tri-State separation between M3 table and M8 table */
        bsp_uDelay(20);

        /* Sub-Window 2 (t = 2.044..2.068 ms): Perturb Matrix 8 ONLY (0x7F00, M3 in Tri-State Hi-Z) */
        maml_run_2x6_hadamard_burst(0x7F00u, off_flag, 2u);
        maml_read_cap_ram(AIO_CAP_ADC49_BASE, resp.cap49);
        maml_fwht16_demodulate(AIO_CAP_ADC49_BASE, resp.fwht49);
    } else {
        int tristate_off = (mode == 5u) ? 1 : 0;
        uint8_t sck_div  = (mode == 7u) ? 1u : 2u;
        maml_run_2x6_hadamard_burst(en_mask, tristate_off, sck_div);
        maml_read_cap_ram(AIO_CAP_ADC45_BASE, resp.cap45);
        maml_read_cap_ram(AIO_CAP_ADC49_BASE, resp.cap49);
        maml_fwht16_demodulate(AIO_CAP_ADC45_BASE, resp.fwht45);
        maml_fwht16_demodulate(AIO_CAP_ADC49_BASE, resp.fwht49);
    }

    resp.settle_cycles = 100u; /* 100 sys_clk cycles = 2.00 us per pulse */
    resp.ack_ok   = T20_REG(T20_H_ACK_OK);
    resp.ack_miss = T20_REG(T20_H_ACK_MISS);
    resp.lat_last = (uint16_t)T20_REG(T20_H_LAT_LAST);
    resp.lat_min  = (uint16_t)T20_REG(0x0A4u);
    resp.lat_max  = (uint16_t)T20_REG(0x0A8u);

    /* Query T20 CH 0x04 OP 0x0 (STATUS) for T20's internal h_word_cnt & h_sync_err */
    uint32_t sw0 = 0, sw1 = 0;
    if (t20_sbus_xact(0x04u, 0x00u, NULL, 0, &sw0, &sw1)) {
        uint32_t sw2 = *(volatile uint32_t *)(T20_BRIDGE_BASE + T20_S_RX_BUF + 8);
        resp.t20_word_cnt = (uint16_t)(((sw1 >> 16) & 0xFF00u) | ((sw1 >> 24) & 0x00FFu));
        resp.t20_sync_err = (uint16_t)(((sw2 << 8)  & 0xFF00u) | ((sw2 >> 8)  & 0x00FFu));
    }

    /* Read quiet 3-state (0x8000 Hi-Z) ADC values */
    aio_trigger_settled_adc_read(resp.adc45_hiz, resp.adc49_hiz);

    AIO_REG(AIO_CTRL) = 0x00000FA9u;

    memcpy(resp_buf, &resp, sizeof(resp));
    return (uint16_t)sizeof(resp);
}

/* ============================================================================
 * UDP Command Dispatcher (Port 5000 Binary MAML Protocol)
 * ============================================================================ */
uint16_t maml_handle_udp_command(const uint8_t *req, uint16_t req_len,
                                 uint8_t *resp_buf, uint16_t resp_max) {
    if (req_len < 5 || resp_max < sizeof(maml_telemetry_pkt_t)) return 0;

    uint32_t magic = ((uint32_t)req[0]) |
                     ((uint32_t)req[1] << 8) |
                     ((uint32_t)req[2] << 16) |
                     ((uint32_t)req[3] << 24);
    if (magic != MAML_MAGIC) return 0;

    uint8_t cmd = req[4];

    switch (cmd) {
        case MAML_CMD_GET_TELEMETRY:
            t20_sync_heater_and_wdog();
            maml_sync_shadow_bytes();
            break;

        case MAML_CMD_SET_CONFIG:
            if (req_len >= 15) {
                uint8_t prev_mode = g_tel.run_mode;
                g_tel.run_mode    = req[5];
                g_tel.jumper_mode       = (req[6] >= 1 && req[6] <= 3) ? req[6] : JUMPER_USE_SIG2;
                g_tel.hadamard_freq_khz = (uint16_t)req[7] | ((uint16_t)req[8] << 8);
                if (g_tel.hadamard_freq_khz < 50)  g_tel.hadamard_freq_khz = 50;
                if (g_tel.hadamard_freq_khz > 500) g_tel.hadamard_freq_khz = 500;
                uint16_t settle_cyc = (uint16_t)((50000u + (g_tel.hadamard_freq_khz >> 1)) / g_tel.hadamard_freq_khz);
                g_tel.settle_cycles = settle_cyc;
                AIO_REG(AIO_SETTLE_CYCLES) = ((uint32_t)25u << 16) | settle_cyc;
                g_tel.max_meas_duty_pct = (req[9] >= 1 && req[9] <= 100) ? req[9] : 25;
                g_tel.inner_loop_n      = (uint16_t)req[10] | ((uint16_t)req[11] << 8);
                if (g_tel.inner_loop_n < 1)   g_tel.inner_loop_n = 1;
                if (g_tel.inner_loop_n > 500) g_tel.inner_loop_n = 500;
                g_tel.num_strata_m      = (req[12] >= 1 && req[12] <= 16) ? req[12] : NUM_STRATA_DEFAULT;
                g_tel.trim_dac_38       = (int8_t)req[13];
                g_hid_amp_dac           = req[14];

                /* Optional byte 15-16: Programmable Hadamard timing delay in microseconds (0..9500 us) */
                if (req_len >= 17) {
                    uint16_t had_dly = (uint16_t)req[15] | ((uint16_t)req[16] << 8);
                    g_hadamard_delay_us = (had_dly <= 9500u) ? had_dly : 9500u;
                }

                if (g_tel.run_mode != MAML_MODE_IDLE) {
                    if (g_comp_is_centered != 0u || prev_mode == MAML_MODE_IDLE) {
                        /* Enable Layer 1 diagonal pass-through on M3 so ACT(4)_D_ROW[0..5] drives M8
                         * with strong intermediate carrier signals while M8 starts near zero! */
                        for (int c = 0; c < 6; c++) {
                            if (g_w_m3_q14[c][c] == 0) {
                                g_w_m3_q14[c][c]  = (int16_t)(80 << 7);
                                g_w0_m3_q14[c][c] = (int16_t)(80 << 7);
                            }
                        }
                        for (int r = 0; r < 7; r++) {
                            for (int c = 0; c < 6; c++) {
                                if (g_w_m8_q14[r][c] == 0) {
                                    int16_t eps = ((r + c) & 1) ? (int16_t)(2 << 7) : (int16_t)-(2 << 7);
                                    g_w_m8_q14[r][c]  = eps;
                                    g_w0_m8_q14[r][c] = eps;
                                }
                            }
                        }
                        g_tel.outer_loop_epoch = 0;
                        g_tel.cur_inner_step   = 0;
                    }
                    g_comp_is_centered = 0;
                }

                maml_refresh_all_columns();
                bsp_uDelay((g_hadamard_delay_us > 0 && g_hadamard_delay_us <= 9500u) ? g_hadamard_delay_us : 5000u);
                aio_trigger_settled_adc_read(g_tel.adc45_sig, g_tel.adc49_sig);
            }
            break;

        case MAML_CMD_SET_HEATER:
            if (req_len >= 10) {
                g_tel.heater_armed   = req[5] ? 1u : 0u;
                g_tel.heater_duty[0] = req[6];
                g_tel.heater_duty[1] = req[7];
                g_tel.heater_duty[2] = req[8];
                g_tel.heater_duty[3] = req[9];
                t20_sync_heater_and_wdog();
            }
            break;

        case MAML_CMD_SET_LEDS:
            if (req_len >= 7) {
                g_tel.comp_led_on  = req[5] ? 1u : 0u;
                g_tel.mat33_led_on = req[6] ? 1u : 0u;
                t20_sync_leds();
            }
            break;

        case MAML_CMD_SET_DAC_DIAG:
            if (req_len >= 10) {
                g_tel.osc_10hz_en = req[5] ? 1u : 0u;
                g_tel.ovr_en      = req[6] ? 1u : 0u;
                uint8_t raw_bank  = req[7];
                g_tel.ovr_bank    = raw_bank & 0x03u;
                g_tel.ovr_ch      = req[8] & 0x07u;
                g_tel.ovr_val     = req[9];

                uint32_t ctrl = 0x00000FA9u; /* base: sclr_n=1, auto_h_adc=1, pi_inv=1, w[11:0], sck_div=15 (280ns SCK/RCK HIGH) */
                if (req_len >= 11 && req[10]) ctrl |= (1u << 4); /* optional r_adc_conv_mode */

                if (g_tel.osc_10hz_en) {
                    /* Drive 255 -> 128 -> 0 from C with bitrev8() so 128 = 0x01 on QA (MSB)! */
                    AIO_REG(AIO_CTRL) = ctrl;
                    g_osc_phase = 0;
                    aio_load_all_30_dacs(255u);
                } else if (g_tel.ovr_en && raw_bank == 0xFFu) {
                    /* Broadcast static override value to ALL 30 DAC channels simultaneously */
                    AIO_REG(AIO_CTRL) = ctrl;
                    aio_load_all_30_dacs(g_tel.ovr_val);
                } else if (g_tel.ovr_en) {
                    /* Load all 30 base DACs to 128 except the overridden (bank, ch) */
                    uint8_t d2[6]  = {128, 128, 128, 128, 128, 128};
                    uint8_t w15[8] = {128, 128, 128, 128, 128, 128, 128, 128};
                    uint8_t w12[8] = {128, 128, 128, 128, 128, 128, 128, 128};
                    uint8_t w34[8] = {128, 128, 128, 128, 128, 128, 128, 128};
                    if (g_tel.ovr_bank == 0 && g_tel.ovr_ch < 6) d2[g_tel.ovr_ch]  = g_tel.ovr_val;
                    if (g_tel.ovr_bank == 1 && g_tel.ovr_ch < 8) w15[g_tel.ovr_ch] = g_tel.ovr_val;
                    if (g_tel.ovr_bank == 2 && g_tel.ovr_ch < 8) w12[g_tel.ovr_ch] = g_tel.ovr_val;
                    if (g_tel.ovr_bank == 3 && g_tel.ovr_ch < 8) w34[g_tel.ovr_ch] = g_tel.ovr_val;
                    AIO_REG(AIO_CTRL) = ctrl;
                    aio_load_dac2(d2);
                    aio_load_weight_banks(w15, w12, w34);
                } else {
                    AIO_REG(AIO_CTRL) = ctrl;
                    aio_load_all_30_dacs(128u);
                }

                bsp_uDelay(5);
                if (g_tel.ovr_en && (raw_bank == 0xFFu || (g_tel.ovr_bank >= 1 && g_tel.ovr_bank <= 3))) {
                    /* Pulse all 6 positive G_P gates (0x3F) so the overridden weight DAC reaches all 6 columns */
                    uint8_t p_mask = (raw_bank == 0xFFu) ? T20_GATE_ALL_P :
                                     ((g_tel.ovr_bank == 1) ? T20_GATE_M3_P :
                                      ((g_tel.ovr_bank == 2) ? T20_GATE_M8_P : T20_GATE_M33_P));
                    maml_pulse_t20_col_gates(0x3Fu, p_mask, 40u);
                    bsp_uDelay(30);
                }
                aio_trigger_settled_adc_read(g_tel.adc45_sig, g_tel.adc49_sig);
            }
            break;

        case MAML_CMD_CENTER_WEIGHTS:
            maml_center_compensation_weights();
            aio_trigger_settled_adc_read(g_tel.adc45_sig, g_tel.adc49_sig);
            break;

        case MAML_CMD_SEED_WEIGHTS:
            if (req_len >= 7) {
                maml_seed_weights(req[5], req[6]);
                maml_refresh_all_columns();
                aio_trigger_settled_adc_read(g_tel.adc45_sig, g_tel.adc49_sig);
            }
            break;

        case MAML_CMD_PROBE_CELL:
            if (req_len >= 13) {
                int8_t   x_amp     = (int8_t)req[8];
                int8_t   w_fixed   = (int8_t)req[9];
                uint8_t  mode_flag = req[10];
                uint16_t snap_dly  = (uint16_t)req[11] | ((uint16_t)req[12] << 8);
                return maml_probe_single_cell(req[5], req[6], req[7], x_amp, w_fixed, mode_flag, snap_dly, resp_buf, resp_max);
            } else if (req_len >= 10) {
                int8_t  x_amp     = (int8_t)req[8];
                int8_t  w_fixed   = (int8_t)req[9];
                uint8_t mode_flag = (req_len >= 11) ? req[10] : 0x01u;
                return maml_probe_single_cell(req[5], req[6], req[7], x_amp, w_fixed, mode_flag, 0, resp_buf, resp_max);
            } else if (req_len >= 8) {
                return maml_probe_single_cell(req[5], req[6], req[7], 96, 96, 0x00u, 0, resp_buf, resp_max);
            }
            break;

        case MAML_CMD_RAND_DATA:
            if (req_len >= 6 && req[5] == 2u) {
                /* Single fresh locked white-noise vector draw while strictly preserving current M3 and M8 weights! */
                g_auto_random_data = 0u;
                maml_generate_new_white_noise_ref();
            } else {
                if (req_len >= 6) {
                    g_auto_random_data = req[5] ? 1u : 0u;
                } else {
                    g_auto_random_data = g_auto_random_data ? 0u : 1u; /* toggle */
                }
                if (g_auto_random_data) {
                    maml_generate_new_white_noise_ref();
                } else {
                    /* Center In-Data rows back to 128 (0.0 V differential) */
                    uint8_t d2_mid[6] = {128, 128, 128, 128, 128, 128};
                    g_dac_row7_code = 128u;
                    g_dac_row8_code = 128u;
                    aio_load_dac2(d2_mid);
                }
            }
            aio_trigger_settled_adc_read(g_tel.adc45_sig, g_tel.adc49_sig);
            break;

        case MAML_CMD_STEP_ONCE:
            {
                /* Synchronize to the exact 10.0 ms (100 Hz) capacitor refresh boundary */
                uint32_t period_ticks = g_refresh_period_us * 50u;
                while ((uint32_t)(clint_getTimeLow(BSP_CLINT) - g_last_refresh_ticks) < period_ticks) {
                    /* wait for 10.0 ms boundary */
                }
                g_last_refresh_ticks = clint_getTimeLow(BSP_CLINT);

                uint8_t saved_mode = g_tel.run_mode;
                g_tel.run_mode     = MAML_MODE_BASE_TRAIN;
                g_comp_is_centered = 0u;
                if (g_hid_amp_dac == 0u) {
                    /* Pure Inner Loop step at exact 100 Hz cadence */
                    maml_execute_step();
                } else {
                    /* 2-step Inner + Outer-Loop (Ref 41 + Ref 40) gather epoch */
                    uint16_t saved_n = g_tel.inner_loop_n;
                    uint8_t  saved_m = g_tel.num_strata_m;
                    g_tel.inner_loop_n   = 2;
                    g_tel.num_strata_m   = 1;
                    g_tel.cur_inner_step = 0;
                    maml_execute_step();
                    while ((uint32_t)(clint_getTimeLow(BSP_CLINT) - g_last_refresh_ticks) < period_ticks);
                    g_last_refresh_ticks = clint_getTimeLow(BSP_CLINT);
                    maml_execute_step();
                    g_tel.num_strata_m = saved_m;
                    g_tel.inner_loop_n = saved_n;
                }
                g_tel.run_mode = saved_mode;
                maml_sync_shadow_bytes();
            }
            break;

        case MAML_CMD_DIAG_HADAMARD:
            if (req_len >= 8) {
                uint8_t  mode    = req[5];
                uint16_t en_mask = (uint16_t)req[6] | ((uint16_t)req[7] << 8);
                return maml_diag_hadamard(mode, en_mask, resp_buf, resp_max);
            }
            break;

        default:
            break;
    }

    memcpy(resp_buf, &g_tel, sizeof(g_tel));
    return (uint16_t)sizeof(g_tel);
}

