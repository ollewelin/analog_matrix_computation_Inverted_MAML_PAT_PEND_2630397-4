"""
Demonstration of Per-Cell Vth OFF Variations in 32x32 Matrix

This script shows how each transistor in a realistic batch has different
threshold voltages, causing:
  - Different compression ratios per cell
  - Some transistors falling outside triode region
  - More realistic analog behavior
  - Better MAML training opportunity
"""

import numpy as np
import matplotlib.pyplot as plt
from matrix_core import AtomicTriad
from maml_optimizer import create_test_vectors

def analyze_triode_violations(triad, x_test):
    """
    Analyze how many transistors violate triode condition for test inputs.
    
    Triode violation: V_ds > V_gs - V_th (transistor in saturation)
    
    Returns:
        Dict with violation statistics
    """
    violation_counts = {'M33': 0, 'M3': 0, 'M8': 0}
    total_cells = {'M33': 0, 'M3': 0, 'M8': 0}
    violation_details = {'M33': [], 'M3': [], 'M8': []}
    
    matrices = {'M33': triad.M33, 'M3': triad.M3, 'M8': triad.M8}
    
    for mat_name, matrix in matrices.items():
        # Convert input to row voltages
        V_ds = matrix.V_source + x_test * 0.25
        
        for i in range(matrix.size):
            for j in range(matrix.size):
                cell_idx = i * matrix.size + j
                cell = matrix.cell_bank.cells_active[cell_idx]
                
                # Triode condition: V_ds <= V_gs - V_th
                V_th_eff = cell.V_th_mfg + cell.V_th_variation_offset
                V_gs_eff = cell.V_gs - V_th_eff
                
                total_cells[mat_name] += 1
                
                if V_ds[j] > V_gs_eff:
                    violation_counts[mat_name] += 1
                    violation_details[mat_name].append({
                        'cell': (i, j),
                        'V_ds': V_ds[j],
                        'V_gs': cell.V_gs,
                        'V_th': V_th_eff,
                        'margin': V_gs_eff - V_ds[j]
                    })
    
    return {
        'violation_counts': violation_counts,
        'total_cells': total_cells,
        'violation_rate': {k: violation_counts[k] / total_cells[k] 
                          for k in violation_counts},
        'details': violation_details
    }

def print_per_cell_vth_statistics(triad):
    """Print statistics about per-cell Vth variations."""
    print("\n" + "="*80)
    print("PER-CELL Vth OFF VARIATION STATISTICS")
    print("="*80)
    
    for mat_name, matrix in [('M33', triad.M33), ('M3', triad.M3), ('M8', triad.M8)]:
        vth_offsets = []
        vth_totals = []
        
        for cell in matrix.cell_bank.cells_active:
            vth_offsets.append(cell.V_th_variation_offset)
            vth_totals.append(cell.V_th_mfg + cell.V_th_variation_offset)
        
        vth_offsets = np.array(vth_offsets)
        vth_totals = np.array(vth_totals)
        
        print(f"\n{mat_name} Matrix (32x32, 1024 cells):")
        print(f"  Per-cell Vth variation (offset):")
        print(f"    Min:     {vth_offsets.min():+.4f}V")
        print(f"    Max:     {vth_offsets.max():+.4f}V")
        print(f"    Mean:    {vth_offsets.mean():+.4f}V")
        print(f"    Std:     {vth_offsets.std():.4f}V")
        print(f"    Range:   {vth_offsets.max() - vth_offsets.min():.4f}V")
        print(f"  Total Vth (base + offset):")
        print(f"    Min:     {vth_totals.min():.4f}V")
        print(f"    Max:     {vth_totals.max():.4f}V")
        print(f"    Mean:    {vth_totals.mean():.4f}V")
        print(f"    Std:     {vth_totals.std():.4f}V")
        
        # Count cells in different Vth ranges
        cells_below_05 = (vth_totals < 0.5).sum()
        cells_05_07 = ((vth_totals >= 0.5) & (vth_totals < 0.7)).sum()
        cells_above_07 = (vth_totals >= 0.7).sum()
        
        print(f"  Cell distribution by Vth:")
        print(f"    Vth < 0.50V:  {cells_below_05:4d} cells ({100*cells_below_05/1024:.1f}%)")
        print(f"    0.50V ≤ Vth < 0.70V: {cells_05_07:4d} cells ({100*cells_05_07/1024:.1f}%)")
        print(f"    Vth ≥ 0.70V:  {cells_above_07:4d} cells ({100*cells_above_07/1024:.1f}%)")

