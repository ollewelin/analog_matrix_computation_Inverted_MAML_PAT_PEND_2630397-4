#!/bin/bash
set -e
source /home/olle/efinix2/efinity-2025.2.288.2.10-linux-x64/efinity/2025.2/bin/setup.sh
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$REPO_ROOT/FPGA_code/T120F324"
efx_run T120_MALM.xml --flow compile

echo "=== Kör Timing Guard kontroll ==="
python3 "$REPO_ROOT/.agents/skills/efinix-timing-guard/check_timing.py" outflow/T120_MALM.timing.rpt top_level.sv
