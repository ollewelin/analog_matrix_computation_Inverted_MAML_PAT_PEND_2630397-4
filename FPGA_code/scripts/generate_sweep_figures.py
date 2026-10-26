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

with open(LOG_DIR / "sweep_summary_registry.json") as f:
    registry = json.load(f)

tb_runs = [d for d in registry if d.get("tag", "").startswith("true_batch_")]

# Set publication style
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

# ---------------------------------------------------------
# Figure 1: Batch Scaling Law & Convergence Landscape
# ---------------------------------------------------------
fig, axes = plt.subplots(1, 3, figsize=(11.5, 3.6))

# Panel A: Convergence Rate (%) vs K
by_k = {}
for r in tb_runs:
    k = r["k"]
    if k not in by_k:
        by_k[k] = []
    by_k[k].append(r)

k_vals = sorted(by_k.keys())
conv_rates = []
avg_trends = []
avg_slopes = []

for k in k_vals:
    runs = by_k[k]
    conv_cnt = sum(1 for x in runs if "CONVERGING" in x["stats"]["verdict"])
    conv_rates.append(conv_cnt / len(runs) * 100)
    avg_trends.append(np.mean([x["stats"]["trend_pct"] for x in runs]))
    avg_slopes.append(np.mean([x["stats"]["slope_loss_per_epoch"] for x in runs]))

bars = axes[0].bar([str(k*10) for k in k_vals], conv_rates, color=['#64748B', '#0EA5E9', '#0284C7', '#0369A1', '#10B981', '#F59E0B'], edgecolor='#0F172A', width=0.6)
axes[0].set_title("(a) Convergence Rate vs Batch Scale", fontweight='bold')
axes[0].set_xlabel("Batch Scale (Samples per Step = 10 x K)")
axes[0].set_ylabel("Convergence Rate (%)")
axes[0].set_ylim(0, 115)
axes[0].grid(axis='y', linestyle='--', alpha=0.5)
for bar in bars:
    yval = bar.get_height()
    axes[0].text(bar.get_x() + bar.get_width()/2.0, yval + 2, f"{int(round(yval))}%", ha='center', va='bottom', fontsize=8, fontweight='bold')

# Panel B: Net Loss Reduction (%) vs K
colors_lr = {0.03: '#10B981', 0.05: '#0284C7', 0.08: '#F59E0B', 0.10: '#6366F1', 0.15: '#EC4899', 0.20: '#EF4444'}
for r in tb_runs:
    k = r["k"]
    trend = r["stats"]["trend_pct"]
    lr = r["lr"]
    c = colors_lr.get(lr, '#94A3B8')
    axes[1].scatter(k*10, trend, color=c, s=40, edgecolors='#0F172A', zorder=4, alpha=0.9)

# Plot average trend curve
axes[1].plot([k*10 for k in k_vals], avg_trends, color='#0F172A', linestyle='--', linewidth=1.5, marker='s', markersize=4, label='Batch Mean Trend', zorder=3)
axes[1].axhline(0, color='gray', linestyle=':', alpha=0.7)
axes[1].set_title("(b) Net Loss Reduction vs Batch Scale", fontweight='bold')
axes[1].set_xlabel("Batch Scale (Samples per Step)")
axes[1].set_ylabel("Net Q1 -> Q4 Loss Trend (%)")
axes[1].grid(True, linestyle='--', alpha=0.5)

# Annotate K=20 Sweetspot
axes[1].annotate('K=20 Sweetspot\n(-16.4% Record)', xy=(200, -16.4), xytext=(150, -22),
            arrowprops=dict(facecolor='#10B981', edgecolor='#065F46', arrowstyle='->', lw=1.5),
            fontsize=8, fontweight='bold', color='#065F46',
            bbox=dict(boxstyle="round,pad=0.3", fc="#ECFDF5", ec="#10B981", lw=1))

# Panel C: Slope Beta_1 vs Batch Scale
for r in tb_runs:
    k = r["k"]
    slope = r["stats"]["slope_loss_per_epoch"]
    lr = r["lr"]
    c = colors_lr.get(lr, '#94A3B8')
    axes[2].scatter(k*10, slope, color=c, s=40, edgecolors='#0F172A', zorder=4, label=f'LR {lr:.2f}x' if k==20 else "")

axes[2].plot([k*10 for k in k_vals], avg_slopes, color='#DC2626', linestyle='-', linewidth=1.5, marker='o', markersize=4, label='Mean Slope')
axes[2].axhline(0, color='gray', linestyle=':', alpha=0.7)
axes[2].set_title("(c) Regression Slope (Beta_1) vs Scale", fontweight='bold')
axes[2].set_xlabel("Batch Scale (Samples per Step)")
axes[2].set_ylabel("Loss Slope (LSB^2 / epoch)")
axes[2].grid(True, linestyle='--', alpha=0.5)
axes[2].legend(loc='lower left', framealpha=0.9, fontsize=7)

plt.tight_layout()
fig_path1 = FIG_DIR / "fig_mode_a_batch_scaling_law.png"
plt.savefig(fig_path1, dpi=300)
plt.close()
print(f"[+] Saved Figure 1 to {fig_path1}")

# ---------------------------------------------------------
# Figure 2: Multi-Condition Validation Loss Trajectories
# ---------------------------------------------------------
fig, axes = plt.subplots(2, 2, figsize=(11.5, 6.2))

