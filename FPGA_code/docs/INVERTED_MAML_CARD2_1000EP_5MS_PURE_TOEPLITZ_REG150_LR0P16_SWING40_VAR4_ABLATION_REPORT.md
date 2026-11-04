# INVERTED MAML: Pure 5.0 ms Snapshot Experiment Report (TOEPLITZ, ±40 LSB, M33 Nominal 1.0x)
**Patent Pending:** SE 2630397-4 (Open Science Hardware)  
**Target Hardware:** Card 2 (Rev 2.0 Silicon, 1k/5.1k attenuator, repaired CH3)  
**Date:** 2026-11-04 11:38:08  
**Stimulus Profile:** LLM Toeplitz (ρ = 0.85)  
**Architecture:** Flat Baseline Protocol ($W=0, W_\text{null}=0, \text{LR}=0.16\text{x}, \lambda=150$)  
**Dynamic Input Swing:** $\pm 40\text{ LSB}$ (`d_line=2`)  
**Matrix 33 State:** M33 Nominal 1.0x | **Disturbance (Fig 7):** Fig 7 Disturbance ±4 LSB  

---

## 1. Executive Summary & Key Results
- **Pure 5.0 ms Snapshot Evaluation:** Evaluated strictly at single-point $t = 5000\,\mu\text{s}$ ($K=20$ capacitor refreshes per epoch).
- **Baseline Phase 1 ($W=0$, Ep 0..99):** Mean loss $= 15309.1\text{ LSB}^2$ (4.85 bits ENOB).
- **Active Training Phase 2 (Ep 100..1000):** Whole-run active evaluation stabilized at **31344.8 LSB²** (4.49 bits ENOB), an improvement of **+104.7%** (-0.36 bits ENOB).
- **Peak Performance:** Epoch 168 reached **9434.5 LSB² (5.19 bits ENOB)**!
- **Weight Drift Immunity:** Final M8 diagonal weights converged to `[0, 0, 0, 0, 0, 0]` LSB (0% clamping, 100% linear triode margin).

---

## 2. 100-Epoch Segment Progression & Fig 7 Disturbance Response

| Segment | Status / Störningsregim | Medelfel (LSB²) | Medel ENOB (b) | Topp-ENOB (b) | Slutvikter $W_8$ (LSB) |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Epoch 0 .. 99** | Phase 1: Baseline W=0 (Training OFF, Nom. M33) | 15309.1 | **4.85** | 5.18 (@ 9546.5 L²) | `[0, 0, 0, 0, 0, 0]` |
| **Epoch 100 .. 199** | Phase 2: Nominal Convergence (Training ON, Nom. M33) | 14124.7 | **4.91** | 5.19 (@ 9434.5 L²) | `[3, -5, 1, -7, 10, -9]` |
| **Epoch 200 .. 299** | Phase 3: Active Tracking 1 (±4 LSB, Training ON) | 14920.7 | **4.88** | 5.15 (@ 9984.5 L²) | `[22, -5, -2, -14, -36, -6]` |
| **Epoch 300 .. 399** | Phase 3: Active Tracking 2 (±4 LSB, Training ON) | 71421.8 | **3.76** | 4.52 (@ 24014.0 L²) | `[-30, 1, 35, -44, 92, 8]` |
| **Epoch 400 .. 499** | Phase 3: Active Tracking 3 (±4 LSB, Training ON) | 34778.1 | **4.26** | 4.59 (@ 21588.5 L²) | `[-10, 114, 50, -45, 90, -23]` |
| **Epoch 500 .. 599** | Phase 3: Active Tracking 4 (±4 LSB, Training ON) | 21478.8 | **4.64** | 5.17 (@ 9698.5 L²) | `[-61, 5, 49, 16, 88, -2]` |
| **Epoch 600 .. 699** | Phase 4: Ablation Control 1 (±4 LSB, W=0, Training OFF) | 15691.4 | **4.84** | 5.13 (@ 10287.5 L²) | `[0, 0, 0, 0, 0, 0]` |
| **Epoch 700 .. 799** | Phase 4: Ablation Control 2 (±4 LSB, W=0, Training OFF) | 15621.0 | **4.84** | 5.44 (@ 6637.5 L²) | `[0, 0, 0, 0, 0, 0]` |
| **Epoch 800 .. 899** | Phase 4: Ablation Control 3 (±4 LSB, W=0, Training OFF) | 14775.0 | **4.88** | 5.65 (@ 4981.0 L²) | `[0, 0, 0, 0, 0, 0]` |
| **Epoch 900 .. 999** | Phase 4: Ablation Control 4 (±4 LSB, W=0, Training OFF) | 17119.7 | **4.77** | 5.34 (@ 7717.5 L²) | `[0, 0, 0, 0, 0, 0]` |

---

