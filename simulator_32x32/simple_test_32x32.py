#!/usr/bin/env python3
"""
Simple 32x32 Test: Easier Problem Setup
========================================

Instead of random targets, use a simple mapping:
  y_target = A @ x  (where A is a known low-rank matrix)

This is much easier to learn and lets us see if the architecture works.
"""

import sys
sys.path.insert(0, '.')

import numpy as np
from matrix_core import AtomicTriad
from maml_optimizer import InvertedMAML
import os
import json
import matplotlib.pyplot as plt


def create_simple_task_32():
    """Create a simple linear task for 32x32."""
    np.random.seed(42)
    
    # Create a simple rank-2 target matrix
    rank_1 = np.random.randn(32)
    rank_2 = np.random.randn(32)
    
    # Task: Given x, predict y = (rank_1 dot x) * rank_2
    #       This is rank-1, very learnable
    
    num_samples = 16
    x_vectors = np.random.uniform(0.1, 0.9, (num_samples, 32))
    
    y_vectors = np.zeros((num_samples, 32))
    for i in range(num_samples):
        coeff = np.dot(rank_1, x_vectors[i])
        y_vectors[i] = coeff * rank_2 / np.linalg.norm(rank_2)
    
    return x_vectors, y_vectors


def run_simple_test_32(max_cycles=200, verbose=True):
    """
    Run simple learnable task on 32x32 with two phases:
    
    Phase 0 (Cycles 0-9):   Training OFF (baseline with fixed center weights)
    Phase 1 (Cycles 10+):   Training ON (learning with compensation)
    """
    
    if verbose:
        print("="*75)
        print("SIMPLE 32x32 TEST: Learnable Rank-1 Task")
        print("="*75)
        print()
        print("Task: Learn y = (w1 · x) * w2  (rank-1 outer product)")
        print("  Input:  32-dim vector x")
        print("  Output: 32-dim vector y")
        print("  Difficulty: EASY (rank-1, highly learnable)")
        print()
        print("Phases:")
        print("  Phase 0 (Cycles 0-9):   Training OFF (baseline, center weights fixed)")
        print("  Phase 1 (Cycles 10+):   Training ON  (learning enabled)")
        print()
    
    # Create simple task
    x_train, y_train = create_simple_task_32()
    
    # Initialize
    triad = AtomicTriad(size=32)
    maml = InvertedMAML(triad, learning_rate=0.1, num_strata=1)  # Higher LR for easier task
    
    # Fix weights at center for Phase 0
    triad.M3.weights.fill(2.6)
    triad.M8.weights.fill(2.6)
    
    precisions = []
    losses = []
    phases = []  # Track which phase each cycle belongs to
    
    if verbose:
        print("Starting measurement...")
        print("-"*75)
    
    # Phase 0: Training OFF (10 cycles)
    for cycle in range(10):
        # Measure
        cycle_loss = 0.0
        for x, y in zip(x_train, y_train):
            triad.refresh_cycle()
            grad_m3, grad_m8, loss = maml.compute_stratified_gradient(x, y)
            cycle_loss += loss
        
        cycle_loss /= len(x_train)
        precision_bits = -np.log2(np.clip(cycle_loss, 1e-6, 1.0))
        precisions.append(precision_bits)
        losses.append(cycle_loss)
        phases.append(0)  # Phase 0
        
        if verbose:
            print(f"  Phase 0, Cycle {cycle:3d}: {precision_bits:.2f} bits | Loss: {cycle_loss:.6f} (training OFF)")
    
    # Phase 1: Training ON (continue for remaining cycles)
    training_cycles = max_cycles - 10
    for cycle in range(training_cycles):
        # Measure
        cycle_loss = 0.0
        for x, y in zip(x_train, y_train):
            triad.refresh_cycle()
            grad_m3, grad_m8, loss = maml.compute_stratified_gradient(x, y)
            cycle_loss += loss
        
        cycle_loss /= len(x_train)
        precision_bits = -np.log2(np.clip(cycle_loss, 1e-6, 1.0))
        precisions.append(precision_bits)
        losses.append(cycle_loss)
        phases.append(1)  # Phase 1
        
        if verbose and (cycle % 20 == 0 or cycle == training_cycles - 1):
            print(f"  Phase 1, Cycle {10+cycle:3d}: {precision_bits:.2f} bits | Loss: {cycle_loss:.6f} (training ON)")
        
        # Train (update weights)
        for x, y in zip(x_train, y_train):
            maml.update_weights(x, y)
    
    if verbose:
        print("-"*75)
        print(f"\nResults (Simple Rank-1 Task with Baseline):")
        print(f"  Phase 0 (OFF, Cycles 0-9):")
        print(f"    Start:  {precisions[0]:.2f} bits")
        print(f"    End:    {precisions[9]:.2f} bits")
        print(f"    Avg:    {np.mean(precisions[0:10]):.2f} bits (baseline)")
        print(f"  Phase 1 (ON, Cycles 10-{max_cycles-1}):")
        print(f"    Start:  {precisions[10]:.2f} bits")
        print(f"    End:    {precisions[-1]:.2f} bits")
        print(f"    Avg:    {np.mean(precisions[10:]):.2f} bits")
        print(f"  Total Improvement: {precisions[-1] - precisions[0]:+.2f} bits")
        print(f"  Training Impact:   {precisions[-1] - np.mean(precisions[0:10]):+.2f} bits")
        print()
    
    if precisions[-1] >= 5.5:
        print(f"✓ SUCCESS: Reached 6-bit target ({precisions[-1]:.2f})")
    else:
        print(f"⚠ Goal: {precisions[-1]:.2f} bits (need {5.5:.1f} for 6-bit)")
    
    return {
        'precisions': precisions,
        'losses': losses,
        'phases': phases,
        'final': float(precisions[-1]),
        'improvement': float(precisions[-1] - precisions[0]),
        'baseline_avg': float(np.mean(precisions[0:10])),
        'training_avg': float(np.mean(precisions[10:]))
    }


