# Technical Specification: Post-Analog $\alpha/\beta$ Calibration Stage & 8-Channel FHP Integration

**Architecture:** Inverted MAML Analog In-Memory Computing (Patent Pending `SE 2630397-4`)  
**Target Hardware:** PCBA v1.3.2 (`Trion T120` Master SoC + `Trion T20` Coprocessor) $\to$ `SKY130` 130 nm CMOS ASIC  
**Objective:** Achieve 8-bit effective output precision via 4+4-bit bit-slicing without digital post-calibration ($\alpha$-gain / $\beta$-offset DSP) after `ADC_49`.

---

## 1. Architectural Rationale & System Goal

### 1.1 Eliminating Digital Post-Processing for 8-Bit Bit-Slicing
To reconstruct an 8-bit matrix-vector product from two sequential 4-bit analog passes (MSB `[7:4]` and LSB `[3:0]`) using pure binary shift-and-add logic:

$$Y_{8\text{-bit}} = (Y_{\text{MSB}} \ll 4) + Y_{\text{LSB}}$$

every physical column entering `ADC_49` (`XC2361A`) must exhibit **zero static DC offset** ($\beta = 0$) and **identical linear conversion gain** ($\alpha = 1.000$). Any mismatch in $\alpha$ or $\beta$ across columns or between MSB/LSB cycles introduces Differential Non-Linearity (DNL) discontinuities at nibble roll-over boundaries.

Instead of spending digital DSP multipliers and adders after `ADC_49`, static DC offset ($\beta$) and linear column gain ($\alpha$) are corrected **post-analogously** immediately prior to `ADC_49` using the same asymmetric paradigm as the core Inverted MAML triad:
* **Full analog bandwidth** in the primary signal path ($< 2.0\ \mu\text{s}$ settling time).
* **Low-bandwidth closed-loop regulation** on the analog trim controls, driven by Forward Hadamard Propagation (FHP).

### 1.2 Decoupling Coarse Linear Errors from Fine Non-Linear Vernier Compensation
In uncompensated standalone operation (`Matrix 33`), column DC offsets vary by $> 1000\ \text{LSB}$ and linear gains diverge across columns. Moving $\alpha$ and $\beta$ correction to a dedicated post-analog stage frees the `Matrix 3` $\to$ `Sigmoid 4` $\to$ `Matrix 8` Vernier branch from absorbing large static DC currents. This allows a strong passive attenuation ratio (e.g., $1\ \text{k}\Omega / 3.3\ \text{k}\Omega$) at summing junction `SUM35`, dedicating the full dynamic range of `Matrix 3/8` to canceling second-order MOS triode distortion ($-0.5 V_{ds}^2$) and localized thermal gradients.

---

## 2. Post-Analog $\alpha/\beta$ Circuit Topology (`SUM35` Interface)

### 2.1 Single-Stage Inverting Op-Amp with T-Network Shunt Triode
For a $3.3\text{ V}$ single-supply system centered at virtual ground $V_{\text{ref}} = 1.65\text{ V}$, each column channel after `SUM35` uses a single inverting `MCP6024T` op-amp ($10\text{ MHz}$ GBW) configured with a resistive T-network and a shunt N-MOSFET (`BSS138` or `DMN2075U`) operating in the deep triode region.

Because the MOSFET is placed in **shunt** to $V_{\text{ref}}$ rather than in **series** with the signal path, the main column current flows through precision passive resistors ($R_1, R_2$), preserving full op-amp bandwidth and keeping drain-source swing $V_{ds}$ below $5\text{ mV}$.

```text
In 1: V_sig ────[ R1: 4.7k ]────┬────[ R2: 4.7k ]────┬────────[ Rf: 10k ]────────┬── Out: V_out
(from SUM35)                     │                    │                           │   (to ADC_49)
                              [ Rs ]                  │      ┌─────────────┐      │
                                 │                    ├──────┤ -           │      │
                                 ├─ Drain             │      │  MCP6024T   ├──────┘
In 2: V_gain ────(AC C_ptu)──────┤  N-MOSFET          │   ┌──┤ +           │
(8-bit R-2R DAC)                 │  (Triode VCR)      │   │  └─────────────┘
                                 ├─ Source            │   │
                                 │                    │   │
V_ref (1.65V) ───────────────────┴────────────────────│───┘
                                                      │
In 3: V_offset ──(AC C_ptu)────[ R_off: 22k ]─────────┘
(8-bit R-2R DAC)
```

