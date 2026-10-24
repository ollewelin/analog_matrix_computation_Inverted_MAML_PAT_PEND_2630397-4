---
name: inverted-maml-inner-loop-mode-a
description: Architectural specification, patent mathematics, schematic analysis, and operational runbook for closing the loop in Mode A (Inner Loop Training). Prepared specifically for Argon AI agent to prevent standard backprop mistakes, enforce carrier wave search, understand the 1k/3.9k passive attenuator, and execute step-by-step ENOB optimization at 5.0 ms.
---

# Inverted MAML Mode A Inner Loop Training & Patent Mathematics Skill
**Prepared as the Master Architectural Specification & Handover Brief for Argon AI Agent**

**Patent Pending:** SE 2630397-4  
**Hardware Target:** Efinix Trion T120 Master SoC + T20 Coprocessor (`192.168.1.50:5000`)  
**Operating Mode:** Mode A (Jumper ON — Active Compensation via $M_3$ and $M_8$)  
**Initial Milestone:** Steg 1 — Reading, locked at $t = 5.0\text{ ms}$, 1k/3.9k check, Inner Loop convergence and ENOB growth  

---

## 🎯 ARGON'S PRIMARY MISSION: STEP 1 (MILSTONE 1)

> [!IMPORTANT]
> **EXACT ACTION STEPS FOR ARGON AI AGENT IN STEP 1:**
>
> 1. **MANDATORY PREREQUISITE READING (PATENT & MATHEMATICS FIRST):**
>    - Thoroughly read `maml_eng.txt` (the complete patent application), `FPGA_code/docs/NON_BACKPROP_HADAMARD_GRADIENT_RULES.md`, and `FPGA_code/docs/IP_REPRODUCTION_SPEC.md`.
>    - **STRICTLY FORBIDDEN:** Do NOT add an extra input multiplication ($x_i$) into the gradient chain rule! Multiplication by $x_i$ has ALREADY occurred physically inside the transistor channel during the forward Hadamard correlation.
>
> 2. **LOCK OPERATING POINT TO 5.0 ms ONLY:**
>    - Lock ADC sampling delay and Hadamard perturbation strictly to **$t = 5.0\text{ ms}$** (`hadamard_delay_us = 5000`).
>    - Do NOT spread out across multiple time slices yet! That is Step 2.
>
> 3. **VERIFY MODE A CENTER WEIGHTS & THE 1k / 3.9k ATTENUATOR:**
>    - Connect jumper (Mode A).
>    - Initialize all compensation weights in $M_3$ ($8\times 6$) and $M_8$ ($7\times 6$) to digital center `128` (differential weight $0.0$) via `client.center_compensation_weights()`.
>    - Measure baseline ENOB and verify that the output swing scales by $\approx 0.796\times$ due to the $1\text{ k}\Omega / 3.9\text{ k}\Omega$ passive summing attenuator.
>
> 4. **CLOSE THE LOOP WITH INNER LOOP TRAINING ONLY (NO MAML YET):**
>    - Disable MAML outer loop meta-hopping (`w_hid_mag = 0, trim_hid_mag = 0`).
>    - Apply **Masked Loss** strictly on functional columns (**Columns 0, 1, 4, 5**). Exclude saturated rails (Columns 2 and 3).
>    - Execute gentle inner loop training iterations ($N = 50\text{--}100$) with a conservative learning rate ($\alpha_{\text{inner}} \approx 0.005$).
>
> 5. **STEP 1 SUCCESS CRITERIA:**
>    - **Achieve convergence!** The masked loss must decline monotonically iteration-by-iteration, and ENOB must slowly and steadily increase!

---

## 1. Executive Brief: The Analog Physical Reality vs. Standard Machine Learning

> [!CAUTION]
> **CRITICAL CARDINAL RULE FOR ARGON AI AGENT:**
> **DO NOT IMPLEMENT STANDARD DIGITAL BACKPROPAGATION ($\frac{\partial \mathcal{L}}{\partial W_{i,j}} = \delta_j \cdot x_i$).**
> In the Inverted MAML Analog In-Memory Computing (AIMC) hardware, the forward Hadamard perturbation ($V_{\text{PTU}}$, Ref 5) is physically applied to the 2T1C MOSFET gate while the input voltage $x_i$ is present across the transistor channel ($V_{ds}$). Because the MOSFET conducts triode drain current $I_{ds} \propto g_m \cdot V_{gs} \cdot V_{ds}$, **the multiplication by input $x_i$ has ALREADY occurred inside the analog physics** during the forward Hadamard correlation.
>
> **Multiplying the demodulated Hadamard sensitivity by input $x_i$ a second time in digital firmware/software squares the input ($x_i^2$), corrupts the gradient sign and magnitude, and destroys training convergence.**

