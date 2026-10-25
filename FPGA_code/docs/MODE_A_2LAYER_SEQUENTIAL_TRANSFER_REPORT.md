# Inverted MAML: Atomic Triad 2-Layer Wakeup, Equations 4 & 7 Resolution, Sequential Transfer & 3D Telemetry Studio

**Document Reference:** `INVERTED-MAML-MODE-A-2LAYER-REPORT-V1`  
**Patent Pending:** SE 2630397-4 (Priority: 2026-06-03)  
**Inventor:** Olle Welin  
**Date:** October 25, 2026  
**Hardware Platforms:** Efinix Trion T120F324 Master SoC + Trion T20F256 Coprocessor (`192.168.1.50:5000`)  
**Operating Mode:** Mode A (Jumper ON, Active 2-Layer Compensation via $M_3$ and $M_8$)  
**Status:** Silicon Verified on Physical Hardware  

---

## 1. Executive Summary & Hardware Status

On October 25, 2026, the Inverted MAML Analog In-Memory Computing (AIMC) platform achieved full closed-loop 2-layer neural network adaptation in physical silicon across all 6 columns simultaneously ($36$ crosspoints in $M_{33}$, $48$ cells in $M_3$, and $42$ cells in $M_8$). Layer 1 (Matrix 3, $8\\times 6$) and Layer 2 (Matrix 8, $7\\times 6$) now adapt synchronously via intermediate BJT Sigmoid 10 and differential ColTIA transimpedance amplifiers.

A critical fixed-point mathematical bug in Equations 4 & 7 (which divided Layer 1 weight gradients by $32\\,768$) was discovered and resolved in `FPGA_code/sw/t120_master/src/maml_platform.c`. The corrected firmware was compiled, verified, and flashed to the T120 SoC via JTAG in 14.3 seconds using `flash_soc.py`.

Subsequent physical measurements on silicon verified:
1. **Monotonic 2-Layer Convergence:** 10-step silicon verification demonstrated rapid error descent: RMSE dropped from $78.75\\text{ LSB} \\to 26.31\\text{ LSB}$ ($4.70\\text{ b} \\to 6.28\\text{ bits}$ ENOB) in just 6 steps, with $M_3$ adapting dynamically by $-1\\text{ to }-12\\text{ LSB}$ per cell.
2. **True Continuous 40+40 Sequential Task Transfer:** An 80-epoch experiment across the $4.90\\text{ to }5.10\\text{ ms}$ multi-stratum window (Vector A for 40 epochs $\\to$ Vector B for 40 epochs with strictly preserved weights) proved that the 2-layer landscape **does NOT flip inside out**: Matrix 3 maintained a strong positive topographical correlation of **$r = +0.7401$** and Matrix 8 maintained **$r = +0.3967$**, while lifting nominal 5.0ms precision to **$6.70\\text{ bits}$ ENOB ($19.64\\text{ LSB}$ RMSE)** on Vector B.

---

## 2. Forensic Diagnosis: Why Matrix 3 Remained Stationary

Prior to this date, Matrix 8 adapted effectively, but Matrix 3 remained stationary at baseline with zero delta ($\\Delta W_3 \\equiv 0$). Audit of `maml_platform.c` pinpointed the root cause:

| Signal Path / Equation | Original Code (Underflow Bug) | Resolved Code (Physical Silicon Verified) |
|:---|:---|:---|
| **Equation 2 (Matrix 8 Gradient)** | `prod = sens_m8 * (-err49)`<br/>`grad_m8 = sat_q14(prod >> 1)` | *Unchanged:* Divides by 2, healthy gradient ~300 |
| **Equation 4 (Backprop to Layer 1)** | `dx8[i] = rshift_rne(sum, 8);`<br/>*Divides 6-col error sum by 256!* | `col_term = (sigma2 * err49) >> 14;`<br/>`dx8[i] = rshift_rne(sum, 6);` *(Fan-in >> 6)* |
| **Equation 7 (Matrix 3 Gradient)** | `prod = sens_m3 * dx8;`<br/>`grad_m3 = sat_q14(prod >> 7);`<br/>*Divides -60 by 128 &rarr; **EXACT 0!*** | `prod = sens_m3 * dx8;`<br/>`grad_m3 = sat_q14(prod >> 3);` *(Divides by 8)* |
| **Cascade Polarity** | Used `-err49[j]` in Eq. 4 &rarr; *Positive feedback* | Corrected to `+err49[j]` in Eq. 4 &rarr; *Negative feedback* |

