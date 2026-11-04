# INVERTED MAML: Pure 5.0 ms Snapshot Experiment Report (TOEPLITZ, ±40 LSB, M33 Nominal 1.0x)
**Patent Pending:** SE 2630397-4 (Open Science Hardware)  
**Target Hardware:** Card 2 (Rev 2.0 Silicon, 1k/5.1k attenuator, repaired CH3)  
**Date:** 2026-11-04 11:01:33  
**Stimulus Profile:** LLM Toeplitz (ρ = 0.85)  
**Architecture:** Flat Baseline Protocol ($W=0, W_\text{null}=0, \text{LR}=0.08\text{x}, \lambda=150$)  
**Dynamic Input Swing:** $\pm 40\text{ LSB}$ (`d_line=2`)  
**Matrix 33 State:** M33 Nominal 1.0x | **Disturbance (Fig 7):** Fig 7 Disturbance ±3 LSB  

---

## 1. Executive Summary & Key Results
- **Pure 5.0 ms Snapshot Evaluation:** Evaluated strictly at single-point $t = 5000\,\mu\text{s}$ ($K=20$ capacitor refreshes per epoch).
- **Baseline Phase 1 ($W=0$, Ep 0..99):** Mean loss $= 14428.3\text{ LSB}^2$ (4.89 bits ENOB).
- **Active Training Phase 2 (Ep 100..500):** Mean loss stabilized at **14355.4 LSB²** (4.91 bits ENOB), an improvement of **-0.5%** (+0.01 bits ENOB).
- **Peak Performance:** Epoch 111 reached **8479.0 LSB² (5.27 bits ENOB)**!
- **Weight Drift Immunity:** Final M8 diagonal weights converged to `[-11, -1, -2, 8, 34, -8]` LSB (0% clamping, 100% linear triode margin).

---

## 2. 100-Epoch Segment Progression & Fig 7 Disturbance Response

| Segment | Status / Störningsregim | Medelfel (LSB²) | Medel ENOB (b) | Topp-ENOB (b) | Slutvikter $W_8$ (LSB) |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Epok 0 .. 99** | Platt Baslinje (W=0, Training OFF, Nom. M33) | 14428.3 | **4.89** | 5.42 (@ 6836.5 L²) | `[0, 0, 0, 0, 0, 0]` |
| **Epok 100 .. 199** | Nominell Etablering (Training ON, Nom. M33) | 13348.4 | **4.95** | 5.27 (@ 8479.0 L²) | `[7, 0, 1, 2, 10, -7]` |
| **Epok 200 .. 299** | Fig 7 Aktiv Störning 1 (±3 LSB) | 13627.4 | **4.94** | 5.24 (@ 8818.0 L²) | `[-4, -2, 1, 1, -35, -7]` |
| **Epok 300 .. 399** | Fig 7 Aktiv Störning 2 (±3 LSB) | 14938.1 | **4.87** | 5.15 (@ 9996.5 L²) | `[4, -1, 1, -1, -25, 12]` |
| **Epok 400 .. 500** | Fig 7 Aktiv Störning 3 (±3 LSB) | 15496.4 | **4.87** | 5.21 (@ 9157.5 L²) | `[-11, -1, -2, 8, 34, -8]` |

---

## 3. Pre- vs. Post-Training Temporal Transfer Function

| Delay (µs) | Pre-Training Loss (LSB²) | Post-Training Loss (LSB²) | Change (%) | Pre ENOB (b) | Post ENOB (b) |
| :---: | :---: | :---: | :---: | :---: | :---: |
| 4500 | 145931.7 | 227184.0 | +55.7% | 3.22 | 2.90 |
| 4600 | 88440.3 | 461690.3 | +422.0% | 3.58 | 2.94 |
| 4700 | 51072.2 | 67618.2 | +32.4% | 3.99 | 3.78 |
| 4800 | 491604.2 | 49722.8 | -89.9% | 3.33 | 4.00 |
| 4900 | 415658.7 | 25867.2 | -93.8% | 3.92 | 4.46 |
| 5000 | 17165.0 | 22262.2 | +29.7% | 4.76 | 4.60 |
| 5100 | 34694.7 | 22835.2 | -34.2% | 4.26 | 4.56 |
| 5200 | 55219.2 | 34632.0 | -37.3% | 3.92 | 4.26 |
| 5300 | 81043.8 | 55745.0 | -31.2% | 3.64 | 3.92 |
| 5400 | 141354.8 | 86596.5 | -38.7% | 3.24 | 3.60 |
| 5500 | 170597.2 | 85282.5 | -50.0% | 3.11 | 3.61 |

---

## 4. Patent SE 2630397-4 Fig 7 Emulator: 100-Epokers Avsnitt & Randomiserade Matriser
*Fusk-Skydd:* Den digitala mål-supervisorn ($Z_\text{target}$) i T120 SoC beräknas strikt mot den nominella frysta matrisen $W^{(33)}_\text{nominal}$. De dolda stokastiska avvikelserna laddas enbart upp på de fysiska 2T1C-kondensatorerna på kiselmatrisen för att emulera hårdvarudrift.

