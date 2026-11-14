#!/home/olle/anaconda3/bin/python
"""
analog_hyperparam_model.py
==========================
Mathematical Physics + Trend-Curve Surrogate Model for Inverted MAML Hyperparameter Generation.

Reads completed thermal bit-slicing JSON logs, extracts ONLY Warm-Phase Trend Curves
(Heater ON: Warm ON vs Warm OFF), evaluates convergence, ON-vs-OFF step contrast, jitter,
and clamp anti-windup recovery, and fits a Physics-Space Gaussian Process (GP-UCB) +
trend-diagnostic generator to propose optimal (lr, l2_reg, momentum, clamp) for the next round.

Strictly offline hyperparameter optimization only; never modifies runtime targets or calibration.
"""

from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple
import numpy as np


def _rolling_mean(arr: np.ndarray, win: int = 15) -> np.ndarray:
    if len(arr) == 0:
        return arr.copy()
    w = min(win, len(arr))
    if w < 3:
        return arr.copy()
    pad_l = w // 2
    pad_r = w - 1 - pad_l
    padded = np.pad(arr, (pad_l, pad_r), mode="edge")
    kernel = np.ones(w, dtype=np.float64) / float(w)
    return np.convolve(padded, kernel, mode="valid")


def _lin_slope_per_min(times_s: np.ndarray, vals: np.ndarray) -> float:
    if len(times_s) < 5:
        return 0.0
    dt = times_s - times_s[0]
    if float(np.ptp(dt)) < 1e-3:
        return 0.0
    p = np.polyfit(dt, vals, 1)
    return float(p[0] * 60.0)


def _pchip_eval(x: np.ndarray, y: np.ndarray, xq: np.ndarray) -> np.ndarray:
    """1D Fritsch-Carlson shape-preserving piecewise cubic Hermite interpolation."""
    n = len(x)
    if n == 0:
        return np.zeros_like(xq, dtype=np.float64)
    if n == 1:
        return np.full_like(xq, float(y[0]), dtype=np.float64)
    if n == 2:
        return np.interp(xq, x, y)

    h = np.diff(x)
    delta = np.diff(y) / np.maximum(1e-9, h)
    d = np.zeros(n, dtype=np.float64)

    for k in range(1, n - 1):
        if delta[k - 1] * delta[k] > 0.0:
            w1 = 2.0 * h[k] + h[k - 1]
            w2 = h[k] + 2.0 * h[k - 1]
            d[k] = (w1 + w2) / (w1 / delta[k - 1] + w2 / delta[k])

    d[0] = ((2.0 * h[0] + h[1]) * delta[0] - h[0] * delta[1]) / max(1e-9, h[0] + h[1])
    if d[0] * delta[0] <= 0.0:
        d[0] = 0.0
    elif abs(d[0]) > 3.0 * abs(delta[0]):
        d[0] = 3.0 * delta[0]

    d[-1] = ((2.0 * h[-1] + h[-2]) * delta[-1] - h[-1] * delta[-2]) / max(1e-9, h[-1] + h[-2])
    if d[-1] * delta[-1] <= 0.0:
        d[-1] = 0.0
    elif abs(d[-1]) > 3.0 * abs(delta[-1]):
        d[-1] = 3.0 * delta[-1]

    out = np.empty_like(xq, dtype=np.float64)
    for idx, xv in enumerate(xq):
        if xv <= x[0]:
            out[idx] = y[0]
        elif xv >= x[-1]:
            out[idx] = y[-1] + d[-1] * (xv - x[-1]) * 0.25
        else:
            k = int(np.searchsorted(x, xv, side="right") - 1)
            k = max(0, min(n - 2, k))
            hk = max(1e-9, h[k])
            s = (xv - x[k]) / hk
            h00 = 2.0 * s**3 - 3.0 * s**2 + 1.0
            h10 = s**3 - 2.0 * s**2 + s
            h01 = -2.0 * s**3 + 3.0 * s**2
            h11 = s**3 - s**2
            out[idx] = h00 * y[k] + h10 * hk * d[k] + h01 * y[k + 1] + h11 * hk * d[k + 1]
    return out


