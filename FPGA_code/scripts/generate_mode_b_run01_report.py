#!/usr/bin/env python3
"""
generate_mode_b_run01_report.py
Inverted MAML (Patent Pending SE 2630397-4) - Open Science Hardware

Generates publication-quality figure and PDF report for Run 01 of the Mode B
Uncompensated Silicon Verification Experiment.
"""

import sys
import os
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

LOG_DIR = REPO_ROOT / "FPGA_code" / "logs" / "mode_b_uncompensated_campaign"
DOCS_DIR = REPO_ROOT / "FPGA_code" / "docs"
ARTIFACTS_DIR = Path("/home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a")


def plot_mode_b_run01(data: dict, out_png_artifacts: Path, out_png_docs: Path):
    epochs_data = data["epochs"]
    ep = np.array([e["epoch"] for e in epochs_data])
    loss = np.array([e["loss_lsb2"] for e in epochs_data])
    rmse = np.array([e["rmse_lsb"] for e in epochs_data])
    enob = np.array([e["enob_bits"] for e in epochs_data])
    err49 = np.array([e["err49"] for e in epochs_data]) # shape (N, 6)

    # 7-point moving average
    w_s = 7
    smooth_loss = np.convolve(loss, np.ones(w_s)/w_s, mode='same')
    smooth_enob = np.convolve(enob, np.ones(w_s)/w_s, mode='same')

    fig, (ax_loss, ax_enob, ax_err) = plt.subplots(3, 1, figsize=(11, 11), sharex=True)

    mean_loss = np.mean(loss)
    mean_enob = np.mean(enob)

    # 1. Loss Panel
    ax_loss.plot(ep, loss, color="#94a3b8", alpha=0.45, linewidth=1.0, label="Raw Uncompensated Loss")
    ax_loss.plot(ep, smooth_loss, color="#dc2626", linewidth=2.2, label=f"7-pt Trend (Mean: {mean_loss:.1f} LSB²)")
    ax_loss.axhline(mean_loss, color="#b91c1c", linestyle="--", linewidth=1.2, alpha=0.8, label=f"Mean Loss ({mean_loss:.1f})")
    ax_loss.set_ylabel("Loss (LSB²)", fontsize=10, fontweight="bold")
    ax_loss.set_title("Mode B (Uncompensated Matrix 33) Silicon Baseline: Run 01 (100 Epochs)",
                      fontsize=12, fontweight="bold", pad=10)
    ax_loss.legend(loc="upper right", framealpha=0.92, fontsize=8.5)
    ax_loss.grid(True, linestyle=":", alpha=0.6)

    # 2. ENOB Panel
    ax_enob.plot(ep, enob, color="#fdba74", alpha=0.5, linewidth=1.0)
    ax_enob.plot(ep, smooth_enob, color="#c2410c", linewidth=2.2, label=f"7-pt Trend (Mean: {mean_enob:.2f} b)")
    ax_enob.axhline(mean_enob, color="#9a3412", linestyle="--", linewidth=1.2, alpha=0.8, label=f"Mean ENOB ({mean_enob:.2f} b)")
    ax_enob.set_ylabel("ENOB (Bits)", fontsize=10, fontweight="bold")
    ax_enob.legend(loc="lower right", framealpha=0.92, fontsize=8.5)
    ax_enob.grid(True, linestyle=":", alpha=0.6)

    # 3. Column Error Panel
    col_colors = ["#2563eb", "#d97706", "#16a34a", "#dc2626", "#9333ea", "#0891b2"]
    for c in range(6):
        ax_err.plot(ep, err49[:, c], label=f"Col {c} Err", color=col_colors[c], linewidth=1.2, alpha=0.85)
    ax_err.axhline(0, color="#64748b", linestyle="-", linewidth=0.8)
    ax_err.set_ylabel("ADC49 Error (LSB)", fontsize=10, fontweight="bold")
    ax_err.set_xlabel("Epoch Number (Rotating Arbitrary White-Noise Vectors on Silicon)", fontsize=10, fontweight="bold")
    ax_err.legend(loc="upper left", ncol=3, framealpha=0.92, fontsize=8)
    ax_err.grid(True, linestyle=":", alpha=0.6)

    plt.tight_layout()
    fig.savefig(out_png_artifacts, dpi=200)
    fig.savefig(out_png_docs, dpi=200)
    plt.close(fig)
    print(f"[+] Saved figure to {out_png_artifacts} and {out_png_docs}")


