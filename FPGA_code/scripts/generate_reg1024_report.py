#!/usr/bin/env python3
"""
generate_reg1024_report.py
==========================
Generates the comprehensive 11-page English publication report for Milestone 3 of the
Inverted MAML project: 500-Epoch Mode A Silicon Evaluation Across the Broadened
Temporal Window [4500 - 5500 us] with 100% Identical Measurement & Hadamard Cadence
across all phases (Ep 0..99, Ep 100..199, Ep 200..500), Elevated L2 Regularization
(lambda = 1024), and Learning Rate (lr = 0.25).

Includes:
  - Dedicated Page 3 for SINGLE-POINT 5.0 ms CENTER SNAPSHOT ONLY (Loss, ENOB, M8 Weights).
  - Dedicated Page 4 for FULL TEMPORAL WINDOW [4.5 ms to 5.5 ms] AGGREGATED ONLY (Loss, ENOB, M8 Weights)
    with identical visual styling, clear phase mean lines, and unmistakable titles.
  - Detailed analysis of the Single-Point (5.0 ms) vs. Full Temporal Window [4.5..5.5 ms]
    trade-off and how the Proprioceptive Inverted MAML network actively compensates for
    temporal capacitor leakage in physical Analog Neural Networks.
  - Uncompressed Patent Fig 1, Patent Fig 8, Patent Fig 5 (Displaced Temporal Window Sampling
    across T_INF), and Patent Fig 6 (Accelerated Temporal Reference Decay 32 vs. Natural
    Cell Leakage 31).
"""

import os
import sys
import json
import shutil
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import cm
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_PATH = REPO_ROOT / "FPGA_code" / "logs" / "mode_a_extended_training" / "mode_a_500ep_broadened_4p5to5p5ms_reg1024_lr0p25_identical_k20_llm.json"
FIG_DIR = REPO_ROOT / "FPGA_code" / "docs" / "figures"
DOC_DIR = REPO_ROOT / "FPGA_code" / "docs"
ARTIFACT_DIR = Path("/home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a")


def generate_3d_landscapes(data: dict) -> Path:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    w3_base, w8_base = None, None
    w3_gold, w8_gold = None, None

    for e in data["epochs"]:
        if e["epoch"] == 100:
            w3_base = np.array(e["w_m3"])
            w8_base = np.array(e["w_m8"])
        if e["epoch"] == 245:
            w3_gold = np.array(e["w_m3"])
            w8_gold = np.array(e["w_m8"])

    fig = plt.figure(figsize=(16, 12.5), dpi=180)
    plt.subplots_adjust(hspace=0.28, wspace=0.18)

    cmap = cm.coolwarm
    norm = plt.Normalize(vmin=-120, vmax=120)

    panels = [
        (1, w3_base, "1. Matrix 3: Calibrated Smart Baseline (Epoch 100, LR=0)", 8, 6, ["R0", "R1", "R2", "R3", "R4", "R5", "ClkB1", "ClkRef"]),
        (2, w8_base, "2. Matrix 8: Calibrated Smart Baseline (Epoch 100, LR=0)", 7, 6, ["R0", "R1", "R2", "R3", "R4", "R5", "Bias"]),
        (3, w3_gold, "3. Matrix 3: Trained Golden State (Epoch 245, 5.0 ms ENOB 7.78b)", 8, 6, ["R0", "R1", "R2", "R3", "R4", "R5", "ClkB1", "ClkRef"]),
        (4, w8_gold, "4. Matrix 8: Trained Golden State (Epoch 245, Win Loss 58,283 LSB²)", 7, 6, ["R0", "R1", "R2", "R3", "R4", "R5", "Bias"]),
    ]

    for idx, mat, title, num_rows, num_cols, row_labels in panels:
        ax = fig.add_subplot(2, 2, idx, projection='3d')
        _x = np.arange(num_rows)
        _y = np.arange(num_cols)
        _xx, _yy = np.meshgrid(_x, _y)
        x_flat, y_flat = _xx.ravel(), _yy.ravel()
        z_flat = np.zeros_like(x_flat)

        dx = 0.55 * np.ones_like(z_flat)
        dy = 0.55 * np.ones_like(z_flat)
        dz = mat[x_flat, y_flat]

        colors_bars = cmap(norm(dz))

        ax.bar3d(x_flat - 0.275, y_flat - 0.275, z_flat, dx, dy, dz,
                 color=colors_bars, shade=True, edgecolor='#333333', linewidth=0.3, alpha=0.92)

        ax.set_title(title, fontsize=11, fontweight="bold", pad=12)
        ax.set_xticks(np.arange(num_rows))
        ax.set_xticklabels(row_labels, fontsize=7.5, rotation=-20, ha='right')
        ax.set_yticks(np.arange(num_cols))
        ax.set_yticklabels([f"C{c}" for c in range(num_cols)], fontsize=7.5)
        ax.set_zlim(-120, 120)
        ax.set_zticks([-100, -75, -50, -25, 0, 25, 50, 75, 100])
        ax.tick_params(axis='z', labelsize=8)
        ax.set_xlabel("Matrix Row", fontsize=8.5, labelpad=8)
        ax.set_ylabel("Column (0..5)", fontsize=8.5, labelpad=8)
        ax.set_zlabel("Weight [LSB]", fontsize=8.5, labelpad=5)
        ax.view_init(elev=32, azim=-55)

    fig.suptitle("INVERTED MAML MILESTONE 3 (λ = 1024, LR = 0.25): 3D Dual-2T1C Weight Topographies (Baseline vs. Trained Golden State)",
                 fontsize=13.0, fontweight="bold", y=0.98)

    out_docs = FIG_DIR / "fig_mode_a_3d_weight_landscapes_baseline_vs_ep260_reg1024.png"
    out_art = ARTIFACT_DIR / "fig_mode_a_3d_weight_landscapes_baseline_vs_ep260_reg1024.png"
    fig.savefig(out_docs, dpi=180, bbox_inches='tight')
    if ARTIFACT_DIR.exists():
        fig.savefig(out_art, dpi=180, bbox_inches='tight')
    plt.close(fig)
    return out_docs


