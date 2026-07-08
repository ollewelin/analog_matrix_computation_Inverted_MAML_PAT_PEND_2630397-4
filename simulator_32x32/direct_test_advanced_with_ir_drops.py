"""
Advanced Direct Test: 32x32 with Resistive IR Drop Warping
Tests MAML convergence with position-dependent voltage distortion.

Features:
  ✓ Resistive warping: V_drop = I·R varies by row/column position
  ✓ Non-linear effects: high current areas see larger distortion
  ✓ Harsh conditions: ±15% mfg variation, +25°C thermal, 2% noise, IR drops
  ✓ Two-phase: 10 cycles OFF (baseline), 90 cycles ON (learning)
  ✓ Resistive compensation: MAML must learn to correct warping too
"""

import sys
sys.path.insert(0, '/home/olle/AnalogAI/git/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/simulator_32x32')

import numpy as np
import os
import json
from datetime import datetime
import matplotlib.pyplot as plt
from matrix_core_advanced import AtomicTriadWithResistiveWarping
from maml_optimizer import InvertedMAML, create_test_vectors


def run_advanced_test(max_cycles: int = 100, num_samples: int = 16, 
                     seed: int = 42, R_interconnect: float = 0.5,
                     verbose: bool = True) -> dict:
    """
    Advanced direct test with resistive IR drop warping.
    
    Args:
        max_cycles: Training cycles
        num_samples: Test vectors
        seed: Random seed
        R_interconnect: Row/column interconnect resistance (Ω)
        verbose: Print progress
    """
    
    if verbose:
        print("="*80)
        print("ADVANCED TEST 32x32: Resistive IR Drop Warping")
        print("="*80)
        print("\nConfiguration:")
        print(f"  Matrix size: 32x32")
        print(f"  Cycles: {max_cycles}")
        print(f"  Samples: {num_samples}")
        print(f"  Seed: {seed}")
        print(f"  Measurement: num_strata=1 (0.5ms)")
        print(f"\nHarsh Physical Effects ENABLED:")
        print(f"  • Manufacturing variation: ±15% (warped transistors)")
        print(f"  • Thermal drift: +25°C (temperature stress)")
        print(f"  • Noise: 2% (thermal + shot noise)")
        print(f"  • IR DROP WARPING: NEW! (interconnect resistance effects)")
        print(f"    - Row/column resistance: {R_interconnect} Ω")
        print(f"    - Position-dependent V_drop from I·R")
        print(f"    - Non-linear distortion in high-current areas")
        print(f"\nPhases:")
        print(f"  Phase 0: 10 cycles OFF (measure baseline with warping)")
        print(f"  Phase 1: 90 cycles ON (learn to compensate warping)")
        print(f"\nLearning rate: 0.05")
        print("-"*80)
    
    # Initialize with resistive warping
    triad = AtomicTriadWithResistiveWarping(size=32, R_row_base=R_interconnect, 
                                            R_col_base=R_interconnect)
    
    # Apply harsh effects
    harsh_config = {
        'V_th_sigma': 0.08,
        'g_m_sigma': 0.15,
        'R_sigma': 0.15
    }
    for matrix in [triad.M33, triad.M3, triad.M8]:
        matrix.cell_bank.inject_manufacturing_variations(harsh_config)
        matrix.cell_bank.inject_thermal_drift(temp_delta_C=25.0)
        matrix.cell_bank.inject_noise(noise_sigma=0.02)
    
    # MAML optimizer (uses standard optimizer, but gets warped signals)
    maml = InvertedMAML(triad, learning_rate=0.05, num_strata=1, 
                       convergence_threshold=5.5)
    
    # Fix center weights for baseline
    triad.M3.weights.fill(2.6)
    triad.M8.weights.fill(2.6)
    
    # Generate test vectors
    x_train, y_train = create_test_vectors(num_vectors=num_samples, dimension=32, seed=seed)
    
    # Storage
    losses = []
    precisions = []
    phases = []
    ir_drop_history = []
    converged_cycle = None
    
    # ===== PHASE 0: Training OFF =====
    if verbose:
        print("\nPhase 0: Training OFF (Baseline with Warping)")
    
    for cycle in range(10):
        cycle_loss = 0.0
        cycle_ir_drops = []
        
        for x, y in zip(x_train, y_train):
            triad.refresh_cycle()
            grad_m3, grad_m8, loss = maml.compute_stratified_gradient(x, y)
            cycle_loss += loss
            
            # Capture IR drop info
            cycle_ir_drops.append({
                'M33_max_drop': triad.M33.ir_drop_history[-1]['max_row_drop_mV'],
                'M3_max_drop': triad.M3.ir_drop_history[-1]['max_row_drop_mV'],
                'M8_max_drop': triad.M8.ir_drop_history[-1]['max_row_drop_mV']
            })
        
        avg_loss = cycle_loss / len(x_train)
        precision = -np.log2(np.clip(avg_loss, 1e-6, 1.0))
        
        losses.append(avg_loss)
        precisions.append(precision)
        phases.append(0)
        ir_drop_history.append(np.mean([x['M33_max_drop'] for x in cycle_ir_drops]))
        
        if verbose and cycle % 5 == 0:
            avg_drop = np.mean([x['M33_max_drop'] for x in cycle_ir_drops])
            print(f"  Phase 0, Cycle {cycle:3d}: Loss={avg_loss:.4e}, Precision={precision:.2f} bits, "
                  f"Max IR drop={avg_drop:.1f}mV")
    
    # ===== PHASE 1: Training ON =====
    if verbose:
        print("\nPhase 1: Training ON (Learning with Warping)")
    
    for cycle in range(10, max_cycles):
        cycle_loss = 0.0
        cycle_ir_drops = []
        
        for x, y in zip(x_train, y_train):
            loss = maml.update_weights(x, y)
            cycle_loss += loss
            
            # Capture IR drops
            cycle_ir_drops.append({
                'M33_max_drop': triad.M33.ir_drop_history[-1]['max_row_drop_mV'],
                'M3_max_drop': triad.M3.ir_drop_history[-1]['max_row_drop_mV'],
                'M8_max_drop': triad.M8.ir_drop_history[-1]['max_row_drop_mV']
            })
        
        avg_loss = cycle_loss / len(x_train)
        precision = -np.log2(np.clip(avg_loss, 1e-6, 1.0))
        
        losses.append(avg_loss)
        precisions.append(precision)
        phases.append(1)
        ir_drop_history.append(np.mean([x['M33_max_drop'] for x in cycle_ir_drops]))
        
        # Check convergence
        if precision >= 5.5 and converged_cycle is None:
            converged_cycle = cycle
        
        if verbose and ((cycle - 10) % 10 == 0 or cycle == max_cycles - 1):
            avg_drop = np.mean([x['M33_max_drop'] for x in cycle_ir_drops])
            status = "✓ CONVERGED" if precision >= 5.5 else ""
            print(f"  Phase 1, Cycle {cycle:3d}: Loss={avg_loss:.4e}, Precision={precision:.2f} bits, "
                  f"Max IR drop={avg_drop:.1f}mV {status}")
    
    # ===== RESULTS =====
    if verbose:
        print("\n" + "="*80)
        print("ADVANCED TEST RESULTS (WITH RESISTIVE WARPING):")
        print("="*80)
        print(f"\nPhase 0 Baseline (Training OFF):")
        print(f"  Cycle 0: Precision={precisions[0]:.2f} bits")
        print(f"  Cycle 9: Precision={precisions[9]:.2f} bits")
        print(f"  Change:  {precisions[9] - precisions[0]:+.2f} bits")
        
        print(f"\nPhase 1 Learning (Training ON):")
        print(f"  Cycle 10: Precision={precisions[10]:.2f} bits")
        print(f"  Cycle 99: Precision={precisions[-1]:.2f} bits")
        print(f"  Improvement: +{precisions[-1] - precisions[10]:.2f} bits")
        
        print(f"\nOverall Summary:")
        print(f"  Total improvement: +{precisions[-1] - precisions[0]:.2f} bits")
        print(f"  Target precision: 5.5 bits (6-bit)")
        print(f"  Status: {'✓ CONVERGED' if precisions[-1] >= 5.5 else '✗ NOT CONVERGED'}")
        print(f"  Convergence cycle: {converged_cycle if converged_cycle else 'N/A'}")
        
        print(f"\nResistive Warping Effects:")
        avg_ir_drop_baseline = np.mean(ir_drop_history[:10])
        avg_ir_drop_learning = np.mean(ir_drop_history[10:])
        print(f"  Phase 0 avg max IR drop: {avg_ir_drop_baseline:.2f} mV")
        print(f"  Phase 1 avg max IR drop: {avg_ir_drop_learning:.2f} mV")
        print(f"  IR drop variation: {np.std(ir_drop_history):.2f} mV")
        print("="*80)
    
    # ===== BUILD RESULTS DICT =====
    return {
        'test_type': 'ADVANCED_32x32_WITH_RESISTIVE_WARPING',
        'timestamp': datetime.now().isoformat(),
        'config': {
            'matrix_size': 32,
            'max_cycles': max_cycles,
            'num_samples': num_samples,
            'seed': seed,
            'num_strata': 1,
            'learning_rate': 0.05,
            'physical_effects': 'HARSH + RESISTIVE WARPING',
            'R_interconnect_ohm': R_interconnect,
            'manufacturing_variation_percent': 15,
            'thermal_drift_celsius': 25,
            'noise_percent': 2
        },
        'phases': {
            'phase_0_cycles': 10,
            'phase_0_baseline_precision': float(precisions[0]),
            'phase_0_final_precision': float(precisions[9]),
            'phase_1_start_precision': float(precisions[10]),
            'phase_1_final_precision': float(precisions[-1]),
            'phase_1_improvement': float(precisions[-1] - precisions[10])
        },
        'convergence': {
            'final_loss': float(losses[-1]),
            'final_precision_bits': float(precisions[-1]),
            'converged': bool(precisions[-1] >= 5.5),
            'convergence_cycle': int(converged_cycle) if converged_cycle else None
        },
        'loss_history': [float(x) for x in losses],
        'precision_history': [float(x) for x in precisions],
        'phase_history': phases,
        'ir_drop_max_history': ir_drop_history
    }


