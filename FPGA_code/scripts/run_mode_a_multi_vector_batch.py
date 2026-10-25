#!/home/olle/anaconda3/bin/python
"""
Inverted MAML Mode A Multi-Vector Mini-Batch (K=4) Training Engine
=================================================================
Physical Silicon Execution on Efinix Trion T120 Master SoC (192.168.1.50:5000):
  1. Rotates K=4 diverse independent input vectors X_k per epoch.
  2. Evaluates gradient backpropagation and applies Q2.14 updates on physical silicon.
  3. Evaluates unseen Holdout / Validation vector per epoch WITHOUT stepping to measure
     true generalization accuracy (loss, RMSE, ENOB) across arbitrary vectors.
  4. Records full 3-matrix telemetry (M33 static, M3 and M8 dynamic 3D topography)
     compatible with maml_post_analysis_gui.py.
"""

from __future__ import annotations
import argparse
import json
import math
import os
import struct
import sys
import time
from datetime import datetime
from pathlib import Path
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from gui.udp_client import (
    MamlUdpClient,
    MAML_CMD_GET_TELEMETRY,
    MAML_CMD_STEP_OUTER,
    MAML_CMD_RAND_DATA,
    MAML_CMD_CENTER_COMP,
)

OUT_DIR = REPO_ROOT / "FPGA_code" / "logs" / "mode_a_extended_training"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def parse_telemetry_packet(raw: bytes, client: MamlUdpClient) -> dict:
    """Parse 298-byte raw UDP telemetry into structured dictionary."""
    u = struct.unpack(client.TELEM_FMT, raw[:client.TELEM_SIZE])
    x_ref = list(u[32:38])
    z_target = list(u[38:44])
    adc45 = list(u[44:50])
    adc49 = list(u[50:56])
    err49 = [adc49[i] - z_target[i] for i in range(6)]
    sigma2 = list(u[56:62])

    w_m3 = [list(u[62 + 6 * r : 62 + 6 * (r + 1)]) for r in range(8)]
    w_m8 = [list(u[110 + 6 * r : 110 + 6 * (r + 1)]) for r in range(7)]
    w_m33 = [list(u[152 + 6 * r : 152 + 6 * (r + 1)]) for r in range(6)]

    err_arr = np.array(err49, dtype=np.float64)
    rmse = float(np.sqrt(np.mean(err_arr ** 2)))
    loss = float(np.sum(err_arr ** 2) / 2.0)
    enob_calc = max(0.0, 11.0 - math.log2(max(rmse, 1.0)))

    return {
        "run_mode": int(u[2]),
        "jumper_mode": int(u[3]),
        "outer_epoch": int(u[21]),
        "inner_step": int(u[22]),
        "x_ref": x_ref,
        "z_target": z_target,
        "adc45": adc45,
        "adc49": adc49,
        "err49": err49,
        "sigma2": sigma2,
        "rmse_lsb": round(rmse, 2),
        "loss_lsb2": round(loss, 1),
        "enob_bits": round(enob_calc, 2),
        "w_m3": w_m3,
        "w_m8": w_m8,
        "w_m33": w_m33,
        "w8_diag": [w_m8[i][i] for i in range(6)],
        "w3_diag": [w_m3[i][i] for i in range(6)],
    }


def get_averaged_telemetry(client: MamlUdpClient, n_avg: int = 3) -> dict:
    """Fetch and average consecutive refresh frames for high-precision measurement."""
    acc_adc45 = np.zeros(6, dtype=np.float64)
    acc_adc49 = np.zeros(6, dtype=np.float64)
    acc_z = np.zeros(6, dtype=np.float64)
    last_parsed = None

    for i in range(n_avg):
        if i > 0:
            time.sleep(0.012)
        raw = None
        for attempt in range(4):
            raw = client._send_binary(MAML_CMD_GET_TELEMETRY)
            if raw is not None and len(raw) >= client.TELEM_SIZE:
                break
            time.sleep(0.01)
        if raw is None or len(raw) < client.TELEM_SIZE:
            raise RuntimeError("Failed to read telemetry from hardware!")
        p = parse_telemetry_packet(raw, client)
        last_parsed = p
        acc_adc45 += np.array(p["adc45"], dtype=np.float64)
        acc_adc49 += np.array(p["adc49"], dtype=np.float64)
        acc_z += np.array(p["z_target"], dtype=np.float64)

    res = dict(last_parsed)
    avg_adc45 = [round(float(v), 1) for v in (acc_adc45 / n_avg)]
    avg_adc49 = [round(float(v), 1) for v in (acc_adc49 / n_avg)]
    avg_z = [round(float(v), 1) for v in (acc_z / n_avg)]
    err = [round(avg_adc49[i] - avg_z[i], 1) for i in range(6)]
    err_arr = np.array(err, dtype=np.float64)
    rmse = float(np.sqrt(np.mean(err_arr ** 2)))
    loss = float(np.sum(err_arr ** 2) / 2.0)
    enob = max(0.0, 11.0 - math.log2(max(rmse, 1.0)))

    res["adc45"] = avg_adc45
    res["adc49"] = avg_adc49
    res["z_target"] = avg_z
    res["err49"] = err
    res["rmse_lsb"] = round(rmse, 2)
    res["loss_lsb2"] = round(loss, 1)
    res["enob_bits"] = round(enob, 2)
    return res


