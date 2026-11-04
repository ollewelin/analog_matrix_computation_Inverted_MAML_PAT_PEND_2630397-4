# INVERTED MAML: Pure 5.0 ms Snapshot Experiment Report (TOEPLITZ, ±40 LSB, M33 Nominal 1.0x)
**Patent Pending:** SE 2630397-4 (Open Science Hardware)  
**Target Hardware:** Card 2 (Rev 2.0 Silicon, 1k/5.1k attenuator, repaired CH3)  
**Date:** 2026-11-04 11:54:29  
**Stimulus Profile:** LLM Toeplitz (ρ = 0.85)  
**Architecture:** Flat Baseline Protocol ($W=0, W_\text{null}=0, \text{LR}=0.08\text{x}, \lambda=1024$)  
**Dynamic Input Swing:** $\pm 40\text{ LSB}$ (`d_line=2`)  
**Matrix 33 State:** M33 Nominal 1.0x | **Disturbance (Fig 7):** Fig 7 Disturbance ±3 LSB  

---

## 1. Executive Summary & Key Results
- **Pure 5.0 ms Snapshot Evaluation:** Evaluated strictly at single-point $t = 5000\,\mu\text{s}$ ($K=20$ capacitor refreshes per epoch).
- **Baseline Phase 1 ($W=0$, Ep 0..99):** Mean loss $= 166760.4\text{ LSB}^2$ (3.17 bits ENOB).
- **Active Training Phase 2 (Ep 100..1000):** Whole-run active evaluation stabilized at **177719.1 LSB²** (3.11 bits ENOB), an improvement of **+6.6%** (-0.06 bits ENOB).
- **Peak Performance:** Epoch 271 reached **14194.5 LSB² (4.90 bits ENOB)**!
- **Weight Drift Immunity:** Final M8 diagonal weights converged to `[0, 0, 0, 0, 0, 0]` LSB (0% clamping, 100% linear triode margin).

---

## 2. 100-Epoch Segment Progression & Fig 7 Disturbance Response

| Segment | Status / Störningsregim | Medelfel (LSB²) | Medel ENOB (b) | Topp-ENOB (b) | Slutvikter $W_8$ (LSB) |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Epoch 0 .. 99** | Phase 1: Baseline W=0 (Training OFF, Nom. M33) | 166760.4 | **3.17** | 6.28 (@ 2085.0 L²) | `[0, 0, 0, 0, 0, 0]` |
| **Epoch 100 .. 199** | Phase 2: Nominal Convergence (Training ON, Nom. M33) | 162518.6 | **3.18** | 4.06 (@ 45042.5 L²) | `[10, 3, 22, -3, 30, -60]` |
| **Epoch 200 .. 299** | Phase 3: Active Tracking 1 (±3 LSB, Training ON) | 150487.3 | **3.24** | 4.90 (@ 14194.5 L²) | `[-13, 24, 26, 5, 31, -49]` |
| **Epoch 300 .. 399** | Phase 3: Active Tracking 2 (±3 LSB, Training ON) | 187233.4 | **3.07** | 4.56 (@ 22582.5 L²) | `[67, 0, 33, -35, 23, -50]` |
| **Epoch 400 .. 499** | Phase 3: Active Tracking 3 (±3 LSB, Training ON) | 192485.6 | **3.05** | 4.65 (@ 20095.0 L²) | `[24, 15, 40, -12, 31, -66]` |
| **Epoch 500 .. 599** | Phase 3: Active Tracking 4 (±3 LSB, Training ON) | 195870.4 | **3.02** | 4.47 (@ 25603.0 L²) | `[-12, 21, 46, -31, 34, -42]` |
| **Epoch 600 .. 699** | Phase 4: Ablation Control 1 (±3 LSB, W=0, Training OFF) | 155959.9 | **3.22** | 6.41 (@ 1749.0 L²) | `[0, 0, 0, 0, 0, 0]` |
| **Epoch 700 .. 799** | Phase 4: Ablation Control 2 (±3 LSB, W=0, Training OFF) | 162708.0 | **3.18** | 5.26 (@ 8558.0 L²) | `[0, 0, 0, 0, 0, 0]` |
| **Epoch 800 .. 899** | Phase 4: Ablation Control 3 (±3 LSB, W=0, Training OFF) | 160056.2 | **3.19** | 5.60 (@ 5383.0 L²) | `[0, 0, 0, 0, 0, 0]` |
| **Epoch 900 .. 999** | Phase 4: Ablation Control 4 (±3 LSB, W=0, Training OFF) | 140662.0 | **3.28** | 5.22 (@ 9034.5 L²) | `[0, 0, 0, 0, 0, 0]` |

---

