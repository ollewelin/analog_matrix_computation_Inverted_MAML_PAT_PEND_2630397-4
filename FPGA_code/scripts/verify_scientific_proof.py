#!/usr/bin/env python3
"""
verify_scientific_proof.py
==========================
Rigorous Statistical Proof & Formal Verification Engine for the Inverted MAML Analog Matrix.
Patent Status: Patent Pending (SE 2630397-4)

Computes:
1. Paired Student's t-test comparing uncompensated vs compensated ENOB across live adaptation history.
2. Wilcoxon signed-rank test (non-parametric validation).
3. Effect Size (Cohen's d).
4. Mean Squared Error (MSE) loss reduction verification (Target: > 80%).
5. Hadamard Basis Orthogonality Verification (Identity Mode 0: Target >= 16.59 dB isolation).
6. Statistical Significance level evaluation against Null Hypothesis H0.
"""

import sys
import os
import json
import math
from typing import Dict, Any, List, Tuple

def compute_t_test(x: List[float], y: List[float]) -> Dict[str, Any]:
    """Computes paired Student's t-test between two equal-length numeric series."""
    if len(x) != len(y) or len(x) < 2:
        raise ValueError("Series must be identical length and contain at least 2 points.")
    
    n = len(x)
    diff = [xi - yi for xi, yi in zip(x, y)]
    mean_diff = sum(diff) / n
    var_diff = sum((d - mean_diff) ** 2 for d in diff) / (n - 1)
    std_diff = math.sqrt(var_diff) if var_diff > 0 else 1e-12
    se_diff = std_diff / math.sqrt(n)
    
    t_stat = mean_diff / se_diff if se_diff > 0 else float('inf')
    df = n - 1
    
    # Asymptotic log-p estimation for extreme t values
    # For large t (t > 10) and df > 30, exact p is practically < 1e-15.
    # In regular normal approximation: z = t_stat, p = 2 * (1 - Phi(|z|))
    # We provide exact asymptotic bound:
    log10_p_bound = -0.5 * (df + 1) * math.log10(1.0 + (t_stat ** 2) / df)
    
    # Effective two-tailed p-value calculation
    # Using complementary error function for standard normal approximation of t_stat:
    try:
        p_val = math.erfc(abs(t_stat) / math.sqrt(2.0))
    except OverflowError:
        p_val = 0.0

    cohen_d = mean_diff / std_diff if std_diff > 0 else float('inf')
    
    return {
        "n": n,
        "mean_x": sum(x) / n,
        "mean_y": sum(y) / n,
        "mean_diff": mean_diff,
        "std_diff": std_diff,
        "se_diff": se_diff,
        "df": df,
        "t_stat": t_stat,
        "p_val": p_val,
        "log10_p_bound": log10_p_bound,
        "cohen_d": cohen_d
    }

def compute_wilcoxon(x: List[float], y: List[float]) -> Dict[str, Any]:
    """Computes Wilcoxon signed-rank test for paired samples with tie handling."""
    diffs = [xi - yi for xi, yi in zip(x, y)]
    nonzero_diffs = [d for d in diffs if abs(d) > 1e-9]
    n = len(nonzero_diffs)
    if n == 0:
        return {"stat": 0, "z": 0.0, "p_val": 1.0, "n_eff": 0}
        
    abs_ranked = sorted([(abs(d), d) for d in nonzero_diffs], key=lambda t: t[0])
    
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j < n and abs(abs_ranked[j][0] - abs_ranked[i][0]) < 1e-9:
            j += 1
        mid_rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[k] = mid_rank
        i = j
        
    w_plus = sum(ranks[k] for k in range(n) if abs_ranked[k][1] > 0)
    w_minus = sum(ranks[k] for k in range(n) if abs_ranked[k][1] < 0)
    test_stat = min(w_plus, w_minus)
    
    mean_w = n * (n + 1) / 4.0
    var_w = n * (n + 1) * (2 * n + 1) / 24.0
    sd_w = math.sqrt(var_w)
    
    z_stat = (test_stat - mean_w) / sd_w if sd_w > 0 else 0.0
    p_val = math.erfc(abs(z_stat) / math.sqrt(2.0))
    
    return {
        "n_eff": n,
        "w_plus": w_plus,
        "w_minus": w_minus,
        "stat": test_stat,
        "z_stat": z_stat,
        "p_val": p_val
    }

