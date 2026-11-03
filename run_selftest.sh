#!/bin/bash
# ==============================================================================
# Inverted MAML Hardware Self-Test Runner
# Executes automated Jumper & Attenuator Continuity Test on Card 2
# ==============================================================================
PYTHON_BIN="/home/olle/anaconda3/bin/python"
SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/FPGA_code/scripts/run_hadamard_attenuator_selftest.py"

if [ ! -x "$PYTHON_BIN" ]; then
    PYTHON_BIN="python3"
fi

$PYTHON_BIN "$SCRIPT_PATH" "$@"

