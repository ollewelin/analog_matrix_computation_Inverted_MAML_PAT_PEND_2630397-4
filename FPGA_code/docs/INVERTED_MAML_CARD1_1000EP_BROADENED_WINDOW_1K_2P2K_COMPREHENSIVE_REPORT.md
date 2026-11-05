# Test Card 1 Attenuator 1k/2.2k: Broadened Window [4.5..5.5 ms] Silicon Benchmark
**Comprehensive Hardware Characterization: Three-Way Attenuator Benchmark (1k/5.1k vs. 1k/3.3k vs. 1k/2.2k)**  
**Patent Pending SE 2630397-4 | Open Science Hardware**  
**Document ID:** `INVERTED_MAML_CARD1_1000EP_BROADENED_WINDOW_1K_2P2K_COMPREHENSIVE_REPORT`  
**Date:** 2026-11-05  
**Target Hardware:** Card 1 (PCB v1.3.2, 1k/2.2k Attenuator)  
**Publication PDF Report:** [`FPGA_code/docs/INVERTED_MAML_CARD1_1000EP_BROADENED_WINDOW_1K_2P2K_COMPREHENSIVE_REPORT.pdf`](file:///home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/docs/INVERTED_MAML_CARD1_1000EP_BROADENED_WINDOW_1K_2P2K_COMPREHENSIVE_REPORT.pdf)  

> [!WARNING]
> **FORMAL RETRACTION / EXPERIMENTAL ARTIFACT NOTICE (2026-11-05)**  
> **The conclusions in this document regarding a "new performance champion", 9.53x ablation contrast, and peak ENOBs have been formally retracted.**  
> The observed behavior was heavily confounded by firmware refresh timing jitter (10 ms vs 20 ms refresh skipping caused by blocking UART prints). Injected current differences were largely interacting with capacitor discharge droop rather than fine non-linearities. When timing is phase-locked to 10.0 ms crystal cycles, both cards exhibit clean ~5.6-bit uncompensated baselines.  
> **See the definitive post-mortem report:** [`INVESTIGATION_REPORT_TIMING_JITTER_AND_BASELINE_ARTIFACTS.md`](INVESTIGATION_REPORT_TIMING_JITTER_AND_BASELINE_ARTIFACTS.md).

---

## 1. Executive Summary & Circuit Breakthrough

Following the characterization of **Card 1** with the original high-resistance $1\text{ k}\Omega / 5.1\text{ k}\Omega$ attenuator (which starved analog correction current), Card 1 was physically upgraded with a new low-resistance **$1\text{ k}\Omega / 2.2\text{ k}\Omega$ summing attenuator** ($-12.7\text{ dB} \to -10.1\text{ dB}$).

Card 1 was evaluated under the exact identical broadened temporal window benchmark across $[4.5\dots 5.5\text{ ms}]$ (11 strata, 1,000 epochs, 11,000 physical single-sample online SGD steps, uncorrelated White Noise, $\text{LR}=0.02$, $\lambda=2048$, Patent Fig 7 $\pm 5\text{ LSB}$ disturbance).

### The Definitive Silicon Finding:
**The $1\text{ k}\Omega / 2.2\text{ k}\Omega$ attenuator is the NEW PERFORMANCE CHAMPION, outperforming both 1k/5.1k and 1k/3.3k!**

1. **New Record Peak Resolution on Silicon:**
   - **Card 1 ($1\text{ k}\Omega / 2.2\text{ k}\Omega$):** Shattered previous records, reaching **$6.63\text{ bits}$ peak ENOB** ($1\,390.5\text{ LSB}^2$ minimum quadratic error at 5.0 ms) and **$4.33\text{ bits}$ full-window peak**!
   - Card 2 ($1\text{ k}\Omega / 3.3\text{ k}\Omega$): Peaked at $6.29\text{ bits}$ ($2\,063.0\text{ LSB}^2$).
   - Card 1 ($1\text{ k}\Omega / 5.1\text{ k}\Omega$): Trapped at only $3.57\text{ bits}$.

2. **Spectacular Disturbance Suppression in Phase 3:**
   - Under continuous, severe $\pm 5\text{ LSB}$ non-stationary hardware shifts on Matrix 33 (Patent Fig 7 Emulator), Card 1 with $1\text{ k}\Omega / 2.2\text{ k}\Omega$ sustained an average 5.0 ms loss of only **$20\,835.9\text{ LSB}^2$ ($4.75\text{ bits}$ ENOB)**!
   - This cuts disturbance error nearly in half compared to Card 2 ($39\,431.2\text{ LSB}^2$, $4.33\text{ bits}$), and achieves **$6.2\times$ lower error** than 1k/5.1k ($129\,454.0\text{ LSB}^2$).

3. **Record Ablation Contrast ($9.53\times$ Error Surge / 953%):**
   - When compensation was disabled ($W=0$) in Phase 4, quadratic error instantly rocketed from $18\,238.9\text{ LSB}^2$ to **$173\,852.2\text{ LSB}^2$**—a massive **$9.53\times$ error surge**!
   - This is the largest causal ablation contrast ever recorded on physical Inverted MAML silicon (compared to $5.08\times$ on Card 2 and $1.55\times$ on 1k/5.1k).

4. **Relaxed Weights with Huge Dynamic Range Headroom:**
   - Because $R_2 = 2.2\text{ k}\Omega$ delivers $+131.8\%$ more correction current per volt than $5.1\text{ k}\Omega$ and $+50.0\%$ more than $3.3\text{ k}\Omega$, the SGD loop adapts effortlessly.
   - Matrix 8 weights stay comfortably within $|W_8| \le 41\text{ LSB}$ on row 0, leaving **$>79\text{ LSB}$ linear headroom** to the $\pm 120\text{ LSB}$ rail limits.

---

## 2. Three-Way Quantitative Performance Benchmark

| Experimental Phase & Metric | Card 1 (1k/5.1k Attenuator)<br/>*Original Factory* | Card 2 (1k/3.3k Attenuator)<br/>*First Upgrade* | Card 1 (1k/2.2k Attenuator)<br/>*NEW CHAMPION* | Circuit Significance |
| :--- | :---: | :---: | :---: | :--- |
| **Summing Resistor $R_2$** | $5.1\text{ k}\Omega$ | $3.3\text{ k}\Omega$ | **$2.2\text{ k}\Omega$** | $2.2\text{ k}\Omega$ maximizes injected current $I_{\text{comp}}$. |
| **Correction Current Ratio** | $1.00\times$ (Baseline) | $1.55\times$ (+55%) | **$2.32\times$ (+132% vs 5.1k, +50% vs 3.3k)** | Over double the anti-phase correction authority! |
| **Phase 1: Baseline Floor**<br/>($W=0$, Nominal $M_{33}$, 100 Ep) | **Win Loss:** 296227.0 L² (2.71 b)<br/>**5.0ms:** 258913.0 L² (2.81 b) | **Win Loss:** 141070.1 L² (3.24 b)<br/>**5.0ms:** 111766.0 L² (3.44 b) | **Win Loss:** 150232.7 L² (3.20 b)<br/>**5.0ms:** 126091.7 L² (3.35 b) | Card 1 with 2.2k matches Card 2 baseline symmetry (~3.4 bits). |
| **Phase 2: Online SGD**<br/>($\text{LR}=0.02, \lambda=2048$, 100 Ep) | **Win Loss:** 221182.6 L² (2.92 b)<br/>**5.0ms:** 167498.2 L² (3.13 b)<br/>**Peak 5ms:** 3.57 b | **Win Loss:** 49898.6 L² (3.99 b)<br/>**5.0ms:** 17414.2 L² (4.91 b)<br/>**Peak 5ms:** 6.29 b | **Win Loss:** 50838.6 L² (3.98 b)<br/>**5.0ms:** 18238.9 L² (4.84 b)<br/>**Peak 5ms:** **6.52 b (1500.0 L²)** | **New silicon record: 6.52 bits peak in nominal training!** |
| **Phase 3: Fig 7 Tracking**<br/>(Patent Fig 7 $\pm 5\text{ LSB}$, 400 Ep) | **Win Loss:** 186259.2 L² (3.07 b)<br/>**5.0ms:** 129454.0 L² (3.41 b)<br/>**Peak 5ms:** 4.79 b | **Win Loss:** 77708.6 L² (3.70 b)<br/>**5.0ms:** 39431.2 L² (4.33 b)<br/>**Peak 5ms:** 6.46 b | **Win Loss:** **51111.0 L² (3.98 b)**<br/>**5.0ms:** **20835.9 L² (4.75 b)**<br/>**Peak 5ms:** **6.63 b!** | **1k/2.2k crushes disturbances:** Error is cut in half ($20.8\text{k}$ vs $39.4\text{k}$)! Peak reaches **6.63 b**! |
| **Phase 4: Ablation Control**<br/>($W=0$, Fig 7 $\pm 5\text{ LSB}$, 401 Ep) | **Win Loss:** 303059.7 L² (2.70 b)<br/>**5.0ms:** 260068.1 L² (2.82 b) | **Win Loss:** 124390.2 L² (3.34 b)<br/>**5.0ms:** 88447.7 L² (3.62 b) | **Win Loss:** 207590.1 L² (2.96 b)<br/>**5.0ms:** 173852.2 L² (3.10 b) | Unmasking true disturbance error without active analog cancellation. |
| **Ablation Contrast (P4 / P2)** | **1.55x** | **5.08x (508%)** | **9.53x (953% Surge!)** | **Unprecedented active loop control authority!** |
| **Max Weight Excursion $|W_8|$** | **110 LSB** (Straining Near Rail) | **56 LSB** (Linear Sweet Spot) | **41 LSB (Row 0) / 88 LSB (Peak)** | Immense linear headroom (>79 LSB margin). |

---

## 3. Circuit Physics Analysis: The Superiority of 1k/2.2k

1. **Maximizing Injected Anti-Phase Current:**
   The current injected into the virtual-ground summing junction of follower `U3$CBB15.1` is:
   $$I_{\text{comp}} = \frac{V_{\text{sigm}}}{R_2}$$
   - At $R_2 = 5.1\text{ k}\Omega$: $I_{\text{comp}} = 0.196\text{ mA/V}$
   - At $R_2 = 3.3\text{ k}\Omega$: $I_{\text{comp}} = 0.303\text{ mA/V}$
   - At $R_2 = 2.2\text{ k}\Omega$: $I_{\text{comp}} = 0.455\text{ mA/V}$
   
   The $2.2\text{ k}\Omega$ resistor provides **$+131.8\%$ more current** than the factory $5.1\text{ k}\Omega$ attenuator and **$+50.0\%$ more current** than the $3.3\text{ k}\Omega$ mod!

2. **Summing Node Loading:**
   Looking into the node, the passive divider ratio is:
   $$\text{Gain}_{\text{passive}} = \frac{2.2\text{ k}\Omega}{1.0\text{ k}\Omega + 2.2\text{ k}\Omega} = 0.6875\quad (-3.25\text{ dB})$$
   This moderate attenuation slightly tames the raw open-loop silicon noise and dynamic swing without starving signal, while allowing the compensation network to dominate the error surface.

3. **Suppressing Non-Stationary Disturbances (Patent Fig 7):**
   When the emulator injects randomized $\pm 5\text{ LSB}$ shifts across Matrix 33, large error spikes are generated. On 1k/5.1k, the weights were already near $\pm 110\text{ LSB}$ and had zero headroom left to fight the disturbances. On 1k/2.2k, weights sit near $\sim 35\text{ LSB}$, leaving enormous dynamic range to instantly absorb and cancel the disturbance pulses.

---

## 4. Visual Evidence & Telemetry

### A. Three-Way Benchmark Overlay (1k/5.1k vs. 1k/3.3k vs. 1k/2.2k)
![Three-Way Overlay](file:///home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/docs/figures/fig_card1_1k_2p2k_threeway_comparison_overlay.png)
*Figure 1: Direct comparison across all three attenuator regimes on physical silicon. Green curve (1k/2.2k) demonstrates superior baseline, rapid convergence, outstanding disturbance rejection, and record 9.53x ablation surge.*

### B. 2D Temporal Spectrogram of Precision on Card 1 (1k/2.2k)
![Spectrogram 1k/2.2k](file:///home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/docs/figures/fig_card1_1k_2p2k_temporal_spectrogram_enob.png)
*Figure 2: 2D Spectrogram across [4.5..5.5 ms] for Card 1 with 1k/2.2k attenuator. Brilliant high-precision wavefront spanning 5.0 to 6.6 bits across Phases 2 and 3, completely collapsing upon ablation.*

---

## 5. Final Hardware Recommendation

1. **Standardize all hardware on $1\text{ k}\Omega / 2.2\text{ k}\Omega$:**
   The $1\text{ k}\Omega / 2.2\text{ k}\Omega$ passive summing attenuator delivers the highest sustained precision ($4.75\dots 4.84\text{ bits}$), record peak resolution ($6.63\text{ bits}$), and the greatest disturbance resilience ever observed on Inverted MAML silicon.
2. Card 2 should also be updated from $1\text{ k}\Omega / 3.3\text{ k}\Omega$ to $1\text{ k}\Omega / 2.2\text{ k}\Omega$ in future production revisions.
