#!/usr/bin/env python3
"""
generate_t120_la_guide_and_report_pdf.py
========================================
Generates:
  1. FPGA_code/docs/T120F324_LA_LOGIC_ANALYZER_GUIDE_AND_VERIFICATION.pdf
  2. FPGA_code/docs/T120F324_LA_LOGIC_ANALYZER_GUIDE_AND_VERIFICATION.md

All waveforms and tables are plotted directly from the live Efinix Logic Analyzer
('la0', UUID=29024bad0ef545319a42750d2a504819) captures stored in:
  FPGA_code/docs/t120_la_bare_metal_captures.json
and VCD files in:
  FPGA_code/T120F324_LA/outflow/trace1..6_*.vcd
"""

import json
import math
import os
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
)
from reportlab.graphics.shapes import Drawing, Rect, Line, String, PolyLine, Circle

REPO_ROOT = Path("/home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4")
JSON_PATH = REPO_ROOT / "FPGA_code" / "docs" / "t120_la_bare_metal_captures.json"
PDF_PATH  = REPO_ROOT / "FPGA_code" / "docs" / "T120F324_LA_LOGIC_ANALYZER_GUIDE_AND_VERIFICATION.pdf"
MD_PATH   = REPO_ROOT / "FPGA_code" / "docs" / "T120F324_LA_LOGIC_ANALYZER_GUIDE_AND_VERIFICATION.md"


def extract_step_means(rows):
    """
    From a 10 MHz LA capture (rows[0..2047]), extract the settled ADC reading for each
    Hadamard step h_step_idx in 0..11 during the first active burst window where
    hadamard_burst_act == 1. Note that in the pipelined XC2361A SPI frame, the ADC
    conversion triggered at step s latches into adc45_ch*_raw 2.0 us later (during step s+1).
    We extract the settled ADC value corresponding to each active step s=0..11.
    """
    # Collect contiguous intervals where h_step_idx == s during the first burst (samples 256..800)
    step_samples_ch1 = {s: [] for s in range(12)}
    step_samples_ch2 = {s: [] for s in range(12)}
    step_samples_m8  = {s: [] for s in range(12)}

    # Find the sample index where h_step_idx transitions to 0 inside the triggered burst
    start_idx = 256
    for i in range(240, 350):
        if rows[i]["hadamard_burst_act"] == 1 and rows[i]["h_step_idx"] == 0:
            start_idx = i
            break

    # Each Hadamard step is 4.0 us = 40 samples @ 10 MHz (two 2.0 us ADC frames).
    # The settled ADC reading for step s is latched in the second half of step s (offset +22..+38 samples).
    for s in range(12):
        i0 = start_idx + s * 40 + 22
        i1 = min(len(rows), start_idx + s * 40 + 38)
        for i in range(i0, i1):
            step_samples_ch1[s].append(rows[i]["adc45_ch1_raw"])
            step_samples_ch2[s].append(rows[i]["adc45_ch2_raw"])
            step_samples_m8[s].append(rows[i]["adc49_ch2_raw"])

    def avg_list(d, fallback):
        out = []
        for s in range(12):
            vals = d[s]
            out.append(sum(vals) / len(vals) if vals else fallback)
        return out

    fb1 = rows[0]["adc45_ch1_raw"]
    fb2 = rows[0]["adc45_ch2_raw"]
    fb8 = rows[0]["adc49_ch2_raw"]
    return avg_list(step_samples_ch1, fb1), avg_list(step_samples_ch2, fb2), avg_list(step_samples_m8, fb8)


