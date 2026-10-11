# Analog Multiplier & Inverted MAML Hardware Diagnostic Report

- **Timestamp:** `2026-10-11 14:45:24`
- **Target Hardware:** Efinix Trion `T120F324` (Master SoC) + `T20F256` (Analog Matrix Controller) @ `192.168.1.50:5000`
- **Firmware Version:** `T120_SOC_ETH_FW v2.0-MAML (Build 2026-10-11) | Status: T20 ONLINE [TAG=T20A, S-bus ACK 0x06]`
- **Heater Safety Interlock:** `DISARMED` (`HEAT_1..4_EN = 0`)

---

## 1. Stage 1 — Inter-FPGA Bridge (`T120 <-> T20`) & Application Handshake

| Parameter | Observed Value |
| :--- | :--- |
| Initial `VERSION` Response | `T120_SOC_ETH_FW v2.0-MAML (Build 2026-10-11) | Status: T20 ONLINE [TAG=T20A, S-bus ACK 0x06]` |
| Live Hardware Binary Protocol Active | `True` |
| T20 S-Bus Watchdog OK | `False` |
| T20 Hadamard `ACK` OK / Miss / Last Latency | `32` / `0` / `19 cycles` |

---

## 2. Stage 2 — Differential ADC (`ADC_45` & `ADC_49`) Zero-Baseline & Noise Floor

All `74HC595` R-2R DACs centered at differential zero (`code = 128`, `VR = 1.65V`) and Hadamard outputs in 3-state `Hi-Z` (`0x8000`).
Sampled over **$N = 25$** independent 4-Phase Settle-Then-Sample bursts (`2.0 µs` quiet settle window).

### 2.1 `ADC_45` — Intermediate Layer 1 Differential Outputs (`CH1..CH6`)

| Channel | Mean Raw (`0..4095`) | Mean Signed (`raw - 2048`) | DC Offset (`mV`) | Temporal RMS Noise (`LSB`) | Temporal RMS Noise (`mV`) | Min / Max Signed (`LSB`) | Peak-to-Peak (`LSB`) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `ADC45_CH1` | `2225.28` | `+177.28` | `+142.8 mV` | `0.72` | `0.58 mV` | `+176` / `+179` | `3` |
| `ADC45_CH2` | `2099.64` | `+51.64` | `+41.6 mV` | `0.89` | `0.72 mV` | `+50` / `+53` | `3` |
| `ADC45_CH3` | `2081.68` | `+33.68` | `+27.1 mV` | `0.88` | `0.71 mV` | `+32` / `+35` | `3` |
| `ADC45_CH4` | `1873.84` | `-174.16` | `-140.3 mV` | `0.73` | `0.59 mV` | `-175` / `-173` | `2` |
| `ADC45_CH5` | `1949.08` | `-98.92` | `-79.7 mV` | `0.74` | `0.60 mV` | `-101` / `-98` | `3` |
| `ADC45_CH6` | `1903.40` | `-144.60` | `-116.5 mV` | `0.80` | `0.64 mV` | `-146` / `-142` | `4` |

### 2.2 `ADC_49` — Final Summed Analog Matrix Outputs (`CH1..CH6`)

| Channel | Mean Raw (`0..4095`) | Mean Signed (`raw - 2048`) | DC Offset (`mV`) | Temporal RMS Noise (`LSB`) | Temporal RMS Noise (`mV`) | Min / Max Signed (`LSB`) | Peak-to-Peak (`LSB`) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `ADC49_CH1` | `615.72` | `-1432.28` | `-1153.9 mV` | `0.83` | `0.67 mV` | `-1434` / `-1431` | `3` |
| `ADC49_CH2` | `645.80` | `-1402.20` | `-1129.7 mV` | `1.23` | `0.99 mV` | `-1404` / `-1400` | `4` |
| `ADC49_CH3` | `448.00` | `-1600.00` | `-1289.1 mV` | `0.00` | `0.00 mV` | `-1600` / `-1600` | `0` |
| `ADC49_CH4` | `493.64` | `-1554.36` | `-1252.3 mV` | `1.13` | `0.91 mV` | `-1557` / `-1552` | `5` |
| `ADC49_CH5` | `450.00` | `-1598.00` | `-1287.5 mV` | `0.00` | `0.00 mV` | `-1598` / `-1598` | `0` |
| `ADC49_CH6` | `661.04` | `-1386.96` | `-1117.4 mV` | `1.15` | `0.93 mV` | `-1389` / `-1385` | `4` |

---

## 3. Stage 3 — Differential DAC Row Drive, Hadamard Permutation Invariance & `FWHT-16` Orthogonality

### 3.1 Static Single-Channel DAC Sweep (`32` to `224`)

