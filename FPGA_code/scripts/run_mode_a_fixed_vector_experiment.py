#!/usr/bin/env python3
"""
run_mode_a_fixed_vector_experiment.py
Runs Inverted MAML Mode A training on a SINGLE FIXED (LOCKED) VECTOR
on the new 1k/15k ohm hardware summing attenuator.

Eliminates random vector amplitude variance, demonstrating pure monotonic
deterministic analog convergence without 'vector noise'.
"""

import sys
import time
import json
import argparse
from pathlib import Path
import numpy as np

sys.path.append(str(Path(__file__).parent))
from run_mode_a_longterm_batch_sweep import (
    MamlUdpClient,
    get_averaged_telemetry,
)
from gui.udp_client import MAML_CMD_STEP_OUTER

def run_fixed_vector_experiment(lr=2.0, epochs=20, host="192.168.1.50", port=5000, out_json=None):
    client = MamlUdpClient(host=host, port=port, timeout=3.0)
    lr_inner_q16 = max(32, min(32768, int(round(1024 * lr))))

    print("=" * 78)
    print("MODE A FIXED-VECTOR EXPERIMENT: 1k / 15k Ohm Summing Attenuator")
    print(f"Target: {host}:{port} | LOCKED Vector (No PRNG) | LR={lr:.2f}x (Q16={lr_inner_q16}) | Epochs={epochs}")
    print("=" * 78)

    # 1. Initialize Mode A centered baseline
    print("[*] Initializing baseline configuration & centering weights...")
    client.set_config(
        mode=0, jumper_mode=3, led_switches=3, max_meas_win_pct=100, hadamard_khz=500,
        inner_loop_n=100, seed_pct=28, seed_mode=1, w_hid_mag=0, trim_hid_mag=0,
        hadamard_delay_us=5000,
        lr_inner_q16=lr_inner_q16,
    )
    time.sleep(0.05)
    client.center_compensation_weights()
    time.sleep(0.05)

    # 2. Extract baseline telemetry (locking x_ref)
    init_telem = get_averaged_telemetry(client, n_avg=5)
    if not init_telem:
        print("[!] ERROR: Failed to read initial telemetry from hardware.")
        return

    x_ref_locked = list(init_telem["x_ref"])
    z_target_locked = [round(x, 1) for x in init_telem["z_target"]]

    print("\n--- Locked Vector Status ---")
    print(f"  Fixed Input X_ref:  {x_ref_locked}")
    print(f"  Fixed Z_target LSB: {z_target_locked}")
    print(f"  Initial ADC45 LSB:  {[round(x, 1) for x in init_telem['adc45']]}")
    print(f"  Initial ADC49 LSB:  {[round(x, 1) for x in init_telem['adc49']]}")
    print(f"  Initial ERR49 LSB:  {[round(x, 1) for x in init_telem['err49']]}")
    print(f"  Initial W8 Diag:    {init_telem['w8_diag']}")
    print(f"  Initial W3 Diag:    {init_telem['w3_diag']}")
    print(f"  Initial Loss:       {init_telem['loss_lsb2']:.1f} LSB^2 | RMSE: {init_telem['rmse_lsb']:.2f} LSB | ENOB: {init_telem['enob_bits']:.2f} bits\n")

    epoch_records = []
    epoch_records.append({
        "epoch": 0,
        "loss_lsb2": init_telem["loss_lsb2"],
        "rmse_lsb": init_telem["rmse_lsb"],
        "enob_bits": init_telem["enob_bits"],
        "w8_diag": list(init_telem["w8_diag"]),
        "w3_diag": list(init_telem["w3_diag"]),
        "w_m8": init_telem["w_m8"],
        "w_m3": init_telem["w_m3"],
        "x_ref": x_ref_locked,
        "z_target": z_target_locked,
        "adc45": [round(x, 1) for x in init_telem["adc45"]],
        "adc49": [round(x, 1) for x in init_telem["adc49"]],
        "err49": [round(x, 1) for x in init_telem["err49"]],
        "r_m3": 1.0,
    })

    t_start = time.time()
    print("-" * 78)
    print("Ep  # | RMSE (LSB) | ENOB (bits) | Loss (LSB²) | M8 Diag (Columns 0..5)   | r_M3")
    print("-" * 78)

    best_rmse = init_telem["rmse_lsb"]
    best_enob = init_telem["enob_bits"]
    best_ep = 0

    for ep in range(1, epochs + 1):
        # Execute single deterministic step on the LOCKED vector
        client._send_binary(MAML_CMD_STEP_OUTER)
        time.sleep(0.04)

        # Read settled post-step telemetry
        p = get_averaged_telemetry(client, n_avg=4)
        if not p:
            print(f"[!] Warning: Dropped telemetry packet at Ep {ep}")
            continue

        rmse = p["rmse_lsb"]
        loss = p["loss_lsb2"]
        enob = p["enob_bits"]
        w8_diag = p["w8_diag"]
        w3_diag = p["w3_diag"]

        if rmse < best_rmse:
            best_rmse = rmse
            best_enob = enob
            best_ep = ep

        # Matrix 3 correlation
        r_m3 = 1.0
        try:
            m3_init = np.array(init_telem["w_m3"]).flatten()
            m3_curr = np.array(p["w_m3"]).flatten()
            if np.std(m3_init) > 1e-6 and np.std(m3_curr) > 1e-6:
                r_m3 = round(float(np.corrcoef(m3_init, m3_curr)[0, 1]), 4)
        except Exception:
            pass

        epoch_records.append({
            "epoch": ep,
            "train_rmse": rmse,
            "loss_lsb2": loss,
            "rmse_lsb": rmse,
            "enob_bits": enob,
            "w8_diag": list(w8_diag),
            "w3_diag": list(w3_diag),
            "w_m8": p.get("w_m8", []),
            "w_m3": p.get("w_m3", []),
            "x_ref": x_ref_locked,
            "z_target": z_target_locked,
            "adc45": [round(x, 1) for x in p.get("adc45", [0]*6)],
            "adc49": [round(x, 1) for x in p.get("adc49", [0]*6)],
            "err49": [round(x, 1) for x in p.get("err49", [0]*6)],
            "r_m3": r_m3,
        })

        print(f"Ep {ep:2d}/{epochs} | {rmse:6.2f} LSB | {enob:5.2f} bits | {loss:8.1f} LSB² | M8: {w8_diag} | r_M3={r_m3:+.4f}", flush=True)

    elapsed = time.time() - t_start
    print("-" * 78)
    print(f"[+] Completed {epochs} epochs in {elapsed:.2f} s ({elapsed/epochs*1000:.1f} ms/ep)")

    # Statistical evaluation
    losses = [r["loss_lsb2"] for r in epoch_records[1:]]
    eps = [r["epoch"] for r in epoch_records[1:]]
    coeffs = np.polyfit(eps, losses, 1)
    slope = coeffs[0]
    r2 = 1 - (np.sum((losses - np.poly1d(coeffs)(eps))**2) / np.sum((losses - np.mean(losses))**2))
    
    net_drop_pct = ((epoch_records[-1]["loss_lsb2"] - epoch_records[0]["loss_lsb2"]) / epoch_records[0]["loss_lsb2"]) * 100

    print("\n" + "="*60)
    print(f"FIXED VECTOR RESULTS: 1k/15k Ohm | LR={lr:.2f}x | {epochs} Epochs")
    print("="*60)
    print(f"Initial Error:           {epoch_records[0]['rmse_lsb']:.2f} LSB ({epoch_records[0]['enob_bits']:.2f} b, Loss {epoch_records[0]['loss_lsb2']:.1f} LSB^2)")
    print(f"Final Error (Ep {epochs}):       {epoch_records[-1]['rmse_lsb']:.2f} LSB ({epoch_records[-1]['enob_bits']:.2f} b, Loss {epoch_records[-1]['loss_lsb2']:.1f} LSB^2)")
    print(f"Net Loss Change:         {net_drop_pct:+.1f}%")
    print(f"Slope (beta_1):          {slope:+.2f} LSB^2/epoch")
    print(f"Linear Fit R^2:          {r2:.4f}")
    print(f"Best Residual Error:     {best_rmse:.2f} LSB ({best_enob:.2f} bits ENOB) at Ep {best_ep}")
    print(f"Final M8 Diag:           {epoch_records[-1]['w8_diag']}")
    print(f"Final M3 Diag:           {epoch_records[-1]['w3_diag']}")
    print(f"Matrix 33 r_M3:          {epoch_records[-1]['r_m3']}")

    if out_json is None:
        out_json = Path(f"FPGA_code/logs/mode_a_longterm_sweep/test_1k15k_fixed_vec_lr{int(round(lr*100)):02d}p_{epochs}ep.json")
    else:
        out_json = Path(out_json)

    out_json.parent.mkdir(parents=True, exist_ok=True)
    with open(out_json, "w") as f:
        json.dump({
            "test": "1k_15k_fixed_vector_experiment",
            "k": 1, "lr": lr, "lr_inner_q16": lr_inner_q16, "num_epochs": epochs,
            "elapsed_s": elapsed,
            "slope": slope, "r2": r2, "net_drop_pct": net_drop_pct,
            "best_rmse": best_rmse, "best_enob": best_enob, "best_ep": best_ep,
            "epochs": epoch_records,
            "records": epoch_records,
            "metadata": {
                "t_ms": 5.0,
                "vector_mode": "locked_fixed",
                "x_ref": x_ref_locked,
                "z_target": z_target_locked,
                "lr": lr,
            }
        }, f, indent=2)
    print(f"[+] Saved fixed vector log to {out_json}")
    return out_json

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--lr", type=float, default=2.0)
    parser.add_argument("--epochs", type=int, default=20)
    args = parser.parse_args()
    run_fixed_vector_experiment(lr=args.lr, epochs=args.epochs)
