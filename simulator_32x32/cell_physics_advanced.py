"""
Advanced Cell Physics Layer: 2T1C + Resistive IR Drop Warping
Extends cell_physics.py with interconnect resistance effects.

New Features:
  - Row/Column metal line resistance (100 mΩ - 1 Ω)
  - IR drop effects: V_drop = I·R varies by position
  - Non-uniform distortion: cells at matrix edges see different gate voltages
  - Current-dependent warping: higher data → larger distortion

Physics Model:
  - Metal resistance: R_row = R_base * (1 + temp_factor)
  - Current through interconnect: I_row = sum of all cell currents in row
  - Voltage drop: V_drop_row = I_row * R_row
  - Effective gate: V_gs_eff = V_gs - (V_drop_row + V_drop_col) / 2

This adds realistic parasitic effects common in large analog arrays.
"""

import numpy as np
from typing import Dict, Tuple, Optional
from cell_physics import AnalogCell, ReferenceCell, BiasCell


class AnalogCellWithIRDrop(AnalogCell):
    """
    Extended analog cell that accounts for resistive voltage drops from interconnect.
    
    Additional attributes:
        row_index: Position in matrix (0 to size-1)
        col_index: Position in matrix (0 to size-1)
        matrix_size: Total matrix dimension
        V_drop_row: Voltage drop on row interconnect (V)
        V_drop_col: Voltage drop on column interconnect (V)
    """
    
    def __init__(self, cell_id: int, row_index: int = 0, col_index: int = 0, 
                 matrix_size: int = 32, V_th: float = 0.6, g_m_scale: float = 1.0e-2,
                 C_w: float = 100e-9, R_discharge: float = 1.0e6, 
                 is_reference: bool = False):
        """Initialize cell with position tracking for IR drop effects."""
        super().__init__(cell_id, V_th, g_m_scale, C_w, R_discharge, is_reference)
        
        # Position tracking
        self.row_index = row_index
        self.col_index = col_index
        self.matrix_size = matrix_size
        
        # IR drop state
        self.V_drop_row = 0.0
        self.V_drop_col = 0.0
        self.I_from_cell = 0.0
    
    def compute_output_with_ir_drop(self, V_ds: float) -> float:
        """
        Compute output current accounting for IR drop warping.
        
        Args:
            V_ds: Drain-source voltage (data row voltage)
        
        Returns:
            Output current (reduced by effective V_gs due to IR drops)
        """
        # Effective parameters with manufacturing variation
        V_th_eff = self.V_th_mfg
        g_m_eff = self.g_m_mfg
        
        # Gate voltage reduced by row/column IR drops
        # Cells at matrix edges (far from supply) see larger drops
        V_gs_eff_reduced = self.V_gs - V_th_eff - (self.V_drop_row + self.V_drop_col) / 2.0
        
        # Check triode condition with reduced gate voltage
        if V_ds > V_gs_eff_reduced:
            # Saturation: minimal current
            I_out = g_m_eff * 1e-8
        else:
            # Triode: reduced current due to lower gate voltage
            I_out = g_m_eff * (V_gs_eff_reduced - V_ds / 2.0) * V_ds
        
        # Store for interconnect calculations
        self.I_from_cell = abs(I_out)
        
        # Add thermal noise
        if self.noise_sigma > 0:
            noise = np.random.normal(0, self.noise_sigma * abs(I_out))
            I_out += noise
        
        return I_out
    
    def set_ir_drops(self, V_drop_row: float, V_drop_col: float):
        """Set current row/column voltage drops for this cell."""
        self.V_drop_row = V_drop_row
        self.V_drop_col = V_drop_col


