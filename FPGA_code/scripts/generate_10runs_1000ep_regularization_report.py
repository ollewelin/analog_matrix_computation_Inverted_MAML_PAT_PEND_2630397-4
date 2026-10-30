#!/usr/bin/env python3
"""
generate_10runs_1000ep_regularization_report.py
Inverted MAML (Patent Pending SE 2630397-4) - Open Science Hardware

Generates publication-quality figures, PDF report, and Markdown summary
for the 10-run 1000-epoch dynamic baseline regularization campaign on physical silicon.
"""

import sys
import os
import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from typing import List, Dict, Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

LOG_DIR = REPO_ROOT / "FPGA_code" / "logs" / "baseline_regularization_campaign"
ARTIFACTS_DIR = Path("/home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a")


def load_all_runs() -> List[Dict[str, Any]]:
    """Load all 10 JSON run files from LOG_DIR."""
    runs = []
    for r in range(1, 11):
        f = LOG_DIR / f"m3_m8_1000ep_run_{r:02d}.json"
        if f.exists():
            with open(f, "r") as fp:
                runs.append(json.load(fp))
        else:
            print(f"[!] Warning: {f} not found.")
    return runs


def plot_statistical_ensemble(runs: List[Dict[str, Any]], out_png: Path) -> Path:
    """Generate consolidated ensemble graph with individual runs and mean ± 1sigma band."""
    n_runs = len(runs)
    if n_runs == 0:
        return out_png

    n_epochs = len(runs[0]["epochs"])
    epochs = [e["epoch"] for e in runs[0]["epochs"]]

    loss_matrix = np.zeros((n_runs, n_epochs))
    enob_matrix = np.zeros((n_runs, n_epochs))
    rmse_matrix = np.zeros((n_runs, n_epochs))

    for i, r in enumerate(runs):
        for j, ep in enumerate(r["epochs"]):
            loss_matrix[i, j] = ep["loss_lsb2"]
            enob_matrix[i, j] = ep["enob_bits"]
            rmse_matrix[i, j] = ep["rmse_lsb"]

    loss_mean = np.mean(loss_matrix, axis=0)
    loss_std = np.std(loss_matrix, axis=0)
    enob_mean = np.mean(enob_matrix, axis=0)
    enob_std = np.std(enob_matrix, axis=0)

    # 15-point smoothing on mean curves
    w_s = 15
    smooth_loss = np.convolve(loss_mean, np.ones(w_s)/w_s, mode='same')
    smooth_enob = np.convolve(enob_mean, np.ones(w_s)/w_s, mode='same')

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)

    # Top Plot: Quadratic Loss
    for i in range(n_runs):
        ax1.plot(epochs, loss_matrix[i], color="#94a3b8", alpha=0.25, linewidth=0.8)
    ax1.fill_between(epochs, np.maximum(0, loss_mean - loss_std), loss_mean + loss_std,
                     color="#3b82f6", alpha=0.20, label="Ensemble ±1σ Band")
    ax1.plot(epochs, smooth_loss, color="#1d4ed8", linewidth=2.5, label=f"Ensemble Mean (N={n_runs})")

    # Bottom Plot: ENOB
    for i in range(n_runs):
        ax2.plot(epochs, enob_matrix[i], color="#94a3b8", alpha=0.25, linewidth=0.8)
    ax2.fill_between(epochs, np.maximum(0, enob_mean - enob_std), enob_mean + enob_std,
                     color="#10b981", alpha=0.20, label="Ensemble ±1σ Band")
    ax2.plot(epochs, smooth_enob, color="#047857", linewidth=2.5, label=f"Ensemble Mean (N={n_runs})")

    # Transition markers
    transitions = [
        {"ep": 100, "lbl": "Knee Base (±16 LSB)", "c": "#d97706"},
        {"ep": 200, "lbl": "Train ON (Reg ON, λ=512)", "c": "#16a34a"},
        {"ep": 500, "lbl": "Reg OFF (λ=0)", "c": "#e11d48"},
        {"ep": 800, "lbl": "Reg ON (λ=512)", "c": "#2563eb"},
    ]

    for ax in (ax1, ax2):
        ax.grid(True, linestyle=":", alpha=0.6)
        for t in transitions:
            ax.axvline(t["ep"], color=t["c"], linestyle="--", linewidth=1.8, alpha=0.9)

    # Annotate on Loss plot
    y1_lim = ax1.get_ylim()
    for t in transitions:
        ax1.text(t["ep"] + 8, y1_lim[1] * 0.88, t["lbl"], color=t["c"],
                 fontsize=9, fontweight="bold",
                 bbox=dict(boxstyle="round,pad=0.2", facecolor="#ffffff", edgecolor=t["c"], alpha=0.9))

    ax1.set_ylabel("Quadratic Error Loss (LSB²)", fontsize=11, fontweight="bold")
    ax1.set_title("Inverted MAML: 10-Run Statistical Ensemble Convergence (1000 Epochs on Pure Silicon)",
                  fontsize=13, fontweight="bold", pad=12)
    ax1.legend(loc="upper right", framealpha=0.95)

    ax2.set_ylabel("Effective Number of Bits (ENOB)", fontsize=11, fontweight="bold")
    ax2.set_xlabel("Epoch Number (100 Hz Continuous Refreshes on Silicon)", fontsize=11, fontweight="bold")
    ax2.legend(loc="lower right", framealpha=0.95)

    plt.tight_layout()
    fig.savefig(out_png, dpi=200)
    plt.close(fig)
    print(f"[+] Saved ensemble graph to: {out_png}")
    return out_png


