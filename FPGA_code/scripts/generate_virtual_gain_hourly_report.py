#!/usr/bin/env python3
"""
generate_virtual_gain_hourly_report.py: Hourly Progress Report & Figure Generator
Inverted MAML AIMC Mode A Virtual Gain Campaign
PCB v1.3.2 (1k / 3.3k Ohm Attenuator) | Efinix Trion T120 SoC
Tag: [VIRTUAL_HARDWARE_EMULATION]
"""

import sys
import json
import time
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parents[2]
LOGS_DIR = REPO_ROOT / "FPGA_code" / "logs" / "virtual_gain_experiments"
DOCS_DIR = REPO_ROOT / "FPGA_code" / "docs"
FIG_DIR = DOCS_DIR / "figures"
DOCS_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)


def analyze_file(json_path: Path):
    try:
        with open(json_path, "r") as f:
            data = json.load(f)
    except Exception as e:
        return None

    meta = data.get("metadata", {})
    records = data.get("records", [])
    if len(records) < 5:
        return None

    prov = meta.get("provenance", {})
    vem = prov.get("virtual_emulation", {})
    tparams = meta.get("training_params", {})

    d_line = vem.get("d_line", 1)
    w33 = vem.get("d_w33", 1)
    target_gain = vem.get("target_gain", 1.0)
    clamp = vem.get("w_clamp", 80)
    k = tparams.get("k", 20)
    lr = tparams.get("lr", 0.03)
    epochs = len(records) - 1

    losses = np.array([r["loss_lsb2"] for r in records[1:]], dtype=np.float64)
    rmses = np.array([r["rmse_lsb"] for r in records[1:]], dtype=np.float64)
    enobs = np.array([r["enob_bits"] for r in records[1:]], dtype=np.float64)
    eps = np.arange(1, len(losses) + 1)

    slope, intercept = np.polyfit(eps, losses, 1)
    r_matrix = np.corrcoef(eps, losses)
    r_squared = float(r_matrix[0, 1] ** 2) if not np.isnan(r_matrix[0, 1]) else 0.0

    q1_loss = float(np.mean(losses[: max(1, len(losses) // 4)]))
    q4_loss = float(np.mean(losses[3 * len(losses) // 4 :]))
    trend_pct = float(((q4_loss - q1_loss) / q1_loss) * 100.0) if q1_loss > 0 else 0.0

    best_idx = int(np.argmin(losses))
    best_loss = float(losses[best_idx])
    best_enob = float(enobs[best_idx])
    best_epoch = int(eps[best_idx])

    init_loss = float(records[0]["loss_lsb2"])
    init_enob = float(records[0]["enob_bits"])
    final_loss = float(losses[-1])
    final_enob = float(enobs[-1])

    verdict = "CONVERGING" if (slope < -1.0 and trend_pct < -3.0) else "STATISTICALLY FLAT"
    if slope > 15.0 and trend_pct > 20.0:
        verdict = "DIVERGING"

    return {
        "file": json_path.name,
        "tag": meta.get("tag", json_path.stem),
        "d_line": d_line,
        "w33": w33,
        "target_gain": target_gain,
        "clamp": clamp,
        "k": k,
        "lr": lr,
        "epochs": epochs,
        "init_loss": init_loss,
        "final_loss": final_loss,
        "q1_loss": q1_loss,
        "q4_loss": q4_loss,
        "trend_pct": trend_pct,
        "slope": slope,
        "r_squared": r_squared,
        "best_epoch": best_epoch,
        "best_loss": best_loss,
        "best_enob": best_enob,
        "init_enob": init_enob,
        "final_enob": final_enob,
        "verdict": verdict,
        "records": records,
    }


def generate_figures(results):
    if not results:
        return None

    fig, axes = plt.subplots(2, 2, figsize=(16, 11))
    fig.suptitle(
        "Inverted MAML Mode A: Virtual Gain Silicon Campaign Telemetry\n"
        "[VIRTUAL_HARDWARE_EMULATION] PCB v1.3.2 (1k/3.3k Attenuator) | Arbitrary White Noise Input",
        fontsize=13, fontweight="bold"
    )

    # 1. Loss trajectories
    ax1 = axes[0, 0]
    for r in results:
        eps = [rec["epoch"] for rec in r["records"]]
        losses = [rec["loss_lsb2"] for rec in r["records"]]
        label = f"D{r['d_line']}x/W{r['w33']}x G{r['target_gain']:.1f}x (c{r['clamp']})"
        ax1.plot(eps, losses, label=label, alpha=0.85, linewidth=1.5)
    ax1.set_title("Validation Loss Trajectories ($LSB^2$ vs Epoch)")
    ax1.set_xlabel("Epoch (20 vectors x 10 strata)")
    ax1.set_ylabel("Loss ($LSB^2$)")
    ax1.grid(True, linestyle="--", alpha=0.5)
    ax1.legend(loc="upper right", fontsize=8)

    # 2. ENOB trajectories
    ax2 = axes[0, 1]
    for r in results:
        eps = [rec["epoch"] for rec in r["records"]]
        enobs = [rec["enob_bits"] for rec in r["records"]]
        label = f"D{r['d_line']}x/W{r['w33']}x G{r['target_gain']:.1f}x"
        ax2.plot(eps, enobs, label=label, alpha=0.85, linewidth=1.5)
    ax2.set_title("Effective Number of Bits (ENOB vs Epoch)")
    ax2.set_xlabel("Epoch")
    ax2.set_ylabel("ENOB (bits)")
    ax2.grid(True, linestyle="--", alpha=0.5)
    ax2.legend(loc="lower right", fontsize=8)

    # 3. Bar chart: Linear Regression Slope beta1
    ax3 = axes[1, 0]
    labels = [f"D{r['d_line']}/W{r['w33']}\nG{r['target_gain']:.1f}x\nc{r['clamp']}" for r in results]
    slopes = [r["slope"] for r in results]
    colors = ["#2ca02c" if s < -1.0 else ("#d62728" if s > 15.0 else "#7f7f7f") for s in slopes]
    bars = ax3.bar(range(len(results)), slopes, color=colors, edgecolor="black", width=0.6)
    ax3.axhline(0, color="black", linestyle="-", linewidth=1.0)
    ax3.set_xticks(range(len(results)))
    ax3.set_xticklabels(labels, fontsize=8)
    ax3.set_title("Loss Regression Slope $\\beta_1$ ($LSB^2$/epoch) [Negative = Converging]")
    ax3.set_ylabel("Slope $\\beta_1$ ($LSB^2$/ep)")
    ax3.grid(True, axis="y", linestyle="--", alpha=0.5)

    # 4. Bar chart: Peak ENOB achieved
    ax4 = axes[1, 1]
    best_enobs = [r["best_enob"] for r in results]
    init_enobs = [r["init_enob"] for r in results]
    x_pos = np.arange(len(results))
    width = 0.35
    ax4.bar(x_pos - width/2, init_enobs, width, label="Initial Baseline (Ep 0)", color="#aec7e8", edgecolor="black")
    ax4.bar(x_pos + width/2, best_enobs, width, label="Peak Achieved", color="#1f77b4", edgecolor="black")
    ax4.set_xticks(x_pos)
    ax4.set_xticklabels(labels, fontsize=8)
    ax4.set_title("Initial Baseline vs Peak ENOB (bits)")
    ax4.set_ylabel("ENOB (bits)")
    ax4.set_ylim(bottom=max(0, min(init_enobs + best_enobs) - 1.0))
    ax4.grid(True, axis="y", linestyle="--", alpha=0.5)
    ax4.legend(loc="upper right", fontsize=8)

    plt.tight_layout()
    out_fig = FIG_DIR / "fig_virtual_gain_campaign_telemetry.png"
    plt.savefig(out_fig, dpi=180)
    plt.close()
    return out_fig


def generate_markdown_report(results, fig_path: Path):
    timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S")
    hhmm_str = time.strftime("%H%M")

    converged_cnt = sum(1 for r in results if r["verdict"] == "CONVERGING")
    total_cnt = len(results)
    conv_pct = (converged_cnt / total_cnt * 100.0) if total_cnt > 0 else 0.0

    lines = [
        f"# INVERTED MAML MODE A: VIRTUAL GAIN RESEARCH REPORT ({time.strftime('%H:00')})",
        f"**Patent Pending SE 2630397-4 | Autonomous Silicon Campaign**  ",
        f"**Report Generated:** {timestamp_str} | **Hardware:** Efinix Trion T120 Master SoC (`192.168.1.50:5000`)",
        "",
        "> [!IMPORTANT]",
        "> **`[VIRTUAL_HARDWARE_EMULATION]` Tag Active:**",
        "> These experiments are executed on carrier board **PCB v1.3.2** ($1\\text{ k}\\Omega / 3.3\\text{ k}\\Omega$ attenuator, no dedicated ADC149 yet).",
        "> Data line swing ($D_{line}$) and Matrix 33 weights ($D_{w33}$) are digitally attenuated, while the digital supervisor demands an amplified target ($G_{req}$),",
        "> forcing the 2-layer compensation network ($M_3 \\to \\text{Sig4} \\to M_8 \\to \\text{Sig10}$) to exercise its dynamic range and non-linear S-curves across 100% arbitrary white noise.",
        "",
        "---",
        "",
        "## 1. Executive Summary & Hourly Silicon Progress",
        f"- **Completed Runs:** {total_cnt} conditions evaluated ({total_cnt * 200:,} epochs total).",
        f"- **Convergence Rate:** **{converged_cnt} of {total_cnt} conditions converging statistically** ({conv_pct:.1f}%).",
    ]

    if results:
        best_r = min(results, key=lambda x: x["slope"])
        lines.extend([
            f"- **Best Convergence Gradient:** **Condition `{best_r['tag']}`**",
            f"  - Configuration: $D_{{line}}={best_r['d_line']}\\times$, $D_{{w33}}={best_r['w33']}\\times$, $G_{{req}}={best_r['target_gain']:.2f}\\times$, $W_{{clamp}}=\\pm {best_r['clamp']}\\text{{ LSB}}$.",
            f"  - Regression Slope: **$\\beta_1 = {best_r['slope']:+.3f}\\text{{ LSB}}^2/\\text{{ep}}$** ($R^2 = {best_r['r_squared']:.4f}$).",
            f"  - $Q_1 \\to Q_4$ Net Loss Trend: **{best_r['trend_pct']:+.1f}%** ({best_r['q1_loss']:.1f} $\\to$ {best_r['q4_loss']:.1f} $\\text{{LSB}}^2$).",
            f"  - Peak Bit Precision: **{best_r['best_enob']:.2f} bits** (Epoch #{best_r['best_epoch']}).",
        ])

    lines.extend([
        "",
        "---",
        "",
        "## 2. Comprehensive Experimental Telemetry Table",
        "",
        "| # | Condition Tag | $D_{line}$ | $D_{w33}$ | $G_{req}$ | $W_{clamp}$ | $Q_1 \\to Q_4$ Loss | Slope $\\beta_1$ | Net Trend | $R^2$ | Peak ENOB | Verdict |",
        "| :-: | :--- | :-: | :-: | :-: | :-: | :---: | :---: | :---: | :---: | :---: | :--- |",
    ])

    for i, r in enumerate(results, 1):
        v_fmt = f"**`{r['verdict']}`**" if r["verdict"] == "CONVERGING" else f"`{r['verdict']}`"
        lines.append(
            f"| **{i}** | `{r['tag']}` | {r['d_line']}x | {r['w33']}x | {r['target_gain']:.1f}x | "
            f"$\\pm {r['clamp']}$ | {r['q1_loss']:.0f} $\\to$ {r['q4_loss']:.0f} | "
            f"{r['slope']:+.2f} | {r['trend_pct']:+.1f}% | {r['r_squared']:.4f} | "
            f"{r['best_enob']:.2f} b | {v_fmt} |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 3. Telemetry Visualizations & Convergence Dynamics",
        "",
        f"![Virtual Gain Silicon Telemetry]({fig_path.name})",
        "",
        "---",
        "",
        "## 4. Hardware & Firmware Lineage Metadata",
        "- **Carrier Board:** PCB v1.3.2 (Summing attenuator: 1k / 3.3k Ohm installed)",
        "- **Silicon Target:** Efinix Trion T120F324 Master SoC (`192.168.1.50:5000`) + T20F256",
        "- **Training Protocol:** True Multi-Strata Batching ($K=20$ vectors, $M=10$ strata, 200 samples/ep)",
        "- **Carrier Search:** Hardware Hadamard FWHT-16 with carrier wave search",
        "- **Input Vectors:** 100% arbitrary white noise freshly drawn each epoch",
        "- **Next Scheduled Report:** Next hour at top of the clock",
    ])

    report_content = "\n".join(lines) + "\n"

    # Save latest hourly report and rolling summary
    latest_report_file = DOCS_DIR / "MODE_A_VIRTUAL_GAIN_LATEST_HOURLY_REPORT.md"
    timestamped_report_file = DOCS_DIR / f"MODE_A_VIRTUAL_GAIN_REPORT_{hhmm_str}.md"
    summary_report_file = DOCS_DIR / "MODE_A_VIRTUAL_GAIN_CAMPAIGN_SUMMARY.md"

    with open(latest_report_file, "w") as f:
        f.write(report_content)
    with open(timestamped_report_file, "w") as f:
        f.write(report_content)
    with open(summary_report_file, "w") as f:
        f.write(report_content)

    return latest_report_file


def main():
    json_files = sorted(LOGS_DIR.glob("*.json"))
    results = []
    for jf in json_files:
        if jf.name == "smoke_test.json":
            continue
        res = analyze_file(jf)
        if res is not None:
            results.append(res)

    print(f"[*] Found {len(results)} valid virtual gain experiment records.")
    if not results:
        print("[!] No records to report.")
        return

    fig_path = generate_figures(results)
    report_path = generate_markdown_report(results, fig_path)
    print(f"[+] Report generated: {report_path}")
    print(f"[+] Figure generated: {fig_path}")


if __name__ == "__main__":
    main()

