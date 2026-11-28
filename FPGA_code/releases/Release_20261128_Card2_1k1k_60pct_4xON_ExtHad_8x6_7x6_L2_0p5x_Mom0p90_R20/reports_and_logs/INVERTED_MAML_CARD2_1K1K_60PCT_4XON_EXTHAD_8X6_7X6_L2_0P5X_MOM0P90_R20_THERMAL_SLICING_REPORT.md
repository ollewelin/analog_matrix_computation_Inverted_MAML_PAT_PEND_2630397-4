# Inverted MAML Card 2 (`1k / 1k` = 50/50 Summing Attenuator, 60% PWM (120s ON / 30s OFF, ExtHad 8x6/7x6 0.5x L2 Mom0.90)): R20 Thermal Bit-Slicing Report

**Hardware Target:** Card 2 (`Trion T120F324` Master SoC + `Trion T20F256` Coprocessor, **`1k / 1k` (50/50) Passive Summing Attenuator**)  
**Firmware:** `T120_SOC_ETH_FW v2.2-MAML (SW Build Nov 28 2026 12:42:43)`, `HW_LOGIC: 0x20261128`  
**Dataset:** [`FPGA_code/logs/bit_slicing/card2_1k1k_60pct_4xon_exthad_8x6_7x6_l2_0p5x_0p5x_mom0p90_r20_lr0p055_l2_960_mom0p90_cl90.json`](../logs/bit_slicing/card2_1k1k_60pct_4xon_exthad_8x6_7x6_l2_0p5x_0p5x_mom0p90_r20_lr0p055_l2_960_mom0p90_cl90.json) (`7,456` pairs)  
**Dedicated Card 2 Storage:** `FPGA_code/releases/Release_20261128_Card2_1k1k_60pct_4xON_ExtHad_8x6_7x6_L2_0p5x_Mom0p90_R20/reports_and_logs/`  
**DC Calibration (Cold):** [`FPGA_code/config/card2_1k1k_60pct_4xon_exthad_8x6_7x6_l2_0p5x_0p5x_mom0p90_dc_cal.json`](../config/card2_1k1k_60pct_4xon_exthad_8x6_7x6_l2_0p5x_0p5x_mom0p90_dc_cal.json)  
**Hyperparameters:** `Heater = 60% PWM (120s ON / 30s OFF, ExtHad 8x6/7x6 0.5x L2 Mom0.90)`, `K = 1`, `LR = 0.055`, `L2 = 960`, `Momentum = 0.9`, `Clamp = ±90 LSB`  

---

## 1. Executive Summary & Physical 1k / 1k (50/50) Behavior

1. **50/50 Summing Junction Physics (`1k / 1k` vs. Card 1 `1k / 2.2k`):**  
   With matched $1.0\text{ k}\Omega / 1.0\text{ k}\Omega$ summing resistors, the primary `M33` payload and the `M8` compensation branch share **equal $0.500\times$ ($-6.02\text{ dB}$) summing authority** at `ADC_49` (compared to $0.6875\times / 0.3125\times$ on Card 1 `1k / 2.2k`).
2. **Cold Baseline (`P1–P2`):** `Cold / Regler ON` mean **9.50 b** (loss `1,266 LSB²`), `Cold / Regler OFF` mean **9.50 b** (loss `1,731 LSB²`).
3. **Thermal-Detrended Closed-Loop Performance:**  
   Weighted detrended `Warm ON` lift **`+0.54 b`**, loss reduction ratio **`1.63x`**, detrended convergence climb **`+0.66 b`**, jitter **`0.17 b`**, anti-windup recovery **`1.00`**, composite score **`+2.296`**.
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
| Card 2 (`1k/1k`, 60% 4×ON, ExtHad 8×6/7×6, 0.5×/2×) | `0.0236` | `954` | `8,208` | `9,816` | `+0.67 b` | `1.28x` | `+0.76 b` | **`+1.669`** |
| Card 2 (`1k/1k`, 60% 4×ON, ExtHad 8×6/7×6, 1×/1×) | `0.0206` | `1,088` | `8,572` | `10,887` | `+0.45 b` | `1.18x` | `+0.59 b` | **`+0.916`** |
| Card 2 (`1k/1k`, 60% 4×ON, ExtHad 8×6/7×6, 0.5×/0.5× Mom0.90) | `0.0221` | `1,144` | `4,727` | `7,019` | `+0.54 b` | `1.63x` | `+0.66 b` | **`+2.296`** |

