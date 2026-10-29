---
name: m3-sigmoid-activation-mapping
description: Protocol, methodologies, and characterization workflows for mapping Matrix 3 (48 crosspoints, 8 rows x 6 cols) through the analog ColTIA transimpedance amplifiers and hardware sigmoid activation function (Ref 4), measured via differential ADC_45 at nominal 5.0 ms snapshot delay. Guides Steg 1 (single-cell sweep) and Steg 2 (column collective sigmoid S-curve sweep) to identify optimal baseline weights and polarity balancing dynamic swing and smoothness.
---

# Matrix 3 Sigmoid Analog Activation Mapping Skill (Ref 4)

This skill formalizes the 2-stage characterization and calibration protocol for **Matrix 3** ($M_3$, $8\text{ rows} \times 6\text{ cols} = 48\text{ cells}$) driving the **analog sigmoid activation network (Ref 4)**, measured on differential **ADC_45** at nominal snapshot time $t = 5.0\text{ ms}$ on the physical Trion T120 Master SoC (`192.168.1.50:5000`).

---

## 1. Physical Architecture & Motivation

Matrix 3 is the first adaptive compensation layer in the Inverted MAML silicon computing engine:
- **Topology:** 8 input rows ($X_0..X_5$ from DAC_2[0..5], Row 6 from `DAC2_D_ROW7` Trim $B_1$, Row 7 from `DAC2_D_ROW8` Trim Ref) by 6 output columns ($C_0..C_5$).
- **Summing Junction:** Each column current $I_{\text{col},c} = \sum_{r=0}^7 I_{r,c}$ enters the ColTIA transimpedance amplifier stage.
- **Analog Sigmoid Activation (Ref 4):** The ColTIA output feeds the physical BJT/MOSFET differential sigmoid compression network (Ref 4).
- **Readout:** Differential ADC_45 directly converts the activated column outputs $ACT(4)\_D\_COL[0..5]$.

### Core Engineering Objective:
Standard backpropagation initializes weights at zero or random gaussian. In this analog substrate:
1. $W = 0$ is NOT the optimal operating point if the sigmoid activation has physical DC offsets, asymmetry, or dead zones.
2. We want to place the **baseline initial weights** $W_{3,\text{baseline}}$ directly into the "sweet spot" knee/bend of the analog S-curve:
   - Either the **negative bend ($-$)** or **positive bend ($+$)**.
   - High dynamic gain ($|\Delta Y|$) combined with smooth, non-stochastic, low-jitter transfer ($1 / (1 + \text{Jerk})$).
3. In future training runs, any L2 weight regularization ($\lambda \sum (W - W_{\text{base}})^2$) will pull weights toward this optimal knee rather than toward dead zero.

---

## 2. Two-Stage Characterization Protocol

### Steg 1: Single-Cell Full 48-Crosspoint Landscape Map
- **Scope:** All 48 cells ($R_0..R_7 \times C_0..C_5$) probed individually.
- **Isolation:** Active cell $(r, c)$ set to $W \in [-127, +127]$ (17 steps: $\pm 127, \pm 112, \pm 96, \pm 80, \pm 64, \pm 48, \pm 32, \pm 16, 0$). All other rows clamped quiescent ($X=0, W=0$).
- **Inputs:** 5 standardized DAC_2 levels:
  - $X = -127$ (Blue)
  - $X = -64$ (Red)
  - $X = 0$ (Green)
  - $X = +64$ (Orange)
  - $X = +127$ (Yellow/Gold)
- **Timing:** Strictly locked to nominal snapshot delay $t = 5.0\text{ ms}$ ($5000\ \mu\text{s}$). No other delays probed.
- **Metrics Computed Per Cell:**
  - $\text{Dynamic Swing } \Delta Y = \max(Y) - \min(Y)$ for $W \le 0$ vs $W \ge 0$.
  - $\text{Jerk / Roughness } J = \sqrt{\text{Resid}^2 + \sigma_{\text{noise}}^2}$ (residual from cubic polynomial fit plus measurement standard deviation).
  - $\text{Monotonicity } M \in [0, 1]$.
  - $\text{Bend Magnitude } B = \max |d^2Y / dW^2|$ and its position $W_{\text{bend}}$.
  - $\text{Polarity Quality Score } S = \frac{\Delta Y}{1 + J / 10} \times M$.
  - Decision: Recommend $(+)$ or $(-)$ polarity for each column and cell.

### Steg 2: Column Collective Sigmoid S-Curve Map
- **Scope:** Sweeps entire column $c \in [0..5]$ with all 8 rows driven collectively:
  $$W_3[0..7][c] = W \quad \text{ramped from } 0 \to +127 \text{ and } 0 \to -127$$
- **Input Levels Tested:** Focus on arbitrary and representative operating levels:
  - $X = \pm 127$ (Full scale)
  - $X = \pm 64$ (Medium operating point)
- **Goal:**
  - Observe the full macroscopic S-curve into the sigmoid (Ref 4) under collective column current drive.
  - Locate the optimal knee $W_{\text{knee}}[c]$ where medium signals ($X = \pm 64$) achieve maximum linear/sigmoid sensitivity without falling into saturation or dead zones.
  - Formulate the calibrated baseline weight vector:
    $$\mathbf{W}_{3,\text{baseline}} = [W_{\text{base},0}, W_{\text{base},1}, W_{\text{base},2}, W_{\text{base},3}, W_{\text{base},4}, W_{\text{base},5}]$$

---

## 3. Automation Scripts & Artifact Locations

| Tool / Script | Purpose | Output Path |
| :--- | :--- | :--- |
| `FPGA_code/scripts/m3_sigmoid_step1_cell_map.py` | Steg 1 hardware sweep (48 cells, 5 levels, reps=6, 5ms) | `FPGA_code/logs/m3_sigmoid_characterization/step1_m3_cell_map_5ms.json` |
| `FPGA_code/scripts/plot_m3_sigmoid_step1.py` | Generates 48-cell transfer grid, heatmaps of swing, jerk, and polarity score | `FPGA_code/docs/figures/fig_m3_sigmoid_step1_*.png` |
| `FPGA_code/scripts/generate_m3_sigmoid_step1_report_pdf.py` | Generates formal PDF & MD reports for Steg 1 | `FPGA_code/docs/M3_SIGMOID_STEP1_48CELL_REPORT.pdf` & `.md` |
| `FPGA_code/scripts/m3_sigmoid_step2_column_scurve.py` | Steg 2 collective column sweep & baseline knee optimizer | `FPGA_code/logs/m3_sigmoid_characterization/step2_column_scurve.json` |
| `FPGA_code/scripts/generate_m3_sigmoid_step2_report_pdf.py` | Generates formal PDF & MD reports for Steg 2 | `FPGA_code/docs/M3_SIGMOID_STEP2_COLUMN_SCURVE_REPORT.pdf` & `.md` |

---

## 4. Hardware Safety & Quota Compliance

1. **Pure Physical Silicon:** All measurements are obtained over UDP (`192.168.1.50:5000`) with zero simulation.
2. **Quota Guard:** Total JSON export size per characterization run must be $< 10\text{ MB}$ (well below the $100\text{ MB}$ repo limit).
3. **No Continuous Background Disk Writes:** Single structured JSON file written per step.
4. **Git Discipline:** Strictly NO `git push`. Local commits only.

