# MDIO Master IP for RTL8211F-CG PHY

## Overview

SystemVerilog Clause-22 MDIO Master designed for Efinix T120 FPGA (U100) 
to communicate with Realtek RTL8211F-CG Gigabit Ethernet PHY (U98).

## Hardware Connections

From your netlist (Netlist_top_level_2026-01-04.asc):

| Signal | U98 Pin | U100 Pin | FPGA GPIO | Description |
|--------|---------|----------|-----------|-------------|
| F2-MDC | 13 | T18 | GPIOB_TXN01 | Management Data Clock |
| F2-MDIO | 14 | R15 | GPIOB_TXN05_CDI26 | Management Data I/O |
| F2-RSTB | 12 | T17 | GPIOB_TXP00 | PHY Reset (active low) |

## Files

- `mdio_master.sv` - Core MDIO master with APB interface
- `mdio_master_top.sv` - Top-level wrapper matching Efinix GPIO names
- `tb_mdio_master.sv` - Simulation testbench

## Register Map (APB Interface)

| Offset | Name | Access | Description |
|--------|------|--------|-------------|
| 0x00 | CTRL | RW | Control Register |
| 0x04 | STATUS | RO/W1C | Status Register |
| 0x08 | CONFIG | RW | Configuration Register |
| 0x0C | VERSION | RO | Version Register |

### CTRL Register (0x00)

| Bits | Field | Description |
|------|-------|-------------|
| [0] | START | Write 1 to start transaction (auto-clears) |
| [1] | RW | 1=Read, 0=Write |
| [4:2] | Reserved | - |
| [9:5] | PHY_ADDR | PHY Address (RTL8211F default: 0x01) |
| [14:10] | REG_ADDR | Register Address |
| [15] | Reserved | - |
| [31:16] | WDATA | Write Data |

### STATUS Register (0x04)

| Bits | Field | Description |
|------|-------|-------------|
| [0] | BUSY | 1=Transaction in progress |
| [1] | DONE | 1=Transaction complete (write 1 to clear) |
| [15:2] | Reserved | - |
| [31:16] | RDATA | Read Data |

### CONFIG Register (0x08)

| Bits | Field | Description |
|------|-------|-------------|
| [0] | PHY_RST | 0=PHY Reset, 1=Normal operation |
| [1] | IRQ_EN | Interrupt enable |

## RTL8211F-CG Important Registers

### Basic Registers (Clause 22)

| Address | Name | Description |
|---------|------|-------------|
| 0x00 | BMCR | Basic Mode Control |
| 0x01 | BMSR | Basic Mode Status |
| 0x02 | PHYID1 | PHY ID 1 (0x001C) |
| 0x03 | PHYID2 | PHY ID 2 (0xC916) |
| 0x04 | ANAR | Auto-Negotiation Advertisement |
| 0x05 | ANLPAR | Auto-Negotiation Link Partner Ability |
| 0x06 | ANER | Auto-Negotiation Expansion |
| 0x09 | GBCR | 1000BASE-T Control |
| 0x0A | GBSR | 1000BASE-T Status |

### Extended Registers (Page 0xA43)

To access extended registers:
1. Write page number to register 0x1F (Page Select)
2. Read/write from register 0x10-0x1E

| Page | Register | Name | Description |
|------|----------|------|-------------|
| 0xA43 | 0x19 | PHYCR1 | PHY Specific Control 1 |
| 0xA43 | 0x1A | PHYCR2 | PHY Specific Control 2 |
| 0xA43 | 0x1B | PHYSR | PHY Specific Status |

## Usage Example (C code for RISC-V)

```c
#include <stdint.h>

#define MDIO_BASE       0x80010000  // Adjust to your APB address
#define MDIO_CTRL       (*(volatile uint32_t*)(MDIO_BASE + 0x00))
#define MDIO_STATUS     (*(volatile uint32_t*)(MDIO_BASE + 0x04))
#define MDIO_CONFIG     (*(volatile uint32_t*)(MDIO_BASE + 0x08))

#define PHY_ADDR        0x01  // RTL8211F default

// Release PHY from reset
void phy_init(void) {
    MDIO_CONFIG = 0x01;  // PHY_RST = 1
    for (volatile int i = 0; i < 100000; i++);  // Wait ~10ms
}

// Read PHY register
uint16_t phy_read(uint8_t reg) {
    // Build CTRL: start=1, rw=1(read), phy_addr, reg_addr
    uint32_t ctrl = (1 << 0) |          // START
                    (1 << 1) |          // RW=read
                    (PHY_ADDR << 5) |   // PHY_ADDR
                    (reg << 10);        // REG_ADDR
    MDIO_CTRL = ctrl;
    
    // Wait for completion
    while (MDIO_STATUS & 0x01);
    
    return (MDIO_STATUS >> 16) & 0xFFFF;
}

// Write PHY register
void phy_write(uint8_t reg, uint16_t data) {
    // Build CTRL: start=1, rw=0(write), phy_addr, reg_addr, wdata
    uint32_t ctrl = (1 << 0) |          // START
                    (0 << 1) |          // RW=write
                    (PHY_ADDR << 5) |   // PHY_ADDR
                    (reg << 10) |       // REG_ADDR
                    ((uint32_t)data << 16);  // WDATA
    MDIO_CTRL = ctrl;
    
    // Wait for completion
    while (MDIO_STATUS & 0x01);
}

// Read PHY ID (should return 0x001CC916 for RTL8211F)
uint32_t phy_read_id(void) {
    uint32_t id1 = phy_read(0x02);  // PHYID1
    uint32_t id2 = phy_read(0x03);  // PHYID2
    return (id1 << 16) | id2;
}

// Example: Get link status
int phy_get_link_status(void) {
    uint16_t bmsr = phy_read(0x01);  // Read BMSR twice per spec
    bmsr = phy_read(0x01);
    return (bmsr >> 2) & 1;  // Bit 2 = Link Status
}
```

