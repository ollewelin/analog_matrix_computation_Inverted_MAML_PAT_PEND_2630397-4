#!/usr/bin/env python3
"""
run_flat_baseline_experiment.py
Inverted MAML (Patent Pending SE 2630397-4) - Open Science Hardware

Experiment: Platt Baslinje (W=0) med L2-regularisering mot W_null = 0:
- Fas 1 (Epok 0..99): W = 0 (Öppen loop referens)
- Fas 2 (Epok 100..500): Aktiv träning med L2-regularisering (λ = 512) direkt från W=0.
- INGEN Fas 2-störning (ingen knä-matris som skapar 209 000 LSB² fel)!
- L2-regulariseringens ankare W_null är satt till exakt 0.
"""

import sys
import os
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
    MAML_CMD_STEP_OUTER,
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
    }


def main():
    parser = argparse.ArgumentParser(description="Platt Baslinje Experiment på Kort 2")
    parser.add_argument("--host", default="192.168.1.50")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--epochs", type=int, default=500)
    parser.add_argument("--lr", type=float, default=0.25)
    parser.add_argument("--reg-lambda", type=int, default=512)
    parser.add_argument("--rho", type=float, default=0.85)
    parser.add_argument("--d-line", type=int, default=2)
    args = parser.parse_args()

    ver_info = ensure_version_guard(host=args.host, port=args.port)
    client = MamlUdpClient(host=args.host, port=args.port, timeout=1.5)

    print("\n" + "=" * 80)
    print("INVERTED MAML: EXPERIMENT MED PLATT BASLINJE (W=0) OCH L2 MOT W_NULL=0")
    print(f"Mål: {args.host}:{args.port} | Epoker: {args.epochs} | LR: {args.lr:.2f}x | L2: λ = {args.reg_lambda}")
    print("Fas 1 (Ep 0..99): W = 0 (Öppen loop referens)")
    print("Fas 2 (Ep 100..500): Aktiv träning direkt från W=0 med L2 mot W_null = 0 (Ingen knä-störning!)")
    print("=" * 80)

    # 1. Konfigurera regim
    client.set_gain_experiment(d_line=args.d_line, w33=1, target_gain=1.0, clamp=120)
    time.sleep(0.03)

    lr_inner_q16 = max(32, min(4096, int(round(1024 * args.lr))))
    client.set_config(
        mode=0, jumper_mode=3, led_switches=3, max_meas_win_pct=100, hadamard_khz=500,
        inner_loop_n=100, seed_pct=0, seed_mode=0, w_hid_mag=0, trim_hid_mag=0,
        hadamard_delay_us=5000, lr_inner_q16=lr_inner_q16
    )
    time.sleep(0.03)
    client._send_binary(0x13, struct.pack("<BB", 1, 1)) # LEDs ON
    time.sleep(0.02)
    client.set_data_color(COLOR_LLM_TOEPLITZ, args.rho)
    time.sleep(0.03)

    # 2. Sätt PLATT baslinje och W_null = 0 i T120 RAM (91-byte all-zero payload)
    print("[*] Sätter platt baslinje: M3_null = 0, M8_null = 0, W = 0 LSB...")
    flat_payload = struct.pack("<B48b42b", 0, *([0] * 48), *([0] * 42))
    client._send_binary(MAML_CMD_CENTER_WEIGHTS, flat_payload)
    client.set_regularization(0)
    time.sleep(0.05)

    client.draw_fresh_vector()
    time.sleep(0.03)
    t0 = get_averaged_telemetry(client, n_avg=3)

    records = [{
        "epoch": 0,
        "phase": "PHASE1_W0_FLAT",
        "reg_lambda_q16": 0,
        **t0,
    }]

    t_start = time.time()
    for ep in range(1, args.epochs + 1):
        if ep < 100:
            phase = "PHASE1_W0_FLAT"
            cur_reg = 0
            is_training = False
        else:
            phase = "PHASE2_TRAIN_FLAT_START"
            cur_reg = args.reg_lambda
            is_training = True

        if ep == 100:
            print("\n" + "=" * 80)
            print(f">>> [EPOK 100]: SLÅR PÅ AKTIV TRÄNING DIREKT FRÅN W=0! (λ = {args.reg_lambda}, LR = {args.lr:.2f}x)")
            print(">>> INGEN KNÄ-STÖRNING! Träningen startar direkt från jämviktsläget!")
            print("=" * 80)
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
        records.append({
            "epoch": ep,
            "phase": phase,
            "reg_lambda_q16": cur_reg,
            **t_cur,
        })

        if ep % 50 == 0 or ep == 100 or ep == args.epochs:
            dt = time.time() - t_start
            rate = ep / max(dt, 0.001)
            print(
                f"  Ep {ep:3d} {phase:<24} | Loss={t_cur['loss_lsb2']:<8.1f} | "
                f"ENOB={t_cur['enob_bits']:<5.2f} b | W8={str(t_cur['w8_diag'])} ({rate:.1f} ep/s)"
            )

    client.close()

    # Beräkna fas-statistik
    p1_losses = [r["loss_lsb2"] for r in records if r["phase"] == "PHASE1_W0_FLAT"]
    p2_losses = [r["loss_lsb2"] for r in records if r["phase"] == "PHASE2_TRAIN_FLAT_START"]
    p1_enobs = [r["enob_bits"] for r in records if r["phase"] == "PHASE1_W0_FLAT"]
    p2_enobs = [r["enob_bits"] for r in records if r["phase"] == "PHASE2_TRAIN_FLAT_START"]

    p1_loss_m, p2_loss_m = np.mean(p1_losses), np.mean(p2_losses)
    p1_enob_m, p2_enob_m = np.mean(p1_enobs), np.mean(p2_enobs)
    delta_loss_pct = (p2_loss_m - p1_loss_m) / p1_loss_m * 100.0
    delta_enob = p2_enob_m - p1_enob_m

    print("\n" + "=" * 80)
    print("RESULTAT: PLATT BASLINJE (W=0) vs AKTIV TRÄNING DIREKT FRÅN W=0")
    print("=" * 80)
    print(f"  FAS 1 (W = 0, 100 epoker)          : Snitt Loss = {p1_loss_m:8.1f} LSB² | Snitt ENOB = {p1_enob_m:.2f} bitar")
    print(f"  FAS 2 (Träning direkt, 401 epoker) : Snitt Loss = {p2_loss_m:8.1f} LSB² | Snitt ENOB = {p2_enob_m:.2f} bitar")
    print(f"  FÖRÄNDRING (Hela fas-snittet)      : Loss = {delta_loss_pct:+6.1f}% | ENOB = {delta_enob:+.2f} bitar")
    print(f"  Bästa Loss under Träning           : {min(p2_losses):.1f} LSB² ({max(p2_enobs):.2f} bitar)")
    print("=" * 80)

    # Spara JSON
    out_json = LOG_DIR / "mode_a_flat_baseline_experiment_card2.json"
    with open(out_json, "w") as f:
        json.dump({"metadata": {"title": "Platt Baslinje Experiment", "date": time.strftime("%Y-%m-%d %H:%M:%S")}, "epochs": records}, f, indent=2)

    # Rita graf
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    epochs = [r["epoch"] for r in records]
    losses = [r["loss_lsb2"] for r in records]
    enobs = [r["enob_bits"] for r in records]

    ax1.axvspan(0, 99, color="#e3f2fd", alpha=0.5, label=f"Fas 1: Platt W=0 (Snitt: {p1_loss_m:.1f} LSB²)")
    ax1.axvspan(100, args.epochs, color="#e8f5e9", alpha=0.5, label=f"Fas 2: Träning direkt från W=0 (Snitt: {p2_loss_m:.1f} LSB²)")
    ax1.semilogy(epochs, losses, color="#1565c0", linewidth=1.5, label="Loss (LSB²)")
    ax1.set_ylabel("Loss (LSB²)", fontweight="bold")
    ax1.set_title("Inverted MAML: Platt Baslinje (W=0) med Aktiv Träning Direkt från W=0 (Ingen Knä-störning!)", fontweight="bold")
    ax1.grid(True, which="both", linestyle=":", alpha=0.6)
    ax1.legend(loc="upper right")

    ax2.axvspan(0, 99, color="#e3f2fd", alpha=0.5)
    ax2.axvspan(100, args.epochs, color="#e8f5e9", alpha=0.5)
    ax2.plot(epochs, enobs, color="#2e7d32", linewidth=1.5, label=f"ENOB (Snitt: {p2_enob_m:.2f} b, Topp: {max(p2_enobs):.2f} b)")
    ax2.set_xlabel("Epok (Kontinuerligt roterande LLM Toeplitz-brus, ρ = 0.85)", fontweight="bold")
    ax2.set_ylabel("ENOB (Bitar)", fontweight="bold")
    ax2.grid(True, linestyle=":", alpha=0.6)
    ax2.legend(loc="lower right")

    out_png = DOCS_DIR / "fig_mode_a_flat_baseline_experiment.png"
    plt.tight_layout()
    plt.savefig(out_png, dpi=160)
    plt.close()

    if ARTIFACT_DIR.exists():
        import shutil
        shutil.copy2(out_png, ARTIFACT_DIR / out_png.name)
    print(f"[+] Graf sparad till: {out_png}")


if __name__ == "__main__":
    main()

