/**
 * mdio_driver.h - C driver for mdio_master APB3 peripheral
 * 
 * Base address: IO_APB_SLAVE_0_INPUT + 0x1000 = 0xf8101000
 * 
 * MDIO register map (mdio_master.sv uses word-addressed paddr[3:0]):
 *   paddr=0 (offset 0x00): CTRL   - [0]=start, [1]=RW(1=read,0=write),
 *                                    [9:5]=PHY addr, [14:10]=Reg addr, [31:16]=Write data
 *   paddr=1 (offset 0x04): STATUS - [0]=busy, [1]=done, [31:16]=Read data
 *   paddr=2 (offset 0x08): CONFIG - [0]=PHY reset (0=reset, 1=normal), [1]=IRQ enable
 *   paddr=3 (offset 0x0C): VERSION - [15:0]=version
 * 
 * RTL8211F-CG PHY address is typically 0x01 (PHYAD[2:0] pins)
 */

#ifndef MDIO_DRIVER_H
#define MDIO_DRIVER_H

#include <stdint.h>

// MDIO master base address (second 4KB block in APB slave 0)
#define MDIO_BASE_ADDR       0xf8101000

// Register byte offsets
#define MDIO_CTRL_REG        0x00
#define MDIO_STATUS_REG      0x04
#define MDIO_CONFIG_REG      0x08
#define MDIO_VERSION_REG     0x0C

// Status bits
#define MDIO_STATUS_BUSY     (1 << 0)
#define MDIO_STATUS_DONE     (1 << 1)

// RTL8211F standard PHY address (depends on PHYAD pins - typically 0x01)
#define PHY_ADDR_DEFAULT     0x01

// IEEE 802.3 Standard PHY Registers (Clause 22)
#define PHY_REG_BMCR         0x00   // Basic Mode Control
#define PHY_REG_BMSR         0x01   // Basic Mode Status
#define PHY_REG_PHYID1       0x02   // PHY Identifier 1 (OUI MSB)
#define PHY_REG_PHYID2       0x03   // PHY Identifier 2 (OUI LSB + model)
#define PHY_REG_ANAR         0x04   // Auto-Negotiation Advertisement
#define PHY_REG_ANLPAR       0x05   // Auto-Negotiation Link Partner Ability
#define PHY_REG_ANER         0x06   // Auto-Negotiation Expansion
#define PHY_REG_GBCR         0x09   // 1000BASE-T Control
#define PHY_REG_GBSR         0x0A   // 1000BASE-T Status
#define PHY_REG_PHYSR        0x11   // RTL8211F PHY Specific Status

// Expected RTL8211F PHY ID
#define RTL8211F_PHYID1      0x001C   // Realtek OUI
#define RTL8211F_PHYID2_MASK 0xFFF0   // Model mask (ignore revision)
#define RTL8211F_PHYID2_VAL  0xC910   // RTL8211F model

// BMCR bits
#define BMCR_RESET           (1 << 15)
#define BMCR_AN_ENABLE       (1 << 12)
#define BMCR_AN_RESTART      (1 << 9)

// BMSR bits
#define BMSR_LINK_STATUS     (1 << 2)
#define BMSR_AN_COMPLETE     (1 << 5)

// RTL8211F PHYSR (reg 0x11) bits
#define PHYSR_LINK           (1 << 10)
#define PHYSR_SPEED_MASK     (3 << 4)
#define PHYSR_SPEED_10       (0 << 4)
#define PHYSR_SPEED_100      (1 << 4)
#define PHYSR_SPEED_1000     (2 << 4)
#define PHYSR_DUPLEX         (1 << 3)

// ============================================================================
// Low-level register access
// ============================================================================

static inline void mdio_write_reg(uint32_t offset, uint32_t val)
{
    volatile uint32_t *reg = (volatile uint32_t *)(MDIO_BASE_ADDR + offset);
    *reg = val;
}

static inline uint32_t mdio_read_reg(uint32_t offset)
{
    volatile uint32_t *reg = (volatile uint32_t *)(MDIO_BASE_ADDR + offset);
    return *reg;
}

// ============================================================================
// MDIO transaction functions
// ============================================================================

/**
 * mdio_wait_done() - Wait for MDIO transaction to complete
 * 
 * Two-phase polling:
 *   1. Wait for BUSY=1 (state machine picked up start_req on MDC falling edge)
 *   2. Wait for DONE=1 (transaction finished, read data available)
 * 
 * Returns: 1 on success, 0 on timeout
 */
static inline int mdio_wait_done(void)
{
    // Phase 1: Wait for BUSY to assert (transaction started)
    // At 1 MHz MDC, worst case is ~500ns (25 sys_clk cycles)
    int busy_seen = 0;
    for (int i = 0; i < 2000; i++) {
        if (mdio_read_reg(MDIO_STATUS_REG) & MDIO_STATUS_BUSY) {
            busy_seen = 1;
            break;
        }
    }
    if (!busy_seen)
        return 0;  // State machine never started - hardware problem
    
    // Phase 2: Wait for DONE flag (transaction complete, rdata valid)
    // At 1 MHz MDC, one MDIO frame = 64 MDC clocks = 64 µs
    for (int i = 0; i < 500000; i++) {
        uint32_t status = mdio_read_reg(MDIO_STATUS_REG);
        if (status & MDIO_STATUS_DONE)
            return 1;
    }
    return 0;  // Timeout
}

/**
 * mdio_read() - Read a PHY register via MDIO
 * @phy_addr: PHY address (0-31)
 * @reg_addr: Register address (0-31)
 * Returns: 16-bit register value, or 0xFFFF on error
 */
