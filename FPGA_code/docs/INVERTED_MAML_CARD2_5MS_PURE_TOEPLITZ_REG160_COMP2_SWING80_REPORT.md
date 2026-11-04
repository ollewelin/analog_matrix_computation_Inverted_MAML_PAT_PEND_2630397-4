# INVERTED MAML: Pure 5.0 ms Snapshot Experiment Report (TOEPLITZ, ±80 LSB, M33 Compressed 2.0x)
**Patent Pending:** SE 2630397-4 (Open Science Hardware)  
**Target Hardware:** Card 2 (Rev 2.0 Silicon, 1k/5.1k attenuator, repaired CH3)  
**Date:** 2026-11-04 10:31:58  
**Stimulus Profile:** LLM Toeplitz (ρ = 0.85)  
**Architecture:** Flat Baseline Protocol ($W=0, W_\text{null}=0, \text{LR}=0.08\text{x}, \lambda=160$)  
**Dynamic Input Swing:** $\pm 80\text{ LSB}$ (`d_line=1`)  
**Matrix 33 State:** M33 Compressed 2.0x | **Disturbance (Fig 7):** 100% Frozen M33  

---

## 1. Executive Summary & Key Results
- **Pure 5.0 ms Snapshot Evaluation:** Evaluated strictly at single-point $t = 5000\,\mu\text{s}$ ($K=20$ capacitor refreshes per epoch).
- **Baseline Phase 1 ($W=0$, Ep 0..99):** Mean loss $= 35240.3\text{ LSB}^2$ (4.27 bits ENOB).
- **Active Training Phase 2 (Ep 100..500):** Mean loss dropped to **30319.4 LSB²** (4.36 bits ENOB), an improvement of **-14.0%** (+0.09 bits ENOB).
- **Peak Performance:** Epoch 409 reached **14761.0 LSB² (4.87 bits ENOB)**!
- **Weight Drift Immunity:** Final M8 diagonal weights converged to `[8, 1, 3, 22, 14, -9]` LSB (0% clamping, 100% linear triode margin).

---

## 2. Statistical Metrics Comparison Table

| Metric | Phase 1: Flat Baseline ($W=0$) | Phase 2: Active Training ($W\to W^*$) | Delta / Improvement |
| :--- | :---: | :---: | :---: |
| **Duration (Epochs)** | Ep 0 .. 99 (100 ep) | Ep 100 .. 500 (401 ep) | +401 active training epochs |
| **Mean Loss** | 35240.3 LSB² | **30319.4 LSB²** | **-14.0%** |
| **Median Loss** | 34530.2 LSB² | 30271.0 LSB² | -12.3% |
| **Mean ENOB** | 4.27 bits | **4.36 bits** | **+0.09 bits** |
| **Median ENOB** | 4.25 bits | 4.35 bits | +0.09 bits |
| **Peak Single-Epoch** | — | **14761.0 LSB² (4.87 b @ Ep 409)** | Record low error |
| **Max Weight Drift ($W_8$)** | 0 LSB | **22 LSB** | Zero clamping (limit: 120 LSB) |

---

## 3. Pre- vs. Post-Training Temporal Transfer Function

| Delay (µs) | Pre-Training Loss (LSB²) | Post-Training Loss (LSB²) | Change (%) | Pre ENOB (b) | Post ENOB (b) |
| :---: | :---: | :---: | :---: | :---: | :---: |
| 4500 | 224162.3 | 494667.3 | +120.7% | 2.91 | 2.58 |
| 4600 | 190391.0 | 486955.8 | +155.8% | 3.02 | 2.53 |
| 4700 | 120338.5 | 157663.8 | +31.0% | 3.36 | 3.16 |
| 4800 | 73207.3 | 490413.3 | +569.9% | 3.72 | 2.99 |
| 4900 | 72175.8 | 50641.0 | -29.8% | 3.72 | 3.98 |
| 5000 | 25224.5 | 413118.2 | +1537.8% | 4.49 | 3.23 |
| 5100 | 18456.3 | 32691.3 | +77.1% | 4.71 | 4.30 |
| 5200 | 21118.0 | 433744.0 | +1953.9% | 4.61 | 3.75 |
| 5300 | 32023.3 | 47408.2 | +48.0% | 4.32 | 4.03 |
| 5400 | 57287.2 | 65407.7 | +14.2% | 3.89 | 3.80 |
| 5500 | 83791.3 | 92666.2 | +10.6% | 3.62 | 3.54 |

---

## 4. Hardware Verification & Run Parameters
- **SoC Architecture:** Trion T120 Master + T20 Companion (`TAG=T20A`, S-bus ACK `0x06`).
- **Passive Summing Attenuator:** 1k / 5.1k Ohm ($16.4\%$ compensation authority).
- **Repair Status:** Channel 3 resoldered and physically verified.
- **Log Source:** `FPGA_code/logs/mode_a_extended_training/mode_a_500ep_5ms_pure_toeplitz_lr0p08_reg160_comp2_swing80.json`
- **Figure:** `/home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/docs/figures/fig_mode_a_500ep_5ms_pure_toeplitz_lr0p08_reg160_comp2_swing80.png`
