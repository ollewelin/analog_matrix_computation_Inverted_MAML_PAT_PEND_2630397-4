# Release 2026-11-14: Card 1 Mode A 2-Beat Bit-Slicing Anti-Windup Baseline (Round 1)

**Hardware Platform:** Card 1 (`Trion T120F324` Master SoC + `Trion T20F256` Coprocessor, `1k / 2.2k` Passive Summing Attenuator)  
**Patent Pending:** SE 2630397-4 (Inverted MAML Silicon)  
**Firmware Version:** `T120_SOC_ETH_FW v2.2-MAML (SW Build Nov 14 2026 10:15:16)`  
**Hardware Logic ID:** `0x20261030 (ID=MAM1)`  
**Release Tag:** `Release_20261114_ModeA_Card1_BitSlicing_AntiWindup_Baseline_R1`

---

## 1. Purpose & Restoration Guarantee

This package is a verified, self-contained **restore baseline** covering the C firmware, FPGA merged bitstream, Python runner, live monitoring GUI, fixed `W(3)` staircase configuration, offline thermal-detrended ML hyperparameter generator, and Round 1 experimental verification logs (`Cold` + `Warm` closed-loop ON/OFF contrast).

### Key Firmware Fixes Included in This Baseline
1. **Corrected Two-Layer `dx8` Back-Propagation Sign, Gain Shift & M3 Data-Row Protection ([maml_platform.c](sw/t120_master/src/maml_platform.c)):**
   - Fixed the sign inversion in `dx8[i]` column accumulation (`err49[j]` -> `-err49[j]`) so Layer 1 (`M3` rows `0..5`) reduces error monotonically alongside Layer 2 (`M8`) rather than amplifying thermal drift in positive feedback.
   - Adjusted `grad_m3_out` arithmetic shift from `>> 3` to `>> 6` and added `sat_comp_m3_q14()` capping dynamic `M3` data rows `0..5` to `±max(15, clamp/3)` (`±25 LSB` at `clamp=75`) so `M3` never swamps the fixed `±40 LSB` temporal reference clock staircase (`M3` rows `6..7`).
2. **Integrated-L2 Back-Calculation Anti-Windup (`maml_momentum_step_antiwindup`):**
   - Folded L2 regularization decay directly inside the momentum velocity update and projected stored velocity `vel_io` to the actually realized clamped step `(w_cur - w_clamped)` whenever weights touch `±clamp` (`±75 LSB`), eliminating limit-cycle sawtooth bouncing at the rails.
   - Added clip-recovery velocity halving (`/= 2`) and L2 pullback when `valid_samples == 0` under ColTIA clipping.
3. **Ethernet Minimum-Frame Length Fix (`MAML_CMD_BATCH_STEP`):**
   - Preserved `if (req_len >= 5)` in `maml_handle_udp_command()` because raw IEEE 802.3 frames (`>= 60` bytes) pad 15-byte `MAML_CMD_BATCH_STEP` payloads to `req_len == 18`, ensuring reliable calibration and batch execution on every packet.

---

## 2. Verified Baseline Performance (`K=1`, Fixed Cold Calibration after 60 s Cooldown)

### Cold Reference Check (`cold_verify_k1.json`, Heaters OFF, 643 pairs)
- **Phase 1 (`Cold / Regler ON`):** Mean Combined ENOB **9.45 b** (`min 8.80 b`), zero `RankWarning` on static cold `alpha`/`beta` calibration.
- **Phase 2 (`Cold / Regler OFF`, `W8=0`):** Mean Combined ENOB **9.45 b** (`min 8.61 b`), strictly `0/311` non-zero `W8` leaks.

### Round 1 Warm Thermal Cycling (`opt_r1_lr0p03_l2_1024_mom0p90_cl75.json`, `4,289` pairs, `40%` PWM)
- **Hyperparameters:** `lr = 0.03`, `l2_reg = 1024`, `momentum = 0.90`, `clamp = ±75 LSB`, `K = 1`.
- **Phase 5 (`Warm / Regler ON`) Convergence:** Climbs from **7.74 b -> 7.99 b** (mean **8.07 b**) while `Loss` drops (`18,781 -> 16,896` MSB, `17,635 -> 13,715` LSB), overcoming the underlying heating curve.
- **Phase 6 (`Warm / Regler OFF`, `W8=0`):** Drops cleanly from **6.96 b -> 6.59 b** (mean **6.71 b**) with `0.00%` `W8` leak.
- **Thermal-Detrended Model Summary (`analog_hyperparam_model.py`):** Step Lift **+0.66 b**, Loss Ratio **1.57x**, Convergence Climb **+0.74 b**, Recovery Rate **0.67**, Score **+1.957**.

---

## 3. Exact Restore Commands (Return to This Baseline)

From repository root:
```bash
cp FPGA_code/releases/Release_20261114_ModeA_Card1_BitSlicing_AntiWindup_Baseline_R1/sw/t120_master/src/* FPGA_code/sw/t120_master/src/
cp FPGA_code/releases/Release_20261114_ModeA_Card1_BitSlicing_AntiWindup_Baseline_R1/sw/t120_master/include/* FPGA_code/sw/t120_master/include/
cp FPGA_code/releases/Release_20261114_ModeA_Card1_BitSlicing_AntiWindup_Baseline_R1/pc_python/run_card1_thermal_bit_slicing.py FPGA_code/scripts/
cp FPGA_code/releases/Release_20261114_ModeA_Card1_BitSlicing_AntiWindup_Baseline_R1/pc_python/analog_hyperparam_model.py FPGA_code/scripts/
cp FPGA_code/releases/Release_20261114_ModeA_Card1_BitSlicing_AntiWindup_Baseline_R1/pc_python/bit_slicing_live_gui.py gui/
cp FPGA_code/releases/Release_20261114_ModeA_Card1_BitSlicing_AntiWindup_Baseline_R1/pc_python/udp_client.py gui/
cp FPGA_code/releases/Release_20261114_ModeA_Card1_BitSlicing_AntiWindup_Baseline_R1/pc_python/config/* FPGA_code/config/

make -C FPGA_code/sw/t120_master clean all
/home/olle/anaconda3/bin/python FPGA_code/scripts/flash_soc.py
```

### Launch Live Monitoring GUI & Run Baseline Experiment:
```bash
/home/olle/anaconda3/bin/python gui/bit_slicing_live_gui.py &
/home/olle/anaconda3/bin/python FPGA_code/scripts/run_card1_thermal_bit_slicing.py \
  --cooldown-sec 60 --cold-phase-duration 0.25 --phase-duration 1.0 \
  --warm-phases 4 --cool-phases 0 --heater-duty-pct 40 --k-batch 1 \
  --lr 0.03 --l2-reg 1024 --momentum 0.90 --clamp 75
```
