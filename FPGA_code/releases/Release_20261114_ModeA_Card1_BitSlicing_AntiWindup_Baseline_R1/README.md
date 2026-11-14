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

## 3. Verified Locked-DC Performance (`R1dc_fix..R8dc_fix`, `K=1`, `40%` PWM)

- **Cold Reference (`cold_verify_k1.json`, Heaters OFF, 643 pairs):** `Cold / Regler ON` mean **9.45 b** (`min 8.80 b`); `Cold / Regler OFF (W8=0)` mean **9.45 b** (`min 8.61 b`), `0/311` non-zero leaks.
- **2x2 Factorial Accounting (`R8dc_fix` + Cold Reference):** Cold ON **9.45 b** (`3,748.0 L²`), Cold OFF **9.45 b** (`3,947.3 L²`), Warm ON **7.19 b** (`50,580.5 L²`), Warm OFF **5.66 b** (`106,727.2 L²`).

| Round | LR | L2 Reg | Mom | Clamp | Lift vs `E_base` | Loss Ratio | Hot Climb | Jitter | Recov | Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `R1dc_fix` | `0.03` | `1024` | `0.9` | `±75` | `+1.00 b` | `1.71x` | `+0.95 b` | `0.40 b` | `0.00` | **`+1.799`** |
| `R2dc_fix` | `0.035` | `1536` | `0.85` | `±75` | `+0.99 b` | `1.69x` | `+1.16 b` | `0.39 b` | `0.00` | **`+1.957`** |
| `R3dc_fix` | `0.02` | `2560` | `0.8` | `±70` | `+0.04 b` | `1.00x` | `+0.24 b` | `0.34 b` | `1.00` | **`+0.204`** |
| `R4dc_fix` | `0.05` | `1792` | `0.85` | `±70` | `+1.08 b` | `1.78x` | `+0.97 b` | `0.40 b` | `0.50` | **`+2.480`** |
| `R5dc_fix` | `0.055` | `1792` | `0.85` | `±85` | `+1.12 b` | `1.77x` | `+1.37 b` | `0.42 b` | `0.00` | **`+2.393`** |
| `R6dc_fix` | `0.055` | `1792` | `0.8` | `±90` | `+0.99 b` | `1.72x` | `+1.02 b` | `0.40 b` | `0.00` | **`+1.770`** |
| **`R7dc_fix` ★** | **`0.055`** | **`2048`** | **`0.85`** | **`±75`** | `+1.04 b` | `1.74x` | `+1.17 b` | `0.40 b` | `0.50` | **`+2.665`** |
| **`R8dc_fix` (13m)** | **`0.055`** | **`2048`** | **`0.85`** | **`±75`** | **`+1.16 b`** | **`1.85x`** | `+0.68 b` | `0.42 b` | `0.00` | **`+1.855`** |

---

## 4. Exact Restore & Reproduction Commands

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

### Run Live GUI + Verified `R7dc_fix` / `R8dc_fix` Optimum (`LR=0.055, L2=2048, Mom=0.85, Clamp=75`)
```bash
# Optional live monitor GUI
/home/olle/anaconda3/bin/python gui/bit_slicing_live_gui.py &

# Standard 4.5-min optimization benchmark (R7dc_fix configuration, Score +2.665)
/home/olle/anaconda3/bin/python FPGA_code/scripts/run_card1_thermal_bit_slicing.py \
  --cooldown-sec 60 --cold-phase-duration 0.25 --phase-duration 1.0 \
  --warm-phases 4 --cool-phases 0 --heater-duty-pct 40 --k-batch 1 \
  --lr 0.055 --l2-reg 2048 --momentum 0.85 --clamp 75 \
  --load-dc-calib FPGA_code/config/r1_dc_cal_fixed.json

# Full 13-min sustained thermal verification (R8dc_fix configuration, +1.16 b Lift / 1.85x LossR)
/home/olle/anaconda3/bin/python FPGA_code/scripts/run_card1_thermal_bit_slicing.py \
  --cooldown-sec 60 --cold-phase-duration 0.5 --phase-duration 2.0 \
  --warm-phases 6 --cool-phases 0 --heater-duty-pct 40 --k-batch 1 \
  --lr 0.055 --l2-reg 2048 --momentum 0.85 --clamp 75 \
  --load-dc-calib FPGA_code/config/r1_dc_cal_fixed.json
```
