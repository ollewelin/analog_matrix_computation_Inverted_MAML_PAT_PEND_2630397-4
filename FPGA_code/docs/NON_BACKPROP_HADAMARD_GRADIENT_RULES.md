# CRITICAL MATHEMATICAL SPECIFICATION: Forward Hadamard Gradient Extraction (NOT Standard Digital Backpropagation)

> [!CAUTION]
> **MANDATORY RULE FOR ALL IMPLEMENTATION AGENTS:**
> **DO NOT IMPLEMENT STANDARD DIGITAL BACKPROPAGATION ($\frac{\partial L}{\partial W_{i,j}} = \delta_j \cdot x_i$).**
> In the Inverted MAML Analog In-Memory Computing (AIMC) hardware (Patent Application SE 2630397-4), the forward Hadamard perturbation (`V_PTU`, Ref `5`) is physically injected onto the 2T1C cell gate while the analog input signal $x_i$ is present on the transistor channel. Because the analog crosspoint transistor acts as a physical multiplier ($I_{\text{out}} \propto g_m \cdot V_{gs} \cdot V_{ds}$), **the multiplication by input $x_i$ has ALREADY occurred inside the analog physics** during the forward Hadamard correlation.
>
> **Multiplying the demodulated Hadamard sensitivity by input $x_i$ a second time in digital firmware/software squares the input ($x_i^2$), corrupts the gradient sign and magnitude, and destroys training convergence.**

---

## 1. Architectural Context & Patent Reference Numerals

The hardware comprises an **Atomic Triad** of three coupled analog 2T1C crosspoint matrices controlled by a digital unit (`Ref 9`: Trion T120 Master SoC + Trion T20 Gate/Hadamard Node):

| Patent Ref | Hardware Element | Role in Forward & Gradient Path |
|:---|:---|:---|
| **`1`** | Digital Input Vector $\mathbf{x}$ | Stationary input data pattern (generated as 100% white noise inside T120 during training/calibration). |
| **`2`** | Input Row DAC Bank (`DAC_2`, 6 ch) | Converts digital input $\mathbf{x}$ into analog row voltages feeding both Primary Matrix `33` and Correction Matrix `3`. |
| **`33`** | Primary Payload Matrix ($M_{33}$) | Holds deterministic target weights (`Ref 34`, bank `W_34`) from the ideal digital model (`Ref 39`). Unperturbed during Hadamard measurement. |
| **`3`** | First Correction Matrix ($M_3$, Layer 1) | 8 rows $\times$ 6 cols (`W_15` bank). Upper region (`Ref 30`) holds fast-decay reference cells (`Ref 29`, $\tau_{\text{fast}} = 33\text{ ms}$); lower region (`Ref 37`) holds slow-decay compute cells (`Ref 27`, $\tau_{\text{slow}} = 100\text{ ms}$). |
| **`4`** | First Analog Activation ($\sigma_1$) | Non-linear analog Sigmoid / $\tanh$ stage at the column outputs of Matrix `3`. |
| **`45`** | Intermediate ADC Bank (`ADC_45`, 6 ch) | `XC2361A` SAR ADCs measuring the output of Layer 1 ($\mathbf{z}^{(45)} = \mathbf{x}^{(8)}$), which serves as the row input into Matrix `8`. |
| **`8`** | Second Correction Matrix ($M_8$, Layer 2) | 7 rows $\times$ 6 cols (`W_12` bank). Receives $\mathbf{x}^{(8)}$ from activation stage `4` (`ADC_45`). |
| **`10`** | Second Analog Activation ($\sigma_2$) | Configurable via physical board jumper: (1) `OFF` (no compensation), (2) `Bypass second sigmoid` (linear Layer 2 output), or (3) `Use second sigmoid layer`. |
| **`35`** | Analog Summing Junction | Sums the primary payload output ($M_{33}\mathbf{x}$) with the correction output from Matrix `8` / Activation `10`. |
| **`49`** | Final Output ADC Bank (`ADC_49`, 6 ch) | `XC2361A` SAR ADCs measuring the total summed analog output $\mathbf{z}^{(49)}$ (`Ref 11`). |
| **`5, 6, 7`** | Hadamard Perturbation Unit ($V_{\text{PTU}}$) | Differential pins `H_M3_P/N[1..8]` and `H_M8_P/N[1..7]` on T20 inject zero-DC orthogonal Walsh-Hadamard sequences (`Ref 43`) through small coupling capacitors $C_{\text{PTU}} \ll C_W$ (`Ref 7`) onto the 2T1C storage nodes (`Ref 44`). |
| **`36, 38`** | Matrix Supply $V_{\text{DD}}$ & `trim-DAC` | Controllable global supply/bias shift (`Ref 38`) used during Base Model Training (`Ref 40/41`) to emulate global thermal/voltage drift. |
| **`40`** | Base Model Outer Loop (Inverted MAML) | Meta-optimization loop that updates initial base weights $W_0$ across emulated hardware offset states using the **dot-product second-derivative approximation**. |
| **`41`** | Base Model Inner Loop | Fast task-adaptation loop ($N$ steps, default $N=100$) under a fixed emulated hidden offset state. |
| **`42`** | Operational Inference Mode | Live physical drift compensation mode with all artificial hidden offsets zeroed/centered. |

