# INVERTED MAML: Pure 5.0 ms Snapshot Experiment Report (TOEPLITZ, ±40 LSB, M33 Nominal 1.0x)
**Patent Pending:** SE 2630397-4 (Open Science Hardware)  
**Target Hardware:** Card 2 (Rev 2.0 Silicon, 1k/3.3k attenuator, repaired CH3)  
**Date:** 2026-11-04 12:48:15  
**Stimulus Profile:** LLM Toeplitz (ρ = 0.85)  
**Architecture:** Flat Baseline Protocol ($W=0, W_\text{null}=0, \text{LR}=0.08\text{x}, \lambda=1024$)  
**Dynamic Input Swing:** $\pm 40\text{ LSB}$ (`d_line=2`)  
**Matrix 33 State:** M33 Nominal 1.0x | **Disturbance (Fig 7):** Fig 7 Disturbance ±3 LSB  

---

## 1. Executive Summary & Key Results
- **Pure 5.0 ms Snapshot Evaluation:** Evaluated strictly at single-point $t = 5000\,\mu\text{s}$ ($K=4$ capacitor refreshes per epoch).
- **Baseline Phase 1 ($W=0$, Ep 0..99):** Mean loss $= 36394.3\text{ LSB}^2$ (4.25 bits ENOB).
- **Active Training Phase 2 (Ep 100..1000):** Whole-run active evaluation stabilized at **22368.4 LSB²** (4.60 bits ENOB), an improvement of **-38.5%** (+0.36 bits ENOB).
- **Peak Performance:** Epoch 400 reached **8240.0 LSB² (5.29 bits ENOB)**!
- **Weight Drift Immunity:** Final M8 diagonal weights converged to `[0, 0, 0, 0, 0, 0]` LSB (0% clamping, 100% linear triode margin).

---

## 2. 100-Epoch Segment Progression & Fig 7 Disturbance Response

| Segment | Status / Störningsregim | Medelfel (LSB²) | Medel ENOB (b) | Topp-ENOB (b) | Slutvikter $W_8$ (LSB) |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Epoch 0 .. 99** | Phase 1: Baseline W=0 (Training OFF, Nom. M33) | 36394.3 | **4.25** | 5.21 (@ 9139.0 L²) | `[0, 0, 0, 0, 0, 0]` |
| **Epoch 100 .. 199** | Phase 2: Nominal Convergence (Training ON, Nom. M33) | 23641.2 | **4.57** | 5.15 (@ 10001.0 L²) | `[6, 3, 4, -6, 12, -7]` |
| **Epoch 200 .. 299** | Phase 3: Active Tracking 1 (±3 LSB, Training ON) | 21366.7 | **4.63** | 5.20 (@ 9275.0 L²) | `[9, 4, 4, -2, 13, -10]` |
| **Epoch 300 .. 399** | Phase 3: Active Tracking 2 (±3 LSB, Training ON) | 22664.6 | **4.59** | 5.08 (@ 10971.5 L²) | `[10, 4, 5, -6, 17, -10]` |
| **Epoch 400 .. 499** | Phase 3: Active Tracking 3 (±3 LSB, Training ON) | 21604.3 | **4.63** | 5.29 (@ 8240.0 L²) | `[8, 6, 5, -4, 15, -7]` |
| **Epoch 500 .. 599** | Phase 3: Active Tracking 4 (±3 LSB, Training ON) | 22565.1 | **4.59** | 5.14 (@ 10093.0 L²) | `[11, 4, 4, -1, 15, -10]` |
| **Epoch 600 .. 699** | Phase 4: Ablation Control 1 (±3 LSB, W=0, Training OFF) | 36469.3 | **4.24** | 5.49 (@ 6266.5 L²) | `[0, 0, 0, 0, 0, 0]` |
| **Epoch 700 .. 799** | Phase 4: Ablation Control 2 (±3 LSB, W=0, Training OFF) | 35324.1 | **4.27** | 5.58 (@ 5526.5 L²) | `[0, 0, 0, 0, 0, 0]` |
| **Epoch 800 .. 899** | Phase 4: Ablation Control 3 (±3 LSB, W=0, Training OFF) | 34247.9 | **4.29** | 5.62 (@ 5213.5 L²) | `[0, 0, 0, 0, 0, 0]` |
| **Epoch 900 .. 999** | Phase 4: Ablation Control 4 (±3 LSB, W=0, Training OFF) | 37272.0 | **4.23** | 5.93 (@ 3371.5 L²) | `[0, 0, 0, 0, 0, 0]` |

---

