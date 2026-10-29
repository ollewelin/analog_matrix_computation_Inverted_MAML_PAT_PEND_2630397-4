#!/usr/bin/env python3
"""
compare_hadamard_start_vs_final_weights.py
==========================================
Direct physical silicon comparison of Hadamard carrier response (FWHT demodulation):
1. Start/Centered Weights:
   - Resets/centers weights to physical null baseline (W_null).
   - Measures live Hadamard carrier amplitude & FWHT demodulation on ADC_45 (Layer 1) & ADC_49 (Summing).
2. Clamped / Final Weights:
   - Steps weights with high learning rate until weights saturate/reach rails (clamped at +/-120 LSB).
   - Measures live Hadamard carrier amplitude & FWHT demodulation on ADC_45 & ADC_49.
3. Comparative Analysis:
   - Does FWHT carrier demodulation stall (attenuate, collapse, lose dynamic range) when weights clamp?
"""

import sys
import time
import socket
import struct
from pathlib import Path
import numpy as np

MAML_UDP_MAGIC = 0x4D414D4C

def send_recv(pkt, host="192.168.1.50", port=5000, timeout=2.5, retries=3):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(timeout)
    for _ in range(retries):
        try:
            s.sendto(pkt, (host, port))
            data, _ = s.recvfrom(2048)
            s.close()
            return data
        except socket.timeout:
            time.sleep(0.05)
    s.close()
    return None

def center_weights():
    pkt = struct.pack("<I", MAML_UDP_MAGIC) + bytes([0x15])
    return send_recv(pkt)

def get_telemetry():
    pkt = struct.pack("<I", MAML_UDP_MAGIC) + bytes([0x10])
    data = send_recv(pkt)
    if not data or len(data) < 306:
        return None
    w_m3 = np.frombuffer(data, dtype=np.int8, count=48, offset=110).reshape(8, 6).copy()
    w_m8 = np.frombuffer(data, dtype=np.int8, count=42, offset=158).reshape(7, 6).copy()
    loss_milli, rmse_lsb = struct.unpack_from("<II", data, 76)
    enob_bits = (struct.unpack_from("<I", data, 84)[0]) / 1000.0
    return {
        "w_m3": w_m3,
        "w_m8": w_m8,
        "loss": loss_milli / 1000.0,
        "rmse": rmse_lsb / 1000.0,
        "enob": enob_bits,
    }

def run_hadamard_diag(mode=6, en_mask=0x7FFF):
    pkt = struct.pack("<IBBH", MAML_UDP_MAGIC, 0x19, mode, en_mask)
    data = send_recv(pkt)
    if not data or len(data) < 868:
        return None
    ack_ok, ack_miss, lat_last = struct.unpack_from("<IIH", data, 56)
    cap45 = np.frombuffer(data, dtype="<i2", count=96, offset=100).reshape(16, 6)[:12].copy()
    cap49 = np.frombuffer(data, dtype="<i2", count=96, offset=292).reshape(16, 6)[:12].copy()
    fwht45 = np.frombuffer(data, dtype="<i2", count=96, offset=484).reshape(16, 6).copy()
    fwht49 = np.frombuffer(data, dtype="<i2", count=96, offset=676).reshape(16, 6).copy()
    return {
        "ack_ok": ack_ok,
        "ack_miss": ack_miss,
        "lat": lat_last,
        "cap45": cap45,
        "cap49": cap49,
        "fwht45": fwht45,
        "fwht49": fwht49,
    }

