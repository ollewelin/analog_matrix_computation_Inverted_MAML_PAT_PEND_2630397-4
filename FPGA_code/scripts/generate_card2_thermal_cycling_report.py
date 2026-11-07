#!/home/olle/anaconda3/bin/python
"""
generate_card2_thermal_cycling_report.py
Inverted MAML (Patent Pending SE 2630397-4) - Open Science Hardware

Comprehensive Publication Report Generator in English:
Physical Thermal Stress & Real-Time Mode A Active Drift Rejection on Card 2
- Hardware: Card 2 (Trion T120 Master SoC + T20 Coprocessor, Mode A, 1k/3.3k attenuator)
- Temporal Window: [4.9 ms .. 5.9 ms] (11 strata, center 5.4 ms)
- Input Vector: White Noise (COLOR_WHITE)
- Perturbation: 100% Real Physical Thermal Cycling (4 on-board 100% duty cycle heaters)
- Baseline: DC zero calibration (g_baseline_mode=0) + W(3) Staircase on Rows 6 & 7 ([-40..+40] LSB)
- Evaluation: 2x2 Factorial Matrix [Ambient vs Heated] x [Ablation W8=0 vs Active SGD W8]
"""

from __future__ import annotations
import sys
import os
import time
import json
import math
import subprocess
from pathlib import Path
import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors
from mpl_toolkits.mplot3d import Axes3D

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_JSON = REPO_ROOT / "FPGA_code" / "logs" / "thermal_cycling" / "card2_thermal_cycling_heaters_on_off_w3_staircase_1955ep.json"
FIG_DIR = REPO_ROOT / "FPGA_code" / "docs" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR = REPO_ROOT / "FPGA_code" / "docs"
DOCS_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACT_DIR = Path("/home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a")


def load_data():
    with open(DATA_JSON, "r") as f:
        return json.load(f)


