# Release 2026-11-08: Card 2 Physical Thermal Stress & Real-Time Mode A Active Drift Rejection

**Hardware Platform:** Card 2 (PCBA v1.3.2 | Trion T120F324 Master SoC + Trion T20F256 Coprocessor)  
**Patent Pending:** SE 2630397-4 (Inverted MAML Silicon)  
**Release Tag:** `Release_20261108_ModeA_Card2_ThermalStress_Cycling_30pctDuty_1Hz`  
**Date:** 2026-11-08  
**Author & Inventor:** Olle Welin  

---

## 1. Overview & Experimental Highlights

This release provides the complete, self-contained reproducibility package for the **20-minute physical thermal stress and real-time Mode A active drift rejection benchmark** executed on Card 2 live silicon on November 8, 2026.

### Key Milestones:
1. **100% Real Physical Thermal Cycling:** Four on-board power resistors were driven at **30% duty cycle pulsed at 1.0 Hz PWM** (300 ms ON / 700 ms OFF) in an 8-minute ON / 8-minute OFF thermal cycle, interleaved with a 2-minute ON / 2-minute OFF Mode A online SGD regulation cycle ($K=2$, $\text{LR}=0.02$, $\lambda=768$).
2. **Focused Temporal Sampling Window [5.0 – 5.4 ms]:** Evaluated across 5 strata spaced by 100 µs (5000, 5100, 5200, 5300, 5400 µs, nominal center at 5.2 ms), locking all measurements into the linear high-sensitivity inflection regime of Sigmoid 4.
3. **BJT Differential Saturation Guard:** Embedded firmware clip detection (`SIG4_CLIP_THRESHOLD_LSB=1415`, `SIG10_CLIP_THRESHOLD_LSB=1680`) completely eliminated ColTIA transimpedance amplifier saturation and phantom gradient accumulation.
4. **Definitive 2x2 Factorial Demonstration:**
   - When the board cooled down without compensation ($W_8=0$), open-loop error surged by **+2.48x** to **75,637.8 LSB²** (ENOB collapsing to **3.70 bits**).
   - Under active Mode A SGD regulation, the compensator drove error down to **22,753.5 LSB²** (**-69.9% error reduction**, +1.00 bit gain to **4.69 / 5.00 bits**).
   - Matrix 8 dynamically deployed an asymmetric positive bias reaching **+117 LSB (98% of the ±120 LSB hardware rail)** to counteract cold transistor drift.

---

## 2. 2x2 Factorial Performance Summary Table (3,331 Epochs)

| Factorial Condition | Thermal State | Regulation State | Mean Loss (LSB²) | Window ENOB | 5.2 ms Center ENOB | Matrix 8 Dynamic Envelope | Performance Delta |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **1. Warm Closed-Loop** | Heaters ON (30% @ 1Hz) | Comp ON (SGD, K=2, λ=768) | **22,067.4 L²** | **4.62 b** | **5.01 b** | [-51, +72] LSB | Baseline Reference |
| **2. Warm Open-Loop** | Heaters ON (30% @ 1Hz) | Comp OFF (Ablation W8=0) | **30,557.5 L²** | **4.36 b** | **4.69 b** | [0, 0] LSB | Warm Uncompensated |
| **3. Cold Closed-Loop** | Heaters OFF (Cooling) | Comp ON (SGD, K=2, λ=768) | **22,753.5 L²** | **4.69 b** | **5.00 b** | **[-32, +117] LSB** | **-69.9% Error Reduction** (+1.00 b Gain) |
| **4. Cold Open-Loop** | Heaters OFF (Cooling) | Comp OFF (Ablation W8=0) | **75,637.8 L²** | **3.70 b** | **3.72 b** | [0, 0] LSB | **+2.48x Error Surge** (Severe Degradation) |

---

## 3. Package Structure

```
Release_20261108_ModeA_Card2_ThermalStress_Cycling_30pctDuty_1Hz/
├── README.md                                    # This document
├── reports_and_logs/
│   ├── INVERTED_MAML_CARD2_THERMAL_STRESS_COMPREHENSIVE_REPORT.pdf  # 11-page publication report
│   ├── INVERTED_MAML_CARD2_THERMAL_STRESS_COMPREHENSIVE_REPORT.md   # Full Markdown report
│   ├── card2_thermal_cycling_heaters_8m8m_30pct_1hz_...20min.json   # Complete 3,331-epoch dataset
│   └── figures/
│       ├── fig_card2_thermal_timeline.png       # 2D curves of Loss, ENOB & W8 over 20 min
│       ├── fig_card2_thermal_waterfall.png      # Spatio-temporal waterfall heatmap
│       ├── fig_card2_thermal_2d_matrices.png    # 2D weight trajectories across epochs (M8 & M3)
│       ├── fig_card2_thermal_strata_profiles.png# Strata profiles for all 4 factorial states
│       ├── fig_card2_thermal_factorial_summary.png# 2x2 Factorial summary card
│       ├── fig_card2_pcb_thermal_heaters.jpg    # Photograph of Card 2 operating under thermal stress
│       └── fig_card2_thermal_gui_full_run.jpg   # Real-time GUI monitor screenshot at epoch 3330
├── pc_python/
│   ├── run_card2_thermal_cycling.py             # 20-minute thermal cycling runner script
│   ├── generate_card2_thermal_cycling_report.py # 2D figure generator
│   ├── compile_card2_thermal_report_pdf.py      # 11-page publication PDF/MD compiler
│   ├── thermal_live_gui.py                      # Real-time PySide6/PyQt5 GUI monitor
│   ├── udp_client.py                            # Binary UDP protocol client
│   ├── verify_and_guard_version.py              # Hardware/firmware version verification guard
│   ├── flash_soc.py                             # Automated BRAM merging & JTAG programmer
│   ├── program_t120.py                          # JTAG programmer
│   └── config/
│       ├── w3_staircase_pattern.py              # W(3) Staircase binary payload builder
│       └── w3_staircase_pattern.json            # Staircase configuration vector
├── sw/t120_master/                              # RISC-V C-firmware (v2.2-MAML)
│   ├── src/maml_platform.c                      # Core firmware with BJT saturation guard & 10ms engine
│   ├── include/maml_platform.h
│   └── Makefile
├── T120F324/                                    # Master SoC HDL & Bitstream
│   └── bitstreams/
│       ├── T120_MALM.bit                        # Synthesized bitstream (HW 0x20261030)
│       └── T120_MALM.hex                        # Flash hex file
└── T20F256/                                     # Coprocessor HDL & Bitstream
    └── bitstreams/
        ├── T20F256.bit                          # Coprocessor bitstream
        └── T20F256.hex
```

---

## 4. How to Reproduce & Execute

### Run 20-Minute Thermal Cycling Experiment:
```bash
/home/olle/anaconda3/bin/python pc_python/run_card2_thermal_cycling.py \
    --duration-minutes 20.0 \
    --heater-on 8.0 --heater-off 8.0 \
    --heater-duty-pct 30.0 --heater-pwm-hz 1.0 \
    --regler-on 2.0 --regler-off 2.0 \
    --l2-reg 768 --k-batch 2 --lr 0.02
```

### Launch Real-Time Monitoring GUI:
```bash
/home/olle/anaconda3/bin/python pc_python/thermal_live_gui.py
```

### Generate Figures & Compile 11-Page PDF Report:
```bash
/home/olle/anaconda3/bin/python pc_python/generate_card2_thermal_cycling_report.py
/home/olle/anaconda3/bin/python pc_python/compile_card2_thermal_report_pdf.py
```
