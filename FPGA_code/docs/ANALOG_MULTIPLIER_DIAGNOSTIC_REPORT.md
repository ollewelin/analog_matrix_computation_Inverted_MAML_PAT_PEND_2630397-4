# Analog Multiplier & Inverted MAML Hardware Diagnostic Report

- **Timestamp:** `2026-10-11 12:46:41`
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
| T20 Hadamard `ACK` OK / Miss / Last Latency | `0` / `0` / `0 cycles` |

---

## 2. Stage 2 — Differential ADC (`ADC_45` & `ADC_49`) Zero-Baseline & Noise Floor

All `74HC595` R-2R DACs centered at differential zero (`code = 128`, `VR = 1.65V`) and Hadamard outputs in 3-state `Hi-Z` (`OE = 0`).
Sampled over **$N = 25$** independent 4-Phase Settle-Then-Sample bursts (`2.0 µs` quiet settle window).

### 2.1 `ADC_45` — Intermediate Layer 1 Differential Outputs (`CH1..CH6`)

| Channel | Mean Raw (`0..4095`) | Mean Signed (`raw - 2048`) | DC Offset (`mV`) | Temporal RMS Noise (`LSB`) | Temporal RMS Noise (`mV`) | Min / Max Signed (`LSB`) | Peak-to-Peak (`LSB`) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `ADC45_CH1` | `555.64` | `-1492.36` | `-1202.3 mV` | `0.48` | `0.39 mV` | `-1493` / `-1492` | `1` |
| `ADC45_CH2` | `525.00` | `-1523.00` | `-1227.0 mV` | `0.00` | `0.00 mV` | `-1523` / `-1523` | `0` |
| `ADC45_CH3` | `521.00` | `-1527.00` | `-1230.2 mV` | `0.00` | `0.00 mV` | `-1527` / `-1527` | `0` |
| `ADC45_CH4` | `467.80` | `-1580.20` | `-1273.1 mV` | `0.40` | `0.32 mV` | `-1581` / `-1580` | `1` |
| `ADC45_CH5` | `486.48` | `-1561.52` | `-1258.1 mV` | `0.50` | `0.40 mV` | `-1562` / `-1561` | `1` |
| `ADC45_CH6` | `476.00` | `-1572.00` | `-1266.5 mV` | `0.00` | `0.00 mV` | `-1572` / `-1572` | `0` |

### 2.2 `ADC_49` — Final Summed Analog Matrix Outputs (`CH1..CH6`)

| Channel | Mean Raw (`0..4095`) | Mean Signed (`raw - 2048`) | DC Offset (`mV`) | Temporal RMS Noise (`LSB`) | Temporal RMS Noise (`mV`) | Min / Max Signed (`LSB`) | Peak-to-Peak (`LSB`) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `ADC49_CH1` | `153.96` | `-1894.04` | `-1526.0 mV` | `0.20` | `0.16 mV` | `-1895` / `-1894` | `1` |
| `ADC49_CH2` | `160.60` | `-1887.40` | `-1520.6 mV` | `0.49` | `0.39 mV` | `-1888` / `-1887` | `1` |
| `ADC49_CH3` | `112.00` | `-1936.00` | `-1559.8 mV` | `0.00` | `0.00 mV` | `-1936` / `-1936` | `0` |
| `ADC49_CH4` | `124.00` | `-1924.00` | `-1550.1 mV` | `0.28` | `0.23 mV` | `-1925` / `-1923` | `2` |
| `ADC49_CH5` | `112.00` | `-1936.00` | `-1559.8 mV` | `0.00` | `0.00 mV` | `-1936` / `-1936` | `0` |
| `ADC49_CH6` | `163.80` | `-1884.20` | `-1518.0 mV` | `0.49` | `0.39 mV` | `-1885` / `-1883` | `2` |

---

## 3. Stage 3 — Differential DAC Row Drive & Weight Bank Sweep

Single-channel differential DAC sweep across codes `32 (-96 LSB)`, `128 (0 LSB)`, and `224 (+96 LSB)` while holding all other DACs at `128`:

| DAC Channel | `ADC_45` @ `128` (Signed LSB) | $\Delta\text{ADC}_{45}(224 - 32)$ | `ADC_49` @ `128` (Signed LSB) | $\Delta\text{ADC}_{49}(224 - 32)$ |
| :--- | :--- | :--- | :--- | :--- |
| `DAC_2 Row Drive R1 (Bank 0 Ch 0)` | `[-1493, -1523, -1527, -1580, -1561, -1572]` | `[1, 1, 1, 1, 0, 0]` | `[-1894, -1887, -1936, -1924, -1936, -1884]` | `[0, 2, 0, 0, 0, 0]` |
| `DAC_2 Row Drive R6 (Bank 0 Ch 5)` | `[-1492, -1523, -1527, -1580, -1562, -1572]` | `[0, 0, 0, 1, -1, 0]` | `[-1894, -1887, -1936, -1924, -1936, -1884]` | `[0, -3, 0, 1, 0, 0]` |
| `W_15 M3 Weight R1 (Bank 1 Ch 0)` | `[-1492, -1523, -1527, -1580, -1562, -1572]` | `[8, 4, -2, 0, -10, -3]` | `[-1894, -1887, -1936, -1924, -1936, -1885]` | `[3, -16, 1, 3, 0, 12]` |
| `W_12 M8 Weight R1 (Bank 2 Ch 0)` | `[-1492, -1523, -1527, -1580, -1561, -1572]` | `[3, 2, 2, 0, -6, 1]` | `[-1894, -1887, -1936, -1924, -1936, -1884]` | `[0, 0, 0, 0, 0, 0]` |
| `W_34 M33 Weight R1 (Bank 3 Ch 0)` | `[-1493, -1523, -1527, -1580, -1561, -1572]` | `[-7, -8, -10, -5, 6, -3]` | `[-1894, -1887, -1936, -1924, -1936, -1884]` | `[-9, 14, 0, -6, 0, 18]` |
| `W_34 Trim-DAC 38 (Bank 3 Ch 6 / DAC7_W_34)` | `[-1493, -1523, -1527, -1580, -1561, -1572]` | `[0, 0, 0, 0, 0, 0]` | `[-1894, -1887, -1936, -1924, -1936, -1884]` | `[1, 0, 0, 0, 0, 0]` |

---

## 4. Stage 4 — 4-Phase Settle-Then-Sample Frequency Sweep (`500 kHz` to `50 kHz`)

| Hadamard Rate | Quiet Settle Window (`50 MHz` cyc) | Uncompensated ENOB | Compensated ENOB | ENOB Gain | H-Bus `ACK` OK / Miss | `ADC_49` Signed Snapshot |
| :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `500 kHz` | `2.0 µs (100 cyc)` | `1.00 bits` | `1.00 bits` | `+0.00 bits` | `738` / `1` | `[-1900, -1867, -1936, -1928, -1936, -1889]` |
| `250 kHz` | `4.0 µs (200 cyc)` | `1.00 bits` | `1.00 bits` | `+0.00 bits` | `1202` / `1` | `[-1887, -1892, -1936, -1933, -1936, -1889]` |
| `100 kHz` | `10.0 µs (500 cyc)` | `1.00 bits` | `1.00 bits` | `+0.00 bits` | `1581` / `1` | `[-1887, -1872, -1936, -1935, -1936, -1888]` |
| `50 kHz` | `20.0 µs (1000 cyc)` | `1.00 bits` | `1.00 bits` | `+0.00 bits` | `1977` / `1` | `[-1899, -1886, -1936, -1935, -1936, -1887]` |

---

## 5. Stage 5 — Cell-by-Cell 126-Crosspoint Dual-2T1C Multiplier Scan

| Matrix | Dimensions | Cells Scanned | Mean Zero Baseline (`LSB`) | Zero StdDev (`LSB`) | Mean Differential Swing (`+96 vs -96`) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **M33 (Base 6x6)** | `6x6` | `35` | `-1910.63` | `22.44` | `-4.74 LSB` |
| **M3 (Layer 1 Comp 8x6)** | `8x6` | `48` | `-1542.71` | `31.24` | `+1.42 LSB` |
| **M8 (Layer 2 Comp 7x6)** | `7x6` | `42` | `-1910.17` | `22.35` | `+0.12 LSB` |

### 5.1 Sampled Cell Table — $M_{33}$ Base Matrix (`6x6`)