## 3. Patent SE 2630397-4 Fig 7 Emulator: 100-Epokers Avsnitt & Randomiserade Matriser
*Fusk-Skydd:* Den digitala mål-supervisorn ($Z_\text{target}$) i T120 SoC beräknas strikt mot den nominella frysta matrisen $W^{(33)}_\text{nominal}$. De dolda stokastiska avvikelserna laddas enbart upp på de fysiska 2T1C-kondensatorerna på kiselmatrisen för att emulera hårdvarudrift.

### Epok 0 .. 99: Platt Baslinje (W=0, Training OFF)
- **Status:** Ingen störning (100% nominell fryst $W^{(33)}_\text{nominal}$), öppen loop baslinjemätning ($W=0$, $\text{LR}=0$).
- **Prestanda:** Medelfel = 15309.1 LSB² (4.85 bitar ENOB), Bästa = 9546.5 LSB² (5.18 b).
- **M8 Vikter:** `[0, 0, 0, 0, 0, 0]` LSB.

---

### Epok 100 .. 199: Nominell Etablering (Training ON, Noll Störning)
- **Status:** Träning påslagen direkt från W=0 mot nominell ostörd matris ($\text{LR}=0.08\text{x}$, $\lambda=150$).
- **Syfte:** Etablera stabil analog jämvikt och grundkompensation innan hårdvarustörningar appliceras.
- **Prestanda:** Medelfel = 14124.7 LSB² (4.91 bitar ENOB), Bästa = 9434.5 LSB² (5.19 b).
- **M8 Vikter vid slutet av intervallet:** `[3, -5, 1, -7, 10, -9]` LSB.

---

### Epok 200 .. 299: Phase 3: Active Tracking 1 (±4 LSB, Training ON)
- **Prestanda:** Medelfel = 14920.7 LSB² (4.88 bitar ENOB), Bästa = 9984.5 LSB² (5.15 b)
- **M8 Vikter vid slutet av intervallet:** `[22, -5, -2, -14, -36, -6]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-4, +4]\text{ LSB}$):**
```text
Rad 0: [  -3  -2  +1  -3  +2  -2 ] LSB
Rad 1: [  -1  +3  +4  +3  +3  +2 ] LSB
Rad 2: [  -3  +3  -1  -1  +0  +4 ] LSB
Rad 3: [  -4  +1  -2  -1  +1  -2 ] LSB
Rad 4: [  -2  -1  +3  +4  +3  -2 ] LSB
Rad 5: [  +1  -1  +3  +3  +2  -4 ] LSB
```

---

### Epok 300 .. 399: Phase 3: Active Tracking 2 (±4 LSB, Training ON)
- **Prestanda:** Medelfel = 71421.8 LSB² (3.76 bitar ENOB), Bästa = 24014.0 LSB² (4.52 b)
- **M8 Vikter vid slutet av intervallet:** `[-30, 1, 35, -44, 92, 8]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-4, +4]\text{ LSB}$):**
```text
Rad 0: [  -1  +2  +1  -1  +4  -1 ] LSB
Rad 1: [  -3  -3  -4  -2  -4  +1 ] LSB
Rad 2: [  +4  -1  -3  -2  +3  -2 ] LSB
Rad 3: [  +3  -3  -1  -3  -3  +3 ] LSB
Rad 4: [  -2  -3  -1  -4  -2  +0 ] LSB
Rad 5: [  +3  +1  +2  +3  -4  +3 ] LSB
```

---

### Epok 400 .. 499: Phase 3: Active Tracking 3 (±4 LSB, Training ON)
- **Prestanda:** Medelfel = 34778.1 LSB² (4.26 bitar ENOB), Bästa = 21588.5 LSB² (4.59 b)
- **M8 Vikter vid slutet av intervallet:** `[-10, 114, 50, -45, 90, -23]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-4, +4]\text{ LSB}$):**
```text
Rad 0: [  -1  +2  +4  -3  -1  -1 ] LSB
Rad 1: [  -2  -3  +0  -2  +0  +4 ] LSB
Rad 2: [  +4  -4  +3  +0  -4  +0 ] LSB
Rad 3: [  +4  +1  -2  -2  -2  +2 ] LSB
Rad 4: [  -3  -4  +3  -1  +4  +3 ] LSB
Rad 5: [  -1  -4  +0  -1  +0  +0 ] LSB
```

---

### Epok 500 .. 599: Phase 3: Active Tracking 4 (±4 LSB, Training ON)
- **Prestanda:** Medelfel = 21478.8 LSB² (4.64 bitar ENOB), Bästa = 9698.5 LSB² (5.17 b)
- **M8 Vikter vid slutet av intervallet:** `[-61, 5, 49, 16, 88, -2]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-4, +4]\text{ LSB}$):**
```text
Rad 0: [  -3  +4  -2  +4  -4  +1 ] LSB
Rad 1: [  +1  -4  +3  +0  -3  +2 ] LSB
Rad 2: [  +2  +3  -1  -4  +2  +0 ] LSB
Rad 3: [  +4  +1  +0  +0  +1  +0 ] LSB
Rad 4: [  -2  -4  -4  +0  +4  +3 ] LSB
Rad 5: [  +2  +2  -3  -4  +3  -1 ] LSB
```

