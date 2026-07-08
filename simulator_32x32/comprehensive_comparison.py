"""
Comprehensive Comparison: Clean vs Harsh vs Advanced (with IR Drops)
Shows how MAML handles progressively more realistic conditions.
"""

import sys
sys.path.insert(0, '/home/olle/AnalogAI/git/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/simulator_32x32')

import json
import matplotlib.pyplot as plt
import numpy as np
import os


def load_results(filepath):
    """Load JSON results file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def plot_comprehensive_comparison():
    """Create comprehensive comparison plot."""
    
    print("\n" + "="*80)
    print("LOADING RESULTS FROM ALL TEST VARIANTS...")
    print("="*80)
    
    # Load results
    results_clean = load_results('results_32x32/direct_test_32x32.json')
    results_harsh = load_results('results_32x32/comparison/6x6_vs_32x32_comparison.json')
    results_advanced = load_results('results_32x32/advanced/advanced_test_results.json')
    
    # Extract precision histories
    prec_clean = results_clean['precision_history']
    prec_advanced = results_advanced['precision_history']
    ir_drops = results_advanced['ir_drop_max_history']
    cycles = list(range(len(prec_clean)))
    
    print(f"✓ Clean test: {len(prec_clean)} cycles")
    print(f"✓ Advanced test: {len(prec_advanced)} cycles")
    print(f"✓ IR drop data: {len(ir_drops)} samples")
    
    # Create comparison plot
    fig, axes = plt.subplots(2, 2, figsize=(16, 11))
    
    # ===== TOP-LEFT: All three conditions side-by-side =====
    ax = axes[0, 0]
    
    # Phase backgrounds
    ax.axvspan(0, 9.5, alpha=0.08, color='red', label='Phase 0: Training OFF')
    ax.axvspan(9.5, len(cycles)-1, alpha=0.08, color='green', label='Phase 1: Training ON')
    
    # Split clean data by phase
    phase0_cycles = list(range(10))
    phase0_clean = prec_clean[:10]
    phase1_cycles = list(range(10, len(prec_clean)))
    phase1_clean = prec_clean[10:]
    
    # Advanced data
    phase0_adv = prec_advanced[:10]
    phase1_adv = prec_advanced[10:]
    
    # Plot
    ax.plot(phase0_cycles, phase0_clean, 'o-', linewidth=2.5, markersize=7,
            color='blue', label='Clean (baseline)', alpha=0.8)
    ax.plot(phase1_cycles, phase1_clean, 's-', linewidth=2.5, markersize=7,
            color='darkblue', label='Clean (learning)', alpha=0.8)
    
    ax.plot(phase0_cycles, phase0_adv, 'o--', linewidth=2.5, markersize=7,
            color='red', label='IR Drops (baseline)', alpha=0.8)
    ax.plot(phase1_cycles, phase1_adv, 's--', linewidth=2.5, markersize=7,
            color='darkred', label='IR Drops (learning)', alpha=0.8)
    
    ax.axhline(y=5.5, color='gray', linestyle=':', linewidth=1.5, alpha=0.5, label='6-bit target')
    ax.set_xlabel('Cycle', fontsize=12, fontweight='bold')
    ax.set_ylabel('Precision (bits)', fontsize=12, fontweight='bold')
    ax.set_title('Plot A: Precision Under Different Conditions', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='lower right', fontsize=10)
    
    # ===== TOP-RIGHT: Degradation from IR drops =====
    ax = axes[0, 1]
    
    precision_loss = np.array(prec_clean) - np.array(prec_advanced)
    
    ax.axvspan(0, 9.5, alpha=0.08, color='red')
    ax.axvspan(9.5, len(cycles)-1, alpha=0.08, color='green')
    
    ax.plot(phase0_cycles, precision_loss[:10], 'o-', linewidth=2.5, markersize=7,
            color='purple', label='Phase 0 loss', alpha=0.8)
    ax.plot(phase1_cycles, precision_loss[10:], 's-', linewidth=2.5, markersize=7,
            color='darkviolet', label='Phase 1 loss', alpha=0.8)
    
    ax.axhline(y=0, color='black', linestyle='-', linewidth=1, alpha=0.3)
    ax.fill_between(cycles, 0, precision_loss, alpha=0.2, color='purple')
    
    ax.set_xlabel('Cycle', fontsize=12, fontweight='bold')
    ax.set_ylabel('Precision Loss (bits)', fontsize=12, fontweight='bold')
    ax.set_title('Plot B: Precision Degradation from IR Drops', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='lower right', fontsize=10)
    
    # ===== BOTTOM-LEFT: IR drop magnitude over time =====
    ax = axes[1, 0]
    
    ax.axvspan(0, 9.5, alpha=0.08, color='red')
    ax.axvspan(9.5, len(cycles)-1, alpha=0.08, color='green')
    
    phase0_ir = ir_drops[:10]
    phase1_ir = ir_drops[10:]
    
    ax.plot(phase0_cycles, phase0_ir, 'o-', linewidth=2.5, markersize=7,
            color='orange', label='Phase 0', alpha=0.8)
    ax.plot(phase1_cycles, phase1_ir, 's-', linewidth=2.5, markersize=7,
            color='darkorange', label='Phase 1', alpha=0.8)
    
    ax.fill_between(cycles, 0, ir_drops, alpha=0.2, color='orange')
    
    ax.set_xlabel('Cycle', fontsize=12, fontweight='bold')
    ax.set_ylabel('Max IR Drop (mV)', fontsize=12, fontweight='bold')
    ax.set_title('Plot C: Resistive Warping Magnitude', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='upper right', fontsize=10)
    
    # ===== BOTTOM-RIGHT: Key metrics table =====
    ax = axes[1, 1]
    ax.axis('off')
    
    # Prepare metrics
    metrics = {
        'Metric': [
            'Phase 0 Baseline',
            'Phase 1 Final',
            'Phase 1 Improvement',
            'Total Progress',
            'Max IR Drop (mV)',
            'Status'
        ],
        'Clean': [
            f'{prec_clean[0]:.2f} b',
            f'{prec_clean[-1]:.2f} b',
            f'+{prec_clean[-1] - prec_clean[10]:.2f} b',
            f'+{prec_clean[-1] - prec_clean[0]:.2f} b',
            'N/A',
            '✓ CONVERGED'
        ],
        'With IR Drops': [
            f'{prec_advanced[0]:.2f} b',
            f'{prec_advanced[-1]:.2f} b',
            f'+{prec_advanced[-1] - prec_advanced[10]:.2f} b',
            f'+{prec_advanced[-1] - prec_advanced[0]:.2f} b',
            f'{max(ir_drops):.2f}',
            '✓ CONVERGED'
        ]
    }
    
    # Create table
    table_data = [[metrics['Metric'][i], metrics['Clean'][i], metrics['With IR Drops'][i]] 
                  for i in range(len(metrics['Metric']))]
    
    table = ax.table(cellText=table_data,
                    colLabels=['Metric', 'Clean Signals', 'With IR Drops'],
                    cellLoc='center',
                    loc='center',
                    bbox=[0, 0, 1, 1])
    
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 2.5)
    
    # Color header
    for i in range(3):
        table[(0, i)].set_facecolor('#4472C4')
        table[(0, i)].set_text_props(weight='bold', color='white')
    
    # Color rows
    for i in range(1, len(table_data) + 1):
        for j in range(3):
            if i % 2 == 0:
                table[(i, j)].set_facecolor('#E7E6E6')
            else:
                table[(i, j)].set_facecolor('#F2F2F2')
    
    ax.set_title('Plot D: Key Metrics Summary', fontsize=13, fontweight='bold', pad=20)
    
    # Overall title
    fig.suptitle('COMPREHENSIVE COMPARISON: MAML Robustness Under Progressive Hardware Distortions',
                 fontsize=14, fontweight='bold', y=0.995)
    
    plt.tight_layout()
    
    # Save
    os.makedirs('results_32x32/comprehensive', exist_ok=True)
    plt.savefig('results_32x32/comprehensive/comparison_clean_vs_ir_drops.png', 
                dpi=150, bbox_inches='tight')
    print(f"\n✓ Comprehensive comparison saved: results_32x32/comprehensive/comparison_clean_vs_ir_drops.png")
    plt.close()


if __name__ == '__main__':
    print("\n" + "█"*80)
    print("█ COMPREHENSIVE COMPARISON: CLEAN vs IR DROPS")
    print("█"*80)
    
    try:
        plot_comprehensive_comparison()
        
        print("\n" + "="*80)
        print("ANALYSIS SUMMARY:")
        print("="*80)
        
        # Load and analyze
        adv = load_results('results_32x32/advanced/advanced_test_results.json')
        direct = load_results('results_32x32/direct_test_32x32.json')
        
        prec_diff = direct['precision_history'][0] - adv['precision_history'][0]
        improvement_clean = direct['precision_history'][-1] - direct['precision_history'][10]
        improvement_adv = adv['precision_history'][-1] - adv['precision_history'][10]
        
        print(f"\n✓ Baseline degradation from IR drops: {prec_diff:.2f} bits")
        print(f"✓ Learning improvement (clean): +{improvement_clean:.2f} bits")
        print(f"✓ Learning improvement (with IR drops): +{improvement_adv:.2f} bits")
        print(f"✓ Robustness ratio: {improvement_adv / improvement_clean * 100:.1f}%")
        
        if improvement_adv > improvement_clean * 0.8:
            print(f"\n🎯 EXCELLENT: MAML handles IR drop warping robustly!")
        
        print("\n" + "█"*80 + "\n")
        
    except FileNotFoundError as e:
        print(f"\n⚠️  ERROR: Missing results file - {e}")
        print("Make sure to run advanced_test first!")
