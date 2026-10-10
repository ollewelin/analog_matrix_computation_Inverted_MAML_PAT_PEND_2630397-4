#!/bin/bash
set -e
source /home/olle/efinix2/efinity-2025.2.288.2.10-linux-x64/efinity/2025.2/bin/setup.sh
cd /home/olle/AnalogAI/git/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/T120F324
efx_run T120_MALM.xml --flow compile

echo "=== Kör Timing Guard kontroll ==="
python3 /home/olle/AnalogAI/git/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/.agents/skills/efinix-timing-guard/check_timing.py outflow/T120_MALM.timing.rpt top_level.sv
