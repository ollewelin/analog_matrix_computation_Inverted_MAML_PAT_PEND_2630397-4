#!/home/olle/anaconda3/bin/python
"""
thermal_live_gui.py
Inverted MAML (Patent Pending SE 2630397-4) - Open Science Hardware

Standalone Real-Time GUI for Thermal Cycling & Mode A Regulation on Card 2:
- Reads EXCLUSIVELY from the log file: FPGA_code/logs/thermal_cycling/thermal_ring_buffer_30min.json
- Zero network or UDP traffic: never disturbs hardware execution!
- Can be started, stopped, and restarted at any time.
- Features:
    * HUD with telemetry & countdown for Heating Elements (8 min) and Training (2 min)
    * Performance curves: Loss (LSB²) & ENOB (bits) with clearly dashed vertical lines on Training toggles
    * Waterfall Heatmap: 4.9–5.9 ms over time/epochs
    * 3D Bar Mapping: Interactive 3D bars for Matrix 3 (8x6) and Matrix 8 (7x6)
    * Timeline Scrubber & Play/Pause: Scrub forward and backward in the 30-minute ring buffer
    * Light (White) theme & English language UI
"""

from __future__ import annotations
import sys
import os
import json
import time
from pathlib import Path
import numpy as np

from PyQt5 import QtWidgets, QtCore, QtGui
import matplotlib
matplotlib.use("Qt5Agg")
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.cm as cm
import matplotlib.colors as mcolors

REPO_ROOT = Path(__file__).resolve().parent.parent
RING_BUFFER_JSON = REPO_ROOT / "FPGA_code" / "logs" / "thermal_cycling" / "thermal_ring_buffer_30min.json"
LATEST_STATUS_JSON = REPO_ROOT / "FPGA_code" / "logs" / "thermal_cycling" / "thermal_latest_status.json"

LIGHT_STYLE = """
QMainWindow {
    background-color: #f1f5f9;
}
QWidget {
    background-color: #f1f5f9;
    color: #0f172a;
    font-family: 'Segoe UI', 'Ubuntu', 'Roboto', 'Helvetica Neue', sans-serif;
    font-size: 11px;
}
QTabWidget::pane {
    border: 1px solid #cbd5e1;
    background-color: #ffffff;
    border-radius: 6px;
}
QTabBar::tab {
    background-color: #e2e8f0;
    color: #475569;
    padding: 8px 18px;
    margin-right: 3px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: bold;
    font-size: 11px;
}
QTabBar::tab:selected {
    background-color: #ffffff;
    color: #0284c7;
    border: 1px solid #cbd5e1;
    border-bottom: 1px solid #ffffff;
}
QTabBar::tab:hover {
    color: #0f172a;
    background-color: #f8fafc;
}
QGroupBox {
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    margin-top: 10px;
    padding-top: 10px;
    font-weight: bold;
    background-color: #ffffff;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    color: #0284c7;
    font-size: 11px;
}
QPushButton {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 5px;
    color: #0f172a;
    padding: 6px 14px;
    font-weight: bold;
    font-size: 11px;
}
QPushButton:hover {
    background-color: #f1f5f9;
    border-color: #0284c7;
}
QPushButton:pressed {
    background-color: #0284c7;
    color: #ffffff;
}
QPushButton#liveBtn {
    background-color: #ecfdf5;
    border: 1.5px solid #10b981;
    color: #047857;
}
QPushButton#liveBtn:hover {
    background-color: #d1fae5;
}
QPushButton#pauseBtn {
    background-color: #fef2f2;
    border: 1.5px solid #ef4444;
    color: #b91c1c;
}
QPushButton#pauseBtn:hover {
    background-color: #fee2e2;
}
QSlider::groove:horizontal {
    height: 8px;
    background: #e2e8f0;
    border-radius: 4px;
}
QSlider::sub-page:horizontal {
    background: #0284c7;
    border-radius: 4px;
}
QSlider::handle:horizontal {
    background: #0284c7;
    border: 2px solid #ffffff;
    width: 18px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 9px;
}
QSlider::handle:horizontal:hover {
    background: #0369a1;
}
"""


