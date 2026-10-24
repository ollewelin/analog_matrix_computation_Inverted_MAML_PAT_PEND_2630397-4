#!/home/olle/anaconda3/bin/python3
"""
Plotting script for Comprehensive Physical Silicon Characterization of Cell (0,0)
================================================================================
Generates publication-quality figures:
  1. fig_cell_0_0_5curves_nominal_5ms.png (5 colored curves at t = 5.0 ms)
  2. fig_cell_0_0_10_time_slices.png (10-panel grid from 0.5 ms to 9.2 ms)
  3. fig_cell_0_0_temporal_decay.png (Capacitive retention & leakage decay over 10 ms)
  4. fig_cell_0_0_surface_3d.png (3D Transfer Surface at t = 5.0 ms)
"""

import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DOCS_DIR = REPO_ROOT / "FPGA_code" / "docs"
FIG_DIR = DOCS_DIR / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

JSON_PATH = DOCS_DIR / "cell_0_0_comprehensive_sweep.json"
with open(JSON_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

curves_by_time = data["curves_by_time"]
weights = np.array(data["weights"])

# Exact user-specified colors:
# 1. -127: blue
# 2. -64:  red
# 3. 0:    green
# 4. +64:  orange
# 5. +127: yellow / gold
COLOR_MAP = {
    "-127": "#1976d2",  # Vivid Blue
    "-64":  "#d32f2f",  # Bold Red
    "0":    "#388e3c",  # Deep Green
    "+64":  "#f57c00",  # Vibrant Orange
    "+127": "#fbc02d",  # Sun Yellow
}

LABEL_MAP = {
    "-127": r"Data $X = -127$ LSB (Blue)",
    "-64":  r"Data $X = -64$ LSB (Red)",
    "0":    r"Data $X = 0$ LSB (Green)",
    "+64":  r"Data $X = +64$ LSB (Orange)",
    "+127": r"Data $X = +127$ LSB (Yellow)",
}

# -----------------------------------------------------------------------------
# FIGURE 1: Primary Nominal Multiplication Graph at t = 5.0 ms
# -----------------------------------------------------------------------------
def plot_figure_1_nominal():
    fig, ax = plt.subplots(figsize=(10, 6.5), dpi=300)
    ax.set_facecolor("#ffffff")
    fig.patch.set_facecolor("#ffffff")

    entry_5ms = curves_by_time["5.0ms"]
    net_gains = entry_5ms["net_gain_mv"]

    for key in ["-127", "-64", "0", "+64", "+127"]:
        y = np.array(net_gains[key])
        color = COLOR_MAP[key]
        label = LABEL_MAP[key]
        lw = 2.4 if key in ("-127", "+127") else 1.8
        marker = "o" if key in ("-127", "+127") else "s"
        ms = 4.5 if key in ("-127", "+127") else 3.5

        if key == "+127":
            # Yellow curve with subtle dark edge for maximum visibility
            ax.plot(weights, y, label=label, color=color, linewidth=lw, marker=marker,
                    markersize=ms, markeredgecolor="#7f6000", markeredgewidth=0.7)
        else:
            ax.plot(weights, y, label=label, color=color, linewidth=lw, marker=marker, markersize=ms)

    ax.axhline(0, color="#616161", linestyle="--", linewidth=0.9, alpha=0.7)
    ax.axvline(0, color="#616161", linestyle="--", linewidth=0.9, alpha=0.7)

    # Annotate Key Physical Features
    ax.annotate("Peak Gain: +512.4 mV\n(W = -80 LSB)",
                xy=(-80, 512.4), xytext=(-65, 540),
                arrowprops=dict(arrowstyle="->", color="#1976d2", lw=1.5),
                fontsize=9.5, fontweight="bold", color="#1976d2",
                bbox=dict(boxstyle="round,pad=0.3", fc="#e3f2fd", ec="#1976d2", lw=1))

    ax.annotate("Turnaround Roll-over\n(W < -100 LSB)\nSubthreshold pinch-off",
                xy=(-120, 244.1), xytext=(-125, 360),
                arrowprops=dict(arrowstyle="->", color="#b71c1c", lw=1.5),
                fontsize=8.5, color="#b71c1c",
                bbox=dict(boxstyle="round,pad=0.3", fc="#ffebee", ec="#b71c1c", lw=1))

    ax.annotate("Electrical Null\n(W ≈ -5 LSB)\nGain ≈ 0 mV",
                xy=(-5, 0), xytext=(12, 120),
                arrowprops=dict(arrowstyle="->", color="#2e7d32", lw=1.5),
                fontsize=8.5, color="#2e7d32",
                bbox=dict(boxstyle="round,pad=0.3", fc="#e8f5e9", ec="#2e7d32", lw=1))

    ax.set_title("Physical Multiplier Transfer Characteristic: Cell (0,0) on Matrix 33 (Mode B)\n"
                 r"Nominal Snapshot Slice $t = 5.0\ \mathrm{ms}$ Post-Refresh ($100\ \mathrm{Hz}$ Autonomous Refresh Active)",
                 fontsize=12, fontweight="bold", pad=12, color="#111827")
    ax.set_xlabel(r"Differential Weight Voltage $W$ (LSB, $[-127 \dots +127]$)", fontsize=10.5, labelpad=8)
    ax.set_ylabel(r"Multiplier Gain Output $\Delta V_{\mathrm{out}}$ (mV relative to $X=0$)", fontsize=10.5, labelpad=8)

    ax.set_xlim(-135, 135)
    ax.set_ylim(-480, 620)
    ax.grid(True, linestyle=":", alpha=0.6, color="#9e9e9e")
    ax.legend(loc="lower left", framealpha=0.92, facecolor="#fafafa", edgecolor="#cfd8dc", fontsize=9)

    fig.tight_layout()
    out_path = FIG_DIR / "fig_cell_0_0_5curves_nominal_5ms.png"
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"[+] Saved Figure 1: {out_path}")


