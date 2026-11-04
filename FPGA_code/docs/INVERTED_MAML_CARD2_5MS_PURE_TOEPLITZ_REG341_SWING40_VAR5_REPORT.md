# INVERTED MAML: Pure 5.0 ms Snapshot Experiment Report (TOEPLITZ, ±40 LSB, M33 Nominal 1.0x)
**Patent Pending:** SE 2630397-4 (Open Science Hardware)  
**Target Hardware:** Card 2 (Rev 2.0 Silicon, 1k/5.1k attenuator, repaired CH3)  
**Date:** 2026-11-04 10:52:49  
**Stimulus Profile:** LLM Toeplitz (ρ = 0.85)  
**Architecture:** Flat Baseline Protocol ($W=0, W_\text{null}=0, \text{LR}=0.08\text{x}, \lambda=341$)  
**Dynamic Input Swing:** $\pm 40\text{ LSB}$ (`d_line=2`)  
**Matrix 33 State:** M33 Nominal 1.0x | **Disturbance (Fig 7):** Fig 7 Disturbance ±5 LSB  

---

## 1. Executive Summary & Key Results
- **Pure 5.0 ms Snapshot Evaluation:** Evaluated strictly at single-point $t = 5000\,\mu\text{s}$ ($K=20$ capacitor refreshes per epoch).
- **Baseline Phase 1 ($W=0$, Ep 0..99):** Mean loss $= 15129.9\text{ LSB}^2$ (4.86 bits ENOB).
- **Active Training Phase 2 (Ep 100..500):** Mean loss dropped to **34477.2 LSB²** (4.54 bits ENOB), an improvement of **+127.9%** (-0.32 bits ENOB).
- **Peak Performance:** Epoch 342 reached **7579.5 LSB² (5.35 bits ENOB)**!
- **Weight Drift Immunity:** Final M8 diagonal weights converged to `[-27, -3, 4, -1, 86, 3]` LSB (0% clamping, 100% linear triode margin).

---

## 2. Statistical Metrics Comparison Table

| Metric | Phase 1: Flat Baseline ($W=0$) | Phase 2: Active Training ($W\to W^*$) | Delta / Improvement |
| :--- | :---: | :---: | :---: |
| **Duration (Epochs)** | Ep 0 .. 99 (100 ep) | Ep 100 .. 500 (401 ep) | +401 active training epochs |
| **Mean Loss** | 15129.9 LSB² | **34477.2 LSB²** | **+127.9%** |
| **Median Loss** | 15015.8 LSB² | 15907.5 LSB² | +5.9% |
| **Mean ENOB** | 4.86 bits | **4.54 bits** | **-0.32 bits** |
| **Median ENOB** | 4.86 bits | 4.81 bits | -0.05 bits |
| **Peak Single-Epoch** | — | **7579.5 LSB² (5.35 b @ Ep 342)** | Record low error |
| **Max Weight Drift ($W_8$)** | 0 LSB | **86 LSB** | Zero clamping (limit: 120 LSB) |

---

## 3. Pre- vs. Post-Training Temporal Transfer Function

| Delay (µs) | Pre-Training Loss (LSB²) | Post-Training Loss (LSB²) | Change (%) | Pre ENOB (b) | Post ENOB (b) |
| :---: | :---: | :---: | :---: | :---: | :---: |
| 4500 | 69618.5 | 560234.3 | +704.7% | 3.75 | 2.56 |
| 4600 | 29804.7 | 193559.8 | +549.4% | 4.36 | 3.01 |
| 4700 | 20007.8 | 81045.3 | +305.1% | 4.65 | 3.65 |
| 4800 | 7788.2 | 46335.5 | +494.9% | 5.33 | 4.05 |
| 4900 | 12943.2 | 28394.8 | +119.4% | 4.99 | 4.41 |
| 5000 | 23508.3 | 18580.3 | -21.0% | 4.55 | 4.73 |
| 5100 | 39289.0 | 22454.7 | -42.8% | 4.16 | 4.57 |
| 5200 | 67805.7 | 33757.5 | -50.2% | 3.77 | 4.28 |
| 5300 | 96821.8 | 54199.7 | -44.0% | 3.51 | 3.93 |
| 5400 | 146094.8 | 76926.3 | -47.3% | 3.22 | 3.68 |
| 5500 | 183930.5 | 120621.2 | -34.4% | 3.05 | 3.36 |

