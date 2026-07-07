# Inverted MAML 3x6x6 Analog Compute Simulator

**Project**: Digital Twin for Inverted MAML Patent Validation  
**Status**: Planning Phase  
**Target Date**: 2026-07-14  
**Author**: Olle Welin  
**Reference**: SE 2630397-4 (Patent Pending)

---

## 1. Executive Summary

This simulator validates the **Inverted MAML architecture** before physical hardware implementation. It models a single **atomic triad** (3 analog matrices + digital control) in a 6×6 configuration, allowing rapid iteration on:

- **IF #1**: Can MAML track thermal drift faster than it occurs?
- **IF #2**: Can we extract clean gradients from noisy physical measurements?
- **IF #3**: How much thermal noise can the system tolerate?
- **IF #4**: What's the minimum convergence time for 6-bit precision?

The simulator will mature into a **digital twin** that can guide physical layout and control algorithm tuning.

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│           Inverted MAML Simulator (Python)                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 1. Cell Physics Layer                                │  │
│  │    - 2T1C multiplier (triode equations)              │  │
│  │    - RC decay curves (τ_slow=100ms, τ_fast=33ms)    │  │
│  │    - Thermal drift injection                        │  │
│  │    - Component variations (Gaussian)                │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↓                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 2. Matrix Operations                                 │  │
│  │    - 3 × (6×6) matrix compute                        │  │
│  │    - Payload matrix (M33)                           │  │
│  │    - Correction matrices (M3, M8)                   │  │
│  │    - Summing point (OUT = M33·x + corrections)      │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↓                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 3. Measurement & Sensing                             │  │
│  │    - 10 stratified snapshot windows                  │  │
│  │    - Hadamard-encoded row excitation                │  │
│  │    - Reference cell tracking (fast decay clock)     │  │
│  │    - ADC quantization simulation                    │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↓                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 4. MAML Learning Loop                                │  │
│  │    - Stratified mini-batch gradient computation     │  │
│  │    - Meta-gradient across 10 strata                 │  │
│  │    - Weight updates (M3, M8)                        │  │
│  │    - Convergence tracking                           │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↓                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 5. Validation & Analysis                             │  │
│  │    - Precision vs. ideal digital model              │  │
│  │    - Convergence speed analysis                     │  │
│  │    - Noise robustness curves                        │  │
│  │    - Thermal compensation effectiveness            │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Core Components & Implementation

### 3.1 Cell Physics Layer (`cell_physics.py`)

#### 3.1.1 2T1C Analog Multiplier

**Physics Model:**
```
Output current: I_out = g_m · V_gs · V_ds
Where:
  - g_m = transconductance (V_gs dependent in triode)
  - V_gs = gate-source voltage (weight stored on capacitor)
  - V_ds = drain-source voltage (input signal on row)

Triode condition: V_ds ≤ V_gs - V_th
  - V_th ≈ 0.6V (DOX3134A)
  - V_gs swings 2.1V (Data 0) → 3.1V (Data 255)
  - V_ds swings 1.65V (Data 0) → 1.90V (Data 255)
```

**Class: `AnalogCell`**
```python
class AnalogCell:
    def __init__(self, V_th=0.6, g_m_scale=1e-4):
        self.V_gs = 2.6  # Initial gate voltage (Data ~128)
        self.C_w = 100e-9  # Weight capacitor (100 nF)
        self.R_discharge = 1e6  # Discharge resistor (1 MΩ)
        self.V_th = V_th
        self.g_m_scale = g_m_scale
        
    def discharge_step(self, dt):
        """RC decay step: V(t) = V₀ · e^(-t/τ)"""
        tau = self.R_discharge * self.C_w
        decay_factor = np.exp(-dt / tau)
        self.V_gs *= decay_factor
        
    def compute_output(self, V_ds):
        """Compute I_out in triode region"""
        V_gs_eff = self.V_gs - self.V_th
        if V_gs_eff <= V_ds:
            # Triode: I ∝ (V_gs - V_th - V_ds/2) · V_ds
            I_out = self.g_m_scale * (V_gs_eff - V_ds/2) * V_ds
        else:
            # Saturation (avoid): return reduced current
            I_out = self.g_m_scale * 1e-6
        return I_out
        
    def add_thermal_drift(self, drift_rate):
        """Inject temperature-dependent leakage"""
        self.V_gs *= (1 - drift_rate)
```

