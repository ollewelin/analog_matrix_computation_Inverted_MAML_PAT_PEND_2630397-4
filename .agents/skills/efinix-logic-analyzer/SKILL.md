---
name: efinix-logic-analyzer
description: Guide and runbook for the Efinix JTAG In-System Logic Analyzer (ILA) on the Trion T120. Details tool mutual exclusion with OpenOCD, resource budgeting (sample depth and probe limits), and when to choose Logic Analyzer over testbenches or OpenOCD.
---

# Efinix In-System Logic Analyzer (ILA) Guide & Runbook (Trion T120)

This skill documents how to configure, insert, and debug using the **Efinix In-System Logic Analyzer (ILA)** on the **Trion T120F324** FPGA, including tool mutual exclusion rules, FPGA resource trade-offs, and triage workflows.

---

## 1. Tool Role & When to Use

Understanding which debug tool to reach for saves hours of development time:

| Tool | Target Domain | Best Used For | Turnaround Speed |
| :--- | :--- | :--- | :--- |
| **OpenOCD / GDB SoC Debugger** | Software / Firmware inside RISC-V | C/C++ control flow, register values (`mepc`, `mcause`, `sp`), memory dumps, peripheral APB registers. | **~3 seconds** (BRAM update flow) |
| **Logic Simulation / Testbench** | Pure HDL logic & unit blocks | Protocol state machines, AXI/APB bus arbitration, FIFOs, before running on hardware. | **Fast** (seconds in Icarus / Verilator) |
| **Efinix Logic Analyzer (ILA)** | **Real Hardware $\leftrightarrow$ Logic interaction** | Physical pin transitions (RGMII, MDIO, SPI), external PHY timing glitches, PLL clock domain crossing, asynchronous reset timing, unknown hardware faults. | **Slow (~11 minutes)** (Requires full Place & Route) |

> [!TIP]
> **Guideline**: Use the Logic Analyzer only when you are genuinely stuck on physical hardware interface behavior or unexplained timing glitches at the boundary between FPGA logic and external chips. If the issue is inside the RISC-V firmware, use OpenOCD and the 3-second BRAM update method instead.

---

## 2. STRICT RULE: Mutual Exclusion with OpenOCD

> [!CAUTION]
> **NEVER run the Efinix Logic Analyzer and OpenOCD simultaneously!**
> 
> Both tools communicate through the **same physical FTDI FT2232H USB-to-JTAG chip** (Device ID: `0x00220A79`, VID: `0x0403`, PID: `0x6010`).
> Attempting to run both concurrently causes USB interface contention, corrupted JTAG shift registers, and drops the connection.

### Switching Rules:
1. **Before launching OpenOCD**:
   - Ensure any running Efinix Debugger / Logic Analyzer GUI (`efinity_dbg.sh`) is closed or killed.
2. **Before launching Efinix Logic Analyzer**:
   - Terminate any running OpenOCD background daemon:
     ```bash
     killall openocd 2>/dev/null || true
     ```

---

## 3. Resource Budgeting: Keeping Sample Depth & Trace Counts Low

The Efinix Logic Analyzer IP consumes **on-chip Block RAM (BRAM / M10K)** and logic elements inside the Trion T120:
- The Sapphire SoC with 128 KB cache/ram already uses a significant portion of T120 BRAMs.
- Adding a high sample depth (e.g. 16K or 64K samples) or too many probed signals will cause **BRAM overflow** or routing congestion.

### Recommended Budgeting Guidelines:
- **Sample Depth**: Keep depth reasonably low — typically **512 to 2048 samples** is more than enough to capture transient protocol transactions (e.g., MDIO frames, RGMII packet preambles, or SPI transactions).
- **Probed Traces**: Restrict probe inputs to the specific signals of interest (e.g., `mdio_mdc`, `mdio_mdo`, `mdio_mdo_en`, `mdio_mdi`, `phy_rst_n`, state bits). Avoid probing wide 32-bit internal buses unless strictly necessary.
- **Trigger Conditions**: Use simple single-stage or 2-stage edge/level triggers (e.g. trigger on falling edge of `phy_rst_n` or rising edge of `mdio_start`).

---

## 4. Workflow to Add and Run the Logic Analyzer

When you determine that physical signal analysis is needed:

### Step 1: Insert Logic Analyzer IP Core
1. In the Efinity project (`FPGA_code/T120F324/T120_MALM.xml`), open IP Manager or Debug Core Manager.
2. Add the **Debug Core / Logic Analyzer**.
3. Select the sampling clock (must be a free-running clock, e.g. `sys_clk` 50 MHz or `eth_gtx_clk` 125 MHz depending on the domain being probed).
4. Assign probe nets to target signals.
5. Set sample depth to **1024 samples**.

### Step 2: Full Synthesis & Place-and-Route
Because logic and routing are added, a full compile is required:
```bash
cd FPGA_code/T120F324
/home/olle/efinix2/efinity-2025.2.288.2.10-linux-x64/efinity/2025.2/bin/efx_run --project T120_MALM.xml --flow compile
```

### Step 3: Flash the Instrumented Bitstream
```bash
python3 FPGA_code/scripts/program_t120.py
```

### Step 4: Run the Analyzer GUI
Ensure OpenOCD is stopped, then launch the debugger:
```bash
/home/olle/efinix2/efinity-2025.2.288.2.10-linux-x64/efinity/2025.2/bin/efinity_dbg.sh &
```
Arm the trigger, capture the event, and inspect waveforms.

---

## 5. Summary Checklist Before Using
- [ ] Is OpenOCD stopped?
- [ ] Is sample depth set to $\le 2048$?
- [ ] Are probe traces kept minimal (only signals under investigation)?
- [ ] Could this bug be triaged faster with OpenOCD memory/register reads? If yes, use `openocd-sapphire-debug`.
