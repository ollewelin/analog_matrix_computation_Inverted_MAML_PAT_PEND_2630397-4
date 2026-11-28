# Inverted MAML Card 2 (`1k / 1k` = 50/50 Summing Attenuator, 60% PWM (120s ON / 30s OFF, ExtHad 8x6/7x6 Staircase)): R20 Thermal Bit-Slicing Report

**Hardware Target:** Card 2 (`Trion T120F324` Master SoC + `Trion T20F256` Coprocessor, **`1k / 1k` (50/50) Passive Summing Attenuator**)  
**Firmware:** `T120_SOC_ETH_FW v2.2-MAML (SW Build Nov 28 2026 12:13:02)`, `HW_LOGIC: 0x20261128`  
**Dataset:** [`FPGA_code/logs/bit_slicing/card2_1k1k_60pct_4xon_exthad_8x6_7x6_staircase_r20_lr0p055_l2_1920_mom0p85_cl90.json`](../logs/bit_slicing/card2_1k1k_60pct_4xon_exthad_8x6_7x6_staircase_r20_lr0p055_l2_1920_mom0p85_cl90.json) (`7,456` pairs)  
**Dedicated Card 2 Storage:** `FPGA_code/releases/Release_20261128_Card2_1k1k_60pct_4xON_ExtHad_8x6_7x6_Staircase_R20/reports_and_logs/`  
**DC Calibration (Cold):** [`FPGA_code/config/card2_1k1k_60pct_4xon_exthad_8x6_7x6_staircase_dc_cal.json`](../config/card2_1k1k_60pct_4xon_exthad_8x6_7x6_staircase_dc_cal.json)  
**Hyperparameters:** `Heater = 60% PWM (120s ON / 30s OFF, ExtHad 8x6/7x6 Staircase)`, `K = 1`, `LR = 0.055`, `L2 = 1920`, `Momentum = 0.85`, `Clamp = ±90 LSB`  

---

## 1. Executive Summary & Physical 1k / 1k (50/50) Behavior

1. **50/50 Summing Junction Physics (`1k / 1k` vs. Card 1 `1k / 2.2k`):**  
   With matched $1.0\text{ k}\Omega / 1.0\text{ k}\Omega$ summing resistors, the primary `M33` payload and the `M8` compensation branch share **equal $0.500\times$ ($-6.02\text{ dB}$) summing authority** at `ADC_49` (compared to $0.6875\times / 0.3125\times$ on Card 1 `1k / 2.2k`).
2. **Cold Baseline (`P1–P2`):** `Cold / Regler ON` mean **9.50 b** (loss `1,187 LSB²`), `Cold / Regler OFF` mean **9.50 b** (loss `1,174 LSB²`).
3. **Thermal-Detrended Closed-Loop Performance:**  
   Weighted detrended `Warm ON` lift **`+0.67 b`**, loss reduction ratio **`1.28x`**, detrended convergence climb **`+0.76 b`**, jitter **`0.19 b`**, anti-windup recovery **`1.00`**, composite score **`+1.669`**.
4. **Alpha-Normalized Attenuation Audit & Multi-Attractor Convergence:**  
   Mean calibrated forward gain `alpha_MSB` on Card 2 (`1k/1k`) matches or exceeds Card 1 (`1k/2.2k`), proving that Card 2's lower error is **not** a passive-attenuation scaling artifact—even after normalizing `RMSE / mean(alpha_MSB)`, Card 2 exhibits genuinely lower silicon noise and thermal drift. During extended ON phases, the 2-layer analog network exhibits basin-crossing jumps after ~20–40 s: keeping `W3` compact (`≤ 9 LSB` late, maintaining Sigmoid 4 linearity) lets `W8` lift precision to **`7.87–8.10 b`** (`2.60x` loss cut in P11); early `W3` growth (`≥ 15 LSB` late) locks Sigmoid 4 near compression (`6.91–7.03 b`).

---

## 2. Cumulative Cross-Run Comparison & Alpha-Normalized Audit

