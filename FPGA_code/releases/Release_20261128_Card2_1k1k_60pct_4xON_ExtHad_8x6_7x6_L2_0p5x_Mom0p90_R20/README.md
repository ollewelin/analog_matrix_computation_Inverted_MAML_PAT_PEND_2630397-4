# Release Package: Card 2 (`1k / 1k` = 50/50) Extended 2x8 Hadamard (`8x6` M3 / `7x6` M8) + Trainable Bias & Reference Cells

**Patent Pending:** SE 2630397-4 (Open Science Hardware, `SHL-2.1`)  
**Hardware Target:** Card 2 (`Trion T120F324` Master SoC + `Trion T20F256` Coprocessor, `1k / 1k` Summing Attenuator)  
**HW Logic Version:** `0x20261128` (`ID=MAM1`, full 16-pulse `2x8` Sylvester `H_8` orthogonal Hadamard engine, zero STA timing violations)  
**SW Firmware:** `T120_SOC_ETH_FW v2.2-MAML (Build Nov 28 2026 12:42:43)`  
**Experiment Settings:** `Heater = 60% PWM (120s ON / 30s OFF)`, `K = 1`, `LR = 0.055`, `L2 = 960 (0.5x)`, `Momentum = 0.90`, `Clamp = ±90 LSB`, Staircase Init (`±40 LSB` on `M(3) R6–R7`)

## Key Results (`7,456` sample pairs)
- **Cold Baseline (`P1–P2`):** `9.50 b` (`1,266–1,731 LSB²`)
- **Warm ON Convergence (`P11`, `P13`):** `7.57 -> 8.33 b` (`1.86x` loss drop) and `7.54 -> 8.30 b` (`1.75x` loss drop)
- **Overall Thermal-Detrended Metrics:** `Warm ON` lift **`+0.54 b`**, loss reduction ratio **`1.63x`**, hot climb **`+0.66 b`**, jitter **`0.17 b`**, composite score **`+2.296`**
- **Normalized Warm RMSE (`P13`):** `4,727` (`ON`) vs `7,019` (`OFF`)

## Package Contents
- `T120F324/`: Synthesized `T120_MALM.bit`, `T120_MALM.hex`, `T120_MALM.timing.rpt`, `t120_inter_fpga_bridge.sv`, `t120_analog_io_ctrl.sv`, `T120_MALM.xml`, `const.sdc`
- `sw/`: `maml_platform.c`, `maml_platform.h`, `t120_bridge_regs.h`, `t120_master.bin`
- `pc_python/`: `run_card1_extended_thermal_sweep.py`, `generate_card2_1k1k_report.py`, `verify_2x8_hadamard_bias_ref.py`, `verify_and_guard_version.py`, `w3_staircase_pattern.json`
- `reports_and_logs/`: `INVERTED_MAML_CARD2_1K1K_60PCT_4XON_EXTHAD_8X6_7X6_L2_0P5X_MOM0P90_R20_THERMAL_SLICING_REPORT.{md,pdf}`, `card2_1k1k_60pct_4xon_exthad_8x6_7x6_l2_0p5x_0p5x_mom0p90_dc_cal.json`, and all 6 publication figures (`figures/`)