#### 3.1.2 RC Discharge Curves

**Slow Discharge (Payload + Correction Matrices):**
- $\tau_{slow} = 1 \text{ M}\Omega \times 100 \text{ nF} = 100 \text{ ms}$
- Voltage drop over 10ms: $V(10ms) = V_0 \cdot e^{-10/100} \approx 0.905 V_0$ (9.5% droop)

**Fast Discharge (Reference Cells):**
- $\tau_{fast} = 330 \text{ k}\Omega \times 100 \text{ nF} = 33 \text{ ms}$
- Voltage sweep: $V(10ms) = 3.0V \cdot e^{-10/33} \approx 2.216V$ (Data 230 → 30)
- Acts as **internal analog clock** for system synchronization

#### 3.1.3 Thermal Drift & Component Variation

```python
def inject_variations(cells, temp_change_C, mfg_sigma=0.02):
    """
    Inject realistic physical non-idealities
    
    Args:
        cells: List of AnalogCell objects
        temp_change_C: Temperature rise (°C) → affects leakage
        mfg_sigma: Manufacturing tolerance std-dev (±2%)
    """
    for cell in cells:
        # Thermal drift: leakage increases ~0.5%/°C
        thermal_factor = 1.0 + (0.005 * temp_change_C)
        cell.R_discharge *= (1 - 0.003 * temp_change_C)  # R decreases
        
        # Manufacturing variation (Gaussian)
        cell.V_th += np.random.normal(0, mfg_sigma * cell.V_th)
        cell.g_m_scale *= np.random.normal(1, mfg_sigma)
```

---

### 3.2 Matrix Operations (`matrix_core.py`)

#### 3.2.1 Atomic Triad Structure

```python
class AtomicTriad:
    """
    Inverted MAML atomic triad: 3 coupled 6×6 matrices
    
    Computation:
        output = M33(x) + correction(M3, M8, x)
    """
    
    def __init__(self, matrix_size=6):
        self.M33 = self.create_matrix(matrix_size, "payload")
        self.M3 = self.create_matrix(matrix_size, "correction_1")
        self.M8 = self.create_matrix(matrix_size, "correction_2")
        
        # Reference cells (fast decay, Data 230→30 per cycle)
        self.ref_cells = [AnalogCell() for _ in range(matrix_size)]
        
        # Bias cells (constant input × learnable weight)
        self.bias_cells = [AnalogCell() for _ in range(matrix_size)]
        
    def forward(self, x_input, t_snapshot=None):
        """
        Compute: output = M33·x + M8·(nonlin(M3·x))
        
        Args:
            x_input: Input vector [6]
            t_snapshot: Measurement time within cycle [0, 10ms]
        
        Returns:
            output: Corrected output vector [6]
            diagnostics: Intermediate values for gradient computation
        """
        # Primary computation
        payload = np.dot(self.M33.weights, x_input) + self.bias_cells[0].compute_output(1.9)
        
        # First correction layer (M3)
        m3_hidden = self.activation(np.dot(self.M3.weights, x_input))
        
        # Second correction layer (M8)
        correction = np.dot(self.M8.weights, m3_hidden)
        
        # Summing point
        output = payload + correction
        
        return output, {
            "payload": payload,
            "m3_hidden": m3_hidden,
            "correction": correction,
            "ref_clock": self.get_reference_clock(t_snapshot)
        }
    
    def activation(self, x):
        """Tanh activation (captures nonlinearity)"""
        return np.tanh(x)
    
    def get_reference_clock(self, t_ms):
        """
        Simulate accelerated reference cell discharge
        Returns normalized position in refresh cycle [0, 1]
        """
        if t_ms is None:
            return 0.5
        # Map fast decay (33ms tau) to cycle time [0, 10ms]
        decay_factor = np.exp(-t_ms / 33.0)
        return decay_factor
```

#### 3.2.2 10-Strata Measurement Windows

