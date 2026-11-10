#!/bin/bash
# run_thermal_gui.sh - Startar fristående Live-GUI för Termisk Cykling och Mode A Reglering
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export DISPLAY=${DISPLAY:-:1}
echo "[*] Startar Inverted MAML Thermal Live GUI på DISPLAY=$DISPLAY..."
cd "$REPO_ROOT"
/home/olle/anaconda3/bin/python gui/thermal_live_gui.py "$@"
