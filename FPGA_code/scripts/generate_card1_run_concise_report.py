#!/home/olle/anaconda3/bin/python
"""
generate_card1_run_concise_report.py
====================================
Inverted MAML (Patent Pending SE 2630397-4) - Open Science Hardware

Parameterized concise 2-page report & multi-figure generator for every Card 1
2-beat bit-slicing thermal optimization run (R1, R2, R3, ...):
  - Page 1: Executive Summary, Cumulative Multi-Round Table, Phase-by-Phase
            Metrics, and 4-Panel Performance + Weight Envelope Timeline.
  - Page 2: Dedicated All-W(8) (7x6 MSB+LSB) & All-W(3) (8x6 MSB+LSB)
            Weight Dynamics Figure and Anti-Windup Assessment.
"""

from __future__ import annotations
import argparse
import json
import shutil
import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from FPGA_code.scripts.analog_hyperparam_model import (
    _fit_thermal_baseline,
    _pchip_eval,
    _rolling_mean,
    extract_warm_trend_metrics,
)

DEFAULT_COLD_JSON = REPO_ROOT / "FPGA_code" / "logs" / "bit_slicing" / "cold_verify_k1.json"
REL_DIR = REPO_ROOT / "FPGA_code" / "releases" / "Release_20261114_ModeA_Card1_BitSlicing_AntiWindup_Baseline_R1"
REL_RPT_DIR = REL_DIR / "reports_and_logs"
REL_FIG_DIR = REL_RPT_DIR / "figures"
DOCS_DIR = REPO_ROOT / "FPGA_code" / "docs"
DOCS_FIG_DIR = DOCS_DIR / "figures"
LOGS_DIR = REPO_ROOT / "FPGA_code" / "logs" / "bit_slicing"
ARTIFACT_DIR = Path("/home/olle/.gemini/antigravity/brain/fa59cd2e-8c8b-41e2-add0-77ffdf2fe431")

STAIRCASE_ROW6 = [-40, -24, -8, 8, 24, 40]
STAIRCASE_ROW7 = [40, 24, 8, -8, -24, -40]


def make_run_slug(meta: dict, round_num: int) -> tuple[str, str]:
    lr_str = f"{meta['lr']:.4g}".replace(".", "p")
    l2 = int(meta["l2_reg"])
    mom_str = f"{meta['momentum']:.2f}".replace(".", "p")
    clamp = int(meta.get("clamp_lsb", 75))
    prefix = f"r{round_num}dc_fix" if str(meta.get("dc_calib_mode", "")).startswith("LOCKED_R1") else f"r{round_num}"
    lower_tag = f"{prefix}_lr{lr_str}_l2_{l2}_mom{mom_str}_cl{clamp}"
    return lower_tag, f"{prefix.upper()}_LR{lr_str.upper()}_L2_{l2}_MOM{mom_str.upper()}_CL{clamp}"


