#!/usr/bin/env python3
"""run_demo.py
==============
Inverted MAML (Patent Pending SE 2630397-4) - Open Science Hardware

One-Click Live Hardware Demo & Report Generator for Card 1:
1. Runs the 14-phase thermal stress & analog bit-slicing test on physical silicon:
   - 2 Cold Baseline phases (0% heat)
   - 6 Warm 30% PWM phases (3 ON / 3 OFF)
   - 6 Warm 40% PWM phases (3 ON / 3 OFF)
   - Optimal Locked Settings: Clamp = ±90 LSB, LR = 0.055, L2 = 1920, Mom = 0.85, K = 1
2. Automatically generates the publication-quality PDF report and high-res PNG plots.
3. Prints direct clickable links to the results in the terminal.

Usage:
  python FPGA_code/scripts/run_demo.py
  python FPGA_code/scripts/run_demo.py --phase-sec 15   # Faster 3.5-min quick demo
"""

from __future__ import annotations
import sys
import os
import time
import argparse
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PYTHON = sys.executable or "/home/olle/anaconda3/bin/python"
DC_CAL = str(REPO_ROOT / "FPGA_code" / "config" / "r1_dc_cal_fixed.json")


def run_cmd(cmd: list[str], desc: str) -> None:
    print("=" * 80)
    print(f"[*] {desc}")
    print(f"    CMD: {' '.join(cmd)}")
    print("=" * 80)
    t0 = time.time()
    res = subprocess.run(cmd)
    dt = time.time() - t0
    if res.returncode != 0:
        print(f"\n[!] FAILED with exit code {res.returncode} after {dt:.1f}s")
        sys.exit(res.returncode)
    print(f"[+] Completed in {dt:.1f}s (exit 0)\n")


def main():
    parser = argparse.ArgumentParser(description="Inverted MAML Live Silicon Demo Runner")
    parser.add_argument("--phase-sec", type=float, default=30.0, help="Duration of each phase in seconds (default 30.0s)")
    parser.add_argument("--cooldown-sec", type=float, default=30.0, help="Forced cooldown before test in seconds (default 30.0s)")
    parser.add_argument("--clamp", type=int, default=90, help="Hardware weight clamp in LSB (default 90)")
    parser.add_argument("--lr", type=float, default=0.055, help="Learning rate (default 0.055)")
    parser.add_argument("--l2-reg", type=int, default=1920, help="L2 regularization (default 1920)")
    parser.add_argument("--momentum", type=float, default=0.85, help="SGD momentum (default 0.85)")
    parser.add_argument("--tag", type=str, default="demo", help="Identifier tag for log/report files (default 'demo')")
    args = parser.parse_args()

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    out_json = str(REPO_ROOT / "FPGA_code" / "logs" / "bit_slicing" / f"card1_{args.tag}_{timestamp}_cl{args.clamp}.json")

    total_active_sec = 14 * args.phase_sec
    print("=" * 80)
    print(f" INVERTED MAML: LIVE SILICON HARDWARE DEMO (Card 1)")
    print(f" Profile: 2 Cold ({args.phase_sec:.0f}s) + 6 Warm 30% ({args.phase_sec:.0f}s) + 6 Warm 40% ({args.phase_sec:.0f}s)")
    print(f" Active Duration: {total_active_sec/60:.1f} min ({total_active_sec:.0f}s) + {args.cooldown_sec:.0f}s Cooldown")
    print(f" Parameters: Clamp = ±{args.clamp} LSB, LR = {args.lr}, L2 = {args.l2_reg}, Mom = {args.momentum}, K = 1")
    print(f" Target JSON: {out_json}")
    print("=" * 80)

    # 1. Run silicon test
    test_cmd = [
        PYTHON, str(REPO_ROOT / "FPGA_code" / "scripts" / "run_card1_extended_thermal_sweep.py"),
        "--cold-duration-sec", str(args.phase_sec),
        "--phase-duration-sec", str(args.phase_sec),
        "--stage1-phases", "6",
        "--stage1-duty-pct", "30",
        "--stage2-phases", "6",
        "--stage2-duty-pct", "40",
        "--cooldown-sec", str(args.cooldown_sec),
        "--k-batch", "1",
        "--lr", str(args.lr),
        "--l2-reg", str(args.l2_reg),
        "--momentum", str(args.momentum),
        "--clamp", str(args.clamp),
        "--load-dc-calib", DC_CAL,
        "--out-json", out_json,
    ]
    run_cmd(test_cmd, "Step 1/2: Running Physical Silicon Demo Test")

    # 2. Generate report & figures
    report_cmd = [
        PYTHON, str(REPO_ROOT / "FPGA_code" / "scripts" / "generate_card1_run_concise_report.py"),
        "--round", "20",
        "--json", out_json,
    ]
    run_cmd(report_cmd, "Step 2/2: Generating Publication PDF Report & Figures")

    pdf_path = str(REPO_ROOT / "FPGA_code" / "docs" / f"INVERTED_MAML_CARD1_R20_LR{str(args.lr).replace('.', 'P')}_L2_{args.l2_reg}_MOM{str(args.momentum).replace('.', 'P')}_CL{args.clamp}_THERMAL_SLICING_REPORT.pdf")
    fig_timeline = str(REPO_ROOT / "FPGA_code" / "docs" / "figures" / f"fig_card1_r20_lr{str(args.lr).replace('.', 'p')}_l2_{args.l2_reg}_mom{str(args.momentum).replace('.', 'p')}_cl{args.clamp}_thermal_slicing.png")
    fig_weights = str(REPO_ROOT / "FPGA_code" / "docs" / "figures" / f"fig_card1_r20_lr{str(args.lr).replace('.', 'p')}_l2_{args.l2_reg}_mom{str(args.momentum).replace('.', 'p')}_cl{args.clamp}_w8_w3_all_weights.png")

    print("\n" + "=" * 80)
    print(" DEMO COMPLETED SUCCESSFULLY!")
    print(" Generated Artifacts:")
    print(f"   [PDF Report] : file://{pdf_path}")
    print(f"   [Timeline]   : file://{fig_timeline}")
    print(f"   [All Weights]: file://{fig_weights}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
