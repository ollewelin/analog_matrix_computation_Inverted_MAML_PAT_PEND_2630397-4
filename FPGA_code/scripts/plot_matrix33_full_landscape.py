#!/usr/bin/env python3
"""
plot_matrix33_full_landscape.py
===============================
Generates high-resolution 3D and 2D scientific publication graphics
illustrating the uncompensated 6x6 analog multiplier gain landscape of Matrix 33:
  1. fig_matrix33_3d_gain_topography.png: 3D spatial gain surface & bar landscape.
  2. fig_matrix33_3d_spatiotemporal.png: 3D landscape evolution across time slices.
  3. fig_matrix33_all_36_cells_5curves.png: 6x6 matrix of transfer curves (5 colors).
  4. fig_matrix33_spatial_heatmaps.png: 4-panel annotated heatmaps of matrix parameters.

Uses Python 3 with Matplotlib & NumPy.
"""

from __future__ import annotations
import json
import os
import sys
from pathlib import Path
import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import cm
from mpl_toolkits.mplot3d import Axes3D

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DOCS_DIR = REPO_ROOT / "FPGA_code" / "docs"
FIG_DIR = DOCS_DIR / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)
JSON_PATH = DOCS_DIR / "matrix33_full_landscape.json"

# 5 User-Specified Standardized Publication Colors
COLORS_5 = {
    "-127": "#1976d2",  # Curve 1: Blue
    "-64":  "#d32f2f",  # Curve 2: Red
    "0":    "#388e3c",  # Curve 3: Green
    "+64":  "#f57c00",  # Curve 4: Orange
    "+127": "#fbc02d",  # Curve 5: Yellow (Gold)
}


def load_dataset() -> dict:
    if not JSON_PATH.exists():
        raise FileNotFoundError(f"Missing dataset at {JSON_PATH}")
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def plot_3d_gain_topography(data: dict):
    """
    Figure 1: 3D Surface & 3D Bar Topography of Matrix 33 Gain at nominal t = 5.0 ms.
    """
    times = data.get("time_slices_ms", [5.0])
    target_time_str = "5.0ms" if "5.0ms" in list(data["cells"]["R0_C0"]["by_time"].keys()) else list(data["cells"]["R0_C0"]["by_time"].keys())[0]

    gain_grid = np.zeros((6, 6))
    for r in range(6):
        for c in range(6):
            cell_k = f"R{r}_C{c}"
            if cell_k in data["cells"]:
                cell_entry = data["cells"][cell_k]["by_time"].get(target_time_str, {})
                gain_grid[r, c] = cell_entry.get("peak_gain_mv", 0.0)

    fig = plt.figure(figsize=(15, 7), dpi=300)

    # Left: 3D Surface with contour projection
    ax1 = fig.add_subplot(1, 2, 1, projection="3d")
    X = np.arange(6)
    Y = np.arange(6)
    X_grid, Y_grid = np.meshgrid(X, Y)

    surf = ax1.plot_surface(
        X_grid,
        Y_grid,
        gain_grid,
        cmap=cm.plasma,
        edgecolor="#1E293B",
        linewidth=0.6,
        alpha=0.92,
        antialiased=True,
    )
    # Add contour on bottom plane
    z_min, z_max = np.min(gain_grid), np.max(gain_grid)
    ax1.contour(X_grid, Y_grid, gain_grid, zdir="z", offset=min(-200.0, z_min - 50), cmap=cm.plasma, alpha=0.5)

    ax1.set_title(f"A: 3D Gain Surface Topography\n(t = {target_time_str}, Peak Gain at W = -80 LSB)", fontsize=11, fontweight="bold", pad=12)
    ax1.set_xlabel("Column (ColTIA 0..5)", fontsize=9, labelpad=8)
    ax1.set_ylabel("Row (In-Data 0..5)", fontsize=9, labelpad=8)
    ax1.set_zlabel("Peak Gain ΔV_out (mV)", fontsize=9, labelpad=8)
    ax1.set_xticks(range(6))
    ax1.set_yticks(range(6))
    ax1.view_init(elev=28, azim=225)

    cbar = fig.colorbar(surf, ax=ax1, shrink=0.55, aspect=14, pad=0.08)
    cbar.set_label("ΔV_out (mV)", fontsize=8)

    # Right: 3D Discrete Bar Chart showing crosspoint heights
    ax2 = fig.add_subplot(1, 2, 2, projection="3d")
    _x = np.arange(6)
    _y = np.arange(6)
    _xx, _yy = np.meshgrid(_x, _y)
    x_flat, y_flat = _xx.ravel(), _yy.ravel()
    z_flat = np.zeros_like(x_flat)
    dx = dy = 0.55
    dz = gain_grid.ravel()

    # Colormap based on height
    norm = plt.Normalize(vmin=z_min, vmax=z_max)
    bar_colors = cm.plasma(norm(dz))

    ax2.bar3d(x_flat - dx/2, y_flat - dy/2, z_flat, dx, dy, dz, color=bar_colors, edgecolor="#0F172A", linewidth=0.5, alpha=0.9)
    ax2.set_title(f"B: 3D Discrete Crosspoint Bars\n(Matrix 33 Uncompensated Silicon Matrix)", fontsize=11, fontweight="bold", pad=12)
    ax2.set_xlabel("Column (ColTIA 0..5)", fontsize=9, labelpad=8)
    ax2.set_ylabel("Row (In-Data 0..5)", fontsize=9, labelpad=8)
    ax2.set_zlabel("Gain ΔV_out (mV)", fontsize=9, labelpad=8)
    ax2.set_xticks(range(6))
    ax2.set_yticks(range(6))
    ax2.view_init(elev=28, azim=225)

    fig.suptitle(
        "Inverted MAML — Matrix 33 Full 6x6 Analog Multiplier Gain Topography (Pure Mode B Silicon)",
        fontsize=13,
        fontweight="bold",
        y=0.98,
    )
    plt.tight_layout()
    out_path = FIG_DIR / "fig_matrix33_3d_gain_topography.png"
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"[+] Saved 3D topography: {out_path}")


