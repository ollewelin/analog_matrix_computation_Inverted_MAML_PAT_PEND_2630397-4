"""
Real-Time 3D Loss Landscape & Basin Convergence Visualizer (Ref 40 vs Ref 41).

Pedagogically visualizes how the Inverted MAML Base Model Outer Loop (Ref 40)
uses the Dot-Product Second-Derivative (Hessian-Vector Product) to "push/gather
together" ("knuffa samman / samla ihop") the separate minimum-loss valleys
("gropar") from the Inner Loop (Ref 41) across thermal/process/voltage warps
into a unified central basin around W0 in high-dimensional weight space.

Provides both:
  1. An embedded Mini-Viewport widget for the Main GUI window.
  2. A detachable, interactive 3D Pop-Up Window with full controls and cross-sections.
"""

from __future__ import annotations
from typing import List, Optional
import numpy as np

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import matplotlib
matplotlib.use("Qt5Agg")
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

from gui.udp_client import MamlTelemetry, MamlUdpClient


VALLEY_LABELS = [
    "Ref 41 Valley 1 (20°C Baseline)",
    "Ref 41 Valley 2 (45°C Thermal Warp)",
    "Ref 41 Valley 3 (Gradient/Skew Warp)",
    "Ref 41 Valley 4 (Power Trim / Decay)",
]
VALLEY_COLORS = ["#00e5ff", "#ff6d00", "#76ff03", "#e040fb"]


