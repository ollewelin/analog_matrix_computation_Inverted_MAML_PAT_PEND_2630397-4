#!/usr/bin/env python3
"""
run_card1_bit_slicing_serial.py
================================
Alternativ A: 1 Card, 2-Step Serial Analog Bit Slicing on Inverted MAML Silicon.

Protocol:
1. Card 1 operates with fixed Mode A SGD running to keep analog operating point stable.
2. Given a target 8-bit digital matrix W_8bit in range [-128, +127]:
   - We split into 4-bit MSB slice and 4-bit LSB slice:
     W_MSB = (W_8bit >> 4)      # range [-8, +7]
     W_LSB = (W_8bit & 0x0F)     # range [0, 15] or zero-centered [-8, +7]
   - Each slice is mapped to physical M33 matrix weights (scaled appropriately to [-60, +60] LSB).
3. Given an input vector X:
   - Step 1 (MSB Phase): Load W_MSB onto M33. Run analog dot-product Y_msb_raw.
   - Step 2 (LSB Phase): Load W_LSB onto M33. Run analog dot-product Y_lsb_raw.
4. Shift-and-Add Recombination:
   - Strictly NO digital moving-target patches or alpha/beta per-column tricks!
   - Ideal digital target: Y_target = X @ W_8bit.
   - Combined analog reconstruction:
     Y_recon = (Y_msb_scaled << 4) + Y_lsb_scaled.
   - Compare naive raw recombination vs. grid-rounded (integer restored) recombination.
   - Calculate ENOB for MSB slice, LSB slice, naive combined, and restored combined.

Usage:
    python FPGA_code/scripts/run_card1_bit_slicing_serial.py --num-vectors 100 --w-scale 60
"""

import sys
import os
import time
import argparse
import numpy as np
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scripts.t120_client import T120Client

def build_8bit_benchmark_matrix():
    """
    Creates a fixed non-trivial 6x6 8-bit integer matrix W_8b in range [-120, +120].
    """
    np.random.seed(42)
    # 6x6 matrix with varied dynamic range and polarity
    W = np.array([
        [ 95, -45,  60, -80,  30, -15],
        [-30,  85, -50,  40, -90,  65],
        [ 70, -60,  90, -35,  45, -75],
        [-85,  40, -65, 100, -20,  50],
        [ 50, -75,  35, -60,  80, -40],
        [-65,  55, -40,  70, -50,  95]
    ], dtype=np.int32)
    return W

def slice_matrix_4bit(W_8b):
    """
    Splits 8-bit integer matrix into MSB (4 bits) and LSB (4 bits).
    W_8b = 16 * W_msb + W_lsb
    Where W_msb in [-8, 7], W_lsb in [0, 15] (or centered [-8, 7] with carry).
    Using simple arithmetic:
      W_msb = np.floor_divide(W_8b + 8, 16)
      W_lsb = W_8b - 16 * W_msb   # in [-8, 7]
    Check: 16 * W_msb + W_lsb == W_8b identically!
    """
    W_msb = np.floor_divide(W_8b + 8, 16).astype(np.int32)
    W_lsb = (W_8b - 16 * W_msb).astype(np.int32)
    assert np.all(16 * W_msb + W_lsb == W_8b), "Slicing decomposition error!"
    return W_msb, W_lsb

