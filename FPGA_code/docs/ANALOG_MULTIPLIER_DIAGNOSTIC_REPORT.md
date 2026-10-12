\\
| `W_15[7]` | `[-35, -37, -39, -49, -35, -33, -59, 167]` | **`[167, 138, 135, 71, 78, 79]`** |

### 3.5 `W_34` ($M_{33}$ Base Matrix Rows `0..5`) — Static Differential Response (`code 255 - code 0`)

| Base Weight Row | $\Delta\text{ADC}_{45,\text{HiZ}}[0..5]$ (`LSB`) | $\Delta\text{ADC}_{49,\text{HiZ}}[0..5]$ (`LSB`) |
| :---: | :--- | :--- |
| `W_34[0]` | `[-27, -34, -39, -18, 18, -13]` | **`[-39, 61, -2, -24, -1, 71]`** |
| `W_34[1]` | `[11, 37, -15, 13, 30, 32]` | **`[-133, 91, 0, -31, 0, 123]`** |
| `W_34[2]` | `[23, 31, 18, 5, 11, 35]` | **`[110, 48, 0, 1, -1, 150]`** |
| `W_34[3]` | `[-73, -67, 0, 26, -12, 36]` | **`[73, 235, -1, 35, -1, 189]`** |
| `W_34[4]` | `[-39, -46, -9, 42, 11, 1]` | **`[75, 44, 0, 42, -1, 141]`** |
| `W_34[5]` | `[-5, -42, -14, -25, 22, 6]` | **`[38, 29, 0, -29, 0, 276]`** |

---

## 4. Stage 4 — 4-Phase Settle-Then-Sample Frequency Sweep (`500 kHz` to `50 kHz`)

| Hadamard Rate | Quiet Settle Window (`50 MHz` cyc) | Uncompensated ENOB | Compensated ENOB | ENOB Gain | H-Bus `ACK` OK / Miss | `ADC_49` Signed Snapshot |
| :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `500 kHz` | `2.0 µs (100 cyc)` | `4.13 bits` | `6.65 bits` | `+2.52 bits` | `32` / `0` | `[-1413, -1333, -1601, -1559, -1599, -1346]` |
| `250 kHz` | `4.0 µs (200 cyc)` | `4.10 bits` | `7.70 bits` | `+3.60 bits` | `32` / `0` | `[-1365, -1410, -1600, -1538, -1599, -1317]` |
| `100 kHz` | `10.0 µs (500 cyc)` | `5.25 bits` | `6.73 bits` | `+1.48 bits` | `32` / `0` | `[-1426, -1301, -1600, -1560, -1599, -1329]` |
| `50 kHz` | `20.0 µs (1000 cyc)` | `4.95 bits` | `7.45 bits` | `+2.50 bits` | `32` / `0` | `[-1443, -1378, -1601, -1556, -1599, -1313]` |

---

## 5. Stage 5 — Cell-by-Cell 126-Crosspoint Dual-2T1C Multiplier Scan

| Matrix | Dimensions | Cells Scanned | Mean Zero Baseline (`LSB`) | Zero StdDev (`LSB`) | Mean Differential Swing (`+96 vs -96`) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **M33 (Base 6x6)** | `6x6` | `36` | `+0.56` | `4.55` | `+322.00 LSB` |
| **M3 (Layer 1 Comp 8x6)** | `8x6` | `48` | `+0.15` | `4.98` | `+326.58 LSB` |
| **M8 (Layer 2 Comp 7x6)** | `7x6` | `42` | `-0.38` | `5.06` | `+309.29 LSB` |

### 5.1 Sampled Cell Table — $M_{33}$ Base Matrix (`6x6`)

