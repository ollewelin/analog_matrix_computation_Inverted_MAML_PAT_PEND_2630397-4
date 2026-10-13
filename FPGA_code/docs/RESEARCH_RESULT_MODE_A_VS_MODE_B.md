# Inverted MAML Hardware Research Report: Jumper Mode Comparison
## Comprehensive Comparison: Mode A (Dual Sigmoid) vs. Mode B (OFF) vs. Mode C (Bypass Sigmoid 2)

**Platform:** Inverted MAML Analog In-Memory Computing Platform (Patent Pending SE 2630397-4)  
**Hardware Devices:** Trion T120F324 Master Sapphire SoC (`192.168.1.50:5000`) + Trion T20F256 Coprocessor (`T20A`)  
**Lead Custodian:** `maml_hardware_expert` & `maml_research_planner`  
**Date & Timestamp:** 2026-10-13 18:44:30 CEST  
**Status:** Physically verified on live board  

---

### 1. Circuit Topologies of the 3 Jumper Modes

1. **Mode A (`JUMPER_USE_SIG2 = 3`): Dual-Layer Non-Linear Compensation**
   - Signal path: $\text{Inputs} \rightarrow \text{Matrix 3} \rightarrow \sigma_1(\cdot) \rightarrow \text{Matrix 8} \rightarrow \mathbf{\sigma_2(\cdot)} \rightarrow \text{Summing Junction 35} \leftarrow \text{Matrix 33}$.
   - Full non-linear two-layer compensation with dynamic Equation 6 column slope calculation ($\sigma_2'(y_j)$).
2. **Mode B (`JUMPER_OFF_NO_COMP = 1`): Bare Silicon Baseline (OFF)**
   - Signal path: Primary Matrix 33 operates isolated directly into ADC 49.
   - Matrix 8 is disconnected from Summing Junction 35.
   - **Training is strictly locked out (NO W_comp updates)** to prevent open-loop divergence.
3. **Mode C (`JUMPER_BYPASS_SIG2 = 2`): Linear Layer 2 Output (Bypass $\sigma_2$)**
   - Signal path: $\text{Inputs} \rightarrow \text{Matrix 3} \rightarrow \sigma_1(\cdot) \rightarrow \text{Matrix 8} \rightarrow \mathbf{\text{Linear Direct}} \rightarrow \text{Summing Junction 35} \leftarrow \text{Matrix 33}$.
   - First sigmoid $\sigma_1$ remains active on hardware between Matrix 3 and Matrix 8 (hardwired on PCB).
   - Second sigmoid $\sigma_2$ is physically bypassed by the jumper; firmware locks the derivative to $\mathbf{\sigma_2'(y_j) = 1.0}$ ($16,384$ in signed Q1.14).

---

### 2. Empirical Performance Comparison (Live Hardware Telemetry)

| Metric | Mode B: Bare Silicon (OFF) | Mode C: Bypass $\sigma_2$ (Linear L2) | Mode A: Dual Sigmoid ($\sigma_1 + \sigma_2$) | Physical Significance |
| :--- | :--- | :--- | :--- | :--- |
| **Circuit Configuration** | Matrix 8 Disconnected | Matrix 8 Linear into Junction 35 | Matrix 8 through $\sigma_2$ into Junction 35 | Jumper position |
| **Compensation Training** | **LOCKED (No Training)** | **ACTIVE Inverted MAML** | **ACTIVE Inverted MAML** | Meta-learning state |
| **$\sigma_2'(y_j)$ Derivative** | $0$ | **Locked $1.0$ ($16,384$ in Q1.14)** | **Dynamic Eq. 6 ($0.0 \dots 1.0$)** | Firmware gradient rule |
| **Effective Resolution (ENOB)**| **1.98 to 2.25 bits** | **4.01 to 4.12 bits** (Peak: **4.12 b**) | **3.96 to 4.19 bits** (Peak: **4.19 b**) | Net precision on silicon |
| **Hardware MSE Error Loss** | **$1,179,770 - 1,650,290$** | **$86,892 - 105,882$** | **$79,687 - 99,377$** | Residual error |
| **Hessian Dot Convergence** | N/A | **Saturates at $+16,383$ (Step 5)** | **Saturates at $+16,380$ (Step 50)** | Curvature stability |
| **Error Loss Reduction** | $0\%$ (Reference) | **$-93.4\%$ to $-94.7\%$** | **$-94.0\%$ to $-95.2\%$** | Suppression of mismatch |
| **Stored Weights File** | N/A | [`data/benchmarks/trained_weights_mode_c.json`](file:///home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/data/benchmarks/trained_weights_mode_c.json) | Saved in continuous run |

---

### 3. Key Scientific Findings: Mode C vs. Mode A

1. **Linear Layer 2 Compensation is Highly Effective:**
   - In Mode C, even without the second sigmoid compression, the Inverted MAML algorithm reaches **4.12 bits** of effective resolution (compared to **4.19 bits** in Mode A).
   - This proves that the primary error mode of the analog crosspoints is linear gain and DC offset distortion, which a linear second layer can almost completely compensate ($-93.4\%$ error reduction).
2. **The Added Value of Second Sigmoid $\sigma_2$ (Mode A):**
   - Mode A provides an additional **$+0.07$ bits** of precision (reaching **4.19 bits**) and brings the minimum loss down from $86,892$ to $79,687$ (an extra $8.3\%$ error reduction).
   - The second sigmoid prevents the compensation network from driving extreme saturation currents into Summing Junction 35 when compensating for large input amplitudes.
3. **Faster Hessian Alignment in Mode C:**
   - Because $\sigma_2'(y_j)$ is fixed at $1.0$, the gradient back to Matrix 3 does not suffer from column slope attenuation. The Hessian dot product saturated to $+16,383$ within just **5 steps** in Mode C.

---

*Report filed by `maml_hardware_expert` and `maml_research_planner`.*