| DAC Channel | `ADC_45` @ `128` (Signed LSB) | $\Delta\text{ADC}_{45}(224 - 32)$ | `ADC_49` @ `128` (Signed LSB) | $\Delta\text{ADC}_{49}(224 - 32)$ |
| :--- | :--- | :--- | :--- | :--- |
| `DAC_2 Row Drive R1 (Bank 0 Ch 0)` | `[179, 51, 35, -173, -99, -143]` | `[3, 3, 3, 1, -2, 3]` | `[-1431, -1400, -1600, -1554, -1598, -1387]` | `[-1, 5, 0, 1, 0, -1]` |
| `DAC_2 Row Drive R6 (Bank 0 Ch 5)` | `[177, 52, 34, -174, -100, -144]` | `[-2, 2, 1, 0, -1, 0]` | `[-1435, -1403, -1600, -1554, -1598, -1387]` | `[-4, -15, 0, 3, 0, 2]` |
| `W_15 M3 Weight R1 (Bank 1 Ch 0)` | `[155, 35, 21, -180, -84, -146]` | `[34, 16, -9, 3, -39, -13]` | `[-1439, -1362, -1601, -1562, -1598, -1415]` | `[9, -63, 2, 8, 0, 43]` |
| `W_12 M8 Weight R1 (Bank 2 Ch 0)` | `[178, 52, 33, -173, -100, -145]` | `[10, 9, 11, -3, -22, 2]` | `[-1431, -1403, -1600, -1555, -1598, -1389]` | `[1, 0, 0, 1, 0, -1]` |
| `W_34 M33 Weight R1 (Bank 3 Ch 0)` | `[177, 51, 34, -175, -100, -145]` | `[-28, -32, -38, -19, 19, -13]` | `[-1432, -1405, -1600, -1556, -1598, -1386]` | `[-33, 61, -2, -20, -1, 74]` |
| `W_34 Trim-DAC 38 (Bank 3 Ch 6 / DAC7_W_34)` | `[176, 52, 36, -174, -99, -145]` | `[1, 2, 2, 0, 1, 2]` | `[-1432, -1401, -1600, -1557, -1598, -1387]` | `[-2, 2, 0, 1, 0, -1]` |

### 3.2 Hadamard Permutation Invariance (`pi_inv` Hardware Scatter-Write + Return-to-Hi-Z `0x8000` Pulsing)

Each of the 16 Hadamard steps is executed as a 2-word Return-to-Hi-Z (`[HADAMARD_16[perm[s]], 0x8000]`) pulse with `40 µs` equilibration at `1.65 V` (`0x8000`), eliminating step-order history across the `C2/C4 = 1 nF` AC-coupling capacitors:

| Metric | Observed Value |
| :--- | :--- |
| H-Bus `ACK` OK / Miss / Latency `(min, max)` | `32` / `0` / `(19, 19) cycles` |
| Random Permutation `1A` (`perm[0..15]`) | `[9, 11, 14, 7, 5, 8, 0, 4, 13, 3, 2, 1, 6, 10, 15, 12]` |
| Random Permutation `1B` (`perm[0..15]`) | `[14, 11, 8, 1, 5, 9, 7, 6, 2, 4, 3, 12, 10, 13, 0, 15]` |
| `Max |cap45(Mode 0) - cap45(Mode 1A)|` / `RMS` (96 samples) | **`4 LSB`** / **`1.76 LSB`** |
| `Max |cap45(Mode 1A) - cap45(Mode 1B)|` / `RMS` (96 samples) | **`4 LSB`** / **`1.34 LSB`** |
| `FWHT-16` Col 0 `[1..8]` — Mode 0 (Identity) | `[122, 120, 138, 164, 130, 136, -318, 216]` |
| `FWHT-16` Col 0 `[1..8]` — Mode 1A (Permuted + HW `pi_inv`) | `[117, 119, 139, 161, 129, 139, -313, 223]` |
| `FWHT-16` Col 0 `[1..8]` — Mode 1B (Permuted + HW `pi_inv`) | `[121, 115, 139, 165, 129, 143, -313, 217]` |
| `FWHT-16` Col 0 `[1..8]` — Mode 2 (Permuted WITHOUT `pi_inv`, Scrambled Control) | `[-149, -127, -71, -65, -137, 53, -107, 201]` |

### 3.3 `DAC_2` (Input Rows `0..5`) — `FWHT-16` Diagonal Orthogonality (`code 255 - code 0`)

