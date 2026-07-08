"""
TWO-STAGE MAML DEMONSTRATION FOR 16x16 MATRICES
===============================================

Adapted version of the 32x32 demo for smaller matrices.

16x16 Matrix = 256 cells per matrix × 3 = 768 total cells
(vs 32x32 = 1024 cells per matrix × 3 = 3072 total cells)

Expected behavior:
- Faster execution (4x speedup)
- More pronounced per-cell variation effects
- Individual cell effects less smoothed by averaging
- Should show similar learning patterns but with better observability
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


def run_two_stage_maml_16x16_demo():
    """
    Run complete two-stage MAML demonstration for 16x16 matrices.
    
    This is a faster, more observable version of the 32x32 demo.
    Individual cell effects are more visible with smaller total cell count.
    """
    
    print("\n" + "=" * 100)
    print("TWO-STAGE META-LEARNING (MAML) DEMONSTRATION - 16×16 MATRICES")
    print("=" * 100)
    
    # ==================== SETUP ====================
    print("\n[SETUP] Initializing two-stage MAML system (16x16)...")
    
    # Create system with 16x16 size
    triad = AtomicTriad(size=16)
    
    # Physics configuration (harsh environment)
    harsh_config = {
        'V_th_sigma': 0.15,
        'g_m_sigma': 0.20,
        'R_sigma': 0.20,
    }
    
    # Initialize two-stage trainer
    trainer = TwoStageDynamicMAML(
        triad=triad,
        learning_rate=0.50,        # Inner loop base
        inner_lr=0.05,             # Per-cycle rate
        outer_lr=0.01,             # Meta-learning rate
        num_strata=1,
        adaptive_lr=True
    )
    
    print(f"  ✓ Created TwoStageDynamicMAML (16×16)")
    print(f"  ✓ System: 16×16 matrix (256 cells per matrix × 3 = 768 cells)")
    print(f"  ✓ Physics config: V_th ±15%, g_m ±20%, R ±20%")
    print(f"  ✓ 4× FASTER than 32×32 (256 vs 1024 cells per matrix)")
    
    # Create training and test data (dimension=16 for 16x16 matrices)
    print("\n[DATA] Creating training/test vectors...")
    num_train_samples = 16
    num_test_samples = 8
    
    x_train, y_train = create_test_vectors(num_vectors=num_train_samples, dimension=16, seed=42)
    x_test, y_test = create_test_vectors(num_vectors=num_test_samples, dimension=16, seed=43)
    
    print(f"  ✓ Training data: {num_train_samples} vectors (dimension 16)")
    print(f"  ✓ Test/Operation data: {num_test_samples} vectors (dimension 16)")
    
    # ==================== STAGE 1: BASE MODEL TRAINING ====================
    print("\n" + "=" * 100)
    print("STAGE 1: BASE MODEL TRAINING WITH OUTER LOOP (16×16)")
    print("=" * 100)
    print("\nConcept:")
    print("  • Outer Loop: Create NEW physics (new manufacturing variations)")
    print("  • Inner Loops: MAML learns to adapt quickly to that physics")
    print("  • Result: Base model learns a 'good starting point' for ANY physics")
    print("  • Physics changes ABRUPTLY between outer iterations")
    
    training_log = trainer.train_outer_loop(
        x_train=x_train,
        y_train=y_train,
        outer_iterations=5,              # 5 different physics environments
        inner_cycles_per_outer=50,       # 50 adaptation cycles per physics
        harsh_config=harsh_config,
        verbose=True
    )
    
    # Print training summary
    print("\n" + "─" * 100)
    print("STAGE 1 SUMMARY (16×16)")
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
    print("STAGE 2: OPERATION MODE WITH GRADUAL PHYSICS DRIFT (16×16)")
    print("=" * 100)
    print("\nConcept:")
    print("  • Uses learned base model from Stage 1")
    print("  • No outer loop: Single deployment environment")
    print("  • Physics changes GRADUALLY (thermal drift, aging)")
    print("  • Inner loop continuously adapts weights")
    print("  • Result: Precision maintained despite slow degradation")
    
    operation_log = trainer.run_operation_mode(
        x_test=x_test,
        y_test=y_test,
        operation_cycles=150,            # 150 cycles of gradual drift
        drift_speed=0.5,                 # 0.5 = maximum drift by end
        verbose=True
    )
    
    # Print operation summary
    print("\n" + "─" * 100)
    print("STAGE 2 SUMMARY (16×16)")
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
    print("GENERATING PLOTS (16×16)")
    print("=" * 100)
    
    output_dir = Path("results_32x32/two_stage_maml_16x16")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("\n[PLOT 1] Base Model Training (16×16)...")
    fig1 = plot_base_model_training(
        training_log,
        output_path=str(output_dir / "01_base_model_training_16x16.png")
    )
    
    print("\n[PLOT 2] Operation Mode (16×16)...")
    fig2 = plot_operation_mode(
        operation_log,
        output_path=str(output_dir / "02_operation_mode_16x16.png")
    )
    
    print("\n[PLOT 3] Stage 1 vs Stage 2 Comparison (16×16)...")
    fig3 = plot_comparison_training_vs_operation(
        training_log,
        operation_log,
        output_path=str(output_dir / "03_stage1_vs_stage2_comparison_16x16.png")
    )
    
    # ==================== SAVE RESULTS ====================
    print("\n" + "=" * 100)
    print("SAVING RESULTS (16×16)")
    print("=" * 100)
    
    results = {
        'matrix_size': '16x16',
        'total_cells': 768,
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
    
    results_path = output_dir / "two_stage_maml_16x16_results.json"
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"  ✓ Results saved: {results_path}")
    
    # ==================== FINAL SUMMARY ====================
    print("\n" + "=" * 100)
    print("TWO-STAGE MAML DEMONSTRATION COMPLETE (16×16)")
    print("=" * 100)
    
    print("\n📊 STAGE 1: Base Model Training")
    print(f"  ✓ Matrix size: 16×16 (768 cells total)")
    print(f"  ✓ Outer iterations (physics changes): {len(training_log['inner_cycle_stats'])}")
    print(f"  ✓ Total training cycles: {sum(len(s['precisions']) for s in training_log['inner_cycle_stats'])}")
    print(f"  ✓ Base model quality: {initial_base_precision:.2f} → {final_base_precision:.2f} bits")
    print(f"  ✓ Key insight: Meta-learned base model ADAPTS QUICKLY to new physics")
    
    print("\n📈 STAGE 2: Operation Mode")
    print(f"  ✓ Operation cycles: {len(operation_log['cycles'])}")
    print(f"  ✓ Physics drift: 0.0 → {operation_log['drift_level'][-1]:.2f}")
    print(f"  ✓ Precision: {initial_op_precision:.2f} bits (maintained {final_op_precision - initial_op_precision:+.2f})")
    print(f"  ✓ Key insight: Inner loop CONTINUOUSLY ADAPTS to slow physics drift")
    
    print("\n⚡ PERFORMANCE")
    print(f"  ✓ 16×16 is ~4× FASTER than 32×32")
    print(f"  ✓ Cells per matrix: 256 vs 1024")
    print(f"  ✓ Averaging effect: LESS (per-cell effects MORE visible)")
    print(f"  ✓ Better for observing individual cell behavior")
    
    print("\n🎯 OVERALL PATENT CONCEPT")
    print("  ✓ Stage 1: Learn base model that can adapt to ANY physics variation")
    print("  ✓ Stage 2: Deploy base model with online adaptation to manufacturing drift")
    print("  ✓ Result: Analog hardware maintains precision despite environmental changes")
    print("  ✓ Advantage: Generalization + Real-time compensation")
    
    print("\n📁 Output files:")
    print(f"  ✓ {output_dir / '01_base_model_training_16x16.png'}")
    print(f"  ✓ {output_dir / '02_operation_mode_16x16.png'}")
    print(f"  ✓ {output_dir / '03_stage1_vs_stage2_comparison_16x16.png'}")
    print(f"  ✓ {results_path}")
    
    # Show plots
    plt.show(block=False)
    
    return trainer, training_log, operation_log, results


if __name__ == "__main__":
    trainer, training_log, operation_log, results = run_two_stage_maml_16x16_demo()
    
    print("\n✅ Execution complete! Check the plots and results above.")
