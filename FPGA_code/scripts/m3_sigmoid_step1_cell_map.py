#!/usr/bin/env python3
"""
m3_sigmoid_step1_cell_map.py
============================
STEG 1 — Karakterisering av ALLA korspunkter i Matrix 3 (8 rader x 6 kolumner = 48 celler)
genom den analoga sigmoid-aktiveringen (Ref 4), utläst på ADC_45[col].

Protokoll (fysiskt kisel, 192.168.1.50:5000, endast t = 5.0 ms):
  - En ensam cell (r, c) aktiv, alla andra vikter = 0 (firmware maml_probe_single_cell).
  - X-axel: Weight W3[r][c] svept -127 .. +127.
  - Y-axel: ADC_45[c] delta (LSB) relativt kvarvarande baslinje (W=0, X=0).
  - 5 kurvor (DAC_2 data-nivå): X = -127 (blå), -64 (röd), 0 (grön), +64 (orange), +127 (gul).
  - N repetitioner per punkt (default 8) -> medel + standardavvikelse (50 Hz-brus / stokastik).

Analys per cell:
  - Dynamik (swing) på negativ resp. positiv W-sida för X=±127 / ±64.
  - Ryckighet (jerk): residual mot glatt polynomanpassning + mätbrus (std över repetitioner).
  - Böj (bend): max |andraderivata| och var den ligger (W-position).
  - Polaritetspoäng: score = dynamik / (1 + ryckighet/10) -> rekommenderad sida (+ eller -).

Utdata:
  FPGA_code/logs/m3_sigmoid_characterization/step1_m3_cell_map_5ms.json
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from gui.udp_client import MamlUdpClient, MAT_M3  # noqa: E402

OUT_DIR = REPO_ROOT / "FPGA_code" / "logs" / "m3_sigmoid_characterization"
OUT_DIR.mkdir(parents=True, exist_ok=True)

WEIGHTS = [-127, -112, -96, -80, -64, -48, -32, -16, 0, 16, 32, 48, 64, 80, 96, 112, 127]
LEVELS = [-127, -64, 0, 64, 127]
SNAP_US = 5000


def probe(client, r, c, x_amp, w, retries=6):
    for _ in range(retries):
        try:
            res = client.probe_cell_xw(MAT_M3, r, c, x_amp=x_amp, w_fixed=w,
                                       sweep_input=True, hold=False, snap_dly_us=SNAP_US)
            if res is not None:
                return res
        except Exception:
            pass
        time.sleep(0.02)
    return None


def side_metrics(w_arr, y_mean, y_std, side):
    """Metrics for one W polarity side (including W=0)."""
    mask = (w_arr <= 0) if side == "neg" else (w_arr >= 0)
    w = w_arr[mask]
    y = y_mean[mask]
    s = y_std[mask]
    dyn = float(np.max(y) - np.min(y))
    # Glatt anpassning (3:e grads polynom) -> residual = ryckighet utöver mätbrus
    if len(w) >= 5:
        p = np.polyfit(w, y, 3)
        resid = float(np.sqrt(np.mean((y - np.polyval(p, w)) ** 2)))
    else:
        resid = 0.0
    noise = float(np.mean(s))
    # Monotoni (andel steg i dominerande riktning)
    d = np.diff(y)
    mono = float(max(np.sum(d > 0), np.sum(d < 0)) / max(1, len(d)))
    # Böj: max |andraderivata| och dess position
    if len(w) >= 3:
        d2 = np.abs(np.diff(y, 2))
        k = int(np.argmax(d2))
        bend_w = float(w[k + 1])
        bend_mag = float(d2[k])
    else:
        bend_w, bend_mag = 0.0, 0.0
    jerk = float(np.sqrt(resid ** 2 + noise ** 2))
    score = dyn / (1.0 + jerk / 10.0) * mono
    return {
        "dynamic_lsb": round(dyn, 2),
        "fit_residual_lsb": round(resid, 2),
        "noise_std_lsb": round(noise, 2),
        "jerk_lsb": round(jerk, 2),
        "monotonicity": round(mono, 3),
        "bend_w": bend_w,
        "bend_mag_lsb": round(bend_mag, 2),
        "score": round(score, 2),
    }


def main():
    ap = argparse.ArgumentParser(description="M3 Sigmoid Step 1: 48-cell map via ADC45 at 5.0 ms")
    ap.add_argument("--host", default="192.168.1.50")
    ap.add_argument("--port", type=int, default=5000)
    ap.add_argument("--reps", type=int, default=8)
    ap.add_argument("--rows", default="0-7")
    ap.add_argument("--cols", default="0-5")
    ap.add_argument("--out", default=str(OUT_DIR / "step1_m3_cell_map_5ms.json"))
    args = ap.parse_args()

    def rng(s):
        a, b = s.split("-") if "-" in s else (s, s)
        return list(range(int(a), int(b) + 1))

    rows, cols = rng(args.rows), rng(args.cols)
    client = MamlUdpClient(host=args.host, port=args.port, timeout=0.6)
    print(f"[*] Target: {client.query_version().strip()}")

    client.set_config(mode=0, jumper_mode=3, led_switches=3, max_meas_win_pct=100, hadamard_khz=500,
                      inner_loop_n=100, seed_pct=28, seed_mode=1, w_hid_mag=0, trim_hid_mag=0,
                      hadamard_delay_us=5000, lr_inner_q16=256)
    time.sleep(0.05)
    client.center_compensation_weights()
    time.sleep(0.05)

    ds = {
        "title": "M3 Sigmoid Step 1 — Single-Cell Map through Analog Activation (Ref 4)",
        "matrix": "M3 (8 rows x 6 cols)",
        "readout": "ADC_45[col] delta vs quiescent baseline (W=0, X=0)",
        "snap_us": SNAP_US,
        "reps": args.reps,
        "weights": WEIGHTS,
        "levels": LEVELS,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "cells": {},
    }

    t0 = time.time()
    n_cells = len(rows) * len(cols)
    k = 0
    for r in rows:
        for c in cols:
            k += 1
            # samples[level] -> list over W of list over reps
            samp = {lv: [[] for _ in WEIGHTS] for lv in LEVELS}
            for wi, w in enumerate(WEIGHTS):
                for _ in range(args.reps):
                    for amp in (127, 64):
                        res = probe(client, r, c, amp, w)
                        if res is None:
                            continue
                        samp[-amp][wi].append(res.adc45_neg[c])
                        samp[+amp][wi].append(res.adc45_pos[c])
                        samp[0][wi].append(res.adc45_zero[c])
            curves = {}
            w_arr = np.array(WEIGHTS, dtype=float)
            for lv in LEVELS:
                mean = np.array([np.mean(v) if v else np.nan for v in samp[lv]])
                std = np.array([np.std(v) if v else np.nan for v in samp[lv]])
                curves[str(lv)] = {"mean": [round(float(x), 2) for x in mean],
                                   "std": [round(float(x), 2) for x in std]}
            # Polaritetsanalys på kombinerade |X|-kurvor (X=-127, -64, +64, +127)
            pol = {}
            for side in ("neg", "pos"):
                per = {}
                for lv in (-127, -64, 64, 127):
                    m = np.array(curves[str(lv)]["mean"])
                    s = np.array(curves[str(lv)]["std"])
                    per[str(lv)] = side_metrics(w_arr, m, s, side)
                agg_score = float(np.mean([per[x]["score"] for x in per]))
                agg_dyn = float(np.mean([per[x]["dynamic_lsb"] for x in per]))
                agg_jerk = float(np.mean([per[x]["jerk_lsb"] for x in per]))
                pol[side] = {"per_level": per, "score": round(agg_score, 2),
                             "dynamic_lsb": round(agg_dyn, 2), "jerk_lsb": round(agg_jerk, 2)}
            best = "pos" if pol["pos"]["score"] >= pol["neg"]["score"] else "neg"
            ds["cells"][f"R{r}_C{c}"] = {"row": r, "col": c, "curves": curves,
                                         "polarity": pol, "recommended_side": best}
            el = time.time() - t0
            eta = el / k * (n_cells - k)
            print(f"[{k:02d}/{n_cells}] M3 R{r} C{c}: dyn-={pol['neg']['dynamic_lsb']:.0f} "
                  f"jerk-={pol['neg']['jerk_lsb']:.1f} | dyn+={pol['pos']['dynamic_lsb']:.0f} "
                  f"jerk+={pol['pos']['jerk_lsb']:.1f} -> best={best.upper()}  (ETA {eta/60:.1f} min)",
                  flush=True)
            with open(args.out, "w") as f:
                json.dump(ds, f, indent=1)

    # Kolumnsammanfattning
    summ = {}
    for c in cols:
        cells = [ds["cells"][f"R{r}_C{c}"] for r in rows]
        sn = float(np.mean([x["polarity"]["neg"]["score"] for x in cells]))
        sp = float(np.mean([x["polarity"]["pos"]["score"] for x in cells]))
        summ[f"C{c}"] = {"score_neg": round(sn, 2), "score_pos": round(sp, 2),
                         "recommended_side": "pos" if sp >= sn else "neg"}
    ds["column_summary"] = summ
    ds["duration_s"] = round(time.time() - t0, 1)
    with open(args.out, "w") as f:
        json.dump(ds, f, indent=1)
    print(f"[+] Steg 1 klart på {ds['duration_s']/60:.1f} min -> {args.out}")
    for c, v in summ.items():
        print(f"    {c}: score- = {v['score_neg']:.1f}  score+ = {v['score_pos']:.1f}  -> {v['recommended_side'].upper()}")


if __name__ == "__main__":
    main()

