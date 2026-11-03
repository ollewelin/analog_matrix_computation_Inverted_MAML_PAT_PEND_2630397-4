#!/home/olle/anaconda3/bin/python
"""
run_500ep_1strata_5ms_rev2.py
Inverted MAML (Patent Pending SE 2630397-4) - Open Science Hardware

500-Epoch Mode A Training on Rev 2.0 Silicon (1k/3.9k Attenuator & T20A Companion):
- Evaluated strictly at single-point t = 5.0 ms (num_strata = 1, t_min = 5000 us, t_max = 5000 us)
- Milestone 2 style single-stratum pure spatial non-linear matrix compensation
- Full +/-80 LSB zero-mean colored input swing (COLOR_LLM_TOEPLITZ, rho = 0.85)
- Schedule:
    * Epochs   0..99 : Baseline Zero (W = 0 LSB, LR = 0, Reg = 0)
    * Epochs 100..199: Calibrated Smart Baseline tuned for Rev 2.0 sweet spot:
                       W8_diag = [-28, -16, +6, 0, -10, +6] LSB
    * Epochs 200..500: Active Closed-Loop Training ON (LR = 0.08x, L2 Reg lambda = 1024)
"""

from __future__ import annotations
import sys
import time
import json
import math
import struct
import argparse
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

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
from FPGA_code.scripts.verify_and_guard_version import ensure_version_guard

