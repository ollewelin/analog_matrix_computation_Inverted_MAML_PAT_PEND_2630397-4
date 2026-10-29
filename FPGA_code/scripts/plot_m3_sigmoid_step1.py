#!/usr/bin/env python3
"""
plot_m3_sigmoid_step1.py
========================
Generates high-resolution publication-quality diagnostic plots for
Steg 1 of Matrix 3 Sigmoid Analog Activation Mapping (Ref 4):
  1. 8x6 (48-cell) transfer function grid with 5 colored DAC_2 input curves
  2. Heatmaps of Dynamic Swing, Jerk, and Polarity Decision (+ vs -)
  3. Column summary comparing average quality and recommended bias per column
"""

import json
import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
IN_FILE = REPO_ROOT / "FPGA_code" / "logs" / "m3_sigmoid_characterization" / "step1_m3_cell_map_5ms.json"
FIG_DIR = REPO_ROOT / "FPGA_code" / "docs" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

# 5 standard input curve colors
COLORS = {
    "-127": "#1f77b4",  # Blue
    "-64":  "#d62728",  # Red
    "0":    "#2ca02c",  # Green
    "64":   "#ff7f0e",  # Orange
    "127":  "#bcbd22",  # Gold / Yellow
}

LABELS = {
    "-127": "X = -127 (Blue)",
    "-64":  "X = -64 (Red)",
    "0":    "X = 0 (Green)",
    "64":   "X = +64 (Orange)",
    "127":  "X = +127 (Gold)",
}


def plot_48cell_grid(data, out_path):
    weights = np.array(data["weights"])
    cells = data["cells"]
    
    fig, axes = plt.subplots(8, 6, figsize=(22, 26), sharex=True, sharey=True)
    fig.suptitle("Matrix 3 (8x6 = 48 Cells) Sigmoid Analog Activation Transfer Grid (Ref 4)\n"
                 "Physical Silicon @ t = 5.0 ms Settled Snapshot Delay | Differential ADC_45 Readout",
                 fontsize=18, fontweight="bold", y=0.995)

    legend_handles = []
    legend_labels = []

    for r in range(8):
        for c in range(6):
            ax = axes[r, c]
            key = f"R{r}_C{c}"
            if key not in cells:
                ax.text(0.5, 0.5, "No Data", ha="center", va="center", transform=ax.transAxes)
                continue
            
            cdata = cells[key]
            curves = cdata["curves"]
            rec_side = cdata.get("recommended_side", "pos")
            pol = cdata.get("polarity", {})
            
            for lv in ["-127", "-64", "0", "64", "127"]:
                if lv not in curves:
                    continue
                mean = np.array(curves[lv]["mean"])
                std = np.array(curves[lv]["std"])
                color = COLORS[lv]
                line, = ax.plot(weights, mean, color=color, lw=1.6)
                ax.fill_between(weights, mean - std, mean + std, color=color, alpha=0.15)
                if r == 0 and c == 0:
                    legend_handles.append(line)
                    legend_labels.append(LABELS[lv])

            ax.axvline(0, color="gray", ls="--", lw=0.8, alpha=0.7)
            ax.axhline(0, color="gray", ls=":", lw=0.6, alpha=0.5)
            
            # Badge showing recommended polarity
            badge_color = "#2ca02c" if rec_side == "pos" else "#1f77b4"
            badge_text = f"+ ({pol.get('pos', {}).get('score', 0):.0f})" if rec_side == "pos" else f"- ({pol.get('neg', {}).get('score', 0):.0f})"
            ax.text(0.04, 0.90, f"R{r}C{c}", transform=ax.transAxes, fontsize=10, fontweight="bold")
            ax.text(0.96, 0.90, badge_text, transform=ax.transAxes, fontsize=9,
                    ha="right", bbox=dict(boxstyle="round,pad=0.2", facecolor=badge_color, alpha=0.25))

            ax.grid(True, ls=":", alpha=0.4)
            if r == 7:
                ax.set_xlabel("Weight W3", fontsize=9)
            if c == 0:
                ax.set_ylabel(f"Row {r}\nADC45 Δ (LSB)", fontsize=9)
            if r == 0:
                ax.set_title(f"Column {c}", fontsize=11, fontweight="bold", pad=4)

    fig.legend(legend_handles, legend_labels, loc="upper right", bbox_to_anchor=(0.98, 0.992),
               ncol=5, fontsize=11, frameon=True, framealpha=0.9)
    plt.tight_layout(rect=[0.02, 0.02, 0.98, 0.98])
    plt.savefig(out_path, dpi=200)
    plt.close()
    print(f"[+] Saved 48-cell grid -> {out_path}")