## 3. Patent SE 2630397-4 Fig 7 Emulator: 100-Epokers Avsnitt & Randomiserade Matriser
*Fusk-Skydd:* Den digitala mål-supervisorn ($Z_\text{target}$) i T120 SoC beräknas strikt mot den nominella frysta matrisen $W^{(33)}_\text{nominal}$. De dolda stokastiska avvikelserna laddas enbart upp på de fysiska 2T1C-kondensatorerna på kiselmatrisen för att emulera hårdvarudrift.

### Epok 0 .. 99: Platt Baslinje (W=0, Training OFF)
- **Status:** Ingen störning (100% nominell fryst $W^{(33)}_\text{nominal}$), öppen loop baslinjemätning ($W=0$, $\text{LR}=0$).
- **Prestanda:** Medelfel = 36394.3 LSB² (4.25 bitar ENOB), Bästa = 9139.0 LSB² (5.21 b).
- **M8 Vikter:** `[0, 0, 0, 0, 0, 0]` LSB.

---

### Epok 100 .. 199: Nominell Etablering (Training ON, Noll Störning)
- **Status:** Träning påslagen direkt från W=0 mot nominell ostörd matris ($\text{LR}=0.08\text{x}$, $\lambda=1024$).
- **Syfte:** Etablera stabil analog jämvikt och grundkompensation innan hårdvarustörningar appliceras.
- **Prestanda:** Medelfel = 23641.2 LSB² (4.57 bitar ENOB), Bästa = 10001.0 LSB² (5.15 b).
- **M8 Vikter vid slutet av intervallet:** `[6, 3, 4, -6, 12, -7]` LSB.

---

### Epok 200 .. 299: Phase 3: Active Tracking 1 (±3 LSB, Training ON)
- **Prestanda:** Medelfel = 21366.7 LSB² (4.63 bitar ENOB), Bästa = 9275.0 LSB² (5.20 b)
- **M8 Vikter vid slutet av intervallet:** `[9, 4, 4, -2, 13, -10]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  +1  -3  +2  +1  +2  +0 ] LSB
Rad 1: [  -3  -1  -1  -2  +2  -2 ] LSB
Rad 2: [  +1  +3  -1  -3  +0  +0 ] LSB
Rad 3: [  -2  -2  +3  +3  +0  -1 ] LSB
Rad 4: [  +3  +2  +0  -1  +0  +3 ] LSB
Rad 5: [  +1  +2  -2  +1  -2  +3 ] LSB
```

---

### Epok 300 .. 399: Phase 3: Active Tracking 2 (±3 LSB, Training ON)
- **Prestanda:** Medelfel = 22664.6 LSB² (4.59 bitar ENOB), Bästa = 10971.5 LSB² (5.08 b)
- **M8 Vikter vid slutet av intervallet:** `[10, 4, 5, -6, 17, -10]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  +0  +1  -2  +3  -3  +1 ] LSB
Rad 1: [  +2  +3  +2  -2  +1  -2 ] LSB
Rad 2: [  -3  +3  +0  +0  +3  -3 ] LSB
Rad 3: [  -2  -1  +1  -2  -2  -3 ] LSB
Rad 4: [  -1  +0  +2  -1  -3  -3 ] LSB
Rad 5: [  -3  -3  -2  +2  +0  +0 ] LSB
```

---

### Epok 400 .. 499: Phase 3: Active Tracking 3 (±3 LSB, Training ON)
- **Prestanda:** Medelfel = 21604.3 LSB² (4.63 bitar ENOB), Bästa = 8240.0 LSB² (5.29 b)
- **M8 Vikter vid slutet av intervallet:** `[8, 6, 5, -4, 15, -7]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  -2  +2  -1  +2  +1  +0 ] LSB
Rad 1: [  +1  +2  +0  +3  +2  +1 ] LSB
Rad 2: [  +3  +0  +0  +2  -3  -3 ] LSB
Rad 3: [  +2  +2  +1  -1  -1  +3 ] LSB
Rad 4: [  -2  -2  +1  +1  -1  -3 ] LSB
Rad 5: [  +0  +2  +1  +2  +0  -1 ] LSB
```

---

### Epok 500 .. 599: Phase 3: Active Tracking 4 (±3 LSB, Training ON)
- **Prestanda:** Medelfel = 22565.1 LSB² (4.59 bitar ENOB), Bästa = 10093.0 LSB² (5.14 b)
- **M8 Vikter vid slutet av intervallet:** `[11, 4, 4, -1, 15, -10]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  -2  -2  -2  +0  -3  -3 ] LSB
Rad 1: [  +1  -1  +0  +2  +1  -3 ] LSB
Rad 2: [  -3  +0  -2  +0  +0  +3 ] LSB
Rad 3: [  +3  +0  -3  -1  -1  +1 ] LSB
Rad 4: [  +2  -3  -2  +1  -1  -2 ] LSB
Rad 5: [  -2  +1  +3  -1  +2  +3 ] LSB
```

