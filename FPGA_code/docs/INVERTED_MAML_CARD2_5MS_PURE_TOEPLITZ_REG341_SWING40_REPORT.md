# INVERTED MAML: Pure 5.0 ms Snapshot Experiment Report (TOEPLITZ, ±40 LSB)
**Patent Pending:** SE 2630397-4 (Open Science Hardware)  
**Target Hardware:** Card 2 (Rev 2.0 Silicon, 1k/5.1k attenuator, repaired CH3)  
**Date:** 2026-11-03 21:43:37  
**Stimulus Profile:** LLM Toeplitz (ρ = 0.85)  
**Architecture:** Flat Baseline Protocol ($W=0, W_\text{null}=0, \text{LR}=0.08\text{x}, \lambda=341$)  
**Dynamic Input Swing:** $\pm 40\text{ LSB}$ (`d_line=2`)  

---

## 1. Executive Summary & Key Results
- **Pure 5.0 ms Snapshot Evaluation:** Evaluated strictly at single-point $t = 5000\,\mu\text{s}$ ($K=20$ capacitor refreshes per epoch).
- **Baseline Phase 1 ($W=0$, Ep 0..99):** Mean loss $= 16393.0\text{ LSB}^2$ (4.80 bits ENOB).
- **Active Training Phase 2 (Ep 100..500):** Mean loss dropped to **14227.0 LSB²** (4.90 bits ENOB), an improvement of **-13.2%** (+0.10 bits ENOB).
- **Peak Performance:** Epoch 451 reached **7064.0 LSB² (5.40 bits ENOB)**!
- **Weight Drift Immunity:** Final M8 diagonal weights converged to `[2, -3, 2, 2, 8, -9]` LSB (0% clamping, 100% linear triode margin).

---

## 2. Statistical Metrics Comparison Table

| Metric | Phase 1: Flat Baseline ($W=0$) | Phase 2: Active Training ($W\to W^*$) | Delta / Improvement |
| :--- | :---: | :---: | :---: |
| **Duration (Epochs)** | Ep 0 .. 99 (100 ep) | Ep 100 .. 500 (401 ep) | +401 active training epochs |
| **Mean Loss** | 16393.0 LSB² | **14227.0 LSB²** | **-13.2%** |
| **Median Loss** | 16462.2 LSB² | 14067.5 LSB² | -14.5% |
| **Mean ENOB** | 4.80 bits | **4.90 bits** | **+0.10 bits** |
| **Median ENOB** | 4.79 bits | 4.90 bits | +0.11 bits |
| **Peak Single-Epoch** | — | **7064.0 LSB² (5.40 b @ Ep 451)** | Record low error |
| **Max Weight Drift ($W_8$)** | 0 LSB | **9 LSB** | Zero clamping (limit: 120 LSB) |

---

## 3. Pre- vs. Post-Training Temporal Transfer Function

| Delay (µs) | Pre-Training Loss (LSB²) | Post-Training Loss (LSB²) | Change (%) | Pre ENOB (b) | Post ENOB (b) |
| :---: | :---: | :---: | :---: | :---: | :---: |
| 4500 | 112410.0 | 167643.8 | +49.1% | 3.40 | 3.12 |
| 4600 | 62721.5 | 121120.7 | +93.1% | 3.83 | 3.35 |
| 4700 | 39006.8 | 72953.5 | +87.0% | 4.17 | 3.72 |
| 4800 | 14232.8 | 46598.5 | +227.4% | 4.90 | 4.04 |
| 4900 | 6972.5 | 48074.0 | +589.5% | 5.47 | 4.02 |
| 5000 | 9170.7 | 9840.3 | +7.3% | 5.29 | 5.19 |
| 5100 | 15740.3 | 5365.8 | -65.9% | 4.83 | 5.70 |
| 5200 | 37106.5 | 7006.0 | -81.1% | 4.21 | 5.42 |
| 5300 | 69147.0 | 17600.7 | -74.5% | 3.76 | 4.76 |
| 5400 | 111578.7 | 41619.7 | -62.7% | 3.41 | 4.13 |
| 5500 | 158444.7 | 73566.2 | -53.6% | 3.16 | 3.71 |

---

## 4. Hardware Verification & Run Parameters
- **SoC Architecture:** Trion T120 Master + T20 Companion (`TAG=T20A`, S-bus ACK `0x06`).
- **Passive Summing Attenuator:** 1k / 5.1k Ohm ($16.4\%$ compensation authority).
- **Repair Status:** Channel 3 resoldered and physically verified.
- **Log Source:** `FPGA_code/logs/mode_a_extended_training/mode_a_500ep_5ms_pure_toeplitz_lr0p08_reg341_swing40.json`
- **Figure:** `/home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/docs/figures/fig_mode_a_500ep_5ms_pure_toeplitz_lr0p08_reg341_swing40.png`
