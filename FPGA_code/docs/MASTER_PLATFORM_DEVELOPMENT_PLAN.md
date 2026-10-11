# Master Development & Architecture Specification: Inverted MAML Analog In-Memory Computing (AIMC) Platform

**Project:** Inverted MAML 3×6×6 Analog Matrix Computing Platform  
**Patent Reference:** SE 2630397-4 (*Method and System for Analog In-Memory Computing with Proprioceptive Drift Compensation*)  
**Target Hardware:** Dual-FPGA Custom PCBA (`Efinix Trion T120F324` Master + `Efinix Trion T20F256` Analog Matrix Controller)  
**Document Purpose:** Comprehensive, implementation-ready specification for AI coding agents and engineers to build Track 1 (Embedded FPGA Logic & SoC Firmware) and Track 2 (English PC GUI, 3D Loss Landscape Visualizer & Automated Diagnostics).

---

## 0. Current Baseline & Verified Foundation

The foundational inter-FPGA communication, clocking, Ethernet stack, and remote boot infrastructure are **already implemented and verified on physical hardware**:

1. **T120F324 Master SoC (`FPGA_code/T120F324/`):**
   - Runs the Efinix Sapphire RISC-V SoC (`RISC_mini`) at `50 MHz` (`T120_GCLK`).
   - **100BASE-TX Ethernet (`RTL8211F-CG`):** Active at IP `192.168.1.50`, UDP port `5000` (`eth_mac_100m` at APB `0xF810_2000`, `mdio_master` at `0xF810_1000`).
   - **Inter-FPGA Bridge (`t120_inter_fpga_bridge` at APB `0xF810_3000`):**
     - Generates master bus clock `T20_CLK9` (`1.25 MHz .. 10 MHz`, default `2 MHz`).
     - **H-Bus (Hardware-Synchronous Hadamard Stream):** `TX11_T20_P1` (`H_SYNC`), `TX11_T20_N1` (`H_DATA`), `RX00_T20_P1` (`H_ACK`). Zero-jitter hardware sequencer (`t120_hbus_seq.sv`) with `h_step_strobe` trigger output.
     - **S-Bus (CRC8 Service Bus):** 2-bit TX (`TX12_T20_P1/N1`) and 4-bit RX (`RX02_T20_P1/N1`, `RX03_T20_P1/N1`) for configuration, status polling, SPI flash updates, and reconfiguration commands.
     - **Hardware Reset Line:** `T120_LED1` patch wire drives `T20_CRESET_N`.
2. **T20F256 Analog Matrix Companion (`FPGA_code/T20_Golden/` & `FPGA_code/T20_Custom/`):**
   - Programmed with a dual-image SPI flash (`FPGA_code/T20_multi_image.hex`):
     - **Image 0 (`0x000000`, `T20_Golden`, `TAG=T20G`):** Safe fallback bootloader (`T20_LED2` blinking).
     - **Image 1 (`0x080000`, `T20_Custom`, `TAG=T20A`):** Application image (`T20_LED8` 50 MHz heartbeat, `T20_LED7` `T20_CLK9` indicator, `T20_LED6` H-bus traffic indicator, `T20_LED2` off).
   - **Live Reconfiguration Verified:** Sending UDP command `"JUMP_APP"` to `192.168.1.50:5000` issues S-bus `CMD_JUMP` (`0x04` on Channel `0x01`), causing T20 to switch via `CONFIG_CTRL0` into `T20_Custom`.

> [!IMPORTANT]
> **Critical Companion Document:** Before writing any gradient, learning loop, or FWHT code, the implementing agent **MUST** read [`NON_BACKPROP_HADAMARD_GRADIENT_RULES.md`](./NON_BACKPROP_HADAMARD_GRADIENT_RULES.md). **Do NOT implement standard digital backpropagation ($\delta \cdot x_i$).**

---

## 1. Complete Hardware Inventory & Pinout Architecture

### 1.1 Analog Compute Triad Topology
The board implements an **Atomic Triad** of three coupled analog 2T1C (`DOX3134A` MOSFET + `100 nF` storage capacitor) crosspoint matrices:

1. **Primary Payload Matrix ($M_{33}$, Patent Ref `33`):**
   - `6 rows × 6 columns` of slow-decay compute cells ($\tau_{\text{slow}} = 1\text{ M}\Omega \times 100\text{ nF} = 100\text{ ms}$) plus bias/trim channels.
   - Holds the deterministic target weights (`Ref 34`, charged via DAC bank `W_34`).
   - Receives the 6-channel analog input vector $\mathbf{x}$ from `DAC_2` (`Ref 2`).
   - **Never perturbed by Hadamard signals.**
2. **First Correction Matrix ($M_3$, Layer 1, Patent Ref `3`):**
   - `8 rows × 6 columns` (charged via DAC bank `W_15`, perturbed via `H_M3_P/N[1..8]`).
   - **Rows 1–6 (Lower Part, Ref `37`):** 6 compute rows driven by input `DAC_2` (`Ref 2`) with $\tau_{\text{slow}} = 100\text{ ms}$.
   - **Rows 7–8 (Upper Part, Ref `30`):** Reference / bias rows containing **accelerated-discharge reference clock cells (`Ref 29`, $\tau_{\text{fast}} = 330\text{ k}\Omega \times 100\text{ nF} = 33\text{ ms}$)** that sweep steeply across each refresh cycle (`Data 230 → 30`) to provide an intrinsic analog time-base (`Ref 32`) for the correction network.
   - Column outputs pass through **First Analog Non-Linear Activation `4` (Sigmoid / $\tanh$)** and are sampled by **`ADC_45` (`Ref 45`, 6 channels)** before entering Matrix `8`.
3. **Second Correction Matrix ($M_8$, Layer 2, Patent Ref `8`):**
   - `7 rows × 6 columns` (charged via DAC bank `W_12`, perturbed via `H_M8_P/N[1..7]`).
   - Rows 1–6 receive the intermediate signals $\mathbf{x}^{(8)}$ from Layer 1 (`ADC_45`); Row 7 serves as a learnable bias/reference row.
   - Column outputs pass through **Second Analog Non-Linear Activation `10`** (configurable via physical 3-state hardware jumper) and sum into **Analog Summing Junction `35`** with the output of Primary Matrix `33`.
   - The final summed 6-channel output is digitized by **`ADC_49` (`Ref 49`, 6 channels)**.

---

### 1.2 T120F324 Peripheral Pinout (DACs & ADCs)

#### A. Four `74HC595` 8-Bit Shift-Register DAC Banks (Driven by T120)
Each DAC channel consists of an 8-bit `74HC595` serial-in/parallel-out shift register driving an 8-bit R-2R analog DAC ladder (`0..255` digital code). All channels within a bank share a common Latch Clock (`RCK_*`, rising edge transfers shift register to DAC output) and active-low Clear (`SCLR_*`, must be held HIGH `1'b1` during normal operation), while having individual Serial Data (`SI_*`) and Shift Clock (`SCK_*`) lines (allowing all 6 or 8 channels in a bank to be shifted in parallel in just **8 clock cycles**!).