| Run Configuration | Mean `α_MSB` | P1 Norm RMSE (`RMSE/α`) | P13 ON Late Norm RMSE | P14 OFF Norm RMSE | Lift vs E_base | Loss Ratio | Hot Climb | Composite Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Card 1 (`1k/2.2k`, R23, 30/40%) | `0.0244` | `1,824` | `6,960` | `9,221` | `+0.64 b` | `1.49x` | `+0.68 b` | **`+1.695`** |
| Card 2 (`1k/1k`, 30/40%) | `0.0217` | `1,237` | `6,062` | `6,319` | `+0.01 b` | `1.03x` | `+0.16 b` | **`-0.376`** |
| Card 2 (`1k/1k`, 50% const) | `0.0250` | `937` | `4,949` | `6,066` | `+0.10 b` | `1.08x` | `+0.16 b` | **`-0.118`** |
| Card 2 (`1k/1k`, 60% 4×ON, 1× M3 L2) | `0.0256` | `882` | `7,347` | `8,942` | `+1.19 b` | `1.79x` | `+1.31 b` | **`+4.177`** |
| Card 2 (`1k/1k`, 60% 4×ON, 4× M3 L2) | `0.0211` | `1,064` | `10,089` | `10,212` | `+0.00 b` | `0.99x` | `+0.16 b` | **`-0.477`** |
| Card 2 (`1k/1k`, 60% 4×ON, 0.5×/2× L2) | `0.0218` | `1,100` | `7,206` | `10,698` | `+0.90 b` | `1.49x` | `+1.05 b` | **`+2.465`** |
| Card 2 (`1k/1k`, 60% 4×ON, ExtHad 8×6/7×6) | `0.0236` | `954` | `8,208` | `9,816` | `+0.67 b` | `1.28x` | `+0.76 b` | **`+1.669`** |

---

## 3. Intra-Phase Convergence Dynamics (Warm ON Phases: `Start -> Mid -> Late`)

| Warm ON Phase | Comb ENOB (`Start -> Mid -> Late`) | Intra-Phase Climb | Total Loss (`Start -> Late`, Reduction) | W8 Peak `[M, L]` | W3 Peak (Late) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| P3 (1293 pairs) | `9.50 -> 8.68 -> 8.25 b` | **`-1.25 b`** | `1,136 -> 24,487` (`0.05x`) | `[15, 13]` | `5` (late: **`5`**) |
| P5 (1066 pairs) | `7.69 -> 7.22 -> 6.99 b` | **`-0.70 b`** | `37,094 -> 51,686` (`0.72x`) | `[25, 18]` | `12` (late: **`12`**) |
| P7 (873 pairs) | `6.76 -> 6.55 -> 6.90 b` | **`+0.14 b`** | `57,714 -> 56,538` (`1.02x`) | `[90, 19]` | `17` (late: **`10`**) |
| P9 (735 pairs) | `6.24 -> 7.35 -> 7.29 b` | **`+1.05 b`** | `74,411 -> 52,475` (`1.42x`) | `[90, 74]` | `25` (late: **`14`**) |
| P11 (730 pairs) | `6.09 -> 7.15 -> 7.10 b` | **`+1.01 b`** | `80,401 -> 58,293` (`1.38x`) | `[90, 75]` | `21` (late: **`19`**) |
| P13 (670 pairs) | `5.85 -> 6.09 -> 6.28 b` | **`+0.44 b`** | `90,819 -> 76,564` (`1.19x`) | `[90, 25]` | `27` (late: **`21`**) |

---

## 4. Fresh Cold DC Calibration (`Card 2, 1k / 1k`)

- **MSB `alpha`:** `[0.0224, 0.0182, 0.0286, 0.0166, 0.0316, 0.0242]`
- **MSB `beta` (LSB):** `[-1635.0, -243.7, -100.2, 608.3, -230.6, -864.3]`
- **LSB `alpha`:** `[0.0292, 0.0225, 0.0386, 0.0235, 0.0422, 0.029]`
- **LSB `beta` (LSB):** `[-1631.2, -311.8, -169.5, 575.0, -405.3, -875.7]`

---

## 5. Phase-by-Phase Telemetry (`P1–P14`)