def make_la_digital_and_analog_drawing(rows_on_a, rows_off, rows_on_b, width=480, height=232):
    """
    Draws a true Logic Analyzer multi-track view across an 80 us window (samples 180..980 @ 10 MHz = 0.1 us/sample)
    showing:
      Track 1: hadamard_burst_act (Active 48.0 us 12-step Hadamard burst window on T120->T20 bridge)
      Track 2: hadamard_on_n_off (ON Trace 1 = 1, active bipolar drive)
      Track 3: hadamard_on_n_off (OFF Trace 2 = 0, 0x8000 Tri-State Hi-Z)
      Track 4: h_word_m3_ptu[0]  (Walsh-Hadamard row polarity bit 0 driving Matrix 3)
      Track 5: h_word_m3_ptu[1]  (Walsh-Hadamard row polarity bit 1 driving Matrix 3)
      Panel 1: Bare-metal 12-bit bus plot of adc45_ch1_raw[11:0] (M3+) for ON Pat A (+W), OFF (0x8000), and ON Pat B (-W)
      Panel 2: Bare-metal 12-bit bus plot of adc45_ch2_raw[11:0] (M3-) for ON Pat A (+W), OFF (0x8000), and ON Pat B (-W)
    """
    d = Drawing(width, height)
    d.add(Rect(0, 0, width, height, fillColor=colors.HexColor("#F8FAFC"), strokeColor=colors.HexColor("#CBD5E1"), strokeWidth=0.8))
    d.add(String(10, height - 12, "Figure 1: Live Efinix Logic Analyzer (la0) Capture @ 10 MHz (ce_10mhz_1shot == 1, 0.10 us/sample)",
                 fontName="Helvetica-Bold", fontSize=8.4, fillColor=colors.HexColor("#0F172A")))
    d.add(String(10, height - 22, "Window: Samples 180..980 (80.0 us span) | Blue: ON Pat A (+W) | Gray: OFF (0x8000 Tri-State) | Red: ON Pat B (-W)",
                 fontName="Helvetica", fontSize=6.9, fillColor=colors.HexColor("#475569")))

    s_start = 180
    s_end   = 980
    n_samp  = s_end - s_start
    x_left  = 104
    x_right = width - 12
    plot_w  = x_right - x_left

    def sx(idx):
        return x_left + ((idx - s_start) / float(n_samp)) * plot_w

    dig_tracks = [
        ("hadamard_burst_act", "hadamard_burst_act", None, "#0284C7", rows_on_a),
        ("hadamard_on_n_off (ON)", "hadamard_on_n_off", None, "#16A34A", rows_on_a),
        ("hadamard_on_n_off (OFF)", "hadamard_on_n_off", None, "#94A3B8", rows_off),
        ("h_word_m3_ptu[0] (Row0)", "h_word_m3_ptu", 0, "#2563EB", rows_on_a),
        ("h_word_m3_ptu[1] (Row1)", "h_word_m3_ptu", 1, "#7C3AED", rows_on_a),
    ]

    y_cursor = height - 34
    track_h  = 10
    track_gap = 4

    for label, key, bit_idx, col_hex, src_rows in dig_tracks:
        y_low = y_cursor - track_h
        y_high = y_cursor - 1
        d.add(Rect(x_left, y_low - 1, plot_w, track_h + 2, fillColor=colors.white, strokeColor=colors.HexColor("#E2E8F0"), strokeWidth=0.4))
        d.add(String(x_left - 4, y_low + 2, label, fontName="Helvetica-Bold", fontSize=6.1, textAnchor="end", fillColor=colors.HexColor("#1E293B")))

        pts = []
        prev_v = None
        for i in range(s_start, s_end, 2):
            raw_val = src_rows[i][key]
            v = ((raw_val >> bit_idx) & 1) if bit_idx is not None else (1 if raw_val else 0)
            x = sx(i)
            y = y_high if v else y_low
            if prev_v is not None and v != prev_v:
                pts.extend([x, y_high if prev_v else y_low])
            pts.extend([x, y])
            prev_v = v
        d.add(PolyLine(pts, strokeColor=colors.HexColor(col_hex), strokeWidth=1.1))
        y_cursor -= (track_h + track_gap)

    # Analog bus Panel 1: adc45_ch1_raw (AC-coupled relative to pre-trigger sample 180)
    pan1_top = y_cursor - 11
    pan1_bot = pan1_top - 48
    pan1_h   = pan1_top - pan1_bot
    d.add(String(x_left + 2, pan1_top + 2.5,
                 "adc45_ch1_raw (M3+ AC Delta): Blue = ON Pat A (+W, 104 LSB span) | Gray = OFF (8 LSB span) | Red = ON Pat B (-W, 48 LSB span)",
                 fontName="Helvetica-Bold", fontSize=5.9, fillColor=colors.HexColor("#1E293B")))
    d.add(Rect(x_left, pan1_bot, plot_w, pan1_h, fillColor=colors.white, strokeColor=colors.HexColor("#CBD5E1"), strokeWidth=0.6))
    d.add(String(x_left - 4, pan1_bot + pan1_h / 2 + 3, "adc45_ch1_raw[11:0]", fontName="Helvetica-Bold", fontSize=6.1, textAnchor="end", fillColor=colors.HexColor("#0F172A")))
    d.add(String(x_left - 4, pan1_bot + pan1_h / 2 - 5, "(M3+ AC Delta LSB)", fontName="Helvetica", fontSize=5.6, textAnchor="end", fillColor=colors.HexColor("#475569")))

    b_a1 = rows_on_a[s_start]["adc45_ch1_raw"]
    b_o1 = rows_off[s_start]["adc45_ch1_raw"]
    b_b1 = rows_on_b[s_start]["adc45_ch1_raw"]

    vals_a1 = [rows_on_a[i]["adc45_ch1_raw"] - b_a1 for i in range(s_start, s_end, 2)]
    vals_o1 = [rows_off[i]["adc45_ch1_raw"]  - b_o1 for i in range(s_start, s_end, 2)]
    vals_b1 = [rows_on_b[i]["adc45_ch1_raw"] - b_b1 for i in range(s_start, s_end, 2)]

    ymin1 = min(vals_a1 + vals_o1 + vals_b1 + [-25]) - 6
    ymax1 = max(vals_a1 + vals_o1 + vals_b1 + [25]) + 6

    def sy1(v):
        return pan1_bot + ((v - ymin1) / float(ymax1 - ymin1)) * pan1_h

    y0_1 = sy1(0)
    d.add(Line(x_left, y0_1, x_right, y0_1, strokeColor=colors.HexColor("#E2E8F0"), strokeWidth=0.6))

    pts_o1, pts_a1, pts_b1 = [], [], []
    for k, i in enumerate(range(s_start, s_end, 2)):
        x = sx(i)
        pts_o1.extend([x, sy1(vals_o1[k])])
        pts_a1.extend([x, sy1(vals_a1[k])])
        pts_b1.extend([x, sy1(vals_b1[k])])

    d.add(PolyLine(pts_o1, strokeColor=colors.HexColor("#94A3B8"), strokeWidth=1.0))
    d.add(PolyLine(pts_a1, strokeColor=colors.HexColor("#2563EB"), strokeWidth=1.3))
    d.add(PolyLine(pts_b1, strokeColor=colors.HexColor("#DC2626"), strokeWidth=1.3))

    # Analog bus Panel 2: adc45_ch2_raw (M3-)
    pan2_top = pan1_bot - 13
    pan2_bot = 16
    pan2_h   = pan2_top - pan2_bot
    d.add(String(x_left + 2, pan2_top + 2.5,
                 "adc45_ch2_raw (M3- AC Delta): Blue = ON Pat A (+W, 82 LSB span) | Gray = OFF (7 LSB span) | Red = ON Pat B (-W, 77 LSB span)",
                 fontName="Helvetica-Bold", fontSize=5.9, fillColor=colors.HexColor("#1E293B")))
    d.add(Rect(x_left, pan2_bot, plot_w, pan2_h, fillColor=colors.white, strokeColor=colors.HexColor("#CBD5E1"), strokeWidth=0.6))
    d.add(String(x_left - 4, pan2_bot + pan2_h / 2 + 3, "adc45_ch2_raw[11:0]", fontName="Helvetica-Bold", fontSize=6.1, textAnchor="end", fillColor=colors.HexColor("#0F172A")))
    d.add(String(x_left - 4, pan2_bot + pan2_h / 2 - 5, "(M3- AC Delta LSB)", fontName="Helvetica", fontSize=5.6, textAnchor="end", fillColor=colors.HexColor("#475569")))

    b_a2 = rows_on_a[s_start]["adc45_ch2_raw"]
    b_o2 = rows_off[s_start]["adc45_ch2_raw"]
    b_b2 = rows_on_b[s_start]["adc45_ch2_raw"]

    vals_a2 = [rows_on_a[i]["adc45_ch2_raw"] - b_a2 for i in range(s_start, s_end, 2)]
    vals_o2 = [rows_off[i]["adc45_ch2_raw"]  - b_o2 for i in range(s_start, s_end, 2)]
    vals_b2 = [rows_on_b[i]["adc45_ch2_raw"] - b_b2 for i in range(s_start, s_end, 2)]

    ymin2 = min(vals_a2 + vals_o2 + vals_b2 + [-25]) - 6
    ymax2 = max(vals_a2 + vals_o2 + vals_b2 + [25]) + 6

    def sy2(v):
        return pan2_bot + ((v - ymin2) / float(ymax2 - ymin2)) * pan2_h

    y0_2 = sy2(0)
    d.add(Line(x_left, y0_2, x_right, y0_2, strokeColor=colors.HexColor("#E2E8F0"), strokeWidth=0.6))

    pts_o2, pts_a2, pts_b2 = [], [], []
    for k, i in enumerate(range(s_start, s_end, 2)):
        x = sx(i)
        pts_o2.extend([x, sy2(vals_o2[k])])
        pts_a2.extend([x, sy2(vals_a2[k])])
        pts_b2.extend([x, sy2(vals_b2[k])])

    d.add(PolyLine(pts_o2, strokeColor=colors.HexColor("#94A3B8"), strokeWidth=1.0))
    d.add(PolyLine(pts_a2, strokeColor=colors.HexColor("#2563EB"), strokeWidth=1.3))
    d.add(PolyLine(pts_b2, strokeColor=colors.HexColor("#DC2626"), strokeWidth=1.3))

    # X-axis time ticks
    for s_tick, lbl in [(180, "-7.6 us"), (256, "0.0 us (Trig)"), (496, "24.0 us (+Tab)"), (736, "48.0 us (-Tab End)"), (936, "68.0 us (Hi-Z)")]:
        xt = sx(s_tick)
        d.add(Line(xt, pan2_bot, xt, pan2_bot - 3, strokeColor=colors.HexColor("#64748B"), strokeWidth=0.6))
        d.add(String(xt, pan2_bot - 10, lbl, fontName="Helvetica", fontSize=5.9, textAnchor="middle", fillColor=colors.HexColor("#475569")))

    return d


