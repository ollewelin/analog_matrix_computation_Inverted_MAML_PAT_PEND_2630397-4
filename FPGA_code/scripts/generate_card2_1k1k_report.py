#!/usr/bin/env python3
"""
generate_card2_1k1k_report.py
=============================
Inverted MAML (Patent Pending SE 2630397-4) - Open Science Hardware

Generates the dedicated Card 2 (1k / 1k, 50/50 Passive Summing Attenuator)
Round 20 Thermal Bit-Slicing Report (Markdown + PDF + 4-Panel Timeline +
All-180-Weight Dynamics Figure) and archives dataset + reports in dedicated
Card 2 storage under FPGA_code/releases/Release_20261127_Card2_1k1k_BitSlicing_R20/.
"""

from __future__ import annotations
import argparse
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

LOGS_DIR = REPO_ROOT / "FPGA_code" / "logs" / "bit_slicing"
CONFIG_DIR = REPO_ROOT / "FPGA_code" / "config"
DOCS_DIR = REPO_ROOT / "FPGA_code" / "docs"
DOCS_FIG_DIR = DOCS_DIR / "figures"
ARTIFACT_DIR = Path("/home/olle/.gemini/antigravity/brain/fa59cd2e-8c8b-41e2-add0-77ffdf2fe431")


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

        detr_mean = None
        loss_ratio_mean = None
        if p["heater"] and len(base_t) >= 2:
            eb = _pchip_eval(base_t, base_e, t_s)
            lb = np.exp(_pchip_eval(base_t, base_lnL, t_s))
            detr_mean = float(np.mean(comb - eb))
            loss_ratio_mean = float(np.mean(lb) / max(float(np.mean(loss_tot)), 1.0))

        stats.append({
            "phase_num": pi + 1,
            "name": p["name"],
            "heater": bool(p["heater"]),
            "duty": float(p.get("duty", 0.0)),
            "regler": bool(p["regler"]),
            "n": n,
            "comb_start": float(np.mean(comb[:q_start])),
            "comb_late": float(np.mean(comb[q_late:])),
            "comb_mean": float(np.mean(comb)),
            "msb_mean": float(np.mean(msb)),
            "lsb_mean": float(np.mean(lsb)),
            "loss_start": float(np.mean(loss_tot[:q_start])),
            "loss_late": float(np.mean(loss_tot[q_late:])),
            "loss_mean": float(np.mean(loss_tot)),
            "detr_mean": detr_mean,
            "loss_ratio_mean": loss_ratio_mean,
            "w8m_peak": int(np.max(w8m_max)),
            "w8l_peak": int(np.max(w8l_max)),
            "w3_peak": int(np.max(w3_max)),
            "w8_nz": int(w8_nz),
        })
    return stats


