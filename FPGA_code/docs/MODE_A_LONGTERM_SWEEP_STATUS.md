# Inverted MAML Mode A: Long-Term Batch & Learning Rate Statistical Sweep

**Last Updated:** 2026-10-26 16:17:09  
**Target Platform:** Efinix Trion T120F324 Master SoC (`192.168.1.50:5000`)  
**Operating Mode:** Mode A (Active 2-Layer Triad via Sigmoid 10, Jumper Mode 3)  
**Hardware Summing Attenuator:** $1\text{ k}\Omega / 3.9\text{ k}\Omega$ ($20.4\%$ authority, baseline before $15\text{ k}\Omega$ rework)  
**Completed Conditions:** 26 experiments  

---

## 1. Executive Statistical Ranking (Convergence vs Flat vs Divergent)

| Rank | Batch Size $K$ | LR Scale | Epochs | Slope ($\beta_1$) | $\Delta Q_1 \to Q_4$ | Q4 ENOB | Peak ENOB | Statistical Verdict |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| 1 | K=4 | 0.05x | 200 | `-23.96` | **-18.0%** | 4.75 b | 5.15 b | CONVERGING (STATISTICAL DESCENT) |
| 2 | K=20 | 0.03x | 200 | `-23.35` | **-16.4%** | 4.73 b | 5.17 b | CONVERGING (STATISTICAL DESCENT) |
| 3 | K=4 | 0.20x | 200 | `-49.51` | **-16.3%** | 4.77 b | 5.19 b | CONVERGING (STATISTICAL DESCENT) |
| 4 | K=25 | 0.05x | 200 | `-18.87` | **-13.8%** | 4.73 b | 5.21 b | CONVERGING (STATISTICAL DESCENT) |
| 5 | K=16 | 0.08x | 200 | `-13.25` | **-11.7%** | 4.72 b | 5.14 b | CONVERGING (STATISTICAL DESCENT) |
| 6 | K=12 | 0.10x | 200 | `-15.38` | **-10.8%** | 4.74 b | 5.34 b | CONVERGING (STATISTICAL DESCENT) |
| 7 | K=20 | 0.10x | 200 | `-14.51` | **-10.8%** | 4.73 b | 5.33 b | CONVERGING (STATISTICAL DESCENT) |
| 8 | K=8 | 0.03x | 200 | `-14.50` | **-10.8%** | 4.73 b | 5.19 b | CONVERGING (STATISTICAL DESCENT) |
| 9 | K=12 | 0.05x | 200 | `-8.72` | **-9.1%** | 4.71 b | 5.21 b | CONVERGING (STATISTICAL DESCENT) |
| 10 | K=20 | 0.08x | 200 | `-12.73` | **-8.7%** | 4.75 b | 5.22 b | CONVERGING (STATISTICAL DESCENT) |
| 11 | K=20 | 0.05x | 200 | `-10.90` | **-7.9%** | 4.71 b | 5.42 b | CONVERGING (STATISTICAL DESCENT) |
| 12 | K=16 | 0.05x | 200 | `-9.09` | **-5.9%** | 4.76 b | 5.24 b | CONVERGING (STATISTICAL DESCENT) |
| 13 | K=8 | 0.08x | 200 | `-7.94` | **-5.4%** | 4.72 b | 5.49 b | CONVERGING (STATISTICAL DESCENT) |
| 14 | K=8 | 0.10x | 200 | `-3.27` | **-3.4%** | 4.73 b | 5.40 b | STATISTICALLY FLAT (PURE NOISE FLOOR) |
| 15 | K=12 | 0.05x | 200 | `-4.17` | **-2.8%** | 4.79 b | 5.30 b | STATISTICALLY FLAT (PURE NOISE FLOOR) |
| 16 | K=4 | 0.10x | 200 | `-3.78` | **-1.6%** | 4.67 b | 5.24 b | STATISTICALLY FLAT (PURE NOISE FLOOR) |
| 17 | K=8 | 0.05x | 200 | `-0.99` | **-1.5%** | 4.73 b | 5.21 b | STATISTICALLY FLAT (PURE NOISE FLOOR) |
| 18 | K=25 | 0.08x | 200 | `-2.74` | **-1.2%** | 4.74 b | 5.41 b | STATISTICALLY FLAT (PURE NOISE FLOOR) |
| 19 | K=25 | 0.03x | 200 | `-0.70` | **-0.9%** | 4.70 b | 5.21 b | STATISTICALLY FLAT (PURE NOISE FLOOR) |
| 20 | K=12 | 0.08x | 200 | `+2.18` | **-0.3%** | 4.74 b | 5.19 b | STATISTICALLY FLAT (PURE NOISE FLOOR) |
| 21 | K=8 | 0.10x | 200 | `+1.99` | **+1.5%** | 4.80 b | 5.46 b | STATISTICALLY FLAT (PURE NOISE FLOOR) |
| 22 | K=12 | 0.10x | 200 | `+0.93` | **+2.5%** | 4.73 b | 5.17 b | STATISTICALLY FLAT (PURE NOISE FLOOR) |
| 23 | K=8 | 0.03x | 200 | `+4.87` | **+3.5%** | 4.77 b | 5.19 b | STATISTICALLY FLAT (PURE NOISE FLOOR) |
| 24 | K=8 | 0.08x | 200 | `+7.92` | **+5.7%** | 4.70 b | 5.25 b | DIVERGING / INSTABILITY |
| 25 | K=8 | 0.05x | 200 | `+7.97` | **+7.3%** | 4.79 b | 5.47 b | DIVERGING / INSTABILITY |
| 26 | K=12 | 0.08x | 200 | `+162.19` | **+117.7%** | 4.70 b | 5.39 b | DIVERGING / INSTABILITY |

