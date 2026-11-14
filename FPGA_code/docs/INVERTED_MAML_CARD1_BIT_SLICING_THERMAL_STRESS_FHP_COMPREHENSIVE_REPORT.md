# Inverted MAML Card 1: Cold-Start 2-Beat Analog Bit-Slicing, Anti-Windup & Forward Hadamard Propagation (FHP)
## Comprehensive Scientific Validation, Multi-Round Hyperparameter Search & 100% Open-Source ASIC Blueprint
**License:** **100% Open Source under Solderpad Hardware License v2.1 (`SHL-2.1`)** — including commercial ASIC/IC silicon manufacturing, PCB layouts, schematics, FPGA gateware, firmware, and royalty-free patent grant for **Swedish Patent Application SE 2630397-4**.

---

## Executive Summary & Scientific Scope

This comprehensive report documents the complete cold-start Card 1 (`1k/2.2k` attenuator, Trion `T120F324` + `T20F256`) validation of 2-beat time-division multiplexed **Analog Bit Slicing (`K=1`)** after resolving the two-layer backpropagation sign (`dx8`), M3 scaling (`>> 6`), M3 active-row saturation (`±25 LSB` vs frozen `±40 LSB` staircases), IEEE 802.3 Ethernet batch frame padding, and **integrated-L2 back-calculation anti-windup** (`T120_SOC_ETH_FW v2.2-MAML`, `HW_LOGIC 0x20261030`).

- **Unheated Cold Reference (`cold_verify_k1.json`):** `Cold / Regler ON` achieves **`9.45 b`** and `Cold / Regler OFF (W8=0)` achieves **`9.45 b`** combined 8-bit ENOB — well above the `> 8.0 b` cold baseline criterion.
- **Primary Evaluated Dataset (`opt_r7_lr0p035_l2_768_mom0p90_cl75.json`, `3,917` pairs):** `LR=0.035, L2=768, Momentum=0.9, Clamp=±75 LSB, K=1, 40% PWM` delivers **`+0.18 b`** detrended `Warm ON` lift above continuous PCHIP baseline $E_{\text{base}}(t)$, **`1.38x`** detrended loss suppression, **`+0.48 b`** hot convergence climb, and **`0.95`** anti-windup recovery (Composite Score **`+1.191`**).
- **Cumulative Optimization Progress (`R1–R7`):** Best verified configuration so far is **Round 2** (`LR=0.035, L2=1536, Mom=0.85, Clamp=±75`) with Composite Score **`+2.004`**.

---

## 1. 2x2 Factorial Performance Accounting, Phase Telemetry & Hyperparameter Optimization

### Table 1A: 2x2 Factorial Performance Accounting

| Factorial Condition | Thermal State | Regulation State | Mean Loss (LSB²) | Mean Comb ENOB | Peak Comb ENOB | MSB / LSB Mean | W8 Range [MSB / LSB] |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **1. Cold Closed-Loop** | Heaters OFF (0%) | Comp ON (`K=1`, L2=768) | 4,073.3 | **9.42 b** | 9.50 b | 5.57 / 5.77 b | `[-27, 15]` / `[-12, 18]` |
| **2. Cold Open-Loop** | Heaters OFF (0%) | Comp OFF (`W8=0`) | 4,840.9 | **9.39 b** | 9.50 b | 5.45 / 5.71 b | `[0, 0]` (0% leak) |
| **3. Warm Closed-Loop** | Heaters ON (40% @ 1Hz) | Comp ON (`K=1`, L2=768) | **7,659.9** | **9.13 b** | 9.50 b | 5.25 / 5.27 b | `[-48, 75]` / `[-42, 75]` |
| **4. Warm Open-Loop** | Heaters ON (40% @ 1Hz) | Comp OFF (`W8=0`) | 12,853.7 | 8.78 b | 9.50 b | 4.85 / 4.79 b | `[0, 0]` (0% leak) |

### Table 1B: Latest Hyperparameter & Detrended Trend-Curve Results (`R1–R7`)

| Round | Dataset | LR | L2 Reg | Mom | Clamp | Lift vs E_base | Loss Ratio | Hot Climb | Jitter | Recovery | Composite Score |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| R1 | `opt_r1_lr0p03_l2_1024_mom0p90_cl75.json` | `0.03` | `1024` | `0.9` | `±75` | `+0.66 b` | `1.57x` | `+0.74 b` | `0.33 b` | `0.67` | **`+1.957`** |
| R2 ★ | `opt_r2_lr0p035_l2_1536_mom0p85_cl75.json` | `0.035` | `1536` | `0.85` | `±75` | `+0.50 b` | `1.38x` | `+0.82 b` | `0.29 b` | `0.96` | **`+2.004`** |
| R3 | `opt_r3_lr0p02_l2_2560_mom0p80_cl70.json` | `0.02` | `2560` | `0.8` | `±70` | `+0.09 b` | `1.11x` | `+0.22 b` | `0.26 b` | `1.00` | **`+0.559`** |
| R4 | `opt_r4_lr0p045_l2_2048_mom0p88_cl75.json` | `0.045` | `2048` | `0.88` | `±75` | `+0.11 b` | `1.17x` | `+0.14 b` | `0.24 b` | `1.00` | **`+0.643`** |
| R5 | `opt_r5_lr0p03_l2_1024_mom0p85_cl75.json` | `0.03` | `1024` | `0.85` | `±75` | `+0.20 b` | `1.34x` | `+0.43 b` | `0.26 b` | `0.89` | **`+1.147`** |
| R6 | `opt_r6_lr0p025_l2_1280_mom0p92_cl75.json` | `0.025` | `1280` | `0.92` | `±75` | `+0.06 b` | `1.12x` | `+0.34 b` | `0.23 b` | `1.00` | **`+0.689`** |
| R7 | `opt_r7_lr0p035_l2_768_mom0p90_cl75.json` | `0.035` | `768` | `0.9` | `±75` | `+0.18 b` | `1.38x` | `+0.48 b` | `0.26 b` | `0.95` | **`+1.191`** |
*Active Next Optimization Target (`Round 8`):* `LR=0.04, L2=1536, Momentum=0.82, Clamp=±75 LSB` (GP predicted `+1.788 ± 0.405`).

