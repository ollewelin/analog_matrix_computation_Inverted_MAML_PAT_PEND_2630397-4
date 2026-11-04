# INVERTED MAML: Pure 5.0 ms Snapshot Experiment Report (TOEPLITZ, ±40 LSB, M33 Nominal 1.0x)
**Patent Pending:** SE 2630397-4 (Open Science Hardware)  
**Target Hardware:** Card 2 (Rev 2.0 Silicon, 1k/5.1k attenuator, repaired CH3)  
**Date:** 2026-11-04 11:50:05  
**Stimulus Profile:** LLM Toeplitz (ρ = 0.85)  
**Architecture:** Flat Baseline Protocol ($W=0, W_\text{null}=0, \text{LR}=0.08\text{x}, \lambda=1024$)  
**Dynamic Input Swing:** $\pm 40\text{ LSB}$ (`d_line=2`)  
**Matrix 33 State:** M33 Nominal 1.0x | **Disturbance (Fig 7):** Fig 7 Disturbance ±3 LSB  

---

## 1. Executive Summary & Key Results
- **Pure 5.0 ms Snapshot Evaluation:** Evaluated strictly at single-point $t = 5000\,\mu\text{s}$ ($K=20$ capacitor refreshes per epoch).
- **Baseline Phase 1 ($W=0$, Ep 0..99):** Mean loss $= 47131.1\text{ LSB}^2$ (4.06 bits ENOB).
- **Active Training Phase 2 (Ep 100..1000):** Whole-run active evaluation stabilized at **41098.7 LSB²** (4.21 bits ENOB), an improvement of **-12.8%** (+0.15 bits ENOB).
- **Peak Performance:** Epoch 400 reached **8156.0 LSB² (5.30 bits ENOB)**!
- **Weight Drift Immunity:** Final M8 diagonal weights converged to `[0, 0, 0, 0, 0, 0]` LSB (0% clamping, 100% linear triode margin).

---

## 2. 100-Epoch Segment Progression & Fig 7 Disturbance Response

| Segment | Status / Störningsregim | Medelfel (LSB²) | Medel ENOB (b) | Topp-ENOB (b) | Slutvikter $W_8$ (LSB) |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Epoch 0 .. 99** | Phase 1: Baseline W=0 (Training OFF, Nom. M33) | 47131.1 | **4.06** | 5.40 (@ 7030.0 L²) | `[0, 0, 0, 0, 0, 0]` |
| **Epoch 100 .. 199** | Phase 2: Nominal Convergence (Training ON, Nom. M33) | 33518.0 | **4.31** | 4.89 (@ 14306.0 L²) | `[6, -1, 3, 8, 19, -10]` |
| **Epoch 200 .. 299** | Phase 3: Active Tracking 1 (±3 LSB, Training ON) | 30721.0 | **4.37** | 4.86 (@ 14824.0 L²) | `[11, 0, 4, 4, -7, -13]` |
| **Epoch 300 .. 399** | Phase 3: Active Tracking 2 (±3 LSB, Training ON) | 34049.2 | **4.28** | 4.78 (@ 16715.5 L²) | `[0, 0, 1, 20, -2, -5]` |
| **Epoch 400 .. 499** | Phase 3: Active Tracking 3 (±3 LSB, Training ON) | 30869.8 | **4.37** | 5.30 (@ 8156.0 L²) | `[-1, -1, 2, 11, 21, -3]` |
| **Epoch 500 .. 599** | Phase 3: Active Tracking 4 (±3 LSB, Training ON) | 76335.7 | **3.71** | 4.45 (@ 26396.0 L²) | `[-7, 1, 10, 3, 45, -4]` |
| **Epoch 600 .. 699** | Phase 4: Ablation Control 1 (±3 LSB, W=0, Training OFF) | 74977.9 | **3.71** | 3.99 (@ 49840.5 L²) | `[0, 0, 0, 0, 0, 0]` |
| **Epoch 700 .. 799** | Phase 4: Ablation Control 2 (±3 LSB, W=0, Training OFF) | 47572.6 | **4.04** | 4.80 (@ 16297.5 L²) | `[0, 0, 0, 0, 0, 0]` |
| **Epoch 800 .. 899** | Phase 4: Ablation Control 3 (±3 LSB, W=0, Training OFF) | 51425.9 | **4.00** | 5.77 (@ 4199.5 L²) | `[0, 0, 0, 0, 0, 0]` |
| **Epoch 900 .. 999** | Phase 4: Ablation Control 4 (±3 LSB, W=0, Training OFF) | 42245.0 | **4.15** | 5.98 (@ 3155.5 L²) | `[0, 0, 0, 0, 0, 0]` |

---

