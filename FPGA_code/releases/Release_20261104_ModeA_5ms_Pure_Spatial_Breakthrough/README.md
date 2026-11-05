# Inverted MAML Release Package: Pure Spatial 5.0 ms Breakthrough
**Release Tag:** `Release_20261104_ModeA_5ms_Pure_Spatial_Breakthrough`  
**Date:** 2026-11-04  
**Hardware:** Card 2 (PCB v1.3.2, 1k/3.3k Attenuator Mod, Repaired CH3) | Trion T120 SoC + T20 Coprocessor  
**Benchmark:** 1,000-Epoch Pure Spatial 5.0 ms Snapshot | "Naked" Batch K=1 Online SGD | Fig 7 Disturbance ±5 LSB  
**Peak Achievement:** 7.17 bits ENOB (605.5 LSB² loss), 7.72x Ablation Contrast, >95 LSB Linear Headroom  

---

## 1. Release Manifest & Directory Structure

- `sw/t120_master/`: C firmware source code (RISC-V Sapphire SoC), headers, Makefile, and compiled hex/binaries.
- `T120F324/`: Open-source SystemVerilog logic source files, pin constraints (const.sdc), timing constraints, and verified bitstream/hex. (Proprietary Efinix IP excluded).
- `T20F256/`: Open-source SystemVerilog logic source files for the T20 coprocessor and verified bitstream/hex. (Proprietary Efinix IP excluded).
- `pc_python/`: Python host runner, version verification guard, JTAG flash script, and telemetry driver.
- `reports_and_logs/`: Full 1000-epoch silicon JSON dataset log, publication PDF report, and synthesis documentation.

---

## 2. Exact Reproduction & Re-Run Commands

### Verify & Flash Firmware:
```bash
/home/olle/anaconda3/bin/python pc_python/verify_and_guard_version.py
/home/olle/anaconda3/bin/python pc_python/flash_soc.py
```

### Re-Run 1000-Epoch Benchmark:
```bash
/home/olle/anaconda3/bin/python pc_python/run_and_report_5ms_pure.py --epochs 1000 --lr 0.02 --reg 2048 --swing 40 --var 5 --attenuator 1k/3.3k
```

### Re-Generate Publication PDF Report:
```bash
/home/olle/anaconda3/bin/python pc_python/generate_mode_a_var5_comprehensive_report.py
```

---

## 3. Hardware Configuration State
- **Primary Attenuator:** $1\text{ k}\Omega / 3.3\text{ k}\Omega$ ($-12.7\text{ dB}$) on ColTIA virtual ground summing junction.
- **In-Data Drivers:** High-current `MCP664-E/SL` installed on DAC2 rows 1..6.
- **Operating Delay:** Fixed static snapshot at $t = 5000\text{ \mu s}$ ($5.0\text{ ms}$).
- **Disturbance Protocol:** Patent SE 2630397-4 Fig 7 Emulator active (±5 LSB injected on M33 every 100 epochs).