---

## 2. Detailed Condition Summaries & Weight Topographies

### Condition: K=8, LR=0.05x (200 epochs)
- **Dataset File:** [`sweep_k8_lr05p_200ep.json`](../logs/mode_a_longterm_sweep/sweep_k8_lr05p_200ep.json)
- **Execution Time:** 897.3 s (15.0 min)
- **Statistical Verdict:** **DIVERGING / INSTABILITY**
- **Loss Trajectory Slope:** `+7.973 LSB^2/epoch` ($R^2 = 0.0124$)
- **Quartile 1 Mean Loss:** `16428.4 LSB^2` (4.87 bits) $\to$ **Quartile 4 Mean Loss:** `17631.7 LSB^2` (4.79 bits)
- **Net Long-Term Trend:** `+7.32%`
- **Final Weights:** M8 Diag = `[18, 22, 24, 21, 19, 28]`, M3 Diag = `[67, 67, 67, 66, 62, 75]` ($r_{M3} = 0.9966$)

### Condition: K=8, LR=0.08x (200 epochs)
- **Dataset File:** [`sweep_k8_lr08p_200ep.json`](../logs/mode_a_longterm_sweep/sweep_k8_lr08p_200ep.json)
- **Execution Time:** 888.7 s (14.8 min)
- **Statistical Verdict:** **DIVERGING / INSTABILITY**
- **Loss Trajectory Slope:** `+7.916 LSB^2/epoch` ($R^2 = 0.0099$)
- **Quartile 1 Mean Loss:** `18960.0 LSB^2` (4.75 bits) $\to$ **Quartile 4 Mean Loss:** `20041.1 LSB^2` (4.7 bits)
- **Net Long-Term Trend:** `+5.70%`
- **Final Weights:** M8 Diag = `[19, 34, 30, 39, 14, 46]`, M3 Diag = `[72, 80, 80, 78, 66, 80]` ($r_{M3} = 0.8844$)

### Condition: K=8, LR=0.10x (200 epochs)
- **Dataset File:** [`sweep_k8_lr10p_200ep.json`](../logs/mode_a_longterm_sweep/sweep_k8_lr10p_200ep.json)
- **Execution Time:** 888.5 s (14.8 min)
- **Statistical Verdict:** **STATISTICALLY FLAT (PURE NOISE FLOOR)**
- **Loss Trajectory Slope:** `+1.985 LSB^2/epoch` ($R^2 = 0.0006$)
- **Quartile 1 Mean Loss:** `17452.1 LSB^2` (4.81 bits) $\to$ **Quartile 4 Mean Loss:** `17710.2 LSB^2` (4.8 bits)
- **Net Long-Term Trend:** `+1.48%`
- **Final Weights:** M8 Diag = `[25, 20, 23, 19, 31, 34]`, M3 Diag = `[67, 63, 66, 65, 54, 72]` ($r_{M3} = 0.9932$)

