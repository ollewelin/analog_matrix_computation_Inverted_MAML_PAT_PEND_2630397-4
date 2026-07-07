#!/usr/bin/env python3
"""
Two-Phase Compensation Test: Show M33 Baseline vs M3/M8 Correction
====================================================================

ARCHITECTURE:
  - M33: PRIMARY PAYLOAD (fixed, from original task)
  - M3: FIRST CORRECTION (trainable, learns to adapt)
  - M8: SECOND CORRECTION (trainable, learns to compensate)

Phase 1 (Cycles 0-10):
  - M3 and M8 are FIXED at center point (NO CORRECTION)
  - M33 payload remains fixed (always fixed in Inverted MAML)
  - Shows how BAD the system is without correction!
  
Phase 2 (Cycles 10+):
  - M3 and M8 training is ENABLED
  - Corrections learn to compensate for M33 errors + analog nonidealities
  - Shows improvement from corrections

This validates that M3 and M8 correction are ESSENTIAL for high precision!
"""

import numpy as np
import matplotlib.pyplot as plt
import json
from matrix_core import AtomicTriad
from maml_optimizer import InvertedMAML, create_test_vectors


def run_two_phase_test(max_cycles=100, num_samples=16, seed=42, verbose=True):
    """
    Run two-phase compensation test.
    
    Phase 1: M3/M8 disabled (fixed at center) - baseline M33 performance
    Phase 2: M3/M8 enabled (training ON) - with correction
    
    Returns:
        results: Dict with phase1_precisions, phase2_precisions, transition_cycle
    """
    
    if verbose:
        print("="*75)
        print("TWO-PHASE COMPENSATION TEST")
        print("="*75)
        print()
        print("ARCHITECTURE:")
        print("  M33: PRIMARY PAYLOAD (fixed, from training task)")
        print("  M3:  FIRST CORRECTION (trainable)")
        print("  M8:  SECOND CORRECTION (trainable)")
        print()
        print("PHASE 1 (Cycles 0-10): M3 & M8 DISABLED (NO CORRECTION)")
        print("  - M3 & M8 weights fixed at 2.55V (center, zero output)")
        print("  - M33 PAYLOAD fixed (always fixed in Inverted MAML)")
        print("  - Question: How bad is M33 ALONE without correction?")
        print()
        print("PHASE 2 (Cycles 10+): M3 & M8 ENABLED (CORRECTION ON)")
        print("  - M3 & M8 learn to compensate for M33 errors")
        print("  - M33 remains fixed (never learns)")
        print("  - Question: How much do corrections improve precision?")
        print()
        print("-"*75)
    
    # Create test data
    x_train, y_train = create_test_vectors(num_vectors=num_samples, dimension=6, seed=seed)
    
    # Initialize system with MORE DISTORTION
    triad = AtomicTriad(size=6)
    triad.inject_manufacturing_variations({
        'V_th_sigma': 0.03,           # ±3% threshold variation (was 2%)
        'g_m_sigma': 0.05,            # ±5% transconductance variation (was 2%)
        'R_sigma': 0.05               # ±5% resistance variation (was 2%)
    })
    triad.inject_thermal_drift(temp_delta_C=12.0)  # INCREASED: 12°C (was 5°C)
    triad.inject_noise(noise_sigma=0.005)          # INCREASED: 0.5% (was 0.1%)
    
    # Create optimizer
    maml = InvertedMAML(triad, learning_rate=0.05, num_strata=1)
    
    # Center point voltage (middle of 2.1V - 3.1V range)
    W_center = np.full((6, 6), 2.55)
    
    # Track results
    phase1_precisions = []
    phase2_precisions = []
    phase1_losses = []
    phase2_losses = []
    
    # ===== PHASE 1: Cycles 0-10, M3/M8 DISABLED =====
    print("PHASE 1: Running without correction...")
    print()
    
    for cycle in range(11):
        # LOCK M3 and M8 at center (NO CORRECTION)
        maml.triad.set_correction_weights(W_center.copy(), W_center.copy())
        
        # Reset velocity (don't learn yet)
        maml.velocity_M3 = np.zeros((6, 6))
        maml.velocity_M8 = np.zeros((6, 6))
        
        # Measure precision with corrections disabled
        cycle_loss = 0.0
        for x, y in zip(x_train, y_train):
            triad.refresh_cycle()
            grad_m3, grad_m8, loss = maml.compute_stratified_gradient(x, y)
            cycle_loss += loss
        
        cycle_loss /= len(x_train)
        precision_bits = -np.log2(np.clip(cycle_loss, 1e-6, 1.0))
        phase1_precisions.append(precision_bits)
        phase1_losses.append(cycle_loss)
        
        if verbose:
            print(f"  Cycle {cycle:2d}: {precision_bits:.2f} bits | Loss: {cycle_loss:.6f}")
        
        # NOTE: Not updating weights in Phase 1 (M33 is fixed, M3/M8 locked at center)
    
    print()
    print(f"PHASE 1 RESULTS: M33 Baseline (no correction)")
    print(f"  Cycle 0:  {phase1_precisions[0]:.2f} bits (M33 alone, random M3/M8)")
    print(f"  Cycle 10: {phase1_precisions[10]:.2f} bits (M33 alone, fixed center M3/M8)")
    print(f"  Change:   {phase1_precisions[10] - phase1_precisions[0]:+.2f} bits")
    print()
    
    # ===== PHASE 2: Cycles 10+, M3/M8 ENABLED =====
    print("Turning ON correction training (M3 + M8 learning)...")
    print()
    
    for cycle in range(11, max_cycles):
        # Measure precision with M3/M8 learning enabled
        cycle_loss = 0.0
        for x, y in zip(x_train, y_train):
            triad.refresh_cycle()
            grad_m3, grad_m8, loss = maml.compute_stratified_gradient(x, y)
            cycle_loss += loss
        
        cycle_loss /= len(x_train)
        precision_bits = -np.log2(np.clip(cycle_loss, 1e-6, 1.0))
        phase2_precisions.append(precision_bits)
        phase2_losses.append(cycle_loss)
        
        if verbose and cycle % 5 == 0:
            print(f"  Cycle {cycle:2d}: {precision_bits:.2f} bits | Loss: {cycle_loss:.6f}")
        
        # Train M3 and M8 (normal Inverted MAML update)
        for x, y in zip(x_train, y_train):
            maml.update_weights(x, y)
    
    print()
    print(f"PHASE 2 RESULTS: With Correction (M3 + M8 learning)")
    print(f"  Cycle 10: {phase1_precisions[10]:.2f} bits (end of Phase 1, no correction yet)")
    print(f"  Cycle {max_cycles-1:2d}: {phase2_precisions[-1]:.2f} bits (after Phase 2 training)")
    print(f"  Improvement: {phase2_precisions[-1] - phase1_precisions[10]:+.2f} bits")
    print()
    
    results = {
        'phase1_precisions': phase1_precisions,
        'phase2_precisions': phase2_precisions,
        'phase1_losses': phase1_losses,
        'phase2_losses': phase2_losses,
        'transition_cycle': 10,
        'seed': seed,
        'max_cycles': max_cycles,
        'distortion': {
            'manufacturing_tolerance': 0.05,
            'thermal_drift_C': 12.0,
            'thermal_noise': 0.005
        }
    }
    
    return results


