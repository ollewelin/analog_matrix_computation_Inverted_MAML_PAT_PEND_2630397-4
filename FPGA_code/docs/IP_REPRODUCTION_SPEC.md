# Efinix IP Reproduction & Architecture Guide (AI Agent & Developer Guide)

This guide provides precise, automated, and reproducible instructions for AI coding assistants and developers who clone this repository. Following these instructions allows anyone with their own licensed Efinix Efinity toolchain to cleanly regenerate proprietary vendor IP blocks locally, compile the FPGA bitstream, build the firmware, and run the verified 100M Ethernet system without violating Efinix copyright or EULA restrictions.

---

## 1. Architectural Overview

The design is split cleanly into **Vendor Proprietary IP (generated locally)** and **Custom Open RTL (committed to repository)**:

```
+-----------------------------------------------------------------------------------------+
|                                    T120F324 FPGA TOP LEVEL                              |
|                                                                                         |
|  +---------------------------+                     +---------------------------------+  |
|  |     RISC_mini (Sapphire)  |                     |        eth_mac_100m             |  |
|  |  [Regenerated via IPMGR]  |   APB3 Bus (32-bit) |      [Custom Clean RTL]         |  |
|  |                           |<===================>|                                 |  |
|  |  - RISC-V RV32IM CPU      |  Offset: 0xF8102000 |  - 25 MHz SDR TX/RX engines     |  |
|  |  - 128KB OCR On-Chip RAM  |                     |  - Hardware CRC32 + Padding     |  |
|  |  - UART0 (/dev/ttyACM0)   |                     |  - Negedge RX eye sampling      |  |
|  |  - APB3 Master Port       |                     |  - Synchronous pad registers    |  |
|  +---------------------------+                     +---------------------------------+  |
|               |                                                     |                   |
|               | (MDIO bus)                                          | (RGMII 25MHz)     |
|               v                                                     v                   |
|  +---------------------------+                     +---------------------------------+  |
|  |     mdio_master           |                     |          RTL8211F PHY           |  |
|  |     [Custom RTL]          |                     |     (External Ethernet Chip)    |  |
|  +---------------------------+                     +---------------------------------+  |
+-----------------------------------------------------------------------------------------+
```

