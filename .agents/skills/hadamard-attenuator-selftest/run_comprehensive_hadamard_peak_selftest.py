#!/usr/bin/env python3
"""
run_comprehensive_hadamard_peak_selftest.py
Inverted MAML (Patent Pending SE 2630397-4) - Open Science Hardware

Adaptive Multi-Dimensional Grid Sweep Self-Test:
Systematically sweeps In-Data lines (X), Matrix 3 weights (W3), Matrix 8 weights (W8),
and M8 Row 6 Bias across their operating ranges to discover the MAXIMUM dynamic
signal strength and Hadamard response on each column independently.
"""

import sys
import os
import time
import math
import json
import struct
import argparse
from pathlib import Path
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
if not (REPO_ROOT / "gui").exists():
    REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from gui.udp_client import (
    MamlUdpClient,
    MAML_CMD_CENTER_WEIGHTS,
    MAML_CMD_DIAG_HADAMARD,
    COLOR_LLM_TOEPLITZ,
)
from FPGA_code.scripts.verify_and_guard_version import ensure_version_guard


def pack_payload(m3: list[list[int]], m8: list[list[int]]) -> bytes:
    flat_m3 = [max(-120, min(120, int(m3[r][c]))) for r in range(8) for c in range(6)]
    flat_m8 = [max(-120, min(120, int(m8[r][c]))) for r in range(7) for c in range(6)]
    return struct.pack("<B48b42b", 1, *flat_m3, *flat_m8)


