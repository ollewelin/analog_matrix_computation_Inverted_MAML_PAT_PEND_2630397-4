#!/usr/bin/env python3
"""
Dedicated Clamp Sweep Campaign (R10..R13) on Inverted MAML Card 1 (SE 2630397-4).
Requested by user:
  R10: Clamp = 78 LSB
  R11: Clamp = 80 LSB
  R12: Clamp = 82 LSB
  R13: Clamp = 85 LSB
Baseline parameters: LR=0.055, L2=1920 (Alternativ A), Mom=0.85, K=1, Locked 25°C DC Cal.
Generates 2-page reports with all 180 weights per round.
Waits with Git commit as instructed.
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
]

SWEEP_ROUNDS = [
    {"round": 10, "clamp": 78, "lr": 0.055, "l2": 1920, "mom": 0.85, "desc": "Clamp = 78 LSB"},
    {"round": 11, "clamp": 80, "lr": 0.055, "l2": 1920, "mom": 0.85, "desc": "Clamp = 80 LSB"},
    {"round": 12, "clamp": 82, "lr": 0.055, "l2": 1920, "mom": 0.85, "desc": "Clamp = 82 LSB"},
    {"round": 13, "clamp": 85, "lr": 0.055, "l2": 1920, "mom": 0.85, "desc": "Clamp = 85 LSB"},
]


def run_command(cmd, desc):
    print(f"\n{'='*80}\n[*] {desc}\n    CMD: {' '.join(cmd)}\n{'='*80}", flush=True)
    t0 = time.time()
    res = subprocess.run(cmd, cwd=str(REPO_ROOT))
    elapsed = time.time() - t0
    if res.returncode != 0:
        print(f"[!] FAILED with exit code {res.returncode} after {elapsed:.1f}s", flush=True)
        sys.exit(res.returncode)
    print(f"[+] Completed in {elapsed:.1f}s (exit 0)", flush=True)


def main():
    accumulated_logs = [p for p in BASE_LOGS if Path(p).exists()]

    print("=" * 80, flush=True)
    print(" INVERTED MAML CARD 1: USER-REQUESTED CLAMP SWEEP (R10..R13)", flush=True)
    print(" Testing Clamp = 78 -> 80 -> 82 -> 85 LSB", flush=True)
    print(" Baseline: LR=0.055, L2=1920 (Alternativ A), Mom=0.85, K=1, Locked 25°C DC Cal", flush=True)
    print("=" * 80, flush=True)

    for idx, cfg in enumerate(SWEEP_ROUNDS, start=1):
        rnd = cfg["round"]
        clamp = cfg["clamp"]
        lr = cfg["lr"]
        l2 = cfg["l2"]
        mom = cfg["mom"]
        desc = cfg["desc"]

        lr_str = f"{lr:.4g}".replace(".", "p")
        mom_str = f"{mom:.2f}".replace(".", "p")
        out_json_name = f"opt_r{rnd}dc_fix_lr{lr_str}_l2_{l2}_mom{mom_str}_cl{clamp}.json"
        out_json_path = LOGS_DIR / out_json_name

        print(f"\n>>> [CLAMP SWEEP {idx}/4] STARTING ROUND {rnd}dc_fix: {desc} <<<", flush=True)
        print(f"    Parameters: Clamp=±{clamp} LSB, LR={lr}, L2={l2}, Mom={mom}, K=1", flush=True)
        print(f"    Log File  : {out_json_path}", flush=True)

        # 1. Run physical silicon thermal experiment
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
        run_command(run_cmd, f"Running Physical Silicon Test: Round {rnd}dc_fix ({desc})")

        # Add to accumulated logs
        if str(out_json_path) not in accumulated_logs:
            accumulated_logs.append(str(out_json_path))

        # 2. Generate 2-page report with all 180 weights
        rep_cmd = [
            PYTHON_EXE,
            "FPGA_code/scripts/generate_card1_run_concise_report.py",
            "--round", str(rnd),
            "--json", str(out_json_path),
            "--all-logs", *accumulated_logs,
        ]
        run_command(rep_cmd, f"Generating 180-Weight Concise Report for Round {rnd}dc_fix ({desc})")

        # 3. Copy reports and figures
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

        print(f"[+] Round {rnd}dc_fix ({desc}) completed and reports synced.", flush=True)

    print("\n" + "=" * 80, flush=True)
    print(" ALL 4 CLAMP SWEEP ROUNDS (R10..R13) COMPLETED SUCCESSFULLY ON SILICON!", flush=True)
    print(" Comparing Clamp 75 vs 78 vs 80 vs 82 vs 85...", flush=True)
    print("=" * 80, flush=True)

    # 4. Evaluate with ML model
    sel_cmd = [
        PYTHON_EXE,
        "FPGA_code/scripts/analog_hyperparam_model.py",
        "--logs", *accumulated_logs,
        "--select-best",
        "--out-json", str(LOGS_DIR / "opt_clamp_sweep_r10_r13_selection.json"),
    ]
    run_command(sel_cmd, "Evaluating Clamp Sweep vs R7 Champion")

    # 5. Refresh FHP Comprehensive Report
    comp_cmd = [
        PYTHON_EXE,
        "FPGA_code/scripts/compile_card1_bit_slicing_fhp_comprehensive_report_pdf.py",
        "--primary-log", str(accumulated_logs[-1]),
        "--all-logs", *accumulated_logs,
        "--proposal-json", str(LOGS_DIR / "opt_clamp_sweep_r10_r13_selection.json"),
    ]
    run_command(comp_cmd, "Compiling Refreshed FHP Comprehensive Report")

    print("\n[+] Clamp sweep finished cleanly! No Git commit was made (waiting as instructed).", flush=True)


if __name__ == "__main__":
    main()
