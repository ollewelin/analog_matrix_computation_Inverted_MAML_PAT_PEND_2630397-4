#!/usr/bin/env python3
"""
Generate a professional PDF Document illustrating the Research Team AI Agent Structure.
Output: FPGA_code/docs/RESEARCH_TEAM_AI_AGENT_STRUCTURE.pdf
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from pathlib import Path
import datetime

def create_agent_structure_pdf():
    pdf_path = Path("FPGA_code/docs/RESEARCH_TEAM_AI_AGENT_STRUCTURE.pdf")
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=32,
        bottomMargin=32
    )

    styles = getSampleStyleSheet()

    # Typography
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=17,
        leading=21,
        textColor=colors.HexColor('#0F172A'),
        alignment=TA_CENTER
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor('#475569'),
        alignment=TA_CENTER
    )

    h1_style = ParagraphStyle(
        'H1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#1E3A8A'),
        spaceBefore=7,
        spaceAfter=3
    )

    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#334155'),
        alignment=TA_JUSTIFY
    )

    bullet_style = ParagraphStyle(
        'Bullet',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11.5,
        textColor=colors.HexColor('#1E293B')
    )

    box_title = ParagraphStyle(
        'BoxTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#0F172A')
    )

    box_desc = ParagraphStyle(
        'BoxDesc',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor('#334155')
    )

    th_style = ParagraphStyle(
        'TH',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white,
        alignment=TA_CENTER
    )

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S CEST")

    story = []

    # Title & Header
    story.append(Paragraph("INVERTED MAML RESEARCH TEAM — MULTI-AGENT ARCHITECTURE", title_style))
    story.append(Spacer(1, 2))
    story.append(Paragraph("Autonomous Multi-Agent Organization, Responsibilities, and Adversarial Scientific Protocol", subtitle_style))
    story.append(Spacer(1, 2))
    story.append(Paragraph(f"<b>Patent Pending:</b> SE 2630397-4 &nbsp;|&nbsp; <b>Hardware:</b> Trion T120 SoC + T20 Coprocessor &nbsp;|&nbsp; <b>Date:</b> {now_str}", subtitle_style))
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1E3A8A'), spaceBefore=2, spaceAfter=6))

    # Architecture Overview
    intro_txt = ("The Inverted MAML research framework operates as a specialized multi-agent hierarchy designed to decouple strategic direction, physical hardware execution, mathematical modeling, and rigorous adversarial validation. This structure guarantees reproducible research, prevents confirmation bias, strictly enforces hardware safety (heaters disarmed, storage budgets < 100 KB), and ensures that physical jumper configurations (Modes A, B, and C) are respected at all times.")
    story.append(Paragraph(intro_txt, body_style))
    story.append(Spacer(1, 6))

    # Block Diagram Table (Visual representation)
    story.append(Paragraph("1. Multi-Agent Functional Block Architecture", h1_style))

    # 4 Pillars Table
    block_data = [
        [
            Paragraph("PILLAR 1: STRATEGIC LEADERSHIP", th_style),
            Paragraph("PILLAR 2: HARDWARE & EMULATION", th_style),
            Paragraph("PILLAR 3: ALGORITHM & DATA", th_style),
            Paragraph("PILLAR 4: ANTI-SIMULATION & AUDIT", th_style),
        ],
        [
            Paragraph("<b>maml_team_leader</b><br/>Overall picture, roadmap orchestration, and datacenter perspective.<br/><br/><b>maml_public_rep</b><br/>Public liaison, human reporting, and PDF dossier generation.<br/><br/><b>maml_research_planner</b><br/>Firmware changelog maintainer, scheduling, and gatekeeper.", box_desc),
            Paragraph("<b>maml_hardware_expert</b><br/><i>Primary Custodian for Jumper Modes A/B/C.</i> Enforces no-training rule in Mode B. Manages heater lockout (HEAT=0).<br/><br/><b>maml_hardware_emulator_expert</b><br/>Physical Hidden-Offset Emulation (Patent Fig. 7: W + Hidden_offset, DAC(2), trim-DAC 38) on real PCB.", box_desc),
            Paragraph("<b>maml_nn_specialist</b><br/>Inverted MAML outer loop 40, inner loop 41, and 2x6 Hadamard (24 us) gradient extraction.<br/><br/><b>maml_data_crawler</b><br/>UDP binary telemetry (0x4D414D4C), live hardware captures.<br/><br/><b>maml_data_analyzer</b><br/>Computes real SNR, derivatives, and ADC response metrics.", box_desc),
            Paragraph("<b>maml_anti_simulation_enforcer</b><br/><i>ZERO-SIMULATION WATCHDOG:</i> Strictly bans all software simulations and synthetic surrogates.<br/><br/><b>maml_bug_methodology_critic</b><br/><i>'The Devil's Advocate'</i>: Challenges oscilloscope signals, op-amp drive limits, and ADC settling.", box_desc),
        ]
    ]

    t_blocks = Table(block_data, colWidths=[135, 135, 135, 135])
    t_blocks.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#1E3A8A')),
        ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#B45309')),
        ('BACKGROUND', (2, 0), (2, 0), colors.HexColor('#2563EB')),
        ('BACKGROUND', (3, 0), (3, 0), colors.HexColor('#DC2626')),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#F8FAFC')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_blocks)
    story.append(Spacer(1, 6))

    # Detailed Responsibilities & Protocols
    story.append(Paragraph("2. Operational Responsibilities & Inter-Agent Protocols", h1_style))

    roles_data = [
        [
            Paragraph("Agent Name", th_style),
            Paragraph("Primary Mandate", th_style),
            Paragraph("Key Deliverables & Enforced Constraints", th_style)
        ],
        [
            Paragraph("<b>maml_anti_simulation_enforcer</b>", box_title),
            Paragraph("<b>Zero-Simulation Watchdog:</b> Total ban on all software simulations in measurements and NN training.", box_desc),
            Paragraph("<b>FORBIDS all synthetic surrogates.</b> Only real physical ADC measurements and real hardware hidden-offset emulation (Fig. 7) allowed.", box_desc)
        ],
        [
            Paragraph("<b>maml_team_leader</b>", box_title),
            Paragraph("Synthesizes overall research trajectory, balances model architecture with physical silicon limits.", box_desc),
            Paragraph("Ensures hardware-first verification and strict scientific honesty.", box_desc)
        ],
        [
            Paragraph("<b>maml_hardware_expert</b>", box_title),
            Paragraph("Hardware Custodian: Jumper Modes (A/B/C), analog multi-carrier buses, and thermal safety.", box_desc),
            Paragraph("<b>Enforces Jumper Mode B strict no-training rule.</b> Interlocks HEAT_1..4_EN to 0% duty at all times.", box_desc)
        ],
        [
            Paragraph("<b>maml_hardware_emulator_expert</b>", box_title),
            Paragraph("Physical Hardware Hidden-Offset Emulation (Patent Fig. 7 / Ref 38, 40, 41) on real DACs.", box_desc),
            Paragraph("Applies programmatic hidden offsets to physical 74HC595 DACs and trim-DAC 38. Emulation != Simulation.", box_desc)
        ],
        [
            Paragraph("<b>maml_nn_specialist</b>", box_title),
            Paragraph("Oversees non-backpropagation Hadamard gradient descent (Eqs. 1–7) on physical hardware.", box_desc),
            Paragraph("Implements contiguous 2x6 (12 x 2 us = 24 us) Hadamard bursts with zero tri-state gaps between pulses.", box_desc)
        ],
        [
            Paragraph("<b>maml_bug_methodology_critic</b>", box_title),
            Paragraph("Adversarial Skeptic: Audits oscilloscope traces, op-amp current drive, and ADC timing.", box_desc),
            Paragraph("Verifies that ADC sampling occurs strictly at the end of each 2 us pulse and within the flat post-refresh window.", box_desc)
        ],
        [
            Paragraph("<b>maml_research_planner</b>", box_title),
            Paragraph("Maintains system changelog, software builds, and execution sequence.", box_desc),
            Paragraph("Authors firmware_changelog.md with exact release dates, bitstream hashes, and hardware verification steps.", box_desc)
        ]
    ]

    t_roles = Table(roles_data, colWidths=[120, 185, 235])
    t_roles.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t_roles)
    story.append(Spacer(1, 6))

    # Core Principles
    story.append(Paragraph("3. Core Operational Directives", h1_style))
    directives = [
        "<b>1. Total Ban on Simulations:</b> Zero software simulations in measurements or NN training. Only physical hardware and real hidden weights (Patent Fig. 7) are permitted.",
        "<b>2. Contiguous 24 us Hadamard Table:</b> 2x6 pulses (6 (+) and 6 (-)), each exactly 2 us long with ADC sampling at the end of each 2 us pulse and zero tri-state gaps between pulses.",
        "<b>3. Zero Unsupervised Thermal Risk:</b> Power heaters (HEAT_1..4_EN) remain permanently disarmed (duty = 0) to protect hardware.",
        "<b>4. Jumper Discipline:</b> Mode B (bare silicon) is purely diagnostic; compensation weights are frozen to prevent divergence."
    ]
    for d in directives:
        story.append(Paragraph(f"&bull; {d}", bullet_style))
        story.append(Spacer(1, 1.5))

    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor('#94A3B8'), spaceBefore=2, spaceAfter=4))
    story.append(Paragraph(f"<i>Generated automatically by Inverted MAML AI System &bull; Timestamp: {now_str} &bull; Classification: Research Document</i>", ParagraphStyle('Foot', parent=styles['Normal'], fontSize=7, fontName='Helvetica-Oblique', textColor=colors.HexColor('#64748B'), alignment=TA_CENTER)))

    doc.build(story)
    print(f"PDF built successfully: {pdf_path} ({pdf_path.stat().st_size} bytes)")

if __name__ == '__main__':
    create_agent_structure_pdf()
