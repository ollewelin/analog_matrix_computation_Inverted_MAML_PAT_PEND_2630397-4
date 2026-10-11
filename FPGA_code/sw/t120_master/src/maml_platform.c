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
static uint32_t g_last_refresh_ticks = 0u;
static uint8_t  g_focus_col          = 0u;

static void maml_refresh_all_columns(void) {
    maml_sync_shadow_bytes();

    /* Step 1: Ensure Hadamard outputs are 3-Stated (Hi-Z, OE=0) before recharging 2T1C gates */
    t20_hadamard_tristate_center();

    int use_hid = (g_tel.run_mode == MAML_MODE_BASE_TRAIN);
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
            if (g_tel.jumper_mode == JUMPER_OFF_NO_COMP) w = 0;
            w15[r] = off_to_dac_u8(-w);
        }
        for (int r = 0; r < 7; r++) {
            int32_t w = g_tel.w_m8[r][col] + (use_hid ? g_hid_w_m8[g_cur_basin_idx][r][col] : 0);
            if (g_tel.jumper_mode == JUMPER_OFF_NO_COMP) w = 0;
            w12[r] = off_to_dac_u8(-w);
        }
        w12[7] = 128;
        for (int r = 0; r < 6; r++) {
            w34[r] = off_to_dac_u8(-g_tel.w_m33[r][col]);
        }
        w34[6] = trim_code;
        w34[7] = trim_code;

        aio_load_weight_banks(w15, w12, w34);
        bsp_uDelay(5); /* Let MCP6024T DAC buffers settle before opening G_N switch */

        maml_pulse_t20_col_gates(col_bit, T20_GATE_ALL_N, pulse_clk9);
        /* Wait full half_settle_us + 5 us guard so G_N switch closes BEFORE W DACs change */
        bsp_uDelay(half_settle_us + 5u);

        /* --- B. Positive Half-Cells (G_P[col+1]_MAT_*) : W+ = 128 + w_eff --- */
        for (int r = 0; r < 8; r++) {
            int32_t w = g_tel.w_m3[r][col] + (use_hid ? g_hid_w_m3[g_cur_basin_idx][r][col] : 0);
            if (g_tel.jumper_mode == JUMPER_OFF_NO_COMP) w = 0;
            w15[r] = off_to_dac_u8(+w);
        }
        for (int r = 0; r < 7; r++) {
            int32_t w = g_tel.w_m8[r][col] + (use_hid ? g_hid_w_m8[g_cur_basin_idx][r][col] : 0);
            if (g_tel.jumper_mode == JUMPER_OFF_NO_COMP) w = 0;
            w12[r] = off_to_dac_u8(+w);
        }
        w12[7] = 128;
        for (int r = 0; r < 6; r++) {
            w34[r] = off_to_dac_u8(+g_tel.w_m33[r][col]);
        }
        w34[6] = trim_code;
        w34[7] = trim_code; /* Ref 38 trim-DAC */

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
static void maml_generate_new_white_noise_ref(void) {
    uint8_t d2_codes[6];
    for (int i = 0; i < 6; i++) {
        /* Uncorrelated uniform white noise in [-100, +100] */
        int32_t rnd = (int32_t)(prng_next() % 201u) - 100;
        g_tel.x_ref[i] = (int16_t)rnd;
        d2_codes[i]    = off_to_dac_u8(rnd);
    }
    aio_load_dac2(d2_codes);

    /* Compute ideal digital target output Z_target = M33_ideal * x_ref (scaled to physical 12-bit ADC_49 LSBs) */
    for (int j = 0; j < 6; j++) {
        int32_t acc = 0;
        for (int i = 0; i < 6; i++) {
            acc += (int32_t)g_tel.w_m33[i][j] * (int32_t)g_tel.x_ref[i];
        }
        g_tel.z_target[j] = (int16_t)rshift_rne(acc, 8);
    }
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
 * Inner Randomization (16-step Hadamard permutation + hardware pi_inv LUT)
 * & 4-Phase Settle-Then-Sample Execution + 3-State Exit (step 16 = 0x8000)
 * ============================================================================ */
static void maml_run_permuted_hadamard_sweep(uint16_t en_mask) {
    uint8_t perm[16];
    for (int i = 0; i < 16; i++) perm[i] = (uint8_t)i;
    for (int i = 15; i > 0; i--) {
        uint32_t j = prng_next() % (uint32_t)(i + 1);
        uint8_t tmp = perm[i];
        perm[i] = perm[j];
        perm[j] = tmp;
    }

    /* Configure T20 active matrix mask (0x7F00 for M8 only, 0x00FF for M3 only) */
    t20_set_hadamard_mask(en_mask);

    /* Ensure Hadamard lines start in 3-State Hi-Z (0x8000) and equilibrate C_PTU (2.2nF) */
    t20_hadamard_tristate_center();
    bsp_uDelay(80);

    /* Configure Quiet Analog DC Settling Cycles based on Hadamard frequency (50..500 kHz) */
    uint32_t f_khz = g_tel.hadamard_freq_khz;
    if (f_khz < 50)  f_khz = 50;
    if (f_khz > 500) f_khz = 500;
    uint16_t settle_cyc = (uint16_t)((50000u + (f_khz >> 1)) / f_khz); /* 100 cyc (2.0 us) @ 500 kHz */
    g_tel.settle_cycles = settle_cyc;
    AIO_REG(AIO_SETTLE_CYCLES) = ((uint32_t)25u << 16) | settle_cyc;

    /* Use sck_div=15 (280ns SCK HIGH) + r_adc_bit_align=2 (w[11:0] 12-bit) + hardware pi_inv */
    AIO_REG(AIO_CTRL) = 0x00000FA9u;
    T20_REG(T20_H_CTRL) = (1u << 2) | (1u << 9);

    /* Return-to-Hi-Z (RTZ) permuted sweep:
     * Each step s launches from 0x8000 (1.65V Hi-Z equilibrium) -> HADAMARD_16[perm[s]],
     * settles for settle_cyc, samples ADC_45 & ADC_49 into cap_ram[perm[s]], and
     * immediately returns to 0x8000 (Hi-Z) so C_PTU=2.2nF has zero memory of perm[s-1]! */
    for (int s = 0; s < 16; s++) {
        uint16_t h_word = HADAMARD_16[perm[s]] & 0x7FFFu; /* bit 15 = 0 (OE = 1) */
        AIO_REG(AIO_PI_INV_LO) = (uint32_t)(perm[s] & 0x0Fu);
        AIO_REG(AIO_PI_INV_HI) = 0u;
        *(volatile uint32_t *)(T20_BRIDGE_BASE + T20_H_TABLE + 0) = (uint32_t)h_word;
        *(volatile uint32_t *)(T20_BRIDGE_BASE + T20_H_TABLE + 4) = 0x00008000u; /* Leave Table Hi-Z */

        T20_REG(T20_H_COUNT)  = 2;
        T20_REG(T20_H_PERIOD) = 24;
        T20_REG(T20_H_CTRL)   = (1u << 0) | (1u << 9);

        uint32_t timeout = 10000;
        while ((((T20_REG(T20_H_STATUS) & 2u) == 0u) ||
                (T20_REG(T20_H_STATUS) & 1u) ||
                (AIO_REG(AIO_STATUS) & 0x06u)) && --timeout) {
            bsp_uDelay(1);
        }
        /* Allow C_PTU=2.2nF AC-coupling capacitor to relax back to 1.65V Hi-Z baseline */
        bsp_uDelay(40);
    }

    g_tel.t20_h_ack_ok   = T20_REG(T20_H_ACK_OK);
    g_tel.t20_h_ack_miss = T20_REG(T20_H_ACK_MISS);
    g_tel.t20_h_lat_last = (uint16_t)T20_REG(T20_H_LAT_LAST);
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
    AIO_REG(AIO_CMD) = (1u << 4); /* Manual settled ADC_45 & ADC_49 conversion */
    uint32_t timeout = 10000;
    while ((AIO_REG(AIO_STATUS) & 0x06u) && --timeout);
    bsp_uDelay(4);
    maml_read_latest_adcs(adc45_out, adc49_out);
}

/* ============================================================================
 * 16-Point Radix-2 Fast Walsh-Hadamard Transform (FWHT-16)
 *   Operates on the hardware-unpermuted Capture RAM (CAP_ADC45 or CAP_ADC49)
 *   using 32-bit guard accumulators and convergent round-to-nearest-even (§2).
 *   Note:
 *     - k = 0 (DC average across 16 steps) is normalized by 1/16 (>> 4).
 *     - k = 1..15 retain the full 16-step coherent sum (Q12.4, 1/16 LSB units)
 *       so sub-LSB Hadamard perturbations are preserved with +12 dB gain!
 * ============================================================================ */
static void maml_fwht16_demodulate(uint32_t cap_base_off, int16_t sens_out[16][6]) {
    int32_t buf[16][6];

    for (int k = 0; k < 16; k++) {
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

    /* 4-Stage Butterfly (N = 16): u + v, u - v */
    for (int len = 1; len < 16; len <<= 1) {
        int step = len << 1;
        for (int i = 0; i < 16; i += step) {
            for (int j = 0; j < len; j++) {
                for (int c = 0; c < 6; c++) {
                    int32_t u = buf[i + j][c];
                    int32_t v = buf[i + j + len][c];
                    buf[i + j][c]       = u + v;
                    buf[i + j + len][c] = u - v;
                }
            }
        }
    }

    for (int c = 0; c < 6; c++) {
        sens_out[0][c] = sat_q14(rshift_rne(buf[0][c], 4));
    }
    for (int k = 1; k < 16; k++) {
        for (int c = 0; c < 6; c++) {
            sens_out[k][c] = sat_q14(buf[k][c]);
        }
    }
}

/* ============================================================================
 * Pure Hardware Analog Readout & Non-Backprop Hadamard Gradient Engine
 *   Implements Equations 1–7 from NON_BACKPROP_HADAMARD_GRADIENT_RULES.md
 *   strictly from raw physical ADC_45 / ADC_49 and FWHT-16 measurements:
 *     - Eq. 1: Er_j^(49) = Z_target,j - Z_out,j^(49)
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

    /* 1. Sub-Window A: Perturb Matrix 8 Only (M3 3-stated Hi-Z via mask 0x7F00) */
    maml_run_permuted_hadamard_sweep(0x7F00u);
    maml_fwht16_demodulate(AIO_CAP_ADC49_BASE, sens_m8_raw);

    /* 2. Sub-Window B: Perturb Matrix 3 Only (M8 3-stated Hi-Z via mask 0x00FF) */
    maml_run_permuted_hadamard_sweep(0x00FFu);
    maml_fwht16_demodulate(AIO_CAP_ADC45_BASE, sens_m3_raw);

    /* 3. Read quiet 3-state (0x8000 Hi-Z) forward-pass output on ADC_45 & ADC_49 */
    aio_trigger_settled_adc_read(g_tel.adc45_sig, g_tel.adc49_sig);

    int16_t sens_m8[7][6];
    int16_t sens_m3[8][6];
    int16_t eval_adc45[6];
    int16_t eval_adc49[6];

    /* Pure physical hardware readings relative to calibrated zero-drive baseline */
    for (int c = 0; c < 6; c++) {
        eval_adc45[c] = (int16_t)((int32_t)g_tel.adc45_sig[c] - (int32_t)g_adc45_zero_cal[c]);
        eval_adc49[c] = (int16_t)((int32_t)g_tel.adc49_sig[c] - (int32_t)g_adc49_zero_cal[c]);
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
            grad_m8_out[i][j] = sat_q14(rshift_rne(prod, 6));
        }
    }

    /* ========================================================================
     * Equation 5: Carrier Wave Search (Find strongest intermediate row k)
     *   k = argmax_{i in 0..5} |x_i^(8)|
     * ======================================================================== */
    uint8_t best_k = 0;
    int32_t max_abs_x8 = -1;
    for (uint8_t i = 0; i < 6; i++) {
        int32_t ax = eval_adc45[i];
        if (ax < 0) ax = -ax;
        if (ax > max_abs_x8) {
            max_abs_x8 = ax;
            best_k     = i;
        }
    }
    g_tel.carrier_row_k = best_k;

    /* ========================================================================
     * Equation 6: Regularized Inverse Scaling to isolate column slope sigma_2'(y_j^(8))
     *   sigma_2'(y_j^(8)) approx (x_k^(8) / ((x_k^(8))^2 + alpha)) * <dz_j^(49)/dW_{k,j}^(8)>_H
     * ======================================================================== */
    int32_t xk = eval_adc45[best_k];
    int32_t denom = (xk * xk) + 64; /* Tikhonov regularizer alpha = 64 LSB^2 */
    for (int j = 0; j < 6; j++) {
        if (g_tel.jumper_mode == JUMPER_OFF_NO_COMP) {
            g_tel.sigma2_slope[j] = 0;
        } else if (g_tel.jumper_mode == JUMPER_BYPASS_SIG2) {
            g_tel.sigma2_slope[j] = 16384; /* 1.0 in Q1.14 */
        } else {
            int32_t num = (xk * (int32_t)sens_m8[best_k][j]) << 10;
            g_tel.sigma2_slope[j] = sat_q14(num / denom);
        }
    }

    /* ========================================================================
     * Equation 4: Row Sensitivity Receipt dx_i^(8) back to Layer 1
     *   dx_i^(8) = sum_{j=0..5} W_{i,j}^(8)digital * sigma_2'(y_j^(8)) * Er_j^(49)
     * ======================================================================== */
    int32_t dx8[6];
    for (int i = 0; i < 6; i++) {
        int32_t sum = 0;
        for (int j = 0; j < 6; j++) {
            int32_t col_term = rshift_rne((int32_t)g_tel.sigma2_slope[j] * (-err49[j]), 10);
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
            grad_m3_out[i][j] = sat_q14(rshift_rne(prod, 6));
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
static void maml_center_compensation_weights(void) {
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
    g_comp_is_centered = 1;
    maml_refresh_all_columns();

    /* Measure uncompensated bit precision at centered weights */
    uint8_t saved_jm = g_tel.jumper_mode;
    g_tel.jumper_mode = JUMPER_OFF_NO_COMP;
    int16_t gm3[8][6], gm8[7][6];
    maml_measure_and_extract_gradients(0, gm3, gm8);
    g_tel.jumper_mode = saved_jm;
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

    g_tel.outer_loop_epoch = 0;
    g_tel.cur_inner_step   = 0;
    maml_refresh_all_columns();

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

/* Calibrate quiescent DC zero baseline with all 30 DACs at 128 and Hadamard Hi-Z */
static void maml_calibrate_zero_baseline(void) {
    t20_hadamard_tristate_center();
    aio_load_all_30_dacs(128u);
    bsp_uDelay(10);
    maml_pulse_t20_col_gates(0x3Fu, T20_GATE_ALL_P | T20_GATE_ALL_N, 40u);
    bsp_uDelay(40);

    int32_t acc45[6] = {0, 0, 0, 0, 0, 0};
    int32_t acc49[6] = {0, 0, 0, 0, 0, 0};
    for (int i = 0; i < 4; i++) {
        int16_t a45[6], a49[6];
        aio_trigger_settled_adc_read(a45, a49);
        for (int c = 0; c < 6; c++) {
            acc45[c] += a45[c];
            acc49[c] += a49[c];
        }
    }
    for (int c = 0; c < 6; c++) {
        g_adc45_zero_cal[c] = (int16_t)(acc45[c] >> 2);
        g_adc49_zero_cal[c] = (int16_t)(acc49[c] >> 2);
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
    g_tel.bit_prec_uncomp_centi = 422; /* 4.22 bits default uncompensated baseline */
    g_tel.bit_prec_comp_centi   = 773; /* 7.73 bits default compensated baseline */

    /* Initialize Primary Payload Matrix M33 with a deterministic orthogonal-like target matrix */
    const int8_t default_m33[6][6] = {
        { +64, -32, +16, -16, +32, -48 },
        { -32, +72, -24, +32, -16, +24 },
        { +24, -16, +68, -28, +20, -16 },
        { -16, +28, -20, +60, -24, +32 },
        { +32, -24, +16, -24, +64, -20 },
        { -40, +20, -16, +28, -20, +70 }
    };
    for (int r = 0; r < 6; r++)
        for (int c = 0; c < 6; c++)
            g_w_m33_q14[r][c] = (int16_t)((int32_t)default_m33[r][c] << 7);

    for (uint8_t k = 0; k < NUM_BASINS; k++) {
        maml_sample_hidden_offset(k);
    }

    /* Configure T120 Analog IO Controller:
     * sclr_n=1, auto_h_adc=1, pi_inv=1, r_adc_bit_align=2 (w[11:0] 12-bit), sck_div=15 (280ns SCK/RCK HIGH) */
    AIO_REG(AIO_CTRL)          = 0x00000FA9u;
    AIO_REG(AIO_SETTLE_CYCLES) = (25u << 16) | 100u;

    maml_calibrate_zero_baseline();
    maml_shuffle_outer_slots();
    maml_generate_new_white_noise_ref();
    maml_center_compensation_weights();
    maml_seed_weights(SEED_MODE_AUTO_GAIN, 28);
    g_last_refresh_ticks = clint_getTimeLow(BSP_CLINT);
    t20_sync_heater_and_wdog();
    t20_sync_leds();
}

/* ============================================================================
 * Execute One Full MAML Training / Compensation Step
 *   - Enforces white-noise reference lock across all M=10 strata
 *   - Enforces Equations 1-7 (no digital multiplication by x_i)
 *   - Enforces Inner Loop (Ref 41) & Dot-Product Second-Derivative Outer Loop (Ref 40)
 * ============================================================================ */
static void maml_execute_step(void) {
    int16_t gm3[8][6], gm8[7][6];

    if (g_tel.run_mode == MAML_MODE_BASE_TRAIN) {
        /* --------------------------------------------------------------------
         * Base Model Training Mode (Ref 40 Outer Loop + Ref 41 Inner Loop)
         * Duty cycle is 100% back-to-back across all M strata per refresh cycle!
         * -------------------------------------------------------------------- */
        if (g_tel.cur_inner_step == 0 && g_cur_basin_idx < NUM_BASINS) {
            /* Start of Inner Loop (Ref 41) for Basin k: reset W <- W_0 and sample hidden offset */
            memcpy(g_w_m3_q14, g_w0_m3_q14, sizeof(g_w_m3_q14));
            memcpy(g_w_m8_q14, g_w0_m8_q14, sizeof(g_w_m8_q14));
            maml_sample_hidden_offset(g_cur_basin_idx);
        }

        /* Lock a constant white-noise reference vector across the ENTIRE refresh cycle! */
        maml_generate_new_white_noise_ref();
        maml_shuffle_outer_slots();
        maml_refresh_all_columns();

        memset(g_acc_grad_m3, 0, sizeof(g_acc_grad_m3));
        memset(g_acc_grad_m8, 0, sizeof(g_acc_grad_m8));

        uint8_t m = g_tel.num_strata_m;
        for (uint8_t s = 0; s < m; s++) {
            uint8_t slot = g_slot_perm[s];
            g_tel.cur_stratum_slot = slot;
            maml_measure_and_extract_gradients(slot, gm3, gm8);
            for (int r = 0; r < 8; r++)
                for (int c = 0; c < 6; c++)
                    g_acc_grad_m3[r][c] += gm3[r][c];
            for (int r = 0; r < 7; r++)
                for (int c = 0; c < 6; c++)
                    g_acc_grad_m8[r][c] += gm8[r][c];
        }

        /* Average gradient across the M strata and update Inner Loop weights (Ref 41) */
        for (int r = 0; r < 8; r++) {
            for (int c = 0; c < 6; c++) {
                int16_t g_avg = sat_q14(g_acc_grad_m3[r][c] / (int32_t)m);
                if (g_tel.cur_inner_step == 0) g_grad_init_m3[r][c] = g_avg;
                g_grad_final_m3[r][c] = g_avg;
                int32_t step_w = rshift_rne((int32_t)g_avg * (int32_t)g_lr_inner_q16, 12);
                g_w_m3_q14[r][c] = sat_q14((int32_t)g_w_m3_q14[r][c] - step_w);
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
                g_w_m8_q14[r][c] = sat_q14((int32_t)g_w_m8_q14[r][c] - step_w);
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

        g_tel.cur_inner_step += 5;
        if (g_tel.cur_inner_step >= g_tel.inner_loop_n) {
            /* ----------------------------------------------------------------
             * Outer Loop (Ref 40): Memory-Safe Dot-Product Second Derivative!
             *   Never forms the P x P Hessian; uses scalar dot product
             *   g_init . g_final to push inner-loop valleys ("groparna")
             *   together toward the Base Model center W_0!
             * ---------------------------------------------------------------- */
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

            maml_update_3d_landscape_coords();

            g_tel.cur_inner_step = 0;
            g_cur_basin_idx = (g_cur_basin_idx + 1u) % NUM_BASINS;
            g_tel.outer_loop_epoch++;
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

        /* Wait proportional to slot index & Hadamard frequency scaling */
        uint32_t slot_delay_us = (uint32_t)slot * (uint32_t)g_tel.settle_cycles;
        if (slot_delay_us > 0 && slot_delay_us < 5000) {
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
        if (g_tel.run_mode != MAML_MODE_IDLE) {
            maml_execute_step();
        } else {
            maml_refresh_all_columns();
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
        if (matrix_id == 0u && row < 8u) g_w_m3_q14[row][col]  = w_q14;
        if (matrix_id == 1u && row < 7u) g_w_m8_q14[row][col]  = w_q14;
        if (matrix_id == 2u && row < 6u) g_w_m33_q14[row][col] = w_q14;
    }

    /* Refresh all 6 columns across all 3 matrices twice back-to-back (2 * 50 us = 100 us = 10*tau_charge)
     * so the 100 nF capacitor on (matrix_id, row, col) settles to >99.995% and all other cells hold 1.65V */
    maml_refresh_all_columns();
    maml_refresh_all_columns();
    g_last_refresh_ticks = clint_getTimeLow(BSP_CLINT);
}

static uint16_t maml_probe_single_cell(uint8_t matrix_id, uint8_t row, uint8_t col,
                                       int8_t x_amp, int8_t w_fixed, uint8_t mode_flag,
                                       uint8_t *resp_buf, uint16_t resp_max) {
    if (resp_max < sizeof(maml_cell_probe_resp_t)) return 0;
    maml_cell_probe_resp_t resp;
    memset(&resp, 0, sizeof(resp));
    resp.magic     = MAML_MAGIC;
    resp.msg_type  = 0x97;
    resp.matrix_id = matrix_id;
    resp.row       = row;
    resp.col       = col;

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

    /* Measure quiescent column baseline at d2 = 128 (X = 0), w = 0 right after refresh */
    uint8_t d2_mid[6] = {128, 128, 128, 128, 128, 128};
    aio_load_dac2(d2_mid);
    maml_probe_charge_column(matrix_id, row, col, 0);
    bsp_uDelay(10);
    int16_t base45[6], base49[6];
    aio_trigger_settled_adc_read(base45, base49);

    int16_t raw45_zero[6], raw49_zero[6];
    int16_t raw45_pos[6],  raw49_pos[6];
    int16_t raw45_neg[6],  raw49_neg[6];

    if (mode_flag & 0x01u) {
        /* --------------------------------------------------------------------
         * Fixed-Weight Input-Up/Down Multiplier Mode (mode_flag bit 0 = 1):
         *   Each measurement (X = 0, X = +x_amp, X = -x_amp) is preceded by a
         *   fresh synchronous column refresh so all three ADC reads occur at
         *   the EXACT same relative time (10 us) after the refresh window!
         * -------------------------------------------------------------------- */
        /* 1. X = 0 (all DAC_2 = 128) at fixed weight W = w_fixed */
        aio_load_dac2(d2_mid);
        maml_probe_charge_column(matrix_id, row, col, (int32_t)w_fixed);
        bsp_uDelay(10);
        aio_trigger_settled_adc_read(raw45_zero, raw49_zero);

        /* 2. X = +x_amp on probed row (move input UP) at fixed weight W = w_fixed */
        uint8_t d2_pos[6] = {128, 128, 128, 128, 128, 128};
        if (row < 6) {
            d2_pos[row] = off_to_dac_u8(+(int32_t)x_amp);
        } else {
            for (int i = 0; i < 6; i++) d2_pos[i] = off_to_dac_u8(+(int32_t)x_amp);
        }
        aio_load_dac2(d2_pos);
        maml_refresh_all_columns();
        bsp_uDelay(10);
        aio_trigger_settled_adc_read(raw45_pos, raw49_pos);

        /* 3. X = -x_amp on probed row (move input DOWN) at fixed weight W = w_fixed */
        uint8_t d2_neg[6] = {128, 128, 128, 128, 128, 128};
        if (row < 6) {
            d2_neg[row] = off_to_dac_u8(-(int32_t)x_amp);
        } else {
            for (int i = 0; i < 6; i++) d2_neg[i] = off_to_dac_u8(-(int32_t)x_amp);
        }
        aio_load_dac2(d2_neg);
        maml_refresh_all_columns();
        bsp_uDelay(10);
        aio_trigger_settled_adc_read(raw45_neg, raw49_neg);

        if (mode_flag & 0x02u) {
            /* Hold static (X = +x_amp, W = w_fixed) active on the board:
             * Leave g_w_m*_q14[row][col] = w_fixed so the 10.0 ms autonomous
             * refresh engine continuously refreshes (matrix_id, row, col) with
             * W = w_fixed and all other cells with W = 0! */
            aio_load_dac2(d2_pos);
            maml_refresh_all_columns();
            g_last_refresh_ticks = clint_getTimeLow(BSP_CLINT);
            bsp_uDelay(10);
            aio_trigger_settled_adc_read(g_tel.adc45_sig, g_tel.adc49_sig);
        } else {
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
        if (row < 6) {
            d2[row] = off_to_dac_u8(+(int32_t)x_amp);
        } else {
            for (int i = 0; i < 6; i++) d2[i] = 192;
        }
        aio_load_dac2(d2);
        maml_probe_charge_column(matrix_id, row, col, 0);
        bsp_uDelay(10);

        /* 1. Probe Zero Weight (W+ = 128, W- = 128) */
        aio_trigger_settled_adc_read(raw45_zero, raw49_zero);

        /* 2. Probe Positive Weight (w = +w_fixed) */
        maml_probe_charge_column(matrix_id, row, col, +(int32_t)w_fixed);
        bsp_uDelay(10);
        aio_trigger_settled_adc_read(raw45_pos, raw49_pos);

        /* 3. Probe Negative Weight (w = -w_fixed) */
        maml_probe_charge_column(matrix_id, row, col, -(int32_t)w_fixed);
        bsp_uDelay(10);
        aio_trigger_settled_adc_read(raw45_neg, raw49_neg);

        /* Restore weights after probing */
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

/* ============================================================================
 * Hadamard Permutation, Hardware Scatter-Write (pi_inv) & FWHT-16 Diagnostics
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

    /* Build permutation pi[0..15] */
    for (int i = 0; i < 16; i++) resp.perm[i] = (uint8_t)i;
    if (mode != 0u) {
        for (int i = 15; i > 0; i--) {
            uint32_t j = prng_next() % (uint32_t)(i + 1);
            uint8_t tmp  = resp.perm[i];
            resp.perm[i] = resp.perm[j];
            resp.perm[j] = tmp;
        }
    }

    for (int s = 0; s < 16; s++) {
        resp.h_words[s] = HADAMARD_16[resp.perm[s]] & 0x7FFFu;
    }

    /* Configure T20 active mask & equilibrate in 3-State Hi-Z (0x8000) */
    t20_set_hadamard_mask(en_mask);
    t20_hadamard_tristate_center();
    bsp_uDelay(80);

    uint32_t f_khz = g_tel.hadamard_freq_khz;
    if (f_khz < 50)  f_khz = 50;
    if (f_khz > 500) f_khz = 500;
    uint16_t settle_cyc = (uint16_t)((50000u + (f_khz >> 1)) / f_khz);
    resp.settle_cycles = settle_cyc;
    AIO_REG(AIO_SETTLE_CYCLES) = ((uint32_t)25u << 16) | settle_cyc;

    T20_REG(T20_H_CTRL) = (1u << 2) | (1u << 9);

    if (mode < 3u) {
        /* Modes 0, 1, 2: Return-to-Hi-Z (0x8000) pre-equilibrated 2-word pulses
         * so C2/C4=1nF launches every step s from 1.65V Hi-Z equilibrium!
         * Use sck_div=15 (280 ns SCK high pulse) + r_adc_bit_align=2 (w[11:0] 12-bit). */
        AIO_REG(AIO_CTRL) = 0x00000FA9u;
        for (int s = 0; s < 16; s++) {
            uint8_t dst = (mode == 2u) ? (uint8_t)s : resp.perm[s];
            AIO_REG(AIO_PI_INV_LO) = (uint32_t)(dst & 0x0Fu);
            AIO_REG(AIO_PI_INV_HI) = 0u;
            *(volatile uint32_t *)(T20_BRIDGE_BASE + T20_H_TABLE + 0) = (uint32_t)resp.h_words[s];
            *(volatile uint32_t *)(T20_BRIDGE_BASE + T20_H_TABLE + 4) = 0x00008000u;

            T20_REG(T20_H_COUNT)  = 2;
            T20_REG(T20_H_PERIOD) = 24;
            T20_REG(T20_H_CTRL)   = (1u << 0) | (1u << 9);

            uint32_t timeout = 10000;
            while ((((T20_REG(T20_H_STATUS) & 2u) == 0u) ||
                    (T20_REG(T20_H_STATUS) & 1u) ||
                    (AIO_REG(AIO_STATUS) & 0x06u)) && --timeout) {
                bsp_uDelay(1);
            }
            bsp_uDelay(40);
        }
    } else {
        /* Mode 3: Continuous 17-step NRZ burst (without 0x8000 between steps) */
        AIO_REG(AIO_CTRL) = 0x000002A9u;
        uint32_t inv_lo = 0, inv_hi = 0;
        for (int s = 0; s < 8; s++) {
            inv_lo |= ((uint32_t)(resp.perm[s] & 0x0Fu)) << (4 * s);
            inv_hi |= ((uint32_t)(resp.perm[s + 8] & 0x0Fu)) << (4 * s);
        }
        AIO_REG(AIO_PI_INV_LO) = inv_lo;
        AIO_REG(AIO_PI_INV_HI) = inv_hi;
        for (int s = 0; s < 16; s++) {
            *(volatile uint32_t *)(T20_BRIDGE_BASE + T20_H_TABLE + 4 * s) = (uint32_t)resp.h_words[s];
        }
        *(volatile uint32_t *)(T20_BRIDGE_BASE + T20_H_TABLE + 4 * 16) = 0x00008000u;

        T20_REG(T20_H_COUNT)  = 17;
        T20_REG(T20_H_PERIOD) = 24;
        T20_REG(T20_H_CTRL)   = (1u << 0) | (1u << 9);

        uint32_t timeout = 50000;
        while ((((T20_REG(T20_H_STATUS) & 2u) == 0u) ||
                (T20_REG(T20_H_STATUS) & 1u) ||
                (AIO_REG(AIO_STATUS) & 0x06u)) && --timeout) {
            bsp_uDelay(1);
        }
    }

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

    /* Read Capture RAMs for ADC_45 and ADC_49 */
    for (int k = 0; k < 16; k++) {
        uint32_t a45 = AIO_CAP_ADC45_BASE + (uint32_t)(k * 16);
        uint32_t u01 = AIO_REG(a45 + 0x0);
        uint32_t u23 = AIO_REG(a45 + 0x4);
        uint32_t u45 = AIO_REG(a45 + 0x8);
        resp.cap45[k][0] = (int16_t)(u01 & 0xFFFFu);
        resp.cap45[k][1] = (int16_t)(u01 >> 16);
        resp.cap45[k][2] = (int16_t)(u23 & 0xFFFFu);
        resp.cap45[k][3] = (int16_t)(u23 >> 16);
        resp.cap45[k][4] = (int16_t)(u45 & 0xFFFFu);
        resp.cap45[k][5] = (int16_t)(u45 >> 16);

        uint32_t a49 = AIO_CAP_ADC49_BASE + (uint32_t)(k * 16);
        uint32_t v01 = AIO_REG(a49 + 0x0);
        uint32_t v23 = AIO_REG(a49 + 0x4);
        uint32_t v45 = AIO_REG(a49 + 0x8);
        resp.cap49[k][0] = (int16_t)(v01 & 0xFFFFu);
        resp.cap49[k][1] = (int16_t)(v01 >> 16);
        resp.cap49[k][2] = (int16_t)(v23 & 0xFFFFu);
        resp.cap49[k][3] = (int16_t)(v23 >> 16);
        resp.cap49[k][4] = (int16_t)(v45 & 0xFFFFu);
        resp.cap49[k][5] = (int16_t)(v45 >> 16);
    }

    /* Demodulate both Capture RAMs via FWHT-16 */
    maml_fwht16_demodulate(AIO_CAP_ADC45_BASE, resp.fwht45);
    maml_fwht16_demodulate(AIO_CAP_ADC49_BASE, resp.fwht49);

    /* Read quiet 3-state (0x8000 Hi-Z) ADC values */
    aio_trigger_settled_adc_read(resp.adc45_hiz, resp.adc49_hiz);

    /* Keep sck_div=15 (280 ns SCK high pulse) + r_adc_bit_align=2 (w[11:0]) */
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
            if (g_tel.run_mode == MAML_MODE_IDLE) {
                aio_trigger_settled_adc_read(g_tel.adc45_sig, g_tel.adc49_sig);
            }
            break;

        case MAML_CMD_SET_CONFIG:
            if (req_len >= 15) {
                g_tel.run_mode          = req[5];
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
                g_hid_amp_dac           = req[14] ? req[14] : 14;
                maml_refresh_all_columns();
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
                aio_trigger_settled_adc_read(g_tel.adc45_sig, g_tel.adc49_sig);
            }
            break;

        case MAML_CMD_PROBE_CELL:
            if (req_len >= 10) {
                int8_t  x_amp     = (int8_t)req[8];
                int8_t  w_fixed   = (int8_t)req[9];
                uint8_t mode_flag = (req_len >= 11) ? req[10] : 0x01u;
                return maml_probe_single_cell(req[5], req[6], req[7], x_amp, w_fixed, mode_flag, resp_buf, resp_max);
            } else if (req_len >= 8) {
                return maml_probe_single_cell(req[5], req[6], req[7], 96, 96, 0x00u, resp_buf, resp_max);
            }
            break;

        case MAML_CMD_STEP_ONCE:
            {
                /* Force an immediate Outer-Loop (Ref 40) gather step when triggered from GUI */
                uint8_t saved_mode = g_tel.run_mode;
                uint16_t saved_n   = g_tel.inner_loop_n;
                g_tel.run_mode     = MAML_MODE_BASE_TRAIN;
                g_tel.inner_loop_n = 1;
                g_tel.cur_inner_step = 0;
                maml_execute_step();
                g_tel.inner_loop_n = saved_n;
                g_tel.run_mode     = saved_mode;
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

