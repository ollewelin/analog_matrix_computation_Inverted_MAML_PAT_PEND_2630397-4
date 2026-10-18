# Analog Matrix Multiplication with Proprioception
### Patent pending: document inverterad MAML_12_Eng.pdf translated
`inverterad MAML_12_Eng.pdf`
![](Fig1.png)

#### PATENT APP NO: SE 2630397-4
#### STATUS: PATENT PENDING
#### INVENTOR: OLLE WELIN
#### PRIORITY DATE: 2026-06-03
## Analog 2T1C Matrix with Inverted Meta-Learning (MAML)

## Youtube Video Audio:
https://youtu.be/LbWriQ0J6QY?si=GyIZ1UnNZuVdLi54

### Project Vision: Redefining Efficient Inference

The primary goal of this project is to drastically reduce power consumption for Neural Network inference. By moving away from energy-intensive digital data movement and leveraging In-Memory Computing (IMC), my aim to overcome the traditional "memory wall."

My approach combines analog matrix hardware with a novel Inverted Meta-Learning (MAML) algorithm. Instead of adapting to external input data, my system uses intrinsic meta-learning to dynamically calibrate and compensate for hardware non-idealities—such as thermal drift, component aging, and voltage leakage—in real-time during ongoing operations.

### The Adventure of Discovery
Working with analog computing is an act of balancing physics and precision. Very funny and exciting project!

### Project Status & Development Timeline

- **2026-06-10:** Initial concept and planning. Nothing tested on hardware yet (minimal SPICE simulations in June 2026). Plan outlined to build a 3x 6x6 analog matrix PCB with 500 kHz throughput, 8-bit R-2R DACs, 10-bit SAR ADCs, an Efinix Trion FPGA, and N-channel MOSFETs.
- **2026-10-15 (Disclaimer & Cleanup):** Removed simulated / hallucinated data that was generated between Oct 14–15 by the AI agent. All unverified AI simulation results were cleaned out.
- **2026-10-16:** Back on track — pure software simulations are now strictly banned. All focus shifts 100% to live bench measurements on the real physical PCB.
- **2026-10-17:** Started physical measurement of the real Hadamard carrier wave modulation on hardware. Neural network training has not started yet; priority is strictly on validating analog matrix derivative responses first.
- **2026-10-18:** In-depth bare-metal verification using an embedded Efinix Logic Analyzer directly on the FPGA. The project has moved past the "paper product" phase into real silicon physics on the scaled-up PCBA board, producing very interesting real-world data!


#### Disclaimer on Audiobooks: 
The earlier podcast generation:
`pod_inverted_maml_audiobook_96k.m4a`
states that this entire system has already been fully tested and run; at the time of its generation, that was not true (NotebookLM was summarizing the patent application without knowing the real bench status). 

However, as of October 2026, the first **real baby steps on physical silicon and PCBA hardware** have now begun (validating physical Hadamard carrier modulation, DAC/Weight line dynamics, and bare-metal ADC responses).

For a more accurate overview of the architecture and vision, check the updated 52-minute audio:
#### Recommended Audiobook (52 minutes):
`Shattering_the_Memory_Wall_with_Proprioception_56k.m4a`

This version gives a much fairer and more grounded representation of the project.  


### The Atomic Triad
![](Atomic_Triad.png)
### Mutiplication cell
![](Cell_Kernel.png)
### 6x6 matrix EasyEDA
![](6x6_matrix.png)
### LTspice simulation sigmoid OP-amp
![](LTspice_sigmoid_sim.png)
### The MATRIX ! Imagination or vision what if... "The self aware MATRIX" is possible ? :) 
![](EasyEDA/matrix.png)
![](EasyEDA/Matrix_PCB_view.png)
### Claude Simulation 3x6x6 PCB (NO hadamard included):
![](Simulation_Proof_of_concept_3x6x6_triad.png)

### JLCPCB manufacture placement 
T12F324 3D step is not showed here but mounted
![](EasyEDA/Component_Top.png)
![](EasyEDA/Component_bottom.png)

