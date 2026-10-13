"""
Calibrated Analog Hardware Surrogate for Inverted MAML Outer Loop (Ref 40).
Models empirical physical non-idealities measured on the physical T120/T20
Inverted MAML PCB (Dual-2T1C multipliers, XC2361A ADCs, 74HC595 DACs):
1. Hidden crosspoint weights (W_hidden) with realistic mismatch matching empirical
   span standard deviation (~59 LSB std dev on Matrix 3 data rows).
2. Power trim hidden offsets and ADC/DAC quantization / pedestal shifts (+48 LSB on M33).
3. Crosspoint Warp: soft-saturation sigmoid compression and two-quadrant slope
   asymmetry (+19.81 LSB pos vs -19.11 LSB neg per DAC step).
4. Temporal Drift: Sawtooth exponential capacitor droop over the 10.0 ms refresh
   window with fast-decay (330 kOhm) and normal 1 MOhm rows.
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional, Union
import numpy as np


@dataclass
class SurrogateConfig:
    """Hardware calibration parameters derived from benchmark_baseline_latest.json."""
    m3_rows: int = 8          # Rows 0..5 data, Row 6 bias, Row 7 fast decay
    m3_cols: int = 6
    m33_rows: int = 6         # Payload matrix 6x6
    m33_cols: int = 6
    
    # Weight span mismatch (LSB)
    m3_data_span_mean: float = 253.94
    m3_data_span_std: float = 59.16
    m3_bias_span_mean: float = -472.67
    m3_bias_span_std: float = 139.52
    m3_decay_span_mean: float = 1007.50
    m3_decay_span_std: float = 234.54
    m33_span_mean: float = 507.03
    m33_span_std: float = 195.32
    
    # Two-quadrant slope parameters (LSB output delta per +/-96 LSB weight swing)
    slope_pos_mean: float = 19.81
    slope_pos_std: float = 10.98
    slope_neg_mean: float = -19.11
    slope_neg_std: float = 10.37
    
    # Pedestal shifts and quantization offsets
    m33_pedestal_bias: float = 48.0   # +48 LSB pedestal bias on M33 / ADC_49
    adc45_pedestal: float = 0.0
    adc_resolution_bits: int = 12
    adc_max_code: int = 2047
    adc_min_code: int = -2048
    
    # Refresh and temporal drift (10.0 ms refresh cycle)
    refresh_period_ms: float = 10.0
    tau_normal_ms: float = 100.0       # 100 nF * 1.0 MOhm = 100 ms
    tau_fast_decay_ms: float = 33.0    # 100 nF * 330 kOhm = 33 ms
    
    # Soft saturation threshold (LSB) and sigmoid compression factor
    saturation_threshold: float = 320.0
    compression_k: float = 0.0035


class AnalogHardwareSurrogate:
    """
    Calibrated Python emulator surrogate for the Inverted MAML outer loop (40).
    Provides realistic analog matrix multiplication with spatial mismatch,
    asymmetric two-quadrant slope distortion, RC droop over 10ms, and power trim offsets.
    """
    def __init__(self, config: Optional[SurrogateConfig] = None, seed: Optional[int] = 42):
        self.cfg = config or SurrogateConfig()
        self.rng = np.random.default_rng(seed)
        
        # Power trim-DAC 38 state
        self.trim_dac_38: float = 0.0          # Digital nominal setting (-128..127)
        self.hidden_trim_offset: float = 0.0    # Secret hardware supply drift
        
        # Hidden crosspoint mismatch maps
        self.w_hidden_m3: np.ndarray = np.zeros((self.cfg.m3_rows, self.cfg.m3_cols))
        self.w_hidden_m33: np.ndarray = np.zeros((self.cfg.m33_rows, self.cfg.m33_cols))
        self.span_scale_m3: np.ndarray = np.zeros((self.cfg.m3_rows, self.cfg.m3_cols))
        self.span_scale_m33: np.ndarray = np.zeros((self.cfg.m33_rows, self.cfg.m33_cols))
        self.two_quadrant_asym_m3: np.ndarray = np.zeros((self.cfg.m3_rows, self.cfg.m3_cols))
        self.two_quadrant_asym_m33: np.ndarray = np.zeros((self.cfg.m33_rows, self.cfg.m33_cols))
        
        # ADC / DAC offsets
        self.dac_offsets_base: np.ndarray = np.zeros(self.cfg.m3_rows)
        self.adc45_offsets_base: np.ndarray = np.zeros(self.cfg.m3_cols)
        self.adc49_offsets_base: np.ndarray = np.zeros(self.cfg.m33_cols)
        self.adc45_offsets_hidden: np.ndarray = np.zeros(self.cfg.m3_cols)
        self.adc49_offsets_hidden: np.ndarray = np.zeros(self.cfg.m33_cols)
        
        # Generate initial hardware individual
        self.sample_hardware_mismatch()

    def sample_hardware_mismatch(self) -> None:
        """Sample permanent physical process variation across cross-points."""
        # Matrix 3 spans: rows 0..5 data (mean 253.94, std 59.16), row 6 bias, row 7 fast decay
        for r in range(self.cfg.m3_rows):
            for c in range(self.cfg.m3_cols):
                if r < 6:
                    span = self.rng.normal(self.cfg.m3_data_span_mean, self.cfg.m3_data_span_std)
                elif r == 6:
                    span = self.rng.normal(self.cfg.m3_bias_span_mean, self.cfg.m3_bias_span_std)
                else:
                    span = self.rng.normal(self.cfg.m3_decay_span_mean, self.cfg.m3_decay_span_std)
                # Gain per (w_cell * x_in / 128.0)
                self.span_scale_m3[r, c] = span / 192.0
                
                # Two-quadrant slope asymmetry (+19.81 vs -19.11)
                pos_s = self.rng.normal(self.cfg.slope_pos_mean, self.cfg.slope_pos_std)
                neg_s = self.rng.normal(self.cfg.slope_neg_mean, self.cfg.slope_neg_std)
                self.two_quadrant_asym_m3[r, c] = (pos_s + neg_s) / 96.0

        # Matrix 33 spans (mean 507.03, std 195.32)
        m33_spans = self.rng.normal(self.cfg.m33_span_mean, self.cfg.m33_span_std, (self.cfg.m33_rows, self.cfg.m33_cols))
        self.span_scale_m33 = m33_spans / 192.0
        self.two_quadrant_asym_m33 = self.rng.normal(0.04, 0.02, (self.cfg.m33_rows, self.cfg.m33_cols))

        # Base physical DC offsets on DAC and ADCs
        self.dac_offsets_base = self.rng.normal(0.0, 1.5, size=self.cfg.m3_rows)
        self.adc45_offsets_base = self.rng.normal(0.0, 4.0, size=self.cfg.m3_cols)
        self.adc49_offsets_base = self.rng.normal(self.cfg.m33_pedestal_bias, 4.0, size=self.cfg.m33_cols)
        
        # Emulated hidden shifts for outer loop (Ref 40)
        self.adc45_offsets_hidden = np.zeros(self.cfg.m3_cols)
        self.adc49_offsets_hidden = np.zeros(self.cfg.m33_cols)

    def trigger_outer_loop_epoch(self, trim_drift_lsb: float = 0.0) -> Dict[str, Union[float, int]]:
        """
        Emulate outer loop (reference numeral 40) sudden environmental / physical shift:
        Randomizes supply trim-DAC shift (+/- 5%) and shifts hidden cross-point offsets.
        """
        if trim_drift_lsb == 0.0:
            self.hidden_trim_offset = float(self.rng.uniform(-12.8, 12.8)) # ~ +/-5% on 256 LSB
        else:
            self.hidden_trim_offset = float(trim_drift_lsb)
            
        # Intentionally shift hidden matrix weights W_hidden (Ref 40)
        self.w_hidden_m3 = self.rng.normal(0.0, self.cfg.m3_data_span_std * 0.15, size=self.w_hidden_m3.shape)
        self.w_hidden_m33 = self.rng.normal(0.0, self.cfg.m33_span_std * 0.15, size=self.w_hidden_m33.shape)
        
        # Column-wise ADC converter deviation (Ref 40 item 4)
        col_gain_factor = 1.0 + (self.hidden_trim_offset / 256.0) * 0.10
        self.adc45_offsets_hidden = self.rng.normal(0.0, 2.5, size=self.adc45_offsets_hidden.shape)
        self.adc49_offsets_hidden = self.rng.normal(0.0, 3.0, size=self.adc49_offsets_hidden.shape)

        return {
            "hidden_trim_offset": self.hidden_trim_offset,
            "col_gain_factor": col_gain_factor,
            "m3_hidden_norm": float(np.linalg.norm(self.w_hidden_m3)),
            "m33_hidden_norm": float(np.linalg.norm(self.w_hidden_m33)),
        }

    def reset_to_operational_mode(self) -> None:
        """Patent claim 5 / Ref 42: Reset all artificial outer loop hidden shifts."""
        self.hidden_trim_offset = 0.0
        self.trim_dac_38 = 0.0
        self.w_hidden_m3.fill(0.0)
        self.w_hidden_m33.fill(0.0)
        self.adc45_offsets_hidden.fill(0.0)
        self.adc49_offsets_hidden.fill(0.0)

    @property
    def adc45_offsets(self) -> np.ndarray:
        return self.adc45_offsets_base + self.adc45_offsets_hidden

    @property
    def adc49_offsets(self) -> np.ndarray:
        return self.adc49_offsets_base + self.adc49_offsets_hidden

    @property
    def dac_offsets(self) -> np.ndarray:
        return self.dac_offsets_base

    def _warp_crosspoint(self, w_eff: float, x_in: float, asym: float) -> float:
        """
        Apply soft-saturation compression and two-quadrant asymmetry.
        Linear baseline response: (w_eff * x_in) / 128.0
        """
        linear_val = (w_eff * x_in) / 128.0
        
        # Two-quadrant asymmetry: response differs between x_in > 0 and x_in < 0
        if x_in >= 0:
            asym_factor = 1.0 + asym * 0.5
        else:
            asym_factor = 1.0 - asym * 0.5
        val = linear_val * asym_factor
        
        # Soft-saturation sigmoid compression (tanh model)
        v_thresh = self.cfg.saturation_threshold
        if abs(val) > v_thresh:
            excess = abs(val) - v_thresh
            compressed = v_thresh + (1.0 / self.cfg.compression_k) * math.tanh(self.cfg.compression_k * excess)
            val = math.copysign(compressed, val)
        return val

    def compute_temporal_droop(self, t_ms: float, row_idx: int) -> float:
        """
        Exponential capacitor droop over 10.0 ms refresh window.
        Sawtooth profile resetting at each 10.0 ms boundary.
        Row 7 uses fast decay (tau = 33 ms, 330 kOhm), other rows use 100 ms (1 MOhm).
        """
        t_phase = t_ms % self.cfg.refresh_period_ms
        tau = self.cfg.tau_fast_decay_ms if row_idx == 7 else self.cfg.tau_normal_ms
        return math.exp(-t_phase / tau)

    def forward_matrix_3(self, x_in: np.ndarray, w_m3: np.ndarray, t_ms: float = 0.0) -> np.ndarray:
        """
        Compute Matrix 3 Layer 1 forward propagation -> ADC_45 output (6 channels).
        x_in: (8,) or (6,) input DAC vector (-128..127) on In-Data rows
        w_m3: (8, 6) matrix weights (-128..127)
        """
        x_arr = np.zeros(self.cfg.m3_rows, dtype=float)
        x_len = min(len(x_in), self.cfg.m3_rows)
        x_arr[:x_len] = np.array(x_in[:x_len], dtype=float)
        x_eff = np.clip(x_arr + self.dac_offsets, -128.0, 127.0)
        
        out = np.zeros(self.cfg.m3_cols, dtype=float)
        supply_scale = 1.0 + ((self.trim_dac_38 + self.hidden_trim_offset) / 256.0) * 0.10
        
        for r in range(self.cfg.m3_rows):
            droop = self.compute_temporal_droop(t_ms, r)
            for c in range(self.cfg.m3_cols):
                w_cell = (w_m3[r, c] + self.w_hidden_m3[r, c]) * droop
                scaled_w = w_cell * self.span_scale_m3[r, c] * supply_scale
                warped = self._warp_crosspoint(scaled_w, x_eff[r], self.two_quadrant_asym_m3[r, c])
                out[c] += warped
                
        out += self.adc45_offsets
        return np.clip(np.round(out), self.cfg.adc_min_code, self.cfg.adc_max_code).astype(int)

    def forward_matrix_33(self, x_in: np.ndarray, w_m33: np.ndarray, t_ms: float = 0.0) -> np.ndarray:
        """
        Compute Matrix 33 Main Payload forward propagation -> ADC_49 output (6 channels).
        Includes the empirical +48 LSB pedestal bias on ADC_49.
        x_in: (6,) input DAC vector (-128..127)
        w_m33: (6, 6) matrix weights (-128..127)
        """
        x_eff = np.clip(np.array(x_in[:self.cfg.m33_rows], dtype=float), -128.0, 127.0)
        out = np.zeros(self.cfg.m33_cols, dtype=float)
        supply_scale = 1.0 + ((self.trim_dac_38 + self.hidden_trim_offset) / 256.0) * 0.10
        
        for r in range(self.cfg.m33_rows):
            droop = self.compute_temporal_droop(t_ms, r)
            for c in range(self.cfg.m33_cols):
                w_cell = (w_m33[r, c] + self.w_hidden_m33[r, c]) * droop
                scaled_w = w_cell * self.span_scale_m33[r, c] * supply_scale
                warped = self._warp_crosspoint(scaled_w, x_eff[r], self.two_quadrant_asym_m33[r, c])
                out[c] += warped
                
        out += self.adc49_offsets  # Includes +48 pedestal bias
        return np.clip(np.round(out), self.cfg.adc_min_code, self.cfg.adc_max_code).astype(int)