def _fit_thermal_baseline(hist: List[dict]) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Fits the continuous uncompensated thermal drift curve E_base(t) & ln(L_base(t))
    anchored on Cold OFF (just before Heater ON) and binned medians of all Warm OFF phases.
    """
    heat_recs = [r for r in hist if r.get("heater_on", False)]
    if not heat_recs:
        return np.array([]), np.array([]), np.array([])
    t_heat_on = float(heat_recs[0]["elapsed_s"])

    anchors_t: List[float] = []
    anchors_e: List[float] = []
    anchors_l: List[float] = []

    cold_off = [
        r for r in hist
        if (not r.get("heater_on", False))
        and (not r.get("reglering_on", False))
        and float(r["elapsed_s"]) <= t_heat_on + 1e-6
    ]
    if cold_off:
        tail = cold_off[len(cold_off) // 2:] if len(cold_off) >= 6 else cold_off
        e_c = float(np.median([float(r["combined_enob_raw"]) for r in tail]))
        l_c = float(np.median([math.log(max(1.0, float(r["loss_msb"]) + float(r["loss_lsb"]))) for r in tail]))
        anchors_t.append(t_heat_on)
        anchors_e.append(e_c)
        anchors_l.append(l_c)

    off_map: Dict[int, List[dict]] = {}
    for r in heat_recs:
        if not r.get("reglering_on", False):
            off_map.setdefault(int(r["phase_idx"]), []).append(r)

    for pidx in sorted(off_map.keys()):
        recs = off_map[pidx]
        if len(recs) > 8:
            recs = recs[3:]  # Skip immediate W8=0 switching transient
        n = len(recs)
        nbins = min(4, max(1, n // 15))
        for b in range(nbins):
            i0 = (b * n) // nbins
            i1 = ((b + 1) * n) // nbins
            seg = recs[i0:i1]
            if not seg:
                continue
            tb = float(np.median([float(r["elapsed_s"]) for r in seg]))
            eb = float(np.median([float(r["combined_enob_raw"]) for r in seg]))
            lb = float(np.median([math.log(max(1.0, float(r["loss_msb"]) + float(r["loss_lsb"]))) for r in seg]))
            if not anchors_t or tb > anchors_t[-1] + 0.5:
                anchors_t.append(tb)
                anchors_e.append(eb)
                anchors_l.append(lb)

    return (
        np.array(anchors_t, dtype=np.float64),
        np.array(anchors_e, dtype=np.float64),
        np.array(anchors_l, dtype=np.float64),
    )


def extract_warm_trend_metrics(log_path: str) -> Dict[str, Any]:
    with open(log_path, "r") as f:
        data = json.load(f)

    meta = data.get("metadata", {})
    hist = data.get("history", [])
    lr = float(meta.get("lr", 0.03))
    l2_reg = int(meta.get("l2_reg", 1536))
    momentum = float(meta.get("momentum", 0.90) if meta.get("momentum") is not None else 0.90)
    clamp = int(meta.get("clamp_lsb", 75))

    # Fit continuous thermal drift curve E_base(t), L_base(t) across Cold OFF -> Warm OFF
    base_t, base_e, base_lnL = _fit_thermal_baseline(hist)

    # Group strictly by warm phase index
    phase_map: Dict[int, List[dict]] = {}
    for rec in hist:
        if rec.get("heater_on", False):
            pidx = int(rec["phase_idx"])
            phase_map.setdefault(pidx, []).append(rec)

    sorted_pidxs = sorted(phase_map.keys())
    on_phases = []
    off_phases = []

    for pidx in sorted_pidxs:
        recs = phase_map[pidx]
        if len(recs) < 10:
            continue
        reg_on = bool(recs[0].get("reglering_on", False))
        t = np.array([float(r["elapsed_s"]) for r in recs], dtype=np.float64)
        enob = np.array([float(r["combined_enob_raw"]) for r in recs], dtype=np.float64)
        loss = np.array([float(r["loss_msb"]) + float(r["loss_lsb"]) for r in recs], dtype=np.float64)
        n = len(recs)

        e_base = _pchip_eval(base_t, base_e, t) if len(base_t) >= 2 else np.full_like(enob, float(np.mean(enob)))
        l_base = np.exp(_pchip_eval(base_t, base_lnL, t)) if len(base_t) >= 2 else np.full_like(loss, float(np.mean(loss)))
        detr_enob = enob - e_base

        trend = _rolling_mean(enob, win=15)
        detr_trend = _rolling_mean(detr_enob, win=15)
        jitter = float(np.std(enob - trend))

        q_start = max(5, min(15, n // 6))
        q_late_start = max(q_start, int(0.60 * n))

        start_enob = float(np.mean(enob[:q_start]))
        late_enob = float(np.mean(enob[q_late_start:]))
        start_loss = float(np.mean(loss[:q_start]))
        late_loss = float(np.mean(loss[q_late_start:]))
        mean_enob = float(np.mean(enob))
        mean_loss = float(np.mean(loss))

        late_detr_lift = float(np.mean(detr_enob[q_late_start:]))
        late_detr_loss_ratio = float(np.exp(np.mean(np.log(np.maximum(1.0, l_base[q_late_start:]) / np.maximum(1.0, loss[q_late_start:])))))

        # Slope & climb on BOTH detrended (relative to continuous thermal curve) and raw signals
        idx_15 = max(1, int(0.15 * n))
        slope_full = _lin_slope_per_min(t, enob)
        slope_post = _lin_slope_per_min(t[idx_15:], detr_enob[idx_15:])
        trend_end_minus_min_early = float(np.mean(detr_trend[-min(15, n):]) - np.min(detr_trend[:max(q_start, int(0.35 * n))]))

        w8_max_series = np.array([
            max(abs(r["w8_msb_range"][0]), abs(r["w8_msb_range"][1]),
                abs(r["w8_lsb_range"][0]), abs(r["w8_lsb_range"][1]))
            for r in recs
        ], dtype=np.float64)
        w3_max_series = np.array([
            max(abs(r.get("w3_msb_range", [0, 0])[0]), abs(r.get("w3_msb_range", [0, 0])[1]),
                abs(r.get("w3_lsb_range", [0, 0])[0]), abs(r.get("w3_lsb_range", [0, 0])[1]))
            for r in recs
        ], dtype=np.float64)

        w8_msb_zero_bad = sum(1 for r in recs if r["w8_msb_range"] != [0, 0])
        w8_lsb_zero_bad = sum(1 for r in recs if r["w8_lsb_range"] != [0, 0])
        clip_delta = (
            max(0, int(recs[-1].get("clip_msb", 0)) - int(recs[0].get("clip_msb", 0))) +
            max(0, int(recs[-1].get("clip_lsb", 0)) - int(recs[0].get("clip_lsb", 0)))
        )

        # Clamp hit & recovery analysis
        rail_thr = float(max(10, clamp - 1))
        recover_thr = float(max(5, clamp - 4))
        at_rail = w8_max_series >= rail_thr
        clamp_hit_frac = float(np.mean(at_rail))

        # Count distinct rail-touch episodes and whether weight pulls back cleanly within horizon
        episodes = 0
        recovered = 0
        in_ep = False
        for i in range(n):
            if at_rail[i] and not in_ep:
                in_ep = True
                episodes += 1
            elif in_ep and w8_max_series[i] <= recover_thr:
                recovered += 1
                in_ep = False
        # Pinned fraction: rail hits without recovery episodes or staying at rail at end
        recovery_rate = (float(recovered) / float(episodes)) if episodes > 0 else 1.0
        pinned_frac = clamp_hit_frac * (1.0 - 0.7 * recovery_rate)

        info = {
            "phase_idx": pidx,
            "n": n,
            "mean_enob": mean_enob,
            "start_enob": start_enob,
            "late_enob": late_enob,
            "mean_loss": mean_loss,
            "start_loss": start_loss,
            "late_loss": late_loss,
            "late_detr_lift_b": late_detr_lift,
            "late_detr_loss_ratio": late_detr_loss_ratio,
            "slope_full_b_per_min": slope_full,
            "slope_post_b_per_min": slope_post,
            "conv_climb_b": trend_end_minus_min_early,
            "jitter_std": jitter,
            "w8_peak": float(np.max(w8_max_series)),
            "w8_mean_peak": float(np.mean(w8_max_series)),
            "w3_peak": float(np.max(w3_max_series)),
            "clamp_hit_frac": clamp_hit_frac,
            "recovery_rate": recovery_rate,
            "pinned_frac": pinned_frac,
            "clip_delta": clip_delta,
            "off_w8_leak_frac": float(w8_msb_zero_bad + w8_lsb_zero_bad) / float(2 * n),
        }
        if reg_on:
            on_phases.append(info)
        else:
            off_phases.append(info)

    # Pair-wise + continuous thermal-detrended contrast:
    # Evaluates how much Warm ON lifts ENOB and reduces Loss above the underlying
    # thermal drift curve E_base(t), and confirms Warm OFF drops back onto E_base(t).
    step_lifts = []
    loss_ratios = []
    off_drops = []

    phase_by_idx = {p["phase_idx"]: p for p in (on_phases + off_phases)}
    for p_on in on_phases:
        if len(base_t) >= 2:
            step_lifts.append(p_on["late_detr_lift_b"])
            loss_ratios.append(p_on["late_detr_loss_ratio"])
        else:
            idx = p_on["phase_idx"]
            prev_off = phase_by_idx.get(idx - 1) if (idx - 1) in phase_by_idx and any(o["phase_idx"] == idx - 1 for o in off_phases) else None
            next_off = phase_by_idx.get(idx + 1) if (idx + 1) in phase_by_idx and any(o["phase_idx"] == idx + 1 for o in off_phases) else None
            if prev_off and next_off:
                base_enob = 0.5 * (prev_off["late_enob"] + next_off["start_enob"])
                base_loss = math.sqrt(max(1.0, prev_off["late_loss"]) * max(1.0, next_off["start_loss"]))
                step_lifts.append(p_on["late_enob"] - base_enob)
                loss_ratios.append(base_loss / max(1.0, p_on["late_loss"]))

    for p_off in off_phases:
        off_drops.append(p_off["start_enob"] - p_off["late_enob"])
        prev_on = phase_by_idx.get(p_off["phase_idx"] - 1)
        if prev_on and len(base_t) >= 2:
            # Drop in detrended ENOB when switching ON -> OFF (should return near 0)
            off_drops.append(prev_on["late_detr_lift_b"] - p_off["late_detr_lift_b"])

    # Secondary ON phases (Phase 5+) where chip is already hot -> strongest detrended signal;
    # combine with Phase 3 detrended metrics when thermal curve is available.
    hot_on = [p for p in on_phases if p["phase_idx"] >= 4]
    if not hot_on:
        hot_on = on_phases

    mean_step_lift = float(np.average(
        [p["late_detr_lift_b"] if len(base_t) >= 2 else 0.0 for p in on_phases],
        weights=[2.0 if p["phase_idx"] >= 4 else 1.0 for p in on_phases],
    )) if (on_phases and len(base_t) >= 2) else (float(np.mean(step_lifts)) if step_lifts else 0.0)
    mean_loss_ratio = float(np.exp(np.average(
        [math.log(max(0.1, p["late_detr_loss_ratio"])) for p in on_phases],
        weights=[2.0 if p["phase_idx"] >= 4 else 1.0 for p in on_phases],
    ))) if (on_phases and len(base_t) >= 2) else (float(np.exp(np.mean(np.log(np.maximum(0.1, loss_ratios))))) if loss_ratios else 1.0)
    hot_conv_climb = float(np.average(
        [p["conv_climb_b"] for p in on_phases],
        weights=[2.0 if p["phase_idx"] >= 4 else 1.0 for p in on_phases],
    )) if on_phases else 0.0
    hot_slope = float(np.mean([p["slope_post_b_per_min"] for p in hot_on])) if hot_on else 0.0
    mean_jitter = float(np.mean([p["jitter_std"] for p in on_phases])) if on_phases else 0.5
    mean_recovery = float(np.mean([p["recovery_rate"] for p in hot_on])) if hot_on else 1.0
    mean_pinned = float(np.mean([p["pinned_frac"] for p in hot_on])) if hot_on else 0.0
    mean_clamp_hit = float(np.mean([p["clamp_hit_frac"] for p in hot_on])) if hot_on else 0.0
    mean_w8_peak = float(np.mean([p["w8_mean_peak"] for p in hot_on])) if hot_on else 0.0
    max_w3_peak = float(np.max([p["w3_peak"] for p in on_phases])) if on_phases else 0.0
    total_clips = int(sum(p["clip_delta"] for p in on_phases))
    off_leak = float(np.max([p["off_w8_leak_frac"] for p in off_phases])) if off_phases else 0.0
    mean_off_slope = float(np.mean([p["slope_full_b_per_min"] for p in off_phases])) if off_phases else 0.0
    mean_hot_on_enob = float(np.mean([p["late_enob"] for p in hot_on])) if hot_on else 0.0
    mean_hot_off_enob = float(np.mean([p["mean_enob"] for p in off_phases])) if off_phases else 0.0

    # Composite objective J(theta) strictly from Warm ON / OFF trend curves
    score = (
        1.6 * mean_step_lift
        + 1.0 * math.log2(max(0.25, mean_loss_ratio))
        + 0.9 * max(-0.5, min(1.5, hot_conv_climb))
        + 0.4 * max(-0.5, min(1.0, hot_slope))
        + 0.4 * mean_recovery
        - 1.4 * mean_jitter
        - 0.9 * mean_pinned
        - 2.0 * off_leak
        - 0.015 * min(50, total_clips)
    )

    eta_eff = 4.0 * lr
    gamma = float(l2_reg) / 65536.0
    tau_mom = 1.0 / max(1e-3, 1.0 - momentum)
    g_eff = eta_eff * tau_mom
    noise_amp = eta_eff / math.sqrt(max(1e-3, 1.0 - momentum ** 2))

    return {
        "log_path": log_path,
        "name": Path(log_path).name,
        "params": {
            "lr": lr,
            "l2_reg": l2_reg,
            "momentum": momentum,
            "clamp": clamp,
        },
        "physics": {
            "eta_eff": eta_eff,
            "gamma": gamma,
            "tau_mom_beats": tau_mom,
            "G_eff": g_eff,
            "noise_amp": noise_amp,
        },
        "trends": {
            "hot_on_late_enob": mean_hot_on_enob,
            "warm_off_mean_enob": mean_hot_off_enob,
            "warm_step_lift_b": mean_step_lift,
            "warm_loss_ratio": mean_loss_ratio,
            "hot_conv_climb_b": hot_conv_climb,
            "hot_post_slope_b_per_min": hot_slope,
            "warm_off_slope_b_per_min": mean_off_slope,
            "jitter_std": mean_jitter,
            "w8_mean_peak_lsb": mean_w8_peak,
            "w3_max_peak_lsb": max_w3_peak,
            "clamp_hit_frac": mean_clamp_hit,
            "recovery_rate": mean_recovery,
            "pinned_frac": mean_pinned,
            "clip_delta": total_clips,
            "off_w8_leak_frac": off_leak,
        },
        "score": float(score),
        "on_phases": on_phases,
        "off_phases": off_phases,
    }


def _phi(lr: float, l2_reg: float, momentum: float, clamp: float) -> np.ndarray:
    """Physics-informed feature vector for Gaussian Process surrogate."""
    tau = 1.0 / max(0.03, 1.0 - momentum)
    g_eff = (4.0 * lr) * tau
    n_amp = (4.0 * lr) / math.sqrt(max(0.05, 1.0 - momentum ** 2))
    gamma = max(128.0, float(l2_reg)) / 65536.0
    eq_ratio = (4.0 * lr) / (gamma * max(40.0, clamp))
    # Standardized scales around expected sweet spot
    return np.array([
        (math.log(lr) - math.log(0.035)) / 0.45,
        (math.log(max(256.0, float(l2_reg))) - math.log(1280.0)) / 0.60,
        (math.log(tau) - math.log(7.5)) / 0.55,
        (float(clamp) - 75.0) / 8.0,
        (math.log(g_eff) - math.log(1.0)) / 0.60,
        (math.log(n_amp) - math.log(0.28)) / 0.45,
        (math.log(max(0.05, eq_ratio)) - math.log(0.10)) / 0.60,
    ], dtype=np.float64)


def _gp_predict(X_train: np.ndarray, y_train: np.ndarray, X_cand: np.ndarray,
                length_scale: float = 1.35, noise_var: float = 0.08) -> Tuple[np.ndarray, np.ndarray]:
    y_mean = float(np.mean(y_train))
    y_centered = y_train - y_mean
    # RBF kernel
    d2_tr = np.sum((X_train[:, None, :] - X_train[None, :, :]) ** 2, axis=-1)
    K = np.exp(-0.5 * d2_tr / (length_scale ** 2)) + noise_var * np.eye(len(X_train))
    alpha = np.linalg.solve(K, y_centered)
    K_inv = np.linalg.inv(K)

    d2_ca = np.sum((X_cand[:, None, :] - X_train[None, :, :]) ** 2, axis=-1)
    K_s = np.exp(-0.5 * d2_ca / (length_scale ** 2))
    mu = y_mean + K_s @ alpha
    var = np.maximum(1e-6, 1.0 - np.sum((K_s @ K_inv) * K_s, axis=1))
    sigma = np.sqrt(var)
    return mu, sigma


def propose_next_hyperparams(
    analyses: List[Dict[str, Any]],
    next_round_idx: int,
    max_rounds: int = 5,
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Uses extracted warm trend curves + physics priors + GP-UCB surrogate to propose next round parameters.
    """
    reasons: List[str] = []
    latest = analyses[-1]
    best = max(analyses, key=lambda a: a["score"])

    # Candidate grid constrained inside physically valid regimes
    lrs = [0.020, 0.025, 0.028, 0.030, 0.032, 0.035, 0.038, 0.040, 0.045, 0.055]
    l2s = [768, 896, 1024, 1280, 1536, 1792, 2048, 2560]
    moms = [0.75, 0.80, 0.82, 0.85, 0.86, 0.88, 0.90, 0.92]
    clamps = [65, 70, 72, 75, 78, 80]

    candidates = []
    for lr in lrs:
        for l2 in l2s:
            for mom in moms:
                for cl in clamps:
                    candidates.append((lr, l2, mom, cl))

    X_train = np.array([
        _phi(a["params"]["lr"], a["params"]["l2_reg"], a["params"]["momentum"], a["params"]["clamp"])
        for a in analyses
    ])
    y_train = np.array([a["score"] for a in analyses], dtype=np.float64)
    X_cand = np.array([_phi(lr, l2, mom, cl) for (lr, l2, mom, cl) in candidates])

    mu, sigma = _gp_predict(X_train, y_train, X_cand)

    # Physics trend-curve shaping prior anchored on the latest & best runs
    tr = latest["trends"]
    p_best = best["params"]
    b_tr = best["trends"]

    # Exploration coefficient decays across the 5 rounds (Round 2..3 explore, Round 4..5 exploit)
    kappa = max(0.25, 1.35 - 0.25 * max(0, next_round_idx - 2))

    prior_bonus = np.zeros(len(candidates), dtype=np.float64)
    target_lr = p_best["lr"]
    target_l2 = float(p_best["l2_reg"])
    target_mom = p_best["momentum"]
    target_clamp = float(p_best["clamp"])

    # Compute physics directional nudges from the trend curves
    if tr["jitter_std"] > 0.28:
        reasons.append(f"High Warm-ON jitter ({tr['jitter_std']:.3f} b) -> penalize high noise_amp (lower lr or momentum).")
    else:
        reasons.append(f"Clean Warm-ON trend stability (jitter={tr['jitter_std']:.3f} b).")

    if tr["hot_conv_climb_b"] < 0.05 and tr["w8_mean_peak_lsb"] < 0.80 * latest["params"]["clamp"]:
        reasons.append(
            f"Under-powered thermal tracking (conv_climb={tr['hot_conv_climb_b']:+.2f} b, "
            f"W8_peak={tr['w8_mean_peak_lsb']:.1f} < 0.8*clamp) -> bias toward higher G_eff (higher lr/mom or lower L2)."
        )
    elif tr["pinned_frac"] > 0.35 or tr["recovery_rate"] < 0.5:
        reasons.append(
            f"Rail pinning detected (pinned={tr['pinned_frac']:.2f}, recovery={tr['recovery_rate']:.2f}) "
            f"-> bias toward stronger L2 anchor or wider/tuned clamp headroom."
        )
    else:
        reasons.append(
            f"Healthy anti-windup dynamics (W8_peak={tr['w8_mean_peak_lsb']:.1f}/{latest['params']['clamp']}, "
            f"recovery={tr['recovery_rate']:.2f})."
        )

    # Pinch-off guard: check if higher clamp previously degraded score
    high_clamp_runs = [a for a in analyses if a["params"]["clamp"] >= 78]
    mid_clamp_runs = [a for a in analyses if 70 <= a["params"]["clamp"] <= 76]
    if high_clamp_runs and mid_clamp_runs:
        if max(a["score"] for a in high_clamp_runs) < max(a["score"] for a in mid_clamp_runs) - 0.15:
            reasons.append("Pinch-off turnaround detected at clamp >= 78 -> restrict clamp <= 75.")

    tested_set = {
        (round(a["params"]["lr"], 4), int(a["params"]["l2_reg"]), round(a["params"]["momentum"], 3), int(a["params"]["clamp"]))
        for a in analyses
    }

    best_acq = -1e9
    best_cand = None

    for idx, (lr, l2, mom, cl) in enumerate(candidates):
        key = (round(lr, 4), int(l2), round(mom, 3), int(cl))
        if key in tested_set:
            continue

        # Physics prior regularization around physical tradeoffs
        b = 0.0
        # 1. Subthreshold pinch-off soft penalty above clamp=75
        if cl > 75:
            b -= 0.04 * (cl - 75)
        # 2. If jitter was high, penalize higher N_amp
        n_amp = (4.0 * lr) / math.sqrt(max(0.05, 1.0 - mom ** 2))
        if tr["jitter_std"] > 0.28:
            if n_amp > latest["physics"]["noise_amp"]:
                b -= 0.65 * (n_amp - latest["physics"]["noise_amp"]) / 0.10
        # 3. If under-powered, reward moderately higher G_eff vs best
        g_eff = (4.0 * lr) / max(0.05, 1.0 - mom)
        if b_tr["hot_conv_climb_b"] < 0.10 and b_tr["pinned_frac"] < 0.25:
            if g_eff > best["physics"]["G_eff"] * 1.15 and g_eff < 3.5:
                b += 0.22
        # 4. If pinned at rail, reward higher l2_reg or moderate clamp shift
        if tr["pinned_frac"] > 0.35 or tr["recovery_rate"] < 0.5:
            if l2 > latest["params"]["l2_reg"]:
                b += 0.20
            if cl >= 75:
                b += 0.10
        # 5. Structured diverse coverage in Round 2 & 3 so GP learns sensitivity to each axis
        if next_round_idx == 2:
            # Test higher G_eff + slightly lower L2 or nearby L2/mom to probe dynamic headroom around clamp=75
            if mom in (0.85, 0.88, 0.90) and l2 in (1024, 1536) and lr >= 0.035 and cl == 75:
                b += 0.45
        elif next_round_idx == 3:
            # Test clamp & momentum trade-off (e.g. mom=0.80 vs 0.90, clamp=70 vs 80 depending on Round 2)
            if mom == 0.80 and cl in (70, 80):
                b += 0.30

        # Avoid extreme diverging regime G_eff > 4.0 or dead regime G_eff < 0.35
        if g_eff > 3.6 or g_eff < 0.35:
            b -= 2.0

        acq = float(mu[idx] + kappa * sigma[idx] + b)
        if acq > best_acq:
            best_acq = acq
            best_cand = {
                "lr": lr,
                "l2_reg": l2,
                "momentum": mom,
                "clamp": cl,
                "pred_mu": float(mu[idx]),
                "pred_sigma": float(sigma[idx]),
                "acq_score": acq,
            }

    assert best_cand is not None
    return best_cand, reasons


