#!/usr/bin/env python3
"""
m3_full_temporal_clock_vs_compute_sweep.py
==========================================
Comprehensive silicon characterization of Temporal Clock Cells (M3 Rows 6 & 7),
Regular Compute Cells (M3 Rows 0..5 and M33 Rows 0..5), and Bias Cells (M8 Row 6)
across:
  1. The FULL capacitor refresh window: 1.0 ms to 9.0 ms (1000 .. 9000 µs)
  2. High-resolution zoom inside the operational window: 4.5 ms to 5.5 ms (100 µs steps)

Also evaluates multi-weight curves (W in [-64, -32, -16, 0, +16, +32, +64]) to show
how to place the clock cells in the S-curve center vs. S-bend (inflection knee).
"""

import os
import sys
import time
import json
import argparse
from pathlib import Path
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from gui.udp_client import MamlUdpClient, MAT_M3, MAT_M8, MAT_M33, MAML_CMD_CENTER_WEIGHTS

# 21 time points: full 1.0..9.0 ms sweep + dense 100 us steps in [4.5..5.5 ms]
DELAYS_US = [
    1000, 1500, 2000, 2500, 3000, 3500, 4000,
    4500, 4600, 4700, 4800, 4900, 5000, 5100, 5200, 5300, 5400, 5500,
    6000, 6500, 7000, 7500, 8000, 8500, 9000
]

WEIGHTS_SWEEP = [-64, -32, -16, 0, 16, 32, 64]
COLS = [0, 1, 2, 3, 4, 5]


def probe_row_across_time(client, matrix_id, row, w_fixed, x_amp, delays_us, reps=2, use_adc49=False):
    """Probes all 6 columns for a specific row and weight across all delays."""
    out_pos = {}
    out_neg = {}
    out_zero = {}
    for dly in delays_us:
        c_pos = []
        c_neg = []
        c_zero = []
        for c in COLS:
            vp, vn, vz = [], [], []
            for _ in range(reps):
                res = client.probe_cell_xw(
                    matrix_id=matrix_id,
                    row=row,
                    col=c,
                    x_amp=x_amp,
                    w_fixed=w_fixed,
                    sweep_input=True,
                    hold=False,
                    snap_dly_us=dly,
                )
                if res:
                    if use_adc49:
                        vp.append(res.adc49_pos[c])
                        vn.append(res.adc49_neg[c])
                        vz.append(res.adc49_zero[c])
                    else:
                        vp.append(res.adc45_pos[c])
                        vn.append(res.adc45_neg[c])
                        vz.append(res.adc45_zero[c])
                time.sleep(0.002)
            c_pos.append(round(float(np.mean(vp)), 1) if vp else 0.0)
            c_neg.append(round(float(np.mean(vn)), 1) if vn else 0.0)
            c_zero.append(round(float(np.mean(vz)), 1) if vz else 0.0)
        out_pos[str(dly)] = c_pos
        out_neg[str(dly)] = c_neg
        out_zero[str(dly)] = c_zero
    return {"pos": out_pos, "neg": out_neg, "zero": out_zero}


