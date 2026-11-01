#!/usr/bin/env python3
"""
m3_characterize_clock_cells.py
==============================
Empirical hardware characterization of Matrix 3 Temporal Clock & Reference Cells
(Row 6 = TRIM_B1 / Row 7 = TRIM_REF) and Matrix 8 Bias Row (Row 6) across
the temporal snapshot window [1.0 .. 9.0 ms], focusing on [4.5 .. 5.5 ms].

Physical Silicon Target: 192.168.1.50:5000 (Trion T120 Master SoC).
Output: Differential ADC_45 (Layer 1 Sigmoid 4) and ADC_49 (Layer 2 Sigmoid 10).
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

from gui.udp_client import MamlUdpClient, MAT_M3, MAT_M8, MAML_CMD_CENTER_WEIGHTS

DELAYS_US = [1000, 2000, 3000, 4000, 4500, 4800, 5000, 5200, 5500, 6000, 7000, 8000, 9000]
COLS = [0, 1, 2, 3, 4, 5]


def main():
    parser = argparse.ArgumentParser(description="M3 Temporal Clock & M8 Bias Characterization")
    parser.add_argument("--host", default="192.168.1.50")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--reps", type=int, default=2)
    args = parser.parse_args()

    client = MamlUdpClient(args.host, args.port)
    print("=" * 84)
    print("INVERTED MAML: TEMPORAL CLOCK & BIAS CELL HARDWARE CHARACTERIZATION")
    print(f"Target: {args.host}:{args.port} | Snapshot Delays: {DELAYS_US} µs")
    print("=" * 84)

    # Center weights initially
    client._send_binary(MAML_CMD_CENTER_WEIGHTS, b"\x00")
    time.sleep(0.05)

    results = {
        "delays_us": DELAYS_US,
        "m3_row6_clock_b1": {},
        "m3_row7_clock_ref": {},
        "m8_row6_bias": {},
    }

    # 1. Sweep Matrix 3 Row 6 (Clock B1) across Delays for Column 0..5
    print("\n[*] 1. Sweeping Matrix 3 Row 6 (TRIM_B1, Clock Cell) across Delays @ W=+32, X=64...")
    for dly in DELAYS_US:
        col_readings = []
        for c in COLS:
            vals = []
            for _ in range(args.reps):
                res = client.probe_cell_xw(
                    matrix_id=MAT_M3,
                    row=6,
                    col=c,
                    x_amp=64,
                    w_fixed=32,
                    sweep_input=True,
                    hold=False,
                    snap_dly_us=dly,
                )
                if res:
                    vals.append(res.adc45_pos[c])
                time.sleep(0.003)
            col_readings.append(float(np.mean(vals)) if vals else 0.0)
        results["m3_row6_clock_b1"][str(dly)] = [round(v, 1) for v in col_readings]
        print(f"  Delay {dly:4d} µs | M3 Row 6 (ADC_45 Cols 0..5): {results['m3_row6_clock_b1'][str(dly)]}")

    # 2. Sweep Matrix 3 Row 7 (Clock REF) across Delays for Column 0..5
    print("\n[*] 2. Sweeping Matrix 3 Row 7 (TRIM_REF, Clock Cell) across Delays @ W=+32, X=64...")
    for dly in DELAYS_US:
        col_readings = []
        for c in COLS:
            vals = []
            for _ in range(args.reps):
                res = client.probe_cell_xw(
                    matrix_id=MAT_M3,
                    row=7,
                    col=c,
                    x_amp=64,
                    w_fixed=32,
                    sweep_input=True,
                    hold=False,
                    snap_dly_us=dly,
                )
                if res:
                    vals.append(res.adc45_pos[c])
                time.sleep(0.003)
            col_readings.append(float(np.mean(vals)) if vals else 0.0)
        results["m3_row7_clock_ref"][str(dly)] = [round(v, 1) for v in col_readings]
        print(f"  Delay {dly:4d} µs | M3 Row 7 (ADC_45 Cols 0..5): {results['m3_row7_clock_ref'][str(dly)]}")

    # 3. Sweep Matrix 8 Row 6 (Bias Row) across Delays for Column 0..5 (Output on ADC_49)
    print("\n[*] 3. Sweeping Matrix 8 Row 6 (Layer 2 Bias Row) across Delays @ W=+32, X=64...")
    for dly in DELAYS_US:
        col_readings = []
        for c in COLS:
            vals = []
            for _ in range(args.reps):
                res = client.probe_cell_xw(
                    matrix_id=MAT_M8,
                    row=6,
                    col=c,
                    x_amp=64,
                    w_fixed=32,
                    sweep_input=True,
                    hold=False,
                    snap_dly_us=dly,
                )
                if res:
                    vals.append(res.adc49_pos[c])
                time.sleep(0.003)
            col_readings.append(float(np.mean(vals)) if vals else 0.0)
        results["m8_row6_bias"][str(dly)] = [round(v, 1) for v in col_readings]
        print(f"  Delay {dly:4d} µs | M8 Row 6 (ADC_49 Cols 0..5): {results['m8_row6_bias'][str(dly)]}")

    # 4. Summary: Dynamic Swing over [4.5 .. 5.5 ms]
    print("\n" + "=" * 84)
    print("ANALYSIS: DYNAMIC SWING OVER [4.5 .. 5.5 ms] (S-CURVE CENTERING ASSESSMENT)")
    print("=" * 84)
    for name, key, adc_name in [
        ("Matrix 3 Row 6 (Clock B1)", "m3_row6_clock_b1", "ADC_45"),
        ("Matrix 3 Row 7 (Clock REF)", "m3_row7_clock_ref", "ADC_45"),
        ("Matrix 8 Row 6 (Bias Row)", "m8_row6_bias", "ADC_49"),
    ]:
        v45 = np.array(results[key]["4500"])
        v50 = np.array(results[key]["5000"])
        v55 = np.array(results[key]["5500"])
        swing = (v45 - v55).round(1).tolist()
        mean_at_5ms = v50.tolist()
        print(f"\n{name} ({adc_name}):")
        print(f"  Level at 4.5 ms (4500 µs) : {v45.tolist()}")
        print(f"  Level at 5.0 ms (5000 µs) : {mean_at_5ms}")
        print(f"  Level at 5.5 ms (5500 µs) : {v55.tolist()}")
        print(f"  Dynamic Swing (4.5 - 5.5) : {swing} LSB")
        print(f"  Center Offset at 5.0 ms   : {np.mean(v50):.1f} LSB (Distance from ideal 0 LSB)")

    # Save to JSON
    out_dir = REPO_ROOT / "FPGA_code" / "logs" / "m3_clock_characterization"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "m3_and_m8_clock_bias_characterization.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n[+] Saved full characterization dataset to: {out_path}")


if __name__ == "__main__":
    main()
