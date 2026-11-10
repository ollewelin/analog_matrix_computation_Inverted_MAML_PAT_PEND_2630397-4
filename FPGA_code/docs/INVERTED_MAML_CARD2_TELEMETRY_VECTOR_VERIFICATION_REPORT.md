# Inverted MAML: Telemetry Vector Verification & Arithmetic Audit Report
## Deep-Dive Hardware Telemetry Audit: White-Noise Input Switching, Matrix 33 Multiplication, Analog Output Readout & Step-by-Step ENOB Verification
**Hardware Target:** Card 2 (PCBA v1.3.2 | Trion T120 Master SoC + T20 Coprocessor | 1k/3.3k Attenuator)  
**Patent Pending:** SE 2630397-4 (Inverted MAML Silicon) &nbsp;|&nbsp; **Open Science Hardware Documentation**

---

## 1. Executive Summary & Audit Scope
This verification report provides an exhaustive numerical audit of telemetry data captured on physical Inverted MAML Card 2 silicon.
The primary objective is to verify the deterministic integrity of the hardware pipeline:
1. Proving that pseudo-random white-noise input vectors $X \in [-40, +40]\text{ LSB}$ update genuinely between consecutive epochs.
2. Demonstrating the exact mathematical dot product against the frozen 6x6 Matrix 33 payload ($X \cdot W_{33}$).
3. Deriving the theoretical supervisor target $Z_{\text{target}}$ accounting for empirical DC baseline offsets and hardware scaling ($\times 1/32$).
4. Comparing this target to the actual physical analog readout $Z_{\text{snap}}^{(49)}$ sampled by the differential XC2361A ADC at the ColTIA summer.
5. Proving that the reported Mean Squared Error Loss and Effective Number of Bits (ENOB) strictly follow IEEE standards without rounding discrepancies.

---

## 2. Binary Telemetry Packet Anatomy (UDP Port 5000, `maml_telemetry_pkt_t`)

| Field Name | Type | Byte Offset | Physical Function & Signal Routing |
| :--- | :--- | :--- | :--- |
| `magic` / `cmd` | `uint32` / `uint8` | 0 .. 4 | Protocol frame magic (`0x4D414D31` = 'MAM1') and command opcode (`0x90`). |
| `loss_total_milli` | `uint32` | 36 .. 39 | Cumulative squared error across all 6 columns in milli-LSB² ($\text{Loss} = \text{loss\_total\_milli} / 2.0$). |
| `bit_prec_comp` | `uint16` | 40 .. 41 | Hardware-computed resolution in centi-bits ($\text{ENOB} = \text{bit\_prec\_comp} / 100.0$). |
| **`x_ref[6]`** | `int16[6]` | **50 .. 61** | **Active reference input vector $X = [x_0..x_5]$ fed to 74HC595 DAC_2 array.** |
| **`z_target[6]`** | `int16[6]` | **62 .. 73** | **Theoretical digital target vector computed in real-time by T120 Master SoC C-firmware.** |
| `adc45_sig[6]` | `int16[6]` | 74 .. 85 | Differential analog signal sampled after Sigmoid 4 (drives Matrix 8 input gates). |
| **`adc49_sig[6]`** | `int16[6]` | **86 .. 97** | **Physical ColTIA summer output (Matrix 33 payload + Matrix 8 anti-phase compensation).** |
| `w_m3[8][6]` | `int8[48]` | 110 .. 157 | Adaptive weights and reference clock staircases for Matrix 3. |
| `w_m8[7][6]` | `int8[42]` | 158 .. 199 | Vernier compensation weights for Matrix 8. |
| **`w_m33[6][6]`** | `int8[36]` | **200 .. 235** | **Frozen 6x6 signed differential weight payload (-128..+127 LSB) of primary multiplier.** |

---

## 3. Standard Frozen Payload Reference Matrix (Matrix 33, 6x6 Array)

$$W_{33} = \begin{bmatrix}
+76 & -20 & +28 &  -4 & +44 & -36 \\
-20 & +84 & -12 & +44 &  -4 & +36 \\
+36 &  -4 & +80 & -16 & +32 &  -4 \\
 -4 & +40 &  -8 & +72 & -12 & +44 \\