def main():
    print("=" * 78)
    print("HADAMARD STALL TEST: START (CENTERED) VS FINAL (CLAMPED) WEIGHTS")
    print("Target: Efinix Trion T120 Master SoC (192.168.1.50:5000)")
    print("=" * 78)

    # -------------------------------------------------------------
    # PHASE 1: START / CENTERED WEIGHTS
    # -------------------------------------------------------------
    print("\n[PHASE 1] Centering weights on physical hardware (Opcode 0x15)...")
    center_weights()
    time.sleep(0.1)

    t_start = get_telemetry()
    if not t_start:
        print("[!] ERROR: Hardware not responding to telemetry!")
        sys.exit(1)

    diag_start_on  = run_hadamard_diag(mode=6, en_mask=0x7FFF)
    diag_start_off = run_hadamard_diag(mode=5, en_mask=0x7FFF)

    if not diag_start_on or not diag_start_off:
        print("[!] ERROR: Hadamard diag failed at start weights!")
        sys.exit(1)

    # PtP and FWHT metrics
    ptp45_start = np.ptp(diag_start_on["cap45"], axis=0)
    ptp49_start = np.ptp(diag_start_on["cap49"], axis=0)
    fwht45_start_max = np.max(np.abs(diag_start_on["fwht45"]), axis=0)
    fwht49_start_max = np.max(np.abs(diag_start_on["fwht49"]), axis=0)
    frob49_start = float(np.linalg.norm(diag_start_on["fwht49"]))

    print(f"  Start W8 Diag:    {[int(t_start['w_m8'][i,i]) for i in range(6)]}")
    print(f"  Start W3 Diag:    {[int(t_start['w_m3'][i,i]) for i in range(6)]}")
    print(f"  Start Loss:       {t_start['loss']:.1f} LSB^2 | ENOB: {t_start['enob']:.2f} bits")
    print(f"  Start ADC45 FWHT max (M3 Layer 1): {fwht45_start_max.tolist()} LSB")
    print(f"  Start ADC49 FWHT max (M8 Summing): {fwht49_start_max.tolist()} LSB")
    print(f"  Start FWHT49 Frobenius Norm:       {frob49_start:.1f}")

    # -------------------------------------------------------------
    # PHASE 2: DRIVE WEIGHTS TO CLAMPED / FINAL VALUES
    # -------------------------------------------------------------
    print("\n[PHASE 2] Stepping weights into deep saturation / rail clamp (+/-120 LSB)...")
    # Configure clamp = 120, gain = 1.0x, w33=1, d=1
    pkt_cfg = struct.pack("<IBBBHB", MAML_UDP_MAGIC, 0x1C, 1, 1, 256, 120)
    send_recv(pkt_cfg)

    # Use large learning rate to force weights to the clamp limits
    k_batch = 4
    num_strata = 10
    lr_q16 = 2500  # High LR to aggressively push weights to +/-120 clamp
    pkt_step = struct.pack("<IBBBHHH", MAML_UDP_MAGIC, 0x1B, k_batch, num_strata, 4900, 5100, lr_q16)

    # Step in blocks of 50
    for block in range(6):
        for _ in range(50):
            send_recv(pkt_step)
        t_curr = get_telemetry()
        n_clamped_m8 = int(np.sum(np.abs(t_curr["w_m8"]) >= 118))
        n_clamped_m3 = int(np.sum(np.abs(t_curr["w_m3"]) >= 118))
        print(f"  Step {(block+1)*50:3d} | Clamped: M8={n_clamped_m8:2d}/42, M3={n_clamped_m3:2d}/48 | Loss: {t_curr['loss']:7.1f} LSB^2")
        if n_clamped_m8 >= 15:
            break

    t_final = get_telemetry()
    diag_final_on  = run_hadamard_diag(mode=6, en_mask=0x7FFF)
    diag_final_off = run_hadamard_diag(mode=5, en_mask=0x7FFF)

    ptp45_final = np.ptp(diag_final_on["cap45"], axis=0)
    ptp49_final = np.ptp(diag_final_on["cap49"], axis=0)
    fwht45_final_max = np.max(np.abs(diag_final_on["fwht45"]), axis=0)
    fwht49_final_max = np.max(np.abs(diag_final_on["fwht49"]), axis=0)
    frob49_final = float(np.linalg.norm(diag_final_on["fwht49"]))

    n_clamped_m8_final = int(np.sum(np.abs(t_final["w_m8"]) >= 118))
    n_clamped_m3_final = int(np.sum(np.abs(t_final["w_m3"]) >= 118))

    print(f"\n  Final W8 Diag:    {[int(t_final['w_m8'][i,i]) for i in range(6)]}")
    print(f"  Final W3 Diag:    {[int(t_final['w_m3'][i,i]) for i in range(6)]}")
    print(f"  Final Clamped:    M8 = {n_clamped_m8_final}/42 ({n_clamped_m8_final/42*100:.1f}%), M3 = {n_clamped_m3_final}/48 ({n_clamped_m3_final/48*100:.1f}%)")
    print(f"  Final Loss:       {t_final['loss']:.1f} LSB^2 | ENOB: {t_final['enob']:.2f} bits")
    print(f"  Final ADC45 FWHT max (M3 Layer 1): {fwht45_final_max.tolist()} LSB")
    print(f"  Final ADC49 FWHT max (M8 Summing): {fwht49_final_max.tolist()} LSB")
    print(f"  Final FWHT49 Frobenius Norm:       {frob49_final:.1f}")

    # -------------------------------------------------------------
    # PHASE 3: COMPARATIVE ANALYSIS (DID HADAMARD STALL?)
    # -------------------------------------------------------------
    print("\n" + "=" * 78)
    print("HADAMARD DEMODULATION VERDICT: START VS FINAL CLAMPED WEIGHTS")
    print("=" * 78)
    print(f"{'Col':<6} | {'Start W8':<10} | {'Final W8':<10} | {'FWHT49 Start':<14} | {'FWHT49 Final':<14} | {'Carrier Ratio (Final/Start)'}")
    print("-" * 78)
    for c in range(6):
        ratio = (fwht49_final_max[c] / max(1, fwht49_start_max[c])) * 100.0
        status = "HEALTHY" if ratio >= 70.0 else ("ATTENUATED" if ratio >= 30.0 else "STALLED/COLLAPSED")
        print(f"Col {c:<2d} | {t_start['w_m8'][c,c]:+4d} LSB   | {t_final['w_m8'][c,c]:+4d} LSB   | {fwht49_start_max[c]:5d} LSB       | {fwht49_final_max[c]:5d} LSB       | {ratio:5.1f}% [{status}]")
    print("-" * 78)

    ratio_total = (frob49_final / max(1.0, frob49_start)) * 100.0
    print(f"Overall FWHT-16 Frobenius Energy: Start = {frob49_start:.1f} -> Final = {frob49_final:.1f} ({ratio_total:.1f}%)")

    # Center back to leave hardware clean
    center_weights()
    print("\n[+] Restored weights to centered state. Hardware ready.")

if __name__ == "__main__":
    main()