```python
def compute_strata_measurements(triad, x_input, num_strata=10):
    """
    Stratified batching: sample output at 10 time windows
    across the 10ms refresh cycle
    
    Returns stratified gradients for MAML meta-learning
    """
    cycle_time = 10.0  # ms
    stratum_duration = cycle_time / num_strata
    
    measurements = []
    
    for stratum in range(num_strata):
        # Categ orize stratum
        if stratum < 3:
            category = "Peak"  # Early cycle, high gradient
        elif stratum < 7:
            category = "Linear"  # Quasi-linear decay
        else:
            category = "Tail"  # Compressed, low energy
        
        # Measurement time within this stratum
        t_ms = stratum * stratum_duration + 0.5 * stratum_duration
        
        # Inject thermal drift relative to time
        triad.inject_drift(t_ms / cycle_time)
        
        # Compute output
        output, diagnostics = triad.forward(x_input, t_snapshot=t_ms)
        
        measurements.append({
            "stratum": stratum,
            "category": category,
            "t_ms": t_ms,
            "output": output,
            "gradient": compute_local_gradient(output, diagnostics)
        })
    
    return measurements
```

---

### 3.3 MAML Learning Loop (`maml_optimizer.py`)

#### 3.3.1 Stratified Mini-Batch Gradient

```python
class InvertedMAML:
    """
    Inverted MAML: Adapt correction matrices to compensate for
    hardware drift using stratified time-slice batching
    """
    
    def __init__(self, triad, learning_rate=0.01):
        self.triad = triad
        self.lr = learning_rate
        self.loss_history = []
        
    def compute_stratified_gradient(self, x_input, y_target, num_strata=10):
        """
        Core algorithm: measure across 10 strata, average gradients
        
        ∇W = (1/10) · Σᵢ ∇L(tᵢ)
        
        This discrete integration resolves the unknown offset and
        yields optimal starting weights for next refresh pulse.
        """
        strata_measurements = compute_strata_measurements(
            self.triad, x_input, num_strata
        )
        
        stratified_gradients = []
        
        for measurement in strata_measurements:
            output = measurement["output"]
            
            # Compute loss at this stratum
            loss = 0.5 * np.sum((output - y_target) ** 2)
            
            # Gradient w.r.t. correction matrices
            grad_M3, grad_M8 = self.backprop_corrections(
                measurement, y_target, loss
            )
            
            stratified_gradients.append({
                "loss": loss,
                "grad_M3": grad_M3,
                "grad_M8": grad_M8,
                "stratum": measurement["stratum"],
                "category": measurement["category"]
            })
        
        # Average across all strata (discrete integration)
        avg_grad_M3 = np.mean([g["grad_M3"] for g in stratified_gradients], axis=0)
        avg_grad_M8 = np.mean([g["grad_M8"] for g in stratified_gradients], axis=0)
        avg_loss = np.mean([g["loss"] for g in stratified_gradients])
        
        self.loss_history.append(avg_loss)
        
        return avg_grad_M3, avg_grad_M8, avg_loss
    
    def update_weights(self, x_input, y_target):
        """
        Single MAML update cycle: measure, compute gradients, adapt
        """
        grad_M3, grad_M8, loss = self.compute_stratified_gradient(
            x_input, y_target
        )
        
        # Update correction matrices
        self.triad.M3.weights -= self.lr * grad_M3
        self.triad.M8.weights -= self.lr * grad_M8
        
        return loss
    
    def backprop_corrections(self, measurement, y_target, loss):
        """
        Backpropagate loss through correction pathway only
        (M33 is fixed; only M3, M8 are adapted)
        """
        # Simplified: actual impl uses full backprop
        grad_M3 = np.random.randn(6, 6) * 0.1
        grad_M8 = np.random.randn(6, 6) * 0.1
        return grad_M3, grad_M8
```

#### 3.3.2 Convergence Validation

```python
def measure_convergence(triad, test_vectors, target_vectors, 
                       max_cycles=100, precision_bits=6):
    """
    Run MAML learning across cycles, measure convergence
    
    Returns:
        - Convergence curve (loss vs. cycle)
        - Achieved precision (bits)
        - Adaptation speed (cycles to <1 LSB error)
    """
    maml = InvertedMAML(triad, learning_rate=0.01)
    
    convergence_data = {
        "loss_history": [],
        "precision_history": [],
        "cycle_count": 0
    }
    
    for cycle in range(max_cycles):
        cycle_loss = 0.0
        
        for x_test, y_target in zip(test_vectors, target_vectors):
            loss = maml.update_weights(x_test, y_target)
            cycle_loss += loss
        
        avg_cycle_loss = cycle_loss / len(test_vectors)
        
        # Measure precision in bits
        precision = estimate_precision_bits(maml, test_vectors, 
                                            target_vectors, precision_bits)
        
        convergence_data["loss_history"].append(avg_cycle_loss)
        convergence_data["precision_history"].append(precision)
        convergence_data["cycle_count"] = cycle + 1
        
        # Early exit if converged
        if precision >= precision_bits - 0.5:
            break
    
    return convergence_data
```

