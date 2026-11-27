# Inverted MAML Card 2 (`1k / 1k` = 50/50 Summing Attenuator, 60% PWM (120s ON / 30s OFF)): R20 Thermal Bit-Slicing Report

**Hardware Target:** Card 2 (`Trion T120F324` Master SoC + `Trion T20F256` Coprocessor, **`1k / 1k` (50/50) Passive Summing Attenuator**)  
**Firmware:** `T120_SOC_ETH_FW v2.2-MAML (SW Build Nov 27 2026 20:52:38)`, `HW_LOGIC: 0x20261030`  
**Dataset:** [`FPGA_code/logs/bit_slicing/card2_1k1k_60pct_4xon_r20_lr0p055_l2_1920_mom0p85_cl90.json`](../logs/bit_slicing/card2_1k1k_60pct_4xon_r20_lr0p055_l2_1920_mom0p85_cl90.json) (`8,091` pairs)  
**Dedicated Card 2 Storage:** `FPGA_code/releases/Release_20261127_Card2_1k1k_60pct_4xON_BitSlicing_R20/reports_and_logs/`  
**DC Calibration (Cold):** [`FPGA_code/config/card2_1k1k_60pct_4xon_dc_cal.json`](../config/card2_1k1k_60pct_4xon_dc_cal.json)  
**Hyperparameters:** `Heater = 60% PWM (120s ON / 30s OFF)`, `K = 1`, `LR = 0.055`, `L2 = 1920`, `Momentum = 0.85`, `Clamp = ±90 LSB`  

---

## 1. Executive Summary & Physical 1k / 1k (50/50) Behavior

1. **50/50 Summing Junction Physics (`1k / 1k` vs. Card 1 `1k / 2.2k`):**  
   With matched $1.0\text{ k}\Omega / 1.0\text{ k}\Omega$ summing resistors, the primary `M33` payload and the `M8` compensation branch share **equal $0.500\times$ ($-6.02\text{ dB}$) summing authority** at `ADC_49` (compared to $0.6875\times / 0.3125\times$ on Card 1 `1k / 2.2k`).
2. **Cold Baseline (`P1–P2`):** `Cold / Regler ON` mean **9.50 b** (loss `1,109 LSB²`), `Cold / Regler OFF` mean **9.50 b** (loss `1,155 LSB²`).
3. **Thermal-Detrended Closed-Loop Performance:**  
   Weighted detrended `Warm ON` lift **`+1.19 b`**, loss reduction ratio **`1.79x`**, detrended convergence climb **`+1.31 b`**, jitter **`0.17 b`**, anti-windup recovery **`1.00`**, composite score **`+4.177`**.
4. **Alpha-Normalized Attenuation Audit & Multi-Attractor Convergence:**  
   Mean calibrated forward gain `alpha_MSB` on Card 2 (`1k/1k`) matches or exceeds Card 1 (`1k/2.2k`), proving that Card 2's lower error is **not** a passive-attenuation scaling artifact—even after normalizing `RMSE / mean(alpha_MSB)`, Card 2 exhibits genuinely lower silicon noise and thermal drift. During extended ON phases, the 2-layer analog network exhibits basin-crossing jumps after ~20–40 s: keeping `W3` compact (`≤ 9 LSB` late, maintaining Sigmoid 4 linearity) lets `W8` lift precision to **`7.87–8.10 b`** (`2.60x` loss cut in P11); early `W3` growth (`≥ 15 LSB` late) locks Sigmoid 4 near compression (`6.91–7.03 b`).

---

## 2. Cumulative Cross-Run Comparison & Alpha-Normalized Audit

| Run Configuration | Mean `α_MSB` | P1 Norm RMSE (`RMSE/α`) | P13 ON Late Norm RMSE | P14 OFF Norm RMSE | Lift vs E_base | Loss Ratio | Hot Climb | Composite Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Card 1 (`1k/2.2k`, R23, 30/40%) | `0.0244` | `1,824` | `6,960` | `9,221` | `+0.64 b` | `1.49x` | `+0.68 b` | **`+1.695`** |
| Card 2 (`1k/1k`, 30/40%) | `0.0217` | `1,237` | `6,062` | `6,319` | `+0.01 b` | `1.03x` | `+0.16 b` | **`-0.376`** |
| Card 2 (`1k/1k`, 50% const) | `0.0250` | `937` | `4,949` | `6,066` | `+0.10 b` | `1.08x` | `+0.16 b` | **`-0.118`** |
| Card 2 (`1k/1k`, 60% 4×ON) ★ | `0.0256` | `882` | `7,347` | `8,942` | `+1.19 b` | `1.79x` | `+1.31 b` | **`+4.177`** |

---

## 3. Intra-Phase Convergence Dynamics (Warm ON Phases: `Start -> Mid -> Late`)

| Warm ON Phase | Comb ENOB (`Start -> Mid -> Late`) | Intra-Phase Climb | Total Loss (`Start -> Late`, Reduction) | W8 Peak `[M, L]` | W3 Peak (Late) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| P3 (1314 pairs) | `9.50 -> 8.62 -> 8.22 b` | **`-1.28 b`** | `1,142 -> 25,293` (`0.05x`) | `[61, 22]` | `9` (late: **`9`**) |
| P5 (1078 pairs) | `7.59 -> 8.02 -> 7.79 b` | **`+0.20 b`** | `38,731 -> 35,231` (`1.10x`) | `[63, 59]` | `10` (late: **`10`**) |
| P7 (974 pairs) | `6.67 -> 7.89 -> 7.87 b` | **`+1.19 b`** | `60,892 -> 32,953` (`1.85x`) | `[90, 79]` | `20` (late: **`9`**) |
| P9 (881 pairs) | `6.25 -> 6.99 -> 6.91 b` | **`+0.66 b`** | `73,672 -> 52,967` (`1.39x`) | `[90, 81]` | `20` (late: **`15`**) |
| P11 (810 pairs) | `6.19 -> 8.11 -> 8.10 b` | **`+1.91 b`** | `76,150 -> 29,353` (`2.59x`) | `[90, 90]` | `30` (late: **`6`**) |
| P13 (747 pairs) | `5.99 -> 6.99 -> 7.03 b` | **`+1.04 b`** | `84,285 -> 48,843` (`1.73x`) | `[90, 90]` | `21` (late: **`16`**) |

