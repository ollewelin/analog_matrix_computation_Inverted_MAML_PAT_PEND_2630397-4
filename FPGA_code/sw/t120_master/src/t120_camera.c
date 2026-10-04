////////////////////////////////////////////////////////////////////////////////
// t120_camera.c - CAM2 (IMX219) I2C Camera Setup for T120F324_A
// 
// Configures IMX219 camera via I2C for 96x96 RAW8 output to MIPI CSI-2 RX
// Uses SoC I2C interface (SYSTEM_I2C_0) directly connected to CAM2 I2C pins
// No PCA9542A mux required (unlike T20F169)
////////////////////////////////////////////////////////////////////////////////

#include <stdint.h>
#include "bsp.h"
#include "gpio.h"
#include "i2c.h"
#include "uart_mini_driver.h"

// =============================================================================
// CAM2 IMX219 Reference - Adapted from T20F169 PiCamDriver.h
// =============================================================================

// IMX219 7-bit I2C address
#define CAM_I2C_ADDR7     0x10            // IMX219 native 7-bit address
#define CAM_I2C_ADDR8     (CAM_I2C_ADDR7 << 1)  // 8-bit with R/W bit

// IMX219 Register Address Map (from PiCamDriver.h reference - verified correct)
#define mode_select             0x0100    // Standby/Streaming
#define CSI_LANE_MODE           0x0114    // Number of CSI lanes
#define DPHY_CTRL               0x0128    // DPHY control
#define EMBEDDED_DATA_EN        0x012E    // Embedded data enable (0x00=off, removes metadata lines)
#define EXCK_FREQ_1             0x012A    // Input clock frequency [15:8]
#define EXCK_FREQ_0             0x012B    // Input clock frequency [7:0]
#define FRM_LENGTH_A_1          0x0160    // Frame length [15:8]
#define FRM_LENGTH_A_0          0x0161    // Frame length [7:0]
#define LINE_LENGTH_A_1         0x0162    // Line length [15:8]
#define LINE_LENGTH_A_0         0x0163    // Line length [7:0]
#define X_ADD_STA_A_1           0x0164    // Crop X start [11:8]
#define X_ADD_STA_A_0           0x0165    // Crop X start [7:0]
#define X_ADD_END_A_1           0x0166    // Crop X end [11:8]
#define X_ADD_END_A_0           0x0167    // Crop X end [7:0]
#define Y_ADD_STA_A_1           0x0168    // Crop Y start [11:8]
#define Y_ADD_STA_A_0           0x0169    // Crop Y start [7:0]
#define Y_ADD_END_A_1           0x016A    // Crop Y end [11:8]
#define Y_ADD_END_A_0           0x016B    // Crop Y end [7:0]
#define x_output_size_A_1       0x016C    // Output width [11:8]
#define x_output_size_A_0       0x016D    // Output width [7:0]
#define y_output_size_A_1       0x016E    // Output height [11:8]
#define y_output_size_A_0       0x016F    // Output height [7:0]
#define X_ODD_INC_A             0x0170    // X odd increment
#define Y_ODD_INC_A             0x0171    // Y odd increment
#define IMG_ORIENTATION_A       0x0172    // Image orientation
#define BINNING_MODE_H_A        0x0174    // Horizontal binning
#define BINNING_MODE_V_A        0x0175    // Vertical binning
#define CSI_DATA_FORMAT_A_1     0x018C    // CSI data format [15:8]
#define CSI_DATA_FORMAT_A_0     0x018D    // CSI data format [7:0]
#define COARSE_INTEGRATION_TIME_A_1  0x015A  // Exposure time [15:8]
#define COARSE_INTEGRATION_TIME_A_0  0x015B  // Exposure time [7:0]
#define ANA_GAIN_GLOBAL_A       0x0157    // Analogue gain
#define DIG_GAIN_GLOBAL_A_1     0x0158    // Digital gain [11:8]
#define DIG_GAIN_GLOBAL_A_0     0x0159    // Digital gain [7:0]
// Test Pattern Registers (Section 3-2-5-5)
#define TP_MODE_1               0x0600    // test_pattern_mode [0]  (bit 0 only in high byte)
#define TP_MODE_0               0x0601    // test_pattern_mode [7:0]
// Modes: 0x0000=off, 0x0001=solid, 0x0002=100% color bars, 0x0003=fade grey,
//        0x0004=PN9, 0x0005=16 split bar, 0x0007=column counter, 0x0009=PN31
#define TP_RED_1                0x0602    // TD_R[9:8]
#define TP_RED_0                0x0603    // TD_R[7:0]
#define TP_GREENR_1             0x0604    // TD_GR[9:8]
#define TP_GREENR_0             0x0605    // TD_GR[7:0]
#define TP_BLUE_1               0x0606    // TD_B[9:8]
#define TP_BLUE_0               0x0607    // TD_B[7:0]
#define TP_GREENB_1             0x0608    // TD_GB[9:8]
#define TP_GREENB_0             0x0609    // TD_GB[7:0]

