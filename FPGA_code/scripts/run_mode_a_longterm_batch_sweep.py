#!/home/olle/anaconda3/bin/python
"""
Inverted MAML Mode A Long-Term Batch & Learning Rate Statistical Sweep Engine
=============================================================================
Orchestrates continuous multi-hour hardware characterization up to 17:00:
  - Sweeps Mini-Batch size K in [4 .. 25] and Learning Rate in [0.02 .. 0.25]
  - Runs >= 200 epochs per condition on physical Efinix Trion T120 SoC (192.168.1.50:5000)
  - Evaluates true generalization error on 4 unseen holdout vectors per epoch
  - Computes rigorous statistical metrics across the full 200-epoch trajectory:
      1. Linear Regression Slope (beta_1 in LSB^2/epoch) and R^2
      2. Quartile 1 (Ep 1..50) vs Quartile 4 (Ep 151..200) Loss Reduction (%)
      3. Statistical Verdict: CONVERGING vs FLAT/NOISE vs DIVERGING
      4. Weight Stability & Topographical Correlation (r_M3, r_M8)
  - Automatically writes cumulative registry and updates hourly status report
"""

from __future__ import annotations
import argparse
import json
import math
import os
import struct
import sys
import time
from datetime import datetime
from pathlib import Path
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from gui.udp_client import (
    MamlUdpClient,
    MAML_CMD_GET_TELEMETRY,
    MAML_CMD_STEP_OUTER,
    MAML_CMD_RAND_DATA,
    MAML_CMD_BATCH_STEP,
)
from FPGA_code.scripts.run_mode_a_multi_vector_batch import (
    parse_telemetry_packet,
    get_averaged_telemetry,
    draw_fresh_vector,
)

LOG_DIR = REPO_ROOT / "FPGA_code" / "logs" / "mode_a_longterm_sweep"
LOG_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR = REPO_ROOT / "FPGA_code" / "docs"
DOCS_DIR.mkdir(parents=True, exist_ok=True)

REGISTRY_FILE = LOG_DIR / "sweep_summary_registry.json"
STATUS_MD_FILE = DOCS_DIR / "MODE_A_LONGTERM_SWEEP_STATUS.md"

# Initial Sweep Plan (prioritizing user instruction: start with K=8 and lower LR, test K=4..25)
DEFAULT_SWEEP_PLAN = [
    # 1. K=8 Lower LR Exploration (User Priority)
    {"k": 8, "lr": 0.05, "epochs": 200, "note": "K=8 Low LR baseline"},
    {"k": 8, "lr": 0.08, "epochs": 200, "note": "K=8 Mid-Low LR"},
    {"k": 8, "lr": 0.10, "epochs": 200, "note": "K=8 Standard Low LR"},
    {"k": 8, "lr": 0.03, "epochs": 200, "note": "K=8 Ultra-Low LR"},

    # 2. K=12 Medium-High Batch Exploration
    {"k": 12, "lr": 0.05, "epochs": 200, "note": "K=12 Low LR"},
    {"k": 12, "lr": 0.08, "epochs": 200, "note": "K=12 Mid-Low LR"},
    {"k": 12, "lr": 0.10, "epochs": 200, "note": "K=12 Standard Low LR"},

    # 3. K=16 High Batch Exploration
    {"k": 16, "lr": 0.05, "epochs": 200, "note": "K=16 Low LR"},
    {"k": 16, "lr": 0.08, "epochs": 200, "note": "K=16 Mid-Low LR"},

    # 4. K=20 High Batch Exploration (User Priority)
    {"k": 20, "lr": 0.03, "epochs": 200, "note": "K=20 Ultra-Low LR"},
    {"k": 20, "lr": 0.05, "epochs": 200, "note": "K=20 Low LR"},
    {"k": 20, "lr": 0.08, "epochs": 200, "note": "K=20 Mid-Low LR"},
    {"k": 20, "lr": 0.10, "epochs": 200, "note": "K=20 Standard Low LR"},

    # 5. K=25 Maximum Batch Exploration (User Priority)
    {"k": 25, "lr": 0.03, "epochs": 200, "note": "K=25 Ultra-Low LR"},
    {"k": 25, "lr": 0.05, "epochs": 200, "note": "K=25 Low LR"},
    {"k": 25, "lr": 0.08, "epochs": 200, "note": "K=25 Mid-Low LR"},

    # 6. K=4 Lower Batch Controls
    {"k": 4, "lr": 0.05, "epochs": 200, "note": "K=4 Low LR control"},
    {"k": 4, "lr": 0.10, "epochs": 200, "note": "K=4 Mid LR control"},
    {"k": 4, "lr": 0.20, "epochs": 200, "note": "K=4 High LR control"},

    # 7. Higher LR Controls for K=8
    {"k": 8, "lr": 0.15, "epochs": 200, "note": "K=8 Higher LR control"},
    {"k": 8, "lr": 0.20, "epochs": 200, "note": "K=8 High LR control"},
]