def plot_3d_spatiotemporal(data: dict):
    """
    Figure 2: 3D Landscape Evolution across available time slices.
    """
    time_keys = list(data["cells"]["R0_C0"]["by_time"].keys())
    if len(time_keys) < 2:
        print("[!] Not enough time slices for spatiotemporal comparison, skipping Fig 2.")
        return

    n_slices = min(4, len(time_keys))
    selected_times = time_keys[:n_slices]

    fig = plt.figure(figsize=(5 * n_slices, 5.5), dpi=300)

    for i, t_k in enumerate(selected_times):
        ax = fig.add_subplot(1, n_slices, i + 1, projection="3d")
        gain_grid = np.zeros((6, 6))
        for r in range(6):
            for c in range(6):
                cell_k = f"R{r}_C{c}"
                if cell_k in data["cells"]:
                    gain_grid[r, c] = data["cells"][cell_k]["by_time"].get(t_k, {}).get("peak_gain_mv", 0.0)

        X_grid, Y_grid = np.meshgrid(range(6), range(6))
        surf = ax.plot_surface(X_grid, Y_grid, gain_grid, cmap=cm.viridis, edgecolor="#1E293B", linewidth=0.4, alpha=0.9)
        ax.set_title(f"t = {t_k}", fontsize=11, fontweight="bold")
        ax.set_xlabel("Col", fontsize=8)
        ax.set_ylabel("Row", fontsize=8)
        ax.set_zlabel("ΔV (mV)", fontsize=8)
        ax.set_xticks(range(6))
        ax.set_yticks(range(6))
        ax.view_init(elev=30, azim=225)

    fig.suptitle(
        "Matrix 33 Spatiotemporal Landscape Evolution (0.5 to 9.2 ms 100 Hz Refresh Cycle)",
        fontsize=13,
        fontweight="bold",
        y=0.98,
    )
    plt.tight_layout()
    out_path = FIG_DIR / "fig_matrix33_3d_spatiotemporal.png"
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"[+] Saved 3D spatiotemporal evolution: {out_path}")