+44 & -12 & +28 & -12 & +76 &  -8 \\
-28 & +32 &  -4 & +40 &  -8 & +82
\end{bmatrix}$$

**Mathematical Target Synthesis Rule:**  
In T120 C-firmware (`maml_recompute_z_target`), the ideal supervisor target is computed as:
$$Z_{\text{target}, j} = g_{\text{adc49\_zero\_cal}, j} + \text{round}\left( \frac{(X \cdot W_{33})_j}{32} \right)$$
where $g_{\text{adc49\_zero\_cal}} = [-1338, -807, -677, +216, -632, -1521]\text{ LSB}$ is the empirical zero-calibration baseline measured at $t=0$ with $X=0, W=0$.

---

## 4. Consecutive Epoch Hardware Audit: Epoch 150 & Epoch 151

Dataset Source: `card2_mode_a_new_fw_1000ep_5ms_pure_toeplitz_reg2048_lr0p02_swing40_var5_k1_1k_3p3k_ablation.json`  
Operating Regime: Phase 2 Nominal Convergence (Epoch 100–199, active closed-loop Mode A SGD). Epochs 150 and 151 represent the exact midpoint.

### 4.1 Epoch 150 Step-by-Step Numerical Derivation
* **Input Vector $X^{(150)}$:** `[-13, +5, +5, -1, +5, -1]` (White Noise within $\pm 40\text{ LSB}$).
* **Matrix Multiplication ($X \cdot W_{33}$):**
  - Col 0: $(-13 \times 76) + (5 \times -20) + (5 \times 36) + (-1 \times -4) + (5 \times 44) + (-1 \times -28) = \mathbf{-656}$
  - Col 1: $(-13 \times -20) + (5 \times 84) + (5 \times -4) + (-1 \times 40) + (5 \times -12) + (-1 \times 32) = \mathbf{+528}$
  - Col 2: $(-13 \times 28) + (5 \times -12) + (5 \times 80) + (-1 \times -8) + (5 \times 28) + (-1 \times -4) = \mathbf{+128}$
  - Col 3: $(-13 \times -4) + (5 \times 44) + (5 \times -16) + (-1 \times 72) + (5 \times -12) + (-1 \times 40) = \mathbf{+20}$
  - Col 4: $(-13 \times 44) + (5 \times -4) + (5 \times 32) + (-1 \times -12) + (5 \times 76) + (-1 \times -8) = \mathbf{-32}$
  - Col 5: $(-13 \times -36) + (5 \times 36) + (5 \times -4) + (-1 \times 44) + (5 \times -8) + (-1 \times 82) = \mathbf{+462}$  
  $\Rightarrow$ **Dot Product Vector:** `[-656, +528, +128, +20, -32, +462]`
* **Theoretical Target $Z_{\text{target}}$:**
  `[-1338-20, -807+17, -677+4, 216+1, -632-1, -1521+14]` = **`[-1358, -790, -673, +217, -633, -1507] LSB`**
* **Physical Silicon Readout (ADC 49):** **`[-1319, -824, -684, +202, -616, -1443] LSB`**
* **Error Vector ($\text{err49} = Z_{\text{snap}} - Z_{\text{target}}$):** **`[+39, -34, -11, -15, +17, +64] LSB`**
* **Loss & ENOB Calculation:**
  - $\sum (\text{err49})^2 = 39^2 + (-34)^2 + (-11)^2 + (-15)^2 + 17^2 + 64^2 = 1521 + 1156 + 121 + 225 + 289 + 4096 = \mathbf{7,408}$
  - Mean Squared Error Loss: $\text{Loss} = 7408 / 2 = \mathbf{3704.0\text{ LSB}^2}$ *(Telemetry Log: `3704.0`)*
  - Root Mean Square Error: $\text{RMSE} = \sqrt{7408 / 6} = \mathbf{35.14\text{ LSB}}$ *(Telemetry Log: `35.14`)*
  - Effective Number of Bits: $\text{ENOB} = 11.0 - \log_2(35.138) = 11.0 - 5.135 = \mathbf{5.87\text{ bits}}$ *(Telemetry Log: `5.87`)*

---

