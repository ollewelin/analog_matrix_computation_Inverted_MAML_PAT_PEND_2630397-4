#!/home/olle/anaconda3/bin/python
"""
plot_rev2_opt2_5ms_results.py
Generates high-resolution comparative figures for Rev 2.0 Option 2 run at 5.0 ms.
"""

import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Load datasets
f_rev14 = REPO_ROOT / "FPGA_code/logs/mode_a_extended_training/mode_a_500ep_broadened_4p5to5p5ms_reg1024_lr0p08_swing80_identical_k20_llm.json"
f_raw = REPO_ROOT / "FPGA_code/logs/mode_a_extended_training/mode_a_500ep_1strata_5ms_rev2_1k3p9k_1strata_5ms_t20a.json"
f_opt2 = REPO_ROOT / "FPGA_code/logs/mode_a_extended_training/mode_a_500ep_1strata_5ms_rev2_opt2_dc_lift_1strata_5ms.json"

with open(f_rev14) as f:
    d_rev14 = json.load(f)["epochs"]
with open(f_raw) as f:
    d_raw = json.load(f)["epochs"]
with open(f_opt2) as f:
    d_opt2 = json.load(f)["epochs"]

epochs = [e["epoch"] for e in d_opt2]
loss_opt2 = [e["loss_lsb2"] for e in d_opt2]
enob_opt2 = [e["enob_bits"] for e in d_opt2]
w8_opt2 = np.array([e["w8_diag"] for e in d_opt2])
w8_row6 = np.array([e.get("w8_row6", [0]*6) for e in d_opt2])

loss_raw = [e["loss_lsb2"] for e in d_raw]
enob_raw = [e["enob_bits"] for e in d_raw]

loss_rev14 = [e["loss_lsb2"] for e in d_rev14]
enob_rev14 = [e["enob_bits"] for e in d_rev14]

# Rolling window smooth (window = 11)
def smooth(y, box_pts=11):
    box = np.ones(box_pts) / box_pts
    return np.convolve(y, box, mode="same")

fig, axes = plt.subplots(2, 2, figsize=(16, 11), dpi=200)
plt.subplots_adjust(hspace=0.28, wspace=0.22)

# Panel 1: Loss trajectory
ax1 = axes[0, 0]
ax1.plot(epochs, loss_raw, color="#d9534f", alpha=0.3, label="Rev 2.0 Raw (Unshifted) Raw")
ax1.plot(epochs, smooth(loss_raw), color="#d9534f", lw=2, label="Rev 2.0 Raw Smoothed")
ax1.plot(epochs, loss_opt2, color="#0275d8", alpha=0.3, label="Rev 2.0 Option 2 (DC-Lift) Raw")
ax1.plot(epochs, smooth(loss_opt2), color="#0275d8", lw=2.5, label="Rev 2.0 Option 2 Smoothed")
ax1.axvline(100, color="gray", linestyle="--", lw=1.2, label="Ep 100: Smart Baseline")
ax1.axvline(200, color="green", linestyle="--", lw=1.2, label="Ep 200: Active Train (LR=0.08x)")
ax1.set_title("A. Loss Trajectory Across 500 Epochs (t = 5.0 ms)", fontsize=13, fontweight="bold")
ax1.set_xlabel("Epoch", fontsize=11)
ax1.set_ylabel("Loss (LSB²)", fontsize=11)
ax1.set_yscale("log")
ax1.grid(True, linestyle=":", alpha=0.6)
ax1.legend(loc="upper right", fontsize=8.5)

