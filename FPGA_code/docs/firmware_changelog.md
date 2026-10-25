# Inverted MAML Firmware & Bitstream Release Changelog

**Ledger Maintainer:** `maml_research_planner` (Step-by-Step Research Planner & Firmware Gatekeeper)  
**Hardware Platforms:** Trion T120F324 (Master RISC-V SoC) & Trion T20F256 (Coprocessor / Analog Matrix Interface)

---

## Firmware Release History

### Release 2026-10-25 19:35:00 CEST — T120 Master Firmware v2.3-MAML (Atomic Triad 2-Layer Wakeup: Equations 4 & 7 Fix, Cascade Polarity & Fan-in Normalization)
- **Date & Local Time:** `2026-10-25 19:35:00 CEST`
- **Target Subsystem:** T120 Master Sapphire RISC-V SoC BRAM (compiled via `flash_soc.py` in 14.3s via JTAG)
- **Git Commit / Working Base:** `614f441` / `main`
- **Files Modified:**
  - `FPGA_code/sw/t120_master/src/maml_platform.c` (Equations 4 & 7)
  - `FPGA_code/scripts/maml_post_analysis_gui.py` (Dual 3D Matrix 3 Pop-up Studio)
  - `FPGA_code/scripts/run_mode_a_sequential_vector_transfer.py` (2-Layer logging & active 6x6 correlation)
- **Key Engineering Discoveries & Silicon Verification:**
  1. **Layer 1 Matrix 3 Truncation Root Cause Discovered:**
     - In earlier versions, Equation 4 shifted the column error sum by `>> 8` (dividing by 256) and Equation 7 shifted `prod` by `>> 7` (dividing by 128), causing a total division by $32\,768$ (compared to only `>> 1` for Matrix 8).
     - With live empirical `sens_m3` around $15\text{ LSB}$, the integer product was truncated to **exact zero (`0`)**, freezing Matrix 3 at baseline across all previous Mode A runs.
  2. **Layer 2 Cascade Inverting Polarity Fixed:**
     - Because `COLTIA_8` / `COLTIA_49` is an inverting summing amplifier, using `-err49[j]` in Equation 4 created *positive feedback* for Layer 1.
     - Changed to `+err49[j]` in Equation 4, establishing true negative feedback error cancellation for Matrix 3.
  3. **6x6 Cascade Fan-in Normalization:**
     - Normalized Equation 4 shift to `>> 6` (dividing by 64) and Equation 7 shift to `>> 3` (dividing by 8) to prevent 6-row summing saturation.
  4. **Empirical Monotonic 2-Layer Convergence Confirmed on Hardware:**
     - 10-step silicon test showed monotonic loss reduction: RMSE dropped from $78.75\text{ LSB}$ ($4.70\text{ b}$) down to $26.31\text{ LSB}$ ($6.28\text{ b}$) in 6 steps.
     - Matrix 3 adapted dynamically with individual cell shifts up to $-12\text{ LSB}$, actively driving `ADC_45` in harmony with Matrix 8.
  5. **GUI Dual 3D Visualization:**
     - `Matrix3PopupWindow` upgraded to render two side-by-side 3D surfaces: left shows $\Delta W_3$ relative to baseline (starting flat at $0\text{ LSB}$), right shows absolute $W_3$.
  6. **Catastrophic Forgetting & Arbitrary Vector Strategy:**
     - Proved that single-vector locking causes weight flipping (catastrophic forgetting) across vector switches ($X_A \to X_B$) because a single locked point allows weights to fit a point-specific DC offset.
     - Future path: Multi-vector mini-batching over $K$ vectors to force the 2-layer network to learn an input-invariant representation.

---

