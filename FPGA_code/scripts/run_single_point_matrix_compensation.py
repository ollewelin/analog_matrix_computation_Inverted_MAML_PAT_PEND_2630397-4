#!/home/olle/anaconda3/bin/python
"""
Full-Matrix Neural Network Compensation & Bit Precision Evaluator
================================================================
Evaluates Inverted MAML Inner-Loop Neural Compensation at a single,
deterministic time point (t0 = 3000 µs / 3.0 ms) within the 10 ms cycle.
All training, sensitivity extraction, and weight adaptation run 100% locally
inside the T120 RISC-V Master SoC.

Policy: 100% Real Physical Hardware Telemetry (Strict Anti-Simulation Enforcement).
"""

from __future__ import annotations
import sys
import os
import time
import json
import csv
import struct
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
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
    MAT_M3,
    MAT_M8,
    MAT_M33,
    MAML_CMD_GET_TELEMETRY,
    MAML_CMD_SET_CONFIG,
    MAML_CMD_CENTER_COMP,
)
from check_quota import enforce_quota_before_write, get_quota_status

DOCS_DIR = REPO_ROOT / "FPGA_code" / "docs"
FIG_DIR = DOCS_DIR / "figures"
DOCS_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)


class SinglePointMatrixCompensationRunner:
    def __init__(self, host: str = "192.168.1.50", port: int = 5000, target_time_us: int = 3000):
        self.host = host
        self.port = port
        self.target_time_us = target_time_us
        self.client = MamlUdpClient(host=host, port=port, timeout=1.5)
        # Enforce heater safety
        self.client.set_heaters(False, [0, 0, 0, 0])
        self.banner = self._verify_connection()
        print(f"[+] Connected to Hardware: {self.banner}")
        print(f"    Evaluation Time Slice: t0 = {self.target_time_us} us ({self.target_time_us/1000.0:.1f} ms after refresh)")

    def _verify_connection(self) -> str:
        version = self.client.query_version()
        if "MAML" not in version:
            raise RuntimeError(f"Unexpected response: {version}")
        return version

    def get_telemetry_raw(self) -> Dict[str, Any]:
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

        # Errors per column
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

    def measure_uncompensated_baseline(self, num_samples: int = 15) -> Dict[str, Any]:
        """Centers compensation weights and samples uncompensated matrix error at t0."""
        print(f"\n[*] Phase 1: Measuring Uncompensated Baseline (W_comp = 0) across {num_samples} patterns at t0={self.target_time_us} us...")
        self.client.center_compensation_weights()
        time.sleep(0.05)

        # Set IDLE with delay
        self.client.set_config(
            mode=0,
            jumper_mode=1, # JUMPER_OFF_NO_COMP
            led_switches=0,
            max_meas_win_pct=25,
            hadamard_khz=500,
            inner_loop_n=20,
            seed_pct=28,
            seed_mode=1,
            w_hid_mag=0,
            trim_hid_mag=0,
            hadamard_delay_us=self.target_time_us,
        )

        samples = []
        for i in range(num_samples):
            # Probe single cell or refresh to cycle
            time.sleep(0.12) # wait for refresh tick
            telem = self.get_telemetry_raw()
            samples.append(telem)

        rmses = [s["rmse"] for s in samples]
        enobs = [s["enob_uncomp"] for s in samples]
        col_errors = np.array([s["err49"] for s in samples]) # shape (N, 6)
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

    def run_local_t120_inner_training(self, train_duration_sec: float = 12.0, jumper_mode: int = 2) -> Dict[str, Any]:
        """
        Commands the T120 RISC-V SoC to execute local inner-loop neural network training.
        All gradient descent and Hadamard sensitivities execute in T120 C firmware.
        """
        mode_str = "JUMPER_BYPASS_SIG2 (Mode C: Sigmoid Bypass)" if jumper_mode == 2 else "JUMPER_USE_SIG2 (Mode A: Sigmoid Active)"
        print(f"\n[*] Phase 2: Starting Local T120 Inner-Loop Training for {train_duration_sec:.1f} seconds...")
        print("    Configuration:")
        print("      - Run Mode: MAML_MODE_BASE_TRAIN (Local Autonomous C Execution)")
        print("      - Outer MAML: SKIPPED (w_hid_mag = 0, no resets)")
        print("      - Strata: num_strata_m = 1 (Fixed Single Time-Point)")
        print(f"      - Target Time Slice: t0 = {self.target_time_us} us")
        print(f"      - Analog Jumper: {mode_str}")
        print("      - Reduced Step Schedule: inner_loop_n = 10, seed_pct = 14% (Lower Learning Steps)")

        self.client.set_config(
            mode=1, # BASE_TRAIN
            jumper_mode=jumper_mode, # 2 for Mode C (Bypass Sigmoid)
            led_switches=0,
            max_meas_win_pct=25,
            hadamard_khz=500,
            inner_loop_n=10,
            seed_pct=14,
            seed_mode=1,
            w_hid_mag=0, # SKIPS outer MAML!
            trim_hid_mag=0,
            hadamard_delay_us=self.target_time_us,
        )

        t_start = time.time()
        trajectory = []
        poll_interval = 0.25 # poll every 250 ms (25 T120 cycles)

        while (time.time() - t_start) < train_duration_sec:
            time.sleep(poll_interval)
            telem = self.get_telemetry_raw()
            telem["elapsed_sec"] = time.time() - t_start
            trajectory.append(telem)
            print(f"    T120 Epoch {telem['epoch']:2d} (t={telem['elapsed_sec']:4.1f}s): "
                  f"Loss={telem['loss']:7d}, RMSE={telem['rmse']:5.1f} LSB, "
                  f"Comp ENOB={telem['enob_comp']:4.2f} bits (Uncomp={telem['enob_uncomp']:4.2f})")

        # Stop training, place into IDLE but KEEP LEARNED WEIGHTS active
        self.client.set_config(
            mode=0, # IDLE
            jumper_mode=jumper_mode,
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
        print(f"[+] Completed {len(trajectory)} telemetry telemetry checkpoints.")
        return {"trajectory": trajectory, "total_time": time.time() - t_start}

    def measure_compensated_performance(self, num_samples: int = 15) -> Dict[str, Any]:
        """Measures full-matrix computation precision with trained compensation weights active."""
        print(f"\n[*] Phase 3: Evaluating Trained Compensated Performance across {num_samples} patterns at t0={self.target_time_us} us...")
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
        print(f"    [+] Trained Compensated: Mean RMSE = {mean_rmse:.1f} LSB, Mean ENOB = {mean_enob:.2f} bits")
        print(f"        Per-column RMSE (C1..C6): {[round(x, 1) for x in mean_col_rmse.tolist()]} LSB")

        return {
            "num_samples": num_samples,
            "mean_rmse": mean_rmse,
            "mean_enob": mean_enob,
            "col_rmses": mean_col_rmse.tolist(),
            "samples": samples,
        }


def generate_experiment_figures(
    baseline: Dict[str, Any],
    training: Dict[str, Any],
    compensated: Dict[str, Any],
    fig_dir: Path = FIG_DIR,
) -> Tuple[Path, Path]:
    print("\n[*] Generating Figures for Olle's Evening Report...")

    # Figure 7: Training Convergence Curve (Loss and ENOB vs Time/Steps)
    traj = training["trajectory"]
    t_sec = [pt["elapsed_sec"] for pt in traj]
    loss_vals = [pt["loss"] for pt in traj]
    rmse_vals = [pt["rmse"] for pt in traj]
    comp_enobs = [pt["enob_comp"] for pt in traj]
    uncomp_enobs = [pt["enob_uncomp"] for pt in traj]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))

    # Loss curve
    ax1.plot(t_sec, rmse_vals, "r-o", linewidth=1.5, markersize=4, label="Compensated Hardware RMSE")
    ax1.axhline(baseline["mean_rmse"], color="k", linestyle="--", alpha=0.7, label=f"Uncompensated Baseline ({baseline['mean_rmse']:.1f} LSB)")
    ax1.set_title("Full-Matrix RMSE Loss Convergence (T120 Local Training)\n(Sampled at Fixed t0 = 3.0 ms Plateau)", fontsize=9, fontweight="bold")
    ax1.set_xlabel("Elapsed Training Time (s) [~100 steps/s]", fontsize=8)
    ax1.set_ylabel("Hardware Output RMSE (12-bit ADC LSB)", fontsize=8)
    ax1.grid(True, linestyle="--", alpha=0.6)
    ax1.legend(fontsize=8)

    # ENOB curve
    ax2.plot(t_sec, comp_enobs, "g-s", linewidth=1.5, markersize=4, label="Trained Compensated ENOB")
    ax2.axhline(baseline["mean_enob"], color="k", linestyle="--", alpha=0.7, label=f"Uncompensated Baseline ({baseline['mean_enob']:.2f} bits)")
    ax2.set_title("Effective Bit Precision (ENOB) Improvement\n(Inverted MAML Inner-Loop on Real Silicon)", fontsize=9, fontweight="bold")
    ax2.set_xlabel("Elapsed Training Time (s)", fontsize=8)
    ax2.set_ylabel("Effective Number of Bits (ENOB)", fontsize=8)
    ax2.grid(True, linestyle="--", alpha=0.6)
    ax2.legend(fontsize=8)

    plt.tight_layout()
    p1 = fig_dir / "fig7_inner_loop_training_convergence.png"
    plt.savefig(p1, dpi=300)
    plt.close()

    # Figure 8: Column-by-Column Error Reduction
    cols = [f"Col {c+1}" for c in range(6)]
    uncomp_c = baseline["col_rmses"]
    comp_c = compensated["col_rmses"]

    fig, ax = plt.subplots(figsize=(8, 4.2))
    x_pos = np.arange(6)
    w = 0.35
    b1 = ax.bar(x_pos - w/2, uncomp_c, width=w, color="#d95f02", alpha=0.85, label=f"Uncompensated (Mean = {baseline['mean_rmse']:.1f} LSB)")
    b2 = ax.bar(x_pos + w/2, comp_c, width=w, color="#2ca02c", alpha=0.85, label=f"Compensated (Mean = {compensated['mean_rmse']:.1f} LSB)")

    ax.set_xticks(x_pos)
    ax.set_xticklabels(cols, fontsize=8)
    ax.set_ylabel("Column Output RMSE (ADC LSB)", fontsize=8)
    ax.set_title("Full-Matrix Column Error Reduction via Local Neural Compensation\n(Worst-Case MCP6024 Baseline at Fixed t0 = 3.0 ms)", fontsize=9, fontweight="bold")
    ax.grid(True, axis="y", linestyle="--", alpha=0.6)
    ax.legend(fontsize=8)

    for bar in b1:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2.0, h + 8, f"{h:.0f}", ha="center", va="bottom", fontsize=7, color="#d95f02", fontweight="bold")
    for bar in b2:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2.0, h + 8, f"{h:.0f}", ha="center", va="bottom", fontsize=7, color="#2ca02c", fontweight="bold")

    plt.tight_layout()
    p2 = fig_dir / "fig8_column_error_reduction.png"
    plt.savefig(p2, dpi=300)
    plt.close()

    print(f"[+] Generated Figures:\n    {p1}\n    {p2}")
    return p1, p2


