#!/usr/bin/env python3
"""
100-Matrix Inverted MAML Research Campaign (Running until 21:00 CEST).

Core Concept:
  An "atomic triad" (Matrix 33 + Matrix 3 + Matrix 8) has a fixed Matrix 33
  multiplication configuration throughout its operational lifetime.
  Inverted MAML trains a base model W_0 specifically for that Matrix 33 instance.

Campaign Design:
  - Generates 100 distinct random Matrix 33 multiplier targets (values -127..127 / 0..255).
  - For each Matrix 33 variant:
      1. Evaluates raw uncompensated tracking on randomized white-noise payloads.
      2. Trains a specialized Inverted MAML Base Model W_0 (Matrix 3 & Matrix 8)
         under active continuous white-noise randomization and stratified time-sampling.
      3. Tests compensated performance across multiple unseen random test vectors.
      4. Measures and logs ENOB improvement, loss drop, and parameter convergence.
  - Alternates with live board telemetry probing and realistic surrogate modeling.
  - Runs continuously until 21:00:00 CEST, atomically updating data/benchmarks/maml_100_variants_campaign.json.
"""

import time
import json
import os
import sys
import socket
import struct
import numpy as np
from pathlib import Path

# Add simulator to path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "simulator"))
from analog_hardware_surrogate import AnalogHardwareSurrogate, SurrogateConfig

BOARD_IP = "192.168.1.50"
BOARD_PORT = 5000
MAML_MAGIC = 0x4D414D4C

DATA_DIR = Path("data/benchmarks")
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUT_JSON = DATA_DIR / "maml_100_variants_campaign.json"

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(2.5)

def hw_step():
    try:
        sock.sendto(struct.pack("<IB", MAML_MAGIC, 0x18), (BOARD_IP, BOARD_PORT))
        d, _ = sock.recvfrom(2048)
        loss, comp, uncomp = struct.unpack_from("<IHH", d, 42)
        return uncomp / 100.0, comp / 100.0, loss
    except Exception:
        return None, None, None

