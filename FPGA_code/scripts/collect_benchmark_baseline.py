#!/usr/bin/env python3
"""
Benchmark Collection Script for Inverted MAML Hardware Board.
Hardware Target: 192.168.1.50:5000 (UDP binary protocol 0x4D414D4C)
"""

from __future__ import annotations
import datetime
import json
import math
import os
import sys
import time
from pathlib import Path
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from gui.udp_client import MamlUdpClient, MAT_M3, MAT_M8, MAT_M33


def collect_benchmark() -> dict:
    client = MamlUdpClient(host="192.168.1.50", port=5000, timeout=1.0)
    version_str = client.query_version()
    print(f"Connected to T120 SoC: {version_str}")

    # 1. Telemetry query (MAML_CMD_GET_TELEMETRY, 0x10)
    telem = client.poll_telemetry()
    if not telem.connected_hw:
        raise RuntimeError("Failed to communicate with physical board! Check network or board state.")

    telemetry_dict = {
        "connected_hw": telem.connected_hw,
        "version": version_str,
        "run_mode": telem.mode,
        "jumper_mode": telem.jumper_mode,
        "heater_armed": telem.heater_armed,
        "heater_wdog_ok": telem.heater_wdog_ok,
        "heater_duty": telem.heater_duty,
        "led_switches": telem.led_switches,
        "hadamard_khz": telem.hadamard_khz,
        "settle_cycles": telem.settle_cycles,
        "refresh_cnt": telem.refresh_cnt,
        "enob_bits": round(telem.enob_bits, 3),
        "enob_comp_bits": round(telem.enob_comp_bits, 3),
        "enob_uncomp_bits": round(telem.enob_uncomp_bits, 3),
        "mse_q14": telem.mse_q14,
        "t20_h_ack_ok": telem.t20_h_ack_ok,
        "t20_h_ack_miss": telem.t20_h_ack_miss,
        "t20_h_lat_last": telem.t20_h_lat_last,
        "status_text": telem.status_text,
    }
    print(f"Telemetry verified: Mode={telem.mode}, Refresh={telem.refresh_cnt}, LEDs={telem.led_switches}")

    # 2. Complete 48-cell scan of Matrix 3 (8x6 -> ADC_45)
    print("\nScanning Matrix 3 (8x6 = 48 cells) across W in [-96, 0, +96] and DAC_2 in [32, 128, 224]...")
    matrix3_cells = []
    m3_spans = []
    t_start = time.time()
    for r in range(8):
        for c in range(6):
            cell_entry = {
                "row": r,
                "col": c,
                "w_neg96": {},
                "w_0": {},
                "w_pos96": {},
                "weight_span_at_mid": 0,
            }
            # Sweep W = -96, 0, +96 with x_amp = 96 (DAC_2 = 32, 128, 224)
            p_neg = client.probe_cell_xw(MAT_M3, r, c, x_amp=96, w_fixed=-96, sweep_input=True)
            p_zero = client.probe_cell_xw(MAT_M3, r, c, x_amp=96, w_fixed=0, sweep_input=True)
            p_pos = client.probe_cell_xw(MAT_M3, r, c, x_amp=96, w_fixed=96, sweep_input=True)

            if p_neg and p_zero and p_pos:
                cell_entry["w_neg96"] = {
                    "dac2_32": p_neg.adc45_neg[c],
                    "dac2_128": p_neg.adc45_zero[c],
                    "dac2_224": p_neg.adc45_pos[c],
                    "delta_x": p_neg.adc45_pos[c] - p_neg.adc45_neg[c],
                }
                cell_entry["w_0"] = {
                    "dac2_32": p_zero.adc45_neg[c],
                    "dac2_128": p_zero.adc45_zero[c],
                    "dac2_224": p_zero.adc45_pos[c],
                    "delta_x": p_zero.adc45_pos[c] - p_zero.adc45_neg[c],
                }
                cell_entry["w_pos96"] = {
                    "dac2_32": p_pos.adc45_neg[c],
                    "dac2_128": p_pos.adc45_zero[c],
                    "dac2_224": p_pos.adc45_pos[c],
                    "delta_x": p_pos.adc45_pos[c] - p_pos.adc45_neg[c],
                }
                span = p_pos.adc45_zero[c] - p_neg.adc45_zero[c]
                cell_entry["weight_span_at_mid"] = span
                m3_spans.append(span)

            matrix3_cells.append(cell_entry)
    print(f"Matrix 3 scan complete ({len(matrix3_cells)} cells in {time.time() - t_start:.2f}s). Mean weight span: {np.mean(m3_spans):.1f} LSB")

    # 3. Complete 36-cell scan of Matrix 33 (6x6 -> ADC_49) with +48 pedestal bias
    print("\nScanning Matrix 33 (6x6 = 36 cells) across W in [-96, 0, +96] and DAC_2 in [32, 128, 224]...")
    matrix33_cells = []
    m33_spans = []
    t_start = time.time()
    for r in range(6):
        for c in range(6):
            cell_entry = {
                "row": r,
                "col": c,
                "w_neg96": {},
                "w_0": {},
                "w_pos96": {},
                "weight_span_at_mid": 0,
            }
            # Sweep W = -96, 0, +96 with x_amp = 96 (DAC_2 = 32, 128, 224)
            p_neg = client.probe_cell_xw(MAT_M33, r, c, x_amp=96, w_fixed=-96, sweep_input=True)
            p_zero = client.probe_cell_xw(MAT_M33, r, c, x_amp=96, w_fixed=0, sweep_input=True)
            p_pos = client.probe_cell_xw(MAT_M33, r, c, x_amp=96, w_fixed=96, sweep_input=True)

            if p_neg and p_zero and p_pos:
                cell_entry["w_neg96"] = {
                    "dac2_32": p_neg.adc49_neg[c],
                    "dac2_128": p_neg.adc49_zero[c],
                    "dac2_224": p_neg.adc49_pos[c],
                    "delta_x": p_neg.adc49_pos[c] - p_neg.adc49_neg[c],
                }
                cell_entry["w_0"] = {
                    "dac2_32": p_zero.adc49_neg[c],
                    "dac2_128": p_zero.adc49_zero[c],
                    "dac2_224": p_zero.adc49_pos[c],
                    "delta_x": p_zero.adc49_pos[c] - p_zero.adc49_neg[c],
                }
                cell_entry["w_pos96"] = {
                    "dac2_32": p_pos.adc49_neg[c],
                    "dac2_128": p_pos.adc49_zero[c],
                    "dac2_224": p_pos.adc49_pos[c],
                    "delta_x": p_pos.adc49_pos[c] - p_pos.adc49_neg[c],
                }
                span = p_pos.adc49_zero[c] - p_neg.adc49_zero[c]
                cell_entry["weight_span_at_mid"] = span
                m33_spans.append(span)

            matrix33_cells.append(cell_entry)
    print(f"Matrix 33 scan complete ({len(matrix33_cells)} cells in {time.time() - t_start:.2f}s). Mean weight span: {np.mean(m33_spans):.1f} LSB")

    # 4. 16-step Hadamard FWHT-16 diagnostic sweep for Mode 0, Mode 1, Mode 2 (en_mask = 0x00FF)
    print("\nExecuting Hadamard FWHT-16 sweeps (en_mask=0x00FF) for Mode 0, Mode 1, Mode 2...")
    h0 = client.diag_hadamard(mode=0, en_mask=0x00FF)
    time.sleep(0.05)
    h1 = client.diag_hadamard(mode=1, en_mask=0x00FF)
    time.sleep(0.05)
    h2 = client.diag_hadamard(mode=2, en_mask=0x00FF)

    # Compute isolation ratio
    # Active Matrix 3 basis functions: m = 1..7 (or 1..8)
    # Disabled Matrix 8 basis functions: m = 9..15 (or 8..15)
    fwht45_m0 = np.array(h0.fwht45)
    active_m0 = np.abs(fwht45_m0[1:8, :])
    quiet_m0 = np.abs(fwht45_m0[9:16, :])
    mean_act_m0 = float(np.mean(active_m0))
    mean_quiet_m0 = float(np.mean(quiet_m0))
    isolation_ratio_m0 = mean_act_m0 / max(1e-3, mean_quiet_m0)
    isolation_db_m0 = 20.0 * math.log10(max(1.0, isolation_ratio_m0))

    fwht45_m1 = np.array(h1.fwht45)
    active_m1 = np.abs(fwht45_m1[1:8, :])
    quiet_m1 = np.abs(fwht45_m1[9:16, :])
    mean_act_m1 = float(np.mean(active_m1))
    mean_quiet_m1 = float(np.mean(quiet_m1))
    isolation_ratio_m1 = mean_act_m1 / max(1e-3, mean_quiet_m1)
    isolation_db_m1 = 20.0 * math.log10(max(1.0, isolation_ratio_m1))

    fwht45_m2 = np.array(h2.fwht45)
    active_m2 = np.abs(fwht45_m2[1:8, :])
    quiet_m2 = np.abs(fwht45_m2[9:16, :])
    mean_act_m2 = float(np.mean(active_m2))
    mean_quiet_m2 = float(np.mean(quiet_m2))
    isolation_ratio_m2 = mean_act_m2 / max(1e-3, mean_quiet_m2)
    isolation_db_m2 = 20.0 * math.log10(max(1.0, isolation_ratio_m2))

    hadamard_results = {
        "en_mask": "0x00FF",
        "mode_0_identity": {
            "ack_ok": h0.ack_ok,
            "ack_miss": h0.ack_miss,
            "lat_min": h0.lat_min,
            "lat_max": h0.lat_max,
            "t20_sync_err": h0.t20_sync_err,
            "mean_active_fwht": round(mean_act_m0, 2),
            "mean_quiet_fwht": round(mean_quiet_m0, 2),
            "isolation_ratio": round(isolation_ratio_m0, 2),
            "isolation_db": round(isolation_db_m0, 2),
            "perm": h0.perm,
            "fwht45": h0.fwht45,
            "fwht49": h0.fwht49,
            "adc45_hiz": h0.adc45_hiz,
            "adc49_hiz": h0.adc49_hiz,
        },
        "mode_1_perm_pi_inv": {
            "ack_ok": h1.ack_ok,
            "ack_miss": h1.ack_miss,
            "lat_min": h1.lat_min,
            "lat_max": h1.lat_max,
            "t20_sync_err": h1.t20_sync_err,
            "mean_active_fwht": round(mean_act_m1, 2),
            "mean_quiet_fwht": round(mean_quiet_m1, 2),
            "isolation_ratio": round(isolation_ratio_m1, 2),
            "isolation_db": round(isolation_db_m1, 2),
            "perm": h1.perm,
            "fwht45": h1.fwht45,
            "fwht49": h1.fwht49,
            "adc45_hiz": h1.adc45_hiz,
            "adc49_hiz": h1.adc49_hiz,
        },
        "mode_2_perm_no_pi_inv": {
            "ack_ok": h2.ack_ok,
            "ack_miss": h2.ack_miss,
            "lat_min": h2.lat_min,
            "lat_max": h2.lat_max,
            "t20_sync_err": h2.t20_sync_err,
            "mean_active_fwht": round(mean_act_m2, 2),
            "mean_quiet_fwht": round(mean_quiet_m2, 2),
            "isolation_ratio": round(isolation_ratio_m2, 2),
            "isolation_db": round(isolation_db_m2, 2),
            "perm": h2.perm,
            "fwht45": h2.fwht45,
            "fwht49": h2.fwht49,
            "adc45_hiz": h2.adc45_hiz,
            "adc49_hiz": h2.adc49_hiz,
        },
    }

    # Summary metrics
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    benchmark_payload = {
        "metadata": {
            "timestamp": now_iso,
            "target": "192.168.1.50:5000",
            "protocol": "MAML (0x4D414D4C)",
            "schema_version": "1.0",
        },
        "telemetry": telemetry_dict,
        "matrix_3_scan": {
            "description": "Matrix 3 (8x6 Layer 1 -> ADC_45) full cell scan",
            "total_cells": len(matrix3_cells),
            "mean_weight_span_lsb": round(float(np.mean(m3_spans)), 2),
            "min_weight_span_lsb": int(np.min(m3_spans)),
            "max_weight_span_lsb": int(np.max(m3_spans)),
            "cells": matrix3_cells,
        },
        "matrix_33_scan": {
            "description": "Matrix 33 (6x6 Main Payload -> ADC_49) full cell scan with +48 pedestal bias",
            "total_cells": len(matrix33_cells),
            "mean_weight_span_lsb": round(float(np.mean(m33_spans)), 2),
            "min_weight_span_lsb": int(np.min(m33_spans)),
            "max_weight_span_lsb": int(np.max(m33_spans)),
            "cells": matrix33_cells,
        },
        "hadamard_diagnostics": hadamard_results,
    }

    return benchmark_payload


