#!/usr/bin/env python3
"""
verify_24us_hadamard_snr.py
===========================
100% Pure Live Hardware Verification of the Contiguous 24.00 us (2x6 x 2.00 us)
Hadamard Table at 2.0 ms after Refresh on the T120 + T20 Inverted MAML Board.

ZERO SIMULATION POLICY (enforced by maml_anti_simulation_enforcer):
Every single measurement in this script is read directly from the physical
XC2361A 12-bit differential ADCs (ADC_45 and ADC_49) over UDP from 192.168.1.50:5000.

Test Protocol:
1. Lock DAC_2 input rows to evenly distributed fixed values across 0..255:
   DAC_2 = [0, 51, 102, 153, 204, 255] (signed offsets [-128, -77, -26, +25, +76, +127]).
2. Randomize all weights (M3, M8, M33) once and keep them 100% fixed throughout the test.
3. Place the 24.00 us (2x6 = 12 pulses x 2.00 us, zero tri-state gaps) Hadamard burst
   at 2.0 ms after refresh, sampling ADC_45 & ADC_49 at the end of each 2.00 us pulse.
4. Alternate every other 10 ms refresh period between:
   - Hadamard OFF (Tri-State 0x8000 across all 12 x 2.00 us slots)
   - Hadamard ON  (Contiguous 2x6 (+) and (-) table across all 12 x 2.00 us slots)
5. Compute true physical carrier signal, noise floor, repeatability, and SNR (dB)
   on ADC_45 and ADC_49 to determine whether real derivatives can be extracted on T120.
"""

import socket
import struct
import time
import json
import numpy as np

BOARD_IP   = "192.168.1.50"
BOARD_PORT = 5000
MAML_MAGIC = 0x4D414D4C

HADAMARD_2X6_POS = [0x2AAA, 0x1999, 0x4CCC, 0x0787, 0x52D2, 0x61E1]


def udp_xact(sock, payload):
    sock.sendto(payload, (BOARD_IP, BOARD_PORT))
    data, _ = sock.recvfrom(4096)
    return data


def get_telemetry(sock):
    pkt = struct.pack("<IB", MAML_MAGIC, 0x10)
    data = udp_xact(sock, pkt)
    x_ref  = struct.unpack_from("<6h", data, 40)
    z_tgt  = struct.unpack_from("<6h", data, 52)
    adc45  = struct.unpack_from("<6h", data, 64)
    adc49  = struct.unpack_from("<6h", data, 76)
    w_m3   = np.frombuffer(data, dtype=np.int8, count=48, offset=100).reshape(8, 6).copy()
    w_m8   = np.frombuffer(data, dtype=np.int8, count=42, offset=148).reshape(7, 6).copy()
    w_m33  = np.frombuffer(data, dtype=np.int8, count=36, offset=190).reshape(6, 6).copy()
    return {
        "x_ref": x_ref,
        "z_target": z_tgt,
        "adc45_sig": adc45,
        "adc49_sig": adc49,
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
        "h_words": h_words[:13],
        "ack_ok": ack_ok,
        "ack_miss": ack_miss,
        "lat_last": lat_last,
        "lat_min": lat_min,
        "lat_max": lat_max,
        "t20_word_cnt": t20_wcnt,
        "t20_sync_err": t20_serr,
        "settle_cycles": settle_cyc,
        "hiz45": hiz45,
        "hiz49": hiz49,
        "cap45": cap45[:12],   # 12 pulses (0..5 = (+) table, 6..11 = (-) table)
        "cap49": cap49[:12],
        "fwht45": fwht45,
        "fwht49": fwht49,
    }