### Condition: K=8, LR=0.03x (200 epochs)
- **Dataset File:** [`sweep_k8_lr03p_200ep.json`](../logs/mode_a_longterm_sweep/sweep_k8_lr03p_200ep.json)
- **Execution Time:** 856.5 s (14.3 min)
- **Statistical Verdict:** **STATISTICALLY FLAT (PURE NOISE FLOOR)**
- **Loss Trajectory Slope:** `+4.872 LSB^2/epoch` ($R^2 = 0.0047$)
- **Quartile 1 Mean Loss:** `17571.1 LSB^2` (4.8 bits) $\to$ **Quartile 4 Mean Loss:** `18181.7 LSB^2` (4.77 bits)
- **Net Long-Term Trend:** `+3.47%`
- **Final Weights:** M8 Diag = `[22, 25, 24, 24, 28, 26]`, M3 Diag = `[64, 62, 64, 64, 61, 63]` ($r_{M3} = 0.9995$)

### Condition: K=12, LR=0.05x (200 epochs)
- **Dataset File:** [`sweep_k12_lr05p_200ep.json`](../logs/mode_a_longterm_sweep/sweep_k12_lr05p_200ep.json)
- **Execution Time:** 1261.4 s (21.0 min)
- **Statistical Verdict:** **STATISTICALLY FLAT (PURE NOISE FLOOR)**
- **Loss Trajectory Slope:** `-4.168 LSB^2/epoch` ($R^2 = 0.0027$)
- **Quartile 1 Mean Loss:** `18825.2 LSB^2` (4.77 bits) $\to$ **Quartile 4 Mean Loss:** `18308.1 LSB^2` (4.79 bits)
- **Net Long-Term Trend:** `-2.75%`
- **Final Weights:** M8 Diag = `[27, 21, 25, 23, 22, 27]`, M3 Diag = `[65, 62, 66, 64, 57, 69]` ($r_{M3} = 0.9963$)

### Condition: K=12, LR=0.08x (200 epochs)
- **Dataset File:** [`sweep_k12_lr08p_200ep.json`](../logs/mode_a_longterm_sweep/sweep_k12_lr08p_200ep.json)
- **Execution Time:** 1243.3 s (20.7 min)
- **Statistical Verdict:** **DIVERGING / INSTABILITY**
- **Loss Trajectory Slope:** `+162.191 LSB^2/epoch` ($R^2 = 0.0158$)
- **Quartile 1 Mean Loss:** `18561.3 LSB^2` (4.78 bits) $\to$ **Quartile 4 Mean Loss:** `40397.9 LSB^2` (4.7 bits)
- **Net Long-Term Trend:** `+117.65%`
- **Final Weights:** M8 Diag = `[22, 25, 24, 18, 37, 27]`, M3 Diag = `[67, 58, 65, 63, 49, 71]` ($r_{M3} = 0.9891$)

### Condition: K=12, LR=0.10x (200 epochs)
- **Dataset File:** [`sweep_k12_lr10p_200ep.json`](../logs/mode_a_longterm_sweep/sweep_k12_lr10p_200ep.json)
- **Execution Time:** 1168.1 s (19.5 min)
- **Statistical Verdict:** **STATISTICALLY FLAT (PURE NOISE FLOOR)**
- **Loss Trajectory Slope:** `+0.931 LSB^2/epoch` ($R^2 = 0.0001$)
- **Quartile 1 Mean Loss:** `19199.6 LSB^2` (4.75 bits) $\to$ **Quartile 4 Mean Loss:** `19684.8 LSB^2` (4.73 bits)
- **Net Long-Term Trend:** `+2.53%`
- **Final Weights:** M8 Diag = `[18, 25, 23, 18, 33, 34]`, M3 Diag = `[64, 55, 62, 61, 51, 55]` ($r_{M3} = 0.9907$)

### Condition: K=8, LR=0.05x (200 epochs)
- **Dataset File:** [`true_batch_k8_lr05p_200ep.json`](../logs/mode_a_longterm_sweep/true_batch_k8_lr05p_200ep.json)
- **Execution Time:** 1166.6 s (19.4 min)
- **Statistical Verdict:** **STATISTICALLY FLAT (PURE NOISE FLOOR)**
- **Loss Trajectory Slope:** `-0.990 LSB^2/epoch` ($R^2 = 0.0001$)
- **Quartile 1 Mean Loss:** `19804.8 LSB^2` (4.72 bits) $\to$ **Quartile 4 Mean Loss:** `19507.7 LSB^2` (4.73 bits)
- **Net Long-Term Trend:** `-1.50%`
- **Final Weights:** M8 Diag = `[25, 25, 24, 25, 25, 23]`, M3 Diag = `[64, 63, 64, 64, 63, 62]` ($r_{M3} = 0.9997$)

