"""
Main English GUI Dashboard for the Inverted MAML Analog Matrix Platform
(Patent Application SE 2630397-4 — Efinix T120F324 Master + T20F256 Controller).
"""

from __future__ import annotations
from typing import List, Optional

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from gui.diagnostics_engine import CellDiagnosticsCanvas, CellDiagnosticsEngine
from gui.loss_landscape_3d import LossLandscape3DCanvas, LossLandscapePopUpWindow
from gui.udp_client import MamlUdpClient


DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #0b0f19;
    color: #e2e8f0;
    font-family: 'DejaVu Sans', 'Segoe UI', Arial, sans-serif;
    font-size: 11px;
}
QGroupBox {
    background-color: #111827;
    border: 1px solid #1e293b;
    border-radius: 6px;
    margin-top: 9px;
    padding-top: 10px;
    font-weight: bold;
    color: #38bdf8;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}
QPushButton {
    background-color: #1e293b;
    color: #f8fafc;
    border: 1px solid #334155;
    border-radius: 4px;
    padding: 5px 10px;
}
QPushButton:hover {
    background-color: #334155;
}
QPushButton:checked {
    background-color: #0284c7;
    border-color: #38bdf8;
    font-weight: bold;
}
QComboBox, QSpinBox {
    background-color: #1e293b;
    color: #f8fafc;
    border: 1px solid #334155;
    border-radius: 4px;
    padding: 3px 6px;
}
QSlider::groove:horizontal {
    height: 6px;
    background: #1e293b;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #38bdf8;
    width: 14px;
    margin: -4px 0;
    border-radius: 7px;
}
"""


class InvertedMamlMainWindow(QMainWindow):
    """Comprehensive English GUI for controlling & visualizing the Inverted MAML Platform."""

    def __init__(self, host: str = "192.168.1.50", port: int = 5000):
        super().__init__()
        self.client = MamlUdpClient(host=host, port=port)
        self.diag_engine = CellDiagnosticsEngine(self.client)
        self.popup_3d: Optional[LossLandscapePopUpWindow] = None

        self.setWindowTitle(
            "Inverted MAML Analog Matrix Development Platform (SE 2630397-4) — T120 & T20 Control Center"
        )
        self.resize(1540, 940)
        self.setStyleSheet(DARK_STYLE)

        central = QWidget(self)
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(6)

        # Top Status & Architecture Banner
        root_layout.addWidget(self._build_top_banner())

        # Main 3-Column Workspace
        cols_layout = QHBoxLayout()
        cols_layout.setSpacing(8)
        root_layout.addLayout(cols_layout, stretch=1)

        # Left Column: Heater Safety + Hardware/Oscilloscope/Single-Cell Multiplier/LED/Jumper Controls
        left_col = QVBoxLayout()
        left_col.addWidget(self._build_heater_safety_group())
        left_col.addWidget(self._build_hardware_diag_group())
        left_col.addWidget(self._build_single_cell_multiplier_group())
        left_col.addWidget(self._build_jumper_and_led_group())
        left_col.addStretch(1)
        cols_layout.addLayout(left_col, stretch=3)

        # Center Column: Timing/Refresh/Hadamard Speed + MAML Loop & Seed Controls + Live ADC/Ref Monitor
        mid_col = QVBoxLayout()
        mid_col.addWidget(self._build_timing_and_refresh_group())
        mid_col.addWidget(self._build_maml_and_seed_group())
        mid_col.addWidget(self._build_bit_precision_and_telemetry_group())
        mid_col.addStretch(1)
        cols_layout.addLayout(mid_col, stretch=4)

        # Right Column: Embedded 3D Loss Landscape Mini-Viewport (with Pop-Up button) + Cell-by-Cell Heatmaps
        right_col = QVBoxLayout()
        right_col.addWidget(self._build_3d_landscape_group(), stretch=5)
        right_col.addWidget(self._build_cell_diagnostics_group(), stretch=4)
        cols_layout.addLayout(right_col, stretch=6)

        # Initial diagnostic report render + telemetry timer
        report = self.diag_engine.run_full_cell_diagnostics()
        self.client.restore_compensation_weights()
        self.diag_canvas.render_report(report)
        self.lbl_diag_summary.setText(report.summary_text)

        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(250)
        self.poll_timer.timeout.connect(self._on_poll_tick)
        self.poll_timer.start()
        self._on_poll_tick()

    # =========================================================================
    # Top Architecture & Connection Banner
    # =========================================================================
    def _build_top_banner(self) -> QWidget:
        bar = QWidget(self)
        bar.setStyleSheet("background-color: #111827; border: 1px solid #1e293b; border-radius: 6px;")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(10, 6, 10, 6)

        title = QLabel(
            "<b>INVERTED MAML ANALOG MATRIX PLATFORM</b> &nbsp;|&nbsp; "
            "<span style='color:#38bdf8;'>Full Differential (+/-) DAC &amp; ADC + 3-State Hi-Z Centered Hadamard</span> &nbsp;|&nbsp; "
            "<span style='color:#a7f3d0;'>4-Phase Settle-Then-Sample (~2 µs Quiet DC Window)</span> &nbsp;|&nbsp; "
            "<span style='color:#fde047;'>Non-Backprop Forward Hadamard Eq. 5 &amp; 6</span>"
        )
        lay.addWidget(title, stretch=1)

        self.lbl_conn_status = QLabel("Connecting...")
        self.lbl_conn_status.setStyleSheet(
            "background-color: #1e293b; color: #38bdf8; padding: 4px 10px; border-radius: 4px; font-weight: bold;"
        )
        lay.addWidget(self.lbl_conn_status)

        btn_ping = QPushButton("Ping T120/T20 (UDP 5000)")
        btn_ping.clicked.connect(self._on_ping_board)
        lay.addWidget(btn_ping)

        btn_rst = QPushButton("Pulse T20 CRESET_N")
        btn_rst.clicked.connect(lambda: self.client.send_ascii("RESET_PULSE"))
        lay.addWidget(btn_rst)

        return bar

    # =========================================================================
    # Left Column: Heater Safety & Thermal Warping (0.2 Hz PWM)
    # =========================================================================
    def _build_heater_safety_group(self) -> QGroupBox:
        grp = QGroupBox("1. Thermal Warping & Manual Heater Safety Interlock (0.2 Hz PWM)")
        lay = QVBoxLayout(grp)

        # Manual ARM HEATER switch + Warning Lamp
        arm_row = QHBoxLayout()
        self.btn_arm_heater = QPushButton("MANUAL ARM HEATER SWITCH: DISARMED (SAFE)")
        self.btn_arm_heater.setCheckable(True)
        self.btn_arm_heater.setChecked(False)
        self.btn_arm_heater.setStyleSheet(
            "background-color: #1e293b; color: #94a3b8; font-weight: bold; padding: 8px;"
        )
        self.btn_arm_heater.toggled.connect(self._on_heater_arm_toggled)
        arm_row.addWidget(self.btn_arm_heater)
        lay.addLayout(arm_row)

        self.lbl_heater_lamp = QLabel("SAFE: Heaters 1..4 Hardware-Disabled (Cold)")
        self.lbl_heater_lamp.setAlignment(Qt.AlignCenter)
        self.lbl_heater_lamp.setStyleSheet(
            "background-color: #064e3b; color: #a7f3d0; font-weight: bold; padding: 6px; border-radius: 4px;"
        )
        lay.addWidget(self.lbl_heater_lamp)

        # 4 Heater Sliders (0.2 Hz ultra-slow PWM)
        grid = QGridLayout()
        self.heater_sliders: List[QSlider] = []
        self.heater_val_labels: List[QLabel] = []
        zones = ["Heater 1 (NW Corner)", "Heater 2 (NE Corner)", "Heater 3 (SW Corner)", "Heater 4 (SE Corner)"]
        for i, name in enumerate(zones):
            lbl = QLabel(f"{name}:")
            sld = QSlider(Qt.Horizontal)
            sld.setRange(0, 100)
            sld.setValue(0)
            sld.setEnabled(False)
            val_lbl = QLabel("0% (0.2 Hz)")
            val_lbl.setMinimumWidth(82)
            sld.valueChanged.connect(self._on_heater_slider_changed)
            self.heater_sliders.append(sld)
            self.heater_val_labels.append(val_lbl)
            grid.addWidget(lbl, i, 0)
            grid.addWidget(sld, i, 1)
            grid.addWidget(val_lbl, i, 2)
        lay.addLayout(grid)

        # Thermal Warp Presets
        preset_row = QHBoxLayout()
        for label, duties in [
            ("All Off", [0, 0, 0, 0]),
            ("Uniform 45°C", [65, 65, 65, 65]),
            ("Left-Right Warp", [85, 10, 85, 10]),
            ("Diagonal Twist", [90, 0, 0, 90]),
        ]:
            b = QPushButton(label)
            b.clicked.connect(lambda _, d=duties: self._apply_heater_preset(d))
            preset_row.addWidget(b)
        lay.addLayout(preset_row)
        return grp

    # =========================================================================
    # Left Column: Oscilloscope DAC Pattern & Single-DAC Static Override
    # =========================================================================
    def _build_hardware_diag_group(self) -> QGroupBox:
        grp = QGroupBox("2. Oscilloscope DAC Swing Test (10 Hz) & Manual DAC Override")
        lay = QVBoxLayout(grp)

        self.btn_osc_10hz = QPushButton("10 Hz 3-State DAC Oscilloscope Mode (255 ⇄ 128 ⇄ 0 All 30 Channels)")
        self.btn_osc_10hz.setCheckable(True)
        self.btn_osc_10hz.toggled.connect(self._on_dac_diag_changed)
        lay.addWidget(self.btn_osc_10hz)

        ovr_grid = QGridLayout()
        ovr_grid.addWidget(QLabel("Target DAC Bank:"), 0, 0)
        self.cmb_dac_bank = QComboBox()
        self.cmb_dac_bank.addItems([
            "Bank 0: DAC_2 (Input Row Drive x[1..6])",
            "Bank 1: W_15 (Matrix 3 Comp L1 Weights)",
            "Bank 2: W_12 (Matrix 8 Comp L2 Weights)",
            "Bank 3: W_34 (Matrix 33 Main + Trim 38)",
            "ALL 4 Banks (Broadcast All 30 DACs Simultaneously)",
        ])
        self.cmb_dac_bank.setCurrentIndex(4)
        self.cmb_dac_bank.currentIndexChanged.connect(self._on_dac_diag_changed)
        ovr_grid.addWidget(self.cmb_dac_bank, 0, 1)

        ovr_grid.addWidget(QLabel("Channel (0..7):"), 1, 0)
        self.spn_dac_ch = QSpinBox()
        self.spn_dac_ch.setRange(0, 7)
        self.spn_dac_ch.valueChanged.connect(self._on_dac_diag_changed)
        ovr_grid.addWidget(self.spn_dac_ch, 1, 1)

        ovr_grid.addWidget(QLabel("Static Code (0..255):"), 2, 0)
        self.spn_dac_val = QSpinBox()
        self.spn_dac_val.setRange(0, 255)
        self.spn_dac_val.setValue(128)
        self.spn_dac_val.valueChanged.connect(self._on_dac_diag_changed)
        ovr_grid.addWidget(self.spn_dac_val, 2, 1)
        lay.addLayout(ovr_grid)

        quick_row = QHBoxLayout()
        for lbl, code in [("Set MIN (0)", 0), ("Set CENTER (128)", 128), ("Set MAX (255)", 255)]:
            b = QPushButton(lbl)
            b.clicked.connect(lambda _, c=code: self._set_quick_dac_code(c))
            quick_row.addWidget(b)
        lay.addLayout(quick_row)

        self.lbl_dac_diff_info = QLabel("Differential Value: +0 LSB (128 = 1.65V R-2R Midpoint)")
        self.lbl_dac_diff_info.setStyleSheet("color: #94a3b8; font-size: 10px;")
        lay.addWidget(self.lbl_dac_diff_info)

        self.btn_dac_ovr = QPushButton("Enable Static DAC Override")
        self.btn_dac_ovr.setCheckable(True)
        self.btn_dac_ovr.toggled.connect(self._on_dac_diag_changed)
        lay.addWidget(self.btn_dac_ovr)

        return grp

    # =========================================================================
    # Left Column: Single-Cell Multiplier (X × W) Interactive Test
    # =========================================================================
    def _build_single_cell_multiplier_group(self) -> QGroupBox:
        grp = QGroupBox("2B. Single-Cell Multiplier (X × W) Test (Fix W, Move Input Row Up/Down)")
        lay = QVBoxLayout(grp)

        grid = QGridLayout()
        grid.addWidget(QLabel("Target Matrix:"), 0, 0)
        self.cmb_mult_mat = QComboBox()
        self.cmb_mult_mat.addItems([
            "M33 Main (6×6 → ADC_49)",
            "M3 Comp L1 (8×6 → ADC_45)",
            "M8 Comp L2 (7×6 → ADC_49)",
        ])
        self.cmb_mult_mat.setCurrentIndex(0)
        grid.addWidget(self.cmb_mult_mat, 0, 1, 1, 3)

        grid.addWidget(QLabel("Row (0..7):"), 1, 0)
        self.spn_mult_row = QSpinBox()
        self.spn_mult_row.setRange(0, 7)
        self.spn_mult_row.setValue(0)
        grid.addWidget(self.spn_mult_row, 1, 1)

        grid.addWidget(QLabel("Col (0..5):"), 1, 2)
        self.spn_mult_col = QSpinBox()
        self.spn_mult_col.setRange(0, 5)
        self.spn_mult_col.setValue(0)
        grid.addWidget(self.spn_mult_col, 1, 3)

        grid.addWidget(QLabel("Fixed Weight W (-127..+127):"), 2, 0)
        self.spn_mult_w = QSpinBox()
        self.spn_mult_w.setRange(-127, 127)
        self.spn_mult_w.setSingleStep(16)
        self.spn_mult_w.setValue(64)
        grid.addWidget(self.spn_mult_w, 2, 1)

        grid.addWidget(QLabel("Input Step ±X (1..127):"), 2, 2)
        self.spn_mult_x = QSpinBox()
        self.spn_mult_x.setRange(1, 127)
        self.spn_mult_x.setSingleStep(16)
        self.spn_mult_x.setValue(96)
        grid.addWidget(self.spn_mult_x, 2, 3)
        lay.addLayout(grid)

        btn_row = QHBoxLayout()
        btn_single_w = QPushButton("Test Fixed W (Step Input Row ±X)")
        btn_single_w.setStyleSheet("background-color: #0284c7; font-weight: bold;")
        btn_single_w.clicked.connect(self._on_run_single_w_mult_test)
        btn_row.addWidget(btn_single_w)

        btn_sweep_w = QPushButton("Sweep 5 Weights (W=-96..+96) × (±X)")
        btn_sweep_w.setStyleSheet("background-color: #047857; font-weight: bold;")
        btn_sweep_w.clicked.connect(self._on_run_multi_w_sweep_test)
        btn_row.addWidget(btn_sweep_w)
        lay.addLayout(btn_row)

        self.lbl_mult_result = QLabel("Select (Matrix, Row, Col, W, ±X) and click to test single-cell X×W multiplication.")
        self.lbl_mult_result.setStyleSheet(
            "font-family: monospace; font-size: 9.5px; background-color: #0f172a; color: #a7f3d0; padding: 5px; border-radius: 4px;"
        )
        lay.addWidget(self.lbl_mult_result)

        return grp

    def _get_selected_mult_mat_id(self) -> int:
        idx = self.cmb_mult_mat.currentIndex()
        return 2 if idx == 0 else (0 if idx == 1 else 1)

    def _on_run_single_w_mult_test(self) -> None:
        mat_id = self._get_selected_mult_mat_id()
        row = self.spn_mult_row.value()
        col = self.spn_mult_col.value()
        w_fixed = self.spn_mult_w.value()
        x_amp = self.spn_mult_x.value()

        res = self.client.probe_cell_xw(mat_id, row, col, x_amp=x_amp, w_fixed=w_fixed, sweep_input=True, hold=True)
        if res is None:
            self.lbl_mult_result.setText("Hardware offline or no response from MAML_CMD_PROBE_CELL.")
            return

        if mat_id == 0:
            v_neg, v_zero, v_pos = res.adc45_neg[col], res.adc45_zero[col], res.adc45_pos[col]
            adc_lbl = f"ADC_45[C{col+1}]"
            mat_lbl = "M3"
        else:
            v_neg, v_zero, v_pos = res.adc49_neg[col], res.adc49_zero[col], res.adc49_pos[col]
            adc_lbl = f"ADC_49[C{col+1}]"
            mat_lbl = "M33" if mat_id == 2 else "M8"

        delta = v_pos - v_neg
        self.lbl_mult_result.setText(
            f"{mat_lbl}[R{row+1},C{col+1}] @ Fixed W={w_fixed:+d} (W+={128+w_fixed}, W-={128-w_fixed}) → {adc_lbl}:\n"
            f"  X={-x_amp:+4d} ({128-x_amp:3d}): {v_neg:+5d} LSB | X=0 (128): {v_zero:+5d} LSB | "
            f"X={+x_amp:+4d} ({128+x_amp:3d}): {v_pos:+5d} LSB\n"
            f"  Input Up-Down Swing Δ = (X+{x_amp}) - (X-{x_amp}) = {delta:+d} LSB ({delta*0.806:+.1f} mV)"
        )

    def _on_run_multi_w_sweep_test(self) -> None:
        mat_id = self._get_selected_mult_mat_id()
        row = self.spn_mult_row.value()
        col = self.spn_mult_col.value()
        x_amp = self.spn_mult_x.value()
        weights = [-96, -48, 0, +48, +96]

        curve = self.client.run_single_cell_multiplier_curve(mat_id, row, col, x_amp=x_amp, weights=weights)
        if not curve:
            self.lbl_mult_result.setText("Hardware offline or no response from MAML_CMD_PROBE_CELL.")
            return

        mat_lbl = "M33" if mat_id == 2 else ("M3" if mat_id == 0 else "M8")
        adc_lbl = curve[0]["adc_name"]
        lines = [f"{mat_lbl}[R{row+1},C{col+1}] → {adc_lbl}  (Input Row R{row+1} stepped X = -{x_amp}, 0, +{x_amp}):"]
        for pt in curve:
            lines.append(
                f"  W={pt['w']:+4d}: X={-x_amp:+4d}→{pt['out_x_neg']:+5d} | X=0→{pt['out_x_zero']:+5d} | "
                f"X={+x_amp:+4d}→{pt['out_x_pos']:+5d} | Δ(Up-Down)={pt['delta_up_down']:+5d} LSB"
            )
        self.lbl_mult_result.setText("\n".join(lines))

    # =========================================================================
    # Left Column: Analog Jumper Selector & Analog Column LED Switches
    # =========================================================================
    def _build_jumper_and_led_group(self) -> QGroupBox:
        grp = QGroupBox("3. Analog Jumper Configuration & Column LED Output Switches")
        lay = QVBoxLayout(grp)

        lay.addWidget(QLabel("Manual Hardware Analog Jumper Setting:"))
        self.cmb_jumper = QComboBox()
        self.cmb_jumper.addItems([
            "1. OFF — No Compensation (Raw Matrix 33 Only)",
            "2. Bypass Second Sigmoid (Linear 2nd Layer Output)",
            "3. Use Second Sigmoid Layer (Full Dual-Sigmoid Compensation)",
        ])
        self.cmb_jumper.setCurrentIndex(1)  # Default: Mode 2
        self.cmb_jumper.currentIndexChanged.connect(self._sync_config_to_board)
        lay.addWidget(self.cmb_jumper)

        led_row = QHBoxLayout()
        self.chk_comp_led = QCheckBox("COMP_LED_ON (Comp Column LEDs)")
        self.chk_comp_led.setChecked(True)
        self.chk_comp_led.stateChanged.connect(self._sync_config_to_board)
        led_row.addWidget(self.chk_comp_led)

        self.chk_mat33_led = QCheckBox("MAT33_LED_ON (Main Column LEDs)")
        self.chk_mat33_led.setChecked(True)
        self.chk_mat33_led.stateChanged.connect(self._sync_config_to_board)
        led_row.addWidget(self.chk_mat33_led)
        lay.addLayout(led_row)

        return grp

    # =========================================================================
    # Center Column: Timing, Refresh Period, & Hadamard Speed Controls
    # =========================================================================
    def _build_timing_and_refresh_group(self) -> QGroupBox:
        grp = QGroupBox("4. Hadamard Pulse Speed (50–500 kHz), Settle-Then-Sample & Refresh Window")
        lay = QVBoxLayout(grp)

        # Operating Mode Selector (Ref 40 / Ref 41 / Ref 42)
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Platform Mode:"))
        self.cmb_mode = QComboBox()
        self.cmb_mode.addItems([
            "0 — Idle / Standby (3-State Hi-Z Centered)",
            "1 — Base Model Training (Ref 40 Outer + Ref 41 Inner, 100% Refresh Window)",
            "2 — Fast Inner-Loop Adaptation Only (Ref 41)",
            "3 — Operation Mode (Ref 42, Hidden Offsets Zeroed, Max Window % Capped)",
        ])
        self.cmb_mode.setCurrentIndex(1)
        self.cmb_mode.currentIndexChanged.connect(self._on_mode_or_timing_changed)
        mode_row.addWidget(self.cmb_mode, stretch=1)
        lay.addLayout(mode_row)

        # Hadamard Frequency Slider (50 kHz .. 500 kHz, default 500 kHz = 2 us settle)
        lay.addWidget(QLabel("Hadamard Pulse Frequency (Default 500 kHz = 2.0 µs Quiet DC Settle Window):"))
        freq_row = QHBoxLayout()
        self.sld_hadamard_khz = QSlider(Qt.Horizontal)
        self.sld_hadamard_khz.setRange(50, 500)
        self.sld_hadamard_khz.setSingleStep(10)
        self.sld_hadamard_khz.setValue(500)
        self.sld_hadamard_khz.valueChanged.connect(self._on_mode_or_timing_changed)
        freq_row.addWidget(self.sld_hadamard_khz, stretch=1)
        self.lbl_hadamard_khz = QLabel("500 kHz (2.00 µs Settle | 0.34 ms Refresh)")
        self.lbl_hadamard_khz.setMinimumWidth(250)
        freq_row.addWidget(self.lbl_hadamard_khz)
        lay.addLayout(freq_row)

        # Max Measurement Window % Slider (0..25% in Operation Mode Ref 42; 100% in Base Training Ref 40)
        lay.addWidget(QLabel("Max Measurement Window % of Full Refresh Period (Ref 42 Operation Duty Limit):"))
        win_row = QHBoxLayout()
        self.sld_meas_win = QSlider(Qt.Horizontal)
        self.sld_meas_win.setRange(1, 25)
        self.sld_meas_win.setValue(10)
        self.sld_meas_win.valueChanged.connect(self._on_mode_or_timing_changed)
        win_row.addWidget(self.sld_meas_win, stretch=1)
        self.lbl_meas_win = QLabel("100% (Locked for Ref 40 Base Training)")
        self.lbl_meas_win.setMinimumWidth(250)
        win_row.addWidget(self.lbl_meas_win)
        lay.addLayout(win_row)

        info = QLabel(
            "• <b>1 Measurement Window per Time Slot</b> across M=10 shuffled strata P[0..9] covers 100% of capacitor decay.<br>"
            "• <b>White-Noise Reference Lock:</b> x_ref is held 100% constant across all 10 strata of a full refresh cycle."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #94a3b8; font-size: 10px;")
        lay.addWidget(info)

        return grp

    # =========================================================================
    # Center Column: Inner Loop N, Seed Randomization, & Hidden Offsets
    # =========================================================================
    def _build_maml_and_seed_group(self) -> QGroupBox:
        grp = QGroupBox("5. Inner Loop (Ref 41), Seed Randomization & Hidden Offset Emulator")
        lay = QVBoxLayout(grp)

        grid = QGridLayout()

        # Inner Loop N slider (default 100)
        grid.addWidget(QLabel("Inner Loop Steps N per Outer Step (Ref 41):"), 0, 0)
        self.sld_inner_n = QSlider(Qt.Horizontal)
        self.sld_inner_n.setRange(1, 500)
        self.sld_inner_n.setValue(100)
        self.sld_inner_n.valueChanged.connect(self._sync_config_to_board)
        grid.addWidget(self.sld_inner_n, 0, 1)
        self.lbl_inner_n = QLabel("N = 100 (Default)")
        self.lbl_inner_n.setMinimumWidth(120)
        grid.addWidget(self.lbl_inner_n, 0, 2)

        # Seed Randomization % of Full DAC Swing
        grid.addWidget(QLabel("Seed Randomization (% of Full DAC Swing):"), 1, 0)
        self.sld_seed_pct = QSlider(Qt.Horizontal)
        self.sld_seed_pct.setRange(0, 100)
        self.sld_seed_pct.setValue(15)
        self.sld_seed_pct.valueChanged.connect(self._sync_config_to_board)
        grid.addWidget(self.sld_seed_pct, 1, 1)
        self.lbl_seed_pct = QLabel("15% (±19 LSB)")
        grid.addWidget(self.lbl_seed_pct, 1, 2)

        # Seed Mode Selector + Auto Seed Button
        grid.addWidget(QLabel("Seed Randomizer Strategy:"), 2, 0)
        self.cmb_seed_mode = QComboBox()
        self.cmb_seed_mode.addItems([
            "0 — Manual % of Full DAC Swing",
            "1 — Auto Standard Gain (1/√fan_in Optimal)",
            "2 — Cosine Annealed Decay Across Epochs",
            "3 — Thermal-Adaptive Spread (Heater Coupled)",
            "4 — Antithetic (+/-) Symmetrical Mirror Pairs",
        ])
        self.cmb_seed_mode.setCurrentIndex(1)
        self.cmb_seed_mode.currentIndexChanged.connect(self._sync_config_to_board)
        grid.addWidget(self.cmb_seed_mode, 2, 1)

        btn_auto_seed = QPushButton("Auto Seed Gain")
        btn_auto_seed.clicked.connect(self._on_auto_seed_clicked)
        grid.addWidget(btn_auto_seed, 2, 2)

        # Hidden Offset Emulator (W weight hidden offset + Power Trim DAC 38 hidden offset)
        grid.addWidget(QLabel("W Weight Hidden Offset Spread (±LSB):"), 3, 0)
        self.sld_w_hid = QSlider(Qt.Horizontal)
        self.sld_w_hid.setRange(0, 48)
        self.sld_w_hid.setValue(12)
        self.sld_w_hid.valueChanged.connect(self._sync_config_to_board)
        grid.addWidget(self.sld_w_hid, 3, 1)
        self.lbl_w_hid = QLabel("±12 LSB")
        grid.addWidget(self.lbl_w_hid, 3, 2)

        grid.addWidget(QLabel("Power Trim (DAC 38) Hidden Offset (±LSB):"), 4, 0)
        self.sld_trim_hid = QSlider(Qt.Horizontal)
        self.sld_trim_hid.setRange(0, 48)
        self.sld_trim_hid.setValue(8)
        self.sld_trim_hid.valueChanged.connect(self._sync_config_to_board)
        grid.addWidget(self.sld_trim_hid, 4, 1)
        self.lbl_trim_hid = QLabel("±8 LSB")
        grid.addWidget(self.lbl_trim_hid, 4, 2)

        lay.addLayout(grid)
        return grp

    # =========================================================================
    # Center Column: Bit-Precision Benchmark & Center Compensation Button
    # =========================================================================
    def _build_bit_precision_and_telemetry_group(self) -> QGroupBox:
        grp = QGroupBox("6. Bit-Precision Benchmark (White-Noise Ref) & Compensation Center Test")
        lay = QVBoxLayout(grp)

        # Big Bit-Precision Readout
        metrics_row = QHBoxLayout()
        self.lbl_enob_live = QLabel("Live Precision: 7.73 bits ENOB")
        self.lbl_enob_live.setStyleSheet(
            "background-color: #064e3b; color: #6ee7b7; font-size: 13px; font-weight: bold; padding: 8px; border-radius: 5px;"
        )
        metrics_row.addWidget(self.lbl_enob_live)

        self.lbl_enob_bench = QLabel("Centered (128): 4.22 bits  →  Compensated: 7.73 bits  (Δ = +3.51 bits)")
        self.lbl_enob_bench.setStyleSheet(
            "background-color: #1e293b; color: #fde047; font-weight: bold; padding: 8px; border-radius: 5px;"
        )
        metrics_row.addWidget(self.lbl_enob_bench, stretch=1)
        lay.addLayout(metrics_row)

        # Manual Center Compensation Weights button + Restore + Auto Bit-Precision Test
        btn_row = QHBoxLayout()
        self.btn_center_comp = QPushButton("Center All Compensation Weights (Set M3 & M8 = 128)")
        self.btn_center_comp.setStyleSheet("background-color: #b45309; font-weight: bold; padding: 7px;")
        self.btn_center_comp.clicked.connect(self._on_center_comp_clicked)
        btn_row.addWidget(self.btn_center_comp)

        btn_restore_comp = QPushButton("Restore Trained Compensation")
        btn_restore_comp.setStyleSheet("background-color: #0369a1; font-weight: bold; padding: 7px;")
        btn_restore_comp.clicked.connect(self._on_restore_comp_clicked)
        btn_row.addWidget(btn_restore_comp)

        btn_auto_bit = QPushButton("Run Auto Bit-Precision Test")
        btn_auto_bit.setStyleSheet("background-color: #047857; font-weight: bold; padding: 7px;")
        btn_auto_bit.clicked.connect(self._on_auto_bit_test_clicked)
        btn_row.addWidget(btn_auto_bit)
        lay.addLayout(btn_row)

        # Live Differential ADC_45 / ADC_49 & White-Noise Reference Readout
        self.lbl_adc_live = QLabel("ADC_45 / ADC_49 Signed Differential (raw - 2048): polling...")
        self.lbl_adc_live.setStyleSheet(
            "font-family: monospace; font-size: 10px; background-color: #0f172a; padding: 6px; border-radius: 4px;"
        )
        lay.addWidget(self.lbl_adc_live)

        return grp

    # =========================================================================
    # Right Column Top: Embedded 3D Loss Landscape + Detachable Pop-Up Launcher
    # =========================================================================
    def _build_3d_landscape_group(self) -> QGroupBox:
        grp = QGroupBox("7. Real-Time 3D Loss Landscape (Ref 40 2nd-Deriv Gathering Ref 41 Valleys)")
        lay = QVBoxLayout(grp)

        top_bar = QHBoxLayout()
        lbl = QLabel(
            "Shows Inner-Loop minima ('gropar', Ref 41) pushed together toward Base Model W₀ (Ref 40):"
        )
        lbl.setStyleSheet("color: #cbd5e1; font-size: 10px;")
        top_bar.addWidget(lbl, stretch=1)

        btn_step_outer = QPushButton("Step Outer Loop (Ref 40)")
        btn_step_outer.setStyleSheet("background-color: #0284c7; font-weight: bold;")
        btn_step_outer.clicked.connect(self._on_step_outer_clicked)
        top_bar.addWidget(btn_step_outer)

        btn_respread = QPushButton("Re-Spread Valleys")
        btn_respread.clicked.connect(self._on_respread_clicked)
        top_bar.addWidget(btn_respread)

        btn_popup = QPushButton("Open Detachable 3D Loss Landscape Pop-Up Window ↗")
        btn_popup.setStyleSheet(
            "background-color: #7c3aed; color: #ffffff; font-weight: bold; padding: 5px 12px;"
        )
        btn_popup.clicked.connect(self._on_open_3d_popup)
        top_bar.addWidget(btn_popup)
        lay.addLayout(top_bar)

        self.mini_3d_canvas = LossLandscape3DCanvas(compact=True, parent=self)
        lay.addWidget(self.mini_3d_canvas, stretch=1)

        return grp

    # =========================================================================
    # Right Column Bottom: PC-Computed Cell-by-Cell Self-Diagnosis Heatmaps
    # =========================================================================
    def _build_cell_diagnostics_group(self) -> QGroupBox:
        grp = QGroupBox("8. PC-Computed Cell-by-Cell Self-Diagnosis (126 Dual-2T1C Multipliers @ Comp=128)")
        lay = QVBoxLayout(grp)

        ctrl_row = QHBoxLayout()
        btn_run_diag = QPushButton("Run Cell-by-Cell Self-Diagnosis (M33 6×6, M3 8×6, M8 7×6)")
        btn_run_diag.setStyleSheet("background-color: #0284c7; font-weight: bold; padding: 6px 12px;")
        btn_run_diag.clicked.connect(self._on_run_cell_diag)
        ctrl_row.addWidget(btn_run_diag)

        self.btn_toggle_diag_view = QPushButton("Showing: Multiplier Gain (%) — Click for Zero-Offset (LSB)")
        self.btn_toggle_diag_view.setCheckable(True)
        self.btn_toggle_diag_view.toggled.connect(self._on_toggle_diag_metric)
        ctrl_row.addWidget(self.btn_toggle_diag_view)
        lay.addLayout(ctrl_row)

        self.lbl_diag_summary = QLabel("Ready to run PC cell-by-cell crosspoint characterization.")
        self.lbl_diag_summary.setStyleSheet("color: #a7f3d0; font-size: 10px;")
        lay.addWidget(self.lbl_diag_summary)

        self.diag_canvas = CellDiagnosticsCanvas(parent=self)
        lay.addWidget(self.diag_canvas, stretch=1)

        return grp

    # =========================================================================
    # Event Handlers & Board Synchronization
    # =========================================================================
    def _on_heater_arm_toggled(self, armed: bool) -> None:
        for sld in self.heater_sliders:
            sld.setEnabled(armed)
            if not armed:
                sld.blockSignals(True)
                sld.setValue(0)
                sld.blockSignals(False)

        if armed:
            self.btn_arm_heater.setText("MANUAL ARM HEATER SWITCH: ARMED (HEATERS ENABLED)")
            self.btn_arm_heater.setStyleSheet(
                "background-color: #dc2626; color: #ffffff; font-weight: bold; padding: 8px;"
            )
            self.lbl_heater_lamp.setText(
                "⚠️ WARNING: HEATER ARMED — ANALOG MATRIX BOARD CAN BECOME HOT (UP TO 45°C)! ⚠️"
            )
            self.lbl_heater_lamp.setStyleSheet(
                "background-color: #991b1b; color: #fef08a; font-weight: bold; padding: 6px; border-radius: 4px; border: 1px solid #f87171;"
            )
        else:
            self.btn_arm_heater.setText("MANUAL ARM HEATER SWITCH: DISARMED (SAFE)")
            self.btn_arm_heater.setStyleSheet(
                "background-color: #1e293b; color: #94a3b8; font-weight: bold; padding: 8px;"
            )
            self.lbl_heater_lamp.setText("SAFE: Heaters 1..4 Hardware-Disabled (Cold)")
            self.lbl_heater_lamp.setStyleSheet(
                "background-color: #064e3b; color: #a7f3d0; font-weight: bold; padding: 6px; border-radius: 4px;"
            )
        self._on_heater_slider_changed()

    def _on_heater_slider_changed(self) -> None:
        armed = self.btn_arm_heater.isChecked()
        duties = [sld.value() if armed else 0 for sld in self.heater_sliders]
        for i, d in enumerate(duties):
            self.heater_val_labels[i].setText(f"{d}% (0.2 Hz)")
        self.client.set_heaters(armed, duties)

    def _apply_heater_preset(self, duties: List[int]) -> None:
        if not self.btn_arm_heater.isChecked() and any(d > 0 for d in duties):
            self.btn_arm_heater.setChecked(True)
        for sld, d in zip(self.heater_sliders, duties):
            sld.blockSignals(True)
            sld.setValue(d)
            sld.blockSignals(False)
        self._on_heater_slider_changed()

    def _set_quick_dac_code(self, code: int) -> None:
        self.btn_osc_10hz.blockSignals(True)
        self.btn_osc_10hz.setChecked(False)
        self.btn_osc_10hz.blockSignals(False)
        self.btn_dac_ovr.blockSignals(True)
        self.btn_dac_ovr.setChecked(True)
        self.btn_dac_ovr.blockSignals(False)
        self.spn_dac_val.blockSignals(True)
        self.spn_dac_val.setValue(code)
        self.spn_dac_val.blockSignals(False)
        self._on_dac_diag_changed()

    def _on_dac_diag_changed(self) -> None:
        val = self.spn_dac_val.value()
        signed_val = val - 128
        r2r_v = (val / 256.0) * 3.30
        dac2_v = 1.65 + (val / 255.0) * 0.25
        w_v = 2.10 + (val / 255.0) * 1.00
        self.lbl_dac_diff_info.setText(
            f"Diff: {signed_val:+d} LSB | R-2R={r2r_v:.2f}V | DAC_2={dac2_v:.3f}V | Weight={w_v:.2f}V"
        )
        self.client.set_dac_mode(
            osc_10hz_en=self.btn_osc_10hz.isChecked(),
            ovr_en=self.btn_dac_ovr.isChecked(),
            bank=self.cmb_dac_bank.currentIndex(),
            ch=self.spn_dac_ch.value(),
            val=val,
        )

    def _on_mode_or_timing_changed(self) -> None:
        mode = self.cmb_mode.currentIndex()
        khz = self.sld_hadamard_khz.value()
        step_us = 1000.0 / max(50, khz)
        refresh_ms = (10.0 * 17.0 * step_us) / 1000.0
        self.lbl_hadamard_khz.setText(f"{khz} kHz ({step_us:.2f} µs Settle | {refresh_ms:.2f} ms Refresh)")

        if mode == 1:
            # Base Model Training (Ref 40) occupies 100% of time between refresh pulses
            self.sld_meas_win.setEnabled(False)
            self.lbl_meas_win.setText("100% (Locked for Ref 40 Base Training)")
        else:
            self.sld_meas_win.setEnabled(True)
            pct = self.sld_meas_win.value()
            self.lbl_meas_win.setText(f"Max {pct}% of Refresh Period (Ref 42 Cap)")

        if mode == 3:
            # Operation mode (Ref 42) zeroes out hidden offsets
            self.lbl_w_hid.setText("0 LSB (Ref 42 Zeroed)")
            self.lbl_trim_hid.setText("0 LSB (Ref 42 Zeroed)")
        else:
            self.lbl_w_hid.setText(f"±{self.sld_w_hid.value()} LSB")
            self.lbl_trim_hid.setText(f"±{self.sld_trim_hid.value()} LSB")

        self._sync_config_to_board()

    def _on_auto_seed_clicked(self) -> None:
        self.cmb_seed_mode.setCurrentIndex(1)
        self.sld_seed_pct.setValue(18)  # Optimal 1/sqrt(fan_in) standard seed gain
        self._sync_config_to_board()

    def _sync_config_to_board(self) -> None:
        mode = self.cmb_mode.currentIndex()
        jumper = self.cmb_jumper.currentIndex() + 1
        leds = (1 if self.chk_comp_led.isChecked() else 0) | (2 if self.chk_mat33_led.isChecked() else 0)
        win_pct = 100 if mode == 1 else self.sld_meas_win.value()
        khz = self.sld_hadamard_khz.value()
        inner_n = self.sld_inner_n.value()
        seed_pct = self.sld_seed_pct.value()
        seed_mode = self.cmb_seed_mode.currentIndex()
        w_hid = self.sld_w_hid.value()
        trim_hid = self.sld_trim_hid.value()

        self.lbl_inner_n.setText(f"N = {inner_n}")
        self.lbl_seed_pct.setText(f"{seed_pct}% (±{int(seed_pct * 1.27)} LSB)")
        if mode != 3:
            self.lbl_w_hid.setText(f"±{w_hid} LSB")
            self.lbl_trim_hid.setText(f"±{trim_hid} LSB")

        self.client.set_config(
            mode=mode,
            jumper_mode=jumper,
            led_switches=leds,
            max_meas_win_pct=win_pct,
            hadamard_khz=khz,
            inner_loop_n=inner_n,
            seed_pct=seed_pct,
            seed_mode=seed_mode,
            w_hid_mag=w_hid,
            trim_hid_mag=trim_hid,
        )

    def _on_center_comp_clicked(self) -> None:
        self.client.center_compensation_weights()
        self._on_poll_tick()

    def _on_restore_comp_clicked(self) -> None:
        self.client.restore_compensation_weights()
        self._on_poll_tick()

    def _on_auto_bit_test_clicked(self) -> None:
        u_bits, c_bits, delta = self.client.run_auto_bit_precision_test()
        self.lbl_enob_bench.setText(
            f"Centered (128): {u_bits:.2f} bits  →  Compensated: {c_bits:.2f} bits  (Δ = +{delta:.2f} bits)"
        )
        self._on_poll_tick()

    def _on_step_outer_clicked(self) -> None:
        self.client.step_outer_loop()
        self._on_poll_tick()

    def _on_respread_clicked(self) -> None:
        self.mini_3d_canvas.clear_trails()
        if self.popup_3d is not None:
            self.popup_3d.canvas.clear_trails()
        self.client.reset_valleys_spread()
        self._on_poll_tick()

    def _on_open_3d_popup(self) -> None:
        if self.popup_3d is None:
            self.popup_3d = LossLandscapePopUpWindow(self.client, parent=self)
        self.popup_3d.show()
        self.popup_3d.raise_()
        self.popup_3d.activateWindow()
        self.popup_3d.refresh_view()

    def _on_run_cell_diag(self) -> None:
        report = self.diag_engine.run_full_cell_diagnostics()
        self.diag_canvas.render_report(report)
        self.lbl_diag_summary.setText(report.summary_text)
        self._on_poll_tick()

    def _on_toggle_diag_metric(self, show_offset: bool) -> None:
        self.diag_canvas.show_offset_mode = show_offset
        if show_offset:
            self.btn_toggle_diag_view.setText("Showing: Zero-Offset (ADC LSB) — Click for Multiplier Gain (%)")
        else:
            self.btn_toggle_diag_view.setText("Showing: Multiplier Gain (%) — Click for Zero-Offset (LSB)")
        if self.diag_engine.last_report is not None:
            self.diag_canvas.render_report(self.diag_engine.last_report)

    def _on_ping_board(self) -> None:
        resp = self.client.send_ascii("VERSION")
        self.lbl_conn_status.setText(resp[:85])

    def _on_poll_tick(self) -> None:
        t = self.client.poll_telemetry()
        # Keep Heater Watchdog alive when armed
        if self.btn_arm_heater.isChecked():
            duties = [sld.value() for sld in self.heater_sliders]
            self.client.set_heaters(True, duties)

        self.lbl_conn_status.setText(t.status_text)
        self.lbl_enob_live.setText(
            f"Live Precision: {t.enob_bits:.2f} bits ENOB  (MSE={t.mse_q14})"
        )
        delta = t.enob_comp_bits - t.enob_uncomp_bits
        self.lbl_enob_bench.setText(
            f"Centered (128): {t.enob_uncomp_bits:.2f} bits  →  "
            f"Compensated: {t.enob_comp_bits:.2f} bits  (Δ = {delta:+.2f} bits)"
        )

        adc45_str = " ".join(f"{v:+5d}" for v in t.adc45_sig)
        adc49_str = " ".join(f"{v:+5d}" for v in t.adc49_sig)
        refx_str  = " ".join(f"{v:+4d}" for v in t.ref_x)
        self.lbl_adc_live.setText(
            f"Locked White-Noise x_ref (Stratum {t.stratum_idx}/9, Refresh #{t.refresh_cnt}): [{refx_str}]\n"
            f"ADC_45 Diff (raw-2048): [{adc45_str}]  |  ADC_49 Diff (raw-2048): [{adc49_str}]"
        )

        # Update embedded 3D mini-viewport and detachable pop-up window (if open)
        self.mini_3d_canvas.update_landscape(
            self.client.valley_coords,
            t,
            self.client.sim_comp_centered,
        )
        if self.popup_3d is not None and self.popup_3d.isVisible():
            self.popup_3d.refresh_view()

