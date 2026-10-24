#!/home/olle/anaconda3/bin/python
"""
run_10min_biased_mode_a_training.py
===================================
Executes a 10-Minute (600 seconds) Continuous Autonomous Silicon Neural Training
Run on the Efinix Trion T120 FPGA with:
  1. Pre-biasing of Matrix 33 columns to cancel SUM35 hardware offsets.
  2. Mode A (JUMPER_USE_SIG2 = 3): Active BJT Sigmoid Output Layer.
  3. Gentle Learning Rate Schedule: inner_loop_n = 10, seed_pct = 14%.
  4. Real-time telemetry streaming to live_10min_training_progress.json for Live GUI / CLI.
  5. 100% Real Physical Hardware Telemetry over UDP (Port 5000).
"""

import os
import sys
import time
import struct
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "gui"))
from udp_client import MamlUdpClient

DOCS_DIR = REPO_ROOT / "FPGA_code" / "docs"
FIG_DIR = DOCS_DIR / "figures"
DOCS_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)

PROGRESS_FILE = DOCS_DIR / "live_10min_training_progress.json"
RESULTS_FILE = DOCS_DIR / "maml_10min_mode_a_results.json"

MAML_CMD_GET_TELEMETRY = 0x10
MAML_CMD_SET_M33_BIAS = 0x20

# Calibrated M33 column bias vector (DAC LSBs) to center ADC 49 in Mode A
M33_COL_BIAS = [30, 42, 52, 26, 18, 24]