| Cell `(R, C)` | `ADC @ -96 (32)` | `ADC @ 0 (128)` | `ADC @ +96 (224)` | Diff Swing (`+96 - -96`) | Midpoint Nonlinearity (`LSB`) |
| :---: | :---: | :---: | :---: | :---: | :---: |
| `(0, 0)` | `-161.0` | `-2.0` | `+157.0` | `+318.0` | `+0.00` |
| `(0, 1)` | `-162.0` | `+2.0` | `+166.0` | `+328.0` | `+0.00` |
| `(0, 2)` | `-162.0` | `+2.0` | `+166.0` | `+328.0` | `+0.00` |
| `(0, 3)` | `-166.0` | `+6.0` | `+178.0` | `+344.0` | `+0.00` |
| `(0, 4)` | `-163.0` | `+7.0` | `+177.0` | `+340.0` | `+0.00` |
| `(0, 5)` | `-152.0` | `-6.0` | `+140.0` | `+292.0` | `+0.00` |
| `(1, 0)` | `-168.0` | `+7.0` | `+182.0` | `+350.0` | `+0.00` |
| `(1, 1)` | `-161.0` | `-8.0` | `+145.0` | `+306.0` | `+0.00` |
| `(1, 2)` | `-151.0` | `-4.0` | `+143.0` | `+294.0` | `+0.00` |
| `(1, 3)` | `-161.0` | `-3.0` | `+155.0` | `+316.0` | `+0.00` |
| `(1, 4)` | `-158.0` | `+1.0` | `+160.0` | `+318.0` | `+0.00` |
| `(1, 5)` | `-169.0` | `+3.0` | `+175.0` | `+344.0` | `+0.00` |
| `(2, 0)` | `-161.0` | `+3.0` | `+167.0` | `+328.0` | `+0.00` |
| `(2, 1)` | `-166.0` | `+4.0` | `+174.0` | `+340.0` | `+0.00` |
| `(2, 2)` | `-162.0` | `+5.0` | `+172.0` | `+334.0` | `+0.00` |
| `(2, 3)` | `-164.0` | `+8.0` | `+180.0` | `+344.0` | `+0.00` |
| `(2, 4)` | `-149.0` | `-6.0` | `+137.0` | `+286.0` | `+0.00` |
| `(2, 5)` | `-163.0` | `-3.0` | `+157.0` | `+320.0` | `+0.00` |

---

## 6. Stage 6 — Inverted MAML Outer/Inner Loop (`Ref 40 / Ref 41`) & Bit Precision

- **Uncompensated Precision (`M3, M8 = 128`):** `4.12 Effective Bits`
- **Compensated Precision (Trained `M3, M8`):** `7.28 Effective Bits`
- **Net ENOB Improvement:** `+3.16 bits`

| Step | Outer Epoch | Inner Step | Loss (`MSE_Q14`) | Uncomp ENOB | Comp ENOB | Mean Basin Distance | Hessian Dot-Product Alignment |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `1` | `1` | `0` | `33` | `4.62b` | `7.10b` | `3310.8` | `[11800, 12220, 12640, 16380]` |
| `2` | `2` | `0` | `17` | `4.62b` | `7.53b` | `2895.2` | `[16253, 12220, 12640, 16380]` |
| `3` | `3` | `0` | `58` | `4.62b` | `6.70b` | `2531.5` | `[16253, 16383, 12640, 16380]` |
| `4` | `4` | `0` | `16` | `4.62b` | `7.61b` | `2213.0` | `[16253, 16383, 16331, 16380]` |
| `5` | `5` | `0` | `35` | `4.62b` | `7.04b` | `1934.5` | `[16253, 16383, 16331, 16378]` |
| `6` | `6` | `0` | `13` | `4.62b` | `7.75b` | `1689.8` | `[16268, 16383, 16331, 16378]` |
| `7` | `7` | `0` | `11` | `4.62b` | `7.88b` | `1478.0` | `[16268, 16383, 16331, 16378]` |
| `8` | `8` | `0` | `20` | `4.62b` | `7.42b` | `1289.5` | `[16268, 16383, 16383, 16378]` |
| `9` | `9` | `0` | `15` | `4.62b` | `7.66b` | `1128.0` | `[16268, 16383, 16383, 16355]` |
| `10` | `10` | `0` | `16` | `4.62b` | `7.58b` | `981.5` | `[16291, 16383, 16383, 16355]` |
| `11` | `11` | `0` | `8` | `4.62b` | `8.08b` | `855.0` | `[16291, 16383, 16383, 16355]` |
| `12` | `12` | `0` | `6` | `4.62b` | `8.24b` | `747.2` | `[16291, 16383, 16243, 16355]` |

---

