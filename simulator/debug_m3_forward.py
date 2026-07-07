"""Debug: Detailed M3 forward pass analysis"""

import numpy as np
from matrix_core import AtomicTriad
from maml_optimizer import create_test_vectors

# Setup
x_train, y_train = create_test_vectors(num_vectors=1, dimension=6, seed=42)
x = x_train[0]

# Create system
triad = AtomicTriad(size=6)

print("="*70)
print("DEBUG: M3 Forward Pass Analysis")
print("="*70)

print("\n--- M3 Weights ---")
print(f"M3 weights shape: {triad.M3.weights.shape}")
print(f"M3 weights:\n{triad.M3.weights}")
print(f"M3 weights range: [{triad.M3.weights.min():.4f}, {triad.M3.weights.max():.4f}]")

print("\n--- Input ---")
print(f"x_input: {x}")
print(f"x range: [{x.min():.4f}, {x.max():.4f}]")

print("\n--- Manual M3 Multiplication ---")
# Manually compute what should happen
V_source = 1.65
V_ds = V_source + x * 0.25
print(f"V_ds: {V_ds}")
print(f"V_ds range: [{V_ds.min():.4f}, {V_ds.max():.4f}]")

# Check cell computation
cell = triad.M3.cell_bank.cells_active[0]
print(f"\nCell [0,0] properties:")
print(f"  V_gs (from weight): {cell.V_gs:.4f}")
print(f"  g_m_scale: {cell.g_m_scale:.4e}")
print(f"  V_th: {cell.V_th:.4f}")
print(f"  computing with V_ds={V_ds[0]:.4f}")
I_out = cell.compute_output(V_ds[0])
print(f"  I_out: {I_out:.4e}")

print("\n--- M3 Forward Pass ---")
triad.refresh_cycle()
y_m3, diag = triad.M3.forward(x)
print(f"y_m3: {y_m3}")
print(f"y_m3 range: [{y_m3.min():.4e}, {y_m3.max():.4e}]")
print(f"y_m3 != 0? {np.any(y_m3 != 0)}")

print("\n--- AtomicTriad Forward Pass ---")
triad.refresh_cycle()
output, diag_triad = triad.forward(x)
print(f"y_m3_raw from diagnostics: {diag_triad['y_m3_raw']}")
print(f"y_payload: {diag_triad['y_payload']}")
print(f"y_correction: {diag_triad['y_correction']}")
print(f"output (normalized): {output}")
