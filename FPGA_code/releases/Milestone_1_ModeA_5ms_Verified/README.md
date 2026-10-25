# Milestone 1: Mode A (5.0 ms) Physical Inner-Loop Baseline Release
**Timestamp:** 2026-10-24 / 2026-10-25  
**Platform:** Efinix Trion T120F324 (Master) + Trion T20F256 (Controller)  
**Hardware Address:** `192.168.1.50:5000`  
**Status:** Physically Verified & Latched (Milestone 1 Complete)

---

## 1. Overview & Purpose
This directory contains a complete, self-contained reference snapshot ("time-stamp") of both the FPGA RTL and the Sapphire RISC-V C software corresponding to the successful completion of **Milestone 1**.

This release serves as the official immutable baseline against which future firmware, RTL expansions (e.g., Milestone 2 broadened timing window $4.0 - 6.0\text{ ms}$), and hardware tuning can be directly diffed and compared.

---

## 2. Directory Structure
```
Milestone_1_ModeA_5ms_Verified/
├── .gitignore          # Ignores all Efinity work dirs, netlists, and compiler temporaries
├── README.md           # This release documentation
├── T120F324/           # Master FPGA (T120) RTL, SDC constraints, and project XML
│   ├── top_level.sv
│   ├── t120_analog_io_ctrl.sv
│   ├── t120_inter_fpga_bridge.sv
│   ├── t120_hbus_seq.sv
│   ├── eth_mac_100m.sv
│   ├── T120_MALM.xml
│   └── const.sdc
├── T20F256/            # Controller FPGA (T20) RTL and project XML
│   ├── top_level.sv
│   ├── t20_hw_responder.sv
│   ├── t20_sbus_rx.sv / tx.sv
│   ├── T20F256.xml
│   └── const.sdc
├── sw/t120_master/     # Sapphire RISC-V SoC Embedded C Firmware
│   ├── src/            # main.c, maml_platform.c, eth_mac_100m.c, etc.
│   ├── include/        # Register maps, bus definitions, protocol headers
│   └── Makefile        # RISC-V cross-compilation makefile
└── bitstreams/         # Verified flashable bitstreams & software hex
    ├── T120_MALM.hex   # Master FPGA bitstream (Flash format)
    ├── T120_MALM.bit   # Master FPGA bitstream (JTAG format)
    ├── t120_master.hex # Sapphire RISC-V firmware hex (offset 0x00380000)
    └── t120_master.bin # Raw binary firmware image
```

---

## 3. Verified Milestone 1 Performance Metrics
Across three rigorous, independent hardware verification runs on physical silicon:

| Metric | Run 1 | Run 2 | Run 3 | Target / Baseline |
| :--- | :--- | :--- | :--- | :--- |
| **Operating Delay ($t_{delay}$)** | 5.0 ms | 5.0 ms | 5.0 ms | Settled linear regime (100 Hz refresh) |
| **Initial RMSE (LSB)** | 54.38 LSB | 45.21 LSB | 46.61 LSB | Step 0 uncompensated raw analog response |
| **Best Converged RMSE** | **10.40 LSB** | **14.81 LSB** | **14.85 LSB** | Step 8 to 18 inner-loop convergence |
| **Loss Reduction** | **$-96.3\%$** | **$-89.3\%$** | **$-89.9\%$** | Quadratic loss $L = \frac{1}{2}\sum \mathrm{Err}_j^2$ |
| **Uncompensated ENOB** | 5.23 bits | 5.50 bits | 5.46 bits | Rå hårdvaruprecision före MAML |
| **Compensated ENOB** | **7.62 bits** | **7.11 bits** | **7.11 bits** | **$>7.0\text{ bits}$ patent claim exceeded** |
| **Attenuator Ratio** | 0.2041× | 0.2041× | 0.2041× | $R_{in}/(R_{in}+R_s) = 1.0\text{ k}\Omega / (1.0+3.9\text{ k}\Omega)$ |
| **Convergence Speed** | 80 ms | 80 ms | 140 ms | 8 to 14 iterations @ 100 Hz |

---

## 4. How to Compare Future Firmware / RTL Against This Timestamp

### Comparing FPGA RTL (T120):
```bash
diff -ruN FPGA_code/releases/Milestone_1_ModeA_5ms_Verified/T120F324/ FPGA_code/T120F324/
```

### Comparing Sapphire RISC-V Software:
```bash
diff -ruN FPGA_code/releases/Milestone_1_ModeA_5ms_Verified/sw/t120_master/src/ FPGA_code/sw/t120_master/src/
```

### Comparing Bitstream Checksums:
```bash
md5sum FPGA_code/releases/Milestone_1_ModeA_5ms_Verified/bitstreams/*
```
*(Bitstream MD5s: `T120_MALM.hex` and `t120_master.hex` match the physical flash latched on 2026-10-24).*

