#!/usr/bin/env python3
"""
CLI Tool: Single-Cell Multiplier (X × W) Hardware Test
======================================================
Tests a single Dual-2T1C crosspoint multiplier cell (Matrix, Row, Col) by:
  1. Locking the cell's differential weight W (W+ = 128 + W, W- = 128 - W).
  2. Stepping the In-Data Row value X on DAC_2[row] (code = 128 + X) across
     either [-x_step, 0, +x_step] or any custom list of --inputs while holding
     all other 29 DACs at 128 (0.0V differential).

Usage examples:
  # 1. Step In-Data Row DAC_2[0] by ±96 (codes 32, 128, 224) across 5 weights W:
  python3 FPGA_code/scripts/test_single_cell_multiplier.py --matrix M33 --row 0 --col 0 --x-step 96

  # 2. Step In-Data Row DAC_2[0] across a custom list of X values (-120, -60, 0, +60, +120):
  python3 FPGA_code/scripts/test_single_cell_multiplier.py --matrix M33 --row 0 --col 0 --inputs -120,-60,0,60,120

  # 3. Lock ONE specific In-Data Row value (--x) and ONE Weight (--w) on the board for oscilloscope probing:
  python3 FPGA_code/scripts/test_single_cell_multiplier.py --matrix M33 --row 0 --col 0 --x 96 --w 64 --hold
"""

from __future__ import annotations
import argparse
import sys
from pathlib import Path

REPO_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from gui.udp_client import MAT_M3, MAT_M8, MAT_M33, MamlUdpClient


def parse_matrix_id(name: str) -> tuple[int, str]:
    s = name.strip().upper()
    if s in ("M3", "0", "3"):
        return MAT_M3, "M3 (Layer 1 Comp 8×6 → ADC_45)"
    if s in ("M8", "1", "8"):
        return MAT_M8, "M8 (Layer 2 Comp 7×6 → ADC_49)"
    if s in ("M33", "2", "33"):
        return MAT_M33, "M33 (Main Payload 6×6 → ADC_49)"
    raise ValueError(f"Unknown matrix '{name}'. Choose M3, M8, or M33.")


def read_cell_at_xw(client: MamlUdpClient, mat_id: int, row: int, col: int, x_val: int, w_val: int, hold: bool = False) -> int:
    res = client.probe_cell_xw(mat_id, row, col, x_amp=x_val, w_fixed=w_val, sweep_input=True, hold=hold)
    if res is None:
        raise RuntimeError("No response from hardware on MAML_CMD_PROBE_CELL (0x17).")
    if x_val == 0:
        return res.adc45_zero[col] if mat_id == MAT_M3 else res.adc49_zero[col]
    return res.adc45_pos[col] if mat_id == MAT_M3 else res.adc49_pos[col]


