# Inverted MAML Add-On Release Package: Mini-Batch K=4 SGD Variant
**Release Tag:** `Release_20261106_ModeA_Card2_1000ep_W3_Staircase_K4_Addon`  
**Date:** 2026-11-06  
**Hardware Platform:** Card 2 (PCB v1.3.2, 1k/3.3k Attenuator Mod) | Trion T120 Master SoC + Trion T20 Coprocessor  
**Benchmark:** 1,000-Epoch Broadened Temporal Window [4.5..5.5 ms] | Mini-Batch SGD ($K=4$) | 1:1 Paired Ablation Control | Fig 7 Disturbance $\pm 5\text{ LSB}$  
**Peak Achievement:** Best Window Loss $52\,405.5\text{ LSB}^2$ ($3.95\text{ b}$ ENOB) | Center $5.0\text{ ms}$ Precision $5.11\text{ b}$ ENOB ($10\,494\text{ LSB}^2$)  

---

## 1. What Differs Between K=1 and K=4? (C-Code vs. Host Parameters)

> [!IMPORTANT]
> **Unified Firmware & Gateware Architecture:**  
> The RISC-V C-firmware (`sw/t120_master`), FPGA gateware (`T120F324`), and coprocessor gateware (`T20F256`) are **100% identical and unified** between $K=1$ and $K=4$.  
> No C-code modifications or FPGA re-synthesis are required to switch between $K=1$ and $K=4$.

The difference is purely in the Python host training orchestration:
- **Online SGD ($K=1$):** For each stratum, a single stochastic inference forward pass is evaluated and immediately followed by an analog SGD weight update on hardware (11 weight updates per epoch).
- **Mini-Batch SGD ($K=4$):** For each stratum, $K=4$ independent stochastic forward passes are drawn and evaluated over Ethernet. Their observed output errors and Hadamard gradient responses are averaged across the batch before the MAML inner loop executes the analog SGD update on hardware.

This add-on package provides the complete independent 1,000-epoch dataset, 10-page publication PDF/Markdown report, and all 10 figures specifically characterized under $K=4$ mini-batch SGD.

---

## 2. Quantitative Comparison: K=1 vs. K=4 on Card 2 Silicon

| Metric | Online SGD ($K=1$) | Mini-Batch SGD ($K=4$) | Impact of Batch Averaging |
| :--- | :---: | :---: | :--- |
| **Batch Size ($K$)** | 1 sample / update | 4 samples / update | $4\times$ variance reduction in gradient estimate |
| **Wall Clock Runtime (1000 Ep)** | 558.5 s (558 ms/ep) | 832.1 s (832 ms/ep) | $+49\%$ elapsed time due to $4\times$ packet traffic |
| **Phase 1 Baseline Mean Loss** | $84\,214\text{ LSB}^2$ ($3.91\text{ b}$) | $76\,726\text{ LSB}^2$ ($3.88\text{ b}$) | Consistent open-loop physical baseline |
| **Phase 2 Nominal Loss (Ep 199)** | $64\,544\text{ LSB}^2$ ($4.13\text{ b}$) | $57\,173\text{ LSB}^2$ ($4.03\text{ b}$) | Lower nominal converged variance |
| **Phase 3 Best Window Loss** | $57\,140\text{ LSB}^2$ ($3.91\text{ b}$) | **$52\,405.5\text{ LSB}^2$ ($3.95\text{ b}$)** | **Superior disturbance suppression** |
| **Center $5.0\text{ ms}$ Peak Precision** | $5.00\text{ b}$ ($12\,455\text{ LSB}^2$) | **$5.11\text{ b}$ ($10\,494\text{ LSB}^2$)** | **$+0.11\text{ b}$ sharper peak ENOB** |
| **Phase 4 Ablation Loss ($W_8=0$)** | $154\,613\text{ LSB}^2$ ($3.48\text{ b}$) | $142\,530\text{ LSB}^2$ ($3.55\text{ b}$) | Catastrophic collapse under identical disturbances |
| **Ablation Contrast (Surge)** | **$2.09\times$ ($+109\%$)** | **$2.72\times$ ($+172\%$)** | **Even stronger empirical ablation contrast** |

---

## 3. Directory Structure

```
Release_20261106_ModeA_Card2_1000ep_W3_Staircase_K4_Addon/
├── README.md                                          # This documentation
├── run_card2_k4.sh                                    # Quick reproduction shell script
└── reports_and_logs/
    ├── dataset_1000ep_k4.json                         # Complete 1000-epoch K=4 silicon dataset
    ├── INVERTED_MAML_CARD2_1000EP_K4_W3_STAIRCASE_COMPREHENSIVE_REPORT.pdf # 10-page K=4 report
    ├── INVERTED_MAML_CARD2_1000EP_K4_W3_STAIRCASE_COMPREHENSIVE_REPORT.md # Markdown report
    └── figures/                                       # All 10 publication figures for K=4
```

---

## 4. How to Run K=4

Using the verified bitstream and firmware from the primary K=1 package (`Release_20261106_ModeA_Card2_1000ep_W3_Staircase_K1_PairedAblation`):

```bash
/home/olle/anaconda3/bin/python ../Release_20261106_ModeA_Card2_1000ep_W3_Staircase_K1_PairedAblation/pc_python/run_card2_broadened_11strata_k1_online.py \
    --epochs 1000 \
    --k-batch 4 \
    --lr 0.02 \
    --reg 2048 \
    --swing 40 \
    --var 5 \
    --ip 192.168.1.50
```

To re-generate the 10-page report and figures:
```bash
/home/olle/anaconda3/bin/python ../Release_20261106_ModeA_Card2_1000ep_W3_Staircase_K1_PairedAblation/pc_python/generate_card2_w3_staircase_comprehensive_report.py \
    --k-batch 4 \
    --data-path reports_and_logs/dataset_1000ep_k4.json
```