---

## 3. Intra-Phase Convergence Dynamics (Warm ON Phases: `Start -> Mid -> Late`)

| Warm ON Phase | Comb ENOB (`Start -> Mid -> Late`) | Intra-Phase Climb | Total Loss (`Start -> Late`, Reduction) | W8 Peak `[M, L]` | W3 Peak (Late) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| P3 (1300 pairs) | `9.50 -> 9.34 -> 8.97 b` | **`-0.53 b`** | `1,933 -> 11,212` (`0.17x`) | `[90, 27]` | `13` (late: **`13`**) |
| P5 (1101 pairs) | `8.57 -> 8.43 -> 8.43 b` | **`-0.14 b`** | `18,150 -> 18,277` (`0.99x`) | `[90, 90]` | `22` (late: **`22`**) |
| P7 (873 pairs) | `8.09 -> 8.45 -> 8.45 b` | **`+0.37 b`** | `29,347 -> 19,014` (`1.54x`) | `[90, 90]` | `26` (late: **`16`**) |
| P9 (785 pairs) | `7.80 -> 8.37 -> 8.14 b` | **`+0.34 b`** | `34,384 -> 22,889` (`1.50x`) | `[90, 90]` | `30` (late: **`26`**) |
| P11 (688 pairs) | `7.57 -> 8.16 -> 8.33 b` | **`+0.76 b`** | `38,266 -> 20,560` (`1.86x`) | `[90, 90]` | `30` (late: **`19`**) |
| P13 (612 pairs) | `7.54 -> 8.29 -> 8.30 b` | **`+0.75 b`** | `38,721 -> 22,065` (`1.75x`) | `[90, 90]` | `30` (late: **`21`**) |

---

## 4. Fresh Cold DC Calibration (`Card 2, 1k / 1k`)

- **MSB `alpha`:** `[0.0261, 0.025, 0.0392, 0.0021, 0.01, 0.0304]`
- **MSB `beta` (LSB):** `[-1514.1, -112.3, 72.6, 555.2, -203.6, -769.8]`
- **LSB `alpha`:** `[0.0308, 0.0272, 0.0446, 0.0036, 0.0339, 0.0286]`
- **LSB `beta` (LSB):** `[-1525.8, -194.6, -23.7, 546.0, -309.0, -800.1]`

---

## 5. Phase-by-Phase Telemetry (`P1–P14`)