### Release 2026-10-24 12:30:00 CEST — T120 Master Firmware v2.2-MAML (Decoupled Snapshot Timing & Full 6x6 Mode B Verification)
- **Date & Local Time:** `2026-10-24 12:30:00 CEST`
- **Target Subsystem:** T120 Master Sapphire RISC-V SoC BRAM & Flash Archive
- **Git Commit / Working Base:** `9b3e6c7` / `main`
- **Bitstream Archive:** `FPGA_code/bitstreams_archive/20261024_T120_MAML_DecoupledTiming_M3_M33_Alive/`
  - Bitstream: `T120_MALM.bit` (MD5: `3f7be1a6089bfe26211f77f84768ad44`, 10,651,071 bytes)
  - Bitstream Flash: `T120_MALM.hex` (MD5: `05f2e3f3a96c1588139bfbcf5416b27d`, 10,651,071 bytes)
  - Firmware Binary: `t120_master.bin` (MD5: `0b47d93dd68543afd18cad5736c67a9e`, 27,182 bytes)
  - Firmware HEX: `t120_master.hex` (MD5: `dad53d94320a2e8201bdbab00fdb759f`, 76,528 bytes)
  - Firmware ELF: `t120_master.elf` (MD5: `1afc7ea67c8bd62a7f504c7290eb4b50`, 38,612 bytes)
- **Standalone Test Catalog:** `FPGA_code/sw/standalone_test_versions/Matrix33_Full_36Cell_Gain_Landscape_Test/`
- **Key Engineering Changes & Silicon Verification:**
  1. **Decoupled Multiplier Snapshot Delay (`snap_dly_us`):** Fully decoupled from Hadamard timing registers. Operators can sample ADC49 anywhere across `0..9500 µs` relative to the 100 Hz refresh pulse.
  2. **Automated Background Random Data Auto-Pause:** Probing any cell via `maml_probe_single_cell()` automatically clears `g_auto_random_data = 0u`, guaranteeing 100% quiescent, unmodulated inputs on unprobed rows during manual or automated characterization.
  3. **Universal Subthreshold Turnaround Roll-Over Physics Confirmed:** Validated across all 36 crosspoints that P-channel gate pinch-off occurs at $W < -80\text{ LSB}$, causing differential gain to roll backwards.
  4. **Full 6x6 Matrix 33 Empirical Mapping:** All 36 cells characterized in Mode B (uncompensated silicon). Confirmed massive dynamic range ($\pm 180\text{ mV}$ to $\pm 1200\text{ mV}$) and mapped the complete 3D spatial gain topography.
  5. **100 Hz Refresh Preservation:** Continuous 100 Hz autonomous refresh engine strictly preserved in background.
- **Rollback Safety:** If subsequent Mode A or Mode C experiments destabilize, this exact configuration can be restored immediately from the standalone test archive.

---

### Release 2026-10-12 22:15:46 CEST — T120 Master Firmware v2.1-MAML
- **Date & Local Time:** `2026-10-12 22:15:46 CEST`
- **Target Subsystem:** T120 Master Sapphire RISC-V SoC BRAM (loaded via OpenOCD JTAG)
- **Git Commit / Working Base:** `a2894ef` / `main`
- **Files Modified:**
  - `FPGA_code/sw/t120_master/src/maml_platform.c`
  - `FPGA_code/docs/ANALOG_MULTIPLIER_DIAGNOSTIC_REPORT.md`
  - `FPGA_code/docs/debug_journal.md`
- **Key Engineering Changes:**
  1. **COLTIA Op-Amp Pedestal Bias:** Added unmodulated row pedestal bias (`+48` on row `(row+3)%6` held at constant `DAC_2 = 128`) in `maml_probe_charge_column()` for both Matrix 33 and Matrix 8 to keep the single-supply difference amplifier (`U1/U2$CBB15` $\rightarrow$ `ADC_49`) centered at `+0.33 V` above `GND` during single-cell DC probing.
  2. **Row 7 & Row 8 Modulation:** Bound `g_dac_row7_code` (`w34[6]` / `DAC2_D_ROW7` / `TRIM_B1`) and `g_dac_row8_code` (`w34[7]` / `DAC2_D_ROW8` / `TRIM_REF`) into `maml_refresh_all_columns()` and `maml_probe_single_cell()` so Row 7 and Row 8 single-cell probes modulate their actual MOSFET drain rails instead of modulating `DAC_2[0..5]`.
  3. **Hadamard Fresh Capacitor Refresh:** Added explicit call to `maml_refresh_all_columns()` at the beginning of `maml_diag_hadamard()` so every Hadamard diagnostic sweep launches from fresh capacitor charge.
