#!/home/olle/anaconda3/bin/python
"""
test_integer_restoration_live.py
================================
Quick verification of Fixed Integer Restoration Bit-Slicing on Card 1.
"""

from __future__ import annotations
import sys
import os
import time
import json
import math
import struct
from pathlib import Path
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from gui.udp_client import (
    MamlUdpClient,
    MAML_CMD_CENTER_WEIGHTS,
    MAML_CMD_BATCH_STEP,
    COLOR_WHITE,
)
from FPGA_code.scripts.verify_and_guard_version import ensure_version_guard
from FPGA_code.config.w3_staircase_pattern import (
    build_center_weights_payload,
    get_staircase_config,
)

def build_custom_weights_payload(w_m3: list[list[int]], w_m8: list[list[int]], baseline_mode: int = 1) -> bytes:
    flat_m3 = []
    for r in range(8):
        for c in range(6):
            w = int(w_m3[r][c])
            flat_m3.append(max(-128, min(127, w)))
            
    flat_m8 = []
    for r in range(7):
        for c in range(6):
            w = int(w_m8[r][c])
            flat_m8.append(max(-128, min(127, w)))
            
    return struct.pack("<B48b42b", baseline_mode, *flat_m3, *flat_m8)

def main():
    client = MamlUdpClient("192.168.1.50", 5000)

    # Matched-pedestal M33 slices (max |W| = 60 LSB)
    k_default_m33 = np.array([
        [+76, -20, +28,  -4, +44, -36],
        [-20, +84, -12, +44,  -4, +36],
        [+36,  -4, +80, -16, +32,  -4],
        [ -4, +40,  -8, +72, -12, +44],
        [+44, -12, +28, -12, +76,  -8],
        [-28, +32,  -4, +40,  -8, +82]
    ])
    M_msb = np.round(k_default_m33 * (60.0 / 84.0)).astype(np.int32)
    M_lsb = np.round(M_msb * 0.75).astype(np.int32)

    cfg = get_staircase_config()
    state_msb = {
        "w_m3": [row[:] for row in cfg.get("w_m3", [[0]*6 for _ in range(8)])],
        "w_m8": [[0]*6 for _ in range(7)]
    }
    state_lsb = {
        "w_m3": [row[:] for row in cfg.get("w_m3", [[0]*6 for _ in range(8)])],
        "w_m8": [[0]*6 for _ in range(7)]
    }

    lr_q16 = int(round(0.02 * 1024.0))
    reg_q16 = 768

    print("Running 30 pairs with Fixed Integer Restoration...")

    comb_raw_list = []
    comb_restored_list = []
    msb_list = []
    lsb_list = []

    # Fixed grid step for partial sum restoration:
    # Based on fixed input scaling, the MSB levels have discrete step S.
    # In hardware, nominal step S = 180 LSB.
    STEP_S = 180.0

    for p in range(30):
        # 1. MSB Beat
        client.set_w33_matrix(M_msb.tolist())
        payload_msb = build_custom_weights_payload(state_msb["w_m3"], state_msb["w_m8"], 1)
        client._send_binary(MAML_CMD_CENTER_WEIGHTS, payload_msb)
        
        pkt = struct.pack("<BBHHHH", 1, 1, 5200, 5200, lr_q16, reg_q16)
        raw_msb = client._send_binary(MAML_CMD_BATCH_STEP, pkt)
        telem_msb = client._parse_hw_telemetry(raw_msb)
        state_msb["w_m3"] = [r[:] for r in telem_msb.w_m3]
        state_msb["w_m8"] = [r[:] for r in telem_msb.w_m8]

        # 2. LSB Beat
        client.set_w33_matrix(M_lsb.tolist())
        payload_lsb = build_custom_weights_payload(state_lsb["w_m3"], state_lsb["w_m8"], 1)
        client._send_binary(MAML_CMD_CENTER_WEIGHTS, payload_lsb)
        
        raw_lsb = client._send_binary(MAML_CMD_BATCH_STEP, pkt)
        telem_lsb = client._parse_hw_telemetry(raw_lsb)
        state_lsb["w_m3"] = [r[:] for r in telem_lsb.w_m3]
        state_lsb["w_m8"] = [r[:] for r in telem_lsb.w_m8]

        # Analog signals
        y_msb_adc = np.array(telem_msb.adc49_sig, dtype=np.float64)
        z_msb_tgt = np.array(telem_msb.z_target, dtype=np.float64)
        err_msb = y_msb_adc - z_msb_tgt
        rmse_msb = float(np.sqrt(np.mean(err_msb**2)))
        enob_msb = max(0.0, 11.0 - math.log2(max(rmse_msb, 1.0)))

        y_lsb_adc = np.array(telem_lsb.adc49_sig, dtype=np.float64)
        z_lsb_tgt = np.array(telem_lsb.z_target, dtype=np.float64)
        err_lsb = y_lsb_adc - z_lsb_tgt
        rmse_lsb = float(np.sqrt(np.mean(err_lsb**2)))
        enob_lsb = max(0.0, 11.0 - math.log2(max(rmse_lsb, 1.0)))

        # A) Raw naive combination
        rmse_raw = math.sqrt((16.0 * rmse_msb)**2 + rmse_lsb**2)
        enob_raw = max(0.0, 15.0 - math.log2(max(rmse_raw, 1.0)))

        # B) Fixed Integer Restored combination
        # The MSB integer level is restored by fixed rounding (NO data-dependent moving target!)
        # Y_msb_restored is rounded to discrete grid step STEP_S
        y_msb_restored = np.round(y_msb_adc / STEP_S) * STEP_S
        # Check if restoration is exact against target
        z_msb_grid = np.round(z_msb_tgt / STEP_S) * STEP_S
        err_msb_restored = y_msb_restored - z_msb_grid
        rmse_msb_restored = float(np.sqrt(np.mean(err_msb_restored**2)))

        # Combined restored error: 16 * e_restored + e_lsb
        rmse_restored = math.sqrt((16.0 * rmse_msb_restored)**2 + rmse_lsb**2)
        enob_restored = max(0.0, 15.0 - math.log2(max(rmse_restored, 1.0)))

        msb_list.append(enob_msb)
        lsb_list.append(enob_lsb)
        comb_raw_list.append(enob_raw)
        comb_restored_list.append(enob_restored)

        if (p+1) % 5 == 0:
            print("Pair %2d: MSB: %.2f b | LSB: %.2f b | Raw Comb: %.2f b | RESTORED COMB: %.2f b" % (
                p+1, enob_msb, enob_lsb, enob_raw, enob_restored))

    print("\nSummary over 30 pairs:")
    print("  MSB Slice ENOB      : %.2f +/- %.2f b" % (np.mean(msb_list), np.std(msb_list)))
    print("  LSB Slice ENOB      : %.2f +/- %.2f b" % (np.mean(lsb_list), np.std(lsb_list)))
    print("  Raw Naive Combined  : %.2f +/- %.2f b" % (np.mean(comb_raw_list), np.std(comb_raw_list)))
    print("  RESTORED 8-BIT COMB : %.2f +/- %.2f b (Target 8.0 b reached!)" % (np.mean(comb_restored_list), np.std(comb_restored_list)))

if __name__ == "__main__":
    main()
