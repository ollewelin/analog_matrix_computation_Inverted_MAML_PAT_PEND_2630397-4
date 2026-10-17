#!/usr/bin/env python3
"""
verify_separated_hadamard_and_weight_flip.py
============================================
100% Pure Live Hardware Verification of:
1. Time-Separated M3 (0x00FF) then M8 (0x7F00) 24.00 us (2x6 x 2.00 us) Hadamard Tables
   at t = 2.0 ms after Refresh (confirming patent separation of Mat(3) and Mat(8) in time).
2. Three-Test Sequence in a Row across N = 20 cycles:
   - Test 1 (OFF)      : Hadamard OFF (Tri-State 0x8000)
   - Test 2 (Pattern A): Weight Pattern A (+W) with 24.00 us Hadamard Table H
   - Test 3 (Pattern B): Weight Pattern B (-W = -W_A, all weight signs flipped)
                         with the EXACT same 24.00 us Hadamard Table H and input DAC_2.

ZERO SIMULATION POLICY (enforced by maml_anti_simulation_enforcer):
Every single number in this script is read directly from the physical XC2361A 12-bit
differential ADCs (ADC_45 and ADC_49) over UDP from 192.168.1.50:5000.
"""

import socket
import struct
import json
from pathlib import Path
import numpy as np

BOARD_IP   = "192.168.1.50"
BOARD_PORT = 5000
MAML_MAGIC = 0x4D414D4C


def udp_xact(sock, payload):
    sock.settimeout(0.6)
    for attempt in range(8):
        try:
            sock.sendto(payload, (BOARD_IP, BOARD_PORT))
            data, _ = sock.recvfrom(4096)
            return data
        except socket.timeout:
            if attempt == 7:
                raise
    raise TimeoutError("UDP transaction timed out after retries")


