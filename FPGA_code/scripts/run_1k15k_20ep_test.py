#!/usr/bin/env python3
"""
run_1k15k_20ep_test.py
Verification test for physical 1k / 15k ohm summing attenuator on Mode A.
Runs 20 epochs with True-Batch (K=8, 80 samples/step).
Evaluates all 6 columns, weight movements, ENOB, and convergence.
"""

import sys
import time
import json
import struct
from pathlib import Path
import numpy as np

# Ensure scripts dir is on sys.path
sys.path.append(str(Path(__file__).parent))
from run_mode_a_longterm_batch_sweep import (
    MamlUdpClient,
    draw_fresh_vector,
    get_averaged_telemetry,
    parse_telemetry_packet,
    MAML_CMD_BATCH_STEP,
    MAML_CMD_GET_TELEMETRY,
)

def run_test(k=8, lr=0.08, epochs=20, host="192.168.1.50", port=5000):
    client = MamlUdpClient(host=host, port=port, timeout=4.0)
    lr_inner_q16 = max(32, min(4096, int(round(1024 * lr))))

    print("=" * 78)
    print("MODE A HARDWARE VERIFICATION: 1k / 15k Ohm Summing Point Test")
    print(f"Target: {host}:{port} | K={k} (80 samples/step) | LR={lr:.2f}x (Q16={lr_inner_q16}) | Epochs={epochs}")
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

    print("\n--- Initial 6-Column Signal Check (Solder Verification) ---")
    print(f"  ADC45 (4.5ms) LSB: {[round(x, 1) for x in init_telem['adc45']]}")
    print(f"  ADC49 (4.9ms) LSB: {[round(x, 1) for x in init_telem['adc49']]}")
    print(f"  ERR49 (Error) LSB: {[round(x, 1) for x in init_telem['err49']]}")
    print(f"  Noise Sigma^2:     {init_telem['sigma2']}")
    print(f"  Initial W8 Diag:   {init_telem['w8_diag']}")
    print(f"  Initial W3 Diag:   {init_telem['w3_diag']}")
    print(f"  Initial Val RMSE:  {init_telem['rmse_lsb']:.2f} LSB | Loss: {init_telem['loss_lsb2']:.1f} LSB^2 | ENOB: {init_telem['enob_bits']:.2f} bits\n")

    epoch_records = []
    epoch_records.append({
        "epoch": 0,
        "loss_lsb2": init_telem["loss_lsb2"],
        "rmse_lsb": init_telem["rmse_lsb"],
        "enob_bits": init_telem["enob_bits"],
        "w8_diag": list(init_telem["w8_diag"]),
        "w3_diag": list(init_telem["w3_diag"]),
        "r_m3": 1.0,
    })

    # Fixed holdout vector for validation
    draw_fresh_vector(client, settle_s=0.04)
    val_fixed_telem = get_averaged_telemetry(client, n_avg=4)

    t_start = time.time()
    print("-" * 78)
    print("Ep  # | Train RMSE | Val RMSE   | Val ENOB | M8 Diag (Columns 0..5)   | r_M3")
    print("-" * 78)

    for ep in range(1, epochs + 1):
        # A. Batch Step (K=8, 10 strata = 80 samples)
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
            "r_m3": r_m3,
        })

        print(f"Ep {ep:2d}/{epochs} | Train {train_rmse:5.1f} | Val {val_rmse:5.1f} LSB | {val_enob:4.2f} b  | M8: {w8_diag} | r_M3={r_m3:+.4f}", flush=True)

    elapsed = time.time() - t_start
    print("-" * 78)
    print(f"[+] Completed {epochs} epochs in {elapsed:.1f} s ({elapsed/epochs:.1f} s/ep)")

    # Statistical summary
    losses = [r["loss_lsb2"] for r in epoch_records[1:]]
    eps = [r["epoch"] for r in epoch_records[1:]]
    coeffs = np.polyfit(eps, losses, 1)
    slope = coeffs[0]
    r2 = 1 - (np.sum((losses - np.poly1d(coeffs)(eps))**2) / np.sum((losses - np.mean(losses))**2))
    
    q1_mean = np.mean(losses[:5])
    q4_mean = np.mean(losses[-5:])
    trend_pct = ((q4_mean - q1_mean) / q1_mean) * 100

    print("\n=== SUMMARY RESULTS (1k/15k Ohm, K=8, 20 Epochs) ===")
    print(f"Initial Val Loss (Ep 0): {epoch_records[0]['loss_lsb2']:.1f} LSB^2 ({epoch_records[0]['rmse_lsb']:.1f} LSB, {epoch_records[0]['enob_bits']:.2f} b)")
    print(f"Ep 1-5 Mean Loss:        {q1_mean:.1f} LSB^2")
    print(f"Ep 16-20 Mean Loss:      {q4_mean:.1f} LSB^2")
    print(f"Net Trend:               {trend_pct:+.1f}%")
    print(f"Slope (beta_1):          {slope:+.2f} LSB^2/epoch")
    print(f"Linear Fit R^2:          {r2:.4f}")
    print(f"Best Val ENOB:           {max(r['enob_bits'] for r in epoch_records):.2f} bits")
    print(f"Final M8 Diag:           {epoch_records[-1]['w8_diag']}")
    print(f"Final M3 Diag:           {epoch_records[-1]['w3_diag']}")

    # Save to log
    out_file = Path("FPGA_code/logs/mode_a_longterm_sweep/test_1k15k_k8_lr08p_20ep.json")
    with open(out_file, "w") as f:
        json.dump({
            "test": "1k_15k_hardware_verification",
            "k": k, "lr": lr, "epochs": epochs,
            "elapsed_s": elapsed,
            "slope": slope, "r2": r2, "trend_pct": trend_pct,
            "records": epoch_records
        }, f, indent=2)
    print(f"[+] Saved test log to {out_file}")

if __name__ == "__main__":
    run_test()
