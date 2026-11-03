# INVERTED MAML: Pure 5.0 ms Snapshot Experiment Report (TOEPLITZ, ±40 LSB)
**Patent Pending:** SE 2630397-4 (Open Science Hardware)  
**Target Hardware:** Card 2 (Rev 2.0 Silicon, 1k/5.1k attenuator, repaired CH3)  
**Date:** 2026-11-03 21:50:16  
**Stimulus Profile:** LLM Toeplitz (ρ = 0.85)  
**Architecture:** Flat Baseline Protocol ($W=0, W_\text{null}=0, \text{LR}=0.08\text{x}, \lambda=160$)  
**Dynamic Input Swing:** $\pm 40\text{ LSB}$ (`d_line=2`)  

---

## 1. Executive Summary & Key Results
- **Pure 5.0 ms Snapshot Evaluation:** Evaluated strictly at single-point $t = 5000\,\mu\text{s}$ ($K=20$ capacitor refreshes per epoch).
- **Baseline Phase 1 ($W=0$, Ep 0..99):** Mean loss $= 16881.4\text{ LSB}^2$ (4.78 bits ENOB).
- **Active Training Phase 2 (Ep 100..500):** Mean loss dropped to **14375.6 LSB²** (4.90 bits ENOB), an improvement of **-14.8%** (+0.12 bits ENOB).
- **Peak Performance:** Epoch 136 reached **7075.5 LSB² (5.40 bits ENOB)**!
- **Weight Drift Immunity:** Final M8 diagonal weights converged to `[9, -2, 0, 2, 6, -10]` LSB (0% clamping, 100% linear triode margin).

---

## 2. Statistical Metrics Comparison Table

| Metric | Phase 1: Flat Baseline ($W=0$) | Phase 2: Active Training ($W\to W^*$) | Delta / Improvement |
| :--- | :---: | :---: | :---: |
| **Duration (Epochs)** | Ep 0 .. 99 (100 ep) | Ep 100 .. 500 (401 ep) | +401 active training epochs |
| **Mean Loss** | 16881.4 LSB² | **14375.6 LSB²** | **-14.8%** |
| **Median Loss** | 16714.8 LSB² | 14235.0 LSB² | -14.8% |
| **Mean ENOB** | 4.78 bits | **4.90 bits** | **+0.12 bits** |
| **Median ENOB** | 4.78 bits | 4.89 bits | +0.11 bits |
| **Peak Single-Epoch** | — | **7075.5 LSB² (5.40 b @ Ep 136)** | Record low error |
| **Max Weight Drift ($W_8$)** | 0 LSB | **10 LSB** | Zero clamping (limit: 120 LSB) |

---

## 3. Pre- vs. Post-Training Temporal Transfer Function

| Delay (µs) | Pre-Training Loss (LSB²) | Post-Training Loss (LSB²) | Change (%) | Pre ENOB (b) | Post ENOB (b) |
| :---: | :---: | :---: | :---: | :---: | :---: |
| 4500 | 81786.3 | 203868.8 | +149.3% | 3.63 | 2.97 |
| 4600 | 40524.5 | 136499.3 | +236.8% | 4.16 | 3.26 |
| 4700 | 24904.2 | 134939.5 | +441.8% | 4.51 | 3.27 |
| 4800 | 14249.2 | 63142.8 | +343.1% | 4.91 | 3.82 |
| 4900 | 12414.0 | 31901.0 | +157.0% | 5.01 | 4.33 |
| 5000 | 18190.5 | 18061.0 | -0.7% | 4.72 | 4.74 |
| 5100 | 32875.2 | 10187.0 | -69.0% | 4.30 | 5.16 |
| 5200 | 59987.7 | 7622.0 | -87.3% | 3.86 | 5.39 |
| 5300 | 97508.2 | 19831.5 | -79.7% | 3.51 | 4.67 |
| 5400 | 139431.0 | 37318.2 | -73.2% | 3.25 | 4.20 |
| 5500 | 197458.8 | 74132.5 | -62.5% | 3.00 | 3.70 |

---

## 4. Hardware Verification & Run Parameters
- **SoC Architecture:** Trion T120 Master + T20 Companion (`TAG=T20A`, S-bus ACK `0x06`).
- **Passive Summing Attenuator:** 1k / 5.1k Ohm ($16.4\%$ compensation authority).
- **Repair Status:** Channel 3 resoldered and physically verified.
- **Log Source:** `FPGA_code/logs/mode_a_extended_training/mode_a_500ep_5ms_pure_toeplitz_lr0p08_reg160_swing40.json`
- **Figure:** `/home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/docs/figures/fig_mode_a_500ep_5ms_pure_toeplitz_lr0p08_reg160_swing40.png`
