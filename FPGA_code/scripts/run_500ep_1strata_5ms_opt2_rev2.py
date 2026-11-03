#!/home/olle/anaconda3/bin/python
"""
run_500ep_1strata_5ms_opt2_rev2.py
500-Epoch Pure Single-Stratum (t = 5.0 ms Only) Mode A Training Run on Revision 2.0 Silicon
Executing Option 2: Software DC Offset Centering & Headroom Lift.

Experiment Phases:
  - Phase 1 (Epochs   0.. 99): Baseline Zero (W = 0 LSB, LR = 0, Reg = 0)
  - Phase 2 (Epochs 100..199): Option 2 Calibrated Smart Baseline (LR = 0, Reg = 0)
  - Phase 3 (Epochs 200..500): Active Inverted MAML Training (LR = 0.08x, lambda = 1024, K = 20)
"""

from __future__ import annotations
import sys
import time
import math
import json
import struct
import argparse
from pathlib import Path
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from gui.udp_client import (
    MamlUdpClient,
    MAML_CMD_GET_TELEMETRY,
    MAML_CMD_CENTER_WEIGHTS,
    MAML_CMD_BATCH_STEP,
    COLOR_LLM_TOEPLITZ,
)


def ensure_version_guard(host: str = "192.168.1.50", port: int = 5000):
    client = MamlUdpClient(host=host, port=port, timeout=1.0)
    v = client.get_versions()
    client.close()
    print(f"[*] Version Guard: HW={v.get('hw_version', 'N/A')} ({v.get('hw_id', 'N/A')}) | SW={v.get('sw_version', 'N/A')}")


def run_identical_batch_epoch(
    client: MamlUdpClient,
    k_batch: int,
    num_strata: int,
    t_min_us: int,
    t_max_us: int,
    lr_q16: int,
    reg_q16: int,
) -> dict:
    pkt = struct.pack(
        "<BBHHHH",
        k_batch,
        num_strata,
        t_min_us,
        t_max_us,
        lr_q16,
        reg_q16,
    )
    raw = None
    for attempt in range(10):
        raw = client._send_binary(MAML_CMD_BATCH_STEP, pkt)
        if raw is not None and len(raw) >= client.TELEM_SIZE:
            break
        time.sleep(0.05 * (attempt + 1))

    if raw is None or len(raw) < client.TELEM_SIZE:
        raise RuntimeError("Failed to receive MAML_CMD_BATCH_STEP telemetry from T120.")

    u = struct.unpack(client.TELEM_FMT, raw[:client.TELEM_SIZE])
    loss_total_milli = u[64]
    loss_baseline_milli = u[65]

    total_samples = max(1, k_batch * num_strata)
    mean_loss_lsb2 = (loss_total_milli / 1000.0) / total_samples
    mean_rmse_lsb = math.sqrt(max(0.0, mean_loss_lsb2 * 2.0 / 6.0))
    mean_enob_bits = max(0.0, 11.0 - math.log2(max(mean_rmse_lsb, 1.0)))

    base_loss_lsb2 = (loss_baseline_milli / 1000.0) / total_samples
    base_rmse_lsb = math.sqrt(max(0.0, base_loss_lsb2 * 2.0 / 6.0))
    base_enob_bits = max(0.0, 11.0 - math.log2(max(base_rmse_lsb, 1.0)))

    window_metrics = {
        "mean_loss_lsb2": round(mean_loss_lsb2, 1),
        "mean_rmse_lsb": round(mean_rmse_lsb, 2),
        "mean_enob_bits": round(mean_enob_bits, 2),
        "baseline_loss_lsb2": round(base_loss_lsb2, 1),
        "baseline_rmse_lsb": round(base_rmse_lsb, 2),
        "baseline_enob_bits": round(base_enob_bits, 2),
        "samples_evaluated": total_samples,
    }

    t = client._parse_hw_telemetry(raw)
    err = np.array(t.adc49_sig, dtype=np.float64) - np.array(t.z_target, dtype=np.float64)
    loss_lsb2 = float(0.5 * np.sum(err ** 2))
    rmse_lsb = float(np.sqrt(np.mean(err ** 2)))
    enob_bits = max(0.0, 11.0 - math.log2(max(rmse_lsb, 1.0)))

    flat_m3 = [w for row in t.w_m3 for w in row]
    flat_m8 = [w for row in t.w_m8 for w in row]
    clamped_count = sum(1 for w in (flat_m3 + flat_m8) if abs(w) >= 120)

    return {
        "loss_lsb2": round(loss_lsb2, 1),
        "rmse_lsb": round(rmse_lsb, 2),
        "enob_bits": round(enob_bits, 2),
        "w8_diag": [t.w_m8[i][i] for i in range(6)],
        "w3_diag": [t.w_m3[i][i] for i in range(6)],
        "w8_row6": [t.w_m8[6][c] for c in range(6)],
        "w3_row6": [t.w_m3[6][c] for c in range(6)],
        "w3_row7": [t.w_m3[7][c] for c in range(6)],
        "clamped_count": clamped_count,
        "w_m3": [list(row) for row in t.w_m3],
        "w_m8": [list(row) for row in t.w_m8],
        "w_m33": [list(row) for row in t.w_m33],
        "adc45": list(t.adc45_sig),
        "adc49": list(t.adc49_sig),
        "z_target": list(t.z_target),
        "x_ref": list(t.ref_x),
        "window_eval": window_metrics,
    }