### Bringup test 1
IMPORTANT fix to get JTAG working.
1. CSI pull down need to remove both T20 (Remove R12$CBB23) and T120 (remove R169$CBB22/CBB2)
2. T120_CRESET_N patch wire between Reset circuit and T120 <--> FT2232 programmer to get auto start T120 from SIP flash
3. Bug fix 2026-09-30: missing input net T120_CRESET_N
4. 2026-10-07: Bug at Centertap 0-ohm to GND there should be 10nF to GND Eth Phy magnetics
![](LED_test1.jpeg)

### Regenerate FPGA code with AI agent example (one prompt)
Install the Efinix software tool locally on you computer
VS code and AI agent support
![](regerate_SoC_and_Ethernet_IP.png)

### Example timing report (125Mhz requirement passed)
![](Timing_report_T120_Soc_Eth.png)

### Hardware Bringup & Oscilloscope Discovery: DAC Data & Weight Op-Amp Current Drive Limitation

During physical bench bringup of the 3x 6x6 matrix PCB, direct oscilloscope probing on the **DAC Data row lines and Weight charging lines** (behind the `MCP6024T-I/SL` buffer op-amps) revealed that the **output current capability of the DAC Data and Weight buffer op-amps is too low** (whereas the column TIA stages are not the primary bottleneck):

![](Oscilloscope_OpAmp_Insufficient_Current_Drive_276mV.jpg)

#### Oscilloscope Observations:
- **R-2R DAC output before buffer:** Clean, stable DC output directly at the R-2R ladder.
- **DAC Data line & Weight line after op-amp buffer:** Periodic $\sim 250\text{--}276.6\text{ mV}_\text{pp}$ voltage swing repeating at $100\text{ Hz}$ ($10\text{ ms}$ period, $1.84\text{ V}$ peak).
- **Behavior as memory leaks out:** When the $100\text{ nF}$ 2T1C weight capacitors are charged, the matrix draws heavy current from the **DAC Data line** op-amp (which has to supply all active `DOX3134A` multiplier channels across the row in parallel across the 3 matrices) and the **Weight line** op-amp (which has to charge the $100\text{ nF}$ capacitors). Because the `MCP6024T-I/SL` cannot source enough current, its output voltage drops by $\sim 250\text{ mV}$. As the memory capacitors leak out over the $10\text{ ms}$ decay cycle, the load current drops and the op-amp output voltage rises back up by $250\text{ mV}$ to reach the R-2R DAC target level.

#### Physics Root Cause:
1. **Insufficient Output Current Drive on DAC Data & Weight Op-Amps (`MCP6024T-I/SL`):**
   - **DAC Data Row Buffers (`DAC(2)`):** A single DAC Data row buffer drives the drain paths of all connected matrix columns simultaneously (up to $3 \times 6 = 18$ cells across Matrix 3, Matrix 8, and Matrix 33). At high weight voltages, the combined channel current exceeds the linear sourcing capability of the `MCP6024`, causing a $250\text{ mV}$ sag until the gate capacitors discharge.
   - **Weight Charging Buffers (`W_M1(15)`, `W_M2(12)`, `W_A(34)`):** Charging the large $100\text{ nF}$ gate storage capacitors within the short refresh window demands high peak charging current ($I = C \cdot dV/dt$), which hits the current limit of the `MCP6024` buffer.
   - **Column TIAs:** Each column TIA only sinks the current of a single column into virtual ground ($1.65\text{ V}$), so the TIA is not the problem—the bottleneck is strictly on the **DAC Data and Weight buffer op-amps**.

> **Designer's Note on Prototype Board v1.3.2 Schematic Phase & Stiff Voltage-Source Driver Bottom Line (2026-10-18):**
> Looking back at the EasyEDA schematic design phase of the first prototype board (`v1.3.2`), I realized that I missed accounting for the fact that each Data line from `DAC(2)` actually has to drive the current for **both Matrix(3) and Matrix(33) simultaneously** in parallel. From my perspective, that was a design oversight—I sized the row buffer thinking of a 6-column driver load, whereas in reality I should have designed it for **at least 12 columns of simultaneous current drive capability** (plus Matrix 8 paths).
>
> **Bottom Line of Oscilloscope Findings:** The **copper traces on the PCB are completely fine**, and RF transmission-line "characteristic impedance" is not relevant for this slow-motion test PCB. What we actually need at **every DAC Weight driver output and every DAC Data driver output** is a **stiff voltage source with low output resistance ($R_\text{out}$) and high current-drive capability**—so the op-amp output stage can source both the steady-state 12-column load current and the transient `100 nF` refresh charging surges without voltage droop.