// =============================================================================
// TEST PATTERN ON/OFF TOGGLE  -- change this to 0 to disable test pattern
// =============================================================================
#define TEST_PATTERN_ENABLE     0         // 1 = 100% color bars, 0 = live camera
//Note have never get Test pattern to kick in and override the real video unclear why Test pattern not working

// PLL clock registers
#define VTPXCK_DIV              0x0301
#define VTSYCK_DIV              0x0303
#define PREPLLCK_VT_DIV         0x0304
#define PREPLLCK_OP_DIV         0x0305
#define PLL_VT_MPY_1            0x0306    // [10:8]
#define PLL_VT_MPY_0            0x0307    // [7:0]
#define OPPXCK_DIV              0x0309
#define OPSYCK_DIV              0x030B
#define PLL_OP_MPY_1            0x030C    // [10:8]
#define PLL_OP_MPY_0            0x030D    // [7:0]

// =============================================================================
// UART Helper Functions (from test_1g_udp.c)
// =============================================================================
void uart_drain(void) {
    while (!(uart_mini_get_status() & UART_STATUS_TX_EMPTY)) { }
    bsp_uDelay(2000);
}

void print(const char *s) {
    uart_mini_tx_string(s);
}

void println(const char *s) {
    print(s);
    uart_mini_newline();
    uart_drain();
}

void print_hex8(uint8_t val) {
    static const char hex[] = "0123456789ABCDEF";
    uart_mini_tx_byte(hex[(val >> 4) & 0xF]);
    uart_mini_tx_byte(hex[val & 0xF]);
}

void print_hex16(uint16_t val) {
    print_hex8((val >> 8) & 0xFF);
    print_hex8(val & 0xFF);
}

void print_hex32(uint32_t val) {
    print_hex16((val >> 16) & 0xFFFF);
    print_hex16(val & 0xFFFF);
}

// =============================================================================
// I2C Helper Functions
// =============================================================================

/**
 * i2c_init_100khz - Configure I2C for ~100 kHz operation
 * 
 * Uses SoC clock (50 MHz assumed per soc.h) to generate ~100 kHz SCL
 * Adapted from T20F169 reference code
 */
static void i2c_init_100khz(void) {
    I2c_Config cfg;

    // SoC clock frequency (50 MHz for T120_GCLK)
    const uint32_t fclk_hz      = 50000000;  // 50 MHz
    const uint32_t cycles_per_us = fclk_hz / 1000000;  // 50 cycles per µs

    // Target 100 kHz SCL: period ~10 µs -> ~5 µs low, ~5 µs high
    const uint32_t t_low_us  = 5;
    const uint32_t t_high_us = 5;

    // Conservative setup/hold timings
    const uint32_t tsu_dat_us = 1;   // SDA setup time
    const uint32_t t_buf_us   = 5;   // STOP to START

    // Fill config (all are "cycles - 1")
    cfg.samplingClockDivider = 3;                                    // modest oversampling
    cfg.timeout              = (1000 * cycles_per_us) - 1;          // ~1 ms bus timeout
    cfg.tsuDat               = (tsu_dat_us * cycles_per_us) - 1;    // SDA setup
    cfg.tLow                 = (t_low_us  * cycles_per_us) - 1;     // SCL low
    cfg.tHigh                = (t_high_us * cycles_per_us) - 1;     // SCL high
    cfg.tBuf                 = (t_buf_us  * cycles_per_us) - 1;     // STOP→START

    i2c_applyConfig(SYSTEM_I2C_0_IO_CTRL, &cfg);
    
    print("I2C 100kHz init OK"); println("");
}

