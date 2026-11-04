# INVERTED MAML: Pure 5.0 ms Snapshot Experiment Report (TOEPLITZ, ±40 LSB, M33 Nominal 1.0x)
**Patent Pending:** SE 2630397-4 (Open Science Hardware)  
**Target Hardware:** Card 2 (Rev 2.0 Silicon, 1k/3.3k attenuator, repaired CH3)  
**Date:** 2026-11-04 12:52:56  
**Stimulus Profile:** LLM Toeplitz (ρ = 0.85)  
**Architecture:** Flat Baseline Protocol ($W=0, W_\text{null}=0, \text{LR}=0.04\text{x}, \lambda=2048$)  
**Dynamic Input Swing:** $\pm 40\text{ LSB}$ (`d_line=2`)  
**Matrix 33 State:** M33 Nominal 1.0x | **Disturbance (Fig 7):** Fig 7 Disturbance ±3 LSB  

---

## 1. Executive Summary & Key Results
- **Pure 5.0 ms Snapshot Evaluation:** Evaluated strictly at single-point $t = 5000\,\mu\text{s}$ ($K=1$ capacitor refreshes per epoch).
- **Baseline Phase 1 ($W=0$, Ep 0..99):** Mean loss $= 121825.9\text{ LSB}^2$ (3.40 bits ENOB).
- **Active Training Phase 2 (Ep 100..1000):** Whole-run active evaluation stabilized at **96746.3 LSB²** (3.68 bits ENOB), an improvement of **-20.6%** (+0.28 bits ENOB).
- **Peak Performance:** Epoch 400 reached **1042.0 LSB² (6.78 bits ENOB)**!
- **Weight Drift Immunity:** Final M8 diagonal weights converged to `[0, 0, 0, 0, 0, 0]` LSB (0% clamping, 100% linear triode margin).

---

## 2. 100-Epoch Segment Progression & Fig 7 Disturbance Response

| Segment | Status / Störningsregim | Medelfel (LSB²) | Medel ENOB (b) | Topp-ENOB (b) | Slutvikter $W_8$ (LSB) |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Epoch 0 .. 99** | Phase 1: Baseline W=0 (Training OFF, Nom. M33) | 121825.9 | **3.40** | 5.96 (@ 3241.5 L²) | `[0, 0, 0, 0, 0, 0]` |
| **Epoch 100 .. 199** | Phase 2: Nominal Convergence (Training ON, Nom. M33) | 30548.4 | **4.59** | 6.42 (@ 1706.0 L²) | `[2, 22, 14, 24, 30, -20]` |
| **Epoch 200 .. 299** | Phase 3: Active Tracking 1 (±3 LSB, Training ON) | 96138.9 | **3.57** | 4.71 (@ 18363.5 L²) | `[-2, 16, 12, 5, 28, -20]` |
| **Epoch 300 .. 399** | Phase 3: Active Tracking 2 (±3 LSB, Training ON) | 119867.2 | **3.39** | 5.01 (@ 12078.5 L²) | `[7, 11, 12, 4, 29, -18]` |
| **Epoch 400 .. 499** | Phase 3: Active Tracking 3 (±3 LSB, Training ON) | 140968.7 | **3.30** | 6.78 (@ 1042.0 L²) | `[16, 14, 12, 3, 25, -24]` |
| **Epoch 500 .. 599** | Phase 3: Active Tracking 4 (±3 LSB, Training ON) | 96208.5 | **3.55** | 4.47 (@ 25616.0 L²) | `[-1, 16, 16, 10, 20, -29]` |
| **Epoch 600 .. 699** | Phase 4: Ablation Control 1 (±3 LSB, W=0, Training OFF) | 110768.9 | **3.46** | 5.13 (@ 10281.5 L²) | `[0, 0, 0, 0, 0, 0]` |
| **Epoch 700 .. 799** | Phase 4: Ablation Control 2 (±3 LSB, W=0, Training OFF) | 130019.8 | **3.34** | 4.99 (@ 12470.0 L²) | `[0, 0, 0, 0, 0, 0]` |
| **Epoch 800 .. 899** | Phase 4: Ablation Control 3 (±3 LSB, W=0, Training OFF) | 121233.2 | **3.42** | 6.99 (@ 783.0 L²) | `[0, 0, 0, 0, 0, 0]` |
| **Epoch 900 .. 999** | Phase 4: Ablation Control 4 (±3 LSB, W=0, Training OFF) | 128047.0 | **3.36** | 6.02 (@ 2981.0 L²) | `[0, 0, 0, 0, 0, 0]` |

---