def set_run_mode(sock, run_mode):
    # MAML_CMD_SET_CONFIG (0x11): magic(4), cmd(1), run_mode(1), jumper_mode(1),
    # hadamard_freq_khz(2), max_duty(1), inner_n(2), strata_m(1), trim38(1), hid_amp(1)
    pkt = struct.pack("<IBBBHBHBbB", MAML_MAGIC, 0x11, run_mode, 3, 500, 25, 100, 10, 0, 14)
    udp_xact(sock, pkt)


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(3.0)

    # Ensure IDLE during controlled UDP alternating measurement
    set_run_mode(sock, 0)

    print("=========================================================================")
    print(" 1. INITIALIZING FIXED DAC_2 [0..255] & FIXED RANDOM WEIGHTS (MODE 4)")
    print("=========================================================================")
    init_res = run_diag_hadamard(sock, 4, 0x7FFF)
    tel = get_telemetry(sock)
    d2_codes = [int(x + 128) for x in tel["x_ref"]]
    print(f"  Fixed DAC_2 codes (rows 0..5): {d2_codes}  (x_ref = {list(tel['x_ref'])})")
    print(f"  Fixed M3 weights (row 0..1):   {tel['w_m3'][0].tolist()} / {tel['w_m3'][1].tolist()}")
    print(f"  Fixed M8 weights (row 0..1):   {tel['w_m8'][0].tolist()} / {tel['w_m8'][1].tolist()}")
    print(f"  Fixed M33 weights (row 0..1):  {tel['w_m33'][0].tolist()} / {tel['w_m33'][1].tolist()}")
    print(f"  H-bus 13-word table (0..11 active, 12=Hi-Z): {[f'0x{w:04X}' for w in init_res['h_words']]}")
    print(f"  H-bus ACK OK={init_res['ack_ok']}, MISS={init_res['ack_miss']}, "
          f"LAT min/max={init_res['lat_min']}/{init_res['lat_max']} CLK9 cycles, "
          f"T20 sync_err={init_res['t20_sync_err']}")

    print("\n=========================================================================")
    print(" 2. CHECKING XC2361A ADC SPEED AT 2.00 us/PULSE: sck_div=2 (12.5 MHz) vs sck_div=1 (25 MHz)")
    print("=========================================================================")
    r_sck2 = run_diag_hadamard(sock, 6, 0x7FFF)
    r_sck1 = run_diag_hadamard(sock, 7, 0x7FFF)
    diff45_sck = np.abs(r_sck2["cap45"] - r_sck1["cap45"]).mean(axis=0)
    diff49_sck = np.abs(r_sck2["cap49"] - r_sck1["cap49"]).mean(axis=0)
    print(f"  sck_div=2 (12.5 MHz SCK, 1.28 us shift) cap45 ptp across 12 pulses: {np.ptp(r_sck2['cap45'], axis=0)}")
    print(f"  sck_div=1 (25.0 MHz SCK, 0.64 us shift) cap45 ptp across 12 pulses: {np.ptp(r_sck1['cap45'], axis=0)}")
    print(f"  sck_div=2 (12.5 MHz SCK, 1.28 us shift) cap49 ptp across 12 pulses: {np.ptp(r_sck2['cap49'], axis=0)}")
    print(f"  sck_div=1 (25.0 MHz SCK, 0.64 us shift) cap49 ptp across 12 pulses: {np.ptp(r_sck1['cap49'], axis=0)}")
    print(f"  Mean |sck_div=2 - sck_div=1| difference: ADC_45={np.round(diff45_sck, 1)} LSB, ADC_49={np.round(diff49_sck, 1)} LSB")

    results_summary = {}

    for mask_name, en_mask in [
        ("BOTH_M3_AND_M8 (0x7FFF)", 0x7FFF),
        ("M3_ONLY (0x00FF)",        0x00FF),
        ("M8_ONLY (0x7F00)",        0x7F00),
    ]:
        print(f"\n=========================================================================")
        print(f" 3. ALTERNATING OFF (TRI-STATE) vs ON (24us 2x6 TABLE) @ 2ms AFTER REFRESH: {mask_name}")
        print(f"=========================================================================")
        n_pairs = 20
        off_cap45_list, on_cap45_list = [], []
        off_cap49_list, on_cap49_list = [], []
        off_fwht45_list, on_fwht45_list = [], []
        off_fwht49_list, on_fwht49_list = [], []

        for i in range(n_pairs):
            # Period A: Hadamard OFF (Tri-State 0x8000) at 2.0 ms after refresh
            res_off = run_diag_hadamard(sock, 5, en_mask)
            # Period B: Hadamard ON (24.00 us 2x6 contiguous table) at 2.0 ms after refresh
            res_on  = run_diag_hadamard(sock, 6, en_mask)

            off_cap45_list.append(res_off["cap45"])
            on_cap45_list.append(res_on["cap45"])
            off_cap49_list.append(res_off["cap49"])
            on_cap49_list.append(res_on["cap49"])

            off_fwht45_list.append(res_off["fwht45"])
            on_fwht45_list.append(res_on["fwht45"])
            off_fwht49_list.append(res_off["fwht49"])
            on_fwht49_list.append(res_on["fwht49"])

        off_cap45 = np.array(off_cap45_list, dtype=np.float64)  # (N, 12, 6)
        on_cap45  = np.array(on_cap45_list,  dtype=np.float64)
        off_cap49 = np.array(off_cap49_list, dtype=np.float64)
        on_cap49  = np.array(on_cap49_list,  dtype=np.float64)

        off_fwht45 = np.array(off_fwht45_list, dtype=np.float64) # (N, 16, 6)
        on_fwht45  = np.array(on_fwht45_list,  dtype=np.float64)
        off_fwht49 = np.array(off_fwht49_list, dtype=np.float64)
        on_fwht49  = np.array(on_fwht49_list,  dtype=np.float64)

        # (+) - (-) differential pulse response dY[p] = Y[p] - Y[p+6] for p=0..5
        dy_off_45 = off_cap45[:, :6, :] - off_cap45[:, 6:12, :]  # (N, 6, 6)
        dy_on_45  = on_cap45[:, :6, :]  - on_cap45[:, 6:12, :]
        dy_off_49 = off_cap49[:, :6, :] - off_cap49[:, 6:12, :]
        dy_on_49  = on_cap49[:, :6, :]  - on_cap49[:, 6:12, :]

        # Carrier RMS amplitude of dY = Y(+) - Y(-) in ON vs OFF
        rms_dy_off_45 = np.sqrt(np.mean(dy_off_45 ** 2, axis=(0, 1)))
        rms_dy_on_45  = np.sqrt(np.mean(dy_on_45  ** 2, axis=(0, 1)))
        rms_dy_off_49 = np.sqrt(np.mean(dy_off_49 ** 2, axis=(0, 1)))
        rms_dy_on_49  = np.sqrt(np.mean(dy_on_49  ** 2, axis=(0, 1)))

        # Peak-to-peak across the 12 pulses (mean over N runs)
        ptp_off_45 = np.mean(np.ptp(off_cap45, axis=1), axis=0)
        ptp_on_45  = np.mean(np.ptp(on_cap45,  axis=1), axis=0)
        ptp_off_49 = np.mean(np.ptp(off_cap49, axis=1), axis=0)
        ptp_on_49  = np.mean(np.ptp(on_cap49,  axis=1), axis=0)

        # True carrier signal isolated by subtracting average OFF baseline trace (cancels any residual 24us slope)
        net_carrier_45 = np.mean(on_cap45 - off_cap45, axis=0)  # (12, 6)
        net_carrier_49 = np.mean(on_cap49 - off_cap49, axis=0)  # (12, 6)
        noise_std_45   = np.std(on_cap45 - off_cap45, axis=0).mean(axis=0) / np.sqrt(2.0)
        noise_std_49   = np.std(on_cap49 - off_cap49, axis=0).mean(axis=0) / np.sqrt(2.0)

        snr_on_vs_off_45_db = 20.0 * np.log10(np.maximum(rms_dy_on_45, 1e-3) / np.maximum(rms_dy_off_45, 1e-3))
        snr_on_vs_off_49_db = 20.0 * np.log10(np.maximum(rms_dy_on_49, 1e-3) / np.maximum(rms_dy_off_49, 1e-3))

        # Demodulated derivative SNR across the 20 runs: |mean(fwht_on)| / std(fwht_on)
        # Rows 1..6 (bits 0..5 = M3 rows 0..5) and Rows 9..14 (bits 8..13 = M8 rows 0..5)
        m3_der_mean_45 = np.mean(on_fwht45[:, 1:7, :], axis=0)
        m3_der_std_45  = np.std(on_fwht45[:, 1:7, :],  axis=0)
        m3_der_off_45  = np.mean(np.abs(off_fwht45[:, 1:7, :]), axis=0)

        m3_der_mean_49 = np.mean(on_fwht49[:, 1:7, :], axis=0)
        m3_der_std_49  = np.std(on_fwht49[:, 1:7, :],  axis=0)
        m3_der_off_49  = np.mean(np.abs(off_fwht49[:, 1:7, :]), axis=0)

        m8_der_mean_49 = np.mean(on_fwht49[:, 9:15, :], axis=0)
        m8_der_std_49  = np.std(on_fwht49[:, 9:15, :],  axis=0)
        m8_der_off_49  = np.mean(np.abs(off_fwht49[:, 9:15, :]), axis=0)

        print(f"  [ADC_45] 12-pulse Peak-to-Peak (LSB):")
        print(f"    Hadamard OFF (Tri-State): {np.round(ptp_off_45, 1)}")
        print(f"    Hadamard ON  (24us 2x6):  {np.round(ptp_on_45, 1)}")
        print(f"  [ADC_45] Differential Y(+)-Y(-) RMS (LSB):")
        print(f"    Hadamard OFF (Tri-State): {np.round(rms_dy_off_45, 2)}")
        print(f"    Hadamard ON  (24us 2x6):  {np.round(rms_dy_on_45, 2)}")
        print(f"    ON/OFF Carrier SNR (dB):  {np.round(snr_on_vs_off_45_db, 1)} dB")

        print(f"  [ADC_49] 12-pulse Peak-to-Peak (LSB):")
        print(f"    Hadamard OFF (Tri-State): {np.round(ptp_off_49, 1)}")
        print(f"    Hadamard ON  (24us 2x6):  {np.round(ptp_on_49, 1)}")
        print(f"  [ADC_49] Differential Y(+)-Y(-) RMS (LSB):")
        print(f"    Hadamard OFF (Tri-State): {np.round(rms_dy_off_49, 2)}")
        print(f"    Hadamard ON  (24us 2x6):  {np.round(rms_dy_on_49, 2)}")
        print(f"    ON/OFF Carrier SNR (dB):  {np.round(snr_on_vs_off_49_db, 1)} dB")

        print(f"  [Demodulated Derivatives |Signal| vs OFF Floor & Run-to-Run Std]:")
        print(f"    ADC_45 (M3 rows 0..5): mean|der_ON|={np.mean(np.abs(m3_der_mean_45)):.1f} LSB, "
              f"mean|der_OFF|={np.mean(m3_der_off_45):.1f} LSB, run-std={np.mean(m3_der_std_45):.1f} LSB")
        print(f"    ADC_49 (M3 rows 0..5): mean|der_ON|={np.mean(np.abs(m3_der_mean_49)):.1f} LSB, "
              f"mean|der_OFF|={np.mean(m3_der_off_49):.1f} LSB, run-std={np.mean(m3_der_std_49):.1f} LSB")
        print(f"    ADC_49 (M8 rows 0..5): mean|der_ON|={np.mean(np.abs(m8_der_mean_49)):.1f} LSB, "
              f"mean|der_OFF|={np.mean(m8_der_off_49):.1f} LSB, run-std={np.mean(m8_der_std_49):.1f} LSB")

        results_summary[mask_name] = {
            "ptp_off_45": ptp_off_45.tolist(),
            "ptp_on_45": ptp_on_45.tolist(),
            "rms_dy_off_45": rms_dy_off_45.tolist(),
            "rms_dy_on_45": rms_dy_on_45.tolist(),
            "snr_on_vs_off_45_db": snr_on_vs_off_45_db.tolist(),
            "ptp_off_49": ptp_off_49.tolist(),
            "ptp_on_49": ptp_on_49.tolist(),
            "rms_dy_off_49": rms_dy_off_49.tolist(),
            "rms_dy_on_49": rms_dy_on_49.tolist(),
            "snr_on_vs_off_49_db": snr_on_vs_off_49_db.tolist(),
            "mean_on_cap45": np.mean(on_cap45, axis=0).tolist(),
            "mean_off_cap45": np.mean(off_cap45, axis=0).tolist(),
            "mean_on_cap49": np.mean(on_cap49, axis=0).tolist(),
            "mean_off_cap49": np.mean(off_cap49, axis=0).tolist(),
            "m3_der_mean_45": m3_der_mean_45.tolist(),
            "m3_der_std_45": m3_der_std_45.tolist(),
            "m8_der_mean_49": m8_der_mean_49.tolist(),
            "m8_der_std_49": m8_der_std_49.tolist(),
        }

    # Put board into run_mode = 3 so the oscilloscope shows continuous 10ms refresh -> 2ms -> alternating OFF/ON 24us burst
    set_run_mode(sock, 3)
    print("\n[+] Board placed in run_mode=3 (Autonomous 10ms Refresh -> 2.0ms delay -> Alternating OFF/ON 24.00us 2x6 Burst for Oscilloscope).")

    with open("/tmp/hadamard_24us_live_results.json", "w") as f:
        json.dump(results_summary, f, indent=2)


if __name__ == "__main__":
    main()

