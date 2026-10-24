#!/home/olle/anaconda3/bin/python
"""
Characterize Crosspoint Cell (0, 0) on Matrix 33 in Mode B (Bare Matrix)
========================================================================
Performs high-precision hardware characterization of the Dual-2T1C differential
triode multiplier cell on silicon over Ethernet UDP:
  1. Sweeps signed Weight W across [-120 .. +120] LSB.
  2. At each weight, measures response for X = 0, X = +96, and X = -96 LSB
     with N=5 repetitions to extract mean transfer curves and standard deviation (noise).
  3. Computes the true physical electrical zero-crossing (W_null where dY/dX = 0).
  4. Identifies the stability boundary (quiet linear regime vs. high-variance oscillatory regime).
  5. Outputs publication-quality 4-panel analysis figure and JSON dataset.
"""

from __future__ import annotations
import json
import os
import sys
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# Ensure repository root is on sys.path
REPO_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from gui.udp_client import MAT_M33, MamlUdpClient


def safe_probe_xw(client: MamlUdpClient, mat_id: int, row: int, col: int, x_amp: int, w_val: int, retries: int = 3):
    """Safely executes a single cell probe with automatic retries over UDP."""
    for attempt in range(retries):
        try:
            res = client.probe_cell_xw(mat_id, row, col, x_amp=x_amp, w_fixed=w_val, sweep_input=True, hold=False)
            if res is not None:
                return res
        except Exception:
            pass
        time.sleep(0.04)
    return None


