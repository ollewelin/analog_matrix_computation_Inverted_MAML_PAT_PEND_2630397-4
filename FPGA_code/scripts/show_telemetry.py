#!/home/olle/anaconda3/bin/python
"""
show_telemetry.py - CLI tool to inspect live Inverted MAML silicon telemetry
=============================================================================
Queries T120 SoC telemetry over UDP (192.168.1.50:5000) and displays:
  - Analog ADCs: ADC_49 (ColTIA/Sig10), ADC_45 (Sig4)
  - Ideal Target: Z_target
  - Residual Errors: Err = Z_target - ADC_49 (per column)
  - Metrics: Loss (LSB²), RMSE (LSB), ENOB (bits)
  - Reference Input: X_ref
  - Compensation Weights: W_M8 (Row 0)
  - Status flags: Jumper mode, Clipping, Hadamard freq

Usage:
  # Single snapshot:
  ./FPGA_code/scripts/show_telemetry.py

  # Live continuous watch mode (refreshes every 0.5s):
  ./FPGA_code/scripts/show_telemetry.py --watch

  # Raw JSON output:
  ./FPGA_code/scripts/show_telemetry.py --json
"""

from __future__ import annotations
import sys
import time
import json
import argparse
from pathlib import Path
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from gui.udp_client import MamlUdpClient

C_RESET   = "\033[0m"
C_BOLD    = "\033[1m"
C_CYAN    = "\033[36m"
C_GREEN   = "\033[32m"
C_YELLOW  = "\033[33m"
C_RED     = "\033[31m"
C_BLUE    = "\033[34m"
C_MAGENTA = "\033[35m"
C_DIM     = "\033[2m"
CLEAR_SCREEN = "\033[2J\033[H"


def format_vector(vec, width=7):
    return "[" + ", ".join(f"{v:{width}d}" for v in vec) + "]"


def fetch_telemetry_snapshot(client: MamlUdpClient) -> dict | None:
    try:
        t = client.get_telemetry()
        if not t or not t.connected_hw:
            return None

        z = np.array(t.z_target, dtype=float)
        adc49 = np.array(t.adc49_sig, dtype=float)
        adc45 = np.array(t.adc45_sig, dtype=float)
        err = z - adc49
        loss = float(np.sum(err**2)) / 2.0
        rmse = float(np.sqrt(np.mean(err**2)))
        enob = max(0.0, 11.0 - np.log2(max(rmse, 1.0)))

        return {
            "connected": t.connected_hw,
            "mode": t.mode,
            "jumper_mode": t.jumper_mode,
            "clip_cnt": t.clip_events_cnt,
            "hadamard_khz": t.hadamard_khz,
            "x_ref": list(t.x_ref),
            "z_target": list(t.z_target),
            "adc49": list(t.adc49_sig),
            "adc45": list(t.adc45_sig),
            "err": [int(round(e)) for e in err],
            "loss_lsb2": round(loss, 1),
            "rmse_lsb": round(rmse, 2),
            "enob_bits": round(enob, 2),
            "enob_hw_comp": round(float(t.enob_comp_bits), 2),
            "w8_row0": list(t.w_m8[0]),
            "timestamp": time.strftime("%H:%M:%S"),
        }
    except Exception as e:
        return {"error": str(e)}


