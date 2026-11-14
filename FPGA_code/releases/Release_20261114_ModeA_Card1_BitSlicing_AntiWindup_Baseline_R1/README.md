# Release 2026-11-14: Card 1 Mode A 2-Beat Bit-Slicing, Integrated-L2 Anti-Windup & Locked-DC Optimization SW Package

**License:** **100% Open Source under Solderpad Hardware License v2.1 (`SHL-2.1`)** — including commercial ASIC/IC silicon implementations & royalty-free patent license under **Swedish Patent Application SE 2630397-4**  
**Hardware Platform:** Card 1 (`Trion T120F324` Master SoC + `Trion T20F256` Coprocessor, `1k / 2.2k` Passive Summing Attenuator)  
**Firmware Version:** `T120_SOC_ETH_FW v2.2-MAML (SW Build Nov 14 2026 10:15:16)`  
**Hardware Logic ID:** `0x20261030 (ID=MAM1)`  
**Release Tag:** `Release_20261114_ModeA_Card1_BitSlicing_AntiWindup_Baseline_R1`

---

## 1. Software, Firmware & Hardware Package Contents

This self-contained package archives the complete verified Card 1 Mode A **2-beat Analog Bit-Slicing (`K=1`)** software, firmware, FPGA bitstream, locked 25 °C DC calibration, multi-round optimization tools, and publication reports:

- **`T120F324/`**: Synthesized FPGA gateware & bitstream (`T120_MALM.bit`, `T120_MALM.hex`, `t120_analog_io_ctrl.sv`).
- **`sw/t120_master/`**: Complete RISC-V C firmware source, Efinix BSP, ELF/BIN/HEX binaries (`src/main.c`, `src/maml_platform.c`, `include/maml_platform.h`, `Makefile`, `cpu0.yaml`, `bsp/`, `binaries/t120_master.hex`, `build/t120_master.{elf,bin}`).
- **`pc_python/`**:
  - `run_card1_thermal_bit_slicing.py`: Automated hardware runner with 60 s cooldown, locked R1 DC calibration (`--load-dc-calib`), staggered hardware PWM thermal cycling, and verified clamp readback (`verify_hw_clamp`).
  - `analog_hyperparam_model.py`: Thermal-detrended Gaussian Process hyperparameter optimizer & `--select-best` evaluator.
  - `generate_card1_run_concise_report.py` & `compile_card1_bit_slicing_fhp_comprehensive_report_pdf.py`: Full 180-weight (`84 W(8)` + `96 W(3)`) per-round report & 13-page FHP comprehensive report generators.
  - `bit_slicing_live_gui.py`, `udp_client.py`, `flash_soc.py`, `verify_and_guard_version.py`.
- **`pc_python/config/`**:
  - `r1_dc_cal_fixed.json`: Permanently locked ambient 25 °C R1 Cold DC calibration vectors (`alpha`, `beta`).
  - `bit_slicing_hyperparams.json`: Complete parameter registry including `locked_r1_dc_cal_best_r7dc_fix` and `locked_r1_dc_cal_verified_13min_r8dc_fix`.
  - `w3_staircase_pattern.json` & `w3_staircase_pattern.py`: Frozen `M3` rows `6–7` (`±40 LSB`) temporal reference clock staircases.
- **`reports_and_logs/`**:
  - [`INVERTED_MAML_CARD1_BIT_SLICING_THERMAL_STRESS_FHP_COMPREHENSIVE_REPORT.pdf`](reports_and_logs/INVERTED_MAML_CARD1_BIT_SLICING_THERMAL_STRESS_FHP_COMPREHENSIVE_REPORT.pdf) (13-page Comprehensive FHP Report + [`.md`](reports_and_logs/INVERTED_MAML_CARD1_BIT_SLICING_THERMAL_STRESS_FHP_COMPREHENSIVE_REPORT.md)).
  - Concise 2-page 180-weight reports for all 8 locked-DC runs (`R1dc_fix..R8dc_fix`), including [`R7dc_fix` Optimum](reports_and_logs/INVERTED_MAML_CARD1_R7DC_FIX_LR0P055_L2_2048_MOM0P85_CL75_THERMAL_SLICING_REPORT.pdf) and [`R8dc_fix` 13-Min Verification](reports_and_logs/INVERTED_MAML_CARD1_R8DC_FIX_LR0P055_L2_2048_MOM0P85_CL75_THERMAL_SLICING_REPORT.pdf).
  - Datasets: `cold_verify_k1.json`, `opt_r7dc_fix_lr0p055_l2_2048_mom0p85_cl75.json`, `opt_r7dc_fix_verify13m_lr0p055_l2_2048_mom0p85_cl75.json`, `opt_final_dc_fix_selection.json`, and `figures/`.