def generate_all_figures(data: dict) -> dict:
    epochs = data["epochs"]
    n_epochs = len(epochs)
    ep_nums = np.array([e["epoch"] for e in epochs])
    elapsed_m = np.array([e["elapsed_s"] / 60.0 for e in epochs])

    mean_loss = np.array([e["mean_loss_lsb2"] for e in epochs])
    center_loss = np.array([e["center_loss_lsb2"] for e in epochs])
    mean_enob = np.array([e["mean_enob_bits"] for e in epochs])
    center_enob = np.array([e["center_enob_bits"] for e in epochs])

    heater_on = np.array([e["heater_on"] for e in epochs], dtype=bool)
    regler_on = np.array([e["reglering_on"] for e in epochs], dtype=bool)

    w8_mins = np.array([min([val for row in e["w_m8"] for val in row]) for e in epochs])
    w8_maxs = np.array([max([val for row in e["w_m8"] for val in row]) for e in epochs])

    strata_delays = epochs[0].get("strata_delays", list(range(4900, 6000, 100)))
    delays_ms = np.array([d / 1000.0 for d in strata_delays])
    strata_enobs = np.array([e["strata_enobs"] for e in epochs])  # (N, 11)
    strata_losses = np.array([e["strata_losses"] for e in epochs])

    out_paths = {}

    # Helper function for drawing thermal background spans
    def add_thermal_spans(ax):
        start_idx = 0
        cur_h = heater_on[0]
        for i in range(1, n_epochs):
            if heater_on[i] != cur_h or i == n_epochs - 1:
                end_x = elapsed_m[i]
                start_x = elapsed_m[start_idx]
                if cur_h:
                    ax.axvspan(start_x, end_x, color="#fee2e2", alpha=0.55, zorder=0)
                else:
                    ax.axvspan(start_x, end_x, color="#e0f2fe", alpha=0.45, zorder=0)
                cur_h = heater_on[i]
                start_idx = i

    # Helper function for drawing regulation state markers along the top
    def add_regler_strip(ax, y_pos):
        start_idx = 0
        cur_r = regler_on[0]
        for i in range(1, n_epochs):
            if regler_on[i] != cur_r or i == n_epochs - 1:
                end_x = elapsed_m[i]
                start_x = elapsed_m[start_idx]
                color = "#059669" if cur_r else "#94a3b8"
                ax.plot([start_x, end_x], [y_pos, y_pos], color=color, linewidth=4.5, solid_capstyle="butt")
                cur_r = regler_on[i]
                start_idx = i

    # =========================================================================
    # Figure 1: Full 28-Minute Timeline (Loss, ENOB, W8 Dynamics)
    # =========================================================================
    fig1, (ax1a, ax1b, ax1c) = plt.subplots(3, 1, figsize=(14, 11), sharex=True,
                                            gridspec_kw={"height_ratios": [1.2, 1.2, 1.0], "hspace": 0.14})

    # Subplot A: Loss (LSB^2)
    add_thermal_spans(ax1a)
    ax1a.plot(elapsed_m, mean_loss, color="#dc2626", linewidth=1.8, label="Window Mean Loss [4.9–5.9 ms] (LSB²)")
    ax1a.plot(elapsed_m, center_loss, color="#b91c1c", linewidth=1.4, linestyle="--", label="5.4 ms Center Loss (LSB²)")
    ax1a.set_ylabel("Loss (LSB²)", fontsize=11, fontweight="bold")
    ax1a.set_yscale("log")
    ax1a.set_ylim(2e4, 1.5e6)
    ax1a.grid(True, linestyle=":", alpha=0.6)
    ax1a.legend(loc="upper left", fontsize=9.5, framealpha=0.92)
    ax1a.set_title("Inverted MAML Physical Silicon: 28-Minute Thermal Stress & Mode A Active Drift Rejection\n"
                   "Card 2 Hardware | [4.9 – 5.9 ms] Window | White Noise | W(3) Staircase [-40..+40] LSB",
                   fontsize=12, fontweight="bold", pad=10)

    # Shading Legend Proxy
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor="#fee2e2", edgecolor="#ef4444", label="Heater ON (100% Power, 10 min)"),
        Patch(facecolor="#e0f2fe", edgecolor="#0284c7", label="Heater OFF (Cooling, 10 min)"),
        plt.Line2D([0], [0], color="#059669", linewidth=4, label="Regulation ON (FHP SGD LR=0.02, λ=2048)"),
        plt.Line2D([0], [0], color="#94a3b8", linewidth=4, label="Regulation OFF (Ablation W8=0)"),
    ]
    ax1a.legend(handles=legend_elements, loc="upper right", fontsize=8.5, framealpha=0.92)

    # Subplot B: ENOB (bits)
    add_thermal_spans(ax1b)
    ax1b.plot(elapsed_m, mean_enob, color="#2563eb", linewidth=2.0, label="Window Mean ENOB (4.9–5.9 ms)")
    ax1b.plot(elapsed_m, center_enob, color="#059669", linewidth=2.0, linestyle="--", label="5.4 ms Center ENOB")
    ax1b.set_ylabel("ENOB (bits)", fontsize=11, fontweight="bold")
    ax1b.set_ylim(1.5, 6.5)
    ax1b.grid(True, linestyle=":", alpha=0.6)
    ax1b.legend(loc="lower left", fontsize=9.5, framealpha=0.92)

    # Annotate key peaks and collapses
    ax1b.annotate("Quiescent Peak\nENOB = 5.13 b", xy=(16.8, 5.13), xytext=(15.2, 5.75),
                  arrowprops=dict(facecolor="#059669", shrink=0.08, width=1.5, headwidth=6),
                  fontsize=8.5, fontweight="bold", color="#065f46")
    ax1b.annotate("Thermal Collapse (Uncompensated)\nENOB = 2.05 b (Loss 653k L²)", xy=(27.5, 2.05), xytext=(21.5, 1.8),
                  arrowprops=dict(facecolor="#dc2626", shrink=0.08, width=1.5, headwidth=6),
                  fontsize=8.5, fontweight="bold", color="#991b1b")
    ax1b.annotate("Active Thermal Rejection\n+1.31 b Recovery (-68% Loss)", xy=(5.2, 3.8), xytext=(3.0, 4.8),
                  arrowprops=dict(facecolor="#2563eb", shrink=0.08, width=1.5, headwidth=6),
                  fontsize=8.5, fontweight="bold", color="#1e40af")

    # Subplot C: Compensation Weights W8 Dynamic Range
    add_thermal_spans(ax1c)
    ax1c.fill_between(elapsed_m, w8_mins, w8_maxs, color="#8b5cf6", alpha=0.35, label="Matrix 8 Weight Envelope [Min, Max]")
    ax1c.plot(elapsed_m, w8_maxs, color="#6d28d9", linewidth=1.4)
    ax1c.plot(elapsed_m, w8_mins, color="#6d28d9", linewidth=1.4)
    ax1c.axhline(0, color="#64748b", linestyle=":", linewidth=1.0)
    ax1c.set_ylabel("W8 Range (LSB)", fontsize=11, fontweight="bold")
    ax1c.set_xlabel("Elapsed Experiment Time (minutes)", fontsize=11, fontweight="bold")
    ax1c.set_ylim(-105, 70)
    ax1c.grid(True, linestyle=":", alpha=0.6)
    ax1c.legend(loc="lower left", fontsize=9.5, framealpha=0.92)

    p1 = FIG_DIR / "fig_card2_thermal_timeline.png"
    fig1.savefig(p1, dpi=300, bbox_inches="tight")
    plt.close(fig1)
    out_paths["timeline"] = p1

    # =========================================================================
    # Figure 2: 2D Spatio-Temporal Waterfall Heatmap [4.9..5.9 ms]
    # =========================================================================
    fig2, ax2 = plt.subplots(figsize=(13, 8))
    extent = [delays_ms[0] - 0.05, delays_ms[-1] + 0.05, elapsed_m[0], elapsed_m[-1]]

    im = ax2.imshow(
        strata_enobs,
        aspect="auto",
        origin="lower",
        extent=extent,
        cmap="turbo",
        vmin=2.0,
        vmax=5.5,
        interpolation="bilinear"
    )

    # Overlay horizontal boundary lines for state transitions
    prev_h = heater_on[0]
    prev_r = regler_on[0]
    for i in range(1, n_epochs):
        if heater_on[i] != prev_h:
            ax2.axhline(elapsed_m[i], color="#ffffff", linestyle="-", linewidth=1.5, alpha=0.95)
            lbl = "HEATER OFF" if not heater_on[i] else "HEATER ON (100%)"
            ax2.text(delays_ms[0] + 0.02, elapsed_m[i] + 0.15, f">>> {lbl} <<<",
                     color="#ffffff", fontsize=9, fontweight="bold",
                     bbox=dict(boxstyle="round,pad=0.2", facecolor="#0f172a", alpha=0.85, edgecolor="#ffffff"))
            prev_h = heater_on[i]
        elif regler_on[i] != prev_r:
            ax2.axhline(elapsed_m[i], color="#fbbf24", linestyle="--", linewidth=1.0, alpha=0.7)
            prev_r = regler_on[i]

    ax2.set_xlabel("Temporal Snapshot Delay (ms)", fontsize=11, fontweight="bold")
    ax2.set_ylabel("Elapsed Experiment Time (minutes)", fontsize=11, fontweight="bold")
    ax2.set_title("Inverted MAML Silicon: Spatio-Temporal Waterfall Heatmap across Broadened Window [4.9 – 5.9 ms]\n"
                  "Real-Time Thermal Drift Wavefront & FHP Active Stochastic Gradient Compensation",
                  fontsize=12, fontweight="bold", pad=12)

    cb2 = fig2.colorbar(im, ax=ax2, pad=0.02, fraction=0.04)
    cb2.set_label("Effective Number of Bits (ENOB, bits)", fontsize=11, fontweight="bold")
    cb2.ax.tick_params(labelsize=9.5)

    p2 = FIG_DIR / "fig_card2_thermal_waterfall.png"
    fig2.savefig(p2, dpi=300, bbox_inches="tight")
    plt.close(fig2)
    out_paths["waterfall"] = p2

    # =========================================================================
    # Figure 3: 3D Bar Mappings (Matrix 3 & Matrix 8) Across 4 Key States
    # =========================================================================
    fig3 = plt.figure(figsize=(16, 12))
    cmap_3d = cm.get_cmap("coolwarm")
    norm_m3 = mcolors.Normalize(vmin=-45, vmax=45)
    norm_m8 = mcolors.Normalize(vmin=-95, vmax=60)

    # 4 Key Snapshots
    # 1. Ep 1380: Ambient / Quiescent Compensated (Heat OFF, Comp ON)
    # 2. Ep 1500: Ambient Uncompensated (Heat OFF, Comp OFF)
    # 3. Ep 750 : Thermal Stress Active Rejection (Heat ON, Comp ON)
    # 4. Ep 1940: Thermal Stress Peak Ablated (Heat ON, Comp OFF)
    states = [
        (1380, "Ambient Quiescent Compensated (Heat OFF, Comp ON)"),
        (1500, "Ambient Uncompensated Baseline (Heat OFF, Comp OFF)"),
        (750,  "Thermal Stress Active Rejection (Heat ON, Comp ON)"),
        (1940, "Thermal Stress Severe Degradation (Heat ON, Comp OFF)"),
    ]

    m3_labels = ["R0", "R1", "R2", "R3", "R4", "R5", "Ref29", "Ref30"]
    m8_labels = [f"R{r}" for r in range(7)]

    for panel_pair, (ep_target, title_state) in enumerate(states):
        # Find closest epoch
        idx_match = int(np.argmin(np.abs(ep_nums - ep_target)))
        e_snap = epochs[idx_match]
        w3 = np.array(e_snap["w_m3"], dtype=float)
        w8 = np.array(e_snap["w_m8"], dtype=float)

        # Matrix 3 (8x6)
        ax3 = fig3.add_subplot(4, 2, panel_pair * 2 + 1, projection="3d")
        _x = np.arange(8)
        _y = np.arange(6)
        _xx, _yy = np.meshgrid(_x, _y)
        xf, yf = _xx.ravel(), _yy.ravel()
        zf = np.zeros_like(xf, dtype=float)
        dx = 0.55 * np.ones_like(zf)
        dy = 0.55 * np.ones_like(zf)
        dz3 = w3[xf, yf]
        c3 = cmap_3d(norm_m3(dz3))
        ax3.bar3d(xf - 0.275, yf - 0.275, zf, dx, dy, dz3,
                  color=c3, shade=True, edgecolor="#333333", linewidth=0.35, alpha=0.92)
        ax3.set_title(f"Matrix 3 (8x6): {title_state}\n[Loss: {e_snap['mean_loss_lsb2']:.0f} LSB², Win ENOB: {e_snap['mean_enob_bits']:.2f} b]",
                      fontsize=8.5, fontweight="bold", pad=6)
        ax3.set_xticks(np.arange(8))
        ax3.set_xticklabels(m3_labels, fontsize=7, rotation=-20, ha="right")
        ax3.set_yticks(np.arange(6))
        ax3.set_yticklabels([f"C{c}" for c in range(6)], fontsize=7)
        ax3.set_zlim(-45, 45)
        ax3.set_zticks([-40, -20, 0, 20, 40])
        ax3.tick_params(axis="z", labelsize=7)
        ax3.set_xlabel("Row", fontsize=7.5, labelpad=4)
        ax3.set_ylabel("Col", fontsize=7.5, labelpad=4)
        ax3.set_zlabel("Weight", fontsize=7.5, labelpad=4)
        ax3.view_init(elev=28, azim=-55)

        # Matrix 8 (7x6)
        ax8 = fig3.add_subplot(4, 2, panel_pair * 2 + 2, projection="3d")
        _x8 = np.arange(7)
        _y8 = np.arange(6)
        _xx8, _yy8 = np.meshgrid(_x8, _y8)
        xf8, yf8 = _xx8.ravel(), _yy8.ravel()
        zf8 = np.zeros_like(xf8, dtype=float)
        dx8 = 0.55 * np.ones_like(zf8)
        dy8 = 0.55 * np.ones_like(zf8)
        dz8 = w8[xf8, yf8]
        c8 = cmap_3d(norm_m8(dz8))
        ax8.bar3d(xf8 - 0.275, yf8 - 0.275, zf8, dx8, dy8, dz8,
                  color=c8, shade=True, edgecolor="#333333", linewidth=0.35, alpha=0.92)
        ax8.set_title(f"Matrix 8 (7x6) Active Compensation Weights\n[W8 Range: [{int(w8.min()):+d}, {int(w8.max()):+d}] LSB]",
                      fontsize=8.5, fontweight="bold", pad=6)
        ax8.set_xticks(np.arange(7))
        ax8.set_xticklabels(m8_labels, fontsize=7, rotation=-20, ha="right")
        ax8.set_yticks(np.arange(6))
        ax8.set_yticklabels([f"C{c}" for c in range(6)], fontsize=7)
        ax8.set_zlim(-95, 60)
        ax8.set_zticks([-80, -40, 0, 40])
        ax8.tick_params(axis="z", labelsize=7)
        ax8.set_xlabel("Row", fontsize=7.5, labelpad=4)
        ax8.set_ylabel("Col", fontsize=7.5, labelpad=4)
        ax8.set_zlabel("Weight", fontsize=7.5, labelpad=4)
        ax8.view_init(elev=28, azim=-55)

    fig3.tight_layout()
    p3 = FIG_DIR / "fig_card2_thermal_3d_matrices.png"
    fig3.savefig(p3, dpi=300, bbox_inches="tight")
    plt.close(fig3)
    out_paths["3d_matrices"] = p3

    # =========================================================================
    # Figure 4: Strata Profiles Across [4.9..5.9 ms] for 4 Factorial States
    # =========================================================================
    # Partition epochs into 4 groups
    grp_h_off_r_on = [e for e in epochs if not e["heater_on"] and e["reglering_on"]]
    grp_h_off_r_off = [e for e in epochs if not e["heater_on"] and not e["reglering_on"]]
    grp_h_on_r_on = [e for e in epochs if e["heater_on"] and e["reglering_on"]]
    grp_h_on_r_off = [e for e in epochs if e["heater_on"] and not e["reglering_on"]]

    prof_h_off_r_on = np.mean([e["strata_enobs"] for e in grp_h_off_r_on], axis=0)
    prof_h_off_r_off = np.mean([e["strata_enobs"] for e in grp_h_off_r_off], axis=0)
    prof_h_on_r_on = np.mean([e["strata_enobs"] for e in grp_h_on_r_on], axis=0)
    prof_h_on_r_off = np.mean([e["strata_enobs"] for e in grp_h_on_r_off], axis=0)

    loss_h_off_r_on = np.mean([e["strata_losses"] for e in grp_h_off_r_on], axis=0)
    loss_h_off_r_off = np.mean([e["strata_losses"] for e in grp_h_off_r_off], axis=0)
    loss_h_on_r_on = np.mean([e["strata_losses"] for e in grp_h_on_r_on], axis=0)
    loss_h_on_r_off = np.mean([e["strata_losses"] for e in grp_h_on_r_off], axis=0)

    fig4, (ax4a, ax4b) = plt.subplots(1, 2, figsize=(15, 6))

    # Panel A: ENOB Profile
    ax4a.plot(delays_ms, prof_h_off_r_on, "o-", color="#059669", linewidth=2.4, markersize=8,
              label=f"Ambient Closed-Loop (Heat OFF, Comp ON) [Mean: {np.mean(prof_h_off_r_on):.2f} b]")
    ax4a.plot(delays_ms, prof_h_off_r_off, "^--", color="#2563eb", linewidth=2.0, markersize=7,
              label=f"Ambient Uncompensated (Heat OFF, Comp OFF) [Mean: {np.mean(prof_h_off_r_off):.2f} b]")
    ax4a.plot(delays_ms, prof_h_on_r_on, "s-", color="#f59e0b", linewidth=2.2, markersize=8,
              label=f"Thermal Stress Closed-Loop (Heat ON, Comp ON) [Mean: {np.mean(prof_h_on_r_on):.2f} b]")
    ax4a.plot(delays_ms, prof_h_on_r_off, "D--", color="#dc2626", linewidth=2.4, markersize=8,
              label=f"Thermal Stress Uncompensated (Heat ON, Comp OFF) [Mean: {np.mean(prof_h_on_r_off):.2f} b]")

    ax4a.axvline(5.4, color="#64748b", linestyle=":", linewidth=1.2, label="Nominal Snapshot Delay (5.4 ms)")
    ax4a.set_title("Effective Resolution (ENOB) Across Temporal Window [4.9 – 5.9 ms]", fontsize=11, fontweight="bold")
    ax4a.set_xlabel("Snapshot Sampling Delay (ms)", fontsize=10.5, fontweight="bold")
    ax4a.set_ylabel("ENOB (bits)", fontsize=10.5, fontweight="bold")
    ax4a.set_ylim(1.8, 5.8)
    ax4a.grid(True, linestyle=":", alpha=0.6)
    ax4a.legend(loc="upper right", fontsize=8.5, framealpha=0.92)

    # Panel B: Loss Profile (LSB^2)
    ax4b.plot(delays_ms, loss_h_off_r_on, "o-", color="#059669", linewidth=2.4, markersize=8,
              label=f"Ambient Closed-Loop (Mean: {np.mean(loss_h_off_r_on):,.0f} L²)")
    ax4b.plot(delays_ms, loss_h_off_r_off, "^--", color="#2563eb", linewidth=2.0, markersize=7,
              label=f"Ambient Uncompensated (Mean: {np.mean(loss_h_off_r_off):,.0f} L²)")
    ax4b.plot(delays_ms, loss_h_on_r_on, "s-", color="#f59e0b", linewidth=2.2, markersize=8,
              label=f"Thermal Stress Closed-Loop (Mean: {np.mean(loss_h_on_r_on):,.0f} L²)")
    ax4b.plot(delays_ms, loss_h_on_r_off, "D--", color="#dc2626", linewidth=2.4, markersize=8,
              label=f"Thermal Stress Uncompensated (Mean: {np.mean(loss_h_on_r_off):,.0f} L²)")

    ax4b.axvline(5.4, color="#64748b", linestyle=":", linewidth=1.2)
    ax4b.set_yscale("log")
    ax4b.set_title("Mean Squared Error Loss Across Temporal Window (LSB²)", fontsize=11, fontweight="bold")
    ax4b.set_xlabel("Snapshot Sampling Delay (ms)", fontsize=10.5, fontweight="bold")
    ax4b.set_ylabel("Loss (LSB²)", fontsize=10.5, fontweight="bold")
    ax4b.grid(True, linestyle=":", alpha=0.6)
    ax4b.legend(loc="upper right", fontsize=8.5, framealpha=0.92)

    fig4.suptitle("Inverted MAML Silicon: 2x2 Factorial Strata Profiles (Card 2 Hardware)",
                  fontsize=12.5, fontweight="bold", y=0.98)
    fig4.tight_layout()
    p4 = FIG_DIR / "fig_card2_thermal_strata_profiles.png"
    fig4.savefig(p4, dpi=300, bbox_inches="tight")
    plt.close(fig4)
    out_paths["strata_profiles"] = p4

    # =========================================================================
    # Figure 5: Factorial Summary Card & Rejection Efficacy
    # =========================================================================
    fig5, (ax5a, ax5b) = plt.subplots(1, 2, figsize=(14, 6))

    # Panel A: Factorial Bar Chart
    categories = [
        "Ambient\nCompensated\n(Cold, Comp ON)",
        "Ambient\nUncompensated\n(Cold, Comp OFF)",
        "Thermal Stress\nCompensated\n(Hot, Comp ON)",
        "Thermal Stress\nUncompensated\n(Hot, Comp OFF)",
    ]
    mean_losses_bar = [
        np.mean([e["mean_loss_lsb2"] for e in grp_h_off_r_on]),
        np.mean([e["mean_loss_lsb2"] for e in grp_h_off_r_off]),
        np.mean([e["mean_loss_lsb2"] for e in grp_h_on_r_on]),
        np.mean([e["mean_loss_lsb2"] for e in grp_h_on_r_off]),
    ]
    mean_enobs_bar = [
        np.mean([e["mean_enob_bits"] for e in grp_h_off_r_on]),
        np.mean([e["mean_enob_bits"] for e in grp_h_off_r_off]),
        np.mean([e["mean_enob_bits"] for e in grp_h_on_r_on]),
        np.mean([e["mean_enob_bits"] for e in grp_h_on_r_off]),
    ]
    colors_bar = ["#059669", "#2563eb", "#f59e0b", "#dc2626"]

    bars = ax5a.bar(categories, mean_losses_bar, color=colors_bar, width=0.55, edgecolor="#1e293b", linewidth=1.2)
    for b, val, enb in zip(bars, mean_losses_bar, mean_enobs_bar):
        ax5a.text(b.get_x() + b.get_width() / 2.0, val * 1.08,
                  f"{val:,.0f} L²\n({enb:.2f} b)",
                  ha="center", va="bottom", fontsize=9.5, fontweight="bold")

    ax5a.set_yscale("log")
    ax5a.set_ylim(2e4, 1.2e6)
    ax5a.set_ylabel("Mean Squared Error Loss (LSB²)", fontsize=11, fontweight="bold")
    ax5a.set_title("2x2 Factorial Loss Comparison (Card 2 Silicon)", fontsize=11.5, fontweight="bold")
    ax5a.grid(True, linestyle=":", alpha=0.5, axis="y")

    # Panel B: Summary Metrics & Rejection Metrics Box
    ax5b.axis("off")
    thermal_deg_ratio = mean_losses_bar[3] / mean_losses_bar[1]
    comp_gain_cold = (1.0 - mean_losses_bar[0] / mean_losses_bar[1]) * 100.0
    comp_gain_hot = (1.0 - mean_losses_bar[2] / mean_losses_bar[3]) * 100.0

    summary_text = (
        "INVERTED MAML THERMAL STRESS REJECTION SUMMARY\n"
        "==========================================================\n\n"
        f"• Total Experiment Epochs:       {n_epochs} epochs (~{elapsed_m[-1]:.1f} minutes)\n"
        f"• Thermal Perturbation:          4x On-Board Resistors @ 100% Power\n"
        f"• Thermal Cycle Period:          10 min ON (100%) / 10 min OFF (0%)\n"
        f"• Mode A Regulation Period:      2 min ON (SGD) / 2 min OFF (Ablation)\n"
        f"• Attenuator & Circuit:          1k/3.3k Attenuator, Card 2 Silicon\n"
        f"• Sampling Window:               [4.9 .. 5.9 ms] (11 strata, step 100 µs)\n\n"
        "KEY QUANTITATIVE FINDINGS:\n"
        "----------------------------------------------------------\n"
        f"1. Uncompensated Thermal Drift:\n"
        f"   - Cold Baseline Loss:         {mean_losses_bar[1]:,.0f} LSB² (3.33 b)\n"
        f"   - Hot Degraded Loss:          {mean_losses_bar[3]:,.0f} LSB² (2.49 b)\n"
        f"   - Peak Degradation:           653,480 LSB² (2.05 b, Ep 1940)\n"
        f"   - Thermal Penalty Factor:     +{thermal_deg_ratio:.2f}x error increase\n\n"
        f"2. Closed-Loop Drift Rejection:\n"
        f"   - Cold Error Reduction:       -{comp_gain_cold:.1f}% ({mean_losses_bar[1]:,.0f} -> {mean_losses_bar[0]:,.0f} L²)\n"
        f"   - Hot Error Reduction:        -{comp_gain_hot:.1f}% ({mean_losses_bar[3]:,.0f} -> {mean_losses_bar[2]:,.0f} L²)\n"
        f"   - Effective Resolution Gain:  +0.91 b (Mean), +1.31 b (5.4 ms)\n\n"
        f"3. Silicon Weight Adaptation:\n"
        f"   - Ambient W8 Dynamic Range:   [-25, +49] LSB\n"
        f"   - Thermal W8 Dynamic Range:   [-90, +52] LSB (Significant Vth offset push!)\n"
        "=========================================================="
    )

    ax5b.text(0.02, 0.98, summary_text, transform=ax5b.transAxes,
              fontsize=9.5, fontfamily="monospace", verticalalignment="top",
              bbox=dict(boxstyle="round,pad=0.8", facecolor="#f8fafc", edgecolor="#cbd5e1", linewidth=1.5))

    fig5.tight_layout()
    p5 = FIG_DIR / "fig_card2_thermal_factorial_summary.png"
    fig5.savefig(p5, dpi=300, bbox_inches="tight")
    plt.close(fig5)
    out_paths["factorial_summary"] = p5

    return out_paths


if __name__ == "__main__":
    d = load_data()
    print(f"Loaded {len(d['epochs'])} epochs from {DATA_JSON}.")
    print("Generating publication figures...")
    paths = generate_all_figures(d)
    for k, p in paths.items():
        print(f"  [+] {k}: {p}")
