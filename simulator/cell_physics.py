"""
Cell Physics Layer: 2T1C Analog Multiplier Model
Implements triode-region transistor computation + RC discharge dynamics
Reference: Design_Specification_Analog_Matrix_2T1C.pdf
"""

import numpy as np
from typing import Dict, Tuple, Optional


class AnalogCell:
    """
    Single 2T1C (Two Transistor, One Capacitor) analog multiplier cell.
    
    Physics:
        - Multiplication: I_out = g_m(V_gs, V_ds) · V_ds
        - Triode condition: V_ds ≤ V_gs - V_th (ensures linear region)
        - Weight storage: Voltage on gate-source capacitor (100 nF)
        - Leakage: Controlled discharge through parallel resistor (1 MΩ or 330 kΩ)
    
    Parameters:
        cell_id: Unique identifier for this cell
        V_th: Threshold voltage (V), typically 0.6V for DOX3134A
        g_m_scale: Transconductance scaling factor
        C_w: Weight capacitor (Farads), default 100 nF
        R_discharge: Discharge resistor (Ohms), default 1 MΩ (slow) or 330 kΩ (fast ref)
    """
    
    def __init__(self, cell_id: int, V_th: float = 0.6, g_m_scale: float = 1.0e-2,
                 C_w: float = 100e-9, R_discharge: float = 1.0e6, is_reference: bool = False):
        """Initialize an analog cell."""
        self.cell_id = cell_id
        self.V_th = V_th
        self.g_m_scale = g_m_scale
        self.C_w = C_w
        self.R_discharge = R_discharge
        self.is_reference = is_reference
        
        # Discharge time constant: τ = R · C
        self.tau_discharge = R_discharge * C_w
        
        # Gate voltage (weight storage)
        self.V_gs = 2.6  # Initial: midpoint (~Data 128)
        
        # Manufacturing variations
        self.V_th_mfg = V_th
        self.g_m_mfg = g_m_scale
        self.R_discharge_mfg = R_discharge
        
        # Thermal state
        self.temperature_delta_C = 0.0
        
        # Noise injection
        self.noise_sigma = 0.0
        
        # History tracking
        self.history = {
            'V_gs': [self.V_gs],
            't_ms': [0.0]
        }
    
    def set_weight(self, weight_8bit: int):
        """
        Set gate voltage corresponding to 8-bit weight value.
        
        Mapping:
            Data 0 → V_gs = 2.1 V (minimum)
            Data 255 → V_gs = 3.1 V (maximum)
        """
        # Normalize to [0, 1]
        normalized = weight_8bit / 255.0
        # Linear interpolation: 2.1V + 1.0V * normalized
        self.V_gs = 2.1 + 1.0 * normalized
    
    def discharge_step(self, dt_ms: float):
        """
        Execute RC discharge step: V(t) = V₀ · e^(-dt/τ)
        
        Args:
            dt_ms: Time step (milliseconds)
        """
        # Effective time constant with temperature effects
        tau_eff = self.tau_discharge * self._temperature_compensation()
        
        # Decay factor
        decay_factor = np.exp(-dt_ms / (tau_eff * 1000))  # Convert ms to seconds
        
        # Update voltage
        self.V_gs *= decay_factor
    
    def compute_output(self, V_ds: float) -> float:
        """
        Compute output current in triode region: I_out = g_m · (V_gs - V_th - V_ds/2) · V_ds
        
        Args:
            V_ds: Drain-source voltage (data row voltage)
        
        Returns:
            Output current (unitless, scaled by g_m_scale)
        
        Note:
            If triode condition violated (V_ds > V_gs - V_th), returns minimal current.
        """
        # Effective parameters with manufacturing variation
        V_th_eff = self.V_th_mfg
        g_m_eff = self.g_m_mfg
        
        # Gate-source voltage drop across capacitor
        V_gs_eff = self.V_gs - V_th_eff
        
        # Check triode condition
        if V_ds > V_gs_eff:
            # Saturation region: return near-zero current
            I_out = g_m_eff * 1e-8
        else:
            # Triode region (linear): I_out ∝ (V_gs - V_th - V_ds/2) · V_ds
            I_out = g_m_eff * (V_gs_eff - V_ds / 2.0) * V_ds
        
        # Add thermal noise
        if self.noise_sigma > 0:
            noise = np.random.normal(0, self.noise_sigma * abs(I_out))
            I_out += noise
        
        return I_out
    
    def inject_manufacturing_variation(self, V_th_sigma: float, g_m_sigma: float, R_sigma: float):
        """
        Inject realistic manufacturing tolerances (Gaussian).
        
        Args:
            V_th_sigma: Threshold voltage tolerance (V)
            g_m_sigma: Transconductance tolerance (fraction)
            R_sigma: Resistance tolerance (fraction)
        """
        self.V_th_mfg = self.V_th + np.random.normal(0, V_th_sigma)
        self.g_m_mfg = self.g_m_scale * np.random.normal(1.0, g_m_sigma)
        self.R_discharge_mfg = self.R_discharge * np.random.normal(1.0, R_sigma)
        
        # Recalculate tau
        self.tau_discharge = self.R_discharge_mfg * self.C_w
    
    def inject_thermal_drift(self, temp_delta_C: float):
        """
        Inject temperature-dependent leakage effects.
        
        Physics:
            - Leakage increases ~0.5% per °C
            - Resistance decreases slightly with temperature
        
        Args:
            temp_delta_C: Temperature rise above nominal (°C)
        """
        self.temperature_delta_C = temp_delta_C
    
    def _temperature_compensation(self) -> float:
        """
        Compute temperature-dependent compensation factor.
        
        Returns:
            Multiplication factor for τ (> 1 = slower discharge, < 1 = faster)
        """
        # Leakage increases with temp → effective R decreases → tau decreases
        # Model: tau_eff = tau * (1 - 0.003 * ΔT)
        return 1.0 - (0.003 * self.temperature_delta_C)
    
    def inject_noise(self, noise_sigma: float):
        """
        Enable thermal/environmental noise injection.
        
        Args:
            noise_sigma: Noise standard deviation as fraction of signal
        """
        self.noise_sigma = noise_sigma
    
    def get_state(self) -> Dict[str, float]:
        """Return current cell state for diagnostics."""
        return {
            'V_gs': self.V_gs,
            'V_th': self.V_th_mfg,
            'tau_discharge': self.tau_discharge,
            'temperature_C': self.temperature_delta_C,
            'triode_margin': self.V_gs - self.V_th_mfg
        }
    
    def record_history(self, t_ms: float):
        """Record state for later analysis."""
        self.history['V_gs'].append(self.V_gs)
        self.history['t_ms'].append(t_ms)


