# Inverted MAML Card 1: Cold-Start 2-Beat Analog Bit-Slicing, Anti-Windup & Forward Hadamard Propagation (FHP)
## Comprehensive Scientific Validation, Multi-Round Hyperparameter Search & 100% Open-Source ASIC Blueprint
**License:** **100% Open Source under Solderpad Hardware License v2.1 (`SHL-2.1`)** — including commercial ASIC/IC silicon manufacturing, PCB layouts, schematics, FPGA gateware, firmware, and royalty-free patent grant for **Swedish Patent Application SE 2630397-4**.

---

## Executive Summary & Scientific Scope

This comprehensive report documents the complete cold-start Card 1 (`1k/2.2k` attenuator, Trion `T120F324` + `T20F256`) validation of 2-beat time-division multiplexed **Analog Bit Slicing (`K=1`)** after resolving the two-layer backpropagation sign (`dx8`), M3 scaling (`>> 6`), M3 active-row saturation (`±25 LSB` vs frozen `±40 LSB` staircases), IEEE 802.3 Ethernet batch frame padding, and **integrated-L2 back-calculation anti-windup** (`T120_SOC_ETH_FW v2.2-MAML`, `HW_LOGIC 0x20261030`).

- **Unheated Cold Reference (`cold_verify_k1.json`):** `Cold / Regler ON` achieves **`9.45 b`** and `Cold / Regler OFF (W8=0)` achieves **`9.45 b`** combined 8-bit ENOB — well above the `> 8.0 b` cold baseline criterion.
- **Primary Evaluated Dataset (`opt_r20dc_fix_lr0p055_l2_1920_mom0p85_cl90.json`, `4,702` pairs):** `LR=0.055, L2=1920, Momentum=0.85, Clamp=±90 LSB, K=1, 40% PWM` delivers **`+0.82 b`** detrended `Warm ON` lift above continuous PCHIP baseline $E_{\text{base}}(t)$, **`1.58x`** detrended loss suppression, **`+0.80 b`** hot convergence climb, and **`0.51`** anti-windup recovery (Composite Score **`+1.902`**).
- **Cumulative Optimization Progress (`R1–R19`):** Best verified configuration so far is **Round 7** (`LR=0.055, L2=2048, Mom=0.85, Clamp=±75`) with Composite Score **`+2.665`**.

---

## 1. 2x2 Factorial Performance Accounting, Phase Telemetry & Hyperparameter Optimization

### Table 1A: 2x2 Factorial Performance Accounting

| Factorial Condition | Thermal State | Regulation State | Mean Loss (LSB²) | Mean Comb ENOB | Peak Comb ENOB | MSB / LSB Mean | W8 Range [MSB / LSB] |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **1. Cold Closed-Loop** | Heaters OFF (0%) | Comp ON (`K=1`, L2=1920) | 16,734.8 | **8.58 b** | 9.50 b | 4.54 / 4.60 b | `[-38, 90]` / `[-46, 82]` |
| **2. Cold Open-Loop** | Heaters OFF (0%) | Comp OFF (`W8=0`) | 15,154.6 | **8.69 b** | 9.50 b | 4.56 / 4.70 b | `[0, 0]` (0% leak) |
| **3. Warm Closed-Loop** | Heaters ON (40% @ 1Hz) | Comp ON (`K=1`, L2=1920) | **33,633.9** | **7.87 b** | 9.50 b | 4.06 / 4.17 b | `[-90, 90]` / `[-76, 90]` |
| **4. Warm Open-Loop** | Heaters ON (40% @ 1Hz) | Comp OFF (`W8=0`) | 60,094.1 | 6.92 b | 9.05 b | 3.62 / 3.71 b | `[0, 0]` (0% leak) |

### Table 1B: Latest Hyperparameter & Detrended Trend-Curve Results (`R1–R19`)