def main() -> int:
    print("=" * 70)
    print(" INVERTED MAML SINGLE-POINT FULL-MATRIX COMPENSATION SYSTEM")
    print(" 100% Physical Silicon Measurements (Trion T120 + T20 Hardware)")
    print("=" * 70)

    # Check quota
    enforce_quota_before_write(incoming_bytes=5_000_000, max_mb=100.0, auto_prune=True, docs_dir=DOCS_DIR)

    runner = SinglePointMatrixCompensationRunner(host="192.168.1.50", port=5000, target_time_us=3000)

    try:
        # 1. Uncompensated Baseline
        baseline_results = runner.measure_uncompensated_baseline(num_samples=15)

        # 2. Local T120 Inner-Loop Training in Mode C (Bypass Sigmoid, Reduced Step Schedule)
        training_results = runner.run_local_t120_inner_training(train_duration_sec=12.0, jumper_mode=2)

        # 3. Compensated Evaluation
        compensated_results = runner.measure_compensated_performance(num_samples=15)

    finally:
        # Safety enforcement
        runner.client.set_heaters(False, [0, 0, 0, 0])
        print("[+] Verified Heater Safety: All Heaters DISARMED.")

    # Generate Figures
    p1, p2 = generate_experiment_figures(baseline_results, training_results, compensated_results, fig_dir=FIG_DIR)

    # Copy to artifact directory
    artifact_dir = Path("/home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a")
    if artifact_dir.exists():
        import shutil
        shutil.copy(p1, artifact_dir / p1.name)
        shutil.copy(p2, artifact_dir / p2.name)
        print(f"[+] Copied figures to artifact directory: {artifact_dir}")

    # Summary Data Export
    summary_data = {
        "metadata": {
            "title": "Single-Point Full-Matrix Neural Network Compensation Experiment",
            "timestamp": datetime.now().isoformat(),
            "sample_point_us": runner.target_time_us,
            "sample_point_ms": runner.target_time_us / 1000.0,
            "training_architecture": "Inner-Loop Neural Network (M3 -> Sigmoid -> M8) running locally in T120 RISC-V SoC",
            "anti_simulation_enforcement": "100% Real Physical Hardware Telemetry",
        },
        "baseline_uncompensated": {
            "mean_rmse_lsb": baseline_results["mean_rmse"],
            "mean_enob_bits": baseline_results["mean_enob"],
            "col_rmses_lsb": baseline_results["col_rmses"],
        },
        "compensated_trained": {
            "mean_rmse_lsb": compensated_results["mean_rmse"],
            "mean_enob_bits": compensated_results["mean_enob"],
            "col_rmses_lsb": compensated_results["col_rmses"],
            "rmse_reduction_ratio": baseline_results["mean_rmse"] / (compensated_results["mean_rmse"] + 1e-6),
            "enob_gain_bits": compensated_results["mean_enob"] - baseline_results["mean_enob"],
        },
        "training_trajectory": training_results["trajectory"],
    }

    json_path = DOCS_DIR / "maml_inner_loop_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)
    print(f"[+] Saved structured results to: {json_path}")

    # Final Quota check
    status = get_quota_status(max_mb=100.0, docs_dir=DOCS_DIR)
    print(f"[+] Data Log Quota Status: {status['usage_mb']:.2f} MB / 100 MB ({status['usage_pct']:.1f}%)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
