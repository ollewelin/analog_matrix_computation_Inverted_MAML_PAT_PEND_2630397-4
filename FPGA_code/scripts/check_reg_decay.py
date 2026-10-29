#!/usr/bin/env python3
"""
check_reg_decay.py
==================
Physical-silicon verification of the L2 weight-decay (regularization) toward the
centered W_null pedestal in MAML_CMD_BATCH_STEP (bytes 13-14, reg_lambda Q0.16).

Procedure (repeated for each lambda in --lambdas):
  1. Center weights (0x15) -> W = W_null.
  2. Run N batch steps with identical K / strata / window / LR.
  3. Read telemetry: readback of reg_lambda_q16 + mean/max |W - W_null| for M3 & M8,
     number of cells at the clamp rail.
Expected: distance from W_null shrinks as lambda grows; readback == commanded value.
"""

import argparse
import socket
import struct
import time
import numpy as np

MAGIC = 0x4D414D4C
HOST, PORT = "192.168.1.50", 5000

W_NULL_M3 = np.zeros((8, 6), dtype=int)
for c in range(6):
    W_NULL_M3[c, c] = 64
    W_NULL_M3[6, c] = 48
W_NULL_M8 = np.zeros((7, 6), dtype=int)
W_NULL_M8[:6, :] = 24


def xact(sock, pkt, retries=3):
    for _ in range(retries):
        try:
            sock.sendto(pkt, (HOST, PORT))
            data, _ = sock.recvfrom(2048)
            return data
        except socket.timeout:
            time.sleep(0.05)
    return None


def parse(data):
    w_m3 = np.frombuffer(data, dtype=np.int8, count=48, offset=110).reshape(8, 6).astype(int)
    w_m8 = np.frombuffer(data, dtype=np.int8, count=42, offset=158).reshape(7, 6).astype(int)
    reg_q16 = struct.unpack_from("<H", data, 303)[0] if len(data) >= 305 else None
    loss = struct.unpack_from("<I", data, 76)[0] / 1000.0
    return w_m3, w_m8, reg_q16, loss


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lambdas", type=float, nargs="+", default=[0.0, 0.01, 0.05])
    ap.add_argument("--steps", type=int, default=40)
    ap.add_argument("--k", type=int, default=4)
    ap.add_argument("--strata", type=int, default=1)
    ap.add_argument("--t", type=int, default=5000, help="Window in us (t_min = t_max)")
    ap.add_argument("--lr", type=float, default=0.30, help="High LR so weights move noticeably")
    ap.add_argument("--clamp", type=int, default=120)
    args = ap.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(4.0)
    lr_q16 = max(32, min(4096, int(round(1024 * args.lr))))

    # Nominal 1/1 condition, clamp
    xact(sock, struct.pack("<IBBBHB", MAGIC, 0x1C, 1, 1, 256, args.clamp))

    print("=" * 86)
    print(f"L2 DECAY VERIFICATION | K={args.k} strata={args.strata} t={args.t}us LR={args.lr} "
          f"(Q16={lr_q16}) steps={args.steps}")
    print("=" * 86)
    print(f"{'lambda':>8} | {'readback':>9} | {'M3 mean|dW|':>11} {'max':>4} | "
          f"{'M8 mean|dW|':>11} {'max':>4} | {'rail M3/M8':>10} | {'loss':>8}")
    print("-" * 86)

    for lam in args.lambdas:
        reg_q16 = max(0, min(16384, int(round(65536 * lam))))
        xact(sock, struct.pack("<IB", MAGIC, 0x15))
        time.sleep(0.05)
        pkt = struct.pack("<IB", MAGIC, 0x1B) + struct.pack(
            "<BBHHHH", args.k, args.strata, args.t, args.t, lr_q16, reg_q16)
        data = None
        for _ in range(args.steps):
            d = xact(sock, pkt)
            if d:
                data = d
        if data is None:
            print(f"{lam:8.4f} | NO RESPONSE")
            continue
        w3, w8, rb, loss = parse(data)
        d3 = np.abs(w3 - W_NULL_M3)
        d8 = np.abs(w8 - W_NULL_M8)
        rail3 = int(np.sum(np.abs(w3) >= args.clamp - 2))
        rail8 = int(np.sum(np.abs(w8) >= args.clamp - 2))
        rb_str = f"{rb}" if rb is not None else "n/a"
        ok = "" if rb == reg_q16 else "  <-- MISMATCH"
        print(f"{lam:8.4f} | {rb_str:>9} | {d3.mean():11.2f} {d3.max():4d} | "
              f"{d8.mean():11.2f} {d8.max():4d} | {rail3:4d}/{rail8:<5d} | {loss:8.0f}{ok}")

    xact(sock, struct.pack("<IB", MAGIC, 0x15))
    print("-" * 86)
    print("[+] Weights re-centered. Hardware idle.")


if __name__ == "__main__":
    main()