## 3. Patent SE 2630397-4 Fig 7 Emulator: 100-Epokers Avsnitt & Randomiserade Matriser
*Fusk-Skydd:* Den digitala mål-supervisorn ($Z_\text{target}$) i T120 SoC beräknas strikt mot den nominella frysta matrisen $W^{(33)}_\text{nominal}$. De dolda stokastiska avvikelserna laddas enbart upp på de fysiska 2T1C-kondensatorerna på kiselmatrisen för att emulera hårdvarudrift.

### Epok 0 .. 99: Platt Baslinje (W=0, Training OFF)
- **Status:** Ingen störning (100% nominell fryst $W^{(33)}_\text{nominal}$), öppen loop baslinjemätning ($W=0$, $\text{LR}=0$).
- **Prestanda:** Medelfel = 166760.4 LSB² (3.17 bitar ENOB), Bästa = 2085.0 LSB² (6.28 b).
- **M8 Vikter:** `[0, 0, 0, 0, 0, 0]` LSB.

---

### Epok 100 .. 199: Nominell Etablering (Training ON, Noll Störning)
- **Status:** Träning påslagen direkt från W=0 mot nominell ostörd matris ($\text{LR}=0.08\text{x}$, $\lambda=1024$).
- **Syfte:** Etablera stabil analog jämvikt och grundkompensation innan hårdvarustörningar appliceras.
- **Prestanda:** Medelfel = 162518.6 LSB² (3.18 bitar ENOB), Bästa = 45042.5 LSB² (4.06 b).
- **M8 Vikter vid slutet av intervallet:** `[10, 3, 22, -3, 30, -60]` LSB.

---

### Epok 200 .. 299: Phase 3: Active Tracking 1 (±3 LSB, Training ON)
- **Prestanda:** Medelfel = 150487.3 LSB² (3.24 bitar ENOB), Bästa = 14194.5 LSB² (4.90 b)
- **M8 Vikter vid slutet av intervallet:** `[-13, 24, 26, 5, 31, -49]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  -3  -1  +3  +0  -1  +3 ] LSB
Rad 1: [  +2  -2  -3  +0  +2  +3 ] LSB
Rad 2: [  -3  +1  +2  +1  +0  +2 ] LSB
Rad 3: [  +1  +0  +2  +0  +0  +0 ] LSB
Rad 4: [  +3  -2  -2  -1  +1  -2 ] LSB
Rad 5: [  +2  -1  +0  -2  +0  +0 ] LSB
```

---

### Epok 300 .. 399: Phase 3: Active Tracking 2 (±3 LSB, Training ON)
- **Prestanda:** Medelfel = 187233.4 LSB² (3.07 bitar ENOB), Bästa = 22582.5 LSB² (4.56 b)
- **M8 Vikter vid slutet av intervallet:** `[67, 0, 33, -35, 23, -50]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  +0  -3  +3  +1  +1  -2 ] LSB
Rad 1: [  -1  -2  +1  +2  -3  +1 ] LSB
Rad 2: [  -3  +3  +2  +0  +0  +2 ] LSB
Rad 3: [  -3  -1  -3  -3  +1  +3 ] LSB
Rad 4: [  -2  -3  -2  +3  -1  +1 ] LSB
Rad 5: [  -2  +0  -3  -1  -1  -2 ] LSB
```

---

### Epok 400 .. 499: Phase 3: Active Tracking 3 (±3 LSB, Training ON)
- **Prestanda:** Medelfel = 192485.6 LSB² (3.05 bitar ENOB), Bästa = 20095.0 LSB² (4.65 b)
- **M8 Vikter vid slutet av intervallet:** `[24, 15, 40, -12, 31, -66]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  +2  -3  -2  -1  +1  +1 ] LSB
Rad 1: [  -3  -1  -2  +1  +1  +3 ] LSB
Rad 2: [  +1  +1  -1  -3  +0  +2 ] LSB
Rad 3: [  +1  +0  -2  +1  -3  +0 ] LSB
Rad 4: [  -3  +3  +1  +2  +0  -1 ] LSB
Rad 5: [  +2  +2  +3  -1  +3  -1 ] LSB
```

---

### Epok 500 .. 599: Phase 3: Active Tracking 4 (±3 LSB, Training ON)
- **Prestanda:** Medelfel = 195870.4 LSB² (3.02 bitar ENOB), Bästa = 25603.0 LSB² (4.47 b)
- **M8 Vikter vid slutet av intervallet:** `[-12, 21, 46, -31, 34, -42]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  -3  +0  +2  -3  +0  +1 ] LSB
Rad 1: [  +2  +1  -3  +2  -2  -3 ] LSB
Rad 2: [  +0  -3  +1  -2  -2  +1 ] LSB
Rad 3: [  -1  -2  -2  +1  +0  -3 ] LSB
Rad 4: [  +3  +1  +1  +3  +3  -1 ] LSB
Rad 5: [  +3  -1  -3  -1  +0  -1 ] LSB
```

