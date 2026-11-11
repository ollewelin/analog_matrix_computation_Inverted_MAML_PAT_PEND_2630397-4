#!/home/olle/anaconda3/bin/python
"""
run_card1_2beat_bit_slicing.py
==============================
Inverted MAML (Patent Pending SE 2630397-4) - Open Science Hardware

2-Beat Interleaved Analog Bit Slicing on Card 1:
- Operates on 1 physical card (Card 1 @ 192.168.1.50)
- Scaled M33 Matched-Pedestal Slices: Max |W| = 60 LSB
- Beat 2k   (MSB Beat): Loads M33_MSB, dedicated MSB state (W_M3_MSB, W_M8_MSB), runs SGD on MSB state
- Beat 2k+1 (LSB Beat): Loads M33_LSB, dedicated LSB state (W_M3_LSB, W_M8_LSB), runs SGD on LSB state
- True Hardware Telemetry ENOB computed per beat and shift-and-add combined
"""

from __future__ import annotations
import sys
import os
import time
import json
import math
import struct
import signal
import argparse
from pathlib import Path
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from gui.udp_client import (
    MamlUdpClient,
    MAML_CMD_CENTER_WEIGHTS,
    MAML_CMD_BATCH_STEP,
    COLOR_WHITE,
)
from FPGA_code.scripts.verify_and_guard_version import ensure_version_guard
from FPGA_code.config.w3_staircase_pattern import (
    build_center_weights_payload,
    get_staircase_config,
)

running = True
client_global: MamlUdpClient | None = None

def safe_shutdown(sig=None, frame=None):
    global running, client_global
    print("\n[!] Shutting down 2-beat bit slicing cleanly...")
    running = False
    if client_global is not None:
        try:
            print("[*] Resetting M33 to default...")
            client_global.set_w33_matrix(None)
            time.sleep(0.05)
            print("[*] Resetting compensation weights W8=0...")
            payload = build_center_weights_payload(1)
            client_global._send_binary(MAML_CMD_CENTER_WEIGHTS, payload)
            client_global.close()
        except Exception as e:
            print(f"[!] Warning during shutdown: {e}")
    print("[+] Safe shutdown complete.")
    if sig is not None:
        os._exit(0)

signal.signal(signal.SIGINT, safe_shutdown)
signal.signal(signal.SIGTERM, safe_shutdown)

def drain_udp(client: MamlUdpClient):
    try:
        old_to = client.sock.gettimeout()
        client.sock.settimeout(0.002)
        while True:
            client.sock.recvfrom(2048)
    except Exception:
        pass
    finally:
        try:
            client.sock.settimeout(old_to)
        except Exception:
            pass

def build_custom_weights_payload(w_m3: list[list[int]], w_m8: list[list[int]], baseline_mode: int = 1) -> bytes:
    flat_m3 = []
    for r in range(8):
        for c in range(6):
            w = int(w_m3[r][c])
            flat_m3.append(max(-128, min(127, w)))
            
    flat_m8 = []
    for r in range(7):
        for c in range(6):
            w = int(w_m8[r][c])
            flat_m8.append(max(-128, min(127, w)))
            
    return struct.pack("<B48b42b", baseline_mode, *flat_m3, *flat_m8)

def execute_hardware_beat(
    client: MamlUdpClient,
    delay_us: int,
    lr_q16: int,
    reg_q16: int,
    k_batch: int = 1
) -> dict:
    pkt = struct.pack(
        "<BBHHHH",
        k_batch,
        1, # num_strata = 1
        delay_us,
        delay_us,
        lr_q16,
        reg_q16
    )
    raw = None
    for attempt in range(15):
        if attempt > 0:
            drain_udp(client)
        raw = client._send_binary(MAML_CMD_BATCH_STEP, pkt)
        if raw is not None and len(raw) >= client.TELEM_SIZE:
            break
        time.sleep(0.01 * min(attempt + 1, 5))
        
    if raw is None or len(raw) < client.TELEM_SIZE:
        raise RuntimeError(f"Could not receive telemetry from hardware for delay {delay_us} us.")
        
    telem = client._parse_hw_telemetry(raw)
    err = np.array(telem.adc49_sig, dtype=np.float64) - np.array(telem.z_target, dtype=np.float64)
    rmse = float(np.sqrt(np.mean(err**2)))
    enob = max(0.0, 11.0 - math.log2(max(rmse, 1.0)))
    
    return {
        "rmse_lsb": rmse,
        "enob_bits": enob,
        "telem": telem
    }

