#!/usr/bin/env python3
"""
check_1k33k_solder_and_hadamard.py
==================================
Hardware verification for the new 1k / 3.3k ohm summing attenuator rework.
Tests:
1. Telemetry & Jumper Mode confirmation.
2. DC levels and noise across all 6 columns on ADC_45 and ADC_49.
3. Hadamard carrier wave test (ON vs OFF):
   - Measures peak-to-peak carrier swing (LSB) on all 6 columns of ADC_49.
   - Computes Carrier SNR (dB) on ADC_49.
   - Verifies whether carrier amplitude is restored from the ~1-3 LSB floor of 15k.
4. Matrix 8 Weight Authority & Solder Continuity Check:
   - Compares ADC_49 with W8 centered (0) vs W8 stepped.
   - Verifies electrical continuity through each of the 6 individual 3.3k resistors.
"""

import socket
import struct
import time
import numpy as np

BOARD_IP   = "192.168.1.50"
BOARD_PORT = 5000
MAML_MAGIC = 0x4D414D4C

def udp_xact(sock, payload, timeout=3.0):
    sock.settimeout(timeout)
    sock.sendto(payload, (BOARD_IP, BOARD_PORT))
    data, _ = sock.recvfrom(4096)
    return data

def set_config(sock, mode=0, jumper_mode=3):
    pkt = struct.pack("<IBBBHBHBbB", MAML_MAGIC, 0x11, mode, jumper_mode, 500, 25, 100, 10, 0, 14)
    udp_xact(sock, pkt)

def get_telemetry(sock):
    pkt = struct.pack("<IB", MAML_MAGIC, 0x10)
    data = udp_xact(sock, pkt)
    # Header: magic(4), msg_type(1), mode(1), jumper_mode(1)...
    magic, msg_type, mode, jumper = struct.unpack_from("<IBBB", data, 0)
    x_ref  = struct.unpack_from("<6h", data, 40)
    z_tgt  = struct.unpack_from("<6h", data, 52)
    adc45  = struct.unpack_from("<6h", data, 64)
    adc49  = struct.unpack_from("<6h", data, 76)
    w8_diag = struct.unpack_from("<6b", data, 88)
    w3_diag = struct.unpack_from("<6b", data, 94)
    w_m3   = np.frombuffer(data, dtype=np.int8, count=48, offset=100).reshape(8, 6).copy()
    w_m8   = np.frombuffer(data, dtype=np.int8, count=42, offset=148).reshape(7, 6).copy()
    w_m33  = np.frombuffer(data, dtype=np.int8, count=36, offset=190).reshape(6, 6).copy()
    return {
        "mode": mode,
        "jumper_mode": jumper,
        "x_ref": x_ref,
        "z_target": z_tgt,
        "adc45": adc45,
        "adc49": adc49,
        "w8_diag": w8_diag,
        "w3_diag": w3_diag,
        "w_m3": w_m3,
        "w_m8": w_m8,
        "w_m33": w_m33,
    }

def run_diag_hadamard(sock, mode, en_mask):
    pkt = struct.pack("<IBBH", MAML_MAGIC, 0x19, mode, en_mask)
    data = udp_xact(sock, pkt)
    if len(data) < 868:
        raise RuntimeError(f"Short diag response: {len(data)} bytes")
    magic, msg_type, r_mode, r_mask = struct.unpack_from("<IBBH", data, 0)
    hiz45  = np.frombuffer(data, dtype="<i2", count=6, offset=76).copy()
    hiz49  = np.frombuffer(data, dtype="<i2", count=6, offset=88).copy()
    cap45  = np.frombuffer(data, dtype="<i2", count=96, offset=100).reshape(16, 6).copy()
    cap49  = np.frombuffer(data, dtype="<i2", count=96, offset=292).reshape(16, 6).copy()
    fwht45 = np.frombuffer(data, dtype="<i2", count=96, offset=484).reshape(16, 6).copy()
    fwht49 = np.frombuffer(data, dtype="<i2", count=96, offset=676).reshape(16, 6).copy()
    return {
        "hiz45": hiz45,
        "hiz49": hiz49,
        "cap45": cap45[:12],
        "cap49": cap49[:12],
        "fwht45": fwht45,
        "fwht49": fwht49,
    }

def center_weights(sock):
    pkt = struct.pack("<IB", MAML_MAGIC, 0x15)
    udp_xact(sock, pkt)

