#!/usr/bin/env python3
"""
DIRECT TEST 32x32: Scaled version of breakthrough 6x6 convergence
===================================================================

What is "Direct Test"?
  - Tests the PURE optimization algorithm WITHOUT physical complexity
  - Creates fresh 32x32 triad + MAML + test vectors
  - Runs training without manufacturing variations or thermal effects
  - Shows what optimal num_strata=1 strategy achieves on larger matrices
  - Should converge similarly to 6x6 (6-7 bits range)

Key Differences from scaled wrong version:
  ✓ FIXED: Calls update_weights() directly (handles gradient internally)
  ✗ WRONG: Was calling compute_stratified_gradient() THEN update_weights() (double measurement)
  
What IS included in Direct Test 32x32:
  ✓ Full Atomic Triad (M33 PRIMARY + M3 + M8 CORRECTIONS)
  ✓ Inverted MAML learning algorithm
  ✓ Stratified batching (num_strata=1 = BREAKTHROUGH strategy)
  ✓ Momentum SGD
  ✓ 32-dimensional vectors
  
Expected Result:
  Should follow similar convergence curve as 6x6:
  Cycle  0: ~5-6 bits
  Cycle 10: ~5-6 bits
  Cycle 50: ~6-7 bits
  Cycle 99: ~7+ bits (if initialization favorable)
"""

import numpy as np
import json
from datetime import datetime
from pathlib import Path
import matplotlib.pyplot as plt

from matrix_core import AtomicTriad
from maml_optimizer import InvertedMAML, create_test_vectors