def main():
    parser = argparse.ArgumentParser(description="Full Temporal Clock vs Compute Cell Characterization")
    parser.add_argument("--host", default="192.168.1.50")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--reps", type=int, default=2)
    args = parser.parse_args()

    client = MamlUdpClient(args.host, args.port)
    print("=" * 88)
    print("INVERTED MAML: FULL TEMPORAL WINDOW [1.0 - 9.0 ms] & ZOOM [4.5 - 5.5 ms] CHARACTERIZATION")
    print(f"Target: {args.host}:{args.port} | Time Points: {len(DELAYS_US)} | Reps: {args.reps}")
    print("=" * 88)

    client._send_binary(MAML_CMD_CENTER_WEIGHTS, b"\x00")
    time.sleep(0.05)

    dataset = {
        "delays_us": DELAYS_US,
        "weights_sweep": WEIGHTS_SWEEP,
        "m3_clock_row6_weights": {},
        "m3_clock_row7_weights": {},
        "m3_compute_rows_w32": {},
        "m33_compute_row0_w32": {},
        "m8_bias_row6_weights": {},
    }

    t0 = time.time()

    # 1. Sweep M3 Row 6 (Clock B1) across multiple weights [-64..+64] at key delays + full time at W=+32, -32, +16, -16
    print("\n[*] 1/5: Sweeping M3 Clock Row 6 (TRIM_B1) across weights [-64, -32, -16, 0, +16, +32, +64]...")
    for w in [-64, -32, -16, 0, 16, 32, 64]:
        print(f"    -> M3 Row 6 @ W = {w:+3d} LSB...")
        dataset["m3_clock_row6_weights"][str(w)] = probe_row_across_time(
            client, MAT_M3, row=6, w_fixed=w, x_amp=64, delays_us=DELAYS_US, reps=args.reps, use_adc49=False
        )

    # 2. Sweep M3 Row 7 (Clock REF) across weights [-64, -32, 0, +32, +64]
    print("\n[*] 2/5: Sweeping M3 Clock Row 7 (TRIM_REF) across weights [-64, -32, 0, +32, +64]...")
    for w in [-64, -32, 0, 32, 64]:
        print(f"    -> M3 Row 7 @ W = {w:+3d} LSB...")
        dataset["m3_clock_row7_weights"][str(w)] = probe_row_across_time(
            client, MAT_M3, row=7, w_fixed=w, x_amp=64, delays_us=DELAYS_US, reps=args.reps, use_adc49=False
        )

    # 3. Sweep Regular Compute Cells in M3 (Rows 0, 1, 2) at W = +32 to compare decay vs Clock Cells!
    print("\n[*] 3/5: Sweeping M3 Regular Compute Rows (Rows 0, 1, 2) @ W = +32 LSB for direct comparison...")
    for r in [0, 1, 2]:
        print(f"    -> M3 Compute Row {r} @ W = +32 LSB...")
        dataset["m3_compute_rows_w32"][f"row_{r}"] = probe_row_across_time(
            client, MAT_M3, row=r, w_fixed=32, x_amp=64, delays_us=DELAYS_US, reps=args.reps, use_adc49=False
        )

    # 4. Sweep M33 Primary Compute Row 0 at W = +32 (measured on ADC_49)
    print("\n[*] 4/5: Sweeping M33 Primary Compute Row 0 @ W = +32 LSB (ADC_49)...")
    dataset["m33_compute_row0_w32"] = probe_row_across_time(
        client, MAT_M33, row=0, w_fixed=32, x_amp=64, delays_us=DELAYS_US, reps=args.reps, use_adc49=True
    )

    # 5. Sweep M8 Bias Row 6 across weights [-64, -32, 0, +32, +64] (measured on ADC_49)
    print("\n[*] 5/5: Sweeping M8 Bias Row 6 across weights [-64, -32, 0, +32, +64] (ADC_49)...")
    for w in [-64, -32, 0, 32, 64]:
        print(f"    -> M8 Bias Row 6 @ W = {w:+3d} LSB...")
        dataset["m8_bias_row6_weights"][str(w)] = probe_row_across_time(
            client, MAT_M8, row=6, w_fixed=w, x_amp=64, delays_us=DELAYS_US, reps=args.reps, use_adc49=True
        )

    elapsed = time.time() - t0
    out_dir = REPO_ROOT / "FPGA_code" / "logs" / "m3_clock_characterization"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "full_temporal_clock_vs_compute_dataset.json"
    with open(out_path, "w") as f:
        json.dump(dataset, f, indent=2)

    print("=" * 88)
    print(f"[COMPLETE] Sweep finished in {elapsed:.1f} s. Saved to: {out_path}")
    print("=" * 88)


if __name__ == "__main__":
    main()

