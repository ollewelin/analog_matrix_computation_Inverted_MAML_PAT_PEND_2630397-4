#!/usr/bin/env python3
"""
calibrate_card2_5p1k_smart_baseline.py
Inverted MAML (Patent Pending SE 2630397-4) - Open Science Hardware

Card 2 Smart DC Null & Baseline Calibration with 1k/5.1k Ohm Summing Attenuator:
- Aligns the physical L2 regularizer anchor (W_base) directly over each column's silicon null point.
- Eliminates the static DC offset on Kolumn 3 (+352 LSB) and balances all 6 columns.
- Uses Milestone 2 regime: d_line = 2 (+/-45 LSB), LLM Toeplitz (rho = 0.85), t = 5.0 ms snapshot.
- Saves calibrated M3 (8x6) and M8 (7x6) baseline weight tables to JSON.
"""

import sys
import os
import time
import math
import json
import struct
from pathlib import Path
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from gui.udp_client import (
    MamlUdpClient,
    MAML_CMD_GET_TELEMETRY,
    MAML_CMD_CENTER_WEIGHTS,
    COLOR_LLM_TOEPLITZ,
)
from FPGA_code.scripts.verify_and_guard_version import ensure_version_guard

LOG_DIR = REPO_ROOT / "FPGA_code" / "logs" / "llm_noise_campaign"
LOG_DIR.mkdir(parents=True, exist_ok=True)
OUT_JSON = LOG_DIR / "card2_5p1k_smart_baseline.json"


def pack_smart_baseline_payload(m3_8x6: list[list[int]], m8_7x6: list[list[int]]) -> bytes:
    flat_m3 = []
    for r in range(8):
        for c in range(6):
            flat_m3.append(max(-120, min(120, int(m3_8x6[r][c]))))
    flat_m8 = []
    for r in range(7):
        for c in range(6):
            flat_m8.append(max(-120, min(120, int(m8_7x6[r][c]))))
    return struct.pack("<B48b42b", 1, *flat_m3, *flat_m8)


def measure_multi_vector_stats(client: MamlUdpClient, n_vecs: int = 24) -> dict:
    errs = []
    adc45s = []
    adc49s = []
    z_targets = []
    for _ in range(n_vecs):
        t = client.draw_fresh_vector()
        if t and t.connected_hw:
            err = np.array(t.adc49_sig, dtype=np.float64) - np.array(t.z_target, dtype=np.float64)
            errs.append(err)
            adc45s.append(t.adc45_sig)
            adc49s.append(t.adc49_sig)
            z_targets.append(t.z_target)
        time.sleep(0.005)

    err_arr = np.array(errs)
    col_mean_err = np.mean(err_arr, axis=0)
    col_std_err = np.std(err_arr, axis=0)
    col_mse = np.mean(err_arr ** 2, axis=0)
    col_rmse = np.sqrt(col_mse)

    vec_losses = np.sum(err_arr ** 2, axis=1) / 2.0
    vec_rmses = np.sqrt(np.mean(err_arr ** 2, axis=1))
    vec_enobs = [max(0.0, 11.0 - math.log2(max(float(r), 1.0))) for r in vec_rmses]

    return {
        "mean_loss_lsb2": float(np.mean(vec_losses)),
        "mean_rmse_lsb": float(np.mean(vec_rmses)),
        "mean_enob_bits": float(np.mean(vec_enobs)),
        "col_mean_err": [round(float(x), 2) for x in col_mean_err],
        "col_std_err": [round(float(x), 2) for x in col_std_err],
        "col_rmse": [round(float(x), 2) for x in col_rmse],
        "col_mse": [round(float(x), 1) for x in col_mse],
        "mean_adc45": [round(float(x), 1) for x in np.mean(adc45s, axis=0)],
        "mean_adc49": [round(float(x), 1) for x in np.mean(adc49s, axis=0)],
    }


def build_candidate_tables(
    m3_diag: list[int],
    m3_off: list[int],
    m3_row6: list[int],
    m3_row7: list[int],
    m8_diag: list[int],
    m8_off: list[int],
    m8_row6: list[int],
) -> tuple[list[list[int]], list[list[int]]]:
    m3 = [[0] * 6 for _ in range(8)]
    m8 = [[0] * 6 for _ in range(7)]

    for c in range(6):
        off_idx = 0
        pattern = [0, +1, -1, +1, -1]
        for r in range(6):
            if r == c:
                m3[r][c] = int(m3_diag[c])
                m8[r][c] = int(m8_diag[c])
            else:
                s = pattern[off_idx]
                off_idx += 1
                m3[r][c] = int(s * m3_off[c])
                m8[r][c] = int(s * m8_off[c])
        m3[6][c] = int(m3_row6[c])
        m3[7][c] = int(m3_row7[c])
        m8[6][c] = int(m8_row6[c])

    return m3, m8


