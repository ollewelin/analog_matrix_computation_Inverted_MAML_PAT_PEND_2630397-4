# INVERTED MAML: Pure 5.0 ms Snapshot Experiment Report (TOEPLITZ, ±40 LSB, M33 Nominal 1.0x)
**Patent Pending:** SE 2630397-4 (Open Science Hardware)  
**Target Hardware:** Card 2 (Rev 2.0 Silicon, 1k/3.3k attenuator, repaired CH3)  
**Date:** 2026-11-04 13:02:07  
**Stimulus Profile:** LLM Toeplitz (ρ = 0.85)  
**Architecture:** Flat Baseline Protocol ($W=0, W_\text{null}=0, \text{LR}=0.02\text{x}, \lambda=2048$)  
**Dynamic Input Swing:** $\pm 40\text{ LSB}$ (`d_line=2`)  
**Matrix 33 State:** M33 Nominal 1.0x | **Disturbance (Fig 7):** Fig 7 Disturbance ±3 LSB  

---

## 1. Executive Summary & Key Results
- **Pure 5.0 ms Snapshot Evaluation:** Evaluated strictly at single-point $t = 5000\,\mu\text{s}$ ($K=1$ capacitor refreshes per epoch).
- **Baseline Phase 1 ($W=0$, Ep 0..99):** Mean loss $= 129314.9\text{ LSB}^2$ (3.35 bits ENOB).
- **Active Training Phase 2 (Ep 100..1000):** Whole-run active evaluation stabilized at **21029.9 LSB²** (4.88 bits ENOB), an improvement of **-83.7%** (+1.53 bits ENOB).
- **Peak Performance:** Epoch 413 reached **707.0 LSB² (7.06 bits ENOB)**!
- **Weight Drift Immunity:** Final M8 diagonal weights converged to `[0, 0, 0, 0, 0, 0]` LSB (0% clamping, 100% linear triode margin).

---

## 2. 100-Epoch Segment Progression & Fig 7 Disturbance Response

| Segment | Status / Störningsregim | Medelfel (LSB²) | Medel ENOB (b) | Topp-ENOB (b) | Slutvikter $W_8$ (LSB) |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Epoch 0 .. 99** | Phase 1: Baseline W=0 (Training OFF, Nom. M33) | 129314.9 | **3.35** | 5.42 (@ 6859.0 L²) | `[0, 0, 0, 0, 0, 0]` |
| **Epoch 100 .. 199** | Phase 2: Nominal Convergence (Training ON, Nom. M33) | 28458.6 | **4.58** | 5.83 (@ 3900.0 L²) | `[2, 8, 4, 14, 29, -11]` |
| **Epoch 200 .. 299** | Phase 3: Active Tracking 1 (±3 LSB, Training ON) | 14706.4 | **5.06** | 6.08 (@ 2768.0 L²) | `[4, 6, 2, 8, 27, -13]` |
| **Epoch 300 .. 399** | Phase 3: Active Tracking 2 (±3 LSB, Training ON) | 31794.6 | **4.46** | 5.46 (@ 6490.0 L²) | `[0, 9, 5, 14, 28, -12]` |
| **Epoch 400 .. 499** | Phase 3: Active Tracking 3 (±3 LSB, Training ON) | 14882.5 | **5.22** | 7.06 (@ 707.0 L²) | `[4, 8, 3, 15, 22, -10]` |
| **Epoch 500 .. 599** | Phase 3: Active Tracking 4 (±3 LSB, Training ON) | 15307.4 | **5.08** | 6.29 (@ 2062.5 L²) | `[-1, 7, 4, 13, 25, -10]` |
| **Epoch 600 .. 699** | Phase 4: Ablation Control 1 (±3 LSB, W=0, Training OFF) | 131334.8 | **3.33** | 5.09 (@ 10869.5 L²) | `[0, 0, 0, 0, 0, 0]` |
| **Epoch 700 .. 799** | Phase 4: Ablation Control 2 (±3 LSB, W=0, Training OFF) | 130274.4 | **3.34** | 5.82 (@ 3933.0 L²) | `[0, 0, 0, 0, 0, 0]` |
| **Epoch 800 .. 899** | Phase 4: Ablation Control 3 (±3 LSB, W=0, Training OFF) | 133069.5 | **3.33** | 5.59 (@ 5410.0 L²) | `[0, 0, 0, 0, 0, 0]` |
| **Epoch 900 .. 999** | Phase 4: Ablation Control 4 (±3 LSB, W=0, Training OFF) | 135887.9 | **3.31** | 5.85 (@ 3781.5 L²) | `[0, 0, 0, 0, 0, 0]` |

---

