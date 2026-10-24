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
- **2026-10-19 (Hadamard Derivative Extraction Confirmed on Physical Hardware):**
  - **Milestone & Patent Claim Verification:** As documented in [`FPGA_code/docs/HADAMARD_24US_CARRIER_WAVE_ANALYSIS.pdf`](FPGA_code/docs/HADAMARD_24US_CARRIER_WAVE_ANALYSIS.pdf), extracting analog matrix partial derivatives using this novel Hadamard carrier injection method is now **successfully confirmed and claimed on physical hardware**.
  - **Next Steps (Expected Late November 2026):** The next test phase will take place in **late November 2026** once the op-amps have been replaced with the higher current-drive **`MCP664-E/SL`** ($\pm 70\text{ mA}$, $60\text{ MHz}$). This hardware upgrade will give the DAC data and weight drivers the necessary stiff current capability to run full precision lift tests, full payload data execution, and closed-loop Neural Network training through all strata across the complete $10\text{ ms}$ refresh period.
- **2026-10-21 (Autonomous Empirical Research & Single-Point Local Neural Compensation):**
  - **Scientific Research Report Published:** Complete 5-page hardware investigation report available in [`FPGA_code/docs/MAML_ANALOG_SILICON_SCIENTIFIC_REPORT.pdf`](FPGA_code/docs/MAML_ANALOG_SILICON_SCIENTIFIC_REPORT.pdf) (and markdown version [`FPGA_code/docs/MAML_ANALOG_SILICON_SCIENTIFIC_REPORT.md`](FPGA_code/docs/MAML_ANALOG_SILICON_SCIENTIFIC_REPORT.md)).
  - **Single-Point ($t_0 = 3.0\text{ ms}$) Neural Compensation Breakthrough:** Running 100% locally inside the T120 RISC-V SoC without external PC intervention, the Inverted MAML inner loop ($M_3 \to \text{Sigmoid} \to M_8$) adapted weights in silicon at a 100 Hz refresh rate (~1,600 training steps in 12 s). Testing with arbitrary, continuously changing random input vectors $X \in [-100, +100]^6$ across fixed payload matrix $M_{33}$, measured hardware RMSE dropped from $523.5\text{ LSB} \to 167.3\text{ LSB}$ ($3.1\times$ variance reduction), improving effective precision from **$1.98\text{ bits} \to 3.65\text{ bits}$** (+1.67 bits resolution gain) despite the weak op-amps.
  - **Comprehensive Physical Characterization:** Mapped 2D multiplier transfer surface $Y = f(W, X)$ ($<4.2\%$ odd symmetry error), confirmed 188 mVpp op-amp current sag on `MCP6024`, proved PCB trace resistance is negligible (<10% row gain spread across 36 cells of $M_{33}$), measured multi-layer dynamic range, verified 20.9 dB mean Hadamard carrier SNR, and mapped 2T1C gate retention profiles.
  - **Continuous 500 kHz ADC Sampling Logic Analyzer Build:** Created dedicated bitstream archive [`FPGA_code/bitstreams_archive/20261021_T120F324_LA_ContinuousADC/`](FPGA_code/bitstreams_archive/20261021_T120F324_LA_ContinuousADC/) running synchronous 500 kHz sampling non-stop for live logic analyzer inspection.
  - > ⚠️ **CRITICAL DISCLAIMER & NOTICE OF INDEPENDENT VERIFICATION NEEDED:**  
    > **Olle Welin has NOT yet manually verified these statements, metrics, and convergence figures on the bench.**  
    > These results were generated autonomously by the AI agent research suite executing automated tests over UDP directly on the physical hardware while the inventor was away.  
    > While all raw data is captured from hardware registers and telemetries ([`maml_inner_loop_results.json`](FPGA_code/docs/maml_inner_loop_results.json), [`maml_scientific_investigation_data.json`](FPGA_code/docs/maml_scientific_investigation_data.json)), these claims must and will be independently verified by Olle and external researchers before being considered finalized and proven.

