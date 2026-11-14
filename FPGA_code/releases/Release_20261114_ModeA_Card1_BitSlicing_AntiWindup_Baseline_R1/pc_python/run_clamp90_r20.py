#!/usr/bin/env python3
"""Run Round 20dc_fix: Replicate Clamp = 90 LSB multi-stage test on Card 1 physical silicon.

Schedule:
  - 60s Pre-cooldown (0% heat)
  - 2 Cold Baseline phases (30s ON, 30s OFF @ 0% heat)
  - 6 Warm 30% phases (30s each: 3 ON, 3 OFF @ 30% heat)
  - 6 Warm 40% phases (30s each: 3 ON, 3 OFF @ 40% heat)
  - Total Duration: 7.0 min active + 60s cooldown

Hyperparameters:
  - LR       = 0.055
  - L2       = 1920
  - Momentum = 0.85
  - Clamp    = 90 LSB
  - K-batch  = 1
  - Locked DC Cal = FPGA_code/config/r1_dc_cal_fixed.json
"""

import os
import subprocess
import sys
import time

PYTHON = "/home/olle/anaconda3/bin/python"
OUT_JSON = "/home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/logs/bit_slicing/opt_r20dc_fix_lr0p055_l2_1920_mom0p85_cl90.json"
DC_CAL = "FPGA_code/config/r1_dc_cal_fixed.json"

ALL_LOGS = [
    "FPGA_code/logs/bit_slicing/opt_r1dc_fix_lr0p03_l2_1024_mom0p90_cl75.json",
    "FPGA_code/logs/bit_slicing/opt_r2dc_fix_lr0p035_l2_1536_mom0p85_cl75.json",
    "FPGA_code/logs/bit_slicing/opt_r3dc_fix_lr0p02_l2_2560_mom0p80_cl70.json",
    "FPGA_code/logs/bit_slicing/opt_r4dc_fix_lr0p05_l2_1792_mom0p85_cl80.json",
    "FPGA_code/logs/bit_slicing/opt_r5dc_fix_lr0p055_l2_1792_mom0p85_cl85.json",
    "FPGA_code/logs/bit_slicing/opt_r6dc_fix_lr0p055_l2_1792_mom0p80_cl90.json",
    "FPGA_code/logs/bit_slicing/opt_r7dc_fix_lr0p055_l2_2048_mom0p85_cl75.json",
    "FPGA_code/logs/bit_slicing/opt_r7dc_fix_verify13m_lr0p055_l2_2048_mom0p85_cl75.json",
    "FPGA_code/logs/bit_slicing/opt_r10dc_fix_lr0p055_l2_1920_mom0p85_cl75.json",
    "FPGA_code/logs/bit_slicing/opt_r11dc_fix_lr0p055_l2_1920_mom0p85_cl78.json",
    "FPGA_code/logs/bit_slicing/opt_r12dc_fix_lr0p055_l2_1920_mom0p85_cl80.json",
    "FPGA_code/logs/bit_slicing/opt_r13dc_fix_lr0p055_l2_1920_mom0p85_cl82.json",
    "FPGA_code/logs/bit_slicing/opt_r14dc_fix_lr0p055_l2_1920_mom0p85_cl85.json",
    "FPGA_code/logs/bit_slicing/opt_r15dc_fix_lr0p055_l2_1920_mom0p85_cl90.json",
    "FPGA_code/logs/bit_slicing/opt_r16dc_fix_lr0p055_l2_1920_mom0p85_cl100.json",
    "FPGA_code/logs/bit_slicing/opt_r17dc_fix_lr0p055_l2_1920_mom0p85_cl90.json",
    "FPGA_code/logs/bit_slicing/opt_r18dc_fix_lr0p055_l2_1920_mom0p85_cl90.json",
    "FPGA_code/logs/bit_slicing/opt_r19dc_fix_lr0p055_l2_1920_mom0p85_cl90.json",
    OUT_JSON,
]

def run_cmd(cmd, desc):
    print("=" * 80)
    print(f"[*] {desc}")
    print(f"    CMD: {' '.join(cmd)}")
    print("=" * 80)
    t0 = time.time()
    res = subprocess.run(cmd)
    dt = time.time() - t0
    if res.returncode != 0:
        print(f"[!] FAILED with exit code {res.returncode} in {dt:.1f}s")
        sys.exit(res.returncode)
    print(f"[+] Completed in {dt:.1f}s (exit 0)")

def main():
    print("=" * 80)
    print(" INVERTED MAML CARD 1: RUNNING ROUND 20dc_fix")
    print(" Schedule: 2 Cold (30s) + 6 Warm 30% (30s) + 6 Warm 40% (30s)")
    print(" Baseline: LR=0.055, L2=1920, Mom=0.85, K=1, Clamp=90, Locked 25°C DC Cal")
    print("=" * 80)

    # 1. Run physical silicon experiment
    test_cmd = [
        PYTHON, "FPGA_code/scripts/run_card1_extended_thermal_sweep.py",
        "--cold-duration-sec", "30",
        "--phase-duration-sec", "30",
        "--stage1-phases", "6",
        "--stage1-duty-pct", "30",
        "--stage2-phases", "6",
        "--stage2-duty-pct", "40",
        "--cooldown-sec", "60",
        "--k-batch", "1",
        "--lr", "0.055",
        "--l2-reg", "1920",
        "--momentum", "0.85",
        "--clamp", "90",
        "--load-dc-calib", DC_CAL,
        "--out-json", OUT_JSON,
    ]
    run_cmd(test_cmd, "Running Physical Silicon Test: Round 20dc_fix (30% 6 cyc + 40% 6 cyc)")

    # 2. Generate concise R20 report
    report_cmd = [
        PYTHON, "FPGA_code/scripts/generate_card1_run_concise_report.py",
        "--round", "20",
        "--json", OUT_JSON,
        "--all-logs", *ALL_LOGS,
    ]
    run_cmd(report_cmd, "Generating 180-Weight Concise Report for Round 20dc_fix")

    # 3. Model comparison
    model_cmd = [
        PYTHON, "FPGA_code/scripts/analog_hyperparam_model.py",
        "--select-best",
        "--logs", *ALL_LOGS,
        "--out-json", "FPGA_code/logs/bit_slicing/opt_r20_selection.json",
    ]
    run_cmd(model_cmd, "Updating Hyperparameter Optimization Model")

    # 4. Compile comprehensive report
    comp_cmd = [
        PYTHON, "FPGA_code/scripts/compile_card1_bit_slicing_fhp_comprehensive_report_pdf.py",
        "--primary-log", OUT_JSON,
        "--all-logs", *ALL_LOGS,
        "--proposal-json", "FPGA_code/logs/bit_slicing/opt_r20_selection.json",
    ]
    run_cmd(comp_cmd, "Compiling Refreshed FHP Comprehensive Report")

    print("\n[+] Round 20dc_fix completed cleanly!")

if __name__ == "__main__":
    main()