def plot_all_36_cells_grid(data: dict):
    """
    Figure 3: Full 6x6 Matrix Subplot Grid showing the 5 colored curves for EVERY cell!
    """
    target_time_str = "5.0ms" if "5.0ms" in list(data["cells"]["R0_C0"]["by_time"].keys()) else list(data["cells"]["R0_C0"]["by_time"].keys())[0]
    weights = data["weights"]

    fig, axes = plt.subplots(6, 6, figsize=(22, 16), sharex=True, sharey=True, dpi=300)

    for r in range(6):
        for c in range(6):
            ax = axes[r, c]
            cell_k = f"R{r}_C{c}"
            cell_entry = data["cells"].get(cell_k, {}).get("by_time", {}).get(target_time_str, {})
            net_gains = cell_entry.get("net_gain_mv", {})

            if net_gains:
                ax.plot(weights, net_gains.get("-127", []), color=COLORS_5["-127"], lw=1.6, label="X=-127 (Blue)" if (r==0 and c==0) else None)
                ax.plot(weights, net_gains.get("-64",  []), color=COLORS_5["-64"],  lw=1.3, label="X=-64 (Red)" if (r==0 and c==0) else None)
                ax.plot(weights, net_gains.get("0",    []), color=COLORS_5["0"],    lw=1.2, ls="--", label="X=0 (Green)" if (r==0 and c==0) else None)
                ax.plot(weights, net_gains.get("+64",  []), color=COLORS_5["+64"],  lw=1.3, label="X=+64 (Orange)" if (r==0 and c==0) else None)
                ax.plot(weights, net_gains.get("+127", []), color=COLORS_5["+127"], lw=1.6, label="X=+127 (Yellow)" if (r==0 and c==0) else None)

            # Highlighting functional vs saturated
            peak_val = cell_entry.get("peak_gain_mv", 0.0)
            if c in (2, 3) or peak_val < 50.0:
                ax.set_facecolor("#FFF1F2")  # Light red for saturated / defective
            else:
                ax.set_facecolor("#F8FAFC")

            ax.grid(True, alpha=0.3, ls=":")
            ax.axhline(0, color="#64748B", lw=0.6, alpha=0.5)
            ax.set_title(f"Cell ({r},{c}) | {peak_val:+.0f} mV", fontsize=8.2, fontweight="bold", pad=3)

            if r == 5:
                ax.set_xlabel("Weight W (LSB)", fontsize=8)
            if c == 0:
                ax.set_ylabel("Gain (mV)", fontsize=8)

    # Single common legend at top
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.995),
        ncol=5,
        fontsize=10.5,
        frameon=True,
        facecolor="#FFFFFF",
        edgecolor="#CBD5E1",
    )

    fig.suptitle(
        f"Inverted MAML — Matrix 33 Complete 6x6 Multiplier Cell Array (36 Crosspoints, t = {target_time_str})\n"
        "5 Standard In-Data Curves (Blue: -127, Red: -64, Green: 0, Orange: +64, Yellow: +127)",
        fontsize=13,
        fontweight="bold",
        y=0.975,
    )
    plt.tight_layout(rect=[0.01, 0.01, 0.99, 0.955])
    out_path = FIG_DIR / "fig_matrix33_all_36_cells_5curves.png"
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"[+] Saved 36-cell matrix grid: {out_path}")


