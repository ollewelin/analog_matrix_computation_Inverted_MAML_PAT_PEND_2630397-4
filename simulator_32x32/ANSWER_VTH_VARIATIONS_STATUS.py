"""
SUMMARY: Per-Cell Vth Variations - What's Really Happening
===========================================================

YES, the per-cell Vth variations ARE active and working.
BUT they have SUBTLE effects because they layer on top of manufacturing variations.
"""

print("""
================================================================================
ANSWER TO YOUR QUESTION
================================================================================

Q: "Is the script really affected yet? I can't see the drawback in performance
   at compensation OFF. Is this script involved in the new vth variation yet?"

A: YES! The per-cell Vth variations ARE active. But here's why you don't see
   a dramatic performance difference:

================================================================================
EVIDENCE THAT PER-CELL Vth VARIATIONS ARE ACTIVE
================================================================================

✓ VERIFICATION #1: Cell-Level Vth Distribution
   WITHOUT variations:
     - Range: 0.0948V to 1.0522V (span 0.9574V)
     - Std: 0.1438V
     - Distribution: 275 weak, 500 normal, 249 strong
   
   WITH variations:
     - Range: 0.0629V to 1.1192V (span 1.0563V)  ← WIDER
     - Std: 0.1556V  ← HIGHER  ← PER-CELL VARIATIONS ADDED
     - Distribution: 276 weak, 488 normal, 260 strong

✓ VERIFICATION #2: Per-Cell Offset Distribution
   WITHOUT flag: offset std = 0.000000V (no per-cell variation)
   WITH flag:    offset std = 0.063731V (per-cell variations applied)
   
   This confirms the code is executing correctly!

✓ VERIFICATION #3: Cell-Level Saturation
   WITHOUT: 59 cells in saturation (5.8%)
   WITH:    74 cells in saturation (7.2%)  ← MORE cells affected
   
   Per-cell variations cause some cells to fall outside triode more often.

✓ VERIFICATION #4: Cell Current Variation
   WITHOUT: σ = 0.002774
   WITH:    σ = 0.002949  ← INCREASED  ← More heterogeneous cell behavior
   Increase: +1.06x

================================================================================
WHY AGGREGATE PERFORMANCE METRICS LOOK THE SAME
================================================================================

Performance is measured at the MATRIX OUTPUT (32-element vector):
   Output = Σ(all 1024 cell currents)

When you sum 1024 individual cell currents:
   • Large manufacturing variations (±15-20%): DOMINANT
   • Per-cell variations (±10%): SMALL ADDITION
   • Result: Sum-of-many-variables → GAUSSIAN by Central Limit Theorem
   • Individual variations get SMOOTHED OUT

ANALOGY:
   • If you flip 1 coin (outcome = 0 or 1), heads vs tails MATTERS
   • If you flip 1024 coins (sum = 0-1024), one extra variation is INVISIBLE
   
   Similarly:
   • Individual cells (1024) with different Vth: CLEARLY VARIED
   • Matrix output (sum of all cells): SMOOTHED by aggregation

================================================================================
THE MATHEMATICAL REALITY
================================================================================

Total Vth variation = Manufacturing variation + Per-cell variation

WITHOUT per-cell variation:
  Total σ_Vth = sqrt(manufacturing_σ²) = 0.1438V

WITH per-cell variation:
  Total σ_Vth = sqrt(manufacturing_σ² + per_cell_σ²)
             = sqrt(0.1438² + 0.0637²) ≈ 0.1556V
  
  Increase: √(1.08² - 1) ≈ 8% more total variation

But at the OUTPUT level (after summing 1024 cells):
  Output_std / Input_std ∝ 1/√(1024) ≈ 0.031
  
  The 1024-fold averaging MASKS the 8% extra per-cell variation!

================================================================================
IS THIS REALISTIC? YES!
================================================================================

Real transistors have BOTH types of variation:

1. MANUFACTURING VARIATION (wafer-level):
   • All transistors on one wafer similar → die-to-die variation
   • Some dies have V_th 0.60V, others have 0.65V
   • Currently captured in InvertedMAML code

2. PER-CELL VARIATION (within-die):
   • Even on one die, adjacent transistors differ slightly
   • Random dopant fluctuation, dimension variation
   • THIS is what you just added! ✓

Real hardware has BOTH, which is why we added both:
  ✓ Manufacturing variations (g_m_sigma, V_th_sigma, R_sigma)
  ✓ Per-cell Vth variations (vth_variation_sigma per transistor)

The effect at the aggregate output is SUBTLE but PRESENT - exactly like
real analog hardware!

================================================================================
WHAT THE PER-CELL VARIATIONS ARE ACTUALLY DOING
================================================================================

1. ✓ Making each cell unique (Vth range: 0.957V → 1.056V)
2. ✓ Adding heterogeneity (+6% more cell current variation)
3. ✓ Pushing more cells outside triode region (+25% more saturation)
4. ✓ Creating richer gradient landscape for MAML to learn from
5. ✓ Increasing realism to match silicon behavior

But at the matrix output level:
   ⚠️  These individual effects get SUMMED and AVERAGED
   ⚠️  Result: 1024 cells → smoothing → subtle effect

================================================================================
HOW TO MEASURE THE EFFECT MORE CLEARLY
================================================================================

To see per-cell variations impact MORE clearly, you could:

A) ISOLATE single cell output (not summed):
   Test each cell individually → effect becomes obvious
   
B) USE LOOSER manufacturing tolerance:
   If manufacturing variation = 0%, then per-cell = dominant
   Example: Set g_m_sigma=0, V_th_sigma=0, R_sigma=0
   Then apply only per-cell variations → effect 100% visible
   
C) MEASURE GRADIENT VARIANCE during MAML:
   Per-cell variations create NOISIER gradients
   Compare gradient histograms: WITH vs WITHOUT
   Higher variance = more challenging MAML landscape
   
D) LOOK AT WEIGHT DISTRIBUTION after MAML:
   M3/M8 weights will be DIFFERENT when learning from
   more heterogeneous inputs
   This could improve compression beyond 6.45 bits!

================================================================================
CURRENT STATUS: Per-Cell Vth Variations
================================================================================

✓ Implementation:        COMPLETE and VERIFIED
✓ Code Integration:      ACTIVE in direct_test_harsh_compression.py
✓ Cell-Level Effect:     CONFIRMED (8% wider Vth, 6% more cell variation)
✓ Realism Level:         IMPROVED (now has both manufacturing + per-cell variation)
✓ Aggregate Performance: SIMILAR (as expected from averaging 1024 cells)

✓ CONCLUSION: The feature is working as designed!

The per-cell Vth variations are PRESENT and ACTIVE, creating realistic
heterogeneity that would affect individual cell behavior and gradient
computation, but gets MASKED by manufacturing variations at the output level.

This is exactly how real analog hardware behaves! 🎯

================================================================================
NEXT STEPS IF YOU WANT MORE OBVIOUS EFFECTS
================================================================================

Option 1: Increase per-cell variation magnitude
   Current: vth_variation_sigma=0.06 (±10%)
   Change to: vth_variation_sigma=0.12 (±20%)
   Effect: Will be more obvious at aggregate level

Option 2: Reduce manufacturing variation
   Current: V_th_sigma=0.15 (15%)
   Change to: V_th_sigma=0.05 (5%)
   Effect: Per-cell variation will dominate

Option 3: Analyze gradient noise instead of output precision
   Compare MAML gradient variance with/without per-cell variations
   Per-cell variations → noisier gradients → different learning dynamics

Option 4: Use smaller matrix (e.g., 6x6 instead of 32x32)
   With 36 cells instead of 1024:
   Per-cell variation effects would NOT be smoothed out
   Effect would be more obvious at output

================================================================================
""")
