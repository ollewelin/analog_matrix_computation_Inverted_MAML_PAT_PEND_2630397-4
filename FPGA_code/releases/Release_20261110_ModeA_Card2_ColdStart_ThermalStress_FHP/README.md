# Release 2026-11-10: Mode A Card 2 Cold-Start Thermal Stress & Forward Hadamard Demodulation (FHP)

**Patent Pending:** SE 2630397-4 (Inverted MAML Silicon)  
**Hardware Target:** Card 2 (PCBA v1.3.2 | Trion T120 Master SoC + Trion T20 Coprocessor | 1k/3.3k Attenuator)  
**Execution Type:** Cold-Start Initialization (DC Zero-Cal at Ambient Room Temp 21°C with Heaters OFF at t=0)

---

## 1. Release Package Contents

- **`reports_and_logs/`**:
  - `INVERTED_MAML_CARD2_COLD_START_THERMAL_STRESS_FHP_COMPREHENSIVE_REPORT.pdf`: Complete 14-page publication report in English.
  - `INVERTED_MAML_CARD2_COLD_START_THERMAL_STRESS_FHP_COMPREHENSIVE_REPORT.md`: Comprehensive Markdown documentation.
  - `card2_thermal_cycling_heaters_8m8m_30pct_1hz_regler_2m2m_l2_768_k2_lr0p02_5p0_to_5p4ms_cold_start_20min.json`: Complete 20-minute (3,576 epochs) hardware execution dataset.
  - `figures/`: High-resolution publication figures (Timeline, Waterfall Heatmap, 2D/3D Weight Matrices with active M3/M8 rows, 5-Strata Profiles, 2x2 Factorial Summary).
- **`pc_python/`**:
  - `run_card2_thermal_cycling.py`: Master hardware runner supporting `--heater-start {off,on}`.
  - `run_card2_thermal_cold_start.sh`: Convenience launcher for cold-start thermal cycling.
  - `thermal_live_gui.py` & `run_thermal_gui.sh`: Real-time PyQt GUI telemetry monitor.
  - `generate_card2_thermal_cycling_report.py`: Telemetry analysis and figure generation script.
  - `compile_card2_cold_start_thermal_report_pdf.py`: Dedicated 14-page PDF and Markdown compilation engine.

---

## 2. Key Quantitative Findings (Cold-Start Silicon Execution)

1. **Heating Drift Surge (+91.5% Error):**
   - Cold Open-Loop Baseline (Heat OFF, W=0): **30,010.2 LSB² (4.37 b window, 4.66 b center 5.2 ms)**.
   - Warm Open-Loop Thermal Drift (Heat ON, W=0): surged to **57,471.5 LSB² (3.91 b window, 4.02 b center)**.
   - Thermal expansion away from the cold DC anchor caused a **+91.5% (+1.92x) error spike**.
2. **Mode A Closed-Loop Drift Rejection (-56.9% Error):**
   - Warm Closed-Loop Regulation (Heat ON, SGD ON): suppressed error down to **24,786.3 LSB² (4.57 b window, 4.92 b center)**.
   - Mode A delivers **-56.9% error reduction**, recovering **+0.66 bits window-wide (+0.90 bits at center)**.
3. **Ambient Closed-Loop Gain (-42.4% Error):**
   - Cold Closed-Loop Regulation (Heat OFF, SGD ON): suppressed error to **17,280.6 LSB² (4.82 b window, 5.15 b center)**.
4. **Bidirectional Symmetry & Physical Proof:**
   - Comparing the Warm-Start test (cold drift surge to 75,638 LSB², W8 pull to +117 LSB) and this Cold-Start test (hot drift surge to 57,472 LSB², active W3 expansion to +58 LSB and W8 to -41 LSB) provides irrefutable physical proof of bidirectional MOS drift cancellation on physical silicon.
5. **Forward Hadamard Propagation (FHP):**
   - Walsh-Hadamard orthogonal carrier modulation (Patent Fig 8) extracts exact physical gradients directly on silicon without mathematical backprop, preventing gradient mismatch catastrophe.
