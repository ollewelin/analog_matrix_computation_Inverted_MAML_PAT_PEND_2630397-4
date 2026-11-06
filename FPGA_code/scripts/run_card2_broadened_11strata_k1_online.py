#!/home/olle/anaconda3/bin/python
"""
run_card2_broadened_11strata_k1_online.py
Inverted MAML (Patent Pending SE 2630397-4) - Open Science Hardware

Card 2 Broadened Window [4.5 ms .. 5.5 ms] Pure Online Single-Sample SGD:
- Evaluates 11 strata [4500, 4600, ..., 5500 us] sequentially per epoch.
- PURE ONLINE SINGLE-SAMPLE UPDATE: k_batch = 1, num_strata = 1 for EVERY step!
- No hardware batch accumulation: weights update immediately on silicon for EVERY sample!
- 4-Phase Protocol (1000 Epochs):
    * Phase 1 (Ep   0.. 99): Open-loop flat baseline W = 0 LSB (LR=0, Reg=0, Nominal M33)
    * Phase 2 (Ep 100..199): Nominal Online Convergence (LR=0.02x, λ=2048, Nominal M33)
    * Phase 3 (Ep 200..599): Online Disturbance Tracking (LR=0.02x, λ=2048, Fig 7 ±5 LSB shifted every 100 ep)
    * Phase 4 (Ep 600..1000): Ablation Control (W=0, LR=0, Reg=0, Fig 7 ±5 LSB shifted every 100 ep)
"""

from __future__ import annotations
import sys
import time
import json
import math
import struct
import random
import argparse
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from gui.udp_client import (
    MamlUdpClient,
    MAML_CMD_GET_TELEMETRY,
    MAML_CMD_CENTER_WEIGHTS,
    MAML_CMD_BATCH_STEP,
    COLOR_WHITE,
    COLOR_LLM_TOEPLITZ,
)
from FPGA_code.scripts.verify_and_guard_version import ensure_version_guard

LOG_DIR = REPO_ROOT / "FPGA_code" / "logs" / "mode_a_extended_training"
LOG_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR = REPO_ROOT / "FPGA_code" / "docs" / "figures"
DOCS_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACT_DIR = Path("/home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a")