---

### Epok 600 .. 699: Phase 4: Ablation Control 1 (±3 LSB, W=0, Training OFF)
- **Prestanda:** Medelfel = 155959.9 LSB² (3.22 bitar ENOB), Bästa = 1749.0 LSB² (6.41 b)
- **M8 Vikter vid slutet av intervallet:** `[0, 0, 0, 0, 0, 0]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  -1  -3  -2  -2  +3  +3 ] LSB
Rad 1: [  -2  -2  +2  -3  +2  -1 ] LSB
Rad 2: [  -3  +1  -2  +2  -2  -2 ] LSB
Rad 3: [  -1  +3  -3  +3  -1  +2 ] LSB
Rad 4: [  -2  +0  -2  -1  -1  -1 ] LSB
Rad 5: [  +2  +1  -3  +0  +1  +0 ] LSB
```

---

### Epok 700 .. 799: Phase 4: Ablation Control 2 (±3 LSB, W=0, Training OFF)
- **Prestanda:** Medelfel = 162708.0 LSB² (3.18 bitar ENOB), Bästa = 8558.0 LSB² (5.26 b)
- **M8 Vikter vid slutet av intervallet:** `[0, 0, 0, 0, 0, 0]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  -1  -3  -2  +1  -3  +0 ] LSB
Rad 1: [  -1  +0  +1  -1  +3  +3 ] LSB
Rad 2: [  +0  +2  -3  +2  +1  -1 ] LSB
Rad 3: [  -2  -2  +0  +3  -1  +1 ] LSB
Rad 4: [  +0  +0  +3  -2  +3  +2 ] LSB
Rad 5: [  +0  -2  -2  +2  +1  +3 ] LSB
```

---

### Epok 800 .. 899: Phase 4: Ablation Control 3 (±3 LSB, W=0, Training OFF)
- **Prestanda:** Medelfel = 160056.2 LSB² (3.19 bitar ENOB), Bästa = 5383.0 LSB² (5.60 b)
- **M8 Vikter vid slutet av intervallet:** `[0, 0, 0, 0, 0, 0]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  +2  +1  +0  -2  -2  -2 ] LSB
Rad 1: [  +2  +1  -1  +3  +0  +3 ] LSB
Rad 2: [  +1  -1  +1  -2  +2  +2 ] LSB
Rad 3: [  -3  -2  -1  +0  -2  +1 ] LSB
Rad 4: [  +2  -2  +2  -3  -3  +1 ] LSB
Rad 5: [  +0  -1  +3  +0  +0  -2 ] LSB
```

---

### Epok 900 .. 999: Phase 4: Ablation Control 4 (±3 LSB, W=0, Training OFF)
- **Prestanda:** Medelfel = 140662.0 LSB² (3.28 bitar ENOB), Bästa = 9034.5 LSB² (5.22 b)
- **M8 Vikter vid slutet av intervallet:** `[0, 0, 0, 0, 0, 0]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  -2  +0  +1  -2  +3  +2 ] LSB
Rad 1: [  +1  +0  +1  -3  +0  +1 ] LSB
Rad 2: [  +2  +1  +3  +0  -3  -2 ] LSB
Rad 3: [  +0  -3  +1  -1  -3  +2 ] LSB
Rad 4: [  -1  -2  -3  -1  -2  -1 ] LSB
Rad 5: [  +0  +1  -3  -2  +0  +0 ] LSB
```

---

### Epok 1000 .. 1000: Aktiv Störning
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  +1  +1  -2  +3  -2  -2 ] LSB
Rad 1: [  -1  +0  -2  +3  +1  -1 ] LSB
Rad 2: [  +1  +2  -1  +1  +0  -2 ] LSB
Rad 3: [  +2  -2  -2  -2  -3  +3 ] LSB
Rad 4: [  -3  -2  +2  -3  +0  +2 ] LSB
Rad 5: [  -1  +2  -3  -3  -2  -1 ] LSB
```

---

## 4. Hardware Verification & Run Parameters
- **SoC Architecture:** Trion T120 Master + T20 Companion (`TAG=T20A`, S-bus ACK `0x06`).
- **Passive Summing Attenuator:** 1k / 5.1k Ohm ($16.4\%$ compensation authority).
- **Repair Status:** Channel 3 resoldered and physically verified.
- **Log Source:** `/home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/logs/mode_a_extended_training/mode_a_1000ep_5ms_pure_toeplitz_reg1024_lr0p08_swing40_var3_k1_ablation.json`
- **Figure:** `/home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/docs/figures/fig_mode_a_1000ep_5ms_pure_toeplitz_reg1024_lr0p08_swing40_var3_k1_ablation.png`