def main():
    parser = argparse.ArgumentParser(description="500-Epoch Mode A Training at 1 Stratum (5.0 ms Only) - Option 2 DC Centering")
    parser.add_argument("--host", default="192.168.1.50")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--epochs", type=int, default=500)
    parser.add_argument("--k-batch", type=int, default=20)
    parser.add_argument("--lr", type=float, default=0.08)
    parser.add_argument("--reg-lambda", type=int, default=1024)
    parser.add_argument("--rho", type=float, default=0.85)
    parser.add_argument("--tag", default="rev2_opt2_dc_lift_1strata_5ms")
    args = parser.parse_args()

    ensure_version_guard(host=args.host, port=args.port)

    client = MamlUdpClient(host=args.host, port=args.port, timeout=5.0)

    print("=" * 105)
    print("INVERTED MAML 500-EPOCH 1-STRATUM (t = 5.0 ms ONLY) OPTION 2 RUN (Rev 2.0 PCB, 1k/3.9k Attenuator)")
    print("=" * 105)
    print(f"Target: {args.host}:{args.port} | Epochs: {args.epochs} | Batch K: {args.k_batch} @ 5000 µs (1 Stratum)")
    print(f"Noise Mode: COLOR_LLM_TOEPLITZ (rho={args.rho}) with Full ±80 LSB Zero-Mean Proportional Swing")
    print(f"Phase 1 (Ep   0.. 99): Baseline Zero (W=0 LSB, LR=0, Reg=0)")
    print(f"Phase 2 (Ep 100..199): Option 2 Calibrated Smart Baseline (DC-Centered Bias Rows, LR=0, Reg=0)")
    print(f"Phase 3 (Ep 200..500): Active Inverted MAML Training (LR={args.lr:.2f}x, lambda={args.reg_lambda})")
    print("=" * 105)

    client.set_gain_experiment(d_line=1, w33=1, target_gain=1.0, clamp=120)
    time.sleep(0.04)

    client.set_config(
        mode=0,
        jumper_mode=3,
        led_switches=3,
        max_meas_win_pct=100,
        hadamard_khz=500,
        inner_loop_n=100,
        seed_pct=28,
        seed_mode=1,
        w_hid_mag=0,
        trim_hid_mag=0,
        hadamard_delay_us=5000,
        lr_inner_q16=0,
    )
    time.sleep(0.04)

    client.set_data_color(COLOR_LLM_TOEPLITZ, args.rho)
    client.set_regularization(0)
    time.sleep(0.04)

    # Stage 1 Init (Epoch 0): Baseline 0 (W = 0 LSB)
    print(f"[*] Stage 1 Init: Setting Baseline 0 (W = 0 LSB) on M3 & M8...")
    client._send_binary(MAML_CMD_CENTER_WEIGHTS, struct.pack("<B", 0))
    time.sleep(0.06)

    lr_active_q16 = int(round(1024 * args.lr))

    records = []
    t_start = time.time()

    # Pre-epoch 0 baseline telemetry
    t0 = run_identical_batch_epoch(client, args.k_batch, 1, 5000, 5000, 0, 0)
    t0["epoch"] = 0
    t0["phase"] = "BASELINE_ZERO"
    t0["lr"] = 0.0
    t0["reg_lambda"] = 0
    t0["num_strata"] = 1
    t0["t_min"] = 5000
    t0["t_max"] = 5000
    t0["samples_evaluated"] = args.k_batch
    records.append(t0)

    print(f"[Ep   0] Init W=0 | Loss: {t0['loss_lsb2']:8.1f} LSB² | RMSE: {t0['rmse_lsb']:5.2f} LSB | ENOB: {t0['enob_bits']:.2f} b | W8: {t0['w8_diag']}")

    # Calibrated Option 2 Smart Baseline weights
    m3_opt2 = [
        [-24,   0,  +8,  -8,  +8, -24],
        [  0, -24,  -8,  +8,  -8,  +8],
        [ +8,  +8, +24,   0,  +8,  -8],
        [ -8,  -8,   0, +24,  -8,  +8],
        [ +8,  +8,  -8,  +8, -24,   0],
        [ -8,  -8,  +8,  -8,   0, -24],
        [-16, -16, +16, +16, -16, -24],
        [+16, +16, -16, -16, +16, +16],
    ]
    m8_opt2 = [
        [-28,   0,  +4,  -4,  +4, -28],
        [  0, -16,  -4,  +4,  -4,  +4],
        [ +4,  +4,  +6,   0,  +4,  -4],
        [ -4,  -4,   0,   0,  -4,  +4],
        [ +4,  +4,  -4,  +4, -10,   0],
        [ -4,  -4,  +4,  -4,   0, -28],
        [ -80,  65,   0,  -7, -38, +30],
    ]

    for ep in range(1, args.epochs + 1):
        if ep < 100:
            lr_q16 = 0
            reg_q16 = 0
            phase = "BASELINE_ZERO"
        elif ep < 200:
            lr_q16 = 0
            reg_q16 = 0
            phase = "REV2_OPT2_SMART_BASELINE"
        else:
            lr_q16 = lr_active_q16
            reg_q16 = args.reg_lambda
            phase = "ACTIVE_TRAINING"

        if ep == 100:
            print("=" * 105)
            print(f">>> [EPOCH 100]: ACTIVATING OPTION 2 CALIBRATED SMART BASELINE ON M3 & M8! (LR=0, Reg=0)")
            print(f">>> M8 Bias Row 6: {m8_opt2[6]}")
            print("=" * 105)
            flat_m3 = [v for row in m3_opt2 for v in row]
            flat_m8 = [v for row in m8_opt2 for v in row]
            client._send_binary(MAML_CMD_CENTER_WEIGHTS, struct.pack("<B48b42b", 1, *flat_m3, *flat_m8))
            client.set_regularization(0)
            time.sleep(0.04)

        elif ep == 200:
            print("=" * 105)
            print(f">>> [EPOCH 200]: ACTIVE TRAINING ON! SINGLE-STRATUM 5.0 ms (K={args.k_batch}, λ={args.reg_lambda}, LR={args.lr:.2f}x)")
            print("=" * 105)
            client.set_regularization(args.reg_lambda)
            time.sleep(0.03)

        rec = run_identical_batch_epoch(
            client=client,
            k_batch=args.k_batch,
            num_strata=1,
            t_min_us=5000,
            t_max_us=5000,
            lr_q16=lr_q16,
            reg_q16=reg_q16,
        )

        rec["epoch"] = ep
        rec["phase"] = phase
        rec["lr"] = args.lr if ep >= 200 else 0.0
        rec["reg_lambda"] = args.reg_lambda if ep >= 200 else 0
        rec["num_strata"] = 1
        rec["t_min"] = 5000
        rec["t_max"] = 5000
        rec["samples_evaluated"] = args.k_batch
        records.append(rec)

        if ep in [1, 25, 50, 75, 99, 100, 125, 150, 175, 199, 200, 225, 250, 275, 300, 350, 400, 450, 500] or (ep > 200 and ep % 20 == 0):
            elapsed = time.time() - t_start
            print(
                f"[Ep {ep:3d}/500 | {phase[:12]:12s}] 5.0ms: {rec['loss_lsb2']:8.1f} LSB² ({rec['enob_bits']:.2f} b, RMSE {rec['rmse_lsb']:5.2f}) | "
                f"W8: {rec['w8_diag']} | Clamped: {rec['clamped_count']} | Elapsed: {elapsed:.1f}s",
                flush=True
            )

    elapsed_total = time.time() - t_start
    print("=" * 105)
    print(f"[+] 500-Epoch Option 2 Run Completed in {elapsed_total:.1f} seconds ({elapsed_total/500:.3f} s/epoch)")

    # Save to JSON
    log_dir = REPO_ROOT / "FPGA_code" / "logs" / "mode_a_extended_training"
    log_dir.mkdir(parents=True, exist_ok=True)
    out_json = log_dir / f"mode_a_500ep_1strata_5ms_{args.tag}.json"

    meta = {
        "tag": args.tag,
        "pcb_revision": "Revision 2.0 (Dual FPGA T120 Master + T20 Companion)",
        "companion_fpga": "Trion T20A (ACK=0x06)",
        "attenuator": "1 kOhm / 3.9 kOhm (High-Headroom Passive Summer)",
        "option": "Option 2: Software DC Offset Centering & Headroom Lift",
        "m8_bias_row6": m8_opt2[6],
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_epochs": args.epochs,
        "k_batch": args.k_batch,
        "learning_rate": args.lr,
        "reg_lambda": args.reg_lambda,
        "rho": args.rho,
        "noise_mode": "COLOR_LLM_TOEPLITZ",
        "hadamard_delay_us": 5000,
        "num_strata": 1,
        "elapsed_seconds": round(elapsed_total, 2),
    }

    out_data = {
        "metadata": meta,
        "epochs": records,
    }

    with open(out_json, "w") as f:
        json.dump(out_data, f, indent=2)

    print(f"[+] Saved complete telemetry records to: {out_json}")
    client.close()


if __name__ == "__main__":
    main()