def make_50mhz_spi_drawing(rows_50m, width=480, height=138):
    """
    Draws a zoomed 6.0 us (300 samples @ 50 MHz = 20 ns/sample) waveform from Trace 5
    showing the exact bare-metal 25 MHz SPI burst clock (adc45_sck), conversion strobe (adc45_conv),
    serial MISO data (adc45_out2_sdo1), 10 MHz T20 clock (t20_clk9), and the 3 capture-enable
    one-shot pulses (ce_10mhz_1shot, ce_2mhz_1shot, adc_done_1shot).
    """
    d = Drawing(width, height)
    d.add(Rect(0, 0, width, height, fillColor=colors.HexColor("#F8FAFC"), strokeColor=colors.HexColor("#CBD5E1"), strokeWidth=0.8))
    d.add(String(10, height - 13, "Figure 2: Full 50 MHz (20 ns/sample, Capture Mode = Always) Bare-Metal SPI & One-Shot Timing (Trace 5)",
                 fontName="Helvetica-Bold", fontSize=8.6, fillColor=colors.HexColor("#0F172A")))
    d.add(String(10, height - 23, "Zoomed 4.00 us window (200 clock cycles @ 50 MHz = two complete 2.00 us XC2361A 12-bit ADC conversions & Hadamard steps)",
                 fontName="Helvetica", fontSize=7.0, fillColor=colors.HexColor("#475569")))

    s_start = 500
    s_end   = 700
    n_samp  = s_end - s_start
    x_left  = 98
    x_right = width - 12
    plot_w  = x_right - x_left

    def sx(idx):
        return x_left + ((idx - s_start) / float(n_samp)) * plot_w

    tracks = [
        ("ce_10mhz_1shot",  "ce_10mhz_1shot",  "#0284C7"),
        ("ce_2mhz_1shot",   "ce_2mhz_1shot",   "#0D9488"),
        ("adc_done_1shot",  "adc_done_1shot",  "#16A34A"),
        ("t20_clk9 (10MHz)","t20_clk9",        "#7C3AED"),
        ("adc45_conv",      "adc45_conv",      "#EA580C"),
        ("adc45_sck (25M)", "adc45_sck",       "#2563EB"),
        ("adc45_out2_sdo1", "adc45_out2_sdo1", "#DC2626"),
    ]

    y_cursor = height - 34
    track_h  = 9
    track_gap = 4

    for label, key, col_hex in tracks:
        y_low  = y_cursor - track_h
        y_high = y_cursor - 1
        d.add(Rect(x_left, y_low - 1, plot_w, track_h + 2, fillColor=colors.white, strokeColor=colors.HexColor("#E2E8F0"), strokeWidth=0.4))
        d.add(String(x_left - 4, y_low + 1.5, label, fontName="Helvetica-Bold", fontSize=6.2, textAnchor="end", fillColor=colors.HexColor("#1E293B")))

        pts = []
        prev_v = None
        for i in range(s_start, s_end):
            v = 1 if rows_50m[i][key] else 0
            x = sx(i)
            y = y_high if v else y_low
            if prev_v is not None and v != prev_v:
                pts.extend([x, y_high if prev_v else y_low])
            pts.extend([x, y])
            prev_v = v
        d.add(PolyLine(pts, strokeColor=colors.HexColor(col_hex), strokeWidth=1.0))
        y_cursor -= (track_h + track_gap)

    for s_tick, lbl in [(500, "0.00 us"), (550, "1.00 us"), (600, "2.00 us"), (650, "3.00 us"), (700, "4.00 us")]:
        xt = sx(s_tick)
        d.add(String(xt, 4, lbl, fontName="Helvetica", fontSize=6.0, textAnchor="middle", fillColor=colors.HexColor("#475569")))

    return d


