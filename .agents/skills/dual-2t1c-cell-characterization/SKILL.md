---
name: dual-2t1c-cell-characterization
description: Comprehensive characterization, calibration, and operating regime protocol for the Inverted MAML Dual-2T1C differential analog triode multiplier cells. Covers physical electrical null-point asymmetry (W_null offset), quiet linear regime vs. high-variance oscillation instability, 60 MHz ColTIA op-amp dynamics, and single-cell probe protocols on physical silicon.
---

# Dual-2T1C Analog Crosspoint Multiplier Characterization Skill

This skill documents the physical electrical characteristics, operating regimes, zero-gain calibration, and measurement protocol for the **Dual-2T1C (`2X_2T1C`) differential analog multiplier cells** used in the Inverted MAML analog neural accelerator (T120F324 Master + T20F256 Coprocessor).

---

## 1. Physical Circuit Architecture & Triode Operating Theory

Each crosspoint $(i, j)$ in the analog weight matrices ($M_{33}\ 6\times 6$, $M_3\ 8\times 6$, $M_8\ 7\times 6$) implements an analog four-quadrant multiplier $(X_i \times W_{ij})$ using two matched 2T1C half-cells:

```
          In-Data Row i (DAC_2[i], Drain Line V_ds)
                       │
       ┌───────────────┴───────────────┐
       │                               │
  ┌────┴────┐                     ┌────┴────┐
  │  Q5 (P) │                     │  Q8 (N) │  (Triode MOSFETs)
  └────┬────┘                     └────┬────┘
       │ Gate: G_P                     │ Gate: G_N
   [C_P 100nF]                     [C_N 100nF]
       │                               │
       ▼                               ▼
   ColTIA(+) Summing Line         ColTIA(-) Summing Line
```

### Triode Conduction Equation
When operating in the deep triode (linear) region ($V_{DS} \ll V_{GS} - V_{th}$):
$$I_P = \mu_P C_{ox} \left(\frac{W}{L}\right)_P \left( (V_{G,P} - V_{th,P}) V_{DS} - \frac{1}{2} V_{DS}^2 \right)$$
$$I_N = \mu_N C_{ox} \left(\frac{W}{L}\right)_N \left( (V_{G,N} - V_{th,N}) V_{DS} - \frac{1}{2} V_{DS}^2 \right)$$

The net differential column current delivered to the column transimpedance amplifier (ColTIA) virtual ground ($V_S = 1.650\text{ V}$) is:
$$I_{\text{col}} = I_P - I_N = \left[ k_P (V_{G,P} - V_{th,P}) - k_N (V_{G,N} - V_{th,N}) \right] V_{DS} - \frac{1}{2} (k_P - k_N) V_{DS}^2$$

---

## 2. Empirical Operating Regimes on Silicon

Real silicon characterization (measured via UDP on the physical T120/T20 board in Mode B, `ADC_49[C1]`) reveals three distinct operating regimes:

| Regime | Signed Weight Range ($W$) | Standard Deviation ($\sigma$) | Physical Behavior & Multiplier Response |
| :--- | :--- | :--- | :--- |
| **Quiet Linear Zone** | $W \in [-127, -40]$ LSB | **$\sigma \le 1.0$ LSB** (often **0.00 LSB**) | Clean, deterministic linear multiplication. Virtual ground summing node is stable; 60 MHz ColTIA op-amp phase margin is high. |
| **True Electrical Null** | $W \approx -43 \text{ to } -45$ LSB | **$\sigma = 0.00 \text{ to } 0.40$ LSB** | Differential transconductance matches exactly: $k_P(V_{GP}-V_{th,P}) = k_N(V_{GN}-V_{th,N})$. Net gain $\frac{dY}{dX} = 0.0$ LSB. Output does not move regardless of $X$. |
| **High-Variance / Oscillatory Zone** | $W > -20$ LSB (up to $+127$) | **$\sigma = 15 \text{ to } 47$ LSB** | Positive gate voltage increases $P$-channel conductance, loading the ColTIA virtual ground with parasitic bus capacitance. The new 60 MHz op-amps suffer phase margin degradation, bursting into ~10 MHz ringing (~100 mV pk-pk on oscilloscope). |

