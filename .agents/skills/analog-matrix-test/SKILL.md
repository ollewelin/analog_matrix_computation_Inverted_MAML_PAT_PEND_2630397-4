---
name: analog-matrix-test
description: Automated testing, characterization, and diagnostics skill for the Inverted MAML Analog Matrix hardware (T120F324 Master + T20F256 Controller, Dual-2T1C multipliers M33/M3/M8, 74HC595 differential DACs, XC2361A differential ADCs, and 3-state Hadamard drivers). Use whenever the user asks to test, diagnose, benchmark, or characterize the analog multipliers, DACs, ADCs, Hadamard settling timing, or MAML compensation network.
---

# Analog Matrix Multiplier Testing & Diagnostics Skill

This skill provides a standardized protocol and automated CLI script (`.agents/skills/analog-matrix-test/run_analog_diagnostics.py`) for testing, characterizing, and diagnosing the physical Dual-2T1C (`2X_2T1C`) analog multiplier matrices ($M_{33}$ $6\times 6$, $M_3$ $8\times 6$, $M_8$ $7\times 6$), differential `74HC595` R-2R DACs, differential `XC2361A` 12-bit SAR ADCs (`ADC_45` & `ADC_49`), and 3-state (`Data + OE`) Hadamard perturbation drivers.

---

## 1. Safety & Hardware Rules (Mandatory)

1. **Heater Safety First:**
   - **NEVER** arm `HEAT_1..4_EN` (`heater_armed = 1`) during routine multiplier diagnostics unless explicitly requested by the user. Always ensure `set_heaters(False, [0, 0, 0, 0])` is sent at the start and end of every diagnostic run.
2. **Single-Ended Row Data (`DAC_2`) vs. Differential Weight (`W`) & Hadamard (`H+/H-`) — MANDATORY NOTATION RULE:**
   - **Outside the matrix, ONLY Weight $W$ and Hadamard $H$ are differential:**
     - **Weight $W$ (`W_15`, `W_12`, `W_34`):** Differential across the mirrored `P`-branch (`G_P`) and `N`-branch (`G_N`) 2T1C half-cells (`W+ = 128 + W`, `W- = 128 - W` for signed $W \in [-127, +127]$; `W = 0` sets both gates to `code 128` = `2.60 V`, which cancels out at `COL+` minus `COL-`).
     - **Hadamard (`H_M3_P/N[1..8]`, `H_M8_P/N[1..7]`):** Differential AC-coupled (`1 nF`) into `G_P` and `G_N`, 3-stated (`OE = 0`, `Hi-Z` centered at `1.65 V`) when idle or on word `16'h8000`.
     - **ADCs (`ADC_45` & `ADC_49`):** Differential 12-bit SAR readings (`0..4095`) centered at **`2048`** (`signed_lsb = raw_12b - 2048`, `1.650 V` reference).
   - **Row Data Input (`DAC_2`, `IN_R1..6`) is STRICTLY SINGLE-ENDED UNIPOLAR (`0..255`):**
     - Per Patent Fig. 12 and [`Design_Specification_Analog_Matrix_2T1C.pdf`](../../../Design_Specification_Analog_Matrix_2T1C.pdf), each row data line is a single-ended wire shared by the Drains of both `Q5` (`P`-branch) and `Q8` (`N`-branch) with Source virtual ground $V_s = 1.650\text{ V}$:
       - `DAC_2 = 0` $\rightarrow$ $V_{\text{row}} = 1.650\text{ V}$ $\rightarrow$ **$V_{ds} = 0\text{ mV}$ (`0%` / Physical Zero Data Drive)**
       - `DAC_2 = 128` $\rightarrow$ $V_{\text{row}} = 1.775\text{ V}$ $\rightarrow$ **$V_{ds} = +125\text{ mV}$ (`50%` Mid-Scale Data Drive — NOT zero volts!)**
       - `DAC_2 = 255` $\rightarrow$ $V_{\text{row}} = 1.900\text{ V}$ $\rightarrow$ **$V_{ds} = +250\text{ mV}$ (`100%` Full-Scale Data Drive)**
   - **Pedagogical Rule for Future GUI & CLI Tables:**
     - **NEVER label Row Data `DAC_2` with signed differential notation (`X = -120, 0, +120`)!** Writing `X = -120` for `DAC_2 = 8` (`+8 mV`) and `X = 0` for `DAC_2 = 128` (`+125 mV`) is misleading because it makes `DAC_2 = 128` look like `0 V` (zero multiplier drive) and `DAC_2 = 8` look like negative voltage.
     - Always label Row Data in CLI/GUI tables using **unsigned single-ended notation**: `DAC_2` code (`0..255`), drive percentage (`0%..100%`), and/or single-ended drain-source voltage ($V_{ds} = +8\text{ mV}, +125\text{ mV}, +243\text{ mV}$ or $V_{\text{row}} = 1.658\text{ V}, 1.775\text{ V}, 1.893\text{ V}$).
