#!/usr/bin/env python3
"""
verify_and_guard_version.py - T120 Master SoC Version Guard & Automatic Programmer
Patent Pending SE 2630397-4 (Open Science Hardware)

Mandatory protocol:
1. Queries T120 Master SoC via UDP port 5000 ("VERSION").
2. Checks both Hardware Logic Version (synthesized Verilog date/ID) and Software Firmware Version.
3. If offline, unprogrammed, or version mismatch detected:
   Automatically triggers `flash_soc.py` / `program_t120.py` to restore the correct bitstream and firmware.
4. Confirms active link and verified version before allowing experiment to start.
"""

import sys
import time
import argparse
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from gui.udp_client import MamlUdpClient

EXPECTED_HW_DEFAULT = "0x20261030"
EXPECTED_HW_ID_DEFAULT = "MAM1"
EXPECTED_SW_DEFAULT = "v2.1-MAML"


def query_t120_versions(host: str = "192.168.1.50", port: int = 5000, timeout: float = 1.0) -> dict:
    """Query HW and SW versions via UDP."""
    client = MamlUdpClient(host=host, port=port, timeout=timeout)
    try:
        return client.get_versions()
    finally:
        client.close()


def reprogram_t120(recompile_sw: bool = True) -> bool:
    """Reprogram T120 FPGA via flash_soc.py or program_t120.py."""
    print("=" * 80)
    print("[VERSION GUARD] TRIGGERING AUTOMATIC T120 FPGA PROGRAMMING VIA JTAG...")
    print("=" * 80)

    if recompile_sw:
        script = REPO_ROOT / "FPGA_code" / "scripts" / "flash_soc.py"
        cmd = [sys.executable, str(script)]
    else:
        script = REPO_ROOT / "FPGA_code" / "scripts" / "program_t120.py"
        bit_file = REPO_ROOT / "FPGA_code" / "T120F324" / "outflow" / "T120_MALM.bit"
        cmd = [sys.executable, str(script), str(bit_file)]

    print(f"[*] Executing: {' '.join(cmd)}")
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
    print(res.stdout)
    if res.returncode != 0:
        print(f"[!] Programming failed with code {res.returncode}:\n{res.stderr}", file=sys.stderr)
        return False

    print("[+] Programming complete. Waiting 6 seconds for Gigabit PHY auto-negotiation...")
    time.sleep(6.0)
    return True


def ensure_version_guard(
    host: str = "192.168.1.50",
    port: int = 5000,
    expected_hw: str = EXPECTED_HW_DEFAULT,
    expected_sw: str = EXPECTED_SW_DEFAULT,
    force_reprogram: bool = False,
    max_retries: int = 15,
) -> dict:
    """
    Ensure T120 is online and running the exact required HW and SW versions.
    If mismatch or offline, automatically reprograms and verifies.
    """
    print("=" * 80)
    print(f"[VERSION GUARD] Verifying T120 SoC @ {host}:{port}")
    print(f"  Expected HW Logic : {expected_hw} (Subsystem {EXPECTED_HW_ID_DEFAULT})")
    print(f"  Expected SW FW    : {expected_sw}")
    print("=" * 80)

    info = query_t120_versions(host=host, port=port, timeout=0.8)
    print(f"[*] Current board response:\n    {info['raw'].replace(chr(10), chr(10) + '    ')}")

    hw_match = (expected_hw in info["hw_version"]) if expected_hw else True
    sw_match = (expected_sw in info["sw_version"]) if expected_sw else True
    online = "Offline" not in info["raw"]

    if not force_reprogram and online and hw_match and sw_match:
        print("[+] VERIFICATION PASSED: Board is running target HW and SW versions!")
        return info

    if not online:
        print("[!] Board is OFFLINE or unprogrammed.")
    elif not hw_match:
        print(f"[!] HW Logic Version Mismatch: Board={info['hw_version']!r} vs Target={expected_hw!r}")
    elif not sw_match:
        print(f"[!] SW Firmware Version Mismatch: Board={info['sw_version']!r} vs Target={expected_sw!r}")

    # Trigger automatic reprogramming
    if not reprogram_t120(recompile_sw=True):
        raise RuntimeError("Failed to reprogram T120 FPGA!")

    # Poll for link recovery and verify version
    print(f"[*] Polling T120 version up to {max_retries} times...")
    for attempt in range(1, max_retries + 1):
        time.sleep(1.0)
        info = query_t120_versions(host=host, port=port, timeout=0.8)
        hw_match = (expected_hw in info["hw_version"]) if expected_hw else True
        sw_match = (expected_sw in info["sw_version"]) if expected_sw else True
        online = "Offline" not in info["raw"]

        if online and hw_match and sw_match:
            print(f"[+] VERIFICATION SUCCESSFUL on attempt {attempt}:")
            print(f"    HW Version: {info['hw_version']} (ID={info['hw_id']})")
            print(f"    SW Version: {info['sw_version']} ({info['sw_build']})")
            print(f"    Status    : {info['status']}")
            return info
        print(f"    Attempt {attempt}/{max_retries}: {info['raw'].splitlines()[0] if info['raw'] else 'Waiting...'}")

    raise TimeoutError(f"T120 failed to report expected version {expected_hw} / {expected_sw} after reprogramming.")


def main():
    parser = argparse.ArgumentParser(description="T120 Version Guard & Verification Tool")
    parser.add_argument("--host", default="192.168.1.50", help="T120 IP address")
    parser.add_argument("--port", type=int, default=5000, help="T120 UDP port")
    parser.add_argument("--expected-hw", default=EXPECTED_HW_DEFAULT, help=f"Expected HW Logic version (default: {EXPECTED_HW_DEFAULT})")
    parser.add_argument("--expected-sw", default=EXPECTED_SW_DEFAULT, help=f"Expected SW FW version (default: {EXPECTED_SW_DEFAULT})")
    parser.add_argument("--force-reprogram", action="store_true", help="Force FPGA reprogramming regardless of current version")
    args = parser.parse_args()

    try:
        ensure_version_guard(
            host=args.host,
            port=args.port,
            expected_hw=args.expected_hw,
            expected_sw=args.expected_sw,
            force_reprogram=args.force_reprogram,
        )
    except Exception as exc:
        print(f"[ERROR] Version Guard Failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

