#!/home/olle/anaconda3/bin/python
"""
10-Minute Silicon Mode C Neural Network Training & Live Convergence Engine
==========================================================================
Runs local on-chip gradient descent in Trion T120 RISC-V SoC for 10 minutes (600s).
Mode: Mode C (Sigmoid Bypass, jumper_mode = 2)
Schedule: Lugn learning rate / step size (inner_loop_n = 10, seed_pct = 14%).
Logs live on-the-fly telemetry every 1.0s and saves real-time progress.
"""

from __future__ import annotations
import sys
import os
import time
import json
import struct
from pathlib import Path
import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))
SKILL_DIR = REPO_ROOT / ".agents" / "skills" / "data-log-quota"
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))

from gui.udp_client import (
    MamlUdpClient,
    MAML_CMD_GET_TELEMETRY,
)
from check_quota import enforce_quota_before_write

DOCS_DIR = REPO_ROOT / "FPGA_code" / "docs"
FIG_DIR = DOCS_DIR / "figures"
DOCS_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)

PROGRESS_FILE = DOCS_DIR / "live_10min_training_progress.json"
RESULTS_FILE = DOCS_DIR / "maml_10min_mode_c_results.json"


class TenMinuteModeCTrainer:
    def __init__(self, host: str = "192.168.1.50", port: int = 5000, target_time_us: int = 3000):
        self.host = host
        self.port = port
        self.target_time_us = target_time_us
        self.client = MamlUdpClient(host=host, port=port, timeout=1.5)
        self.client.set_heaters(False, [0, 0, 0, 0])
        self.banner = self._verify_connection()
        print(f"[+] Connected to Hardware: {self.banner}")
        print(f"    Target Time Slice: t0 = {self.target_time_us} us")
        print("    Mode: MODE C (Sigmoid Bypass, jumper_mode = 2)")
        print("    Schedule: Lugn LR (inner_loop_n = 10, seed_pct = 14%)")

    def _verify_connection(self) -> str:
        version = self.client.query_version()
        if "MAML" not in version:
            raise RuntimeError(f"Unexpected response from hardware: {version}")
        return version.strip()

    def get_telemetry_raw(self) -> dict:
        raw = None
        for retry in range(3):
            raw = self.client._send_binary(MAML_CMD_GET_TELEMETRY)
            if raw is not None and len(raw) >= self.client.TELEM_SIZE:
                break
            time.sleep(0.05)
        if raw is None or len(raw) < self.client.TELEM_SIZE:
            raise RuntimeError("Failed to receive telemetry from hardware!")

        u = struct.unpack(self.client.TELEM_FMT, raw[:self.client.TELEM_SIZE])
        loss = u[29]
        rmse = (loss / 6.0) ** 0.5
        enob_comp = u[30] / 100.0
        enob_uncomp = u[31] / 100.0
        x_ref = list(u[32:38])
        z_target = list(u[38:44])
        adc45 = list(u[44:50])
        adc49 = list(u[50:56])
        err49 = [z - a for z, a in zip(z_target, adc49)]

        return {
            "mode": u[2],
            "epoch": u[24],
            "inner_step": u[23],
            "loss": loss,
            "rmse": rmse,
            "enob_comp": enob_comp,
            "enob_uncomp": enob_uncomp,
            "x_ref": x_ref,
            "z_target": z_target,
            "adc45": adc45,
            "adc49": adc49,
            "err49": err49,
            "timestamp": time.time(),
        }

    def measure_uncompensated_baseline(self, num_samples: int = 15) -> dict:
        print(f"\n[*] Phase 1: Measuring Uncompensated Baseline across {num_samples} patterns at t0={self.target_time_us} us...")
        self.client.center_compensation_weights()
        time.sleep(0.05)

        self.client.set_config(
            mode=0, # IDLE
            jumper_mode=2, # Mode C
            led_switches=0,
            max_meas_win_pct=25,
            hadamard_khz=500,
            inner_loop_n=10,
            seed_pct=14,
            seed_mode=1,
            w_hid_mag=0,
            trim_hid_mag=0,
            hadamard_delay_us=self.target_time_us,
        )

        samples = []
        for i in range(num_samples):
            time.sleep(0.12)
            telem = self.get_telemetry_raw()
            samples.append(telem)

        rmses = [s["rmse"] for s in samples]
        enobs = [s["enob_uncomp"] for s in samples]
        col_errors = np.array([s["err49"] for s in samples])
        mean_col_rmse = np.sqrt(np.mean(col_errors ** 2, axis=0))

        mean_rmse = float(np.mean(rmses))
        mean_enob = float(np.mean(enobs))
        print(f"    [+] Baseline Uncompensated: Mean RMSE = {mean_rmse:.1f} LSB, Mean ENOB = {mean_enob:.2f} bits")
        print(f"        Per-column RMSE (C1..C6): {[round(x, 1) for x in mean_col_rmse.tolist()]} LSB")

        return {
            "num_samples": num_samples,
            "mean_rmse": mean_rmse,
            "mean_enob": mean_enob,
            "col_rmses": mean_col_rmse.tolist(),
            "samples": samples,
        }

    def run_10min_training(self, duration_sec: float = 600.0, poll_sec: float = 1.0) -> dict:
        print(f"\n[*] Phase 2: Starting 10-Minute Silicon Training in Mode C (duration={duration_sec:.0f}s)...")
        print("    - T120 Clock Rate: 100 Hz Native Refresh (~60,000 silicon iterations)")
        print(f"    - On-The-Fly Polling: Every {poll_sec:.1f}s")
        print(f"    - Live Progress saved to: {PROGRESS_FILE.name}")

        # Seed compensation weights gently (14% swing) so dx8 backpropagates sensitivity to M3
        self.client.seed_weights(seed_mode=1, swing_pct=14)
        time.sleep(0.05)

        # Start autonomous on-chip training in Mode C
        self.client.set_config(
            mode=1, # BASE_TRAIN (Local Autonomous C Execution)
            jumper_mode=2, # Mode C: JUMPER_BYPASS_SIG2
            led_switches=0,
            max_meas_win_pct=25,
            hadamard_khz=500,
            inner_loop_n=10, # Lugn schedule: 10 steps per vector
            seed_pct=14, # 14% swing for gentle start
            seed_mode=1,
            w_hid_mag=0, # SKIPS outer MAML resets!
            trim_hid_mag=0,
            hadamard_delay_us=self.target_time_us,
        )

        t_start = time.time()
        trajectory = []
        time_hist = []
        rmse_hist = []
        enob_hist = []
        last_print = 0.0

        try:
            while (time.time() - t_start) < duration_sec:
                time.sleep(poll_sec)
                telem = self.get_telemetry_raw()
                elapsed = time.time() - t_start
                telem["elapsed_sec"] = elapsed
                trajectory.append(telem)

                time_hist.append(round(elapsed, 1))
                rmse_hist.append(round(telem["rmse"], 1))
                enob_hist.append(round(telem["enob_comp"], 2))

                # Format per-column errors
                errs = [round(e, 0) for e in telem["err49"]]

                # Print on-the-fly loss to stdout every ~2 seconds (or every poll)
                if (elapsed - last_print) >= 2.0 or len(trajectory) == 1:
                    last_print = elapsed
                    print(f"  [t={elapsed:5.1f}s | Epok {telem['epoch']:3d}] "
                          f"Loss={telem['loss']:7d} | RMSE={telem['rmse']:5.1f} LSB | "
                          f"Comp ENOB={telem['enob_comp']:4.2f} bits | "
                          f"Col Err: {errs}")

                # Save live progress to disk on every poll so the GUI curve is unbroken from t=0
                live_data = {
                    "mode_name": "Mode C (Sigmoid Bypass)",
                    "elapsed_sec": elapsed,
                    "duration_sec": duration_sec,
                    "progress_pct": (elapsed / duration_sec) * 100.0,
                    "latest_epoch": telem["epoch"],
                    "latest_loss": telem["loss"],
                    "latest_rmse": telem["rmse"],
                    "latest_enob_comp": telem["enob_comp"],
                    "num_checkpoints": len(trajectory),
                    "full_history": {
                        "time": time_hist,
                        "rmse": rmse_hist,
                        "enob": enob_hist,
                    },
                    "trajectory_tail": trajectory[-10:],
                }
                with open(PROGRESS_FILE, "w") as pf:
                    json.dump(live_data, pf, indent=2)

        finally:
            # Stop training, freeze learned weights in IDLE mode
            self.client.set_config(
                mode=0, # IDLE
                jumper_mode=2,
                led_switches=0,
                max_meas_win_pct=25,
                hadamard_khz=500,
                inner_loop_n=10,
                seed_pct=14,
                seed_mode=1,
                w_hid_mag=0,
                trim_hid_mag=0,
                hadamard_delay_us=self.target_time_us,
            )
            print(f"[+] Training stopped. Completed {len(trajectory)} live checkpoints.")

        return {"trajectory": trajectory, "total_time": time.time() - t_start}

    def measure_compensated_performance(self, num_samples: int = 20) -> dict:
        print(f"\n[*] Phase 3: Evaluating Trained Compensated Performance across {num_samples} patterns in Mode C...")
        samples = []
        for i in range(num_samples):
            time.sleep(0.12)
            telem = self.get_telemetry_raw()
            samples.append(telem)

        rmses = [s["rmse"] for s in samples]
        enobs = [s["enob_comp"] for s in samples]
        col_errors = np.array([s["err49"] for s in samples])
        mean_col_rmse = np.sqrt(np.mean(col_errors ** 2, axis=0))

        mean_rmse = float(np.mean(rmses))
        mean_enob = float(np.mean(enobs))
        print(f"    [+] Trained Compensated (Mode C): Mean RMSE = {mean_rmse:.1f} LSB, Mean ENOB = {mean_enob:.2f} bits")
        print(f"        Per-column RMSE (C1..C6): {[round(x, 1) for x in mean_col_rmse.tolist()]} LSB")

        return {
            "num_samples": num_samples,
            "mean_rmse": mean_rmse,
            "mean_enob": mean_enob,
            "col_rmses": mean_col_rmse.tolist(),
            "samples": samples,
        }