### 2.2 Transfer Function & Component Dimensioning
With $R_1 = 4.7\ \text{k}\Omega$, $R_2 = 4.7\ \text{k}\Omega$, $R_f = 10\ \text{k}\Omega$, and $R_{\text{off}} = 22\ \text{k}\Omega$, the output voltage relative to $V_{\text{ref}} = 1.65\text{ V}$ is:

$$V_{\text{out}} = 1.65\text{ V} - G(V_{\text{gain}}) \cdot (V_{\text{sig}} - 1.65\text{ V}) - \frac{R_f}{R_{\text{off}}} \cdot (V_{\text{offset}} - 1.65\text{ V})$$

where the closed-loop signal gain $G(V_{\text{gain}})$ is governed by the T-network equivalent input resistance:

$$G(V_{\text{gain}}) = \frac{R_f}{R_1 + R_2 + \frac{R_1 R_2}{R_s + R_{ds}(V_{\text{gain}})}}$$

Select the shunt series resistor $R_s$ according to the desired trim span (assuming $R_{ds,\text{on}} \approx 200\ \Omega$):

| Target Trim Span | Shunt Resistor ($R_s$) | Max Gain (FET Off) | Min Gain (FET On) | Effective Span | Max $V_{ds}$ at $1\text{ V}$ Swing |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **$\approx 1/10$ ($9.6\%$)** | $22\ \text{k}\Omega$ | $1.064\times$ | $0.962\times$ | $9.6\%$ | $4.1\ \text{mV}$ |
| **$\approx 1/20$ ($4.7\%$)** | $47\ \text{k}\Omega$ | $1.064\times$ | $1.013\times$ | $4.7\%$ | $2.0\ \text{mV}$ |

* **Linearity Guarantee:** Because $R_s \gg R_{ds}$, over $99\%$ of the shunt voltage drops across the passive resistor $R_s$, restricting transistor $V_{ds}$ to $\le 4.1\ \text{mV}$. Since the quadratic triode non-linearity scales with $V_{ds}^2$, harmonic distortion is suppressed by $> 600\times$ compared to a series MOSFET.
* **Offset Range ($\beta$):** With $R_{\text{off}} = 22\ \text{k}\Omega$ and $R_f = 10\ \text{k}\Omega$, a $0\text{ V}$ to $3.3\text{ V}$ swing on `V_offset` shifts `V_out` by $\pm 0.75\text{ V}$ around $1.65\text{ V}$ ($\approx 5.9\ \text{mV}$ per 8-bit DAC LSB, with mid-scale code `128` = $1.65\text{ V}$ = zero offset current).
* **Gate Drive Mapping ($\alpha$):** Since the N-MOSFET Source is fixed at $V_{\text{ref}} = 1.65\text{ V}$, channel conduction begins at $V_{\text{gate}} = 1.65\text{ V} + V_{th}$ ($\approx 2.2\text{ V}$ to $2.5\text{ V}$). Use a resistive divider between $3.3\text{ V}$ and the `V_gain` R-2R DAC output to map the full $0\text{–}3.3\text{ V}$ DAC range into $[2.15\text{ V}, 3.30\text{ V}]$ at the Gate, maximizing 8-bit trim resolution.

---

## 3. Closed-Loop Control via 8-Channel Forward Hadamard Propagation (FHP)

Even if the shunt triode exhibits residual non-linearity or thermal drift in $V_{th}(T)$, the system treats the entire post-analog stage as part of the unknown physical plant inside the FHP loop.

### 3.1 Expansion from 12-Pulse ($6\times 6$) to 16-Pulse ($8\times 8$) Hadamard Burst
To calibrate the 6 matrix rows plus the 2 post-analog controls ($\alpha$ and $\beta$) simultaneously in $O(1)$ time without cross-talk, expand the contiguous Hadamard burst on `Trion T20` from $2 \times 6 = 12$ pulses ($24.00\ \mu\text{s}$) to **$2 \times 8 = 16$ pulses ($32.00\ \mu\text{s}$ at $2.00\ \mu\text{s}$/pulse)**:

