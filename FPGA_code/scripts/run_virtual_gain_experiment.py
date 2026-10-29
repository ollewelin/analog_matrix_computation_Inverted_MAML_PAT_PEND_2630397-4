#!/usr/bin/env python3
"""
run_virtual_gain_experiment.py: Automated 200-Epoch Runner for Virtual Gain Experiments
Inverted MAML AIMC Platform (Patent Pending SE 2630397-4)
Hardware: Efinix Trion T120 Master SoC + T20 Controller on PCB v1.3.2 (1k / 3.3k Ohm)
Tag: [VIRTUAL_HARDWARE_EMULATION]
"""

import sys
import time
import json
import struct
import argparse
import subprocess
import numpy as np
from pathlib import Path

# Add repo root to import path
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from gui.udp_client import MamlUdpClient, MAML_CMD_BATCH_STEP


def get_git_commit():
    try:
        res = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except Exception:
        return "unknown"


def run_single_condition(
    d_line: int = 2,
    w33: int = 2,
    target_gain: float = 4.0,
    clamp: int = 120,
    k: int = 20,
    lr: float = 0.03,
    epochs: int = 200,
    strata: int = 10,
    t_min_us: int = 4900,
    t_max_us: int = 5100,
    host: str = "192.168.1.50",
    port: int = 5000,
    out_json: Path = None,
    telem_stride: int = 100,
    warm_start: bool = False,
    reg_lambda: float = 0.0,
):
    client = MamlUdpClient(host=host, port=port, timeout=4.0)
    lr_inner_q16 = max(32, min(4096, int(round(1024 * lr))))
    git_hash = get_git_commit()

    tag = f"gain_exp_d{d_line}_w{w33}_g{int(round(target_gain*100)):03d}p_c{clamp}_k{k}_lr{int(round(lr*100)):02d}p_{epochs}ep"
    reg_q16 = max(0, min(16384, int(round(65536 * reg_lambda))))
    if strata == 1 and t_min_us == t_max_us:
        tag += f"_s1_{t_min_us}us"
    if reg_q16 > 0:
        tag += f"_reg{reg_q16}q16"
    if out_json is None:
        cand = Path(f"FPGA_code/logs/virtual_gain_experiments/{tag}.json")
        if cand.exists():
            run_id = 2
            while True:
                cand_next = Path(f"FPGA_code/logs/virtual_gain_experiments/{tag}_run{run_id}.json")
                if not cand_next.exists():
                    cand = cand_next
                    break
                run_id += 1
        out_json = cand
    else:
        out_json = Path(out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)

    m33_share_pct = 100.0 / (d_line * w33)
    target_rel_pct = target_gain * m33_share_pct
    triad_burden_pct = max(0.0, target_rel_pct - m33_share_pct)

    print("=" * 78)
    print("INVERTED MAML MODE A: VIRTUAL GAIN EXPERIMENT [VIRTUAL_HARDWARE_EMULATION]")
    print(f"Hardware: PCB v1.3.2 (1k/3.3k Ohm) | SoC: {host}:{port} | Commit: {git_hash}")
    print(f"Condition: D_line={d_line}x, D_w33={w33}x, Target_Gain={target_gain:.2f}x, Clamp=+/-{clamp} LSB")
    print(f"Dynamics:  Primary M33={m33_share_pct:.1f}% | Target Demanded={target_rel_pct:.1f}% | Triad Burden={triad_burden_pct:.1f}%")
    print(f"Training:  K={k} ({k*strata} samples/ep) | LR={lr:.2f}x (Q16={lr_inner_q16}) | Epochs={epochs}")
    print(f"Regular.:  L2 decay -> W_null lambda={reg_q16/65536.0:.5f} (Q16={reg_q16}) | Window={t_min_us}-{t_max_us} us | Strata={strata}")
    print(f"Log File:  {out_json}")
    print("=" * 78)

    # 1. Apply Virtual Gain Configuration
    print("[*] Configuring Virtual Gain hardware registers...")
    telem = client.set_gain_experiment(d_line=d_line, w33=w33, target_gain=target_gain, clamp=clamp)
    time.sleep(0.05)

    # 2. Reset compensation weights to center (Clean Baseline) or Warm Start
    if not warm_start:
        print("[*] Centering baseline compensation weights...")
        client.center_compensation_weights()
        time.sleep(0.05)
    else:
        print("[*] WARM START: Preserving active converged weights from previous run!")

    # 3. Read initial settled baseline
    init_telem = client.poll_telemetry()
    init_loss = init_telem.mse_q14 * 10
    init_enob = init_telem.enob_bits
    init_rmse = np.sqrt(init_loss / 6.0) if init_loss > 0 else 0.0

    print(f"[*] Initial Baseline (Epoch 0): RMSE={init_rmse:.2f} LSB | ENOB={init_enob:.2f} b | Loss={init_loss} LSB^2")
    print(f"    Ref X: {init_telem.ref_x}")
    print(f"    Target Z: {init_telem.z_target}")
    print(f"    ADC49: {init_telem.adc49_sig}")

    epoch_records = []
    epoch_records.append({
        "epoch": 0,
        "loss_lsb2": float(init_loss),
        "rmse_lsb": float(init_rmse),
        "enob_bits": float(init_enob),
        "ref_x": list(init_telem.ref_x),
        "x_ref": list(init_telem.ref_x),
        "z_target": list(init_telem.z_target),
        "adc45": list(init_telem.adc45_sig),
        "adc49": list(init_telem.adc49_sig),
        "err49": [int(init_telem.z_target[i] - init_telem.adc49_sig[i]) for i in range(6)],
        "w_m3": init_telem.w_m3,
        "w_m8": init_telem.w_m8,
        "w_m33": init_telem.w_m33,
        "w8_diag": list(init_telem.w8_diag),
        "w3_diag": list(init_telem.w3_diag),
    })

    metadata = {
        "tag": tag,
        "date": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "provenance": {
            "pcb_version": "v1.3.2",
            "hardware_mods": "1k / 3.3k ohm summing attenuator (no ADC149)",
            "git_commit": git_hash,
            "soc_target": f"{host}:{port}",
            "mode": f"Mode {init_telem.mode} (Jumper {init_telem.jumper_mode})",
            "virtual_emulation": {
                "active": True,
                "d_line": d_line,
                "d_w33": w33,
                "target_gain": target_gain,
                "w_clamp": clamp,
                "m33_share_pct": m33_share_pct,
                "triad_burden_pct": triad_burden_pct,
                "note": "Virtual Attenuator Emulation on PCB v1.3.2"
            }
        },
        "training_params": {
            "k": k,
            "strata": strata,
            "t_min_us": t_min_us,
            "t_max_us": t_max_us,
            "lr": lr,
            "lr_inner_q16": lr_inner_q16,
            "reg_lambda": reg_q16 / 65536.0,
            "reg_lambda_q16": reg_q16,
            "epochs": epochs
        }
    }

    # Save initial stub
    with open(out_json, "w") as f:
        json.dump({"metadata": metadata, "records": epoch_records}, f, indent=2)

    t_start = time.time()
    print("-" * 78)
    print("Ep  # | Loss (LSB^2) | RMSE (LSB) | ENOB (bits) | ADC49 Sample (Col 0..5)")
    print("-" * 78)

    best_loss = init_loss
    best_enob = init_enob
    best_ep = 0

    for ep in range(1, epochs + 1):
        # Fresh arbitrary white-noise vector draw every epoch
        # Executed inside T120 maml_execute_strata_batch per vector
        raw_train = None
        for attempt in range(3):
            raw_train = client._send_binary(
                MAML_CMD_BATCH_STEP,
                struct.pack("<BBHHHH", k, strata, t_min_us, t_max_us, lr_inner_q16, reg_q16)
            )
            if raw_train and len(raw_train) >= 298:
                break
            time.sleep(0.02)

        is_telem_epoch = (ep % telem_stride == 0) or (ep == 1) or (ep == epochs)

        if not raw_train or len(raw_train) < 298:
            print(f"[!] Warning: UDP drop at epoch {ep}, retrying telemetry poll...")
            train_p = client.poll_telemetry()
            if train_p:
                ep_loss = train_p.mse_q14 * 10
                ep_enob = train_p.enob_bits
            else:
                ep_loss, ep_enob = 0, 0.0
        else:
            if is_telem_epoch:
                train_p = client._parse_hw_telemetry(raw_train)
                ep_loss = train_p.mse_q14 * 10
                ep_enob = train_p.enob_bits
            else:
                # Ultra-fast unpack from raw packet header at byte offset 42 (<IH)
                loss_milli, enob_centi = struct.unpack_from("<IH", raw_train, 42)
                ep_loss = (loss_milli // 10) * 10
                ep_enob = enob_centi / 100.0
                train_p = None

        ep_rmse = np.sqrt(ep_loss / 6.0) if ep_loss > 0 else 0.0

        if ep_loss < best_loss and ep_loss > 0:
            best_loss = ep_loss
            best_enob = ep_enob
            best_ep = ep

        # 1/100 Telemetry Logging & Disk Write
        if is_telem_epoch:
            if train_p is None:
                train_p = client._parse_hw_telemetry(raw_train)

            print(
                f"{ep:5d} | {ep_loss:12d} | {ep_rmse:10.2f} | {ep_enob:9.2f} b | {train_p.adc49_sig}",
                flush=True
            )

            epoch_records.append({
                "epoch": ep,
                "loss_lsb2": float(ep_loss),
                "rmse_lsb": float(ep_rmse),
                "enob_bits": float(ep_enob),
                "ref_x": list(train_p.ref_x),
                "x_ref": list(train_p.ref_x),
                "z_target": list(train_p.z_target),
                "adc45": list(train_p.adc45_sig),
                "adc49": list(train_p.adc49_sig),
                "err49": [int(train_p.z_target[i] - train_p.adc49_sig[i]) for i in range(6)],
                "w_m3": train_p.w_m3,
                "w_m8": train_p.w_m8,
                "w_m33": train_p.w_m33,
                "w8_diag": list(train_p.w8_diag),
                "w3_diag": list(train_p.w3_diag),
            })

            # Incremental save only on telemetry epochs (saves 99% of disk I/O)
            with open(out_json, "w") as f:
                json.dump({
                    "metadata": metadata,
                    "summary": {
                        "epochs_completed": ep,
                        "best_epoch": best_ep,
                        "best_loss": float(best_loss),
                        "best_enob": float(best_enob),
                    },
                    "records": epoch_records
                }, f, indent=2)

    t_elapsed = time.time() - t_start
    print("-" * 78)
    print(f"EXPERIMENT FINISHED in {t_elapsed:.1f} s ({t_elapsed/60:.1f} min)")

    # Compute Statistical Metrics (OLS linear regression slope & trend)
    losses = np.array([r["loss_lsb2"] for r in epoch_records[1:]])
    eps = np.arange(1, len(losses) + 1)
    if len(losses) >= 10:
        slope, intercept = np.polyfit(eps, losses, 1)
        r_matrix = np.corrcoef(eps, losses)
        r_squared = float(r_matrix[0, 1] ** 2) if not np.isnan(r_matrix[0, 1]) else 0.0
        q1_loss = float(np.mean(losses[: len(losses) // 4]))
        q4_loss = float(np.mean(losses[3 * len(losses) // 4 :]))
        trend_pct = float(((q4_loss - q1_loss) / q1_loss) * 100.0) if q1_loss > 0 else 0.0
    else:
        slope, r_squared, q1_loss, q4_loss, trend_pct = 0.0, 0.0, 0.0, 0.0, 0.0

    verdict = "CONVERGING (STATISTICAL DESCENT)" if slope < -1.0 and trend_pct < -3.0 else "STATISTICALLY FLAT"
    print(f" Verdict:      {verdict}")
    print(f" Slope beta1:  {slope:+.3f} LSB^2/epoch (R^2 = {r_squared:.4f})")
    print(f" Q1 -> Q4 Loss:{q1_loss:.1f} -> {q4_loss:.1f} LSB^2 (Net Trend: {trend_pct:+.1f}%)")
    print(f" Best Epoch:   #{best_ep} (Loss: {best_loss} LSB^2, ENOB: {best_enob:.2f} bits)")
    print("=" * 78)

    final_results = {
        "metadata": metadata,
        "summary": {
            "duration_s": round(t_elapsed, 2),
            "epochs_completed": epochs,
            "verdict": verdict,
            "slope_beta1": float(slope),
            "r_squared": float(r_squared),
            "q1_loss_mean": float(q1_loss),
            "q4_loss_mean": float(q4_loss),
            "trend_pct": float(trend_pct),
            "best_epoch": int(best_ep),
            "best_loss": float(best_loss),
            "best_enob": float(best_enob),
        },
        "records": epoch_records
    }

    with open(out_json, "w") as f:
        json.dump(final_results, f, indent=2)

    return final_results


def main():
    parser = argparse.ArgumentParser(description="Run Virtual Gain Mode A Experiment on Physical Silicon")
    parser.add_argument("--d-line", type=int, default=2, help="Data line divider (default: 2)")
    parser.add_argument("--w33", type=int, default=2, help="Matrix 33 divider (default: 2)")
    parser.add_argument("--target-gain", type=float, default=4.0, help="Digital target demand gain (default: 4.0)")
    parser.add_argument("--clamp", type=int, default=120, help="Compensation weight clamp in LSB (default: 120)")
    parser.add_argument("--k", type=int, default=20, help="Batch size K vectors (default: 20)")
    parser.add_argument("--lr", type=float, default=0.03, help="Learning rate multiplier (default: 0.03)")
    parser.add_argument("--reg", type=float, default=0.0,
                        help="L2 weight-decay lambda toward centered W_null per epoch (default: 0.0 = off, max 0.25)")
    parser.add_argument("--epochs", type=int, default=200, help="Number of training epochs (default: 200)")
    parser.add_argument("--strata", type=int, default=10, help="Number of strata slots (default: 10)")
    parser.add_argument("--t-min", type=int, default=4900, help="Min plateau delay in us (default: 4900)")
    parser.add_argument("--t-max", type=int, default=5100, help="Max plateau delay in us (default: 5100)")
    parser.add_argument("--stride", type=int, default=100, help="Telemetry stride in epochs (default: 100)")
    parser.add_argument("--host", default="192.168.1.50", help="T120 SoC IP")
    parser.add_argument("--port", type=int, default=5000, help="T120 SoC UDP port")
    parser.add_argument("--out", type=str, default=None, help="Output JSON path")
    args = parser.parse_args()

    out_p = Path(args.out) if args.out else None
    run_single_condition(
        d_line=args.d_line,
        w33=args.w33,
        target_gain=args.target_gain,
        clamp=args.clamp,
        k=args.k,
        lr=args.lr,
        epochs=args.epochs,
        strata=args.strata,
        t_min_us=args.t_min,
        t_max_us=args.t_max,
        telem_stride=args.stride,
        host=args.host,
        port=args.port,
        out_json=out_p,
        reg_lambda=args.reg,
    )


if __name__ == "__main__":
    main()

