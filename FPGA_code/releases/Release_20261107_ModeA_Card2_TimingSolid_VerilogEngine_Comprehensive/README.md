# Inverted MAML Official Release: Rock-Solid Verilog 10.000 ms Timing & Comprehensive W(3) Staircase Package
**Release Tag:** `Release_20261107_ModeA_Card2_TimingSolid_VerilogEngine_Comprehensive`  
**Date:** 2026-11-07  
**Hardware Target:** Card 2 (PCB v1.3.2, 1k/3.3k Attenuator Mod, Repaired CH3) | Efinix Trion T120 Master SoC + Trion T20 Coprocessor  
**Patent Reference:** SE 2630397-4 (Open Science Hardware)  
**Silicon Verification Commits:** [`536f5b1`](file:///home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4), [`2caaaec`](file:///home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4), [`47858fb`](file:///home/olle/AnalogAI/git/git_test_c/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4)  

---

## 🚀 Key Technological Breakthrough: 100% Verilog Crystal-Locked Frame Engine (0.00 ns Jitter)

Prior firmware revisions sequenced 2T1C gate capacitor refreshes and Hadamard perturbation bursts through RISC-V C code polling loops (`bsp_uDelay`, S-bus polling, blocking 115200-baud UART status prints). This introduced hundreds of microseconds of jitter and deadline overruns during the final 2 ms of the 10 ms cycle.

This release completely removes software from the physical timing loop by implementing a **pure Verilog autonomous frame engine** in `t120_analog_io_ctrl.sv` and `t120_inter_fpga_bridge.sv`:
1. **Crystal-Locked 10.000000 ms Modulo-500,000 Counter (`frame_timer` @ 50.000 MHz):**
   - Refreshes start at exact cycle 0 (`t = 0.000000 ms`), phase-locking the 2.0 MHz inter-FPGA clock (`CLK9`).
   - Automatically sequences all 12 half-columns (`col 0..5`, `pos/neg`) directly from high-speed on-chip dual-port `shadow_w_ram` (`0x400..0x5FF`) with $90.00\,\mu\text{s}$ dwell per step ($1.080\,\text{ms}$ total refresh).
2. **Deterministic Hardware Stratum Settling & ADC Read:**
   - Counts down exact hardware stratum delays ($4500\dots 5900\,\mu\text{s}$).
   - Samples 16× hardware-averaged forward ADCs in quiet Hi-Z ($0x8000$).
3. **Synchronous 14-Step Sylvester $H_8$ Simplex Hadamard Burst:**
   - Shifts Hadamard carriers directly from hardwired Verilog ROM at 10.0 MHz `CLK9`.
   - Executes time-separated Matrix 8 burst ($0x3F00$), quiet $20.00\,\mu\text{s}$ Hi-Z separation gap, and Matrix 3 burst ($0x003F$).
   - Returns to $0x8000$ Hi-Z and autonomously refreshes T20 watchdog and LED states.
4. **C Firmware Decoupled:**
   - RISC-V software now operates purely as an asynchronous supervisor: it writes updated weights to `shadow_w_ram` and reads finished hardware frames. Software delays or UART traffic can **never** distort physical silicon timing!

---

## 📊 Consolidated Empirical Benchmarks on Card 2 Silicon

### 1. Broadened Window [4.5..5.5 ms] Online SGD ($K=1$, 11 Strata, $\pm 5$ LSB Disturbance):
- **Phase 1 (Baseline $W=0$):** Window Loss $= 51,653.8\,\text{LSB}^2$ ($3.97\,\text{b}$) | 5.0 ms: $6,965.3\,\text{LSB}^2$ ($5.54\,\text{b}$)
- **Phase 2 (Active Nominal):** Window Loss $= 49,157.5\,\text{LSB}^2$ ($4.00\,\text{b}$) | 5.0 ms: $6,878.2\,\text{LSB}^2$ ($5.60\,\text{b}$)
- **Phase 3 (Active Tracking $\pm 5$ LSB):** Window Loss $= 50,795.1\,\text{LSB}^2$ ($3.99\,\text{b}$) | 5.0 ms: $24,345.0\,\text{LSB}^2$ ($4.61\,\text{b}$)
- **Phase 4 (Ablation $W=0$ under $\pm 5$ LSB):** Window Loss $= 83,128.9\,\text{LSB}^2$ ($3.65\,\text{b}$) | 5.0 ms: $41,762.3\,\text{LSB}^2$ ($4.22\,\text{b}$)
- **Ablation Contrast:** $+63.7\%$ error increase upon disconnecting compensation ($+71.5\%$ surge at 5.0 ms).

### 2. Shifted Window [4.9..5.9 ms] Online SGD ($K=1$, 11 Strata, $\pm 5$ LSB Disturbance):
- **Phase 1 (Baseline $W=0$):** Window Loss $= 102,342.3\,\text{LSB}^2$ ($3.47\,\text{b}$)
- **Phase 2 (Active Nominal):** Window Loss $= 41,834.9\,\text{LSB}^2$ ($4.12\,\text{b}$, **$-59.1\%$ error reduction**, $+0.65\,\text{b}$ gain!)
- **Phase 3 (Active Tracking $\pm 5$ LSB):** Window Loss $= 55,163.0\,\text{LSB}^2$ ($3.93\,\text{b}$)
- **Phase 4 (Ablation $W=0$ under $\pm 5$ LSB):** Window Loss $= 117,572.5\,\text{LSB}^2$ ($3.38\,\text{b}$, **$+113.1\%$ error increase!**)
- **Ablation Contrast:** More than **$2.1\times$ error increase** without active compensation on the deep capacitor discharge slope.

---

## 📦 Directory Structure & Deliverables

- `sw/t120_master/`:
  - `src/main.c`: Clean runtime loop without blocking UART/MDIO operations.
  - `src/maml_platform.c`: Pure Verilog frame engine driver, `shadow_w_ram` synchronization, and non-blocking background ticks.
  - `include/t120_bridge_regs.h`: Hardware register map for APB3 base `0xF8104000` (`0x080..0x0B0` and `0x400..0x5FF`).
  - `binaries/`: Pre-compiled `t120_master.hex` and `t120_master.bin`.
- `T120F324/`:
  - `t120_analog_io_ctrl.sv`: Pure Verilog 10.000000 ms autonomous frame engine.
  - `t120_inter_fpga_bridge.sv`: Autonomous hardware master ports & Sylvester $H_8$ Simplex ROM.
  - `t120_bridge_clkgen.sv`: Phase-locked 2.0 MHz / 10.0 MHz `CLK9` generator.
  - `top_level.sv`: Master interlock wiring.
  - `bitstreams/`: Synthesized and timing-verified bitstream (`T120_MALM.bit` and `T120_MALM.hex`).
- `T20F256/`:
  - `t20_hw_responder.sv`: Slave responder logic for differential column gates (`G_P/G_N`) and Hadamard 3-state drivers.
  - `bitstreams/`: Verified `T20F256.bit` and `T20F256.hex`.
- `pc_python/`:
  - `run_card2_broadened_11strata_k1_online.py`: Primary 1000-epoch online runner.
  - `generate_card2_w3_staircase_comprehensive_report.py`: Automated 10-page publication PDF/MD report generator.
  - `verify_and_guard_version.py`: Pre-flight version guard.
  - `flash_soc.py` & `program_t120.py`: High-speed JTAG flashing tools.
- `reports_and_logs/`:
  - `INVERTED_MAML_CARD2_1000EP_W3_STAIRCASE_COMPREHENSIVE_REPORT.pdf` ([4.5..5.5 ms])
  - `INVERTED_MAML_CARD2_1000EP_4900TO5900US_W3_STAIRCASE_COMPREHENSIVE_REPORT.pdf` ([4.9..5.9 ms])
  - Complete 1000-epoch JSON telemetry datasets and high-resolution 3D figures.

---

## 🛠 Reproduction Runbook

### 1. Verify Board Telemetry & Logic Version
```bash
/home/olle/anaconda3/bin/python pc_python/verify_and_guard_version.py
```

### 2. Flash T120 SoC (if needed)
```bash
/home/olle/anaconda3/bin/python pc_python/flash_soc.py
```

### 3. Execute 1000-Epoch Benchmark:
- **[4.5..5.5 ms] Window:**
  ```bash
  /home/olle/anaconda3/bin/python pc_python/run_card2_broadened_11strata_k1_online.py \
    --noise-color white --staircase-w3 --epochs 1000 --k-batch 1 --lr 0.02 --reg-lambda 2048 \
    --d-line 2 --t-min 4500 --t-max 5500 --t-step 100 --attenuator 1k/3.3k --w33-variance-lsb-range 5
  ```
- **[4.9..5.9 ms] Window:**
  ```bash
  /home/olle/anaconda3/bin/python pc_python/run_card2_broadened_11strata_k1_online.py \
    --noise-color white --staircase-w3 --epochs 1000 --k-batch 1 --lr 0.02 --reg-lambda 2048 \
    --d-line 2 --t-min 4900 --t-max 5900 --t-step 100 --attenuator 1k/3.3k --w33-variance-lsb-range 5
  ```