### Mandatory Prerequisite Reading for Argon AI Agent
Before touching code or executing training cycles, Argon MUST read:
1. **`maml_eng.txt`**: The complete patent application (1416 lines) for SE 2630397-4. Details the Atomic Triad (3, 8, 33), activations (4, 10), reference numerals 1..44, and Equations 1–7.
2. **`FPGA_code/docs/NON_BACKPROP_HADAMARD_GRADIENT_RULES.md`**: Architectural derivation of why forward Hadamard perturbation replaces standard backpropagation and why $x_i$ multiplication is strictly forbidden.
3. **`FPGA_code/docs/IP_REPRODUCTION_SPEC.md`**: Hardware reproduction specification and schematic mappings.
4. **`FPGA_code/docs/inverted_maml_math.md`**: Mathematical formulations of the inner loop and dot-product outer loop.

---

### Why Standard PyTorch / Backprop Assumptions Fail
In digital neural networks, backpropagation assumes:
1. Every forward operation is perfectly linear or known analytically ($y = Wx$, $\sigma(y) = \frac{1}{1 + e^{-y}}$).
2. The exact intermediate activations and Jacobian matrices can be computed analytically by software.

On physical silicon:
1. Matrix 33 exhibits **brutal non-linearities**, threshold scatter ($V_{th}$ variations across 36 cells), subthreshold pinch-off turnaround ($W < -80\text{ LSB}$), and time-varying $RC$ decay ($\tau \approx 6.8\text{ ms}$).
2. The exact transconductance $g_m(V_{gs}, V_{ds}, t)$ is an **unknown analog transfer medium**.
3. Therefore, gradients are extracted **purely through physical perturbation (Forward Walsh-Hadamard)**, letting the laws of physics compute the local derivatives directly on the chip.

---

## 2. Schematic Analysis: The $1\text{ k}\Omega / 3.9\text{ k}\Omega$ Vernier Attenuator

The uploaded schematic detail (`MCP6024T-I/SL-MS`, `U3$CBB15.1`) reveals the exact analog summing junction at each column output:

```
 COLTIA_j (From Matrix 33 Primary Payload)
       │
      [R1: 1.0 kΩ]
       │
       ├─── Node Pin 3 (+) ───[ U3: MCP6024T Buffer ]─── SUM_j (To ADC_49)
       │                              │         ▲
      [R2: 3.9 kΩ]                    └── Pin 2 ┘ (Unity Gain Follower)
       │
 COMP_IN_j (From Matrix 8 / Sigmoid 10 Correction)
```

### 2.1 The Mathematical Summing Superposition
The non-inverting input of op-amp buffer `U3` presents a high-impedance CMOS gate ($> 10^{12}\,\Omega$). Therefore, resistors $R_1$ ($1.0\text{ k}\Omega$) and $R_2$ ($3.9\text{ k}\Omega$) form a clean passive resistive divider / summer:

$$V_{\text{SUM\_j}} = \left( \frac{R_2}{R_1 + R_2} \right) V_{\text{COLTIA,j}} + \left( \frac{R_1}{R_1 + R_2} \right) V_{\text{COMP\_IN,j}}$$

Substituting the physical component values:

$$V_{\text{SUM\_j}} = \left( \frac{3.9\,\text{k}\Omega}{4.9\,\text{k}\Omega} \right) V_{\text{COLTIA,j}} + \left( \frac{1.0\,\text{k}\Omega}{4.9\,\text{k}\Omega} \right) V_{\text{COMP\_IN,j}} \approx 0.796 \cdot V_{\text{COLTIA,j}} + 0.204 \cdot V_{\text{COMP\_IN,j}}$$

### 2.2 Why This $1\text{ k}\Omega / 3.9\text{ k}\Omega$ Network is Crucial for ENOB
1. **Vernier Fine-Trimming Scale:**
   The compensation signal $V_{\text{COMP\_IN,j}}$ is attenuated by a factor of:
   $$\text{Atten}_{\text{comp}} = \frac{1.0}{4.9} \approx 0.204 \quad (\approx -13.8\text{ dB})$$
   Relative to the main payload ($0.796$), the compensation authority is $\frac{1.0}{3.9} \approx 0.256$ ($\approx \frac{1}{4}$ of payload scale).
   - This means a full $1\text{ LSB}$ step on the compensation weight DAC produces only a **$\approx 0.2\text{ LSB}$ fine adjustment** at `SUM_j`!
   - This gives the inner loop **fractional-LSB trimming capability**, allowing ENOB to climb far beyond the raw 8-bit DAC resolution limit.
2. **Noise & Ripple Suppression:**
   Any high-frequency switching noise, multiplexer charge injection, or parasitic DAC feedthrough from the $M_3 / M_8$ strata is immediately suppressed by $\approx 14\text{ dB}$ before reaching the `SUM_j` output buffer.
