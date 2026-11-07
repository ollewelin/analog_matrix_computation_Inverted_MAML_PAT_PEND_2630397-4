#!/home/olle/anaconda3/bin/python
"""
thermal_live_gui.py
Inverted MAML (Patent Pending SE 2630397-4) - Open Science Hardware

Fristående Realtids-GUI för Termisk Cykling & Mode A Reglering på Card 2:
- Läser ENBART från loggfilen: FPGA_code/logs/thermal_cycling/thermal_ring_buffer_30min.json
- Noll nätverkstrafik eller UDP: stör ALDRIG hårdvarukörningen!
- Kan startas, stängas och återstartas när som helst.
- Funktioner:
    * HUD med status & nedräkning för Värmeelement (10 min) och Reglering (2 min)
    * Prestandakurvor: Förlust (LSB²) & ENOB (bits) med färgkodade termiska/reglerings-zoner
    * Vattenfallsdiagram (Waterfall Heatmap): 4.9–5.9 ms över tid/epoker
    * 3D Stapel-Mappning: Interaktiva 3D-staplar för Matrix 3 (8x6) och Matrix 8 (7x6)
    * Tidslinje-Scrubber & Play/Pause: Spola fram och tillbaka i 30-minuters ringbufferten
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

DARK_STYLE = """
QMainWindow {
    background-color: #0b1120;
}
QWidget {
    background-color: #0b1120;
    color: #e2e8f0;
    font-family: 'Segoe UI', 'Ubuntu', 'Roboto', sans-serif;
    font-size: 11px;
}
QTabWidget::pane {
    border: 1px solid #1e293b;
    background-color: #0f172a;
    border-radius: 6px;
}
QTabBar::tab {
    background-color: #1e293b;
    color: #94a3b8;
    padding: 8px 18px;
    margin-right: 3px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: bold;
    font-size: 11px;
}
QTabBar::tab:selected {
    background-color: #0f172a;
    color: #38bdf8;
    border: 1px solid #334155;
    border-bottom: 1px solid #0f172a;
}
QTabBar::tab:hover {
    color: #f8fafc;
    background-color: #334155;
}
QGroupBox {
    border: 1px solid #1e293b;
    border-radius: 8px;
    margin-top: 10px;
    padding-top: 10px;
    font-weight: bold;
    background-color: #0f172a;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    color: #38bdf8;
}
QPushButton {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 5px;
    color: #f1f5f9;
    padding: 6px 14px;
    font-weight: bold;
    font-size: 11px;
}
QPushButton:hover {
    background-color: #334155;
    border-color: #38bdf8;
}
QPushButton:pressed {
    background-color: #0284c7;
}
QPushButton#liveBtn {
    background-color: #065f46;
    border: 1px solid #10b981;
    color: #a7f3d0;
}
QPushButton#liveBtn:hover {
    background-color: #047857;
}
QPushButton#pauseBtn {
    background-color: #7f1d1d;
    border: 1px solid #ef4444;
    color: #fecaca;
}
QSlider::groove:horizontal {
    height: 8px;
    background: #1e293b;
    border-radius: 4px;
}
QSlider::sub-page:horizontal {
    background: #0284c7;
    border-radius: 4px;
}
QSlider::handle:horizontal {
    background: #38bdf8;
    border: 1px solid #ffffff;
    width: 18px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 9px;
}
QSlider::handle:horizontal:hover {
    background: #7dd3fc;
}
"""


class ThermalLiveGui(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("INVERTED MAML — Realtidsövervakning: Termisk Cykling & Mode A Reglering (Card 2)")
        self.resize(1450, 960)
        self.setStyleSheet(DARK_STYLE)

        self.data: dict | None = None
        self.last_mtime: float = 0.0
        self.is_live: bool = True
        self.selected_idx: int = -1

        self._init_ui()

        # Timer för periodisk filläsning (var 500 ms)
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

        # 1. Toppbanner med HUD Telemetri
        hud_box = QtWidgets.QGroupBox("HÅRDVARU-TELEMETRI & REGLERINGSSTATUS")
        hud_layout = QtWidgets.QHBoxLayout(hud_box)
        hud_layout.setContentsMargins(10, 6, 10, 6)
        hud_layout.setSpacing(12)

        # HUD Kort 1: Värmeelement
        self.heater_card = QtWidgets.QFrame()
        self.heater_card.setStyleSheet("background-color: #1e293b; border-radius: 6px; padding: 6px;")
        h_layout = QtWidgets.QVBoxLayout(self.heater_card)
        h_layout.setContentsMargins(8, 4, 8, 4)
        h_layout.setSpacing(2)
        h_title = QtWidgets.QLabel("🔥 TERMISK CYKEL (10 min ON / 10 min OFF)")
        h_title.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: bold;")
        self.heater_status_lbl = QtWidgets.QLabel("VÄNTAR...")
        self.heater_status_lbl.setStyleSheet("color: #f1f5f9; font-size: 15px; font-weight: bold;")
        self.heater_timer_lbl = QtWidgets.QLabel("Tid kvar: --:--")
        self.heater_timer_lbl.setStyleSheet("color: #fb923c; font-size: 11px;")
        h_layout.addWidget(h_title)
        h_layout.addWidget(self.heater_status_lbl)
        h_layout.addWidget(self.heater_timer_lbl)
        hud_layout.addWidget(self.heater_card, stretch=1)

        # HUD Kort 2: Reglering
        self.regler_card = QtWidgets.QFrame()
        self.regler_card.setStyleSheet("background-color: #1e293b; border-radius: 6px; padding: 6px;")
        r_layout = QtWidgets.QVBoxLayout(self.regler_card)
        r_layout.setContentsMargins(8, 4, 8, 4)
        r_layout.setSpacing(2)
        r_title = QtWidgets.QLabel("⚡ MODE A REGLERING (2 min ON / 2 min OFF)")
        r_title.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: bold;")
        self.regler_status_lbl = QtWidgets.QLabel("VÄNTAR...")
        self.regler_status_lbl.setStyleSheet("color: #f1f5f9; font-size: 15px; font-weight: bold;")
        self.regler_timer_lbl = QtWidgets.QLabel("Tid kvar: --:--")
        self.regler_timer_lbl.setStyleSheet("color: #34d399; font-size: 11px;")
        r_layout.addWidget(r_title)
        r_layout.addWidget(self.regler_status_lbl)
        r_layout.addWidget(self.regler_timer_lbl)
        hud_layout.addWidget(self.regler_card, stretch=1)

        # HUD Kort 3: Prestanda vid vald tidpunkt
        self.perf_card = QtWidgets.QFrame()
        self.perf_card.setStyleSheet("background-color: #1e293b; border-radius: 6px; padding: 6px;")
        p_layout = QtWidgets.QVBoxLayout(self.perf_card)
        p_layout.setContentsMargins(8, 4, 8, 4)
        p_layout.setSpacing(2)
        p_title = QtWidgets.QLabel("📊 REALTIDSPRESTANDA (4.9–5.9 ms FÖNSTER)")
        p_title.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: bold;")
        self.perf_enob_lbl = QtWidgets.QLabel("ENOB: -- b (Fönster) | -- b (5.4ms)")
        self.perf_enob_lbl.setStyleSheet("color: #38bdf8; font-size: 14px; font-weight: bold;")
        self.perf_loss_lbl = QtWidgets.QLabel("Förlust: -- LSB² | W8: [--, --] LSB")
        self.perf_loss_lbl.setStyleSheet("color: #e2e8f0; font-size: 11px;")
        p_layout.addWidget(p_title)
        p_layout.addWidget(self.perf_enob_lbl)
        p_layout.addWidget(self.perf_loss_lbl)
        hud_layout.addWidget(self.perf_card, stretch=1)

        # HUD Kort 4: Tidslogg & Ringbuffert
        self.time_card = QtWidgets.QFrame()
        self.time_card.setStyleSheet("background-color: #1e293b; border-radius: 6px; padding: 6px;")
        t_layout = QtWidgets.QVBoxLayout(self.time_card)
        t_layout.setContentsMargins(8, 4, 8, 4)
        t_layout.setSpacing(2)
        t_title = QtWidgets.QLabel("⏱️ LOGG & RINGBUFFERT (30 MIN)")
        t_title.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: bold;")
        self.time_elapsed_lbl = QtWidgets.QLabel("Total tid: 00:00:00 | Epok: 0")
        self.time_elapsed_lbl.setStyleSheet("color: #f1f5f9; font-size: 13px; font-weight: bold;")
        self.buffer_size_lbl = QtWidgets.QLabel("Buffert: 0 epoker (~0.0 MB)")
        self.buffer_size_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        t_layout.addWidget(t_title)
        t_layout.addWidget(self.time_elapsed_lbl)
        t_layout.addWidget(self.buffer_size_lbl)
        hud_layout.addWidget(self.time_card, stretch=1)

        main_layout.addWidget(hud_box)

        # 2. Animator & Tidslinje Scrubber Toolbar
        ctrl_bar = QtWidgets.QHBoxLayout()
        ctrl_bar.setSpacing(8)

        self.play_pause_btn = QtWidgets.QPushButton("⏸ PAUSA")
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
        self.epoch_info_lbl.setStyleSheet("font-weight: bold; color: #10b981; min-width: 220px;")
        ctrl_bar.addWidget(self.epoch_info_lbl)

        self.live_btn = QtWidgets.QPushButton("🔴 FÖLJ LIVE")
        self.live_btn.setObjectName("liveBtn")
        self.live_btn.setFixedWidth(120)
        self.live_btn.clicked.connect(self.snap_to_live)
        ctrl_bar.addWidget(self.live_btn)

        main_layout.addLayout(ctrl_bar)

        # 3. Fliksystem för visualisering
        self.tabs = QtWidgets.QTabWidget()
        main_layout.addWidget(self.tabs, stretch=1)

        # Flik 1: Prestandakurvor & Vattenfallsdiagram
        self.tab1 = QtWidgets.QWidget()
        t1_layout = QtWidgets.QVBoxLayout(self.tab1)
        t1_layout.setContentsMargins(4, 4, 4, 4)
        t1_layout.setSpacing(4)
        self.fig1 = Figure(facecolor="#0f172a")
        self.canvas1 = FigureCanvas(self.fig1)
        t1_layout.addWidget(self.canvas1)
        self.tabs.addTab(self.tab1, "📈 Prestandakurvor & Vattenfall")

        # Flik 2: 3D Stapel-Mappning (M3 & M8)
        self.tab2 = QtWidgets.QWidget()
        t2_layout = QtWidgets.QVBoxLayout(self.tab2)
        t2_layout.setContentsMargins(4, 4, 4, 4)
        t2_layout.setSpacing(4)
        self.fig2 = Figure(facecolor="#0f172a")
        self.canvas2 = FigureCanvas(self.fig2)
        t2_layout.addWidget(self.canvas2)
        self.tabs.addTab(self.tab2, "🧊 3D Stapel-Mappning (M3 & M8)")

        # Flik 3: Kombinerad Instrumentpanel (Alla vyer)
        self.tab3 = QtWidgets.QWidget()
        t3_layout = QtWidgets.QVBoxLayout(self.tab3)
        t3_layout.setContentsMargins(4, 4, 4, 4)
        t3_layout.setSpacing(4)
        self.fig3 = Figure(facecolor="#0f172a")
        self.canvas3 = FigureCanvas(self.fig3)
        t3_layout.addWidget(self.canvas3)
        self.tabs.addTab(self.tab3, "🎛️ Komplett Översikt")

        self.tabs.currentChanged.connect(self.on_tab_changed)

    def toggle_play_pause(self):
        if self.is_live:
            self.is_live = False
            self.play_pause_btn.setText("▶ SPELA")
            self.play_pause_btn.setObjectName("")
            self.play_pause_btn.setStyleSheet("background-color: #0284c7; color: white;")
            self.epoch_info_lbl.setStyleSheet("font-weight: bold; color: #fbbf24;")
        else:
            self.is_live = True
            self.play_pause_btn.setText("⏸ PAUSA")
            self.play_pause_btn.setObjectName("pauseBtn")
            self.play_pause_btn.setStyleSheet("")
            self.snap_to_live()

    def snap_to_live(self):
        self.is_live = True
        self.play_pause_btn.setText("⏸ PAUSA")
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
        self.play_pause_btn.setText("▶ SPELA")
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
            self.play_pause_btn.setText("▶ SPELA")
            self.play_pause_btn.setStyleSheet("background-color: #0284c7; color: white;")
        else:
            self.is_live = True
            self.play_pause_btn.setText("⏸ PAUSA")
            self.play_pause_btn.setStyleSheet("")
        self.update_views()

    def on_tab_changed(self, idx: int):
        self.update_views()

    def check_log_file(self):
        if not RING_BUFFER_JSON.exists():
            self.heater_status_lbl.setText("VÄNTAR PÅ HÅRDVARA...")
            self.regler_status_lbl.setText("INGEN DATA")
            self.perf_enob_lbl.setText("Väntar på start av run_card2_thermal_cycling.py...")
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
        except Exception as e:
            # File might be mid-write (even though atomic os.replace is used)
            pass

    def update_views(self):
        if not self.data or not self.data.get("epochs"):
            return

        epochs = self.data["epochs"]
        n = len(epochs)
        idx = max(0, min(n - 1, self.selected_idx if self.selected_idx >= 0 else n - 1))
        cur_e = epochs[idx]
        latest_e = epochs[-1]

        # 1. Uppdatera HUD
        h_on = cur_e.get("heater_on", False)
        h_left = cur_e.get("heater_time_left_s", 0)
        h_min = int(h_left // 60)
        h_sec = int(h_left % 60)
        if h_on:
            self.heater_card.setStyleSheet("background-color: #451a03; border: 1px solid #ea580c; border-radius: 6px; padding: 6px;")
            self.heater_status_lbl.setText("🔥 PÅ (100% EFFEKT)")
            self.heater_status_lbl.setStyleSheet("color: #ffedd5; font-size: 15px; font-weight: bold;")
            self.heater_timer_lbl.setText(f"Tid kvar i värmefas: {h_min:02d}:{h_sec:02d}")
        else:
            self.heater_card.setStyleSheet("background-color: #0c4a6e; border: 1px solid #0284c7; border-radius: 6px; padding: 6px;")
            self.heater_status_lbl.setText("❄️ AV (0% EFFEKT)")
            self.heater_status_lbl.setStyleSheet("color: #e0f2fe; font-size: 15px; font-weight: bold;")
            self.heater_timer_lbl.setText(f"Tid kvar i svalningsfas: {h_min:02d}:{h_sec:02d}")

        r_on = cur_e.get("reglering_on", False)
        r_left = cur_e.get("reglering_time_left_s", 0)
        r_min = int(r_left // 60)
        r_sec = int(r_left % 60)
        if r_on:
            self.regler_card.setStyleSheet("background-color: #064e3b; border: 1px solid #059669; border-radius: 6px; padding: 6px;")
            self.regler_status_lbl.setText("⚡ AKTIV (SGD Online LR=0.02)")
            self.regler_status_lbl.setStyleSheet("color: #d1fae5; font-size: 15px; font-weight: bold;")
            self.regler_timer_lbl.setText(f"Tid kvar i regleringsfas: {r_min:02d}:{r_sec:02d}")
        else:
            self.regler_card.setStyleSheet("background-color: #334155; border: 1px solid #64748b; border-radius: 6px; padding: 6px;")
            self.regler_status_lbl.setText("⏸️ AV (Ablation W8=0)")
            self.regler_status_lbl.setStyleSheet("color: #cbd5e1; font-size: 15px; font-weight: bold;")
            self.regler_timer_lbl.setText(f"Tid kvar i ablationsfas: {r_min:02d}:{r_sec:02d}")

        w8 = cur_e.get("w_m8", [[0]*6])
        w8_flat = [val for row in w8 for val in row]
        w8_min = min(w8_flat) if w8_flat else 0
        w8_max = max(w8_flat) if w8_flat else 0

        self.perf_enob_lbl.setText(f"ENOB: {cur_e['mean_enob_bits']:.2f} b (Medel) | {cur_e['center_enob_bits']:.2f} b (5.4ms)")
        self.perf_loss_lbl.setText(f"Förlust: {cur_e['mean_loss_lsb2']:,.0f} LSB² | W8: [{w8_min:+d}, {w8_max:+d}] LSB")

        elap = latest_e.get("elapsed_s", 0)
        elap_h = int(elap // 3600)
        elap_m = int((elap % 3600) // 60)
        elap_s = int(elap % 60)
        file_size_mb = RING_BUFFER_JSON.stat().st_size / (1024 * 1024) if RING_BUFFER_JSON.exists() else 0.0
        self.time_elapsed_lbl.setText(f"Total tid: {elap_h:02d}:{elap_m:02d}:{elap_s:02d} | Epok: {latest_e['epoch']}")
        self.buffer_size_lbl.setText(f"Buffert: {n} epoker (~{file_size_mb:.1f} MB av 100 MB kvot)")

        if self.is_live:
            self.epoch_info_lbl.setText(f"🔴 LIVE (Epok {cur_e['epoch']})")
            self.epoch_info_lbl.setStyleSheet("font-weight: bold; color: #10b981; font-size: 12px;")
        else:
            diff_s = latest_e.get("elapsed_s", 0) - cur_e.get("elapsed_s", 0)
            diff_m = int(diff_s // 60)
            diff_sec = int(diff_s % 60)
            self.epoch_info_lbl.setText(f"⏸ VISAR EPOK {cur_e['epoch']} / {latest_e['epoch']} (För {diff_m:02d}:{diff_sec:02d} sedan)")
            self.epoch_info_lbl.setStyleSheet("font-weight: bold; color: #fbbf24; font-size: 12px;")

        # Rendera aktiv flik
        cur_tab = self.tabs.currentIndex()
        if cur_tab == 0:
            self._render_tab1(epochs, idx)
        elif cur_tab == 1:
            self._render_tab2(cur_e)
        elif cur_tab == 2:
            self._render_tab3(epochs, cur_e, idx)

    def _render_tab1(self, epochs: list[dict], selected_idx: int):
        self.fig1.clear()

        # Övre del: Prestandakurvor (Förlust & ENOB)
        # Nedre del: Vattenfall (Waterfall Heatmap 4.9–5.9 ms över epoker)
        gs = self.fig1.add_gridspec(2, 1, height_ratios=[1.1, 1.0], hspace=0.28, left=0.07, right=0.96, top=0.94, bottom=0.08)
        ax_top = self.fig1.add_subplot(gs[0])
        ax_top.set_facecolor("#1e293b")

        ax_bot = self.fig1.add_subplot(gs[1])
        ax_bot.set_facecolor("#1e293b")

        ep_nums = [e["epoch"] for e in epochs]
        mean_losses = [e["mean_loss_lsb2"] for e in epochs]
        mean_enobs = [e["mean_enob_bits"] for e in epochs]
        c_enobs = [e["center_enob_bits"] for e in epochs]

        # 1. Toppgraf: ENOB och Förlust
        ax_top_right = ax_top.twinx()

        l1 = ax_top.plot(ep_nums, mean_enobs, color="#38bdf8", linewidth=2.0, label="Fönster Medel ENOB (4.9–5.9 ms)")
        l2 = ax_top.plot(ep_nums, c_enobs, color="#10b981", linewidth=1.8, linestyle="--", label="5.4 ms Centrum ENOB")
        l3 = ax_top_right.plot(ep_nums, mean_losses, color="#f43f5e", linewidth=1.4, alpha=0.65, label="Fönster Medel Förlust (LSB²)")

        ax_top.set_ylabel("ENOB (bits)", color="#38bdf8", fontsize=10, fontweight="bold")
        ax_top_right.set_ylabel("Förlust (LSB²)", color="#f43f5e", fontsize=10, fontweight="bold")
        ax_top.tick_params(colors="#94a3b8")
        ax_top_right.tick_params(colors="#94a3b8")
        ax_top.grid(True, linestyle=":", alpha=0.4, color="#475569")

        # Rita termiska zoner och regleringszoner
        self._draw_phase_spans(ax_top, epochs)

        # Markör för vald epok
        sel_ep = epochs[selected_idx]["epoch"]
        ax_top.axvline(sel_ep, color="#f59e0b", linestyle="-", linewidth=2.0, alpha=0.9, label=f"Vald Epok {sel_ep}")

        lines = l1 + l2 + l3
        labels = [l.get_label() for l in lines]
        ax_top.legend(lines, labels, loc="upper right", fontsize=8.5, facecolor="#0f172a", edgecolor="#334155")
        ax_top.set_title("Prestandakurvor över Tid: Termisk Drift vs Mode A Adaptiv Reglering", color="#f8fafc", fontsize=11, fontweight="bold", pad=6)

        # 2. Vattenfallsdiagram (Waterfall Heatmap)
        strata_matrix = np.array([e.get("strata_enobs", [0]*11) for e in epochs])  # Form: (N, 11)
        delays = epochs[0].get("strata_delays", list(range(4900, 6000, 100)))
        delays_ms = [d / 1000.0 for d in delays]

        extent = [delays_ms[0] - 0.05, delays_ms[-1] + 0.05, ep_nums[0], ep_nums[-1] if len(ep_nums) > 1 else ep_nums[0] + 1]
        im = ax_bot.imshow(
            strata_matrix,
            aspect="auto",
            origin="lower",
            extent=extent,
            cmap="turbo",
            vmin=3.0,
            vmax=6.0,
            interpolation="nearest"
        )
        ax_bot.axhline(sel_ep, color="#f59e0b", linestyle="--", linewidth=2.0, alpha=0.9)
        ax_bot.set_xlabel("Samplingsfördröjning (ms)", color="#e2e8f0", fontsize=10, fontweight="bold")
        ax_bot.set_ylabel("Epok", color="#e2e8f0", fontsize=10, fontweight="bold")
        ax_bot.tick_params(colors="#94a3b8")
        ax_bot.set_title("Vattenfall (Waterfall Heatmap): ENOB (bits) över 11 Strata [4.9 – 5.9 ms]", color="#f8fafc", fontsize=11, fontweight="bold", pad=6)

        cb = self.fig1.colorbar(im, ax=ax_bot, orientation="horizontal", pad=0.18, fraction=0.04)
        cb.set_label("ENOB (bits)", color="#e2e8f0", fontsize=9)
        cb.ax.tick_params(colors="#94a3b8", labelsize=8)

        self.canvas1.draw_idle()

    def _draw_phase_spans(self, ax, epochs: list[dict]):
        """Ritar bakgrundsband för Heater ON och Reglering ON."""
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
                    ax.axvspan(start_ep, end_ep, color="#ea580c", alpha=0.12)
                else:
                    ax.axvspan(start_ep, end_ep, color="#0284c7", alpha=0.07)
                cur_heater = h_state
                start_idx = i

    def _render_tab2(self, cur_e: dict):
        self.fig2.clear()

        # Två 3D subplots sida vid sida för M3 och M8
        ax3 = self.fig2.add_subplot(1, 2, 1, projection="3d")
        ax8 = self.fig2.add_subplot(1, 2, 2, projection="3d")

        ax3.set_facecolor("#0f172a")
        ax8.set_facecolor("#0f172a")

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
                  color=c3, shade=True, edgecolor="#334155", linewidth=0.4, alpha=0.92)

        ax3.set_title(f"Matrix 3 (8x6) — Signal & W3 Trappceller\n[Epok {cur_e['epoch']} | Loss: {cur_e['mean_loss_lsb2']:.0f} LSB² | ENOB: {cur_e['mean_enob_bits']:.2f} b]",
                      color="#f8fafc", fontsize=10.5, fontweight="bold", pad=10)
        ax3.set_xticks(np.arange(w3.shape[0]))
        ax3.set_xticklabels(m3_row_labels[:w3.shape[0]], fontsize=8, color="#94a3b8", rotation=-20, ha="right")
        ax3.set_yticks(np.arange(6))
        ax3.set_yticklabels([f"C{c}" for c in range(6)], fontsize=8, color="#94a3b8")
        ax3.set_zlim(-45, 45)
        ax3.set_zticks([-40, -20, 0, 20, 40])
        ax3.tick_params(colors="#94a3b8", labelsize=8)
        ax3.set_xlabel("Matrisrad", fontsize=9, color="#e2e8f0", labelpad=6)
        ax3.set_ylabel("Kolumn", fontsize=9, color="#e2e8f0", labelpad=6)
        ax3.set_zlabel("Vikt [LSB]", fontsize=9, color="#e2e8f0", labelpad=4)
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
                  color=c8, shade=True, edgecolor="#334155", linewidth=0.4, alpha=0.92)

        reg_str = "REGLERING AKTIV" if cur_e.get("reglering_on", False) else "ABLATION (W8=0)"
        ax8.set_title(f"Matrix 8 (7x6) — Adaptiv Kompensation [{reg_str}]\n[Epok {cur_e['epoch']} | Vikter: [{int(w8.min()):+d}, {int(w8.max()):+d}] LSB]",
                      color="#f8fafc", fontsize=10.5, fontweight="bold", pad=10)
        ax8.set_xticks(np.arange(w8.shape[0]))
        ax8.set_xticklabels(m8_row_labels[:w8.shape[0]], fontsize=8, color="#94a3b8", rotation=-20, ha="right")
        ax8.set_yticks(np.arange(6))
        ax8.set_yticklabels([f"C{c}" for c in range(6)], fontsize=8, color="#94a3b8")
        ax8.set_zlim(-35, 35)
        ax8.set_zticks([-30, -15, 0, 15, 30])
        ax8.tick_params(colors="#94a3b8", labelsize=8)
        ax8.set_xlabel("Matrisrad", fontsize=9, color="#e2e8f0", labelpad=6)
        ax8.set_ylabel("Kolumn", fontsize=9, color="#e2e8f0", labelpad=6)
        ax8.set_zlabel("Vikt [LSB]", fontsize=9, color="#e2e8f0", labelpad=4)
        ax8.view_init(elev=30, azim=-50)

        self.canvas2.draw_idle()

    def _render_tab3(self, epochs: list[dict], cur_e: dict, selected_idx: int):
        self.fig3.clear()

        # 4-kvadrantsöversikt
        gs = self.fig3.add_gridspec(2, 2, hspace=0.32, wspace=0.22, left=0.06, right=0.96, top=0.92, bottom=0.08)

        ax_curve = self.fig3.add_subplot(gs[0, 0])
        ax_waterfall = self.fig3.add_subplot(gs[1, 0])
        ax3 = self.fig3.add_subplot(gs[0, 1], projection="3d")
        ax8 = self.fig3.add_subplot(gs[1, 1], projection="3d")

        for ax in [ax_curve, ax_waterfall, ax3, ax8]:
            ax.set_facecolor("#1e293b")

        ep_nums = [e["epoch"] for e in epochs]
        mean_enobs = [e["mean_enob_bits"] for e in epochs]
        sel_ep = cur_e["epoch"]

        # Kurva
        ax_curve.plot(ep_nums, mean_enobs, color="#38bdf8", linewidth=1.8, label="Medel ENOB")
        ax_curve.axvline(sel_ep, color="#f59e0b", linestyle="-", linewidth=1.8)
        self._draw_phase_spans(ax_curve, epochs)
        ax_curve.set_title("Prestanda: Fönster Medel ENOB (bits)", color="#f8fafc", fontsize=9.5, fontweight="bold")
        ax_curve.tick_params(colors="#94a3b8", labelsize=8)
        ax_curve.grid(True, linestyle=":", alpha=0.3)

        # Vattenfall
        strata_matrix = np.array([e.get("strata_enobs", [0]*11) for e in epochs])
        delays = epochs[0].get("strata_delays", list(range(4900, 6000, 100)))
        delays_ms = [d / 1000.0 for d in delays]
        extent = [delays_ms[0], delays_ms[-1], ep_nums[0], ep_nums[-1] if len(ep_nums) > 1 else ep_nums[0] + 1]
        ax_waterfall.imshow(strata_matrix, aspect="auto", origin="lower", extent=extent, cmap="turbo", vmin=3.0, vmax=6.0)
        ax_waterfall.axhline(sel_ep, color="#f59e0b", linestyle="--", linewidth=1.8)
        ax_waterfall.set_title("Vattenfall (4.9–5.9 ms)", color="#f8fafc", fontsize=9.5, fontweight="bold")
        ax_waterfall.set_xlabel("Delay (ms)", color="#e2e8f0", fontsize=8)
        ax_waterfall.set_ylabel("Epok", color="#e2e8f0", fontsize=8)
        ax_waterfall.tick_params(colors="#94a3b8", labelsize=8)

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
        ax3.set_title(f"M3 3D Staplar (Epok {sel_ep})", color="#f8fafc", fontsize=9.5, fontweight="bold")
        ax3.tick_params(colors="#94a3b8", labelsize=7)
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
        ax8.set_title(f"M8 3D Staplar (Epok {sel_ep})", color="#f8fafc", fontsize=9.5, fontweight="bold")
        ax8.tick_params(colors="#94a3b8", labelsize=7)
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
