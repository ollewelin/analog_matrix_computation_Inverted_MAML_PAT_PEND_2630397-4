#!/home/olle/anaconda3/bin/python
"""
run_card1_thermal_bit_slicing.py
================================
Inverted MAML (Patent Pending SE 2630397-4) - Open Science Hardware

Full Thermal Stress & Closed-Loop 2-Beat Interleaved Bit-Slicing on Card 1:
- Thermal Stress: 30% PWM Heater Duty @ 1.0 Hz (4 min OFF / 4 min ON)
- Mode A Regulation: 2 min ON (SGD active, LR=0.02, L2=768, K=1) <-> 2 min OFF (W8=0 ablation)
- 2-Beat Interleaved Slicing:
  * Beat 2k   (MSB Beat): Loads M33_MSB, dedicated MSB state (W_M3_MSB, W_M8_MSB)
  * Beat 2k+1 (LSB Beat): Loads M33_LSB, dedicated LSB state (W_M3_LSB, W_M8_LSB)
- Live Atomic Ring Buffer & Status Logging for Bit-Slicing GUI:
  * FPGA_code/logs/bit_slicing/slicing_ring_buffer.json
  * FPGA_code/logs/bit_slicing/slicing_latest_status.json
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
from collections import deque
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

LOG_DIR = REPO_ROOT / "FPGA_code" / "logs" / "bit_slicing"
LOG_DIR.mkdir(parents=True, exist_ok=True)
RING_BUFFER_JSON = LOG_DIR / "slicing_ring_buffer.json"
RING_BUFFER_TMP = LOG_DIR / "slicing_ring_buffer.json.tmp"
LATEST_STATUS_JSON = LOG_DIR / "slicing_latest_status.json"
LATEST_STATUS_TMP = LOG_DIR / "slicing_latest_status.json.tmp"

running = True
client_global: MamlUdpClient | None = None

def safe_shutdown(sig=None, frame=None):
    global running, client_global
    print("\n[!] Shutting down experiment cleanly...")
    running = False
    if client_global is not None:
        try:
            print("[*] Turning OFF all on-board heaters (0% power)...")
            client_global.set_heaters(False, [0, 0, 0, 0])
            time.sleep(0.05)
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
    loss_lsb2 = float(np.mean(err**2))
    rmse = float(np.sqrt(loss_lsb2))
    enob = max(0.0, 11.0 - math.log2(max(rmse, 1.0)))
    
    return {
        "loss_lsb2": loss_lsb2,
        "rmse_lsb": rmse,
        "enob_bits": enob,
        "telem": telem
    }

def write_ring_buffer_atomic(data: dict):
    try:
        with open(RING_BUFFER_TMP, "w") as f:
            json.dump(data, f)
        os.replace(RING_BUFFER_TMP, RING_BUFFER_JSON)
    except Exception:
        pass

def write_latest_status_atomic(data: dict):
    try:
        with open(LATEST_STATUS_TMP, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(LATEST_STATUS_TMP, LATEST_STATUS_JSON)
    except Exception:
        pass

def main():
    global client_global, running
    parser = argparse.ArgumentParser(description="Card 1 Thermal Stress 2-Beat Bit Slicing")
    parser.add_argument("--ip", type=str, default="192.168.1.50")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--duration-minutes", type=float, default=8.0, help="Experiment duration in minutes")
    parser.add_argument("--heater-start", type=str, default="off", choices=["off", "on"])
    parser.add_argument("--heater-off", type=float, default=4.0, help="Heater OFF period in minutes")
    parser.add_argument("--heater-on", type=float, default=4.0, help="Heater ON period in minutes")
    parser.add_argument("--heater-duty-pct", type=float, default=30.0, help="Heater PWM duty cycle pct (default 30%)")
    parser.add_argument("--heater-pwm-hz", type=float, default=1.0, help="Heater PWM frequency in Hz")
    parser.add_argument("--regler-on", type=float, default=2.0, help="Mode A ON duration in minutes")
    parser.add_argument("--regler-off", type=float, default=2.0, help="Mode A OFF duration in minutes")
    parser.add_argument("--delay-us", type=int, default=5000, help="Delay in us (default 5000 = 5.0 ms)")
    parser.add_argument("--k-batch", type=int, default=1, help="Mini-batch size K (default 1)")
    parser.add_argument("--lr", type=float, default=0.04, help="Learning rate (default 0.04)")
    parser.add_argument("--l2-reg", type=int, default=96, help="L2 regularization (default 96)")
    parser.add_argument("--out-json", type=str, default="FPGA_code/logs/bit_slicing/card1_thermal_slicing_30pct_8min.json")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.out_json), exist_ok=True)

    print("=" * 85)
    print("  INVERTED MAML: THERMAL CYCLING & 2-BEAT INTERLEAVED ANALOG BIT SLICING")
    print(f"  Hardware: Card 1 @ {args.ip}:{args.port} | Total Duration: {args.duration_minutes:.1f} min")
    print(f"  Thermal: {args.heater_duty_pct:.0f}% PWM @ {args.heater_pwm_hz:.1f} Hz ({args.heater_off:.1f}m OFF / {args.heater_on:.1f}m ON)")
    print(f"  Regler: {args.regler_on:.1f}m ON (SGD) <-> {args.regler_off:.1f}m OFF (W8=0) | Max M33 = ±60 LSB")
    print("=" * 85)

    ensure_version_guard(host=args.ip, port=args.port)
    client = MamlUdpClient(args.ip, args.port)
    client_global = client

    # Slices for M33 (Scaled to ±50 LSB for both MSB and LSB)
    k_default_m33 = np.array([
        [+76, -20, +28,  -4, +44, -36],
        [-20, +84, -12, +44,  -4, +36],
        [+36,  -4, +80, -16, +32,  -4],
        [ -4, +40,  -8, +72, -12, +44],
        [+44, -12, +28, -12, +76,  -8],
        [-28, +32,  -4, +40,  -8, +82]
    ])
    sc = 50.0 / 84.0
    M_msb = np.round(k_default_m33 * sc).astype(np.int32)
    M_lsb = np.round(k_default_m33 * sc).astype(np.int32)

    W_msb_silicon = M_msb.tolist()
    W_lsb_silicon = M_lsb.tolist()

    # Hardware Init
    client.clear_w33_hidden_offset()
    time.sleep(0.03)

    client.set_gain_experiment(d_line=2, w33=1, target_gain=1.0, clamp=120)
    time.sleep(0.03)

    lr_q16_active = int(round(args.lr * 1024.0))
    reg_q16_active = args.l2_reg

    client.set_config(
        mode=0, jumper_mode=3, led_switches=3, max_meas_win_pct=100, hadamard_khz=500,
        inner_loop_n=100, seed_pct=28, seed_mode=1, w_hid_mag=0, trim_hid_mag=0,
        hadamard_delay_us=args.delay_us, lr_inner_q16=lr_q16_active
    )
    time.sleep(0.03)
    client._send_binary(0x13, struct.pack("<BB", 1, 1))  # LEDs ON
    time.sleep(0.02)
    client.set_data_color(COLOR_WHITE, 0.0)
    time.sleep(0.03)

    cfg = get_staircase_config()
    init_w_m3 = [row[:] for row in cfg["w_m3_lsb"]]
    w_m8_zero = [[0]*6 for _ in range(7)]
    init_payload = build_center_weights_payload(1)
    payload_zero_w8 = build_custom_weights_payload(init_w_m3, w_m8_zero, 1)

    # Initial DC zero cal with active staircase W(3) and W(8)=0
    flat_init_m3 = [init_w_m3[r][c] for r in range(8) for c in range(6)]
    zero_cal_payload = struct.pack("<B48b42b", 0, *flat_init_m3, *([0] * 42))
    client._send_binary(MAML_CMD_CENTER_WEIGHTS, zero_cal_payload)
    time.sleep(0.05)
    client._send_binary(MAML_CMD_CENTER_WEIGHTS, init_payload)
    time.sleep(0.05)
    client.set_heaters(False, [0, 0, 0, 0])
    time.sleep(0.03)

    total_duration_s = args.duration_minutes * 60.0
    heater_off_s = args.heater_off * 60.0
    heater_on_s = args.heater_on * 60.0
    heater_period_s = heater_off_s + heater_on_s

    regler_on_s = args.regler_on * 60.0
    regler_off_s = args.regler_off * 60.0
    regler_period_s = regler_on_s + regler_off_s

    ring_history: deque[dict] = deque(maxlen=3600)
    t_start = time.time()
    last_physical_heater_state = None
    last_regler_state = None
    pair_idx = 0

    print("\n[+] STARTING 2-BEAT THERMAL EXPERIMENT:\n")

    while running:
        t_now = time.time()
        elapsed = t_now - t_start
        if elapsed >= total_duration_s:
            print(f"\n[✓] Target duration reached: {elapsed/60:.2f} / {args.duration_minutes:.2f} min.")
            break

        # Heater timing
        heater_time_in_period = elapsed % heater_period_s
        if args.heater_start == "off":
            heater_macro_on = heater_time_in_period >= heater_off_s
            heater_time_left = (heater_period_s - heater_time_in_period) if heater_macro_on else (heater_off_s - heater_time_in_period)
        else:
            heater_macro_on = heater_time_in_period < heater_on_s
            heater_time_left = (heater_on_s - heater_time_in_period) if heater_macro_on else (heater_period_s - heater_time_in_period)

        pwm_period_s = 1.0 / max(0.1, args.heater_pwm_hz)
        pwm_on_s = pwm_period_s * (args.heater_duty_pct / 100.0)
        time_in_pwm_cycle = elapsed % pwm_period_s
        physical_heater_on = heater_macro_on and (time_in_pwm_cycle < pwm_on_s)

        if physical_heater_on != last_physical_heater_state:
            pwr = 100 if physical_heater_on else 0
            client.set_heaters(physical_heater_on, [pwr, pwr, pwr, pwr])
            last_physical_heater_state = physical_heater_on

        # Regler timing
        regler_time_in_period = elapsed % regler_period_s
        reglering_on = (regler_time_in_period < regler_on_s)
        reglering_time_left = (regler_on_s - regler_time_in_period) if reglering_on else (regler_period_s - regler_time_in_period)

        if reglering_on != last_regler_state:
            last_regler_state = reglering_on
            if reglering_on:
                lr_q16 = lr_q16_active
                reg_q16 = reg_q16_active
                print(f"\n>>> [T={elapsed/60:.2f} min]: TRAINING ON (Active Online SGD, K={args.k_batch}, LR={args.lr}, λ={args.l2_reg}) <<<")
            else:
                lr_q16 = 0
                reg_q16 = 0
                print(f"\n>>> [T={elapsed/60:.2f} min]: TRAINING OFF (Ablation W8=0, LR=0) <<<")
                # Zero out W8 on silicon ONCE for ablation
                client._send_binary(MAML_CMD_CENTER_WEIGHTS, payload_zero_w8)
                time.sleep(0.02)

        # -------------------------------------------------------------
        # BEAT 2k: MSB SLICE
        # -------------------------------------------------------------
        client.set_w33_matrix(W_msb_silicon)
        res_msb = execute_hardware_beat(client, args.delay_us, lr_q16, reg_q16, k_batch=args.k_batch)
        telem_msb = res_msb["telem"]

        # -------------------------------------------------------------
        # BEAT 2k+1: LSB SLICE
        # -------------------------------------------------------------
        client.set_w33_matrix(W_lsb_silicon)
        res_lsb = execute_hardware_beat(client, args.delay_us, lr_q16, reg_q16, k_batch=args.k_batch)
        telem_lsb = res_lsb["telem"]

        # Recombination
        rmse_msb = res_msb["rmse_lsb"]
        rmse_lsb = res_lsb["rmse_lsb"]
        enob_msb = res_msb["enob_bits"]
        enob_lsb = res_lsb["enob_bits"]
        combined_rmse = math.sqrt((16.0 * rmse_msb)**2 + (rmse_lsb)**2)
        combined_enob_raw = max(0.0, 15.0 - math.log2(max(combined_rmse, 1.0)))

        w8_msb_min = min(min(r) for r in telem_msb.w_m8)
        w8_msb_max = max(max(r) for r in telem_msb.w_m8)
        w8_lsb_min = min(min(r) for r in telem_lsb.w_m8)
        w8_lsb_max = max(max(r) for r in telem_lsb.w_m8)

        pair_record = {
            "pair": pair_idx,
            "timestamp": time.time(),
            "elapsed_s": round(elapsed, 1),
            "heater_on": heater_macro_on,
            "heater_time_left_s": round(heater_time_left, 1),
            "reglering_on": reglering_on,
            "reglering_time_left_s": round(reglering_time_left, 1),
            "enob_msb": round(enob_msb, 2),
            "enob_lsb": round(enob_lsb, 2),
            "rmse_msb": round(rmse_msb, 2),
            "rmse_lsb": round(rmse_lsb, 2),
            "loss_msb": round(res_msb["loss_lsb2"], 1),
            "loss_lsb": round(res_lsb["loss_lsb2"], 1),
            "combined_enob_raw": round(combined_enob_raw, 2),
            "w8_msb_range": [w8_msb_min, w8_msb_max],
            "w8_lsb_range": [w8_lsb_min, w8_lsb_max],
        }

        ring_history.append(pair_record)

        # Atomic writes for GUI
        write_ring_buffer_atomic({"history": list(ring_history)})
        write_latest_status_atomic({
            "pair": pair_idx,
            "elapsed_s": round(elapsed, 1),
            "heater_on": heater_macro_on,
            "heater_duty_pct": args.heater_duty_pct,
            "heater_time_left_s": round(heater_time_left, 1),
            "reglering_on": reglering_on,
            "reglering_time_left_s": round(reglering_time_left, 1),
            "comb_enob": round(combined_enob_raw, 2),
            "msb_enob": round(enob_msb, 2),
            "lsb_enob": round(enob_lsb, 2),
            "w8_msb_range": [w8_msb_min, w8_msb_max],
            "w8_lsb_range": [w8_lsb_min, w8_lsb_max],
        })

        if pair_idx % 10 == 0:
            h_str = f"HEAT: ON ({args.heater_duty_pct:.0f}%)" if heater_macro_on else "HEAT: OFF ( 0%)"
            r_str = "REGL: ON (SGD )" if reglering_on else "REGL: OFF( W8=0)"
            print(f"Pair {pair_idx:4d} [{int(elapsed//60):02d}:{int(elapsed%60):02d}] | "
                  f"{h_str} [{int(heater_time_left//60):02d}:{int(heater_time_left%60):02d}] | "
                  f"{r_str} [{int(reglering_time_left//60):02d}:{int(reglering_time_left%60):02d}] | "
                  f"MSB: {enob_msb:.2f} b | LSB: {enob_lsb:.2f} b | Comb: {combined_enob_raw:.2f} b | "
                  f"W8_msb: [{w8_msb_min:+3d}, {w8_msb_max:+3d}]")

        pair_idx += 1

    # Save final complete dataset
    with open(args.out_json, "w") as f:
        json.dump({
            "metadata": {
                "title": "Inverted MAML Card 1 2-Beat Bit Slicing Thermal Stress Experiment",
                "duration_minutes": args.duration_minutes,
                "heater_duty_pct": args.heater_duty_pct,
                "w_msb": W_msb_silicon,
                "w_lsb": W_lsb_silicon
            },
            "history": list(ring_history)
        }, f, indent=2)

    print(f"\n[+] Saved complete dataset ({len(ring_history)} pairs) to: {args.out_json}")
    safe_shutdown()

if __name__ == "__main__":
    main()
