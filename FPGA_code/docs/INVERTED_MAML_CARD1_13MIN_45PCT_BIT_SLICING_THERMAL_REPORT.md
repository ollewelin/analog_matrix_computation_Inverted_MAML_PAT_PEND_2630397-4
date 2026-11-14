# Inverted MAML Card 1: 13-Minute 45% PWM 2-Beat Analog Bit-Slicing Thermal Report

**Hardware:** Card 1 (`Trion T120F324` Master SoC + `Trion T20F256` Coprocessor, `1k/3.3k` summing attenuator)  
**Dataset:** `FPGA_code/logs/bit_slicing/card1_thermal_slicing_45pct_k1_lr0p06_l2_1024_13min_6warm.json` (`5,278` pairs)  
**Hyperparameters:** `Heater Duty = 45%` (T20 0.2 Hz 90°-staggered hardware PWM), `K = 1`, `LR = 0.06`, `L2 = 1024`, `Momentum = 0.0` (pure SGD)  

---

## 1. Executive Summary

Under aggressive **45% hardware PWM thermal stress**, open-loop analog precision (`Regler OFF`, `W8 = 0`) degraded by **3.63 bits** from the cold baseline (**9.38 bits** in Phase 2) down to **5.75 bits** in Phase 8. Enabling closed-loop Forward Hadamard Propagation (`Regler ON`, `LR = 0.06`, `L2 = 1024`, `K = 1`) produced clear, repeatable positive ENOB steps during hot operation:

- **Phase 5 vs Phase 6 (Warm):** Mean **+0.93 bits** (**6.95 b** vs **6.02 b**); steady-state **+1.08 bits** (**7.06 b** vs **5.98 b**).
- **Phase 7 vs Phase 8 (Warm):** Mean **+0.87 bits** (**6.62 b** vs **5.75 b**); steady-state **+1.01 bits** (**6.74 b** vs **5.73 b**).
- **Bottleneck Identified:** In Phases 5 and 7, `W8_msb` and `W8_lsb` both **railed at `+120 LSB`** under the `1k/3.3k` passive summing attenuator. Because the Vernier branch hit its rail, compensation authority saturated before fully canceling the 45% thermal drift. Resoldering the attenuator to **`1k/2.2k`** (+50% Vernier gain) is the primary hardware action item.

---

## 2. Phase-by-Phase Experimental Results

| Phase | Regime | Pairs | Mean Comb ENOB | Steady-State Comb | MSB ENOB | LSB ENOB | W8 MSB [min, max] | W8 LSB [min, max] |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | :--- | :--- |
| P1 | Cold / Regler ON | 481 | **9.37 b** | 9.36 b | 5.51 b | 5.58 b | `[-26, +5]` | `[-5, +13]` |
| P2 | Cold / Regler OFF | 387 | **9.38 b** | 9.36 b | 5.38 b | 5.62 b | `[+0, +0]` | `[+0, +0]` |
| P3 | Warm / Regler ON | 1208 | **8.59 b** | 8.14 b | 4.78 b | 4.65 b | `[-26, +88]` | `[-48, +90]` |
| P4 | Warm / Regler OFF | 858 | **7.03 b** | 6.73 b | 3.71 b | 3.63 b | `[+0, +0]` | `[+0, +0]` |
| P5 | Warm / Regler ON | 690 | **6.95 b** | 7.06 b | 3.72 b | 3.48 b | `[-93, +120]` | `[-63, +120]` |
| P6 | Warm / Regler OFF | 616 | **6.02 b** | 5.98 b | 3.31 b | 3.27 b | `[+0, +0]` | `[+0, +0]` |
| P7 | Warm / Regler ON | 549 | **6.62 b** | 6.74 b | 3.59 b | 3.37 b | `[-94, +120]` | `[-89, +120]` |
| P8 | Warm / Regler OFF | 489 | **5.75 b** | 5.73 b | 3.21 b | 3.17 b | `[+0, +0]` | `[+0, +0]` |

![Full 13-min Timeline](fig_card1_thermal_slicing_45pct_13min.png)

![Hot-Phase Regler Step Response](fig_45pct_phase5_8_transient.png)

---

## 3. 2-Beat Analog Bit-Slicing Architecture & Locked Calibration

1. **2-Beat Time-Multiplexed Slices:** Each pair executes Beat `2k` (`MSB`, Bank 0, `M_msb` scaled to ±50 LSB) followed by Beat `2k+1` (`LSB`, Bank 1, `M_lsb = round(0.75 * M_msb)`). T120 maintains completely isolated weight/velocity banks (`g_slice_bank[2]`, `0x1E subcmd 4`).
2. **Strict Honesty (`t = 0` Cold Calibration):** Static linear gain `alpha` and DC offset `beta` are calibrated once at `t = 0` (heaters OFF) and locked inside T120 (`g_slice_alpha_q16`, `g_slice_beta`, `0x1E subcmd 5`) for the entire 13-minute run with zero post-hoc DSP correction.
3. **Combined 8-Bit ENOB:** `Y_8bit = 16 * Y_MSB + Y_LSB`, evaluated continuously via `min(4.0, ENOB_MSB) + ENOB_LSB * clip(ENOB_MSB / 4.0, 0, 1)`.

---

## 4. Roadmap: Post-Analog Alpha/Beta 8-Channel FHP & `1k/2.2k` Attenuator

Per `post_analog_alpha_beta_calibration_8_channel_fhp_specification.md`:
- **Short-Term (Next Hardware Step):** Replace the `1k/3.3k` passive summing attenuator at `SUM35` with **`1k/2.2k`** to increase `Matrix 3/8` Vernier authority by `1.50x`, eliminating the `+120 LSB` rail saturation observed in Phases 5 and 7.
- **Medium-Term (`PCBA v1.3.2` -> `SKY130` ASIC):** Add a shunt-triode post-analog `alpha/beta` stage before `ADC_49` driven by an expanded 16-pulse (`8x8`) Hadamard burst (Ch 0–5: matrix rows, Ch 6: `V_gain`, Ch 7: `V_offset`). Offloading static DC offset and linear gain to this slow outer loop lets L2 regularization keep `W8` centered near `0 LSB` for maximum non-linear thermal headroom.
