# Inverted MAML Release Package: Card 2 W(3) Staircase Calibration & Paired-Ablation Control (K=1 Online SGD)
**Release Tag:** `Release_20261106_ModeA_Card2_1000ep_W3_Staircase_K1_PairedAblation`  
**Date:** 2026-11-06  
**Hardware Platform:** Card 2 (PCB v1.3.2, 1k/3.3k Attenuator Mod, Repaired CH3) | Trion T120 Master SoC (`192.168.1.50:5000`) + Trion T20 Coprocessor  
**Benchmark:** 1,000-Epoch Broadened Temporal Window [4.5..5.5 ms] | Online Single-Sample SGD ($K=1$) | 1:1 Paired Ablation Control | Fig 7 Disturbance $\pm 5\text{ LSB}$  
**Empirical Verdict:** Active Error Reduction $>52\%$ ($73\,911\text{ LSB}^2 \to 154\,613\text{ LSB}^2$, $+109\%$ error surge on ablation $W_8=0$) with Crystal-Locked 10.0 ms Timing  

---

## 1. Executive Summary & Verification Context

Following the November 5 retrospective ([`INVESTIGATION_REPORT_TIMING_JITTER_AND_BASELINE_ARTIFACTS.md`](../../docs/INVESTIGATION_REPORT_TIMING_JITTER_AND_BASELINE_ARTIFACTS.md)), which proved that earlier apparent 7x–9x breakthroughs were software artifacts of a $10/20\text{ ms}$ refresh jitter bug, this release establishes the **first definitive, verified benchmark of Inverted MAML on physical silicon with crystal-locked 10.0 ms timing**.

### Key Innovations in this Release:
1. **Crystal-Locked 10.0 ms Timing:** All UART diagnostic prints removed from the C firmware inner polling loop; refresh intervals strictly locked to hardware CLINT timer boundaries.
2. **Matrix 3 Temporal Reference Staircase Pattern:** Columns 0..5 initialized with $W_3 \in [-40, -24, -8, +8, +24, +40]\text{ LSB}$ across Rows 7 & 8, providing dynamic swing and linear inflection sensitivity across all 11 strata ($4.5\dots 5.5\text{ ms}$).
3. **1:1 Paired Ablation Control:** Phase 3 (Active Compensation, Epochs 200..599) and Phase 4 (Ablation $W_8=0$, Epochs 600..1000) evaluate against the **exact identical 4 disturbance matrices** on $M_{33}$ (Patent SE 2630397-4 Fig 7 Emulator).
4. **Empirical Ground Truth:**
   - **Phase 3 (Active Compensation under $\pm 5\text{ LSB}$ Disturbance):** Mean Window Loss = $73\,911.2\text{ LSB}^2$ ($4.05\text{ b}$ ENOB); Center $5.0\text{ ms}$ precision = $5.00\text{ b}$ ENOB ($12\,455\text{ LSB}^2$).
   - **Phase 4 (Ablation $W_8=0$ under Identical Disturbance):** Mean Window Loss = $154\,613.5\text{ LSB}^2$ ($3.48\text{ b}$ ENOB); Center $5.0\text{ ms}$ precision = $3.41\text{ b}$ ENOB ($36\,329\text{ LSB}^2$).
   - **Ablation Surge:** Disabling active compensation causes a **$+109\%$ surge in quadratic error** ($2.09\times$), proving active physical analog error cancellation on live silicon without any software artifacts.

---

## 2. Directory Structure & Contents

```
Release_20261106_ModeA_Card2_1000ep_W3_Staircase_K1_PairedAblation/
├── README.md                                          # This documentation
├── T120F324/                                          # Master FPGA (Trion T120F324)
│   ├── bitstreams/
│   │   ├── T120_MALM.bit                              # Synthesized SRAM bitstream
│   │   └── T120_MALM.hex                              # SPI Flash binary
│   ├── const.sdc                                      # Timing constraints
│   ├── T120_MALM.xml / T120_MALM.peri.xml            # Efinity project definitions
│   └── *.sv, *.svh                                    # Open-source SystemVerilog HDL
├── T20F256/                                           # Coprocessor FPGA (Trion T20F256)
│   ├── bitstreams/
│   │   ├── T20F256.bit / T20F256.hex
│   └── *.sv, const.sdc, *.xml                         # Open-source Coprocessor HDL
├── sw/t120_master/                                    # RISC-V C Firmware
│   ├── src/ (main.c, maml_platform.c, eth_mac_100m.c) # Clean crystal-locked C source
│   ├── include/                                       # Headers and register maps
│   ├── binaries/ / build/                             # Compiled hex/binaries
│   └── Makefile                                       # Standard RISC-V build flow
├── pc_python/                                         # Host Orchestration & Calibration
│   ├── run_card2_broadened_11strata_k1_online.py      # Hardware runner (K=1 online SGD)
│   ├── config/w3_staircase_pattern.py                 # W(3) staircase bias calibration
│   ├── udp_client.py                                  # Low-level Ethernet driver
│   ├── verify_and_guard_version.py                    # Version guard & sanity check
│   └── generate_card2_w3_staircase_comprehensive_report.py
└── reports_and_logs/                                  # Complete Benchmark Evidence
    ├── dataset_1000ep_k1.json                         # Raw 1000-epoch silicon telemetry
    ├── INVERTED_MAML_CARD2_1000EP_W3_STAIRCASE_COMPREHENSIVE_REPORT.pdf  # 10-page report
    ├── INVERTED_MAML_CARD2_1000EP_W3_STAIRCASE_COMPREHENSIVE_REPORT.md  # Markdown report
    └── figures/                                       # All 10 publication figures
```

---

## 3. Reproduction & Execution Instructions

### A. Hardware Verification
Connect Card 2 via Ethernet to host PC (`192.168.1.50:5000`):
```bash
/home/olle/anaconda3/bin/python pc_python/verify_and_guard_version.py
```

### B. Flash Firmware (if needed)
```bash
/home/olle/anaconda3/bin/python pc_python/flash_soc.py
```

### C. Run 1000-Epoch Online Single-Sample SGD ($K=1$) Benchmark
```bash
/home/olle/anaconda3/bin/python pc_python/run_card2_broadened_11strata_k1_online.py \
    --epochs 1000 \
    --k-batch 1 \
    --lr 0.02 \
    --reg 2048 \
    --swing 40 \
    --var 5 \
    --ip 192.168.1.50
```

### D. Generate 10-Page Comprehensive Report & Figures
```bash
/home/olle/anaconda3/bin/python pc_python/generate_card2_w3_staircase_comprehensive_report.py --k-batch 1
```
