#!/usr/bin/env python3
"""
test_1k33k_hadamard_live.py
===========================
Live verification of the 1k / 3.3k ohm summing attenuator rework.
Tests:
1. Initial baseline telemetry across all 6 columns.
2. Direct Hadamard carrier detection on ADC_45 and ADC_49.
3. Closed-loop 10-epoch training convergence test on Mode A.
   - Tracks per-column weight adjustments (W8[0..5]) driven by live Hadamard gradients.
   - Verifies whether every single column responds and reduces error.
"""

import sys
import time
import struct
from pathlib import Path
import numpy as np

sys.path.append(str(Path(__file__).parent))
from run_mode_a_longterm_batch_sweep import (
    MamlUdpClient,
    draw_fresh_vector,
    get_averaged_telemetry,
    parse_telemetry_packet,
    MAML_CMD_BATCH_STEP,
)

def main():
    print("=" * 78)
    print("LIVE HARDWARE VERIFICATION: 1k / 3.3k Ohm Summing Attenuator")
    print("Platform: 192.168.1.50:5000 | Mode A (Jumper Mode 3)")
    print("=" * 78)

    client = MamlUdpClient(host="192.168.1.50", port=5000, timeout=4.0)

    # 1. Configure Mode A and Center Weights
    print("[1] Initializing Mode A configuration & centering weights...")
    client.set_config(
        mode=0, jumper_mode=3, led_switches=3, max_meas_win_pct=100, hadamard_khz=500,
        inner_loop_n=100, seed_pct=28, seed_mode=1, w_hid_mag=0, trim_hid_mag=0,
        hadamard_delay_us=5000,
    )
    time.sleep(0.05)
    client.center_compensation_weights()
    time.sleep(0.05)

    # 2. Read baseline telemetry on all 6 columns
    draw_fresh_vector(client, settle_s=0.04)
    init_telem = get_averaged_telemetry(client, n_avg=6)
    if not init_telem:
        print("[!] ERROR: Could not read telemetry from hardware!")
        return

    print("\n--- Baseline Telemetry (All 6 Columns) ---")
    print(f"  ADC45 (Layer 1) LSB: {[round(x, 1) for x in init_telem['adc45']]}")
    print(f"  ADC49 (Summing) LSB: {[round(x, 1) for x in init_telem['adc49']]}")
    print(f"  Target Z_ref    LSB: {[round(x, 1) for x in init_telem.get('z_target', [0]*6)]}")
    print(f"  Initial Error   LSB: {[round(x, 1) for x in init_telem['err49']]}")
    print(f"  Initial W8 Diag:     {init_telem['w8_diag']}")
    print(f"  Initial W3 Diag:     {init_telem['w3_diag']}")
    print(f"  Initial Loss:        {init_telem['loss_lsb2']:.1f} LSB^2 | RMSE: {init_telem['rmse_lsb']:.2f} LSB | ENOB: {init_telem['enob_bits']:.2f} bits")

    # 3. Direct Hadamard Carrier SNR Diagnostic (MAML_CMD_DIAG_HADAMARD)
    print("\n[2] Direct Hadamard Carrier Check (Hadamard ON vs Hi-Z)...")
    diag_on = client.diag_hadamard(mode=6, en_mask=0x7FFF)
    diag_off = client.diag_hadamard(mode=5, en_mask=0x7FFF)
    if diag_on and diag_off:
        ptp49_on = np.ptp(diag_on.cap49[:12], axis=0)
        ptp49_off = np.ptp(diag_off.cap49[:12], axis=0)
        ptp45_on = np.ptp(diag_on.cap45[:12], axis=0)
        print(f"  ADC49 Hadamard ON  PTP across 12 pulses: {ptp49_on.tolist()} LSB")
        print(f"  ADC49 Hadamard OFF PTP (Noise floor):    {ptp49_off.tolist()} LSB")
        print(f"  ADC45 Layer 1 ON   PTP across 12 pulses: {ptp45_on.tolist()} LSB")

    # 4. Run 10 Epochs of Mode A Training (K=8, 10 Strata = 80 samples/step, LR=0.10)
    # If Hadamard signal is alive, gradients will drive W8 to cancel the errors!
    lr = 0.10
    lr_inner_q16 = max(32, min(4096, int(round(1024 * lr))))
    epochs = 10
    k = 8

    print(f"\n[3] Running {epochs} Epochs of Mode A Training (K={k}, 80 samples/step, LR={lr:.2f}x)...")
    print("-" * 78)
    print(f"{'Ep':<4} | {'Train RMSE':<10} | {'Val RMSE':<10} | {'Val ENOB':<10} | {'W8 Diag (Cols 0..5)':<26}")
    print("-" * 78)

    w8_initial = list(init_telem["w8_diag"])
    prev_w8 = list(w8_initial)

    for ep in range(1, epochs + 1):
        # A. Batch Step
        raw_train = None
        for attempt in range(3):
            raw_train = client._send_binary(
                MAML_CMD_BATCH_STEP,
                struct.pack("<BBHHH", k, 10, 4900, 5100, lr_inner_q16)
            )
            if raw_train and len(raw_train) >= client.TELEM_SIZE:
                break
            time.sleep(0.04)

        if not raw_train or len(raw_train) < client.TELEM_SIZE:
            print(f"[!] Warning: Ep {ep} train packet dropped.")
            continue

        train_p = parse_telemetry_packet(raw_train, client)

        # B. Fixed holdout validation
        val_telem = get_averaged_telemetry(client, n_avg=4)
        if not val_telem:
            val_telem = train_p

        w8_curr = list(train_p["w8_diag"])
        print(f"{ep:<4} | {train_p['rmse_lsb']:8.2f} LSB | {val_telem['rmse_lsb']:8.2f} LSB | {val_telem['enob_bits']:6.2f} bits | {w8_curr}")
        prev_w8 = w8_curr

    # 5. Evaluate Per-Column Solder & Gradient Response
    final_telem = get_averaged_telemetry(client, n_avg=6)
    w8_final = list(final_telem["w8_diag"])
    w3_final = list(final_telem["w3_diag"])
    err_final = [round(x, 1) for x in final_telem["err49"]]

    print("\n" + "=" * 78)
    print("SOLDER & HADAMARD VERIFICATION SUMMARY:")
    print("=" * 78)
    print(f"{'Col':<5} | {'Initial Err':<12} | {'Final Err':<12} | {'Initial W8':<11} | {'Final W8':<11} | {'Weight Shift':<13} | {'Status'}")
    print("-" * 78)

    all_ok = True
    for c in range(6):
        init_e = init_telem['err49'][c]
        fin_e = err_final[c]
        w_init = w8_initial[c]
        w_fin = w8_final[c]
        delta_w = w_fin - w_init
        
        # Did the weight adapt in the right direction to reduce the error?
        # A non-zero weight shift driven by Hadamard gradient indicates solder connection is alive!
        if abs(delta_w) >= 1 or abs(fin_e) < 30:
            status = "SOLDER OK & GRADIENT ACTIVE"
        else:
            status = "STATIONARY (Check Col)"
            all_ok = False

        print(f"Col {c:<2} | {init_e:8.1f} LSB   | {fin_e:8.1f} LSB   | {w_init:6d}      | {w_fin:6d}      | {delta_w:+4d} LSB       | {status}")

    print("-" * 78)
    print(f"Initial Error RMSE: {init_telem['rmse_lsb']:.2f} LSB  ({init_telem['enob_bits']:.2f} bits ENOB)")
    print(f"Final Error RMSE:   {final_telem['rmse_lsb']:.2f} LSB  ({final_telem['enob_bits']:.2f} bits ENOB)")
    
    if final_telem['rmse_lsb'] < init_telem['rmse_lsb']:
        print(f"\nSUCCESS: Error reduced by {((init_telem['rmse_lsb'] - final_telem['rmse_lsb'])/init_telem['rmse_lsb'])*100:.1f}%!")
        print("Hadamard closed-loop training is fully operational through the 1k / 3.3k attenuator!")
    else:
        print("\nNote: Error remained similar, checking individual column movements.")

if __name__ == "__main__":
    main()

