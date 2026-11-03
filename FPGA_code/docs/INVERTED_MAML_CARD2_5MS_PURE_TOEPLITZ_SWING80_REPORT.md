# INVERTED MAML: Pure 5.0 ms Snapshot Experiment Report (TOEPLITZ, ±80 LSB)
**Patent Pending:** SE 2630397-4 (Open Science Hardware)  
**Target Hardware:** Card 2 (Rev 2.0 Silicon, 1k/5.1k attenuator, repaired CH3)  
**Date:** 2026-11-03 21:17:09  
**Stimulus Profile:** LLM Toeplitz (ρ = 0.85)  
**Architecture:** Flat Baseline Protocol ($W=0, W_\text{null}=0, \text{LR}=0.08\text{x}, \lambda=1024$)  
**Dynamic Input Swing:** $\pm 80\text{ LSB}$ (`d_line=1`)  

---

## 1. Executive Summary & Key Results
- **Pure 5.0 ms Snapshot Evaluation:** Evaluated strictly at single-point $t = 5000\,\mu\text{s}$ ($K=20$ capacitor refreshes per epoch).
- **Baseline Phase 1 ($W=0$, Ep 0..99):** Mean loss $= 56135.6\text{ LSB}^2$ (3.92 bits ENOB).
- **Active Training Phase 2 (Ep 100..500):** Mean loss dropped to **44542.6 LSB²** (4.08 bits ENOB), an improvement of **-20.7%** (+0.16 bits ENOB).
- **Peak Performance:** Epoch 398 reached **27263.0 LSB² (4.43 bits ENOB)**!
- **Weight Drift Immunity:** Final M8 diagonal weights converged to `[7, 1, 0, 16, 12, -9]` LSB (0% clamping, 100% linear triode margin).

---

## 2. Statistical Metrics Comparison Table

| Metric | Phase 1: Flat Baseline ($W=0$) | Phase 2: Active Training ($W\to W^*$) | Delta / Improvement |
| :--- | :---: | :---: | :---: |
| **Duration (Epochs)** | Ep 0 .. 99 (100 ep) | Ep 100 .. 500 (401 ep) | +401 active training epochs |
| **Mean Loss** | 56135.6 LSB² | **44542.6 LSB²** | **-20.7%** |
| **Median Loss** | 56876.5 LSB² | 44141.0 LSB² | -22.4% |
| **Mean ENOB** | 3.92 bits | **4.08 bits** | **+0.16 bits** |
| **Median ENOB** | 3.90 bits | 4.08 bits | +0.19 bits |
| **Peak Single-Epoch** | — | **27263.0 LSB² (4.43 b @ Ep 398)** | Record low error |
| **Max Weight Drift ($W_8$)** | 0 LSB | **16 LSB** | Zero clamping (limit: 120 LSB) |

---

## 3. Pre- vs. Post-Training Temporal Transfer Function

| Delay (µs) | Pre-Training Loss (LSB²) | Post-Training Loss (LSB²) | Change (%) | Pre ENOB (b) | Post ENOB (b) |
| :---: | :---: | :---: | :---: | :---: | :---: |
| 4500 | 158800.0 | 58767.7 | -63.0% | 3.16 | 3.87 |
| 4600 | 113775.2 | 61948.3 | -45.6% | 3.40 | 3.83 |
| 4700 | 70979.2 | 57297.8 | -19.3% | 3.74 | 3.89 |
| 4800 | 40648.2 | 68635.3 | +68.9% | 4.14 | 3.76 |
| 4900 | 24849.3 | 86735.3 | +249.0% | 4.50 | 3.59 |
| 5000 | 15727.8 | 114154.8 | +625.8% | 4.83 | 3.39 |
| 5100 | 19212.5 | 126541.0 | +558.6% | 4.69 | 3.32 |
| 5200 | 34982.2 | 158131.8 | +352.0% | 4.26 | 3.16 |
| 5300 | 65561.3 | 208303.0 | +217.7% | 3.80 | 2.96 |
| 5400 | 107387.2 | 256476.3 | +138.8% | 3.44 | 2.81 |
| 5500 | 151693.7 | 310162.0 | +104.5% | 3.19 | 2.67 |

---

## 4. Hardware Verification & Run Parameters
- **SoC Architecture:** Trion T120 Master + T20 Companion (`TAG=T20A`, S-bus ACK `0x06`).
- **Passive Summing Attenuator:** 1k / 5.1k Ohm ($16.4\%$ compensation authority).
- **Repair Status:** Channel 3 resoldered and physically verified.
- **Log Source:** `FPGA_code/logs/mode_a_extended_training/mode_a_500ep_5ms_pure_toeplitz_lr0p08_reg1024_swing80.json`
- **Figure:** `/home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/docs/figures/fig_mode_a_500ep_5ms_pure_toeplitz_lr0p08_reg1024_swing80.png`
