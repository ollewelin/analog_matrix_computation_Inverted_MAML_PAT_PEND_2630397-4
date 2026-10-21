# Bitstream Archive: 20261021_T120F324_LA_ContinuousADC

- **Date:** 2026-10-21
- **Target FPGA:** Efinix Trion T120F324 (Package: F324, Speed: C4)
- **Top Level:** `top_level.sv` from `FPGA_code/T120F324_LA_ContinuousADC`
- **Bitstream:** `T120_MALM.bit` (SRAM configuration via JTAG / SPI)
- **Flash Hex:** `T120_MALM.hex` (SPI Active Flash boot image)
- **ILA Debug Profile:** `debug_profile.json` (for Efinity Debugger / OpenOCD)

## Key Features & Modifications
1. **Continuous 500 kHz ADC Sampling:** Hardware ADCs (XC2361A / MCP33141) run continuous synchronous sampling at 500 kHz across all conditions regardless of GUI test mode, enabling non-stop logic analyzer observation without needing software re-triggering.
2. **24 µs Hadamard Burst Support:** Fully wired and timed 24 µs Hadamard carrier generation across all 12 pulse slots.
3. **Hardware In-System Logic Analyzer (ILA):** Integrated Efinix Logic Analyzer core probing ADC SPI buses (`ADC_45`, `ADC_49`), Hadamard triggers, and row/column multiplexer states.