#### Pin-Compatible High-Current SOIC-14 Upgrade Options (for DAC Data & Weight Buffers):
The `MCP6024T-I/SL` uses the industry-standard **14-pin SOIC Quad Op-Amp pinout** (Pin 4 = $V_{DD}$ `+3.3V`, Pin 11 = $V_{SS}$ `GND`, Outputs on Pins 1, 7, 8, 14). Direct drop-in, pin-compatible replacements with much higher output current capability at $3.3\text{ V}$ for the DAC Data and Weight buffers include:

| Part Number | Manufacturer | Package | Output Current Capability | Bandwidth (GBW) | Supply Range | Key Advantage |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **MCP6024T-I/SL** *(Current)* | Microchip | SOIC-14 | Weak linear drive ($< 10\text{ mA}$ before drop) | $10\text{ MHz}$ | $2.5\text{V} - 5.5\text{V}$ | Drops $\sim 250\text{ mV}$ on DAC Data & Weight lines |
| **AD8534ARZ** | Analog Devices | SOIC-14 | **$\pm 250\text{ mA}$ per channel** | $3\text{ MHz}$ | $2.7\text{V} - 6.0\text{V}$ | Massive current drive, Rail-to-Rail I/O, built for heavy capacitive/resistive loads |
| **OPA4310IDR** | Texas Instruments | SOIC-14 | **$\pm 150\text{ mA}$ per channel** | $3\text{ MHz}$ | $1.5\text{V} - 5.5\text{V}$ | Very strong $3.3\text{ V}$ linear drive, Rail-to-Rail I/O, thermal protection |
| **OPA4354AIDR** | Texas Instruments | SOIC-14 | **$\pm 100\text{ mA}$ per channel** | $100\text{ MHz}$ | $2.5\text{V} - 5.5\text{V}$ | High current + high speed ($150\text{ V/\mu s}$), fast capacitor charging |
| **TS924IDT** | STMicroelectronics | SOIC-14 | **$\pm 80\text{ mA}$ per channel** | $4\text{ MHz}$ | $2.7\text{V} - 12\text{V}$ | Proven high-current Rail-to-Rail driver (drives down to $32\ \Omega$ loads without droop) |

### Corrected Hadamard Carrier Modulation: 24 µs Contiguous Burst at 2.0 ms Post-Refresh

Oscilloscope measurements initially revealed that the legacy Hadamard perturbation suffered from multi-hundred-microsecond pulse trains with unintended tri-state gaps between pulses. This distorted the measurement window across the analog memory capacitor decay curve.

The Hadamard sequence was rebuilt in both RTL (`t120_hbus_seq.sv`, `t120_inter_fpga_bridge.sv`, `t120_analog_io_ctrl.sv`) and C firmware (`maml_platform.c`):
1. **Contiguous 24.00 µs Table (2 x 6 = 12 pulses x 2.00 µs):** Zero tri-state gaps between pulses. 
   - 6 pulses for the (+) orthogonal Hadamard basis (12.00 µs).
   - 6 pulses for the complementary (-) basis (12.00 µs).
2. **Deterministic Tri-State Boundary:** The outputs remain actively driven throughout the full 24.00 µs burst. On the 13th word (`0x8000`), the hardware immediately switches all pins to High-Z (tri-state) until the next 10 ms refresh period.
3. **Optimized Timing Window (t = 2.0 ms Post-Refresh):** Executing the 24 µs burst early at t = 2.0 ms positions the measurement on the flat, stable plateau of the DAC and weight lines before capacitor leakage causes droop.
4. **End-of-Pulse ADC Sampling (t = 1.96 µs):** Differential SAR ADCs (`XC2361A`, `ADC_45` & `ADC_49`) sample at the end of each 2.00 µs pulse right before the next pulse transition.

#### Oscilloscope Verification: Corrected Hadamard Carrier Lines

**First Hadamard Line Probed:**
![](Hadamard_corrected_first_line.jpeg)

