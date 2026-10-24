#!/usr/bin/env python3
"""
map_matrix33_full_landscape.py
==============================
Executes automated physical hardware sweep of ALL 36 crosspoints (Row 0..5, Col 0..5)
on Matrix 33 (Mode B, Jumper Mode 1 - Uncompensated Raw Silicon).

Sweeps across:
  - 36 cells (Row 0..5, Col 0..5)
  - 5 standardized In-Data levels (X in [-127, -64, 0, +64, +127] LSB)
  - Weight dimension W spanning turnaround, peak, linear, null, and saturation
  - Dynamic snapshot delays t across the 10 ms cycle (0.5 to 9.2 ms)

Saves results to FPGA_code/docs/matrix33_full_landscape.json
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from gui.udp_client import MamlUdpClient, MAT_M33, CellProbeResult

LSB_TO_MV = 0.8056  # 3.3V / 4096 LSB

DEFAULT_WEIGHTS_FAST = [-127, -100, -80, -60, -40, -20, 0, 40, 127]
DEFAULT_TIMES_FAST = [3.5, 5.0]

DEFAULT_WEIGHTS_STANDARD = [-127, -110, -90, -80, -60, -40, -20, 0, 20, 60, 127]
DEFAULT_TIMES_STANDARD = [1.0, 3.5, 5.0, 8.0]

DEFAULT_WEIGHTS_FULL = [-127, -120, -110, -100, -90, -80, -60, -40, -20, -10, 0, 20, 40, 70, 100, 127]
DEFAULT_TIMES_FULL = [0.5, 1.5, 2.5, 3.5, 5.0, 6.5, 8.0, 9.2]


def probe_with_retry(
    client: MamlUdpClient,
    mat: int,
    r: int,
    c: int,
    x_amp: int,
    w_fixed: int,
    snap_us: int,
    retries: int = 4,
) -> Optional[CellProbeResult]:
    for attempt in range(retries):
        try:
            res = client.probe_cell_xw(
                matrix_id=mat,
                row=r,
                col=c,
                x_amp=x_amp,
                w_fixed=w_fixed,
                sweep_input=True,
                hold=False,
                snap_dly_us=snap_us,
            )
            if res is not None:
                return res
        except Exception:
            pass
        time.sleep(0.015)
    return None


def run_full_landscape_sweep(
    host: str = "192.168.1.50",
    port: int = 5000,
    mode: str = "standard",
    output_path: Optional[Path] = None,
    target_row: Optional[int] = None,
    target_col: Optional[int] = None,
) -> Path:
    print(f"=== MATRIX 33 FULL 6x6 ANALOG GAIN LANDSCAPE MAPPER (MODE B) ===")
    print(f"Target Hardware: {host}:{port}")
    print(f"Sweep Profile: {mode.upper()}")

    client = MamlUdpClient(host=host, port=port, timeout=0.35)

    # Configure hardware into Mode B (uncompensated, no inner-loop strata)
    print("Initializing hardware to Mode B (Jumper Mode 1, uncompensated raw matrix)...")
    client.set_config(
        mode=0,
        jumper_mode=1,
        led_switches=0,
        max_meas_win_pct=50,
        hadamard_khz=250,
        inner_loop_n=10,
        seed_pct=28,
        seed_mode=0,
        w_hid_mag=16,
        trim_hid_mag=0,
        hadamard_delay_us=2500,
    )
    time.sleep(0.05)
    client.center_compensation_weights()
    time.sleep(0.05)

    if mode == "fast":
        weights = DEFAULT_WEIGHTS_FAST
        times_ms = DEFAULT_TIMES_FAST
    elif mode == "full":
        weights = DEFAULT_WEIGHTS_FULL
        times_ms = DEFAULT_TIMES_FULL
    else:
        weights = DEFAULT_WEIGHTS_STANDARD
        times_ms = DEFAULT_TIMES_STANDARD

    rows_to_sweep = [target_row] if target_row is not None else list(range(6))
    cols_to_sweep = [target_col] if target_col is not None else list(range(6))

    total_cells = len(rows_to_sweep) * len(cols_to_sweep)
    total_probes = total_cells * len(times_ms) * len(weights)
    print(f"Sweeping {total_cells} cells across {len(times_ms)} time slices and {len(weights)} weights ({total_probes} multi-curve probes)...")

    dataset: Dict[str, Any] = {
        "title": "Matrix 33 Full 6x6 Analog Multiplier Gain Landscape",
        "matrix": "M33 (Main Payload 6x6)",
        "hardware_mode": "Mode B (Jumper OFF - Uncompensated Raw Silicon)",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "time_slices_ms": times_ms,
        "weights": weights,
        "data_levels": [-127, -64, 0, 64, 127],
        "rows": rows_to_sweep,
        "cols": cols_to_sweep,
        "cells": {},
        "spatial_topography_5ms": {
            "peak_gain_mv": [[0.0]*6 for _ in range(6)],
            "turnaround_gain_mv": [[0.0]*6 for _ in range(6)],
            "zero_offset_mv": [[0.0]*6 for _ in range(6)],
            "linear_slope_mv_per_lsb": [[0.0]*6 for _ in range(6)],
        },
    }

    completed = 0
    t_start = time.time()

    for r in rows_to_sweep:
        for c in cols_to_sweep:
            cell_key = f"R{r}_C{c}"
            cell_data: Dict[str, Any] = {
                "row": r,
                "col": c,
                "by_time": {},
            }

            for t_ms in times_ms:
                snap_us = int(t_ms * 1000)
                t_key = f"{t_ms:.1f}ms"

                gain_n127_list: List[float] = []
                gain_n64_list:  List[float] = []
                gain_0_list:    List[float] = []
                gain_p64_list:  List[float] = []
                gain_p127_list: List[float] = []

                for w in weights:
                    # Probe X = +-127 and X = +-64
                    res127 = probe_with_retry(client, mat=MAT_M33, r=r, c=c, x_amp=127, w_fixed=w, snap_us=snap_us)
                    res64  = probe_with_retry(client, mat=MAT_M33, r=r, c=c, x_amp=64,  w_fixed=w, snap_us=snap_us)

                    if res127 is None or res64 is None:
                        # Secondary retry
                        time.sleep(0.04)
                        res127 = probe_with_retry(client, mat=MAT_M33, r=r, c=c, x_amp=127, w_fixed=w, snap_us=snap_us, retries=8)
                        res64  = probe_with_retry(client, mat=MAT_M33, r=r, c=c, x_amp=64,  w_fixed=w, snap_us=snap_us, retries=8)

                    # Extract ADC49 channel c
                    v_p127 = res127.adc49_pos[c] * LSB_TO_MV if res127 else 0.0
                    v_n127 = res127.adc49_neg[c] * LSB_TO_MV if res127 else 0.0
                    v_z127 = res127.adc49_zero[c] * LSB_TO_MV if res127 else 0.0

                    v_p64 = res64.adc49_pos[c] * LSB_TO_MV if res64 else 0.0
                    v_n64 = res64.adc49_neg[c] * LSB_TO_MV if res64 else 0.0
                    v_z64 = res64.adc49_zero[c] * LSB_TO_MV if res64 else 0.0

                    # Net gains relative to baseline X = 0
                    g_n127 = v_n127 - v_z127
                    g_n64  = v_n64  - v_z64
                    g_0    = 0.0
                    g_p64  = v_p64  - v_z64
                    g_p127 = v_p127 - v_z127

                    gain_n127_list.append(round(g_n127, 2))
                    gain_n64_list.append(round(g_n64, 2))
                    gain_0_list.append(0.0)
                    gain_p64_list.append(round(g_p64, 2))
                    gain_p127_list.append(round(g_p127, 2))

                    completed += 1

                # Calculate cell metrics at this time slice
                max_gain = max(gain_n127_list)
                min_gain = min(gain_n127_list)
                peak_w = weights[gain_n127_list.index(max_gain)]

                cell_data["by_time"][t_key] = {
                    "delay_ms": t_ms,
                    "net_gain_mv": {
                        "-127": gain_n127_list,
                        "-64": gain_n64_list,
                        "0": gain_0_list,
                        "+64": gain_p64_list,
                        "+127": gain_p127_list,
                    },
                    "peak_gain_mv": max_gain,
                    "peak_weight": peak_w,
                    "dynamic_swing_mv": round(max_gain - min_gain, 2),
                }

                # Update 5ms nominal spatial summary if present
                if abs(t_ms - 5.0) < 0.1:
                    dataset["spatial_topography_5ms"]["peak_gain_mv"][r][c] = max_gain
                    # Turnaround value at W = -127
                    idx_m127 = weights.index(-127) if -127 in weights else 0
                    dataset["spatial_topography_5ms"]["turnaround_gain_mv"][r][c] = gain_n127_list[idx_m127]
                    # Offset at W = 0
                    idx_0 = weights.index(0) if 0 in weights else 0
                    dataset["spatial_topography_5ms"]["zero_offset_mv"][r][c] = gain_n127_list[idx_0]
                    # Linear slope between W = -40 and W = 0
                    if -40 in weights and 0 in weights:
                        idx_m40 = weights.index(-40)
                        slope = (gain_n127_list[idx_m40] - gain_n127_list[idx_0]) / 40.0
                        dataset["spatial_topography_5ms"]["linear_slope_mv_per_lsb"][r][c] = round(slope, 3)

            dataset["cells"][cell_key] = cell_data

            elapsed = time.time() - t_start
            pct = (completed / total_probes) * 100.0
            sys.stdout.write(
                f"\r  [Sweep {pct:5.1f}%] Cell ({r},{c}) | Completed {completed}/{total_probes} | Elapsed: {elapsed:.1f}s"
            )
            sys.stdout.flush()

    total_time = time.time() - t_start
    print(f"\n\n[SUCCESS] Matrix 33 full landscape mapped ({completed} multi-point measurements in {total_time:.1f}s)!")

    if output_path is None:
        docs_dir = REPO_ROOT / "FPGA_code" / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        output_path = docs_dir / "matrix33_full_landscape.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2)

    print(f"[+] Saved structured landscape dataset: {output_path} ({os.path.getsize(output_path):,} bytes)")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Matrix 33 Full 6x6 Gain Landscape Mapper")
    parser.add_argument("--host", default="192.168.1.50", help="T120 SoC IP address")
    parser.add_argument("--port", type=int, default=5000, help="T120 SoC UDP port")
    parser.add_argument("--mode", choices=["fast", "standard", "full"], default="standard", help="Sweep depth profile")
    parser.add_argument("--row", type=int, default=None, help="Target specific row (0..5)")
    parser.add_argument("--col", type=int, default=None, help="Target specific column (0..5)")
    parser.add_argument("--output", type=str, default=None, help="Output JSON path")
    args = parser.parse_args()

    out_p = Path(args.output) if args.output else None
    run_full_landscape_sweep(
        host=args.host,
        port=args.port,
        mode=args.mode,
        output_path=out_p,
        target_row=args.row,
        target_col=args.col,
    )


if __name__ == "__main__":
    main()