def main():
    parser = argparse.ArgumentParser(description="Card 1 Serial Analog Bit Slicing")
    parser.add_argument("--ip", type=str, default="192.168.1.50")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--num-vectors", type=int, default=50, help="Number of test epochs/vectors")
    parser.add_argument("--delay-ms", type=float, default=5.2, help="Snapshot delay in ms")
    parser.add_argument("--out-json", type=str, default="FPGA_code/logs/bit_slicing/card1_serial_8bit_test.json")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.out_json), exist_ok=True)

    print(f"================================================================")
    print(f"  CARD 1 SERIAL ANALOG BIT SLICING (Alternativ A)")
    print(f"  Target: 8-bit matrix multiplication decomposed into 2x 4-bit slices")
    print(f"  IP: {args.ip}:{args.port} | Delay: {args.delay_ms} ms")
    print(f"================================================================")

    # 1. Prepare benchmark matrix and slices
    W_8b = build_8bit_benchmark_matrix()
    W_msb, W_lsb = slice_matrix_4bit(W_8b)

    print(f"\n[Matrix Slicing Details]")
    print(f"W_8b range : [{W_8b.min()}, {W_8b.max()}] LSB")
    print(f"W_msb range: [{W_msb.min()}, {W_msb.max()}] (4-bit signed)")
    print(f"W_lsb range: [{W_lsb.min()}, {W_lsb.max()}] (4-bit signed)")

    # Physical scaling factor for silicon:
    # 4-bit weights are in [-8, +7]. To scale them to analog dynamic range [-56, +49]:
    # weight_gain = 7
    WEIGHT_SCALE = 7
    W_msb_silicon = (W_msb * WEIGHT_SCALE).astype(np.int32)
    W_lsb_silicon = (W_lsb * WEIGHT_SCALE).astype(np.int32)

    print(f"W_msb_silicon range: [{W_msb_silicon.min()}, {W_msb_silicon.max()}] LSB on M33")
    print(f"W_lsb_silicon range: [{W_lsb_silicon.min()}, {W_lsb_silicon.max()}] LSB on M33")

    client = T120Client(host=args.ip, port=args.port)

    # Generate fixed random test vectors (small integers, e.g. [-8, 7] or [-4, 4] for 4-bit input)
    np.random.seed(1337)
    # Using 4-bit input activations [-7, 7]
    X_test = np.random.randint(-7, 8, size=(args.num_vectors, 6), dtype=np.int32)

    # Physical input line scaling (DAC swing):
    # e.g., input_scale = 10 -> [-70, +70] LSB differential on data lines
    INPUT_SCALE = 10
    
    # Store results
    results = []

    print(f"\nStarting 2-Step Serial Evaluation across {args.num_vectors} vectors...")

    for v_idx in range(args.num_vectors):
        x_vec = X_test[v_idx]
        x_dac = x_vec * INPUT_SCALE

        # Exact Digital Targets
        y_msb_ideal = np.dot(x_vec, W_msb)
        y_lsb_ideal = np.dot(x_vec, W_lsb)
        y_total_ideal = np.dot(x_vec, W_8b) # identically = 16 * y_msb_ideal + y_lsb_ideal

        # -------------------------------------------------------------
        # STEP 1: MSB Slice on Card 1
        # -------------------------------------------------------------
        client.set_w33_matrix(W_msb_silicon)
        time.sleep(0.005) # Settling time
        
        # Inject test vector and measure ADC response
        resp_msb = client.evaluate_vector(x_dac, delay_ms=args.delay_ms)
        y_msb_raw = np.array(resp_msb['adc45_cols'], dtype=np.float64)

        # -------------------------------------------------------------
        # STEP 2: LSB Slice on Card 1
        # -------------------------------------------------------------
        client.set_w33_matrix(W_lsb_silicon)
        time.sleep(0.005) # Settling time

        resp_lsb = client.evaluate_vector(x_dac, delay_ms=args.delay_ms)
        y_lsb_raw = np.array(resp_lsb['adc45_cols'], dtype=np.float64)

        results.append({
            "vector_idx": v_idx,
            "x": x_vec.tolist(),
            "y_msb_ideal": y_msb_ideal.tolist(),
            "y_lsb_ideal": y_lsb_ideal.tolist(),
            "y_total_ideal": y_total_ideal.tolist(),
            "y_msb_raw": y_msb_raw.tolist(),
            "y_lsb_raw": y_lsb_raw.tolist()
        })

        if (v_idx + 1) % 10 == 0 or v_idx == args.num_vectors - 1:
            print(f"  Vector {v_idx+1:3d}/{args.num_vectors}: MSB & LSB slices collected.")

    # Save raw measurements
    with open(args.out_json, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n[DONE] Saved {len(results)} vector evaluations to {args.out_json}")

if __name__ == "__main__":
    main()
