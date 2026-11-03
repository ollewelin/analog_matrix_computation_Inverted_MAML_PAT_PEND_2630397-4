#!/bin/bash
# ==============================================================================
# Inverted MAML Hardware DC Null Baseline Calibration Runner
# Executes automated generic column-by-column DC calibration on physical silicon
# ==============================================================================
PYTHON_BIN="/home/olle/anaconda3/bin/python"
SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/FPGA_code/scripts/run_dc_baseline_calibration.py"

if [ ! -x "$PYTHON_BIN" ]; then
    PYTHON_BIN="python3"
fi

$PYTHON_BIN "$SCRIPT_PATH" "$@"