| DAC Bank | Patent Ref | Channels | T120 Signal Names | Functional Role |
|:---|:---|:---|:---|:---|
| **`DAC_2`** | `Ref 2` | 6 (`DAC1..6`) | `SI_DAC[1..6]_DAC_2`, `SCK_DAC[1..6]_DAC_2`, `RCK_DAC_2`, `SCLR_DAC_2` | Primary 6-row analog input vector $\mathbf{x}$ (`1.65V` @ `0` $\to$ `1.90V` @ `255`). |
| **`W_15`** | `Ref 46` ($M_3$) | 8 (`DAC1..8`) | `SI_DAC[1..8]_W_15`, `SCK_DAC[1..8]_W_15`, `RCK_DAC_W_15`, `SCLR_DAC_W_15` | Weight charging voltages (`2.1V` $\to$ `3.1V`) for Matrix `3` (rows 1–6 compute, rows 7–8 fast-decay ref cells `Ref 29`). |
| **`W_12`** | `Ref 46` ($M_8$) | 8 (`DAC1..8`) | `SI_DAC[1..8]_W_12`, `SCK_DAC[1..8]_W_12`, `RCK_DAC_W_12`, `SCLR_DAC_W_12` | Weight charging voltages for Matrix `8` (rows 1–6 compute, row 7 bias, ch 8 spare/trim). |
| **`W_34`** | `Ref 34, 38` ($M_{33}$) | 8 (`DAC1..8`) | `SI_DAC[1..8]_W_34`, `SCK_DAC[1..8]_W_34`, `RCK_DAC_W_34`, `SCLR_DAC_W_34` | Weight charging voltages for Primary Matrix `33` (`Ref 34`) + **Matrix Supply Power Trim (`trim-DAC`, `Ref 38`)**. |

> [!WARNING]
> **Mandatory Pin Direction Fix in `T120_MALM.peri.xml` and `T120F324/top_level.sv`:**
> In the current baseline `FPGA_code/T120F324/top_level.sv` (lines 13–18), six DAC pins (`RCK_DAC_W_34`, `SCK_DAC7_W_34`, `SCK_DAC8_W_34`, `SI_DAC2_DAC_2`, `SI_DAC5_DAC_2`, `SI_DAC8_W_34`) are still declared as `input` from an earlier pin-exploration template, and `SCLR_DAC_W_34` is tied to `1'b0` on line 251.
> **Action Required:** Change those 6 ports to `output` in both `T120_MALM.peri.xml` and `top_level.sv`, and drive `SCLR_DAC_W_34 = 1'b1` (de-asserted) during normal operation so all 4 DAC banks operate fully.

#### B. Two 6-Channel `XC2361A` Serial SAR ADC Banks (Read by T120)
Both intermediate `ADC_45` (`Ref 45`) and final `ADC_49` (`Ref 49`) consist of 6 parallel `XC2361A` SPI SAR ADCs:

| ADC Bank | Patent Ref | Channels | T120 Signal Names | Sampling Role |
|:---|:---|:---|:---|:---|
| **`ADC_45`** | `Ref 45` | 6 (`OUT1..6`) | Inputs: `OUT[1..6]_ADC_45`<br>Outputs: `ADC_45_CONV`, `ADC_45_SCK_1_2`, `ADC_45_SCK_3_4`, `ADC_45_SCK_5_6` | Digitizes Layer 1 column outputs $\mathbf{z}^{(45)} = \mathbf{x}^{(8)}$ after First Sigmoid `4`. Used for $M_3$ Hadamard demodulation (`Eq. 7`) and Carrier Wave Search (`Eq. 5/6`). |
| **`ADC_49`** | `Ref 49` | 6 (`OUT1..6`) | Inputs: `OUT[1..6]_ADC_49`<br>Outputs: `ADC_49_CONV`, `ADC_49_SCK_1_2`, `ADC_49_SCK_3_4`, `ADC_49_SCK_5_6` | Digitizes final summed column outputs $\mathbf{z}^{(49)}$ (`Ref 11`) after Summing Junction `35`. Used for output error $Er_j^{(49)}$ (`Eq. 1`) and $M_8$ Hadamard demodulation (`Eq. 2`). |

---

### 1.3 T20F256 Peripheral Pinout (3-State Hadamard, Differential `G_P/G_N` Column Gates, Heaters, Analog LEDs)

All analog switching, column refresh gates, thermal heaters, and LED array enables reside on the `T20F256` FPGA (`FPGA_code/Auto_gen_Interface_spec_FPGA/T20F256_connection_report.txt` and `T20F256_connections.json`):

1. **3-Stated Differential Hadamard Perturbation Outputs (`Ref 5, 6, 7`, `Data` + `OE`):**
   - **Matrix 3 (`8 pairs` = 16 pins):** `H_M3_P1..P8` and `H_M3_N1..N8` (with per-pin Output Enables `H_M3_P1_OE..P8_OE` and `H_M3_N1_OE..N8_OE`).
   - **Matrix 8 (`7 pairs` = 14 pins):** `H_M8_P1..P7` and `H_M8_N1..N7` (with per-pin Output Enables `H_M8_P1_OE..P7_OE` and `H_M8_N1_OE..N7_OE`).
   - **Mandatory 3-State (`Hi-Z`) Centering Rule:**
     - During an active Hadamard table state (`vec[15] == 0` and `en_mask[k] == 1`), `OE = 1` actively drives complementary `+` / `-` levels (`P = 1, N = 0` or `P = 0, N = 1`).
     - **When leaving the Hadamard table (`vec[15] == 1`), when a row is masked off (`en_mask[k] == 0`), or at reset:** `OE = 0` (**High-Impedance `Hi-Z`**, `pull_option="none"`). Both `H+` and `H-` float in the analog middle (`VR = 1.65V`) so that the permutation is **100% centered** with zero residual charge injection!
   - **Efinix Trion 3-State Rule:** Never assign `'z` in logic code. In `T20F256.peri.xml`, configure each Hadamard pin as `mode="inout"` with `<efxpt:input_config name="" pull_option="none"/>`, `<efxpt:output_config name="<PIN>"/>`, and `<efxpt:output_enable_config name="<PIN>_OE"/>`, exposing two ports (`<PIN>` and `<PIN>_OE`) on `top_level.sv`.
2. **Differential Column Refresh Gate Drivers (`Ref 48`, 36 pins = 18 `G_P/G_N` pairs across 3 matrices):**
   - Every crosspoint is a **Differential Dual-2T1C (`2X_2T1C`) cell** with a positive half-cell (`W+`, `G+`, `H+`, `OUT_COL+`) and a negative half-cell (`W-`, `G-`, `H-`, `OUT_COL-`).
   - **Matrix 3 Differential Column Gates (12 pins):** `G_P1_MAT_3..G_P6_MAT_3` (`D13, F13, D12, E11, B13, A14`) and `G_N1_MAT_3..G_N6_MAT_3` (`D14, E13, D11, F11, C13, A13`).
   - **Matrix 8 Differential Column Gates (12 pins):** `G_P1_MAT_8..G_P6_MAT_8` (`B9, A9, C9, B8, E10, D10`) and `G_N1_MAT_8..G_N6_MAT_8` (`A10, B10, D9, A8, C10, E9`).
   - **Matrix 33 Differential Column Gates (12 pins):** `G_P1_MAT_33..G_P6_MAT_33` (`E6, D7, C6, D5, B6, A6`) and `G_N1_MAT_33..G_N6_MAT_33` (`E7, D6, B7, C5, C7, A5`).
3. **Thermal Board Heaters (`HEAT_1_EN` .. `HEAT_4_EN`):**
   - `HEAT_1_EN` (`Pin E16`, `GPIOR_119_CTRL12`)
   - `HEAT_2_EN` (`Pin E15`, `GPIOR_120_CLK15`)
   - `HEAT_3_EN` (`Pin F15`, `GPIOR_122_CLK13_CDI21`)
   - `HEAT_4_EN` (`Pin F16`, `GPIOR_123_CLK12_CDI20`)
