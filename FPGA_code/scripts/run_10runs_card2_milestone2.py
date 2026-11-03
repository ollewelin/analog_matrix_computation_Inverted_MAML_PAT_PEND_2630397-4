#!/usr/bin/env python3
"""
run_10runs_card2_milestone2.py
Inverted MAML (Patent Pending SE 2630397-4) - Open Science Hardware

10-Run Milestone 2 Statistical Verification Campaign on Physical Silicon:
- Hardware: Card 2 (Rev 2.0 Silicon, 1k / 3.9k Ohm summing attenuator)
- Post-Resoldering Verification: High-current MCP6444-E/SL drivers active
- 10 Independent 500-Epoch Runs with dynamic rotating LLM Toeplitz vectors (rho = 0.85)
- Hyperparameters: LR = 0.25x, L2 reg lambda = 512, d_line = 2 (+/-45 LSB swing), t = 5.0 ms
- Produces individual plots for Run 1 & Run 2, plus combined 10-run multi-trajectory Loss & ENOB figure.
"""

import sys
import os
import time
import json
import struct
import argparse
import shutil
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
    MAML_CMD_RAND_DATA,
    MAML_CMD_STEP_OUTER,
    MAML_CMD_SET_REG,
    COLOR_LLM_TOEPLITZ,
)
from FPGA_code.scripts.verify_and_guard_version import ensure_version_guard

LOG_DIR = REPO_ROOT / "FPGA_code" / "logs" / "llm_noise_campaign"
LOG_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR = REPO_ROOT / "FPGA_code" / "docs" / "figures"
DOCS_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACT_DIR = Path("/home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a")


def get_averaged_telemetry(client: MamlUdpClient, n_avg: int = 3) -> dict:
    t_list = []
    for _ in range(n_avg):
        for _att in range(5):
            raw = client._send_binary(MAML_CMD_GET_TELEMETRY)
            if raw is not None and len(raw) >= client.TELEM_SIZE:
                t = client._parse_hw_telemetry(raw)
                if t is not None and t.connected_hw:
                    t_list.append(t)
                    break
            time.sleep(0.005)
        time.sleep(0.006)

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


def plot_single_run(run_idx: int, run_data: dict, out_png: Path):
    epochs = [e["epoch"] for e in run_data["epochs"]]
    loss = [e["loss_lsb2"] for e in run_data["epochs"]]
    enob = [e["enob_bits"] for e in run_data["epochs"]]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    fig.patch.set_facecolor("#ffffff")

    # Plot 1: Loss
    ax1.axvspan(0, 99, color="#e3f2fd", alpha=0.5, label="Fas 1: Baseline Zero (W=0)")
    ax1.axvspan(100, 199, color="#fff3e0", alpha=0.5, label="Fas 2: Baseline Knä (W=±16)")
    ax1.axvspan(200, 500, color="#e8f5e9", alpha=0.5, label="Fas 3: Aktiv Träning (λ=512, LR=0.25x)")

    ax1.semilogy(epochs, loss, color="#1565c0", linewidth=1.5, label=f"Körning {run_idx:02d} Loss")
    ax1.axhline(280.6, color="#d32f2f", linestyle="--", linewidth=1.2, label="Kort 1 Rekord (280.6 LSB²)")

    best_l = run_data["metadata"]["best_loss_lsb2"]
    best_ep = run_data["metadata"]["best_loss_epoch"]
    ax1.scatter([best_ep], [best_l], color="#d32f2f", s=50, zorder=5)
    ax1.annotate(
        f"Lägsta Loss: {best_l:.1f} LSB²\n(Ep {best_ep})",
        xy=(best_ep, best_l),
        xytext=(best_ep + 15, best_l * 2.5),
        arrowprops=dict(facecolor="#d32f2f", shrink=0.08, width=1, headwidth=6),
        fontweight="bold", fontsize=9, color="#b71c1c"
    )

    ax1.set_ylabel("Loss (LSB²)", fontweight="bold", fontsize=11)
    ax1.set_title(f"Inverted MAML (Kort 2, 1k/3.9k) - Körning {run_idx:02d}: Loss & ENOB (500 Epoker vid 5.0 ms)", fontweight="bold", fontsize=12)
    ax1.grid(True, which="both", linestyle=":", alpha=0.6)
    ax1.legend(loc="upper right", framealpha=0.9, fontsize=9)

    # Plot 2: ENOB
    ax2.axvspan(0, 99, color="#e3f2fd", alpha=0.5)
    ax2.axvspan(100, 199, color="#fff3e0", alpha=0.5)
    ax2.axvspan(200, 500, color="#e8f5e9", alpha=0.5)

    ax2.plot(epochs, enob, color="#2e7d32", linewidth=1.5, label=f"Körning {run_idx:02d} ENOB")
    ax2.axhline(7.73, color="#d32f2f", linestyle="--", linewidth=1.2, label="Kort 1 Rekord (7.73 bitar)")

    best_b = run_data["metadata"]["best_enob_bits"]
    ax2.scatter([best_ep], [best_b], color="#2e7d32", s=50, zorder=5)
    ax2.annotate(
        f"Topp ENOB: {best_b:.2f} bitar",
        xy=(best_ep, best_b),
        xytext=(best_ep + 15, best_b - 0.7),
        arrowprops=dict(facecolor="#2e7d32", shrink=0.08, width=1, headwidth=6),
        fontweight="bold", fontsize=9, color="#1b5e20"
    )

    ax2.set_xlabel("Epok (Kontinuerligt roterande LLM Toeplitz-brus, ρ = 0.85)", fontweight="bold", fontsize=11)
    ax2.set_ylabel("ENOB (Bitar)", fontweight="bold", fontsize=11)
    ax2.set_ylim(4.0, 8.5)
    ax2.grid(True, linestyle=":", alpha=0.6)
    ax2.legend(loc="lower right", framealpha=0.9, fontsize=9)

    plt.tight_layout()
    plt.savefig(out_png, dpi=160)
    plt.close()

    # Also copy to artifact dir if present
    if ARTIFACT_DIR.exists():
        shutil.copy2(out_png, ARTIFACT_DIR / out_png.name)
    print(f"[+] Genererade graf för Körning {run_idx:02d}: {out_png.name}")


