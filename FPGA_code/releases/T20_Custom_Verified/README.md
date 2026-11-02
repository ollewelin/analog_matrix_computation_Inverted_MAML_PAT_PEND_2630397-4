# Verified T20 Custom Bitstream Release (2026-11-02)

## Bitstream Metadata
- **FPGA Device:** Efinix Trion T20F256
- **Source Project:** `FPGA_code/T20_Custom`
- **Build Date:** 2026-10-12 21:04
- **Verification Date on Silicon:** 2026-11-02 (PCB Rev 2.0 with 1k / 3.9k attenuator)
- **Status in UDP Telemetry:** `Status: T20 ONLINE [TAG=T20A, S-bus ACK 0x06]`
- **Binary Size:** 678,650 Bytes (`0xA5AFA`)
- **Hex File Size:** 2,035,950 Bytes
- **Pins Configured:** 89 GPIOs (All 36 Dual-2T1C gate lines, tristate OE for Hadamard drivers, S-bus transceiver, status LEDs)

## Files
- `T20F256.hex`: Intel hex-format ASCII file for Efinity Programmer (`SPI Active using JTAG Bridge`).
- `T20F256.bit`: JTAG direct programming file.
- `T20F256.bin`: Pure binary image (678,650 bytes) for raw SPI flash programming or embedded bootloaders.

## Verification
- S-bus Acknowledged with opcode `0x06`.
- Hadamard modulation active with zero missing acknowledgments (`t20_h_ack_miss=0`).
- Analog gate lines actively modulating ADC_45 and ADC_49 across M3, M8, and M33 matrices.

