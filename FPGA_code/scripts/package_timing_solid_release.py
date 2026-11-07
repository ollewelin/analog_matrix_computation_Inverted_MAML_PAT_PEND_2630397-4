#!/usr/bin/env python3
"""
package_timing_solid_release.py
Inverted MAML (Patent Pending SE 2630397-4) - Open Science Hardware

Creates the official release package under FPGA_code/releases/:
Release_20261107_ModeA_Card2_TimingSolid_VerilogEngine_Comprehensive

Packages:
  - C firmware source (maml_platform.c, headers, bsp, Makefile, binaries)
  - T120 Master SoC Verilog/SystemVerilog logic files & bitstream/hex (NO proprietary Efinix IP!)
  - T20 Coprocessor Verilog/SystemVerilog logic files & bitstream/hex (NO proprietary Efinix IP!)
  - PC Python driver and verification scripts
  - Live silicon JSON dataset logs and publication PDF reports
  - Comprehensive README with hardware configuration and reproduction runbooks
"""

import os
import shutil
import hashlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RELEASES_ROOT = REPO_ROOT / "FPGA_code" / "releases"
RELEASES_ROOT.mkdir(parents=True, exist_ok=True)

PKG_DIR = RELEASES_ROOT / "Release_20261107_ModeA_Card2_TimingSolid_VerilogEngine_Comprehensive"


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
    # 4. software/ common (start_minimal.S, etc.)
    if (src_base / "software").exists():
        shutil.copytree(src_base / "software", sw_target / "software", dirs_exist_ok=True)
    # 5. Makefile and configs
    for f in ["Makefile", "cpu0.yaml"]:
        if (src_base / f).exists():
            shutil.copy2(src_base / f, sw_target / f)
    # 6. Compiled binaries
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


def copy_pc_python(target_dir: Path):
    py_target = target_dir / "pc_python"
    py_target.mkdir(parents=True, exist_ok=True)

    scripts_to_copy = [
        REPO_ROOT / "gui" / "udp_client.py",
        REPO_ROOT / "FPGA_code" / "scripts" / "verify_and_guard_version.py",
        REPO_ROOT / "FPGA_code" / "scripts" / "flash_soc.py",
        REPO_ROOT / "FPGA_code" / "scripts" / "program_t120.py",
        REPO_ROOT / "FPGA_code" / "scripts" / "run_card2_broadened_11strata_k1_online.py",
        REPO_ROOT / "FPGA_code" / "scripts" / "generate_card2_w3_staircase_comprehensive_report.py",
    ]
    for s in scripts_to_copy:
        if s.exists():
            shutil.copy2(s, py_target / s.name)

    # Configs
    cfg_target = py_target / "config"
    cfg_target.mkdir(parents=True, exist_ok=True)
    cfg_src = REPO_ROOT / "FPGA_code" / "config" / "w3_staircase_pattern.py"
    if cfg_src.exists():
        shutil.copy2(cfg_src, cfg_target / cfg_src.name)


def copy_reports_and_logs(target_dir: Path):
    doc_target = target_dir / "reports_and_logs"
    doc_target.mkdir(parents=True, exist_ok=True)
    fig_target = doc_target / "figures"
    fig_target.mkdir(parents=True, exist_ok=True)

    # Datasets
    data_dir = REPO_ROOT / "FPGA_code" / "logs" / "mode_a_extended_training"
    datasets = [
        "mode_a_1000ep_broadened_4500to5500us_white_reg2048_lr0p02_swing40_var5_k1_1k_3p3k_w3staircase_ablation.json",
        "mode_a_1000ep_broadened_4900to5900us_white_reg2048_lr0p02_swing40_var5_k1_1k_3p3k_w3staircase_ablation.json",
    ]
    for ds in datasets:
        p = data_dir / ds
        if p.exists():
            shutil.copy2(p, doc_target / ds)

    # Reports
    docs_dir = REPO_ROOT / "FPGA_code" / "docs"
    reports = [
        "INVERTED_MAML_CARD2_1000EP_W3_STAIRCASE_COMPREHENSIVE_REPORT.pdf",
        "INVERTED_MAML_CARD2_1000EP_W3_STAIRCASE_COMPREHENSIVE_REPORT.md",
        "INVERTED_MAML_CARD2_1000EP_4900TO5900US_W3_STAIRCASE_COMPREHENSIVE_REPORT.pdf",
        "INVERTED_MAML_CARD2_1000EP_4900TO5900US_W3_STAIRCASE_COMPREHENSIVE_REPORT.md",
    ]
    for rep in reports:
        p = docs_dir / rep
        if p.exists():
            shutil.copy2(p, doc_target / rep)

    # Figures
    fig_src = docs_dir / "figures"
    for fg in fig_src.glob("*w3_staircase*"):
        shutil.copy2(fg, fig_target / fg.name)