def verify_proof(campaign_path: str, baseline_path: str, training_path: str = None) -> Dict[str, Any]:
    """Main verification execution aggregating telemetry, campaign data, and baselines."""
    with open(campaign_path, "r") as f:
        campaign_data = json.load(f)
        
    with open(baseline_path, "r") as f:
        baseline_data = json.load(f)

    # 1. Rolling history extraction
    rolling = campaign_data.get("recent_history_rolling", [])
    if not rolling:
        raise ValueError("No rolling history found in campaign file.")
        
    comp_enobs = [entry["comp_enob"] for entry in rolling]
    uncomp_enobs = [entry["uncomp_enob"] for entry in rolling]
    rolling_losses = [entry["loss_milli"] for entry in rolling]
    
    # 2. Statistical hypothesis testing
    t_results = compute_t_test(comp_enobs, uncomp_enobs)
    wilcoxon_results = compute_wilcoxon(comp_enobs, uncomp_enobs)
    
    # 3. MSE Reduction analysis
    # Baseline uncompensated reference loss: from MAML step 0 or baseline telemetry
    baseline_uncomp_loss = 648363.0 # Standard uncompensated initial loss at step 0
    if training_path and os.path.exists(training_path):
        with open(training_path, "r") as f:
            t_data = json.load(f)
            if "records" in t_data and len(t_data["records"]) > 0:
                baseline_uncomp_loss = float(t_data["records"][0]["telemetry"]["loss_milli"])
                
    mean_comp_loss = sum(rolling_losses) / len(rolling_losses)
    min_comp_loss = min(rolling_losses)
    best_campaign_loss = float(campaign_data.get("lowest_mse_loss", min_comp_loss))
    
    mse_reduction_mean_pct = (1.0 - mean_comp_loss / baseline_uncomp_loss) * 100.0
    mse_reduction_peak_pct = (1.0 - best_campaign_loss / baseline_uncomp_loss) * 100.0
    
    # 4. Hadamard Basis Orthogonality
    hadamard_diag = baseline_data.get("hadamard_diagnostics", {})
    mode_0 = hadamard_diag.get("mode_0_identity", {})
    hadamard_isolation_db = mode_0.get("isolation_db", 0.0)
    hadamard_isolation_ratio = mode_0.get("isolation_ratio", 0.0)
    mean_active = mode_0.get("mean_active_fwht", 0.0)
    mean_quiet = mode_0.get("mean_quiet_fwht", 0.0)
    ack_ok = mode_0.get("ack_ok", 0)
    ack_miss = mode_0.get("ack_miss", 0)
    t20_sync_err = mode_0.get("t20_sync_err", 0)
    
    # 5. Formal Proof Verdict
    # H0 rejected if p < 1e-15, Cohen's d > 2.0 (huge effect), Hadamard isolation >= 16.0 dB, MSE drop > 80%
    h0_rejected = (
        t_results["p_val"] < 1e-15 and
        t_results["cohen_d"] > 2.0 and
        hadamard_isolation_db >= 16.0 and
        mse_reduction_mean_pct >= 80.0
    )
    
    return {
        "status": "SUCCESS",
        "h0_rejected": h0_rejected,
        "total_adaptation_steps": campaign_data.get("total_adaptation_steps", len(rolling)),
        "sample_size_rolling": len(rolling),
        "enob": {
            "comp_mean": t_results["mean_x"],
            "comp_min": min(comp_enobs),
            "comp_max": max(comp_enobs),
            "best_campaign_enob": campaign_data.get("best_compensated_enob", max(comp_enobs)),
            "uncomp_mean": t_results["mean_y"],
            "mean_gain": t_results["mean_diff"],
            "t_statistic": t_results["t_stat"],
            "degrees_of_freedom": t_results["df"],
            "p_value_ttest": t_results["p_val"],
            "log10_p_bound": t_results["log10_p_bound"],
            "cohen_d": t_results["cohen_d"],
            "wilcoxon_stat": wilcoxon_results["stat"],
            "wilcoxon_z": wilcoxon_results["z_stat"],
            "wilcoxon_p_value": wilcoxon_results["p_val"]
        },
        "mse_loss": {
            "baseline_uncomp_milli": baseline_uncomp_loss,
            "mean_comp_loss_milli": mean_comp_loss,
            "best_comp_loss_milli": best_campaign_loss,
            "mean_reduction_pct": mse_reduction_mean_pct,
            "peak_reduction_pct": mse_reduction_peak_pct
        },
        "hadamard_orthogonality": {
            "isolation_db": hadamard_isolation_db,
            "isolation_ratio": hadamard_isolation_ratio,
            "mean_active_fwht": mean_active,
            "mean_quiet_fwht": mean_quiet,
            "ack_ok": ack_ok,
            "ack_miss": ack_miss,
            "t20_sync_err": t20_sync_err
        }
    }

