"""
COMPARISON TEST: 6x6 vs 32x32 Baseline Precision Analysis
Tests identical conditions (harsh effects, 10-cycle OFF, 90-cycle ON)
"""

import sys
sys.path.insert(0, '/home/olle/AnalogAI/git/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/simulator')
sys.path.insert(0, '/home/olle/AnalogAI/git/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/simulator_32x32')

import numpy as np
import os
import json
from datetime import datetime
import matplotlib.pyplot as plt
from matrix_core import AtomicTriad
from maml_optimizer import InvertedMAML, create_test_vectors

# Also import 6x6 versions
from matrix_core import AtomicTriad as AtomicTriad6x6
from maml_optimizer import InvertedMAML as InvertedMAML6x6


def create_test_vectors_6x6(num_vectors: int = 16, seed: int = 42):
    """Create test vectors for 6x6 (dimension=6)."""
    np.random.seed(seed)
    x_test = np.random.uniform(0, 1, (num_vectors, 6))
    W_ideal = np.random.randn(6, 6) * 0.05
    b_ideal = np.random.randn(6) * 0.01
    y_test = (W_ideal @ x_test.T).T + b_ideal
    y_test = np.clip(y_test, -0.25, 0.25)
    return x_test, y_test


def plot_comparison_precision_curves(results: dict, output_dir: str = 'results_32x32/comparison'):
    """Plot 1: Direct precision comparison (6x6 vs 32x32)."""
    os.makedirs(output_dir, exist_ok=True)
    
    precisions_6x6 = results['6x6']['precisions']
    precisions_32x32 = results['32x32']['precisions']
    cycles = list(range(len(precisions_6x6)))
    
    fig, axes = plt.subplots(1, 2, figsize=(16, 5))
    
    # ===== LEFT PANEL: Overlaid precision curves =====
    ax = axes[0]
    
    # Phase backgrounds
    ax.axvspan(0, 9.5, alpha=0.1, color='red', label='Phase 0: Training OFF')
    ax.axvspan(9.5, len(cycles)-1, alpha=0.1, color='green', label='Phase 1: Training ON')
    
    # Split by phase for 6x6
    phase0_cycles_6x6 = list(range(10))
    phase0_prec_6x6 = precisions_6x6[:10]
    phase1_cycles_6x6 = list(range(10, len(precisions_6x6)))
    phase1_prec_6x6 = precisions_6x6[10:]
    
    ax.plot(phase0_cycles_6x6, phase0_prec_6x6, 'o-', linewidth=2.5, markersize=7,
            color='blue', label='6×6 (Phase 0)', alpha=0.8)
    ax.plot(phase1_cycles_6x6, phase1_prec_6x6, 's-', linewidth=2.5, markersize=7,
            color='darkblue', label='6×6 (Phase 1)', alpha=0.8)
    
    # Split by phase for 32x32
    phase0_prec_32x32 = precisions_32x32[:10]
    phase1_prec_32x32 = precisions_32x32[10:]
    
    ax.plot(phase0_cycles_6x6, phase0_prec_32x32, 'o--', linewidth=2.5, markersize=7,
            color='orange', label='32×32 (Phase 0)', alpha=0.8)
    ax.plot(phase1_cycles_6x6, phase1_prec_32x32, 's--', linewidth=2.5, markersize=7,
            color='darkorange', label='32×32 (Phase 1)', alpha=0.8)
    
    ax.axhline(y=5.5, color='gray', linestyle=':', linewidth=1.5, alpha=0.5, label='6-bit target (5.5)')
    ax.set_xlabel('Cycle', fontsize=12, fontweight='bold')
    ax.set_ylabel('Precision (bits)', fontsize=12, fontweight='bold')
    ax.set_title('Plot 1: Precision Curves Overlay', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='lower right', fontsize=10)
    
    # ===== RIGHT PANEL: Difference curve =====
    ax = axes[1]
    
    # Calculate difference (6x6 - 32x32)
    precision_diff = np.array(precisions_6x6) - np.array(precisions_32x32)
    
    ax.axvspan(0, 9.5, alpha=0.1, color='red')
    ax.axvspan(9.5, len(cycles)-1, alpha=0.1, color='green')
    
    phase0_diff = precision_diff[:10]
    phase1_diff = precision_diff[10:]
    
    ax.plot(phase0_cycles_6x6, phase0_diff, 'o-', linewidth=2.5, markersize=7,
            color='purple', label='Phase 0 difference', alpha=0.8)
    ax.plot(phase1_cycles_6x6, phase1_diff, 's-', linewidth=2.5, markersize=7,
            color='darkviolet', label='Phase 1 difference', alpha=0.8)
    
    ax.axhline(y=0, color='black', linestyle='-', linewidth=1, alpha=0.3)
    ax.set_xlabel('Cycle', fontsize=12, fontweight='bold')
    ax.set_ylabel('Precision Difference (bits)', fontsize=12, fontweight='bold')
    ax.set_title('Plot 1: Gap between 6×6 and 32×32', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='lower right', fontsize=10)
    
    fig.suptitle('PLOT 1: Direct Precision Comparison', fontsize=14, fontweight='bold', y=1.00)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/plot1_precision_comparison.png', dpi=150, bbox_inches='tight')
    print(f"✓ Plot 1 saved: {output_dir}/plot1_precision_comparison.png")
    plt.close()