# Panel 2: ENOB resolution
ax2 = axes[0, 1]
ax2.plot(epochs, enob_rev14, color="#5cb85c", alpha=0.25, label="Rev 1.4 (5.1k) Raw")
ax2.plot(epochs, smooth(enob_rev14), color="#5cb85c", lw=1.5, label="Rev 1.4 Smoothed (Ref)")
ax2.plot(epochs, smooth(enob_raw), color="#d9534f", lw=2, label="Rev 2.0 Raw (3.9k)")
ax2.plot(epochs, smooth(enob_opt2), color="#0275d8", lw=2.5, label="Rev 2.0 Option 2 (DC-Lift)")
ax2.axvline(100, color="gray", linestyle="--", lw=1.2)
ax2.axvline(200, color="green", linestyle="--", lw=1.2)
ax2.set_title("B. Effective Number of Bits (ENOB) at 5.0 ms", fontsize=13, fontweight="bold")
ax2.set_xlabel("Epoch", fontsize=11)
ax2.set_ylabel("Resolution (Bits ENOB)", fontsize=11)
ax2.set_ylim(2.5, 6.2)
ax2.grid(True, linestyle=":", alpha=0.6)
ax2.legend(loc="lower right", fontsize=8.5)

# Panel 3: Matrix 8 Adaptive Weight Trajectories
ax3 = axes[1, 0]
colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]
for c in range(6):
    ax3.plot(epochs, w8_opt2[:, c], color=colors[c], lw=1.6, label=f"Col {c+1} W8[{c},{c}]")
ax3.axvline(100, color="gray", linestyle="--", lw=1.2)
ax3.axvline(200, color="green", linestyle="--", lw=1.2)
ax3.axhline(120, color="red", linestyle=":", lw=1, alpha=0.5, label="±120 Clamp Rail")
ax3.axhline(-120, color="red", linestyle=":", lw=1, alpha=0.5)
ax3.set_title("C. Matrix 8 Diagonal Weight Trajectories (Zero Clamping)", fontsize=13, fontweight="bold")
ax3.set_xlabel("Epoch", fontsize=11)
ax3.set_ylabel("Weight Value (DAC LSB)", fontsize=11)
ax3.set_ylim(-130, 130)
ax3.grid(True, linestyle=":", alpha=0.6)
ax3.legend(loc="upper left", fontsize=8, ncol=2)

# Panel 4: Per-Column Static Error Comparison (Phase 2 vs Phase 1)
ax4 = axes[1, 1]
errs_raw_p2 = np.array([np.array(e["adc49"]) - np.array(e["z_target"]) for e in d_raw[100:200]])
errs_opt2_p2 = np.array([np.array(e["adc49"]) - np.array(e["z_target"]) for e in d_opt2[100:200]])

mean_raw = np.mean(errs_raw_p2, axis=0)
mean_opt2 = np.mean(errs_opt2_p2, axis=0)
std_raw = np.std(errs_raw_p2, axis=0)
std_opt2 = np.std(errs_opt2_p2, axis=0)

x = np.arange(6)
w = 0.35
ax4.bar(x - w/2, mean_raw, width=w, yerr=std_raw, capsize=4, color="#d9534f", label="Rev 2.0 Raw (Phase 2)", alpha=0.85)
ax4.bar(x + w/2, mean_opt2, width=w, yerr=std_opt2, capsize=4, color="#0275d8", label="Rev 2.0 Option 2 (Phase 2)", alpha=0.85)
ax4.axhline(0, color="black", lw=1)
ax4.set_title("D. Phase 2 Static Column Error Elimination (DC Lift)", fontsize=13, fontweight="bold")
ax4.set_xlabel("Column Index", fontsize=11)
ax4.set_ylabel("Mean Residual Error (LSB)", fontsize=11)
ax4.set_xticks(x)
ax4.set_xticklabels([f"Col {i+1}" for i in range(6)])
ax4.grid(True, linestyle=":", alpha=0.6)
ax4.legend(loc="lower right", fontsize=8.5)

fig_path = REPO_ROOT / "FPGA_code/docs/figures/fig_mode_a_500ep_rev2_opt2_dc_lift_5ms.png"
fig_path.parent.mkdir(parents=True, exist_ok=True)
plt.savefig(fig_path, bbox_inches="tight")
plt.close()
print(f"[+] Saved 4-panel comparison plot to: {fig_path}")

