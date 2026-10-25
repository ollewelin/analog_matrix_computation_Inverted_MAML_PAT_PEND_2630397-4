---
name: mode-a-strata-batch-optimization
description: Multi-strata batch training, temporal window exploration (4.9–5.1 ms), learning rate benchmark and stability characterization for Inverted MAML Mode A hardware.
---

# Inverted MAML Mode A Multi-Strata Batch Optimization Skill

## 1. Overview & Patent Background
This skill provides operational methodologies, physical constraints, and automated benchmark workflows for training and optimizing the Inverted MAML Analog In-Memory Computing (AIMC) Triad ($M_{33}, M_3, M_8$) across broadened temporal payload windows on physical silicon (Trion T120 Master SoC + T20 Coprocessor, Patent Pending SE 2630397-4).

In Mode A, the primary $6 \times 6$ compute matrix ($M_{33}$) executes at nominal fixed gain, while the $8 \times 6$ carrier matrix ($M_3$) and $7 \times 6$ Vernier compensation layer ($M_8$) dynamically compensate physical distortion, amplifier offsets, and gate capacitor drift.

---

## 2. The Physical Window Constraint: Why Window Sizing Matters
On physical silicon, each multiplier synapse stores gate charges on $100\text{ nF}$ capacitors refreshed at $100\text{ Hz}$ ($10.0\text{ ms}$ cadence):
* **Wide Window ($4.0\text{ ms} - 6.0\text{ ms}$):**
  Over a span of $2.0\text{ ms}$, continuous capacitive leakage causes a massive voltage drop ($\approx 1000\text{ LSB}$ on ADC outputs). A single static weight matrix $W_8$ cannot simultaneously offset a $+350\text{ LSB}$ early transient and a $-580\text{ LSB}$ late decay. Aggressive gradient updates will pull weights to extreme values ($W > 60\text{ LSB}$), causing severe overshoot at early times.
* **Narrow Window ($4.8\text{ ms} - 5.2\text{ ms}$ or $4.9\text{ ms} - 5.1\text{ ms}$):**
  Over a $200\text{--}400\text{ µs}$ span centered at $5.0\text{ ms}$, capacitive drift is negligible ($< 30\text{ LSB}$). The ColTIA summing amplifiers operate within their linear sweet spot, enabling $W_8$ to achieve homogeneous $\ge 5.0\text{--}5.5\text{ bits}$ precision simultaneously across all strata.

---

## 3. Batch Training & Gradient Cadence Rules

### Cardinal Rules for Multi-Strata Training
1. **Locked Input Pattern ($x_{\text{ref}}$) per Batch:**
   Within each batch/epoch, the input vector $x_{\text{ref}}$ must remain strictly frozen across all temporal strata. If $x_{\text{ref}}$ is randomized between strata within the same batch, the neural network conflates input variation with temporal drift, degrading convergence.
2. **Fisher-Yates Random Strata Execution:**
   The strata sampling order must be randomly shuffled per epoch to eliminate systematic sequence bias.
3. **Learning Rate & Update Cadence:**
   * T120 internal learning rate is defined in fixpoint: $g\_lr\_inner\_q16 = 1024$ ($25\%$ step per update).
   * To achieve smooth non-oscillating convergence, the effective learning rate is scaled via update cadence:
     $$\text{Update Divisor} = \text{round}(1.0 / \text{lr\_scale})$$
   * **Benchmarked Sweet Spot:** $\text{lr\_scale} = 0.20\text{--}0.25$ ($1/5$ to $1/4$ rate) achieves optimal damping without sluggish stagnation.
   * $\text{lr} \ge 0.50$ ($1/2$): Too erratic, causes weight jumping and boundary overshoot.
   * $\text{lr} \le 0.10$ ($1/10$): Ultra-conservative, requires $> 50$ epochs to reach optimum.

---

## 4. Operational Scripts & Tools

### Running Batch Training on Hardware
```bash
/home/olle/anaconda3/bin/python FPGA_code/scripts/run_mode_a_batch_training.py \
    --epochs 100 \
    --t-min 4.9 \
    --t-max 5.1 \
    --strata 5 \
    --lr-scale 0.2 \
    --n-updates 1 \
    --out mode_a_100ep_4p9to5p1ms_lr0p2.json
```

### Visualizing Telemetry in 3D Telemetry Studio GUI
```bash
/home/olle/anaconda3/bin/python FPGA_code/scripts/maml_post_analysis_gui.py \
    FPGA_code/logs/mode_a_extended_training/mode_a_100ep_4p9to5p1ms_lr0p2.json
```
Features available in GUI:
* **Loss ($\text{LSB}^2$) Plot:** Top 2D plot showing quadratic loss trajectory over epochs.
* **RMSE & ENOB Plot:** Middle 2D plot with current epoch marker.
* **M8 Diag W Plot:** Bottom 2D plot showing 6-column adaptive weight trajectories.
* **3D Surface Views:** Toggle between Matrix 8 Vernier surface, Matrix 3 hidden surface, Matrix 33 static target, and Multi-strata temporal error landscape.

---

## 5. Weight Representation & Limits
* Hardware DACs: 8-bit ($0\text{--}255$), centered at $128$.
* Telemetry format: Signed offset $W = \text{DAC} - 128$.
* Pedestal at reset: $W = +24\text{ LSB}$ ($\text{DAC} = 152$) across all columns (biases 2T1C into quiet linear regime).
* Hard linear saturation (`sat_w80_q14`): $[-80, +80]\text{ LSB}$ ($\text{DAC} \in [48, 208]$).

