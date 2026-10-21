# MDIO Master IP - Quick Simulation Start

## ✅ Simulation Ready!

Your MDIO Master IP is configured for immediate simulation testing.

---

## Quick Start (2 minutes)

### Option A: Automated Script (Easiest)
```bash
cd /home/olle/efinity_p2/BRAM/T120F324_A/ip/mdio_master

# Run simulation and view waveforms
./run_sim.sh --view

# View just waveforms (after first run)
gtkwave sim/waveforms.vcd &
```

### Option B: Manual Commands
```bash
cd /home/olle/efinity_p2/BRAM/T120F324_A/ip/mdio_master

# Compile
iverilog -g2009 -o sim/mdio_sim.vvp tb_mdio_master.sv mdio_master.sv

# Run with waveform capture
cd sim && vvp mdio_sim.vvp -vcd waveforms.vcd

# View waveforms
gtkwave waveforms.vcd &
```

---

## What Gets Tested ✓

The current testbench (`tb_mdio_master.sv`) runs two core tests:

**Test 1: Write Operation**
- PHY Address: `0x01`
- Register Address: `0x00`
- Write Data: `0x1234`
- Verifies APB write → MDC clock generation → MDIO frame transmission

**Test 2: Read Operation**
- PHY Address: `0x01`
- Register Address: `0x02`
- Reads data from PHY simulation model
- Verifies complete Clause-22 MDIO protocol frame

---

## Understanding Architecture (2 Files)

```
┌─────────────────────────────────────┐
│  Your FPGA Design (Efinix T120)    │
│  - Sapphire SoC (RISC-V)           │
│  - GPIO: F2_MDC, F2_MDIO, F2_RSTB  │
└────────────┬────────────────────────┘
             │
    ┌────────▼──────────────┐
    │  mdio_master_top.sv   │  ← For Synthesis/Implementation
    │  (Platform wrapper)   │     Handles Efinix-specific I/O
    └────────┬──────────────┘
             │
    ┌────────▼──────────────────────┐
    │  mdio_master.sv               │  ← Core IP (Portable)
    │  (Clause-22 MDIO Protocol)    │     Reusable across platforms
    │  - APB interface              │
    │  - Clock divider              │
    │  - MDIO frame generation      │
    └────────────────────────────────┘
             │
    ┌────────▼──────────────────────┐
    │  tb_mdio_master.sv            │  ← For Simulation
    │  (Testbench - SIMULATION ONLY) │     Tests core logic
    │  - Generates clocks           │
    │  - PHY simulation model       │
    │  - Test cases                 │
    └────────────────────────────────┘
```

**Summary:**
- **`mdio_master.sv`** = Pure logic (100% reusable)
- **`mdio_master_top.sv`** = Efinix wrapper (platform-specific)
- **`tb_mdio_master.sv`** = Simulation only (not synthesized)

This is **industry-standard**, used by Xilinx, Altera, Mentor, etc.

---

## Waveform Analysis

After running simulation, open `sim/waveforms.vcd` in GTKWave to view:

### Clock Signals
- `clk` - 50 MHz system clock
- `mdc` - Generated MDIO Management Clock (~2.5 MHz in simulation)

### APB Interface (Control)
- `psel`, `penable`, `pwrite` - APB protocol
- `paddr` - Register address
- `pwdata` - Write data
- `prdata` - Read data response
- `pready` - Transaction complete

### MDIO Protocol
- `mdio_o` - MDIO master drives low (0)
- `mdio_oe` - Output enable (when master drives)
- `mdio_i` - MDIO bus line (includes PHY response)

### Status
- `busy` - Operation in progress
- `done` - Transaction complete (sticky)

---

## Common Waveform Patterns

### Write Transaction Sequence
```
1. psel=1, pwrite=1  → APB setup phase
2. penable=1        → APB enable (sample data)
3. busy goes high   → MDIO protocol starts
4. mdc oscillates   → MDC clock generation
5. mdio_oe toggles  → MDIO frame transmission
6. done goes high   → Write complete
```

### Read Transaction Sequence
```
1. psel=1, pwrite=0  → APB setup (read mode)
2. penable=1         → APB enable
3. mdc oscillates    → MDC generation
4. mdio_oe toggles   → Master transmits frame
5. prdata updates    → PHY response captured
6. done goes high    → Read complete
```

---

## Next: Writing Custom Tests

Edit `tb_mdio_master.sv` to add test cases:

```systemverilog
// Example: Add to initial block
initial begin
    wait(rst_n);  // Wait for reset release
    @(posedge clk);
    
    // Test: Read Status Register (Register 1) from PHY address 0
    write_control(32'h0000_0001);  // PHY_ADDR=0, REG_ADDR=1, READ
    wait_done();
    
    $display("Status Register Value: 0x%04X", dut.prdata[15:0]);
    
    if (dut.prdata[15:0] == 16'h7800)
        $display("✓ PHY detected and responding");
    else
        $display("✗ Unexpected PHY response");
end
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `sim/mdio_sim.vvp: No such file or directory` | Run: `mkdir -p sim` first |
| GTKWave won't open | Install: `sudo apt-get install gtkwave` |
| No output in testbench | Check `$display()` statements - iverilog shows them on terminal |
| Simulation hangs | Check for infinite loops in `wait_done()` task |
| Waveforms not generated | Use `-vcd` flag with `vvp` command |

---

## Tools Installed on Your System

✅ **iverilog** - Compile SystemVerilog/Verilog  
✅ **gtkwave** - View `.vcd` waveforms  
✓ **Verilator** - (Optional) C++ simulator for faster runs  

---

## Files in This Directory

```
mdio_master/
├── mdio_master.sv              ← Core IP logic (portable)
├── mdio_master_top.sv          ← Efinix wrapper (for synthesis)
├── tb_mdio_master.sv           ← Testbench (simulation only)
├── SIMULATION_GUIDE.md         ← Detailed reference guide
├── QUICKSTART.md               ← This file
├── run_sim.sh                  ← Automated simulation script
└── sim/                        ← Generated outputs
    ├── mdio_sim.vvp            ← Compiled simulation
    └── waveforms.vcd           ← Waveform dump (GTKWave)
```

---

## Typical Workflow

```bash
# 1. Edit testbench to add new tests
vim tb_mdio_master.sv

# 2. Run simulation
./run_sim.sh

# 3. View waveforms
gtkwave sim/waveforms.vcd &

# 4. Review output messages in terminal
# Look for $display() messages in testbench

# 5. Repeat for different test scenarios
```

---

## Next Steps

1. ✅ **Run the basic simulation** - See what's already there
2. 📊 **Examine waveforms** - Understand the MDIO protocol in action
3. ✏️ **Add test cases** - Write tests for specific RTL8211F registers
4. 🔍 **Debug failures** - Use `$display()` and waveforms to troubleshoot
5. 📦 **Use mdio_master_top.sv** in your top-level design for synthesis

---

## Reference Documents

- [SIMULATION_GUIDE.md](SIMULATION_GUIDE.md) - Comprehensive testing guide
- [README.md](README.md) - API documentation
- RTL8211F Datasheet - Register definitions and timing

---

**Status:** ✅ Ready to simulate  
**Command:** `./run_sim.sh --view`
