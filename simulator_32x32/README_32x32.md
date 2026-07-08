# 32×32 Inverted MAML Simulator

Scaled-up version from 6×6 to 32×32 matrices (16× more cells)

## Architecture

```
┌──────────────────────┐
│  32-dim Input (x)    │
└──────────┬───────────┘
           │
      ┌────┴────┐
      │          │
      ▼          ▼
   [M33]      [M3 + tanh]
    32×32      32×32
   (1024)      (1024)
     ▼          ▼
     │          ▼
     │        [M8]
     │        32×32
     │       (1024)
     │        ▼
     └────────┼────────┐
              │        │
              ▼        │
         [SUM + norm]  │
              │        │
              ▼        ▼
         32-dim output
```

## Files

| File | Purpose |
|------|---------|
| `cell_physics.py` | 2T1C cell model (size-agnostic) |
| `matrix_core.py` | 32×32 matrices + Atomic Triad |
| `maml_optimizer.py` | Stratified MAML optimizer (dimension: 32) |
| `direct_test_32x32.py` | Pure algorithm test (no physical effects) |

## Key Parameters

```
Matrix Size:      32×32 (1,024 cells per matrix)
Total Cells:      3,072 (3 matrices × 1,024)
Input Dimension:  32
Output Dimension: 32
Architecture:     M33 (FIXED) + M8(tanh(M3)) (TRAINED)
```

## How to Run

### Quick Test (100 cycles)
```bash
python direct_test_32x32.py
```

### Expected Output
```
Configuration:
  Matrix size: 32×32 (1024 cells per matrix)
  Total cells: 3072 (3 matrices)
  Input dimension: 32
  Training cycles: 100
  Samples per cycle: 16
  Architecture: M33(FIXED) + M8(tanh(M3))

Starting training...
  Cycle   0: X.XX bits | Loss: 0.XXXXXX
  Cycle  10: X.XX bits | Loss: 0.XXXXXX
  ...
  Cycle  90: X.XX bits | Loss: 0.XXXXXX

Final Results (32×32 Matrix):
  Cycle 0:    X.XX bits (initial)
  Cycle 10:   X.XX bits
  Cycle 99:   X.XX bits (final)
  Improvement: +X.XX bits

✓ SUCCESS: Reached target (X.XX >= 5.5)
```

## Comparison: 6×6 vs 32×32

| Metric | 6×6 | 32×32 | Scale |
|--------|-----|-------|-------|
| Matrix cells | 36 | 1,024 | 28× |
| Total cells | 108 | 3,072 | 28× |
| Input dim | 6 | 32 | 5.3× |
| Computation | Fast | Slower | ~28× |
| Theoretical capacity | ~3 bits | ~5-6 bits | +2-3 bits |

## Physical Effects (Optional)

Can enable realistic effects:
```python
triad.inject_manufacturing_variations({
    'V_th_sigma': 0.03,    # ±3% variation
    'g_m_sigma': 0.05,     # ±5% variation
    'R_sigma': 0.05        # ±5% variation
})
triad.inject_thermal_drift(temp_delta_C=12.0)  # +12°C
triad.inject_noise(noise_sigma=0.005)          # 0.5% noise
```

## Architecture Notes

1. **M33 (Primary 32×32)**
   - Contains random weights for matrix multiplication
   - FIXED (not trained)
   - Provides baseline computation

2. **M3 (Correction 32×32)**
   - Learns nonlinear compensation for M33 errors
   - Uses tanh activation (steep gradient region)
   - Output scaled 7× for optimal sigmoid operation
   - TRAINED via backprop

3. **M8 (Correction 32×32)**
   - Combines M3 output with M33 baseline
   - Learns linear weighting of correction
   - TRAINED via backprop

## Key Differences from 6×6

- ✓ Larger problem space (32-dim vectors vs 6-dim)
- ✓ More cell-level interactions
- ✓ Potentially higher precision (more capacity)
- ✓ Longer compute time per cycle
- ✓ Matches hardware scaling (future 32×32 layouts)

## Expected Performance

- **Without physical effects**: 5-7 bits convergence
- **With physical effects**: 4-6 bits (depending on distortion)
- **6-bit target**: Should be achievable with training

## Next Steps

1. Run `direct_test_32x32.py` to verify baseline performance
2. Add physical effects and test robustness
3. Compare precision vs 6×6 version
4. Scale up further (64×64, 128×128)

---

**Created**: 2026-07-07  
**Scale factor**: 32×32 (from 6×6)  
**Total cells**: 3,072 (M33 + M3 + M8)
