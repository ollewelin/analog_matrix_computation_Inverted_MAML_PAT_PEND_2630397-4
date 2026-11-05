#!/usr/bin/env python3
"""
run_card1_mode_b_1000ep.py
Convenience runner for Step 3: Card 1 (1k/2.2k Attenuator) in MODE B (Jumpers Removed).
Executes 1,000-Epoch Broadened Window [4.5..5.5 ms] Pure Online SGD under White Noise.
"""

import sys
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PYTHON = "/home/olle/anaconda3/bin/python"
SCRIPT = REPO_ROOT / "FPGA_code" / "scripts" / "run_card2_broadened_11strata_k1_online.py"

cmd = [
    PYTHON, str(SCRIPT),
    "--card", "Card 1",
    "--prefix", "card1_mode_b",
    "--attenuator", "1k/2.2k",
    "--noise-color", "white",
    "--lr", "0.02",
    "--reg-lambda", "2048",
    "--d-line", "2",
    "--w33-variance-lsb-range", "5",
    "--jumper-mode", "3",
    "--epochs", "1000"
]

print("=" * 90)
print("STARTING STEP 3: CARD 1 (1k/2.2k) IN MODE B (JUMPERS REMOVED)")
print("Command:", " ".join(cmd))
print("=" * 90)

sys.exit(subprocess.call(cmd))

