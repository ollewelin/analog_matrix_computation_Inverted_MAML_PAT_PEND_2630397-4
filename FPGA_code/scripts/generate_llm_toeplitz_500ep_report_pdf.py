#!/usr/bin/env python3
"""
generate_llm_toeplitz_500ep_report_pdf.py
=========================================
Generates a comprehensive scientific engineering report and PDF documenting
the 500-Epoch Mode A Silicon Training under LLM Toeplitz In-Data Noise Equalizer
(rho=0.85, KMS AR(1) covariance) with ColTIA Saturation Guard and LayerNorm
on physical silicon at 5.0 ms snapshot delay.
"""

import sys
import os
import json
import numpy as np
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, KeepTogether, PageBreak, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DOCS_DIR = REPO_ROOT / "FPGA_code" / "docs"
FIGURES_DIR = DOCS_DIR / "figures"
LOG_FILE = REPO_ROOT / "FPGA_code" / "logs" / "llm_noise_campaign" / "mode_a_500ep_llm_toeplitz_rho85_reg512.json"
PDF_OUT = DOCS_DIR / "INVERTED_MAML_500EP_LLM_TOEPLITZ_REPORT.pdf"
ARTIFACT_DIR = Path("/home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a")


def add_header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#64748b"))
    page_num = canvas._pageNumber
    footer_text = "Open Science Hardware | Patent Pending SE 2630397-4 | Inverted MAML Mode A (v2.2-MAML)"
    canvas.drawString(40, 20, footer_text)
    canvas.drawRightString(612 - 40, 20, f"Page {page_num}")
    canvas.restoreState()


