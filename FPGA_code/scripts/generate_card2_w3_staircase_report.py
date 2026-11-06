#!/usr/bin/env python3
"""
generate_card2_w3_staircase_report.py
Inverted MAML (Patent Pending SE 2630397-4) - Open Science Hardware

Generates the comprehensive benchmark report, 2D spectrogram waterfall heatmap,
multi-strata timeline, and publication PDF for:
  Card 2 (1k/3.3k Attenuator) with W(3) Staircase Reference & Bias Cells ([-40..+40] LSB)
  Broadened Window [4.5..5.5 ms] under Uncorrelated White Noise.
"""

from __future__ import annotations
import sys
import json
import math
import shutil
import subprocess
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.cm as cm

from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, PageBreak, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfgen import canvas

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_PATH = REPO_ROOT / "FPGA_code" / "logs" / "mode_a_extended_training" / "mode_a_1000ep_broadened_4500to5500us_white_reg2048_lr0p02_swing40_var5_k1_1k_3p3k_w3staircase_ablation.json"
DOCS_DIR = REPO_ROOT / "FPGA_code" / "docs"
FIGURES_DIR = DOCS_DIR / "figures"
ARTIFACTS_DIR = Path("/home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a")

FIGURES_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

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
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        self.setLineWidth(0.5)
        self.setStrokeColor(colors.HexColor("#cbd5e1"))

        # Header (pages 2+)
        if self._pageNumber > 1:
            self.drawString(54, 755, "INVERTED MAML — Card 2 (1k/3.3k) W(3) Staircase Benchmark Report")
            self.drawRightString(558, 755, "Patent Pending SE 2630397-4")
            self.line(54, 747, 558, 747)

        # Footer (all pages)
        self.line(54, 45, 558, 45)
        self.drawString(54, 32, "Confidential — Inverted MAML Silicon Research (Card 2 Rev 2.0 Silicon)")
        self.drawRightString(558, 32, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()


def load_dataset(json_file: Path) -> dict:
    with open(json_file, "r") as f:
        return json.load(f)


def generate_spectrogram_heatmap(data: dict, out_path: Path):
    eps = data["epochs"]
    delays_us = data["metadata"]["strata_delays_us"]
    delays_ms = np.array(delays_us) / 1000.0

    matrix_enob = np.zeros((len(delays_us), len(eps)))
    for ep_idx, e in enumerate(eps):
        for s_idx in range(len(delays_us)):
            matrix_enob[s_idx, ep_idx] = e["strata_enobs"][s_idx]

    fig, ax = plt.subplots(figsize=(13, 6.5), dpi=200)
    im = ax.imshow(matrix_enob, aspect="auto", origin="lower", cmap="viridis",
                   extent=[0, len(eps) - 1, delays_ms[0], delays_ms[-1]],
                   vmin=np.percentile(matrix_enob, 2), vmax=np.percentile(matrix_enob, 98))

    cbar = fig.colorbar(im, ax=ax, pad=0.02, shrink=0.92)
    cbar.set_label("Measured Precision (ENOB Bits)", fontsize=11, fontweight="bold")
    cbar.ax.tick_params(labelsize=9)

    ax.axvline(x=100, color="white", linestyle="--", linewidth=1.5, alpha=0.9)
    ax.axvline(x=200, color="white", linestyle="--", linewidth=1.5, alpha=0.9)
    ax.axvline(x=600, color="red", linestyle="-", linewidth=2.0, alpha=0.95)

    ax.text(50, 5.43, "Phase 1: Staircase Base (LR=0)", color="white", fontsize=9, fontweight="bold", ha="center",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="#1e293b", alpha=0.75))
    ax.text(150, 5.43, "Phase 2: Train ON", color="white", fontsize=9, fontweight="bold", ha="center",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="#065f46", alpha=0.75))
    ax.text(400, 5.43, "Phase 3: Disturbance ±5 LSB", color="white", fontsize=9, fontweight="bold", ha="center",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="#92400e", alpha=0.75))
    ax.text(800, 5.43, "Phase 4: Ablation (LR=0)", color="white", fontsize=9, fontweight="bold", ha="center",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="#991b1b", alpha=0.75))

    ax.set_ylabel("Snapshot Sampling Delay (ms)", fontsize=11, fontweight="bold")
    ax.set_xlabel("Epoch (11 Online Updates/Epoch across 4.5..5.5 ms)", fontsize=11, fontweight="bold")
    ax.set_yticks(delays_ms)
    ax.set_yticklabels([f"{d:.1f} ms" for d in delays_ms], fontsize=9)
    ax.set_title("INVERTED MAML SILICON: 2D TEMPORAL SPECTROGRAM OF PRECISION (DELAY × EPOCH)\n"
                 "Card 2 (1k/3.3k Attenuator) with W(3) Staircase Ref & Bias Cells ([-40..+40] LSB)",
                 fontsize=12, fontweight="bold", pad=12)

    plt.tight_layout()
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"[+] Saved Spectrogram Heatmap Figure to: {out_path}")