**Another Hadamard Line Probed:**
![](Hadamard_corrected_another_line.jpeg)

#### Code Example: 2x6 Hadamard Matrix & Hardware Sequencer Configuration

```c
/* ============================================================================
 * Contiguous 2x6 = 12-Pulse Hadamard Table (2.00 us per pulse = 24.00 us total)
 *   - (+) Table (pulses 0..5, 12.00 us): 6 orthogonal non-DC Walsh-Hadamard rows
 *   - (-) Table (pulses 6..11, 12.00 us): exact bitwise complement (~(+) & 0x7FFF)
 *   - Step 12 (at t = 24.00 us): 0x8000 (Tri-State Hi-Z exit until next 10 ms cycle)
 *   - ZERO tri-state gaps between the 12 pulses!
 *   - ADC_45 & ADC_49 sample at t = 1.96 us (end of each 2.00 us pulse)
 * ============================================================================ */
static const uint16_t HADAMARD_2X6_POS[6] = {
    0x2AAAu, /* p=0: basis row 1 */
    0x1999u, /* p=1: basis row 2 */
    0x4CCCu, /* p=2: basis row 3 */
    0x0787u, /* p=3: basis row 4 */
    0x52D2u, /* p=4: basis row 5 */
    0x61E1u  /* p=5: basis row 6 */
};

/* Load contiguous 12 pulses + Hi-Z termination into T120 H-bus sequence RAM */
for (int p = 0; p < 6; p++) {
    uint16_t w_pos = HADAMARD_2X6_POS[p] & 0x7FFFu;
    uint16_t w_neg = (~HADAMARD_2X6_POS[p]) & 0x7FFFu;
    *(volatile uint32_t *)(T20_BRIDGE_BASE + T20_H_TABLE + 4 * p)       = (uint32_t)w_pos;
    *(volatile uint32_t *)(T20_BRIDGE_BASE + T20_H_TABLE + 4 * (p + 6)) = (uint32_t)w_neg;
}
*(volatile uint32_t *)(T20_BRIDGE_BASE + T20_H_TABLE + 4 * 12) = 0x00008000u; /* Exit to Hi-Z */

/* Configure 10.0 MHz T20_CLK9, 2.000 us pulse period, and 13 words */
T20_REG(T20_CLK_PERIOD) = 5u;   /* 10.0 MHz CLK9 (100 ns period) */
T20_REG(T20_H_PERIOD)   = 20u;  /* 20 cycles = 2.000 us exact pulse width */
T20_REG(T20_H_COUNT)    = 13u;  /* 12 active pulses (24.00 us) + 1 Hi-Z word */
```

---

### Weight Line Transient Loading During Refresh & 100 nF Memory Cell Probing — 2026-10-18

To understand how the `100 nF` 2T1C gate storage capacitors interact with the Weight charging bus (`W_M1_ROW1`) during the refresh phase, two dual-channel oscilloscope measurements were captured on **2026-10-18** (`500 mV/div`, `2 ms/div`):

- **Channel 2 (Blue):** Probed directly on the Matrix 3 Weight row line **`W_M1_ROW1`**.
- **Channel 1 (Yellow):** Probed directly at the internal **`100 nF` memory capacitor storage node** (`\$1I15\\\$1I2\\\$2N1` and a second memory cell along the same row).

![](EasyEDA/W_M1_ROW1_100nF_mem_cell_node.png)

#### 1. First `100 nF` Memory Cell (`\$1I15\\\$1I2\\\$2N1`) vs. `W_M1_ROW1`:
![](Blue_Weight_line_Yellow_100nF_mem_cell_1.jpeg)

#### 2. Second `100 nF` Memory Cell on the Same Row vs. `W_M1_ROW1`:
![](Blue_Weight_line_Yellow_100nF_mem_cell_2.jpeg)

