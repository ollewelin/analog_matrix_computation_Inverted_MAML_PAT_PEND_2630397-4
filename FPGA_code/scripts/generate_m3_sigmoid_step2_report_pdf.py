#!/usr/bin/env python3
"""
generate_m3_sigmoid_step2_report_pdf.py
=======================================
Generates:
  1. Formal PDF Report: FPGA_code/docs/M3_SIGMOID_STEP2_COLUMN_SCURVE_REPORT.pdf
  2. Markdown Summary:  FPGA_code/docs/M3_SIGMOID_STEP2_COLUMN_SCURVE_REPORT.md
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
DATA_PATH = REPO_ROOT / "FPGA_code" / "logs" / "m3_sigmoid_characterization" / "step2_column_scurve.json"
PDF_PATH = DOCS_DIR / "M3_SIGMOID_STEP2_COLUMN_SCURVE_REPORT.pdf"
MD_PATH = DOCS_DIR / "M3_SIGMOID_STEP2_COLUMN_SCURVE_REPORT.md"

ARTIFACT_DIR = Path("/home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a")


def add_header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#64748B"))
    if canvas._pageNumber > 1:
        canvas.drawString(12 * mm, 287 * mm, "INVERTED MAML ANALOG MATRIX — PATENT PENDING SE 2630397-4")
        canvas.drawRightString(198 * mm, 287 * mm, "M3 Sigmoid Step 2 Report | Column S-Curve")
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
    story.append(Paragraph("M3 SIGMOID STEP 2: COLUMN S-CURVE & BASELINE OPTIMIZATION", title_style))
    story.append(Paragraph("Macroscopic Sigmoid S-Curve Characterization (Ref 4) on Differential ADC_45<br/>"
                           "<b>Optimal Baseline Initial Weight Vector W<sub>3,baseline</sub> for Inverted MAML</b>", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1E3A8A"), spaceAfter=10))

    # Executive Summary Box
    summary_text = (
        "<b>EXECUTIVE SUMMARY & OPERATIONAL FINDINGS:</b><br/>"
        "Steg 2 drives all rows on each column collectively (W3[0..7][c] ramped simultaneously) through the "
        "ColTIA and analog sigmoid activation network (Ref 4). By testing arbitrary medium-scale signals "
        "(X = &plusmn;64) alongside full-scale signals (X = &plusmn;127), we observe the true macroscopic S-curve "
        "and determine the precise baseline weight bias point W_base[c] where sensitivity is maximal and stochastic jitter is minimal. "
        "This calibrated vector will serve as the starting weights for compensation matrices and the center for future L2 regularization."
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

    # Figure: S-Curves
    story.append(Paragraph("1. Macroscopic Column S-Curves (X = &plusmn;127, &plusmn;64)", h1_style))
    fig_scurve = FIG_DIR / "fig_m3_sigmoid_step2_column_scurves.png"
    if fig_scurve.exists():
        story.append(Image(str(fig_scurve), width=186 * mm, height=130 * mm))
    story.append(Spacer(1, 10))

    # Quantitative Baseline Table
    story.append(Paragraph("2. Calibrated Baseline Weight Vector W<sub>3,baseline</sub>", h1_style))
    rec_w = data.get("recommended_baseline_w3", {})
    cols_data = data.get("columns", {})
    t_rows = [[
        Paragraph("Column", th_style),
        Paragraph("Optimal Knee W<sub>base</sub>", th_style),
        Paragraph("Best Polarity", th_style),
        Paragraph("Sensitivity @ X=&plusmn;64", th_style),
        Paragraph("Dynamic Swing (LSB)", th_style),
        Paragraph("Regularization Anchor", th_style),
    ]]
    for c_id in sorted(cols_data.keys()):
        cd = cols_data[c_id]
        pol = cd["best_polarity"].upper()
        w_opt = rec_w.get(c_id, 0)
        m = cd["metrics_x64_pos"] if pol == "POS" else cd["metrics_x64_neg"]
        t_rows.append([
            Paragraph(f"<b>{c_id}</b>", td_style),
            Paragraph(f"<b>{w_opt:+d} LSB</b>", td_style),
            Paragraph(f"<b>{pol} ({'+' if pol=='POS' else '-'})</b>", td_style),
            Paragraph(f"{m.get('knee_pos_gain' if pol=='POS' else 'knee_neg_gain', 0):.2f} LSB/W", td_style),
            Paragraph(f"{m.get('dynamic_lsb', 0):.0f} LSB", td_style),
            Paragraph(f"Pull toward {w_opt:+d}", td_style),
        ])
    col_table = Table(t_rows, colWidths=[22 * mm, 34 * mm, 28 * mm, 36 * mm, 34 * mm, 32 * mm])
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

    # Recommended Vector Summary
    story.append(Paragraph("3. Recommended Global Baseline Configuration", h1_style))
    vec_str = ", ".join([f"C{i}: {rec_w.get(f'C{i}', 0):+d}" for i in range(6)])
    vec_text = (
        f"<b>Calibrated Vector:</b> <code>[{vec_str}]</code><br/>"
        "By setting the compensation weights at these initial knee biases instead of 0, "
        "the analog gradient feedback immediately enters the responsive non-linear regime with maximum dynamic sensitivity "
        "and zero dead-band delay."
    )
    story.append(Paragraph(vec_text, body_style))

    doc.build(story, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
    print(f"[+] Successfully built PDF report -> {PDF_PATH}")
    if ARTIFACT_DIR.exists():
        shutil.copy(PDF_PATH, ARTIFACT_DIR / "M3_SIGMOID_STEP2_COLUMN_SCURVE_REPORT.pdf")


def build_md(data):
    rec_w = data.get("recommended_baseline_w3", {})
    cols_data = data.get("columns", {})
    duration = data.get("duration_s", 0)
    lines = [
        "# Matrix 3 Sigmoid Analog Activation Characterization Report (Ref 4)",
        "",
        "**Steg 2: Column Collective S-Curve Sweep & Optimal Baseline Starting Weights**  ",
        f"**Execution Environment:** Pure Physical Silicon (Trion T120 Master SoC @ 192.168.1.50:5000)  ",
        f"**Settled Snapshot Timing:** Locked strictly to nominal $t = 5.0\\text{{ ms}}$ ($5000\\ \\mu\\text{{s}}$)  ",
        f"**Total Execution Duration:** {duration/60:.1f} minutes  ",
        "",
        "---",
        "",
        "## 1. Executive Summary",
        "",
        "Steg 2 evaluated the macroscopic S-curve into the analog sigmoid activation (Ref 4) on differential ADC_45 by ramping all 8 rows of each column simultaneously ($W_3[0..7][c] = W$).",
        "By analyzing responses across full scale ($X = \\pm 127$) and medium scale ($X = \\pm 64$), we located the optimal knee/bend that achieves:",
        "1. **High Dynamic Sensitivity:** $|dY/dW| > 0$ for arbitrary inputs.",
        "2. **Minimal Stochastic Jitter:** Smooth, non-jerky analog transfer.",
        "3. **Optimal Anchor:** Initial baseline weights $\\mathbf{W}_{3,\\text{baseline}}$ for compensation matrices and future L2 regularization.",
        "",
        "---",
        "",
        "## 2. Calibrated Baseline Weight Vector Table",
        "",
        "| Column | Optimal Knee $W_{\\text{base}}$ | Polarity | Sensitivity ($X=\\pm 64$) | Dynamic Swing | Regularization Anchor |",
        "| :---: | :---: | :---: | :---: | :---: | :--- |",
    ]
    for c_id in sorted(cols_data.keys()):
        cd = cols_data[c_id]
        pol = cd["best_polarity"].upper()
        w_opt = rec_w.get(c_id, 0)
        m = cd["metrics_x64_pos"] if pol == "POS" else cd["metrics_x64_neg"]
        lines.append(f"| **{c_id}** | **{w_opt:+d} LSB** | **{pol}** | {m.get('knee_pos_gain' if pol=='POS' else 'knee_neg_gain', 0):.2f} LSB/W | {m.get('dynamic_lsb', 0):.0f} LSB | Pull toward {w_opt:+d} |")

    vec_str = ", ".join([f"C{i}: {rec_w.get(f'C{i}', 0):+d}" for i in range(6)])
    lines.extend([
        "",
        "### Final Baseline Vector:",
        f"```python",
        f"W3_BASELINE = [{vec_str}]",
        f"```",
        "",
        "---",
        "",
        "## 3. Visualizations",
        "",
        "- Column S-Curves: `FPGA_code/docs/figures/fig_m3_sigmoid_step2_column_scurves.png`",
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

