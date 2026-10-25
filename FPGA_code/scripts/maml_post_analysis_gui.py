#!/home/olle/anaconda3/bin/python
"""
Post-Data Analysis & Multi-Dimensional Visualization GUI
========================================================
Interactive graphical suite for deep empirical inspection of Inverted MAML Mode A
physical silicon training and temporal window experiments.

Features:
  - Step-by-step Epoch slider & playback animation (Play / Pause / Speed).
  - 3D Weight Surface Topography (Matrix 33 static target, Matrix 3, Matrix 8).
  - 3D Convergence Trajectory in State Space (RMSE, Loss, ENOB).
  - 2D Signal Flow & Triad Summation Window:
      In-Vector X -> M33 Raw -> M3/M8 Vernier Compensation -> Passive Summing -> ENOB.
  - Multi-Strata Temporal Leakage Map across [t_min .. t_max].
"""

from __future__ import annotations
import json
import math
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont, QIcon, QColor
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSlider,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import matplotlib
matplotlib.use("Qt5Agg")
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_JSON = REPO_ROOT / "FPGA_code" / "logs" / "mode_a_extended_training" / "mode_a_extended_training_telemetry.json"
TEST_JSON = REPO_ROOT / "FPGA_code" / "logs" / "mode_a_extended_training" / "test_trial_3epochs.json"