def plot_heatmaps(data, out_path):
    cells = data["cells"]
    rows, cols = 8, 6
    
    dyn_neg = np.zeros((rows, cols))
    dyn_pos = np.zeros((rows, cols))
    jerk_neg = np.zeros((rows, cols))
    jerk_pos = np.zeros((rows, cols))
    score_neg = np.zeros((rows, cols))
    score_pos = np.zeros((rows, cols))
    rec_side = np.zeros((rows, cols)) # 1 for pos, -1 for neg

    for r in range(rows):
        for c in range(cols):
            key = f"R{r}_C{c}"
            if key in cells:
                pol = cells[key]["polarity"]
                dyn_neg[r, c] = pol["neg"]["dynamic_lsb"]
                dyn_pos[r, c] = pol["pos"]["dynamic_lsb"]
                jerk_neg[r, c] = pol["neg"]["jerk_lsb"]
                jerk_pos[r, c] = pol["pos"]["jerk_lsb"]
                score_neg[r, c] = pol["neg"]["score"]
                score_pos[r, c] = pol["pos"]["score"]
                rec_side[r, c] = 1 if cells[key]["recommended_side"] == "pos" else -1

    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle("Matrix 3 Sigmoid Analog Activation: Polarity & Smoothness Heatmaps (Ref 4)\n"
                 "Comparison of Negative (W ≤ 0) vs Positive (W ≥ 0) Polarity across 48 Cells",
                 fontsize=15, fontweight="bold")

    cmaps = ["viridis", "viridis", "magma_r", "magma_r", "Blues", "Oranges"]
    maps = [
        (dyn_neg, "Dynamic Swing ΔY (LSB) [W ≤ 0]", cmaps[0]),
        (dyn_pos, "Dynamic Swing ΔY (LSB) [W ≥ 0]", cmaps[1]),
        (jerk_neg, "Jerk / Noise J (LSB) [W ≤ 0] (Lower=Better)", cmaps[2]),
        (jerk_pos, "Jerk / Noise J (LSB) [W ≥ 0] (Lower=Better)", cmaps[3]),
        (score_neg, "Quality Score S [W ≤ 0]", cmaps[4]),
        (score_pos, "Quality Score S [W ≥ 0]", cmaps[5]),
    ]

    for idx, (arr, title, cmap) in enumerate(maps):
        ax = axes[idx // 3, idx % 3]
        im = ax.imshow(arr, cmap=cmap, aspect="auto")
        ax.set_title(title, fontsize=11, fontweight="bold", pad=8)
        ax.set_xticks(range(cols))
        ax.set_xticklabels([f"Col {c}" for c in range(cols)])
        ax.set_yticks(range(rows))
        ax.set_yticklabels([f"Row {r}" for r in range(rows)])
        plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        for r in range(rows):
            for c in range(cols):
                val = arr[r, c]
                text_color = "white" if (idx >= 4 and val > np.mean(arr)) or (idx < 2 and val < np.mean(arr)) else "black"
                ax.text(c, r, f"{val:.0f}", ha="center", va="center", color=text_color, fontsize=9, fontweight="bold")

    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()
    print(f"[+] Saved heatmaps -> {out_path}")


def plot_column_summary(data, out_path):
    summ = data.get("column_summary", {})
    cols = sorted(summ.keys())
    s_neg = [summ[c]["score_neg"] for c in cols]
    s_pos = [summ[c]["score_pos"] for c in cols]
    recs = [summ[c]["recommended_side"].upper() for c in cols]

    x = np.arange(len(cols))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 5.5))
    rects1 = ax.bar(x - width/2, s_neg, width, label="Negative Polarity (W ≤ 0)", color="#1f77b4", alpha=0.85)
    rects2 = ax.bar(x + width/2, s_pos, width, label="Positive Polarity (W ≥ 0)", color="#ff7f0e", alpha=0.85)

    ax.set_ylabel("Mean Quality Score (Swing / (1 + Jerk/10))", fontsize=11, fontweight="bold")
    ax.set_title("Matrix 3 Column-Wise Polarity Quality Score & Recommendation\n(Averaged across all 8 Rows per Column)",
                 fontsize=13, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{c}\n[Rec: {r}]" for c, r in zip(cols, recs)], fontsize=10, fontweight="bold")
    ax.legend(fontsize=11)
    ax.grid(True, axis="y", ls=":", alpha=0.5)

    for r1, r2, rec in zip(rects1, rects2, recs):
        h1 = r1.get_height()
        h2 = r2.get_height()
        ax.text(r1.get_x() + r1.get_width()/2., h1 + 1, f"{h1:.1f}", ha="center", va="bottom", fontsize=9)
        ax.text(r2.get_x() + r2.get_width()/2., h2 + 1, f"{h2:.1f}", ha="center", va="bottom", fontsize=9)

    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()
    print(f"[+] Saved column summary -> {out_path}")


def main():
    if not IN_FILE.exists():
        print(f"Error: {IN_FILE} does not exist yet.")
        sys.exit(1)
    with open(IN_FILE, "r") as f:
        data = json.load(f)

    plot_48cell_grid(data, FIG_DIR / "fig_m3_sigmoid_step1_48cell_grid.png")
    plot_heatmaps(data, FIG_DIR / "fig_m3_sigmoid_step1_heatmaps.png")
    plot_column_summary(data, FIG_DIR / "fig_m3_sigmoid_step1_column_summary.png")


if __name__ == "__main__":
    main()

