# Inverted MAML Card 1: Cold-Start 2-Beat Analog Bit-Slicing, Anti-Windup & Forward Hadamard Propagation (FHP)
## Comprehensive Scientific Validation, Multi-Round Hyperparameter Search & 100% Open-Source ASIC Blueprint
**License:** **100% Open Source under Solderpad Hardware License v2.1 (`SHL-2.1`)** — including commercial ASIC/IC silicon manufacturing, PCB layouts, schematics, FPGA gateware, firmware, and royalty-free patent grant for **Swedish Patent Application SE 2630397-4**.

---

## Executive Summary & Scientific Scope

This comprehensive report documents the complete cold-start Card 1 (`1k/2.2k` attenuator, Trion `T120F324` + `T20F256`) validation of 2-beat time-division multiplexed **Analog Bit Slicing (`K=1`)** after resolving the two-layer backpropagation sign (`dx8`), M3 scaling (`>> 6`), M3 active-row saturation (`±25 LSB` vs frozen `±40 LSB` staircases), IEEE 802.3 Ethernet batch frame padding, and **integrated-L2 back-calculation anti-windup** (`T120_SOC_ETH_FW v2.2-MAML`, `HW_LOGIC 0x20261030`).

- **Unheated Cold Reference (`cold_verify_k1.json`):** `Cold / Regler ON` achieves **`9.45 b`** and `Cold / Regler OFF (W8=0)` achieves **`9.45 b`** combined 8-bit ENOB — well above the `> 8.0 b` cold baseline criterion.
- **Primary Evaluated Dataset (`opt_r4dc_fix_lr0p05_l2_1792_mom0p85_cl80.json`, `3,871` pairs):** `LR=0.05, L2=1792, Momentum=0.85, Clamp=±70 LSB, K=1, 40% PWM` delivers **`+1.08 b`** detrended `Warm ON` lift above continuous PCHIP baseline $E_{\text{base}}(t)$, **`1.78x`** detrended loss suppression, **`+0.97 b`** hot convergence climb, and **`0.50`** anti-windup recovery (Composite Score **`+2.480`**).
- **Cumulative Optimization Progress (`R1–R5`):** Best verified configuration so far is **Round 4** (`LR=0.05, L2=1792, Mom=0.85, Clamp=±70`) with Composite Score **`+2.480`**.

---

## 1. 2x2 Factorial Performance Accounting, Phase Telemetry & Hyperparameter Optimization

### Table 1A: 2x2 Factorial Performance Accounting

| Factorial Condition | Thermal State | Regulation State | Mean Loss (LSB²) | Mean Comb ENOB | Peak Comb ENOB | MSB / LSB Mean | W8 Range [MSB / LSB] |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **1. Cold Closed-Loop** | Heaters OFF (0%) | Comp ON (`K=1`, L2=1792) | 20,145.0 | **8.40 b** | 9.50 b | 4.41 / 4.43 b | `[-38, 70]` / `[-41, 70]` |
| **2. Cold Open-Loop** | Heaters OFF (0%) | Comp OFF (`W8=0`) | 23,117.4 | **8.35 b** | 9.43 b | 4.31 / 4.41 b | `[0, 0]` (0% leak) |
| **3. Warm Closed-Loop** | Heaters ON (40% @ 1Hz) | Comp ON (`K=1`, L2=1792) | **34,371.5** | **7.81 b** | 9.50 b | 4.05 / 4.12 b | `[-70, 70]` / `[-58, 70]` |
| **4. Warm Open-Loop** | Heaters ON (40% @ 1Hz) | Comp OFF (`W8=0`) | 76,898.5 | 6.33 b | 8.22 b | 3.39 / 3.46 b | `[0, 0]` (0% leak) |

### Table 1B: Latest Hyperparameter & Detrended Trend-Curve Results (`R1–R5`)

| Round | Dataset | LR | L2 Reg | Mom | Clamp | Lift vs E_base | Loss Ratio | Hot Climb | Jitter | Recovery | Composite Score |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| R1 | `opt_r1dc_fix_lr0p03_l2_1024_mom0p90_cl75.json` | `0.03` | `1024` | `0.9` | `±75` | `+1.00 b` | `1.71x` | `+0.95 b` | `0.40 b` | `0.00` | **`+1.799`** |
| R2 | `opt_r2dc_fix_lr0p035_l2_1536_mom0p85_cl75.json` | `0.035` | `1536` | `0.85` | `±75` | `+0.99 b` | `1.69x` | `+1.16 b` | `0.39 b` | `0.00` | **`+1.957`** |
| R3 | `opt_r3dc_fix_lr0p02_l2_2560_mom0p80_cl70.json` | `0.02` | `2560` | `0.8` | `±70` | `+0.04 b` | `1.00x` | `+0.24 b` | `0.34 b` | `1.00` | **`+0.204`** |
| R4 ★ | `opt_r4dc_fix_lr0p05_l2_1792_mom0p85_cl80.json` | `0.05` | `1792` | `0.85` | `±70` | `+1.08 b` | `1.78x` | `+0.97 b` | `0.40 b` | `0.50` | **`+2.480`** |
| R5 | `opt_r5dc_fix_lr0p055_l2_1792_mom0p85_cl85.json` | `0.055` | `1792` | `0.85` | `±85` | `+1.12 b` | `1.77x` | `+1.37 b` | `0.42 b` | `0.00` | **`+2.393`** |
*Active Next Optimization Target (`Round 6`):* `LR=0.055, L2=1792, Momentum=0.8, Clamp=±90 LSB` (GP predicted `+2.158 ± 0.667`).

### Table 1C: Phase-by-Phase Telemetry (`opt_r4dc_fix_lr0p05_l2_1792_mom0p85_cl80.json`)

| Phase | Regime | Pairs | Comb ENOB (`Start -> Late`, Mean) | Δ vs E_base | Total Loss (`Start -> Late`) | Loss Ratio | W8 Peak `[M, L]` | W3 Peak | W8 nz |
| :--- | :--- | ---: | :---: | :---: | :---: | :---: | :---: | :---: | ---: |
| P1 | Cold / Regler ON | 279 | `8.18 -> 8.45` (**8.40 b**) | — | `24114 -> 19771` | — | `[70, 70]` | `14` | `279` |
| P2 | Cold / Regler OFF | 300 | `8.30 -> 8.42` (**8.35 b**) | — | `22607 -> 20779` | — | `[0, 0]` | `0` | `0` |
| P3 | Warm / Regler ON | 1077 | `8.51 -> 8.01` (**8.28 b**) | **+0.86 b** | `19556 -> 29278` | **1.61x** | `[70, 70]` | `19` | `1077` |
| P4 | Warm / Regler OFF | 895 | `7.02 -> 6.40` (**6.67 b**) | **-0.01 b** | `52248 -> 71776` | **1.01x** | `[0, 0]` | `0` | `0` |
| P5 | Warm / Regler ON | 768 | `6.38 -> 7.04` (**7.15 b**) | **+1.19 b** | `71157 -> 52465` | **1.86x** | `[70, 70]` | `23` | `768` |
| P6 | Warm / Regler OFF | 552 | `5.79 -> 5.76` (**5.77 b**) | **+0.02 b** | `97639 -> 99490` | **1.02x** | `[0, 0]` | `0` | `0` |

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
