#!/usr/bin/env python3
"""
maml_w33_and_color_ctl.py - Frozen W33 Matrix Loader & In-Data Noise Equalizer CLI
Inverted MAML Hardware Controller | Patent Pending SE 2630397-4 (Open Science Hardware)

Features:
1. Telemetry inspection of active frozen Matrix 33 weights and current Noise Equalizer mode.
2. Dynamic loading of custom frozen W33 matrices under runtime, with instant readback and verification.
3. Resetting back to factory default k_default_m33.
4. Runtime configuration of the In-Data Noise Equalizer:
   - Mode 0: WHITE (Flat multivariate white noise)
   - Mode 1: PINK  (1/f spectral rolloff across channel dimensions)
   - Mode 2: RED   (1/f^2 Brownian random walk across row activations)
   - Mode 3: LLM   (Kac-Murdock-Szegö AR(1) spatial correlation rho^|i-j|)
   - Mode 4: GELU  (Correlated Toeplitz with rectified GELU/ReLU sparsity)
5. Continuous spatial correlation rho tuning (0.0 .. 1.0).
"""

import sys
import time
import argparse
import numpy as np
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from gui.udp_client import (
    MamlUdpClient,
    COLOR_WHITE,
    COLOR_PINK,
    COLOR_RED,
    COLOR_LLM_TOEPLITZ,
    COLOR_LLM_SPARSE_GELU,
)

COLOR_NAMES = {
    COLOR_WHITE: "WHITE (Flat Independent)",
    COLOR_PINK: "PINK (1/f Spectral Rolloff)",
    COLOR_RED: "RED (1/f^2 Brownian Walk)",
    COLOR_LLM_TOEPLITZ: "LLM_TOEPLITZ (Kac-Murdock-Szegö AR(1))",
    COLOR_LLM_SPARSE_GELU: "LLM_SPARSE_GELU (Correlated + Rectified Sparsity)",
}

COLOR_MAP = {
    "white": COLOR_WHITE,
    "pink": COLOR_PINK,
    "red": COLOR_RED,
    "llm": COLOR_LLM_TOEPLITZ,
    "toeplitz": COLOR_LLM_TOEPLITZ,
    "gelu": COLOR_LLM_SPARSE_GELU,
    "sparse": COLOR_LLM_SPARSE_GELU,
}


