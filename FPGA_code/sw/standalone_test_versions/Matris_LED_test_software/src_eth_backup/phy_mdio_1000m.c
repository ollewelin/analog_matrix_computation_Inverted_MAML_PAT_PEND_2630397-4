#include "phy_mdio_1000m.h"

#if __has_include("bsp.h")
#include "bsp.h"
#define DELAY_US(us) bsp_uDelay(us)
#else
static inline void DELAY_US(uint32_t us) {
    volatile uint32_t count = us * 50;
    while (count--);
}
#endif

/* APB MDIO Master Register offsets */
#define REG_MDIO_CTRL       0x00
#define REG_MDIO_STATUS     0x04
#define REG_MDIO_CONFIG     0x08

#define MDIO_START_BIT      (1 << 0)
#define MDIO_READ_BIT       (1 << 1)
#define MDIO_BUSY_BIT       (1 << 0)

static uint32_t g_mdio_base = 0;

void phy_mdio_init(uint32_t apb_mdio_base) {
    g_mdio_base = apb_mdio_base;
}

static inline void write_reg(uint32_t offset, uint32_t val) {
    *(volatile uint32_t*)(uintptr_t)(g_mdio_base + offset) = val;
}

static inline uint32_t read_reg(uint32_t offset) {
    return *(volatile uint32_t*)(uintptr_t)(g_mdio_base + offset);
}

static void wait_mdio_idle(void) {
    uint32_t timeout = 50000;
    while ((read_reg(REG_MDIO_STATUS) & MDIO_BUSY_BIT) && timeout--) {
        DELAY_US(1);
    }
}

uint16_t phy_mdio_read(uint8_t phy_addr, uint8_t reg_addr) {
    if (g_mdio_base == 0) return 0xFFFF;
    wait_mdio_idle();

    uint32_t ctrl = MDIO_START_BIT | MDIO_READ_BIT |
                    ((uint32_t)(phy_addr & 0x1F) << 5) |
                    ((uint32_t)(reg_addr & 0x1F) << 10);
    write_reg(REG_MDIO_CTRL, ctrl);

    wait_mdio_idle();
    uint32_t status = read_reg(REG_MDIO_STATUS);
    return (uint16_t)((status >> 16) & 0xFFFF);
}

void phy_mdio_write(uint8_t phy_addr, uint8_t reg_addr, uint16_t val) {
    if (g_mdio_base == 0) return;
    wait_mdio_idle();

    uint32_t ctrl = MDIO_START_BIT | // write = 0
                    ((uint32_t)(phy_addr & 0x1F) << 5) |
                    ((uint32_t)(reg_addr & 0x1F) << 10) |
                    ((uint32_t)val << 16);
    write_reg(REG_MDIO_CTRL, ctrl);

    wait_mdio_idle();
}

void phy_mdio_hw_reset(void) {
    if (g_mdio_base == 0) return;
    /* Pull PHY reset pin LOW (Bit 0 of CONFIG register = 0) */
    write_reg(REG_MDIO_CONFIG, 0x00);
    DELAY_US(50000);   /* Hold in reset for 50 ms */

    /* Release PHY reset pin HIGH (Bit 0 of CONFIG register = 1) */
    write_reg(REG_MDIO_CONFIG, 0x01);
    DELAY_US(300000);  /* Wait 300 ms for PHY boot and internal clock stabilization */
}

bool phy_mdio_configure_1000m_default(void) {
    /* 1. Perform Hardware Reset */
    phy_mdio_hw_reset();

    /* 2. Validate PHY JEDEC ID (Realtek RTL8211F should return 0x001C in PHYID1) */
    uint16_t id1 = phy_mdio_read(RTL8211F_PHY_ADDR, PHY_REG_PHYID1);
    if (id1 != 0x001C) {
        return false; /* Bus error or PHY not responding */
    }

    /* 3. Configure 1000BASE-T Control Register (Reg 0x09: GBCR)
     * Enable 1000BASE-T Full Duplex advertisement (Bit 9)
     */
    phy_mdio_write(RTL8211F_PHY_ADDR, PHY_REG_GBCR, GBCR_ADV_1000M_FD);

    /* 4. Configure Auto-Negotiation Advertisement (Reg 0x04: ANAR)
     * Advertise 100BASE-TX FD/HD, 10BASE-T FD/HD, Selector 802.3
     */
    phy_mdio_write(RTL8211F_PHY_ADDR, PHY_REG_ANAR, 0x01E1);

    /* 5. Set Calibrated RGMII TX/RX Clock Timing Delays
     * Switch to Page 0xd08, write Reg 0x11 = 0x018A, return to Page 0
     */
    phy_mdio_write(RTL8211F_PHY_ADDR, PHY_REG_PAGSR, 0x0d08);
    DELAY_US(1000);
    phy_mdio_write(RTL8211F_PHY_ADDR, 0x11, 0x018A);
    DELAY_US(1000);
    phy_mdio_write(RTL8211F_PHY_ADDR, PHY_REG_PAGSR, 0x0000);

    /* 6. Enable 1000M Full Duplex Auto-Negotiation (Reg 0x00: BMCR)
     * Bit 12 = AN Enable, Bit 9 = Restart AN, Bit 8 = Full Duplex, Bit 6 = 1000M LSB
     */
    uint16_t bmcr = BMCR_AN_ENABLE | BMCR_AN_RESTART | BMCR_FULL_DUPLEX | BMCR_SPEED_1000M;
    phy_mdio_write(RTL8211F_PHY_ADDR, PHY_REG_BMCR, bmcr);

    return true;
}

bool phy_mdio_wait_link_up(uint32_t timeout_ms) {
    while (timeout_ms--) {
        /* Double-read BMSR (bit 2 is latch-low) */
        phy_mdio_read(RTL8211F_PHY_ADDR, PHY_REG_BMSR);
        uint16_t bmsr = phy_mdio_read(RTL8211F_PHY_ADDR, PHY_REG_BMSR);

        if (bmsr & BMSR_LINK_STATUS) {
            return true; /* Link established at 1000M Full Duplex */
        }
        DELAY_US(1000);
    }
    return false;
}