def main() -> int:
    parser = argparse.ArgumentParser(description="Single-Cell Multiplier (X × W) Hardware Test")
    parser.add_argument("--host", default="192.168.1.50", help="T120 IP address (default: 192.168.1.50)")
    parser.add_argument("--port", type=int, default=5000, help="T120 UDP port (default: 5000)")
    parser.add_argument("--matrix", default="M33", help="Target matrix: M33, M3, or M8 (default: M33)")
    parser.add_argument("--row", type=int, default=0, help="In-Data Row index 0..7 (default: 0 = Row 1)")
    parser.add_argument("--col", type=int, default=0, help="Column index 0..5 (default: 0 = Col 1)")
    parser.add_argument("--x-step", type=int, default=96, help="In-Data Row DAC_2[row] step ±X in LSBs (default: 96)")
    parser.add_argument(
        "--inputs",
        default=None,
        help="Optional comma-separated list of In-Data Row X values in [-127..+127] (e.g. -120,-60,0,60,120)",
    )
    parser.add_argument(
        "--weights",
        default="-96,-48,0,48,96",
        help="Comma-separated list of signed weights W in [-127..+127] (default: -96,-48,0,48,96)",
    )
    parser.add_argument("--x", type=int, default=None, help="Single In-Data Row value X (-127..+127) to set")
    parser.add_argument("--w", type=int, default=None, help="Single Weight value W (-127..+127) to set")
    parser.add_argument("--hold", action="store_true", help="Hold the (X, W) DAC voltages active on the board after test")

    # Allow negative values like `--inputs -120,-60,0,60,120` or `--x -96` without requiring `=`
    norm_argv: list[str] = []
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] in ("--inputs", "--weights", "--x", "--w", "--x-step") and i + 1 < len(sys.argv):
            norm_argv.append(f"{sys.argv[i]}={sys.argv[i + 1]}")
            i += 2
        else:
            norm_argv.append(sys.argv[i])
            i += 1
    args = parser.parse_args(norm_argv)

    mat_id, mat_desc = parse_matrix_id(args.matrix)
    client = MamlUdpClient(host=args.host, port=args.port)
    ver = client.query_version()
    print(f"Connected to: {ver}")
    print(f"Target Cell : {mat_desc} | Row={args.row} (R{args.row+1}), Col={args.col} (C{args.col+1})")

    # Mode A: Single (DAC_2, W) point (optionally held on board for oscilloscope)
    if args.x is not None or args.w is not None:
        x_val = max(-127, min(127, args.x if args.x is not None else args.x_step))
        w_val = max(-127, min(127, args.w if args.w is not None else 64))
        dac2_code = 128 + x_val
        vds_mv = (dac2_code / 255.0) * 250.0
        v = read_cell_at_xw(client, mat_id, args.row, args.col, x_val, w_val, hold=args.hold)
        print(
            f"Single Point: Single-Ended Data DAC_2[{args.row}]={dac2_code} (Vds={vds_mv:+.0f}mV, {dac2_code*100//255}%) × "
            f"Diff Weight W={w_val:+d} (W+={128+w_val}, W-={128-w_val}) -> ADC Output = {v:+d} LSB ({v*0.8057:+.1f} mV)"
        )
        if args.hold:
            print("STATUS: Holding (DAC_2, W) active on hardware DACs for oscilloscope probing.")
        return 0

    weights = [max(-127, min(127, int(w.strip()))) for w in args.weights.split(",") if w.strip()]

    # Mode B: Custom list of In-Data Row values (--inputs)
    if args.inputs:
        x_list = [max(-127, min(127, int(x.strip()))) for x in args.inputs.split(",") if x.strip()]
        dac_codes = [128 + x for x in x_list]
        print(
            f"Single-Ended Data Row : DAC_2[{args.row}] swept across unsigned codes {dac_codes} "
            f"(Vds = {[round(c*250.0/255.0) for c in dac_codes]} mV above 1.65V)"
        )
        hdr = (
            f"{'Diff W':>10} | {'W+/W- DAC':>11} | "
            + " | ".join(f"DAC2={128+x:3d}({(128+x)*250//255:3d}mV)" for x in x_list)
            + " |  ΔADC(Max-Min)"
        )
        print("-" * len(hdr))
        print(hdr)
        print("-" * len(hdr))
        for w in weights:
            vals = [read_cell_at_xw(client, mat_id, args.row, args.col, x, w, hold=False) for x in x_list]
            delta = vals[-1] - vals[0]
            row_str = " | ".join(f"{v:+15d}" for v in vals)
            print(f"{w:+10d} | {128+w:4d}/{128-w:<4d}   | {row_str} | {delta:+6d} ({delta*0.8057:+.1f}mV)")
        print("-" * len(hdr))
        return 0

    # Mode C: Default 3-point Single-Ended In-Data Row sweep (Min, Mid=128, Max)
    x_amp = max(1, min(127, args.x_step))
    c_low, c_mid, c_hi = 128 - x_amp, 128, 128 + x_amp
    v_low, v_mid, v_hi = round(c_low * 250.0 / 255.0), 125, round(c_hi * 250.0 / 255.0)
    print(
        f"Single-Ended Data Row : DAC_2[{args.row}] stepped across codes "
        f"{c_low} (+{v_low}mV), {c_mid} (+{v_mid}mV, 50%), {c_hi} (+{v_hi}mV)"
    )
    print("Note: Table values are measured ADC output offsets (LSB) relative to (DAC_2=128, W=0).")
    print("-" * 96)
    print(
        f"{'Diff W':>10} | {'W+ / W- DAC':>13} | "
        f"{f'DAC2={c_low}(+{v_low}mV)':>17} | {f'DAC2={c_mid}(+{v_mid}mV)':>17} | {f'DAC2={c_hi}(+{v_hi}mV)':>17} | {'ΔADC(Hi-Low)':>14}"
    )
    print("-" * 96)

    curve = client.run_single_cell_multiplier_curve(
        matrix_id=mat_id,
        row=args.row,
        col=args.col,
        x_amp=x_amp,
        weights=weights,
    )
    if not curve:
        print("ERROR: No response from hardware on MAML_CMD_PROBE_CELL (0x17).")
        return 1

    for pt in curve:
        w = pt["w"]
        w_pos = max(0, min(255, 128 + w))
        w_neg = max(0, min(255, 128 - w))
        d_lsb = pt["delta_up_down"]
        d_mv = d_lsb * 0.8057
        print(
            f"{w:+10d} | {w_pos:5d} / {w_neg:<5d} | {pt['out_x_neg']:+17d} | "
            f"{pt['out_x_zero']:+17d} | {pt['out_x_pos']:+17d} | {d_lsb:+6d} ({d_mv:+6.1f}mV)"
        )
    print("-" * 96)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
