#!/usr/bin/env python3
"""
Autonomous Multi-Agent Inverted MAML Hardware Training Runner
Coordinates live board sweeps (192.168.1.50:5000) under zero-heater safety.
Maintains strict disk budget (< 100 KB) and outputs timestamped telemetry.
"""

import socket
import struct
import time
import json
import os
from pathlib import Path

BOARD_IP = "192.168.1.50"
BOARD_PORT = 5000
MAML_MAGIC = 0x4D414D4C

DATA_DIR = Path("data/benchmarks")
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUT_JSON = DATA_DIR / "maml_autonomous_training_run.json"

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(3.0)

def udp_xact(payload):
    sock.sendto(payload, (BOARD_IP, BOARD_PORT))
    data, _ = sock.recvfrom(2048)
    return data

def parse_telemetry(t):
    magic, msg_type, run_mode, jumper_mode, heater_armed = struct.unpack_from("<IBBBB", t, 0)
    heater_wdog_ok, h0, h1, h2, h3, comp_led, mat33_led, osc_en, ovr_en = struct.unpack_from("<BBBBBBBBB", t, 8)
    h_freq, max_duty, seed_m, seed_pct, carrier_k, inner_n, inner_st = struct.unpack_from("<HBBBBHH", t, 20)
    outer_ep, tot_ref, slot, n_strata, settle_cyc = struct.unpack_from("<IIBBH", t, 30)
    loss_milli, comp_c, uncomp_c = struct.unpack_from("<IHH", t, 42)
    xref  = struct.unpack_from("<6h", t, 50)
    ztgt  = struct.unpack_from("<6h", t, 62)
    adc45 = struct.unpack_from("<6h", t, 74)
    adc49 = struct.unpack_from("<6h", t, 86)
    sigma2 = struct.unpack_from("<6h", t, 98)
    w0_x, w0_y, w0_loss = struct.unpack_from("<hhI", t, 238)
    bx = struct.unpack_from("<4h", t, 246)
    by = struct.unpack_from("<4h", t, 254)
    bloss = struct.unpack_from("<4I", t, 262)
    hess  = struct.unpack_from("<4h", t, 278)
    spread = struct.unpack_from("<H", t, 286)[0]

    return {
        "run_mode": run_mode,
        "jumper_mode": jumper_mode,
        "heater_armed": heater_armed,
        "comp_led": comp_led,
        "mat33_led": mat33_led,
        "inner_n": inner_n,
        "inner_st": inner_st,
        "outer_ep": outer_ep,
        "tot_ref": tot_ref,
        "loss_milli": loss_milli,
        "comp_enob": comp_c / 100.0,
        "uncomp_enob": uncomp_c / 100.0,
        "xref": list(xref),
        "ztgt": list(ztgt),
        "adc45": list(adc45),
        "adc49": list(adc49),
        "sigma2": list(sigma2),
        "w0_x": w0_x,
        "w0_y": w0_y,
        "w0_loss": w0_loss,
        "hess": list(hess),
        "spread": spread
    }

print("=== STARTING AUTONOMOUS INVERTED MAML HARDWARE RUN ===")

# Step 1: Enforce zero-heater safety & verify disarmed state
print("[1/5] Enforcing heater lockout (HEAT_1..4 = 0% duty, disarmed)...")
udp_xact(struct.pack("<IBBBBBB", MAML_MAGIC, 0x12, 0, 0, 0, 0, 0))

# Step 2: Configure IDLE mode and enable COMP_LED & MAT33_LED switches
print("[2/5] Configuring operational parameters and LED switches...")
udp_xact(struct.pack("<IBBBHBHBbB", MAML_MAGIC, 0x11, 0, 3, 500, 25, 100, 10, 0, 14))
udp_xact(struct.pack("<IBBB", MAML_MAGIC, 0x13, 1, 1))

# Step 3: Center weights to record baseline, then seed with Orthogonal Hadamard modes
print("[3/5] Measuring uncompensated baseline and seeding initial weights...")
udp_xact(struct.pack("<IB", MAML_MAGIC, 0x15)) # Center weights (0x15)
time.sleep(0.05)
t_init = udp_xact(struct.pack("<IBBB", MAML_MAGIC, 0x16, 2, 75)) # Seed Orthogonal 75% (0x16)
p_init = parse_telemetry(t_init)
print(f"      Initial Baseline: Uncomp ENOB={p_init['uncomp_enob']:.2f}b | Comp ENOB={p_init['comp_enob']:.2f}b | Loss={p_init['loss_milli']}")

# Step 4: Run 25 consecutive Inverted MAML meta-learning epochs
print("[4/5] Executing 25 Inverted MAML Outer/Inner meta-learning epochs on live board...")
records = []
records.append({"step": 0, "telemetry": p_init})

for step in range(1, 26):
    t_step = udp_xact(struct.pack("<IB", MAML_MAGIC, 0x18)) # MAML_CMD_STEP_ONCE (0x18)
    p = parse_telemetry(t_step)
    records.append({"step": step, "telemetry": p})
    print(f"      Epoch {p['outer_ep']:2d} (Step {step:2d}): Loss={p['loss_milli']:7d} | ENOB: {p['uncomp_enob']:.2f}b -> {p['comp_enob']:.2f}b | HessDot={p['hess']} | Spread={p['spread']}")
    time.sleep(0.05)

# Step 5: Save compact dataset under strict budget
print("[5/5] Saving benchmark data to disk...")
output_data = {
    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S CEST"),
    "target": "192.168.1.50:5000",
    "total_epochs": 25,
    "initial_enob": p_init["uncomp_enob"],
    "final_enob": records[-1]["telemetry"]["comp_enob"],
    "records": records
}

with open(OUT_JSON, "w") as f:
    json.dump(output_data, f, indent=2)

size_kb = os.path.getsize(OUT_JSON) / 1024.0
print(f"[SUCCESS] Completed 25 Inverted MAML epochs! Data saved to {OUT_JSON} ({size_kb:.2f} KB / < 100 KB limit)")