configs = [
    ("true_batch_k20_lr03p_200ep.json", axes[0, 0], "K=20, LR=0.03x (All-Time High Record)", "#10B981"),
    ("true_batch_k25_lr05p_200ep.json", axes[0, 1], "K=25, LR=0.05x (High Batch Clean Descent)", "#0284C7"),
    ("true_batch_k4_lr05p_200ep.json",  axes[1, 0], "K=4, LR=0.05x (Low Batch Noisy Descent)", "#F59E0B"),
    ("true_batch_k8_lr05p_200ep.json",  axes[1, 1], "K=8, LR=0.05x (Statistically Flat Floor)", "#64748B"),
]

for fname, ax, title, color_theme in configs:
    p = LOG_DIR / fname
    with open(p) as f:
        d = json.load(f)
    epochs = [x["epoch"] for x in d["epochs"][1:]]
    losses = [x["loss_lsb2"] for x in d["epochs"][1:]]
    
    # 15-epoch rolling average
    w = 15
    rolling = np.convolve(losses, np.ones(w)/w, mode='valid')
    rolling_epochs = epochs[w-1:]
    
    # Linear fit
    coeffs = np.polyfit(epochs, losses, 1)
    poly = np.poly1d(coeffs)
    r2 = 1 - (np.sum((losses - poly(epochs))**2) / np.sum((losses - np.mean(losses))**2))
    
    # Plot raw scatter / faint line
    ax.plot(epochs, losses, color=color_theme, alpha=0.25, lw=0.8, label="Raw Val Loss")
    ax.plot(rolling_epochs, rolling, color=color_theme, lw=2.0, label="15-Ep Moving Avg")
    ax.plot(epochs, poly(epochs), color='#0F172A', linestyle='--', lw=1.5, label=f"Trend (β1={coeffs[0]:.2f}, R²={r2:.3f})")
    
    ax.set_title(title, fontweight='bold', fontsize=9.5)
    ax.set_xlabel("Epoch (1 - 200)")
    ax.set_ylabel("Validation Loss (LSB²)")
    ax.grid(True, linestyle='--', alpha=0.5)
    ax.legend(loc='upper right', framealpha=0.9, fontsize=7.5)

plt.tight_layout()
fig_path2 = FIG_DIR / "fig_mode_a_convergence_trajectories_comparison.png"
plt.savefig(fig_path2, dpi=300)
plt.close()
print(f"[+] Saved Figure 2 to {fig_path2}")

# ---------------------------------------------------------
# Figure 3: Weight Dynamics & Matrix Topography
# ---------------------------------------------------------
fig, axes = plt.subplots(1, 3, figsize=(11.5, 3.6))

# Load K=20 LR=0.03x trajectory
p_rec = LOG_DIR / "true_batch_k20_lr03p_200ep.json"
with open(p_rec) as f:
    d_rec = json.load(f)

epochs = [x["epoch"] for x in d_rec["epochs"]]
w8_diags = np.array([[x["w_m8"][i][i] for i in range(6)] for x in d_rec["epochs"]])
r_m3 = [x["r_m3"] for x in d_rec["epochs"]]
enobs = [x["enob_bits"] for x in d_rec["epochs"]]

# Panel A: M8 Diagonal Weight Adjustments
for i in range(6):
    axes[0].plot(epochs, w8_diags[:, i], lw=1.6, label=f"Ch {i}")
axes[0].set_title("(a) M8 Weight Evolution (K=20 LR=0.03x)", fontweight='bold')
axes[0].set_xlabel("Epoch (0 - 200)")
axes[0].set_ylabel("M8 DAC Code (0 - 63)")
axes[0].grid(True, linestyle='--', alpha=0.5)
axes[0].legend(ncol=3, loc='upper left', fontsize=7)

# Panel B: Matrix 33 Topological Correlation Preservation
axes[1].plot(epochs, r_m3, color='#4F46E5', lw=1.8, label="Matrix 33 Pearson r")
axes[1].set_title("(b) Matrix 33 Geometric Correlation", fontweight='bold')
axes[1].set_xlabel("Epoch (0 - 200)")
axes[1].set_ylabel("Correlation (r_M3)")
axes[1].set_ylim(0.9990, 1.0001)
axes[1].grid(True, linestyle='--', alpha=0.5)
axes[1].legend(loc='lower left', fontsize=8)

# Panel C: ENOB Progression
rolling_enob = np.convolve(enobs[1:], np.ones(15)/15, mode='valid')
axes[2].plot(epochs[1:], enobs[1:], color='#059669', alpha=0.3, lw=0.8, label="Val ENOB")
axes[2].plot(epochs[15:], rolling_enob, color='#059669', lw=2.0, label="15-Ep Moving Avg")
axes[2].axhline(np.mean(enobs[1:51]), color='#DC2626', linestyle=':', label=f"Q1 Mean ({np.mean(enobs[1:51]):.2f} b)")
axes[2].axhline(np.mean(enobs[151:]), color='#2563EB', linestyle=':', label=f"Q4 Mean ({np.mean(enobs[151:]):.2f} b)")
axes[2].set_title("(c) Resolution (ENOB) Trajectory", fontweight='bold')
axes[2].set_xlabel("Epoch (1 - 200)")
axes[2].set_ylabel("ENOB (Bits)")
axes[2].grid(True, linestyle='--', alpha=0.5)
axes[2].legend(loc='lower right', fontsize=7.5)

plt.tight_layout()
fig_path3 = FIG_DIR / "fig_mode_a_weight_dynamics_and_topography.png"
plt.savefig(fig_path3, dpi=300)
plt.close()
print(f"[+] Saved Figure 3 to {fig_path3}")
