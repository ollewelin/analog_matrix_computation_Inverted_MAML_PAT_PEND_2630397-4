#!/usr/bin/env python3
"""
run_mode_b_uncomp_campaign.py
Inverted MAML (Patent Pending SE 2630397-4) - Open Science Hardware

Executes a full 10-run campaign (100 epochs per run = 1,000 epochs total)
in MODE B on physical silicon (Trion T120 Master SoC @ 192.168.1.50).

Strict Experimental Constraints:
  1. Jumpers physically placed in MODE B (compensation loop disconnected).
  2. STRICTLY UNCHANGED input data swing (PRNG range [-45, +45], d_line=1).
  3. STRICTLY FROZEN Primary Payload Matrix W33 (k_default_m33, w33=1).
  4. Quiescent DC baseline offset calibrated per column to match summing junction in Mode B.
  5. Consistent ENOB calculation (both standard 11.0 - log2(RMSE) and IEEE formulas).
"""

import argparse
import json
import struct
import sys
import time
from pathlib import Path
from typing import Dict, List, Any

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from gui.udp_client import (
    MamlUdpClient,
    MamlTelemetry,
    MAML_CMD_RAND_DATA,
)
from FPGA_code.scripts.verify_and_guard_version import ensure_version_guard

LOG_DIR = REPO_ROOT / "FPGA_code" / "logs" / "mode_b_uncompensated_campaign"
DOCS_DIR = REPO_ROOT / "FPGA_code" / "docs"
FIGURES_DIR = DOCS_DIR / "figures"

LOG_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

FROZEN_W33_EXPECTED = [
    [+76, -20, +28,  -4, +44, -36],
    [-20, +84, -12, +44,  -4, +36],
    [+36,  -4, +80, -16, +32,  -4],
    [ -4, +40,  -8, +72, -12, +44],
    [+44, -12, +28, -12, +76,  -8],
    [-28, +32,  -4, +40,  -8, +82],
]


def get_averaged_telemetry(client: MamlUdpClient, n_avg: int = 4) -> MamlTelemetry:
    t_list = []
    for _ in range(n_avg):
        t = client.get_telemetry()
        if t is not None:
            t_list.append(t)
        time.sleep(0.005)
    if not t_list:
        raise RuntimeError("Failed to read telemetry from hardware!")
    last_t = t_list[-1]
    last_t.adc45_sig = np.mean([t.adc45_sig for t in t_list], axis=0).round().astype(int).tolist()
    last_t.adc49_sig = np.mean([t.adc49_sig for t in t_list], axis=0).round().astype(int).tolist()
    last_t.z_target = np.mean([t.z_target for t in t_list], axis=0).round().astype(int).tolist()
    last_t.ref_x = np.mean([t.ref_x for t in t_list], axis=0).round().astype(int).tolist()
    return last_t


def measure_mode_b_baseline(client: MamlUdpClient, w_m33: np.ndarray, samples: int = 30):
    """Calibrate physical DC baseline offset and column post-gain."""
    cal_x, cal_y = [], []
    for _ in range(samples):
        client._send_binary(MAML_CMD_RAND_DATA, struct.pack("<B", 2))
        time.sleep(0.015)
        t = get_averaged_telemetry(client, n_avg=4)
        cal_x.append(t.ref_x)
        cal_y.append(t.adc49_sig)

    cal_X = np.array(cal_x, dtype=np.float64)
    cal_Y = np.array(cal_y, dtype=np.float64)
    cal_dot = cal_X @ w_m33

    dc_opt = np.mean(cal_Y - cal_dot * (8.0 / 256.0), axis=0)

    col_slopes = []
    col_intercepts = []
    for c in range(6):
        p = np.polyfit(cal_dot[:, c], cal_Y[:, c], 1)
        col_slopes.append(float(p[0]))
        col_intercepts.append(float(p[1]))

    return dc_opt, np.array(col_slopes), np.array(col_intercepts)


