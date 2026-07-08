#!/usr/bin/env python3
"""
Direct Test for 32x32 Inverted MAML Simulator
==============================================

Scaled version: 6x6 → 32x32 matrices (16x more cells)

Tests with:
  - M33: Primary 32x32 matrix (FIXED)
  - M3: Correction 32x32 matrix (TRAINED)
  - M8: Correction 32x32 matrix (TRAINED)
  
Input vectors: 32-dimensional (scaled from 6)
Output: Precision in bits
"""

import sys
sys.path.insert(0, '.')

import numpy as np
from matrix_core import AtomicTriad
from maml_optimizer import InvertedMAML
import os
import json


def create_test_vectors_32(num_vectors=16, seed=42):
    """Generate 32-dimensional test vectors (scaled from 6-dim)."""
    np.random.seed(seed)
    x_vectors = np.random.uniform(0.2, 0.8, (num_vectors, 32))  # 32-dim inputs
    
    # Target: random 32-dim outputs
    y_vectors = np.random.uniform(-0.5, 0.5, (num_vectors, 32))
    
    return x_vectors, y_vectors


def run_direct_test_32(max_cycles=100, num_samples=16, seed=42, verbose=True):
    """
    Run Inverted MAML test with 32x32 matrices.
    
    Returns:
        results: Dict with precision over cycles
    """
    
    if verbose:
        print("="*75)
        print("DIRECT TEST: 32x32 Inverted MAML Simulator")
        print("="*75)
        print(f"\nConfiguration:")
        print(f"  Matrix size: 32x32 (1024 cells per matrix)")
        print(f"  Total cells: 3072 (3 matrices)")
        print(f"  Input dimension: 32")
        print(f"  Training cycles: {max_cycles}")
        print(f"  Samples per cycle: {num_samples}")
        print(f"  Architecture: M33(FIXED) + M8(tanh(M3))")
        print()
    
    # Create test data
    x_train, y_train = create_test_vectors_32(num_vectors=num_samples, seed=seed)
    
    # Initialize with no physical effects (pure algorithm test)
    triad = AtomicTriad(size=32)
    
    # IMPORTANT: Don't inject physical effects - testing pure algorithm
    # (Can enable later with: triad.inject_manufacturing_variations, etc.)
    
    maml = InvertedMAML(triad, learning_rate=0.05, num_strata=1)
    
    precisions = []
    losses = []
    
    if verbose:
        print("Starting training...")
        print("-"*75)
    
    for cycle in range(max_cycles):
        # Measure precision before update
        cycle_loss = 0.0
        for x, y in zip(x_train, y_train):
            triad.refresh_cycle()
            grad_m3, grad_m8, loss = maml.compute_stratified_gradient(x, y)
            cycle_loss += loss
        
        cycle_loss /= len(x_train)
        precision_bits = -np.log2(np.clip(cycle_loss, 1e-6, 1.0))
        precisions.append(precision_bits)
        losses.append(cycle_loss)
        
        if verbose and cycle % 10 == 0:
            print(f"  Cycle {cycle:3d}: {precision_bits:.2f} bits | Loss: {cycle_loss:.6f}")
        
        # Train
        for x, y in zip(x_train, y_train):
            maml.update_weights(x, y)
    
    if verbose:
        print("-"*75)
        print(f"\nFinal Results (32x32 Matrix):")
        print(f"  Cycle 0:    {precisions[0]:.2f} bits (initial)")
        print(f"  Cycle 10:   {precisions[10]:.2f} bits")
        print(f"  Cycle {max_cycles-1:2d}:   {precisions[-1]:.2f} bits (final)")
        print(f"  Improvement: {precisions[-1] - precisions[0]:+.2f} bits")
        print()
        
        target = 5.5  # 6-bit target
        if precisions[-1] >= target:
            print(f"✓ SUCCESS: Reached target ({precisions[-1]:.2f} >= {target:.1f})")
        else:
            print(f"✗ MISS: Below target ({precisions[-1]:.2f} < {target:.1f})")
    
    results = {
        'precisions': precisions,
        'losses': losses,
        'final_precision': float(precisions[-1]),
        'cycle_0': float(precisions[0]),
        'improvement': float(precisions[-1] - precisions[0]),
        'matrix_size': 32,
        'total_cells': 3072,
        'input_dimension': 32,
        'seed': seed,
        'max_cycles': max_cycles,
        'converged': bool(precisions[-1] >= 5.5)
    }
    
    return results


def plot_results(results, output_dir='results_32x32'):
    """Plot precision over training cycles."""
    import matplotlib.pyplot as plt
    
    os.makedirs(output_dir, exist_ok=True)
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    cycles = list(range(len(results['precisions'])))
    precisions = results['precisions']
    
    ax.plot(cycles, precisions, 'o-', linewidth=2, markersize=4, label='32x32 Inverted MAML')
    ax.axhline(y=5.5, color='orange', linestyle='--', linewidth=2, label='6-bit Target (5.5 bits)')
    ax.fill_between(cycles, 5.5, max(precisions)+0.5, alpha=0.1, color='green')
    
    ax.set_xlabel('Training Cycle', fontsize=12)
    ax.set_ylabel('Precision (bits)', fontsize=12)
    ax.set_title('32x32 Inverted MAML: Precision Convergence', fontsize=13, fontweight='bold')
    ax.legend(fontsize=11, loc='best')
    ax.grid(True, alpha=0.3)
    ax.set_ylim([0, 8])
    
    plt.tight_layout()
    filepath = os.path.join(output_dir, 'precision_32x32.png')
    plt.savefig(filepath, dpi=150, bbox_inches='tight')
    print(f"✓ Plot saved: {filepath}")
    plt.close()


if __name__ == '__main__':
    results = run_direct_test_32(max_cycles=100, num_samples=16, seed=42, verbose=True)
    
    # Plot
    plot_results(results)
    
    # Save results
    os.makedirs('results_32x32', exist_ok=True)
    with open('results_32x32/direct_test_32x32.json', 'w') as f:
        json.dump(results, f, indent=2)
    print(f"✓ Results saved: results_32x32/direct_test_32x32.json")