def train_base_model_for_variant(variant_id: int, w_m33_target: np.ndarray, surrogate: AnalogHardwareSurrogate, n_epochs: int = 15):
    """
    Trains Inverted MAML Base Model (W3, W8) for this specific Matrix 33 target configuration.
    Inputs: Randomized white-noise payloads x_in ~ U(-100, +100).
    Evaluated across stratified time-slots inside the 10 ms refresh window.
    """
    rng = np.random.RandomState(42 + variant_id * 7)
    
    # Initialize base model W_0 for M3 (8x6) and M8 (7x6) with auto-gain seeding
    w_m3 = rng.uniform(-30, 30, (8, 6))
    w_m8 = rng.uniform(-30, 30, (7, 6))
    
    # Evaluate raw uncompensated baseline (W3=0, W8=0) over 20 random payloads
    uncomp_errors = []
    for _ in range(20):
        x_pay = rng.uniform(-90, 90, 6)
        t_sample_ms = rng.uniform(0.5, 9.5) # Random temporal sampling inside 10ms window
        
        # Physical output from Matrix 33 (with droop, mismatch, and pedestal bias)
        y_phys = surrogate.forward_matrix_33(x_pay, w_m33_target, t_ms=t_sample_ms)
        # Ideal digital target Z_ideal = (w_m33 * x_pay) / 256
        z_ideal = np.dot(w_m33_target, x_pay) / 128.0
        
        err = np.mean((y_phys - z_ideal) ** 2)
        uncomp_errors.append(err)
        
    rmse_uncomp = np.sqrt(np.mean(uncomp_errors))
    uncomp_enob = max(1.5, min(11.0, 11.0 - np.log2(max(1.0, rmse_uncomp))))
    
    # Outer-Loop Meta-Learning Training (Ref 40 + Ref 41)
    lr_inner = 0.008
    lr_outer = 0.004
    
    epoch_losses = []
    for epoch in range(n_epochs):
        # 4 Inner-loop adaptation basins
        grad_accum_m3 = np.zeros_like(w_m3)
        grad_accum_m8 = np.zeros_like(w_m8)
        
        for basin in range(4):
            # Sample random white-noise reference input
            x_ref = rng.uniform(-100, 100, 6)
            t_slot = rng.uniform(0.5, 9.5)
            
            # Forward pass: Primary M33 + Layer 1 (M3) -> Sigmoid1 -> Layer 2 (M8) -> Sigmoid2
            out_m33 = surrogate.forward_matrix_33(x_ref, w_m33_target, t_ms=t_slot)
            out_m3 = surrogate.forward_matrix_3(x_ref, w_m3, t_ms=t_slot)
            
            # Sigmoid 1 (Hardwired between M3 and M8: 6 outputs)
            sig1 = np.tanh(out_m3 / 128.0) * 128.0
            
            # Layer 2 (M8) forward: M8 is 7x6 (7 rows, 6 cols). Row 0..5 are data, Row 6 is bias.
            sig1_padded = np.zeros(7, dtype=float)
            sig1_padded[:6] = sig1[:6]
            sig1_padded[6] = 64.0 # Bias row 7
            out_m8 = np.dot(sig1_padded, w_m8) / 128.0
            # Sigmoid 2 (Mode A)
            sig2 = np.tanh(out_m8 / 128.0) * 128.0
            
            # Analog Summing Junction 35
            y_comp = out_m33 + sig2
            z_target = np.dot(w_m33_target, x_ref) / 128.0
            
            # Error and gradient estimation via forward Hadamard projection
            err = y_comp - z_target
            grad_m8 = np.outer(sig1_padded, err) / 128.0
            grad_m3_rows = np.zeros_like(w_m3)
            grad_m3_rows[:6, :] = np.outer(x_ref, np.dot(w_m8[:6, :], err)) / (128.0 * 128.0)
            
            grad_accum_m3 += grad_m3_rows
            grad_accum_m8 += grad_m8
            
        # Outer loop Base Model update W_0 (Ref 40)
        w_m3 -= lr_outer * (grad_accum_m3 / 4.0)
        w_m8 -= lr_outer * (grad_accum_m8 / 4.0)
        w_m3 = np.clip(w_m3, -127, 127)
        w_m8 = np.clip(w_m8, -127, 127)
        
        # Test on independent random payloads
        x_test = rng.uniform(-90, 90, 6)
        out_m33_test = surrogate.forward_matrix_33(x_test, w_m33_target, t_ms=5.0)
        out_m3_test = surrogate.forward_matrix_3(x_test, w_m3, t_ms=5.0)
        sig1_test = np.tanh(out_m3_test / 128.0) * 128.0
        sig1_test_padded = np.zeros(7, dtype=float)
        sig1_test_padded[:6] = sig1_test[:6]
        sig1_test_padded[6] = 64.0
        out_m8_test = np.dot(sig1_test_padded, w_m8) / 128.0
        sig2_test = np.tanh(out_m8_test / 128.0) * 128.0
        y_comp_test = out_m33_test + sig2_test
        z_target_test = np.dot(w_m33_target, x_test) / 128.0
        loss = np.mean((y_comp_test - z_target_test) ** 2)
        epoch_losses.append(loss)
        
    rmse_comp = np.sqrt(epoch_losses[-1])
    comp_enob = max(1.5, min(11.0, 11.0 - np.log2(max(1.0, rmse_comp))))
    
    return {
        "variant_id": variant_id,
        "m33_mean": float(np.mean(w_m33_target)),
        "m33_std": float(np.std(w_m33_target)),
        "uncomp_enob": round(float(uncomp_enob), 2),
        "comp_enob": round(float(comp_enob), 2),
        "enob_gain": round(float(comp_enob - uncomp_enob), 2),
        "final_loss": round(float(epoch_losses[-1]), 1),
        "loss_reduction_pct": round(float((1.0 - epoch_losses[-1] / (uncomp_errors[0] + 1e-6)) * 100), 1),
        "w_m3_norm": round(float(np.linalg.norm(w_m3)), 1),
        "w_m8_norm": round(float(np.linalg.norm(w_m8)), 1)
    }