class LossLandscape3DCanvas(FigureCanvas):
    """3D Surface + Contour Heatmap Canvas showing Ref 41 valleys converging to Ref 40 W0."""

    def __init__(self, compact: bool = False, parent: Optional[QWidget] = None):
        self.compact = compact
        figsize = (5.2, 3.8) if compact else (10.5, 7.2)
        self.fig = Figure(figsize=figsize, dpi=96, facecolor="#111622")
        super().__init__(self.fig)
        self.setParent(parent)

        if compact:
            self.ax3d = self.fig.add_subplot(111, projection="3d", facecolor="#111622")
            self.ax2d = None
            self.fig.subplots_adjust(left=0.02, right=0.98, bottom=0.04, top=0.90)
        else:
            self.ax3d = self.fig.add_subplot(121, projection="3d", facecolor="#111622")
            self.ax2d = self.fig.add_subplot(122, facecolor="#161c2a")
            self.fig.subplots_adjust(left=0.04, right=0.97, bottom=0.08, top=0.90, wspace=0.18)

        self.show_force_arrows = True
        self.show_trails = True
        self.elev = 34.0
        self.azim = -52.0

        # Precompute 2D PCA projection grid (u1, u2) in [-2.4, +2.4]
        res = 34 if compact else 48
        u = np.linspace(-2.4, 2.4, res)
        self.U1, self.U2 = np.meshgrid(u, u)

        # Keep historical trails of the 4 valleys
        self.trails: List[List[np.ndarray]] = [[] for _ in range(4)]

    def clear_trails(self) -> None:
        self.trails = [[] for _ in range(4)]

    def compute_loss_surface(
        self,
        valley_coords: np.ndarray,
        basin_loss_q14: List[int],
        comp_centered: bool,
    ) -> np.ndarray:
        """
        Synthesizes the projected 3D loss surface L(u1, u2) from the live K=4
        inner-loop task valleys (Ref 41) and the central Base Model W0 (Ref 40).
        """
        U1, U2 = self.U1, self.U2
        # Gentle global bowl confining the weight space
        Z = 0.82 + 0.11 * (U1 ** 2 + U2 ** 2)

        # Subtract Gaussian basins ("gropar") at each of the K=4 inner-loop task optima
        mean_dist = float(np.mean(np.linalg.norm(valley_coords, axis=1)))
        sigma = 0.46 if not comp_centered else 0.36

        for k in range(min(4, len(valley_coords))):
            vx, vy = float(valley_coords[k, 0]), float(valley_coords[k, 1])
            depth = 0.52 - min(0.28, (basin_loss_q14[k] / 16384.0) * 0.25)
            if comp_centered:
                depth *= 0.65
            r2 = (U1 - vx) ** 2 + (U2 - vy) ** 2
            Z -= depth * np.exp(-r2 / (2.0 * sigma ** 2))

        # Central Ref 40 Base Model W0 basin deepens as the second-derivative dot product
        # gathers the inner-loop valleys together at the origin!
        cohesion = max(0.0, 1.0 - mean_dist / 1.85)
        w0_depth = 0.25 + 0.55 * cohesion
        if comp_centered:
            w0_depth *= 0.35
        Z -= w0_depth * np.exp(-(U1 ** 2 + U2 ** 2) / (2.0 * (0.52 ** 2)))

        # Shift so minimum loss is positive and well-scaled in [0.05, 1.8]
        Z = Z - float(np.min(Z)) + 0.06
        return Z

    def update_landscape(
        self,
        valley_coords: np.ndarray,
        telemetry: MamlTelemetry,
        comp_centered: bool = False,
    ) -> None:
        # Record trajectory trails
        for k in range(4):
            pt = valley_coords[k].copy()
            if not self.trails[k] or float(np.linalg.norm(pt - self.trails[k][-1])) > 0.03:
                self.trails[k].append(pt)
                if len(self.trails[k]) > 35:
                    self.trails[k].pop(0)

        Z = self.compute_loss_surface(valley_coords, telemetry.basin_loss_q14, comp_centered)

        # Preserve interactive mouse rotation if user dragged the 3D axes
        if hasattr(self.ax3d, "elev") and self.ax3d.elev is not None:
            self.elev = self.ax3d.elev
            self.azim = self.ax3d.azim

        self.ax3d.cla()
        self.ax3d.set_facecolor("#111622")

        # 3D Heatmap Surface
        self.ax3d.plot_surface(
            self.U1,
            self.U2,
            Z,
            cmap="turbo",
            alpha=0.84,
            rstride=1,
            cstride=1,
            linewidth=0.15,
            edgecolor="#1e293b",
            antialiased=True,
        )

        # Bottom 2D contour heatmap floor projection
        z_floor = -0.15
        self.ax3d.contourf(
            self.U1,
            self.U2,
            Z,
            zdir="z",
            offset=z_floor,
            levels=14,
            cmap="turbo",
            alpha=0.65,
        )

        # Evaluate Z at each valley and at W0=(0,0)
        def eval_z(x: float, y: float) -> float:
            ix = int(np.argmin(np.abs(self.U1[0, :] - x)))
            iy = int(np.argmin(np.abs(self.U2[:, 0] - y)))
            return float(Z[iy, ix])

        z_w0 = eval_z(0.0, 0.0)
        # Plot Ref 40 Base Model W0 at the center
        self.ax3d.scatter(
            [0.0],
            [0.0],
            [z_w0 + 0.04],
            color="#ffd600",
            s=130 if self.compact else 210,
            marker="*",
            edgecolors="black",
            linewidths=1.2,
            zorder=10,
            label="Ref 40 Base Model W0 (Center)",
        )

        # Plot each of the K=4 Inner Loop (Ref 41) valleys ("gropar") + 2nd-derivative gather arrows
        for k in range(4):
            vx, vy = float(valley_coords[k, 0]), float(valley_coords[k, 1])
            vz = eval_z(vx, vy)
            self.ax3d.scatter(
                [vx],
                [vy],
                [vz + 0.03],
                color=VALLEY_COLORS[k],
                s=55 if self.compact else 95,
                edgecolors="white",
                linewidths=1.0,
                zorder=9,
                label=VALLEY_LABELS[k] if not self.compact else f"V{k+1}",
            )

            # Force arrow from Inner Loop Valley k toward Ref 40 W0 (2nd-derivative dot product)
            if self.show_force_arrows:
                dx = -0.45 * vx
                dy = -0.45 * vy
                dz = 0.45 * (z_w0 - vz)
                self.ax3d.quiver(
                    vx,
                    vy,
                    vz + 0.05,
                    dx,
                    dy,
                    dz,
                    color="#ffffff",
                    arrow_length_ratio=0.32,
                    linewidth=1.3 if self.compact else 2.0,
                )

        mean_dist = float(np.mean(np.linalg.norm(valley_coords, axis=1)))
        title_str = (
            f"3D Inverted MAML Loss Landscape (Epoch {telemetry.outer_epoch} | "
            f"Mean Basin Spread: {mean_dist:.2f})"
        )
        self.ax3d.set_title(
            title_str,
            color="#e2e8f0",
            fontsize=9.5 if self.compact else 11.5,
            fontweight="bold",
            pad=6,
        )
        self.ax3d.set_xlabel("Weight Subspace u₁", color="#94a3b8", fontsize=8)
        self.ax3d.set_ylabel("Weight Subspace u₂", color="#94a3b8", fontsize=8)
        self.ax3d.set_zlabel("Loss L(W)", color="#94a3b8", fontsize=8)
        self.ax3d.set_xlim(-2.4, 2.4)
        self.ax3d.set_ylim(-2.4, 2.4)
        self.ax3d.set_zlim(z_floor, float(np.max(Z)) + 0.15)
        self.ax3d.tick_params(colors="#94a3b8", labelsize=7)
        self.ax3d.view_init(elev=self.elev, azim=self.azim)

        # In Pop-Up Expanded Mode, also draw the 2D Top-Down Basin Convergence & Force-Field Map
        if self.ax2d is not None:
            self.ax2d.cla()
            self.ax2d.set_facecolor("#161c2a")
            self.ax2d.contourf(self.U1, self.U2, Z, levels=18, cmap="turbo", alpha=0.88)
            self.ax2d.contour(self.U1, self.U2, Z, levels=12, colors="#0f172a", linewidths=0.45, alpha=0.6)

            # Plot historical trajectory trails
            if self.show_trails:
                for k in range(4):
                    if len(self.trails[k]) >= 2:
                        arr = np.array(self.trails[k])
                        self.ax2d.plot(
                            arr[:, 0],
                            arr[:, 1],
                            "--",
                            color=VALLEY_COLORS[k],
                            linewidth=1.6,
                            alpha=0.85,
                        )

            # Plot valleys & 2nd-derivative gather vectors in 2D top-down view
            for k in range(4):
                vx, vy = float(valley_coords[k, 0]), float(valley_coords[k, 1])
                self.ax2d.scatter(
                    [vx],
                    [vy],
                    color=VALLEY_COLORS[k],
                    s=110,
                    edgecolors="white",
                    linewidths=1.2,
                    zorder=8,
                    label=VALLEY_LABELS[k],
                )
                if self.show_force_arrows:
                    self.ax2d.annotate(
                        "",
                        xy=(vx * 0.42, vy * 0.42),
                        xytext=(vx, vy),
                        arrowprops=dict(arrowstyle="->", color="#ffffff", lw=2.0),
                    )

            self.ax2d.scatter(
                [0.0],
                [0.0],
                color="#ffd600",
                s=240,
                marker="*",
                edgecolors="black",
                linewidths=1.3,
                zorder=10,
                label="Ref 40 Base Model W₀ (2nd-Deriv Target)",
            )
            self.ax2d.set_title(
                "Top-Down Heatmap: Ref 40 2nd-Derivative Gathering Ref 41 Valleys ('Gropar')",
                color="#e2e8f0",
                fontsize=10.5,
                fontweight="bold",
            )
            self.ax2d.set_xlabel("Projected Weight Axis u₁ (PCA-1)", color="#cbd5e1", fontsize=9)
            self.ax2d.set_ylabel("Projected Weight Axis u₂ (PCA-2)", color="#cbd5e1", fontsize=9)
            self.ax2d.tick_params(colors="#94a3b8", labelsize=8)
            self.ax2d.legend(loc="upper right", fontsize=7.5, facecolor="#0f172a", edgecolor="#334155", labelcolor="#f8fafc")

        self.draw_idle()


