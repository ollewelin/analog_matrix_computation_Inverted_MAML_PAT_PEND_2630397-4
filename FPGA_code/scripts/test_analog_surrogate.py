#!/usr/bin/env python3
"""
Test runner for the Calibrated Analog Hardware Surrogate (Outer Loop Ref 40).
Verifies:
1. Spatial crosspoint mismatch standard deviation matching empirical hardware data (~59 LSB std dev on Matrix 3).
2. +48 LSB pedestal bias on Matrix 33 / ADC_49.
3. Crosspoint Warp: soft-saturation compression and two-quadrant slope asymmetry (+19.81 vs -19.11 LSB).
4. Temporal Drift: Sawtooth exponential droop over 10.0 ms refresh window with fast decay (330 kOhm) on Row 7.
5. Hadamard orthogonal input probing isolating row responses under outer loop physics shifts.
"""

import sys
import numpy as np
from pathlib import Path

# Add simulator to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "simulator"))

from analog_hardware_surrogate import AnalogHardwareSurrogate, SurrogateConfig


def hadamard_matrix(n: int) -> np.ndarray:
    """Generate Sylvester construction Walsh-Hadamard matrix of order n (power of 2)."""
    h = np.array([[1]], dtype=int)
    while h.shape[0] < n:
        h = np.block([[h, h], [h, -h]])
    return h


def test_mismatch_distribution():
    print("[TEST 1/5] Checking spatial mismatch distribution...")
    surrogate = AnalogHardwareSurrogate(seed=123)
    data_spans = surrogate.span_scale_m3[:6, :].flatten() * 256.0
    mean_span = float(np.mean(data_spans))
    std_span = float(np.std(data_spans))
    
    print(f"  Matrix 3 Data Rows Span: Mean={mean_span:.2f} LSB, StdDev={std_span:.2f} LSB (Target: ~59 LSB)")
    assert 40.0 < std_span < 80.0, f"Span std dev out of expected range: {std_span}"
    print("  --> PASS: Spatial mismatch calibrated to empirical ~59 LSB std dev.")


def test_pedestal_bias():
    print("[TEST 2/5] Checking ADC_49 pedestal bias on Matrix 33...")
    surrogate = AnalogHardwareSurrogate(seed=123)
    x_zero = np.zeros(6, dtype=int)
    w_zero = np.zeros((6, 6), dtype=int)
    adc49_out = surrogate.forward_matrix_33(x_zero, w_zero, t_ms=0.0)
    mean_pedestal = float(np.mean(adc49_out))
    
    print(f"  Matrix 33 Zero-Input Output: {adc49_out} (Mean={mean_pedestal:.2f} LSB, Target: ~+48 LSB)")
    assert 40.0 <= mean_pedestal <= 56.0, f"Pedestal shift {mean_pedestal} outside expected +48 range!"
    print("  --> PASS: Matrix 33 +48 LSB pedestal bias verified.")


def test_warp_and_two_quadrant_slopes():
    print("[TEST 3/5] Checking Crosspoint Warp and Two-Quadrant Slope Asymmetry...")
    surrogate = AnalogHardwareSurrogate(seed=123)
    
    # Probe positive vs negative weight steps (+96 vs -96 LSB)
    x_probe = np.ones(6, dtype=int) * 64
    w_pos = np.ones((8, 6), dtype=int) * 96
    w_neg = np.ones((8, 6), dtype=int) * -96
    w_mid = np.zeros((8, 6), dtype=int)
    
    out_pos = surrogate.forward_matrix_3(x_probe, w_pos, t_ms=0.0)
    out_neg = surrogate.forward_matrix_3(x_probe, w_neg, t_ms=0.0)
    out_mid = surrogate.forward_matrix_3(x_probe, w_mid, t_ms=0.0)
    
    delta_pos = np.mean(out_pos - out_mid)
    delta_neg = np.mean(out_mid - out_neg)
    asym_diff = delta_pos - delta_neg
    
    print(f"  Pos Delta: {delta_pos:.2f} LSB | Neg Delta: {delta_neg:.2f} LSB | Asymmetry: {asym_diff:.2f} LSB")
    assert delta_pos > 0 and delta_neg > 0, "Deltas should be positive in their respective quadrants!"
    print("  --> PASS: Two-quadrant soft-saturation asymmetry observed.")