def execute_single_run(run_idx: int, client: MamlUdpClient, ver_info: dict, args) -> dict:
    print("\n" + "=" * 80)
    print(f">>> STARTAR KÖRNING {run_idx:02d} / {args.total_runs:02d} (500 EPOKER)")
    print("=" * 80)

    # 1. Reset gain knobs
    client.set_gain_experiment(d_line=args.d_line, w33=1, target_gain=1.0, clamp=120)
    time.sleep(0.03)

    # 2. Configure initial Mode A: Training OFF (mode=0), LEDs ON, jumper_mode=3
    lr_inner_q16 = max(32, min(4096, int(round(1024 * args.lr))))
    client.set_config(
        mode=0, jumper_mode=3, led_switches=3, max_meas_win_pct=100, hadamard_khz=500,
        inner_loop_n=100, seed_pct=0, seed_mode=0, w_hid_mag=0, trim_hid_mag=0,
        hadamard_delay_us=5000, lr_inner_q16=lr_inner_q16
    )
    time.sleep(0.03)

    # LEDs ON
    client._send_binary(0x13, struct.pack("<BB", 1, 1))
    time.sleep(0.02)

    # Set noise equalizer
    client.set_data_color(COLOR_LLM_TOEPLITZ, args.rho)
    time.sleep(0.03)

    # Center zero weights
    client._send_binary(MAML_CMD_CENTER_WEIGHTS, struct.pack("<B", 0))
    client.set_regularization(0)
    time.sleep(0.05)

    client.draw_fresh_vector()
    time.sleep(0.03)

    t0 = get_averaged_telemetry(client, n_avg=3)
    records = [{
        "epoch": 0,
        "phase": "BASELINE_ZERO",
        "reg_lambda_q16": 0,
        **t0,
    }]

    best_loss = t0["loss_lsb2"]
    best_ep = 0
    best_enob = t0["enob_bits"]

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

        if ep == 100:
            client._send_binary(MAML_CMD_CENTER_WEIGHTS, struct.pack("<B", 1))
            client.set_regularization(0)
            time.sleep(0.04)
        elif ep == 200:
            client.set_regularization(args.reg_lambda)
            time.sleep(0.03)

        client.draw_fresh_vector()
        time.sleep(0.012)

        if is_training:
            client._send_binary(MAML_CMD_STEP_OUTER, struct.pack("<H", cur_reg))
            time.sleep(0.015)
        else:
            time.sleep(0.015)

        t_cur = get_averaged_telemetry(client, n_avg=3)
        rec = {
            "epoch": ep,
            "phase": phase,
            "reg_lambda_q16": cur_reg,
            **t_cur,
        }
        records.append(rec)

        if t_cur["loss_lsb2"] < best_loss:
            best_loss = t_cur["loss_lsb2"]
            best_ep = ep
        if t_cur["enob_bits"] > best_enob:
            best_enob = t_cur["enob_bits"]

        if ep % 50 == 0 or ep == 100 or ep == 200 or ep == args.epochs:
            dt = time.time() - t_start
            rate = ep / max(dt, 0.001)
            eta = (args.epochs - ep) / max(rate, 0.001)
            print(
                f"  [Körning {run_idx:02d}] Ep {ep:3d} {phase:<15} | "
                f"Loss={t_cur['loss_lsb2']:<10.1f} | ENOB={t_cur['enob_bits']:<5.2f} b | "
                f"W8={str(t_cur['w8_diag']):<25} ({rate:.1f} ep/s, ETA {eta:.0f}s)"
            )

    total_time = time.time() - t_start
    summary_obj = {
        "metadata": {
            "title": f"Inverted MAML Kort 2 Milestone 2 - Körning {run_idx:02d}",
            "run_index": run_idx,
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "epochs": args.epochs,
            "lr": args.lr,
            "reg_lambda": args.reg_lambda,
            "color_mode": "LLM_TOEPLITZ",
            "color_rho": args.rho,
            "d_line": args.d_line,
            "best_loss_lsb2": best_loss,
            "best_loss_epoch": best_ep,
            "best_enob_bits": best_enob,
            "final_loss_lsb2": records[-1]["loss_lsb2"],
            "final_enob_bits": records[-1]["enob_bits"],
            "duration_sec": round(total_time, 2),
            "sw_version": ver_info.get("sw_version"),
            "hw_version": ver_info.get("hw_version"),
        },
        "epochs": records,
    }

    out_file = LOG_DIR / f"mode_a_500ep_llm_toeplitz_rho85_reg512_card2_run{run_idx:02d}.json"
    with open(out_file, "w") as f:
        json.dump(summary_obj, f, indent=2)

    print(f"[+] Sparade Körning {run_idx:02d}: {out_file.name} (Bästa Loss: {best_loss:.1f} LSB², {best_enob:.2f} b)")

    # Plot single run
    out_png = DOCS_DIR / f"fig_mode_a_500ep_card2_run{run_idx:02d}.png"
    plot_single_run(run_idx, summary_obj, out_png)

    return summary_obj


