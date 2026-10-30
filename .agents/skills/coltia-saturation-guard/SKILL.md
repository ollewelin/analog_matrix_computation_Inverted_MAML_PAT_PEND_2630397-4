---
name: coltia-saturation-guard
description: Diagnostic tool, protection rules, and operating protocol for physical ColTIA transimpedance amplifier and XC2361A ADC saturation ("bottning") on Inverted MAML silicon. Explains why Hadamard demodulation creates phantom gradient bursts when the analog signal exceeds available headroom, details the 243 LSB safety margin, zero-mean centering (LayerNorm), and automatic telemetry alarms.
---

# ColTIA Saturation Guard (Anti-Distortion & Headroom Protection Protocol)

## 1. Physical Phenomenon ("Bottning" / Clipping)

The Inverted MAML analog core features dual transimpedance column amplifiers (ColTIA) driving differential 12-bit ADCs (ADC_45 and ADC_49).
- **Nominal ADC dynamic range**: $[-2048, +2047]\text{ LSB}$ ($0\text{ LSB} = 1.65\text{ V}$ common mode virtual ground).
- **Hadamard perturbation step swing**: Measured directly on physical silicon via `diag_hadamard(mode=9)`:
  - Peak-to-peak step swing on Layer 1 (ADC_45): **$243\text{ LSB}$** ($250\text{ LSB}$ nominal).
  - Peak-to-peak step swing on Output (ADC_49): **$57\text{ LSB}$**.

```
    ADC Rail (+2047 LSB) ----------------------------------------------------
                                ▲
                                │  HADAMARD_MAX_SWING_LSB = 250 LSB (Headroom Margin)
                                ▼
    Clip Threshold (+1797 LSB)  =============================================  <-- COLTIA_CLIP_THRESHOLD_LSB
                                │
                                │  Linear Operating Region (Fast Walsh-Hadamard Demodulation OK)
                                │  FWHT: (Y_pos - Y_neg) recovers clean symmetric perturbation
                                │
    Zero Center (0 LSB)         --------------------------------------------- (1.65 V Quiescent virtual ground)
                                │
                                │
    Clip Threshold (-1797 LSB)  =============================================  <-- COLTIA_CLIP_THRESHOLD_LSB
                                ▲
                                │  250 LSB Margin
                                ▼
    ADC Rail (-2048 LSB) ----------------------------------------------------
```

### Why Saturation Creates Violent Gradient Spikes ("Hysteriska Ryck")
The inner-loop gradient extraction relies on exact orthogonal Sylvester $H_8$ Simplex demodulation (14 interleaved $\pm$ pulses over $28\ \mu\text{s}$):
$$\frac{\partial L}{\partial W_{i,j}} = \langle \Delta Z_j, V_i^{\text{PTU}} \rangle_H \cdot E_j$$
- When the quiet operating point sits close to the rail ($|ADC| > 1797\text{ LSB}$), the $+250\text{ LSB}$ Hadamard pulse hits the power rail or ADC plateau ($+2047\text{ LSB}$).
- The positive pulse clips flat while the negative pulse swings freely.
- This **destroys wave symmetry and orthogonality** ($\langle H_i, H_j \rangle \ne 0$).
- FWHT demodulation interprets this non-linear clipping as massive, non-existent sensitivities across all rows simultaneously ("phantom gradient burst").
- The weights take an unphysical violent leap, which pushes the circuit even further into saturation, locking the system in permanent distortion.

---

## 2. Headroom Margin Rule & Detection Threshold

To ensure that the 14-pulse Hadamard carrier can complete its full $\pm 243\text{ LSB}$ excursion without ever touching the saturation plateau:

$$\text{COLTIA\_CLIP\_THRESHOLD\_LSB} = 2047 - 250 = 1797\text{ LSB}$$

### Rules Enforced on Master T120 RISC-V SoC:
1. **Immediate Headroom Detection**:
   Immediately after quiet forward-pass ADC conversion, if any column $|ADC_{45}[c]| \ge 1797$ or $|ADC_{49}[c]| \ge 1797$, column bitmask `g_col_clip_mask |= (1 << c)` is flagged and `g_clip_events_cnt` is incremented.
2. **Zero Weight Mutation on Clipped Epochs**:
   If `g_col_clip_mask != 0`, the training step **MUST NOT UPDATE WEIGHTS** ($\Delta W \equiv 0$). Gradients derived from clipped waveforms are corrupted and immediately suppressed.
3. **Telemetry Streaming**:
   Live telemetry packet `maml_telemetry_pkt_t` streams:
   - `clip_events_cnt` (uint16)
   - `col_clip_mask` (uint8)
   - `last_clip_adc_id` (uint8: 45 or 49)

---

## 3. LayerNorm / Zero-Mean Centering Countermeasure

When feeding correlated In-Data (such as LLM Toeplitz embeddings with $\rho = 0.85$ or GELU activations):
- Highly correlated inputs can cause all 6 input channels to take simultaneous negative or positive values (e.g. `[-23, -18, -23, -22, -20, -14]`).
- Matrix $M_{33}$ has a net positive column pedestal ($+114$ to $+128\text{ LSB}$).
- Multiplying a large common-mode negative vector through positive weights creates a massive aggregate negative current:
  $$\sum_i x_i \cdot W_i \gg I_{\text{linear\_max}}$$
  slamming the single-supply ColTIA op-amps against the $0\text{ V}$ rail.

### LayerNorm Rule:
For all colored In-Data modes (`g_color_mode != COLOR_WHITE`), the T120 SoC automatically applies zero-mean spatial centering:
$$x_i \leftarrow x_i - \frac{1}{6}\sum_{k=0}^{5} x_k$$
This guarantees $\sum x_i \equiv 0$, eliminating common-mode DC current drift while preserving the relative spatial token correlation.

---

## 4. Diagnostics & Live Verification CLI

To inspect the saturation guard status and verify that headroom margins are respected on physical silicon:

```bash
/home/olle/anaconda3/bin/python FPGA_code/scripts/maml_w33_and_color_ctl.py --show
```

Output format:
```text
ENOB (Sustained/Comp)  : 4.10 bits (Uncomp: 4.09 bits)
ColTIA Saturation Guard: 0 clipped epochs suppressed | Mask=0b000000 (ADC0) OK (Linear)
```

If clipping occurs under extreme external stress:
```text
ColTIA Saturation Guard: 14 clipped epochs suppressed | Mask=0b000100 (ADC45) [!] HEADROOM MARGIN EXCEEDED - CLIPPING
```
The system will safely hold its weights without runaway spiking or weight rail exhaustion until the input returns to linear headroom.