def plot_two_phase(results, output_dir='results'):
    """Plot comparison of Phase 1 vs Phase 2."""
    
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    phase1 = results['phase1_precisions']
    phase2 = results['phase2_precisions']
    transition = results['transition_cycle']
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    # --- Plot 1: Precision over time ---
    cycles_phase1 = list(range(len(phase1)))
    cycles_phase2 = list(range(transition, transition + len(phase2)))
    
    ax1.plot(cycles_phase1, phase1, 'o-', linewidth=2, markersize=6, 
             label='Phase 1: M33 Only (no correction)', color='red', alpha=0.7)
    ax1.plot(cycles_phase2, phase2, 's-', linewidth=2, markersize=6,
             label='Phase 2: M33 + M3 + M8 (with correction)', color='green', alpha=0.7)
    
    ax1.axvline(x=transition, color='orange', linestyle='--', linewidth=2, 
                label=f'Correction ON (Cycle {transition})')
    ax1.axhline(y=5.5, color='gray', linestyle=':', linewidth=1.5, label='6-bit Target (5.5b)')
    
    ax1.set_xlabel('Training Cycle', fontsize=11)
    ax1.set_ylabel('Precision (bits)', fontsize=11)
    ax1.set_title('M33 Baseline vs Full Correction (Two Phases)', fontsize=12, fontweight='bold')
    ax1.legend(loc='best', fontsize=10)
    ax1.grid(True, alpha=0.3)
    
    # --- Plot 2: Phase comparison (bar chart) ---
    categories = ['Phase 1\nCycle 0\n(M33+random)', 'Phase 1\nCycle 10\n(M33 ONLY)', 
                  'Phase 2\nCycle 11\n(Correction ON)', f'Phase 2\nCycle {results["max_cycles"]-1}\n(Trained)']
    values = [phase1[0], phase1[10], phase2[0] if len(phase2) > 0 else phase1[10], phase2[-1] if len(phase2) > 0 else phase1[10]]
    colors = ['red', 'orange', 'yellow', 'green']
    
    bars = ax2.bar(categories, values, color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)
    ax2.axhline(y=5.5, color='gray', linestyle=':', linewidth=2, label='6-bit Target')
    
    ax2.set_ylabel('Precision (bits)', fontsize=11)
    ax2.set_title('Correction Impact: Baseline vs With M3/M8 Learning', fontsize=12, fontweight='bold')
    ax2.set_ylim([4, 8.5])
    ax2.legend()
    ax2.grid(True, alpha=0.3, axis='y')
    
    # Add value labels on bars
    for bar, val in zip(bars, values):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.2f}b', ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    plt.tight_layout()
    filepath = os.path.join(output_dir, 'compensation_phases.png')
    plt.savefig(filepath, dpi=150, bbox_inches='tight')
    print(f"✓ Plot saved: {filepath}")
    plt.close()


