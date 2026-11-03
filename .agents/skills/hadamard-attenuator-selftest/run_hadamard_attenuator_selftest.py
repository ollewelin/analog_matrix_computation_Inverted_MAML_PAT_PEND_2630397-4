#!/usr/bin/env python3
"""
run_hadamard_attenuator_selftest.py
Inverted MAML (Patent Pending SE 2630397-4) - Open Science Hardware

Deterministiskt och robust hårdvarusjälvtest för Inverted MAML Jumper-headers & Dämpsats:
- Signalväg: DAC(2) -> Matris 3 -> ColTIA_3 -> Sigmoid 4 [ADC45] -> OP-nedskalning
             -> Matris 8 -> ColTIA_8 -> Sigmoid 10 / Header H1$CBB -> Dämpsats 1k/5.1k -> ADC(49).
- Håller DAC(2) och Matris 3 på fast, stabil aktiv diagonal så att alla 6 rader in i Matris 8 drivs hälsosamt.
- Inga slumpmässiga vitbrusvektorer (eliminerar lotterieffekten helt).
- Mäter både 500 kHz Walsh-Hadamard demodulering (FWHT rader 9..14 för Matris 8)
  och direkt kontrollerad M8-viktstegning (-80 till +80 LSB).
"""

import sys
import os
import time
import math
import struct
from pathlib import Path
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if not (REPO_ROOT / "gui").exists():
    REPO_ROOT = Path(__file__).resolve().parent.parent
if not (REPO_ROOT / "gui").exists():
    REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from gui.udp_client import (
    MamlUdpClient,
    MAML_CMD_CENTER_WEIGHTS,
)
from FPGA_code.scripts.verify_and_guard_version import ensure_version_guard

HEADER_NAMES = [
    "H1$CBB8",   # Ch 0 (1:a headern)
    "H1$CBB10",  # Ch 1 (2:a headern)
    "H1$CBB11",  # Ch 2 (3:e headern)
    "H1$CBB12",  # Ch 3 (4:e headern)
    "H1$CBB13",  # Ch 4 (5:e headern)
    "H1$CBB14",  # Ch 5 (6:e headern)
]


def pack_payload(m3: list[list[int]], m8: list[list[int]]) -> bytes:
    flat_m3 = [max(-120, min(120, int(m3[r][c]))) for r in range(8) for c in range(6)]
    flat_m8 = [max(-120, min(120, int(m8[r][c]))) for r in range(7) for c in range(6)]
    return struct.pack("<B48b42b", 1, *flat_m3, *flat_m8)