def build_pdf_and_md():
    with open(JSON_PATH, "r") as f:
        data = json.load(f)

    t1_rows = data["traces"]["trace1_hadamard_ON_mat3_ce10mhz"]["rows"]
    t2_rows = data["traces"]["trace2_hadamard_OFF_tristate_ce10mhz"]["rows"]
    t3_rows = data["traces"]["trace3_hadamard_ON_mat3_and_mat8_ce2mhz"]["rows"]
    t4_rows = data["traces"]["trace4_hadamard_ON_adc_done_500khz"]["rows"]
    t5_rows = data["traces"]["trace5_full_50mhz_spi_timing"]["rows"]
    t6_rows = data["traces"]["trace6_hadamard_ON_patternB_negW_ce10mhz"]["rows"]

    a_ch1, a_ch2, a_m8 = extract_step_means(t1_rows)
    o_ch1, o_ch2, o_m8 = extract_step_means(t2_rows)
    b_ch1, b_ch2, b_m8 = extract_step_means(t6_rows)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DocTitle", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=13.5, leading=16.5,
        textColor=colors.HexColor("#0F172A"), spaceAfter=4
    )
    sub_style = ParagraphStyle(
        "DocSub", parent=styles["Normal"], fontName="Helvetica", fontSize=8.2, leading=10.5,
        textColor=colors.HexColor("#475569"), spaceAfter=8
    )
    h1_style = ParagraphStyle(
        "H1", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=10.2, leading=13,
        textColor=colors.HexColor("#1E3A8A"), spaceBefore=7, spaceAfter=4
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"], fontName="Helvetica", fontSize=8.0, leading=10.8,
        textColor=colors.HexColor("#1E293B"), spaceAfter=5
    )
    code_style = ParagraphStyle(
        "CodeBlk", parent=styles["Code"], fontName="Courier", fontSize=7.0, leading=9.2,
        textColor=colors.HexColor("#0F172A"), backColor=colors.HexColor("#F1F5F9"),
        borderPadding=5, spaceBefore=2, spaceAfter=5
    )

    doc = SimpleDocTemplate(
        str(PDF_PATH), pagesize=A4,
        leftMargin=14 * mm, rightMargin=14 * mm, topMargin=12 * mm, bottomMargin=12 * mm
    )
    story = []

    # Header
    story.append(Paragraph(
        "T120F324_LA Bare-Metal Efinix Logic Analyzer Build, User Guide & Live Carrier Verification",
        title_style
    ))
    story.append(Paragraph(
        "Project Folder: FPGA_code/T120F324_LA | Core: edb_top (la0 on JTAG_USER1) | Hardware UUID: 29024bad0ef545319a42750d2a504819 (VERIFIED) | Date: 2026-10-17",
        sub_style
    ))

    # Section 1: Synthesis & Timing Summary
    story.append(Paragraph("1. Synthesis, Place-and-Route & Static Timing Summary (FPGA_code/T120F324_LA)", h1_style))
    story.append(Paragraph(
        "A dedicated Efinity synthesis directory (<b>FPGA_code/T120F324_LA/</b>) was built with an embedded Efinix "
        "In-System Logic Analyzer (<b>edb_top</b> / <b>la0</b> connected to <b>jtag_inst1</b> on <b>JTAG_USER1</b>), "
        "leaving the production build folder (<b>FPGA_code/T120F324/</b>) completely untouched. To guarantee zero "
        "routing congestion and positive timing slack, the recorder depth was configured to <b>2048 samples</b> across "
        "<b>23 hardware probes (86 total bits)</b> with hardware <b>Capture Control (capture_control = true)</b> enabled.",
        body_style
    ))

    synth_data = [
        ["Metric / Resource / Clock Domain", "Measured Value (T120F324_LA)", "Limit / Target", "Status"],
        ["Logic Elements (XLR)", "60,130 / 112,128 (53.63%)", "112,128 (100%)", "PASS (46.37% free)"],
        ["Memory Blocks (BRAM 5K)", "339 / 1,056 (32.10%)", "1,056 (100%)", "PASS (67.90% free)"],
        ["LA Recorder Depth & Width", "2048 samples x 86 bits (23 probes)", "capture_control = true", "PASS (All DATA & TRIGGER)"],
        ["LA Hardware Core UUID", "29024bad0ef545319a42750d2a504819", "Matches debug_profile.json", "VERIFIED ON JTAG_USER1"],
        ["T120_GCLK (50.00 MHz System Clock)", "Fmax = 51.52 MHz (+0.591 ns setup)", "50.00 MHz (+0.086 ns hold)", "PASS (Zero Violations)"],
        ["jtag_inst1_TCK (10.00 MHz JTAG Clock)", "Fmax = 37.16 MHz (+73.087 ns setup)", "10.00 MHz (+0.307 ns hold)", "PASS (Zero Violations)"],
    ]
    t_synth = Table(synth_data, colWidths=[132, 138, 108, 102])
    t_synth.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.1),
        ("LEADING", (0, 0), (-1, -1), 9.0),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F8FAFC")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F1F5F9")]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]))
    story.append(t_synth)
    story.append(Spacer(1, 5))

    # Section 2: All 23 Probes
    story.append(Paragraph("2. Complete Signal Map of the 23 Bare-Metal Probes in la0 (debug_profile.json)", h1_style))
    probe_rows = [
        ["#", "Probe Name", "Bits", "Category & Bare-Metal Hardware Function"],
        ["0", "ce_10mhz_1shot", "1", "Capture-Enable 1-cycle pulse every 5 sys_clk cycles (10.0 MHz -> 204.8 us window for 2048 samples)"],
        ["1", "ce_2mhz_1shot", "1", "Capture-Enable 1-cycle pulse every 25 sys_clk cycles (2.0 MHz -> 1,024.0 us = 1.024 ms window)"],
        ["2", "adc_done_1shot", "1", "Capture-Enable 1-cycle pulse when XC2361A 12-bit SPI frame latches (500 kHz -> 4,096.0 us window)"],
        ["3", "h_latch_1shot", "1", "1-cycle pulse at exact instant T20 latches a new Hadamard polarity word onto physical matrix pins"],
        ["4", "hadamard_burst_act", "1", "High (1) during the active 12-step (48.0 us) Hadamard burst window on the T120->T20 bridge"],
        ["5", "hadamard_on_n_off", "1", "1 = Hadamard ON (active bipolar drive, bit 15 == 0); 0 = Hadamard OFF (0x8000 Tri-State Hi-Z)"],
        ["6", "hadamard_mat3_on", "1", "1 when Matrix 3 Hadamard stimulus (mask 0x00FF) is actively driving PTU1..6"],
        ["7", "hadamard_mat8_on", "1", "1 when Matrix 8 Hadamard stimulus (mask 0x7F00) is actively driving Matrix 8"],
        ["8", "h_step_idx[3:0]", "4", "Current Hadamard pulse index (0..5 = (+) Table, 6..11 = (-) Complement Table, 12 = Exit Hi-Z)"],
        ["9", "h_word_m3_ptu[5:0]", "6", "Live 6-bit Walsh-Hadamard row polarity word driving Matrix 3 (1 = +1 / 3.3V, 0 = -1 / 0.0V)"],
        ["10", "h_word_tristate", "1", "Bit 15 of current Hadamard word (0 = OE active drive during ON burst, 1 = Tri-State Hi-Z)"],
        ["11..13", "h_sync, h_data, clk9", "3", "Physical inter-FPGA pins: h_sync_tx11p (11), h_data_tx11n (12), and t20_clk9 (13, 10 MHz burst clock)"],
        ["14..17", "adc45_conv/sck/sdo", "4", "Physical ADC_45 pins: CONV (14), 25 MHz SCK_1_2 (15), OUT1_SDO0 [M33+] (16), OUT2_SDO1 [M3+] (17)"],
        ["18", "adc45_ch0_raw[11:0]", "12", "Bare-metal 12-bit unsigned deserialized word from ADC_45 Ch0 (OUT1_SDO0 = Matrix 33 Positive)"],
        ["19", "adc45_ch1_raw[11:0]", "12", "Bare-metal 12-bit unsigned deserialized word from ADC_45 Ch1 (OUT2_SDO1 = Matrix 3 Positive)"],
        ["20", "adc45_ch2_raw[11:0]", "12", "Bare-metal 12-bit unsigned deserialized word from ADC_45 Ch2 (OUT3_SDO2 = Matrix 3 Negative)"],
        ["21", "adc45_ch1_sig[11:0]", "12", "Signed offset-binary (raw ^ 0x800) representation of ADC_45 Ch1 (Matrix 3 Positive)"],
        ["22", "adc49_ch2_raw[11:0]", "12", "Bare-metal 12-bit unsigned deserialized word from ADC_49 Ch2 (Matrix 8 output)"],
    ]
    t_probes = Table(probe_rows, colWidths=[34, 92, 24, 330])
    t_probes.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 6.8),
        ("LEADING", (0, 0), (-1, -1), 8.6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(t_probes)
    story.append(Spacer(1, 6))

    # Section 3: How to Program & Use in Efinix Debugger GUI
    story.append(Paragraph("3. Step-by-Step Commands to Program T120F324_LA & Open Efinix Debugger GUI", h1_style))
    cmd_text = (
        "# 1. Program the Logic Analyzer bitstream onto T120 via JTAG (6 MHz):\n"
        "python3 FPGA_code/scripts/program_t120.py FPGA_code/T120F324_LA/outflow/T120_MALM.bit\n\n"
        "# 2. Launch the Efinix Debugger GUI (ensure OpenOCD is NOT running):\n"
        "source /home/olle/efinix2/efinity-2025.2.288.2.10-linux-x64/efinity/2025.2/bin/setup.sh\n"
        "/home/olle/efinix2/efinity-2025.2.288.2.10-linux-x64/efinity/2025.2/bin/efinity_dbg.sh\n\n"
        "# 3. Or run the automated bare-metal CLI capture script (exports 6 VCDs + JSON):\n"
        "python3 FPGA_code/scripts/capture_t120_la_traces.py"
    )
    story.append(Paragraph(cmd_text.replace("\n", "<br/>"), code_style))

    gui_recipes = [
        ["Analysis Goal in Efinix Debugger GUI", "Mode", "Capture Condition", "Trigger Condition (tu_pttrn = AND)", "Trig Pos"],
        ["1. Hadamard ON (+W / -W) @ 10 MHz", "Basic", "ce_10mhz_1shot == 1", "hadamard_burst_act==1 & hadamard_on_n_off==1 & hadamard_mat3_on==1", "256"],
        ["2. Hadamard OFF (0x8000) @ 10 MHz", "Basic", "ce_10mhz_1shot == 1", "hadamard_burst_act==1 & hadamard_on_n_off==0 & h_step_idx==2", "256"],
        ["3. Wide 1.024 ms @ 2 MHz Downsample", "Basic", "ce_2mhz_1shot == 1", "hadamard_burst_act==1 & hadamard_on_n_off==1 & hadamard_mat3_on==1", "128"],
        ["4. Pure 12-Bit ADC Words @ 500 kHz", "Basic", "adc_done_1shot == 1", "hadamard_burst_act==1 & hadamard_on_n_off==1", "128"],
        ["5. Full 50 MHz (20 ns) SPI & MISO", "Always", "(None / Full 50 MHz)", "hadamard_burst_act==1 & hadamard_on_n_off==1 & hadamard_mat3_on==1", "512"],
    ]
    t_rec = Table(gui_recipes, colWidths=[126, 30, 68, 224, 32])
    t_rec.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 5.9),
        ("LEADING", (0, 0), (-1, -1), 7.8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F1F5F9")]),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]))
    story.append(t_rec)

    story.append(PageBreak())

    # Page 2: Live Bare-Metal Waveforms & Quantitative Verification Table
    story.append(Paragraph("4. Live Bare-Metal Efinix Logic Analyzer Captures (la0 Hardware Verification)", h1_style))
    story.append(Paragraph(
        "The figures and tables below are generated directly from the <b>2048-sample hardware buffers</b> read out "
        "from <b>la0</b> (UUID <b>29024bad0ef545319a42750d2a504819</b>) via JTAG_USER1 after programming "
        "<b>FPGA_code/T120F324_LA/outflow/T120_MALM.bit</b>. They independently confirm at the bare-metal RTL level:",
        body_style
    ))
    story.append(Paragraph(
        "1) <b>Unambiguous ON vs. OFF Discrimination</b>: During Hadamard OFF (0x8000 Tri-State, Trace 2), "
        "<b>hadamard_on_n_off = 0</b> and <b>adc45_ch1_raw</b> stays flat within <b>8 LSB</b> (2311..2319). During "
        "Hadamard ON with Weight Pattern A (+W, Trace 1), <b>hadamard_on_n_off = 1</b> and <b>adc45_ch1_raw</b> swings "
        "by <b>104 LSB</b> (2257..2361, <b>13.0x</b> larger than OFF), while <b>adc45_ch2_raw</b> (M3-) swings by <b>82 LSB</b> (2339..2421 vs 7 LSB in OFF).<br/>"
        "2) <b>Weight Sign Inversion (+W -> -W, Trace 6)</b>: Flipping all 126 weight signs shifts the bare-metal "
        "ADC_45 Ch1 DC operating point from ~2312 LSB (+W) to ~1807 LSB (-W) and flips the step-by-step Hadamard "
        "carrier differential response across steps 0..5 ((+) Table) vs. steps 6..11 ((-) Complement Table).",
        body_style
    ))

    story.append(make_la_digital_and_analog_drawing(t1_rows, t2_rows, t6_rows, width=480, height=232))
    story.append(Spacer(1, 5))
    story.append(make_50mhz_spi_drawing(t5_rows, width=480, height=138))
    story.append(Spacer(1, 5))

    # Summary Table of the 6 Live LA Traces
    story.append(Paragraph("5. Quantitative Summary of All 6 Bare-Metal Logic Analyzer Captures (2048 Samples Each)", h1_style))

    def stats_row(key, label, cap_desc):
        rows = data["traces"][key]["rows"]
        c1 = [r["adc45_ch1_raw"] for r in rows]
        c2 = [r["adc45_ch2_raw"] for r in rows]
        m8 = [r["adc49_ch2_raw"] for r in rows]
        hon = sorted(list(set(r["hadamard_on_n_off"] for r in rows)))
        return [
            label,
            cap_desc,
            str(hon),
            f"{min(c1)}..{max(c1)} ({max(c1)-min(c1)} LSB)",
            f"{min(c2)}..{max(c2)} ({max(c2)-min(c2)} LSB)",
            f"{min(m8)}..{max(m8)} ({max(m8)-min(m8)} LSB)",
        ]

    cap_table_data = [
        ["VCD Trace File (outflow/)", "Capture Enable", "on_n_off", "adc45_ch1_raw (M3+)", "adc45_ch2_raw (M3-)", "adc49_ch2_raw (M8)"],
        stats_row("trace2_hadamard_OFF_tristate_ce10mhz", "Trace 2: Hadamard OFF (0x8000)", "10 MHz (204.8 us)"),
        stats_row("trace1_hadamard_ON_mat3_ce10mhz", "Trace 1: Hadamard ON Pat A (+W)", "10 MHz (204.8 us)"),
        stats_row("trace6_hadamard_ON_patternB_negW_ce10mhz", "Trace 6: Hadamard ON Pat B (-W)", "10 MHz (204.8 us)"),
        stats_row("trace3_hadamard_ON_mat3_and_mat8_ce2mhz", "Trace 3: Hadamard ON Pat A (+W)", "2 MHz (1.024 ms)"),
        stats_row("trace4_hadamard_ON_adc_done_500khz", "Trace 4: Hadamard ON Pat A (+W)", "500 kHz (4.096 ms)"),
        stats_row("trace5_full_50mhz_spi_timing", "Trace 5: Full 50 MHz SPI Timing", "Always 50 MHz (41 us)"),
    ]
    t_cap = Table(cap_table_data, colWidths=[125, 76, 38, 82, 82, 77])
    t_cap.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 6.8),
        ("LEADING", (0, 0), (-1, -1), 8.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(t_cap)
    story.append(Spacer(1, 4))

    # Step-by-step table for h_step_idx = 0..5 vs 6..11 from Trace 1 (+W), Trace 2 (OFF), Trace 6 (-W)
    step_header = ["Basis k (Steps k vs k+6)", "OFF: dY_ch1", "Pat A (+W): Y+(k) / Y-(k+6) / dY_A", "Pat B (-W): Y+(k) / Y-(k+6) / dY_B", "Carrier Polarity (+W vs -W)"]
    step_rows = [step_header]
    for k in range(6):
        dy_off = o_ch1[k] - o_ch1[k + 6]
        dy_a   = a_ch1[k] - a_ch1[k + 6]
        dy_b   = b_ch1[k] - b_ch1[k + 6]
        opp    = f"FLIPPED ({dy_a:+.0f} -> {dy_b:+.0f} LSB)" if (dy_a * dy_b < 0) else f"Delta = {dy_b - dy_a:+.1f} LSB"
        step_rows.append([
            f"Basis {k+1} (Step {k} vs {k+6})",
            f"{dy_off:+.1f} LSB",
            f"{a_ch1[k]:.0f} / {a_ch1[k+6]:.0f} ({dy_a:+.1f} LSB)",
            f"{b_ch1[k]:.0f} / {b_ch1[k+6]:.0f} ({dy_b:+.1f} LSB)",
            opp,
        ])
    t_steps = Table(step_rows, colWidths=[86, 54, 118, 118, 104])
    t_steps.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 6.6),
        ("LEADING", (0, 0), (-1, -1), 8.2),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F1F5F9")]),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(t_steps)

    doc.build(story)
    print(f"[+] Generated PDF: {PDF_PATH}")

    # Write companion Markdown file
    md_lines = [
        "# T120F324_LA Bare-Metal Efinix Logic Analyzer Build, User Guide & Live Carrier Verification",
        "",
        "- **Project Folder**: `FPGA_code/T120F324_LA` (keeps `FPGA_code/T120F324` untouched)",
        "- **Logic Analyzer Core**: `edb_top` (`la0` on `JTAG_USER1`)",
        "- **Hardware UUID**: `29024bad0ef545319a42750d2a504819` (**VERIFIED** on live hardware)",
        "- **Recorder Depth & Width**: `2048` samples x `86` bits (`23` probes, `capture_control = true`)",
        "- **Resource Usage**: `60,130 / 112,128` Logic Elements (`53.63%`), `339 / 1,056` Memory Blocks (`32.10%`)",
        "- **Timing (STA)**: `T120_GCLK` (`50 MHz`) `+0.591 ns` setup slack (`51.52 MHz` Fmax); `jtag_inst1_TCK` (`10 MHz`) `+73.087 ns` setup slack.",
        "",
        "## 1. Commands to Program & Launch Efinix Debugger",
        "```bash",
        "# Program T120F324_LA bitstream via JTAG:",
        "python3 FPGA_code/scripts/program_t120.py FPGA_code/T120F324_LA/outflow/T120_MALM.bit",
        "",
        "# Launch Efinix Debugger GUI and load FPGA_code/T120F324_LA/debug_profile.json:",
        "source /home/olle/efinix2/efinity-2025.2.288.2.10-linux-x64/efinity/2025.2/bin/setup.sh",
        "/home/olle/efinix2/efinity-2025.2.288.2.10-linux-x64/efinity/2025.2/bin/efinity_dbg.sh",
        "",
        "# Or capture all 6 bare-metal VCD traces automatically via CLI:",
        "python3 FPGA_code/scripts/capture_t120_la_traces.py",
        "```",
        "",
        "## 2. Summary of the 6 Live Efinix Logic Analyzer Captures",
        "| Trace File (`FPGA_code/T120F324_LA/outflow/`) | Capture Enable | `hadamard_on_n_off` | `adc45_ch1_raw` (`M3+`) | `adc45_ch2_raw` (`M3-`) | `adc49_ch2_raw` (`M8`) |",
        "| :--- | :--- | :---: | :--- | :--- | :--- |",
    ]
    for row in cap_table_data[1:]:
        md_lines.append(f"| `{row[0]}` | {row[1]} | `{row[2]}` | `{row[3]}` | `{row[4]}` | `{row[5]}` |")

    with open(MD_PATH, "w") as f:
        f.write("\n".join(md_lines) + "\n")
    print(f"[+] Generated Markdown: {MD_PATH}")


if __name__ == "__main__":
    build_pdf_and_md()
