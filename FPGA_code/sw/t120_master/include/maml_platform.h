#ifndef MAML_PLATFORM_H
#define MAML_PLATFORM_H

#include <stdint.h>
#include <stddef.h>

/* ============================================================================
 * Inverted MAML Analog In-Memory Computing (AIMC) Platform Firmware Header
 * Patent Application SE 2630397-4
 * ============================================================================
 * Enforces:
 *   1. Full Differential (+/-) Symmetry:
 *        - 3-State Hadamard (OE=1 during table, OE=0 Hi-Z centered via 0x8000 on exit)
 *        - Differential Dual-2T1C Column Gates (G_P: W+ = 128 + w, G_N: W- = 128 - w)
 *        - Differential Bipolar DACs (signed = code - 128)
 *        - Differential Bipolar ADCs (signed Q1.11 = raw_12b - 2048)
 *   2. Non-Overlapping 4-Phase Settle-Then-Sample ADC Timing:
 *        Shift Hadamard -> Quiet Analog DC Settle (2..20 us) -> ADC S/H & Read -> Next State
 *   3. Strictly Non-Backprop Forward Hadamard Gradient Extraction (Equations 1-7):
 *        Never multiplies digitally by x_i; uses Carrier Wave Search (Eq. 5/6).
 *   4. Memory-Safe Dot-Product Second-Derivative MAML Outer Loop (Ref 40) +
 *      Inner Loop (Ref 41) + Operational Mode (Ref 42).
 * ============================================================================ */

#define MAML_MAGIC              0x4D414D4Cu  /* "MAML" */

/* UDP Command Opcodes (Port 5000) */
#define MAML_CMD_GET_TELEMETRY  0x10
#define MAML_CMD_SET_CONFIG     0x11
#define MAML_CMD_SET_HEATER     0x12
#define MAML_CMD_SET_LEDS       0x13
#define MAML_CMD_SET_DAC_DIAG   0x14
#define MAML_CMD_CENTER_WEIGHTS 0x15
#define MAML_CMD_SEED_WEIGHTS   0x16
#define MAML_CMD_PROBE_CELL     0x17
#define MAML_CMD_STEP_ONCE      0x18
#define MAML_CMD_DIAG_HADAMARD  0x19
#define MAML_CMD_RAND_DATA      0x1A

/* Run Modes */
#define MAML_MODE_IDLE          0
#define MAML_MODE_BASE_TRAIN    1   /* Ref 40 (Outer) + Ref 41 (Inner), 100% duty, Hidden Offset ON */
#define MAML_MODE_OPERATIONAL   2   /* Ref 42 (Live Compensation), capped duty %, Hidden Offset OFF */

/* Analog Jumper Modes */
#define JUMPER_OFF_NO_COMP      1   /* 1. OFF (no compensation) */
#define JUMPER_BYPASS_SIG2      2   /* 2. Bypass second sigmoid (linear Layer 2 output) */
#define JUMPER_USE_SIG2         3   /* 3. Use second sigmoid layer */

/* Seed Modes */
#define SEED_MODE_UNIFORM       0
#define SEED_MODE_AUTO_GAIN     1
#define SEED_MODE_ORTHOGONAL    2
#define SEED_MODE_CHECKERBOARD  3
#define SEED_MODE_LATIN         4

#define NUM_BASINS              4
#define NUM_STRATA_DEFAULT      10

#pragma pack(push, 1)

