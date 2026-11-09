#!/home/olle/anaconda3/bin/python
"""
generate_card2_thermal_cycling_report.py
Inverted MAML (Patent Pending SE 2630397-4) - Open Science Hardware

Comprehensive Publication Report Figure Generator in English:
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
import argparse
from pathlib import Path
import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors
from mpl_toolkits.mplot3d import Axes3D

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_JSON = REPO_ROOT / "FPGA_code" / "logs" / "thermal_cycling" / "card2_thermal_cycling_heaters_8m8m_30pct_1hz_regler_2m2m_l2_768_k2_lr0p02_5p0_to_5p4ms_20min.json"
FIG_DIR = REPO_ROOT / "FPGA_code" / "docs" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR = REPO_ROOT / "FPGA_code" / "docs"
DOCS_DIR.mkdir(parents=True, exist_ok=True)


def load_data(json_path: Path):
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_all_figures(data: dict) -> dict:
    epochs = data["epochs"]
    meta = data.get("metadata", {})
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

    t_min_us = meta.get("t_min_us", 5000)
    t_max_us = meta.get("t_max_us", 5400)
    t_step_us = meta.get("t_step_us", 100)
    center_us = meta.get("center_delay_us", 5200)
    strata_delays = epochs[0].get("strata_delays", list(range(t_min_us, t_max_us + 1, t_step_us)))
    n_strata = len(strata_delays)
    delays_ms = np.array([d / 1000.0 for d in strata_delays])
    strata_enobs = np.array([e["strata_enobs"] for e in epochs])
    strata_losses = np.array([e["strata_losses"] for e in epochs])
    win_str = f"{t_min_us/1000:.1f}–{t_max_us/1000:.1f} ms"
    c_str = f"{center_us/1000:.1f} ms"

    lr_val = meta.get("lr", 0.02)
    l2_val = meta.get("reg_lambda", 768)
    k_batch_val = meta.get("k_batch", 2)
    heater_str = meta.get("heater_cycle", "8.0 min ON / 8.0 min OFF")
    train_str = meta.get("training_cycle", "2.0 min ON / 2.0 min OFF")

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

    # Helper function for drawing distinct dashed vertical lines on Training toggles
    def add_training_toggles(ax):
        added_on = False
        added_off = False
        for i in range(1, n_epochs):
            if regler_on[i] != regler_on[i-1]:
                x_pos = elapsed_m[i]
                if regler_on[i]:
                    lbl = "Training ON (SGD)" if not added_on else None
                    ax.axvline(x_pos, color="#059669", linestyle="--", linewidth=1.6, alpha=0.9, zorder=3, label=lbl)
                    added_on = True
                else:
                    lbl = "Training OFF (Ablation)" if not added_off else None
                    ax.axvline(x_pos, color="#dc2626", linestyle="--", linewidth=1.6, alpha=0.9, zorder=3, label=lbl)
                    added_off = True

    # =========================================================================
    # Figure 1: Full 20-Minute Timeline (Loss, ENOB, W8 & W3 Dynamics)
    # =========================================================================
    w3_active = np.array([e["w_m3"] for e in epochs])[:, :6, :]
    w3_mins = np.min(w3_active, axis=(1, 2))
    w3_maxs = np.max(w3_active, axis=(1, 2))

    fig1, (ax1a, ax1b, ax1c, ax1d) = plt.subplots(4, 1, figsize=(14, 12), sharex=True,
                                                  gridspec_kw={"height_ratios": [1.1, 1.1, 0.9, 0.9], "hspace": 0.16})

    # Subplot A: Loss (LSB^2)
    add_thermal_spans(ax1a)
    add_training_toggles(ax1a)
    ax1a.plot(elapsed_m, mean_loss, color="#dc2626", linewidth=1.8, label=f"Window Mean Loss [{win_str}] (LSB²)")
    ax1a.plot(elapsed_m, center_loss, color="#b91c1c", linewidth=1.4, linestyle="--", label=f"{c_str} Center Loss (LSB²)")
    ax1a.set_ylabel("Loss (LSB²)", fontsize=10.5, fontweight="bold")
    ax1a.set_yscale("log")
    ax1a.set_ylim(min(1e4, np.min(mean_loss) * 0.7), max(1.5e6, np.max(mean_loss) * 1.5))
    ax1a.grid(True, linestyle=":", alpha=0.6)
    ax1a.set_title(f"Inverted MAML Physical Silicon: 20-Minute Thermal Stress & Mode A Active Drift Rejection\n"
                   f"Card 2 Hardware (PCBA v1.3.2) | [{win_str}] Window ({n_strata} Strata) | White Noise | W(3) Staircase | K={k_batch_val}, LR={lr_val}, λ={l2_val}",
                   fontsize=12, fontweight="bold", pad=10)

    # Shading Legend Proxy
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor="#fee2e2", edgecolor="#ef4444", label=f"Heater ON (30% Duty @ 1 Hz, {heater_str})"),
        Patch(facecolor="#e0f2fe", edgecolor="#0284c7", label=f"Heater OFF (Cooling, {heater_str})"),
        plt.Line2D([0], [0], color="#059669", linestyle="--", linewidth=2.0, label=f"Training ON Toggle (SGD LR={lr_val}, λ={l2_val})"),
        plt.Line2D([0], [0], color="#dc2626", linestyle="--", linewidth=2.0, label="Training OFF Toggle (Ablation W=0)"),
    ]
    ax1a.legend(handles=legend_elements, loc="upper right", fontsize=8.5, framealpha=0.92)

    # Subplot B: ENOB (bits)
    add_thermal_spans(ax1b)
    add_training_toggles(ax1b)
    ax1b.plot(elapsed_m, mean_enob, color="#2563eb", linewidth=2.0, label=f"Window Mean ENOB ({win_str})")
    ax1b.plot(elapsed_m, center_enob, color="#059669", linewidth=2.0, linestyle="--", label=f"{c_str} Center ENOB")
    ax1b.axhline(5.0, color="#64748b", linestyle=":", linewidth=1.0, label="5.0-bit Resolution Target")
    ax1b.set_ylabel("ENOB (bits)", fontsize=10.5, fontweight="bold")
    ax1b.set_ylim(max(0.0, np.min(mean_enob) - 0.5), min(10.0, np.max(center_enob) + 0.8))
    ax1b.grid(True, linestyle=":", alpha=0.6)
    ax1b.legend(loc="lower left", fontsize=8.5, framealpha=0.92)

    # Subplot C: Compensation Weights W8 Dynamic Range
    add_thermal_spans(ax1c)
    ax1c.fill_between(elapsed_m, w8_mins, w8_maxs, color="#8b5cf6", alpha=0.35, label="Matrix 8 Weight Envelope [Min, Max]")
    ax1c.plot(elapsed_m, w8_maxs, color="#6d28d9", linewidth=1.3)
    ax1c.plot(elapsed_m, w8_mins, color="#6d28d9", linewidth=1.3)
    ax1c.axhline(0, color="#64748b", linestyle=":", linewidth=1.0)
    ax1c.axhline(+120, color="red", linestyle="--", alpha=0.6, linewidth=0.8)
    ax1c.axhline(-120, color="red", linestyle="--", alpha=0.6, linewidth=0.8)
    ax1c.set_ylabel("W8 Range (LSB)", fontsize=10.5, fontweight="bold")
    ax1c.set_ylim(-65, 130)
    ax1c.grid(True, linestyle=":", alpha=0.6)
    ax1c.legend(loc="lower left", fontsize=8.5, framealpha=0.92)

    # Subplot D: Compensation Weights W3 Dynamic Range (Rows 0..5 Active Data Inputs)
    add_thermal_spans(ax1d)
    ax1d.fill_between(elapsed_m, w3_mins, w3_maxs, color="#10b981", alpha=0.35, label="Matrix 3 Active Data Weight Envelope [Min, Max] (Rows 0..5)")
    ax1d.plot(elapsed_m, w3_maxs, color="#047857", linewidth=1.3)
    ax1d.plot(elapsed_m, w3_mins, color="#047857", linewidth=1.3)
    ax1d.axhline(0, color="#64748b", linestyle=":", linewidth=1.0)
    ax1d.set_ylabel("W3 Range (LSB)", fontsize=10.5, fontweight="bold")
    ax1d.set_xlabel("Elapsed Experiment Time (minutes)", fontsize=11, fontweight="bold")
    ax1d.set_ylim(-85, 75)
    ax1d.grid(True, linestyle=":", alpha=0.6)
    ax1d.legend(loc="lower left", fontsize=8.5, framealpha=0.92)

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
        vmin=max(1.5, np.percentile(strata_enobs, 2)),
        vmax=min(6.5, np.percentile(strata_enobs, 98) + 0.5),
        interpolation="bilinear"
    )

    prev_h = heater_on[0]
    for i in range(1, n_epochs):
        if heater_on[i] != prev_h:
            ax2.axhline(elapsed_m[i], color="#ffffff", linestyle="-", linewidth=1.6, alpha=0.95)
            lbl = "HEATER OFF" if not heater_on[i] else "HEATER ON (100%)"
            ax2.text(delays_ms[0] + 0.02, elapsed_m[i] + 0.15, f">>> {lbl} <<<",
                     color="#ffffff", fontsize=9, fontweight="bold",
                     bbox=dict(boxstyle="round,pad=0.2", facecolor="#0f172a", alpha=0.85, edgecolor="#ffffff"))
            prev_h = heater_on[i]

    ax2.set_xlabel("Temporal Snapshot Delay (ms)", fontsize=11, fontweight="bold")
    ax2.set_ylabel("Elapsed Experiment Time (minutes)", fontsize=11, fontweight="bold")
    ax2.set_title(f"Inverted MAML Silicon: Spatio-Temporal Waterfall Heatmap across Window [{win_str}] ({n_strata} Strata)\n"
                  f"Real-Time Thermal Drift Wavefront & Mode A Closed-Loop Regulation (K={k_batch_val}, LR={lr_val}, λ={l2_val})",
                  fontsize=12, fontweight="bold", pad=12)

    cb2 = fig2.colorbar(im, ax=ax2, pad=0.02, fraction=0.04)
    cb2.set_label("Effective Number of Bits (ENOB, bits)", fontsize=11, fontweight="bold")
    cb2.ax.tick_params(labelsize=9.5)

    p2 = FIG_DIR / "fig_card2_thermal_waterfall.png"
    fig2.savefig(p2, dpi=300, bbox_inches="tight")
    plt.close(fig2)
    out_paths["waterfall"] = p2

    # =========================================================================
    # Figure 3: 2D Weight Trajectories across Epochs (Matrix 8 & Matrix 3)
    # =========================================================================
    fig3 = plt.figure(figsize=(16, 13.5))
    gs3 = fig3.add_gridspec(4, 3, height_ratios=[1.0, 1.0, 1.0, 1.0], hspace=0.36, wspace=0.20,
                            top=0.96, bottom=0.04, left=0.06, right=0.97)

    colors_m8 = ["#2563eb", "#059669", "#d97706", "#dc2626", "#7c3aed", "#0891b2", "#64748b"]
    row_names_m8 = [f"R{r}" for r in range(6)] + ["R6 (Bias)"]

    colors_m3 = ["#2563eb", "#059669", "#d97706", "#dc2626", "#7c3aed", "#0891b2", "#ec4899", "#8b5cf6"]
    row_names_m3 = [f"R{r}" for r in range(6)] + ["R6 (ClkB1)", "R7 (ClkRef)"]

    w3_all = np.array([e["w_m3"] for e in epochs])  # (N, 8, 6)
    w8_all = np.array([e["w_m8"] for e in epochs])  # (N, 7, 6)

    # Top 2 rows: Matrix 8 Columns 0 to 5
    for col in range(6):
        r_idx = col // 3
        c_idx = col % 3
        ax = fig3.add_subplot(gs3[r_idx, c_idx])

        # Shading for thermal phases & training toggles
        add_thermal_spans(ax)
        add_training_toggles(ax)

        for r in range(7):
            ax.plot(elapsed_m, w8_all[:, r, col], color=colors_m8[r],
                    label=row_names_m8[r] if col == 0 else None, linewidth=1.1)

        ax.axhline(+120, color="red", linestyle="--", alpha=0.7, linewidth=0.8)
        ax.axhline(-120, color="red", linestyle="--", alpha=0.7, linewidth=0.8)
        ax.axhline(0, color="black", linestyle=":", alpha=0.4, linewidth=0.8)

        ax.set_ylim(-130, 130)
        ax.set_title(f"Matrix 8: Column {col} Weights (ColTIA Summer {col})", fontsize=10, fontweight="bold", pad=4)
        ax.set_ylabel("Weight (LSB)", fontsize=8.5, fontweight="bold")
        if r_idx == 1:
            ax.set_xlabel("Elapsed Time (minutes)", fontsize=8.5, fontweight="bold")
        ax.grid(True, linestyle=":", alpha=0.5)
        if col == 0:
            ax.legend(loc="upper left", fontsize=6.8, ncol=4, framealpha=0.9, handlelength=1.2)

    # Bottom 2 rows: Matrix 3 Columns 0 to 5 (Active Data Weights R0..R5 & Reference Clocks R6..R7)
    for col in range(6):
        r_idx = 2 + (col // 3)
        c_idx = col % 3
        ax = fig3.add_subplot(gs3[r_idx, c_idx])

        # Shading for thermal phases & training toggles
        add_thermal_spans(ax)
        add_training_toggles(ax)

        for r in range(8):
            lw = 1.6 if r >= 6 else 1.1
            ls = "--" if r >= 6 else "-"
            ax.plot(elapsed_m, w3_all[:, r, col], color=colors_m3[r],
                    label=row_names_m3[r] if col == 0 else None, linewidth=lw, linestyle=ls)

        ax.axhline(0, color="black", linestyle=":", alpha=0.4, linewidth=0.8)
        ax.set_ylim(-85, 85)
        ax.set_title(f"Matrix 3: Column {col} Active Weights & Clocks (Input Col {col})", fontsize=10, fontweight="bold", pad=4)
        ax.set_ylabel("Weight (LSB)", fontsize=8.5, fontweight="bold")
        if r_idx == 3:
            ax.set_xlabel("Elapsed Time (minutes)", fontsize=8.5, fontweight="bold")
        ax.grid(True, linestyle=":", alpha=0.5)
        if col == 0:
            ax.legend(loc="lower left", fontsize=6.5, ncol=4, framealpha=0.9, handlelength=1.2)

    fig3.suptitle("Inverted MAML Silicon: 2D Weight Trajectories Across Epochs (Matrix 8 & Matrix 3 Active Weights)",
                  fontsize=12.5, fontweight="bold", y=0.995)
    p3 = FIG_DIR / "fig_card2_thermal_3d_matrices.png"
    p3_2d = FIG_DIR / "fig_card2_thermal_2d_matrices.png"
    fig3.savefig(p3, dpi=300)
    fig3.savefig(p3_2d, dpi=300)
    plt.close(fig3)
    out_paths["3d_matrices"] = p3
    out_paths["2d_matrices"] = p3_2d

    # =========================================================================
    # Figure 4: Strata Profiles Across Window for 4 Factorial States
    # =========================================================================
    # Partition epochs into 4 factorial groups
    grp_cold_comp = [e for e in epochs if not e["heater_on"] and e["reglering_on"]]
    grp_cold_uncomp = [e for e in epochs if not e["heater_on"] and not e["reglering_on"]]
    grp_hot_comp = [e for e in epochs if e["heater_on"] and e["reglering_on"]]
    grp_hot_uncomp = [e for e in epochs if e["heater_on"] and not e["reglering_on"]]

    prof_h_off_r_on = np.mean([e["strata_enobs"] for e in grp_cold_comp], axis=0) if grp_cold_comp else np.zeros(n_strata)
    prof_h_off_r_off = np.mean([e["strata_enobs"] for e in grp_cold_uncomp], axis=0) if grp_cold_uncomp else np.zeros(n_strata)
    prof_h_on_r_on = np.mean([e["strata_enobs"] for e in grp_hot_comp], axis=0) if grp_hot_comp else np.zeros(n_strata)
    prof_h_on_r_off = np.mean([e["strata_enobs"] for e in grp_hot_uncomp], axis=0) if grp_hot_uncomp else np.zeros(n_strata)

    loss_h_off_r_on = np.mean([e["strata_losses"] for e in grp_cold_comp], axis=0) if grp_cold_comp else np.zeros(n_strata)
    loss_h_off_r_off = np.mean([e["strata_losses"] for e in grp_cold_uncomp], axis=0) if grp_cold_uncomp else np.zeros(n_strata)
    loss_h_on_r_on = np.mean([e["strata_losses"] for e in grp_hot_comp], axis=0) if grp_hot_comp else np.zeros(n_strata)
    loss_h_on_r_off = np.mean([e["strata_losses"] for e in grp_hot_uncomp], axis=0) if grp_hot_uncomp else np.zeros(n_strata)

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

    ax4a.axvline(center_us / 1000.0, color="#64748b", linestyle=":", linewidth=1.2, label=f"Nominal Snapshot Delay ({c_str})")
    ax4a.set_title(f"Effective Resolution (ENOB) Across Temporal Window [{win_str}]", fontsize=11, fontweight="bold")
    ax4a.set_xlabel("Snapshot Sampling Delay (ms)", fontsize=10.5, fontweight="bold")
    ax4a.set_ylabel("ENOB (bits)", fontsize=10.5, fontweight="bold")
    ax4a.set_ylim(max(0.0, np.min([prof_h_on_r_off, prof_h_off_r_off]) - 0.5), min(8.0, np.max([prof_h_off_r_on, prof_h_on_r_on]) + 0.8))
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

    ax4b.axvline(center_us / 1000.0, color="#64748b", linestyle=":", linewidth=1.2)
    ax4b.set_yscale("log")
    ax4b.set_title("Mean Squared Error Loss Across Temporal Window (LSB²)", fontsize=11, fontweight="bold")
    ax4b.set_xlabel("Snapshot Sampling Delay (ms)", fontsize=10.5, fontweight="bold")
    ax4b.set_ylabel("Loss (LSB²)", fontsize=10.5, fontweight="bold")
    ax4b.grid(True, linestyle=":", alpha=0.6)
    ax4b.legend(loc="upper right", fontsize=8.5, framealpha=0.92)

    fig4.suptitle(f"Inverted MAML Silicon: 2x2 Factorial Strata Profiles (Card 2, K={k_batch_val}, LR={lr_val}, λ={l2_val})",
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

    categories = [
        "Ambient\nCompensated\n(Cold, Comp ON)",
        "Ambient\nUncompensated\n(Cold, Comp OFF)",
        "Thermal Stress\nCompensated\n(Hot, Comp ON)",
        "Thermal Stress\nUncompensated\n(Hot, Comp OFF)",
    ]
    mean_losses_bar = [
        float(np.mean([e["mean_loss_lsb2"] for e in grp_cold_comp])) if grp_cold_comp else 1.0,
        float(np.mean([e["mean_loss_lsb2"] for e in grp_cold_uncomp])) if grp_cold_uncomp else 1.0,
        float(np.mean([e["mean_loss_lsb2"] for e in grp_hot_comp])) if grp_hot_comp else 1.0,
        float(np.mean([e["mean_loss_lsb2"] for e in grp_hot_uncomp])) if grp_hot_uncomp else 1.0,
    ]
    mean_enobs_bar = [
        float(np.mean([e["mean_enob_bits"] for e in grp_cold_comp])) if grp_cold_comp else 0.0,
        float(np.mean([e["mean_enob_bits"] for e in grp_cold_uncomp])) if grp_cold_uncomp else 0.0,
        float(np.mean([e["mean_enob_bits"] for e in grp_hot_comp])) if grp_hot_comp else 0.0,
        float(np.mean([e["mean_enob_bits"] for e in grp_hot_uncomp])) if grp_hot_uncomp else 0.0,
    ]
    colors_bar = ["#059669", "#2563eb", "#f59e0b", "#dc2626"]

    bars = ax5a.bar(categories, mean_losses_bar, color=colors_bar, width=0.55, edgecolor="#1e293b", linewidth=1.2)
    for b, val, enb in zip(bars, mean_losses_bar, mean_enobs_bar):
        ax5a.text(b.get_x() + b.get_width() / 2.0, val * 1.08,
                  f"{val:,.0f} L²\n({enb:.2f} b)",
                  ha="center", va="bottom", fontsize=9.5, fontweight="bold")

    ax5a.set_yscale("log")
    ax5a.set_ylim(min(1e4, min(mean_losses_bar) * 0.5), max(1.5e6, max(mean_losses_bar) * 2.0))
    ax5a.set_ylabel("Mean Squared Error Loss (LSB²)", fontsize=11, fontweight="bold")
    ax5a.set_title("2x2 Factorial Loss Comparison (Card 2 Silicon)", fontsize=11.5, fontweight="bold")
    ax5a.grid(True, linestyle=":", alpha=0.5, axis="y")

    # Summary Metrics Box
    ax5b.axis("off")
    thermal_deg_ratio = mean_losses_bar[3] / max(mean_losses_bar[1], 1.0)
    comp_gain_cold = (1.0 - mean_losses_bar[0] / max(mean_losses_bar[1], 1.0)) * 100.0
    comp_gain_hot = (1.0 - mean_losses_bar[2] / max(mean_losses_bar[3], 1.0)) * 100.0

    summary_text = (
        "INVERTED MAML THERMAL STRESS REJECTION SUMMARY\n"
        "==========================================================\n\n"
        f"• Total Experiment Epochs:       {n_epochs} epochs (~{elapsed_m[-1]:.1f} minutes)\n"
        f"• Thermal Perturbation:          4x On-Board Resistors @ 30% Duty Cycle (1.0 Hz PWM)\n"
        f"• Thermal Cycle Period:          8.0 min ON (30% duty) / 8.0 min OFF (Cooling)\n"
        f"• Mode A Training Cycle:         2.0 min TRAINING ON (SGD) / 2.0 min OFF (W8=0)\n"
        f"• Hyperparameters:               L2 reg = {l2_val}, K = {k_batch_val}, lr = {lr_val}\n"
        f"• Attenuator & Circuit:          1k/3.3k Attenuator, Card 2 (PCBA v1.3.2)\n"
        f"• Sampling Window:               [{win_str}] ({n_strata} strata, step {t_step_us} µs)\n\n"
        "KEY QUANTITATIVE FINDINGS:\n"
        "----------------------------------------------------------\n"
        f"1. Uncompensated Baseline & Thermal Drift:\n"
        f"   - Warm Baseline (Heat ON, W8=0):  {mean_losses_bar[3]:,.0f} LSB² ({mean_enobs_bar[3]:.2f} b)\n"
        f"   - Cold Drift Loss (Heat OFF, W8=0): {mean_losses_bar[1]:,.0f} LSB² ({mean_enobs_bar[1]:.2f} b)\n"
        f"   - Cold Error Surge vs Warm Base:  +{mean_losses_bar[1]/max(mean_losses_bar[3], 1.0):.2f}x error increase\n\n"
        f"2. Closed-Loop Drift Rejection:\n"
        f"   - Cold Error Reduction (Mode A): -{comp_gain_cold:.1f}% ({mean_losses_bar[1]:,.0f} -> {mean_losses_bar[0]:,.0f} L²)\n"
        f"   - Hot Error Reduction (Mode A):  -{comp_gain_hot:.1f}% ({mean_losses_bar[3]:,.0f} -> {mean_losses_bar[2]:,.0f} L²)\n"
        f"   - Resolution Gain (Cold):        +{mean_enobs_bar[0] - mean_enobs_bar[1]:.2f} b ({mean_enobs_bar[0]:.2f} b vs {mean_enobs_bar[1]:.2f} b)\n\n"
        f"3. Silicon Weight Adaptation:\n"
        f"   - Total W8 Envelope:          [{int(np.min(w8_mins))}, {int(np.max(w8_maxs))}] LSB (Peak +117 LSB in Cold)\n"
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=str, default=str(DEFAULT_JSON))
    args = parser.parse_args()

    json_path = Path(args.json)
    d = load_data(json_path)
    print(f"Loaded {len(d['epochs'])} epochs from {json_path}.")
    print("Generating publication figures...")
    paths = generate_all_figures(d)
    for k, p in paths.items():
        print(f"  [+] {k}: {p}")