| Round | Dataset | LR | L2 Reg | Mom | Clamp | Lift vs E_base | Loss Ratio | Hot Climb | Jitter | Recovery | Composite Score |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| R1 | `opt_r1dc_fix_lr0p03_l2_1024_mom0p90_cl75.json` | `0.03` | `1024` | `0.9` | `±75` | `+1.00 b` | `1.71x` | `+0.95 b` | `0.40 b` | `0.00` | **`+1.799`** |
| R2 | `opt_r2dc_fix_lr0p035_l2_1536_mom0p85_cl75.json` | `0.035` | `1536` | `0.85` | `±75` | `+0.99 b` | `1.69x` | `+1.16 b` | `0.39 b` | `0.00` | **`+1.957`** |
| R3 | `opt_r3dc_fix_lr0p02_l2_2560_mom0p80_cl70.json` | `0.02` | `2560` | `0.8` | `±70` | `+0.04 b` | `1.00x` | `+0.24 b` | `0.34 b` | `1.00` | **`+0.204`** |
| R4 | `opt_r4dc_fix_lr0p05_l2_1792_mom0p85_cl80.json` | `0.05` | `1792` | `0.85` | `±70` | `+1.08 b` | `1.78x` | `+0.97 b` | `0.40 b` | `0.50` | **`+2.480`** |
| R5 | `opt_r5dc_fix_lr0p055_l2_1792_mom0p85_cl85.json` | `0.055` | `1792` | `0.85` | `±85` | `+1.12 b` | `1.77x` | `+1.37 b` | `0.42 b` | `0.00` | **`+2.393`** |
| R6 | `opt_r6dc_fix_lr0p055_l2_1792_mom0p80_cl90.json` | `0.055` | `1792` | `0.8` | `±90` | `+0.99 b` | `1.72x` | `+1.02 b` | `0.40 b` | `0.00` | **`+1.770`** |
| R7 ★ | `opt_r7dc_fix_lr0p055_l2_2048_mom0p85_cl75.json` | `0.055` | `2048` | `0.85` | `±75` | `+1.04 b` | `1.74x` | `+1.17 b` | `0.40 b` | `0.50` | **`+2.665`** |
| R8 | `opt_r7dc_fix_verify13m_lr0p055_l2_2048_mom0p85_cl75.json` | `0.055` | `2048` | `0.85` | `±75` | `+1.16 b` | `1.85x` | `+0.68 b` | `0.42 b` | `0.00` | **`+1.855`** |
| R9 | `opt_r10dc_fix_lr0p055_l2_1920_mom0p85_cl75.json` | `0.055` | `1920` | `0.85` | `±75` | `+0.81 b` | `1.59x` | `+0.66 b` | `0.38 b` | `0.50` | **`+1.756`** |
| R10 | `opt_r11dc_fix_lr0p055_l2_1920_mom0p85_cl78.json` | `0.055` | `1920` | `0.85` | `±78` | `+0.96 b` | `1.67x` | `+1.13 b` | `0.40 b` | `0.00` | **`+1.898`** |
| R11 | `opt_r12dc_fix_lr0p055_l2_1920_mom0p85_cl80.json` | `0.055` | `1920` | `0.85` | `±80` | `+0.95 b` | `1.70x` | `+0.98 b` | `0.42 b` | `0.00` | **`+1.810`** |
| R12 | `opt_r13dc_fix_lr0p055_l2_1920_mom0p85_cl82.json` | `0.055` | `1920` | `0.85` | `±82` | `+1.04 b` | `1.75x` | `+0.83 b` | `0.42 b` | `0.00` | **`+1.721`** |
| R13 | `opt_r14dc_fix_lr0p055_l2_1920_mom0p85_cl85.json` | `0.055` | `1920` | `0.85` | `±85` | `+1.12 b` | `1.78x` | `+1.06 b` | `0.43 b` | `0.50` | **`+2.645`** |
| R14 | `opt_r15dc_fix_lr0p055_l2_1920_mom0p85_cl90.json` | `0.055` | `1920` | `0.85` | `±90` | `+0.78 b` | `1.55x` | `+0.97 b` | `0.39 b` | `0.67` | **`+2.117`** |
| R15 | `opt_r16dc_fix_lr0p055_l2_1920_mom0p85_cl100.json` | `0.055` | `1920` | `0.85` | `±100` | `+0.94 b` | `1.67x` | `+0.89 b` | `0.40 b` | `0.75` | **`+2.443`** |
| R16 | `opt_r17dc_fix_lr0p055_l2_1920_mom0p85_cl90.json` | `0.055` | `1920` | `0.85` | `±90` | `+0.70 b` | `1.52x` | `+0.82 b` | `0.34 b` | `0.75` | **`+2.026`** |
| R17 | `opt_r18dc_fix_lr0p055_l2_1920_mom0p85_cl90.json` | `0.055` | `1920` | `0.85` | `±90` | `+0.88 b` | `1.65x` | `+1.25 b` | `0.39 b` | `0.50` | **`+2.385`** |
| R18 | `opt_r19dc_fix_lr0p055_l2_1920_mom0p85_cl90.json` | `0.055` | `1920` | `0.85` | `±90` | `+0.77 b` | `1.52x` | `+0.74 b` | `0.37 b` | `0.67` | **`+1.888`** |
| R19 | `opt_r20dc_fix_lr0p055_l2_1920_mom0p85_cl90.json` | `0.055` | `1920` | `0.85` | `±90` | `+0.82 b` | `1.58x` | `+0.80 b` | `0.41 b` | `0.51` | **`+1.902`** |
*Active Next Optimization Target (`Round 20`):* `LR=0.055, L2=2048, Momentum=0.85, Clamp=±75 LSB` (GP predicted `+0.000 ± 0.000`).