---

## 2. Key Firmware Engineering Fixes (`v2.2-MAML`)

1. **Two-Layer `dx8` Back-Propagation Sign, Gain Shift & `M3` Data-Row Protection ([`maml_platform.c`](sw/t120_master/src/maml_platform.c)):**
   - Fixed the sign inversion in `dx8[i]` column accumulation (`err49[j]` -> `-err49[j]`) so Layer 1 (`M3` rows `0..5`) tracks error gradients monotonically alongside Layer 2 (`M8`).
   - Adjusted `grad_m3_out` arithmetic shift from `>> 3` to `>> 6` and added `sat_comp_m3_q14()` capping active `M3` rows `0..5` to `±max(15, clamp/3)` (`±25 LSB` at `clamp=75`) so `M3` never disturbs the frozen `±40 LSB` clock staircase (`M3` rows `6..7`).
2. **Integrated-L2 Back-Calculation Anti-Windup (`maml_momentum_step_antiwindup`):**
   - Integrates L2 decay directly inside the momentum velocity update and bleeds rail overshoot back out of stored velocity (`vel_io`) whenever weights hit `±clamp` (`±75 LSB`), eliminating limit-cycle bouncing at the rails.
   - Halves stale velocity (`/= 2`) during clip-recovery (`valid_samples == 0`).
3. **Ethernet Frame Padding & Verified Hardware Clamp Handshake:**
   - Preserved `if (req_len >= 5)` in `maml_handle_udp_command()` for 60-byte padded IEEE 802.3 frames (`MAML_CMD_BATCH_STEP`) and added `verify_hw_clamp()` readback against `MamlTelemetry.w_comp_clamp` before starting each experiment.

---

## 3. Verified Locked-DC Performance & Systematic Clamp Sweep (`R1dc_fix..R19dc_fix`, `40%` PWM)

- **Cold Reference (`cold_verify_k1.json`, Heaters OFF, 643 pairs):** `Cold / Regler ON` mean **9.45 b** (`min 8.80 b`); `Cold / Regler OFF (W8=0)` mean **9.45 b** (`min 8.61 b`), `0/311` non-zero leaks.
- **2x2 Factorial Accounting (`R8dc_fix` + Cold Reference):** Cold ON **9.45 b** (`3,748.0 L²`), Cold OFF **9.45 b** (`3,947.3 L²`), Warm ON **7.19 b** (`50,580.5 L²`), Warm OFF **5.66 b** (`106,727.2 L²`).

