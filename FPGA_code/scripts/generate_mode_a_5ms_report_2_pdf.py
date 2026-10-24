#!/usr/bin/env python3
"""
Generates publication-quality multi-page PDF report:
  FPGA_code/docs/MODE_A_5MS_INNER_LOOP_VERIFICATION_REPORT_2.pdf
matching FPGA_code/docs/MODE_A_5MS_INNER_LOOP_VERIFICATION_REPORT_2.md.
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
PDF_PATH = DOCS_DIR / "MODE_A_5MS_INNER_LOOP_VERIFICATION_REPORT_2.pdf"
ARTIFACT_DIR = Path("/home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a")

FIG_CONV = FIG_DIR / "fig_mode_a_5ms_inner_loop_convergence_run2.png"
FIG_TRAJ = FIG_DIR / "fig_mode_a_5ms_6col_error_trajectories_run2.png"
FIG_ATT  = FIG_DIR / "fig_mode_a_1k_3k9_attenuator_verification_run2.png"


def add_header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#64748B"))

    canvas.drawString(
        14 * mm,
        287 * mm,
        "Inverted MAML Analog Matrix — Mode A (t = 5.0 ms) Verification Report 2",
    )
    canvas.drawRightString(210 * mm - 14 * mm, 287 * mm, "2026-10-24 | Efinix Trion T120 + T20")
    canvas.setStrokeColor(colors.HexColor("#CBD5E1"))
    canvas.setLineWidth(0.5)
    canvas.line(14 * mm, 285 * mm, 210 * mm - 14 * mm, 285 * mm)

    canvas.line(14 * mm, 12 * mm, 210 * mm - 14 * mm, 12 * mm)
    canvas.drawString(
        14 * mm,
        8 * mm,
        "Inverted MAML Research — PAT. PEND. SE 2630397-4 | 100% Pure Physical Hardware Telemetry (Run 2)",
    )
    canvas.drawRightString(210 * mm - 14 * mm, 8 * mm, f"Sida {canvas._pageNumber}")
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
            "Mode A (t = 5.0 ms) Inre Loop-Verifiering — Rapport 2 (Ny Flash- & Repeterbarhetsverifiering)",
            title_style,
        )
    )
    story.append(
        Paragraph(
            "<b>Datum:</b> 2026-10-24 &nbsp;|&nbsp; "
            "<b>Hårdvara:</b> Inverted MAML Analog Matrix (192.168.1.50:5000, Trion T120F324 + T20F256)<br/>"
            "<b>Byglingsläge:</b> Mode A (jumper_mode = 3 — Aktiv kompensationsslinga via Matris 3, Sigmoid 4, Matris 8, Sigmoid 10 och 1 kΩ / 3.9 kΩ summeringsnät)<br/>"
            "<b>Arbetspunkt:</b> t = 5.0 ms (hadamard_delay_us = 5000, 100 Hz / 10.0 ms synkron kondensatoruppdatering) &nbsp;|&nbsp; "
            "<b>Kolumnomfattning:</b> Samtliga 6 kolumner (j = 0..5) aktiva (noll kolumnmaskering)",
            body_style,
        )
    )
    story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#CBD5E1"), spaceAfter=5))

    # Section 1
    story.append(Paragraph("1. Syfte och Jämförelse Mellan Körning 1 och Körning 2", h2_style))
    story.append(
        Paragraph(
            "Efter att <b>maml_platform.c</b> verifierats, kompilerats om från källkod och nyprogrammerats till "
            "T120F324 via JTAG (<b>flash_soc.py</b>) genomfördes ett nytt, oberoende verifieringsvarv (<b>Körning 2</b>) "
            "med nya slumpade vitbrus-insignaler x_ref över samtliga 6 kolumner vid t = 5.0 ms:",
            body_style,
        )
    )

    comp_data = [
        ["Metrik (Alla 6 kolumner, t = 5.0 ms)", "Körning 1 (Rapport 1)", "Körning 2 — Omgång A", "Körning 2 — Omgång B", "Körning 2 — Omgång C"],
        ["Steg 0 Centrerad Förlust L_0", "8 870.9 LSB²", "20 094.2 LSB²", "9 449.9 LSB²", "6 133.1 LSB²"],
        ["Bästa Konvergerade Förlust L_min", "324.5 LSB²", "3 257.7 LSB²", "1 592.1 LSB²", "657.7 LSB²"],
        ["Relativ Förlustreduktion", "-96.3 %", "-83.8 %", "-83.2 %", "-89.3 %"],
        ["Steg 0 6-Kolumners RMSE", "54.38 LSB", "81.84 LSB", "56.12 LSB", "45.21 LSB"],
        ["Bästa 6-Kolumners RMSE", "10.40 LSB (Steg 18)", "32.95 LSB (Steg 13)", "23.04 LSB (Steg 16)", "14.81 LSB (Steg 8)"],
        ["Slutlig 6-Kolumners RMSE (Steg 20)", "16.04 LSB", "44.56 LSB", "28.24 LSB", "21.67 LSB"],
        ["Steg 0 Effektiv Bithöjd (ENOB)", "5.24 bitar", "4.65 bitar", "5.19 bitar", "5.50 bitar"],
        ["Topp-ENOB under Inre Loop", "7.62 bitar (+2.38)", "5.96 bitar (+1.31)", "6.47 bitar (+1.28)", "7.11 bitar (+1.61)"],
    ]
    t_comp = Table(comp_data, colWidths=[56 * mm, 31.5 * mm, 31.5 * mm, 31.5 * mm, 31.5 * mm])
    t_comp.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.8),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("BACKGROUND", (4, 1), (4, -1), colors.HexColor("#EFF6FF")),
                ("FONTNAME", (4, 1), (4, -1), "Helvetica-Bold"),
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
    story.append(Paragraph("2. Verifiering av Bidirektionell Viktadaption över Alla 6 Kolumner", h2_style))
    story.append(
        Paragraph(
            "<b>Bidirektionell Vernier-styrning verifierad:</b> I Körning 2 (Omgång C) gav det slumpade insignalmönstret "
            "både <b>negativa initiala kolumnfel</b> på Kolumn 0 (-45.0 LSB) och Kolumn 2 (-87.8 LSB) samt "
            "<b>positiva initiala kolumnfel</b> på Kolumn 4 (+42.5 LSB), Kolumn 1 (+18.5 LSB), Kolumn 5 (+14.2 LSB) "
            "och Kolumn 3 (+13.5 LSB). Den icke-backprop-baserade Hadamard-gradienten styrde kompensationsvikterna "
            "W_8[c,c] automatiskt <b>uppåt</b> på Kolumn 0 (24 -> 31) och Kolumn 2 (24 -> 28) och <b>nedåt</b> på "
            "Kolumn 4 (24 -> 14), Kolumn 1 (24 -> 21) och Kolumn 5 (24 -> 21).",
            callout_style,
        )
    )

    if FIG_TRAJ.exists():
        story.append(Image(str(FIG_TRAJ), width=182 * mm, height=65 * mm))
        story.append(Spacer(1, 5))

    traj_data = [
        ["Steg", "Er_0 (Col 0)", "Er_1 (Col 1)", "Er_2 (Col 2)", "Er_3 (Col 3)", "Er_4 (Col 4)", "Er_5 (Col 5)", "6-Kol RMSE", "Förlust L", "ENOB"],
        ["0 (Start)", "-45.0", "+18.5", "-87.8", "+13.5", "+42.5", "+14.2", "45.21 LSB", "6 133.1", "5.50 bitar"],
        ["1", "-23.2", "+17.0", "-66.2", "-28.8", "+55.2", "+18.8", "39.66 LSB", "4 719.8", "5.69 bitar"],
        ["2", "-41.2", "+23.5", "-61.0", "-1.5", "+45.5", "+13.2", "37.01 LSB", "4 108.7", "5.79 bitar"],
        ["4", "-39.5", "+31.8", "-48.2", "+8.8", "+34.2", "+26.8", "33.81 LSB", "3 430.0", "5.92 bitar"],
        ["6", "+1.0", "+3.5", "-39.8", "-7.5", "+42.8", "-3.2", "24.14 LSB", "1 747.8", "6.41 bitar"],
        ["8 (Bäst)", "-14.0", "-9.8", "-27.2", "-4.5", "+14.0", "+8.2", "14.81 LSB", "657.7", "7.11 bitar"],
        ["10", "-17.0", "-5.0", "-35.5", "+9.8", "+19.5", "+14.0", "19.35 LSB", "1 123.3", "6.73 bitar"],
        ["11", "-21.2", "+8.5", "-43.2", "-3.5", "+14.5", "+9.8", "21.24 LSB", "1 353.2", "6.59 bitar"],
        ["19", "-14.2", "-15.0", "-31.8", "-0.2", "+34.2", "+11.5", "21.37 LSB", "1 369.9", "6.58 bitar"],
        ["20 (Slut)", "+11.8", "-12.2", "-41.8", "+5.2", "+24.8", "+11.8", "21.67 LSB", "1 408.3", "6.56 bitar"],
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
                ("BACKGROUND", (0, 6), (-1, 6), colors.HexColor("#DCFCE7")),
                ("FONTNAME", (0, 6), (-1, 6), "Helvetica-Bold"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(t_traj)
    story.append(Spacer(1, 6))

    # Section 3
    story.append(Paragraph("3. 1 kΩ / 3.9 kΩ-Summeringsdämparen & Verifierad Källkodsstatus", h2_style))
    if FIG_ATT.exists():
        story.append(Image(str(FIG_ATT), width=182 * mm, height=64 * mm))
        story.append(Spacer(1, 4))

    story.append(
        Paragraph(
            "• <b>HADAMARD_2X7_POS[7] och maml_fwht16_demodulate() (rad 475–657):</b> 2x7 = 14 interfolierade 2.00 µs "
            "Sylvester-H8-pulser med exakt Simplex-ortogonalisering (>> 1) och 0 % överhörning mellan rader.",
            bullet_style,
        )
    )
    story.append(
        Paragraph(
            "• <b>maml_measure_and_extract_gradients() (rad 674–841):</b> Sub-Window A (Matris 8 först, 0x3F00u) -> "
            "20 µs 3-State Hi-Z -> Sub-Window B (Matris 3 sedan, 0x003Fu), bärvågssökning best_k på ADC_45 (Ekvation 5 & 6) "
            "samt direkt Hadamard-felprodukt utan digital multiplicering med x_i (Ekvation 2 & 7).",
            bullet_style,
        )
    )
    story.append(
        Paragraph(
            "• <b>maml_center_compensation_weights() (rad 897–946):</b> Linjär +1.65 V-piedestal (M3 diagonal +64, "
            "rad 6 +48, M8 rader 0..5 +24) och 100 Hz synkron nollpunktskalibrering.",
            bullet_style,
        )
    )

    doc.build(story, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
    shutil.copy2(PDF_PATH, ARTIFACT_DIR / "MODE_A_5MS_INNER_LOOP_VERIFICATION_REPORT_2.pdf")
    print(f"Generated PDF report 2: {PDF_PATH}")


if __name__ == "__main__":
    build_pdf()