def generate_joint_loss_and_enob_figure(data: dict, out_path: Path):
    eps = data["epochs"]
    meta = data["metadata"]
    epochs = [e["epoch"] for e in eps]
    delays_us = meta["strata_delays_us"]
    num_strata = len(delays_us)

    cmap = cm.coolwarm
    colors_strata = [cmap(i / (num_strata - 1)) for i in range(num_strata)]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 9.5), sharex=True)

    for s_idx, dly in enumerate(delays_us):
        losses = [e["strata_losses"][s_idx] for e in eps]
        ax1.plot(epochs, losses, color=colors_strata[s_idx], alpha=0.75, linewidth=1.1,
                 label=f"{dly/1000:.1f} ms")

    ax1.set_yscale("log")
    ax1.set_ylabel("Quadratic Loss (LSB²)", fontsize=11, fontweight="bold")
    ax1.set_title("Inverted MAML Card 2: Joint Quadratic Loss across 11 Discrete Strata [4.5..5.5 ms]\n"
                  "W(3) Staircase Reference & Bias Baseline ([-40..+40] LSB), Pure Online SGD (K=1)",
                  fontsize=12, fontweight="bold", pad=10)
    ax1.grid(True, which="both", linestyle=":", alpha=0.5)
    ax1.legend(loc="upper right", ncol=6, fontsize=8.5, framealpha=0.9)

    for s_idx, dly in enumerate(delays_us):
        enobs = [e["strata_enobs"][s_idx] for e in eps]
        ax2.plot(epochs, enobs, color=colors_strata[s_idx], alpha=0.75, linewidth=1.1)

    ax2.set_ylabel("Measured Precision (ENOB Bits)", fontsize=11, fontweight="bold")
    ax2.set_xlabel("Epoch", fontsize=11, fontweight="bold")
    ax2.grid(True, linestyle=":", alpha=0.5)

    for ax in (ax1, ax2):
        ax.axvline(100, color="gray", linestyle="--", linewidth=1.2)
        ax.axvline(200, color="gray", linestyle="--", linewidth=1.2)
        ax.axvline(600, color="red", linestyle="--", linewidth=1.5)

    plt.tight_layout()
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"[+] Saved Joint Loss/ENOB Figure to: {out_path}")


def generate_temporal_profile(data: dict, out_path: Path):
    eps = data["epochs"]
    delays_us = data["metadata"]["strata_delays_us"]
    delays_ms = np.array(delays_us) / 1000.0

    p1_recs = [r for r in eps if r["epoch"] < 100]
    p2_recs = [r for r in eps if 100 <= r["epoch"] < 200]
    p3_recs = [r for r in eps if 200 <= r["epoch"] < 600]
    p4_recs = [r for r in eps if r["epoch"] >= 600]

    p1_enobs = np.mean([[r["strata_enobs"][i] for i in range(len(delays_us))] for r in p1_recs], axis=0)
    p2_enobs = np.mean([[r["strata_enobs"][i] for i in range(len(delays_us))] for r in p2_recs], axis=0)
    p3_enobs = np.mean([[r["strata_enobs"][i] for i in range(len(delays_us))] for r in p3_recs], axis=0)
    p4_enobs = np.mean([[r["strata_enobs"][i] for i in range(len(delays_us))] for r in p4_recs], axis=0)

    fig, ax = plt.subplots(figsize=(11, 6.5), dpi=200)
    ax.plot(delays_ms, p1_enobs, "o-", color="#64748b", linewidth=2.0, markersize=7,
            label=f"Phase 1: Staircase Baseline (Mean: {np.mean(p1_enobs):.2f} b)")
    ax.plot(delays_ms, p2_enobs, "s-", color="#2563eb", linewidth=2.2, markersize=7,
            label=f"Phase 2: Nominal Converged (Mean: {np.mean(p2_enobs):.2f} b)")
    ax.plot(delays_ms, p3_enobs, "D-", color="#059669", linewidth=2.5, markersize=8,
            label=f"Phase 3: Active Comp (Dist ±5 LSB) (Mean: {np.mean(p3_enobs):.2f} b)")
    ax.plot(delays_ms, p4_enobs, "^--", color="#dc2626", linewidth=2.0, markersize=7,
            label=f"Phase 4: Ablation Control (Mean: {np.mean(p4_enobs):.2f} b)")

    ax.set_title(
        "Inverted MAML: Generalization Profile across Broadened Temporal Window [4.5 – 5.5 ms]\n"
        "Card 2 Silicon (1k/3.3k Attenuator) with W(3) Staircase Ref & Bias Cells",
        fontsize=12, fontweight="bold", pad=12
    )
    ax.set_xlabel("Snapshot Sampling Delay (ms)", fontsize=11, fontweight="bold")
    ax.set_ylabel("Measured Precision (ENOB Bits)", fontsize=11, fontweight="bold")
    ax.set_xticks(delays_ms)
    ax.set_xticklabels([f"{d:.1f} ms" for d in delays_ms], fontsize=9)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(loc="lower left", fontsize=10, framealpha=0.92)

    plt.tight_layout()
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"[+] Saved Temporal Profile Figure to: {out_path}")


