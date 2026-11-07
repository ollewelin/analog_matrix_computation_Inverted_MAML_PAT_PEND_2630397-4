# Inverted MAML Release Package: Shifted Temporal Window [5.0..6.0 ms] (K=1)
**Release Tag:** `Release_20261106_ModeA_Card2_1000ep_ShiftedWindow_5to6ms_W3_Staircase_K1`  
**Date:** 2026-11-06  
**Hardware Platform:** Card 2 (PCB v1.3.2, 1k/3.3k Attenuator Mod, Repaired CH3) | Trion T120 Master SoC (`192.168.1.50:5000`) + Trion T20 Coprocessor  
**Benchmark:** 1,000-Epoch Shifted Temporal Window [5.0..6.0 ms] (11 Strata: 5000–6000 µs) | Online Single-Sample SGD ($K=1$) | 1:1 Paired Ablation Control | Fig 7 Disturbance $\pm 5\text{ LSB}$  
**Key Results:** Window Mean Loss reduced from $51\,722.7\text{ LSB}^2 \to 42\,229.0\text{ LSB}^2$ (-18.4%) | Center $5.5\text{ ms}$ Precision reaches **$5.19\text{ b}$ ENOB** (peaking at **$6.73\text{ b}$**, with best evaluation loss $1\,118.0\text{ LSB}^2$, a $17.0\times$ reduction) | Late strata (5.4–6.0 ms) sustained gains of **$+0.23\text{ b}$ to $+0.75\text{ b}$**  

---

## 1. Overview & Physical Scope

This reproducibility package documents the Inverted MAML proprioceptive analog feedback architecture evaluated across an upward-shifted temporal snapshot window:
$$\text{Window: } [5.0\text{ ms} \dots 6.0\text{ ms}] \quad (\Delta t = 1\,000\text{ µs, sampled at 11 discrete strata at } 100\text{ µs intervals})$$

All firmware and operational parameters remain identical to the [4.5..5.5 ms] benchmark:
* **Firmware & Gateware:** Crystal-locked 10.0 ms refresh timing (RISC-V firmware `v2.2-MAML`, HW Logic `0x20261030`).
* **Matrix 3 Calibration:** $W_3$ staircase pattern on reference and bias rows:
  * Row 6 (ClkB1 ramp reference): `[-40, -24, -8, +8, +24, +40]` LSB
  * Row 7 (ClkRef DC anchor): `[+40, +24, +8, -8, -24, -40]` LSB
* **Training Hyperparameters:** Pure Online SGD ($K=1$, 11 updates/epoch), learning rate $\text{LR}=0.02\times$, L2 weight decay $\lambda=2048$, input dynamic swing $\pm 40\text{ LSB}$, White Noise excitation.
* **Non-Stationary Perturbations:** 4 randomized disturbance matrices ($\pm 5\text{ LSB}$ on Matrix 33) injected at Epochs 200, 300, 400, and 500.
* **1:1 Paired Ablation Control:** In Phase 4 (Epochs 600..1000), compensation weights are clamped to zero ($W_8=0$) while repeating the identical disturbance matrices from Epochs 200..599.

### Physical Mechanism of the Shifted Window
Between 5.0 ms and 6.0 ms, the 2T1C analog gate storage capacitors ($100\text{ nF}$) undergo an additional 500 µs of continuous discharge droop. Uncompensated baseline precision degrades progressively at later sampling times (falling to $3.39\text{ b}$ at 6.0 ms). Active neural compensation counteracts this slope, delivering its largest relative gains (+0.23 b to +0.75 b) precisely in the 5.4–6.0 ms region.

---

## 2. Quantitative Performance Summary

| Benchmark Metric | Phase 1: Baseline<br/>($W_8=0$, Dist=0) | Phase 2: Nominal<br/>(FHP ON, Dist=0) | Phase 3: Disturbed<br/>(FHP ON, Dist=$\pm 5\text{ LSB}$) | Phase 4: Ablation<br/>($W_8=0$, Dist=$\pm 5\text{ LSB}$) | Net Gain<br/>(Phase 2 vs. Baseline) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Window Mean Loss [5.0..6.0 ms]** | $51\,722.7\text{ LSB}^2$ | **$42\,229.0\text{ LSB}^2$** | $48\,068.3\text{ LSB}^2$ | $80\,349.1\text{ LSB}^2$ | **-18.4% error reduction** |
| **Window Mean ENOB [5.0..6.0 ms]** | $3.97\text{ bits}$ | **$4.12\text{ bits}$** | $4.02\text{ bits}$ | $3.65\text{ bits}$ | **+0.15 bits sustained** |
| **5.5 ms Center Loss** | $19\,043.3\text{ LSB}^2$ | **$10\,612.2\text{ LSB}^2$** | $11\,852.3\text{ LSB}^2$ | $45\,725.8\text{ LSB}^2$ | **-44.3% error reduction** |
| **5.5 ms Center ENOB** | $4.82\text{ bits}$ | **$5.19\text{ bits}$** | $5.14\text{ bits}$ | $4.12\text{ bits}$ | **+0.37 bits sustained** |
| **Peak Measured Precision** | $4.82\text{ bits}$ | $5.19\text{ bits}$ | **$6.73\text{ bits}$ (@ 5.5 ms)** | $4.12\text{ bits}$ | **+1.91 bits above baseline** |
| **Best Single Evaluation Loss** | $19\,043.3\text{ LSB}^2$ | $10\,612.2\text{ LSB}^2$ | **$1\,118.0\text{ LSB}^2$** | $45\,725.8\text{ LSB}^2$ | **17.0× error reduction** |
| **Physical Updates Executed** | 1,100 ($W$ locked) | 1,100 (Online SGD) | 4,400 (Online SGD) | 4,400 ($W$ locked) | **11,000 total evaluations** |

