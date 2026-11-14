#!/home/olle/anaconda3/bin/python
"""
compile_card1_45pct_13min_report_pdf.py
Inverted MAML (Patent Pending SE 2630397-4) - Open Science Hardware

Generates publication figures, Markdown report, and PDF report for the
Card 1 13-minute 45% PWM 2-Beat Analog Bit Slicing Thermal Stress Run
(LR=0.06, L2=1024, K=1, 1k/3.3k attenuator), including:
  - Phase-by-phase analysis & W8 rail saturation diagnosis
  - 2-Beat Analog Bit Slicing principle & T120 state isolation
  - Summary of post_analog_alpha_beta_calibration_8_channel_fhp_specification.md
  - Hardware action plan: 1k/2.2k attenuator modification
"""

from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_JSON = REPO_ROOT / "FPGA_code" / "logs" / "bit_slicing" / "card1_thermal_slicing_45pct_k1_lr0p06_l2_1024_13min_6warm.json"
FIG_TIMELINE = REPO_ROOT / "FPGA_code" / "logs" / "bit_slicing" / "fig_card1_thermal_slicing_45pct_13min.png"
FIG_TRANSIENT = REPO_ROOT / "FPGA_code" / "logs" / "bit_slicing" / "fig_45pct_phase5_8_transient.png"

DOCS_DIR = REPO_ROOT / "FPGA_code" / "docs"
ARTIFACT_DIR = Path("/home/olle/.gemini/antigravity/brain/fa59cd2e-8c8b-41e2-add0-77ffdf2fe431")

PDF_OUT_DOCS = DOCS_DIR / "INVERTED_MAML_CARD1_13MIN_45PCT_BIT_SLICING_THERMAL_REPORT.pdf"
PDF_OUT_ARTIFACT = ARTIFACT_DIR / "INVERTED_MAML_CARD1_13MIN_45PCT_BIT_SLICING_THERMAL_REPORT.pdf"
MD_OUT_DOCS = DOCS_DIR / "INVERTED_MAML_CARD1_13MIN_45PCT_BIT_SLICING_THERMAL_REPORT.md"
MD_OUT_ARTIFACT = ARTIFACT_DIR / "INVERTED_MAML_CARD1_13MIN_45PCT_BIT_SLICING_THERMAL_REPORT.md"