class ThermalLiveGui(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("INVERTED MAML — Real-Time Monitor: Thermal Cycling & Mode A Regulation (Card 2)")
        self.resize(1450, 960)
        self.setStyleSheet(LIGHT_STYLE)

        self.data: dict | None = None
        self.last_mtime: float = 0.0
        self.is_live: bool = True
        self.selected_idx: int = -1

        self._init_ui()

        # Timer for polling log file (every 500 ms)
        self.poll_timer = QtCore.QTimer(self)
        self.poll_timer.timeout.connect(self.check_log_file)
        self.poll_timer.start(500)

        self.check_log_file()

    def _init_ui(self):
        main_widget = QtWidgets.QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QtWidgets.QVBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # 1. Top HUD Telemetry Banner
        hud_box = QtWidgets.QGroupBox("HARDWARE TELEMETRY & REGULATION STATUS")
        hud_layout = QtWidgets.QHBoxLayout(hud_box)
        hud_layout.setContentsMargins(10, 8, 10, 8)
        hud_layout.setSpacing(12)

        # HUD Card 1: Heaters
        self.heater_card = QtWidgets.QFrame()
        self.heater_card.setStyleSheet("background-color: #f8fafc; border: 1px solid #cbd5e1; border-radius: 6px; padding: 6px;")
        h_layout = QtWidgets.QVBoxLayout(self.heater_card)
        h_layout.setContentsMargins(8, 4, 8, 4)
        h_layout.setSpacing(2)
        h_title = QtWidgets.QLabel("🔥 THERMAL CYCLING (8 min ON / 8 min OFF)")
        h_title.setStyleSheet("color: #64748b; font-size: 10px; font-weight: bold;")
        self.heater_status_lbl = QtWidgets.QLabel("WAITING...")
        self.heater_status_lbl.setStyleSheet("color: #0f172a; font-size: 15px; font-weight: bold;")
        self.heater_timer_lbl = QtWidgets.QLabel("Time remaining: --:--")
        self.heater_timer_lbl.setStyleSheet("color: #ea580c; font-size: 11px; font-weight: 600;")
        h_layout.addWidget(h_title)
        h_layout.addWidget(self.heater_status_lbl)
        h_layout.addWidget(self.heater_timer_lbl)
        hud_layout.addWidget(self.heater_card, stretch=1)

        # HUD Card 2: Training / Regulation
        self.regler_card = QtWidgets.QFrame()
        self.regler_card.setStyleSheet("background-color: #f8fafc; border: 1px solid #cbd5e1; border-radius: 6px; padding: 6px;")
        r_layout = QtWidgets.QVBoxLayout(self.regler_card)
        r_layout.setContentsMargins(8, 4, 8, 4)
        r_layout.setSpacing(2)
        r_title = QtWidgets.QLabel("⚡ MODE A REGULATION (2 min ON / 2 min OFF)")
        r_title.setStyleSheet("color: #64748b; font-size: 10px; font-weight: bold;")
        self.regler_status_lbl = QtWidgets.QLabel("WAITING...")
        self.regler_status_lbl.setStyleSheet("color: #0f172a; font-size: 15px; font-weight: bold;")
        self.regler_timer_lbl = QtWidgets.QLabel("Time remaining: --:--")
        self.regler_timer_lbl.setStyleSheet("color: #059669; font-size: 11px; font-weight: 600;")
        r_layout.addWidget(r_title)
        r_layout.addWidget(self.regler_status_lbl)
        r_layout.addWidget(self.regler_timer_lbl)
        hud_layout.addWidget(self.regler_card, stretch=1)

        # HUD Card 3: Performance metrics
        self.perf_card = QtWidgets.QFrame()
        self.perf_card.setStyleSheet("background-color: #f8fafc; border: 1px solid #cbd5e1; border-radius: 6px; padding: 6px;")
        p_layout = QtWidgets.QVBoxLayout(self.perf_card)
        p_layout.setContentsMargins(8, 4, 8, 4)
        p_layout.setSpacing(2)
        self.perf_title = QtWidgets.QLabel("📊 REAL-TIME PERFORMANCE WINDOW")
        self.perf_title.setStyleSheet("color: #64748b; font-size: 10px; font-weight: bold;")
        self.perf_enob_lbl = QtWidgets.QLabel("ENOB: -- b (Window) | -- b (Center)")
        self.perf_enob_lbl.setStyleSheet("color: #0284c7; font-size: 14px; font-weight: bold;")
        self.perf_loss_lbl = QtWidgets.QLabel("Loss: -- LSB² | W8: [--, --] LSB")
        self.perf_loss_lbl.setStyleSheet("color: #334155; font-size: 11px; font-weight: 600;")
        p_layout.addWidget(self.perf_title)
        p_layout.addWidget(self.perf_enob_lbl)
        p_layout.addWidget(self.perf_loss_lbl)
        hud_layout.addWidget(self.perf_card, stretch=1)

        # HUD Card 4: Timeline & Ring Buffer
        self.time_card = QtWidgets.QFrame()
        self.time_card.setStyleSheet("background-color: #f8fafc; border: 1px solid #cbd5e1; border-radius: 6px; padding: 6px;")
        t_layout = QtWidgets.QVBoxLayout(self.time_card)
        t_layout.setContentsMargins(8, 4, 8, 4)
        t_layout.setSpacing(2)
        t_title = QtWidgets.QLabel("⏱️ LOG & RING BUFFER (30 MIN)")
        t_title.setStyleSheet("color: #64748b; font-size: 10px; font-weight: bold;")
        self.time_elapsed_lbl = QtWidgets.QLabel("Total elapsed: 00:00:00 | Epoch: 0")
        self.time_elapsed_lbl.setStyleSheet("color: #0f172a; font-size: 13px; font-weight: bold;")
        self.buffer_size_lbl = QtWidgets.QLabel("Buffer: 0 epochs (~0.0 MB)")
        self.buffer_size_lbl.setStyleSheet("color: #64748b; font-size: 11px;")
        t_layout.addWidget(t_title)
        t_layout.addWidget(self.time_elapsed_lbl)
        t_layout.addWidget(self.buffer_size_lbl)
        hud_layout.addWidget(self.time_card, stretch=1)

        main_layout.addWidget(hud_box)

        # 2. Scrubber Toolbar
        ctrl_bar = QtWidgets.QHBoxLayout()
        ctrl_bar.setSpacing(8)

        self.play_pause_btn = QtWidgets.QPushButton("⏸ PAUSE")
        self.play_pause_btn.setObjectName("pauseBtn")
        self.play_pause_btn.setFixedWidth(110)
        self.play_pause_btn.clicked.connect(self.toggle_play_pause)
        ctrl_bar.addWidget(self.play_pause_btn)

        self.step_back_btn = QtWidgets.QPushButton("⏮ -1")
        self.step_back_btn.setFixedWidth(55)
        self.step_back_btn.clicked.connect(lambda: self.step_epoch(-1))
        ctrl_bar.addWidget(self.step_back_btn)

        self.step_fwd_btn = QtWidgets.QPushButton("+1 ⏭")
        self.step_fwd_btn.setFixedWidth(55)
        self.step_fwd_btn.clicked.connect(lambda: self.step_epoch(1))
        ctrl_bar.addWidget(self.step_fwd_btn)

        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.setValue(0)
        self.slider.valueChanged.connect(self.on_slider_changed)
        ctrl_bar.addWidget(self.slider, stretch=1)

        self.epoch_info_lbl = QtWidgets.QLabel("🔴 LIVE")
        self.epoch_info_lbl.setStyleSheet("font-weight: bold; color: #059669; min-width: 240px; font-size: 11.5px;")
        ctrl_bar.addWidget(self.epoch_info_lbl)

        self.live_btn = QtWidgets.QPushButton("🔴 FOLLOW LIVE")
        self.live_btn.setObjectName("liveBtn")
        self.live_btn.setFixedWidth(130)
        self.live_btn.clicked.connect(self.snap_to_live)
        ctrl_bar.addWidget(self.live_btn)

        main_layout.addLayout(ctrl_bar)

        # 3. Tab System for Visualizations
        self.tabs = QtWidgets.QTabWidget()
        main_layout.addWidget(self.tabs, stretch=1)

        # Tab 1: Performance Curves & Waterfall
        self.tab1 = QtWidgets.QWidget()
        t1_layout = QtWidgets.QVBoxLayout(self.tab1)
        t1_layout.setContentsMargins(6, 6, 6, 6)
        t1_layout.setSpacing(4)
        self.fig1 = Figure(facecolor="#ffffff")
        self.canvas1 = FigureCanvas(self.fig1)
        t1_layout.addWidget(self.canvas1)
        self.tabs.addTab(self.tab1, "📈 Performance Curves & Waterfall")

        # Tab 2: 3D Bar Mapping (M3 & M8)
        self.tab2 = QtWidgets.QWidget()
        t2_layout = QtWidgets.QVBoxLayout(self.tab2)
        t2_layout.setContentsMargins(6, 6, 6, 6)
        t2_layout.setSpacing(4)
        self.fig2 = Figure(facecolor="#ffffff")
        self.canvas2 = FigureCanvas(self.fig2)
        t2_layout.addWidget(self.canvas2)
        self.tabs.addTab(self.tab2, "🧊 3D Bar Mapping (M3 & M8)")

        # Tab 3: Complete Overview (Quad layout)
        self.tab3 = QtWidgets.QWidget()
        t3_layout = QtWidgets.QVBoxLayout(self.tab3)
        t3_layout.setContentsMargins(6, 6, 6, 6)
        t3_layout.setSpacing(4)
        self.fig3 = Figure(facecolor="#ffffff")
        self.canvas3 = FigureCanvas(self.fig3)
        t3_layout.addWidget(self.canvas3)
        self.tabs.addTab(self.tab3, "🎛️ Complete Overview")

        self.tabs.currentChanged.connect(self.on_tab_changed)

    def toggle_play_pause(self):
        if self.is_live:
            self.is_live = False
            self.play_pause_btn.setText("▶ PLAY")
            self.play_pause_btn.setObjectName("")
            self.play_pause_btn.setStyleSheet("background-color: #0284c7; color: white;")
            self.epoch_info_lbl.setStyleSheet("font-weight: bold; color: #d97706;")
        else:
            self.is_live = True
            self.play_pause_btn.setText("⏸ PAUSE")
            self.play_pause_btn.setObjectName("pauseBtn")
            self.play_pause_btn.setStyleSheet("")
            self.snap_to_live()

    def snap_to_live(self):
        self.is_live = True
        self.play_pause_btn.setText("⏸ PAUSE")
        self.play_pause_btn.setObjectName("pauseBtn")
        self.play_pause_btn.setStyleSheet("")
        if self.data and self.data.get("epochs"):
            n = len(self.data["epochs"])
            self.slider.blockSignals(True)
            self.slider.setValue(n - 1)
            self.slider.blockSignals(False)
            self.selected_idx = n - 1
            self.update_views()

    def step_epoch(self, delta: int):
        if not self.data or not self.data.get("epochs"):
            return
        self.is_live = False
        self.play_pause_btn.setText("▶ PLAY")
        self.play_pause_btn.setStyleSheet("background-color: #0284c7; color: white;")
        n = len(self.data["epochs"])
        cur = self.selected_idx if self.selected_idx >= 0 else n - 1
        new_idx = max(0, min(n - 1, cur + delta))
        self.slider.setValue(new_idx)

    def on_slider_changed(self, val: int):
        if not self.data or not self.data.get("epochs"):
            return
        n = len(self.data["epochs"])
        self.selected_idx = val
        if val < n - 1:
            self.is_live = False
            self.play_pause_btn.setText("▶ PLAY")
            self.play_pause_btn.setStyleSheet("background-color: #0284c7; color: white;")
        else:
            self.is_live = True
            self.play_pause_btn.setText("⏸ PAUSE")
            self.play_pause_btn.setStyleSheet("")
        self.update_views()

    def on_tab_changed(self, idx: int):
        self.update_views()

    def check_log_file(self):
        if not RING_BUFFER_JSON.exists():
            self.heater_status_lbl.setText("WAITING FOR HARDWARE...")
            self.regler_status_lbl.setText("NO DATA")
            self.perf_enob_lbl.setText("Waiting for run_card2_thermal_cycling.py...")
            return

        try:
            mtime = os.path.getmtime(RING_BUFFER_JSON)
            if mtime != self.last_mtime:
                self.last_mtime = mtime
                with open(RING_BUFFER_JSON, "r", encoding="utf-8") as f:
                    new_data = json.load(f)
                self.data = new_data
                epochs = self.data.get("epochs", [])
                n = len(epochs)
                if n > 0:
                    self.slider.blockSignals(True)
                    self.slider.setRange(0, n - 1)
                    if self.is_live or self.selected_idx < 0 or self.selected_idx >= n:
                        self.slider.setValue(n - 1)
                        self.selected_idx = n - 1
                    self.slider.blockSignals(False)

                self.update_views()
        except Exception:
            pass

    def update_views(self):
        if not self.data or not self.data.get("epochs"):
            return

        epochs = self.data["epochs"]
        n = len(epochs)
        idx = max(0, min(n - 1, self.selected_idx if self.selected_idx >= 0 else n - 1))
        cur_e = epochs[idx]
        latest_e = epochs[-1]

        # 1. Update HUD
        h_on = cur_e.get("heater_on", False)
        h_duty = cur_e.get("heater_duty_pct", 30)
        h_cont = cur_e.get("continuous_heater", False)
        h_left = cur_e.get("heater_time_left_s", 0)
        h_min = int(h_left // 60)
        h_sec = int(h_left % 60)
        if h_on:
            self.heater_card.setStyleSheet("background-color: #fff7ed; border: 1.5px solid #ea580c; border-radius: 6px; padding: 6px;")
            self.heater_status_lbl.setText(f"🔥 ON ({h_duty:.0f}% DUTY @ 1Hz)")
            self.heater_status_lbl.setStyleSheet("color: #c2410c; font-size: 15px; font-weight: bold;")
            if h_cont:
                self.heater_timer_lbl.setText(f"Continuous {h_duty:.0f}% Thermal Load (1Hz PWM)")
            else:
                self.heater_timer_lbl.setText(f"Remaining in Heating Phase: {h_min:02d}:{h_sec:02d}")
        else:
            self.heater_card.setStyleSheet("background-color: #f0f9ff; border: 1.5px solid #0284c7; border-radius: 6px; padding: 6px;")
            self.heater_status_lbl.setText("❄️ OFF (0% POWER)")
            self.heater_status_lbl.setStyleSheet("color: #0369a1; font-size: 15px; font-weight: bold;")
            self.heater_timer_lbl.setText(f"Remaining in Cooling Phase: {h_min:02d}:{h_sec:02d}")

        r_on = cur_e.get("reglering_on", False)
        r_left = cur_e.get("reglering_time_left_s", 0)
        r_min = int(r_left // 60)
        r_sec = int(r_left % 60)
        lr_val = cur_e.get("lr_q16", 0) / 1024.0
        l2_val = cur_e.get("reg_lambda", 768)
        if r_on:
            self.regler_card.setStyleSheet("background-color: #f0fdf4; border: 1.5px solid #10b981; border-radius: 6px; padding: 6px;")
            self.regler_status_lbl.setText(f"⚡ TRAINING ON (LR={lr_val:.2f}, λ={l2_val})")
            self.regler_status_lbl.setStyleSheet("color: #15803d; font-size: 15px; font-weight: bold;")
            self.regler_timer_lbl.setText(f"Remaining in Training Phase: {r_min:02d}:{r_sec:02d}")
        else:
            self.regler_card.setStyleSheet("background-color: #f8fafc; border: 1.5px solid #94a3b8; border-radius: 6px; padding: 6px;")
            self.regler_status_lbl.setText("⏸️ TRAINING OFF (Ablation W8=0)")
            self.regler_status_lbl.setStyleSheet("color: #475569; font-size: 15px; font-weight: bold;")
            self.regler_timer_lbl.setText(f"Remaining in Ablation Phase: {r_min:02d}:{r_sec:02d}")

        w8 = cur_e.get("w_m8", [[0]*6])
        w8_flat = [val for row in w8 for val in row]
        w8_min = min(w8_flat) if w8_flat else 0
        w8_max = max(w8_flat) if w8_flat else 0

        c_dly = self.data.get("center_delay_us", 5000)
        t_min_dly = self.data.get("t_min_us", 4500)
        t_max_dly = self.data.get("t_max_us", 5500)
        self.perf_title.setText(f"📊 REAL-TIME PERFORMANCE ([{t_min_dly/1000:.1f}–{t_max_dly/1000:.1f} ms] WINDOW)")
        self.perf_enob_lbl.setText(f"ENOB: {cur_e['mean_enob_bits']:.2f} b (Mean) | {cur_e['center_enob_bits']:.2f} b ({c_dly/1000:.1f}ms)")
        self.perf_loss_lbl.setText(f"Loss: {cur_e['mean_loss_lsb2']:,.0f} LSB² | W8 Weights: [{w8_min:+d}, {w8_max:+d}] LSB")

        elap = latest_e.get("elapsed_s", 0)
        elap_h = int(elap // 3600)
        elap_m = int((elap % 3600) // 60)
        elap_s = int(elap % 60)
        file_size_mb = RING_BUFFER_JSON.stat().st_size / (1024 * 1024) if RING_BUFFER_JSON.exists() else 0.0
        self.time_elapsed_lbl.setText(f"Total Time: {elap_h:02d}:{elap_m:02d}:{elap_s:02d} | Epoch: {latest_e['epoch']}")
        self.buffer_size_lbl.setText(f"Buffer: {n} epochs (~{file_size_mb:.1f} MB of 100 MB quota)")

        if self.is_live:
            self.epoch_info_lbl.setText(f"🔴 LIVE (Epoch {cur_e['epoch']})")
            self.epoch_info_lbl.setStyleSheet("font-weight: bold; color: #059669; font-size: 12px;")
        else:
            diff_s = latest_e.get("elapsed_s", 0) - cur_e.get("elapsed_s", 0)
            diff_m = int(diff_s // 60)
            diff_sec = int(diff_s % 60)
            self.epoch_info_lbl.setText(f"⏸ VIEWING EPOCH {cur_e['epoch']} / {latest_e['epoch']} ({diff_m:02d}:{diff_sec:02d} ago)")
            self.epoch_info_lbl.setStyleSheet("font-weight: bold; color: #d97706; font-size: 12px;")

        # Render active tab
        cur_tab = self.tabs.currentIndex()
        if cur_tab == 0:
            self._render_tab1(epochs, idx)
        elif cur_tab == 1:
            self._render_tab2(cur_e)
        elif cur_tab == 2:
            self._render_tab3(epochs, cur_e, idx)

    def _render_tab1(self, epochs: list[dict], selected_idx: int):
        self.fig1.clear()

        # Grid: Top = Performance curves, Bottom = Waterfall Heatmap
        gs = self.fig1.add_gridspec(2, 1, height_ratios=[1.15, 1.0], hspace=0.30, left=0.07, right=0.95, top=0.93, bottom=0.08)
        ax_top = self.fig1.add_subplot(gs[0])
        ax_top.set_facecolor("#ffffff")

        ax_bot = self.fig1.add_subplot(gs[1])
        ax_bot.set_facecolor("#ffffff")

        ep_nums = [e["epoch"] for e in epochs]
        mean_losses = [e["mean_loss_lsb2"] for e in epochs]
        mean_enobs = [e["mean_enob_bits"] for e in epochs]
        c_enobs = [e["center_enob_bits"] for e in epochs]

        # 1. Top Plot: ENOB and Loss curves
        ax_top_right = ax_top.twinx()

        # Phase background shading for heater
        self._draw_phase_spans(ax_top, epochs)

        # Draw clearly dashed vertical lines when Training toggles ON/OFF
        self._draw_training_toggle_lines(ax_top, epochs)

        c_dly = self.data.get("center_delay_us", 5000)
        t_min_dly = self.data.get("t_min_us", 4500)
        t_max_dly = self.data.get("t_max_us", 5500)

        l1 = ax_top.plot(ep_nums, mean_enobs, color="#0284c7", linewidth=2.2, label=f"Mean ENOB ({t_min_dly/1000:.1f}–{t_max_dly/1000:.1f} ms Window)")
        l2 = ax_top.plot(ep_nums, c_enobs, color="#059669", linewidth=2.0, linestyle="--", label=f"{c_dly/1000:.1f} ms Center ENOB")
        l3 = ax_top_right.plot(ep_nums, mean_losses, color="#e11d48", linewidth=1.5, alpha=0.75, label="Mean Loss (LSB²)")

        ax_top.set_ylabel("Resolution (ENOB, bits)", color="#0284c7", fontsize=10.5, fontweight="bold")
        ax_top_right.set_ylabel("Mean Squared Error (LSB²)", color="#e11d48", fontsize=10.5, fontweight="bold")
        ax_top.tick_params(colors="#334155")
        ax_top_right.tick_params(colors="#334155")
        ax_top.grid(True, linestyle=":", alpha=0.6, color="#cbd5e1")

        # Marker for selected epoch
        sel_ep = epochs[selected_idx]["epoch"]
        ax_top.axvline(sel_ep, color="#d97706", linestyle="-", linewidth=2.2, alpha=0.95, label=f"Selected Epoch ({sel_ep})")

        lines = l1 + l2 + l3
        labels = [l.get_label() for l in lines]
        ax_top.legend(lines, labels, loc="upper right", fontsize=8.5, facecolor="#ffffff", edgecolor="#cbd5e1")
        ax_top.set_title("Inverted MAML Real-Time Performance: Thermal Drift vs Mode A Closed-Loop Regulation",
                         color="#0f172a", fontsize=11.5, fontweight="bold", pad=8)

        # 2. Bottom Plot: Waterfall Heatmap
        delays = self.data.get("strata_delays") or epochs[0].get("strata_delays", list(range(5000, 5500, 100)))
        n_strata = len(delays)
        strata_matrix = np.array([e.get("strata_enobs", [0]*n_strata) for e in epochs])
        delays_ms = [d / 1000.0 for d in delays]

        extent = [delays_ms[0] - 0.05, delays_ms[-1] + 0.05, ep_nums[0], ep_nums[-1] if len(ep_nums) > 1 else ep_nums[0] + 1]
        im = ax_bot.imshow(
            strata_matrix,
            aspect="auto",
            origin="lower",
            extent=extent,
            cmap="turbo",
            vmin=2.5,
            vmax=6.0,
            interpolation="nearest"
        )
        ax_bot.axhline(sel_ep, color="#d97706", linestyle="--", linewidth=2.0, alpha=0.95)
        ax_bot.set_xlabel("Snapshot Sampling Delay (ms)", color="#0f172a", fontsize=10, fontweight="bold")
        ax_bot.set_ylabel("Epoch", color="#0f172a", fontsize=10, fontweight="bold")
        ax_bot.tick_params(colors="#334155")
        ax_bot.set_title(f"Waterfall Heatmap: ENOB (bits) across {n_strata} Strata [{t_min_dly/1000:.1f} – {t_max_dly/1000:.1f} ms]",
                         color="#0f172a", fontsize=11, fontweight="bold", pad=8)

        cb = self.fig1.colorbar(im, ax=ax_bot, orientation="horizontal", pad=0.18, fraction=0.04)
        cb.set_label("Resolution (ENOB, bits)", color="#0f172a", fontsize=9, fontweight="bold")
        cb.ax.tick_params(colors="#334155", labelsize=8)

        self.canvas1.draw_idle()

    def _draw_phase_spans(self, ax, epochs: list[dict]):
        """Draw background shading for Heater ON / Heater OFF phases."""
        if not epochs:
            return
        n = len(epochs)
        start_idx = 0
        cur_heater = epochs[0].get("heater_on", False)

        for i in range(1, n):
            h_state = epochs[i].get("heater_on", False)
            if h_state != cur_heater or i == n - 1:
                end_ep = epochs[i]["epoch"]
                start_ep = epochs[start_idx]["epoch"]
                if cur_heater:
                    # Heater ON: subtle warm amber tint
                    ax.axvspan(start_ep, end_ep, color="#ffedd5", alpha=0.55, zorder=0)
                else:
                    # Heater OFF: subtle cool blue tint
                    ax.axvspan(start_ep, end_ep, color="#e0f2fe", alpha=0.45, zorder=0)
                cur_heater = h_state
                start_idx = i

    def _draw_training_toggle_lines(self, ax, epochs: list[dict]):
        """Draw distinct dashed vertical lines whenever Training toggles ON or OFF."""
        if not epochs or len(epochs) < 2:
            return

        added_on_label = False
        added_off_label = False

        for i in range(1, len(epochs)):
            prev_r = epochs[i-1].get("reglering_on", False)
            cur_r = epochs[i].get("reglering_on", False)
            if prev_r != cur_r:
                ep = epochs[i]["epoch"]
                if cur_r:
                    # Switched to Training ON (Active SGD)
                    lbl = "Training ON (SGD)" if not added_on_label else None
                    ax.axvline(x=ep, color="#059669", linestyle="--", linewidth=1.8, alpha=0.9, zorder=3, label=lbl)
                    added_on_label = True
                else:
                    # Switched to Training OFF (Ablation W8=0)
                    lbl = "Training OFF (Ablation)" if not added_off_label else None
                    ax.axvline(x=ep, color="#dc2626", linestyle="--", linewidth=1.8, alpha=0.9, zorder=3, label=lbl)
                    added_off_label = True

    def _render_tab2(self, cur_e: dict):
        self.fig2.clear()

        # Two 3D subplots side by side for M3 and M8
        ax3 = self.fig2.add_subplot(1, 2, 1, projection="3d")
        ax8 = self.fig2.add_subplot(1, 2, 2, projection="3d")

        ax3.set_facecolor("#ffffff")
        ax8.set_facecolor("#ffffff")

        w3 = np.array(cur_e.get("w_m3", [[0]*6]*8), dtype=float)
        w8 = np.array(cur_e.get("w_m8", [[0]*6]*7), dtype=float)

        cmap = cm.get_cmap("coolwarm")
        norm_m3 = mcolors.Normalize(vmin=-45, vmax=45)
        norm_m8 = mcolors.Normalize(vmin=-35, vmax=35)

        m3_row_labels = ["R0", "R1", "R2", "R3", "R4", "R5", "Ref29", "Ref30"]
        m8_row_labels = [f"R{r}" for r in range(w8.shape[0])]

        # 1. Matrix 3 3D Bars
        _x = np.arange(w3.shape[0])
        _y = np.arange(w3.shape[1])
        _xx, _yy = np.meshgrid(_x, _y)
        xf, yf = _xx.ravel(), _yy.ravel()
        zf = np.zeros_like(xf, dtype=float)
        dx = 0.55 * np.ones_like(zf)
        dy = 0.55 * np.ones_like(zf)
        dz3 = w3[xf, yf]
        c3 = cmap(norm_m3(dz3))

        ax3.bar3d(xf - 0.275, yf - 0.275, zf, dx, dy, dz3,
                  color=c3, shade=True, edgecolor="#64748b", linewidth=0.5, alpha=0.92)

        ax3.set_title(f"Matrix 3 (8x6) — Signal & W3 Staircase Cells\n[Epoch {cur_e['epoch']} | Loss: {cur_e['mean_loss_lsb2']:.0f} LSB² | ENOB: {cur_e['mean_enob_bits']:.2f} b]",
                      color="#0f172a", fontsize=10.5, fontweight="bold", pad=10)
        ax3.set_xticks(np.arange(w3.shape[0]))
        ax3.set_xticklabels(m3_row_labels[:w3.shape[0]], fontsize=8, color="#334155", rotation=-20, ha="right")
        ax3.set_yticks(np.arange(6))
        ax3.set_yticklabels([f"C{c}" for c in range(6)], fontsize=8, color="#334155")
        ax3.set_zlim(-45, 45)
        ax3.set_zticks([-40, -20, 0, 20, 40])
        ax3.tick_params(colors="#334155", labelsize=8)
        ax3.set_xlabel("Matrix Row", fontsize=9, color="#0f172a", labelpad=6)
        ax3.set_ylabel("Column", fontsize=9, color="#0f172a", labelpad=6)
        ax3.set_zlabel("Weight [LSB]", fontsize=9, color="#0f172a", labelpad=4)
        ax3.view_init(elev=30, azim=-50)

        # 2. Matrix 8 3D Bars
        _x8 = np.arange(w8.shape[0])
        _y8 = np.arange(w8.shape[1])
        _xx8, _yy8 = np.meshgrid(_x8, _y8)
        xf8, yf8 = _xx8.ravel(), _yy8.ravel()
        zf8 = np.zeros_like(xf8, dtype=float)
        dx8 = 0.55 * np.ones_like(zf8)
        dy8 = 0.55 * np.ones_like(zf8)
        dz8 = w8[xf8, yf8]
        c8 = cmap(norm_m8(dz8))

        ax8.bar3d(xf8 - 0.275, yf8 - 0.275, zf8, dx8, dy8, dz8,
                  color=c8, shade=True, edgecolor="#64748b", linewidth=0.5, alpha=0.92)

        reg_str = "REGULATION ACTIVE (SGD)" if cur_e.get("reglering_on", False) else "ABLATION (W8=0)"
        ax8.set_title(f"Matrix 8 (7x6) — Adaptive Compensation [{reg_str}]\n[Epoch {cur_e['epoch']} | Weights: [{int(w8.min()):+d}, {int(w8.max()):+d}] LSB]",
                      color="#0f172a", fontsize=10.5, fontweight="bold", pad=10)
        ax8.set_xticks(np.arange(w8.shape[0]))
        ax8.set_xticklabels(m8_row_labels[:w8.shape[0]], fontsize=8, color="#334155", rotation=-20, ha="right")
        ax8.set_yticks(np.arange(6))
        ax8.set_yticklabels([f"C{c}" for c in range(6)], fontsize=8, color="#334155")
        ax8.set_zlim(-35, 35)
        ax8.set_zticks([-30, -15, 0, 15, 30])
        ax8.tick_params(colors="#334155", labelsize=8)
        ax8.set_xlabel("Matrix Row", fontsize=9, color="#0f172a", labelpad=6)
        ax8.set_ylabel("Column", fontsize=9, color="#0f172a", labelpad=6)
        ax8.set_zlabel("Weight [LSB]", fontsize=9, color="#0f172a", labelpad=4)
        ax8.view_init(elev=30, azim=-50)

        self.canvas2.draw_idle()

    def _render_tab3(self, epochs: list[dict], cur_e: dict, selected_idx: int):
        self.fig3.clear()

        # Quad overview
        gs = self.fig3.add_gridspec(2, 2, hspace=0.35, wspace=0.25, left=0.06, right=0.95, top=0.92, bottom=0.08)

        ax_curve = self.fig3.add_subplot(gs[0, 0])
        ax_waterfall = self.fig3.add_subplot(gs[1, 0])
        ax3 = self.fig3.add_subplot(gs[0, 1], projection="3d")
        ax8 = self.fig3.add_subplot(gs[1, 1], projection="3d")

        for ax in [ax_curve, ax_waterfall, ax3, ax8]:
            ax.set_facecolor("#ffffff")

        ep_nums = [e["epoch"] for e in epochs]
        mean_enobs = [e["mean_enob_bits"] for e in epochs]
        sel_ep = cur_e["epoch"]

        # Curve
        self._draw_phase_spans(ax_curve, epochs)
        self._draw_training_toggle_lines(ax_curve, epochs)
        ax_curve.plot(ep_nums, mean_enobs, color="#0284c7", linewidth=2.0, label="Mean ENOB")
        ax_curve.axvline(sel_ep, color="#d97706", linestyle="-", linewidth=2.0)
        ax_curve.set_title("Performance: Window Mean ENOB (bits)", color="#0f172a", fontsize=10, fontweight="bold")
        ax_curve.tick_params(colors="#334155", labelsize=8)
        ax_curve.grid(True, linestyle=":", alpha=0.5, color="#cbd5e1")

        # Waterfall
        delays = self.data.get("strata_delays") or epochs[0].get("strata_delays", list(range(5000, 5500, 100)))
        n_strata = len(delays)
        strata_matrix = np.array([e.get("strata_enobs", [0]*n_strata) for e in epochs])
        delays_ms = [d / 1000.0 for d in delays]
        extent = [delays_ms[0], delays_ms[-1], ep_nums[0], ep_nums[-1] if len(ep_nums) > 1 else ep_nums[0] + 1]
        ax_waterfall.imshow(strata_matrix, aspect="auto", origin="lower", extent=extent, cmap="turbo", vmin=2.5, vmax=6.0)
        ax_waterfall.axhline(sel_ep, color="#d97706", linestyle="--", linewidth=2.0)
        t_min_dly = self.data.get("t_min_us", 4500)
        t_max_dly = self.data.get("t_max_us", 5500)
        ax_waterfall.set_title(f"Waterfall ({t_min_dly/1000:.1f}–{t_max_dly/1000:.1f} ms)", color="#0f172a", fontsize=10, fontweight="bold")
        ax_waterfall.set_xlabel("Delay (ms)", color="#0f172a", fontsize=8.5)
        ax_waterfall.set_ylabel("Epoch", color="#0f172a", fontsize=8.5)
        ax_waterfall.tick_params(colors="#334155", labelsize=8)

        # 3D M3
        w3 = np.array(cur_e.get("w_m3", [[0]*6]*8), dtype=float)
        cmap = cm.get_cmap("coolwarm")
        norm_m3 = mcolors.Normalize(vmin=-45, vmax=45)
        _x = np.arange(w3.shape[0])
        _y = np.arange(w3.shape[1])
        _xx, _yy = np.meshgrid(_x, _y)
        xf, yf = _xx.ravel(), _yy.ravel()
        zf = np.zeros_like(xf, dtype=float)
        ax3.bar3d(xf - 0.25, yf - 0.25, zf, 0.5, 0.5, w3[xf, yf], color=cmap(norm_m3(w3[xf, yf])), shade=True, alpha=0.9)
        ax3.set_title(f"M3 3D Bars (Epoch {sel_ep})", color="#0f172a", fontsize=10, fontweight="bold")
        ax3.tick_params(colors="#334155", labelsize=7)
        ax3.view_init(elev=28, azim=-50)

        # 3D M8
        w8 = np.array(cur_e.get("w_m8", [[0]*6]*7), dtype=float)
        norm_m8 = mcolors.Normalize(vmin=-35, vmax=35)
        _x8 = np.arange(w8.shape[0])
        _y8 = np.arange(w8.shape[1])
        _xx8, _yy8 = np.meshgrid(_x8, _y8)
        xf8, yf8 = _xx8.ravel(), _yy8.ravel()
        zf8 = np.zeros_like(xf8, dtype=float)
        ax8.bar3d(xf8 - 0.25, yf8 - 0.25, zf8, 0.5, 0.5, w8[xf8, yf8], color=cmap(norm_m8(w8[xf8, yf8])), shade=True, alpha=0.9)
        ax8.set_title(f"M8 3D Bars (Epoch {sel_ep})", color="#0f172a", fontsize=10, fontweight="bold")
        ax8.tick_params(colors="#334155", labelsize=7)
        ax8.view_init(elev=28, azim=-50)

        self.canvas3.draw_idle()


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    gui = ThermalLiveGui()
    gui.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