/* Binary Telemetry Packet sent from T120 to PC GUI over UDP Port 5000 */
typedef struct {
    uint32_t magic;                 /* 0x4D414D4C ("MAML") */
    uint8_t  msg_type;              /* 0x90 = Telemetry Response */
    uint8_t  run_mode;              /* 0=Idle, 1=Base Train (Ref 40/41), 2=Operational (Ref 42) */
    uint8_t  jumper_mode;           /* 1=OFF, 2=Bypass Sig2, 3=Use Sig2 */
    uint8_t  heater_armed;          /* 0=Disarmed, 1=ARMED (Hot warning active) */

    uint8_t  heater_wdog_ok;        /* 1=T20 S-bus watchdog active */
    uint8_t  heater_duty[4];        /* 0..255 duty cycle for HEAT_1..4 at 0.2 Hz PWM */
    uint8_t  comp_led_on;           /* COMP_LED_ON switch state */
    uint8_t  mat33_led_on;          /* MAT33_LED_ON switch state */
    uint8_t  osc_10hz_en;           /* 10 Hz 255/128/0 DAC test enabled */

    uint8_t  ovr_en;                /* Single-DAC manual override enabled */
    uint8_t  ovr_bank;              /* 0=DAC_2, 1=W_15, 2=W_12, 3=W_34 */
    uint8_t  ovr_ch;                /* 0..7 */
    uint8_t  ovr_val;               /* 0..255 */

    uint16_t hadamard_freq_khz;     /* 50 .. 500 kHz (default 500 kHz -> 2.0 us quiet settle) */
    uint8_t  max_meas_duty_pct;     /* 1 .. 100 % */
    uint8_t  seed_mode;             /* 0..4 */
    uint8_t  seed_swing_pct;        /* 0 .. 100 % of full DAC swing */
    uint8_t  carrier_row_k;         /* Selected carrier wave row k (0..5) from Eq. 5 */

    uint16_t inner_loop_n;          /* Inner loop steps N (Ref 41, default 100) */
    uint16_t cur_inner_step;        /* Current inner loop step (0..N-1) */
    uint32_t outer_loop_epoch;      /* Total Ref 40 outer loop epochs completed */
    uint32_t total_refresh_cycles;  /* Total 2T1C refresh cycles executed */
    uint8_t  cur_stratum_slot;      /* Current shuffled time slot P[k] (0..M-1) */
    uint8_t  num_strata_m;          /* Number of strata M (default 10) */
    uint16_t settle_cycles;         /* Quiet analog DC settle cycles at 50 MHz */

    /* Precision & Loss Metrics (scaled x1000 for integer transport) */
    uint32_t loss_total_milli;      /* L_total * 1000 (Eq. 1) */
    uint16_t bit_prec_comp_centi;   /* Compensated Bit Precision * 100 (e.g. 745 = 7.45 bits) */
    uint16_t bit_prec_uncomp_centi; /* Centered/Uncompensated Bit Precision * 100 */

    /* Live Analog Vectors (Signed differential values) */
    int16_t  x_ref[6];              /* Locked white-noise reference input (-127..+127) */
    int16_t  z_target[6];           /* Ideal digital target output M33 * x_ref */
    int16_t  adc45_sig[6];          /* Intermediate Layer 1 ADC_45 signed (raw - 2048) */
    int16_t  adc49_sig[6];          /* Final Output ADC_49 signed (raw - 2048) */
    int16_t  sigma2_slope[6];       /* Extracted 2nd activation slope (Eq. 6, Q1.14) */

    /* Signed Differential Weight Shadow Matrices (-127..+127 DAC offset from 128) */
    int8_t   w_m3[8][6];            /* First Correction Matrix M3 (W_15) */
    int8_t   w_m8[7][6];            /* Second Correction Matrix M8 (W_12) */
    int8_t   w_m33[6][6];           /* Primary Payload Matrix M33 (W_34) */
    int8_t   trim_dac_38;           /* Power supply trim-DAC 38 signed offset */
    int8_t   hid_trim_offset;       /* Emulated hidden offset on trim-DAC 38 (Ref 40/41) */

    /* 3D Loss Landscape / Basin Telemetry (Ref 40 pushing Ref 41 valleys together) */
    int16_t  w0_coord_x;            /* Projected 2D coordinate X of Base Model W_0 (Q8.8) */
    int16_t  w0_coord_y;            /* Projected 2D coordinate Y of Base Model W_0 (Q8.8) */
    uint32_t w0_loss_milli;         /* Loss at Base Model center W_0 * 1000 */
    int16_t  basin_coord_x[NUM_BASINS]; /* Projected X of inner-loop minimum valleys ("gropar") */
    int16_t  basin_coord_y[NUM_BASINS]; /* Projected Y of inner-loop minimum valleys ("gropar") */
    uint32_t basin_loss_milli[NUM_BASINS]; /* Minimum loss in each inner-loop valley * 1000 */
    int16_t  basin_hess_dot[NUM_BASINS];   /* Dot-product alignment g_init . g_final (Q1.14) */
    uint16_t basin_spread_milli;    /* Mean distance of inner-loop valleys from W_0 * 1000 */

    /* T20 Bridge Diagnostics */
    uint32_t t20_h_ack_ok;
    uint32_t t20_h_ack_miss;
    uint16_t t20_h_lat_last;
} maml_telemetry_pkt_t;