class Matrix3PopupWindow(QDialog):
    """Independent Pop-Up Window displaying 3D Topography of Matrix 3 (Layer 1 Projection)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Matrix 3 (Layer 1 Projection / Hidden Layer) — 3D Topography")
        self.resize(1180, 620)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        self.fig = Figure(figsize=(11.5, 5.8), dpi=100)
        self.fig.patch.set_facecolor("#f8f9fa")
        self.canvas = FigureCanvas(self.fig)
        layout.addWidget(self.canvas)

    def update_epoch(self, rec: dict, baseline_rec: Optional[dict] = None):
        self.fig.clear()
        w_m3 = np.array(rec.get("w_m3", np.zeros((8, 6))))
        if baseline_rec is not None:
            w_m3_0 = np.array(baseline_rec.get("w_m3", np.zeros((8, 6))))
        else:
            w_m3_0 = np.zeros((8, 6))
            for c in range(6):
                w_m3_0[c, c] = 64
                w_m3_0[6, c] = 48
        delta_m3 = w_m3 - w_m3_0
        X, Y = np.meshgrid(np.arange(6), np.arange(8))

        ax1 = self.fig.add_subplot(121, projection="3d")
        ax1.plot_surface(X, Y, delta_m3, cmap="coolwarm", edgecolor="k", linewidth=0.5, alpha=0.9)
        ax1.set_title(f"Matrix 3 Learned ΔW3 (vs Ep 0) — Epoch {rec.get('epoch', 0)}", fontsize=11, fontweight="bold")
        ax1.set_xlabel("Columns 0..5")
        ax1.set_ylabel("Rows 0..7")
        ax1.set_zlabel("ΔWeight (LSB)")
        ax1.set_zlim(-25, 25)

        ax2 = self.fig.add_subplot(122, projection="3d")
        ax2.plot_surface(X, Y, w_m3, cmap="plasma", edgecolor="k", linewidth=0.5, alpha=0.9)
        ax2.set_title(f"Matrix 3 Absolute W3 — Epoch {rec.get('epoch', 0)}", fontsize=11, fontweight="bold")
        ax2.set_xlabel("Columns 0..5")
        ax2.set_ylabel("Rows 0..7")
        ax2.set_zlabel("Weight W (LSB)")
        ax2.set_zlim(-25, 85)

        self.fig.tight_layout()
        self.canvas.draw()


class MamlPostAnalysisGUI(QMainWindow):
    def __init__(self, json_path: Optional[str] = None):
        super().__init__()
        self.setWindowTitle("Inverted MAML: Mode A Post-Data Analysis & 3D Telemetry Studio")
        self.resize(1500, 950)

        self.dataset = None
        self.epochs_data: List[dict] = []
        self.static_m33 = np.zeros((6, 6))
        self.current_idx = 0
        self.is_playing = False
        self.m3_popup: Optional[Matrix3PopupWindow] = None

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_play_step)

        self._init_ui()

        # Load initial file if provided or available
        target_path = json_path or (str(DEFAULT_JSON) if DEFAULT_JSON.exists() else str(TEST_JSON) if TEST_JSON.exists() else None)
        if target_path and os.path.exists(target_path):
            self.load_dataset(target_path)

    def _init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # --- Top Header & Controls Panel ---
        ctrl_box = QGroupBox("Experiment Controls & Playback")
        ctrl_layout = QHBoxLayout(ctrl_box)

        self.btn_load = QPushButton("📂 Load Data JSON")
        self.btn_load.clicked.connect(self._on_browse_file)
        ctrl_layout.addWidget(self.btn_load)

        self.lbl_file_info = QLabel("No dataset loaded")
        self.lbl_file_info.setStyleSheet("color: #2b5797; font-weight: bold;")
        ctrl_layout.addWidget(self.lbl_file_info, stretch=1)

        self.btn_play = QPushButton("▶ Play Animation")
        self.btn_play.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 6px 12px;")
        self.btn_play.clicked.connect(self._toggle_playback)
        ctrl_layout.addWidget(self.btn_play)

        ctrl_layout.addWidget(QLabel("Speed (ms):"))
        self.spin_speed = QSpinBox()
        self.spin_speed.setRange(20, 2000)
        self.spin_speed.setValue(150)
        ctrl_layout.addWidget(self.spin_speed)

        ctrl_layout.addWidget(QLabel("Epoch:"))
        self.slider_epoch = QSlider(Qt.Horizontal)
        self.slider_epoch.setRange(0, 0)
        self.slider_epoch.valueChanged.connect(self._on_slider_changed)
        ctrl_layout.addWidget(self.slider_epoch, stretch=2)

        self.lbl_epoch_val = QLabel("0 / 0")
        self.lbl_epoch_val.setFont(QFont("Monospace", 10, QFont.Bold))
        ctrl_layout.addWidget(self.lbl_epoch_val)

        main_layout.addWidget(ctrl_box)

        # --- Main Splitter: Left 3D Visualizer, Right 2D Signal Flow & Metrics ---
        splitter = QSplitter(Qt.Horizontal)

        # === Left Panel: 3D Graphics ===
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # Matplotlib 3D Canvas
        self.fig_3d = Figure(figsize=(7, 7), dpi=100)
        self.fig_3d.patch.set_facecolor("#f8f9fa")
        self.canvas_3d = FigureCanvas(self.fig_3d)
        left_layout.addWidget(self.canvas_3d, stretch=1)

        # Selector for 3D View mode
        view_sel_layout = QHBoxLayout()
        view_sel_layout.addWidget(QLabel("3D View Topography:"))
        self.combo_3d_view = QComboBox()
        self.combo_3d_view.addItems([
            "3D Matrix 8 (Active Vernier Layer)",
            "3D Matrix 3 (Hidden Projection Layer)",
            "3D Matrix 33 (Static Frozen Primary Payload)",
            "3D Multi-Strata Temporal Loss Landscape",
        ])
        self.combo_3d_view.currentIndexChanged.connect(self._update_plots)
        view_sel_layout.addWidget(self.combo_3d_view)

        self.btn_m3_popup = QPushButton("🪟 Pop-up 3D Matrix 3")
        self.btn_m3_popup.setToolTip("Open independent synchronized 3D window for Matrix 3")
        self.btn_m3_popup.setStyleSheet("background-color: #5c6bc0; color: white; font-weight: bold; padding: 4px 10px; border-radius: 4px;")
        self.btn_m3_popup.clicked.connect(self._open_m3_popup)
        view_sel_layout.addWidget(self.btn_m3_popup)

        left_layout.addLayout(view_sel_layout)

        splitter.addWidget(left_widget)

        # === Right Panel: 2D Signal Flow, Convergence Charts & Numerics ===
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # 2D Convergence Charts Canvas
        self.fig_2d = Figure(figsize=(7, 4), dpi=100)
        self.fig_2d.patch.set_facecolor("#f8f9fa")
        self.canvas_2d = FigureCanvas(self.fig_2d)
        right_layout.addWidget(self.canvas_2d, stretch=2)

        # Numerical Matrix & Vector Flow Box
        flow_box = QGroupBox("Signal Flow & Real-Time Numerics (Current Epoch)")
        flow_layout = QGridLayout(flow_box)

        self.table_signal = QTableWidget(6, 6)
        self.table_signal.setHorizontalHeaderLabels(["Input X", "Z Target", "M33 (ADC45)", "Triad (ADC49)", "Error", "M8 Diag W"])
        self.table_signal.setVerticalHeaderLabels([f"Col {c}" for c in range(6)])
        self.table_signal.horizontalHeader().setStretchLastSection(True)
        flow_layout.addWidget(self.table_signal, 0, 0, 1, 2)

        # Metrics Labels
        self.lbl_enob = QLabel("ENOB: -- bits")
        self.lbl_enob.setStyleSheet("font-size: 14px; font-weight: bold; color: #2e7d32;")
        flow_layout.addWidget(self.lbl_enob, 1, 0)

        self.lbl_rmse = QLabel("RMSE: -- LSB | Loss: --")
        self.lbl_rmse.setStyleSheet("font-size: 13px; font-weight: bold; color: #1565c0;")
        flow_layout.addWidget(self.lbl_rmse, 1, 1)

        right_layout.addWidget(flow_box, stretch=1)
        splitter.addWidget(right_widget)

        splitter.setSizes([750, 750])
        main_layout.addWidget(splitter, stretch=1)

    def load_dataset(self, file_path: str):
        try:
            with open(file_path, "r") as f:
                self.dataset = json.load(f)
            self.epochs_data = self.dataset.get("epochs", [])
            meta = self.dataset.get("metadata", {})
            self.static_m33 = np.array(self.dataset.get("static_weights", {}).get("w_m33", np.zeros((6, 6))))

            n_epochs = len(self.epochs_data)
            self.slider_epoch.setRange(0, max(0, n_epochs - 1))
            self.slider_epoch.setValue(0)
            self.current_idx = 0

            info = (
                f"Loaded: {os.path.basename(file_path)} | "
                f"Epochs: {n_epochs} | "
                f"Window: [{meta.get('t_min_ms', 5.0):.1f} - {meta.get('t_max_ms', 5.0):.1f}] ms | "
                f"LR Scale: {meta.get('lr_scale', 1.0)}"
            )
            self.lbl_file_info.setText(info)
            self._update_all()
        except Exception as e:
            self.lbl_file_info.setText(f"Error loading {os.path.basename(file_path)}: {e}")

    def _on_browse_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Telemetry JSON", str(REPO_ROOT / "FPGA_code" / "logs"), "JSON Files (*.json)")
        if path:
            self.load_dataset(path)

    def _toggle_playback(self):
        if self.is_playing:
            self.timer.stop()
            self.is_playing = False
            self.btn_play.setText("▶ Play Animation")
            self.btn_play.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 6px 12px;")
        else:
            if not self.epochs_data:
                return
            self.timer.start(self.spin_speed.value())
            self.is_playing = True
            self.btn_play.setText("⏸ Pause Animation")
            self.btn_play.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; padding: 6px 12px;")

    def _on_play_step(self):
        if not self.epochs_data:
            return
        nxt = self.current_idx + 1
        if nxt >= len(self.epochs_data):
            nxt = 0
        self.slider_epoch.setValue(nxt)

    def _on_slider_changed(self, val: int):
        self.current_idx = val
        self.lbl_epoch_val.setText(f"{val} / {max(0, len(self.epochs_data) - 1)}")
        self._update_all()

    def _update_all(self):
        if not self.epochs_data or self.current_idx >= len(self.epochs_data):
            return
        rec = self.epochs_data[self.current_idx]
        self._update_table_and_metrics(rec)
        self._update_plots()

    def _update_table_and_metrics(self, rec: dict):
        x_ref = rec.get("x_ref", [0] * 6)
        z_target = rec.get("z_target", [0] * 6)
        adc45 = rec.get("adc45", [0] * 6)
        adc49 = rec.get("adc49", [0] * 6)
        err49 = rec.get("err49", [0] * 6)
        w8_diag = rec.get("w8_diag", [0] * 6)

        for col in range(6):
            vals = [
                f"{x_ref[col]:+d}",
                f"{z_target[col]:.1f}",
                f"{adc45[col]:.1f}",
                f"{adc49[col]:.1f}",
                f"{err49[col]:+.1f}",
                f"{w8_diag[col]:+d}",
            ]
            for r, v in enumerate(vals):
                item = QTableWidgetItem(v)
                item.setTextAlignment(Qt.AlignCenter)
                if r == 4: # Error column
                    err_val = abs(err49[col])
                    if err_val < 20:
                        item.setBackground(QColor("#c8e6c9"))
                    elif err_val < 60:
                        item.setBackground(QColor("#fff9c4"))
                    else:
                        item.setBackground(QColor("#ffcdd2"))
                self.table_signal.setItem(col, r, item)

        enob = rec.get("enob_bits", 0.0)
        rmse = rec.get("rmse_lsb", 0.0)
        loss = rec.get("loss_lsb2", 0.0)
        w_enob = rec.get("window_mean_enob_bits")
        base_ep = self.dataset.get("metadata", {}).get("baseline_epochs", 0)
        vec_id = rec.get("vector_id")
        phase = rec.get("phase", "BASELINE" if rec.get("epoch", 0) <= base_ep and base_ep > 0 else "TRAINING")
        eff_lr = rec.get("effective_lr", 0.0 if phase == "BASELINE" else self.dataset.get("metadata", {}).get("active_lr_scale", 0.2))

        if vec_id:
            phase_tag = f"[Vector {vec_id} | Ep {rec.get('epoch', 0)}] "
        elif base_ep > 0:
            phase_tag = f"[{phase} | LR={eff_lr:.2f}] "
        else:
            phase_tag = ""

        enob_txt = f"{phase_tag}Nominal 5ms ENOB: {enob:.2f} bits"
        if w_enob is not None:
            enob_txt += f" | Window Mean ENOB: {w_enob:.2f} bits"
        self.lbl_enob.setText(enob_txt)
        if phase == "BASELINE":
            self.lbl_enob.setStyleSheet("font-weight: bold; color: #795548;")
        elif vec_id == "A":
            self.lbl_enob.setStyleSheet("font-weight: bold; color: #1565c0;")
        elif vec_id == "B":
            self.lbl_enob.setStyleSheet("font-weight: bold; color: #00695c;")
        else:
            self.lbl_enob.setStyleSheet("font-weight: bold; color: #2e7d32;")
        self.lbl_rmse.setText(f"RMSE: {rmse:.2f} LSB | Quadratic Loss: {loss:.1f} LSB²")

    def _open_m3_popup(self):
        if self.m3_popup is None:
            self.m3_popup = Matrix3PopupWindow(self)
        if self.epochs_data:
            self.m3_popup.update_epoch(self.epochs_data[self.current_idx], self.epochs_data[0])
        self.m3_popup.show()
        self.m3_popup.raise_()

    def _update_plots(self):
        if not self.epochs_data:
            return
        rec = self.epochs_data[self.current_idx]

        if self.m3_popup and self.m3_popup.isVisible():
            self.m3_popup.update_epoch(rec, self.epochs_data[0])

        # 1. --- Update 3D Topography Plot ---
        self.fig_3d.clear()
        ax_3d = self.fig_3d.add_subplot(111, projection="3d")
        view_mode = self.combo_3d_view.currentIndex()

        if view_mode == 0: # M8 Vernier
            w_m8 = np.array(rec.get("w_m8", np.zeros((7, 6))))
            X, Y = np.meshgrid(np.arange(6), np.arange(7))
            surf = ax_3d.plot_surface(X, Y, w_m8, cmap="viridis", edgecolor="k", linewidth=0.5, alpha=0.9)
            ax_3d.set_title(f"Matrix 8 (Vernier Layer) — Epoch {rec.get('epoch', 0)}", fontsize=11, fontweight="bold")
            ax_3d.set_xlabel("Columns 0..5")
            ax_3d.set_ylabel("Rows 0..6")
            ax_3d.set_zlabel("Weight W (LSB)")
            ax_3d.set_zlim(-50, 50)
        elif view_mode == 1: # M3 Hidden
            w_m3 = np.array(rec.get("w_m3", np.zeros((8, 6))))
            X, Y = np.meshgrid(np.arange(6), np.arange(8))
            surf = ax_3d.plot_surface(X, Y, w_m3, cmap="plasma", edgecolor="k", linewidth=0.5, alpha=0.9)
            ax_3d.set_title(f"Matrix 3 (Hidden Layer) — Epoch {rec.get('epoch', 0)}", fontsize=11, fontweight="bold")
            ax_3d.set_xlabel("Columns 0..5")
            ax_3d.set_ylabel("Rows 0..7")
            ax_3d.set_zlabel("Weight W (LSB)")
        elif view_mode == 2: # M33 Static
            X, Y = np.meshgrid(np.arange(6), np.arange(6))
            surf = ax_3d.plot_surface(X, Y, self.static_m33, cmap="coolwarm", edgecolor="k", linewidth=0.5, alpha=0.9)
            ax_3d.set_title("Matrix 33 (Frozen Static Target Matrix)", fontsize=11, fontweight="bold")
            ax_3d.set_xlabel("Columns 0..5")
            ax_3d.set_ylabel("Rows 0..5")
            ax_3d.set_zlabel("Weight W (LSB)")
        else: # Multi-strata
            samples = sorted(rec.get("strata_samples", []), key=lambda s: s["t_us"])
            if samples:
                times = [s["t_us"] / 1000.0 for s in samples]
                cols = np.arange(6)
                T, C = np.meshgrid(times, cols)
                err_mat = np.array([[abs(s["err49"][c]) for s in samples] for c in range(6)])
                surf = ax_3d.plot_surface(T, C, err_mat, cmap="magma", edgecolor="k", linewidth=0.5, alpha=0.85)
                ax_3d.set_title(f"Temporal Error Across Window — Epoch {rec.get('epoch', 0)}", fontsize=11, fontweight="bold")
                ax_3d.set_xlabel("Snapshot Time (ms)")
                ax_3d.set_ylabel("Column Index")
                ax_3d.set_zlabel("|Error| (LSB)")
            else:
                ax_3d.text(0.5, 0.5, 0.5, "Single Delay Mode (No Strata Sweep)", ha="center")

        self.canvas_3d.draw()

        # 2. --- Update 2D Trajectory & Convergence Plot ---
        self.fig_2d.clear()
        ax_loss = self.fig_2d.add_subplot(311)
        ax_rmse = self.fig_2d.add_subplot(312)
        ax_w8   = self.fig_2d.add_subplot(313)

        epochs = [e.get("epoch", i) for i, e in enumerate(self.epochs_data)]
        rmses = [e.get("rmse_lsb", 0) for e in self.epochs_data]
        enobs = [e.get("enob_bits", 0) for e in self.epochs_data]
        losses = [e.get("loss_lsb2", e.get("loss_milli", 0)) for e in self.epochs_data]
        base_ep = self.dataset.get("metadata", {}).get("baseline_epochs", 0)

        # Visual indicator for baseline phase (LR=0)
        if base_ep > 0:
            for ax in [ax_loss, ax_rmse, ax_w8]:
                ax.axvspan(0, base_ep, color="#ebebeb", alpha=0.65, zorder=0)
                ax.axvline(base_ep, color="#ff9800", linestyle=":", linewidth=1.5, alpha=0.9)
            if losses:
                ax_loss.text(base_ep / 2.0, max(losses) * 0.85, "BASELINE (LR=0)", 
                             color="#666666", fontsize=8, ha="center", fontweight="bold")
            if rmses:
                ax_rmse.text(base_ep + 0.3, max(rmses) * 0.85, "Training Start ➔", 
                             color="#e65100", fontsize=8, fontweight="bold")

        # Visual indicator for vector switch (40+40 transfer)
        switch_ep = self.dataset.get("metadata", {}).get("switch_epoch", 0)
        if switch_ep > 0:
            for ax in [ax_loss, ax_rmse, ax_w8]:
                ax.axvline(switch_ep, color="#00bcd4", linestyle="--", linewidth=1.8, alpha=0.9)
            if losses:
                max_l = max(losses) if max(losses) > 0 else 1.0
                ax_loss.text(switch_ep / 2.0, max_l * 0.9, "Vector A (XA)", color="#1565c0", fontsize=8, ha="center", fontweight="bold")
                ax_loss.text(switch_ep + (len(epochs) - switch_ep) / 2.0, max_l * 0.9, "Vector B (XB)", color="#00695c", fontsize=8, ha="center", fontweight="bold")

        # Top: Quadratic Loss (LSB²)
        ax_loss.plot(epochs, losses, "m-s", markersize=2.5, label="Loss (LSB²)", alpha=0.8)
        ax_loss.axvline(rec.get("epoch", 0), color="r", linestyle="--", alpha=0.8)
        ax_loss.set_ylabel("Loss (LSB²)", color="m")
        ax_loss.grid(True, linestyle=":", alpha=0.6)
        ax_loss.legend(loc="upper right", fontsize=8)

        # Middle: RMSE & Current Epoch Marker + ENOB
        ax_rmse.plot(epochs, rmses, "b-o", markersize=2.5, label="RMSE (LSB)", alpha=0.7)
        ax_rmse.axvline(rec.get("epoch", 0), color="r", linestyle="--", alpha=0.8, label=f"Current: Ep {rec.get('epoch', 0)}")
        ax_rmse.set_ylabel("RMSE (LSB)", color="b")
        ax_rmse.grid(True, linestyle=":", alpha=0.6)
        ax_rmse.legend(loc="upper right", fontsize=8)

        # Secondary Y axis for ENOB
        ax_enob = ax_rmse.twinx()
        ax_enob.plot(epochs, enobs, "g--", alpha=0.7, label="ENOB (bits)")
        ax_enob.set_ylabel("ENOB (bits)", color="g")

        # Bottom: Matrix 8 Adaptive Diagonal Weights
        w8_hist = np.array([[e.get("w8_diag", [0]*6)[c] for e in self.epochs_data] for c in range(6)])
        for c in range(6):
            ax_w8.plot(epochs, w8_hist[c], label=f"W8[{c},{c}]", alpha=0.85)
        ax_w8.axvline(rec.get("epoch", 0), color="r", linestyle="--", alpha=0.8)
        ax_w8.set_xlabel("Training Epoch")
        ax_w8.set_ylabel("M8 Diag W (LSB)")
        ax_w8.grid(True, linestyle=":", alpha=0.6)
        ax_w8.legend(loc="upper left", ncol=3, fontsize=7)

        self.fig_2d.tight_layout()
        self.canvas_2d.draw()


def main():
    app = QApplication(sys.argv)
    target_json = sys.argv[1] if len(sys.argv) > 1 else None
    gui = MamlPostAnalysisGUI(json_path=target_json)
    gui.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