def run_direct_test_32(max_cycles: int = 100, num_samples: int = 16, 
                       seed: int = 42, verbose: bool = True) -> dict:
    """
    Direct Test 32x32: Pure MAML optimization without physical effects.
    
    CRITICAL FIX: Use update_weights() directly, not separate measure+update.
    
    TWO-PHASE:
    Phase 0 (Cycles 0-9):   Training OFF (baseline, center weights fixed)
    Phase 1 (Cycles 10+):   Training ON (learning enabled)
    
    Args:
        max_cycles: Training cycles
        num_samples: Number of test vectors
        seed: Random seed for reproducibility
        verbose: Print progress
    
    Returns:
        results: Dict with all metrics
    """
    
    if verbose:
        print("="*70)
        print("DIRECT TEST 32x32: Harsh Conditions with Physical Effects")
        print("="*70)
        print("\nConfiguration:")
        print(f"  Matrix size: 32x32 (scaled from 6x6)")
        print(f"  Cycles: {max_cycles}")
        print(f"  Samples: {num_samples}")
        print(f"  Seed: {seed}")
        print(f"  Measurement strategy: num_strata=1 (OPTIMAL - 0.5ms only)")
        print(f"  Physical effects: HARSH CONDITIONS ENABLED")
        print(f"    - Manufacturing variation: ±15% (warped transistors)")
        print(f"    - Thermal drift: +25°C (temperature stress)")
        print(f"    - Distortion noise: 2% (nonlinear effects)")
        print(f"  Learning rate: 0.05")
        print("\nPhases:")
        print(f"  Phase 0 (Cycles 0-9):   Training OFF (baseline, center weights)")
        print(f"  Phase 1 (Cycles 10+):   Training ON (learning enabled)")
        print("\nNote: HARSH PHYSICAL CONDITIONS - real-world challenge")
        print("      Warped transistors with manufacturing distortion")
        print("      Thermal drift and nonlinear effects active")
        print("      Full Atomic Triad with M3/M8 corrections ACTIVE")
        print("-"*70 + "\n")
    
    # Initialize 32x32 system with HARSH physical effects
    # Warped transistors with manufacturing variations and thermal stress
    triad = AtomicTriad(size=32)
    
    # Apply harsh physical effects to all matrices
    harsh_config = {
        'V_th_sigma': 0.08,      # ±8% threshold variation (warped transistors)
        'g_m_sigma': 0.15,       # ±15% transconductance variation (distortion)
        'R_sigma': 0.15          # ±15% resistance variation (discharge variation)
    }
    
    # Apply to all three matrices
    for matrix in [triad.M33, triad.M3, triad.M8]:
        matrix.cell_bank.inject_manufacturing_variations(harsh_config)
        matrix.cell_bank.inject_thermal_drift(temp_delta_C=25.0)  # +25°C thermal stress
        matrix.cell_bank.inject_noise(noise_sigma=0.02)           # 2% noise injection
    maml = InvertedMAML(triad, learning_rate=0.05, num_strata=1, 
                       convergence_threshold=5.5)
    
    # Fix compensation weights at center for Phase 0
    triad.M3.weights.fill(2.6)
    triad.M8.weights.fill(2.6)
    
    # Generate 32-dimensional test vectors
    x_train, y_train = create_test_vectors(num_vectors=num_samples, 
                                          dimension=32, seed=seed)
    
    # Training loop - TWO PHASES
    losses = []
    precisions = []
    phases = []
    converged_cycle = None
    
    # Phase 0: Training OFF (10 cycles - just measure, don't update)
    if verbose:
        print("Phase 0: Training OFF")
    
    for cycle in range(10):
        cycle_loss = 0.0
        
        # Measure only (don't update weights)
        for x, y in zip(x_train, y_train):
            triad.refresh_cycle()
            grad_m3, grad_m8, loss = maml.compute_stratified_gradient(x, y)
            cycle_loss += loss
        
        # Average cycle loss
        avg_loss = cycle_loss / len(x_train)
        
        # Calculate precision
        precision = -np.log2(np.clip(avg_loss, 1e-6, 1.0))
        
        losses.append(avg_loss)
        precisions.append(precision)
        phases.append(0)
        
        if verbose:
            print(f"  Phase 0, Cycle {cycle:3d}: Loss={avg_loss:.4e}, Precision={precision:.2f} bits (training OFF)")
    
    # Phase 1: Training ON (remaining cycles - measure and update)
    if verbose:
        print("\nPhase 1: Training ON")
    
    for cycle in range(10, max_cycles):
        cycle_loss = 0.0
        
        # Update weights on each sample (update_weights handles gradient internally)
        for x, y in zip(x_train, y_train):
            loss = maml.update_weights(x, y)
            cycle_loss += loss
        
        # Average cycle loss
        avg_loss = cycle_loss / len(x_train)
        
        # Calculate precision
        precision = -np.log2(np.clip(avg_loss, 1e-6, 1.0))
        
        losses.append(avg_loss)
        precisions.append(precision)
        phases.append(1)
        
        # Check convergence (6-bit = 5.5 bits)
        if precision >= 5.5 and converged_cycle is None:
            converged_cycle = cycle
        
        # Print progress
        if verbose and ((cycle - 10) % 10 == 0 or cycle == max_cycles - 1):
            status = "✓ CONVERGED" if precision >= 5.5 else ""
            print(f"  Phase 1, Cycle {cycle:3d}: Loss={avg_loss:.4e}, Precision={precision:.2f} bits {status}")
    
    # Results summary
    results = {
        'test_type': 'DIRECT_32x32_TWO_PHASE',
        'timestamp': datetime.now().isoformat(),
        'config': {
            'matrix_size': 32,
            'max_cycles': max_cycles,
            'num_samples': num_samples,
            'seed': seed,
            'num_strata': 1,
            'learning_rate': 0.05,
            'physical_effects': 'HARSH CONDITIONS (±15% mfg, +25°C thermal, 2% distortion)',
            'measurement_method': 'FIXED (single update_weights call)',
            'phases': 'Phase 0 (10 cycles OFF) + Phase 1 (remaining ON)'
        },
        'phases': {
            'phase_0_cycles': 10,
            'phase_0_off_precision_start': float(precisions[0]),
            'phase_0_off_precision_end': float(precisions[9]),
            'phase_1_on_precision_start': float(precisions[10]),
            'phase_1_on_precision_end': float(precisions[-1]),
            'phase_1_improvement': float(precisions[-1] - precisions[10])
        },
        'convergence': {
            'final_loss': float(losses[-1]),
            'final_precision_bits': float(precisions[-1]),
            'target_precision_bits': 5.5,
            'converged': bool(precisions[-1] >= 5.5),
            'convergence_cycle': int(converged_cycle) if converged_cycle is not None else None,
            'start_precision': float(precisions[0]),
            'start_loss': float(losses[0])
        },
        'loss_history': [float(x) for x in losses],
        'precision_history': [float(x) for x in precisions],
        'phase_history': phases
    }
    
    if verbose:
        print("\n" + "-"*70)
        print("DIRECT TEST 32x32 RESULTS (TWO PHASES):")
        print(f"\n  Phase 0 (Training OFF - Baseline):")
        print(f"    Cycle 0: Precision={precisions[0]:.2f} bits (start)")
        print(f"    Cycle 9: Precision={precisions[9]:.2f} bits (end)")
        print(f"    Change:  {precisions[9] - precisions[0]:+.2f} bits (expected: ~0)")
        print(f"\n  Phase 1 (Training ON - Learning):")
        print(f"    Cycle 10: Precision={precisions[10]:.2f} bits (start)")
        print(f"    Cycle 99: Precision={precisions[-1]:.2f} bits (final)")
        print(f"    Improvement: +{precisions[-1] - precisions[10]:.2f} bits")
        print(f"\n  Overall Summary:")
        print(f"    Total improvement: +{precisions[-1] - precisions[0]:.2f} bits")
        print(f"    Target precision:  5.5 bits (6-bit)")
        print(f"    Status: {'✓ CONVERGED' if precisions[-1] >= 5.5 else '✗ NOT CONVERGED'}")
        if converged_cycle is not None:
            print(f"    Converged at cycle: {converged_cycle}")
        print("-"*70)
    
    return results


