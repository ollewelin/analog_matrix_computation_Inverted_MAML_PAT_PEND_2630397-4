#!/usr/bin/env bash
# =============================================================================
# regenerate_efinix_ip.sh
# 
# Clean, automated, reproducible generator for proprietary Efinix IP blocks
# (Sapphire SoC `RISC_mini`) using the local user's Efinity installation.
#
# Designed for developers and AI agents cloning this public repository.
# Complies with Efinix EULA by generating vendor RTL locally.
# =============================================================================

set -e

# Detect script location and repository root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PROJECT_DIR="$REPO_ROOT/FPGA_code/T120F324"
IP_DIR="$PROJECT_DIR/ip/RISC_mini"
SETTINGS_FILE="$IP_DIR/settings.json"

echo "=== Efinix IP Regeneration Tool ==="

# 1. Check EFINITY_HOME
if [ -z "$EFINITY_HOME" ]; then
    echo "[!] ERROR: EFINITY_HOME environment variable is not set."
    echo "    Please source your Efinity setup script before running:"
    echo "    source /path/to/efinity/<version>/bin/setup.sh"
    exit 1
fi

echo "[*] EFINITY_HOME: $EFINITY_HOME"

# 2. Check settings.json existence
if [ ! -f "$SETTINGS_FILE" ]; then
    echo "[!] ERROR: Missing IP configuration: $SETTINGS_FILE"
    exit 1
fi

# Ensure EFINITY_USER_DIR is defined (needed by efx_ipmgr)
if [ -z "$EFINITY_USER_DIR" ]; then
    export EFINITY_USER_DIR="$HOME/.efinity"
    mkdir -p "$EFINITY_USER_DIR"
fi

# 3. Execute Headless IP Generation
echo "[*] Regenerating Sapphire RISC_mini SoC from settings.json..."

"$EFINITY_HOME/bin/python3" - <<EOF
import os, sys, json
from pathlib import Path

# Add Efinity IPM binaries to path
ipm_bin = os.path.join(os.environ['EFINITY_HOME'], 'ipm', 'bin')
sys.path.insert(0, ipm_bin)

from efx_ipmgr.api_v2 import IPManagerBackend, IPGenSettingDecoder

project_dir = Path("$PROJECT_DIR").resolve()
ip_dir = Path("$IP_DIR").resolve()
setting_file = Path("$SETTINGS_FILE").resolve()

with open(setting_file) as f:
    setting = json.load(f, cls=IPGenSettingDecoder)

backend = IPManagerBackend.singleton()
backend.init()

out_dir = project_dir

# Backup settings.json content because upgrade_ip might overwrite or move it
settings_backup = setting_file.read_text()

print(f"[*] Calling Efinity IP Manager backend...")
res = backend.upgrade_ip(
    out_dir=out_dir,
    setting_path=setting_file,
    from_vlnv=setting.vlnv,
    to_vlnv=setting.vlnv,
    device='T120F324',
    family='Trion',
    project_xml_path=str(project_dir / 'T120_MALM.xml'),
    peri_xml_file_path=str(project_dir / 'T120_MALM.peri.xml')
)

# Ensure settings.json is preserved
if not setting_file.exists():
    setting_file.write_text(settings_backup)

target_v = ip_dir / 'RISC_mini.v'
if target_v.exists():
    print(f"[+] Successfully generated: {target_v} ({target_v.stat().st_size} bytes)")
else:
    print(f"[!] Warning: {target_v} was not found after generation.")
    sys.exit(1)
EOF

echo "[+] IP generation complete! You can now run build_t120_fpga.sh"