def compile_pdf(data: dict, out_pdf: Path, fig_dict: dict):
    doc = SimpleDocTemplate(
        str(out_pdf),
        pagesize=letter,
        leftMargin=54, rightMargin=54,
        topMargin=54, bottomMargin=54
    )
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#475569"),
        spaceAfter=14
    )
    h2_style = ParagraphStyle(
        "DocH2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=14,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        "DocBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#334155"),
        spaceAfter=8
    )

    meta = data["metadata"]
    eps = data["epochs"]

    p1_recs = [r for r in eps if r["epoch"] < 100]
    p2_recs = [r for r in eps if 100 <= r["epoch"] < 200]
    p3_recs = [r for r in eps if 200 <= r["epoch"] < 600]
    p4_recs = [r for r in eps if r["epoch"] >= 600]

    p1_win_loss = np.mean([r["window_eval"]["mean_loss_lsb2"] for r in p1_recs])
    p1_win_enob = np.mean([r["window_eval"]["mean_enob_bits"] for r in p1_recs])
    p1_c5_loss = np.mean([r["center_5ms"]["loss_lsb2"] for r in p1_recs])
    p1_c5_enob = np.mean([r["center_5ms"]["enob_bits"] for r in p1_recs])

    p2_win_loss = np.mean([r["window_eval"]["mean_loss_lsb2"] for r in p2_recs])
    p2_win_enob = np.mean([r["window_eval"]["mean_enob_bits"] for r in p2_recs])
    p2_c5_loss = np.mean([r["center_5ms"]["loss_lsb2"] for r in p2_recs])
    p2_c5_enob = np.mean([r["center_5ms"]["enob_bits"] for r in p2_recs])

    p3_win_loss = np.mean([r["window_eval"]["mean_loss_lsb2"] for r in p3_recs])
    p3_win_enob = np.mean([r["window_eval"]["mean_enob_bits"] for r in p3_recs])
    p3_c5_loss = np.mean([r["center_5ms"]["loss_lsb2"] for r in p3_recs])
    p3_c5_enob = np.mean([r["center_5ms"]["enob_bits"] for r in p3_recs])

    p4_win_loss = np.mean([r["window_eval"]["mean_loss_lsb2"] for r in p4_recs])
    p4_win_enob = np.mean([r["window_eval"]["mean_enob_bits"] for r in p4_recs])
    p4_c5_loss = np.mean([r["center_5ms"]["loss_lsb2"] for r in p4_recs])
    p4_c5_enob = np.mean([r["center_5ms"]["enob_bits"] for r in p4_recs])

    story = []

    # Title Banner
    story.append(Paragraph("Inverted MAML: Silicon Hardware Benchmark Report", title_style))
    story.append(Paragraph(
        "<b>Evaluation of Card 2 (1k/3.3k Attenuator) with W(3) Staircase Reference & Bias Cells across [4.5..5.5 ms]</b><br/>"
        "Patent Pending Application: SE 2630397-4 | Open Science Hardware | Date: " + meta.get("date", "2026-11-06"),
        subtitle_style
    ))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0f172a"), spaceAfter=12))

    # Executive Summary
    story.append(Paragraph("1. Executive Summary & Experimental Configuration", h2_style))
    summary_text = (
        f"This report presents empirical measurements from <b>Card 2</b> (Trion T120 Master SoC, PCB v1.3.2, 1k/3.3k summing attenuator) "
        f"evaluated across a full 1,000 µs temporal discharge window (<b>4.5 ms to 5.5 ms</b>, 11 discrete strata at 100 µs intervals) "
        f"under pure online single-sample SGD (11 physical weight updates per epoch = <b>11,000 total updates on silicon</b>). "
        f"Matrix 3 was initialized with an engineered staircase pattern spanning <b>±40 LSB around 0</b> across the 6 columns: "
        f"Row 6 (Ref ClkB1 temporal ramp) set to <code>[-40, -24, -8, +8, +24, +40]</code> and Row 7 (Bias ClkRef DC anchor) "
        f"set to complementary <code>[+40, +24, +8, -8, -24, -40]</code> to provide full dynamic range across Sigmoid 4 "
        f"while preserving exact zero-mean common-mode current at the ColTIA virtual grounds."
    )
    story.append(Paragraph(summary_text, body_style))

    # Summary Table
    table_data = [
        ["Phase Segment", "Epochs", "FHP Online SGD", "Window Loss (LSB²)", "Window ENOB", "5.0 ms Loss (LSB²)", "5.0 ms ENOB"],
        ["Phase 1: Staircase Baseline", "0..99", "OFF (LR=0)", f"{p1_win_loss:.1f}", f"{p1_win_enob:.2f} b", f"{p1_c5_loss:.1f}", f"{p1_c5_enob:.2f} b"],
        ["Phase 2: Nominal Converged", "100..199", "ON (LR=0.02x)", f"{p2_win_loss:.1f}", f"{p2_win_enob:.2f} b", f"{p2_c5_loss:.1f}", f"{p2_c5_enob:.2f} b"],
        ["Phase 3: Disturbance Tracking", "200..599", "ON (Dist ±5)", f"{p3_win_loss:.1f}", f"{p3_win_enob:.2f} b", f"{p3_c5_loss:.1f}", f"{p3_c5_enob:.2f} b"],
        ["Phase 4: Ablation Control", "600..1000", "OFF (LR=0)", f"{p4_win_loss:.1f}", f"{p4_win_enob:.2f} b", f"{p4_c5_loss:.1f}", f"{p4_c5_enob:.2f} b"],
    ]
    t = Table(table_data, colWidths=[110, 50, 80, 75, 65, 75, 65])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#f8fafc")),
        ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#f0fdf4")),
        ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#fefce8")),
        ("BACKGROUND", (0, 4), (-1, 4), colors.HexColor("#fef2f2")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
    ]))
    story.append(t)
    story.append(Spacer(1, 14))

    # Page Break for Waterfall Spectrogram
    story.append(PageBreak())
    story.append(Paragraph("2. 2D Temporal Spectrogram Waterfall Heatmap", h2_style))
    story.append(Paragraph(
        "The figure below illustrates the 2D spectrogram of precision across delay (4.5 to 5.5 ms) and epoch (0 to 1000). "
        "With crystal-locked 10.0 ms refresh timing, each horizontal stratum tracks smoothly across time without timing jitter drops.",
        body_style
    ))
    if fig_dict.get("heatmap") and fig_dict["heatmap"].exists():
        story.append(Image(str(fig_dict["heatmap"]), width=500, height=250))
    story.append(Spacer(1, 14))

    # Joint Loss and Generalization Profile
    story.append(Paragraph("3. Generalization Profile across 11 Strata [4.5..5.5 ms]", h2_style))
    if fig_dict.get("profile") and fig_dict["profile"].exists():
        story.append(Image(str(fig_dict["profile"]), width=480, height=270))
    story.append(Spacer(1, 14))

    # Page Break for Joint Curves
    story.append(PageBreak())
    story.append(Paragraph("4. Joint Loss & ENOB Dynamics across All 11 Strata", h2_style))
    if fig_dict.get("joint") and fig_dict["joint"].exists():
        story.append(Image(str(fig_dict["joint"]), width=500, height=340))
    story.append(Spacer(1, 14))

    # Build PDF
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[+] Compiled Publication PDF Report to: {out_pdf}")