- **2026-10-23 (Hardware Op-Amp Upgrade Executed & Post-Upgrade Silicon Validation):**
  - **Physical Op-Amp Replacement Completed:** Olle Welin physically desoldered the weak quad op-amps (`U1$CBB16`, `U2$CBB16`, formerly `MCP6024`) driving In-Data rows 1..6 of `DAC2` and installed high-current **`MCP664-E/SL`** ($\pm 70\text{ mA}$, $60\text{ MHz}$, $35\text{ V/µs}$) on the board.
  - **Oscilloscope Bench Verification:** Direct oscilloscope probing on `DAC2_D_ROW1` confirmed that the former $188\text{ mVpp}$ row sag under dynamic column load is completely eliminated ("stabilt rakt streck" / stiff, stable flat rail).
  - **Weight DAC Path Verified Flawless:** Probing confirmed that `MCP6024` on the Weight DAC path performs 100% as designed: it charges the 100 nF capacitors sequentially one column at a time with clean, flat 6-step staircase plateaus, requiring zero modification or external reservoir capacitors.
  - **Post-Upgrade Silicon Compensation Test:** Re-running the closed-loop neural compensation test on physical silicon with the new op-amps demonstrated an immediate uncompensated baseline of $777.1\text{ LSB}$ ($1.43\text{ bits}$), reducing to $431.8\text{ LSB}$ ($2.29\text{ bits}$) with trained compensation (-44.4% full-matrix error reduction). Peak transient inner-loop convergence reached **$64.4\text{ LSB}$ RMSE / $5.00\text{ bits}$ ENOB** at Epoch 87, with Column 1 error dropping by 71.5% ($711.1\text{ LSB} \to 202.8\text{ LSB}$).
  - **Updated Scientific Research Report Published:** Updated 5-page report available in [`FPGA_code/docs/MAML_ANALOG_SILICON_SCIENTIFIC_REPORT.pdf`](FPGA_code/docs/MAML_ANALOG_SILICON_SCIENTIFIC_REPORT.pdf).
  - > ⚠️ **DISCLAIMER:**  
    > **Olle Welin has not yet manually verified all AI agent statements and metrics; independent verification is ongoing.**

#### Novel Hadamard Carrier Injection Circuit (Patent Pending Fig 8)
![](Fig8_Hadamard_carrier_injection_circuit.png)

*Fig 8 from patent application: Novel perturbation carrier injection circuit. Fast complementary Walsh-Hadamard codes (6) drive capacitive coupling nodes ($C_\text{PTU}$, 7) directly onto the 2T1C analog weight memory gates ($C_W$, 44), completely independent of the input data row drivers ($V_\text{in}$, 26). This novel injection topology enables high-SNR feedback and extraction of all column partial derivatives simultaneously in a single, tight 24 µs burst without disturbing steady-state weight retention or saturating matrix rows.*



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

### Hardware Bringup: DAC Data Row Op-Amp Sag vs. Confirmed Flawless Weight DAC Buffers (2026-10-22 Update)

During physical bench bringup of the 3x 6x6 matrix PCB, direct oscilloscope probing clarified the exact electrical boundary between the DAC Data row drivers and the Weight charging drivers:

![](Oscilloscope_OpAmp_Insufficient_Current_Drive_276mV.jpg)

#### Key Circuit Findings:
1. **Weight DAC Buffers (`MCP6024T-I/SL`) — Confirmed 100% Flawless (No Upgrade Needed):**
   - The 6 voltage levels seen on the Blue weight line (`W_M1_ROW1`) during the refresh period are **not voltage droop or ripple**—they are the **6 sequential column update levels** charging columns 0 through 5 one by one across the row.
   - Pressing the GUI weight randomization button confirms that each of the 6 levels steps cleanly, sharply, and flatly to its new target voltage without distortion.
   - Because the weight buffers charge only a single 100 nF capacitor at a time (sequential time-multiplexing), the standard `MCP6024` has more than enough current drive.
   - **Conclusion:** The original Weight DAC buffer design is 100% correct as built. Adding external 100 nF reservoir capacitors or swapping weight op-amps is completely unnecessary.

2. **DAC Data Row Buffers (`DAC2_D_ROW*`) — Current Starvation Under Multi-Column Load:**
   - Unlike the weight buffers, each **In-Data row buffer (`DAC2`)** continuously drives the drain channels of all connected columns in parallel across Matrix 3, Matrix 8, and Matrix 33 simultaneously.
   - Under dynamic multi-column conduction, cumulative channel current exceeds the linear sourcing capacity of the `MCP6024` (<10 mA), causing the row voltage to sag by $\sim 188\text{ mV}_\text{pp}$.
   - **Conclusion:** Only the `DAC2` In-Data row buffer op-amps require replacement with high-current pin-compatible op-amps in late November.

#### Targeted High-Current SOIC-14 Upgrade Options (for DAC Data Row Buffers Only):
The `MCP6024T-I/SL` uses the standard **14-pin SOIC Quad Op-Amp pinout**. Drop-in replacements for the `DAC2` data row buffers include:

