#!/usr/bin/env python3
"""
run_500ep_1strata_5ms_old_board.py
==================================
Inverted MAML (Patent Pending SE 2630397-4) - Open Science Hardware

500-Epoch Pure Single-Stratum (t = 5.0 ms ONLY) Training on Old Board (Rev 1.4, 1k/5.1k Attenuator)
using the CURRENT SPI flash binaries:
  - FPGA_code/T20_Custom/outflow/T20F256.hex
  - FPGA_code/T120F324/outflow/T120_MALM.hex

Purpose:
  Diagnostic comparison to determine if previous poorer results on Rev 2.0 were caused
  by the new hardware (1k/3.9k) or if the current T20/T120 firmware behaves identically here.

Protocol:
  - 15s warm-up burst to thermally stabilize newly powered board
  - Single-stratum t = 5.0 ms (num_strata = 1, t_min = 5000 us, t_max = 5000 us)
  - Full +/-80 LSB zero-mean colored input swing (COLOR_LLM_TOEPLITZ, rho = 0.85)
  - Schedule:
      * Epochs   0..99 : Baseline Zero (W = 0 LSB, LR = 0, Reg = 0)
      * Epochs 100..199: Calibrated Smart Baseline for Old Board (W8_diag = [-20, -20, 20, 20, -20, 20])
      * Epochs 200..500: Active Training ON (LR = 0.08x, L2 Reg lambda = 1024, Batch K = 20)
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
    loss_total_milli = u[29]
    loss_baseline_milli = u[30]

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
    parser = argparse.ArgumentParser(description="500-Epoch Mode A Training on Old Board (1k/5.1k) with Current Hex")
    parser.add_argument("--host", default="192.168.1.50")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--epochs", type=int, default=500)
    parser.add_argument("--k-batch", type=int, default=20)
    parser.add_argument("--lr", type=float, default=0.08)
    parser.add_argument("--reg-lambda", type=int, default=1024)
    parser.add_argument("--rho", type=float, default=0.85)
    parser.add_argument("--warmup-sec", type=float, default=15.0)
    args = parser.parse_args()

    ensure_version_guard(host=args.host, port=args.port)

    client = MamlUdpClient(host=args.host, port=args.port, timeout=5.0)

    print("=" * 105)
    print("INVERTED MAML: 500-EPOCH 1-STRATUM (t = 5.0 ms ONLY) ON OLD BOARD (1k/5.1k Attenuator)")
    print("=" * 105)
    print(f"Target: {args.host}:{args.port} | Epochs: {args.epochs} | Batch K: {args.k_batch} @ 5000 µs (1 Stratum)")
    print(f"Noise Mode: COLOR_LLM_TOEPLITZ (rho={args.rho}) with Full ±80 LSB Zero-Mean Proportional Swing")
    print(f"Firmware Tested: CURRENT T20 (T20F256.hex) & CURRENT T120 (T120_MALM.hex)")
    print(f"Phase 1 (Ep   0.. 99): Baseline Zero (W=0 LSB, LR=0, Reg=0)")
    print(f"Phase 2 (Ep 100..199): Old Board Calibrated Baseline (W8_diag=[-20, -20, 20, 20, -20, 20], LR=0, Reg=0)")
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

    # Pre-warm burst since board is freshly booted
    if args.warmup_sec > 0:
        print(f"[*] Pre-warming physical silicon ({args.warmup_sec:.0f}s burst to thermally stabilize cold board)...")
        t_w_start = time.time()
        pkt_dummy = struct.pack("<BBHHHH", 10, 1, 5000, 5000, 0, 0)
        while time.time() - t_w_start < args.warmup_sec:
            client._send_binary(MAML_CMD_BATCH_STEP, pkt_dummy)
            time.sleep(0.05)
        print("[+] Pre-warm burst complete! Silicon thermal equilibrium achieved.")

    # Phase 1 Init (Epoch 0): Baseline 0 (W = 0 LSB)
    print(f"[*] Phase 1 Init: Setting Baseline 0 (W = 0 LSB) on M3 & M8...")
    client._send_binary(MAML_CMD_CENTER_WEIGHTS, struct.pack("<B", 0))
    client.set_regularization(0)
    time.sleep(0.05)

    lr_inner_q16 = max(32, min(4096, int(round(1024 * args.lr))))

    t_start = time.time()
    records = []

    # Calibrated Old Board Smart Baseline Matrices
    m3_rev14 = [
        [-24,   0,  +8,  -8,  +8,  -8],
        [  0, -24,  -8,  +8,  -8,  +8],
        [ +8,  +8, +24,   0,  +8,  -8],
        [ -8,  -8,   0, +24,  -8,  +8],
        [ +8,  +8,  -8,  +8, -24,   0],
        [ -8,  -8,  +8,  -8,   0, +24],
        [-16, -16, +16, +16, -16, +16],
        [+16, +16, -16, -16, +16, -16],
    ]
    m8_rev14 = [
        [-20,   0,  +6,  -6,  +6,  -6],
        [  0, -20,  -6,  +6,  -6,  +6],
        [ +6,  +6, +20,   0,  +6,  -6],
        [ -6,  -6,   0, +20,  -6,  +6],
        [ +6,  +6,  -6,  +6, -20,   0],
        [ -6,  -6,  +6,  -6,   0, +20],
        [  0, +16, -16, -16, +16, -16],
    ]
    flat_m3 = [v for row in m3_rev14 for v in row]
    flat_m8 = [v for row in m8_rev14 for v in row]

    for ep in range(0, args.epochs + 1):
        if ep < 100:
            phase = "BASELINE_ZERO"
            lr_q16 = 0
            reg_q16 = 0
        elif ep < 200:
            phase = "SMART_BASELINE"
            lr_q16 = 0
            reg_q16 = 0
        else:
            phase = "ACTIVE_TRAINING"
            lr_q16 = lr_inner_q16
            reg_q16 = args.reg_lambda

        if ep == 100:
            print("=" * 105)
            print(f">>> [EPOCH 100]: ACTIVATING OLD BOARD CALIBRATED SMART BASELINE ON M3 & M8! (LR=0, Reg=0)")
            print("=" * 105)
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

        if ep in [0, 1, 25, 50, 75, 99, 100, 125, 150, 175, 199, 200, 225, 250, 275, 300, 350, 400, 450, 500] or (ep > 200 and ep % 20 == 0):
            elapsed = time.time() - t_start
            print(
                f"[Ep {ep:3d}/500 | {phase[:12]:12s}] 5.0ms: {rec['loss_lsb2']:8.1f} LSB² ({rec['enob_bits']:.2f} b, RMSE {rec['rmse_lsb']:5.2f}) | "
                f"W8: {rec['w8_diag']} | Clamped: {rec['clamped_count']} | Elapsed: {elapsed:.1f}s",
                flush=True
            )

    elapsed_total = time.time() - t_start
    print("=" * 105)
    print(f"[+] 500-Epoch Training Complete in {elapsed_total:.1f} seconds ({elapsed_total/500:.3f} s/epoch)")

    p1 = [r for r in records if r["epoch"] < 100]
    p2 = [r for r in records if 100 <= r["epoch"] < 200]
    p3 = [r for r in records if r["epoch"] >= 200]

    p1_mean = float(np.mean([r["loss_lsb2"] for r in p1]))
    p2_mean = float(np.mean([r["loss_lsb2"] for r in p2]))
    p3_mean = float(np.mean([r["loss_lsb2"] for r in p3]))

    best_p3 = min(p3, key=lambda r: r["loss_lsb2"])
    best_enob_p3 = max(p3, key=lambda r: r["enob_bits"])

    print(f"[*] Phase 1 (W=0) Mean Loss: {p1_mean:.1f} LSB²")
    print(f"[*] Phase 2 (Smart) Mean Loss: {p2_mean:.1f} LSB²")
    print(f"[*] Phase 3 (Active) Mean Loss: {p3_mean:.1f} LSB²")
    print(f"[*] Best Phase 3 Epoch: Ep {best_p3['epoch']} with Loss = {best_p3['loss_lsb2']:.1f} LSB² | ENOB = {best_p3['enob_bits']:.2f} b")
    print(f"[*] Peak ENOB: Ep {best_enob_p3['epoch']} with ENOB = {best_enob_p3['enob_bits']:.2f} b | Loss = {best_enob_p3['loss_lsb2']:.1f} LSB²")
    print("=" * 105)

    log_path = LOG_DIR / "mode_a_500ep_1strata_5ms_old_board_1k5p1k_current_hex.json"
    with open(log_path, "w") as f:
        json.dump({"hardware": "Old Board (Rev 1.4, 1k/5.1k)", "epochs": records}, f, indent=2)
    print(f"[+] Saved telemetry log: {log_path}")

    # Generate Quick 3-Panel Plot
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 9), sharex=True, dpi=180)
    plt.subplots_adjust(hspace=0.18, top=0.92)

    epochs = [r["epoch"] for r in records]
    losses = [r["loss_lsb2"] for r in records]
    enobs = [r["enob_bits"] for r in records]
    w8_arr = np.array([r["w8_diag"] for r in records])

    for ax in (ax1, ax2, ax3):
        ax.axvspan(0, 100, color="#dbeafe", alpha=0.35)
        ax.axvspan(100, 200, color="#fee2e2", alpha=0.35)
        ax.axvspan(200, 500, color="#dcfce7", alpha=0.35)
        ax.axvline(100, color="#b45309", linestyle="--", linewidth=1.2)
        ax.axvline(200, color="#15803d", linestyle="--", linewidth=1.5)
        ax.grid(True, linestyle="--", alpha=0.4)

    ax1.plot(epochs, losses, color="#1d4ed8", linewidth=1.3)
    ax1.set_ylabel("Loss [LSB²]", fontsize=10, fontweight="bold")
    ax1.set_title(f"Old Board (Rev 1.4, 1k/5.1k) 5.0ms: Ph1={p1_mean:.0f}, Ph2={p2_mean:.0f}, Ph3={p3_mean:.0f} LSB² (Best Ep {best_p3['epoch']}: {best_p3['loss_lsb2']:.1f} LSB²)", fontsize=10.5, fontweight="bold")

    ax2.plot(epochs, enobs, color="#047857", linewidth=1.3)
    ax2.set_ylabel("ENOB [bits]", fontsize=10, fontweight="bold")
    ax2.set_title(f"Effective Resolution: Peak = {best_enob_p3['enob_bits']:.2f} bits (Ep {best_enob_p3['epoch']})", fontsize=10.5, fontweight="bold")

    colors_w = ["#1e293b", "#0284c7", "#16a34a", "#eab308", "#ea580c", "#9333ea"]
    for c in range(6):
        ax3.plot(epochs, w8_arr[:, c], color=colors_w[c], linewidth=1.3, label=f"M8[{c},{c}]")
    ax3.axhline(120, color="#dc2626", linestyle="--", linewidth=0.8)
    ax3.axhline(-120, color="#dc2626", linestyle="--", linewidth=0.8)
    ax3.set_ylabel("W8 Diag [LSB]", fontsize=10, fontweight="bold")
    ax3.set_xlabel("Epoch", fontsize=10, fontweight="bold")
    ax3.legend(loc="upper left", ncol=6, fontsize=7.5)

    fig.suptitle("INVERTED MAML: Old Board (Rev 1.4, 1k/5.1k) Diagnostic Evaluation with Current T20/T120 Hex",
                 fontsize=12, fontweight="bold")

    plot_path = DOCS_DIR / "fig_mode_a_500ep_old_board_1k5p1k_current_hex.png"
    fig.savefig(plot_path, dpi=180, bbox_inches="tight")
    if ARTIFACT_DIR.exists():
        fig.savefig(ARTIFACT_DIR / plot_path.name, dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(f"[+] Saved comparison plot: {plot_path}")


if __name__ == "__main__":
    main()

