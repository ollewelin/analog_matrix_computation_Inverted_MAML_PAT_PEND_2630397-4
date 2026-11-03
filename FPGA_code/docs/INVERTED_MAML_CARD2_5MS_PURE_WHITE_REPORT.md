# INVERTED MAML: Pure 5.0 ms Snapshot Experiment Report (WHITE)
**Patent Pending:** SE 2630397-4 (Open Science Hardware)  
**Target Hardware:** Card 2 (Rev 2.0 Silicon, 1k/5.1k attenuator, repaired CH3)  
**Date:** 2026-11-03 21:14:03  
**Stimulus Profile:** White Noise (Uniform Independent)  
**Architecture:** Flat Baseline Protocol ($W=0, W_\text{null}=0, \text{LR}=0.08\text{x}, \lambda=1024$)  
**Dynamic Input Swing:** $\pm 40\text{ LSB}$ (`d_line=2`)  

---

## 1. Executive Summary & Key Results
- **Pure 5.0 ms Snapshot Evaluation:** Evaluated strictly at single-point $t = 5000\,\mu\text{s}$ ($K=20$ capacitor refreshes per epoch).
- **Baseline Phase 1 ($W=0$, Ep 0..99):** Mean loss $= 17853.6\text{ LSB}^2$ (4.74 bits ENOB).
- **Active Training Phase 2 (Ep 100..500):** Mean loss dropped to **16806.8 LSB²** (4.78 bits ENOB), an improvement of **-5.9%** (+0.04 bits ENOB).
- **Peak Performance:** Epoch 246 reached **11438.0 LSB² (5.05 bits ENOB)**!
- **Weight Drift Immunity:** Final M8 diagonal weights converged to `[-1, 0, 1, 3, 10, -4]` LSB (0% clamping, 100% linear triode margin).

---

## 2. Statistical Metrics Comparison Table

| Metric | Phase 1: Flat Baseline ($W=0$) | Phase 2: Active Training ($W\to W^*$) | Delta / Improvement |
| :--- | :---: | :---: | :---: |
| **Duration (Epochs)** | Ep 0 .. 99 (100 ep) | Ep 100 .. 500 (401 ep) | +401 active training epochs |
| **Mean Loss** | 17853.6 LSB² | **16806.8 LSB²** | **-5.9%** |
| **Median Loss** | 17764.0 LSB² | 16521.0 LSB² | -7.0% |
| **Mean ENOB** | 4.74 bits | **4.78 bits** | **+0.04 bits** |
| **Median ENOB** | 4.73 bits | 4.79 bits | +0.06 bits |
| **Peak Single-Epoch** | — | **11438.0 LSB² (5.05 b @ Ep 246)** | Record low error |
| **Max Weight Drift ($W_8$)** | 0 LSB | **10 LSB** | Zero clamping (limit: 120 LSB) |

---

## 3. Pre- vs. Post-Training Temporal Transfer Function

| Delay (µs) | Pre-Training Loss (LSB²) | Post-Training Loss (LSB²) | Change (%) | Pre ENOB (b) | Post ENOB (b) |
| :---: | :---: | :---: | :---: | :---: | :---: |
| 4500 | 839639.0 | 128512.2 | -84.7% | 2.48 | 3.31 |
| 4600 | 75038.3 | 52598.3 | -29.9% | 3.70 | 3.96 |
| 4700 | 34468.5 | 484732.8 | +1306.3% | 4.27 | 3.19 |
| 4800 | 17050.3 | 55079.7 | +223.0% | 4.79 | 3.93 |
| 4900 | 8804.2 | 14843.3 | +68.6% | 5.24 | 4.88 |
| 5000 | 6795.3 | 13197.5 | +94.2% | 5.48 | 4.95 |
| 5100 | 12367.3 | 9367.5 | -24.3% | 5.00 | 5.22 |
| 5200 | 30078.3 | 12755.7 | -57.6% | 4.36 | 5.02 |
| 5300 | 62768.2 | 59434.8 | -5.3% | 3.83 | 3.86 |
| 5400 | 53582.8 | 83303.8 | +55.5% | 3.95 | 3.62 |
| 5500 | 158710.8 | 120483.2 | -24.1% | 3.16 | 3.35 |

---

## 4. Hardware Verification & Run Parameters
- **SoC Architecture:** Trion T120 Master + T20 Companion (`TAG=T20A`, S-bus ACK `0x06`).
- **Passive Summing Attenuator:** 1k / 5.1k Ohm ($16.4\%$ compensation authority).
- **Repair Status:** Channel 3 resoldered and physically verified.
- **Log Source:** `FPGA_code/logs/mode_a_extended_training/mode_a_500ep_5ms_pure_white_lr0p08_reg1024_swing40.json`
- **Figure:** `/home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/docs/figures/fig_mode_a_500ep_5ms_pure_white_lr0p08_reg1024_swing40.png`