def main():
    ensure_version_guard(host="192.168.1.50", port=5000)
    client = MamlUdpClient(host="192.168.1.50", port=5000, timeout=3.0)

    print("=" * 84)
    print("CARD 2 (1k/5.1k) SMART DC NULL & BASELINE CALIBRATION")
    print("Target: 192.168.1.50:5000 | Regime: Milestone 2 (d_line=2, +/-45 LSB, rho=0.85, 5.0 ms)")
    print("=" * 84)

    client.set_gain_experiment(d_line=2, w33=1, target_gain=1.0, clamp=120)
    time.sleep(0.03)

    lr_inner_q16 = int(round(1024 * 0.25))
    client.set_config(
        mode=0, jumper_mode=3, led_switches=3, max_meas_win_pct=100, hadamard_khz=500,
        inner_loop_n=100, seed_pct=0, seed_mode=0, w_hid_mag=0, trim_hid_mag=0,
        hadamard_delay_us=5000, lr_inner_q16=lr_inner_q16
    )
    time.sleep(0.03)
    client.set_data_color(COLOR_LLM_TOEPLITZ, 0.85)
    client.set_regularization(0)
    time.sleep(0.03)

    # 1. Measure Initial W=0 Baseline
    print("\n[1] Mäter Initial W=0 Quiescent Baslinje (g_baseline_mode=0)...")
    client._send_binary(MAML_CMD_CENTER_WEIGHTS, struct.pack("<B", 0))
    time.sleep(0.08)

    w0_stats = measure_multi_vector_stats(client, n_vecs=24)
    print(f"    W=0 Medel Loss: {w0_stats['mean_loss_lsb2']:.1f} LSB² | RMSE: {w0_stats['mean_rmse_lsb']:.2f} LSB | ENOB: {w0_stats['mean_enob_bits']:.2f} b")
    print(f"    DC Offset per Kolumn: {w0_stats['col_mean_err']}")
    print(f"    RMSE per Kolumn     : {w0_stats['col_rmse']}")
    print(f"    ADC49 Medel (LSB)   : {w0_stats['mean_adc49']}")

    # 2. Template Matrix 3 (preserve smooth S-bend knee from Card 1)
    m3_diag = [-16, -16, +16, +16, -16, +16]
    m3_off  = [  6,   6,   6,   6,   6,   6]
    m3_row6 = [-12, -12, +12, +12, -12, +12]
    m3_row7 = [+12, +12, -12, -12, +12, -12]

    # 3. Sweep Matrix 8 Bias Row 6 per column to zero out the DC offset!
    print("\n[2] Sveper Matrix 8 Bias Row 6 per kolumn för att släcka DC-offset...")
    best_col_mse = [1e12] * 6
    best_m8_diag = [0] * 6
    best_m8_off  = [4] * 6
    best_m8_row6 = [0] * 6

    # Test both polarities of M8 diag and sweep Row 6 bias across [-56 .. +56] in steps of 8
    total_steps = 4 * len(range(-56, 60, 8))
    step_cnt = 0
    for d8_val in [-16, -12, +12, +16]:
        for b6_val in range(-56, 60, 8):
            step_cnt += 1
            cand_m8_diag = [d8_val] * 6
            cand_m8_off  = [4] * 6
            cand_m8_row6 = [b6_val] * 6
            m3_cand, m8_cand = build_candidate_tables(
                m3_diag, m3_off, m3_row6, m3_row7,
                cand_m8_diag, cand_m8_off, cand_m8_row6
            )
            payload = pack_smart_baseline_payload(m3_cand, m8_cand)
            client._send_binary(MAML_CMD_CENTER_WEIGHTS, payload)
            time.sleep(0.015)
            st = measure_multi_vector_stats(client, n_vecs=8)
            for c in range(6):
                # We prioritize minimizing column MSE, which penalizes both DC offset and variance
                if st["col_mse"][c] < best_col_mse[c]:
                    best_col_mse[c] = st["col_mse"][c]
                    best_m8_diag[c] = d8_val
                    best_m8_row6[c] = b6_val
            if step_cnt % 10 == 0 or step_cnt == total_steps:
                print(f"    Grovsvep framsteg: {step_cnt}/{total_steps} (d8={d8_val:+d}, b6={b6_val:+d}) | Bäst MSE={min(best_col_mse):.0f}", flush=True)

    print(f"    Grov Optimal Baslinje:")
    print(f"      best_m8_diag = {best_m8_diag}")
    print(f"      best_m8_row6 = {best_m8_row6}")
    print(f"      RMSE per kolumn = {[round(math.sqrt(m), 1) for m in best_col_mse]}")

    # 4. Fine-Tune M8 Bias Row 6 in fine steps of 2 LSB
    print("\n[3] Finjusterar M8 Bias Row 6 (steg = 2 LSB) över 16 Toeplitz-vektorer...")
    base_b6 = list(best_m8_row6)
    for delta in range(-8, 10, 2):
        cand_m8_row6 = [max(-120, min(120, base_b6[c] + delta)) for c in range(6)]
        m3_cand, m8_cand = build_candidate_tables(
            m3_diag, m3_off, m3_row6, m3_row7,
            best_m8_diag, best_m8_off, cand_m8_row6
        )
        payload = pack_smart_baseline_payload(m3_cand, m8_cand)
        client._send_binary(MAML_CMD_CENTER_WEIGHTS, payload)
        time.sleep(0.015)
        st = measure_multi_vector_stats(client, n_vecs=16)
        for c in range(6):
            if st["col_mse"][c] < best_col_mse[c]:
                best_col_mse[c] = st["col_mse"][c]
                best_m8_row6[c] = cand_m8_row6[c]

    print(f"    Finjusterad Optimal Baslinje:")
    print(f"      best_m8_diag = {best_m8_diag}")
    print(f"      best_m8_row6 = {best_m8_row6}")
    print(f"      RMSE per kolumn = {[round(math.sqrt(m), 1) for m in best_col_mse]}")

    # 5. Full Side-by-Side Verification: W=0 vs New Calibrated Smart Baseline (32 vecs)
    print("\n[4] Slutlig Verifiering över 32 Roterande Toeplitz-vektorer:")
    client._send_binary(MAML_CMD_CENTER_WEIGHTS, struct.pack("<B", 0))
    time.sleep(0.06)
    final_w0 = measure_multi_vector_stats(client, n_vecs=32)

    m3_opt, m8_opt = build_candidate_tables(
        m3_diag, m3_off, m3_row6, m3_row7,
        best_m8_diag, best_m8_off, best_m8_row6
    )
    payload_opt = pack_smart_baseline_payload(m3_opt, m8_opt)
    client._send_binary(MAML_CMD_CENTER_WEIGHTS, payload_opt)
    time.sleep(0.06)
    final_smart = measure_multi_vector_stats(client, n_vecs=32)

    print("-" * 84)
    print(f"  Phase 1 (W = 0 LSB Okompenserad): Loss = {final_w0['mean_loss_lsb2']:8.1f} LSB² | RMSE = {final_w0['mean_rmse_lsb']:5.2f} LSB | ENOB = {final_w0['mean_enob_bits']:.2f} b")
    print(f"    DC Offset (W=0):  {final_w0['col_mean_err']}")
    print(f"    RMSE (W=0)     :  {final_w0['col_rmse']}")
    print(f"  Phase 2 (NY KALIBRERAD SMART BASLINJE): Loss = {final_smart['mean_loss_lsb2']:8.1f} LSB² | RMSE = {final_smart['mean_rmse_lsb']:5.2f} LSB | ENOB = {final_smart['mean_enob_bits']:.2f} b")
    print(f"    DC Offset (Smart): {final_smart['col_mean_err']}")
    print(f"    RMSE (Smart)     : {final_smart['col_rmse']}")
    print("-" * 84)

    # Save to JSON
    cal_data = {
        "title": "Card 2 Smart DC Null Baseline Calibration (1k/5.1k Attenuator)",
        "hardware": "Card 2 (Rev 2.0 Silicon, 1k/5.1k attenuator, MCP6444 on DAC2)",
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "best_m8_diag": best_m8_diag,
        "best_m8_row6_bias": best_m8_row6,
        "m3_opt": m3_opt,
        "m8_opt": m8_opt,
        "payload_hex": payload_opt.hex(),
        "phase1_w0": final_w0,
        "phase2_smart": final_smart,
    }
    with open(OUT_JSON, "w") as f:
        json.dump(cal_data, f, indent=2)

    print(f"\n[+] Kalibrering sparad till: {OUT_JSON.name}")
    client.close()


if __name__ == "__main__":
    main()

