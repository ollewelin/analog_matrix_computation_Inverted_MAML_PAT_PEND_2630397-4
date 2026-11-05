#!/usr/bin/env python3
"""
create_release_packages.py
Inverted MAML (Patent Pending SE 2630397-4) - Open Science Hardware

Creates two self-contained release directories under FPGA_code/releases/:
1. Release_20261104_ModeA_5ms_Pure_Spatial_Breakthrough
2. Release_20261105_ModeA_Broadened_Temporal_WhiteNoise_and_ModeB_CrossCheck

Packages:
  - C firmware source (maml_platform.c, headers, bsp, Makefile, binaries)
  - T120 Master SoC Verilog/SystemVerilog logic files & bitstream/hex (NO proprietary Efinix IP!)
  - T20 Coprocessor Verilog/SystemVerilog logic files & bitstream/hex (NO proprietary Efinix IP!)
  - PC Python driver and verification scripts
  - Live silicon JSON dataset logs and publication PDF reports
  - Comprehensive README with hardware configuration and re-run runbooks
"""

import os
import shutil
import hashlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RELEASES_ROOT = REPO_ROOT / "FPGA_code" / "releases"
RELEASES_ROOT.mkdir(parents=True, exist_ok=True)

REL1_DIR = RELEASES_ROOT / "Release_20261104_ModeA_5ms_Pure_Spatial_Breakthrough"
REL2_DIR = RELEASES_ROOT / "Release_20261105_ModeA_Broadened_Temporal_WhiteNoise_and_ModeB_CrossCheck"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()[:16]


def copy_c_firmware(target_dir: Path):
    sw_target = target_dir / "sw" / "t120_master"
    sw_target.mkdir(parents=True, exist_ok=True)
    
    src_base = REPO_ROOT / "FPGA_code" / "sw" / "t120_master"
    
    # 1. src/
    shutil.copytree(src_base / "src", sw_target / "src", dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("*copy*", "*~", "#*"))
    # 2. include/
    shutil.copytree(src_base / "include", sw_target / "include", dirs_exist_ok=True)
    # 3. bsp/
    if (src_base / "bsp").exists():
        shutil.copytree(src_base / "bsp", sw_target / "bsp", dirs_exist_ok=True)
    # 4. Makefile and configs
    for f in ["Makefile", "cpu0.yaml"]:
        if (src_base / f).exists():
            shutil.copy2(src_base / f, sw_target / f)
    # 5. Compiled binaries
    bin_target = sw_target / "binaries"
    bin_target.mkdir(parents=True, exist_ok=True)
    for bf in [src_base / "build" / "t120_master.hex",
               src_base / "build" / "t120_master.bin",
               src_base / "rom" / "t120_master.bin"]:
        if bf.exists():
            shutil.copy2(bf, bin_target / bf.name)


def copy_fpga_logic(target_dir: Path):
    # T120 Logic (strictly open source SystemVerilog, excluding proprietary ip/)
    t120_target = target_dir / "T120F324"
    t120_target.mkdir(parents=True, exist_ok=True)
    t120_src = REPO_ROOT / "FPGA_code" / "T120F324"
    for item in t120_src.glob("*.sv*"):
        shutil.copy2(item, t120_target / item.name)
    for item in t120_src.glob("*.sdc"):
        shutil.copy2(item, t120_target / item.name)
    for item in t120_src.glob("*.xml"):
        shutil.copy2(item, t120_target / item.name)
    
    # Copy T120 target bitstream and hex
    bit_target = t120_target / "bitstreams"
    bit_target.mkdir(parents=True, exist_ok=True)
    for bf in [t120_src / "outflow" / "T120_MALM.bit", t120_src / "outflow" / "T120_MALM.hex"]:
        if bf.exists():
            shutil.copy2(bf, bit_target / bf.name)

    # T20 Logic (strictly open source SystemVerilog, excluding proprietary ip/)
    t20_target = target_dir / "T20F256"
    t20_target.mkdir(parents=True, exist_ok=True)
    t20_src = REPO_ROOT / "FPGA_code" / "T20_Custom"
    for item in t20_src.glob("*.sv*"):
        shutil.copy2(item, t20_target / item.name)
    for item in t20_src.glob("*.sdc"):
        shutil.copy2(item, t20_target / item.name)
    for item in t20_src.glob("*.xml"):
        shutil.copy2(item, t20_target / item.name)
    
    # Copy T20 target bitstream and hex
    t20_bit_target = t20_target / "bitstreams"
    t20_bit_target.mkdir(parents=True, exist_ok=True)
    for bf in [t20_src / "outflow" / "T20F256.bit", t20_src / "outflow" / "T20F256.hex"]:
        if bf.exists():
            shutil.copy2(bf, t20_bit_target / bf.name)


def copy_common_python(py_target: Path):
    py_target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO_ROOT / "gui" / "udp_client.py", py_target / "udp_client.py")
    shutil.copy2(REPO_ROOT / "FPGA_code" / "scripts" / "verify_and_guard_version.py", py_target / "verify_and_guard_version.py")
    shutil.copy2(REPO_ROOT / "FPGA_code" / "scripts" / "flash_soc.py", py_target / "flash_soc.py")