# -----------------------------------------------------------------------------
# FIGURE 2: 10-Panel Grid Across Time Window (0.5 ms to 9.2 ms)
# -----------------------------------------------------------------------------
def plot_figure_2_ten_slices():
    fig, axes = plt.subplots(2, 5, figsize=(18, 7.5), dpi=300, sharex=True, sharey=True)
    fig.patch.set_facecolor("#ffffff")

    time_keys = list(curves_by_time.keys())
    for idx, key in enumerate(time_keys):
        r = idx // 5
        c = idx % 5
        ax = axes[r, c]
        ax.set_facecolor("#ffffff")

        entry = curves_by_time[key]
        d_ms = entry["delay_ms"]
        net_gains = entry["net_gain_mv"]

        for k in ["-127", "-64", "0", "+64", "+127"]:
            y = np.array(net_gains[k])
            color = COLOR_MAP[k]
            lw = 1.8 if k in ("-127", "+127") else 1.2
            ax.plot(weights, y, color=color, linewidth=lw)

        ax.axhline(0, color="#757575", linestyle="--", linewidth=0.7, alpha=0.6)
        ax.axvline(0, color="#757575", linestyle="--", linewidth=0.7, alpha=0.6)

        # Subplot Title with Status
        if d_ms <= 1.0:
            status = "Transient / Clamped"
            bg_badge = "#eeeeee"
        elif d_ms <= 1.5:
            status = "Recovery Boundary"
            bg_badge = "#fff3e0"
        elif d_ms <= 3.5:
            status = "Peak Amplification"
            bg_badge = "#e8f5e9"
        elif d_ms <= 5.5:
            status = "Settled Linear Regime"
            bg_badge = "#e3f2fd"
        else:
            status = "Capacitive Decay"
            bg_badge = "#f3e5f5"

        ax.set_title(f"t = {d_ms:.1f} ms\n({status})", fontsize=9.5, fontweight="bold",
                     bbox=dict(boxstyle="round,pad=0.25", fc=bg_badge, ec="#bdbdbd", lw=0.6))
        ax.set_xlim(-135, 135)
        ax.set_ylim(-450, 1150)
        ax.grid(True, linestyle=":", alpha=0.5, color="#bdbdbd")

        if r == 1:
            ax.set_xlabel("Weight $W$ (LSB)", fontsize=8.5)
        if c == 0:
            ax.set_ylabel(r"Gain $\Delta V_{\mathrm{out}}$ (mV)", fontsize=8.5)

    # Custom Common Legend at the bottom
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], color=COLOR_MAP["-127"], lw=2, label="Data X = -127 (Blue)"),
        Line2D([0], [0], color=COLOR_MAP["-64"], lw=2, label="Data X = -64 (Red)"),
        Line2D([0], [0], color=COLOR_MAP["0"], lw=2, label="Data X = 0 (Green)"),
        Line2D([0], [0], color=COLOR_MAP["+64"], lw=2, label="Data X = +64 (Orange)"),
        Line2D([0], [0], color=COLOR_MAP["+127"], lw=2, label="Data X = +127 (Yellow)"),
    ]
    fig.legend(handles=legend_elements, loc="lower center", ncol=5, fontsize=9.5,
               framealpha=0.9, facecolor="#f5f5f5", edgecolor="#b0bec5", bbox_to_anchor=(0.5, -0.02))

    fig.suptitle("Evolution of Single-Cell Multiplier Response across the 10 ms Operating Cycle (Cell 0,0 on Matrix 33)\n"
                 "Measured in 10 Continuous Snapshot Slices from t = 0.5 ms (Recharge Boundary) to t = 9.2 ms (Pre-Refresh)",
                 fontsize=12, fontweight="bold", y=1.02, color="#111827")

    fig.tight_layout()
    out_path = FIG_DIR / "fig_cell_0_0_10_time_slices.png"
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"[+] Saved Figure 2: {out_path}")