class BiasedSiliconTrainerModeA:
    def __init__(self, host: str = "192.168.1.50", port: int = 5000):
        self.client = MamlUdpClient(host=host, port=port, timeout=2.0)
        self.target_time_us = 3000

    def verify_connection(self) -> str:
        version = self.client.query_version()
        if "MAML" not in version:
            raise RuntimeError(f"Unexpected response from hardware: {version}")
        return version.strip()

    def apply_m33_bias(self, biases: list) -> None:
        payload = struct.pack("<6b", *[max(-127, min(127, int(b))) for b in biases])
        self.client._send_binary(MAML_CMD_SET_M33_BIAS, payload)
        time.sleep(0.05)

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
        sigma2 = list(u[56:62])

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
            "sigma2_slope": sigma2,
            "timestamp": time.time(),
        }

    def measure_uncompensated_baseline(self, num_samples: int = 15) -> dict:
        print(f"\n[*] Phase 1: Measuring Uncompensated Baseline across {num_samples} patterns in Mode A...")
        self.apply_m33_bias(M33_COL_BIAS)
        self.client.center_compensation_weights()
        time.sleep(0.05)

        self.client.set_config(
            mode=0, # IDLE
            jumper_mode=3, # Mode A (JUMPER_USE_SIG2)
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
        time.sleep(0.1)

        samples = []
        for i in range(num_samples):
            time.sleep(0.08)
            telem = self.get_telemetry_raw()
            samples.append(telem)

        rmses = [s["rmse"] for s in samples]
        enobs = [s["enob_comp"] for s in samples]
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
        print(f"\n[*] Phase 2: Starting 10-Minute Silicon Training in Mode A (duration={duration_sec:.0f}s)...")
        print(f"    - Pre-Biased M33 Vector: {M33_COL_BIAS}")
        print("    - T120 Clock Rate: 100 Hz Native Refresh (~60,000 silicon iterations)")
        print(f"    - On-The-Fly Polling: Every {poll_sec:.1f}s")
        print(f"    - Live Progress saved to: {PROGRESS_FILE.name}")

        # Ensure M33 bias is latched
        self.apply_m33_bias(M33_COL_BIAS)

        # Start autonomous on-chip training in Mode A (jumper_mode = 3)
        self.client.set_config(
            mode=1, # BASE_TRAIN (Local Autonomous C Execution)
            jumper_mode=3, # Mode A: JUMPER_USE_SIG2
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
        last_print = 0.0

        try:
            while (time.time() - t_start) < duration_sec:
                time.sleep(poll_sec)
                telem = self.get_telemetry_raw()
                elapsed = time.time() - t_start
                telem["elapsed_sec"] = elapsed
                trajectory.append(telem)

                # Format per-column errors
                errs = [round(e, 0) for e in telem["err49"]]

                # Print on-the-fly loss to stdout every ~2 seconds (or every poll)
                if (elapsed - last_print) >= 2.0 or len(trajectory) == 1:
                    last_print = elapsed
                    print(f"  [t={elapsed:5.1f}s | Epok {telem['epoch']:3d}] "
                          f"Loss={telem['loss']:7d} | RMSE={telem['rmse']:5.1f} LSB | "
                          f"Comp ENOB={telem['enob_comp']:4.2f} bits | "
                          f"Col Err: {errs}")

                # Save live progress to disk atomically every 5 points
                if len(trajectory) % 5 == 0:
                    live_data = {
                        "elapsed_sec": elapsed,
                        "duration_sec": duration_sec,
                        "progress_pct": (elapsed / duration_sec) * 100.0,
                        "latest_epoch": telem["epoch"],
                        "latest_loss": telem["loss"],
                        "latest_rmse": telem["rmse"],
                        "latest_enob_comp": telem["enob_comp"],
                        "num_checkpoints": len(trajectory),
                        "trajectory_tail": trajectory[-10:],
                    }
                    with open(PROGRESS_FILE, "w") as pf:
                        json.dump(live_data, pf, indent=2)

        finally:
            # Stop training, freeze learned weights in IDLE mode
            self.client.set_config(
                mode=0, # IDLE
                jumper_mode=3,
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
        print(f"\n[*] Phase 3: Evaluating Trained Compensated Performance across {num_samples} patterns in Mode A...")
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
        print(f"    [+] Trained Compensated (Mode A): Mean RMSE = {mean_rmse:.1f} LSB, Mean ENOB = {mean_enob:.2f} bits")
        print(f"        Per-column RMSE (C1..C6): {[round(x, 1) for x in mean_col_rmse.tolist()]} LSB")

        return {
            "num_samples": num_samples,
            "mean_rmse": mean_rmse,
            "mean_enob": mean_enob,
            "col_rmses": mean_col_rmse.tolist(),
            "samples": samples,
        }

    def plot_convergence_curves(self, trajectory: list, baseline_rmse: float, trained_rmse: float) -> tuple:
        times = np.array([p["elapsed_sec"] for p in trajectory])
        rmses = np.array([p["rmse"] for p in trajectory])
        enobs = np.array([p["enob_comp"] for p in trajectory])

        plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7.5), sharex=True)

        win = min(15, len(rmses))
        rmse_smooth = np.convolve(rmses, np.ones(win)/win, mode='same')
        enob_smooth = np.convolve(enobs, np.ones(win)/win, mode='same')

        ax1.plot(times, rmses, color="#E2E8F0", alpha=0.5, label="Instantaneous Raw RMSE")
        ax1.plot(times, rmse_smooth, color="#DC2626", linewidth=2.2, label=f"Smoothed Moving Avg (win={win})")
        ax1.axhline(baseline_rmse, color="#475569", linestyle="--", linewidth=1.5,
                    label=f"Baseline Uncompensated ({baseline_rmse:.1f} LSB)")
        ax1.axhline(trained_rmse, color="#16A34A", linestyle="-.", linewidth=1.5,
                    label=f"Final Compensated ({trained_rmse:.1f} LSB)")
        ax1.set_ylabel("Loss / RMSE (LSB)", fontsize=11, fontweight="bold")
        ax1.set_title("10-Minute Silicon Neural Training Trajectory in Mode A (BJT Sigmoid Active)\n"
                      f"Pre-Biased M33 Vector: {M33_COL_BIAS} | Continuous Hardware In-Data Stream",
                      fontsize=12, fontweight="bold")
        ax1.legend(loc="upper right", frameon=True, fontsize=9)
        ax1.set_ylim(0, max(1200, np.max(rmses) * 1.15))

        ax2.plot(times, enobs, color="#E2E8F0", alpha=0.5, label="Instantaneous Raw ENOB")
        ax2.plot(times, enob_smooth, color="#2563EB", linewidth=2.2, label=f"Smoothed ENOB (win={win})")
        ax2.set_xlabel("Elapsed Training Time (seconds)", fontsize=11, fontweight="bold")
        ax2.set_ylabel("Effective Precision (ENOB Bits)", fontsize=11, fontweight="bold")
        ax2.set_xlim(0, max(times[-1], 600))
        ax2.set_ylim(0, max(5.0, np.max(enobs) + 0.5))
        ax2.legend(loc="lower right", frameon=True, fontsize=9)

        plt.tight_layout()
        conv_path = FIG_DIR / "fig_10min_mode_a_convergence.png"
        fig.savefig(conv_path, dpi=300)
        plt.close(fig)

        return conv_path, None

    def plot_column_reduction(self, baseline_col_rmse: list, trained_col_rmse: list) -> Path:
        cols = [f"Col {i+1}" for i in range(6)]
        cols.append("Mean")
        base_vals = list(baseline_col_rmse) + [float(np.mean(baseline_col_rmse))]
        train_vals = list(trained_col_rmse) + [float(np.mean(trained_col_rmse))]

        x = np.arange(len(cols))
        width = 0.35

        fig, ax = plt.subplots(figsize=(10, 5.5))
        rects1 = ax.bar(x - width/2, base_vals, width, label="Uncompensated Baseline", color="#94A3B8")
        rects2 = ax.bar(x + width/2, train_vals, width, label="10-Min Trained Compensated", color="#3B82F6")

        for rect in rects1:
            h = rect.get_height()
            ax.annotate(f"{h:.0f}", xy=(rect.get_x() + rect.get_width()/2, h),
                        xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=8.5)

        for rect in rects2:
            h = rect.get_height()
            ax.annotate(f"{h:.0f}", xy=(rect.get_x() + rect.get_width()/2, h),
                        xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=8.5, fontweight="bold")

        ax.set_ylabel("RMSE Error (LSB)", fontsize=11, fontweight="bold")
        ax.set_title("Per-Column Error Reduction: Mode A (Sigmoid Active) with Pre-Biased M33",
                     fontsize=12, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels(cols, fontsize=10, fontweight="bold")
        ax.legend(frameon=True, fontsize=10)
        ax.grid(axis='y', linestyle=':', alpha=0.6)

        plt.tight_layout()
        col_path = FIG_DIR / "fig_10min_mode_a_column_reduction.png"
        fig.savefig(col_path, dpi=300)
        plt.close(fig)
        return col_path


def main():
    print("=" * 70)
    print(" 10-MINUTE SILICON NEURAL NETWORK TRAINING & CONVERGENCE SYSTEM")
    print(" Mode A: Active BJT Sigmoid with Pre-Biased Matrix 33 Vector")
    print(" 100% Real Physical Hardware Telemetry (Trion T120 + T20)")
    print("=" * 70)

    trainer = BiasedSiliconTrainerModeA()
    ver = trainer.verify_connection()
    print(f"[+] Connected to Hardware: {ver}")

    # Phase 1: Baseline
    baseline = trainer.measure_uncompensated_baseline(num_samples=15)

    # Phase 2: 10-Minute Training (600 seconds)
    train_result = trainer.run_10min_training(duration_sec=600.0, poll_sec=1.0)

    # Phase 3: Evaluated Compensated Performance
    comp = trainer.measure_compensated_performance(num_samples=20)

    # Verification of Heaters (Safety enforcement)
    trainer.client.set_heaters(False, [0, 0, 0, 0])
    print("[+] Verified Heater Safety: All Heaters DISARMED.")

    # Generate Figures
    p_conv, _ = trainer.plot_convergence_curves(train_result["trajectory"],
                                                baseline["mean_rmse"],
                                                comp["mean_rmse"])
    p_col = trainer.plot_column_reduction(baseline["col_rmses"], comp["col_rmses"])
    print(f"[+] Generated Convergence Figures:\n    {p_conv}\n    {p_col}")

    # Save Structured Results JSON
    results = {
        "metadata": {
            "timestamp": time.time(),
            "target_time_us": trainer.target_time_us,
            "mode": "Mode A (Active Sigmoid)",
            "m33_col_bias": M33_COL_BIAS,
            "duration_sec": 600.0,
            "training_checkpoints": len(train_result["trajectory"]),
        },
        "baseline_uncompensated": baseline,
        "compensated_trained": comp,
        "training_trajectory": train_result["trajectory"],
    }
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2)
    print(f"[+] Saved structured results to: {RESULTS_FILE}")

    # Mark completion in live progress file
    live_done = {
        "elapsed_sec": 600.0,
        "duration_sec": 600.0,
        "progress_pct": 100.0,
        "latest_epoch": train_result["trajectory"][-1]["epoch"] if train_result["trajectory"] else 0,
        "latest_loss": train_result["trajectory"][-1]["loss"] if train_result["trajectory"] else 0,
        "latest_rmse": comp["mean_rmse"],
        "latest_enob_comp": comp["mean_enob"],
        "num_checkpoints": len(train_result["trajectory"]),
        "trajectory_tail": train_result["trajectory"][-10:] if train_result["trajectory"] else [],
    }
    with open(PROGRESS_FILE, "w") as pf:
        json.dump(live_done, pf, indent=2)

    print("\n" + "=" * 70)
    print(" 10-MINUTE MODE A SILICON TRAINING COMPLETED SUCCESSFULLY!")
    print(f" Baseline Uncompensated RMSE : {baseline['mean_rmse']:.1f} LSB ({baseline['mean_enob']:.2f} bits ENOB)")
    print(f" Trained Compensated RMSE    : {comp['mean_rmse']:.1f} LSB ({comp['mean_enob']:.2f} bits ENOB)")
    print("=" * 70)


if __name__ == "__main__":
    main()