## 7. Key Hardware, Oscilloscope & Schematic Diagnostic Findings

### 7.1 T20 `LED2` vs. `LED8` (Golden vs. Application Image)
- **Observation:** When `T20` boots from SPI flash (`CBSEL=00`), it loads `T20_Golden` (`TAG=T20G`), which blinks `T20_LED1`/`T20_LED2` in counter-phase at `~1.5 Hz`.
- **Resolution:** `bridge_selftest()` in `FPGA_code/sw/t120_master/src/main.c` polls `T20` over the S-Bus after releasing `T20_CRESET_N` until `T20G` completes SPI boot (`~400 ms`), then automatically issues `CMD_JUMP(1)` (`CBSEL=01`). `T20` immediately reconfigures into `T20A` (`T20_Custom`), where `LED8` blinks instead of `LED2`.

### 7.2 `74HC595` R-2R DACs: `SCK`/`RCK` Pulse-Width Fix (`20 ns -> 280 ns`) & `bitrev8()` (`QA = MSB`)
- **Oscilloscope Diagnosis:** Probing `74HC595` (`U6$CBB17`) revealed that `SCK` and `RCK` (routed on `T120` `GPIOB_TX` high-speed I/O pins with `~35 ns` rise time) produced only a `~25 ns` high pulse at `r_sck_div = 2`, which failed to clock `SER` data into `QA..QH` (`Q<n> = 0`).
- **Resolution:** Widened `SCK`/`RCK` high time to **`280 ns`** (`r_sck_div = 15`, `0x00000F29u`) and added `bitrev8()` (`QA = pin 15 = MSB`, `QH = pin 7 = LSB`). Oscilloscope verification on `W_15` confirmed clean 3-step R-2R analog output switching between **`2.1 V` (`code 0`)**, **`2.6 V` (`code 128`)**, and **`2.9..3.1 V` (`code 255`)**.

### 7.3 `XC2361A` 12-Bit Differential SAR ADCs (`ADC_45` & `ADC_49`) — Sub-LSB Noise Floor
- **Observation:** All 12 differential `XC2361A` channels (`ADC_45 CH1..6` and `ADC_49 CH1..6`) convert with **temporal RMS noise between `0.00 LSB` and `0.50 LSB` (`0.00 to 0.40 mV RMS`, `0 to 1 LSB` peak-to-peak)**.
- **Zero-Drive Baseline:** When all 30 DACs are driven to `code = 0` (`DAC_2 = 1.65 V = VR`, so $V_{DS} = 0\text{ V}$ across all multiplier MOSFETs), all 6 columns of `ADC_45` align to **`-1534..-1536 LSB` (`raw = 512..514`)** and all 6 columns of `ADC_49` align to **`-1935..-1936 LSB` (`raw = 112..113`)**, within `1..2 LSB` across all 6 columns.

### 7.4 Hadamard Permutation Invariance (`0.48 LSB RMS`) & `FWHT-16` Diagonal Orthogonality
- **Physics of AC-Coupled Hadamard Injection (`C2/C4 = 1 nF`, `C1/C3 = 100 nF`):** In each `2X_2T1C` cell (`DOX3134A` MOSFETs `Q5, Q6, Q8, Q9`), `H+` and `H-` couple through `1 nF` capacitors (`0402B102K500NT`) onto the `100 nF` gate storage capacitors (`CL05B104KO5NNNC`). Under continuous NRZ stepping, each step $s$ injects $h_{\pi[s]} - (1-\beta)h_{\pi[s-1]}$, which depends on the previous step $\pi[s-1]$.
- **Return-to-Hi-Z (`0x8000`) Pre-Equilibrated Pulsing:** Driving each Hadamard step as a 2-word `[HADAMARD_16[perm[s]], 0x8000]` pulse with `40 µs` equilibration at `1.65 V` (`0x8000`) ensures every step launches from identical initial conditions. Across all $16 \times 6 = 96$ samples, **`Max |cap45(Mode 0) - cap45(Mode 1)| = 1 LSB` (`0.48 LSB RMS`)**, and `FWHT-16` demodulation extracts every input row `DAC_2[0..5]` and every weight row `W_15[0..7]` on its exact diagonal Walsh-Hadamard basis `fwht45[row + 1]`.