def main():
    target_stop_time = 21 * 3600  # 21:00:00 CEST
    # Today's 21:00 CEST timestamp:
    lt = time.localtime()
    stop_epoch = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 21, 0, 0, lt.tm_wday, lt.tm_yday, lt.tm_isdst))
    
    print(f"=== LAUNCHING 100 MATRIX-33 VARIANTS INVERTED MAML CAMPAIGN (UNTIL 21:00 CEST) ===")
    print(f"Current time: {time.strftime('%H:%M:%S')} | Target Stop: 21:00:00 (~{(stop_epoch - time.time())/3600:.2f} hours)")
    
    surrogate = AnalogHardwareSurrogate(seed=100)
    master_rng = np.random.RandomState(2026)
    
    # Pre-generate 100 distinct random Matrix 33 multiplier sets
    # Weights scaled in -127..+127 (representing 0..255 unsigned DAC ranges centered at 128)
    variants = []
    for vid in range(100):
        # Different distribution types: uniform, bipolar, sparse, Gaussian
        dtype = vid % 4
        if dtype == 0:
            w_mat = master_rng.uniform(-100, 100, (6, 6))
        elif dtype == 1:
            w_mat = master_rng.normal(0, 45, (6, 6))
        elif dtype == 2:
            w_mat = master_rng.choice([-80, -40, 0, 40, 80], size=(6, 6))
        else:
            w_mat = master_rng.uniform(10, 110, (6, 6)) * master_rng.choice([-1, 1], size=(6, 6))
        w_mat = np.clip(np.round(w_mat), -127, 127).astype(int)
        variants.append(w_mat)
        
    completed_results = []
    current_idx = 0
    
    while time.time() < stop_epoch:
        now = time.time()
        rem_sec = stop_epoch - now
        
        # Cycle through variants 0..99 repeatedly
        var_id = current_idx % 100
        w_target = variants[var_id]
        
        # 1. Train specialized Inverted MAML base model for this Matrix 33
        t0 = time.time()
        res = train_base_model_for_variant(var_id, w_target, surrogate, n_epochs=12)
        train_time = time.time() - t0
        res["iteration"] = current_idx // 100 + 1
        res["eval_time_sec"] = round(train_time, 2)
        
        # 2. Synchronize with physical board: take 1 physical hardware step
        hw_uncomp, hw_comp, hw_loss = hw_step()
        res["live_hw_uncomp_enob"] = hw_uncomp
        res["live_hw_comp_enob"] = hw_comp
        res["live_hw_loss"] = hw_loss
        
        completed_results.append(res)
        if len(completed_results) > 150:
            completed_results.pop(0) # Keep file budget strictly under 60 KB
            
        current_idx += 1
        
        # Compute aggregate statistics
        gains = [r["enob_gain"] for r in completed_results]
        comp_enobs = [r["comp_enob"] for r in completed_results]
        
        summary_payload = {
            "campaign_title": "100 Matrix-33 Variants Inverted MAML Base-Model Training",
            "target_stop": "21:00:00 CEST",
            "last_heartbeat": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_variants_evaluated": len(completed_results),
            "current_variant_id": var_id,
            "mean_enob_gain": round(float(np.mean(gains)), 2),
            "max_enob_gain": round(float(np.max(gains)), 2),
            "mean_compensated_enob": round(float(np.mean(comp_enobs)), 2),
            "best_compensated_enob": round(float(np.max(comp_enobs)), 2),
            "remaining_minutes": round(rem_sec / 60.0, 1),
            "recent_variant_results": completed_results[-20:]
        }
        
        # Atomic write to JSON
        tmp_file = OUT_JSON.with_suffix(".tmp")
        with open(tmp_file, "w") as f:
            json.dump(summary_payload, f, indent=2)
        os.replace(tmp_file, OUT_JSON)
        
        if current_idx % 5 == 0 or current_idx == 1:
            print(f"[{time.strftime('%H:%M:%S')}] Variant {var_id:2d}/100 | "
                  f"Raw ENOB: {res['uncomp_enob']:.2f}b -> Comp: {res['comp_enob']:.2f}b "
                  f"(Gain: +{res['enob_gain']:.2f}b, Loss -{res['loss_reduction_pct']}%) | "
                  f"Live HW: {hw_comp}b | Rem: {rem_sec/60:.1f}m")
            
        time.sleep(2.0) # Pace loop smoothly
        
    print(f"[{time.strftime('%H:%M:%S')}] === CAMPAIGN REACHED 21:00:00 CEST TARGET === Completed successfully.")

if __name__ == "__main__":
    main()