if __name__ == '__main__':
    results = run_two_phase_test(max_cycles=100, num_samples=16, seed=42, verbose=True)
    plot_two_phase(results)
    
    # Save results
    import json
    with open('results/compensation_phases.json', 'w') as f:
        # Convert numpy arrays to lists for JSON serialization
        results_json = {
            'phase1_precisions': [float(x) for x in results['phase1_precisions']],
            'phase2_precisions': [float(x) for x in results['phase2_precisions']],
            'phase1_losses': [float(x) for x in results['phase1_losses']],
            'phase2_losses': [float(x) for x in results['phase2_losses']],
            'transition_cycle': results['transition_cycle'],
            'seed': results['seed'],
            'max_cycles': results['max_cycles'],
            'distortion': results['distortion']
        }
        json.dump(results_json, f, indent=2)
    
    print(f"✓ Results saved: results/compensation_phases.json")
    
    # Print final summary
    print()
    print("="*75)
    print("VALIDATION QUESTIONS:")
    print("="*75)
    print()
    print(f"1. How bad is M33 without correction?")
    print(f"   → Phase 1 (no correction): {results['phase1_precisions'][10]:.2f} bits")
    print()
    print(f"2. Does turning on M3/M8 correction help?")
    if len(results['phase2_precisions']) > 0:
        improvement = results['phase2_precisions'][-1] - results['phase1_precisions'][10]
        print(f"   → Improvement from corrections: {improvement:+.2f} bits")
    else:
        print(f"   → Phase 2 not completed")
    print()
    print(f"3. Can we reach 6-bit target with correction?")
    final_precision = results['phase2_precisions'][-1] if len(results['phase2_precisions']) > 0 else results['phase1_precisions'][-1]
    status = "✓ YES" if final_precision >= 5.5 else "✗ NO"
    print(f"   → {status}: Final precision is {final_precision:.2f} bits")
    print()
    print("CONCLUSION:")
    if len(results['phase2_precisions']) > 0:
        if results['phase2_precisions'][-1] - results['phase1_precisions'][10] > 0.5:
            print("  ✓ M3 and M8 corrections are CRITICAL for achieving high precision")
            print(f"  ✓ Corrections provide {results['phase2_precisions'][-1] - results['phase1_precisions'][10]:.2f} bits of improvement")
        else:
            print("  ? Corrections help but not dramatically")
    else:
        print("  ? Phase 2 incomplete, cannot assess correction impact")