### 4.2 Epoch 151 Step-by-Step Numerical Derivation (Input Vector Updated)
* **Updated Input Vector $X^{(151)}$:** `[-40, -18, +7, +14, +25, +14]` (Notice: all 6 coordinates randomly updated).
* **Matrix Multiplication ($X \cdot W_{33}$):**
  - Col 0: $(-40 \times 76) + (-18 \times -20) + (7 \times 36) + (14 \times -4) + (25 \times 44) + (14 \times -28) = \mathbf{-1,776}$
  - Col 1: $(-40 \times -20) + (-18 \times 84) + (7 \times -4) + (14 \times 40) + (25 \times -12) + (14 \times 32) = \mathbf{-32}$
  - Col 2: $(-40 \times 28) + (-18 \times -12) + (7 \times 80) + (14 \times -8) + (25 \times 28) + (14 \times -4) = \mathbf{+188}$
  - Col 3: $(-40 \times -4) + (-18 \times 44) + (7 \times -16) + (14 \times 72) + (25 \times -12) + (14 \times 40) = \mathbf{+524}$
  - Col 4: $(-40 \times 44) + (-18 \times -4) + (7 \times 32) + (14 \times -12) + (25 \times 76) + (14 \times -8) = \mathbf{+156}$
  - Col 5: $(-40 \times -36) + (-18 \times 36) + (7 \times -4) + (14 \times 44) + (25 \times -8) + (14 \times 82) = \mathbf{+2,328}$  
  $\Rightarrow$ **Dot Product Vector:** `[-1776, -32, +188, +524, +156, +2328]`
* **Theoretical Target $Z_{\text{target}}$:**
  `[-1338-56, -807-1, -677+6, 216+16, -632+5, -1521+73]` = **`[-1394, -807, -671, +232, -627, -1448] LSB`**
* **Physical Silicon Readout (ADC 49):** **`[-1318, -812, -680, +225, -653, -1381] LSB`**
* **Error Vector ($\text{err49} = Z_{\text{snap}} - Z_{\text{target}}$):** **`[+76, -5, -9, -7, -26, +67] LSB`**
* **Loss & ENOB Calculation:**
  - $\sum (\text{err49})^2 = 76^2 + (-5)^2 + (-9)^2 + (-7)^2 + (-26)^2 + 67^2 = 5776 + 25 + 81 + 49 + 676 + 4489 = \mathbf{11,096}$
  - Mean Squared Error Loss: $\text{Loss} = 11096 / 2 = \mathbf{5548.0\text{ LSB}^2}$ *(Telemetry Log: `5548.0`)*
  - Root Mean Square Error: $\text{RMSE} = \sqrt{11096 / 6} = \mathbf{43.00\text{ LSB}}$ *(Telemetry Log: `43.00`)*
  - Effective Number of Bits: $\text{ENOB} = 11.0 - \log_2(43.00) = 11.0 - 5.426 = \mathbf{5.57\text{ bits}}$ *(Telemetry Log: `5.57`)*

---

### 4.3 Side-by-Side Audit Summary: Manual Derivation vs. Hardware Telemetry