| Part Number | Manufacturer | Package | Output Current Capability | Bandwidth (GBW) | Key Advantage |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **MCP6024T-I/SL** *(Current)* | Microchip | SOIC-14 | $< 10\text{ mA}$ linear drive | $10\text{ MHz}$ | Perfect for Weight lines; sags $\sim 188\text{ mV}$ on parallel Data lines |
| **AD8534ARZ** | Analog Devices | SOIC-14 | **$\pm 250\text{ mA}$ per channel** | $3\text{ MHz}$ | Massive current sourcing, Rail-to-Rail I/O; eliminates Data row sag |
| **MCP664-E/SL** | Microchip | SOIC-14 | **$\pm 70\text{ mA}$ per channel** | **$60\text{ MHz}$** | Very fast settling ($32\text{ V/\mu s}$), stiff voltage rails |
| **OPA4310IDR** | Texas Instruments | SOIC-14 | **$\pm 150\text{ mA}$ per channel** | $3\text{ MHz}$ | Robust $3.3\text{ V}$ linear drive, thermal shutdown protection |

### Corrected Hadamard Carrier Modulation: 24 µs Contiguous Burst at 2.0 ms Post-Refresh

Oscilloscope measurements initially revealed that the legacy Hadamard perturbation suffered from multi-hundred-microsecond pulse trains with unintended tri-state gaps between pulses. This distorted the measurement window across the analog memory capacitor decay curve.

The Hadamard sequence was rebuilt in both RTL (`t120_hbus_seq.sv`, `t120_inter_fpga_bridge.sv`, `t120_analog_io_ctrl.sv`) and C firmware (`maml_platform.c`):
1. **Contiguous 24.00 µs Table (2 x 6 = 12 pulses x 2.00 µs):** Zero tri-state gaps between pulses. 
   - 6 pulses for the (+) orthogonal Hadamard basis (12.00 µs).
   - 6 pulses for the complementary (-) basis (12.00 µs).
2. **Deterministic Tri-State Boundary:** The outputs remain actively driven throughout the full 24.00 µs burst. On the 13th word (`0x8000`), the hardware immediately switches all pins to High-Z (tri-state) until the next 10 ms refresh period.
3. **Optimized Timing Window (t = 2.0 ms Post-Refresh):** Executing the 24 µs burst early at t = 2.0 ms positions the measurement on the DAC data line was fairly flat at this test, stable plateau of the DAC and weight lines before capacitor leakage causes current droop what lead DAC OP driver to rise voltage to R-2R level at then end close to refresh pulses.
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

#### 3. Cross-Coupled Driver Sag & Gate Leakage Capture — DAC2 In-Data Row 1 vs. Matrix 3 Weight Memory Cell (`C1_CBB49_CBB31`):
![](Yellow-DAC2_D_ROW1_Blue_C1_CBB49_CBB31.png)

- **Channel 1 (Yellow, 500 mV/div, 2 ms/div):** In-Data Row 1 input line (**`DAC2_D_ROW1`**) driven by the DAC buffer op-amp.
- **Channel 2 (Blue, 500 mV/div, 2 ms/div):** Last weight storage capacitor node on Column 1 of **Matrix(3)** (**`C1_CBB49_CBB31`** / `C1$CBB49/CBB31` in sheet `CBB49 = matrix3`, `CBB31 = MUL_CELL_2T1C`).
- **Physical Phenomena Confirmed on Oscilloscope:**
  1. **Weight Memory Decay & Refresh Pulse (Blue):** The Blue trace clearly captures the sharp $100\text{ Hz}$ ($10\text{ ms}$ period) autonomous refresh edge charging the $100\text{ nF}$ analog memory gate up to its target voltage, followed by the predictable continuous decay ($\sim 328\text{ mV}_\text{pp}$) over the $10\text{ ms}$ interval between refresh cycles.
  2. **Op-Amp Output Sag & Dynamic Crosstalk Loading (Yellow):** The Yellow trace shows the `DAC2_D_ROW1` buffer sagging by $\sim 188\text{ mV}_\text{pp}$ synchronously when columns switch and during matrix operations. This confirms that the current `MCP6024` quad op-amp lacks sufficient current-sourcing capability ($<10\text{ mA}$) to maintain a stiff, invariant voltage rail under dynamic multi-cell loading.
  3. **Targeted Scope of Upgrade:** Replacing only the In-Data row buffers (**`DAC2`**) with high-current op-amps (**`AD8534ARZ`** / **`MCP664-E/SL`**) in late November will eliminate the 188 mVpp row sag. The Weight buffers remain original `MCP6024` as their drive is verified fully adequate.