### Table 1C: Phase-by-Phase Telemetry (`opt_r7_lr0p035_l2_768_mom0p90_cl75.json`)

| Phase | Regime | Pairs | Comb ENOB (`Start -> Late`, Mean) | Δ vs E_base | Total Loss (`Start -> Late`) | Loss Ratio | W8 Peak `[M, L]` | W3 Peak | W8 nz |
| :--- | :--- | ---: | :---: | :---: | :---: | :---: | :---: | :---: | ---: |
| P1 | Cold / Regler ON | 334 | `9.38 -> 9.42` (**9.42 b**) | — | `4438 -> 4204` | — | `[27, 18]` | `1` | `333` |
| P2 | Cold / Regler OFF | 296 | `9.40 -> 9.38` (**9.39 b**) | — | `5993 -> 4965` | — | `[0, 0]` | `0` | `0` |
| P3 | Warm / Regler ON | 1066 | `9.39 -> 9.35` (**9.38 b**) | **+0.01 b** | `5141 -> 4725` | **1.21x** | `[34, 33]` | `3` | `1066` |
| P4 | Warm / Regler OFF | 933 | `9.31 -> 8.83` (**8.99 b**) | **+0.02 b** | `5220 -> 11143` | **1.00x** | `[0, 0]` | `0` | `0` |
| P5 | Warm / Regler ON | 817 | `8.74 -> 8.76` (**8.80 b**) | **+0.29 b** | `11691 -> 12402` | **1.49x** | `[75, 75]` | `19` | `817` |
| P6 | Warm / Regler OFF | 471 | `8.42 -> 8.31` (**8.35 b**) | **+0.03 b** | `18601 -> 22121` | **1.01x** | `[0, 0]` | `0` | `0` |

---

## 2. Cold-Start Calibration, 2-Beat Bit Slicing & Integrated-L2 Anti-Windup Architecture
- **Single-Shot Cold DC Calibration (`Heaters OFF, W8=0`):** After a 60-second unheated cooldown, Card 1 locks static linear calibration pairs `(alpha_msb, beta_msb)` and `(alpha_lsb, beta_lsb)` permanently inside the T120 SoC (`0x1E subcmd 5`) without any runtime surrogate recalibration.
- **Integrated-L2 Back-Calculation Anti-Windup:** Rather than hard-clamping stale momentum integrators at the ±75 LSB rail, `maml_platform.c` feeds clamp overflow back into velocity (`vel -= overflow >> 2`), halves stale momentum on saturation frames, and enforces `±max(15, clamp/3) = ±25 LSB` on `W(3)` rows `0..5` so rows `6..7` temporal staircases (`±40 LSB`) remain strictly intact.

---

## 3. Empirical Visualizations & Telemetry

![Figure 1: Performance Timeline](figures/fig_card1_bs_comp_timeline.png)

![Figure 2: Multi-Round & Phase Heatmap](figures/fig_card1_bs_comp_heatmap.png)

### All W(8) (7x6 MSB+LSB) & W(3) (8x6 MSB+LSB) Weights (per-synapse individual trajectories across all 180 weights)
![Figure 3A: All 84 W(8) Weights](figures/fig_card1_bs_comp_all_w8_weights.png)

![Figure 3B: All 96 W(3) Weights](figures/fig_card1_bs_comp_all_w3_weights.png)

![Figure 4: Hot-Phase Convergence Comparison](figures/fig_card1_bs_comp_hot_convergence.png)

![Figure 5: 2x2 Factorial Summary](figures/fig_card1_bs_comp_factorial_summary.png)

![Figure 6: Physical Hardware Photograph](figures/fig_card2_pcb_thermal_heaters.jpg)

---

## 4. Solid-State Physics: The 2-Layer Triad Network & Forward Hadamard Propagation (FHP)
![Patent Fig 1: 2-Layer Triad Architecture](figures/fig_patent_fig1_architecture.jpg)

![Patent Fig 8: Forward Hadamard Propagation Circuit](figures/fig_patent_fig8_fhp_circuit.jpg)

**Open-Source Notice (`SHL-2.1`):** All hardware schematics, PCB layouts, commercial ASIC/IC silicon implementations, FPGA HDL, RISC-V C firmware, and Python tools are 100% open source under Solderpad Hardware License v2.1 with a perpetual, worldwide, royalty-free patent license under SE 2630397-4.