def plot_combined_10runs(all_runs: list, out_png: Path):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    fig.patch.set_facecolor("#ffffff")

    epochs = np.arange(501)
    loss_matrix = np.zeros((len(all_runs), 501))
    enob_matrix = np.zeros((len(all_runs), 501))

    colors = [
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
        "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"
    ]

    # Plot phase shading
    for ax in (ax1, ax2):
        ax.axvspan(0, 99, color="#e3f2fd", alpha=0.45)
        ax.axvspan(100, 199, color="#fff3e0", alpha=0.45)
        ax.axvspan(200, 500, color="#e8f5e9", alpha=0.45)

    for i, r in enumerate(all_runs):
        l_arr = np.array([e["loss_lsb2"] for e in r["epochs"]])
        e_arr = np.array([e["enob_bits"] for e in r["epochs"]])
        loss_matrix[i, :] = l_arr
        enob_matrix[i, :] = e_arr

        c = colors[i % len(colors)]
        run_no = r["metadata"].get("run_index", i + 1)
        ax1.semilogy(epochs, l_arr, color=c, alpha=0.35, linewidth=1.1, label=f"Körning {run_no:02d}")
        ax2.plot(epochs, e_arr, color=c, alpha=0.35, linewidth=1.1, label=f"Körning {run_no:02d}")

    # Calculate statistics across runs
    mean_loss = np.mean(loss_matrix, axis=0)
    std_loss = np.std(loss_matrix, axis=0)
    mean_enob = np.mean(enob_matrix, axis=0)
    std_enob = np.std(enob_matrix, axis=0)

    # Plot mean and std on ax1 (Loss)
    ax1.semilogy(epochs, mean_loss, color="#000000", linewidth=2.5, label="Medelvärde (10 körningar)")
    ax1.fill_between(epochs, np.maximum(1.0, mean_loss - std_loss), mean_loss + std_loss, color="#9e9e9e", alpha=0.25, label="±1σ Spridning")
    ax1.axhline(280.6, color="#d32f2f", linestyle="--", linewidth=1.5, label="Kort 1 Rekord (280.6 LSB²)")

    ax1.set_ylabel("Loss (LSB²)", fontweight="bold", fontsize=11)
    ax1.set_title("Inverted MAML (Kort 2, 1k/3.9k) - Statistisk Sammanställning av 10 Körningar vid 5.0 ms", fontweight="bold", fontsize=13)
    ax1.grid(True, which="both", linestyle=":", alpha=0.6)
    ax1.legend(loc="upper right", ncol=3, fontsize=8, framealpha=0.92)

    # Plot mean and std on ax2 (ENOB)
    ax2.plot(epochs, mean_enob, color="#0d47a1", linewidth=2.5, label="Medelvärde (10 körningar)")
    ax2.fill_between(epochs, mean_enob - std_enob, mean_enob + std_enob, color="#90caf9", alpha=0.35, label="±1σ Spridning")
    ax2.axhline(7.73, color="#d32f2f", linestyle="--", linewidth=1.5, label="Kort 1 Rekord (7.73 bitar)")

    ax2.set_xlabel("Epok (500 epoker, kontinuerligt roterande LLM Toeplitz-brusvektorer, ρ = 0.85)", fontweight="bold", fontsize=11)
    ax2.set_ylabel("ENOB (Bitar)", fontweight="bold", fontsize=11)
    ax2.set_ylim(4.0, 8.5)
    ax2.grid(True, linestyle=":", alpha=0.6)
    ax2.legend(loc="lower right", ncol=3, fontsize=8, framealpha=0.92)

    plt.tight_layout()
    plt.savefig(out_png, dpi=160)
    plt.close()

    if ARTIFACT_DIR.exists():
        shutil.copy2(out_png, ARTIFACT_DIR / out_png.name)
    print(f"[+] Genererade kombinerad 10-körningsgraf: {out_png.name}")