### Condition: K=8, LR=0.08x (200 epochs)
- **Dataset File:** [`true_batch_k8_lr08p_200ep.json`](../logs/mode_a_longterm_sweep/true_batch_k8_lr08p_200ep.json)
- **Execution Time:** 1065.3 s (17.8 min)
- **Statistical Verdict:** **CONVERGING (STATISTICAL DESCENT)**
- **Loss Trajectory Slope:** `-7.936 LSB^2/epoch` ($R^2 = 0.0086$)
- **Quartile 1 Mean Loss:** `20966.7 LSB^2` (4.68 bits) $\to$ **Quartile 4 Mean Loss:** `19831.8 LSB^2` (4.72 bits)
- **Net Long-Term Trend:** `-5.41%`
- **Final Weights:** M8 Diag = `[26, 25, 24, 26, 23, 22]`, M3 Diag = `[64, 63, 64, 64, 63, 63]` ($r_{M3} = 0.9999$)

### Condition: K=8, LR=0.10x (200 epochs)
- **Dataset File:** [`true_batch_k8_lr10p_200ep.json`](../logs/mode_a_longterm_sweep/true_batch_k8_lr10p_200ep.json)
- **Execution Time:** 942.1 s (15.7 min)
- **Statistical Verdict:** **STATISTICALLY FLAT (PURE NOISE FLOOR)**
- **Loss Trajectory Slope:** `-3.265 LSB^2/epoch` ($R^2 = 0.0017$)
- **Quartile 1 Mean Loss:** `19989.3 LSB^2` (4.71 bits) $\to$ **Quartile 4 Mean Loss:** `19309.1 LSB^2` (4.73 bits)
- **Net Long-Term Trend:** `-3.40%`
- **Final Weights:** M8 Diag = `[24, 23, 24, 24, 29, 26]`, M3 Diag = `[64, 63, 63, 64, 63, 62]` ($r_{M3} = 0.9997$)

### Condition: K=8, LR=0.03x (200 epochs)
- **Dataset File:** [`true_batch_k8_lr03p_200ep.json`](../logs/mode_a_longterm_sweep/true_batch_k8_lr03p_200ep.json)
- **Execution Time:** 761.1 s (12.7 min)
- **Statistical Verdict:** **CONVERGING (STATISTICAL DESCENT)**
- **Loss Trajectory Slope:** `-14.496 LSB^2/epoch` ($R^2 = 0.0293$)
- **Quartile 1 Mean Loss:** `22137.4 LSB^2` (4.64 bits) $\to$ **Quartile 4 Mean Loss:** `19754.7 LSB^2` (4.73 bits)
- **Net Long-Term Trend:** `-10.76%`
- **Final Weights:** M8 Diag = `[24, 24, 24, 25, 30, 22]`, M3 Diag = `[64, 63, 64, 64, 63, 62]` ($r_{M3} = 0.9997$)

### Condition: K=12, LR=0.05x (200 epochs)
- **Dataset File:** [`true_batch_k12_lr05p_200ep.json`](../logs/mode_a_longterm_sweep/true_batch_k12_lr05p_200ep.json)
- **Execution Time:** 1237.0 s (20.6 min)
- **Statistical Verdict:** **CONVERGING (STATISTICAL DESCENT)**
- **Loss Trajectory Slope:** `-8.717 LSB^2/epoch` ($R^2 = 0.0088$)
- **Quartile 1 Mean Loss:** `22303.6 LSB^2` (4.63 bits) $\to$ **Quartile 4 Mean Loss:** `20285.3 LSB^2` (4.71 bits)
- **Net Long-Term Trend:** `-9.05%`
- **Final Weights:** M8 Diag = `[26, 24, 24, 25, 31, 25]`, M3 Diag = `[63, 62, 62, 63, 62, 58]` ($r_{M3} = 0.9992$)

