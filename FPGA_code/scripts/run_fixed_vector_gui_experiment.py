#!/usr/bin/env python3
"""
run_fixed_vector_gui_experiment.py
==================================
Runs Inverted MAML Mode A training on a SINGLE FIXED (LOCKED) VECTOR from scratch.
Logs in exact JSON format compatible with maml_post_analysis_gui.py.
Target: Efinix Trion T120 Master SoC (192.168.1.50:5000) on PCB v1.3.2.
"""

import sys
import time
import json
import math
import struct
import argparse
from pathlib import Path
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from gui.udp_client import (
    MamlUdpClient,
    MAML_CMD_STEP_OUTER,
    MAML_CMD_RAND_DATA,
)
from FPGA_code.scripts.run_mode_a_batch_training import get_averaged_telemetry

def main():
    parser = argparse.ArgumentParser(description="Mode A Training Experiment")
    parser.add_argument("--epochs", type=int, default=200, help="Number of total epochs (default: 200)")
    parser.add_argument("--baseline-epochs", type=int, default=40, help="Number of initial baseline epochs with training OFF (default: 40)")
    parser.add_argument("--lr", type=float, default=0.25, help="Learning rate for training phase (default: 0.25x)")
    parser.add_argument("--variable", action="store_true", default=True, help="Draw fresh random white-noise vector every epoch (default: True)")
    parser.add_argument("--fixed", action="store_true", help="Lock single fixed vector instead of variable vectors")
    parser.add_argument("--host", default="192.168.1.50")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--out", default="FPGA_code/logs/virtual_gain_experiments/fixed_vector_scratch_300ep.json")
    args = parser.parse_args()

    is_variable = not args.fixed
    out_file = Path(args.out)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    lr_inner_q16 = max(32, min(4096, int(round(1024 * args.lr))))
    mode_desc = "Variable Random Vectors (Continuous Rotating In-Data)" if is_variable else "Locked Vector (Single Deterministic Sample)"

    print("=" * 78)
    print("MODE A 2-LAYER TRAINING WITH STATISTICAL BASELINE (100% PURE SILICON)")
    print(f"Target: {args.host}:{args.port} | Mode: {mode_desc}")
    print(f"Phase 1: Baseline (Training OFF, LR=0.0) -> Epochs 0 .. {args.baseline_epochs}")
    print(f"Phase 2: Training (Active M3+M8, LR={args.lr:.2f}x) -> Epochs {args.baseline_epochs + 1} .. {args.epochs}")
    print(f"Log: {out_file}")
    print("=" * 78)

    client = MamlUdpClient(host=args.host, port=args.port, timeout=1.5)

    # 1. Reset gain experiment knobs to nominal 1/1 hardware baseline
    client.set_gain_experiment(d_line=1, w33=1, target_gain=1.0, clamp=120)
    time.sleep(0.05)

    # 2. Configure Mode A at nominal 5.0 ms settled delay
    client.set_config(
        mode=0, jumper_mode=3, led_switches=3, max_meas_win_pct=100, hadamard_khz=500,
        inner_loop_n=100, seed_pct=28, seed_mode=1, w_hid_mag=0, trim_hid_mag=0,
        hadamard_delay_us=5000, lr_inner_q16=lr_inner_q16
    )
    time.sleep(0.05)

    # 3. Center compensation weights to physical null baseline (W_null)
    print("[*] Centering compensation weights to physical null baseline (W_null)...")
    client.center_compensation_weights()
    time.sleep(0.05)

    # 4. Draw EXACTLY ONE fresh white-noise vector and permanently lock it (payload = 2)
    print("[*] Drawing single fresh white-noise vector and permanently locking it...")
    client._send_binary(MAML_CMD_RAND_DATA, struct.pack("<B", 2))
    time.sleep(0.05)

    # Read baseline telemetry (Epoch 0) with 50 Hz hum cancellation (4 frames = 40 ms = 2 full 50 Hz cycles)
    t0_dict = get_averaged_telemetry(client, n_avg=4)
    rec0 = {
        "epoch": 0,
        "phase": "BASELINE" if args.baseline_epochs > 0 else "TRAINING",
        "loss_lsb2": t0_dict["loss_lsb2"],
        "rmse_lsb": t0_dict["rmse_lsb"],
        "enob_bits": t0_dict["enob_bits"],
        "ref_x": list(t0_dict["x_ref"]),
        "x_ref": list(t0_dict["x_ref"]),
        "z_target": list(t0_dict["z_target"]),
        "adc45": list(t0_dict["adc45"]),
        "adc49": list(t0_dict["adc49"]),
        "err49": list(t0_dict["err49"]),
        "w_m3": t0_dict["w_m3"],
        "w_m8": t0_dict["w_m8"],
        "w_m33": t0_dict["w_m33"],
        "w8_diag": list(t0_dict["w8_diag"]),
        "w3_diag": list(t0_dict["w3_diag"]),
    }

    records = [rec0]

    print(f"  Initial Input X: {rec0['x_ref']}")
    print(f"  Target Z:        {rec0['z_target']}")
    print(f"  Initial Loss:    {rec0['loss_lsb2']:.1f} LSB² | RMSE: {rec0['rmse_lsb']:.2f} LSB | ENOB: {rec0['enob_bits']:.2f} bits")
    print(f"  Initial W8:      {rec0['w8_diag']}")
    print(f"  Initial W3:      {rec0['w3_diag']}")

    metadata = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "hardware": "PCB v1.3.2 (1k/5.1k Attenuator) + Efinix Trion T120 Master SoC",
        "condition": mode_desc,
        "training_params": {
            "k": 1,
            "strata": 1,
            "t_min_us": 5000,
            "t_max_us": 5000,
            "lr": args.lr,
            "lr_inner_q16": lr_inner_q16,
            "epochs": args.epochs,
            "baseline_epochs": args.baseline_epochs,
            "fixed_vector": not is_variable
        }
    }

    print("-" * 78)
    print(f"{'Ep #':<6} {'Phase':<7} | {'Loss (LSB²)':<12} | {'RMSE (LSB)':<11} | {'ENOB (b)':<10} | {'W8 Diag (Cols 0..5)':<25}")
    print("-" * 78)

    best_loss = rec0["loss_lsb2"]
    best_ep = 0
    best_enob = rec0["enob_bits"]

    baseline_losses = [rec0["loss_lsb2"]] if args.baseline_epochs > 0 else []
    baseline_rmses = [rec0["rmse_lsb"]] if args.baseline_epochs > 0 else []
    baseline_enobs = [rec0["enob_bits"]] if args.baseline_epochs > 0 else []

    for ep in range(1, args.epochs + 1):
        is_baseline = (ep <= args.baseline_epochs)
        current_phase = "BASELINE" if is_baseline else "TRAINING"

        if ep == args.baseline_epochs + 1 and args.baseline_epochs > 0:
            mean_b_rmse = float(np.mean(baseline_rmses))
            std_b_rmse = float(np.std(baseline_rmses))
            mean_b_enob = float(np.mean(baseline_enobs))
            mean_b_loss = float(np.mean(baseline_losses))
            print("=" * 78)
            print(f">>> [EPOCH {ep} SWITCHOVER]: TURNING ON 2-LAYER ADAPTATION (LR = {args.lr:.2f}x)")
            print(f">>> Untrained Baseline Statistics across {len(baseline_rmses)} arbitrary vectors:")
            print(f">>>   Mean Baseline RMSE: {mean_b_rmse:.2f} ± {std_b_rmse:.2f} LSB | Mean ENOB: {mean_b_enob:.2f} bits | Mean Loss: {mean_b_loss:.1f} LSB²")
            print("=" * 78)

        if is_variable:
            # Draw fresh random white-noise vector for this epoch
            client._send_binary(MAML_CMD_RAND_DATA, struct.pack("<B", 2))
            time.sleep(0.015)

        if not is_baseline:
            # Step inner loop on the vector ONLY during active training phase
            client._send_binary(MAML_CMD_STEP_OUTER)
            time.sleep(0.015)

        # Average 4 consecutive frames (40 ms = 2 full 50 Hz periods) for rock-solid cancellation
        t_dict = get_averaged_telemetry(client, n_avg=4)

        if is_baseline:
            baseline_losses.append(t_dict["loss_lsb2"])
            baseline_rmses.append(t_dict["rmse_lsb"])
            baseline_enobs.append(t_dict["enob_bits"])

        rec = {
            "epoch": ep,
            "phase": current_phase,
            "loss_lsb2": t_dict["loss_lsb2"],
            "rmse_lsb": t_dict["rmse_lsb"],
            "enob_bits": t_dict["enob_bits"],
            "ref_x": list(t_dict["x_ref"]),
            "x_ref": list(t_dict["x_ref"]),
            "z_target": list(t_dict["z_target"]),
            "adc45": list(t_dict["adc45"]),
            "adc49": list(t_dict["adc49"]),
            "err49": list(t_dict["err49"]),
            "w_m3": t_dict["w_m3"],
            "w_m8": t_dict["w_m8"],
            "w_m33": t_dict["w_m33"],
            "w8_diag": list(t_dict["w8_diag"]),
            "w3_diag": list(t_dict["w3_diag"]),
        }

        records.append(rec)

        if not is_baseline and t_dict["loss_lsb2"] < best_loss:
            best_loss = t_dict["loss_lsb2"]
            best_ep = ep
            best_enob = t_dict["enob_bits"]

        phase_tag = f"[{current_phase[:4]}]"
        if ep % 10 == 0 or ep <= 5 or ep == args.baseline_epochs or ep == args.baseline_epochs + 1 or ep == args.epochs:
            print(f"{ep:<4d} {phase_tag:<6s} | {rec['loss_lsb2']:<12.1f} | {rec['rmse_lsb']:<11.2f} | {rec['enob_bits']:<10.2f} | {rec['w8_diag']}")

        # Save to disk every single epoch so GUI updates dynamically
        with open(out_file, "w") as f:
            json.dump({
                "metadata": metadata,
                "static_weights": {
                    "w_m33": rec0["w_m33"],
                    "w_m3_start": rec0["w_m3"],
                    "w_m8_start": rec0["w_m8"],
                },
                "epochs": records,
                "records": records,
                "summary": {
                    "best_epoch": best_ep,
                    "best_loss": float(best_loss),
                    "best_enob": float(best_enob),
                    "latest_loss": float(t_dict["loss_lsb2"]),
                    "total_epochs": ep,
                    "baseline_epochs": args.baseline_epochs,
                    "mean_baseline_rmse": round(float(np.mean(baseline_rmses)), 2) if baseline_rmses else None,
                    "mean_baseline_enob": round(float(np.mean(baseline_enobs)), 2) if baseline_enobs else None,
                }
            }, f, indent=2)

    print("-" * 78)
    print(f"[+] Fixed-Vector Training Complete!")
    print(f"    Initial Loss: {rec0['loss_lsb2']:.1f} LSB² -> Best Loss: {best_loss:.1f} LSB² (Ep #{best_ep}, ENOB: {best_enob:.2f} bits)")
    drop_pct = ((rec0['loss_lsb2'] - best_loss) / rec0['loss_lsb2']) * 100.0
    print(f"    Monotonic Error Drop: {drop_pct:.1f}%")

if __name__ == "__main__":
    main()
