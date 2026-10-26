#!/usr/bin/env python3
"""
run_1k15k_experiment.py
Runs True-Batch Mode A experiment on the new 1k/15k ohm hardware summing attenuator.
Supports configurable K, LR, and Epochs.
"""

import sys
import time
import json
import struct
import argparse
from pathlib import Path
import numpy as np

sys.path.append(str(Path(__file__).parent))
from run_mode_a_longterm_batch_sweep import (
    MamlUdpClient,
    draw_fresh_vector,
    get_averaged_telemetry,
    parse_telemetry_packet,
    MAML_CMD_BATCH_STEP,
)

def run_experiment(k=8, lr=0.32, epochs=40, host="192.168.1.50", port=5000, out_json=None):
    client = MamlUdpClient(host=host, port=port, timeout=4.0)
    lr_inner_q16 = max(32, min(4096, int(round(1024 * lr))))

    print("=" * 78)
    print("MODE A HARDWARE EXPERIMENT: 1k / 15k Ohm Summing Attenuator")
    print(f"Target: {host}:{port} | K={k} ({k*10} samples/step) | LR={lr:.2f}x (Q16={lr_inner_q16}) | Epochs={epochs}")
    print("=" * 78)

    # 1. Initialize Mode A centered baseline
    print("[*] Centering baseline weights...")
    client.set_config(
        mode=0, jumper_mode=3, led_switches=3, max_meas_win_pct=100, hadamard_khz=500,
        inner_loop_n=100, seed_pct=28, seed_mode=1, w_hid_mag=0, trim_hid_mag=0,
        hadamard_delay_us=5000,
        lr_inner_q16=lr_inner_q16,
    )
    time.sleep(0.05)
    client.center_compensation_weights()
    time.sleep(0.05)

    # 2. Extract baseline telemetry & check all 6 columns
    draw_fresh_vector(client, settle_s=0.04)
    init_telem = get_averaged_telemetry(client, n_avg=6)
    if not init_telem:
        print("[!] ERROR: Failed to read initial telemetry from hardware.")
        return

    print("\n--- Initial 6-Column Signal Status ---")
    print(f"  ADC45 (4.5ms) LSB: {[round(x, 1) for x in init_telem['adc45']]}")
    print(f"  ADC49 (4.9ms) LSB: {[round(x, 1) for x in init_telem['adc49']]}")
    print(f"  ERR49 (Error) LSB: {[round(x, 1) for x in init_telem['err49']]}")
    print(f"  Initial W8 Diag:   {init_telem['w8_diag']}")
    print(f"  Initial W3 Diag:   {init_telem['w3_diag']}")
    print(f"  Initial Val Loss:  {init_telem['loss_lsb2']:.1f} LSB^2 | RMSE: {init_telem['rmse_lsb']:.2f} LSB | ENOB: {init_telem['enob_bits']:.2f} bits\n")

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
        "x_ref": list(init_telem.get("x_ref", [0]*6)),
        "z_target": [round(x, 1) for x in init_telem.get("z_target", [0]*6)],
        "adc45": [round(x, 1) for x in init_telem.get("adc45", [0]*6)],
        "adc49": [round(x, 1) for x in init_telem.get("adc49", [0]*6)],
        "err49": [round(x, 1) for x in init_telem.get("err49", [0]*6)],
        "r_m3": 1.0,
    })

    t_start = time.time()
    print("-" * 78)
    print("Ep  # | Train RMSE | Val RMSE   | Val ENOB | M8 Diag (Columns 0..5)   | r_M3")
    print("-" * 78)

    best_rmse = 999.0
    best_enob = 0.0
    best_ep = 0

    for ep in range(1, epochs + 1):
        # A. Batch Step (K vectors * 10 strata = Total Samples)
        raw_train = None
        for attempt in range(3):
            raw_train = client._send_binary(
                MAML_CMD_BATCH_STEP,
                struct.pack("<BBHHH", k, 10, 4900, 5100, lr_inner_q16)
            )
            if raw_train and len(raw_train) >= client.TELEM_SIZE:
                break
            time.sleep(0.04)

        if not raw_train or len(raw_train) < client.TELEM_SIZE:
            print(f"[!] Warning: Ep {ep} train packet dropped.")
            continue

        train_p = parse_telemetry_packet(raw_train, client)
        train_rmse = train_p["rmse_lsb"]

        # B. Validation Step (unseen vector)
        draw_fresh_vector(client, settle_s=0.03)
        val_p = get_averaged_telemetry(client, n_avg=2)
        if not val_p:
            val_p = train_p

        val_rmse = val_p["rmse_lsb"]
        val_loss = val_p["loss_lsb2"]
        val_enob = val_p["enob_bits"]
        w8_diag = val_p["w8_diag"]
        w3_diag = val_p["w3_diag"]

        if val_rmse < best_rmse:
            best_rmse = val_rmse
            best_enob = val_enob
            best_ep = ep

        # Correlation Matrix 33
        r_m3 = 1.0
        try:
            m3_init = np.array(init_telem["w_m3"]).flatten()
            m3_curr = np.array(val_p["w_m3"]).flatten()
            if np.std(m3_init) > 1e-6 and np.std(m3_curr) > 1e-6:
                r_m3 = round(float(np.corrcoef(m3_init, m3_curr)[0, 1]), 4)
        except Exception:
            pass

        epoch_records.append({
            "epoch": ep,
            "train_rmse": train_rmse,
            "loss_lsb2": val_loss,
            "rmse_lsb": val_rmse,
            "enob_bits": val_enob,
            "w8_diag": list(w8_diag),
            "w3_diag": list(w3_diag),
            "w_m8": val_p.get("w_m8", []),
            "w_m3": val_p.get("w_m3", []),
            "x_ref": list(val_p.get("x_ref", [0]*6)),
            "z_target": [round(x, 1) for x in val_p.get("z_target", [0]*6)],
            "adc45": [round(x, 1) for x in val_p.get("adc45", [0]*6)],
            "adc49": [round(x, 1) for x in val_p.get("adc49", [0]*6)],
            "err49": [round(x, 1) for x in val_p.get("err49", [0]*6)],
            "r_m3": r_m3,
        })

        print(f"Ep {ep:2d}/{epochs} | Train {train_rmse:5.1f} | Val {val_rmse:5.1f} LSB | {val_enob:4.2f} b  | M8: {w8_diag} | r_M3={r_m3:+.4f}", flush=True)

    elapsed = time.time() - t_start
    print("-" * 78)
    print(f"[+] Completed {epochs} epochs in {elapsed:.1f} s ({elapsed/epochs:.1f} s/ep)")

    # Statistical evaluation
    losses = [r["loss_lsb2"] for r in epoch_records[1:]]
    eps = [r["epoch"] for r in epoch_records[1:]]
    coeffs = np.polyfit(eps, losses, 1)
    slope = coeffs[0]
    r2 = 1 - (np.sum((losses - np.poly1d(coeffs)(eps))**2) / np.sum((losses - np.mean(losses))**2))
    
    q_len = max(2, epochs // 4)
    q1_mean = np.mean(losses[:q_len])
    q4_mean = np.mean(losses[-q_len:])
    trend_pct = ((q4_mean - q1_mean) / q1_mean) * 100

    print("\n" + "="*50)
    print(f"RESULTS: 1k/15k Ohm | K={k} | LR={lr:.2f}x | {epochs} Epochs")
    print("="*50)
    print(f"Initial Val Loss (Ep 0): {epoch_records[0]['loss_lsb2']:.1f} LSB^2 ({epoch_records[0]['rmse_lsb']:.1f} LSB, {epoch_records[0]['enob_bits']:.2f} b)")
    print(f"Q1 Mean Loss (Ep 1-{q_len}):      {q1_mean:.1f} LSB^2")
    print(f"Q4 Mean Loss (Ep {epochs-q_len+1}-{epochs}):     {q4_mean:.1f} LSB^2")
    print(f"Net Trend:               {trend_pct:+.1f}%")
    print(f"Slope (beta_1):          {slope:+.2f} LSB^2/epoch")
    print(f"Linear Fit R^2:          {r2:.4f}")
    print(f"Best Val Error:          {best_rmse:.2f} LSB ({best_enob:.2f} bits ENOB) at Ep {best_ep}")
    print(f"Final M8 Diag:           {epoch_records[-1]['w8_diag']}")
    print(f"Final M3 Diag:           {epoch_records[-1]['w3_diag']}")
    print(f"Matrix 33 r_M3:          {epoch_records[-1]['r_m3']}")

    if out_json is None:
        out_json = Path(f"FPGA_code/logs/mode_a_longterm_sweep/test_1k15k_k{k}_lr{int(round(lr*100)):02d}p_{epochs}ep.json")
    else:
        out_json = Path(out_json)

    out_json.parent.mkdir(parents=True, exist_ok=True)
    with open(out_json, "w") as f:
        json.dump({
            "test": "1k_15k_hardware_experiment",
            "k": k, "lr": lr, "lr_inner_q16": lr_inner_q16, "num_epochs": epochs,
            "elapsed_s": elapsed,
            "slope": slope, "r2": r2, "trend_pct": trend_pct,
            "best_rmse": best_rmse, "best_enob": best_enob, "best_ep": best_ep,
            "epochs": epoch_records,
            "records": epoch_records,
            "metadata": {
                "t_min_ms": 4.9,
                "t_max_ms": 5.1,
                "k": k,
                "lr": lr,
                "lr_scale": lr,
            }
        }, f, indent=2)
    print(f"[+] Saved experiment log to {out_json}")
    return out_json

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, default=8)
    parser.add_argument("--lr", type=float, default=0.32)
    parser.add_argument("--epochs", type=int, default=40)
    args = parser.parse_args()
    run_experiment(k=args.k, lr=args.lr, epochs=args.epochs)
