#!/home/olle/anaconda3/bin/python
"""
run_1k33k_experiment.py
Runs True-Batch Mode A experiment on the new 1k / 3.3k ohm hardware summing attenuator.
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

def run_experiment(k=8, lr=0.08, epochs=30, strata=1, t_min_us=5000, t_max_us=5000, seed_pct=0, seed_mode=0, host="192.168.1.50", port=5000, out_json=None):
    client = MamlUdpClient(host=host, port=port, timeout=4.0)
    lr_inner_q16 = max(32, min(32768, int(round(1024 * lr))))

    if out_json is None:
        out_json = Path(f"FPGA_code/logs/mode_a_longterm_sweep/test_1k33k_k{k}_s{strata}_5ms_seed{seed_pct}_lr{int(round(lr*100)):02d}p_{epochs}ep.json")
    else:
        out_json = Path(out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 78)
    print("MODE A HARDWARE EXPERIMENT: 1k / 3.3k Ohm Summing Attenuator")
    print(f"Target: {host}:{port} | K={k} ({k*strata} samples/step) | Strata={strata} ({t_min_us}-{t_max_us} us) | Seed={seed_pct}% (m={seed_mode}) | LR={lr:.2f}x (Q16={lr_inner_q16}) | Epochs={epochs}")
    print(f"Log Destination: {out_json}")
    print("=" * 78)

    # 1. Initialize Mode A baseline (Centered or Seeded)
    client.set_config(
        mode=0, jumper_mode=3, led_switches=3, max_meas_win_pct=100, hadamard_khz=500,
        inner_loop_n=100, seed_pct=seed_pct, seed_mode=seed_mode, w_hid_mag=0, trim_hid_mag=0,
        hadamard_delay_us=5000,
        lr_inner_q16=lr_inner_q16,
    )
    time.sleep(0.05)
    if seed_pct > 0:
        print(f"[*] Seeding compensation weights with {seed_pct}% swing (mode={seed_mode})...")
        client.seed_weights(seed_mode=seed_mode, swing_pct=seed_pct)
    else:
        print("[*] Centering baseline weights...")
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

    with open(out_json, "w") as f:
        json.dump({
            "hardware": "Efinix Trion T120F324 Master SoC",
            "resistors": "1k / 3.3k ohm summing attenuator",
            "k": k, "lr": lr, "epochs": epochs, "epochs_completed": 0,
            "best_rmse": init_telem["rmse_lsb"], "best_enob": init_telem["enob_bits"], "best_epoch": 0,
            "records": epoch_records,
            "metadata": {"baseline_epochs": 0, "lr_scale": lr, "t_min_ms": 4.9, "t_max_ms": 5.1}
        }, f, indent=2)

    t_start = time.time()
    print("-" * 78)
    print("Ep  # | Train RMSE | Val RMSE   | Val ENOB | M8 Diag (Columns 0..5)   | r_M3")
    print("-" * 78)

    best_rmse = 999.0
    best_enob = 0.0
    best_ep = 0

    for ep in range(1, epochs + 1):
        # A. Batch Step (K vectors * strata = Total Samples)
        raw_train = None
        for attempt in range(3):
            raw_train = client._send_binary(
                MAML_CMD_BATCH_STEP,
                struct.pack("<BBHHH", k, strata, t_min_us, t_max_us, lr_inner_q16)
            )
            if raw_train and len(raw_train) >= client.TELEM_SIZE:
                break
            time.sleep(0.04)

        if not raw_train or len(raw_train) < client.TELEM_SIZE:
            print(f"[!] Warning: Ep {ep} train packet dropped.")
            continue

        train_p = parse_telemetry_packet(raw_train, client)

        # B. Fixed Holdout Validation
        draw_fresh_vector(client, settle_s=0.04)
        val_telem = get_averaged_telemetry(client, n_avg=4)
        if not val_telem:
            val_telem = train_p

        # Topographical correlation of M3
        m3_init = np.array(init_telem["w_m3"], dtype=np.float64)[:6, :6].flatten()
        m3_curr = np.array(val_telem["w_m3"], dtype=np.float64)[:6, :6].flatten()
        if np.std(m3_init) > 1e-4 and np.std(m3_curr) > 1e-4:
            r_m3 = float(np.corrcoef(m3_init, m3_curr)[0, 1])
        else:
            r_m3 = 1.0

        if val_telem["rmse_lsb"] < best_rmse:
            best_rmse = val_telem["rmse_lsb"]
            best_enob = val_telem["enob_bits"]
            best_ep = ep

        print(
            f"{ep:4d} | {train_p['rmse_lsb']:8.2f} LSB | {val_telem['rmse_lsb']:8.2f} LSB | "
            f"{val_telem['enob_bits']:6.2f} b | {list(val_telem['w8_diag'])} | {r_m3:+.4f}",
            flush=True
        )

        epoch_records.append({
            "epoch": ep,
            "loss_lsb2": val_telem["loss_lsb2"],
            "rmse_lsb": val_telem["rmse_lsb"],
            "enob_bits": val_telem["enob_bits"],
            "w8_diag": list(val_telem["w8_diag"]),
            "w3_diag": list(val_telem["w3_diag"]),
            "w_m8": val_telem["w_m8"],
            "w_m3": val_telem["w_m3"],
            "x_ref": list(val_telem.get("x_ref", [0]*6)),
            "z_target": [round(x, 1) for x in val_telem.get("z_target", [0]*6)],
            "adc45": [round(x, 1) for x in val_telem.get("adc45", [0]*6)],
            "adc49": [round(x, 1) for x in val_telem.get("adc49", [0]*6)],
            "err49": [round(x, 1) for x in val_telem.get("err49", [0]*6)],
            "r_m3": r_m3,
        })

        # Incremental save every epoch so live telemetry & GUI always have 100% complete data
        incremental_summary = {
            "hardware": "Efinix Trion T120F324 Master SoC",
            "resistors": "1k / 3.3k ohm summing attenuator",
            "k": k,
            "lr": lr,
            "epochs": epochs,
            "epochs_completed": ep,
            "best_rmse": best_rmse,
            "best_enob": best_enob,
            "best_epoch": best_ep,
            "records": epoch_records,
            "metadata": {
                "baseline_epochs": 0,
                "lr_scale": lr,
                "t_min_ms": t_min_us / 1000.0,
                "t_max_ms": t_max_us / 1000.0,
                "strata": strata
            }
        }
        with open(out_json, "w") as f:
            json.dump(incremental_summary, f, indent=2)

    t_elapsed = time.time() - t_start
    print("-" * 78)
    print(f"EXPERIMENT FINISHED in {t_elapsed:.1f} s ({t_elapsed/60:.1f} min)")
    print(f"Best Hardware Result: {best_rmse:.2f} LSB RMSE | {best_enob:.2f} bits ENOB at Epoch {best_ep}")
    print(f"Saving telemetry dataset to {out_json}...")

    summary_data = {
        "hardware": "Efinix Trion T120F324 Master SoC",
        "resistors": "1k / 3.3k ohm summing attenuator",
        "k": k,
        "strata": strata,
        "t_min_ms": t_min_us / 1000.0,
        "t_max_ms": t_max_us / 1000.0,
        "lr": lr,
        "epochs": epochs,
        "best_rmse": best_rmse,
        "best_enob": best_enob,
        "best_epoch": best_ep,
        "duration_s": t_elapsed,
        "records": epoch_records,
    }

    with open(out_json, "w") as f:
        json.dump(summary_data, f, indent=2)
    print("[+] Dataset saved successfully.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run 1k/3.3k True-Batch Mode A Experiment")
    parser.add_argument("--k", type=int, default=8, help="Mini-batch size K (default 8)")
    parser.add_argument("--lr", type=float, default=0.08, help="Learning rate multiplier (default 0.08)")
    parser.add_argument("--epochs", type=int, default=1000, help="Number of training epochs (default 1000)")
    parser.add_argument("--strata", type=int, default=1, help="Number of strata per vector (default 1)")
    parser.add_argument("--t-min", type=int, default=5000, help="Min time in us (default 5000)")
    parser.add_argument("--t-max", type=int, default=5000, help="Max time in us (default 5000)")
    parser.add_argument("--seed-pct", type=int, default=0, help="Initial Seed swing percentage (0..100)")
    parser.add_argument("--seed-mode", type=int, default=0, help="Seed mode (0=Uniform, 1=Auto/Xavier, 2=Orthogonal, 3=Checkerboard)")
    parser.add_argument("--out", type=str, default=None, help="Output JSON path")
    args = parser.parse_args()

    run_experiment(
        k=args.k, lr=args.lr, epochs=args.epochs,
        strata=args.strata, t_min_us=args.t_min, t_max_us=args.t_max,
        seed_pct=args.seed_pct, seed_mode=args.seed_mode,
        out_json=args.out
    )

