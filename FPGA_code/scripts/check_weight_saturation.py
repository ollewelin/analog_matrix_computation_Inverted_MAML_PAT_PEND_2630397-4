#!/usr/bin/env python3
"""
check_weight_saturation.py
===========================
Automated diagnostic tool to audit weight clamping / rail-to-rail saturation (M3 and M8).
Reports:
  - Exact epoch when first weight hits the clamp boundary (|W| >= clamp - margin).
  - List of clamped cells (Matrix, Row, Col, Value).
  - Saturation timeline & percentage of clamped matrix capacity.
"""

import sys
import json
import argparse
from pathlib import Path
import numpy as np


def analyze_saturation(json_path: str, clamp: int = 120, margin: int = 2):
    path = Path(json_path)
    if not path.exists():
        print(f"[!] Error: File {path} not found.")
        sys.exit(1)

    print(f"[*] Analyzing weight saturation for: {path.name}")
    print(f"[*] Clamp threshold: |W| >= {clamp - margin} LSB (nominal clamp = ±{clamp} LSB)\n")

    with open(path, "r") as f:
        data = json.load(f)

    records = data.get("records") or data.get("epochs") or []
    if not records:
        print("[!] No epoch records found.")
        return

    first_hit = None
    timeline = []
    
    threshold = clamp - margin

    for r in records:
        ep = r.get("epoch", 0)
        w_m8 = r.get("w_m8", [])
        w_m3 = r.get("w_m3", [])

        clamped_m8 = []
        for ri, row in enumerate(w_m8):
            for ci, val in enumerate(row):
                if abs(val) >= threshold:
                    clamped_m8.append((ri, ci, val))

        clamped_m3 = []
        for ri, row in enumerate(w_m3):
            for ci, val in enumerate(row):
                if abs(val) >= threshold:
                    clamped_m3.append((ri, ci, val))

        tot_clamped = len(clamped_m8) + len(clamped_m3)
        if tot_clamped > 0:
            if first_hit is None:
                first_hit = (ep, len(clamped_m8), len(clamped_m3), clamped_m8, clamped_m3)
            timeline.append((ep, len(clamped_m8), len(clamped_m3)))

    print("=" * 70)
    print("SATURATION AUDIT REPORT")
    print("=" * 70)

    if first_hit is None:
        print("✅ CLEAN: Inga vikter slog i taket/botten under hela körningen!")
        return

    ep_0, n8_0, n3_0, m8_list, m3_list = first_hit
    print(f"🚨 FÖRSTA KLAMPNING: Epok #{ep_0}")
    print(f"   M8 klampar: {n8_0} st celler")
    for ri, ci, v in m8_list:
        print(f"     -> M8[{ri},{ci}] = {v:+d} LSB ({'TAK (+)' if v > 0 else 'BOTTEN (-)'})")
    if n3_0 > 0:
        print(f"   M3 klampar: {n3_0} st celler")
        for ri, ci, v in m3_list:
            print(f"     -> M3[{ri},{ci}] = {v:+d} LSB ({'TAK (+)' if v > 0 else 'BOTTEN (-)'})")

    last_ep, last_n8, last_n3 = timeline[-1]
    tot_m8_cells = 7 * 6
    tot_m3_cells = 8 * 6
    pct_m8 = (last_n8 / tot_m8_cells) * 100.0
    print("-" * 70)
    print(f"STATUS VID SLUTET (Epok #{last_ep}):")
    print(f"   M8 klampar: {last_n8} / {tot_m8_cells} celler ({pct_m8:.1f} % av matrisen har bottnat!)")
    if last_n3 > 0:
        pct_m3 = (last_n3 / tot_m3_cells) * 100.0
        print(f"   M3 klampar: {last_n3} / {tot_m3_cells} celler ({pct_m3:.1f} % av matrisen)")

    print("\nFörlopp (urval av epoker):")
    step = max(1, len(timeline) // 10)
    for t in timeline[::step]:
        print(f"   Epok #{t[0]:5d} | M8 klampar: {t[1]:2d} st | M3 klampar: {t[2]:2d} st")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check weight clamp saturation")
    parser.add_argument("json_file", help="Path to experiment JSON")
    parser.add_argument("--clamp", type=int, default=120, help="Clamp limit (default 120)")
    parser.add_argument("--margin", type=int, default=2, help="Margin from clamp (default 2)")
    args = parser.parse_args()

    analyze_saturation(args.json_file, clamp=args.clamp, margin=args.margin)