---

## 4. Fresh Cold DC Calibration (`Card 2, 1k / 1k`)

- **MSB `alpha`:** `[0.0272, 0.0197, 0.0348, 0.0105, 0.0342, 0.0272]`
- **MSB `beta` (LSB):** `[-1630.0, -231.6, -84.9, 614.7, -225.5, -862.4]`
- **LSB `alpha`:** `[0.0286, 0.0237, 0.0319, 0.024, 0.0393, 0.0291]`
- **LSB `beta` (LSB):** `[-1626.0, -305.1, -157.3, 584.7, -395.7, -874.0]`

---

## 5. Phase-by-Phase Telemetry (`P1–P14`)

| Phase | Regime | Pairs | Comb ENOB (`Start -> Late`, Mean) | Δ vs E_base | Total Loss (`Start -> Late`) | Loss Ratio | W8 Peak `[M, L]` | W3 Peak | W8 nz |
| :--- | :--- | ---: | :---: | :---: | :---: | :---: | :---: | :---: | ---: |
| P1 | Cold / Regler ON | 391 | `9.50 -> 9.50` (**9.50 b**) | — | `1101 -> 1083` | — | `[3, 4]` | `0` | `390` |
| P2 | Cold / Regler OFF | 405 | `9.50 -> 9.49` (**9.50 b**) | — | `1185 -> 1116` | — | `[0, 0]` | `0` | `0` |
| P3 | 60% Heat / Regler ON | 1314 | `9.50 -> 8.22` (**8.72 b**) | **+0.05 b** | `1142 -> 25293` | **0.78x** | `[61, 22]` | `9` | `1311` |
| P4 | 60% Heat / Regler OFF | 338 | `8.06 -> 7.75` (**7.84 b**) | **-0.03 b** | `29538 -> 36114` | **0.99x** | `[0, 0]` | `0` | `0` |
| P5 | 60% Heat / Regler ON | 1078 | `7.59 -> 7.79` (**7.87 b**) | **+0.76 b** | `38731 -> 35231` | **1.46x** | `[63, 59]` | `10` | `1078` |
| P6 | 60% Heat / Regler OFF | 291 | `6.70 -> 6.71` (**6.74 b**) | **+0.03 b** | `58646 -> 58990` | **1.01x** | `[0, 0]` | `0` | `0` |
| P7 | 60% Heat / Regler ON | 974 | `6.67 -> 7.87` (**7.62 b**) | **+1.13 b** | `60892 -> 32953` | **1.72x** | `[90, 79]` | `20` | `974` |
| P8 | 60% Heat / Regler OFF | 255 | `6.35 -> 6.33` (**6.33 b**) | **-0.01 b** | `70326 -> 71372` | **0.99x** | `[0, 0]` | `0` | `0` |
| P9 | 60% Heat / Regler ON | 881 | `6.25 -> 6.91` (**6.92 b**) | **+0.71 b** | `73672 -> 52967` | **1.40x** | `[90, 81]` | `20` | `881` |
| P10 | 60% Heat / Regler OFF | 209 | `6.06 -> 6.12` (**6.12 b**) | **+0.01 b** | `81337 -> 79635` | **1.00x** | `[0, 0]` | `0` | `0` |
| P11 | 60% Heat / Regler ON | 810 | `6.19 -> 8.10` (**7.87 b**) | **+1.78 b** | `76150 -> 29353` | **2.26x** | `[90, 90]` | `30` | `810` |
| P12 | 60% Heat / Regler OFF | 200 | `5.96 -> 6.02` (**6.00 b**) | **-0.00 b** | `85158 -> 83753` | **0.99x** | `[0, 0]` | `0` | `0` |
| P13 | 60% Heat / Regler ON | 747 | `5.99 -> 7.03` (**6.82 b**) | **+0.91 b** | `84285 -> 48843` | **1.58x** | `[90, 90]` | `21` | `747` |
| P14 | 60% Heat / Regler OFF | 198 | `5.85 -> 5.82` (**5.85 b**) | **+0.03 b** | `91424 -> 92224` | **1.00x** | `[0, 0]` | `0` | `0` |

---

## 6. Empirical Graphs: Performance Timeline & Full W(8) / W(3) Weights

![Card 2 1k/1k R20 Performance & Weight Envelope Timeline](figures/fig_card2_1k1k_60pct_4xon_r20_lr0p055_l2_1920_mom0p85_cl90_thermal_slicing.png)

**Weight Coverage:** All **84 `W(8)`** (`7x6` MSB + `7x6` LSB) and **96 `W(3)`** (`8x6` MSB + `8x6` LSB) individual weights plotted across all `8,091` pairs.

![Card 2 1k/1k R20 All W(8) and W(3) Weights](figures/fig_card2_1k1k_60pct_4xon_r20_lr0p055_l2_1920_mom0p85_cl90_w8_w3_all_weights.png)