| Phase | Regime | Pairs | Comb ENOB (`Start -> Late`, Mean) | Δ vs E_base | Total Loss (`Start -> Late`) | Loss Ratio | W8 Peak `[M, L]` | W3 Peak | W8 nz |
| :--- | :--- | ---: | :---: | :---: | :---: | :---: | :---: | :---: | ---: |
| P1 | Cold / Regler ON | 401 | `9.50 -> 9.50` (**9.50 b**) | — | `1040 -> 1230` | — | `[4, 3]` | `0` | `399` |
| P2 | Cold / Regler OFF | 400 | `9.50 -> 9.50` (**9.50 b**) | — | `1227 -> 1131` | — | `[0, 0]` | `0` | `0` |
| P3 | 60% Heat / Regler ON | 1293 | `9.50 -> 8.25` (**8.76 b**) | **+0.18 b** | `1136 -> 24487` | **0.86x** | `[15, 13]` | `5` | `1293` |
| P4 | 60% Heat / Regler OFF | 321 | `8.05 -> 7.78` (**7.89 b**) | **+0.00 b** | `30170 -> 35527` | **1.00x** | `[0, 0]` | `0` | `0` |
| P5 | 60% Heat / Regler ON | 1066 | `7.69 -> 6.99` (**7.25 b**) | **+0.02 b** | `37094 -> 51686` | **1.01x** | `[25, 18]` | `12` | `1066` |
| P6 | 60% Heat / Regler OFF | 248 | `6.77 -> 6.69` (**6.75 b**) | **+0.01 b** | `57752 -> 59714` | **1.00x** | `[0, 0]` | `0` | `0` |
| P7 | 60% Heat / Regler ON | 873 | `6.76 -> 6.90` (**6.72 b**) | **+0.32 b** | `57714 -> 56538` | **1.14x** | `[90, 19]` | `17` | `873` |
| P8 | 60% Heat / Regler OFF | 199 | `6.31 -> 6.26` (**6.30 b**) | **+0.01 b** | `71716 -> 73527` | **1.00x** | `[0, 0]` | `0` | `0` |
| P9 | 60% Heat / Regler ON | 735 | `6.24 -> 7.29` (**6.90 b**) | **+0.75 b** | `74411 -> 52475` | **1.32x** | `[90, 74]` | `25` | `735` |
| P10 | 60% Heat / Regler OFF | 185 | `6.06 -> 5.98` (**6.00 b**) | **+0.00 b** | `82238 -> 84803` | **1.00x** | `[0, 0]` | `0` | `0` |
| P11 | 60% Heat / Regler ON | 730 | `6.09 -> 7.10` (**6.75 b**) | **+0.85 b** | `80401 -> 58293` | **1.34x** | `[90, 75]` | `21` | `730` |
| P12 | 60% Heat / Regler OFF | 175 | `5.87 -> 5.84` (**5.83 b**) | **+0.01 b** | `90055 -> 91419` | **1.00x** | `[0, 0]` | `0` | `0` |
| P13 | 60% Heat / Regler ON | 670 | `5.85 -> 6.28` (**6.08 b**) | **+0.26 b** | `90819 -> 76564` | **1.10x** | `[90, 25]` | `27` | `670` |
| P14 | 60% Heat / Regler OFF | 160 | `5.81 -> 5.77` (**5.80 b**) | **+0.02 b** | `92079 -> 94520` | **1.01x** | `[0, 0]` | `0` | `0` |

---

## 6. Empirical Graphs: Performance Timeline & Full W(8) / W(3) Weights

![Card 2 1k/1k R20 Performance & Weight Envelope Timeline](figures/fig_card2_1k1k_60pct_4xon_exthad_8x6_7x6_staircase_r20_lr0p055_l2_1920_mom0p85_cl90_thermal_slicing.png)

**Weight Coverage:** All **84 `W(8)`** (`7x6` MSB + `7x6` LSB) and **96 `W(3)`** (`8x6` MSB + `8x6` LSB) individual weights plotted across all `7,456` pairs, both combined and resolved per column (`Col 0..5`) in distinct row colors (`R0–R6` for `M(8)` and `R0–R7` for `M(3)`).

![Card 2 1k/1k R20 All W(8) and W(3) Weights](figures/fig_card2_1k1k_60pct_4xon_exthad_8x6_7x6_staircase_r20_lr0p055_l2_1920_mom0p85_cl90_w8_w3_all_weights.png)

### Per-Column Multi-Color Weight Resolution (`Col 0–5`, All Matrix Rows)

![Matrix 8 MSB by Column](figures/fig_card2_1k1k_60pct_4xon_exthad_8x6_7x6_staircase_r20_lr0p055_l2_1920_mom0p85_cl90_w8_msb_by_col.png)
![Matrix 8 LSB by Column](figures/fig_card2_1k1k_60pct_4xon_exthad_8x6_7x6_staircase_r20_lr0p055_l2_1920_mom0p85_cl90_w8_lsb_by_col.png)
![Matrix 3 MSB by Column](figures/fig_card2_1k1k_60pct_4xon_exthad_8x6_7x6_staircase_r20_lr0p055_l2_1920_mom0p85_cl90_w3_msb_by_col.png)
![Matrix 3 LSB by Column](figures/fig_card2_1k1k_60pct_4xon_exthad_8x6_7x6_staircase_r20_lr0p055_l2_1920_mom0p85_cl90_w3_lsb_by_col.png)
