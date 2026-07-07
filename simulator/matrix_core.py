"""
Matrix Core Layer: Atomic Triad (3 × 6×6 matrices) + Computation Model
Implements the core Inverted MAML architecture:
    - M33: Primary payload matrix (fixed)
    - M3: First correction layer (adaptive via MAML)
    - M8: Second correction layer (adaptive via MAML)

Reference: inverterad_MAML_12_Eng.pdf, Atomic_Triad.pdf
"""

import numpy as np
from typing import Dict, Tuple, List, Optional
from cell_physics import AnalogCell, CellBank


class AnalogMatrix:
    """
    Single 6×6 analog matrix with physical cell-level modeling.
    
    Structure:
        - Weight storage: 36 cells (6×6) storing gate voltages
        - Reference cells: 6 fast-decay cells for calibration clock
        - Bias cells: 6 cells for hardware bias term
    
    Computation: I_out[i] = Σⱼ g_m(V_gs[i,j], V_ds[j]) · (V_ds[j] - V_s)
                where V_s = 1.65V (virtual ground)
    """
    
    def __init__(self, matrix_id: int, size: int = 6, is_correction: bool = False):
        """
        Initialize a 6×6 analog matrix.
        
        Args:
            matrix_id: Identifier (3=payload, 8=2nd correction, 33=primary)
            size: Matrix dimension (default 6×6)
            is_correction: If True, weights are trainable (MAML)
        """
        self.matrix_id = matrix_id
        self.size = size
        self.is_correction = is_correction
        
        # Weight storage: matrix of gate voltages
        if matrix_id == 33:
            # Primary matrix: Initialize with varied weights to enable matrix multiplication
            # V_gs ∈ [2.1V, 3.1V] corresponding to Data [0, 255]
            np.random.seed(matrix_id)
            weights_8bit = np.random.randint(0, 256, (size, size))
            self.weights = 2.1 + (weights_8bit / 255.0) * 1.0
        else:
            # Correction matrices (M3, M8): Initialize near midpoint with small random offset
            # This allows M3/M8 to contribute meaningful gradients without overshooting
            # Start at 2.6V ± 0.05V (small perturbations around center)
            np.random.seed(matrix_id)
            perturbations = np.random.uniform(-0.05, 0.05, (size, size))
            self.weights = 2.6 + perturbations
        
        # Cell bank: physical cells backing this matrix
        self.cell_bank = CellBank(num_active=size*size, 
                                   num_reference=size, 
                                   num_bias=size)
        
        # Sync cell bank weights with matrix
        for i in range(size):
            for j in range(size):
                self.cell_bank.cells_active[i*size + j].V_gs = self.weights[i, j]
        
        # System parameters
        self.V_source = 1.65  # Virtual ground
        self.tau_discharge = 100.0  # ms (slow discharge for non-reference)
        
        # State tracking
        self.last_output = np.zeros(size)
        self.state_history = []
    
    def set_weights_8bit(self, weights_8bit: np.ndarray):
        """
        Set matrix weights from 8-bit values.
        
        Args:
            weights_8bit: (6, 6) array with values in [0, 255]
        """
        # Convert 8-bit to gate voltages: 2.1V + (w/255) * 1.0V
        self.weights = 2.1 + (weights_8bit / 255.0) * 1.0
        
        # Sync to cell bank
        for i in range(self.size):
            for j in range(self.size):
                self.cell_bank.cells_active[i*self.size + j].V_gs = self.weights[i, j]
    
    def forward(self, x_input: np.ndarray) -> Tuple[np.ndarray, Dict]:
        """
        Compute matrix-vector product with physical cell modeling.
        
        Args:
            x_input: (6,) input vector, normalized to [0, 1] → [1.65V, 1.90V]
        
        Returns:
            output: (6,) output current vector
            diagnostics: Dict with intermediate values for gradient computation
        """
        # Convert input to row voltages: 1.65V + (x/2) * 0.25V
        # Range: x ∈ [0, 1] → V_ds ∈ [1.65V, 1.90V]
        V_ds = self.V_source + x_input * 0.25
        
        # Matrix-vector multiply: output[i] = sum_j( weight[i,j] * input[j] )
        # Modeled as: I[i] = sum_j( g_m[i,j](V_gs[i,j], V_ds[j]) )
        output = np.zeros(self.size)
        
        for i in range(self.size):
            for j in range(self.size):
                # Cell index: linear index in cell_active array
                cell_idx = i * self.size + j
                cell = self.cell_bank.cells_active[cell_idx]
                
                # Compute current from this cell
                # Input[j] is routed to column j (controls V_ds)
                # Weight[i,j] is stored on gate (V_gs)
                I_cell = cell.compute_output(V_ds[j])
                output[i] += I_cell
        
        # Add hardware bias: each output gets a configurable constant current
        for i in range(self.size):
            bias_cell = self.cell_bank.cells_bias[i]
            I_bias = bias_cell.compute_output(bias_cell.fixed_input_V_ds)
            output[i] += I_bias
        
        self.last_output = output
        
        return output, {
            'V_ds': V_ds,
            'weights': self.weights.copy(),
            'matrix_id': self.matrix_id,
            'output': output.copy()
        }
    
    def discharge_step(self, dt_ms: float):
        """
        Simulate RC discharge: V(t) = V₀ · e^(-t/τ)
        
        Args:
            dt_ms: Time step (milliseconds)
        """
        self.cell_bank.discharge_step(dt_ms)
        
        # Update internal weight matrix to reflect discharge
        for i in range(self.size):
            for j in range(self.size):
                self.weights[i, j] = self.cell_bank.cells_active[i*self.size + j].V_gs
    
    def get_reference_clock(self, t_ms: float) -> float:
        """
        Read reference cell voltage as normalized clock signal.
        
        Returns:
            Normalized position in discharge cycle [0, 1]
            0 = start (V_gs = 3.0V), 1 = end (V_gs ≈ 2.1V)
        """
        ref_cell = self.cell_bank.cells_reference[0]
        data_equiv = ref_cell.get_data_equivalent()
        # Normalize: Data 230 (start) → 0, Data 30 (end) → 1
        return (230 - data_equiv) / 200.0
    
    def inject_manufacturing_variations(self, config: Dict):
        """Inject Gaussian manufacturing tolerances."""
        self.cell_bank.inject_manufacturing_variations(config)
    
    def inject_thermal_drift(self, temp_delta_C: float):
        """Inject temperature-dependent drift."""
        self.cell_bank.inject_thermal_drift(temp_delta_C)
    
    def inject_noise(self, noise_sigma: float):
        """Enable thermal noise."""
        self.cell_bank.inject_noise(noise_sigma)


