#!/home/olle/anaconda3/bin/python
"""
run_500ep_broadened_window_k20.py
Inverted MAML (Patent Pending SE 2630397-4) - Open Science Hardware

100% Identical-Cadence 500-Epoch Physical Silicon Experiment:
- Every single epoch (0..500) executes MAML_CMD_BATCH_STEP across K=20 vectors x 10 strata
  ([4500 .. 5500] µs = 200 physical capacitor refreshes & 200 full Hadamard bursts per epoch).
- Identical EMC, identical thermal load, identical Hadamard switching, and identical 200-sample
  window Loss/RMSE/ENOB measurement across ALL epochs!
- Schedule (ONLY difference between phases is Baseline & LR/Reg ON vs OFF):
    * Epochs   0..99 : Baseline Zero (W = 0 LSB, LR = 0, Reg = 0, Full Hadamard ON)
    * Epochs 100..199: Calibrated Smart Baseline (W = Smart Knee, LR = 0, Reg = 0, Full Hadamard ON)
    * Epochs 200..500: Active Training ON (K=20, 10 Strata, LR = 0.25x, L2 Reg λ = 1024, Full Hadamard ON)
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
    """
    Executes MAML_CMD_BATCH_STEP on physical T120 silicon for ANY epoch (Training OFF when lr_q16=0, reg_q16=0;
    Training ON when lr_q16>0).
    In all cases, the T120 executes k_batch * num_strata (20 * 10 = 200) capacitor refreshes across
    [t_min_us .. t_max_us], fires 200 full Hadamard bursts, accumulates the exact 200-sample quadratic
    error sum into loss_total_milli, and reads settled 5.0 ms telemetry at the end of the batch.
    """
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
    loss_total_milli = float(u[29])  # Hardware-accumulated mean of sum_{j=0..5} err49[j]^2 across all 200 samples!
    t = client._parse_hw_telemetry(raw)

    # 1. Exact 200-sample (20 vectors x 10 strata [4.5..5.5 ms]) Window Metrics (with full Hadamard active)
    win_loss = loss_total_milli / 2.0
    win_rmse = math.sqrt(loss_total_milli / 6.0)
    win_enob = max(0.0, 11.0 - math.log2(max(win_rmse, 1.0)))

    # 2. Settled 5.0 ms Center Snapshot Metrics at end of batch
    adc45_arr = np.array(t.adc45_sig, dtype=np.float64)
    adc49_arr = np.array(t.adc49_sig, dtype=np.float64)
    z_target_arr = np.array(t.z_target, dtype=np.float64)
    err49 = adc49_arr - z_target_arr
    nom_rmse = float(np.sqrt(np.mean(err49 ** 2)))
    nom_loss = float(np.sum(err49 ** 2) / 2.0)
    nom_enob = max(0.0, 11.0 - math.log2(max(nom_rmse, 1.0)))

    return {
        "loss_lsb2": round(nom_loss, 1),
        "rmse_lsb": round(nom_rmse, 2),
        "enob_bits": round(nom_enob, 2),
        "x_ref": [int(v) for v in t.x_ref],
        "z_target": [int(v) for v in t.z_target],
        "adc45": [int(v) for v in t.adc45_sig],
        "adc49": [int(v) for v in t.adc49_sig],
        "err49": [int(round(v)) for v in err49],
        "w_m3": t.w_m3,
        "w_m8": t.w_m8,
        "w_m33": t.w_m33,
        "w8_diag": [t.w_m8[i][i] for i in range(6)],
        "w3_diag": [t.w_m3[i][i] for i in range(6)],
        "color_mode": t.color_mode,
        "color_rho": t.color_rho,
        "w33_is_custom": t.w33_is_custom,
        "window_eval": {
            "mean_loss_lsb2": round(win_loss, 1),
            "mean_rmse_lsb": round(win_rmse, 2),
            "mean_enob_bits": round(win_enob, 2),
            "samples_per_epoch": k_batch * num_strata,
        },
    }


def main():
    parser = argparse.ArgumentParser(description="500-Epoch Mode A Training with Identical 200-Sample Batch Cadence Across All Phases")
    parser.add_argument("--host", default="192.168.1.50")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--epochs", type=int, default=500)
    parser.add_argument("--k-batch", type=int, default=20)
    parser.add_argument("--lr", type=float, default=0.25)
    parser.add_argument("--reg-lambda", type=int, default=1024)
    parser.add_argument("--rho", type=float, default=0.85)
    parser.add_argument("--t-min", type=int, default=4500)
    parser.add_argument("--t-max", type=int, default=5500)
    parser.add_argument("--num-strata", type=int, default=10)
    parser.add_argument("--tag", type=str, default="", help="Optional tag for output files")
    args = parser.parse_args()

    print("=" * 105)
    print("INVERTED MAML: 500-EPOCH IDENTICAL-CADENCE BROADENED WINDOW [4.5 - 5.5 ms] EXPERIMENT")
    print(f"Target: {args.host}:{args.port} | Epochs: {args.epochs} | Batch K: {args.k_batch} x {args.num_strata} Strata = {args.k_batch * args.num_strata} Hadamard Samples/Ep")
    print(f"Window: [{args.t_min} .. {args.t_max}] µs | Active LR: {args.lr:.2f}x | L2 Reg: λ = {args.reg_lambda} | Spatial ρ: {args.rho:.2f}")
    print("=" * 105)

    ensure_version_guard(host=args.host, port=args.port)

    client = MamlUdpClient(host=args.host, port=args.port, timeout=6.0)

    # 1. Reset gain knobs
    client.set_gain_experiment(d_line=1, w33=1, target_gain=1.0, clamp=120)
    time.sleep(0.03)

    # 2. Configure initial Mode A: Training OFF (mode=0), LEDs ON, jumper_mode=3
    lr_inner_q16 = max(32, min(4096, int(round(1024 * args.lr))))
    client.set_config(
        mode=0, jumper_mode=3, led_switches=3, max_meas_win_pct=100, hadamard_khz=500,
        inner_loop_n=100, seed_pct=28, seed_mode=1, w_hid_mag=0, trim_hid_mag=0,
        hadamard_delay_us=5000, lr_inner_q16=lr_inner_q16
    )
    time.sleep(0.03)

    # Turn LEDs ON
    client._send_binary(0x13, struct.pack("<BB", 1, 1))
    time.sleep(0.02)

    # 3. Configure Noise Equalizer to LLM Toeplitz with specified rho
    print(f"[*] Setting In-Data Equalizer to LLM_TOEPLITZ (mode={COLOR_LLM_TOEPLITZ}, rho={args.rho})...")
    client.set_data_color(COLOR_LLM_TOEPLITZ, args.rho)
    time.sleep(0.03)

    # 4. Phase 1 Init (Epoch 0..99): Baseline 0 (W = 0 LSB, Center Zero, Training OFF)
    print(f"[*] Stage 1 Init: Setting Baseline 0 (W = 0 LSB) on M3 & M8 (LR=0, Reg=0, Full Hadamard ON)...")
    client._send_binary(MAML_CMD_CENTER_WEIGHTS, struct.pack("<B", 0))
    client.set_regularization(0)
    time.sleep(0.05)

    if args.num_strata > 1:
        strata_us_list = [int(round(args.t_min + i * (args.t_max - args.t_min) / (args.num_strata - 1))) for i in range(args.num_strata)]
    else:
        strata_us_list = [args.t_min]
    print(f"[*] Window Strata ({len(strata_us_list)} points, {args.k_batch} vecs each = {args.k_batch * len(strata_us_list)} samples/ep): {strata_us_list}")

    t_start = time.time()

    # Epoch 0: Execute full 200-sample batch with lr=0, reg=0
    t0 = run_identical_batch_epoch(client, args.k_batch, args.num_strata, args.t_min, args.t_max, lr_q16=0, reg_q16=0)
    eval0 = t0["window_eval"]

    print(f"  Ep   0 [BASE 0   ]: 200-Sample Win: Loss={eval0['mean_loss_lsb2']:.1f} LSB² | RMSE={eval0['mean_rmse_lsb']:.2f} LSB | ENOB={eval0['mean_enob_bits']:.2f} b")
    print(f"                    5.0ms Snapshot: Loss={t0['loss_lsb2']:.1f} LSB² | RMSE={t0['rmse_lsb']:.2f} LSB | ENOB={t0['enob_bits']:.2f} b | W8={t0['w8_diag']}")
    print("-" * 105)
    print(f"{'Ep #':<6} {'Phase':<15} {'Reg':<5} | {'Nom Loss':<10} | {'Nom RMSE':<9} | {'Nom ENOB':<9} | {'Win Loss':<10} | {'Win ENOB':<9} | {'W8 Diag (Cols 0..5)':<23}")
    print("-" * 105)

    records = [{
        "epoch": 0,
        "phase": "BASELINE_ZERO",
        "lr_q16": 0,
        "reg_lambda_q16": 0,
        "batch_k": args.k_batch,
        "t_min_us": args.t_min,
        "t_max_us": args.t_max,
        "num_strata": args.num_strata,
        **t0,
    }]

    best_loss = t0["loss_lsb2"]
    best_ep = 0
    best_enob = t0["enob_bits"]
    best_win_enob = eval0["mean_enob_bits"]

    w3_flat_0 = np.array(t0["w_m3"])[:6, :6].flatten()
    w8_flat_0 = np.array(t0["w_m8"])[:6, :6].flatten()

    for ep in range(1, args.epochs + 1):
        if ep < 100:
            phase = "BASELINE_ZERO"
            cur_lr_q16 = 0
            cur_reg = 0
        elif ep < 200:
            phase = "BASELINE_FIXED"
            cur_lr_q16 = 0
            cur_reg = 0
        else:
            phase = "TRAIN_REG_ON"
            cur_lr_q16 = lr_inner_q16
            cur_reg = args.reg_lambda

        # Phase switchover triggers
        if ep == 100:
            print("=" * 105)
            print(f">>> [EPOCH 100]: ACTIVATING CALIBRATED SMART BASELINE ON M3 & M8! (LR=0, Reg=0, Full Hadamard ON)")
            print("=" * 105)
            m3_bal = [
                [-24,   0,  +8,  -8,  +8,  -8],
                [  0, -24,  -8,  +8,  -8,  +8],
                [ +8,  +8, +24,   0,  +8,  -8],
                [ -8,  -8,   0, +24,  -8,  +8],
                [ +8,  +8,  -8,  +8, -24,   0],
                [ -8,  -8,  +8,  -8,   0, +24],
                [-16, -16, +16, +16, -16, +16],
                [+16, +16, -16, -16, +16, -16],
            ]
            m8_bal = [
                [-20,   0,  +6,  -6,  +6,  -6],
                [  0, -20,  -6,  +6,  -6,  +6],
                [ +6,  +6, +20,   0,  +6,  -6],
                [ -6,  -6,   0, +20,  -6,  +6],
                [ +6,  +6,  -6,  +6, -20,   0],
                [ -6,  -6,  +6,  -6,   0, +20],
                [  0, +16, -16, -16, +16, -16],
            ]
            flat_m3 = [v for row in m3_bal for v in row]
            flat_m8 = [v for row in m8_bal for v in row]
            client._send_binary(MAML_CMD_CENTER_WEIGHTS, struct.pack("<B48b42b", 1, *flat_m3, *flat_m8))
            client.set_regularization(0)
            time.sleep(0.04)
        elif ep == 200:
            print("=" * 105)
            print(f">>> [EPOCH 200]: ACTIVE TRAINING ON! BROADENED WINDOW [{args.t_min}..{args.t_max} µs] BATCH (K={args.k_batch}, λ={args.reg_lambda}, LR={args.lr:.2f}x)")
            print("=" * 105)
            client.set_regularization(args.reg_lambda)
            time.sleep(0.03)

        # Execute the EXACT SAME 200-sample (20 vectors x 10 strata) Hadamard-active batch step on EVERY epoch!
        t_cur = run_identical_batch_epoch(
            client,
            args.k_batch,
            args.num_strata,
            args.t_min,
            args.t_max,
            lr_q16=cur_lr_q16,
            reg_q16=cur_reg,
        )
        eval_cur = t_cur["window_eval"]

        # Weight correlation metrics
        w3_flat = np.array(t_cur["w_m3"])[:6, :6].flatten()
        w8_flat = np.array(t_cur["w_m8"])[:6, :6].flatten()
        r3 = float(np.corrcoef(w3_flat_0, w3_flat)[0, 1]) if (np.std(w3_flat) > 1e-6 and np.std(w3_flat_0) > 1e-6) else 1.0
        r8 = float(np.corrcoef(w8_flat_0, w8_flat)[0, 1]) if (np.std(w8_flat) > 1e-6 and np.std(w8_flat_0) > 1e-6) else 1.0

        rec = {
            "epoch": ep,
            "phase": phase,
            "lr_q16": cur_lr_q16,
            "reg_lambda_q16": cur_reg,
            "batch_k": args.k_batch,
            "t_min_us": args.t_min,
            "t_max_us": args.t_max,
            "num_strata": args.num_strata,
            "r_m3": round(r3, 4),
            "r_m8": round(r8, 4),
            **t_cur,
        }
        records.append(rec)

        if t_cur["loss_lsb2"] < best_loss:
            best_loss = t_cur["loss_lsb2"]
            best_ep = ep
        if t_cur["enob_bits"] > best_enob:
            best_enob = t_cur["enob_bits"]
        if eval_cur["mean_enob_bits"] > best_win_enob:
            best_win_enob = eval_cur["mean_enob_bits"]

        if ep % 20 == 0 or ep == 1 or ep == 100 or ep == 200 or ep == args.epochs:
            dt = time.time() - t_start
            rate = ep / max(dt, 0.001)
            eta = (args.epochs - ep) / max(rate, 0.001)
            print(
                f"  Ep {ep:3d} {phase:<15} {cur_reg:<5d} | "
                f"{t_cur['loss_lsb2']:<10.1f} | {t_cur['rmse_lsb']:<9.2f} | {t_cur['enob_bits']:<9.2f} | "
                f"{eval_cur['mean_loss_lsb2']:<10.1f} | {eval_cur['mean_enob_bits']:<9.2f} | "
                f"{str(t_cur['w8_diag']):<23} "
                f"({rate:.2f} ep/s, ETA {eta/60:.1f}m)"
            )

    client.close()
    total_time = time.time() - t_start

    print("=" * 105)
    print(f"[EXPERIMENT COMPLETE] Total Time: {total_time:.1f} s ({total_time/60:.1f} min)")
    print(f"Best Nominal 5ms Loss: {best_loss:.1f} LSB² (Ep {best_ep}) | Best Nominal ENOB: {best_enob:.2f} b | Best Window ENOB: {best_win_enob:.2f} b")
    print(f"Final Nominal 5ms Loss: {records[-1]['loss_lsb2']:.1f} LSB² | Final Nominal ENOB: {records[-1]['enob_bits']:.2f} b | Final Window ENOB: {records[-1]['window_eval']['mean_enob_bits']:.2f} b")
    print("=" * 105)

    if args.t_min == 4900 and args.t_max == 5100:
        win_tag = "plateau_4p9to5p1ms"
    elif args.t_min == 4500 and args.t_max == 5500:
        win_tag = "broadened_4p5to5p5ms"
    else:
        win_tag = f"win_{args.t_min}to{args.t_max}us"

    if args.tag:
        win_tag = f"{win_tag}_{args.tag}"

    out_json = LOG_DIR / f"mode_a_500ep_{win_tag}_k{args.k_batch}_llm.json"
    full_output = {
        "metadata": {
            "title": f"500-Epoch Mode A Silicon Training: Identical 200-Sample Batch Window [{args.t_min}..{args.t_max} µs] & K={args.k_batch}",
            "patent": "SE 2630397-4 (Open Science Hardware)",
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "epochs": args.epochs,
            "k_batch": args.k_batch,
            "lr": args.lr,
            "reg_lambda": args.reg_lambda,
            "color_mode": "LLM_TOEPLITZ",
            "color_rho": args.rho,
            "t_min_us": args.t_min,
            "t_max_us": args.t_max,
            "num_strata": args.num_strata,
            "best_loss_lsb2": best_loss,
            "best_loss_epoch": best_ep,
            "best_enob_bits": best_enob,
            "best_window_enob_bits": best_win_enob,
            "final_loss_lsb2": records[-1]["loss_lsb2"],
            "final_enob_bits": records[-1]["enob_bits"],
            "final_window_enob_bits": records[-1]["window_eval"]["mean_enob_bits"],
            "duration_sec": round(total_time, 1),
            "sw_version": "v2.2-MAML",
            "hw_version": "0x20261030",
        },
        "epochs": records,
    }

    with open(out_json, "w") as f:
        json.dump(full_output, f, indent=2)
    print(f"[+] Saved hardware telemetry dataset: {out_json}")

    fig_path = DOCS_DIR / f"fig_mode_a_500ep_{win_tag}_k{args.k_batch}.png"
    generate_figure(records, full_output["metadata"], fig_path)

    artifact_fig = ARTIFACT_DIR / f"fig_mode_a_500ep_{win_tag}_k{args.k_batch}.png"
    try:
        import shutil
        shutil.copyfile(fig_path, artifact_fig)
        print(f"[+] Copied figure to artifact directory: {artifact_fig}")
    except Exception as e:
        print(f"[-] Warning: Failed to copy figure to artifact: {e}")


def generate_figure(records: list[dict], meta: dict, out_path: Path):
    epochs = [r["epoch"] for r in records]
    nom_losses = [r["loss_lsb2"] for r in records]
    win_losses = [r["window_eval"]["mean_loss_lsb2"] for r in records]
    nom_enobs = [r["enob_bits"] for r in records]
    win_enobs = [r["window_eval"]["mean_enob_bits"] for r in records]

    fig, axes = plt.subplots(3, 1, figsize=(12, 11), sharex=True)

    # Panel 1: Quadratic Loss (Both 200-sample Window Loss and 5.0ms Snapshot Loss on all 500 epochs)
    ax1 = axes[0]
    ax1.plot(epochs, win_losses, color="#d97706", linewidth=1.4, label="200-Sample Window [4.5..5.5 ms] Mean Loss (LSB²)")
    ax1.plot(epochs, nom_losses, color="#2563eb", linewidth=1.0, alpha=0.75, label="5.0 ms Center Snapshot Loss (LSB²)")
    ax1.axvspan(0, 100, color="#f1f5f9", alpha=0.6, label="Phase 1: Baseline Zero (W=0 LSB, LR=0, Hadamard ON)")
    ax1.axvspan(100, 200, color="#fee2e2", alpha=0.5, label="Phase 2: Calibrated Smart Baseline (LR=0, Hadamard ON)")
    ax1.axvspan(200, 500, color="#dcfce7", alpha=0.5, label=f"Phase 3: Active Training ON (K=20, 10 Strata, LR={meta['lr']:.2f}, λ={meta['reg_lambda']})")
    ax1.set_ylabel("Loss (LSB²)", fontsize=11, fontweight="bold")
    ax1.set_title(
        f"Inverted MAML Silicon Training: Identical 200-Sample Batch Window [4.5..5.5 ms], LR={meta['lr']:.2f}, λ={meta['reg_lambda']}",
        fontsize=12, fontweight="bold"
    )
    ax1.grid(True, linestyle="--", alpha=0.5)
    ax1.legend(loc="upper right", fontsize=8.5)

    # Panel 2: ENOB (Both 200-sample Window ENOB and 5.0ms Snapshot ENOB on all 500 epochs)
    ax2 = axes[1]
    ax2.plot(epochs, win_enobs, color="#d97706", linewidth=1.5, label="200-Sample Window [4.5..5.5 ms] Mean ENOB (bits)")
    ax2.plot(epochs, nom_enobs, color="#059669", linewidth=1.0, alpha=0.75, label="5.0 ms Center Snapshot ENOB (bits)")
    ax2.axvspan(0, 100, color="#f1f5f9", alpha=0.6)
    ax2.axvspan(100, 200, color="#fee2e2", alpha=0.5)
    ax2.axvspan(200, 500, color="#dcfce7", alpha=0.5)
    ax2.axhline(6.0, color="#dc2626", linestyle=":", label="6-Bit Target")
    ax2.set_ylabel("ENOB (Bits)", fontsize=11, fontweight="bold")
    ax2.grid(True, linestyle="--", alpha=0.5)
    ax2.legend(loc="upper left", fontsize=9)

    # Panel 3: M8 Vernier Compensation Weights
    ax3 = axes[2]
    colors = ["#1e293b", "#0284c7", "#16a34a", "#eab308", "#ea580c", "#9333ea"]
    for c in range(6):
        col_w = [r["w8_diag"][c] for r in records]
        ax3.plot(epochs, col_w, color=colors[c], linewidth=1.4, label=f"M8[{c},{c}] (Col {c})")
    ax3.axvspan(0, 100, color="#f1f5f9", alpha=0.6)
    ax3.axvspan(100, 200, color="#fee2e2", alpha=0.5)
    ax3.axvspan(200, 500, color="#dcfce7", alpha=0.5)
    ax3.axhline(120, color="#dc2626", linestyle="--", linewidth=0.9, alpha=0.7, label="±120 LSB Clamp")
    ax3.axhline(-120, color="#dc2626", linestyle="--", linewidth=0.9, alpha=0.7)
    ax3.set_xlabel("Epoch (Each Epoch = 20 Vectors × 10 Strata = 200 Hadamard Measurements)", fontsize=11, fontweight="bold")
    ax3.set_ylabel("M8 Diagonal Weight (LSB)", fontsize=11, fontweight="bold")
    ax3.grid(True, linestyle="--", alpha=0.5)
    ax3.legend(loc="upper left", ncol=4, fontsize=8.5)

    plt.tight_layout()
    plt.savefig(out_path, dpi=220)
    plt.close(fig)


if __name__ == "__main__":
    main()
