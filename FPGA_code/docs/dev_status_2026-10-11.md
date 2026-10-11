# Analog Matrix & Inverted MAML Hardware Bring-Up Summary — 2026-10-11

- **Date:** `2026-10-11` (Evening)
- **Target Hardware:** Efinix Trion `T120F324` (Master SoC) + `T20F256` (Analog Matrix Controller) @ `192.168.1.50:5000`
- **Firmware Build:** `T120_SOC_ETH_FW v2.0-MAML (Build 2026-10-11) | Status: T20 ONLINE [TAG=T20A, S-bus ACK 0x06]`

---

## 1. Executive Summary of Today's Milestones

On the first full day of analog matrix hardware bring-up and characterization, the following milestones were achieved and verified directly on the physical PCB:

1. **T120 $\leftrightarrow$ T20 Bridge & Automatic Application Image Boot (`T20A`):**
   - Verified `T120` automatically transitions `T20` from SPI Golden (`T20G`) into `T20_Custom` (`T20A`) via `CMD_JUMP(1)` after `T20_CRESET_N` release.
2. **All 30 `74HC595` R-2R DACs Fixed (`280 ns` `SCK`/`RCK` + `bitrev8`):**
   - Solved the `25 ns` narrow-pulse issue on `GPIOB_TX` high-speed pins by widening `SCK`/`RCK` high time to `280 ns` (`r_sck_div = 15`) and matching MSB/LSB bit order (`QA = pin 15 = MSB`) via `bitrev8()`.
   - Verified clean analog output switching (`1.65 V .. 1.90 V` after the `MCP6024T` scaling buffer) on oscilloscope.
