#!/home/olle/anaconda3/bin/python
"""
optimize_smart_baseline_rev2_5ms.py
Optimizes M3 and M8 Smart Baseline weights specifically for Revision 2.0 PCB
at t = 5.0 ms pure single-stratum measurement.
"""

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
    MAML_CMD_CENTER_WEIGHTS,
    COLOR_LLM_TOEPLITZ,
)


def pack_payload(m3, m8):
    flat_m3 = [max(-120, min(120, int(v))) for row in m3 for v in row]
    flat_m8 = [max(-120, min(120, int(v))) for row in m8 for v in row]
    return struct.pack("<B48b42b", 1, *flat_m3, *flat_m8)


def measure_stats(client, n_vecs=16):
    errs = []
    adc49s = []
    adc45s = []
    for _ in range(n_vecs):
        client.draw_fresh_vector()
        time.sleep(0.012)
        t = client.get_telemetry()
        err = np.array(t.adc49_sig, dtype=float) - np.array(t.z_target, dtype=float)
        errs.append(err)
        adc49s.append(t.adc49_sig)
        adc45s.append(t.adc45_sig)

    errs = np.array(errs)
    col_mse = np.mean(errs ** 2, axis=0)
    col_mean_err = np.mean(errs, axis=0)
    col_rmse = np.sqrt(col_mse)
    total_loss = float(np.mean(np.sum(errs ** 2, axis=1) / 2.0))
    rmse = math.sqrt(max(0.0, total_loss * 2.0 / 6.0))
    enob = max(0.0, 11.0 - math.log2(max(1.0, rmse)))
    mean_adc49 = np.mean(adc49s, axis=0)
    mean_adc45 = np.mean(adc45s, axis=0)

    return {
        "loss_lsb2": total_loss,
        "rmse_lsb": rmse,
        "enob_bits": enob,
        "col_mse": col_mse,
        "col_rmse": col_rmse,
        "col_mean_err": col_mean_err,
        "mean_adc49": mean_adc49,
        "mean_adc45": mean_adc45,
    }


