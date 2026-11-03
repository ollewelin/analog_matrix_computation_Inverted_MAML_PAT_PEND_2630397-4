---
name: hadamard-attenuator-selftest
description: Automated hardware self-test and continuity diagnostic skill for the Inverted MAML Analog Compensation Branch, 16x16 Walsh-Hadamard demodulation, Sigmoid 4 jumpers (H1$CBB), and the passive summing attenuator (1k/5.1k vs 1k/3.9k). Use whenever testing solder joints, verifying attenuator installation, checking for disconnected jumpers, or diagnosing missing Hadamard gradient response on physical silicon.
---

# Hadamard & Attenuator Branch Continuity Self-Test Skill

This skill provides an automated hardware diagnostic protocol and executable CLI tool (`run_hadamard_attenuator_selftest.py`) to systematically verify the physical integrity, solder joints, header jumpers, and dynamic AC transfer functions of the **Inverted MAML Analog Compensation Network**.

---

## 1. The Critical Failure Mode: Why DC Voltage Inspection Fails

A common and dangerous pitfall when inspecting analog neural network hardware is relying on static DC voltage readings:
* **The High-Impedance DC Illusion:** When an analog header jumper (such as `H1$CBB8`) is unplugged, or when a surface-mount attenuator resistor has a cold solder joint, the downstream node (`SIG_OUT_Y` or ColTIA summing junction) floats in a high-impedance (High-Z) state.
* **Leakage Currents Mimic Valid DC:** High-Z nodes collect parasitic PCB leakage currents and input bias currents, often settling at static DC levels (e.g. between $-1800\text{ LSB}$ and $0\text{ LSB}$) that look deceptively "normal" to simple DC range guards.
* **The Only True Test is Dynamic AC Response:** A physical signal connection can **only** be verified by injecting a dynamic perturbation (such as Walsh-Hadamard carrier modulation or single-cell weight steps in Matrix 8) and confirming that the demodulated differential signal $\Delta ADC_{49}$ changes with the expected gain and phase.

```
       [DAC2 In-Data / Clock]
                 │
                 ▼
         [Matrix 3 Multipliers]
                 │
                 ▼
          [ColTIA_3 Op-Amp]
                 │
                 ▼
      [Sigmoid 4 Non-Linear Stage]
                 │
                 ▼
         [Matrix 8 Multipliers]
                 │
                 ▼
          [ColTIA_8 Op-Amp]
                 │
                 ▼
     [Sigmoid 10 Stage & Jumper H1$CBB (Ch 0..5)]
         ├── Pin 1–2 (Mode A): Sigmoid 10 Non-Linear Mode (SIGM)
         ├── Open    (Mode B): Disconnected / Dangling (NO SIGNAL to attenuator)
         └── Pin 2–3 (Mode C): Linear Bypass Mode (SIGM_BYPAS)
                 │
                 ▼
    [PASSIVE SUMMING ATTENUATOR (1k / 5.1k or 1k / 3.9k)]
                 │  <-- IF COLD SOLDER JOINT: NO HADAMARD RESPONSE!
                 ▼
      [Primary Summing Junction at ADC_49]
```

### Jumper Header H1$CBB Configuration (Ch 0..5)
* **Header assignment:** `H1$CBB8` = Ch 0, `H1$CBB10` = Ch 1, `H1$CBB11` = Ch 2, `H1$CBB12` = Ch 3, `H1$CBB13` = Ch 4, `H1$CBB14` = Ch 5.
* **Mode A (Pins 1–2):** Mat(8) runs through Sigmoid(10) non-linear stage to the 1k/5.1k attenuator.
* **Mode B (Urkopplad / Open):** Jumper removed / dangling. Output node `SIG_OUT_Y` floats; zero compensation signal reaches the attenuator or summing junction.
* **Mode C (Pins 2–3):** Mat(8) runs linearly (bypasses Sigmoid(10)) directly to the 1k/5.1k attenuator.

---

## 2. Three-Phase Diagnostic Protocol

The self-test runs three deterministic tests across all 6 analog processing columns:

### Phase 1: Matrix 8 Dynamic Crosspoint Deflection ($\Delta ADC_{49} / \Delta W_{M8}$)
* Holds Matrix 33 (primary payload) and Matrix 3 at fixed quiescent baseline.
* Steps Matrix 8 weights symmetrically between $+80\text{ LSB}$ and $-80\text{ LSB}$ on diagonal crosspoints $(c, c)$ for each column $c \in [0..5]$.
* Measures the physical differential deflection $\Delta ADC_{49}[c] = ADC_{49}(W=+80) - ADC_{49}(W=-80)$.
* **Pass Criteria:**
  * $|\Delta ADC_{49}[c]| \ge 30\text{ LSB}$ with consistent phase.
* **Fail Criteria:**
  * $|\Delta ADC_{49}[c]| < 10\text{ LSB} \implies$ **FLAG: DISCONNECTED JUMPER (H1$CBB) OR BROKEN ATTENUATOR SOLDER JOINT!**

### Phase 2: 16x16 Walsh-Hadamard Carrier Transmission & Demodulation
* Executes `MAML_CMD_DIAG_HADAMARD` across the 16 Walsh-Hadamard modulation channels at $500\text{ kHz}$.
* Computes the in-band carrier power vs. orthogonal noise floor across each column.
* **Pass Criteria:**
  * In-band Carrier-to-Noise Ratio (CNR) $\ge 12.0\text{ dB}$.
* **Fail Criteria:**
  * $\text{CNR} < 6.0\text{ dB} \implies$ **FLAG: NO HADAMARD MODULATION REACHING SUMMING AMPLIFIER!**

### Phase 3: Attenuator Transfer Function & Resistance Ratio Discrimination
* Compares the measured empirical slope $\frac{\partial ADC_{49}}{\partial W_{M8}}$ against known reference ranges:
  * **$1\text{ k}\Omega / 3.9\text{ k}\Omega$ Attenuator:** Lower attenuation, higher authority ($\approx 0.85 - 1.20\text{ LSB/weight LSB}$).
  * **$1\text{ k}\Omega / 5.1\text{ k}\Omega$ Attenuator:** Higher attenuation, ultra-high resolution ($\approx 0.60 - 0.82\text{ LSB/weight LSB}$).
  * **Broken / Open Trace:** $\approx 0.00\text{ LSB/weight LSB}$.

---

## 3. CLI Execution

To run the automated self-test on physical hardware with a single command:

```bash
# Easy one-line runner from workspace root:
./run_selftest.sh

# Or directly via Python:
/home/olle/anaconda3/bin/python FPGA_code/scripts/run_hadamard_attenuator_selftest.py
```

---

## 4. Diagnostic Checklist for Failed Columns

If the self-test reports `[FAIL]` on column $c$:
1. **Check Header `H1$CBB[c]`:** Verify the jumper shunt is firmly seated across **Pins 1–2** (`Sigmoid mode`). If the shunt is missing or loose, `SIG_OUT_Y` is completely disconnected.
2. **Inspect Attenuator Resistors for Column $c$:**
   * Verify the series resistor ($1\text{ k}\Omega$) and shunt resistor ($5.1\text{ k}\Omega$ or $3.9\text{ k}\Omega$) for cold joints or cracked solder fillets.
3. **Check Op-Amp Drive:**
   * Probe `SIG_OUT_Y` with an oscilloscope during Hadamard modulation ($500\text{ kHz}$) to verify active dynamic signal before the attenuator.

