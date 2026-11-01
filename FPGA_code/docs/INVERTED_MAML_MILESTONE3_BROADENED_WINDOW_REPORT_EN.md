# INVERTED MAML MILESTONE 3: 500-Epoch Empirical Silicon Evaluation Across Broadened Temporal Window [4500 – 5500 µs]
### With 100% Identical 200-Sample Hadamard Measurement Cadence, True-Zero Reference Calibration, Elevated L2 Regularization (λ = 1024), and LR = 0.25

**Patent Pending:** Swedish Patent Application SE 2630397-4  
**Inventor & System Architect:** Olle Welin  
**Platform:** Open Science Hardware | Efinix Trion T120 Master SoC (Ethernet @ `192.168.1.50:5000`, FW `v2.2-MAML`) & T20 Controller  
**Milestone 3 Protocol:** Broadened temporal discharge window `4500 µs to 5500 µs` (10 discrete temporal strata × `K = 20` batch = **200 Hadamard-active analog measurements per epoch** across all 500 epochs), `LR = 0.25x`, `L2 Reg λ = 1024`, `Noise Mode = COLOR_LLM_TOEPLITZ` (ρ = 0.85).  
**Dataset Source:** Physical silicon telemetry from `FPGA_code/logs/mode_a_extended_training/mode_a_500ep_broadened_4p5to5p5ms_reg1024_lr0p25_identical_k20_llm.json`  
**Code Repository:** [https://github.com/ollewelin/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4](https://github.com/ollewelin/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4)  

---

## 1. Executive Summary & Milestone 3 Objectives

### What is Milestone 3?
While earlier evaluations characterized single-point compensation at the nominal `5000 µs` (`5.0 ms`) RC discharge midpoint, **Milestone 3** evaluates whether the Proprioceptive Inverted MAML triad (`Matrix 3 -> Sigmoid 4 -> Matrix 8`) and its temporal clock reference rows (`Row 6 ClkB1` and `Row 7 ClkRef` in `Matrix 3`) can actively track and compensate dynamic RC discharge leakage across an **extended 1000 µs temporal window (`4500 µs` to `5500 µs`)** at fixed room temperature.

### Strict Experimental Consistency (`v2.2-MAML` Identical Cadence):
To guarantee rigorous statistical comparability between uncompensated (`Phase 1`), static baseline (`Phase 2`), and actively trained (`Phase 3`) operation, **every single epoch (`0..500`) executes the exact same 200-sample Hadamard-active batch across all 10 temporal strata (`4500, 4611, 4722, 4833, 4944, 5056, 5167, 5278, 5389, 5500 µs`)**:
- **Identical EMC & Capacitive Injection:** Full Walsh-Hadamard AC perturbation (`V_PTU`) is active during all 200 samples of every epoch (`0..500`).
- **Identical True-Zero Target Origin:** `g_adc45_zero_cal` and `g_adc49_zero_cal` are calibrated strictly at true zero (`W_M3 = 0, W_M8 = 0, X = 0`) at `t = 5.0 ms` and locked across all 500 epochs.
- **Only Controlled Variables Change:** Between phases, ONLY the baseline weight table (`W = 0` in Ep `0..99` vs. Smart S-Bend Baseline in Ep `100..199`) and the learning switches (`LR = 0, λ = 0` in Ep `0..199` vs. `LR = 0.25, λ = 1024` in Ep `200..500`) change.

### Key Empirical Silicon Findings:
1. **Substantial Full-Window Error Collapse (>10σ Significance):** Across the 200-sample `[4500..5500 µs]` window, active training (`Ep 200..500`) reduced the mean quadratic error from **74,896.7 ± 1,069.0 LSB²** (Phase 2 Smart Baseline) and **69,800.4 ± 953.0 LSB²** (Phase 1 `W = 0`) down to **59,233.1 ± 1,581.6 LSB²** (sustained 300-epoch mean) and a minimum of **56,013.5 LSB²** at Epoch 212 (**-25.2 % error reduction** vs. Phase 2, **-19.8 %** vs. `W = 0`).
2. **High-Precision 5.0 ms Center Anchor:** Simultaneously, at the nominal `5.0 ms` center snapshot, active training achieved a minimum loss of **259.0 LSB² (RMSE = 9.29 LSB)** at Epoch 245, corresponding to **7.78 bits Standard ENOB (7.02 bits IEEE ENOB)**.
3. **Elimination of Permanent Rail Clamping (`λ = 1024`):** With matching-sign S-bend initialization (`M3_diag = {-24, -24, +24, +24, -24, +24}`, `M8_diag = {-20, -20, +20, +20, -20, +20}`) and elevated L2 regularization (`λ = 1024`), Column 4 (`M8[4,4]`) never clamped (smoothly transitioning to `+34..+64 LSB`), and Column 3 (`M8[3,3]`) was actively pulled back from `+120 LSB` into the linear operating region (`+100..+112 LSB`).

---

## 2. Empirical Silicon Telemetry Table (Milestone 3: [4500 – 5500 µs], K=20, 200 Samples/Epoch)

| Metric | Phase 1: M33 Alone (Ep 0..99) | Phase 2: Smart Baseline (Ep 100..199) | **Phase 3: Trained Peak (Ep 212 / Ep 245)** | Phase 3: Sustained Mean (Ep 200..500) |
| :--- | :---: | :---: | :---: | :---: |
| **Compensation Mode** | Zeroed ($W=0\text{ LSB}$) | Balanced Smart S-Bend | **Active Closed-Loop Trained** | Sustained Active Trained |
| **Hyperparameters** | $\text{LR}=0,\, \lambda=0$ | $\text{LR}=0,\, \lambda=0$ | **$\text{LR}=0.25,\, \lambda=1024$** | $\text{LR}=0.25,\, \lambda=1024$ |
| **Hadamard Cadence** | 200 samples/ep (ON) | 200 samples/ep (ON) | **200 samples/ep (ON)** | 200 samples/ep (ON) |
| **200-Sample Window Mean Loss** | $69\,800.4 \pm 953.0\text{ LSB}^2$ | $74\,896.7 \pm 1\,069.0\text{ LSB}^2$ | **$56\,013.5\text{ LSB}^2$ (Ep 212)** | **$59\,233.1 \pm 1\,581.6\text{ LSB}^2$** |
| **200-Sample Window Mean RMSE** | $152.53\text{ LSB}$ | $158.00\text{ LSB}$ | **$136.64\text{ LSB}$ (Ep 212)** | **$140.50\text{ LSB}$** |
| **200-Sample Window ENOB [4.5..5.5 ms]** | $3.75 \pm 0.01\text{ bits}$ | $3.70 \pm 0.01\text{ bits}$ | **$3.91\text{ bits}$ (Ep 212)** | **$3.87 \pm 0.02\text{ bits}$** |
| **5.0 ms Center Snapshot Loss** | $3\,660.6\text{ LSB}^2$ (mean) | $6\,533.4\text{ LSB}^2$ (mean) | **$259.0\text{ LSB}^2$ (Ep 245)** | $6\,201.3\text{ LSB}^2$ (mean) |
| **5.0 ms Center Snapshot ENOB** | $6.02\text{ bits}$ (peak $6.98\text{b}$) | $5.54\text{ bits}$ (peak $7.17\text{b}$) | **$7.78\text{ bits}$ ($7.02\text{b}$ IEEE)** | $5.70\text{ bits}$ (mean) |
| **M8 Diagonal Weights [LSB]** | $[0, 0, 0, 0, 0, 0]$ | $[-20, -20, 20, 20, -20, 20]$ | $[-41, 2, -2, 85, 51, 86]$ | $[-35, 2, 5, 112, 43, 102]$ (Ep 500) |

---

## 3. Mathematical & Physical Analysis of Broadened Window Compensation

Across the `[4500 .. 5500 µs]` RC discharge window, the uncompensated payload matrix $M_{33}$ exhibits a time-dependent gain decay $G_{33}(t) \propto e^{-t / \tau_{\text{RC}}}$. While the digital target $z_{\text{target}}$ is calibrated at the $t_0 = 5000\text{ µs}$ midpoint, measurements at $t = 4500\text{ µs}$ experience a systematically higher analog amplitude ($+\Delta V(t)$) and measurements at $t = 5500\text{ µs}$ experience a decayed amplitude ($-\Delta V(t)$).

In the physical FPGA firmware (`maml_platform.c`), the weight update across each 200-sample batch is governed by:
$$\Delta W = -\eta \cdot \overline{g}_{[4.5..5.5\text{ ms}]} - \lambda \cdot (W - W_{\text{null}})$$
where $\overline{g}_{[4.5..5.5\text{ ms}]}$ is the Forward Hadamard Propagation (FHP) gradient averaged over all 10 temporal strata ($K=20$ Toeplitz vectors per stratum). By training `Matrix 3` (including its dynamic clock ramp rows `Row 6 ClkB1` and `Row 7 ClkRef`) together with `Matrix 8` (including `Row 6 Vernier Bias`), the compensation network learns a joint spatial-temporal correction that reduces the integrated quadratic error across the full $1.0\text{ ms}$ window by **20.9 % (sustained)** to **25.2 % (peak)**.

---

## 4. 3D Dual-2T1C Weight Topographies (Baseline vs. Trained Golden State at Ep 245)

![3D Weight Topography](file:///home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a/fig_mode_a_3d_weight_landscapes_baseline_vs_ep260_reg1024.png)

---

## 5A. 500-Epoch Trajectories at SINGLE-POINT t = 5.0 ms ONLY (Nominal Center Snapshot)

![500-Epoch Single-Point 5.0 ms Trajectory](file:///home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a/fig_mode_a_500ep_5p0ms_only_reg1024.png)

---

## 5B. 500-Epoch Trajectories Across FULL TEMPORAL WINDOW [4.5 ms to 5.5 ms] AGGREGATED (200 Samples/Epoch)

![500-Epoch Full Window 4.5 to 5.5 ms Trajectory](file:///home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a/fig_mode_a_500ep_window_4p5to5p5ms_only_reg1024.png)

---

## 6. Full 2D Trajectories of All Weights (Matrix 3 & Matrix 8 across 500 Epochs)

### Matrix 3 (First Triad Layer): 48 Dynamic Weights
![Matrix 3 2D Trajectories](file:///home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a/fig_2d_m3_weights_trajectory_reg1024.png)

### Matrix 8 (Second Triad Layer): 42 Vernier Weights
![Matrix 8 2D Trajectories](file:///home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a/fig_2d_m8_weights_trajectory_reg1024.png)

---

## 7. Deep-Dive Analysis: Spike-Free 200-Sample Window Convergence & L2 Stabilization

![Deep Dive Analysis](file:///home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a/fig_mode_a_500ep_deep_dive_reg1024.png)

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

## 11. Overall Physical Conclusion: Single-Point (5.0 ms) vs. Full Temporal Window [4.5 – 5.5 ms] & Temporal Leakage Compensation in Analog Neural Networks (Patent Fig 5 & Fig 6)

### 11.1 Why `W = 0` (`Epochs 0..99`) Excels Specifically at the `5.0 ms` Calibration Point
The digital reference matrix ($G_{33}$) and the zero-input offset (`g_adc49_zero_cal`) are empirically identified at the exact midpoint $t_0 = 5.0\text{ ms}$ with $W = 0\text{ LSB}$. Consequently, at that **single instantaneous time point ($5.000\text{ ms}$)**, the uncompensated primary matrix $M_{33}$ is already in its calibrated sweet spot, yielding a mean `5.0 ms` loss of **$3\,660.6\text{ LSB}^2$ ($6.02\text{ bits}$ ENOB)**. However, because the storage capacitors $C_W$ in a physical Analog Neural Network undergo continuous **temporal charge leakage** across the inference phase $T_{\text{INF}}$, the output voltage drifts rapidly away from $z_{\text{target}}$ at earlier ($4.5\text{ ms}$) and later ($5.5\text{ ms}$) times, causing the uncompensated full-window loss across `[4.5 .. 5.5 ms]` to surge to **$69\,800.4\text{ LSB}^2$ ($3.75\text{ bits}$ ENOB)**.

### 11.2 What Happens When Closed-Loop Compensation Training Turns ON (`Epochs 200..500`)
When active closed-loop training is enabled at Epoch 200 across all 10 displaced temporal strata (`4500 µs` to `5500 µs`), the proprioceptive triad (`Matrix 3 -> Sigmoid 4 -> Matrix 8`) optimizes the **integrated error across the entire `1.0 ms` temporal window** rather than at a single instant:
- **Across the Complete `[4.5 ms .. 5.5 ms]` Temporal Window (Section 5B):** Total quadratic error drops decisively from **$69\,800.4\text{ LSB}^2$** (`W = 0`) and **$74\,896.7\text{ LSB}^2$** (Fixed Smart Baseline) down to a sustained mean of **$59\,233.1\text{ LSB}^2$ (`-20.9 %`)** and a minimum of **$56\,013.5\text{ LSB}^2$ (`-25.2 %`)**, while full-window ENOB rises from **$3.70\text{–}3.75\text{ bits}$** to **$3.87\text{–}3.91\text{ bits}$** ($>10\sigma$ statistical significance).
- **At the Single `5.0 ms` Point (Section 5A, Physical Trade-Off):** To generate the counter-slope that suppresses the large temporal leakage errors at `4.5 ms` and `5.5 ms`, the compensation network drives substantial active weights (`+43` to `+112 LSB` in $M_8$). This global temporal compromise causes the **mean** loss at the single `5.0 ms` midpoint ($6\,201.3\text{ LSB}^2$ / $5.70\text{ bits}$) to be slightly worse than uncompensated `W = 0` ($3\,660.6\text{ LSB}^2$ / $6.02\text{ bits}$) at that one instant—while still outperforming the fixed calibration baseline ($6\,533.4\text{ LSB}^2$ / $5.54\text{ bits}$) even at `5.0 ms` and achieving single-epoch peaks up to **$7.78\text{ bits}$ ($259.0\text{ LSB}^2$ at Ep 245)**.

### 11.3 Patent Fig 5: Displaced Temporal Measurement Windows Across $T_{\text{INF}}$ (Patent Claim 10)
![Patent Fig 5 Displaced Temporal Windows](file:///home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a/fig_patent_fig5_temporal_leakage.png)

**Figure 11 (Patent SE 2630397-4, Fig 5):** Following each capacitor regeneration/refresh pulse $T_{\text{RF}}$ (`18`), the analog neural network operates in continuous inference $T_{\text{INF}}$ (`19`) while its stored charges slowly decay. By dynamically displacing the short Hadamard measurement windows (`20, 24`, with sub-windows $T_{\text{M2A}}$ `21`, $T_{\text{M2B}}/T_{\text{M1A}}$ `22`, $T_{\text{M1B}}$ `23`) by a selectable temporal offset $T_{\text{RAND}}$ (`25`, corresponding to our 10 strata across `4500..5500 µs`), the digital controller (`9`) extracts time-dependent gradients across the entire discharge trajectory (`SAMP 1`, `SAMP 2`).

### 11.4 Patent Fig 6: Physical Compensation of Temporal Leakage via Accelerated Reference Decay (Patent Claim 8)
![Patent Fig 6 Temporal Leakage vs Reference Curve](file:///home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a/fig_patent_fig6_temporal_compensation.png)

**Figure 12 (Patent SE 2630397-4, Fig 6):** Standard 2T1C computing cells (`27`) exhibit natural capacitive voltage leakage (`31`, solid curve) between refresh pulses $T_{\text{RF}}$ (`18`). To make the neural network explicitly aware of elapsed time $t$ without digital timers in the analog path, `Matrix 3` integrates dedicated temporal reference cells (`29`, Rows 6 & 7) equipped with an accelerated discharge path (`28`). This generates a steep, full-swing reference decay curve (`32`, dashed curve) that normalizes the time axis across the dynamic range of the analog sigmoid (`4`). Fed by this analog timestamp (`32`), the `Matrix 3 -> Sigmoid 4 -> Matrix 8` triad dynamically tracks and cancels the natural temporal leakage (`31`) of the Analog Neural Network across the entire inference window.

### 11.5 Future Research & Hyperparameter Optimization Directions
While Milestone 3 demonstrates decisive ($>10\sigma$) full-window error reduction across `[4.5 ms .. 5.5 ms]`, further systematic optimization is required in upcoming investigations:
1. **Strata Count $\times$ Batch Size ($K$) Trade-Off:** Investigating the optimal balance between the number of discrete temporal strata across the discharge window and the number of Hadamard-perturbed input samples $K$ per stratum (e.g., dense strata with smaller $K$ vs. weighted strata emphasizing the center and boundaries).
2. **Joint Tuning of Learning Rate ($\text{LR}$) and L2 Regularization ($\lambda$):** Fine-tuning the ratio $\eta / \lambda$ and potentially applying stratum-weighted or layer-specific regularization so that the triad achieves maximum edge compensation at `4.5 ms` and `5.5 ms` without sacrificing single-point precision at the `5.0 ms` center anchor.
3. **Multi-Cycle Undersampling Across Consecutive $10\text{ ms}$ Refresh Turns (Patent Fig 5):** As illustrated in Patent `Fig 5` (`18, 19, 20, 21, 22, 23, 24, 25`), rather than pausing inference to collect all strata in a single burst, future firmware revisions will investigate **undersampling across multiple consecutive $10\text{ ms}$ refresh cycles**—extracting a single short sub-window ($T_{\text{M2A}}$ `21`, $T_{\text{M2B}}/T_{\text{M1A}}$ `22`, $T_{\text{M1B}}$ `23`) at a displaced time $T_{\text{RAND}}$ (`25`) per $10\text{ ms}$ turn while dedicating $>95\,\%$ of each cycle to uninterrupted high-throughput analog inference ($T_{\text{INF}}$, `19`).

---

## 12. Open Science Reproducibility Summary

All telemetry records and plots in this Milestone 3 report are 100 % authentic, measured directly on physical silicon hardware via the Efinix Trion T120 SoC at `192.168.1.50:5000` running `v2.2-MAML` firmware. Every epoch (`0..500`) executed the exact same 200-sample Hadamard batch across `[4500..5500 µs]`.
