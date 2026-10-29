#!/usr/bin/env python3
"""
m3_sigmoid_step2_column_scurve.py
=================================
STEG 2 — Kolumnvis Kollektiv Karakterisering av Sigmoid S-kurvan (Ref 4)
och Optimering av Baslinje-startvikter (W3_baseline).

Protokoll:
  - För varje kolumn c in [0..5]:
    * Alla 8 rader på kolumn c styrs gemensamt till samma vikt W: W3[0..7][c] = W
    * W sveps från 0 upp till +127 (positiv böj) och från 0 ner till -127 (negativ böj).
    * Kolumnen exciteras med 4 representativa insignaler: X in {-127, -64, +64, +127}.
  - ADC_45[c] mäts vid nominal t = 5.0 ms settled delay.
  - Identifierar den "sköna mjuka S-kurvan":
    * Hög dynamik (gain |dY/dW| > 0) särskilt för medel-data X = ±64.
    * Mjukt, icke-stokastiskt beteende (minimal jerk / lågt brus).
    * Hitta optimal knäpunkt (W_knee) för varje kolumn.
  - Sparar den rekommenderade baslinjen W3_baseline[0..5].
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from gui.udp_client import MamlUdpClient, MAT_M3  # noqa: E402

OUT_DIR = REPO_ROOT / "FPGA_code" / "logs" / "m3_sigmoid_characterization"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 25 viktpunkter för mjuk kurvupplösning kring böjarna
WEIGHT_STEPS = [-127, -112, -96, -80, -64, -52, -40, -28, -16, -8, 0,
                 8, 16, 28, 40, 52, 64, 80, 96, 112, 127]
SNAP_US = 5000


def probe_col_collective(client, col, x_amp, w, reps=4):
    """
    Probes column `col` collectively with all rows set to `w`.
    Uses row=255 (0xFF) convention in firmware probe API.
    """
    neg_samples, zero_samples, pos_samples = [], [], []
    for _ in range(reps):
        try:
            res = client.probe_cell_xw(MAT_M3, 255, col, x_amp=x_amp, w_fixed=w,
                                       sweep_input=True, hold=False, snap_dly_us=SNAP_US)
            if res is not None:
                neg_samples.append(res.adc45_neg[col])
                zero_samples.append(res.adc45_zero[col])
                pos_samples.append(res.adc45_pos[col])
        except Exception:
            pass
        time.sleep(0.015)
    return {
        "neg_mean": float(np.mean(neg_samples)) if neg_samples else 0.0,
        "neg_std":  float(np.std(neg_samples)) if neg_samples else 0.0,
        "zero_mean": float(np.mean(zero_samples)) if zero_samples else 0.0,
        "zero_std":  float(np.std(zero_samples)) if zero_samples else 0.0,
        "pos_mean": float(np.mean(pos_samples)) if pos_samples else 0.0,
        "pos_std":  float(np.std(pos_samples)) if pos_samples else 0.0,
    }


def analyze_scurve(weights, y_curve, y_std):
    """
    Analyzes an S-curve to identify:
      - Dynamic range: max(y) - min(y)
      - Max derivative (linear sensitivity region)
      - Curvature peaks (second derivative = knees)
      - Jerk (stochastic noise + fit residual)
    """
    w = np.array(weights, dtype=float)
    y = np.array(y_curve, dtype=float)
    s = np.array(y_std, dtype=float)
    
    dyn = float(np.max(y) - np.min(y))
    noise = float(np.mean(s))
    
    # 1st and 2nd derivatives
    dy_dw = np.gradient(y, w)
    d2y_dw2 = np.gradient(dy_dw, w)
    
    # Negative side knee (W < 0)
    neg_mask = (w < -8)
    if np.any(neg_mask):
        w_neg = w[neg_mask]
        curv_neg = np.abs(d2y_dw2[neg_mask])
        k_neg = int(np.argmax(curv_neg))
        knee_neg_w = float(w_neg[k_neg])
        knee_neg_gain = float(np.abs(dy_dw[neg_mask][k_neg]))
    else:
        knee_neg_w, knee_neg_gain = -40.0, 0.0
        
    # Positive side knee (W > 0)
    pos_mask = (w > 8)
    if np.any(pos_mask):
        w_pos = w[pos_mask]
        curv_pos = np.abs(d2y_dw2[pos_mask])
        k_pos = int(np.argmax(curv_pos))
        knee_pos_w = float(w_pos[k_pos])
        knee_pos_gain = float(np.abs(dy_dw[pos_mask][k_pos]))
    else:
        knee_pos_w, knee_pos_gain = 40.0, 0.0

    return {
        "dynamic_lsb": round(dyn, 2),
        "noise_std_lsb": round(noise, 2),
        "knee_neg_w": knee_neg_w,
        "knee_neg_gain": round(knee_neg_gain, 3),
        "knee_pos_w": knee_pos_w,
        "knee_pos_gain": round(knee_pos_gain, 3),
    }


def main():
    ap = argparse.ArgumentParser(description="M3 Sigmoid Step 2: Column Collective S-Curve Sweep")
    ap.add_argument("--host", default="192.168.1.50")
    ap.add_argument("--port", type=int, default=5000)
    ap.add_argument("--reps", type=int, default=4)
    ap.add_argument("--cols", default="0-5")
    ap.add_argument("--out", default=str(OUT_DIR / "step2_column_scurve.json"))
    args = ap.parse_args()

    client = MamlUdpClient(host=args.host, port=args.port, timeout=0.8)
    print(f"[*] Target: {client.query_version().strip()}")

    cols = [int(c) for c in (args.cols.split("-") if "-" not in args.cols else range(int(args.cols.split("-")[0]), int(args.cols.split("-")[1]) + 1))]
    
    ds = {
        "title": "M3 Sigmoid Step 2 — Column Collective S-Curve Sweep & Baseline Optimizer",
        "description": "Macroscopic Sigmoid S-Curve under collective 8-row column excitation",
        "weights": WEIGHT_STEPS,
        "snap_us": SNAP_US,
        "reps": args.reps,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "columns": {},
        "recommended_baseline_w3": {},
    }

    t0 = time.time()
    for col in cols:
        print(f"\n[+] Probing Column {col} Collective S-Curve...", flush=True)
        col_res = {
            "x127_pos": [], "x127_neg": [],
            "x64_pos":  [], "x64_neg":  [],
            "x0":       [],
        }
        for w in WEIGHT_STEPS:
            # 1. Full Scale X = ±127
            r127 = probe_col_collective(client, col, 127, w, reps=args.reps)
            # 2. Medium Scale X = ±64
            r64  = probe_col_collective(client, col, 64,  w, reps=args.reps)
            
            col_res["x127_pos"].append(r127["pos_mean"])
            col_res["x127_neg"].append(r127["neg_mean"])
            col_res["x64_pos"].append(r64["pos_mean"])
            col_res["x64_neg"].append(r64["neg_mean"])
            col_res["x0"].append((r127["zero_mean"] + r64["zero_mean"]) / 2.0)
            print(f"  Col {col} W={w:+4d} | X=+64: {r64['pos_mean']:+6.1f} LSB | X=-64: {r64['neg_mean']:+6.1f} LSB", flush=True)

        # Analyze curves for X=±64 (medium) and X=±127 (full)
        metrics_x64_pos = analyze_scurve(WEIGHT_STEPS, col_res["x64_pos"], [0]*len(WEIGHT_STEPS))
        metrics_x64_neg = analyze_scurve(WEIGHT_STEPS, col_res["x64_neg"], [0]*len(WEIGHT_STEPS))
        
        # Decide optimal polarity and knee
        # Priority: Good sensitivity for medium signals (X=±64)
        pos_score = metrics_x64_pos["knee_pos_gain"] * metrics_x64_pos["dynamic_lsb"]
        neg_score = metrics_x64_neg["knee_neg_gain"] * metrics_x64_neg["dynamic_lsb"]
        
        best_side = "pos" if pos_score >= neg_score else "neg"
        opt_knee_w = metrics_x64_pos["knee_pos_w"] if best_side == "pos" else metrics_x64_neg["knee_neg_w"]
        
        ds["columns"][f"C{col}"] = {
            "curves": col_res,
            "metrics_x64_pos": metrics_x64_pos,
            "metrics_x64_neg": metrics_x64_neg,
            "best_polarity": best_side,
            "optimal_knee_w": opt_knee_w,
        }
        ds["recommended_baseline_w3"][f"C{col}"] = int(round(opt_knee_w))
        print(f"[>] Column {col} Optimal Knee: W = {int(round(opt_knee_w)):+d} (Side: {best_side.upper()})")

    ds["duration_s"] = round(time.time() - t0, 1)
    with open(args.out, "w") as f:
        json.dump(ds, f, indent=2)
    print(f"\n[+] Steg 2 klart på {ds['duration_s']/60:.1f} min -> {args.out}")
    print("[+] Recommended Baseline W3 Vector:", ds["recommended_baseline_w3"])


if __name__ == "__main__":
    main()

