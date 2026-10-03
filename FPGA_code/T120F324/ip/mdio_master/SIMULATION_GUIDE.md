# MDIO Master IP - Simulation Guide

## Overview
The MDIO Master IP consists of two complementary files:

- **`mdio_master.sv`** - Core Clause-22 MDIO controller logic (portable, reusable)
- **`mdio_master_top.sv`** - Efinix T120 platform wrapper (handles GPIO tri-state I/O)
- **`tb_mdio_master.sv`** - Standalone testbench for core IP

For simulation, we test **`mdio_master.sv`** directly with the testbench, as it's the core logic.

## Why Two Files? (Architecture Pattern)

This is **industry-standard practice**:

| Component | Purpose | Reusable |
|-----------|---------|----------|
| `mdio_master.sv` | Pure MDIO protocol logic | ✓ Yes (any platform) |
| `mdio_master_top.sv` | Hardware wrapper | ✗ No (Efinix-specific) |

**Benefits:**
- Core logic is platform-agnostic
- Easy to test without hardware constraints
- Can port to different FPGAs by just updating the wrapper
- Follows Xilinx/Altera IP design patterns

---

## Simulation Tools (Open Source)

### Option 1: **iverilog** (Recommended for quick tests)
Lightweight, fast compilation, good for basic verification.

```bash
# Install (if needed)
sudo apt-get install iverilog gtkwave

# Compile and run
iverilog -g2009 -o sim.vvp tb_mdio_master.sv mdio_master.sv
vvp sim.vvp -vcd waveforms.vcd

# View waveforms
gtkwave waveforms.vcd &
```

### Option 2: **Verilator** (Fast, modern, best for large designs)
C++ simulator, very fast for complex designs.

```bash
# Install (if needed)
sudo apt-get install verilator

# Compile with C++ wrapper (see example below)
verilator -sv -trace tb_mdio_master.sv mdio_master.sv --exe tb_wrapper.cpp
make -C obj_dir -f Vmdio_master.mk
./obj_dir/Vmdio_master

# View with gtkwave
gtkwave waveforms.vcd &
```

### Option 3: **GHDL** (If using VHDL components)
For mixed VHDL/Verilog designs.

```bash
ghdl -a --std=08 component.vhd
ghdl -a --std=08 tb_component.vhd
ghdl -e tb_component
ghdl -r tb_component --vcd=waveforms.vcd
gtkwave waveforms.vcd &
```

---

## Quick Start: Running Simulation with iverilog

### Step 1: Run the Testbench
```bash
cd /home/olle/efinity_p2/BRAM/T120F324_A/ip/mdio_master/

# Compile
iverilog -g2009 -o mdio_sim.vvp tb_mdio_master.sv mdio_master.sv

# Run with waveform output
vvp mdio_sim.vvp -vcd waveforms.vcd

# View results
gtkwave waveforms.vcd &
```

### Step 2: Examine Waveforms
The `.vcd` file (Value Change Dump) shows:
- Clock, reset, APB signals
- MDC clock generation
- MDIO protocol exchanges
- Status/control register updates

---

## What the Testbench Verifies

The `tb_mdio_master.sv` currently tests:

✓ **Clock generation** - 50 MHz system clock  
✓ **Reset behavior** - Active-low reset assertion/release  
✓ **APB interface** - Register read/write access  
✓ **MDC generation** - Proper clock divider operation  
✓ **MDIO bus model** - Simulated PHY responds to reads  
✓ **Frame detection** - Proper Clause-22 frame structure  

---

## How to Extend the Testbench

Add new test cases in `tb_mdio_master.sv`:

```systemverilog
// Example: Test a register write
initial begin
    @(posedge clk);
    // Write operation: PHY addr=1, Reg addr=2, Data=0xABCD
    apb_write(4'h0, {16'hABCD, 5'd2, 5'd1, 1'b0, 4'h1});  // CTRL
    wait_done();
    check_mdio_frame("Write to REG[2]");
end

task apb_write(input [3:0] addr, input [31:0] data);
    psel = 1;
    penable = 0;
    pwrite = 1;
    paddr = addr;
    pwdata = data;
    @(posedge clk);
    penable = 1;
    @(posedge clk);
    psel = 0;
    penable = 0;
endtask
```

---

## Debugging Tips

1. **Add $display() statements** in testbench to track state:
   ```systemverilog
   $display("APB Write: addr=%h, data=%h, time=%0t", paddr, pwdata, $time);
   ```

2. **Monitor MDIO bus** in waveforms:
   - Rising edge of MDC = data change
   - MDIO_OE = master driving
   - Look for START, OPCODE, PHY_ADDR, REG_ADDR, TA, DATA

3. **Use assertions** for protocol compliance:
   ```systemverilog
   always @(posedge mdc)
       assert(mdio_oe | ~mdio_o) else $error("Invalid MDIO state");
   ```

---

## Files Organization

```
mdio_master/
├── mdio_master.sv          ← Core logic (tested)
├── mdio_master_top.sv      ← Efinix wrapper (for synthesis)
├── tb_mdio_master.sv       ← Testbench
├── SIMULATION_GUIDE.md     ← This file
├── run_sim.sh              ← Automation script (optional)
└── waveforms.vcd           ← Generated waveform output
```

---

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| `tb_mdio_master.sv not found` | Ensure you're in the correct directory |
| `Undefined module mdio_master` | Add `mdio_master.sv` to compile list |
| No VCD output | Add `-vcd` flag to `vvp` command |
| GTKWave won't open | Install: `sudo apt-get install gtkwave` |
| Testbench hangs | Check for infinite `@(posedge mdc)` loops |

---

## Next Steps

1. **Run the existing testbench** to verify basic operation
2. **Add test cases** for specific MDIO operations (read/write specific registers)
3. **Create a mixed testbench** that instantiates `mdio_master_top.sv` to verify GPIO wrapper
4. **Generate coverage reports** (with Verilator/commercial tools)
5. **Compare against RTL8211F datasheet** MDIO traces

---

## References

- **Clause-22 MDIO Spec:** IEEE 802.3 Section 22
- **RTL8211F Datasheet:** PHY register definitions and timing
- **iverilog Docs:** http://iverilog.icarus.org/
- **Verilator Docs:** https://verilator.org/