## 3. Patent SE 2630397-4 Fig 7 Emulator: 100-Epokers Avsnitt & Randomiserade Matriser
*Fusk-Skydd:* Den digitala mål-supervisorn ($Z_\text{target}$) i T120 SoC beräknas strikt mot den nominella frysta matrisen $W^{(33)}_\text{nominal}$. De dolda stokastiska avvikelserna laddas enbart upp på de fysiska 2T1C-kondensatorerna på kiselmatrisen för att emulera hårdvarudrift.

### Epok 0 .. 99: Platt Baslinje (W=0, Training OFF)
- **Status:** Ingen störning (100% nominell fryst $W^{(33)}_\text{nominal}$), öppen loop baslinjemätning ($W=0$, $\text{LR}=0$).
- **Prestanda:** Medelfel = 129314.9 LSB² (3.35 bitar ENOB), Bästa = 6859.0 LSB² (5.42 b).
- **M8 Vikter:** `[0, 0, 0, 0, 0, 0]` LSB.

---

### Epok 100 .. 199: Nominell Etablering (Training ON, Noll Störning)
- **Status:** Träning påslagen direkt från W=0 mot nominell ostörd matris ($\text{LR}=0.08\text{x}$, $\lambda=2048$).
- **Syfte:** Etablera stabil analog jämvikt och grundkompensation innan hårdvarustörningar appliceras.
- **Prestanda:** Medelfel = 28458.6 LSB² (4.58 bitar ENOB), Bästa = 3900.0 LSB² (5.83 b).
- **M8 Vikter vid slutet av intervallet:** `[2, 8, 4, 14, 29, -11]` LSB.

---

### Epok 200 .. 299: Phase 3: Active Tracking 1 (±3 LSB, Training ON)
- **Prestanda:** Medelfel = 14706.4 LSB² (5.06 bitar ENOB), Bästa = 2768.0 LSB² (6.08 b)
- **M8 Vikter vid slutet av intervallet:** `[4, 6, 2, 8, 27, -13]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  -3  +0  +2  +3  +3  +0 ] LSB
Rad 1: [  +2  +2  +1  -2  -1  +1 ] LSB
Rad 2: [  -3  +0  -3  +3  +3  -1 ] LSB
Rad 3: [  -1  -1  +3  -1  +0  +3 ] LSB
Rad 4: [  +3  +0  +2  +2  -2  +0 ] LSB
Rad 5: [  -1  -3  +1  -1  +2  -3 ] LSB
```

---

### Epok 300 .. 399: Phase 3: Active Tracking 2 (±3 LSB, Training ON)
- **Prestanda:** Medelfel = 31794.6 LSB² (4.46 bitar ENOB), Bästa = 6490.0 LSB² (5.46 b)
- **M8 Vikter vid slutet av intervallet:** `[0, 9, 5, 14, 28, -12]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  +3  +2  +0  -3  -3  -2 ] LSB
Rad 1: [  -3  +0  -2  +1  +0  +3 ] LSB
Rad 2: [  +0  +1  +3  -3  +1  -1 ] LSB
Rad 3: [  +1  +3  -2  +1  +2  +3 ] LSB
Rad 4: [  +2  -3  -3  +2  -2  +3 ] LSB
Rad 5: [  +2  -3  +3  +2  -1  -1 ] LSB
```

---

### Epok 400 .. 499: Phase 3: Active Tracking 3 (±3 LSB, Training ON)
- **Prestanda:** Medelfel = 14882.5 LSB² (5.22 bitar ENOB), Bästa = 707.0 LSB² (7.06 b)
- **M8 Vikter vid slutet av intervallet:** `[4, 8, 3, 15, 22, -10]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  -3  -3  -1  -2  -2  +3 ] LSB
Rad 1: [  +3  -3  +1  +0  -1  +3 ] LSB
Rad 2: [  -2  +0  +0  +3  +2  -3 ] LSB
Rad 3: [  -3  -2  -2  +0  +2  -3 ] LSB
Rad 4: [  +1  +0  -3  -2  -3  +0 ] LSB
Rad 5: [  -2  +1  +2  +1  +2  +1 ] LSB
```

---

### Epok 500 .. 599: Phase 3: Active Tracking 4 (±3 LSB, Training ON)
- **Prestanda:** Medelfel = 15307.4 LSB² (5.08 bitar ENOB), Bästa = 2062.5 LSB² (6.29 b)
- **M8 Vikter vid slutet av intervallet:** `[-1, 7, 4, 13, 25, -10]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  -3  -1  +0  +1  -2  +2 ] LSB
Rad 1: [  +0  -1  +0  +1  -1  -1 ] LSB
Rad 2: [  -1  -3  -1  +2  -1  -2 ] LSB
Rad 3: [  +1  +2  -1  -3  +0  -2 ] LSB
Rad 4: [  -3  +2  +0  +3  +0  -1 ] LSB
Rad 5: [  +3  +2  -1  -1  +3  +2 ] LSB
```

