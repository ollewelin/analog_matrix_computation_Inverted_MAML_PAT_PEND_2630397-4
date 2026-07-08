"""
VISUALIZATION: Two-Stage MAML Training & Operation Mode Plots
==============================================================

Plots:
1. Base Model Training: Shows outer loop iterations with abrupt physics changes
   - Precision trajectory for each outer iteration
   - How base model improves with each iteration
   - Quick adaptation within each inner loop
   
2. Operation Mode: Shows inner loop only with gradual physics drift
   - Precision stability during slow drift
   - Weight adaptation activity
   - Comparison: precision with/without inner loop adaptation
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict, List


def plot_base_model_training(training_log: Dict, output_path: str = None) -> plt.Figure:
    """
    Plot Stage 1: Base Model Training with Outer Loop.
    
    Shows:
    - Each outer iteration as a colored block
    - Precision rising within each inner loop
    - Abrupt physics changes between iterations (vertical lines)
    
    Args:
        training_log: Output from TwoStageDynamicMAML.train_outer_loop()
        output_path: Path to save figure
    
    Returns:
        Figure object
    """
    inner_stats = training_log['inner_cycle_stats']
    physics_change_cycles = training_log['physics_change_cycles']
    
    # Flatten all cycles and precisions
    all_cycles = []
    all_precisions = []
    outer_boundaries = []
    colors = []
    color_map = plt.cm.viridis(np.linspace(0, 1, len(inner_stats)))
    
    global_cycle = 0
    for outer_idx, stats in enumerate(inner_stats):
        precisions = stats['precisions']
        baseline = stats['baseline']
        
        # Mark where this outer iteration starts (new physics)
        outer_boundaries.append(global_cycle)
        
        for rel_cycle, precision in enumerate(precisions):
            all_cycles.append(global_cycle)
            all_precisions.append(precision)
            colors.append(color_map[outer_idx])
            global_cycle += 1
    
    # Create figure with subplots
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # ===== PLOT 1: Main trajectory with outer loop coloring =====
    ax = axes[0, 0]
    scatter = ax.scatter(all_cycles, all_precisions, c=list(range(len(all_cycles))),
                        cmap='viridis', s=50, alpha=0.7, edgecolors='black', linewidth=0.5)
    
    # Add vertical lines for outer loop boundaries
    for boundary in outer_boundaries[1:]:  # Skip first
        ax.axvline(boundary, color='red', linestyle='--', linewidth=2, alpha=0.7, label='Abrupt Physics Change')
    
    ax.set_xlabel('Training Cycle', fontsize=12, fontweight='bold')
    ax.set_ylabel('Precision (bits)', fontsize=12, fontweight='bold')
    ax.set_title('Stage 1: Base Model Training\n(Outer Loop: Abrupt Physics Changes)', 
                fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=10)
    
    # ===== PLOT 2: Per-outer-iteration summary =====
    ax = axes[0, 1]
    outer_indices = list(range(len(inner_stats)))
    baselines = [s['baseline'] for s in inner_stats]
    finals = [s['final'] for s in inner_stats]
    improvements = [s['improvement'] for s in inner_stats]
    
    x_pos = np.arange(len(outer_indices))
    width = 0.35
    
    ax.bar(x_pos - width/2, baselines, width, label='Before Adaptation', alpha=0.8, color='steelblue')
    ax.bar(x_pos + width/2, finals, width, label='After Adaptation', alpha=0.8, color='darkorange')
    
    # Add improvement labels
    for i, improvement in enumerate(improvements):
        ax.text(i, finals[i] + 0.1, f'+{improvement:.2f}b', ha='center', fontsize=10, fontweight='bold')
    
    ax.set_xlabel('Outer Loop Iteration', fontsize=12, fontweight='bold')
    ax.set_ylabel('Precision (bits)', fontsize=12, fontweight='bold')
    ax.set_title('Per-Iteration Improvement\n(Physics Changes Each Iteration)', 
                fontsize=13, fontweight='bold')
    ax.set_xticks(x_pos)
    ax.set_xticklabels([f'Iter {i+1}' for i in outer_indices])
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')
    
    # ===== PLOT 3: Loss trajectories per outer iteration =====
    ax = axes[1, 0]
    for outer_idx, stats in enumerate(inner_stats):
        losses = stats['losses']
        ax.plot(losses, label=f'Outer Iter {outer_idx+1}', linewidth=2, alpha=0.8, marker='o', markersize=3)
    
    ax.set_xlabel('Inner Loop Cycle (within iteration)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Loss (MSE)', fontsize=12, fontweight='bold')
    ax.set_title('Loss Convergence Per Outer Iteration\n(Fast Adaptation Within Each Physics Space)',
                fontsize=13, fontweight='bold')
    ax.set_yscale('log')
    ax.legend(fontsize=9, loc='best')
    ax.grid(True, alpha=0.3, which='both')
    
    # ===== PLOT 4: Base model quality trend =====
    ax = axes[1, 1]
    base_precisions = training_log['base_model_precision']
    
    ax.plot(outer_indices, base_precisions, marker='o', markersize=10, linewidth=3,
           color='darkgreen', label='Meta-Learned Base Model Quality', alpha=0.8)
    ax.fill_between(outer_indices, base_precisions, alpha=0.3, color='darkgreen')
    
    # Add value labels
    for i, (x, y) in enumerate(zip(outer_indices, base_precisions)):
        ax.text(x, y + 0.05, f'{y:.2f}', ha='center', fontsize=10, fontweight='bold')
    
    ax.set_xlabel('Outer Loop Iteration', fontsize=12, fontweight='bold')
    ax.set_ylabel('Base Model Precision (bits)', fontsize=12, fontweight='bold')
    ax.set_title('Base Model Learning Progress\n(Meta-Learned Starting Point Improves)',
                fontsize=13, fontweight='bold')
    ax.set_xticks(outer_indices)
    ax.set_xticklabels([f'Iter {i+1}' for i in outer_indices])
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=10)
    
    plt.tight_layout()
    
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"✓ Saved: {output_path}")
    
    return fig


def plot_operation_mode(operation_log: Dict, output_path: str = None) -> plt.Figure:
    """
    Plot Stage 2: Operation Mode with Gradual Physics Drift.
    
    Shows:
    - Precision stability as physics drifts
    - Weight adaptation activity
    - Drift level over time
    
    Args:
        operation_log: Output from TwoStageDynamicMAML.run_operation_mode()
        output_path: Path to save figure
    
    Returns:
        Figure object
    """
    cycles = operation_log['cycles']
    precisions = operation_log['precisions']
    losses = operation_log['losses']
    drift_levels = operation_log['drift_level']
    weight_changes = operation_log['weight_changes']
    
    # Create figure with subplots
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # ===== PLOT 1: Precision trajectory with drift overlay =====
    ax1 = axes[0, 0]
    ax1_twin = ax1.twinx()
    
    line1 = ax1.plot(cycles, precisions, marker='o', markersize=4, linewidth=2.5,
                    color='darkblue', label='Precision', alpha=0.8)
    ax1.fill_between(cycles, precisions, alpha=0.2, color='darkblue')
    
    line2 = ax1_twin.fill_between(cycles, drift_levels, alpha=0.3, color='red', label='Physics Drift')
    ax1_twin.plot(cycles, drift_levels, color='darkred', linewidth=2, linestyle='--', alpha=0.8)
    
    ax1.set_xlabel('Operation Cycle', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Precision (bits)', fontsize=12, fontweight='bold', color='darkblue')
    ax1_twin.set_ylabel('Physics Drift Level', fontsize=12, fontweight='bold', color='darkred')
    ax1.set_title('Stage 2: Operation Mode\n(Inner Loop Only + Gradual Physics Drift)',
                 fontsize=13, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.tick_params(axis='y', labelcolor='darkblue')
    ax1_twin.tick_params(axis='y', labelcolor='darkred')
    
    # Combined legend
    lines = line1 + [line2]
    labels = ['Precision', 'Drift Level']
    ax1.legend(lines, labels, fontsize=10, loc='upper left')
    
    # ===== PLOT 2: Loss convergence during operation =====
    ax = axes[0, 1]
    ax.semilogy(cycles, losses, marker='s', markersize=4, linewidth=2, color='orange', alpha=0.8)
    ax.fill_between(cycles, losses, alpha=0.2, color='orange')
    
    ax.set_xlabel('Operation Cycle', fontsize=12, fontweight='bold')
    ax.set_ylabel('Loss (MSE, log scale)', fontsize=12, fontweight='bold')
    ax.set_title('Loss During Operation\n(Inner Loop Continues Fine-Tuning)',
                fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3, which='both')
    
    # ===== PLOT 3: Weight adaptation activity =====
    ax = axes[1, 0]
    ax.semilogy(cycles, weight_changes, marker='^', markersize=4, linewidth=2.5,
               color='purple', alpha=0.8, label='Weight Change Magnitude')
    ax.fill_between(cycles, weight_changes, alpha=0.2, color='purple')
    
    ax.set_xlabel('Operation Cycle', fontsize=12, fontweight='bold')
    ax.set_ylabel('Total Weight Change (log scale)', fontsize=12, fontweight='bold')
    ax.set_title('Adaptation Activity During Operation\n(Shows When Inner Loop is Actively Learning)',
                fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3, which='both')
    ax.legend(fontsize=10)
    
    # ===== PLOT 4: Drift vs Precision correlation =====
    ax = axes[1, 1]
    scatter = ax.scatter(drift_levels, precisions, c=cycles, cmap='plasma', s=100, alpha=0.7, edgecolors='black', linewidth=1)
    
    # Add trend line
    z = np.polyfit(drift_levels, precisions, 2)
    p = np.poly1d(z)
    drift_smooth = np.linspace(min(drift_levels), max(drift_levels), 100)
    ax.plot(drift_smooth, p(drift_smooth), 'r--', linewidth=2.5, label='Trend', alpha=0.8)
    
    ax.set_xlabel('Physics Drift Level', fontsize=12, fontweight='bold')
    ax.set_ylabel('Precision (bits)', fontsize=12, fontweight='bold')
    ax.set_title('Physics Drift Impact on Precision\n(with Inner Loop Adaptation)',
                fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('Operation Cycle', fontsize=11, fontweight='bold')
    ax.legend(fontsize=10)
    
    plt.tight_layout()
    
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"✓ Saved: {output_path}")
    
    return fig


def plot_comparison_training_vs_operation(training_log: Dict, operation_log: Dict,
                                         output_path: str = None) -> plt.Figure:
    """
    Compare Stage 1 (Training) and Stage 2 (Operation) in one comprehensive figure.
    
    Shows:
    - How base model training enables fast operation mode adaptation
    - Precision trajectory across both stages
    
    Args:
        training_log: Output from train_outer_loop()
        operation_log: Output from run_operation_mode()
        output_path: Path to save figure
    
    Returns:
        Figure object
    """
    fig, axes = plt.subplots(1, 2, figsize=(18, 6))
    
    # ===== STAGE 1: Base Model Training =====
    ax = axes[0]
    inner_stats = training_log['inner_cycle_stats']
    
    all_cycles = []
    all_precisions = []
    global_cycle = 0
    colors_list = []
    color_map = plt.cm.Blues(np.linspace(0.3, 1, len(inner_stats)))
    
    for outer_idx, stats in enumerate(inner_stats):
        precisions = stats['precisions']
        for rel_cycle, precision in enumerate(precisions):
            all_cycles.append(global_cycle)
            all_precisions.append(precision)
            colors_list.append(color_map[outer_idx])
            global_cycle += 1
    
    ax.scatter(all_cycles, all_precisions, c=list(range(len(all_cycles))), 
              cmap='Blues', s=80, alpha=0.7, edgecolors='navy', linewidth=0.5)
    
    # Vertical lines for outer loop boundaries
    for boundary in training_log['physics_change_cycles'][1:]:
        ax.axvline(boundary, color='red', linestyle='--', linewidth=2.5, alpha=0.7)
    
    ax.set_xlabel('Cycle', fontsize=13, fontweight='bold')
    ax.set_ylabel('Precision (bits)', fontsize=13, fontweight='bold')
    ax.set_title('Stage 1: Base Model Training\n(Outer Loop: Learning Across Multiple Physics Spaces)',
                fontsize=14, fontweight='bold', color='navy')
    ax.grid(True, alpha=0.3)
    
    # Add annotation
    ax.text(0.02, 0.98, 'RED LINES = Abrupt Physics Changes', transform=ax.transAxes,
           fontsize=11, verticalalignment='top', bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.3))
    
    # ===== STAGE 2: Operation Mode =====
    ax = axes[1]
    op_cycles = operation_log['cycles']
    op_precisions = operation_log['precisions']
    op_drifts = operation_log['drift_level']
    
    ax_twin = ax.twinx()
    
    line1 = ax.plot(op_cycles, op_precisions, marker='o', markersize=6, linewidth=3,
                   color='darkgreen', label='Precision', alpha=0.8)
    ax.fill_between(op_cycles, op_precisions, alpha=0.2, color='darkgreen')
    
    line2 = ax_twin.fill_between(op_cycles, op_drifts, alpha=0.25, color='orange', label='Drift')
    ax_twin.plot(op_cycles, op_drifts, color='darkorange', linewidth=2.5, linestyle='--', alpha=0.8)
    
    ax.set_xlabel('Cycle', fontsize=13, fontweight='bold')
    ax.set_ylabel('Precision (bits)', fontsize=13, fontweight='bold', color='darkgreen')
    ax_twin.set_ylabel('Physics Drift', fontsize=13, fontweight='bold', color='darkorange')
    ax.set_title('Stage 2: Operation Mode\n(Inner Loop Only: Gradual Physics Drift)',
                fontsize=14, fontweight='bold', color='darkgreen')
    ax.grid(True, alpha=0.3)
    ax.tick_params(axis='y', labelcolor='darkgreen')
    ax_twin.tick_params(axis='y', labelcolor='darkorange')
    
    lines = line1 + [line2]
    labels = ['Precision', 'Drift']
    ax.legend(lines, labels, fontsize=11, loc='upper left')
    
    # Add annotation
    ax.text(0.02, 0.98, 'Starts with learned base model\nfrom Stage 1', transform=ax.transAxes,
           fontsize=11, verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.3))
    
    plt.tight_layout()
    
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"✓ Saved: {output_path}")
    
    return fig
