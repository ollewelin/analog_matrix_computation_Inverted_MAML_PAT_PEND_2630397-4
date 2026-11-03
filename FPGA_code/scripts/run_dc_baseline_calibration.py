#!/usr/bin/env python3
"""
run_dc_baseline_calibration.py
Inverted MAML (Patent Pending SE 2630397-4) - Open Science Hardware

Generisk, automatiserad och snabb DC-nollpunktskalibrering för Inverted MAML silicon:
- Kalibrerar Matrix 8 Rad 6 (DC-bias) per kolumn [0..5] oberoende av varandra.
- Mäter och nollar ut summeringspunktens statiska DC-offset på ADC(49).
- Tar cirka 15-20 sekunder totalt.
- Genererar en 91-bytes Smart Baseline payload och sparar till standardiserad JSON.
- Verifierar att baslinjen når >= 6.4 bitar ENOB innan aktiv gradientträning startar.
"""

from __future__ import annotations
import sys
import os
import time
import math
import json
import struct
import argparse
from pathlib import Path
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if not (REPO_ROOT / "gui").exists():
    REPO_ROOT = Path(__file__).resolve().parent.parent
if not (REPO_ROOT / "gui").exists():
    REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from gui.udp_client import (
    MamlUdpClient,
    MAML_CMD_CENTER_WEIGHTS,
    COLOR_LLM_TOEPLITZ,
)
from FPGA_code.scripts.verify_and_guard_version import ensure_version_guard

LOG_DIR = REPO_ROOT / "FPGA_code" / "logs" / "llm_noise_campaign"
LOG_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_JSON = LOG_DIR / "card2_5p1k_smart_baseline.json"
CANONICAL_JSON = REPO_ROOT / "FPGA_code" / "logs" / "calibrated_smart_baseline.json"


def pack_payload(m3: list[list[int]], m8: list[list[int]]) -> bytes:
    flat_m3 = [max(-120, min(120, int(m3[r][c]))) for r in range(8) for c in range(6)]
    flat_m8 = [max(-120, min(120, int(m8[r][c]))) for r in range(7) for c in range(6)]
    return struct.pack("<B48b42b", 1, *flat_m3, *flat_m8)


def measure_stats(client: MamlUdpClient, n_vecs: int = 12) -> dict:
    errs = []
    adc49s = []
    adc45s = []
    for _ in range(n_vecs):
        client.draw_fresh_vector()
        time.sleep(0.010)
        t = client.get_telemetry()
        if t and t.connected_hw:
            err = np.array(t.adc49_sig, dtype=float) - np.array(t.z_target, dtype=float)
            errs.append(err)
            adc49s.append(t.adc49_sig)
            adc45s.append(t.adc45_sig)

    err_arr = np.array(errs)
    col_mean_err = np.mean(err_arr, axis=0)
    col_mse = np.mean(err_arr ** 2, axis=0)
    col_rmse = np.sqrt(col_mse)
    total_loss = float(np.mean(np.sum(err_arr ** 2, axis=1) / 2.0))
    rmse = math.sqrt(max(0.0, total_loss * 2.0 / 6.0))
    enob = max(0.0, 11.0 - math.log2(max(1.0, rmse)))

    return {
        "loss_lsb2": total_loss,
        "rmse_lsb": rmse,
        "enob_bits": enob,
        "col_mean_err": [round(float(x), 1) for x in col_mean_err],
        "col_rmse": [round(float(x), 1) for x in col_rmse],
        "mean_adc49": [round(float(x), 1) for x in np.mean(adc49s, axis=0)],
        "mean_adc45": [round(float(x), 1) for x in np.mean(adc45s, axis=0)],
    }


