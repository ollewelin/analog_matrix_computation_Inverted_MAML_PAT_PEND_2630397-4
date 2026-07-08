"""
Advanced Matrix Core Layer: Atomic Triad + Resistive Warping
Extends matrix_core.py with IR drop effects from interconnect resistance.

New Feature:
  - Row/Column interconnect resistance modeling
  - Position-dependent voltage warping
  - Non-linear distortion increases with current
  - Realistic for 32x32+ arrays

Architecture remains:
    input x → M33 (payload) ─┐
                              ├─ [summing point] → output
    input x → M3 → tanh ─ M8 ┘
    
But now with resistive warping in all three matrices.
"""

import numpy as np
from typing import Dict, Tuple, Optional
from cell_physics_advanced import CellBankWithResistiveWarping, AnalogCellWithIRDrop


class AnalogMatrixWithResistiveWarping:
    """
    Single 32x32 analog matrix with resistive IR drop warping.
    
    Structure:
        - Weight storage: 1024 cells (32x32)
        - Reference cells: 32 fast-decay cells
        - Bias cells: 32 hardware bias cells
        - Row interconnects: 32 metal lines with ~0.5 Ω each
        - Column interconnects: 32 metal lines with ~0.5 Ω each
    """
    
    def __init__(self, matrix_id: int, size: int = 32, is_correction: bool = False,
                 R_row_base: float = 0.5, R_col_base: float = 0.5):
        """
        Initialize 32x32 matrix with resistive warping.
        
        Args:
            matrix_id: Identifier (3=payload, 8=2nd correction, 33=primary)
            size: Matrix dimension (32)
            is_correction: If True, weights are trainable
            R_row_base: Base row resistance (Ω)
            R_col_base: Base column resistance (Ω)
        """
        self.matrix_id = matrix_id
        self.size = size
        self.is_correction = is_correction
        
        # Weight storage
        if matrix_id == 33:
            np.random.seed(matrix_id)
            weights_8bit = np.random.randint(0, 256, (size, size))
            self.weights = 2.1 + (weights_8bit / 255.0) * 1.0
        else:
            np.random.seed(matrix_id)
            perturbations = np.random.uniform(-0.05, 0.05, (size, size))
            self.weights = 2.6 + perturbations
        
        # Cell bank with resistive warping
        self.cell_bank = CellBankWithResistiveWarping(
            num_active=size*size,
            num_reference=size,
            num_bias=size,
            matrix_size=size,
            R_row_base=R_row_base,
            R_col_base=R_col_base
        )
        
        # Sync weights to cells
        for i in range(size):
            for j in range(size):
                self.cell_bank.cells_active[i*size + j].V_gs = self.weights[i, j]
        
        # System parameters
        self.V_source = 1.65
        self.tau_discharge = 100.0
        
        # State tracking
        self.last_output = np.zeros(size)
        self.last_I_matrix = np.zeros((size, size))  # Cell current matrix
        self.state_history = []
        self.ir_drop_history = []
    
    def set_weights_8bit(self, weights_8bit: np.ndarray):
        """Set matrix weights from 8-bit values."""
        self.weights = 2.1 + (weights_8bit / 255.0) * 1.0
        for i in range(self.size):
            for j in range(self.size):
                self.cell_bank.cells_active[i*self.size + j].V_gs = self.weights[i, j]
    
    def forward(self, x_input: np.ndarray, t_snapshot_ms: Optional[float] = None) -> Tuple[np.ndarray, Dict]:
        """
        Compute matrix-vector product with resistive warping effects.
        
        Args:
            x_input: (32,) input vector [0, 1]
            t_snapshot_ms: Measurement time within cycle
        
        Returns:
            output: (32,) output vector
            diagnostics: Dict with IR drop info
        """
        # Convert input to gate voltages
        V_in_gate = 1.65 + 0.25 * x_input  # [1.65V, 1.90V]
        
        # Compute cell currents with initial IR drop
        I_matrix = np.zeros((self.size, self.size))
        
        # Iterative computation: solve for equilibrium IR drops
        for iteration in range(3):  # 3 iterations for convergence
            for i in range(self.size):
                for j in range(self.size):
                    cell = self.cell_bank.cells_active[i*self.size + j]
                    V_ds = V_in_gate[j]
                    I_matrix[i, j] = cell.compute_output_with_ir_drop(V_ds)
            
            # Update IR drops based on currents
            self.cell_bank.compute_ir_drops(I_matrix)
        
        # Store for diagnostics
        self.last_I_matrix = I_matrix.copy()
        
        # Sum row currents to get output
        output = np.sum(I_matrix, axis=1)
        
        # Get IR drop diagnostics
        ir_diag = self.cell_bank.get_ir_drop_diagnostics()
        self.ir_drop_history.append(ir_diag)
        
        # Standard diagnostics plus IR drop effects
        diagnostics = {
            'I_matrix': I_matrix,
            'output_raw': output,
            'ir_drops': ir_diag
        }
        
        return output, diagnostics
    
    def refresh_cycle(self):
        """Execute one discharge cycle (10ms)."""
        dt_step = 1.0  # 1ms per step
        for _ in range(10):
            self.cell_bank.discharge_step(dt_step)


