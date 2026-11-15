#!/usr/bin/env python3
"""
Autonomous 10-Round Optimization Campaign for Inverted MAML Card 1 (SE 2630397-4).
Explores the Clamp=78..85 LSB sweep requested by user (R10..R13) and fine-tuning (R14..R18).
Executes with K=1, Locked 25°C DC Cal, generates 2-page reports with all 180 weights,
and waits with git commit as instructed by the user.
"""

import sys
import os
import subprocess
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PYTHON_EXE = "/home/olle/anaconda3/bin/python"
LOGS_DIR = REPO_ROOT / "FPGA_code" / "logs" / "bit_slicing"
DOCS_DIR = REPO_ROOT / "FPGA_code" / "docs"
REL_RPT_DIR = REPO_ROOT / "FPGA_code" / "releases" / "Release_20261114_ModeA_Card1_BitSlicing_AntiWindup_Baseline_R1" / "reports_and_logs"
ARTIFACT_DIR = Path("/home/olle/.gemini/antigravity/brain/fa59cd2e-8c8b-41e2-add0-77ffdf2fe431")

BASE_LOGS = [
    str(LOGS_DIR / "opt_r1dc_fix_lr0p03_l2_1024_mom0p90_cl75.json"),
    str(LOGS_DIR / "opt_r2dc_fix_lr0p035_l2_1536_mom0p85_cl75.json"),
    str(LOGS_DIR / "opt_r3dc_fix_lr0p02_l2_2560_mom0p80_cl70.json"),
    str(LOGS_DIR / "opt_r4dc_fix_lr0p05_l2_1792_mom0p85_cl80.json"),
    str(LOGS_DIR / "opt_r5dc_fix_lr0p055_l2_1792_mom0p85_cl85.json"),
    str(LOGS_DIR / "opt_r6dc_fix_lr0p055_l2_1792_mom0p80_cl90.json"),
    str(LOGS_DIR / "opt_r7dc_fix_lr0p055_l2_2048_mom0p85_cl75.json"),
    str(LOGS_DIR / "opt_r7dc_fix_verify13m_lr0p055_l2_2048_mom0p85_cl75.json"),
    str(LOGS_DIR / "opt_r9dc_fix_lr0p055_l2_1920_mom0p85_cl75.json"),
]

# User requested Clamp Sweep:
# R10: Clamp = 78 LSB
# R11: Clamp = 80 LSB
# R12: Clamp = 82 LSB
# R13: Clamp = 85 LSB
# Followed by testing the top clamps on L2=2048 and fine tuning
ROUNDS_CONFIG = [
    # Round 10: Clamp = 78 LSB on L2=1920
    {"round": 10, "lr": 0.055, "l2": 1920, "mom": 0.85, "clamp": 78, "desc": "Clamp=78 LSB sweep (L2=1920)"},
    # Round 11: Clamp = 80 LSB on L2=1920
    {"round": 11, "lr": 0.055, "l2": 1920, "mom": 0.85, "clamp": 80, "desc": "Clamp=80 LSB sweep (L2=1920)"},
    # Round 12: Clamp = 82 LSB on L2=1920
    {"round": 12, "lr": 0.055, "l2": 1920, "mom": 0.85, "clamp": 82, "desc": "Clamp=82 LSB sweep (L2=1920)"},
    # Round 13: Clamp = 85 LSB on L2=1920
    {"round": 13, "lr": 0.055, "l2": 1920, "mom": 0.85, "clamp": 85, "desc": "Clamp=85 LSB sweep (L2=1920)"},
    # Round 14: Clamp = 78 LSB on L2=2048
    {"round": 14, "lr": 0.055, "l2": 2048, "mom": 0.85, "clamp": 78, "desc": "Clamp=78 LSB on L2=2048"},
    # Round 15: Clamp = 80 LSB on L2=2048
    {"round": 15, "lr": 0.055, "l2": 2048, "mom": 0.85, "clamp": 80, "desc": "Clamp=80 LSB on L2=2048"},
    # Round 16: Clamp = 82 LSB on L2=2048
    {"round": 16, "lr": 0.055, "l2": 2048, "mom": 0.85, "clamp": 82, "desc": "Clamp=82 LSB on L2=2048"},
    # Round 17: Clamp = 85 LSB on L2=2048
    {"round": 17, "lr": 0.055, "l2": 2048, "mom": 0.85, "clamp": 85, "desc": "Clamp=85 LSB on L2=2048"},
    # Round 18: Fine LR tuning on the leading clamp
    {"round": 18, "lr": 0.052, "l2": 1920, "mom": 0.85, "clamp": 80, "desc": "Fine LR=0.052 on Clamp=80 LSB"},
]


def run_command(cmd, desc):
    print(f"\n{'='*80}\n[*] {desc}\n    CMD: {' '.join(cmd)}\n{'='*80}")
    t0 = time.time()
    res = subprocess.run(cmd, cwd=str(REPO_ROOT))
    elapsed = time.time() - t0
    if res.returncode != 0:
        print(f"[!] FAILED with exit code {res.returncode} after {elapsed:.1f}s")
        sys.exit(res.returncode)
    print(f"[+] Completed in {elapsed:.1f}s (exit 0)")