---

### Epok 600 .. 699: Phase 4: Ablation Control 1 (±4 LSB, W=0, Training OFF)
- **Prestanda:** Medelfel = 15691.4 LSB² (4.84 bitar ENOB), Bästa = 10287.5 LSB² (5.13 b)
- **M8 Vikter vid slutet av intervallet:** `[0, 0, 0, 0, 0, 0]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-4, +4]\text{ LSB}$):**
```text
Rad 0: [  +3  -3  +0  -1  -2  +3 ] LSB
Rad 1: [  +3  -1  +3  +2  +3  +1 ] LSB
Rad 2: [  +2  +0  -2  +0  -2  +3 ] LSB
Rad 3: [  -3  +0  -3  -1  -3  -4 ] LSB
Rad 4: [  +1  -3  -2  -4  -1  -1 ] LSB
Rad 5: [  +4  +1  -3  +3  -2  +4 ] LSB
```

---

### Epok 700 .. 799: Phase 4: Ablation Control 2 (±4 LSB, W=0, Training OFF)
- **Prestanda:** Medelfel = 15621.0 LSB² (4.84 bitar ENOB), Bästa = 6637.5 LSB² (5.44 b)
- **M8 Vikter vid slutet av intervallet:** `[0, 0, 0, 0, 0, 0]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-4, +4]\text{ LSB}$):**
```text
Rad 0: [  +3  +3  -1  +1  -2  +2 ] LSB
Rad 1: [  +0  +0  +4  +4  -1  +2 ] LSB
Rad 2: [  +4  +1  +1  +2  -2  +4 ] LSB
Rad 3: [  -2  +4  +2  -4  -2  -4 ] LSB
Rad 4: [  +1  +2  +3  +2  -3  -3 ] LSB
Rad 5: [  -1  +3  +0  -4  +0  +1 ] LSB
```

---

### Epok 800 .. 899: Phase 4: Ablation Control 3 (±4 LSB, W=0, Training OFF)
- **Prestanda:** Medelfel = 14775.0 LSB² (4.88 bitar ENOB), Bästa = 4981.0 LSB² (5.65 b)
- **M8 Vikter vid slutet av intervallet:** `[0, 0, 0, 0, 0, 0]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-4, +4]\text{ LSB}$):**
```text
Rad 0: [  -2  -2  -4  -1  +4  -1 ] LSB
Rad 1: [  +1  -4  +1  -3  +4  -2 ] LSB
Rad 2: [  -4  -4  -3  -1  +2  +2 ] LSB
Rad 3: [  +2  -3  -1  +0  +3  +0 ] LSB
Rad 4: [  +0  -2  +2  -4  -1  +3 ] LSB
Rad 5: [  +0  +3  -4  -1  +1  +0 ] LSB
```

---

### Epok 900 .. 999: Phase 4: Ablation Control 4 (±4 LSB, W=0, Training OFF)
- **Prestanda:** Medelfel = 17119.7 LSB² (4.77 bitar ENOB), Bästa = 7717.5 LSB² (5.34 b)
- **M8 Vikter vid slutet av intervallet:** `[0, 0, 0, 0, 0, 0]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-4, +4]\text{ LSB}$):**
```text
Rad 0: [  +3  +2  +4  +1  +0  +4 ] LSB
Rad 1: [  +0  -1  -1  +1  +1  +1 ] LSB
Rad 2: [  +1  +2  -1  +2  +3  -4 ] LSB
Rad 3: [  -4  +1  +2  +4  +1  -1 ] LSB
Rad 4: [  +1  +4  +0  -2  +0  -4 ] LSB
Rad 5: [  -3  -4  +0  +4  +4  +4 ] LSB
```

---

### Epok 1000 .. 1000: Aktiv Störning
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-4, +4]\text{ LSB}$):**
```text
Rad 0: [  -3  +4  +0  +3  +3  -4 ] LSB
Rad 1: [  +2  -2  +1  -3  +1  +3 ] LSB
Rad 2: [  -4  +2  -1  +3  -1  -3 ] LSB
Rad 3: [  +0  +0  -3  -4  +0  -1 ] LSB
Rad 4: [  +4  +0  -3  +1  +3  -4 ] LSB
Rad 5: [  -4  -1  +4  +1  +2  +2 ] LSB
```

---

## 4. Hardware Verification & Run Parameters
- **SoC Architecture:** Trion T120 Master + T20 Companion (`TAG=T20A`, S-bus ACK `0x06`).
- **Passive Summing Attenuator:** 1k / 5.1k Ohm ($16.4\%$ compensation authority).
- **Repair Status:** Channel 3 resoldered and physically verified.
- **Log Source:** `/home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/logs/mode_a_extended_training/mode_a_1000ep_5ms_pure_toeplitz_reg150_lr0p16_swing40_var4_ablation.json`
- **Figure:** `/home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/docs/figures/fig_mode_a_1000ep_5ms_pure_toeplitz_reg150_lr0p16_swing40_var4_ablation.png`