/* Cell Self-Diagnosis Response Packet */
typedef struct {
    uint32_t magic;                 /* 0x4D414D4C */
    uint8_t  msg_type;              /* 0x97 = Cell Probe Response */
    uint8_t  matrix_id;             /* 0=M3, 1=M8, 2=M33 */
    uint8_t  row;
    uint8_t  col;
    int16_t  adc45_pos[6];          /* ADC_45 when cell set to +w_probe */
    int16_t  adc45_neg[6];          /* ADC_45 when cell set to -w_probe */
    int16_t  adc45_zero[6];         /* ADC_45 when cell centered at 0 (128/128) */
    int16_t  adc49_pos[6];          /* ADC_49 when cell set to +w_probe */
    int16_t  adc49_neg[6];          /* ADC_49 when cell set to -w_probe */
    int16_t  adc49_zero[6];         /* ADC_49 when cell centered at 0 (128/128) */
} maml_cell_probe_resp_t;

/* Hadamard Permutation & Demodulation Diagnostic Response Packet */
typedef struct {
    uint32_t magic;                 /* 0x4D414D4C */
    uint8_t  msg_type;              /* 0x99 = Hadamard Diag Response */
    uint8_t  mode;                  /* 0=Identity, 1=Permuted+pi_inv, 2=Permuted no pi_inv */
    uint16_t en_mask;               /* Active Hadamard mask on T20 */
    uint8_t  perm[16];              /* 16-step permutation pi[0..15] */
    uint16_t h_words[16];           /* 16 Hadamard words loaded into T20_H_TABLE */
    uint32_t ack_ok;                /* H-bus ACK OK count */
    uint32_t ack_miss;              /* H-bus ACK MISS count */
    uint16_t lat_last;              /* H-bus ACK latency (last) */
    uint16_t lat_min;               /* H-bus ACK latency (min) */
    uint16_t lat_max;               /* H-bus ACK latency (max) */
    uint16_t t20_word_cnt;          /* T20 H-bus word counter from S-bus status */
    uint16_t t20_sync_err;          /* T20 H-bus sync error counter */
    uint16_t settle_cycles;         /* Quiet analog settle cycles used */
    int16_t  adc45_hiz[6];          /* Quiet 3-state (0x8000) ADC_45 readout */
    int16_t  adc49_hiz[6];          /* Quiet 3-state (0x8000) ADC_49 readout */
    int16_t  cap45[16][6];          /* Hardware Capture RAM for ADC_45 (16 x 6) */
    int16_t  cap49[16][6];          /* Hardware Capture RAM for ADC_49 (16 x 6) */
    int16_t  fwht45[16][6];         /* FWHT-16 Demodulated Matrix 3 / ADC_45 (16 x 6) */
    int16_t  fwht49[16][6];         /* FWHT-16 Demodulated Matrix 8 / ADC_49 (16 x 6) */
} maml_hadamard_diag_resp_t;

#pragma pack(pop)

/* Public API called by main.c */
void maml_platform_init(void);
void maml_platform_tick(void);
uint16_t maml_handle_udp_command(const uint8_t *req, uint16_t req_len,
                                 uint8_t *resp_buf, uint16_t resp_max);

#endif /* MAML_PLATFORM_H */