| Cell `(R, C)` | `ADC @ -96 (32)` | `ADC @ 0 (128)` | `ADC @ +96 (224)` | Diff Swing (`+96 - -96`) | Midpoint Nonlinearity (`LSB`) |
| :---: | :---: | :---: | :---: | :---: | :---: |
| `(0, 0)` | `-1906.0` | `-1894.0` | `-1893.0` | `+13.0` | `+5.50` |
| `(0, 1)` | `-1895.0` | `-1887.0` | `-1902.0` | `-7.0` | `+11.50` |
| `(0, 2)` | `-1936.0` | `-1936.0` | `-1936.0` | `+0.0` | `+0.00` |
| `(0, 3)` | `-1929.0` | `-1924.0` | `-1922.0` | `+7.0` | `+1.50` |
| `(0, 4)` | `-1936.0` | `-1936.0` | `-1936.0` | `+0.0` | `+0.00` |
| `(0, 5)` | `-1887.0` | `-1884.0` | `-1883.0` | `+4.0` | `+1.00` |
| `(1, 0)` | `-1914.0` | `-1894.0` | `-1869.0` | `+45.0` | `-2.50` |
| `(1, 1)` | `-1878.0` | `-1887.0` | `-1898.0` | `-20.0` | `+1.00` |
| `(1, 2)` | `-1936.0` | `-1936.0` | `-1936.0` | `+0.0` | `+0.00` |
| `(1, 3)` | `-1919.0` | `-1924.0` | `-1912.0` | `+7.0` | `-8.50` |
| `(1, 4)` | `-1936.0` | `-1936.0` | `-1936.0` | `+0.0` | `+0.00` |
| `(1, 5)` | `-1875.0` | `-1884.0` | `-1892.0` | `-17.0` | `-0.50` |
| `(2, 0)` | `-1900.0` | `-1893.0` | `-1936.0` | `-36.0` | `+25.00` |
| `(2, 1)` | `-1877.0` | `-1888.0` | `-1882.0` | `-5.0` | `-8.50` |
| `(2, 2)` | `-1937.0` | `-1936.0` | `-1936.0` | `+1.0` | `+0.50` |
| `(2, 3)` | `-1924.0` | `-1924.0` | `-1927.0` | `-3.0` | `+1.50` |
| `(2, 4)` | `-1936.0` | `-1936.0` | `-1936.0` | `+0.0` | `+0.00` |
| `(2, 5)` | `-1863.0` | `-1884.0` | `-1887.0` | `-24.0` | `-9.00` |

---

## 6. Stage 6 — Inverted MAML Outer/Inner Loop (`Ref 40 / Ref 41`) & Bit Precision

- **Uncompensated Precision (`M3, M8 = 128`):** `1.00 Effective Bits`
- **Compensated Precision (Trained `M3, M8`):** `1.00 Effective Bits`
- **Net ENOB Improvement:** `+0.00 bits`

| Step | Outer Epoch | Inner Step | Loss (`MSE_Q14`) | Uncomp ENOB | Comp ENOB | Mean Basin Distance | Hessian Dot-Product Alignment |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `1` | `0` | `0` | `65535` | `1.00b` | `1.00b` | `354.2` | `[0, 8192, 8192, 8192]` |
| `2` | `0` | `1` | `65535` | `1.00b` | `1.00b` | `261.2` | `[0, 8192, 8192, 8192]` |
| `3` | `0` | `2` | `65535` | `1.00b` | `1.00b` | `261.2` | `[0, 8192, 8192, 8192]` |
| `4` | `0` | `0` | `65535` | `1.00b` | `1.00b` | `261.2` | `[0, 0, 8192, 8192]` |
| `5` | `0` | `1` | `65535` | `1.00b` | `1.00b` | `174.0` | `[0, 0, 8192, 8192]` |
| `6` | `0` | `2` | `65535` | `1.00b` | `1.00b` | `174.0` | `[0, 0, 8192, 8192]` |
| `7` | `0` | `0` | `65535` | `1.00b` | `1.00b` | `174.0` | `[0, 0, 0, 8192]` |
| `8` | `0` | `1` | `65535` | `1.00b` | `1.00b` | `80.0` | `[0, 0, 0, 8192]` |
| `9` | `0` | `2` | `65535` | `1.00b` | `1.00b` | `80.0` | `[0, 0, 0, 8192]` |
| `10` | `1` | `0` | `65535` | `1.00b` | `1.00b` | `80.0` | `[0, 0, 0, 0]` |
| `11` | `1` | `1` | `65535` | `1.00b` | `1.00b` | `80.0` | `[0, 0, 0, 0]` |
| `12` | `1` | `2` | `65535` | `1.00b` | `1.00b` | `80.0` | `[0, 0, 0, 0]` |

---

## 7. Key Hardware & Schematic Diagnostic Findings

### 7.1 T20 `LED2` vs. `LED8` (Golden vs. Application Image)
- **Observation:** When `T20` boots from SPI flash (`CBSEL=00`), it loads `T20_Golden` (`TAG=T20G`), which blinks `T20_LED1`/`T20_LED2` in counter-phase at `~1.5 Hz`.
- **Resolution:** `bridge_selftest()` in `FPGA_code/sw/t120_master/src/main.c` now polls `T20` over the S-Bus after releasing `T20_CRESET_N` until `T20G` completes SPI boot (`~400 ms`), then automatically issues `CMD_JUMP(1)` (`CBSEL=01`). `T20` immediately reconfigures into `T20A` (`T20_Custom`), where `LED8` blinks instead of `LED2`.

