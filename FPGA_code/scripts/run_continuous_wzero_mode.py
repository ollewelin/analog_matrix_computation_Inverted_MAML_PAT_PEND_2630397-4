#!/home/olle/anaconda3/bin/python
"""
run_continuous_wzero_mode.py
Inverted MAML (Patent Pending SE 2630397-4) - Open Science Hardware

Continuous W=0 Zero-Baseline Mode for Oscilloscope Probing:
- Runs indefinitely with W(3) = 0 and W(8) = 0 (centered weights).
- White noise input vectors (COLOR_WHITE, d_line=2 => ±40 LSB swing).
- Evaluates 11 strata [4500 .. 5500 us] with lr_q16 = 0, reg_q16 = 0.
- Hardware continuously refreshes gate capacitors with true zero compensation weights.
- STRICT DATA POLICY: Zero file logging / zero disk writes to protect flash/storage during oscilloscope probing.
- Graceful shutdown on SIGINT/SIGTERM.
"""

from __future__ import annotations
import sys
import time
import math
import struct
import signal
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

running = True

def handle_signal(sig, frame):
    global running
    print("\n[!] Stop signal received. Exiting cleanly...")
    running = False

signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)


def drain_udp(client: MamlUdpClient):
    try:
        old_to = client.sock.gettimeout()
        client.sock.settimeout(0.002)
        while True:
            client.sock.recvfrom(2048)
    except Exception:
        pass
    finally:
        client.sock.settimeout(old_to)


def run_single_sample_stratum_step(
    client: MamlUdpClient,
    delay_us: int,
    lr_q16: int,
    reg_q16: int,
) -> dict:
    pkt = struct.pack(
        "<BBHHHH",
        1,         # k_batch = 1
        1,         # num_strata = 1
        delay_us,  # t_min_us
        delay_us,  # t_max_us
        lr_q16,
        reg_q16,
    )
    raw = None
    for attempt in range(15):
        drain_udp(client)
        raw = client._send_binary(MAML_CMD_BATCH_STEP, pkt)
        if raw is not None and len(raw) >= client.TELEM_SIZE:
            break
        time.sleep(0.04 * (attempt + 1))

    if raw is None or len(raw) < client.TELEM_SIZE:
        raise RuntimeError(f"Failed to receive MAML_CMD_BATCH_STEP telemetry for delay {delay_us} us.")

    u = struct.unpack(client.TELEM_FMT, raw[:client.TELEM_SIZE])
    loss_total_milli = float(u[29])
    t = client._parse_hw_telemetry(raw)

    step_loss = loss_total_milli / 2.0
    step_rmse = math.sqrt(loss_total_milli / 6.0)
    step_enob = max(0.0, 11.0 - math.log2(max(step_rmse, 1.0)))

    return {
        "delay_us": delay_us,
        "loss_lsb2": round(step_loss, 1),
        "rmse_lsb": round(step_rmse, 2),
        "enob_bits": round(step_enob, 2),
        "t_obj": t,
    }


def main():
    host = "192.168.1.50"
    port = 5000
    d_line = 2
    strata_delays = list(range(4500, 5501, 100))  # 11 strata [4500..5500 us]
    num_strata = len(strata_delays)

    print("=" * 100)
    print("INVERTED MAML: CONTINUOUS W=0 (ZERO-WEIGHT BASELINE) RUNNING FOREVER")
    print(f"Target: {host}:{port} | 11 Strata [{strata_delays[0]} .. {strata_delays[-1]} µs]")
    print("Compensation Weights: W(3) = 0, W(8) = 0 LSB (CENTER / ZERO BASELINE)")
    print("Input Data: White Noise (±40 LSB, d_line=2)")
    print("Disturbances: OFF (Nominal undisturbed M33)")
    print("Data Logging: DISABLED (0 bytes written to disk)")
    print("=" * 100)

    ensure_version_guard(host=host, port=port)
    client = MamlUdpClient(host=host, port=port, timeout=8.0)

    # 1. Konfigurera regim & M33
    client.set_w33_matrix(None)  # Reset factory default
    client.clear_w33_hidden_offset()
    time.sleep(0.03)

    client.set_gain_experiment(d_line=d_line, w33=1, target_gain=1.0, clamp=120)
    time.sleep(0.03)

    client.set_config(
        mode=0, jumper_mode=3, led_switches=3, max_meas_win_pct=100, hadamard_khz=500,
        inner_loop_n=100, seed_pct=28, seed_mode=1, w_hid_mag=0, trim_hid_mag=0,
        hadamard_delay_us=5000, lr_inner_q16=32
    )
    time.sleep(0.03)
    client._send_binary(0x13, struct.pack("<BB", 1, 1))  # LEDs ON
    time.sleep(0.02)
    client.set_data_color(COLOR_WHITE, 0.0)
    time.sleep(0.03)

    # 2. Sätt platt baslinje och W_null = 0 (all-zero payload)
    print("[*] Sätter platt baslinje: M3_null = 0, M8_null = 0, W = 0 LSB...")
    flat_payload = struct.pack("<B48b42b", 0, *([0] * 48), *([0] * 42))
    client._send_binary(MAML_CMD_CENTER_WEIGHTS, flat_payload)
    client.set_regularization(0)
    time.sleep(0.05)

    print("\n[+] Kontinuerligt W=0-läge är igång! Kör för alltid (lr=0, reg=0). Mät med oscilloskop när du vill.\n")
    sys.stdout.flush()

    epoch = 0
    t_start = time.time()

    while running:
        epoch += 1
        epoch_strata = []
        last_t = None

        for dly in strata_delays:
            if not running:
                break
            # lr=0, reg=0 => vikterna rörs inte, hålls strikt på W=0
            res = run_single_sample_stratum_step(client, dly, lr_q16=0, reg_q16=0)
            epoch_strata.append(res)
            last_t = res["t_obj"]

        if not running:
            break

        if epoch % 20 == 0 or epoch == 1:
            mean_loss = float(np.mean([s["loss_lsb2"] for s in epoch_strata]))
            c5 = [s for s in epoch_strata if s["delay_us"] == 5000][0]
            elapsed = time.time() - t_start
            w8_sample = list(last_t.w_m8[0][:6])
            print(f"  [W=0 Ep {epoch:5d} | {elapsed:5.1f}s] Win Mean: {mean_loss:7.1f} L² | 5.0ms: Loss={c5['loss_lsb2']:7.1f} L² ({c5['enob_bits']:4.2f} b) | W8[row0]={w8_sample}")
            sys.stdout.flush()

    print(f"\n[+] Stoppat. Körde {epoch} epoker i W=0 läge.")

if __name__ == "__main__":
    main()