class CellBankWithResistiveWarping:
    """
    Cell bank extended with row/column interconnect resistance modeling.
    
    Architecture:
        - Active cells: (size × size) cells forming computation
        - Row interconnects: size lines, each carrying sum of cell currents
        - Column interconnects: size lines, each carrying sum of cell currents
        - Reference cells: size fast-decay cells
        - Bias cells: size hardware bias cells
    """
    
    def __init__(self, num_active: int = 1024, num_reference: int = 32, 
                 num_bias: int = 32, matrix_size: int = 32,
                 R_row_base: float = 0.5, R_col_base: float = 0.5):
        """
        Initialize cell bank with resistive interconnects.
        
        Args:
            num_active: Number of active cells (32×32 = 1024)
            num_reference: Number of reference cells
            num_bias: Number of bias cells
            matrix_size: Matrix dimension (32)
            R_row_base: Base row interconnect resistance (Ω)
            R_col_base: Base column interconnect resistance (Ω)
        """
        self.matrix_size = matrix_size
        self.num_active = num_active
        self.num_reference = num_reference
        self.num_bias = num_bias
        
        # Create active cells with position tracking
        self.cells_active = []
        for i in range(num_active):
            row_idx = i // matrix_size
            col_idx = i % matrix_size
            cell = AnalogCellWithIRDrop(
                cell_id=i, 
                row_index=row_idx, 
                col_index=col_idx,
                matrix_size=matrix_size
            )
            self.cells_active.append(cell)
        
        # Reference and bias cells (no IR drop effects)
        self.cells_reference = [ReferenceCell(i + num_active) for i in range(num_reference)]
        self.cells_bias = [BiasCell(i + num_active + num_reference) for i in range(num_bias)]
        
        self.all_cells = self.cells_active + self.cells_reference + self.cells_bias
        
        # Interconnect resistance
        self.R_row_base = R_row_base  # Ω per row line
        self.R_col_base = R_col_base  # Ω per column line
        self.R_row = np.ones(matrix_size) * R_row_base
        self.R_col = np.ones(matrix_size) * R_col_base
        
        # Current tracking
        self.I_row = np.zeros(matrix_size)
        self.I_col = np.zeros(matrix_size)
        self.V_drop_row = np.zeros(matrix_size)
        self.V_drop_col = np.zeros(matrix_size)
    
    def discharge_step(self, dt_ms: float):
        """Execute discharge for all cells."""
        for cell in self.all_cells:
            cell.discharge_step(dt_ms)
    
    def compute_ir_drops(self, I_cell_matrix: np.ndarray):
        """
        Compute row/column voltage drops based on cell currents.
        
        Args:
            I_cell_matrix: (32, 32) matrix of cell output currents
        """
        # Sum currents per row (cells sharing row interconnect)
        self.I_row = np.sum(np.abs(I_cell_matrix), axis=1)
        
        # Sum currents per column
        self.I_col = np.sum(np.abs(I_cell_matrix), axis=0)
        
        # Temperature-dependent resistance increase
        temp_factor = 1.0 + self.cells_active[0].temperature_delta_C * 0.005
        
        # Compute voltage drops: V = I * R
        self.V_drop_row = self.I_row * self.R_row * temp_factor
        self.V_drop_col = self.I_col * self.R_col * temp_factor
        
        # Update each cell with its row/column drops
        for cell in self.cells_active:
            row_idx = cell.row_index
            col_idx = cell.col_index
            cell.set_ir_drops(self.V_drop_row[row_idx], self.V_drop_col[col_idx])
    
    def inject_manufacturing_variations(self, config: Dict):
        """Inject Gaussian manufacturing tolerances."""
        V_th_sigma = config.get('V_th_sigma', 0.02)
        g_m_sigma = config.get('g_m_sigma', 0.02)
        R_sigma = config.get('R_sigma', 0.02)
        
        for cell in self.cells_active + self.cells_bias:
            cell.inject_manufacturing_variation(V_th_sigma, g_m_sigma, R_sigma)
        
        # Also vary interconnect resistance (±10%)
        self.R_row *= np.random.normal(1.0, 0.1, self.matrix_size)
        self.R_col *= np.random.normal(1.0, 0.1, self.matrix_size)
    
    def inject_thermal_drift(self, temp_delta_C: float):
        """Inject temperature-dependent drift."""
        for cell in self.all_cells:
            cell.inject_thermal_drift(temp_delta_C)
    
    def inject_noise(self, noise_sigma: float):
        """Enable thermal noise on all cells."""
        for cell in self.all_cells:
            cell.inject_noise(noise_sigma)
    
    def get_ir_drop_diagnostics(self) -> Dict:
        """Return diagnostic info about IR drop effects."""
        return {
            'max_row_drop_mV': float(np.max(self.V_drop_row) * 1000),
            'max_col_drop_mV': float(np.max(self.V_drop_col) * 1000),
            'avg_row_drop_mV': float(np.mean(self.V_drop_row) * 1000),
            'avg_col_drop_mV': float(np.mean(self.V_drop_col) * 1000),
            'max_row_current_mA': float(np.max(self.I_row) * 1000),
            'max_col_current_mA': float(np.max(self.I_col) * 1000)
        }
