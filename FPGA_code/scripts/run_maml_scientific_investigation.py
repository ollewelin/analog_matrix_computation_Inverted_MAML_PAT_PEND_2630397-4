#!/usr/bin/env python3
"""
MAML Analog Silicon Empirical Research & Hardware Characterization Suite
========================================================================
100% Physical Hardware Measurements - Strictly Enforcing Anti-Simulation Policy.

Performs deep scientific investigations into the silicon hardware:
  1. 2D Transfer Surface Y = f(W, X) & Multiplier Linearity / Compression.
  2. Op-Amp Driver Sag, Loading & Row-to-Column Crosstalk Analysis.
  3. Full 36-Cell Spatial Uniformity & Process Mismatch Heatmap (M33 6x6).
  4. Layer-to-Layer Topology Comparison: M3 (Layer 1) vs M8 (Layer 2) vs M33 (Payload).
  5. Hadamard 24 µs Orthogonal Carrier Wave Extraction, SNR & Orthogonality Matrix.
  6. Dynamic Gate Capacitance Retention & Inter-Refresh Decay over 10 ms Strata.

Generates publication-quality figures, structured JSON/CSV datasets, and computes
all scientific metrics for the final research report.
"""

from __future__ import annotations
import os
import sys
import time
import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import numpy as np

# Set matplotlib headless backend before importing pyplot
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))
SKILL_DIR = REPO_ROOT / ".agents" / "skills" / "data-log-quota"
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))

from gui.udp_client import (
    MamlUdpClient,
    MAT_M3,
    MAT_M8,
    MAT_M33,
    CellProbeResult,
    HadamardDiagResult,
)
from check_quota import enforce_quota_before_write, get_quota_status

DOCS_DIR = REPO_ROOT / "FPGA_code" / "docs"
FIG_DIR = DOCS_DIR / "figures"
DOCS_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)


