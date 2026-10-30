#!/usr/bin/env python3
"""
run_10runs_1000ep_regularization_campaign.py
Inverted MAML (Patent Pending SE 2630397-4) - Open Science Hardware

10-Run 1000-Epoch Dynamic Baseline Regularization Campaign on Physical Silicon:
- Target: Trion T120 Master SoC (192.168.1.50:5000) on PCB v1.3.2 (1k / 5.1k Ohm summing attenuator)
- 10 Independent Runs (run_01 .. run_10) with continuous rotating arbitrary vectors
- 1000 Epochs per run:
    Stage 1: Ep 0 .. 99    -> Baseline 0 (W = 0 LSB, Training OFF, LR = 0)
    Stage 2: Ep 100 .. 199 -> Knee Baseline (W = ±16 LSB, Training OFF, LR = 0)
    Stage 3: Ep 200 .. 499 -> Active Training ON (LR = 0.25x), Regularization ON (lambda = 512)
    Stage 4: Ep 500 .. 799 -> Active Training ON (LR = 0.25x), Regularization OFF (lambda = 0)
    Stage 5: Ep 800 .. 1000-> Active Training ON (LR = 0.25x), Regularization ON (lambda = 512)
- Zero digital seeding (seed_pct = 0, pure physical silicon thermal/channel noise)
- Snapshot delay strictly locked to t = 5.0 ms
- LEDs ON (led_switches = 3)
- Automatically verifies and guards FPGA HW/SW version at start via verify_and_guard_version.py!
"""

import os
import sys
import time
import json
import struct
import argparse
from pathlib import Path
from typing import List, Dict, Any
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from gui.udp_client import (
    MamlUdpClient,
    MAML_CMD_CENTER_WEIGHTS,
    MAML_CMD_RAND_DATA,
    MAML_CMD_STEP_OUTER,
    MAML_CMD_SET_REG,
)
from FPGA_code.scripts.verify_and_guard_version import ensure_version_guard

LOG_DIR = REPO_ROOT / "FPGA_code" / "logs" / "baseline_regularization_campaign"


def get_averaged_telemetry(client: MamlUdpClient, n_avg: int = 4) -> dict:
    """Read and average n_avg consecutive telemetry frames from physical silicon."""
    t_list = []
    for _ in range(n_avg):
        t = client.get_telemetry()
        if t is not None:
            t_list.append(t)
        time.sleep(0.005)

    if not t_list:
        raise RuntimeError("Failed to receive telemetry from T120 hardware.")

    adc45_arr = np.mean([t.adc45_sig for t in t_list], axis=0)
    adc49_arr = np.mean([t.adc49_sig for t in t_list], axis=0)
    z_target_arr = np.mean([t.z_target for t in t_list], axis=0)
    x_ref_arr = np.mean([t.x_ref for t in t_list], axis=0)

    err49 = adc49_arr - z_target_arr
    mse_loss = float(np.mean(err49 ** 2))
    rmse = float(np.sqrt(mse_loss))
    fs = 4096.0
    enob = float((np.log2(fs / (rmse + 1e-9)) - 1.76) / 6.02 * 6.02)
    if enob < 0:
        enob = 0.0

    last_t = t_list[-1]
    w8_diag = [int(last_t.w_m8[c][c]) for c in range(min(6, len(last_t.w_m8)))]
    w3_diag = [int(last_t.w_m3[c][c]) for c in range(min(6, len(last_t.w_m3)))]

    return {
        "loss_lsb2": mse_loss,
        "rmse_lsb": rmse,
        "enob_bits": enob,
        "adc45": adc45_arr.tolist(),
        "adc49": adc49_arr.tolist(),
        "z_target": z_target_arr.tolist(),
        "x_ref": x_ref_arr.tolist(),
        "err49": err49.tolist(),
        "w_m3": [[int(val) for val in row] for row in last_t.w_m3],
        "w_m8": [[int(val) for val in row] for row in last_t.w_m8],
        "w_m33": [[int(val) for val in row] for row in last_t.w_m33],
        "w8_diag": w8_diag,
        "w3_diag": w3_diag,
        "reg_lambda_q16": int(last_t.reg_lambda_q16),
    }