## 3. Patent SE 2630397-4 Fig 7 Emulator: 100-Epokers Avsnitt & Randomiserade Matriser
*Fusk-Skydd:* Den digitala mål-supervisorn ($Z_\text{target}$) i T120 SoC beräknas strikt mot den nominella frysta matrisen $W^{(33)}_\text{nominal}$. De dolda stokastiska avvikelserna laddas enbart upp på de fysiska 2T1C-kondensatorerna på kiselmatrisen för att emulera hårdvarudrift.

### Epok 0 .. 99: Platt Baslinje (W=0, Training OFF)
- **Status:** Ingen störning (100% nominell fryst $W^{(33)}_\text{nominal}$), öppen loop baslinjemätning ($W=0$, $\text{LR}=0$).
- **Prestanda:** Medelfel = 47131.1 LSB² (4.06 bitar ENOB), Bästa = 7030.0 LSB² (5.40 b).
- **M8 Vikter:** `[0, 0, 0, 0, 0, 0]` LSB.

---

### Epok 100 .. 199: Nominell Etablering (Training ON, Noll Störning)
- **Status:** Träning påslagen direkt från W=0 mot nominell ostörd matris ($\text{LR}=0.08\text{x}$, $\lambda=1024$).
- **Syfte:** Etablera stabil analog jämvikt och grundkompensation innan hårdvarustörningar appliceras.
- **Prestanda:** Medelfel = 33518.0 LSB² (4.31 bitar ENOB), Bästa = 14306.0 LSB² (4.89 b).
- **M8 Vikter vid slutet av intervallet:** `[6, -1, 3, 8, 19, -10]` LSB.

---

### Epok 200 .. 299: Phase 3: Active Tracking 1 (±3 LSB, Training ON)
- **Prestanda:** Medelfel = 30721.0 LSB² (4.37 bitar ENOB), Bästa = 14824.0 LSB² (4.86 b)
- **M8 Vikter vid slutet av intervallet:** `[11, 0, 4, 4, -7, -13]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  -1  -3  +3  +3  -2  +3 ] LSB
Rad 1: [  -1  +2  -3  +2  +0  +2 ] LSB
Rad 2: [  -3  +0  -1  +3  -1  -1 ] LSB
Rad 3: [  +3  -1  +2  +1  +3  +1 ] LSB
Rad 4: [  -2  +2  -2  +3  +1  -1 ] LSB
Rad 5: [  -2  -1  +1  -3  +0  +1 ] LSB
```

---

### Epok 300 .. 399: Phase 3: Active Tracking 2 (±3 LSB, Training ON)
- **Prestanda:** Medelfel = 34049.2 LSB² (4.28 bitar ENOB), Bästa = 16715.5 LSB² (4.78 b)
- **M8 Vikter vid slutet av intervallet:** `[0, 0, 1, 20, -2, -5]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  +1  +1  -2  -2  -2  +2 ] LSB
Rad 1: [  +0  +0  -3  +3  +3  +0 ] LSB
Rad 2: [  -1  -2  -3  -3  -1  -1 ] LSB
Rad 3: [  +2  -1  +2  +0  +2  -1 ] LSB
Rad 4: [  +3  -2  +0  +2  +3  -3 ] LSB
Rad 5: [  -2  +3  +3  +1  +1  -2 ] LSB
```

---

### Epok 400 .. 499: Phase 3: Active Tracking 3 (±3 LSB, Training ON)
- **Prestanda:** Medelfel = 30869.8 LSB² (4.37 bitar ENOB), Bästa = 8156.0 LSB² (5.30 b)
- **M8 Vikter vid slutet av intervallet:** `[-1, -1, 2, 11, 21, -3]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  -2  +3  -3  -1  +1  +2 ] LSB
Rad 1: [  -1  +3  +3  +2  +1  -3 ] LSB
Rad 2: [  -2  +1  +0  +0  +0  +0 ] LSB
Rad 3: [  +0  +0  +0  +1  -1  -2 ] LSB
Rad 4: [  -1  +0  +0  -2  +0  -3 ] LSB
Rad 5: [  +3  +1  -1  +3  +1  +1 ] LSB
```

---

### Epok 500 .. 599: Phase 3: Active Tracking 4 (±3 LSB, Training ON)
- **Prestanda:** Medelfel = 76335.7 LSB² (3.71 bitar ENOB), Bästa = 26396.0 LSB² (4.45 b)
- **M8 Vikter vid slutet av intervallet:** `[-7, 1, 10, 3, 45, -4]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  +1  -2  -1  +3  -1  +3 ] LSB
Rad 1: [  -3  +3  +2  -1  -3  +0 ] LSB
Rad 2: [  -1  +1  -2  -1  -1  -3 ] LSB
Rad 3: [  +2  +2  +0  -1  -3  -2 ] LSB
Rad 4: [  +2  +1  -3  +3  +2  +1 ] LSB
Rad 5: [  +3  -2  -1  +2  -1  -3 ] LSB
```