# Exact Factory Calibrated Frozen Reference Payload for Matrix 33 (SE 2630397-4)
ORIGINAL_M33 = [
    [+76, -20, +28,  -4, +44, -36],  # Row 0
    [-20, +84, -12, +44,  -4, +36],  # Row 1
    [+36,  -4, +80, -16, +32,  -4],  # Row 2
    [ -4, +40,  -8, +72, -12, +44],  # Row 3
    [+44, -12, +28, -12, +76,  -8],  # Row 4
    [-28, +32,  -4, +40,  -8, +82],  # Row 5
]


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
    k_batch: int = 1,
) -> dict:
    """
    Executes MAML_CMD_BATCH_STEP with k_batch, num_strata=1 at delay_us.
    Hardware evaluates k_batch samples, extracts Hadamard gradients, and
    updates weights with lr_q16 and reg_q16.
    """
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
    parser = argparse.ArgumentParser(description="1000-Epoch Mode A Online Single-Sample SGD across [4.5..5.5 ms] on Card 2")
    parser.add_argument("--host", default="192.168.1.50")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--epochs", type=int, default=1000)
    parser.add_argument("--k-batch", type=int, default=1, help="Mini-batch size K vectors per stratum update")
    parser.add_argument("--lr", type=float, default=0.02)
    parser.add_argument("--reg-lambda", type=int, default=2048)
    parser.add_argument("--noise-color", choices=["toeplitz", "white"], default="toeplitz")
    parser.add_argument("--rho", type=float, default=0.85)
    parser.add_argument("--d-line", type=int, default=2, help="Data line divider (2=>+/-40 LSB)")
    parser.add_argument("--w33-variance-lsb-range", type=int, default=5, help="Patent Fig 7 hidden offset range (±5 LSB)")
    parser.add_argument("--attenuator", type=str, default="1k/3.3k")
    parser.add_argument("--t-min", type=int, default=4500)
    parser.add_argument("--t-max", type=int, default=5500)
    parser.add_argument("--t-step", type=int, default=100)
    parser.add_argument("--card", type=str, default="Card 2", help="Card name (e.g. Card 1 or Card 2)")
    parser.add_argument("--prefix", type=str, default="mode_a", help="Prefix for log/figures: mode_a, mode_b, or card1_mode_a")
    parser.add_argument("--jumper-mode", type=int, default=3, help="Jumper mode for set_config: 1=OFF (Mode B), 3=Mode A")
    parser.add_argument("--staircase-w3", action="store_true", help="Apply staircase pattern [-40..+40] LSB to M3 reference and bias rows")
    parser.add_argument("--tag", type=str, default=None)
    args = parser.parse_args()

    strata_delays = list(range(args.t_min, args.t_max + 1, args.t_step))
    num_strata = len(strata_delays)

    lr_str = f"lr{str(args.lr).replace('.', 'p')}"
    swing_str = f"swing{80 if args.d_line == 1 else 40}"
    var_str = f"var{args.w33_variance_lsb_range}"
    att_slug = args.attenuator.replace("/", "_").replace(".", "p")
    stair_str = "_w3staircase" if args.staircase_w3 else ""
    abl_str = "_ablation" if args.epochs >= 600 else ""
    k_str = f"k{args.k_batch}"
    tag = args.tag or f"broadened_{args.t_min}to{args.t_max}us_{args.noise_color}_reg{args.reg_lambda}_{lr_str}_{swing_str}_{var_str}_{k_str}_{att_slug}{stair_str}{abl_str}"

    out_stem = f"{args.prefix}_{args.epochs}ep_{tag}"
    json_path = LOG_DIR / f"{out_stem}.json"
    fig_path = DOCS_DIR / f"fig_{out_stem}.png"
    fig_profile_path = DOCS_DIR / f"fig_{out_stem}_temporal_profile.png"

    print("=" * 105)
    print(f"INVERTED MAML: 1000-EPOCH BROADENED WINDOW [4.5 - 5.5 ms] PURE ONLINE SGD ON {args.card.upper()}")
    print(f"Sampling Protocol: {num_strata} Strata [{args.t_min} .. {args.t_max} µs, step {args.t_step} µs]")
    print(f"Weight Update: PURE ONLINE SINGLE-SAMPLE (k_batch=1, num_strata=1) - UPDATED EVERY SAMPLE!")
    print(f"Target: {args.host}:{args.port} | Epochs: {args.epochs} | Updates per Epoch: {num_strata} (Total: {args.epochs * num_strata})")
    print(f"Hyperparameters: LR = {args.lr:.2f}x | L2 Reg: λ = {args.reg_lambda} | Data Div: {args.d_line} (Swing: ±{80 if args.d_line==1 else 40} LSB)")
    print(f"Perturbation: Fig 7 Hidden Offset ±{args.w33_variance_lsb_range} LSB (every 100 epochs) | Attenuator: {args.attenuator}")
    print("=" * 105)

    ver_info = ensure_version_guard(host=args.host, port=args.port)
    client = MamlUdpClient(host=args.host, port=args.port, timeout=8.0)

    # 1. Konfigurera regim & M33
    client.set_w33_matrix(None)  # Reset factory default
    client.clear_w33_hidden_offset()
    time.sleep(0.03)

    client.set_gain_experiment(d_line=args.d_line, w33=1, target_gain=1.0, clamp=120)
    time.sleep(0.03)

    lr_inner_q16 = max(1, min(4096, int(round(1024 * args.lr))))
    client.set_config(
        mode=0, jumper_mode=args.jumper_mode, led_switches=3, max_meas_win_pct=100, hadamard_khz=500,
        inner_loop_n=100, seed_pct=28, seed_mode=1, w_hid_mag=0, trim_hid_mag=0,
        hadamard_delay_us=5000, lr_inner_q16=max(32, lr_inner_q16)
    )
    time.sleep(0.03)
    client._send_binary(0x13, struct.pack("<BB", 1, 1))  # LEDs ON
    time.sleep(0.02)
    if args.noise_color == "white":
        client.set_data_color(COLOR_WHITE, 0.0)
    else:
        client.set_data_color(COLOR_LLM_TOEPLITZ, args.rho)
    time.sleep(0.03)

    # 2. Sätt baslinje i T120 RAM
    if args.staircase_w3:
        from FPGA_code.config.w3_staircase_pattern import build_center_weights_payload, get_staircase_config
        staircase_cfg = get_staircase_config()
        baseline_payload = build_center_weights_payload(1)
        print("[*] Sätter W(3) trappmönster ([-40..+40] LSB) på referens- och biasrader...")
    else:
        staircase_cfg = None
        baseline_payload = struct.pack("<B48b42b", 0, *([0] * 48), *([0] * 42))
        print("[*] Sätter platt baslinje: M3_null = 0, M8_null = 0, W = 0 LSB...")

    client._send_binary(MAML_CMD_CENTER_WEIGHTS, baseline_payload)
    client.set_regularization(0)
    time.sleep(0.05)

    print("\n" + "=" * 105)
    print("STARTAR 1000-EPOKERS HÅRDVARUTRÄNING (ONLINE SINGLE-SAMPLE SGD ÖVER 4.5..5.5 ms):")
    print(f"Fas 1 (Ep   0.. 99): Öppen loop baslinje W = 0 LSB (LR=0, Reg=0, 11 strata utvärderas)")
    print(f"Fas 2 (Ep 100..199): Nominell Online Träning (LR={args.lr:.2f}x, λ={args.reg_lambda}, 11 uppdateringar/ep)")
    print(f"Fas 3 (Ep 200..599): Online Störningsföljning (Fig 7 ±{args.w33_variance_lsb_range} LSB, 11 uppdateringar/ep)")
    print(f"Fas 4 (Ep 600..1000): Ablation Control (W=0, LR=0, Reg=0, Fig 7 ±{args.w33_variance_lsb_range} LSB aktiv)")
    print("=" * 105)

    # Epoch 0: Initial measurement
    strata_0 = []
    last_t_obj = None
    for dly in strata_delays:
        res = run_single_sample_stratum_step(client, dly, lr_q16=0, reg_q16=0, k_batch=args.k_batch)
        strata_0.append(res)
        last_t_obj = res["t_obj"]

    mean_loss_0 = float(np.mean([s["loss_lsb2"] for s in strata_0]))
    mean_rmse_0 = float(np.sqrt(np.mean([s["loss_lsb2"] * 2.0 / 6.0 for s in strata_0])))
    mean_enob_0 = max(0.0, 11.0 - math.log2(max(mean_rmse_0, 1.0)))

    # 5.0ms center stratum (index 5)
    center_idx = strata_delays.index(5000) if 5000 in strata_delays else len(strata_delays) // 2
    s5_0 = strata_0[center_idx]

    print(f"  Ep   0 [BASE 0   ]: Window Mean [4.5..5.5ms]: Loss={mean_loss_0:8.1f} L² | ENOB={mean_enob_0:4.2f} b")
    print(f"                    5.0ms Snapshot:            Loss={s5_0['loss_lsb2']:8.1f} L² | ENOB={s5_0['enob_bits']:4.2f} b | W8={s5_0['t_obj'].w_m8[0]}")
    print("-" * 105)

    records = [{
        "epoch": 0,
        "phase": "PHASE1_BASELINE_ZERO",
        "lr_q16": 0,
        "reg_lambda_q16": 0,
        "window_eval": {
            "mean_loss_lsb2": round(mean_loss_0, 1),
            "mean_rmse_lsb": round(mean_rmse_0, 2),
            "mean_enob_bits": round(mean_enob_0, 2),
            "num_strata": num_strata,
        },
        "center_5ms": {
            "loss_lsb2": s5_0["loss_lsb2"],
            "rmse_lsb": s5_0["rmse_lsb"],
            "enob_bits": s5_0["enob_bits"],
        },
        "strata_losses": [s["loss_lsb2"] for s in strata_0],
        "strata_enobs": [s["enob_bits"] for s in strata_0],
        "w_m3": last_t_obj.w_m3,
        "w_m8": last_t_obj.w_m8,
        "w8_row0": list(last_t_obj.w_m8[0]),
    }]

    t_start = time.time()
    best_loss = mean_loss_0
    best_ep = 0
    best_enob = mean_enob_0

    applied_disturbances = {}
    current_hid_offsets = [[0] * 6 for _ in range(6)]

    for ep in range(1, args.epochs + 1):
        if ep < 100:
            phase = "PHASE1_BASELINE_ZERO"
            cur_lr_q16 = 0
            cur_reg = 0
        elif ep < 200:
            phase = "PHASE2_NOMINAL_CONVERGE"
            cur_lr_q16 = lr_inner_q16
            cur_reg = args.reg_lambda
        elif ep < 600 or args.epochs <= 500:
            phase = "PHASE3_DISTURBANCE_ADAPT"
            cur_lr_q16 = lr_inner_q16
            cur_reg = args.reg_lambda
        else:
            phase = "PHASE4_ABLATION_OPEN_LOOP"
            cur_lr_q16 = 0
            cur_reg = 0

        if ep == 100:
            print("\n" + "=" * 105)
            print(f">>> [EPOK 100]: FAS 2 STARTAR: Slår PÅ aktiv online-träning mot nominell M33!")
            print(f"    (LR={args.lr:.2f}x, λ={args.reg_lambda}, W_null=0, 11 singel-sample uppdateringar per epok)")
            print("=" * 105)

        if ep == 200 and args.w33_variance_lsb_range > 0:
            print("\n" + "=" * 105)
            print(f">>> [EPOK 200]: FAS 3 STARTAR: Kopplar in Patent Fig 7 Hårdvarustörning (±{args.w33_variance_lsb_range} LSB) med aktiv online-kompensation!")
            print("=" * 105)

        if ep == 600 and args.epochs >= 600:
            print("\n" + "=" * 105)
            print(f">>> [EPOK 600]: FAS 4 ABLATION CONTROL STARTAR!")
            print(f"    Slår AV träning (LR=0, Reg=0) och nollställer kompensationsvikterna W(3,8) = 0 LSB!")
            print(f"    Hårdvarustörningen (±{args.w33_variance_lsb_range} LSB) fortsätter över alla 11 strata!")
            print("=" * 105 + "\n")
            client._send_binary(MAML_CMD_CENTER_WEIGHTS, baseline_payload)
            client.set_regularization(0)
            time.sleep(0.05)

        # Fig 7 Emulator: Inject hidden random offsets on M33 every 100 epochs starting at ep 200
        # Fas 3 (ep 200..599): 4 unika paket genereras (ep 200, 300, 400, 500)
        # Fas 4 (ep 600..1000): Exakt samma 4 paket återanvänds (200->600, 300->700, 400->800, 500->900)
        if args.w33_variance_lsb_range > 0 and ep >= 200 and ep % 100 == 0:
            if ep in [200, 300, 400, 500]:
                current_hid_offsets = [
                    [random.randint(-args.w33_variance_lsb_range, args.w33_variance_lsb_range) for _ in range(6)]
                    for _ in range(6)
                ]
                applied_disturbances[str(ep)] = current_hid_offsets
                tag_phase = "FAS 3 AKTIV ONLINE KOMPENSATION"
                print("\n" + "=" * 105)
                print(f">>> [FIG 7 EMULATOR @ EPOK {ep} - {tag_phase}]: NY RANDOMISERAD HIDDEN OFFSET MATRIX PÅ M33 (±{args.w33_variance_lsb_range} LSB):")
            else:
                mirror_ep = 500 if ep == 1000 else (200 + ((ep - 600) % 400))
                current_hid_offsets = [row[:] for row in applied_disturbances[str(mirror_ep)]]
                applied_disturbances[str(ep)] = current_hid_offsets
                tag_phase = f"FAS 4 ABLATION (W=0, LR=0) [SPEGLAR EPOK {mirror_ep}]"
                print("\n" + "=" * 105)
                print(f">>> [FIG 7 EMULATOR @ EPOK {ep} - {tag_phase}]: ÅTERANVÄNDER PARAD OFFSET MATRIX FRÅN EPOK {mirror_ep} (±{args.w33_variance_lsb_range} LSB):")

            client.set_w33_hidden_offset(current_hid_offsets)
            for r in range(6):
                row_str = " ".join(f"{current_hid_offsets[r][c]:+3d}" for c in range(6))
                print(f"    Rad {r}: [ {row_str} ] LSB")
            print("=" * 105 + "\n")
            sys.stdout.flush()

            if ep >= 600:
                client._send_binary(MAML_CMD_CENTER_WEIGHTS, baseline_payload)

        # Execute 11 stratum steps sequentially, updating weights IMMEDIATELY after each step!
        ep_strata = []
        last_t = None
        for dly in strata_delays:
            res = run_single_sample_stratum_step(client, dly, lr_q16=cur_lr_q16, reg_q16=cur_reg, k_batch=args.k_batch)
            ep_strata.append(res)
            last_t = res["t_obj"]

        ep_mean_loss = float(np.mean([s["loss_lsb2"] for s in ep_strata]))
        ep_mean_rmse = float(np.sqrt(np.mean([s["loss_lsb2"] * 2.0 / 6.0 for s in ep_strata])))
        ep_mean_enob = max(0.0, 11.0 - math.log2(max(ep_mean_rmse, 1.0)))
        s5 = ep_strata[center_idx]

        rec = {
            "epoch": ep,
            "phase": phase,
            "lr_q16": cur_lr_q16,
            "reg_lambda_q16": cur_reg,
            "window_eval": {
                "mean_loss_lsb2": round(ep_mean_loss, 1),
                "mean_rmse_lsb": round(ep_mean_rmse, 2),
                "mean_enob_bits": round(ep_mean_enob, 2),
                "num_strata": num_strata,
            },
            "center_5ms": {
                "loss_lsb2": s5["loss_lsb2"],
                "rmse_lsb": s5["rmse_lsb"],
                "enob_bits": s5["enob_bits"],
            },
            "strata_losses": [s["loss_lsb2"] for s in ep_strata],
            "strata_enobs": [s["enob_bits"] for s in ep_strata],
            "w_m3": last_t.w_m3,
            "w_m8": last_t.w_m8,
            "w8_row0": list(last_t.w_m8[0]),
            "hidden_offset": [row[:] for row in current_hid_offsets],
        }
        records.append(rec)

        if ep_mean_loss < best_loss and ep >= 100:
            best_loss = ep_mean_loss
            best_ep = ep
            best_enob = ep_mean_enob

        if ep % 10 == 0 or ep in [1, 99, 100, 199, 200, 599, 600, args.epochs]:
            p_code = "P1_BASE" if ep < 100 else ("P2_NOMI" if ep < 200 else ("P3_DIST" if ep < 600 else "P4_ABLA"))
            elapsed = time.time() - t_start
            rate = ep / elapsed if elapsed > 0 else 0
            w8_samp = [int(v) for v in last_t.w_m8[0]]
            w3_samp = [int(v) for v in last_t.w_m3[0]]
            print(
                f"  Ep {ep:4d} [{p_code}]: Win Loss={ep_mean_loss:8.1f} L² | Win ENOB={ep_mean_enob:4.2f} b | "
                f"5.0ms: {s5['loss_lsb2']:8.1f} L² ({s5['enob_bits']:4.2f}b) | W8_R0={w8_samp} | Rate={rate:4.1f} ep/s"
            )
            sys.stdout.flush()

    total_time = time.time() - t_start
    print("\n" + "=" * 105)
    print(f"[+] HÅRDVARUTRÄNING FULLBORDAD:")
    print(f"    Totaltid:            {total_time:.1f} s ({total_time / args.epochs * 1000:.1f} ms/epok, {total_time / (args.epochs * num_strata) * 1000:.1f} ms/sample)")
    print(f"    Bästa Window Loss:   {best_loss:.1f} LSB² (Epok {best_ep})")
    print(f"    Bästa Window ENOB:   {best_enob:.2f} bitar")
    print("=" * 105)

    # 5. Spara JSON
    payload_json = {
        "metadata": {
            "experiment": f"Inverted MAML {'Mode B (Uncompensated, Jumpers Disconnected)' if args.prefix=='mode_b' else 'Mode A (Compensated)'} Broadened Window [4.5..5.5 ms] Pure Online Single-Sample SGD on {args.card}",
            "mode": args.prefix,
            "card": args.card,
            "jumper_mode": args.jumper_mode,
            "patent": "SE 2630397-4 (Open Science Hardware)",
            "hardware": f"{args.card} (Rev 2.0 Silicon, {args.attenuator} attenuator)",
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "epochs": args.epochs,
            "strata_delays_us": strata_delays,
            "num_strata": num_strata,
            "k_batch": args.k_batch,
            "online_mode": f"immediate_k{args.k_batch}_update_per_stratum",
            "lr": args.lr,
            "reg_lambda": args.reg_lambda,
            "d_line": args.d_line,
            "noise_color": args.noise_color,
            "rho": args.rho,
            "w33_variance_lsb_range": args.w33_variance_lsb_range,
            "attenuator": args.attenuator,
            "staircase_w3": args.staircase_w3,
            "staircase_config": staircase_cfg,
            "best_loss": best_loss,
            "best_enob": best_enob,
            "best_loss_ep": best_ep,
            "total_time_s": round(total_time, 2),
            "applied_disturbances": applied_disturbances,
        },
        "epochs": records,
    }
    with open(json_path, "w") as f:
        json.dump(payload_json, f, indent=2)
    print(f"\n[+] Sparade JSON logg: {json_path}")

    # 6. Generera Figurer
    generate_timeline_figure(records, payload_json["metadata"], fig_path)
    print(f"[+] Genererade timeline-figur: {fig_path}")

    generate_temporal_profile_figure(records, strata_delays, payload_json["metadata"], fig_profile_path)
    print(f"[+] Genererade temporal profilfigur: {fig_profile_path}")

    if ARTIFACT_DIR.exists():
        import shutil
        shutil.copy2(json_path, ARTIFACT_DIR / json_path.name)
        shutil.copy2(fig_path, ARTIFACT_DIR / fig_path.name)
        shutil.copy2(fig_profile_path, ARTIFACT_DIR / fig_profile_path.name)
        print(f"[+] Kopierade logg och figurer till artefakt-katalogen: {ARTIFACT_DIR}")

    client.close()