def plot_direct_test(results: dict, output_dir: str = './results_32x32'):
    """Plot convergence curve with two-phase visualization."""
    os.makedirs(output_dir, exist_ok=True)
    
    precisions = results['precision_history']
    losses = results['loss_history']
    phases = results.get('phase_history', [0]*10 + [1]*(len(precisions)-10))
    cycles = list(range(len(precisions)))
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 10))
    
    # === Panel 1: Precision vs cycle with phase background ===
    # Add phase backgrounds
    ax1.axvspan(0, 9.5, alpha=0.1, color='red', label='Phase 0: Training OFF')
    ax1.axvspan(9.5, len(precisions)-1, alpha=0.1, color='green', label='Phase 1: Training ON')
    
    # Split data by phase
    phase0_cycles = [c for c, p in enumerate(phases) if p == 0]
    phase0_prec = [precisions[c] for c in phase0_cycles]
    phase1_cycles = [c for c, p in enumerate(phases) if p == 1]
    phase1_prec = [precisions[c] for c in phase1_cycles]
    
    ax1.plot(phase0_cycles, phase0_prec, 'o-', linewidth=2, markersize=6, 
             color='red', label='Phase 0 data', alpha=0.7)
    ax1.plot(phase1_cycles, phase1_prec, 'o-', linewidth=2, markersize=6, 
             color='green', label='Phase 1 data', alpha=0.7)
    ax1.axhline(y=5.5, color='orange', linestyle='--', linewidth=2, label='6-bit Target (5.5)')
    ax1.set_xlabel('Cycle', fontsize=11)
    ax1.set_ylabel('Precision (bits)', fontsize=11)
    ax1.set_title('32x32 Direct Test: Precision with Phases', fontsize=12, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='lower right')
    
    # === Panel 2: Loss vs cycle (log scale) with phase background ===
    ax2.axvspan(0, 9.5, alpha=0.1, color='red')
    ax2.axvspan(9.5, len(losses)-1, alpha=0.1, color='green')
    
    phase0_loss = [losses[c] for c in phase0_cycles]
    phase1_loss = [losses[c] for c in phase1_cycles]
    
    ax2.semilogy(phase0_cycles, phase0_loss, 'o-', linewidth=2, markersize=6, 
                 color='red', label='Phase 0', alpha=0.7)
    ax2.semilogy(phase1_cycles, phase1_loss, 'o-', linewidth=2, markersize=6, 
                 color='green', label='Phase 1', alpha=0.7)
    ax2.set_xlabel('Cycle', fontsize=11)
    ax2.set_ylabel('Loss (MSE)', fontsize=11)
    ax2.set_title('32x32 Direct Test: Loss (log scale)', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3, which='both')
    ax2.legend(loc='upper right')
    
    # === Panel 3: Phase 0 zoom (just baseline) ===
    ax3.plot(phase0_cycles, phase0_prec, 'o-', linewidth=3, markersize=8, 
             color='red', label='Phase 0 (Training OFF)', alpha=0.8)
    ax3.set_xlabel('Cycle', fontsize=11)
    ax3.set_ylabel('Precision (bits)', fontsize=11)
    ax3.set_title('Phase 0: Baseline (Training OFF)', fontsize=12, fontweight='bold')
    ax3.grid(True, alpha=0.3)
    ax3.legend()
    ax3.set_ylim([min(phase0_prec)-0.1, max(phase0_prec)+0.1])
    
    # === Panel 4: Phase 1 zoom (learning curve) ===
    ax4.plot(phase1_cycles, phase1_prec, 'o-', linewidth=3, markersize=8, 
             color='green', label='Phase 1 (Training ON)', alpha=0.8)
    ax4.axhline(y=5.5, color='orange', linestyle='--', linewidth=2, label='6-bit Target (5.5)')
    ax4.set_xlabel('Cycle', fontsize=11)
    ax4.set_ylabel('Precision (bits)', fontsize=11)
    ax4.set_title('Phase 1: Learning Curve (Training ON)', fontsize=12, fontweight='bold')
    ax4.grid(True, alpha=0.3)
    ax4.legend()
    
    # Add overall figure title
    fig.suptitle('32x32 Direct Test: Two-Phase Analysis', fontsize=14, fontweight='bold', y=0.995)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/direct_test_32x32.png', dpi=150, bbox_inches='tight')
    print(f"\n✓ Plot saved: {output_dir}/direct_test_32x32.png")
    plt.close()


if __name__ == '__main__':
    import os
    
    # Run test with reproducible seed
    results = run_direct_test_32(max_cycles=100, num_samples=16, seed=42, verbose=True)
    
    # Save results
    os.makedirs('results_32x32', exist_ok=True)
    with open('results_32x32/direct_test_32x32.json', 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n✓ Results saved: results_32x32/direct_test_32x32.json")
    
    # Plot
    plot_direct_test(results)
