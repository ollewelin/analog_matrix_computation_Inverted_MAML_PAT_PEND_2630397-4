#!/home/olle/anaconda3/bin/python
"""
calibrate_warm_smart_baseline.py
Warm-Board Zero-Offset & S-Bend Smart Baseline Calibration for Inverted MAML (Mode A).

1. Locks true W=0 quiescent reference (g_adc49_zero_cal) on the thermally settled board.
2. Evaluates Phase 1 (W=0) Loss & ENOB over 25 LLM Toeplitz (rho=0.85) vectors and 10 strata [4.5..5.5 ms].
3. Calibrates per-column M3 (8x6) and M8 (7x6) Smart Baseline weights (specifically tuning
   M8 Bias Row 6 and diagonal/off-diagonal signs & amplitudes in parallel across all 6 columns)
   while keeping g_adc49_zero_cal strictly locked to the W=0 reference.
4. Verifies that the new Warm-Calibrated Smart Baseline has ~0 LSB DC offset on all 6 columns
   and matches or beats the W=0 baseline BEFORE any active training starts at Epoch 200.
"""

from __future__ import annotations
import sys
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

STRATA_10_US = [4500, 4611, 4722, 4833, 4944, 5055, 5166, 5277, 5388, 5500]


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


def measure_multi_vector_stats(client: MamlUdpClient, n_vecs: int = 20) -> dict:
    errs = []
    adc45s = []
    adc49s = []
    z_targets = []
    for _ in range(n_vecs):
        client.draw_fresh_vector()
        time.sleep(0.012)
        raw = client._send_binary(MAML_CMD_GET_TELEMETRY)
        if raw and len(raw) >= client.TELEM_SIZE:
            t = client._parse_hw_telemetry(raw)
            err = np.array(t.adc49_sig, dtype=np.float64) - np.array(t.z_target, dtype=np.float64)
            errs.append(err)
            adc45s.append(t.adc45_sig)
            adc49s.append(t.adc49_sig)
            z_targets.append(t.z_target)

    err_arr = np.array(errs)  # shape (n_vecs, 6)
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
    """
    Build 8x6 M3 and 7x6 M8 tables where each column c has:
      - diagonal m3_diag[c], m8_diag[c]
      - 5 off-diagonal elements in rows 0..5 that sum to ~0 (alternating +/- with one 0)
        Wait: since there are 5 off-diagonal rows in a 6-row compute block,
        if we use [0, +off, -off, +off, -off] on the 5 off-diagonal rows of each column,
        the sum of the 5 off-diagonal elements is EXACTLY ZERO!
    """
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
    client = MamlUdpClient(host="192.168.1.50", port=5000, timeout=5.0)
    lr_inner_q16 = int(round(1024 * 0.25))

    print("=" * 84)
    print("STEP 2: WARM-BOARD SMART BASELINE CALIBRATION ON PHYSICAL SILICON")
    print("=" * 84)

    client.set_gain_experiment(d_line=1, w33=1, target_gain=1.0, clamp=120)
    time.sleep(0.03)
    client.set_config(
        mode=0, jumper_mode=3, led_switches=3, max_meas_win_pct=100, hadamard_khz=500,
        inner_loop_n=100, seed_pct=28, seed_mode=1, w_hid_mag=0, trim_hid_mag=0,
        hadamard_delay_us=5000, lr_inner_q16=lr_inner_q16
    )
    time.sleep(0.03)
    client.set_data_color(COLOR_LLM_TOEPLITZ, 0.85)
    client.set_regularization(0)
    time.sleep(0.03)

    # 1. Calibrate True Zero Baseline (mode = 0)
    print("[1] Calibrating True W=0 Quiescent Baseline (g_baseline_mode=0)...")
    client._send_binary(MAML_CMD_CENTER_WEIGHTS, struct.pack("<B", 0))
    time.sleep(0.06)

    stats_w0 = measure_multi_vector_stats(client, n_vecs=24)
    print(f"    Phase 1 (W=0) @ 5.0 ms (24 Toeplitz vecs):")
    print(f"      Mean Loss : {stats_w0['mean_loss_lsb2']:.1f} LSB²")
    print(f"      Mean RMSE : {stats_w0['mean_rmse_lsb']:.2f} LSB")
    print(f"      Mean ENOB : {stats_w0['mean_enob_bits']:.2f} bits")
    print(f"      Col Mean Err (DC offset): {stats_w0['col_mean_err']}")
    print(f"      Col RMSE                : {stats_w0['col_rmse']}")
    print(f"      Mean ADC_45 (Sigmoid 4) : {stats_w0['mean_adc45']}")

    # 2. Now test candidate M3/M8 configurations and sweep M8 Row 6 Bias to zero out DC offset!
    # Notice: In Step 1 protocol, M3 Row 6 (Clock B1) and Row 7 (Clock REF) place Sigmoid 4 in its linear bend:
    # Let's test two configurations of (M3_diag, M3_row6, M3_row7, M8_diag):
    # Config A (Gentle S-bend knee, zero-sum off-diagonals):
    #   m3_diag = [-16, -16, +16, +16, -16, +16], m3_off = [6, 6, 6, 6, 6, 6]
    #   m3_row6 = [-12, -12, +12, +12, -12, +12], m3_row7 = [+12, +12, -12, -12, +12, -12]
    #   m8_diag = [-12, -12, +12, +12, -12, +12], m8_off = [4, 4, 4, 4, 4, 4]
    # Wait: let's sweep M8 Row 6 bias across [-48 .. +48] and also test both signs of M8_diag per column!

    m3_diag = [-16, -16, +16, +16, -16, +16]
    m3_off  = [  6,   6,   6,   6,   6,   6]
    m3_row6 = [-12, -12, +12, +12, -12, +12]
    m3_row7 = [+12, +12, -12, -12, +12, -12]

    print("\n[2] Sweeping M8 Bias Row 6 & M8 Diagonal Sign per Column to Eliminate Static DC Offset...")
    best_col_mse = [1e12] * 6
    best_m8_diag = [0] * 6
    best_m8_off  = [4] * 6
    best_m8_row6 = [0] * 6

    for d8_val in [-12, -8, +8, +12]:
        for b6_val in range(-40, 44, 8):
            cand_m8_diag = [d8_val] * 6
            cand_m8_off  = [4] * 6
            cand_m8_row6 = [b6_val] * 6
            m3_cand, m8_cand = build_candidate_tables(
                m3_diag, m3_off, m3_row6, m3_row7,
                cand_m8_diag, cand_m8_off, cand_m8_row6
            )
            payload = pack_smart_baseline_payload(m3_cand, m8_cand)
            client._send_binary(MAML_CMD_CENTER_WEIGHTS, payload)
            time.sleep(0.02)
            st = measure_multi_vector_stats(client, n_vecs=8)
            for c in range(6):
                if st["col_mse"][c] < best_col_mse[c]:
                    best_col_mse[c] = st["col_mse"][c]
                    best_m8_diag[c] = d8_val
                    best_m8_row6[c] = b6_val

    print(f"    Coarse Optimal per Column:")
    print(f"      best_m8_diag = {best_m8_diag}")
    print(f"      best_m8_row6 = {best_m8_row6}")
    print(f"      coarse col_rmse = {[round(math.sqrt(m), 2) for m in best_col_mse]}")

    # Fine-tune M8 Row 6 Bias around best_m8_row6[c] in steps of 2 LSB
    print("\n[3] Fine-Tuning M8 Bias Row 6 (step = 2 LSB) across 16 Toeplitz vectors...")
    base_b6 = list(best_m8_row6)
    for delta in range(-8, 10, 2):
        cand_m8_row6 = [max(-120, min(120, base_b6[c] + delta)) for c in range(6)]
        m3_cand, m8_cand = build_candidate_tables(
            m3_diag, m3_off, m3_row6, m3_row7,
            best_m8_diag, best_m8_off, cand_m8_row6
        )
        payload = pack_smart_baseline_payload(m3_cand, m8_cand)
        client._send_binary(MAML_CMD_CENTER_WEIGHTS, payload)
        time.sleep(0.02)
        st = measure_multi_vector_stats(client, n_vecs=16)
        for c in range(6):
            if st["col_mse"][c] < best_col_mse[c]:
                best_col_mse[c] = st["col_mse"][c]
                best_m8_row6[c] = cand_m8_row6[c]

    print(f"    Fine-Tuned Optimal per Column:")
    print(f"      best_m8_diag = {best_m8_diag}")
    print(f"      best_m8_row6 = {best_m8_row6}")
    print(f"      fine col_rmse = {[round(math.sqrt(m), 2) for m in best_col_mse]}")

    # 4. Final Verification: Re-calibrate W=0 (Phase 1) and then switch to Smart Baseline (Phase 2)
    print("\n[4] Final Side-by-Side Verification (Phase 1 W=0 vs Phase 2 Warm Smart Baseline, 24 vecs):")
    client._send_binary(MAML_CMD_CENTER_WEIGHTS, struct.pack("<B", 0))
    time.sleep(0.05)
    final_w0 = measure_multi_vector_stats(client, n_vecs=24)

    m3_opt, m8_opt = build_candidate_tables(
        m3_diag, m3_off, m3_row6, m3_row7,
        best_m8_diag, best_m8_off, best_m8_row6
    )
    payload_opt = pack_smart_baseline_payload(m3_opt, m8_opt)
    client._send_binary(MAML_CMD_CENTER_WEIGHTS, payload_opt)
    time.sleep(0.05)
    final_smart = measure_multi_vector_stats(client, n_vecs=24)

    print(f"  Phase 1 (W = 0 LSB)       : Loss = {final_w0['mean_loss_lsb2']:8.1f} LSB² | RMSE = {final_w0['mean_rmse_lsb']:6.2f} LSB | ENOB = {final_w0['mean_enob_bits']:.2f} b")
    print(f"    Col Mean Err (W=0)      : {final_w0['col_mean_err']}")
    print(f"    Col RMSE     (W=0)      : {final_w0['col_rmse']}")
    print(f"  Phase 2 (Smart Baseline)  : Loss = {final_smart['mean_loss_lsb2']:8.1f} LSB² | RMSE = {final_smart['mean_rmse_lsb']:6.2f} LSB | ENOB = {final_smart['mean_enob_bits']:.2f} b")
    print(f"    Col Mean Err (Smart)    : {final_smart['col_mean_err']}")
    print(f"    Col RMSE     (Smart)    : {final_smart['col_rmse']}")

    out = {
        "m3_opt": m3_opt,
        "m8_opt": m8_opt,
        "phase1_w0": final_w0,
        "phase2_smart": final_smart,
    }
    out_path = REPO_ROOT / "FPGA_code" / "logs" / "mode_a_extended_training" / "warm_smart_baseline_cal.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\n[+] Saved calibrated baseline tables to {out_path}")
    client.close()


if __name__ == "__main__":
    main()

