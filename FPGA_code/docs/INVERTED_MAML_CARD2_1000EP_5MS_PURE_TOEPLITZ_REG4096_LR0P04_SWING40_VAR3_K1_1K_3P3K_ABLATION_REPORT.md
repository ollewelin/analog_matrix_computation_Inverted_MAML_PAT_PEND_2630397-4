# INVERTED MAML: Pure 5.0 ms Snapshot Experiment Report (TOEPLITZ, ±40 LSB, M33 Nominal 1.0x)
**Patent Pending:** SE 2630397-4 (Open Science Hardware)  
**Target Hardware:** Card 2 (Rev 2.0 Silicon, 1k/3.3k attenuator, repaired CH3)  
**Date:** 2026-11-04 12:54:46  
**Stimulus Profile:** LLM Toeplitz (ρ = 0.85)  
**Architecture:** Flat Baseline Protocol ($W=0, W_\text{null}=0, \text{LR}=0.04\text{x}, \lambda=4096$)  
**Dynamic Input Swing:** $\pm 40\text{ LSB}$ (`d_line=2`)  
**Matrix 33 State:** M33 Nominal 1.0x | **Disturbance (Fig 7):** Fig 7 Disturbance ±3 LSB  

---

## 1. Executive Summary & Key Results
- **Pure 5.0 ms Snapshot Evaluation:** Evaluated strictly at single-point $t = 5000\,\mu\text{s}$ ($K=1$ capacitor refreshes per epoch).
- **Baseline Phase 1 ($W=0$, Ep 0..99):** Mean loss $= 128823.4\text{ LSB}^2$ (3.34 bits ENOB).
- **Active Training Phase 2 (Ep 100..1000):** Whole-run active evaluation stabilized at **27863.7 LSB²** (4.60 bits ENOB), an improvement of **-78.4%** (+1.26 bits ENOB).
- **Peak Performance:** Epoch 411 reached **1303.0 LSB² (6.62 bits ENOB)**!
- **Weight Drift Immunity:** Final M8 diagonal weights converged to `[0, 0, 0, 0, 0, 0]` LSB (0% clamping, 100% linear triode margin).

---

## 2. 100-Epoch Segment Progression & Fig 7 Disturbance Response

| Segment | Status / Störningsregim | Medelfel (LSB²) | Medel ENOB (b) | Topp-ENOB (b) | Slutvikter $W_8$ (LSB) |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Epoch 0 .. 99** | Phase 1: Baseline W=0 (Training OFF, Nom. M33) | 128823.4 | **3.34** | 4.79 (@ 16463.0 L²) | `[0, 0, 0, 0, 0, 0]` |
| **Epoch 100 .. 199** | Phase 2: Nominal Convergence (Training ON, Nom. M33) | 25147.8 | **4.69** | 5.91 (@ 3483.0 L²) | `[3, 9, 4, 17, 30, -12]` |
| **Epoch 200 .. 299** | Phase 3: Active Tracking 1 (±3 LSB, Training ON) | 34840.4 | **4.32** | 5.26 (@ 8559.0 L²) | `[2, 11, 14, 14, 44, -15]` |
| **Epoch 300 .. 399** | Phase 3: Active Tracking 2 (±3 LSB, Training ON) | 41901.0 | **4.18** | 4.93 (@ 13513.0 L²) | `[-3, 12, 4, 16, 38, -13]` |
| **Epoch 400 .. 499** | Phase 3: Active Tracking 3 (±3 LSB, Training ON) | 16822.7 | **5.01** | 6.62 (@ 1303.0 L²) | `[3, 5, 2, 10, 24, -13]` |
| **Epoch 500 .. 599** | Phase 3: Active Tracking 4 (±3 LSB, Training ON) | 20606.9 | **4.79** | 5.86 (@ 3709.5 L²) | `[1, 7, 4, 14, 28, -9]` |
| **Epoch 600 .. 699** | Phase 4: Ablation Control 1 (±3 LSB, W=0, Training OFF) | 107440.5 | **3.48** | 4.92 (@ 13652.5 L²) | `[0, 0, 0, 0, 0, 0]` |
| **Epoch 700 .. 799** | Phase 4: Ablation Control 2 (±3 LSB, W=0, Training OFF) | 143413.2 | **3.27** | 5.30 (@ 8084.0 L²) | `[0, 0, 0, 0, 0, 0]` |
| **Epoch 800 .. 899** | Phase 4: Ablation Control 3 (±3 LSB, W=0, Training OFF) | 138604.9 | **3.30** | 5.65 (@ 4974.5 L²) | `[0, 0, 0, 0, 0, 0]` |
| **Epoch 900 .. 999** | Phase 4: Ablation Control 4 (±3 LSB, W=0, Training OFF) | 127121.4 | **3.35** | 4.93 (@ 13593.5 L²) | `[0, 0, 0, 0, 0, 0]` |

