#!/usr/bin/env python3
import json
import shutil
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

FIG_DIR = Path("FPGA_code/docs/figures")
FIG_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR = Path("FPGA_code/logs/mode_a_longterm_sweep")
ARTIFACT_DIR = Path("/home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a")

with open(LOG_DIR / "test_1k15k_k8_lr08p_20ep.json") as f:
    d20 = json.load(f)

with open(LOG_DIR / "test_1k15k_k8_lr32p_40ep.json") as f:
    d40_high = json.load(f)

with open(LOG_DIR / "test_1k15k_k16_lr08p_40ep.json") as f:
    d40_k16 = json.load(f)

with open(LOG_DIR / "test_1k15k_k4_lr100p_40ep.json") as f:
    d40_k4_lr100 = json.load(f)

plt.rcParams.update({
    'font.sans-serif': 'DejaVu Sans',
    'font.family': 'sans-serif',
    'figure.dpi': 300,
    'axes.labelsize': 9,
    'axes.titlesize': 10,
    'xtick.labelsize': 8,
    'ytick.labelsize': 8,
    'legend.fontsize': 7.5,
    'figure.titlesize': 11
})

fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.5))

# Panel 1: Validation Loss Trajectories
ep20 = [r["epoch"] for r in d20["records"][1:]]
loss20 = [r["loss_lsb2"] for r in d20["records"][1:]]

ep40_high = [r["epoch"] for r in d40_high["records"][1:]]
loss40_high = [r["loss_lsb2"] for r in d40_high["records"][1:]]

ep40_k16 = [r["epoch"] for r in d40_k16["records"][1:]]
loss40_k16 = [r["loss_lsb2"] for r in d40_k16["records"][1:]]

ep40_k4 = [r["epoch"] for r in d40_k4_lr100["records"][1:]]
loss40_k4 = [r["loss_lsb2"] for r in d40_k4_lr100["records"][1:]]

axes[0].plot(ep20, loss20, color='#0284C7', marker='o', lw=1.6, label="K=8, LR=0.08x (20 Ep, Steady)")
axes[0].plot(ep40_high, loss40_high, color='#EF4444', marker='^', lw=1.2, alpha=0.5, label="K=8, LR=0.32x (40 Ep, High Noise)")
axes[0].plot(ep40_k16, loss40_k16, color='#10B981', marker='s', lw=1.8, label="K=16, LR=0.08x (40 Ep, Smooth)")
axes[0].plot(ep40_k4, loss40_k4, color='#8B5CF6', marker='D', lw=1.8, label="K=4, LR=1.00x (40 Ep, Dynamic Backprop)")

axes[0].set_title("(a) Validation Loss Trajectories on 1k/15k Attenuator", fontweight='bold')
axes[0].set_xlabel("Epoch")
axes[0].set_ylabel("Validation Loss (LSB²)")
axes[0].grid(True, linestyle='--', alpha=0.5)
axes[0].legend(loc='upper right', framealpha=0.9)

# Panel 2: Effective Resolution (ENOB)
enob20 = [r["enob_bits"] for r in d20["records"][1:]]
enob40_high = [r["enob_bits"] for r in d40_high["records"][1:]]
enob40_k16 = [r["enob_bits"] for r in d40_k16["records"][1:]]
enob40_k4 = [r["enob_bits"] for r in d40_k4_lr100["records"][1:]]

axes[1].plot(ep20, enob20, color='#0284C7', marker='o', lw=1.6, label=f"K=8, LR=0.08x (Peak {max(enob20):.2f} b)")
axes[1].plot(ep40_high, enob40_high, color='#EF4444', marker='^', lw=1.2, alpha=0.5, label=f"K=8, LR=0.32x (Peak {max(enob40_high):.2f} b)")
axes[1].plot(ep40_k16, enob40_k16, color='#10B981', marker='s', lw=1.8, label=f"K=16, LR=0.08x (Peak {max(enob40_k16):.2f} b)")
axes[1].plot(ep40_k4, enob40_k4, color='#8B5CF6', marker='D', lw=1.8, label=f"K=4, LR=1.00x (All-Time Peak {max(enob40_k4):.2f} b!)")

axes[1].axhline(6.28, color='#7C3AED', linestyle='-.', lw=1.3, label="New Silicon Record: 6.28 bits (Ep 27)")
axes[1].axhline(6.00, color='#DC2626', linestyle='--', lw=1.0, alpha=0.7, label="6.0-Bit Barrier")
axes[1].set_title("(b) Effective Resolution (ENOB Bits) Progression", fontweight='bold')
axes[1].set_xlabel("Epoch")
axes[1].set_ylabel("ENOB (Bits)")
axes[1].set_ylim(3.8, 6.5)
axes[1].grid(True, linestyle='--', alpha=0.5)
axes[1].legend(loc='lower right', framealpha=0.9)

plt.tight_layout()
fig_out = FIG_DIR / "fig_1k15k_hardware_verification.png"
plt.savefig(fig_out, dpi=300)
plt.close()
print(f"[+] Saved figure to {fig_out}")

# Copy to artifact directory
shutil.copy2(fig_out, ARTIFACT_DIR / "fig_1k15k_hardware_verification.png")
print(f"[+] Copied to {ARTIFACT_DIR / 'fig_1k15k_hardware_verification.png'}")
