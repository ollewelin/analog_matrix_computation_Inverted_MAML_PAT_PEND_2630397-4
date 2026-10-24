# Bitstream & Firmware Archive: 2026-10-24
## Release: T120 MAML Decoupled Timing, Matrix 3/33 Refresh, and Autonomous 100 Hz In-Data

- **Date:** 2026-10-24 10:31 CEST
- **Target Hardware:** Efinix Trion T120F324 Master SoC + Trion T20F256 Coprocessor
- **Operating Mode:** Mode B (`JUMPER_OFF_NO_COMP`, Jumper Mode = 1) verified on silicon
- **Files Archived:**
  - `T120_MALM.bit` (10,651,071 bytes, FPGA bitstream)
  - `T120_MALM.hex` (10,651,071 bytes, SPI flash image)
  - `t120_master.elf` (38,508 bytes, RISC-V SoC firmware ELF)
  - `t120_master.bin` (27,078 bytes, RISC-V BRAM binary)
  - `t120_master.hex` (76,216 bytes, Verilog hex format)
  - `t120_master.asm` (309,957 bytes, Disassembled RISC-V firmware)
  - `t120_master.map` (17,993 bytes, Linker symbol map)

### Key Fixes & Enhancements in this Build:
1. **Decoupled Multiplier Snapshot Delay (`snap_dly_us`):**
   - User has full continuous freedom to select snapshot delay from 0.0 ms to 9.5 ms (`MAML_CMD_PROBE_CELL`).
   - Probe sampling is completely decoupled from Hadamard carrier timing.
   - Preserves active `jumper_mode` in UDP configuration calls (no silent switching to Mode A).
2. **Restored Matrix 3 (`W_M1_ROW1`) 100 Hz Refresh Pulse Train:**
   - Removed artificial `if (g_tel.jumper_mode == JUMPER_OFF_NO_COMP) w = 0;` override from `maml_refresh_all_columns()`.
   - Restored the normal 6-step column update staircase across the 100 Hz refresh on `W_M1_ROW1` (DAC 15) and `W_M2_ROW1` (DAC 12).
3. **Payload Matrix 33 Weight Randomization:**
   - `maml_seed_weights()` now populates `g_w_m33_q14` (DAC 34) in addition to M3 and M8.
4. **Autonomous 100 Hz In-Data Random Pulse Train:**
   - Added `MAML_CMD_RAND_DATA` (0x1A) enabling continuous white-noise updates on `DAC_2` every 10 ms.
5. **Physical Multiplier Output Swing Confirmed:**
   - Peak dynamic range $\pm 600\text{ mV}$ on physical silicon at $t = 2.5\text{--}5.0\text{ ms}$.