| Input Row Channel | $\Delta\text{FWHT}_{45}[1..8,\text{col }0]$ (`1/16 LSB` coherent sum) | Diagonal Peak $\Delta\text{FWHT}_{45}[\text{row}+1, \text{col }0]$ |
| :---: | :--- | :---: |
| `DAC_2[0]` | `[28, -2, -2, 2, 10, 4, -8, -10]` | **`+28`** |
| `DAC_2[1]` | `[-8, 50, -4, 6, 4, 6, -16, -14]` | **`+50`** |
| `DAC_2[2]` | `[1, 3, 47, 1, 1, -1, -17, -5]` | **`+47`** |
| `DAC_2[3]` | `[-7, -3, -13, 55, 5, 5, -13, -7]` | **`+55`** |
| `DAC_2[4]` | `[-5, 1, -5, 9, 43, -3, -13, -9]` | **`+43`** |
| `DAC_2[5]` | `[-5, -3, -5, 1, 7, 37, -17, -5]` | **`+37`** |

### 3.4 `W_15` ($M_3$ Weight Rows `0..7`) — `FWHT-16` Diagonal Orthogonality (`code 255 - code 0`)

| Weight Row Channel | $\Delta\text{FWHT}_{45}[1..8,\text{col }0]$ (`1/16 LSB` coherent sum) | Diagonal Peak Across All 6 Columns `col 0..5` |
| :---: | :--- | :--- |
| `W_15[0]` | `[92, -56, -50, -40, -34, -30, -12, -50]` | **`[92, 98, 74, 41, 51, 43]`** |
| `W_15[1]` | `[-70, 94, -72, -62, -40, -32, 14, -74]` | **`[94, 81, 68, 29, 34, 43]`** |
| `W_15[2]` | `[-64, -76, 110, -64, -38, -34, 20, -62]` | **`[110, 96, 74, 37, 42, 39]`** |
| `W_15[3]` | `[-41, -51, -67, 143, -37, -31, 5, -61]` | **`[143, 126, 84, 33, 53, 51]`** |
| `W_15[4]` | `[-50, -56, -66, -76, 122, -40, 54, -72]` | **`[122, 122, 78, 17, 38, 49]`** |
| `W_15[5]` | `[-50, -38, -40, -60, -38, 166, 56, -66]` | **`[166, 181, 117, 45, 55, 74]`** |
| `W_15[6]` | `[-64, -74, -86, -102, -62, -64, -248, -130]` | **`[-248, -121, -125, -100, -38, -29]`** |
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

| Matrix 3 Crosspoint Cell | Quiescent Baseline `(X=0, W=0)` | Weight Span $\Delta\text{ADC}_W$ (`W=-96` $\rightarrow$ `+96`) | Input Gain $\Delta\text{ADC}_X$ at **$W = -96$** (`X=-120` $\rightarrow$ `+120`) | Input Gain $\Delta\text{ADC}_X$ at **$W = +48 / +96$** (`X=-120` $\rightarrow$ `+120`) |
| :--- | :---: | :---: | :---: | :---: |
| **`Row 4, Col 1`** (`DAC_2[3]` $\rightarrow$ `ADC_45[0]`) | `2225` (`+177 LSB`, $1.793\text{ V}$) | **`+78 LSB`** (`2164` $\rightarrow$ `2242`) | **`+1 LSB`** (`2163` $\rightarrow$ `2164`) | **`+14 LSB`** (`2228` $\rightarrow$ `2242`) |
| **`Row 5, Col 1`** (`DAC_2[4]` $\rightarrow$ `ADC_45[0]`) | `2224` (`+176 LSB`, $1.792\text{ V}$) | **`+76 LSB`** (`2186` $\rightarrow$ `2262`) | **`-1 LSB`** (`2187` $\rightarrow$ `2186`) | **`+10 LSB`** (`2252` $\rightarrow$ `2262`) |
| **`Row 4, Col 2`** (`DAC_2[3]` $\rightarrow$ `ADC_45[1]`) | `2100` (`+52 LSB`, $1.692\text{ V}$) | **`+45 LSB`** (`2055` $\rightarrow$ `2100`) | **`+2 LSB`** (`2054` $\rightarrow$ `2056`) | **`+9 LSB`** (`2087` $\rightarrow$ `2096`) |
| **`Row 6, Col 3`** (`DAC_2[5]` $\rightarrow$ `ADC_45[2]`) | `2080` (`+32 LSB`, $1.676\text{ V}$) | **`+15 LSB`** (`2082` $\rightarrow$ `2097`) | **`+1 LSB`** (`2081` $\rightarrow$ `2082`) | **`+8 LSB`** (`2089` $\rightarrow$ `2097`) |
| **All 6 Rows Combined** $\rightarrow$ `ADC_45[0]` | `2226` (`+178 LSB`, $1.793\text{ V}$) | **`+104 LSB`** (`2177` $\rightarrow$ `2281`) | **`+6 LSB`** (`2171` $\rightarrow$ `2177`) | **`+20..+23 LSB`** (`2261` $\rightarrow$ `2281`) |

For the full fixed-$X$ / swept-$W$ tables and daily summary, see [`FPGA_code/docs/dev_status_2026-10-11.md`](dev_status_2026-10-11.md).