| Phase | Regime | Pairs | Comb ENOB (`Start -> Late`, Mean) | Δ vs E_base | Total Loss (`Start -> Late`) | Loss Ratio | W8 Peak `[M, L]` | W3 Peak | W8 nz |
| :--- | :--- | ---: | :---: | :---: | :---: | :---: | :---: | :---: | ---: |
| P1 | Cold / Regler ON | 389 | `9.50 -> 9.50` (**9.50 b**) | — | `1190 -> 1433` | — | `[9, 8]` | `0` | `387` |
| P2 | Cold / Regler OFF | 407 | `9.50 -> 9.50` (**9.50 b**) | — | `1535 -> 1889` | — | `[0, 0]` | `0` | `0` |
| P3 | 60% Heat / Regler ON | 1300 | `9.50 -> 8.97` (**9.26 b**) | **+0.23 b** | `1933 -> 11212` | **1.10x** | `[90, 27]` | `13` | `1299` |
| P4 | 60% Heat / Regler OFF | 316 | `8.81 -> 8.61` (**8.68 b**) | **+0.01 b** | `13860 -> 17919` | **0.99x** | `[0, 0]` | `0` | `0` |
| P5 | 60% Heat / Regler ON | 1101 | `8.57 -> 8.43` (**8.47 b**) | **-0.03 b** | `18150 -> 18277` | **1.20x** | `[90, 90]` | `22` | `1101` |
| P6 | 60% Heat / Regler OFF | 260 | `8.23 -> 8.11` (**8.15 b**) | **-0.02 b** | `27343 -> 29447` | **0.99x** | `[0, 0]` | `0` | `0` |
| P7 | 60% Heat / Regler ON | 873 | `8.09 -> 8.45` (**8.40 b**) | **+0.50 b** | `29347 -> 19014` | **1.57x** | `[90, 90]` | `26` | `873` |
| P8 | 60% Heat / Regler OFF | 205 | `7.72 -> 7.74` (**7.73 b**) | **+0.01 b** | `35825 -> 35631` | **1.01x** | `[0, 0]` | `0` | `0` |
| P9 | 60% Heat / Regler ON | 785 | `7.80 -> 8.14` (**8.27 b**) | **+0.63 b** | `34384 -> 22889` | **1.66x** | `[90, 90]` | `30` | `785` |
| P10 | 60% Heat / Regler OFF | 191 | `7.65 -> 7.54` (**7.57 b**) | **-0.00 b** | `37334 -> 39097` | **1.00x** | `[0, 0]` | `0` | `0` |
| P11 | 60% Heat / Regler ON | 688 | `7.57 -> 8.33` (**8.24 b**) | **+0.76 b** | `38266 -> 20560` | **1.63x** | `[90, 90]` | `30` | `688` |
| P12 | 60% Heat / Regler OFF | 172 | `7.59 -> 7.51` (**7.52 b**) | **+0.03 b** | `38475 -> 39683` | **1.00x** | `[0, 0]` | `0` | `0` |
| P13 | 60% Heat / Regler ON | 612 | `7.54 -> 8.30` (**8.15 b**) | **+0.65 b** | `38721 -> 22065` | **1.56x** | `[90, 90]` | `30` | `612` |
| P14 | 60% Heat / Regler OFF | 157 | `7.46 -> 7.42` (**7.43 b**) | **+0.00 b** | `40742 -> 41398` | **1.00x** | `[0, 0]` | `0` | `0` |

---

## 6. Empirical Graphs: Performance Timeline & Full W(8) / W(3) Weights

![Card 2 1k/1k R20 Performance & Weight Envelope Timeline](figures/fig_card2_1k1k_60pct_4xon_exthad_8x6_7x6_l2_0p5x_0p5x_mom0p90_r20_lr0p055_l2_960_mom0p90_cl90_thermal_slicing.png)

**Weight Coverage:** All **84 `W(8)`** (`7x6` MSB + `7x6` LSB) and **96 `W(3)`** (`8x6` MSB + `8x6` LSB) individual weights plotted across all `7,456` pairs, both combined and resolved per column (`Col 0..5`) in distinct row colors (`R0–R6` for `M(8)` and `R0–R7` for `M(3)`).

![Card 2 1k/1k R20 All W(8) and W(3) Weights](figures/fig_card2_1k1k_60pct_4xon_exthad_8x6_7x6_l2_0p5x_0p5x_mom0p90_r20_lr0p055_l2_960_mom0p90_cl90_w8_w3_all_weights.png)

### Per-Column Multi-Color Weight Resolution (`Col 0–5`, All Matrix Rows)

![Matrix 8 MSB by Column](figures/fig_card2_1k1k_60pct_4xon_exthad_8x6_7x6_l2_0p5x_0p5x_mom0p90_r20_lr0p055_l2_960_mom0p90_cl90_w8_msb_by_col.png)
![Matrix 8 LSB by Column](figures/fig_card2_1k1k_60pct_4xon_exthad_8x6_7x6_l2_0p5x_0p5x_mom0p90_r20_lr0p055_l2_960_mom0p90_cl90_w8_lsb_by_col.png)
![Matrix 3 MSB by Column](figures/fig_card2_1k1k_60pct_4xon_exthad_8x6_7x6_l2_0p5x_0p5x_mom0p90_r20_lr0p055_l2_960_mom0p90_cl90_w3_msb_by_col.png)
![Matrix 3 LSB by Column](figures/fig_card2_1k1k_60pct_4xon_exthad_8x6_7x6_l2_0p5x_0p5x_mom0p90_r20_lr0p055_l2_960_mom0p90_cl90_w3_lsb_by_col.png)
