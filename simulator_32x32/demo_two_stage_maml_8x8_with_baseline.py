"""
TWO-STAGE MAML 8×8 WITH BASELINE MEASUREMENT (No Compensation)
==============================================================

Enhanced version showing BASELINE PRECISION before compensation starts.

Measurement Phase Structure:
  Phase 0: BASELINE (10 cycles, NO compensation)
           - M3 and M8 set to center/identity values
           - No weight updates
           - Shows raw hardware performance
  
  Phase 1: TRAINING (MAML enabled)
           - Weights updated normally
           - Shows improvement over baseline
           - Demonstrates compensation effect

Perfect for comparing:
- Without compensation (baseline)
- With compensation (trained)
- To quantify the improvement clearly
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


def run_two_stage_maml_8x8_with_baseline():
    """
    Run two-stage MAML for 8×8 with baseline measurement phase.
    
    Includes:
    - 10 cycles with NO compensation (baseline measurement)
    - Followed by normal MAML training
    - Clear visualization of compensation effect
    """
    
    print("\n" + "=" * 100)
    print("TWO-STAGE META-LEARNING (MAML) - 8×8 WITH BASELINE MEASUREMENT")
    print("=" * 100)
    print("\nMeasurement Strategy:")
    print("  Phase 0: BASELINE (cycles 0-9)")
    print("    • Compensation OFF (M3, M8 = center values)")
    print("    • No weight updates")
    print("    • Shows raw hardware performance without compensation")
    print("\n  Phase 1: TRAINING (cycles 10+)")
    print("    • MAML enabled")
    print("    • Weights updated normally")
    print("    • Shows improvement over baseline")
    
    # ==================== SETUP ====================
    print("\n[SETUP] Initializing two-stage MAML system (8×8 with baseline)...")
    
    # Create system with 8×8 size
    triad = AtomicTriad(size=8)
    
    # Physics configuration (harsh environment)
    harsh_config = {
        'V_th_sigma': 0.15,
        'g_m_sigma': 0.20,
        'R_sigma': 0.20,
    }
    
    # Initialize two-stage trainer
    trainer = TwoStageDynamicMAML(
        triad=triad,
        learning_rate=0.50,
        inner_lr=0.05,
        outer_lr=0.01,
        num_strata=1,
        adaptive_lr=True
    )
    
    print(f"  ✓ Created TwoStageDynamicMAML (8×8)")
    print(f"  ✓ System: 8×8 matrix (64 cells per matrix × 3 = 192 cells)")
    print(f"  ✓ Physics config: V_th ±15%, g_m ±20%, R ±20%")
    
    # Create training and test data
    print("\n[DATA] Creating training/test vectors...")
    num_train_samples = 8
    num_test_samples = 4
    
    x_train, y_train = create_test_vectors(num_vectors=num_train_samples, dimension=8, seed=42)
    x_test, y_test = create_test_vectors(num_vectors=num_test_samples, dimension=8, seed=43)
    
    print(f"  ✓ Training data: {num_train_samples} vectors (dimension 8)")
    print(f"  ✓ Test/Operation data: {num_test_samples} vectors (dimension 8)")
    
    # ==================== STAGE 1: BASE MODEL TRAINING WITH BASELINE ====================
    print("\n" + "=" * 100)
    print("STAGE 1: BASE MODEL TRAINING WITH BASELINE MEASUREMENT")
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
    print("STAGE 1 SUMMARY (8×8 with Baseline)")
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
    print("STAGE 2: OPERATION MODE WITH GRADUAL PHYSICS DRIFT")
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
    print("STAGE 2 SUMMARY (8×8 with Baseline)")
    print("─" * 100)
    initial_op_precision = operation_log['precisions'][0]
    final_op_precision = operation_log['precisions'][-1]
    max_op_precision = max(operation_log['precisions'])
    
    print(f"  Initial operation precision: {initial_op_precision:.2f} bits")
    print(f"  Peak precision during operation: {max_op_precision:.2f} bits")
    print(f"  Final precision after drift: {final_op_precision:.2f} bits")
    print(f"  Precision retention: {final_op_precision - initial_op_precision:+.2f} bits")
    
    # ==================== BASELINE MEASUREMENT ====================
    print("\n" + "=" * 100)
    print("BASELINE MEASUREMENT (Compensation OFF)")
    print("=" * 100)
    print("\nMeasuring raw hardware performance without any compensation...")
    
    # Reset to baseline (no compensation)
    baseline_M3 = np.eye(8) * 0.5  # Center value (identity * 0.5)
    baseline_M8 = np.eye(8) * 0.5  # Center value (identity * 0.5)
    
    trainer.triad.set_correction_weights(baseline_M3, baseline_M8)
    
    baseline_precisions = []
    baseline_losses = []
    
    for cycle in range(10):
        cycle_loss = 0.0
        
        # Measure only (don't update weights)
        for x, y in zip(x_train, y_train):
            trainer.triad.refresh_cycle()
            output, _ = trainer.triad.forward(x, t_snapshot_ms=0.5)
            error = np.abs(output - y)
            loss = np.mean(error ** 2)
            cycle_loss += loss
        
        avg_loss = cycle_loss / len(x_train)
        precision = -np.log2(np.clip(np.mean([np.abs(o - y).mean() for o, y in zip(
            [trainer.triad.forward(x, t_snapshot_ms=0.5)[0] for x in x_train],
            y_train
        )]), 1e-6, 1.0))
        
        baseline_precisions.append(precision)
        baseline_losses.append(avg_loss)
        
        if cycle % 2 == 0 or cycle == 9:
            print(f"  Baseline Cycle {cycle}: Loss={avg_loss:.2e}, Precision={precision:.2f} bits")
    
    baseline_avg_precision = np.mean(baseline_precisions)
    print(f"\n  ➜ Average baseline precision (NO compensation): {baseline_avg_precision:.2f} bits")
    print(f"  ➜ First iteration precision (with compensation): {training_log['inner_cycle_stats'][0]['final']:.2f} bits")
    print(f"  ➜ Improvement from baseline: +{training_log['inner_cycle_stats'][0]['final'] - baseline_avg_precision:.2f} bits")
    
    # ==================== PLOTTING ====================
    print("\n" + "=" * 100)
    print("GENERATING PLOTS (8×8 with Baseline)")
    print("=" * 100)
    
    output_dir = Path("results_32x32/two_stage_maml_8x8_with_baseline")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("\n[PLOT 1] Base Model Training (8×8 with Baseline)...")
    fig1 = plot_base_model_training(
        training_log,
        output_path=str(output_dir / "01_base_model_training_8x8_baseline.png")
    )
    
    print("\n[PLOT 2] Operation Mode (8×8 with Baseline)...")
    fig2 = plot_operation_mode(
        operation_log,
        output_path=str(output_dir / "02_operation_mode_8x8_baseline.png")
    )
    
    print("\n[PLOT 3] Stage 1 vs Stage 2 Comparison (8×8 with Baseline)...")
    fig3 = plot_comparison_training_vs_operation(
        training_log,
        operation_log,
        output_path=str(output_dir / "03_stage1_vs_stage2_comparison_8x8_baseline.png")
    )
    
    # ===== PLOT 4: BASELINE VISUALIZATION =====
    print("\n[PLOT 4] Baseline Measurement vs Trained (8×8)...")
    fig4, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Left: Baseline vs First Iteration
    ax = axes[0]
    baseline_cycles = list(range(10))
    first_iter_cycles = list(range(len(training_log['inner_cycle_stats'][0]['precisions'])))
    
    ax.plot(baseline_cycles, baseline_precisions, 'r-o', linewidth=2.5, markersize=8, 
           label=f'Baseline (No Compensation)', alpha=0.8)
    ax.axhline(baseline_avg_precision, color='red', linestyle='--', linewidth=2, alpha=0.6,
              label=f'Baseline Average: {baseline_avg_precision:.2f} bits')
    
    ax.plot(first_iter_cycles, training_log['inner_cycle_stats'][0]['precisions'], 'g-s', 
           linewidth=2.5, markersize=8, label='First Iteration (With Compensation)', alpha=0.8)
    
    ax.fill_between([-1, 55], baseline_avg_precision, 
                   training_log['inner_cycle_stats'][0]['final'], 
                   alpha=0.2, color='green', label='Improvement Area')
    
    ax.set_xlabel('Cycle Number', fontsize=12, fontweight='bold')
    ax.set_ylabel('Precision (bits)', fontsize=12, fontweight='bold')
    ax.set_title('Baseline (No Compensation) vs First Training Iteration\n(8×8 Single Window)',
                fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=10)
    ax.set_xlim(-2, 55)
    
    # Right: Improvement Summary
    ax = axes[1]
    categories = ['Baseline\n(No Comp)', 'After First\nIteration', 'After All\n5 Iterations', 'After Op\nMode']
    values = [
        baseline_avg_precision,
        training_log['inner_cycle_stats'][0]['final'],
        training_log['base_model_precision'][-1],
        operation_log['precisions'][-1]
    ]
    colors = ['red', 'orange', 'blue', 'darkgreen']
    
    bars = ax.bar(categories, values, color=colors, alpha=0.7, edgecolor='black', linewidth=2)
    
    # Add value labels on bars
    for i, (bar, val) in enumerate(zip(bars, values)):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
               f'{val:.2f}', ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    # Add improvement annotations
    ax.annotate('', xy=(0, baseline_avg_precision), xytext=(1, training_log['inner_cycle_stats'][0]['final']),
               arrowprops=dict(arrowstyle='<->', color='green', lw=2))
    ax.text(0.5, (baseline_avg_precision + training_log['inner_cycle_stats'][0]['final'])/2 + 0.15,
           f'+{training_log["inner_cycle_stats"][0]["final"] - baseline_avg_precision:.2f}',
           ha='center', fontsize=11, fontweight='bold', color='green',
           bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8))
    
    ax.set_ylabel('Precision (bits)', fontsize=12, fontweight='bold')
    ax.set_title('Precision Progression: Baseline → Training → Operation',
                fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_ylim(0, max(values) * 1.2)
    
    plt.tight_layout()
    plt.savefig(str(output_dir / "04_baseline_vs_trained_8x8.png"), dpi=150, bbox_inches='tight')
    print("✓ Saved: results_32x32/two_stage_maml_8x8_with_baseline/04_baseline_vs_trained_8x8.png")
    
    # ==================== SAVE RESULTS ====================
    print("\n" + "=" * 100)
    print("SAVING RESULTS (8×8 with Baseline)")
    print("=" * 100)
    
    results = {
        'matrix_size': '8x8',
        'total_cells': 192,
        'baseline_measurement': {
            'cycles': 10,
            'compensation_state': 'OFF',
            'precision_per_cycle': [float(p) for p in baseline_precisions],
            'average_precision': float(baseline_avg_precision),
            'loss_per_cycle': [float(l) for l in baseline_losses],
        },
        'stage1_training': {
            'outer_iterations': len(training_log['inner_cycle_stats']),
            'initial_base_precision': float(initial_base_precision),
            'final_base_precision': float(final_base_precision),
            'base_improvement': float(final_base_precision - initial_base_precision),
            'improvement_vs_baseline': float(training_log['inner_cycle_stats'][0]['final'] - baseline_avg_precision),
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
    
    results_path = output_dir / "two_stage_maml_8x8_with_baseline_results.json"
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"  ✓ Results saved: {results_path}")
    
    # ==================== FINAL SUMMARY ====================
    print("\n" + "=" * 100)
    print("TWO-STAGE MAML DEMONSTRATION COMPLETE (8×8 with Baseline)")
    print("=" * 100)
    
    print("\n📊 BASELINE MEASUREMENT (Compensation OFF)")
    print(f"  ✓ Cycles: 10")
    print(f"  ✓ Average precision (no compensation): {baseline_avg_precision:.2f} bits")
    print(f"  ✓ Range: {min(baseline_precisions):.2f} - {max(baseline_precisions):.2f} bits")
    
    print("\n📊 STAGE 1: Base Model Training")
    print(f"  ✓ Matrix size: 8×8 (192 cells total)")
    print(f"  ✓ Outer iterations (physics changes): {len(training_log['inner_cycle_stats'])}")
    print(f"  ✓ Total training cycles: {sum(len(s['precisions']) for s in training_log['inner_cycle_stats'])}")
    print(f"  ✓ Base model quality: {initial_base_precision:.2f} → {final_base_precision:.2f} bits")
    print(f"  ✓ Improvement vs baseline: +{training_log['inner_cycle_stats'][0]['final'] - baseline_avg_precision:.2f} bits")
    
    print("\n📈 STAGE 2: Operation Mode")
    print(f"  ✓ Operation cycles: {len(operation_log['cycles'])}")
    print(f"  ✓ Physics drift: 0.0 → {operation_log['drift_level'][-1]:.2f}")
    print(f"  ✓ Precision: {initial_op_precision:.2f} → {final_op_precision:.2f} bits")
    print(f"  ✓ Precision gain: +{final_op_precision - initial_op_precision:.2f} bits")
    
    print("\n🎯 Key Comparisons")
    print(f"  ✓ Baseline (no comp):           {baseline_avg_precision:.2f} bits")
    print(f"  ✓ First iteration (trained):    {training_log['inner_cycle_stats'][0]['final']:.2f} bits")
    print(f"  ✓ After 5 outer iterations:     {training_log['base_model_precision'][-1]:.2f} bits")
    print(f"  ✓ After operation mode:         {operation_log['precisions'][-1]:.2f} bits")
    print(f"  ✓ Total improvement:            +{operation_log['precisions'][-1] - baseline_avg_precision:.2f} bits")
    
    print("\n📁 Output files:")
    print(f"  ✓ {output_dir / '01_base_model_training_8x8_baseline.png'}")
    print(f"  ✓ {output_dir / '02_operation_mode_8x8_baseline.png'}")
    print(f"  ✓ {output_dir / '03_stage1_vs_stage2_comparison_8x8_baseline.png'}")
    print(f"  ✓ {output_dir / '04_baseline_vs_trained_8x8.png'} ← NEW: Baseline comparison")
    print(f"  ✓ {results_path}")
    
    # Show plots
    plt.show(block=False)
    
    return trainer, training_log, operation_log, baseline_precisions, results


if __name__ == "__main__":
    trainer, training_log, operation_log, baseline_precisions, results = run_two_stage_maml_8x8_with_baseline()
    
    print("\n✅ Execution complete! Check the plots and results above.")
    print("\nKey insight from baseline measurement:")
    print(f"  • Without any compensation: ~{np.mean(baseline_precisions):.2f} bits")
    print(f"  • With trained compensation: ~{training_log['inner_cycle_stats'][0]['final']:.2f} bits")
    print(f"  • Improvement: ~{training_log['inner_cycle_stats'][0]['final'] - np.mean(baseline_precisions):.2f} bits")