def compare_results(result_32):
    """Compare baseline vs training phases."""
    print()
    print("="*75)
    print("PHASE ANALYSIS")
    print("="*75)
    print()
    print(f"Phase 0 (Training OFF - Baseline):")
    print(f"  Average precision: {result_32['baseline_avg']:.2f} bits")
    print()
    print(f"Phase 1 (Training ON - Learning):")
    print(f"  Average precision: {result_32['training_avg']:.2f} bits")
    print(f"  Improvement over baseline: +{result_32['training_avg'] - result_32['baseline_avg']:.2f} bits")
    print()
    print(f"Total improvement (Cycle 0 → {len(result_32['precisions'])-1}):")
    print(f"  {result_32['improvement']:+.2f} bits")
    print()
    print("Notes:")
    print("  - 32x32 has 28.4x more cells than 6x6 (1024 vs 36)")
    print("  - Rank-1 task is easier than full 32x32 mapping")
    print("  - Training OFF (Phase 0) shows baseline precision without compensation")
    print("  - Training ON (Phase 1) shows learning with M3/M8 weight updates")


if __name__ == '__main__':
    result_32 = run_simple_test_32(max_cycles=200, verbose=True)
    
    # Plot with two phases highlighted
    fig, ax = plt.subplots(figsize=(14, 7))
    
    cycles = list(range(len(result_32['precisions'])))
    precisions = result_32['precisions']
    phases = result_32['phases']
    
    # Split into phases for separate plotting
    phase0_cycles = [c for c, p in enumerate(cycles) if phases[c] == 0]
    phase1_cycles = [c for c, p in enumerate(cycles) if phases[c] == 1]
    
    phase0_prec = [precisions[c] for c in phase0_cycles]
    phase1_prec = [precisions[c] for c in phase1_cycles]
    
    # Plot each phase with different color
    ax.plot(phase0_cycles, phase0_prec, 'o-', linewidth=2, markersize=6, 
            color='red', label='Phase 0: Training OFF (Baseline)', alpha=0.7)
    ax.plot(phase1_cycles, phase1_prec, 'o-', linewidth=2, markersize=6, 
            color='green', label='Phase 1: Training ON (Learning)')
    
    # Add vertical separator at phase boundary
    ax.axvline(x=9.5, color='gray', linestyle='--', linewidth=2, alpha=0.5)
    ax.text(9.5, ax.get_ylim()[1] * 0.95, 'Training\nStarts', 
            ha='center', fontsize=10, bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.3))
    
    # Add target line
    ax.axhline(y=5.5, color='orange', linestyle='--', linewidth=2, label='6-bit Target')
    
    # Add baseline average line
    ax.axhline(y=result_32['baseline_avg'], color='red', linestyle=':', linewidth=1.5, 
               alpha=0.5, label=f'Baseline Avg: {result_32["baseline_avg"]:.2f} bits')
    
    ax.set_xlabel('Cycle', fontsize=12)
    ax.set_ylabel('Precision (bits)', fontsize=12)
    ax.set_title('32x32 Simple Rank-1 Task: Training OFF vs ON', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best', fontsize=11)
    ax.set_ylim([2.5, 6.5])
    
    os.makedirs('results_32x32', exist_ok=True)
    plt.savefig('results_32x32/simple_task_32x32_with_baseline.png', dpi=150, bbox_inches='tight')
    print(f"\n✓ Plot saved: results_32x32/simple_task_32x32_with_baseline.png")
    plt.close()
    
    compare_results(result_32)