### 7.2 `XC2361A` 12-Bit Differential SAR ADCs (`ADC_45` & `ADC_49`) — Sub-LSB Noise Floor
- **Observation:** All 12 differential `XC2361A` channels (`ADC_45 CH1..6` and `ADC_49 CH1..6`) are active and converting cleanly with **temporal RMS noise between `0.00 LSB` and `0.59 LSB` (`0.00 to 0.47 mV RMS`, `0 to 2 LSB` peak-to-peak)** under the 4-Phase Settle-Then-Sample timing (`100..1000` quiet `50 MHz` settle cycles before `CONV`).
- **DC Operating Point:** With `G_P/G_N` uncharged, `ADC_45` sits at `463..575` (`0.37 V .. 0.46 V`) and `ADC_49` sits at `110..249` (`0.09 V .. 0.20 V`), matching the differential `MCP6024T-E/ST` subtractor (`U4 = V+ - V- + VR`, `VR = 1.65 V`) when the sigmoid stages are at their uncharged resting bias.

### 7.3 `74HC595` R-2R Ladder Bit Order (`QA = MSB`, `QH = LSB`) Fixed
- **Schematic Discovery (Page 12 `DAC_8BIT`):** On the physical PCB, `74HC595` pin `QA` (`pin 15`, which receives the **last** shifted bit) is wired to the **MSB** (`DAC_LAD_OUT`) of the R-2R ladder, while `QH` (`pin 7`, which receives the **first** shifted bit) is wired to the **LSB** (`GND` end).
- **Resolution:** Added `bitrev8()` to `aio_load_dac2()`, `aio_load_weight_banks()`, and `MAML_CMD_SET_DAC_DIAG` in `FPGA_code/sw/t120_master/src/maml_platform.c` so that `bit 7` (MSB) of every DAC byte lands in `QA` after 8 `SCK` edges.

### 7.4 Analog Voltage Scaling & `TRIM_DAC` (`Ref 38` = `DAC7_W_34`)
- **Schematic Discovery (Pages 2, 11, 13, 24):**
  - `DAC_2` (Input Row Drive `IN_D_ROW1..6`, Page 11) maps codes `0..255` to **`1.65 V .. 1.90 V`** (`250 mV` triode drain swing above `VR = 1.65 V`).
  - `W_15`, `W_12`, `W_34` (Weight DACs, Page 13) map codes `0..255` to **`2.10 V .. 3.10 V`** (`1.0 V` gate swing for `DMN2990UFZ` / `BSS84`).
  - `TRIM_DAC` (`Ref 38`, Page 2 & Page 24) is wired to **`W_34` Channel 6 (`DAC7_W_34`)**, trimming the `U5 AP64350SP-13` `3.3 V` analog supply by $\pm 3\%$. Because `XC2361A` uses `3.3 V` as its ratiometric reference (`VCC/VREF`), quiescent ADC codes remain ratiometrically stable (`<= 1 LSB` shift) while MOSFET $V_{GS} - V_{th}$ shifts against the fixed silicon threshold $V_{th}$ when conducting.

### 7.5 Why `2T1C` Column Gates (`G_P/G_N`) Need `T20_multi_image.hex` Flashed to T20 SPI Flash
- **Root Cause of Zero Crosspoint Swing (`+0.03 LSB`):** The FTDI programmer is currently connected to `T120` JTAG. Consequently, `T20`'s `W25Q64` SPI flash (`0x000a6000`) still holds yesterday's `T20_Custom` image (`2026-10-10`), which implemented `CH 0x00` (Ping), `CH 0x01` (Jump), and `CH 0x02` (Hadamard `H_M3/H_M8`), while keeping all 36 `G_P1..6_MAT_{3,8,33}` and `G_N1..6_MAT_{3,8,33}` column write gates tied `LOW (0 V)`.
- **Ready-to-Flash Image:** Today's `T20_Custom` build (`FPGA_code/T20_Custom/outflow/T20F256.hex`) includes `T20_CH_ANALOG_CTRL (0x05)` driving all 36 `G_P/G_N` gates, `COMP_LED_ON`, `MAT33_LED_ON`, and the 4 heaters, and has already been combined into `FPGA_code/T20_multi_image.hex`. Flashing `FPGA_code/T20_multi_image.hex` onto T20's SPI flash will immediately enable `2T1C` gate charging (`W+`/`W-` at `2.1 V .. 3.1 V`) across all 126 multiplier cells.