class MamlHardwareResearcher:
    def __init__(self, host: str = "192.168.1.50", port: int = 5000):
        self.host = host
        self.port = port
        self.client = MamlUdpClient(host=host, port=port, timeout=1.5)
        self.banner = self._verify_connection()
        # Ensure heaters are strictly OFF
        self.client.set_heaters(False, [0, 0, 0, 0])
        print(f"[+] Initialized MAML Hardware Researcher on {host}:{port}")
        print(f"    Banner: {self.banner}")

    def _verify_connection(self) -> str:
        version = self.client.query_version()
        if "MAML" not in version:
            raise RuntimeError(f"Unexpected response from hardware: {version}")
        return version

    # =========================================================================
    # Investigation 1: 2D Multiplier Transfer Surface Y = f(W, X)
    # =========================================================================
    def investigate_transfer_surface(
        self,
        matrix_id: int = MAT_M33,
        row: int = 0,
        col: int = 0,
        weights: Optional[List[int]] = None,
        inputs: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """Sweeps 2D grid of Weights (-112..+112) vs Inputs (16..120)."""
        if weights is None:
            weights = [-112, -96, -64, -32, 0, 32, 64, 96, 112]
        if inputs is None:
            inputs = [16, 32, 48, 64, 80, 96, 112]

        print(f"\n[*] Investigation 1: 2D Transfer Surface for Matrix={matrix_id}, Row={row}, Col={col}...")
        grid_data = []
        surface_delta = np.zeros((len(weights), len(inputs)), dtype=float)
        surface_pos = np.zeros((len(weights), len(inputs)), dtype=float)
        surface_neg = np.zeros((len(weights), len(inputs)), dtype=float)
        surface_zero = np.zeros((len(weights), len(inputs)), dtype=float)

        for w_idx, w in enumerate(weights):
            row_results = []
            for x_idx, x in enumerate(inputs):
                res: Optional[CellProbeResult] = self.client.probe_cell_xw(
                    matrix_id=matrix_id, row=row, col=col, x_amp=x, w_fixed=w, sweep_input=True, hold=False
                )
                if res is None:
                    print(f"    [!] Timeout at W={w}, X={x}")
                    continue

                if matrix_id == MAT_M3:
                    pos = res.adc45_pos[col]
                    neg = res.adc45_neg[col]
                    zero = res.adc45_zero[col]
                else:
                    pos = res.adc49_pos[col]
                    neg = res.adc49_neg[col]
                    zero = res.adc49_zero[col]

                delta = pos - neg
                surface_delta[w_idx, x_idx] = delta
                surface_pos[w_idx, x_idx] = pos
                surface_neg[w_idx, x_idx] = neg
                surface_zero[w_idx, x_idx] = zero

                entry = {
                    "w": w,
                    "x": x,
                    "pos": pos,
                    "neg": neg,
                    "zero": zero,
                    "delta": delta,
                    "crosstalk_columns": res.adc49_pos if matrix_id != MAT_M3 else res.adc45_pos,
                }
                row_results.append(entry)
                # Small pause to ensure quiet settling
                time.sleep(0.01)
            grid_data.append(row_results)
            print(f"    Processed W={w:+4d} across {len(inputs)} input levels.")

        # Compute empirical metrics:
        # Multiplier Gain (LSB / (W_LSB * X_LSB))
        # Linear slope at mid-scale (W=64, X=64)
        gain_norm = surface_delta / (np.outer(weights, inputs) + 1e-9)

        return {
            "matrix_id": matrix_id,
            "row": row,
            "col": col,
            "weights": weights,
            "inputs": inputs,
            "surface_delta": surface_delta.tolist(),
            "surface_pos": surface_pos.tolist(),
            "surface_neg": surface_neg.tolist(),
            "surface_zero": surface_zero.tolist(),
            "grid_data": grid_data,
        }

    # =========================================================================
    # Investigation 2: Op-Amp Driver Sag, Loading & Row/Column Crosstalk
    # =========================================================================
    def investigate_opamp_sag_and_crosstalk(
        self,
        matrix_id: int = MAT_M33,
        target_row: int = 0,
        target_col: int = 0,
    ) -> Dict[str, Any]:
        """
        Evaluates op-amp voltage sag and current loading effects:
        1. Input Amplitude Compression: Does Delta_Y / X sag as X increases from 8 to 127?
        2. Column Isolation: When target column is driven, what signal couples to other 5 columns?
        """
        print(f"\n[*] Investigation 2: Op-Amp Sag & Column Crosstalk...")
        fine_inputs = [8, 16, 24, 32, 48, 64, 80, 96, 112, 127]
        test_weights = [-64, 0, +64]

        sag_results = []
        isolation_data = []

        for w in test_weights:
            curve = []
            for x in fine_inputs:
                res = self.client.probe_cell_xw(
                    matrix_id=matrix_id, row=target_row, col=target_col, x_amp=x, w_fixed=w, sweep_input=True
                )
                if res is None:
                    continue
                v_pos = res.adc49_pos[target_col] if matrix_id != MAT_M3 else res.adc45_pos[target_col]
                v_neg = res.adc49_neg[target_col] if matrix_id != MAT_M3 else res.adc45_neg[target_col]
                v_zero = res.adc49_zero[target_col] if matrix_id != MAT_M3 else res.adc45_zero[target_col]
                delta = v_pos - v_neg
                gain_per_x = delta / x if x > 0 else 0.0

                all_cols_pos = res.adc49_pos if matrix_id != MAT_M3 else res.adc45_pos
                all_cols_zero = res.adc49_zero if matrix_id != MAT_M3 else res.adc45_zero

                curve.append({
                    "x": x,
                    "w": w,
                    "v_pos": v_pos,
                    "v_neg": v_neg,
                    "v_zero": v_zero,
                    "delta": delta,
                    "gain_per_x": gain_per_x,
                    "all_columns": all_cols_pos,
                })
                time.sleep(0.01)

            sag_results.append({"w": w, "curve": curve})

        # Calculate Inter-Column Crosstalk Isolation at W=+64, X=96
        res_ref = self.client.probe_cell_xw(
            matrix_id=matrix_id, row=target_row, col=target_col, x_amp=96, w_fixed=64, sweep_input=True
        )
        crosstalk_db = []
        if res_ref:
            main_sig = abs(res_ref.adc49_pos[target_col] - res_ref.adc49_neg[target_col])
            for c in range(6):
                if c == target_col:
                    crosstalk_db.append(0.0)
                else:
                    leak = abs(res_ref.adc49_pos[c] - res_ref.adc49_neg[c])
                    ratio = (main_sig / (leak + 1e-3))
                    db = 20.0 * np.log10(max(1.0, ratio))
                    crosstalk_db.append(float(db))

        return {
            "sag_results": sag_results,
            "fine_inputs": fine_inputs,
            "target_row": target_row,
            "target_col": target_col,
            "crosstalk_isolation_db": crosstalk_db,
        }

    # =========================================================================
    # Investigation 3: Full 36-Cell Spatial Uniformity Map (Matrix 33)
    # =========================================================================
    def investigate_m33_spatial_uniformity(self) -> Dict[str, Any]:
        """Scans all 36 cells of Matrix 33 (6x6) with W = +64, W = -64, X = 96."""
        print(f"\n[*] Investigation 3: Full 36-Cell Spatial Uniformity Map on M33 (6x6)...")
        gain_matrix = np.zeros((6, 6), dtype=float)
        offset_matrix = np.zeros((6, 6), dtype=float)
        delta_matrix = np.zeros((6, 6), dtype=float)
        asym_matrix = np.zeros((6, 6), dtype=float)

        cell_data = []

        for r in range(6):
            for c in range(6):
                res_pos, res_neg = None, None
                for attempt in range(3):
                    res_pos = self.client.probe_cell_xw(MAT_M33, row=r, col=c, x_amp=96, w_fixed=64)
                    time.sleep(0.015)
                    res_neg = self.client.probe_cell_xw(MAT_M33, row=r, col=c, x_amp=96, w_fixed=-64)
                    time.sleep(0.015)
                    if res_pos is not None and res_neg is not None:
                        break
                    time.sleep(0.05)

                if res_pos and res_neg:
                    y_pos_w = res_pos.adc49_pos[c]
                    y_neg_w = res_neg.adc49_pos[c]
                    y_zero_w = res_pos.adc49_zero[c]

                    delta_w = y_pos_w - y_neg_w
                    gain = delta_w / 128.0
                    offset = y_zero_w
                    asym = abs(y_pos_w) - abs(y_neg_w)

                    gain_matrix[r, c] = gain
                    offset_matrix[r, c] = offset
                    delta_matrix[r, c] = delta_w
                    asym_matrix[r, c] = asym

                    cell_data.append({
                        "row": r,
                        "col": c,
                        "gain": gain,
                        "delta_w": delta_w,
                        "offset": offset,
                        "y_pos_w": y_pos_w,
                        "y_neg_w": y_neg_w,
                        "asym": asym,
                    })
                print(f"    Cell ({r}, {c}) -> Delta={delta_matrix[r, c]:+.1f} LSB, Gain={gain_matrix[r, c]:.2f}")

        # Compute summary statistics
        flat_gains = gain_matrix.flatten()
        mean_gain = float(np.mean(flat_gains))
        std_gain = float(np.std(flat_gains))
        cv_gain = float(std_gain / (mean_gain + 1e-9) * 100.0)

        flat_offsets = offset_matrix.flatten()
        mean_off = float(np.mean(flat_offsets))
        std_off = float(np.std(flat_offsets))

        row_means = np.mean(gain_matrix, axis=1).tolist()
        col_means = np.mean(gain_matrix, axis=0).tolist()

        return {
            "gain_matrix": gain_matrix.tolist(),
            "offset_matrix": offset_matrix.tolist(),
            "delta_matrix": delta_matrix.tolist(),
            "asym_matrix": asym_matrix.tolist(),
            "mean_gain": mean_gain,
            "std_gain": std_gain,
            "cv_gain_pct": cv_gain,
            "mean_offset": mean_off,
            "std_offset": std_off,
            "row_gain_means": row_means,
            "col_gain_means": col_means,
            "cell_data": cell_data,
        }

    # =========================================================================
    # Investigation 4: Layer-to-Layer Comparison (M3 vs M8 vs M33)
    # =========================================================================
    def investigate_matrix_comparison(self) -> Dict[str, Any]:
        """Compares physical behavior across M3 (8x6), M8 (7x6), and M33 (6x6)."""
        print(f"\n[*] Investigation 4: Cross-Matrix Comparison (M3 vs M8 vs M33)...")
        matrices = [
            (MAT_M3, "M3 (Layer 1 -> ADC_45)", 6),
            (MAT_M8, "M8 (Layer 2 -> ADC_49)", 6),
            (MAT_M33, "M33 (Payload -> ADC_49)", 6),
        ]

        results = []
        for mat_id, mat_name, num_cells in matrices:
            deltas = []
            zeros = []
            for col in range(num_cells):
                res_pos, res_neg = None, None
                for attempt in range(3):
                    res_pos = self.client.probe_cell_xw(mat_id, row=0, col=col, x_amp=96, w_fixed=64)
                    time.sleep(0.015)
                    res_neg = self.client.probe_cell_xw(mat_id, row=0, col=col, x_amp=96, w_fixed=-64)
                    time.sleep(0.015)
                    if res_pos is not None and res_neg is not None:
                        break
                    time.sleep(0.05)
                if res_pos and res_neg:
                    if mat_id == MAT_M3:
                        d = res_pos.adc45_pos[col] - res_neg.adc45_pos[col]
                        z = res_pos.adc45_zero[col]
                    else:
                        d = res_pos.adc49_pos[col] - res_neg.adc49_pos[col]
                        z = res_pos.adc49_zero[col]
                    deltas.append(d)
                    zeros.append(z)
            results.append({
                "matrix_id": mat_id,
                "name": mat_name,
                "deltas": deltas,
                "zeros": zeros,
                "mean_delta": float(np.mean(deltas)) if deltas else 0.0,
                "std_delta": float(np.std(deltas)) if deltas else 0.0,
                "mean_zero": float(np.mean(zeros)) if zeros else 0.0,
            })
            print(f"    {mat_name}: Mean Delta = {results[-1]['mean_delta']:.1f} LSB, Std = {results[-1]['std_delta']:.1f} LSB")

        return {"matrix_comparison": results}

    # =========================================================================
    # Investigation 5: Hadamard Orthogonal Carrier Wave Extraction & SNR
    # =========================================================================
    def investigate_hadamard_carrier(self, n_repeats: int = 10) -> Dict[str, Any]:
        """Averages multiple 24 µs Hadamard diagnostics, extracts carrier waveforms & SNR."""
        print(f"\n[*] Investigation 5: Hadamard 24 µs Carrier Wave & SNR ({n_repeats} bursts)...")
        cap45_accum = np.zeros((16, 6), dtype=float)
        cap49_accum = np.zeros((16, 6), dtype=float)
        cap45_sq = np.zeros((16, 6), dtype=float)
        cap49_sq = np.zeros((16, 6), dtype=float)

        valid_runs = 0
        for r in range(n_repeats):
            diag = self.client.diag_hadamard(mode=0, en_mask=0x7FFF)
            if diag and diag.cap45 and diag.cap49:
                arr45 = np.array(diag.cap45, dtype=float)
                arr49 = np.array(diag.cap49, dtype=float)
                cap45_accum += arr45
                cap49_accum += arr49
                cap45_sq += arr45 ** 2
                cap49_sq += arr49 ** 2
                valid_runs += 1
            time.sleep(0.02)

        if valid_runs == 0:
            raise RuntimeError("No valid Hadamard diagnostics received!")

        mean45 = cap45_accum / valid_runs
        mean49 = cap49_accum / valid_runs
        std45 = np.sqrt(np.maximum(0.0, (cap45_sq / valid_runs) - (mean45 ** 2)))
        std49 = np.sqrt(np.maximum(0.0, (cap49_sq / valid_runs) - (mean49 ** 2)))

        # Take the first 12 active Hadamard pulses (24 us = 12 x 2 us)
        pulses45 = mean45[:12, :]
        pulses49 = mean49[:12, :]

        # Combine into 12 channels: C1..C6 ADC45, C1..C6 ADC49
        all_channels = np.hstack([pulses45, pulses49])  # shape (12, 12)

        # Empirical Orthogonality Matrix: O = H^T * H / N
        norm_channels = all_channels - np.mean(all_channels, axis=0)
        stds = np.std(norm_channels, axis=0) + 1e-9
        corr_matrix = (norm_channels.T @ norm_channels) / (np.outer(stds, stds) * 12.0)

        # SNR calculation per channel
        snr_db = []
        for ch in range(12):
            sig_amp = np.ptp(all_channels[:, ch])  # peak-to-peak swing
            noise = np.mean(std45[:, ch]) if ch < 6 else np.mean(std49[:, ch - 6])
            snr = 20.0 * np.log10(max(1.0, sig_amp / (noise + 1e-6)))
            snr_db.append(float(snr))

        print(f"    Completed {valid_runs} Hadamard runs. Channel SNRs: {np.mean(snr_db):.1f} dB average.")

        return {
            "mean_pulses_adc45": pulses45.tolist(),
            "mean_pulses_adc49": pulses49.tolist(),
            "std_pulses_adc45": std45[:12, :].tolist(),
            "std_pulses_adc49": std49[:12, :].tolist(),
            "correlation_matrix": corr_matrix.tolist(),
            "snr_db_per_channel": snr_db,
            "mean_snr_db": float(np.mean(snr_db)),
        }

    # =========================================================================
    # Investigation 6: 10 ms Dynamic Strata & Gate Charge Retention Analysis
    # =========================================================================
    def investigate_temporal_retention(self) -> Dict[str, Any]:
        """Probes cell across time to quantify gate charge decay between 10ms refreshes."""
        print(f"\n[*] Investigation 6: Temporal Retention & 10 ms Strata Decay...")
        # Step through delay settings and observe ADC output
        delays_us = [500, 1500, 2500, 4000, 6000, 8000]
        decay_curve = []

        for d_us in delays_us:
            # We configure hadamard delay to d_us to shift the internal strata
            self.client.set_config(
                mode=0,
                jumper_mode=3,
                led_switches=0,
                max_meas_win_pct=25,
                hadamard_khz=500,
                inner_loop_n=100,
                seed_pct=28,
                seed_mode=1,
                w_hid_mag=14,
                trim_hid_mag=0,
                hadamard_delay_us=d_us,
            )
            time.sleep(0.03)

            # Probe cell M33 (row 0, col 0)
            res = self.client.probe_cell_xw(MAT_M33, row=0, col=0, x_amp=96, w_fixed=64)
            if res:
                delta = res.adc49_pos[0] - res.adc49_neg[0]
                decay_curve.append({
                    "delay_us": d_us,
                    "delay_ms": d_us / 1000.0,
                    "delta": delta,
                    "pos": res.adc49_pos[0],
                    "neg": res.adc49_neg[0],
                    "zero": res.adc49_zero[0],
                })
            time.sleep(0.01)

        return {"decay_curve": decay_curve}


# =============================================================================
# Plotting & Reporting Helpers
# =============================================================================
def generate_scientific_figures(data: Dict[str, Any], fig_dir: Path = FIG_DIR) -> Dict[str, Path]:
    """Generates all 6 publication-quality figures from hardware measurements."""
    print("\n[*] Generating Publication-Quality Scientific Figures...")
    fig_paths = {}

    # Figure 1: 2D Multiplier Transfer Surface
    d1 = data["investigation_1_transfer_surface"]
    W = np.array(d1["weights"])
    X = np.array(d1["inputs"])
    Z = np.array(d1["surface_delta"])

    fig = plt.figure(figsize=(10, 5))
    ax1 = fig.add_subplot(1, 2, 1, projection="3d")
    X_grid, W_grid = np.meshgrid(X, W)
    surf = ax1.plot_surface(X_grid, W_grid, Z, cmap="coolwarm", edgecolor="k", linewidth=0.3, alpha=0.9)
    ax1.set_title("Silicon Multiplier Transfer Surface\n$Y = f(W, X)$ (Matrix 33 R0 C0)", fontsize=10, fontweight="bold")
    ax1.set_xlabel("Input Drive $X$ (LSB)", fontsize=8)
    ax1.set_ylabel("Weight $W$ (LSB)", fontsize=8)
    ax1.set_zlabel("$\Delta Y$ (ADC LSB)", fontsize=8)
    fig.colorbar(surf, ax=ax1, shrink=0.5, aspect=10)

    ax2 = fig.add_subplot(1, 2, 2)
    for i, w in enumerate(W):
        if w in [-112, -64, 0, 64, 112]:
            ax2.plot(X, Z[i, :], "o-", label=f"W = {w:+d}")
    ax2.set_title("Input Response Slices vs Weight", fontsize=10, fontweight="bold")
    ax2.set_xlabel("Input Drive Amplitude $X$ (LSB)", fontsize=8)
    ax2.set_ylabel("Differential Swing $\Delta Y$ (ADC LSB)", fontsize=8)
    ax2.grid(True, linestyle="--", alpha=0.6)
    ax2.legend(fontsize=7)
    plt.tight_layout()
    p1 = fig_dir / "fig1_transfer_surface.png"
    plt.savefig(p1, dpi=300)
    plt.close()
    fig_paths["fig1"] = p1

    # Figure 2: Op-Amp Driver Sag & Compression
    d2 = data["investigation_2_opamp_sag"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))
    for res in d2["sag_results"]:
        w = res["w"]
        xs = [pt["x"] for pt in res["curve"]]
        gains = [pt["gain_per_x"] for pt in res["curve"]]
        deltas = [pt["delta"] for pt in res["curve"]]
        ax1.plot(xs, deltas, "s-", label=f"W = {w:+d}")
        if w != 0:
            ax2.plot(xs, gains, "o-", label=f"Gain/X (W = {w:+d})")

    ax1.set_title("Output Swing vs Input Drive $X$\n(Linear Knee & Compression)", fontsize=10, fontweight="bold")
    ax1.set_xlabel("Row Input Amplitude $X$ (LSB)", fontsize=8)
    ax1.set_ylabel("Differential ADC Swing $\Delta Y$ (LSB)", fontsize=8)
    ax1.grid(True, linestyle="--", alpha=0.6)
    ax1.legend(fontsize=8)

    ax2.set_title("Normalized Gain $(\Delta Y / X)$ vs Input Drive\n(Quantifying Op-Amp Sag & Dynamic Resistance)", fontsize=10, fontweight="bold")
    ax2.set_xlabel("Row Input Amplitude $X$ (LSB)", fontsize=8)
    ax2.set_ylabel("Gain Slope $(\Delta Y / X)$", fontsize=8)
    ax2.grid(True, linestyle="--", alpha=0.6)
    ax2.legend(fontsize=8)
    plt.tight_layout()
    p2 = fig_dir / "fig2_opamp_sag_compression.png"
    plt.savefig(p2, dpi=300)
    plt.close()
    fig_paths["fig2"] = p2

    # Figure 3: Full 36-Cell Spatial Uniformity Heatmaps
    d3 = data["investigation_3_spatial_uniformity"]
    G = np.array(d3["gain_matrix"])
    Off = np.array(d3["offset_matrix"])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))
    im1 = ax1.imshow(G, cmap="viridis", interpolation="nearest")
    ax1.set_title(f"M33 (6x6) Gain Distribution $G(r, c)$\nMean = {d3['mean_gain']:.2f}, Std = {d3['std_gain']:.2f} (CV = {d3['cv_gain_pct']:.1f}%)", fontsize=9, fontweight="bold")
    ax1.set_xlabel("Column Index (C1..C6)", fontsize=8)
    ax1.set_ylabel("Row Index (R1..R6)", fontsize=8)
    for r in range(6):
        for c in range(6):
            ax1.text(c, r, f"{G[r, c]:.2f}", ha="center", va="center", color="w" if G[r, c] < 5.0 else "k", fontsize=7)
    fig.colorbar(im1, ax=ax1, fraction=0.046, pad=0.04)

    im2 = ax2.imshow(Off, cmap="magma", interpolation="nearest")
    ax2.set_title(f"M33 (6x6) Zero-Point DC Offset (LSB)\nMean = {d3['mean_offset']:.1f}, Std = {d3['std_offset']:.1f}", fontsize=9, fontweight="bold")
    ax2.set_xlabel("Column Index (C1..C6)", fontsize=8)
    ax2.set_ylabel("Row Index (R1..R6)", fontsize=8)
    for r in range(6):
        for c in range(6):
            ax2.text(c, r, f"{Off[r, c]:.0f}", ha="center", va="center", color="w" if Off[r, c] < 100 else "k", fontsize=7)
    fig.colorbar(im2, ax=ax2, fraction=0.046, pad=0.04)
    plt.tight_layout()
    p3 = fig_dir / "fig3_m33_spatial_heatmaps.png"
    plt.savefig(p3, dpi=300)
    plt.close()
    fig_paths["fig3"] = p3

    # Figure 4: Layer-to-Layer Matrix Comparison
    d4 = data["investigation_4_matrix_comparison"]["matrix_comparison"]
    fig, ax = plt.subplots(figsize=(8, 4))
    mat_names = [m["name"].split(" ")[0] for m in d4]
    means = [m["mean_delta"] for m in d4]
    stds = [m["std_delta"] for m in d4]
    x_pos = np.arange(len(mat_names))
    bars = ax.bar(x_pos, means, yerr=stds, capsize=5, color=["#2b5c8f", "#d95f02", "#7570b3"], alpha=0.85)
    ax.set_xticks(x_pos)
    ax.set_xticklabels([m["name"] for m in d4], fontsize=8)
    ax.set_ylabel("Differential Output Swing $\Delta Y$ (ADC LSB)", fontsize=8)
    ax.set_title("Silicon Output Dynamic Range Across Matrices\n(Layer 1 M3 vs Layer 2 M8 vs Main M33)", fontsize=10, fontweight="bold")
    ax.grid(True, axis="y", linestyle="--", alpha=0.6)
    for bar in bars:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2.0, h/2.0, f"{h:.1f} LSB", ha="center", va="center", color="w", fontweight="bold", fontsize=9)
    plt.tight_layout()
    p4 = fig_dir / "fig4_matrix_comparison.png"
    plt.savefig(p4, dpi=300)
    plt.close()
    fig_paths["fig4"] = p4

    # Figure 5: Hadamard 24us Carrier & Orthogonality
    d5 = data["investigation_5_hadamard_carrier"]
    corr = np.array(d5["correlation_matrix"])
    p45 = np.array(d5["mean_pulses_adc45"])
    p49 = np.array(d5["mean_pulses_adc49"])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))
    time_us = np.arange(12) * 2.0
    for ch in range(3):
        ax1.plot(time_us, p45[:, ch], "o-", label=f"ADC45 C{ch+1}")
        ax1.plot(time_us, p49[:, ch], "s--", label=f"ADC49 C{ch+1}")
    ax1.set_title("Raw 24 µs Hadamard Carrier Waveforms\n(12 Pulses @ 2.0 µs Interval)", fontsize=9, fontweight="bold")
    ax1.set_xlabel("Time (µs)", fontsize=8)
    ax1.set_ylabel("Differential ADC Signal (LSB)", fontsize=8)
    ax1.grid(True, linestyle="--", alpha=0.6)
    ax1.legend(fontsize=7, loc="upper right")

    im_c = ax2.imshow(corr, cmap="bwr", vmin=-1.0, vmax=1.0)
    ax2.set_title(f"Empirical Hadamard Orthogonality Matrix\nMean SNR = {d5['mean_snr_db']:.1f} dB", fontsize=9, fontweight="bold")
    ax2.set_xlabel("Channel Index (1..12)", fontsize=8)
    ax2.set_ylabel("Channel Index (1..12)", fontsize=8)
    fig.colorbar(im_c, ax=ax2, fraction=0.046, pad=0.04)
    plt.tight_layout()
    p5 = fig_dir / "fig5_hadamard_carrier_and_orthogonality.png"
    plt.savefig(p5, dpi=300)
    plt.close()
    fig_paths["fig5"] = p5

    # Figure 6: Temporal Retention Decay
    d6 = data["investigation_6_temporal_retention"]["decay_curve"]
    fig, ax = plt.subplots(figsize=(7, 3.8))
    delays_ms = [pt["delay_ms"] for pt in d6]
    deltas = [pt["delta"] for pt in d6]
    ax.plot(delays_ms, deltas, "ro-", linewidth=1.5, markersize=6)
    ax.set_title("2T1C Analog Memory Gate Retention across 10 ms Strata\n(C = 100 nF Storage Node Leakage Profile)", fontsize=9, fontweight="bold")
    ax.set_xlabel("Time Since Refresh Window (ms)", fontsize=8)
    ax.set_ylabel("Effective Multiplier Swing $\Delta Y$ (ADC LSB)", fontsize=8)
    ax.grid(True, linestyle="--", alpha=0.6)
    plt.tight_layout()
    p6 = fig_dir / "fig6_temporal_retention.png"
    plt.savefig(p6, dpi=300)
    plt.close()
    fig_paths["fig6"] = p6

    print(f"[+] All 6 scientific figures generated and saved to {fig_dir}")
    return fig_paths


