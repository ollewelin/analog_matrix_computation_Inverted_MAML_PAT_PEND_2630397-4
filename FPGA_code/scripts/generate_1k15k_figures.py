#!/usr/bin/env python3
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

FIG_DIR = Path("FPGA_code/docs/figures")
FIG_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR = Path("FPGA_code/logs/mode_a_longterm_sweep")

with open(LOG_DIR / "test_1k15k_k8_lr08p_20ep.json") as f:
    d20 = json.load(f)

with open(LOG_DIR / "test_1k15k_k8_lr32p_40ep.json") as f:
    d40 = json.load(f)

plt.rcParams.update({
    'font.sans-serif': 'DejaVu Sans',
    'font.family': 'sans-serif',
    'figure.dpi': 300,
    'axes.labelsize': 9,
    'axes.titlesize': 10,
    'xtick.labelsize': 8,
    'ytick.labelsize': 8,
    'legend.fontsize': 8,
    'figure.titlesize': 11
})

fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.2))

# Panel 1: Validation Loss Trajectories
ep20 = [r["epoch"] for r in d20["records"][1:]]
loss20 = [r["loss_lsb2"] for r in d20["records"][1:]]
ep40 = [r["epoch"] for r in d40["records"][1:]]
loss40 = [r["loss_lsb2"] for r in d40["records"][1:]]

axes[0].plot(ep20, loss20, color='#0284C7', marker='o', lw=1.8, label="20-Ep Test (LR=0.08x, -57.0% Net)")
axes[0].plot(ep40, loss40, color='#10B981', marker='s', lw=1.5, alpha=0.8, label="40-Ep Test (LR=0.32x, 4x Higher LR)")
axes[0].axhline(np.mean(loss20[-5:]), color='#0284C7', linestyle='--', alpha=0.7, label=f"LR=0.08x End Mean ({np.mean(loss20[-5:]):.0f} LSB²)")
axes[0].set_title("(a) Validation Loss Trajectories on 1k/15k Resistor", fontweight='bold')
axes[0].set_xlabel("Epoch")
axes[0].set_ylabel("Validation Loss (LSB²)")
axes[0].grid(True, linestyle='--', alpha=0.5)
axes[0].legend(loc='upper right', framealpha=0.9, fontsize=7.5)

# Panel 2: Effective Resolution (ENOB)
enob20 = [r["enob_bits"] for r in d20["records"][1:]]
enob40 = [r["enob_bits"] for r in d40["records"][1:]]

axes[1].plot(ep20, enob20, color='#0284C7', marker='o', lw=1.8, label=f"LR=0.08x (Peak {max(enob20):.2f} b)")
axes[1].plot(ep40, enob40, color='#10B981', marker='s', lw=1.5, alpha=0.8, label=f"LR=0.32x (Peak {max(enob40):.2f} b!)")
axes[1].axhline(5.89, color='#DC2626', linestyle=':', lw=1.5, label="All-Time Record (5.89 bits @ Ep 24)")
axes[1].set_title("(b) Effective Resolution (ENOB Bits) Progression", fontweight='bold')
axes[1].set_xlabel("Epoch")
axes[1].set_ylabel("ENOB (Bits)")
axes[1].set_ylim(3.8, 6.2)
axes[1].grid(True, linestyle='--', alpha=0.5)
axes[1].legend(loc='lower right', framealpha=0.9, fontsize=7.5)

plt.tight_layout()
fig_out = FIG_DIR / "fig_1k15k_hardware_verification.png"
plt.savefig(fig_out, dpi=300)
plt.close()
print(f"[+] Saved figure to {fig_out}")
