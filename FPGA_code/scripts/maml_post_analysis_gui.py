#!/home/olle/anaconda3/bin/python
"""
Post-Data Analysis & Multi-Dimensional Visualization GUI
========================================================
Interactive graphical suite for deep empirical inspection of Inverted MAML Mode A
physical silicon training, Virtual Gain campaigns, and temporal window dynamics.

Title: "Injected FORWARD Propagation" (What you need for Analog Neural Network to fly)

Features:
  - Dynamic dataset parameter ingestion (K, Strata, LR, Telemetry Stride, Window ms, Emulation).
  - Step-by-step Epoch slider & playback animation (Play / Pause / Speed).
  - 3D Weight Surface Topography (Matrix 33 static target, Matrix 3, Matrix 8).
  - 3D Convergence Trajectory in State Space (RMSE, Loss, ENOB).
  - 2D Signal Flow & Triad Summation Window:
      In-Vector X -> M33 Raw -> M3/M8 Vernier Compensation -> Passive Summing -> ENOB.
  - Multi-Strata Temporal Leakage Map across [t_min .. t_max].
"""

from __future__ import annotations
import argparse
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
DEFAULT_JSON = REPO_ROOT / "FPGA_code" / "logs" / "virtual_gain_experiments" / "gain_exp_d1_w1_g100p_c120_k4_lr05p_30000ep_run2.json"
TEST_JSON = REPO_ROOT / "FPGA_code" / "logs" / "virtual_gain_experiments" / "gain_exp_d1_w1_g100p_c120_k4_lr05p_10000ep.json"


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
        ax2.set_zlim(0, 127)

        self.fig.tight_layout()
        self.canvas.draw()


