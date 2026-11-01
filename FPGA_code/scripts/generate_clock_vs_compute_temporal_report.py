#!/usr/bin/env python3
"""
generate_clock_vs_compute_temporal_report.py
============================================
Generates high-resolution figures and a formal PDF + Markdown report analyzing:
  1. Matrix 3 Temporal Clock Cells (Rows 6 & 7) across the FULL window (1.0 - 9.0 ms)
     and zoomed window (4.5 - 5.5 ms).
  2. Direct comparison against Regular Compute Cells (M3 Rows 0..2 and M33 Row 0).
  3. Matrix 8 Bias Row (Row 6) characterization across weights and time.
  4. Physical & mathematical explanation of how the analog network distinguishes
     decaying compute cells from temporal clock cells (Constant Carrier vs Data X,
     and S-curve AGC Gain Modulation vs Center Ramp).
"""

import os
import sys
import json
import shutil
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_PATH = REPO_ROOT / "FPGA_code" / "logs" / "m3_clock_characterization" / "full_temporal_clock_vs_compute_dataset.json"
FIG_DIR = REPO_ROOT / "FPGA_code" / "docs" / "figures"
DOC_DIR = REPO_ROOT / "FPGA_code" / "docs"
ARTIFACT_DIR = Path("/home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a")


def generate_figures(data: dict):
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    delays_ms = np.array(data["delays_us"], dtype=float) / 1000.0
    zoom_mask = (delays_ms >= 4.5) & (delays_ms <= 5.5)
    delays_zoom = delays_ms[zoom_mask]

    # Helper to extract mean across 6 columns for a given dict of {delay_str: [c0..c5]}
    def get_col_mean_and_std(d_dict, mode="pos"):
        sub = d_dict[mode]
        means, stds, per_col = [], [], []
        for d_us in data["delays_us"]:
            arr = np.array(sub[str(d_us)], dtype=float)
            means.append(float(np.mean(arr)))
            stds.append(float(np.std(arr)))
            per_col.append(arr)
        return np.array(means), np.array(stds), np.array(per_col)

    # =========================================================================
    # FIGURE 1: 4-Panel Comprehensive Overview (Full Window + Zoom + Compute vs Clock)
    # =========================================================================
    fig, axes = plt.subplots(2, 2, figsize=(16, 12), dpi=180)
    plt.subplots_adjust(hspace=0.32, wspace=0.25)

    weight_colors = {
        "-64": "#1f77b4",
        "-32": "#2ca02c",
        "-16": "#17becf",
        "0":   "#7f7f7f",
        "16":  "#ff7f0e",
        "32":  "#d62728",
        "64":  "#9467bd",
    }

    # --- Panel A: Full Window (1.0 - 9.0 ms) M3 Row 6 (Clock B1) across weights ---
    ax = axes[0, 0]
    ax.axvspan(4.5, 5.5, color="#ffeeba", alpha=0.45, label="Operativt Fönster (4.5–5.5 ms)")
    ax.axhline(0, color="black", linestyle="--", linewidth=1.2, label="S-Kurva Centrum (0 LSB)")
    for w_str in ["-64", "-32", "-16", "0", "16", "32", "64"]:
        if w_str in data["m3_clock_row6_weights"]:
            m, s, _ = get_col_mean_and_std(data["m3_clock_row6_weights"][w_str], "pos")
            ax.plot(delays_ms, m, marker="o", markersize=4, linewidth=2.0,
                    color=weight_colors[w_str], label=f"W = {int(w_str):+d} LSB")
    ax.set_title("A. Klockcell M3 Rad 6 (TRIM_B1) — Hela Fönstret [1.0 .. 9.0 ms]", fontsize=12, fontweight="bold")
    ax.set_xlabel("Tid efter Refresh t [ms]", fontsize=10)
    ax.set_ylabel("ADC_45 Utsignal (Medel Kol 0..5) [LSB]", fontsize=10)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(loc="upper right", fontsize=8, ncol=2)

    # --- Panel B: Zoomed Window (4.5 - 5.5 ms) M3 Row 6 (Clock B1) ---
    ax = axes[0, 1]
    ax.axhline(0, color="black", linestyle="--", linewidth=1.5, label="S-Kurva Centrum (0 LSB)")
    ax.axhspan(-100, 100, color="#d4edda", alpha=0.35, label="Optimalt Linjärt Cirkelområde (±100 LSB)")
    for w_str in ["-64", "-32", "-16", "0", "16", "32", "64"]:
        if w_str in data["m3_clock_row6_weights"]:
            m, s, _ = get_col_mean_and_std(data["m3_clock_row6_weights"][w_str], "pos")
            m_z = m[zoom_mask]
            slope = m_z[-1] - m_z[0]
            ax.plot(delays_zoom, m_z, marker="s", markersize=5, linewidth=2.2,
                    color=weight_colors[w_str], label=f"W={int(w_str):+d} (5ms: {m_z[delays_zoom==5.0][0]:.0f} LSB, Δ={slope:+.0f})")
    ax.set_title("B. Inzoomat Operativt Fönster [4.5 .. 5.5 ms] (100 µs steg)", fontsize=12, fontweight="bold")
    ax.set_xlabel("Tid efter Refresh t [ms]", fontsize=10)
    ax.set_ylabel("ADC_45 Utsignal [LSB]", fontsize=10)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(loc="upper right", fontsize=8)

    # --- Panel C: Direct Decay Comparison: Clock Cells vs Regular Compute Cells (1.0 - 9.0 ms) ---
    ax = axes[1, 0]
    ax.axvspan(4.5, 5.5, color="#ffeeba", alpha=0.45, label="4.5–5.5 ms Fönster")
    ax.axhline(0, color="black", linestyle="--", linewidth=1.0)

    # Clock Row 6 @ W=+32
    m_clk6, _, _ = get_col_mean_and_std(data["m3_clock_row6_weights"]["32"], "pos")
    ax.plot(delays_ms, m_clk6, "-o", color="#d62728", linewidth=2.5, markersize=5,
            label="Klockcell M3 Rad 6 (W=+32, Konstant Ref +64)")

    # Clock Row 7 @ W=+32
    m_clk7, _, _ = get_col_mean_and_std(data["m3_clock_row7_weights"]["32"], "pos")
    ax.plot(delays_ms, m_clk7, "-s", color="#9467bd", linewidth=2.2, markersize=4,
            label="Klockcell M3 Rad 7 (W=+32, Konstant Ref +64)")

    # Compute Rows 0, 1, 2 @ W=+32 (when X = +64 vs X = -64 vs X = 0)
    comp_colors = ["#1f77b4", "#2ca02c", "#ff7f0e"]
    for idx, r_idx in enumerate([0, 1, 2]):
        r_key = f"row_{r_idx}"
        if r_key in data["m3_compute_rows_w32"]:
            m_pos, _, _ = get_col_mean_and_std(data["m3_compute_rows_w32"][r_key], "pos")
            m_neg, _, _ = get_col_mean_and_std(data["m3_compute_rows_w32"][r_key], "neg")
            ax.plot(delays_ms, m_pos, "--^", color=comp_colors[idx], linewidth=1.8, markersize=4,
                    label=f"Vanlig Cell M3 Rad {r_idx} (W=+32, Data X=+64)")
            if idx == 0:
                ax.plot(delays_ms, m_neg, ":v", color=comp_colors[idx], linewidth=1.8, markersize=4,
                        label=f"Vanlig Cell M3 Rad {r_idx} (W=+32, Data X=-64)")

    ax.set_title("C. Jämförelse: Klockceller vs. Vanliga Beräkningsceller [1.0 .. 9.0 ms]", fontsize=12, fontweight="bold")
    ax.set_xlabel("Tid efter Refresh t [ms]", fontsize=10)
    ax.set_ylabel("ADC_45 Utsignal [LSB]", fontsize=10)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(loc="upper right", fontsize=8)

    # --- Panel D: Matrix 8 Bias Row 6 & M33 Primary Compute Decay on ADC_49 ---
    ax = axes[1, 1]
    ax.axvspan(4.5, 5.5, color="#ffeeba", alpha=0.45, label="4.5–5.5 ms Fönster")
    ax.axhline(0, color="black", linestyle="--", linewidth=1.2, label="ADC_49 Centrum (0 LSB)")
    for w_str in ["-64", "-32", "0", "32", "64"]:
        if w_str in data["m8_bias_row6_weights"]:
            m_b, _, _ = get_col_mean_and_std(data["m8_bias_row6_weights"][w_str], "pos")
            ax.plot(delays_ms, m_b, "-o", markersize=4, linewidth=1.8,
                    color=weight_colors[w_str], label=f"M8 Bias Rad 6 (W={int(w_str):+d} LSB)")

    # M33 Compute Row 0 on ADC_49
    m33_pos, _, _ = get_col_mean_and_std(data["m33_compute_row0_w32"], "pos")
    ax.plot(delays_ms, m33_pos, "--d", color="black", linewidth=2.2, markersize=5,
            label="M33 Primär Beräkning Rad 0 (W=+32, X=+64)")

    ax.set_title("D. Matris 8 Bias-Rad 6 & Matris 33 på ADC_49 [1.0 .. 9.0 ms]", fontsize=12, fontweight="bold")
    ax.set_xlabel("Tid efter Refresh t [ms]", fontsize=10)
    ax.set_ylabel("ADC_49 Utsignal [LSB]", fontsize=10)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(loc="upper right", fontsize=8)

    fig.suptitle(
        "INVERTED MAML (SE 2630397-4): Temporala Klockceller, Vanliga Beräkningsceller & Bias-Celler (1.0 – 9.0 ms)",
        fontsize=14, fontweight="bold", y=0.98
    )
    fig1_path = FIG_DIR / "fig_m3_clock_vs_compute_full_window.png"
    fig.savefig(fig1_path, bbox_inches="tight")
    plt.close(fig)

    # =========================================================================
    # FIGURE 2: Per-Column (Cols 0..5) Zoom in [4.5 .. 5.5 ms] & Optimal Centering
    # =========================================================================
    fig2, axes2 = plt.subplots(2, 3, figsize=(16, 9.5), dpi=180)
    plt.subplots_adjust(hspace=0.36, wspace=0.28)

    optimal_w_per_col = []
    for c in range(6):
        ax = axes2[c // 3, c % 3]
        ax.axhline(0, color="black", linestyle="--", linewidth=1.3, label="Centrum (0 LSB)")
        ax.axhspan(-80, 80, color="#d4edda", alpha=0.35)

        w_vals = [-64, -32, -16, 0, 16, 32, 64]
        v_at_5ms = []
        for w_int in w_vals:
            w_str = str(w_int)
            _, _, per_col = get_col_mean_and_std(data["m3_clock_row6_weights"][w_str], "pos")
            col_curve = per_col[zoom_mask, c]
            val_5ms = col_curve[delays_zoom == 5.0][0]
            v_at_5ms.append(val_5ms)
            ax.plot(delays_zoom, col_curve, "-o", markersize=4, linewidth=1.8,
                    color=weight_colors[w_str], label=f"W={w_int:+d} ({val_5ms:+.0f}@5ms)")

        # Also plot Compute Row 0 for this column in [4.5..5.5 ms]
        _, _, comp_per_col = get_col_mean_and_std(data["m3_compute_rows_w32"]["row_0"], "pos")
        ax.plot(delays_zoom, comp_per_col[zoom_mask, c], "--^", color="#1f77b4", linewidth=2.0,
                alpha=0.7, label="Vanlig Rad 0 (W=+32, X=+64)")

        # Find weight that places 5.0 ms closest to 0 LSB
        best_idx = int(np.argmin(np.abs(v_at_5ms)))
        optimal_w_per_col.append((w_vals[best_idx], v_at_5ms[best_idx]))

        ax.set_title(f"Kolumn {c}: Klockrad 6 vs. Datarad 0 [4.5–5.5 ms]", fontsize=9.8, fontweight="bold")
        ax.set_xlabel("Tid t [ms]", fontsize=9)
        ax.set_ylabel("ADC_45 [LSB]", fontsize=9)
        ax.grid(True, linestyle=":", alpha=0.6)
        if c == 0:
            ax.legend(loc="best", fontsize=7, ncol=2)

    fig2.suptitle(
        "Kolumn-för-Kolumn Analys [4.5 .. 5.5 ms]: Klockcell Rad 6 vid olika vikter W vs. Vanlig Beräkningscell",
        fontsize=13, fontweight="bold", y=0.98
    )
    fig2_path = FIG_DIR / "fig_m3_clock_per_column_4p5to5p5ms.png"
    fig2.savefig(fig2_path, bbox_inches="tight")
    plt.close(fig2)

    # Copy figures to artifact directory
    if ARTIFACT_DIR.exists():
        shutil.copy2(fig1_path, ARTIFACT_DIR / fig1_path.name)
        shutil.copy2(fig2_path, ARTIFACT_DIR / fig2_path.name)

    return fig1_path, fig2_path, optimal_w_per_col


def generate_pdf_and_md(data: dict, fig1_path: Path, fig2_path: Path, optimal_w_per_col):
    delays_us = data["delays_us"]

    def get_mean_at(d_dict, dly_us, mode="pos"):
        return float(np.mean(d_dict[mode][str(dly_us)]))

    # Extract summary table rows
    clk6_w32 = data["m3_clock_row6_weights"]["32"]
    clk6_w16 = data["m3_clock_row6_weights"]["16"]
    clk6_w0  = data["m3_clock_row6_weights"]["0"]
    clk6_wm16 = data["m3_clock_row6_weights"]["-16"]
    clk7_w32 = data["m3_clock_row7_weights"]["32"]
    comp0_w32 = data["m3_compute_rows_w32"]["row_0"]
    comp1_w32 = data["m3_compute_rows_w32"]["row_1"]
    m33_r0_w32 = data["m33_compute_row0_w32"]
    m8_bias_w0 = data["m8_bias_row6_weights"]["0"]
    m8_bias_w32 = data["m8_bias_row6_weights"]["32"]

    # Build Markdown Report
    md_path = DOC_DIR / "M3_TEMPORAL_CLOCK_AND_BIAS_CHARACTERIZATION_REPORT.md"
    pdf_path = DOC_DIR / "M3_TEMPORAL_CLOCK_AND_BIAS_CHARACTERIZATION_REPORT.pdf"

    rows_summary = [
        ("Klockcell M3 Rad 6 (W=+32)", clk6_w32, "pos", "ADC_45"),
        ("Klockcell M3 Rad 6 (W=+16)", clk6_w16, "pos", "ADC_45"),
        ("Klockcell M3 Rad 6 (W=0)",   clk6_w0,  "pos", "ADC_45"),
        ("Klockcell M3 Rad 6 (W=-16)", clk6_wm16,"pos", "ADC_45"),
        ("Klockcell M3 Rad 7 (W=+32)", clk7_w32, "pos", "ADC_45"),
        ("Vanlig Cell M3 Rad 0 (W=+32, X=+64)", comp0_w32, "pos", "ADC_45"),
        ("Vanlig Cell M3 Rad 0 (W=+32, X=-64)", comp0_w32, "neg", "ADC_45"),
        ("Vanlig Cell M3 Rad 1 (W=+32, X=+64)", comp1_w32, "pos", "ADC_45"),
        ("Primär Cell M33 Rad 0 (W=+32, X=+64)", m33_r0_w32, "pos", "ADC_49"),
        ("Bias-Cell M8 Rad 6 (W=0)",   m8_bias_w0, "pos", "ADC_49"),
        ("Bias-Cell M8 Rad 6 (W=+32)", m8_bias_w32, "pos", "ADC_49"),
    ]

    md_lines = [
        "# Inverted MAML: Karakteriseringsrapport för Klockceller, Vanliga Beräkningsceller & Bias-Celler (1.0 – 9.0 ms & 4.5 – 5.5 ms)",
        "**Patent Pending SE 2630397-4 | Milstolpe 3: Temporal Kompensation & S-Kurva Kalibrering**  ",
        "**Hårdvara:** Efinix Trion T120 Master SoC (`192.168.1.50:5000`, PCB v1.3.2)  ",
        "**Datum:** 2026-10-31  ",
        "",
        "---",
        "",
        "## 1. Huvudfrågan: Hur kan vi och nätverket skilja på Klockcellerna och de Vanliga Cellerna när båda dalar över tid?",
        "",
        "Detta är den mest centrala fysikaliska frågan i hela Milstolpe 3: **Eftersom även de vanliga beräkningscellerna (Rad 0..5) har kondensatorer som laddas ur över tid, hur kan kompensationsnätverket veta vad som är *tid* och vad som är *data*?**",
        "",
        "Svaret ligger i **tre fundamentala fysikaliska och matematiska mekanismer** i kretsen:",
        "",
        "### Mekanism 1: Konstant Likspänningsreferens ($V_{\\text{ref}}$) vs. Stokastisk Datavektor ($X$)",
        "- **De vanliga beräkningscellerna (Rad 0..5):** Matas med den varierande datavektorn $X_i \\in [-127, +127]$.",
        "  - När $X_i = +64$, är strömmen positiv och dalar *uppifrån och ned*.",
        "  - När $X_i = -64$, byter strömmen tecken och dalar *underifrån och upp* (se tabellen nedan!).",
        "  - När $X_i = 0$, är utströmmen $0\\text{ LSB}$ oavsett vad klockan är.",
        "  - **Konsekvens:** En vanlig beräkningscell kan **aldrig** ge en entydig tidssignal, eftersom en utsignal på t.ex. $+100\\text{ LSB}$ lika gärna kan betyda *\"hög insignal sent i cykeln ($5.5\\text{ ms}$)\"* som *\"låg insignal tidigt i cykeln ($4.5\\text{ ms}$)\"*.",
        "- **Klockcellerna (Rad 6 & 7 i Matris 3):** Matas med en **100 % konstant, känd likspänningsreferens ($V_{\\text{ref}}$)** som är helt oberoende av datavektorn $X$.",
        "  - Därför är klockcellens ström $I_{\\text{clock}}(t) = G(V_{\\text{gate}}(t)) \\cdot V_{\\text{ref}}$ en **entydig, deterministisk funktion av tiden $t$** i varje 10 ms-period!",
        "",
        "### Mekanism 2: Hur Sigmoid 4 kombinerar Klocka och Data (Tidsstyrd Gain-kontroll / AGC)",
        "I varje kolumn av Matris 3 summeras strömmen från de 6 beräkningsraderna med strömmen från klockraderna *innan* den olinjära Sigmoid 4 ($ADC_{45}$):",
        "$$ADC_{45, c}(t) = \\sigma_4\\!\\left( \\sum_{r=0}^{5} W_3[r,c](t) \\cdot X_r + I_{\\text{clock}, c}(t) \\right)$$",
        "Genom Taylorutveckling kring klockcellens arbetspunkt $I_{\\text{clock}}(t)$ får vi:",
        "$$ADC_{45, c}(t) \\approx \\underbrace{\\sigma_4\\big(I_{\\text{clock}}(t)\\big)}_{\\text{1. Additiv Tidsramp}} + \\underbrace{\\sigma_4'\\big(I_{\\text{clock}}(t)\\big)}_{\\text{2. Tidsstyrd Lutning (AGC!)}} \\cdot \\left(\\sum_{r=0}^{5} W_3[r,c](t) \\cdot X_r\\right)$$",
        "",
        "Här ser vi två samverkande effekter beroende på var på S-kurvan vi lägger klockcellen:",
        "1. **Om klockcellen läggs i Centrum på S-kurvan ($0\\text{ LSB}$ vid $5.0\\text{ ms}$):**",
        "   - Term 1 ($\\sigma_4(I_{\\text{clock}}(t))$) sveper linjärt från $+\\Delta V$ vid $4.5\\text{ ms}$ genom $0$ vid $5.0\\text{ ms}$ till $-\\Delta V$ vid $5.5\\text{ ms}$. Detta ger Matris 8 en ren tidsramp som släcker ut all tidsberoende DC-offsetdrift i $M_{33}$.",
        "2. **Om klockcellen glider genom S-böjen (knät på S-kurvan där $\\sigma_4'' \\neq 0$):**",
        "   - Term 2 ($\\sigma_4'(I_{\\text{clock}}(t))$) ändrar **lutningen (förstärkningen)** för datasignalen $\\sum W_3 X_r$ som funktion av tiden $t$!",
        "   - Eftersom $M_{33}$ tappar förstärkning multiplikativt med $X$ över tid ($Y_{33}(t) = W_{33}(t) \\cdot X$), fungerar klockcellen i Sigmoid 4 som en **automatisk tidsstyrd förstärkningskontroll (AGC)** som skruvar upp eller ner kompensationsförstärkningen av $X$ exakt i takt med att $M_{33}$-kondensatorerna laddas ur!",
        "",
        "### Mekanism 3: Ortogonal Hadamard-separation under inlärning",
        "Under Hadamard-gradientmätningen har varje rad i Matris 3 (inklusive Rad 6 & 7 när masken `0x00FF` aktiveras) sin egen ortogonala Walsh-kod i $H_{16}$. Vid FWHT-demodulering separeras $\\partial ADC_{45} / \\partial W_3[6,c]$ med **exakt noll överhörning** från $\\partial ADC_{45} / \\partial W_3[0..5,c]$.",
        "",
        "---",
        "",
        "## 2. Uppmätt Hårdvarutabell över Tid (1.0 ms till 9.0 ms)",
        "",
        "| Cell / Konfiguration | ADC | 2.0 ms | 4.0 ms | **4.5 ms** | **5.0 ms** | **5.5 ms** | 7.0 ms | 9.0 ms | **Sving (4.5–5.5 ms)** |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]

    table_data_pdf = [
        ["Cell / Konfiguration", "ADC", "2.0ms", "4.0ms", "4.5ms", "5.0ms", "5.5ms", "7.0ms", "9.0ms", "Δ(4.5-5.5)"]
    ]

    for label, d_obj, mode, adc_lbl in rows_summary:
        v20 = get_mean_at(d_obj, 2000, mode)
        v40 = get_mean_at(d_obj, 4000, mode)
        v45 = get_mean_at(d_obj, 4500, mode)
        v50 = get_mean_at(d_obj, 5000, mode)
        v55 = get_mean_at(d_obj, 5500, mode)
        v70 = get_mean_at(d_obj, 7000, mode)
        v90 = get_mean_at(d_obj, 9000, mode)
        sw  = v45 - v55
        md_lines.append(
            f"| **{label}** | `{adc_lbl}` | {v20:+.1f} | {v40:+.1f} | **{v45:+.1f}** | **{v50:+.1f}** | **{v55:+.1f}** | {v70:+.1f} | {v90:+.1f} | **{sw:+.1f} LSB** |"
        )
        table_data_pdf.append([
            label, adc_lbl, f"{v20:+.0f}", f"{v40:+.0f}", f"{v45:+.0f}",
            f"{v50:+.0f}", f"{v55:+.0f}", f"{v70:+.0f}", f"{v90:+.0f}", f"{sw:+.1f}"
        ])

    md_lines.extend([
        "",
        "---",
        "",
        "## 3. Grafisk Analys: Hela Fönstret [1.0 – 9.0 ms] & Inzoomat [4.5 – 5.5 ms]",
        "",
        f"![Översikt Klockceller vs Beräkningsceller](file://{ARTIFACT_DIR / fig1_path.name})",
        "",
        "### Viktiga observationer från Figur 1:",
        "1. **Panel A (Hela fönstret 1.0–9.0 ms):** Vid $1.0 - 2.0\\text{ ms}$ håller RC-filtret och ColTIA fortfarande på att svänga in efter kolumn-refreshen. Toppen nås vid $\\approx 4.0\\text{ ms}$, varefter den rena exponentiella urladdningen dominerar hela vägen från $4.0\\text{ ms}$ ner till $9.0\\text{ ms}$.",
        "2. **Panel B (Inzoomat 4.5–5.5 ms med 100 µs upplösning):** Inuti fönstret $4.5 - 5.5\\text{ ms}$ är urladdningskurvan **nästan perfekt linjär**!",
        "   - Vid $W = +32\\text{ LSB}$ ligger kurvan högt ($+310\\text{ LSB}$) med tydlig lutning.",
        "   - Vid $W = 0\\text{ LSB}$ ligger kurvan nära mitten ($0\\text{ LSB}$).",
        "   - Genom att välja vikt mellan $W = -16$ och $W = +16$ kan vi placera klockcellen exakt där vi vill ha den i S-kurvan!",
        "3. **Panel C (Klockcell vs. Vanlig Beräkningscell):**",
        "   - Den vanliga beräkningscellen (Rad 0, blå streckad) vid $X = +64$ dalar med ungefär samma form som klockcellen, **men** när insignalen byter tecken till $X = -64$ (blå prickad) **speglas hela kurvan upp-och-ner till negativa värden**!",
        "   - Klockcellen (röd heldragen) ligger däremot alltid fast på sin deterministiska tidsbana, oavsett vad datavektorn $X$ innehåller.",
        "",
        "---",
        "",
        "## 4. Kolumn-för-Kolumn Kalibrering [4.5 – 5.5 ms] & Smart 8-Raders Baslinje",
        "",
        f"![Kolumn-för-kolumn Klockceller](file://{ARTIFACT_DIR / fig2_path.name})",
        "",
        f"![Smart 8-Raders Kalibrering](file://{ARTIFACT_DIR / 'fig_smart_m3_all_8rows_calibration.png'})",
        "",
        "### Kritisk Upptäckt på `v2.2-MAML`: Kolumn 4 Fold-Over vid $W_3[6, 4] \\ge +32\\text{ LSB}$",
        "- På verifierad `v2.2-MAML`-hårdvara ser vi i `fig_smart_m3_all_8rows_calibration.png` att om Klockrad 6 (`TRIM_B1`) sätts till $+32$ eller $+48\\text{ LSB}$ i **Kolumn 4**, bottnar BJT-transistorn i Sigmoid 4 vid $+638\\text{ LSB}$ och **vänder tecken på tidsderivatan till $-307\\text{ LSB}$** (fold-over)!",
        "- Vid **$W = \\pm 16\\text{ LSB}$** hålls däremot **samtliga 6 kolumner** (inklusive Kolumn 4) strikt monotona i S-böjen ($\\pm 100\\text{ till }\\pm 280\\text{ LSB}$ vid $5.0\\text{ ms}$) med en ren linjär tidsramp på **$+85\\text{ LSB}$** (vid $W=+16$) respektive **$-91\\text{ LSB}$** (vid $W=-16$) över $[4.5, 5.5]\\text{ ms}$.",
        "",
        "---",
        "",
        "## 5. Slutsats: Smart Baslinje för Alla 8 Rader (Steg 1: Fixerad, Steg 2: Dynamisk Nödåtgärd)",
        "",
        "1. **Steg 1A — Vanliga Beräkningsrader (M3 Rad 0..5): Balanserad Noll-Summa med Stark Diagonal:**",
        "   - Varje kolumn får en stark diagonalvikt ($\\pm 24\\text{ LSB}$ i kolumnens bästa lutningspolaritet) kombinerat med alternerande off-diagonalvikter ($\\pm 12\\text{ LSB}$) vars radsumma tar ut varandra.",
        "   - Detta laddar upp alla 36 kondensatorer i det linjära triodområdet, samtidigt som korrelerad common-mode-ström ($\\rho = 0.85$) tar ut sig själv i ColTIA-knutpunkten så att Sigmoid 4 aldrig bottnar!",
        "2. **Steg 1B — Fixerade Klockrader (M3 Rad 6 & Rad 7) i S-böjen utan Fold-Over:**",
        "   - **Rad 6 (`TRIM_B1`, $330\\text{ k}\\Omega$ snabb klocka):** Fixeras på $W = \\pm 16\\text{ LSB}$ per kolumn (inuti den aktiva S-böjen där den ger både tidsramp och tidsstyrd AGC-lutning $\\sigma_4'(t)$, med god marginal till Kolumn 4:s fold-over).",
        "   - **Rad 7 (`TRIM_REF`, Referens):** Fixeras som kolumnvis DC-motvikt ($W \\in [-16, +16]\\text{ LSB}$) för att centrera vilopunkten nära S-kurvans mitt vid $5.0\\text{ ms}$.",
        "3. **Steg 1C — Fixerad Bias-Rad i Matris 8 (M8 Rad 6):**",
        "   - Fixeras så att utgångssigmoiden (`ADC_49`) centreras i S-kurvans mitt vid $5.0\\text{ ms}$, medan `M8 Rad 0..5` startar med balanserade diagonalvikter ($\\pm 24\\text{ LSB}$).",
        "4. **Steg 2 — Dynamisk Träning av Klock- & Bias-rader (Nödåtgärd vid behov):**",
        "   - I Steg 1 håller vi Rad 6/7 i M3 och Rad 6 i M8 **fixerade** på sina kalibrerade arbetspunkter (Hadamard-mask `0x003F` / `0x3F00`) så att de vanliga beräkningsraderna lär sig utnyttja den fasta tidsreferensen.",
        "   - Om vi i Steg 2 behöver finjustera klock- och bias-raderna dynamiskt under gång, aktiverar vi enkelt bit 6 & 7 i Hadamard-masken (`0x00FF` / `0x7F00`).",
    ])

    with open(md_path, "w") as f:
        f.write("\n".join(md_lines) + "\n")

    if ARTIFACT_DIR.exists():
        shutil.copy2(md_path, ARTIFACT_DIR / md_path.name)

    # =========================================================================
    # Build PDF Report with ReportLab
    # =========================================================================
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DocTitle", parent=styles["Title"], fontSize=15, leading=19, textColor=colors.HexColor("#1a252f"), spaceAfter=4
    )
    sub_style = ParagraphStyle(
        "DocSub", parent=styles["Normal"], fontSize=9.5, leading=13, textColor=colors.HexColor("#555555"), spaceAfter=10
    )
    h1_style = ParagraphStyle(
        "H1", parent=styles["Heading2"], fontSize=12, leading=15, textColor=colors.HexColor("#1a5276"), spaceBefore=8, spaceAfter=4
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"], fontSize=9.2, leading=13, spaceAfter=5
    )
    bullet_style = ParagraphStyle(
        "Bullet", parent=body_style, leftIndent=12, spaceAfter=4
    )

    story = []
    story.append(Paragraph(
        "Inverted MAML: Karakterisering av Temporala Klockceller, Beräkningsceller & Bias-Celler (1.0 – 9.0 ms & 4.5 – 5.5 ms)",
        title_style
    ))
    story.append(Paragraph(
        "<b>Patent Pending SE 2630397-4</b> | Milstolpe 3: Hur nätverket särskiljer tid från data | Hårdvara: Trion T120 SoC (192.168.1.50)",
        sub_style
    ))

    story.append(Paragraph("1. Hur särskiljer kretsen Klockceller från Vanliga Beräkningsceller?", h1_style))
    story.append(Paragraph(
        "Eftersom både de vanliga beräkningscellerna (Rad 0..5) och klockcellerna (Rad 6..7) i Matris 3 består av 2T1C-kondensatorer som laddas ur över tid, uppstår den kritiska frågan: <b>Hur vet kompensationsnätverket vad som är tid (klocka) och vad som är insignal (data)?</b> Fysiken i kretsen löser detta genom tre distinkta mekanismer:",
        body_style
    ))
    story.append(Paragraph(
        "• <b>1. Konstant Referens (V_ref) vs. Stokastisk Data (X):</b> De vanliga beräkningscellerna multiplicerar sin kondensatorladdning med datavektorn X_i. När X_i = +64 dalar strömmen uppifrån (+300 -> +150 LSB), men när X_i = -64 byter hela kurvan tecken och dalar underifrån (-300 -> -150 LSB), och vid X_i = 0 är strömmen 0 LSB. En vanlig cell har därför <i>noll entydig tidsinformation</i>. Klockcellerna (Rad 6 & 7) matas däremot med en <b>konstant, känd likspänning (V_ref)</b> som är 100 % oberoende av X. Därför ger klockcellen alltid exakt samma deterministiska spänningsramp som funktion av tiden t i varje 10 ms-cykel.",
        bullet_style
    ))
    story.append(Paragraph(
        "• <b>2. Sigmoid 4 som Tidsstyrd Förstärkningskontroll (AGC) i S-böjen:</b> I Matris 3 summeras strömmen från beräkningsraderna med strömmen från klockraden in i den olinjära Sigmoid 4 (ADC_45): <i>ADC_45(t) ≈ σ_4(I_clock(t)) + σ_4'(I_clock(t)) · (W_3 · X)</i>. Den första termen <i>σ_4(I_clock(t))</i> ger en ren additiv tidsramp (starkast i S-kurvans centrum) som kompenserar DC-drift. Den andra termen <i>σ_4'(I_clock(t))</i> är S-kurvans lutning vid klockcellens arbetspunkt. När klockcellen glider genom S-böjen ändras lutningen <i>σ_4'</i> över tid, vilket <b>multiplicerar datasignalen X med tiden t</b> och därmed kompenserar att M33 tappar förstärkning över tid!",
        bullet_style
    ))
    story.append(Paragraph(
        "• <b>3. Ortogonal Hadamard-demodulering:</b> Under inlärning har klockraderna egna Walsh-Hadamard-koder i H_16, vilket separerar deras partiella derivator med 0 % överhörning från beräkningsraderna.",
        bullet_style
    ))

    story.append(Paragraph("2. Empirisk Hårdvarutabell: Hela Fönstret [1.0 .. 9.0 ms] & Sving [4.5 .. 5.5 ms]", h1_style))
    t = Table(table_data_pdf, colWidths=[54*mm, 14*mm, 14*mm, 14*mm, 15*mm, 15*mm, 15*mm, 14*mm, 14*mm, 18*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a5276")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f6f7")]),
        ("BACKGROUND", (4, 1), (6, -1), colors.HexColor("#fef9e7")),
    ]))
    story.append(t)
    story.append(Spacer(1, 4 * mm))

    story.append(Image(str(fig1_path), width=178 * mm, height=133 * mm))
    story.append(PageBreak())

    story.append(Paragraph("3. Kolumn-för-Kolumn Karakterisering i Operativa Fönstret [4.5 .. 5.5 ms]", h1_style))
    story.append(Paragraph(
        "Grafen nedan visar för var och en av de 6 kolumnerna hur Klockcell Rad 6 (TRIM_B1) beter sig vid olika vikter W ∈ [-64 .. +64] LSB med 100 µs tidsupplösning mellan 4.5 ms och 5.5 ms, jämfört med en vanlig beräkningscell (Rad 0).",
        body_style
    ))
    story.append(Image(str(fig2_path), width=178 * mm, height=106 * mm))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("4. Smart 8-Raders Kalibrering för 4.5 – 5.5 ms (Steg 1: Fixerad, Steg 2: Dynamisk)", h1_style))
    story.append(Paragraph(
        "1. <b>Kritisk Upptäckt på v2.2-MAML (Kolumn 4 Fold-Over):</b> Vid W >= +32 LSB på Klockrad 6 (TRIM_B1) bottnar BJT-transistorn i Kolumn 4 av Sigmoid 4 vid +638 LSB och vänder tidsderivatan till -307 LSB! Vid <b>W = ±16 LSB</b> ligger däremot alla 6 kolumner rent i den monotona S-böjen med ~85–91 LSB linjärt tids-sving mellan 4.5 och 5.5 ms.<br/>"
        "2. <b>Steg 1A — Beräkningsrader (M3 Rad 0..5):</b> Balanserad noll-summa per kolumn (stark diagonal ±24 LSB, alternerande ±12 LSB off-diagonal) som laddar alla kondensatorer i det linjära området utan att mätta Sigmoid 4 vid korrelerad insignal.<br/>"
        "3. <b>Steg 1B — Fixerade Klock- & Bias-rader:</b> M3 Rad 6 (TRIM_B1) fixeras vid W = ±16 LSB i S-böjen (tidsramp + AGC-lutning), medan M3 Rad 7 (TRIM_REF) och M8 Rad 6 (Bias) centrerar vilopunkten vid 5.0 ms.<br/>"
        "4. <b>Steg 2 — Dynamisk Nödåtgärd (vid behov):</b> Om fixerade referens-/biasceller slår i taket kan vi i Steg 2 aktivera Hadamard-mask 0x00FF / 0x7F00 för att låta hårdvaran finjustera dem dynamiskt.",
        body_style
    ))
    fig3_path = FIG_DIR / "fig_smart_m3_all_8rows_calibration.png"
    if fig3_path.exists():
        story.append(Spacer(1, 3 * mm))
        story.append(Image(str(fig3_path), width=178 * mm, height=82 * mm))

    doc.build(story)
    if ARTIFACT_DIR.exists():
        shutil.copy2(pdf_path, ARTIFACT_DIR / pdf_path.name)

    return md_path, pdf_path


def main():
    if not DATA_PATH.exists():
        print(f"[!] Dataset not found at {DATA_PATH}")
        sys.exit(1)
    with open(DATA_PATH, "r") as f:
        data = json.load(f)
    fig1_path, fig2_path, opt_w = generate_figures(data)
    md_path, pdf_path = generate_pdf_and_md(data, fig1_path, fig2_path, opt_w)
    print(f"[+] Generated Figure 1: {fig1_path}")
    print(f"[+] Generated Figure 2: {fig2_path}")
    print(f"[+] Generated Markdown Report: {md_path}")
    print(f"[+] Generated PDF Report: {pdf_path}")


if __name__ == "__main__":
    main()

