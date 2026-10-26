# Inverted MAML Mode A: Long-Term Batch & Learning Rate Statistical Sweep

**Last Updated:** 2026-10-26 08:31:23  
**Target Platform:** Efinix Trion T120F324 Master SoC (`192.168.1.50:5000`)  
**Operating Mode:** Mode A (Active 2-Layer Triad via Sigmoid 10, Jumper Mode 3)  
**Hardware Summing Attenuator:** $1\text{ k}\Omega / 3.9\text{ k}\Omega$ ($20.4\%$ authority, baseline before $15\text{ k}\Omega$ rework)  
**Completed Conditions:** 7 experiments  

---

## 1. Executive Statistical Ranking (Convergence vs Flat vs Divergent)

| Rank | Batch Size $K$ | LR Scale | Epochs | Slope ($\beta_1$) | $\Delta Q_1 \to Q_4$ | Q4 ENOB | Peak ENOB | Statistical Verdict |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| 1 | K=12 | 0.05x | 200 | `-4.17` | **-2.8%** | 4.79 b | 5.30 b | STATISTICALLY FLAT (PURE NOISE FLOOR) |
| 2 | K=8 | 0.10x | 200 | `+1.99` | **+1.5%** | 4.80 b | 5.46 b | STATISTICALLY FLAT (PURE NOISE FLOOR) |
| 3 | K=12 | 0.10x | 200 | `+0.93` | **+2.5%** | 4.73 b | 5.17 b | STATISTICALLY FLAT (PURE NOISE FLOOR) |
| 4 | K=8 | 0.03x | 200 | `+4.87` | **+3.5%** | 4.77 b | 5.19 b | STATISTICALLY FLAT (PURE NOISE FLOOR) |
| 5 | K=8 | 0.08x | 200 | `+7.92` | **+5.7%** | 4.70 b | 5.25 b | DIVERGING / INSTABILITY |
| 6 | K=8 | 0.05x | 200 | `+7.97` | **+7.3%** | 4.79 b | 5.47 b | DIVERGING / INSTABILITY |
| 7 | K=12 | 0.08x | 200 | `+162.19` | **+117.7%** | 4.70 b | 5.39 b | DIVERGING / INSTABILITY |

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

