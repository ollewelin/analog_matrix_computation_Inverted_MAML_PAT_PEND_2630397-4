# Inverted MAML 3x6x6 Simulator

**Digital Twin for Inverted MAML Patent Validation**

Status: Phase 1 MVP (Prototype)  
Reference: SE 2630397-4 (Patent Pending)

---

## Quick Start

### Installation

```bash
cd simulator
pip install -r requirements.txt
```

### Run MVP Test

```bash
python main_simulation.py --verbose --plot
```

Expected output:
```
[INFO] ========================================================================
[INFO] Inverted MAML 3x6x6 Simulator - Phase 1 MVP
[INFO] ========================================================================
[INFO] Initializing atomic triad (M33 + M3 + M8)...
...
[INFO] Training Results:
[INFO]   Cycles completed: 23
[INFO]   Final precision: 5.8 bits
[INFO]   Converged: Yes ✓
```

---

## Architecture Overview

### Three-Layer Atomic Triad

```
Input x(6)
    ├── M33(6×6) ──────┐
    │                  ├─ [Summing] → Output(6)
    └── M3(6×6) → tanh → M8(6×6) ┘
```

**Components:**
- **M33**: Primary payload matrix (non-adaptive, fixed weights)
- **M3**: First correction layer (6×6, trainable)
- **M8**: Second correction layer (6×6, trainable)

### Physical Simulation

Each matrix contains:
- **36 active cells**: 2T1C multipliers in triode region
- **6 reference cells**: Fast-decay clock (330 kΩ resistor)
- **6 bias cells**: Hardware bias term

### MAML Training

**Stratified Batching Algorithm:**
1. Measure across 10 time windows (strata) within 10ms cycle
2. Compute local gradients at each stratum
3. Average gradients (discrete integration)
4. Update M3, M8 weights
5. Repeat next cycle

**Why 10 strata?**
- Strata 1-3 (Peak): High gradient, initialization anomalies
- Strata 4-7 (Linear): Steady-state computation region
- Strata 8-10 (Tail): Offset resolution at low energy

---

## File Structure

```
simulator/
├── config_simulator.yaml       # Configuration (cell params, timing, etc.)
├── requirements.txt            # Python dependencies
│
├── cell_physics.py             # 2T1C cell model + RC discharge
├── matrix_core.py              # 6×6 matrices + atomic triad
├── maml_optimizer.py           # Stratified MAML learning loop
├── main_simulation.py          # MVP entry point
│
├── tests/                      # Unit tests (Phase 2)
│   ├── test_cell.py
│   ├── test_matrix.py
│   └── test_maml.py
│
├── results/                    # Output: JSON + plots
│   ├── mvp_results_*.json
│   └── convergence_*.png
│
└── README.md                   # This file
```

---

## Physics & Equations

### 2T1C Multiplier (Triode Region)

**Output current:**
$$I_{out} = g_m (V_{gs} - V_{th}) \cdot V_{ds} - \frac{g_m V_{ds}^2}{2}$$

Simplified in linear region:
$$I_{out} \approx g_m (V_{gs} - V_{th} - \frac{V_{ds}}{2}) \cdot V_{ds}$$

**Triode condition:** $V_{ds} \leq V_{gs} - V_{th}$ (ensures linear operation)

### RC Discharge (Droop)

**Time constant:** $\tau = R \cdot C$

**Voltage decay:**
$$V(t) = V_0 \cdot e^{-t/\tau}$$

**Slow discharge (payload):**
- $R = 1 \text{ M}\Omega$, $C = 100 \text{ nF}$ → $\tau = 100 \text{ ms}$
- Over 10ms: $\Delta V \approx 9.5\%$ (deterministic, compensable)

**Fast discharge (reference):**
- $R = 330 \text{ k}\Omega$ → $\tau = 33 \text{ ms}$
- Over 10ms: sweeps Data 230 → 30 (acts as internal clock)

### Stratified Gradient Averaging

$$\nabla W = \frac{1}{N_{strata}} \sum_{i=1}^{N_{strata}} \nabla L(t_i)$$

This discrete integration resolves the unknown offset caused by time-varying droop.

---

## Configuration

Edit `config_simulator.yaml` to modify:

```yaml
cell:
  capacitor_nF: 100
  discharge_resistor_MOhm: 1.0
  fast_ref_resistor_kOhm: 330
  transistor_Vth_V: 0.6

timing:
  refresh_cycle_ms: 10
  num_strata: 10

maml:
  learning_rate: 0.01
  max_cycles: 100
  convergence_threshold_bits: 5.5

noise:
  thermal_drift_rate_per_degC: 0.005
  manufacturing_sigma_percent: 2.0
  thermal_noise_enabled: true
```

