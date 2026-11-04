# INVERTED MAML: Pure 5.0 ms Snapshot Experiment Report (TOEPLITZ, ±40 LSB, M33 Nominal 1.0x)
**Patent Pending:** SE 2630397-4 (Open Science Hardware)  
**Target Hardware:** Card 2 (Rev 2.0 Silicon, 1k/3.3k attenuator, repaired CH3)  
**Date:** 2026-11-04 13:10:16  
**Stimulus Profile:** LLM Toeplitz (ρ = 0.85)  
**Architecture:** Flat Baseline Protocol ($W=0, W_\text{null}=0, \text{LR}=0.02\text{x}, \lambda=2048$)  
**Dynamic Input Swing:** $\pm 40\text{ LSB}$ (`d_line=2`)  
**Matrix 33 State:** M33 Nominal 1.0x | **Disturbance (Fig 7):** Fig 7 Disturbance ±5 LSB  

---

## 1. Executive Summary & Key Results
- **Pure 5.0 ms Snapshot Evaluation:** Evaluated strictly at single-point $t = 5000\,\mu\text{s}$ ($K=1$ capacitor refreshes per epoch).
- **Baseline Phase 1 ($W=0$, Ep 0..99):** Mean loss $= 133318.0\text{ LSB}^2$ (3.33 bits ENOB).
- **Active Training Phase 2 (Ep 100..1000):** Whole-run active evaluation stabilized at **21149.4 LSB²** (4.88 bits ENOB), an improvement of **-84.1%** (+1.55 bits ENOB).
- **Peak Performance:** Epoch 518 reached **605.5 LSB² (7.17 bits ENOB)**!
- **Weight Drift Immunity:** Final M8 diagonal weights converged to `[0, 0, 0, 0, 0, 0]` LSB (0% clamping, 100% linear triode margin).

---

## 2. 100-Epoch Segment Progression & Fig 7 Disturbance Response

| Segment | Status / Störningsregim | Medelfel (LSB²) | Medel ENOB (b) | Topp-ENOB (b) | Slutvikter $W_8$ (LSB) |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Epoch 0 .. 99** | Phase 1: Baseline W=0 (Training OFF, Nom. M33) | 133318.0 | **3.33** | 5.50 (@ 6138.0 L²) | `[0, 0, 0, 0, 0, 0]` |
| **Epoch 100 .. 199** | Phase 2: Nominal Convergence (Training ON, Nom. M33) | 29633.1 | **4.60** | 5.92 (@ 3453.5 L²) | `[1, 8, 4, 12, 29, -11]` |
| **Epoch 200 .. 299** | Phase 3: Active Tracking 1 (±5 LSB, Training ON) | 24730.9 | **4.73** | 6.72 (@ 1132.5 L²) | `[4, 11, 6, 16, 21, -8]` |
| **Epoch 300 .. 399** | Phase 3: Active Tracking 2 (±5 LSB, Training ON) | 15277.1 | **5.05** | 6.12 (@ 2610.5 L²) | `[-7, 7, 4, 10, 13, -9]` |
| **Epoch 400 .. 499** | Phase 3: Active Tracking 3 (±5 LSB, Training ON) | 18448.5 | **4.97** | 6.53 (@ 1478.5 L²) | `[-6, 6, 3, 10, 10, -12]` |
| **Epoch 500 .. 599** | Phase 3: Active Tracking 4 (±5 LSB, Training ON) | 17657.5 | **5.02** | 7.17 (@ 605.5 L²) | `[3, 7, 2, 12, 23, -10]` |
| **Epoch 600 .. 699** | Phase 4: Ablation Control 1 (±5 LSB, W=0, Training OFF) | 143764.5 | **3.28** | 6.70 (@ 1165.5 L²) | `[0, 0, 0, 0, 0, 0]` |
| **Epoch 700 .. 799** | Phase 4: Ablation Control 2 (±5 LSB, W=0, Training OFF) | 152062.2 | **3.22** | 4.86 (@ 14933.0 L²) | `[0, 0, 0, 0, 0, 0]` |
| **Epoch 800 .. 899** | Phase 4: Ablation Control 3 (±5 LSB, W=0, Training OFF) | 162574.4 | **3.17** | 4.88 (@ 14565.5 L²) | `[0, 0, 0, 0, 0, 0]` |
| **Epoch 900 .. 999** | Phase 4: Ablation Control 4 (±5 LSB, W=0, Training OFF) | 130993.7 | **3.33** | 5.21 (@ 9224.5 L²) | `[0, 0, 0, 0, 0, 0]` |

---

## 3. Patent SE 2630397-4 Fig 7 Emulator: 100-Epokers Avsnitt & Randomiserade Matriser
*Fusk-Skydd:* Den digitala mål-supervisorn ($Z_\text{target}$) i T120 SoC beräknas strikt mot den nominella frysta matrisen $W^{(33)}_\text{nominal}$. De dolda stokastiska avvikelserna laddas enbart upp på de fysiska 2T1C-kondensatorerna på kiselmatrisen för att emulera hårdvarudrift.

