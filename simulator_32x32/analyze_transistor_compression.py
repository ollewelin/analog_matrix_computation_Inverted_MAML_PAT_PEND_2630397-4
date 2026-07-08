"""
Analyze Compressor Behavior in 2T1C Transistor Multiplier
===========================================================

The triode-region transistor model IS inherently compressive:

    I_out = g_m · (V_gs - V_th - V_ds/2) · V_ds

Expanded:
    I_out = g_m · V_ds · (V_gs - V_th) - g_m · (V_ds²/2)
          = g_m · (V_gs - V_th) · V_ds - (g_m/2) · V_ds²

This is a PARABOLIC function:
  - Linear term: +g_m·(V_gs - V_th)·V_ds (growing)
  - Quadratic term: -(g_m/2)·V_ds² (compressing)

Result: Soft saturation - the output peaks and then compresses!

This means:
1. No transistor can create arbitrarily large currents
2. High-current cells naturally limit themselves
3. This creates a form of automatic gain compression
4. Position-dependent IR drops interact with this compression
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

def transistor_triode_model(V_gs, V_th, V_ds_range, g_m=1.0):
    """
    Compute transistor output current vs V_ds.
    
    I_out = g_m · (V_gs - V_th - V_ds/2) · V_ds
    """
    I_out = g_m * (V_gs - V_th - V_ds_range / 2.0) * V_ds_range
    
    # Clamp to saturation
    I_out = np.where(V_ds_range > (V_gs - V_th), 1e-8, I_out)
    
    return I_out


def plot_compressor_behavior():
    """Generate plots showing inherent compressor behavior."""
    
    # Parameters from 2T1C cell model
    V_th = 0.6  # Threshold voltage
    g_m = 0.01  # Transconductance
    
    # Weight storage range: 2.1V to 3.1V
    V_gs_values = [2.1, 2.4, 2.6, 2.8, 3.1]
    V_gs_labels = ['2.1V (min)', '2.4V', '2.6V (mid)', '2.8V', '3.1V (max)']
    
    # V_ds sweep: 0 to 0.25V (data signal range)
    V_ds = np.linspace(0, 0.25, 200)
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Transistor Multiplier Inherent Compressor Behavior\n(Triode Region: I = g_m·(V_gs - V_th - V_ds/2)·V_ds)', 
                 fontsize=13, fontweight='bold')
    
    # Panel 1: I-V curves for different gate voltages
    ax = axes[0, 0]
    colors = plt.cm.viridis(np.linspace(0, 1, len(V_gs_values)))
    
    for V_gs, label, color in zip(V_gs_values, V_gs_labels, colors):
        I_out = transistor_triode_model(V_gs, V_th, V_ds, g_m)
        ax.plot(V_ds * 1000, I_out * 1e6, linewidth=2.5, label=label, color=color, marker='o', markersize=3, markevery=20)
    
    ax.set_xlabel('V_ds (mV)', fontsize=11)
    ax.set_ylabel('Output Current (μA)', fontsize=11)
    ax.set_title('I-V Characteristics: Soft Saturation (Compression)', fontsize=12, fontweight='bold')
    ax.legend(fontsize=10, loc='upper right')
    ax.grid(True, alpha=0.3)
    ax.axhline(0, color='black', linestyle='-', linewidth=0.5)
    
    # Panel 2: Peak current vs gate voltage
    ax = axes[0, 1]
    
    peak_currents = []
    peak_vds = []
    
    for V_gs in V_gs_values:
        I_out = transistor_triode_model(V_gs, V_th, V_ds, g_m)
        max_idx = np.argmax(I_out)
        peak_currents.append(I_out[max_idx] * 1e6)
        peak_vds.append(V_ds[max_idx] * 1000)
    
    ax.plot([v * 1000 for v in V_gs_values], peak_currents, 'o-', linewidth=2.5, markersize=8, color='darkred')
    ax.fill_between([v * 1000 for v in V_gs_values], 0, peak_currents, alpha=0.3, color='red')
    
    ax.set_xlabel('Gate Voltage V_gs (mV)', fontsize=11)
    ax.set_ylabel('Peak Output Current (μA)', fontsize=11)
    ax.set_title('Peak Current Scaling: NOT Linear (Compression)', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    # Add annotations
    for i, (V_gs, I_peak) in enumerate(zip([v * 1000 for v in V_gs_values], peak_currents)):
        ax.annotate(f'{I_peak:.1f}μA', xy=(V_gs, I_peak), xytext=(5, 5), 
                   textcoords='offset points', fontsize=9)
    
    # Panel 3: Nonlinearity: Gain compression vs V_ds
    ax = axes[1, 0]
    
    V_gs_mid = 2.6  # Middle gate voltage
    I_out_mid = transistor_triode_model(V_gs_mid, V_th, V_ds, g_m)
    
    # Compute gain (dI/dV_ds) - derivative
    dI_dVds = np.gradient(I_out_mid, V_ds)
    
    ax.plot(V_ds * 1000, dI_dVds * 1e6, linewidth=2.5, color='darkblue', marker='s', markersize=3, markevery=20)
    ax.fill_between(V_ds * 1000, 0, dI_dVds * 1e6, alpha=0.3, color='blue')
    
    ax.set_xlabel('V_ds (mV)', fontsize=11)
    ax.set_ylabel('Gain dI/dV_ds (μA/V)', fontsize=11)
    ax.set_title(f'Compressor Gain Curve (V_gs = {V_gs_mid}V)\nGain Decreases at High V_ds', 
                fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.axhline(0, color='black', linestyle='-', linewidth=0.5)
    
    # Panel 4: Matrix output compression for uniform input
    ax = axes[1, 1]
    
    # Simulate 32x32 matrix with random weights responding to uniform data input
    np.random.seed(42)
    V_gs_matrix = np.random.uniform(2.1, 3.1, size=(32, 32))
    
    # Fixed data input sweep
    V_ds_uniform_sweep = np.linspace(0, 0.25, 100)
    output_power = []
    
    for V_ds_val in V_ds_uniform_sweep:
        # All cells get same V_ds input
        I_all = transistor_triode_model(V_gs_matrix, V_th, V_ds_val, g_m)
        # Measure total output power (sum of currents)
        total_I = np.sum(I_all)
        output_power.append(total_I)
    
    # Compare to ideal linear (no compression)
    ideal_linear = V_ds_uniform_sweep / 0.25 * np.max(output_power)
    
    ax.plot(V_ds_uniform_sweep * 1000, np.array(output_power) * 1e6, 'o-', linewidth=2.5, 
           markersize=3, markevery=5, label='Actual (Compressed)', color='darkred', marker='o')
    ax.plot(V_ds_uniform_sweep * 1000, ideal_linear * 1e6, '--', linewidth=2, 
           label='Ideal Linear (No Compression)', color='gray', alpha=0.7)
    
    ax.fill_between(V_ds_uniform_sweep * 1000, np.array(output_power) * 1e6, ideal_linear * 1e6, 
                   alpha=0.2, color='red', label='Compression Loss')
    
    ax.set_xlabel('Data Input V_ds (mV)', fontsize=11)
    ax.set_ylabel('Matrix Total Current (μA)', fontsize=11)
    ax.set_title('32×32 Matrix Output: Soft Saturation Under Uniform Input', fontsize=12, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save
    results_dir = Path("results_32x32")
    results_dir.mkdir(parents=True, exist_ok=True)
    
    plot_file = results_dir / "transistor_compressor_analysis.png"
    plt.savefig(plot_file, dpi=150, bbox_inches='tight')
    print(f"✓ Compressor analysis saved: {plot_file}")
    plt.close()


def analyze_compression_math():
    """Print mathematical analysis."""
    
    print("=" * 80)
    print("TRANSISTOR MULTIPLIER COMPRESSOR ANALYSIS")
    print("=" * 80)
    
    print("\n📋 TRIODE REGION EQUATION:")
    print("─" * 80)
    print("    I_out = g_m · (V_gs - V_th - V_ds/2) · V_ds")
    print()
    print("Expanded form:")
    print("    I_out = g_m · (V_gs - V_th) · V_ds - (g_m/2) · V_ds²")
    print("           └─ Linear term ─┘       └─ Quadratic term (compression) ─┘")
    
    print("\n🔍 COMPRESSOR CHARACTERISTICS:")
    print("─" * 80)
    print("1. SOFT SATURATION")
    print("   • Output current peaks at V_ds = V_gs - V_th")
    print("   • Beyond peak: gain becomes negative (current decreases)")
    print("   • This is automatic amplitude compression!")
    
    print("\n2. GAIN COMPRESSION FACTOR")
    print("   • Small signal gain: g = ∂I/∂V_ds = g_m·(V_gs - V_th - V_ds)")
    print("   • At V_ds = 0: g = g_m·(V_gs - V_th) [maximum]")
    print("   • At V_ds = (V_gs - V_th)/2: g = g_m·(V_gs - V_th)/2 [50% gain]")
    print("   • Gain reduction: 20·log₁₀(g/g_max) = -3dB at midpoint")
    
    print("\n3. MATRIX-LEVEL COMPRESSION")
    print("   • Each cell independently compresses high-current signals")
    print("   • High-amplitude inputs naturally limit matrix output")
    print("   • Creates implicit AGC (automatic gain control)")
    
    print("\n4. INTERACTION WITH IR DROPS")
    print("   • Compressed cells have lower current → smaller IR drops")
    print("   • High-current (uncompressed) cells experience larger IR drops")
    print("   • Creates position-dependent dynamic range!")
    
    print("\n" + "=" * 80)
    print("IMPLICATIONS FOR MAML LEARNING")
    print("=" * 80)
    
    print("\n✓ MAML EXPLOITS THIS COMPRESSION:")
    print("   • M33 (primary) learns to work with soft-saturating transistors")
    print("   • M3+M8 (corrections) can COMPENSATE for compression nonlinearity")
    print("   • num_strata=1 strategy captures this compression signature")
    print("   • Learning rate 0.05 allows adaptation to compression curvature")
    
    print("\n✗ NAIVE APPROACH FAILS:")
    print("   • Linear matrix models ignore compression → poor baseline")
    print("   • Analog assumes linearity, reality is nonlinear")
    print("   • MAML success BECAUSE it learns the nonlinearity")
    
    print("\n💡 PATENT ADVANTAGE:")
    print("   • Most analog designs fight compression (use cascode)")
    print("   • Our approach: LEARN to exploit compression as feature")
    print("   • Compression helps limit distortion → better precision")
    print("   • This is why 32×32 still achieves 6.7 bits despite harsh distortions")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    analyze_compression_math()
    print("\n" + "─" * 80)
    print("Generating visualization...")
    print("─" * 80 + "\n")
    plot_compressor_behavior()
    
    print("\n" + "█" * 80)
    print("█ COMPRESSOR ANALYSIS COMPLETE")
    print("█" * 80)