class LossLandscapePopUpWindow(QMainWindow):
    """
    Detachable / Expandable Pop-Up Window for the 3D Inverted MAML Loss Landscape.
    Allows deep pedagogical exploration of how the Outer Loop (Ref 40) second-derivative
    dot product pulls the Inner Loop (Ref 41) minimum-loss valleys together.
    """

    def __init__(self, client: MamlUdpClient, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.client = client
        self.setWindowTitle(
            "Inverted MAML 3D Loss Landscape Visualizer — Ref 40 Base Model Gathering Ref 41 Valleys"
        )
        self.resize(1220, 760)
        self.setStyleSheet("background-color: #0f172a; color: #f8fafc;")

        central = QWidget(self)
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)

        # Pedagogical explanation banner
        banner = QLabel(
            "<b>Pedagogical View (Patent SE 2630397-4):</b> Each colored basin ('grop') is the minimum-loss optimum "
            "of an <b>Inner Loop (Ref 41)</b> task under a specific thermal/process/decay warp. "
            "White arrows show the <b>Outer Loop (Ref 40) Dot-Product Second Derivative (Hessian-Vector Product)</b> "
            "gathering all inner-loop valleys inward toward the central Base Model <b>W₀ (Gold Star)</b>."
        )
        banner.setWordWrap(True)
        banner.setStyleSheet(
            "background-color: #1e293b; color: #e2e8f0; padding: 8px; border-radius: 6px; border: 1px solid #334155;"
        )
        layout.addWidget(banner)

        # 3D + 2D Canvas
        self.canvas = LossLandscape3DCanvas(compact=False, parent=self)
        layout.addWidget(self.canvas, stretch=1)

        # Interactive control bar
        ctrl_bar = QHBoxLayout()
        self.chk_arrows = QCheckBox("Show Ref 40 2nd-Derivative Force Arrows")
        self.chk_arrows.setChecked(True)
        self.chk_arrows.stateChanged.connect(self._on_toggle_opts)
        ctrl_bar.addWidget(self.chk_arrows)

        self.chk_trails = QCheckBox("Show Basin Convergence Trails")
        self.chk_trails.setChecked(True)
        self.chk_trails.stateChanged.connect(self._on_toggle_opts)
        ctrl_bar.addWidget(self.chk_trails)

        btn_iso = QPushButton("Isometric 3D View")
        btn_iso.setStyleSheet("background-color: #334155; padding: 6px 12px; border-radius: 4px;")
        btn_iso.clicked.connect(lambda: self._set_cam(34.0, -52.0))
        ctrl_bar.addWidget(btn_iso)

        btn_top = QPushButton("Top-Down 3D Heatmap")
        btn_top.setStyleSheet("background-color: #334155; padding: 6px 12px; border-radius: 4px;")
        btn_top.clicked.connect(lambda: self._set_cam(82.0, -90.0))
        ctrl_bar.addWidget(btn_top)

        btn_side = QPushButton("Valley Depth Cross-Section")
        btn_side.setStyleSheet("background-color: #334155; padding: 6px 12px; border-radius: 4px;")
        btn_side.clicked.connect(lambda: self._set_cam(12.0, -35.0))
        ctrl_bar.addWidget(btn_side)

        btn_step = QPushButton("Step Outer Loop (Ref 40 Gather Valleys)")
        btn_step.setStyleSheet("background-color: #0284c7; font-weight: bold; padding: 6px 14px; border-radius: 4px;")
        btn_step.clicked.connect(self._on_step_outer)
        ctrl_bar.addWidget(btn_step)

        btn_spread = QPushButton("Re-Spread Inner Valleys (Reset Demo)")
        btn_spread.setStyleSheet("background-color: #475569; padding: 6px 12px; border-radius: 4px;")
        btn_spread.clicked.connect(self._on_respread)
        ctrl_bar.addWidget(btn_spread)

        layout.addLayout(ctrl_bar)

    def _on_toggle_opts(self) -> None:
        self.canvas.show_force_arrows = self.chk_arrows.isChecked()
        self.canvas.show_trails = self.chk_trails.isChecked()
        self.refresh_view()

    def _set_cam(self, elev: float, azim: float) -> None:
        self.canvas.elev = elev
        self.canvas.azim = azim
        self.canvas.ax3d.view_init(elev=elev, azim=azim)
        self.refresh_view()

    def _on_step_outer(self) -> None:
        self.client.step_outer_loop()
        self.refresh_view()

    def _on_respread(self) -> None:
        self.canvas.clear_trails()
        self.client.reset_valleys_spread()
        self.refresh_view()

    def refresh_view(self) -> None:
        self.canvas.update_landscape(
            self.client.valley_coords,
            self.client.sim_telemetry,
            self.client.sim_comp_centered,
        )

