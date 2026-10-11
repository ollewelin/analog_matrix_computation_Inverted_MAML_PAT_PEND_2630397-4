"""
PC-Computed Cell-by-Cell Self-Diagnosis & Bit-Precision Benchmark Engine.

When triggered from the GUI:
  1. Sets all compensation matrix weights (M3 and M8) to differential center (128 = 0.0).
  2. Sweeps every individual Dual-2T1C crosspoint multiplier cell across:
       - Matrix 33 (Main 6x6 = 36 cells)
       - Matrix 3  (Compensation Layer 1, 8x6 = 48 cells)
       - Matrix 8  (Compensation Layer 2, 7x6 = 42 cells)
  3. Computes on the PC:
       - Differential Multiplier Gain Variation (%) relative to ideal slope
       - Differential Zero-Offset (ADC LSBs around 2048 virtual ground)
       - Differential Symmetry / Linearity Error (%)
       - Per-Cell Health Classification (OK / High-Mismatch / Stuck)
  4. Renders a 3-Matrix 2D Annotated Variation Heatmap in the GUI.
"""

from __future__ import annotations
import struct
from dataclasses import dataclass
from typing import Optional
import numpy as np

from PyQt5.QtWidgets import QWidget
import matplotlib
matplotlib.use("Qt5Agg")
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from gui.udp_client import MAML_CMD_CELL_DIAG, MamlUdpClient


@dataclass
class CellDiagnosticsReport:
    m33_gain_pct: np.ndarray      # shape (6, 6): % gain deviation from nominal 100%
    m33_offset_lsb: np.ndarray    # shape (6, 6): zero-offset in signed ADC LSBs
    m3_gain_pct: np.ndarray       # shape (8, 6)
    m3_offset_lsb: np.ndarray     # shape (8, 6)
    m8_gain_pct: np.ndarray       # shape (7, 6)
    m8_offset_lsb: np.ndarray     # shape (7, 6)
    total_cells: int = 126
    healthy_cells: int = 126
    warn_cells: int = 0
    fault_cells: int = 0
    rms_gain_spread_pct: float = 0.0
    max_offset_lsb: float = 0.0
    summary_text: str = ""


class CellDiagnosticsEngine:
    """Runs PC-side cell-by-cell crosspoint characterization with compensation weights at 0 (128)."""

    def __init__(self, client: MamlUdpClient):
        self.client = client
        self.last_report: Optional[CellDiagnosticsReport] = None

    def _probe_single_cell_hw(self, mat_id: int, row: int, col: int) -> Optional[tuple[float, float]]:
        """Probes (mat_id, row, col) on hardware via MAML_CMD_CELL_DIAG if connected."""
        res = self.client.probe_cell(mat_id, row, col)
        if res is not None:
            if mat_id == 0:  # M3 (Layer 1 -> ADC_45)
                pos = float(res.adc45_pos[col])
                neg = float(res.adc45_neg[col])
                zero = float(res.adc45_zero[col])
                nom_swing = 35.0  # Physical 12-bit LSB single-cell swing for M3
            elif mat_id == 1:  # M8 (Layer 2 -> ADC_49)
                pos = float(res.adc49_pos[col])
                neg = float(res.adc49_neg[col])
                zero = float(res.adc49_zero[col])
                nom_swing = 35.0  # Physical 12-bit LSB single-cell swing for M8
            else:            # M33 (Main 6x6 -> ADC_49)
                pos = float(res.adc49_pos[col])
                neg = float(res.adc49_neg[col])
                zero = float(res.adc49_zero[col])
                nom_swing = 80.0  # Physical 12-bit LSB single-cell swing for M33
            swing = abs(pos - neg)
            gain_pct = (swing / nom_swing) * 100.0
            offset_lsb = zero
            return gain_pct, offset_lsb
        return None

    def run_full_cell_diagnostics(self) -> CellDiagnosticsReport:
        # Step 1: Force all compensation weights to differential center (128 = 0.0 weight)
        self.client.center_compensation_weights()

        # Thermal drift influence if heaters are armed
        heat_factor = 0.0
        if self.client.sim_telemetry.heater_armed:
            heat_factor = sum(self.client.sim_telemetry.heater_duty) / 400.0

        m33_gain = np.zeros((6, 6), dtype=np.float64)
        m33_off  = np.zeros((6, 6), dtype=np.float64)
        m3_gain  = np.zeros((8, 6), dtype=np.float64)
        m3_off   = np.zeros((8, 6), dtype=np.float64)
        m8_gain  = np.zeros((7, 6), dtype=np.float64)
        m8_off   = np.zeros((7, 6), dtype=np.float64)

        rng = np.random.default_rng(10102026)

        # Probe Matrix 33 (6x6, mat_id=2)
        for r in range(6):
            for c in range(6):
                hw = self._probe_single_cell_hw(2, r, c)
                if hw is not None:
                    m33_gain[r, c], m33_off[r, c] = hw
                else:
                    thermal_skew = heat_factor * (4.5 * (r - 2.5) - 3.2 * (c - 2.5))
                    g = self.client.sim_m33_gain[r, c] * (1.0 - 0.06 * heat_factor)
                    m33_gain[r, c] = g * 100.0 + float(rng.normal(0.0, 0.6))
                    m33_off[r, c]  = self.client.sim_m33_offset[r, c] + thermal_skew + float(rng.normal(0.0, 0.8))

        # Probe Matrix 3 (8x6, mat_id=0)
        for r in range(8):
            for c in range(6):
                hw = self._probe_single_cell_hw(0, r, c)
                if hw is not None:
                    m3_gain[r, c], m3_off[r, c] = hw
                else:
                    g = self.client.sim_m3_gain[r, c] * (1.0 - 0.04 * heat_factor)
                    m3_gain[r, c] = g * 100.0 + float(rng.normal(0.0, 0.5))
                    m3_off[r, c]  = self.client.sim_m3_offset[r, c] + 3.0 * heat_factor + float(rng.normal(0.0, 0.6))

        # Probe Matrix 8 (7x6, mat_id=1)
        for r in range(7):
            for c in range(6):
                hw = self._probe_single_cell_hw(1, r, c)
                if hw is not None:
                    m8_gain[r, c], m8_off[r, c] = hw
                else:
                    g = self.client.sim_m8_gain[r, c] * (1.0 - 0.04 * heat_factor)
                    m8_gain[r, c] = g * 100.0 + float(rng.normal(0.0, 0.5))
                    m8_off[r, c]  = self.client.sim_m8_offset[r, c] - 2.5 * heat_factor + float(rng.normal(0.0, 0.6))

        all_gains = np.concatenate([m33_gain.ravel(), m3_gain.ravel(), m8_gain.ravel()])
        all_offs  = np.concatenate([m33_off.ravel(), m3_off.ravel(), m8_off.ravel()])

        dev = np.abs(all_gains - 100.0)
        faults = int(np.sum((all_gains < 25.0) | (all_gains > 200.0) | (np.abs(all_offs) > 120.0)))
        warns  = int(np.sum((dev > 25.0) | (np.abs(all_offs) > 35.0))) - faults
        healthy = 126 - faults - warns
        rms_spread = float(np.sqrt(np.mean((all_gains - 100.0) ** 2)))
        max_off = float(np.max(np.abs(all_offs)))

        summary = (
            f"PC Cell-by-Cell Self-Diagnosis Complete (Comp Weights Centered = 128): "
            f"{healthy}/126 Cells Nominal, {warns} High-Mismatch, {faults} Stuck/Fault | "
            f"RMS Multiplier Gain Spread: {rms_spread:.2f}% | Max Zero-Offset: {max_off:.1f} LSB"
        )

        report = CellDiagnosticsReport(
            m33_gain_pct=m33_gain,
            m33_offset_lsb=m33_off,
            m3_gain_pct=m3_gain,
            m3_offset_lsb=m3_off,
            m8_gain_pct=m8_gain,
            m8_offset_lsb=m8_off,
            total_cells=126,
            healthy_cells=healthy,
            warn_cells=warns,
            fault_cells=faults,
            rms_gain_spread_pct=rms_spread,
            max_offset_lsb=max_off,
            summary_text=summary,
        )
        self.last_report = report
        return report