def main():
    parser = argparse.ArgumentParser(description="10-Run Milestone 2 Statistical Campaign on Card 2")
    parser.add_argument("--host", default="192.168.1.50")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--epochs", type=int, default=500)
    parser.add_argument("--lr", type=float, default=0.25)
    parser.add_argument("--reg-lambda", type=int, default=512)
    parser.add_argument("--rho", type=float, default=0.85)
    parser.add_argument("--d-line", type=int, default=2)
    parser.add_argument("--total-runs", type=int, default=10)
    parser.add_argument("--skip-existing", action="store_true", default=True)
    args = parser.parse_args()

    ver_info = ensure_version_guard(host=args.host, port=args.port)
    client = MamlUdpClient(host=args.host, port=args.port, timeout=1.5)

    all_runs = []

    # Check Run 1: if test_same_as_before exists and run01 does not, migrate it!
    f_test = LOG_DIR / "mode_a_500ep_llm_toeplitz_rho85_reg512_test_same_as_before.json"
    f_run01 = LOG_DIR / "mode_a_500ep_llm_toeplitz_rho85_reg512_card2_run01.json"
    if f_test.exists() and not f_run01.exists():
        with open(f_test) as f:
            d01 = json.load(f)
        d01["metadata"]["run_index"] = 1
        d01["metadata"]["title"] = "Inverted MAML Kort 2 Milestone 2 - Körning 01"
        with open(f_run01, "w") as f:
            json.dump(d01, f, indent=2)
        print("[+] Importerade test_same_as_before som Körning 01!")

    for r_idx in range(1, args.total_runs + 1):
        r_file = LOG_DIR / f"mode_a_500ep_llm_toeplitz_rho85_reg512_card2_run{r_idx:02d}.json"
        p_file = DOCS_DIR / f"fig_mode_a_500ep_card2_run{r_idx:02d}.png"

        if args.skip_existing and r_file.exists():
            print(f"[*] Körning {r_idx:02d} finns redan ({r_file.name}), laddar in...")
            with open(r_file) as f:
                r_data = json.load(f)
            if not p_file.exists():
                plot_single_run(r_idx, r_data, p_file)
            all_runs.append(r_data)
            continue

        r_data = execute_single_run(r_idx, client, ver_info, args)
        all_runs.append(r_data)

    client.close()

    # Generate combined 10-runs plot
    comb_png = DOCS_DIR / "fig_mode_a_500ep_card2_10runs_combined.png"
    plot_combined_10runs(all_runs, comb_png)

    # Save summary JSON
    summary_file = LOG_DIR / "mode_a_500ep_card2_10runs_summary.json"
    summary_data = {
        "title": "Inverted MAML Kort 2 Milestone 2 - 10-Run Statistical Summary",
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "hardware": "Card 2 (Rev 2.0 Silicon, 1k/3.9k attenuator, MCP6444 on DAC2)",
        "total_runs": len(all_runs),
        "epochs_per_run": args.epochs,
        "runs": [
            {
                "run_index": r["metadata"].get("run_index", idx + 1),
                "best_loss_lsb2": r["metadata"]["best_loss_lsb2"],
                "best_loss_epoch": r["metadata"]["best_loss_epoch"],
                "best_enob_bits": r["metadata"]["best_enob_bits"],
                "final_loss_lsb2": r["metadata"]["final_loss_lsb2"],
                "final_enob_bits": r["metadata"]["final_enob_bits"],
            }
            for idx, r in enumerate(all_runs)
        ]
    }
    with open(summary_file, "w") as f:
        json.dump(summary_data, f, indent=2)

    print("\n" + "=" * 80)
    print(f"[+] KAMPANJ SLUTFÖRD! {len(all_runs)} KÖRNINGAR GENOMFÖRDA OCH SAMMANSTÄLLDA.")
    print(f"[+] Sparade: {summary_file.name}")
    print(f"[+] Kombinerad graf: {comb_png.name}")
    print("=" * 80)


if __name__ == "__main__":
    main()

