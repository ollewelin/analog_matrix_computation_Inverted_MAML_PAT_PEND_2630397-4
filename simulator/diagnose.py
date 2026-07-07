#!/usr/bin/env python3
"""
Diagnostic: Check if gradient computation and weight updates work
"""

import numpy as np
from matrix_core import AtomicTriad
from maml_optimizer import InvertedMAML, create_test_vectors

# Create triad
triad = AtomicTriad(size=6)

# Generate test
x_train, y_train = create_test_vectors(num_vectors=2, dimension=6, seed=42)

# Create MAML
maml = InvertedMAML(triad, learning_rate=0.1, num_strata=10)

print("=" * 70)
print("DIAGNOSTIC: Weight Update Check")
print("=" * 70)

# Take first sample
x_sample = x_train[0]
y_sample = y_train[0]

print(f"\nInput shape: {x_sample.shape}")
print(f"Target shape: {y_sample.shape}")
print(f"Target values: {y_sample}")

# Initial weights
W_M3_init = triad.M3.weights.copy()
W_M8_init = triad.M8.weights.copy()

print(f"\nInitial M3 weight range: [{W_M3_init.min():.4f}, {W_M3_init.max():.4f}]")
print(f"Initial M8 weight range: [{W_M8_init.min():.4f}, {W_M8_init.max():.4f}]")

# Forward pass
output_before, diag = triad.forward(x_sample, t_snapshot_ms=5.0)
print(f"\nForward pass output: {output_before}")
print(f"Output range: [{output_before.min():.6f}, {output_before.max():.6f}]")

# Compute error
error = output_before - y_sample
loss = 0.5 * np.sum(error ** 2)
print(f"\nError: {error}")
print(f"Error range: [{error.min():.6f}, {error.max():.6f}]")
print(f"Loss: {loss:.6e}")

# Compute gradients manually
grad_M3, grad_M8 = maml._backprop_corrections(error, diag, x_sample)

print(f"\nGradient M3:")
print(f"  Shape: {grad_M3.shape}")
print(f"  Range: [{grad_M3.min():.6f}, {grad_M3.max():.6f}]")
print(f"  Norm: {np.linalg.norm(grad_M3):.6e}")
print(f"  Sample values: {grad_M3[0, :3]}")

print(f"\nGradient M8:")
print(f"  Shape: {grad_M8.shape}")
print(f"  Range: [{grad_M8.min():.6f}, {grad_M8.max():.6f}]")
print(f"  Norm: {np.linalg.norm(grad_M8):.6e}")

# Update weights manually
lr = 0.1
W_M3_updated = W_M3_init - lr * grad_M3
W_M8_updated = W_M8_init - lr * grad_M8

print(f"\nWeight updates (lr={lr}):")
print(f"  M3 delta range: [{(W_M3_updated - W_M3_init).min():.6f}, {(W_M3_updated - W_M3_init).max():.6f}]")
print(f"  M8 delta range: [{(W_M8_updated - W_M8_init).min():.6f}, {(W_M8_updated - W_M8_init).max():.6f}]")

# Set updated weights
triad.set_correction_weights(W_M3_updated, W_M8_updated)

# Forward pass with updated weights
triad.refresh_cycle()
output_after, _ = triad.forward(x_sample, t_snapshot_ms=5.0)
print(f"\nOutput after update: {output_after}")

error_after = output_after - y_sample
loss_after = 0.5 * np.sum(error_after ** 2)

print(f"Loss after update: {loss_after:.6e}")
print(f"Loss improvement: {loss - loss_after:.6e} ({100*(loss-loss_after)/loss:.1f}%)")

if abs(loss - loss_after) < 1e-10:
    print("\n⚠ WARNING: No loss improvement detected!")
    print("  This suggests gradients may not be flowing correctly.")
else:
    print(f"\n✓ Learning working! Loss decreased.")

print("\n" + "=" * 70)
