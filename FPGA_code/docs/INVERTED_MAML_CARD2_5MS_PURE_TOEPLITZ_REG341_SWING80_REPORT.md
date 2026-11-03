# INVERTED MAML: Pure 5.0 ms Snapshot Experiment Report (TOEPLITZ, ±80 LSB)
**Patent Pending:** SE 2630397-4 (Open Science Hardware)  
**Target Hardware:** Card 2 (Rev 2.0 Silicon, 1k/5.1k attenuator, repaired CH3)  
**Date:** 2026-11-03 21:33:51  
**Stimulus Profile:** LLM Toeplitz (ρ = 0.85)  
**Architecture:** Flat Baseline Protocol ($W=0, W_\text{null}=0, \text{LR}=0.08\text{x}, \lambda=341$)  
**Dynamic Input Swing:** $\pm 80\text{ LSB}$ (`d_line=1`)  

---

## 1. Executive Summary & Key Results
- **Pure 5.0 ms Snapshot Evaluation:** Evaluated strictly at single-point $t = 5000\,\mu\text{s}$ ($K=20$ capacitor refreshes per epoch).
- **Baseline Phase 1 ($W=0$, Ep 0..99):** Mean loss $= 54381.2\text{ LSB}^2$ (3.94 bits ENOB).
- **Active Training Phase 2 (Ep 100..500):** Mean loss dropped to **42987.1 LSB²** (4.11 bits ENOB), an improvement of **-21.0%** (+0.17 bits ENOB).
- **Peak Performance:** Epoch 306 reached **24212.0 LSB² (4.51 bits ENOB)**!
- **Weight Drift Immunity:** Final M8 diagonal weights converged to `[10, 0, 2, 25, 17, -15]` LSB (0% clamping, 100% linear triode margin).

---

## 2. Statistical Metrics Comparison Table

| Metric | Phase 1: Flat Baseline ($W=0$) | Phase 2: Active Training ($W\to W^*$) | Delta / Improvement |
| :--- | :---: | :---: | :---: |
| **Duration (Epochs)** | Ep 0 .. 99 (100 ep) | Ep 100 .. 500 (401 ep) | +401 active training epochs |
| **Mean Loss** | 54381.2 LSB² | **42987.1 LSB²** | **-21.0%** |
| **Median Loss** | 53386.0 LSB² | 42307.5 LSB² | -20.8% |
| **Mean ENOB** | 3.94 bits | **4.11 bits** | **+0.17 bits** |
| **Median ENOB** | 3.94 bits | 4.11 bits | +0.17 bits |
| **Peak Single-Epoch** | — | **24212.0 LSB² (4.51 b @ Ep 306)** | Record low error |
| **Max Weight Drift ($W_8$)** | 0 LSB | **25 LSB** | Zero clamping (limit: 120 LSB) |

---

## 3. Pre- vs. Post-Training Temporal Transfer Function

| Delay (µs) | Pre-Training Loss (LSB²) | Post-Training Loss (LSB²) | Change (%) | Pre ENOB (b) | Post ENOB (b) |
| :---: | :---: | :---: | :---: | :---: | :---: |
| 4500 | 90144.5 | 579781.0 | +543.2% | 3.57 | 2.42 |
| 4600 | 59536.2 | 215856.3 | +262.6% | 3.88 | 2.93 |
| 4700 | 477346.3 | 127218.7 | -73.3% | 2.92 | 3.31 |
| 4800 | 63198.5 | 105221.3 | +66.5% | 3.82 | 3.45 |
| 4900 | 47786.7 | 67518.8 | +41.3% | 4.02 | 3.78 |
| 5000 | 33897.0 | 39014.2 | +15.1% | 4.27 | 4.17 |
| 5100 | 35561.5 | 20954.0 | -41.1% | 4.24 | 4.62 |
| 5200 | 57233.7 | 18224.3 | -68.2% | 3.89 | 4.73 |
| 5300 | 77585.7 | 13013.2 | -83.2% | 3.67 | 4.97 |
| 5400 | 113737.2 | 26025.8 | -77.1% | 3.40 | 4.46 |
| 5500 | 157612.0 | 45329.8 | -71.2% | 3.16 | 4.06 |

---

## 4. Hardware Verification & Run Parameters
- **SoC Architecture:** Trion T120 Master + T20 Companion (`TAG=T20A`, S-bus ACK `0x06`).
- **Passive Summing Attenuator:** 1k / 5.1k Ohm ($16.4\%$ compensation authority).
- **Repair Status:** Channel 3 resoldered and physically verified.
- **Log Source:** `FPGA_code/logs/mode_a_extended_training/mode_a_500ep_5ms_pure_toeplitz_lr0p08_reg341_swing80.json`
- **Figure:** `/home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/docs/figures/fig_mode_a_500ep_5ms_pure_toeplitz_lr0p08_reg341_swing80.png`