def main():
    print("=" * 80)
    print("Inverted MAML: Generating Card 2 W(3) Staircase Comprehensive Report")
    print("=" * 80)

    if not DATA_PATH.exists():
        print(f"[!] Error: Dataset not found: {DATA_PATH}")
        sys.exit(1)

    data = load_dataset(DATA_PATH)

    heatmap_path = FIGURES_DIR / "fig_card2_w3_staircase_spectrogram.png"
    joint_path = FIGURES_DIR / "fig_card2_w3_staircase_joint_loss_enob.png"
    profile_path = FIGURES_DIR / "fig_card2_w3_staircase_profile.png"
    pdf_path = DOCS_DIR / "INVERTED_MAML_CARD2_W3_STAIRCASE_COMPREHENSIVE_REPORT.pdf"

    fig_dict = {
        "heatmap": heatmap_path,
        "joint": joint_path,
        "profile": profile_path,
    }

    generate_spectrogram_heatmap(data, heatmap_path)
    generate_joint_loss_and_enob_figure(data, joint_path)
    generate_temporal_profile(data, profile_path)
    compile_pdf(data, pdf_path, fig_dict)

    # Copy to artifacts
    for f in [heatmap_path, joint_path, profile_path, pdf_path]:
        if f.exists():
            shutil.copy2(f, ARTIFACTS_DIR / f.name)

    print("\n[SUCCESS] Report and waterfall assets generated successfully!")

if __name__ == "__main__":
    main()

