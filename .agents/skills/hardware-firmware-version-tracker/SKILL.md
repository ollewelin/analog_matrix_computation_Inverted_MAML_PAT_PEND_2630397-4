---
name: hardware-firmware-version-tracker
description: Systematic hardware revision, modification status, firmware commit lineage, and experimental parameter tracking for Inverted MAML silicon experiments.
---

# Inverted MAML Hardware & Firmware Version Lineage Protocol

## 1. Scope & Objective
This skill defines the mandatory protocol for logging, tracking, and propagating hardware revision status, physical board modifications, FPGA firmware commit hashes, and experimental operating parameters across all scripts, telemetry dumps, research notes, and publication reports.

Whenever experiments are conducted on physical silicon (Trion T120 Master + T20 Controller, Patent Pending SE 2630397-4), the exact hardware setup and firmware state must be unambiguously documented so past and future results can be compared without ambiguity.

---

## 2. Hardware Status Registry (Current Setup: October 2026)

| Parameter | Current Silicon Setup | Next PCB Spin (Target) |
| :--- | :--- | :--- |
| **Carrier Board PCB** | **PCB v1.3.2** | PCB v1.4 / v2.0 |
| **Summing Attenuator Mod** | **$1\text{ k}\Omega / 5.1\text{ k}\Omega$ SMD network** ($\sim 16.4\%$ compensation authority) | $1\text{ k}\Omega / 15\text{ k}\Omega$ ($\sim 6.25\%$) |
| **ADC Architecture** | Primary $M_{33}$ (ADC45) + Summed Triad (ADC49) (XC2361A 12-bit differential) | Dedicated intermediate ADC149 rack (6 extra ADCs) |
| **Target FPGAs** | Efinix Trion T120F324 Master SoC (`192.168.1.50:5000`) + T20F256 Controller | Same or Titanium Ti180 |
| **Operational Mode** | Mode A (Jumper mode 3: Layer 1 $M_3 \to$ COLTIA3 $\to$ Layer 2 $M_8 \to$ COLTIA8) | Mode A |
| **Refresh Frequency** | $100\text{ Hz}$ ($10.0\text{ ms}$ capacitive cadence on 100 nF gates) | $100\text{ Hz}$ |

---

## 3. Firmware Baseline Registry

