# T120 MAML FPGA Bitstream & Hex Archive: Knee Baseline Milestone (7.90 b ENOB)

- **Date:** 2026-10-29 20:28 CET
- **Target Silicon:** Efinix Trion T120F324 Master SoC (`192.168.1.50:5000`)
- **Carrier Board:** PCB v1.3.2 (Summing attenuator: $1\text{ k}\Omega / 5.1\text{ k}\Omega$ installed)
- **Controller FPGA:** Efinix Trion T20F256
- **Patent Application:** SE 2630397-4 (Open Science Hardware)

## Contents
- `T120_MALM.bit` (10,651,071 bytes): JTAG programming bitstream
- `T120_MALM.hex` (10,651,071 bytes): SPI flash programming hex file

## Provenance & Performance Milestone
This bitstream corresponds to the milestone achieved during the 3-stage 500-epoch benchmark on October 29, 2026:
- Zero digital seeding (`seed_pct = 0`)
- LEDs ON (`led_switches = 3`)
- Snapshot delay: $t = 5.0\text{ ms}$
- Optimal S-curve knee baseline $\mathbf{W}_{\text{baseline}} = [-16, -16, +16, +16, -16, +16]\text{ LSB}$ on both $M_3$ and $M_8$
- Verified peak ENOB: **$7.90\text{ bits}$** ($221.1\text{ LSB}^2$ loss, RMSE $8.59\text{ LSB}$) at Epoch 427.

Use this archived bitstream whenever rolling back to the verified October 29, 2026 milestone.