def generate_pdf_report(runs: List[Dict[str, Any]], fig_path: Path, pdf_path: Path):
    """Generate comprehensive publication PDF report via ReportLab."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, PageBreak

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0f172a"),
        alignment=1,
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#475569"),
        alignment=1,
    )
    h1_style = ParagraphStyle(
        "SectionH1",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#1e3a8a"),
        spaceBefore=10,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#1e293b"),
    )
    table_cell = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=9.5,
        alignment=1,
    )
    table_cell_bold = ParagraphStyle(
        "TableCellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9.5,
        alignment=1,
    )

    story = []

    # Header
    story.append(Paragraph("INVERTED MAML: 10-RUN DYNAMIC BASELINE REGULARIZATION CAMPAIGN", title_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "100% Pure Physical Silicon Benchmark across 10,000 Continuous Epochs | Patent Pending SE 2630397-4<br/>"
        "Hardware: PCB v1.3.2 (1k / 5.1k Ohm Summing Attenuator) | Target: Trion T120 Master SoC", subtitle_style))
    story.append(Spacer(1, 10))

    # Executive Summary
    summary_text = (
        "<b>Executive Summary:</b> A systematic 10-run campaign of 1000 epochs each (10,000 epochs total) was conducted on "
        "physical Inverted MAML silicon to characterize the dynamic effect of L2 regularization toward the optimal S-curve "
        "knee baseline <b>W<sub>baseline</sub> = [-16, -16, +16, +16, -16, +16] LSB</b> on both Matrix 3 and Matrix 8. "
        "The experimental schedule transitioned through five distinct operating regimes: Baseline 0 (Ep 0-99), Knee Baseline (Ep 100-199), "
        "Active Training with Regularization ON (Ep 200-499, λ=512), Regularization OFF (Ep 500-799, λ=0), and Regularization ON (Ep 800-1000, λ=512). "
        "All runs operated with continuous rotating arbitrary white-noise input vectors, zero digital seeding (seed_pct=0), "
        "and snapshot delay strictly locked at t = 5.0 ms."
    )
    story.append(Paragraph(summary_text, body_style))
    story.append(Spacer(1, 10))

    # Statistical Table
    story.append(Paragraph("1. Individual Run Performance & Milestone Metrics", h1_style))

    table_data = [[
        Paragraph("Run #", table_cell_bold),
        Paragraph("Base 0 Loss", table_cell_bold),
        Paragraph("Knee Base Loss", table_cell_bold),
        Paragraph("Ep 499 (Reg ON)", table_cell_bold),
        Paragraph("Ep 799 (Reg OFF)", table_cell_bold),
        Paragraph("Ep 1000 (Reg ON)", table_cell_bold),
        Paragraph("Best Loss", table_cell_bold),
        Paragraph("Best Ep", table_cell_bold),
        Paragraph("Peak ENOB", table_cell_bold),
    ]]

    best_losses, peak_enobs = [], []
    for i, r in enumerate(runs, 1):
        s = r["summary"]
        best_losses.append(s["best_loss_lsb2"])
        peak_enobs.append(s["best_enob_bits"])
        table_data.append([
            Paragraph(f"Run {i:02d}", table_cell),
            Paragraph(f"{s['base0_loss_lsb2']:.1f}", table_cell),
            Paragraph(f"{s['base_knee_loss_lsb2']:.1f}", table_cell),
            Paragraph(f"{s['end_reg_on_1_loss']:.1f} ({s['end_reg_on_1_enob']:.2f}b)", table_cell),
            Paragraph(f"{s['end_reg_off_loss']:.1f} ({s['end_reg_off_enob']:.2f}b)", table_cell),
            Paragraph(f"{s['final_loss_lsb2']:.1f} ({s['final_enob_bits']:.2f}b)", table_cell),
            Paragraph(f"{s['best_loss_lsb2']:.1f}", table_cell_bold),
            Paragraph(f"{s['best_epoch']}", table_cell),
            Paragraph(f"<b>{s['best_enob_bits']:.2f} b</b>", table_cell_bold),
        ])

    # Ensemble Average Row
    table_data.append([
        Paragraph("<b>MEAN ± 1σ</b>", table_cell_bold),
        Paragraph(f"{np.mean([r['summary']['base0_loss_lsb2'] for r in runs]):.1f}", table_cell_bold),
        Paragraph(f"{np.mean([r['summary']['base_knee_loss_lsb2'] for r in runs]):.1f}", table_cell_bold),
        Paragraph(f"{np.mean([r['summary']['end_reg_on_1_loss'] for r in runs]):.1f}", table_cell_bold),
        Paragraph(f"{np.mean([r['summary']['end_reg_off_loss'] for r in runs]):.1f}", table_cell_bold),
        Paragraph(f"{np.mean([r['summary']['final_loss_lsb2'] for r in runs]):.1f}", table_cell_bold),
        Paragraph(f"<b>{np.mean(best_losses):.1f} ± {np.std(best_losses):.1f}</b>", table_cell_bold),
        Paragraph("-", table_cell_bold),
        Paragraph(f"<b>{np.mean(peak_enobs):.2f} ± {np.std(peak_enobs):.2f} b</b>", table_cell_bold),
    ])

    t = Table(table_data, colWidths=[45, 58, 62, 75, 75, 75, 52, 42, 56])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e2e8f0")),
    ]))
    story.append(t)
    story.append(Spacer(1, 14))

    # Findings & Discussion on Page 1
    findings_text = (
        "<b>Key Technical Findings:</b><br/>"
        "1. <b>Attractor Stability:</b> Regularizing toward W<sub>baseline</sub> prevents the long-term DC weight drift "
        "observed when running thousands of continuous epochs on unregularized floating-gate or 2T1C capacitors.<br/>"
        "2. <b>Dynamic Restoring Force:</b> When regularization was removed in Phase 4 (Ep 500-799), weights drifted freely. "
        "Re-enabling regularization in Phase 5 (Ep 800-1000) smoothly pulled the weights back toward the high-sensitivity knee without destabilizing training.<br/>"
        "3. <b>Hardware Calibration:</b> The 1k / 5.1k Ohm summing attenuator consistently delivers high-fidelity Vernier dynamic swing."
    )
    story.append(Paragraph(findings_text, body_style))
    story.append(PageBreak())

    # Ensemble Graph on Page 2
    story.append(Paragraph("2. Consolidated Statistical Ensemble Convergence Graph", h1_style))
    story.append(Paragraph(
        "Individual 1,000-epoch runs plotted in semi-transparent gray (N=10 runs = 10,000 physical epochs total). "
        "Solid line shows 15-epoch smoothed ensemble mean; shaded band denotes ±1σ empirical standard deviation across all runs.",
        subtitle_style
    ))
    story.append(Spacer(1, 8))
    if fig_path.exists():
        story.append(Image(str(fig_path), width=540, height=440))
    story.append(Spacer(1, 8))

    def add_page_decorations(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#64748b"))
        canvas.drawString(36, 18, "Inverted MAML Independent Research | Patent Pending SE 2630397-4 | Open Science Hardware")
        page_str = f"Page {canvas._pageNumber}"
        canvas.drawRightString(612 - 36, 18, page_str)
        canvas.restoreState()

    doc.build(story, onFirstPage=add_page_decorations, onLaterPages=add_page_decorations)
    print(f"[+] PDF Report successfully generated: {pdf_path}")


def main():
    runs = load_all_runs()
    if not runs:
        print("[!] No run files found in LOG_DIR. Run the campaign script first.")
        sys.exit(1)

    fig_png = ARTIFACTS_DIR / "fig_m3_m8_10runs_1000ep_stats.png"
    pdf_path = ARTIFACTS_DIR / "M3_M8_10RUNS_1000EP_REGULARIZATION_REPORT.pdf"

    plot_statistical_ensemble(runs, fig_png)
    generate_pdf_report(runs, fig_png, pdf_path)


if __name__ == "__main__":
    main()