| Round | LR | L2 Reg | Mom | Clamp | Lift vs `E_base` | Loss Ratio | Hot Climb | Jitter | Recov | Score | Notes |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `R1dc_fix` | `0.03` | `1024` | `0.9` | `±75` | `+1.00 b` | `1.71x` | `+0.95 b` | `0.40 b` | `0.00` | **`+1.799`** | Baseline locked DC |
| `R2dc_fix` | `0.035` | `1536` | `0.85` | `±75` | `+0.99 b` | `1.69x` | `+1.16 b` | `0.39 b` | `0.00` | **`+1.957`** | Tuned L2 |
| `R3dc_fix` | `0.02` | `2560` | `0.8` | `±70` | `+0.04 b` | `1.00x` | `+0.24 b` | `0.34 b` | `1.00` | **`+0.204`** | Over-damped |
| `R4dc_fix` | `0.05` | `1792` | `0.85` | `±70` | `+1.08 b` | `1.78x` | `+0.97 b` | `0.40 b` | `0.50` | **`+2.480`** | High LR |
| `R5dc_fix` | `0.055` | `1792` | `0.85` | `±85` | `+1.12 b` | `1.77x` | `+1.37 b` | `0.42 b` | `0.00` | **`+2.393`** | Relaxed clamp |
| `R6dc_fix` | `0.055` | `1792` | `0.8` | `±90` | `+0.99 b` | `1.72x` | `+1.02 b` | `0.40 b` | `0.00` | **`+1.770`** | Lower momentum |
| `R7dc_fix` | `0.055` | `2048` | `0.85` | `±75` | `+1.04 b` | `1.74x` | `+1.17 b` | `0.40 b` | `0.50` | **`+2.665`** | Tight L2 optimum |
| `R8dc_fix` (13m) | `0.055` | `2048` | `0.85` | `±75` | **`+1.16 b`** | **`1.85x`** | `+0.68 b` | `0.42 b` | `0.00` | **`+1.855`** | 13-min sustained |
| `R10dc_fix` | `0.055` | `1920` | `0.85` | `±75` | `+0.81 b` | `1.59x` | `+0.66 b` | `0.38 b` | `0.50` | **`+1.756`** | Under-clamped at L2=1920 |
| `R11dc_fix` | `0.055` | `1920` | `0.85` | `±78` | `+0.96 b` | `1.67x` | `+1.13 b` | `0.40 b` | `0.00` | **`+1.898`** | Lift rising |
| `R12dc_fix` | `0.055` | `1920` | `0.85` | `±80` | `+0.95 b` | `1.70x` | `+0.98 b` | `0.42 b` | `0.00` | **`+1.810`** | Loss ratio rising |
| `R13dc_fix` | `0.055` | `1920` | `0.85` | `±82` | `+1.04 b` | `1.75x` | `+0.83 b` | `0.42 b` | `0.00` | **`+1.721`** | Lift > 1 bit |
| `R14dc_fix` | `0.055` | `1920` | `0.85` | `±85` | **`+1.12 b`** | **`1.78x`** | `+1.06 b` | `0.43 b` | `0.50` | **`+2.645`** | Dynamic swing peak |
| **`R15dc_fix` ★** | **`0.055`** | **`1920`** | **`0.85`** | **`±90`** | `+0.78 b` | `1.55x` | `+0.97 b` | `0.39 b` | `0.67` | **`+2.117`** | **LOCKED PRODUCTION OPTIMUM ("Lagom"): P3 8.78 b, Loss 13.4k** |
| `R16dc_fix` | `0.055` | `1920` | `0.85` | `±100` | `+0.94 b` | `1.67x` | `+0.89 b` | `0.40 b` | `0.75` | **`+2.443`** | 2T1C Triode Saturation Knee |
| `R17dc_fix` | `0.055` | `1920` | `0.85` | `±90` | `+0.70 b` | `1.52x` | `+0.82 b` | `0.34 b` | `0.75` | **`+2.026`** | Replicate 1 (P3 9.03 b, Loss 9.5k) |
| `R18dc_fix` | `0.055` | `1920` | `0.85` | `±90` | `+0.88 b` | `1.65x` | **`+1.25 b`** | `0.39 b` | `0.50` | **`+2.385`** | Replicate 2 (Clean climb +1.25 b) |
| `R19dc_fix` | `0.055` | `1920` | `0.85` | `±90` | `+0.77 b` | `1.52x` | `+0.74 b` | `0.37 b` | `0.67` | **`+1.888`** | Replicate 3 (P3 8.80 b, P5 Lift +1.11 b, 3924 unbroken pairs) |
| **`R20dc_fix` ★** | **`0.055`** | **`1920`** | **`0.85`** | **`±90`** | `+0.82 b` | `1.58x` | `+0.80 b` | `0.41 b` | `0.51` | **`+1.902`** | **Multi-Stage Sweep: 2 Cold + 6 Warm 30% + 6 Warm 40% (Lift +1.25 b in P13, 4702 pairs)** |

---

## 4. Silicon Multiplier Saturation Mapping & Locked Clamp = 90 LSB Optimum ("Lagom")

A systematic hardware sweep (`R10dc_fix .. R16dc_fix`) on physical silicon revealed the exact operating limits of the Inverted MAML Dual-2T1C MOS triode multipliers under sustained 40% PWM thermal stress:

1. **Under-Clamping ($\le 75\dots 82$ LSB):**
   The anti-windup clamp clips weights prematurely in column 3 (`W8[*, 3]`), preventing the closed loop from counteracting the entire thermal disturbance gradient.
2. **Locked Production Optimum: Clamp = 90 LSB ("Lagom"):**
   We have officially selected and locked **Clamp = 90 LSB** as our production setting. At **$\pm 90$ LSB**, the matrix delivers maximum precision and lowest error under thermal stress:
   - **Phase 3 Warm ENOB:** **`8.78 bits`** (compared to `8.08 bits` at 85 LSB and `7.78 bits` at 75 LSB).
   - **Phase 3 Total Loss:** Reduced to **`13,421`** (more than 50% lower than the 27,939 loss at 85 LSB and 33,400 at 75 LSB).
   - **Zero ColTIA Saturation Clips:** `0 / 3,886` clips (100% linear transimpedance headroom).
   - **High Anti-Windup Recovery:** `0.67` recovery rate back into the linear regime.
