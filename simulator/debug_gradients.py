"""Debug: Analyze why gradients stall training"""

import numpy as np
from matrix_core import AtomicTriad
from maml_optimizer import InvertedMAML, create_test_vectors

# Setup
x_train, y_train = create_test_vectors(num_vectors=1, dimension=6, seed=42)
x = x_train[0]
y_target = y_train[0]

# Create system
triad = AtomicTriad(size=6)
maml = InvertedMAML(triad, learning_rate=0.1)

print("="*70)
print("DEBUG: Gradient Analysis")
print("="*70)

# Cycle 0
print("\n--- CYCLE 0 (Initial) ---")
triad.refresh_cycle()
output_0, diag = triad.forward(x)
error_0 = output_0 - y_target
loss_0 = 0.5 * np.sum(error_0 ** 2)
print(f"Output: {output_0}")
print(f"Target: {y_target}")
print(f"Error:  {error_0}")
print(f"Loss:   {loss_0:.4e}")
print(f"M3 weights range: [{triad.M3.weights.min():.4f}, {triad.M3.weights.max():.4f}]")
print(f"M8 weights range: [{triad.M8.weights.min():.4f}, {triad.M8.weights.max():.4f}]")

# Compute gradients manually
grad_M3, grad_M8, loss = maml.compute_stratified_gradient(x, y_target)
print(f"\nGradients after cycle 0:")
print(f"  grad_M3 norm: {np.linalg.norm(grad_M3):.4e}")
print(f"  grad_M8 norm: {np.linalg.norm(grad_M8):.4e}")
print(f"  grad_M3 range: [{grad_M3.min():.4e}, {grad_M3.max():.4e}]")
print(f"  grad_M8 range: [{grad_M8.min():.4e}, {grad_M8.max():.4e}]")

# Update
loss_1 = maml.update_weights(x, y_target)
print(f"\nAfter weight update:")
print(f"  Loss: {loss_1:.4e}")
print(f"  M3 weights changed? {np.any(triad.M3.weights != diag['M3_weights'])}")
print(f"  M3 delta: {np.max(np.abs(triad.M3.weights - diag['M3_weights'])):.4e}")

# Cycle 1
print("\n--- CYCLE 1 (After 1 update) ---")
triad.refresh_cycle()
output_1, diag = triad.forward(x)
error_1 = output_1 - y_target
loss = 0.5 * np.sum(error_1 ** 2)
print(f"Output: {output_1}")
print(f"Error:  {error_1}")
print(f"Loss:   {loss:.4e}")
print(f"Loss change: {loss - loss_0:.4e}")

grad_M3, grad_M8, loss = maml.compute_stratified_gradient(x, y_target)
print(f"\nGradients after cycle 1:")
print(f"  grad_M3 norm: {np.linalg.norm(grad_M3):.4e}")
print(f"  grad_M8 norm: {np.linalg.norm(grad_M8):.4e}")

# Check tanh saturation
print("\n--- TANH SATURATION CHECK ---")
for cycle in range(5):
    triad.refresh_cycle()
    output, diag = triad.forward(x, t_snapshot_ms=5.0)
    y_m3_raw = diag['y_m3_raw']
    y_m3_hidden = diag['y_m3_hidden']
    print(f"Cycle {cycle}:")
    print(f"  y_m3_raw range: [{y_m3_raw.min():.4f}, {y_m3_raw.max():.4f}]")
    print(f"  y_m3_hidden range: [{y_m3_hidden.min():.4f}, {y_m3_hidden.max():.4f}]")
    print(f"  tanh saturation: {np.sum(np.abs(y_m3_hidden) > 0.9)}/6 neurons")
    if cycle < 4:
        maml.update_weights(x, y_target)