### Condition: K=12, LR=0.08x (200 epochs)
- **Dataset File:** [`true_batch_k12_lr08p_200ep.json`](../logs/mode_a_longterm_sweep/true_batch_k12_lr08p_200ep.json)
- **Execution Time:** 1462.3 s (24.4 min)
- **Statistical Verdict:** **STATISTICALLY FLAT (PURE NOISE FLOOR)**
- **Loss Trajectory Slope:** `+2.179 LSB^2/epoch` ($R^2 = 0.0008$)
- **Quartile 1 Mean Loss:** `19461.7 LSB^2` (4.73 bits) $\to$ **Quartile 4 Mean Loss:** `19409.8 LSB^2` (4.74 bits)
- **Net Long-Term Trend:** `-0.27%`
- **Final Weights:** M8 Diag = `[22, 23, 24, 24, 31, 26]`, M3 Diag = `[64, 63, 64, 64, 62, 62]` ($r_{M3} = 0.9998$)

### Condition: K=12, LR=0.10x (200 epochs)
- **Dataset File:** [`true_batch_k12_lr10p_200ep.json`](../logs/mode_a_longterm_sweep/true_batch_k12_lr10p_200ep.json)
- **Execution Time:** 1217.7 s (20.3 min)
- **Statistical Verdict:** **CONVERGING (STATISTICAL DESCENT)**
- **Loss Trajectory Slope:** `-15.383 LSB^2/epoch` ($R^2 = 0.0322$)
- **Quartile 1 Mean Loss:** `21513.9 LSB^2` (4.66 bits) $\to$ **Quartile 4 Mean Loss:** `19183.8 LSB^2` (4.74 bits)
- **Net Long-Term Trend:** `-10.83%`
- **Final Weights:** M8 Diag = `[27, 26, 24, 26, 25, 24]`, M3 Diag = `[63, 62, 63, 63, 62, 58]` ($r_{M3} = 0.9990$)

### Condition: K=16, LR=0.05x (200 epochs)
- **Dataset File:** [`true_batch_k16_lr05p_200ep.json`](../logs/mode_a_longterm_sweep/true_batch_k16_lr05p_200ep.json)
- **Execution Time:** 1413.6 s (23.6 min)
- **Statistical Verdict:** **CONVERGING (STATISTICAL DESCENT)**
- **Loss Trajectory Slope:** `-9.085 LSB^2/epoch` ($R^2 = 0.0108$)
- **Quartile 1 Mean Loss:** `20165.1 LSB^2` (4.72 bits) $\to$ **Quartile 4 Mean Loss:** `18978.1 LSB^2` (4.76 bits)
- **Net Long-Term Trend:** `-5.89%`
- **Final Weights:** M8 Diag = `[23, 24, 24, 24, 28, 24]`, M3 Diag = `[64, 64, 64, 64, 63, 63]` ($r_{M3} = 0.9999$)

### Condition: K=16, LR=0.08x (200 epochs)
- **Dataset File:** [`true_batch_k16_lr08p_200ep.json`](../logs/mode_a_longterm_sweep/true_batch_k16_lr08p_200ep.json)
- **Execution Time:** 1443.6 s (24.1 min)
- **Statistical Verdict:** **CONVERGING (STATISTICAL DESCENT)**
- **Loss Trajectory Slope:** `-13.252 LSB^2/epoch` ($R^2 = 0.028$)
- **Quartile 1 Mean Loss:** `22128.2 LSB^2` (4.64 bits) $\to$ **Quartile 4 Mean Loss:** `19541.2 LSB^2` (4.72 bits)
- **Net Long-Term Trend:** `-11.69%`
- **Final Weights:** M8 Diag = `[26, 26, 24, 24, 33, 25]`, M3 Diag = `[63, 61, 62, 63, 62, 57]` ($r_{M3} = 0.9986$)

### Condition: K=20, LR=0.03x (200 epochs)
- **Dataset File:** [`true_batch_k20_lr03p_200ep.json`](../logs/mode_a_longterm_sweep/true_batch_k20_lr03p_200ep.json)
- **Execution Time:** 1397.6 s (23.3 min)
- **Statistical Verdict:** **CONVERGING (STATISTICAL DESCENT)**
- **Loss Trajectory Slope:** `-23.353 LSB^2/epoch` ($R^2 = 0.0621$)
- **Quartile 1 Mean Loss:** `23586.7 LSB^2` (4.6 bits) $\to$ **Quartile 4 Mean Loss:** `19717.9 LSB^2` (4.73 bits)
- **Net Long-Term Trend:** `-16.40%`
- **Final Weights:** M8 Diag = `[24, 25, 24, 23, 31, 24]`, M3 Diag = `[63, 63, 63, 64, 63, 61]` ($r_{M3} = 0.9996$)