def plot_advanced_test(results: dict, output_dir: str = './results_32x32/advanced'):
    """Plot advanced test with IR drop effects."""
    os.makedirs(output_dir, exist_ok=True)
    
    precisions = results['precision_history']
    ir_drops = results['ir_drop_max_history']
    cycles = list(range(len(precisions)))
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    
    # ===== TOP-LEFT: Precision with phases =====
    ax = axes[0, 0]
    ax.axvspan(0, 9.5, alpha=0.1, color='red', label='Phase 0: OFF')
    ax.axvspan(9.5, len(cycles)-1, alpha=0.1, color='green', label='Phase 1: ON')
    
    phase0_cycles = list(range(10))
    phase0_prec = precisions[:10]
    phase1_cycles = list(range(10, len(precisions)))
    phase1_prec = precisions[10:]
    
    ax.plot(phase0_cycles, phase0_prec, 'o-', linewidth=2.5, markersize=6,
            color='red', label='Phase 0 data', alpha=0.8)
    ax.plot(phase1_cycles, phase1_prec, 's-', linewidth=2.5, markersize=6,
            color='green', label='Phase 1 data', alpha=0.8)
    ax.axhline(y=5.5, color='orange', linestyle='--', linewidth=2, label='6-bit target')
    ax.set_xlabel('Cycle', fontsize=11)
    ax.set_ylabel('Precision (bits)', fontsize=11)
    ax.set_title('Precision Convergence (with IR Drop Warping)', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='lower right')
    
    # ===== TOP-RIGHT: IR drops over cycles =====
    ax = axes[0, 1]
    ax.axvspan(0, 9.5, alpha=0.1, color='red')
    ax.axvspan(9.5, len(cycles)-1, alpha=0.1, color='green')
    
    phase0_ir = ir_drops[:10]
    phase1_ir = ir_drops[10:]
    
    ax.plot(phase0_cycles, phase0_ir, 'o-', linewidth=2.5, markersize=6,
            color='purple', label='Phase 0', alpha=0.8)
    ax.plot(phase1_cycles, phase1_ir, 's-', linewidth=2.5, markersize=6,
            color='darkviolet', label='Phase 1', alpha=0.8)
    ax.set_xlabel('Cycle', fontsize=11)
    ax.set_ylabel('Max IR Drop (mV)', fontsize=11)
    ax.set_title('Resistive Warping Effects Over Time', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    # ===== BOTTOM-LEFT: Precision vs IR drops =====
    ax = axes[1, 0]
    scatter = ax.scatter(ir_drops, precisions, c=cycles, cmap='viridis', s=100, alpha=0.7, edgecolors='black', linewidth=1)
    ax.set_xlabel('Max IR Drop (mV)', fontsize=11)
    ax.set_ylabel('Precision (bits)', fontsize=11)
    ax.set_title('Precision vs IR Drop Distortion', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('Cycle', fontsize=10)
    
    # ===== BOTTOM-RIGHT: Loss (log scale) =====
    ax = axes[1, 1]
    losses = results['loss_history']
    
    ax.axvspan(0, 9.5, alpha=0.1, color='red')
    ax.axvspan(9.5, len(losses)-1, alpha=0.1, color='green')
    
    ax.semilogy(phase0_cycles, losses[:10], 'o-', linewidth=2.5, markersize=6,
                color='red', label='Phase 0', alpha=0.8)
    ax.semilogy(phase1_cycles, losses[10:], 's-', linewidth=2.5, markersize=6,
                color='green', label='Phase 1', alpha=0.8)
    ax.set_xlabel('Cycle', fontsize=11)
    ax.set_ylabel('Loss (MSE)', fontsize=11)
    ax.set_title('Loss Convergence (log scale)', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3, which='both')
    ax.legend()
    
    fig.suptitle('ADVANCED TEST: 32x32 with Resistive IR Drop Warping', 
                 fontsize=14, fontweight='bold', y=0.995)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/advanced_test_with_ir_drops.png', dpi=150, bbox_inches='tight')
    print(f"\n✓ Advanced plot saved: {output_dir}/advanced_test_with_ir_drops.png")
    plt.close()


if __name__ == '__main__':
    print("\n" + "█"*80)
    print("█ INVERTED MAML ADVANCED TEST: RESISTIVE IR DROP WARPING")
    print("█"*80)
    
    # Run advanced test
    results = run_advanced_test(max_cycles=100, num_samples=16, seed=42, 
                               R_interconnect=0.5, verbose=True)
    
    # Save results
    os.makedirs('results_32x32/advanced', exist_ok=True)
    with open('results_32x32/advanced/advanced_test_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n✓ Results saved: results_32x32/advanced/advanced_test_results.json")
    
    # Generate plot
    plot_advanced_test(results)
    
    print("\n" + "█"*80)
    print("█ TEST COMPLETE!")
    print("█"*80 + "\n")
