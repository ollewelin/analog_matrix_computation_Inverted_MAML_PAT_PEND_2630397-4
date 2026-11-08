#!/home/olle/anaconda3/bin/python
"""
run_card2_thermal_cycling.py
Inverted MAML (Patent Pending SE 2630397-4) - Open Science Hardware

Long-Term Continuous Thermal Cycling & Mode A Closed-Loop Regulation on Card 2:
- Experiment Duration: 20 minutes (1200 seconds)
- Temporal window: [4.9 ms .. 5.9 ms] (11 strata: 4900, 5000, ..., 5900 us, center 5.4 ms)
- Input Vector: White Noise (COLOR_WHITE)
- Perturbation: 100% Real Physical Thermal Drift (4 on-board 100% duty cycle heaters)
- Baseline & Reference:
    * Initial DC zero calibration (g_baseline_mode=0)
    * W(3) Staircase reference & bias pattern ([-40..+40] LSB on rows 6 & 7)
- Alternating Continuous Loops:
    * Thermal Cycling: 8 min HEATER ON (100% duty) <-> 8 min HEATER OFF (0% duty) [Period: 16 min]
    * Mode A Regulation: 2 min TRAINING ON (SGD active, LR=0.02, λ=768, K=2) <-> 2 min TRAINING OFF (Ablation W8=0, LR=0)
- Ring Buffer & File Outputs:
    * Atomic writes to FPGA_code/logs/thermal_cycling/thermal_ring_buffer_30min.json
    * Final export to FPGA_code/logs/thermal_cycling/card2_thermal_cycling_heaters_8m8m_regler_2m2m_l2_768_k2_lr0p02_20min.json
    * Strictly preserves disk quota (<100 MB ceiling)
- Safe Shutdown:
    * Turning off heaters and resetting weights cleanly on completion or SIGINT.
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
DEFAULT_FINAL_JSON = LOG_DIR / "card2_thermal_cycling_heaters_8m8m_regler_2m2m_l2_768_k2_lr0p02_5p0_to_5p4ms_20min.json"

running = True
client_global: MamlUdpClient | None = None
baseline_payload_global: bytes = b""


def safe_shutdown(sig=None, frame=None):
    global running, client_global, baseline_payload_global
    print("\n[!] Shutting down experiment cleanly...")
    running = False
    if client_global is not None:
        try:
            print("[*] Turning OFF all 4 on-board heaters (0% power)...")
            client_global.set_heaters(False, [0, 0, 0, 0])
            time.sleep(0.05)
            if baseline_payload_global:
                print("[*] Resetting compensation weights W8=0...")
                client_global._send_binary(MAML_CMD_CENTER_WEIGHTS, baseline_payload_global)
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


def run_single_sample_stratum_step(
    client: MamlUdpClient,
    delay_us: int,
    lr_q16: int,
    reg_q16: int,
    k_batch: int = 2,
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
        if attempt > 0:
            drain_udp(client)
        raw = client._send_binary(MAML_CMD_BATCH_STEP, pkt)
        if raw is not None and len(raw) >= client.TELEM_SIZE:
            break
        time.sleep(0.02 * min(attempt + 1, 5))

    if raw is None or len(raw) < client.TELEM_SIZE:
        raise RuntimeError(f"Could not receive telemetry from hardware for delay {delay_us} us.")

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
        print(f"[!] Warning: Could not write ring buffer file: {e}", file=sys.stderr)


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

    parser = argparse.ArgumentParser(description="Inverted MAML Card 2 Long-Term Thermal Stress Experiment")
    parser.add_argument("--duration-minutes", type=float, default=20.0, help="Total experiment duration in minutes (default: 20.0)")
    parser.add_argument("--heater-on", type=float, default=8.0, help="Heater ON duration in minutes (default: 8.0)")
    parser.add_argument("--heater-off", type=float, default=8.0, help="Heater OFF duration in minutes (default: 8.0)")
    parser.add_argument("--regler-on", type=float, default=2.0, help="Training ON duration in minutes (default: 2.0)")
    parser.add_argument("--regler-off", type=float, default=2.0, help="Training OFF duration in minutes (default: 2.0)")
    parser.add_argument("--l2-reg", type=int, default=768, help="L2 regularization lambda (default: 768)")
    parser.add_argument("--k-batch", type=int, default=2, help="K batch size per stratum (default: 2)")
    parser.add_argument("--lr", type=float, default=0.02, help="Learning rate (default: 0.02)")
    parser.add_argument("--out-json", type=str, default=str(DEFAULT_FINAL_JSON), help="Output final JSON path")
    args = parser.parse_args()

    host = "192.168.1.50"
    port = 5000
    t_min = 5000
    t_max = 5400
    t_step = 100
    lr_nominal = args.lr
    reg_lambda_nominal = args.l2_reg
    d_line = 2   # +/-40 LSB swing
    k_batch = args.k_batch

    total_duration_s = args.duration_minutes * 60.0
    heater_on_s = args.heater_on * 60.0
    heater_off_s = args.heater_off * 60.0
    heater_period_s = heater_on_s + heater_off_s

    regler_on_s = args.regler_on * 60.0
    regler_off_s = args.regler_off * 60.0
    regler_period_s = regler_on_s + regler_off_s

    strata_delays = list(range(t_min, t_max + 1, t_step))
    num_strata = len(strata_delays)
    target_center_us = 5200
    center_idx = strata_delays.index(target_center_us) if target_center_us in strata_delays else len(strata_delays) // 2

    # Scaled parameters:
    # 1. stratum_reg: Distribute L2 regularization across the 5 strata so total epoch decay = lambda (768)
    stratum_reg_nominal = max(1, int(round(reg_lambda_nominal / num_strata)))
    # 2. lr_inner_q16: Standard nominal learning rate (lr_nominal = 0.02 -> Q16 = 20)
    lr_inner_q16 = max(1, min(4096, int(round(1024 * lr_nominal))))

    print("=" * 105)
    print("INVERTED MAML: 20-MINUTE LONG-TERM THERMAL CYCLING & MODE A REGULATION EXPERIMENT")
    print(f"Hardware: Card 2 (PCBA v1.3.2, T120 SoC @ {host}:{port}) | Mode: Mode A")
    print(f"Total Duration: {args.duration_minutes:.1f} minutes ({total_duration_s:.0f} seconds)")
    print(f"Temporal Window: [{t_min/1000:.2f} .. {t_max/1000:.2f} ms] ({num_strata} strata @ 100us step, center {target_center_us/1000:.1f} ms)")
    print(f"Input Vector: White Noise (COLOR_WHITE) | Swing: ±40 LSB (d_line=2)")
    print(f"Hyperparameters: L2 reg = {reg_lambda_nominal} (stratum reg = {stratum_reg_nominal}), K = {k_batch}, lr = {lr_nominal:.2f} (Q16={lr_inner_q16})")
    print(f"Thermal Cycle: {args.heater_on:.1f} min HEATER ON (100%) <-> {args.heater_off:.1f} min HEATER OFF (0%) [Period: {heater_period_s/60:.1f} min]")
    print(f"Training Cycle: {args.regler_on:.1f} min TRAINING ON (SGD) <-> {args.regler_off:.1f} min TRAINING OFF (W8=0) [Period: {regler_period_s/60:.1f} min]")
    print(f"Live Ring Buffer: Rolling 30 minutes in {RING_BUFFER_JSON}")
    print(f"Final Output: {args.out_json}")
    print("=" * 105)

    # 1. Verify version and initialize client (0.45s timeout avoids 8.3s freezes on dropped UDP packets)
    ensure_version_guard(host=host, port=port)
    client = MamlUdpClient(host=host, port=port, timeout=0.45)
    client_global = client

    # 2. Reset M33 and configure regime
    client.set_w33_matrix(None)  # Reset factory default
    client.clear_w33_hidden_offset()
    time.sleep(0.03)

    client.set_gain_experiment(d_line=d_line, w33=1, target_gain=1.0, clamp=120)
    time.sleep(0.03)

    client.set_config(
        mode=0, jumper_mode=3, led_switches=3, max_meas_win_pct=100, hadamard_khz=500,
        inner_loop_n=100, seed_pct=28, seed_mode=1, w_hid_mag=0, trim_hid_mag=0,
        hadamard_delay_us=5200, lr_inner_q16=max(32, lr_inner_q16)
    )
    time.sleep(0.03)
    client._send_binary(0x13, struct.pack("<BB", 1, 1))  # LEDs ON
    time.sleep(0.02)
    client.set_data_color(COLOR_WHITE, 0.0)
    time.sleep(0.03)

    # 3. DC Baseline calibration with W=0
    print("[*] Executing hardware DC zero calibration (g_baseline_mode=0, W_3=0, W_8=0)...")
    zero_cal_payload = struct.pack("<B48b42b", 0, *([0] * 48), *([0] * 42))
    client._send_binary(MAML_CMD_CENTER_WEIGHTS, zero_cal_payload)
    time.sleep(0.15)
    drain_udp(client)

    # 4. Set W(3) Staircase pattern on reference and bias rows (rows 6 & 7)
    baseline_payload = build_center_weights_payload(1)
    baseline_payload_global = baseline_payload
    print("[*] Setting W(3) staircase pattern ([-40..+40] LSB) on rows 6 & 7...")
    client._send_binary(MAML_CMD_CENTER_WEIGHTS, baseline_payload)
    time.sleep(0.05)
    client.set_regularization(0)
    time.sleep(0.05)

    # Ensure initial heaters are OFF
    client.set_heaters(False, [0, 0, 0, 0])
    time.sleep(0.03)

    ring_history: deque[dict] = deque(maxlen=7200)
    t_start = time.time()
    last_heater_state = None
    last_regler_state = None
    epoch = 0

    print("\n[+] STARTING 20-MINUTE CONTINUOUS EXPERIMENTAL RUN:")
    print("    Live telemetry streaming to GUI and ring buffer.\n")

    while running:
        t_now = time.time()
        elapsed = t_now - t_start

        if elapsed >= total_duration_s:
            print(f"\n[✓] Target experiment duration reached: {elapsed/60:.2f} / {args.duration_minutes:.2f} minutes.")
            break

        # Calculate Heater phase
        heater_time_in_period = elapsed % heater_period_s
        heater_on = heater_time_in_period < heater_on_s
        if heater_on:
            heater_time_left = heater_on_s - heater_time_in_period
        else:
            heater_time_left = heater_period_s - heater_time_in_period

        # Calculate Training phase
        regler_time_in_period = elapsed % regler_period_s
        regler_on = regler_time_in_period < regler_on_s
        if regler_on:
            regler_time_left = regler_on_s - regler_time_in_period
        else:
            regler_time_left = regler_period_s - regler_time_in_period

        # Handle heater toggle
        if heater_on != last_heater_state:
            last_heater_state = heater_on
            if heater_on:
                print(f"\n>>> [T={elapsed/60:.2f} min]: HEATER ON! (All 4 on-board heating elements @ 100%) <<<")
                client.set_heaters(True, [100, 100, 100, 100])
            else:
                print(f"\n>>> [T={elapsed/60:.2f} min]: HEATER OFF! (All 4 on-board heating elements @ 0%) <<<")
                client.set_heaters(False, [0, 0, 0, 0])
            time.sleep(0.02)

        # Handle training toggle
        if regler_on != last_regler_state:
            last_regler_state = regler_on
            if regler_on:
                cur_lr_q16 = lr_inner_q16
                cur_reg = reg_lambda_nominal
                print(f">>> [T={elapsed/60:.2f} min]: TRAINING ON! (Active Online SGD, K={k_batch}, LR={lr_nominal}, λ={reg_lambda_nominal}) <<<")
            else:
                cur_lr_q16 = 0
                cur_reg = 0
                print(f">>> [T={elapsed/60:.2f} min]: TRAINING OFF! (Ablation W8=0, LR=0, pure thermal drift measurement) <<<")
                client._send_binary(MAML_CMD_CENTER_WEIGHTS, baseline_payload)
                client.set_regularization(0)
            time.sleep(0.02)

        if regler_on:
            cur_lr_q16 = lr_inner_q16
            cur_reg = reg_lambda_nominal
            cur_reg_stratum = stratum_reg_nominal
        else:
            cur_lr_q16 = 0
            cur_reg = 0
            cur_reg_stratum = 0

        # Evaluate all 11 strata sequentially
        ep_strata = []
        last_t = None
        for dly in strata_delays:
            res = run_single_sample_stratum_step(client, dly, lr_q16=cur_lr_q16, reg_q16=cur_reg_stratum, k_batch=k_batch)
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

        # Write ring buffer and status for live GUI
        buffer_export = {
            "version": "2.0",
            "experiment": "20min_thermal_cycling",
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
            "k_batch": k_batch,
            "reg_lambda": reg_lambda_nominal,
            "total_records": len(ring_history),
            "max_records": 7200,
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

        # Terminal logging
        h_str = f"ON (100%) [{int(heater_time_left//60):02d}:{int(heater_time_left%60):02d}]" if heater_on else f"OFF (  0%) [{int(heater_time_left//60):02d}:{int(heater_time_left%60):02d}]"
        r_str = f"ON (SGD ) [{int(regler_time_left//60):02d}:{int(regler_time_left%60):02d}]" if regler_on else f"OFF( W8=0) [{int(regler_time_left//60):02d}:{int(regler_time_left%60):02d}]"
        print(
            f"Ep {epoch:5d} [{int(elapsed//3600):02d}:{int((elapsed%3600)//60):02d}:{int(elapsed%60):02d}] | "
            f"HEAT: {h_str} | REGL: {r_str} | "
            f"Mean: {ep_mean_loss:7.0f} L² ({ep_mean_enob:4.2f} b) | "
            f"{target_center_us/1000:.1f}ms: {s_center['loss_lsb2']:7.0f} L² ({s_center['enob_bits']:4.2f} b) | "
            f"W8: [{w8_min:+3d}, {w8_max:+3d}] LSB"
        )
        sys.stdout.flush()

        epoch += 1

    # End of experiment: safe shutdown & save final dataset
    safe_shutdown()

    final_dataset = {
        "metadata": {
            "title": "Inverted MAML Card 2 20-Minute Thermal Stress & Mode A Closed-Loop Regulation",
            "card": "Card 2",
            "attenuator": "1k/3.3k",
            "reference_pattern": "W(3) Staircase on Rows 6 & 7 ([-40..+40] LSB)",
            "duration_minutes": args.duration_minutes,
            "total_elapsed_s": round(time.time() - t_start, 2),
            "total_epochs": len(ring_history),
            "lr": lr_nominal,
            "k_batch": k_batch,
            "reg_lambda": reg_lambda_nominal,
            "heater_cycle": f"{args.heater_on:.1f} min ON / {args.heater_off:.1f} min OFF",
            "training_cycle": f"{args.regler_on:.1f} min ON / {args.regler_off:.1f} min OFF",
            "t_min_us": t_min,
            "t_max_us": t_max,
            "t_step_us": t_step,
            "center_delay_us": target_center_us,
        },
        "epochs": list(ring_history),
    }

    out_file = Path(args.out_json)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(final_dataset, f, indent=2)
    print(f"\n[+] Successfully saved complete {len(ring_history)}-epoch dataset to:\n    {out_file}")


if __name__ == "__main__":
    main()