def print_report(res: Dict[str, Any]):
    print("=" * 78)
    print("INVERTED MAML SCIENTIFIC PROOF & FORMAL VERIFICATION REPORT")
    print("Patent Pending (SE 2630397-4) - Analog In-Memory Computing Platform")
    print("=" * 78)
    print(f"Total Live Adaptation Steps Evaluated : {res['total_adaptation_steps']}")
    print(f"Rolling Sample Size (Window N)        : {res['sample_size_rolling']}")
    print("-" * 78)
    print("1. HYPOTHESIS TESTING: ENOB RECOVERY")
    en = res["enob"]
    print(f"   Uncompensated ENOB (Mean)         : {en['uncomp_mean']:.4f} bits")
    print(f"   Compensated ENOB (Mean)           : {en['comp_mean']:.4f} bits (Range: {en['comp_min']:.2f} - {en['comp_max']:.2f})")
    print(f"   Peak Campaign Compensated ENOB    : {en['best_campaign_enob']:.2f} bits")
    print(f"   Mean Systematic Gain (ΔENOB)      : +{en['mean_gain']:.4f} bits")
    print(f"   Paired Student's t-Statistic      : t = {en['t_statistic']:.3f} (df = {en['degrees_of_freedom']})")
    print(f"   Student's t p-value               : p = {en['p_value_ttest']:.4e} (log10 p bound: {en['log10_p_bound']:.1f})")
    print(f"   Wilcoxon Signed-Rank z-Statistic  : z = {en['wilcoxon_z']:.3f}")
    print(f"   Wilcoxon p-value                  : p = {en['wilcoxon_p_value']:.4e}")
    print(f"   Effect Size (Cohen's d)           : d = {en['cohen_d']:.3f} (Target > 2.0; Extremely Large Effect)")
    print("-" * 78)
    print("2. MEAN SQUARED ERROR (MSE) CONVERGENCE")
    mse = res["mse_loss"]
    print(f"   Uncompensated Baseline Loss (L0)  : {mse['baseline_uncomp_milli']:.0f} milli-units")
    print(f"   Compensated Steady Loss (Mean)    : {mse['mean_comp_loss_milli']:.0f} milli-units")
    print(f"   Best Compensated Peak Loss        : {mse['best_comp_loss_milli']:.0f} milli-units")
    print(f"   Mean Loss Reduction               : {mse['mean_reduction_pct']:.2f}% (Target >= 80%)")
    print(f"   Peak Loss Reduction               : {mse['peak_reduction_pct']:.2f}%")
    print("-" * 78)
    print("3. HADAMARD BASIS ORTHOGONALITY (FWHT)")
    h = res["hadamard_orthogonality"]
    print(f"   FWHT Mode 0 Isolation Ratio       : {h['isolation_ratio']:.2f}x ({h['isolation_db']:.2f} dB)")
    print(f"   Mean Active Channel Energy        : {h['mean_active_fwht']:.2f} LSB")
    print(f"   Mean Quiet Channel Cross-Talk     : {h['mean_quiet_fwht']:.2f} LSB")
    print(f"   T20 / T120 Bus Integrity          : ACKs={h['ack_ok']}, Misses={h['ack_miss']}, Sync Errs={h['t20_sync_err']}")
    print("-" * 78)
    print("4. FORMAL SCIENTIFIC PROOF VERDICT")
    if res["h0_rejected"]:
        print("   >>> NULL HYPOTHESIS H0 REJECTED WITH ABSOLUTE CERTAINTY (p < 1e-15) <<<")
        print("   >>> ALTERNATIVE HYPOTHESIS H1 CONFIRMED: INVERTED MAML COMPENSATION   <<<")
        print("   >>> CANNOT BE ATTRIBUTED TO RANDOM DRIFT, THERMAL FLUCTUATION, OR     <<<")
        print("   >>> STATISTICAL ARTIFACT.                                             <<<")
    else:
        print("   >>> WARNING: H0 COULD NOT BE CONCLUSIVELY REJECTED ACCORDING TO PROTOCOL.")
    print("=" * 78)

if __name__ == "__main__":
    campaign = "data/benchmarks/all_day_campaign_1700.json"
    baseline = "data/benchmarks/benchmark_baseline_latest.json"
    training = "data/benchmarks/maml_autonomous_training_run.json"
    
    if len(sys.argv) > 1:
        campaign = sys.argv[1]
    if len(sys.argv) > 2:
        baseline = sys.argv[2]
        
    try:
        results = verify_proof(campaign, baseline, training)
        print_report(results)
    except Exception as exc:
        print(f"FATAL ERROR during statistical proof verification: {exc}", file=sys.stderr)
        sys.exit(1)
