#!/usr/bin/env python3
"""
run_3stage_baseline_experiment.py
=================================
Runs a 3-stage 500-epoch Inverted MAML Mode A experiment on pure physical silicon:
  - Stage 1: Epochs 0..99   -> Baseline 0 (W3=0, W8=0), Training OFF (LR = 0)
  - Stage 2: Epochs 100..199 -> Baseline Knee (W3=±16, W8=±16), Training OFF (LR = 0)
  - Stage 3: Epochs 200..500 -> Active Adaptation ON (M3 + M8, LR = 0.25x)
  - Arbitrary continuously rotating random white-noise vectors every epoch.
  - Zero digital seeding (seed_pct = 0, letting natural silicon noise and bias operate).
  - LED output ON throughout the experiment.
"""

import sys
import time
import json
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

MAML_CMD_CENTER_WEIGHTS = 0x15
from FPGA_code.scripts.run_mode_a_batch_training import get_averaged_telemetry

SCRATCH_JSON = REPO_ROOT / "FPGA_code" / "logs" / "virtual_gain_experiments" / "fixed_vector_scratch_300ep.json"
OUT_DEFAULT = REPO_ROOT / "FPGA_code" / "logs" / "virtual_gain_experiments" / "m3_m8_3stage_500ep_run.json"


