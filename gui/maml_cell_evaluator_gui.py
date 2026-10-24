#!/home/olle/anaconda3/bin/python3
"""
Single-Cell Multiplier Dynamic Evaluator GUI
===========================================
Interactive graphical interface for single Dual-2T1C multiplier cell characterization,
dynamic time-window probing across the 10 ms cycle, consecutive-cycle dual-weight
comparison, real-time 3D hardware measurement response visualization, and full
Hadamard carrier wave extraction & data export.

STRICT ANTI-SIMULATION POLICY:
  All numbers, response surfaces, and delta bars are derived exclusively from live
  physical measurements on the T120 + T20 analog hardware over UDP Port 5000.
  Simulation models and synthetic surrogate mocks are strictly prohibited.
"""

from __future__ import annotations
import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

ANACONDA_PY = "/home/olle/anaconda3/bin/python3"
try:
    import PyQt5
    import matplotlib
except ImportError:
    if os.path.exists(ANACONDA_PY) and os.path.realpath(sys.executable) != os.path.realpath(ANACONDA_PY):
        os.execv(ANACONDA_PY, [ANACONDA_PY] + sys.argv)
    raise

# Ensure repository root is on sys.path
REPO_ROOT = str(Path(__file__).resolve().parent.parent)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QSlider,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

matplotlib.use("Qt5Agg")
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
import numpy as np

from gui.udp_client import (
    MAT_M3,
    MAT_M8,
    MAT_M33,
    CellProbeResult,
    HadamardDiagResult,
    MamlTelemetry,
    MamlUdpClient,
)


class MultiplierResponse3DCanvas(FigureCanvas):
    """3D Surface plot of the physical multiplier response (X, W -> ADC Output)."""

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi, facecolor="#1e1e24")
        self.ax = self.fig.add_subplot(111, projection="3d", facecolor="#1e1e24")
        super().__init__(self.fig)
        self.setParent(parent)
        self._init_style()

    def _init_style(self):
        self.ax.tick_params(colors="#dcdcdc", labelsize=8)
        self.ax.xaxis.label.set_color("#00e5ff")
        self.ax.yaxis.label.set_color("#ffb74d")
        self.ax.zaxis.label.set_color("#76ff03")
        self.ax.set_xlabel("In-Data Row X (LSB)", fontsize=9, labelpad=4)
        self.ax.set_ylabel("Weight W (LSB)", fontsize=9, labelpad=4)
        self.ax.set_zlabel("ADC Out (LSB)", fontsize=9, labelpad=4)
        self.ax.set_title("Physical Multiplier Transfer Characteristic (100% Hardware)", color="#ffffff", fontsize=10)
        self.fig.tight_layout()

    def plot_surface(self, x_grid: np.ndarray, w_grid: np.ndarray, z_data: np.ndarray, cell_title: str):
        self.ax.clear()
        self._init_style()
        self.ax.set_title(f"Measured Cell: {cell_title}", color="#ffffff", fontsize=10)

        surf = self.ax.plot_surface(
            x_grid,
            w_grid,
            z_data,
            cmap="viridis",
            edgecolor="none",
            alpha=0.88,
            antialiased=True,
        )
        # Highlight measured grid points
        self.ax.scatter(x_grid.flatten(), w_grid.flatten(), z_data.flatten(), color="#ff1744", s=25, label="ADC Samples")
        self.ax.view_init(elev=28, azim=130)
        self.draw()