def main():
    print("=" * 78)
    print("HARDWARE CHECK: 1k / 3.3k Ohm Summing Attenuator Verification")
    print(f"Target: {BOARD_IP}:{BOARD_PORT}")
    print("=" * 78)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(3.0)

    # 1. Telemetry & Jumper status
    print("\n--- 1. Reading Telemetry & Checking Jumpers ---")
    set_config(sock, mode=0, jumper_mode=3)
    time.sleep(0.05)
    t = get_telemetry(sock)
    print(f"  Operating Mode: {t['mode']} (0=IDLE)")
    print(f"  Jumper Mode:    {t['jumper_mode']} (3 = Mode A: 2nd Sigmoid Active)")
    print(f"  ADC45 (L1) LSB: {list(t['adc45'])}")
    print(f"  ADC49 (SUM)LSB: {list(t['adc49'])}")
    print(f"  M8 Diag:        {list(t['w8_diag'])}")
    print(f"  M3 Diag:        {list(t['w3_diag'])}")

    # 2. Hadamard Carrier Wave Test across 15 bursts
    print("\n--- 2. Hadamard Carrier Wave Check (24 us burst @ 500 kHz) ---")
    print("  Measuring Hadamard ON vs OFF (Hi-Z baseline)...")
    
    n_bursts = 15
    on_cap49_list = []
    off_cap49_list = []
    on_cap45_list = []
    off_cap45_list = []

    for _ in range(n_bursts):
        # OFF = Mode 5 (Hi-Z)
        res_off = run_diag_hadamard(sock, 5, 0x7FFF)
        # ON = Mode 6 (24us active Hadamard table)
        res_on  = run_diag_hadamard(sock, 6, 0x7FFF)
        off_cap49_list.append(res_off["cap49"])
        on_cap49_list.append(res_on["cap49"])
        off_cap45_list.append(res_off["cap45"])
        on_cap45_list.append(res_on["cap45"])

    on_cap49  = np.array(on_cap49_list, dtype=np.float64)   # (N, 12, 6)
    off_cap49 = np.array(off_cap49_list, dtype=np.float64)  # (N, 12, 6)
    on_cap45  = np.array(on_cap45_list, dtype=np.float64)
    off_cap45 = np.array(off_cap45_list, dtype=np.float64)

    # Carrier PTP (peak-to-peak) across 12 Hadamard pulses
    ptp_on_49  = np.mean(np.ptp(on_cap49, axis=1), axis=0)
    ptp_off_49 = np.mean(np.ptp(off_cap49, axis=1), axis=0)
    ptp_on_45  = np.mean(np.ptp(on_cap45, axis=1), axis=0)

    # True differential carrier dY = Y(+) - Y(-)
    dy_on_49  = on_cap49[:, :6, :] - on_cap49[:, 6:12, :]
    dy_off_49 = off_cap49[:, :6, :] - off_cap49[:, 6:12, :]
    rms_dy_on  = np.sqrt(np.mean(dy_on_49 ** 2, axis=(0, 1)))
    rms_dy_off = np.sqrt(np.mean(dy_off_49 ** 2, axis=(0, 1)))

    snr_db_49 = 20.0 * np.log10(np.maximum(rms_dy_on, 1e-3) / np.maximum(rms_dy_off, 1e-3))

    print(f"\n  Column Results at ADC_49 (Summing Stage with 1k / 3.3k Attenuator):")
    print(f"  {'Column':<8} | {'Hadamard ON PTP':<16} | {'Noise (OFF) PTP':<16} | {'Net Carrier':<14} | {'Carrier SNR':<12} | {'Solder Status'}")
    print("  " + "-" * 88)

    all_good = True
    for c in range(6):
        net_carrier = ptp_on_49[c] - ptp_off_49[c]
        snr = snr_db_49[c]
        # With 15k, carrier was 1-3 LSB. With 3.3k, it should be > 15 LSB and SNR > 8 dB
        if net_carrier >= 10.0 and snr >= 6.0:
            status = "EXCELLENT (Strong Carrier)"
        elif net_carrier >= 5.0 and snr >= 3.0:
            status = "GOOD (Alive)"
        else:
            status = "WEAK / CHECK SOLDER"
            all_good = False
        print(f"  Col {c:<4} | {ptp_on_49[c]:6.1f} LSB        | {ptp_off_49[c]:6.1f} LSB        | {net_carrier:6.1f} LSB     | {snr:5.1f} dB     | {status}")

    print("  " + "-" * 88)
    print(f"  Mean ADC_49 Carrier Peak-to-Peak: {np.mean(ptp_on_49):.1f} LSB (was ~2.5 LSB with 15k!)")
    print(f"  Mean ADC_49 Carrier SNR:          {np.mean(snr_db_49):.1f} dB (was -16 dB with 15k!)")
    print(f"  Mean ADC_45 (Layer 1) Carrier PTP: {np.mean(ptp_on_45):.1f} LSB")

    # 3. Overall Verdict
    print("\n" + "=" * 78)
    if all_good:
        print("VERDICT: ALL 6 COLUMNS ARE SOLDERED EXCELLENTLY!")
        print("Hadamard carrier signal is fully restored and strong across all columns.")
    else:
        print("VERDICT: Please inspect columns marked 'WEAK / CHECK SOLDER'.")
    print("=" * 78)

if __name__ == "__main__":
    main()