/* --- Timeout-protected I2C primitives ----------------------------------- */

/* Print raw I2C master status register as hex for analyzer debug */
static void dbg_i2c_status(void) {
    uint32_t s = read_u32(SYSTEM_I2C_0_IO_CTRL + I2C_MASTER_STATUS);
    print(" [MSTS=0x"); print_hex32(s); print("] ");
    uart_drain();
}

/* cam_i2c_start - START with timeout; returns 0=ok, -1=timeout */
static int cam_i2c_start(void) {
    i2c_masterStart(SYSTEM_I2C_0_IO_CTRL);
    volatile uint32_t t = 2000000;
    while (read_u32(SYSTEM_I2C_0_IO_CTRL + I2C_MASTER_STATUS) & I2C_MASTER_START) {
        if (--t == 0) { print("[START_TO]"); dbg_i2c_status(); return -1; }
    }
    return 0;
}

/* cam_i2c_stop - STOP with timeout; always continues (best-effort cleanup) */
static void cam_i2c_stop(void) {
    i2c_masterStop(SYSTEM_I2C_0_IO_CTRL);
    volatile uint32_t t = 2000000;
    while (read_u32(SYSTEM_I2C_0_IO_CTRL + I2C_MASTER_STATUS) & I2C_MASTER_BUSY) {
        if (--t == 0) { print("[STOP_TO]"); uart_drain(); return; }
    }
}

/* cam_i2c_txbyte_ack - TX byte + listen for ACK, timeout-protected.
 * Mirrors TX_AND_CHECK macro: write byte, write NACK-slot to TX_ACK,
 * wait for TX_ACK VALID to clear (= 9-bit frame done), then read RX_ACK. */
static int cam_i2c_txbyte_ack(uint8_t byte) {
    i2c_txByte(SYSTEM_I2C_0_IO_CTRL, byte);
    /* Write NACK to TX_ACK - this releases SDA for the ACK bit clock cycle */
    i2c_txNack(SYSTEM_I2C_0_IO_CTRL);
    /* Wait for TX_ACK VALID to clear = 9-bit slot (8 data + 1 ACK) complete */
    volatile uint32_t t = 1000000;
    while (read_u32(SYSTEM_I2C_0_IO_CTRL + I2C_TX_ACK) & I2C_TX_VALID) {
        if (--t == 0) { print("[TXACK_TO]"); uart_drain(); return -1; }
    }
    /* RX_ACK bit: 0 = slave ACKed, 1 = slave NACKed */
    if (read_u32(SYSTEM_I2C_0_IO_CTRL + I2C_RX_ACK) & I2C_RX_VALUE) {
        return -1;
    }
    return 0;
}

/* cam_write_reg8 - Write 8-bit value to 16-bit IMX219 register.
 * Verbose: prints which step fails so you can correlate with analyzer. */
static int cam_write_reg8(uint16_t reg, uint8_t data) {
    if (cam_i2c_start()) { print("[WR:START_FAIL]"); uart_drain(); return -1; }
    if (cam_i2c_txbyte_ack(CAM_I2C_ADDR8 | I2C_WRITE)) {
        print("[WR:ADDR_NACK addr=0x"); print_hex8(CAM_I2C_ADDR8); print("]");
        uart_drain(); goto fail;
    }
    if (cam_i2c_txbyte_ack((reg >> 8) & 0xFF)) {
        print("[WR:REG_H_NACK]"); uart_drain(); goto fail;
    }
    if (cam_i2c_txbyte_ack(reg & 0xFF)) {
        print("[WR:REG_L_NACK]"); uart_drain(); goto fail;
    }
    if (cam_i2c_txbyte_ack(data)) {
        print("[WR:DATA_NACK]"); uart_drain(); goto fail;
    }
    cam_i2c_stop();
    bsp_uDelay(500);
    return 0;
fail:
    cam_i2c_stop();
    bsp_uDelay(500);
    return -1;
}