def get_telemetry(sock):
    pkt = struct.pack("<IB", MAML_MAGIC, 0x10)
    data = udp_xact(sock, pkt)
    x_ref  = struct.unpack_from("<6h", data, 50)
    z_tgt  = struct.unpack_from("<6h", data, 62)
    adc45  = struct.unpack_from("<6h", data, 74)
    adc49  = struct.unpack_from("<6h", data, 86)
    w_m3   = np.frombuffer(data, dtype=np.int8, count=48, offset=110).reshape(8, 6).copy()
    w_m8   = np.frombuffer(data, dtype=np.int8, count=42, offset=158).reshape(7, 6).copy()
    w_m33  = np.frombuffer(data, dtype=np.int8, count=36, offset=200).reshape(6, 6).copy()
    return {
        "x_ref": list(x_ref),
        "z_target": list(z_tgt),
        "adc45_sig": list(adc45),
        "adc49_sig": list(adc49),
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
    perm    = struct.unpack_from("<16B", data, 8)
    h_words = struct.unpack_from("<16H", data, 24)
    ack_ok, ack_miss, lat_last, lat_min, lat_max, t20_wcnt, t20_serr, settle_cyc = struct.unpack_from(
        "<IIHHHHHH", data, 56
    )
    hiz45  = np.frombuffer(data, dtype="<i2", count=6,   offset=76).copy()
    hiz49  = np.frombuffer(data, dtype="<i2", count=6,   offset=88).copy()
    cap45  = np.frombuffer(data, dtype="<i2", count=96,  offset=100).reshape(16, 6).copy()
    cap49  = np.frombuffer(data, dtype="<i2", count=96,  offset=292).reshape(16, 6).copy()
    fwht45 = np.frombuffer(data, dtype="<i2", count=96,  offset=484).reshape(16, 6).copy()
    fwht49 = np.frombuffer(data, dtype="<i2", count=96,  offset=676).reshape(16, 6).copy()
    return {
        "mode": r_mode,
        "en_mask": r_mask,
        "h_words": list(h_words[:13]),
        "ack_ok": int(ack_ok),
        "ack_miss": int(ack_miss),
        "lat_last": int(lat_last),
        "lat_min": int(lat_min),
        "lat_max": int(lat_max),
        "t20_word_cnt": int(t20_wcnt),
        "t20_sync_err": int(t20_serr),
        "settle_cycles": int(settle_cyc),
        "hiz45": hiz45,
        "hiz49": hiz49,
        "cap45": cap45[:12],   # 12 pulses (0..5 = (+) table, 6..11 = (-) table)
        "cap49": cap49[:12],
        "fwht45": fwht45,
        "fwht49": fwht49,
    }


def set_run_mode(sock, run_mode):
    pkt = struct.pack("<IBBBHBHBbB", MAML_MAGIC, 0x11, run_mode, 3, 500, 25, 100, 10, 0, 14)
    udp_xact(sock, pkt)


def summarize_pulse_snr(off_cap, on_cap):
    """Compute PtP, differential Y(+)-Y(-) RMS, and SNR (dB) from (N, 12, 6) arrays."""
    dy_off = off_cap[:, :6, :] - off_cap[:, 6:12, :]
    dy_on  = on_cap[:, :6, :]  - on_cap[:, 6:12, :]
    rms_off = np.sqrt(np.mean(dy_off ** 2, axis=(0, 1)))
    rms_on  = np.sqrt(np.mean(dy_on  ** 2, axis=(0, 1)))
    ptp_off = np.mean(np.ptp(off_cap, axis=1), axis=0)
    ptp_on  = np.mean(np.ptp(on_cap,  axis=1), axis=0)
    snr_db  = 20.0 * np.log10(np.maximum(rms_on, 1e-3) / np.maximum(rms_off, 1e-3))
    return {
        "ptp_off": ptp_off.tolist(),
        "ptp_on": ptp_on.tolist(),
        "rms_dy_off": rms_off.tolist(),
        "rms_dy_on": rms_on.tolist(),
        "snr_db": snr_db.tolist(),
        "mean_off_cap": np.mean(off_cap, axis=0).tolist(),
        "mean_on_cap": np.mean(on_cap, axis=0).tolist(),
    }


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(4.0)

    set_run_mode(sock, 0)

    print("====================================================================================")
    print(" 1. SEEDING WEIGHT PATTERN A (+W) & VERIFYING SIGN FLIP TO PATTERN B (-W = -W_A)")
    print("====================================================================================")
    init_a = run_diag_hadamard(sock, 4, 0x00FF)
    tel_a  = get_telemetry(sock)
    w_m3_a  = tel_a["w_m3"].copy()
    w_m8_a  = tel_a["w_m8"].copy()
    w_m33_a = tel_a["w_m33"].copy()

    # Flip to Pattern B (-W) via mode 8 and verify exact negation
    init_b = run_diag_hadamard(sock, 8, 0x00FF)
    tel_b  = get_telemetry(sock)
    w_m3_b  = tel_b["w_m3"].copy()
    w_m8_b  = tel_b["w_m8"].copy()
    w_m33_b = tel_b["w_m33"].copy()

    # Flip back to Pattern A (+W) before starting N-cycle loop
    run_diag_hadamard(sock, 8, 0x00FF)

    assert np.array_equal(w_m3_b, -w_m3_a), "M3 weights did not negate!"
    assert np.array_equal(w_m8_b, -w_m8_a), "M8 weights did not negate!"
    assert np.array_equal(w_m33_b, -w_m33_a), "M33 weights did not negate!"

    d2_codes = [int(x + 128) for x in tel_a["x_ref"]]
    print(f"  Fixed DAC_2 codes (rows 0..5): {d2_codes} (unsigned 0..255)")
    print(f"  Pattern A W_M3[0]:  {w_m3_a[0].tolist()}  --> Pattern B W_M3[0]:  {w_m3_b[0].tolist()}")
    print(f"  Pattern A W_M8[0]:  {w_m8_a[0].tolist()}  --> Pattern B W_M8[0]:  {w_m8_b[0].tolist()}")
    print(f"  Pattern A W_M33[0]: {w_m33_a[0].tolist()}  --> Pattern B W_M33[0]: {w_m33_b[0].tolist()}")
    print("  [OK] Confirmed 100% exact sign inversion (W_B == -W_A) across all 126 cells (M3, M8, M33).")

    print("\n====================================================================================")
    print(" 2. RUNNING 3-STEP TEST IN A ROW (N = 20 CYCLES):")
    print("    Step 1: OFF Hadamard (Tri-State 0x8000)")
    print("    Step 2: Pattern A (+W) — Time-Separated Mat(3) [0x00FF] then Mat(8) [0x7F00]")
    print("    Step 3: Pattern B (-W) — Time-Separated Mat(3) [0x00FF] then Mat(8) [0x7F00]")
    print("====================================================================================")

    n_cycles = 20

    # Time-separated combined mode (mode 10 = OFF, mode 9 = ON: Sub-Window 1 M3->ADC45, Sub-Window 2 M8->ADC49)
    sep_off_cap45, sep_off_cap49 = [], []
    sep_off_fwht45, sep_off_fwht49 = [], []

    sep_a_cap45, sep_a_cap49 = [], []
    sep_a_fwht45, sep_a_fwht49 = [], []
    sep_a_hiz45, sep_a_hiz49 = [], []

    sep_b_cap45, sep_b_cap49 = [], []
    sep_b_fwht45, sep_b_fwht49 = [], []
    sep_b_hiz45, sep_b_hiz49 = [], []

    # Also capture full ADC_49 response during Sub-Window 1 (M3_ONLY 0x00FF) for Pattern A vs Pattern B
    # so we see how M3 perturbations propagating through M8/M33 into ADC_49 behave when W -> -W!
    m3only_off_cap49, m3only_off_fwht49 = [], []
    m3only_a_cap49,   m3only_a_fwht49   = [], []
    m3only_b_cap49,   m3only_b_fwht49   = [], []

    for i in range(n_cycles):
        # Ensure we are in Pattern A (+W)
        run_diag_hadamard(sock, 4, 0x00FF)

        # --- STEP 1: OFF HADAMARD (Tri-State 0x8000 in both M3 and M8 windows) ---
        r_off_sep = run_diag_hadamard(sock, 10, 0x00FF)
        r_off_m3  = run_diag_hadamard(sock, 5,  0x00FF)
        sep_off_cap45.append(r_off_sep["cap45"])
        sep_off_cap49.append(r_off_sep["cap49"])
        sep_off_fwht45.append(r_off_sep["fwht45"])
        sep_off_fwht49.append(r_off_sep["fwht49"])
        m3only_off_cap49.append(r_off_m3["cap49"])
        m3only_off_fwht49.append(r_off_m3["fwht49"])

        # --- STEP 2: PATTERN A (+W) HADAMARD ON (Time-Separated M3 -> M8) ---
        r_a_sep = run_diag_hadamard(sock, 9, 0x00FF)
        r_a_m3  = run_diag_hadamard(sock, 6, 0x00FF)
        sep_a_cap45.append(r_a_sep["cap45"])
        sep_a_cap49.append(r_a_sep["cap49"])
        sep_a_fwht45.append(r_a_sep["fwht45"])
        sep_a_fwht49.append(r_a_sep["fwht49"])
        sep_a_hiz45.append(r_a_sep["hiz45"])
        sep_a_hiz49.append(r_a_sep["hiz49"])
        m3only_a_cap49.append(r_a_m3["cap49"])
        m3only_a_fwht49.append(r_a_m3["fwht49"])

        # --- STEP 3: PATTERN B (-W = -W_A) FLIP ALL WEIGHT SIGNS & RUN HADAMARD ON ---
        r_b_m3 = run_diag_hadamard(sock, 8, 0x00FF)  # Flips W <- -W and runs M3_ONLY (0x00FF)
        if get_telemetry(sock)["w_m3"][0, 0] != w_m3_b[0, 0]:
            r_b_m3 = run_diag_hadamard(sock, 8, 0x00FF)
        r_b_sep = run_diag_hadamard(sock, 9, 0x00FF)  # Runs Time-Separated M3 (0x00FF) then M8 (0x7F00) at -W
        sep_b_cap45.append(r_b_sep["cap45"])
        sep_b_cap49.append(r_b_sep["cap49"])
        sep_b_fwht45.append(r_b_sep["fwht45"])
        sep_b_fwht49.append(r_b_sep["fwht49"])
        sep_b_hiz45.append(r_b_sep["hiz45"])
        sep_b_hiz49.append(r_b_sep["hiz49"])
        m3only_b_cap49.append(r_b_m3["cap49"])
        m3only_b_fwht49.append(r_b_m3["fwht49"])

    # Convert to numpy arrays
    sep_off_cap45  = np.array(sep_off_cap45,  dtype=np.float64)
    sep_off_cap49  = np.array(sep_off_cap49,  dtype=np.float64)
    sep_off_fwht45 = np.array(sep_off_fwht45, dtype=np.float64)
    sep_off_fwht49 = np.array(sep_off_fwht49, dtype=np.float64)

    sep_a_cap45  = np.array(sep_a_cap45,  dtype=np.float64)
    sep_a_cap49  = np.array(sep_a_cap49,  dtype=np.float64)
    sep_a_fwht45 = np.array(sep_a_fwht45, dtype=np.float64)
    sep_a_fwht49 = np.array(sep_a_fwht49, dtype=np.float64)
    sep_a_hiz45  = np.array(sep_a_hiz45,  dtype=np.float64)
    sep_a_hiz49  = np.array(sep_a_hiz49,  dtype=np.float64)

    sep_b_cap45  = np.array(sep_b_cap45,  dtype=np.float64)
    sep_b_cap49  = np.array(sep_b_cap49,  dtype=np.float64)
    sep_b_fwht45 = np.array(sep_b_fwht45, dtype=np.float64)
    sep_b_fwht49 = np.array(sep_b_fwht49, dtype=np.float64)
    sep_b_hiz45  = np.array(sep_b_hiz45,  dtype=np.float64)
    sep_b_hiz49  = np.array(sep_b_hiz49,  dtype=np.float64)

    m3only_off_cap49  = np.array(m3only_off_cap49,  dtype=np.float64)
    m3only_off_fwht49 = np.array(m3only_off_fwht49, dtype=np.float64)
    m3only_a_cap49    = np.array(m3only_a_cap49,    dtype=np.float64)
    m3only_a_fwht49   = np.array(m3only_a_fwht49,   dtype=np.float64)
    m3only_b_cap49    = np.array(m3only_b_cap49,    dtype=np.float64)
    m3only_b_fwht49   = np.array(m3only_b_fwht49,   dtype=np.float64)

    # Compute summaries
    snr_m3_adc45_a = summarize_pulse_snr(sep_off_cap45, sep_a_cap45)
    snr_m3_adc45_b = summarize_pulse_snr(sep_off_cap45, sep_b_cap45)

    snr_m8_adc49_a = summarize_pulse_snr(sep_off_cap49, sep_a_cap49)
    snr_m8_adc49_b = summarize_pulse_snr(sep_off_cap49, sep_b_cap49)

    snr_m3_adc49_a = summarize_pulse_snr(m3only_off_cap49, m3only_a_cap49)
    snr_m3_adc49_b = summarize_pulse_snr(m3only_off_cap49, m3only_b_cap49)

    # Demodulated derivatives (rows 1..6 = bits 0..5 for M3, rows 9..14 = bits 8..13 for M8)
    der_m3_adc45_off = np.mean(sep_off_fwht45[:, 1:7, :], axis=0)
    der_m3_adc45_a   = np.mean(sep_a_fwht45[:, 1:7, :],   axis=0)
    der_m3_adc45_a_sd = np.std(sep_a_fwht45[:, 1:7, :],   axis=0)
    der_m3_adc45_b   = np.mean(sep_b_fwht45[:, 1:7, :],   axis=0)
    der_m3_adc45_b_sd = np.std(sep_b_fwht45[:, 1:7, :],   axis=0)

    der_m8_adc49_off = np.mean(sep_off_fwht49[:, 9:15, :], axis=0)
    der_m8_adc49_a   = np.mean(sep_a_fwht49[:, 9:15, :],   axis=0)
    der_m8_adc49_a_sd = np.std(sep_a_fwht49[:, 9:15, :],   axis=0)
    der_m8_adc49_b   = np.mean(sep_b_fwht49[:, 9:15, :],   axis=0)
    der_m8_adc49_b_sd = np.std(sep_b_fwht49[:, 9:15, :],   axis=0)

    der_m3_adc49_off = np.mean(m3only_off_fwht49[:, 1:7, :], axis=0)
    der_m3_adc49_a   = np.mean(m3only_a_fwht49[:, 1:7, :],   axis=0)
    der_m3_adc49_a_sd = np.std(m3only_a_fwht49[:, 1:7, :],   axis=0)
    der_m3_adc49_b   = np.mean(m3only_b_fwht49[:, 1:7, :],   axis=0)
    der_m3_adc49_b_sd = np.std(m3only_b_fwht49[:, 1:7, :],   axis=0)

    print("\n--- QUIESCENT DC FORWARD OUTPUT (Hi-Z): PATTERN A (+W) vs PATTERN B (-W) ---")
    print(f"  ADC_45 DC Forward A (+W): {np.round(np.mean(sep_a_hiz45, axis=0), 1)}")
    print(f"  ADC_45 DC Forward B (-W): {np.round(np.mean(sep_b_hiz45, axis=0), 1)}")
    print(f"  ADC_45 Forward Shift (B - A): {np.round(np.mean(sep_b_hiz45 - sep_a_hiz45, axis=0), 1)} LSB")
    print(f"  ADC_49 DC Forward A (+W): {np.round(np.mean(sep_a_hiz49, axis=0), 1)}")
    print(f"  ADC_49 DC Forward B (-W): {np.round(np.mean(sep_b_hiz49, axis=0), 1)}")
    print(f"  ADC_49 Forward Shift (B - A): {np.round(np.mean(sep_b_hiz49 - sep_a_hiz49, axis=0), 1)} LSB")

    print("\n--- SUB-WINDOW 1 (M3_ONLY 0x00FF, M8 TRI-STATE) ON ADC_45 ---")
    print(f"  Carrier SNR A (+W) (dB): {np.round(snr_m3_adc45_a['snr_db'], 1)}")
    print(f"  Carrier SNR B (-W) (dB): {np.round(snr_m3_adc45_b['snr_db'], 1)}")
    print(f"  Demodulated Derivative dY45/dV_M3 Row 3 A (+W): {np.round(der_m3_adc45_a[3], 1)}")
    print(f"  Demodulated Derivative dY45/dV_M3 Row 3 B (-W): {np.round(der_m3_adc45_b[3], 1)}")
    print(f"  Difference (B - A) Row 3:                       {np.round(der_m3_adc45_b[3] - der_m3_adc45_a[3], 1)}")

    print("\n--- SUB-WINDOW 1 (M3_ONLY 0x00FF, M8 TRI-STATE) PROPAGATED TO ADC_49 ---")
    print(f"  Carrier SNR A (+W) on ADC_49 (dB): {np.round(snr_m3_adc49_a['snr_db'], 1)}")
    print(f"  Carrier SNR B (-W) on ADC_49 (dB): {np.round(snr_m3_adc49_b['snr_db'], 1)}")
    print(f"  Propagated Derivative dY49/dV_M3 Row 3 A (+W): {np.round(der_m3_adc49_a[3], 1)}")
    print(f"  Propagated Derivative dY49/dV_M3 Row 3 B (-W): {np.round(der_m3_adc49_b[3], 1)}")
    print(f"  Difference (B - A) Row 3:                      {np.round(der_m3_adc49_b[3] - der_m3_adc49_a[3], 1)}")

    print("\n--- SUB-WINDOW 2 (M8_ONLY 0x7F00, M3 TRI-STATE) ON ADC_49 ---")
    print(f"  Carrier SNR A (+W) on ADC_49 (dB): {np.round(snr_m8_adc49_a['snr_db'], 1)}")
    print(f"  Carrier SNR B (-W) on ADC_49 (dB): {np.round(snr_m8_adc49_b['snr_db'], 1)}")
    print(f"  Direct Derivative dY49/dV_M8 Row 3 A (+W):     {np.round(der_m8_adc49_a[3], 1)}")
    print(f"  Direct Derivative dY49/dV_M8 Row 3 B (-W):     {np.round(der_m8_adc49_b[3], 1)}")
    print(f"  Difference (B - A) Row 3:                      {np.round(der_m8_adc49_b[3] - der_m8_adc49_a[3], 1)}")

    # Leave board in run_mode = 3 (Time-Separated M3 then M8 bursts at 2.0 ms post-refresh)
    set_run_mode(sock, 3)
    print("\n[+] Board placed in run_mode=3 (Time-Separated M3 [0x00FF] -> 20us Hi-Z -> M8 [0x7F00] @ 2.0ms post-refresh).")

    out_data = {
        "metadata": {
            "n_cycles": n_cycles,
            "dac2_unsigned_codes": d2_codes,
            "x_ref_signed": tel_a["x_ref"],
            "w_m3_pattern_a": w_m3_a.tolist(),
            "w_m3_pattern_b": w_m3_b.tolist(),
            "w_m8_pattern_a": w_m8_a.tolist(),
            "w_m8_pattern_b": w_m8_b.tolist(),
            "w_m33_pattern_a": w_m33_a.tolist(),
            "w_m33_pattern_b": w_m33_b.tolist(),
        },
        "dc_forward_hiz": {
            "adc45_pattern_a": np.mean(sep_a_hiz45, axis=0).tolist(),
            "adc45_pattern_b": np.mean(sep_b_hiz45, axis=0).tolist(),
            "adc45_diff_b_minus_a": np.mean(sep_b_hiz45 - sep_a_hiz45, axis=0).tolist(),
            "adc49_pattern_a": np.mean(sep_a_hiz49, axis=0).tolist(),
            "adc49_pattern_b": np.mean(sep_b_hiz49, axis=0).tolist(),
            "adc49_diff_b_minus_a": np.mean(sep_b_hiz49 - sep_a_hiz49, axis=0).tolist(),
        },
        "subwindow1_m3_on_adc45": {
            "pattern_a": snr_m3_adc45_a,
            "pattern_b": snr_m3_adc45_b,
            "der_off_mean": der_m3_adc45_off.tolist(),
            "der_a_mean": der_m3_adc45_a.tolist(),
            "der_a_std": der_m3_adc45_a_sd.tolist(),
            "der_b_mean": der_m3_adc45_b.tolist(),
            "der_b_std": der_m3_adc45_b_sd.tolist(),
            "der_diff_b_minus_a": (der_m3_adc45_b - der_m3_adc45_a).tolist(),
        },
        "subwindow1_m3_propagated_to_adc49": {
            "pattern_a": snr_m3_adc49_a,
            "pattern_b": snr_m3_adc49_b,
            "der_off_mean": der_m3_adc49_off.tolist(),
            "der_a_mean": der_m3_adc49_a.tolist(),
            "der_a_std": der_m3_adc49_a_sd.tolist(),
            "der_b_mean": der_m3_adc49_b.tolist(),
            "der_b_std": der_m3_adc49_b_sd.tolist(),
            "der_diff_b_minus_a": (der_m3_adc49_b - der_m3_adc49_a).tolist(),
        },
        "subwindow2_m8_on_adc49": {
            "pattern_a": snr_m8_adc49_a,
            "pattern_b": snr_m8_adc49_b,
            "der_off_mean": der_m8_adc49_off.tolist(),
            "der_a_mean": der_m8_adc49_a.tolist(),
            "der_a_std": der_m8_adc49_a_sd.tolist(),
            "der_b_mean": der_m8_adc49_b.tolist(),
            "der_b_std": der_m8_adc49_b_sd.tolist(),
            "der_diff_b_minus_a": (der_m8_adc49_b - der_m8_adc49_a).tolist(),
        },
    }

    out_path = Path("FPGA_code/docs/hadamard_separated_weight_flip_live_results.json")
    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2)
    print(f"[+] Saved complete live dataset to {out_path}")


if __name__ == "__main__":
    main()
