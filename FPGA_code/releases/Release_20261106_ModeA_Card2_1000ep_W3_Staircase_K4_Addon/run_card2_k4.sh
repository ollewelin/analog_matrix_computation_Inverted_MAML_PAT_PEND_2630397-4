#!/usr/bin/env bash
set -e
# Run Card 2 Broadened 11-Strata K=4 Mini-Batch SGD Benchmark
PYTHON=/home/olle/anaconda3/bin/python
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
K1_PKG="${SCRIPT_DIR}/../Release_20261106_ModeA_Card2_1000ep_W3_Staircase_K1_PairedAblation"

echo "[*] Launching Card 2 1000-Epoch Benchmark (K=4 Mini-Batch SGD)..."
$PYTHON "${K1_PKG}/pc_python/run_card2_broadened_11strata_k1_online.py" \
    --epochs 1000 \
    --k-batch 4 \
    --lr 0.02 \
    --reg 2048 \
    --swing 40 \
    --var 5 \
    --ip 192.168.1.50

echo "[*] Generating Comprehensive 10-page Report (K=4)..."
$PYTHON "${K1_PKG}/pc_python/generate_card2_w3_staircase_comprehensive_report.py" \
    --k-batch 4