class MamlPostAnalysisGUI(QMainWindow):
    def __init__(self, json_path: Optional[str] = None, auto_play: bool = False):
        super().__init__()
        self.setWindowTitle("Injected FORWARD Propagation: Inverted MAML Silicon Studio & 3D Telemetry")
        self.resize(1540, 980)

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
            if auto_play:
                QTimer.singleShot(250, self._toggle_playback)

    def _init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(6)

        # --- Top Header & Controls Panel ---
        ctrl_box = QGroupBox("Experiment Controls & Playback")
        ctrl_box.setStyleSheet("QGroupBox { font-weight: bold; color: #1e3a8a; }")
        ctrl_layout = QHBoxLayout(ctrl_box)

        self.btn_load = QPushButton("📂 Load Data JSON")
        self.btn_load.setStyleSheet("font-weight: bold; padding: 5px 10px;")
        self.btn_load.clicked.connect(self._on_browse_file)
        ctrl_layout.addWidget(self.btn_load)

        self.lbl_file_info = QLabel("No dataset loaded")
        self.lbl_file_info.setStyleSheet("color: #0f172a; font-weight: bold;")
        ctrl_layout.addWidget(self.lbl_file_info, stretch=1)

        self.btn_play = QPushButton("▶ Play Animation")
        self.btn_play.setStyleSheet("background-color: #16a34a; color: white; font-weight: bold; padding: 6px 14px; border-radius: 4px;")
        self.btn_play.clicked.connect(self._toggle_playback)
        ctrl_layout.addWidget(self.btn_play)

        ctrl_layout.addWidget(QLabel("Speed (ms):"))
        self.spin_speed = QSpinBox()
        self.spin_speed.setRange(20, 2000)
        self.spin_speed.setValue(120)
        ctrl_layout.addWidget(self.spin_speed)

        ctrl_layout.addWidget(QLabel("Epoch Marker:"))
        self.slider_epoch = QSlider(Qt.Horizontal)
        self.slider_epoch.setRange(0, 0)
        self.slider_epoch.valueChanged.connect(self._on_slider_changed)
        ctrl_layout.addWidget(self.slider_epoch, stretch=2)

        self.lbl_epoch_val = QLabel("0 / 0")
        self.lbl_epoch_val.setFont(QFont("Monospace", 10, QFont.Bold))
        self.lbl_epoch_val.setStyleSheet("color: #2563eb; padding: 2px 6px; background: #eff6ff; border-radius: 3px;")
        ctrl_layout.addWidget(self.lbl_epoch_val)

        main_layout.addWidget(ctrl_box)

        # --- Dynamic Silicon Parameter Dashboard (Ingested dynamically from JSON) ---
        param_box = QGroupBox("Injected FORWARD Propagation: Dynamic Hardware Parameters (Read From Silicon Dataset)")
        param_box.setStyleSheet("QGroupBox { font-weight: bold; color: #0f172a; background-color: #f8fafc; border: 1px solid #cbd5e1; border-radius: 5px; margin-top: 4px; padding-top: 10px; }")
        param_layout = QHBoxLayout(param_box)
        param_layout.setContentsMargins(8, 6, 8, 6)

        badge_style = "background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 4px; padding: 3px 8px; font-weight: bold;"

        self.lbl_k_param = QLabel("K: --")
        self.lbl_k_param.setStyleSheet(badge_style + " color: #1e3a8a;")
        param_layout.addWidget(self.lbl_k_param)

        self.lbl_strata_param = QLabel("Strata: --")
        self.lbl_strata_param.setStyleSheet(badge_style + " color: #0284c7;")
        param_layout.addWidget(self.lbl_strata_param)

        self.lbl_lr_param = QLabel("LR: --")
        self.lbl_lr_param.setStyleSheet(badge_style + " color: #b45309;")
        param_layout.addWidget(self.lbl_lr_param)

        self.lbl_stride_param = QLabel("Mean Stride: --")
        self.lbl_stride_param.setStyleSheet(badge_style + " color: #7c3aed;")
        param_layout.addWidget(self.lbl_stride_param)

        self.lbl_window_param = QLabel("Window: -- ms")
        self.lbl_window_param.setStyleSheet(badge_style + " color: #059669;")
        param_layout.addWidget(self.lbl_window_param)

        self.lbl_emul_param = QLabel("Condition: --")
        self.lbl_emul_param.setStyleSheet(badge_style + " color: #334155;")
        param_layout.addWidget(self.lbl_emul_param)

        self.lbl_best_param = QLabel("Best: --")
        self.lbl_best_param.setStyleSheet(badge_style + " color: #dc2626; background-color: #fef2f2;")
        param_layout.addWidget(self.lbl_best_param)

        main_layout.addWidget(param_box)

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
        self.btn_m3_popup.clicked.connect(self._open_m3_popup)
        view_sel_layout.addWidget(self.btn_m3_popup)

        left_layout.addLayout(view_sel_layout)
        splitter.addWidget(left_widget)

        # === Right Panel: 2D Signal Flow, Vector Table & Real-Time Plots ===
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Matplotlib 2D Graphs (Loss trajectory, ENOB progression, M8 weights)
        self.fig_2d = Figure(figsize=(7, 4.5), dpi=100)
        self.fig_2d.patch.set_facecolor("#ffffff")
        self.canvas_2d = FigureCanvas(self.fig_2d)
        right_layout.addWidget(self.canvas_2d, stretch=2)

        # 2D Signal Flow Box: Table of Inputs, Targets, M33, Compensator, Error
        flow_box = QGroupBox("Signal Flow & Real-Time Channel Diagnostics (Hardware ADC Readouts)")
        flow_layout = QGridLayout(flow_box)

        self.table_signal = QTableWidget(6, 6)
        self.table_signal.setHorizontalHeaderLabels(["Input X", "Z Target", "M3 (ADC45)", "Triad (ADC49)", "Error", "M8 Diag W"])
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

            # Robust extraction of epoch records across different log schemas
            epochs_val = self.dataset.get("epochs")
            if isinstance(epochs_val, list):
                self.epochs_data = epochs_val
            elif "records" in self.dataset and isinstance(self.dataset["records"], list):
                self.epochs_data = self.dataset["records"]
            elif "epoch_records" in self.dataset and isinstance(self.dataset["epoch_records"], list):
                self.epochs_data = self.dataset["epoch_records"]
            else:
                self.epochs_data = []

            meta = self.dataset.get("metadata", {})
            t_params = meta.get("training_params", {})
            prov = meta.get("provenance", {})
            emul = prov.get("virtual_emulation", {})
            summary = self.dataset.get("summary", {})

            self.static_m33 = np.array(self.dataset.get("static_weights", {}).get("w_m33", np.zeros((6, 6))))

            n_records = len(self.epochs_data)
            self.slider_epoch.setRange(0, max(0, n_records - 1))
            self.slider_epoch.setValue(0)
            self.current_idx = 0

            # Dynamic extraction of K, Strata, LR, Window, Stride
            k_val = t_params.get("k", meta.get("k", "--"))
            strata_val = t_params.get("strata", meta.get("strata", "--"))
            lr_val = t_params.get("lr", meta.get("lr", "--"))
            lr_q16 = t_params.get("lr_inner_q16", meta.get("lr_inner_q16", None))
            lr_str = f"{lr_val}x" if lr_val != "--" else "--"
            if lr_q16 is not None:
                lr_str += f" (Q16={lr_q16})"

            # Temporal window
            t_min_us = t_params.get("t_min_us", meta.get("t_min_us", 4900))
            t_max_us = t_params.get("t_max_us", meta.get("t_max_us", 5100))
            if t_min_us == t_max_us:
                window_str = f"{t_min_us/1000.0:.2f} ms"
            else:
                window_str = f"[{t_min_us/1000.0:.2f} - {t_max_us/1000.0:.2f}] ms"

            # Telemetry stride / mean calc setting (calculated dynamically from epoch deltas)
            stride = 1
            if len(self.epochs_data) >= 3:
                ep_diffs = [
                    self.epochs_data[i]["epoch"] - self.epochs_data[i-1]["epoch"]
                    for i in range(1, min(6, len(self.epochs_data)))
                    if "epoch" in self.epochs_data[i] and "epoch" in self.epochs_data[i-1]
                ]
                if ep_diffs:
                    stride = int(round(np.median(ep_diffs)))
            elif len(self.epochs_data) == 2:
                stride = max(1, self.epochs_data[1].get("epoch", 1) - self.epochs_data[0].get("epoch", 0))

            stride_str = f"1/{stride} ep" if stride > 1 else "1/1 (All ep)"

            # Condition / Emulation tag
            d_line = emul.get("d_line", t_params.get("d_line", 1))
            w33 = emul.get("w33", t_params.get("w33", 1))
            gain = emul.get("target_gain", t_params.get("target_gain", 1.0))
            clamp = emul.get("w_clamp", t_params.get("clamp", 120))
            cond_str = f"D={d_line}x, W33={w33}x, G={gain:.1f}x, C=±{clamp}"
            reg_val = t_params.get("reg_lambda", 0.0) or 0.0
            cond_str += f", λ={reg_val:.4f}" if reg_val > 0 else ", λ=off"

            # Best epoch / metrics
            best_ep = summary.get("best_epoch", "--")
            best_loss = summary.get("best_loss", None)
            best_enob = summary.get("best_enob", None)
            if best_loss is not None and best_enob is not None:
                best_str = f"Ep #{best_ep} ({best_loss:.0f} LSB², {best_enob:.2f} b)"
            else:
                best_str = f"Ep #{best_ep}"

            # Update Parameter Banner Badges
            self.lbl_k_param.setText(f"K = {k_val} vecs")
            self.lbl_strata_param.setText(f"Strata = {strata_val}")
            self.lbl_lr_param.setText(f"LR = {lr_str}")
            self.lbl_stride_param.setText(f"Stride = {stride_str}")
            self.lbl_window_param.setText(f"Window = {window_str}")
            self.lbl_emul_param.setText(f"Mode = {cond_str}")
            self.lbl_best_param.setText(f"Best: {best_str}")

            total_epochs_target = t_params.get("epochs", len(self.epochs_data))
            info = (
                f"File: {os.path.basename(file_path)} | "
                f"Records: {n_records} | Target Ep: {total_epochs_target}"
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
            self.btn_play.setStyleSheet("background-color: #16a34a; color: white; font-weight: bold; padding: 6px 14px; border-radius: 4px;")
        else:
            if not self.epochs_data or not isinstance(self.epochs_data, list):
                return
            self.timer.start(self.spin_speed.value())
            self.is_playing = True
            self.btn_play.setText("⏸ Pause Animation")
            self.btn_play.setStyleSheet("background-color: #dc2626; color: white; font-weight: bold; padding: 6px 14px; border-radius: 4px;")

    def _on_play_step(self):
        if not self.epochs_data or not isinstance(self.epochs_data, list):
            return
        nxt = self.current_idx + 1
        if nxt >= len(self.epochs_data):
            nxt = 0
        self.slider_epoch.setValue(nxt)

    def _on_slider_changed(self, val: int):
        self.current_idx = val
        n_eps = len(self.epochs_data) if isinstance(self.epochs_data, list) else 0
        cur_ep = self.epochs_data[val].get("epoch", val) if self.epochs_data and val < len(self.epochs_data) else val
        self.lbl_epoch_val.setText(f"Rec #{val} (Ep {cur_ep})")
        self._update_all()

    def _update_all(self):
        if not self.epochs_data or not isinstance(self.epochs_data, list) or self.current_idx >= len(self.epochs_data):
            return
        rec = self.epochs_data[self.current_idx]
        self._update_table_and_metrics(rec)
        self._update_plots()

    def _update_table_and_metrics(self, rec: dict):
        x_ref = rec.get("ref_x", rec.get("x_ref", [0] * 6))
        z_target = rec.get("z_target", [0] * 6)
        adc45 = rec.get("adc45", rec.get("adc45_sig", [0] * 6))
        adc49 = rec.get("adc49", rec.get("adc49_sig", [0] * 6))
        err = rec.get("err49", [z_target[i] - adc49[i] for i in range(6)])
        w8_diag = rec.get("w8_diag", [0] * 6)

        for col in range(6):
            def _fmt_val(v):
                try:
                    return f"{int(round(float(v))):+d}"
                except Exception:
                    return f"{v}"

            vals = [
                _fmt_val(x_ref[col]),
                _fmt_val(z_target[col]),
                _fmt_val(adc45[col]),
                _fmt_val(adc49[col]),
                _fmt_val(err[col]),
                _fmt_val(w8_diag[col]),
            ]
            for r, val in enumerate(vals):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                if r == 4:  # Error column
                    if abs(err[col]) < 25:
                        item.setBackground(QColor("#d4edda"))
                    elif abs(err[col]) < 60:
                        item.setBackground(QColor("#fff3cd"))
                    else:
                        item.setBackground(QColor("#ffcdd2"))
                self.table_signal.setItem(col, r, item)

        enob = rec.get("enob_bits", 0.0)
        rmse = rec.get("rmse_lsb", 0.0)
        loss = rec.get("loss_lsb2", 0.0)
        cur_ep = rec.get("epoch", self.current_idx)

        enob_txt = f"Epoch #{cur_ep} | Hardware Settled ENOB: {enob:.2f} bits"
        self.lbl_enob.setText(enob_txt)
        self.lbl_enob.setStyleSheet("font-size: 14px; font-weight: bold; color: #15803d;")
        self.lbl_rmse.setText(f"RMSE: {rmse:.2f} LSB | Quadratic Output Loss: {loss:.1f} LSB²")

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

        if view_mode == 0:  # M8 Vernier
            raw_w_m8 = rec.get("w_m8")
            if raw_w_m8 and len(raw_w_m8) == 7 and len(raw_w_m8[0]) == 6:
                w_m8 = np.array(raw_w_m8)
            else:
                w_m8 = np.zeros((7, 6))
                diag = rec.get("w8_diag", [24] * 6)
                for i in range(min(6, len(diag))):
                    w_m8[i, i] = diag[i]
            X, Y = np.meshgrid(np.arange(6), np.arange(7))
            surf = ax_3d.plot_surface(X, Y, w_m8, cmap="viridis", edgecolor="k", linewidth=0.5, alpha=0.9)
            ax_3d.set_title(f"Matrix 8 (Vernier Compensation Layer) — Ep #{rec.get('epoch', 0)}", fontsize=11, fontweight="bold")
            ax_3d.set_xlabel("Columns 0..5")
            ax_3d.set_ylabel("Rows 0..6")
            ax_3d.set_zlabel("Weight W (LSB)")
            ax_3d.set_zlim(-50, 50)
        elif view_mode == 1:  # M3 Hidden
            raw_w_m3 = rec.get("w_m3")
            if raw_w_m3 and len(raw_w_m3) == 8 and len(raw_w_m3[0]) == 6:
                w_m3 = np.array(raw_w_m3)
            else:
                w_m3 = np.zeros((8, 6))
                diag = rec.get("w3_diag", [64] * 6)
                for i in range(min(6, len(diag))):
                    w_m3[i, i] = diag[i]
            X, Y = np.meshgrid(np.arange(6), np.arange(8))
            surf = ax_3d.plot_surface(X, Y, w_m3, cmap="plasma", edgecolor="k", linewidth=0.5, alpha=0.9)
            ax_3d.set_title(f"Matrix 3 (Projection Hidden Layer) — Ep #{rec.get('epoch', 0)}", fontsize=11, fontweight="bold")
            ax_3d.set_xlabel("Columns 0..5")
            ax_3d.set_ylabel("Rows 0..7")
            ax_3d.set_zlabel("Weight W (LSB)")
            ax_3d.set_zlim(0, 127)
        elif view_mode == 2:  # M33 Target
            raw_w_m33 = rec.get("w_m33")
            if raw_w_m33 and len(raw_w_m33) == 6 and len(raw_w_m33[0]) == 6:
                w_m33 = np.array(raw_w_m33)
            else:
                w_m33 = self.static_m33
            X, Y = np.meshgrid(np.arange(6), np.arange(6))
            surf = ax_3d.plot_surface(X, Y, w_m33, cmap="coolwarm", edgecolor="k", linewidth=0.5, alpha=0.9)
            ax_3d.set_title("Matrix 33 (Static Target Payload Task)", fontsize=11, fontweight="bold")
            ax_3d.set_xlabel("Columns 0..5")
            ax_3d.set_ylabel("Rows 0..5")
            ax_3d.set_zlabel("W33 (LSB)")
        elif view_mode == 3:  # 3D Multi-Strata Loss Landscape
            epochs = [e.get("epoch", i) for i, e in enumerate(self.epochs_data)]
            losses = [e.get("loss_lsb2", 0.0) for e in self.epochs_data]
            enobs = [e.get("enob_bits", 0.0) for e in self.epochs_data]
            ax_3d.plot(epochs, enobs, losses, color="#2563eb", linewidth=2.0, alpha=0.85)
            cur_loss = rec.get("loss_lsb2", 0.0)
            cur_enob = rec.get("enob_bits", 0.0)
            ax_3d.scatter([rec.get("epoch", 0)], [cur_enob], [cur_loss], color="red", s=80, edgecolors="k", zorder=10)
            ax_3d.set_title(f"State-Space Trajectory: Epoch #{rec.get('epoch', 0)}", fontsize=11, fontweight="bold")
            ax_3d.set_xlabel("Epoch")
            ax_3d.set_ylabel("ENOB (bits)")
            ax_3d.set_zlabel("Loss (LSB²)")

        self.fig_3d.tight_layout()
        self.canvas_3d.draw()

        # 2. --- Update 2D Trajectory Graphs ---
        self.fig_2d.clear()
        ax_loss = self.fig_2d.add_subplot(311)
        ax_rmse = self.fig_2d.add_subplot(312)
        ax_w8 = self.fig_2d.add_subplot(313)

        epochs = [e.get("epoch", i) for i, e in enumerate(self.epochs_data)]
        losses = [e.get("loss_lsb2", 0.0) for e in self.epochs_data]
        rmses = [e.get("rmse_lsb", 0.0) for e in self.epochs_data]
        enobs = [e.get("enob_bits", 0.0) for e in self.epochs_data]
        cur_ep = rec.get("epoch", self.current_idx)

        # Top: Loss & Marker
        ax_loss.plot(epochs, losses, color="#94a3b8", alpha=0.45, linewidth=1.0, label="Raw Sample Loss")
        if len(losses) >= 10:
            w_s = min(20, len(losses) // 4)
            if w_s >= 2:
                loss_smooth = np.convolve(losses, np.ones(w_s)/w_s, mode='valid')
                ax_loss.plot(epochs[w_s-1:], loss_smooth, color="#2563eb", linewidth=2.0, label=f"{w_s}-Point Rolling Mean")
        ax_loss.axvline(cur_ep, color="#0284c7", linestyle="-", linewidth=1.8, alpha=0.85, label=f"Current: Ep #{cur_ep}")
        ax_loss.set_ylabel("Loss (LSB²)")
        ax_loss.grid(True, linestyle=":", alpha=0.6)

        # Middle: RMSE & Current Epoch Marker + ENOB
        ax_rmse.plot(epochs, rmses, color="#ea580c", alpha=0.8, linewidth=1.5, label="RMSE (LSB)")
        ax_rmse.axvline(cur_ep, color="#0284c7", linestyle="-", linewidth=1.8, alpha=0.85)
        ax_rmse.set_ylabel("RMSE (LSB)", color="#ea580c")
        ax_rmse.grid(True, linestyle=":", alpha=0.6)

        # Secondary Y axis for ENOB
        ax_enob = ax_rmse.twinx()
        ax_enob.plot(epochs, enobs, color="#16a34a", alpha=0.85, linewidth=1.8, label="ENOB (bits)")
        ax_enob.set_ylabel("ENOB (bits)", color="#16a34a")
        ax_enob.set_ylim(4.0, max(7.5, max(enobs) + 0.5 if enobs else 7.5))

        # Bottom: Matrix 8 Adaptive Diagonal Weights
        w8_hist = np.array([[e.get("w8_diag", [0]*6)[c] for e in self.epochs_data] for c in range(6)])
        for c in range(6):
            ax_w8.plot(epochs, w8_hist[c], label=f"W8[{c},{c}]", alpha=0.85)
        ax_w8.axvline(cur_ep, color="#0284c7", linestyle="-", linewidth=1.8, alpha=0.85)
        ax_w8.set_xlabel("Training Epoch")
        ax_w8.set_ylabel("M8 Diag W (LSB)")
        ax_w8.grid(True, linestyle=":", alpha=0.6)
        ax_w8.legend(loc="upper left", ncol=3, fontsize=7)

        # Baseline Boundary: Red thick dashed vertical line with text "OFF" to the left
        summary = self.dataset.get("summary", {}) if isinstance(self.dataset, dict) else {}
        baseline_ep = summary.get("baseline_epochs", None)
        if baseline_ep is None and self.epochs_data:
            for e in self.epochs_data:
                if e.get("phase") in ("TRAIN", "TRAINING"):
                    baseline_ep = e.get("epoch", 40)
                    break
        if baseline_ep is None and len(epochs) > 40:
            w0 = self.epochs_data[0].get("w8_diag", [24]*6)
            w40 = self.epochs_data[min(40, len(self.epochs_data)-1)].get("w8_diag", [24]*6)
            if w0 == w40 and w0 != self.epochs_data[-1].get("w8_diag", [24]*6):
                baseline_ep = 40

        if baseline_ep is not None and 0 < baseline_ep < max(epochs):
            for ax in (ax_loss, ax_rmse, ax_w8):
                ax.axvline(baseline_ep, color="#dc2626", linestyle="--", linewidth=2.8, alpha=0.95, zorder=6)

            dx = max(1.5, max(epochs) * 0.015)
            # Annotate OFF / ON on Loss plot
            y_loss = ax_loss.get_ylim()
            y_pos_loss = y_loss[0] + 0.85 * (y_loss[1] - y_loss[0])
            ax_loss.text(
                baseline_ep - dx, y_pos_loss, "OFF",
                color="#dc2626", fontsize=10, fontweight="heavy", ha="right", va="center",
                bbox=dict(boxstyle="square,pad=0.2", facecolor="#fee2e2", edgecolor="#dc2626", linewidth=1.2, alpha=0.95),
                zorder=7
            )
            ax_loss.text(
                baseline_ep + dx, y_pos_loss, "ON",
                color="#16a34a", fontsize=10, fontweight="heavy", ha="left", va="center",
                bbox=dict(boxstyle="square,pad=0.2", facecolor="#dcfce7", edgecolor="#16a34a", linewidth=1.2, alpha=0.95),
                zorder=7
            )

            # Annotate OFF / ON on M8 Diag W plot
            y_w8 = ax_w8.get_ylim()
            y_pos_w8 = y_w8[0] + 0.78 * (y_w8[1] - y_w8[0])
            ax_w8.text(
                baseline_ep - dx, y_pos_w8, "OFF",
                color="#dc2626", fontsize=9, fontweight="heavy", ha="right", va="center",
                bbox=dict(boxstyle="square,pad=0.15", facecolor="#fee2e2", edgecolor="#dc2626", linewidth=1.0, alpha=0.95),
                zorder=7
            )
            ax_w8.text(
                baseline_ep + dx, y_pos_w8, "ON",
                color="#16a34a", fontsize=9, fontweight="heavy", ha="left", va="center",
                bbox=dict(boxstyle="square,pad=0.15", facecolor="#dcfce7", edgecolor="#16a34a", linewidth=1.0, alpha=0.95),
                zorder=7
            )

        ax_loss.legend(loc="upper right", fontsize=8)

        self.fig_2d.tight_layout()
        self.canvas_2d.draw()


def main():
    parser = argparse.ArgumentParser(description="Injected FORWARD Propagation: Inverted MAML Post-Analysis GUI")
    parser.add_argument("json_path", nargs="?", default=None, help="Path to telemetry JSON file")
    parser.add_argument("--play", "-p", action="store_true", help="Auto-start animation on load")
    parser.add_argument("--speed", "-s", type=int, default=120, help="Animation speed in ms per frame (default 120)")
    args = parser.parse_args()

    app = QApplication(sys.argv)
    gui = MamlPostAnalysisGUI(json_path=args.json_path, auto_play=args.play)
    if args.speed:
        gui.spin_speed.setValue(args.speed)
    gui.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