def print_telemetry_status(tel, client):
    print("=" * 80)
    print("T120 MASTER SOC TELEMETRY STATUS (v2.2-MAML)")
    print("=" * 80)
    print(f"Connection Target      : {client.host}:{client.port}")
    print(f"Run Mode               : {tel.mode} ({'TRAIN_BASE' if tel.mode==1 else 'OPERATIONAL' if tel.mode==2 else 'IDLE'})")
    print(f"Refresh Counter        : {tel.refresh_cnt}")
    print(f"Comp Centered / Active : {'YES' if tel.connected_hw else 'NO'}")
    print(f"ENOB (Sustained/Comp)  : {tel.enob_bits:.2f} bits (Uncomp: {tel.enob_uncomp_bits:.2f} bits)")
    print("-" * 80)
    color_desc = COLOR_NAMES.get(tel.color_mode, f"UNKNOWN ({tel.color_mode})")
    print(f"Noise Equalizer Mode   : [{tel.color_mode}] {color_desc}")
    print(f"Spatial Correlation rho: {tel.color_rho:.3f} (Q8 = {tel.color_rho_q8})")
    print(f"Active x_ref vector    : {tel.x_ref}")
    print(f"Active z_target vector : {tel.z_target}")
    print("-" * 80)
    w33_status = "CUSTOM LOADED" if tel.w33_is_custom else "FACTORY DEFAULT (k_default_m33)"
    print(f"Frozen Matrix 33 State : {w33_status} (Divisor = {tel.w33_div}x)")
    print("Frozen Matrix 33 Weights (6x6 DAC Offsets [-120..+120]):")
    w_mat = np.array(tel.w_m33, dtype=np.int32)
    for r in range(6):
        row_str = "  ".join(f"{w_mat[r, c]:+4d}" for c in range(6))
        print(f"  Row {r}: [ {row_str} ]")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="Inspect and control frozen W33 weights and In-Data Noise Equalizer on T120 Master SoC."
    )
    parser.add_argument("--host", default="192.168.1.50", help="T120 SoC IP address (default: 192.168.1.50)")
    parser.add_argument("--port", type=int, default=5000, help="T120 SoC UDP port (default: 5000)")
    parser.add_argument("--show", action="store_true", help="Display active telemetry, W33 matrix, and equalizer state")
    parser.add_argument("--w33-default", action="store_true", help="Reset Matrix 33 to factory default k_default_m33")
    parser.add_argument("--w33-preset", choices=["eye", "zeros", "invert", "permute", "strong_diag"], help="Apply standard W33 test preset")
    parser.add_argument("--w33-file", type=str, help="Load custom 6x6 W33 matrix from CSV/text/npy file")
    parser.add_argument("--color", choices=["white", "pink", "red", "llm", "toeplitz", "gelu", "sparse"], help="Set In-Data noise equalizer color mode")
    parser.add_argument("--rho", type=float, default=None, help="Set spatial correlation coefficient rho [0.0 .. 1.0]")
    parser.add_argument("--rand-tick", action="store_true", help="Trigger single autonomous white noise refresh tick")

    args = parser.parse_args()

    client = MamlUdpClient(host=args.host, port=args.port, timeout=0.8)

    # Check connection
    ver_info = client.get_versions()
    if not ver_info.get("status"):
        print(f"[!] ERROR: Cannot communicate with T120 SoC at {args.host}:{args.port}")
        sys.exit(1)

    print(f"Connected to T120: {ver_info.get('sw_version')} | {ver_info.get('hw_id')} (HW: {ver_info.get('hw_version')})")

    # 1. Reset W33 to default if requested
    if args.w33_default:
        print("[*] Sending command to RESET Matrix 33 to factory default (k_default_m33)...")
        ok = client.set_w33_matrix(None)
        if ok:
            print("[+] Matrix 33 successfully reset to default.")
        else:
            print("[!] Failed to send reset command.")

    # 2. Preset W33 matrices
    elif args.w33_preset:
        preset_mat = None
        if args.w33_preset == "eye":
            preset_mat = (np.eye(6, dtype=np.int8) * 80).tolist()
        elif args.w33_preset == "zeros":
            preset_mat = np.zeros((6, 6), dtype=np.int8).tolist()
        elif args.w33_preset == "invert":
            # Invert default weights
            default_m33 = [
                [ +76, -20, +28,  -4, +44, -36 ],
                [ -20, +84, -12, +44,  -4, +36 ],
                [ +36,  -4, +80, -16, +32,  -4 ],
                [  -4, +40,  -8, +72, -12, +44 ],
                [ +44, -12, +28, -12, +76,  -8 ],
                [ -28, +32,  -4, +40,  -8, +82 ]
            ]
            preset_mat = [[-v for v in row] for row in default_m33]
        elif args.w33_preset == "permute":
            # Circular row shift
            default_m33 = [
                [ +76, -20, +28,  -4, +44, -36 ],
                [ -20, +84, -12, +44,  -4, +36 ],
                [ +36,  -4, +80, -16, +32,  -4 ],
                [  -4, +40,  -8, +72, -12, +44 ],
                [ +44, -12, +28, -12, +76,  -8 ],
                [ -28, +32,  -4, +40,  -8, +82 ]
            ]
            preset_mat = default_m33[1:] + default_m33[:1]
        elif args.w33_preset == "strong_diag":
            preset_mat = [
                [ 100, -10,  -5,   0,   0,   0 ],
                [ -10, 100, -10,  -5,   0,   0 ],
                [  -5, -10, 100, -10,  -5,   0 ],
                [   0,  -5, -10, 100, -10,  -5 ],
                [   0,   0,  -5, -10, 100, -10 ],
                [   0,   0,   0,  -5, -10, 100 ]
            ]

        print(f"[*] Loading preset '{args.w33_preset}' into Matrix 33...")
        ok = client.set_w33_matrix(preset_mat)
        if ok:
            print(f"[+] Preset '{args.w33_preset}' successfully loaded.")
        else:
            print("[!] Failed to send preset matrix.")

    # 3. Custom file
    elif args.w33_file:
        file_path = Path(args.w33_file)
        if not file_path.exists():
            print(f"[!] File not found: {file_path}")
            sys.exit(1)
        if file_path.suffix == ".npy":
            mat = np.load(file_path)
        else:
            mat = np.loadtxt(file_path, delimiter="," if "," in file_path.read_text() else None)
        if mat.shape != (6, 6):
            print(f"[!] Matrix must be exactly (6, 6), got {mat.shape}")
            sys.exit(1)
        mat_int = np.clip(np.round(mat).astype(int), -120, 120).tolist()
        print(f"[*] Loading custom (6, 6) matrix from {file_path}...")
        ok = client.set_w33_matrix(mat_int)
        if ok:
            print(f"[+] Custom matrix from {file_path} successfully loaded.")
        else:
            print("[!] Failed to send custom matrix.")

    # 4. Color Equalizer
    if args.color or args.rho is not None:
        tel = client.get_telemetry()
        current_mode = tel.color_mode if tel else COLOR_WHITE
        current_rho = tel.color_rho if tel else 0.70

        target_mode = COLOR_MAP.get(args.color, current_mode) if args.color else current_mode
        target_rho = args.rho if args.rho is not None else current_rho
        target_rho = max(0.0, min(1.0, target_rho))

        print(f"[*] Setting Noise Equalizer: Mode={COLOR_NAMES.get(target_mode)} | rho={target_rho:.3f}...")
        ok = client.set_data_color(target_mode, target_rho)
        if ok:
            print("[+] Noise Equalizer successfully updated.")
        else:
            print("[!] Failed to set Noise Equalizer.")

    # 5. Trigger new random vector
    if args.rand_tick:
        print("[*] Triggering fresh noise vector...")
        client.randomize_in_data_rows()

    # Always fetch fresh telemetry to verify
    time.sleep(0.05)
    tel = client.get_telemetry()
    if tel:
        print_telemetry_status(tel, client)
    else:
        print("[!] Warning: Could not retrieve telemetry readback.")

    client.close()


if __name__ == "__main__":
    main()