def run_selftest(host: str = "192.168.1.50", port: int = 5000) -> dict:
    ensure_version_guard(host=host, port=port)
    client = MamlUdpClient(host=host, port=port, timeout=3.0)

    print("\n" + "=" * 98)
    print("INVERTED MAML: DETERMINISTISKT JUMPER- OCH DÄMPSATSSJÄLVTEST")
    print(f"Hårdvarumål: {host}:{port} | Trion T120 Master SoC + T20 Coprocessor")
    print("=" * 98)
    print("Signalväg: DAC(2) -> [Matris 3] -> [ColTIA_3] -> [Sigmoid 4 / ADC45] -> [OP-nedskalning]")
    print("           -> [Matris 8] -> [ColTIA_8] -> [Sigmoid 10 / Header H1$CBB] -> [Dämpsats 1k/5.1k] -> [ADC49]\n")

    # 1. Konfigurera fast aktiv diagonal drivning på Matris 3 så att Sigmoid 4 / ADC45 ger frisk signal in till Matris 8
    m3_diag = [[0] * 6 for _ in range(8)]
    for c in range(6):
        m3_diag[c][c] = 60  # +60 LSB diagonal överföring

    m8_zero = [[0] * 6 for _ in range(7)]
    client._send_binary(MAML_CMD_CENTER_WEIGHTS, pack_payload(m3_diag, m8_zero))
    time.sleep(0.04)

    t0 = client.get_telemetry()
    adc45_init = t0.adc45_sig if t0 else [0] * 6
    print(f"[*] Verifierar aktiv signal ut ur Sigmoid 4 vid ADC(45): {adc45_init} LSB")

    # -------------------------------------------------------------------------
    # TEST 1: 500 kHz Walsh-Hadamard Carrier Extraction för Matris 8 (FWHT rader 9..14)
    # -------------------------------------------------------------------------
    print("[1/2] Mäter 500 kHz Walsh-Hadamard bärvågsrespons på Matris 8 (FWHT rader 9..14)...")
    m8_hadamard_test = [[60] * 6 for _ in range(7)]
    client._send_binary(MAML_CMD_CENTER_WEIGHTS, pack_payload(m3_diag, m8_hadamard_test))
    time.sleep(0.04)

    diag_res = client.diag_hadamard(mode=0, en_mask=0x7FFF)
    hadamard_ptp = [0.0] * 6
    hadamard_m8_carrier = [0.0] * 6

    if diag_res:
        cap49 = np.array(diag_res.cap49)
        fwht49 = np.array(diag_res.fwht49)
        for c in range(6):
            ptp = float(np.ptp(cap49[:14, c]))
            # Matris 8 känsligheter ligger på FWHT rader 9..14 (maml_platform.c sens_m8_raw)
            m8_sens = [abs(float(fwht49[r, c])) for r in range(9, 15)]
            carrier_peak = max(m8_sens) if m8_sens else 0.0
            hadamard_ptp[c] = round(ptp, 1)
            hadamard_m8_carrier[c] = round(carrier_peak, 1)

    # -------------------------------------------------------------------------
    # TEST 2: Deterministisk Matris 8 viktstegning (-80 till +80 LSB) med FAST insignal
    # -------------------------------------------------------------------------
    print("[2/2] Mäter direkt analog överföring över Matris 8 (-80 till +80 LSB, fast DAC2/M3)...")
    m8_deltas = [0.0] * 6

    for c in range(6):
        # State A: W8 på kolumn c = +80 på alla rader
        m8_hi = [[0] * 6 for _ in range(7)]
        for r in range(6):
            m8_hi[r][c] = 80
        client._send_binary(MAML_CMD_CENTER_WEIGHTS, pack_payload(m3_diag, m8_hi))
        time.sleep(0.04)
        v_hi = np.median([client.get_telemetry().adc49_sig[c] for _ in range(5)])

        # State B: W8 på kolumn c = -80 på alla rader
        m8_lo = [[0] * 6 for _ in range(7)]
        for r in range(6):
            m8_lo[r][c] = -80
        client._send_binary(MAML_CMD_CENTER_WEIGHTS, pack_payload(m3_diag, m8_lo))
        time.sleep(0.04)
        v_lo = np.median([client.get_telemetry().adc49_sig[c] for _ in range(5)])

        delta = v_hi - v_lo
        m8_deltas[c] = round(float(delta), 1)

    # Återställ neutralt tillstånd på Matris 8
    client._send_binary(MAML_CMD_CENTER_WEIGHTS, pack_payload(m3_diag, m8_zero))
    time.sleep(0.04)

    # -------------------------------------------------------------------------
    # DIAGNOS & SAMMANSTÄLLNING
    # -------------------------------------------------------------------------
    print("\n" + "=" * 98)
    print("SJÄLVTESTRAPPORT: STATUS FÖR JUMPERS & DÄMPSATSER PER KANAL")
    print("=" * 98)
    print(f"{'Kanal':<6} | {'Header':<10} | {'M8 Förstärkning':<18} | {'Hadamard M8 Peak':<18} | {'Status':<24}")
    print("-" * 98)

    disconnected_channels = []

    for c in range(6):
        h_name = HEADER_NAMES[c]
        d_str = f"{m8_deltas[c]:+6.1f} LSB"
        car_str = f"{hadamard_m8_carrier[c]:5.1f} LSB"

        is_connected = (abs(m8_deltas[c]) >= 80.0) or (hadamard_m8_carrier[c] >= 20.0)

        if is_connected:
            status = "✅ INKOPPLAD (Frisk länk)"
        else:
            status = "❌ URKOPPLAD (Öppen krets / Avbrott)"
            disconnected_channels.append((c, h_name))

        print(f"Ch {c:<3} | {h_name:<10} | {d_str:<18} | {car_str:<18} | {status:<24}")

    print("=" * 98)
    if disconnected_channels:
        print(f"[!] DETEKTERADE {len(disconnected_channels)} URKOPPLAD(E) / BRUTNA KANAL(ER):")
        for ch, h_name in disconnected_channels:
            print(f"    -> Kanal {ch} (Header {h_name}): Ingen analog ström når dämparen / ADC(49).")
            print(f"       Kontrollera att jumpern sluter Pin 1-2 (Mode A) eller Pin 2-3 (Mode C),")
            print(f"       samt att dämpsatsmotståndet (1k eller 5.1k) har hel lödning.\n")
    else:
        print("[+] ALLA 6 ANALOGA KANALER ÄR INKOPPLADE OCH FUNGERAR PERFEKT!\n")
    print("=" * 98 + "\n")

    return {
        "m8_deltas": m8_deltas,
        "hadamard_carrier": hadamard_m8_carrier,
        "hadamard_ptp": hadamard_ptp,
        "disconnected": disconnected_channels,
    }


if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else "192.168.1.50"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
    run_selftest(host=host, port=port)