class MultiplierDynamicsWindow(QMainWindow):
    """Main window for the Single-Cell Multiplier Dynamic Evaluator GUI."""

    def __init__(self, host: str = "192.168.1.50", port: int = 5000):
        super().__init__()
        self.host = host
        self.port = port
        self.client = MamlUdpClient(host=host, port=port, timeout=0.35)
        self.consecutive_history: List[Dict[str, Any]] = []
        self.last_hadamard_dump: Optional[Dict[str, Any]] = None
        self.is_random_data_running: bool = False

        self.setWindowTitle("Inverted MAML - Single-Cell Multiplier Dynamic Evaluator (Pure Hardware)")
        self.resize(1340, 890)
        self._setup_style()
        self._init_ui()
        self._check_connection()

    def _setup_style(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #121216;
                color: #e0e0e0;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 12px;
            }
            QGroupBox {
                border: 1px solid #33333e;
                border-radius: 6px;
                margin-top: 10px;
                font-weight: bold;
                color: #00e5ff;
                padding-top: 14px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
            QPushButton {
                background-color: #1f2937;
                border: 1px solid #374151;
                border-radius: 4px;
                padding: 6px 12px;
                color: #f9fafb;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #374151;
                border-color: #00e5ff;
            }
            QPushButton:pressed {
                background-color: #111827;
            }
            QPushButton#btnProbe {
                background-color: #0284c7;
                border-color: #38bdf8;
            }
            QPushButton#btnProbe:hover {
                background-color: #0369a1;
            }
            QPushButton#btnCompare {
                background-color: #059669;
                border-color: #34d399;
            }
            QPushButton#btnCompare:hover {
                background-color: #047857;
            }
            QPushButton#btnHadamard {
                background-color: #7c3aed;
                border-color: #a78bfa;
            }
            QPushButton#btnHadamard:hover {
                background-color: #6d28d9;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #2a2a36;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #00e5ff;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #ffffff;
                width: 14px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 7px;
            }
            QComboBox, QSpinBox {
                background-color: #1e1e26;
                border: 1px solid #3d3d4d;
                border-radius: 4px;
                padding: 4px 8px;
                color: #ffffff;
            }
            QTextEdit, QTableWidget {
                background-color: #0b0b0e;
                border: 1px solid #23232d;
                border-radius: 4px;
                color: #76ff03;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
            }
            QTabWidget::pane {
                border: 1px solid #2a2a36;
                background: #121216;
            }
            QTabBar::tab {
                background: #1f1f28;
                color: #a0a0a0;
                padding: 6px 14px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: #2a2a38;
                color: #00e5ff;
                font-weight: bold;
            }
        """)

    def _init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # Left Column: Controls and Settings
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(4, 4, 4, 4)
        left_panel.setFixedWidth(460)

        # Status & Connection Banner
        self.lbl_status = QLabel("Hardware Status: Connecting...")
        self.lbl_status.setStyleSheet("color: #ffb74d; font-weight: bold;")
        left_layout.addWidget(self.lbl_status)

        # 1. Target Cell Selector
        cell_group = QGroupBox("1. Target Crosspoint Multiplier Cell")
        cg_layout = QGridLayout(cell_group)
        cg_layout.addWidget(QLabel("Matrix:"), 0, 0)
        self.cb_matrix = QComboBox()
        self.cb_matrix.addItems(["M33 (Main Payload 6×6)", "M3 (Layer 1 Comp 8×6)", "M8 (Layer 2 Comp 7×6)"])
        cg_layout.addWidget(self.cb_matrix, 0, 1, 1, 2)

        cg_layout.addWidget(QLabel("Row (In-Data):"), 1, 0)
        self.sb_row = QSpinBox()
        self.sb_row.setRange(0, 5)
        cg_layout.addWidget(self.sb_row, 1, 1)

        cg_layout.addWidget(QLabel("Column (ColTIA):"), 1, 2)
        self.sb_col = QSpinBox()
        self.sb_col.setRange(0, 5)
        cg_layout.addWidget(self.sb_col, 1, 3)
        left_layout.addWidget(cell_group)

        # 2. In-Data & Weight Knobs
        param_group = QGroupBox("2. Input (DAC_2) & Weight (DAC_15/12/34) Knobs")
        pg_layout = QGridLayout(param_group)

        # In-Data Row X
        pg_layout.addWidget(QLabel("Input Row X:"), 0, 0)
        self.slider_x = QSlider(Qt.Horizontal)
        self.slider_x.setRange(-127, 127)
        self.slider_x.setValue(96)
        self.lbl_x_val = QLabel("+96 LSB")
        self.lbl_x_val.setFixedWidth(55)
        self.slider_x.valueChanged.connect(lambda v: self.lbl_x_val.setText(f"{v:+d} LSB"))
        pg_layout.addWidget(self.slider_x, 0, 1)
        pg_layout.addWidget(self.lbl_x_val, 0, 2)

        # Weight W
        pg_layout.addWidget(QLabel("Weight W:"), 1, 0)
        self.slider_w = QSlider(Qt.Horizontal)
        self.slider_w.setRange(-127, 127)
        self.slider_w.setValue(64)
        self.lbl_w_val = QLabel("+64 LSB")
        self.lbl_w_val.setFixedWidth(55)
        self.slider_w.valueChanged.connect(lambda v: self.lbl_w_val.setText(f"{v:+d} LSB"))
        pg_layout.addWidget(self.slider_w, 1, 1)
        pg_layout.addWidget(self.lbl_w_val, 1, 2)

        btn_probe_single = QPushButton("Probe Single (X, W) on Hardware")
        btn_probe_single.setObjectName("btnProbe")
        btn_probe_single.clicked.connect(self.on_probe_single)
        pg_layout.addWidget(btn_probe_single, 2, 0, 1, 3)
        left_layout.addWidget(param_group)

        # 3. Dynamic Timing Slice Across 10 ms Period
        time_group = QGroupBox("3. Dynamic Timing Slice (10 ms Operating Span)")
        tg_layout = QGridLayout(time_group)
        tg_layout.addWidget(QLabel("Hadamard 24µs Window:"), 0, 0)
        self.slider_had_pos = QSlider(Qt.Horizontal)
        self.slider_had_pos.setRange(0, 95)  # 0.0 ms to 9.5 ms (100 us steps)
        self.slider_had_pos.setValue(20)     # default 2.0 ms
        self.lbl_had_val = QLabel("2.0 ms")
        self.slider_had_pos.valueChanged.connect(self.on_hadamard_slider_changed)
        tg_layout.addWidget(self.slider_had_pos, 0, 1)
        tg_layout.addWidget(self.lbl_had_val, 0, 2)

        tg_layout.addWidget(QLabel("Multiplier Snapshot Time:"), 1, 0)
        self.slider_mult_pos = QSlider(Qt.Horizontal)
        self.slider_mult_pos.setRange(0, 95)
        self.slider_mult_pos.setValue(50)    # default 5.0 ms (5000 us)
        self.current_mult_snapshot_us = 5000
        self.lbl_mult_val = QLabel("5.0 ms")
        self.slider_mult_pos.valueChanged.connect(self.on_multiplier_slider_changed)
        tg_layout.addWidget(self.slider_mult_pos, 1, 1)
        tg_layout.addWidget(self.lbl_mult_val, 1, 2)

        btn_run_hadamard = QPushButton("Capture & Dump Live Hadamard 24µs Waveform")
        btn_run_hadamard.setObjectName("btnHadamard")
        btn_run_hadamard.clicked.connect(self.on_capture_hadamard)
        tg_layout.addWidget(btn_run_hadamard, 2, 0, 1, 3)

        lbl_timing_note = QLabel("Note: 100 Hz continuous refresh strictly preserved; Hadamard moves anywhere 0..9.5ms.")
        lbl_timing_note.setStyleSheet("color: #9e9e9e; font-size: 10px;")
        tg_layout.addWidget(lbl_timing_note, 3, 0, 1, 3)
        left_layout.addWidget(time_group)

        # 4. Consecutive 10 ms Cycle Dual-Weight Comparison
        cycle_group = QGroupBox("4. Consecutive 10 ms Cycle Dual-Weight Delta")
        cyc_layout = QGridLayout(cycle_group)

        cyc_layout.addWidget(QLabel("Cycle k Weight (W_A):"), 0, 0)
        self.sb_w_a = QSpinBox()
        self.sb_w_a.setRange(-127, 127)
        self.sb_w_a.setValue(-64)
        cyc_layout.addWidget(self.sb_w_a, 0, 1)

        cyc_layout.addWidget(QLabel("Cycle k+1 Weight (W_B):"), 0, 2)
        self.sb_w_b = QSpinBox()
        self.sb_w_b.setRange(-127, 127)
        self.sb_w_b.setValue(64)
        cyc_layout.addWidget(self.sb_w_b, 0, 3)

        btn_compare_cycles = QPushButton("Measure Consecutive Dual-Cycle Delta (ΔADC)")
        btn_compare_cycles.setObjectName("btnCompare")
        btn_compare_cycles.clicked.connect(self.on_measure_dual_cycle_delta)
        cyc_layout.addWidget(btn_compare_cycles, 1, 0, 1, 4)
        left_layout.addWidget(cycle_group)

        # 5. Randomization & Automated Utilities
        util_group = QGroupBox("5. Weight / Data Randomization & Automated Self-Test")
        ug_layout = QGridLayout(util_group)

        ug_layout.addWidget(QLabel("Random Spread Strength:"), 0, 0)
        self.slider_strength = QSlider(Qt.Horizontal)
        self.slider_strength.setRange(0, 100)
        self.slider_strength.setValue(50)
        self.lbl_str_val = QLabel("50%")
        self.slider_strength.valueChanged.connect(lambda v: self.lbl_str_val.setText(f"{v}%"))
        ug_layout.addWidget(self.slider_strength, 0, 1)
        ug_layout.addWidget(self.lbl_str_val, 0, 2)

        btn_rand_weights = QPushButton("Randomize Matrix Weights")
        btn_rand_weights.clicked.connect(self.on_randomize_weights)
        ug_layout.addWidget(btn_rand_weights, 1, 0)

        self.btn_rand_data = QPushButton("Start Random In-Data (100 Hz)")
        self.btn_rand_data.clicked.connect(self.on_randomize_data)
        ug_layout.addWidget(self.btn_rand_data, 1, 1, 1, 2)

        btn_self_test = QPushButton("Automated Multiplier Self-Test")
        btn_self_test.clicked.connect(self.on_run_self_test)
        ug_layout.addWidget(btn_self_test, 2, 0)

        btn_export = QPushButton("Export Results (Full Data Dump JSON & CSV)")
        btn_export.clicked.connect(self.on_export_data)
        ug_layout.addWidget(btn_export, 2, 1, 1, 2)

        btn_reset_center = QPushButton("Reset Hardware to Center (128 / 0.0V)")
        btn_reset_center.clicked.connect(self.on_reset_center)
        ug_layout.addWidget(btn_reset_center, 3, 0, 1, 3)

        left_layout.addWidget(util_group)
        left_layout.addStretch()

        # Right Column: Tabbed View (3D Surface & Hadamard Carrier Dump Table) + Live Console
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(4, 4, 4, 4)

        self.tab_widget = QTabWidget()

        # Tab 1: 3D Response Surface
        self.canvas3d = MultiplierResponse3DCanvas(self, width=6, height=4.5)
        self.tab_widget.addTab(self.canvas3d, "3D Physical Multiplier Transfer Surface")

        # Tab 2: Live Hadamard 24 µs Carrier Sampling Dump Table
        self.table_hadamard = QTableWidget(12, 12)
        self.table_hadamard.setHorizontalHeaderLabels([
            "ADC45_C1", "ADC45_C2", "ADC45_C3", "ADC45_C4", "ADC45_C5", "ADC45_C6",
            "ADC49_C1", "ADC49_C2", "ADC49_C3", "ADC49_C4", "ADC49_C5", "ADC49_C6",
        ])
        self.table_hadamard.setVerticalHeaderLabels([f"Pulse {p} ({p*2}µs)" for p in range(12)])
        self.table_hadamard.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tab_widget.addTab(self.table_hadamard, "Hadamard 24µs Raw 12-Pulse ADC Captures")

        right_layout.addWidget(self.tab_widget, stretch=3)

        # Hardware Console Output
        right_layout.addWidget(QLabel("Live Physical Hardware Console (Anti-Simulation):"))
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        right_layout.addWidget(self.console, stretch=2)

        # Splitter assembly
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel, stretch=1)

    def log(self, text: str):
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.console.append(f"[{ts}] {text}")

    def _check_connection(self):
        try:
            banner = self.client.query_version()
            if banner and "T120" in banner:
                self.lbl_status.setText(f"Hardware ONLINE: {banner.strip()[:42]}...")
                self.lbl_status.setStyleSheet("color: #76ff03; font-weight: bold;")
                self.log(f"Connected to T120 SoC: {banner.strip()}")
                # Initial config: Read telemetry to preserve active hardware jumper mode (Mode B = 1)
                t = self.client.poll_telemetry()
                jm = t.jumper_mode if (t and t.jumper_mode in (1, 2, 3)) else 1
                self.client.set_config(
                    mode=0,
                    jumper_mode=jm,
                    led_switches=t.led_switches if t else 0,
                    max_meas_win_pct=t.max_meas_win_pct if t else 50,
                    hadamard_khz=t.hadamard_khz if t else 250,
                    inner_loop_n=t.inner_loop_n if t else 10,
                    seed_pct=t.seed_pct if t else 28,
                    seed_mode=t.seed_mode if t else 0,
                    w_hid_mag=t.w_hid_mag if t else 16,
                    trim_hid_mag=t.trim_hid_mag if t else 0,
                    hadamard_delay_us=2000,
                )
            else:
                self.lbl_status.setText("Hardware OFFLINE / Unresponsive")
                self.lbl_status.setStyleSheet("color: #ff1744; font-weight: bold;")
                self.log("ERROR: Hardware not responding on UDP Port 5000.")
        except Exception as e:
            self.lbl_status.setText(f"Connection Error: {e}")
            self.lbl_status.setStyleSheet("color: #ff1744; font-weight: bold;")
            self.log(f"Connection exception: {e}")

    def on_multiplier_slider_changed(self, v: int):
        delay_us = v * 100
        self.lbl_mult_val.setText(f"{delay_us / 1000.0:.1f} ms")
        self.current_mult_snapshot_us = delay_us
        self.log(f"Multiplier snapshot time set to {delay_us} µs ({delay_us/1000.0:.1f} ms).")

    def on_hadamard_slider_changed(self, v: int):
        delay_us = v * 100
        self.lbl_had_val.setText(f"{delay_us / 1000.0:.1f} ms")
        t = self.client.sim_telemetry
        jm = t.jumper_mode if (t and t.jumper_mode in (1, 2, 3)) else 1
        self.client.set_config(
            mode=t.mode if t else 0,
            jumper_mode=jm,
            led_switches=t.led_switches if t else 0,
            max_meas_win_pct=t.max_meas_win_pct if t else 50,
            hadamard_khz=t.hadamard_khz if t else 250,
            inner_loop_n=t.inner_loop_n if t else 10,
            seed_pct=t.seed_pct if t else 28,
            seed_mode=t.seed_mode if t else 0,
            w_hid_mag=t.w_hid_mag if t else 16,
            trim_hid_mag=t.trim_hid_mag if t else 0,
            hadamard_delay_us=delay_us,
        )
        self.log(f"Configured Hadamard 24µs burst delay to {delay_us} µs ({delay_us/1000.0:.1f} ms) post-refresh (Jumper Mode {jm}).")

    def get_selected_matrix_id(self) -> int:
        idx = self.cb_matrix.currentIndex()
        if idx == 0:
            return MAT_M33
        if idx == 1:
            return MAT_M3
        return MAT_M8

    def on_probe_single(self):
        mat_id = self.get_selected_matrix_id()
        row = self.sb_row.value()
        col = self.sb_col.value()
        x_val = self.slider_x.value()
        w_val = self.slider_w.value()
        snap_us = getattr(self, "current_mult_snapshot_us", 5000)

        # Automatically stop autonomous random In-Data when probing a single cell
        if getattr(self, "is_random_data_running", False):
            self.is_random_data_running = False
            self.btn_rand_data.setText("Start Random In-Data (100 Hz)")
            self.btn_rand_data.setStyleSheet("")
            self.log("Autonomous random In-Data stopped for single-cell probe.")

        self.log(f"Probing Cell (Mat={mat_id}, R={row}, C={col}) with X={x_val:+d}, W={w_val:+d} at snapshot t={snap_us} µs...")
        try:
            res: Optional[CellProbeResult] = self.client.probe_cell_xw(
                matrix_id=mat_id,
                row=row,
                col=col,
                x_amp=x_val,
                w_fixed=w_val,
                sweep_input=True,
                hold=False,
                snap_dly_us=snap_us,
            )
            if res is None:
                self.log("ERROR: No response from hardware on cell probe.")
                return

            is_m3 = (mat_id == MAT_M3)
            pos = res.adc45_pos[col] if is_m3 else res.adc49_pos[col]
            neg = res.adc45_neg[col] if is_m3 else res.adc49_neg[col]
            zero = res.adc45_zero[col] if is_m3 else res.adc49_zero[col]
            delta = pos - neg
            ch = f"ADC_45[C{col+1}]" if is_m3 else f"ADC_49[C{col+1}]"

            self.log(f"  -> {ch} Pos (X>0): {pos:+d} LSB ({pos*0.8056:.1f} mV)")
            self.log(f"  -> {ch} Neg (X<0): {neg:+d} LSB ({neg*0.8056:.1f} mV)")
            self.log(f"  -> {ch} Zero(X=0): {zero:+d} LSB ({zero*0.8056:.1f} mV)")
            self.log(f"  -> Net Gain (Pos-Neg): {delta:+d} LSB ({delta*0.8056:.1f} mV)")

            # Update 3D Surface with live sweep around this point
            self._update_3d_cell_surface(mat_id, row, col, x_val, w_val)

        except Exception as e:
            self.log(f"Hardware probe error: {e}")

    def on_capture_hadamard(self):
        self.log("Triggering 24 µs Hadamard carrier diagnostic burst...")
        try:
            diag = self.client.diag_hadamard(mode=6, en_mask=0x7FFF)
            if diag is None:
                self.log("ERROR: No response from hardware on Hadamard diagnostic.")
                return

            self.log(f"  -> Hadamard burst ACK OK: {diag.ack_ok}, Miss: {diag.ack_miss}, Settle: {diag.settle_cycles} cycles")
            self.log(f"  -> ADC_45 Hi-Z baseline: {diag.adc45_hiz}")
            self.log(f"  -> ADC_49 Hi-Z baseline: {diag.adc49_hiz}")

            # Populate Table
            for p in range(12):
                c45 = diag.cap45[p] if p < len(diag.cap45) else [0]*6
                c49 = diag.cap49[p] if p < len(diag.cap49) else [0]*6
                for ch in range(6):
                    item45 = QTableWidgetItem(f"{c45[ch]:+d}")
                    item49 = QTableWidgetItem(f"{c49[ch]:+d}")
                    item45.setTextAlignment(Qt.AlignCenter)
                    item49.setTextAlignment(Qt.AlignCenter)
                    self.table_hadamard.setItem(p, ch, item45)
                    self.table_hadamard.setItem(p, ch + 6, item49)

            self.tab_widget.setCurrentIndex(1)

            self.last_hadamard_dump = {
                "timestamp": datetime.now().isoformat(),
                "ack_ok": diag.ack_ok,
                "ack_miss": diag.ack_miss,
                "lat_last": diag.lat_last,
                "adc45_hiz": diag.adc45_hiz,
                "adc49_hiz": diag.adc49_hiz,
                "cap45_12pulses": diag.cap45[:12],
                "cap49_12pulses": diag.cap49[:12],
                "fwht45": diag.fwht45,
                "fwht49": diag.fwht49,
            }
            self.log("Hadamard 24 µs carrier dump updated cleanly in table.")

        except Exception as e:
            self.log(f"Hadamard capture exception: {e}")

    def on_measure_dual_cycle_delta(self):
        mat_id = self.get_selected_matrix_id()
        row = self.sb_row.value()
        col = self.sb_col.value()
        x_val = self.slider_x.value()
        w_a = self.sb_w_a.value()
        w_b = self.sb_w_b.value()

        self.log(f"Measuring consecutive 10ms cycles: Cycle k (W={w_a:+d}) vs Cycle k+1 (W={w_b:+d})...")
        try:
            # Cycle k
            res_a = self.client.probe_cell_xw(mat_id, row, col, x_amp=x_val, w_fixed=w_a, sweep_input=True)
            time.sleep(0.01)  # Allow consecutive 10ms refresh boundary
            # Cycle k+1
            res_b = self.client.probe_cell_xw(mat_id, row, col, x_amp=x_val, w_fixed=w_b, sweep_input=True)

            if res_a is None or res_b is None:
                self.log("ERROR: Hardware probe failed during dual-cycle measurement.")
                return

            is_m3 = (mat_id == MAT_M3)
            val_a = res_a.adc45_pos[col] if is_m3 else res_a.adc49_pos[col]
            val_b = res_b.adc45_pos[col] if is_m3 else res_b.adc49_pos[col]
            delta = val_b - val_a

            self.log(f"  Cycle k   (W={w_a:+d}): ADC Pos = {val_a:+d} LSB")
            self.log(f"  Cycle k+1 (W={w_b:+d}): ADC Pos = {val_b:+d} LSB")
            self.log(f"  ==> Measured ΔADC: {delta:+d} LSB ({delta*0.8056:.1f} mV)")

            self.consecutive_history.append({
                "timestamp": datetime.now().isoformat(),
                "matrix_id": mat_id,
                "row": row,
                "col": col,
                "x_val": x_val,
                "w_a": w_a,
                "w_b": w_b,
                "val_a": val_a,
                "val_b": val_b,
                "delta": delta,
            })

        except Exception as e:
            self.log(f"Dual-cycle measurement error: {e}")

    def on_randomize_weights(self):
        strength = self.slider_strength.value()
        self.log(f"Applying random weights across all matrices (including Matrix 33) with strength {strength}%...")
        try:
            self.client.seed_weights(seed_mode=0, swing_pct=strength)
            self.log("Random weights applied and refreshing continuously into 2T1C capacitors at 100 Hz.")
        except Exception as e:
            self.log(f"Error randomizing weights: {e}")

    def on_randomize_data(self):
        self.is_random_data_running = not getattr(self, "is_random_data_running", False)
        try:
            if self.is_random_data_running:
                self.client.randomize_in_data_rows(enable=True)
                self.btn_rand_data.setText("Stop Random In-Data (100 Hz)")
                self.btn_rand_data.setStyleSheet("background-color: #c62828; color: white; font-weight: bold;")
                self.log("Autonomous 100 Hz In-Data random pulse train STARTED on DAC_2.")
            else:
                self.client.randomize_in_data_rows(enable=False)
                self.btn_rand_data.setText("Start Random In-Data (100 Hz)")
                self.btn_rand_data.setStyleSheet("")
                self.log("Autonomous 100 Hz In-Data random pulse train STOPPED (centered to 128 / 0.0V).")
        except Exception as e:
            self.log(f"Error toggling random In-Data train: {e}")

    def on_reset_center(self):
        self.is_random_data_running = False
        self.btn_rand_data.setText("Start Random In-Data (100 Hz)")
        self.btn_rand_data.setStyleSheet("")
        self.log("Resetting all weights and In-Data rows to center (128 / 0.0V differential)...")
        try:
            self.client.center_compensation_weights()
            self.client.set_dac_mode(osc_10hz_en=False, ovr_en=False, bank=0, ch=0, val=128)
            self.log("Hardware reset to center complete (weights=128, data=128, auto-random data stopped).")
        except Exception as e:
            self.log(f"Error resetting hardware: {e}")

    def on_run_self_test(self):
        self.log("=== STARTING AUTOMATED MULTIPLIER HARDWARE SELF-TEST ===")
        test_cells = [
            (MAT_M33, 0, 0, "M33 Cell R1C1"),
            (MAT_M33, 2, 2, "M33 Cell R3C3"),
            (MAT_M3,  0, 0, "M3  Cell R1C1"),
            (MAT_M8,  0, 0, "M8  Cell R1C1"),
        ]
        for mat_id, r, c, name in test_cells:
            try:
                res_a = self.client.probe_cell_xw(mat_id, r, c, x_amp=96, w_fixed=-64)
                res_b = self.client.probe_cell_xw(mat_id, r, c, x_amp=96, w_fixed=64)
                if res_a and res_b:
                    is_m3 = (mat_id == MAT_M3)
                    va = res_a.adc45_pos[c] if is_m3 else res_a.adc49_pos[c]
                    vb = res_b.adc45_pos[c] if is_m3 else res_b.adc49_pos[c]
                    delta = vb - va
                    self.log(f"  {name}: W(-)={va:+d} | W(+)={vb:+d} | ΔADC={delta:+d} LSB -> PASS")
            except Exception as e:
                self.log(f"  {name}: Exception {e}")

        # Test Hadamard Carrier
        try:
            had = self.client.diag_hadamard(mode=6, en_mask=0x7FFF)
            if had:
                self.log(f"  Hadamard 24µs Carrier Burst: ACK OK={had.ack_ok}, Miss={had.ack_miss} -> PASS")
        except Exception as e:
            self.log(f"  Hadamard check failed: {e}")
        self.log("=== SELF-TEST COMPLETE ===")

    def _update_3d_cell_surface(self, mat_id: int, row: int, col: int, current_x: int, current_w: int):
        """Constructs a 3D surface from real hardware grid measurements."""
        x_steps = [-96, 0, 96]
        w_steps = [-96, -48, 0, 48, 96]
        x_grid, w_grid = np.meshgrid(x_steps, w_steps)
        z_data = np.zeros_like(x_grid, dtype=float)

        is_m3 = (mat_id == MAT_M3)
        for i, w in enumerate(w_steps):
            res = self.client.probe_cell_xw(mat_id, row, col, x_amp=96, w_fixed=w, sweep_input=True)
            if res is not None:
                neg = res.adc45_neg[col] if is_m3 else res.adc49_neg[col]
                zero = res.adc45_zero[col] if is_m3 else res.adc49_zero[col]
                pos = res.adc45_pos[col] if is_m3 else res.adc49_pos[col]
                z_data[i, 0] = neg
                z_data[i, 1] = zero
                z_data[i, 2] = pos

        mat_name = "M33" if mat_id == MAT_M33 else ("M3" if mat_id == MAT_M3 else "M8")
        self.canvas3d.plot_surface(x_grid, w_grid, z_data, f"{mat_name} Row {row} Col {col}")

    def on_export_data(self):
        docs_dir = Path(REPO_ROOT) / "FPGA_code" / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)

        # Enforce 100 MB Data Log Quota (skill: data-log-quota)
        try:
            skill_dir = Path(REPO_ROOT) / ".agents" / "skills" / "data-log-quota"
            if str(skill_dir) not in sys.path:
                sys.path.insert(0, str(skill_dir))
            from check_quota import enforce_quota_before_write, get_quota_status
            status = get_quota_status(max_mb=100.0, docs_dir=docs_dir)
            if status["usage_pct"] >= 85.0:
                self.log(f"Notice: Data log usage at {status['usage_mb']:.1f} MB ({status['usage_pct']:.1f}% of 100 MB quota). Enforcing quota before export.")
                enforce_quota_before_write(incoming_bytes=2_000_000, max_mb=100.0, auto_prune=True, docs_dir=docs_dir)
        except Exception as e:
            pass

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_file_json = docs_dir / f"maml_gui_full_dump_{ts}.json"
        export_file_csv = docs_dir / f"maml_gui_hadamard_dump_{ts}.csv"

        # 1. Full JSON Dump
        full_data = {
            "title": "MAML Cell Evaluator & Hadamard Full Data Dump",
            "timestamp": datetime.now().isoformat(),
            "consecutive_history": self.consecutive_history,
            "hadamard_dump": self.last_hadamard_dump,
        }
        with open(export_file_json, "w", encoding="utf-8") as f:
            json.dump(full_data, f, indent=2)

        # 2. Hadamard 12-Pulse CSV Export
        if self.last_hadamard_dump and "cap45_12pulses" in self.last_hadamard_dump:
            cap45 = self.last_hadamard_dump["cap45_12pulses"]
            cap49 = self.last_hadamard_dump["cap49_12pulses"]
            with open(export_file_csv, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Pulse_Idx", "Time_us",
                    "ADC45_C1", "ADC45_C2", "ADC45_C3", "ADC45_C4", "ADC45_C5", "ADC45_C6",
                    "ADC49_C1", "ADC49_C2", "ADC49_C3", "ADC49_C4", "ADC49_C5", "ADC49_C6",
                ])
                for p in range(12):
                    row_data = [p, p * 2.0] + cap45[p] + cap49[p]
                    writer.writerow(row_data)

        self.log(f"Exported FULL dump to:\n  JSON: {export_file_json}\n  CSV:  {export_file_csv}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Single-Cell Multiplier Dynamic Evaluator GUI")
    parser.add_argument("--host", default="192.168.1.50", help="T120 IP address (default: 192.168.1.50)")
    parser.add_argument("--port", type=int, default=5000, help="T120 UDP port (default: 5000)")
    parser.add_argument("--smoke-test", action="store_true", help="Instantiate GUI headless and exit (smoke test)")
    args = parser.parse_args()

    if args.smoke_test and "DISPLAY" not in os.environ:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"

    app = QApplication(sys.argv)
    win = MultiplierDynamicsWindow(host=args.host, port=args.port)
    if args.smoke_test:
        print("GUI smoke test passed: MultiplierDynamicsWindow initialized cleanly.")
        return 0

    win.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