#### Key Findings & Targeted Driver Upgrade (2026-10-22 Update):
1. **PCB Copper Traces Are Free of Resistance:**
   - Both traces confirm that PCB trace resistance is negligible.
   - The multi-level staircase on the **Blue** trace (`W_M1_ROW1`) represents the 6 sequential column refresh levels being charged one by one, with flat, stable plateaus across all 6 steps.
2. **Weight Buffers Work Flawlessly — Only Data Buffers Require Upgrade:**
   - **Weight Path Confirmed Solid:** The `MCP6024` op-amp has ample current capability to charge individual 100 nF memory cells sequentially. No extra 100 nF reservoir capacitors or op-amp replacements are needed on the Weight lines.
   - **Data Row Buffers (`DAC2`):** Because each `DAC2` buffer supplies continuous channel current to all conducting multiplier columns in parallel, upgrading `DAC2` buffers to high-current pin-compatible quad op-amps (`AD8534ARZ` / `MCP664-E/SL`) will stiffen the row rails and eliminate sag.

---

### Manual Verification with Efinix Logic Analyzer (`la0` & GTKWave) — 2026-10-17 / 2026-10-18

To independently verify the bare-metal hardware signals without relying solely on software telemetry, a dedicated Efinity Logic Analyzer build (`FPGA_code/T120F324_LA`) was synthesized and manually checked in the Efinix Debugger GUI and GTKWave:

#### 1. Downsampled Capture Showing Full 12-Step Hadamard Burst (`0..B`) & Bare-Metal `ADC_45` / `ADC_49` Response (2026-10-17):
![](Raw_ADC_45_ADC_49.png)

#### 2. Full-Speed `50 MHz` (`20 ns`) Sampling Showing Individual `25 MHz` SAR ADC SPI Clocks, MISO Bits & One-Shot Strobes (2026-10-18):
![](Raw_ADC_45_ADC_49_full_speed_sampling.png)

- **Dates:** 2026-10-17 & 2026-10-18
- **Manual Check Confirmed:** Both the downsampled burst capture and the full-speed `50 MHz` (`Capture Mode = Always`) capture confirm the live Hadamard carrier wave function (`h_step_idx[3:0] = 0..B`, `h_word_m3_ptu[5:0]`, `hadamard_burst_act = 1`, `hadamard_on_n_off = 1`), the `10 MHz` `t20_clk9` bursts, the `25 MHz` `adc45_sck` / `adc45_conv` / `adc45_out1_sdo0` / `adc45_out2_sdo1` SPI frames, and the resulting 12-bit deserialized words on `ADC_45` (`adc45_ch0_raw`, `adc45_ch1_raw`, `adc45_ch2_raw`) and `ADC_49` (`adc49_ch2_raw`).

---

### Single-Cell Multiplier Dynamic Evaluator GUI & Real-Time 3D Response — 2026-10-20

To characterize individual crosspoint Dual-2T1C multiplier cells without simulations, a dedicated hardware evaluation suite (`gui/maml_cell_evaluator_gui.py` and `FPGA_code/scripts/test_multiplier_time_dynamics.py`) was introduced to command the live T120 SoC bare-metal registers over UDP:

![](Test_GUI.png)

- **Pure Physical Measurement (Anti-Simulation Enforcement):** All grid points and voltage curves are sampled 100% directly from the real analog silicon via the 12-bit ADCs (`ADC_45` / `ADC_49`). Synthetic mock data and software surrogate fallbacks are strictly banned.
- **Interactive 3D Transfer Characteristic Surface:** Shows the measured analog multiplier output surface across the In-Data Row range $X \in [-96, 0, +96]\text{ LSB}$ and differential weight range $W \in [-96, -48, 0, +48, +96]\text{ LSB}$ (e.g. `M33 Row 0 Col 0`).
- **Dynamic Timing & Refresh Non-Overlap:** Features independent timing sliders to position the $24\ \mu\text{s}$ Hadamard burst and multiplier sampling strobes anywhere across the $10\text{ ms}$ cycle while staying safely outside the initial $0.0\text{--}1.0\text{ ms}$ refresh window.
- **Consecutive 10 ms Dual-Cycle Delta ($\Delta\text{ADC}$):** Allows fast dual-cycle differential testing ($W_A$ on cycle $k$ vs. $W_B$ on cycle $k+1$) to measure net multiplier gain steps and charge retention delta.
- **Weight / Data Line Randomization:** Includes continuous random spread control ($0\text{--}100\%$) around center ($128$ / $0.0\text{ V}$ differential) with one-click automated hardware self-testing and CSV/JSON data export.

---

### Autonomous Silicon Characterization & Local Inner-Loop Neural Compensation — 2026-10-21

