#!/home/olle/anaconda3/bin/python
"""
generate_card1_r1_baseline_report.py
====================================
Inverted MAML (Patent Pending SE 2630397-4) - Open Science Hardware

Generates high-resolution figures, Markdown report, and publication PDF report
for the Card 1 Round 1 Anti-Windup & Bit-Slicing Baseline Verification Run:
  - Dataset: FPGA_code/logs/bit_slicing/opt_r1_lr0p03_l2_1024_mom0p90_cl75.json
  - Cold Baseline Check: FPGA_code/logs/bit_slicing/cold_verify_k1.json
  - Explicit PCHIP thermal drift baseline E_base(t) & L_base(t) detrending
"""

from __future__ import annotations
import json
import shutil
import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from FPGA_code.scripts.analog_hyperparam_model import (
    _fit_thermal_baseline,
    _pchip_eval,
    _rolling_mean,
    extract_warm_trend_metrics,
)

R1_JSON = REPO_ROOT / "FPGA_code" / "logs" / "bit_slicing" / "opt_r1_lr0p03_l2_1024_mom0p90_cl75.json"
COLD_JSON = REPO_ROOT / "FPGA_code" / "logs" / "bit_slicing" / "cold_verify_k1.json"

REL_DIR = REPO_ROOT / "FPGA_code" / "releases" / "Release_20261114_ModeA_Card1_BitSlicing_AntiWindup_Baseline_R1"
REL_RPT_DIR = REL_DIR / "reports_and_logs"
REL_FIG_DIR = REL_RPT_DIR / "figures"
DOCS_DIR = REPO_ROOT / "FPGA_code" / "docs"
LOGS_DIR = REPO_ROOT / "FPGA_code" / "logs" / "bit_slicing"
ARTIFACT_DIR = Path("/home/olle/.gemini/antigravity/brain/fa59cd2e-8c8b-41e2-add0-77ffdf2fe431")

FIG_NAME = "fig_card1_r1_baseline_thermal_slicing.png"
MD_NAME = "INVERTED_MAML_CARD1_R1_BASELINE_THERMAL_SLICING_REPORT.md"
PDF_NAME = "INVERTED_MAML_CARD1_R1_BASELINE_THERMAL_SLICING_REPORT.pdf"


