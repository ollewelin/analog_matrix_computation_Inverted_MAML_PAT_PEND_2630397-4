---
name: m3-clock-cell-characterization
description: Protocol and automated characterization for Matrix 3 temporal reference clock cells (Rows 7 & 8, Ref 29/30) and Sigmoid 4 (Ref 4) operating points across the temporal window (4.5 to 5.5 ms). Sweeps carrier amplitude, baseline weights, and discharge delay to center the dynamic clock ramp directly in the linear high-sensitivity inflection of the sigmoid.
---

# Matrix 3 Temporal Clock & Reference Cell Characterization (Milestone 3)

This skill formalizes the calibration and operating regime protocol for the **temporal reference clock cells (Rows 7 & 8, Ref 29/30)** of Matrix 3 ($M_3$) in the Inverted MAML analog architecture ([SE 2630397-4](file:///home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/docs/MODE_B_VS_MODE_A_FINAL_CONSOLIDATED_REPORT.pdf)).

---

## 1. Physical Principle & Purpose (Milestone 3)

In analog computing with capacitive 2T1C cells, charge leakage is inevitable:
$$V_{\text{gate}}(t) = V_{\text{refresh}} \cdot e^{-t/\tau}$$

- **Compute Cells (Rows 1..6):** Have long retention times ($\tau_{\text{slow}} \approx 100\text{ ms}$, 100 nF).
- **Temporal Clock Cells (Rows 7 & 8, Ref 29/30):** Have faster, intentional discharge via $330\text{ k}\Omega$ discharge resistors ($\tau_{\text{fast}} \approx 33\text{ ms}$).
- **The Core Problem:** If the compensation network ($M_3 \to \text{Sigmoid 4} \to M_8$) only processes spatial signals, it cannot cancel time-dependent drift when evaluating over a broadened temporal window (e.g. $4.5\text{ ms} - 5.5\text{ ms}$).
- **The Solution:** The temporal clock cells generate an analog current ramp $I_{\text{clock}}(t)$. Fed through the ColTIA transimpedance amplifiers and hardware sigmoid (Sigmoid 4, Ref 4), this produces an analog time-reference voltage $V_{\text{clock}}(t)$ on differential $ADC_{45}$.
- **Matrix 8 Receiving Input:** Matrix 8 uses this time-varying signal to synthesize a temporal cancellation term:
  $$\Delta z_j(t) = W_8[\text{clock}, j] \cdot x_{\text{clock}}(t)$$
  which cancels the decay of $M_{33}$ over the entire measurement window.

---

## 2. The S-Curve Operating Point: Why Center at 5.0 ms?

The hardware sigmoid (Sigmoid 4) compresses large currents and has maximum derivative (gain) at its center:
$$\sigma'(0) = \max$$

1. **If the Clock Signal Saturates:**
   If $V_{\text{clock}}(t)$ falls into the upper or lower flat saturation zone of the sigmoid ($|ADC_{45}| > 600\text{ LSB}$), $\sigma'(V) \to 0$. The sensitivity to time vanishes, and the network is "blind" to time.
2. **If Placed in the Center (0 LSB at 5.0 ms):**
   - At $t = 4.5\text{ ms}$: Output is $+ \Delta V$ (higher charge, active positive slope).
   - At $t = 5.0\text{ ms}$: Output is $0\text{ LSB}$ (exact center of sigmoid inflection).
   - At $t = 5.5\text{ ms}$: Output is $- \Delta V$ (lower charge, active negative slope).
   - **Result:** Monotonic, highly linear, maximum dynamic range, zero clipping!

---

## 3. Characterization Workflow

1. **Step 1: Quiescent & Carrier Setup**
   - Set differential carrier DAC on Row 7 (`g_dac_row7_code`) and Row 8 (`g_dac_row8_code`).
   - Enable weights $W_{\text{clock}} \in [-120, +120]$ on Rows 6 & 7 of Matrix 3.
2. **Step 2: Dynamic Snapshot Sweep across Time**
   - Sweep delay $t \in [1.0, 2.0, 3.0, 4.0, 4.5, 4.8, 5.0, 5.2, 5.5, 6.0, 7.0, 8.0, 9.0]\text{ ms}$.
   - Read $ADC_{45}[0..5]$ directly at each time point.
3. **Step 3: Slope & Linearity Assessment**
   - Compute dynamic swing $\Delta ADC_{45} = ADC_{45}(4.5\text{ ms}) - ADC_{45}(5.5\text{ ms})$.
   - Verify that $|ADC_{45}| < 300\text{ LSB}$ across $[4.5, 5.5]\text{ ms}$ (strictly inside linear sigmoid regime).
   - Calibrate $W_{\text{clock}}$ and carrier DAC codes so that $ADC_{45}(5.0\text{ ms}) \approx 0\text{ LSB}$.
