#ifndef PHY_MDIO_1000M_H
#define PHY_MDIO_1000M_H

#include <stdint.h>
#include <stdbool.h>

#define RTL8211F_PHY_ADDR       0x01

/* Standard MII / Clause-22 Registers */
#define PHY_REG_BMCR            0x00
#define PHY_REG_BMSR            0x01
#define PHY_REG_PHYID1          0x02
#define PHY_REG_PHYID2          0x03
#define PHY_REG_ANAR            0x04
#define PHY_REG_ANLPAR          0x05
#define PHY_REG_GBCR            0x09    /* 1000BASE-T Control */
#define PHY_REG_GBSR            0x0A    /* 1000BASE-T Status */
#define PHY_REG_PAGSR           0x1F    /* Page Select Register */

/* 1000M Configuration Bits */
#define BMCR_SPEED_1000M        0x0040  /* Bit 6 = 1000 Mbps */
#define BMCR_FULL_DUPLEX        0x0100  /* Bit 8 = Full Duplex */
#define BMCR_AN_RESTART         0x0200  /* Bit 9 = Restart Auto-Negotiation */
#define BMCR_AN_ENABLE          0x1000  /* Bit 12 = Auto-Negotiation Enable */
#define BMCR_RESET              0x8000  /* Bit 15 = Soft Reset */

#define GBCR_ADV_1000M_FD       0x0200  /* Advertise 1000BASE-T Full Duplex */
#define BMSR_LINK_STATUS        0x0004  /* Link up flag */
#define BMSR_AN_COMPLETE        0x0020  /* Auto-negotiation complete flag */

/**
 * @brief Initialize MDIO peripheral base address.
 * @param apb_mdio_base Base address of the APB MDIO Master.
 */
void phy_mdio_init(uint32_t apb_mdio_base);

/**
 * @brief Perform Clause-22 MDIO Register Read.
 * @param phy_addr PHY address (typically 0x01).
 * @param reg_addr Register address (0x00..0x1F).
 * @return 16-bit register value.
 */
uint16_t phy_mdio_read(uint8_t phy_addr, uint8_t reg_addr);

/**
 * @brief Perform Clause-22 MDIO Register Write.
 * @param phy_addr PHY address (typically 0x01).
 * @param reg_addr Register address (0x00..0x1F).
 * @param val 16-bit value to write.
 */
void phy_mdio_write(uint8_t phy_addr, uint8_t reg_addr, uint16_t val);

/**
 * @brief Assert and release hardware reset line to RTL8211F PHY.
 */
void phy_mdio_hw_reset(void);

/**
 * @brief Configure RTL8211F PHY in 1000M (Gigabit) Full Duplex mode as default.
 * @return true if configured and link partner negotiation initiated, false on bus error.
 */
bool phy_mdio_configure_1000m_default(void);

/**
 * @brief Poll until Gigabit Link is established or timeout expires.
 * @param timeout_ms Timeout in milliseconds.
 * @return true if 1000M link is UP, false if timed out.
 */
bool phy_mdio_wait_link_up(uint32_t timeout_ms);

#endif /* PHY_MDIO_1000M_H */
