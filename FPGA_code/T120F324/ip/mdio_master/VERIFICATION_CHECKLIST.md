# MDIO Master IP - Verification Checklist

## Pre-Simulation Checklist

- [ ] All required files present in `/home/olle/efinity_p2/BRAM/T120F324_A/ip/mdio_master/`
  - [ ] `mdio_master.sv`
  - [ ] `mdio_master_top.sv`
  - [ ] `tb_mdio_master.sv`
  - [ ] `run_sim.sh` (optional - for convenience)

- [ ] iverilog installed
  ```bash
  which iverilog  # Should show /usr/bin/iverilog
  ```

- [ ] gtkwave installed (optional but recommended)
  ```bash
  which gtkwave   # Should show /usr/local/bin/gtkwave or similar
  ```

---

## Run Simulation

### Step 1: Navigate to IP directory
```bash
cd /home/olle/efinity_p2/BRAM/T120F324_A/ip/mdio_master
```
- [ ] Directory exists and contains the files

### Step 2: Create sim output directory
```bash
mkdir -p sim
```
- [ ] `sim/` directory created

### Step 3: Compile with iverilog
```bash
iverilog -g2009 -o sim/mdio_sim.vvp tb_mdio_master.sv mdio_master.sv
```

✅ **Expected output:**
```
Note: ... warning about task definition ...  [OK - harmless]
[No error messages - compilation successful]
```

- [ ] No compilation errors
- [ ] `sim/mdio_sim.vvp` file created (size ~30KB)

### Step 4: Run simulation
```bash
cd sim && vvp mdio_sim.vvp -vcd waveforms.vcd
```

✅ **Expected output:**
```
=== MDIO Master Testbench ===
SYS_CLK_HZ = 50000000, MDC_HZ = 2500000
VCD info: dumpfile tb_mdio_master.vcd opened for output.
[450000] Version = 0x00000100 (v1.0)
[450000] Releasing PHY reset...
[2510000] Test 1: Write PHY_ADDR=0x01, REG_ADDR=0x00, DATA=0x1234
[2630000] Write complete
[3690000] Test 2: Read PHY_ADDR=0x01, REG_ADDR=0x02
[28470000] Read complete, DATA=0xffff
=== Test Complete ===
```

- [ ] All test messages printed
- [ ] No error messages
- [ ] `waveforms.vcd` file created (size ~64KB)

### Step 5: View waveforms (optional)
```bash
gtkwave waveforms.vcd &
```

- [ ] GTKWave window opens
- [ ] Waveforms display correctly
- [ ] Can zoom/pan/scroll waveforms

---

## Verify Functionality

### Check APB Interface
In GTKWave, look for these signals:
- [ ] `psel` - APB select (goes high during transfers)
- [ ] `penable` - APB enable (pulse high for one cycle)
- [ ] `pwrite` - Write/Read mode selector
- [ ] `paddr` - Address bus (0-3 for 4 registers)
- [ ] `pwdata` - Data to write
- [ ] `prdata` - Data read back
- [ ] `pready` - Ready signal (should pulse after operation)

### Check MDC Clock Generation
- [ ] `mdc` signal visible
- [ ] Frequency is approximately 2.5 MHz (in simulation)
- [ ] Divider working correctly from 50 MHz system clock
- [ ] Ratio approximately 20:1 (50M / 2.5M)

### Check MDIO Protocol
- [ ] `mdio_oe` - Output enable toggles during transmission
- [ ] `mdio_o` - Master output data changes with protocol
- [ ] `mdio_i` - Bus state reflects master + PHY
- [ ] Both transitions occur on `mdc` edges

### Check Status Register
- [ ] `busy` flag goes high at start of operation
- [ ] `busy` flag goes low when complete
- [ ] `done` flag pulses at end
- [ ] `prdata` contains response data

---

## Interpret Test Results

### Test 1: Write Operation (Expected ~1ms)
```
[2510000 ns] Test 1 starts
    → APB interface sets up write command
    → mdio_master generates MDC clock
    → MDIO frame transmitted (64 bits for write)
    → Contains: START, OPCODE(01=write), PHY_ADDR(0x01), REG_ADDR(0x00), TA, DATA(0x1234)
[2630000 ns] Test 1 completes
    → done flag asserts
    → busy flag clears
```

**Verification:**
- [ ] Timestamps make sense (time > 0)
- [ ] Message appears in console
- [ ] Duration reasonable (write takes ~120µs in simulation)

