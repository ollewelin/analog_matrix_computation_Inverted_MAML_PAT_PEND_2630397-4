"""
Clean Diagnostic: Velocity Saturation Effect in Isolation
==========================================================

Test velocity saturation WITHOUT manufacturing variations to isolate the effect.
"""

import numpy as np
from matrix_core import AtomicTriad


def measure_clean_baseline(v_sat_param: float, num_cycles: int = 5, 
                           num_samples: int = 16, seed: int = 42):
    """Measure baseline precision without manufacturing variations."""
    
    np.random.seed(seed)
    X = np.random.uniform(0, 1, size=(num_samples, 32))
    Y = X.copy()
    
    # Initialize triad
    triad = AtomicTriad(size=32, v_sat_param=v_sat_param)
    
    # NO manufacturing variations - just velocity saturation
    
    # Fix M3/M8 at center
    triad.M3.weights.fill(2.6)
    triad.M8.weights.fill(2.6)
    
    # Measure over multiple cycles
    precisions = []
    for cycle in range(num_cycles):
        losses = []
        for x, y in zip(X, Y):
            output, _ = triad.forward(x)
            error = output - y
            loss = np.mean(error ** 2)
            losses.append(loss)
        
        avg_loss = np.mean(losses)
        precision = -np.log2(avg_loss + 1e-8)
        precisions.append(precision)
    
    return np.mean(precisions), np.std(precisions)


print("\n" + "=" * 80)
print("CLEAN BASELINE: Velocity Saturation Isolated")
print("=" * 80)

print("\nMeasuring baseline precision with/without velocity saturation...")
print("  - NO manufacturing variations")
print("  - Only velocity saturation effect")
print("  - 32×32 matrix, 5 cycles, 16 samples/cycle")
print()

# Measure baseline with v_sat = 0.0 (ideal)
print("Test 1: Ideal model (v_sat = 0.0)")
mean_ideal, std_ideal = measure_clean_baseline(v_sat_param=0.0)
print(f"  Precision: {mean_ideal:.2f} ± {std_ideal:.3f} bits")

# Measure baseline with v_sat = 0.15 (realistic)
print("\nTest 2: Realistic model (v_sat = 0.15)")
mean_realistic, std_realistic = measure_clean_baseline(v_sat_param=0.15)
print(f"  Precision: {mean_realistic:.2f} ± {std_realistic:.3f} bits")

degradation = mean_ideal - mean_realistic
degradation_pct = degradation / mean_ideal * 100 if mean_ideal > 0 else 0

print(f"\nVelocity Saturation Effect (CLEAN):")
print(f"  Precision loss: {degradation:.2f} bits ({degradation_pct:.1f}%)")

print("\n" + "=" * 80)
print("DIAGNOSIS")
print("=" * 80)

if degradation < 0.1:
    print("""
✗ PROBLEM IDENTIFIED:
  - Velocity saturation parameter (0.15) is TOO SMALL
  - Having almost no effect on baseline precision
  - This suggests we're in the linear region (low V_ds)
  
SOLUTION: Need to increase v_sat_param for realistic effect
  - Try v_sat_param = 0.30 or 0.50
  - Or change how E_field is computed
  - Make the saturation effect MUCH stronger
  """)
else:
    print(f"""
✓ GOOD: Velocity saturation has measurable effect
  - {degradation:.2f} bits degradation is realistic
  - Parameters seem reasonable
    """)

print("=" * 80)