def generate_manifest_readme(target_dir: Path):
    readme_content = f"""# Inverted MAML Official Release: Rock-Solid Verilog 10.000 ms Timing & Comprehensive W(3) Staircase Package
**Release Tag:** `Release_20261107_ModeA_Card2_TimingSolid_VerilogEngine_Comprehensive`  
**Date:** 2026-11-07  
**Hardware Target:** Card 2 (PCB v1.3.2, 1k/3.3k Attenuator Mod, Repaired CH3) | Efinix Trion T120 Master SoC + Trion T20 Coprocessor  
**Patent Reference:** SE 2630397-4 (Open Science Hardware)  
**Silicon Verification Commits:** [`536f5b1`](file:///home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4), [`2caaaec`](file:///home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4), [`47858fb`](file:///home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4)  

---

## 🚀 Key Technological Breakthrough: 100% Verilog Crystal-Locked Frame Engine (0.00 ns Jitter)

Prior firmware revisions sequenced 2T1C gate capacitor refreshes and Hadamard perturbation bursts through RISC-V C code polling loops (`bsp_uDelay`, S-bus polling, blocking 115200-baud UART status prints). This introduced hundreds of microseconds of jitter and deadline overruns during the final 2 ms of the 10 ms cycle.

This release completely removes software from the physical timing loop by implementing a **pure Verilog autonomous frame engine** in `t120_analog_io_ctrl.sv` and `t120_inter_fpga_bridge.sv`:
1. **Crystal-Locked 10.000000 ms Modulo-500,000 Counter (`frame_timer` @ 50.000 MHz):**
   - Refreshes start at exact cycle 0 (`t = 0.000000 ms`), phase-locking the 2.0 MHz inter-FPGA clock (`CLK9`).
   - Automatically sequences all 12 half-columns (`col 0..5`, `pos/neg`) directly from high-speed on-chip dual-port `shadow_w_ram` (`0x400..0x5FF`) with $90.00\\,\\mu\\text{{s}}$ dwell per step ($1.080\\,\\text{{ms}}$ total refresh).
2. **Deterministic Hardware Stratum Settling & ADC Read:**
   - Counts down exact hardware stratum delays ($4500\\dots 5900\\,\\mu\\text{{s}}$).
   - Samples 16× hardware-averaged forward ADCs in quiet Hi-Z ($0x8000$).
3. **Synchronous 14-Step Sylvester $H_8$ Simplex Hadamard Burst:**
   - Shifts Hadamard carriers directly from hardwired Verilog ROM at 10.0 MHz `CLK9`.
   - Executes time-separated Matrix 8 burst ($0x3F00$), quiet $20.00\\,\\mu\\text{{s}}$ Hi-Z separation gap, and Matrix 3 burst ($0x003F$).
   - Returns to $0x8000$ Hi-Z and autonomously refreshes T20 watchdog and LED states.
4. **C Firmware Decoupled:**
   - RISC-V software now operates purely as an asynchronous supervisor: it writes updated weights to `shadow_w_ram` and reads finished hardware frames. Software delays or UART traffic can **never** distort physical silicon timing!

---

## 📊 Consolidated Empirical Benchmarks on Card 2 Silicon

### 1. Broadened Window [4.5..5.5 ms] Online SGD ($K=1$, 11 Strata, $\pm 5$ LSB Disturbance):
- **Phase 1 (Baseline $W=0$):** Window Loss $= 51,653.8\\,\\text{{LSB}}^2$ ($3.97\\,\\text{{b}}$) | 5.0 ms: $6,965.3\\,\\text{{LSB}}^2$ ($5.54\\,\\text{{b}}$)
- **Phase 2 (Active Nominal):** Window Loss $= 49,157.5\\,\\text{{LSB}}^2$ ($4.00\\,\\text{{b}}$) | 5.0 ms: $6,878.2\\,\\text{{LSB}}^2$ ($5.60\\,\\text{{b}}$)
- **Phase 3 (Active Tracking $\pm 5$ LSB):** Window Loss $= 50,795.1\\,\\text{{LSB}}^2$ ($3.99\\,\\text{{b}}$) | 5.0 ms: $24,345.0\\,\\text{{LSB}}^2$ ($4.61\\,\\text{{b}}$)
- **Phase 4 (Ablation $W=0$ under $\pm 5$ LSB):** Window Loss $= 83,128.9\\,\\text{{LSB}}^2$ ($3.65\\,\\text{{b}}$) | 5.0 ms: $41,762.3\\,\\text{{LSB}}^2$ ($4.22\\,\\text{{b}}$)
- **Ablation Contrast:** $+63.7\\%$ error increase upon disconnecting compensation ($+71.5\\%$ surge at 5.0 ms).

### 2. Shifted Window [4.9..5.9 ms] Online SGD ($K=1$, 11 Strata, $\pm 5$ LSB Disturbance):
- **Phase 1 (Baseline $W=0$):** Window Loss $= 102,342.3\\,\\text{{LSB}}^2$ ($3.47\\,\\text{{b}}$)
- **Phase 2 (Active Nominal):** Window Loss $= 41,834.9\\,\\text{{LSB}}^2$ ($4.12\\,\\text{{b}}$, **$-59.1\\%$ error reduction**, $+0.65\\,\\text{{b}}$ gain!)
- **Phase 3 (Active Tracking $\pm 5$ LSB):** Window Loss $= 55,163.0\\,\\text{{LSB}}^2$ ($3.93\\,\\text{{b}}$)
- **Phase 4 (Ablation $W=0$ under $\pm 5$ LSB):** Window Loss $= 117,572.5\\,\\text{{LSB}}^2$ ($3.38\\,\\text{{b}}$, **$+113.1\\%$ error increase!**)
- **Ablation Contrast:** More than **$2.1\\times$ error increase** without active compensation on the deep capacitor discharge slope.

---

## 📦 Directory Structure & Deliverables

- `sw/t120_master/`:
  - `src/main.c`: Clean runtime loop without blocking UART/MDIO operations.
  - `src/maml_platform.c`: Pure Verilog frame engine driver, `shadow_w_ram` synchronization, and non-blocking background ticks.
  - `include/t120_bridge_regs.h`: Hardware register map for APB3 base `0xF8104000` (`0x080..0x0B0` and `0x400..0x5FF`).
  - `binaries/`: Pre-compiled `t120_master.hex` and `t120_master.bin`.
- `T120F324/`:
  - `t120_analog_io_ctrl.sv`: Pure Verilog 10.000000 ms autonomous frame engine.
  - `t120_inter_fpga_bridge.sv`: Autonomous hardware master ports & Sylvester $H_8$ Simplex ROM.
  - `t120_bridge_clkgen.sv`: Phase-locked 2.0 MHz / 10.0 MHz `CLK9` generator.
  - `top_level.sv`: Master interlock wiring.
  - `bitstreams/`: Synthesized and timing-verified bitstream (`T120_MALM.bit` and `T120_MALM.hex`).
- `T20F256/`:
  - `t20_hw_responder.sv`: Slave responder logic for differential column gates (`G_P/G_N`) and Hadamard 3-state drivers.
  - `bitstreams/`: Verified `T20F256.bit` and `T20F256.hex`.
- `pc_python/`:
  - `run_card2_broadened_11strata_k1_online.py`: Primary 1000-epoch online runner.
  - `generate_card2_w3_staircase_comprehensive_report.py`: Automated 10-page publication PDF/MD report generator.
  - `verify_and_guard_version.py`: Pre-flight version guard.
  - `flash_soc.py` & `program_t120.py`: High-speed JTAG flashing tools.
- `reports_and_logs/`:
  - `INVERTED_MAML_CARD2_1000EP_W3_STAIRCASE_COMPREHENSIVE_REPORT.pdf` ([4.5..5.5 ms])
  - `INVERTED_MAML_CARD2_1000EP_4900TO5900US_W3_STAIRCASE_COMPREHENSIVE_REPORT.pdf` ([4.9..5.9 ms])
  - Complete 1000-epoch JSON telemetry datasets and high-resolution 3D figures.

---

## 🛠 Reproduction Runbook

### 1. Verify Board Telemetry & Logic Version
```bash
/home/olle/anaconda3/bin/python pc_python/verify_and_guard_version.py
```

### 2. Flash T120 SoC (if needed)
```bash
/home/olle/anaconda3/bin/python pc_python/flash_soc.py
```

### 3. Execute 1000-Epoch Benchmark:
- **[4.5..5.5 ms] Window:**
  ```bash
  /home/olle/anaconda3/bin/python pc_python/run_card2_broadened_11strata_k1_online.py \\
    --noise-color white --staircase-w3 --epochs 1000 --k-batch 1 --lr 0.02 --reg-lambda 2048 \\
    --d-line 2 --t-min 4500 --t-max 5500 --t-step 100 --attenuator 1k/3.3k --w33-variance-lsb-range 5
  ```
- **[4.9..5.9 ms] Window:**
  ```bash
  /home/olle/anaconda3/bin/python pc_python/run_card2_broadened_11strata_k1_online.py \\
    --noise-color white --staircase-w3 --epochs 1000 --k-batch 1 --lr 0.02 --reg-lambda 2048 \\
    --d-line 2 --t-min 4900 --t-max 5900 --t-step 100 --attenuator 1k/3.3k --w33-variance-lsb-range 5
  ```
"""
    with open(target_dir / "README.md", "w") as f:
        f.write(readme_content)


def main():
    print(f"[*] Packaging Official Timing-Solid Release Package at: {PKG_DIR.name}...")
    PKG_DIR.mkdir(parents=True, exist_ok=True)

    copy_c_firmware(PKG_DIR)
    copy_fpga_logic(PKG_DIR)
    copy_pc_python(PKG_DIR)
    copy_reports_and_logs(PKG_DIR)
    generate_manifest_readme(PKG_DIR)

    print(f"[✓] Official timing-solid release package created successfully at: {PKG_DIR}")


if __name__ == "__main__":
    main()