### 7.5 Sigmoid Analog Activation & Op-Amp Power Verification (`MCP6024` Top-Side Oscilloscope Probe)
- **Oscilloscope Supply Verification:** Direct top-side oscilloscope probing of all Sigmoid and TIA `MCP6024` quad op-amps confirmed **`Pin 4 (VDD) = 3.3 V`** and **`Pin 11 (VSS) = 0.0 V (GND)`** across all packages.
- **Sigmoid Soft-Clipping Stability (`SIG_OUT_FULL` -> `ADC_45`):** Full-range DAC sweep (`codes 0..224`) confirmed smooth Sigmoid transfer compression (`S-curve`) centered at **`1.650 V .. 1.656 V` (`raw 12-bit = 2048..2056`)** at zero drive (`DAC_2 = 1.65 V`), with **`0.33 to 0.87 LSB RMS` (`0.27 to 0.70 mV RMS`)** noise across the entire linear + `MMBT3904` BJT feedback knee (`Q1..Q4`, `C1 = 100 pF` Miller compensation), proving **zero op-amp oscillation or instability**.

---

## 8. Evening Update (`2026-10-11 21:20`) — Synchronous Autonomous 2T1C Refresh (`10.0 ms` / `100 Hz`) & Matrix 3 (`M3`) Multiplication Characterization