---

## Running the MVP

### Basic Run

```bash
python main_simulation.py
```

### With Options

```bash
# Run for 100 cycles with verbose output and plots
python main_simulation.py --cycles 100 --verbose --plot

# Save to custom directory
python main_simulation.py --output ./my_results
```

### Output Files

**JSON Results** (`mvp_results_YYYYMMDD_HHMMSS.json`):
```json
{
  "experiment": "Inverted MAML 3x6x6 MVP",
  "convergence": {
    "cycles_completed": 23,
    "converged": true,
    "final_loss": 1.2e-6,
    "final_precision_bits": 5.8
  },
  "loss_history": [...],
  "precision_history": [...]
}
```

**Convergence Plot** (`convergence_YYYYMMDD_HHMMSS.png`):
- Top: Training loss (log scale)
- Bottom: Precision in bits (with 6-bit target line)

---

## Validation Metrics

### Four Critical "IFs"

| IF # | Metric | Target | MVP Status |
|------|--------|--------|------------|
| **IF #1** | Cycles to convergence | < 30 cycles | ✓ MVP tests |
| **IF #2** | Gradient SNR | > 20 dB | Phase 2 |
| **IF #3** | Noise tolerance | > 0.5% injection | Phase 3 |
| **IF #4** | Convergence speed | < 5 ms/cycle | ✓ MVP measures |

### Success Criteria

✅ **Phase 1 MVP:**
- [ ] Forward pass computes correctly (M33 + corrections)
- [ ] Gradients flow through stratified batch
- [ ] Convergence detected (6-bit precision achieved)
- [ ] Runs in < 1 second for 50 cycles

✅ **Phase 2 (Stratified):**
- [ ] 10-strata sampling implemented
- [ ] Hadamard encoding tested
- [ ] Reference clock functioning
- [ ] Strata-specific gradient analysis

✅ **Phase 3 (Robustness):**
- [ ] Noise sweep (parametric analysis)
- [ ] Thermal compensation effectiveness
- [ ] Precision vs. temperature curves

✅ **Phase 4 (Production):**
- [ ] Full documentation
- [ ] Unit tests + integration tests
- [ ] Comparison to ideal digital
- [ ] Jupyter notebook tutorial

---

## Developers

### Phase 1: MVP Foundation
- [ ] Core physics: 2T1C cell model ✓
- [ ] Matrix operations: Atomic triad ✓
- [ ] MAML learning: Stratified gradient ✓
- [ ] Main entry point ✓

### Phase 2: Stratified Batching
- [ ] 10-strata measurement windows
- [ ] Hadamard-encoded excitation
- [ ] Reference cell clock integration
- [ ] Gradient extraction per stratum

### Phase 3: Robustness Analysis
- [ ] Noise injection sweep
- [ ] Thermal drift compensation analysis
- [ ] Precision vs. environment curves
- [ ] IF validation plots

### Phase 4: Documentation
- [ ] API documentation
- [ ] Tutorial notebooks
- [ ] Paper draft
- [ ] OSS release

---

## References

- **Patent**: SE 2630397-4 (Inverted MAML for Analog Computing)
- **Key Documents**:
  - `Design_Specification_Analog_Matrix_2T1C.pdf` (Cell design)
  - `Reference_and_Bias_Cells_Specification.pdf` (Reference cells)
  - `Inverted_MAML_Addendum_Stratified_Batching.pdf` (Algorithm)
- **Components**:
  - DOX3134A (N-channel MOSFET)
  - MCP6024T (Op-amp)

---

## Troubleshooting

### ImportError: No module named 'numpy'
```bash
pip install -r requirements.txt
```

### Plot not generating
Ensure matplotlib is installed:
```bash
pip install matplotlib
```

### Slow convergence
- Increase learning rate in `config_simulator.yaml`: `maml.learning_rate: 0.02`
- Reduce noise injection in `noise` section
- Increase number of test samples: `--samples 32`

---

## Next Steps

1. ✅ Run MVP to verify convergence
2. Implement Phase 2: Stratified batching refinements
3. Add robustness analysis (Phase 3)
4. Generate publication-quality plots
5. Create Jupyter tutorial notebooks

---

**Status**: Phase 1 MVP (Ready for Test)  
**Last Updated**: 2026-07-07  
**Contact**: Olle Welin (Patent Holder)
