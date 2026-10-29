w#!/usr/bin/env python3
"""
maml_gain_ctl.py: Dynamic CLI Controller for Virtual Gain / Attenuation Experiments
Inverted MAML AIMC Platform (Patent Pending SE 2630397-4)
Carrier Board PCB v1.3.2 (Summing Attenuator Mod: 1k / 3.3k Ohm)

Usage:
    # Query live hardware configuration & telemetry:
    ./maml_gain_ctl.py --status

    # Configure Olle's 1/4 attenuation + 4x target demand (Triad takes 75%):
    ./maml_gain_ctl.py --d-line 2 --w33 2 --target-gain 4.0 --clamp 120

    # Configure Olle's 1/4 attenuation + 2x target demand (50/50 balance):
    ./maml_gain_ctl.py --d-line 2 --w33 2 --target-gain 2.0 --clamp 120

    # Reset back to nominal baseline (1x, 1x, 1.0x, clamp 80 LSB):
    ./maml_gain_ctl.py --reset
"""

import sys
import argparse
from pathlib import Path

# Add repo root to import path
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from gui.udp_client import MamlUdpClient


def print_status(telem):
    if telem is None:
        print("[!] ERROR: No telemetry received from T120 SoC. Hardware offline?")
        return

    print("=" * 72)
    print(" INVERTED MAML MODE A: VIRTUAL GAIN & HARDWARE STATUS")
    print("=" * 72)
    print(f" Target Hardware:       {telem.status_text}")
    print(f" Operational Mode:      Mode {telem.mode} (Jumper {telem.jumper_mode})")
    print("-" * 72)
    print(" VIRTUAL GAIN EXPERIMENT SETTINGS [VIRTUAL_HARDWARE_EMULATION]:")
    print(f"   Data Line Divider:   D_line = {telem.d_line_div}x (Input span: [-{45//telem.d_line_div}, +{45//telem.d_line_div}] LSB)")
    print(f"   Matrix 33 Divider:   D_w33  = {telem.w33_div}x (W33 scale: 1/{telem.w33_div})")
    print(f"   Total M33 Output:    A_33   = 1/{telem.d_line_div * telem.w33_div} ({100.0 / (telem.d_line_div * telem.w33_div):.1f}% of nominal)")
    print(f"   Target Demand Gain:  G_req  = {telem.target_gain_mult:.2f}x (Q8={telem.target_gain_q8})")
    
    # Calculate required Triad compensation share
    m33_share = 100.0 / (telem.d_line_div * telem.w33_div)
    target_rel = telem.target_gain_mult * m33_share
    triad_share = max(0.0, target_rel - m33_share)
    print(f"   Demanded Net Target: {target_rel:.1f}% nominal | Primary M33: {m33_share:.1f}% | Triad Burden: {triad_share:.1f}%")
    print(f"   Compensation Clamp:  W_clamp = +/-{telem.w_comp_clamp} LSB (M3 & M8)")
    print("-" * 72)
    print(" LIVE SILICON TELEMETRY:")
    print(f"   Current ENOB:        {telem.enob_bits:.2f} bits (Comp: {telem.enob_comp_bits:.2f} b, Uncomp: {telem.enob_uncomp_bits:.2f} b)")
    print(f"   Quadratic Loss:      {telem.mse_q14 * 10} LSB^2 (Epoch: {telem.outer_epoch}, Step: {telem.inner_step})")
    print(f"   Reference Vector X:  {telem.ref_x}")
    print(f"   Digital Target Z:    {telem.z_target}")
    print(f"   Intermediate ADC45:  {telem.adc45_sig}")
    print(f"   Final Output ADC49:  {telem.adc49_sig}")
    print("=" * 72)


def main():
    parser = argparse.ArgumentParser(
        description="CLI Controller for Inverted MAML Virtual Gain / Attenuation Experiments"
    )
    parser.add_argument("--host", default="192.168.1.50", help="T120 SoC IP address (default: 192.168.1.50)")
    parser.add_argument("--port", type=int, default=5000, help="T120 SoC UDP port (default: 5000)")
    parser.add_argument("--status", action="store_true", help="Query and display current telemetry and gain settings")
    parser.add_argument("--d-line", type=int, default=None, help="Data line divider (1..16, e.g. 1=nominal, 2=half swing)")
    parser.add_argument("--w33", type=int, default=None, help="Matrix 33 weight divider (1..16, e.g. 1=nominal, 2=half scale)")
    parser.add_argument("--target-gain", type=float, default=None, help="Digital target demand gain multiplier (e.g. 1.0, 2.0, 4.0)")
    parser.add_argument("--clamp", type=int, default=None, help="Compensation weight clamp in LSB (40..127, e.g. 80 or 120)")
    parser.add_argument("--reset", action="store_true", help="Reset all settings to nominal baseline (d_line=1, w33=1, gain=1.0, clamp=80)")
    args = parser.parse_args()

    client = MamlUdpClient(host=args.host, port=args.port, timeout=2.0)

    if args.reset:
        print(f"[*] Resetting virtual gain settings to nominal baseline on {args.host}:{args.port}...")
        telem = client.set_gain_experiment(d_line=1, w33=1, target_gain=1.0, clamp=80)
        print_status(telem)
        return

    # Check if any configuration flags were provided
    any_cfg = (args.d_line is not None or args.w33 is not None or 
               args.target_gain is not None or args.clamp is not None)

    if any_cfg:
        # First query current state to preserve unmentioned fields
        cur = client.poll_telemetry()
        cur_d_line = cur.d_line_div if cur else 1
        cur_w33 = cur.w33_div if cur else 1
        cur_gain = cur.target_gain_mult if cur else 1.0
        cur_clamp = cur.w_comp_clamp if cur else 80

        new_d_line = args.d_line if args.d_line is not None else cur_d_line
        new_w33 = args.w33 if args.w33 is not None else cur_w33
        new_gain = args.target_gain if args.target_gain is not None else cur_gain
        new_clamp = args.clamp if args.clamp is not None else cur_clamp

        print(f"[*] Sending new gain configuration to {args.host}:{args.port}...")
        print(f"    D_line={new_d_line}x, W33_div={new_w33}x, Target_Gain={new_gain:.2f}x, Clamp={new_clamp} LSB")
        telem = client.set_gain_experiment(
            d_line=new_d_line,
            w33=new_w33,
            target_gain=new_gain,
            clamp=new_clamp
        )
        print_status(telem)
    else:
        # Just query status
        telem = client.poll_telemetry()
        print_status(telem)


if __name__ == "__main__":
    main()

