# Test Card 1 Attenuator 1k/5.1k: Broadened Window [4.5..5.5 ms] White Noise Silicon Benchmark
**Comparative Hardware Characterization: Attenuator Resistance Benchmark (1k/5.1k on Card 1 vs. 1k/3.3k on Card 2)**  
**Patent Pending SE 2630397-4 | Open Science Hardware**  
**Document ID:** `INVERTED_MAML_CARD1_1000EP_BROADENED_WINDOW_1K_5P1K_COMPREHENSIVE_REPORT`  
**Date:** 2026-11-05  
**Target Hardware:** Card 1 (PCB v1.3.2, 1k/5.1k Attenuator) vs. Card 2 (PCB v1.3.2, 1k/3.3k Attenuator)  
**Publication PDF Report:** [`FPGA_code/docs/INVERTED_MAML_CARD1_1000EP_BROADENED_WINDOW_1K_5P1K_COMPREHENSIVE_REPORT.pdf`](file:///home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/docs/INVERTED_MAML_CARD1_1000EP_BROADENED_WINDOW_1K_5P1K_COMPREHENSIVE_REPORT.pdf)  

> [!WARNING]
> **FORMAL RETRACTION / EXPERIMENTAL ARTIFACT NOTICE (2026-11-05)**  
> **The conclusions in this document regarding attenuator comparisons and precision ceilings have been formally retracted.**  
> The observed behavior was heavily confounded by firmware refresh timing jitter (10 ms vs 20 ms refresh skipping caused by blocking UART prints). Injected current differences were largely interacting with capacitor discharge droop rather than fine non-linearities. When timing is phase-locked to 10.0 ms crystal cycles, both cards exhibit clean ~5.6-bit uncompensated baselines.  
> **See the definitive post-mortem report:** [`INVESTIGATION_REPORT_TIMING_JITTER_AND_BASELINE_ARTIFACTS.md`](INVESTIGATION_REPORT_TIMING_JITTER_AND_BASELINE_ARTIFACTS.md).

---

## 1. Executive Summary & Hardware Context

This test evaluates **Card 1** equipped with the higher-resistance **$1\text{ k}\Omega / 5.1\text{ k}\Omega$ passive summing attenuator** under the exact same broadened dynamic temporal benchmark across $[4.5\dots 5.5\text{ ms}]$ (11 strata, 1,000 epochs, 11,000 physical single-sample online SGD steps, uncorrelated White Noise, $\text{LR}=0.02$, $\lambda=2048$, Patent Fig 7 $\pm 5\text{ LSB}$ disturbance).

### The Key Question:
> *Does the $1\text{ k}\Omega / 5.1\text{ k}\Omega$ attenuator perform better, worse, or approximately equal compared to Card 2 with $1\text{ k}\Omega / 3.3\text{ k}\Omega$?*

### Definitive Silicon Verdict:
**Card 1 ($1\text{ k}\Omega / 5.1\text{ k}\Omega$) performs SIGNIFICANTLY WORSE than Card 2 ($1\text{ k}\Omega / 3.3\text{ k}\Omega$) in both precision ceiling and dynamic range headroom.**

1. **Precision Ceiling (Center 5.0 ms Snapshot):**
   - **Card 2 ($1\text{ k}\Omega / 3.3\text{ k}\Omega$):** Attained **$4.91\text{ bits}$ sustained ENOB** ($17\,414.2\text{ LSB}^2$ loss) and **$6.29\text{ bits}$ peak precision** ($2\,063.0\text{ LSB}^2$).
   - **Card 1 ($1\text{ k}\Omega / 5.1\text{ k}\Omega$):** Attained only **$3.13\text{ bits}$ sustained ENOB** ($167\,498.2\text{ LSB}^2$ loss) and **$3.57\text{ bits}$ nominal peak** ($89\,324.5\text{ LSB}^2$).
   - Card 2 delivers **$+1.78\text{ bits}$ higher resolution** and nearly **$10\times$ lower quadratic error** ($17.4\text{k}$ vs $167.5\text{k}\text{ LSB}^2$).

2. **Window Mean Precision [4.5..5.5 ms across 11 strata]:**
   - **Card 2:** Lifted window mean precision to **$3.99\text{ bits}$** ($49\,898.6\text{ LSB}^2$).
   - **Card 1:** Reached only **$2.92\text{ bits}$** ($221\,182.6\text{ LSB}^2$).

3. **Ablation Contrast (Phase 4 vs Phase 2):**
   - **Card 2:** Showed a dramatic **$5.08\times$ error surge (508%)** upon zeroing weights ($W=0$), proving massive active analog authority.
   - **Card 1:** Showed only a modest **$1.55\times$ error increase (155%)**, indicating that compensation authority is severely starved.

4. **Weight Dynamic Range & Rail Clamping:**
   - **Card 2:** Remained completely relaxed in the linear sweet spot, with maximum weight $|W_8| \le 56\text{ LSB}$ ($>64\text{ LSB}$ margin to rails).
   - **Card 1:** Strained severely against the rails, with $|W_8|$ surging to **$110\text{ LSB}$** (just $10\text{ LSB}$ from the $\pm 120\text{ LSB}$ clamping limit) as the SGD loop desperately tried to pump sufficient correction current through the $5.1\text{ k}\Omega$ resistor.

---

## 2. Quantitative Performance Comparison: Card 1 vs. Card 2

| Experimental Phase & Protocol | Card 1 (1k/5.1k Attenuator)<br/>*Nov 5 2026 Live Silicon* | Card 2 (1k/3.3k Attenuator)<br/>*Nov 5 2026 Live Silicon* | Relative Performance & Significance |
| :--- | :---: | :---: | :--- |
| **Phase 1: Baseline Floor**<br/>($W=0$, Nominal $M_{33}$, 100 Ep) | **Window Loss:** 296227.0\text{ LSB}^2 (2.71\text{ b})<br/>**5.0 ms Loss:** 258913.0\text{ LSB}^2 (2.81\text{ b}) | **Window Loss:** 141070.1\text{ LSB}^2 (3.24\text{ b})<br/>**5.0 ms Loss:** 111766.0\text{ LSB}^2 (3.44\text{ b}) | Card 1 open-loop error is $2.3\times$ higher due to original row line op-amps and uncompensated channel skews. |
| **Phase 2: Online SGD**<br/>($\text{LR}=0.02, \lambda=2048$, 100 Ep) | **Window Loss:** 221182.6\text{ LSB}^2 (2.92\text{ b})<br/>**5.0 ms Loss:** 167498.2\text{ LSB}^2 (3.13\text{ b})<br/>**Peak 5.0 ms:** 3.57\text{ b} (89324.5\text{ LSB}^2) | **Window Loss:** **49898.6\text{ LSB}^2 (3.99\text{ b})**<br/>**5.0 ms Loss:** **17414.2\text{ LSB}^2 (4.91\text{ b})**<br/>**Peak 5.0 ms:** **6.29\text{ b} (2063.0\text{ LSB}^2)** | **Card 2 outperforms Card 1 by +1.78 bits sustained and +2.72 bits peak!** Quadratic error is nearly $10\times$ lower on Card 2. |
| **Phase 3: Fig 7 Tracking**<br/>(Patent Fig 7 $\pm 5\text{ LSB}$, 400 Ep) | **Window Loss:** 186259.2\text{ LSB}^2 (3.07\text{ b})<br/>**5.0 ms Loss:** 129454.0\text{ LSB}^2 (3.41\text{ b})<br/>**Peak 5.0 ms:** 4.79\text{ b} | **Window Loss:** **77708.6\text{ LSB}^2 (3.70\text{ b})**<br/>**5.0 ms Loss:** **39431.2\text{ LSB}^2 (4.33\text{ b})**<br/>**Peak 5.0 ms:** **6.46\text{ b}** | Card 1 partially adapts but cannot suppress large disturbance pulses because $5.1\text{ k}\Omega$ starves injected current. |
| **Phase 4: Ablation Control**<br/>($W=0$, Fig 7 $\pm 5\text{ LSB}$, 401 Ep) | **Window Loss:** 303059.7\text{ LSB}^2 (2.70\text{ b})<br/>**5.0 ms Loss:** 260068.1\text{ LSB}^2 (2.82\text{ b}) | **Window Loss:** 124390.2\text{ LSB}^2 (3.34\text{ b})<br/>**5.0 ms Loss:** 88447.7\text{ LSB}^2 (3.62\text{ b}) | When compensation is cut off, error on Card 1 returns to baseline with only a modest jump. |
| **Ablation Contrast (P4 / P2)** | **1.55x Error Increase** | **5.08x Error Surge (508%)** | Card 2 exerts $3.3\times$ higher control authority than Card 1. |
| **Max Weight Excursion $|W_8|$** | **110 LSB** (Near Saturation) | **56 LSB** (Quiet Linear Regime) | Card 1 risks rail saturation; Card 2 operates with $>64\text{ LSB}$ headroom. |

---

## 3. Circuit Physics Analysis: Why 1k/3.3k Greatly Outperforms 1k/5.1k

The mathematical and physical explanation for this performance disparity lies directly in Ohm's Law and op-amp summing junction dynamics:

1. **Injected Correction Current:**
   The neural network generates a correction voltage $V_{\text{sigm}}$ from op-amp `U1$CBB8.4` (Sigmoid 10). This voltage injects current into the non-inverting summing node of `U3$CBB15.1`:
   $$I_{\text{comp}} = \frac{V_{\text{sigm}}}{R_2}$$
   - On **Card 1** ($R_2 = 5.1\text{ k}\Omega$): $I_{\text{comp}} = \frac{V_{\text{sigm}}}{5.1\text{ k}\Omega}$
   - On **Card 2** ($R_2 = 3.3\text{ k}\Omega$): $I_{\text{comp}} = \frac{V_{\text{sigm}}}{3.3\text{ k}\Omega}$
   
   The ratio of available correction current is:
   $$\frac{I_{\text{comp, Card 2}}}{I_{\text{comp, Card 1}}} = \frac{5.1\text{ k}\Omega}{3.3\text{ k}\Omega} = 1.545\quad (+54.5\%\text{ more current on Card 2})$$

2. **Weight Excursion vs. Clamping Limits:**
   Because Card 1 has $-35\%$ less current per volt, the SGD algorithm is forced to push the digital compensation weights $W_8$ significantly harder to achieve equivalent current.
   - On Card 1, weights reach **$110\text{ LSB}$**, bumping against the non-linear curvature and saturation threshold of the dual-2T1C MOS triode cells ($\pm 120\text{ LSB}$).
   - On Card 2, the higher transconductance allows weights to achieve full error cancellation while staying below **$56\text{ LSB}$**, well within the ultra-clean, linear transconductance region.

---

## 4. Visual Evidence & Live Telemetry

### A. Side-by-Side Comparison Overlay: Card 1 vs. Card 2
![Card 1 vs Card 2 Telemetry Overlay](file:///home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/docs/figures/fig_card1_vs_card2_comparative_overlay.png)
*Figure 1: Direct comparison between Card 1 (Amber, 1k/5.1k) and Card 2 (Blue/Green, 1k/3.3k) across 1,000 epochs of online SGD under uncorrelated White Noise.*

### B. 2D Temporal Spectrogram of Precision on Card 1
![Card 1 Spectrogram](file:///home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/docs/figures/fig_card1_temporal_spectrogram_enob.png)
*Figure 2: 2D Spectrogram across [4.5..5.5 ms] for Card 1. Notice the precision ceiling hovers at ~3.0–3.4 bits, compared to the bright 4.5–6.0 bit wavefront achieved on Card 2.*

### C. Weight Dynamics & Rail Straining
![Weight Excursions](file:///home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/docs/figures/fig_card1_weight_excursions.png)
*Figure 3: Weight trajectories for Matrix 8 row 0. Card 1 (top) strains up to 110 LSB near the rail limit. Card 2 (bottom) converges quietly below 56 LSB.*

---

## 5. Engineering Conclusion & Recommendations

1. **Card 1 ($1\text{ k}\Omega / 5.1\text{ k}\Omega$) gives definitively WORSE performance** than Card 2 ($1\text{ k}\Omega / 3.3\text{ k}\Omega$).
2. The $5.1\text{ k}\Omega$ resistor chokes the available analog correction current by $35\%$, capping sustained precision at $3.13\text{ bits}$ (vs $4.91\text{ bits}$ on Card 2) and forcing weights dangerously close to saturation ($110\text{ LSB}$).
3. **Hardware Recommendation:** If Card 1 is to be used for high-precision inference or training experiments, its summing attenuator should be physically resoldered from **$1\text{ k}\Omega / 5.1\text{ k}\Omega$ to $1\text{ k}\Omega / 3.3\text{ k}\Omega$**, mirroring the successful hardware upgrade performed on Card 2.