---

### 3.4 Validation & Analysis (`analyzer.py`)

#### 3.4.1 Precision Measurement

```python
def estimate_precision_bits(triad, test_vectors, target_vectors, 
                            ideal_bits=6):
    """
    Measure effective precision: How many bits match ideal digital?
    
    6-bit precision = max error < 1 LSB = V_range / 2^6
    """
    errors = []
    
    for x_test, y_ideal in zip(test_vectors, target_vectors):
        output_analog, _ = triad.forward(x_test)
        error = np.abs(output_analog - y_ideal)
        errors.append(error)
    
    max_error = np.max(errors)
    v_range = 1.0  # Normalized voltage swing
    lsb = v_range / (2 ** ideal_bits)
    
    achieved_bits = -np.log2(max_error / v_range)
    
    return achieved_bits
```

#### 3.4.2 Noise Robustness Analysis

```python
def sweep_noise_levels(triad, test_vectors, target_vectors):
    """
    Inject increasing levels of thermal noise, measure degradation
    
    Returns:
        - Noise level (σ) vs. precision (bits)
        - Failure threshold
    """
    noise_levels = np.logspace(-4, -2, 20)  # σ from 0.01% to 1%
    results = []
    
    for sigma_noise in noise_levels:
        # Inject Gaussian noise into all cell outputs
        for cell in triad.all_cells():
            cell.noise_sigma = sigma_noise
        
        precision = estimate_precision_bits(triad, test_vectors, 
                                            target_vectors)
        
        results.append({
            "noise_sigma": sigma_noise,
            "noise_percent": 100 * sigma_noise,
            "achieved_bits": precision,
            "passes_6bit": precision >= 5.5
        })
    
    return results
```

#### 3.4.3 Thermal Drift Compensation

```python
def measure_thermal_compensation(triad, test_vectors, target_vectors,
                                 temp_sweep_C=20):
    """
    Sweep temperature, measure how well MAML tracks drift
    
    Returns:
        - Temperature (°C) vs. precision without adaptation
        - Temperature (°C) vs. precision with MAML adaptation
        - Compensation effectiveness
    """
    maml = InvertedMAML(triad)
    results = {"no_adapt": [], "with_adapt": []}
    
    temp_range = np.linspace(0, temp_sweep_C, 10)
    
    for temp_delta in temp_range:
        # Inject thermal drift
        for cell in triad.all_cells():
            cell.add_thermal_drift(0.005 * temp_delta)
        
        # Measure without adaptation
        precision_no_adapt = estimate_precision_bits(triad, test_vectors, 
                                                     target_vectors)
        results["no_adapt"].append(precision_no_adapt)
        
        # Run one MAML cycle
        for x_test, y_target in zip(test_vectors, target_vectors):
            maml.update_weights(x_test, y_target)
        
        # Measure with adaptation
        precision_with_adapt = estimate_precision_bits(triad, test_vectors, 
                                                       target_vectors)
        results["with_adapt"].append(precision_with_adapt)
    
    return {
        "temp_range": temp_range,
        "precision_no_adapt": results["no_adapt"],
        "precision_with_adapt": results["with_adapt"],
        "improvement": np.array(results["with_adapt"]) - np.array(results["no_adapt"])
    }
```

---

## 4. Implementation Phases

### Phase 1: MVP (Week 1)
- [ ] `cell_physics.py` - 2T1C model + RC discharge
- [ ] `matrix_core.py` - Single 6×6 atomic triad
- [ ] `maml_optimizer.py` - Basic MAML loop
- [ ] **Test**: Single input vector → verify convergence

### Phase 2: Stratified Batching (Week 2)
- [ ] Implement 10-strata measurement windows
- [ ] Hadamard encoding for gradient extraction
- [ ] Reference cell fast-decay simulation
- [ ] **Test**: Stratified gradient vs. single-point gradient

### Phase 3: Robustness Analysis (Week 2.5)
- [ ] Thermal drift injection
- [ ] Noise sweep (parametric)
- [ ] Precision measurement (bits achieved)
- [ ] **Test**: Generate robustness curves

