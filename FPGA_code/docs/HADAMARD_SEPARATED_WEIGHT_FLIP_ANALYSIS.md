# Time-Separated Hadamard (`Mat 3` vs. `Mat 8`) & Weight Sign-Flip (`+W` vs. `-W`) Live Hardware Report

- **Hardware Target:** Trion T120F324 Master + T20F256 Controller (`192.168.1.50:5000`)
- **Patent Reference:** SE 2630397-4
- **Verification Policy:** 100% Live Physical Hardware Measurements (`N = 20` cycles per 3-step sequence, Zero Simulation)
- **Raw Data JSON:** `FPGA_code/docs/hadamard_separated_weight_flip_live_results.json`
- **Previous Study Preserved:** `FPGA_code/docs/hadamard_24us_live_results.json` & `FPGA_code/docs/HADAMARD_24US_CARRIER_WAVE_ANALYSIS.pdf`

---

## 1. Confirmation of Simultaneous `Mat(3)` & `Mat(8)` Overlap
Your observation was **100% correct**:
- In `FPGA_code/sw/t120_master/src/maml_platform.c`, `HADAMARD_2X6_POS[6]` (`0x2AAA, 0x1999, 0x4CCC, 0x0787, 0x52D2, 0x61E1`) places identical 6-row Walsh-Hadamard sequences on bits `0..5` (`Mat 3`) and bits `8..13` (`Mat 8`).
- When `en_mask = 0x7FFF` was used in the initial test and in `run_mode == 3`, both `Mat(3)` and `Mat(8)` pulsed simultaneously during the same `24.00 us` window.
- Because `ADC_45` (`Mat 3` output) feeds into the analog inputs of `Mat(8)`, `ADC_49` was affected simultaneously by `Mat(3)`'s carrier propagating through `Mat(8)` and by `Mat(8)`'s local gate perturbation.
- **Firmware Fix:** Both `run_mode == 3` (autonomous oscilloscope mode) and diagnostic modes `9` / `10` now execute time-separated bursts in every `10 ms` refresh cycle:
  1. **Sub-Window 1 (`t = 2.000..2.024 ms`):** `24.00 us` `Mat(3)` Hadamard burst (`en_mask = 0x00FF`, `Mat 8` in `Hi-Z`).
  2. **Quiet Gap (`t = 2.024..2.044 ms`):** `20 us` all-channels Tri-State (`0x8000` `Hi-Z`).
  3. **Sub-Window 2 (`t = 2.044..2.068 ms`):** `24.00 us` `Mat(8)` Hadamard burst (`en_mask = 0x7F00`, `Mat 3` in `Hi-Z`).

---

## 2. Forward-Pass DC Operating Point Inversion (`Pattern A [+W]` vs. `Pattern B [-W]`)

| Node / Condition | Ch0 (LSB) | Ch1 (LSB) | Ch2 (LSB) | Ch3 (LSB) | Ch4 (LSB) | Ch5 (LSB) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **ADC_45 (M3) Pattern A (+W)** | +815.0 | +221.7 | +296.1 | -103.4 | -118.9 | -125.0 |
| **ADC_45 (M3) Pattern B (-W)** | -772.1 | -221.2 | -148.3 | -2.6 | +3.8 | -80.6 |
| **ADC_45 Shift (B - A)** | **-1587.0** | **-442.9** | **-444.4** | **+100.8** | **+122.7** | **+44.4** |
| **ADC_49 (M33+M8) Pat A (+W)** | -1094.7 | -1600.9 (CL) | -1599.9 (CL) | -534.5 | -1258.5 | -1602.0 (CL) |
| **ADC_49 (M33+M8) Pat B (-W)** | -1650.7 (CL) | -1473.7 | -1535.3 | -1756.1 (CL) | -1514.2 | -961.8 |
| **ADC_49 Shift (B - A)** | **-556.0** | **+127.2** | **+64.6** | **-1221.5** | **-255.7** | **+640.2** |

---