def main():
    client = MamlUdpClient(host="192.168.1.50", port=5000, timeout=5.0)

    print("=" * 90)
    print("REVISION 2.0 SMART BASELINE OPTIMIZATION (t = 5.0 ms ONLY, 1k/3.9k ATTENUATOR)")
    print("=" * 90)

    client.set_gain_experiment(d_line=1, w33=1, target_gain=1.0, clamp=120)
    client.set_config(
        mode=0, jumper_mode=3, led_switches=3, max_meas_win_pct=100, hadamard_khz=500,
        inner_loop_n=100, seed_pct=28, seed_mode=1, w_hid_mag=0, trim_hid_mag=0,
        hadamard_delay_us=5000, lr_inner_q16=0
    )
    client.set_data_color(COLOR_LLM_TOEPLITZ, 0.85)
    client.set_regularization(0)
    time.sleep(0.04)

    # 1. Baseline Zero (W=0)
    print("[1] Evaluating Baseline Zero (W = 0 LSB)...")
    client._send_binary(MAML_CMD_CENTER_WEIGHTS, struct.pack("<B", 0))
    time.sleep(0.08)
    base_zero = measure_stats(client, n_vecs=20)
    print(f"    W=0: Loss={base_zero['loss_lsb2']:8.1f} LSB² | RMSE={base_zero['rmse_lsb']:5.2f} LSB | ENOB={base_zero['enob_bits']:.2f} b")
    print(f"    Col Mean Error: {[round(x, 1) for x in base_zero['col_mean_err']]}")
    print(f"    Col RMSE      : {[round(x, 1) for x in base_zero['col_rmse']]}")
    print(f"    Mean ADC_49   : {[round(x, 1) for x in base_zero['mean_adc49']]}")

    # 2. Start from candidate M3 / M8 structure
    # M3 diagonal provides pass-through; rows 6 & 7 provide clock bias
    m3_opt = [
        [-16,   0,  +8,  -8,  +8,  -8],
        [  0, -16,  -8,  +8,  -8,  +8],
        [ +8,  +8, +16,   0,  +8,  -8],
        [ -8,  -8,   0, +16,  -8,  +8],
        [ +8,  +8,  -8,  +8, -16,   0],
        [ -8,  -8,  +8,  -8,   0, +16],
        [-12, -12, +12, +12, -12, +12],
        [+12, +12, -12, -12, +12, -12],
    ]

    m8_opt = [
        [-12,   0,  +4,  -4,  +4,  -4],
        [  0, -12,  -4,  +4,  -4,  +4],
        [ +4,  +4,  +6,   0,  +4,  -4],
        [ -4,  -4,   0,   0,  -4,  +4],
        [ +4,  +4,  -4,  +4, -10,   0],
        [ -4,  -4,  +4,  -4,   0,  +6],
        [  0,   0,   0,   0,   0,   0],  # Row 6 bias will be tuned per column
    ]

    # Grid search M8 row 6 bias per column to cancel column mean errors
    print("\n[2] Optimizing M8 Row 6 Bias per column (searching [-90 .. +90] step 10)...")
    best_row6 = [0] * 6
    best_col_mse = list(base_zero['col_mse'])

    # Test baseline candidate first
    payload = pack_payload(m3_opt, m8_opt)
    client._send_binary(MAML_CMD_CENTER_WEIGHTS, payload)
    time.sleep(0.04)
    st = measure_stats(client, n_vecs=12)
    print(f"    Initial Candidate: Loss={st['loss_lsb2']:8.1f} LSB² | ENOB={st['enob_bits']:.2f} b | MeanErr={[round(x, 1) for x in st['col_mean_err']]}")

    # Column-by-column 1D line sweeps for M8 row 6
    for c in range(6):
        best_val = best_row6[c]
        best_mse = 1e12
        for val in range(-90, 95, 15):
            m8_opt[6][c] = val
            payload = pack_payload(m3_opt, m8_opt)
            client._send_binary(MAML_CMD_CENTER_WEIGHTS, payload)
            time.sleep(0.02)
            res = measure_stats(client, n_vecs=10)
            mse_c = res['col_mse'][c]
            if mse_c < best_mse:
                best_mse = mse_c
                best_val = val
        best_row6[c] = best_val
        m8_opt[6][c] = best_val
        print(f"    Col {c}: Best M8[6][{c}] = {best_val:+3d} (RMSE: {math.sqrt(best_mse):.1f} LSB)")

    # Fine-tune with step 4
    print("\n[3] Fine-tuning M8 Row 6 Bias (step 4)...")
    for c in range(6):
        cur = best_row6[c]
        best_val = cur
        best_mse = 1e12
        for val in range(max(-100, cur - 16), min(100, cur + 17), 4):
            m8_opt[6][c] = val
            payload = pack_payload(m3_opt, m8_opt)
            client._send_binary(MAML_CMD_CENTER_WEIGHTS, payload)
            time.sleep(0.02)
            res = measure_stats(client, n_vecs=12)
            mse_c = res['col_mse'][c]
            if mse_c < best_mse:
                best_mse = mse_c
                best_val = val
        best_row6[c] = best_val
        m8_opt[6][c] = best_val
        print(f"    Col {c}: Fine-tuned M8[6][{c}] = {best_val:+3d} (RMSE: {math.sqrt(best_mse):.1f} LSB)")

    # Final Verification of Optimized Smart Baseline
    print("\n[4] Final Verification of Calibrated Smart Baseline (25 vecs)...")
    payload = pack_payload(m3_opt, m8_opt)
    client._send_binary(MAML_CMD_CENTER_WEIGHTS, payload)
    time.sleep(0.05)
    opt_stats = measure_stats(client, n_vecs=25)

    print("=" * 90)
    print(f"Phase 1 (W = 0 LSB)   : Loss={base_zero['loss_lsb2']:8.1f} LSB² | RMSE={base_zero['rmse_lsb']:5.2f} LSB | ENOB={base_zero['enob_bits']:.2f} b")
    print(f"  Col Mean Err (W=0)  : {[round(x, 1) for x in base_zero['col_mean_err']]}")
    print(f"Phase 2 (Rev 2.0 Smart): Loss={opt_stats['loss_lsb2']:8.1f} LSB² | RMSE={opt_stats['rmse_lsb']:5.2f} LSB | ENOB={opt_stats['enob_bits']:.2f} b")
    print(f"  Col Mean Err (Smart): {[round(x, 1) for x in opt_stats['col_mean_err']]}")
    print(f"  Col RMSE     (Smart): {[round(x, 1) for x in opt_stats['col_rmse']]}")
    print(f"  Mean ADC_49  (Smart): {[round(x, 1) for x in opt_stats['mean_adc49']]}")
    print("=" * 90)

    # Save to JSON
    cal_data = {
        "m3_opt": m3_opt,
        "m8_opt": m8_opt,
        "phase1_w0": {
            "loss_lsb2": base_zero['loss_lsb2'],
            "rmse_lsb": base_zero['rmse_lsb'],
            "enob_bits": base_zero['enob_bits'],
            "col_mean_err": [round(float(x), 2) for x in base_zero['col_mean_err']],
            "col_rmse": [round(float(x), 2) for x in base_zero['col_rmse']],
            "mean_adc49": [round(float(x), 1) for x in base_zero['mean_adc49']],
        },
        "phase2_smart": {
            "loss_lsb2": opt_stats['loss_lsb2'],
            "rmse_lsb": opt_stats['rmse_lsb'],
            "enob_bits": opt_stats['enob_bits'],
            "col_mean_err": [round(float(x), 2) for x in opt_stats['col_mean_err']],
            "col_rmse": [round(float(x), 2) for x in opt_stats['col_rmse']],
            "mean_adc49": [round(float(x), 1) for x in opt_stats['mean_adc49']],
        },
    }

    out_file = REPO_ROOT / "FPGA_code" / "logs" / "mode_a_extended_training" / "rev2_smart_baseline_5ms_opt.json"
    with open(out_file, "w") as f:
        json.dump(cal_data, f, indent=2)
    print(f"\n[+] Saved Rev 2.0 Smart Baseline to: {out_file}")

    # Output Python code snippet
    print("\nPython weights for run script:")
    print("m3_rev2 =", json.dumps(m3_opt))
    print("m8_rev2 =", json.dumps(m8_opt))

    client.close()


if __name__ == "__main__":
    main()

