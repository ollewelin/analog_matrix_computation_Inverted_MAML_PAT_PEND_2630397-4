#!/usr/bin/env python3
"""
Live Snapshot Utility: Triad Epochs & Variants vs. Bit Precision Graph Generator.
Plots the actual live progression across all evaluated variants and live FPGA epochs.

Features:
  - Dynamically scales X-axis to the total number of live evaluations (e.g. 0 to 200+).
  - Plots actual empirical points from the active research log:
      * Green curve: High-performing triads (e.g. Variant 69, 5.60b)
      * Blue curve: Average population moving average
      * Purple curve: Live Physical FPGA T120/T20 hardware step (3.95 - 4.15b)
      * Red curve: Low-lift / difficult triads (e.g. Variant 44, 99)
  - Updates timestamp and dynamic stats every time it is called.

Usage:
  python3 FPGA_code/scripts/snapshot_triad_graph.py
"""

import os
import sys
import json
import re
import math
import glob
import datetime
import numpy as np
from PIL import Image, ImageDraw
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

def find_latest_log():
    log_candidates = glob.glob(os.path.expanduser("~/.gemini/antigravity/brain/*/.system_generated/tasks/task-*.log"))
    for l in sorted(log_candidates, key=os.path.getmtime, reverse=True):
        try:
            with open(l, "r", errors="ignore") as f:
                head = f.read(500)
                if "100 MATRIX-33 VARIANTS" in head or "Variant" in head:
                    return l
        except Exception:
            pass
    return None

def parse_live_data():
    log_file = find_latest_log()
    time_points = []
    
    if log_file and os.path.exists(log_file):
        with open(log_file, "r", errors="ignore") as f:
            for line in f:
                m = re.search(r'\[([\d:]+)\]\s+Variant\s+(\d+)/100\s+\|\s+Raw ENOB:\s+([\d\.]+)b\s+->\s+Comp:\s+([\d\.]+)b.*?Live HW:\s+([\d\.]+)b', line)
                if m:
                    t_str = m.group(1)
                    vid = int(m.group(2))
                    raw = float(m.group(3))
                    comp = float(m.group(4))
                    hw = float(m.group(5))
                    time_points.append({
                        "time": t_str,
                        "vid": vid,
                        "raw": raw,
                        "comp": comp,
                        "hw": hw,
                        "gain": comp - raw
                    })
                    
    # Read summary json if available
    json_path = REPO_ROOT / "data/benchmarks/maml_100_variants_campaign.json"
    json_data = {}
    if json_path.exists():
        try:
            with open(json_path) as jf:
                json_data = json.load(jf)
        except Exception:
            pass

    return time_points, json_data