### Key Components:
1. **`RISC_mini` (Efinix Sapphire RISC-V SoC):**
   - **Type:** Efinix Proprietary IP Core (`efx_soc` v3.3.0).
   - **Legal Status:** Generated locally on the user's workstation using Efinity's IP Manager. Never commit generated `.v`, `.vh`, `.bin`, or devkits to public repositories.
   - **Configuration:** Stored legally and reproducibly in [`FPGA_code/T120F324/ip/RISC_mini/settings.json`](file:///home/olle/AnalogAI/git/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/T120F324/ip/RISC_mini/settings.json).

2. **`eth_mac_100m.sv` (Lightweight 100M APB3 Ethernet MAC):**
   - **Type:** Pure custom SystemVerilog RTL (committed in repo).
   - **Why this instead of `efx_tsemac`:** Efinix's Triple-Speed Ethernet MAC with AXI interconnect produces heavy routing congestion and negative static timing slack ($-0.326\text{ ns}$ to $-3.3\text{ ns}$) on Trion T120. In contrast, `eth_mac_100m.sv` achieves **strictly positive timing slack (+0.689 ns to +36.6 ns)** across all clock domains, passes IEEE 802.3 CRC32 verification with 100% integrity, and answers ping in ~0.3 ms.

3. **`mdio_master.sv` (PHY Management Core):**
   - **Type:** Custom SystemVerilog RTL (committed in repo).
   - **Function:** Manages RTL8211F MDIO/MDC registers (page selection, auto-negotiation, RGMII RX delay).

---

## 2. Efinix Sapphire SoC (`RISC_mini`) Specification

### A. Core Configuration Summary
- **IP Core Name:** `efx_soc`
- **IP Core Version:** `3.3.0`
- **Instance Name:** `RISC_mini`
- **Target Family:** Trion (`T120F324`)
- **CPU:** 32-bit RISC-V RV32IM (Integer + Hardware Multiply/Divide `MULDIV_EXT=1`)
- **System Clock:** 50 MHz (`T120_GCLK`)
- **On-Chip RAM (OCR):** 128 KB (`0x0002_0000` bytes)
- **Caches:** 4 KB Instruction Cache (`ICacheSize=4096`), 4 KB Data Cache (`DCacheSize=4096`)
- **External Memory (DDR):** Disabled (`DDR=0`) — all firmware runs directly from zero-wait-state BRAM
- **Peripherals Included:**
  - **UART0:** 115200 baud, 128-byte FIFO (Console on `/dev/ttyACM0`)
  - **SPI0 / SPI1:** Enabled (8-bit, 256-byte FIFO)
  - **I2C0:** Enabled
  - **GPIO0:** 4-bit width (status and control)
  - **APB3 Slave 0:** Enabled (`APBSlave0=1`, Size: 64 KB, Address: `0xF810_0000`)
    - Sub-allocated in `top_level.sv` to Ethernet MAC (`0xF810_2000`) and Inter-FPGA Bridge (`0xF810_3000`).

### B. Memory Map
| Base Address | Size | Component | Function |
| :--- | :--- | :--- | :--- |
| `0x0000_0000` | 128 KB | Internal BRAM (OCR) | CPU Code & Stack (`main.c`) |
| `0xF800_0000` | 4 KB | UART0 | Console serial IO (`115200 8N1`) |
| `0xF801_0000` | 4 KB | SPI0 | SPI Flash / Peripherals |
| `0xF801_4000` | 4 KB | SPI1 | SPI Bus 1 |
| `0xF802_0000` | 4 KB | I2C0 | I2C Bus |
| `0xF803_0000` | 4 KB | GPIO0 | User Status LEDs & Controls |
| `0xF810_2000` | 4 KB | `eth_mac_100m` | Ethernet MAC Control & Dual BRAM Buffers |
| `0xF810_3000` | 4 KB | `t120_inter_fpga_bridge` | Hardware Matrix Inter-FPGA Bus |

---

## 3. Step-by-Step IP Regeneration for AI Agents & Developers

When cloning this repo on a machine with Efinity installed, follow these exact steps to recreate the vendor IP:

### Option A: Automated CLI Generation (Recommended for Headless / AI Agents)
Efinity stores the full generation parameters in [`FPGA_code/T120F324/ip/RISC_mini/settings.json`](file:///home/olle/AnalogAI/git/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/T120F324/ip/RISC_mini/settings.json).
### Option A: One-Command Automated CLI Generation (Recommended for Headless / AI Agents)
A dedicated reproduction script is provided at [`FPGA_code/scripts/regenerate_efinix_ip.sh`](file:///home/olle/AnalogAI/git/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/scripts/regenerate_efinix_ip.sh). It loads the portable configuration from [`FPGA_code/T120F324/ip/RISC_mini/settings.json`](file:///home/olle/AnalogAI/git/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/T120F324/ip/RISC_mini/settings.json) and runs Efinity's IP Manager backend:

```bash
# 1. Setup Efinity environment variables
source /path/to/efinity/<version>/bin/setup.sh

# 2. Run the automated IP generator script
bash FPGA_code/scripts/regenerate_efinix_ip.sh
```

### Option B: GUI Generation via Efinity IDE
1. Open Efinity IDE: `efinity &`
2. Open project: **File** -> **Open Project** -> select `FPGA_code/T120F324/T120_MALM.xml`.
3. In the **Project Pane**, right-click **IP** and select **Import IP**.
4. Browse to `FPGA_code/T120F324/ip/RISC_mini/settings.json` and click **Open**.
5. When the configuration wizard appears, verify the core name is `RISC_mini` and click **Generate**.
6. The IDE will generate `RISC_mini.v`, `RISC_mini_define.vh`, and template wrappers in `FPGA_code/T120F324/ip/RISC_mini/`.

---

## 4. Building Firmware & Bitstream

Once `RISC_mini.v` is generated locally, the entire build flow is 100% automated:

```bash
# Compile FPGA bitstream (Synthesis, Interface Designer, Place & Route, STA Guard)
bash FPGA_code/scripts/build_t120_fpga.sh

# Compile RISC-V C Firmware and flash to board via JTAG
python3 FPGA_code/scripts/flash_and_listen.py --listen-only --seconds 15

# Test ping from Host PC (interface enp2s0)
ping -c 5 192.168.1.50
```

---

## 5. Git & Copyright Checklist Before Committing

To ensure strict compliance with Efinix EULA and copyright requirements:
- [x] **Committed:** [`settings.json`](file:///home/olle/AnalogAI/git/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/T120F324/ip/RISC_mini/settings.json) (IP configuration metadata).
- [x] **Committed:** [`T120_MALM.xml`](file:///home/olle/AnalogAI/git/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/T120F324/T120_MALM.xml), [`T120_MALM.peri.xml`](file:///home/olle/AnalogAI/git/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/T120F324/T120_MALM.peri.xml), and [`const.sdc`](file:///home/olle/AnalogAI/git/analog_matrix_computation_Inverted_MAML_PAT_PEND_2630397-4/FPGA_code/T120F324/const.sdc).
- [x] **Committed:** All custom RTL (`top_level.sv`, `eth_mac_100m.sv`, `mdio_master.sv`, bridge controllers).
- [x] **Excluded in `.gitignore`:**
  - `**/ip/RISC_mini/RISC_mini.v`
  - `**/ip/RISC_mini/RISC_mini_define.vh`
  - `**/ip/RISC_mini/*_devkit/`
  - `**/ip/RISC_mini/Testbench/`
  - `**/ip/RISC_mini/source/`
  - `**/ip/RISC_mini/ipm/`
  - `**/outflow/` and `**/work_*/`