### Condition: K=20, LR=0.05x (200 epochs)
- **Dataset File:** [`true_batch_k20_lr05p_200ep.json`](../logs/mode_a_longterm_sweep/true_batch_k20_lr05p_200ep.json)
- **Execution Time:** 1517.0 s (25.3 min)
- **Statistical Verdict:** **CONVERGING (STATISTICAL DESCENT)**
- **Loss Trajectory Slope:** `-10.901 LSB^2/epoch` ($R^2 = 0.0139$)
- **Quartile 1 Mean Loss:** `22228.4 LSB^2` (4.64 bits) $\to$ **Quartile 4 Mean Loss:** `20466.7 LSB^2` (4.71 bits)
- **Net Long-Term Trend:** `-7.93%`
- **Final Weights:** M8 Diag = `[22, 26, 24, 22, 29, 24]`, M3 Diag = `[64, 64, 64, 64, 63, 64]` ($r_{M3} = 1.0000$)

### Condition: K=20, LR=0.08x (200 epochs)
- **Dataset File:** [`true_batch_k20_lr08p_200ep.json`](../logs/mode_a_longterm_sweep/true_batch_k20_lr08p_200ep.json)
- **Execution Time:** 1432.5 s (23.9 min)
- **Statistical Verdict:** **CONVERGING (STATISTICAL DESCENT)**
- **Loss Trajectory Slope:** `-12.733 LSB^2/epoch` ($R^2 = 0.0247$)
- **Quartile 1 Mean Loss:** `20852.1 LSB^2` (4.68 bits) $\to$ **Quartile 4 Mean Loss:** `19034.2 LSB^2` (4.75 bits)
- **Net Long-Term Trend:** `-8.72%`
- **Final Weights:** M8 Diag = `[26, 25, 24, 24, 30, 21]`, M3 Diag = `[64, 63, 64, 64, 62, 63]` ($r_{M3} = 0.9998$)

### Condition: K=20, LR=0.10x (200 epochs)
- **Dataset File:** [`true_batch_k20_lr10p_200ep.json`](../logs/mode_a_longterm_sweep/true_batch_k20_lr10p_200ep.json)
- **Execution Time:** 1506.9 s (25.1 min)
- **Statistical Verdict:** **CONVERGING (STATISTICAL DESCENT)**
- **Loss Trajectory Slope:** `-14.505 LSB^2/epoch` ($R^2 = 0.0266$)
- **Quartile 1 Mean Loss:** `21998.9 LSB^2` (4.65 bits) $\to$ **Quartile 4 Mean Loss:** `19616.1 LSB^2` (4.73 bits)
- **Net Long-Term Trend:** `-10.83%`
- **Final Weights:** M8 Diag = `[27, 25, 24, 27, 29, 21]`, M3 Diag = `[63, 62, 63, 63, 62, 60]` ($r_{M3} = 0.9995$)

### Condition: K=25, LR=0.03x (200 epochs)
- **Dataset File:** [`true_batch_k25_lr03p_200ep.json`](../logs/mode_a_longterm_sweep/true_batch_k25_lr03p_200ep.json)
- **Execution Time:** 1509.4 s (25.2 min)
- **Statistical Verdict:** **STATISTICALLY FLAT (PURE NOISE FLOOR)**
- **Loss Trajectory Slope:** `-0.696 LSB^2/epoch` ($R^2 = 0.0001$)
- **Quartile 1 Mean Loss:** `20406.2 LSB^2` (4.7 bits) $\to$ **Quartile 4 Mean Loss:** `20222.8 LSB^2` (4.7 bits)
- **Net Long-Term Trend:** `-0.90%`
- **Final Weights:** M8 Diag = `[24, 23, 24, 24, 29, 25]`, M3 Diag = `[64, 63, 63, 64, 63, 62]` ($r_{M3} = 0.9997$)