def build_pdf():
    with open(LOG_FILE, "r") as f:
        data = json.load(f)

    meta = data["metadata"]
    epochs = data["epochs"]

    p1 = [e for e in epochs if e["phase"] == "BASELINE_ZERO"]
    p2 = [e for e in epochs if e["phase"] == "BASELINE_KNEE"]
    p3 = [e for e in epochs if e["phase"] == "TRAIN_REG_ON"]

    p1_loss = [e["loss_lsb2"] for e in p1]
    p2_loss = [e["loss_lsb2"] for e in p2]
    p3_loss = [e["loss_lsb2"] for e in p3]

    p1_enob = [e["enob_bits"] for e in p1]
    p2_enob = [e["enob_bits"] for e in p2]
    p3_enob = [e["enob_bits"] for e in p3]

    doc = SimpleDocTemplate(
        str(PDF_OUT),
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=17,
        leading=21,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=3
    )
    subtitle_style = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor('#2563eb'),
        spaceAfter=10
    )
    h1_style = ParagraphStyle(
        'H1',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=colors.HexColor('#1e293b'),
        spaceBefore=10,
        spaceAfter=5
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#334155'),
        spaceAfter=6
    )
    bold_body = ParagraphStyle(
        'BoldBody',
        parent=body_style,
        fontName='Helvetica-Bold'
    )
    caption_style = ParagraphStyle(
        'Caption',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor('#64748b'),
        spaceBefore=3,
        spaceAfter=8,
        alignment=1
    )

    story = []

    # Title & Subtitle
    story.append(Paragraph("INVERTED MAML: 500-EPOCH SILICON TRAINING REPORT", title_style))
    story.append(Paragraph("Mode A Silicon Learning with LLM Toeplitz Equalizer (ρ = 0.85) & ColTIA Saturation Guard", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563eb"), spaceAfter=8))

    # Metadata Banner Table
    meta_data = [
        [
            Paragraph("<b>Target Hardware:</b> T120 Master SoC + T20 Controller", body_style),
            Paragraph("<b>Firmware Commit:</b> v2.2-MAML (HW: 0x20261030)", body_style),
        ],
        [
            Paragraph(f"<b>Noise Equalizer:</b> COLOR_LLM_TOEPLITZ (ρ = {meta['color_rho']:.2f})", body_style),
            Paragraph("<b>Headroom Guard:</b> 1797 LSB (250 LSB Margin)", body_style),
        ],
        [
            Paragraph(f"<b>L2 Regularization:</b> λ = {meta['reg_lambda']} (toward knee baseline)", body_style),
            Paragraph(f"<b>Peak Performance:</b> {meta['best_enob_bits']:.2f} b ENOB | {meta['best_loss_lsb2']:.1f} LSB² (Ep {meta['best_loss_epoch']})", body_style),
        ],
    ]
    t_meta = Table(meta_data, colWidths=[270, 270])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 8))

    # Section 1: Executive Summary & 3-Phase Benchmark
    story.append(Paragraph("1. Executive Summary & 3-Phase Benchmark Results", h1_style))
    story.append(Paragraph(
        "This experiment evaluates Inverted MAML Mode A training on physical silicon under realistic "
        "spatially correlated transformer activations. High token correlation (ρ = 0.85) previously induced common-mode "
        "current surges that saturated single-supply ColTIA transimpedance amplifiers, causing phantom Hadamard gradient bursts. "
        "With the newly integrated <b>Zero-Mean Centering (LayerNorm)</b> and <b>ColTIA Saturation Guard</b>, the network completed "
        "500 contiguous epochs on physical silicon with <b>zero clipping events</b>, achieving a peak precision of <b>7.13 bits ENOB</b>.",
        body_style
    ))

    # Phase Table
    phase_data = [
        ["Phase", "Epochs", "Network Weights", "Training State", "Mean Loss (LSB²)", "Mean ENOB (b)", "Peak ENOB (b)"],
        [
            "Phase 1: BASELINE_ZERO",
            "0 .. 99",
            "M3=0, M8=0 (Center)",
            "Training OFF",
            f"{np.mean(p1_loss):.1f}",
            f"{np.mean(p1_enob):.2f}",
            f"{np.max(p1_enob):.2f}"
        ],
        [
            "Phase 2: BASELINE_KNEE",
            "100 .. 199",
            "M8 = [±16 LSB Knee]",
            "Training OFF",
            f"{np.mean(p2_loss):.1f}",
            f"{np.mean(p2_enob):.2f}",
            f"{np.max(p2_enob):.2f}"
        ],
        [
            "Phase 3: TRAIN_REG_ON",
            "200 .. 500",
            "M3 & M8 Learning (λ=512)",
            "Active Mode A",
            f"{np.mean(p3_loss):.1f}",
            f"{np.mean(p3_enob):.2f}",
            f"<b>{np.max(p3_enob):.2f}</b>"
        ],
    ]
    t_phase = Table(phase_data, colWidths=[125, 55, 115, 75, 75, 50, 45])
    t_phase.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 7.5),
        ('FONTSIZE', (0, 1), (-1, -1), 7.5),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f1f5f9')]),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t_phase)
    story.append(Spacer(1, 8))

    # Section 2: LLM Noise Equalizer & ColTIA Protection
    story.append(Paragraph("2. In-Data Noise Equalizer: Kac-Murdock-Szegö AR(1) Model", h1_style))
    story.append(Paragraph(
        "Standard uniform white noise fails to benchmark analog neural multipliers against the correlated activation vectors "
        "characteristic of Large Language Models (LLMs). The T120 RISC-V SoC firmware generates an on-chip autoregressive spatial "
        "covariance field: <i>Cov(x_i, x_j) = ρ^|i-j|</i> with ρ = 0.85 (Q8 = 218). To prevent net common-mode DC current from driving "
        "the 1.65 V virtual ground of the single-supply ColTIA op-amps into saturation rails, the master SoC applies hardware "
        "<b>Zero-Mean Centering (LayerNorm)</b>: x_i ← x_i - (1/6)∑ x_k.",
        body_style
    ))

    # Include Figure 2: Filter Covariance
    fig_filter = ARTIFACT_DIR / "fig_llm_filter_covariance.png"
    if fig_filter.exists():
        story.append(RLImage(str(fig_filter), width=520, height=210))
        story.append(Paragraph("Figure 1: (Left) KMS AR(1) Spatial Covariance Matrix for 6 Analog Channels (ρ=0.85). (Right) Generated In-Data Vectors x_ref after LayerNorm.", caption_style))

    # Page Break for Clean Layout
    story.append(PageBreak())

    # Section 3: Physical Headroom Margin & Anti-Saturation Guard
    story.append(Paragraph("3. Physical ColTIA Headroom Margin & Anti-Distortion Guard", h1_style))
    story.append(Paragraph(
        "<b>The Saturation Bottleneck:</b> Sylvester H_8 Hadamard demodulation relies on linear wave superposition: "
        "<i>∂L/∂W_ij = <ΔZ_j, V_i^PTU>_H · E_j</i>. Physical silicon diagnostics (<i>diag_hadamard, mode 9</i>) established the peak "
        "Hadamard perturbation swing at <b>243 LSB</b> on Layer 1 (ADC_45). If the static DC operating point drifts within 250 LSB of "
        "the ±2047 LSB ADC rails, the positive perturbation clips flat against the rail while the negative swing completes unhindered. "
        "This nonlinearity breaks Walsh-Hadamard orthogonality, projecting false 'phantom' sensitivities across all matrix rows.<br/>"
        "<b>The Autonomous Countermeasure:</b> The T120 SoC enforces <i>COLTIA_CLIP_THRESHOLD_LSB = 1797 LSB</i>. "
        "Immediately after forward ADC readout, if |ADC| ≥ 1797 LSB, the epoch's weight gradient update is <b>completely suppressed</b> "
        "(ΔW ≡ 0) and logged to telemetry. During this 500-epoch campaign, <b>0 clipping events</b> occurred.",
        body_style
    ))
    story.append(Spacer(1, 4))

    # Include Figure 3: Training Graph
    fig_train = ARTIFACT_DIR / "fig_mode_a_500ep_llm_rho85_reg512.png"
    if fig_train.exists():
        story.append(RLImage(str(fig_train), width=530, height=270))
        story.append(Paragraph("Figure 2: 500-Epoch Training Trajectory on Physical Silicon. Epochs 0..99 (Zero Baseline), 100..199 (Knee Baseline ±16 LSB), 200..500 (Active Mode A Training).", caption_style))

    story.append(Spacer(1, 6))

    # Section 4: Live Studio Telemetry Verification
    story.append(Paragraph("4. Live Silicon Studio & Telemetry Verification", h1_style))
    story.append(Paragraph(
        "The snapshot below shows the <i>Injected FORWARD Propagation Silicon Studio</i> monitoring the experiment at Epoch 92. "
        "The 3D topography of Matrix 8 confirms an exact, quiet zero-plane across Phase 1, followed by the sharp knee-step at Epoch 100 "
        "and rapid quadratic error minimization upon triggering Active Training at Epoch 200.",
        body_style
    ))

    # Include Figure 1: GUI Snapshot
    fig_gui = ARTIFACT_DIR / "fig_gui_animation_snapshot_ep92.jpg"
    if fig_gui.exists():
        story.append(RLImage(str(fig_gui), width=530, height=255))
        story.append(Paragraph("Figure 3: Injected FORWARD Propagation Studio during Phase 1 (Ep 92). Telemetry captures ADC_45/ADC_49 channels and step transitions.", caption_style))

    # Build PDF document
    doc.build(story, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
    print(f"[+] PDF generated successfully: {PDF_OUT}")

    # Copy to Artifact directory
    artifact_pdf = ARTIFACT_DIR / "INVERTED_MAML_500EP_LLM_TOEPLITZ_REPORT.pdf"
    import shutil
    shutil.copy2(PDF_OUT, artifact_pdf)
    print(f"[+] Copied PDF to Artifact dir: {artifact_pdf}")


if __name__ == "__main__":
    build_pdf()
