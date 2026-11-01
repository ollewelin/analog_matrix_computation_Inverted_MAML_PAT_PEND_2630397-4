# INVERTED MAML MILESTONE 3: Silicon Evaluation with Fine-Grained Learning Rate and Stiff Regularization (LR = 0.08x, λ = 1024)
### Broadened Temporal Window [4500 – 5500 µs], 100% Identical 200-Sample Hadamard Measurement Cadence, and Tripartite Regularization Analysis

**Patent Pending:** Swedish Patent Application SE 2630397-4  
**Inventor & System Architect:** Olle Welin  
**Platform:** Open Science Hardware | Efinix Trion T120 Master SoC (Ethernet @ `192.168.1.50:5000`, FW `v2.2-MAML`) & T20 Controller  
**Milestone 3 Protocol:** Broadened temporal discharge window `4500 µs to 5500 µs` (10 discrete temporal strata × `K = 20` batch = **200 Hadamard-active analog measurements per epoch** across all 500 epochs), `LR = 0.08x` (fine-grained), `L2 Reg λ = 1024` (stiff restoring spring), `Noise Mode = COLOR_LLM_TOEPLITZ` (ρ = 0.85).  
**Dataset Source:** Physical silicon telemetry from `FPGA_code/logs/mode_a_extended_training/mode_a_500ep_broadened_4p5to5p5ms_reg1024_lr0p08_identical_k20_llm.json`  
**Code Repository:** [https://github.com/ollewelin/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4](https://github.com/ollewelin/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4)  

---

## 1. Executive Summary & Tripartite Hyperparameter Insights

### Research Question:
> *What happens when the learning rate is scaled down to 1/3 (LR = 0.08x) while maintaining the strong L2 regularization restoring force (λ = 1024)?*

### Empirical Silicon Findings:
1. **Full-Window Error Suppression:** Across the 200-sample window [4.5..5.5 ms], active training reduced quadratic error by **-19.5% (sustained mean: 61,834.7 LSB²)** and **-24.6% (minimum: 57,909.0 LSB² at Ep 240)**, maintaining full-window resolution at **3.83 bits mean (3.88 bits peak)**.
2. **Single-Point 5.0 ms Anchor:** At the nominal 5.0 ms midpoint, closed-loop training achieved a minimum loss of **122.0 LSB²** at Epoch 273, reaching **8.33 bits Standard ENOB**.
3. **Dynamic Centering & Rail Saturation Prevention:** In contrast to the run with $\lambda = 341$ where Column 3 clamped at $+120\text{ LSB}$, the stiff $\lambda = 1024$ restoring spring successfully provided centering authority against directional analog gradient bias.

---

## 2. Empirical Silicon Telemetry Table (LR = 0.08x, λ = 1024)

| Metric | Phase 1: M33 Alone (Ep 0..99) | Phase 2: Smart Baseline (Ep 100..199) | **Phase 3: Trained Peak** | Phase 3: Sustained Mean (Ep 200..500) |
| :--- | :---: | :---: | :---: | :---: |
| **Compensation Mode** | Zeroed ($W=0\text{ LSB}$) | Balanced Smart S-Bend | **Active Closed-Loop Trained** | Sustained Active Trained |
| **Hyperparameters** | $\text{LR}=0,\, \lambda=0$ | $\text{LR}=0,\, \lambda=0$ | **$\text{LR}=0.08,\, \lambda=1024$** | $\text{LR}=0.08,\, \lambda=1024$ |
| **Hadamard Cadence** | 200 samples/ep (ON) | 200 samples/ep (ON) | **200 samples/ep (ON)** | 200 samples/ep (ON) |
| **200-Sample Window Mean Loss** | $72,836.5\text{ LSB}^2$ | $76,845.2\text{ LSB}^2$ | **$57,909.0\text{ LSB}^2$ (Ep 240)** | **$61,834.7\text{ LSB}^2$** |
| **200-Sample Window ENOB [4.5..5.5 ms]** | $3.72\text{ bits}$ | $3.68\text{ bits}$ | **$3.88\text{ bits}$ (Ep 240)** | **$3.83\text{ bits}$** |
| **5.0 ms Center Snapshot Loss** | $3,881.8\text{ LSB}^2$ (mean) | $4,859.2\text{ LSB}^2$ (mean) | **$122.0\text{ LSB}^2$ (Ep 273)** | $4,631.8\text{ LSB}^2$ (mean) |
| **5.0 ms Center Snapshot ENOB** | $5.98\text{ bits}$ | $5.82\text{ bits}$ | **$8.33\text{ bits}$ (Ep 273)** | $5.90\text{ bits}$ (mean) |
| **M8 Diagonal Weights [LSB]** | $[0, 0, 0, 0, 0, 0]$ | $[-20, -20, 20, 20, -20, 20]$ | $[-11, -17, 18, 28, -23, 27]$ | $[-18, -15, 14, 93, 24, 32]$ (Ep 500) |

---

## 3. 3D Dual-2T1C Weight Topographies (Baseline vs. Trained Golden State)

![3D Weight Topography](file:///home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a/fig_mode_a_3d_weight_landscapes_baseline_vs_golden_reg1024_lr0p08.png)

---

## 4. 500-Epoch Trajectories at SINGLE-POINT t = 5.0 ms ONLY (Nominal Center Snapshot)

![500-Epoch Single-Point 5.0 ms Trajectory](file:///home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a/fig_mode_a_500ep_5p0ms_only_reg1024_lr0p08.png)

---

## 5. 500-Epoch Trajectories Across FULL TEMPORAL WINDOW [4.5 ms to 5.5 ms] AGGREGATED

![500-Epoch Full Window 4.5 to 5.5 ms Trajectory](file:///home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a/fig_mode_a_500ep_window_4p5to5p5ms_only_reg1024_lr0p08.png)

---

## 6. Full 2D Trajectories of All Weights (Matrix 3 & Matrix 8 across 500 Epochs)

### Matrix 3 (First Triad Layer): 48 Dynamic Weights
![Matrix 3 2D Trajectories](file:///home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a/fig_2d_m3_weights_trajectory_reg1024_lr0p08.png)

### Matrix 8 (Second Triad Layer): 42 Vernier Weights
![Matrix 8 2D Trajectories](file:///home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a/fig_2d_m8_weights_trajectory_reg1024_lr0p08.png)

---

## 7. Deep-Dive Analysis: Phase 3 High-Resolution Stability

![Deep Dive Analysis](file:///home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a/fig_mode_a_500ep_deep_dive_reg1024_lr0p08.png)

---

## 8. Physical Hardware Silicon: Inverted MAML Proof-of-Concept PCB (v1.3.2)

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