def create_release_1():
    print(f"[*] Packaging Release 1: {REL1_DIR.name}...")
    REL1_DIR.mkdir(parents=True, exist_ok=True)
    
    copy_c_firmware(REL1_DIR)
    copy_fpga_logic(REL1_DIR)
    
    py_target = REL1_DIR / "pc_python"
    copy_common_python(py_target)
    
    # Specific python scripts for 5.0ms pure run
    for s in ["run_and_report_5ms_pure.py", "generate_5ms_pure_short_report.py", "generate_mode_a_var5_comprehensive_report.py"]:
        shutil.copy2(REPO_ROOT / "FPGA_code" / "scripts" / s, py_target / s)
        
    # Dataset and Reports
    doc_target = REL1_DIR / "reports_and_logs"
    doc_target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO_ROOT / "FPGA_code" / "logs" / "mode_a_extended_training" / "mode_a_1000ep_5ms_pure_toeplitz_reg2048_lr0p02_swing40_var5_k1_1k_3p3k_ablation.json", doc_target / "dataset_1000ep_5ms_pure.json")
    shutil.copy2(REPO_ROOT / "FPGA_code" / "docs" / "INVERTED_MAML_CARD2_1000EP_5MS_PURE_TOEPLITZ_REG2048_LR0P02_SWING40_VAR5_K1_1K_3P3K_ABLATION_REPORT.pdf", doc_target / "INVERTED_MAML_CARD2_1000EP_5MS_PURE_TOEPLITZ_REG2048_LR0P02_SWING40_VAR5_K1_1K_3P3K_ABLATION_REPORT.pdf")
    shutil.copy2(REPO_ROOT / "FPGA_code" / "docs" / "INVERTED_MAML_CARD2_1K3P3K_ATTENUATOR_BREAKTHROUGH_SYNTHESIS.md", doc_target / "INVERTED_MAML_CARD2_1K3P3K_ATTENUATOR_BREAKTHROUGH_SYNTHESIS.md")

    # Generate Manifest README
    readme_content = f"""# Inverted MAML Release Package: Pure Spatial 5.0 ms Breakthrough
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
- **Primary Attenuator:** $1\\text{{ k}}\\Omega / 3.3\\text{{ k}}\\Omega$ ($-12.7\\text{{ dB}}$) on ColTIA virtual ground summing junction.
- **In-Data Drivers:** High-current `MCP664-E/SL` installed on DAC2 rows 1..6.
- **Operating Delay:** Fixed static snapshot at $t = 5000\\text{{ \\mu s}}$ ($5.0\\text{{ ms}}$).
- **Disturbance Protocol:** Patent SE 2630397-4 Fig 7 Emulator active (±5 LSB injected on M33 every 100 epochs).
"""
    with open(REL1_DIR / "README.md", "w") as f:
        f.write(readme_content)
    print(f"[+] Release 1 successfully created at: {REL1_DIR}")


def create_release_2():
    print(f"[*] Packaging Release 2: {REL2_DIR.name}...")
    REL2_DIR.mkdir(parents=True, exist_ok=True)
    
    copy_c_firmware(REL2_DIR)
    copy_fpga_logic(REL2_DIR)
    
    py_target = REL2_DIR / "pc_python"
    copy_common_python(py_target)
    
    # Specific python scripts for broadened window and Mode B cross-check
    for s in ["run_card2_broadened_11strata_k1_online.py",
              "generate_broadened_online_white_noise_comprehensive_report.py",
              "generate_mode_b_crosscheck_report_pdf.py"]:
        shutil.copy2(REPO_ROOT / "FPGA_code" / "scripts" / s, py_target / s)
        
    # Dataset and Reports
    doc_target = REL2_DIR / "reports_and_logs"
    doc_target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO_ROOT / "FPGA_code" / "logs" / "mode_a_extended_training" / "mode_a_1000ep_broadened_4500to5500us_white_reg2048_lr0p02_swing40_var5_k1_1k_3p3k_ablation.json", doc_target / "dataset_mode_a_1000ep_broadened_white.json")
    shutil.copy2(REPO_ROOT / "FPGA_code" / "logs" / "mode_a_extended_training" / "mode_b_1000ep_broadened_4500to5500us_white_reg2048_lr0p02_swing40_var5_k1_1k_3p3k_mode_b_control.json", doc_target / "dataset_mode_b_1000ep_crosscheck.json")
    shutil.copy2(REPO_ROOT / "FPGA_code" / "docs" / "INVERTED_MAML_CARD2_1000EP_BROADENED_WINDOW_WHITE_NOISE_COMPREHENSIVE_REPORT.pdf", doc_target / "INVERTED_MAML_CARD2_1000EP_BROADENED_WINDOW_WHITE_NOISE_COMPREHENSIVE_REPORT.pdf")
    shutil.copy2(REPO_ROOT / "FPGA_code" / "docs" / "INVERTED_MAML_CARD2_MODE_A_VS_MODE_B_CROSSCHECK_REPORT.pdf", doc_target / "INVERTED_MAML_CARD2_MODE_A_VS_MODE_B_CROSSCHECK_REPORT.pdf")
    shutil.copy2(REPO_ROOT / "FPGA_code" / "docs" / "INVERTED_MAML_CARD2_MODE_A_VS_MODE_B_CROSSCHECK_REPORT.md", doc_target / "INVERTED_MAML_CARD2_MODE_A_VS_MODE_B_CROSSCHECK_REPORT.md")

    # Generate Manifest README
    readme_content = f"""# Inverted MAML Release Package: Broadened Temporal Window [4.5..5.5 ms] White Noise & Mode B Cross-Check
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
"""
    with open(REL2_DIR / "README.md", "w") as f:
        f.write(readme_content)
    print(f"[+] Release 2 successfully created at: {REL2_DIR}")


if __name__ == "__main__":
    create_release_1()
    create_release_2()
    print("[SUCCESS] Both release packages created cleanly!")