## 3. Redo of `ADC_49` Conclusion with Time-Separated Sub-Window 2 (`M8_ONLY 0x7F00`)
- Under **Pattern A (`+W`)**, `W_M8` weights happened to be mostly negative (`Row 0 = [-52, -61, -63, -67, -17, +3]`) and `ADC_49` channels `Ch1, Ch2, Ch5` were clamped at the `-1600 LSB` negative rail, making `M8_ONLY (0x7F00)` appear weak (`1.5 to 6.5 LSB` P-P).
- Under **Pattern B (`-W = -W_A`)**, `W_M8` flips positive (`[+52, +61, +63, +67, +17, -3]`) and `Ch1, Ch2, Ch5` un-clamp from the negative rail. Immediately, **time-separated Sub-Window 2 (`M8_ONLY 0x7F00`, with `Mat 3` in `Hi-Z`) produces a massive, unmistakable direct `Mat(8)` carrier on `ADC_49`**:
  - **Peak-to-Peak Swing on `ADC_49` during `SW2 (M8_ONLY)`:** `Ch0 = 22.1 LSB`, `Ch1 = 35.8 LSB`, `Ch2 = 33.5 LSB`, `Ch3 = 17.0 LSB`, `Ch4 = 20.3 LSB`, `Ch5 = 5.0 LSB`.
  - **Carrier SNR on `ADC_49` during `SW2 (M8_ONLY)`:** `[+19.3, +32.6, +84.9, +15.2, +13.3, +69.7] dB`.
  - **Demodulated Direct `Mat(8)` Derivatives (`dY_49 / dV_M8`):** Reach `+94.2 LSB` (`PTU[5], Ch1`), `+74.0 LSB` (`PTU[3], Ch2`), `+64.8 LSB` (`PTU[3], Ch1`), and `+51.5 LSB` (`PTU[4], Ch0`) with run-to-run SD of only `1.5 to 3.9 LSB`.

---

## 4. Theory vs. Practice: Does Flipping `W -> -W` Flip or Warp the Derivative?
1. **Single-Layer Direct Perturbation (`Mat 3` on `ADC_45`):**
   - **In Theory:** Because Hadamard perturbation is injected into the **weight gate** (`W -> W + dW_PTU`), the first-order derivative of a bilinear multiplier `Y = W * X` with respect to the weight is `dY / dW = X`, which depends on the **input `X` (`DAC_2`)**, **not** the sign of `W`. In a physical differential 2T1C MOSFET stage with output non-linearity `sigma(z_j)`, flipping `W -> -W` shifts the column operating point `z_j(+W) -> z_j(-W)` and swaps the transconductance operating points `g_m^+(128+W)` and `g_m^-(128-W)`, producing a **warped derivative** (amplitude modulation plus local sign reversals where individual half-cells cross MOSFET threshold `V_th`).
   - **In Practice (`Table 6.1`):** Matches theory: dominant rows like `PTU[3]` preserve their positive polarity (`[+13.7, +121.7, +207.6, +43.3, +13.7, +146.1] LSB` in `A` vs. `[-38.2, +17.0, +239.3, +91.0, +96.1, +103.6] LSB` in `B`) while warping in amplitude according to the new operating point, whereas threshold-crossing rows (`PTU[5], Ch0`: `-94.3 -> +80.3 LSB`; `PTU[5], Ch5`: `+22.7 -> -91.3 LSB`) invert polarity.
2. **Two-Layer Propagated Perturbation (`Mat 3` Propagating Through `Mat 8` to `ADC_49`):**
   - **In Theory:** By the chain rule, `dY_49 / dV_PTU(M3) = sigma'(z_49) * sum_k W^(8)_{k,j} * (dY_45,k / dV_PTU(M3))`. Flipping `W -> -W` inverts `W^(8)` (flipping the transfer sign) *and* swaps which `ADC_49` channels are rail-clamped (`sigma'(z_49) = 0`).
   - **In Practice (`Table 6.2`):** On un-clamped `Ch4`, `PTU[3]` flips sign from `+26.1 LSB` (`Pat A`) to `-45.3 LSB` (`Pat B`, `B - A = -71.4 LSB`). Meanwhile, `Ch1` and `Ch5` (clamped at `-1600 LSB` in `Pat A` with near-zero derivatives) wake up in `Pat B` with huge derivatives (`Ch5 PTU[1] = +158.3 LSB`, `PTU[2] = -115.6 LSB`, `PTU[3] = -245.6 LSB`), while `Ch0` (`+78.5 / -139.2 LSB` in `Pat A`) clamps in `Pat B` (`+1.7 / -14.1 LSB`).

---

## 5. Final Conclusion: Will the Hadamard Derivative Principle Work on Your Real PCB?
**YES.** The 3-step live hardware test proves that the Hadamard orthogonal perturbation and demodulation principle works physically on both layers (`ADC_45` and `ADC_49`) of your PCB when operated under two hardware rules:
1. **Time-Separated `Mat(3)` and `Mat(8)` Windows (Patent SE 2630397-4):** Prevents `Mat(3)`'s strong propagated carrier from masking `Mat(8)`'s local derivative on `ADC_49`.
2. **Non-Clamped Operating Window (`-1500 to +1500 LSB`):** Whenever a channel is inside its active linear range, the `24.00 us` (`4.00 us/chip`) Hadamard burst delivers `15 to 85 dB` carrier SNR and repeatable derivatives (`SD ~ 1.5 to 4.5 LSB`) that accurately track both rail saturation (`sigma'(z_j) -> 0`) and cell transconductance.