def execute_single_run(
    client: MamlUdpClient,
    run_idx: int,
    total_runs: int,
    epochs: int,
    lr: float,
    reg_lambda: int,
    ver_info: dict,
) -> Path:
    """Execute a single 1000-epoch benchmark run on pure physical silicon."""
    run_str = f"run_{run_idx:02d}"
    out_file = LOG_DIR / f"m3_m8_1000ep_{run_str}.json"

    print("\n" + "=" * 80)
    print(f"STARTING EXPERIMENTAL RUN [{run_idx:02d}/{total_runs:02d}] : {run_str}")
    print(f"Total Epochs: {epochs} | LR = {lr:.2f}x | Reg Lambda = {reg_lambda} (Q0.16)")
    print(f"Hardware Summing Attenuator: 1k / 5.1k Ohm (PCB v1.3.2)")
    print(f"Saving to: {out_file}")
    print("=" * 80)

    lr_inner_q16 = max(32, min(4096, int(round(1024 * lr))))

    # 1. Reset gain knobs
    client.set_gain_experiment(d_line=1, w33=1, target_gain=1.0, clamp=120)
    time.sleep(0.03)

    # 2. Configure Mode A: LEDs ON (led_switches=3), seed_pct=0, 5000 us delay
    client.set_config(
        mode=0, jumper_mode=3, led_switches=3, max_meas_win_pct=100, hadamard_khz=500,
        inner_loop_n=100, seed_pct=0, seed_mode=0, w_hid_mag=0, trim_hid_mag=0,
        hadamard_delay_us=5000, lr_inner_q16=lr_inner_q16
    )
    time.sleep(0.03)

    # Explicitly turn LEDs ON
    client._send_binary(0x13, struct.pack("<BB", 1, 1))
    time.sleep(0.02)

    # 3. Stage 1 Init: Set Baseline 0 (W = 0 LSB)
    print("[*] Stage 1 Init: Centering weights to Baseline 0 (W = 0 LSB)...")
    client._send_binary(MAML_CMD_CENTER_WEIGHTS, struct.pack("<B", 0))
    client._send_binary(MAML_CMD_SET_REG, struct.pack("<H", 0))
    time.sleep(0.05)

    # Draw fresh random vector
    client._send_binary(MAML_CMD_RAND_DATA, struct.pack("<B", 2))
    time.sleep(0.03)

    t0 = get_averaged_telemetry(client, n_avg=4)
    rec0 = {
        "epoch": 0,
        "phase": "BASELINE_ZERO",
        "reg_lambda_q16": 0,
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

    print(f"  Ep   0 [BASE 0   ]: Loss={t0['loss_lsb2']:.1f} LSB² | RMSE={t0['rmse_lsb']:.2f} LSB | ENOB={t0['enob_bits']:.2f} b | W8={t0['w8_diag']}")

    best_loss = t0["loss_lsb2"]
    best_ep = 0
    best_enob = t0["enob_bits"]

    print("-" * 80)
    print(f"{'Ep #':<6} {'Phase':<16} {'Reg λ':<7} | {'Loss (LSB²)':<12} | {'RMSE (LSB)':<11} | {'ENOB (b)':<10} | {'W8 Diag (Cols 0..5)':<25}")
    print("-" * 80)

    for ep in range(1, epochs + 1):
        if ep < 100:
            phase = "BASELINE_ZERO"
            cur_reg = 0
            is_training = False
        elif ep < 200:
            phase = "BASELINE_KNEE"
            cur_reg = 0
            is_training = False
        elif ep < 500:
            phase = "TRAIN_REG_ON"
            cur_reg = reg_lambda
            is_training = True
        elif ep < 800:
            phase = "TRAIN_REG_OFF"
            cur_reg = 0
            is_training = True
        else:
            phase = "TRAIN_REG_ON_2"
            cur_reg = reg_lambda
            is_training = True

        # Phase Switchovers
        if ep == 100:
            print("=" * 80)
            print(f">>> [EPOCH 100]: SMACKING ON KNEE BASELINE (±16 LSB) ON M3 & M8! (Training OFF, LR = 0)")
            print("=" * 80)
            client._send_binary(MAML_CMD_CENTER_WEIGHTS, struct.pack("<B", 1))
            client._send_binary(MAML_CMD_SET_REG, struct.pack("<H", 0))
            time.sleep(0.04)

        elif ep == 200:
            print("=" * 80)
            print(f">>> [EPOCH 200]: ACTIVE TRAINING ON! REGULARIZATION ON (λ = {reg_lambda}, LR = {lr:.2f}x)")
            print("=" * 80)
            client._send_binary(MAML_CMD_SET_REG, struct.pack("<H", reg_lambda))
            time.sleep(0.02)

        elif ep == 500:
            print("=" * 80)
            print(f">>> [EPOCH 500]: REGULARIZATION OFF! (λ = 0, Active Training continues)")
            print("=" * 80)
            client._send_binary(MAML_CMD_SET_REG, struct.pack("<H", 0))
            time.sleep(0.02)

        elif ep == 800:
            print("=" * 80)
            print(f">>> [EPOCH 800]: REGULARIZATION ON AGAIN! (λ = {reg_lambda}, Active Training continues)")
            print("=" * 80)
            client._send_binary(MAML_CMD_SET_REG, struct.pack("<H", reg_lambda))
            time.sleep(0.02)

        # Draw fresh arbitrary random white-noise vector every epoch
        client._send_binary(MAML_CMD_RAND_DATA, struct.pack("<B", 2))
        time.sleep(0.012)

        # Active training step in Stages 3, 4, 5
        if is_training:
            client._send_binary(MAML_CMD_STEP_OUTER, struct.pack("<H", cur_reg))
            time.sleep(0.015)

        t_dict = get_averaged_telemetry(client, n_avg=4)

        if is_training and t_dict["loss_lsb2"] < best_loss:
            best_loss = t_dict["loss_lsb2"]
            best_ep = ep
            best_enob = t_dict["enob_bits"]

        rec = {
            "epoch": ep,
            "phase": phase,
            "reg_lambda_q16": cur_reg,
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

        if ep % 50 == 0 or ep in (1, 99, 100, 199, 200, 499, 500, 799, 800, epochs):
            print(
                f"  Ep {ep:<4d} [{phase:<14s}] λ={cur_reg:<5d} | "
                f"Loss={t_dict['loss_lsb2']:<10.1f} LSB² | "
                f"RMSE={t_dict['rmse_lsb']:<9.2f} LSB | "
                f"ENOB={t_dict['enob_bits']:<8.2f} b | "
                f"W8={t_dict['w8_diag']}"
            )

    # Save Run JSON
    out_obj = {
        "provenance": {
            "run_id": run_idx,
            "total_runs": total_runs,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "pcb_version": "v1.3.2",
            "hardware_mods": "1k / 5.1k ohm summing attenuator (no ADC149)",
            "soc_target": "Efinix Trion T120F324 @ 192.168.1.50:5000",
            "hw_logic_version": ver_info.get("hw_version", "0x20261030"),
            "hw_logic_id": ver_info.get("hw_id", "MAM1"),
            "sw_firmware_version": ver_info.get("sw_version", "v2.1-MAML"),
            "sw_build": ver_info.get("sw_build", "Oct 30 2026"),
            "mode": "Mode A (Jumper 3, 2-layer Triad)",
            "hadamard_delay_us": 5000,
            "seed_pct": 0,
            "lr": lr,
            "reg_lambda_q16": reg_lambda,
            "patent": "SE 2630397-4 (Open Science Hardware)",
        },
        "summary": {
            "total_epochs": epochs,
            "best_loss_lsb2": best_loss,
            "best_epoch": best_ep,
            "best_enob_bits": best_enob,
            "base0_loss_lsb2": records[0]["loss_lsb2"],
            "base_knee_loss_lsb2": records[100]["loss_lsb2"] if len(records) > 100 else records[-1]["loss_lsb2"],
            "end_reg_on_1_loss": records[499]["loss_lsb2"] if len(records) > 499 else records[-1]["loss_lsb2"],
            "end_reg_on_1_enob": records[499]["enob_bits"] if len(records) > 499 else records[-1]["enob_bits"],
            "end_reg_off_loss": records[799]["loss_lsb2"] if len(records) > 799 else records[-1]["loss_lsb2"],
            "end_reg_off_enob": records[799]["enob_bits"] if len(records) > 799 else records[-1]["enob_bits"],
            "final_loss_lsb2": records[-1]["loss_lsb2"],
            "final_enob_bits": records[-1]["enob_bits"],
            "transitions": [
                {"epoch": 100, "label": "Knee Base", "color": "#d97706", "bg": "#fef3c7"},
                {"epoch": 200, "label": "Train ON (Reg ON)", "color": "#16a34a", "bg": "#dcfce7"},
                {"epoch": 500, "label": "Reg OFF", "color": "#e11d48", "bg": "#ffe4e6"},
                {"epoch": 800, "label": "Reg ON", "color": "#2563eb", "bg": "#dbeafe"},
            ],
        },
        "epochs": records,
    }

    with open(out_file, "w") as f:
        json.dump(out_obj, f, indent=2)

    print(f"\n[+] Run {run_idx:02d} complete! Saved to {out_file}")
    print(f"    Best Loss: {best_loss:.1f} LSB² (Ep {best_ep}) | Peak ENOB: {best_enob:.2f} bits")
    if len(records) > 499:
        print(f"    Epoch 499 (End of Reg ON):  Loss={records[499]['loss_lsb2']:.1f} LSB², ENOB={records[499]['enob_bits']:.2f} b")
    if len(records) > 799:
        print(f"    Epoch 799 (End of Reg OFF): Loss={records[799]['loss_lsb2']:.1f} LSB², ENOB={records[799]['enob_bits']:.2f} b")
    print(f"    Final Epoch (Ep {records[-1]['epoch']}): Loss={records[-1]['loss_lsb2']:.1f} LSB², ENOB={records[-1]['enob_bits']:.2f} b")

    return out_file


def main():
    parser = argparse.ArgumentParser(description="10-Run 1000-Epoch Dynamic Baseline Regularization Campaign")
    parser.add_argument("--runs", type=int, default=10, help="Total number of consecutive runs (default 10)")
    parser.add_argument("--epochs", type=int, default=1000, help="Total epochs per run (default 1000)")
    parser.add_argument("--lr", type=float, default=0.25, help="Learning rate (default 0.25x)")
    parser.add_argument("--reg-lambda", type=int, default=512, help="L2 Regularization strength Q0.16 (default 512)")
    parser.add_argument("--host", default="192.168.1.50")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--skip-version-guard", action="store_true", help="Skip version guard verification")
    args = parser.parse_args()

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("INVERTED MAML 10-RUN 1000-EPOCH REGULARIZATION BENCHMARK CAMPAIGN")
    print(f"Target: {args.host}:{args.port} | Total Runs: {args.runs} | Epochs/Run: {args.epochs}")
    print(f"Knobs: LR = {args.lr:.2f}x | Reg Lambda = {args.reg_lambda} | Delay = 5.0 ms | Seed = 0 (Pure Analog Noise)")
    print("=" * 80)

    # 1. Version Guard Verification
    if not args.skip_version_guard:
        ver_info = ensure_version_guard(host=args.host, port=args.port)
    else:
        ver_info = {"hw_version": "0x20261030", "hw_id": "MAM1", "sw_version": "v2.1-MAML", "sw_build": "Oct 30 2026"}

    client = MamlUdpClient(host=args.host, port=args.port, timeout=1.5)

    saved_files: List[Path] = []
    t_start = time.time()

    for r in range(1, args.runs + 1):
        f = execute_single_run(
            client=client,
            run_idx=r,
            total_runs=args.runs,
            epochs=args.epochs,
            lr=args.lr,
            reg_lambda=args.reg_lambda,
            ver_info=ver_info,
        )
        saved_files.append(f)
        time.sleep(0.5)

    client.close()
    total_dt = time.time() - t_start

    print("\n" + "=" * 80)
    print(f"ALL {args.runs} RUNS COMPLETED SUCCESSFULLY in {total_dt/60:.2f} minutes!")
    print("=" * 80)
    print("\nANIMATION GUI COMMANDS TO INSPECT EACH RUN:")
    for i, path in enumerate(saved_files, 1):
        print(f"  Run {i:02d}: /home/olle/anaconda3/bin/python FPGA_code/scripts/maml_post_analysis_gui.py {path}")
    print("=" * 80)


if __name__ == "__main__":
    main()

