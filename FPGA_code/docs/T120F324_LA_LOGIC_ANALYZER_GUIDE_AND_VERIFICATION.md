# T120F324_LA Bare-Metal Efinix Logic Analyzer Build, User Guide & Live Carrier Verification

- **Project Folder**: `FPGA_code/T120F324_LA` (keeps `FPGA_code/T120F324` untouched)
- **Logic Analyzer Core**: `edb_top` (`la0` on `JTAG_USER1`)
- **Hardware UUID**: `29024bad0ef545319a42750d2a504819` (**VERIFIED** on live hardware)
- **Recorder Depth & Width**: `2048` samples x `86` bits (`23` probes, `capture_control = true`)
- **Resource Usage**: `60,130 / 112,128` Logic Elements (`53.63%`), `339 / 1,056` Memory Blocks (`32.10%`)
- **Timing (STA)**: `T120_GCLK` (`50 MHz`) `+0.591 ns` setup slack (`51.52 MHz` Fmax); `jtag_inst1_TCK` (`10 MHz`) `+73.087 ns` setup slack.

## 1. Commands to Program & Launch Efinix Debugger
```bash
# Program T120F324_LA bitstream via JTAG:
python3 FPGA_code/scripts/program_t120.py FPGA_code/T120F324_LA/outflow/T120_MALM.bit

# Launch Efinix Debugger GUI and load FPGA_code/T120F324_LA/debug_profile.json:
source /home/olle/efinix2/efinity-2025.2.288.2.10-linux-x64/efinity/2025.2/bin/setup.sh
/home/olle/efinix2/efinity-2025.2.288.2.10-linux-x64/efinity/2025.2/bin/efinity_dbg.sh

# Or capture all 6 bare-metal VCD traces automatically via CLI:
python3 FPGA_code/scripts/capture_t120_la_traces.py
```

## 2. Summary of the 6 Live Efinix Logic Analyzer Captures
| Trace File (`FPGA_code/T120F324_LA/outflow/`) | Capture Enable | `hadamard_on_n_off` | `adc45_ch1_raw` (`M3+`) | `adc45_ch2_raw` (`M3-`) | `adc49_ch2_raw` (`M8`) |
| :--- | :--- | :---: | :--- | :--- | :--- |
| `Trace 2: Hadamard OFF (0x8000)` | 10 MHz (204.8 us) | `[0]` | `2311..2319 (8 LSB)` | `2367..2374 (7 LSB)` | `444..448 (4 LSB)` |
| `Trace 1: Hadamard ON Pat A (+W)` | 10 MHz (204.8 us) | `[0, 1]` | `2257..2361 (104 LSB)` | `2339..2421 (82 LSB)` | `444..448 (4 LSB)` |
| `Trace 6: Hadamard ON Pat B (-W)` | 10 MHz (204.8 us) | `[0, 1]` | `1792..1840 (48 LSB)` | `1830..1907 (77 LSB)` | `460..482 (22 LSB)` |
| `Trace 3: Hadamard ON Pat A (+W)` | 2 MHz (1.024 ms) | `[0, 1]` | `2259..2360 (101 LSB)` | `2343..2424 (81 LSB)` | `444..448 (4 LSB)` |
| `Trace 4: Hadamard ON Pat A (+W)` | 500 kHz (4.096 ms) | `[0, 1]` | `2251..2371 (120 LSB)` | `2331..2427 (96 LSB)` | `444..448 (4 LSB)` |
| `Trace 5: Full 50 MHz SPI Timing` | Always 50 MHz (41 us) | `[0, 1]` | `2265..2318 (53 LSB)` | `2339..2396 (57 LSB)` | `444..448 (4 LSB)` |