def run_campaign(total_runs: int = 10, epochs_per_run: int = 100):
    print("=" * 80)
    print("MODE B (STANDALONE M33) 10-RUN BENCHMARK CAMPAIGN (10x100 = 1,000 EPOCHS)")
    print("Constraints: Strictly Unchanged Input Swing & Strictly Frozen W33")
    print("Hardware: PCB v1.3.2 | Jumpers in Mode B | T120 SoC @ 192.168.1.50:5000")
    print("=" * 80)

    ver_info = ensure_version_guard(host="192.168.1.50", port=5000)
    client = MamlUdpClient(host="192.168.1.50", port=5000, timeout=1.5)

    client.set_gain_experiment(d_line=1, w33=1, target_gain=1.0, clamp=120)
    time.sleep(0.03)

    client.set_config(
        mode=0, jumper_mode=1, led_switches=2, max_meas_win_pct=100, hadamard_khz=500,
        inner_loop_n=100, seed_pct=0, seed_mode=0, w_hid_mag=0, trim_hid_mag=0,
        hadamard_delay_us=5000, lr_inner_q16=256
    )
    time.sleep(0.05)

    # Initial check of w_m33
    t_init = get_averaged_telemetry(client, n_avg=4)
    w_m33 = np.array(t_init.w_m33, dtype=np.float64)
    assert np.array_equal(w_m33, np.array(FROZEN_W33_EXPECTED)), f"W33 mismatch! Got:\n{w_m33}"
    print("[+] Verified Frozen W33 matches k_default_m33 exactly.")

    # Measure initial baseline
    print("[*] Performing Mode B baseline calibration...")
    dc_opt, col_slopes, col_intercepts = measure_mode_b_baseline(client, w_m33, samples=30)
    print(f"[*] Baseline DC Offsets: {np.round(dc_opt, 1)}")
    print(f"[*] Calibrated Slopes:   {np.round(col_slopes, 4)}")

    all_runs_summary = []

    for run_idx in range(1, total_runs + 1):
        run_name = f"run_{run_idx:02d}"
        out_json = LOG_DIR / f"m33_mode_b_100ep_{run_name}.json"

        print("\n" + "=" * 80)
        print(f"STARTING MODE B RUN [{run_idx:02d}/{total_runs:02d}] : {run_name} (100 Epochs)")
        print("-" * 80)

        run_records = []
        for ep in range(1, epochs_per_run + 1):
            client._send_binary(MAML_CMD_RAND_DATA, struct.pack("<B", 2))
            time.sleep(0.015)

            t = get_averaged_telemetry(client, n_avg=4)
            y = np.array(t.adc49_sig, dtype=np.float64)
            x = np.array(t.ref_x, dtype=np.float64)
            dot = x @ w_m33

            z_opt = dc_opt + dot * (8.0 / 256.0)
            err_opt = y - z_opt
            mse_opt = float(np.mean(err_opt ** 2))
            rmse_opt = float(np.sqrt(mse_opt))
            enob_std = max(0.0, float(11.0 - np.log2(max(rmse_opt, 1e-9))))
            enob_ieee = max(0.0, float(np.log2(4096.0 / max(rmse_opt, 1e-9)) - 1.76))

            # Post-gain calibrated
            z_pg = col_intercepts + dot * col_slopes
            err_pg = y - z_pg
            mse_pg = float(np.mean(err_pg ** 2))
            rmse_pg = float(np.sqrt(mse_pg))
            enob_pg_std = max(0.0, float(11.0 - np.log2(max(rmse_pg, 1e-9))))

            rec = {
                "epoch": ep,
                "x_ref": [int(v) for v in t.ref_x],
                "adc49": [int(v) for v in t.adc49_sig],
                "adc45": [int(v) for v in t.adc45_sig],
                "z_opt": [round(float(v), 2) for v in z_opt],
                "err_opt": [round(float(v), 2) for v in err_opt],
                "loss_lsb2": mse_opt,
                "rmse_lsb": rmse_opt,
                "enob_std_bits": enob_std,
                "enob_ieee_bits": enob_ieee,
                "loss_pg_lsb2": mse_pg,
                "rmse_pg_lsb": rmse_pg,
                "enob_pg_std_bits": enob_pg_std,
            }
            run_records.append(rec)

            if ep % 20 == 0 or ep == 1:
                print(f"  Ep {ep:<4} | Loss: {mse_opt:<9.1f} LSB² | RMSE: {rmse_opt:<6.2f} LSB | ENOB std: {enob_std:<4.2f} b | IEEE: {enob_ieee:<4.2f} b")

        run_losses = [r["loss_lsb2"] for r in run_records]
        run_enobs_std = [r["enob_std_bits"] for r in run_records]
        run_enobs_ieee = [r["enob_ieee_bits"] for r in run_records]

        run_summary = {
            "run_index": run_idx,
            "run_name": run_name,
            "epochs": epochs_per_run,
            "mean_loss_lsb2": float(np.mean(run_losses)),
            "std_loss_lsb2": float(np.std(run_losses)),
            "best_loss_lsb2": float(np.min(run_losses)),
            "mean_enob_std_bits": float(np.mean(run_enobs_std)),
            "std_enob_std_bits": float(np.std(run_enobs_std)),
            "best_enob_std_bits": float(np.max(run_enobs_std)),
            "mean_enob_ieee_bits": float(np.mean(run_enobs_ieee)),
            "best_enob_ieee_bits": float(np.max(run_enobs_ieee)),
        }
        all_runs_summary.append(run_summary)

        run_doc = {
            "provenance": {
                "title": f"Mode B Standalone M33 Verification Run {run_idx:02d}",
                "run_name": run_name,
                "date": time.strftime("%Y-%m-%d %H:%M:%S"),
                "hardware_setup": "Physical Jumpers in MODE B",
                "input_swing": "[-45, +45] (d_line=1)",
                "weight_matrix": "k_default_m33 (frozen, w33=1)",
                "calibrated_dc_offsets": [float(v) for v in dc_opt],
                "calibrated_column_slopes": [float(v) for v in col_slopes],
                "calibrated_column_intercepts": [float(v) for v in col_intercepts],
            },
            "summary": run_summary,
            "epochs": run_records,
        }

        with open(out_json, "w") as f:
            json.dump(run_doc, f, indent=2)
        print(f"[+] Saved {out_json}")

    campaign_summary_file = LOG_DIR / "mode_b_10runs_summary.json"
    with open(campaign_summary_file, "w") as f:
        json.dump({
            "campaign": "Mode B 10-Run Benchmark",
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "runs": all_runs_summary,
            "overall_mean_loss": float(np.mean([s["mean_loss_lsb2"] for s in all_runs_summary])),
            "overall_mean_enob_std": float(np.mean([s["mean_enob_std_bits"] for s in all_runs_summary])),
            "overall_mean_enob_ieee": float(np.mean([s["mean_enob_ieee_bits"] for s in all_runs_summary])),
            "overall_best_enob_std": float(np.max([s["best_enob_std_bits"] for s in all_runs_summary])),
        }, f, indent=2)

    print("\n" + "=" * 80)
    print("MODE B 10-RUN CAMPAIGN COMPLETED SUCCESSFULLY!")
    print(f"Overall Mean Loss : {np.mean([s['mean_loss_lsb2'] for s in all_runs_summary]):.1f} LSB²")
    print(f"Overall Mean ENOB : {np.mean([s['mean_enob_std_bits'] for s in all_runs_summary]):.2f} bits (Standard)")
    print(f"                  : {np.mean([s['mean_enob_ieee_bits'] for s in all_runs_summary]):.2f} bits (IEEE)")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=10, help="Total runs")
    parser.add_argument("--epochs", type=int, default=100, help="Epochs per run")
    args = parser.parse_args()
    run_campaign(total_runs=args.runs, epochs_per_run=args.epochs)