4. **Analog Column Output LED Array Switches:**
   - `COMP_LED_ON` (`Pin J3`, `GPIOL_16`): Switches ON/OFF the analog LED array monitoring the Compensation matrix column outputs.
   - `MAT33_LED_ON` (`Pin K1`, `GPIOL_18`): Switches ON/OFF the analog LED array monitoring the Primary Matrix `33` column outputs.

---

## 2. Track 1 — Embedded FPGA Logic & Firmware Specification (`T20` & `T120`)

### 2.1 Ultra-Low Frequency Heater PWM Controller (`0.2 Hz` on T20)
To thermally warp the PCB and induce realistic, spatially varying transistor $V_{\text{th}}$ and capacitor leakage drift **without injecting high-frequency switching noise into the analog crosspoint array**:

- **PWM Carrier Frequency:** Strictly **0.2 Hz** (`5.0 second` full period = `250,000,000` cycles of `CLK_50MHZ` on T20).
- **Resolution & Phase Staggering:**
  - 8-bit duty cycle resolution (`0..255`, where `0 = 0% OFF`, `255 = 100% ON`, step size $\approx 19.6\text{ ms}$) independently configurable for `HEAT_1_EN`, `HEAT_2_EN`, `HEAT_3_EN`, and `HEAT_4_EN`.
  - Phase-staggered turn-on (`0°`, `90°`, `180°`, `270°` across the 5-second period) to minimize peak $dI/dt$ on the board power supply.
- **Hardware Safety Interlock & Watchdog:**
  - `HEAT_1..4_EN` outputs on T20 are hardware-gated by:
    ```systemverilog
    assign HEAT_1_EN = heater_armed_reg & heater_wdog_ok & pwm_out[0];
    ```
  - `heater_armed_reg` defaults to `1'b0` on reset and can only be set when the user explicitly toggles the **"ARM HEATER"** switch in the PC GUI.
  - `heater_wdog_ok` requires a periodic heartbeat frame over S-bus from T120 (which in turn requires an active UDP heartbeat from the PC GUI within the last `4.0 seconds`). If the PC GUI disconnects or crashes, all 4 heaters automatically shut off within `4 seconds`.

---

### 2.2 Synchronized Differential DAC, Dual-2T1C Column Refresh & ADC Engine

#### A. Differential Dual-2T1C Refresh Pulse Sequence (`Ref 18`)
All DACs (`0..255` around `128 = 1.65V`) and ADCs (`0..4095` around `2048 = 1.65V`) operate with full differential `(+/-)` symmetry. At the start of each refresh cycle $T_{\text{INF}}$ (default $10\text{ ms}$ at $500\text{ kHz}$ Hadamard rate):
1. **3-State Hadamard Perturbation (`Hi-Z`):** T120 shifts `16'h8000` (`vec[15] = 1`) so T20 sets `H_M3_OE = 0` and `H_M8_OE = 0` (`Hi-Z`, floating in the analog middle `1.65V`).
2. **Column-by-Column Differential Capacitor Recharge ($j = 1 \dots 6$):**
   - **Positive Half-Cell (`G_Pj_MAT_*`):** For column $j$, T120 shifts the positive weight DAC codes $W_{i,j}^+ = \text{clamp}(128 + w_{i,j}, 0, 255)$ into `W_15` ($M_3$), `W_12` ($M_8$), and `W_34` ($M_{33}$) in parallel and pulses `RCK_DAC_W_*`. After DAC settling ($\sim 2\,\mu\text{s}$), T20 pulses `G_Pj_MAT_3`, `G_Pj_MAT_8`, and `G_Pj_MAT_33` high for $T_{\text{charge}}$ (`10–20 µs`), charging the `W+` storage capacitors.
   - **Negative Half-Cell (`G_Nj_MAT_*`):** Next, T120 shifts the complementary negative weight DAC codes $W_{i,j}^- = \text{clamp}(128 - w_{i,j}, 0, 255)$ into `W_15`, `W_12`, and `W_34` and pulses `RCK_DAC_W_*`. After DAC settling ($\sim 2\,\mu\text{s}$), T20 pulses `G_Nj_MAT_3`, `G_Nj_MAT_8`, and `G_Nj_MAT_33` high for $T_{\text{charge}}$, charging the `W-` storage capacitors.
   - **Center Compensation Weights (`w = 0`):** Setting a weight to zero charges both `W+` and `W-` to `128` (`1.65V`).

#### B. Hardware-Locked Hadamard & ADC Acquisition (`Ref 20, 24`) — Preventing "Earthquake" Switching Noise

> [!CAUTION]
> **CRITICAL ANALOG SIGNAL-INTEGRITY RULE (STRICT NON-OVERLAPPING SETTLE-THEN-SAMPLE SEQUENCE):**
> Digital bus shifting and Hadamard pin transitions generate ground bounce, capacitive coupling spikes, and op-amp transient ringing ("earthquake noise"). If the ADCs sample while the H-bus is shifting or before the analog matrix has fully settled to a steady DC level, the Hadamard correlation will be corrupted by switching transients.
>
> **Every single Hadamard table step MUST execute in the following strict, non-overlapping 4-phase sequence:**
> 1. **Phase 1 — Shift & Latch Hadamard Word (`T120 -> T20`):**
>    - T120 shifts the 16-bit Hadamard word (`vec[15] = 0`) over the H-bus (`H_SYNC` + `H_DATA`) into T20's shift register.
>    - On the final bit edge (`R(S+15)`), T20 latches the complete vector simultaneously onto the differential Hadamard output pins (`H_M3_P/N` or `H_M8_P/N`) with `OE = 1`.
> 2. **Phase 2 — Quiet Analog DC Settling Window ($\approx 2.0\,\mu\text{s}$ at default `500 kHz`, scaling up to $20.0\,\mu\text{s}$ at `50 kHz`):**
>    - Immediately after T20 latches the Hadamard pins, **all digital buses (`H_DATA`, `S_TX/RX`, `DAC_SCK`, `ADC_SCK`) MUST remain completely quiet (static)** while the analog crosspoint matrix (`2T1C` cells, `MCP6024T` differential TIAs, and Sigmoid stages `4` & `10`) settles into a clean, steady **DC state** over the full settling time ($\approx 2\,\mu\text{s}$ at `500 kHz`).
>    - During this window, the `XC2361A` ADCs are in **Track (Acquire)** mode, tracking the settling analog column voltages.
> 3. **Phase 3 — ADC Sample-and-Hold & Readout to T120 (At the END of the $\approx 2\,\mu\text{s}$ Settling Window):**
>    - Right at the **end** of the $\approx 2\,\mu\text{s}$ quiet DC settling window—when the analog signal is completely flat and settled—T120 asserts `ADC_45_CONV` and `ADC_49_CONV`.
>    - This immediately locks the `XC2361A` internal Sample-and-Hold (S/H) capacitors on all 12 channels simultaneously, capturing the noise-free DC value.
>    - T120 then clocks `ADC_45_SCK_*` and `ADC_49_SCK_*` to shift the digitized 12-bit ADC words out of the ADCs, subtracts the differential mid-scale offset `2048` (`signed_val = raw_12b - 2048`), and stores them into T120 RAM.
> 4. **Phase 4 — Advance to Next Hadamard Table State (ONLY After ADC Read Completes) & 3-State Exit:**
>    - **Only AFTER** the ADC Sample-and-Hold conversion and serial readout into T120 are 100% finished does the hardware interlock release `t120_hbus_seq` to shift the next Hadamard state in the table!
>    - **Leaving the Hadamard Table (`Step 16`):** Immediately after the 16th state (`Step 15`) finishes its ADC readout, T120 shifts a 17th trailing word `16'h8000` (`vec[15] = 1`), which causes T20 to deassert `H_M3_OE = 0` and `H_M8_OE = 0` (`Hi-Z`), returning all Hadamard pins to the floating analog center (`1.65V`) so the permutation is 100% centered.