### 8.1 Hardware-Synchronous Autonomous Refresh Engine (`100 µs/col`, `10.0 ms` Period)
- **Root Cause Fixed:** Previously, the `100 nF` gate storage capacitors (`C_N`, `C_P`) across the 126 Dual-2T1C cells were not refreshed in `IDLE` or `HOLD` mode, allowing gate charge to leak down between measurements.
- **Implementation ([`maml_platform.c`](../sw/t120_master/src/maml_platform.c#L306-L395)):**
  - `g_col_settle_us = 100u` (`50 µs` = $5\tau_{\text{charge}}$ for `G_N` + `50 µs` = $5\tau_{\text{charge}}$ for `G_P`, where $\tau_{\text{charge}} = 100\ \Omega \times 100\text{ nF} = 10\ \mu\text{s}$ $\rightarrow$ `>99.3%` settled; total refresh duty time $= 6 \times 100\ \mu\text{s} = 600\ \mu\text{s} = 6\%$ duty cycle).
  - `g_refresh_period_us = 10000u` (`10.0 ms` = `100 Hz` refresh rate clocked by the 50 MHz RISC-V CLINT timer `clint_getTimeLow(BSP_CLINT)`).
  - Deterministic single-cell readout timing in `maml_probe_single_cell()`: every `(X, W)` measurement (`X = 0`, `X = +x_amp`, `X = -x_amp`) is preceded by a synchronous column refresh and sampled at the exact same relative delay (`10 µs`) after the refresh window.

### 8.2 Extended Matrix 3 (`M3` $\rightarrow$ Layer 1 Sigmoid $\rightarrow$ `ADC_45`) Multiplication Summary

| Matrix 3 Crosspoint Cell | Quiescent Baseline `(DAC2=128, W=0)` | Weight Span $\Delta\text{ADC}_W$ (`W=-96` $\rightarrow$ `+96`) | Data Gain $\Delta\text{ADC}_{\text{Data}}$ at **$W = -96$** (`DAC2=8 [+8mV]` $\rightarrow$ `248 [+243mV]`) | Data Gain $\Delta\text{ADC}_{\text{Data}}$ at **$W = +48 / +96$** (`DAC2=8 [+8mV]` $\rightarrow$ `248 [+243mV]`) |
| :--- | :---: | :---: | :---: | :---: |
| **`Row 4, Col 1`** (`DAC_2[3]` $\rightarrow$ `ADC_45[0]`) | `2225` (`+177 LSB`, $1.793\text{ V}$) | **`+78 LSB`** (`2164` $\rightarrow$ `2242`) | **`+1 LSB`** (`2163` $\rightarrow$ `2164`) | **`+14 LSB`** (`2228` $\rightarrow$ `2242`) |
| **`Row 5, Col 1`** (`DAC_2[4]` $\rightarrow$ `ADC_45[0]`) | `2224` (`+176 LSB`, $1.792\text{ V}$) | **`+76 LSB`** (`2186` $\rightarrow$ `2262`) | **`-1 LSB`** (`2187` $\rightarrow$ `2186`) | **`+10 LSB`** (`2252` $\rightarrow$ `2262`) |
| **`Row 4, Col 2`** (`DAC_2[3]` $\rightarrow$ `ADC_45[1]`) | `2100` (`+52 LSB`, $1.692\text{ V}$) | **`+45 LSB`** (`2055` $\rightarrow$ `2100`) | **`+2 LSB`** (`2054` $\rightarrow$ `2056`) | **`+9 LSB`** (`2087` $\rightarrow$ `2096`) |
| **`Row 6, Col 3`** (`DAC_2[5]` $\rightarrow$ `ADC_45[2]`) | `2080` (`+32 LSB`, $1.676\text{ V}$) | **`+15 LSB`** (`2082` $\rightarrow$ `2097`) | **`+1 LSB`** (`2081` $\rightarrow$ `2082`) | **`+8 LSB`** (`2089` $\rightarrow$ `2097`) |
| **All 6 Rows Combined** $\rightarrow$ `ADC_45[0]` | `2226` (`+178 LSB`, $1.793\text{ V}$) | **`+104 LSB`** (`2177` $\rightarrow$ `2281`) | **`+6 LSB`** (`2171` $\rightarrow$ `2177`) | **`+20..+23 LSB`** (`2261` $\rightarrow$ `2281`) |

### 8.3 Mandatory Signal & Table Notation Rule (Single-Ended `DAC_2` vs. Differential `W` & Hadamard `H`)
- **Outside the matrix, ONLY Weight $W$ and Hadamard $H$ are differential:**
  - **Weight $W$ (`W_15`, `W_12`, `W_34`):** Differential across the mirrored `P`-branch (`G_P`, `Q5/Q6`) and `N`-branch (`G_N`, `Q8/Q9`) half-cells (`W+ = 128 + W`, `W- = 128 - W` for signed $W \in [-127, +127]$).
  - **Hadamard (`H+ / H-`):** Differential AC-coupled (`1 nF`) into `G_P` and `G_N`.
- **Row Data Input (`DAC_2`, `IN_R1..6`) is STRICTLY SINGLE-ENDED UNIPOLAR (`0..255`):**
  - Per Patent Fig. 12 and [`Design_Specification_Analog_Matrix_2T1C.pdf`](../../Design_Specification_Analog_Matrix_2T1C.pdf), each row data line is a single-ended wire shared by the Drains of both `Q5` and `Q8` with Source virtual ground $V_s = 1.650\text{ V}$:
    - `DAC_2 = 0` (`1.650 V`) $\rightarrow$ **$V_{ds} = 0\text{ mV}$ (`0%` / Physical Zero Data Drive)**
    - `DAC_2 = 8` (`1.658 V`) $\rightarrow$ **$V_{ds} = +8\text{ mV}$ (`3%` / Lowest Single-Ended Data Drive)**
    - `DAC_2 = 128` (`1.775 V`) $\rightarrow$ **$V_{ds} = +125\text{ mV}$ (`50%` Mid-Scale Data Drive — NOT zero volts!)**
    - `DAC_2 = 248` (`1.893 V`) $\rightarrow$ **$V_{ds} = +243\text{ mV}$ (`97%` Full-Scale Data Drive)**
- **Rule for All Future GUI & CLI Tables:** Never use signed differential notation (`X = -120, 0, +120`) for Row Data `DAC_2`. Always display `DAC_2` using its unsigned code (`0..255`), drive percentage (`0%..100%`), and single-ended voltage ($V_{ds} = +8\text{ mV}, +125\text{ mV}, +243\text{ mV}$).

For the full fixed-`DAC_2` / swept-$W$ tables and daily summary, see [`FPGA_code/docs/dev_status_2026-10-11.md`](dev_status_2026-10-11.md).

---

## 9. Post-Fix Full Hardware Characterization (`2026-10-12`) — True Column-by-Column `50 µs` Gate Refresh (`100 Hz` Sawtooth Active)

### 9.1 Before vs. After Comparison (`Matrix 3` Single-Cell Multiplier)
After mapping and driving all 36 `G_P` and `G_N` pass-transistor gate pins on `T20` (`50 µs` `G_N` pulse followed by `50 µs` `G_P` pulse per column at `100 Hz`, eliminating the stuck-high `3.3 V` gate condition), each `100 nF` storage capacitor now holds its own column weight without being overwritten by neighboring columns:

| Matrix 3 Cell | **Before Fix (`2026-10-11`)** Weight Span $\Delta\text{ADC}_W$ | **After Fix (`2026-10-12`)** Weight Span $\Delta\text{ADC}_W$ | **Before Fix** Slope at $W=-96$ / $+96$ | **After Fix** Two-Quadrant Slope $\Delta\text{ADC}_{\text{Data}}$ at $W=-96$ / $+96$ |Improvement Factor |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **`R4, C1`** | `+78 LSB` | **`+298 LSB`** (`-144` $\rightarrow$ `+154`) | `+1` / `+14 LSB` | **`-34 LSB` / `+29 LSB`** | **`3.8x` span + full negative slope** |
| **`R5, C1`** | `+76 LSB` | **`+334 LSB`** (`-163` $\rightarrow$ `+171`) | `-1` / `+10 LSB` | **`-40 LSB` / `+39 LSB`** | **`4.4x` span + full negative slope** |
| **`R4, C2`** | `+45 LSB` | **`+166 LSB`** (`-81` $\rightarrow$ `+85`) | `+2` / `+9 LSB` | **`-17 LSB` / `+16 LSB`** | **`3.7x` span + symmetric slope** |
| **`R6, C3`** | `+15 LSB` | **`+213 LSB`** (`-108` $\rightarrow$ `+105`) | `+1` / `+8 LSB` | **`-22 LSB` / `+22 LSB`** | **`14.2x` span + symmetric slope** |

### 9.2 Full 48-Cell `Matrix 3` (`8×6 -> ADC_45`) Characterization Table
- **Data Rows `R1..R6` (`36 / 36` cells = `100%` working):**
  - Weight span $\Delta\text{ADC}_W$ (`W = +96` vs `W = -96` at `DAC_2 = 128 [+125 mV]`): **`+133 LSB` to `+388 LSB` (`mean = +255.1 LSB`)**.
  - Two-quadrant data multiplication slope $\Delta\text{ADC}_{\text{Data}}$ (`DAC_2 = 224 [+220 mV]` vs `DAC_2 = 32 [+31 mV]`):
    - At $W = +96$: **36 / 36 cells positive**, **`+13 LSB` to `+39 LSB` (`mean = +24.8 LSB`)**.
    - At $W = -96$: **36 / 36 cells negative**, **`-11 LSB` to `-40 LSB` (`mean = -24.4 LSB`)**.
- **Row 7 (`R7`, `1 MΩ` Bias Row `DAC2_D_ROW7`):** `6 / 6` columns active, $\Delta\text{ADC}_W \in [-741, -358]\text{ LSB}$ (`mean = -488.2 LSB`).
- **Row 8 (`R8`, `330 kΩ` Fast-Decay Reference Row `DAC2_D_ROW8`):** `6 / 6` columns active, $\Delta\text{ADC}_W \in [+645, +1256]\text{ LSB}$ (`mean = +969.7 LSB`).

| M3 Row | `Col 1` (`W=-96..+96`, $\Delta W$, $\Delta X_{-/+ }$) | `Col 2` (`W=-96..+96`, $\Delta W$, $\Delta X_{-/+ }$) | `Col 3` (`W=-96..+96`, $\Delta W$, $\Delta X_{-/+ }$) | `Col 4` (`W=-96..+96`, $\Delta W$, $\Delta X_{-/+ }$) | `Col 5` (`W=-96..+96`, $\Delta W$, $\Delta X_{-/+ }$) | `Col 6` (`W=-96..+96`, $\Delta W$, $\Delta X_{-/+ }$) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`R1`** | `-186..+202` (**`+388`**, `-37/+39`) | `-105..+109` (**`+214`**, `-20/+22`) | `-129..+129` (**`+258`**, `-25/+23`) | `-96..+100` (**`+196`**, `-19/+21`) | `-164..+167` (**`+331`**, `-32/+34`) | `-98..+102` (**`+200`**, `-20/+21`) |
| **`R2`** | `-186..+197` (**`+383`**, `-38/+37`) | `-106..+107` (**`+213`**, `-22/+21`) | `-95..+95` (**`+190`**, `-19/+19`) | `-70..+69` (**`+139`**, `-13/+14`) | `-158..+162` (**`+320`**, `-31/+31`) | `-75..+76` (**`+151`**, `-14/+16`) |
| **`R3`** | `-186..+197` (**`+383`**, `-37/+38`) | `-101..+101` (**`+202`**, `-20/+20`) | `-122..+124` (**`+246`**, `-25/+24`) | `-96..+98` (**`+194`**, `-19/+19`) | `-158..+156` (**`+314`**, `-31/+31`) | `-94..+93` (**`+187`**, `-19/+19`) |
| **`R4`** | `-144..+154` (**`+298`**, `-34/+29`) | `-81..+85` (**`+166`**, `-17/+16`) | `-97..+101` (**`+198`**, `-19/+20`) | `-76..+78` (**`+154`**, `-15/+15`) | `-157..+159` (**`+316`**, `-30/+31`) | `-67..+66` (**`+133`**, `-11/+13`) |
| **`R5`** | `-163..+171` (**`+334`**, `-40/+39`) | `-127..+134` (**`+261`**, `-26/+25`) | `-160..+164` (**`+324`**, `-31/+32`) | `-115..+119` (**`+234`**, `-23/+24`) | `-162..+166` (**`+328`**, `-31/+33`) | `-115..+116` (**`+231`**, `-22/+23`) |
| **`R6`** | `-185..+195` (**`+380`**, `-36/+38`) | `-106..+107` (**`+213`**, `-21/+21`) | `-108..+105` (**`+213`**, `-22/+22`) | `-123..+127` (**`+250`**, `-24/+25`) | `-157..+161` (**`+318`**, `-31/+32`) | `-93..+92` (**`+185`**, `-18/+19`) |
| **`R7`** | `-363..+378` (**`-741`**) | `-221..+230` (**`-451`**) | `-196..+203` (**`-399`**) | `-176..+183` (**`-359`**) | `-291..+301` (**`-592`**) | `-190..+197` (**`-387`**) |
| **`R8`** | `-372..+396` (**`+768`**) | `-313..+332` (**`+645`**) | `-611..+640` (**`+1251`**) | `-458..+482` (**`+940`**) | `-586..+613` (**`+1199`**) | `-506..+529` (**`+1035`**) |

---

### 9.3 Full 36-Cell `Matrix 33` (`6×6 Primary Payload Matrix -> ADC_49`) Characterization Table
With an unmodulated pedestal bias (`+48` on row `(row+3)%6` at constant `DAC_2 = 128`) keeping the single-supply `COLTIA` difference amplifier (`U1/U2$CBB15`, `0..3.3V`) centered at `+0.33 V` above `GND`:
- **36 / 36 cells (`100%`)** swing cleanly in both negative (`W = -96`) and positive (`W = +96`) directions around `0 LSB`.
- **Weight Span $\Delta\text{ADC}_W$ (`W = +96` vs `W = -96`):** **`+492 LSB` to `+1049 LSB` (`mean = +725.2 LSB` = `0.584 V`)**.
- **Two-Quadrant Multiplication Slope $\Delta\text{ADC}_{\text{Data}}$:**
  - At $W = +96$: **36 / 36 cells positive**, **`+15 LSB` to `+79 LSB` (`mean = +44.8 LSB`)**.
  - At $W = -96$: **36 / 36 cells negative/inverted**, down to **`-86 LSB` (`mean = -33.6 LSB`)**.

| M33 Row | `Col 1` (`W=-96..+96`, $\Delta W$, $\Delta X_{-/+ }$) | `Col 2` (`W=-96..+96`, $\Delta W$, $\Delta X_{-/+ }$) | `Col 3` (`W=-96..+96`, $\Delta W$, $\Delta X_{-/+ }$) | `Col 4` (`W=-96..+96`, $\Delta W$, $\Delta X_{-/+ }$) | `Col 5` (`W=-96..+96`, $\Delta W$, $\Delta X_{-/+ }$) | `Col 6` (`W=-96..+96`, $\Delta W$, $\Delta X_{-/+ }$) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`R1`** | `-186..+361` (**`+547`**, `+0/+35`) | `-219..+458` (**`+677`**, `-8/+50`) | `-529..+520` (**`+1049`**, `-86/+76`) | `-312..+390` (**`+702`**, `-23/+47`) | `-167..+512` (**`+679`**, `+1/+31`) | `-370..+424` (**`+794`**, `-41/+48`) |
| **`R2`** | `-216..+383` (**`+599`**, `-11/+38`) | `-242..+465` (**`+707`**, `-16/+49`) | `-511..+501` (**`+1012`**, `-80/+79`) | `-328..+411` (**`+739`**, `-29/+48`) | `-180..+502` (**`+682`**, `+0/+30`) | `-382..+429` (**`+811`**, `-46/+47`) |
| **`R3`** | `-180..+360` (**`+540`**, `+0/+34`) | `-206..+452` (**`+658`**, `-4/+50`) | `-427..+434` (**`+861`**, `-64/+63`) | `-253..+325` (**`+578`**, `-10/+37`) | `-158..+509` (**`+667`**, `+0/+28`) | `-291..+334` (**`+625`**, `-22/+36`) |
| **`R4`** | `-346..+242` (**`+588`**, `-41/+25`) | `-392..+308` (**`+700`**, `-46/+37`) | `-517..+493` (**`+1010`**, `-84/+71`) | `-363..+350` (**`+713`**, `-41/+39`) | `-514..+214` (**`+728`**, `-56/+16`) | `-414..+378` (**`+792`**, `-51/+44`) |
| **`R5`** | `-336..+246` (**`+582`**, `-38/+26`) | `-388..+315` (**`+703`**, `-45/+38`) | `-495..+511` (**`+1006`**, `-75/+76`) | `-345..+328` (**`+673`**, `-39/+37`) | `-514..+212` (**`+726`**, `-56/+15`) | `-406..+375` (**`+781`**, `-49/+45`) |
| **`R6`** | `-343..+242` (**`+585`**, `-39/+25`) | `-400..+312` (**`+712`**, `-47/+38`) | `-428..+418` (**`+846`**, `-61/+62`) | `-252..+240` (**`+492`**, `-19/+27`) | `-514..+217` (**`+731`**, `-57/+15`) | `-312..+292` (**`+604`**, `-28/+34`) |

---

### 9.4 Hadamard `FWHT-16` Parallel Demodulation & Hardware $\pi^{-1}$ Scatter-Write Verification
- **Zero Timing Jitter:** `ack_ok = 32, ack_miss = 0, lat_min = 19, lat_max = 19, t20_sync_err = 0`.
- **41.8x (`32.4 dB`) Active-to-Quiet Basis Isolation (`en_mask = 0x00FF`):**
  - Active `Matrix 3` rows (`fwht45[m=1..7]`): **`[120, 288, 330, 320, 250, 118, 328] LSB` (`mean = 250.6 LSB`)**.
  - Disabled `Matrix 8` rows (`fwht45[m=9..15]`): **`[12, 8, 6, 12, 2, 2, 0] LSB` (`mean = 6.0 LSB`)**.
- **Hardware $\pi^{-1}$ Scatter-Write Verification (`Mode 1` vs `Mode 2`):**
  - In `Mode 1` (random step permutation $\pi$ + hardware $\pi^{-1}$ scatter-write LUT enabled), the reordered capture RAM matches the unpermuted waveform structure (`cap45[0..7] = [53, 9, 6, 13, 7, 13, 1, 6]` vs `cap45[8..15] = [49, 9, 7, 14, 7, 13, 1, 7]`, within `1 LSB` on `m=1..7`) and keeps inactive basis leakage at **`4.4 LSB`**.
  - In `Mode 2` (same random permutation $\pi$ with hardware $\pi^{-1}$ disabled), basis orthogonality collapses (`545 LSB` leakage into `m=8`), confirming the hardware `pi_inv` scatter-write LUT in `t120_analog_io_ctrl.sv`.