3. **Synchronous Autonomous 2T1C Refresh (`10.0 ms` / `100 Hz`, $6 \times 100\ \mu\text{s}$):**
   - The `100 nF` gate capacitors (`C1, C3`) must be continuously refreshed every **`10.0 ms` (`100 Hz`)** with **`100 µs` setting time per column** (`50 µs` = $5\tau_{\text{charge}}$ for `G_N` + `50 µs` = $5\tau_{\text{charge}}$ for `G_P`, total duty window $= 600\ \mu\text{s} = 6\%$), and single-cell ADC reads must occur at a fixed deterministic delay (`10 µs`) after a synchronous refresh window.
4. **4-Phase Settle-Then-Sample Timing:**
   - Always allow the quiet analog DC settling window (`~2 µs` at 500 kHz, scaling up to `20 µs` at 50 kHz) with `T20_CLK9`, `H-bus`, and `DAC_SCK` frozen low before asserting `ADC_45_CONV` / `ADC_49_CONV`.

---

## 2. Diagnostic Workflow & Execution

### Step 1: Ensure `v2.0-MAML` Bitstream is Loaded on T120 and `T20` App Image is Active
```bash
# Check live UDP version on 192.168.1.50:5000 (auto-programs T120_MALM.bit if needed)
python3 .agents/skills/analog-matrix-test/run_analog_diagnostics.py --program-if-needed
```

### Step 2: Run the 6-Stage Analog Multiplier Diagnostic Suite (Without Reprogramming)
```bash
python3 .agents/skills/analog-matrix-test/run_analog_diagnostics.py --report FPGA_code/docs/ANALOG_MULTIPLIER_DIAGNOSTIC_REPORT.md
```

---

## 3. What the 6-Stage Diagnostic Suite Tests

1. **Stage 1 — Inter-FPGA Bridge (`T120 <-> T20`) & Application Image (`CBSEL=1`) Handshake:**
   - Verifies Ethernet UDP Port `5000` responsiveness, S-bus `ACK 0x06`, and `JUMP_APP` transition from `T20G` (Golden) to `T20` (Application Image).
2. **Stage 2 — Differential ADC (`ADC_45` & `ADC_49`) Zero-Baseline, DC Offset & Noise Floor:**
   - Centers all DACs and compensation weights at `128` (`0.0` differential) with Hadamard in `Hi-Z` (`OE=0`).
   - Samples `ADC_45[0..5]` (Intermediate Layer 1 outputs) and `ADC_49[0..5]` (Final Summed outputs) across $N=20$ bursts to measure per-column DC offset (relative to `2048`) and temporal RMS noise ($\sigma_{\text{LSB}}$).
3. **Stage 3 — Differential DAC Row Drive (`DAC_2`) & Power Trim (`W_34 / DAC 38`) Sweep:**
   - Sweeps individual DAC channels across `-96 LSB` (`code 32`), `0 LSB` (`code 128`), and `+96 LSB` (`code 224`) using `MAML_CMD_SET_DAC_MODE`, measuring analog response on `ADC_45` and `ADC_49`.
4. **Stage 4 — Analog Settling Window Frequency Sweep (`500 kHz` down to `50 kHz`):**
   - Evaluates `ADC_45` and `ADC_49` readings and MSE/ENOB across `500 kHz` (`2.0 µs` settle), `250 kHz` (`4.0 µs` settle), `100 kHz` (`10.0 µs` settle), and `50 kHz` (`20.0 µs` settle).
5. **Stage 5 — Cell-by-Cell Crosspoint Multiplier Scan (`126 Dual-2T1C Cells`):**
   - Sweeps all 36 cells in $M_{33}$ ($6\times 6$), 48 cells in $M_3$ ($8\times 6$), and 42 cells in $M_8$ ($7\times 6$) via `MAML_CMD_CELL_DIAG` and analyzes per-cell differential response, column bias, and uniformity.
6. **Stage 6 — Inverted MAML Outer/Inner Loop (`Ref 40 / Ref 41`) & Auto Bit-Precision Benchmark:**
   - Runs `MAML_CMD_AUTO_BIT_TEST` (Compensation Centered at `128` vs. Trained Compensation) and executes `MAML_CMD_STEP_OUTER` epochs to verify non-backprop forward Hadamard gradient convergence.