def make_timeline_figure(data: dict, base_t: np.ndarray, base_e: np.ndarray, base_lnL: np.ndarray, out_path: Path):
    hist = data["history"]
    meta = data["metadata"]
    t_min = np.array([float(r["elapsed_s"]) / 60.0 for r in hist])
    t_s = np.array([float(r["elapsed_s"]) for r in hist])
    comb = np.array([float(r["combined_enob_raw"]) for r in hist])
    msb = np.array([float(r["enob_msb"]) for r in hist])
    lsb = np.array([float(r["enob_lsb"]) for r in hist])
    loss_tot = np.array([float(r["loss_msb"]) + float(r["loss_lsb"]) for r in hist])
    w8m_min = np.array([r["w8_msb_range"][0] for r in hist])
    w8m_max = np.array([r["w8_msb_range"][1] for r in hist])
    w8l_min = np.array([r["w8_lsb_range"][0] for r in hist])
    w8l_max = np.array([r["w8_lsb_range"][1] for r in hist])
    w3_min = np.array([min(r.get("w3_msb_range", [0, 0])[0], r.get("w3_lsb_range", [0, 0])[0]) for r in hist])
    w3_max = np.array([max(r.get("w3_msb_range", [0, 0])[1], r.get("w3_lsb_range", [0, 0])[1]) for r in hist])
    pidx = np.array([r["phase_idx"] for r in hist])

    bounds = []
    last_p = -1
    for i, p in enumerate(pidx):
        if p != last_p:
            bounds.append(t_min[i])
            last_p = p
    bounds.append(t_min[-1])

    fig, axes = plt.subplots(4, 1, figsize=(14, 12.5), sharex=True, gridspec_kw={"height_ratios": [2.4, 2.0, 1.7, 1.9]})

    ax0 = axes[0]
    ax0.set_title(
        "Inverted MAML Card 2 (1k / 1k = 50/50 Summing Attenuator): R20 Thermal Bit-Slicing\n"
        f"LR={meta['lr']}, L2={meta['l2_reg']}, Mom={meta['momentum']}, Clamp=±{meta['clamp_lsb']} LSB, K={meta['k_batch']} | Fresh Cold DC Cal",
        fontsize=13, fontweight="bold", pad=10,
    )
    for pi in range(len(bounds) - 1):
        reg = meta["phases"][pi]["regler"]
        heat = meta["phases"][pi]["duty"] if meta["phases"][pi]["heater"] else 0.0
        col = "#e8f5e9" if reg else ("#fff3e0" if heat <= 30 else "#ffebee")
        for ax in axes:
            ax.axvspan(bounds[pi], bounds[pi + 1], color=col, alpha=0.55, zorder=0)
        mid = 0.5 * (bounds[pi] + bounds[pi + 1])
        ax0.text(mid, 9.95, f"P{pi+1} ({heat:.0f}%)\n{'ON' if reg else 'OFF'}",
                 ha="center", va="top", fontsize=7.8, fontweight="bold",
                 color="#1b5e20" if reg else "#b71c1c")

    ax0.plot(t_min, comb, color="#1565c0", alpha=0.25, linewidth=0.8)
    ax0.plot(t_min, _rolling_mean(comb, 25), color="#0d47a1", linewidth=2.3, label="Combined ENOB (25-beat smooth)")
    if len(base_t) >= 2:
        eb = _pchip_eval(base_t, base_e, t_s)
        warm_mask = t_s >= float(base_t[0])
        ax0.plot(t_min[warm_mask], eb[warm_mask], color="#d32f2f", linestyle="--", linewidth=1.6, label="Thermal OFF Baseline E_base(t)")
    ax0.axhline(8.0, color="gray", linestyle=":", linewidth=1.1, label="8.0-Bit Target")
    ax0.set_ylabel("Combined ENOB (b)", fontweight="bold")
    ax0.set_ylim(5.5, 10.2)
    ax0.grid(True, linestyle=":", alpha=0.6)
    ax0.legend(loc="lower left", fontsize=9, framealpha=0.92)

    ax1 = axes[1]
    ax1.semilogy(t_min, loss_tot, color="#d84315", alpha=0.25, linewidth=0.8)
    ax1.semilogy(t_min, _rolling_mean(loss_tot, 25), color="#bf360c", linewidth=2.1, label="Total Squared Loss (LSB², 25-beat smooth)")
    if len(base_t) >= 2:
        lb = np.exp(_pchip_eval(base_t, base_lnL, t_s))
        warm_mask = t_s >= float(base_t[0])
        ax1.semilogy(t_min[warm_mask], lb[warm_mask], color="#5d4037", linestyle="--", linewidth=1.5, label="Thermal OFF Baseline Loss")
    ax1.set_ylabel("Total Loss (LSB², Log)", fontweight="bold")
    ax1.set_ylim(1000, 80000)
    ax1.grid(True, which="both", linestyle=":", alpha=0.6)
    ax1.legend(loc="upper left", fontsize=9, framealpha=0.92)

    ax2 = axes[2]
    ax2.plot(t_min, _rolling_mean(msb, 25), color="#1976d2", linewidth=1.8, label="MSB Slice ENOB")
    ax2.plot(t_min, _rolling_mean(lsb, 25), color="#7b1fa2", linewidth=1.8, label="LSB Slice ENOB")
    ax2.set_ylabel("Slice ENOB (b)", fontweight="bold")
    ax2.set_ylim(3.0, 7.2)
    ax2.grid(True, linestyle=":", alpha=0.6)
    ax2.legend(loc="lower left", fontsize=9, framealpha=0.92)

    ax3 = axes[3]
    ax3.fill_between(t_min, w8m_min, w8m_max, color="#00897b", alpha=0.38, label="W8 MSB Envelope")
    ax3.fill_between(t_min, w8l_min, w8l_max, color="#26a69a", alpha=0.25, label="W8 LSB Envelope")
    ax3.plot(t_min, w3_max, color="#f57c00", linewidth=1.2, label="W3 Max/Min Envelope")
    ax3.plot(t_min, w3_min, color="#f57c00", linewidth=1.2)
    ax3.axhline(+meta["clamp_lsb"], color="#b71c1c", linestyle="--", linewidth=1.1, label=f"Clamp (±{meta['clamp_lsb']} LSB)")
    ax3.axhline(-meta["clamp_lsb"], color="#b71c1c", linestyle="--", linewidth=1.1)
    ax3.set_ylabel("Weights (LSB)", fontweight="bold")
    ax3.set_xlabel("Elapsed Experiment Time (Minutes)", fontweight="bold")
    ax3.set_ylim(-100, 100)
    ax3.grid(True, linestyle=":", alpha=0.6)
    ax3.legend(loc="lower left", ncol=2, fontsize=8.5, framealpha=0.92)

    plt.tight_layout()
    plt.savefig(out_path, dpi=250)
    plt.close()