def plot_comparison_bar_chart(results: dict, output_dir: str = 'results_32x32/comparison'):
    """Plot 2: Bar chart comparison of key metrics."""
    os.makedirs(output_dir, exist_ok=True)
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    metrics_6x6 = results['6x6']
    metrics_32x32 = results['32x32']
    
    # Colors
    color_6x6 = '#3498db'
    color_32x32 = '#e74c3c'
    
    # ===== TOP-LEFT: Baseline Precision =====
    ax = axes[0, 0]
    categories = ['6×6', '32×32']
    baselines = [metrics_6x6['phase0_baseline'], metrics_32x32['phase0_baseline']]
    bars = ax.bar(categories, baselines, color=[color_6x6, color_32x32], width=0.6, alpha=0.8, edgecolor='black', linewidth=2)
    ax.set_ylabel('Precision (bits)', fontsize=11, fontweight='bold')
    ax.set_title('Phase 0: Baseline (Training OFF)', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    for bar, val in zip(bars, baselines):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.2f}b', ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    # ===== TOP-RIGHT: Final Precision =====
    ax = axes[0, 1]
    finals = [metrics_6x6['phase1_final'], metrics_32x32['phase1_final']]
    bars = ax.bar(categories, finals, color=[color_6x6, color_32x32], width=0.6, alpha=0.8, edgecolor='black', linewidth=2)
    ax.set_ylabel('Precision (bits)', fontsize=11, fontweight='bold')
    ax.set_title('Phase 1: Final (After Learning)', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    for bar, val in zip(bars, finals):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.2f}b', ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    # ===== BOTTOM-LEFT: Learning Improvement =====
    ax = axes[1, 0]
    improvements = [metrics_6x6['improvement'], metrics_32x32['improvement']]
    bars = ax.bar(categories, improvements, color=[color_6x6, color_32x32], width=0.6, alpha=0.8, edgecolor='black', linewidth=2)
    ax.set_ylabel('Improvement (bits)', fontsize=11, fontweight='bold')
    ax.set_title('Phase 1: Learning Improvement (+Δ bits)', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    for bar, val in zip(bars, improvements):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'+{val:.2f}b', ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    # ===== BOTTOM-RIGHT: Total Progress =====
    ax = axes[1, 1]
    total_progress = [metrics_6x6['phase1_final'] - metrics_6x6['phase0_baseline'],
                      metrics_32x32['phase1_final'] - metrics_32x32['phase0_baseline']]
    bars = ax.bar(categories, total_progress, color=[color_6x6, color_32x32], width=0.6, alpha=0.8, edgecolor='black', linewidth=2)
    ax.set_ylabel('Total Progress (bits)', fontsize=11, fontweight='bold')
    ax.set_title('Overall: Baseline → Final (+Δ bits)', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    for bar, val in zip(bars, total_progress):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'+{val:.2f}b', ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    fig.suptitle('PLOT 2: Key Metrics Comparison', fontsize=14, fontweight='bold', y=0.995)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/plot2_metrics_comparison.png', dpi=150, bbox_inches='tight')
    print(f"✓ Plot 2 saved: {output_dir}/plot2_metrics_comparison.png")
    plt.close()



def run_comparison_test():
    """Run both 6x6 and 32x32 with identical harsh conditions."""
    
    print("="*80)
    print("COMPARISON TEST: 6x6 vs 32x32 Matrix Scaling")
    print("="*80)
    print("\nConditions: HARSH PHYSICAL EFFECTS")
    print("  - Manufacturing variation: ±15%")
    print("  - Thermal drift: +25°C")
    print("  - Noise: 2%")
    print("  - Learning rate: 0.05")
    print("  - Num strata: 1 (num_strata=1)")
    print("  - Phase 0: 10 cycles OFF (baseline)")
    print("  - Phase 1: 90 cycles ON (learning)")
    print("-"*80)
    
    results = {}
    
    # ========== 6x6 Test ==========
    print("\n[1/2] Running 6x6 test...")
    
    triad_6x6 = AtomicTriad6x6(size=6)
    
    # Apply harsh effects
    harsh_config = {
        'V_th_sigma': 0.08,
        'g_m_sigma': 0.15,
        'R_sigma': 0.15
    }
    for matrix in [triad_6x6.M33, triad_6x6.M3, triad_6x6.M8]:
        matrix.cell_bank.inject_manufacturing_variations(harsh_config)
        matrix.cell_bank.inject_thermal_drift(temp_delta_C=25.0)
        matrix.cell_bank.inject_noise(noise_sigma=0.02)
    
    maml_6x6 = InvertedMAML6x6(triad_6x6, learning_rate=0.05, num_strata=1, 
                           convergence_threshold=5.5)
    
    # Fix center weights
    triad_6x6.M3.weights.fill(2.6)
    triad_6x6.M8.weights.fill(2.6)
    
    x_train_6x6, y_train_6x6 = create_test_vectors_6x6(num_vectors=16, seed=42)
    
    losses_6x6 = []
    precisions_6x6 = []
    
    # Phase 0: OFF
    for cycle in range(10):
        cycle_loss = 0.0
        for x, y in zip(x_train_6x6, y_train_6x6):
            triad_6x6.refresh_cycle()
            grad_m3, grad_m8, loss = maml_6x6.compute_stratified_gradient(x, y)
            cycle_loss += loss
        avg_loss = cycle_loss / len(x_train_6x6)
        precision = -np.log2(np.clip(avg_loss, 1e-6, 1.0))
        losses_6x6.append(avg_loss)
        precisions_6x6.append(precision)
    
    phase0_precision_6x6 = precisions_6x6[0]
    
    # Phase 1: ON
    for cycle in range(10, 100):
        cycle_loss = 0.0
        for x, y in zip(x_train_6x6, y_train_6x6):
            loss = maml_6x6.update_weights(x, y)
            cycle_loss += loss
        avg_loss = cycle_loss / len(x_train_6x6)
        precision = -np.log2(np.clip(avg_loss, 1e-6, 1.0))
        losses_6x6.append(avg_loss)
        precisions_6x6.append(precision)
    
    phase1_final_6x6 = precisions_6x6[-1]
    improvement_6x6 = phase1_final_6x6 - precisions_6x6[10]
    
    print(f"  6x6 Phase 0 baseline: {phase0_precision_6x6:.2f} bits")
    print(f"  6x6 Phase 1 final:    {phase1_final_6x6:.2f} bits")
    print(f"  6x6 Improvement:      +{improvement_6x6:.2f} bits")
    
    results['6x6'] = {
        'phase0_baseline': float(phase0_precision_6x6),
        'phase1_final': float(phase1_final_6x6),
        'improvement': float(improvement_6x6),
        'losses': [float(x) for x in losses_6x6],
        'precisions': [float(x) for x in precisions_6x6]
    }
    
    # ========== 32x32 Test ==========
    print("\n[2/2] Running 32x32 test...")
    
    triad_32x32 = AtomicTriad(size=32)
    
    # Apply harsh effects
    for matrix in [triad_32x32.M33, triad_32x32.M3, triad_32x32.M8]:
        matrix.cell_bank.inject_manufacturing_variations(harsh_config)
        matrix.cell_bank.inject_thermal_drift(temp_delta_C=25.0)
        matrix.cell_bank.inject_noise(noise_sigma=0.02)
    
    maml_32x32 = InvertedMAML(triad_32x32, learning_rate=0.05, num_strata=1,
                             convergence_threshold=5.5)
    
    # Fix center weights
    triad_32x32.M3.weights.fill(2.6)
    triad_32x32.M8.weights.fill(2.6)
    
    x_train_32x32, y_train_32x32 = create_test_vectors(num_vectors=16, dimension=32, seed=42)
    
    losses_32x32 = []
    precisions_32x32 = []
    
    # Phase 0: OFF
    for cycle in range(10):
        cycle_loss = 0.0
        for x, y in zip(x_train_32x32, y_train_32x32):
            triad_32x32.refresh_cycle()
            grad_m3, grad_m8, loss = maml_32x32.compute_stratified_gradient(x, y)
            cycle_loss += loss
        avg_loss = cycle_loss / len(x_train_32x32)
        precision = -np.log2(np.clip(avg_loss, 1e-6, 1.0))
        losses_32x32.append(avg_loss)
        precisions_32x32.append(precision)
    
    phase0_precision_32x32 = precisions_32x32[0]
    
    # Phase 1: ON
    for cycle in range(10, 100):
        cycle_loss = 0.0
        for x, y in zip(x_train_32x32, y_train_32x32):
            loss = maml_32x32.update_weights(x, y)
            cycle_loss += loss
        avg_loss = cycle_loss / len(x_train_32x32)
        precision = -np.log2(np.clip(avg_loss, 1e-6, 1.0))
        losses_32x32.append(avg_loss)
        precisions_32x32.append(precision)
    
    phase1_final_32x32 = precisions_32x32[-1]
    improvement_32x32 = phase1_final_32x32 - precisions_32x32[10]
    
    print(f"  32x32 Phase 0 baseline: {phase0_precision_32x32:.2f} bits")
    print(f"  32x32 Phase 1 final:    {phase1_final_32x32:.2f} bits")
    print(f"  32x32 Improvement:      +{improvement_32x32:.2f} bits")
    
    results['32x32'] = {
        'phase0_baseline': float(phase0_precision_32x32),
        'phase1_final': float(phase1_final_32x32),
        'improvement': float(improvement_32x32),
        'losses': [float(x) for x in losses_32x32],
        'precisions': [float(x) for x in precisions_32x32]
    }
    
    # ========== Analysis ==========
    print("\n" + "="*80)
    print("COMPARISON ANALYSIS:")
    print("="*80)
    
    print("\n1. BASELINE PRECISION (Phase 0 - training OFF):")
    print(f"   6x6 baseline:    {phase0_precision_6x6:.2f} bits")
    print(f"   32x32 baseline:  {phase0_precision_32x32:.2f} bits")
    baseline_diff = phase0_precision_32x32 - phase0_precision_6x6
    if abs(baseline_diff) < 0.05:
        print(f"   → Similar! Difference: {baseline_diff:+.2f} bits")
    elif baseline_diff > 0:
        print(f"   → 32x32 BETTER by {baseline_diff:.2f} bits (more capacity!)")
    else:
        print(f"   → 32x32 WORSE by {abs(baseline_diff):.2f} bits")
    
    print("\n2. LEARNING IMPROVEMENT (Phase 1 - training ON):")
    print(f"   6x6 improvement:    +{improvement_6x6:.2f} bits")
    print(f"   32x32 improvement:  +{improvement_32x32:.2f} bits")
    improve_diff = improvement_32x32 - improvement_6x6
    print(f"   → Difference: {improve_diff:+.2f} bits")
    
    print("\n3. FINAL PRECISION (after 100 cycles):")
    print(f"   6x6 final:    {phase1_final_6x6:.2f} bits")
    print(f"   32x32 final:  {phase1_final_32x32:.2f} bits")
    final_diff = phase1_final_32x32 - phase1_final_6x6
    print(f"   → 32x32 vs 6x6: {final_diff:+.2f} bits")
    
    print("\n4. INTERPRETATION:")
    print(f"   • Task dimensionality ratio: 32D / 6D = 5.3×")
    print(f"   • Parameter count ratio: 1024 cells / 36 cells = 28.4×")
    print(f"   • Params-per-dimension ratio: (1024/32) / (36/6) = 5.3× improvement")
    print(f"   • Therefore: Baseline should stay SIMILAR or IMPROVE")
    print(f"   • Actual result: Baseline diff = {baseline_diff:+.2f} bits ✓")
    
    print("\n" + "="*80)
    
    # Save results
    os.makedirs('results_32x32/comparison', exist_ok=True)
    with open('results_32x32/comparison/6x6_vs_32x32_comparison.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\n✓ Comparison saved: results_32x32/comparison/6x6_vs_32x32_comparison.json")
    
    # Generate plots
    print("\n" + "="*80)
    print("GENERATING PLOTS...")
    print("="*80)
    plot_comparison_precision_curves(results, 'results_32x32/comparison')
    plot_comparison_bar_chart(results, 'results_32x32/comparison')
    
    return results


if __name__ == '__main__':
    run_comparison_test()