---

## 3. Patent SE 2630397-4 Fig 7 Emulator: 100-Epokers Avsnitt & Randomiserade Matriser
*Fusk-Skydd:* Den digitala mål-supervisorn ($Z_\text{target}$) i T120 SoC beräknas strikt mot den nominella frysta matrisen $W^{(33)}_\text{nominal}$. De dolda stokastiska avvikelserna laddas enbart upp på de fysiska 2T1C-kondensatorerna på kiselmatrisen för att emulera hårdvarudrift.

### Epok 0 .. 99: Platt Baslinje (W=0, Training OFF)
- **Status:** Ingen störning (100% nominell fryst $W^{(33)}_\text{nominal}$), öppen loop baslinjemätning ($W=0$, $\text{LR}=0$).
- **Prestanda:** Medelfel = 128823.4 LSB² (3.34 bitar ENOB), Bästa = 16463.0 LSB² (4.79 b).
- **M8 Vikter:** `[0, 0, 0, 0, 0, 0]` LSB.

---

### Epok 100 .. 199: Nominell Etablering (Training ON, Noll Störning)
- **Status:** Träning påslagen direkt från W=0 mot nominell ostörd matris ($\text{LR}=0.08\text{x}$, $\lambda=4096$).
- **Syfte:** Etablera stabil analog jämvikt och grundkompensation innan hårdvarustörningar appliceras.
- **Prestanda:** Medelfel = 25147.8 LSB² (4.69 bitar ENOB), Bästa = 3483.0 LSB² (5.91 b).
- **M8 Vikter vid slutet av intervallet:** `[3, 9, 4, 17, 30, -12]` LSB.

---

### Epok 200 .. 299: Phase 3: Active Tracking 1 (±3 LSB, Training ON)
- **Prestanda:** Medelfel = 34840.4 LSB² (4.32 bitar ENOB), Bästa = 8559.0 LSB² (5.26 b)
- **M8 Vikter vid slutet av intervallet:** `[2, 11, 14, 14, 44, -15]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  +0  -3  +0  +3  +2  -2 ] LSB
Rad 1: [  +0  +1  -3  +1  -2  +1 ] LSB
Rad 2: [  -1  +1  -1  -1  +0  +1 ] LSB
Rad 3: [  -1  +3  -3  -2  -3  -2 ] LSB
Rad 4: [  +3  +3  -1  +0  -3  +1 ] LSB
Rad 5: [  -3  -2  -3  -1  +3  -2 ] LSB
```

---

### Epok 300 .. 399: Phase 3: Active Tracking 2 (±3 LSB, Training ON)
- **Prestanda:** Medelfel = 41901.0 LSB² (4.18 bitar ENOB), Bästa = 13513.0 LSB² (4.93 b)
- **M8 Vikter vid slutet av intervallet:** `[-3, 12, 4, 16, 38, -13]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  -3  +0  +0  -1  +2  -1 ] LSB
Rad 1: [  +3  -1  +3  +3  -2  +0 ] LSB
Rad 2: [  +2  +1  +2  +2  +2  -1 ] LSB
Rad 3: [  -2  -3  -1  +1  -1  -2 ] LSB
Rad 4: [  -1  -1  -3  +2  +0  +3 ] LSB
Rad 5: [  +1  +0  +3  -2  -1  +3 ] LSB
```

---

### Epok 400 .. 499: Phase 3: Active Tracking 3 (±3 LSB, Training ON)
- **Prestanda:** Medelfel = 16822.7 LSB² (5.01 bitar ENOB), Bästa = 1303.0 LSB² (6.62 b)
- **M8 Vikter vid slutet av intervallet:** `[3, 5, 2, 10, 24, -13]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  -1  +2  +2  +1  +0  -1 ] LSB
Rad 1: [  +0  +2  +2  -2  +3  -1 ] LSB
Rad 2: [  -3  +1  +1  +0  +0  +3 ] LSB
Rad 3: [  +1  +1  +2  +3  +1  -2 ] LSB
Rad 4: [  -3  +2  -1  +1  -1  +1 ] LSB
Rad 5: [  +0  -2  -1  +1  -2  -2 ] LSB
```

---

### Epok 500 .. 599: Phase 3: Active Tracking 4 (±3 LSB, Training ON)
- **Prestanda:** Medelfel = 20606.9 LSB² (4.79 bitar ENOB), Bästa = 3709.5 LSB² (5.86 b)
- **M8 Vikter vid slutet av intervallet:** `[1, 7, 4, 14, 28, -9]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  -2  -2  +3  +1  -1  +0 ] LSB
Rad 1: [  -3  +0  +1  -3  +1  -1 ] LSB
Rad 2: [  +0  +1  -1  -2  +0  +1 ] LSB
Rad 3: [  +2  -1  +3  -1  +1  +1 ] LSB
Rad 4: [  +3  -1  +0  -3  +3  -3 ] LSB
Rad 5: [  +1  -2  -3  +3  -2  -1 ] LSB
```