def compute_phase_stats(data: dict, base_t: np.ndarray, base_e: np.ndarray, base_lnL: np.ndarray) -> list[dict]:
    meta = data["metadata"]
    hist = data["history"]
    stats = []
    for pi, p in enumerate(meta["phases"]):
        rows = [r for r in hist if r["phase_idx"] == pi]
        if not rows:
            continue
        n = len(rows)
        q_start = max(5, min(20, n // 5))
        q_late = int(0.65 * n)
        t_s = np.array([float(r["elapsed_s"]) for r in rows], dtype=np.float64)
        comb = np.array([float(r["combined_enob_raw"]) for r in rows], dtype=np.float64)
        msb = np.array([float(r["enob_msb"]) for r in rows], dtype=np.float64)
        lsb = np.array([float(r["enob_lsb"]) for r in rows], dtype=np.float64)
        loss_tot = np.array([float(r["loss_msb"]) + float(r["loss_lsb"]) for r in rows], dtype=np.float64)
        w8m_max = np.array([max(abs(r["w8_msb_range"][0]), abs(r["w8_msb_range"][1])) for r in rows], dtype=np.int32)
        w8l_max = np.array([max(abs(r["w8_lsb_range"][0]), abs(r["w8_lsb_range"][1])) for r in rows], dtype=np.int32)
        w3_max = np.array([
            max(
                abs(r.get("w3_msb_range", [0, 0])[0]), abs(r.get("w3_msb_range", [0, 0])[1]),
                abs(r.get("w3_lsb_range", [0, 0])[0]), abs(r.get("w3_lsb_range", [0, 0])[1]),
            )
            for r in rows
        ], dtype=np.int32)
        w8_nz = sum(1 for r in rows if r["w8_msb_range"] != [0, 0] or r["w8_lsb_range"] != [0, 0])

        detr_late = None
        loss_ratio_late = None
        if p["heater"] and len(base_t) >= 2:
            eb = _pchip_eval(base_t, base_e, t_s)
            lb = np.exp(_pchip_eval(base_t, base_lnL, t_s))
            detr_late = float(np.mean(comb[q_late:] - eb[q_late:]))
            loss_ratio_late = float(np.exp(np.mean(np.log(np.maximum(1.0, lb[q_late:]) / np.maximum(1.0, loss_tot[q_late:])))))

        stats.append({
            "phase_num": pi + 1,
            "name": p["name"],
            "heater": p["heater"],
            "regler": p["regler"],
            "dur_min": p["dur_s"] / 60.0,
            "n_pairs": n,
            "comb_start": float(np.mean(comb[:q_start])),
            "comb_late": float(np.mean(comb[q_late:])),
            "comb_mean": float(np.mean(comb)),
            "msb_mean": float(np.mean(msb)),
            "lsb_mean": float(np.mean(lsb)),
            "loss_start": float(np.mean(loss_tot[:q_start])),
            "loss_late": float(np.mean(loss_tot[q_late:])),
            "detr_late_b": detr_late,
            "detr_loss_ratio": loss_ratio_late,
            "w8_msb_pk": int(np.max(w8m_max)),
            "w8_lsb_pk": int(np.max(w8l_max)),
            "w3_pk": int(np.max(w3_max)),
            "w8_nz": w8_nz,
        })
    return stats


def _shade_phases(ax, phases):
    acc = 0.0
    for p in phases:
        t0 = acc / 60.0
        t1 = (acc + p["dur_s"]) / 60.0
        acc += p["dur_s"]
        if not p["heater"]:
            col, al = ("#dbeafe", 0.40) if p["regler"] else ("#e0e7ff", 0.25)
        else:
            col, al = ("#dcfce7", 0.45) if p["regler"] else ("#fee2e2", 0.40)
        ax.axvspan(t0, t1, color=col, alpha=al, zorder=0)
        ax.axvline(t0, color="#94a3b8", linestyle="--", linewidth=0.75, zorder=1)


def generate_timeline_figure(
    data: dict, base_t: np.ndarray, base_e: np.ndarray, base_lnL: np.ndarray,
    fig_out: Path, round_num: int
) -> None:
    hist = data["history"]
    meta = data["metadata"]
    phases = meta["phases"]
    clamp = int(meta.get("clamp_lsb", 75))
    w3_cap = max(15, clamp // 3)

    t_s = np.array([float(r["elapsed_s"]) for r in hist], dtype=np.float64)
    t_min = t_s / 60.0
    comb = np.array([float(r["combined_enob_raw"]) for r in hist], dtype=np.float64)
    msb = np.array([float(r["enob_msb"]) for r in hist], dtype=np.float64)
    lsb = np.array([float(r["enob_lsb"]) for r in hist], dtype=np.float64)
    loss_tot = np.array([float(r["loss_msb"]) + float(r["loss_lsb"]) for r in hist], dtype=np.float64)

    comb_sm = _rolling_mean(comb, win=21)
    loss_sm = _rolling_mean(loss_tot, win=21)

    heat_mask = np.array([bool(r.get("heater_on", False)) for r in hist])
    eb_curve = _pchip_eval(base_t, base_e, t_s[heat_mask]) if len(base_t) >= 2 and np.any(heat_mask) else None
    lb_curve = np.exp(_pchip_eval(base_t, base_lnL, t_s[heat_mask])) if len(base_t) >= 2 and np.any(heat_mask) else None

    w8m_min = np.array([r["w8_msb_range"][0] for r in hist])
    w8m_max = np.array([r["w8_msb_range"][1] for r in hist])
    w8l_min = np.array([r["w8_lsb_range"][0] for r in hist])
    w8l_max = np.array([r["w8_lsb_range"][1] for r in hist])
    w3m_min = np.array([r["w3_msb_range"][0] for r in hist])
    w3m_max = np.array([r["w3_msb_range"][1] for r in hist])
    w3l_min = np.array([r["w3_lsb_range"][0] for r in hist])
    w3l_max = np.array([r["w3_lsb_range"][1] for r in hist])

    fig, axes = plt.subplots(4, 1, figsize=(11.2, 9.6), sharex=True, gridspec_kw={"height_ratios": [1.35, 0.95, 0.95, 0.85]})
    fig.patch.set_facecolor("white")

    # Panel 1: ENOB + PCHIP thermal drift baseline E_base(t)
    ax = axes[0]
    _shade_phases(ax, phases)
    ax.plot(t_min, comb, color="#7dd3fc", linewidth=0.55, alpha=0.55, label="Raw Combined ENOB")
    ax.plot(t_min, comb_sm, color="#0369a1", linewidth=2.0, label="21-Pair Mean Combined ENOB")
    ax.plot(t_min, msb, color="#16a34a", linewidth=0.65, alpha=0.42, label="MSB Slice")
    ax.plot(t_min, lsb, color="#ea580c", linewidth=0.65, alpha=0.42, label="LSB Slice")
    if eb_curve is not None:
        ax.plot(t_min[heat_mask], eb_curve, color="#dc2626", linestyle="--", linewidth=1.9, label="Thermal Baseline E_base(t)")
        ax.fill_between(
            t_min[heat_mask], eb_curve, comb_sm[heat_mask],
            where=(comb_sm[heat_mask] >= eb_curve),
            color="#22c55e", alpha=0.18, interpolate=True, label="Closed-Loop Gain > E_base(t)"
        )
    ax.axhline(8.0, color="#d97706", linestyle=":", linewidth=1.2, label="8.0-bit Target")
    ax.set_ylabel("ENOB (b)", fontsize=9.5, fontweight="bold")
    ax.set_ylim(2.8, 9.95)
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.legend(loc="lower left", fontsize=7.5, ncol=3, framealpha=0.92)
    ax.set_title(
        f"Card 1 Round {round_num} Bit-Slicing ({meta['heater_duty_pct']:.0f}% PWM, K={meta['k_batch']}, "
        f"LR={meta['lr']}, L2={meta['l2_reg']}, Mom={meta['momentum']}, Clamp=±{clamp} LSB)",
        fontsize=10.8, fontweight="bold"
    )
    acc = 0.0
    for pi, p in enumerate(phases):
        t_mid = (acc + 0.5 * p["dur_s"]) / 60.0
        acc += p["dur_s"]
        lbl = f"P{pi+1} ({'ON' if p['regler'] else 'OFF'})"
        ax.text(t_mid, 9.75, lbl, ha="center", va="top", fontsize=7.8, fontweight="bold",
                color="#15803d" if p["regler"] else "#b91c1c")

    # Panel 2: Combined Loss + L_base(t)
    ax = axes[1]
    _shade_phases(ax, phases)
    ax.plot(t_min, loss_tot, color="#94a3b8", linewidth=0.5, alpha=0.45, label="Raw Loss (MSB+LSB)")
    ax.plot(t_min, loss_sm, color="#0f172a", linewidth=1.8, label="21-Pair Mean Loss (LSB²)")
    if lb_curve is not None:
        ax.plot(t_min[heat_mask], lb_curve, color="#dc2626", linestyle="--", linewidth=1.8, label="Thermal Baseline L_base(t)")
    ax.set_ylabel("Loss (LSB²)", fontsize=9.5, fontweight="bold")
    ax.set_ylim(0, max(75000.0, float(np.percentile(loss_sm, 99.5) * 1.12)))
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.legend(loc="upper left", fontsize=7.8, framealpha=0.92)

    # Panel 3: W8 MSB & LSB Envelope
    ax = axes[2]
    _shade_phases(ax, phases)
    ax.fill_between(t_min, w8m_min, w8m_max, color="#16a34a", alpha=0.14)
    ax.fill_between(t_min, w8l_min, w8l_max, color="#ea580c", alpha=0.12)
    ax.plot(t_min, w8m_max, color="#15803d", linewidth=1.15, label="W8 MSB [min, max]")
    ax.plot(t_min, w8m_min, color="#15803d", linewidth=1.15, linestyle="--")
    ax.plot(t_min, w8l_max, color="#c2410c", linewidth=1.15, label="W8 LSB [min, max]")
    ax.plot(t_min, w8l_min, color="#c2410c", linewidth=1.15, linestyle="--")
    ax.axhline(clamp, color="#dc2626", linestyle=":", linewidth=1.2, label=f"W8 Clamp (±{clamp} LSB)")
    ax.axhline(-clamp, color="#dc2626", linestyle=":", linewidth=1.2)
    ax.axhline(0, color="#64748b", linewidth=0.6, alpha=0.6)
    ax.set_ylabel("W(8) (LSB)", fontsize=9.5, fontweight="bold")
    ax.set_ylim(-clamp - 12, clamp + 12)
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.legend(loc="lower left", fontsize=7.6, ncol=3, framealpha=0.92)

    # Panel 4: W3 MSB & LSB Active Data Envelope + Clock Rails
    ax = axes[3]
    _shade_phases(ax, phases)
    ax.fill_between(t_min, w3m_min, w3m_max, color="#7c3aed", alpha=0.18, label="W3 MSB Rows 0–5 [min, max]")
    ax.fill_between(t_min, w3l_min, w3l_max, color="#0284c7", alpha=0.14, label="W3 LSB Rows 0–5 [min, max]")
    ax.plot(t_min, w3m_max, color="#6d28d9", linewidth=1.1)
    ax.plot(t_min, w3m_min, color="#6d28d9", linewidth=1.1, linestyle="--")
    ax.plot(t_min, w3l_max, color="#0369a1", linewidth=1.0)
    ax.plot(t_min, w3l_min, color="#0369a1", linewidth=1.0, linestyle="--")
    ax.axhline(w3_cap, color="#9333ea", linestyle=":", linewidth=1.2, label=f"W3 Data Cap (±{w3_cap} LSB)")
    ax.axhline(-w3_cap, color="#9333ea", linestyle=":", linewidth=1.2)
    ax.axhline(40, color="#475569", linestyle="-.", linewidth=0.9, label="Frozen W3 Clock Rows 6–7 (±40 LSB)")
    ax.axhline(-40, color="#475569", linestyle="-.", linewidth=0.9)
    ax.set_ylabel("W(3) (LSB)", fontsize=9.5, fontweight="bold")
    ax.set_xlabel("Elapsed Time (minutes)", fontsize=9.8, fontweight="bold")
    ax.set_ylim(-48, 48)
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.legend(loc="lower left", fontsize=7.3, ncol=2, framealpha=0.92)

    plt.tight_layout()
    fig_out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(fig_out, dpi=180)
    plt.close(fig)


def generate_all_weights_figure(data: dict, fig_out: Path, round_num: int) -> bool:
    """
    Plots ALL W(8) (7x6 MSB & 7x6 LSB) and ALL W(3) (8x6 MSB & 8x6 LSB) weights.
    Returns True if full 180 individual weight trajectories were plotted, False if envelope mode.
    """
    hist = data["history"]
    meta = data["metadata"]
    phases = meta["phases"]
    clamp = int(meta.get("clamp_lsb", 75))
    w3_cap = max(15, clamp // 3)
    t_min = np.array([float(r["elapsed_s"]) for r in hist], dtype=np.float64) / 60.0

    has_full = ("w8_msb" in hist[0] and "w3_msb" in hist[0])

    if has_full:
        w8m = np.array([r["w8_msb"] for r in hist], dtype=np.int16)  # (N, 7, 6)
        w8l = np.array([r["w8_lsb"] for r in hist], dtype=np.int16)  # (N, 7, 6)
        w3m = np.array([r["w3_msb"] for r in hist], dtype=np.int16)  # (N, 8, 6)
        w3l = np.array([r["w3_lsb"] for r in hist], dtype=np.int16)  # (N, 8, 6)

        row_colors_7 = ["#dc2626", "#ea580c", "#ca8a04", "#16a34a", "#0284c7", "#4f46e5", "#9333ea"]
        fig, axes = plt.subplots(4, 6, figsize=(15.5, 10.2), sharex=True, gridspec_kw={"hspace": 0.28, "wspace": 0.16})
        fig.patch.set_facecolor("white")

        for col in range(6):
            # Row 0: W(8) MSB 7 rows
            ax = axes[0, col]
            _shade_phases(ax, phases)
            for r in range(7):
                ax.plot(t_min, w8m[:, r, col], color=row_colors_7[r], linewidth=0.9, label=f"r{r}" if col == 0 else None)
            ax.axhline(clamp, color="#ef4444", linestyle=":", linewidth=0.8)
            ax.axhline(-clamp, color="#ef4444", linestyle=":", linewidth=0.8)
            ax.set_ylim(-clamp - 8, clamp + 8)
            ax.set_title(f"W8 MSB Col {col}", fontsize=8.8, fontweight="bold")
            ax.grid(True, linestyle=":", alpha=0.45)
            if col == 0:
                ax.set_ylabel("W8 MSB (LSB)", fontsize=8.5, fontweight="bold")
                ax.legend(loc="upper left", fontsize=6.0, ncol=4, framealpha=0.85)

            # Row 1: W(8) LSB 7 rows
            ax = axes[1, col]
            _shade_phases(ax, phases)
            for r in range(7):
                ax.plot(t_min, w8l[:, r, col], color=row_colors_7[r], linewidth=0.9)
            ax.axhline(clamp, color="#ef4444", linestyle=":", linewidth=0.8)
            ax.axhline(-clamp, color="#ef4444", linestyle=":", linewidth=0.8)
            ax.set_ylim(-clamp - 8, clamp + 8)
            ax.set_title(f"W8 LSB Col {col}", fontsize=8.8, fontweight="bold")
            ax.grid(True, linestyle=":", alpha=0.45)
            if col == 0:
                ax.set_ylabel("W8 LSB (LSB)", fontsize=8.5, fontweight="bold")

            # Row 2: W(3) MSB 8 rows (0..5 active + 6..7 staircases)
            ax = axes[2, col]
            _shade_phases(ax, phases)
            for r in range(6):
                ax.plot(t_min, w3m[:, r, col], color=row_colors_7[r], linewidth=0.9, label=f"r{r}" if col == 0 else None)
            ax.plot(t_min, w3m[:, 6, col], color="#0f172a", linewidth=1.25, linestyle="--", label="clk6" if col == 0 else None)
            ax.plot(t_min, w3m[:, 7, col], color="#64748b", linewidth=1.25, linestyle="-.", label="clk7" if col == 0 else None)
            ax.axhline(w3_cap, color="#9333ea", linestyle=":", linewidth=0.8)
            ax.axhline(-w3_cap, color="#9333ea", linestyle=":", linewidth=0.8)
            ax.set_ylim(-48, 48)
            ax.set_title(f"W3 MSB Col {col}", fontsize=8.8, fontweight="bold")
            ax.grid(True, linestyle=":", alpha=0.45)
            if col == 0:
                ax.set_ylabel("W3 MSB (LSB)", fontsize=8.5, fontweight="bold")
                ax.legend(loc="lower left", fontsize=5.8, ncol=4, framealpha=0.85)

            # Row 3: W(3) LSB 8 rows
            ax = axes[3, col]
            _shade_phases(ax, phases)
            for r in range(6):
                ax.plot(t_min, w3l[:, r, col], color=row_colors_7[r], linewidth=0.9)
            ax.plot(t_min, w3l[:, 6, col], color="#0f172a", linewidth=1.25, linestyle="--")
            ax.plot(t_min, w3l[:, 7, col], color="#64748b", linewidth=1.25, linestyle="-.")
            ax.axhline(w3_cap, color="#9333ea", linestyle=":", linewidth=0.8)
            ax.axhline(-w3_cap, color="#9333ea", linestyle=":", linewidth=0.8)
            ax.set_ylim(-48, 48)
            ax.set_title(f"W3 LSB Col {col}", fontsize=8.8, fontweight="bold")
            ax.set_xlabel("Time (m)", fontsize=8.0)
            ax.grid(True, linestyle=":", alpha=0.45)
            if col == 0:
                ax.set_ylabel("W3 LSB (LSB)", fontsize=8.5, fontweight="bold")

        fig.suptitle(
            f"Round {round_num} Full Hardware Weight Telemetry: ALL 84 W(8) [7x6 MSB+LSB] & ALL 96 W(3) [8x6 MSB+LSB] Synapses",
            fontsize=11.5, fontweight="bold", y=0.992
        )
        fig_out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(fig_out, dpi=180, bbox_inches="tight")
        plt.close(fig)
        return True

    # Fallback for R1-R3 JSONs where per-pair matrices weren't stored (only bank ranges + frozen staircase)
    w8m_min = np.array([r["w8_msb_range"][0] for r in hist])
    w8m_max = np.array([r["w8_msb_range"][1] for r in hist])
    w8l_min = np.array([r["w8_lsb_range"][0] for r in hist])
    w8l_max = np.array([r["w8_lsb_range"][1] for r in hist])
    w3m_min = np.array([r["w3_msb_range"][0] for r in hist])
    w3m_max = np.array([r["w3_msb_range"][1] for r in hist])
    w3l_min = np.array([r["w3_lsb_range"][0] for r in hist])
    w3l_max = np.array([r["w3_lsb_range"][1] for r in hist])
    clip_m = np.array([int(r.get("clip_msb", 0)) for r in hist])
    clip_l = np.array([int(r.get("clip_lsb", 0)) for r in hist])

    fig, axes = plt.subplots(2, 2, figsize=(12.2, 7.6), gridspec_kw={"hspace": 0.30, "wspace": 0.22})
    fig.patch.set_facecolor("white")

    # (0,0) W(8) MSB 7x6
    ax = axes[0, 0]
    _shade_phases(ax, phases)
    ax.fill_between(t_min, w8m_min, w8m_max, color="#16a34a", alpha=0.22, label="W8 MSB [min, max] (42 weights)")
    ax.plot(t_min, w8m_max, color="#15803d", linewidth=1.2, label="Max (+)")
    ax.plot(t_min, w8m_min, color="#166534", linewidth=1.2, linestyle="--", label="Min (-)")
    ax.axhline(clamp, color="#dc2626", linestyle=":", linewidth=1.2, label=f"Clamp ±{clamp}")
    ax.axhline(-clamp, color="#dc2626", linestyle=":", linewidth=1.2)
    ax.set_title("W(8) MSB Bank (7 rows × 6 cols = 42 Synapses)", fontsize=9.8, fontweight="bold")
    ax.set_ylabel("Weight (LSB)", fontsize=9.0, fontweight="bold")
    ax.set_ylim(-clamp - 12, clamp + 12)
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.legend(loc="lower left", fontsize=7.5, framealpha=0.9)

    # (0,1) W(8) LSB 7x6
    ax = axes[0, 1]
    _shade_phases(ax, phases)
    ax.fill_between(t_min, w8l_min, w8l_max, color="#ea580c", alpha=0.22, label="W8 LSB [min, max] (42 weights)")
    ax.plot(t_min, w8l_max, color="#c2410c", linewidth=1.2, label="Max (+)")
    ax.plot(t_min, w8l_min, color="#9a3412", linewidth=1.2, linestyle="--", label="Min (-)")
    ax.axhline(clamp, color="#dc2626", linestyle=":", linewidth=1.2, label=f"Clamp ±{clamp}")
    ax.axhline(-clamp, color="#dc2626", linestyle=":", linewidth=1.2)
    ax.set_title("W(8) LSB Bank (7 rows × 6 cols = 42 Synapses)", fontsize=9.8, fontweight="bold")
    ax.set_ylim(-clamp - 12, clamp + 12)
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.legend(loc="lower left", fontsize=7.5, framealpha=0.9)

    # (1,0) W(3) Active Data Rows 0..5 MSB & LSB
    ax = axes[1, 0]
    _shade_phases(ax, phases)
    ax.fill_between(t_min, w3m_min, w3m_max, color="#7c3aed", alpha=0.22, label="W3 MSB Rows 0–5 (36 weights)")
    ax.fill_between(t_min, w3l_min, w3l_max, color="#0284c7", alpha=0.18, label="W3 LSB Rows 0–5 (36 weights)")
    ax.plot(t_min, w3m_max, color="#6d28d9", linewidth=1.1)
    ax.plot(t_min, w3m_min, color="#6d28d9", linewidth=1.1, linestyle="--")
    ax.plot(t_min, w3l_max, color="#0369a1", linewidth=1.1)
    ax.plot(t_min, w3l_min, color="#0369a1", linewidth=1.1, linestyle="--")
    ax.axhline(w3_cap, color="#9333ea", linestyle=":", linewidth=1.2, label=f"M3 Cap ±{w3_cap}")
    ax.axhline(-w3_cap, color="#9333ea", linestyle=":", linewidth=1.2)
    ax.set_title("W(3) Active Data Rows 0–5 (MSB + LSB = 72 Synapses)", fontsize=9.8, fontweight="bold")
    ax.set_ylabel("Weight (LSB)", fontsize=9.0, fontweight="bold")
    ax.set_xlabel("Elapsed Time (minutes)", fontsize=9.2, fontweight="bold")
    ax.set_ylim(-w3_cap - 10, w3_cap + 10)
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.legend(loc="lower left", fontsize=7.5, framealpha=0.9)

    # (1,1) Frozen W(3) Clock Staircases (Rows 6..7) + Anti-Windup Clip Activity
    ax = axes[1, 1]
    cols_idx = np.arange(6)
    ax.plot(cols_idx, STAIRCASE_ROW6, "o-", color="#0f172a", linewidth=2.0, markersize=7, label="W3 Row 6 Clock [-40..+40]")
    ax.plot(cols_idx, STAIRCASE_ROW7, "s--", color="#0284c7", linewidth=2.0, markersize=7, label="W3 Row 7 Clock [+40..-40]")
    ax.axhline(0, color="#94a3b8", linewidth=0.7)
    ax.set_xticks(cols_idx)
    ax.set_xticklabels([f"Col {c}" for c in range(6)])
    ax.set_ylim(-48, 48)
    ax.set_ylabel("Frozen Weight (LSB)", fontsize=9.0, fontweight="bold")
    ax.set_xlabel("Physical ColTIA Column (0..5)", fontsize=9.2, fontweight="bold")
    ax.set_title(
        f"W(3) Frozen Clock Staircases (24 Weights) & Clip Counts (M={int(clip_m[-1])}, L={int(clip_l[-1])})",
        fontsize=9.8, fontweight="bold"
    )
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.legend(loc="lower right", fontsize=7.6, framealpha=0.9)

    fig.suptitle(
        f"Round {round_num} W(8) & W(3) Bank Coverage (84 W8 + 96 W3 Synapses; Clamp=±{clamp}, M3 Cap=±{w3_cap})",
        fontsize=11.0, fontweight="bold", y=0.99
    )
    fig_out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(fig_out, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return False


def collect_round_summary(all_log_paths: list[Path]) -> list[dict]:
    rows = []
    for idx, p in enumerate(all_log_paths, start=1):
        with open(p) as f:
            d = json.load(f)
        m = d["metadata"]
        tr_info = extract_warm_trend_metrics(str(p))
        tr = tr_info["trends"]
        rows.append({
            "round": idx,
            "label": f"R{idx}dc_fix" if ("dc_fix" in p.name or str(m.get("dc_calib_mode", "")).startswith("LOCKED_R1")) else f"R{idx}",
            "file": p.name,
            "lr": m["lr"],
            "l2": int(m["l2_reg"]),
            "mom": m["momentum"],
            "clamp": int(m.get("clamp_lsb", 75)),
            "lift": tr["warm_step_lift_b"],
            "loss_r": tr["warm_loss_ratio"],
            "climb": tr["hot_conv_climb_b"],
            "jitt": tr["jitter_std"],
            "recov": tr["recovery_rate"],
            "score": tr_info["score"],
        })
    return rows


def write_markdown(
    round_num: int, slug_upper: str, stats: list[dict], meta: dict, trend_info: dict,
    cold_stats: list[dict], all_rows: list[dict], has_full_w: bool,
    md_path: Path, fig1_ref: str, fig2_ref: str, json_name: str
) -> None:
    tr = trend_info["trends"]
    best_row = max(all_rows, key=lambda r: r["score"])
    lines = [
        f"# Inverted MAML Card 1: Round {round_num} Thermal Bit-Slicing Report ({slug_upper})",
        "",
        "**Hardware:** Card 1 (`Trion T120F324` Master SoC + `Trion T20F256` Coprocessor, `1k / 2.2k` Passive Attenuator)  ",
        "**Firmware:** `T120_SOC_ETH_FW v2.2-MAML (SW Build Nov 14 2026 10:15:16)`, `HW_LOGIC: 0x20261030`  ",
        f"**Dataset:** `FPGA_code/logs/bit_slicing/{json_name}` (`{sum(s['n_pairs'] for s in stats):,}` pairs)  ",
        f"**Hyperparameters:** `Heater = {meta['heater_duty_pct']:.0f}%` PWM, `K = {meta['k_batch']}`, `LR = {meta['lr']}`, `L2 = {meta['l2_reg']}`, `Momentum = {meta['momentum']}`, `Clamp = ±{meta.get('clamp_lsb', 75)} LSB`  ",
        "",
        "---",
        "",
        "## 1. Executive Summary & Verification Milestones",
        "",
        f"1. **Cold Reference Without Heating (`cold_verify_k1.json`):** `Cold / Regler ON` mean **{cold_stats[0]['comb_mean']:.2f} b** (`min {cold_stats[0]['comb_min']:.2f} b`), `Cold / Regler OFF` mean **{cold_stats[1]['comb_mean']:.2f} b** (`min {cold_stats[1]['comb_min']:.2f} b`).",
        f"2. **Thermal-Detrended Closed-Loop Performance (Round {round_num}):** Weighted detrended `Warm ON` lift **`{tr['warm_step_lift_b']:+.2f} b`**, loss reduction ratio **`{tr['warm_loss_ratio']:.2f}x`**, detrended convergence climb **`{tr['hot_conv_climb_b']:+.2f} b`**, jitter **`{tr['jitter_std']:.2f} b`**, anti-windup recovery **`{tr['recovery_rate']:.2f}`**, composite score **`{trend_info['score']:+.3f}`**.",
        f"3. **Cumulative Best Across R1–R{len(all_rows)}:** Round {best_row['round']} (`LR={best_row['lr']}, L2={best_row['l2']}, Mom={best_row['mom']}, Clamp=±{best_row['clamp']}`) with score **`{best_row['score']:+.3f}`**.",
        "",
        "---",
        "",
        f"## 2. Cumulative Multi-Round Optimization Comparison (R1–R{len(all_rows)})",
        "",
        "| Round | LR | L2 Reg | Mom | Clamp | Lift vs E_base | Loss Ratio | Hot Climb | Jitter | Recovery | Composite Score |",
        "| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]
    for r in all_rows:
        star = " ★" if r["round"] == best_row["round"] else ""
        lines.append(
            f"| {r['label']}{star} | `{r['lr']}` | `{r['l2']}` | `{r['mom']}` | `±{r['clamp']}` | "
            f"`{r['lift']:+.2f} b` | `{r['loss_r']:.2f}x` | `{r['climb']:+.2f} b` | `{r['jitt']:.2f} b` | `{r['recov']:.2f}` | **`{r['score']:+.3f}`** |"
        )

    lines += [
        "",
        f"## 3. Round {round_num} Phase-by-Phase Telemetry",
        "",
        "| Phase | Regime | Pairs | Comb ENOB (`Start -> Late`, Mean) | Δ vs E_base | Total Loss (`Start -> Late`) | Loss Ratio | W8 Peak `[M, L]` | W3 Peak | W8 nz |",
        "| :--- | :--- | ---: | :---: | :---: | :---: | :---: | :---: | :---: | ---: |",
    ]
    for s in stats:
        d_str = f"**{s['detr_late_b']:+.2f} b**" if s["detr_late_b"] is not None else "—"
        lr_str = f"**{s['detr_loss_ratio']:.2f}x**" if s["detr_loss_ratio"] is not None else "—"
        lines.append(
            f"| P{s['phase_num']} | {s['name'].replace('Phase ' + str(s['phase_num']) + ': ', '')} | "
            f"{s['n_pairs']} | `{s['comb_start']:.2f} -> {s['comb_late']:.2f}` (**{s['comb_mean']:.2f} b**) | "
            f"{d_str} | `{s['loss_start']:.0f} -> {s['loss_late']:.0f}` | {lr_str} | "
            f"`[{s['w8_msb_pk']}, {s['w8_lsb_pk']}]` | `{s['w3_pk']}` | `{s['w8_nz']}` |"
        )

    w_note = (
        "All **84 `W(8)`** (`7x6` MSB + `7x6` LSB) and **96 `W(3)`** (`8x6` MSB + `8x6` LSB) individual weights plotted across all pairs."
        if has_full_w
        else "Bank `[min, max]` excursion envelopes across `W(8)` (84 synapses) and `W(3)` (72 active + 24 frozen staircase synapses)."
    )
    lines += [
        "",
        "## 4. Empirical Graphs: Performance Timeline & Full W(8) / W(3) Weights",
        "",
        f"![Round {round_num} Performance & Weight Envelope Timeline]({fig1_ref})",
        "",
        f"**Weight Coverage:** {w_note}",
        "",
        f"![Round {round_num} All W(8) and W(3) Weights]({fig2_ref})",
        "",
    ]
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(lines))


def build_pdf(
    round_num: int, slug_upper: str, stats: list[dict], meta: dict, trend_info: dict,
    cold_stats: list[dict], all_rows: list[dict], has_full_w: bool,
    fig1_path: Path, fig2_path: Path, pdf_out: Path
) -> None:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable, PageBreak
    )
    from reportlab.pdfgen import canvas

    class NumberedCanvas(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._saved_page_states = []

        def showPage(self):
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            num_pages = len(self._saved_page_states)
            for state in self._saved_page_states:
                self.__dict__.update(state)
                self.draw_decorations(num_pages)
                super().showPage()
            super().save()

        def draw_decorations(self, page_count):
            self.saveState()
            self.setFont("Helvetica", 7.8)
            self.setFillColor(colors.HexColor("#64748b"))
            self.line(40, 36, 572, 36)
            self.drawString(40, 24, f"INVERTED MAML (SE 2630397-4) | Card 1 Round {round_num} Concise Report ({slug_upper})")
            self.drawRightString(572, 24, f"Page {self._pageNumber} of {page_count}")
            self.restoreState()

    styles = getSampleStyleSheet()
    title_s = ParagraphStyle("T", parent=styles["Heading1"], fontSize=13.5, leading=16.5, textColor=colors.HexColor("#0f172a"), spaceAfter=2)
    sub_s = ParagraphStyle("Sub", parent=styles["Normal"], fontSize=8.3, leading=11.0, textColor=colors.HexColor("#475569"), spaceAfter=6)
    h2_s = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=10.2, leading=13, textColor=colors.HexColor("#0369a1"), spaceBefore=5, spaceAfter=3)
    body_s = ParagraphStyle("B", parent=styles["Normal"], fontSize=8.3, leading=11.4, textColor=colors.HexColor("#1e293b"), spaceAfter=3)
    bul_s = ParagraphStyle("Bul", parent=body_s, leftIndent=10, bulletIndent=2, spaceAfter=2.0)

    tr = trend_info["trends"]
    best_row = max(all_rows, key=lambda r: r["score"])
    clamp = int(meta.get("clamp_lsb", 75))
    doc = SimpleDocTemplate(str(pdf_out), pagesize=letter, leftMargin=40, rightMargin=40, topMargin=34, bottomMargin=42)

    story = [
        Paragraph(f"Inverted MAML Card 1: Round {round_num} Thermal Bit-Slicing Report", title_s),
        Paragraph(
            f"<b>Hardware:</b> Card 1 (T120+T20, 1k/2.2k) &nbsp;|&nbsp; "
            f"<b>FW:</b> v2.2-MAML (0x20261030) &nbsp;|&nbsp; "
            f"<b>Params:</b> {meta['heater_duty_pct']:.0f}% PWM, K={meta['k_batch']}, LR={meta['lr']}, L2={meta['l2_reg']}, Mom={meta['momentum']}, Clamp=±{clamp} LSB",
            sub_s,
        ),
        HRFlowable(width="100%", thickness=0.9, color=colors.HexColor("#cbd5e1")),
        Spacer(1, 4),
        Paragraph(f"1. Round {round_num} Summary & Cumulative Comparison (R1–R{len(all_rows)})", h2_s),
        Paragraph(
            f"&bull; <b>Cold Verification:</b> Phase 1 ON = <b>{cold_stats[0]['comb_mean']:.2f} b</b>, Phase 2 OFF = <b>{cold_stats[1]['comb_mean']:.2f} b</b> (W8=0 strictly).",
            bul_s,
        ),
        Paragraph(
            f"&bull; <b>Round {round_num} Detrended Trend Metrics:</b> Lift vs E_base = <b>{tr['warm_step_lift_b']:+.2f} b</b>, "
            f"Loss Ratio = <b>{tr['warm_loss_ratio']:.2f}x</b>, Climb = <b>{tr['hot_conv_climb_b']:+.2f} b</b>, "
            f"Jitter = <b>{tr['jitter_std']:.2f} b</b>, Recovery = <b>{tr['recovery_rate']:.2f}</b>, Score = <b>{trend_info['score']:+.3f}</b>.",
            bul_s,
        ),
    ]

    # Cumulative Table (last up to 8 rounds to always fit Page 1 neatly)
    show_rows = all_rows[-8:]
    c_data = [["Rnd", "LR", "L2", "Mom", "Clamp", "Lift", "LossR", "Climb", "Jitt", "Recov", "Score"]]
    for r in show_rows:
        star = "*" if r["round"] == best_row["round"] else ""
        c_data.append([
            f"{r['label']}{star}", f"{r['lr']}", f"{r['l2']}", f"{r['mom']}", f"±{r['clamp']}",
            f"{r['lift']:+.2f}b", f"{r['loss_r']:.2f}x", f"{r['climb']:+.2f}b", f"{r['jitt']:.2f}b",
            f"{r['recov']:.2f}", f"{r['score']:+.3f}",
        ])
    c_tbl = Table(c_data, colWidths=[46, 40, 36, 34, 38, 46, 42, 50, 40, 40, 52])
    c_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.2),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    story.append(c_tbl)
    story.append(Paragraph(f"2. Phase-by-Phase Telemetry ({sum(s['n_pairs'] for s in stats):,} Pairs)", h2_s))

    tdata = [["Phase", "Regime", "N", "Start->Late (Mean)", "Δ vs E_base", "Loss Start->Late", "W8 Pk [M,L]", "W3 Pk", "W8 nz"]]
    for s in stats:
        d_str = f"{s['detr_late_b']:+.2f} b" if s["detr_late_b"] is not None else "-"
        tdata.append([
            f"P{s['phase_num']}",
            s["name"].replace(f"Phase {s['phase_num']}: ", ""),
            str(s["n_pairs"]),
            f"{s['comb_start']:.2f}->{s['comb_late']:.2f} ({s['comb_mean']:.2f}b)",
            d_str,
            f"{s['loss_start']:.0f}->{s['loss_late']:.0f}",
            f"[{s['w8_msb_pk']},{s['w8_lsb_pk']}]",
            str(s["w3_pk"]),
            str(s["w8_nz"]),
        ])
    tbl = Table(tdata, colWidths=[26, 92, 30, 96, 48, 86, 52, 32, 34])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.2),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
        ("ALIGN", (2, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 5))
    from PIL import Image as PILImage

    def fit_image(img_p: Path, max_w: float, max_h: float) -> Image:
        with PILImage.open(img_p) as im:
            iw, ih = im.size
        scale = min(max_w / iw, max_h / ih)
        return Image(str(img_p), width=iw * scale, height=ih * scale)

    p1_max_h = max(280, 365 - 11 * len(show_rows))
    story.append(fit_image(fig1_path, 524, p1_max_h))

    # Page 2: All W(8) and W(3) Weights
    story.append(PageBreak())
    story.append(Paragraph(f"3. All W(8) (7x6 MSB+LSB) & W(3) (8x6 MSB+LSB) Weight Dynamics — Round {round_num}", h2_s))
    if has_full_w:
        story.append(Paragraph(
            f"&bull; <b>Full 180-Synapse Per-Pair Capture:</b> Every individual weight in <b>Matrix 8 MSB (42 weights)</b>, "
            f"<b>Matrix 8 LSB (42 weights)</b>, <b>Matrix 3 MSB (36 active + 12 clock)</b>, and <b>Matrix 3 LSB (36 active + 12 clock)</b> "
            f"is plotted below across all columns `Col 0..5`. W(8) enforces anti-windup clamping at ±{clamp} LSB, while W(3) rows 0–5 stay within ±{max(15, clamp//3)} LSB so rows 6–7 clock staircases remain locked at ±40 LSB.",
            bul_s,
        ))
        story.append(Spacer(1, 4))
        story.append(fit_image(fig2_path, 532, 605))
    else:
        story.append(Paragraph(
            f"&bull; <b>Full 84 W(8) + 96 W(3) Weight Coverage:</b> Displays the signed `[min, max]` excursion envelopes of all 42 `W(8) MSB`, "
            f"42 `W(8) LSB`, and 72 `W(3)` active data synapses (capped at ±{max(15, clamp//3)} LSB), plus the 24 frozen `W(3)` clock staircase weights "
            f"in rows 6–7 (`[-40..+40]` & `[+40..-40]` LSB). Full per-synapse 180-trace trajectories are logged natively from Round 4 onward.",
            bul_s,
        ))
        story.append(Spacer(1, 6))
        story.append(fit_image(fig2_path, 524, 360))

    doc.build(story, canvasmaker=NumberedCanvas)


def main():
    parser = argparse.ArgumentParser(description="Generate concise per-run report + All W(8)/W(3) weight plots")
    parser.add_argument("--round", type=int, required=True, help="Round number (e.g. 2, 3, 4...)")
    parser.add_argument("--json", type=Path, required=True, help="Path to run JSON file")
    parser.add_argument("--all-logs", type=Path, nargs="*", default=[], help="Ordered list of completed opt_r*.json files")
    parser.add_argument("--cold-json", type=Path, default=DEFAULT_COLD_JSON)
    args = parser.parse_args()

    run_json = args.json.resolve()
    with open(run_json) as f:
        data = json.load(f)
    with open(args.cold_json) as f:
        cold_data = json.load(f)

    cold_stats = []
    for pidx in [0, 1]:
        rows = [r for r in cold_data["history"] if r["phase_idx"] == pidx]
        vals = [float(r["combined_enob_raw"]) for r in rows]
        cold_stats.append({"comb_mean": float(np.mean(vals)), "comb_min": float(np.min(vals))})

    all_paths = [p.resolve() for p in args.all_logs] if args.all_logs else [run_json]
    all_rows = collect_round_summary(all_paths)

    meta = data["metadata"]
    lower_tag, upper_tag = make_run_slug(meta, args.round)
    fig1_name = f"fig_card1_{lower_tag}_thermal_slicing.png"
    fig2_name = f"fig_card1_{lower_tag}_w8_w3_all_weights.png"
    md_name = f"INVERTED_MAML_CARD1_{upper_tag}_THERMAL_SLICING_REPORT.md"
    pdf_name = f"INVERTED_MAML_CARD1_{upper_tag}_THERMAL_SLICING_REPORT.pdf"

    base_t, base_e, base_lnL = _fit_thermal_baseline(data["history"])
    stats = compute_phase_stats(data, base_t, base_e, base_lnL)
    trend_info = extract_warm_trend_metrics(str(run_json))

    fig1_rel = REL_FIG_DIR / fig1_name
    fig2_rel = REL_FIG_DIR / fig2_name
    generate_timeline_figure(data, base_t, base_e, base_lnL, fig1_rel, args.round)
    has_full_w = generate_all_weights_figure(data, fig2_rel, args.round)

    for src, name in [(fig1_rel, fig1_name), (fig2_rel, fig2_name)]:
        for dst_dir in (LOGS_DIR, ARTIFACT_DIR, DOCS_DIR, DOCS_FIG_DIR):
            dst_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst_dir / name)

    write_markdown(
        args.round, upper_tag, stats, meta, trend_info, cold_stats, all_rows, has_full_w,
        REL_RPT_DIR / md_name, f"figures/{fig1_name}", f"figures/{fig2_name}", run_json.name,
    )
    write_markdown(
        args.round, upper_tag, stats, meta, trend_info, cold_stats, all_rows, has_full_w,
        DOCS_DIR / md_name, f"figures/{fig1_name}", f"figures/{fig2_name}", run_json.name,
    )
    write_markdown(
        args.round, upper_tag, stats, meta, trend_info, cold_stats, all_rows, has_full_w,
        ARTIFACT_DIR / md_name, str(ARTIFACT_DIR / fig1_name), str(ARTIFACT_DIR / fig2_name), run_json.name,
    )

    build_pdf(
        args.round, upper_tag, stats, meta, trend_info, cold_stats, all_rows, has_full_w,
        fig1_rel, fig2_rel, REL_RPT_DIR / pdf_name,
    )
    shutil.copy2(REL_RPT_DIR / pdf_name, DOCS_DIR / pdf_name)
    shutil.copy2(REL_RPT_DIR / pdf_name, ARTIFACT_DIR / pdf_name)

    print(f"[+] Generated concise R{args.round} report ({'full 180-weight' if has_full_w else 'bank-envelope'}):")
    print(f"    PDF : {DOCS_DIR / pdf_name}")
    print(f"    MD  : {DOCS_DIR / md_name}")
    print(f"    Figs: {DOCS_FIG_DIR / fig1_name}, {DOCS_FIG_DIR / fig2_name}")


if __name__ == "__main__":
    main()
