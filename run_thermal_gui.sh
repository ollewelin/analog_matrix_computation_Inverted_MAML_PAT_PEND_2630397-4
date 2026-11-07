#!/bin/bash
# run_thermal_gui.sh - Startar fristående Live-GUI för Termisk Cykling och Mode A Reglering
export DISPLAY=${DISPLAY:-:1}
echo "[*] Startar Inverted MAML Thermal Live GUI på DISPLAY=$DISPLAY..."
/home/olle/anaconda3/bin/python gui/thermal_live_gui.py "$@"