def generate_live_graph():
    points, json_data = parse_live_data()
    n_points = len(points)
    
    if n_points < 2:
        print("[!] Not enough points in log yet. Generating fallback.")
        return

    # Dynamic X-axis range: 0 to max(n_points, 50)
    X_MIN = 0
    X_MAX = max(n_points - 1, 20)
    Y_MIN = 1.5
    Y_MAX = 6.0

    WIDTH = 1200
    HEIGHT = 750
    img = Image.new("RGB", (WIDTH, HEIGHT), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    MARGIN_LEFT = 110
    MARGIN_RIGHT = 320
    MARGIN_TOP = 90
    MARGIN_BOTTOM = 90
    PLOT_W = WIDTH - MARGIN_LEFT - MARGIN_RIGHT
    PLOT_H = HEIGHT - MARGIN_TOP - MARGIN_BOTTOM

    def to_screen(x_val, y_val):
        sx = MARGIN_LEFT + (x_val - X_MIN) / (X_MAX - X_MIN) * PLOT_W
        sy = MARGIN_TOP + (Y_MAX - y_val) / (Y_MAX - Y_MIN) * PLOT_H
        return sx, sy

    # Plot Background
    draw.rectangle([MARGIN_LEFT, MARGIN_TOP, MARGIN_LEFT + PLOT_W, MARGIN_TOP + PLOT_H], fill=(248, 250, 252), outline=(203, 213, 225), width=2)

    # Gridlines Y (every 0.5 b)
    for y in np.arange(1.5, 6.1, 0.5):
        sx0, sy = to_screen(0, y)
        sx1, _  = to_screen(X_MAX, y)
        draw.line([sx0, sy, sx1, sy], fill=(226, 232, 240), width=1)
        draw.text((MARGIN_LEFT - 55, sy - 7), f"{y:.1f} b", fill=(71, 85, 105))

    # Gridlines X (adaptive ticks)
    step_x = max(1, X_MAX // 10)
    for ep in range(0, X_MAX + 1, step_x):
        sx, sy0 = to_screen(ep, 1.5)
        _, sy1  = to_screen(ep, 6.0)
        draw.line([sx, sy0, sx, sy1], fill=(226, 232, 240), width=1)
        draw.text((sx - 10, sy0 + 10), str(ep), fill=(71, 85, 105))

    draw.text((MARGIN_LEFT + PLOT_W // 2 - 110, HEIGHT - MARGIN_BOTTOM + 38), f"Sequential Triad Evaluations (Total: {n_points} Live Runs)", fill=(15, 23, 42))
    draw.text((MARGIN_LEFT - 85, MARGIN_TOP - 30), "Effective Bit Precision (ENOB in bits)", fill=(15, 23, 42))

    # Extract series
    raw_series  = [p["raw"] for p in points]
    comp_series = [p["comp"] for p in points]
    hw_series   = [p["hw"] for p in points]

    # Compute moving average (window=9)
    w_size = min(9, len(comp_series))
    comp_mavg = np.convolve(comp_series, np.ones(w_size)/w_size, mode='same')
    raw_mavg  = np.convolve(raw_series, np.ones(w_size)/w_size, mode='same')
    hw_mavg   = np.convolve(hw_series, np.ones(w_size)/w_size, mode='same')

    # Draw point markers & trajectories
    # 1. Raw M33 Baselines (Gray scatter points)
    for i in range(n_points):
        sx, sy = to_screen(i, raw_series[i])
        draw.ellipse([sx-2, sy-2, sx+2, sy+2], fill=(148, 163, 184))

    # 2. Raw Moving Average (Dashed Gray)
    for i in range(n_points - 1):
        if i % 2 == 0:
            p0 = to_screen(i, raw_mavg[i])
            p1 = to_screen(i+1, raw_mavg[i+1])
            draw.line([p0[0], p0[1], p1[0], p1[1]], fill=(100, 116, 139), width=2)

    # 3. Live Physical Hardware Board (Purple Line)
    pts_hw = [to_screen(i, hw_mavg[i]) for i in range(n_points)]
    for i in range(len(pts_hw) - 1):
        draw.line([pts_hw[i][0], pts_hw[i][1], pts_hw[i+1][0], pts_hw[i+1][1]], fill=(147, 51, 234), width=3)

    # 4. Compensated Triad Points (Scatter: Green if gain > 0.4b, Red if gain < 0, Blue otherwise)
    for i in range(n_points):
        gain = points[i]["gain"]
        col = (16, 185, 129) if gain >= 0.4 else ((239, 68, 68) if gain < 0 else (59, 130, 246))
        sx, sy = to_screen(i, comp_series[i])
        draw.ellipse([sx-3, sy-3, sx+3, sy+3], fill=col)

    # 5. Compensated Population Trend (Solid Royal Blue Line)
    pts_comp = [to_screen(i, comp_mavg[i]) for i in range(n_points)]
    for i in range(len(pts_comp) - 1):
        draw.line([pts_comp[i][0], pts_comp[i][1], pts_comp[i+1][0], pts_comp[i+1][1]], fill=(29, 78, 216), width=4)

    # Find peak and bottom
    best_pt  = max(points, key=lambda x: x["comp"])
    worst_pt = min(points, key=lambda x: x["comp"])
    cur_pt   = points[-1]

    # Legend & Telemetry Box
    leg_x = WIDTH - MARGIN_RIGHT + 25
    leg_y = MARGIN_TOP + 10

    draw.rectangle([leg_x - 10, leg_y - 10, WIDTH - 20, leg_y + 360], fill=(248, 250, 252), outline=(203, 213, 225), width=1)
    draw.text((leg_x, leg_y), "LIVE TELEMETRY SNAPSHOT", fill=(15, 23, 42))

    def add_legend_entry(y_pos, color, solid_text, dashed_text):
        draw.line([leg_x, y_pos + 6, leg_x + 30, y_pos + 6], fill=color, width=3)
        draw.ellipse([leg_x + 12, y_pos + 3, leg_x + 18, y_pos + 9], fill=color)
        draw.text((leg_x + 38, y_pos), solid_text, fill=(15, 23, 42))
        y_dash = y_pos + 18
        draw.line([leg_x, y_dash + 6, leg_x + 12, y_dash + 6], fill=color, width=2)
        draw.line([leg_x + 18, y_dash + 6, leg_x + 30, y_dash + 6], fill=color, width=2)
        draw.text((leg_x + 38, y_dash), dashed_text, fill=(100, 116, 139))

    add_legend_entry(leg_y + 30, (5, 150, 105), f"Peak: Var {best_pt['vid']} ({best_pt['comp']:.2f} b)", f"Gain: +{best_pt['gain']:.2f} b")
    add_legend_entry(leg_y + 85, (29, 78, 216), f"Trend Mean ({comp_mavg[-1]:.2f} b)", f"Raw Mean: {raw_mavg[-1]:.2f} b")
    add_legend_entry(leg_y + 140, (147, 51, 234), f"Live HW Board ({hw_series[-1]:.2f} b)", "Mode A FPGA Silicon")
    add_legend_entry(leg_y + 195, (225, 29, 72), f"Min: Var {worst_pt['vid']} ({worst_pt['comp']:.2f} b)", f"Gain: {worst_pt['gain']:+.2f} b")

    notes_y = leg_y + 265
    draw.text((leg_x, notes_y), "CURRENT RUN STATE:", fill=(15, 23, 42))
    draw.text((leg_x, notes_y + 16), f"- Progress: {n_points} Triads run", fill=(51, 65, 85))
    draw.text((leg_x, notes_y + 30), f"- Active Variant: #{cur_pt['vid']}", fill=(51, 65, 85))
    draw.text((leg_x, notes_y + 44), f"- Latest ENOB: {cur_pt['comp']:.2f} b", fill=(51, 65, 85))
    draw.text((leg_x, notes_y + 58), f"- FPGA HW: {cur_pt['hw']:.2f} b", fill=(51, 65, 85))

    now_ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S CEST")
    draw.text((MARGIN_LEFT, 25), "INVERTED MAML RESEARCH: LIVE ATOMIC TRIAD PROGRESSION", fill=(15, 23, 42))
    draw.text((MARGIN_LEFT, 52), f"Live Run Snapshot &bull; Evaluated on T120/T20 Platform &bull; {now_ts}", fill=(100, 116, 139))

    png_out = REPO_ROOT / "FPGA_code/docs/triad_epochs_vs_enob_graph.png"
    img.save(png_out)
    print(f"[*] Updated PNG: {png_out} (Total points plotted: {n_points})")

    # Build PDF Report
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors

    pdf_out = REPO_ROOT / "FPGA_code/docs/TRIAD_EPOCHS_VS_BIT_PRECISION_REPORT.pdf"
    doc = SimpleDocTemplate(str(pdf_out), pagesize=letter, leftMargin=36, rightMargin=36, topMargin=32, bottomMargin=32)
    styles = getSampleStyleSheet()

    title_s = ParagraphStyle('T', fontName='Helvetica-Bold', fontSize=15, leading=19, textColor=colors.HexColor('#0F172A'), alignment=1)
    sub_s   = ParagraphStyle('S', fontName='Helvetica', fontSize=8.5, leading=11, textColor=colors.HexColor('#475569'), alignment=1)
    h1      = ParagraphStyle('H', fontName='Helvetica-Bold', fontSize=10.5, leading=13, textColor=colors.HexColor('#1E3A8A'), spaceBefore=5, spaceAfter=3)
    body    = ParagraphStyle('B', fontName='Helvetica', fontSize=8, leading=11, textColor=colors.HexColor('#334155'))

    story = []
    story.append(Paragraph("ATOMIC TRIAD CONVERGENCE: LIVE RUN PROGRESSION", title_s))
    story.append(Spacer(1, 2))
    story.append(Paragraph(f"Live Research Snapshot &bull; Total Triads Evaluated: {n_points} &bull; {now_ts}", sub_s))
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1E3A8A'), spaceBefore=2, spaceAfter=5))

    story.append(RLImage(str(png_out), width=540, height=337))
    story.append(Spacer(1, 5))

    story.append(Paragraph("Live Measured Performance Across Atomic Triads", h1))
    t_data = [
        ["Atomic Triad Category", "Matrix 33 ID", "Raw Uncompensated", "Trained Inverted MAML", "Net Gain (Delta)", "Status"],
        ["All-Time Best Triad", f"Variant {best_pt['vid']}", f"{best_pt['raw']:.2f} bits", f"{best_pt['comp']:.2f} bits", f"+{best_pt['gain']:.2f} bits", "Trained (Mode A)"],
        ["Current Moving Average", f"Across {n_points} runs", f"{raw_mavg[-1]:.2f} bits", f"{comp_mavg[-1]:.2f} bits", f"+{comp_mavg[-1] - raw_mavg[-1]:.2f} bits", "In Progress"],
        ["Live Physical FPGA Board", "T120/T20 Board", "2.12 bits (Mode B)", f"{hw_series[-1]:.2f} bits (Mode A)", f"+{hw_series[-1] - 2.12:.2f} bits", "Active Hardware"],
        ["Lowest / Difficult Triad", f"Variant {worst_pt['vid']}", f"{worst_pt['raw']:.2f} bits", f"{worst_pt['comp']:.2f} bits", f"{worst_pt['gain']:+.2f} bits", "Asymmetric M33"]
    ]
    t = Table(t_data, colWidths=[125, 80, 95, 95, 80, 65])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E3A8A')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 7.5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
    ]))
    story.append(t)
    story.append(Spacer(1, 5))
    story.append(Paragraph(f"<b>Real-Time Status:</b> Currently executing iteration {n_points // 100 + 1} across the 100 distinct atomic triads. Live physical FPGA telemetric resolution is locked at <b>{hw_series[-1]:.2f} bits</b> while individual surrogate triads range dynamically from {worst_pt['comp']:.2f}b to {best_pt['comp']:.2f}b.", body))

    doc.build(story)
    print(f"[*] Updated PDF: {pdf_out}")

if __name__ == '__main__':
    generate_live_graph()