def generate_mode_b_pdf(data: dict, fig_png: Path, out_pdf_artifacts: Path, out_pdf_docs: Path):
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image

    doc = SimpleDocTemplate(
        str(out_pdf_artifacts),
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
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#475569"),
        alignment=1,
    )
    h1_style = ParagraphStyle(
        "SectionH1",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1e3a8a"),
        spaceBefore=8,
        spaceAfter=3,
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
    prov = data.get("provenance", {})
    summary = data.get("summary", {})

    story.append(Paragraph("INVERTED MAML: MODE B UNCOMPENSATED SILICON VERIFICATION REPORT", title_style))
    story.append(Spacer(1, 3))
    story.append(Paragraph(
        "Run 01 (100 Epochs) | Hardware Jumpers set to MODE B (Compensation Loop Physically Disconnected)<br/>"
        f"<b>Hardware:</b> PCB v1.3.2 (Summing Attenuator 1k / 5.1k Ohm) | <b>SoC:</b> Trion T120 ({prov.get('hw_logic_version', '0x20261030')}, {prov.get('sw_firmware_version', 'v2.1-MAML')})<br/>"
        "<b>Patent:</b> SE 2630397-4 (Open Science Hardware)", subtitle_style))
    story.append(Spacer(1, 8))

    summary_text = (
        "<b>Executive Summary:</b> Verification of pure uncompensated Matrix 33 multiplier dynamics on physical silicon was conducted in Mode B. "
        "The physical jumpers were manually set to Mode B, disconnecting the active M3 / M8 compensation branch from the summing junction. "
        f"Across 100 continuous epochs with arbitrary rotating white-noise input vectors, the uncompensated system demonstrated an empirical mean loss of "
        f"<b>{summary.get('mean_loss_lsb2', 0):.1f} ± {summary.get('std_loss_lsb2', 0):.1f} LSB²</b> and an uncompensated mean ENOB of "
        f"<b>{summary.get('mean_enob_bits', 0):.2f} ± {summary.get('std_enob_bits', 0):.2f} bits</b>. "
        f"This establishes the raw physical silicon baseline against which Inverted MAML active Vernier compensation is benchmarked."
    )
    story.append(Paragraph(summary_text, body_style))
    story.append(Spacer(1, 8))

    table_data = [
        [
            Paragraph("Metric", table_cell_bold),
            Paragraph("Uncompensated Mode B (Run 01)", table_cell_bold),
            Paragraph("Mode A Baseline (Ep 0..99)", table_cell_bold),
            Paragraph("Mode A Compensated (Peak)", table_cell_bold),
        ],
        [
            Paragraph("Mean Loss", table_cell_bold),
            Paragraph(f"<b>{summary.get('mean_loss_lsb2', 0):.1f} LSB²</b>", table_cell),
            Paragraph("23,077.1 LSB²", table_cell),
            Paragraph("<b>287.0 LSB²</b> (-98.8%)", table_cell_bold),
        ],
        [
            Paragraph("Mean ENOB", table_cell_bold),
            Paragraph(f"<b>{summary.get('mean_enob_bits', 0):.2f} bits</b>", table_cell),
            Paragraph("~3.13 bits", table_cell),
            Paragraph("<b>6.23 bits</b> (+3.3 bits)", table_cell_bold),
        ],
        [
            Paragraph("Peak ENOB", table_cell_bold),
            Paragraph(f"{summary.get('best_enob_bits', 0):.2f} b (Ep {summary.get('best_epoch', 0)})", table_cell),
            Paragraph("3.63 bits", table_cell),
            Paragraph("<b>6.74 bits</b>", table_cell_bold),
        ],
    ]

    t = Table(table_data, colWidths=[130, 130, 130, 150])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#fef3c7")),
    ]))
    story.append(t)
    story.append(Spacer(1, 8))

    if fig_png.exists():
        story.append(Image(str(fig_png), width=540, height=450))

    def add_page_decorations(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#64748b"))
        canvas.drawString(36, 18, "Inverted MAML Independent Research | Patent Pending SE 2630397-4 | Open Science Hardware")
        page_str = f"Page {canvas._pageNumber}"
        canvas.drawRightString(612 - 36, 18, page_str)
        canvas.restoreState()

    doc.build(story, onFirstPage=add_page_decorations, onLaterPages=add_page_decorations)

    import shutil
    shutil.copy(out_pdf_artifacts, out_pdf_docs)
    print(f"[+] Saved PDF to {out_pdf_artifacts} and {out_pdf_docs}")


def main():
    json_path = LOG_DIR / "m33_mode_b_100ep_run_01.json"
    if not json_path.exists():
        print(f"[!] Error: {json_path} does not exist.")
        sys.exit(1)

    with open(json_path, "r") as f:
        data = json.load(f)

    fig_artifacts = ARTIFACTS_DIR / "fig_mode_b_100ep_run_01.png"
    fig_docs = DOCS_DIR / "figures" / "fig_mode_b_100ep_run_01.png"
    pdf_artifacts = ARTIFACTS_DIR / "MODE_B_UNCOMPENSATED_100EP_RUN_01_REPORT.pdf"
    pdf_docs = DOCS_DIR / "MODE_B_UNCOMPENSATED_100EP_RUN_01_REPORT.pdf"

    plot_mode_b_run01(data, fig_artifacts, fig_docs)
    generate_mode_b_pdf(data, fig_artifacts, pdf_artifacts, pdf_docs)


if __name__ == "__main__":
    main()