---

## 2. Two-Step Isolated Perturbation Protocol

Because Matrix `3` (Layer 1) feeds into Matrix `8` (Layer 2) in series, **perturbing both matrices simultaneously causes cross-modulation distortion** that violates Hadamard orthogonality. Therefore, each short measurement window (`Ref 20, 24`) is divided into **two strictly isolated sub-windows** while the input vector $\mathbf{x}$ (`Ref 1`) is held completely stationary:

1. **Sub-Window A — Perturb Matrix `8` Only ($M_3$ Quiet):**
   - `H_M3_P/N` are held quiet (constant common-mode).
   - `H_M8_P/N` are driven with a permuted 16-cycle Walsh-Hadamard sequence (`Ref 43`).
   - `ADC_49` (`Ref 49`) samples the 6 column outputs at every Hadamard chip (`2 µs` default = `500 kHz`).
   - Simultaneously, `ADC_45` (`Ref 45`) reads the unperturbed stationary intermediate vector $\mathbf{x}^{(8)} = [x_1^{(8)}, \dots, x_6^{(8)}]^T$.
   - The Fast Walsh-Hadamard Transform (FWHT) demodulates `ADC_49` readings into the direct physical sensitivity matrix:
     $$\left\langle \frac{\partial z_j^{(49)}}{\partial V_i^{\text{PTU}(5)}} \right\rangle_{\text{Hadamard}} \equiv \left\langle \frac{\partial z_j^{(49)}}{\partial W_{i,j}^{(8)}} \right\rangle_{\text{Hadamard}}$$

2. **Sub-Window B — Perturb Matrix `3` Only ($M_8$ Quiet):**
   - `H_M8_P/N` are held quiet.
   - `H_M3_P/N` are driven with a permuted 16-cycle Walsh-Hadamard sequence.
   - `ADC_45` (`Ref 45`) samples the 6 intermediate column outputs at every Hadamard chip.
   - The FWHT demodulates `ADC_45` readings into Layer 1's direct physical sensitivity matrix (which naturally includes the analog derivative of Sigmoid `4`):
     $$\left\langle \frac{\partial z_j^{(45)}}{\partial V_i^{\text{PTU}(5)}} \right\rangle_{\text{Hadamard}}$$

### 2.1 Critical Per-State Timing Sequence (Preventing "Earthquake" Switching Noise)
To prevent digital switching transients, ground bounce, and op-amp ringing ("earthquake noise") from corrupting the analog measurements, **every individual Hadamard table state MUST execute in four strictly non-overlapping phases**:
1. **Shift & Latch First:** T120 shifts the 16-bit Hadamard word over the H-bus to T20, and T20 latches the new Hadamard state onto `H_M3_P/N` or `H_M8_P/N`.
2. **Quiet Analog DC Settling ($\approx 2.0\,\mu\text{s}$ at default `500 kHz`, scaling up to $20.0\,\mu\text{s}$ at `50 kHz`):** All digital buses (`H-bus`, `S-bus`, `DAC_SCK`, `ADC_SCK`) remain **100% quiet/static** while the analog matrix (`2T1C` cells, `MCP6024T` TIAs, and Sigmoids `4` & `10`) settles into a steady **DC state** over the $\approx 2\,\mu\text{s}$ window.
3. **ADC Sample-and-Hold & Store (At the END of the $\approx 2\,\mu\text{s}$ Settling Window):** Right at the end of the quiet settling window, `ADC_45_CONV` / `ADC_49_CONV` are asserted to lock the `XC2361A` Sample-and-Hold (S/H) capacitors on the settled DC voltage, and the digitized values are shifted out and stored in T120 RAM.
4. **Next Hadamard State After ADC Read Completes:** Only **after** the ADC Sample-and-Hold conversion and readout to T120 are completely finished does T120 shift and trigger the next state in the Hadamard table.