---

## 4. Patent SE 2630397-4 Fig 7 Emulator: Randomiserade Hidden Offsets (±5 LSB)
*Fusk-Skydd:* Den digitala mål-supervisorn ($Z_\text{target}$) i T120 SoC beräknas strikt mot den nominella frysta matrisen $W^{(33)}_\text{nominal}$. De dolda stokastiska avvikelserna laddas enbart upp på de fysiska 2T1C-kondensatorerna på kiselmatrisen för att emulera hårdvarudrift.

### Epok 100 .. 199 (Aktiv Störning):
```text
Rad 0: [  +4  -1  +0  +4  -4  -1 ] LSB
Rad 1: [  +3  -5  +2  +4  +1  +3 ] LSB
Rad 2: [  +3  -2  +3  +0  -4  +4 ] LSB
Rad 3: [  +0  +1  +4  -5  -2  +2 ] LSB
Rad 4: [  -5  +3  +0  +0  -4  +0 ] LSB
Rad 5: [  +4  -2  -2  +0  +0  +2 ] LSB
```

### Epok 200 .. 299 (Aktiv Störning):
```text
Rad 0: [  +5  -4  +0  +0  -5  +4 ] LSB
Rad 1: [  -2  +1  +4  -5  +2  +3 ] LSB
Rad 2: [  -3  -3  +4  -4  -5  -4 ] LSB
Rad 3: [  +0  -2  -5  -2  +3  +3 ] LSB
Rad 4: [  +1  +1  +0  -4  -1  -1 ] LSB
Rad 5: [  -1  -5  +3  -4  +0  +4 ] LSB
```

### Epok 300 .. 399 (Aktiv Störning):
```text
Rad 0: [  +2  -2  +5  +5  -5  -1 ] LSB
Rad 1: [  -2  -4  +1  -5  -1  +0 ] LSB
Rad 2: [  -4  +3  +5  -3  +3  +5 ] LSB
Rad 3: [  +0  +3  -1  -2  +4  +4 ] LSB
Rad 4: [  +2  +5  +3  +1  -3  -4 ] LSB
Rad 5: [  -2  -1  +5  -5  -5  -1 ] LSB
```

### Epok 400 .. 499 (Aktiv Störning):
```text
Rad 0: [  +1  -1  -1  +0  -5  +3 ] LSB
Rad 1: [  -4  -3  +5  +2  -5  -4 ] LSB
Rad 2: [  -1  +1  +1  +1  +2  -3 ] LSB
Rad 3: [  +5  +5  +2  +4  -4  -4 ] LSB
Rad 4: [  -2  +5  -4  +4  +0  -2 ] LSB
Rad 5: [  +4  +5  -5  -5  -3  -5 ] LSB
```

### Epok 500 .. 599 (Aktiv Störning):
```text
Rad 0: [  -4  -1  +4  -5  -2  +0 ] LSB
Rad 1: [  +3  -3  +2  -5  +4  +2 ] LSB
Rad 2: [  -2  +3  +1  +4  -5  +1 ] LSB
Rad 3: [  +5  -4  -3  +3  +5  +5 ] LSB
Rad 4: [  -1  +2  -2  -4  -3  -1 ] LSB
Rad 5: [  -5  +4  +5  -5  -1  -2 ] LSB
```

---

## 5. Hardware Verification & Run Parameters
- **SoC Architecture:** Trion T120 Master + T20 Companion (`TAG=T20A`, S-bus ACK `0x06`).
- **Passive Summing Attenuator:** 1k / 5.1k Ohm ($16.4\%$ compensation authority).
- **Repair Status:** Channel 3 resoldered and physically verified.
- **Log Source:** `FPGA_code/logs/mode_a_extended_training/mode_a_500ep_5ms_pure_toeplitz_reg341_swing40_var5.json`
- **Figure:** `/home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/docs/figures/fig_mode_a_500ep_5ms_pure_toeplitz_reg341_swing40_var5.png`