def main():
    parser = argparse.ArgumentParser(description="Analog Hyperparameter Trend-Curve Generator (SE 2630397-4)")
    parser.add_argument("--logs", nargs="+", required=True, help="Completed JSON logs to feed into the model")
    parser.add_argument("--next-round", type=int, default=2, help="Next round index (2..5)")
    parser.add_argument("--select-best", action="store_true", help="Select the overall best verified parameters instead of proposing exploration")
    parser.add_argument("--out-json", type=str, default=None, help="Optional path to save model analysis and proposal JSON")
    args = parser.parse_args()

    analyses = [extract_warm_trend_metrics(p) for p in args.logs]

    print("=" * 98)
    print("  INVERTED MAML: WARM TREND-CURVE ANALYSIS & ML HYPERPARAMETER GENERATOR")
    print("=" * 98)
    print(f"{'Log File':42s} | {'LR':>5s} {'L2':>4s} {'Mom':>4s} {'Clmp':>4s} | {'Lift':>5s} {'LossR':>5s} {'Climb':>5s} {'Jitt':>5s} {'Recov':>5s} | {'Score':>6s}")
    print("-" * 98)
    for a in analyses:
        p = a["params"]
        t = a["trends"]
        nm = a["name"][:42]
        print(
            f"{nm:42s} | {p['lr']:5.3f} {p['l2_reg']:4d} {p['momentum']:4.2f} {p['clamp']:4d} | "
            f"{t['warm_step_lift_b']:+5.2f} {t['warm_loss_ratio']:5.2f} {t['hot_conv_climb_b']:+5.2f} "
            f"{t['jitter_std']:5.2f} {t['recovery_rate']:5.2f} | {a['score']:+6.3f}"
        )
        if t["off_w8_leak_frac"] > 0.0:
            print(f"    [!] WARNING: Regler OFF W8 non-zero fraction = {t['off_w8_leak_frac']:.2%}")
    print("-" * 98)

    best = max(analyses, key=lambda a: a["score"])
    if args.select_best:
        result = {
            "mode": "select_best",
            "best_run": best["name"],
            "recommended": best["params"],
            "best_score": best["score"],
            "best_trends": best["trends"],
        }
        bp = best["params"]
        print(f"\n[+] FINAL OPTIMAL SELECTION (Best Verified Run: {best['name']}, Score={best['score']:+.3f}):")
        print(f"    lr={bp['lr']}, l2_reg={bp['l2_reg']}, momentum={bp['momentum']}, clamp={bp['clamp']}")
    else:
        prop, reasons = propose_next_hyperparams(analyses, args.next_round)
        result = {
            "mode": "propose_next",
            "next_round": args.next_round,
            "best_so_far": best["params"],
            "recommended": {
                "lr": prop["lr"],
                "l2_reg": prop["l2_reg"],
                "momentum": prop["momentum"],
                "clamp": prop["clamp"],
            },
            "pred_mu": prop["pred_mu"],
            "pred_sigma": prop["pred_sigma"],
            "acq_score": prop["acq_score"],
            "diagnostics": reasons,
        }
        print(f"\n[*] Model Diagnostics for Round {args.next_round}:")
        for r in reasons:
            print(f"    - {r}")
        print(f"\n[+] PROPOSED ROUND {args.next_round} HYPERPARAMETERS (GP pred_mu={prop['pred_mu']:+.3f} ± {prop['pred_sigma']:.3f}):")
        print(f"    lr={prop['lr']}, l2_reg={prop['l2_reg']}, momentum={prop['momentum']}, clamp={prop['clamp']}")

    if args.out_json:
        with open(args.out_json, "w") as f:
            json.dump(result, f, indent=2)


if __name__ == "__main__":
    main()