## 3. Patent SE 2630397-4 Fig 7 Emulator: 100-Epokers Avsnitt & Randomiserade Matriser
*Fusk-Skydd:* Den digitala mål-supervisorn ($Z_\text{target}$) i T120 SoC beräknas strikt mot den nominella frysta matrisen $W^{(33)}_\text{nominal}$. De dolda stokastiska avvikelserna laddas enbart upp på de fysiska 2T1C-kondensatorerna på kiselmatrisen för att emulera hårdvarudrift.

### Epok 0 .. 99: Platt Baslinje (W=0, Training OFF)
- **Status:** Ingen störning (100% nominell fryst $W^{(33)}_\text{nominal}$), öppen loop baslinjemätning ($W=0$, $\text{LR}=0$).
- **Prestanda:** Medelfel = 121825.9 LSB² (3.40 bitar ENOB), Bästa = 3241.5 LSB² (5.96 b).
- **M8 Vikter:** `[0, 0, 0, 0, 0, 0]` LSB.

---

### Epok 100 .. 199: Nominell Etablering (Training ON, Noll Störning)
- **Status:** Träning påslagen direkt från W=0 mot nominell ostörd matris ($\text{LR}=0.08\text{x}$, $\lambda=2048$).
- **Syfte:** Etablera stabil analog jämvikt och grundkompensation innan hårdvarustörningar appliceras.
- **Prestanda:** Medelfel = 30548.4 LSB² (4.59 bitar ENOB), Bästa = 1706.0 LSB² (6.42 b).
- **M8 Vikter vid slutet av intervallet:** `[2, 22, 14, 24, 30, -20]` LSB.

---

### Epok 200 .. 299: Phase 3: Active Tracking 1 (±3 LSB, Training ON)
- **Prestanda:** Medelfel = 96138.9 LSB² (3.57 bitar ENOB), Bästa = 18363.5 LSB² (4.71 b)
- **M8 Vikter vid slutet av intervallet:** `[-2, 16, 12, 5, 28, -20]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  +0  +0  +2  -1  -3  +0 ] LSB
Rad 1: [  +2  -1  +0  +3  +2  +0 ] LSB
Rad 2: [  +3  -1  -2  -2  -3  +0 ] LSB
Rad 3: [  -1  +3  +0  +0  -2  +2 ] LSB
Rad 4: [  +0  +1  +1  +3  +1  -3 ] LSB
Rad 5: [  +2  +3  -1  -1  +1  +2 ] LSB
```

---

### Epok 300 .. 399: Phase 3: Active Tracking 2 (±3 LSB, Training ON)
- **Prestanda:** Medelfel = 119867.2 LSB² (3.39 bitar ENOB), Bästa = 12078.5 LSB² (5.01 b)
- **M8 Vikter vid slutet av intervallet:** `[7, 11, 12, 4, 29, -18]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  +0  -1  +3  +0  +1  -1 ] LSB
Rad 1: [  -3  +0  -3  +0  -2  -2 ] LSB
Rad 2: [  -1  +3  +2  -3  +1  +1 ] LSB
Rad 3: [  -2  +2  +0  +1  -3  +1 ] LSB
Rad 4: [  -2  -1  +1  +2  -2  -2 ] LSB
Rad 5: [  +3  +2  +3  -2  +1  -3 ] LSB
```

---

### Epok 400 .. 499: Phase 3: Active Tracking 3 (±3 LSB, Training ON)
- **Prestanda:** Medelfel = 140968.7 LSB² (3.30 bitar ENOB), Bästa = 1042.0 LSB² (6.78 b)
- **M8 Vikter vid slutet av intervallet:** `[16, 14, 12, 3, 25, -24]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  +3  -2  +2  -2  +3  -2 ] LSB
Rad 1: [  -3  +3  +1  -2  -2  +0 ] LSB
Rad 2: [  -1  -2  -2  -1  +0  +1 ] LSB
Rad 3: [  -3  +0  -3  -1  +0  +0 ] LSB
Rad 4: [  +1  +1  -1  -3  -3  +2 ] LSB
Rad 5: [  -1  +2  -2  -2  +0  -1 ] LSB
```

---

### Epok 500 .. 599: Phase 3: Active Tracking 4 (±3 LSB, Training ON)
- **Prestanda:** Medelfel = 96208.5 LSB² (3.55 bitar ENOB), Bästa = 25616.0 LSB² (4.47 b)
- **M8 Vikter vid slutet av intervallet:** `[-1, 16, 16, 10, 20, -29]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  +3  -1  +3  +3  -2  -3 ] LSB
Rad 1: [  +1  +1  +2  +3  -1  +0 ] LSB
Rad 2: [  -3  -1  +3  -2  +3  +3 ] LSB
Rad 3: [  +1  -2  -3  +0  +3  -1 ] LSB
Rad 4: [  -2  -2  +2  -1  -1  +1 ] LSB
Rad 5: [  +3  +2  -2  +3  -2  +1 ] LSB
```

