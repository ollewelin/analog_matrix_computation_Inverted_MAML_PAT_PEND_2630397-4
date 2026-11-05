import json
import matplotlib.pyplot as plt
import numpy as np

# Load the two empirical benchmark runs on Card 2
with open("FPGA_code/logs/mode_a_extended_training/card2_mode_a_1000ep_5ms_pure_toeplitz_reg2048_lr0p02_swing40_var5_k1_1k_3p3k_ablation.json", "r") as f:
    old_fw = json.load(f)

with open("FPGA_code/logs/mode_a_extended_training/card2_mode_a_new_fw_1000ep_5ms_pure_toeplitz_reg2048_lr0p02_swing40_var5_k1_1k_3p3k_ablation.json", "r") as f:
    new_fw = json.load(f)

epochs = [ep["epoch"] for ep in old_fw["epochs"]]
old_loss = [ep["loss_lsb2"] for ep in old_fw["epochs"]]
old_enob = [ep["enob_bits"] for ep in old_fw["epochs"]]
new_loss = [ep["loss_lsb2"] for ep in new_fw["epochs"]]
new_enob = [ep["enob_bits"] for ep in new_fw["epochs"]]

# Calculate rolling averages
window = 20
old_loss_ma = np.convolve(old_loss, np.ones(window)/window, mode='same')
new_loss_ma = np.convolve(new_loss, np.ones(window)/window, mode='same')
old_enob_ma = np.convolve(old_enob, np.ones(window)/window, mode='same')
new_enob_ma = np.convolve(new_enob, np.ones(window)/window, mode='same')

fig, axs = plt.subplots(3, 1, figsize=(14, 11), sharex=False)
fig.suptitle("Inverted MAML Post-Mortem Analysis: Firmware Timing Jitter vs. True Silicon Precision\nCard 2 (1k/3.3k Attenuator) - Side-by-Side Comparison on Identical Silicon", fontsize=14, fontweight='bold', y=0.98)

# Panel 1: Quadratic Loss
ax1 = axs[0]
ax1.plot(epochs, old_loss, color='#e74c3c', alpha=0.25, label='Old FW (Jittery 10/20 ms) Raw')
ax1.plot(epochs, old_loss_ma, color='#c0392b', linewidth=2.0, label='Old FW Moving Avg (MA-20)')
ax1.plot(epochs, new_loss, color='#27ae60', alpha=0.25, label='New FW (Crystal-Locked 10.0 ms) Raw')
ax1.plot(epochs, new_loss_ma, color='#1e8449', linewidth=2.0, label='New FW Moving Avg (MA-20)')
ax1.set_yscale('log')
ax1.set_ylabel("Quadratic Loss (LSB²)", fontweight='bold')
ax1.set_title("Panel A: Loss Dynamics - The Artifactual Phase Contrast vs. True Flat Baseline", fontweight='bold', fontsize=11)
ax1.grid(True, which='both', linestyle='--', alpha=0.5)
ax1.axvspan(1, 100, color='gray', alpha=0.1, label='Phase 1: Baseline')
ax1.axvspan(100, 200, color='green', alpha=0.08, label='Phase 2: MAML Nom')
ax1.axvspan(200, 600, color='orange', alpha=0.08, label='Phase 3: Disturbance')
ax1.axvspan(600, 1000, color='red', alpha=0.08, label='Phase 4: Ablation (W=0)')
ax1.legend(loc='upper right', ncol=2, fontsize=9)
ax1.set_xlim(1, 1000)

# Panel 2: Effective Bits (ENOB)
ax2 = axs[1]
ax2.plot(epochs, old_enob, color='#e74c3c', alpha=0.25)
ax2.plot(epochs, old_enob_ma, color='#c0392b', linewidth=2.0, label='Old FW: Artificial 4.2 b → 5.6 b → 4.0 b Contrast')
ax2.plot(epochs, new_enob, color='#27ae60', alpha=0.25)
ax2.plot(epochs, new_enob_ma, color='#1e8449', linewidth=2.0, label='New FW: Constant ~5.6 b Real Silicon Baseline (Δ = 0.04 b)')
ax2.set_ylabel("ENOB (Bits)", fontweight='bold')
ax2.set_title("Panel B: Effective Precision - Unmasking the 5.6-bit Physical Matrix 33 Baseline", fontweight='bold', fontsize=11)
ax2.grid(True, linestyle='--', alpha=0.5)
ax2.axvspan(1, 100, color='gray', alpha=0.1)
ax2.axvspan(100, 200, color='green', alpha=0.08)
ax2.axvspan(200, 600, color='orange', alpha=0.08)
ax2.axvspan(600, 1000, color='red', alpha=0.08)
ax2.legend(loc='lower right', fontsize=10)
ax2.set_xlim(1, 1000)

# Panel 3: Phase Bar Comparison
ax3 = axs[2]
phases = ['Phase 1\n(Baseline W=0)', 'Phase 2\n(MAML Clean)', 'Phase 3\n(±5 LSB Dist)', 'Phase 4\n(Ablation W=0)']
x = np.arange(len(phases))
width = 0.35

old_losses = [
    np.mean(old_loss[0:100]),
    np.mean(old_loss[100:200]),
    np.mean(old_loss[200:600]),
    np.mean(old_loss[600:1000])
]
new_losses = [
    np.mean(new_loss[0:100]),
    np.mean(new_loss[100:200]),
    np.mean(new_loss[200:600]),
    np.mean(new_loss[600:1000])
]

old_enobs = [
    np.mean(old_enob[0:100]),
    np.mean(old_enob[100:200]),
    np.mean(old_enob[200:600]),
    np.mean(old_enob[600:1000])
]
new_enobs = [
    np.mean(new_enob[0:100]),
    np.mean(new_enob[100:200]),
    np.mean(new_enob[200:600]),
    np.mean(new_enob[600:1000])
]

rects1 = ax3.bar(x - width/2, old_losses, width, label='Old FW (10/20 ms Jitter)', color='#e74c3c', alpha=0.85)
rects2 = ax3.bar(x + width/2, new_losses, width, label='New FW (Crystal-Locked 10.0 ms)', color='#27ae60', alpha=0.85)

ax3.set_ylabel("Mean Quadratic Loss (LSB²)", fontweight='bold')
ax3.set_title("Panel C: Quantitative Phase Breakdown & Collapse of Pseudo-Contrast", fontweight='bold', fontsize=11)
ax3.set_xticks(x)
ax3.set_xticklabels(phases, fontweight='bold')
ax3.grid(True, axis='y', linestyle='--', alpha=0.5)
ax3.legend(loc='upper right', fontsize=10)

# Add text labels on bars
for i in range(len(phases)):
    ax3.text(x[i] - width/2, old_losses[i] + 1500, f"{old_losses[i]:.0f} L²\n({old_enobs[i]:.2f} b)", ha='center', va='bottom', fontsize=8, color='#c0392b', fontweight='bold')
    ax3.text(x[i] + width/2, new_losses[i] + 1500, f"{new_losses[i]:.0f} L²\n({new_enobs[i]:.2f} b)", ha='center', va='bottom', fontsize=8, color='#1e8449', fontweight='bold')

ax3.set_ylim(0, max(old_losses) * 1.25)

plt.tight_layout(rect=[0, 0.03, 1, 0.95])
plt.savefig("FPGA_code/docs/figures/fig_timing_jitter_post_mortem_side_by_side.png", dpi=300)
print("Saved fig_timing_jitter_post_mortem_side_by_side.png successfully!")