def main():
    global client_global, running
    parser = argparse.ArgumentParser(description="Card 1 2-Beat Interleaved Bit Slicing")
    parser.add_argument("--ip", type=str, default="192.168.1.50")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--pairs", type=int, default=100, help="Number of 2-beat pairs to execute")
    parser.add_argument("--delay-us", type=int, default=5200, help="Snapshot delay (default 5200 us = 5.2 ms)")
    parser.add_argument("--lr", type=float, default=0.02, help="Learning rate (default 0.02)")
    parser.add_argument("--l2-reg", type=int, default=768, help="L2 regularization (default 768)")
    parser.add_argument("--out-json", type=str, default="FPGA_code/logs/bit_slicing/card1_2beat_slicing_k1_w60.json")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.out_json), exist_ok=True)

    print("=" * 80)
    print("  INVERTED MAML: 2-BEAT INTERLEAVED ANALOG BIT SLICING")
    print(f"  Hardware: Card 1 @ {args.ip}:{args.port} | Delay: {args.delay_us} us | K = 1")
    print(f"  Hyperparams: LR = {args.lr}, L2 = {args.l2_reg} | Max M33 = ±60 LSB")
    print("=" * 80)

    # 1. Version guard check
    ensure_version_guard(host=args.ip, port=args.port)
    client = MamlUdpClient(args.ip, args.port)
    client_global = client

    # 2. Build Matched-Pedestal Slices for M33 (Scaled to ±60 LSB)
    k_default_m33 = np.array([
        [+76, -20, +28,  -4, +44, -36],
        [-20, +84, -12, +44,  -4, +36],
        [+36,  -4, +80, -16, +32,  -4],
        [ -4, +40,  -8, +72, -12, +44],
        [+44, -12, +28, -12, +76,  -8],
        [-28, +32,  -4, +40,  -8, +82]
    ])
    M_msb = np.round(k_default_m33 * (60.0 / 84.0)).astype(np.int32)
    # LSB slice with slightly lower amplitude but identical pedestal stability
    M_lsb = np.round(M_msb * 0.75).astype(np.int32)

    W_msb_silicon = M_msb.tolist()
    W_lsb_silicon = M_lsb.tolist()

    print(f"\n[Matrix Slices]")
    print(f"M_msb range : [{M_msb.min()}, {M_msb.max()}] LSB")
    print(f"M_lsb range : [{M_lsb.min()}, {M_lsb.max()}] LSB")

    # 3. Hardware Initialization
    print("\n[*] Initializing silicon operating point...")
    client.clear_w33_hidden_offset()
    time.sleep(0.03)

    client.set_gain_experiment(d_line=2, w33=1, target_gain=1.0, clamp=120)
    time.sleep(0.03)

    lr_q16 = int(round(args.lr * 1024.0))
    reg_q16 = args.l2_reg

    client.set_config(
        mode=0, jumper_mode=3, led_switches=3, max_meas_win_pct=100, hadamard_khz=500,
        inner_loop_n=100, seed_pct=28, seed_mode=1, w_hid_mag=0, trim_hid_mag=0,
        hadamard_delay_us=args.delay_us, lr_inner_q16=lr_q16
    )
    time.sleep(0.03)
    client._send_binary(0x13, struct.pack("<BB", 1, 1))  # LEDs ON
    time.sleep(0.02)
    client.set_data_color(COLOR_WHITE, 0.0)
    time.sleep(0.03)

    cfg = get_staircase_config()
    init_payload = build_center_weights_payload(1)
    
    # Extract baseline staircase W_M3 and W_M8
    state_msb = {
        "w_m3": [row[:] for row in cfg.get("w_m3", [[0]*6 for _ in range(8)])],
        "w_m8": [[0]*6 for _ in range(7)]
    }
    state_lsb = {
        "w_m3": [row[:] for row in cfg.get("w_m3", [[0]*6 for _ in range(8)])],
        "w_m8": [[0]*6 for _ in range(7)]
    }

    # Quiescent zero baseline calibration
    zero_cal_payload = struct.pack("<B48b42b", 0, *([0] * 48), *([0] * 42))
    client._send_binary(MAML_CMD_CENTER_WEIGHTS, zero_cal_payload)
    time.sleep(0.05)
    client._send_binary(MAML_CMD_CENTER_WEIGHTS, init_payload)
    time.sleep(0.05)

    history = []
    print("\n[+] STARTING 2-BEAT INTERLEAVED EXECUTION:")
    print("    Beat 2k = MSB slice | Beat 2k+1 = LSB slice | Recombine = (MSB << 4) + LSB\n")

    t_start = time.time()
    for pair_idx in range(args.pairs):
        if not running:
            break

        # =====================================================================
        # BEAT 2k: MSB SLICE
        # =====================================================================
        client.set_w33_matrix(W_msb_silicon)
        payload_msb = build_custom_weights_payload(state_msb["w_m3"], state_msb["w_m8"], 1)
        client._send_binary(MAML_CMD_CENTER_WEIGHTS, payload_msb)
        
        res_msb = execute_hardware_beat(client, args.delay_us, lr_q16, reg_q16, k_batch=1)
        telem_msb = res_msb["telem"]
        state_msb["w_m3"] = [r[:] for r in telem_msb.w_m3]
        state_msb["w_m8"] = [r[:] for r in telem_msb.w_m8]

        # =====================================================================
        # BEAT 2k+1: LSB SLICE
        # =====================================================================
        client.set_w33_matrix(W_lsb_silicon)
        payload_lsb = build_custom_weights_payload(state_lsb["w_m3"], state_lsb["w_m8"], 1)
        client._send_binary(MAML_CMD_CENTER_WEIGHTS, payload_lsb)
        
        res_lsb = execute_hardware_beat(client, args.delay_us, lr_q16, reg_q16, k_batch=1)
        telem_lsb = res_lsb["telem"]
        state_lsb["w_m3"] = [r[:] for r in telem_lsb.w_m3]
        state_lsb["w_m8"] = [r[:] for r in telem_lsb.w_m8]

        # =====================================================================
        # RECOMBINATION
        # =====================================================================
        enob_msb = res_msb["enob_bits"]
        enob_lsb = res_lsb["enob_bits"]
        rmse_msb = res_msb["rmse_lsb"]
        rmse_lsb = res_lsb["rmse_lsb"]
        
        # Combined RMSE and ENOB (full 8-bit scale):
        combined_rmse = math.sqrt((16.0 * rmse_msb)**2 + (rmse_lsb)**2)
        combined_enob_raw = max(0.0, 15.0 - math.log2(max(combined_rmse, 1.0)))

        w8_msb_min = min(min(r) for r in state_msb["w_m8"])
        w8_msb_max = max(max(r) for r in state_msb["w_m8"])
        w8_lsb_min = min(min(r) for r in state_lsb["w_m8"])
        w8_lsb_max = max(max(r) for r in state_lsb["w_m8"])

        history.append({
            "pair": pair_idx,
            "enob_msb": round(enob_msb, 2),
            "enob_lsb": round(enob_lsb, 2),
            "combined_enob_raw": round(combined_enob_raw, 2),
            "w8_msb_range": [w8_msb_min, w8_msb_max],
            "w8_lsb_range": [w8_lsb_min, w8_lsb_max],
        })

        if (pair_idx + 1) % 5 == 0 or pair_idx == 0:
            print(f"Pair {pair_idx+1:3d}/{args.pairs:3d} | "
                  f"MSB: {enob_msb:.2f} b (W8: [{w8_msb_min:+3d}, {w8_msb_max:+3d}]) | "
                  f"LSB: {enob_lsb:.2f} b (W8: [{w8_lsb_min:+3d}, {w8_lsb_max:+3d}]) | "
                  f"Comb: {combined_enob_raw:.2f} b")

    with open(args.out_json, "w") as f:
        json.dump({
            "w_msb": W_msb_silicon,
            "w_lsb": W_lsb_silicon,
            "history": history
        }, f, indent=2)

    print(f"\n[+] Experiment Complete! Saved {len(history)} 2-beat pairs to {args.out_json}")
    safe_shutdown()

if __name__ == "__main__":
    main()