```
Single Hadamard State Timeline (Repeated for each row 0..15 of the Hadamard table, followed by trailing 16'h8000 Hi-Z word):

H_SYNC/H_DATA : [1. Shift 16b Word]__________________________________________________________[Next Word / 16'h8000 Hi-Z
T20 H_M3/M8   : XXXXXXXXXXXXXXXXXXX[======== 2. Steady Hadamard State (OE=1, +/-) ========]XX[Hi-Z (OE=0, Centered)]
Analog Matrix : ~~~~~\ringing/~~~~~\____________________Settled DC State______________________/~~~~~~~~~~~~~~~~~~~~~~~
ADC S/H Mode  : [      Track / Acquire Analog Output       ][3. HOLD & Convert][Shift to T120]
ADC_CONV      : ____________________________________________/‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾\______________________________________
ADC_SCK       : _______________________________________________________________/‾\__/‾\__/‾\__________________________
                |<-- Shift/Latch ->|<---- ~2 us Quiet Analog DC Settling ----->|<-- Read ADC ->|<-- Next / Leave Table
```

During each short measurement window (`Ref 20, 24`):
1. **Two-Phase Isolated Sweep (`16` states + `1` trailing `Hi-Z` word per sub-window):**
   - **Sub-Window A — Perturb $M_8$ Only ($M_3$ in `Hi-Z`):** T20 `en_mask` is set to `16'h7F00` (so `H_M3_OE = 0` `Hi-Z` centered, `H_M8_OE = 1` active during the table). T120 steps through the 16 permuted Hadamard states (`0..15`) followed by trailing word `16` (`16'h8000` $\to$ all `OE = 0` `Hi-Z`). Every active state `0..15` follows the hardware-interlocked **Shift $\to$ `~2 µs` Quiet DC Settle $\to$ ADC Sample-and-Hold & Readout $\to$ Next State** sequence.
   - **Sub-Window B — Perturb $M_3$ Only ($M_8$ in `Hi-Z`):** T20 `en_mask` is set to `16'h00FF` (so `H_M8_OE = 0` `Hi-Z` centered, `H_M3_OE = 1` active during the table). T120 steps through the 16 permuted Hadamard states (`0..15`) followed by trailing word `16` (`16'h8000` $\to$ all `OE = 0` `Hi-Z`), again obeying the strict **Settle $\to$ ADC Sample-and-Hold & Store $\to$ Next State** sequence.
2. **Hadamard Frequency Scaling (`500 kHz` Default down to `50 kHz`):**
   - Controlled by GUI slider `f_hadamard_khz` $\in [50, 500]\text{ kHz}$ (governing the quiet DC settling time $T_{\text{settle}} \in [2.0\,\mu\text{s}, 20.0\,\mu\text{s}]$ per Hadamard state).
   - **Proportional Refresh Period Scaling:** When $T_{\text{settle}}$ is increased by factor $\kappa = T_{\text{settle}} / 2.0\,\mu\text{s} \in [1.0, 10.0]$, the measurement window duration $T_{\text{meas}}$ and the entire refresh cycle period $T_{\text{INF}}$ scale proportionally by $\kappa$ ($T_{\text{INF}} = T_{\text{INF, base}} \cdot \kappa$) so the number of discrete measurement slots $M$ per refresh period remains invariant.

---

### 2.3 Two-Level Randomization & White-Noise Reference Pattern Locking

#### A. Strict White-Noise Reference Input Pattern Rule (`Ref 1`)
> [!IMPORTANT]
> **MANDATORY INPUT DATA RULE:**
> 1. The reference input data vector $\mathbf{x}_{\text{ref}} \in [0, 255]^6$ (`DAC_2`) is generated inside T120 as **100% uncorrelated White Noise** (via a deterministic 32-bit Xorshift/PCG PRNG so the ideal digital target $\mathbf{Z}_{\text{target}} = M_{33}^{\text{ideal}} \mathbf{x}_{\text{ref}}$ is known exactly).
> 2. **Full-Cycle Pattern Locking:** The **EXACT SAME white-noise reference pattern $\mathbf{x}_{\text{ref}}$ MUST be held constant across the ENTIRE refresh time cycle (and across all consecutive refresh cycles required to sample every time slot between refreshes)** until a 100% complete temporal map of how the analog matrix warps/decays over the refresh cycle is obtained.
> 3. **Pattern Advance Condition:** Only **after** all time slots $P[0 \dots M-1]$ across the refresh period have been measured for the current $\mathbf{x}_{\text{ref}}$ (and the resulting full-cycle delta has been passed to the neural network weight update) may T120 generate and latch the next random white-noise reference pattern!

#### B. Inner & Outer Randomization (`FPGA_code/docs/hadamard_table_colum_randomizer.md`)
1. **Inner Randomization (Column Permutation before FWHT):**
   - Before each measurement window, T120 generates a random permutation $\pi$ of the active Hadamard rows (`1..15`) and loads the permuted words into `t120_hbus_seq` BRAM (`0xC00..0xFFF`).
   - As `ADC_45` and `ADC_49` samples arrive during the 16-step sweep, T120 performs a **reverse scatter-write** (`buf[pi_inv[t]] = adc_sample`) into data RAM, restoring natural Walsh-Hadamard order at zero extra cycle cost before executing the 4-stage radix-2 Fast Walsh-Hadamard Transform (`FWHT-16`).
2. **Outer Randomization (Single Measurement Window per Time Slot Initial Mode):**
   - Let the refresh period $T_{\text{INF}}$ be partitioned into $M$ contiguous time slots of length $T_{\text{meas}}$: $t_m = T_{\text{refresh\_pulse}} + m \cdot T_{\text{meas}}$ for $m \in \{0, 1, \dots, M-1\}$.
   - T120 maintains a slot index array `P[0 .. M-1]` and shuffles it via the **Fisher-Yates algorithm** at the start of each full temporal scan.
   - **Initial Operational Mode (1 Window per Refresh Cycle):**
     - On refresh cycle $k \in \{0 \dots M-1\}$ (while keeping $\mathbf{x}_{\text{ref}}$ locked!), the hardware waits until time slot $P[k]$ after the refresh pulse, executes **one** short Hadamard measurement window (`Sub-Window A + Sub-Window B`), and records the local gradient $\nabla L(t_{P[k]})$.
     - After $M$ refresh cycles, every single time point $0 \dots M-1$ between refresh pulses has been covered without any systematic temporal bias or self-heating artifact from the Hadamard pulses themselves.
     - The $M$ slot gradients are integrated ($\Delta \mathbf{W} = \frac{1}{M}\sum_{m=0}^{M-1} \nabla L(t_m)$) and sent as the delta update to the neural network weights ($M_3, M_8$).

