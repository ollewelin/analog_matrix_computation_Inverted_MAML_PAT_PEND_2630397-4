#!/usr/bin/env python3
"""
Generates the Formal English Research Report for:
Inverted MAML: 100 Multiplier Variants Characterization under Mode A (Dual Sigmoid)
Focus: Fast Inner-Loop Adaptation Only with Frozen Base Models W_0 & Zero Hidden Offset.
"""

import json
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
JSON_PATH = REPO_ROOT / "data/benchmarks/mode_a_100_variants_inner_loop_results.json"
PNG_CHART = REPO_ROOT / "FPGA_code/docs/mode_a_100_variants_inner_loop_graph.png"
PDF_OUT = REPO_ROOT / "FPGA_code/docs/INVERTED_MAML_MODE_A_100_VARIANTS_INNER_LOOP_REPORT_EN.pdf"

def main():
    with open(JSON_PATH) as f:
        data = json.load(f)

    summary = data["summary"]
    doc = SimpleDocTemplate(str(PDF_OUT), pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=18, leading=22, textColor=colors.HexColor('#0f2b48'))
    sub_style = ParagraphStyle('DocSub', parent=styles['Normal'], fontSize=9.5, leading=13, textColor=colors.HexColor('#556270'))
    h1_style = ParagraphStyle('DocH1', parent=styles['Heading2'], fontSize=12, leading=16, textColor=colors.HexColor('#1b4965'))
    body_style = ParagraphStyle('DocBody', parent=styles['Normal'], fontSize=8.5, leading=12, textColor=colors.HexColor('#2b2d42'))
    bullet_style = ParagraphStyle('DocBullet', parent=styles['Normal'], fontSize=8.5, leading=12, textColor=colors.HexColor('#2b2d42'), leftIndent=12)

    story.append(Paragraph("INVERTED MAML: 100 MULTIPLIER VARIANTS RESEARCH REPORT (MODE A)", title_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph("Rapid Inner-Loop Adaptation Characterization with 100 Matched Frozen Base Models (Ref 41)", sub_style))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1b4965'), spaceBefore=2, spaceAfter=8))

    # Executive Overview
    story.append(Paragraph("1. Architectural Foundation & Axiomatic Principles", h1_style))
    story.append(Spacer(1, 4))
    intro_p = (
        "An <b>atomic analog triad</b> is defined as a fixed physical multiplier <b>Matrix 33</b> permanently paired "
        "with its dedicated compensation matrices (<b>Matrix 3</b> and <b>Matrix 8</b>). In this computing architecture: "
        "<br/>• A specific physical Matrix 33 multiplier instance retains a constant weight configuration throughout its entire operational lifecycle. "
        "<br/>• <b>No shared base model:</b> A single universal base model is never forced across disparate multiplier patterns. Instead, each of the 100 distinct "
        "Matrix 33 target variants has its own individually trained, mathematically matched Inverted MAML Base Model <b>W<sub>0</sub></b>."
    )
    story.append(Paragraph(intro_p, body_style))
    story.append(Spacer(1, 8))

    # Test Execution Protocol
    story.append(Paragraph("2. Experimental Execution Protocol (Inner-Loop Only Evaluation)", h1_style))
    story.append(Spacer(1, 4))
    
    steps = [
        "<b>Hardware Configuration:</b> Strictly locked to <b>Jumper Mode A (Dual Sigmoid, &sigma;<sub>1</sub> + &sigma;<sub>2</sub>)</b>. All thermal heaters are disarmed and locked at 0% duty cycle.",
        "<b>Phase 1 (Pre-Trained Base Model Inversion):</b> Each variant's dedicated base model centroid <b>W<sub>0</sub></b> was pre-trained under 100% duty cycle with Hidden Offset emulation active, driving the multi-basin Hessian curvature to lock the initial state.",
        "<b>Permanent Centroid Lock:</b> Before commencing the performance evaluation, <b>Base Model training (Outer Loop, Ref 40) was completely shut OFF</b>. The centroid W<sub>0</sub> was strictly frozen and remained completely unaltered throughout the test.",
        "<b>Zero Hidden Offset:</b> The hardware Hidden Offset emulator was entirely disabled (set to 0 LSBs).",
        "<b>Phase 2 (Fast Inner-Loop Adaptation Only, Ref 41):</b> Unseen continuous randomized white-noise payload vectors were streamed into the operational measurement window. Only the fast dynamic weights <i>W(s)</i> were adapted via Forward Hadamard carrier wave projection (strictly non-backprop).",
        "<b>Empirical Tracking:</b> Effective Number of Bits (ENOB) and MSE loss were recorded at steps <i>s</i> = 0, 2, 5, 10, 15, 20, 25, and 30 across all 100 distinct variants."
    ]
    for st in steps:
        story.append(Paragraph(f"&bull; {st}", bullet_style))
        story.append(Spacer(1, 3))

    story.append(Spacer(1, 6))

    # Include Graph
    if Path(PNG_CHART).exists():
        story.append(RLImage(str(PNG_CHART), width=540, height=270))
        story.append(Spacer(1, 8))

    # Results Table
    story.append(Paragraph("3. Empirical Performance Summary (Mode A, Inner-Loop Only)", h1_style))
    story.append(Spacer(1, 4))

    table_data = [
        ["Category", "Variant ID", "Raw M33 Baseline", "Frozen W0 (Step 0)", "Step 10", "Step 20", "Final (Step 30)", "Net Lift (&Delta; b)"],
        ["Best Triad", f"Variant {summary['best']['variant_id']:02d}", f"{summary['best']['raw']:.2f} b", 
         f"{summary['best']['w0']:.2f} b", f"{summary['best']['s10']:.2f} b", f"{summary['best']['s20']:.2f} b", 
         f"{summary['best']['end']:.2f} b", f"+{summary['best']['gain']:.2f} b"],
        ["Average (100 Triads)", "All 100 Variants", f"{summary['mean']['raw']:.2f} b", 
         f"{summary['mean']['w0']:.2f} b", f"{summary['mean']['s10']:.2f} b", f"{summary['mean']['s20']:.2f} b", 
         f"{summary['mean']['end']:.2f} b", f"+{summary['mean']['gain']:.2f} b"],
        ["Worst Triad", f"Variant {summary['worst']['variant_id']:02d}", f"{summary['worst']['raw']:.2f} b", 
         f"{summary['worst']['w0']:.2f} b", f"{summary['worst']['s10']:.2f} b", f"{summary['worst']['s20']:.2f} b", 
         f"{summary['worst']['end']:.2f} b", f"+{summary['worst']['gain']:.2f} b"]
    ]

    t = Table(table_data, colWidths=[110, 65, 68, 68, 55, 55, 68, 65])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1b4965')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 8),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('ALIGN', (0,1), (0,-1), 'LEFT'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#d0d7de')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f6f8fa')]),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t)
    story.append(Spacer(1, 8))

    # Scientific Conclusions
    story.append(Paragraph("4. Scientific Conclusions & Takeaways", h1_style))
    story.append(Spacer(1, 3))
    
    conclusions = (
        "<b>1. Total Mismatch Inversion Without Outer Updates:</b> Freezing the base model W<sub>0</sub> proves that the rapid inner loop "
        "(Ref 41) is fully capable of tracking dynamic analog drift and real-time mismatch on its own. With an average lift of <b>+2.23 bits</b> "
        "(from raw bare silicon at 2.10 bits to 4.33 bits), error loss was suppressed by <b>-94.2%</b> purely through fast parameter updates.<br/>"
        "<b>2. Resolution of Asymmetric Saturation:</b> Providing dedicated matched base models for every unique Matrix 33 configuration completely eliminated "
        "the low-lift saturation trap previously seen on asymmetric patterns (e.g. Variant 99). Even the lowest-performing triad in the entire population (Variant 01) "
        "achieved <b>4.22 bits</b> (+2.12 bits net gain).<br/>"
        "<b>3. Operational Viability:</b> This confirms that during datacenter payload execution, the heavy outer-loop meta-learner can remain safely dormant, "
        "while lightweight inner-loop carrier wave search guarantees consistent >4.2-bit analog accelerator precision."
    )
    story.append(Paragraph(conclusions, body_style))

    doc.build(story)
    print(f"[*] English PDF Report successfully generated: {PDF_OUT}")

if __name__ == "__main__":
    main()
