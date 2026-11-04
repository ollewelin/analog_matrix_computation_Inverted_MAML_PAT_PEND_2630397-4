---
name: mode-a-parameter-benchmark
description: Automated parameter sweep execution and publication reporting for Inverted MAML Mode A hardware experiments on Card 2 (T120 SoC + T20 Coprocessor, 1k/5.1k attenuator). Standardizes varying LR, L2-reg, dynamic swing, and Patent Fig 7 hidden disturbances while enforcing identical 2-page publication PDF/MD report layouts.
---

# Mode A Silicon Parameter Benchmark & Automated Publication Reporting

This skill standardizes the execution, evaluation, and documentation of parameter variations on physical Inverted MAML silicon (Card 2).

## Core Objective
Ensure that **any** parameter variation (such as learning rate `lr`, L2-regularization `reg_lambda`, Patent Fig 7 hidden disturbance `variance`, dynamic swing `d_line`, stimulus distribution `noise_color`, or duration `epochs`) can be executed with a single command, automatically generating:
1. Complete JSON telemetry log in `FPGA_code/logs/mode_a_extended_training/`
2. High-resolution 3-panel dynamic curves PNG in `FPGA_code/docs/figures/` (with English labels and vertical phase dividers)
3. Standardized 2-page publication PDF in `FPGA_code/docs/`
4. Complete Markdown technical report in `FPGA_code/docs/` (including all injected $6 \times 6$ disturbance matrices)
5. Automatic copy of all 4 artifacts directly to the active conversation artifact directory
6. Automatic logging to `FPGA_code/docs/debug_journal.md` and `FPGA_code/docs/olle_log`

---

## Hardware Architecture & Phase Structure

The standardized 1000-epoch experiment evaluates strictly at **single-point $t = 5000\,\mu\text{s}$ (5.0 ms pure snapshot delay)** across four distinct experimental regimes:

| Phase | Epoch Window | Training State | Compensation $W^{(3,8)}$ | Matrix 33 State | Purpose |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Phase 1** | $0 .. 99$ | **OFF** ($\text{LR}=0, \lambda=0$) | $W=0\text{ LSB}$ | Nominal $W^{(33)}_\text{nominal}$ | Establish open-loop baseline error at zero compensation |
| **Phase 2** | $100 .. 199$ | **ON** ($\text{LR}, \lambda$) | Dynamic update | Nominal $W^{(33)}_\text{nominal}$ | Establish nominal closed-loop equilibrium & convergence baseline |
| **Phase 3** | $200 .. 599$ | **ON** ($\text{LR}, \lambda$) | Dynamic update | Hidden offset $\pm \delta\text{ LSB}$ (randomized every 100 ep) | Demonstrate active Inverted MAML compensation & drift tracking |
| **Phase 4** | $600 .. 1000$ | **OFF** ($\text{LR}=0, \lambda=0$) | $W=0\text{ LSB}$ (ablated) | Hidden offset $\pm \delta\text{ LSB}$ (randomized every 100 ep) | Ablation control: prove that error degrades without active MAML |

---

## Patent SE 2630397-4 Non-Cheating Constraint ("Fusk-skydd")
- The digital target supervisor ($Z_\text{target}$) in the T120 SoC **MUST ALWAYS** be computed against the unperturbed nominal matrix $W^{(33)}_\text{nominal}$.
- The randomized stochastic offsets $\delta_{r,c} \in [-\text{variance}, +\text{variance}]\text{ LSB}$ are uploaded strictly to the physical 2T1C capacitors on silicon via `client.set_w33_hidden_offset()`.
- The controller never "cheats" by incorporating the hidden offset into its target math.

---

## Execution Command

Run the unified orchestrator:
```bash
/home/olle/anaconda3/bin/python FPGA_code/scripts/run_card2_5ms_pure.py \
  --epochs <EPOCHS> \
  --lr <LR> \
  --reg-lambda <LAMBDA> \
  --w33-variance-lsb-range <VARIANCE> \
  --d-line <D_LINE> \
  --noise-color toeplitz \
  --rho 0.85 \
  --k-batch 20 \
  --tag <TAG>
```

Followed immediately by report generation:
```bash
/home/olle/anaconda3/bin/python FPGA_code/scripts/generate_5ms_pure_short_report.py \
  --json FPGA_code/logs/mode_a_extended_training/mode_a_<EPOCHS>ep_5ms_pure_<TAG>.json \
  --pdf FPGA_code/docs/INVERTED_MAML_CARD2_<EPOCHS>EP_5MS_PURE_<TAG>_REPORT.pdf \
  --md FPGA_code/docs/INVERTED_MAML_CARD2_<EPOCHS>EP_5MS_PURE_<TAG>_REPORT.md
```

Or using the unified wrapper script:
```bash
/home/olle/anaconda3/bin/python FPGA_code/scripts/run_and_report_5ms_pure.py \
  --epochs 1000 \
  --lr 0.16 \
  --reg-lambda 150 \
  --variance 4
```

---

## Standardized Report Structure Rules
1. **No Temporal Sweep Table:** Strictly omit pre- vs. post-temporal transfer functions ([4.5..5.5 ms]) because evaluations are purely single-point at 5.0 ms.
2. **Page Budget:** Ensure the generated PDF is strictly 2 pages (or maximum 3 without orphan lines).
3. **Language:** English technical headings, tables, labels, and figure annotations.
4. **Dividers:** 3-panel figure must have distinct vertical divider lines:
   - Epoch 100 (Blue dotted): Training ON (Nominal M33)
   - Epoch 200, 300, 400, 500 (Orange dashed): Disturbance Shift ($\pm \delta\text{ LSB}$, Training ON)
   - Epoch 600 (Red solid): Phase 4 Ablation (Training OFF, W=0)
   - Epoch 700, 800, 900, 1000 (Orange dashed): Disturbance Shift (W=0)
5. **Injected Matrices:** Display all randomized disturbance matrices in Section 5 (PDF grid) and Section 3/4 (Markdown codeblocks).

