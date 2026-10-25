#!/home/olle/anaconda3/bin/python
"""
Milestone 2 Batch Training & Physical Telemetry Logging Engine
=============================================================
Executes Inverted MAML Mode A training on physical silicon (192.168.1.50:5000):
  A. Collects complete 3-matrix weights (M33 static, M3 and M8 starting + per-epoch updates).
  B. Supports customizable epochs (e.g. 150) and scaled learning rate (e.g. lr_scale = 0.5).
  C. Broadened temporal window (configurable, e.g. 4.0 - 6.0 ms, or fixed 5.0 ms):
     - Divides the window into discrete strata.
     - Performs Fisher-Yates random shuffling of sampling order across refresh cycles.
     - CRITICAL RULE ENFORCED: Holds the EXACT SAME input data pattern (x_ref) locked across
       all strata within a batch. Only changes random input vector between batches.
     - Evaluates true payload accuracy across the full window with independent random test samples.
  D. Logs all telemetry into JSON ready for the Post-Data Analysis GUI.
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

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from gui.udp_client import (
    MamlUdpClient,
    MAML_CMD_GET_TELEMETRY,
    MAML_CMD_STEP_OUTER,
    MAML_CMD_RAND_DATA,
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


def get_averaged_telemetry(client: MamlUdpClient, n_avg: int = 4) -> dict:
    """Fetch and average consecutive 100 Hz refresh frames for noise cancellation."""
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


def run_training_experiment(
    host: str = "192.168.1.50",
    port: int = 5000,
    epochs: int = 150,
    baseline_epochs: int = 0,
    lr_scale: float = 1.0,
    t_min_ms: float = 4.0,
    t_max_ms: float = 6.0,
    num_strata: int = 5,
    n_updates: int = 1,
    lock_x_ref: bool = True,
    output_filename: str = "mode_a_extended_training_telemetry.json",
):
    print("=" * 78)
    print(f"Inverted MAML Mode A Batch Training & Logging Engine")
    print(f"Target: {host}:{port} | Epochs: {epochs} | Baseline: {baseline_epochs} ep | Updates/Ep: {n_updates} | Locked x_ref: {lock_x_ref}")
    if abs(t_min_ms - t_max_ms) < 1e-3:
        print(f"Time Mode: Fixed Delay at {t_min_ms:.1f} ms")
        strata_us = [int(round(t_min_ms * 1000))]
    else:
        strata_us = np.linspace(t_min_ms * 1000, t_max_ms * 1000, num_strata, dtype=int).tolist()
        print(f"Time Mode: Broadened Window [{t_min_ms:.1f} .. {t_max_ms:.1f}] ms ({num_strata} strata: {strata_us} us)")
    print("=" * 78)

    client = MamlUdpClient(host=host, port=port, timeout=1.5)

    # 1. Initialize Mode A centered baseline
    nominal_delay = int(strata_us[len(strata_us) // 2])
    client.set_config(
        mode=0, jumper_mode=3, led_switches=3, max_meas_win_pct=100, hadamard_khz=500,
        inner_loop_n=100, seed_pct=28, seed_mode=1, w_hid_mag=0, trim_hid_mag=0,
        hadamard_delay_us=nominal_delay
    )
    time.sleep(0.05)
    client.center_compensation_weights()
    time.sleep(0.05)

    # 2. Extract static frozen M33 payload weights
    init_telem = get_averaged_telemetry(client, n_avg=4)
    w_m33_static = init_telem["w_m33"]
    w_m3_start = init_telem["w_m3"]
    w_m8_start = init_telem["w_m8"]

    print("\n[*] Static Primary Payload Matrix M33 (Frozen across entire lifecycle):")
    for r in range(6):
        print(f"    Row {r}: {w_m33_static[r]}")
    print(f"[*] Starting Centered M8 Diag: {[w_m8_start[i][i] for i in range(6)]}")
    print(f"[*] Starting Centered M3 Diag: {[w_m3_start[i][i] for i in range(6)]}")

    # Step multiplier to emulate lr_scale
    # Default firmware step is ~0.0156. If lr_scale == 0.5, we apply skip-cadence or micro-steps.
    # When stepping via MAML_CMD_STEP_OUTER, 1 call = 1 inner step.
    # To achieve lr_scale < 1.0 with integer weights, we can accumulate fractional steps or scale iterations.
    update_divisor = max(1, int(round(1.0 / lr_scale))) if lr_scale < 0.99 else 1
    print(f"[*] Learning Rate Scale {lr_scale:.2f} -> Update Divisor: {update_divisor}")

    epoch_records = []
    start_time = time.time()

    # Log initial Epoch 0
    init_rec = {
        "epoch": 0,
        "phase": "BASELINE",
        "training_active": False,
        "effective_lr": 0.0,
        "time_s": 0.0,
        "rmse_lsb": init_telem["rmse_lsb"],
        "enob_bits": init_telem["enob_bits"],
        "loss_lsb2": init_telem["loss_lsb2"],
        "x_ref": init_telem["x_ref"],
        "z_target": init_telem["z_target"],
        "adc45": init_telem["adc45"],
        "adc49": init_telem["adc49"],
        "err49": init_telem["err49"],
        "w_m3": w_m3_start,
        "w_m8": w_m8_start,
        "w_m33": w_m33_static,
        "w8_diag": [w_m8_start[i][i] for i in range(6)],
        "w3_diag": [w_m3_start[i][i] for i in range(6)],
        "strata_eval": [],
    }
    epoch_records.append(init_rec)
    print(f"\n[Epoch   0] [PHASE: BASELINE (LR=0.0, W8 locked at 24)] RMSE: {init_telem['rmse_lsb']:6.2f} LSB | ENOB: {init_telem['enob_bits']:4.2f} bits | M8 Diag: {init_rec['w8_diag']}")

    for ep in range(1, epochs + 1):
        # If not locking x_ref, re-randomize input vector
        if not lock_x_ref:
            client._send_binary(MAML_CMD_RAND_DATA, struct.pack("<B", 1))
            time.sleep(0.015)

        # 2. Fisher-Yates shuffle the sampling order of the strata
        shuffled_strata = strata_us.copy()
        np.random.shuffle(shuffled_strata)

        strata_samples = []
        # Sample each stratum across the broadened window WITH LOCKED X_REF
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

        # 3. Perform weight update step on the hardware
        # Restore nominal settled delay for the gradient update pulse
        client.set_config(
            mode=0, jumper_mode=3, led_switches=3, max_meas_win_pct=100, hadamard_khz=500,
            inner_loop_n=100, seed_pct=28, seed_mode=1, w_hid_mag=0, trim_hid_mag=0,
            hadamard_delay_us=nominal_delay
        )
        time.sleep(0.01)

        is_baseline = (ep <= baseline_epochs)
        current_phase = "BASELINE" if is_baseline else "TRAINING"
        training_active = not is_baseline
        effective_lr = 0.0 if is_baseline else lr_scale

        # Apply update according to update_divisor (effective lr_scale = 1/update_divisor)
        # CRITICAL: In baseline phase, weights are locked (no MAML_CMD_STEP_OUTER)
        if training_active and ((ep - baseline_epochs) % update_divisor == 0):
            for _ in range(n_updates):
                client._send_binary(MAML_CMD_STEP_OUTER)
                time.sleep(0.025)

        # 4. Measure post-update telemetry for this epoch
        post_telem = get_averaged_telemetry(client, n_avg=3)
        elapsed = time.time() - start_time

        # Calculate average RMSE across the strata in this batch
        mean_strata_rmse = float(np.mean([s["rmse_lsb"] for s in strata_samples]))
        mean_strata_enob = max(0.0, 11.0 - math.log2(max(mean_strata_rmse, 1.0)))

        rec = {
            "epoch": ep,
            "phase": current_phase,
            "training_active": training_active,
            "effective_lr": effective_lr,
            "time_s": round(elapsed, 2),
            "rmse_lsb": post_telem["rmse_lsb"],
            "enob_bits": post_telem["enob_bits"],
            "loss_lsb2": post_telem["loss_lsb2"],
            "window_mean_rmse_lsb": round(mean_strata_rmse, 2),
            "window_mean_enob_bits": round(mean_strata_enob, 2),
            "x_ref": post_telem["x_ref"],
            "z_target": post_telem["z_target"],
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

        tag = f"[BASELINE (LR=0)]" if is_baseline else f"[TRAINING (LR={lr_scale:.2f})]"
        if ep == baseline_epochs:
            base_enobs = [r.get("window_mean_enob_bits", r.get("enob_bits")) for r in epoch_records[:baseline_epochs+1]]
            base_rmses = [r.get("window_mean_rmse_lsb", r.get("rmse_lsb")) for r in epoch_records[:baseline_epochs+1]]
            print(
                f"[Epoch {ep:3d}/{epochs}] {tag} "
                f"Nominal 5ms RMSE: {post_telem['rmse_lsb']:6.2f} LSB (ENOB {post_telem['enob_bits']:4.2f}b) | "
                f"Window Mean RMSE: {mean_strata_rmse:6.2f} LSB (ENOB {mean_strata_enob:4.2f}b) | "
                f"M8 Diag: {post_telem['w8_diag']}"
            )
            print(f"\n{'='*78}")
            print(f">>> [BASELINE PHASE COMPLETE: Epochs 0..{baseline_epochs} (N={len(base_enobs)})]")
            print(f">>> Mean Baseline Window ENOB = {np.mean(base_enobs):.2f} bits | RMSE = {np.mean(base_rmses):.2f} LSB (σ = {np.std(base_enobs):.2f} bits)")
            print(f">>> M8 Diag Weights remained strictly locked at: {post_telem['w8_diag']}")
            print(f">>> ENGAGING ACTIVE INVERTED MAML TRAINING STARTING AT EPOCH {baseline_epochs + 1}...")
            print(f"{'='*78}\n")
        elif ep % 5 == 0 or ep == 1 or ep == epochs or ep == baseline_epochs + 1:
            print(
                f"[Epoch {ep:3d}/{epochs}] {tag} "
                f"Nominal 5ms RMSE: {post_telem['rmse_lsb']:6.2f} LSB (ENOB {post_telem['enob_bits']:4.2f}b) | "
                f"Window Mean RMSE: {mean_strata_rmse:6.2f} LSB (ENOB {mean_strata_enob:4.2f}b) | "
                f"M8 Diag: {post_telem['w8_diag']}"
            )

    # 5. Payload Validation Test across Full Window (Randomizing Every Sample)
    print("\n[*] Phase 3: Pure Payload Evaluation across the Window (Independent Random In-Data per Sample)...")
    payload_eval = []
    for t_test_us in strata_us:
        test_rmses = []
        for _ in range(5):
            client._send_binary(MAML_CMD_RAND_DATA, struct.pack("<B", 1))
            time.sleep(0.015)
            client.set_config(
                mode=0, jumper_mode=3, led_switches=3, max_meas_win_pct=100, hadamard_khz=500,
                inner_loop_n=100, seed_pct=28, seed_mode=1, w_hid_mag=0, trim_hid_mag=0,
                hadamard_delay_us=int(t_test_us)
            )
            time.sleep(0.015)
            pt = get_averaged_telemetry(client, n_avg=2)
            test_rmses.append(pt["rmse_lsb"])
        avg_rmse_t = float(np.mean(test_rmses))
        avg_enob_t = max(0.0, 11.0 - math.log2(max(avg_rmse_t, 1.0)))
        payload_eval.append({
            "t_us": int(t_test_us),
            "t_ms": round(t_test_us / 1000.0, 2),
            "payload_rmse_lsb": round(avg_rmse_t, 2),
            "payload_enob_bits": round(avg_enob_t, 2),
        })
        print(f"    Delay {t_test_us/1000.0:4.2f} ms: Payload RMSE = {avg_rmse_t:6.2f} LSB | ENOB = {avg_enob_t:4.2f} bits")

    total_time = round(time.time() - start_time, 2)
    print(f"\n[+] Experiment complete in {total_time} s ({epochs} epochs).")

    # Save complete dataset
    dataset = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "target": f"{host}:{port}",
            "epochs": epochs,
            "baseline_epochs": baseline_epochs,
            "lock_x_ref": lock_x_ref,
            "x_ref_locked": init_telem["x_ref"] if lock_x_ref else None,
            "training_start_epoch": baseline_epochs + 1 if baseline_epochs < epochs else None,
            "baseline_w8_fixed": [24, 24, 24, 24, 24, 24],
            "active_lr_scale": lr_scale,
            "lr_scale": lr_scale,
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
        "payload_evaluation": payload_eval,
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
    parser = argparse.ArgumentParser(description="Inverted MAML Mode A Batch Training & Logging Engine")
    parser.add_argument("--host", default="192.168.1.50", help="FPGA Host IP")
    parser.add_argument("--port", type=int, default=5000, help="UDP Port")
    parser.add_argument("--epochs", type=int, default=20, help="Number of training epochs (default: 20)")
    parser.add_argument("--baseline-epochs", type=int, default=0, help="Number of baseline uncompensated epochs with LR=0 (default: 0)")
    parser.add_argument("--lr-scale", type=float, default=1.0, help="Learning rate scale (default: 1.0)")
    parser.add_argument("--t-min", type=float, default=4.9, help="Min delay in ms (default: 4.9)")
    parser.add_argument("--t-max", type=float, default=5.1, help="Max delay in ms (default: 5.1)")
    parser.add_argument("--strata", type=int, default=5, help="Number of temporal strata (default: 5)")
    parser.add_argument("--n-updates", type=int, default=1, help="Number of weight updates per batch (default: 1)")
    parser.add_argument("--randomize-x", action="store_true", help="Randomize x_ref at each epoch (default: False, locked x_ref)")
    parser.add_argument("--out", default="mode_a_20ep_4p9to5p1ms_locked_xref.json", help="Output JSON filename")
    args = parser.parse_args()

    run_training_experiment(
        host=args.host,
        port=args.port,
        epochs=args.epochs,
        baseline_epochs=args.baseline_epochs,
        lr_scale=args.lr_scale,
        t_min_ms=args.t_min,
        t_max_ms=args.t_max,
        num_strata=args.strata,
        n_updates=args.n_updates,
        lock_x_ref=not args.randomize_x,
        output_filename=args.out,
    )