STRATA_US = [4900, 4950, 5000, 5050, 5100]  # 4.9 ms to 5.1 ms multi-strata window


def compute_statistical_trajectory(epoch_records: list[dict]) -> dict:
    """Compute linear regression slope, quartile comparisons, and statistical convergence verdict."""
    epochs = np.array([r["epoch"] for r in epoch_records[1:]], dtype=np.float64)
    val_losses = np.array([r["loss_lsb2"] for r in epoch_records[1:]], dtype=np.float64)
    val_rmses = np.array([r["rmse_lsb"] for r in epoch_records[1:]], dtype=np.float64)
    val_enobs = np.array([r["enob_bits"] for r in epoch_records[1:]], dtype=np.float64)

    n = len(epochs)
    if n < 10:
        return {"verdict": "INSUFFICIENT_DATA"}

    # 1. Linear regression of Validation Loss vs Epoch (y = beta_1 * x + beta_0)
    p = np.polyfit(epochs, val_losses, 1)
    slope_loss = float(p[0])  # LSB^2 per epoch
    intercept_loss = float(p[1])
    fitted = slope_loss * epochs + intercept_loss
    ss_tot = float(np.sum((val_losses - np.mean(val_losses)) ** 2))
    ss_res = float(np.sum((val_losses - fitted) ** 2))
    r_squared = float(1.0 - (ss_res / ss_tot)) if ss_tot > 1e-6 else 0.0

    # 2. Quartile comparisons
    q1_idx = max(1, n // 4)
    q4_idx = max(q1_idx + 1, n - (n // 4))

    q1_loss_mean = float(np.mean(val_losses[:q1_idx]))
    q4_loss_mean = float(np.mean(val_losses[q4_idx:]))
    q1_rmse_mean = float(np.mean(val_rmses[:q1_idx]))
    q4_rmse_mean = float(np.mean(val_rmses[q4_idx:]))
    q1_enob_mean = float(np.mean(val_enobs[:q1_idx]))
    q4_enob_mean = float(np.mean(val_enobs[q4_idx:]))

    trend_pct = float(((q4_loss_mean - q1_loss_mean) / q1_loss_mean) * 100.0) if q1_loss_mean > 1e-6 else 0.0
    loss_volatility = float(np.std(val_losses))

    # 3. Statistical Convergence Verdict
    # If loss significantly decreases over the full 200 epochs: CONVERGING
    # If loss change is within +/- 5%: STATISTICALLY FLAT (PURE NOISE)
    # If loss increases > +5%: DIVERGING
    if slope_loss < -5.0 and trend_pct < -5.0:
        verdict = "CONVERGING (STATISTICAL DESCENT)"
    elif trend_pct > 7.0 or slope_loss > 5.0:
        verdict = "DIVERGING / INSTABILITY"
    else:
        verdict = "STATISTICALLY FLAT (PURE NOISE FLOOR)"

    best_idx = int(np.argmin(val_rmses))
    best_rmse = float(val_rmses[best_idx])
    best_enob = float(val_enobs[best_idx])
    best_epoch = int(epochs[best_idx])

    return {
        "verdict": verdict,
        "slope_loss_per_epoch": round(slope_loss, 3),
        "r_squared": round(r_squared, 4),
        "q1_loss_mean": round(q1_loss_mean, 1),
        "q4_loss_mean": round(q4_loss_mean, 1),
        "trend_pct": round(trend_pct, 2),
        "loss_volatility": round(loss_volatility, 1),
        "q1_rmse_mean": round(q1_rmse_mean, 2),
        "q4_rmse_mean": round(q4_rmse_mean, 2),
        "q1_enob_mean": round(q1_enob_mean, 2),
        "q4_enob_mean": round(q4_enob_mean, 2),
        "best_epoch": best_epoch,
        "best_val_rmse": round(best_rmse, 2),
        "best_val_enob": round(best_enob, 2),
        "final_val_rmse": round(float(val_rmses[-1]), 2),
        "final_val_enob": round(float(val_enobs[-1]), 2),
    }


def update_status_markdown(registry: list[dict]):
    """Update publication-ready live markdown summary document."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# Inverted MAML Mode A: Long-Term Batch & Learning Rate Statistical Sweep",
        "",
        f"**Last Updated:** {now_str}  ",
        "**Target Platform:** Efinix Trion T120F324 Master SoC (`192.168.1.50:5000`)  ",
        "**Operating Mode:** Mode A (Active 2-Layer Triad via Sigmoid 10, Jumper Mode 3)  ",
        "**Hardware Summing Attenuator:** $1\\text{ k}\\Omega / 3.9\\text{ k}\\Omega$ ($20.4\\%$ authority, baseline before $15\\text{ k}\\Omega$ rework)  ",
        f"**Completed Conditions:** {len(registry)} experiments  ",
        "",
        "---",
        "",
        "## 1. Executive Statistical Ranking (Convergence vs Flat vs Divergent)",
        "",
        "| Rank | Batch Size $K$ | LR Scale | Epochs | Slope ($\\beta_1$) | $\\Delta Q_1 \\to Q_4$ | Q4 ENOB | Peak ENOB | Statistical Verdict |",
        "|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|",
    ]

    # Sort registry by trend_pct ascending (best loss reduction first)
    sorted_reg = sorted(registry, key=lambda x: x.get("stats", {}).get("trend_pct", 999.0))
    for rank, item in enumerate(sorted_reg, 1):
        st = item.get("stats", {})
        k = item.get("k", "-")
        lr = item.get("lr", 0.0)
        ep = item.get("epochs", 0)
        slope = st.get("slope_loss_per_epoch", 0.0)
        trend = st.get("trend_pct", 0.0)
        q4_enob = st.get("q4_enob_mean", 0.0)
        pk_enob = st.get("best_val_enob", 0.0)
        verdict = st.get("verdict", "N/A")
        trend_str = f"{trend:+.1f}%"
        slope_str = f"{slope:+.2f}"
        lines.append(f"| {rank} | K={k} | {lr:.2f}x | {ep} | `{slope_str}` | **{trend_str}** | {q4_enob:.2f} b | {pk_enob:.2f} b | {verdict} |")

    lines.extend([
        "",
        "---",
        "",
        "## 2. Detailed Condition Summaries & Weight Topographies",
        "",
    ])

    for item in registry:
        st = item.get("stats", {})
        k = item.get("k")
        lr = item.get("lr")
        ep = item.get("epochs")
        name = item.get("tag")
        m8 = item.get("final_w8_diag", [])
        m3 = item.get("final_w3_diag", [])
        r3 = item.get("r_m3", 1.0)
        duration = item.get("duration_s", 0.0)

        lines.extend([
            f"### Condition: K={k}, LR={lr:.2f}x ({ep} epochs)",
            f"- **Dataset File:** [`{name}.json`](../logs/mode_a_longterm_sweep/{name}.json)",
            f"- **Execution Time:** {duration:.1f} s ({duration/60:.1f} min)",
            f"- **Statistical Verdict:** **{st.get('verdict')}**",
            f"- **Loss Trajectory Slope:** `{st.get('slope_loss_per_epoch'):+.3f} LSB^2/epoch` ($R^2 = {st.get('r_squared')}$)",
            f"- **Quartile 1 Mean Loss:** `{st.get('q1_loss_mean')} LSB^2` ({st.get('q1_enob_mean')} bits) $\\to$ **Quartile 4 Mean Loss:** `{st.get('q4_loss_mean')} LSB^2` ({st.get('q4_enob_mean')} bits)",
            f"- **Net Long-Term Trend:** `{st.get('trend_pct'):+.2f}%`",
            f"- **Final Weights:** M8 Diag = `{m8}`, M3 Diag = `{m3}` ($r_{{M3}} = {r3:.4f}$)",
            "",
        ])

    with open(STATUS_MD_FILE, "w") as f:
        f.write("\n".join(lines) + "\n")


def run_single_condition(
    client: MamlUdpClient,
    k: int,
    lr: float,
    epochs: int = 200,
    tag: str = "condition",
    note: str = "",
) -> dict:
    print("\n" + "=" * 78)
    print(f"RUNNING CONDITION: K={k} | LR={lr:.2f}x | Epochs={epochs} | Note: {note}")
    print("=" * 78)

    lr_inner_q16 = max(32, min(4096, int(round(1024 * lr))))
    t0 = time.time()

    # 1. Initialize Mode A centered baseline
    client.set_config(
        mode=0, jumper_mode=3, led_switches=3, max_meas_win_pct=100, hadamard_khz=500,
        inner_loop_n=100, seed_pct=28, seed_mode=1, w_hid_mag=0, trim_hid_mag=0,
        hadamard_delay_us=5000,
        lr_inner_q16=lr_inner_q16,
    )
    time.sleep(0.04)
    client.center_compensation_weights()
    time.sleep(0.04)

    # 2. Extract baseline telemetry
    draw_fresh_vector(client, settle_s=0.03)
    init_telem = get_averaged_telemetry(client, n_avg=4)
    w_m33_static = init_telem["w_m33"]
    w_m3_start = init_telem["w_m3"]
    w_m8_start = init_telem["w_m8"]

    epoch_records = []
    # Epoch 0 Baseline
    epoch_records.append({
        "epoch": 0,
        "phase": "BASELINE",
        "batch_k": k,
        "time_s": 0.0,
        "rmse_lsb": init_telem["rmse_lsb"],
        "enob_bits": init_telem["enob_bits"],
        "loss_lsb2": init_telem["loss_lsb2"],
        "train_rmse_mean": init_telem["rmse_lsb"],
        "val_rmse": init_telem["rmse_lsb"],
        "val_enob": init_telem["enob_bits"],
        "x_ref": init_telem["x_ref"],
        "z_target": init_telem["z_target"],
        "adc45": init_telem["adc45"],
        "adc49": init_telem["adc49"],
        "err49": init_telem["err49"],
        "w_m3": w_m3_start,
        "w_m8": w_m8_start,
        "w8_diag": [w_m8_start[i][i] for i in range(6)],
        "w3_diag": [w_m3_start[i][i] for i in range(6)],
        "r_m3": 1.0,
        "r_m8": 1.0,
    })

    w3_flat_0 = np.array(w_m3_start)[:6, :6].flatten()
    w8_flat_0 = np.array(w_m8_start)[:6, :6].flatten()

    for ep in range(1, epochs + 1):
        batch_rmses = []
        batch_losses = []
        last_train_p = None

        # A. True Multi-Strata Batch Gradient Step (Total Samples = M * k)
        # Keeps each vector locked across all 10 strata (4.9..5.1 ms), accumulates
        # all 10*k samples, and performs ONE single weight update on physical silicon!
        raw_train = client._send_binary(
            MAML_CMD_BATCH_STEP,
            struct.pack("<BBHHH", k, 10, 4900, 5100, lr_inner_q16)
        )
        if raw_train and len(raw_train) >= client.TELEM_SIZE:
            train_p = parse_telemetry_packet(raw_train, client)
            train_loss = train_p["loss_lsb2"]
            train_rmse = train_p["rmse_lsb"]
            train_enob = train_p["enob_bits"]
            last_train_p = train_p
        else:
            train_loss, train_rmse, train_enob = 0.0, 0.0, 0.0

        # B. Multi-Strata Unseen Holdout Validation (Arbitrary vectors across [4.9..5.1] ms)
        val_rmses = []
        val_losses = []
        last_val_telem = None
        for t_val in STRATA_US:
            client.set_config(
                mode=0, jumper_mode=3, led_switches=3, max_meas_win_pct=100, hadamard_khz=500,
                inner_loop_n=100, seed_pct=28, seed_mode=1, w_hid_mag=0, trim_hid_mag=0,
                hadamard_delay_us=t_val,
                lr_inner_q16=lr_inner_q16,
            )
            # Draw fresh independent arbitrary validation vector
            draw_fresh_vector(client, settle_s=0.010)
            raw = client._send_binary(MAML_CMD_GET_TELEMETRY)
            if raw and len(raw) >= client.TELEM_SIZE:
                p_v = parse_telemetry_packet(raw, client)
                val_rmses.append(p_v["rmse_lsb"])
                val_losses.append(p_v["loss_lsb2"])
                if t_val == 5000:
                    last_val_telem = p_v

        val_rmse = round(float(np.mean(val_rmses)), 2) if val_rmses else 0.0
        val_loss = round(float(np.mean(val_losses)), 1) if val_losses else 0.0
        val_enob = round(max(0.0, 11.0 - math.log2(max(val_rmse, 1.0))), 2)
        val_telem = last_val_telem if last_val_telem is not None else last_train_p

        w_m3_cur = val_telem["w_m3"]
        w_m8_cur = val_telem["w_m8"]
        w8_diag = val_telem["w8_diag"]
        w3_diag = val_telem["w3_diag"]

        w3_flat_cur = np.array(w_m3_cur)[:6, :6].flatten()
        w8_flat_cur = np.array(w_m8_cur)[:6, :6].flatten()
        r3 = float(np.corrcoef(w3_flat_0, w3_flat_cur)[0, 1]) if np.std(w3_flat_cur) > 1e-6 else 1.0
        r8 = float(np.corrcoef(w8_flat_0, w8_flat_cur)[0, 1]) if np.std(w8_flat_cur) > 1e-6 else 1.0

        rec = {
            "epoch": ep,
            "phase": "TRAINING",
            "batch_k": k,
            "time_s": round(time.time() - t0, 2),
            "rmse_lsb": val_rmse,
            "enob_bits": val_enob,
            "loss_lsb2": val_loss,
            "train_rmse_mean": train_rmse,
            "train_loss_mean": train_loss,
            "train_enob": train_enob,
            "val_rmse": val_rmse,
            "val_enob": val_enob,
            "x_ref": val_telem["x_ref"],
            "z_target": val_telem["z_target"],
            "adc45": val_telem["adc45"],
            "adc49": val_telem["adc49"],
            "err49": val_telem["err49"],
            "w_m3": w_m3_cur,
            "w_m8": w_m8_cur,
            "w8_diag": w8_diag,
            "w3_diag": w3_diag,
            "r_m3": round(r3, 4),
            "r_m8": round(r8, 4),
        }
        epoch_records.append(rec)

        if ep % 10 == 0 or ep == 1 or ep == epochs:
            diag_str = str([int(w) for w in w8_diag])
            print(f"Ep {ep:3d}/{epochs} | Train {train_rmse:5.2f} LSB | Val {val_rmse:5.2f} LSB ({val_enob:4.2f} b) | M8: {diag_str} | r_M3={r3:+.4f}", flush=True)

    duration = time.time() - t0
    stats = compute_statistical_trajectory(epoch_records)

    print(f"\n[+] Condition Completed in {duration:.1f} s ({duration/60:.1f} min)", flush=True)
    print(f"[*] Statistical Verdict: {stats.get('verdict')}", flush=True)
    print(f"[*] Slope beta_1: {stats.get('slope_loss_per_epoch'):+.3f} LSB^2/ep (R^2 = {stats.get('r_squared')})", flush=True)
    print(f"[*] Q1 Loss: {stats.get('q1_loss_mean')} -> Q4 Loss: {stats.get('q4_loss_mean')} (Trend: {stats.get('trend_pct'):+.1f}%)", flush=True)
    print(f"[*] Q4 Mean ENOB: {stats.get('q4_enob_mean')} bits | Peak ENOB: {stats.get('best_val_enob')} bits (Ep {stats.get('best_epoch')})", flush=True)

    # Save detailed telemetry dataset
    dataset_file = LOG_DIR / f"{tag}.json"
    dataset = {
        "metadata": {
            "title": f"Inverted MAML Long-Term Batch Sweep: {tag}",
            "date": datetime.now().isoformat(),
            "target": "192.168.1.50:5000",
            "k": k,
            "lr": lr,
            "lr_inner_q16": lr_inner_q16,
            "epochs": epochs,
            "duration_s": round(duration, 2),
            "note": note,
            "statistics": stats,
        },
        "static_weights": {"w_m33": w_m33_static},
        "epochs": epoch_records,
    }
    with open(dataset_file, "w") as f:
        json.dump(dataset, f, indent=2)

    return {
        "tag": tag,
        "k": k,
        "lr": lr,
        "lr_inner_q16": lr_inner_q16,
        "epochs": epochs,
        "duration_s": round(duration, 2),
        "note": note,
        "stats": stats,
        "final_w8_diag": epoch_records[-1]["w8_diag"],
        "final_w3_diag": epoch_records[-1]["w3_diag"],
        "r_m3": epoch_records[-1]["r_m3"],
        "r_m8": epoch_records[-1]["r_m8"],
    }


def main():
    parser = argparse.ArgumentParser(description="Long-Term Mode A Statistical Sweep Orchestrator")
    parser.add_argument("--host", type=str, default="192.168.1.50")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--max-runs", type=int, default=100, help="Max conditions to execute")
    parser.add_argument("--until-hour", type=int, default=17, help="Stop after this 24h clock hour (default: 17 = 17:00)")
    args = parser.parse_args()

    print("=" * 78)
    print("INVERTED MAML MODE A LONG-TERM BATCH & LR SWEEP ORCHESTRATOR")
    print(f"Target: {args.host}:{args.port} | Run until: {args.until_hour:02d}:00")
    print(f"Log Directory: {LOG_DIR}")
    print(f"Status Document: {STATUS_MD_FILE}")
    print("=" * 78)

    client = MamlUdpClient(host=args.host, port=args.port, timeout=6.0)

    # Load existing registry if present
    registry = []
    if REGISTRY_FILE.exists():
        try:
            with open(REGISTRY_FILE, "r") as f:
                registry = json.load(f)
            print(f"[*] Loaded existing registry with {len(registry)} completed conditions.")
        except Exception:
            registry = []

    plan = list(DEFAULT_SWEEP_PLAN)
    runs_done = 0

    for item in plan:
        now = datetime.now()
        if now.hour >= args.until_hour and now.minute >= 0:
            print(f"\n[!] Reached scheduled cutoff time ({args.until_hour:02d}:00). Stopping sweep gracefully.")
            break

        k = item["k"]
        lr = item["lr"]
        ep = item["epochs"]
        note = item.get("note", "")
        lr_tag = f"lr{int(round(lr * 100)):02d}p"
        tag = f"true_batch_k{k}_{lr_tag}_{ep}ep"

        # Check if already executed
        if any(r.get("tag") == tag for r in registry):
            print(f"[*] Skipping already completed condition: {tag}")
            continue

        res = run_single_condition(client, k=k, lr=lr, epochs=ep, tag=tag, note=note)
        registry.append(res)
        runs_done += 1

        # Save cumulative registry
        with open(REGISTRY_FILE, "w") as f:
            json.dump(registry, f, indent=2)

        # Update markdown status document
        update_status_markdown(registry)

        if runs_done >= args.max_runs:
            print(f"[*] Reached max runs limit ({args.max_runs}). Finished.")
            break

        # Brief 1s pause between conditions for thermal and DAC baseline stability
        time.sleep(1.0)

    print("\n" + "=" * 78)
    print(f"[SUCCESS] Sweep Orchestrator completed {runs_done} conditions.")
    print(f"Final registry: {REGISTRY_FILE}")
    print(f"Live Markdown Report: {STATUS_MD_FILE}")
    print("=" * 78)


if __name__ == "__main__":
    main()
