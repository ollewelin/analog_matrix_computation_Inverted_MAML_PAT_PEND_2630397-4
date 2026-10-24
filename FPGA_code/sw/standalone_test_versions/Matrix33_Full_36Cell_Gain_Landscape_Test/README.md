# Matrix 33 Full 36-Cell Gain Landscape — Standalone Test Suite

**Directory:** `FPGA_code/sw/standalone_test_versions/Matrix33_Full_36Cell_Gain_Landscape_Test/`  
**Date:** 2026-10-24  
**Hardware Mode:** Mode B (Jumper Mode 1 — Pure Uncompensated Raw Matrix 33)  
**Git Commit:** `094eea7`  

---

## Overview

This standalone directory freezes the complete software environment, firmware source, compiled binaries, and test automation scripts used to map and characterize the **full $6\times 6$ analog multiplier gain landscape (all 36 crosspoints)** of Matrix 33 on the Trion T120 Master SoC.

---

## Directory Structure

```
Matrix33_Full_36Cell_Gain_Landscape_Test/
├── FPGA_LOGIC_VERSION_LINK.txt   # Explicit links, file paths & MD5 hashes to bitstreams & binaries
├── README.md                     # This documentation
├── Makefile                      # Firmware build Makefile (RISC-V GCC)
├── cpu0.yaml                     # Efinix Sapphire SoC core configuration
├── bin/                          # Pre-compiled RISC-V firmware binaries
│   ├── t120_master.bin           # Raw binary image for flash/RAM
│   ├── t120_master.hex           # Intel HEX format for memory loader
│   ├── t120_master.elf           # ELF binary with symbols
│   ├── t120_master.map           # Memory link map
│   └── t120_master.asm           # Disassembly listing
├── src/                          # Complete C firmware source code
│   ├── maml_platform.c           # Single-cell probe, decoupled snapshot timing, ADC readout
│   ├── main.c                    # Sapphire SoC boot and main loop
│   └── ...
├── bsp/                          # Board Support Package headers and runtime
├── include/                      # Hardware register definitions and constants
└── scripts/                      # Sweep, plotting, and PDF generation scripts
    ├── map_matrix33_full_landscape.py
    ├── plot_matrix33_full_landscape.py
    ├── generate_matrix33_landscape_report_pdf.py
    ├── run_cell_0_0_comprehensive_sweep.py
    ├── plot_comprehensive_cell_0_0_report.py
    └── generate_cell_0_0_comprehensive_report_pdf.py
```

---

## Bitstream Link

The hardware FPGA bitstream matching this software is located at:
- **Bitstream Archive:** [`FPGA_code/bitstreams_archive/20261024_T120_MAML_DecoupledTiming_M3_M33_Alive/`](../../bitstreams_archive/20261024_T120_MAML_DecoupledTiming_M3_M33_Alive/)
  - `T120_MALM.bit` (MD5: `3f7be1a6089bfe26211f77f84768ad44`)
  - `T120_MALM.hex` (MD5: `05f2e3f3a96c1588139bfbcf5416b27d`)

---

## Running the Automated Test

From the repository root:
```bash
# Fast 36-cell sweep across all crosspoints (~48 s)
python3 FPGA_code/sw/standalone_test_versions/Matrix33_Full_36Cell_Gain_Landscape_Test/scripts/map_matrix33_full_landscape.py --mode fast

# Generate 3D topography and 36-cell grid figures
python3 FPGA_code/sw/standalone_test_versions/Matrix33_Full_36Cell_Gain_Landscape_Test/scripts/plot_matrix33_full_landscape.py

# Generate PDF report
python3 FPGA_code/sw/standalone_test_versions/Matrix33_Full_36Cell_Gain_Landscape_Test/scripts/generate_matrix33_landscape_report_pdf.py
```