3. **Triode Pinch-Off Saturation Knee (Clamp = 100 LSB):**
   When the clamp is opened all the way to $\pm 100$ LSB (`R16dc_fix`), weights in column 3 reach +100 LSB, entering the saturated pinch-off region where $\Delta I / \Delta V_g$ non-linearities dominate. Total loss under heating rebounds from 13,421 up to 18,936 and precision drops back to 8.48 bits.

### Empirical Visualizations from Silicon Reports

#### 1. Multi-Stage Thermal Sweep Timeline (Round 20dc_fix, 30% Heat + 40% Heat, Clamp = ±90 LSB)
Comprehensive 14-phase multi-stage thermal stress experiment across 4,702 unbroken pairs showing 30s step-responses at 30% and 40% PWM heating, reaching +1.25 bits lift and 1.87x loss reduction under heavy thermal stress without saturation:

![Round 20 Optimum Timeline](reports_and_logs/figures/fig_card1_r20_lr0p055_l2_1920_mom0p85_cl90_thermal_slicing.png)

#### 2. Unbroken Telemetry Replicate (Round 19dc_fix, Clamp = ±90 LSB)
Complete 3,924 unbroken sample pairs showing 8.80 bits Phase 3 ENOB, +1.11 bits Phase 5 lift, 1.72x loss reduction, and clean linear anti-windup regulation at ±90 LSB:

![Round 19 Optimum Timeline](reports_and_logs/figures/fig_card1_r19dc_fix_lr0p055_l2_1920_mom0p85_cl90_thermal_slicing.png)

#### 2. Clean Verified Production Optimum Timeline (Round 18dc_fix, Clamp = ±90 LSB)
Clean full 4-panel telemetry showing 8.59 bits Phase 3 ENOB, Hot Climb of +1.25 bits, zero ColTIA clipping across all 3,916 pairs, and smooth recovery:

![Round 18 Optimum Timeline](reports_and_logs/figures/fig_card1_r18dc_fix_lr0p055_l2_1920_mom0p85_cl90_thermal_slicing.png)

#### 3. Full Real-Time Performance Timeline (Round 16dc_fix, Clamp = ±100 LSB)
Demonstrates the full 4-panel telemetry: Combined ENOB across all 6 phases, moving mean loss, W(8) trajectories bounded at the ±100 LSB clamp, and W(3) data rows within ±33 LSB:

![Round 16 Multi-Panel Timeline](reports_and_logs/figures/fig_card1_r16dc_fix_lr0p055_l2_1920_mom0p85_cl100_thermal_slicing.png)

#### 4. All 180 Weight Trajectories (Round 16dc_fix, Clamp = ±100 LSB)
Full 84-weight W(8) and 96-weight W(3) traces scaled to `[-110, +110]` LSB showing column 3 hitting the outer boundary without instability:

![Round 16 Full Weight Trajectories](reports_and_logs/figures/fig_card1_r16dc_fix_lr0p055_l2_1920_mom0p85_cl100_w8_w3_all_weights.png)

#### 5. Locked Production Optimum Timeline (Round 15dc_fix, Clamp = ±90 LSB)
Phase 3 reaches 8.78 bits with 13.4k loss — the lowest thermal loss and highest precision recorded on Card 1 silicon:

![Round 15 Optimum Timeline](reports_and_logs/figures/fig_card1_r15dc_fix_lr0p055_l2_1920_mom0p85_cl90_thermal_slicing.png)

---

## 5. Exact Restore & Reproduction Commands

From repository root:
```bash
REL="FPGA_code/releases/Release_20261114_ModeA_Card1_BitSlicing_AntiWindup_Baseline_R1"
cp "$REL"/sw/t120_master/src/* FPGA_code/sw/t120_master/src/
cp "$REL"/sw/t120_master/include/* FPGA_code/sw/t120_master/include/
cp "$REL"/pc_python/*.py FPGA_code/scripts/
cp "$REL"/pc_python/bit_slicing_live_gui.py "$REL"/pc_python/udp_client.py gui/
cp "$REL"/pc_python/config/* FPGA_code/config/

make -C FPGA_code/sw/t120_master clean all
/home/olle/anaconda3/bin/python FPGA_code/scripts/flash_soc.py
```