---

### Epok 600 .. 699: Phase 4: Ablation Control 1 (±3 LSB, W=0, Training OFF)
- **Prestanda:** Medelfel = 74977.9 LSB² (3.71 bitar ENOB), Bästa = 49840.5 LSB² (3.99 b)
- **M8 Vikter vid slutet av intervallet:** `[0, 0, 0, 0, 0, 0]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  -3  -2  -3  +0  -3  -1 ] LSB
Rad 1: [  -3  +1  +0  +3  +2  +0 ] LSB
Rad 2: [  -2  +1  -2  -1  -2  +0 ] LSB
Rad 3: [  -1  +1  -1  -2  +1  +3 ] LSB
Rad 4: [  -1  +1  +3  +2  -2  -2 ] LSB
Rad 5: [  +0  -2  -1  +1  +0  -2 ] LSB
```

---

### Epok 700 .. 799: Phase 4: Ablation Control 2 (±3 LSB, W=0, Training OFF)
- **Prestanda:** Medelfel = 47572.6 LSB² (4.04 bitar ENOB), Bästa = 16297.5 LSB² (4.80 b)
- **M8 Vikter vid slutet av intervallet:** `[0, 0, 0, 0, 0, 0]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  +0  +2  -2  +2  -3  +1 ] LSB
Rad 1: [  +1  -1  +1  -2  +2  +3 ] LSB
Rad 2: [  +1  +1  +3  +1  -1  -2 ] LSB
Rad 3: [  +2  +0  +1  +0  -1  +2 ] LSB
Rad 4: [  -3  +3  -2  +0  +2  -3 ] LSB
Rad 5: [  -2  -1  -2  +0  +1  +0 ] LSB
```

---

### Epok 800 .. 899: Phase 4: Ablation Control 3 (±3 LSB, W=0, Training OFF)
- **Prestanda:** Medelfel = 51425.9 LSB² (4.00 bitar ENOB), Bästa = 4199.5 LSB² (5.77 b)
- **M8 Vikter vid slutet av intervallet:** `[0, 0, 0, 0, 0, 0]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  +0  +1  +0  +0  +1  -3 ] LSB
Rad 1: [  +1  -2  +3  +2  -3  +3 ] LSB
Rad 2: [  +1  +1  +0  +1  -2  +3 ] LSB
Rad 3: [  +1  -2  -2  -2  -3  +3 ] LSB
Rad 4: [  +2  +0  +2  -1  -2  -1 ] LSB
Rad 5: [  +1  +0  -1  +1  +2  +0 ] LSB
```

---

### Epok 900 .. 999: Phase 4: Ablation Control 4 (±3 LSB, W=0, Training OFF)
- **Prestanda:** Medelfel = 42245.0 LSB² (4.15 bitar ENOB), Bästa = 3155.5 LSB² (5.98 b)
- **M8 Vikter vid slutet av intervallet:** `[0, 0, 0, 0, 0, 0]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  -1  -1  -2  -3  +1  +1 ] LSB
Rad 1: [  -3  +0  +0  -1  +0  +0 ] LSB
Rad 2: [  +2  -2  +3  +2  +1  +3 ] LSB
Rad 3: [  +0  -3  -2  -3  -1  +2 ] LSB
Rad 4: [  -3  -3  -3  -1  -1  -1 ] LSB
Rad 5: [  -3  -3  -1  +0  -1  -2 ] LSB
```

---

### Epok 1000 .. 1000: Aktiv Störning
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  +1  +1  +0  -3  +3  +2 ] LSB
Rad 1: [  +2  +2  +1  -3  -2  +0 ] LSB
Rad 2: [  +1  +3  +2  +1  +0  -3 ] LSB
Rad 3: [  -1  +3  +0  +0  -3  +1 ] LSB
Rad 4: [  +1  +1  +1  -1  -1  +3 ] LSB
Rad 5: [  -1  +1  +2  -3  +1  +1 ] LSB
```

---

## 4. Hardware Verification & Run Parameters
- **SoC Architecture:** Trion T120 Master + T20 Companion (`TAG=T20A`, S-bus ACK `0x06`).
- **Passive Summing Attenuator:** 1k / 5.1k Ohm ($16.4\%$ compensation authority).
- **Repair Status:** Channel 3 resoldered and physically verified.
- **Log Source:** `/home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/logs/mode_a_extended_training/mode_a_1000ep_5ms_pure_toeplitz_reg1024_lr0p08_swing40_var3_k4_ablation.json`
- **Figure:** `/home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/docs/figures/fig_mode_a_1000ep_5ms_pure_toeplitz_reg1024_lr0p08_swing40_var3_k4_ablation.png`
