#!/home/olle/anaconda3/bin/python
"""
run_card2_5ms_pure.py
Inverted MAML (Patent Pending SE 2630397-4) - Open Science Hardware

500-Epoch Mode A Training on Card 2 (Rev 2.0 Silicon, 1k/5.1k Attenuator, Repaired CH3):
- Single-point temporal snapshot strictly at t = 5.0 ms (5000 us, num_strata = 1)
- Flat Baseline Protocol:
    * Phase 1 (Epochs  0.. 99): Open-loop flat baseline W = 0 LSB (LR = 0, Reg = 0)
    * Phase 2 (Epochs 100..500): Active training directly from W = 0 with L2 anchored at W_null = 0
- Hardware Configuration:
    * Learning Rate: LR = 0.08x (lr_inner_q16 = 82)
    * L2-Regularization: lambda = 1024 (reg_lambda_q16 = 1024)
    * Input Data Dynamic Swing: +/-40 LSB (d_line = 2)
    * Selectable Noise Distribution: LLM Toeplitz (rho=0.85) vs. White Noise
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


def get_compressed_m33(compress_factor: float) -> list[list[int]]:
    """Compresses Matrix 33 weights symmetrically around zero: w_comp = round(w_orig / compress_factor)."""
    if compress_factor <= 1.0:
        return [row[:] for row in ORIGINAL_M33]
    return [
        [int(round(v / compress_factor)) for v in row]
        for row in ORIGINAL_M33
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


def run_5ms_batch_epoch(
    client: MamlUdpClient,
    k_batch: int,
    lr_q16: int,
    reg_q16: int,
) -> dict:
    """
    Executes MAML_CMD_BATCH_STEP on physical T120 silicon strictly at 5000 us (1 stratum).
    Evaluates k_batch capacitor refreshes at 5.0 ms delay.
    """
    pkt = struct.pack(
        "<BBHHHH",
        k_batch,
        1,       # num_strata = 1
        5000,    # t_min_us = 5000
        5000,    # t_max_us = 5000
        lr_q16,
        reg_q16,
    )
    raw = None
    for attempt in range(15):
        drain_udp(client)
        raw = client._send_binary(MAML_CMD_BATCH_STEP, pkt)
        if raw is not None and len(raw) >= client.TELEM_SIZE:
            break
        time.sleep(0.05 * (attempt + 1))

    if raw is None or len(raw) < client.TELEM_SIZE:
        raise RuntimeError("Failed to receive MAML_CMD_BATCH_STEP telemetry from T120.")

    u = struct.unpack(client.TELEM_FMT, raw[:client.TELEM_SIZE])
    loss_total_milli = float(u[29])
    t = client._parse_hw_telemetry(raw)

    epoch_loss = loss_total_milli / 2.0
    epoch_rmse = math.sqrt(loss_total_milli / 6.0)
    epoch_enob = max(0.0, 11.0 - math.log2(max(epoch_rmse, 1.0)))

    err49 = np.array(t.adc49_sig) - np.array(t.z_target)
    snap_rmse = float(np.sqrt(np.mean(err49 ** 2)))
    snap_loss = float(np.sum(err49 ** 2) / 2.0)
    snap_enob = max(0.0, 11.0 - math.log2(max(snap_rmse, 1.0)))

    return {
        "loss_lsb2": round(snap_loss, 1),
        "rmse_lsb": round(snap_rmse, 2),
        "enob_bits": round(snap_enob, 2),
        "batch_eval": {
            "mean_loss_lsb2": round(epoch_loss, 1),
            "mean_rmse_lsb": round(epoch_rmse, 2),
            "mean_enob_bits": round(epoch_enob, 2),
            "samples_evaluated": k_batch,
        },
        "x_ref": [int(v) for v in t.x_ref],
        "z_target": [int(v) for v in t.z_target],
        "adc45": [int(v) for v in t.adc45_sig],
        "adc49": [int(v) for v in t.adc49_sig],
        "err49": [int(v) for v in err49],
        "w_m3": t.w_m3,
        "w_m8": t.w_m8,
        "w_m33": t.w_m33,
        "w8_diag": [t.w_m8[i][i] for i in range(6)],
        "w3_diag": [t.w_m3[i][i] for i in range(6)],
    }


def sweep_temporal_profile(client: MamlUdpClient, delays_us: list[int], n_reps: int = 5) -> dict:
    """Measures single-snapshot loss and ENOB across a sequence of discrete delays."""
    results = {}
    for dly in delays_us:
        client.set_config(
            mode=0, jumper_mode=3, led_switches=3, max_meas_win_pct=100, hadamard_khz=500,
            inner_loop_n=100, seed_pct=28, seed_mode=1, w_hid_mag=0, trim_hid_mag=0,
            hadamard_delay_us=dly, lr_inner_q16=0
        )
        time.sleep(0.03)

        losses = []
        rmses = []
        enobs = []
        for _ in range(n_reps):
            client.draw_fresh_vector()
            time.sleep(0.015)
            raw = client._send_binary(MAML_CMD_GET_TELEMETRY)
            if raw and len(raw) >= client.TELEM_SIZE:
                t = client._parse_hw_telemetry(raw)
                err = np.array(t.adc49_sig) - np.array(t.z_target)
                r = float(np.sqrt(np.mean(err**2)))
                l = float(np.sum(err**2) / 2.0)
                b = max(0.0, 11.0 - math.log2(max(r, 1.0)))
                losses.append(l)
                rmses.append(r)
                enobs.append(b)

        results[str(dly)] = {
            "delay_us": dly,
            "mean_loss_lsb2": round(float(np.mean(losses)), 1) if losses else 0.0,
            "mean_rmse_lsb": round(float(np.mean(rmses)), 2) if rmses else 0.0,
            "mean_enob_bits": round(float(np.mean(enobs)), 2) if enobs else 0.0,
        }
    return results


def main():
    parser = argparse.ArgumentParser(description="500-Epoch Pure 5.0ms Flat Baseline Run on Card 2")
    parser.add_argument("--host", default="192.168.1.50")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--epochs", type=int, default=500)
    parser.add_argument("--k-batch", type=int, default=20)
    parser.add_argument("--lr", type=float, default=0.08)
    parser.add_argument("--reg-lambda", type=int, default=1024)
    parser.add_argument("--noise-color", choices=["toeplitz", "white"], default="toeplitz")
    parser.add_argument("--rho", type=float, default=0.85)
    parser.add_argument("--d-line", type=int, default=2, help="Data line divider (1=>+/-80, 2=>+/-40 LSB)")
    parser.add_argument("--compress-m33-weight", type=float, default=1.0, help="Compress factor for M33 weights (e.g. 2.0 halves swing)")
    parser.add_argument("--w33-variance-lsb-range", type=int, default=0, help="Hidden random offset range [LSB] injected on M33 every 100 epochs (Patent Fig 7 Emulator)")
    parser.add_argument("--tag", type=str, default="card2_5ms_pure")
    args = parser.parse_args()

    color_mode = COLOR_WHITE if args.noise_color == "white" else COLOR_LLM_TOEPLITZ
    color_desc = "White Noise (Uniform Independent)" if args.noise_color == "white" else f"LLM Toeplitz (rho = {args.rho})"
    swing_desc = "+/-40 LSB" if args.d_line == 2 else "+/-80 LSB"
    comp_desc = f"M33 Komprimerad {args.compress_m33_weight:.1f}x" if args.compress_m33_weight > 1.0 else "M33 Original Nominell"
    var_desc = f"Fig 7 Hidden Disturbance ±{args.w33_variance_lsb_range} LSB" if args.w33_variance_lsb_range > 0 else "100% Fryst M33"

    print("=" * 105)
    print("INVERTED MAML: 500-EPOCH PURE 5.0 ms SNAPSHOT EXPERIMENT ON CARD 2")
    print("FLAT BASELINE PROTOCOL: Active Training directly from W = 0 with L2 anchored at W_null = 0")
    print(f"Target: {args.host}:{args.port} | Epochs: {args.epochs} | Batch K: {args.k_batch} @ strictly 5000 µs (1 Stratum)")
    print(f"Noise Profile: {color_desc} | LR: {args.lr:.2f}x | L2 Reg: λ = {args.reg_lambda} | Data Div: {args.d_line} ({swing_desc})")
    print(f"Matrix 33 State: {comp_desc} | Disturbance: {var_desc}")
    print("=" * 105)

    ver_info = ensure_version_guard(host=args.host, port=args.port)
    client = MamlUdpClient(host=args.host, port=args.port, timeout=8.0)

    # 1. Konfigurera regim & M33
    nominal_m33 = get_compressed_m33(args.compress_m33_weight)
    if args.compress_m33_weight > 1.0:
        client.set_w33_matrix(nominal_m33)
        min_w = min(min(r) for r in nominal_m33)
        max_w = max(max(r) for r in nominal_m33)
        print(f"[*] M33 komprimerad med faktor {args.compress_m33_weight:.1f}x runt nollan (Swing: [{min_w:+d}, {max_w:+d}] LSB)")
    else:
        client.set_w33_matrix(None)  # Reset factory default
        print("[*] M33 körs med fabrikskalibrerad 100% fryst originalmatris (Swing: [-36, +84] LSB)")
    client.clear_w33_hidden_offset()
    time.sleep(0.03)

    client.set_gain_experiment(d_line=args.d_line, w33=1, target_gain=1.0, clamp=120)
    time.sleep(0.03)

    lr_inner_q16 = max(32, min(4096, int(round(1024 * args.lr))))
    client.set_config(
        mode=0, jumper_mode=3, led_switches=3, max_meas_win_pct=100, hadamard_khz=500,
        inner_loop_n=100, seed_pct=28, seed_mode=1, w_hid_mag=0, trim_hid_mag=0,
        hadamard_delay_us=5000, lr_inner_q16=lr_inner_q16
    )
    time.sleep(0.03)
    client._send_binary(0x13, struct.pack("<BB", 1, 1))  # LEDs ON
    time.sleep(0.02)
    client.set_data_color(color_mode, args.rho if args.noise_color == "toeplitz" else 0.0)
    time.sleep(0.03)

    # 2. Sätt PLATT baslinje och W_null = 0 i T120 RAM (90-byte all-zero payload)
    print("[*] Sätter platt baslinje: M3_null = 0, M8_null = 0, W = 0 LSB...")
    flat_payload = struct.pack("<B48b42b", 0, *([0] * 48), *([0] * 42))
    client._send_binary(MAML_CMD_CENTER_WEIGHTS, flat_payload)
    client.set_regularization(0)
    time.sleep(0.05)

    # 3. Pre-training Temporal Sweep (4.5 .. 5.5 ms)
    delays_sweep = list(range(4500, 5501, 100))
    print(f"\n[*] Kör förundersökning av tidsfönster: {len(delays_sweep)} punkter över [4500..5500] µs...")
    pre_sweep = sweep_temporal_profile(client, delays_sweep, n_reps=3)
    for d_k, d_v in pre_sweep.items():
        print(f"    {d_k} µs: Loss = {d_v['mean_loss_lsb2']:>9.1f} LSB² | RMSE = {d_v['mean_rmse_lsb']:>6.2f} LSB | ENOB = {d_v['mean_enob_bits']:>5.2f} b")

    # Återställ till 5.0 ms batchkonfiguration
    client.set_config(
        mode=0, jumper_mode=3, led_switches=3, max_meas_win_pct=100, hadamard_khz=500,
        inner_loop_n=100, seed_pct=28, seed_mode=1, w_hid_mag=0, trim_hid_mag=0,
        hadamard_delay_us=5000, lr_inner_q16=lr_inner_q16
    )
    time.sleep(0.03)
    client.set_data_color(color_mode, args.rho if args.noise_color == "toeplitz" else 0.0)
    time.sleep(0.02)

    # Epoch 0: Initial batch measurement with lr=0, reg=0
    print("\n" + "=" * 105)
    print("STARTAR 500-EPOKERS HÅRDVARUTRÄNING (5.0 ms RENT):")
    print(f"Fas 1 (Ep   0.. 99): Öppen loop baslinje W = 0 LSB (LR=0, Reg=0, K={args.k_batch} @ 5.0ms)")
    print(f"Fas 2 (Ep 100..500): Aktiv träning direkt från W = 0 (LR={args.lr:.2f}x, λ={args.reg_lambda}, W_null=0)")
    print("=" * 105)

    t0 = run_5ms_batch_epoch(client, args.k_batch, lr_q16=0, reg_q16=0)
    eval0 = t0["batch_eval"]

    print(f"  Ep   0 [BASE 0   ]: 5.0ms Batch: Loss={eval0['mean_loss_lsb2']:.1f} LSB² | RMSE={eval0['mean_rmse_lsb']:.2f} LSB | ENOB={eval0['mean_enob_bits']:.2f} b | W8={t0['w8_diag']}")
    print("-" * 105)
    print(f"{'Ep #':<6} {'Phase':<20} {'Reg':<5} | {'Loss (LSB²)':<12} | {'RMSE (LSB)':<11} | {'ENOB (Bitar)':<12} | {'W8 Diag (Cols 0..5)':<25}")
    print("-" * 105)

    records = [{
        "epoch": 0,
        "phase": "PHASE1_BASELINE_ZERO",
        "lr_q16": 0,
        "reg_lambda_q16": 0,
        "batch_k": args.k_batch,
        "hadamard_delay_us": 5000,
        **t0,
    }]

    t_start = time.time()
    best_loss = eval0["mean_loss_lsb2"]
    best_ep = 0
    best_enob = eval0["mean_enob_bits"]

    for ep in range(1, args.epochs + 1):
        if ep < 100:
            phase = "PHASE1_BASELINE_ZERO"
            cur_lr_q16 = 0
            cur_reg = 0
        else:
            phase = "PHASE2_TRAIN_FLAT_START"
            cur_lr_q16 = lr_inner_q16
            cur_reg = args.reg_lambda

        if ep == 100:
            print("\n" + "=" * 105)
            print(f">>> [EPOK 100]: SLÅR PÅ AKTIV TRÄNING DIREKT FRÅN W = 0 VID 5.0 ms! (LR={args.lr:.2f}x, λ={args.reg_lambda}, W_null=0)")
            print("=" * 105)

        # Patent Fig 7 Emulator: Inject hidden random offsets on M33 every 100 epochs
        if args.w33_variance_lsb_range > 0 and ep >= 100 and ep % 100 == 0:
            hid_offsets = [
                [random.randint(-args.w33_variance_lsb_range, args.w33_variance_lsb_range) for _ in range(6)]
                for _ in range(6)
            ]
            client.set_w33_hidden_offset(hid_offsets)
            print(f"\n>>> [FIG 7 EMULATOR @ EPOK {ep}]: Injicerade hidden offset på M33 (range ±{args.w33_variance_lsb_range} LSB)!")
            print(f"    FUSK-SKYDD: Digital supervisor Z_target är strikt oförändrad mot nominell M33!\n")
            sys.stdout.flush()

        t_cur = run_5ms_batch_epoch(client, args.k_batch, lr_q16=cur_lr_q16, reg_q16=cur_reg)
        eval_cur = t_cur["batch_eval"]

        records.append({
            "epoch": ep,
            "phase": phase,
            "lr_q16": cur_lr_q16,
            "reg_lambda_q16": cur_reg,
            "batch_k": args.k_batch,
            "hadamard_delay_us": 5000,
            **t_cur,
        })

        if eval_cur["mean_loss_lsb2"] < best_loss and ep >= 100:
            best_loss = eval_cur["mean_loss_lsb2"]
            best_ep = ep
            best_enob = eval_cur["mean_enob_bits"]

        if ep % 25 == 0 or ep == 100 or ep == args.epochs:
            elapsed = time.time() - t_start
            rate = ep / max(1.0, elapsed)
            remain = (args.epochs - ep) / max(0.01, rate)
            print(
                f"Ep {ep:03d}  {phase:<20} {cur_reg:<5} | "
                f"{eval_cur['mean_loss_lsb2']:>10.1f} L² | {eval_cur['mean_rmse_lsb']:>9.2f} L | {eval_cur['mean_enob_bits']:>10.2f} b | "
                f"{str(t_cur['w8_diag']):<25} [{rate:.1f} ep/s, ETA {remain:.0f}s]"
            )
            sys.stdout.flush()

    total_dur = time.time() - t_start
    print("=" * 105)
    print(f"[+] 500-epokers körning slutförd på {total_dur:.1f} sek ({total_dur/60:.1f} min)")

    # 4. Post-training Temporal Sweep (4.5 .. 5.5 ms)
    print(f"\n[*] Kör efterundersökning av tidsfönster med tränade vikter: {len(delays_sweep)} punkter...")
    post_sweep = sweep_temporal_profile(client, delays_sweep, n_reps=3)
    for d_k, d_v in post_sweep.items():
        pre_l = pre_sweep[d_k]["mean_loss_lsb2"]
        post_l = d_v["mean_loss_lsb2"]
        delta_pct = (post_l - pre_l) / max(1.0, pre_l) * 100.0
        print(f"    {d_k} µs: Pre={pre_l:>8.1f} L² -> Post={post_l:>8.1f} L² ({delta_pct:+.1f}%) | ENOB: {pre_sweep[d_k]['mean_enob_bits']:.2f}b -> {d_v['mean_enob_bits']:.2f}b")

    # 5. Spara JSON
    out_stem = f"mode_a_500ep_5ms_pure_{args.tag}"
    json_path = LOG_DIR / f"{out_stem}.json"
    fig_path = DOCS_DIR / f"fig_{out_stem}.png"

    p1_records = [r for r in records if r["phase"] == "PHASE1_BASELINE_ZERO"]
    p2_records = [r for r in records if r["phase"] == "PHASE2_TRAIN_FLAT_START"]

    p1_losses = [r["batch_eval"]["mean_loss_lsb2"] for r in p1_records]
    p2_losses = [r["batch_eval"]["mean_loss_lsb2"] for r in p2_records]
    p1_enobs = [r["batch_eval"]["mean_enob_bits"] for r in p1_records]
    p2_enobs = [r["batch_eval"]["mean_enob_bits"] for r in p2_records]

    meta = {
        "title": f"500-Epoch Mode A Silicon Training: Pure 5.0ms ({color_desc}) on Card 2",
        "patent": "SE 2630397-4 (Open Science Hardware)",
        "hardware": "Card 2 (Rev 2.0 Silicon, 1k/5.1k attenuator, repaired CH3)",
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "epochs": args.epochs,
        "k_batch": args.k_batch,
        "num_strata": 1,
        "t_min_us": 5000,
        "t_max_us": 5000,
        "hadamard_delay_us": 5000,
        "noise_color": args.noise_color,
        "rho": args.rho if args.noise_color == "toeplitz" else 0.0,
        "lr": args.lr,
        "reg_lambda": args.reg_lambda,
        "d_line": args.d_line,
        "compress_m33_weight": args.compress_m33_weight,
        "w33_variance_lsb_range": args.w33_variance_lsb_range,
        "nominal_m33": nominal_m33,
        "duration_sec": round(total_dur, 1),
        "phase1_mean_loss": round(float(np.mean(p1_losses)), 1) if p1_losses else 0.0,
        "phase2_mean_loss": round(float(np.mean(p2_losses)), 1) if p2_losses else 0.0,
        "phase1_mean_enob": round(float(np.mean(p1_enobs)), 2) if p1_enobs else 0.0,
        "phase2_mean_enob": round(float(np.mean(p2_enobs)), 2) if p2_enobs else 0.0,
        "best_loss": round(best_loss, 1),
        "best_loss_ep": best_ep,
        "best_enob": round(best_enob, 2),
        "pre_sweep": pre_sweep,
        "post_sweep": post_sweep,
    }

    payload_json = {
        "metadata": meta,
        "epochs": records,
    }
    with open(json_path, "w") as f:
        json.dump(payload_json, f, indent=2)
    print(f"\n[+] Sparade JSON logg: {json_path}")

    # 6. Generera Figur
    generate_figure(records, meta, fig_path)
    print(f"[+] Genererade figur: {fig_path}")

    if ARTIFACT_DIR.exists():
        import shutil
        shutil.copy2(json_path, ARTIFACT_DIR / json_path.name)
        shutil.copy2(fig_path, ARTIFACT_DIR / fig_path.name)
        print(f"[+] Kopierade logg och figur till artefakt-katalogen: {ARTIFACT_DIR}")

    client.close()


def generate_figure(records: list[dict], meta: dict, out_path: Path):
    epochs = [r["epoch"] for r in records]
    losses = [r["batch_eval"]["mean_loss_lsb2"] for r in records]
    enobs = [r["batch_eval"]["mean_enob_bits"] for r in records]

    fig, axes = plt.subplots(3, 1, figsize=(12, 11), sharex=True)

    # Panel 1: Quadratic Loss
    ax1 = axes[0]
    ax1.plot(epochs, losses, color="#2563eb", linewidth=1.4, label=f"5.0 ms Batch Mean Loss (LSB²)")
    ax1.axvspan(0, 100, color="#f1f5f9", alpha=0.7, label=f"Fas 1: Platt Baslinje W=0 (Snitt: {meta['phase1_mean_loss']:.1f} LSB²)")
    ax1.axvspan(100, len(epochs) - 1, color="#dcfce7", alpha=0.6, label=f"Fas 2: Aktiv Träning direkt från W=0 (Snitt: {meta['phase2_mean_loss']:.1f} LSB²)")
    ax1.set_ylabel("Loss (LSB²)", fontsize=11, fontweight="bold")
    comp_txt = f", M33 Kompr={meta.get('compress_m33_weight', 1.0):.1f}x" if meta.get("compress_m33_weight", 1.0) > 1.0 else ""
    var_txt = f", Var=±{meta.get('w33_variance_lsb_range', 0)} LSB" if meta.get("w33_variance_lsb_range", 0) > 0 else ""
    ax1.set_title(
        f"Inverted MAML: 500 Epoker Rent 5.0 ms ({meta['metadata']['noise_color'].upper() if 'metadata' in meta else meta['noise_color'].upper()}) på Kort 2\n"
        f"Platt Baslinje (W=0), LR={meta['lr']}x, λ={meta['reg_lambda']}, Insving +/-{80 if meta['d_line']==1 else 40} LSB{comp_txt}{var_txt}, 1k/5.1k Dämpare",
        fontsize=12, fontweight="bold"
    )
    ax1.grid(True, linestyle=":", alpha=0.6)
    ax1.legend(loc="upper right", framealpha=0.9)

    # Panel 2: ENOB
    ax2 = axes[1]
    ax2.plot(epochs, enobs, color="#059669", linewidth=1.4, label=f"ENOB (Fas 2 Snitt: {meta['phase2_mean_enob']:.2f} b, Topp: {meta['best_enob']:.2f} b)")
    ax2.axvspan(0, 100, color="#f1f5f9", alpha=0.7)
    ax2.axvspan(100, len(epochs) - 1, color="#dcfce7", alpha=0.6)
    ax2.set_ylabel("ENOB (Bitar)", fontsize=11, fontweight="bold")
    ax2.grid(True, linestyle=":", alpha=0.6)
    ax2.legend(loc="lower right", framealpha=0.9)

    # Panel 3: M8 Weights Trajectory
    ax3 = axes[2]
    w8_cols = np.array([r["w8_diag"] for r in records])  # (501, 6)
    colors = ["#2563eb", "#d97706", "#059669", "#dc2626", "#7c3aed", "#0891b2"]
    for c in range(6):
        ax3.plot(epochs, w8_cols[:, c], color=colors[c], linewidth=1.3, label=f"Ch {c} (Slut: {w8_cols[-1, c]:+d} LSB)")
    ax3.axvspan(0, 100, color="#f1f5f9", alpha=0.7)
    ax3.axvspan(100, len(epochs) - 1, color="#dcfce7", alpha=0.6)
    ax3.axhline(0, color="#64748b", linestyle="--", linewidth=0.8)
    ax3.set_ylabel("M8 Vikt (LSB)", fontsize=11, fontweight="bold")
    ax3.set_xlabel("Epok (K=20 Batch @ 5.0 ms)", fontsize=11, fontweight="bold")
    ax3.grid(True, linestyle=":", alpha=0.6)
    ax3.legend(loc="upper left", ncol=3, framealpha=0.9, fontsize=9)

    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()


if __name__ == "__main__":
    main()

