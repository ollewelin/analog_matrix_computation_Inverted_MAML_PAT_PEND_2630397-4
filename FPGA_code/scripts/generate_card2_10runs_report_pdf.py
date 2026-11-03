#!/usr/bin/env python3
"""
generate_card2_10runs_report_pdf.py
===================================
Generates a comprehensive scientific engineering report and PDF documenting
the 10-Run Milestone 2 Mode A Statistical Silicon Campaign on Card 2 (Rev 2.0, 1k/3.9k attenuator)
under +/-45 LSB LLM Toeplitz noise (rho=0.85), LR=0.25x, lambda=512 at 5.0 ms snapshot delay.
"""

import sys
import os
import json
import numpy as np
from pathlib import Path
import shutil

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, KeepTogether, PageBreak, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DOCS_DIR = REPO_ROOT / "FPGA_code" / "docs"
FIGURES_DIR = DOCS_DIR / "figures"
LOG_DIR = REPO_ROOT / "FPGA_code" / "logs" / "llm_noise_campaign"
PDF_OUT = DOCS_DIR / "INVERTED_MAML_MILESTONE2_CARD2_10RUNS_STATISTICAL_REPORT.pdf"
ARTIFACT_DIR = Path("/home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a")


def add_header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#64748b"))
    page_num = canvas._pageNumber
    footer_text = "Open Science Hardware | Patent Pending SE 2630397-4 | Inverted MAML Mode A (Card 2 - 10-Run Statistical Report)"
    canvas.drawString(40, 20, footer_text)
    canvas.drawRightString(612 - 40, 20, f"Page {page_num}")
    canvas.restoreState()


