#!/usr/bin/env python3
"""
plot_m3_sigmoid_step2.py
========================
Generates diagnostic plots for Steg 2:
  1. 6-column macroscopic S-curve grid with X = ±127 and X = ±64
  2. Annotated optimal knee marker W_base[c] on each column
"""

import json
import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
IN_FILE = REPO_ROOT / "FPGA_code" / "logs" / "m3_sigmoid_characterization" / "step2_column_scurve.json"
FIG_DIR = REPO_ROOT / "FPGA_code" / "docs" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)
OUT_FIG = FIG_DIR / "fig_m3_sigmoid_step2_column_scurves.png"


def main():
    if not IN_FILE.exists():
        print(f"Error: {IN_FILE} does not exist.")
        sys.exit(1)
    with open(IN_FILE, "r") as f:
        data = json.load(f)

    weights = np.array(data["weights"])
    cols = data["columns"]
    rec_w = data.get("recommended_baseline_w3", {})

    fig, axes = plt.subplots(2, 3, figsize=(18, 11), sharex=True)
    fig.suptitle("Matrix 3 Macroscopic Sigmoid S-Curves (Ref 4) & Optimal Baseline Knees\n"
                 "Collective 8-Row Column Drive @ Nominal t = 5.0 ms | Pure Physical Silicon",
                 fontsize=15, fontweight="bold", y=0.98)

    for c in range(6):
        ax = axes[c // 3, c % 3]
        key = f"C{c}"
        if key not in cols:
            ax.text(0.5, 0.5, "No Data", ha="center", va="center", transform=ax.transAxes)
            continue
        cd = cols[key]
        curves = cd["curves"]
        opt_w = rec_w.get(key, 0)
        pol = cd["best_polarity"].upper()

        ax.plot(weights, curves["x127_neg"], label="X = -127 (Blue)", color="#1f77b4", lw=2.0)
        ax.plot(weights, curves["x64_neg"],  label="X = -64 (Red)",   color="#d62728", lw=1.8)
        ax.plot(weights, curves["x0"],        label="X = 0 (Green)",   color="#2ca02c", lw=1.2, ls="--")
        ax.plot(weights, curves["x64_pos"],  label="X = +64 (Orange)",color="#ff7f0e", lw=1.8)
        ax.plot(weights, curves["x127_pos"], label="X = +127 (Gold)",  color="#bcbd22", lw=2.0)

        # Highlight optimal knee
        ax.axvline(opt_w, color="purple", ls="-.", lw=1.8, label=f"Optimal Knee W={opt_w:+d}")
        ax.axvline(0, color="gray", ls=":", lw=0.8, alpha=0.6)
        ax.axhline(0, color="gray", ls=":", lw=0.8, alpha=0.6)

        ax.set_title(f"Column {c} (Recommended Knee: W = {opt_w:+d} LSB | {pol})", fontsize=11, fontweight="bold")
        ax.set_ylabel("ADC_45 Δ (LSB)", fontsize=10)
        if c >= 3:
            ax.set_xlabel("Collective Weight W3[0..7]", fontsize=10)
        ax.grid(True, ls=":", alpha=0.5)
        if c == 0:
            ax.legend(fontsize=8.5, loc="upper left")

    plt.tight_layout(rect=[0.02, 0.02, 0.98, 0.95])
    plt.savefig(OUT_FIG, dpi=200)
    plt.close()
    print(f"[+] Saved S-curves figure -> {OUT_FIG}")


if __name__ == "__main__":
    main()

