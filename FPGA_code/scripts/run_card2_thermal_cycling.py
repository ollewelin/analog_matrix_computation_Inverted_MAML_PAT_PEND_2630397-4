#!/home/olle/anaconda3/bin/python
"""
run_card2_thermal_cycling.py
Inverted MAML (Patent Pending SE 2630397-4) - Open Science Hardware

Long-Term Continuous Thermal Cycling & Mode A Closed-Loop Regulation on Card 2:
- Temporal window: [4.9 ms .. 5.9 ms] (11 strata: 4900, 5000, ..., 5900 us, center 5.4 ms)
- Input Vector: White Noise (COLOR_WHITE)
- Perturbation: 100% Real Physical Thermal Drift (w33_variance = 0, no synthetic offsets!)
- Baseline & Reference:
    * Initial DC zero calibration (g_baseline_mode=0)
    * W(3) Staircase reference & bias pattern ([-40..+40] LSB on rows 6 & 7)
- Alternating Continuous Loops:
    * Thermal Cycling: 10 min HEATER ON (100% duty) <-> 10 min HEATER OFF (0% duty)
    * Mode A Regulation: 2 min REGLERING ON (SGD active, LR=0.02, λ=2048) <-> 2 min REGLERING OFF (Ablation W8=0, LR=0)
- Ring Buffer Data Logger:
    * Rolling 30-minute buffer (last ~3,600 epochs, ~2.0 MB)
    * Atomically written to FPGA_code/logs/thermal_cycling/thermal_ring_buffer_30min.json
    * Strictly preserves disk quota (<100 MB hard ceiling)
- Safe Shutdown:
    * SIGINT / SIGTERM turns off heaters and resets weights cleanly.
"""

from __future__ import annotations
import sys
import os
import time
import json
import math
import struct
import signal
from collections import deque
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

LOG_DIR = REPO_ROOT / "FPGA_code" / "logs" / "thermal_cycling"
LOG_DIR.mkdir(parents=True, exist_ok=True)
RING_BUFFER_JSON = LOG_DIR / "thermal_ring_buffer_30min.json"
RING_BUFFER_TMP = LOG_DIR / "thermal_ring_buffer_30min.json.tmp"
LATEST_STATUS_JSON = LOG_DIR / "thermal_latest_status.json"

# Timing configuration (seconds)
HEATER_PERIOD_S = 1200.0   # 20 minutes total (10 min ON, 10 min OFF)
HEATER_ON_DUTY_S = 600.0   # 10 minutes ON
REGLER_PERIOD_S = 240.0    # 4 minutes total (2 min ON, 2 min OFF)
REGLER_ON_DUTY_S = 120.0   # 2 minutes ON

MAX_RING_BUFFER_EPOCHS = 3600  # ~30 minutes at ~2 ep/s

running = True
client_global: MamlUdpClient | None = None
baseline_payload_global: bytes = b""


def safe_shutdown(sig, frame):
    global running, client_global, baseline_payload_global
    print("\n[!] Mottog avbrottssignal (Ctrl+C / SIGTERM). Stänger av säkert...")
    running = False
    if client_global is not None:
        try:
            print("[*] Stänger av alla 4 värmeelement (Heaters 0%)...")
            client_global.set_heaters(False, [0, 0, 0, 0])
            time.sleep(0.05)
            if baseline_payload_global:
                print("[*] Nollställer kompensationsvikter W8=0...")
                client_global._send_binary(MAML_CMD_CENTER_WEIGHTS, baseline_payload_global)
            client_global.close()
        except Exception as e:
            print(f"[!] Fel vid säker nedstängning: {e}")
    print("[+] Säker nedstängning klar. Avslutar.")
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


