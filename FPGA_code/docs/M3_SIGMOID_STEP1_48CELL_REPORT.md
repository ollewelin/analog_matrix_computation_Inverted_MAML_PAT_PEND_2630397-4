# Matrix 3 Sigmoid Analog Activation Characterization Report (Ref 4)

**Steg 1: Full 48-Crosspoint Transfer Landscape via ColTIA + Sigmoid (Ref 4) on Differential ADC_45**  
**Execution Environment:** Pure Physical Silicon (Trion T120 Master SoC @ 192.168.1.50:5000)  
**Settled Snapshot Timing:** Locked strictly to nominal $t = 5.0\text{ ms}$ ($5000\ \mu\text{s}$)  
**Sweep Repetitions:** 6 recharges per operating point  
**Total Execution Duration:** 8.4 minutes  

---

## 1. Executive Summary

Matrix 3 is the primary adaptive compensation layer in the Inverted MAML architecture, driving the ColTIA summing stages and the physical analog sigmoid activation circuitry (Ref 4).
This empirical characterization measured all 48 crosspoints ($8\text{ rows} \times 6\text{ cols}$) under 17 weight levels ($W \in [-127..+127]$) across 5 standard input DAC_2 levels ($X \in \{-127, -64, 0, +64, +127\}$).

### Key Findings:
- **Active Dynamics Across All 6 Columns:** Unlike uncompensated Matrix 33 Mode B where Columns 2 and 3 were railed at $-2048\text{ LSB}$, the ColTIA and analog sigmoid activation in Matrix 3 are active and responsive across all 6 columns.
- **Polarity Trade-off:** Positive weights ($W \ge 0$) vs Negative weights ($W \le 0$) were evaluated using the objective score metric:
  $$\text{Score} = \frac{\text{Dynamic Swing } \Delta Y}{1 + \text{Jerk} / 10} \times \text{Monotonicity}$$

---

## 2. Column-Wise Polarity Summary Table

| Column | Score (W ≤ 0) | Score (W ≥ 0) | Recommended Polarity | Optimal Biasing Direction |
| :--- | :---: | :---: | :---: | :--- |
| **C0** | 48.1 | 73.3 | **POS** | Positive sigmoid knee (+) |
| **C1** | 49.4 | 77.5 | **POS** | Positive sigmoid knee (+) |
| **C2** | 41.7 | 93.4 | **POS** | Positive sigmoid knee (+) |
| **C3** | 43.3 | 69.1 | **POS** | Positive sigmoid knee (+) |
| **C4** | 57.5 | 65.8 | **POS** | Positive sigmoid knee (+) |
| **C5** | 43.5 | 78.6 | **POS** | Positive sigmoid knee (+) |

---

## 3. Diagnostic Visualizations

- Full 48-Cell Transfer Grid: `FPGA_code/docs/figures/fig_m3_sigmoid_step1_48cell_grid.png`
- Dynamic Swing and Jerk Heatmaps: `FPGA_code/docs/figures/fig_m3_sigmoid_step1_heatmaps.png`
- Column-Wise Quality Comparison: `FPGA_code/docs/figures/fig_m3_sigmoid_step1_column_summary.png`

---

## 4. Next Step: Steg 2 Column Collective S-Curve

Now proceeding to Steg 2: sweeping all rows collectively on each column ($W_3[0..7][c]$ ramped together) across $X = \pm 127$ and $X = \pm 64$ to observe the full macroscopic sigmoid curve and locate the optimal baseline knee vector $\mathbf{W}_{3,\text{baseline}}$.
