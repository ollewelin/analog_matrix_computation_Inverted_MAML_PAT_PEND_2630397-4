#!/usr/bin/env python3
"""
run_autonomous_day_campaign.py: Autonomous Multi-Condition Silicon Runner Until 17:00
Inverted MAML Mode A Virtual Gain Campaign [VIRTUAL_HARDWARE_EMULATION]
Hardware: Efinix Trion T120 Master SoC (`192.168.1.50:5000`)
"""

import sys
import json
import time
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from FPGA_code.scripts.run_virtual_gain_experiment import run_single_condition

CAMPAIGN_CONDITIONS = [
    # Nominal_1_1_4000ep_k4: Full Swing 1/1 (D_line=1x, W33=1x, Gain=1.0x, K=4, LR=0.05x, 4000 ep)
    {"d_line": 1, "w33": 1, "target_gain": 1.0, "clamp": 120, "k": 4, "lr": 0.05, "epochs": 4000},
    # Nominal_1_1_10000ep_k4: Full Swing 1/1 (D_line=1x, W33=1x, Gain=1.0x, K=4, LR=0.05x, 10000 ep)
    {"d_line": 1, "w33": 1, "target_gain": 1.0, "clamp": 120, "k": 4, "lr": 0.05, "epochs": 10000},
    # G1_4000ep_k4: Olle's Primary Proposal (1/4 M33, 4x Target Demand => 75% Triad Burden, K=4, 4000 ep)
    {"d_line": 2, "w33": 2, "target_gain": 4.0, "clamp": 120, "k": 4, "lr": 0.05, "epochs": 4000},
    # G2_4000ep_k4: 50/50 Balance (1/4 M33, 2x Target Demand => 25% Triad Burden, K=4, 4000 ep)
    {"d_line": 2, "w33": 2, "target_gain": 2.0, "clamp": 120, "k": 4, "lr": 0.05, "epochs": 4000},
    # G4_4000ep_k4: Data 1/2 with K=4, LR=0.05x (4000 ep)
    {"d_line": 2, "w33": 1, "target_gain": 2.0, "clamp": 120, "k": 4, "lr": 0.05, "epochs": 4000},
]


def get_campaign_queue():
    queue_file = REPO_ROOT / "FPGA_code" / "scripts" / "campaign_queue.json"
    if queue_file.exists():
        try:
            with open(queue_file, "r") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    return data
        except Exception:
            pass
    return CAMPAIGN_CONDITIONS


def update_hourly_report():
    script = REPO_ROOT / "FPGA_code" / "scripts" / "generate_virtual_gain_hourly_report.py"
    py_bin = "/home/olle/anaconda3/bin/python" if Path("/home/olle/anaconda3/bin/python").exists() else sys.executable
    try:
        subprocess.run([py_bin, str(script)], check=True)
    except Exception as e:
        print(f"[!] Warning: Failed to generate hourly report: {e}")


def main():
    print("=" * 80)
    print("AUTONOMOUS MODE A SILICON CAMPAIGN: Virtual Gain Optimization")
    print(f"Target Hardware: Efinix Trion T120 Master SoC (192.168.1.50:5000)")
    print(f"Start Time:      {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"End Time Target: 17:00:00 Local Time")
    print(f"Queue Size:      {len(CAMPAIGN_CONDITIONS)} distinct parameter conditions")
    print("=" * 80)

    cond_idx = 0
    total_conds = len(CAMPAIGN_CONDITIONS)

    while True:
        queue = get_campaign_queue()
        if cond_idx >= len(queue):
            print(f"[*] Completed all {len(queue)} conditions in queue. Campaign stopping as requested!")
            break

        c = queue[cond_idx]
        cond_idx += 1

        print("\n" + "#" * 80)
        print(f"STARTING CONDITION #{cond_idx}: D_line={c['d_line']}x, D_w33={c['w33']}x, G_req={c['target_gain']:.1f}x, Clamp={c['clamp']} LSB, K={c['k']}, LR={c['lr']:.2f}x")
        print(f"Local Time: {time.strftime('%H:%M:%S')}")
        print("#" * 80)

        try:
            run_single_condition(
                d_line=c["d_line"],
                w33=c["w33"],
                target_gain=c["target_gain"],
                clamp=c["clamp"],
                k=c["k"],
                lr=c["lr"],
                epochs=c["epochs"],
                strata=10,
                host="192.168.1.50",
                port=5000,
                telem_stride=100,
                warm_start=c.get("warm_start", False),
            )
        except Exception as exc:
            print(f"[!] Exception during run #{cond_idx}: {exc}")
            time.sleep(5.0)

        # Trigger report update after every completed condition
        print("[*] Generating updated research report and telemetry figures...")
        update_hourly_report()

        # Brief cool-down between runs
        time.sleep(2.0)


if __name__ == "__main__":
    main()