def main():
    accumulated_logs = [p for p in BASE_LOGS if Path(p).exists()]

    print("=" * 80)
    print(" INVERTED MAML CARD 1: SYSTEMATIC CLAMP SWEEP CAMPAIGN (R10..R18)")
    print(" User-Requested Focus: Clamp = 78 -> 80 -> 82 -> 85 LSB (K=1, Locked 25°C DC Cal)")
    print("=" * 80)

    for idx, cfg in enumerate(ROUNDS_CONFIG, start=1):
        rnd = cfg["round"]
        lr = cfg["lr"]
        l2 = cfg["l2"]
        mom = cfg["mom"]
        clamp = cfg["clamp"]
        desc = cfg["desc"]

        lr_str = f"{lr:.4g}".replace(".", "p")
        mom_str = f"{mom:.2f}".replace(".", "p")
        out_json_name = f"opt_r{rnd}dc_fix_lr{lr_str}_l2_{l2}_mom{mom_str}_cl{clamp}.json"
        out_json_path = LOGS_DIR / out_json_name

        print(f"\n>>> STARTING CAMPAIGN STEP {idx}/{len(ROUNDS_CONFIG)}: Round {rnd}dc_fix ({desc}) <<<")
        print(f"    Params: LR={lr}, L2={l2}, Mom={mom}, Clamp={clamp}, K=1, Locked DC Cal")
        print(f"    Target Log: {out_json_path}")

        # Check if already completed
        if out_json_path.exists() and out_json_path.stat().st_size > 10000:
            print(f"[+] {out_json_path} already exists. Skipping execution.")
        else:
            # 1. Run physical silicon thermal bit-slicing experiment (5.5 min)
            run_cmd = [
                PYTHON_EXE,
                "FPGA_code/scripts/run_card1_thermal_bit_slicing.py",
                "--cooldown-sec", "60",
                "--cold-phase-duration", "0.25",
                "--phase-duration", "1.0",
                "--warm-phases", "4",
                "--cool-phases", "0",
                "--heater-duty-pct", "40",
                "--k-batch", "1",
                "--lr", str(lr),
                "--l2-reg", str(l2),
                "--momentum", str(mom),
                "--clamp", str(clamp),
                "--load-dc-calib", "FPGA_code/config/r1_dc_cal_fixed.json",
                "--out-json", str(out_json_path),
            ]
            run_command(run_cmd, f"Executing Hardware Run: Round {rnd}dc_fix ({desc})")

        # Add to accumulated logs
        if str(out_json_path) not in accumulated_logs:
            accumulated_logs.append(str(out_json_path))

        # 2. Generate 2-page concise report with all 180 weights
        rep_cmd = [
            PYTHON_EXE,
            "FPGA_code/scripts/generate_card1_run_concise_report.py",
            "--round", str(rnd),
            "--json", str(out_json_path),
            "--all-logs", *accumulated_logs,
        ]
        run_command(rep_cmd, f"Generating 180-Weight Concise Report for Round {rnd}dc_fix")

        # 3. Copy reports and figures to release directory and artifacts directory
        slug_lower = f"r{rnd}dc_fix_lr{lr_str}_l2_{l2}_mom{mom_str}_cl{clamp}"
        slug_upper = f"R{rnd}DC_FIX_LR{lr_str.upper()}_L2_{l2}_MOM{mom_str.upper()}_CL{clamp}"
        pdf_name = f"INVERTED_MAML_CARD1_{slug_upper}_THERMAL_SLICING_REPORT.pdf"
        md_name = f"INVERTED_MAML_CARD1_{slug_upper}_THERMAL_SLICING_REPORT.md"
        fig_ts = f"fig_card1_{slug_lower}_thermal_slicing.png"
        fig_w = f"fig_card1_{slug_lower}_w8_w3_all_weights.png"

        for f_name in [pdf_name, md_name]:
            src = DOCS_DIR / f_name
            if src.exists():
                subprocess.run(["cp", "-f", str(src), str(REL_RPT_DIR / f_name)])
                subprocess.run(["cp", "-f", str(src), str(ARTIFACT_DIR / f_name)])

        for f_fig in [fig_ts, fig_w]:
            src = DOCS_DIR / "figures" / f_fig
            if src.exists():
                subprocess.run(["cp", "-f", str(src), str(REL_RPT_DIR / "figures" / f_fig)])
                subprocess.run(["cp", "-f", str(src), str(ARTIFACT_DIR / f_fig)])

        print(f"[+] Round {rnd}dc_fix reports and figures synced.")

    print("\n" + "=" * 80)
    print(" ALL ROUNDS COMPLETED SUCCESSFULLY ON SILICON!")
    print(" Evaluating final champion and refreshing Comprehensive FHP Report...")
    print("=" * 80)

    # 4. Evaluate all runs with ML model
    sel_cmd = [
        PYTHON_EXE,
        "FPGA_code/scripts/analog_hyperparam_model.py",
        "--logs", *accumulated_logs,
        "--select-best",
        "--out-json", str(LOGS_DIR / "opt_campaign_selection.json"),
    ]
    run_command(sel_cmd, "Selecting Global Champion Across All Runs")

    # 5. Refresh FHP Comprehensive Report
    comp_cmd = [
        PYTHON_EXE,
        "FPGA_code/scripts/compile_card1_bit_slicing_fhp_comprehensive_report_pdf.py",
        "--primary-log", str(accumulated_logs[-1]),
        "--all-logs", *accumulated_logs,
        "--proposal-json", str(LOGS_DIR / "opt_campaign_selection.json"),
    ]
    run_command(comp_cmd, "Compiling FHP Comprehensive Report")

    print("\n[+] Campaign fully finished! No Git commit was made (waiting as instructed).")


if __name__ == "__main__":
    main()