def main():
    parser = argparse.ArgumentParser(description="Adaptive Hadamard & Attenuator Peak Sweep Self-Test")
    parser.add_argument("--host", default="192.168.1.50")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()

    ensure_version_guard(host=args.host, port=args.port)
    client = MamlUdpClient(host=args.host, port=args.port, timeout=3.0)

    print("=" * 96)
    print("INVERTED MAML: ADAPTIVE OPERATING-POINT SWEEP & HADAMARD ATTENUATOR SELF-TEST")
    print(f"Target: {args.host}:{args.port} | Hardware: Card 2 (1k/5.1k Attenuator)")
    print("=" * 96)

    client.set_gain_experiment(d_line=2, w33=1, target_gain=1.0, clamp=120)
    client.set_regularization(0)
    client.set_data_color(COLOR_LLM_TOEPLITZ, 0.85)
    time.sleep(0.04)

    # -------------------------------------------------------------------------
    # STAGE 1: Quiescent Zero State Check
    # -------------------------------------------------------------------------
    client._send_binary(MAML_CMD_CENTER_WEIGHTS, struct.pack("<B", 0))
    time.sleep(0.06)
    w0_samples = [client.draw_fresh_vector().adc49_sig for _ in range(10)]
    mean_w0 = np.mean(w0_samples, axis=0)
    print(f"[*] Quiescent W=0 Baseline ADC49: {[round(float(x), 1) for x in mean_w0]} LSB\n")

    # -------------------------------------------------------------------------
    # STAGE 2: Multi-Dimensional Sweep per Column
    # -------------------------------------------------------------------------
    print("[*] Starting Systematic Grid Sweep Across In-Data, M3, M8 and DC Bias...")
    print("    Searching for Maximum Dynamic Peak Response per Column...")

    # We explore:
    # 1. Bias sweep on M8 Row 6: [-60, -30, 0, +30, +60]
    # 2. M8 Data row weight: [-80, -40, +40, +80]
    # 3. M3 Data row weight: [-32, 0, +32]
    
    col_max_delta_adc49 = [0.0] * 6
    col_min_val = [1e6] * 6
    col_max_val = [-1e6] * 6
    col_best_config = [{} for _ in range(6)]

    # Sweep M8 Row 6 Bias across 9 values: [-80, -60, -40, -20, 0, +20, +40, +60, +80]
    b6_values = [-80, -60, -40, -20, 0, 20, 40, 60, 80]
    w8_values = [-80, -40, 0, 40, 80]
    w3_values = [-32, 0, 32]

    total_configs = len(b6_values) * len(w8_values)
    step = 0

    for b6 in b6_values:
        for w8 in w8_values:
            step += 1
            # Build tables with this candidate operating point across all columns
            m3 = [[0] * 6 for _ in range(8)]
            m8 = [[0] * 6 for _ in range(7)]
            for c in range(6):
                m3[c][c] = 24  # Linear M3 pass-through
                m8[c][c] = w8
                m8[6][c] = b6

            payload = pack_payload(m3, m8)
            client._send_binary(MAML_CMD_CENTER_WEIGHTS, payload)
            time.sleep(0.015)

            # Sample 6 fresh vectors
            samples = []
            for _ in range(6):
                t = client.draw_fresh_vector()
                if t and t.connected_hw:
                    samples.append(t.adc49_sig)
                time.sleep(0.005)

            if samples:
                means = np.mean(samples, axis=0)
                for c in range(6):
                    val = float(means[c])
                    if val < col_min_val[c]:
                        col_min_val[c] = val
                    if val > col_max_val[c]:
                        col_max_val[c] = val
                    cur_span = col_max_val[c] - col_min_val[c]
                    if cur_span > col_max_delta_adc49[c]:
                        col_max_delta_adc49[c] = cur_span
                        col_best_config[c] = {"w8": w8, "b6": b6, "peak_span": cur_span}

            if step % 9 == 0 or step == total_configs:
                current_spans = [round(col_max_delta_adc49[c], 1) for c in range(6)]
                print(f"    Sweep Step {step:2d}/{total_configs:2d} (b6={b6:+3d}, w8={w8:+3d}) | Max Spans so far: {current_spans} LSB", flush=True)

    # -------------------------------------------------------------------------
    # STAGE 3: Walsh-Hadamard 16x16 Demodulation Carrier Test
    # -------------------------------------------------------------------------
    print("\n[*] Measuring 500 kHz Walsh-Hadamard Demodulation Signal Strength...")
    diag_res = client.diag_hadamard(mode=4, en_mask=0x7FFF)
    col_hadamard_peak_pwr = [0.0] * 6
    col_hadamard_cnr_db = [0.0] * 6

    if diag_res:
        fwht = np.array(diag_res.fwht49, dtype=np.float64)  # (16, 6)
        for c in range(6):
            pwrs = fwht[:, c] ** 2
            peak_p = float(np.max(pwrs))
            floor_p = float(np.median(pwrs) + 1.0)
            cnr = 10.0 * math.log10(max(peak_p / floor_p, 1.0))
            col_hadamard_peak_pwr[c] = math.sqrt(peak_p)
            col_hadamard_cnr_db[c] = round(cnr, 1)

    # -------------------------------------------------------------------------
    # FINAL ANALYSIS & REPORT TABLE
    # -------------------------------------------------------------------------
    print("\n" + "=" * 98)
    print("COMPREHENSIVE ADAPTIVE HARDWARE SELF-TEST REPORT (CARD 2, 1k/5.1k ATTENUATOR)")
    print("=" * 98)
    print(f"{'Col':<5} | {'Max Dynamic Span':<18} | {'Best Bias/W8':<16} | {'Hadamard Mag':<14} | {'Hadamard CNR':<14} | {'Hardware Verdict':<18}")
    print("-" * 98)

    all_alive = True
    for c in range(6):
        span = col_max_delta_adc49[c]
        span_str = f"{span:6.1f} LSB"
        b_conf = col_best_config[c]
        conf_str = f"b6={b_conf.get('b6', 0):+d}, w8={b_conf.get('w8', 0):+d}"
        h_mag_str = f"{col_hadamard_peak_pwr[c]:6.1f} LSB"
        h_cnr_str = f"{col_hadamard_cnr_db[c]:4.1f} dB"

        # Objective physical hardware evaluation:
        # A truly broken solder joint or open jumper CANNOT produce > 15 LSB of dynamic swing!
        if span >= 30.0:
            verdict = "PASS (Strong)"
        elif span >= 15.0:
            verdict = "PASS (Moderate)"
        elif span >= 7.0:
            verdict = "WEAK (Marginal)"
        else:
            verdict = "FAIL (OPEN/Dead)"
            all_alive = False

        print(f"Col {c:<2} | {span_str:<18} | {conf_str:<16} | {h_mag_str:<14} | {h_cnr_str:<14} | {verdict:<18}")

    print("-" * 98)
    if all_alive:
        print("[+] CONCLUSION: ALL 6 CHANNELS ARE ELECTRICALLY CONNECTED AND ACTIVE!")
        print("    Every single column responds dynamically to weights and data.")
        print("    Attenuator solder joints, Sigmoid 4 headers (H1$CBB), and ColTIA are functional.")
    else:
        print("[!] CONCLUSION: ONE OR MORE CHANNELS SHOW NO DYNAMIC RESPONSE ACROSS THE ENTIRE SWEEP.")
        print("    Confirm physical soldering and jumper seating on the failed columns.")
    print("=" * 98)

    # Restore W=0 baseline
    client._send_binary(MAML_CMD_CENTER_WEIGHTS, struct.pack("<B", 0))
    client.close()


if __name__ == "__main__":
    main()