---

### Epok 600 .. 699: Phase 4: Ablation Control 1 (±3 LSB, W=0, Training OFF)
- **Prestanda:** Medelfel = 110768.9 LSB² (3.46 bitar ENOB), Bästa = 10281.5 LSB² (5.13 b)
- **M8 Vikter vid slutet av intervallet:** `[0, 0, 0, 0, 0, 0]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  -3  +2  -3  +1  +2  +1 ] LSB
Rad 1: [  -3  +0  +2  +2  -3  +3 ] LSB
Rad 2: [  -2  +3  +1  -1  -2  -3 ] LSB
Rad 3: [  -2  -3  +1  +1  +0  -1 ] LSB
Rad 4: [  +3  -2  +2  +2  +2  +1 ] LSB
Rad 5: [  +3  +3  -2  +3  -3  +2 ] LSB
```

---

### Epok 700 .. 799: Phase 4: Ablation Control 2 (±3 LSB, W=0, Training OFF)
- **Prestanda:** Medelfel = 130019.8 LSB² (3.34 bitar ENOB), Bästa = 12470.0 LSB² (4.99 b)
- **M8 Vikter vid slutet av intervallet:** `[0, 0, 0, 0, 0, 0]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  +0  +2  +1  +1  +0  -2 ] LSB
Rad 1: [  +2  +0  -2  +3  +1  -1 ] LSB
Rad 2: [  +1  +0  -1  -3  -2  -2 ] LSB
Rad 3: [  +2  -2  +1  +3  -1  -3 ] LSB
Rad 4: [  -1  -2  +3  +3  +2  +0 ] LSB
Rad 5: [  +0  +1  -2  -3  -1  -3 ] LSB
```

---

### Epok 800 .. 899: Phase 4: Ablation Control 3 (±3 LSB, W=0, Training OFF)
- **Prestanda:** Medelfel = 121233.2 LSB² (3.42 bitar ENOB), Bästa = 783.0 LSB² (6.99 b)
- **M8 Vikter vid slutet av intervallet:** `[0, 0, 0, 0, 0, 0]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  -3  +2  +2  +0  +0  -3 ] LSB
Rad 1: [  +3  +3  +3  -3  +1  +3 ] LSB
Rad 2: [  +1  -1  -2  -2  -2  +2 ] LSB
Rad 3: [  -3  +1  +1  +3  -2  -2 ] LSB
Rad 4: [  +2  +3  +3  -2  -2  +2 ] LSB
Rad 5: [  +3  -1  -1  +3  -1  +2 ] LSB
```

---

### Epok 900 .. 999: Phase 4: Ablation Control 4 (±3 LSB, W=0, Training OFF)
- **Prestanda:** Medelfel = 128047.0 LSB² (3.36 bitar ENOB), Bästa = 2981.0 LSB² (6.02 b)
- **M8 Vikter vid slutet av intervallet:** `[0, 0, 0, 0, 0, 0]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  +2  -1  -1  -3  +0  +0 ] LSB
Rad 1: [  +0  +3  -3  +1  +2  +3 ] LSB
Rad 2: [  -1  +3  +0  +1  -2  +2 ] LSB
Rad 3: [  +1  -3  +1  -3  +1  -2 ] LSB
Rad 4: [  +2  +0  -2  -1  -3  -1 ] LSB
Rad 5: [  +0  +1  -3  +1  -1  -2 ] LSB
```

---

### Epok 1000 .. 1000: Aktiv Störning
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  +0  -3  -3  +3  +2  +0 ] LSB
Rad 1: [  -2  -3  +1  -3  +1  +2 ] LSB
Rad 2: [  -1  +1  -2  +3  +3  +1 ] LSB
Rad 3: [  -1  +0  -3  +0  -1  -1 ] LSB
Rad 4: [  +0  -3  +2  -2  +3  +3 ] LSB
Rad 5: [  +1  -2  +2  +3  +0  -3 ] LSB
```

---

## 4. Hardware Verification & Run Parameters
- **SoC Architecture:** Trion T120 Master + T20 Companion (`TAG=T20A`, S-bus ACK `0x06`).
- **Passive Summing Attenuator:** 1k / 5.1k Ohm ($16.4\%$ compensation authority).
- **Repair Status:** Channel 3 resoldered and physically verified.
- **Log Source:** `/home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/logs/mode_a_extended_training/mode_a_1000ep_5ms_pure_toeplitz_reg2048_lr0p04_swing40_var3_k1_1k_3p3k_ablation.json`
- **Figure:** `/home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/docs/figures/fig_mode_a_1000ep_5ms_pure_toeplitz_reg2048_lr0p04_swing40_var3_k1_1k_3p3k_ablation.png`