### 2.2 Full Differential `(+/-)` Symmetry & Efinix 3-State (`Data` + `OE`) Hadamard Centering
Every analog signal path on the PCB is designed with **full differential `(+/-)` symmetry** referenced around the virtual analog ground `VR = 1.65V`:
1. **3-Stated Differential Hadamard Outputs (`H_M3_P/N[1..8]`, `H_M8_P/N[1..7]` on T20):**
   - **Active Hadamard Table (`vec[15] == 0` and `en_mask[k] == 1`):** Output Enable is asserted (`OE = 1`), driving complementary `+` / `-` states (`P = 1, N = 0` for `+1`; `P = 0, N = 1` for `-1`).
   - **Leaving the Hadamard Table (`vec[15] == 1`), Quiet Matrix, or Reset:** Output Enable is deasserted (`OE = 0`, High-Impedance `Hi-Z` with `pull_option="none"`). Both `H+` and `H-` immediately float at the analog mid-point (`VR = 1.65V`), ensuring the Hadamard permutation is **100% centered with zero DC bias** outside the active 16-state table. To exit a 16-state Hadamard sweep cleanly, T120 appends a 17th trailing H-bus word `16'h8000` (`vec[15] = 1`) that immediately places all 30 Hadamard pins into `Hi-Z`.
   - **Efinix Trion 3-State Implementation Rule:** In Efinix synthesis, **never assign `'z` in SystemVerilog/Verilog RTL**. Instead, configure each pin in `T20F256.peri.xml` as `mode="inout"` with `<efxpt:input_config name="" pull_option="none"/>`, `<efxpt:output_config name="<PIN>"/>`, and `<efxpt:output_enable_config name="<PIN>_OE"/>`, exposing two separate top-level ports (`output <PIN>` for data and `output <PIN>_OE` for active-high output enable).
2. **Differential Dual-2T1C Cells (`2X_2T1C`) & Differential Column Refresh Gates (`G_P1..6_MAT_m`, `G_N1..6_MAT_m`):**
   - Each crosspoint cell contains a positive half-cell (`MULTIPLYER (+)`: `W+`, `G+`, `H+`, `OUT_COL+`) and a negative half-cell (`MULTIPLYER (-)`: `W-`, `G-`, `H-`, `OUT_COL-`).
   - Charging a signed weight $w_{i,j} \in [-127, +127]$ onto column $j$ of matrix $m \in \{3, 8, 33\}$ requires driving the row weight DACs with $W^+ = 128 + w_{i,j}$ while pulsing positive gate `G_Pj_MAT_m`, and driving $W^- = 128 - w_{i,j}$ while pulsing negative gate `G_Nj_MAT_m`. Setting a weight to zero ("Center Weights") charges both $W^+$ and $W^-$ to `128` (`1.65V`).
3. **Differential Bipolar DACs (`74HC595` 8-bit R-2R, `0..255`):**
   - Mid-scale code `128` corresponds to `VR = 1.65V` (zero differential drive). Signed digital value $= \text{code} - 128 \in [-128, +127]$.
4. **Differential Bipolar ADCs (`XC2361A` 12-bit SAR, `ADC_45` & `ADC_49`, `0..4095`):**
   - Each column's differential currents (`OUT_COL+` and `OUT_COL-`) are subtracted by a differential instrumentation TIA (`MCP6024T`) biased around `VR = 1.65V`. Mid-scale ADC code `2048` represents `0.0V` differential (`1.65V` single-ended); signed digital reading $= \text{raw\_adc} - 2048 \in [-2048, +2047]$.

---

## 3. Exact Non-Backpropagation Gradient Equations (`maml_eng.txt`)

### 3.1 Output Error & Loss Function (Equation 1)
For a known stationary white-noise input vector $\mathbf{x}$, the T120 computes the ideal digital target output $\mathbf{Z}_{\text{target}}$ from the reference digital model (`Ref 39`) and compares it against the physical analog measurement $\mathbf{Z}_{\text{out}}$ at `ADC_49`:

$$Er_j^{(49)} = Z_{\text{target}, j} - Z_{\text{out}, j}^{(49)}$$

$$L_{\text{total}} = \frac{1}{2} \sum_j \left( Er_j^{(49)} \right)^2 \quad \text{(Equation 1)}$$

