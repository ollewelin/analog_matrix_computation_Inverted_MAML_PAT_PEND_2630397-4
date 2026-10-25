#!/usr/bin/env python3
"""
Generates publication-quality multi-page PDF report in English:
  FPGA_code/docs/MODE_A_5MS_INNER_LOOP_VERIFICATION_REPORT_3.pdf
matching FPGA_code/docs/MODE_A_5MS_INNER_LOOP_VERIFICATION_REPORT_3.md.
"""

import shutil
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DOCS_DIR = REPO_ROOT / "FPGA_code" / "docs"
FIG_DIR = DOCS_DIR / "figures"
PDF_PATH = DOCS_DIR / "MODE_A_5MS_INNER_LOOP_VERIFICATION_REPORT_3.pdf"
ARTIFACT_DIR = Path("/home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a")

FIG_CONV = FIG_DIR / "fig_mode_a_5ms_inner_loop_convergence_run3.png"
FIG_TRAJ = FIG_DIR / "fig_mode_a_5ms_6col_error_trajectories_run3.png"
FIG_ATT  = FIG_DIR / "fig_mode_a_1k_3k9_attenuator_verification_run3.png"


def add_header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#64748B"))

    canvas.drawString(
        14 * mm,
        287 * mm,
        "Inverted MAML Analog Matrix — Mode A (t = 5.0 ms) Verification Report 3",
    )
    canvas.drawRightString(210 * mm - 14 * mm, 287 * mm, "2026-10-24 | Efinix Trion T120 + T20")
    canvas.setStrokeColor(colors.HexColor("#CBD5E1"))
    canvas.setLineWidth(0.5)
    canvas.line(14 * mm, 285 * mm, 210 * mm - 14 * mm, 285 * mm)

    canvas.line(14 * mm, 12 * mm, 210 * mm - 14 * mm, 12 * mm)
    canvas.drawString(
        14 * mm,
        8 * mm,
        "Inverted MAML Research — PAT. PEND. SE 2630397-4 | 100% Pure Physical Silicon Telemetry",
    )
    canvas.drawRightString(210 * mm - 14 * mm, 8 * mm, f"Page {canvas._pageNumber}")
    canvas.restoreState()