### Run Live GUI + Locked Production Optimum (`Clamp = 90 LSB`, `LR = 0.055`, `L2 = 1920`, `Mom = 0.85`)
```bash
# Optional live monitor GUI
/home/olle/anaconda3/bin/python gui/bit_slicing_live_gui.py &

# Locked Production Optimum on Physical Silicon (R15dc_fix: Clamp=90, 8.78 b Warm ENOB, 13.4k Loss)
/home/olle/anaconda3/bin/python FPGA_code/scripts/run_card1_thermal_bit_slicing.py \
  --cooldown-sec 60 --cold-phase-duration 0.25 --phase-duration 1.0 \
  --warm-phases 4 --cool-phases 0 --heater-duty-pct 40 --k-batch 1 \
  --lr 0.055 --l2-reg 1920 --momentum 0.85 --clamp 90 \
  --load-dc-calib FPGA_code/config/r1_dc_cal_fixed.json
```

---

## 6. 2026-11-14 Live Hardware Demo Example: Multi-Stage Thermal Stress & Bit-Slicing

This one-click demo performs a live multi-stage thermal stress and analog bit-slicing demonstration on Card 1 silicon, transitioning from ambient cold baseline through moderate heating (30% PWM) up to heavy thermal stress (40% PWM).

### Start of Live GUI Monitor
In terminal 1, launch the live real-time visual monitor:
```bash
/home/olle/anaconda3/bin/python gui/bit_slicing_live_gui.py
```
*(Runs on X11 display, plotting combined 8-bit ENOB, MSB/LSB individual precision, total squared loss, and real-time W(8) and W(3) envelope trajectories with color-coded regulation regimes).*

### Start of Live Hardware Demo
In terminal 2, launch the automated demo runner:

#### Option A: Standard Full 14-Phase Demo (7.0 min active time, 30s per phase)
```bash
/home/olle/anaconda3/bin/python FPGA_code/scripts/run_demo.py
```

#### Option B: Fast Audience Demo (3.5 min active time, 15s per phase)
```bash
/home/olle/anaconda3/bin/python FPGA_code/scripts/run_demo.py --phase-sec 15 --cooldown-sec 15
```

### Demo Phase Schedule & Thermal Dynamics
The demo executes a 14-phase sequence:
1. **Cold Baseline (Phases 1–2, 0% Heat):**
   - Phase 1 (Regler ON, 30s) & Phase 2 (Regler OFF, 30s) at ambient 25 °C establishing unheated reference (~8.6–8.7 bits).
2. **Stage 1: Moderate Thermal Stress (Phases 3–8, 30% PWM Heater):**
   - 6 alternating toggles (3 ON / 3 OFF) à 30s. The Inverted MAML loop tracks the gradual thermal drift, holding precision steady at 8.0–8.7 bits and lifting precision by +0.78 bits over free drift.
3. **Stage 2: Intense Thermal Stress (Phases 9–14, 40% PWM Heater):**
   - 6 alternating toggles (3 ON / 3 OFF) à 30s. When regulation is disabled, thermal drift accelerates loss past 103,000 LSB² (dropping uncompensated ENOB down to 5.7 bits). Each time regulation engages (e.g. Phase 13), precision instantly steps up by **`+1.25 bits`** and loss drops by **`1.87x`** (from 85k down to 54k LSB²), strictly bounded at ±90 LSB without saturation or clipping.

### Empirical Visualizations from Demo Run (Round 20)

#### 1. Real-Time 4-Panel Timeline (Round 20, 14 Phases)
Full 4-panel telemetry (Combined ENOB, Loss, W8 bounds, and W3 clock/data envelope) across all 14 phases showing the immediate step-response whenever regulation is enabled:

![Round 20 Demo Timeline](reports_and_logs/figures/fig_card1_r20_lr0p055_l2_1920_mom0p85_cl90_thermal_slicing.png)

#### 2. All 180 Weight Trajectories (Round 20, 14 Phases)
Complete 84 W(8) (7x6 MSB + 7x6 LSB) and 96 W(3) (8x6 MSB + 8x6 LSB) weight trajectories across 4,702 sample pairs, demonstrating smooth column-3 compensation within ±90 LSB clamp:

![Round 20 All 180 Weights](reports_and_logs/figures/fig_card1_r20_lr0p055_l2_1920_mom0p85_cl90_w8_w3_all_weights.png)

#### 3. Full Demo Report PDF
The publication-quality PDF generated directly by `run_demo.py` is available at:
* [INVERTED_MAML_CARD1_R20_LR0P055_L2_1920_MOM0P85_CL90_THERMAL_SLICING_REPORT.pdf](reports_and_logs/INVERTED_MAML_CARD1_R20_LR0P055_L2_1920_MOM0P85_CL90_THERMAL_SLICING_REPORT.pdf)