def main() -> int:
    out_dir = REPO_ROOT / "data" / "benchmarks"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "benchmark_baseline_latest.json"

    print("=== Executing Inverted MAML Benchmark Collection Turn ===")
    data = collect_benchmark()

    # Save compact JSON (<100KB budget)
    json_bytes = json.dumps(data, separators=(",", ":")).encode("utf-8")
    size_kb = len(json_bytes) / 1024.0

    with open(out_file, "wb") as f:
        f.write(json_bytes)

    print(f"\nSaved benchmark dataset to: {out_file}")
    print(f"File size: {size_kb:.2f} KB (Budget: < 100 KB)")

    # Print summary metrics
    m3_cells = data["matrix_3_scan"]["total_cells"]
    m3_mean_span = data["matrix_3_scan"]["mean_weight_span_lsb"]
    m33_cells = data["matrix_33_scan"]["total_cells"]
    m33_mean_span = data["matrix_33_scan"]["mean_weight_span_lsb"]
    h_iso_db = data["hadamard_diagnostics"]["mode_0_identity"]["isolation_db"]

    print("\n================== SUMMARY ==================")
    print(f"Total Cells Scanned   : {m3_cells + m33_cells} ({m3_cells} M3 + {m33_cells} M33)")
    print(f"Matrix 3 Mean Span    : {m3_mean_span:+.1f} LSB")
    print(f"Matrix 33 Mean Span   : {m33_mean_span:+.1f} LSB")
    print(f"Hadamard Isolation    : {h_iso_db:.1f} dB (Active vs Quiet Basis)")
    print(f"Disk Budget Usage     : {size_kb:.2f} KB / 100 KB")
    print("=============================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