def print_snapshot(data: dict):
    if "error" in data:
        print(f"{C_RED}[ERROR]{C_RESET} Telemetry fetch failed: {data['error']}")
        return

    loss = data["loss_lsb2"]
    rmse = data["rmse_lsb"]
    enob = data["enob_bits"]
    hw_enob = data["enob_hw_comp"]

    print(f"{C_BOLD}{C_CYAN}╔════════════════════════════════════════════════════════════════════════════════════════╗{C_RESET}")
    print(f"{C_BOLD}{C_CYAN}║     INVERTED MAML — LIVE HARDWARE TELEMETRY SNAPSHOT (T120 SoC @ 192.168.1.50)     ║{C_RESET}")
    print(f"{C_BOLD}{C_CYAN}╚════════════════════════════════════════════════════════════════════════════════════════╝{C_RESET}")
    print(f"  {C_BOLD}Time:{C_RESET} {data['timestamp']}  |  {C_BOLD}Jumper Mode:{C_RESET} {data['jumper_mode']}  |  {C_BOLD}Hadamard:{C_RESET} {data['hadamard_khz']} kHz  |  {C_BOLD}Clips:{C_RESET} {data['clip_cnt']}")
    print("")
    print(f"  {C_BOLD}Overall Precision & Loss:{C_RESET}")
    print(f"    • {C_BOLD}Loss:{C_RESET} {C_YELLOW}{loss:10.1f} LSB²{C_RESET}    • {C_BOLD}RMSE:{C_RESET} {C_YELLOW}{rmse:6.2f} LSB{C_RESET}")
    print(f"    • {C_BOLD}ENOB (Instant):{C_RESET} {C_GREEN}{C_BOLD}{enob:5.2f} bits{C_RESET}  • {C_BOLD}ENOB (HW Avg):{C_RESET} {C_GREEN}{hw_enob:5.2f} bits{C_RESET}")
    print("")
    print(f"  {C_BOLD}Per-Column Analog Signal Breakdown (6 Columns):{C_RESET}")
    print(f"  {C_DIM}Col   Target (Z_target)   Measured (ADC_49)   Error (Z - ADC)   Sig4 (ADC_45)   Bar (LSB){C_RESET}")
    print(f"  {C_DIM}────  ─────────────────   ─────────────────   ───────────────   ─────────────   ──────────────{C_RESET}")

    errs = data["err"]
    z_t = data["z_target"]
    a49 = data["adc49"]
    a45 = data["adc45"]

    for c in range(6):
        e = errs[c]
        color = C_GREEN if abs(e) < 80 else (C_YELLOW if abs(e) < 180 else C_RED)
        bars = min(16, int(abs(e) / 20))
        bar_str = "■" * bars
        sign = "+" if e >= 0 else ""
        print(f"  C{c}:      {z_t[c]:7d} LSB        {a49[c]:7d} LSB   {color}{sign}{e:6d} LSB{C_RESET}      {a45[c]:7d} LSB   {color}{bar_str}{C_RESET}")

    print("")
    print(f"  {C_BOLD}Inputs & Active Compensation Weights:{C_RESET}")
    print(f"    • {C_BOLD}X_ref (DAC2):{C_RESET}      {format_vector(data['x_ref'], 5)}")
    print(f"    • {C_BOLD}W_M8 Row 0:{C_RESET}        {format_vector(data['w8_row0'], 5)} LSB")
    print(f"{C_DIM}────────────────────────────────────────────────────────────────────────────────────────{C_RESET}")


def main():
    parser = argparse.ArgumentParser(description="Show live telemetry from Inverted MAML T120 hardware")
    parser.add_argument("--host", default="192.168.1.50", help="T120 IP address")
    parser.add_argument("--port", type=int, default=5000, help="T120 UDP port")
    parser.add_argument("-w", "--watch", action="store_true", help="Continuously refresh telemetry dashboard")
    parser.add_argument("-i", "--interval", type=float, default=0.5, help="Refresh interval in seconds (watch mode)")
    parser.add_argument("--json", action="store_true", help="Print telemetry as JSON")
    args = parser.parse_args()

    client = MamlUdpClient(host=args.host, port=args.port, timeout=1.0)

    if args.json:
        snap = fetch_telemetry_snapshot(client)
        print(json.dumps(snap, indent=2))
        return

    if not args.watch:
        snap = fetch_telemetry_snapshot(client)
        if snap:
            print_snapshot(snap)
        else:
            print(f"{C_RED}[ERROR]{C_RESET} Could not connect to T120 at {args.host}:{args.port}")
        return

    # Watch mode
    try:
        while True:
            snap = fetch_telemetry_snapshot(client)
            print(CLEAR_SCREEN, end="")
            if snap:
                print_snapshot(snap)
                print(f"  {C_DIM}Press Ctrl+C to exit monitor (background training continues unaffected).{C_RESET}")
            else:
                print(f"{C_YELLOW}[!] Waiting for T120 telemetry at {args.host}:{args.port}...{C_RESET}")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print(f"\n{C_DIM}[*] Monitor stopped.{C_RESET}")


if __name__ == "__main__":
    main()