#### C. Duty Cycle Governance: Base Model Training (`Ref 40/41`) vs. Operational Mode (`Ref 42`)
| Operating Mode | Patent Ref | Measurement Window Duty Cycle | Behavior Between Refresh Pulses |
|:---|:---|:---|:---|
| **Base Model Training** | `Ref 40` (Outer) & `Ref 41` (Inner) | **100% of interval between refresh pulses** | Short measurement windows are executed **back-to-back** across all $M$ slots within a single refresh cycle (or up to the 100% duty limit), because no external user inference payload is running. Maximizes training speed while preserving short window physics. |
| **Operational Inference Mode** | `Ref 42` | **Capped by GUI Slider `MAX_MEAS_DUTY_%`** (e.g., `1%` to `25%`, default `1 window / refresh`) | At least `100% - MAX_MEAS_DUTY_%` of every refresh cycle is dedicated to unperturbed 500 kHz+ payload inference (`Ref 19`). Measurement windows are interleaved at Fisher-Yates randomized slots $P[k]$ within the allowed duty budget. |

---

### 2.4 Embedded MAML Engine (`Ref 40`, `Ref 41`) & Hardware Hidden Offset Emulator

The T120 Sapphire RISC-V SoC firmware (`FPGA_code/sw/t120_master/`) implements the complete fixed-point (`Q1.14` / `Q8.14`) and/or soft-float MAML engine following [`NON_BACKPROP_HADAMARD_GRADIENT_RULES.md`](./NON_BACKPROP_HADAMARD_GRADIENT_RULES.md):

1. **Forward Hadamard Gradient Step (`Equations 1–7`):**
   - Computes $Er_j^{(49)} = Z_{\text{target}, j} - Z_{\text{out}, j}^{(49)}$ (`Eq. 1`).
   - Computes $\nabla W_{i,j}^{(8)} = \langle \partial z_j^{(49)} / \partial V_i^{\text{PTU}} \rangle_{\text{Hadamard}} \cdot Er_j^{(49)}$ (`Eq. 2` — **NO multiplication by $x_i^{(8)}$**).
   - Finds carrier row $k = \arg\max_i |x_i^{(8)}|$ from `ADC_45` (`Eq. 5`) and computes column slope $\sigma_2'(y_j^{(8)})$ via regularized inverse scaling (`Eq. 6`, or sets $\sigma_2' = 1.0$ if Jumper Mode = `2. Bypass Second Sigmoid`).
   - Computes row sensitivity receipt $\partial x_i^{(8)}$ (`Eq. 4`) and Layer 1 gradient $\nabla W_{i,j}^{(3)} = \langle \partial z_j^{(45)} / \partial V_i^{\text{PTU}} \rangle_{\text{Hadamard}} \cdot \partial x_j^{(8)}$ (`Eq. 7` — **NO multiplication by $x_i^{(3)}$**).
2. **Hardware Hidden Offset Emulator (Active ONLY in `Ref 40/41` Base Model Training):**
   - To train the Base Model (`Ref 40`) to be resilient against physical hardware drift before or alongside thermal heating, the T120 DAC driver supports injecting synthetic **Hidden Offsets** unknown to the inner loop (`Ref 41`):
     - **Included Offset #1 — Compensation Weight ($W$) Hidden Offset:** When the inner loop requests writing digital weight $W_{i,j}$ to $M_3$ (`W_15`) or $M_8$ (`W_12`), the hardware driver actually writes $\text{clamp}(W_{i,j} + \Delta W_{i,j}^{\text{hidden}}, 0, 255)$, where $\Delta W_{i,j}^{\text{hidden}}$ is sampled per outer-loop task $\mathcal{T}_k$.
     - **Included Offset #2 — Power Trim (`trim-DAC`, `Ref 38`) Hidden Offset:** Shifts the global matrix supply/bias trim DAC channel on bank `W_34` by $\Delta V_{\text{trim}, k}^{\text{hidden}}$, warping the analog operating point of all cells simultaneously.
     - **Explicitly Excluded in Phase 1:** Do **NOT** inject hidden offsets on Input `DAC_2` (`Ref 2`) or on `ADC_45`/`ADC_49` (`Ref 45, 49`). Keep those zeroed in Phase 1 to ensure clean observability.
   - **Zeroing in Operational Mode (`Ref 42`):** When switched to Operational Mode (`Ref 42`), all synthetic hidden offsets ($\Delta \mathbf{W}^{\text{hidden}}$ and $\Delta V_{\text{trim}}^{\text{hidden}}$) are immediately set to **zero/center**, and the system adapts purely to the real physical analog hardware and heater-induced thermal drift.
3. **Inner Loop (`Ref 41`) & Dot-Product Second-Derivative Outer Loop (`Ref 40`):**
   - **Inner Loop (`Ref 41`):** Runs $N_{\text{inner}}$ adaptation iterations (default **`100`**, adjustable via GUI slider) from base weights $\mathbf{W}_0$, recording initial gradient $\mathbf{g}_1$, trajectory snapshots, final adapted basin weights $\mathbf{W}_k^{(N)}$, and final gradient $\mathbf{g}_N$.
   - **Outer Loop (`Ref 40`):** Updates $\mathbf{W}_0$ across a meta-batch of $K$ tasks (e.g., $K = 4\text{--}8$ hidden offset / thermal states) using the **$O(P)$ dot-product directional second-derivative update** (see Section 4 of `NON_BACKPROP_HADAMARD_GRADIENT_RULES.md`), streaming the basin coordinates and gradient dot-product alignment metrics to the PC GUI over UDP.

---

### 2.5 Ethernet Control, Telemetry & Diagnostic Protocol (`192.168.1.50:5000`)

Extend the existing UDP command handler on T120 (`FPGA_code/sw/t120_master/src/main.c`) with structured binary/JSON-friendly command & telemetry packets over UDP port `5000`:

| Packet Type / Opcode | Direction | Payload & Function |
|:---|:---|:---|
| `0x01 CMD_PING / HEARTBEAT` | PC $\leftrightarrow$ T120 | Keeps Heater Watchdog alive; returns T120 + T20 status, `TAG=T20A`, uptime, and link counters. |
| `0x10 CMD_HEATER_CTRL` | PC $\to$ T120 $\to$ T20 | `{armed_bool, pwm_duty[4]}`: Sets master `HEATER_ARMED` interlock and 8-bit `0.2 Hz` PWM duty cycles for `HEAT_1..4_EN`. |
| `0x11 CMD_LED_JUMPER_CFG` | PC $\to$ T120 $\to$ T20 | `{comp_led_on, mat33_led_on, jumper_mode[1:0]}`: Controls `COMP_LED_ON`, `MAT33_LED_ON` on T20 and informs firmware of physical jumper setting (`1=OFF`, `2=Bypass Sigmoid 2`, `3=Use Sigmoid 2`). |
| `0x20 CMD_DAC_DIAG_MODE` | PC $\to$ T120 | `{mode, bank, channel, static_val}`:<br>• `mode=0`: Normal MAML operation<br>• `mode=1`: **10 Hz Oscilloscope 3-State Toggle (`255 -> 128 -> 0`)** on all DACs<br>• `mode=2`: **Single-DAC Manual Static Override** (`bank`, `ch` set to `static_val`). |
| `0x21 CMD_CENTER_WEIGHTS` | PC $\to$ T120 | Immediately sets all compensation weights ($M_3$ `W_15` and $M_8$ `W_12`) to center (`128`) to measure uncompensated baseline bit-precision. |
| `0x22 CMD_CELL_SWEEP_STEP` | PC $\leftrightarrow$ T120 | Used by PC Automated Cell-by-Cell Self-Test: sets a single intersection $(m, i, j)$ to a requested test weight & row input, triggers refresh + ADC read, and returns raw `ADC_45[1..6]` and `ADC_49[1..6]`. |
| `0x30 CMD_TIMING_MAML_CFG` | PC $\to$ T120 | `{hadamard_khz (50..500), max_duty_pct (0..100), op_mode (40/41 vs 42), inner_loops_N (1..500), lr_inner, lr_outer, seed_mode, seed_swing_pct, w_offset_amp, trim_offset_amp}`. |
| `0x80 TELEM_STREAM_FRAME` | T120 $\to$ PC | Streamed after every refresh cycle / inner step: `{cycle_id, outer_step, inner_step, mode, loss_total, bit_precision_active, bit_precision_centered, adc45[6], adc49[6], target[6], W_M3[8][6], W_M8[7][6], grad_M3_norm, grad_M8_norm, dot_product_alignment, ref_clock_decay}`. |