---

### 3.2 Layer 2 ($M_8$) Weight Gradient — Direct Hadamard Error Product (Equation 2)
When row $i$ of Matrix `8` is perturbed by $V_i^{\text{PTU}(5)}$, the 2T1C cell at $(i, j)$ physically modulates its output current by $\Delta I_{i,j} \propto \Delta V_{gs, i} \cdot x_i^{(8)}$. Passing through column activation `10` ($\sigma_2$), the demodulated Hadamard sensitivity measured at `ADC_49` is **already**:

$$\left\langle \frac{\partial z_j^{(49)}}{\partial W_{i,j}^{(8)}} \right\rangle_{\text{Hadamard}} = \sigma_2'\!\left(y_j^{(8)}\right) \cdot x_i^{(8)} \quad \text{(Equation 5a)}$$

Consequently, the exact weight gradient for Matrix `8` (`Equation 2` in `maml_eng.txt`) is simply the product of the demodulated Hadamard reading and the output error:

$$\boxed{\frac{\partial L_{\text{total}}}{\partial W_{i,j}^{(8)}} = \left\langle \frac{\partial z_j^{(49)}}{\partial V_i^{\text{PTU}(5)}} \right\rangle_{\text{Hadamard}} \cdot Er_j^{(49)}} \quad \text{(Equation 2)}$$

> [!IMPORTANT]
> **Notice what is NOT in Equation 2:**
> - There is **NO digital multiplication by $x_i^{(8)}$** (already performed by the 2T1C FET in hardware).
> - There is **NO analytical calculation of $\sigma_2'(y_j^{(8)})$** needed for $M_8$ updates (already included in the `ADC_49` perturbation response).

---

### 3.3 Carrier Wave Search & Regularized Inverse Scaling for $\sigma_2'(y_j^{(8)})$ (Equations 5 & 6)
To propagate error sensitivity back to Matrix `3` (Layer 1), the digital controller needs the local error at the input of Matrix `8` ($\partial x_i^{(8)}$). By the chain rule (`Equation 4`), this requires knowing how much each column $j$ of Matrix `8` is currently throttled by the second non-linear activation function $\sigma_2'(y_j^{(8)})$ (`Ref 10`).

However, the hardware only measures the *combined* product $\left\langle \frac{\partial z_j^{(49)}}{\partial W_{i,j}^{(8)}} \right\rangle_{\text{Hadamard}} = \sigma_2'(y_j^{(8)}) \cdot x_i^{(8)}$ (`Equation 5a`). Notice that **$\sigma_2'(y_j^{(8)})$ is a column property** (identical for all rows $i$ in column $j$).

To isolate $\sigma_2'(y_j^{(8)})$ with maximum signal-to-noise ratio and zero division-by-zero risk:

1. **Step 1 — Carrier Wave Search (Find Strongest Row $k$):**
   Inspect the stationary intermediate ADC readings $x_i^{(8)}$ from `ADC_45` (`Ref 45`) and select the row index $k$ with the largest absolute signal amplitude:
   $$k = \arg\max_{i \in \{1..6\}} \left| x_i^{(8)} \right|$$
   Row $k$ acts as the **strongest physical carrier wave** through Matrix `8`.