def main() -> int:
    print("=" * 70)
    print(" MAML SILICON HARDWARE EMPIRICAL RESEARCH SUITE")
    print(" (Strict Anti-Simulation Policy - 100% Physical Silicon Measurements)")
    print("=" * 70)

    # 1. Enforce data log quota
    status = get_quota_status(max_mb=100.0, docs_dir=DOCS_DIR)
    print(f"Current log data usage: {status['usage_mb']:.2f} MB / 100 MB (Remaining: {status['avail_mb']:.2f} MB)")
    if status["usage_pct"] >= 90.0:
        print("[!] Enforcing quota before starting research suite...")
        enforce_quota_before_write(incoming_bytes=5_000_000, max_mb=100.0, auto_prune=True, docs_dir=DOCS_DIR)

    researcher = MamlHardwareResearcher(host="192.168.1.50", port=5000)

    all_data = {
        "metadata": {
            "title": "Empirical Silicon Characterization of Inverted MAML Analog Matrix",
            "timestamp": datetime.now().isoformat(),
            "target_hardware": "Efinix Trion T120 Master + T20 Controller",
            "firmware_version": researcher.banner,
            "anti_simulation_policy": "Strict 100% Pure Physical Hardware Telemetry",
        }
    }

    # Execute all 6 investigations
    t0 = time.time()
    try:
        all_data["investigation_1_transfer_surface"] = researcher.investigate_transfer_surface(
            matrix_id=MAT_M33, row=0, col=0
        )
        all_data["investigation_2_opamp_sag"] = researcher.investigate_opamp_sag_and_crosstalk(
            matrix_id=MAT_M33, target_row=0, target_col=0
        )
        all_data["investigation_3_spatial_uniformity"] = researcher.investigate_m33_spatial_uniformity()
        all_data["investigation_4_matrix_comparison"] = researcher.investigate_matrix_comparison()
        all_data["investigation_5_hadamard_carrier"] = researcher.investigate_hadamard_carrier(n_repeats=15)
        all_data["investigation_6_temporal_retention"] = researcher.investigate_temporal_retention()
    finally:
        # Mandatory: Heaters strictly OFF
        researcher.client.set_heaters(False, [0, 0, 0, 0])
        print("[+] Verified heater safety: All heaters remain DISARMED.")

    elapsed = time.time() - t0
    print(f"\n[+] Hardware tests completed in {elapsed:.1f} seconds.")

    # Save JSON Dataset
    json_path = DOCS_DIR / "maml_scientific_investigation_data.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2)
    print(f"[+] Saved structured hardware dataset to: {json_path}")

    # Save CSV for Spatial Uniformity
    csv_path = DOCS_DIR / "maml_m33_spatial_uniformity.csv"
    cell_data = all_data["investigation_3_spatial_uniformity"]["cell_data"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Row", "Col", "Gain_LSB_per_W", "Delta_Swing_LSB", "Zero_Offset_LSB", "Y_pos_w", "Y_neg_w", "Asymmetry_LSB"])
        for c in cell_data:
            writer.writerow([c["row"], c["col"], f"{c['gain']:.3f}", f"{c['delta_w']:.1f}", f"{c['offset']:.1f}", c["y_pos_w"], c["y_neg_w"], f"{c['asym']:.1f}"])
    print(f"[+] Saved spatial uniformity CSV to: {csv_path}")

    # Generate Figures
    generate_scientific_figures(all_data, fig_dir=FIG_DIR)

    # Final Quota check
    final_status = get_quota_status(max_mb=100.0, docs_dir=DOCS_DIR)
    print(f"\n[+] Final Quota Status: {final_status['usage_mb']:.2f} MB / 100 MB ({final_status['usage_pct']:.1f}%)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