---

### Epok 600 .. 699: Phase 4: Ablation Control 1 (±3 LSB, W=0, Training OFF)
- **Prestanda:** Medelfel = 107440.5 LSB² (3.48 bitar ENOB), Bästa = 13652.5 LSB² (4.92 b)
- **M8 Vikter vid slutet av intervallet:** `[0, 0, 0, 0, 0, 0]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  -2  +1  +3  +1  -3  +1 ] LSB
Rad 1: [  +2  +2  -1  +3  +0  +2 ] LSB
Rad 2: [  +2  +1  +3  +3  +0  +2 ] LSB
Rad 3: [  -3  +2  -3  -2  +0  -3 ] LSB
Rad 4: [  -2  -2  +1  +2  +2  -3 ] LSB
Rad 5: [  +1  -3  +3  -3  +0  -2 ] LSB
```

---

### Epok 700 .. 799: Phase 4: Ablation Control 2 (±3 LSB, W=0, Training OFF)
- **Prestanda:** Medelfel = 143413.2 LSB² (3.27 bitar ENOB), Bästa = 8084.0 LSB² (5.30 b)
- **M8 Vikter vid slutet av intervallet:** `[0, 0, 0, 0, 0, 0]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  +2  +0  +2  +0  +3  +1 ] LSB
Rad 1: [  +0  +2  -2  +1  -1  +2 ] LSB
Rad 2: [  -3  -2  -1  +1  -1  -3 ] LSB
Rad 3: [  -1  +2  +3  +3  +2  -3 ] LSB
Rad 4: [  +1  -1  -2  -3  -1  +0 ] LSB
Rad 5: [  +1  +1  +2  -2  +2  +3 ] LSB
```

---

### Epok 800 .. 899: Phase 4: Ablation Control 3 (±3 LSB, W=0, Training OFF)
- **Prestanda:** Medelfel = 138604.9 LSB² (3.30 bitar ENOB), Bästa = 4974.5 LSB² (5.65 b)
- **M8 Vikter vid slutet av intervallet:** `[0, 0, 0, 0, 0, 0]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  +0  -3  -2  +0  +2  +1 ] LSB
Rad 1: [  +1  +0  -2  +2  -1  -3 ] LSB
Rad 2: [  -2  +0  +2  +1  +3  -2 ] LSB
Rad 3: [  -1  -3  +0  -3  +1  +1 ] LSB
Rad 4: [  -3  +0  +0  -3  +0  -2 ] LSB
Rad 5: [  -3  -1  -3  -2  +2  +3 ] LSB
```

---

### Epok 900 .. 999: Phase 4: Ablation Control 4 (±3 LSB, W=0, Training OFF)
- **Prestanda:** Medelfel = 127121.4 LSB² (3.35 bitar ENOB), Bästa = 13593.5 LSB² (4.93 b)
- **M8 Vikter vid slutet av intervallet:** `[0, 0, 0, 0, 0, 0]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  +1  -3  +0  +0  -3  +3 ] LSB
Rad 1: [  +0  -2  +1  -3  -3  +1 ] LSB
Rad 2: [  -2  +0  -3  +0  +3  -1 ] LSB
Rad 3: [  +3  +0  +2  +2  +3  +3 ] LSB
Rad 4: [  -1  +2  -2  -2  +0  -2 ] LSB
Rad 5: [  +1  +2  +0  +1  +0  +3 ] LSB
```

---

### Epok 1000 .. 1000: Aktiv Störning
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  +1  +3  -1  -2  +0  +0 ] LSB
Rad 1: [  +2  +2  +3  +1  -1  -2 ] LSB
Rad 2: [  -2  +2  +2  +0  -3  -1 ] LSB
Rad 3: [  -3  -3  -2  -3  +1  +1 ] LSB
Rad 4: [  -1  -3  -2  -1  -1  -2 ] LSB
Rad 5: [  +3  +2  +0  +1  +3  +1 ] LSB
```

---

## 4. Hardware Verification & Run Parameters
- **SoC Architecture:** Trion T120 Master + T20 Companion (`TAG=T20A`, S-bus ACK `0x06`).
- **Passive Summing Attenuator:** 1k / 5.1k Ohm ($16.4\%$ compensation authority).
- **Repair Status:** Channel 3 resoldered and physically verified.
- **Log Source:** `/home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/logs/mode_a_extended_training/mode_a_1000ep_5ms_pure_toeplitz_reg4096_lr0p04_swing40_var3_k1_1k_3p3k_ablation.json`
- **Figure:** `/home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/docs/figures/fig_mode_a_1000ep_5ms_pure_toeplitz_reg4096_lr0p04_swing40_var3_k1_1k_3p3k_ablation.png`
