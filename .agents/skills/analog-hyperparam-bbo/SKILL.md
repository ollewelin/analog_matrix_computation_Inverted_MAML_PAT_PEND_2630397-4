---
name: analog-hyperparam-bbo
description: Mathematical ML hyperparameter generator and trend-curve analyzer for Inverted MAML analog bit slicing (`lr`, `l2_reg`, `momentum`, `clamp`) under physical Dual-2T1C pinch-off, ColTIA headroom, and thermal drift constraints.
---

# Analog Hyperparameter Generator & Trend-Curve Model (`Mode A`)

**Purpose:** This skill defines the mathematical physics model and offline iterative optimization loop (Bayesian / Physics-Informed Surrogate Optimization) used to propose improved hardware SGD hyperparameters $\theta = (\text{lr}, \lambda_{\text{L2}}, \beta_{\text{mom}}, C_{\text{clamp}})$ from measured **warm-phase time-series trend curves**.

> [!CAUTION]
> **STRICT HONESTY & CALIBRATION RULES:**
> 1. **Offline Parameter Generator Only:** This ML model ONLY proposes `(lr, l2_reg, momentum, clamp)` between hardware runs. It NEVER adjusts outputs, targets, or gains during a run.
> 2. **Cold Startup DC Calibration Only:** `alpha` and `beta` are fitted **once** in cold state (`Heaters OFF, W8=0`) after at least **60 seconds cooldown**, then locked permanently inside the T120 SoC. Moving digital targets are strictly forbidden.
> 3. **Warm-Phase Evaluation Only:** Cold phases already sit near `~9.4 bits` ENOB with minimal loss; convergence lift, thermal compensation, and `Training ON -> OFF` contrast are evaluated strictly in the **Warm phases** (`Heater ON`).
> 4. **Fixed Staircase Geometry:** Retain `w3_staircase_pattern.json` (`±40 LSB` clock/bias staircase on `M3` rows 6–7, `M3` cols 0–5 feeding `M8` rows 0–5, and `M8` bias row 6 fixed at `0`).

---

## 1. Coupled Discrete-Time Analog SGD & Anti-Windup Physics

Inside `maml_platform.c` (`maml_execute_strata_batch` + `maml_momentum_step_antiwindup`), weights evolve in Q1.14 (`1 LSB = 128 Q1.14`) at `K=1` (~100 ms per slice beat) according to:

$$g_{\text{step}, t} = 4 \cdot \text{lr} \cdot g_t, \qquad \gamma = \frac{\lambda_{\text{L2}}}{65536}, \qquad \beta = \text{momentum}$$

With back-calculation anti-windup and integrated L2 decay around the baseline anchor $W_{\text{null}}$:

$$v_t = \beta v_{t-1} + \eta_{\text{eff}} g_t + \gamma (w_{t-1} - w_{\text{null}}), \qquad \eta_{\text{eff}} = 4 \cdot \text{lr}$$
$$w_t = \text{clip}_{[-C, +C]}\!\left(w_{t-1} - v_t\right), \qquad v_t \leftarrow w_{t-1} - w_t \text{ (if clipped)}$$

Layer 1 data rows (`M3[0..5][0..5]`) are clamped to $\pm \max(15, \lfloor C/3 \rfloor)\text{ LSB}$ so Layer 1 never swamps the fixed $\pm 40\text{ LSB}$ staircase on `M3[6..7]` that drives `M8[0..5]`.

### Derived Physical Scaling Laws

| Quantity | Formula | Analog Physical Meaning |
| :--- | :--- | :--- |
| **Momentum Time Constant** | $\tau_{\text{mom}} = \frac{1}{1 - \beta}$ beats | At $\beta=0.80$: $5$ beats ($\approx 1.0\text{ s}$); at $\beta=0.90$: $10$ beats ($\approx 2.0\text{ s}$); at $\beta=0.94$: $16.7$ beats ($\approx 3.3\text{ s}$). |
| **Effective DC Gain** | $G_{\text{eff}} = \frac{\eta_{\text{eff}}}{1 - \beta}$ | Steady-state responsiveness to slow thermal drift gradients $\bar{g}_{\text{therm}}$. |
| **L2 Equilibrium Swing** | $W_{\text{eq}}(\bar{g}) = \min\!\left(C, \, \frac{\eta_{\text{eff}} |\bar{g}|}{(1 - \beta)\gamma + \epsilon}\right)$ or $\frac{\eta_{\text{eff}} |\bar{g}|}{\gamma}$ (stationary) | Balance point between bias drift force and L2 anchor. If $\lambda_{\text{L2}}$ is too high, weights cannot reach the needed compensation current; if too low, weights park on $\pm C$ and recover slowly. |
| **Whitenoise Variance Gain** | $N_{\text{amp}} = \frac{\eta_{\text{eff}}}{\sqrt{1 - \beta^2}}$ | Amplification of single-vector (`K=1`) stochastic white-noise gradient jitter onto DAC weights and ENOB variance. |
| **Subthreshold Pinch-Off Boundary** | $C \lesssim 80\text{--}82\text{ LSB}$ | Empirically measured Dual-2T1C cell (`M33/M8`) peaks near $|W| \approx 80\text{ LSB}$; beyond $\sim 85\text{ LSB}$ subthreshold pinch-off rolls gain down ($\partial V_{\text{out}}/\partial W \le 0$). |

