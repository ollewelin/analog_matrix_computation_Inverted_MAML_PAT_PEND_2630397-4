#!/usr/bin/env python3
"""
check_1k51k_solder_and_hadamard.py
==================================
Hardware verification script for the newly soldered 1k / 5.1k Ohm summing attenuator.
1. Checks UDP connection and initial baseline telemetry.
2. Centers weights to baseline null point.
3. Tests Hadamard carrier ON vs OFF (Hi-Z) across all 6 columns on ADC_45 and ADC_49.
4. Checks solder integrity (detects open/broken solder joints vs active signals).
5. Runs a quick 5-epoch closed-loop gradient test to verify that weights actually move.
"""

import sys
import socket
import struct
import time
import numpy as np

MAML_UDP_MAGIC = 0x4D414D4C
BOARD_IP = "192.168.1.50"
BOARD_PORT = 5000

def send_recv(pkt, timeout=2.5, retries=3):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(timeout)
    for _ in range(retries):
        try:
            s.sendto(pkt, (BOARD_IP, BOARD_PORT))
            data, _ = s.recvfrom(2048)
            s.close()
            return data
        except socket.timeout:
            time.sleep(0.05)
    s.close()
    return None

def main():
    print("=" * 78)
    print("LIVE HARDWARE VERIFICATION: 1k / 5.1k Ohm Summing Attenuator")
    print(f"Target: Efinix Trion T120 Master SoC ({BOARD_IP}:{BOARD_PORT})")
    print("=" * 78)

    # 1. Ping / Center weights
    print("\n[1] Initializing hardware & centering weights (Opcode 0x15)...")
    send_recv(struct.pack("<I", MAML_UDP_MAGIC) + bytes([0x15]))
    time.sleep(0.1)

    # 2. Baseline Telemetry
    print("[2] Reading baseline settled telemetry (Opcode 0x10)...")
    t_data = send_recv(struct.pack("<I", MAML_UDP_MAGIC) + bytes([0x10]))
    if not t_data or len(t_data) < 298:
        print(f"[!] FATAL: Could not read telemetry packet from hardware (len={len(t_data) if t_data else 0})!")
        sys.exit(1)

    adc45_sig = list(struct.unpack_from("<6h", t_data, 12))
    adc49_sig = list(struct.unpack_from("<6h", t_data, 24))
    z_tgt     = list(struct.unpack_from("<6h", t_data, 36))
    err49     = list(struct.unpack_from("<6h", t_data, 48))
    loss_milli, rmse_lsb = struct.unpack_from("<II", t_data, 76)
    w_m3 = np.frombuffer(t_data, dtype=np.int8, count=48, offset=110).reshape(8, 6)
    w_m8 = np.frombuffer(t_data, dtype=np.int8, count=42, offset=158).reshape(7, 6)

    print(f"  ADC45 (Layer 1) LSB: {adc45_sig}")
    print(f"  ADC49 (Summing) LSB: {adc49_sig}")
    print(f"  Target Z_ref    LSB: {z_tgt}")
    print(f"  Initial Error   LSB: {err49}")
    print(f"  Initial W8 Diag:     {[int(w_m8[i,i]) for i in range(6)]}")
    print(f"  Initial W3 Diag:     {[int(w_m3[i,i]) for i in range(6)]}")
    print(f"  Initial Loss:        {loss_milli/1000.0:.1f} LSB^2 | RMSE: {rmse_lsb/1000.0:.2f} LSB")

    # 3. Direct Hadamard Carrier SNR Diagnostic
    print("\n[3] Testing Hadamard Carrier ON (mode 6) vs OFF/Hi-Z (mode 5)...")
    pkt_on = struct.pack("<IBBH", MAML_UDP_MAGIC, 0x19, 6, 0x7FFF)
    d_on = send_recv(pkt_on)
    pkt_off = struct.pack("<IBBH", MAML_UDP_MAGIC, 0x19, 5, 0x7FFF)
    d_off = send_recv(pkt_off)

    if not d_on or not d_off:
        print("[!] FATAL: Hadamard diagnostic did not respond!")
        sys.exit(1)

    cap45_on  = np.frombuffer(d_on, dtype="<i2", count=96, offset=100).reshape(16, 6)[:12]
    cap49_on  = np.frombuffer(d_on, dtype="<i2", count=96, offset=292).reshape(16, 6)[:12]
    fwht45_on = np.frombuffer(d_on, dtype="<i2", count=96, offset=484).reshape(16, 6)
    fwht49_on = np.frombuffer(d_on, dtype="<i2", count=96, offset=676).reshape(16, 6)

    cap49_off = np.frombuffer(d_off, dtype="<i2", count=96, offset=292).reshape(16, 6)[:12]

    ptp49_on  = np.ptp(cap49_on, axis=0)
    ptp49_off = np.ptp(cap49_off, axis=0)
    ptp45_on  = np.ptp(cap45_on, axis=0)
    fwht49_max = np.max(np.abs(fwht49_on), axis=0)
    fwht45_max = np.max(np.abs(fwht45_on), axis=0)

    print(f"  ADC49 Hadamard ON  PTP across 12 pulses: {ptp49_on.tolist()} LSB")
    print(f"  ADC49 Hadamard OFF PTP (Noise floor):    {ptp49_off.tolist()} LSB")
    print(f"  ADC45 Layer 1 ON   PTP across 12 pulses: {ptp45_on.tolist()} LSB")
    print(f"  ADC49 FWHT-16 Peak Demodulation:         {fwht49_max.tolist()} LSB")
    print(f"  ADC45 FWHT-16 Peak Demodulation:         {fwht45_max.tolist()} LSB")

    # 4. Column by Column Solder & Signal Audit
    print("\n" + "=" * 78)
    print("SOLDER & SIGNAL INTEGRITY VERIFICATION TABLE (ALL 6 COLUMNS)")
    print("=" * 78)
    print(f"{'Col':<6} | {'ADC49 PtP':<10} | {'Noise PtP':<10} | {'FWHT49 Max':<12} | {'FWHT45 Max':<12} | {'Solder & Signal Status'}")
    print("-" * 78)
    all_ok = True
    for c in range(6):
        # A channel has signal if FWHT49 > 20 LSB or PtP_on > PtP_off + 5
        has_signal = (fwht49_max[c] >= 25) or (ptp49_on[c] > ptp49_off[c] + 5)
        if has_signal:
            status = "SOLDER OK - SIGNAL DETECTED"
        else:
            status = "WARNING: WEAK / OPEN CIRCUIT"
            all_ok = False
        print(f"Col {c:<2d} | {ptp49_on[c]:4d} LSB   | {ptp49_off[c]:4d} LSB   | {fwht49_max[c]:5d} LSB     | {fwht45_max[c]:5d} LSB     | {status}")
    print("-" * 78)

    # 5. Quick Closed-Loop Gradient Test (5 Epochs)
    print("\n[4] Running 5-epoch closed-loop gradient test to verify weight motion...")
    # Configure gain exp: clamp=120, gain=1.0x
    pkt_cfg = struct.pack("<IBBBHB", MAML_UDP_MAGIC, 0x1C, 1, 1, 256, 120)
    send_recv(pkt_cfg)

    k_batch = 4
    num_strata = 10
    lr_q16 = 102  # LR = 0.10x
    pkt_step = struct.pack("<IBBBHHH", MAML_UDP_MAGIC, 0x1B, k_batch, num_strata, 4900, 5100, lr_q16)

    w8_start = list([int(w_m8[i,i]) for i in range(6)])
    for ep in range(1, 6):
        send_recv(pkt_step)
        t_curr = send_recv(struct.pack("<I", MAML_UDP_MAGIC) + bytes([0x10]))
        w_curr = np.frombuffer(t_curr, dtype=np.int8, count=42, offset=158).reshape(7, 6)
        l_curr, r_curr = struct.unpack_from("<II", t_curr, 76)
        diag_w = [int(w_curr[i,i]) for i in range(6)]
        print(f"  Ep {ep}: Loss = {l_curr/1000.0:7.1f} LSB^2 | RMSE = {r_curr/1000.0:5.2f} LSB | W8 Diag: {diag_w}")

    w8_end = [int(w_curr[i,i]) for i in range(6)]
    shifts = [w8_end[i] - w8_start[i] for i in range(6)]
    print(f"\n[+] Total W8 Weight Shifts after 5 epochs: {shifts}")

    if all_ok:
        print("\n>>> RESULT: SUCCESS! All 6 columns show valid Hadamard signal through 1k/5.1k attenuator! <<<")
    else:
        print("\n>>> RESULT: Attention needed on columns marked with WARNING! <<<")

    # Center back
    send_recv(struct.pack("<I", MAML_UDP_MAGIC) + bytes([0x15]))

if __name__ == "__main__":
    main()