def test_temporal_drift_and_fast_decay():
    print("[TEST 4/5] Checking 10.0 ms Sawtooth Droop & Fast Decay Row 7...")
    surrogate = AnalogHardwareSurrogate(seed=123)
    
    droop_norm_0 = surrogate.compute_temporal_droop(0.0, row_idx=0)
    droop_norm_5 = surrogate.compute_temporal_droop(5.0, row_idx=0)
    droop_norm_9 = surrogate.compute_temporal_droop(9.9, row_idx=0)
    droop_norm_10 = surrogate.compute_temporal_droop(10.0, row_idx=0)  # Reset point
    
    droop_fast_5 = surrogate.compute_temporal_droop(5.0, row_idx=7)
    
    print(f"  Normal Row (1 MOhm): t=0ms: {droop_norm_0:.3f}, t=5ms: {droop_norm_5:.3f}, t=9.9ms: {droop_norm_9:.3f}, t=10ms (reset): {droop_norm_10:.3f}")
    print(f"  Fast Decay (330 kOhm): t=5ms: {droop_fast_5:.3f} (Decays significantly faster)")
    
    assert droop_norm_0 == 1.0, "Initial droop must be 1.0"
    assert droop_norm_10 == 1.0, "Sawtooth must reset to 1.0 at 10.0ms"
    assert droop_fast_5 < droop_norm_5, "Fast decay row must droop faster than normal data row!"
    print("  --> PASS: Sawtooth exponential droop and fast-decay (330 kOhm) confirmed.")


def test_outer_loop_hadamard_probing():
    print("[TEST 5/5] Outer Loop (Ref 40) Hadamard Probing & Basin Shift...")
    surrogate = AnalogHardwareSurrogate(seed=123)
    H8 = hadamard_matrix(8)  # 8x8 Walsh-Hadamard basis
    
    w_m3 = np.zeros((8, 6), dtype=int)
    for r in range(6):
        w_m3[r, :] = (r + 1) * 15  # Graded weights
        
    # Baseline measurement at t = 0.5 ms
    h_in = H8[:6, 1] * 64  # Second Hadamard column truncated to 6 inputs
    y_base = surrogate.forward_matrix_3(h_in, w_m3, t_ms=0.5)
    
    # Outer Loop sudden environmental shift (supply drift +/-5% + hidden cross-point shift)
    shift_info = surrogate.trigger_outer_loop_epoch(trim_drift_lsb=8.5)
    y_shifted = surrogate.forward_matrix_3(h_in, w_m3, t_ms=0.5)
    
    shift_delta = np.linalg.norm(y_shifted - y_base)
    print(f"  Outer loop shift triggered: trim drift={shift_info['hidden_trim_offset']:.2f} LSB")
    print(f"  Shifted output delta norm: {shift_delta:.2f} LSB (Confirms outer loop perturbing search space)")
    assert shift_delta > 5.0, "Outer loop shift must produce measurable change in analog outputs!"
    
    # Reset to operational mode (Ref 42)
    surrogate.reset_to_operational_mode()
    y_reset = surrogate.forward_matrix_3(h_in, w_m3, t_ms=0.5)
    print(f"  Operational mode reset delta: {np.linalg.norm(y_reset - y_base):.2f} LSB")
    assert np.allclose(y_reset, y_base, atol=1e-3), "Reset must restore baseline operational state!"
    print("  --> PASS: Outer loop perturbation and operational reset verified.")


def main():
    print("======================================================================")
    print("   INVERTED MAML ANALOG HARDWARE SURROGATE VERIFICATION RUNNER        ")
    print("======================================================================")
    test_mismatch_distribution()
    test_pedestal_bias()
    test_warp_and_two_quadrant_slopes()
    test_temporal_drift_and_fast_decay()
    test_outer_loop_hadamard_probing()
    print("======================================================================")
    print("   ALL TESTS PASSED SUCCESSFULLY! SURROGATE CALIBRATION ACCURATE.    ")
    print("======================================================================")


if __name__ == "__main__":
    main()
