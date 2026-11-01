# INVERTED MAML MILESTONE 3: Silicon Evaluation with Full ±80 LSB Zero-Mean Colored Input Swing (LR = 0.08x, λ = 1024)
### Broadened Temporal Window [4500 – 5500 µs], 100% Identical 200-Sample Hadamard Cadence, and 6x AC-Boosted LayerNorm Toeplitz Excitation

**Patent Pending:** Swedish Patent Application SE 2630397-4  
**Inventor & System Architect:** Olle Welin  
**Platform:** Open Science Hardware | Efinix Trion T120 Master SoC (Ethernet @ `192.168.1.50:5000`, FW `v2.2-MAML`) & T20 Controller  
**Milestone 3 Protocol:** Broadened temporal discharge window `4500 µs to 5500 µs` (10 discrete temporal strata × `K = 20` batch = **200 Hadamard-active analog measurements per epoch** across all 500 epochs), `LR = 0.08x`, `L2 Reg λ = 1024`, `Noise Mode = COLOR_LLM_TOEPLITZ` (ρ = 0.85) with **Full ±80 LSB Zero-Mean Proportional Swing**.  
**Dataset Source:** Physical silicon telemetry from `FPGA_code/logs/mode_a_extended_training/mode_a_500ep_broadened_4p5to5p5ms_reg1024_lr0p08_swing80_identical_k20_llm.json`  
**Code Repository:** [https://github.com/ollewelin/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4](https://github.com/ollewelin/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4)  

---

## 1. Executive Summary & Upgraded ±80 LSB Zero-Mean Colored Swing

### Why Previous Colored Runs Exhibited ±22 LSB Swing & How ±80 LSB Zero-Mean Swing Was Achieved:
1. **Root Cause of Earlier ±22 LSB Swing:** In previous firmware builds, `max_span` was set to `45 LSB` and the Kac-Murdock-Szegö AR(1) filter (`ρ = 0.85`) weighted new per-channel innovations by `(1 - ρ) = 0.15`. When Hardware LayerNorm subtracted the 6-channel spatial mean (`sum(x_i)/6`) to eliminate common-mode DC current into the single-supply ColTIA pedestal (`sum W_33 ≈ +120 LSB`), the remaining differential AC residual only spanned **±22 LSB max (9.5 LSB mean peak, ~9.6 LSB RMS)**.
2. **Upgraded Full-Scale ±80 LSB Zero-Mean Colored Generator:** In `maml_generate_new_white_noise_ref()`, `max_span` was raised to **80 LSB** (DAC2 codes `48..208` around `128`), and the zero-mean LayerNorm residual `(val[i] - mean_val)` is boosted by **6×** followed by **proportional 6-channel vector scaling** (`val[i] = val[i] * 80 / max_abs` whenever `max_abs > 80`) and rounding-residual trim. Across all 501 epochs of this run, the physical input vectors achieved **`mean_peak = 68.4 LSB`, `median_peak = 78.0 LSB`, `90th percentile = 80.0 LSB`, `max_peak = 80 LSB`, and `mean_rms = 42.0 LSB`** (~19× / +12.9 dB higher input signal power than ±22 LSB) while keeping common-mode DC sum near zero (`|sum(x_i)| <= 4 LSB`) and **zero ColTIA clipping (`col_clip_mask = 0`)**!
3. **Full-Window Error Suppression Under Full ±80 LSB Swing:** Despite 19× higher input signal energy driving much larger uncompensated swing (`Phase 1 mean = 128,033.2 LSB²`, `Phase 2 mean = 135,857.5 LSB²`), activating closed-loop training at Epoch 200 (`LR = 0.08x, λ = 1024`) cut full-window `[4.5..5.5 ms]` quadratic loss by **-19.9% (sustained mean: 108,758.5 LSB²)** and **-36.6% (minimum: 86,094.5 LSB² at Ep 484, reaching 3.60 bits Window ENOB)**, finishing at Epoch 500 with `W8_diag = [-20, -14, 16, 112, 43, 20]` (**0 saturated columns** at Epoch 500).

---

## 2. Empirical Silicon Telemetry Table (±80 LSB Colored Swing, LR = 0.08x, λ = 1024)

| Metric | Phase 1: M33 Alone (Ep 0..99) | Phase 2: Smart Baseline (Ep 100..199) | **Phase 3: Trained Peak** | Phase 3: Sustained Mean (Ep 200..500) |
| :--- | :---: | :---: | :---: | :---: |
| **Compensation Mode** | Zeroed ($W=0\text{ LSB}$) | Balanced Smart S-Bend | **Active Closed-Loop Trained** | Sustained Active Trained |
| **In-Data Colored Swing** | $\pm 80\text{ LSB}$ ($68.4\text{ LSB}$ mean pk) | $\pm 80\text{ LSB}$ ($68.4\text{ LSB}$ mean pk) | **$\pm 80\text{ LSB}$ ($78.0\text{ LSB}$ med pk)** | $\pm 80\text{ LSB}$ ($42.0\text{ LSB}$ RMS) |
| **Hyperparameters** | $\text{LR}=0,\, \lambda=0$ | $\text{LR}=0,\, \lambda=0$ | **$\text{LR}=0.08,\, \lambda=1024$** | $\text{LR}=0.08,\, \lambda=1024$ |
| **200-Sample Window Mean Loss** | $128,033.2\text{ LSB}^2$ | $135,857.5\text{ LSB}^2$ | **$86,094.5\text{ LSB}^2$ (Ep 484)** | **$108,758.5\text{ LSB}^2$ ($-19.9\%$)** |
| **200-Sample Window ENOB [4.5..5.5 ms]** | $3.31\text{ bits}$ | $3.27\text{ bits}$ | **$3.60\text{ bits}$ (Ep 484)** | **$3.43\text{ bits}$** |
| **5.0 ms Center Snapshot Loss** | $62,127.9\text{ LSB}^2$ (mean) | $64,333.9\text{ LSB}^2$ (mean) | **$2,084.0\text{ LSB}^2$ (Ep 218)** | $56,694.6\text{ LSB}^2$ (mean) |
| **5.0 ms Center Snapshot ENOB** | $4.11\text{ bits}$ | $4.12\text{ bits}$ | **$6.28\text{ bits}$ (Ep 218)** | $4.11\text{ bits}$ (mean) |
| **M8 Diagonal Weights [LSB]** | $[0, 0, 0, 0, 0, 0]$ | $[-20, -20, 20, 20, -20, 20]$ | $[-22, -15, 14, 114, 42, 17]$ (Ep 484) | $[-20, -14, 16, 112, 43, 20]$ (Ep 500) |

---

## 3. 3D Dual-2T1C Weight Topographies (Baseline vs. Trained Golden State)

![3D Weight Topography](file:///home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a/fig_mode_a_3d_weight_landscapes_baseline_vs_golden_reg1024_lr0p08_swing80.png)

---

## 4. 500-Epoch Trajectories at SINGLE-POINT t = 5.0 ms ONLY (Nominal Center Snapshot)

![500-Epoch Single-Point 5.0 ms Trajectory](file:///home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a/fig_mode_a_500ep_5p0ms_only_reg1024_lr0p08_swing80.png)

---

## 5. 500-Epoch Trajectories Across FULL TEMPORAL WINDOW [4.5 ms to 5.5 ms] AGGREGATED

![500-Epoch Full Window 4.5 to 5.5 ms Trajectory](file:///home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a/fig_mode_a_500ep_window_4p5to5p5ms_only_reg1024_lr0p08_swing80.png)

---

## 6. Full 2D Trajectories of All Weights (Matrix 3 & Matrix 8 across 500 Epochs)

### Matrix 3 (First Triad Layer): 48 Dynamic Weights
![Matrix 3 2D Trajectories](file:///home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a/fig_2d_m3_weights_trajectory_reg1024_lr0p08_swing80.png)

### Matrix 8 (Second Triad Layer): 42 Vernier Weights
![Matrix 8 2D Trajectories](file:///home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a/fig_2d_m8_weights_trajectory_reg1024_lr0p08_swing80.png)

---

## 7. Deep-Dive Analysis: Phase 3 High-Resolution Stability

![Deep Dive Analysis](file:///home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a/fig_mode_a_500ep_deep_dive_reg1024_lr0p08_swing80.png)

---

## 8. Interactive 3D Silicon Studio GUI, Hardcoded Matrix W33 & Three Concrete Signal-Flow Examples

![Interactive 3D Silicon Studio GUI at Epoch 397](file:///home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a/fig_gui_3d_telemetry_ep397_swing80.jpg)

### 8.1 Hardcoded Frozen Primary Payload Matrix $W_{33}$ (`k_default_m33`, $6 \times 6$ DAC Offsets)
The Digital Supervisor computes the ideal reference output vector $Z_{\text{target}}[j]$ for every new zero-mean colored input vector $X[0..5]$ by multiplying $X$ with the hardcoded $6 \times 6$ matrix $W_{33}$ and adding the calibrated quiescent DC zero baseline $Z_{\text{zero\_cal}}[j]$:
$$S_{\text{dot}}[j] = \sum_{i=0}^{5} X[i] \cdot W_{33}[i, j], \qquad \Delta Z_{\text{ideal}}[j] = \text{round}\!\left(\frac{8 \cdot S_{\text{dot}}[j]}{256}\right), \qquad Z_{\text{target}}[j] = Z_{\text{zero\_cal}}[j] + \Delta Z_{\text{ideal}}[j]$$

| Matrix $W_{33}$ Row / Parameter | Col 0 | Col 1 | Col 2 | Col 3 | Col 4 | Col 5 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Row 0 ($X[0]$)** | $+76$ | $-20$ | $+28$ | $-4$ | $+44$ | $-36$ |
| **Row 1 ($X[1]$)** | $-20$ | $+84$ | $-12$ | $+44$ | $-4$ | $+36$ |
| **Row 2 ($X[2]$)** | $+36$ | $-4$ | $+80$ | $-16$ | $+32$ | $-4$ |
| **Row 3 ($X[3]$)** | $-4$ | $+40$ | $-8$ | $+72$ | $-12$ | $+44$ |
| **Row 4 ($X[4]$)** | $+44$ | $-12$ | $+28$ | $-12$ | $+76$ | $-8$ |
| **Row 5 ($X[5]$)** | $-28$ | $+32$ | $-4$ | $+40$ | $-8$ | $+82$ |
| **Column Sum $\sum_i W_{33}[i,j]$ (Pedestal)** | **$+104$** | **$+120$** | **$+112$** | **$+124$** | **$+128$** | **$+114$** |
| **Calibrated Quiescent Zero $Z_{\text{zero\_cal}}[j]$ (ADC LSB)** | **$-868$** | **$-1114$** | **$-1140$** | **$-521$** | **$+519$** | **$+98$** |

### 8.2 Example 1 — Epoch #397 (Exact GUI Screenshot State: Full $+80\text{ LSB}$ Input Swing on Row 0)
- **Input Vector $X[0..5]$:** `[+80, +9, +15, -57, -27, -21] LSB` (`Peak = +80 LSB`, `Sum = -1 LSB`)
- **5.0 ms Center Snapshot:** `RMSE = 130.96 LSB`, `Quadratic Loss = 51,452.0 LSB²`, **`ENOB = 3.97 bits`**
- **200-Sample [4.5..5.5 ms] Window:** `RMSE = 180.81 LSB`, `Window Loss = 98,076.5 LSB²`, **`Window ENOB = 3.50 bits`**

| Signal / Quantity (Epoch #397) | Col 0 | Col 1 | Col 2 | Col 3 | Col 4 | Col 5 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Input Data $X[j]$ (DAC LSB)** | **$+80$** | **$+9$** | **$+15$** | **$-57$** | **$-27$** | **$-21$** |
| **Dot Product $S_{\text{dot}}[j] = \sum_i X[i] W_{33}[i,j]$** | $+6068$ | $-3532$ | $+3116$ | $-4784$ | $+2764$ | $-6630$ |
| **Ideal AC Swing $\Delta Z_{\text{ideal}}[j] = \text{round}(S_{\text{dot}}/32)$** | $+190$ | $-110$ | $+97$ | $-150$ | $+86$ | $-207$ |
| **Zero-Cal Pedestal $Z_{\text{zero\_cal}}[j]$ (ADC LSB)** | $-868$ | $-1114$ | $-1140$ | $-521$ | $+519$ | $+98$ |
| **Ideal Target $Z_{\text{target}}[j]$ (ADC LSB)** | **$-678$** | **$-1224$** | **$-1043$** | **$-671$** | **$+605$** | **$-109$** |
| **First-Stage $M_3$ Readout $\text{ADC}_{45}[j]$ (ADC LSB)** | $-753$ | $-183$ | $+172$ | $+232$ | $+669$ | $-1037$ |
| **Physical Triad Output $\text{ADC}_{49}[j]$ (ADC LSB)** | **$-862$** | **$-1202$** | **$-1130$** | **$-562$** | **$+788$** | **$+16$** |
| **Residual Error $e[j] = \text{ADC}_{49}[j] - Z_{\text{target}}[j]$** | **$-184$** | **$+22$** | **$-87$** | **$+109$** | **$+183$** | **$+125$** |
| **Active $M_8$ Diagonal Weight $W_8[j,j]$ (LSB)** | $-32$ | $-16$ | $+10$ | $+72$ | $+36$ | $+17$ |

### 8.3 Example 2 — Epoch #372 (Full $-80\text{ LSB}$ Input Swing on Row 5, High 5.0 ms & Window ENOB)
- **Input Vector $X[0..5]$:** `[+36, +46, -5, +17, -15, -80] LSB` (`Peak = -80 LSB`, `Sum = -1 LSB`)
- **5.0 ms Center Snapshot:** `RMSE = 82.90 LSB`, `Quadratic Loss = 20,617.5 LSB²`, **`ENOB = 4.63 bits`**
- **200-Sample [4.5..5.5 ms] Window:** `RMSE = 179.52 LSB`, `Window Loss = 96,685.0 LSB²`, **`Window ENOB = 3.51 bits`**

| Signal / Quantity (Epoch #372) | Col 0 | Col 1 | Col 2 | Col 3 | Col 4 | Col 5 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Input Data $X[j]$ (DAC LSB)** | **$+36$** | **$+46$** | **$-5$** | **$+17$** | **$-15$** | **$-80$** |
| **Dot Product $S_{\text{dot}}[j] = \sum_i X[i] W_{33}[i,j]$** | $+3148$ | $+1464$ | $+44$ | $+692$ | $+364$ | $-5328$ |
| **Ideal AC Swing $\Delta Z_{\text{ideal}}[j] = \text{round}(S_{\text{dot}}/32)$** | $+98$ | $+46$ | $+1$ | $+22$ | $+11$ | $-166$ |
| **Zero-Cal Pedestal $Z_{\text{zero\_cal}}[j]$ (ADC LSB)** | $-868$ | $-1114$ | $-1140$ | $-521$ | $+519$ | $+98$ |
| **Ideal Target $Z_{\text{target}}[j]$ (ADC LSB)** | **$-770$** | **$-1068$** | **$-1139$** | **$-499$** | **$+530$** | **$-68$** |
| **First-Stage $M_3$ Readout $\text{ADC}_{45}[j]$ (ADC LSB)** | $-526$ | $-263$ | $+134$ | $-128$ | $+315$ | $-887$ |
| **Physical Triad Output $\text{ADC}_{49}[j]$ (ADC LSB)** | **$-783$** | **$-1049$** | **$-1095$** | **$-623$** | **$+682$** | **$-51$** |
| **Residual Error $e[j] = \text{ADC}_{49}[j] - Z_{\text{target}}[j]$** | **$-13$** | **$+19$** | **$+44$** | **$-124$** | **$+152$** | **$+17$** |
| **Active $M_8$ Diagonal Weight $W_8[j,j]$ (LSB)** | $-29$ | $-17$ | $+11$ | $+53$ | $+31$ | $+18$ |

### 8.4 Example 3 — Epoch #484 (Best 200-Sample Window Golden State, $+80\text{ LSB}$ Swing) & Epoch #218 (Best 5.0 ms Peak, $6.28\text{ bits}$)
- **Epoch #484 Input Vector $X[0..5]$:** `[+80, +21, -36, -10, -21, -32] LSB` (`Peak = +80 LSB`, `Sum = +2 LSB`) — **Best 200-Sample Window Loss = `86,094.5 LSB²` (`RMSE = 169.41 LSB`, `Window ENOB = 3.60 bits`)**
- **Epoch #218 Input Vector $X[0..5]$:** `[-6, +30, +18, +6, -24, -24] LSB` (`Peak = +30 LSB`, `Sum = 0 LSB`) — **Best 5.0 ms Snapshot Loss = `2,084.0 LSB²` (`RMSE = 26.36 LSB`, `5.0 ms ENOB = 6.28 bits`, `Window ENOB = 3.48 bits`)**

| Signal / Quantity (Epoch #484 / #218) | Col 0 | Col 1 | Col 2 | Col 3 | Col 4 | Col 5 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Ep #484 Input Data $X[j]$ (DAC LSB)** | **$+80$** | **$+21$** | **$-36$** | **$-10$** | **$-21$** | **$-32$** |
| **Ep #484 Dot Product $S_{\text{dot}}[j] = \sum_i X[i] W_{33}[i,j]$** | $+4376$ | $-864$ | $-1272$ | $-568$ | $+1064$ | $-4876$ |
| **Ep #484 Ideal Target $Z_{\text{target}}[j]$ (ADC LSB)** | **$-731$** | **$-1141$** | **$-1180$** | **$-539$** | **$+552$** | **$-54$** |
| **Ep #484 Physical Triad Output $\text{ADC}_{49}[j]$** | **$-1011$** | **$-1088$** | **$-1102$** | **$-471$** | **$+772$** | **$+53$** |
| **Ep #484 Residual Error $e[j]$ (`Win ENOB = 3.60 b`)** | $-280$ | $+53$ | $+78$ | $+68$ | $+220$ | $+107$ |
| **Ep #218 Input Data $X[j]$ (DAC LSB)** | **$-6$** | **$+30$** | **$+18$** | **$+6$** | **$-24$** | **$-24$** |
| **Ep #218 Ideal Target $Z_{\text{target}}[j]$ (ADC LSB)** | **$-894$** | **$-1041$** | **$-1131$** | **$-495$** | **$+472$** | **$+89$** |
| **Ep #218 Physical Triad Output $\text{ADC}_{49}[j]$** | **$-855$** | **$-1067$** | **$-1116$** | **$-498$** | **$+508$** | **$+110$** |
| **Ep #218 Residual Error $e[j]$ (`5.0 ms ENOB = 6.28 b`)** | **$+39$** | **$-26$** | **$+15$** | **$-3$** | **$+36$** | **$+21$** |

---

## 9. Physical Hardware Silicon: Inverted MAML Proof-of-Concept PCB (v1.3.2)

![Physical Hardware PCB v1.3.2](file:///home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a/fig_pcb_v132_hardware.jpg)

---

## 9. Patented Inverted MAML Proprioceptive Architecture (Patent SE 2630397-4 Fig 1)

![Patented Architecture Fig 1](file:///home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a/fig_patent_fig1_architecture.jpg)

---

## 10. Forward Hadamard Propagation (FHP) & Capacitive Perturbation (Patent Fig 8)

![Patent Fig 8 FHP Circuit](file:///home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a/fig_patent_fig8_fhp_circuit.jpg)

---

## 11. Temporal Leakage Compensation & Displaced Sampling (Patent Fig 5 & Fig 6)

![Patent Fig 5 Displaced Sampling](file:///home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a/fig_patent_fig5_temporal_leakage.png)

![Patent Fig 6 Temporal Leakage](file:///home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a/fig_patent_fig6_temporal_compensation.png)

---

## 12. Open Science Reproducibility Summary

All telemetry records and plots in this report are 100 % authentic, measured directly on physical silicon hardware via the Efinix Trion T120 SoC at `192.168.1.50:5000` running `v2.2-MAML` firmware.