---

## 2. Trend-Curve Feature Extraction (Input to the ML Generator)

From each run JSON (`FPGA_code/logs/bit_slicing/*.json`), the model extracts warm-phase (`heater_on == True`) trend curves:

1. **Warm ON Transient & Settled Convergence Trend (`conv_lift`, `conv_slope_late`, `loss_ratio`)**:
   - Splits each `Warm / Regler ON` phase into initial transient (`0..15%`, right after switching from OFF or heating onset) and settled compensation (`25%..100%`).
   - Fits a smoothed 15-pair rolling trend curve: verifies that **after the initial transient**, ENOB rises (or climbs relative to the preceding `Warm OFF` end) and stays stably elevated, while Loss decreases.
2. **Warm OFF Decay Trend (`off_decay_slope`, `off_drop`)**:
   - Fits linear regression of `combined_enob_raw` across `Warm / Regler OFF` (`W8 = 0`), verifying monotonic degradation under heating and zero weight leaks (`w8 == [0, 0]`).
3. **Warm Step Contrast (`step_up_on`, `step_down_off`, `warm_delta_enob`)**:
   - Measures the true ON-vs-OFF delta between hot phases:
     - `step_up_on = ENOB(P5_late) - ENOB(P4_late)`
     - `step_down_off = ENOB(P5_late) - ENOB(P6_mean)`
     - `warm_loss_ratio = mean(Loss_Warm_OFF) / mean(Loss_Warm_ON)`
4. **Anti-Windup & Clamp Recovery Health (`clamp_hit_frac`, `clamp_recovery_rate`, `clip_per_phase`)**:
   - Tracks whenever `max(|W8|) >= clamp - 1` and counts how many of those rail-touch events cleanly unpin back inside `clamp - 3` (anti-windup recovery vs permanently pinned).
5. **Trend Jitter (`jitter_std`)**:
   - Standard deviation of high-frequency residuals (`raw_enob - rolling_trend(15)`) in `Warm ON`.

### Scalar Composite Objective $J(\theta)$

$$J(\theta) = 1.5 \cdot \overline{\Delta\text{ENOB}}_{\text{step (ON-OFF)}} + 1.0 \cdot \log_2\!\left(\frac{\mathcal{L}_{\text{OFF}}}{\mathcal{L}_{\text{ON}}}\right) + 1.2 \cdot \Delta\text{ENOB}_{\text{conv (P5 late - P5 start)}} + 0.5 \cdot \text{RecoveryRate} - 1.2 \cdot \sigma_{\text{jitter}} - 0.8 \cdot f_{\text{pinned}} - 0.02 \cdot N_{\text{clips}}$$

---

## 3. Iterative 5-Round Parameter Generation Loop

1. Cool down hardware for **60 s** (`--cooldown-sec 60`, Heaters OFF).
2. Run warm-focused evaluation (`--cold-phase-duration 0.25 --phase-duration 1.0 --warm-phases 4 --cool-phases 0 --heater-duty-pct 40 --k-batch 1`).
3. Feed all completed round logs into `FPGA_code/scripts/analog_hyperparam_model.py`:
   ```bash
   /home/olle/anaconda3/bin/python FPGA_code/scripts/analog_hyperparam_model.py \
       --logs log_r1.json [log_r2.json ...] --round-idx <next_round>
   ```
4. The generator combines:
   - **Physics-Space Gaussian Process Surrogate** over standardized `[log(lr), log(l2_reg), log(1/(1-mom)), clamp, log(G_eff), log(N_amp)]` maximizing UCB (`mu + kappa * sigma`) across a constrained candidate grid (`lr in [0.015..0.06]`, `l2_reg in [512..3072]`, `mom in [0.75..0.94]`, `clamp in [65..82]`), and
   - **Trend-Curve Physics Corrections** (damping `lr`/`mom` if `jitter_std` spikes, reducing `l2_reg` or nudging `clamp` within pinch-off limits if compensation saturates below drift, raising `l2_reg` if `recovery_ratio < 0.3`).
5. After 5 rounds, select the highest-scoring verified configuration (`--select-best`) and validate with a full 13-minute (`6 x 2.0 min Warm`) thermal run.