## Efinix Efinity Integration

### 1. GPIO Configuration (T120F324_A.peri.xml)

Ensure these GPIOs are configured:

```xml
<!-- F2_MDC - Output -->
<efxpt:gpio name="F2_MDC" gpio_def="GPIOB_TXN01" mode="output" 
            io_standard="3.3 V LVTTL / LVCMOS">
    <efxpt:output_config name="F2_MDC" register_option="none" 
                         drive_strength="1"/>
</efxpt:gpio>

<!-- F2_MDIO - Bidirectional (Inout) -->
<efxpt:gpio name="F2_MDIO" gpio_def="GPIOB_TXN05" mode="inout"
            io_standard="3.3 V LVTTL / LVCMOS">
    <efxpt:input_config name="F2_MDIO_IN" conn_type="normal"/>
    <efxpt:output_config name="F2_MDIO_OUT" register_option="none"/>
    <efxpt:output_enable_config name="F2_MDIO_OE"/>
</efxpt:gpio>

<!-- F2_RSTB - Output -->
<efxpt:gpio name="F2_RSTB" gpio_def="GPIOB_TXP00" mode="output"
            io_standard="3.3 V LVTTL / LVCMOS">
    <efxpt:output_config name="F2_RSTB" register_option="none"
                         drive_strength="1"/>
</efxpt:gpio>
```

### 2. Sapphire RISC-V Integration

When you add Efinix Sapphire RISC-V:

1. Add APB peripheral to the Sapphire configuration
2. Assign base address (e.g., 0x80010000)
3. Connect signals:
   - `pclk` → `clk`
   - `preset_n` → `rst_n`
   - APB signals to `psel`, `penable`, `pwrite`, `paddr`, `pwdata`, `prdata`

### 3. Instantiation Example

```systemverilog
mdio_master_top #(
    .SYS_CLK_HZ (50_000_000),  // Match your system clock
    .MDC_HZ     (1_000_000)    // 1 MHz MDC (safe for RTL8211F)
) u_mdio (
    .clk          (sys_clk),
    .rst_n        (sys_rst_n),
    
    // APB from Sapphire
    .psel         (apb_mdio_psel),
    .penable      (apb_penable),
    .pwrite       (apb_pwrite),
    .paddr        (apb_paddr[3:0]),
    .pwdata       (apb_pwdata),
    .prdata       (apb_mdio_prdata),
    .pready       (apb_mdio_pready),
    .pslverr      (),
    
    // PHY GPIO
    .F2_MDC       (F2_MDC),
    .F2_MDIO_IN   (F2_MDIO_IN),
    .F2_MDIO_OUT  (F2_MDIO_OUT),
    .F2_MDIO_OE   (F2_MDIO_OE),
    .F2_RSTB      (F2_RSTB),
    
    // Interrupt (optional)
    .irq          (mdio_irq)
);
```

## Simulation

```bash
# Using Icarus Verilog
iverilog -g2012 -o sim.vvp mdio_master.sv tb_mdio_master.sv
vvp sim.vvp
gtkwave tb_mdio_master.vcd
```

## Getting Started Steps

1. **Test without RISC-V first:**
   - Instantiate `mdio_master_top` in your design
   - Create simple state machine to read PHY ID (registers 0x02, 0x03)
   - Verify you get 0x001C (PHYID1) and 0xC916 (PHYID2)

2. **Add Sapphire RISC-V:**
   - Use Efinity IP Manager to add Sapphire SoC
   - Add APB peripheral for MDIO master
   - Write simple firmware to test PHY access

3. **Bring up RGMII:**
   - After MDIO works, configure PHY for RGMII mode
   - Add RGMII MAC IP or custom logic

## License

MIT License - Feel free to use and modify.