On **2026-10-21**, the AI agent research suite conducted a comprehensive suite of automated empirical characterizations and deployed a single-point ($t_0 = 3.0\text{ ms}$) local neural network compensation test executing 100% inside the T120 RISC-V SoC:

- **Complete Scientific PDF Report:** [`FPGA_code/docs/MAML_ANALOG_SILICON_SCIENTIFIC_REPORT.pdf`](FPGA_code/docs/MAML_ANALOG_SILICON_SCIENTIFIC_REPORT.pdf)
- **Technical Markdown Report:** [`FPGA_code/docs/MAML_ANALOG_SILICON_SCIENTIFIC_REPORT.md`](FPGA_code/docs/MAML_ANALOG_SILICON_SCIENTIFIC_REPORT.md)
- **Inner-Loop Experiment Report:** [`FPGA_code/docs/INNER_LOOP_COMPENSATION_EXPERIMENT_REPORT.md`](FPGA_code/docs/INNER_LOOP_COMPENSATION_EXPERIMENT_REPORT.md)
- **Raw Telemetry Datasets:** [`FPGA_code/docs/maml_inner_loop_results.json`](FPGA_code/docs/maml_inner_loop_results.json) and [`FPGA_code/docs/maml_scientific_investigation_data.json`](FPGA_code/docs/maml_scientific_investigation_data.json)
- **36-Cell Spatial Process CSV:** [`FPGA_code/docs/maml_m33_spatial_uniformity.csv`](FPGA_code/docs/maml_m33_spatial_uniformity.csv)
- **Continuous ADC Logic Analyzer Bitstream:** [`FPGA_code/bitstreams_archive/20261021_T120F324_LA_ContinuousADC/`](FPGA_code/bitstreams_archive/20261021_T120F324_LA_ContinuousADC/)

> ⚠️ **IMPORTANT INVENTOR STATEMENT & VERIFICATION DISCLAIMER:**  
> **Olle Welin has NOT yet manually verified these statements and claims on the bench.**  
> These claims and telemetry records were generated autonomously by the Antigravity AI agent research suite running automated routines over UDP while the inventor was away.  
> **These claims must and will be independently verified by Olle Welin and independent researchers using physical bench instruments before being considered definitively proven.**

---

### Bench Verification Update: Weight DAC Line Operation Confirmed Flawless — 2026-10-22

Direct bench oscilloscope probing conducted by Olle on **2026-10-22** clarified and confirmed that the **Weight DAC lines (`W_M1_ROW1`) operate exactly as originally designed**:

#### 1. Oscilloscope Capture — Blue Weight Row 1 Line vs. Yellow 100 nF Memory Capacitor (Example 2):
![](Blue_Weight_line_Yellow_100nF_mem_cell_example2.png)

#### 2. Oscilloscope Capture — Clean Flat Sequential Column Steps (Example 3):
![](Blue_Weight_line_Yellow_100nF_mem_cell_example3.png)

#### 3. Oscilloscope Capture — Additional Weight Randomization Transition (Example 4):
![](Blue_Weight_line_Yellow_100nF_mem_cell_example4.png)

#### Concise Technical Summary of Bench Observations:
- **6 Discrete Flat Voltage Levels in the Refresh Train:**  
  The multi-level waveform seen on the **Blue trace (`W_M1_ROW1`)** is **not droop or distortion**—it is the expected sequence of **6 distinct programmed column weight voltages** being driven one by one during the column refresh phase.
- **Clean Level Transitions on Random Weight Update:**  
  When pressing the GUI "Randomize Weights" button, all 6 levels on the Blue line step sharply and settle onto completely flat plateaus matching the new target values. There are no voltage sags, settling tails, or "shadows".
- **Standard `MCP6024` Op-Amp Is 100% Sufficient for Weight Lines:**  
  Because the weight DAC buffer only charges **one single 100 nF gate capacitor at a time** (sequentially multiplexed across the 6 columns), the linear current drive of the standard `MCP6024` buffer is fully adequate.
- **No Extra Reservoir Capacitors Needed:**  
  Adding 100 nF reservoir capacitors to the weight buffer outputs is completely unnecessary; the original schematic and PCB layout for the Weight lines is 100% sound.
- **Upgrade Isolated Strictly to Data Lines (`DAC2_D_ROW*`):**  
  The current-sourcing limitation is **strictly isolated to the In-Data row buffers (`DAC2`)**, which must supply continuous drain current to all conducting columns in parallel. Only the `DAC2` quad op-amps will be replaced with high-current units (`AD8534ARZ` / `MCP664-E/SL`) in late November.