def make_all_weights_figure(data: dict, out_path: Path):
    hist = data["history"]
    t_min = np.array([float(r["elapsed_s"]) / 60.0 for r in hist])
    w8_msb = np.array([r["w8_msb"] for r in hist])  # (N, 7, 6)
    w8_lsb = np.array([r["w8_lsb"] for r in hist])
    w3_msb = np.array([r["w3_msb"] for r in hist])  # (N, 8, 6)
    w3_lsb = np.array([r["w3_lsb"] for r in hist])

    fig, axes = plt.subplots(2, 2, figsize=(14, 9), sharex=True, sharey=True)
    panels = [
        (axes[0, 0], w8_msb.reshape(len(t_min), -1), "Matrix 8 MSB (42 Weights)", "#00695c"),
        (axes[0, 1], w8_lsb.reshape(len(t_min), -1), "Matrix 8 LSB (42 Weights)", "#0277bd"),
        (axes[1, 0], w3_msb.reshape(len(t_min), -1), "Matrix 3 MSB (48 Weights)", "#ef6c00"),
        (axes[1, 1], w3_lsb.reshape(len(t_min), -1), "Matrix 3 LSB (48 Weights)", "#6a1b9a"),
    ]
    for ax, mat, title, col in panels:
        for j in range(mat.shape[1]):
            ax.plot(t_min, mat[:, j], color=col, alpha=0.45, linewidth=0.8)
        ax.axhline(+90, color="#b71c1c", linestyle="--", linewidth=0.9)
        ax.axhline(-90, color="#b71c1c", linestyle="--", linewidth=0.9)
        ax.axhline(0, color="gray", linewidth=0.6)
        ax.set_title(title, fontsize=11, fontweight="bold")
        ax.set_ylim(-98, 98)
        ax.grid(True, linestyle=":", alpha=0.55)
    axes[1, 0].set_xlabel("Elapsed Time (Minutes)", fontweight="bold")
    axes[1, 1].set_xlabel("Elapsed Time (Minutes)", fontweight="bold")
    axes[0, 0].set_ylabel("Weight (LSB)", fontweight="bold")
    axes[1, 0].set_ylabel("Weight (LSB)", fontweight="bold")
    fig.suptitle("Card 2 (1k / 1k): All 84 W(8) & 96 W(3) Individual Weight Trajectories", fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig(out_path, dpi=220)
    plt.close()


def main():
    parser = argparse.ArgumentParser(description="Generate Card 2 (1k/1k) R20 Thermal Slicing Report")
    parser.add_argument("--json", type=Path, default=LOGS_DIR / "card2_1k1k_r20_lr0p055_l2_1920_mom0p85_cl90.json")
    parser.add_argument("--dc-cal", type=Path, default=CONFIG_DIR / "card2_1k1k_dc_cal.json")
    parser.add_argument("--slug", default="card2_1k1k_r20_lr0p055_l2_1920_mom0p85_cl90")
    parser.add_argument("--title-prefix", default="INVERTED_MAML_CARD2_1K1K_R20_LR0P055_L2_1920_MOM0P85_CL90_THERMAL_SLICING_REPORT")
    parser.add_argument("--rel-name", default="Release_20261127_Card2_1k1k_BitSlicing_R20")
    parser.add_argument("--heat-label", default="30%/40% PWM")
    args = parser.parse_args()

    json_path = args.json if args.json.is_absolute() else REPO_ROOT / args.json
    dc_cal_path = args.dc_cal if args.dc_cal.is_absolute() else REPO_ROOT / args.dc_cal
    rel_dir = REPO_ROOT / "FPGA_code" / "releases" / args.rel_name / "reports_and_logs"
    rel_fig_dir = rel_dir / "figures"

    DOCS_FIG_DIR.mkdir(parents=True, exist_ok=True)
    rel_fig_dir.mkdir(parents=True, exist_ok=True)

    with open(json_path) as f:
        data = json.load(f)
    with open(dc_cal_path) as f:
        dc_cal = json.load(f)

    meta = data["metadata"]
    hist = data["history"]

    base_t, base_e, base_lnL = _fit_thermal_baseline(hist)
    warm_metrics = extract_warm_trend_metrics(json_path)
    stats = compute_phase_stats(data, base_t, base_e, base_lnL)

    tl_fig = DOCS_FIG_DIR / f"fig_{args.slug}_thermal_slicing.png"
    w_fig = DOCS_FIG_DIR / f"fig_{args.slug}_w8_w3_all_weights.png"
    make_timeline_figure(data, base_t, base_e, base_lnL, tl_fig)
    make_all_weights_figure(data, w_fig)

    # Copy figures + raw logs to dedicated Card 2 storage + artifacts
    for src in (tl_fig, w_fig):
        shutil.copy2(src, rel_fig_dir / src.name)
        shutil.copy2(src, ARTIFACT_DIR / src.name)
    shutil.copy2(json_path, rel_dir / json_path.name)
    shutil.copy2(dc_cal_path, rel_dir / dc_cal_path.name)

    alpha_msb = [round(x, 4) for x in dc_cal["calib_msb"]["alpha"]]
    beta_msb = [round(x, 1) for x in dc_cal["calib_msb"]["beta"]]
    alpha_lsb = [round(x, 4) for x in dc_cal["calib_lsb"]["alpha"]]
    beta_lsb = [round(x, 1) for x in dc_cal["calib_lsb"]["beta"]]

    # Build phase rows
    rows_md = []
    for s in stats:
        detr_str = f"**{s['detr_mean']:+.2f} b**" if s["detr_mean"] is not None else "—"
        lr_str = f"**{s['loss_ratio_mean']:.2f}x**" if s["loss_ratio_mean"] is not None else "—"
        rows_md.append(
            f"| P{s['phase_num']} | {s['name'].split(': ', 1)[-1]} | {s['n']} | "
            f"`{s['comb_start']:.2f} -> {s['comb_late']:.2f}` (**{s['comb_mean']:.2f} b**) | {detr_str} | "
            f"`{s['loss_start']:.0f} -> {s['loss_late']:.0f}` | {lr_str} | "
            f"`[{s['w8m_peak']}, {s['w8l_peak']}]` | `{s['w3_peak']}` | `{s['w8_nz']}` |"
        )

    w8_overall_pk = max(max(s["w8m_peak"], s["w8l_peak"]) for s in stats)
    warm_on_enobs = [s["comb_mean"] for s in stats if s["heater"] and s["regler"]]
    warm_max_loss = max(s["loss_mean"] for s in stats if s["heater"])
    cold_on_enob = stats[0]["comb_mean"]
    cold_on_loss = stats[0]["loss_mean"]
    cold_off_enob = stats[1]["comb_mean"]
    cold_off_loss = stats[1]["loss_mean"]

    tr = warm_metrics["trends"]
    md_path = DOCS_DIR / f"{args.title_prefix}.md"
    md_text = f"""# Inverted MAML Card 2 (`1k / 1k` = 50/50 Summing Attenuator, {args.heat_label}): R20 Thermal Bit-Slicing Report

**Hardware Target:** Card 2 (`Trion T120F324` Master SoC + `Trion T20F256` Coprocessor, **`1k / 1k` (50/50) Passive Summing Attenuator**)  
**Firmware:** `T120_SOC_ETH_FW v2.2-MAML (SW Build Nov 27 2026 20:52:38)`, `HW_LOGIC: 0x20261030`  
**Dataset:** [`FPGA_code/logs/bit_slicing/{json_path.name}`](../logs/bit_slicing/{json_path.name}) (`{len(hist):,}` pairs)  
**Dedicated Card 2 Storage:** `FPGA_code/releases/{args.rel_name}/reports_and_logs/`  
**DC Calibration (Cold):** [`FPGA_code/config/{dc_cal_path.name}`](../config/{dc_cal_path.name})  
**Hyperparameters:** `Heater = {args.heat_label}`, `K = {meta['k_batch']}`, `LR = {meta['lr']}`, `L2 = {meta['l2_reg']}`, `Momentum = {meta['momentum']}`, `Clamp = ±{meta['clamp_lsb']} LSB`  

---

## 1. Executive Summary & Physical 1k / 1k (50/50) Behavior

1. **50/50 Summing Junction Physics (`1k / 1k` vs. Card 1 `1k / 2.2k`):**  
   With matched $1.0\\text{{ k}}\\Omega / 1.0\\text{{ k}}\\Omega$ summing resistors, the primary `M33` payload and the `M8` compensation branch share **equal $0.500\\times$ ($-6.02\\text{{ dB}}$) summing authority** at `ADC_49` (compared to $0.6875\\times / 0.3125\\times$ on Card 1 `1k / 2.2k`).
2. **Cold Baseline (`P1–P2`):** `Cold / Regler ON` mean **{cold_on_enob:.2f} b** (loss `{cold_on_loss:,.0f} LSB²`), `Cold / Regler OFF` mean **{cold_off_enob:.2f} b** (loss `{cold_off_loss:,.0f} LSB²`).
3. **Thermal-Detrended Closed-Loop Performance:**  
   Weighted detrended `Warm ON` lift **`{tr['warm_step_lift_b']:+.2f} b`**, loss reduction ratio **`{tr['warm_loss_ratio']:.2f}x`**, detrended convergence climb **`{tr['hot_conv_climb_b']:+.2f} b`**, jitter **`{tr['jitter_std']:.2f} b`**, anti-windup recovery **`{tr['recovery_rate']:.2f}`**, composite score **`{warm_metrics['score']:+.3f}`**.
4. **Zero Clamp Saturation & High Headroom:**  
   Because `1k / 1k` provides $50\\%$ compensation authority, `W8` peaked at **`±{w8_overall_pk} LSB`** (well below the **`±{meta['clamp_lsb']} LSB`** anti-windup clamp), keeping warm `ON` precision at **`{min(warm_on_enobs):.2f}–{max(warm_on_enobs):.2f} b`** and max phase loss at **`{warm_max_loss:,.0f} LSB²`**.

---

## 2. Fresh Cold DC Calibration (`Card 2, 1k / 1k`)

- **MSB `alpha`:** `{alpha_msb}`
- **MSB `beta` (LSB):** `{beta_msb}`
- **LSB `alpha`:** `{alpha_lsb}`
- **LSB `beta` (LSB):** `{beta_lsb}`

---

## 3. Phase-by-Phase Telemetry (`P1–P14`)

| Phase | Regime | Pairs | Comb ENOB (`Start -> Late`, Mean) | Δ vs E_base | Total Loss (`Start -> Late`) | Loss Ratio | W8 Peak `[M, L]` | W3 Peak | W8 nz |
| :--- | :--- | ---: | :---: | :---: | :---: | :---: | :---: | :---: | ---: |
{chr(10).join(rows_md)}

---

## 4. Empirical Graphs: Performance Timeline & Full W(8) / W(3) Weights

![Card 2 1k/1k R20 Performance & Weight Envelope Timeline](figures/{tl_fig.name})

**Weight Coverage:** All **84 `W(8)`** (`7x6` MSB + `7x6` LSB) and **96 `W(3)`** (`8x6` MSB + `8x6` LSB) individual weights plotted across all `{len(hist):,}` pairs.

![Card 2 1k/1k R20 All W(8) and W(3) Weights](figures/{w_fig.name})
"""
    md_path.write_text(md_text)
    shutil.copy2(md_path, rel_dir / md_path.name)
    shutil.copy2(md_path, ARTIFACT_DIR / md_path.name)

    # Render clean PDF via ReportLab
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, HRFlowable, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors

    pdf_path = DOCS_DIR / f"{args.title_prefix}.pdf"
    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter, leftMargin=32, rightMargin=32, topMargin=32, bottomMargin=32)
    styles = getSampleStyleSheet()
    t_style = ParagraphStyle("T", parent=styles["Heading1"], fontSize=14, leading=18, textColor=colors.HexColor("#0d47a1"), spaceAfter=3)
    sub_style = ParagraphStyle("Sub", parent=styles["Normal"], fontSize=8.5, leading=11.5, textColor=colors.HexColor("#37474f"), spaceAfter=6)
    h2_style = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=10.5, leading=13, textColor=colors.HexColor("#1565c0"), spaceBefore=5, spaceAfter=4)
    b_style = ParagraphStyle("B", parent=styles["Normal"], fontSize=8.3, leading=11.5, textColor=colors.HexColor("#212121"))
    tc = ParagraphStyle("TC", parent=styles["Normal"], fontSize=7, leading=9, alignment=1)
    tcb = ParagraphStyle("TCB", parent=styles["Normal"], fontSize=7, leading=9, alignment=1, textColor=colors.HexColor("#0d47a1"), fontName="Helvetica-Bold")

    story = [
        Paragraph(f"Inverted MAML Card 2 (1k / 1k = 50/50, {args.heat_label}): R20 Thermal Bit-Slicing", t_style),
        Paragraph(
            f"Firmware: T120_SOC_ETH_FW v2.2-MAML (Build Nov 27 2026) | HW_LOGIC: 0x20261030 | "
            f"LR={meta['lr']}, L2={meta['l2_reg']}, Mom={meta['momentum']}, Clamp=±{meta['clamp_lsb']} LSB | {len(hist):,} Pairs",
            sub_style,
        ),
        HRFlowable(width="100%", thickness=1.2, color=colors.HexColor("#1565c0"), spaceAfter=6),
        Paragraph(
            f"<b>Summary:</b> With matched <b>1k / 1k (50/50)</b> summing resistors under <b>{args.heat_label}</b>, Card 2 gains 50% analog compensation authority. "
            f"Cold precision starts at <b>{cold_on_enob:.2f} b</b> (Loss {cold_on_loss:,.0f} LSB²). Under {args.heat_label} heating, active compensation holds <b>{min(warm_on_enobs):.2f}–{max(warm_on_enobs):.2f} b</b> "
            f"with W8 peaking at <b>±{w8_overall_pk} LSB</b> (inside ±{meta['clamp_lsb']} LSB clamp). Detrended lift: <b>{tr['warm_step_lift_b']:+.2f} b</b>, "
            f"loss ratio: <b>{tr['warm_loss_ratio']:.2f}x</b>, composite score: <b>{warm_metrics['score']:+.3f}</b>.",
            b_style,
        ),
        Spacer(1, 6),
        Paragraph("Phase-by-Phase Telemetry (P1–P14)", h2_style),
    ]

    tbl_rows = [[
        Paragraph(h, tcb) for h in
        ["Phase", "Regime", "N", "Comb ENOB (Mean)", "Δ E_base", "Loss (Start->Late)", "Ratio", "W8 Pk", "W3 Pk"]
    ]]
    for s in stats:
        tbl_rows.append([
            Paragraph(f"P{s['phase_num']}", tc),
            Paragraph(s["name"].split(": ", 1)[-1], tc),
            Paragraph(str(s["n"]), tc),
            Paragraph(f"{s['comb_start']:.2f}->{s['comb_late']:.2f} ({s['comb_mean']:.2f}b)", tc),
            Paragraph(f"{s['detr_mean']:+.2f}b" if s["detr_mean"] is not None else "—", tc),
            Paragraph(f"{s['loss_start']:.0f}->{s['loss_late']:.0f}", tc),
            Paragraph(f"{s['loss_ratio_mean']:.2f}x" if s["loss_ratio_mean"] is not None else "—", tc),
            Paragraph(f"[{s['w8m_peak']},{s['w8l_peak']}]", tc),
            Paragraph(str(s["w3_peak"]), tc),
        ])
    tbl = Table(tbl_rows, colWidths=[28, 118, 28, 102, 42, 82, 36, 46, 36])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e3f2fd")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#b0bec5")),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 8))
    story.append(Image(str(tl_fig), width=530, height=345))
    story.append(PageBreak())
    story.append(Paragraph("Full 180-Weight Dynamics: 84 W(8) & 96 W(3) Trajectories", h2_style))
    story.append(Image(str(w_fig), width=530, height=340))

    doc.build(story)
    shutil.copy2(pdf_path, rel_dir / pdf_path.name)
    shutil.copy2(pdf_path, ARTIFACT_DIR / pdf_path.name)

    print(f"[+] Saved Markdown: {md_path}")
    print(f"[+] Saved PDF     : {pdf_path}")
    print(f"[+] Storage Dir   : {rel_dir}")


if __name__ == "__main__":
    main()