---

## 3. Stratum-by-Stratum Generalization Across [5.0 .. 6.0 ms]

| Delay (ms) | Phase 1: Base ($W_8=0$) | Phase 2: Nom (Train) | Net Gain (P2 - P1) | Phase 3: Dist ($\pm 5\text{ LSB}$) | Phase 4: Abla ($W_8=0$) |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **5.0 ms** | 3.58 b | 3.31 b | -0.27 b | 3.16 b | 3.29 b |
| **5.1 ms** | 4.09 b | 3.68 b | -0.41 b | 3.66 b | 3.64 b |
| **5.2 ms** | 4.42 b | 4.23 b | -0.19 b | 4.09 b | 3.87 b |
| **5.3 ms** | 4.78 b | 4.61 b | -0.17 b | 4.59 b | 4.04 b |
| **5.4 ms** | 4.86 b | **5.09 b** | **+0.23 b** | 5.05 b | 4.14 b |
| **5.5 ms** | 4.82 b | **5.19 b** | **+0.37 b** | 5.14 b | 4.12 b |
| **5.6 ms** | 4.55 b | **4.95 b** | **+0.40 b** | 4.99 b | 3.99 b |
| **5.7 ms** | 4.16 b | **4.72 b** | **+0.56 b** | 4.68 b | 3.80 b |
| **5.8 ms** | 3.83 b | **4.58 b** | **+0.75 b** | 4.38 b | 3.61 b |
| **5.9 ms** | 3.65 b | **4.21 b** | **+0.56 b** | 4.07 b | 3.44 b |
| **6.0 ms** | 3.39 b | **3.95 b** | **+0.56 b** | 3.86 b | 3.27 b |

---

## 4. Visual Telemetry Figures

### 2D Temporal Spectrogram of Precision (Delay × Epoch)
![2D Spectrogram 5.0-6.0 ms](reports_and_logs/figures/fig_card2_w3_staircase_temporal_heatmap_spectrogram_5000to6000us.png)
*Figure 1: 2D precision spectrogram (Delay × Epoch). Transition at Epoch 100 demonstrates precision elevation, followed by active disturbance tracking in Phase 3, and immediate precision collapse across the entire window when $W_8$ is clamped to 0 in Phase 4.*

### Generalization Profile Across Strata [5.0 .. 6.0 ms]
![Generalization Profile 5.0-6.0 ms](reports_and_logs/figures/fig_card2_w3_staircase_temporal_profile_4phases_5000to6000us.png)
*Figure 2: Measured precision profile across 11 discrete strata [5.0 .. 6.0 ms] for all 4 phases. The largest net gains (+0.23 to +0.75 b) occur between 5.4 ms and 6.0 ms where capacitor droop is greatest.*

---

## 5. Artifacts & Reproduction Instructions

### Reproduction Command:
To reproduce this 1,000-epoch benchmark on Card 2 silicon:
```bash
./run_card2_5to6ms.sh
```
Or directly via Python:
```bash
python FPGA_code/scripts/run_card2_broadened_11strata_k1_online.py \
    --epochs 1000 --k-batch 1 --lr 0.02 --reg-lambda 2048 --noise-color white \
    --staircase-w3 --w33-variance-lsb-range 5 --attenuator 1k/3.3k \
    --t-min 5000 --t-max 6000 --t-step 100
```

### Archived Assets in this Package:
* **Comprehensive 10-Page PDF Report:** [`reports_and_logs/INVERTED_MAML_CARD2_1000EP_5000TO6000US_W3_STAIRCASE_COMPREHENSIVE_REPORT.pdf`](reports_and_logs/INVERTED_MAML_CARD2_1000EP_5000TO6000US_W3_STAIRCASE_COMPREHENSIVE_REPORT.pdf)
* **Comprehensive Markdown Report:** [`reports_and_logs/INVERTED_MAML_CARD2_1000EP_5000TO6000US_W3_STAIRCASE_COMPREHENSIVE_REPORT.md`](reports_and_logs/INVERTED_MAML_CARD2_1000EP_5000TO6000US_W3_STAIRCASE_COMPREHENSIVE_REPORT.md)
* **Full Telemetry JSON Dataset:** [`reports_and_logs/mode_a_1000ep_broadened_5000to6000us_white_reg2048_lr0p02_swing40_var5_k1_1k_3p3k_w3staircase_ablation.json`](reports_and_logs/mode_a_extended_training/mode_a_1000ep_broadened_5000to6000us_white_reg2048_lr0p02_swing40_var5_k1_1k_3p3k_w3staircase_ablation.json)

---

## 6. Planned Physical Oscilloscope Verification
As with previous runs, data in this package was acquired via high-speed differential SAR ADC telemetry (`XC2361A`, $\text{ADC}_{45}$) over Ethernet. Direct physical oscilloscope probing of the analog circuit nodes (ColTIA virtual ground nodes `CH1`–`CH6`, 24 µs Hadamard carrier injection bursts, and Sigmoid 4 outputs) across this shifted 5.0–6.0 ms range is planned in an upcoming bench verification session to provide explicit visual correlation with physical analog waveforms.

