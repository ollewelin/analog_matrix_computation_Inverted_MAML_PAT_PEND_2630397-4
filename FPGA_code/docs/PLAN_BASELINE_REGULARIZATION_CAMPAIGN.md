# Inverted MAML: Action Plan & Roadmap for Baseline Regularization
**Date:** 2026-10-29  
**Target:** Trion T120 Master SoC (192.168.1.50:5000) on PCB v1.3.2 (Summing attenuator: 1k / 5.1k Ohm installed)  
**Patent Pending:** SE 2630397-4 (Open Science Hardware)  

---

## 1. Context & Motivation
Under the landmark 3-stage 500-epoch benchmark executed on October 29, 2026, initializing the analog matrix at the experimentally determined optimal S-curve knee baseline:
$$\mathbf{W}_{\text{baseline}} = [-16, -16, +16, +16, -16, +16]\text{ LSB}$$
immediately primed both Layer 1 ($M_3 \to \text{ColTIA} \to \text{Sigmoid 4}$) and Layer 2 ($M_8 \to \text{ColTIA} \to \text{Sigmoid 10}$) at their highest transconductance sensitivity point ($43\dots 58\text{ LSB/W}$). This yielded:
- **36.0% lower average loss** ($17\,269.7\text{ LSB}^2$).
- **Peak analog computational resolution:** **$7.90\text{ bits}$ ENOB** ($221.1\text{ LSB}^2$ quadratic loss, RMSE $8.59\text{ LSB}$) at Epoch 427 without artificial digital seeding (`seed_pct = 0`).

### The Objective for Tomorrow:
During extended continuous runs across thousands of rotating arbitrary vectors, unregularized weights can slowly accumulate DC drift, drifting away from the high-sensitivity knee toward the compressed outer margins ($\pm 60\dots \pm 120\text{ LSB}$).
By applying an L2 weight decay pulling weights back toward $\mathbf{W}_{\text{baseline}}$:
$$\Delta W_i = -\eta \cdot g_i - \lambda_{\text{reg}} \cdot (W_i - W_{\text{baseline}, i})$$
the network acquires an autonomous "rubber band attractor", preventing saturation and forcing the matrices to converge on a universal, vector-invariant compensation manifold.

---

## 2. Technical Architecture & Control via Telemetry

### A. Dynamic Telemetry Control (On/Off & Variable $\lambda$)
We will configure the outer-loop stepping command (`MAML_CMD_STEP_OUTER` / `MAML_CMD_BATCH_STEP` / `MAML_CMD_SET_CONFIG`) to dynamically accept:
1. `reg_lambda_q16`: L2 decay strength ($0 = \text{OFF}$, $64\dots 1024$ for variable stiffness).
2. `reg_target_mode`:
   - `0`: Off ($\lambda = 0$).
   - `1`: Pull toward $\mathbf{W}_{\text{baseline}} = [-16, -16, +16, +16, -16, +16]\text{ LSB}$ on $M_3$ only.
   - `2`: Pull toward $\mathbf{W}_{\text{baseline}}$ on **both** $M_3$ and $M_8$.
   - `3`: Legacy pull toward zero ($W = 0$).

### B. Firmware Implementation Details (`maml_platform.c`)
- Update `maml_platform.c` so that in `MAML_CMD_STEP_ONCE` (0x18) as well as batch mode:
  ```c
  /* L2 weight-decay toward calibrated S-curve knee baseline */
  if (g_reg_lambda_q16 > 0u) {
      int32_t decay_m3 = rshift_rne(((int32_t)g_w_m3_q14[r][c] - maml_wbase_m3_q14(r, c)) * (int32_t)g_reg_lambda_q16, 16);
      g_w_m3_q14[r][c] = sat_comp_w_q14((int32_t)g_w_m3_q14[r][c] - step_w - decay_m3);
      
      if (g_reg_m8_enabled) {
          int32_t decay_m8 = rshift_rne(((int32_t)g_w_m8_q14[r][c] - maml_wbase_m8_q14(r, c)) * (int32_t)g_reg_lambda_q16, 16);
          g_w_m8_q14[r][c] = sat_comp_w_q14((int32_t)g_w_m8_q14[r][c] - step_w - decay_m8);
      }
  }
  ```
- Expose `g_reg_lambda_q16` and `g_reg_m8_enabled` in `g_tel` shadow bytes for real-time verification.

---

## 3. Systematic Evaluation Protocol (Multi-Run 500-Epoch Campaign)

To rigorously determine the optimal regularization strategy, we will execute an automated sequence of **500-epoch runs on physical silicon** under identical conditions (rotating arbitrary white-noise vectors, `seed_pct = 0`, LEDs ON):

1. **Run Suite 1: Unregularized Reference ($\lambda = 0$)**
   - 3 consecutive 500-epoch runs with $\lambda = 0$ as control baseline.
   - Measure mean loss, peak ENOB, and total weight drift $\Delta W$ from baseline.

2. **Run Suite 2: Light Regularization ($\lambda = 64 \approx 0.001$)**
   - 3 consecutive 500-epoch runs with $\lambda = 64$ pulling toward $\mathbf{W}_{\text{baseline}}$ on $M_3$.
   - Evaluate stability and check if peak ENOB ($7.90\text{ b}$) is preserved or improved.

3. **Run Suite 3: Medium Regularization ($\lambda = 256 \approx 0.004$)**
   - 3 consecutive 500-epoch runs testing higher attractor stiffness.
   - Verify whether weight spread stays within $[-25, +25]\text{ LSB}$.

4. **Run Suite 4: Dual-Matrix Regularization ($M_3 + M_8$)**
   - Evaluate pulling both $M_3$ and $M_8$ toward $\mathbf{W}_{\text{baseline}}$ vs. keeping $M_8$ free.

---

## 4. Deliverables for Tomorrow
1. Updated C firmware with dynamic runtime telemetry control of $\lambda_{\text{reg}}$ and attractor targets.
2. CLI and Python script support (`--reg-lambda`, `--reg-m8`) in `run_3stage_baseline_experiment.py` and `run_fixed_vector_gui_experiment.py`.
3. Automated comparative test script executing the multi-run campaign.
4. Aggregated statistical report with boxplots and trajectory overlays comparing unregularized vs. regularized performance.