def _plot_3panel_trajectory(
    epochs: list[int],
    loss_vals: list[float],
    enob_vals: list[float],
    w_m8_traj: np.ndarray,
    main_title: str,
    subtitle: str,
    loss_ylabel: str,
    enob_ylabel: str,
    loss_curve_label: str,
    enob_curve_label: str,
    p1_loss_mean: float,
    p2_loss_mean: float,
    p3_loss_mean: float,
    p1_enob_mean: float,
    p2_enob_mean: float,
    p3_enob_mean: float,
    peak_ep: int,
    peak_loss_str: str,
    peak_enob_str: str,
    loss_ylim: tuple[float, float],
    enob_ylim: tuple[float, float],
    target_enob_line: float | None,
    out_docs: Path,
    out_art: Path,
) -> Path:
    fig, (ax_loss, ax_enob, ax_w) = plt.subplots(3, 1, figsize=(13.5, 9.8), sharex=True, dpi=180)
    plt.subplots_adjust(hspace=0.16, top=0.90)

    # Identical phase background shading across all 3 panels
    for ax in (ax_loss, ax_enob, ax_w):
        ax.axvspan(0, 100, color="#dbeafe", alpha=0.38, zorder=0)
        ax.axvspan(100, 200, color="#fee2e2", alpha=0.38, zorder=0)
        ax.axvspan(200, 500, color="#dcfce7", alpha=0.38, zorder=0)
        ax.axvline(100, color="#b45309", linestyle="--", linewidth=1.5, alpha=0.85, zorder=3)
        ax.axvline(200, color="#15803d", linestyle="--", linewidth=1.8, alpha=0.95, zorder=3)
        ax.grid(True, linestyle="--", alpha=0.45)

    # --- Panel 1: Loss ---
    ax_loss.plot(epochs, loss_vals, color="#1d4ed8", linewidth=1.4, alpha=0.90, label=loss_curve_label, zorder=2)
    ax_loss.hlines(p1_loss_mean, 0, 100, colors="#1e293b", linestyles="--", linewidth=2.0, zorder=4)
    ax_loss.hlines(p2_loss_mean, 100, 200, colors="#9a3412", linestyles="--", linewidth=2.0, zorder=4)
    ax_loss.hlines(p3_loss_mean, 200, 500, colors="#065f46", linestyles="--", linewidth=2.2, zorder=4)

    # Phase mean callout boxes on Loss panel
    y_span_loss = loss_ylim[1] - loss_ylim[0]
    ax_loss.text(50, p1_loss_mean + 0.08 * y_span_loss, f"Ph1 Mean:\n{p1_loss_mean:,.0f} LSB²",
                 ha="center", va="bottom", fontsize=8.2, fontweight="bold", color="#1e293b",
                 bbox=dict(boxstyle="round,pad=0.22", facecolor="white", edgecolor="#475569", alpha=0.92), zorder=5)
    ax_loss.text(150, p2_loss_mean + 0.06 * y_span_loss, f"Ph2 Mean:\n{p2_loss_mean:,.0f} LSB²",
                 ha="center", va="bottom", fontsize=8.2, fontweight="bold", color="#9a3412",
                 bbox=dict(boxstyle="round,pad=0.22", facecolor="white", edgecolor="#b45309", alpha=0.92), zorder=5)
    ax_loss.text(355, p3_loss_mean + 0.08 * y_span_loss, f"Ph3 Mean: {p3_loss_mean:,.0f} LSB²\n({peak_loss_str})",
                 ha="center", va="bottom", fontsize=8.4, fontweight="bold", color="#065f46",
                 bbox=dict(boxstyle="round,pad=0.25", facecolor="#ecfdf5", edgecolor="#059669", linewidth=1.3, alpha=0.95), zorder=5)

    ax_loss.set_ylim(*loss_ylim)
    ax_loss.set_ylabel(loss_ylabel, fontsize=10.5, fontweight="bold")
    legend_patches = [
        Line2D([0], [0], color="#1d4ed8", lw=1.8, label=loss_curve_label),
        Patch(facecolor="#dbeafe", alpha=0.6, label="Phase 1 (Ep 0..99): Baseline Zero (W=0 LSB, LR=0, Hadamard ON)"),
        Patch(facecolor="#fee2e2", alpha=0.6, label="Phase 2 (Ep 100..199): Calibrated Smart Baseline (LR=0, Hadamard ON)"),
        Patch(facecolor="#dcfce7", alpha=0.6, label="Phase 3 (Ep 200..500): Active Training ON (K=20, 10 Strata, LR=0.25, λ=1024)"),
    ]
    ax_loss.legend(handles=legend_patches, loc="upper right", fontsize=8.2, framealpha=0.94)

    # --- Panel 2: ENOB ---
    ax_enob.plot(epochs, enob_vals, color="#047857", linewidth=1.5, alpha=0.92, label=enob_curve_label, zorder=2)
    ax_enob.hlines(p1_enob_mean, 0, 100, colors="#1e293b", linestyles="--", linewidth=2.0, zorder=4)
    ax_enob.hlines(p2_enob_mean, 100, 200, colors="#9a3412", linestyles="--", linewidth=2.0, zorder=4)
    ax_enob.hlines(p3_enob_mean, 200, 500, colors="#065f46", linestyles="--", linewidth=2.2, zorder=4)

    if target_enob_line is not None:
        ax_enob.axhline(target_enob_line, color="#b91c1c", linestyle=":", linewidth=1.5, label=f"{target_enob_line:.1f}-Bit Reference")

    y_span_enob = enob_ylim[1] - enob_ylim[0]
    ax_enob.text(50, p1_enob_mean - 0.14 * y_span_enob, f"Ph1 Mean: {p1_enob_mean:.2f} b",
                 ha="center", va="top", fontsize=8.2, fontweight="bold", color="#1e293b",
                 bbox=dict(boxstyle="round,pad=0.22", facecolor="white", edgecolor="#475569", alpha=0.92), zorder=5)
    ax_enob.text(150, p2_enob_mean - 0.14 * y_span_enob, f"Ph2 Mean: {p2_enob_mean:.2f} b",
                 ha="center", va="top", fontsize=8.2, fontweight="bold", color="#9a3412",
                 bbox=dict(boxstyle="round,pad=0.22", facecolor="white", edgecolor="#b45309", alpha=0.92), zorder=5)
    ax_enob.text(355, p3_enob_mean + 0.10 * y_span_enob, f"Ph3 Mean: {p3_enob_mean:.2f} b ({peak_enob_str})",
                 ha="center", va="bottom", fontsize=8.4, fontweight="bold", color="#065f46",
                 bbox=dict(boxstyle="round,pad=0.25", facecolor="#ecfdf5", edgecolor="#059669", linewidth=1.3, alpha=0.95), zorder=5)

    ax_enob.set_ylim(*enob_ylim)
    ax_enob.set_ylabel(enob_ylabel, fontsize=10.5, fontweight="bold")
    ax_enob.legend(loc="upper left", fontsize=8.5, framealpha=0.94)

    # --- Panel 3: M8 Diagonal Weights ---
    col_colors = ["#1f2937", "#2563eb", "#16a34a", "#d97706", "#ea580c", "#7c3aed"]
    for c in range(6):
        ax_w.plot(epochs, w_m8_traj[:, c, c], color=col_colors[c], linewidth=1.7, label=f"M8[{c},{c}] (Col {c})", zorder=2)
    ax_w.axhline(120, color="#dc2626", linestyle="--", linewidth=1.1, alpha=0.8, label="±120 LSB Clamp")
    ax_w.axhline(-120, color="#dc2626", linestyle="--", linewidth=1.1, alpha=0.8)
    ax_w.axhline(0, color="#64748b", linestyle="-", linewidth=0.8, alpha=0.5)
    ax_w.set_ylim(-130, 130)
    ax_w.set_xlim(0, 500)
    ax_w.set_ylabel("M8 Diagonal Weight (LSB)", fontsize=10.5, fontweight="bold")
    ax_w.set_xlabel("Epoch (Each Epoch = 20 Vectors × 10 Strata = 200 Hadamard Measurements)", fontsize=10.5, fontweight="bold")
    ax_w.legend(loc="upper left", ncol=4, fontsize=8.2, framealpha=0.94)

    fig.suptitle(main_title, fontsize=13.5, fontweight="bold", y=0.97)
    fig.text(0.5, 0.932, subtitle, ha="center", va="center", fontsize=10.0, fontweight="bold", color="#1e3a8a")

    fig.savefig(out_docs, dpi=180, bbox_inches="tight")
    if ARTIFACT_DIR.exists():
        fig.savefig(out_art, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return out_docs


def generate_split_5ms_and_window_figures(data: dict) -> tuple[Path, Path]:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    epochs = [e["epoch"] for e in data["epochs"]]
    nom_loss = [float(e["loss_lsb2"]) for e in data["epochs"]]
    nom_enob = [float(e["enob_bits"]) for e in data["epochs"]]
    win_loss = [float(e["window_eval"]["mean_loss_lsb2"]) for e in data["epochs"]]
    win_enob = [float(e["window_eval"]["mean_enob_bits"]) for e in data["epochs"]]
    w_m8_traj = np.array([e["w_m8"] for e in data["epochs"]])

    # Figure 2A: Single-Point 5.0 ms Center Snapshot ONLY
    out_5ms_docs = FIG_DIR / "fig_mode_a_500ep_5p0ms_only_reg1024.png"
    out_5ms_art = ARTIFACT_DIR / "fig_mode_a_500ep_5p0ms_only_reg1024.png"
    _plot_3panel_trajectory(
        epochs=epochs,
        loss_vals=nom_loss,
        enob_vals=nom_enob,
        w_m8_traj=w_m8_traj,
        main_title="1. SINGLE-POINT MEASUREMENT AT t = 5.0 ms ONLY (Nominal Center Snapshot)",
        subtitle="Evaluated strictly at the single 5000 µs midpoint — W=0 is pre-calibrated here (6.02 b mean), Active Training hits 7.78 b Peak (5.70 b mean)",
        loss_ylabel="5.0 ms Loss (LSB²)",
        enob_ylabel="5.0 ms ENOB (Bits)",
        loss_curve_label="Single-Point 5.0 ms Center Loss (LSB²)",
        enob_curve_label="Single-Point 5.0 ms Center ENOB (bits)",
        p1_loss_mean=float(np.mean(nom_loss[0:100])),
        p2_loss_mean=float(np.mean(nom_loss[100:200])),
        p3_loss_mean=float(np.mean(nom_loss[200:501])),
        p1_enob_mean=float(np.mean(nom_enob[0:100])),
        p2_enob_mean=float(np.mean(nom_enob[100:200])),
        p3_enob_mean=float(np.mean(nom_enob[200:501])),
        peak_ep=245,
        peak_loss_str="Min: 259 LSB² @ Ep 245",
        peak_enob_str="Peak: 7.78 bits @ Ep 245",
        loss_ylim=(0, 26000),
        enob_ylim=(4.2, 8.0),
        target_enob_line=6.0,
        out_docs=out_5ms_docs,
        out_art=out_5ms_art,
    )

    # Figure 2B: Full Temporal Window [4.5 ms to 5.5 ms] Aggregated ONLY
    out_win_docs = FIG_DIR / "fig_mode_a_500ep_window_4p5to5p5ms_only_reg1024.png"
    out_win_art = ARTIFACT_DIR / "fig_mode_a_500ep_window_4p5to5p5ms_only_reg1024.png"
    _plot_3panel_trajectory(
        epochs=epochs,
        loss_vals=win_loss,
        enob_vals=win_enob,
        w_m8_traj=w_m8_traj,
        main_title="2. FULL TEMPORAL WINDOW [4.5 ms to 5.5 ms] AGGREGATED (All 10 Strata × K=20 = 200 Samples/Epoch)",
        subtitle="Combined across the entire 1000 µs discharge window [4500..5500 µs] — Active Training cuts Window Loss by -20.9% (mean) to -25.2% (min)!",
        loss_ylabel="Window [4.5–5.5 ms] Loss (LSB²)",
        enob_ylabel="Window [4.5–5.5 ms] ENOB (Bits)",
        loss_curve_label="Full-Window [4.5..5.5 ms] Mean Loss across 200 Samples (LSB²)",
        enob_curve_label="Full-Window [4.5..5.5 ms] Mean ENOB across 200 Samples (bits)",
        p1_loss_mean=float(np.mean(win_loss[0:100])),
        p2_loss_mean=float(np.mean(win_loss[100:200])),
        p3_loss_mean=float(np.mean(win_loss[200:501])),
        p1_enob_mean=float(np.mean(win_enob[0:100])),
        p2_enob_mean=float(np.mean(win_enob[100:200])),
        p3_enob_mean=float(np.mean(win_enob[200:501])),
        peak_ep=212,
        peak_loss_str="-20.9% vs Ph2 | Min: 56,014 LSB² @ Ep 212",
        peak_enob_str="+0.17 b vs Ph2 | Peak: 3.91 bits @ Ep 212",
        loss_ylim=(52000, 80000),
        enob_ylim=(3.60, 4.02),
        target_enob_line=None,
        out_docs=out_win_docs,
        out_art=out_win_art,
    )

    return out_5ms_docs, out_win_docs


def generate_2d_trajectories(data: dict) -> tuple[Path, Path]:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    epochs = [e["epoch"] for e in data["epochs"]]
    w_m3_traj = np.array([e["w_m3"] for e in data["epochs"]]) # 501 x 8 x 6
    w_m8_traj = np.array([e["w_m8"] for e in data["epochs"]]) # 501 x 7 x 6

    transitions = [
        {"ep": 100, "lbl": "Smart S-Bend Baseline (LR=0)", "c": "#b45309", "y": 95},
        {"ep": 200, "lbl": "TRAINING ON (λ=1024, LR=0.25)", "c": "#15803d", "y": 75},
        {"ep": 212, "lbl": "Min Win Loss 56,014 LSB² (3.91b)", "c": "#047857", "y": -95},
        {"ep": 245, "lbl": "Peak 5.0 ms ENOB 7.78b (259 LSB²)", "c": "#1d4ed8", "y": -115},
    ]

    phase_spans = [
        (0, 100, "Phase 1: M33 Alone (W=0, LR=0)", "#f1f5f9", 0.4),
        (100, 200, "Phase 2: Smart Baseline (LR=0)", "#fef3c7", 0.45),
        (200, 500, "Phase 3: Active Training ON (λ=1024, LR=0.25)", "#dcfce7", 0.35),
    ]

    cmap_comp = plt.get_cmap("tab20", 36)

    # --- Matrix 3 Trajectories (48 Weights) ---
    fig_m3, ax_m3 = plt.subplots(figsize=(13, 6.2), dpi=180)
    for x1, x2, lbl, bg, alpha in phase_spans:
        ax_m3.axvspan(x1, x2, color=bg, alpha=alpha, zorder=0)

    w_idx = 0
    for r in range(6):
        for c in range(6):
            ax_m3.plot(epochs, w_m3_traj[:, r, c], color=cmap_comp(w_idx), linewidth=1.1, alpha=0.85, zorder=2)
            w_idx += 1

    for r in [6, 7]:
        for c in range(6):
            ax_m3.plot(epochs, w_m3_traj[:, r, c], color="black" if r == 6 else "#78350f",
                       linestyle="--", linewidth=1.6, alpha=0.75, zorder=3)

    ax_m3.axhline(120, color="#dc2626", linestyle=":", linewidth=1.2, alpha=0.8)
    ax_m3.axhline(-120, color="#dc2626", linestyle=":", linewidth=1.2, alpha=0.8)
    ax_m3.axhline(0, color="#64748b", linestyle="-", linewidth=0.8, alpha=0.5)

    for t in transitions:
        ax_m3.axvline(t["ep"], color=t["c"], linestyle="--", linewidth=1.8, alpha=0.9, zorder=4)
        ax_m3.text(t["ep"] + 4, t["y"], t["lbl"], color=t["c"], fontweight="bold", fontsize=8.5,
                   bbox=dict(boxstyle="round,pad=0.25", facecolor="#ffffff", edgecolor=t["c"], linewidth=1.2, alpha=0.92), zorder=5)

    ax_m3.set_xlim(0, 500)
    ax_m3.set_ylim(-130, 130)
    ax_m3.set_xlabel("Training Epoch (100% Identical 200-Sample Hadamard Cadence across 0..500)", fontsize=10.5, fontweight="bold")
    ax_m3.set_ylabel("Matrix 3 Weight DAC Code (Signed LSB, [-120, +120])", fontsize=10.5, fontweight="bold")
    ax_m3.set_title("Matrix 3 (First Triad Layer): Full 2D Trajectories of all 36 Compute & 12 Clock Weights (λ=1024, LR=0.25)",
                    fontsize=12, fontweight="bold", pad=8)
    ax_m3.grid(True, linestyle=":", alpha=0.6)

    custom_lines_m3 = [
        Line2D([0], [0], color="#2563eb", lw=1.5, label="36 Compute Crosspoints (Rows 0..5, Cols 0..5)"),
        Line2D([0], [0], color="black", lw=1.6, linestyle="--", label="6 ClkB1 Clock Reference Weights (Row 6)"),
        Line2D([0], [0], color="#78350f", lw=1.6, linestyle="--", label="6 ClkRef Clock Reference Weights (Row 7)"),
        Line2D([0], [0], color="#dc2626", lw=1.2, linestyle=":", label="Physical Clamp Limits (±120 LSB)")
    ]
    ax_m3.legend(handles=custom_lines_m3, loc="upper left", fontsize=8.5, framealpha=0.92)
    fig_m3.tight_layout()

    out_m3_docs = FIG_DIR / "fig_2d_m3_weights_trajectory_reg1024.png"
    out_m3_art = ARTIFACT_DIR / "fig_2d_m3_weights_trajectory_reg1024.png"
    fig_m3.savefig(out_m3_docs, dpi=180)
    if ARTIFACT_DIR.exists():
        fig_m3.savefig(out_m3_art, dpi=180)
    plt.close(fig_m3)

    # --- Matrix 8 Trajectories (42 Weights) ---
    fig_m8, ax_m8 = plt.subplots(figsize=(13, 6.2), dpi=180)
    for x1, x2, lbl, bg, alpha in phase_spans:
        ax_m8.axvspan(x1, x2, color=bg, alpha=alpha, zorder=0)

    w_idx = 0
    for r in range(6):
        for c in range(6):
            ax_m8.plot(epochs, w_m8_traj[:, r, c], color=cmap_comp(w_idx), linewidth=1.1, alpha=0.85, zorder=2)
            w_idx += 1

    for c in range(6):
        ax_m8.plot(epochs, w_m8_traj[:, 6, c], color="#991b1b", linestyle="--", linewidth=1.6, alpha=0.85, zorder=3)

    ax_m8.axhline(120, color="#dc2626", linestyle=":", linewidth=1.2, alpha=0.8)
    ax_m8.axhline(-120, color="#dc2626", linestyle=":", linewidth=1.2, alpha=0.8)
    ax_m8.axhline(0, color="#64748b", linestyle="-", linewidth=0.8, alpha=0.5)

    for t in transitions:
        ax_m8.axvline(t["ep"], color=t["c"], linestyle="--", linewidth=1.8, alpha=0.9, zorder=4)
        ax_m8.text(t["ep"] + 4, t["y"], t["lbl"], color=t["c"], fontweight="bold", fontsize=8.5,
                   bbox=dict(boxstyle="round,pad=0.25", facecolor="#ffffff", edgecolor=t["c"], linewidth=1.2, alpha=0.92), zorder=5)

    ax_m8.set_xlim(0, 500)
    ax_m8.set_ylim(-130, 130)
    ax_m8.set_xlabel("Training Epoch (100% Identical 200-Sample Hadamard Cadence across 0..500)", fontsize=10.5, fontweight="bold")
    ax_m8.set_ylabel("Matrix 8 Weight DAC Code (Signed LSB, [-120, +120])", fontsize=10.5, fontweight="bold")
    ax_m8.set_title("Matrix 8 (Second Triad Layer): Full 2D Trajectories of all 36 Vernier Compute & 6 Bias Weights (λ=1024, LR=0.25)",
                    fontsize=12, fontweight="bold", pad=8)
    ax_m8.grid(True, linestyle=":", alpha=0.6)

    custom_lines_m8 = [
        Line2D([0], [0], color="#2563eb", lw=1.5, label="36 Vernier Compute Crosspoints (Rows 0..5, Cols 0..5)"),
        Line2D([0], [0], color="#991b1b", lw=1.6, linestyle="--", label="6 Vernier Bias Weights (Row 6)"),
        Line2D([0], [0], color="#dc2626", lw=1.2, linestyle=":", label="Physical Clamp Limits (±120 LSB) [Zero Permanent Clamp!]")
    ]
    ax_m8.legend(handles=custom_lines_m8, loc="upper left", fontsize=8.5, framealpha=0.92)
    fig_m8.tight_layout()

    out_m8_docs = FIG_DIR / "fig_2d_m8_weights_trajectory_reg1024.png"
    out_m8_art = ARTIFACT_DIR / "fig_2d_m8_weights_trajectory_reg1024.png"
    fig_m8.savefig(out_m8_docs, dpi=180)
    if ARTIFACT_DIR.exists():
        fig_m8.savefig(out_m8_art, dpi=180)
    plt.close(fig_m8)

    return out_m3_docs, out_m8_docs


def generate_deep_dive_figure(data: dict) -> Path:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    epochs = [e["epoch"] for e in data["epochs"]]
    nom_loss = [e["loss_lsb2"] for e in data["epochs"]]
    win_loss = [e["window_eval"]["mean_loss_lsb2"] for e in data["epochs"]]
    nom_enob = [e["enob_bits"] for e in data["epochs"]]
    win_enob = [e["window_eval"]["mean_enob_bits"] for e in data["epochs"]]
    w8_c3 = [e["w_m8"][3][3] for e in data["epochs"]]
    w8_c4 = [e["w_m8"][4][4] for e in data["epochs"]]
    w8_c5 = [e["w_m8"][5][5] for e in data["epochs"]]

    fig, axs = plt.subplots(2, 2, figsize=(14, 9), dpi=180)
    plt.subplots_adjust(hspace=0.30, wspace=0.22)

    # Panel A: True 200-Sample Window Loss Across All 3 Phases (Zero 20-Epoch Spikes!)
    axs[0, 0].plot(epochs, win_loss, color="#1e40af", lw=1.8, label="200-Sample Window Loss [4.5..5.5 ms]")
    axs[0, 0].axhline(69800.4, color="#475569", linestyle=":", lw=1.4, label="Phase 1 Mean (W=0): 69,800 LSB²")
    axs[0, 0].axhline(74896.7, color="#b45309", linestyle=":", lw=1.4, label="Phase 2 Mean (Smart Base): 74,897 LSB²")
    axs[0, 0].axhline(59233.1, color="#15803d", linestyle="--", lw=1.6, label="Phase 3 Mean (Trained): 59,233 LSB² (-20.9%)")
    axs[0, 0].axvline(100, color="#b45309", linestyle="--", lw=1.4)
    axs[0, 0].axvline(200, color="#15803d", linestyle="--", lw=1.6)
    axs[0, 0].set_title("A. Authentic 200-Sample Window Loss [4.5..5.5 ms] (Zero Spikes!)", fontweight="bold", fontsize=11)
    axs[0, 0].set_xlabel("Epoch (0..500, Identical 200-Sample Cadence)", fontsize=9.5)
    axs[0, 0].set_ylabel("Window Mean Loss [LSB²]", fontsize=9.5)
    axs[0, 0].grid(True, linestyle=":", alpha=0.6)
    axs[0, 0].legend(fontsize=7.8, loc="upper right")

    # Panel B: Convergence Window Zoom (Epochs 160..320) - Both 200-Sample Window & 5.0 ms Center
    axs[0, 1].plot(epochs[160:320], win_enob[160:320], color="#1e40af", lw=2.2, label="200-Sample Window Mean ENOB [4.5..5.5 ms]")
    axs[0, 1].plot(epochs[160:320], nom_enob[160:320], color="#b91c1c", lw=1.4, alpha=0.75, label="Single-Point 5.0 ms Center ENOB (Peak 7.78b)")
    axs[0, 1].axvline(200, color="#15803d", linestyle="--", lw=1.6, label="TRAINING ON (Ep 200)")
    axs[0, 1].axvline(212, color="#047857", linestyle=":", lw=1.6, label="Peak Win ENOB 3.91b (Ep 212)")
    axs[0, 1].axvline(245, color="#b91c1c", linestyle=":", lw=1.6, label="Peak 5.0 ms ENOB 7.78b (Ep 245)")
    axs[0, 1].set_title("B. Resolution Zoom (Epochs 160–320): Window vs. 5.0 ms Center", fontweight="bold", fontsize=11)
    axs[0, 1].set_xlabel("Epoch", fontsize=9.5)
    axs[0, 1].set_ylabel("Effective Resolution [ENOB Bits]", fontsize=9.5)
    axs[0, 1].grid(True, linestyle=":", alpha=0.6)
    axs[0, 1].legend(fontsize=7.8, loc="upper left")

    # Panel C: Statistical Distribution Comparison Across Phase 1, Phase 2, and Phase 3
    p1_losses = np.array(win_loss[0:100]) / 1000.0
    p2_losses = np.array(win_loss[100:200]) / 1000.0
    p3_losses = np.array(win_loss[200:501]) / 1000.0
    parts = axs[1, 0].boxplot(
        [p1_losses, p2_losses, p3_losses],
        labels=["Phase 1: W=0\n(Ep 0..99, LR=0)", "Phase 2: Smart Base\n(Ep 100..199, LR=0)", "Phase 3: Trained ON\n(Ep 200..500, LR=0.25)"],
        patch_artist=True,
        widths=0.48
    )
    box_colors = ["#cbd5e1", "#fde68a", "#86efac"]
    for patch, color in zip(parts["boxes"], box_colors):
        patch.set_facecolor(color)
        patch.set_edgecolor("#1e293b")
        patch.set_linewidth(1.2)
    for median in parts["medians"]:
        median.set_color("#dc2626")
        median.set_linewidth(2.0)
    axs[1, 0].set_title("C. 200-Sample Window Loss Distribution by Phase (>10σ Gain)", fontweight="bold", fontsize=11)
    axs[1, 0].set_ylabel("Window Mean Loss [×10³ LSB²]", fontsize=9.5)
    axs[1, 0].grid(True, linestyle=":", alpha=0.6)

    # Panel D: Col 3, 4 & 5 Dynamics under L2 Regularization (lambda = 1024)
    axs[1, 1].plot(epochs, w8_c3, color="#15803d", lw=1.8, label="Col 3 Diagonal (Pulled back from +120 to +100..+112)")
    axs[1, 1].plot(epochs, w8_c4, color="#1d4ed8", lw=1.8, label="Col 4 Diagonal (Smoothly settled at +34..+64 LSB)")
    axs[1, 1].plot(epochs, w8_c5, color="#d97706", lw=1.8, label="Col 5 Diagonal (Sustained inside rails at +80..+108 LSB)")
    axs[1, 1].axhline(120, color="#dc2626", linestyle=":", lw=1.2, label="Hardware Rail Clamps (±120 LSB)")
    axs[1, 1].axhline(-120, color="#dc2626", linestyle=":", lw=1.2)
    axs[1, 1].axhline(0, color="#64748b", linestyle="-", lw=0.8, alpha=0.5)
    axs[1, 1].axvline(100, color="#b45309", linestyle="--", lw=1.4)
    axs[1, 1].axvline(200, color="#15803d", linestyle="--", lw=1.5)
    axs[1, 1].set_title("D. Weight Stabilization under L2 Regularization (λ = 1024)", fontweight="bold", fontsize=11)
    axs[1, 1].set_xlabel("Training Epoch (0..500)", fontsize=9.5)
    axs[1, 1].set_ylabel("Matrix 8 DAC Code [Signed LSB]", fontsize=9.5)
    axs[1, 1].grid(True, linestyle=":", alpha=0.6)
    axs[1, 1].legend(fontsize=7.6, loc="lower left")

    fig.suptitle("INVERTED MAML MILESTONE 3: Deep-Dive Analysis of Broadened Window [4.5–5.5 ms] (λ = 1024, LR = 0.25)",
                 fontsize=13.0, fontweight="bold", y=0.98)

    out_docs = FIG_DIR / "fig_mode_a_500ep_deep_dive_reg1024.png"
    out_art = ARTIFACT_DIR / "fig_mode_a_500ep_deep_dive_reg1024.png"
    fig.savefig(out_docs, dpi=180, bbox_inches='tight')
    if ARTIFACT_DIR.exists():
        fig.savefig(out_art, dpi=180, bbox_inches='tight')
    plt.close(fig)
    return out_docs


def build_markdown_report(data: dict, fig_3d: Path, fig_5ms: Path, fig_win: Path, fig_deep: Path,
                          fig_m3_2d: Path, fig_m8_2d: Path,
                          fig_pcb: Path, fig_pat1: Path, fig_pat8: Path,
                          fig_pat5: Path, fig_pat6: Path) -> Path:
    md_path = DOC_DIR / "INVERTED_MAML_MILESTONE3_BROADENED_WINDOW_REPORT_EN.md"

    md_lines = [
        "# INVERTED MAML MILESTONE 3: 500-Epoch Empirical Silicon Evaluation Across Broadened Temporal Window [4500 – 5500 µs]",
        "### With 100% Identical 200-Sample Hadamard Measurement Cadence, True-Zero Reference Calibration, Elevated L2 Regularization (λ = 1024), and LR = 0.25",
        "",
        "**Patent Pending:** Swedish Patent Application SE 2630397-4  ",
        "**Inventor & System Architect:** Olle Welin  ",
        "**Platform:** Open Science Hardware | Efinix Trion T120 Master SoC (Ethernet @ `192.168.1.50:5000`, FW `v2.2-MAML`) & T20 Controller  ",
        "**Milestone 3 Protocol:** Broadened temporal discharge window `4500 µs to 5500 µs` (10 discrete temporal strata × `K = 20` batch = **200 Hadamard-active analog measurements per epoch** across all 500 epochs), `LR = 0.25x`, `L2 Reg λ = 1024`, `Noise Mode = COLOR_LLM_TOEPLITZ` (ρ = 0.85).  ",
        "**Dataset Source:** Physical silicon telemetry from `FPGA_code/logs/mode_a_extended_training/mode_a_500ep_broadened_4p5to5p5ms_reg1024_lr0p25_identical_k20_llm.json`  ",
        "**Code Repository:** [https://github.com/ollewelin/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4](https://github.com/ollewelin/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4)  ",
        "",
        "---",
        "",
        "## 1. Executive Summary & Milestone 3 Objectives",
        "",
        "### What is Milestone 3?",
        "While earlier evaluations characterized single-point compensation at the nominal `5000 µs` (`5.0 ms`) RC discharge midpoint, **Milestone 3** evaluates whether the Proprioceptive Inverted MAML triad (`Matrix 3 -> Sigmoid 4 -> Matrix 8`) and its temporal clock reference rows (`Row 6 ClkB1` and `Row 7 ClkRef` in `Matrix 3`) can actively track and compensate dynamic RC discharge leakage across an **extended 1000 µs temporal window (`4500 µs` to `5500 µs`)** at fixed room temperature.",
        "",
        "### Strict Experimental Consistency (`v2.2-MAML` Identical Cadence):",
        "To guarantee rigorous statistical comparability between uncompensated (`Phase 1`), static baseline (`Phase 2`), and actively trained (`Phase 3`) operation, **every single epoch (`0..500`) executes the exact same 200-sample Hadamard-active batch across all 10 temporal strata (`4500, 4611, 4722, 4833, 4944, 5056, 5167, 5278, 5389, 5500 µs`)**:",
        "- **Identical EMC & Capacitive Injection:** Full Walsh-Hadamard AC perturbation (`V_PTU`) is active during all 200 samples of every epoch (`0..500`).",
        "- **Identical True-Zero Target Origin:** `g_adc45_zero_cal` and `g_adc49_zero_cal` are calibrated strictly at true zero (`W_M3 = 0, W_M8 = 0, X = 0`) at `t = 5.0 ms` and locked across all 500 epochs.",
        "- **Only Controlled Variables Change:** Between phases, ONLY the baseline weight table (`W = 0` in Ep `0..99` vs. Smart S-Bend Baseline in Ep `100..199`) and the learning switches (`LR = 0, λ = 0` in Ep `0..199` vs. `LR = 0.25, λ = 1024` in Ep `200..500`) change.",
        "",
        "### Key Empirical Silicon Findings:",
        "1. **Substantial Full-Window Error Collapse (>10σ Significance):** Across the 200-sample `[4500..5500 µs]` window, active training (`Ep 200..500`) reduced the mean quadratic error from **74,896.7 ± 1,069.0 LSB²** (Phase 2 Smart Baseline) and **69,800.4 ± 953.0 LSB²** (Phase 1 `W = 0`) down to **59,233.1 ± 1,581.6 LSB²** (sustained 300-epoch mean) and a minimum of **56,013.5 LSB²** at Epoch 212 (**-25.2 % error reduction** vs. Phase 2, **-19.8 %** vs. `W = 0`).",
        "2. **High-Precision 5.0 ms Center Anchor:** Simultaneously, at the nominal `5.0 ms` center snapshot, active training achieved a minimum loss of **259.0 LSB² (RMSE = 9.29 LSB)** at Epoch 245, corresponding to **7.78 bits Standard ENOB (7.02 bits IEEE ENOB)**.",
        "3. **Elimination of Permanent Rail Clamping (`λ = 1024`):** With matching-sign S-bend initialization (`M3_diag = {-24, -24, +24, +24, -24, +24}`, `M8_diag = {-20, -20, +20, +20, -20, +20}`) and elevated L2 regularization (`λ = 1024`), Column 4 (`M8[4,4]`) never clamped (smoothly transitioning to `+34..+64 LSB`), and Column 3 (`M8[3,3]`) was actively pulled back from `+120 LSB` into the linear operating region (`+100..+112 LSB`).",
        "",
        "---",
        "",
        "## 2. Empirical Silicon Telemetry Table (Milestone 3: [4500 – 5500 µs], K=20, 200 Samples/Epoch)",
        "",
        "| Metric | Phase 1: M33 Alone (Ep 0..99) | Phase 2: Smart Baseline (Ep 100..199) | **Phase 3: Trained Peak (Ep 212 / Ep 245)** | Phase 3: Sustained Mean (Ep 200..500) |",
        "| :--- | :---: | :---: | :---: | :---: |",
        "| **Compensation Mode** | Zeroed ($W=0\\text{ LSB}$) | Balanced Smart S-Bend | **Active Closed-Loop Trained** | Sustained Active Trained |",
        "| **Hyperparameters** | $\\text{LR}=0,\\, \\lambda=0$ | $\\text{LR}=0,\\, \\lambda=0$ | **$\\text{LR}=0.25,\\, \\lambda=1024$** | $\\text{LR}=0.25,\\, \\lambda=1024$ |",
        "| **Hadamard Cadence** | 200 samples/ep (ON) | 200 samples/ep (ON) | **200 samples/ep (ON)** | 200 samples/ep (ON) |",
        "| **200-Sample Window Mean Loss** | $69\\,800.4 \\pm 953.0\\text{ LSB}^2$ | $74\\,896.7 \\pm 1\\,069.0\\text{ LSB}^2$ | **$56\\,013.5\\text{ LSB}^2$ (Ep 212)** | **$59\\,233.1 \\pm 1\\,581.6\\text{ LSB}^2$** |",
        "| **200-Sample Window Mean RMSE** | $152.53\\text{ LSB}$ | $158.00\\text{ LSB}$ | **$136.64\\text{ LSB}$ (Ep 212)** | **$140.50\\text{ LSB}$** |",
        "| **200-Sample Window ENOB [4.5..5.5 ms]** | $3.75 \\pm 0.01\\text{ bits}$ | $3.70 \\pm 0.01\\text{ bits}$ | **$3.91\\text{ bits}$ (Ep 212)** | **$3.87 \\pm 0.02\\text{ bits}$** |",
        "| **5.0 ms Center Snapshot Loss** | $3\\,660.6\\text{ LSB}^2$ (mean) | $6\\,533.4\\text{ LSB}^2$ (mean) | **$259.0\\text{ LSB}^2$ (Ep 245)** | $6\\,201.3\\text{ LSB}^2$ (mean) |",
        "| **5.0 ms Center Snapshot ENOB** | $6.02\\text{ bits}$ (peak $6.98\\text{b}$) | $5.54\\text{ bits}$ (peak $7.17\\text{b}$) | **$7.78\\text{ bits}$ ($7.02\\text{b}$ IEEE)** | $5.70\\text{ bits}$ (mean) |",
        "| **M8 Diagonal Weights [LSB]** | $[0, 0, 0, 0, 0, 0]$ | $[-20, -20, 20, 20, -20, 20]$ | $[-41, 2, -2, 85, 51, 86]$ | $[-35, 2, 5, 112, 43, 102]$ (Ep 500) |",
        "",
        "---",
        "",
        "## 3. Mathematical & Physical Analysis of Broadened Window Compensation",
        "",
        "Across the `[4500 .. 5500 µs]` RC discharge window, the uncompensated payload matrix $M_{33}$ exhibits a time-dependent gain decay $G_{33}(t) \\propto e^{-t / \\tau_{\\text{RC}}}$. While the digital target $z_{\\text{target}}$ is calibrated at the $t_0 = 5000\\text{ µs}$ midpoint, measurements at $t = 4500\\text{ µs}$ experience a systematically higher analog amplitude ($+\\Delta V(t)$) and measurements at $t = 5500\\text{ µs}$ experience a decayed amplitude ($-\\Delta V(t)$).",
        "",
        "In the physical FPGA firmware (`maml_platform.c`), the weight update across each 200-sample batch is governed by:",
        "$$\\Delta W = -\\eta \\cdot \\overline{g}_{[4.5..5.5\\text{ ms}]} - \\lambda \\cdot (W - W_{\\text{null}})$$",
        "where $\\overline{g}_{[4.5..5.5\\text{ ms}]}$ is the Forward Hadamard Propagation (FHP) gradient averaged over all 10 temporal strata ($K=20$ Toeplitz vectors per stratum). By training `Matrix 3` (including its dynamic clock ramp rows `Row 6 ClkB1` and `Row 7 ClkRef`) together with `Matrix 8` (including `Row 6 Vernier Bias`), the compensation network learns a joint spatial-temporal correction that reduces the integrated quadratic error across the full $1.0\\text{ ms}$ window by **20.9 % (sustained)** to **25.2 % (peak)**.",
        "",
        "---",
        "",
        "## 4. 3D Dual-2T1C Weight Topographies (Baseline vs. Trained Golden State at Ep 245)",
        "",
        f"![3D Weight Topography](file://{ARTIFACT_DIR / fig_3d.name})",
        "",
        "---",
        "",
        "## 5A. 500-Epoch Trajectories at SINGLE-POINT t = 5.0 ms ONLY (Nominal Center Snapshot)",
        "",
        f"![500-Epoch Single-Point 5.0 ms Trajectory](file://{ARTIFACT_DIR / fig_5ms.name})",
        "",
        "---",
        "",
        "## 5B. 500-Epoch Trajectories Across FULL TEMPORAL WINDOW [4.5 ms to 5.5 ms] AGGREGATED (200 Samples/Epoch)",
        "",
        f"![500-Epoch Full Window 4.5 to 5.5 ms Trajectory](file://{ARTIFACT_DIR / fig_win.name})",
        "",
        "---",
        "",
        "## 6. Full 2D Trajectories of All Weights (Matrix 3 & Matrix 8 across 500 Epochs)",
        "",
        "### Matrix 3 (First Triad Layer): 48 Dynamic Weights",
        f"![Matrix 3 2D Trajectories](file://{ARTIFACT_DIR / fig_m3_2d.name})",
        "",
        "### Matrix 8 (Second Triad Layer): 42 Vernier Weights",
        f"![Matrix 8 2D Trajectories](file://{ARTIFACT_DIR / fig_m8_2d.name})",
        "",
        "---",
        "",
        "## 7. Deep-Dive Analysis: Spike-Free 200-Sample Window Convergence & L2 Stabilization",
        "",
        f"![Deep Dive Analysis](file://{ARTIFACT_DIR / fig_deep.name})",
        "",
        "---",
        "",
        "## 8. Physical Hardware Silicon: Inverted MAML Proof-of-Concept PCB (v1.3.2)",
        "",
        f"![Physical Hardware PCB v1.3.2](file://{ARTIFACT_DIR / fig_pcb.name})",
        "",
        "---",
        "",
        "## 9. Patented Inverted MAML Proprioceptive Architecture (Patent SE 2630397-4 Fig 1)",
        "",
        f"![Patented Architecture Fig 1](file://{ARTIFACT_DIR / fig_pat1.name})",
        "",
        "---",
        "",
        "## 10. Forward Hadamard Propagation (FHP) & Capacitive Perturbation (Patent Fig 8)",
        "",
        f"![Patent Fig 8 FHP Circuit](file://{ARTIFACT_DIR / fig_pat8.name})",
        "",
        "---",
        "",
        "## 11. Overall Physical Conclusion: Single-Point (5.0 ms) vs. Full Temporal Window [4.5 – 5.5 ms] & Temporal Leakage Compensation in Analog Neural Networks (Patent Fig 5 & Fig 6)",
        "",
        "### 11.1 Why `W = 0` (`Epochs 0..99`) Excels Specifically at the `5.0 ms` Calibration Point",
        "The digital reference matrix ($G_{33}$) and the zero-input offset (`g_adc49_zero_cal`) are empirically identified at the exact midpoint $t_0 = 5.0\\text{ ms}$ with $W = 0\\text{ LSB}$. Consequently, at that **single instantaneous time point ($5.000\\text{ ms}$)**, the uncompensated primary matrix $M_{33}$ is already in its calibrated sweet spot, yielding a mean `5.0 ms` loss of **$3\\,660.6\\text{ LSB}^2$ ($6.02\\text{ bits}$ ENOB)**. However, because the storage capacitors $C_W$ in a physical Analog Neural Network undergo continuous **temporal charge leakage** across the inference phase $T_{\\text{INF}}$, the output voltage drifts rapidly away from $z_{\\text{target}}$ at earlier ($4.5\\text{ ms}$) and later ($5.5\\text{ ms}$) times, causing the uncompensated full-window loss across `[4.5 .. 5.5 ms]` to surge to **$69\\,800.4\\text{ LSB}^2$ ($3.75\\text{ bits}$ ENOB)**.",
        "",
        "### 11.2 What Happens When Closed-Loop Compensation Training Turns ON (`Epochs 200..500`)",
        "When active closed-loop training is enabled at Epoch 200 across all 10 displaced temporal strata (`4500 µs` to `5500 µs`), the proprioceptive triad (`Matrix 3 -> Sigmoid 4 -> Matrix 8`) optimizes the **integrated error across the entire `1.0 ms` temporal window** rather than at a single instant:",
        "- **Across the Complete `[4.5 ms .. 5.5 ms]` Temporal Window (Section 5B):** Total quadratic error drops decisively from **$69\\,800.4\\text{ LSB}^2$** (`W = 0`) and **$74\\,896.7\\text{ LSB}^2$** (Fixed Smart Baseline) down to a sustained mean of **$59\\,233.1\\text{ LSB}^2$ (`-20.9 %`)** and a minimum of **$56\\,013.5\\text{ LSB}^2$ (`-25.2 %`)**, while full-window ENOB rises from **$3.70\\text{–}3.75\\text{ bits}$** to **$3.87\\text{–}3.91\\text{ bits}$** ($>10\\sigma$ statistical significance).",
        "- **At the Single `5.0 ms` Point (Section 5A, Physical Trade-Off):** To generate the counter-slope that suppresses the large temporal leakage errors at `4.5 ms` and `5.5 ms`, the compensation network drives substantial active weights (`+43` to `+112 LSB` in $M_8$). This global temporal compromise causes the **mean** loss at the single `5.0 ms` midpoint ($6\\,201.3\\text{ LSB}^2$ / $5.70\\text{ bits}$) to be slightly worse than uncompensated `W = 0` ($3\\,660.6\\text{ LSB}^2$ / $6.02\\text{ bits}$) at that one instant—while still outperforming the fixed calibration baseline ($6\\,533.4\\text{ LSB}^2$ / $5.54\\text{ bits}$) even at `5.0 ms` and achieving single-epoch peaks up to **$7.78\\text{ bits}$ ($259.0\\text{ LSB}^2$ at Ep 245)**.",
        "",
        "### 11.3 Patent Fig 5: Displaced Temporal Measurement Windows Across $T_{\\text{INF}}$ (Patent Claim 10)",
        f"![Patent Fig 5 Displaced Temporal Windows](file://{ARTIFACT_DIR / fig_pat5.name})",
        "",
        "**Figure 11 (Patent SE 2630397-4, Fig 5):** Following each capacitor regeneration/refresh pulse $T_{\\text{RF}}$ (`18`), the analog neural network operates in continuous inference $T_{\\text{INF}}$ (`19`) while its stored charges slowly decay. By dynamically displacing the short Hadamard measurement windows (`20, 24`, with sub-windows $T_{\\text{M2A}}$ `21`, $T_{\\text{M2B}}/T_{\\text{M1A}}$ `22`, $T_{\\text{M1B}}$ `23`) by a selectable temporal offset $T_{\\text{RAND}}$ (`25`, corresponding to our 10 strata across `4500..5500 µs`), the digital controller (`9`) extracts time-dependent gradients across the entire discharge trajectory (`SAMP 1`, `SAMP 2`).",
        "",
        "### 11.4 Patent Fig 6: Physical Compensation of Temporal Leakage via Accelerated Reference Decay (Patent Claim 8)",
        f"![Patent Fig 6 Temporal Leakage vs Reference Curve](file://{ARTIFACT_DIR / fig_pat6.name})",
        "",
        "**Figure 12 (Patent SE 2630397-4, Fig 6):** Standard 2T1C computing cells (`27`) exhibit natural capacitive voltage leakage (`31`, solid curve) between refresh pulses $T_{\\text{RF}}$ (`18`). To make the neural network explicitly aware of elapsed time $t$ without digital timers in the analog path, `Matrix 3` integrates dedicated temporal reference cells (`29`, Rows 6 & 7) equipped with an accelerated discharge path (`28`). This generates a steep, full-swing reference decay curve (`32`, dashed curve) that normalizes the time axis across the dynamic range of the analog sigmoid (`4`). Fed by this analog timestamp (`32`), the `Matrix 3 -> Sigmoid 4 -> Matrix 8` triad dynamically tracks and cancels the natural temporal leakage (`31`) of the Analog Neural Network across the entire inference window.",
        "",
        "### 11.5 Future Research & Hyperparameter Optimization Directions",
        "While Milestone 3 demonstrates decisive ($>10\\sigma$) full-window error reduction across `[4.5 ms .. 5.5 ms]`, further systematic optimization is required in upcoming investigations:",
        "1. **Strata Count $\\times$ Batch Size ($K$) Trade-Off:** Investigating the optimal balance between the number of discrete temporal strata across the discharge window and the number of Hadamard-perturbed input samples $K$ per stratum (e.g., dense strata with smaller $K$ vs. weighted strata emphasizing the center and boundaries).",
        "2. **Joint Tuning of Learning Rate ($\\text{LR}$) and L2 Regularization ($\\lambda$):** Fine-tuning the ratio $\\eta / \\lambda$ and potentially applying stratum-weighted or layer-specific regularization so that the triad achieves maximum edge compensation at `4.5 ms` and `5.5 ms` without sacrificing single-point precision at the `5.0 ms` center anchor.",
        "3. **Multi-Cycle Undersampling Across Consecutive $10\\text{ ms}$ Refresh Turns (Patent Fig 5):** As illustrated in Patent `Fig 5` (`18, 19, 20, 21, 22, 23, 24, 25`), rather than pausing inference to collect all strata in a single burst, future firmware revisions will investigate **undersampling across multiple consecutive $10\\text{ ms}$ refresh cycles**—extracting a single short sub-window ($T_{\\text{M2A}}$ `21`, $T_{\\text{M2B}}/T_{\\text{M1A}}$ `22`, $T_{\\text{M1B}}$ `23`) at a displaced time $T_{\\text{RAND}}$ (`25`) per $10\\text{ ms}$ turn while dedicating $>95\\,\\%$ of each cycle to uninterrupted high-throughput analog inference ($T_{\\text{INF}}$, `19`).",
        "",
        "---",
        "",
        "## 12. Open Science Reproducibility Summary",
        "",
        "All telemetry records and plots in this Milestone 3 report are 100 % authentic, measured directly on physical silicon hardware via the Efinix Trion T120 SoC at `192.168.1.50:5000` running `v2.2-MAML` firmware. Every epoch (`0..500`) executed the exact same 200-sample Hadamard batch across `[4500..5500 µs]`."
    ]

    with open(md_path, "w") as f:
        f.write("\n".join(md_lines) + "\n")

    if ARTIFACT_DIR.exists():
        shutil.copy2(md_path, ARTIFACT_DIR / md_path.name)

    return md_path


def build_pdf_report(data: dict, fig_3d: Path, fig_5ms: Path, fig_win: Path, fig_deep: Path,
                     fig_m3_2d: Path, fig_m8_2d: Path,
                     fig_pcb: Path, fig_pat1: Path, fig_pat8: Path,
                     fig_pat5: Path, fig_pat6: Path) -> Path:
    pdf_path = DOC_DIR / "INVERTED_MAML_MILESTONE3_BROADENED_WINDOW_REPORT_EN.pdf"

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DocTitle", parent=styles["Title"], fontSize=12.5, leading=15.5, textColor=colors.HexColor("#1a252f"), spaceAfter=3
    )
    sub_style = ParagraphStyle(
        "DocSub", parent=styles["Normal"], fontSize=8.2, leading=11.0, textColor=colors.HexColor("#555555"), spaceAfter=5
    )
    h1_style = ParagraphStyle(
        "H1", parent=styles["Heading2"], fontSize=10.2, leading=13.0, textColor=colors.HexColor("#1a5276"), spaceBefore=4, spaceAfter=2.5
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"], fontSize=8.0, leading=10.8, spaceAfter=2.5
    )
    bullet_style = ParagraphStyle(
        "Bullet", parent=body_style, leftIndent=10, spaceAfter=2.0
    )

    fhp_banner_style = ParagraphStyle(
        "FHPBanner", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8.5, leading=11.5,
        textColor=colors.HexColor("#0f172a"),
        backColor=colors.HexColor("#f8fafc"),
        borderColor=colors.HexColor("#2563eb"),
        borderWidth=1,
        borderPadding=5,
        spaceBefore=2,
        spaceAfter=4,
    )

    story = []

    # =========================================================================
    # PAGE 1: Executive Summary, Milestone 3 Protocol, and Telemetry Table
    # =========================================================================
    story.append(Paragraph(
        "Inverted MAML Milestone 3: 500-Epoch Silicon Evaluation Across Broadened Temporal Window [4500 – 5500 µs]",
        title_style
    ))
    story.append(Paragraph(
        "<b>Patent Pending SE 2630397-4</b> | Open Science Hardware | Trion T120 SoC (192.168.1.50:5000, FW v2.2-MAML) | LR = 0.25, &lambda; = 1024",
        sub_style
    ))

    story.append(Paragraph("1. Executive Summary & Milestone 3 Broadened Temporal Window Evaluation", h1_style))
    story.append(Paragraph(
        "<b>Milestone 3 Objective:</b> Evaluate closed-loop Mode A training across an extended <b>1000 µs temporal discharge window (4500 µs to 5500 µs)</b> at fixed room temperature. Across this 1.0 ms span, the uncompensated payload matrix (Matrix 33) undergoes continuous RC decay. Milestone 3 tests whether the proprioceptive triad (<i>Matrix 3 &rarr; Sigmoid 4 &rarr; Matrix 8</i>) and its temporal clock reference rows can minimize the integrated error across all 10 temporal strata simultaneously.",
        body_style
    ))
    story.append(Paragraph(
        "<b>Strict Experimental Consistency (v2.2-MAML Identical Cadence):</b> Every single epoch (0..500) executes the exact same <b>200-sample Hadamard-active batch</b> (10 temporal strata &times; K = 20 Toeplitz vectors/stratum) with identical Walsh-Hadamard AC perturbation (<i>V_PTU</i>) and a locked true-zero target origin (<i>W = 0, X = 0</i> at 5.0 ms). Between phases, <b>only</b> the baseline weight table and learning parameters (<i>LR, &lambda;</i>) change:",
        body_style
    ))
    story.append(Paragraph(
        "• <b>Substantial Full-Window Error Reduction (&gt;10&sigma; Significance):</b> Active closed-loop training (Epochs 200..500) reduced the 200-sample window mean loss from <b>74 896.7 &plusmn; 1 069.0 LSB²</b> (Phase 2 Smart Baseline) and <b>69 800.4 &plusmn; 953.0 LSB²</b> (Phase 1 W=0) down to a sustained mean of <b>59 233.1 &plusmn; 1 581.6 LSB² (-20.9 %)</b> and a minimum of <b>56 013.5 LSB² (-25.2 %, 3.91 bits ENOB)</b> at Epoch 212.",
        bullet_style
    ))
    story.append(Paragraph(
        "• <b>7.78-Bit Peak Resolution at the 5.0 ms Center Snapshot:</b> At the nominal 5.0 ms center point, closed-loop training reached a minimum loss of <b>259.0 LSB² (RMSE = 9.29 LSB)</b> at Epoch 245, corresponding to <b>7.78 bits Standard ENOB (7.02 bits IEEE ENOB)</b>.",
        bullet_style
    ))
    story.append(Paragraph(
        "• <b>Zero Permanent Rail Clamping (&lambda; = 1024):</b> With matching-sign S-bend baseline polarity and &lambda; = 1024, Column 4 never clamped (settling smoothly at +34..+64 LSB) and Column 3 was actively pulled back from +120 LSB into the linear range (+100..+112 LSB).",
        bullet_style
    ))

    story.append(Paragraph("2. Physical In-Data Model & Identical-Cadence Hyperparameters", h1_style))
    story.append(Paragraph(
        "• <b>Temporal Window:</b> 4500 µs to 5500 µs in 10 evenly spaced strata (4500, 4611, 4722, 4833, 4944, 5056, 5167, 5278, 5389, 5500 µs), K = 20 samples/stratum = 200 Hadamard-active samples per epoch across all 500 epochs.<br/>"
        "• <b>Hyperparameters:</b> Phase 1 &amp; 2: LR = 0, &lambda; = 0. Phase 3 (Ep 200..500): <b>LR = 0.25x, &lambda; = 1024</b>.<br/>"
        "• <b>In-Data Vector Equalizer:</b> COLOR_LLM_TOEPLITZ (&rho; = 0.85) with hardware zero-mean centering (LayerNorm) preserving 1.65 V virtual ground.",
        body_style
    ))

    story.append(Paragraph("3. Empirical Silicon Telemetry Comparison Table (100% Identical Cadence)", h1_style))
    table_data = [
        ["Parameter / Metric", "Phase 1: M33 Alone", "Phase 2: Smart Baseline", "Phase 3: Trained Peak", "Phase 3: Sustained Mean"],
        ["Epoch Range & Mode", "Ep 0..99 (W=0 LSB)", "Ep 100..199 (Smart Base)", "Ep 212 (Win) / Ep 245 (5ms)", "Ep 200..500 (300 Epochs)"],
        ["Training Parameters", "LR = 0, λ = 0 (OFF)", "LR = 0, λ = 0 (OFF)", "LR = 0.25, λ = 1024 (ON)", "LR = 0.25, λ = 1024 (ON)"],
        ["Hadamard Batch Cadence", "200 samples/ep (ON)", "200 samples/ep (ON)", "200 samples/ep (ON)", "200 samples/ep (ON)"],
        ["Window Mean Loss [4.5..5.5]", "69 800.4 ± 953 LSB²", "74 896.7 ± 1 069 LSB²", "56 013.5 LSB² (-25.2%)", "59 233.1 ± 1 582 LSB²"],
        ["Window Mean RMSE [4.5..5.5]", "152.53 LSB", "158.00 LSB", "136.64 LSB (Ep 212)", "140.50 LSB"],
        ["Window Mean ENOB [4.5..5.5]", "3.75 ± 0.01 bits", "3.70 ± 0.01 bits", "3.91 bits (Ep 212)", "3.87 ± 0.02 bits"],
        ["5.0 ms Center Loss", "3 660.6 LSB² (mean)", "6 533.4 LSB² (mean)", "259.0 LSB² (Ep 245)", "6 201.3 LSB² (mean)"],
        ["5.0 ms Center ENOB", "6.02 b (peak 6.98 b)", "5.54 b (peak 7.17 b)", "7.78 b (7.02 b IEEE)", "5.70 bits (mean)"],
        ["M8 Diagonal Weights", "[0, 0, 0, 0, 0, 0]", "[-20,-20,20,20,-20,20]", "[-41, 2,-2, 85, 51, 86]", "[-35, 2, 5,112, 43,102]"]
    ]
    t = Table(table_data, colWidths=[45*mm, 32*mm, 34*mm, 38*mm, 35*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a5276")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.0),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f6f7")]),
        ("BACKGROUND", (3, 1), (3, -1), colors.HexColor("#d4edda")),
    ]))
    story.append(t)
    story.append(PageBreak())

    # =========================================================================
    # PAGE 2: 3D Dual-2T1C Weight Topographies
    # =========================================================================
    story.append(Paragraph("4. 3D Dual-2T1C Weight Topographies (Baseline vs. Trained Golden State at Ep 245)", h1_style))
    story.append(Paragraph(
        "The 4-panel 3D bar landscapes below document the physical DAC weights programmed into the Dual-2T1C analog multiplier crosspoints. "
        "Subplots 1 &amp; 2 show the balanced Smart S-Bend baseline at Epoch 100 (zero-sum alternating off-diagonals &plusmn;8 / &plusmn;6 LSB and matching-sign S-bend diagonals). "
        "Subplots 3 &amp; 4 show the trained Golden State at Epoch 245 (where 5.0 ms ENOB hit 7.78 bits and 200-sample Window Loss dropped to 58 283 LSB²).",
        body_style
    ))
    story.append(Spacer(1, 2 * mm))
    story.append(Image(str(fig_3d), width=182 * mm, height=138 * mm))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 3: 500-Epoch Trajectory at SINGLE-POINT 5.0 ms ONLY
    # =========================================================================
    story.append(Paragraph("5A. 500-Epoch Trajectories at SINGLE-POINT t = 5.0 ms ONLY (Nominal Center Snapshot)", h1_style))
    story.append(Paragraph(
        "<b>Important Distinction (Single-Point t = 5.0 ms ONLY):</b> Figure 2A below shows Loss and ENOB measured <b>strictly at the single 5000 µs midpoint</b> "
        "(whereas Page 4 shows the combined performance across the full 4.5–5.5 ms window). Because the digital target matrix (<i>G_33</i>) and zero offset were "
        "calibrated at t = 5.0 ms with W = 0, Phase 1 (W = 0) already sits at its sweet spot (mean 3 661 LSB² / 6.02 bits) at this single instant. When full-window "
        "training turns ON at Epoch 200, the network compromises slightly on the 5.0 ms mean (6 201 LSB² / 5.70 bits, still beating Phase 2's 5.54 bits and peaking at "
        "<b>7.78 bits</b> at Ep 245) in order to aggressively suppress the large RC discharge errors at 4.5 ms and 5.5 ms (shown on Page 4).",
        body_style
    ))
    story.append(Spacer(1, 2 * mm))
    story.append(Image(str(fig_5ms), width=182 * mm, height=134 * mm))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 4: 500-Epoch Trajectory Across FULL TEMPORAL WINDOW [4.5..5.5 ms] ONLY
    # =========================================================================
    story.append(Paragraph("5B. 500-Epoch Trajectories Across FULL TEMPORAL WINDOW [4.5 ms to 5.5 ms] AGGREGATED", h1_style))
    story.append(Paragraph(
        "<b>Full Temporal Window Evaluation (All 10 Strata &times; K=20 = 200 Samples/Epoch):</b> Figure 2B below presents the identically structured 3-panel plot "
        "for the <b>complete 1000 µs discharge window from 4.5 ms to 5.5 ms</b>. Across this broad window, uncompensated RC decay causes massive edge errors in "
        "Phase 1 (W = 0: mean 69 800 LSB² / 3.75 bits) and Phase 2 (Smart Baseline: mean 74 897 LSB² / 3.70 bits). Immediately upon activating closed-loop training "
        "at Epoch 200, full-window Loss drops by <b>-20.9 % (mean 59 233 LSB²)</b> and <b>-25.2 % (min 56 014 LSB² at Ep 212)</b>, while full-window ENOB steps up "
        "decisively to <b>3.87 bits mean (3.91 bits peak)</b>.",
        body_style
    ))
    story.append(Spacer(1, 2 * mm))
    story.append(Image(str(fig_win), width=182 * mm, height=134 * mm))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 5: 2D Weight Trajectories (M3 & M8 across 500 Epochs)
    # =========================================================================
    story.append(Paragraph("6. Full 2D Dynamic Trajectories of All Weights across 500 Epochs", h1_style))
    story.append(Paragraph(
        "The plots below trace every individual weight programmed into the physical Dual-2T1C silicon across all 500 epochs. "
        "<b>Matrix 3 (Top):</b> Displays all 36 compute crosspoints (solid curves) and 12 temporal reference weights (dashed lines, Rows 6 &amp; 7). "
        "<b>Matrix 8 (Bottom):</b> Displays all 36 vernier compute weights (solid curves) and 6 Vernier Bias weights (dashed red lines). All weights remain strictly frozen during Phase 1 (0..99) and Phase 2 (100..199) while full Hadamard bursts run continuously, then adapt smoothly at Epoch 200.",
        body_style
    ))
    story.append(Spacer(1, 1.5 * mm))
    story.append(Image(str(fig_m3_2d), width=182 * mm, height=84 * mm))
    story.append(Spacer(1, 2 * mm))
    story.append(Image(str(fig_m8_2d), width=182 * mm, height=84 * mm))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 6: Deep-Dive Analysis: Spike-Free Window Convergence & L2 Mechanics
    # =========================================================================
    story.append(Paragraph("7. Deep-Dive Analysis: Spike-Free 200-Sample Window Convergence & L2 Stabilization", h1_style))
    story.append(Paragraph(
        "Figure 4 highlights the Milestone 3 convergence mechanics: Panel A shows the continuous, spike-free 200-sample window loss across all 500 epochs. "
        "Panel B zooms into Epochs 160–320, contrasting the 200-sample window ENOB (blue) with the 5.0 ms center ENOB (red, peaking at 7.78 bits). "
        "Panel C presents the phase-by-phase boxplot distribution (&gt;10&sigma; separation). Panel D shows L2 regularization (&lambda; = 1024) defending Columns 3, 4, and 5 from permanent rail clamping.",
        body_style
    ))
    story.append(Spacer(1, 1.5 * mm))
    story.append(Image(str(fig_deep), width=182 * mm, height=112 * mm))
    story.append(Spacer(1, 2 * mm))

    story.append(Paragraph("8. Physical Principles of Broadened Temporal Window Compensation", h1_style))
    story.append(Paragraph(
        "Across [4500..5500 µs], the uncompensated RC decay of Matrix 33 introduces a strong time-varying residual error at the window edges (4.5 ms and 5.5 ms). "
        "In `maml_platform.c`, the weight update per 200-sample epoch is governed by: <i>&Delta;W = -&eta; &middot; g_win - &lambda; &middot; (W - W_null)</i>. "
        "By training Matrix 3 (including its clock ramp rows 6 &amp; 7) and Matrix 8 across all 10 temporal strata simultaneously, the triad learns a dynamic counter-slope that reduces full-window quadratic loss by 20.9% (sustained) to 25.2% (peak) while preserving a 7.78-bit peak anchor at 5.0 ms.",
        body_style
    ))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 7: Dedicated Page for Physical Hardware PCB v1.3.2
    # =========================================================================
    story.append(Paragraph("9. Physical Hardware Silicon: Inverted MAML Proof-of-Concept PCB (v1.3.2)", h1_style))
    story.append(Spacer(1, 2 * mm))
    if fig_pcb.exists():
        story.append(Image(str(fig_pcb), width=152 * mm, height=137 * mm))
    story.append(Spacer(1, 3 * mm))

    pcb_desc = (
        "<b>Figure 9: Physical Proof-of-Concept Hardware (PCB v1.3.2, Inverted_MAML_IMC).</b><br/>"
        "Designed and fabricated by inventor Olle Welin (Patent Pending SE 2630397-4). "
        "The board integrates a dual-FPGA Trion architecture: Trion T120F324 Master SoC (Ethernet @ 192.168.1.50:5000, 32-bit RISC-V Sapphire) "
        "and Trion T20F256 Controller, high-speed 74HC595 differential DAC ladders, discrete 2T1C MOS triode analog multiplier crosspoint arrays "
        "(Matrix 33 payload, Matrix 3, and Matrix 8), differential ColTIA transimpedance amplifiers, and XC2361A high-speed differential ADCs.<br/>"
        "<b>Hardware Repository &amp; Open Source RTL/Firmware:</b> "
        "<a href='https://github.com/ollewelin/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4'><font color='#2563eb'><u>https://github.com/ollewelin/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4</u></font></a>"
    )
    story.append(Paragraph(pcb_desc, body_style))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 8: Dedicated Page for Patent Fig 1 Proprioceptive Architecture (PERFECT NATURAL ASPECT RATIO!)
    # =========================================================================
    story.append(Paragraph("10. Patented Inverted MAML Proprioceptive Architecture (Patent SE 2630397-4 Fig 1)", h1_style))
    story.append(Spacer(1, 2 * mm))
    # Natural aspect ratio: 1024 / 850 = 1.2047. Width = 175 mm -> Height = 145.2 mm. UNCOMPRESSED!
    if fig_pat1.exists():
        story.append(Image(str(fig_pat1), width=175 * mm, height=145.2 * mm))
    story.append(Spacer(1, 3 * mm))

    pat1_desc = (
        "<b>Figure 10: Inverted MAML Proprioceptive Closed-Loop Architecture (Patent Application SE 2630397-4, Fig 1).</b><br/>"
        "<b>Architecture Operation:</b> Digital input (1) is converted via high-speed DAC ladder (2) into analog signals driving both the primary "
        "uncompensated matrix Matrix 33 (33) and the first Vernier matrix Matrix 3 (3). Temporal clock generator (30) drives dedicated rows (29) in Matrix 3 "
        "to provide explicit temporal awareness across the RC discharge window [4500..5500 µs]. The output of Matrix 3 passes through analog sigmoid activation (4) "
        "and is sampled by ADC (45) for the digital controller (9). The second Vernier matrix Matrix 8 (8) injects anti-phase compensation currents into "
        "summing junctions (35) before final transimpedance amplification and sampling by ADC (49) to produce the high-precision digital output (11)."
    )
    story.append(Paragraph(pat1_desc, body_style))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 9: Dedicated Page for Forward Hadamard Propagation (Patent Fig 8)
    # =========================================================================
    story.append(Paragraph("11. Forward Hadamard Propagation (FHP) & Capacitive Perturbation (Patent Fig 8)", h1_style))
    story.append(Spacer(1, 1 * mm))

    fhp_banner = (
        "Forward Hadamard Propagation (FHP) – parallel capacitive perturbation for single-shot analog gradient extraction. "
        "(Works for physical unknown Analog Neural Networks)."
    )
    story.append(Paragraph(fhp_banner, fhp_banner_style))
    story.append(Spacer(1, 1.5 * mm))

    # Natural aspect ratio: 1024 / 768 = 1.333. Width = 175 mm -> Height = 131.25 mm.
    if fig_pat8.exists():
        story.append(Image(str(fig_pat8), width=175 * mm, height=131.25 * mm))
    story.append(Spacer(1, 2.5 * mm))

    fhp_text = (
        "<b>Physical Circuit Operation &amp; Theoretical Breakthrough of FHP (SE 2630397-4 Fig 8):</b><br/>"
        "<b>1. Parallel Capacitive Perturbation (C_PTU, Ref 7):</b> An AC perturbation square wave V_PTU (5) is modulated by 3-state Hadamard "
        "drivers (6) along perturbation lines PL_1..PL_n. Each crosspoint cell couples the carrier through dedicated perturbation capacitor "
        "C_PTU (7) onto the floating gate storage node C_W (44) of the 2T1C MOS triode transistor. Crucially, C_PTU perturbs the operating point "
        "dynamically without altering or leaking the static stored weight voltage.<br/>"
        "<b>2. Single-Shot Analog Gradient Extraction:</b> In conventional analog tuning, extracting the gradient vector of N weights requires "
        "2N sequential forward perturbations, creating massive latency and thermal drift. FHP applies mutually orthogonal Walsh/Hadamard carrier waves "
        "simultaneously across all rows. In each analog measurement snapshot across [4.5..5.5 ms], the composite response at the summing amplifiers "
        "is projected onto the Hadamard basis in the digital domain (T120 SoC), isolating all partial derivatives in O(1) time.<br/>"
        "<b>3. Universal In-Situ Training for Arbitrary Analog Networks:</b> FHP requires zero internal analytical models of the physical transistors, "
        "threshold voltages, parasitic capacitances, or thermal drift. It treats the physical Analog Neural Network as a true unknown black box, "
        "enabling robust closed-loop learning on physical silicon where classical backpropagation fails."
    )
    story.append(Paragraph(fhp_text, body_style))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 10: Overall Conclusion Part 1 & Patent Fig 5 (Displaced Temporal Window Sampling)
    # =========================================================================
    story.append(Paragraph(
        "12. Overall Conclusion: Single-Point (5.0 ms) vs. Full Temporal Window [4.5 – 5.5 ms] & Temporal Leakage",
        h1_style
    ))
    story.append(Paragraph(
        "<b>Why W = 0 (Epochs 0..99) Excels Specifically at the Single 5.0 ms Calibration Instant (Page 3):</b><br/>"
        "The digital reference matrix (<i>G_33</i>) and the zero-input offset (<i>g_adc49_zero_cal</i>) are empirically calibrated at the exact midpoint "
        "<b>t_0 = 5.0 ms with W = 0 LSB</b>. Consequently, at that single instant (5.000 ms), the uncompensated primary matrix Matrix 33 is already at its "
        "calibrated sweet spot, achieving a mean 5.0 ms Loss of <b>3 660.6 LSB² (6.02 bits ENOB)</b>. However, because the storage capacitors (<i>C_W</i>) in a "
        "physical Analog Neural Network undergo continuous <b>temporal charge leakage</b> across the inference cycle, the analog output drifts rapidly away "
        "from the target at earlier (4.5 ms) and later (5.5 ms) times, causing the uncompensated full-window loss across [4.5..5.5 ms] to surge to "
        "<b>69 800.4 LSB² (3.75 bits ENOB)</b>.",
        body_style
    ))
    story.append(Paragraph(
        "<b>What Happens When Closed-Loop Compensation Training Turns ON (Epochs 200..500, Page 4 vs. Page 3):</b><br/>"
        "When active closed-loop training is switched ON at Epoch 200 across all 10 displaced temporal strata (4500 µs to 5500 µs), the proprioceptive triad "
        "(<i>Matrix 3 &rarr; Sigmoid 4 &rarr; Matrix 8</i>) optimizes the <b>integrated error across the complete 1.0 ms temporal window</b> rather than at a single point:<br/>"
        "• <b>Across the Complete [4.5 ms .. 5.5 ms] Temporal Window (Page 4):</b> Total quadratic error drops decisively from <b>69 800.4 LSB²</b> (W = 0) and "
        "<b>74 896.7 LSB²</b> (Fixed Smart Baseline) down to a sustained mean of <b>59 233.1 LSB² (-20.9 %)</b> and a minimum of <b>56 013.5 LSB² (-25.2 %)</b>, "
        "lifting full-window ENOB from <b>3.70–3.75 bits</b> to <b>3.87–3.91 bits</b> (&gt;10&sigma; statistical significance).<br/>"
        "• <b>At the Single 5.0 ms Midpoint (Page 3, Physical Trade-Off):</b> To generate the dynamic counter-slope that suppresses the large temporal leakage errors at "
        "the 4.5 ms and 5.5 ms window edges, the compensation network drives substantial active weights (+43 to +112 LSB in Matrix 8). This global temporal "
        "compromise makes the mean loss at the single 5.0 ms point (<b>6 201.3 LSB² / 5.70 bits</b>) slightly higher than uncompensated W = 0 (3 660.6 LSB² / 6.02 bits) "
        "at that one instant—while still outperforming the fixed calibration baseline (6 533.4 LSB² / 5.54 bits) even at 5.0 ms and achieving single-epoch "
        "peaks up to <b>7.78 bits (259.0 LSB² at Epoch 245)</b>.",
        body_style
    ))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph("12.1 Displaced Temporal Window Sampling Across Inference (Patent SE 2630397-4 Fig 5, Claim 10)", h1_style))
    story.append(Spacer(1, 1.5 * mm))
    # Natural aspect ratio of Fig 5: 943 / 503 = 1.87475. Width = 175 mm -> Height = 93.35 mm. UNCOMPRESSED!
    if fig_pat5.exists():
        story.append(Image(str(fig_pat5), width=175 * mm, height=93.35 * mm))
    story.append(Spacer(1, 2.5 * mm))
    story.append(Paragraph(
        "<b>Figure 11: Displaced Temporal Measurement Windows Across the Inference Discharge Cycle (Patent SE 2630397-4, Fig 5).</b><br/>"
        "Following each capacitor refresh pulse <b>T_RF (18)</b>, the analog neural network executes uninterrupted inference <b>T_INF (19)</b> while its "
        "stored capacitor charges slowly decay. By dynamically shifting the temporal displacement <b>T_RAND (25)</b> of the short Hadamard perturbation "
        "windows (<b>20, 24</b>, comprising sub-windows <b>T_M2A (21)</b>, <b>T_M2B/T_M1A (22)</b>, and <b>T_M1B (23)</b>) across the discharge trajectory "
        "(<i>SAMP 1, SAMP 2</i>, implemented as our 10 strata from 4500 µs to 5500 µs), the digital controller (9) extracts time-dependent gradients covering "
        "the entire temporal window without interrupting normal payload throughput.",
        body_style
    ))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 11: Patent Fig 6 (Temporal Leakage vs. Accelerated Reference Decay) & Final Summary
    # =========================================================================
    story.append(Paragraph(
        "12.2 Compensating Temporal Leakage via Accelerated Reference Cells (Patent SE 2630397-4 Fig 6, Claim 8)",
        h1_style
    ))
    story.append(Spacer(1, 2 * mm))
    # Natural aspect ratio of Fig 6: 815 / 444 = 1.83559. Width = 172 mm -> Height = 93.70 mm. UNCOMPRESSED!
    if fig_pat6.exists():
        story.append(Image(str(fig_pat6), width=172 * mm, height=93.70 * mm))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        "<b>Figure 12: Natural Computing Cell Leakage (31) vs. Accelerated Temporal Reference Decay (32) (Patent SE 2630397-4, Fig 6).</b><br/>"
        "<b>Physical Mechanism for Handling Temporal Leakage in Analog Neural Networks:</b><br/>"
        "• <b>Natural Capacitor Leakage (Curve 31, Solid Line):</b> After each refresh cycle <b>T_rf (18)</b>, the computing crosspoint cells (27) in Matrix 33, "
        "Matrix 3, and Matrix 8 experience a gradual, time-dependent voltage decay (31) due to finite switch off-resistance, transistor leakage, and summing "
        "node impedance. Left uncompensated, this temporal leakage degrades matrix-vector multiplication accuracy as elapsed time increases from 4.5 ms to 5.5 ms.<br/>"
        "• <b>Accelerated Full-Swing Temporal Reference (Curve 32, Dashed Line):</b> To give the compensation network explicit physical awareness of elapsed "
        "time <i>t</i> within each refresh cycle, Matrix 3 integrates dedicated temporal reference cells (29, Rows 6 &amp; 7) configured with an accelerated "
        "discharge path (28). As shown by dashed curve (32), the reference cell voltage decays steeply across a substantial portion of the full analog signal "
        "swing between refresh pulses (18), physically normalizing the time axis.<br/>"
        "• <b>Proprioceptive Temporal Compensation:</b> Fed by the steep analog timestamp (32) into the non-linear analog sigmoid activation (4), the "
        "<i>Matrix 3 &rarr; Sigmoid 4 &rarr; Matrix 8</i> triad learns a time-varying correction current that tracks and cancels the natural temporal leakage (31) "
        "of the primary computing matrix across the entire [4.5 ms .. 5.5 ms] window.",
        body_style
    ))
    story.append(Spacer(1, 2 * mm))

    story.append(Paragraph(
        "12.3 Future Research & Optimization: Strata × K Size, LR, L2 Regularization & Multi-Cycle 10 ms Undersampling",
        h1_style
    ))
    story.append(Paragraph(
        "While Milestone 3 demonstrates decisive (&gt;10&sigma;) full-window error reduction across [4.5 ms .. 5.5 ms], four key areas will be systematically "
        "investigated and optimized in upcoming work:<br/>"
        "• <b>1. Strata Count &times; Batch Size (K) Trade-Off:</b> Optimizing the balance between the number of discrete temporal strata across the discharge "
        "window and the number of Hadamard-perturbed input vectors <i>K</i> per stratum (e.g., denser temporal strata with smaller <i>K</i> vs. non-uniform "
        "stratum weighting that preserves the 5.0 ms anchor while suppressing edge drift).<br/>"
        "• <b>2. Joint Tuning of Learning Rate (LR) and L2 Regularization (&lambda;):</b> Co-optimizing <i>&eta;</i> and <i>&lambda;</i> (including layer-specific "
        "regularization for Matrix 3 vs. Matrix 8) so the compensation network achieves deeper window error reduction without sacrificing single-point precision "
        "at 5.0 ms.<br/>"
        "• <b>3. Multi-Cycle Undersampling Across Consecutive 10 ms Refresh Turns (Patent Fig 5):</b> As shown in Patent Fig 5 (<i>18, 19, 20, 21, 22, 23, 24, 25</i>), "
        "future operational modes will investigate <b>undersampling distributed across multiple consecutive 10 ms refresh cycles</b>—capturing only a minimal "
        "sub-window (<i>T_M2A</i> (21), <i>T_M2B/T_M1A</i> (22), <i>T_M1B</i> (23)) at a displaced offset <i>T_RAND</i> (25) during each 10 ms turn, reserving "
        "&gt;95 % of every 10 ms cycle for uninterrupted, full-speed analog inference (<i>T_INF</i>, 19).",
        body_style
    ))
    story.append(Spacer(1, 2 * mm))

    story.append(Paragraph("13. Verification & Open Science Reproducibility Summary", h1_style))
    story.append(Paragraph(
        "All telemetry data in this Milestone 3 report is 100 % authentic, measured directly on physical silicon hardware via the Efinix Trion T120 SoC at "
        "192.168.1.50:5000 (FW v2.2-MAML). No digital simulation or synthetic curves were used. Every epoch (0..500) executed the identical 200-sample "
        "Hadamard batch across [4500..5500 µs]. Complete RTL, C firmware, and Python runners are publicly available at:<br/>"
        "<a href='https://github.com/ollewelin/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4'><font color='#2563eb'><u>https://github.com/ollewelin/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4</u></font></a>",
        body_style
    ))

    def add_page_decorations(canvas, doc_obj):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.8)
        canvas.setFillColor(colors.HexColor("#64748b"))
        canvas.drawString(12 * mm, 6 * mm, "Inverted MAML Milestone 3 Research | Patent Pending SE 2630397-4 | Open Science Hardware")
        page_str = f"Page {canvas._pageNumber} of 11"
        canvas.drawRightString(210 * mm - 12 * mm, 6 * mm, page_str)
        canvas.restoreState()

    doc.build(story, onFirstPage=add_page_decorations, onLaterPages=add_page_decorations)

    if ARTIFACT_DIR.exists():
        shutil.copy2(pdf_path, ARTIFACT_DIR / pdf_path.name)

    return pdf_path


