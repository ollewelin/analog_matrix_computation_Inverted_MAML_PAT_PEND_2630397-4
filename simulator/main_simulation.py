#!/usr/bin/env python3
"""
Main Simulation: Inverted MAML 3x6x6 MVP Test
Execute Phase 1: Verify core architecture and convergence

Usage:
    python main_simulation.py
    python main_simulation.py --cycles 50 --verbose
"""

import sys
import argparse
import json
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict

# Import simulator components
from matrix_core import AtomicTriad
from maml_optimizer import InvertedMAML, create_test_vectors


def setup_logging(verbose: bool = True):
    """Simple logging setup."""
    class Logger:
        def __init__(self, verbose=True):
            self.verbose = verbose
        
        def info(self, msg):
            if self.verbose:
                print(f"[INFO] {msg}")
        
        def debug(self, msg):
            if self.verbose:
                print(f"[DEBUG] {msg}")
    
    return Logger(verbose)


def run_phase1_mvp(max_cycles: int = 50, num_test_vectors: int = 16, 
                   verbose: bool = True, plot: bool = True) -> Dict:
    """
    Phase 1 MVP: Single atomic triad + MAML learning
    
    Test objectives:
        1. Verify forward pass works (M33 + M3 + M8)
        2. Verify gradient computation (stratified batching)
        3. Measure convergence (cycles to 6-bit precision)
        4. Profile performance
    
    Args:
        max_cycles: Maximum training cycles
        num_test_vectors: Number of test samples
        verbose: Print progress
        plot: Generate convergence plots
    
    Returns:
        results: Summary dict with all metrics
    """
    logger = setup_logging(verbose)
    logger.info("=" * 70)
    logger.info("Inverted MAML 3x6x6 Simulator - Phase 1 MVP")
    logger.info("=" * 70)
    
    # Create atomic triad
    logger.info("Initializing atomic triad (M33 + M3 + M8)...")
    triad = AtomicTriad(size=6)
    logger.info(f"  ✓ Created 3 × 6×6 matrices")
    logger.info(f"  ✓ Total cells: {len(triad.get_all_cells())} (108 active + refs + bias)")
    
    # Create MAML optimizer
    logger.info("Initializing MAML optimizer...")
    maml = InvertedMAML(triad, learning_rate=0.05, num_strata=1, 
                       convergence_threshold=5.5)
    logger.info(f"  ✓ Learning rate: {maml.lr}")
    logger.info(f"  ✓ Measurement strategy: BREAKTHROUGH - Maximum signal only (0.5ms)")
    logger.info(f"  ✓ Stratified windows: {maml.num_strata}")
    logger.info(f"  ✓ Convergence target: {maml.convergence_threshold} bits (6-bit)")
    
    # Generate test vectors
    logger.info("Generating test vectors...")
    x_train, y_train = create_test_vectors(num_vectors=num_test_vectors, 
                                          dimension=6, seed=42)
    logger.info(f"  ✓ Training samples: {x_train.shape[0]}")
    logger.info(f"  ✓ Input dimension: {x_train.shape[1]}")
    logger.info(f"  ✓ Target range: [{y_train.min():.3f}, {y_train.max():.3f}]")
    
    # Inject physical non-idealities
    logger.info("Injecting physical non-idealities...")
    config = {
        'V_th_sigma': 0.03,       # ±3% threshold voltage variation (was 2%)
        'g_m_sigma': 0.05,        # ±5% transconductance variation (was 2%)
        'R_sigma': 0.05           # ±5% resistance variation (was 2%)
    }
    triad.inject_manufacturing_variations(config)
    triad.inject_thermal_drift(temp_delta_C=12.0)  # 12°C ambient rise (was 5°C)
    triad.inject_noise(noise_sigma=0.005)           # 0.5% thermal noise (was 0.1%)
    logger.info(f"  ✓ Manufacturing tolerance: ±5%")
    logger.info(f"  ✓ Thermal drift: +12°C")
    logger.info(f"  ✓ Thermal noise: 0.5%")
    
    # Training loop
    logger.info("\nStarting training...")
    logger.info("-" * 70)
    
    import time
    start_time = time.time()
    
    training_log = maml.train(x_train, y_train, max_cycles=max_cycles, verbose=verbose)
    
    elapsed_time = time.time() - start_time
    
    logger.info("-" * 70)
    
    # Results summary
    logger.info("\nTraining Results:")
    logger.info(f"  Cycles completed: {training_log['cycles'][-1] + 1}")
    logger.info(f"  Final loss: {training_log['losses'][-1]:.2e}")
    logger.info(f"  Final precision: {training_log['precisions'][-1]:.2f} bits")
    logger.info(f"  Target precision: 5.5 bits (6-bit threshold)")
    logger.info(f"  Converged: {'Yes ✓' if training_log['converged'] else 'No'}")
    
    if training_log['converged']:
        logger.info(f"  Convergence cycle: {training_log['convergence_cycle']}")
    
    logger.info(f"  Elapsed time: {elapsed_time:.2f} sec")
    logger.info(f"  Cycles/sec: {(training_log['cycles'][-1] + 1) / elapsed_time:.1f}")
    
    # Compile results
    results = {
        'experiment': 'Inverted MAML 3x6x6 MVP',
        'date': datetime.now().isoformat(),
        'parameters': {
            'matrix_size': 6,
            'num_matrices': 3,
            'num_strata': maml.num_strata,
            'learning_rate': maml.lr,
            'num_training_samples': len(x_train),
            'max_cycles': max_cycles
        },
        'physical_effects': {
            'manufacturing_tolerance_percent': 5.0,
            'thermal_drift_delta_C': 5.0,
            'thermal_noise_percent': 0.1
        },
        'convergence': {
            'cycles_completed': training_log['cycles'][-1] + 1,
            'converged': training_log['converged'],
            'convergence_cycle': training_log['convergence_cycle'],
            'final_loss': float(training_log['losses'][-1]),
            'final_precision_bits': float(training_log['precisions'][-1]),
            'target_precision_bits': maml.convergence_threshold
        },
        'performance': {
            'elapsed_time_sec': elapsed_time,
            'cycles_per_sec': (training_log['cycles'][-1] + 1) / elapsed_time
        },
        'loss_history': [float(x) for x in training_log['losses']],
        'precision_history': [float(x) for x in training_log['precisions']]
    }
    
    # Compute IF metrics
    if training_log['converged']:
        cycles_to_convergence = training_log['convergence_cycle']
        precision_achieved = training_log['precisions'][training_log['convergence_cycle']]
        results['IF_metrics'] = {
            'IF1_drift_tracking': {
                'cycles_to_convergence': cycles_to_convergence,
                'target_cycles': 30,
                'pass': cycles_to_convergence < 30
            },
            'IF4_convergence_speed': {
                'time_per_cycle_ms': (elapsed_time / (training_log['cycles'][-1] + 1)) * 1000,
                'target_ms': 5.0,
                'pass': (elapsed_time / (training_log['cycles'][-1] + 1)) * 1000 < 5.0
            }
        }
    
    return results