# -----------------------------------------------------------------------------
# FIGURE 3: Capacitive Leakage Decay Curve across the 10 ms Cycle
# -----------------------------------------------------------------------------
def plot_figure_3_decay():
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=300)
    ax.set_facecolor("#ffffff")
    fig.patch.set_facecolor("#ffffff")

    delays = []
    peak_diff_127 = []
    peak_diff_64 = []

    for key, entry in curves_by_time.items():
        delays.append(entry["delay_ms"])
        d127 = np.array(entry["diff_gain_mv"]["127"])
        d64  = np.array(entry["diff_gain_mv"]["64"])
        peak_diff_127.append(np.max(np.abs(d127)))
        peak_diff_64.append(np.max(np.abs(d64)))

    delays = np.array(delays)
    peak_diff_127 = np.array(peak_diff_127)
    peak_diff_64 = np.array(peak_diff_64)

    ax.plot(delays, peak_diff_127, marker="o", color="#1565c0", lw=2.2, label=r"Peak Multiplier Dynamic Range ($X = \pm 127$)")
    ax.plot(delays, peak_diff_64, marker="s", color="#e65100", lw=1.8, label=r"Half-Scale Dynamic Range ($X = \pm 64$)")

    ax.axvspan(0.0, 1.5, color="#ffcdd2", alpha=0.35, label="Refresh Transient & Clamp Zone")
    ax.axvspan(1.5, 4.0, color="#c8e6c9", alpha=0.35, label="High-Gain Peak Window")
    ax.axvspan(4.0, 6.0, color="#bbdefb", alpha=0.35, label="Nominal Quiet Operating Window (5.0 ms)")
    ax.axvspan(6.0, 9.5, color="#e1bee7", alpha=0.35, label="100 nF Subthreshold Leakage Discharge")

    ax.set_title(r"Dual-2T1C Cell (0,0) Dynamic Retention & Decay Profile ($10\ \mathrm{ms}$ Cycle)",
                 fontsize=11, fontweight="bold", pad=10)
    ax.set_xlabel(r"Snapshot Sampling Delay Post-Refresh $t$ (ms)", fontsize=10)
    ax.set_ylabel(r"Maximum Measured Multiplier Swing $|V_{\mathrm{diff}}|$ (mV)", fontsize=10)
    ax.set_xlim(0, 9.5)
    ax.set_ylim(-20, 1150)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(loc="upper right", fontsize=8.5, framealpha=0.9)

    fig.tight_layout()
    out_path = FIG_DIR / "fig_cell_0_0_temporal_decay.png"
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"[+] Saved Figure 3: {out_path}")


# -----------------------------------------------------------------------------
# FIGURE 4: 3D Multiplier Surface (W, X -> Output) at t = 5.0 ms
# -----------------------------------------------------------------------------
def plot_figure_4_surface_3d():
    fig = plt.figure(figsize=(9, 6.5), dpi=300)
    ax = fig.add_subplot(111, projection="3d")
    ax.set_facecolor("#ffffff")
    fig.patch.set_facecolor("#ffffff")

    entry_5ms = curves_by_time["5.0ms"]
    x_vals = np.array([-127, -64, 0, 64, 127])
    w_vals = weights

    W_grid, X_grid = np.meshgrid(w_vals, x_vals)
    Z_grid = np.zeros_like(W_grid, dtype=float)

    for i, x_str in enumerate(["-127", "-64", "0", "+64", "+127"]):
        Z_grid[i, :] = entry_5ms["net_gain_mv"][x_str]

    surf = ax.plot_surface(W_grid, X_grid, Z_grid, cmap="coolwarm", edgecolor="none", alpha=0.88, antialiased=True)
    cbar = fig.colorbar(surf, ax=ax, shrink=0.55, aspect=12, pad=0.1)
    cbar.set_label(r"Gain $\Delta V_{\mathrm{out}}$ (mV)", fontsize=9)

    ax.set_xlabel("Weight $W$ (LSB)", fontsize=9, labelpad=6)
    ax.set_ylabel("In-Data $X$ (LSB)", fontsize=9, labelpad=6)
    ax.set_zlabel("Gain Output (mV)", fontsize=9, labelpad=6)
    ax.set_title(r"3D Measured Multiplier Output Surface: Cell (0,0) at $t = 5.0\ \mathrm{ms}$",
                 fontsize=11, fontweight="bold", pad=10)
    ax.view_init(elev=24, azim=135)

    fig.tight_layout()
    out_path = FIG_DIR / "fig_cell_0_0_surface_3d.png"
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"[+] Saved Figure 4: {out_path}")


def main():
    plot_figure_1_nominal()
    plot_figure_2_ten_slices()
    plot_figure_3_decay()
    plot_figure_4_surface_3d()
    print("[SUCCESS] All 4 publication-quality figures generated successfully!")


if __name__ == "__main__":
    main()
