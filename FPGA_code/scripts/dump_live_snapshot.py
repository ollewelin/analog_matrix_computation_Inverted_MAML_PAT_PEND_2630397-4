#!/usr/bin/env python3
"""
dump_live_snapshot.py
=====================
Reads live_training.log and exports an instant JSON snapshot dataset that can
be loaded directly into maml_post_analysis_gui.py right now while training is running!
"""

import re
import json
from pathlib import Path
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LOG_FILE = REPO_ROOT / "live_training.log"
OUT_JSON = REPO_ROOT / "FPGA_code" / "logs" / "mode_a_longterm_sweep" / "test_1k33k_fullswing_live_snapshot.json"

def main():
    if not LOG_FILE.exists():
        print(f"Log file {LOG_FILE} not found!")
        return

    with open(LOG_FILE, "r") as f:
        lines = f.readlines()

    records = []
    # Base record 0
    records.append({
        "epoch": 0,
        "rmse_lsb": 367.69,
        "enob_bits": 2.48,
        "loss_lsb2": 405593.7,
        "w8_diag": [24, 24, 24, 24, 24, 24],
        "w3_diag": [64, 64, 64, 64, 64, 64],
        "r_m3": 1.0,
    })

    # Line regex: Ep | Train RMSE | Val RMSE | Val ENOB | M8 Diag | r_M3
    # Example: "  25 |   303.56 LSB |   126.48 LSB |   4.02 b | [29, 29, 25, 33, 63, 24] | +0.9784"
    line_re = re.compile(
        r"^\s*(\d+)\s*\|\s*([\d\.]+)\s*LSB\s*\|\s*([\d\.]+)\s*LSB\s*\|\s*([\d\.]+)\s*b\s*\|\s*\[([-\d,\s]+)\]\s*\|\s*([+-][\d\.]+)"
    )

    for line in lines:
        m = line_re.match(line)
        if m:
            ep = int(m.group(1))
            train_rmse = float(m.group(2))
            val_rmse = float(m.group(3))
            val_enob = float(m.group(4))
            w8_diag = [int(x.strip()) for x in m.group(5).split(",")]
            r_m3 = float(m.group(6))
            loss = float(3.0 * (val_rmse ** 2))

            records.append({
                "epoch": ep,
                "train_rmse_lsb": train_rmse,
                "rmse_lsb": val_rmse,
                "enob_bits": val_enob,
                "loss_lsb2": loss,
                "w8_diag": w8_diag,
                "w3_diag": [64, 64, 64, 64, 64, 64],
                "r_m3": r_m3,
            })

    if not records:
        print("No epoch records parsed!")
        return

    best_idx = int(np.argmin([r["rmse_lsb"] for r in records[1:]])) + 1
    best_rmse = records[best_idx]["rmse_lsb"]
    best_enob = records[best_idx]["enob_bits"]
    best_ep = records[best_idx]["epoch"]

    summary = {
        "hardware": "Efinix Trion T120F324 Master SoC",
        "resistors": "1k / 3.3k ohm summing attenuator",
        "k": 20,
        "lr": 0.04,
        "momentum": 0.95,
        "epochs_completed": len(records) - 1,
        "best_rmse": best_rmse,
        "best_enob": best_enob,
        "best_epoch": best_ep,
        "records": records,
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"[+] Successfully exported {len(records)-1} epochs to {OUT_JSON}")
    print(f"    Current Best: {best_rmse:.2f} LSB RMSE | {best_enob:.2f} bits ENOB at Epoch {best_ep}")

if __name__ == "__main__":
    main()
