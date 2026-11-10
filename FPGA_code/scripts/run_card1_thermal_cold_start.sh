#!/bin/bash
# run_card1_thermal_cold_start.sh - Termiskt test med KALL START (Heater OFF först) på Card 1
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

echo "=========================================================================="
echo "STARTAR INVERTED MAML TERMISKT DRIFTTEST PÅ CARD 1 (1k/3.3k ATTENUATOR)"
echo "KALL START / HEATER OFF FÖRST (DC-kalibrering i rumstemperatur)"
echo "Parametrar: K=2, L2=768, LR=0.02, 30% PWM @ 1.0 Hz, 8m OFF / 8m ON"
echo "=========================================================================="

/home/olle/anaconda3/bin/python FPGA_code/scripts/run_card2_thermal_cycling.py \
    --card "Card 1" \
    --duration-minutes 20.0 \
    --heater-start off \
    --heater-off 8.0 \
    --heater-on 8.0 \
    --heater-duty-pct 30.0 \
    --heater-pwm-hz 1.0 \
    --regler-on 2.0 \
    --regler-off 2.0 \
    --l2-reg 768 \
    --k-batch 2 \
    --lr 0.02 \
    --out-json FPGA_code/logs/thermal_cycling/card1_thermal_cycling_heaters_8m8m_30pct_1hz_regler_2m2m_l2_768_k2_lr0p02_5p0_to_5p4ms_cold_start_20min.json