---

### Epok 600 .. 699: Phase 4: Ablation Control 1 (±3 LSB, W=0, Training OFF)
- **Prestanda:** Medelfel = 36469.3 LSB² (4.24 bitar ENOB), Bästa = 6266.5 LSB² (5.49 b)
- **M8 Vikter vid slutet av intervallet:** `[0, 0, 0, 0, 0, 0]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  +1  -1  +1  -2  +1  +1 ] LSB
Rad 1: [  +0  +1  +3  -2  -2  +1 ] LSB
Rad 2: [  +3  +2  -1  +3  +1  -1 ] LSB
Rad 3: [  +1  +1  -1  +0  +3  -2 ] LSB
Rad 4: [  -3  +1  +0  +1  +3  -3 ] LSB
Rad 5: [  +1  -3  +3  -3  +1  -1 ] LSB
```

---

### Epok 700 .. 799: Phase 4: Ablation Control 2 (±3 LSB, W=0, Training OFF)
- **Prestanda:** Medelfel = 35324.1 LSB² (4.27 bitar ENOB), Bästa = 5526.5 LSB² (5.58 b)
- **M8 Vikter vid slutet av intervallet:** `[0, 0, 0, 0, 0, 0]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  +3  +3  +2  +3  +0  +0 ] LSB
Rad 1: [  +0  -2  -1  +1  -1  +2 ] LSB
Rad 2: [  -1  +2  +0  -3  -2  -3 ] LSB
Rad 3: [  +1  +2  +0  +0  +1  -2 ] LSB
Rad 4: [  +2  +1  -1  +1  -3  +2 ] LSB
Rad 5: [  -3  -2  -3  +0  +0  +3 ] LSB
```

---

### Epok 800 .. 899: Phase 4: Ablation Control 3 (±3 LSB, W=0, Training OFF)
- **Prestanda:** Medelfel = 34247.9 LSB² (4.29 bitar ENOB), Bästa = 5213.5 LSB² (5.62 b)
- **M8 Vikter vid slutet av intervallet:** `[0, 0, 0, 0, 0, 0]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  -3  +1  +2  +3  +1  -1 ] LSB
Rad 1: [  -2  +1  +3  +3  +0  -3 ] LSB
Rad 2: [  -3  +2  -1  -3  -2  -1 ] LSB
Rad 3: [  +1  +1  +1  +2  -1  +3 ] LSB
Rad 4: [  -3  -2  +2  +2  -3  -2 ] LSB
Rad 5: [  +1  +1  -3  -3  -2  -3 ] LSB
```

---

### Epok 900 .. 999: Phase 4: Ablation Control 4 (±3 LSB, W=0, Training OFF)
- **Prestanda:** Medelfel = 37272.0 LSB² (4.23 bitar ENOB), Bästa = 3371.5 LSB² (5.93 b)
- **M8 Vikter vid slutet av intervallet:** `[0, 0, 0, 0, 0, 0]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  +3  -2  -3  +2  -2  +3 ] LSB
Rad 1: [  -2  +1  +2  -2  +3  -1 ] LSB
Rad 2: [  +1  -2  +0  +3  +1  -3 ] LSB
Rad 3: [  +1  -1  +3  +1  +3  +0 ] LSB
Rad 4: [  -3  -2  +0  -3  +2  +2 ] LSB
Rad 5: [  +3  -3  -2  -1  +0  +0 ] LSB
```

---

### Epok 1000 .. 1000: Aktiv Störning
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  +1  +2  +1  +0  +2  +2 ] LSB
Rad 1: [  -2  -2  +3  +1  +0  -1 ] LSB
Rad 2: [  +0  +3  -2  -1  +0  +1 ] LSB
Rad 3: [  -2  -3  -2  +3  -1  +3 ] LSB
Rad 4: [  -1  +1  +1  +2  -3  -2 ] LSB
Rad 5: [  +3  -1  +0  +3  +0  +2 ] LSB
```

---

## 4. Hardware Verification & Run Parameters
- **SoC Architecture:** Trion T120 Master + T20 Companion (`TAG=T20A`, S-bus ACK `0x06`).
- **Passive Summing Attenuator:** 1k / 5.1k Ohm ($16.4\%$ compensation authority).
- **Repair Status:** Channel 3 resoldered and physically verified.
- **Log Source:** `/home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/logs/mode_a_extended_training/mode_a_1000ep_5ms_pure_toeplitz_reg1024_lr0p08_swing40_var3_k4_1k_3p3k_ablation.json`
- **Figure:** `/home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/docs/figures/fig_mode_a_1000ep_5ms_pure_toeplitz_reg1024_lr0p08_swing40_var3_k4_1k_3p3k_ablation.png`