---

## 3. Track 2 — English PC Graphical User Interface (GUI) & 3D Loss Landscape Visualizer

**Language & Stack Recommendation:** All GUI text, labels, tooltips, and plots **MUST be in English**. Implement in Python (`PyQt6` / `PySide6` + `pyqtgraph.opengl` / `VisPy` / `Matplotlib` for 60 FPS real-time 3D surface & heatmap rendering) inside a dedicated `gui/` directory.

### 3.1 Main GUI Layout Overview

```
+--------------------------------------------------------------------------------------------------+
|  INVERTED MAML AIMC PLATFORM — T120 (192.168.1.50) [CONNECTED] | T20 [T20A ACTIVE] | Jumper: [3] |
+-----------------------------------+-----------------------------------+--------------------------+
| 1. THERMAL & SAFETY CONTROL       | 2. REAL-TIME METRICS & PRECISION  | 3. 3D MAML LOSS BASINS   |
|  [ ] MASTER ARM HEATER SWITCH     |  Effective Precision:  6.42 bits  |   (Mini Live Viewport)   |
|  (●) WARNING: HEATER ARMED / HOT! |  Centered Baseline:    2.15 bits  |    \  v1   --> ● <-- v2  |
|  Heater 1 (0.2Hz): [====----] 45% |  MAML Gain:           +4.27 bits  |     \_____/W0\_____/     |
|  Heater 2 (0.2Hz): [==------] 20% |  Total Loss (Eq.1):    1.8e-4     |  Dot-Prod Pull: +0.87    |
|  Heater 3 (0.2Hz): [--------]  0% |  [Center Comp. Weights (128)]     |  [ 🔍 Open 3D Pop-Up ]   |
|  Heater 4 (0.2Hz): [======--] 75% |  [Run Auto Bit-Precision Test]    |                          |
+-----------------------------------+-----------------------------------+--------------------------+
| 4. TIMING, DUTY CYCLE & MAML HYPERPARAMETERS                          | 5. HARDWARE DIAGNOSTICS  |
|  Operating Mode: (•) Base Model Train (Ref 40/41, 100% Duty)          |  Analog Jumper Position: |
|                  ( ) Operational Inference (Ref 42, Capped Duty)      |   ( ) 1. OFF (No Comp)   |
|  Max Meas. Window Duty (Ref 42): [===-------] 10% (1 win/refresh)     |   ( ) 2. Bypass Sigmoid2 |
|  Hadamard Pulse Speed:           [=========] 500 kHz (2.0 us/word)    |   (•) 3. Use Sigmoid 2   |
|    -> Scaled Refresh Period:     10.0 ms (scales 1x..10x down to 50k) |  Analog Column LEDs:     |
|  Inner Loop Steps (Ref 41):      [====------] N = 100 / outer step    |   [x] COMP_LED_ON        |
|  Seed Randomization (% DAC):     [===-------] 15%  [Auto Seed (Gain)] |   [x] MAT33_LED_ON       |
|  Seed Mode: [Standard Gaussian v] [QR Orthogonal] [Zero-Sum Pair]     |  Oscilloscope DAC Test:  |
|  Hidden Offsets (Ref 40/41):     W-Offset: 10% | Trim-38 Offset: 8%   |   [ 10Hz 255/128/0 All ] |
|  Ref Input White-Noise Lock:     [LOCKED: Slot 142 / 156]             |   Single DAC: [W_15 Ch3] |
|                                                                       |   Value: [128] [Set DAC] |
|                                                                       |  [Run Cell Self-Test]    |
+-----------------------------------------------------------------------+--------------------------+
| 6. BOTTOM DIAGNOSTIC TABS: [Bit Precision & Loss History] [Cell 6x6 Heatmaps] [Decay Stratum]    |
+--------------------------------------------------------------------------------------------------+
```

---

### 3.2 Pedagogical Real-Time 3D Loss Landscape & Basin-Gathering Visualizer (Mini-View + Pop-Up Window)

A centerpiece of the GUI is a **real-time 3D color heatmap / surface visualizer** that makes the high-dimensional Inverted MAML dynamics (`Ref 40` Outer Loop vs. `Ref 41` Inner Loop) immediately intuitive to a human observer.

#### A. How to Project 84-Dimensional Weight Space ($\mathbf{W} \in \mathbb{R}^{84}$) into a Meaningful 3D Surface
In each Outer Loop (`Ref 40`) cycle, the system evaluates $K$ different physical/emulated offset tasks $\mathcal{T}_1, \dots, \mathcal{T}_K$ (e.g., $K = 4\text{ to }6$ distinct $(W\text{-offset}, \text{Trim-38 offset})$ or thermal states). Starting from the current Base Model weight vector $\mathbf{W}_0$, each inner loop $k$ (`Ref 41`) runs $N$ steps (`default 100`) and settles into its own task-specific local minimum valley $\mathbf{W}_k^{(N)}$.

To visualize all $K$ local valleys simultaneously without dimensional collapse:
1. **Dynamic Orthonormal Plane $(\mathbf{e}_1, \mathbf{e}_2)$ Centered on $\mathbf{W}_0$:**
   - Place the current Base Model weight vector $\mathbf{W}_0$ (`Ref 40`) at the center $(0, 0)$ of the 2D horizontal plane.
   - Compute the displacement vectors $\mathbf{d}_k = \mathbf{W}_k^{(N)} - \mathbf{W}_0$ from the base model to each inner-loop minimum.
   - Extract the top 2 principal directions $(\mathbf{e}_1, \mathbf{e}_2)$ via fast SVD/PCA of $[\mathbf{d}_1, \dots, \mathbf{d}_K]$ (with exponential smoothing across frames so the camera frame never jumps abruptly).
   - Project each inner-loop trajectory step $\mathbf{W}_k^{(t)}$ onto 2D coordinates:
     $$u_{k,t} = \langle \mathbf{W}_k^{(t)} - \mathbf{W}_0, \, \mathbf{e}_1 \rangle, \qquad v_{k,t} = \langle \mathbf{W}_k^{(t)} - \mathbf{W}_0, \, \mathbf{e}_2 \rangle$$
