# Inverted MAML: Mode B Silicon Report (Calibrated Baseline Offset)
**Patent Pending SE 2630397-4 | Open Science Hardware**
**Document ID:** `MODE_B_100EP_OPT_OFFSET_REPORT`
**Date:** 2026-10-30
**Target Hardware:** Trion T120 Master SoC @ `192.168.1.50:5000` (PCB v1.3.2)
**Firmware:** Logic `0x20261030` | C-Firmware `v2.1-MAML`

---

## 1. Executive Summary & Constraints Verification

This report documents the verification run of standalone Matrix 33 in **Mode B** on physical silicon, conducted under strict protocol constraints:
1. **Identical Input Swing:** Input vector $X$ was generated using the identical white-noise rotating PRNG range (`[-45, +45]`, `d_line=1`) as used in Mode A.
2. **Identical Frozen Weight Matrix:** Primary payload matrix $W_{33}$ was held **strictly frozen** to the exact default matrix `k_default_m33` with `w33=1`. No weight scaling or adaptation was performed.
3. **Physical Mode B Jumpers:** Physical jumpers placed in Mode B, disconnecting the Matrix 3 / Matrix 8 compensation loop from the summing junction.
4. **Calibrated Baseline Offset:** The quiescent physical DC offset at the summing junction was measured directly on physical silicon across all 6 columns to eliminate the false -300 LSB Mode A offset artifact.

![Page 1 Preview](file:///home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a/page_mode_b_opt-run01-1.png)

---

## 2. Frozen Weight Matrix $W_{33}$

The primary payload matrix $W_{33}$ is permanently defined in firmware and verified via UDP telemetry:

```
Row 0: [ +76,  -20,  +28,   -4,  +44,  -36 ]
Row 1: [ -20,  +84,  -12,  +44,   -4,  +36 ]
Row 2: [ +36,   -4,  +80,  -16,  +32,   -4 ]
Row 3: [  -4,  +40,   -8,  +72,  -12,  +44 ]
Row 4: [ +44,  -12,  +28,  -12,  +76,   -8 ]
Row 5: [ -28,  +32,   -4,  +40,   -8,  +82 ]
```

---

## 3. Physical Calibration & Results (100 Epochs)

### Baseline DC Offsets at Summing Junction:
$$\mathbf{DC}_{\text{cal}} = [-937.0, -919.6, -1089.7, -528.6, +485.8, +82.1]\text{ LSB}$$

### Performance Metrics:
| Metric | Mode B (Standalone M33) | Mode A (Inverted MAML Compensated) | Delta / Improvement |
| :--- | :---: | :---: | :---: |
| **Mean Loss (LSB²)** | **36,934.2 ± 20,950** | **287.0 ± 120.7** | **-99.2% (128.7x reduction)** |
| **Mean RMSE (LSB)** | **192.18 LSB** | **16.94 LSB** | **11.3x precision gain** |
| **Standard ENOB (bits)** | **3.50 ± 0.36 b** | **6.91 ± 0.33 b** | **+3.41 bits** |
| **IEEE ENOB (bits)** | **2.74 ± 0.36 b** | **6.23 ± 0.33 b** | **+3.49 bits** |
| **Peak Epoch ENOB** | **4.80 b** (Ep 26) | **6.74 b** (Run 03) | **+1.94 bits peak** |

![Page 2 Preview](file:///home/olle/.gemini/antigravity/brain/bb0ca3ae-bf6b-4ffc-b55f-59fb0dae056a/page_mode_b_opt-run01-2.png)

---

## 4. Key Physical Takeaway

By calibrating the summing junction DC offset while keeping the input swing and weights strictly identical to Mode A, the true raw analog precision of the uncompensated triode multiplier matrix $M_{33}$ is established at **3.50 standard bits** (2.74 IEEE bits). 

When the Inverted MAML compensation network (M3 + M8 vernier loop) is engaged in Mode A, it recovers **+3.41 to +3.49 bits**, slashing the quadratic error by **99.2%** down to 287 LSB² (6.91 standard bits / 6.23 IEEE bits).