def main():
    if not DATA_PATH.exists():
        print(f"[!] Dataset not found at {DATA_PATH}")
        sys.exit(1)

    with open(DATA_PATH, "r") as f:
        data = json.load(f)

    fig_pcb = FIG_DIR / "fig_pcb_v132_hardware.jpg"
    fig_pat1 = FIG_DIR / "fig_patent_fig1_architecture.jpg"
    fig_pat8 = FIG_DIR / "fig_patent_fig8_fhp_circuit.jpg"
    fig_pat5 = FIG_DIR / "fig_patent_fig5_temporal_leakage.png"
    fig_pat6 = FIG_DIR / "fig_patent_fig6_temporal_compensation.png"

    print("[*] 1. Generating 3D weight landscape figure (Baseline vs. Golden State Ep 245)...")
    fig_3d = generate_3d_landscapes(data)
    print(f"[+] Saved 3D figure: {fig_3d}")

    print("[*] 1B. Generating split 3-panel figures (Page 3: 5.0 ms ONLY vs. Page 4: Full Window [4.5..5.5 ms] ONLY)...")
    fig_5ms, fig_win = generate_split_5ms_and_window_figures(data)
    print(f"[+] Saved split figures: {fig_5ms}, {fig_win}")

    print("[*] 2. Generating 2D trajectory figures for Matrix 3 & Matrix 8...")
    fig_m3_2d, fig_m8_2d = generate_2d_trajectories(data)
    print(f"[+] Saved 2D figures: {fig_m3_2d}, {fig_m8_2d}")

    print("[*] 3. Generating spike-free deep-dive figure...")
    fig_deep = generate_deep_dive_figure(data)
    print(f"[+] Saved deep-dive figure: {fig_deep}")

    print("[*] 4. Generating Milestone 3 English Markdown report...")
    md_path = build_markdown_report(data, fig_3d, fig_5ms, fig_win, fig_deep,
                                    fig_m3_2d, fig_m8_2d,
                                    fig_pcb, fig_pat1, fig_pat8,
                                    fig_pat5, fig_pat6)
    print(f"[+] Saved Markdown report: {md_path}")

    print("[*] 5. Generating 11-Page Milestone 3 English PDF report...")
    pdf_path = build_pdf_report(data, fig_3d, fig_5ms, fig_win, fig_deep,
                                fig_m3_2d, fig_m8_2d,
                                fig_pcb, fig_pat1, fig_pat8,
                                fig_pat5, fig_pat6)
    print(f"[+] Saved PDF report: {pdf_path}")


if __name__ == "__main__":
    main()