### Condition: K=25, LR=0.05x (200 epochs)
- **Dataset File:** [`true_batch_k25_lr05p_200ep.json`](../logs/mode_a_longterm_sweep/true_batch_k25_lr05p_200ep.json)
- **Execution Time:** 1526.5 s (25.4 min)
- **Statistical Verdict:** **CONVERGING (STATISTICAL DESCENT)**
- **Loss Trajectory Slope:** `-18.869 LSB^2/epoch` ($R^2 = 0.0427$)
- **Quartile 1 Mean Loss:** `22757.3 LSB^2` (4.62 bits) $\to$ **Quartile 4 Mean Loss:** `19623.8 LSB^2` (4.73 bits)
- **Net Long-Term Trend:** `-13.77%`
- **Final Weights:** M8 Diag = `[25, 24, 24, 24, 34, 23]`, M3 Diag = `[63, 62, 63, 63, 63, 60]` ($r_{M3} = 0.9995$)

### Condition: K=25, LR=0.08x (200 epochs)
- **Dataset File:** [`true_batch_k25_lr08p_200ep.json`](../logs/mode_a_longterm_sweep/true_batch_k25_lr08p_200ep.json)
- **Execution Time:** 1479.2 s (24.7 min)
- **Statistical Verdict:** **STATISTICALLY FLAT (PURE NOISE FLOOR)**
- **Loss Trajectory Slope:** `-2.737 LSB^2/epoch` ($R^2 = 0.0009$)
- **Quartile 1 Mean Loss:** `19602.4 LSB^2` (4.73 bits) $\to$ **Quartile 4 Mean Loss:** `19357.5 LSB^2` (4.74 bits)
- **Net Long-Term Trend:** `-1.25%`
- **Final Weights:** M8 Diag = `[25, 26, 24, 25, 27, 22]`, M3 Diag = `[63, 63, 63, 64, 62, 60]` ($r_{M3} = 0.9995$)

### Condition: K=4, LR=0.05x (200 epochs)
- **Dataset File:** [`true_batch_k4_lr05p_200ep.json`](../logs/mode_a_longterm_sweep/true_batch_k4_lr05p_200ep.json)
- **Execution Time:** 1093.2 s (18.2 min)
- **Statistical Verdict:** **CONVERGING (STATISTICAL DESCENT)**
- **Loss Trajectory Slope:** `-23.957 LSB^2/epoch` ($R^2 = 0.073$)
- **Quartile 1 Mean Loss:** `23038.3 LSB^2` (4.62 bits) $\to$ **Quartile 4 Mean Loss:** `18885.5 LSB^2` (4.75 bits)
- **Net Long-Term Trend:** `-18.03%`
- **Final Weights:** M8 Diag = `[28, 25, 24, 25, 31, 22]`, M3 Diag = `[63, 62, 62, 63, 62, 58]` ($r_{M3} = 0.9990$)

### Condition: K=4, LR=0.10x (200 epochs)
- **Dataset File:** [`true_batch_k4_lr10p_200ep.json`](../logs/mode_a_longterm_sweep/true_batch_k4_lr10p_200ep.json)
- **Execution Time:** 1153.7 s (19.2 min)
- **Statistical Verdict:** **STATISTICALLY FLAT (PURE NOISE FLOOR)**
- **Loss Trajectory Slope:** `-3.776 LSB^2/epoch` ($R^2 = 0.0017$)
- **Quartile 1 Mean Loss:** `21532.6 LSB^2` (4.67 bits) $\to$ **Quartile 4 Mean Loss:** `21190.9 LSB^2` (4.67 bits)
- **Net Long-Term Trend:** `-1.59%`
- **Final Weights:** M8 Diag = `[27, 23, 24, 24, 31, 25]`, M3 Diag = `[63, 62, 63, 63, 62, 59]` ($r_{M3} = 0.9994$)

### Condition: K=4, LR=0.20x (200 epochs)
- **Dataset File:** [`true_batch_k4_lr20p_200ep.json`](../logs/mode_a_longterm_sweep/true_batch_k4_lr20p_200ep.json)
- **Execution Time:** 1273.8 s (21.2 min)
- **Statistical Verdict:** **CONVERGING (STATISTICAL DESCENT)**
- **Loss Trajectory Slope:** `-49.507 LSB^2/epoch` ($R^2 = 0.0023$)
- **Quartile 1 Mean Loss:** `21739.2 LSB^2` (4.64 bits) $\to$ **Quartile 4 Mean Loss:** `18204.2 LSB^2` (4.77 bits)
- **Net Long-Term Trend:** `-16.26%`
- **Final Weights:** M8 Diag = `[29, 24, 24, 25, 29, 22]`, M3 Diag = `[64, 62, 64, 64, 61, 63]` ($r_{M3} = 0.9995$)