def draw_fresh_vector(client: MamlUdpClient, settle_s: float = 0.02) -> None:
    """Command hardware to generate fresh locked white-noise vector without resetting weights."""
    client._send_binary(MAML_CMD_RAND_DATA, struct.pack("<B", 2))
    time.sleep(settle_s)


def run_multi_vector_batch_experiment(
    host: str = "192.168.1.50",
    port: int = 5000,
    epochs: int = 40,
    batch_size_k: int = 4,
    lr_scale: float = 0.25,
    nominal_delay_us: int = 5000,
    output_filename: str = "mode_a_multi_vector_batch_k4_baseline3k9.json",
):
    lr_inner_q16 = max(32, min(4096, int(round(1024 * lr_scale))))
    print("=" * 78)
    print("Inverted MAML: Physical Mode A Multi-Vector Mini-Batch (K=4) Training")
    print(f"Target: {host}:{port} | Epochs: {epochs} | Batch Size K: {batch_size_k} | LR Scale: {lr_scale:.2f} ({lr_inner_q16}/1024)")
    print("Hardware: 1k / 3.9k passive summing attenuator (Baseline before hardware rework)")
    print("=" * 78)

    client = MamlUdpClient(host=host, port=port, timeout=1.5)

    # 1. Initialize Mode A centered baseline
    print(f"\n[*] Initializing Mode A configuration (5.0 ms, Jumper Mode 3, 2-layer, LR={lr_inner_q16})...")
    client.set_config(
        mode=0, jumper_mode=3, led_switches=3, max_meas_win_pct=100, hadamard_khz=500,
        inner_loop_n=100, seed_pct=28, seed_mode=1, w_hid_mag=0, trim_hid_mag=0,
        hadamard_delay_us=nominal_delay_us,
        lr_inner_q16=lr_inner_q16,
    )
    time.sleep(0.05)
    client.center_compensation_weights()
    time.sleep(0.05)

    # 2. Extract baseline telemetry
    draw_fresh_vector(client, settle_s=0.03)
    init_telem = get_averaged_telemetry(client, n_avg=4)
    w_m33_static = init_telem["w_m33"]
    w_m3_start = init_telem["w_m3"]
    w_m8_start = init_telem["w_m8"]

    print("\n[*] Static Payload Matrix M33 (Primary):")
    for r in range(6):
        print(f"    Row {r}: {w_m33_static[r]}")
    print(f"[*] Starting M8 Diag: {[w_m8_start[i][i] for i in range(6)]}")
    print(f"[*] Starting M3 Diag: {[w_m3_start[i][i] for i in range(6)]}")
    print(f"[*] Initial Baseline (Pre-Training): RMSE = {init_telem['rmse_lsb']} LSB | ENOB = {init_telem['enob_bits']} bits")

    epoch_records = []
    start_time = time.time()

    # Log initial Epoch 0
    init_rec = {
        "epoch": 0,
        "phase": "BASELINE",
        "batch_k": batch_size_k,
        "time_s": 0.0,
        "rmse_lsb": init_telem["rmse_lsb"],
        "enob_bits": init_telem["enob_bits"],
        "loss_lsb2": init_telem["loss_lsb2"],
        "train_rmse_mean": init_telem["rmse_lsb"],
        "val_rmse": init_telem["rmse_lsb"],
        "val_enob": init_telem["enob_bits"],
        "x_ref": init_telem["x_ref"],
        "z_target": init_telem["z_target"],
        "adc45": init_telem["adc45"],
        "adc49": init_telem["adc49"],
        "err49": init_telem["err49"],
        "w_m3": w_m3_start,
        "w_m8": w_m8_start,
        "w8_diag": [w_m8_start[i][i] for i in range(6)],
        "w3_diag": [w_m3_start[i][i] for i in range(6)],
        "r_m3": 1.0,
        "r_m8": 1.0,
    }
    epoch_records.append(init_rec)

    print("\n" + "-" * 78)
    print(f"{'Epok':<6} | {'Train RMSE':<12} | {'Val RMSE':<10} | {'Val ENOB':<10} | {'M8 Diag (Col 0..5)':<22} | {'r_M3':<6}")
    print("-" * 78)

    w3_flat_0 = np.array(w_m3_start)[:6, :6].flatten()
    w8_flat_0 = np.array(w_m8_start)[:6, :6].flatten()

    for ep in range(1, epochs + 1):
        batch_losses = []
        batch_rmses = []
        last_train_p = None

        # --- A. Mini-Batch Training Loop (K independent vectors) ---
        for k in range(batch_size_k):
            # 1. Draw fresh independent random input vector X_k
            draw_fresh_vector(client, settle_s=0.015)

            # 2. Read pre-step telemetry for vector X_k
            raw = client._send_binary(MAML_CMD_GET_TELEMETRY)
            if raw and len(raw) >= client.TELEM_SIZE:
                p_k = parse_telemetry_packet(raw, client)
                batch_rmses.append(p_k["rmse_lsb"])
                batch_losses.append(p_k["loss_lsb2"])
                last_train_p = p_k

            # 3. Take gradient step on physical silicon for vector X_k
            client.step_outer_loop()
            time.sleep(0.015)

        # Average training metrics across the K-vector batch
        avg_train_rmse = round(float(np.mean(batch_rmses)), 2) if batch_rmses else 0.0
        avg_train_loss = round(float(np.mean(batch_losses)), 1) if batch_losses else 0.0

        # --- B. Generalization / Validation Evaluation (Multi-Vector Holdout) ---
        # Evaluate across 4 independent unseen validation vectors to filter out single-vector noise!
        val_rmses = []
        val_losses = []
        last_val_telem = None
        for _ in range(4):
            draw_fresh_vector(client, settle_s=0.015)
            raw = client._send_binary(MAML_CMD_GET_TELEMETRY)
            if raw and len(raw) >= client.TELEM_SIZE:
                p_v = parse_telemetry_packet(raw, client)
                val_rmses.append(p_v["rmse_lsb"])
                val_losses.append(p_v["loss_lsb2"])
                last_val_telem = p_v

        val_rmse = round(float(np.mean(val_rmses)), 2) if val_rmses else 0.0
        val_loss = round(float(np.mean(val_losses)), 1) if val_losses else 0.0
        val_enob = round(max(0.0, 11.0 - math.log2(max(val_rmse, 1.0))), 2)
        val_telem = last_val_telem if last_val_telem is not None else last_train_p

        w_m3_cur = val_telem["w_m3"]
        w_m8_cur = val_telem["w_m8"]
        w8_diag = val_telem["w8_diag"]
        w3_diag = val_telem["w3_diag"]

        # Calculate topographical correlation with initial baseline
        w3_flat_cur = np.array(w_m3_cur)[:6, :6].flatten()
        w8_flat_cur = np.array(w_m8_cur)[:6, :6].flatten()
        r3 = float(np.corrcoef(w3_flat_0, w3_flat_cur)[0, 1]) if np.std(w3_flat_cur) > 1e-6 else 1.0
        r8 = float(np.corrcoef(w8_flat_0, w8_flat_cur)[0, 1]) if np.std(w8_flat_cur) > 1e-6 else 1.0

        # Create record compatible with maml_post_analysis_gui.py
        rec = {
            "epoch": ep,
            "phase": "TRAINING",
            "batch_k": batch_size_k,
            "time_s": round(time.time() - start_time, 2),
            "rmse_lsb": val_rmse,             # Primary curve in GUI displays validation error
            "enob_bits": val_enob,
            "loss_lsb2": val_loss,
            "train_rmse_mean": avg_train_rmse,
            "train_loss_mean": avg_train_loss,
            "val_rmse": val_rmse,
            "val_enob": val_enob,
            "x_ref": val_telem["x_ref"],
            "z_target": val_telem["z_target"],
            "adc45": val_telem["adc45"],
            "adc49": val_telem["adc49"],
            "err49": val_telem["err49"],
            "w_m3": w_m3_cur,
            "w_m8": w_m8_cur,
            "w8_diag": w8_diag,
            "w3_diag": w3_diag,
            "r_m3": round(r3, 4),
            "r_m8": round(r8, 4),
        }
        epoch_records.append(rec)

        diag_str = str([int(w) for w in w8_diag])
        print(f"Ep {ep:2d}   | {avg_train_rmse:5.2f} LSB     | {val_rmse:5.2f} LSB  | {val_enob:4.2f} bits  | {diag_str:<22} | r={r3:+.3f}")

    total_time = time.time() - start_time
    print("-" * 78)
    print(f"[+] Multi-Vector Batch Training completed in {total_time:.2f} s ({epochs} epochs, {epochs * batch_size_k} vector updates)")

    # 3. Post-Experiment Summary Analysis
    ep0 = epoch_records[0]
    ep_end = epoch_records[-1]

    # Find best validation epoch
    val_rmses = [r["val_rmse"] for r in epoch_records[1:]]
    best_val_idx = int(np.argmin(val_rmses)) + 1
    best_rec = epoch_records[best_val_idx]

    print("\n" + "=" * 78)
    print("MULTI-VECTOR BATCH (K=4) TRAINING SUMMARY ON PHYSICAL HARDWARE")
    print("=" * 78)
    print(f"Baseline Epoch 0:       RMSE = {ep0['rmse_lsb']:.2f} LSB | ENOB = {ep0['enob_bits']:.2f} bits")
    print(f"Final Epoch {epochs}:        Val RMSE = {ep_end['val_rmse']:.2f} LSB | Val ENOB = {ep_end['val_enob']:.2f} bits | Train RMSE = {ep_end['train_rmse_mean']:.2f} LSB")
    print(f"Peak Validation Epoch {best_rec['epoch']}: Val RMSE = {best_rec['val_rmse']:.2f} LSB | Val ENOB = {best_rec['val_enob']:.2f} bits (Loss: {best_rec['loss_lsb2']:.1f} LSB^2)")
    print(f"Matrix 3 Topographical Correlation r: {best_rec['r_m3']}")
    print(f"Matrix 8 Topographical Correlation r: {best_rec['r_m8']}")
    print(f"Final M8 Diagonal Weights: {best_rec['w8_diag']}")
    print(f"Final M3 Diagonal Weights: {best_rec['w3_diag']}")

    # 4. Save JSON dataset
    out_path = OUT_DIR / output_filename
    dataset = {
        "metadata": {
            "title": "Inverted MAML Mode A Multi-Vector Mini-Batch Training",
            "date": datetime.now().isoformat(),
            "target": f"{host}:{port}",
            "hardware_attenuator": "1k / 3.9k passive summing (20.4%)",
            "operating_mode": "Mode A (2-layer Triad via Sigmoid 10)",
            "batch_size_k": batch_size_k,
            "epochs": epochs,
            "total_updates": epochs * batch_size_k,
            "nominal_delay_us": nominal_delay_us,
            "execution_time_s": round(total_time, 2),
            "baseline_rmse_lsb": ep0["rmse_lsb"],
            "peak_val_rmse_lsb": best_rec["val_rmse"],
            "peak_val_enob_bits": best_rec["val_enob"],
            "peak_val_epoch": best_rec["epoch"],
        },
        "static_weights": {
            "w_m33": w_m33_static,
        },
        "epochs": epoch_records,
    }

    with open(out_path, "w") as f:
        json.dump(dataset, f, indent=2)

    print(f"\n[+] Telemetry saved to: {out_path} ({os.path.getsize(out_path) / 1024:.1f} KB)")
    print(f"[*] Ready for 3D playback in GUI: maml_post_analysis_gui.py --json {out_path}")
    print("=" * 78)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mode A Multi-Vector Batch Training Engine")
    parser.add_argument("--epochs", type=int, default=40, help="Number of training epochs (default: 40)")
    parser.add_argument("--batch-size", "-k", type=int, default=4, help="Vectors per mini-batch (default: 4)")
    parser.add_argument("--lr-scale", type=float, default=0.25, help="Learning rate scale (default: 0.25 = 1/4 LR)")
    parser.add_argument("--delay-us", type=int, default=5000, help="Hadamard delay in us (default: 5000 = 5.0ms)")
    parser.add_argument("--out", type=str, default="mode_a_multi_vector_batch_k4_baseline3k9.json", help="Output JSON filename")
    args = parser.parse_args()

    run_multi_vector_batch_experiment(
        epochs=args.epochs,
        batch_size_k=args.batch_size,
        lr_scale=args.lr_scale,
        nominal_delay_us=args.delay_us,
        output_filename=args.out,
    )