| Hadamard Channel | Physical Target Node | Extracted Partial Derivative at `ADC_49` | Control Loop Action |
| :--- | :--- | :--- | :--- |
| **Ch 0 – Ch 5** | Matrix rows `PL1` .. `PL6` | $\frac{\partial Y_j}{\partial V_{\text{PTU}, r}}$ ($r \in [0..5]$) | Updates `Matrix 3` & `Matrix 8` Vernier weights |
| **Ch 6** | AC-coupled to `Gain-FET Gate` | $\frac{\partial Y_j}{\partial V_{\text{gain}, j}}$ | Updates `V_gain` DAC to lock $\alpha_j = 1.000$ |
| **Ch 7** | AC-coupled to `Offset` summing node | $\frac{\partial Y_j}{\partial V_{\text{offset}, j}}$ | Updates `V_offset` DAC to lock $\beta_j = 0$ |

### 3.2 Natural Physical Orthogonality Between $\alpha$ and $\beta$
1. **Offset Perturbation (`Ch 7`):** Injecting a small AC square wave via $C_{\text{PTU}}$ into the `V_offset` resistor produces a constant AC response at `ADC_49` regardless of the instantaneous matrix input vector $X$.
2. **Gain Perturbation (`Ch 6`):** Modulating the `Gain-FET Gate` modulates channel conductance $g_{ds}$, which naturally multiplies the active column signal amplitude $(V_{\text{sig}} - 1.65\text{ V})$ inside the physical transistor:

$$\left\langle \frac{\partial Y_j^{(49)}}{\partial V_{\text{gain}, j}^{\text{PTU}}} \right\rangle_{\text{Hadamard}} \propto (V_{\text{sig}, j} - 1.65\text{ V})$$

Consequently, when a column output is near zero, the demodulated gain gradient automatically vanishes, preventing the $\alpha$-loop from falsely reacting to pure DC offset errors.

### 3.3 Hierarchical Loop Cooperation with L2 Weight Decay
The firmware SGD update rule for `Matrix 8` already includes L2 regularization ($\lambda \cdot W_8$), which acts as a restoring spring toward zero:
* **Fast/Medium Loop (`Matrix 3/8`):** Immediately cancels high-frequency non-linearities and rapid thermal transients.
* **Slow Loop (`V_gain`, `V_offset`):** Integrates persistent column gain and DC offset errors using a smaller learning rate ($\eta_{\alpha,\beta} \ll \eta_{W8}$). As `V_gain` and `V_offset` absorb the static baseline error, the L2 restoring force automatically relaxes the DC component of $W_8$ back toward $0\ \text{LSB}$, preserving maximum headroom in the Vernier branch.

---

## 4. ASIC Migration Note (`SKY130` 130 nm CMOS)
When migrating from `PCBA v1.3.2` to a monolithic `SKY130` tile:
* The `V_offset` trim is implemented via a compact 6-bit current-steering DAC or R-2R poly-resistor ladder sinking/sourcing $\pm 5\ \mu\text{A}$ into the `ColTIA` virtual ground ($1.65\text{ V}$).
* The T-network shunt MOSFET can either use a long-channel `sky130_fd_pr__nfet_g5v0d10v5` device or be replaced by a 5-bit binary-weighted poly-resistor bank switched on the $V_{\text{ref}} = 1.65\text{ V}$ side via CMOS transmission gates for zero static power and pure passive linearity.

---

## 5. Implementation Checklist for AI Agent
When processing this specification, execute the following tasks according to the active target domain:
1. **RTL (`Trion T120` / `T20` SystemVerilog):** Extend `t120_hbus_seq.sv` and `t20_hbus_rx.sv` from 12-word ($2\times 6$) to 16-word ($2\times 8$) contiguous Walsh-Hadamard tables (`H8` positive + `H8` complementary negative, plus termination word `0x8000` at $t = 32.00\ \mu\text{s}$), mapping bits `6` and `7` to dedicated `PL_GAIN` and `PL_OFFSET` pins.
2. **Firmware (`T120` RISC-V C):** Expand the Fast Hadamard Transform (FHT) demodulator from $6\times 6$ to $8\times 6$ to extract `grad_gain[0..5]` and `grad_offset[0..5]` per column, and add slow-loop SGD integrators driving the 12 auxiliary `V_gain` and `V_offset` DAC channels.
3. **SPICE / Verification:** Simulate the T-network stage (`MCP6024T`, $R_1=R_2=4.7\ \text{k}\Omega$, $R_f=10\ \text{k}\Omega$, $R_s=22\ \text{k}\Omega$, $R_{\text{off}}=22\ \text{k}\Omega$) across $V_{\text{sig}} \in [0.65\text{ V}, 2.65\text{ V}]$ to verify $< 2.0\ \mu\text{s}$ step settling and $< -70\ \text{dB}$ THD.