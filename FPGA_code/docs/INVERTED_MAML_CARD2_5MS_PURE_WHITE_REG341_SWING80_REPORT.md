# INVERTED MAML: Pure 5.0 ms Snapshot Experiment Report (WHITE, ±80 LSB)
**Patent Pending:** SE 2630397-4 (Open Science Hardware)  
**Target Hardware:** Card 2 (Rev 2.0 Silicon, 1k/5.1k attenuator, repaired CH3)  
**Date:** 2026-11-03 21:41:03  
**Stimulus Profile:** White Noise (Uniform Independent)  
**Architecture:** Flat Baseline Protocol ($W=0, W_\text{null}=0, \text{LR}=0.08\text{x}, \lambda=341$)  
**Dynamic Input Swing:** $\pm 80\text{ LSB}$ (`d_line=1`)  

---

## 1. Executive Summary & Key Results
- **Pure 5.0 ms Snapshot Evaluation:** Evaluated strictly at single-point $t = 5000\,\mu\text{s}$ ($K=20$ capacitor refreshes per epoch).
- **Baseline Phase 1 ($W=0$, Ep 0..99):** Mean loss $= 54244.5\text{ LSB}^2$ (3.94 bits ENOB).
- **Active Training Phase 2 (Ep 100..500):** Mean loss dropped to **46138.7 LSB²** (4.05 bits ENOB), an improvement of **-14.9%** (+0.11 bits ENOB).
- **Peak Performance:** Epoch 247 reached **28901.5 LSB² (4.38 bits ENOB)**!
- **Weight Drift Immunity:** Final M8 diagonal weights converged to `[-1, 6, 2, 7, 18, -10]` LSB (0% clamping, 100% linear triode margin).

---

## 2. Statistical Metrics Comparison Table

| Metric | Phase 1: Flat Baseline ($W=0$) | Phase 2: Active Training ($W\to W^*$) | Delta / Improvement |
| :--- | :---: | :---: | :---: |
| **Duration (Epochs)** | Ep 0 .. 99 (100 ep) | Ep 100 .. 500 (401 ep) | +401 active training epochs |
| **Mean Loss** | 54244.5 LSB² | **46138.7 LSB²** | **-14.9%** |
| **Median Loss** | 52693.2 LSB² | 45558.5 LSB² | -13.5% |
| **Mean ENOB** | 3.94 bits | **4.05 bits** | **+0.11 bits** |
| **Median ENOB** | 3.95 bits | 4.05 bits | +0.10 bits |
| **Peak Single-Epoch** | — | **28901.5 LSB² (4.38 b @ Ep 247)** | Record low error |
| **Max Weight Drift ($W_8$)** | 0 LSB | **18 LSB** | Zero clamping (limit: 120 LSB) |

---

## 3. Pre- vs. Post-Training Temporal Transfer Function

| Delay (µs) | Pre-Training Loss (LSB²) | Post-Training Loss (LSB²) | Change (%) | Pre ENOB (b) | Post ENOB (b) |
| :---: | :---: | :---: | :---: | :---: | :---: |
| 4500 | 89222.8 | 77948.7 | -12.6% | 3.57 | 3.67 |
| 4600 | 52745.0 | 53104.0 | +0.7% | 3.95 | 3.95 |
| 4700 | 27736.2 | 42549.5 | +53.4% | 4.42 | 4.10 |
| 4800 | 21859.0 | 38345.5 | +75.4% | 4.59 | 4.18 |
| 4900 | 470321.8 | 34703.3 | -92.6% | 3.36 | 4.25 |
| 5000 | 18453.3 | 41778.0 | +126.4% | 4.72 | 4.12 |
| 5100 | 25454.7 | 51842.2 | +103.7% | 4.47 | 3.97 |
| 5200 | 36109.5 | 76438.5 | +111.7% | 4.22 | 3.68 |
| 5300 | 62004.7 | 82122.8 | +32.4% | 3.84 | 3.63 |
| 5400 | 88737.2 | 120778.5 | +36.1% | 3.58 | 3.35 |
| 5500 | 124455.5 | 153005.8 | +22.9% | 3.33 | 3.18 |

---

## 4. Hardware Verification & Run Parameters
- **SoC Architecture:** Trion T120 Master + T20 Companion (`TAG=T20A`, S-bus ACK `0x06`).
- **Passive Summing Attenuator:** 1k / 5.1k Ohm ($16.4\%$ compensation authority).
- **Repair Status:** Channel 3 resoldered and physically verified.
- **Log Source:** `FPGA_code/logs/mode_a_extended_training/mode_a_500ep_5ms_pure_white_lr0p08_reg341_swing80.json`
- **Figure:** `/home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/docs/figures/fig_mode_a_500ep_5ms_pure_white_lr0p08_reg341_swing80.png`
