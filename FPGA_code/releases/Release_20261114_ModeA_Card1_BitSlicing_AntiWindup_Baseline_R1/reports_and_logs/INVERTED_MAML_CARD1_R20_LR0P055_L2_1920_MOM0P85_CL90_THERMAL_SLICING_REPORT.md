# Inverted MAML Card 1: Round 20 Thermal Bit-Slicing Report (R20_LR0P055_L2_1920_MOM0P85_CL90)

**Hardware:** Card 1 (`Trion T120F324` Master SoC + `Trion T20F256` Coprocessor, `1k / 2.2k` Passive Attenuator)  
**Firmware:** `T120_SOC_ETH_FW v2.2-MAML (SW Build Nov 14 2026 10:15:16)`, `HW_LOGIC: 0x20261030`  
**Dataset:** `FPGA_code/logs/bit_slicing/card1_demo_20261114_170111_cl90.json` (`4,629` pairs)  
**Hyperparameters:** `Heater = 30%/40% PWM`, `K = 1`, `LR = 0.055`, `L2 = 1920`, `Momentum = 0.85`, `Clamp = ±90 LSB`  

---

## 1. Executive Summary & Verification Milestones

1. **Cold Reference Without Heating (`cold_verify_k1.json`):** `Cold / Regler ON` mean **9.45 b** (`min 8.80 b`), `Cold / Regler OFF` mean **9.45 b** (`min 8.61 b`).
2. **Thermal-Detrended Closed-Loop Performance (Round 20):** Weighted detrended `Warm ON` lift **`+0.48 b`**, loss reduction ratio **`1.42x`**, detrended convergence climb **`+0.63 b`**, jitter **`0.36 b`**, anti-windup recovery **`0.89`**, composite score **`+1.691`**.
3. **Cumulative Best Across R1–R1:** Round 1 (`LR=0.055, L2=1920, Mom=0.85, Clamp=±90`) with score **`+1.691`**.

---

## 2. Cumulative Multi-Round Optimization Comparison (R1–R1)

| Round | LR | L2 Reg | Mom | Clamp | Lift vs E_base | Loss Ratio | Hot Climb | Jitter | Recovery | Composite Score |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| R1 ★ | `0.055` | `1920` | `0.85` | `±90` | `+0.48 b` | `1.42x` | `+0.63 b` | `0.36 b` | `0.89` | **`+1.691`** |

## 3. Round 20 Phase-by-Phase Telemetry

| Phase | Regime | Pairs | Comb ENOB (`Start -> Late`, Mean) | Δ vs E_base | Total Loss (`Start -> Late`) | Loss Ratio | W8 Peak `[M, L]` | W3 Peak | W8 nz |
| :--- | :--- | ---: | :---: | :---: | :---: | :---: | :---: | :---: | ---: |
| P1 | Cold / Regler ON | 461 | `9.48 -> 9.41` (**9.39 b**) | — | `4138 -> 4443` | — | `[40, 23]` | `2` | `460` |
| P2 | Cold / Regler OFF | 406 | `9.36 -> 9.37` (**9.37 b**) | — | `4976 -> 5177` | — | `[0, 0]` | `0` | `0` |
| P3 | 30% Heat / Regler ON | 389 | `9.34 -> 9.45` (**9.33 b**) | **-0.05 b** | `5136 -> 3683` | **1.21x** | `[22, 90]` | `30` | `389` |
| P4 | 30% Heat / Regler OFF | 388 | `9.37 -> 9.24` (**9.34 b**) | **-0.10 b** | `3936 -> 6575` | **1.02x** | `[0, 0]` | `0` | `0` |
| P5 | 30% Heat / Regler ON | 377 | `9.19 -> 8.97` (**9.02 b**) | **+0.15 b** | `6776 -> 10196` | **1.28x** | `[54, 35]` | `7` | `377` |
| P6 | 30% Heat / Regler OFF | 355 | `8.74 -> 8.51` (**8.57 b**) | **+0.00 b** | `12863 -> 18585` | **1.05x** | `[0, 0]` | `0` | `0` |
| P7 | 30% Heat / Regler ON | 115 | `8.40 -> 8.41` (**8.49 b**) | **+0.07 b** | `17908 -> 21164` | **1.18x** | `[90, 85]` | `16` | `115` |
| P8 | 30% Heat / Regler OFF | 305 | `8.27 -> 8.02` (**8.11 b**) | **-0.05 b** | `24460 -> 29841` | **1.00x** | `[0, 0]` | `0` | `0` |
| P9 | 40% Heat / Regler ON | 327 | `8.15 -> 8.20` (**8.19 b**) | **+0.38 b** | `27268 -> 25478` | **1.42x** | `[90, 90]` | `22` | `327` |
| P10 | 40% Heat / Regler OFF | 308 | `7.76 -> 7.09` (**7.31 b**) | **+0.01 b** | `36286 -> 51047` | **1.00x** | `[0, 0]` | `0` | `0` |
| P11 | 40% Heat / Regler ON | 311 | `7.18 -> 7.78` (**7.74 b**) | **+0.94 b** | `48193 -> 35056` | **1.70x** | `[90, 90]` | `26` | `311` |
| P12 | 40% Heat / Regler OFF | 299 | `6.83 -> 6.53` (**6.63 b**) | **+0.01 b** | `58998 -> 67082` | **1.02x** | `[0, 0]` | `0` | `0` |
| P13 | 40% Heat / Regler ON | 300 | `6.80 -> 7.41` (**7.43 b**) | **+1.14 b** | `59739 -> 43652` | **1.75x** | `[90, 90]` | `27` | `300` |
| P14 | 40% Heat / Regler OFF | 288 | `6.31 -> 6.22` (**6.27 b**) | **-0.02 b** | `74882 -> 78536` | **1.01x** | `[0, 0]` | `0` | `0` |

## 4. Empirical Graphs: Performance Timeline & Full W(8) / W(3) Weights

![Round 20 Performance & Weight Envelope Timeline](figures/fig_card1_r20_lr0p055_l2_1920_mom0p85_cl90_thermal_slicing.png)

**Weight Coverage:** All **84 `W(8)`** (`7x6` MSB + `7x6` LSB) and **96 `W(3)`** (`8x6` MSB + `8x6` LSB) individual weights plotted across all pairs.

![Round 20 All W(8) and W(3) Weights](figures/fig_card1_r20_lr0p055_l2_1920_mom0p85_cl90_w8_w3_all_weights.png)
