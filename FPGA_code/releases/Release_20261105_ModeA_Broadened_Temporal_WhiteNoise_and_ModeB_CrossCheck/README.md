# Inverted MAML Release Package: Broadened Temporal Window [4.5..5.5 ms] White Noise & Mode B Cross-Check
**Release Tag:** `Release_20261105_ModeA_Broadened_Temporal_WhiteNoise_and_ModeB_CrossCheck`  
**Date:** 2026-11-05  
**Hardware:** Card 2 (PCB v1.3.2, 1k/3.3k Attenuator Mod, Repaired CH3) | Trion T120 SoC + T20 Coprocessor  
**Benchmark:** 1,000-Epoch Broadened Temporal Window [4.5..5.5 ms, 11 Strata] | White Noise Stream | Mode A vs. Mode B Cross-Check  
**Key Achievements:**
  - Mode A: 6.29 b peak ENOB (2063 LSB² loss), -64.6% window error reduction, 5.08x ablation contrast.
  - Mode B (Negative Control): Jumpers disconnected, un-damped M33 forward pass, trapped at 3.20 b window mean (zero learning, 1.14x ablation contrast).
  - Definitive physical proof that Inverted MAML operates via active analog current injection, ruling out passive damping or math artifacts.

---

## 1. Release Manifest & Directory Structure

- `sw/t120_master/`: C firmware source code (RISC-V Sapphire SoC), headers, Makefile, and compiled hex/binaries.
- `T120F324/`: Open-source SystemVerilog logic source files, pin constraints (const.sdc), timing constraints, and verified bitstream/hex. (Proprietary Efinix IP excluded).
- `T20F256/`: Open-source SystemVerilog logic source files for the T20 coprocessor and verified bitstream/hex. (Proprietary Efinix IP excluded).
- `pc_python/`: Python host runner, version verification guard, JTAG flash script, and telemetry driver.
- `reports_and_logs/`: Full 1000-epoch Mode A and Mode B JSON dataset logs, 10-page White Noise publication report, 4-page Cross-Check publication report, and markdown report.

---

## 2. Exact Reproduction & Re-Run Commands

### Verify & Flash Firmware:
```bash
/home/olle/anaconda3/bin/python pc_python/verify_and_guard_version.py
/home/olle/anaconda3/bin/python pc_python/flash_soc.py
```

### Re-Run Mode A Broadened Window [4.5..5.5 ms] White Noise:
```bash
/home/olle/anaconda3/bin/python pc_python/run_card2_broadened_11strata_k1_online.py --epochs 1000 --lr 0.02 --reg-lambda 2048 --d-line 2 --noise-color white --w33-variance-lsb-range 5 --attenuator 1k/3.3k --prefix mode_a
```

### Re-Run Mode B (Jumpers Disconnected Negative Control):
```bash
# Ensure physical jumpers are unplugged from H1$CBB8 on Card 2
/home/olle/anaconda3/bin/python pc_python/run_card2_broadened_11strata_k1_online.py --epochs 1000 --lr 0.02 --reg-lambda 2048 --d-line 2 --noise-color white --w33-variance-lsb-range 5 --attenuator 1k/3.3k --prefix mode_b
```

### Re-Generate Reports:
```bash
/home/olle/anaconda3/bin/python pc_python/generate_broadened_online_white_noise_comprehensive_report.py
/home/olle/anaconda3/bin/python pc_python/generate_mode_b_crosscheck_report_pdf.py
```

---

## 3. Technical Notes on C Firmware vs. Python Driver Orchestration
- **C Firmware is 100% UNIFIED:** The RISC-V C-firmware (`v2.2-MAML`, HW `0x20261030`) is identical across both Release 1 and Release 2. The kernel natively accepts `(k_batch, num_strata, t_min_us, t_max_us, lr, reg)` via `MAML_CMD_BATCH_STEP` and handles Patent Fig 7 perturbations.
- **Python Host Orchestration:** What changes between Release 1 and Release 2 is purely the Python driver:
  - In Release 1, delay is held static at 5000 µs for all 1000 epochs.
  - In Release 2, the Python host iterates through 11 discrete strata [4500..5500 µs] per epoch, executing 11 sequential physical forward passes and 11 immediate on-chip weight updates per epoch (11,000 updates total) across the capacitor discharge ramp.