class AtomicTriadWithResistiveWarping:
    """
    Complete Inverted MAML with resistive IR drop warping.
    
    Same 3-matrix architecture but now with interconnect resistance effects:
        input x → M33 (with IR drops) ─┐
                                        ├─ output
        input x → M3 (with IR drops) → tanh ─ M8 (with IR drops) ┘
    """
    
    def __init__(self, size: int = 32, R_row_base: float = 0.5, R_col_base: float = 0.5):
        """
        Initialize atomic triad with resistive warping.
        
        Args:
            size: Matrix dimension
            R_row_base: Base row resistance (Ω)
            R_col_base: Base column resistance (Ω)
        """
        self.size = size
        
        self.M33 = AnalogMatrixWithResistiveWarping(
            matrix_id=33, size=size, is_correction=False,
            R_row_base=R_row_base, R_col_base=R_col_base
        )
        self.M3 = AnalogMatrixWithResistiveWarping(
            matrix_id=3, size=size, is_correction=True,
            R_row_base=R_row_base, R_col_base=R_col_base
        )
        self.M8 = AnalogMatrixWithResistiveWarping(
            matrix_id=8, size=size, is_correction=True,
            R_row_base=R_row_base, R_col_base=R_col_base
        )
        
        self.cycle_time_ms = 10.0
        self.current_time_ms = 0.0
        self.ref_matrices = [self.M33, self.M3, self.M8]
    
    def forward(self, x_input: np.ndarray, t_snapshot_ms: Optional[float] = None) -> Tuple[np.ndarray, Dict]:
        """
        Forward pass with resistive warping.
        
        Computation:
            y1 = M33 @ x (with IR drops)
            y2_raw = M3 @ x (with IR drops)
            y2_scaled = y2_raw * 7.0 (optimal tanh region)
            y2 = tanh(y2_scaled)
            y3 = M8 @ y2 (with IR drops)
            output = y1 + y3 (normalized)
        """
        # Primary output with IR drops
        y1, diag1 = self.M33.forward(x_input, t_snapshot_ms)
        
        # Correction path with IR drops
        y_m3_raw, diag2 = self.M3.forward(x_input, t_snapshot_ms)
        
        # Scale M3 output to optimal tanh gradient region (±0.8 to ±1.0)
        y_m3_scaled = y_m3_raw * 7.0
        y_m3_hidden = np.tanh(y_m3_scaled)
        
        # M8 with IR drops
        y3, diag3 = self.M8.forward(y_m3_hidden, t_snapshot_ms)
        
        # Combined output
        output = y1 + y3
        
        # Output normalization: scale to ±0.25V hardware range
        output_normalized = ((output - np.mean(output)) / (np.max(np.abs(output)) + 1e-6)) * 0.25
        output_normalized = np.clip(output_normalized, -0.25, 0.25)
        
        # Aggregate diagnostics matching what maml_optimizer expects
        diagnostics = {
            'input': x_input.copy(),
            'y_payload': y1.copy(),
            'y_m3_raw': y_m3_raw.copy(),
            'y_m3_scaled': y_m3_scaled.copy(),      # CRITICAL: needed by optimizer
            'y_m3_hidden': y_m3_hidden.copy(),      # Pre-tanh activation
            'y_correction': y3.copy(),
            'output_raw': output.copy(),
            'output': output_normalized.copy(),
            # IR drop tracking
            'M33_ir_drops': diag1['ir_drops'],
            'M3_ir_drops': diag2['ir_drops'],
            'M8_ir_drops': diag3['ir_drops']
        }
        
        return output_normalized, diagnostics
    
    def refresh_cycle(self):
        """Execute one discharge cycle across all matrices."""
        for matrix in self.ref_matrices:
            matrix.refresh_cycle()
    
    def set_correction_weights(self, W_M3: np.ndarray, W_M8: np.ndarray):
        """
        Update correction matrix weights (called by MAML optimizer).
        
        Args:
            W_M3: (32, 32) weights for first correction layer
            W_M8: (32, 32) weights for second correction layer
        """
        self.M3.weights = W_M3.copy()
        self.M8.weights = W_M8.copy()
        
        # Sync to cell banks
        for i in range(self.size):
            for j in range(self.size):
                self.M3.cell_bank.cells_active[i*self.size + j].V_gs = W_M3[i, j]
                self.M8.cell_bank.cells_active[i*self.size + j].V_gs = W_M8[i, j]