def plot_spatial_heatmaps(data: dict):
    """
    Figure 4: 4-Panel Annotated Heatmaps of Peak Gain, Turnaround Ratio, Zero Offset, Dynamic Swing.
    """
    target_time_str = "5.0ms" if "5.0ms" in list(data["cells"]["R0_C0"]["by_time"].keys()) else list(data["cells"]["R0_C0"]["by_time"].keys())[0]

    peak_grid = np.zeros((6, 6))
    swing_grid = np.zeros((6, 6))
    turnaround_grid = np.zeros((6, 6))
    offset_grid = np.zeros((6, 6))

    for r in range(6):
        for c in range(6):
            cell_k = f"R{r}_C{c}"
            entry = data["cells"].get(cell_k, {}).get("by_time", {}).get(target_time_str, {})
            peak = entry.get("peak_gain_mv", 0.0)
            swing = entry.get("dynamic_swing_mv", 0.0)
            g_m127 = entry.get("net_gain_mv", {}).get("-127", [0.0])[0] if entry.get("net_gain_mv", {}).get("-127") else 0.0
            g_0 = entry.get("net_gain_mv", {}).get("0", [0.0])[0] if entry.get("net_gain_mv", {}).get("0") else 0.0

            peak_grid[r, c] = peak
            swing_grid[r, c] = swing
            # Turnaround ratio: Peak / V(W=-127)
            turnaround_grid[r, c] = (peak / g_m127) if (g_m127 > 10.0) else 1.0
            offset_grid[r, c] = g_0

    fig, axes = plt.subplots(2, 2, figsize=(13, 11), dpi=300)

    # Panel A: Peak Gain
    imA = axes[0, 0].imshow(peak_grid, cmap="plasma", origin="upper", aspect="auto")
    axes[0, 0].set_title("A: Peak Gain ΔV_out (mV)", fontsize=11, fontweight="bold")
    fig.colorbar(imA, ax=axes[0, 0], shrink=0.85)

    # Panel B: Dynamic Swing
    imB = axes[0, 1].imshow(swing_grid, cmap="viridis", origin="upper", aspect="auto")
    axes[0, 1].set_title("B: Dynamic Swing (Max - Min, mV)", fontsize=11, fontweight="bold")
    fig.colorbar(imB, ax=axes[0, 1], shrink=0.85)

    # Panel C: Turnaround Ratio
    imC = axes[1, 0].imshow(turnaround_grid, cmap="magma", origin="upper", aspect="auto")
    axes[1, 0].set_title("C: Turnaround Ratio (V_peak / V_W=-127)", fontsize=11, fontweight="bold")
    fig.colorbar(imC, ax=axes[1, 0], shrink=0.85)

    # Panel D: Zero Offset
    imD = axes[1, 1].imshow(offset_grid, cmap="coolwarm", origin="upper", aspect="auto")
    axes[1, 1].set_title("D: Quiescent Zero Offset (mV)", fontsize=11, fontweight="bold")
    fig.colorbar(imD, ax=axes[1, 1], shrink=0.85)

    # Annotate values inside each square
    for ax, grid, fmt in zip(axes.flat, [peak_grid, swing_grid, turnaround_grid, offset_grid], [".0f", ".0f", ".1f", ".1f"]):
        ax.set_xticks(range(6))
        ax.set_yticks(range(6))
        ax.set_xlabel("Column (ColTIA 0..5)", fontsize=9)
        ax.set_ylabel("Row (In-Data 0..5)", fontsize=9)
        for r in range(6):
            for c in range(6):
                val = grid[r, c]
                ax.text(c, r, f"{val:{fmt}}", ha="center", va="center", color="white" if abs(val) > 100 else "black", fontsize=8.5, fontweight="bold")

    fig.suptitle(
        f"Inverted MAML — Matrix 33 Spatial Heterogeneity Heatmaps (Pure Mode B Silicon, t = {target_time_str})",
        fontsize=13,
        fontweight="bold",
        y=0.98,
    )
    plt.tight_layout()
    out_path = FIG_DIR / "fig_matrix33_spatial_heatmaps.png"
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"[+] Saved spatial heatmaps: {out_path}")


def main():
    print("=== PLOTTING MATRIX 33 FULL 6x6 GAIN LANDSCAPE GRAPHICS ===")
    data = load_dataset()
    plot_3d_gain_topography(data)
    plot_3d_spatiotemporal(data)
    plot_all_36_cells_grid(data)
    plot_spatial_heatmaps(data)
    print("=== ALL MATRIX 33 GRAPHICS GENERATED SUCCESSFULLY ===")


if __name__ == "__main__":
    main()