def main():
    parser = argparse.ArgumentParser(description="3-Stage 500-Epoch Mode A Silicon Experiment")
    parser.add_argument("--epochs", type=int, default=500, help="Total epochs (default 500)")
    parser.add_argument("--stage2-ep", type=int, default=100, help="Epoch to switch to knee baseline (default 100)")
    parser.add_argument("--train-ep", type=int, default=200, help="Epoch to turn ON active training (default 200)")
    parser.add_argument("--lr", type=float, default=0.25, help="Learning rate for Phase 3 (default 0.25x)")
    parser.add_argument("--host", default="192.168.1.50")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--out", default=str(OUT_DEFAULT))
    args = parser.parse_args()

    out_file = Path(args.out)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    SCRATCH_JSON.parent.mkdir(parents=True, exist_ok=True)

    lr_inner_q16 = max(32, min(4096, int(round(1024 * args.lr))))

    print("=" * 80)
    print("INVERTED MAML MODE A: 3-STAGE 500-EPOCH BENCHMARK (100% PURE SILICON)")
    print(f"Target: {args.host}:{args.port} | Total Epochs: {args.epochs}")
    print(f"  Stage 1: Ep 0 .. {args.stage2_ep - 1:<3d} -> BASELINE 0 (W=0 LSB, Training OFF, LR=0)")
    print(f"  Stage 2: Ep {args.stage2_ep} .. {args.train_ep - 1:<3d} -> BASELINE KNEE (W=±16 LSB, Training OFF, LR=0)")
    print(f"  Stage 3: Ep {args.train_ep} .. {args.epochs:<3d} -> ACTIVE TRAINING ON (LR = {args.lr:.2f}x)")
    print(f"Knobs: Zero digital seed (seed_pct=0), LEDs ON, continuous rotating arbitrary vectors")
    print(f"Log: {out_file}")
    print("=" * 80)

    client = MamlUdpClient(host=args.host, port=args.port, timeout=1.5)

    # 1. Reset gain knobs: nominal 1/1 hardware baseline, clamp=120
    client.set_gain_experiment(d_line=1, w33=1, target_gain=1.0, clamp=120)
    time.sleep(0.04)

    # 2. Configure Mode A with LEDs ON (led_switches=3), seed_pct=0 (NO SEED), delay=5000 us
    client.set_config(
        mode=0, jumper_mode=3, led_switches=3, max_meas_win_pct=100, hadamard_khz=500,
        inner_loop_n=100, seed_pct=0, seed_mode=0, w_hid_mag=0, trim_hid_mag=0,
        hadamard_delay_us=5000, lr_inner_q16=lr_inner_q16
    )
    time.sleep(0.04)

    # Also explicitly pulse LEDs ON
    client._send_binary(0x13, struct.pack("<BB", 1, 1))
    time.sleep(0.02)

    # 3. Stage 1 Init: Center compensation weights to ZERO BASELINE (payload = 0)
    print("[*] Stage 1 Init: Setting Baseline 0 on M3 and M8 (W = 0 LSB)...")
    client._send_binary(MAML_CMD_CENTER_WEIGHTS, struct.pack("<B", 0))
    time.sleep(0.05)

    # Draw fresh random vector
    client._send_binary(MAML_CMD_RAND_DATA, struct.pack("<B", 2))
    time.sleep(0.04)

    t0 = get_averaged_telemetry(client, n_avg=4)
    rec0 = {
        "epoch": 0,
        "phase": "BASELINE_ZERO",
        "loss_lsb2": t0["loss_lsb2"],
        "rmse_lsb": t0["rmse_lsb"],
        "enob_bits": t0["enob_bits"],
        "ref_x": list(t0["x_ref"]),
        "x_ref": list(t0["x_ref"]),
        "z_target": list(t0["z_target"]),
        "adc45": list(t0["adc45"]),
        "adc49": list(t0["adc49"]),
        "err49": list(t0["err49"]),
        "w_m3": t0["w_m3"],
        "w_m8": t0["w_m8"],
        "w_m33": t0["w_m33"],
        "w8_diag": list(t0["w8_diag"]),
        "w3_diag": list(t0["w3_diag"]),
    }
    records = [rec0]

    print(f"  Ep 0 [BASE 0]: Loss={t0['loss_lsb2']:.1f} LSB² | RMSE={t0['rmse_lsb']:.2f} LSB | ENOB={t0['enob_bits']:.2f} b | W8={t0['w8_diag']}")

    best_loss = t0["loss_lsb2"]
    best_ep = 0
    best_enob = t0["enob_bits"]

    print("-" * 80)
    print(f"{'Ep #':<6} {'Phase':<14} | {'Loss (LSB²)':<12} | {'RMSE (LSB)':<11} | {'ENOB (b)':<10} | {'W8 Diag (Cols 0..5)':<25}")
    print("-" * 80)

    for ep in range(1, args.epochs + 1):
        # Stage determination
        if ep < args.stage2_ep:
            phase = "BASELINE_ZERO"
        elif ep < args.train_ep:
            phase = "BASELINE_KNEE"
        else:
            phase = "TRAINING"

        # Stage switchovers
        if ep == args.stage2_ep:
            print("=" * 80)
            print(f">>> [EPOCH {ep} SWITCHOVER]: SMACKING ON OPTIMAL S-CURVE KNEE BASELINE (±16 LSB) ON M3 & M8! (LR = 0)")
            print("=" * 80)
            client._send_binary(MAML_CMD_CENTER_WEIGHTS, struct.pack("<B", 1))
            time.sleep(0.04)

        if ep == args.train_ep:
            print("=" * 80)
            print(f">>> [EPOCH {ep} SWITCHOVER]: TURNING ACTIVE TRAINING ON! (LR = {args.lr:.2f}x)")
            print("=" * 80)

        # Draw fresh arbitrary random white-noise vector every epoch
        client._send_binary(MAML_CMD_RAND_DATA, struct.pack("<B", 2))
        time.sleep(0.015)

        # In Stage 3 only: active step
        if phase == "TRAINING":
            client._send_binary(MAML_CMD_STEP_OUTER)
            time.sleep(0.015)

        t_dict = get_averaged_telemetry(client, n_avg=4)

        if phase == "TRAINING" and t_dict["loss_lsb2"] < best_loss:
            best_loss = t_dict["loss_lsb2"]
            best_ep = ep
            best_enob = t_dict["enob_bits"]

        rec = {
            "epoch": ep,
            "phase": phase,
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

        if ep % 20 == 0 or ep in (args.stage2_ep, args.train_ep, args.epochs):
            print(f"{ep:<6d} [{phase:<12s}] | {t_dict['loss_lsb2']:<12.1f} | {t_dict['rmse_lsb']:<11.2f} | {t_dict['enob_bits']:<10.2f} | {t_dict['w8_diag']}")

        # Mirror live to scratch JSON for real-time GUI animation
        if ep % 5 == 0 or ep == args.epochs:
            try:
                with open(SCRATCH_JSON, "w") as sf:
                    json.dump({
                        "metadata": {
                            "training_params": {
                                "epochs": args.epochs,
                                "baseline_epochs": args.train_ep,
                                "stage2_epochs": args.stage2_ep,
                                "lr": args.lr
                            },
                            "title": "Inverted MAML: 3-Stage 500-Epoch Experiment (Pure Silicon)"
                        },
                        "summary": {
                            "baseline_epochs": args.train_ep,
                            "stage2_epochs": args.stage2_ep,
                            "best_epoch": best_ep,
                            "best_loss": float(best_loss),
                            "best_enob": float(best_enob)
                        },
                        "epochs": records,
                        "records": records
                    }, sf, indent=2)
            except Exception:
                pass

    # Save final dataset
    with open(out_file, "w") as f:
        json.dump({
            "metadata": {
                "hardware": "PCB v1.3.2 (1k/5.1k Attenuator) + Efinix Trion T120 Master SoC",
                "target": f"{args.host}:{args.port}",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "total_epochs": args.epochs,
                "stage1_zero_baseline": [0, args.stage2_ep - 1],
                "stage2_knee_baseline": [args.stage2_ep, args.train_ep - 1],
                "stage3_training": [args.train_ep, args.epochs],
                "lr": args.lr
            },
            "summary": {
                "baseline_epochs": args.train_ep,
                "best_epoch": best_ep,
                "best_loss": float(best_loss),
                "best_enob": float(best_enob)
            },
            "records": records
        }, f, indent=2)

    print("\n[+] 3-Stage Experiment Complete!")
    print(f"    Saved: {out_file}")
    print(f"    Best Training Loss: {best_loss:.1f} LSB² @ Ep {best_ep} (ENOB: {best_enob:.2f} b)")


if __name__ == "__main__":
    main()