3. **Hardware-Synchronous Autonomous 2T1C Refresh Engine (`10.0 ms` / `100 Hz`, $6 \times 100\ \mu\text{s}$):**
   - Identified and fixed a critical missing feature: previously, the `100 nF` gate storage capacitors (`C_N`, `C_P`) across the 126 Dual-2T1C cells were NOT autonomously refreshed in `IDLE` or `HOLD` mode, allowing gate charge to leak down between measurements.
   - Implemented continuous hardware-timed autonomous refresh driven by the 50 MHz RISC-V CLINT timer (`clint_getTimeLow(BSP_CLINT)`), with future-GUI-tunable parameters set to the exact hardware design specification ([`Design_Specification_Analog_Matrix_2T1C.pdf`](../../Design_Specification_Analog_Matrix_2T1C.pdf)):
     - **Column Setting Time (`g_col_settle_us`):** **`100 µs` per column** (`50 µs` = $5\tau_{\text{charge}}$ for `G_N` + `50 µs` = $5\tau_{\text{charge}}$ for `G_P`, where $\tau_{\text{charge}} = 100\ \Omega \times 100\text{ nF} = 10\ \mu\text{s}$ $\rightarrow$ `>99.3%` settled).
     - **Total Refresh Duty Window:** **`6 × 100 µs = 600 µs`** (`6%` duty cycle).
     - **Autonomous Refresh Period (`g_refresh_period_us`):** **`10.0 ms` (`100 Hz`)** ($\tau_{\text{discharge}} = 1\text{ M}\Omega \times 100\text{ nF} = 100\text{ ms}$ $\rightarrow$ `<9.5%` droop).
   - **Impact:** Matrix 3 (`M3`) peak-to-peak Hadamard response on `ADC_45` immediately increased **8×** (from `13 LSB` to `57–105 LSB` p2p, with `FWHT-16` coherent peaks of `159–354` counts and `+31 dB` SNR above the `2–6` count noise floor).
   - **Deterministic Single-Cell Readout Timing:** Updated `maml_probe_single_cell()` in [`maml_platform.c`](../sw/t120_master/src/maml_platform.c#L1301-L1355) so every single-cell multiplication measurement (`X = 0`, `X = +x_amp`, `X = -x_amp`) is preceded by a synchronous column refresh and sampled at the **exact same relative delay (`10 µs`)** after the refresh window.
4. **Fixed Ethernet 60-Byte Minimum Frame Zero-Padding Bug in `probe_cell()`:**
   - Updated [`gui/udp_client.py`](../../gui/udp_client.py#L512-L513) so `probe_cell()` sends the full 14-byte `MAML_CMD_CELL_DIAG` payload (`x_amp=96, w_fixed=96`) instead of an 8-byte frame that Ethernet zero-padded to `x_amp=0, w_fixed=0`.
5. **Matrix 3 (`M3` $8\times 6 \rightarrow \text{Layer 1 Sigmoid} \rightarrow \text{ADC\_45}$) Confirmed Working & Multiplying:**
   - Verified quiescent DC bias (`1.511 V .. 1.793 V`, within $\pm 140\text{ mV}$ of the $1.650\text{ V}$ center across all 6 columns), Hadamard `FWHT-16` demodulation across all 48 cells (`8 rows × 6 cols`), and static single-cell + multi-row multiplication (`X × W`) through the Layer 1 Sigmoid.

---

## 2. Matrix 3 (`M3` $\rightarrow$ Layer 1 Sigmoid $\rightarrow$ `ADC_45`) Extended Multiplication Results

### 2.1 Quiescent DC Baseline at `W = 0 (128), X = 0 (128)` Across All 6 Columns (`ADC_45[0..5]`)

| Column | `ADC_45` Raw 12-bit (`0..4095`) | `ADC_45` Signed (`raw - 2048`) | Physical Voltage (`V`) | Offset from `1.650 V` Center | Temporal RMS Noise |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **`C1` (`ADC_45[0]`)** | `2225` | `+177 LSB` | `1.7926 V` | `+142.6 mV` | `0.72 LSB` (`0.58 mV`) |
| **`C2` (`ADC_45[1]`)** | `2100` | `+52 LSB` | `1.6919 V` | `+41.9 mV` | `0.89 LSB` (`0.72 mV`) |
| **`C3` (`ADC_45[2]`)** | `2080` | `+32 LSB` | `1.6758 V` | `+25.8 mV` | `0.88 LSB` (`0.71 mV`) |
| **`C4` (`ADC_45[3]`)** | `1875` | `-173 LSB` | `1.5106 V` | `-139.4 mV` | `0.73 LSB` (`0.59 mV`) |
| **`C5` (`ADC_45[4]`)** | `1950` | `-98 LSB` | `1.5710 V` | `-79.0 mV` | `0.74 LSB` (`0.60 mV`) |
| **`C6` (`ADC_45[5]`)** | `1904` | `-144 LSB` | `1.5340 V` | `-116.0 mV` | `0.80 LSB` (`0.64 mV`) |

---

### 2.2 Single-Cell Multiplication: Hold $X$ Fixed, Sweep $W$ (`-96` $\rightarrow$ `+96`), Then Step $X$ (`Row 4 / DAC_2[3]` $\rightarrow$ `Col 1 / ADC_45[0]`)

Only **one cell (`Row 4, Col 1`)** out of 48 is varied (`W = -96..+96`, `X = -120..+120`); all other 47 cells are held at `W = 0, X = 0`.
- **Quiescent `(X=0, W=0)` Baseline on `ADC_45[0]`:** Raw 12-bit = **`2225`** | Signed (`raw - 2048`) = **`+177 LSB`** | Voltage = **`1.7926 V`**

#### Step 1: Hold Input $X = -120$ Fixed (`DAC_2[3] = 8` $\rightarrow$ $1.658\text{ V}$) & Sweep Weight $W$ (`-96` $\rightarrow$ `+96`)

| Held Input $X$ (`DAC_2[3]`) | Swept Weight $W$ (`W+ / W-`) | Actual `ADC_45[0]` Raw 12-bit | Actual `ADC_45[0]` Signed (`raw-2048`) | Actual Voltage | Offset vs `(X=0, W=0)` | $\Delta\text{ADC}_W$ vs $W=-96$ |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **`X = -120`** (`DAC=8`, $1.658\text{ V}$) | **`W = -96`** (`32 / 224`) | **`2163`** | **`+115 LSB`** | `1.7427 V` | `-62 LSB` | `+0 LSB` |
| **`X = -120`** (`DAC=8`, $1.658\text{ V}$) | **`W = -48`** (`80 / 176`) | **`2174`** | **`+126 LSB`** | `1.7515 V` | `-51 LSB` | **`+11 LSB`** |
| **`X = -120`** (`DAC=8`, $1.658\text{ V}$) | **`W = 0`** (`128 / 128`) | **`2215`** | **`+167 LSB`** | `1.7845 V` | `-10 LSB` | **`+52 LSB`** |
| **`X = -120`** (`DAC=8`, $1.658\text{ V}$) | **`W = +48`** (`176 / 80`) | **`2228`** | **`+180 LSB`** | `1.7950 V` | `+3 LSB` | **`+65 LSB`** |
| **`X = -120`** (`DAC=8`, $1.658\text{ V}$) | **`W = +96`** (`224 / 32`) | **`2229`** | **`+181 LSB`** | `1.7958 V` | `+4 LSB` | **`+66 LSB`** |

#### Step 2: Hold Input $X = 0$ Fixed (`DAC_2[3] = 128` $\rightarrow$ $1.775\text{ V}$) & Sweep Weight $W$ (`-96` $\rightarrow$ `+96`)

| Held Input $X$ (`DAC_2[3]`) | Swept Weight $W$ (`W+ / W-`) | Actual `ADC_45[0]` Raw 12-bit | Actual `ADC_45[0]` Signed (`raw-2048`) | Actual Voltage | Offset vs `(X=0, W=0)` | $\Delta\text{ADC}_W$ vs $W=-96$ |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **`X = 0`** (`DAC=128`, $1.775\text{ V}$) | **`W = -96`** (`32 / 224`) | **`2164`** | **`+116 LSB`** | `1.7435 V` | `-61 LSB` | `+0 LSB` |
| **`X = 0`** (`DAC=128`, $1.775\text{ V}$) | **`W = -48`** (`80 / 176`) | **`2176`** | **`+128 LSB`** | `1.7531 V` | `-49 LSB` | **`+12 LSB`** |
| **`X = 0`** (`DAC=128`, $1.775\text{ V}$) | **`W = 0`** (`128 / 128`) | **`2225`** | **`+177 LSB`** | `1.7926 V` | `+0 LSB` | **`+61 LSB`** |
| **`X = 0`** (`DAC=128`, $1.775\text{ V}$) | **`W = +48`** (`176 / 80`) | **`2238`** | **`+190 LSB`** | `1.8031 V` | `+13 LSB` | **`+74 LSB`** |
| **`X = 0`** (`DAC=128`, $1.775\text{ V}$) | **`W = +96`** (`224 / 32`) | **`2237`** | **`+189 LSB`** | `1.8023 V` | `+12 LSB` | **`+73 LSB`** |

#### Step 3: Hold Input $X = +120$ Fixed (`DAC_2[3] = 248` $\rightarrow$ $1.893\text{ V}$) & Sweep Weight $W$ (`-96` $\rightarrow$ `+96`)

| Held Input $X$ (`DAC_2[3]`) | Swept Weight $W$ (`W+ / W-`) | Actual `ADC_45[0]` Raw 12-bit | Actual `ADC_45[0]` Signed (`raw-2048`) | Actual Voltage | Offset vs `(X=0, W=0)` | $\Delta\text{ADC}_W$ vs $W=-96$ | **Multiplicative Input Gain $\Delta\text{ADC}_X$ (`ADC(X=+120) - ADC(X=-120)`)** |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`X = +120`** (`DAC=248`, $1.893\text{ V}$) | **`W = -96`** (`32 / 224`) | **`2164`** | **`+116 LSB`** | `1.7435 V` | `-61 LSB` | `+0 LSB` | `2164 - 2163 =` **`+1 LSB`** *(Cell OFF/Blocked)* |
| **`X = +120`** (`DAC=248`, $1.893\text{ V}$) | **`W = -48`** (`80 / 176`) | **`2175`** | **`+127 LSB`** | `1.7523 V` | `-50 LSB` | **`+11 LSB`** | `2175 - 2174 =` **`+1 LSB`** *(Cell nearly OFF)* |
| **`X = +120`** (`DAC=248`, $1.893\text{ V}$) | **`W = 0`** (`128 / 128`) | **`2226`** | **`+178 LSB`** | `1.7934 V` | `+1 LSB` | **`+62 LSB`** | `2226 - 2215 =` **`+11 LSB`** *(Half conductance)* |
| **`X = +120`** (`DAC=248`, $1.893\text{ V}$) | **`W = +48`** (`176 / 80`) | **`2242`** | **`+194 LSB`** | `1.8063 V` | `+17 LSB` | **`+78 LSB`** | `2242 - 2228 =` **`+14 LSB`** *(Cell ON/Conducting)* |
| **`X = +120`** (`DAC=248`, $1.893\text{ V}$) | **`W = +96`** (`224 / 32`) | **`2240`** | **`+192 LSB`** | `1.8047 V` | `+15 LSB` | **`+76 LSB`** | `2240 - 2229 =` **`+11 LSB`** *(Upper Sigmoid tail)* |

---

### 2.3 All-6-Row Combined Multiplication (`DAC_2[0..5]` $\rightarrow$ `Col 1 / ADC_45[0]`)

#### Step 1: Hold Input $X = -120$ (`DAC_2 = 8` $\rightarrow$ $1.658\text{ V}$) & Sweep Weight $W$ (`-96` $\rightarrow$ `+96`)

| Held Input $X$ (`DAC_2[0..5]`) | Swept Weight $W$ (`W+ / W-`) | Actual `ADC_45[0]` Raw 12-bit | Actual `ADC_45[0]` Signed (`raw-2048`) | Actual Voltage | Offset vs `(X=0, W=0)` | $\Delta\text{ADC}_W$ vs $W=-96$ |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **`X = -120`** (`DAC=8`, $1.658\text{ V}$) | **`W = -96`** (`32 / 224`) | **`2171`** | **`+123 LSB`** | `1.7491 V` | `-55 LSB` | `+0 LSB` |
| **`X = -120`** (`DAC=8`, $1.658\text{ V}$) | **`W = -48`** (`80 / 176`) | **`2182`** | **`+134 LSB`** | `1.7580 V` | `-44 LSB` | **`+11 LSB`** |
| **`X = -120`** (`DAC=8`, $1.658\text{ V}$) | **`W = 0`** (`128 / 128`) | **`2211`** | **`+163 LSB`** | `1.7813 V` | `-15 LSB` | **`+40 LSB`** |
| **`X = -120`** (`DAC=8`, $1.658\text{ V}$) | **`W = +48`** (`176 / 80`) | **`2254`** | **`+206 LSB`** | `1.8160 V` | `+28 LSB` | **`+83 LSB`** |
| **`X = -120`** (`DAC=8`, $1.658\text{ V}$) | **`W = +96`** (`224 / 32`) | **`2261`** | **`+213 LSB`** | `1.8216 V` | `+35 LSB` | **`+90 LSB`** |

#### Step 2: Hold Input $X = 0$ (`DAC_2 = 128` $\rightarrow$ $1.775\text{ V}$) & Sweep Weight $W$ (`-96` $\rightarrow$ `+96`)

| Held Input $X$ (`DAC_2[0..5]`) | Swept Weight $W$ (`W+ / W-`) | Actual `ADC_45[0]` Raw 12-bit | Actual `ADC_45[0]` Signed (`raw-2048`) | Actual Voltage | Offset vs `(X=0, W=0)` | $\Delta\text{ADC}_W$ vs $W=-96$ |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **`X = 0`** (`DAC=128`, $1.775\text{ V}$) | **`W = -96`** (`32 / 224`) | **`2177`** | **`+129 LSB`** | `1.7539 V` | `-49 LSB` | `+0 LSB` |
| **`X = 0`** (`DAC=128`, $1.775\text{ V}$) | **`W = -48`** (`80 / 176`) | **`2194`** | **`+146 LSB`** | `1.7676 V` | `-32 LSB` | **`+17 LSB`** |
| **`X = 0`** (`DAC=128`, $1.775\text{ V}$) | **`W = 0`** (`128 / 128`) | **`2227`** | **`+179 LSB`** | `1.7942 V` | `+1 LSB` | **`+50 LSB`** |
| **`X = 0`** (`DAC=128`, $1.775\text{ V}$) | **`W = +48`** (`176 / 80`) | **`2272`** | **`+224 LSB`** | `1.8305 V` | `+46 LSB` | **`+95 LSB`** |
| **`X = 0`** (`DAC=128`, $1.775\text{ V}$) | **`W = +96`** (`224 / 32`) | **`2280`** | **`+232 LSB`** | `1.8369 V` | `+54 LSB` | **`+103 LSB`** |

#### Step 3: Hold Input $X = +120$ (`DAC_2 = 248` $\rightarrow$ $1.893\text{ V}$) & Sweep Weight $W$ (`-96` $\rightarrow$ `+96`)

| Held Input $X$ (`DAC_2[0..5]`) | Swept Weight $W$ (`W+ / W-`) | Actual `ADC_45[0]` Raw 12-bit | Actual `ADC_45[0]` Signed (`raw-2048`) | Actual Voltage | Offset vs `(X=0, W=0)` | $\Delta\text{ADC}_W$ vs $W=-96$ | **Multiplicative Input Gain $\Delta\text{ADC}_X$ (`ADC(X=+120) - ADC(X=-120)`)** |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`X = +120`** (`DAC=248`, $1.893\text{ V}$) | **`W = -96`** (`32 / 224`) | **`2177`** | **`+129 LSB`** | `1.7539 V` | `-49 LSB` | `+0 LSB` | `2177 - 2171 =` **`+6 LSB`** |
| **`X = +120`** (`DAC=248`, $1.893\text{ V}$) | **`W = -48`** (`80 / 176`) | **`2195`** | **`+147 LSB`** | `1.7684 V` | `-31 LSB` | **`+18 LSB`** | `2195 - 2182 =` **`+13 LSB`** |
| **`X = +120`** (`DAC=248`, $1.893\text{ V}$) | **`W = 0`** (`128 / 128`) | **`2230`** | **`+182 LSB`** | `1.7966 V` | `+4 LSB` | **`+53 LSB`** | `2230 - 2211 =` **`+19 LSB`** |
| **`X = +120`** (`DAC=248`, $1.893\text{ V}$) | **`W = +48`** (`176 / 80`) | **`2274`** | **`+226 LSB`** | `1.8321 V` | `+48 LSB` | **`+97 LSB`** | `2274 - 2254 =` **`+20 LSB`** |
| **`X = +120`** (`DAC=248`, $1.893\text{ V}$) | **`W = +96`** (`224 / 32`) | **`2281`** | **`+233 LSB`** | `1.8377 V` | `+55 LSB` | **`+104 LSB`** | `2281 - 2261 =` **`+20 LSB`** |

---

### 2.4 Summary Across Sampled Matrix 3 Crosspoints

| Matrix 3 Crosspoint Cell | Quiescent Baseline `(X=0, W=0)` | Weight Span $\Delta\text{ADC}_W$ (`W=-96` $\rightarrow$ `+96`) | Input Gain $\Delta\text{ADC}_X$ at **$W = -96$** (`X=-120` $\rightarrow$ `+120`) | Input Gain $\Delta\text{ADC}_X$ at **$W = +48 / +96$** (`X=-120` $\rightarrow$ `+120`) |
| :--- | :---: | :---: | :---: | :---: |
| **`Row 4, Col 1`** (`DAC_2[3]` $\rightarrow$ `ADC_45[0]`) | `2225` (`+177 LSB`, $1.793\text{ V}$) | **`+78 LSB`** (`2164` $\rightarrow$ `2242`) | **`+1 LSB`** (`2163` $\rightarrow$ `2164`) | **`+14 LSB`** (`2228` $\rightarrow$ `2242`) |
| **`Row 5, Col 1`** (`DAC_2[4]` $\rightarrow$ `ADC_45[0]`) | `2224` (`+176 LSB`, $1.792\text{ V}$) | **`+76 LSB`** (`2186` $\rightarrow$ `2262`) | **`-1 LSB`** (`2187` $\rightarrow$ `2186`) | **`+10 LSB`** (`2252` $\rightarrow$ `2262`) |
| **`Row 4, Col 2`** (`DAC_2[3]` $\rightarrow$ `ADC_45[1]`) | `2100` (`+52 LSB`, $1.692\text{ V}$) | **`+45 LSB`** (`2055` $\rightarrow$ `2100`) | **`+2 LSB`** (`2054` $\rightarrow$ `2056`) | **`+9 LSB`** (`2087` $\rightarrow$ `2096`) |
| **`Row 6, Col 3`** (`DAC_2[5]` $\rightarrow$ `ADC_45[2]`) | `2080` (`+32 LSB`, $1.676\text{ V}$) | **`+15 LSB`** (`2082` $\rightarrow$ `2097`) | **`+1 LSB`** (`2081` $\rightarrow$ `2082`) | **`+8 LSB`** (`2089` $\rightarrow$ `2097`) |
| **All 6 Rows Combined** $\rightarrow$ `ADC_45[0]` | `2226` (`+178 LSB`, $1.793\text{ V}$) | **`+104 LSB`** (`2177` $\rightarrow$ `2281`) | **`+6 LSB`** (`2171` $\rightarrow$ `2177`) | **`+20..+23 LSB`** (`2261` $\rightarrow$ `2281`) |

---

### 2.5 Full 8-Row $\times$ 6-Column Hadamard `FWHT-16` Demodulation on Matrix 3 (`0x00FF`)

With the `10.0 ms` (`100 Hz`) autonomous refresh active and all weights centered (`W = 0`, code `128`):
- **Quiet Noise Floor (`0x0000`):** `[5, 3, 6, 2, 4, 3]` counts ($\le 0.4\text{ LSB}$).
- **Active `M3` (`0x00FF`) Demodulated Matrix (`Walsh k = 1..8`):**

| Hadamard Basis | Row Input Source | C1 | C2 | C3 | C4 | C5 | C6 |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`k = 1` (`H_M3_1`)** | `DAC_2[0]` (`1.775 V`) | `+116` | `+145` | `+111` | `+83` | `+65` | `+71` |
| **`k = 2` (`H_M3_2`)** | `DAC_2[1]` (`1.775 V`) | `+136` | `+129` | `+107` | `+63` | `+59` | `+83` |
| **`k = 3` (`H_M3_3`)** | `DAC_2[2]` (`1.775 V`) | `+148` | `+139` | `+119` | `+61` | `+65` | `+81` |
| **`k = 4` (`H_M3_4`)** | `DAC_2[3]` (`1.775 V`) | `+178` | `+109` | `+73` | `+69` | `+81` | `+95` |
| **`k = 5` (`H_M3_5`)** | `DAC_2[4]` (`1.775 V`) | `+142` | `+135` | `+109` | `+87` | `+75` | `+89` |
| **`k = 6` (`H_M3_6`)** | `DAC_2[5]` (`1.775 V`) | `+154` | `+183` | `+117` | `+79` | `+97` | `+117` |
| **`k = 7` (`H_M3_7`)** | **Ref Row 7 (`1.90 V`, $330\text{ k}\Omega$)** | **`-354`** | **`-275`** | **`-271`** | **`-167`** | **`-141`** | **`-157`** |
| **`k = 8` (`H_M3_8`)** | **Bias Row 8 (`1.90 V`, $1\text{ M}\Omega$)** | **`+218`** | **`+183`** | **`+265`** | **`+227`** | **`+159`** | **`+191`** |

---

## 3. Open Items & Next Steps for Tomorrow

1. **Investigate the `-1400 to -1600 LSB` (`~0.36 V .. 0.50 V`) DC Baseline Offset on `ADC_49` (`M33 + M8` Final Summing Stage):**
   - While `ADC_45` (`M3` + Layer 1 Sigmoid) sits cleanly around `1.65 V` (`-173 to +178 LSB`), `ADC_49` sits near `-1400 to -1600 LSB` (`raw = 448..661`), clipping `CH3` and `CH5` against the lower rail until driven strongly positive.
   - Check the Trim-DAC (`Ref 38` = `DAC7_W_34` / `DAC8_W_34`) polarity/range and the `M33` / `M8` column TIA biasing around `1.65 V`.
2. **True Dynamic-Range ENOB Normalization & Live Jumper Re-Zeroing:**
   - Replace the hardcoded `2048 LSB` full-scale numerator in `maml_compute_enob_q8()` with the actual signal RMS of `z_target`, and add a "Re-Zero ADC Baseline" button in the GUI so changing the physical compensation jumpers (`Ref 10`) does not use a stale boot-time `g_adc49_zero_cal` offset.
3. **Expose Autonomous Refresh Tuning (`g_col_settle_us` and `g_refresh_period_us`) in the GUI:**
   - The firmware already uses `g_col_settle_us = 100` (`600 µs` total refresh duty window) and `g_refresh_period_us = 10000` (`10.0 ms`, `100 Hz`); wire these to GUI spinboxes in a future pass.