### Table 1C: Phase-by-Phase Telemetry (`opt_r20dc_fix_lr0p055_l2_1920_mom0p85_cl90.json`)

| Phase | Regime | Pairs | Comb ENOB (`Start -> Late`, Mean) | Δ vs E_base | Total Loss (`Start -> Late`) | Loss Ratio | W8 Peak `[M, L]` | W3 Peak | W8 nz |
| :--- | :--- | ---: | :---: | :---: | :---: | :---: | :---: | :---: | ---: |
| P1 | Cold / Regler ON | 446 | `8.40 -> 8.67` (**8.58 b**) | — | `20906 -> 15183` | — | `[90, 82]` | `14` | `446` |
| P2 | Cold / Regler OFF | 414 | `8.67 -> 8.78` (**8.69 b**) | — | `17205 -> 13670` | — | `[0, 0]` | `0` | `0` |
| P3 | 30% Heat / Regler ON | 400 | `8.86 -> 8.60` (**8.73 b**) | **+0.24 b** | `11876 -> 16285` | **1.31x** | `[90, 74]` | `12` | `400` |
| P4 | 30% Heat / Regler OFF | 382 | `8.34 -> 8.07` (**8.16 b**) | **-0.05 b** | `22816 -> 28802` | **0.98x** | `[0, 0]` | `0` | `0` |
| P5 | 30% Heat / Regler ON | 353 | `8.12 -> 8.09` (**8.16 b**) | **+0.25 b** | `27529 -> 27481` | **1.29x** | `[90, 90]` | `22` | `353` |
| P6 | 30% Heat / Regler OFF | 350 | `7.52 -> 7.39` (**7.50 b**) | **+0.01 b** | `39951 -> 43715` | **1.01x** | `[0, 0]` | `0` | `0` |
| P7 | 30% Heat / Regler ON | 334 | `7.46 -> 7.89` (**7.90 b**) | **+0.78 b** | `42646 -> 33132` | **1.53x** | `[90, 90]` | `26` | `334` |
| P8 | 30% Heat / Regler OFF | 320 | `7.19 -> 7.08` (**7.11 b**) | **+0.02 b** | `48151 -> 51368` | **0.99x** | `[0, 0]` | `0` | `0` |
| P9 | 40% Heat / Regler ON | 322 | `7.27 -> 7.64` (**7.74 b**) | **+0.89 b** | `47600 -> 37739` | **1.60x** | `[90, 90]` | `28` | `322` |
| P10 | 40% Heat / Regler OFF | 315 | `6.67 -> 6.34` (**6.49 b**) | **+0.02 b** | `63025 -> 73184` | **1.01x** | `[0, 0]` | `0` | `0` |
| P11 | 40% Heat / Regler ON | 207 | `6.63 -> 7.27` (**7.17 b**) | **+1.18 b** | `66378 -> 46507` | **1.81x** | `[90, 90]` | `29` | `207` |
| P12 | 40% Heat / Regler OFF | 284 | `6.03 -> 5.94` (**5.95 b**) | **+0.04 b** | `85506 -> 90078` | **1.00x** | `[0, 0]` | `0` | `0` |
| P13 | 40% Heat / Regler ON | 294 | `6.06 -> 6.98` (**6.93 b**) | **+1.25 b** | `85197 -> 54565` | **1.87x** | `[90, 90]` | `30` | `294` |
| P14 | 40% Heat / Regler OFF | 281 | `5.73 -> 5.69` (**5.72 b**) | **+0.03 b** | `100961 -> 103334` | **1.01x** | `[0, 0]` | `0` | `0` |

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