3. **Primary Payload Integrity:**
   The primary payload signal $V_{\text{COLTIA,j}}$ retains $\approx 80\%$ of its dynamic range (attenuated by only $-1.98\text{ dB}$), preserving high SNR.

---

## 3. Patent SE 2630397-4: Exact Gradient Mathematics

### 3.1 Output Error & Masked Loss Function (Equation 1)
For a stationary input vector $\mathbf{x}$, the T120 compares the ideal digital model target output $\mathbf{Z}_{\text{target}}$ against the physical analog reading $\mathbf{Z}_{\text{out}}$ from `ADC_49`:

$$Er_j^{(49)} = Z_{\text{target},j} - Z_{\text{out},j}^{(49)}$$

> [!IMPORTANT]
> **MASKED LOSS ENFORCEMENT:**
> Because Columns 2 and 3 are physically saturated at negative rails ($-1600\text{ to }-2048\text{ LSB}$), **THEY MUST BE EXCLUDED FROM THE LOSS FUNCTION**. Training against saturated rails produces an artificial $2000^2 = 4\times 10^6$ error that destroys the weights.
> Restrict Loss computation strictly to functional columns:
> $$\mathcal{L}_{\text{total}} = \frac{1}{2} \sum_{j \in \{0, 1, 4, 5\}} \left( Er_j^{(49)} \right)^2 \quad \text{(Equation 1 Masked)}$$

---

### 3.2 Layer 2 ($M_8$) Weight Gradient — Direct Hadamard Product (Equation 2)
When row $i$ of Matrix 8 is perturbed by the Hadamard carrier $V_i^{\text{PTU}}$, the 2T1C cell physically multiplies by the input present on its drain line. The demodulated Hadamard sensitivity at `ADC_49` is:

$$\left\langle \frac{\partial z_j^{(49)}}{\partial W_{i,j}^{(8)}} \right\rangle_{\text{Hadamard}} = \sigma_2'\!\left(y_j^{(8)}\right) \cdot x_i^{(8)}$$

Consequently, the exact weight gradient for Matrix 8 is simply:

$$\boxed{\frac{\partial \mathcal{L}_{\text{total}}}{\partial W_{i,j}^{(8)}} = \left\langle \frac{\partial z_j^{(49)}}{\partial V_i^{\text{PTU}(5)}} \right\rangle_{\text{Hadamard}} \cdot Er_j^{(49)}} \quad \text{(Equation 2)}$$

*Notice: NO multiplication by $x_i^{(8)}$! NO analytical sigmoid derivative $\sigma_2'$ calculation needed for $M_8$!*

---

### 3.3 Carrier Wave Search: Isolating Column Slope $\sigma_2'(y_j^{(8)})$ (Equations 5 & 6)
To back-propagate sensitivity from Layer 2 ($M_8$) to Layer 1 ($M_3$), the controller needs the local error $\partial x_i^{(8)}$. By the chain rule, this requires the column throttle factor $\sigma_2'(y_j^{(8)})$.

Because $\sigma_2'(y_j^{(8)})$ is a column property (identical for all rows $i$ in column $j$), the patent specifies the **Carrier Wave Search**:

1. **Find Strongest Row $k$ (Carrier Wave):**
   Inspect the intermediate activations from `ADC_45`:
   $$k = \arg\max_{i \in \{0..5\}} \left| x_i^{(8)} \right|$$
   Row $k$ provides the maximum physical signal-to-noise ratio through Matrix 8.
