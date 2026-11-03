# INVERTED MAML: Pure 5.0 ms Snapshot Experiment Report (TOEPLITZ)
**Patent Pending:** SE 2630397-4 (Open Science Hardware)  
**Target Hardware:** Card 2 (Rev 2.0 Silicon, 1k/5.1k attenuator, repaired CH3)  
**Date:** 2026-11-03 21:10:58  
**Stimulus Profile:** LLM Toeplitz (ρ = 0.85)  
**Architecture:** Flat Baseline Protocol ($W=0, W_\text{null}=0, \text{LR}=0.08\text{x}, \lambda=1024$)  
**Dynamic Input Swing:** $\pm 40\text{ LSB}$ (`d_line=2`)  

---

## 1. Executive Summary & Key Results
- **Pure 5.0 ms Snapshot Evaluation:** Evaluated strictly at single-point $t = 5000\,\mu\text{s}$ ($K=20$ capacitor refreshes per epoch).
- **Baseline Phase 1 ($W=0$, Ep 0..99):** Mean loss $= 17897.2\text{ LSB}^2$ (4.74 bits ENOB).
- **Active Training Phase 2 (Ep 100..500):** Mean loss dropped to **15099.1 LSB²** (4.86 bits ENOB), an improvement of **-15.6%** (+0.12 bits ENOB).
- **Peak Performance:** Epoch 290 reached **9310.0 LSB² (5.20 bits ENOB)**!
- **Weight Drift Immunity:** Final M8 diagonal weights converged to `[9, -1, 1, 4, 13, -6]` LSB (0% clamping, 100% linear triode margin).

---

## 2. Statistical Metrics Comparison Table

| Metric | Phase 1: Flat Baseline ($W=0$) | Phase 2: Active Training ($W\to W^*$) | Delta / Improvement |
| :--- | :---: | :---: | :---: |
| **Duration (Epochs)** | Ep 0 .. 99 (100 ep) | Ep 100 .. 500 (401 ep) | +401 active training epochs |
| **Mean Loss** | 17897.2 LSB² | **15099.1 LSB²** | **-15.6%** |
| **Median Loss** | 17873.2 LSB² | 14920.0 LSB² | -16.5% |
| **Mean ENOB** | 4.74 bits | **4.86 bits** | **+0.12 bits** |
| **Median ENOB** | 4.73 bits | 4.86 bits | +0.13 bits |
| **Peak Single-Epoch** | — | **9310.0 LSB² (5.20 b @ Ep 290)** | Record low error |
| **Max Weight Drift ($W_8$)** | 0 LSB | **13 LSB** | Zero clamping (limit: 120 LSB) |

---

## 3. Pre- vs. Post-Training Temporal Transfer Function

| Delay (µs) | Pre-Training Loss (LSB²) | Post-Training Loss (LSB²) | Change (%) | Pre ENOB (b) | Post ENOB (b) |
| :---: | :---: | :---: | :---: | :---: | :---: |
| 4500 | 65606.2 | 116220.8 | +77.1% | 3.80 | 3.38 |
| 4600 | 35155.7 | 64792.2 | +84.3% | 4.24 | 3.81 |
| 4700 | 13398.2 | 36529.0 | +172.6% | 4.97 | 4.21 |
| 4800 | 586000.5 | 17616.7 | -97.0% | 3.96 | 4.75 |
| 4900 | 13104.5 | 2142.7 | -83.6% | 4.96 | 6.29 |
| 5000 | 15177.5 | 1740.3 | -88.5% | 4.86 | 6.50 |
| 5100 | 47731.5 | 4402.3 | -90.8% | 4.02 | 5.93 |
| 5200 | 19412.5 | 14772.2 | -23.9% | 4.72 | 4.89 |
| 5300 | 41665.7 | 35275.5 | -15.3% | 4.13 | 4.25 |
| 5400 | 79320.0 | 67064.5 | -15.5% | 3.66 | 3.78 |
| 5500 | 120942.2 | 101097.2 | -16.4% | 3.35 | 3.48 |

---

## 4. Hardware Verification & Run Parameters
- **SoC Architecture:** Trion T120 Master + T20 Companion (`TAG=T20A`, S-bus ACK `0x06`).
- **Passive Summing Attenuator:** 1k / 5.1k Ohm ($16.4\%$ compensation authority).
- **Repair Status:** Channel 3 resoldered and physically verified.
- **Log Source:** `FPGA_code/logs/mode_a_extended_training/mode_a_500ep_5ms_pure_toeplitz_lr0p08_reg1024_swing40.json`
- **Figure:** `/home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/docs/figures/fig_mode_a_500ep_5ms_pure_toeplitz_lr0p08_reg1024_swing40.png`
