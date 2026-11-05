#!/home/olle/anaconda3/bin/python
"""
run_train_100ep_then_freeze_continuous.py
Inverted MAML (Patent Pending SE 2630397-4) - Open Science Hardware

Protocol:
1. Trains online single-sample SGD on Card 1 for exactly 100 epochs:
   - 11 strata [4500 .. 5500 us] per epoch
   - LR = 0.02x (lr_q16 = 20), L2 Reg lambda = 2048, Data Div = 2 (Swing: ±40 LSB), White noise
   - Nominal undisturbed M33
2. At Epoch 100:
   - Freezes the learned compensation weights W(3) and W(8) permanently by setting LR = 0 and Reg = 0.
3. Enters an indefinite continuous loop with the frozen weights:
   - Continues refreshing 2T1C capacitors with the exact frozen weights.
   - Evaluates all 11 strata continuously for oscilloscope probing.
   - NO data logging to disk (0 bytes written).
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
    lr = 0.02
    reg_lambda = 2048
    d_line = 2
    strata_delays = list(range(4500, 5501, 100))  # 11 strata
    num_strata = len(strata_delays)

    print("=" * 100)
    print("INVERTED MAML: TRAIN 100 EPOCHS THEN FREEZE WEIGHTS FOR CONTINUOUS OSCILLOSCOPE PROBING")
    print(f"Target: {host}:{port} | 11 Strata [{strata_delays[0]} .. {strata_delays[-1]} µs]")
    print(f"Phase A: 100 Epochs Online SGD (LR={lr}x, λ={reg_lambda})")
    print(f"Phase B: Freeze learned W(3)/W(8) (LR=0, λ=0) and run indefinitely")
    print("=" * 100)

    ensure_version_guard(host=host, port=port)
    client = MamlUdpClient(host=host, port=port, timeout=8.0)

    # 1. Konfigurera nominell regim
    client.set_w33_matrix(None)  # Reset factory default
    client.clear_w33_hidden_offset()
    time.sleep(0.03)

    client.set_gain_experiment(d_line=d_line, w33=1, target_gain=1.0, clamp=120)
    time.sleep(0.03)

    lr_inner_q16 = max(1, min(4096, int(round(1024 * lr))))
    client.set_config(
        mode=0, jumper_mode=3, led_switches=3, max_meas_win_pct=100, hadamard_khz=500,
        inner_loop_n=100, seed_pct=28, seed_mode=1, w_hid_mag=0, trim_hid_mag=0,
        hadamard_delay_us=5000, lr_inner_q16=max(32, lr_inner_q16)
    )
    time.sleep(0.03)
    client._send_binary(0x13, struct.pack("<BB", 1, 1))  # LEDs ON
    time.sleep(0.02)
    client.set_data_color(COLOR_WHITE, 0.0)
    time.sleep(0.03)

    # 2. Sätt platt baslinje och nollställda vikter inför träningsstart
    print("[*] Sätter platt baslinje: W(3)=0, W(8)=0 LSB...")
    flat_payload = struct.pack("<B48b42b", 0, *([0] * 48), *([0] * 42))
    client._send_binary(MAML_CMD_CENTER_WEIGHTS, flat_payload)
    client.set_regularization(0)
    time.sleep(0.05)

    print("\n[+] STARTAR 100 EPOKERS TRÄNING (online SGD mot nominell M33)...")
    t_start = time.time()
    last_t = None

    for ep in range(1, 101):
        if not running:
            break
        epoch_strata = []
        for dly in strata_delays:
            if not running:
                break
            res = run_single_sample_stratum_step(client, dly, lr_q16=lr_inner_q16, reg_q16=reg_lambda)
            epoch_strata.append(res)
            last_t = res["t_obj"]

        if ep % 10 == 0 or ep == 1 or ep == 100:
            mean_loss = float(np.mean([s["loss_lsb2"] for s in epoch_strata]))
            c5 = [s for s in epoch_strata if s["delay_us"] == 5000][0]
            elapsed = time.time() - t_start
            w8_sample = list(last_t.w_m8[0][:6])
            print(f"  [Ep {ep:3d}/100 | {elapsed:4.1f}s] Win Mean: {mean_loss:7.1f} L² | 5.0ms: Loss={c5['loss_lsb2']:7.1f} L² ({c5['enob_bits']:4.2f} b) | W8[row0]={w8_sample}")

    if not running:
        print("[!] Avbruten före frysning.")
        return

    # Frys vikterna
    t_final = client.get_telemetry()
    frozen_w8_row0 = list(t_final.w_m8[0])
    print("\n" + "=" * 100)
    print(">>> [VIKTERNA ÄR NU FASTFRUSNA!] <<<")
    print(f"    Träning avslutad vid Epok 100 ({time.time() - t_start:.1f}s).")
    print(f"    LR sätts till 0, Reg sätts till 0.")
    print(f"    Fastfrusna W8 (rad 0): {frozen_w8_row0}")
    print("    Går in i KONTINUERLIGT OÄNDLIGHETSLÄGE med dessa vikter (kondensatorer refreshas kontinuerligt)!")
    print("    KLART FÖR OSCILLOSKOPMÄTNING!")
    print("=" * 100 + "\n")
    sys.stdout.flush()

    freeze_epoch = 0
    t_freeze_start = time.time()

    while running:
        freeze_epoch += 1
        epoch_strata = []
        for dly in strata_delays:
            if not running:
                break
            # LR=0, REG=0 => vikterna ändras inte alls!
            res = run_single_sample_stratum_step(client, dly, lr_q16=0, reg_q16=0)
            epoch_strata.append(res)
            last_t = res["t_obj"]

        if not running:
            break

        if freeze_epoch % 20 == 0 or freeze_epoch == 1:
            mean_loss = float(np.mean([s["loss_lsb2"] for s in epoch_strata]))
            c5 = [s for s in epoch_strata if s["delay_us"] == 5000][0]
            elapsed = time.time() - t_freeze_start
            print(f"  [FROZEN Ep {freeze_epoch:5d} | {elapsed:5.1f}s] Win Mean: {mean_loss:7.1f} L² | 5.0ms: Loss={c5['loss_lsb2']:7.1f} L² ({c5['enob_bits']:4.2f} b) | W8[row0]={list(last_t.w_m8[0][:6])}")
            sys.stdout.flush()

    print(f"\n[+] Stoppat. Körde {freeze_epoch} frysta epoker.")

if __name__ == "__main__":
    main()

