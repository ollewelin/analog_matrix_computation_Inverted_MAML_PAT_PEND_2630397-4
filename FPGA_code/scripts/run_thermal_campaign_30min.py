#!/usr/bin/env python3
"""
Continuous Thermal Drift & Warp Research Campaign (30 Minutes).
Evaluates Inverted MAML Mode A adaptation under slow thermal transients:
  - Phase 1 (0 to 15 min): Heaters ON (100% duty, heating transient & thermal warp)
  - Phase 2 (15 to 30 min): Heaters OFF (cooling transient & relaxation)

Hardware Target: Trion T120 (192.168.1.50:5000 UDP) + Trion T20 (T20A)
Saves results atomically to: data/benchmarks/thermal_drift_campaign_30min.json
"""

import socket
import struct
import time
import json
import os
import sys
from pathlib import Path
import numpy as np

BOARD_IP = "192.168.1.50"
BOARD_PORT = 5000
MAML_MAGIC = 0x4D414D4C

DATA_DIR = Path("data/benchmarks")
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUT_JSON = DATA_DIR / "thermal_drift_campaign_30min.json"

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(3.0)

def udp_xact(payload, retries=3):
    for attempt in range(retries):
        try:
            sock.sendto(payload, (BOARD_IP, BOARD_PORT))
            data, _ = sock.recvfrom(2048)
            return data
        except socket.timeout:
            time.sleep(0.05)
    raise TimeoutError("UDP Transaction timed out after retries")

def set_heaters(armed: bool, duty: int = 255):
    d = duty if armed else 0
    pkt = struct.pack("<IBBBBBB", MAML_MAGIC, 0x12, 1 if armed else 0, d, d, d, d)
    udp_xact(pkt)

def set_config_mode_a():
    # run_mode = 1 (Base Train), jumper_mode = 3 (Mode A: Dual Sigmoid)
    pkt = struct.pack("<IBBBHBHBbB", MAML_MAGIC, 0x11, 1, 3, 500, 25, 100, 10, 0, 14)
    udp_xact(pkt)

def step_adaptation():
    pkt = struct.pack("<IB", MAML_MAGIC, 0x18)
    data = udp_xact(pkt)
    return data

def parse_telemetry(t):
    magic, msg_type, run_mode, jumper_mode, heater_armed = struct.unpack_from("<IBBBB", t, 0)
    heater_wdog_ok, h0, h1, h2, h3 = struct.unpack_from("<BBBBB", t, 8)
    outer_ep, tot_ref = struct.unpack_from("<II", t, 30)
    loss_milli, comp_c, uncomp_c = struct.unpack_from("<IHH", t, 42)
    ztgt = struct.unpack_from("<6h", t, 62)
    adc49 = struct.unpack_from("<6h", t, 86)
    sigma2 = struct.unpack_from("<6h", t, 98)
    w0_x, w0_y, w0_loss = struct.unpack_from("<hhI", t, 238)
    hess = struct.unpack_from("<4h", t, 278)
    spread = struct.unpack_from("<H", t, 286)[0]

    return {
        "jumper_mode": jumper_mode,
        "heater_armed": heater_armed,
        "heater_duty": h0,
        "outer_ep": outer_ep,
        "tot_ref": tot_ref,
        "loss_milli": loss_milli,
        "comp_enob": comp_c / 100.0,
        "uncomp_enob": uncomp_c / 100.0,
        "hess": list(hess),
        "spread": spread,
        "sigma2": list(sigma2),
        "ztgt": list(ztgt),
        "adc49": list(adc49)
    }

def main():
    print("=== STARTING 30-MINUTE CONTINUOUS THERMAL DRIFT & WARP CAMPAIGN ===")
    total_duration_sec = 30 * 60  # 1800 seconds
    switch_phase_sec = 15 * 60    # 900 seconds
    step_interval_sec = 3.0       # Step every 3.0 seconds (~600 steps total)

    start_time = time.time()
    end_time = start_time + total_duration_sec

    # Configure Mode A
    set_config_mode_a()
    # Phase 1 starts: Heaters ON
    set_heaters(armed=True, duty=255)
    current_phase = "HEATING_ON"
    print(f"[{time.strftime('%H:%M:%S')}] Phase 1 initiated: HEATERS ON (100% duty) for 15 minutes...")

    records = []
    step_count = 0
    best_comp_enob = 0.0
    min_loss = 9999999

    while time.time() < end_time:
        now = time.time()
        elapsed = now - start_time
        remaining = end_time - now

        # Phase transition check at 15 minutes
        if elapsed >= switch_phase_sec and current_phase == "HEATING_ON":
            current_phase = "COOLING_OFF"
            set_heaters(armed=False, duty=0)
            print(f"\n[{time.strftime('%H:%M:%S')}] >>> PHASE SWITCH: HEATERS TURNED OFF! Entering 15-minute cooling/relaxation phase... <<<\n")

        # Execute one adaptation step
        try:
            raw_t = step_adaptation()
            p = parse_telemetry(raw_t)
            step_count += 1

            if p["comp_enob"] > best_comp_enob:
                best_comp_enob = p["comp_enob"]
            if p["loss_milli"] < min_loss:
                min_loss = p["loss_milli"]

            record_entry = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "elapsed_sec": round(elapsed, 1),
                "phase": current_phase,
                "step": step_count,
                "heater_armed": p["heater_armed"],
                "heater_duty": p["heater_duty"],
                "uncomp_enob": p["uncomp_enob"],
                "comp_enob": p["comp_enob"],
                "loss_milli": p["loss_milli"],
                "hess": p["hess"],
                "spread": p["spread"]
            }

            records.append(record_entry)
            # Keep rolling buffer under 200 items for compact disk usage
            if len(records) > 200:
                records.pop(0)

            # Atomic save every step
            payload_data = {
                "campaign_start": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time)),
                "campaign_type": "30-Minute Thermal Transient (15m ON -> 15m OFF)",
                "jumper_mode": "Mode A (Dual Sigmoid)",
                "current_phase": current_phase,
                "total_steps": step_count,
                "elapsed_min": round(elapsed / 60.0, 2),
                "remaining_min": round(remaining / 60.0, 2),
                "best_comp_enob": round(best_comp_enob, 2),
                "lowest_loss": min_loss,
                "rolling_records": records
            }

            tmp_path = OUT_JSON.with_suffix(".tmp")
            with open(tmp_path, "w") as f:
                json.dump(payload_data, f, indent=2)
            os.replace(tmp_path, OUT_JSON)

            # Periodic terminal progress every 10 steps (~30s)
            if step_count % 10 == 0 or step_count == 1:
                print(f"[{time.strftime('%H:%M:%S')}] Step {step_count:3d} ({current_phase}) | "
                      f"Elapsed: {elapsed/60:.1f}m | ENOB: {p['uncomp_enob']:.2f}b -> {p['comp_enob']:.2f}b "
                      f"(Best: {best_comp_enob:.2f}b) | Loss: {p['loss_milli']:6d} | Rem: {remaining/60:.1f}m")

        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] Communication warning: {e}, retrying in 2s...")
            time.sleep(2.0)

        # Pace loop
        time.sleep(step_interval_sec)

    # Clean shutdown at end of 30 minutes
    set_heaters(armed=False, duty=0)
    print(f"\n[{time.strftime('%H:%M:%S')}] === 30-MINUTE CAMPAIGN COMPLETE === Heaters safely shut off.")

if __name__ == "__main__":
    main()