### Phase 4: Validation & Documentation (Week 3)
- [ ] Compare against ideal digital (6-bit requirement)
- [ ] Generate plots: convergence, robustness, thermal
- [ ] Performance profiling (speed)
- [ ] Documentation & tutorial

---

## 5. Input/Output Specifications

### 5.1 Configuration (`config_simulator.yaml`)

```yaml
# Cell Physics
cell:
  capacitor_nF: 100
  discharge_resistor_MOhm: 1.0
  fast_ref_resistor_kOhm: 330
  transistor_Vth_V: 0.6
  transconductance_scale: 1e-4

# Timing
timing:
  refresh_cycle_ms: 10
  num_strata: 10
  sampling_time_us: 2

# Voltages
voltages:
  data_swing_mV: 250
  weight_swing_V: 1.0
  source_potential_V: 1.65

# MAML Learning
maml:
  learning_rate: 0.01
  max_cycles: 100
  convergence_threshold_bits: 5.5
  
# Noise Injection
noise:
  thermal_drift_rate_per_degC: 0.005
  manufacturing_sigma_percent: 2.0
  thermal_noise_enabled: true

# Test Vectors
test:
  num_input_vectors: 16
  vector_dimension: 6
  precision_target_bits: 6
```

### 5.2 Output Metrics (`simulator_results.json`)

```json
{
  "experiment": "Inverted MAML 3x6x6 Simulator",
  "date": "2026-07-07",
  "convergence": {
    "cycles_to_convergence": 23,
    "final_loss": 1.2e-6,
    "precision_achieved_bits": 5.8
  },
  "robustness": {
    "noise_tolerance_percent": 0.3,
    "thermal_tolerance_degC": 15,
    "compensation_improvement_bits": 1.4
  },
  "performance": {
    "cycles_per_second": 1250,
    "total_runtime_sec": 8.4
  }
}
```

---

## 6. Visualization & Reporting

### 6.1 Generated Plots

1. **Convergence Curve**
   - X: Cycle number
   - Y: Loss + Precision (bits)
   - Show: With/without MAML adaptation

2. **Robustness Heatmap**
   - X: Thermal drift (°C)
   - Y: Noise injection (%)
   - Color: Precision achieved (bits)

3. **Strata Analysis**
   - 10 subplots (one per stratum)
   - Show: Gradient magnitude, loss distribution

4. **Thermal Compensation**
   - X: Temperature (°C)
   - Y1: Precision without MAML
   - Y2: Precision with MAML
   - Highlight: Improvement margin

---

## 7. Success Criteria

| Criterion | Target | Measurement |
|-----------|--------|-------------|
| **IF #1: Drift Tracking** | Converge < 30 cycles | Cycles to 6-bit precision |
| **IF #2: Gradient Quality** | SNR > 20dB | Noise-to-signal in stratum gradients |
| **IF #3: Noise Tolerance** | > 0.5% injection | Precision vs. noise sweep |
| **IF #4: Convergence Speed** | < 5ms per cycle | Runtime per MAML update |

---

## 8. File Structure

```
/simulator/
├── config_simulator.yaml
├── cell_physics.py
├── matrix_core.py
├── maml_optimizer.py
├── analyzer.py
├── main_simulation.py
├── requirements.txt
├── tests/
│   ├── test_cell.py
│   ├── test_matrix.py
│   └── test_maml.py
├── results/
│   ├── convergence_curves.png
│   ├── robustness_heatmap.png
│   ├── strata_analysis.png
│   └── simulator_results.json
└── README.md
```

---

## 9. Next Steps

1. **Code repository setup** → Create `/simulator/` directory
2. **Requirements.txt** → NumPy, SciPy, Matplotlib, PyYAML
3. **Phase 1 implementation** → Start with cell physics
4. **Integration testing** → Link components progressively

---

## 10. References

- **Patent**: SE 2630397-4 (Inverted MAML Architecture)
- **Key Docs**:
  - `Design_Specification_Analog_Matrix_2T1C.pdf` (Cell parameters)
  - `Reference_and_Bias_Cells_Specification.pdf` (Reference cell design)
  - `Inverted_MAML_Addendum_Stratified Batching.pdf` (Stratified batching math)
- **Component Datasheets**:
  - DOX3134A (N-channel MOSFET)
  - MCP6024T (Operational Amplifier)

---

**Document Status**: DRAFT (2026-07-07)  
**Next Review**: After Phase 1 completion