2. **Constructing the Multi-Basin 3D Loss Surface $Z(u, v)$:**
   - Around each projected inner-loop minimum $(u_{k,N}, v_{k,N})$, fit a local quadratic/radial loss well matching the measured initial loss $L_k(\mathbf{W}_0)$, final valley loss $L_k(\mathbf{W}_k^{(N)})$, and directional curvature estimated from the Hadamard gradients:
     $$Z(u, v) = \min_{k \in \{1..K\}} \left( L_k\!\left(\mathbf{W}_k^{(N)}\right) + \frac{1}{2} \kappa_k \left[ (u - u_{k,N})^2 + (v - v_{k,N})^2 \right] \right)$$
   - Render $Z(u, v)$ as a **3D shaded terrain mesh + 2D floor contour heatmap** (deep blue/cyan = low-loss valleys/"gropar", yellow/red = high-loss ridges).
3. **Visualizing the Outer-Loop (`Ref 40`) Second-Derivative "Basin Gathering" Action:**
   - **Inner-Loop Trajectories (`Ref 41`):** Drawn as glowing comet trails descending from the central marker $\mathbf{W}_0$ into each of the $K$ surrounding valleys ("gropar").
   - **Outer-Loop Second-Derivative Pull Vectors (`Ref 40`):** Draw prominent 3D force arrows pointing from each outer valley minimum $(u_{k,N}, v_{k,N})$ inward toward the central base model $\mathbf{W}_0$, scaled by the measured second-derivative dot product $\langle \mathbf{g}_{1,k}, \mathbf{g}_{N,k} \rangle$.
   - **Pedagogical Effect Over Time:** Early in training, the user sees $K$ widely separated deep blue valleys ("gropar") far from the center, with long inner-loop trails. As the Inverted MAML Outer Loop (`Ref 40`) applies the second-derivative dot-product updates, **the user watches the separate valleys physically slide inward and merge ("knuffas samman") into a single shared super-basin in the center**, while the inner-loop adaptation distance $\|\mathbf{W}_k^{(N)} - \mathbf{W}_0\|$ shrinks!
4. **Dual-View Architecture (Embedded Mini-Widget + Detachable Pop-Up Window):**
   - **Main GUI Mini-Widget:** Always visible in the top-right panel of the main window (`~320×260 px`), showing the top-down/isometric 3D heatmap and basin convergence metric.
   - **Expandable Pop-Up Window (`"Open 3D Landscape Inspector"`):** Clicking the expand button opens a large, independent, resizable window (`1280×800+`) containing:
     - Full interactive 3D surface mesh (rotate, pan, zoom, toggle wireframe/contours).
     - **1D Cross-Section Slice Plot:** Shows loss $L$ vs. distance along the line connecting Valley $k$ and $\mathbf{W}_0$, clearly displaying how the curvature (second derivative) is flattened/centered.
     - **Basin Dispersion Gauge:** Plots average distance $\frac{1}{K}\sum_k \|\mathbf{W}_k^{(N)} - \mathbf{W}_0\|_2$ and Cosine Alignment $\frac{\langle \mathbf{g}_1, \mathbf{g}_N \rangle}{\|\mathbf{g}_1\|\|\mathbf{g}_N\|}$ over outer-loop epochs.

---

### 3.3 Detailed Specification of GUI Controls & Self-Test Diagnostics

1. **Heater Arm & Thermal Warp Control Panel:**
   - **Master Arm Switch (`ARM HEATER`):** Hardware/software safety lock. When `OFF` (default), the 4 heater sliders are disabled and T20 forces `HEAT_1..4_EN = 0`.
   - **Hot-Board Warning Lamp:** When `ARM HEATER` is switched `ON`, a high-contrast red/orange warning indicator lights up: **`"WARNING: HEATER ARMED — BOARD CAN BECOME HOT"`**.
   - **4 Channel PWM Controls (`0.2 Hz`):** Individual `0–100%` duty sliders for Heaters `1..4`, plus thermal warp presets.
2. **Oscilloscope DAC Diagnostic Mode (`10 Hz` 3-State Toggle + Single-DAC Override):**
   - **`10 Hz Full-Swing Oscilloscope Mode` Button:** Toggles all 30 DAC channels (`DAC_2`, `W_15`, `W_12`, `W_34`) synchronously between **`255` (Max) $\to$ `128` (Mid/Center) $\to$ `0` (Min)** at `10 Hz` so the engineer can attach an oscilloscope probe to any DAC pin or cell gate and immediately verify full analog voltage swing, linearity, and RC settling.
   - **Manual Static Single-DAC Override:** Allows selecting any specific DAC bank (`DAC_2`, `W_15`, `W_12`, `W_34`) and channel (`1..8`) and writing a fixed code (`0..255`).
3. **Manual Analog Column LED Array Switches:**
   - Dedicated toggle buttons for **`COMP_LED_ON`** (enables the LED array on the compensation column outputs) and **`MAT33_LED_ON`** (enables the LED array on the primary payload matrix column outputs).
