#!/usr/bin/env python3
"""
run_500ep_llm_regularization.py
Inverted MAML (Patent Pending SE 2630397-4) - Open Science Hardware

500-Epoch Physical Silicon Experiment:
- In-Data Noise Equalizer: LLM_TOEPLITZ (rho = 0.85)
- L2 Regularization: STRICTLY ON (lambda = 512, Q0.16)
- Mode A (Inner Loop Training at t = 5.0 ms snapshot)
- Dynamic continuous rotating LLM vectors (fresh correlated vector per epoch)
- Saves full epoch telemetry JSON and generates summary figure.
"""

import sys
import time
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


def get_averaged_telemetry(client: MamlUdpClient, n_avg: int = 3) -> dict:
    t_list = []
    for _ in range(n_avg):
        for attempt in range(5):
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


def main():
    parser = argparse.ArgumentParser(description="500-Epoch Mode A Training with LLM Noise & L2 Regularization")
    parser.add_argument("--host", default="192.168.1.50")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--epochs", type=int, default=500)
    parser.add_argument("--lr", type=float, default=0.25)
    parser.add_argument("--reg-lambda", type=int, default=512)
    parser.add_argument("--rho", type=float, default=0.85)
    parser.add_argument("--skip-version-guard", action="store_true")
    args = parser.parse_args()

    print("=" * 80)
    print("INVERTED MAML: 500-EPOCH MODE A TRAINING WITH LLM TOEPLITZ NOISE")
    print(f"Target: {args.host}:{args.port} | Epochs: {args.epochs} | LR: {args.lr:.2f}x")
    print(f"L2 Regularization: STRICTLY ON (lambda = {args.reg_lambda}) | Spatial rho: {args.rho:.2f}")
    print("=" * 80)

    if not args.skip_version_guard:
        ver_info = ensure_version_guard(host=args.host, port=args.port)
    else:
        ver_info = {"sw_version": "v2.2-MAML", "hw_version": "0x20261030"}

    client = MamlUdpClient(host=args.host, port=args.port, timeout=1.5)

    # 1. Reset gain knobs
    client.set_gain_experiment(d_line=1, w33=1, target_gain=1.0, clamp=120)
    time.sleep(0.03)

    # 2. Configure Mode A: LEDs ON (led_switches=3), seed_pct=0, 5000 us delay
    lr_inner_q16 = max(32, min(4096, int(round(1024 * args.lr))))
    client.set_config(
        mode=1, jumper_mode=3, led_switches=3, max_meas_win_pct=100, hadamard_khz=500,
        inner_loop_n=100, seed_pct=0, seed_mode=0, w_hid_mag=0, trim_hid_mag=0,
        hadamard_delay_us=5000, lr_inner_q16=lr_inner_q16
    )
    time.sleep(0.03)

    # Explicitly turn LEDs ON
    client._send_binary(0x13, struct.pack("<BB", 1, 1))
    time.sleep(0.02)

    # 3. Configure Noise Equalizer to LLM Toeplitz with rho=0.85
    print(f"[*] Setting In-Data Equalizer to LLM_TOEPLITZ (mode={COLOR_LLM_TOEPLITZ}, rho={args.rho})...")
    client.set_data_color(COLOR_LLM_TOEPLITZ, args.rho)
    time.sleep(0.03)

    # 4. Set Initial Baseline (Knee baseline ±16 LSB) and Set L2 Regularization
    print(f"[*] Initializing weights to Knee Baseline (±16 LSB)...")
    client._send_binary(MAML_CMD_CENTER_WEIGHTS, struct.pack("<B", 1))
    time.sleep(0.03)

    print(f"[*] Arming L2 Regularization: lambda = {args.reg_lambda}...")
    client.set_regularization(args.reg_lambda)
    time.sleep(0.03)

    # Draw fresh LLM vector
    client.draw_fresh_vector()
    time.sleep(0.03)

    t0 = get_averaged_telemetry(client, n_avg=3)
    print(f"  Ep   0 [INITIAL ]: Loss={t0['loss_lsb2']:.1f} LSB² | RMSE={t0['rmse_lsb']:.2f} LSB | ENOB={t0['enob_bits']:.2f} b | W8={t0['w8_diag']}")
    print("-" * 80)
    print(f"{'Ep #':<6} {'Phase':<16} {'Reg λ':<7} | {'Loss (LSB²)':<12} | {'RMSE (LSB)':<11} | {'ENOB (b)':<10} | {'W8 Diag (Cols 0..5)':<25}")
    print("-" * 80)

    records = [{
        "epoch": 0,
        "phase": "INIT",
        "reg_lambda_q16": args.reg_lambda,
        **t0,
    }]

    best_loss = t0["loss_lsb2"]
    best_ep = 0
    best_enob = t0["enob_bits"]

    t_start = time.time()

    for ep in range(1, args.epochs + 1):
        # Draw fresh rotating LLM vector every epoch
        client.draw_fresh_vector()
        time.sleep(0.012)

        # Execute Inverted MAML Mode A outer optimization step
        client._send_binary(MAML_CMD_STEP_OUTER, struct.pack("<H", args.reg_lambda))
        time.sleep(0.015)

        t_cur = get_averaged_telemetry(client, n_avg=3)
        rec = {
            "epoch": ep,
            "phase": "TRAIN_REG_ON",
            "reg_lambda_q16": args.reg_lambda,
            **t_cur,
        }
        records.append(rec)

        if t_cur["loss_lsb2"] < best_loss:
            best_loss = t_cur["loss_lsb2"]
            best_ep = ep
        if t_cur["enob_bits"] > best_enob:
            best_enob = t_cur["enob_bits"]

        if ep % 25 == 0 or ep == 1 or ep == args.epochs:
            dt = time.time() - t_start
            rate = ep / max(dt, 0.001)
            eta = (args.epochs - ep) / max(rate, 0.001)
            print(
                f"  Ep {ep:3d} TRAIN_REG_ON   {args.reg_lambda:<7d} | "
                f"{t_cur['loss_lsb2']:<12.1f} | {t_cur['rmse_lsb']:<11.2f} | "
                f"{t_cur['enob_bits']:<10.2f} | {str(t_cur['w8_diag']):<25} "
                f"({rate:.1f} ep/s, ETA {eta:.0f}s)"
            )

    client.close()
    total_time = time.time() - t_start

    # Save JSON log
    out_file = LOG_DIR / f"mode_a_500ep_llm_toeplitz_rho{int(args.rho*100):02d}_reg{args.reg_lambda}.json"
    summary_obj = {
        "metadata": {
            "title": "500-Epoch Mode A Silicon Training with LLM Toeplitz In-Data & L2 Regularization",
            "patent": "SE 2630397-4 (Open Science Hardware)",
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "epochs": args.epochs,
            "lr": args.lr,
            "reg_lambda": args.reg_lambda,
            "color_mode": "LLM_TOEPLITZ",
            "color_rho": args.rho,
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

    with open(out_file, "w") as f:
        json.dump(summary_obj, f, indent=2)

    print("\n" + "=" * 80)
    print(f"[+] 500-EPOCH EXPERIMENT COMPLETE in {total_time:.1f}s ({total_time/60:.2f} min)!")
    print(f"    Saved JSON: {out_file}")
    print(f"    Best Loss : {best_loss:.1f} LSB² (Ep {best_ep}) | Peak ENOB: {best_enob:.2f} bits")
    print(f"    Final Loss: {records[-1]['loss_lsb2']:.1f} LSB² | Final ENOB: {records[-1]['enob_bits']:.2f} bits")
    print("=" * 80)

    # Generate Figure
    fig_path = DOCS_DIR / f"fig_mode_a_500ep_llm_rho{int(args.rho*100):02d}_reg{args.reg_lambda}.png"
    ep_list = [r["epoch"] for r in records]
    loss_list = [r["loss_lsb2"] for r in records]
    enob_list = [r["enob_bits"] for r in records]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True, dpi=150)
    ax1.plot(ep_list, loss_list, color="#1e40af", lw=1.2, label=f"Mode A Loss (LLM Toeplitz ρ={args.rho:.2f}, Reg λ={args.reg_lambda})")
    ax1.set_ylabel("Quadratic Loss (LSB²)", fontweight="bold")
    ax1.set_yscale("log")
    ax1.grid(True, which="both", ls="--", alpha=0.5)
    ax1.legend(loc="upper right")
    ax1.set_title("Inverted MAML: 500-Epoch Mode A Training under LLM Correlated In-Data", fontweight="bold")

    ax2.plot(ep_list, enob_list, color="#047857", lw=1.2, label=f"Effective Resolution (ENOB)")
    ax2.axhline(best_enob, color="#dc2626", ls=":", lw=1.0, label=f"Peak ENOB = {best_enob:.2f} b")
    ax2.set_ylabel("Sustained ENOB (bits)", fontweight="bold")
    ax2.set_xlabel("Epoch Number", fontweight="bold")
    ax2.grid(True, which="both", ls="--", alpha=0.5)
    ax2.legend(loc="lower right")

    plt.tight_layout()
    plt.savefig(fig_path)
    plt.close()
    print(f"[+] Figure saved: {fig_path}")


if __name__ == "__main__":
    main()