def plot_10min_convergence(baseline: dict, training: dict, compensated: dict, fig_dir: Path = FIG_DIR) -> tuple[Path, Path]:
    traj = training["trajectory"]
    t_sec = np.array([p["elapsed_sec"] for p in traj])
    rmse = np.array([p["rmse"] for p in traj])
    enob = np.array([p["enob_comp"] for p in traj])
    base_rmse = baseline["mean_rmse"]
    base_enob = baseline["mean_enob"]

    # Running moving average over 15 points (~15s)
    window = min(15, len(rmse))
    if window > 1:
        rmse_smooth = np.convolve(rmse, np.ones(window)/window, mode='same')
        enob_smooth = np.convolve(enob, np.ones(window)/window, mode='same')
    else:
        rmse_smooth = rmse
        enob_smooth = enob

    # Figure 1: 10-Minute Convergence
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6.5), sharex=True)
    fig.patch.set_facecolor("#FFFFFF")

    # Top: RMSE
    ax1.plot(t_sec, rmse, color="#EF4444", alpha=0.35, linewidth=0.8, label="Instantaneous Silicon Loss (RMSE)")
    ax1.plot(t_sec, rmse_smooth, color="#B91C1C", linewidth=2.2, label=f"Moving Average ({window}s window)")
    ax1.axhline(base_rmse, color="#1E293B", linestyle="--", linewidth=1.8, label=f"Uncompensated Baseline ({base_rmse:.1f} LSB)")
    ax1.set_ylabel("Hardware Output RMSE (12-bit LSB)", fontsize=10, fontweight="bold")
    ax1.set_title("10-Minute Autonomous Silicon Neural Network Training in Mode C (Trion T120 Platform)\n100% Real Physical Hardware Telemetry over UDP", fontsize=11, fontweight="bold")
    ax1.grid(True, linestyle=":", alpha=0.6)
    ax1.legend(loc="upper right", frameon=True, fontsize=8.5)

    # Bottom: ENOB
    ax2.plot(t_sec, enob, color="#10B981", alpha=0.35, linewidth=0.8, label="Instantaneous ENOB (bits)")
    ax2.plot(t_sec, enob_smooth, color="#047857", linewidth=2.2, label=f"Moving Average ({window}s window)")
    ax2.axhline(base_enob, color="#1E293B", linestyle="--", linewidth=1.8, label=f"Uncompensated Baseline ({base_enob:.2f} bits)")
    ax2.set_xlabel("Elapsed Training Time (seconds)", fontsize=10, fontweight="bold")
    ax2.set_ylabel("Effective Bit Precision (ENOB)", fontsize=10, fontweight="bold")
    ax2.grid(True, linestyle=":", alpha=0.6)
    ax2.legend(loc="lower right", frameon=True, fontsize=8.5)

    plt.tight_layout()
    p1 = fig_dir / "fig_10min_mode_c_convergence.png"
    plt.savefig(p1, dpi=300)
    plt.close(fig)

    # Figure 2: Column Error Reduction
    fig, ax = plt.subplots(figsize=(8.5, 4.5))
    fig.patch.set_facecolor("#FFFFFF")
    cols = [f"Col {i+1}" for i in range(6)]
    x = np.arange(len(cols))
    w = 0.35

    ax.bar(x - w/2, baseline["col_rmses"], width=w, label=f"Uncompensated Baseline ({baseline['mean_rmse']:.1f} LSB)", color="#F97316", alpha=0.85)
    ax.bar(x + w/2, compensated["col_rmses"], width=w, label=f"10-Min Trained Mode C ({compensated['mean_rmse']:.1f} LSB)", color="#10B981", alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels(cols, fontweight="bold")
    ax.set_ylabel("Output RMSE (ADC LSB)", fontweight="bold")
    ax.set_title("Column-by-Column Error Reduction after 10-Minute Mode C Training", fontweight="bold")
    ax.grid(True, linestyle=":", alpha=0.6, axis="y")
    ax.legend(loc="upper right", frameon=True)

    for i in range(len(cols)):
        b = baseline["col_rmses"][i]
        c = compensated["col_rmses"][i]
        ax.text(i - w/2, b + 25, f"{int(b)}", ha="center", fontsize=8)
        ax.text(i + w/2, c + 25, f"{int(c)}", ha="center", fontsize=8, fontweight="bold")

    plt.tight_layout()
    p2 = fig_dir / "fig_10min_mode_c_column_reduction.png"
    plt.savefig(p2, dpi=300)
    plt.close(fig)

    return p1, p2


def main():
    print("=" * 70)
    print(" 10-MINUTE SILICON NEURAL NETWORK TRAINING & CONVERGENCE SYSTEM")
    print(" 100% Real Physical Hardware Telemetry (Trion T120 + T20)")
    print(" Mode C: Sigmoid Bypass (JUMPER_BYPASS_SIG2)")
    print("=" * 70)

    enforce_quota_before_write(incoming_bytes=2_000_000, max_mb=100.0, auto_prune=True, docs_dir=DOCS_DIR)

    trainer = TenMinuteModeCTrainer(host="192.168.1.50", port=5000, target_time_us=3000)

    try:
        # Phase 1: Baseline
        baseline_res = trainer.measure_uncompensated_baseline(num_samples=15)

        # Phase 2: 10-Minute Training
        training_res = trainer.run_10min_training(duration_sec=600.0, poll_sec=1.0)

        # Phase 3: Compensated Evaluation
        compensated_res = trainer.measure_compensated_performance(num_samples=20)

    finally:
        trainer.client.set_heaters(False, [0, 0, 0, 0])
        print("[+] Verified Heater Safety: All Heaters DISARMED.")

    # Generate Figures
    p1, p2 = plot_10min_convergence(baseline_res, training_res, compensated_res, fig_dir=FIG_DIR)
    print(f"[+] Generated Convergence Figures:\n    {p1}\n    {p2}")

    # Copy to artifacts
    art_dir = Path("/home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a")
    if art_dir.exists():
        import shutil
        shutil.copy(p1, art_dir / p1.name)
        shutil.copy(p2, art_dir / p2.name)

    # Save results json
    results_summary = {
        "metadata": {
            "timestamp": time.time(),
            "target_time_us": 3000,
            "mode": "Mode C (Sigmoid Bypass)",
            "duration_sec": 600.0,
            "training_checkpoints": len(training_res["trajectory"]),
        },
        "baseline_uncompensated": baseline_res,
        "compensated_trained": compensated_res,
        "training_trajectory": training_res["trajectory"],
    }
    with open(RESULTS_FILE, "w") as rf:
        json.dump(results_summary, rf, indent=2)
    print(f"[+] Saved structured results to: {RESULTS_FILE}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

