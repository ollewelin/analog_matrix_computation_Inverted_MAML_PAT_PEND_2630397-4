#!/usr/bin/env python3
"""
w3_staircase_pattern.py
Helper module for loading and packing the W(3) staircase reference and bias pattern.
Pattern: evenly distributed +/-40 LSB across 6 columns (step = 16 LSB):
  [-40, -24, -8, +8, +24, +40]
"""

import json
import struct
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent / "w3_staircase_pattern.json"

def get_staircase_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def build_center_weights_payload(baseline_mode=1):
    """
    Builds the exact 91-byte binary payload for MAML_CMD_CENTER_WEIGHTS:
      byte 0     : g_baseline_mode (1 = apply smart table, 0 = zero)
      bytes 1..48: 48 signed int8 bytes for W_M3[8][6]
      bytes 49..90: 42 signed int8 bytes for W_M8[7][6]
    """
    cfg = get_staircase_config()
    w_m3 = cfg["w_m3_lsb"]
    w_m8 = cfg["w_m8_lsb"]

    flat_m3 = [w_m3[r][c] for r in range(8) for c in range(6)]
    flat_m8 = [w_m8[r][c] for r in range(7) for c in range(6)]

    return struct.pack("<B48b42b", baseline_mode, *flat_m3, *flat_m8)

if __name__ == "__main__":
    cfg = get_staircase_config()
    print("Loaded W(3) Staircase Configuration:")
    print(f"Name: {cfg['name']}")
    print(f"Staircase Vector: {cfg['staircase_vector']}")
    print("Matrix 3 (8x6):")
    for r, row in enumerate(cfg["w_m3_lsb"]):
        print(f"  Row {r}: {row}")
    payload = build_center_weights_payload(1)
    print(f"Binary payload length: {len(payload)} bytes (Matches expected 91 bytes)")

