#!/home/olle/anaconda3/bin/python
"""
run_500ep_broadened_window_k20.py
Inverted MAML (Patent Pending SE 2630397-4) - Open Science Hardware

500-Epoch Physical Silicon Experiment with Broadened Temporal Window & K=20 Batch:
- Temporal Measurement & Payload Window: 4.5 ms to 5.5 ms (4500 µs - 5500 µs)
- Strata: 10 discrete strata across [4500, 5500] µs
- Batch Size: K = 20 vectors per update
- In-Data Noise Equalizer: COLOR_LLM_TOEPLITZ (rho = 0.85)
- Schedule:
    * Epochs   0..99 : Baseline Zero (W = 0 LSB, Training OFF, Reg = 0)
    * Epochs 100..199: Baseline Knee (W = ±16 LSB, Training OFF, Reg = 0)
    * Epochs 200..500: Active Training ON (K=20, 10 Strata, LR = 0.25x, L2 Reg λ = 512)
- Multi-strata holdout validation and continuous telemetry logging.
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

LOG_DIR = REPO_ROOT / "FPGA_code" / "logs" / "mode_a_extended_training"
LOG_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR = REPO_ROOT / "FPGA_code" / "docs" / "figures"
DOCS_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACT_DIR = Path("/home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a")

STRATA_10_US = [4500, 4611, 4722, 4833, 4944, 5055, 5166, 5277, 5388, 5500]


def get_averaged_telemetry(client: MamlUdpClient, n_avg: int = 2) -> dict:
    t_list = []
    for _ in range(n_avg):
        for _ in range(3):
            raw = client._send_binary(MAML_CMD_GET_TELEMETRY)
            if raw is not None and len(raw) >= client.TELEM_SIZE:
                t = client._parse_hw_telemetry(raw)
                if t is not None and t.connected_hw:
                    t_list.append(t)
                    break
            time.sleep(0.005)
        time.sleep(0.005)

    if not t_list:
        raise RuntimeError("Failed to receive live hardware telemetry from T120.")

    adc45_arr = np.mean([t.adc45_sig for t in t_list], axis=0)
    adc49_arr = np.mean([t.adc49_sig for t in t_list], axis=0)
    z_target_arr = np.mean([t.z_target for t in t_list], axis=0)
    last_t = t_list[-1]

    err49 = adc49_arr - z_target_arr
    rmse = float(np.sqrt(np.mean(err49 ** 2)))
    loss = float(np.sum(err49 ** 2) / 2.0)
    enob = max(0.0, 11.0 - np.log2(max(rmse, 1.0)))

    return {
        "loss_lsb2": round(loss, 1),
        "rmse_lsb": round(rmse, 2),
        "enob_bits": round(enob, 2),
        "x_ref": [int(round(v)) for v in last_t.x_ref],
        "z_target": [int(round(v)) for v in z_target_arr],
        "adc45": [int(round(v)) for v in adc45_arr],
        "adc49": [int(round(v)) for v in adc49_arr],
        "err49": [int(round(v)) for v in err49],
        "w_m3": last_t.w_m3,
        "w_m8": last_t.w_m8,
        "w_m33": last_t.w_m33,
        "w8_diag": [last_t.w_m8[i][i] for i in range(6)],
        "w3_diag": [last_t.w_m3[i][i] for i in range(6)],
        "color_mode": last_t.color_mode,
        "color_rho": last_t.color_rho,
        "w33_is_custom": last_t.w33_is_custom,
    }


def evaluate_window_strata(client: MamlUdpClient, lr_inner_q16: int) -> dict:
    """Evaluate generalization across all 10 strata across [4.5, 5.5] ms."""
    strata_rmses = []
    strata_losses = []
    strata_enobs = []
    per_stratum_records = {}

    for t_us in STRATA_10_US:
        client.set_config(
            mode=0, jumper_mode=3, led_switches=3, max_meas_win_pct=100, hadamard_khz=500,
            inner_loop_n=100, seed_pct=28, seed_mode=1, w_hid_mag=0, trim_hid_mag=0,
            hadamard_delay_us=t_us,
            lr_inner_q16=lr_inner_q16,
        )
        time.sleep(0.008)
        raw = client._send_binary(MAML_CMD_GET_TELEMETRY)
        if raw and len(raw) >= client.TELEM_SIZE:
            t = client._parse_hw_telemetry(raw)
            err = np.array(t.adc49_sig) - np.array(t.z_target)
            r = float(np.sqrt(np.mean(err ** 2)))
            l = float(np.sum(err ** 2) / 2.0)
            e = max(0.0, 11.0 - math.log2(max(r, 1.0)))
            strata_rmses.append(r)
            strata_losses.append(l)
            strata_enobs.append(e)
            per_stratum_records[str(t_us)] = {
                "rmse_lsb": round(r, 2),
                "loss_lsb2": round(l, 1),
                "enob_bits": round(e, 2),
            }

    mean_rmse = float(np.mean(strata_rmses)) if strata_rmses else 0.0
    mean_loss = float(np.mean(strata_losses)) if strata_losses else 0.0
    mean_enob = max(0.0, 11.0 - math.log2(max(mean_rmse, 1.0))) if mean_rmse > 0 else 0.0

    return {
        "mean_rmse_lsb": round(mean_rmse, 2),
        "mean_loss_lsb2": round(mean_loss, 1),
        "mean_enob_bits": round(mean_enob, 2),
        "per_stratum": per_stratum_records,
    }


def main():
    parser = argparse.ArgumentParser(description="500-Epoch Mode A Training with Broadened Window [4.5..5.5 ms] & K=20 Batch")
    parser.add_argument("--host", default="192.168.1.50")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--epochs", type=int, default=500)
    parser.add_argument("--k-batch", type=int, default=20)
    parser.add_argument("--lr", type=float, default=0.25)
    parser.add_argument("--reg-lambda", type=int, default=512)
    parser.add_argument("--rho", type=float, default=0.85)
    parser.add_argument("--t-min", type=int, default=4500)
    parser.add_argument("--t-max", type=int, default=5500)
    parser.add_argument("--num-strata", type=int, default=10)
    args = parser.parse_args()

    print("=" * 84)
    print("INVERTED MAML: 500-EPOCH BROADENED TEMPORAL WINDOW [4.5 - 5.5 ms] TRAINING")
    print(f"Target: {args.host}:{args.port} | Epochs: {args.epochs} | Batch K: {args.k_batch} | LR: {args.lr:.2f}x")
    print(f"Window: [{args.t_min} .. {args.t_max}] µs ({args.num_strata} Strata) | L2 Reg: λ = {args.reg_lambda} | Spatial ρ: {args.rho:.2f}")
    print("=" * 84)

    client = MamlUdpClient(host=args.host, port=args.port, timeout=5.0)

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
    print(f"[*] Stage 1 Init: Setting Baseline 0 (W = 0 LSB) on M3 & M8 (Training OFF)...")
    client._send_binary(MAML_CMD_CENTER_WEIGHTS, struct.pack("<B", 0))
    client.set_regularization(0)
    time.sleep(0.05)

    client.draw_fresh_vector()
    time.sleep(0.03)

    t0 = get_averaged_telemetry(client, n_avg=2)
    eval0 = evaluate_window_strata(client, lr_inner_q16)

    print(f"  Ep   0 [BASE 0   ]: Nominal 5ms: Loss={t0['loss_lsb2']:.1f} LSB² | RMSE={t0['rmse_lsb']:.2f} LSB | ENOB={t0['enob_bits']:.2f} b")
    print(f"                    Window Mean : Loss={eval0['mean_loss_lsb2']:.1f} LSB² | RMSE={eval0['mean_rmse_lsb']:.2f} LSB | ENOB={eval0['mean_enob_bits']:.2f} b | W8={t0['w8_diag']}")
    print("-" * 105)
    print(f"{'Ep #':<6} {'Phase':<15} {'Reg':<5} | {'Nom Loss':<10} | {'Nom RMSE':<9} | {'Nom ENOB':<9} | {'Win Loss':<10} | {'Win ENOB':<9} | {'W8 Diag (Cols 0..5)':<23}")
    print("-" * 105)

    records = [{
        "epoch": 0,
        "phase": "BASELINE_ZERO",
        "reg_lambda_q16": 0,
        "batch_k": args.k_batch,
        "t_min_us": args.t_min,
        "t_max_us": args.t_max,
        "num_strata": args.num_strata,
        **t0,
        "window_eval": eval0,
    }]

    best_loss = t0["loss_lsb2"]
    best_ep = 0
    best_enob = t0["enob_bits"]
    best_win_enob = eval0["mean_enob_bits"]

    w3_flat_0 = np.array(t0["w_m3"])[:6, :6].flatten()
    w8_flat_0 = np.array(t0["w_m8"])[:6, :6].flatten()

    t_start = time.time()

    for ep in range(1, args.epochs + 1):
        if ep < 100:
            phase = "BASELINE_ZERO"
            cur_reg = 0
            is_training = False
        elif ep < 200:
            phase = "BASELINE_KNEE"
            cur_reg = 0
            is_training = False
        else:
            phase = "TRAIN_REG_ON"
            cur_reg = args.reg_lambda
            is_training = True

        # Phase switchover triggers
        if ep == 100:
            print("=" * 105)
            print(f">>> [EPOCH 100]: SMACKING ON KNEE BASELINE (±16 LSB) ON M3 & M8! (Training OFF)")
            print("=" * 105)
            client._send_binary(MAML_CMD_CENTER_WEIGHTS, struct.pack("<B", 1))
            client.set_regularization(0)
            time.sleep(0.04)
        elif ep == 200:
            print("=" * 105)
            print(f">>> [EPOCH 200]: ACTIVE TRAINING ON! BROADENED WINDOW [{args.t_min}..{args.t_max} µs] BATCH (K={args.k_batch}, λ={args.reg_lambda}, LR={args.lr:.2f}x)")
            print("=" * 105)
            client.set_regularization(args.reg_lambda)
            time.sleep(0.03)

        # Draw fresh rotating LLM Toeplitz vector
        client.draw_fresh_vector()
        time.sleep(0.01)

        # Execute Batch Gradient Step during Active Training Phase
        batch_telem = None
        if is_training:
            # Send MAML_CMD_BATCH_STEP packet: k, num_strata, t_min, t_max, lr, reg
            pkt = struct.pack(
                "<BBHHHH",
                args.k_batch,
                args.num_strata,
                args.t_min,
                args.t_max,
                lr_inner_q16,
                cur_reg,
            )
            raw = client._send_binary(MAML_CMD_BATCH_STEP, pkt)
            if raw and len(raw) >= client.TELEM_SIZE:
                batch_telem = client._parse_hw_telemetry(raw)
        else:
            time.sleep(0.01)

        # Reset measurement delay to nominal 5.0 ms for standardized tracking
        client.set_config(
            mode=0, jumper_mode=3, led_switches=3, max_meas_win_pct=100, hadamard_khz=500,
            inner_loop_n=100, seed_pct=28, seed_mode=1, w_hid_mag=0, trim_hid_mag=0,
            hadamard_delay_us=5000, lr_inner_q16=lr_inner_q16
        )
        time.sleep(0.005)

        t_cur = get_averaged_telemetry(client, n_avg=2)

        # Evaluate window strata periodically or at key epochs
        do_full_eval = (ep % 20 == 0 or ep == 1 or ep == 99 or ep == 100 or ep == 199 or ep == 200 or ep == args.epochs)
        if do_full_eval:
            eval_cur = evaluate_window_strata(client, lr_inner_q16)
        else:
            # Interpolate / carry forward previous window evaluation
            eval_cur = {
                "mean_rmse_lsb": t_cur["rmse_lsb"],
                "mean_loss_lsb2": t_cur["loss_lsb2"],
                "mean_enob_bits": t_cur["enob_bits"],
                "per_stratum": {},
            }

        # Weight correlation metrics
        w3_flat = np.array(t_cur["w_m3"])[:6, :6].flatten()
        w8_flat = np.array(t_cur["w_m8"])[:6, :6].flatten()
        r3 = float(np.corrcoef(w3_flat_0, w3_flat)[0, 1]) if np.std(w3_flat) > 1e-6 else 1.0
        r8 = float(np.corrcoef(w8_flat_0, w8_flat)[0, 1]) if np.std(w8_flat) > 1e-6 else 1.0

        rec = {
            "epoch": ep,
            "phase": phase,
            "reg_lambda_q16": cur_reg,
            "batch_k": args.k_batch,
            "t_min_us": args.t_min,
            "t_max_us": args.t_max,
            "num_strata": args.num_strata,
            "r_m3": round(r3, 4),
            "r_m8": round(r8, 4),
            **t_cur,
            "window_eval": eval_cur,
        }
        records.append(rec)

        if t_cur["loss_lsb2"] < best_loss:
            best_loss = t_cur["loss_lsb2"]
            best_ep = ep
        if t_cur["enob_bits"] > best_enob:
            best_enob = t_cur["enob_bits"]
        if eval_cur["mean_enob_bits"] > best_win_enob and do_full_eval:
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

    # Save JSON log
    out_json = LOG_DIR / "mode_a_500ep_broadened_4p5to5p5ms_k20_llm.json"
    full_output = {
        "metadata": {
            "title": "500-Epoch Mode A Silicon Training: Broadened Temporal Window [4.5..5.5 ms] & K=20 Batch",
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
            "sw_version": "v2.0-MAML",
            "hw_version": "0x20261030",
        },
        "epochs": records,
    }

    with open(out_json, "w") as f:
        json.dump(full_output, f, indent=2)
    print(f"[+] Saved hardware telemetry dataset: {out_json}")

    # Generate 3-panel figure
    fig_path = DOCS_DIR / "fig_mode_a_500ep_broadened_window_k20.png"
    generate_figure(records, full_output["metadata"], fig_path)

    # Copy to artifacts directory
    artifact_fig = ARTIFACT_DIR / "fig_mode_a_500ep_broadened_window_k20.png"
    try:
        import shutil
        shutil.copyfile(fig_path, artifact_fig)
        print(f"[+] Copied figure to artifact directory: {artifact_fig}")
    except Exception as e:
        print(f"[-] Warning: Failed to copy figure to artifact: {e}")


def generate_figure(records: list[dict], meta: dict, out_path: Path):
    epochs = [r["epoch"] for r in records]
    losses = [r["loss_lsb2"] for r in records]
    rmses = [r["rmse_lsb"] for r in records]
    enobs = [r["enob_bits"] for r in records]

    # Extract window mean ENOB where evaluated
    win_epochs = [r["epoch"] for r in records if "per_stratum" in r["window_eval"] and r["window_eval"]["per_stratum"]]
    win_enobs = [r["window_eval"]["mean_enob_bits"] for r in records if "per_stratum" in r["window_eval"] and r["window_eval"]["per_stratum"]]

    w8_col0 = [r["w8_diag"][0] for r in records]
    w8_col1 = [r["w8_diag"][1] for r in records]
    w8_col2 = [r["w8_diag"][2] for r in records]
    w8_col3 = [r["w8_diag"][3] for r in records]
    w8_col4 = [r["w8_diag"][4] for r in records]
    w8_col5 = [r["w8_diag"][5] for r in records]

    fig, axes = plt.subplots(3, 1, figsize=(12, 11), sharex=True)

    # Panel 1: Quadratic Loss
    ax1 = axes[0]
    ax1.plot(epochs, losses, color="#2563eb", linewidth=1.3, label="Nominal 5.0 ms Loss (LSB²)")
    ax1.axvspan(0, 100, color="#f1f5f9", alpha=0.6, label="Phase 1: Baseline Zero (W=0 LSB)")
    ax1.axvspan(100, 200, color="#fee2e2", alpha=0.5, label="Phase 2: Baseline Knee (W=±16 LSB)")
    ax1.axvspan(200, 500, color="#dcfce7", alpha=0.5, label="Phase 3: Active Training ON (K=20, 10 Strata, λ=512)")
    ax1.set_ylabel("Loss (LSB²)", fontsize=11, fontweight="bold")
    ax1.set_title("Inverted MAML Silicon Training: Broadened Window [4.5..5.5 ms], K=20 Batch, LLM Toeplitz (ρ=0.85)", fontsize=12, fontweight="bold")
    ax1.grid(True, linestyle="--", alpha=0.5)
    ax1.legend(loc="upper right", fontsize=9)

    # Panel 2: ENOB
    ax2 = axes[1]
    ax2.plot(epochs, enobs, color="#059669", linewidth=1.3, label="Nominal 5.0 ms ENOB (bits)")
    if win_epochs:
        ax2.plot(win_epochs, win_enobs, "o--", color="#d97706", linewidth=1.5, markersize=4, label="Window Mean [4.5..5.5 ms] ENOB (bits)")
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
        ax3.plot(epochs, [r["w8_diag"][c] for r in records], color=colors[c], linewidth=1.2, label=f"M8 Diag Col {c}")
    ax3.axvspan(0, 100, color="#f1f5f9", alpha=0.6)
    ax3.axvspan(100, 200, color="#fee2e2", alpha=0.5)
    ax3.axvspan(200, 500, color="#dcfce7", alpha=0.5)
    ax3.set_xlabel("Epoch #", fontsize=11, fontweight="bold")
    ax3.set_ylabel("M8 Weights (LSB)", fontsize=11, fontweight="bold")
    ax3.grid(True, linestyle="--", alpha=0.5)
    ax3.legend(loc="upper right", ncol=3, fontsize=8)

    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()
    print(f"[+] Saved summary figure: {out_path}")


if __name__ == "__main__":
    main()