#### Key Findings & Low-Output-Resistance / High-Current-Drive Tricks at the Op-Amp Output Stage (2026-10-18):
1. **PCB Copper Traces Are Fine — The Bottleneck Is Strictly Op-Amp Output Resistance ($R_\text{out}$) and Current Drive Strength:**
   - The **Blue** trace (`W_M1_ROW1`) shows identical voltage dips when measured at different cell positions along the row (`Cell 1` vs. `Cell 2`), confirming that the **PCB copper trace itself has negligible resistance/drop and looks completely fine**.
   - Instead, each time the column refresh switches turn on to charge the `100 nF` memory capacitors along the row, the charging current exceeds the linear sourcing capability of the **Weight DAC op-amp output stage**, pulling its output voltage down.
   - The **Yellow** trace shows each `100 nF` memory capacitor jumping up to its charged voltage level during the refresh pulse (e.g., $\sim 2.50\text{ V}$ max in Cell 1, $\sim 2.28\text{ V}$ max in Cell 2) and then decaying by $\sim 300\text{ mV}_\text{pp}$ over the $10\text{ ms}$ cycle until the next refresh event.
2. **Bottom-Line Solution — Stiff, Low-Output-Resistance ($R_\text{out}$) Driver Tricks at the Op-Amp Output Stage (All Weight & Data Lines):**
   - Because the PCB copper routing is solid, the fix is focused entirely on making the **op-amp driver output stage a stiff voltage source with low output resistance ($R_\text{out} \to 0$) and high current drive** across all DAC Weight drivers and all DAC Data drivers:
   - **Trick 1 — High-Current Pin-Compatible SOIC-14 Op-Amp Swap (`AD8534ARZ` / `OPA4310IDR`):** Replacing the weak `MCP6024T-I/SL` buffers with high-current ($\pm 150\text{--}250\text{ mA}$) quad op-amps directly provides the current-sourcing muscle needed to hold the output voltage stiff under the 12-column simultaneous load (`Matrix(3) + Matrix(33)`) and during capacitor refresh.
   - **Trick 2 — Local `100 nF+` Charge-Reservoir Buffer Capacitor Right at the Op-Amp Output:** Adding a **local `100 nF` (or larger) energy reservoir capacitor** right at the op-amp driver output stage (with a small series isolation/damping resistor if needed for op-amp stability) acts as a local charge bucket so switching a decayed `100 nF` memory cell onto `W_M1_ROW1` does not pull down the op-amp output voltage.
   - **Trick 3 — Inside-the-Loop Current Booster / Emitter-Follower Output Stage (for Next PCB Revision):** Placing a low-output-resistance current-booster / emitter-follower inside the op-amp feedback loop (or dedicating separate op-amp buffers per 6-column matrix instead of sharing one buffer across `Matrix(3)` and `Matrix(33)`) makes the driver output stage a rock-solid voltage source and **offloads the Inverted MAML compensation loop** so it only has to compensate for 2T1C cell physics.

---

### Manual Verification with Efinix Logic Analyzer (`la0` & GTKWave) — 2026-10-17 / 2026-10-18

To independently verify the bare-metal hardware signals without relying solely on software telemetry, a dedicated Efinity Logic Analyzer build (`FPGA_code/T120F324_LA`) was synthesized and manually checked in the Efinix Debugger GUI and GTKWave:

#### 1. Downsampled Capture Showing Full 12-Step Hadamard Burst (`0..B`) & Bare-Metal `ADC_45` / `ADC_49` Response (2026-10-17):
![](Raw_ADC_45_ADC_49.png)

#### 2. Full-Speed `50 MHz` (`20 ns`) Sampling Showing Individual `25 MHz` SAR ADC SPI Clocks, MISO Bits & One-Shot Strobes (2026-10-18):
![](Raw_ADC_45_ADC_49_full_speed_sampling.png)

- **Dates:** 2026-10-17 & 2026-10-18
- **Manual Check Confirmed:** Both the downsampled burst capture and the full-speed `50 MHz` (`Capture Mode = Always`) capture confirm the live Hadamard carrier wave function (`h_step_idx[3:0] = 0..B`, `h_word_m3_ptu[5:0]`, `hadamard_burst_act = 1`, `hadamard_on_n_off = 1`), the `10 MHz` `t20_clk9` bursts, the `25 MHz` `adc45_sck` / `adc45_conv` / `adc45_out1_sdo0` / `adc45_out2_sdo1` SPI frames, and the resulting 12-bit deserialized words on `ADC_45` (`adc45_ch0_raw`, `adc45_ch1_raw`, `adc45_ch2_raw`) and `ADC_49` (`adc49_ch2_raw`).

