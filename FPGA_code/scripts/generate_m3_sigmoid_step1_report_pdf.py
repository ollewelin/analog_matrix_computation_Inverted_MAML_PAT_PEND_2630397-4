#!/usr/bin/env python3
"""
generate_m3_sigmoid_step1_report_pdf.py
=======================================
Generates:
  1. Formal PDF Report: FPGA_code/docs/M3_SIGMOID_STEP1_48CELL_REPORT.pdf
  2. Markdown Summary:  FPGA_code/docs/M3_SIGMOID_STEP1_48CELL_REPORT.md
"""

from __future__ import annotations
import json
import os
import shutil
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DOCS_DIR = REPO_ROOT / "FPGA_code" / "docs"
FIG_DIR = DOCS_DIR / "figures"
DATA_PATH = REPO_ROOT / "FPGA_code" / "logs" / "m3_sigmoid_characterization" / "step1_m3_cell_map_5ms.json"
PDF_PATH = DOCS_DIR / "M3_SIGMOID_STEP1_48CELL_REPORT.pdf"
MD_PATH = DOCS_DIR / "M3_SIGMOID_STEP1_48CELL_REPORT.md"

ARTIFACT_DIR = Path("/home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a")


def add_header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#64748B"))
    if canvas._pageNumber > 1:
        canvas.drawString(12 * mm, 287 * mm, "INVERTED MAML ANALOG MATRIX — PATENT PENDING SE 2630397-4")
        canvas.drawRightString(198 * mm, 287 * mm, "M3 Sigmoid Step 1 Report | t = 5.0 ms")
        canvas.setStrokeColor(colors.HexColor("#CBD5E1"))
        canvas.setLineWidth(0.5)
        canvas.line(12 * mm, 284 * mm, 198 * mm, 284 * mm)
    canvas.drawString(12 * mm, 10 * mm, "Trion T120 Master SoC + T20 Coprocessor | 100% Pure Physical Silicon Execution")
    canvas.drawRightString(198 * mm, 10 * mm, f"Page {canvas._pageNumber}")
    canvas.line(12 * mm, 13 * mm, 198 * mm, 13 * mm)
    canvas.restoreState()