def build_pdf():
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=15.5,
        leading=19.5,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=6,
    )
    h2_style = ParagraphStyle(
        "SecH2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11.5,
        leading=14.5,
        textColor=colors.HexColor("#1E3A8A"),
        spaceBefore=9,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.2,
        leading=13.0,
        textColor=colors.HexColor("#1E293B"),
        spaceAfter=4,
    )
    bullet_style = ParagraphStyle(
        "BulletItem",
        parent=body_style,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=3.5,
    )
    callout_style = ParagraphStyle(
        "Callout",
        parent=body_style,
        backColor=colors.HexColor("#F1F5F9"),
        borderColor=colors.HexColor("#1E3A8A"),
        borderWidth=0.8,
        borderPadding=6,
        spaceBefore=4,
        spaceAfter=6,
    )

    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=18 * mm,
        bottomMargin=16 * mm,
    )
    story = []

    # Title & Header Metadata
    story.append(
        Paragraph(
            "Mode A (t = 5.0 ms) Inner-Loop Verification Report 3 (Fresh Bitstream Flash)",
            title_style,
        )
    )
    story.append(
        Paragraph(
            "<b>Date:</b> 2026-10-24 &nbsp;|&nbsp; "
            "<b>Hardware:</b> Inverted MAML Analog Matrix (192.168.1.50:5000, Trion T120F324 + T20F256)<br/>"
            "<b>Operating Mode:</b> Mode A (jumper_mode = 3 — Active compensation via Matrix 3, Sigmoid 4, Matrix 8, Sigmoid 10, and 1 kΩ / 3.9 kΩ summing junction)<br/>"
            "<b>Operating Point:</b> t = 5.0 ms (hadamard_delay_us = 5000, 100 Hz / 10.0 ms synchronous capacitor refresh) &nbsp;|&nbsp; "
            "<b>Active Columns:</b> All 6 columns (j = 0..5) active simultaneously (zero column masking)",
            body_style,
        )
    )
    story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#CBD5E1"), spaceAfter=5))

    # Section 1
    story.append(Paragraph("1. Executive Summary & Silicon Flash Verification", h2_style))
    story.append(
        Paragraph(
            "Following a complete bitstream re-flash directly from <b>outflow/T120_MALM.hex</b> onto physical silicon, "
            "<b>Run 3</b> was executed across all 6 columns at t = 5.0 ms under pure forward Hadamard gradient dynamics "
            "according to Patent Application <b>SE 2630397-4</b>:",
            body_style,
        )
    )

    comp_data = [
        ["Metric (All 6 columns, t = 5.0 ms)", "Run 1 (Report 1)", "Run 2 (Report 2)", "Run 3 (Report 3 — Fresh Flash)"],
        ["Step 0 Centered Loss L_0", "8 870.9 LSB²", "6 133.1 LSB²", "6 517.1 LSB²"],
        ["Best Converged Loss L_min", "324.5 LSB²", "657.7 LSB²", "661.4 LSB²"],
        ["Relative Loss Reduction", "-96.3 %", "-89.3 %", "-89.9 %"],
        ["Step 0 6-Column RMSE", "54.38 LSB", "45.21 LSB", "46.61 LSB"],
        ["Best 6-Column RMSE", "10.40 LSB (Step 18)", "14.81 LSB (Step 8)", "14.85 LSB (Step 14)"],
        ["Final Settled RMSE (Step 20)", "16.04 LSB", "21.67 LSB", "16.96 LSB"],
        ["Step 0 Effective Number of Bits (ENOB)", "5.24 bits", "5.50 bits", "5.46 bits"],
        ["Peak ENOB During Inner Loop", "7.62 bits (+2.38)", "7.11 bits (+1.61)", "7.11 bits (+1.65)"],
    ]
    t_comp = Table(comp_data, colWidths=[66 * mm, 38 * mm, 38 * mm, 40 * mm])
    t_comp.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.0),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("BACKGROUND", (3, 1), (3, -1), colors.HexColor("#EFF6FF")),
                ("FONTNAME", (3, 1), (3, -1), "Helvetica-Bold"),
                ("TOPPADDING", (0, 0), (-1, -1), 3.2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.2),
            ]
        )
    )
    story.append(t_comp)
    story.append(Spacer(1, 5))

    if FIG_CONV.exists():
        story.append(Image(str(FIG_CONV), width=182 * mm, height=59 * mm))
        story.append(Spacer(1, 5))

    # Section 2
    story.append(Paragraph("2. Simultaneous 6-Column Bidirectional Weight Adaptation", h2_style))
    story.append(
        Paragraph(
            "<b>Bidirectional Vernier Compensation Confirmed:</b> In Run 3, the initial random input vector created "
            "both <b>negative output errors</b> on Column 0 (-44.2 LSB) and Column 2 (-99.0 LSB) as well as "
            "<b>positive output errors</b> on Column 5 (+24.8 LSB), Column 4 (+12.8 LSB), Column 3 (+6.2 LSB) and Column 1 (-21.5 LSB). "
            "The non-backprop Hadamard gradient autonomously drove weights W_8[c,c] <b>upward</b> on Column 0 (24 -> 31) "
            "and Column 2 (24 -> 28), and <b>downward</b> on Column 4 (24 -> 17) and Column 5 (24 -> 21).",
            callout_style,
        )
    )

    if FIG_TRAJ.exists():
        story.append(Image(str(FIG_TRAJ), width=182 * mm, height=65 * mm))
        story.append(Spacer(1, 5))

    traj_data = [
        ["Step", "Er_0 (Col 0)", "Er_1 (Col 1)", "Er_2 (Col 2)", "Er_3 (Col 3)", "Er_4 (Col 4)", "Er_5 (Col 5)", "6-Col RMSE", "Loss L (LSB²)", "ENOB"],
        ["0 (Base)", "-44.2", "-21.5", "-99.0", "+6.2", "+12.8", "+24.8", "46.61 LSB", "6 517.1", "5.46 bits"],
        ["1", "-36.0", "-11.5", "-80.8", "+3.8", "+24.5", "+23.5", "39.00 LSB", "4 561.9", "5.71 bits"],
        ["3", "-33.2", "-28.8", "-67.0", "-24.5", "+0.8", "+27.2", "35.97 LSB", "3 880.7", "5.83 bits"],
        ["4", "-18.5", "-11.8", "-66.2", "+12.8", "+22.0", "+1.0", "30.31 LSB", "2 756.4", "6.08 bits"],
        ["6", "-24.8", "-26.2", "-39.2", "-13.2", "+4.0", "+17.8", "23.61 LSB", "1 672.6", "6.44 bits"],
        ["9", "-15.8", "-23.5", "-29.8", "+4.5", "+5.8", "+11.8", "17.72 LSB", "941.5", "6.85 bits"],
        ["12", "-4.2", "-24.5", "-29.0", "-5.2", "+24.5", "-9.0", "19.01 LSB", "1 083.6", "6.75 bits"],
        ["14 (Best)", "+19.2", "-10.5", "-27.5", "+2.8", "+5.8", "+6.8", "14.85 LSB", "661.4", "7.11 bits"],
        ["19", "+9.5", "-26.2", "-22.5", "+1.5", "+6.8", "+14.0", "15.96 LSB", "763.7", "7.00 bits"],
        ["20 (Final)", "+1.0", "-18.8", "-30.5", "+0.2", "+14.2", "+15.5", "16.96 LSB", "863.3", "6.92 bits"],
    ]
    t_traj = Table(traj_data, colWidths=[18 * mm] + [16.5 * mm] * 6 + [22 * mm, 21 * mm, 22 * mm])
    t_traj.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.8),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("BACKGROUND", (0, 8), (-1, 8), colors.HexColor("#DCFCE7")),
                ("FONTNAME", (0, 8), (-1, 8), "Helvetica-Bold"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(t_traj)
    story.append(Spacer(1, 6))

    # Section 3
    story.append(Paragraph("3. Passive Summing Network (1 kΩ / 3.9 kΩ) & Firmware Verification", h2_style))
    if FIG_ATT.exists():
        story.append(Image(str(FIG_ATT), width=182 * mm, height=64 * mm))
        story.append(Spacer(1, 4))

    story.append(
        Paragraph(
            "• <b>Primary Attenuation Path (M33 -> 1.0 kΩ):</b> Attenuation factor ~0.70-0.78x (theoretical 3.9/4.9 = 0.7959x).",
            bullet_style,
        )
    )
    story.append(
        Paragraph(
            "• <b>Vernier Compensation Path (M8 -> Sigmoid 10 -> 3.9 kΩ):</b> Attenuation factor ~0.204x (theoretical 1.0/4.9 = 0.2041x). "
            "Provides ultra-fine ±50 LSB correction authority without saturating the single-supply ADC_49.",
            bullet_style,
        )
    )
    story.append(
        Paragraph(
            "• <b>Strict Non-Backprop Hadamard Extraction (Equations 1-7):</b> Verified in live firmware — zero digital multiplication by x_i. "
            "Carrier Wave Search on ADC_45 extracts Sigmoid 10 column slopes σ_2'(y_j) without knowledge of unobserved weights.",
            bullet_style,
        )
    )

    doc.build(story, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
    shutil.copy2(PDF_PATH, ARTIFACT_DIR / "MODE_A_5MS_INNER_LOOP_VERIFICATION_REPORT_3.pdf")
    print(f"Generated PDF report 3: {PDF_PATH}")


if __name__ == "__main__":
    build_pdf()