### Why $W_{\text{null}} \approx -43$ LSB (Electrical Null Offset)
In theoretical models, $W = 0$ (where DAC codes $W_P = 128$ and $W_N = 128$) should yield zero differential output. However, on real physical hardware:
1. **$V_{th}$ and Aspect Ratio Mismatch:** The P-branch transistor turns on slightly earlier or has higher transconductance than the N-branch ($k_P > k_N$ or $V_{th,P} < V_{th,N}$).
2. **Layout & Trace Asymmetry:** Parasitic series resistance in the PCB traces between the recharge multiplexer and the $G_P / G_N$ gate capacitors creates a non-zero static charge bias.
3. **To nullify this positive conductance bias:** The differential weight DAC must be biased negative ($W \approx -43$ LSB), reducing $V_{GP}$ and raising $V_{GN}$ until their differential conductances cancel out with sub-LSB precision ($\Delta Y < 1$ LSB).

---

## 3. Oscilloscope & Hardware Verification Landmarks

When probing the physical hardware with an oscilloscope:
- **Pin landmark:** Probe `ADC_49_CONV` on FPGA Pin `U9` (`GPIOB_TXN17`) or Pin 6 (`CONV`) of the `XC2361A` ADC chip. Use this as the oscilloscope trigger.
- **In-Data Line ($V_{DS}$):**
  - **10 ms (100 Hz) Sway:** A systematic ~20 mV AC sway over each 10 ms period reflects the cyclic gate charge retention of the 100 nF capacitors.
  - **200 µs Staircase Steps:** The 6 sequential column charge pulses ($6 \times 100\ \mu\text{s}$) produce small ~2 mV sharp steps during column refresh.
  - **Quiet Measurement Plateau:** Multiplier reads must occur during the quiet plateau ($t \ge 2.5\text{ ms}$ after the refresh burst), when all FPGA I/O except the ADC serial lines are silent.
- **10 MHz Resonant Bursts:**
  - If $W > 0$, observe bursts of ~10 MHz ringing (~100 mV pk-pk) on the ColTIA summing line.
  - Setting $W \le -40$ eliminates this ringing, restoring absolute DC radio silence.

---

## 4. Standard Single-Cell Probe Protocol (Python)

To characterize or probe any crosspoint cell $(X, W)$ without triggering background Hadamard or refresh jitter:

```python
from gui.udp_client import MamlUdpClient, MAT_M33

client = MamlUdpClient(host="192.168.1.50", port=5000, timeout=1.0)

# Disarm heaters before diagnostic testing
client.set_heaters(False, [0, 0, 0, 0])

# Probe Cell (Row 0, Col 0) on Matrix 33 with W = -43 LSB (Electrical Null)
# Input amplitude X = 96 LSB: steps through X = 0, X = +96, and X = -96
res = client.probe_cell_xw(
    matrix_id=MAT_M33,
    row=0,
    col=0,
    x_amp=96,
    w_fixed=-43,
    sweep_input=True,
    hold=False,
)

if res is not None:
    y_pos  = res.adc49_pos[0]   # Response at X = +96
    y_neg  = res.adc49_neg[0]   # Response at X = -96
    y_zero = res.adc49_zero[0]  # Quiescent baseline at X = 0
    delta  = y_pos - y_neg      # Net differential gain
    print(f"Cell (0,0): Pos={y_pos:+d}, Neg={y_neg:+d}, Zero={y_zero:+d} | Delta={delta:+d} LSB")
```

---

## 5. Column Masking Rules for Silicon Training

When transitioning from single-cell evaluation to closed-loop MAML training:
1. **Identify Functional vs. Damaged Columns:**
   - In Mode B / Mode A, inspect quiescent ADC baselines:
     - **Columns 1 and 5:** Responsive, linear, and non-saturated ($Y \in [-30, +30]$ LSB).
     - **Columns 2, 3, 6:** Stuck in negative saturation rails ($-1600$ to $-2048$ LSB) due to analog front-end op-amp defects or trace damage.
2. **Masked Loss Function Formulation:**
   - **DO NOT** train the neural loss against all 6 columns, as the $1600^2$ error on saturated columns will drown out real gradient signals.
   - Restrict the Inverted MAML Loss computation strictly to the functional columns:
     $$\mathcal{L} = \frac{1}{2} \left[ (Y_1 - Y_{1,\text{target}})^2 + (Y_5 - Y_{5,\text{target}})^2 \right]$$
   - Allow bad columns to idle without penalizing the weight update vectors.