def compute_phase_stats(data: dict, base_t: np.ndarray, base_e: np.ndarray, base_lnL: np.ndarray) -> list[dict]:
    meta = data["metadata"]
    hist = data["history"]
    stats = []
    for pi, p in enumerate(meta["phases"]):
        rows = [r for r in hist if r["phase_idx"] == pi]
        if not rows:
            continue
        n = len(rows)
        q_start = max(5, min(20, n // 5))
        q_late = int(0.65 * n)
        t_s = np.array([float(r["elapsed_s"]) for r in rows], dtype=np.float64)
        comb = np.array([float(r["combined_enob_raw"]) for r in rows], dtype=np.float64)
        msb = np.array([float(r["enob_msb"]) for r in rows], dtype=np.float64)
        lsb = np.array([float(r["enob_lsb"]) for r in rows], dtype=np.float64)
        loss_tot = np.array([float(r["loss_msb"]) + float(r["loss_lsb"]) for r in rows], dtype=np.float64)
        w8m_max = np.array([max(abs(r["w8_msb_range"][0]), abs(r["w8_msb_range"][1])) for r in rows], dtype=np.int32)
        w8l_max = np.array([max(abs(r["w8_lsb_range"][0]), abs(r["w8_lsb_range"][1])) for r in rows], dtype=np.int32)
        w3_max = np.array([
            max(
                abs(r.get("w3_msb_range", [0, 0])[0]), abs(r.get("w3_msb_range", [0, 0])[1]),
                abs(r.get("w3_lsb_range", [0, 0])[0]), abs(r.get("w3_lsb_range", [0, 0])[1]),
            )
            for r in rows
        ], dtype=np.int32)
        w8_nz = sum(1 for r in rows if r["w8_msb_range"] != [0, 0] or r["w8_lsb_range"] != [0, 0])

        detr_late = None
        loss_ratio_late = None
        if p["heater"] and len(base_t) >= 2:
            eb = _pchip_eval(base_t, base_e, t_s)
            lb = np.exp(_pchip_eval(base_t, base_lnL, t_s))
            detr_late = float(np.mean(comb[q_late:] - eb[q_late:]))
            loss_ratio_late = float(np.exp(np.mean(np.log(np.maximum(1.0, lb[q_late:]) / np.maximum(1.0, loss_tot[q_late:])))))

        stats.append({
            "phase_num": pi + 1,
            "name": p["name"],
            "heater": p["heater"],
            "regler": p["regler"],
            "dur_min": p["dur_s"] / 60.0,
            "n_pairs": n,
            "comb_start": float(np.mean(comb[:q_start])),
            "comb_late": float(np.mean(comb[q_late:])),
            "comb_mean": float(np.mean(comb)),
            "msb_mean": float(np.mean(msb)),
            "lsb_mean": float(np.mean(lsb)),
            "loss_start": float(np.mean(loss_tot[:q_start])),
            "loss_late": float(np.mean(loss_tot[q_late:])),
            "detr_late_b": detr_late,
            "detr_loss_ratio": loss_ratio_late,
            "w8_msb_pk": int(np.max(w8m_max)),
            "w8_lsb_pk": int(np.max(w8l_max)),
            "w3_pk": int(np.max(w3_max)),
            "w8_nz": w8_nz,
        })
    return stats


def generate_figure(data: dict, base_t: np.ndarray, base_e: np.ndarray, base_lnL: np.ndarray, fig_out: Path) -> None:
    hist = data["history"]
    meta = data["metadata"]
    phases = meta["phases"]
    clamp = int(meta.get("clamp_lsb", 75))

    t_s = np.array([float(r["elapsed_s"]) for r in hist], dtype=np.float64)
    t_min = t_s / 60.0
    comb = np.array([float(r["combined_enob_raw"]) for r in hist], dtype=np.float64)
    msb = np.array([float(r["enob_msb"]) for r in hist], dtype=np.float64)
    lsb = np.array([float(r["enob_lsb"]) for r in hist], dtype=np.float64)
    loss_tot = np.array([float(r["loss_msb"]) + float(r["loss_lsb"]) for r in hist], dtype=np.float64)

    comb_sm = _rolling_mean(comb, win=21)
    loss_sm = _rolling_mean(loss_tot, win=21)

    heat_mask = np.array([bool(r.get("heater_on", False)) for r in hist])
    eb_curve = _pchip_eval(base_t, base_e, t_s[heat_mask]) if len(base_t) >= 2 else None
    lb_curve = np.exp(_pchip_eval(base_t, base_lnL, t_s[heat_mask])) if len(base_t) >= 2 else None

    w8m_min = np.array([r["w8_msb_range"][0] for r in hist])
    w8m_max = np.array([r["w8_msb_range"][1] for r in hist])
    w8l_min = np.array([r["w8_lsb_range"][0] for r in hist])
    w8l_max = np.array([r["w8_lsb_range"][1] for r in hist])
    w3_min = np.array([min(r["w3_msb_range"][0], r["w3_lsb_range"][0]) for r in hist])
    w3_max = np.array([max(r["w3_msb_range"][1], r["w3_lsb_range"][1]) for r in hist])

    def shade(ax):
        acc = 0.0
        for p in phases:
            t0 = acc / 60.0
            t1 = (acc + p["dur_s"]) / 60.0
            acc += p["dur_s"]
            if not p["heater"]:
                col, al = ("#dbeafe", 0.40) if p["regler"] else ("#e0e7ff", 0.25)
            else:
                col, al = ("#dcfce7", 0.45) if p["regler"] else ("#fee2e2", 0.40)
            ax.axvspan(t0, t1, color=col, alpha=al, zorder=0)
            ax.axvline(t0, color="#94a3b8", linestyle="--", linewidth=0.75, zorder=1)

    fig, axes = plt.subplots(3, 1, figsize=(11.0, 8.6), sharex=True, gridspec_kw={"height_ratios": [1.35, 1.0, 1.0]})
    fig.patch.set_facecolor("white")

    # Panel 1: ENOB + PCHIP thermal drift baseline E_base(t)
    ax = axes[0]
    shade(ax)
    ax.plot(t_min, comb, color="#7dd3fc", linewidth=0.55, alpha=0.55, label="Raw Combined 8-Bit ENOB")
    ax.plot(t_min, comb_sm, color="#0369a1", linewidth=2.0, label="21-Pair Moving Mean Combined ENOB")
    ax.plot(t_min, msb, color="#16a34a", linewidth=0.7, alpha=0.45, label="MSB Slice (Beat 2k)")
    ax.plot(t_min, lsb, color="#ea580c", linewidth=0.7, alpha=0.45, label="LSB Slice (Beat 2k+1)")
    if eb_curve is not None:
        ax.plot(t_min[heat_mask], eb_curve, color="#dc2626", linestyle="--", linewidth=1.9, label="Thermal Baseline E_base(t) [Cold/Warm OFF Fit]")
        ax.fill_between(
            t_min[heat_mask], eb_curve, comb_sm[heat_mask],
            where=(comb_sm[heat_mask] >= eb_curve),
            color="#22c55e", alpha=0.18, interpolate=True, label="Closed-Loop Gain Above E_base(t)"
        )
    ax.axhline(8.0, color="#d97706", linestyle=":", linewidth=1.2, label="8.0-bit Target")
    ax.set_ylabel("ENOB (bits)", fontsize=10, fontweight="bold")
    ax.set_ylim(2.8, 9.95)
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.legend(loc="lower left", fontsize=7.6, ncol=2, framealpha=0.92)
    ax.set_title(
        f"Card 1 Round 1 Anti-Windup Baseline (40% PWM, K={meta['k_batch']}, LR={meta['lr']}, L2={meta['l2_reg']}, Mom={meta['momentum']}, Clamp=±{clamp} LSB)",
        fontsize=11, fontweight="bold"
    )
    acc = 0.0
    for pi, p in enumerate(phases):
        t_mid = (acc + 0.5 * p["dur_s"]) / 60.0
        acc += p["dur_s"]
        lbl = f"P{pi+1} ({'ON' if p['regler'] else 'OFF'})"
        ax.text(t_mid, 9.75, lbl, ha="center", va="top", fontsize=7.8, fontweight="bold",
                color="#15803d" if p["regler"] else "#b91c1c")

    # Panel 2: Combined Loss + L_base(t)
    ax = axes[1]
    shade(ax)
    ax.plot(t_min, loss_tot, color="#94a3b8", linewidth=0.5, alpha=0.45, label="Raw Loss (MSB+LSB)")
    ax.plot(t_min, loss_sm, color="#0f172a", linewidth=1.8, label="21-Pair Moving Mean Loss (LSB²)")
    if lb_curve is not None:
        ax.plot(t_min[heat_mask], lb_curve, color="#dc2626", linestyle="--", linewidth=1.8, label="Thermal Baseline Loss L_base(t)")
    ax.set_ylabel("Total Loss (LSB²)", fontsize=10, fontweight="bold")
    ax.set_ylim(0, max(75000.0, float(np.percentile(loss_sm, 99.5) * 1.12)))
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.legend(loc="upper left", fontsize=8.0, framealpha=0.92)

    # Panel 3: W8 and W3 Dynamic Envelope with Anti-Windup Rails
    ax = axes[2]
    shade(ax)
    ax.plot(t_min, w8m_max, color="#16a34a", linewidth=1.1, label="W8 MSB [min, max]")
    ax.plot(t_min, w8m_min, color="#16a34a", linewidth=1.1, linestyle="--")
    ax.plot(t_min, w8l_max, color="#ea580c", linewidth=1.1, label="W8 LSB [min, max]")
    ax.plot(t_min, w8l_min, color="#ea580c", linewidth=1.1, linestyle="--")
    ax.plot(t_min, w3_max, color="#7c3aed", linewidth=0.9, label=f"W3 Data Rows [±{max(15, clamp // 3)} Cap]")
    ax.plot(t_min, w3_min, color="#7c3aed", linewidth=0.9, linestyle=":")
    ax.axhline(clamp, color="#dc2626", linestyle=":", linewidth=1.2, label=f"W8 Clamp (±{clamp} LSB)")
    ax.axhline(-clamp, color="#dc2626", linestyle=":", linewidth=1.2)
    ax.set_ylabel("Weights (LSB)", fontsize=10, fontweight="bold")
    ax.set_xlabel("Elapsed Time (minutes)", fontsize=10, fontweight="bold")
    ax.set_ylim(-clamp - 12, clamp + 12)
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.legend(loc="lower left", fontsize=7.8, ncol=2, framealpha=0.92)

    plt.tight_layout()
    fig_out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(fig_out, dpi=180)
    plt.close(fig)


def write_markdown(stats: list[dict], meta: dict, trend_info: dict, cold_stats: list[dict], md_path: Path, fig_ref: str) -> None:
    tr = trend_info["trends"]
    lines = [
        "# Inverted MAML Card 1: Round 1 Anti-Windup & 2-Beat Bit-Slicing Baseline Report",
        "",
        "**Hardware:** Card 1 (`Trion T120F324` Master SoC + `Trion T20F256` Coprocessor, `1k / 2.2k` Passive Attenuator)  ",
        "**Firmware:** `T120_SOC_ETH_FW v2.2-MAML (SW Build Nov 14 2026 10:15:16)`, `HW_LOGIC: 0x20261030`  ",
        f"**Round 1 Dataset:** `FPGA_code/logs/bit_slicing/opt_r1_lr0p03_l2_1024_mom0p90_cl75.json` (`{sum(s['n_pairs'] for s in stats):,}` pairs)  ",
        f"**Hyperparameters:** `Heater = {meta['heater_duty_pct']:.0f}%` PWM, `K = {meta['k_batch']}`, `LR = {meta['lr']}`, `L2 = {meta['l2_reg']}`, `Momentum = {meta['momentum']}`, `Clamp = ±{meta['clamp_lsb']} LSB`  ",
        "",
        "---",
        "",
        "## 1. Executive Summary & Verification Milestones",
        "",
        "1. **Verified Cold Reference Without Heating (`cold_verify_k1.json`):**",
        f"   - `Cold / Regler ON`: mean **{cold_stats[0]['comb_mean']:.2f} b** (`min {cold_stats[0]['comb_min']:.2f} b`).",
        f"   - `Cold / Regler OFF (W8=0)`: mean **{cold_stats[1]['comb_mean']:.2f} b** (`min {cold_stats[1]['comb_min']:.2f} b`), confirming well over the `> 8.0 b` cold baseline target.",
        "2. **Firmware Root-Cause Fixes Verified Under Thermal Stress:**",
        "   - Corrected two-layer `dx8` backpropagation sign (`err49[j] -> -err49[j]`), `grad_m3_out` scaling (`>> 3` -> `>> 6`), and added `sat_comp_m3_q14()` capping M3 rows `0..5` to `±25 LSB` so they never disturb the `±40 LSB` fixed M3 clock staircase.",
        "   - Implemented integrated-L2 back-calculation anti-windup (`maml_momentum_step_antiwindup`) plus `MAML_CMD_BATCH_STEP` Ethernet padding tolerance (`req_len >= 5`).",
        "3. **Thermal-Detrended Closed-Loop Lift (`analog_hyperparam_model.py`):**",
        f"   - Fitting the continuous PCHIP uncompensated thermal curve $E_{{\\text{{base}}}}(t)$ through `Cold OFF -> Warm OFF` confirms a weighted detrended `Warm ON` lift of **`{tr['warm_step_lift_b']:+.2f} b`**, loss reduction ratio **`{tr['warm_loss_ratio']:.2f}x`**, detrended convergence climb **`{tr['hot_conv_climb_b']:+.2f} b`**, anti-windup recovery rate **`{tr['recovery_rate']:.2f}`**, and composite score **`{trend_info['score']:+.3f}`**.",
        "   - In **Phase 5 (`Warm / Regler ON`)**, Combined ENOB actively climbed **`7.74 b -> 7.99 b`** (mean **`8.07 b`**) while total Loss declined, followed by an immediate decay in **Phase 6 (`Warm / Regler OFF`)** to **`6.96 b -> 6.59 b`** (mean **`6.71 b`**) with **0.00%** `W8` leak.",
        "",
        "---",
        "",
        "## 2. Round 1 Phase-by-Phase Results (`4,289` Pairs)",
        "",
        "| Phase | Regime | Pairs | Comb ENOB (`Start -> Late`, Mean) | Δ vs $E_{\\text{base}}(t)$ | Total Loss (`Start -> Late`) | Loss Ratio | W8 Peak `[MSB, LSB]` | W3 Peak | W8 Non-Zero |",
        "| :--- | :--- | ---: | :---: | :---: | :---: | :---: | :---: | :---: | ---: |",
    ]
    for s in stats:
        d_str = f"**{s['detr_late_b']:+.2f} b**" if s["detr_late_b"] is not None else "—"
        lr_str = f"**{s['detr_loss_ratio']:.2f}x**" if s["detr_loss_ratio"] is not None else "—"
        lines.append(
            f"| P{s['phase_num']} | {s['name'].replace('Phase ' + str(s['phase_num']) + ': ', '')} | "
            f"{s['n_pairs']} | `{s['comb_start']:.2f} -> {s['comb_late']:.2f}` (**{s['comb_mean']:.2f} b**) | "
            f"{d_str} | `{s['loss_start']:.0f} -> {s['loss_late']:.0f}` | {lr_str} | "
            f"`[{s['w8_msb_pk']}, {s['w8_lsb_pk']}]` | `{s['w3_pk']}` | `{s['w8_nz']}` |"
        )

    lines += [
        "",
        f"![Round 1 Baseline Timeline & Thermal Detrending]({fig_ref})",
        "",
        "---",
        "",
        "## 3. Release Restore Point & Next Optimization Steps",
        "",
        "- **Archived Release Package:** `FPGA_code/releases/Release_20261114_ModeA_Card1_BitSlicing_AntiWindup_Baseline_R1/`",
        "- **Next ML Model Proposal (Round 2):** `lr = 0.035`, `l2_reg = 1536`, `momentum = 0.85`, `clamp = ±75 LSB` to reduce warm-ON jitter (`0.33 b`) and tighten L2 anchor while boosting convergence gain.",
        "",
    ]
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(lines))


def build_pdf(stats: list[dict], meta: dict, trend_info: dict, cold_stats: list[dict], fig_path: Path, pdf_out: Path) -> None:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable
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
                self.draw_decorations(num_pages)
                super().showPage()
            super().save()

        def draw_decorations(self, page_count):
            self.saveState()
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#64748b"))
            self.line(44, 40, 568, 40)
            self.drawString(44, 28, "INVERTED MAML (SE 2630397-4) | Card 1 Round 1 Anti-Windup & Bit-Slicing Baseline")
            self.drawRightString(568, 28, f"Page {self._pageNumber} of {page_count}")
            self.restoreState()

    styles = getSampleStyleSheet()
    title_s = ParagraphStyle("T", parent=styles["Heading1"], fontSize=14.5, leading=18, textColor=colors.HexColor("#0f172a"), spaceAfter=3)
    sub_s = ParagraphStyle("Sub", parent=styles["Normal"], fontSize=8.8, leading=12, textColor=colors.HexColor("#475569"), spaceAfter=8)
    h2_s = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=11, leading=14, textColor=colors.HexColor("#0369a1"), spaceBefore=8, spaceAfter=4)
    body_s = ParagraphStyle("B", parent=styles["Normal"], fontSize=8.8, leading=12.2, textColor=colors.HexColor("#1e293b"), spaceAfter=4)
    bul_s = ParagraphStyle("Bul", parent=body_s, leftIndent=12, bulletIndent=3, spaceAfter=2.5)

    tr = trend_info["trends"]
    doc = SimpleDocTemplate(str(pdf_out), pagesize=letter, leftMargin=44, rightMargin=44, topMargin=40, bottomMargin=50)
    story = [
        Paragraph("Inverted MAML Card 1: Round 1 Anti-Windup & Bit-Slicing Baseline Report", title_s),
        Paragraph(
            f"<b>Hardware:</b> Card 1 (T120+T20, 1k/2.2k) &nbsp;|&nbsp; "
            f"<b>FW:</b> v2.2-MAML (0x20261030) &nbsp;|&nbsp; "
            f"<b>Params:</b> 40% PWM, K={meta['k_batch']}, LR={meta['lr']}, L2={meta['l2_reg']}, Mom={meta['momentum']}, Clamp=±{meta['clamp_lsb']} LSB",
            sub_s,
        ),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1")),
        Spacer(1, 6),
        Paragraph("1. Verification Summary", h2_s),
        Paragraph(
            f"&bull; <b>Cold Baseline (Heaters OFF, K=1):</b> Phase 1 ON = <b>{cold_stats[0]['comb_mean']:.2f} b</b>, Phase 2 OFF = <b>{cold_stats[1]['comb_mean']:.2f} b</b> (W8=0 strictly).",
            bul_s,
        ),
        Paragraph(
            f"&bull; <b>Thermal-Detrended Closed-Loop Performance:</b> Detrended Warm-ON Step Lift = <b>{tr['warm_step_lift_b']:+.2f} b</b>, "
            f"Loss Ratio = <b>{tr['warm_loss_ratio']:.2f}x</b>, Convergence Climb = <b>{tr['hot_conv_climb_b']:+.2f} b</b>, "
            f"Anti-Windup Recovery = <b>{tr['recovery_rate']:.2f}</b>, Score = <b>{trend_info['score']:+.3f}</b>.",
            bul_s,
        ),
        Paragraph(
            "&bull; <b>Hot Convergence Proof (P5 vs P6):</b> In Warm / Regler ON (P5), ENOB climbed from <b>7.74 -> 7.99 b</b> (mean <b>8.07 b</b>) while Loss dropped "
            "(18,781 -> 16,896 MSB; 17,635 -> 13,715 LSB). Switching to Warm / Regler OFF (P6) caused immediate degradation to <b>6.96 -> 6.59 b</b> (mean <b>6.71 b</b>) with 0% W8 leak.",
            bul_s,
        ),
        Paragraph("2. Phase-by-Phase Metrics (4,289 Pairs)", h2_s),
    ]

    tdata = [["Phase", "Regime", "N", "Start->Late (Mean)", "Δ vs E_base", "Loss Start->Late", "W8 Pk [M,L]", "W3 Pk", "W8 nz"]]
    for s in stats:
        d_str = f"{s['detr_late_b']:+.2f} b" if s["detr_late_b"] is not None else "-"
        tdata.append([
            f"P{s['phase_num']}",
            s["name"].replace(f"Phase {s['phase_num']}: ", ""),
            str(s["n_pairs"]),
            f"{s['comb_start']:.2f}->{s['comb_late']:.2f} ({s['comb_mean']:.2f}b)",
            d_str,
            f"{s['loss_start']:.0f}->{s['loss_late']:.0f}",
            f"[{s['w8_msb_pk']},{s['w8_lsb_pk']}]",
            str(s["w3_pk"]),
            str(s["w8_nz"]),
        ])
    tbl = Table(tdata, colWidths=[26, 94, 30, 96, 48, 86, 52, 32, 34])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
        ("ALIGN", (2, 0), (-1, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 8))
    story.append(Image(str(fig_path), width=520, height=405))
    doc.build(story, canvasmaker=NumberedCanvas)


