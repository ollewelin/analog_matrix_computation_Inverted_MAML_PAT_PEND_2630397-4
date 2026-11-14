#!/home/olle/anaconda3/bin/python
"""
run_card1_thermal_bit_slicing.py
================================
Inverted MAML (Patent Pending SE 2630397-4) - Open Science Hardware

Full Thermal Stress & Closed-Loop 2-Beat Interleaved Bit-Slicing on Card 1:
- Thermal Stress: 30% PWM Heater Duty @ 1.0 Hz
- Phase Schedule (8 phases x 2 min = 16.0 min):
  1. Cold / Regler ON   (Heater OFF, SGD ON,  LR=0.04, K=2, λ=96)
  2. Cold / Regler OFF  (Heater OFF, SGD OFF, Ablation W8=0)
  3. Warm / Regler ON   (Heater 30%, SGD ON,  LR=0.04, K=2, λ=96)
  4. Warm / Regler OFF  (Heater 30%, SGD OFF, Ablation W8=0)
  5. Warm / Regler ON   (Heater 30%, SGD ON,  LR=0.04, K=2, λ=96)
  6. Warm / Regler OFF  (Heater 30%, SGD OFF, Ablation W8=0)
  7. Cool / Regler ON   (Heater OFF, SGD ON,  LR=0.04, K=2, λ=96)
  8. Cool / Regler OFF  (Heater OFF, SGD OFF, Ablation W8=0)
- Fixed Startup DC Calibration:
  * Fitted once on cold silicon (t=0, heaters OFF) per slice (MSB and LSB)
  * Locks per-column alpha (gain) and beta (offset): Z_target = alpha * (X @ W) + beta
  * 100% frozen during entire run (strictly NO moving digital DSP during inference)
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

def calibrate_fixed_slice_params(
    client: MamlUdpClient,
    W_silicon: list[list[int]],
    num_samples: int = 40,
    delay_us: int = 5000
) -> tuple[np.ndarray, np.ndarray]:
    """
    Fits static column gain alpha and quiescent offset beta on cold silicon (heaters OFF, W8=0).
    Model: Y_col = alpha_col * (X @ W)_col + beta_col
    Locked permanently for the duration of the experiment.
    """
    client.set_w33_matrix(W_silicon)
    drain_udp(client)
    time.sleep(0.05)
    W_mat = np.array(W_silicon, dtype=np.float64)
    xs, ys = [], []

    for _ in range(num_samples):
        pkt = struct.pack("<BBHHHH", 0, 1, delay_us, delay_us, 0, 0)
        raw = client._send_binary(MAML_CMD_BATCH_STEP, pkt)
        if raw is None or len(raw) < client.TELEM_SIZE:
            drain_udp(client)
            raw = client._send_binary(MAML_CMD_BATCH_STEP, pkt)
        if raw is not None and len(raw) >= client.TELEM_SIZE:
            telem = client._parse_hw_telemetry(raw)
            x_vec = np.array(telem.x_ref, dtype=np.float64)
            y_vec = np.array(telem.adc49_sig, dtype=np.float64)
            xs.append(x_vec @ W_mat)
            ys.append(y_vec)
        time.sleep(0.015)

    X_ideal = np.array(xs)
    Y_meas = np.array(ys)
    alphas = np.zeros(6, dtype=np.float64)
    betas = np.zeros(6, dtype=np.float64)

    for c in range(6):
        p = np.polyfit(X_ideal[:, c], Y_meas[:, c], deg=1)
        alphas[c] = float(p[0])
        betas[c] = float(p[1])

    return alphas, betas

def execute_hardware_beat(
    client: MamlUdpClient,
    delay_us: int,
    lr_q16: int,
    reg_q16: int,
    k_batch: int = 1,
    W_mat: np.ndarray | None = None,
    alpha: np.ndarray | None = None,
    beta: np.ndarray | None = None
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
    x = np.array(telem.x_ref, dtype=np.float64)
    y = np.array(telem.adc49_sig, dtype=np.float64)
    if alpha is not None and beta is not None and W_mat is not None:
        target = (x @ W_mat) * alpha + beta
        err = y - target
    else:
        err = y - np.array(telem.z_target, dtype=np.float64)

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
    parser.add_argument("--phase-duration", type=float, default=2.0, help="Duration of warm/cool phases in minutes (default 2.0 min)")
    parser.add_argument("--cold-phase-duration", type=float, default=0.5, help="Duration of first 2 cold phases in minutes (default 0.5 min = 30s)")
    parser.add_argument("--heater-duty-pct", type=float, default=30.0, help="Heater PWM duty cycle pct (default 30%%)")
    parser.add_argument("--heater-pwm-hz", type=float, default=1.0, help="Heater PWM frequency in Hz")
    parser.add_argument("--delay-us", type=int, default=5000, help="Delay in us (default 5000 = 5.0 ms)")
    parser.add_argument("--k-batch", type=int, default=2, help="Mini-batch size K (default 2)")
    parser.add_argument("--lr", type=float, default=0.04, help="Learning rate (default 0.04)")
    parser.add_argument("--l2-reg", type=int, default=96, help="L2 regularization (default 96)")
    parser.add_argument("--momentum", type=float, default=0.98, help="SGD momentum [0.0..0.999] (default 0.98)")
    parser.add_argument("--clamp", type=int, default=75, help="Dynamic M3/M8 weight clamp limit in LSB (default 75)")
    parser.add_argument("--warm-phases", type=int, default=6, help="Number of warm (Heater ON) phases (default 6)")
    parser.add_argument("--cool-phases", type=int, default=2, help="Number of trailing cool phases (default 2, use 0 to skip)")
    parser.add_argument("--cooldown-sec", type=float, default=60.0, help="Pre-run forced cooldown duration with Heaters OFF before cold DC calibration (default 60s)")
    parser.add_argument("--load-dc-calib", type=str, default="FPGA_code/config/r1_dc_cal_fixed.json", help="Path to locked R1 cold DC calibration JSON (pass '' to fit new calibration at t=0)")
    parser.add_argument("--out-json", type=str, default="FPGA_code/logs/bit_slicing/card1_thermal_slicing_30pct_k2_lr0p04_16min.json")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.out_json), exist_ok=True)

    # Master Schedule: 2 Cold (short, default 30s each) + N Warm (default 6) + 2 Cool
    cold_dur_s = args.cold_phase_duration * 60.0
    phase_dur_s = args.phase_duration * 60.0
    phases = [
        {"name": "Phase 1: Cold / Regler ON",  "heater": False, "regler": True,  "dur_s": cold_dur_s},
        {"name": "Phase 2: Cold / Regler OFF", "heater": False, "regler": False, "dur_s": cold_dur_s},
    ]
    for wi in range(args.warm_phases):
        pnum = 3 + wi
        reg_on = (wi % 2 == 0)
        phases.append({
            "name": f"Phase {pnum}: Warm / Regler {'ON' if reg_on else 'OFF'}",
            "heater": True,
            "regler": reg_on,
            "dur_s": phase_dur_s,
        })
    for ci in range(args.cool_phases):
        pnum = 3 + args.warm_phases + ci
        reg_on = (ci % 2 == 0)
        phases.append({
            "name": f"Phase {pnum}: Cool / Regler {'ON' if reg_on else 'OFF'}",
            "heater": False,
            "regler": reg_on,
            "dur_s": phase_dur_s,
        })
    phase_starts = []
    acc_s = 0.0
    for p in phases:
        phase_starts.append(acc_s)
        acc_s += p["dur_s"]
    total_duration_s = acc_s

    print("=" * 85)
    print("  INVERTED MAML: THERMAL CYCLING & 2-BEAT INTERLEAVED ANALOG BIT SLICING")
    print(f"  Hardware: Card 1 @ {args.ip}:{args.port} | Total Duration: {total_duration_s/60:.1f} min (2x{args.cold_phase_duration:.1f}m + {len(phases)-2}x{args.phase_duration:.1f}m)")
    print(f"  Thermal Stress: {args.heater_duty_pct:.0f}% PWM @ {args.heater_pwm_hz:.1f} Hz")
    print(f"  SGD Reglering : LR = {args.lr:.4f}, Mom = {args.momentum:.2f}, K-batch = {args.k_batch}, λ = {args.l2_reg}, clamp = ±{args.clamp} LSB | Attenuator 1k/2.2k")
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
    M_lsb = np.round(M_msb * 0.75).astype(np.int32)

    W_msb_silicon = M_msb.tolist()
    W_lsb_silicon = M_lsb.tolist()

    # Hardware Init
    client.clear_w33_hidden_offset()
    time.sleep(0.03)

    client.set_gain_experiment(d_line=2, w33=1, target_gain=1.0, clamp=args.clamp)
    time.sleep(0.03)

    lr_q16_active = int(round(args.lr * 1024.0))
    reg_q16_active = args.l2_reg

    client.set_config(
        mode=0, jumper_mode=3, led_switches=3, max_meas_win_pct=100, hadamard_khz=500,
        inner_loop_n=100, seed_pct=28, seed_mode=1, w_hid_mag=0, trim_hid_mag=0,
        hadamard_delay_us=args.delay_us, lr_inner_q16=lr_q16_active
    )
    time.sleep(0.03)
    mom_q16 = max(0, min(65535, int(round(args.momentum * 65536.0))))
    client._send_binary(0x1E, struct.pack("<BH", 7, mom_q16))
    time.sleep(0.02)
    client._send_binary(0x13, struct.pack("<BB", 1, 1))  # LEDs ON
    time.sleep(0.02)
    client.set_data_color(COLOR_WHITE, 0.0)
    time.sleep(0.03)

    cfg = get_staircase_config()
    init_w_m3 = [row[:] for row in cfg["w_m3_lsb"]]
    w_m8_zero = [[0]*6 for _ in range(7)]
    init_payload = build_center_weights_payload(1)
    payload_zero_w8 = build_custom_weights_payload(init_w_m3, w_m8_zero, 1)

    # Ensure heaters are strictly OFF and wait --cooldown-sec so cold DC cal runs on cool silicon
    client.set_heaters(False, [0, 0, 0, 0])
    client._send_binary(MAML_CMD_CENTER_WEIGHTS, payload_zero_w8)
    if args.cooldown_sec > 0:
        print(f"\n[*] Cooling board for {args.cooldown_sec:.0f}s with Heaters OFF (0%) before Cold DC calibration...")
        cool_start = time.time()
        next_log = 15.0
        while running:
            dt_cool = time.time() - cool_start
            if dt_cool >= args.cooldown_sec:
                break
            if dt_cool >= next_log:
                print(f"    ... cooldown {dt_cool:.0f}s / {args.cooldown_sec:.0f}s (Heaters OFF)")
                next_log += 15.0
            client.set_heaters(False, [0, 0, 0, 0])
            time.sleep(min(2.0, max(0.05, args.cooldown_sec - dt_cool)))
        print("[+] Cooldown complete.")

    # Initial DC zero cal with active staircase W(3) and W(8)=0
    flat_init_m3 = [init_w_m3[r][c] for r in range(8) for c in range(6)]
    zero_cal_payload = struct.pack("<B48b42b", 0, *flat_init_m3, *([0] * 42))
    client._send_binary(MAML_CMD_CENTER_WEIGHTS, zero_cal_payload)
    time.sleep(0.05)
    client._send_binary(MAML_CMD_CENTER_WEIGHTS, init_payload)
    time.sleep(0.05)
    client.set_heaters(False, [0, 0, 0, 0])
    time.sleep(0.03)

    # -----------------------------------------------------------------
    # FIXED COLD DC CALIBRATION (Locked R1 Reference or t=0 Fit)
    # -----------------------------------------------------------------
    use_locked_cal = bool(args.load_dc_calib and os.path.exists(args.load_dc_calib))
    if use_locked_cal:
        with open(args.load_dc_calib, "r") as f_cal:
            cal_obj = json.load(f_cal)
        alpha_msb = np.array(cal_obj["calib_msb"]["alpha"], dtype=np.float64)
        beta_msb = np.array(cal_obj["calib_msb"]["beta"], dtype=np.float64)
        alpha_lsb = np.array(cal_obj["calib_lsb"]["alpha"], dtype=np.float64)
        beta_lsb = np.array(cal_obj["calib_lsb"]["beta"], dtype=np.float64)
        print(f"\n[*] Loaded PERMANENT LOCKED R1 Cold DC Calibration from: {args.load_dc_calib}")
    else:
        print("\n[*] Executing Fixed Cold DC Calibration (40 samples per slice, Heaters OFF)...")
        alpha_msb, beta_msb = calibrate_fixed_slice_params(client, W_msb_silicon, num_samples=40, delay_us=args.delay_us)
        alpha_lsb, beta_lsb = calibrate_fixed_slice_params(client, W_lsb_silicon, num_samples=40, delay_us=args.delay_us)

    # Lock cold alpha/beta inside T120 SoC z_target so SGD only tracks thermal drift (not 0.03 vs 1.0 gain)
    for sid, (alp, bet) in [(0, (alpha_msb, beta_msb)), (1, (alpha_lsb, beta_lsb))]:
        a_q16 = [int(round(float(a) * 65536.0)) for a in alp]
        b_i16 = [max(-32768, min(32767, int(round(float(b))))) for b in bet]
        client._send_binary(0x1E, struct.pack("<BB6i6h", 5, sid, *a_q16, *b_i16))

    print("  [+] MSB Slice Static Calib:")
    print(f"      alpha: {[round(x, 4) for x in alpha_msb]}")
    print(f"      beta : {[round(x, 1) for x in beta_msb]}")
    print("  [+] LSB Slice Static Calib:")
    print(f"      alpha: {[round(x, 4) for x in alpha_lsb]}")
    print(f"      beta : {[round(x, 1) for x in beta_lsb]}")
    print("  [+] Locked fixed parameters permanently for the entire test!\n")

    ring_history: deque[dict] = deque(maxlen=7200)
    t_start = time.time()
    last_physical_heater_state = None
    last_regler_state = None
    last_phase_idx = -1
    pair_idx = 0

    print("[+] STARTING 16-MINUTE PHASE-LOCKED EXPERIMENT:\n")

    while running:
        t_now = time.time()
        elapsed = t_now - t_start
        if elapsed >= total_duration_s:
            print(f"\n[✓] Target duration reached: {elapsed/60:.2f} / {total_duration_s/60:.2f} min.")
            break

        # Determine current phase
        phase_idx = 0
        for pi, ps in enumerate(phase_starts):
            if elapsed >= ps:
                phase_idx = pi
        cur_phase = phases[phase_idx]
        time_in_phase = elapsed - phase_starts[phase_idx]
        time_left_phase = cur_phase["dur_s"] - time_in_phase

        phase_changed = False
        if phase_idx != last_phase_idx:
            last_phase_idx = phase_idx
            phase_changed = True
            print(f"\n>>> [T={elapsed/60:.2f} min]: ENTERING {cur_phase['name']} (Duration {cur_phase['dur_s']/60:.1f} min) <<<")

        heater_macro_on = cur_phase["heater"]
        reglering_on = cur_phase["regler"]

        # Hardware-locked T20 PWM Heater control (crystal-locked 0.2 Hz on T20, zero Python/UDP jitter)
        if heater_macro_on != last_physical_heater_state:
            pwr = int(round(args.heater_duty_pct)) if heater_macro_on else 0
            client.set_heaters(heater_macro_on, [pwr, pwr, pwr, pwr])
            last_physical_heater_state = heater_macro_on

        # Reglering toggle
        if reglering_on != last_regler_state:
            last_regler_state = reglering_on
            if reglering_on:
                lr_q16 = lr_q16_active
                reg_q16 = reg_q16_active
                print(f"    --> REGULATION ACTIVE (Online SGD: LR={args.lr:.4f}, Mom={args.momentum:.2f}, K={args.k_batch}, λ={args.l2_reg})")
            else:
                lr_q16 = 0
                reg_q16 = 0
                print(f"    --> REGULATION OFF (Ablation W8=0, Free Drift)")
                drain_udp(client)
                client._send_binary(MAML_CMD_CENTER_WEIGHTS, payload_zero_w8)
                time.sleep(0.02)

        # -------------------------------------------------------------
        # BEAT 2k: MSB SLICE (Hardware Slice Bank 0)
        # -------------------------------------------------------------
        drain_udp(client)
        if client._send_binary(0x1E, struct.pack("<BB", 4, 0)) is None:
            drain_udp(client)
            client._send_binary(0x1E, struct.pack("<BB", 4, 0))
        if not client.set_w33_matrix(W_msb_silicon):
            drain_udp(client)
            client.set_w33_matrix(W_msb_silicon)
        res_msb = execute_hardware_beat(
            client, args.delay_us, lr_q16, reg_q16,
            k_batch=args.k_batch, W_mat=M_msb, alpha=alpha_msb, beta=beta_msb
        )
        telem_msb = res_msb["telem"]

        # -------------------------------------------------------------
        # BEAT 2k+1: LSB SLICE (Hardware Slice Bank 1)
        # -------------------------------------------------------------
        drain_udp(client)
        if client._send_binary(0x1E, struct.pack("<BB", 4, 1)) is None:
            drain_udp(client)
            client._send_binary(0x1E, struct.pack("<BB", 4, 1))
        if not client.set_w33_matrix(W_lsb_silicon):
            drain_udp(client)
            client.set_w33_matrix(W_lsb_silicon)
        res_lsb = execute_hardware_beat(
            client, args.delay_us, lr_q16, reg_q16,
            k_batch=args.k_batch, W_mat=M_lsb, alpha=alpha_lsb, beta=beta_lsb
        )
        telem_lsb = res_lsb["telem"]

        # Recombination
        rmse_msb = res_msb["rmse_lsb"]
        rmse_lsb = res_lsb["rmse_lsb"]
        enob_msb = res_msb["enob_bits"]
        enob_lsb = res_lsb["enob_bits"]

        # Sann Kontinuerlig Deterministisk 8-Bit Recombination ENOB:
        # När MSB >= 4.0 bitar är alla 4 bitar deterministiska (4.0 + LSB).
        # När MSB närmar sig 4.0 bitar skalas LSB-bidraget mjukt och kontinuerligt utan tröskelklipp.
        combined_enob = min(9.5, max(0.0, min(4.0, enob_msb) + enob_lsb * min(1.0, max(0.0, enob_msb / 4.0))))

        w8_msb_min = min(min(r) for r in telem_msb.w_m8)
        w8_msb_max = max(max(r) for r in telem_msb.w_m8)
        w8_lsb_min = min(min(r) for r in telem_lsb.w_m8)
        w8_lsb_max = max(max(r) for r in telem_lsb.w_m8)
        w3_msb_min = min(min(r) for r in telem_msb.w_m3[:6])
        w3_msb_max = max(max(r) for r in telem_msb.w_m3[:6])
        w3_lsb_min = min(min(r) for r in telem_lsb.w_m3[:6])
        w3_lsb_max = max(max(r) for r in telem_lsb.w_m3[:6])

        # Safety guard: in Regler OFF, re-center immediately if W8 drifted from [0, 0]
        if (not reglering_on) and (w8_msb_min != 0 or w8_msb_max != 0 or w8_lsb_min != 0 or w8_lsb_max != 0):
            drain_udp(client)
            client._send_binary(MAML_CMD_CENTER_WEIGHTS, payload_zero_w8)

        pair_record = {
            "pair": pair_idx,
            "timestamp": time.time(),
            "elapsed_s": round(elapsed, 1),
            "phase_name": cur_phase["name"],
            "phase_idx": phase_idx,
            "heater_on": heater_macro_on,
            "heater_time_left_s": round(time_left_phase, 1),
            "reglering_on": reglering_on,
            "reglering_time_left_s": round(time_left_phase, 1),
            "enob_msb": round(enob_msb, 2),
            "enob_lsb": round(enob_lsb, 2),
            "rmse_msb": round(rmse_msb, 2),
            "rmse_lsb": round(rmse_lsb, 2),
            "loss_msb": round(res_msb["loss_lsb2"], 1),
            "loss_lsb": round(res_lsb["loss_lsb2"], 1),
            "combined_enob_raw": round(combined_enob, 2),
            "w8_msb_range": [w8_msb_min, w8_msb_max],
            "w8_lsb_range": [w8_lsb_min, w8_lsb_max],
            "w3_msb_range": [w3_msb_min, w3_msb_max],
            "w3_lsb_range": [w3_lsb_min, w3_lsb_max],
            "w8_msb": [[int(v) for v in row] for row in telem_msb.w_m8],
            "w8_lsb": [[int(v) for v in row] for row in telem_lsb.w_m8],
            "w3_msb": [[int(v) for v in row] for row in telem_msb.w_m3],
            "w3_lsb": [[int(v) for v in row] for row in telem_lsb.w_m3],
            "clip_msb": int(telem_msb.clip_events_cnt),
            "clip_lsb": int(telem_lsb.clip_events_cnt),
        }

        ring_history.append(pair_record)

        # Throttled atomic writes for GUI (~2 Hz and on phase transitions) to prevent CPU/disk stall
        # Strip full 2D matrices from live GUI ring buffer so disk atomic writes stay <1 ms.
        if phase_changed or (pair_idx % 5 == 0):
            lite_hist = [
                {k: v for k, v in r.items() if k not in ("w8_msb", "w8_lsb", "w3_msb", "w3_lsb")}
                for r in ring_history
            ]
            write_ring_buffer_atomic({"history": lite_hist})
            write_latest_status_atomic({
                "pair": pair_idx,
                "elapsed_s": round(elapsed, 1),
                "phase_name": cur_phase["name"],
                "heater_on": heater_macro_on,
                "heater_duty_pct": args.heater_duty_pct,
                "heater_time_left_s": round(time_left_phase, 1),
                "reglering_on": reglering_on,
                "reglering_time_left_s": round(time_left_phase, 1),
                "comb_enob": round(combined_enob, 2),
                "msb_enob": round(enob_msb, 2),
                "lsb_enob": round(enob_lsb, 2),
                "clamp_lsb": args.clamp,
                "w8_msb_range": [w8_msb_min, w8_msb_max],
                "w8_lsb_range": [w8_lsb_min, w8_lsb_max],
            })

        if pair_idx % 10 == 0:
            h_str = f"HEAT: ON ({args.heater_duty_pct:.0f}%)" if heater_macro_on else "HEAT: OFF ( 0%)"
            r_str = "REGL: ON (SGD )" if reglering_on else "REGL: OFF( W8=0)"
            print(f"Pair {pair_idx:4d} [{int(elapsed//60):02d}:{int(elapsed%60):02d}] | "
                  f"{cur_phase['name'][:14]} | {h_str} | {r_str} | "
                  f"MSB: {enob_msb:.2f} b | LSB: {enob_lsb:.2f} b | Comb: {combined_enob:.2f} b | "
                  f"W8_msb: [{w8_msb_min:+3d}, {w8_msb_max:+3d}]")

        pair_idx += 1

    # Save final complete dataset
    with open(args.out_json, "w") as f:
        json.dump({
            "metadata": {
                "title": "Inverted MAML Card 1 2-Beat Bit Slicing Thermal Stress Experiment (Fixed Cold DC Calibrated)",
                "duration_minutes": total_duration_s / 60.0,
                "heater_duty_pct": args.heater_duty_pct,
                "phases": phases,
                "k_batch": args.k_batch,
                "lr": args.lr,
                "l2_reg": args.l2_reg,
                "momentum": args.momentum,
                "clamp_lsb": args.clamp,
                "delay_us": args.delay_us,
                "dc_calib_mode": f"LOCKED_R1_FIXED ({args.load_dc_calib})" if use_locked_cal else "PER_RUN_T0_FIT",
                "w_msb": W_msb_silicon,
                "w_lsb": W_lsb_silicon,
                "calib_msb": {
                    "alpha": alpha_msb.tolist(),
                    "beta": beta_msb.tolist()
                },
                "calib_lsb": {
                    "alpha": alpha_lsb.tolist(),
                    "beta": beta_lsb.tolist()
                }
            },
            "history": list(ring_history)
        }, f, indent=2)

    print(f"\n[+] Saved complete dataset ({len(ring_history)} pairs) to: {args.out_json}")
    safe_shutdown()

if __name__ == "__main__":
    main()
