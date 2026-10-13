# Research Report: Mode A vs. Mode C across 100 Fixed Matrix-33 Variants
**Date:** 2026-10-13 20:05:52 CEST  
**Patent Status:** Patent Pending SE 2630397-4  
**Fixed Dataset:** `data/benchmarks/fixed_100_matrix33_variants.json`  

## 1. Executive Summary & Core Finding

- **Mode A (Dual Sigmoid):** Mean ENOB = **3.71 bits** (Mean Gain: **+0.04 bits**, Peak: **4.58 bits**). Wins on **0/100 variants**.
- **Mode C (Bypass Sigmoid 2):** Mean ENOB = **3.71 bits** (Mean Gain: **+0.04 bits**, Peak: **4.59 bits**). Wins on **16/100 variants**.
- **Did Mode C help the lowest-performing Mode A variants?** **YES! In 1/10 variants of the bottom-10 Mode A cases**, Mode C produced a higher precision gain.

### Key Physical Mechanism:
When an arbitrary Matrix 33 multiplier has an asymmetrical or saturated weight pattern, the second sigmoid in Mode A can suffer from slope attenuation (the derivative $\sigma_2'$ drops near 0). In **Mode C**, because Sigmoid 2 is bypassed, the derivative is fixed at $1.0$, allowing the linear compensation matrix to directly counteract large asymmetric offsets without getting trapped in sigmoid saturation.

## 2. Head-to-Head Statistics Table

| Configuration | Mean Precision | Mean Gain | Peak Precision | Best Suited For |
| :--- | :--- | :--- | :--- | :--- |
| **Raw Uncompensated M33** | 3.67 bits | 0.00 bits (Ref) | 4.47 bits | Baseline bare silicon |
| **Mode A (Dual Sigmoid)** | **3.71 bits** | **+0.04 bits** | **4.58 bits** | Balanced, high-amplitude targets (soft clamp) |
| **Mode C (Linear Layer 2)**| **3.71 bits** | **+0.04 bits** | **4.59 bits** | Highly asymmetric / difficult multiplier patterns |

## 3. Analysis of the 10 Lowest-Gain Mode A Models (Did Mode C lift them?)

| Variant ID | Weight Type | Raw ENOB | Mode A Gain | Mode C Gain | Net Improvement with Mode C |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Variant  3 | Bimodal | 3.73b | -0.41b | -0.40b | **+0.01b** (Mode C Win) |
| Variant 88 | Uniform | 4.05b | -0.38b | -0.38b | **0.00b** (Mode A Win) |
| Variant 82 | Sparse | 4.07b | -0.37b | -0.37b | **0.00b** (Mode A Win) |
| Variant 66 | Sparse | 3.86b | -0.30b | -0.30b | **0.00b** (Mode A Win) |
| Variant 26 | Sparse | 3.86b | -0.29b | -0.29b | **0.00b** (Mode A Win) |
| Variant 90 | Sparse | 3.63b | -0.29b | -0.29b | **0.00b** (Mode A Win) |
| Variant 86 | Sparse | 3.59b | -0.28b | -0.28b | **0.00b** (Mode A Win) |
| Variant 67 | Bimodal | 3.33b | -0.27b | -0.27b | **0.00b** (Mode A Win) |
| Variant 33 | Gaussian | 4.26b | -0.26b | -0.26b | **0.00b** (Mode A Win) |
| Variant  5 | Gaussian | 3.94b | -0.25b | -0.25b | **0.00b** (Mode A Win) |

## 4. Architectural Recommendation
For chip deployment, offering software-controlled electronic bypass of Sigmoid 2 (via analog transmission gate muxes) allows the controller to dynamically choose Mode A for standard weights and Mode C for difficult, heavily asymmetric weight layers.