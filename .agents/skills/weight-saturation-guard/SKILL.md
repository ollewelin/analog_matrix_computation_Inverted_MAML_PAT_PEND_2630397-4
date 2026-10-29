---
name: weight-saturation-guard
description: Diagnostic tool to audit weight clamping, rail-to-rail saturation, and dynamic range exhaustion in Mode A triode matrices (M3/M8). Use whenever weights hit +/-120 LSB or network convergence stalls.
---

# Weight Saturation Guard

This skill audits whether analog compensation weights in Matrix 3 ($8\times 6$) or Matrix 8 ($7\times 6$) have slammed into the hardware clamp ceiling/floor ($\pm 120\text{ LSB}$).

## Quick Run

```bash
/home/olle/anaconda3/bin/python FPGA_code/scripts/check_weight_saturation.py <path_to_json>
```

Options:
- `--clamp 120`: Hardware clamp boundary (default 120 LSB).
- `--margin 2`: Tolerance threshold (default triggers at $\ge 118\text{ LSB}$).

## What It Detects:
1. **Saturation Epoch**: Identifies the exact moment when the first weight leaves its linear regime and hits the rail.
2. **Exhaustion Ratio**: Calculates the percentage of cells in $M_3$ and $M_8$ that have lost gradient authority.
3. **Explosion/Stall Diagnosis**: Differentiates between physical gradient descent and saturation plateaus.

