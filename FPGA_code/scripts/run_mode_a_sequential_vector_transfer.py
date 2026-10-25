#!/home/olle/anaconda3/bin/python
"""
Sequential Task Transfer & 3D Landscape Stability Experiment (40 + 40 Epochs)
=============================================================================
Investigates whether the Inverted MAML compensation landscape (Matrix 8 and Matrix 3)
retains common topographical features (learning physical hardware non-idealities)
or flips inside out when adapting sequentially between two distinct input vectors:
  - Epochs  1 .. 40: Trained on Input Vector A (held locked).
  - Epochs 41 .. 80: Trained on Input Vector B (held locked, NO WEIGHT RESET).
  
Records full 3D matrix topologies (M8: 7x6, M3: 8x6) for every epoch.
"""

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
)
from FPGA_code.scripts.run_mode_a_batch_training import get_averaged_telemetry

OUT_DIR = REPO_ROOT / "FPGA_code" / "logs" / "mode_a_extended_training"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def run_sequential_transfer_experiment(
    host: str = "192.168.1.50",
    port: int = 5000,
    epochs_a: int = 40,
    epochs_b: int = 40,
    t_min_ms: float = 4.9,
    t_max_ms: float = 5.1,
    num_strata: int = 5,
    output_filename: str = "mode_a_40plus40_sequential_transfer.json",
):
    total_epochs = epochs_a + epochs_b
    strata_us = np.linspace(t_min_ms * 1000, t_max_ms * 1000, num_strata, dtype=int).tolist()
    nominal_delay = int(strata_us[len(strata_us) // 2])

    print("=" * 78)
    print("Inverted MAML: Sequential Task Transfer & Landscape Stability (40 + 40 Epochs)")
    print(f"Target: {host}:{port} | Window: [{t_min_ms:.2f} .. {t_max_ms:.2f}] ms ({num_strata} strata)")
    print(f"Phase 1: Vector A ({epochs_a} epochs) -> Phase 2: Vector B ({epochs_b} epochs, continuous)")
    print("=" * 78)

    client = MamlUdpClient(host=host, port=port, timeout=1.5)

    # 1. Initialize Mode A centered baseline
    client.set_config(
        mode=0, jumper_mode=3, led_switches=3, max_meas_win_pct=100, hadamard_khz=500,
        inner_loop_n=100, seed_pct=28, seed_mode=1, w_hid_mag=0, trim_hid_mag=0,
        hadamard_delay_us=nominal_delay
    )
    time.sleep(0.05)
    client.center_compensation_weights()
    time.sleep(0.05)

    # Read Vector A baseline
    init_telem = get_averaged_telemetry(client, n_avg=4)
    x_ref_a = list(init_telem["x_ref"])
    z_target_a = list(init_telem["z_target"])
    w_m33_static = init_telem["w_m33"]
    w_m3_start = init_telem["w_m3"]
    w_m8_start = init_telem["w_m8"]

    print(f"[*] Locked Vector A: {x_ref_a}")
    print(f"[*] Target A (Z_target): {z_target_a}")
    print(f"[*] Starting Centered M8 Diag: {[w_m8_start[i][i] for i in range(6)]}")
    print(f"[*] Starting Centered M3 Diag: {[w_m3_start[i][i] for i in range(6)]}")

    epoch_records = []
    start_time = time.time()

    # Log initial Epoch 0
    init_rec = {
        "epoch": 0,
        "phase": "VECTOR_A_INIT",
        "vector_id": "A",
        "time_s": 0.0,
        "rmse_lsb": init_telem["rmse_lsb"],
        "enob_bits": init_telem["enob_bits"],
        "loss_lsb2": init_telem["loss_lsb2"],
        "window_mean_rmse_lsb": init_telem["rmse_lsb"],
        "window_mean_enob_bits": init_telem["enob_bits"],
        "x_ref": x_ref_a,
        "z_target": z_target_a,
        "adc45": init_telem["adc45"],
        "adc49": init_telem["adc49"],
        "err49": init_telem["err49"],
        "w_m3": w_m3_start,
        "w_m8": w_m8_start,
        "w_m33": w_m33_static,
        "w8_diag": [w_m8_start[i][i] for i in range(6)],
        "w3_diag": [w_m3_start[i][i] for i in range(6)],
        "strata_samples": [],
    }
    epoch_records.append(init_rec)
    print(f"\n[Epoch   0] Initial Baseline RMSE: {init_telem['rmse_lsb']:6.2f} LSB | ENOB: {init_telem['enob_bits']:4.2f} bits | M8: {init_rec['w8_diag']}")

    current_vector_id = "A"
    current_x_ref = x_ref_a
    current_z_target = z_target_a

    for ep in range(1, total_epochs + 1):
        # Check for Switchover to Vector B
        if ep == epochs_a + 1:
            print("\n" + "=" * 78)
            print(f">>> [EPOCH {ep} SWITCHOVER]: GENERATING NEW VECTOR B (INDEPENDENT TASK)")
            print(f">>> Vector A Final M8 Diag: {epoch_records[-1]['w8_diag']}")
            print(f">>> Vector A was: {x_ref_a}")

            # Draw a fresh, locked Vector B WITHOUT touching M3 or M8 weights (True Catastrophic Forgetting test!)
            client._send_binary(MAML_CMD_RAND_DATA, struct.pack("<B", 2))
            time.sleep(0.05)

            # Read new telemetry to capture Vector B
            sw_telem = get_averaged_telemetry(client, n_avg=4)
            x_ref_b = list(sw_telem["x_ref"])
            z_target_b = list(sw_telem["z_target"])
            current_vector_id = "B"
            current_x_ref = x_ref_b
            current_z_target = z_target_b

            print(f">>> Vector B is : {x_ref_b}")
            print(f">>> Target B (Z_target): {z_target_b}")
            print(f">>> Vector B Initial RMSE: {sw_telem['rmse_lsb']:6.2f} LSB (ENOB: {sw_telem['enob_bits']:4.2f} bits)")
            print("=" * 78 + "\n")

        # 1. Fisher-Yates shuffle the sampling order of the strata
        shuffled_strata = strata_us.copy()
        np.random.shuffle(shuffled_strata)

        strata_samples = []
        for t_us in shuffled_strata:
            client.set_config(
                mode=0, jumper_mode=3, led_switches=3, max_meas_win_pct=100, hadamard_khz=500,
                inner_loop_n=100, seed_pct=28, seed_mode=1, w_hid_mag=0, trim_hid_mag=0,
                hadamard_delay_us=int(t_us)
            )
            time.sleep(0.015)
            s_telem = get_averaged_telemetry(client, n_avg=2)
            strata_samples.append({
                "t_us": int(t_us),
                "adc45": s_telem["adc45"],
                "adc49": s_telem["adc49"],
                "err49": s_telem["err49"],
                "rmse_lsb": s_telem["rmse_lsb"],
                "enob_bits": s_telem["enob_bits"],
            })

        # 2. Perform 1 weight update step at nominal settled delay
        client.set_config(
            mode=0, jumper_mode=3, led_switches=3, max_meas_win_pct=100, hadamard_khz=500,
            inner_loop_n=100, seed_pct=28, seed_mode=1, w_hid_mag=0, trim_hid_mag=0,
            hadamard_delay_us=nominal_delay
        )
        time.sleep(0.01)
        client._send_binary(MAML_CMD_STEP_OUTER)
        time.sleep(0.025)

        # 3. Measure post-update telemetry
        post_telem = get_averaged_telemetry(client, n_avg=3)
        elapsed = time.time() - start_time

        mean_strata_rmse = float(np.mean([s["rmse_lsb"] for s in strata_samples]))
        mean_strata_enob = max(0.0, 11.0 - math.log2(max(mean_strata_rmse, 1.0)))

        rec = {
            "epoch": ep,
            "phase": f"VECTOR_{current_vector_id}",
            "vector_id": current_vector_id,
            "time_s": round(elapsed, 2),
            "rmse_lsb": post_telem["rmse_lsb"],
            "enob_bits": post_telem["enob_bits"],
            "loss_lsb2": post_telem["loss_lsb2"],
            "window_mean_rmse_lsb": round(mean_strata_rmse, 2),
            "window_mean_enob_bits": round(mean_strata_enob, 2),
            "x_ref": current_x_ref,
            "z_target": current_z_target,
            "adc45": post_telem["adc45"],
            "adc49": post_telem["adc49"],
            "err49": post_telem["err49"],
            "w_m3": post_telem["w_m3"],
            "w_m8": post_telem["w_m8"],
            "w_m33": w_m33_static,
            "w8_diag": post_telem["w8_diag"],
            "w3_diag": post_telem["w3_diag"],
            "strata_samples": strata_samples,
        }
        epoch_records.append(rec)

        if ep % 5 == 0 or ep == 1 or ep == epochs_a or ep == epochs_a + 1 or ep == total_epochs:
            tag = f"[VECTOR {current_vector_id}]"
            print(
                f"[Epoch {ep:2d}/{total_epochs}] {tag} "
                f"Nom 5ms RMSE: {post_telem['rmse_lsb']:6.2f} LSB ({post_telem['enob_bits']:4.2f}b) | "
                f"Win Mean: {mean_strata_rmse:6.2f} LSB ({mean_strata_enob:4.2f}b) | "
                f"M3: {post_telem['w3_diag']} | M8: {post_telem['w8_diag']}"
            )

    total_time = round(time.time() - start_time, 2)
    print(f"\n[+] Sequential Transfer Experiment complete in {total_time} s ({total_epochs} epochs).")

    # 4. Forensic Topography Correlation Analysis (Active 6x6 Deltas from Baseline)
    w8_0 = np.array(epoch_records[0]["w_m8"])[:6, :6]
    w8_a_final = np.array(epoch_records[epochs_a]["w_m8"])[:6, :6]
    w8_b_final = np.array(epoch_records[-1]["w_m8"])[:6, :6]
    w3_0 = np.array(epoch_records[0]["w_m3"])[:6, :6]
    w3_a_final = np.array(epoch_records[epochs_a]["w_m3"])[:6, :6]
    w3_b_final = np.array(epoch_records[-1]["w_m3"])[:6, :6]

    dw8_a = (w8_a_final - w8_0).flatten()
    dw8_b = (w8_b_final - w8_0).flatten()
    corr_w8 = float(np.corrcoef(dw8_a, dw8_b)[0, 1]) if (np.std(dw8_a) > 1e-6 and np.std(dw8_b) > 1e-6) else 0.0

    dw3_a = (w3_a_final - w3_0).flatten()
    dw3_b = (w3_b_final - w3_0).flatten()
    corr_w3 = float(np.corrcoef(dw3_a, dw3_b)[0, 1]) if (np.std(dw3_a) > 1e-6 and np.std(dw3_b) > 1e-6) else 0.0

    print("\n" + "=" * 78)
    print(">>> TOPOGRAPHICAL CORRELATION ANALYSIS (Active 6x6 ΔW, Vector A vs Vector B):")
    print(f">>> Matrix 8 (Vernier ΔW8) Topographical Correlation: r = {corr_w8:+.4f}")
    print(f">>> Matrix 3 (Hidden  ΔW3) Topographical Correlation: r = {corr_w3:+.4f}")
    print(f">>> Vector A Final M3 Diag: {epoch_records[epochs_a]['w3_diag']} | M8 Diag: {epoch_records[epochs_a]['w8_diag']}")
    print(f">>> Vector B Final M3 Diag: {epoch_records[-1]['w3_diag']} | M8 Diag: {epoch_records[-1]['w8_diag']}")
    print("=" * 78 + "\n")

    dataset = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "target": f"{host}:{port}",
            "experiment": "sequential_vector_transfer_40plus40",
            "epochs_total": total_epochs,
            "epochs_a": epochs_a,
            "epochs_b": epochs_b,
            "switch_epoch": epochs_a,
            "vector_a_x_ref": x_ref_a,
            "vector_b_x_ref": x_ref_b,
            "corr_w8": round(corr_w8, 4),
            "corr_w3": round(corr_w3, 4),
            "t_min_ms": t_min_ms,
            "t_max_ms": t_max_ms,
            "num_strata": num_strata,
            "strata_delays_us": strata_us,
            "nominal_delay_us": nominal_delay,
            "total_time_seconds": total_time,
        },
        "static_weights": {
            "w_m33": w_m33_static,
            "w_m3_start": w_m3_start,
            "w_m8_start": w_m8_start,
        },
        "epochs": epoch_records,
    }

    out_file = Path(output_filename)
    if out_file.is_absolute():
        out_path = out_file
    elif len(out_file.parts) > 1:
        out_path = REPO_ROOT / out_file
    else:
        out_path = OUT_DIR / out_file
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(dataset, f, indent=2)

    print(f"[+] Full telemetry saved to: {out_path}")
    return dataset


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inverted MAML Sequential Transfer Experiment (40+40 Epochs)")
    parser.add_argument("--host", default="192.168.1.50", help="FPGA Host IP")
    parser.add_argument("--port", type=int, default=5000, help="UDP Port")
    parser.add_argument("--epochs-a", type=int, default=40, help="Epochs on Vector A (default: 40)")
    parser.add_argument("--epochs-b", type=int, default=40, help="Epochs on Vector B (default: 40)")
    parser.add_argument("--t-min", type=float, default=4.9, help="Min delay in ms (default: 4.9)")
    parser.add_argument("--t-max", type=float, default=5.1, help="Max delay in ms (default: 5.1)")
    parser.add_argument("--strata", type=int, default=5, help="Number of temporal strata (default: 5)")
    parser.add_argument("--out", default="mode_a_40plus40_sequential_transfer.json", help="Output JSON filename")
    args = parser.parse_args()

    run_sequential_transfer_experiment(
        host=args.host,
        port=args.port,
        epochs_a=args.epochs_a,
        epochs_b=args.epochs_b,
        t_min_ms=args.t_min,
        t_max_ms=args.t_max,
        num_strata=args.strata,
        output_filename=args.out,
    )