/* cam_read_reg8 - Read 8-bit value from 16-bit IMX219 register. */
static uint8_t cam_read_reg8(uint16_t reg) {
    uint8_t val = 0;
    if (cam_i2c_start()) { print("[RD:START_FAIL]"); uart_drain(); return 0; }
    if (cam_i2c_txbyte_ack(CAM_I2C_ADDR8 | I2C_WRITE)) { print("[RD:ADDR_W_NACK]"); uart_drain(); goto fail; }
    if (cam_i2c_txbyte_ack((reg >> 8) & 0xFF))          { print("[RD:REG_H_NACK]");  uart_drain(); goto fail; }
    if (cam_i2c_txbyte_ack(reg & 0xFF))                 { print("[RD:REG_L_NACK]");  uart_drain(); goto fail; }
    if (cam_i2c_start()) { print("[RD:RESTART_FAIL]"); uart_drain(); goto fail; }
    if (cam_i2c_txbyte_ack(CAM_I2C_ADDR8 | I2C_READ))  { print("[RD:ADDR_R_NACK]"); uart_drain(); goto fail; }
    i2c_txByte(SYSTEM_I2C_0_IO_CTRL, 0xFF);
    i2c_txNack(SYSTEM_I2C_0_IO_CTRL);
    volatile uint32_t t = 500000;
    while (read_u32(SYSTEM_I2C_0_IO_CTRL + I2C_TX_ACK) & I2C_TX_VALID) {
        if (--t == 0) break;
    }
    val = (uint8_t)i2c_rxData(SYSTEM_I2C_0_IO_CTRL);
fail:
    cam_i2c_stop();
    bsp_uDelay(500);
    return val;
}

// =============================================================================
// IMX219 Camera Initialization (96x96 RAW8 for CAM2)
// =============================================================================

/**
 * imx219_access_seq - Required access sequence before register writes
 * 
 * Some IMX219 internal states require this specific sequence
 */
static void imx219_access_seq(void) {
    print("  Access seq..."); uart_drain();
    
    int e = 0;
    e |= cam_write_reg8(0x30EB, 0x05);
    e |= cam_write_reg8(0x30EB, 0x0C);
    e |= cam_write_reg8(0x300A, 0xFF);
    e |= cam_write_reg8(0x300B, 0xFF);
    e |= cam_write_reg8(0x30EB, 0x05);
    e |= cam_write_reg8(0x30EB, 0x09);
    
    if (e) println("NACK!");
    else   println("OK");
}

/**
 * imx219_init_96x96_raw8 - Full initialization for 96x96 RAW8 output
 *
 * Register sequence ported from working PiCamDriver.c (Ti60F225 reference).
 * Key fixes vs previous version:
 *   - Correct EXCK_FREQ addresses (0x012A/0x012B not 0x0137/0x0136)
 *   - Correct COARSE_INTEGRATION_TIME addresses (0x015A/0x015B)
 *   - All _1/_0 register pairs corrected (MSB first)
 *   - PLL registers now programmed (required for MIPI clock generation)
 *   - CSI_DATA_FORMAT_A set to RAW8 (0x08/0x08)
 *   - Binning, X/Y ODD INC, gain registers added
 *   - mode_select=0x01 remains last command
 */