4. **Physical Analog Jumper Selector (3-State Control):**
   - Matches the physical jumper configuration placed by the user on the PCB:
     1. **`1. OFF (No Compensation)`**
     2. **`2. Bypass Second Sigmoid (Linear Layer 2 Output)`**
     3. **`3. Use Second Sigmoid Layer (Full Dual-Sigmoid Compensation)`**
   - Selecting the jumper mode updates the gradient engine (e.g., locking $\sigma_2'(y_j^{(8)}) = 1.0$ in Mode 2 vs. active Carrier Wave Equation 6 in Mode 3) and logs the jumper state in all saved test reports.
5. **Automated Cell-by-Cell Self-Diagnosis (Computed on PC):**
   - Triggered by the **`Run Cell-by-Cell Self-Test`** button in the GUI.
   - **Execution Flow (PC-Driven):**
     - The PC commands T120 (`CMD_CELL_SWEEP_STEP`) to center all inactive cells (`128`) and steps through every individual cell intersection $(i, j)$ in $M_{33}$ (`6×6`), $M_3$ (`8×6`), and $M_8$ (`7×6`).
     - For each cell $(i, j)$, the PC sweeps the cell's weight DAC code $W_{i,j} \in \{0, 64, 128, 192, 255\}$ at low and high row input $x_i \in \{0, 255\}$, reading back `ADC_45` and `ADC_49`.
     - **PC Analysis & Visualization:** All linear regression, transconductance slope ($g_m$), threshold offset ($V_{\text{th}}$), and RC droop calculations are performed on the **PC** (keeping embedded firmware lightweight). Displays three `6×6` / `8×6` **2D Cell Health Heatmaps** (`Gain % of Nominal`, `Zero Offset`, `RC Decay Time Constant`) with PASS/WARN/FAIL badges per cell.
6. **"Center Compensation Weights" Button & Automated Bit-Precision Benchmark:**
   - **Manual Button (`Center Compensation Weights`):** Forces all weights in $M_3$ (`W_15`) and $M_8$ (`W_12`) to center (`128`), allowing the user to watch the live **Bit-Precision Meter** drop in real time when compensation is removed, and jump back up when MAML adaptation resumes.
   - **Automated Bit-Precision Test:** Automatically measures output error against the reference white-noise pattern first with **Compensation Centered (`128`)** and then with **Active MAML Compensation**, displaying both bit accuracies and the net **MAML Precision Gain (`+Δ bits`)**.
7. **Timing, Loop & Seed Randomization Sliders:**
   - **Max Measurement Window Duty Cycle (`%` of Refresh Period):** `0%–25%` slider for Operational Mode (`Ref 42`); displays `100% (Locked)` during Base Model Training (`Ref 40/41`).
   - **Hadamard Pulse Frequency Slider:** **`500 kHz` (`2 µs`/word, Default)** down to **`50 kHz` (`20 µs`/word)**, automatically scaling the refresh period $T_{\text{INF}}$ proportionally (`1×` to `10×`).
   - **Inner Loop Iterations (`Ref 41`) per Outer Loop (`Ref 40`):** Slider/spinbox from `1` to `500` (**Default = `100`**).
   - **Seed Randomization Suite:**
     - **Seed Swing `%` Slider:** Sets randomization amplitude as `%` of full DAC range (`0..255`) around `128`.
     - **`Auto Seed (Standard Gain)` Button:** Automatically computes the optimal seed amplitude (`±15%` of full scale, scaled by $1/\sqrt{N_{\text{rows}}}$ and the measured cell gain from the self-test) so Layer 1 Sigmoid `4` operates in its maximum-SNR slope region ($\pm 0.9$).
     - **Additional Seed Modes:**
       1. `Uniform / Gaussian White Seed`
       2. `QR Orthogonal Row/Col Seed` (prevents initial column redundancy)
       3. `Zero-Sum Complementary Seed` (initializes $M_3, M_8$ with rich internal variance while keeping initial net output correction near zero)
       4. `Save / Load Golden Seed` (stores best-converging seed vectors to disk).

---

## 4. Phased Implementation Roadmap for Coding Agents

### Phase 1: T120 & T20 Hardware Peripheral Drivers (RTL + C Firmware)
- [ ] **Step 1.1 (T120 Pin Direction Fix & DAC Driver):** Fix the 6 `input` DAC pins in `FPGA_code/T120F324/T120_MALM.peri.xml` and `top_level.sv` to `output`. Implement `t120_dac_ctrl.sv` to shift all 4 `74HC595` banks (`DAC_2`, `W_15`, `W_12`, `W_34`) in parallel (`8` clock cycles per load) + hardware `10 Hz` `255 -> 128 -> 0` oscilloscope test generator.
- [ ] **Step 1.2 (T120 Dual-Bank ADC Driver):** Implement `t120_adc_ctrl.sv` to trigger `ADC_45_CONV` and `ADC_49_CONV` (`XC2361A` × 12 channels) synchronized to `h_step_strobe` and read all 12 serial `SDO` lines into APB-accessible sample RAM.
- [ ] **Step 1.3 (T20 Column Gates, 0.2 Hz Heater PWM & LED Switches):** Extend `FPGA_code/T20_Custom/top_level.sv` and `t20_hw_responder.sv` with S-bus registers for:
  - `HEAT_1..4_EN` driven by a `0.2 Hz` PWM counter (`CLK_50MHZ / 250,000,000`) gated by `heater_armed` and a `3.0 s` S-bus watchdog timer.
  - `COMP_LED_ON` and `MAT33_LED_ON` GPIO outputs.
  - Column refresh gate sequencer (`G_1..6_MAT_3`, `G_1..6_MAT_8`, `G_1..6_MAT_33`) synchronized via H-bus/S-bus refresh trigger.

### Phase 2: Synchronized Hadamard Scheduler, Randomizer & Non-Backprop MAML Firmware
- [ ] **Step 2.1 (Two-Level Randomizer & White-Noise Reference Lock):** Implement the inner Hadamard row permutation + reverse scatter-write (`FWHT-16`) and the outer Fisher-Yates slot randomizer $P[0 \dots M-1]$ on T120, enforcing the rule that the **100% white-noise reference vector $\mathbf{x}_{\text{ref}}$ stays locked across all refresh cycles required to map 100% of the refresh decay period**.
- [ ] **Step 2.2 (Non-Backprop Gradient Engine — Equations 1–7):** Implement the isolated two-sub-window Hadamard sweep ($M_8$ perturbed first while $M_3$ is quiet; then $M_3$ perturbed while $M_8$ is quiet), Carrier Wave Search (`Eq. 5`), Regularized Inverse Scaling (`Eq. 6`), Row Receipt (`Eq. 4`), and direct Hadamard weight gradients (`Eq. 2` & `Eq. 7`) strictly following `NON_BACKPROP_HADAMARD_GRADIENT_RULES.md`.
- [ ] **Step 2.3 (Embedded Inner/Outer Loop & Hidden Offset Emulator):** Implement Inner Loop (`Ref 41`, default $N=100$), Dot-Product Second-Derivative Outer Loop (`Ref 40`), and the $W$-offset + `trim-DAC 38` hidden offset emulator (active in `Ref 40/41`, zeroed in `Ref 42`).

### Phase 3: English PC GUI, 3D Loss Landscape Visualizer & PC Self-Diagnostics
- [ ] **Step 3.1 (Main GUI Dashboard & UDP Telemetry Client):** Build the English PyQt6 GUI (`gui/main_window.py`) communicating with `192.168.1.50:5000`, including the Heater Arm interlock & warning lamp, 10 Hz oscilloscope DAC toggle, single-DAC override, LED toggles, 3-state Jumper selector, and all timing/MAML/seed sliders.
- [ ] **Step 3.2 (Real-Time 3D Loss Landscape Mini-Widget & Pop-Up Window):** Implement `gui/loss_landscape_3d.py` featuring PCA/anchor projection of the $K$ inner-loop basins (`Ref 41`) around $\mathbf{W}_0$ (`Ref 40`), animated second-derivative inward pull vectors, embedded mini-viewport, and detachable full-screen 3D inspector window.
- [ ] **Step 3.3 (PC-Computed Cell-by-Cell Self-Diagnosis & Auto Bit-Precision Benchmark):** Implement `gui/diagnostics_engine.py` to sweep all crosspoint cells, render `6×6`/`8×6` transconductance & decay heatmaps, and run automated bit-precision comparisons (`Centered 128` vs. `MAML Active`).

---

## 5. Future Phase — PC Digital Twin for Thermal Spread Estimation (`20°C–45°C`)

> [!NOTE]
> **Future Roadmap Extension (Phase 4 — Do Not Block Phase 1–3 On This):**
> Physical thermal warping via `HEAT_1..4_EN` (`0.2 Hz` PWM) has a thermal time constant of several seconds to minutes. However, during Base Model Outer-Loop Training (`Ref 40`), it is desirable to jump between different thermal states on **every training sample / outer-loop step** (millisecond timescale).
>
> **Planned Architecture:**
> 1. **Calibration Sweep (`20°C` to `45°C` + `3.3V` Rail Variations):** Using the Automated Cell-by-Cell Self-Test while slowly ramping `HEAT_1..4_EN` across spatial heater combinations (representing ambient temperatures from `20°C` to `45°C` and supply voltage droop on the `3.3V` rail), record a dataset of physical cell-by-cell effective weight shifts $\Delta \mathbf{W}_{\text{physical}}(T_1, T_2, T_3, T_4, V_{DD})$ and `trim-DAC 38` shifts.
> 2. **PC Neural Thermal Twin:** Train a lightweight surrogate neural network on the PC that maps any virtual thermal/supply state vector $(\theta_{\text{temp}} \in [20^\circ\text{C}, 45^\circ\text{C}]^4, \Delta V_{3.3\text{V}})$ to realistic, spatially correlated hidden-offset tensors $(\Delta \mathbf{W}^{\text{hidden}}, \Delta V_{\text{trim}}^{\text{hidden}})$.
> 3. **High-Speed Sample-by-Sample Thermal Emulation:** Upload the calibrated covariance/basis table from the PC Thermal Twin to T120 so the embedded Outer Loop (`Ref 40`) can synthesize physically exact `20°C–45°C` thermal warp distributions instantaneously on every inner-loop task $\mathcal{T}_k$!