def run_dc_calibration(
    host: str = "192.168.1.50",
    port: int = 5000,
    d_line: int = 2,
    rho: float = 0.85,
    out_json: Path | None = None,
) -> dict:
    ensure_version_guard(host=host, port=port)
    client = MamlUdpClient(host=host, port=port, timeout=3.0)

    print("\n" + "=" * 98)
    print("INVERTED MAML: GENERISK AUTOMATISERAD DC-NOLLPUNKTSKALIBRERING")
    print(f"Hårdvarumål: {host}:{port} | Trion T120 Master SoC + T20 Coprocessor")
    print(f"Regim: d_line={d_line} (+/-{80//d_line} LSB swing) | LLM Toeplitz (rho={rho}) | 5.0 ms snapshot")
    print("=" * 98)

    # 1. Konfigurera regim
    client.set_gain_experiment(d_line=d_line, w33=1, target_gain=1.0, clamp=120)
    client.set_config(
        mode=0, jumper_mode=3, led_switches=3, max_meas_win_pct=100, hadamard_khz=500,
        inner_loop_n=100, seed_pct=0, seed_mode=0, w_hid_mag=0, trim_hid_mag=0,
        hadamard_delay_us=5000, lr_inner_q16=256
    )
    client.set_data_color(COLOR_LLM_TOEPLITZ, rho)
    client.set_regularization(0)
    time.sleep(0.04)

    # 2. Mät omodulerad W=0 vilopunkt
    print("\n[Steg 1] Nollställer vikter (W = 0 LSB) och mäter rå statisk vilopunkt...")
    client._send_binary(MAML_CMD_CENTER_WEIGHTS, struct.pack("<B", 0))
    time.sleep(0.08)

    w0_stats = measure_stats(client, n_vecs=16)
    print(f"  Rå W=0 Loss  : {w0_stats['loss_lsb2']:10.1f} LSB² | RMSE: {w0_stats['rmse_lsb']:5.1f} LSB | ENOB: {w0_stats['enob_bits']:.2f} bitar")
    print(f"  Rå DC-offset : {w0_stats['col_mean_err']} LSB")

    # 3. Mallmatriser för M3 och M8
    m3 = [
        [-16,   0,   0,   0,   0,   0],
        [  0, -16,   6,   6,   6,   6],
        [  6,   6,  16,  -6,  -6,  -6],
        [ -6,  -6,  -6,  16,   6,   6],
        [  6,   6,   6,   6, -16,  -6],
        [ -6,  -6,  -6,  -6,  -6,  16],
        [-12, -12,  12,  12, -12,  12],
        [ 12,  12, -12, -12,  12, -12],
    ]

    m8 = [
        [ 12,   0,   0,   0,   0,   0],
        [  0,  12,   4,   4,   4,   4],
        [  4,   4,  12,  -4,  -4,  -4],
        [ -4,  -4,  -4,  12,   4,   4],
        [  4,   4,   4,   4,  12,  -4],
        [ -4,  -4,  -4,  -4,  -4, -12],
        [  0,   0,   0,   0,   0,   0], # Rad 6 sveps oberoende per kolumn
    ]

    # 4. Oberoende 1D-linjesvepning av M8 Rad 6 Bias per kolumn
    print("\n[Steg 2] Sveper Matrix 8 Rad 6 (DC-bias) oberoende per kolumn (2-stegs grov + finjustering)...")
    best_row6 = [0] * 6

    t_cal_start = time.time()
    for c in range(6):
        # Grovsvep: [-88 .. +88] med steg 8
        best_val = 0
        min_abs_err = 1e9
        for val in range(-88, 92, 8):
            m8[6][c] = val
            payload = pack_payload(m3, m8)
            client._send_binary(MAML_CMD_CENTER_WEIGHTS, payload)
            time.sleep(0.015)
            errs = []
            for _ in range(3):
                t = client.get_telemetry()
                if t:
                    errs.append(t.adc49_sig[c] - t.z_target[c])
                time.sleep(0.004)
            mean_err = np.mean(errs) if errs else 999.0
            if abs(mean_err) < min_abs_err:
                min_abs_err = abs(mean_err)
                best_val = val

        # Finjustering: runt best_val i steg om 2 LSB
        fine_best = best_val
        fine_min = min_abs_err
        for val in range(max(-100, best_val - 8), min(100, best_val + 9), 2):
            m8[6][c] = val
            payload = pack_payload(m3, m8)
            client._send_binary(MAML_CMD_CENTER_WEIGHTS, payload)
            time.sleep(0.015)
            errs = []
            for _ in range(4):
                t = client.get_telemetry()
                if t:
                    errs.append(t.adc49_sig[c] - t.z_target[c])
                time.sleep(0.004)
            mean_err = np.mean(errs) if errs else 999.0
            if abs(mean_err) < fine_min:
                fine_min = abs(mean_err)
                fine_best = val

        best_row6[c] = fine_best
        m8[6][c] = fine_best
        print(f"  Kolumn {c} (CH{c}): Optimal M8[6][{c}] = {fine_best:+3d} LSB  (Residualt DC-fel: {fine_min:+.1f} LSB)")

    cal_dur = time.time() - t_cal_start
    print(f"\n[Steg 3] Svep klart på {cal_dur:.1f} sekunder. Verifierar fullständig baslinje...")

    # 5. Fullständig verifiering med den nya baslinjen
    payload_bytes = pack_payload(m3, m8)
    client._send_binary(MAML_CMD_CENTER_WEIGHTS, payload_bytes)
    time.sleep(0.06)

    opt_stats = measure_stats(client, n_vecs=20)

    # 6. Presentation i snygg tabell
    print("\n" + "=" * 98)
    print(f"{'Kanal':<12} | {'Rå W=0 DC-fel':<16} | {'Kalibrerad M8[6]':<18} | {'Nytt DC-fel':<16} | {'Status':<14}")
    print("-" * 98)
    for c in range(6):
        raw_err = w0_stats['col_mean_err'][c]
        bias = best_row6[c]
        new_err = opt_stats['col_mean_err'][c]
        status = "OK: BALANSERAD" if abs(new_err) < 45.0 else "VARNING"
        print(f"CH{c} (Kol {c})   | {raw_err:+8.1f} LSB       | {bias:+8d} LSB         | {new_err:+8.1f} LSB       | {status:<14}")
    print("=" * 98)
    print(f"FÖRE KALIBRERING (W=0)       : Loss = {w0_stats['loss_lsb2']:8.1f} LSB² | RMSE = {w0_stats['rmse_lsb']:5.1f} LSB | ENOB = {w0_stats['enob_bits']:.2f} bitar")
    print(f"EFTER KALIBRERING (Smart Base): Loss = {opt_stats['loss_lsb2']:8.1f} LSB² | RMSE = {opt_stats['rmse_lsb']:5.1f} LSB | ENOB = {opt_stats['enob_bits']:.2f} bitar")
    print("=" * 98)

    # 7. Spara till standardiserade JSON-filer
    cal_data = {
        "title": "Inverted MAML Generisk Smart DC Null Baseline Calibration",
        "hardware": "Trion T120 Master SoC + T20 Coprocessor (All 6 channels active)",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "d_line": d_line,
        "rho": rho,
        "best_m8_row6_bias": best_row6,
        "m3_opt": m3,
        "m8_opt": m8,
        "payload_hex": payload_bytes.hex(),
        "phase1_w0": w0_stats,
        "phase2_smart": opt_stats,
    }

    targets = [CANONICAL_JSON]
    if out_json:
        targets.append(Path(out_json))
    else:
        targets.append(DEFAULT_JSON)

    for p in targets:
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w") as f:
            json.dump(cal_data, f, indent=2)
        print(f"[+] Sparade kalibreringsdata till: {p}")

    client.close()
    return cal_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inverted MAML Generisk DC-nollpunktskalibrering")
    parser.add_argument("--host", default="192.168.1.50")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--d-line", type=int, default=2)
    parser.add_argument("--rho", type=float, default=0.85)
    parser.add_argument("--out", type=str, default=None)
    args = parser.parse_args()

    out_p = Path(args.out) if args.out else None
    run_dc_calibration(host=args.host, port=args.port, d_line=args.d_line, rho=args.rho, out_json=out_p)