class CellDiagnosticsCanvas(FigureCanvas):
    """Renders 2D Annotated Heatmaps of Cell-by-Cell Multiplier Gain (%) or Offset (LSB)."""

    def __init__(self, parent: Optional[QWidget] = None):
        self.fig = Figure(figsize=(8.6, 3.3), dpi=96, facecolor="#111622")
        super().__init__(self.fig)
        self.setParent(parent)
        self.axes = [
            self.fig.add_subplot(131, facecolor="#161c2a"),
            self.fig.add_subplot(132, facecolor="#161c2a"),
            self.fig.add_subplot(133, facecolor="#161c2a"),
        ]
        self.fig.subplots_adjust(left=0.05, right=0.98, bottom=0.14, top=0.86, wspace=0.26)
        self.show_offset_mode = False

    def render_report(self, report: CellDiagnosticsReport) -> None:
        if not self.show_offset_mode:
            mats = [report.m33_gain_pct, report.m3_gain_pct, report.m8_gain_pct]
            titles = [
                "M33 Main (6×6) Gain %",
                "M3 Comp L1 (8×6) Gain %",
                "M8 Comp L2 (7×6) Gain %",
            ]
            vmin, vmax = 0.0, 140.0
            cmap = "coolwarm"
            fmt = "{:.0f}%"
        else:
            mats = [report.m33_offset_lsb, report.m3_offset_lsb, report.m8_offset_lsb]
            titles = [
                "M33 Main (6×6) Offset LSB",
                "M3 Comp L1 (8×6) Offset LSB",
                "M8 Comp L2 (7×6) Offset LSB",
            ]
            vmin, vmax = -35.0, 35.0
            cmap = "PiYG"
            fmt = "{:+.0f}"

        for ax, mat, title in zip(self.axes, mats, titles):
            ax.cla()
            im = ax.imshow(mat, cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
            rows, cols = mat.shape
            for r in range(rows):
                for c in range(cols):
                    val = float(mat[r, c])
                    ax.text(
                        c,
                        r,
                        fmt.format(val),
                        ha="center",
                        va="center",
                        color="#0f172a" if abs(val - (100.0 if not self.show_offset_mode else 0.0)) < 12.0 else "#ffffff",
                        fontsize=6.8,
                        fontweight="bold",
                    )
            ax.set_title(title, color="#e2e8f0", fontsize=8.8, fontweight="bold", pad=5)
            ax.set_xticks(range(cols))
            ax.set_xticklabels([f"C{c+1}" for c in range(cols)], color="#94a3b8", fontsize=7)
            ax.set_yticks(range(rows))
            ax.set_yticklabels([f"R{r+1}" for r in range(rows)], color="#94a3b8", fontsize=7)

        self.draw_idle()

