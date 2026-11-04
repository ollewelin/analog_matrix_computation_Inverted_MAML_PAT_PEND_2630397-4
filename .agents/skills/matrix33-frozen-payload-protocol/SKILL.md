---
name: matrix33-frozen-payload-protocol
description: Exact frozen reference payload weights for Matrix 33 (M33 6x6 analog multiplier), weight compression scaling (compress_m33_weight), and hidden hardware disturbance protocol (Patent SE 2630397-4 Fig 7 Emulator) for Inverted MAML silicon.
---

# Matrix 33 Frozen Reference Payload & Disturbance Protocol Skill
**Patent Pending SE 2630397-4 | Open Science Hardware**  
**Target Hardware:** Trion T120 Master SoC + Trion T20 Coprocessor (`192.168.1.50:5000`)

This skill documents and permanently preserves the **exact original frozen reference matrix** for **Matrix 33** (`M33`, $6\times 6$ analog multiplier payload), its mathematical scaling protocol (`compress_m33_weight`), and the **Patent Fig 7 Emulator of Changing Hardware States** protocol for hidden weight perturbations.

---

## 1. Original Factory Reference Matrix (`ORIGINAL_M33`)

This is the exact, uncompressed, factory-calibrated reference matrix hardcoded in the T120 firmware (`k_default_m33` in `FPGA_code/sw/t120_master/src/maml_platform.c`):

```c
static const int8_t k_default_m33[6][6] = {
    { +76, -20, +28,  -4, +44, -36 },  /* Row 0 */
    { -20, +84, -12, +44,  -4, +36 },  /* Row 1 */
    { +36,  -4, +80, -16, +32,  -4 },  /* Row 2 */
    {  -4, +40,  -8, +72, -12, +44 },  /* Row 3 */
    { +44, -12, +28, -12, +76,  -8 },  /* Row 4 */
    { -28, +32,  -4, +40,  -8, +82 }   /* Row 5 */
};
```

### Python Representation
```python
ORIGINAL_M33 = [
    [+76, -20, +28,  -4, +44, -36],  # Row 0
    [-20, +84, -12, +44,  -4, +36],  # Row 1
    [+36,  -4, +80, -16, +32,  -4],  # Row 2
    [ -4, +40,  -8, +72, -12, +44],  # Row 3
    [+44, -12, +28, -12, +76,  -8],  # Row 4
    [-28, +32,  -4, +40,  -8, +82],  # Row 5
]
```

### Physical & Analytical Properties
- **Dimension:** $6 \times 6$ crosspoints (36 physical Dual-2T1C differential triode cells).
- **Diagonals:** Strong positive diagonal dominance:
  $[+76, +84, +80, +72, +76, +82]\text{ LSB}$ (mean $+78.3\text{ LSB}$).
- **Off-Diagonals:** Bipolar cross-coupling terms ranging from $-36\text{ LSB}$ to $+44\text{ LSB}$.
- **Full Swing Range:** $[-36, +84]\text{ LSB}$ (differential voltage on gate capacitors).
- **Mathematical Conditioning:** Diagonally dominant, full rank ($\det \neq 0$), non-singular.

---

## 2. Weight Compression Protocol (`compress_m33_weight`)

To investigate whether reducing the gate voltage swing on Matrix 33 prevents cell pinch-off and improves linearity when input swing on DAC(2) is increased to $\pm 80\text{ LSB}$, weights are scaled symmetrically around zero:

$$W^{(33)}_{\text{nominal}}[r][c] = \text{round}\left( \frac{W^{(33)}_{\text{orig}}[r][c]}{\text{compress\_m33\_weight}} \right)$$

### Compressed Matrix at `compress_m33_weight = 2.0` (Half Swing)
When `compress_m33_weight = 2.0`, the matrix is scaled by $0.5\times$:

```python
COMPRESSED_M33_DIV2 = [
    [+38, -10, +14,  -2, +22, -18],  # Row 0
    [-10, +42,  -6, +22,  -2, +18],  # Row 1
    [+18,  -2, +40,  -8, +16,  -2],  # Row 2
    [ -2, +20,  -4, +36,  -6, +22],  # Row 3
    [+22,  -6, +14,  -6, +38,  -4],  # Row 4
    [-14, +16,  -2, +20,  -4, +41],  # Row 5
]
```
- **New Diagonal:** $[+38, +42, +40, +36, +38, +41]\text{ LSB}$ (mean $+39.2\text{ LSB}$).
- **New Swing Range:** $[-18, +42]\text{ LSB}$.
- **Physical Impact:** Dual-2T1C gate storage capacitors stay strictly within the linear triode region, eliminating gate-induced subthreshold turnaround.

---

## 3. Patent Fig 7: Emulator of Changing Hardware States Protocol

Patent SE 2630397-4 Figure 7 illustrates the **Emulator of Changing Hardware States**:
- An analog hardware block injecting hidden random disturbances ($W^{(3,8,33)}_{i,j} + \text{Hidden offset}_{i,j}$, $\text{DAC}(2) + \text{Hidden offset}_i$, $\text{ADC}(45,49) + \text{Hidden offset}_j$).

### Absolute Non-Cheating Requirement ("Fusk-skydd")
> [!CAUTION]
> **CRITICAL RULE:** The Digital Target Controller in the T120 Master SoC and in software evaluation MUST ALWAYS compute $Z_{\text{target}}$ and ENOB strictly against the **unperturbed nominal weights** $W^{(33)}_{\text{nominal}}$.
> 
> Under NO CIRCUMSTANCES may $Z_{\text{target}}$ be computed using the perturbed physical weights:
> $$Z_{\text{target}} = \text{Target\_Gain} \cdot \left( W^{(33)}_{\text{nominal}} \cdot X_{\text{ref}} \right)$$
> 
> If the digital controller recomputes $Z_{\text{target}}$ using the hidden offset, it "cheats" and bypasses the entire physical adaptation loop. The Inverted MAML inner loop on M3/M8 MUST discover and cancel the physical disturbance purely through analog gradient descent!

### Perturbation Cadence & Parameter `w_33_variance_lsb_range`
1. **Parameter:** `w_33_variance_lsb_range` (integer LSB, default `0`).
2. **Nominal Mode (`range = 0`):** 100% frozen, physical weights equal $W^{(33)}_{\text{nominal}}$.
3. **Disturbance Mode (`range > 0`, e.g. `5`):**
   - At every 100-epoch boundary (Epoch 100, 200, 300, 400...), each of the 36 physical cells draws an independent uniform integer disturbance:
     $$\delta_{r,c} \sim \mathcal{U}[-\text{range}, +\text{range}]$$
   - Physical weight loaded onto silicon:
     $$W^{(33)}_{\text{physical}}[r][c] = \text{clamp}(W^{(33)}_{\text{nominal}}[r][c] + \delta_{r,c}, -120, +120)$$
   - The digital target model $Z_{\text{target}}$ remains rigidly locked to $W^{(33)}_{\text{nominal}}$.