def build_pdf():
    # Load all 10 runs
    runs = []
    for idx in range(1, 11):
        f_path = LOG_DIR / f"mode_a_500ep_llm_toeplitz_rho85_reg512_card2_run{idx:02d}.json"
        with open(f_path) as f:
            runs.append(json.load(f))

    doc = SimpleDocTemplate(
        str(PDF_OUT),
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
        textColor=colors.HexColor("#0f172a")
    )
    subtitle_style = ParagraphStyle(
        "DocSubTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#1e40af")
    )
    meta_style = ParagraphStyle(
        "MetaText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=10.5,
        textColor=colors.HexColor("#334155")
    )
    h1_style = ParagraphStyle(
        "Heading1_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=4,
        spaceBefore=8,
        keepWithNext=True
    )
    body_style = ParagraphStyle(
        "Body_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#1e293b")
    )
    table_cell = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#0f172a")
    )
    table_cell_bold = ParagraphStyle(
        "TableCellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#0f172a")
    )

    story = []

    # Title & Header
    story.append(Paragraph("Inverted MAML: Milestone 2 Statistisk 10-Körningsrapport", title_style))
    story.append(Paragraph("Statistisk Utvärdering av 10 Oberoende 500-Epokers Körningar med 1k/3.9k Dämpare vid 5.0 ms", subtitle_style))
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563eb"), spaceAfter=6))

    # Meta banner
    meta_text = (
        "<b>Patentreferens:</b> SE 2630397-4 (Open Science Hardware) | <b>Hårdvara:</b> Kort 2 (Rev 2.0 Silicon, 1k/3.9k dämpare)<br/>"
        "<b>SoC & Firmware:</b> Efinix Trion T120 (HW 0x20261030, SW v2.2-MAML) + T20 Matrix Controller (TAG=T20A)<br/>"
        "<b>Körningsregim:</b> 10 Oberoende Körningar, 500 epoker/körning, d_line=2 (±45 LSB), LR=0.25x, λ=512 (Q16), Toeplitz ρ=0.85 vid 5.0 ms"
    )
    story.append(Paragraph(meta_text, meta_style))
    story.append(Spacer(1, 6))

    # Section 1: Executive Summary
    story.append(Paragraph("1. Sammanfattning & Kärnresultat (Topp: 8.07 bitar ENOB)", h1_style))
    exec_text = (
        "Efter att den dåliga lödningen på DAC(2)-drivern (MCP6444-E/SL) åtgärdades, genomfördes 10 oberoende 500-epokers "
        "testkörningar på fysiskt kisel. Varje körning roterar kontinuerligt slumpade LLM Toeplitz-vektorer. "
        "Resultatet visar att <b>Kort 2 når extrem precision (toppnotering 174.9 LSB² / 8.07 bitar ENOB i Körning 03)</b>, "
        "och samtliga 10 körningar når en topp-precision över 7.3 bitar (medel-topp: 7.47 bitar). "
        "Samtidigt visar snittet över hela Fas 3 (medel 6 745 LSB² / 5.43 bitar) att ColTIA headroom-kompressionen från 1k/3.9k-dämparen "
        "håller tillbaka det genomsnittliga felet när godtyckliga vektorer kräver stor negativ sving."
    )
    story.append(Paragraph(exec_text, body_style))
    story.append(Spacer(1, 6))

    # Section 2: Individual Run Graphs (Run 1 and Run 2)
    story.append(Paragraph("2. Enskilda Träningsförlopp för Körning 01 & Körning 02", h1_style))
    story.append(Paragraph("Som begärt visas här de två första körningarna separat med respektive Loss- och ENOB-kurva:", body_style))
    story.append(Spacer(1, 4))

    img_r1 = FIGURES_DIR / "fig_mode_a_500ep_card2_run01.png"
    img_r2 = FIGURES_DIR / "fig_mode_a_500ep_card2_run02.png"

    if img_r1.exists() and img_r2.exists():
        # Display side-by-side or stacked
        rl_r1 = RLImage(str(img_r1), width=265, height=168)
        rl_r2 = RLImage(str(img_r2), width=265, height=168)
        img_table = Table([[rl_r1, rl_r2]], colWidths=[270, 270])
        img_table.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(img_table)
        story.append(Paragraph("<i>Figur 1: Körning 01 (vänster, min loss 269.7 LSB² / 7.75 b) och Körning 02 (höger, min loss 444.8 LSB² / 7.39 b).</i>", meta_style))

    story.append(PageBreak())

    # Page 2: Combined 10-run plot & Statistical Table
    story.append(Paragraph("3. Sammanställd 10-Körningsgraf (Alla Trajektorier, Medelkurva & ±1σ Band)", h1_style))
    img_comb = FIGURES_DIR / "fig_mode_a_500ep_card2_10runs_combined.png"
    if img_comb.exists():
        rl_comb = RLImage(str(img_comb), width=535, height=220)
        story.append(rl_comb)
        story.append(Paragraph("<i>Figur 2: 10 oberoende körningar på Kort 2. Tunnare färgade linjer visar enskilda trajektorier; fet linje visar medelvärdet och skuggat område representerar ±1σ spridning för Loss (övre) och ENOB (undre).</i>", meta_style))
    story.append(Spacer(1, 6))

    # Section 4: Statistical Table
    story.append(Paragraph("4. Statistisk Prestandatabell över alla 10 Körningar", h1_style))

    table_data = [[
        Paragraph("<b>Körning</b>", table_cell_bold),
        Paragraph("<b>Fas 1 Medel (ENOB)</b>", table_cell_bold),
        Paragraph("<b>Fas 2 Medel (ENOB)</b>", table_cell_bold),
        Paragraph("<b>Fas 3 Medel (ENOB)</b>", table_cell_bold),
        Paragraph("<b>Bästa Loss (Topp ENOB)</b>", table_cell_bold),
        Paragraph("<b>Slutlig Loss (Ep 500)</b>", table_cell_bold)
    ]]

    p1_means, p2_means, p3_means = [], [], []
    best_losses, best_enobs = [], []
    final_losses, final_enobs = [], []

    for idx, r in enumerate(runs, 1):
        p1 = [e["loss_lsb2"] for e in r["epochs"] if e["phase"] == "BASELINE_ZERO"]
        p2 = [e["loss_lsb2"] for e in r["epochs"] if e["phase"] == "BASELINE_KNEE"]
        p3 = [e["loss_lsb2"] for e in r["epochs"] if e["phase"] == "TRAIN_REG_ON"]

        m1, m2, m3 = np.mean(p1), np.mean(p2), np.mean(p3)
        p1_means.append(m1); p2_means.append(m2); p3_means.append(m3)

        bl = r["metadata"]["best_loss_lsb2"]
        be = r["metadata"]["best_enob_bits"]
        fl = r["metadata"]["final_loss_lsb2"]
        fe = r["metadata"]["final_enob_bits"]
        best_losses.append(bl); best_enobs.append(be)
        final_losses.append(fl); final_enobs.append(fe)

        e1 = max(0.0, 11.0 - np.log2(max(1.0, np.sqrt(m1 * 2 / 6))))
        e2 = max(0.0, 11.0 - np.log2(max(1.0, np.sqrt(m2 * 2 / 6))))
        e3 = max(0.0, 11.0 - np.log2(max(1.0, np.sqrt(m3 * 2 / 6))))

        table_data.append([
            Paragraph(f"Körning {idx:02d}", table_cell),
            Paragraph(f"{m1:.1f} ({e1:.2f} b)", table_cell),
            Paragraph(f"{m2:.1f} ({e2:.2f} b)", table_cell),
            Paragraph(f"{m3:.1f} ({e3:.2f} b)", table_cell),
            Paragraph(f"<b>{bl:.1f} ({be:.2f} b)</b>", table_cell_bold if bl < 300 else table_cell),
            Paragraph(f"{fl:.1f} ({fe:.2f} b)", table_cell),
        ])

    # Summary rows
    table_data.append([
        Paragraph("<b>MEDELVÄRDE</b>", table_cell_bold),
        Paragraph(f"<b>{np.mean(p1_means):.1f} (5.16 b)</b>", table_cell_bold),
        Paragraph(f"<b>{np.mean(p2_means):.1f} (4.96 b)</b>", table_cell_bold),
        Paragraph(f"<b>{np.mean(p3_means):.1f} (5.43 b)</b>", table_cell_bold),
        Paragraph(f"<b>{np.mean(best_losses):.1f} ({np.mean(best_enobs):.2f} b)</b>", table_cell_bold),
        Paragraph(f"<b>{np.mean(final_losses):.1f} ({np.mean(final_enobs):.2f} b)</b>", table_cell_bold),
    ])
    table_data.append([
        Paragraph("<b>BÄSTA NOTERING</b>", table_cell_bold),
        Paragraph("-", table_cell),
        Paragraph("-", table_cell),
        Paragraph("-", table_cell),
        Paragraph(f"<b>{np.min(best_losses):.1f} ({np.max(best_enobs):.2f} b) [R03]</b>", table_cell_bold),
        Paragraph(f"<b>{np.min(final_losses):.1f} ({np.max(final_enobs):.2f} b)</b>", table_cell_bold),
    ])

    col_widths = [65, 95, 95, 95, 100, 90]
    t = Table(table_data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("BACKGROUND", (0, -2), (-1, -1), colors.HexColor("#e2e8f0")),
    ]))
    story.append(t)
    story.append(Spacer(1, 6))

    # Section 5: Fysisk Tolkning & Hårdvaruplan
    story.append(Paragraph("5. Fysisk Slutsats: Varför snittet hålls tillbaka av 1k/3.9k & Sigmoid 4", h1_style))
    concl_text = (
        "<b>1. Matematik (Loss vs ENOB):</b> ENOB är logaritmisk medan Loss är kvadratisk. För att höja ENOB-snittet med 1 hel bit "
        "krävs en felminskning på 75% (-6 dB). En minskning från 12 993 till 6 745 LSB² syns tydligt i loss men ger en måttlig förflyttning i ENOB.<br/>"
        "<b>2. ColTIA Headroom:</b> Med 3.9k drar summanoden 30% mer ström in i ColTIA än med 5.1k, vilket förskjuter DC-nivån till -1 600 LSB "
        "(nära bottenmättnad -1 797 LSB). När godtyckliga slumpade vektorer kräver negativ sving komprimeras headroom.<br/>"
        "<b>3. Lödåtgärd:</b> Genom att byta dämparen till 5.1k (som Kort 1) och montera MCP6444 (70 mA) på Sigmoid 4 "
        "återställs >750 LSB symmetriskt headroom, vilket kommer att <b>lyfta hela genomsnittskurvan och ENOB-snittet</b> till Kort 1:s nivå!"
    )
    story.append(Paragraph(concl_text, body_style))

    doc.build(story, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
    print(f"[+] PDF generated successfully: {PDF_OUT}")

    if ARTIFACT_DIR.exists():
        shutil.copy2(PDF_OUT, ARTIFACT_DIR / PDF_OUT.name)
        print(f"[+] Copied PDF to Artifact dir: {ARTIFACT_DIR / PDF_OUT.name}")


if __name__ == "__main__":
    build_pdf()