LOG_DIR = REPO_ROOT / "FPGA_code" / "logs" / "mode_a_extended_training"
LOG_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR = REPO_ROOT / "FPGA_code" / "docs" / "figures"
DOCS_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACT_DIR = Path("/home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a")


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
        "clamped_count": clamped_count,
        "w8_diag": list(t.w8_diag),
        "w3_diag": list(t.w3_diag),
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
    parser = argparse.ArgumentParser(description="500-Epoch Mode A Training at 1 Stratum (5.0 ms Only) on Rev 2.0 Silicon")
    parser.add_argument("--host", default="192.168.1.50")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--epochs", type=int, default=500)
    parser.add_argument("--k-batch", type=int, default=20)
    parser.add_argument("--lr", type=float, default=0.08)
    parser.add_argument("--reg-lambda", type=int, default=1024)
    parser.add_argument("--rho", type=float, default=0.85)
    parser.add_argument("--tag", default="rev2_1k3p9k_1strata_5ms_t20a")
    args = parser.parse_args()

    ensure_version_guard(host=args.host, port=args.port)

    client = MamlUdpClient(host=args.host, port=args.port, timeout=5.0)

    print("=" * 105)
    print("INVERTED MAML 500-EPOCH 1-STRATUM (t = 5.0 ms ONLY) TRAINING (Rev 2.0 PCB, 1k/3.9k Attenuator)")
    print("=" * 105)
    print(f"Target: {args.host}:{args.port} | Epochs: {args.epochs} | Batch K: {args.k_batch} @ 5000 µs (1 Stratum)")
    print(f"Noise Mode: COLOR_LLM_TOEPLITZ (rho={args.rho}) with Full ±80 LSB Zero-Mean Proportional Swing")
    print(f"Phase 1 (Ep   0.. 99): Baseline Zero (W=0 LSB, LR=0, Reg=0)")
    print(f"Phase 2 (Ep 100..199): Rev 2.0 Tuned Smart Baseline (W8_diag=[-28, -16, 6, 0, -10, 6], LR=0, Reg=0)")
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

    for ep in range(1, args.epochs + 1):
        if ep < 100:
            lr_q16 = 0
            reg_q16 = 0
            phase = "BASELINE_ZERO"
        elif ep < 200:
            lr_q16 = 0
            reg_q16 = 0
            phase = "REV2_SMART_BASELINE"
        else:
            lr_q16 = lr_active_q16
            reg_q16 = args.reg_lambda
            phase = "ACTIVE_TRAINING"

        if ep == 100:
            print("=" * 105)
            print(f">>> [EPOCH 100]: ACTIVATING REV 2.0 CALIBRATED SMART BASELINE ON M3 & M8! (LR=0, Reg=0)")
            print("=" * 105)
            m3_rev2 = [
                [-24,   0,  +8,  -8,  +8,  -8],
                [  0, -24,  -8,  +8,  -8,  +8],
                [ +8,  +8, +24,   0,  +8,  -8],
                [ -8,  -8,   0, +24,  -8,  +8],
                [ +8,  +8,  -8,  +8, -24,   0],
                [ -8,  -8,  +8,  -8,   0, +24],
                [-16, -16, +16, +16, -16, +16],
                [+16, +16, -16, -16, +16, -16],
            ]
            m8_rev2 = [
                [-28,   0,  +4,  -4,  +4,  -4],
                [  0, -16,  -4,  +4,  -4,  +4],
                [ +4,  +4,  +6,   0,  +4,  -4],
                [ -4,  -4,   0,   0,  -4,  +4],
                [ +4,  +4,  -4,  +4, -10,   0],
                [ -4,  -4,  +4,  -4,   0,  +6],
                [ -8,   0,   0,  -8,   0,  +8],
            ]
            flat_m3 = [v for row in m3_rev2 for v in row]
            flat_m8 = [v for row in m8_rev2 for v in row]
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
                f"W8: {rec['w8_diag']} | Clamped: {rec['clamped_count']} | Elapsed: {elapsed:.1f}s"
            )

    elapsed_total = time.time() - t_start
    print("=" * 105)
    print(f"[+] 500-Epoch Experiment Completed in {elapsed_total:.1f} seconds ({elapsed_total/60:.2f} minutes)!")

    # Summary Statistics
    p1 = [r for r in records if 0 <= r["epoch"] < 100]
    p2 = [r for r in records if 100 <= r["epoch"] < 200]
    p3 = [r for r in records if 200 <= r["epoch"] <= 500]

    p1_loss_mean = float(np.mean([r["loss_lsb2"] for r in p1]))
    p1_enob_mean = float(np.mean([r["enob_bits"] for r in p1]))

    p2_loss_mean = float(np.mean([r["loss_lsb2"] for r in p2]))
    p2_enob_mean = float(np.mean([r["enob_bits"] for r in p2]))

    p3_loss_mean = float(np.mean([r["loss_lsb2"] for r in p3]))
    p3_enob_mean = float(np.mean([r["enob_bits"] for r in p3]))

    p3_best_rec = min(p3, key=lambda r: r["loss_lsb2"])

    print(f"\n--- EMPIRICAL COMPARISON SUMMARY (1 Stratum @ 5.0 ms, Rev 2.0 Silicon) ---")
    print(f"Phase 1 (Baseline 0,     Ep   0.. 99): Mean Loss = {p1_loss_mean:8.1f} LSB² | Mean ENOB = {p1_enob_mean:.2f} bits")
    print(f"Phase 2 (Rev 2.0 Smart,  Ep 100..199): Mean Loss = {p2_loss_mean:8.1f} LSB² | Mean ENOB = {p2_enob_mean:.2f} bits")
    print(f"Phase 3 (Active Training, Ep 200..500): Mean Loss = {p3_loss_mean:8.1f} LSB² | Mean ENOB = {p3_enob_mean:.2f} bits")
    print(f"Phase 3 Best Nominal Snapshot : Epoch {p3_best_rec['epoch']} | Loss = {p3_best_rec['loss_lsb2']:.1f} LSB² | ENOB = {p3_best_rec['enob_bits']:.2f} bits | RMSE = {p3_best_rec['rmse_lsb']:.2f} LSB | W8 = {p3_best_rec['w8_diag']}")

    # Save JSON log
    out_json = LOG_DIR / f"mode_a_500ep_1strata_5ms_{args.tag}.json"
    full_output = {
        "metadata": {
            "title": "500-Epoch Mode A Training at 1 Stratum (5.0 ms Only) on Rev 2.0 Silicon",
            "patent": "SE 2630397-4",
            "hardware": "Revision 2.0 PCB (1k/3.9k ColTIA attenuator, verified T20A companion)",
            "host": args.host,
            "port": args.port,
            "epochs": args.epochs,
            "k_batch": args.k_batch,
            "num_strata": 1,
            "t_min_us": 5000,
            "t_max_us": 5000,
            "lr": args.lr,
            "reg_lambda": args.reg_lambda,
            "rho": args.rho,
            "elapsed_seconds": round(elapsed_total, 1),
            "summary": {
                "phase1_mean_loss": round(p1_loss_mean, 1),
                "phase1_mean_enob": round(p1_enob_mean, 2),
                "phase2_mean_loss": round(p2_loss_mean, 1),
                "phase2_mean_enob": round(p2_enob_mean, 2),
                "phase3_mean_loss": round(p3_loss_mean, 1),
                "phase3_mean_enob": round(p3_enob_mean, 2),
                "phase3_best_epoch": p3_best_rec["epoch"],
                "phase3_best_loss": p3_best_rec["loss_lsb2"],
                "phase3_best_enob": p3_best_rec["enob_bits"],
                "phase3_best_rmse": p3_best_rec["rmse_lsb"],
                "phase3_best_w8": p3_best_rec["w8_diag"],
            },
        },
        "epochs": records,
    }

    out_json.write_text(json.dumps(full_output, indent=2))
    print(f"\n[+] Saved detailed telemetry log to {out_json}")

    # Generate 3-Panel Trajectory Plot
    epochs = [r["epoch"] for r in records]
    loss_vals = [r["loss_lsb2"] for r in records]
    enob_vals = [r["enob_bits"] for r in records]
    w8_vals = np.array([r["w8_diag"] for r in records])

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 10), sharex=True, dpi=180)
    plt.subplots_adjust(hspace=0.18, top=0.92)

    for ax in (ax1, ax2, ax3):
        ax.axvspan(0, 100, color="#dbeafe", alpha=0.38)
        ax.axvspan(100, 200, color="#fee2e2", alpha=0.38)
        ax.axvspan(200, 500, color="#dcfce7", alpha=0.38)
        ax.axvline(100, color="#b45309", linestyle="--", linewidth=1.5, alpha=0.85)
        ax.axvline(200, color="#15803d", linestyle="--", linewidth=1.8, alpha=0.95)
        ax.grid(True, linestyle="--", alpha=0.45)

    # Panel 1: Loss
    ax1.plot(epochs, loss_vals, color="#1d4ed8", linewidth=1.4, label="5.0 ms Single-Point Loss (LSB²)")
    ax1.hlines(p1_loss_mean, 0, 100, colors="#1e293b", linestyles="--", linewidth=2.0)
    ax1.hlines(p2_loss_mean, 100, 200, colors="#9a3412", linestyles="--", linewidth=2.0)
    ax1.hlines(p3_loss_mean, 200, 500, colors="#065f46", linestyles="--", linewidth=2.2)
    ax1.set_ylabel("Quadratic Loss (LSB²)", fontsize=10.5, fontweight="bold")
    ax1.set_title("500-Epoch Mode A Training at 1 Stratum (5.0 ms Nominal Center Snapshot) on Rev 2.0 Silicon", fontsize=12.5, fontweight="bold")
    ax1.legend(loc="upper right", fontsize=8.5)

    # Panel 2: ENOB
    ax2.plot(epochs, enob_vals, color="#047857", linewidth=1.4, label="5.0 ms Center Snapshot ENOB (bits)")
    ax2.hlines(p1_enob_mean, 0, 100, colors="#1e293b", linestyles="--", linewidth=2.0)
    ax2.hlines(p2_enob_mean, 100, 200, colors="#9a3412", linestyles="--", linewidth=2.0)
    ax2.hlines(p3_enob_mean, 200, 500, colors="#065f46", linestyles="--", linewidth=2.2)
    ax2.axhline(6.0, color="#dc2626", linestyle=":", linewidth=1.5, alpha=0.85, label="6.0-Bit Target Threshold")
    ax2.set_ylabel("ENOB (Bits)", fontsize=10.5, fontweight="bold")
    ax2.legend(loc="upper left", fontsize=8.5)

    # Panel 3: Weights
    colors_c = ["#1e293b", "#0284c7", "#16a34a", "#eab308", "#ea580c", "#9333ea"]
    for c in range(6):
        ax3.plot(epochs, w8_vals[:, c], color=colors_c[c], linewidth=1.5, label=f"Col {c}")
    ax3.axhline(120, color="#dc2626", linestyle="--", linewidth=1.0, alpha=0.75, label="±120 LSB Clamp")
    ax3.axhline(-120, color="#dc2626", linestyle="--", linewidth=1.0, alpha=0.75)
    ax3.set_ylim(-135, 135)
    ax3.set_xlabel("Epoch (Each Epoch = 20 Vectors @ 5000 µs, ±80 LSB Colored Toeplitz Excitation)", fontsize=10.5, fontweight="bold")
    ax3.set_ylabel("M8 Diagonal Weight (LSB)", fontsize=10.5, fontweight="bold")
    ax3.legend(loc="upper left", ncol=4, fontsize=8.2)

    fig_out = DOCS_DIR / f"fig_mode_a_500ep_1strata_5ms_{args.tag}.png"
    fig.savefig(fig_out, dpi=180, bbox_inches="tight")
    if ARTIFACT_DIR.exists():
        fig.savefig(ARTIFACT_DIR / fig_out.name, dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(f"[+] Saved summary plot to {fig_out}")

    client.close()


if __name__ == "__main__":
    main()

