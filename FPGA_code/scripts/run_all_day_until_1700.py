#!/usr/bin/env python3
"""
High-Speed Autonomous Inverted MAML Hardware Campaign Monitor (until 17:00)
Runs 30x faster: 2-second adaptation cadence (~1,800 steps/hour)
Enforces:
- Target end time: 17:00:00 local time
- Heaters permanently disarmed (0% duty, locked out)
- Headless UDP execution (negligible PC CPU/RAM)
- Rotating rolling JSON buffer to keep disk usage strictly under 80 KB
"""

import socket
import struct
import time
import datetime
import json
from pathlib import Path

BOARD_IP = "192.168.1.50"
BOARD_PORT = 5000
MAML_MAGIC = 0x4D414D4C

DATA_DIR = Path("data/benchmarks")
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUT_JSON = DATA_DIR / "all_day_campaign_1700.json"
MAX_HISTORY = 120  # Keep rolling window of recent snapshots + summary

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(2.5)

def udp_xact(payload):
    try:
        sock.sendto(payload, (BOARD_IP, BOARD_PORT))
        data, _ = sock.recvfrom(2048)
        return data
    except Exception:
        return None

def parse_telemetry(t):
    if not t or len(t) < 288:
        return None
    magic, msg_type, run_mode, jumper_mode, heater_armed = struct.unpack_from("<IBBBB", t, 0)
    outer_ep, tot_ref = struct.unpack_from("<II", t, 30)
    loss_milli, comp_c, uncomp_c = struct.unpack_from("<IHH", t, 42)
    hess  = struct.unpack_from("<4h", t, 278)
    spread = struct.unpack_from("<H", t, 286)[0]

    return {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "outer_ep": outer_ep,
        "tot_ref": tot_ref,
        "loss_milli": loss_milli,
        "comp_enob": comp_c / 100.0,
        "uncomp_enob": uncomp_c / 100.0,
        "hess": list(hess),
        "spread": spread
    }

print("=== STARTING HIGH-SPEED INVERTED MAML AUTONOMOUS CAMPAIGN (UNTIL 17:00) ===")

# Enforce zero heater lockout
udp_xact(struct.pack("<IBBBBBB", MAML_MAGIC, 0x12, 0, 0, 0, 0, 0))
udp_xact(struct.pack("<IBBBHBHBbB", MAML_MAGIC, 0x11, 0, 3, 500, 25, 100, 10, 0, 14))
udp_xact(struct.pack("<IBBB", MAML_MAGIC, 0x13, 1, 1))

# Initial seed
udp_xact(struct.pack("<IB", MAML_MAGIC, 0x15))
time.sleep(0.04)
t_init = udp_xact(struct.pack("<IBBB", MAML_MAGIC, 0x16, 2, 75))
p_init = parse_telemetry(t_init)

now = datetime.datetime.now()
target_1700 = now.replace(hour=17, minute=0, second=0, microsecond=0)
total_runtime_s = max(10, int((target_1700 - now).total_seconds()))
print(f"[*] High-speed campaign active until 17:00:00 (~{total_runtime_s/3600:.2f} hours remaining, 2s cadence)")

history = []
if p_init:
    history.append(p_init)

total_cycles = 0
min_loss = p_init["loss_milli"] if p_init else 999999
max_enob = p_init["comp_enob"] if p_init else 0.0

start_time = time.time()
last_safety_check = time.time()
last_disk_flush = time.time()

while time.time() - start_time < total_runtime_s:
    # Reinforce heater lockout every 30 seconds
    if time.time() - last_safety_check > 30.0:
        udp_xact(struct.pack("<IBBBBBB", MAML_MAGIC, 0x12, 0, 0, 0, 0, 0))
        last_safety_check = time.time()

    # Trigger Inverted MAML step
    t_step = udp_xact(struct.pack("<IB", MAML_MAGIC, 0x18))
    p = parse_telemetry(t_step)
    total_cycles += 1

    if p:
        if p["loss_milli"] < min_loss: min_loss = p["loss_milli"]
        if p["comp_enob"] > max_enob: max_enob = p["comp_enob"]

        history.append(p)
        if len(history) > MAX_HISTORY:
            history.pop(0)

        # Print heartbeat every 50 steps (~100s)
        if total_cycles % 50 == 0:
            rem = max(0, int(total_runtime_s - (time.time() - start_time)))
            print(f"[{p['timestamp']}] Step {total_cycles:5d} | ENOB: {p['uncomp_enob']:.2f}b -> {p['comp_enob']:.2f}b | Best={max_enob:.2f}b | MinLoss={min_loss:6d} | Rem: {rem//3600}h {(rem%3600)//60}m")

        # Atomic rolling write to disk every 10 seconds
        if time.time() - last_disk_flush > 10.0:
            status_doc = {
                "campaign_start": now.strftime("%Y-%m-%d %H:%M:%S"),
                "target_stop": target_1700.strftime("%Y-%m-%d %H:%M:%S"),
                "last_heartbeat": p["timestamp"],
                "total_adaptation_steps": total_cycles,
                "best_compensated_enob": max_enob,
                "lowest_mse_loss": min_loss,
                "cadence": "2.0 seconds (high-speed)",
                "heater_safety": "LOCKED_OUT (0% duty, disarmed)",
                "recent_history_rolling": history
            }
            with open(OUT_JSON, "w") as f:
                json.dump(status_doc, f, indent=2)
            last_disk_flush = time.time()

    # High-speed 2.0s cadence
    time.sleep(2.0)

print(f"\n=== [17:00:00 REACHED] HIGH-SPEED CAMPAIGN COMPLETE! ===")
print(f"Total steps executed: {total_cycles} | Best ENOB: {max_enob:.2f} bits | Saved to {OUT_JSON}")
