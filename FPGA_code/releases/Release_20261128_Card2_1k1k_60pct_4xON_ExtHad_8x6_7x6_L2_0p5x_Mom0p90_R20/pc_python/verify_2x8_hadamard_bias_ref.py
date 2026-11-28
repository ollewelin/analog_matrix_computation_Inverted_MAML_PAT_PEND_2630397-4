#!/usr/bin/env python3
"""
verify_2x8_hadamard_bias_ref.py
Silicon sanity check for the extended 2x8 = 16-pulse Sylvester H_8 Hadamard
table supporting Matrix 3 (8x6, including Row 6 Clock/Bias and Row 7 Ref)
and Matrix 8 (7x6, including Row 6 Bias).
"""

import struct
import sys
import time
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from gui.udp_client import MamlUdpClient
from FPGA_code.config.w3_staircase_pattern import build_center_weights_payload, get_staircase_config
from FPGA_code.scripts.run_card1_extended_thermal_sweep import (
    calibrate_fixed_slice_params,
    drain_udp,
    execute_hardware_beat,
)
from FPGA_code.scripts.verify_and_guard_version import ensure_version_guard


def main() -> int:
    ensure_version_guard(expected_hw="0x20261128", expected_sw="v2.2-MAML")

    k_default_m33 = np.array([
        [+84, -12, +36,  -8, +48, -12],
        [-16, +80, -12, +32,  -8, +44],
        [+40, -16, +84, -12, +36,  -8],
        [ -4, +40,  -8, +72, -12, +44],
        [+44, -12, +28, -12, +76,  -8],
        [-28, +32,  -4, +40,  -8, +82],
    ])
    m_msb = np.round(k_default_m33 * (50.0 / 84.0)).astype(np.int32)
    w_msb_si = m_msb.tolist()

    client = MamlUdpClient(host="192.168.1.50", port=5000, timeout=1.0)
    try:
        client.set_heaters(False, [0, 0, 0, 0])
        client.clear_w33_hidden_offset()
        time.sleep(0.03)
        client.set_config(
            mode=0, jumper_mode=3, led_switches=3, max_meas_win_pct=100, hadamard_khz=500,
            inner_loop_n=100, seed_pct=28, seed_mode=1, w_hid_mag=0, trim_hid_mag=0,
            hadamard_delay_us=5000, lr_inner_q16=int(round(0.055 * 1024.0)),
        )
        time.sleep(0.03)
        mom_q16 = int(round(0.85 * 65536.0))
        client._send_binary(0x1E, struct.pack("<BH", 7, mom_q16))
        time.sleep(0.02)
        client._send_binary(0x13, struct.pack("<BB", 1, 1))
        time.sleep(0.02)
        client.set_data_color(2, 0.0)
        client.set_gain_experiment(d_line=2, w33=1, target_gain=1.0, clamp=90)
        time.sleep(0.03)

        cfg = get_staircase_config()
        init_w_m3 = np.array(cfg["w_m3_lsb"], dtype=np.int32)
        init_w_m8 = np.array(cfg["w_m8_lsb"], dtype=np.int32)
        flat_m3 = [int(init_w_m3[r][col]) for r in range(8) for col in range(6)]
        client._send_binary(0x18, struct.pack("<B48b42b", 0, *flat_m3, *([0] * 42)))
        time.sleep(0.25)
        client._send_binary(0x18, build_center_weights_payload(1))
        time.sleep(0.25)
        drain_udp(client)

        t0 = client.get_telemetry()
        ack_miss_0 = t0.t20_h_ack_miss
        print(f"Init M3 R6: {t0.w_m3[6]} | M3 R7: {t0.w_m3[7]} | adc49: {t0.adc49_sig}")

        alpha_msb, beta_msb = calibrate_fixed_slice_params(client, w_msb_si, num_samples=16, delay_us=5000)
        client._send_binary(0x1E, struct.pack("<BB", 4, 0))
        client.set_w33_matrix(w_msb_si)

        clip_total = 0
        last_telem = None
        lr_q16 = int(round(0.055 * 1024.0))
        reg_q16 = 1920

        for _ in range(15):
            res = execute_hardware_beat(
                client, 5000, lr_q16, reg_q16,
                k_batch=1, W_mat=m_msb, alpha=alpha_msb, beta=beta_msb,
            )
            telem = res["telem"]
            last_telem = telem
            if getattr(telem, "col_clip_mask", 0):
                clip_total += 1

        w_m3 = np.array(last_telem.w_m3, dtype=np.int32)
        w_m8 = np.array(last_telem.w_m8, dtype=np.int32)
        dm3 = w_m3 - init_w_m3
        dm8 = w_m8 - init_w_m8

        print("\n=== 2x8 HADAMARD SILICON SANITY CHECK (15 BEATS) ===")
        print(f"H_ACK_OK        : {last_telem.t20_h_ack_ok}")
        print(f"H_ACK_MISS delta: {last_telem.t20_h_ack_miss - ack_miss_0}")
        print(f"Clip steps      : {clip_total} / 15 (col_clip_mask=0x{last_telem.col_clip_mask:02x}, last_adc={last_telem.last_clip_adc_id})")
        print(f"M3 R0..5 max|dW|: {int(np.max(np.abs(dm3[:6])))}")
        print(f"M3 R6 (Clk/Bias): W={w_m3[6].tolist()} | dW={dm3[6].tolist()}")
        print(f"M3 R7 (Ref)     : W={w_m3[7].tolist()} | dW={dm3[7].tolist()}")
        print(f"M8 R0..5 max|dW|: {int(np.max(np.abs(dm8[:6])))}")
        print(f"M8 R6 (Bias)    : W={w_m8[6].tolist()} | dW={dm8[6].tolist()}")
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
