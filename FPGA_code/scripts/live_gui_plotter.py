#!/home/olle/anaconda3/bin/python
"""
live_gui_plotter.py - Real-Time Matplotlib GUI Window for Silicon Neural Training
==================================================================================
Spawns an interactive GUI window on the desktop (X11 / Wayland) showing live
convergence curves for Loss (RMSE) and Bit Precision (ENOB) updating dynamically
every 1.0 second as the Trion T120 trains in physical silicon.
"""

import os
import sys
import json
import time
from pathlib import Path
import numpy as np

import matplotlib
# Use interactive GUI backend
matplotlib.use("Qt5Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PROGRESS_FILE = REPO_ROOT / "FPGA_code" / "docs" / "live_10min_training_progress.json"

plt.style.use("seaborn-v0_8-darkgrid" if "seaborn-v0_8-darkgrid" in plt.style.available else "default")

fig, (ax_loss, ax_enob) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
fig.canvas.manager.set_window_title("Inverted MAML — Live Silicon Training Monitor (T120 Hardware)")
fig.patch.set_facecolor("#0F172A")

for ax in (ax_loss, ax_enob):
    ax.set_facecolor("#1E293B")
    ax.tick_params(colors="#94A3B8")
    ax.xaxis.label.set_color("#CBD5E1")
    ax.yaxis.label.set_color("#CBD5E1")
    ax.grid(True, linestyle=":", alpha=0.3, color="#475569")

# Historical data stores
time_history = []
rmse_history = []
enob_history = []

line_rmse_raw, = ax_loss.plot([], [], color="#EF4444", alpha=0.4, linewidth=1.0, label="Instantaneous RMSE (Raw)")
line_rmse_smooth, = ax_loss.plot([], [], color="#F87171", linewidth=2.2, label="Moving Average (Smooth)")
line_enob_raw, = ax_enob.plot([], [], color="#34D399", alpha=0.4, linewidth=1.0, label="Instantaneous ENOB (Raw)")
line_enob_smooth, = ax_enob.plot([], [], color="#10B981", linewidth=2.2, label="Moving Average (Smooth)")

ax_loss.set_ylabel("Hardware Loss (RMSE in LSB)", fontsize=10, fontweight="bold")
ax_loss.set_title("Live Silicon Training Dynamics (Mode C: Sigmoid Bypass | 100 Hz Native Refresh)",
                  fontsize=12, fontweight="bold", color="#F8FAFC", pad=10)
ax_loss.legend(loc="upper right", facecolor="#334155", edgecolor="#475569", labelcolor="#F1F5F9", fontsize=8.5)

ax_enob.set_xlabel("Elapsed Training Time (seconds)", fontsize=10, fontweight="bold")
ax_enob.set_ylabel("Effective Bit Precision (ENOB)", fontsize=10, fontweight="bold")
ax_enob.legend(loc="lower right", facecolor="#334155", edgecolor="#475569", labelcolor="#F1F5F9", fontsize=8.5)

# Text HUD
hud_text = ax_loss.text(0.02, 0.92, "", transform=ax_loss.transAxes,
                        color="#38BDF8", fontsize=9.5, fontweight="bold",
                        bbox=dict(boxstyle="round,pad=0.5", facecolor="#0F172A", edgecolor="#38BDF8", alpha=0.9))


def update(frame):
    if not PROGRESS_FILE.exists():
        return line_rmse_raw, line_rmse_smooth, line_enob_raw, line_enob_smooth, hud_text

    try:
        with open(PROGRESS_FILE, "r") as f:
            data = json.load(f)
    except Exception:
        return line_rmse_raw, line_rmse_smooth, line_enob_raw, line_enob_smooth, hud_text

    elapsed = data.get("elapsed_sec", 0.0)
    duration = data.get("duration_sec", 600.0)
    pct = data.get("progress_pct", 0.0)
    epoch = data.get("latest_epoch", 0)
    rmse = data.get("latest_rmse", 0.0)
    enob = data.get("latest_enob_comp", 0.0)
    full = data.get("full_history")
    if full and len(full.get("time", [])) > 0:
        t_arr = np.array(full["time"])
        r_arr = np.array(full["rmse"])
        e_arr = np.array(full["enob"])
    else:
        tail = data.get("trajectory_tail", [])
        if tail and time_history and tail[0].get("elapsed_sec", 0.0) < time_history[-1] - 5.0:
            time_history.clear()
            rmse_history.clear()
            enob_history.clear()

        for pt in tail:
            t_pt = pt.get("elapsed_sec", 0.0)
            if not time_history or t_pt > time_history[-1] + 0.1:
                time_history.append(t_pt)
                rmse_history.append(pt.get("rmse", 0.0))
                enob_history.append(pt.get("enob_comp", 0.0))

        if not time_history:
            return line_rmse_raw, line_rmse_smooth, line_enob_raw, line_enob_smooth, hud_text

        t_arr = np.array(time_history)
        r_arr = np.array(rmse_history)
        e_arr = np.array(enob_history)

    # Smooth curves
    win = min(10, len(r_arr))
    if win > 1:
        r_smooth = np.convolve(r_arr, np.ones(win)/win, mode='same')
        e_smooth = np.convolve(e_arr, np.ones(win)/win, mode='same')
    else:
        r_smooth = r_arr
        e_smooth = e_arr

    line_rmse_raw.set_data(t_arr, r_arr)
    line_rmse_smooth.set_data(t_arr, r_smooth)
    line_enob_raw.set_data(t_arr, e_arr)
    line_enob_smooth.set_data(t_arr, e_smooth)

    # Autoscale limits
    ax_loss.set_xlim(0, max(duration, t_arr[-1] + 10))
    ax_loss.set_ylim(0, max(800, np.max(r_arr) * 1.15))

    ax_enob.set_xlim(0, max(duration, t_arr[-1] + 10))
    ax_enob.set_ylim(0, max(5.5, np.max(e_arr) + 0.5))

    # Update HUD
    rem_sec = max(0, int(duration - elapsed))
    hud_str = (f"Epok: {epoch} | Tid: {elapsed:.0f}s / {duration:.0f}s ({pct:.1f}%)\n"
               f"RMSE: {rmse:.1f} LSB | ENOB: {enob:.2f} bitar | Kvar: {rem_sec}s")
    hud_text.set_text(hud_str)

    return line_rmse_raw, line_rmse_smooth, line_enob_raw, line_enob_smooth, hud_text


def main():
    ani = FuncAnimation(fig, update, interval=1000, blit=False)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()