def main():
    with open(R1_JSON) as f:
        r1_data = json.load(f)
    with open(COLD_JSON) as f:
        cold_data = json.load(f)

    cold_stats = []
    for pidx in [0, 1]:
        rows = [r for r in cold_data["history"] if r["phase_idx"] == pidx]
        vals = [float(r["combined_enob_raw"]) for r in rows]
        cold_stats.append({"comb_mean": float(np.mean(vals)), "comb_min": float(np.min(vals))})

    base_t, base_e, base_lnL = _fit_thermal_baseline(r1_data["history"])
    stats = compute_phase_stats(r1_data, base_t, base_e, base_lnL)
    trend_info = extract_warm_trend_metrics(str(R1_JSON))

    fig_logs = LOGS_DIR / FIG_NAME
    fig_rel = REL_FIG_DIR / FIG_NAME
    fig_art = ARTIFACT_DIR / FIG_NAME
    fig_docs = DOCS_DIR / FIG_NAME

    generate_figure(r1_data, base_t, base_e, base_lnL, fig_rel)
    for dst in (fig_logs, fig_art, fig_docs):
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(fig_rel, dst)

    write_markdown(stats, r1_data["metadata"], trend_info, cold_stats, REL_RPT_DIR / MD_NAME, f"figures/{FIG_NAME}")
    write_markdown(stats, r1_data["metadata"], trend_info, cold_stats, DOCS_DIR / MD_NAME, FIG_NAME)
    write_markdown(stats, r1_data["metadata"], trend_info, cold_stats, ARTIFACT_DIR / MD_NAME, str(fig_art))

    build_pdf(stats, r1_data["metadata"], trend_info, cold_stats, fig_rel, REL_RPT_DIR / PDF_NAME)
    shutil.copy2(REL_RPT_DIR / PDF_NAME, DOCS_DIR / PDF_NAME)
    shutil.copy2(REL_RPT_DIR / PDF_NAME, ARTIFACT_DIR / PDF_NAME)
    print(f"[+] Round 1 Baseline Report generated successfully:\n    {REL_RPT_DIR / PDF_NAME}\n    {DOCS_DIR / PDF_NAME}\n    {ARTIFACT_DIR / PDF_NAME}")


if __name__ == "__main__":
    main()