def compute_phase_stats(data):
    meta = data["metadata"]
    hist = data["history"]
    stats = []
    for pi, p in enumerate(meta["phases"]):
        rows = [r for r in hist if r["phase_idx"] == pi]
        if not rows:
            continue
        ss = rows[len(rows) // 2:]
        stats.append({
            "phase_num": pi + 1,
            "name": p["name"],
            "heater": p["heater"],
            "regler": p["regler"],
            "dur_min": p["dur_s"] / 60.0,
            "n_pairs": len(rows),
            "comb_mean": float(np.mean([r["combined_enob_raw"] for r in rows])),
            "comb_ss": float(np.mean([r["combined_enob_raw"] for r in ss])),
            "msb_mean": float(np.mean([r["enob_msb"] for r in rows])),
            "lsb_mean": float(np.mean([r["enob_lsb"] for r in rows])),
            "rmse_msb": float(np.mean([r["rmse_msb"] for r in rows])),
            "rmse_lsb": float(np.mean([r["rmse_lsb"] for r in rows])),
            "w8_msb_min": int(min(r["w8_msb_range"][0] for r in rows)),
            "w8_msb_max": int(max(r["w8_msb_range"][1] for r in rows)),
            "w8_lsb_min": int(min(r["w8_lsb_range"][0] for r in rows)),
            "w8_lsb_max": int(max(r["w8_lsb_range"][1] for r in rows)),
        })
    return stats


def generate_figures(data):
    hist = data["history"]
    meta = data["metadata"]
    phases = meta["phases"]

    t_min = np.array([r["elapsed_s"] / 60.0 for r in hist])
    comb = np.array([r["combined_enob_raw"] for r in hist])
    msb = np.array([r["enob_msb"] for r in hist])
    lsb = np.array([r["enob_lsb"] for r in hist])
    w8m_min = np.array([r["w8_msb_range"][0] for r in hist])
    w8m_max = np.array([r["w8_msb_range"][1] for r in hist])
    w8l_min = np.array([r["w8_lsb_range"][0] for r in hist])
    w8l_max = np.array([r["w8_lsb_range"][1] for r in hist])

    def shade_phases(ax):
        acc = 0.0
        for pi, p in enumerate(phases):
            t0 = acc / 60.0
            t1 = (acc + p["dur_s"]) / 60.0
            acc += p["dur_s"]
            color = "#fee2e2" if p["heater"] else "#dbeafe"
            alpha = 0.45 if p["regler"] else 0.22
            ax.axvspan(t0, t1, color=color, alpha=alpha, zorder=0)
            ax.axvline(t0, color="#94a3b8", linestyle="--", linewidth=0.7, zorder=1)

    # Figure 1: Full 13-min 3-panel timeline
    fig, axes = plt.subplots(3, 1, figsize=(11, 8.2), sharex=True, gridspec_kw={"height_ratios": [1.3, 1.0, 1.0]})
    fig.patch.set_facecolor("white")

    # Panel 1: Combined 8-bit ENOB
    ax = axes[0]
    shade_phases(ax)
    ax.plot(t_min, comb, color="#0284c7", linewidth=0.9, alpha=0.85, label="Combined 8-Bit ENOB (16*Y_MSB + Y_LSB)")
    ax.axhline(8.0, color="#d97706", linestyle=":", linewidth=1.2, label="8.0-bit Target")
    ax.axhline(4.0, color="#64748b", linestyle=":", linewidth=1.0, label="4.0-bit Base Floor")
    ax.set_ylabel("Combined ENOB (bits)", fontsize=10, fontweight="bold")
    ax.set_ylim(4.5, 9.8)
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.legend(loc="upper right", fontsize=8, framealpha=0.9)
    ax.set_title("Card 1 Thermal Stress (45% Hardware PWM, K=1, LR=0.06, L2=1024, 1k/3.3k Attenuator)", fontsize=11.5, fontweight="bold")

    # Annotate phases
    acc = 0.0
    for pi, p in enumerate(phases):
        t_mid = (acc + 0.5 * p["dur_s"]) / 60.0
        acc += p["dur_s"]
        lbl = f"P{pi+1}\n{'ON' if p['regler'] else 'OFF'}"
        ax.text(t_mid, 9.48, lbl, ha="center", va="top", fontsize=7.5, fontweight="bold",
                color="#15803d" if p["regler"] else "#b91c1c")

    # Panel 2: MSB & LSB 4-bit ENOB
    ax = axes[1]
    shade_phases(ax)
    ax.plot(t_min, msb, color="#16a34a", linewidth=0.8, alpha=0.8, label="MSB Slice (Beat 2k)")
    ax.plot(t_min, lsb, color="#ea580c", linewidth=0.8, alpha=0.75, label="LSB Slice (Beat 2k+1)")
    ax.axhline(4.0, color="#64748b", linestyle=":", linewidth=1.0)
    ax.set_ylabel("Slice ENOB (bits)", fontsize=10, fontweight="bold")
    ax.set_ylim(2.5, 6.5)
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.legend(loc="upper right", fontsize=8, framealpha=0.9)

    # Panel 3: W8 Weight Envelope
    ax = axes[2]
    shade_phases(ax)
    ax.plot(t_min, w8m_max, color="#16a34a", linewidth=1.0, label="W8 MSB max")
    ax.plot(t_min, w8m_min, color="#16a34a", linewidth=1.0, linestyle="--", label="W8 MSB min")
    ax.plot(t_min, w8l_max, color="#ea580c", linewidth=1.0, label="W8 LSB max")
    ax.plot(t_min, w8l_min, color="#ea580c", linewidth=1.0, linestyle="--", label="W8 LSB min")
    ax.axhline(120, color="#dc2626", linestyle=":", linewidth=1.1, label="Rail (+120 / -120 LSB)")
    ax.axhline(-120, color="#dc2626", linestyle=":", linewidth=1.1)
    ax.set_ylabel("W8 Weight (LSB)", fontsize=10, fontweight="bold")
    ax.set_xlabel("Elapsed Time (minutes)", fontsize=10, fontweight="bold")
    ax.set_ylim(-132, 132)
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.legend(loc="lower left", fontsize=7.5, ncol=3, framealpha=0.9)

    plt.tight_layout()
    fig.savefig(FIG_TIMELINE, dpi=180)
    plt.close(fig)

    # Figure 2: Zoomed P4 -> P8 (3.0 to 13.0 min) showing Regler ON/OFF steps
    fig2, (ax1, ax2) = plt.subplots(2, 1, figsize=(10.5, 5.8), sharex=True, gridspec_kw={"height_ratios": [1.3, 1.0]})
    mask = t_min >= 3.0
    tz = t_min[mask]
    cz = comb[mask]

    # Moving average (window=25)
    win = 25
    kernel = np.ones(win) / win
    cz_smooth = np.convolve(cz, kernel, mode="same")

    for ax in (ax1, ax2):
        acc = 0.0
        for pi, p in enumerate(phases):
            t0 = max(3.0, acc / 60.0)
            t1 = (acc + p["dur_s"]) / 60.0
            acc += p["dur_s"]
            if t1 <= 3.0:
                continue
            color = "#dcfce7" if p["regler"] else "#fee2e2"
            ax.axvspan(t0, t1, color=color, alpha=0.45, zorder=0)
            ax.axvline(t0, color="#64748b", linestyle="--", linewidth=0.8)

    ax1.plot(tz, cz, color="#38bdf8", linewidth=0.6, alpha=0.55, label="Raw Pair Combined ENOB")
    ax1.plot(tz, cz_smooth, color="#0369a1", linewidth=1.8, label="25-Pair Moving Average")
    ax1.set_ylabel("Combined ENOB (bits)", fontsize=10, fontweight="bold")
    ax1.set_ylim(5.0, 8.2)
    ax1.grid(True, linestyle=":", alpha=0.5)
    ax1.legend(loc="upper right", fontsize=8.5)
    ax1.set_title("Hot-Phase Regler ON/OFF Step Response (Phases 4–8: +0.93 b in P5, +0.87 b in P7)", fontsize=11, fontweight="bold")

    ax2.plot(tz, w8m_max[mask], color="#16a34a", linewidth=1.2, label="W8 MSB max")
    ax2.plot(tz, w8l_max[mask], color="#ea580c", linewidth=1.2, label="W8 LSB max")
    ax2.plot(tz, w8m_min[mask], color="#16a34a", linewidth=1.0, linestyle="--", label="W8 MSB min")
    ax2.plot(tz, w8l_min[mask], color="#ea580c", linewidth=1.0, linestyle="--", label="W8 LSB min")
    ax2.axhline(120, color="#dc2626", linestyle=":", linewidth=1.2, label="±120 LSB Clamp")
    ax2.axhline(-120, color="#dc2626", linestyle=":", linewidth=1.2)
    ax2.set_ylabel("W8 Envelope (LSB)", fontsize=10, fontweight="bold")
    ax2.set_xlabel("Elapsed Time (minutes)", fontsize=10, fontweight="bold")
    ax2.set_ylim(-132, 132)
    ax2.grid(True, linestyle=":", alpha=0.5)
    ax2.legend(loc="lower left", fontsize=8, ncol=3)

    plt.tight_layout()
    fig2.savefig(FIG_TRANSIENT, dpi=180)
    plt.close(fig2)


def write_markdown(stats, meta):
    lines = [
        "# Inverted MAML Card 1: 13-Minute 45% PWM 2-Beat Analog Bit-Slicing Thermal Report",
        "",
        "**Hardware:** Card 1 (`Trion T120F324` Master SoC + `Trion T20F256` Coprocessor, `1k/3.3k` summing attenuator)  ",
        "**Dataset:** `FPGA_code/logs/bit_slicing/card1_thermal_slicing_45pct_k1_lr0p06_l2_1024_13min_6warm.json` (`5,278` pairs)  ",
        f"**Hyperparameters:** `Heater Duty = {meta['heater_duty_pct']:.0f}%` (T20 0.2 Hz 90°-staggered hardware PWM), `K = {meta['k_batch']}`, `LR = {meta['lr']}`, `L2 = {meta['l2_reg']}`, `Momentum = 0.0` (pure SGD)  ",
        "",
        "---",
        "",
        "## 1. Executive Summary",
        "",
        "Under aggressive **45% hardware PWM thermal stress**, open-loop analog precision (`Regler OFF`, `W8 = 0`) degraded by **3.63 bits** from the cold baseline (**9.38 bits** in Phase 2) down to **5.75 bits** in Phase 8. Enabling closed-loop Forward Hadamard Propagation (`Regler ON`, `LR = 0.06`, `L2 = 1024`, `K = 1`) produced clear, repeatable positive ENOB steps during hot operation:",
        "",
        "- **Phase 5 vs Phase 6 (Warm):** Mean **+0.93 bits** (**6.95 b** vs **6.02 b**); steady-state **+1.08 bits** (**7.06 b** vs **5.98 b**).",
        "- **Phase 7 vs Phase 8 (Warm):** Mean **+0.87 bits** (**6.62 b** vs **5.75 b**); steady-state **+1.01 bits** (**6.74 b** vs **5.73 b**).",
        "- **Bottleneck Identified:** In Phases 5 and 7, `W8_msb` and `W8_lsb` both **railed at `+120 LSB`** under the `1k/3.3k` passive summing attenuator. Because the Vernier branch hit its rail, compensation authority saturated before fully canceling the 45% thermal drift. Resoldering the attenuator to **`1k/2.2k`** (+50% Vernier gain) is the primary hardware action item.",
        "",
        "---",
        "",
        "## 2. Phase-by-Phase Experimental Results",
        "",
        "| Phase | Regime | Pairs | Mean Comb ENOB | Steady-State Comb | MSB ENOB | LSB ENOB | W8 MSB [min, max] | W8 LSB [min, max] |",
        "| :--- | :--- | ---: | ---: | ---: | ---: | ---: | :--- | :--- |",
    ]
    for s in stats:
        lines.append(
            f"| P{s['phase_num']} | {s['name'].replace('Phase ' + str(s['phase_num']) + ': ', '')} | "
            f"{s['n_pairs']} | **{s['comb_mean']:.2f} b** | {s['comb_ss']:.2f} b | "
            f"{s['msb_mean']:.2f} b | {s['lsb_mean']:.2f} b | "
            f"`[{s['w8_msb_min']:+d}, {s['w8_msb_max']:+d}]` | `[{s['w8_lsb_min']:+d}, {s['w8_lsb_max']:+d}]` |"
        )

    lines += [
        "",
        "![Full 13-min Timeline](fig_card1_thermal_slicing_45pct_13min.png)",
        "",
        "![Hot-Phase Regler Step Response](fig_45pct_phase5_8_transient.png)",
        "",
        "---",
        "",
        "## 3. 2-Beat Analog Bit-Slicing Architecture & Locked Calibration",
        "",
        "1. **2-Beat Time-Multiplexed Slices:** Each pair executes Beat `2k` (`MSB`, Bank 0, `M_msb` scaled to ±50 LSB) followed by Beat `2k+1` (`LSB`, Bank 1, `M_lsb = round(0.75 * M_msb)`). T120 maintains completely isolated weight/velocity banks (`g_slice_bank[2]`, `0x1E subcmd 4`).",
        "2. **Strict Honesty (`t = 0` Cold Calibration):** Static linear gain `alpha` and DC offset `beta` are calibrated once at `t = 0` (heaters OFF) and locked inside T120 (`g_slice_alpha_q16`, `g_slice_beta`, `0x1E subcmd 5`) for the entire 13-minute run with zero post-hoc DSP correction.",
        "3. **Combined 8-Bit ENOB:** `Y_8bit = 16 * Y_MSB + Y_LSB`, evaluated continuously via `min(4.0, ENOB_MSB) + ENOB_LSB * clip(ENOB_MSB / 4.0, 0, 1)`.",
        "",
        "---",
        "",
        "## 4. Roadmap: Post-Analog Alpha/Beta 8-Channel FHP & `1k/2.2k` Attenuator",
        "",
        "Per `post_analog_alpha_beta_calibration_8_channel_fhp_specification.md`:",
        "- **Short-Term (Next Hardware Step):** Replace the `1k/3.3k` passive summing attenuator at `SUM35` with **`1k/2.2k`** to increase `Matrix 3/8` Vernier authority by `1.50x`, eliminating the `+120 LSB` rail saturation observed in Phases 5 and 7.",
        "- **Medium-Term (`PCBA v1.3.2` -> `SKY130` ASIC):** Add a shunt-triode post-analog `alpha/beta` stage before `ADC_49` driven by an expanded 16-pulse (`8x8`) Hadamard burst (Ch 0–5: matrix rows, Ch 6: `V_gain`, Ch 7: `V_offset`). Offloading static DC offset and linear gain to this slow outer loop lets L2 regularization keep `W8` centered near `0 LSB` for maximum non-linear thermal headroom.",
        "",
    ]

    md_text = "\n".join(lines)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    MD_OUT_DOCS.write_text(md_text)
    MD_OUT_ARTIFACT.write_text(md_text)


def build_pdf(stats, meta):
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, HRFlowable
    )
    from reportlab.pdfgen import canvas

    class NumberedCanvas(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._saved_page_states = []

        def showPage(self):
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            num_pages = len(self._saved_page_states)
            for state in self._saved_page_states:
                self.__dict__.update(state)
                self.draw_page_decorations(num_pages)
                super().showPage()
            super().save()

        def draw_page_decorations(self, page_count):
            self.saveState()
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#64748b"))
            if self._pageNumber > 1:
                self.drawString(48, 756, "INVERTED MAML (SE 2630397-4) | Card 1 13-Min 45% PWM Bit-Slicing Thermal Report")
                self.setStrokeColor(colors.HexColor("#cbd5e1"))
                self.setLineWidth(0.5)
                self.line(48, 750, 564, 750)
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(48, 42, 564, 42)
            self.drawString(48, 30, "Card 1 (1k/3.3k Attenuator) | LR=0.06, L2=1024, K=1")
            self.drawRightString(564, 30, f"Page {self._pageNumber} of {page_count}")
            self.restoreState()

    styles = getSampleStyleSheet()
    title_s = ParagraphStyle("T", parent=styles["Heading1"], fontSize=16, leading=20, textColor=colors.HexColor("#0f172a"), spaceAfter=4)
    sub_s = ParagraphStyle("Sub", parent=styles["Normal"], fontSize=9.5, leading=13, textColor=colors.HexColor("#475569"), spaceAfter=10)
    h2_s = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=11.5, leading=15, textColor=colors.HexColor("#0369a1"), spaceBefore=10, spaceAfter=4)
    body_s = ParagraphStyle("B", parent=styles["Normal"], fontSize=9.2, leading=13, textColor=colors.HexColor("#1e293b"), spaceAfter=6)
    bullet_s = ParagraphStyle("Bul", parent=body_s, leftIndent=14, bulletIndent=4, spaceAfter=3)

    for out_path in (PDF_OUT_DOCS, PDF_OUT_ARTIFACT):
        doc = SimpleDocTemplate(str(out_path), pagesize=letter, leftMargin=48, rightMargin=48, topMargin=56, bottomMargin=52)
        story = []
        story.append(Paragraph("Inverted MAML Card 1: 13-Min 45% PWM 2-Beat Analog Bit-Slicing Thermal Report", title_s))
        story.append(Paragraph(
            f"<b>Hardware:</b> Card 1 (Trion T120 + T20, 1k/3.3k Attenuator) &nbsp;|&nbsp; "
            f"<b>Params:</b> 45% HW PWM, K={meta['k_batch']}, LR={meta['lr']}, L2={meta['l2_reg']}, SGD (Mom=0) &nbsp;|&nbsp; "
            f"<b>Pairs:</b> {sum(s['n_pairs'] for s in stats):,}", sub_s
        ))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1")))
        story.append(Spacer(1, 8))

        story.append(Paragraph("1. Executive Summary", h2_s))
        story.append(Paragraph(
            "Under sustained 45% hardware PWM thermal stress, open-loop analog precision (Regler OFF, W8=0) dropped by <b>3.63 bits</b> "
            "from the cold baseline (<b>9.38 bits</b> in Phase 2) to <b>5.75 bits</b> in Phase 8. Enabling closed-loop Forward Hadamard "
            "Propagation (Regler ON, LR=0.06, L2=1024, K=1) delivered clear, repeatable positive ENOB steps:", body_s
        ))
        story.append(Paragraph("&bull; <b>Phase 5 vs Phase 6 (Warm):</b> Mean <b>+0.93 bits</b> (6.95 b vs 6.02 b); steady-state <b>+1.08 bits</b> (7.06 b vs 5.98 b).", bullet_s))
        story.append(Paragraph("&bull; <b>Phase 7 vs Phase 8 (Warm):</b> Mean <b>+0.87 bits</b> (6.62 b vs 5.75 b); steady-state <b>+1.01 bits</b> (6.74 b vs 5.73 b).", bullet_s))
        story.append(Paragraph("&bull; <b>Physical Bottleneck:</b> Both W8_msb and W8_lsb <b>railed at +120 LSB</b> in Phases 5 and 7 under the 1k/3.3k attenuator, capping compensation authority. Resoldering to <b>1k/2.2k</b> (+50% Vernier gain) is the next hardware step.", bullet_s))

        story.append(Paragraph("2. Phase-by-Phase Performance (5,278 Pairs)", h2_s))
        tdata = [["Phase", "Regime", "N", "Mean Comb", "SS Comb", "MSB", "LSB", "W8 MSB [min,max]", "W8 LSB [min,max]"]]
        for s in stats:
            tdata.append([
                f"P{s['phase_num']}",
                s["name"].replace(f"Phase {s['phase_num']}: ", ""),
                str(s["n_pairs"]),
                f"{s['comb_mean']:.2f} b",
                f"{s['comb_ss']:.2f} b",
                f"{s['msb_mean']:.2f} b",
                f"{s['lsb_mean']:.2f} b",
                f"[{s['w8_msb_min']:+d}, {s['w8_msb_max']:+d}]",
                f"[{s['w8_lsb_min']:+d}, {s['w8_lsb_max']:+d}]",
            ])
        tbl = Table(tdata, colWidths=[28, 96, 32, 54, 48, 38, 38, 86, 86])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7.8),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
            ("ALIGN", (2, 0), (-1, -1), "CENTER"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 8))
        story.append(Image(str(FIG_TIMELINE), width=510, height=375))

        story.append(PageBreak())
        story.append(Paragraph("3. Hot-Phase Step Response & Weight Saturation Diagnosis", h2_s))
        story.append(Image(str(FIG_TRANSIENT), width=510, height=282))
        story.append(Spacer(1, 8))
        story.append(Paragraph(
            "In Phases 5 and 7, activating closed-loop SGD immediately lifts Combined ENOB by ~0.9–1.1 bits relative to the adjacent "
            "Regler-OFF ablation phases (P6 and P8). However, the weight envelope plot confirms that the positive W8 rail (+120 LSB) is "
            "reached on both MSB and LSB slices. Because the 1k/3.3k attenuator limits the Vernier branch current injection into SUM35, "
            "further thermal drift cannot be absorbed once W8 saturates.", body_s
        ))

        story.append(Paragraph("4. Bit-Slicing Architecture & Post-Analog Alpha/Beta Roadmap", h2_s))
        story.append(Paragraph(
            "&bull; <b>2-Beat Time-Multiplexed Slicing:</b> Beat 2k (MSB, Bank 0) and Beat 2k+1 (LSB, Bank 1, 0.75x scale) run with fully isolated "
            "T120 weight/velocity banks (0x1E subcmd 4) and locked t=0 cold alpha/beta targets (0x1E subcmd 5).", bullet_s
        ))
        story.append(Paragraph(
            "&bull; <b>Immediate Hardware Action (1k/2.2k Attenuator):</b> Replacing the 3.3k summing resistor with 2.2k increases Vernier "
            "authority by 1.50x, giving W8 headroom to compensate 45% thermal drift without railing at +120 LSB.", bullet_s
        ))
        story.append(Paragraph(
            "&bull; <b>8-Channel FHP Post-Analog Stage (PCBA v1.3.2 / SKY130):</b> Per <i>post_analog_alpha_beta_calibration_8_channel_fhp_specification.md</i>, "
            "expanding the Hadamard burst from 12 to 16 pulses (Ch 0–5 matrix rows, Ch 6 V_gain shunt-triode, Ch 7 V_offset) offloads static DC "
            "offset and linear gain from Matrix 3/8, allowing L2 regularization to keep W8 centered near 0 LSB for full non-linear thermal headroom.", bullet_s
        ))
        doc.build(story, canvasmaker=NumberedCanvas)


def main():
    with open(DATA_JSON) as f:
        data = json.load(f)
    stats = compute_phase_stats(data)
    generate_figures(data)
    write_markdown(stats, data["metadata"])
    build_pdf(stats, data["metadata"])
    print(f"[+] Report generated:\n    {MD_OUT_DOCS}\n    {PDF_OUT_DOCS}\n    {PDF_OUT_ARTIFACT}")


if __name__ == "__main__":
    main()
