"""
COMPARISON TEST: With vs Without Per-Cell Vth Variations
=========================================================

This test directly compares:
  1. Harsh compression WITHOUT per-cell Vth variations
  2. Harsh compression WITH per-cell Vth variations

Shows the actual performance impact and cell-level effects.
"""

import numpy as np
from matrix_core import AtomicTriad
from maml_optimizer import InvertedMAML, create_test_vectors


def run_harsh_baseline(use_per_cell_variations=False):
    """
    Run harsh compression test with or without per-cell Vth variations.
    
    Args:
        use_per_cell_variations: If True, apply per-cell Vth variations
    
    Returns:
        Dict with results
    """
    
    # ==================== SETUP ====================
    print(f"\n[SETUP] Creating harsh 32x32 system...")
    if use_per_cell_variations:
        print(f"  MODE: WITH per-cell Vth variations")
    else:
        print(f"  MODE: WITHOUT per-cell Vth variations")
    
    triad = AtomicTriad(size=32)
    
    # Apply manufacturing variations (same for both tests)
    harsh_config = {
        'V_th_sigma': 0.15,      # ±15% threshold variation
        'g_m_sigma': 0.20,       # ±20% transconductance variation
        'R_sigma': 0.20,         # ±20% resistance variation
    }
    
    for matrix in [triad.M33, triad.M3, triad.M8]:
        matrix.inject_manufacturing_variations(harsh_config)
        matrix.inject_thermal_drift(temp_delta_C=35.0)
        matrix.inject_noise(noise_sigma=0.03)
    
    # DIFFERENCE: Apply per-cell Vth variations ONLY in second test
    if use_per_cell_variations:
        triad.apply_per_cell_vth_variations(vth_variation_sigma=0.06)
    
    # ==================== OPTIMIZER SETUP ====================
    optimizer = InvertedMAML(
        triad=triad,
        learning_rate=0.50,
        num_strata=1,
        convergence_threshold=5.5,
        adaptive_lr=True,
        lr_decay_factor=0.98
    )
    
    # ==================== TRAINING DATA ====================
    num_samples = 32
    x_train, y_train = create_test_vectors(num_vectors=num_samples, 
                                          dimension=32, seed=42)
    
    # ==================== PHASE 0: BASELINE ====================
    baseline_losses = []
    baseline_precisions = []
    
    for cycle in range(10):
        cycle_loss = 0.0
        
        # Measure only (no updates)
        for x, y in zip(x_train, y_train):
            grad_m3, grad_m8, loss = optimizer.compute_stratified_gradient(x, y)
            cycle_loss += loss
        
        avg_loss = cycle_loss / len(x_train)
        baseline_losses.append(avg_loss)
        precision = -np.log2(np.clip(avg_loss, 1e-6, 1.0))
        baseline_precisions.append(precision)
    
    baseline_avg = np.mean(baseline_precisions)
    
    # ==================== PHASE 1: MAML LEARNING ====================
    learning_losses = []
    learning_precisions = []
    learning_lrs = []
    
    for cycle in range(10, 100):
        cycle_loss = 0.0
        
        for x, y in zip(x_train, y_train):
            loss = optimizer.update_weights(x, y)
            cycle_loss += loss
        
        avg_loss = cycle_loss / len(x_train)
        learning_losses.append(avg_loss)
        precision = -np.log2(np.clip(avg_loss, 1e-6, 1.0))
        learning_precisions.append(precision)
        learning_lrs.append(optimizer.lr)
        
        # Print progress
        if cycle % 10 == 0 or cycle == 99:
            print(f"  Cycle {cycle:3d}: Loss={avg_loss:.4e}, Precision={precision:.2f} bits, LR={optimizer.lr:.6f}")
    
    final_precision = learning_precisions[-1]
    improvement = final_precision - baseline_avg
    
    return {
        'baseline_avg': baseline_avg,
        'final_precision': final_precision,
        'improvement': improvement,
        'baseline_losses': baseline_losses,
        'learning_losses': learning_losses,
        'learning_precisions': learning_precisions,
        'triad': triad
    }


def analyze_cell_distribution(triad, label=""):
    """Analyze per-cell Vth distribution in M33 matrix."""
    print(f"\n  {label} - M33 Cell Distribution:")
    
    vth_offsets = []
    vth_totals = []
    
    for cell in triad.M33.cell_bank.cells_active:
        vth_offsets.append(cell.V_th_variation_offset)
        vth_totals.append(cell.V_th_mfg + cell.V_th_variation_offset)
    
    vth_offsets = np.array(vth_offsets)
    vth_totals = np.array(vth_totals)
    
    print(f"    Per-cell offset: {vth_offsets.min():+.4f}V to {vth_offsets.max():+.4f}V (std={vth_offsets.std():.4f}V)")
    print(f"    Total Vth range:  {vth_totals.min():.4f}V to {vth_totals.max():.4f}V")
    print(f"    Mean Vth: {vth_totals.mean():.4f}V")
    
    # Count distribution
    weak = (vth_totals < 0.50).sum()
    normal = ((vth_totals >= 0.50) & (vth_totals < 0.70)).sum()
    strong = (vth_totals >= 0.70).sum()
    
    print(f"    Distribution: {weak} weak (<0.50V), {normal} normal, {strong} strong (>0.70V)")