def generate_timeline_figure(records: list[dict], meta: dict, out_path: Path):
    epochs = [r["epoch"] for r in records]
    win_losses = [r["window_eval"]["mean_loss_lsb2"] for r in records]
    win_enobs = [r["window_eval"]["mean_enob_bits"] for r in records]
    c5_losses = [r["center_5ms"]["loss_lsb2"] for r in records]
    c5_enobs = [r["center_5ms"]["enob_bits"] for r in records]

    fig, axes = plt.subplots(3, 1, figsize=(14, 11), sharex=True)
    ax1, ax2, ax3 = axes
    var_range = meta.get("w33_variance_lsb_range", 0)

    # Panel 1: Quadratic Loss
    ax1.plot(epochs, win_losses, color="#d97706", linewidth=1.5, label="Window Mean [4.5..5.5 ms] Loss (LSB²)")
    ax1.plot(epochs, c5_losses, color="#2563eb", linewidth=1.0, alpha=0.75, label="5.0 ms Center Loss (LSB²)")

    p1_losses = [r["window_eval"]["mean_loss_lsb2"] for r in records if r["epoch"] < 100]
    p2_losses = [r["window_eval"]["mean_loss_lsb2"] for r in records if 100 <= r["epoch"] < 200]
    p3_losses = [r["window_eval"]["mean_loss_lsb2"] for r in records if 200 <= r["epoch"] < 600]
    p4_losses = [r["window_eval"]["mean_loss_lsb2"] for r in records if r["epoch"] >= 600]

    p1_str = f"{np.mean(p1_losses):.1f} L²" if p1_losses else "N/A"
    p2_str = f"{np.mean(p2_losses):.1f} L²" if p2_losses else "N/A"
    p3_str = f"{np.mean(p3_losses):.1f} L²" if p3_losses else "N/A"
    p4_str = f"{np.mean(p4_losses):.1f} L²" if p4_losses else "N/A"

    for ax in axes:
        ax.axvspan(0, 100, color="#f1f5f9", alpha=0.7)
        ax.axvspan(100, 200, color="#dcfce7", alpha=0.6)
        ax.axvspan(200, 600, color="#fef3c7", alpha=0.6)
        if max(epochs) >= 600:
            ax.axvspan(600, max(epochs), color="#fee2e2", alpha=0.6)

    ax1.axvspan(0, 100, color="#f1f5f9", alpha=0.7, label=f"Phase 1: Baseline W=0 (Win: {p1_str})")
    ax1.axvspan(100, 200, color="#dcfce7", alpha=0.6, label=f"Phase 2: Train ON, Dist=0 (Win: {p2_str})")
    ax1.axvspan(200, 600, color="#fef3c7", alpha=0.6, label=f"Phase 3: Active Comp, Dist=±{var_range} (Win: {p3_str})")
    if max(epochs) >= 600:
        ax1.axvspan(600, max(epochs), color="#fee2e2", alpha=0.6, label=f"Phase 4: Ablation W=0, Dist=±{var_range} (Win: {p4_str})")

    ax1.set_ylabel("Loss (LSB²)", fontsize=11, fontweight="bold")
    ax1.set_title(
        f"Inverted MAML: 1000 Epochs Broadened Window [4.5..5.5 ms] Online Single-Sample SGD on {meta.get('card', 'Card 2')}\n"
        f"LR={meta['lr']}x, λ={meta['reg_lambda']}, Swing ±{40} LSB, Dist=±{var_range} LSB, {meta['attenuator']} Attenuator (K=1, 11 Updates/Epoch)",
        fontsize=12, fontweight="bold"
    )
    ax1.grid(True, linestyle=":", alpha=0.6)
    ax1.legend(loc="upper right", fontsize=8.5, framealpha=0.92)

    # Panel 2: ENOB
    ax2.plot(epochs, win_enobs, color="#d97706", linewidth=1.5, label=f"Window Mean ENOB [4.5..5.5 ms] (Mean: {np.mean(win_enobs[200:600]):.2f} b)")
    peak_c5 = max(c5_enobs[200:600]) if len(c5_enobs) > 200 else max(c5_enobs)
    ax2.plot(epochs, c5_enobs, color="#059669", linewidth=1.1, alpha=0.8, label=f"5.0 ms Center ENOB (Peak: {peak_c5:.2f} b)")
    ax2.set_ylabel("ENOB (Bits)", fontsize=11, fontweight="bold")
    ax2.set_ylim(2.5, 7.8)
    ax2.grid(True, linestyle=":", alpha=0.6)
    ax2.legend(loc="upper right", fontsize=8.5, framealpha=0.92)

    # Panel 3: M8 Weight Trajectories (Row 0, Channels 0..5)
    w8_channels = [[r["w8_row0"][c] for r in records] for c in range(6)]
    colors_ch = ["#2563eb", "#d97706", "#059669", "#dc2626", "#7c3aed", "#0891b2"]
    for c in range(6):
        ax3.plot(epochs, w8_channels[c], color=colors_ch[c], linewidth=1.2, label=f"M8 Ch {c} (End: {w8_channels[c][-1]:+d} LSB)")
    ax3.axhline(0, color="#64748b", linestyle="--", linewidth=0.8)
    ax3.set_ylabel("M8 Row 0 [LSB]", fontsize=11, fontweight="bold")
    ax3.set_xlabel("Epoch (11 Single-Sample Updates per Epoch across 4.5..5.5 ms)", fontsize=11, fontweight="bold")
    ax3.grid(True, linestyle=":", alpha=0.6)
    ax3.legend(loc="upper right", fontsize=8.0, ncol=3, framealpha=0.92)

    for i, ax in enumerate(axes):
        ax.axvline(x=100, color="#2563eb", linestyle=":", linewidth=1.5, alpha=0.9)
        for d_ep in [200, 300, 400, 500]:
            ax.axvline(x=d_ep, color="#ea580c", linestyle="--", linewidth=1.3, alpha=0.85)
        ax.axvline(x=600, color="#dc2626", linestyle="-", linewidth=1.8, alpha=0.95)

    plt.tight_layout()
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def generate_temporal_profile_figure(records: list[dict], strata_delays: list[int], meta: dict, out_path: Path):
    """Plots per-stratum ENOB curves across [4.5..5.5 ms] for each of the 4 phases."""
    delays_ms = np.array(strata_delays) / 1000.0

    # Collect mean per-stratum ENOB across phases
    p1_recs = [r for r in records if r["epoch"] < 100]
    p2_recs = [r for r in records if 100 <= r["epoch"] < 200]
    p3_recs = [r for r in records if 200 <= r["epoch"] < 600]
    p4_recs = [r for r in records if r["epoch"] >= 600]

    fig, ax = plt.subplots(figsize=(11, 6.5), dpi=180)

    if p1_recs:
        p1_enobs = np.mean([[r["strata_enobs"][i] for i in range(len(strata_delays))] for r in p1_recs], axis=0)
        ax.plot(delays_ms, p1_enobs, "o-", color="#64748b", linewidth=2.0, markersize=7,
                label=f"Phase 1: Baseline W=0 (Mean: {np.mean(p1_enobs):.2f} b)")
    if p2_recs:
        p2_enobs = np.mean([[r["strata_enobs"][i] for i in range(len(strata_delays))] for r in p2_recs], axis=0)
        ax.plot(delays_ms, p2_enobs, "s-", color="#2563eb", linewidth=2.2, markersize=7,
                label=f"Phase 2: Nominal Converged (Mean: {np.mean(p2_enobs):.2f} b)")
    if p3_recs:
        p3_enobs = np.mean([[r["strata_enobs"][i] for i in range(len(strata_delays))] for r in p3_recs], axis=0)
        ax.plot(delays_ms, p3_enobs, "D-", color="#059669", linewidth=2.5, markersize=8,
                label=f"Phase 3: Active Comp under Dist ±{meta.get('w33_variance_lsb_range', 5)} (Mean: {np.mean(p3_enobs):.2f} b)")
    if p4_recs:
        p4_enobs = np.mean([[r["strata_enobs"][i] for i in range(len(strata_delays))] for r in p4_recs], axis=0)
        ax.plot(delays_ms, p4_enobs, "^--", color="#dc2626", linewidth=2.0, markersize=7,
                label=f"Phase 4: Ablation W=0 (Mean: {np.mean(p4_enobs):.2f} b)")

    ax.set_title(
        "Inverted MAML: Generalization Profile across Broadened Temporal Window [4.5 – 5.5 ms]\n"
        f"{meta.get('card', 'Card 2')} Silicon | Pure Online Single-Sample SGD (K=1) | Attenuator: {meta.get('attenuator', '1k/3.3k')}",
        fontsize=12, fontweight="bold", pad=12
    )
    ax.set_xlabel("Snapshot Sampling Delay (ms)", fontsize=11, fontweight="bold")
    ax.set_ylabel("Measured Precision (ENOB Bits)", fontsize=11, fontweight="bold")
    ax.set_xticks(delays_ms)
    ax.set_xticklabels([f"{d:.1f} ms" for d in delays_ms], fontsize=9)
    ax.set_ylim(2.5, 7.5)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(loc="lower left", fontsize=10, framealpha=0.92)

    plt.tight_layout()
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()

