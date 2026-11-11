#!/home/olle/anaconda3/bin/python
"""
bit_slicing_live_gui.py
=======================
Inverted MAML (Patent Pending SE 2630397-4) - Open Science Hardware

Real-Time GUI for 2-Beat Interleaved Analog Bit Slicing & Thermal Stress:
- Zero hardware interference: Reads atomic JSON ring buffer/status files.
- UI Layout:
    1. Top Banner / Status HUD:
       - Thermal Heater state (30% duty) & Phase countdown
       - Training state (SGD active vs off)
       - Live KPI Highlights:
           * Combined 8-Bit ENOB (Target 8 b)
           * MSB 4-Bit Slice ENOB & Loss
           * LSB 4-Bit Slice ENOB & Loss
       - Hardware saturation margin (W8 min/max)
    2. Main Graphs (3 Plots - Vattenfall borttagen för maximal översikt):
       - Graph 1 (Top / Prominent): Combined 8-Bit Recombined Precision (Target 8 b ENOB)
       - Graph 2 (Middle): 4-Bit MSB Slice Performance (Dual Axis: ENOB bits & Loss LSB²)
       - Graph 3 (Bottom): 4-Bit LSB Slice Performance (Dual Axis: ENOB bits & Loss LSB²)
    3. Tydliga ON/OFF vertikala streckade linjer:
       - Grön streckad linje (--): Training ON (Active SGD)
       - Röd streckad linje (--): Training OFF (Ablation W8=0)
       - Bakgrunds-shading: Varm bärnsten för Heater ON, Sval blå för Heater OFF
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

REPO_ROOT = Path(__file__).resolve().parent.parent
RING_BUFFER_JSON = REPO_ROOT / "FPGA_code" / "logs" / "bit_slicing" / "slicing_ring_buffer.json"
LATEST_STATUS_JSON = REPO_ROOT / "FPGA_code" / "logs" / "bit_slicing" / "slicing_latest_status.json"

DARK_STYLE = """
QMainWindow {
    background-color: #0f172a;
}
QWidget {
    background-color: #0f172a;
    color: #f8fafc;
    font-family: 'Segoe UI', 'Ubuntu', 'Roboto', sans-serif;
    font-size: 11px;
}
QGroupBox {
    border: 1px solid #334155;
    border-radius: 8px;
    margin-top: 8px;
    padding-top: 8px;
    font-weight: bold;
    background-color: #1e293b;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    color: #38bdf8;
    font-size: 12px;
}
QLabel {
    color: #e2e8f0;
}
"""

class BitSlicingLiveGUI(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Inverted MAML: 2-Beat Analog Bit Slicing & Thermal Stress Monitor (8-Bit Precision)")
        self.resize(1350, 950)
        self.setStyleSheet(DARK_STYLE)

        self.history = []
        self.latest_status = {}

        self._init_ui()

        # Update timer (reads ring buffer file every 250 ms)
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.poll_data)
        self.timer.start(250)

    def _init_ui(self):
        main_widget = QtWidgets.QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QtWidgets.QVBoxLayout(main_widget)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(8)

        # -------------------------------------------------------------
        # TOP HUD BANNER
        # -------------------------------------------------------------
        hud_group = QtWidgets.QGroupBox("Hardware Telemetry & Operating State")
        hud_layout = QtWidgets.QHBoxLayout(hud_group)
        hud_layout.setContentsMargins(15, 8, 15, 8)
        hud_layout.setSpacing(15)

        self.lbl_hw = QtWidgets.QLabel("<b>Hardware:</b> Card 1 (T120 SoC)<br><b>Attenuator:</b> 1k/3.3k (M33: ±60 LSB)")
        hud_layout.addWidget(self.lbl_hw)

        self.lbl_heater = QtWidgets.QLabel("<b>Thermal Heater:</b> OFF (0%)<br>Phase: Cold")
        self.lbl_heater.setStyleSheet("background-color: #0f172a; padding: 6px; border-radius: 6px; border: 1px solid #334155;")
        hud_layout.addWidget(self.lbl_heater)

        self.lbl_training = QtWidgets.QLabel("<b>Regulation:</b> Mode A Active<br>K=1, LR=0.02, L2=768")
        self.lbl_training.setStyleSheet("background-color: #0f172a; padding: 6px; border-radius: 6px; border: 1px solid #334155;")
        hud_layout.addWidget(self.lbl_training)

        # Precision KPI Highlights
        self.lbl_enob_comb = QtWidgets.QLabel("<font color='#38bdf8' size='+2'><b>--- b</b></font><br>Combined 8-Bit")
        self.lbl_enob_comb.setAlignment(QtCore.Qt.AlignCenter)
        self.lbl_enob_comb.setStyleSheet("background-color: #0369a1; padding: 6px 12px; border-radius: 6px; font-weight: bold;")
        hud_layout.addWidget(self.lbl_enob_comb)

        self.lbl_enob_msb = QtWidgets.QLabel("<font color='#4ade80' size='+1'><b>--- b</b></font><br>MSB Slice (4-Bit)")
        self.lbl_enob_msb.setAlignment(QtCore.Qt.AlignCenter)
        self.lbl_enob_msb.setStyleSheet("background-color: #14532d; padding: 6px 12px; border-radius: 6px;")
        hud_layout.addWidget(self.lbl_enob_msb)

        self.lbl_enob_lsb = QtWidgets.QLabel("<font color='#fbbf24' size='+1'><b>--- b</b></font><br>LSB Slice (4-Bit)")
        self.lbl_enob_lsb.setAlignment(QtCore.Qt.AlignCenter)
        self.lbl_enob_lsb.setStyleSheet("background-color: #713f12; padding: 6px 12px; border-radius: 6px;")
        hud_layout.addWidget(self.lbl_enob_lsb)

        self.lbl_w8_margin = QtWidgets.QLabel("<b>W8 Margin (Rail ±120):</b><br>MSB: [--, --] | LSB: [--, --]")
        hud_layout.addWidget(self.lbl_w8_margin)

        main_layout.addWidget(hud_group)

        # -------------------------------------------------------------
        # 3 PERFORMANCE PLOTS
        # -------------------------------------------------------------
        self.fig = Figure(facecolor="#1e293b", figsize=(12, 8.5))
        self.canvas = FigureCanvas(self.fig)
        main_layout.addWidget(self.canvas, stretch=1)

        gs = self.fig.add_gridspec(3, 1, height_ratios=[1.3, 1.0, 1.0], hspace=0.38)
        self.ax_comb = self.fig.add_subplot(gs[0])
        self.ax_msb = self.fig.add_subplot(gs[1])
        self.ax_lsb = self.fig.add_subplot(gs[2])

        self._style_axis(self.ax_comb, "Combined 8-Bit Precision (Shift-and-Add Recombination: 16·Y_MSB + Y_LSB)", "Combined ENOB (bits)")
        self._style_axis(self.ax_msb, "MSB 4-Bit Slice Performance (Beat 2k)", "MSB ENOB (bits)")
        self._style_axis(self.ax_lsb, "LSB 4-Bit Slice Performance (Beat 2k+1)", "LSB ENOB (bits)")

    def _style_axis(self, ax, title, ylabel):
        ax.set_facecolor("#0f172a")
        ax.tick_params(colors="#94a3b8", labelsize=9)
        ax.xaxis.label.set_color("#94a3b8")
        ax.yaxis.label.set_color("#94a3b8")
        ax.set_title(title, color="#f8fafc", fontsize=11, fontweight="bold", pad=6)
        ax.set_ylabel(ylabel, color="#94a3b8", fontsize=9.5, fontweight="bold")
        ax.grid(True, linestyle="--", alpha=0.25, color="#64748b")
        for spine in ax.spines.values():
            spine.set_color("#334155")

    def _draw_phase_spans(self, ax, history: list[dict]):
        """Draw background shading for Heater ON / Heater OFF phases."""
        if not history:
            return
        n = len(history)
        start_idx = 0
        cur_heater = history[0].get("heater_on", False)

        for i in range(1, n):
            h_state = history[i].get("heater_on", False)
            if h_state != cur_heater or i == n - 1:
                end_p = history[i]["pair"]
                start_p = history[start_idx]["pair"]
                if cur_heater:
                    # Heater ON: Warm amber tint
                    ax.axvspan(start_p, end_p, color="#7c2d12", alpha=0.30, zorder=0)
                else:
                    # Heater OFF: Cool slate blue tint
                    ax.axvspan(start_p, end_p, color="#0c4a6e", alpha=0.25, zorder=0)
                cur_heater = h_state
                start_idx = i

    def _draw_training_toggle_lines(self, ax, history: list[dict]):
        """Draw clearly dashed vertical lines when Training toggles ON or OFF."""
        if not history or len(history) < 2:
            return

        added_on_label = False
        added_off_label = False

        for i in range(1, len(history)):
            prev_r = history[i-1].get("reglering_on", True)
            cur_r = history[i].get("reglering_on", True)
            if prev_r != cur_r:
                p = history[i]["pair"]
                if cur_r:
                    # Switched to Training ON (Active SGD)
                    lbl = "Training ON (SGD)" if not added_on_label else None
                    ax.axvline(x=p, color="#10b981", linestyle="--", linewidth=1.8, alpha=0.95, zorder=4, label=lbl)
                    added_on_label = True
                else:
                    # Switched to Training OFF (Ablation W8=0)
                    lbl = "Training OFF (Ablation)" if not added_off_label else None
                    ax.axvline(x=p, color="#ef4444", linestyle="--", linewidth=1.8, alpha=0.95, zorder=4, label=lbl)
                    added_off_label = True

    def poll_data(self):
        # 1. Read latest status
        if LATEST_STATUS_JSON.exists():
            try:
                with open(LATEST_STATUS_JSON, "r") as f:
                    self.latest_status = json.load(f)
            except Exception:
                pass

        # 2. Read ring buffer history
        if RING_BUFFER_JSON.exists():
            try:
                with open(RING_BUFFER_JSON, "r") as f:
                    data = json.load(f)
                    self.history = data.get("history", [])
            except Exception:
                pass

        self.update_hud()
        self.update_plots()

    def update_hud(self):
        s = self.latest_status
        if not s:
            return

        heater_on = s.get("heater_on", False)
        heater_duty = s.get("heater_duty_pct", 30.0)
        t_left_h = s.get("heater_time_left_s", 0)
        reg_on = s.get("reglering_on", True)
        t_left_r = s.get("reglering_time_left_s", 0)

        if heater_on:
            self.lbl_heater.setText(f"<b>Thermal Heater:</b> <font color='#ef4444'><b>ON ({heater_duty:.0f}% @ 1Hz)</b></font><br>Time Left: {int(t_left_h)}s")
            self.lbl_heater.setStyleSheet("background-color: #450a0a; padding: 6px; border-radius: 6px; border: 1.5px solid #ef4444;")
        else:
            self.lbl_heater.setText(f"<b>Thermal Heater:</b> <font color='#38bdf8'><b>OFF (Cold Phase)</b></font><br>Time Left: {int(t_left_h)}s")
            self.lbl_heater.setStyleSheet("background-color: #0f172a; padding: 6px; border-radius: 6px; border: 1px solid #334155;")

        if reg_on:
            self.lbl_training.setText(f"<b>Regulation:</b> <font color='#4ade80'><b>Mode A ACTIVE</b></font><br>SGD Active ({int(t_left_r)}s left)")
            self.lbl_training.setStyleSheet("background-color: #052e16; padding: 6px; border-radius: 6px; border: 1.5px solid #10b981;")
        else:
            self.lbl_training.setText(f"<b>Regulation:</b> <font color='#f87171'><b>OFF (W8=0 Ablation)</b></font><br>Free Drift ({int(t_left_r)}s left)")
            self.lbl_training.setStyleSheet("background-color: #450a0a; padding: 6px; border-radius: 6px; border: 1.5px solid #ef4444;")

        # KPI
        comb_enob = s.get("comb_enob", 0.0)
        msb_enob = s.get("msb_enob", 0.0)
        lsb_enob = s.get("lsb_enob", 0.0)
        # Sann Kontinuerlig Deterministisk 8-Bit Recombination ENOB:
        # När MSB >= 4.0 bitar är alla 4 bitar deterministiska (4.0 + LSB).
        # När MSB närmar sig 4.0 bitar skalas LSB-bidraget mjukt och kontinuerligt utan tröskelklipp.
        comb_display = min(9.5, max(0.0, min(4.0, msb_enob) + lsb_enob * min(1.0, max(0.0, msb_enob / 4.0))))

        self.lbl_enob_comb.setText(f"<font color='#38bdf8' size='+2'><b>{comb_display:.2f} b</b></font><br>Combined 8-Bit")
        self.lbl_enob_msb.setText(f"<font color='#4ade80' size='+1'><b>{msb_enob:.2f} b</b></font><br>MSB Slice (4-Bit)")
        self.lbl_enob_lsb.setText(f"<font color='#fbbf24' size='+1'><b>{lsb_enob:.2f} b</b></font><br>LSB Slice (4-Bit)")

        w8_msb = s.get("w8_msb_range", [0, 0])
        w8_lsb = s.get("w8_lsb_range", [0, 0])
        self.lbl_w8_margin.setText(f"<b>W8 Margin (Rail ±120):</b><br>MSB: [{w8_msb[0]:+3d}, {w8_msb[1]:+3d}]<br>LSB: [{w8_lsb[0]:+3d}, {w8_lsb[1]:+3d}]")

    def update_plots(self):
        if not self.history or len(self.history) < 2:
            return

        pairs = [h["pair"] for h in self.history]
        msb_enob = [h["enob_msb"] for h in self.history]
        lsb_enob = [h["enob_lsb"] for h in self.history]
        msb_loss = [h.get("loss_msb", 2500.0) for h in self.history]
        lsb_loss = [h.get("loss_lsb", 2500.0) for h in self.history]

        # Sann Kontinuerlig Deterministisk 8-Bit Recombination ENOB:
        comb_enob = []
        for m, l in zip(msb_enob, lsb_enob):
            c_val = min(9.5, max(0.0, min(4.0, m) + l * min(1.0, max(0.0, m / 4.0))))
            comb_enob.append(c_val)

        # -------------------------------------------------------------
        # 1. Combined 8-Bit Plot (Top)
        # -------------------------------------------------------------
        self.ax_comb.clear()
        self._style_axis(self.ax_comb, "Combined 8-Bit Precision (Shift-and-Add Recombination: 16·Y_MSB + Y_LSB)", "Combined ENOB (bits)")
        self._draw_phase_spans(self.ax_comb, self.history)
        self._draw_training_toggle_lines(self.ax_comb, self.history)

        l1 = self.ax_comb.plot(pairs, comb_enob, color="#38bdf8", linewidth=2.0, zorder=5, label="Combined 8-Bit ENOB")
        self.ax_comb.axhline(8.0, color="#f59e0b", linestyle=":", linewidth=1.5, alpha=0.85, label="8.0 b Target")
        self.ax_comb.axhline(4.0, color="#64748b", linestyle="--", linewidth=1.0, alpha=0.5, label="4.0 b Base Floor")
        self.ax_comb.set_ylim(0.0, 9.5)
        self.ax_comb.legend(loc="upper right", facecolor="#1e293b", edgecolor="#334155", fontsize=8.5)

        # -------------------------------------------------------------
        # 2. MSB 4-Bit Plot (Middle, Dual Axis: ENOB & Loss)
        # -------------------------------------------------------------
        self.ax_msb.clear()
        self._style_axis(self.ax_msb, "MSB 4-Bit Slice Performance (Beat 2k)", "MSB ENOB (bits)")
        self._draw_phase_spans(self.ax_msb, self.history)
        self._draw_training_toggle_lines(self.ax_msb, self.history)

        l_msb_enob = self.ax_msb.plot(pairs, msb_enob, color="#4ade80", linewidth=1.8, zorder=5, label="MSB ENOB (bits)")
        self.ax_msb.axhline(4.0, color="#f59e0b", linestyle="--", linewidth=1.0, alpha=0.8, label="4.0 b Floor")
        self.ax_msb.set_ylim(0.0, 6.5)

        # Twin axis for loss
        ax_msb_right = getattr(self, "ax_msb_right", None)
        if ax_msb_right is None:
            self.ax_msb_right = self.ax_msb.twinx()
            ax_msb_right = self.ax_msb_right
        else:
            ax_msb_right.clear()
        ax_msb_right.set_ylabel("MSB Loss (LSB²)", color="#f87171", fontsize=9)
        ax_msb_right.tick_params(colors="#94a3b8", labelsize=8)
        l_msb_loss = ax_msb_right.plot(pairs, msb_loss, color="#f87171", linewidth=1.2, alpha=0.65, label="MSB Loss")
        ax_msb_right.spines['right'].set_color("#334155")
        ax_msb_right.spines['top'].set_visible(False)

        lines_msb = l_msb_enob + l_msb_loss
        labels_msb = [l.get_label() for l in lines_msb]
        self.ax_msb.legend(lines_msb, labels_msb, loc="upper right", facecolor="#1e293b", edgecolor="#334155", fontsize=8)

        # -------------------------------------------------------------
        # 3. LSB 4-Bit Plot (Bottom, Dual Axis: ENOB & Loss)
        # -------------------------------------------------------------
        self.ax_lsb.clear()
        self._style_axis(self.ax_lsb, "LSB 4-Bit Slice Performance (Beat 2k+1)", "LSB ENOB (bits)")
        self._draw_phase_spans(self.ax_lsb, self.history)
        self._draw_training_toggle_lines(self.ax_lsb, self.history)

        l_lsb_enob = self.ax_lsb.plot(pairs, lsb_enob, color="#fbbf24", linewidth=1.8, zorder=5, label="LSB ENOB (bits)")
        self.ax_lsb.axhline(4.0, color="#f59e0b", linestyle="--", linewidth=1.0, alpha=0.8, label="4.0 b Floor")
        self.ax_lsb.set_ylim(0.0, 6.5)
        self.ax_lsb.set_xlabel("2-Beat Pair Index (2 Refresh Cycles per Point)", color="#94a3b8", fontsize=9.5)

        # Twin axis for loss
        ax_lsb_right = getattr(self, "ax_lsb_right", None)
        if ax_lsb_right is None:
            self.ax_lsb_right = self.ax_lsb.twinx()
            ax_lsb_right = self.ax_lsb_right
        else:
            ax_lsb_right.clear()
        ax_lsb_right.set_ylabel("LSB Loss (LSB²)", color="#f87171", fontsize=9)
        ax_lsb_right.tick_params(colors="#94a3b8", labelsize=8)
        l_lsb_loss = ax_lsb_right.plot(pairs, lsb_loss, color="#f87171", linewidth=1.2, alpha=0.65, label="LSB Loss")
        ax_lsb_right.spines['right'].set_color("#334155")
        ax_lsb_right.spines['top'].set_visible(False)

        lines_lsb = l_lsb_enob + l_lsb_loss
        labels_lsb = [l.get_label() for l in lines_lsb]
        self.ax_lsb.legend(lines_lsb, labels_lsb, loc="upper right", facecolor="#1e293b", edgecolor="#334155", fontsize=8)

        self.canvas.draw_idle()

def main():
    app = QtWidgets.QApplication(sys.argv)
    gui = BitSlicingLiveGUI()
    gui.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
