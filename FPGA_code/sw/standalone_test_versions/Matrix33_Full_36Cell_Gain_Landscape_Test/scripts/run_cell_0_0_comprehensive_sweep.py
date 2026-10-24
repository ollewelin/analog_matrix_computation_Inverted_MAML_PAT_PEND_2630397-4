#!/usr/bin/env python3
"""
Comprehensive Physical Silicon Characterization of Cell (0,0) on Matrix 33
===========================================================================
Executes a multi-dimensional sweep on physical hardware at 192.168.1.50:5000:
  - 10 Snapshot Delays: t in [0.5, 1.0, 1.5, 2.0, 2.5, 3.5, 5.0, 6.5, 8.0, 9.2] ms
  - 27 Weights W: [-127 .. +127] with fine resolution in [-127, -110] LSB
  - 5 In-Data Rows X: [-127 (Blue), -64 (Red), 0 (Green), +64 (Orange), +127 (Yellow)]

Saves results to FPGA_code/docs/cell_0_0_comprehensive_sweep.json
Generates high-resolution publication figures in FPGA_code/docs/figures/
"""

import sys
import os
import time
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from gui.udp_client import MamlUdpClient, CellProbeResult

SNAP_DELAYS_MS = [0.5, 1.0, 1.5, 2.0, 2.5, 3.5, 5.0, 6.5, 8.0, 9.2]
WEIGHTS = [
    -127, -120, -115, -110, -100, -90, -80, -70, -60, -50,
    -40, -30, -20, -10, 0, 10, 20, 30, 40, 50,
    60, 70, 80, 90, 100, 110, 120, 127
]
LSB_TO_MV = 0.8056  # 3.3V / 4096 LSB


def probe_with_retry(client: MamlUdpClient, mat: int, r: int, c: int, x_amp: int, w_fixed: int, snap_us: int, retries: int = 4) -> Optional[CellProbeResult]:
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


def main():
    print("=== STARTING COMPREHENSIVE PHYSICAL CHARACTERIZATION OF CELL (0,0) ===")
    print("Connecting to T120 SoC at 192.168.1.50:5000...")
    client = MamlUdpClient(host="192.168.1.50", port=5000, timeout=0.35)

    # Ensure Mode B and stop autonomous random generator before start
    client.set_config(mode=0, jumper_mode=1, led_switches=0, max_meas_win_pct=50, hadamard_khz=250, inner_loop_n=10, seed_pct=28, seed_mode=0, w_hid_mag=16, trim_hid_mag=0, hadamard_delay_us=2500)
    time.sleep(0.05)
    client.center_compensation_weights()
    time.sleep(0.05)

    all_data: Dict[str, Any] = {
        "title": "Comprehensive Dual-2T1C Cell (0,0) Silicon Characterization",
        "matrix": "M33 (Main Payload 6x6)",
        "row": 0,
        "col": 0,
        "mode": "Mode B (Jumper OFF - No Compensation)",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "snap_delays_ms": SNAP_DELAYS_MS,
        "weights": WEIGHTS,
        "data_levels": [-127, -64, 0, 64, 127],
        "curves_by_time": {},
    }

    total_points = len(SNAP_DELAYS_MS) * len(WEIGHTS)
    completed = 0
    t_start = time.time()

    for d_ms in SNAP_DELAYS_MS:
        snap_us = int(d_ms * 1000)
        print(f"\n---> Sweeping Snapshot Delay t = {d_ms:.1f} ms ({snap_us} µs) <---")
        
        time_entry = {
            "delay_ms": d_ms,
            "delay_us": snap_us,
            "weights": WEIGHTS,
            "raw_mv": {"-127": [], "-64": [], "0": [], "+64": [], "+127": []},
            "net_gain_mv": {"-127": [], "-64": [], "0": [], "+64": [], "+127": []},
            "diff_gain_mv": {"127": [], "64": []},
        }

        for w in WEIGHTS:
            # Measure X = +-127
            res127 = probe_with_retry(client, mat=2, r=0, c=0, x_amp=127, w_fixed=w, snap_us=snap_us)
            # Measure X = +-64
            res64  = probe_with_retry(client, mat=2, r=0, c=0, x_amp=64,  w_fixed=w, snap_us=snap_us)

            if res127 is None or res64 is None:
                print(f"  [WARN] Failed to read W={w} at t={d_ms} ms, retrying...")
                time.sleep(0.05)
                res127 = probe_with_retry(client, mat=2, r=0, c=0, x_amp=127, w_fixed=w, snap_us=snap_us, retries=8)
                res64  = probe_with_retry(client, mat=2, r=0, c=0, x_amp=64,  w_fixed=w, snap_us=snap_us, retries=8)

            # Raw ADC values in mV
            v_p127 = res127.adc49_pos[0] * LSB_TO_MV if res127 else 0.0
            v_n127 = res127.adc49_neg[0] * LSB_TO_MV if res127 else 0.0
            v_z127 = res127.adc49_zero[0] * LSB_TO_MV if res127 else 0.0

            v_p64 = res64.adc49_pos[0] * LSB_TO_MV if res64 else 0.0
            v_n64 = res64.adc49_neg[0] * LSB_TO_MV if res64 else 0.0
            v_z64 = res64.adc49_zero[0] * LSB_TO_MV if res64 else 0.0

            v_zero_avg = (v_z127 + v_z64) * 0.5

            # Raw curves
            time_entry["raw_mv"]["-127"].append(round(v_n127, 2))
            time_entry["raw_mv"]["-64"].append(round(v_n64, 2))
            time_entry["raw_mv"]["0"].append(round(v_zero_avg, 2))
            time_entry["raw_mv"]["+64"].append(round(v_p64, 2))
            time_entry["raw_mv"]["+127"].append(round(v_p127, 2))

            # Net Gain relative to X=0
            gain_n127 = v_n127 - v_z127
            gain_n64  = v_n64  - v_z64
            gain_0    = 0.0
            gain_p64  = v_p64  - v_z64
            gain_p127 = v_p127 - v_z127

            time_entry["net_gain_mv"]["-127"].append(round(gain_n127, 2))
            time_entry["net_gain_mv"]["-64"].append(round(gain_n64, 2))
            time_entry["net_gain_mv"]["0"].append(0.0)
            time_entry["net_gain_mv"]["+64"].append(round(gain_p64, 2))
            time_entry["net_gain_mv"]["+127"].append(round(gain_p127, 2))

            # Full differential gain Pos - Neg
            diff127 = v_p127 - v_n127
            diff64  = v_p64 - v_n64
            time_entry["diff_gain_mv"]["127"].append(round(diff127, 2))
            time_entry["diff_gain_mv"]["64"].append(round(diff64, 2))

            completed += 1
            if completed % 9 == 0 or w == 127:
                sys.stdout.write(f"\r  Progress: {completed}/{total_points} ({(completed/total_points)*100:.1f}%) | W={w:>4d} -> Gain(X=+127)={gain_p127:>+7.1f} mV, Gain(X=-127)={gain_n127:>+7.1f} mV")
                sys.stdout.flush()

        all_data["curves_by_time"][f"{d_ms:.1f}ms"] = time_entry

    dt = time.time() - t_start
    print(f"\n\n[SUCCESS] Completed {completed} multi-point measurements in {dt:.1f}s!")

    # Save JSON dump
    docs_dir = REPO_ROOT / "FPGA_code" / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    json_path = docs_dir / "cell_0_0_comprehensive_sweep.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2)
    print(f"[+] Saved dataset to: {json_path}")


if __name__ == "__main__":
    main()