### Epok 0 .. 99: Platt Baslinje (W=0, Training OFF)
- **Status:** Ingen störning (100% nominell fryst $W^{(33)}_\text{nominal}$), öppen loop baslinjemätning ($W=0$, $\text{LR}=0$).
- **Prestanda:** Medelfel = 14428.3 LSB² (4.89 bitar ENOB), Bästa = 6836.5 LSB² (5.42 b).
- **M8 Vikter:** `[0, 0, 0, 0, 0, 0]` LSB.

---

### Epok 100 .. 199: Nominell Etablering (Training ON, Noll Störning)
- **Status:** Träning påslagen direkt från W=0 mot nominell ostörd matris ($\text{LR}=0.08\text{x}$, $\lambda=150$).
- **Syfte:** Etablera stabil analog jämvikt och grundkompensation innan hårdvarustörningar appliceras.
- **Prestanda:** Medelfel = 13348.4 LSB² (4.95 bitar ENOB), Bästa = 8479.0 LSB² (5.27 b).
- **M8 Vikter vid slutet av intervallet:** `[7, 0, 1, 2, 10, -7]` LSB.

---

### Epok 200 .. 299: Fig 7 Aktiv Störning 1 (±3 LSB)
- **Prestanda:** Medelfel = 13627.4 LSB² (4.94 bitar ENOB), Bästa = 8818.0 LSB² (5.24 b)
- **M8 Vikter vid slutet av intervallet:** `[-4, -2, 1, 1, -35, -7]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  +2  -1  -1  -3  -1  +1 ] LSB
Rad 1: [  +2  +3  -1  -2  +1  -3 ] LSB
Rad 2: [  +3  +1  +3  +2  +2  -1 ] LSB
Rad 3: [  +0  +2  +2  +3  +2  -1 ] LSB
Rad 4: [  +0  +2  +0  -3  +2  +2 ] LSB
Rad 5: [  -2  +1  -3  +2  +2  -3 ] LSB
```

---

### Epok 300 .. 399: Fig 7 Aktiv Störning 2 (±3 LSB)
- **Prestanda:** Medelfel = 14938.1 LSB² (4.87 bitar ENOB), Bästa = 9996.5 LSB² (5.15 b)
- **M8 Vikter vid slutet av intervallet:** `[4, -1, 1, -1, -25, 12]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  +2  -1  -3  +2  -3  +0 ] LSB
Rad 1: [  -2  +2  -3  -2  -1  +1 ] LSB
Rad 2: [  -2  -1  +2  -1  -2  +1 ] LSB
Rad 3: [  +0  -1  +1  +3  +2  -3 ] LSB
Rad 4: [  +3  -1  +2  +3  +1  -3 ] LSB
Rad 5: [  +2  +1  +0  +1  +3  -3 ] LSB
```

---

### Epok 400 .. 499: Fig 7 Aktiv Störning 3 (±3 LSB)
- **Prestanda:** Medelfel = 15496.4 LSB² (4.87 bitar ENOB), Bästa = 9157.5 LSB² (5.21 b)
- **M8 Vikter vid slutet av intervallet:** `[-11, -1, -2, 8, 34, -8]` LSB
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  +3  +3  -2  -2  -1  +2 ] LSB
Rad 1: [  -1  +0  -1  -1  +1  -1 ] LSB
Rad 2: [  +3  -2  +1  -1  +2  -1 ] LSB
Rad 3: [  +3  +1  +3  +2  -1  +1 ] LSB
Rad 4: [  -1  +0  -1  -1  -3  +2 ] LSB
Rad 5: [  +0  +3  +2  +1  -3  -2 ] LSB
```

---

### Epok 500 .. 500: Aktiv Störning
- **Injicerad Hidden Offset Matris på M33 ($\delta_{r,c} \in [-3, +3]\text{ LSB}$):**
```text
Rad 0: [  +2  -2  +1  +2  +3  -1 ] LSB
Rad 1: [  +0  +0  -1  +0  +2  -3 ] LSB
Rad 2: [  -3  -3  -1  +2  -2  -1 ] LSB
Rad 3: [  -1  -2  +3  +2  +0  -1 ] LSB
Rad 4: [  +2  -1  +2  -1  -3  +2 ] LSB
Rad 5: [  +1  -1  -1  +3  +2  +2 ] LSB
```

---

## 5. Hardware Verification & Run Parameters
- **SoC Architecture:** Trion T120 Master + T20 Companion (`TAG=T20A`, S-bus ACK `0x06`).
- **Passive Summing Attenuator:** 1k / 5.1k Ohm ($16.4\%$ compensation authority).
- **Repair Status:** Channel 3 resoldered and physically verified.
- **Log Source:** `FPGA_code/logs/mode_a_extended_training/mode_a_500ep_5ms_pure_toeplitz_reg150_swing40_var3.json`
- **Figure:** `/home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/docs/figures/fig_mode_a_500ep_5ms_pure_toeplitz_reg150_swing40_var3.png`