### Epok 0 .. 99: Platt Baslinje (W=0, Training OFF)
- **Status:** Ingen störning (100% nominell fryst $W^{(33)}_\text{nominal}$), öppen loop baslinjemätning ($W=0$, $\text{LR}=0$).
- **Prestanda:** Medelfel = 133318.0 LSB² (3.33 bitar ENOB), Bästa = 6138.0 LSB² (5.50 b).
- **M8 Vikter:** `[0, 0, 0, 0, 0, 0]` LSB.

---

### Epok 100 .. 199: Nominell Etablering (Training ON, Noll Störning)
- **Status:** Träning påslagen direkt från W=0 mot nominell ostörd matris ($\text{LR}=0.08\text{x}$, $\lambda=2048$).
- **Syfte:** Etablera stabil analog jämvikt och grundkompensation innan hårdvarustörningar appliceras.
- **Prestanda:** Medelfel = 29633.1 LSB² (4.60 bitar ENOB), Bästa = 3453.5 LSB² (5.92 b).
- **M8 Vikter vid slutet av intervallet:** `[1, 8, 4, 12, 29, -11]` LSB.

---

### Epok 200 .. 299: Phase 3: Active Tracking 1 (±5 LSB, Training ON)
- **Prestanda:** Medelfel = 24730.9 LSB² (4.73 bitar ENOB), Bästa = 1132.5 LSB² (6.72 b)
- **M8 Vikter vid slutet av intervallet:** `[4, 11, 6, 16, 21, -8]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-5, +5]\text{ LSB}$):**
```text
Rad 0: [  -4  +0  -2  -5  -5  -5 ] LSB
Rad 1: [  +2  -5  -5  -5  -5  +4 ] LSB
Rad 2: [  +1  -2  +4  +2  +5  -3 ] LSB
Rad 3: [  -5  +1  +5  -5  +4  -4 ] LSB
Rad 4: [  -1  -4  -4  -2  +0  +0 ] LSB
Rad 5: [  +1  -5  -5  +4  +1  +2 ] LSB
```

---

### Epok 300 .. 399: Phase 3: Active Tracking 2 (±5 LSB, Training ON)
- **Prestanda:** Medelfel = 15277.1 LSB² (5.05 bitar ENOB), Bästa = 2610.5 LSB² (6.12 b)
- **M8 Vikter vid slutet av intervallet:** `[-7, 7, 4, 10, 13, -9]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-5, +5]\text{ LSB}$):**
```text
Rad 0: [  -2  -5  +5  +5  +4  +1 ] LSB
Rad 1: [  +1  -5  +0  +1  +5  -2 ] LSB
Rad 2: [  +5  -1  +2  -3  -1  +1 ] LSB
Rad 3: [  +2  -2  -4  +4  +4  +0 ] LSB
Rad 4: [  +4  -4  +1  -5  +5  -5 ] LSB
Rad 5: [  +2  +3  +0  -4  -1  -3 ] LSB
```

---

### Epok 400 .. 499: Phase 3: Active Tracking 3 (±5 LSB, Training ON)
- **Prestanda:** Medelfel = 18448.5 LSB² (4.97 bitar ENOB), Bästa = 1478.5 LSB² (6.53 b)
- **M8 Vikter vid slutet av intervallet:** `[-6, 6, 3, 10, 10, -12]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-5, +5]\text{ LSB}$):**
```text
Rad 0: [  +4  -4  +3  +1  +4  +5 ] LSB
Rad 1: [  +4  +4  +4  -1  +1  +0 ] LSB
Rad 2: [  -2  +1  +2  +5  +2  +4 ] LSB
Rad 3: [  +0  +3  -2  +1  +3  -5 ] LSB
Rad 4: [  -5  -2  -1  -5  -1  -5 ] LSB
Rad 5: [  +0  +2  -4  -5  +3  -2 ] LSB
```

---

### Epok 500 .. 599: Phase 3: Active Tracking 4 (±5 LSB, Training ON)
- **Prestanda:** Medelfel = 17657.5 LSB² (5.02 bitar ENOB), Bästa = 605.5 LSB² (7.17 b)
- **M8 Vikter vid slutet av intervallet:** `[3, 7, 2, 12, 23, -10]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-5, +5]\text{ LSB}$):**
```text
Rad 0: [  +0  +4  -5  +5  +3  -4 ] LSB
Rad 1: [  +2  +5  -3  +2  +2  -4 ] LSB
Rad 2: [  -1  -3  +0  -5  -5  -4 ] LSB
Rad 3: [  -3  -5  +3  +3  +2  +3 ] LSB
Rad 4: [  -5  +1  +1  -4  -5  +2 ] LSB
Rad 5: [  +2  +0  +4  +0  -1  -5 ] LSB
```

---