| Metric / Parameter | Epoch 150 (Manual Calc) | Epoch 150 (Telemetry Log) | Epoch 151 (Manual Calc) | Epoch 151 (Telemetry Log) | Audit Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Input Vector X** | `[-13, 5, 5, -1, 5, -1]` | `[-13, 5, 5, -1, 5, -1]` | `[-40, -18, 7, 14, 25, 14]` | `[-40, -18, 7, 14, 25, 14]` | **VERIFIED MATCH** |
| **X · W33 Dot Product** | `[-656, 528, 128, 20, -32, 462]` | `[-656, 528, 128, 20, -32, 462]` | `[-1776, -32, 188, 524, 156, 2328]` | `[-1776, -32, 188, 524, 156, 2328]` | **VERIFIED MATCH** |
| **Theoretical Z_target** | `[-1358, -790, -673, 217, -633, -1507]` | `[-1358, -790, -673, 217, -633, -1507]` | `[-1394, -807, -671, 232, -627, -1448]` | `[-1394, -807, -671, 232, -627, -1448]` | **VERIFIED MATCH** |
| **Silicon ADC49 Readout** | `[-1319, -824, -684, 202, -616, -1443]` | `[-1319, -824, -684, 202, -616, -1443]` | `[-1318, -812, -680, 225, -653, -1381]` | `[-1318, -812, -680, 225, -653, -1381]` | **VERIFIED MATCH** |
| **Residual Error (err49)** | `[+39, -34, -11, -15, +17, +64]` | `[+39, -34, -11, -15, +17, +64]` | `[+76, -5, -9, -7, -26, +67]` | `[+76, -5, -9, -7, -26, +67]` | **VERIFIED MATCH** |
| **MSE Loss (LSB²)** | **3,704.0 LSB²** | **3,704.0 LSB²** | **5,548.0 LSB²** | **5,548.0 LSB²** | **EXACT 0.00 L² DELTA** |
| **RMSE (LSB)** | **35.14 LSB** | **35.14 LSB** | **43.00 LSB** | **43.00 LSB** | **EXACT 0.00 LSB DELTA** |
| **Resolution (ENOB)** | **5.87 bits** | **5.87 bits** | **5.57 bits** | **5.57 bits** | **EXACT 0.00 b DELTA** |

---

## 5. Cross-Check with the 20-Minute Cold-Start Thermal Run

Dataset Source: `card2_thermal_cycling_heaters_8m8m_30pct_1hz_regler_2m2m_l2_768_k2_lr0p02_5p0_to_5p4ms_cold_start_20min.json`  
In the 20-minute thermal cycling run, each epoch executes a multi-strata burst evaluating 5 temporal delays (5.0, 5.1, 5.2, 5.3, 5.4 ms) with batch size $K=2$ (total 10 matrix-vector multiplications per epoch).
Examining the exact midpoint of the initial 2-minute training period (elapsed $t \approx 54.5\text{ s}$):

* **Epoch 307 ($t = 54.5\text{ s}$, Heaters OFF, Comp ON):**
  - Strata Losses: `[9204.0, 6731.0, 9827.0, 7625.0, 41344.5] LSB²` &nbsp;|&nbsp; Strata ENOBs: `[5.21, 5.43, 5.16, 5.34, 4.12] bits`
  - Center 5.2 ms Delay: **Loss = 9,827.0 LSB² &rarr; ENOB = 5.16 bits** &nbsp;|&nbsp; Window Mean: **Loss = 14,946.3 LSB² &rarr; ENOB = 4.86 bits**
* **Epoch 308 ($t = 54.7\text{ s}$, Next White-Noise Batch Applied):**
  - Strata Losses: `[4782.0, 4430.5, 6096.5, 16811.5, 17758.0] LSB²` &nbsp;|&nbsp; Strata ENOBs: `[5.65, 5.71, 5.51, 4.88, 4.84] bits`
  - Center 5.2 ms Delay: **Loss = 6,096.5 LSB² &rarr; ENOB = 5.51 bits** &nbsp;|&nbsp; Window Mean: **Loss = 9,975.7 LSB² &rarr; ENOB = 5.15 bits**

---

## 6. Formal Verification Certificate & Conclusions

1. **Unconditional Determinism:** The mathematical dot product, the target scaling formula ($\times 1/32$), the analog DC calibration integration, the error subtraction, and the logarithmic ENOB conversion match between manual calculation and firmware telemetry to zero decimal places.
2. **Genuine Stochastic White-Noise Excitation:** Every epoch introduces an independent random vector $X \in [-40, +40]\text{ LSB}$, exercising all 36 crosspoints of Matrix 33 and all 48 crosspoints of Matrix 3 across their full dynamic range.
3. **Closed-Loop Physical Fidelity:** The analog output ADC 49 tracks the rapidly fluctuating supervisor target across dynamic white-noise shifts, confirming that the 2-layer compensation network ($M_3 \rightarrow \text{Sig4} \rightarrow M_8$) actively sustains 5.5–5.9 bit precision under real-world silicon operation.

**Open Science Verification & Reproduction:**  
Hardware Repository: [https://github.com/ollewelin/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4](https://github.com/ollewelin/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4)  
Zenodo DOI: [10.5281/zenodo.24030796](https://doi.org/10.5281/zenodo.24030796)