### Test 2: Read Operation (Expected ~25ms)
```
[3690000 ns] Test 2 starts
    → Similar to write, but reads PHY register
    → MDIO frame: START, OPCODE(10=read), PHY_ADDR(0x01), REG_ADDR(0x02), TA, DATA_IN
    → PHY model returns 0xFFFF
[28470000 ns] Test 2 completes
    → prdata = 0xFFFF (from PHY model)
```

**Verification:**
- [ ] Read data appears in console
- [ ] Data matches PHY model response
- [ ] Timing reasonable

---

## Troubleshooting

### Problem: Compilation fails with `error: Code generator failure`
**Solution:**
```bash
# Make sure sim directory exists
mkdir -p sim

# Try again
iverilog -g2009 -o sim/mdio_sim.vvp tb_mdio_master.sv mdio_master.sv
```
- [ ] Resolved

### Problem: Simulation produces no output
**Solution:**
```bash
# Make sure you're in the sim directory
cd sim

# Run with explicit path
vvp mdio_sim.vvp -vcd waveforms.vcd
```
- [ ] Output appears

### Problem: GTKWave won't open waveforms
**Solution:**
```bash
# Check VCD file exists and has content
ls -l waveforms.vcd  # Should be ~64KB

# Install gtkwave if needed
sudo apt-get install gtkwave

# Try again
gtkwave waveforms.vcd &
```
- [ ] GTKWave opens

### Problem: No signals visible in GTKWave
**Solution:**
```bash
# In GTKWave:
1. Click the "+" next to "top" in Scope panel
2. Expand "tb_mdio_master" module
3. Drag signals to Signals panel
4. Click "Shift+Ctrl+G" to auto-scroll
```
- [ ] Signals appear

---

## Performance Verification

### Expected Values (with SYS_CLK_HZ=50MHz, MDC_HZ=2.5MHz in sim)

| Parameter | Expected | Actual | Status |
|-----------|----------|--------|--------|
| System Clock | 20 ns | ? | [ ] |
| MDC Period | 400 ns | ? | [ ] |
| Write Duration | ~110 µs | ? | [ ] |
| Read Duration | ~110 µs | ? | [ ] |
| Startup Time | <100 µs | ? | [ ] |

---

## Design Verification

### Core Logic (mdio_master.sv)
- [ ] APB interface working correctly
- [ ] Register map accessible (addresses 0x00-0x03)
- [ ] Clock divider produces correct MDC frequency
- [ ] Control register reflects write operations
- [ ] Status register reflects operation state
- [ ] Version register returns 0x0100

### Platform Wrapper (mdio_master_top.sv)
- [ ] (Not directly tested in this simulation)
- [ ] Will verify during synthesis/hardware integration
- [ ] Tri-state logic verified in hardware test
- [ ] GPIO pin mapping confirmed

### Testbench (tb_mdio_master.sv)
- [ ] PHY model responds correctly
- [ ] Read operation captures PHY data
- [ ] Write operation transmits to PHY
- [ ] MDIO bus simulation working

---

## Sign-Off

Once all checks pass:

```
✅ Simulation infrastructure ready
✅ Core IP functionality verified
✅ Testbench working correctly
✅ Waveform generation working
✅ Protocol compliance verified

Status: READY FOR NEXT PHASE

Next steps:
1. Customize testbench with additional test cases
2. Integrate mdio_master_top.sv into Efinix design
3. Verify hardware synthesis
4. Test on actual Efinix T120 board
```

---

## Quick Commands Reference

```bash
# Navigate to IP directory
cd /home/olle/efinity_p2/BRAM/T120F324_A/ip/mdio_master

# Full simulation (from scratch)
mkdir -p sim && iverilog -g2009 -o sim/mdio_sim.vvp tb_mdio_master.sv mdio_master.sv && cd sim && vvp mdio_sim.vvp -vcd waveforms.vcd && gtkwave waveforms.vcd &

# Just compile
iverilog -g2009 -o sim/mdio_sim.vvp tb_mdio_master.sv mdio_master.sv

# Just run (after compile)
cd sim && vvp mdio_sim.vvp -vcd waveforms.vcd

# Just view existing waveforms
gtkwave sim/waveforms.vcd &

# Clean everything
rm -rf sim *.vvp *.vcd
```

---

**Verification Status:** Ready to begin  
**Created:** January 4, 2026