def build_pdf(data):
    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=A4,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
    )
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "DocSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#334155"),
        spaceAfter=12,
    )
    h1_style = ParagraphStyle(
        "Heading1",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#1E3A8A"),
        spaceBefore=10,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#334155"),
        spaceAfter=6,
    )
    callout_style = ParagraphStyle(
        "Callout",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12.5,
        textColor=colors.HexColor("#0F172A"),
    )
    th_style = ParagraphStyle(
        "TH",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.white,
        alignment=1,
    )
    td_style = ParagraphStyle(
        "TD",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=9.5,
        alignment=1,
    )

    story = []

    # Title Banner
    story.append(Paragraph("MATRIX 3 SIGMOID ANALOG ACTIVATION CHARACTERIZATION", title_style))
    story.append(Paragraph("Steg 1: Full 48-Crosspoint Transfer Landscape via ColTIA + Sigmoid (Ref 4) on Differential ADC_45<br/>"
                           "<b>Pure Physical Silicon Telemetry @ Nominal t = 5.0 ms Settled Delay</b>", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1E3A8A"), spaceAfter=10))

    # Executive Summary Box
    summary_text = (
        "<b>EXECUTIVE SUMMARY & HARDWARE CONTEXT:</b><br/>"
        "This empirical report characterizes all 48 crosspoints (8 rows &times; 6 cols) of Matrix 3 (Layer 1 "
        "adaptive compensation multiplier) driving the ColTIA summing stages and physical analog sigmoid activation "
        "circuitry (Ref 4). Measured via differential ADC_45 at nominal <i>t = 5.0 ms</i>. "
        "Each cell was excited across 17 weight levels [-127..+127] and 5 DAC_2 input amplitudes (X &in; {-127, -64, 0, +64, +127}). "
        "The objective is to discover whether the positive (+) or negative (-) weight polarity offers superior dynamic swing "
        "and lower stochastic jerk, in order to set optimal initial baseline weights and regularization attractors."
    )
    callout_data = [[Paragraph(summary_text, callout_style)]]
    callout_table = Table(callout_data, colWidths=[186 * mm])
    callout_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#94A3B8")),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(callout_table)
    story.append(Spacer(1, 10))

    # Figure 1: 48-cell Grid
    story.append(Paragraph("1. Full 48-Cell Transfer Grid (5 Input Curves per Cell)", h1_style))
    story.append(Paragraph("Every cell transfer curve shows ADC_45 &Delta; (LSB) vs Weight W3. Curves: Blue (X=-127), Red (X=-64), Green (X=0), Orange (X=+64), Gold (X=+127). Shaded bands represent &plusmn;1&sigma; repeatability across multiple synchronous recharges.", body_style))
    fig_grid = FIG_DIR / "fig_m3_sigmoid_step1_48cell_grid.png"
    if fig_grid.exists():
        story.append(Image(str(fig_grid), width=186 * mm, height=220 * mm))
    story.append(PageBreak())

    # Figure 2: Heatmaps
    story.append(Paragraph("2. Polarity, Dynamic Swing, and Smoothness Heatmaps", h1_style))
    story.append(Paragraph("Comparison of Negative Polarity (W &le; 0) vs Positive Polarity (W &ge; 0) across all 48 cells. Score combines dynamic swing with inverse jerk/roughness: Score = Dynamic / (1 + Jerk/10) &times; Monotonicity.", body_style))
    fig_heat = FIG_DIR / "fig_m3_sigmoid_step1_heatmaps.png"
    if fig_heat.exists():
        story.append(Image(str(fig_heat), width=186 * mm, height=124 * mm))
    story.append(Spacer(1, 10))

    # Figure 3: Column Summary
    story.append(Paragraph("3. Column-Wise Quality Comparison & Polarity Decision", h1_style))
    fig_col = FIG_DIR / "fig_m3_sigmoid_step1_column_summary.png"
    if fig_col.exists():
        story.append(Image(str(fig_col), width=186 * mm, height=95 * mm))
    story.append(PageBreak())

    # Quantitative Data Table
    story.append(Paragraph("4. Quantitative Column Summary & Polarity Recommendation", h1_style))
    summ = data.get("column_summary", {})
    t_rows = [[
        Paragraph("Column", th_style),
        Paragraph("Score (W &le; 0)", th_style),
        Paragraph("Score (W &ge; 0)", th_style),
        Paragraph("Recommended Polarity", th_style),
        Paragraph("Verdict / Interpretation", th_style),
    ]]
    for c_id in sorted(summ.keys()):
        item = summ[c_id]
        rec = item["recommended_side"].upper()
        rec_color = "#15803D" if rec == "POS" else "#1D4ED8"
        t_rows.append([
            Paragraph(f"<b>{c_id}</b>", td_style),
            Paragraph(f"{item['score_neg']:.1f}", td_style),
            Paragraph(f"{item['score_pos']:.1f}", td_style),
            Paragraph(f"<b><font color='{rec_color}'>{rec} ({'+' if rec=='POS' else '-'})</font></b>", td_style),
            Paragraph(f"Optimal for {'positive' if rec=='POS' else 'negative'} sigmoid knee biasing", td_style),
        ])
    col_table = Table(t_rows, colWidths=[25 * mm, 35 * mm, 35 * mm, 45 * mm, 46 * mm])
    col_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(col_table)
    story.append(Spacer(1, 14))

    # Discussion & Next Steps
    story.append(Paragraph("5. Architectural Conclusions & Transition to Steg 2", h1_style))
    disc_text = (
        "<b>Transition to Steg 2 (Column Collective Sigmoid S-Curve Sweep):</b><br/>"
        "With Steg 1 establishing cell-level polarity characteristics, Steg 2 will now sweep all rows "
        "of each column collectively (W3[0..7][c] ramped simultaneously) across representative operating "
        "levels (X = &plusmn;127 full-scale and X = &plusmn;64 arbitrary medium signal). "
        "This reveals the macroscopic sigmoid S-curve into ADC_45 under full multi-row current injection, "
        "identifying the exact baseline weight bias point W_base[c] where sensitivity and smoothness are maximized."
    )
    story.append(Paragraph(disc_text, body_style))

    doc.build(story, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
    print(f"[+] Successfully built PDF report -> {PDF_PATH}")
    if ARTIFACT_DIR.exists():
        shutil.copy(PDF_PATH, ARTIFACT_DIR / "M3_SIGMOID_STEP1_48CELL_REPORT.pdf")


def build_md(data):
    summ = data.get("column_summary", {})
    duration = data.get("duration_s", 0)
    lines = [
        "# Matrix 3 Sigmoid Analog Activation Characterization Report (Ref 4)",
        "",
        "**Steg 1: Full 48-Crosspoint Transfer Landscape via ColTIA + Sigmoid (Ref 4) on Differential ADC_45**  ",
        f"**Execution Environment:** Pure Physical Silicon (Trion T120 Master SoC @ 192.168.1.50:5000)  ",
        f"**Settled Snapshot Timing:** Locked strictly to nominal $t = 5.0\\text{{ ms}}$ ($5000\\ \\mu\\text{{s}}$)  ",
        f"**Sweep Repetitions:** {data.get('reps', 6)} recharges per operating point  ",
        f"**Total Execution Duration:** {duration/60:.1f} minutes  ",
        "",
        "---",
        "",
        "## 1. Executive Summary",
        "",
        "Matrix 3 is the primary adaptive compensation layer in the Inverted MAML architecture, driving the ColTIA summing stages and the physical analog sigmoid activation circuitry (Ref 4).",
        "This empirical characterization measured all 48 crosspoints ($8\\text{ rows} \\times 6\\text{ cols}$) under 17 weight levels ($W \\in [-127..+127]$) across 5 standard input DAC_2 levels ($X \\in \\{-127, -64, 0, +64, +127\\}$).",
        "",
        "### Key Findings:",
        "- **Active Dynamics Across All 6 Columns:** Unlike uncompensated Matrix 33 Mode B where Columns 2 and 3 were railed at $-2048\\text{ LSB}$, the ColTIA and analog sigmoid activation in Matrix 3 are active and responsive across all 6 columns.",
        "- **Polarity Trade-off:** Positive weights ($W \\ge 0$) vs Negative weights ($W \\le 0$) were evaluated using the objective score metric:",
        "  $$\\text{Score} = \\frac{\\text{Dynamic Swing } \\Delta Y}{1 + \\text{Jerk} / 10} \\times \\text{Monotonicity}$$",
        "",
        "---",
        "",
        "## 2. Column-Wise Polarity Summary Table",
        "",
        "| Column | Score (W ≤ 0) | Score (W ≥ 0) | Recommended Polarity | Optimal Biasing Direction |",
        "| :--- | :---: | :---: | :---: | :--- |",
    ]
    for c_id in sorted(summ.keys()):
        item = summ[c_id]
        rec = item["recommended_side"].upper()
        dir_text = "Positive sigmoid knee (+)" if rec == "POS" else "Negative sigmoid knee (-)"
        lines.append(f"| **{c_id}** | {item['score_neg']:.1f} | {item['score_pos']:.1f} | **{rec}** | {dir_text} |")

    lines.extend([
        "",
        "---",
        "",
        "## 3. Diagnostic Visualizations",
        "",
        "- Full 48-Cell Transfer Grid: `FPGA_code/docs/figures/fig_m3_sigmoid_step1_48cell_grid.png`",
        "- Dynamic Swing and Jerk Heatmaps: `FPGA_code/docs/figures/fig_m3_sigmoid_step1_heatmaps.png`",
        "- Column-Wise Quality Comparison: `FPGA_code/docs/figures/fig_m3_sigmoid_step1_column_summary.png`",
        "",
        "---",
        "",
        "## 4. Next Step: Steg 2 Column Collective S-Curve",
        "",
        "Now proceeding to Steg 2: sweeping all rows collectively on each column ($W_3[0..7][c]$ ramped together) across $X = \\pm 127$ and $X = \\pm 64$ to observe the full macroscopic sigmoid curve and locate the optimal baseline knee vector $\\mathbf{W}_{3,\\text{baseline}}$.",
    ])
    with open(MD_PATH, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[+] Saved Markdown report -> {MD_PATH}")


def main():
    if not DATA_PATH.exists():
        print(f"Error: {DATA_PATH} not found.")
        sys.exit(1)
    with open(DATA_PATH, "r") as f:
        data = json.load(f)
    build_pdf(data)
    build_md(data)


if __name__ == "__main__":
    main()