2. **Regularized Inverse Scaling (Equation 6):**
   Extract column $j$'s activation slope by dividing row $k$'s Hadamard response by $x_k^{(8)}$ with Tikhonov regularization $\alpha$:
   $$\boxed{\sigma_2'\!\left(y_j^{(8)}\right) \approx \frac{x_k^{(8)}}{\left(x_k^{(8)}\right)^2 + \alpha} \cdot \left\langle \frac{\partial z_j^{(49)}}{\partial W_{k,j}^{(8)}} \right\rangle_{\text{Hadamard}}} \quad \text{(Equation 6)}$$

*Note on Jumper Mode:* When the jumper is set to `Bypass second sigmoid` (Linear Layer 2), $\sigma_2'(y_j^{(8)}) \equiv 1.0$.

---

### 3.4 Row Sensitivity Receipt $\partial x_i^{(8)}$ to Layer 1 (Equation 4)
Using the digital shadow register of the Matrix 8 weights $W_{i,j}^{(8)\text{digital}}$:

$$\boxed{\partial x_i^{(8)} = \sum_{j \in \{0, 1, 4, 5\}} W_{i,j}^{(8)\text{digital}} \cdot \sigma_2'\!\left(y_j^{(8)}\right) \cdot Er_j^{(49)}} \quad \text{(Equation 4)}$$

---

### 3.5 Layer 1 ($M_3$) Weight Gradient — Direct Hadamard Product (Equation 7)
Demodulated sensitivity measured at `ADC_45` during Matrix 3 perturbation already contains the physical multiplication by primary input $x_i^{(3)}$ (`DAC_2`) and the physical slope $\sigma_1'$ of the first sigmoid:

$$\boxed{\frac{\partial \mathcal{L}_{\text{total}}}{\partial W_{i,j}^{(3)}} = \left\langle \frac{\partial z_j^{(45)}}{\partial V_i^{\text{PTU}(5)}} \right\rangle_{\text{Hadamard}} \cdot \partial x_j^{(8)}} \quad \text{(Equation 7)}$$

*Notice: NEVER multiply Equation 7 by input $x_i^{(3)}$ or an analytical $\tanh'$!*

---

## 4. Phase-by-Phase Roadmap for Argon AI Agent

### Phase 1: Mode A Baseline & Center Verification (Do NOT Train Yet!)
1. **Slut Jumpern (Mode A ansluten):**
   Hardware config: `jumper_mode = 2` (or Mode A active).
2. **Centrera Alla Kompensationsvikter:**
   Set all weights in $M_3$ ($8\times 6$) and $M_8$ ($7\times 6$) to digital center `128` (differential weight $0.0$).
3. **Mät Baseline & Initial ENOB vid $t = 5.0\text{ ms}$:**
   - Verify that `COLTIA1` signals pass through the $1\text{ k}\Omega / 3.9\text{ k}\Omega$ network cleanly to `ADC_49`.
   - Measure initial quiescent error and record baseline ENOB.
   - Run a quick gain map of Matrix 33 in Mode A with centered weights to confirm that the $1\text{k}/3.9\text{k}$ attenuator reduces the raw swing from $\pm 600\text{ mV}$ to $\approx \pm 480\text{ mV}$ ($\approx 0.8\times$) as predicted by theory.

### Phase 2: Single-Time-Point ($t = 5.0\text{ ms}$) Inner Loop Training
1. **Lås Snapshot & Hadamard till $5.0\text{ ms}$:**
   - Configure `hadamard_delay_us = 5000` (5.0 ms after the 100 Hz refresh pulse).
   - *Do not spread out across multiple time points yet!* Keep everything strictly locked to $t = 5.0\text{ ms}$.
2. **Kör Endast Inner Loop (Ingen MAML Outer Loop Än):**
   - Set `w_hid_mag = 0` and `trim_hid_mag = 0` (no outer loop meta-hopping, no basin hopping).
   - Set learning rate conservatively: $\alpha_{\text{inner}} \approx 0.005\text{ to }0.01$.
   - Inner loop steps: $N = 50\text{ to }100$ iterations.
3. **Verifiera Konvergens & ENOB-Tillväxt:**
   - Watch the masked loss: does $\mathcal{L}$ decline monotonically?
   - Watch ENOB: does it slowly climb (e.g. from 3–4 bits up toward 6–8 bits)?
   - If loss increases or oscillates violently, reduce $\alpha_{\text{inner}}$ by $2\times$ and check gradient signs.

### Phase 3 (Milstolpe 2 — Senare): Full Inverted MAML & Tidsspridning
- Endast när Phase 2 konvergerar stabilt och reproducerbart kopplar vi på Outer Loop meta-träning (`w_hid_mag > 0`) och tidsdifferentierad kompensation över hela $0\text{--}9.5\text{ ms}$ cykeln.

---

## 5. Review Checklist for Argon AI Agent

| Check | Requirement | Verification Command / Check |
| :--- | :--- | :--- |
| **Hadamard Delay** | Locked strictly to $5000\ \mu\text{s}$ ($5.0\text{ ms}$) | `client.set_config(..., hadamard_delay_us=5000)` |
| **MAML Outer Loop** | Disabled for Phase 1 (`w_hid_mag = 0`) | Verify `g_hid_amp_dac == 0` |
| **Compensation Zeroing**| $M_3$ and $M_8$ initialized to center $128$ | `client.center_compensation_weights()` |
| **Masked Columns** | Columns 2 and 3 EXCLUDED from loss & gradients | `mask = [0, 1, 4, 5]` |
| **$M_8$ Gradient** | `grad_M8 = hadamard_M8 * error_49` | **NO** $x_i^{(8)}$ multiplication! |
| **Carrier Row** | $k = \arg\max_i |x_i^{(8)}|$ on `ADC_45` | Protect with Tikhonov $\alpha$ |
| **$M_3$ Gradient** | `grad_M3 = hadamard_M3 * dx8` | **NO** $x_i^{(3)}$ or $\tanh'$ multiplication! |
| **Attenuator Check** | Compensation authority $\approx 20.4\%$ of output | Confirm Vernier trim scaling |

