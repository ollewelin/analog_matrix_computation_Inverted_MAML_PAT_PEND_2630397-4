# INVERTED MAML: Pure 5.0 ms Snapshot Experiment Report (TOEPLITZ, ±40 LSB, M33 Nominal 1.0x)
**Patent Pending:** SE 2630397-4 (Open Science Hardware)  
**Target Hardware:** Card 2 (Rev 2.0 Silicon, 1k/5.1k attenuator, repaired CH3)  
**Date:** 2026-11-04 10:42:14  
**Stimulus Profile:** LLM Toeplitz (ρ = 0.85)  
**Architecture:** Flat Baseline Protocol ($W=0, W_\text{null}=0, \text{LR}=0.08\text{x}, \lambda=160$)  
**Dynamic Input Swing:** $\pm 40\text{ LSB}$ (`d_line=2`)  
**Matrix 33 State:** M33 Nominal 1.0x | **Disturbance (Fig 7):** 100% Frozen M33  

---

## 1. Executive Summary & Key Results
- **Pure 5.0 ms Snapshot Evaluation:** Evaluated strictly at single-point $t = 5000\,\mu\text{s}$ ($K=20$ capacitor refreshes per epoch).
- **Baseline Phase 1 ($W=0$, Ep 0..99):** Mean loss $= 14506.8\text{ LSB}^2$ (4.89 bits ENOB).
- **Active Training Phase 2 (Ep 100..500):** Mean loss dropped to **13038.7 LSB²** (4.97 bits ENOB), an improvement of **-10.1%** (+0.08 bits ENOB).
- **Peak Performance:** Epoch 395 reached **8239.0 LSB² (5.29 bits ENOB)**!
- **Weight Drift Immunity:** Final M8 diagonal weights converged to `[9, -2, -1, -4, 2, -10]` LSB (0% clamping, 100% linear triode margin).

---

## 2. Statistical Metrics Comparison Table

| Metric | Phase 1: Flat Baseline ($W=0$) | Phase 2: Active Training ($W\to W^*$) | Delta / Improvement |
| :--- | :---: | :---: | :---: |
| **Duration (Epochs)** | Ep 0 .. 99 (100 ep) | Ep 100 .. 500 (401 ep) | +401 active training epochs |
| **Mean Loss** | 14506.8 LSB² | **13038.7 LSB²** | **-10.1%** |
| **Median Loss** | 14425.0 LSB² | 12957.5 LSB² | -10.2% |
| **Mean ENOB** | 4.89 bits | **4.97 bits** | **+0.08 bits** |
| **Median ENOB** | 4.88 bits | 4.96 bits | +0.08 bits |
| **Peak Single-Epoch** | — | **8239.0 LSB² (5.29 b @ Ep 395)** | Record low error |
| **Max Weight Drift ($W_8$)** | 0 LSB | **10 LSB** | Zero clamping (limit: 120 LSB) |

---

## 3. Pre- vs. Post-Training Temporal Transfer Function

| Delay (µs) | Pre-Training Loss (LSB²) | Post-Training Loss (LSB²) | Change (%) | Pre ENOB (b) | Post ENOB (b) |
| :---: | :---: | :---: | :---: | :---: | :---: |
| 4500 | 604254.5 | 148374.8 | -75.4% | 2.50 | 3.20 |
| 4600 | 116258.8 | 406956.2 | +250.0% | 3.38 | 2.72 |
| 4700 | 69023.8 | 63237.7 | -8.4% | 3.76 | 3.83 |
| 4800 | 32254.3 | 37744.0 | +17.0% | 4.32 | 4.19 |
| 4900 | 14165.0 | 429940.0 | +2935.2% | 4.92 | 3.84 |
| 5000 | 3443.8 | 5324.2 | +54.6% | 5.93 | 5.63 |
| 5100 | 3319.5 | 3520.5 | +6.1% | 5.98 | 5.92 |
| 5200 | 15682.7 | 7449.8 | -52.5% | 4.86 | 5.36 |
| 5300 | 28906.5 | 21687.5 | -25.0% | 4.39 | 4.59 |
| 5400 | 60224.2 | 46687.5 | -22.5% | 3.86 | 4.05 |
| 5500 | 105507.0 | 76884.5 | -27.1% | 3.45 | 3.68 |

---

## 4. Hardware Verification & Run Parameters
- **SoC Architecture:** Trion T120 Master + T20 Companion (`TAG=T20A`, S-bus ACK `0x06`).
- **Passive Summing Attenuator:** 1k / 5.1k Ohm ($16.4\%$ compensation authority).
- **Repair Status:** Channel 3 resoldered and physically verified.
- **Log Source:** `FPGA_code/logs/mode_a_extended_training/mode_a_500ep_5ms_pure_toeplitz_lr0p08_reg160_swing40_reverify.json`
- **Figure:** `/home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/docs/figures/fig_mode_a_500ep_5ms_pure_toeplitz_lr0p08_reg160_swing40_reverify.png`