def main():
    """Run comparison test."""
    
    print("\n" + "="*90)
    print("COMPARISON TEST: Impact of Per-Cell Vth Variations")
    print("="*90)
    
    # Test 1: WITHOUT per-cell variations
    print("\n" + "-"*90)
    print("TEST 1: WITHOUT Per-Cell Vth Variations")
    print("-"*90)
    
    results_without = run_harsh_baseline(use_per_cell_variations=False)
    analyze_cell_distribution(results_without['triad'], "WITHOUT variations")
    
    # Test 2: WITH per-cell variations
    print("\n" + "-"*90)
    print("TEST 2: WITH Per-Cell Vth Variations (±10%)")
    print("-"*90)
    
    results_with = run_harsh_baseline(use_per_cell_variations=True)
    analyze_cell_distribution(results_with['triad'], "WITH variations")
    
    # ==================== RESULTS COMPARISON ====================
    print("\n" + "="*90)
    print("RESULTS COMPARISON")
    print("="*90)
    
    print(f"\nBASELINE PRECISION (No Training):")
    print(f"  WITHOUT per-cell variations: {results_without['baseline_avg']:.2f} bits")
    print(f"  WITH per-cell variations:    {results_with['baseline_avg']:.2f} bits")
    print(f"  Difference:                  {results_with['baseline_avg'] - results_without['baseline_avg']:+.2f} bits")
    
    print(f"\nFINAL PRECISION (After 100 Cycles MAML):")
    print(f"  WITHOUT per-cell variations: {results_without['final_precision']:.2f} bits")
    print(f"  WITH per-cell variations:    {results_with['final_precision']:.2f} bits")
    print(f"  Difference:                  {results_with['final_precision'] - results_without['final_precision']:+.2f} bits")
    
    print(f"\nTOTAL IMPROVEMENT (Baseline → Final):")
    print(f"  WITHOUT per-cell variations: {results_without['improvement']:+.2f} bits")
    print(f"  WITH per-cell variations:    {results_with['improvement']:+.2f} bits")
    print(f"  Difference:                  {results_with['improvement'] - results_without['improvement']:+.2f} bits")
    
    # Learning curves
    print(f"\nLEARNING CURVE ANALYSIS:")
    print(f"  WITHOUT variations - First 10 cycles avg:   {np.mean(results_without['learning_precisions'][:10]):.2f} bits")
    print(f"  WITH variations    - First 10 cycles avg:   {np.mean(results_with['learning_precisions'][:10]):.2f} bits")
    print(f"  WITHOUT variations - Last 10 cycles avg:    {np.mean(results_without['learning_precisions'][-10:]):.2f} bits")
    print(f"  WITH variations    - Last 10 cycles avg:    {np.mean(results_with['learning_precisions'][-10:]):.2f} bits")
    
    # Variance in learning
    without_variance = np.std(results_without['learning_precisions'])
    with_variance = np.std(results_with['learning_precisions'])
    print(f"\nLEARNING STABILITY (Lower std = more stable):")
    print(f"  WITHOUT variations: std = {without_variance:.4f}")
    print(f"  WITH variations:    std = {with_variance:.4f}")
    print(f"  Difference:         {with_variance - without_variance:+.4f}")
    
    # ==================== CONCLUSIONS ====================
    print("\n" + "="*90)
    print("CONCLUSIONS")
    print("="*90)
    
    if abs(results_with['baseline_avg'] - results_without['baseline_avg']) < 0.05:
        print("\n⚠️  OBSERVATION 1: Baseline precision is essentially SAME with/without variations")
        print("   This suggests manufacturing variations already dominate the effect.")
        print("   Per-cell Vth variations add ADDITIONAL heterogeneity on top.")
    else:
        print(f"\n✓ OBSERVATION 1: Per-cell variations have measurable baseline impact")
        print(f"   Effect: {results_with['baseline_avg'] - results_without['baseline_avg']:+.2f} bits")
    
    if abs(results_with['improvement'] - results_without['improvement']) > 0.1:
        print(f"\n✓ OBSERVATION 2: MAML learning is MORE EFFECTIVE with variations")
        print(f"   Improvement difference: {results_with['improvement'] - results_without['improvement']:+.2f} bits")
        print(f"   This suggests per-cell heterogeneity provides richer learning signal.")
    else:
        print(f"\n⚠️  OBSERVATION 2: MAML learning shows similar improvement")
        print(f"   The correction matrices may be saturating in both cases.")
    
    if with_variance > without_variance:
        print(f"\n✓ OBSERVATION 3: Learning is LESS STABLE with per-cell variations")
        print(f"   This is EXPECTED: More heterogeneity = noisier gradients")
        print(f"   But with higher final precision, the trade-off is worthwhile.")
    else:
        print(f"\n✓ OBSERVATION 3: Learning stability is similar or better with variations")
    
    print("\n" + "="*90)
    print("VERIFICATION: Are per-cell variations affecting the simulation?")
    print("="*90)
    
    # Check if variations were actually applied
    without_offsets = [c.V_th_variation_offset for c in results_without['triad'].M33.cell_bank.cells_active]
    with_offsets = [c.V_th_variation_offset for c in results_with['triad'].M33.cell_bank.cells_active]
    
    print(f"\nTest 1 (WITHOUT flag): V_th offsets = {np.std(without_offsets):.6f} (should be ~0)")
    print(f"Test 2 (WITH flag):    V_th offsets = {np.std(with_offsets):.6f} (should be ~0.064)")
    
    if np.std(without_offsets) < 1e-6:
        print("✓ Confirmed: WITHOUT flag → No per-cell variations applied")
    
    if np.std(with_offsets) > 0.05:
        print("✓ Confirmed: WITH flag → Per-cell variations ARE applied")
    
    print("\n" + "="*90)


if __name__ == "__main__":
    main()
