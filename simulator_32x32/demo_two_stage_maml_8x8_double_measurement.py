"""
TWO-STAGE MAML WITH DOUBLE MEASUREMENT WINDOW (8×8)
====================================================

Enhanced version that measures at TWO different time points within the cycle:
- Stratum 1 (Peak): Early measurement at high signal (t=0.5ms)
- Stratum 2 (Early): Mid measurement before heavy discharge (t=3.5ms)

By averaging gradients across two measurement windows, we get:
✓ Better SNR (signal-to-noise ratio)
✓ More robust learning (two independent measurements)
✓ Smoother convergence (averaging reduces noise)
✓ Better generalization (captures different discharge phases)

Comparison:
- Single stratum (1): Only one time point, clearest signal
- Double stratum (2): Two time points, averaged, more robust
"""

import os
import sys
import json
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).parent))

from matrix_core import AtomicTriad
from maml_optimizer import InvertedMAML, create_test_vectors
from maml_two_stage_trainer import TwoStageDynamicMAML
from maml_two_stage_plots import (
    plot_base_model_training,
    plot_operation_mode,
    plot_comparison_training_vs_operation
)


def run_two_stage_maml_8x8_double_measurement_demo():
    """
    Run two-stage MAML for 8×8 with DOUBLE MEASUREMENT (2 strata).
    
    Measures at two different time points during discharge cycle:
    - Early measurement (peak signal, t=0.5ms)
    - Mid measurement (post-initial discharge, t=3.5ms)
    
    Gradients averaged across both measurements.
    """
    
    print("\n" + "=" * 100)
    print("TWO-STAGE META-LEARNING (MAML) - 8×8 WITH DOUBLE MEASUREMENT")
    print("=" * 100)
    print("\nMeasurement Strategy: TWO STRATA (Double Window)")
    print("  • Stratum 1 (Peak): t=0.5ms  (high SNR, before discharge)")
    print("  • Stratum 2 (Early): t=3.5ms (signal still good, early discharge)")
    print("  • Averaging: ∇L = (1/2) × (∇L₁ + ∇L₂)")
    print("  • Benefit: More robust learning, better generalization")
    
    # ==================== SETUP ====================
    print("\n[SETUP] Initializing two-stage MAML system (8×8 with double measurement)...")
    
    # Create system with 8×8 size
    triad = AtomicTriad(size=8)
    
    # Physics configuration (harsh environment)
    harsh_config = {
        'V_th_sigma': 0.15,
        'g_m_sigma': 0.20,
        'R_sigma': 0.20,
    }
    
    # Initialize two-stage trainer
    # KEY: Set num_strata=2 for double measurement
    trainer = TwoStageDynamicMAML(
        triad=triad,
        learning_rate=0.50,
        inner_lr=0.05,
        outer_lr=0.01,
        num_strata=2,              # ← CHANGED: Use 2 strata instead of 1
        adaptive_lr=True
    )
    
    print(f"  ✓ Created TwoStageDynamicMAML (8×8)")
    print(f"  ✓ System: 8×8 matrix (64 cells per matrix × 3 = 192 cells)")
    print(f"  ✓ Measurement strategy: DOUBLE WINDOW (2 strata)")
    print(f"  ✓ Physics config: V_th ±15%, g_m ±20%, R ±20%")
    
    # Create training and test data
    print("\n[DATA] Creating training/test vectors...")
    num_train_samples = 8
    num_test_samples = 4
    
    x_train, y_train = create_test_vectors(num_vectors=num_train_samples, dimension=8, seed=42)
    x_test, y_test = create_test_vectors(num_vectors=num_test_samples, dimension=8, seed=43)
    
    print(f"  ✓ Training data: {num_train_samples} vectors (dimension 8)")
    print(f"  ✓ Test/Operation data: {num_test_samples} vectors (dimension 8)")
    
    # ==================== STAGE 1: BASE MODEL TRAINING ====================
    print("\n" + "=" * 100)
    print("STAGE 1: BASE MODEL TRAINING WITH OUTER LOOP (8×8, Double Measurement)")
    print("=" * 100)
    
    training_log = trainer.train_outer_loop(
        x_train=x_train,
        y_train=y_train,
        outer_iterations=5,
        inner_cycles_per_outer=50,
        harsh_config=harsh_config,
        verbose=True
    )
    
    # Print training summary
    print("\n" + "─" * 100)
    print("STAGE 1 SUMMARY (8×8, Double Measurement)")
    print("─" * 100)
    final_base_precision = training_log['base_model_precision'][-1]
    initial_base_precision = training_log['base_model_precision'][0]
    print(f"  Base model quality improved: {initial_base_precision:.2f} → {final_base_precision:.2f} bits")
    print(f"  Improvement: +{final_base_precision - initial_base_precision:.2f} bits")
    
    for i, stats in enumerate(training_log['inner_cycle_stats']):
        print(f"  Outer Iteration {i+1}: {stats['baseline']:.2f} → {stats['final']:.2f} bits "
              f"(+{stats['improvement']:.2f})")
    
    # ==================== STAGE 2: OPERATION MODE ====================
    print("\n" + "=" * 100)
    print("STAGE 2: OPERATION MODE WITH GRADUAL PHYSICS DRIFT (8×8, Double Measurement)")
    print("=" * 100)
    
    operation_log = trainer.run_operation_mode(
        x_test=x_test,
        y_test=y_test,
        operation_cycles=150,
        drift_speed=0.5,
        verbose=True
    )
    
    # Print operation summary
    print("\n" + "─" * 100)
    print("STAGE 2 SUMMARY (8×8, Double Measurement)")
    print("─" * 100)
    initial_op_precision = operation_log['precisions'][0]
    final_op_precision = operation_log['precisions'][-1]
    max_op_precision = max(operation_log['precisions'])
    
    print(f"  Initial operation precision: {initial_op_precision:.2f} bits")
    print(f"  Peak precision during operation: {max_op_precision:.2f} bits")
    print(f"  Final precision after drift: {final_op_precision:.2f} bits")
    print(f"  Precision retention: {final_op_precision - initial_op_precision:+.2f} bits")
    print(f"  Total drift experienced: {operation_log['drift_level'][-1]:.2f}")
    
    # ==================== PLOTTING ====================
    print("\n" + "=" * 100)
    print("GENERATING PLOTS (8×8, Double Measurement)")
    print("=" * 100)
    
    output_dir = Path("results_32x32/two_stage_maml_8x8_double_measurement")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("\n[PLOT 1] Base Model Training (8×8, Double Measurement)...")
    fig1 = plot_base_model_training(
        training_log,
        output_path=str(output_dir / "01_base_model_training_8x8_double.png")
    )
    
    print("\n[PLOT 2] Operation Mode (8×8, Double Measurement)...")
    fig2 = plot_operation_mode(
        operation_log,
        output_path=str(output_dir / "02_operation_mode_8x8_double.png")
    )
    
    print("\n[PLOT 3] Stage 1 vs Stage 2 Comparison (8×8, Double Measurement)...")
    fig3 = plot_comparison_training_vs_operation(
        training_log,
        operation_log,
        output_path=str(output_dir / "03_stage1_vs_stage2_comparison_8x8_double.png")
    )
    
    # ==================== SAVE RESULTS ====================
    print("\n" + "=" * 100)
    print("SAVING RESULTS (8×8, Double Measurement)")
    print("=" * 100)
    
    results = {
        'matrix_size': '8x8',
        'total_cells': 192,
        'measurement_strategy': 'double_window',
        'num_strata': 2,
        'measurement_times_ms': [0.5, 3.5],
        'description': 'Two strata: Peak (t=0.5ms) and Early (t=3.5ms)',
        'stage1_training': {
            'outer_iterations': len(training_log['inner_cycle_stats']),
            'initial_base_precision': float(initial_base_precision),
            'final_base_precision': float(final_base_precision),
            'base_improvement': float(final_base_precision - initial_base_precision),
            'per_iteration': [
                {
                    'iteration': i + 1,
                    'baseline': float(s['baseline']),
                    'final': float(s['final']),
                    'improvement': float(s['improvement']),
                    'avg_loss': float(np.mean(s['losses']))
                }
                for i, s in enumerate(training_log['inner_cycle_stats'])
            ]
        },
        'stage2_operation': {
            'operation_cycles': len(operation_log['cycles']),
            'initial_precision': float(initial_op_precision),
            'final_precision': float(final_op_precision),
            'max_precision': float(max_op_precision),
            'precision_retention': float(final_op_precision - initial_op_precision),
            'total_drift': float(operation_log['drift_level'][-1]),
            'avg_weight_change': float(np.mean(operation_log['weight_changes'])),
            'avg_loss': float(np.mean(operation_log['losses']))
        }
    }
    
    results_path = output_dir / "two_stage_maml_8x8_double_measurement_results.json"
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"  ✓ Results saved: {results_path}")
    
    # ==================== FINAL SUMMARY ====================
    print("\n" + "=" * 100)
    print("TWO-STAGE MAML DEMONSTRATION COMPLETE (8×8, Double Measurement)")
    print("=" * 100)
    
    print("\n📊 STAGE 1: Base Model Training")
    print(f"  ✓ Matrix size: 8×8 (192 cells total)")
    print(f"  ✓ Measurement: DOUBLE WINDOW (2 strata)")
    print(f"  ✓ Outer iterations (physics changes): {len(training_log['inner_cycle_stats'])}")
    print(f"  ✓ Total training cycles: {sum(len(s['precisions']) for s in training_log['inner_cycle_stats'])}")
    print(f"  ✓ Base model quality: {initial_base_precision:.2f} → {final_base_precision:.2f} bits")
    print(f"  ✓ Improvement: +{final_base_precision - initial_base_precision:.2f} bits")
    
    print("\n📈 STAGE 2: Operation Mode")
    print(f"  ✓ Operation cycles: {len(operation_log['cycles'])}")
    print(f"  ✓ Physics drift: 0.0 → {operation_log['drift_level'][-1]:.2f}")
    print(f"  ✓ Precision: {initial_op_precision:.2f} → {final_op_precision:.2f} bits")
    print(f"  ✓ Precision gain: +{final_op_precision - initial_op_precision:.2f} bits")
    
    print("\n🎯 Measurement Strategy Benefits")
    print("  ✓ Double window captures two discharge phases")
    print("  ✓ Averaging reduces measurement noise")
    print("  ✓ More robust gradients")
    print("  ✓ Better generalization across time")
    
    print("\n📁 Output files:")
    print(f"  ✓ {output_dir / '01_base_model_training_8x8_double.png'}")
    print(f"  ✓ {output_dir / '02_operation_mode_8x8_double.png'}")
    print(f"  ✓ {output_dir / '03_stage1_vs_stage2_comparison_8x8_double.png'}")
    print(f"  ✓ {results_path}")
    
    # Show plots
    plt.show(block=False)
    
    return trainer, training_log, operation_log, results


if __name__ == "__main__":
    trainer, training_log, operation_log, results = run_two_stage_maml_8x8_double_measurement_demo()
    
    print("\n✅ Execution complete! Check the plots and results above.")
    print("\nComparison:")
    print("  Single measurement (1 stratum):  demo_two_stage_maml_8x8.py")
    print("  Double measurement (2 strata):   demo_two_stage_maml_8x8_double_measurement.py")