static void imx219_init_96x96_raw8(void) {
    println("=**= CAM2 IMX219 INIT =**=");

    // Dump raw I2C peripheral state before first transaction
    print("  I2C raw status:"); dbg_i2c_status();
    print("  SCL_read="); print_hex8(read_u32(SYSTEM_I2C_0_IO_CTRL + I2C_SLAVE_STATUS) & 0x4 ? 1 : 0);
    print("  SDA_read="); print_hex8(read_u32(SYSTEM_I2C_0_IO_CTRL + I2C_SLAVE_STATUS) & 0x2 ? 1 : 0);
    println("");

    // Stop streaming (standby mode) - must be first
    print("  Stop stream..."); uart_drain();
    if (cam_write_reg8(mode_select, 0x00)) {
        println(" FAIL");
        print("  Final I2C status:"); dbg_i2c_status(); println("");
        println("  Camera not responding - check power/XCLK/pullups");
        return;
    }
    println(" OK");

    // Required access sequence (manufacturer unlock)
    imx219_access_seq();

    // MIPI CSI-2: 2 lanes, DPHY auto, 24 MHz input clock
    // Disable embedded data lines (metadata before pixel data) - prevents INVALID_DATA_TYPE (bit 13)
    print("  MIPI config..."); uart_drain();
    cam_write_reg8(CSI_LANE_MODE,    0x01);
    cam_write_reg8(DPHY_CTRL,        0x00);
    cam_write_reg8(EMBEDDED_DATA_EN, 0x00);  // 0x00=disable metadata lines => clears bit-13 error
    cam_write_reg8(EXCK_FREQ_1,      0x18);  // 24 MHz
    cam_write_reg8(EXCK_FREQ_0,      0x00);
    println("OK");

    // Frame and line timing
    print("  Frame timing..."); uart_drain();
    cam_write_reg8(FRM_LENGTH_A_1,  0x06);
    cam_write_reg8(FRM_LENGTH_A_0,  0xE3);
    cam_write_reg8(LINE_LENGTH_A_1, 0x0D);
    cam_write_reg8(LINE_LENGTH_A_0, 0x78);
    println("OK");

    // ROI: 224x224 sensor pixels => 112x112 colour dots (2x2 Bayer per dot)
    // Centered on IMX219 (3280x2464 sensor):
    //   X: centre=1640, start=1640-112=1528 (0x05F8), end=1528+223=1751 (0x06D7)
    //   Y: centre=1232, start=1232-112=1120 (0x0460), end=1120+223=1343 (0x053F)
    // NOTE: X_ADD_END must equal X_ADD_START + output_width - 1 (no decimation).
    //       Old config had X_ADD_END=3279 (whole sensor) which caused word-count
    //       mismatch and the repeated-pixel glitch at column 86-90.
    print("  ROI 224x224 centered..."); uart_drain();
    cam_write_reg8(X_ADD_STA_A_1, 0x05);    // XStart=1528 = 0x05F8
    cam_write_reg8(X_ADD_STA_A_0, 0xF8);
    cam_write_reg8(X_ADD_END_A_1, 0x06);    // XEnd=1751  = 0x06D7
    cam_write_reg8(X_ADD_END_A_0, 0xD7);
    cam_write_reg8(Y_ADD_STA_A_1, 0x04);    // YStart=1120 = 0x0460
    cam_write_reg8(Y_ADD_STA_A_0, 0x60);
    cam_write_reg8(Y_ADD_END_A_1, 0x05);    // YEnd=1343  = 0x053F
    cam_write_reg8(Y_ADD_END_A_0, 0x3F);
    // Output size: 224 x 224 = 0x00E0
    cam_write_reg8(x_output_size_A_1, 0x00);
    cam_write_reg8(x_output_size_A_0, 0xE0);   // 224 = 0x00E0
    cam_write_reg8(y_output_size_A_1, 0x00);
    cam_write_reg8(y_output_size_A_0, 0xE0);   // 224 = 0x00E0
    println("OK");

    // Pixel increment and binning (no binning = 1:1)
    print("  Binning/inc..."); uart_drain();
    cam_write_reg8(X_ODD_INC_A,      0x01);
    cam_write_reg8(Y_ODD_INC_A,      0x01);
    cam_write_reg8(BINNING_MODE_H_A, 0x00);    // no binning
    cam_write_reg8(BINNING_MODE_V_A, 0x00);
    println("OK");

    // CSI data format: RAW8 (0x08 / 0x08)
    print("  CSI fmt RAW8..."); uart_drain();
    cam_write_reg8(CSI_DATA_FORMAT_A_1, 0x08);
    cam_write_reg8(CSI_DATA_FORMAT_A_0, 0x08);
    println("OK");
    // CSI data format: RAW10 (0x0A / 0x0A)
  //  print("  CSI fmt RAW10..."); uart_drain();
  //  cam_write_reg8(CSI_DATA_FORMAT_A_1, 0x0A);
  //  cam_write_reg8(CSI_DATA_FORMAT_A_0, 0x0A);
  //  println("OK");

    // PLL configuration (from working Ti60 reference, 24 MHz XCLK -> MIPI clock)
    print("  PLL..."); uart_drain();
    cam_write_reg8(VTPXCK_DIV,      0x04);//original 0x05
    cam_write_reg8(VTSYCK_DIV,      0x01);//0x01 origally
    cam_write_reg8(PREPLLCK_VT_DIV, 0x03);
    cam_write_reg8(PREPLLCK_OP_DIV, 0x03);
    cam_write_reg8(PLL_VT_MPY_1,    0x00);
    cam_write_reg8(PLL_VT_MPY_0,    0x39);//Original 0x39
    cam_write_reg8(OPPXCK_DIV,      0x0A);
    cam_write_reg8(OPSYCK_DIV,      0x01);
    cam_write_reg8(PLL_OP_MPY_1,    0x00);
    cam_write_reg8(PLL_OP_MPY_0,    0x72);//Original 0x72 (0x73,0x72, 0x62 tested OK)
    println("OK");

    // Exposure and gain
    print("  Exposure/gain..."); uart_drain();
    cam_write_reg8(COARSE_INTEGRATION_TIME_A_1, 0x04);
    cam_write_reg8(COARSE_INTEGRATION_TIME_A_0, 0x54);
    cam_write_reg8(ANA_GAIN_GLOBAL_A,           0xB9);
    cam_write_reg8(DIG_GAIN_GLOBAL_A_1,         0x02);
    cam_write_reg8(DIG_GAIN_GLOBAL_A_0,         0x00);
    println("OK");

    // Image orientation (normal)
    cam_write_reg8(IMG_ORIENTATION_A, 0x00);

    // Start streaming - MUST happen before test pattern config per datasheet
    // "The prescribed output is obtained by setting the necessary registers while the sensor is operating"
    print("  Start stream..."); uart_drain();
    bsp_uDelay(10000);  // 10 ms settle before streaming
    cam_write_reg8(mode_select, 0x01);
    println("OK");

    // ----- Test Pattern Configuration (after streaming starts per datasheet) -----
#if TEST_PATTERN_ENABLE
    print("  Test pattern 100% color bars..."); uart_drain();
    bsp_uDelay(5000);  // Give sensor time to enter streaming mode
    
    // Enable test pattern generator (100% color bars)
    cam_write_reg8(TP_MODE_1, 0x00);    // test_pattern_mode[8] = 0
    cam_write_reg8(TP_MODE_0, 0x02);    // 0x0002 = 100% color bars
    println("ENABLED");
    
    // Verify test pattern was set by reading back registers
    print("  Verifying test pattern..."); uart_drain();
    uint8_t tp_mode_1_read = cam_read_reg8(TP_MODE_1);
    uint8_t tp_mode_0_read = cam_read_reg8(TP_MODE_0);
    print("TP_MODE=0x"); print_hex8(tp_mode_1_read); print_hex8(tp_mode_0_read);
    println(" (expect 0x0002)");
#else
    // No test pattern (live sensor image)
    print("  Test pattern OFF"); uart_drain();
    cam_write_reg8(TP_MODE_1, 0x00);
    cam_write_reg8(TP_MODE_0, 0x00);    // 0x0000 = off
    println("");
#endif

    println("=CAM2 READY=");
}

// =============================================================================
// Main Entry Point
// =============================================================================

void camera_init(void) {
    // Initialize I2C interface
    print("Init I2C.."); uart_drain();
    i2c_init_100khz();

    // Wait for camera to be fully powered up before first I2C access
    print("Settling..."); uart_drain();
    bsp_uDelay(50000);  // 50 ms power-on settlement
    println("OK");

    // Initialize CAM2
    imx219_init_96x96_raw8();

    println("=CAM SETUP COMPLETE=");
}