- **Reference True-Batch Baseline:** Commit [`34f592a`](file:///home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/sw/t120_master/src/maml_platform.c) (Monday Oct 26, 2026).
  - Proven Condition 10: $K=20$, $\text{LR}=0.03x$ ($Q16=32$), $10\text{ strata}$ in $[4.9, 5.1]\text{ ms}$.
  - Net Loss Reduction: $-16.4\%$ ($\beta_1 = -23.35\text{ LSB}^2/\text{epok}$, $R^2 = 0.0621$).
  - Weight clamping: $\pm 80\text{ LSB}$ (`sat_w80_q14`).
  - Input swing: $[-45, +45]\text{ LSB}$ ($X_{dac} \in [83, 173]$).

- **v2.2-MAML Identical-Cadence & True-Zero Calibration Update (Nov 1, 2026):**
  - **Files Updated:** [`maml_platform.c`](file:///home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/sw/t120_master/src/maml_platform.c) and [`run_500ep_broadened_window_k20.py`](file:///home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/scripts/run_500ep_broadened_window_k20.py).
  - **Bug Fix 1 — True $W=0$ Quiescent Zero Calibration (`maml_calibrate_zero_baseline`):** Removed legacy hardcoded weights (`M3[c][c]=+64, M3[6][c]=+48, M8[r][c]=+24`) during quiescent zero-reference calibration so `g_adc45_zero_cal` and `g_adc49_zero_cal` are calibrated strictly at true zero ($W_{M3}=0, W_{M8}=0, X=0$) at $t = 5.0\text{ ms}$. Locked `g_adc49_zero_cal` at Epoch 0 so switching from Phase 1 (`g_baseline_mode=0`) to Phase 2 (`g_baseline_mode=1`) at Epoch 100 never overwrites or shifts the target origin `z_target`.
  - **Bug Fix 2 — 100% Identical Batch, Hadamard & Window Evaluation Across All 500 Epochs (`MAML_CMD_BATCH_STEP`):** Enabled `lr_val == 0` (`g_lr_inner_q16 = 0`) in `MAML_CMD_BATCH_STEP` and `maml_execute_strata_batch()`. Every single epoch across all three phases (`Ep 0..99` Baseline Zero, `Ep 100..199` Fixed Smart Baseline, and `Ep 200..500` Active Training) now executes the exact same $K=20 \times 10\text{ strata} = 200\text{ samples/epoch}$ (`[4500..5500 µs]`) batch loop with full Hadamard perturbation bursts active on every stratum. Only `lr`, `reg_lambda`, and the baseline weight table change between phases, guaranteeing 100% identical EMC, capacitor refresh cadence, thermal load, and 200-sample statistical Loss/RMSE/ENOB measurement across all 500 epochs.

---

## 4. Virtual Gain & Virtual Attenuation Emulation Protocol (`[VIRTUAL_HARDWARE_EMULATION]`)

Because PCB v1.3.2 lacks the planned $1\text{ k}\Omega / 15\text{ k}\Omega$ attenuator and the intermediate ADC149 rack, experimental runs may employ digital/analog ratio adjustments to force the compensation branch to exercise its non-linear S-curves.

### Mandatory Tagging Rule
Any script, log, or report utilizing this technique MUST include the tag:
`[VIRTUAL_HARDWARE_EMULATION]`
and explicitly specify:
1. **$D_{line}$ (Data line attenuation factor):** e.g. $1\times, 2\times, 4\times$ ($X \in [-45/D_{line}, +45/D_{line}]$).
2. **$D_{w33}$ (Matrix 33 weight attenuation factor):** e.g. $1\times, 2\times, 4\times$ ($W_{33} = k\_default\_m33 / D_{w33}$).
3. **$G_{req}$ (Digital supervisor target demand gain):** e.g. $1.0\times, 2.0\times, 4.0\times$ ($Z_{target} = \text{cal}_0 + G_{req} \times \frac{1}{256}\sum W_{33} X$).
4. **$W_{clamp}$ (Compensation weight limit):** e.g. $80\text{ LSB}, 120\text{ LSB}$.
5. **Note:** Clearly note that this emulation will be superseded by physical hardware in future PCB revisions where analog dynamics are natively optimized.

---

## 5. Automated Metadata Schema for JSON Experiment Logs
Every experiment log written to `FPGA_code/logs/` MUST contain the following root metadata block:

```json
{
  "provenance": {
    "pcb_version": "v1.3.2",
    "hardware_mods": "1k / 5.1k ohm summing attenuator (no ADC149)",
    "git_commit": "<current_short_hash>",
    "git_dirty": false,
    "soc_target": "Efinix Trion T120F324 @ 192.168.1.50:5000",
    "mode": "Mode A (Jumper 3, 2-layer Triad)",
    "virtual_emulation": {
      "active": true,
      "d_line": 2,
      "d_w33": 2,
      "target_gain": 4.0,
      "w_clamp": 120,
      "note": "Virtual Attenuator Emulation on PCB v1.3.2"
    }
  }
}
```

---

## 6. Report Header Format
Every markdown and PDF report generated MUST present the following standardized summary block:

```markdown
### Hardware & Firmware Provenance
- **Carrier Board:** PCB v1.3.2 (Summing attenuator: 1k / 5.1k Ohm installed)
- **Silicon:** Efinix Trion T120F324 Master SoC (`192.168.1.50:5000`) + T20F256
- **Firmware Commit:** `<git_hash>` (`maml_platform.c`)
- **Virtual Emulation:** `[VIRTUAL_HARDWARE_EMULATION]` $D_{line}=2$, $D_{w33}=2$, $G_{req}=4.0\times$, $W_{clamp}=120\text{ LSB}$
- **Batching Parameters:** $K=20$, $10\text{ strata}$ ($4.9\text{--}5.1\text{ ms}$), $\text{LR}=0.03x$
```

