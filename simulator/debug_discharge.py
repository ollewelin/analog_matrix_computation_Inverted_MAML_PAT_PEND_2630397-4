"""Debug: Check if cell discharge kills M3 output"""

import numpy as np
from matrix_core import AtomicTriad
from maml_optimizer import create_test_vectors

# Setup
x_train, y_train = create_test_vectors(num_vectors=1, dimension=6, seed=42)
x = x_train[0]

# Create system
triad = AtomicTriad(size=6)

print("="*70)
print("DEBUG: M3 Output During Discharge Cycle")
print("="*70)

triad.refresh_cycle()

# Simulate the stratified measurement loop
stratum_duration_ms = 1.0  # 1ms per stratum (10ms / 10)

for stratum in range(11):
    t_ms = stratum * stratum_duration_ms
    
    output, diag = triad.forward(x, t_snapshot_ms=t_ms)
    
    print(f"\nStratum {stratum} (t={t_ms:.1f}ms):")
    print(f"  y_m3_raw: {diag['y_m3_raw']}")
    print(f"  y_m3_raw norm: {np.linalg.norm(diag['y_m3_raw']):.4e}")
    print(f"  M3 weight sample: {triad.M3.weights[0,0]:.4f}")
    print(f"  y_payload: {diag['y_payload'][:3]} ...")
    print(f"  y_correction: {diag['y_correction'][:3]} ...")
    print(f"  output (normalized): {output[:3]} ...")
    
    # Discharge cells for next stratum
    if stratum < 10:
        triad.discharge_step(stratum_duration_ms)
