#!/usr/bin/env python3
"""
Operation Mode: Duty Time Switch at Cycle 100

Two-phase experiment simulates hardware reconfiguration:
  Phase 1 (Cycles 0-99):  num_strata=1 (narrow measurement window at peak)
  Phase 2 (Cycles 100+):  num_strata=5 (wider balanced window)

Hypothesis: More measurement windows = more gradient information = better convergence
"""

import numpy as np
import sys
sys.path.insert(0, '.')

from matrix_core import AtomicTriad
from maml_optimizer import InvertedMAML, create_test_vectors

def run_operation_mode_test():
    print("=" * 80)
    print("OPERATION MODE: DUTY TIME SWITCH AT CYCLE 100")
    print("=" * 80)
    print()
    print("Modified test with TWO additional phases:")
    print("  Pre-Phase (Cycles 0-9):   Training OFF, M3/M8 weights FIXED at center")
    print("  Phase 1 (Cycles 10-99):   Training ON, num_strata=1 (narrow window)")
    print("  Phase 2 (Cycles 100-199): Training ON, num_strata=5 (wide window)")
    print()
    
    dim = 32
    num_samples = 16
    
    # ========== PRE-PHASE: Training disabled, center weights ==========
    print("-" * 80)
    print("PRE-PHASE: Cycles 0-9 | Training OFF (baseline without compensation)")
    print("-" * 80)
    
    atomic_triad_pre = AtomicTriad(size=dim)
    optimizer_pre = InvertedMAML(atomic_triad_pre, learning_rate=0.05, num_strata=1)
    
    # Fix M3 and M8 at center (2.6V - no correction)
    optimizer_pre.triad.M3.weights.fill(2.6)
    optimizer_pre.triad.M8.weights.fill(2.6)
    
    pre_phase_precision = []
    pre_phase_loss = []
    
    for cycle in range(10):
        x_batch, y_batch = create_test_vectors(
            num_vectors=num_samples,
            dimension=dim,
            seed=42 + cycle
        )
        
        # Compute loss but DON'T update weights
        cycle_loss = 0.0
        for x, y in zip(x_batch, y_batch):
            optimizer_pre.triad.refresh_cycle()
            grad_M3, grad_M8, loss = optimizer_pre.compute_stratified_gradient(x, y)
            cycle_loss += loss
        
        cycle_loss /= num_samples
        precision_bits = -np.log2(np.clip(cycle_loss, 1e-10, 1.0))
        pre_phase_precision.append(precision_bits)
        pre_phase_loss.append(cycle_loss)
        
        print(f"  Cycle   {cycle:3d}: {precision_bits:6.2f} bits | Loss: {cycle_loss:.6f} (no update)")
    
    # ========== PHASE 1: Training enabled, narrow window (num_strata=1) ==========
    print()
    print("-" * 80)
    print("PHASE 1: Cycles 10-99 | Training ON, narrow measurement window (num_strata=1)")
    print("-" * 80)
    
    atomic_triad_p1 = AtomicTriad(size=dim)
    optimizer_p1 = InvertedMAML(atomic_triad_p1, learning_rate=0.05, num_strata=1)
    
    # Start with center weights
    optimizer_p1.triad.M3.weights.fill(2.6)
    optimizer_p1.triad.M8.weights.fill(2.6)
    
    phase1_precision = []
    phase1_loss = []
    
    for cycle in range(90):  # Cycles 10-99 (90 cycles)
        x_batch, y_batch = create_test_vectors(
            num_vectors=num_samples,
            dimension=dim,
            seed=42 + 10 + cycle  # Continue from where pre-phase ended
        )
        
        # Process batch with training enabled
        cycle_loss = 0.0
        for x, y in zip(x_batch, y_batch):
            optimizer_p1.triad.refresh_cycle()
            grad_M3, grad_M8, loss = optimizer_p1.compute_stratified_gradient(x, y)
            cycle_loss += loss
        
        cycle_loss /= num_samples
        precision_bits = -np.log2(np.clip(cycle_loss, 1e-10, 1.0))
        phase1_precision.append(precision_bits)
        phase1_loss.append(cycle_loss)
        
        # Update weights
        for x, y in zip(x_batch, y_batch):
            optimizer_p1.update_weights(x, y)
        
        if cycle % 20 == 0 or cycle == 89:
            print(f"  Cycle  {10+cycle:3d}: {precision_bits:6.2f} bits | Loss: {cycle_loss:.6f}")
    
    # Save Phase 1 weights for transfer to Phase 2
    weights_M3_p1 = optimizer_p1.triad.M3.weights.copy()
    weights_M8_p1 = optimizer_p1.triad.M8.weights.copy()
    
    # ========== PHASE 2: Wide window (num_strata=5) ==========
    print()
    print("-" * 80)
    print("PHASE 2: Cycles 100-199 | Wide measurement window (num_strata=5)")
    print("         Starting from Phase 1 trained weights")
    print("-" * 80)
    
    atomic_triad_p2 = AtomicTriad(size=dim)
    optimizer_p2 = InvertedMAML(atomic_triad_p2, learning_rate=0.05, num_strata=5)
    
    # Transfer Phase 1 weights to Phase 2
    optimizer_p2.triad.M3.weights = weights_M3_p1.copy()
    optimizer_p2.triad.M8.weights = weights_M8_p1.copy()
    
    phase2_precision = []
    phase2_loss = []
    
    for cycle in range(100):
        x_batch, y_batch = create_test_vectors(
            num_vectors=num_samples,
            dimension=dim,
            seed=42 + 100 + cycle
        )
        
        # Process batch with training enabled
        cycle_loss = 0.0
        for x, y in zip(x_batch, y_batch):
            optimizer_p2.triad.refresh_cycle()
            grad_M3, grad_M8, loss = optimizer_p2.compute_stratified_gradient(x, y)
            cycle_loss += loss
        
        cycle_loss /= num_samples
        precision_bits = -np.log2(np.clip(cycle_loss, 1e-10, 1.0))
        phase2_precision.append(precision_bits)
        phase2_loss.append(cycle_loss)
        
        # Update weights
        for x, y in zip(x_batch, y_batch):
            optimizer_p2.update_weights(x, y)
        
        if cycle % 20 == 0 or cycle == 99:
            print(f"  Cycle {100+cycle:3d}: {precision_bits:6.2f} bits | Loss: {cycle_loss:.6f}")
    
    # ========== RESULTS SUMMARY ==========
    print()
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    
    pre_avg = np.mean(pre_phase_precision)
    pre_start = pre_phase_precision[0]
    pre_end = pre_phase_precision[-1]
    
    p1_avg = np.mean(phase1_precision)
    p1_start = phase1_precision[0]
    p1_end = phase1_precision[-1]
    
    p2_avg = np.mean(phase2_precision)
    p2_start = phase2_precision[0]
    p2_end = phase2_precision[-1]
    
    print(f"\nPre-Phase (training OFF, center weights):")
    print(f"  Cycle 0:   {pre_start:6.2f} bits (baseline)")
    print(f"  Cycle 9:   {pre_end:6.2f} bits")
    print(f"  Avg:       {pre_avg:6.2f} bits")
    
    print(f"\nPhase 1 (training ON, num_strata=1):")
    print(f"  Cycle 10:  {p1_start:6.2f} bits (training starts)")
    print(f"  Cycle 99:  {p1_end:6.2f} bits")
    print(f"  Avg:       {p1_avg:6.2f} bits")
    print(f"  Improvement: +{p1_end - pre_end:.2f} bits vs baseline")
    
    print(f"\nPhase 2 (training ON, num_strata=5):")
    print(f"  Cycle 100: {p2_start:6.2f} bits (wider window)")
    print(f"  Cycle 199: {p2_end:6.2f} bits")
    print(f"  Avg:       {p2_avg:6.2f} bits")
    print(f"  Improvement: +{p2_end - p1_end:.2f} bits vs Phase 1")
    
    print(f"\nSummary:")
    print(f"  Pre-Phase baseline: {pre_avg:6.2f} bits")
    print(f"  Phase 1 trained:    {p1_avg:6.2f} bits (+{p1_avg - pre_avg:.2f})")
    print(f"  Phase 2 wider:      {p2_avg:6.2f} bits (+{p2_avg - pre_avg:.2f} vs baseline)")
    
    print()
    print("=" * 80)
    
    return pre_phase_precision, phase1_precision, phase2_precision, pre_phase_loss, phase1_loss, phase2_loss


if __name__ == "__main__":
    pre_prec, p1_prec, p2_prec, pre_loss, p1_loss, p2_loss = run_operation_mode_test()