def save_results(results: Dict, output_dir: str = './results'):
    """Save results to JSON."""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    filename = output_path / f"mvp_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✓ Results saved to: {filename}")
    return filename


def plot_convergence(results: Dict, output_dir: str = './results'):
    """Generate convergence plots."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("Warning: matplotlib not installed, skipping plots")
        return
    
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Create figure
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
    
    cycles = results['convergence']['cycles_completed']
    losses = results['loss_history']
    precisions = results['precision_history']
    
    # Loss plot
    ax1.semilogy(range(len(losses)), losses, 'b-', linewidth=2, label='Training Loss')
    ax1.set_xlabel('Cycle')
    ax1.set_ylabel('Loss (log scale)')
    ax1.set_title('Convergence: Training Loss')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # Precision plot
    ax2.plot(range(len(precisions)), precisions, 'g-', linewidth=2, label='Achieved Precision')
    ax2.axhline(y=5.5, color='r', linestyle='--', label='6-bit Target (5.5 bits)')
    ax2.set_xlabel('Cycle')
    ax2.set_ylabel('Precision (bits)')
    ax2.set_title('Convergence: Precision (6-bit = 0.39% error)')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    ax2.set_ylim([0, 8])
    
    plt.tight_layout()
    
    filename = output_path / f"convergence_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    plt.savefig(filename, dpi=150)
    print(f"✓ Plot saved to: {filename}")
    plt.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Inverted MAML 3x6x6 Simulator - Phase 1 MVP'
    )
    parser.add_argument('--cycles', type=int, default=50,
                       help='Maximum training cycles (default: 50)')
    parser.add_argument('--samples', type=int, default=16,
                       help='Number of training samples (default: 16)')
    parser.add_argument('--verbose', action='store_true',
                       help='Verbose output')
    parser.add_argument('--plot', action='store_true',
                       help='Generate convergence plots')
    parser.add_argument('--output', type=str, default='./results',
                       help='Output directory for results')
    
    args = parser.parse_args()
    
    # Run MVP
    results = run_phase1_mvp(
        max_cycles=args.cycles,
        num_test_vectors=args.samples,
        verbose=args.verbose or True,
        plot=args.plot
    )
    
    # Save results
    save_results(results, args.output)
    
    # Generate plots
    if args.plot:
        plot_convergence(results, args.output)
    
    print("\n" + "="*70)
    print("Phase 1 MVP Complete ✓")
    print("="*70)
    
    return 0 if results['convergence']['converged'] else 1


if __name__ == '__main__':
    sys.exit(main())
