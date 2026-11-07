#!/bin/bash
# ==============================================================================
# Inverted MAML Silicon Benchmark: Shifted Temporal Window [5.0..6.0 ms] (K=1)
# Card 2 Silicon (T120 SoC + T20 Coprocessor, 1k/3.3k Attenuator)
# ==============================================================================
set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$REPO_ROOT"

echo "=== Launching Inverted MAML Mode A 1000-Epoch Benchmark: Shifted Window [5.0..6.0 ms] ==="
python FPGA_code/scripts/run_card2_broadened_11strata_k1_online.py \
    --epochs 1000 \
    --k-batch 1 \
    --lr 0.02 \
    --reg-lambda 2048 \
    --noise-color white \
    --staircase-w3 \
    --w33-variance-lsb-range 5 \
    --attenuator 1k/3.3k \
    --t-min 5000 \
    --t-max 6000 \
    --t-step 100