def run_single_sample_stratum_step(
    client: MamlUdpClient,
    delay_us: int,
    lr_q16: int,
    reg_q16: int,
    k_batch: int = 1,
) -> dict:
    pkt = struct.pack(
        "<BBHHHH",
        k_batch,   # k_batch
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
        raise RuntimeError(f"Kunde inte ta emot telemetri från hårdvaran för delay {delay_us} us.")

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


def write_ring_buffer_atomic(buffer_data: dict):
    """Atomically writes buffer_data to RING_BUFFER_JSON via a tmp file."""
    try:
        with open(RING_BUFFER_TMP, "w", encoding="utf-8") as f:
            json.dump(buffer_data, f)
        os.replace(RING_BUFFER_TMP, RING_BUFFER_JSON)
    except Exception as e:
        print(f"[!] Varning: Kunde inte skriva ringbuffertfil: {e}", file=sys.stderr)


def write_latest_status_atomic(status_data: dict):
    """Atomically writes status_data to LATEST_STATUS_JSON."""
    tmp_path = LATEST_STATUS_JSON.with_suffix(".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(status_data, f, indent=2)
        os.replace(tmp_path, LATEST_STATUS_JSON)
    except Exception:
        pass


def main():
    global client_global, baseline_payload_global, running

    host = "192.168.1.50"
    port = 5000
    t_min = 4900
    t_max = 5900
    t_step = 100
    lr_nominal = 0.02
    reg_lambda_nominal = 2048
    d_line = 2   # +/-40 LSB swing
    k_batch = 1  # Pure single-sample online SGD

    strata_delays = list(range(t_min, t_max + 1, t_step))
    num_strata = len(strata_delays)
    target_center_us = 5400
    center_idx = strata_delays.index(target_center_us) if target_center_us in strata_delays else len(strata_delays) // 2

    print("=" * 105)
    print("INVERTED MAML: LÅNGTIDSKÖRNING MED TERMISK CYKLING & MODE A REGLERING")
    print(f"Hårdvara: Card 2 (T120 SoC @ {host}:{port}) | Bygelläge: Mode A")
    print(f"Tidsfönster: [{t_min/1000:.2f} .. {t_max/1000:.2f} ms] (11 strata, centrum 5.4 ms)")
    print(f"Indata: Vitt Brus (COLOR_WHITE) | Swing: ±40 LSB (d_line=2)")
    print(f"Störning: 100% Fysisk termisk drift (Inga syntetiska hidden offsets)")
    print(f"Termisk cykel: 10 min HEATER PÅ (100%) <-> 10 min HEATER AV (0%) [Period: 20 min]")
    print(f"Regleringscykel: 2 min REGLERING PÅ (SGD LR={lr_nominal:.2f}, λ={reg_lambda_nominal}) <-> 2 min REGLERING AV (W8=0)")
    print(f"Ringbuffert: Rullande 30 minuter (~3600 epoker) i {RING_BUFFER_JSON}")
    print("=" * 105)

    # 1. Säkerställ version och initiera klient
    ensure_version_guard(host=host, port=port)
    client = MamlUdpClient(host=host, port=port, timeout=8.0)
    client_global = client

    # 2. Återställ M33 och konfigurera regim
    client.set_w33_matrix(None)  # Reset factory default
    client.clear_w33_hidden_offset()
    time.sleep(0.03)

    client.set_gain_experiment(d_line=d_line, w33=1, target_gain=1.0, clamp=120)
    time.sleep(0.03)

    lr_inner_q16 = max(1, min(4096, int(round(1024 * lr_nominal))))
    client.set_config(
        mode=0, jumper_mode=3, led_switches=3, max_meas_win_pct=100, hadamard_khz=500,
        inner_loop_n=100, seed_pct=28, seed_mode=1, w_hid_mag=0, trim_hid_mag=0,
        hadamard_delay_us=5400, lr_inner_q16=max(32, lr_inner_q16)
    )
    time.sleep(0.03)
    client._send_binary(0x13, struct.pack("<BB", 1, 1))  # LEDs ON
    time.sleep(0.02)
    client.set_data_color(COLOR_WHITE, 0.0)
    time.sleep(0.03)

    # 3. DC Baslinjekalibrering med w=0
    print("[*] Utför hårdvaru DC-nollkalibrering (g_baseline_mode=0, W_3=0, W_8=0)...")
    zero_cal_payload = struct.pack("<B48b42b", 0, *([0] * 48), *([0] * 42))
    client._send_binary(MAML_CMD_CENTER_WEIGHTS, zero_cal_payload)
    time.sleep(0.08)

    # 4. Sätt W(3) Trappmönster på referens- och biasrader
    baseline_payload = build_center_weights_payload(1)
    baseline_payload_global = baseline_payload
    print("[*] Sätter W(3) trappmönster ([-40..+40] LSB) på referens- och biasrader (rad 6 & 7)...")
    client._send_binary(MAML_CMD_CENTER_WEIGHTS, baseline_payload)
    time.sleep(0.05)
    client.set_regularization(0)
    time.sleep(0.05)

    # Säkerställ initiala värmeelement AV
    client.set_heaters(False, [0, 0, 0, 0])
    time.sleep(0.03)

    ring_history: deque[dict] = deque(maxlen=MAX_RING_BUFFER_EPOCHS)
    t_start = time.time()
    last_heater_state = None
    last_regler_state = None
    epoch = 0

    print("\n[+] STARTAR KONTINUERLIG KÖRNING:")
    print("    Tryck Ctrl+C när som helst för säker avstängning.\n")

    while running:
        t_now = time.time()
        elapsed = t_now - t_start

        # Beräkna faser
        heater_time_in_period = elapsed % HEATER_PERIOD_S
        heater_on = heater_time_in_period < HEATER_ON_DUTY_S
        if heater_on:
            heater_time_left = HEATER_ON_DUTY_S - heater_time_in_period
        else:
            heater_time_left = HEATER_PERIOD_S - heater_time_in_period

        regler_time_in_period = elapsed % REGLER_PERIOD_S
        regler_on = regler_time_in_period < REGLER_ON_DUTY_S
        if regler_on:
            regler_time_left = REGLER_ON_DUTY_S - regler_time_in_period
        else:
            regler_time_left = REGLER_PERIOD_S - regler_time_in_period

        # Hantera värmeväxling
        if heater_on != last_heater_state:
            last_heater_state = heater_on
            if heater_on:
                print(f"\n>>> [T={elapsed/60:.1f} min]: HEATER PÅ! (Alla 4 värmeelement på 100%) <<<")
                client.set_heaters(True, [100, 100, 100, 100])
            else:
                print(f"\n>>> [T={elapsed/60:.1f} min]: HEATER AV! (Alla 4 värmeelement av 0%) <<<")
                client.set_heaters(False, [0, 0, 0, 0])
            time.sleep(0.02)

        # Hantera regleringsväxling
        if regler_on != last_regler_state:
            last_regler_state = regler_on
            if regler_on:
                cur_lr_q16 = lr_inner_q16
                cur_reg = reg_lambda_nominal
                print(f">>> [T={elapsed/60:.1f} min]: REGLERING PÅ! (Aktiv FHP SGD Online, LR={lr_nominal}, λ={reg_lambda_nominal}) <<<")
            else:
                cur_lr_q16 = 0
                cur_reg = 0
                print(f">>> [T={elapsed/60:.1f} min]: REGLERING AV! (Ablation W8=0, LR=0, mäter ren termisk drift) <<<")
                client._send_binary(MAML_CMD_CENTER_WEIGHTS, baseline_payload)
                client.set_regularization(0)
            time.sleep(0.02)

        if regler_on:
            cur_lr_q16 = lr_inner_q16
            cur_reg = reg_lambda_nominal
        else:
            cur_lr_q16 = 0
            cur_reg = 0

        # Utvärdera alla 11 strata sekventiellt
        ep_strata = []
        last_t = None
        for dly in strata_delays:
            res = run_single_sample_stratum_step(client, dly, lr_q16=cur_lr_q16, reg_q16=cur_reg, k_batch=k_batch)
            ep_strata.append(res)
            last_t = res["t_obj"]

        ep_mean_loss = float(np.mean([s["loss_lsb2"] for s in ep_strata]))
        ep_mean_rmse = float(np.sqrt(np.mean([s["loss_lsb2"] * 2.0 / 6.0 for s in ep_strata])))
        ep_mean_enob = max(0.0, 11.0 - math.log2(max(ep_mean_rmse, 1.0)))
        s_center = ep_strata[center_idx]

        w_m8_snap = [row[:] for row in last_t.w_m8] if last_t else [[0]*6 for _ in range(7)]
        w_m3_snap = [row[:] for row in last_t.w_m3] if last_t else [[0]*6 for _ in range(8)]

        w8_flat = [val for row in w_m8_snap for val in row]
        w8_min = min(w8_flat) if w8_flat else 0
        w8_max = max(w8_flat) if w8_flat else 0

        rec = {
            "epoch": epoch,
            "timestamp": round(t_now, 2),
            "elapsed_s": round(elapsed, 1),
            "heater_on": heater_on,
            "heater_time_left_s": round(heater_time_left, 1),
            "reglering_on": regler_on,
            "reglering_time_left_s": round(regler_time_left, 1),
            "lr_q16": cur_lr_q16,
            "reg_lambda": cur_reg,
            "mean_loss_lsb2": round(ep_mean_loss, 1),
            "mean_enob_bits": round(ep_mean_enob, 2),
            "center_loss_lsb2": round(s_center["loss_lsb2"], 1),
            "center_enob_bits": round(s_center["enob_bits"], 2),
            "strata_losses": [s["loss_lsb2"] for s in ep_strata],
            "strata_enobs": [s["enob_bits"] for s in ep_strata],
            "w_m3": w_m3_snap,
            "w_m8": w_m8_snap,
        }
        ring_history.append(rec)

        # Skriv ringbuffert och status regelbundet
        buffer_export = {
            "version": "1.0",
            "updated_at": round(time.time(), 2),
            "elapsed_s": round(elapsed, 1),
            "epoch": epoch,
            "heater_on": heater_on,
            "heater_time_left_s": round(heater_time_left, 1),
            "reglering_on": regler_on,
            "reglering_time_left_s": round(regler_time_left, 1),
            "t_min_us": t_min,
            "t_max_us": t_max,
            "t_step_us": t_step,
            "strata_delays": strata_delays,
            "center_delay_us": target_center_us,
            "lr": lr_nominal,
            "reg_lambda": reg_lambda_nominal,
            "total_records": len(ring_history),
            "max_records": MAX_RING_BUFFER_EPOCHS,
            "epochs": list(ring_history),
        }
        write_ring_buffer_atomic(buffer_export)

        status_export = {
            "epoch": epoch,
            "elapsed_s": round(elapsed, 1),
            "heater_on": heater_on,
            "heater_time_left_s": round(heater_time_left, 1),
            "reglering_on": regler_on,
            "reglering_time_left_s": round(regler_time_left, 1),
            "mean_loss_lsb2": round(ep_mean_loss, 1),
            "mean_enob_bits": round(ep_mean_enob, 2),
            "center_loss_lsb2": round(s_center["loss_lsb2"], 1),
            "center_enob_bits": round(s_center["enob_bits"], 2),
            "w8_min": w8_min,
            "w8_max": w8_max,
            "records_in_buffer": len(ring_history),
        }
        write_latest_status_atomic(status_export)

        # Terminalutskrift
        h_str = f"PÅ (100%) [{int(heater_time_left//60):02d}:{int(heater_time_left%60):02d}]" if heater_on else f"AV (  0%) [{int(heater_time_left//60):02d}:{int(heater_time_left%60):02d}]"
        r_str = f"PÅ (SGD ) [{int(regler_time_left//60):02d}:{int(regler_time_left%60):02d}]" if regler_on else f"AV ( W8=0) [{int(regler_time_left//60):02d}:{int(regler_time_left%60):02d}]"
        print(
            f"Ep {epoch:5d} [{int(elapsed//3600):02d}:{int((elapsed%3600)//60):02d}:{int(elapsed%60):02d}] | "
            f"HEAT: {h_str} | REGL: {r_str} | "
            f"Mean: {ep_mean_loss:7.0f} L² ({ep_mean_enob:4.2f} b) | "
            f"5.4ms: {s_center['loss_lsb2']:7.0f} L² ({s_center['enob_bits']:4.2f} b) | "
            f"W8: [{w8_min:+3d}, {w8_max:+3d}] LSB"
        )
        sys.stdout.flush()

        epoch += 1


if __name__ == "__main__":
    main()