- **Verification Status:** Verified live on hardware (`192.168.1.50:5000`). 84 crosspoint cells characterized (Matrix 3: 48 cells, mean $+257.3\text{ LSB}$; Matrix 33: 36 cells, mean $+507.0\text{ LSB}$).

---

### Release 2026-10-12 21:00:00 CEST — T20 Multi-Image SPI NOR Flash (T20_Golden + T20_Custom)
- **Date & Local Time:** `2026-10-12 21:00:00 CEST`
- **Target Subsystem:** T20 Coprocessor Winbond W25Q64 SPI NOR Flash (`U19`):
  - Golden Image: `0x000000` (`T20_Golden`, `TAG=T20G`)
  - Custom Application Image: `0x000a6000` (`T20_Custom`, `TAG=T20A`)
  - Merged Bitstream: `FPGA_code/T20_multi_image.hex` via `multi_image_merger.py`
- **Git Commit:** `a2894ef` (`fix(t20,t120): restore 100Hz 50us column-by-column 2T1C gate pulses, sawtooth capacitor refresh, and S-bus SPI flash transceiver`)
- **Files Modified:**
  - `FPGA_code/T20_Golden/T20F256.peri.xml`, `top_level.sv`
  - `FPGA_code/T20_Custom/T20F256.peri.xml`, `top_level.sv`, `t20_hw_responder.sv`
- **Key Engineering Changes:**
  1. **Fixed 36 Gate Lines Floating High (3.3V):** Mapped and actively drove all 36 differential pass-transistor gate pins (`G_P1..6_MAT_3/8/33` and `G_N1..6_MAT_3/8/33`) in both Golden and Custom images, ensuring they initialize to `0 V` (OFF) at reset instead of floating high via Efinix internal pull-ups.
  2. **100 Hz 50 µs Hardware Pulse Engine:** Verified S-bus `CH 0x05, OP 0x4` column pulse sequencing (Phase A: `50 µs` `G_N` pulse at `W-`; Phase B: `50 µs` `G_P` pulse at `W+` per column).
  3. **Oscilloscope Proof:** Observed clean $100\,\text{Hz}$ $50\,\mu\text{s}$ pulses ($0\,\text{V}$ baseline, $3.3\,\text{V}$ peak) and textbook $2.5\,\text{V} \rightarrow 2.1\,\text{V}$ RC sawtooth decay on the $100\,\text{nF}$ gate capacitors.
  4. **S-Bus SPI NOR Flash Transceiver:** Added hardware shift engine on `CH 0x01, OP 0x3` in `t20_hw_responder.sv` allowing T120 to read JEDEC ID, erase, program, and trigger `CONFIG_CTRL0` reconfiguration over S-bus without moving the JTAG cable.

---

### Release 2026-10-11 21:20:00 CEST — T120 Master Firmware v2.0-MAML
- **Date & Local Time:** `2026-10-11 21:20:00 CEST`
- **Target Subsystem:** T120 Master Sapphire RISC-V SoC BRAM
- **Git Commit:** `bb1fc71`
- **Key Engineering Changes:**
  1. Synchronous autonomous 2T1C refresh engine ($100\,\mu\text{s}/\text{column}$, $10.0\,\text{ms}$ full period = $100\,\text{Hz}$).
  2. Fixed 74HC595 R-2R DAC shift timing ($SCK/RCK$ high pulse widened from $20\,\text{ns} \rightarrow 280\,\text{ns}$, $r\_sck\_div = 15$) and added `bitrev8()` for correct $QA = MSB$ mapping.
  3. Fixed XC2361A differential ADC bit alignment ($r\_adc\_bit\_align = 2$, $w[11:0]$).

