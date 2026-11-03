#!/usr/bin/env python3
"""
run_card2_4p5_to_5p5ms_flat_baseline.py
=======================================
Inverted MAML (Patent Pending SE 2630397-4) - Open Science Hardware

500-Epoch Broadened Window [4.5 ms to 5.5 ms] Experiment on Card 2
(Rev 2.0 Silicon, 1k/5.1k attenuator, repaired CH3) using the Flat Baseline Protocol:
- Phase 1 (Epochs   0.. 99): Baseline Zero (W = 0 LSB, LR = 0, Reg = 0, Full 200-sample batch)
- Phase 2 (Epochs 100..500): Active Inverted MAML Training directly from W = 0
  with L2 regularization anchored at W_null = 0 (lambda = 512, LR = 0.25x).
  NO artificial knee disturbance (no 209,000 LSB^2 jump)!
- Pre- & Post-Training Temporal Window Characterization (4.5 .. 5.5 ms, 100 us steps).
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
    Executes MAML_CMD_BATCH_STEP on physical T120 silicon.
    The FPGA executes k_batch * num_strata (e.g. 20 * 10 = 200) capacitor refreshes across
    [t_min_us .. t_max_us], fires full Hadamard bursts, accumulates the exact 200-sample
    quadratic error sum in hardware, and updates weights if lr_q16 > 0 or reg_q16 > 0.
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
    loss_total_milli = float(u[29])
    t = client._parse_hw_telemetry(raw)

    win_loss = loss_total_milli / 2.0
    win_rmse = math.sqrt(loss_total_milli / 6.0)
    win_enob = max(0.0, 11.0 - math.log2(max(win_rmse, 1.0)))

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
        "window_eval": {
            "mean_loss_lsb2": round(win_loss, 1),
            "mean_rmse_lsb": round(win_rmse, 2),
            "mean_enob_bits": round(win_enob, 2),
            "samples_per_epoch": k_batch * num_strata,
        },
    }


def sweep_temporal_profile(client: MamlUdpClient, delays_us: list[int], n_reps: int = 5) -> dict:
    """Measures single-snapshot loss and ENOB across a sequence of discrete delays."""
    results = {}
    for dly in delays_us:
        client.set_config(
            mode=0, jumper_mode=3, led_switches=3, max_meas_win_pct=100, hadamard_khz=500,
            inner_loop_n=100, seed_pct=28, seed_mode=1, w_hid_mag=0, trim_hid_mag=0,
            hadamard_delay_us=dly, lr_inner_q16=0
        )
        time.sleep(0.03)

        losses = []
        rmses = []
        enobs = []
        for _ in range(n_reps):
            client.draw_fresh_vector()
            time.sleep(0.015)
            raw = client._send_binary(MAML_CMD_GET_TELEMETRY)
            if raw and len(raw) >= client.TELEM_SIZE:
                t = client._parse_hw_telemetry(raw)
                err = np.array(t.adc49_sig) - np.array(t.z_target)
                r = float(np.sqrt(np.mean(err**2)))
                l = float(np.sum(err**2) / 2.0)
                b = max(0.0, 11.0 - math.log2(max(r, 1.0)))
                losses.append(l)
                rmses.append(r)
                enobs.append(b)

        results[str(dly)] = {
            "delay_us": dly,
            "mean_loss_lsb2": round(float(np.mean(losses)), 1) if losses else 0.0,
            "mean_rmse_lsb": round(float(np.mean(rmses)), 2) if rmses else 0.0,
            "mean_enob_bits": round(float(np.mean(enobs)), 2) if enobs else 0.0,
        }
    return results


def main():
    parser = argparse.ArgumentParser(description="500-Epoch Broadened Window [4.5..5.5 ms] Flat Baseline Run on Card 2")
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
    parser.add_argument("--d-line", type=int, default=2, help="Data line divider (1=>[-45..45], 2=>[-22..22])")
    parser.add_argument("--tag", type=str, default="card2_flat_baseline")
    args = parser.parse_args()

    print("=" * 105)
    print("INVERTED MAML: 500-EPOCH BROADENED WINDOW [4.5 - 5.5 ms] EXPERIMENT ON CARD 2")
    print("FLAT BASELINE PROTOCOL: Active Training directly from W = 0 with L2 anchored at W_null = 0")
    print(f"Target: {args.host}:{args.port} | Epochs: {args.epochs} | Batch K: {args.k_batch} x {args.num_strata} Strata = {args.k_batch * args.num_strata} Hadamard Samples/Ep")
    print(f"Window: [{args.t_min} .. {args.t_max}] µs | LR: {args.lr:.2f}x | L2 Reg: λ = {args.reg_lambda} | Data Div: {args.d_line}")
    print("=" * 105)

    ver_info = ensure_version_guard(host=args.host, port=args.port)
    client = MamlUdpClient(host=args.host, port=args.port, timeout=8.0)

    # 1. Konfigurera regim
    client.set_gain_experiment(d_line=args.d_line, w33=1, target_gain=1.0, clamp=120)
    time.sleep(0.03)

    lr_inner_q16 = max(32, min(4096, int(round(1024 * args.lr))))
    client.set_config(
        mode=0, jumper_mode=3, led_switches=3, max_meas_win_pct=100, hadamard_khz=500,
        inner_loop_n=100, seed_pct=28, seed_mode=1, w_hid_mag=0, trim_hid_mag=0,
        hadamard_delay_us=5000, lr_inner_q16=lr_inner_q16
    )
    time.sleep(0.03)
    client._send_binary(0x13, struct.pack("<BB", 1, 1))  # LEDs ON
    time.sleep(0.02)
    client.set_data_color(COLOR_LLM_TOEPLITZ, args.rho)
    time.sleep(0.03)

    # 2. Sätt PLATT baslinje och W_null = 0 i T120 RAM (90-byte all-zero payload)
    print("[*] Sätter platt baslinje: M3_null = 0, M8_null = 0, W = 0 LSB...")
    flat_payload = struct.pack("<B48b42b", 0, *([0] * 48), *([0] * 42))
    client._send_binary(MAML_CMD_CENTER_WEIGHTS, flat_payload)
    client.set_regularization(0)
    time.sleep(0.05)

    # 3. Pre-training Temporal Sweep (4.5 .. 5.5 ms)
    delays_sweep = list(range(args.t_min, args.t_max + 1, 100))
    print(f"\n[*] Kör förundersökning av tidsfönster: {len(delays_sweep)} punkter över [{args.t_min}..{args.t_max}] µs...")
    pre_sweep = sweep_temporal_profile(client, delays_sweep, n_reps=3)
    for d_k, d_v in pre_sweep.items():
        print(f"    {d_k} µs: Loss = {d_v['mean_loss_lsb2']:>9.1f} LSB² | RMSE = {d_v['mean_rmse_lsb']:>6.2f} LSB | ENOB = {d_v['mean_enob_bits']:>5.2f} b")

    # Återställ till batchkonfiguration
    client.set_config(
        mode=0, jumper_mode=3, led_switches=3, max_meas_win_pct=100, hadamard_khz=500,
        inner_loop_n=100, seed_pct=28, seed_mode=1, w_hid_mag=0, trim_hid_mag=0,
        hadamard_delay_us=5000, lr_inner_q16=lr_inner_q16
    )
    time.sleep(0.03)

    # Epoch 0: Initial batch measurement with lr=0, reg=0
    print("\n" + "=" * 105)
    print("STARTAR 500-EPOKERS HÅRDVARUTRÄNING:")
    print("Fas 1 (Ep   0.. 99): Öppen loop baslinje W = 0 LSB (LR=0, Reg=0, Full 200-sample batch)")
    print(f"Fas 2 (Ep 100..500): Aktiv träning direkt från W = 0 (LR={args.lr:.2f}x, λ={args.reg_lambda}, W_null=0)")
    print("=" * 105)

    t0 = run_identical_batch_epoch(client, args.k_batch, args.num_strata, args.t_min, args.t_max, lr_q16=0, reg_q16=0)
    eval0 = t0["window_eval"]

    print(f"  Ep   0 [BASE 0   ]: 200-Sample Win: Loss={eval0['mean_loss_lsb2']:.1f} LSB² | RMSE={eval0['mean_rmse_lsb']:.2f} LSB | ENOB={eval0['mean_enob_bits']:.2f} b")
    print(f"                    5.0ms Snapshot: Loss={t0['loss_lsb2']:.1f} LSB² | RMSE={t0['rmse_lsb']:.2f} LSB | ENOB={t0['enob_bits']:.2f} b | W8={t0['w8_diag']}")
    print("-" * 105)
    print(f"{'Ep #':<6} {'Phase':<20} {'Reg':<5} | {'Nom Loss':<10} | {'Nom RMSE':<9} | {'Nom ENOB':<9} | {'Win Loss':<10} | {'Win ENOB':<9} | {'W8 Diag (Cols 0..5)':<23}")
    print("-" * 105)

    records = [{
        "epoch": 0,
        "phase": "PHASE1_BASELINE_ZERO",
        "lr_q16": 0,
        "reg_lambda_q16": 0,
        "batch_k": args.k_batch,
        "t_min_us": args.t_min,
        "t_max_us": args.t_max,
        "num_strata": args.num_strata,
        **t0,
    }]

    t_start = time.time()
    best_loss = eval0["mean_loss_lsb2"]
    best_ep = 0
    best_enob = eval0["mean_enob_bits"]

    for ep in range(1, args.epochs + 1):
        if ep < 100:
            phase = "PHASE1_BASELINE_ZERO"
            cur_lr_q16 = 0
            cur_reg = 0
        else:
            phase = "PHASE2_TRAIN_FLAT_START"
            cur_lr_q16 = lr_inner_q16
            cur_reg = args.reg_lambda

        if ep == 100:
            print("\n" + "=" * 105)
            print(f">>> [EPOK 100]: AKTIVERAR TRÄNING DIREKT FRÅN W=0! (λ = {args.reg_lambda}, LR = {args.lr:.2f}x, W_null = 0)")
            print(">>> INGEN KNÄ-STÖRNING! Fullständig kontinuitet direkt från öppen loop!")
            print("=" * 105)
            client.set_regularization(args.reg_lambda)
            time.sleep(0.03)

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

        records.append({
            "epoch": ep,
            "phase": phase,
            "lr_q16": cur_lr_q16,
            "reg_lambda_q16": cur_reg,
            "batch_k": args.k_batch,
            "t_min_us": args.t_min,
            "t_max_us": args.t_max,
            "num_strata": args.num_strata,
            **t_cur,
        })

        if eval_cur["mean_loss_lsb2"] < best_loss and ep >= 100:
            best_loss = eval_cur["mean_loss_lsb2"]
            best_ep = ep
            best_enob = eval_cur["mean_enob_bits"]

        if ep % 20 == 0 or ep == 100 or ep == args.epochs:
            elapsed = time.time() - t_start
            rate = ep / max(1.0, elapsed)
            remain = (args.epochs - ep) / max(0.01, rate)
            print(
                f"Ep {ep:03d}  {phase:<20} {cur_reg:<5} | "
                f"{t_cur['loss_lsb2']:>8.1f} L² | {t_cur['rmse_lsb']:>7.2f} L | {t_cur['enob_bits']:>7.2f} b | "
                f"{eval_cur['mean_loss_lsb2']:>8.1f} L² | {eval_cur['mean_enob_bits']:>7.2f} b | "
                f"{str(t_cur['w8_diag']):<23} [{rate:.1f} ep/s, ETA {remain:.0f}s]"
            )

    total_dur = time.time() - t_start
    print("=" * 105)
    print(f"[+] 500-epokers körning slutförd på {total_dur:.1f} sek ({total_dur/60:.1f} min)")

    # 4. Post-training Temporal Sweep (4.5 .. 5.5 ms)
    print(f"\n[*] Kör efterundersökning av tidsfönster med tränade vikter: {len(delays_sweep)} punkter...")
    post_sweep = sweep_temporal_profile(client, delays_sweep, n_reps=3)
    for d_k, d_v in post_sweep.items():
        pre_l = pre_sweep[d_k]["mean_loss_lsb2"]
        post_l = d_v["mean_loss_lsb2"]
        delta_pct = (post_l - pre_l) / max(1.0, pre_l) * 100.0
        print(f"    {d_k} µs: Pre={pre_l:>8.1f} L² -> Post={post_l:>8.1f} L² ({delta_pct:+.1f}%) | ENOB: {pre_sweep[d_k]['mean_enob_bits']:.2f}b -> {d_v['mean_enob_bits']:.2f}b")

    # 5. Spara JSON
    out_stem = f"mode_a_500ep_broadened_4p5to5p5ms_{args.tag}"
    json_path = LOG_DIR / f"{out_stem}.json"
    fig_path = DOCS_DIR / f"fig_{out_stem}.png"

    p1_records = [r for r in records if r["phase"] == "PHASE1_BASELINE_ZERO"]
    p2_records = [r for r in records if r["phase"] == "PHASE2_TRAIN_FLAT_START"]

    p1_win_losses = [r["window_eval"]["mean_loss_lsb2"] for r in p1_records]
    p2_win_losses = [r["window_eval"]["mean_loss_lsb2"] for r in p2_records]
    p1_win_enobs = [r["window_eval"]["mean_enob_bits"] for r in p1_records]
    p2_win_enobs = [r["window_eval"]["mean_enob_bits"] for r in p2_records]

    meta = {
        "title": "500-Epoch Mode A Silicon Training: Broadened Window [4.5..5.5 ms] Flat Baseline on Card 2",
        "patent": "SE 2630397-4 (Open Science Hardware)",
        "hardware": "Card 2 (Rev 2.0 Silicon, 1k/5.1k attenuator, repaired CH3)",
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "epochs": args.epochs,
        "k_batch": args.k_batch,
        "num_strata": args.num_strata,
        "t_min_us": args.t_min,
        "t_max_us": args.t_max,
        "lr": args.lr,
        "reg_lambda": args.reg_lambda,
        "d_line": args.d_line,
        "duration_sec": round(total_dur, 1),
        "phase1_mean_win_loss": round(float(np.mean(p1_win_losses)), 1) if p1_win_losses else 0.0,
        "phase2_mean_win_loss": round(float(np.mean(p2_win_losses)), 1) if p2_win_losses else 0.0,
        "phase1_mean_win_enob": round(float(np.mean(p1_win_enobs)), 2) if p1_win_enobs else 0.0,
        "phase2_mean_win_enob": round(float(np.mean(p2_win_enobs)), 2) if p2_win_enobs else 0.0,
        "best_win_loss": round(best_loss, 1),
        "best_win_loss_ep": best_ep,
        "best_win_enob": round(best_enob, 2),
        "pre_sweep": pre_sweep,
        "post_sweep": post_sweep,
    }

    payload_json = {
        "metadata": meta,
        "epochs": records,
    }
    with open(json_path, "w") as f:
        json.dump(payload_json, f, indent=2)
    print(f"\n[+] Sparade JSON logg: {json_path}")

    # 6. Generera Figur
    generate_figure(records, meta, fig_path)
    print(f"[+] Genererade figur: {fig_path}")

    if ARTIFACT_DIR.exists():
        import shutil
        shutil.copy2(json_path, ARTIFACT_DIR / json_path.name)
        shutil.copy2(fig_path, ARTIFACT_DIR / fig_path.name)
        print(f"[+] Kopierade logg och figur till artefakt-katalogen: {ARTIFACT_DIR}")

    client.close()


def generate_figure(records: list[dict], meta: dict, out_path: Path):
    epochs = [r["epoch"] for r in records]
    nom_losses = [r["loss_lsb2"] for r in records]
    win_losses = [r["window_eval"]["mean_loss_lsb2"] for r in records]
    nom_enobs = [r["enob_bits"] for r in records]
    win_enobs = [r["window_eval"]["mean_enob_bits"] for r in records]

    fig, axes = plt.subplots(3, 1, figsize=(12, 11), sharex=True)

    # Panel 1: Quadratic Loss
    ax1 = axes[0]
    ax1.plot(epochs, win_losses, color="#d97706", linewidth=1.4, label="200-Sample Window [4.5..5.5 ms] Mean Loss (LSB²)")
    ax1.plot(epochs, nom_losses, color="#2563eb", linewidth=1.0, alpha=0.75, label="5.0 ms Center Snapshot Loss (LSB²)")
    ax1.axvspan(0, 100, color="#f1f5f9", alpha=0.7, label=f"Fas 1: Platt Baslinje W=0 (Snitt: {meta['phase1_mean_win_loss']:.1f} LSB²)")
    ax1.axvspan(100, len(epochs) - 1, color="#dcfce7", alpha=0.6, label=f"Fas 2: Aktiv Träning direkt från W=0 (Snitt: {meta['phase2_mean_win_loss']:.1f} LSB²)")
    ax1.set_ylabel("Loss (LSB²)", fontsize=11, fontweight="bold")
    ax1.set_title(
        f"Inverted MAML Card 2: 500-Epoch Broadened Window [4.5..5.5 ms] Flat Baseline (LR={meta['lr']:.2f}x, λ={meta['reg_lambda']})",
        fontsize=12, fontweight="bold"
    )
    ax1.grid(True, linestyle="--", alpha=0.5)
    ax1.legend(loc="upper right", fontsize=8.5)

    # Panel 2: ENOB
    ax2 = axes[1]
    ax2.plot(epochs, win_enobs, color="#d97706", linewidth=1.5, label="200-Sample Window [4.5..5.5 ms] Mean ENOB (bits)")
    ax2.plot(epochs, nom_enobs, color="#059669", linewidth=1.0, alpha=0.75, label="5.0 ms Center Snapshot ENOB (bits)")
    ax2.axvspan(0, 100, color="#f1f5f9", alpha=0.7)
    ax2.axvspan(100, len(epochs) - 1, color="#dcfce7", alpha=0.6)
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
    ax3.axvspan(0, 100, color="#f1f5f9", alpha=0.7)
    ax3.axvspan(100, len(epochs) - 1, color="#dcfce7", alpha=0.6)
    ax3.axhline(120, color="#dc2626", linestyle="--", linewidth=0.9, alpha=0.7, label="±120 LSB Clamp")
    ax3.axhline(-120, color="#dc2626", linestyle="--", linewidth=0.9, alpha=0.7)
    ax3.set_xlabel("Epok (Varje epok = 20 Vektorer × 10 Strata = 200 Hadamard-mätningar)", fontsize=11, fontweight="bold")
    ax3.set_ylabel("M8 Diagonala Vikter (LSB)", fontsize=11, fontweight="bold")
    ax3.grid(True, linestyle="--", alpha=0.5)
    ax3.legend(loc="upper left", ncol=4, fontsize=8.5)

    plt.tight_layout()
    plt.savefig(out_path, dpi=220)
    plt.close(fig)


if __name__ == "__main__":
    main()

