---
name: matrix33-full-landscape-mapping
description: Protocol, methodologies, and visualization workflows for mapping the complete 6x6 (36 crosspoints) uncompensated analog multiplier gain landscape of Matrix 33 in Mode B on physical silicon. Covers multi-dimensional sweeps across Space (Rows 0..5, Cols 0..5), In-Data (5 user curves), Weight space, and 10 ms dynamic snapshot slices (0.5 to 9.5 ms) with 3D gain topography.
---

# Matrix 33 Full 6×6 Analog Gain Landscape Mapping Skill

This skill documents the automated characterization, empirical sweep protocol, and 3D visualization architecture for mapping all **36 crosspoints** (Row 0..5, Col 0..5) of **Matrix 33** (`M33`, main $6\times 6$ multiplier payload) in **Mode B** (uncompensated, Jumper Mode 1) on the Trion T120 Master SoC + T20 Coprocessor (`192.168.1.50:5000`).

---

## 1. Physical Architecture & The Brutal Analog Reality

In pure Mode B, no adaptive BJT sigmoid compression, clamp attenuation, or inner-loop compensation strata ($M_3 / M_8$) are active. The ColTIA transimpedance amplifiers receive the raw, uninhibited differential triode currents directly from the Dual-2T1C MOSFET pairs.

Because of microscopic silicon fabrication tolerances, threshold voltage variations ($\Delta V_{th}$), aspect ratio deviations, PCB trace parasitics, and op-amp phase margins:
- Every cell $(r, c)$ in Matrix 33 possesses a unique non-linear transfer function $Y_{r,c}(X, W, t)$.
- Peak gain varies substantially across the matrix (from $250\text{ mV}$ up to $>1300\text{ mV}$).
- Every cell exhibits subthreshold turnaround roll-over when $W < -80\text{ LSB}$ due to P-channel pinch-off.
- ColTIA summing lines suffer capacitive loading, causing differential gain decay across the 10 ms cycle ($\tau \approx 6.8\text{ ms}$).
- Columns 2 and 3 (0-indexed) are saturated at negative rails ($-1600\text{ to }-2048\text{ LSB}$), while Columns 0, 1, 4, and 5 exhibit active, high-dynamic analog multiplication.

---

## 2. Multi-Dimensional Sweep Dimensions

A full-matrix landscape characterization spans four coupled physical dimensions:

| Dimension | Physical Domain | Parametric Range | Resolution / Settings |
| :--- | :--- | :--- | :--- |
| **Spatial Grid** | Matrix Crosspoints | Row $r \in [0..5]$, Col $c \in [0..5]$ | 36 distinct analog multiplier cells |
| **In-Data Level** | Drain Voltage $V_{ds}$ (DAC_2) | $X \in \{-127, -64, 0, +64, +127\}$ LSB | 5 standardized colored curves (Blue, Red, Green, Orange, Yellow) |
| **Weight Bias** | Gate Storage MLCC (DAC_15/12) | $W \in [-127, \dots, +127]$ LSB | Spans turnaround ($<-80$), linear ($[-60..+40]$), null, and positive saturation |
| **Temporal Slice** | 100 Hz Refresh Cycle Delay | $t \in [0.5, 9.2]$ ms ($500\text{ to }9200\ \mu\text{s}$) | Clamped ($0\text{--}1.0\text{ ms}$), peak ($3.5\text{ ms}$), nominal ($5.0\text{ ms}$), decay ($>6.5\text{ ms}$) |

---

## 3. Quiescent Row Isolation & Automated Auto-Pause

When probing cell $(r, c)$:
1. **Unprobed Rows Quiescent:**
   The firmware diagnostic command `maml_probe_single_cell()` drives $X = \pm x_{\text{amp}}$ **strictly on the probed row $r$**, while all unprobed rows $k \neq r$ are clamped to $128$ ($0.0\text{ V}$ differential).
2. **Autonomous Random In-Data Decoupling:**
   Calling `probe_cell_xw()` automatically clears `g_auto_random_data = 0u` in firmware, stopping background white-noise switching during characterization.
3. **Synchronous Column Refresh:**
   Each input step ($X = 0$, $X = +x_{\text{amp}}$, $X = -x_{\text{amp}}$) is immediately preceded by a synchronous column recharge burst, settling before triggering the settled ADC conversion at the user-specified delay $t$.

---

## 4. Hardware Sweep Execution Protocol

Use the standardized hardware execution script:

```bash
# Fast 36-cell sweep at nominal t = 5.0 ms and peak t = 3.5 ms (~45 seconds)
python3 FPGA_code/scripts/map_matrix33_full_landscape.py --mode fast

# Comprehensive multi-time-slice sweep across all 36 cells (0.5 to 9.2 ms)
python3 FPGA_code/scripts/map_matrix33_full_landscape.py --mode full
```

### Python SDK Direct Call Pattern

```python
from gui.udp_client import MamlUdpClient, MAT_M33

client = MamlUdpClient(host="192.168.1.50", port=5000, timeout=0.35)

# Ensure Mode B (jumper_mode = 1)
client.set_config(mode=0, jumper_mode=1, led_switches=0, max_meas_win_pct=50,
                  hadamard_khz=250, inner_loop_n=10, seed_pct=28, seed_mode=0,
                  w_hid_mag=16, trim_hid_mag=0, hadamard_delay_us=2500)
client.center_compensation_weights()

# Probe cell (r, c) at snapshot t = 5.0 ms (5000 us)
res127 = client.probe_cell_xw(matrix_id=MAT_M33, row=r, col=c, x_amp=127, w_fixed=-80, snap_dly_us=5000)
res64  = client.probe_cell_xw(matrix_id=MAT_M33, row=r, col=c, x_amp=64,  w_fixed=-80, snap_dly_us=5000)

# Extract differential response on column c (LSB to mV: factor 0.8056)
v_gain_n127 = (res127.adc49_neg[c] - res127.adc49_zero[c]) * 0.8056
v_gain_p127 = (res127.adc49_pos[c] - res127.adc49_zero[c]) * 0.8056
v_gain_n64  = (res64.adc49_neg[c]  - res64.adc49_zero[c])  * 0.8056
v_gain_p64  = (res64.adc49_pos[c]  - res64.adc49_zero[c])  * 0.8056
```

---

## 5. Visualization Architecture & Graphic Standards

To present the raw uncompensated landscape clearly to users and research papers, generate the following 4 core publication plots:

### 1. 3D Spatial Gain Topography (`fig_matrix33_3d_gain_topography.png`)
- **Axes:** $X$-axis = Columns $0..5$, $Y$-axis = Rows $0..5$, $Z$-axis = Gain $\Delta V_{\text{out}}$ (mV) at $W = -80, X = -127, t = 5.0\text{ ms}$.
- **Rendering:** 3D surface with wireframe overlay or 3D bar chart with viridis/plasma colormap.
- **Physical Insight:** Instantly reveals the spatial gain gradients, column rail boundaries, and row-to-row threshold scatter.

### 2. 3D Spatiotemporal Evolution (`fig_matrix33_3d_spatiotemporal.png`)
- Multi-panel 3D surface plot comparing the $6 \times 6$ landscape across 4 key time slices:
  - $t = 1.0\text{ ms}$ (Recharge clamp / zero state)
  - $t = 3.5\text{ ms}$ (Maximum peak sensitivity $>1000\text{ mV}$)
  - $t = 5.0\text{ ms}$ (Nominal settled operating plateau)
  - $t = 8.0\text{ ms}$ (RC discharge decay)

### 3. $6 \times 6$ Crosspoint Grid Multi-Plot (`fig_matrix33_all_36_cells_5curves.png`)
- $6 \times 6$ subplots corresponding to physical matrix crosspoints $(r, c)$.
- Each subplot displays the 5 user-specified color curves:
  - **Curve 1 ($X = -127$):** Blue (`#1976d2`)
  - **Curve 2 ($X = -64$):** Red (`#d32f2f`)
  - **Curve 3 ($X = 0$):** Green (`#388e3c`)
  - **Curve 4 ($X = +64$):** Orange (`#f57c00`)
  - **Curve 5 ($X = +127$):** Yellow (`#fbc02d`)
- Common voltage scale to immediately highlight active vs saturated channels.

### 4. Gain Variance & Null Offset Heatmap (`fig_matrix33_gain_variance_heatmap.png`)
- 2D annotated heatmaps of:
  - (A) Peak Dynamic Sving $\Delta V_{\text{max}} - \Delta V_{\text{min}}$ (mV).
  - (B) Turnaround Rollover Ratio ($V_{W=-80} / V_{W=-127}$).
  - (C) Mid-scale zero offset $\Delta V(X=0, W=0)$.

---

## 6. Data Log Quota Compliance

Per the `data-log-quota` skill:
- Store all structured JSON datasets in `FPGA_code/docs/` with file sizes strictly under 10 MB (well below the 100 MB hard ceiling).
- Do not continuously stream multi-megabyte raw logs to disk in background tasks; execute bounded batch sweeps on explicit user command.