class ReferenceCell(AnalogCell):
    """
    Fast-decay reference cell for proprioceptive clock.
    
    Physics:
        - Accelerated discharge (330 kΩ vs 1 MΩ)
        - Acts as "internal analog clock" showing phase of discharge cycle
        - Sweeps Data 230 → Data 30 over 10ms cycle
        - Provides symmetry-breaking signal for gradient extraction
    """
    
    def __init__(self, cell_id: int):
        """Initialize reference cell with fast discharge."""
        # Fast resistor: 330 kΩ → τ = 33 ms
        super().__init__(
            cell_id=cell_id,
            V_th=0.6,
            g_m_scale=1.0e-2,
            C_w=100e-9,
            R_discharge=330e3,  # 330 kΩ for fast decay
            is_reference=True
        )
        
        # Fixed input: always maximum (Data 255)
        self.fixed_input_V_ds = 1.90
    
    def initialize_for_cycle(self):
        """Set up for a new refresh cycle: V_gs ≈ 3.0V (Data ~230)."""
        self.V_gs = 3.0
    
    def get_data_equivalent(self) -> float:
        """
        Convert gate voltage to 8-bit data equivalent.
        
        Mapping:
            V_gs = 2.1V → Data 0
            V_gs = 3.1V → Data 255
        
        Returns:
            Equivalent 8-bit value [0, 255]
        """
        # V_gs is outside [2.1, 3.1] after decay, so clamp
        V_gs_clamped = np.clip(self.V_gs, 2.1, 3.1)
        data_equiv = ((V_gs_clamped - 2.1) / 1.0) * 255.0
        return data_equiv


class BiasCell(AnalogCell):
    """
    Hardware bias cell: Constant input × learnable weight.
    
    Physics:
        - Fixed input: V_ds = 1.90V (Data 255, always "on")
        - Programmable weight: Gate voltage updated by MAML
        - Contributes bias term to output: b_i = I_out
    """
    
    def __init__(self, cell_id: int):
        """Initialize bias cell with constant high input."""
        super().__init__(
            cell_id=cell_id,
            V_th=0.6,
            g_m_scale=1.0e-2,
            C_w=100e-9,
            R_discharge=1.0e6  # Standard slow discharge
        )
        
        # Fixed input: maximum (Data 255)
        self.fixed_input_V_ds = 1.90


class CellBank:
    """
    Collection of analog cells representing one layer of the matrix.
    
    Organization:
        - Active cells: Form rows/columns of main computation
        - Reference cells: Provide calibration clock
        - Bias cells: Provide per-neuron biases
    """
    
    def __init__(self, num_active: int = 36, num_reference: int = 6, num_bias: int = 6):
        """
        Initialize cell bank.
        
        Args:
            num_active: Number of active multiplier cells (6×6 = 36)
            num_reference: Number of reference cells for clock
            num_bias: Number of hardware bias cells
        """
        self.cells_active = [AnalogCell(i) for i in range(num_active)]
        self.cells_reference = [ReferenceCell(i + num_active) for i in range(num_reference)]
        self.cells_bias = [BiasCell(i + num_active + num_reference) for i in range(num_bias)]
        
        self.all_cells = self.cells_active + self.cells_reference + self.cells_bias
    
    def discharge_step(self, dt_ms: float):
        """Execute discharge for all cells."""
        for cell in self.all_cells:
            cell.discharge_step(dt_ms)
    
    def inject_manufacturing_variations(self, config: Dict):
        """Inject Gaussian manufacturing tolerances."""
        V_th_sigma = config.get('V_th_sigma', 0.02)
        g_m_sigma = config.get('g_m_sigma', 0.02)
        R_sigma = config.get('R_sigma', 0.02)
        
        for cell in self.cells_active + self.cells_bias:
            cell.inject_manufacturing_variation(V_th_sigma, g_m_sigma, R_sigma)
    
    def inject_thermal_drift(self, temp_delta_C: float):
        """Inject temperature-dependent drift."""
        for cell in self.all_cells:
            cell.inject_thermal_drift(temp_delta_C)
    
    def inject_noise(self, noise_sigma: float):
        """Enable thermal noise on all cells."""
        for cell in self.all_cells:
            cell.inject_noise(noise_sigma)