class AtomicTriad:
    """
    Complete Inverted MAML atomic triad: 3 coupled analog matrices.
    
    Architecture:
        input x → M33 (payload) ─┐
                                  ├─ [summing point] → output
        input x → M3 → tanh ─ M8 ┘
        
    Where:
        - M33: Primary matrix (non-adaptive, fixed)
        - M3: First correction layer (6→6, adaptive)
        - M8: Second correction layer (6→6, adaptive)
    """
    
    def __init__(self, size: int = 6):
        """
        Initialize atomic triad.
        
        Args:
            size: Matrix dimension (default 6×6)
        """
        self.size = size
        
        # Three matrices
        self.M33 = AnalogMatrix(matrix_id=33, size=size, is_correction=False)
        self.M3 = AnalogMatrix(matrix_id=3, size=size, is_correction=True)
        self.M8 = AnalogMatrix(matrix_id=8, size=size, is_correction=True)
        
        # All matrices share synchronized discharge
        self.cycle_time_ms = 10.0
        self.current_time_ms = 0.0
        
        # Reference to synchronize across matrices
        self.ref_matrices = [self.M33, self.M3, self.M8]
    
    def forward(self, x_input: np.ndarray, t_snapshot_ms: Optional[float] = None) -> Tuple[np.ndarray, Dict]:
        """
        Forward pass through atomic triad with physical cell simulation.
        
        Computation:
            1. Primary: y1 = M33 @ x
            2. Correction hidden: y2 = tanh(M3 @ x)
            3. Correction output: y3 = M8 @ y2
            4. Final: output = y1 + y3
        
        Args:
            x_input: (6,) input vector
            t_snapshot_ms: Measurement time within cycle [0, 10ms]
        
        Returns:
            output: (6,) corrected output
            diagnostics: Dict with all intermediate values
        """
        # Primary pathway
        y_payload, diag_33 = self.M33.forward(x_input)
        
        # Correction pathway: M3 → tanh → M8
        # CRITICAL: Scale M3 output to put tanh input in steep gradient region
        # Optimal sigmoid slope is at input ∈ [-1, +1.5], NOT [-0.13, +0.13] or ±2
        # Maximum tanh' occurs near ±0.8 where derivative ≈ 0.4-0.6
        y_m3_raw, diag_3 = self.M3.forward(x_input)
        y_m3_scaled = y_m3_raw * 7.0  # Scale to ±0.9-1.0 range for optimal gradient
        y_m3_hidden = np.tanh(y_m3_scaled)  # Gradients ~0.4-0.6 (optimal)
        y_correction, diag_8 = self.M8.forward(y_m3_hidden)
        
        # Summing point: primary + correction
        output = y_payload + y_correction
        
        # OUTPUT NORMALIZATION: Scale to hardware voltage range [-0.25V, +0.25V]
        # This represents the 250mV data swing (1.65V -> 1.90V)
        # Normalization: center at 0, scale to ±0.25V range
        output_normalized = ((output - np.mean(output)) / (np.max(np.abs(output)) + 1e-6)) * 0.25
        output_normalized = np.clip(output_normalized, -0.25, 0.25)
        
        # Reference clock at this measurement time
        ref_clock = self.M33.get_reference_clock(t_snapshot_ms) if t_snapshot_ms else 0.5
        
        diagnostics = {
            'input': x_input.copy(),
            'y_payload': y_payload.copy(),
            'y_m3_raw': y_m3_raw.copy(),
            'y_m3_scaled': y_m3_scaled.copy(),
            'y_m3_hidden': y_m3_hidden.copy(),
            'y_correction': y_correction.copy(),
            'output_raw': output.copy(),
            'output': output_normalized.copy(),
            'ref_clock': ref_clock,
            't_snapshot_ms': t_snapshot_ms,
            'M33_weights': self.M33.weights.copy(),
            'M3_weights': self.M3.weights.copy(),
            'M8_weights': self.M8.weights.copy()
        }
        
        return output_normalized, diagnostics
    
    def discharge_step(self, dt_ms: float):
        """
        Synchronous discharge across all three matrices.
        
        Args:
            dt_ms: Time step (milliseconds)
        """
        for matrix in self.ref_matrices:
            matrix.discharge_step(dt_ms)
        
        self.current_time_ms += dt_ms
    
    def refresh_cycle(self):
        """Reset timers for new 10ms refresh cycle."""
        self.current_time_ms = 0.0
        
        # Initialize reference cells for new cycle
        for matrix in self.ref_matrices:
            if len(matrix.cell_bank.cells_reference) > 0:
                matrix.cell_bank.cells_reference[0].initialize_for_cycle()
    
    def set_correction_weights(self, W_M3: np.ndarray, W_M8: np.ndarray):
        """
        Update correction matrix weights (called by MAML optimizer).
        
        Args:
            W_M3: (6, 6) weights for first correction layer
            W_M8: (6, 6) weights for second correction layer
        """
        self.M3.weights = W_M3.copy()
        self.M8.weights = W_M8.copy()
        
        # Sync to cell banks
        for i in range(self.size):
            for j in range(self.size):
                self.M3.cell_bank.cells_active[i*self.size + j].V_gs = W_M3[i, j]
                self.M8.cell_bank.cells_active[i*self.size + j].V_gs = W_M8[i, j]
    
    def inject_manufacturing_variations(self, config: Dict):
        """Inject tolerances into all matrices."""
        for matrix in self.ref_matrices:
            matrix.inject_manufacturing_variations(config)
    
    def inject_thermal_drift(self, temp_delta_C: float):
        """Inject temperature drift into all matrices."""
        for matrix in self.ref_matrices:
            matrix.inject_thermal_drift(temp_delta_C)
    
    def inject_noise(self, noise_sigma: float):
        """Enable thermal noise on all matrices."""
        for matrix in self.ref_matrices:
            matrix.inject_noise(noise_sigma)
    
    def get_all_cells(self) -> List[AnalogCell]:
        """Return all physical cells in the triad."""
        all_cells = []
        for matrix in self.ref_matrices:
            all_cells.extend(matrix.cell_bank.all_cells)
        return all_cells