def run_demonstration():
    """Run complete demonstration of per-cell Vth variations."""
    
    print("\n" + "="*80)
    print("PER-CELL Vth OFF VARIATION DEMONSTRATION")
    print("="*80)
    
    # ==================== SETUP ====================
    print("\n[SETUP] Creating 32x32 system with per-cell Vth variations...")
    
    triad = AtomicTriad(size=32)
    
    # Apply manufacturing variations (uniform across all cells initially)
    config = {
        'V_th_sigma': 0.12,      # ±12% threshold variation
        'g_m_sigma': 0.15,       # ±15% transconductance variation
        'R_sigma': 0.15,         # ±15% resistance variation
    }
    
    for matrix in [triad.M33, triad.M3, triad.M8]:
        matrix.inject_manufacturing_variations(config)
        matrix.inject_thermal_drift(temp_delta_C=30.0)
        matrix.inject_noise(noise_sigma=0.02)
    
    print(f"  Applied manufacturing variations:")
    print(f"    - V_th manufacturing tolerance: ±12%")
    print(f"    - g_m manufacturing tolerance: ±15%")
    print(f"    - R manufacturing tolerance: ±15%")
    print(f"    - Thermal stress: +30°C")
    print(f"    - Noise: 2%")
    
    # ==================== PER-CELL VARIATIONS ====================
    print("\n  Applying per-cell Vth OFF variations (±10%)...")
    triad.apply_per_cell_vth_variations(vth_variation_sigma=0.06)
    print(f"    ✓ Each transistor now has unique Vth OFF voltage")
    print(f"    ✓ Realistic batch-to-batch variation")
    print(f"    ✓ Some transistors will fall outside triode region")
    
    # ==================== STATISTICS ====================
    print_per_cell_vth_statistics(triad)
    
    # ==================== TRIODE VIOLATIONS ====================
    print("\n" + "="*80)
    print("TRIODE REGION VIOLATION ANALYSIS")
    print("="*80)
    
    # Test with various inputs
    test_inputs = [
        ('Random (0-1)', np.random.uniform(0, 1, 32)),
        ('Low (0.3)', np.full(32, 0.3)),
        ('Mid (0.5)', np.full(32, 0.5)),
        ('High (0.8)', np.full(32, 0.8)),
    ]
    
    for test_name, x_test in test_inputs:
        print(f"\n  Input condition: {test_name}")
        violations = analyze_triode_violations(triad, x_test)
        
        for mat_name in ['M33', 'M3', 'M8']:
            rate = violations['violation_rate'][mat_name]
            count = violations['violation_counts'][mat_name]
            total = violations['total_cells'][mat_name]
            
            print(f"    {mat_name}: {count:4d}/{total} cells in saturation ({100*rate:5.1f}%)")
    
    # ==================== CELL HETEROGENEITY ====================
    print("\n" + "="*80)
    print("CELL HETEROGENEITY DEMONSTRATION")
    print("="*80)
    
    print("\n  Sample cells from M33 matrix (showing per-cell Vth variation impact):")
    print("  [Cell(i,j)] : Vth_base + Vth_offset = Vth_total | Triode_margin | Compression")
    print("  " + "-"*75)
    
    cells_sample = [
        (0, 0), (0, 10), (0, 31),
        (15, 15),
        (31, 0), (31, 15), (31, 31)
    ]
    
    for i, j in cells_sample:
        cell_idx = i * 32 + j
        cell = triad.M33.cell_bank.cells_active[cell_idx]
        
        vth_base = cell.V_th_mfg
        vth_offset = cell.V_th_variation_offset
        vth_total = vth_base + vth_offset
        margin = cell.V_gs - vth_total
        
        # Compression indicator: lower margin = harder compression
        if margin < 0.5:
            compression = "SEVERE"
        elif margin < 1.0:
            compression = "HEAVY"
        elif margin < 1.5:
            compression = "MODERATE"
        else:
            compression = "MILD"
        
        print(f"  [{i:2d},{j:2d}]: {vth_base:.4f}V + {vth_offset:+.4f}V = {vth_total:.4f}V | "
              f"Margin: {margin:+.4f}V | {compression}")
    
    # ==================== SUMMARY ====================
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    print("\n✓ IMPROVEMENTS WITH PER-CELL Vth VARIATIONS:")
    print("\n  1. REALISM:")
    print("     - Each transistor has unique Vth OFF voltage")
    print("     - Mimics real-world batch variation of transistors")
    print("     - Different compression ratios per cell")
    print("\n  2. TRIODE REGION DYNAMICS:")
    print("     - Some transistors naturally fall outside triode region")
    print("     - Creates non-linear effects at cell level")
    print("     - More complex learning landscape for MAML")
    print("\n  3. TRAINING OPPORTUNITY:")
    print("     - MAML must learn to compensate for heterogeneous cells")
    print("     - Higher accuracy improvement potential")
    print("     - More representative of real analog hardware")
    print("\n  4. OBSERVABLE EFFECTS:")
    print("     - Different cells achieve different precision at end-states")
    print("     - Weight variation effects become more pronounced")
    print("     - Voltage swing and signal-to-noise ratio varies per cell")
    
    print("\n" + "="*80)
    print("DEMONSTRATION COMPLETE")
    print("="*80 + "\n")

if __name__ == "__main__":
    run_demonstration()