### Epok 600 .. 699: Phase 4: Ablation Control 1 (±5 LSB, W=0, Training OFF)
- **Prestanda:** Medelfel = 143764.5 LSB² (3.28 bitar ENOB), Bästa = 1165.5 LSB² (6.70 b)
- **M8 Vikter vid slutet av intervallet:** `[0, 0, 0, 0, 0, 0]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-5, +5]\text{ LSB}$):**
```text
Rad 0: [  +3  -1  -3  -2  +4  +1 ] LSB
Rad 1: [  +0  +4  +0  +1  +0  -3 ] LSB
Rad 2: [  +0  +3  -3  +0  +0  -2 ] LSB
Rad 3: [  +0  +4  -1  -1  -4  +1 ] LSB
Rad 4: [  +2  +3  +2  +3  -5  -2 ] LSB
Rad 5: [  +4  +2  -5  -5  -2  -4 ] LSB
```

---

### Epok 700 .. 799: Phase 4: Ablation Control 2 (±5 LSB, W=0, Training OFF)
- **Prestanda:** Medelfel = 152062.2 LSB² (3.22 bitar ENOB), Bästa = 14933.0 LSB² (4.86 b)
- **M8 Vikter vid slutet av intervallet:** `[0, 0, 0, 0, 0, 0]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-5, +5]\text{ LSB}$):**
```text
Rad 0: [  +1  +2  -2  -1  +5  -5 ] LSB
Rad 1: [  -1  -3  +5  +0  -1  -2 ] LSB
Rad 2: [  +2  +1  +1  +0  -2  +4 ] LSB
Rad 3: [  -2  +0  +2  +5  +0  +4 ] LSB
Rad 4: [  +3  -2  +5  +4  +4  -4 ] LSB
Rad 5: [  -5  -3  +0  -2  -1  -1 ] LSB
```

---

### Epok 800 .. 899: Phase 4: Ablation Control 3 (±5 LSB, W=0, Training OFF)
- **Prestanda:** Medelfel = 162574.4 LSB² (3.17 bitar ENOB), Bästa = 14565.5 LSB² (4.88 b)
- **M8 Vikter vid slutet av intervallet:** `[0, 0, 0, 0, 0, 0]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-5, +5]\text{ LSB}$):**
```text
Rad 0: [  -2  +5  +0  -3  -2  -5 ] LSB
Rad 1: [  +3  -4  -5  -4  -5  +3 ] LSB
Rad 2: [  +1  +0  +4  +4  -2  +3 ] LSB
Rad 3: [  -1  -5  +4  -4  +3  +4 ] LSB
Rad 4: [  -2  -3  +5  +3  -5  +5 ] LSB
Rad 5: [  +3  -4  -4  +3  +0  +5 ] LSB
```

---

### Epok 900 .. 999: Phase 4: Ablation Control 4 (±5 LSB, W=0, Training OFF)
- **Prestanda:** Medelfel = 130993.7 LSB² (3.33 bitar ENOB), Bästa = 9224.5 LSB² (5.21 b)
- **M8 Vikter vid slutet av intervallet:** `[0, 0, 0, 0, 0, 0]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-5, +5]\text{ LSB}$):**
```text
Rad 0: [  -3  +3  +2  +1  -5  -1 ] LSB
Rad 1: [  -5  +5  +4  +0  -3  +3 ] LSB
Rad 2: [  +0  +0  -2  +2  -4  -1 ] LSB
Rad 3: [  +5  -3  -2  -5  -3  +4 ] LSB
Rad 4: [  +4  +2  +4  -5  +4  -5 ] LSB
Rad 5: [  +0  -3  -4  -5  +2  -1 ] LSB
```

---

### Epok 1000 .. 1000: Aktiv Störning
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-5, +5]\text{ LSB}$):**
```text
Rad 0: [  -1  +3  -2  +5  +4  -5 ] LSB
Rad 1: [  +4  +2  +4  -1  +4  +3 ] LSB
Rad 2: [  +1  +4  +5  -3  -4  -5 ] LSB
Rad 3: [  -2  -1  -1  +4  +2  +4 ] LSB
Rad 4: [  +3  -2  +0  +2  -5  +3 ] LSB
Rad 5: [  +4  -4  +5  -3  +4  -3 ] LSB
```

---

## 4. Hardware Verification & Run Parameters
- **SoC Architecture:** Trion T120 Master + T20 Companion (`TAG=T20A`, S-bus ACK `0x06`).
- **Passive Summing Attenuator:** 1k / 5.1k Ohm ($16.4\%$ compensation authority).
- **Repair Status:** Channel 3 resoldered and physically verified.
- **Log Source:** `/home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/logs/mode_a_extended_training/mode_a_1000ep_5ms_pure_toeplitz_reg2048_lr0p02_swing40_var5_k1_1k_3p3k_ablation.json`
- **Figure:** `/home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/docs/figures/fig_mode_a_1000ep_5ms_pure_toeplitz_reg2048_lr0p02_swing40_var5_k1_1k_3p3k_ablation.png`