2. **Step 2 — Regularized Inverse Scaling (Equation 6):**
   For each column $j \in \{1..6\}$, extract the pure activation slope $\sigma_2'(y_j^{(8)})$ by dividing column $j$'s Hadamard sensitivity on carrier row $k$ by $x_k^{(8)}$ using Tikhonov regularization ($\alpha \approx 10^{-5}$ in normalized units, or $\sim 1\text{ LSB}^2$ in fixed-point):

   $$\boxed{\sigma_2'\!\left(y_j^{(8)}\right) \approx \frac{x_k^{(8)}}{\left(x_k^{(8)}\right)^2 + \alpha} \cdot \left\langle \frac{\partial z_j^{(49)}}{\partial W_{k,j}^{(8)}} \right\rangle_{\text{Hadamard}}} \quad \text{(Equation 6)}$$

   - *Jumper Mode Note:* When the physical analog jumper is set to **Mode 2 (`Bypass second sigmoid` / Linear Layer 2)**, $\sigma_2'(y_j^{(8)})$ is physically constant ($= 1$), which can either be verified via Equation 6 as a diagnostic or locked to $1.0$ in firmware.

---

### 3.4 Row Sensitivity Receipt $\partial x_i^{(8)}$ Back to Layer 1 (Equation 4)
Once $\sigma_2'(y_j^{(8)})$ is known for each column $j$, the error sensitivity with respect to each output channel $i$ of Layer 1 (`ADC_45`) is computed in the digital controller using its shadow register of the Matrix `8` weights $W_{i,j}^{(8)\text{digital}}$ (`Equation 4`):

$$\boxed{\partial x_i^{(8)} = \sum_{j=1}^{n} W_{i,j}^{(8)\text{digital}} \cdot \sigma_2'\!\left(y_j^{(8)}\right) \cdot Er_j^{(49)}} \quad \text{(Equation 4)}$$

---

### 3.5 Layer 1 ($M_3$) Weight Gradient — Direct Hadamard Product (Equation 7)
During Sub-Window B (perturbing Matrix `3` while monitoring `ADC_45`), the demodulated Hadamard sensitivity $\left\langle \frac{\partial z_j^{(45)}}{\partial V_i^{\text{PTU}(5)}} \right\rangle_{\text{Hadamard}}$ measured at `ADC_45` **already contains** both the physical multiplication by the primary input $x_i^{(3)}$ (`Ref 1/2`) and the physical slope of the first analog Sigmoid `4` ($\sigma_1'$).

Therefore, the exact weight gradient for Matrix `3` (`Equation 7` in `maml_eng.txt`) is:

$$\boxed{\frac{\partial L_{\text{total}}}{\partial W_{i,j}^{(3)}} = \left\langle \frac{\partial z_j^{(45)}}{\partial V_i^{\text{PTU}(5)}} \right\rangle_{\text{Hadamard}} \cdot \partial x_j^{(8)}} \quad \text{(Equation 7)}$$

> [!WARNING]
> **Again: DO NOT multiply Equation 7 by the primary input $x_i^{(3)}$ (`DAC_2`) or by a digital $\tanh'/\text{sigmoid}'$ of Layer 1!** Both factors are already physically embedded in $\left\langle \frac{\partial z_j^{(45)}}{\partial V_i^{\text{PTU}(5)}} \right\rangle_{\text{Hadamard}}$ measured at `ADC_45`.

---

## 4. Memory-Safe Dot-Product MAML Second-Derivative Outer Loop (`Ref 40`)

During **Base Model Training (`Ref 40` Outer Loop + `Ref 41` Inner Loop)**, the goal is to find an optimal meta-initial weight tensor $\mathbf{W}_0 = \{W_0^{(3)}, W_0^{(8)}\}$ that sits at the geometric center of all possible physical drift/offset basins so that, during live inference (`Ref 42`), a single fast adaptation step compensates for arbitrary thermal warping or capacitor droop.

### 4.1 Why Full Hessian MAML is Forbidden on Embedded SoC
Standard second-order MAML requires computing and storing the full Hessian matrix $\nabla_{\mathbf{W}}^2 L(\mathbf{W})$, which scales as $O(P^2)$ where $P$ is the number of parameters, causing a **memory and compute explosion** on the T120 Sapphire RISC-V SoC.

### 4.2 The Dot-Product / Hessian-Vector Second-Derivative Formulation
Instead of forming the Hessian matrix, the Inverted MAML Outer Loop (`Ref 40`) uses the **Dot-Product (Directional Derivative / Reptile-MAML Second-Order Approximation)** formulation:

For each Outer Loop iteration $m$:
1. **Sample / Emulate Hardware Hidden Offset Task $\mathcal{T}_k$:**
   - Apply a randomized **Hidden Offset** to the compensation weights ($W_{\text{actual}} = W + \Delta W_{\text{hidden}}$) and to the **Power Trim DAC (`Ref 38`, `trim-DAC`)** ($\Delta V_{\text{trim, hidden}}$).
   - *(Note: Input DAC `Ref 2` hidden offsets and ADC `Ref 45/49` hidden offsets are intentionally omitted in Phase 1 to avoid over-complicating initial convergence).*
2. **Record Pre-Adaptation Initial Gradient $\mathbf{g}_{\text{init}}$:**
   - At the base weights $\mathbf{W}_0$, perform one forward Hadamard sweep (`Equations 1–7`) to obtain the initial gradient vector $\mathbf{g}_1 = \nabla_{\mathbf{W}} L_{\mathcal{T}_k}(\mathbf{W}_0)$.
3. **Run Inner Loop (`Ref 41`) for $N$ Steps (Default $N = 100$, GUI-adjustable):**
   - Starting from $\mathbf{W}^{(0)} = \mathbf{W}_0$, iteratively adapt the weights within the task's local basin:
     $$\mathbf{W}^{(t+1)} = \mathbf{W}^{(t)} - \alpha_{\text{inner}} \cdot \mathbf{g}_t \quad \text{for } t = 0 \dots N-1$$
   - Let $\mathbf{W}^{(N)}$ be the adapted weight state at the bottom of task $\mathcal{T}_k$'s local valley, and $\mathbf{g}_N = \nabla_{\mathbf{W}} L_{\mathcal{T}_k}(\mathbf{W}^{(N)})$ be the final gradient.
4. **Compute the Second-Derivative Dot-Product Meta-Gradient:**
   - By Taylor expansion, the directional second derivative (Hessian-vector product) along the adaptation trajectory $\Delta \mathbf{W}_k = \mathbf{W}^{(N)} - \mathbf{W}_0$ is governed by the **inner-product alignment (dot product)** between the initial gradient and step gradients:
     $$d_k = \left\langle \mathbf{g}_1, \, \mathbf{g}_N \right\rangle = \sum_{p} g_{1,p} \cdot g_{N,p}$$
   - Equivalently, using finite-difference Hessian-vector projection along the displacement vector $\mathbf{v}_k = \mathbf{W}_0 - \mathbf{W}^{(N)}$:
     $$\mathbf{g}_{\text{meta}, k} = \left( \mathbf{W}_0 - \mathbf{W}^{(N)} \right) - \lambda_{\text{dot}} \cdot \frac{\langle \mathbf{g}_1 - \mathbf{g}_N, \, \mathbf{v}_k \rangle}{\|\mathbf{v}_k\|^2 + \epsilon} \cdot (\mathbf{g}_1 - \mathbf{g}_N)$$
   - **Memory Footprint:** Requires only **$O(P)$ vector dot products and vector additions** (3 flat arrays of size $P$: $\mathbf{W}_0$, $\mathbf{W}^{(N)}$, $\mathbf{g}_1$), completely eliminating the $O(P^2)$ Hessian matrix!
   - **Physical/Geometric Meaning (Visualized in the 3D GUI):** Each inner loop (`Ref 41`) finds a separate local minimum valley under a different thermal/offset warp. The Outer Loop (`Ref 40`) second-derivative dot product acts as a **centering force that "pushes/gathers" all the distinct inner-loop valleys together** toward a single shared basin around $\mathbf{W}_0$.

---

## 5. Summary Checklist for Code Review

| Check | Correct Implementation | Forbidden Bug |
|:---|:---|:---|
| **$M_8$ Gradient (`Eq. 2`)** | `grad_M8[i][j] = hadamard_M8[i][j] * err_49[j]` | ❌ Multiplying by `x_45[i]` or `1 - tanh(z)^2` |
| **Carrier Row $k$ (`Eq. 5`)** | `k = argmax_i(abs(x_45[i]))` | ❌ Dividing by small/zero `x_45[i]` on every row |
| **Layer 2 Slope (`Eq. 6`)** | `sigma2_prime[j] = (x_45[k] / (x_45[k]^2 + alpha)) * hadamard_M8[k][j]` | ❌ Using analytical digital `sech^2` on uncalibrated voltage |
| **Row Receipt (`Eq. 4`)** | `dx_8[i] = sum_j(W8_dig[i][j] * sigma2_prime[j] * err_49[j])` | ❌ Skipping `sigma2_prime[j]` when Sigmoid 10 is active |
| **$M_3$ Gradient (`Eq. 7`)** | `grad_M3[i][j] = hadamard_M3[i][j] * dx_8[j]` | ❌ Multiplying by `x_input[i]` (`DAC_2`) |
| **Perturbation Timing** | Perturb $M_8$ while $M_3$ is quiet, then perturb $M_3$ while $M_8$ is quiet | ❌ Driving Hadamard on $M_3$ and $M_8$ simultaneously |
| **Per-State ADC Timing** | 1. Shift & Latch Hadamard $\to$ 2. Quiet Analog DC Settle ($\approx 2\,\mu\text{s}$) $\to$ 3. ADC S/H & Readout $\to$ 4. Next State | ❌ Sampling ADC during H-bus shift or before analog DC settling ("earthquake noise") |
| **MAML Outer Loop (`Ref 40`)** | $O(P)$ vector dot-product second-derivative formulation | ❌ $O(P^2)$ full Hessian matrix allocation |