Because `sens_m3` is $\\approx 15\\text{ LSB}$ and `dx8` was shrunken to $-4$, the product `sens_m3 * dx8` was $\\approx -60$. Shifting right by `>> 7` (dividing by 128) in integer arithmetic rounded the gradient to **exact zero (`0`)**, preventing Matrix 3 from adapting.

---

## 3. Physical Silicon Verification & Sequential Transfer Metrics

### 10-Step Rapid Verification (5.0 ms Nominal Delay)
- **Step 0 (Baseline):** RMSE = $78.75\\text{ LSB}$ (ENOB $4.70\\text{ b}$), `ADC_45` = `[+578.5, +479.5, +324.0, +172.5, +1156.0, +612.0]`
- **Step 1:** RMSE = $65.58\\text{ LSB}$ (ENOB $4.96\\text{ b}$)
- **Step 2:** RMSE = $59.89\\text{ LSB}$ (ENOB $5.10\\text{ b}$)
- **Step 4:** RMSE = $46.94\\text{ LSB}$ (ENOB $5.45\\text{ b}$)
- **Step 6 (Peak):** RMSE = **$26.31\\text{ LSB}$ (ENOB $6.28\\text{ b}$)**, `ADC_45` = `[+385.5, +441.5, +298.5, +116.0, +1127.5, +399.0]`
- **Matrix 3 Learned Deltas (Row 0..5):** Individual cell adaptations ranged from $-1\\text{ to }-12\\text{ LSB}$, actively driving `ADC_45` in lockstep with Matrix 8.

### 40 + 40 Sequential Transfer Results
- **Phase 1 (Vector A, Epochs 0..40):** Baseline RMSE $83.66\\text{ LSB} \\to$ Peak **$20.75\\text{ LSB}$ ($6.63\\text{ bits}$ ENOB)** at Epoch 30.
- **Transition Point (Epoch 40 &rarr; 41):** Fresh locked Vector B drawn via `MAML_CMD_RAND_DATA` payload 2. Weights strictly preserved.
- **Phase 2 (Vector B, Epochs 41..80):** Initial RMSE $58.50\\text{ LSB} \\to$ Peak **$19.64\\text{ LSB}$ ($6.70\\text{ bits}$ ENOB)** at Epoch 80.
- **Topographical Correlation (Active 6x6 Cells):**
  - **Matrix 3:** **$r = +0.7401$** (Shared physical silicon geometry preserved across different tasks!)
  - **Matrix 8:** **$r = +0.3967$** (Vernier layer adapts smoothly without flipping inside out!)

---

## 4. Visualizations from the 3D Telemetry Studio

![Sequential Transfer Studio](figures/fig_mode_a_sequential_transfer_studio.png)

*Figure 1: Inverted MAML Post-Analysis Studio displaying 40+40 sequential task transfer. Left: Matrix 8 3D surface at Epoch 14. Top right: Quadratic loss descent for Vector A and continuous re-convergence for Vector B across the Epoch 40 transition boundary. Middle right: RMSE / ENOB curves. Bottom right: Smooth 6-column $W_8$ diagonal trajectory across the task boundary.*

![Matrix 3 3D Topography Studio](figures/fig_mode_a_matrix3_3d_topography.png)

*Figure 2: Matrix 3 (Layer 1 Projection / Hidden Layer) 3D Topography Studio at Epoch 60. Left: Learned $\\Delta W_3$ adaptation surface relative to baseline ($0\\text{ LSB}$), revealing autonomous spatial feature hills and valleys. Right: Absolute $W_3$ surface showing the $+64\\text{ LSB}$ diagonal pass-through ridges and row 6/7 bias pedestals.*

---

## 5. Strategic Engineering Roadmap

1. **Hardware Summing Attenuator Scaling ($1\\text{ k}\\Omega / 10\\text{ k}\\Omega \\text{--} 20\\text{ k}\\Omega$):**
   The current $1\\text{ k}\\Omega / 3.9\\text{ k}\\Omega$ attenuator provides $20.4\\%$ authority ($\\pm 100\\text{ LSB}$). Increasing the resistor to $10\\text{ k}\\Omega$ or $15\\text{ k}\\Omega$ scales authority to $6.2\\%\\text{--}9.1\\%$ ($\\pm 30\\text{--}50\\text{ LSB}$), delivering $2.5\\times$ finer Vernier resolution and $\\approx 8\\text{ dB}$ noise floor reduction.
2. **Software Multi-Vector Mini-Batching:**
   To permanently prevent catastrophic forgetting on arbitrary input vectors, the inner loop will be upgraded to sample gradients over a mini-batch of $K = 4\\text{--}8$ diverse vectors before updating weights. This compels the 2-layer network to extract a universal, input-invariant non-linear compensation surface.