static inline uint16_t mdio_read(uint8_t phy_addr, uint8_t reg_addr)
{
    // Clear done flag first (write 1 to bit 1 of STATUS)
    mdio_write_reg(MDIO_STATUS_REG, MDIO_STATUS_DONE);
    
    // Build CTRL word: start=1, RW=1(read), phy_addr, reg_addr, wdata=0
    uint32_t ctrl = (1 << 0)                      // start
                  | (1 << 1)                       // RW = read
                  | ((phy_addr & 0x1F) << 5)       // PHY address
                  | ((reg_addr & 0x1F) << 10);     // Register address
    
    mdio_write_reg(MDIO_CTRL_REG, ctrl);
    
    // Wait for completion
    if (!mdio_wait_done())
        return 0xFFFF;
    
    // Read data from STATUS[31:16]
    uint32_t status = mdio_read_reg(MDIO_STATUS_REG);
    return (uint16_t)(status >> 16);
}

/**
 * mdio_write() - Write a PHY register via MDIO
 * @phy_addr: PHY address (0-31)
 * @reg_addr: Register address (0-31)
 * @data: 16-bit value to write
 * Returns: 1 on success, 0 on timeout
 */
static inline int mdio_write(uint8_t phy_addr, uint8_t reg_addr, uint16_t data)
{
    // Clear done flag
    mdio_write_reg(MDIO_STATUS_REG, MDIO_STATUS_DONE);
    
    // Build CTRL word: start=1, RW=0(write), phy_addr, reg_addr, wdata
    uint32_t ctrl = (1 << 0)                      // start
                  | (0 << 1)                       // RW = write
                  | ((phy_addr & 0x1F) << 5)       // PHY address
                  | ((reg_addr & 0x1F) << 10)      // Register address
                  | ((uint32_t)data << 16);         // Write data
    
    mdio_write_reg(MDIO_CTRL_REG, ctrl);
    
    return mdio_wait_done();
}

/**
 * mdio_phy_reset_release() - Release PHY from hardware reset
 * Sets CONFIG[0] = 1 (PHY reset inactive)
 */
static inline void mdio_phy_reset_release(void)
{
    mdio_write_reg(MDIO_CONFIG_REG, 0x01);
}

/**
 * mdio_phy_reset_assert() - Assert PHY hardware reset
 * Sets CONFIG[0] = 0 (PHY in reset)
 */
static inline void mdio_phy_reset_assert(void)
{
    mdio_write_reg(MDIO_CONFIG_REG, 0x00);
}

// ============================================================================
// RTL8211F Page Register Access
// ============================================================================
// RTL8211F uses paged register scheme.  Write page# to reg 0x1F first.

#define RTL8211F_PAGE_REG       0x1F

/**
 * rtl8211f_set_page() - Select RTL8211F register page
 */
static inline void rtl8211f_set_page(uint8_t phy_addr, uint16_t page)
{
    mdio_write(phy_addr, RTL8211F_PAGE_REG, page);
}

// ============================================================================
// RTL8211F RGMII Delay Configuration
// ============================================================================
// Page 0xd08, Register 0x11:
//   Bit 8: TXDLY - adds ~2ns delay on RXC output (PHY→FPGA clock)
//   Bit 3: RXDLY - adds ~2ns delay on internal TXC sampling (FPGA→PHY)
//
// For equal-length PCB traces, BOTH delays must be enabled.

#define RTL8211F_PAGE_RGMII    0x0d08
#define RTL8211F_REG_RGMII     0x11
#define RTL8211F_TXDLY_BIT     (1 << 8)   // Delay RXC output (PHY TX clock)
#define RTL8211F_RXDLY_BIT     (1 << 3)   // Delay internal TXC sampling (PHY RX clock)

/**
 * rtl8211f_setup_rgmii_delay() - Enable RGMII TX+RX internal clock delays
 * Required when PCB has equal-length clock and data traces.
 * @phy_addr: PHY address
 * Returns: 1 on success
 */
static inline int rtl8211f_setup_rgmii_delay(uint8_t phy_addr)
{
    // Switch to RGMII delay config page
    rtl8211f_set_page(phy_addr, RTL8211F_PAGE_RGMII);
    
    // Read current value of register 0x11
    uint16_t val = mdio_read(phy_addr, RTL8211F_REG_RGMII);
    
    // Enable both TX delay (bit 8) and RX delay (bit 3)
    val |= RTL8211F_TXDLY_BIT | RTL8211F_RXDLY_BIT;
    mdio_write(phy_addr, RTL8211F_REG_RGMII, val);
    
    // Return to page 0
    rtl8211f_set_page(phy_addr, 0x0000);
    
    return 1;
}

/**
 * rtl8211f_read_rgmii_delay() - Read current RGMII delay config
 * @phy_addr: PHY address
 * Returns: raw register value from page 0xd08 reg 0x11
 */
static inline uint16_t rtl8211f_read_rgmii_delay(uint8_t phy_addr)
{
    rtl8211f_set_page(phy_addr, RTL8211F_PAGE_RGMII);
    uint16_t val = mdio_read(phy_addr, RTL8211F_REG_RGMII);
    rtl8211f_set_page(phy_addr, 0x0000);
    return val;
}

/**
 * rtl8211f_soft_reset() - Perform PHY soft reset via BMCR
 * After changing RGMII delay settings, a soft reset applies them.
 */
static inline void rtl8211f_soft_reset(uint8_t phy_addr)
{
    uint16_t bmcr = mdio_read(phy_addr, PHY_REG_BMCR);
    mdio_write(phy_addr, PHY_REG_BMCR, bmcr | BMCR_RESET);
    // Bit self-clears after reset completes (~500ms max)
}

#endif // MDIO_DRIVER_H