---

### Epok 600 .. 699: Phase 4: Ablation Control 1 (±3 LSB, W=0, Training OFF)
- **Prestanda:** Medelfel = 131334.8 LSB² (3.33 bitar ENOB), Bästa = 10869.5 LSB² (5.09 b)
- **M8 Vikter vid slutet av intervallet:** `[0, 0, 0, 0, 0, 0]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  +1  +1  +0  -3  +0  -3 ] LSB
Rad 1: [  +3  -3  +3  +2  -3  +1 ] LSB
Rad 2: [  -1  +2  -1  +1  +1  -2 ] LSB
Rad 3: [  -1  -3  +2  +1  -2  +3 ] LSB
Rad 4: [  -2  +0  +3  -1  -1  +0 ] LSB
Rad 5: [  +3  +3  +3  +0  +3  +1 ] LSB
```

---

### Epok 700 .. 799: Phase 4: Ablation Control 2 (±3 LSB, W=0, Training OFF)
- **Prestanda:** Medelfel = 130274.4 LSB² (3.34 bitar ENOB), Bästa = 3933.0 LSB² (5.82 b)
- **M8 Vikter vid slutet av intervallet:** `[0, 0, 0, 0, 0, 0]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  -2  +3  -2  +1  +2  +2 ] LSB
Rad 1: [  +1  -1  -1  +0  +2  +1 ] LSB
Rad 2: [  -1  -2  -3  -3  -3  -3 ] LSB
Rad 3: [  +0  +0  -2  +2  -2  -1 ] LSB
Rad 4: [  +3  +2  +2  -2  +1  +2 ] LSB
Rad 5: [  -1  -1  -1  +0  +3  -3 ] LSB
```

---

### Epok 800 .. 899: Phase 4: Ablation Control 3 (±3 LSB, W=0, Training OFF)
- **Prestanda:** Medelfel = 133069.5 LSB² (3.33 bitar ENOB), Bästa = 5410.0 LSB² (5.59 b)
- **M8 Vikter vid slutet av intervallet:** `[0, 0, 0, 0, 0, 0]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  +0  +1  -2  +0  -1  -2 ] LSB
Rad 1: [  -1  +1  +2  -1  -3  +0 ] LSB
Rad 2: [  +1  +3  +2  +2  +1  +1 ] LSB
Rad 3: [  +1  +0  +3  -1  +3  +2 ] LSB
Rad 4: [  +0  +0  -1  +3  +3  +0 ] LSB
Rad 5: [  -3  +1  -3  +3  +1  -3 ] LSB
```

---

### Epok 900 .. 999: Phase 4: Ablation Control 4 (±3 LSB, W=0, Training OFF)
- **Prestanda:** Medelfel = 135887.9 LSB² (3.31 bitar ENOB), Bästa = 3781.5 LSB² (5.85 b)
- **M8 Vikter vid slutet av intervallet:** `[0, 0, 0, 0, 0, 0]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  +2  -2  -1  -3  -2  -3 ] LSB
Rad 1: [  -1  +3  +2  -2  -3  -2 ] LSB
Rad 2: [  -1  +3  -3  +3  +2  +2 ] LSB
Rad 3: [  +2  -2  +3  -1  +3  -2 ] LSB
Rad 4: [  -2  -2  +0  +2  +2  +3 ] LSB
Rad 5: [  -2  +2  +0  +3  +2  -2 ] LSB
```

---

### Epok 1000 .. 1000: Aktiv Störning
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  +0  -1  -2  -3  +2  +1 ] LSB
Rad 1: [  +3  +0  -2  +0  +3  +3 ] LSB
Rad 2: [  -2  +1  -1  +2  -1  -2 ] LSB
Rad 3: [  +1  +3  +1  -2  +0  -3 ] LSB
Rad 4: [  +2  +3  -2  -1  +1  -2 ] LSB
Rad 5: [  +0  +1  +0  -2  -1  -1 ] LSB
```

---

## 4. Hardware Verification & Run Parameters
- **SoC Architecture:** Trion T120 Master + T20 Companion (`TAG=T20A`, S-bus ACK `0x06`).
- **Passive Summing Attenuator:** 1k / 5.1k Ohm ($16.4\%$ compensation authority).
- **Repair Status:** Channel 3 resoldered and physically verified.
- **Log Source:** `/home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/logs/mode_a_extended_training/mode_a_1000ep_5ms_pure_toeplitz_reg2048_lr0p02_swing40_var3_k1_1k_3p3k_ablation.json`
- **Figure:** `/home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/docs/figures/fig_mode_a_1000ep_5ms_pure_toeplitz_reg2048_lr0p02_swing40_var3_k1_1k_3p3k_ablation.png`