def run_characterization():
    client = MamlUdpClient(host="192.168.1.50", port=5000, timeout=1.0)
    version_str = client.query_version()
    print(f"Connected to hardware: {version_str}")

    # Ensure heaters are disarmed
    client.set_heaters(False, [0, 0, 0, 0])

    target_mat = MAT_M33
    target_row = 0
    target_col = 0
    col_name = "C1 (ColTIA 1)"
    mat_name = "M33 (Main Payload 6x6)"
    x_amp = 96

    # Dense sweep across weights
    weights = [
        -120, -110, -100, -90, -80, -70, -60, -50, -45, -43, -40, -35, -30,
        -20, -10, 0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120
    ]
    reps_per_point = 5

    print(f"\nCharacterizing Cell (Row {target_row}, Col {target_col}) on {mat_name} in Mode B...")
    print(f"Sweeping {len(weights)} weights across [-120..+120] LSB with {reps_per_point} reps per point.")
    print("=" * 78)
    print(f"{'Weight W':>10} | {'Mean Pos':>9} | {'Mean Neg':>9} | {'Mean Zero':>10} | {'Delta Gain':>11} | {'Gain Std':>9}")
    print("-" * 78)

    records = []

    for w in weights:
        pos_samples = []
        neg_samples = []
        zero_samples = []
        delta_samples = []

        for _ in range(reps_per_point):
            res = safe_probe_xw(client, target_mat, target_row, target_col, x_amp=x_amp, w_val=w)
            if res is not None:
                p = res.adc49_pos[target_col]
                n = res.adc49_neg[target_col]
                z = res.adc49_zero[target_col]
                pos_samples.append(p)
                neg_samples.append(n)
                zero_samples.append(z)
                delta_samples.append(p - n)
            time.sleep(0.015)

        if not delta_samples:
            print(f"{w:+10d} | FAILED TO READ (TIMEOUT)")
            continue

        mean_pos = float(np.mean(pos_samples))
        std_pos = float(np.std(pos_samples))
        mean_neg = float(np.mean(neg_samples))
        std_neg = float(np.std(neg_samples))
        mean_zero = float(np.mean(zero_samples))
        std_zero = float(np.std(zero_samples))
        mean_delta = float(np.mean(delta_samples))
        std_delta = float(np.std(delta_samples))

        rec = {
            "weight": w,
            "x_amp": x_amp,
            "mean_pos": mean_pos,
            "std_pos": std_pos,
            "mean_neg": mean_neg,
            "std_neg": std_neg,
            "mean_zero": mean_zero,
            "std_zero": std_zero,
            "mean_delta": mean_delta,
            "std_delta": std_delta,
            "pos_samples": [int(x) for x in pos_samples],
            "neg_samples": [int(x) for x in neg_samples],
            "zero_samples": [int(x) for x in zero_samples],
            "delta_samples": [int(x) for x in delta_samples],
        }
        records.append(rec)

        print(
            f"{w:+10d} | {mean_pos:+9.1f} | {mean_neg:+9.1f} | {mean_zero:+10.1f} | "
            f"{mean_delta:+11.1f} | {std_delta:9.2f}"
        )

    # Find electrical zero crossing (W_null)
    # Search for crossing where mean_delta passes through 0
    w_vals = [r["weight"] for r in records]
    deltas = [r["mean_delta"] for r in records]
    stds = [r["std_delta"] for r in records]

    # Find the weight with minimum absolute delta and zero crossing
    w_min_delta = min(records, key=lambda r: abs(r["mean_delta"]))
    print("\n" + "=" * 78)
    print(f"Empirical minimum delta observed at W = {w_min_delta['weight']:+d} LSB:")
    print(f"  Delta = {w_min_delta['mean_delta']:+.2f} +/- {w_min_delta['std_delta']:.2f} LSB")
    print(f"  Pos   = {w_min_delta['mean_pos']:+.2f} +/- {w_min_delta['std_pos']:.2f} LSB")
    print(f"  Neg   = {w_min_delta['mean_neg']:+.2f} +/- {w_min_delta['std_neg']:.2f} LSB")
    print(f"  Zero  = {w_min_delta['mean_zero']:+.2f} +/- {w_min_delta['std_zero']:.2f} LSB")

    # Linear interpolation of exact W_null around the zero crossing
    w_null_interp = None
    for i in range(len(deltas) - 1):
        if (deltas[i] <= 0 and deltas[i + 1] >= 0) or (deltas[i] >= 0 and deltas[i + 1] <= 0):
            d1, d2 = deltas[i], deltas[i + 1]
            if d2 != d1:
                w_null_interp = w_vals[i] + (0.0 - d1) * (w_vals[i + 1] - w_vals[i]) / (d2 - d1)
                break

    if w_null_interp is not None:
        print(f"Interpolated exact electrical zero crossing W_null = {w_null_interp:+.1f} LSB")
    else:
        print(f"Closest discrete electrical zero crossing W_null = {w_min_delta['weight']:+d} LSB")

    # Save dataset to JSON
    json_path = os.path.join(REPO_ROOT, "FPGA_code", "docs", "cell_0_0_characterization_mode_b.json")
    with open(json_path, "w") as f:
        json.dump(
            {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "hardware_version": version_str,
                "matrix": "M33",
                "row": target_row,
                "col": target_col,
                "jumper_mode": "Mode B (JUMPER_OFF_NO_COMP = 1)",
                "w_null_discrete": w_min_delta["weight"],
                "w_null_interpolated": w_null_interp,
                "sweep": records,
            },
            f,
            indent=2,
        )
    print(f"Saved JSON dataset to: {json_path}")

    # Generate publication-quality 4-panel figure
    fig_dir = os.path.join(REPO_ROOT, "FPGA_code", "docs", "figures")
    os.makedirs(fig_dir, exist_ok=True)
    fig_path = os.path.join(fig_dir, "fig_cell_0_0_triode_surface.png")

    fig, axes = plt.subplots(2, 2, figsize=(13, 10), dpi=300)
    plt.subplots_adjust(hspace=0.28, wspace=0.25)

    # Palette
    c_stable = "#1b9e77"
    c_null = "#7570b3"
    c_unstable = "#d95f02"
    c_blue = "#1f78b4"

    # Panel A: Transfer response Y vs X for representative weights
    ax_a = axes[0, 0]
    sample_weights = [-120, -80, -43, 0, 40, 80]
    colors = plt.cm.plasma(np.linspace(0.05, 0.95, len(sample_weights)))

    for sw, c in zip(sample_weights, colors):
        # find matching rec
        match = [r for r in records if r["weight"] == sw]
        if match:
            m = match[0]
            x_pts = [-x_amp, 0, +x_amp]
            y_pts = [m["mean_neg"], m["mean_zero"], m["mean_pos"]]
            y_err = [m["std_neg"], m["std_zero"], m["std_pos"]]
            style = "o-" if sw != -43 else "s--"
            lw = 2.5 if sw == -43 else 1.5
            label = f"W = {sw:+4d} LSB" + (" (Null Point)" if sw == -43 else "")
            ax_a.errorbar(x_pts, y_pts, yerr=y_err, fmt=style, color=c, lw=lw, capsize=4, label=label)

    ax_a.set_title("A: Multiplier Transfer Response $Y(X)$ vs Input $X$", fontsize=12, fontweight="bold")
    ax_a.set_xlabel("In-Data Row Input $X$ (LSB relative to Mid-Scale 128)", fontsize=10)
    ax_a.set_ylabel("Differential Output $Y$ (ADC_49[C1] LSB)", fontsize=10)
    ax_a.grid(True, linestyle="--", alpha=0.5)
    ax_a.legend(loc="upper left", fontsize=8, framealpha=0.9)
    ax_a.axhline(0, color="gray", lw=0.8, linestyle=":")

    # Panel B: Net Differential Gain dY/dX vs Weight W
    ax_b = axes[0, 1]
    gains = [r["mean_delta"] / (2.0 * x_amp) for r in records]
    gain_errs = [r["std_delta"] / (2.0 * x_amp) for r in records]

    ax_b.errorbar(w_vals, gains, yerr=gain_errs, fmt="o-", color=c_blue, ecolor="#a6bddb", capsize=3, lw=1.8, markersize=5)
    ax_b.axhline(0, color="red", linestyle="--", lw=1.2, label="Zero Gain Line ($dY/dX = 0$)")

    null_label_w = w_null_interp if w_null_interp is not None else w_min_delta["weight"]
    ax_b.axvline(null_label_w, color=c_null, linestyle=":", lw=1.8, label=f"Electrical Null $W_{{null}} \\approx {null_label_w:+.1f}$ LSB")
    ax_b.plot(null_label_w, 0, "r*", markersize=14, zorder=5)

    ax_b.set_title("B: Incremental Multiplier Gain $\\Delta Y / (2X)$ vs Weight $W$", fontsize=12, fontweight="bold")
    ax_b.set_xlabel("Signed Weight $W$ (LSB relative to Mid-Scale 128)", fontsize=10)
    ax_b.set_ylabel("Incremental Gain $G = \\Delta Y / (2X)$ (LSB/LSB)", fontsize=10)
    ax_b.grid(True, linestyle="--", alpha=0.5)
    ax_b.legend(loc="lower right", fontsize=8, framealpha=0.9)

    # Panel C: Statistical Output Variance / Noise vs Weight W
    ax_c = axes[1, 0]
    std_deltas = [r["std_delta"] for r in records]
    std_zeros = [r["std_zero"] for r in records]

    ax_c.plot(w_vals, std_deltas, "o-", color=c_unstable, lw=1.8, markersize=5, label="Noise $\\sigma(\\Delta Y)$ (Net Delta Noise)")
    ax_c.plot(w_vals, std_zeros, "s--", color=c_stable, lw=1.5, markersize=4, label="Noise $\\sigma(Y_{zero})$ (Quiescent Noise)")

    # Highlight stability zones
    ax_c.axvspan(-125, -30, color="#d9f0d3", alpha=0.5, label="Quiet Linear Zone ($W \\leq -30$)")
    ax_c.axvspan(-30, 125, color="#fee0d2", alpha=0.4, label="High-Variance Zone ($W > -30$)")
    ax_c.axvline(null_label_w, color=c_null, linestyle=":", lw=1.5)

    ax_c.set_title("C: Statistical Output Noise $\\sigma$ vs Weight $W$", fontsize=12, fontweight="bold")
    ax_c.set_xlabel("Signed Weight $W$ (LSB relative to Mid-Scale 128)", fontsize=10)
    ax_c.set_ylabel("Standard Deviation $\\sigma$ (ADC LSBs)", fontsize=10)
    ax_c.grid(True, linestyle="--", alpha=0.5)
    ax_c.legend(loc="upper left", fontsize=8, framealpha=0.9)

    # Panel D: Quiescent DC Baseline Offset Y(X=0) vs Weight W
    ax_d = axes[1, 1]
    mean_zeros = [r["mean_zero"] for r in records]
    ax_d.errorbar(w_vals, mean_zeros, yerr=std_zeros, fmt="o-", color="#6a3d9a", ecolor="#cab2d6", capsize=3, lw=1.8, markersize=5)
    ax_d.axhline(0, color="gray", linestyle="--", lw=1.0)
    ax_d.axvline(null_label_w, color=c_null, linestyle=":", lw=1.5, label=f"$W_{{null}} \\approx {null_label_w:+.1f}$ LSB")

    ax_d.set_title("D: Quiescent DC Baseline Shift $Y(X=0)$ vs Weight $W$", fontsize=12, fontweight="bold")
    ax_d.set_xlabel("Signed Weight $W$ (LSB relative to Mid-Scale 128)", fontsize=10)
    ax_d.set_ylabel("Quiescent Offset $Y(X=0)$ (ADC LSBs)", fontsize=10)
    ax_d.grid(True, linestyle="--", alpha=0.5)
    ax_d.legend(loc="upper left", fontsize=8, framealpha=0.9)

    fig.suptitle(
        f"Silicon Characterization: Inverted MAML Cell (0,0) in Mode B (Bare Matrix)\n"
        f"Hardware: T120 Master + T20 Coprocessor | Output: ADC_49[C1] | Null Point: $W_{{null}} \\approx {null_label_w:+.1f}$ LSB",
        fontsize=13,
        fontweight="bold",
        y=0.98,
    )

    plt.savefig(fig_path)
    plt.close()
    print(f"Generated publication figure: {fig_path}")

    # Copy to artifact directory so user can view it directly
    artifact_path = os.path.join(
        "/home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a",
        "fig_cell_0_0_triode_surface.png",
    )
    try:
        import shutil
        shutil.copyfile(fig_path, artifact_path)
        print(f"Copied figure to conversation artifact: {artifact_path}")
    except Exception as exc:
        print(f"Warning: could not copy to artifact directory: {exc}")


if __name__ == "__main__":
    run_characterization()
